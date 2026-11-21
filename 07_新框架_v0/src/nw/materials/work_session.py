"""Budgeted stage calls; retain the old study experiment for historical replay."""
from dataclasses import replace
import json
from pathlib import Path
import re
from uuid import NAMESPACE_URL,uuid5

from nw.call_budget import prepare_call
from nw.call_control import model_settings
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.materials.steps import type_connections
from nw.materials.work_catalog import SourceDesk
from nw.materials.work_contract import POLICY,STUDY_PROMPT,functions_for,validate_study
from nw.materials.work_application import APPLICATION_PROMPT
from nw.store import Store
from nw.task_models import InputManifest,TaskRequest,canonical,content_sha256
from nw.tasks import freeze_manifest,read_input_manifest,run_task


def model_source(source: dict,*,stage: str | None=None,semantics: dict | None=None, full_text: bool=False,
                 step_use: str | None = None) -> dict:
    result={key:value for key,value in source.items() if key!='application_layers'}
    if step_use is not None:
        if stage:
            type_connections.apply_step_text(result, source, stage)
        result.pop('original_text')
        result['step_use'] = step_use
        result['application_layers'] = (semantics or {}).get('application_guidance', [])
        return result
    layers=[]
    for layer in source['application_layers']:
        raw=layer['text'];match=re.search(r'(?m)^```json[^\n]*\n',raw)
        try:
            value,_=json.JSONDecoder().raw_decode(raw[match.end() if match else max(raw.find('{'),0):].strip())
            bindings=value.get('runtime_calling_layer',[]) if isinstance(value,dict) else []
            guidance=[{k:b[k] for k in ('semantic_interpretation','creation_binding') if k in b}
                      for b in bindings if isinstance(b,dict)]
        except ValueError:
            guidance=[]
        layers.append({'source_ref':layer['source_ref'],'aligned_fields':layer['aligned_fields'],
                       'rejected_fields':layer['rejected_fields'],'legacy_application_guidance':guidance,
                       'authority':'compare_with_original_not_a_fact_or_approval'})
    result['application_layers']=(semantics['application_guidance'] if semantics is not None else layers)
    if stage:
        type_connections.apply_step_text(result, source, stage)
    if stage and not full_text:
        try:original=json.loads(result['original_text'])
        except ValueError:original=None
        if isinstance(original,dict):
            empty=[key for key,value in original.items() if value is None or value==[] or value=={}]
            result['frozen_original_text_sha256']=source['original_text_sha256']
            result['original_text']=canonical({key:value for key,value in original.items() if key not in empty})
            result['original_text_sha256']=content_sha256(result['original_text'])
            result['projection']={'policy':'omit_only_top_level_null_or_empty_containers',
                'omitted_empty_fields':empty,'empty_fields_provide_no_preset_project_values':True,
                'complete_original_frozen_and_readable':True}
    return result


def _ident(text: str) -> str:
    return uuid5(NAMESPACE_URL,'nw:'+text).hex


def _study_call(store: Store,request: TaskRequest,config: Config,provider: LLMProvider,
                index: int,payload: dict,sources: list[dict],desk: SourceDesk,retry_failed: bool,verify,
                *,prompt: str=STUDY_PROMPT,validator=None,version: str='source-method-study-v2',
                read_only_sources: list[dict] | None=None, step_material: str = '',
                prompt_suffix: str = '') -> tuple[dict,dict]:
    if provider.name=='ollama' and payload.get('stage'):
        from nw.materials.phase_schema import schema
        shape=schema(payload['stage'],sources,
            payload.get('readable_source_ids',[]),payload.get('inputs'),allow_requests=payload.get('mode')!='execute',
            contracts=payload.get('source_contracts'), type_network_inputs=bool(payload.get('type_network_policy')),
            chapter_progress=bool(payload.get('chapter_progress_policy')),
            cast_demand=bool(payload.get('cast_demand_policy')),
            narration=payload.get('narration_policy', False))
        if payload.get('network_design_candidates'):
            from nw.materials.design_network import add_schema
            add_schema(shape, payload['network_design_candidates'])
        if 'static_relations_basis' in payload:
            from nw.materials.static_followup_call import FOLLOWUP_FIELDS
            products = shape['properties']['products']
            products['properties'] = {key: products['properties'][key] for key in FOLLOWUP_FIELDS}
            products['required'] = list(FOLLOWUP_FIELDS)
        if 'production_methods' in payload:
            from nw.production_methods.runtime import extra_fields
            ai_world = payload.get('production_method_selection', {}).get('mode') == 'ai'
            shape = extra_fields(shape, ai_world=ai_world)
            if ai_world:
                from nw.production_methods.world_gap import schema as gap_schema
                shape = {'anyOf': [*shape.get('anyOf', [shape]), gap_schema({'candidates': payload['production_methods']})]}
        if 'cast_gap_format' in payload or 'cast_gap_limit_instruction' in payload:
            from nw.materials.cast_gap import schema as cast_gap_schema
            shape = {'anyOf': [*shape.get('anyOf', [shape]), cast_gap_schema()]}
        config=replace(config,params={**config.params,'format':shape})
    root=_ident(f'{version}:{request.id}:{index}')
    previous=store.connection.execute('SELECT id,attempt,status,validation,request_json FROM task_calls WHERE root_id=? ORDER BY attempt DESC LIMIT 1',(root,)).fetchone()
    saved=json.loads(previous['request_json']) if previous else None
    attempt=previous['attempt'] if previous else 1
    retry_of=None
    ident=previous['id'] if previous else root
    if previous and retry_failed and previous['validation']!='VALID':
        attempt+=1;retry_of=previous['id'];ident=_ident(f'{root}:retry:{attempt}')
    elif previous and previous['attempt']>1:
        retry_of=saved['retry_of']
    model_payload={key:value for key,value in payload.items() if key!='mode'}
    if payload.get('stage_source_policy'):
        model_payload['current_instruction'] = ('所请求的本步资料已交付。现在提交本步设计产物或逐项说明为何不适用。'
            if payload['mode'] == 'execute' else '按本步资料与实际前置完成设计，需要补查时只在本步查找。')
    elif payload.get('mode'):
        model_payload['current_instruction']=('本步请求的完整原文已经交付，现在提交实际设计产物。'
            if payload['mode']=='execute' else '使用已给原文与上游产物完成当前设计；确实缺方法时才检索、读取。')
    payload_text=canonical(model_payload)
    if saved:
        # Resume with the exact original messages, including any older step text.
        system_text=saved['payload']['messages'][0]['content']
    else:
        system_text=prompt+prompt_suffix
    if step_material and not saved:
        from nw.materials.stage_input import step_material_prompt
        step_sources=[] if payload.get('stage_source_policy') else [
            *sources,*payload.get('method_requirement_sources',()),*payload.get('semantic_requirement_sources',())]
        system_text=step_material_prompt(prompt,step_material,(s['source']['key'] for s in step_sources))+prompt_suffix
    messages=[{'role':'system','content':system_text},{'role':'user','content':payload_text}]
    params,_=prepare_call(store,request.budget_id,provider.name,config.params,messages)
    originals=[*sources,*(read_only_sources or [])]
    frozen={'study_input':model_payload,'call_mode':payload.get('mode'),'frozen_sources':originals,'base_plan_manifest':request.manifest_id,
            'actual_messages_sha256':content_sha256(messages)}
    manifest_id=saved['manifest_id'] if saved else 'method-study:'+ident
    try:
        freeze_manifest(store,InputManifest(manifest_id,'material_work',
            model_settings(provider,config.model,params,version),content_sha256(frozen)),frozen)
    except ValueError as exc:
        if saved and read_input_manifest(store, manifest_id)[1].get('frozen_sources') != originals:
            raise ValueError('STALE_MATERIAL: checkpoint sources changed; propose a new plan with current sources') from exc
        raise
    task=TaskRequest(ident,request.project_id,'material_work',manifest_id,{'messages':messages},request.budget_id,attempt,retry_of)
    def before() -> None:
        if verify:verify()
        desk.verify(originals)
    validate=validator or (lambda value:validate_study(value,sources,payload['scope'],payload['demand']))
    result=run_task(store,task,provider,config,validate=validate,before_reserve=before)
    if result.validation!='VALID':
        raise ValueError(f'MATERIAL_WORK: {result.status}/{result.validation}: {result.reason or "study_not_ready"}; task={ident}')
    validate(result.parsed)
    return result.parsed,{'task_id':ident,'manifest_id':manifest_id}


def legacy_study_plan(store: Store,request: TaskRequest,package: dict,provider: LLMProvider,config: Config,*,
               retry_failed: bool=False,verify=None,max_rounds: int=8) -> tuple[TaskRequest,dict]:
    workspace=store.directory.parent
    if not (workspace/'materials/catalog.db').is_file():
        if config.source_driven:
            raise ValueError('MATERIAL_WORK: MATERIAL_CATALOG_REQUIRED: index the source materials before novel design')
        return request,package
    if package.get('material_work'):
        SourceDesk(workspace).verify(package['material_work']['sources']);return request,package
    desk=SourceDesk(workspace)
    sources={}
    for row in package.get('materials',[]):
        ident=row['source']['id']
        sources[ident]=desk.read(ident)
    demand=' '.join((package['brief']['text'],package['brief']['constraints']))
    responses=[];history=[];memory=None
    for index in range(max_rounds):
        payload={'policy':POLICY,'round':index,'scope':package['scope'],'demand':demand,
                 'required_functions':functions_for(package['scope']),'directory':desk.directory(),
                 'sources':[model_source(row) for row in sources.values()],
                 'responses':responses,'previous_study':memory,'parent':package.get('parent'),
                 'parent_material_work':package.get('parent_material_work')}
        result,receipt=_study_call(store,request,config,provider,index,payload,list(sources.values()),desk,retry_failed,verify)
        history.append(receipt)
        if result['status']=='ready':break
        responses=[]
        for action in result['requests']:
            if action['action']=='search':
                responses.append(desk.search(action['query'],cursor=action.get('cursor',0)))
            else:
                source=desk.read(action['id']);sources[action['id']]=source
                responses.append({'read':action['id'],'source_sha256':source['source']['sha256']})
        memory=result
    else:
        raise ValueError('MATERIAL_WORK: source study did not reach ready within its bounded work rounds')
    session={'policy':POLICY,'id':'work:'+request.id,'scope':package['scope'],
             'sources':list(sources.values()),'result':result,'calls':history}
    desk.verify(session['sources'])
    package={**package,'material_work':session,'material_mode':'source_driven_active'}
    if package.get('material_recall'):
        used={i for row in result['work_plan'] for i in row['source_ids']}
        # The old recall list is a seed. The model's actual method work decides
        # optional use; inherited type decisions and source procedures remain.
        from nw.materials.binding import BOOK,PROCESS
        package['materials']=[row for row in package.get('materials',[]) if row['source']['id'] in used or row['profile'] in BOOK|PROCESS]
    from nw.materials.binding import material_prompt
    from nw.materials.stage_input import model_package,input_record
    from nw.plan_contract import plan_prompt
    prompt=plan_prompt(package['scope'])+material_prompt(package.get('materials',[]),book=package['scope']=='book',deferrals=package.get('material_deferrals'))+APPLICATION_PROMPT
    if package.get('length_context'):
        from nw.length_plan import instructions
        prompt += '\n' + instructions('plan', package['length_context'])
    package['material_input']=input_record(package)
    messages=[{'role':'system','content':prompt},{'role':'user','content':canonical(model_package(package))}]
    params,_=prepare_call(store,request.budget_id,provider.name,config.params,messages)
    manifest_id=request.manifest_id+':source-driven'
    from nw.tasks import read_input_manifest
    previous,_=read_input_manifest(store,request.manifest_id)
    manifest=replace(InputManifest(**previous),id=manifest_id,
                     settings=model_settings(provider,config.model,params,'story-plan-v2-materials'),
                     context_sha256=content_sha256(package))
    freeze_manifest(store,manifest,package)
    return replace(request,manifest_id=manifest_id,payload={'messages':messages}),package


def drive_plan(store: Store,request: TaskRequest,package: dict,provider: LLMProvider,config: Config,*,
               retry_failed: bool=False,verify=None,max_rounds: int=8,method_decision=None) -> tuple[TaskRequest,dict]:
    """Normal entry: create actual upstream products before calling each method."""
    from nw.materials.phase_flow import drive_phases
    return drive_phases(store,request,package,provider,config,retry_failed=retry_failed,
                        verify=verify,max_rounds=max_rounds,method_decision=method_decision)
