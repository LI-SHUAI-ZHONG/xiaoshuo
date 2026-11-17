"""Run pinned source governance on actual stage inputs and replay it at adoption."""
from collections.abc import Iterator
from collections import Counter
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from nw.materials.catalog import _connect,show_fragment
from nw.materials.governance_contracts import (SOURCE_ID,NAMES,CONNECTION_ENUMS,DYNAMIC_LIMITS,
    compile_governance,fingerprint)
from nw.materials.governance_checks import check_dynamic_references, evaluate_governance
from nw.materials.steps.bind_scope_type_rules import TDV_020
from nw.materials.steps.type_connections import FILE_SHA256, material_document
from nw.materials.type_adjudication import _original

GROUPS={'connection_id':'connections','dynamic_pattern_id':'dynamic_patterns',
        'static_pattern_id':'static_patterns','combination_id':'combinations'}
CONFIG=('genre_ids','mechanism_ids','structure_ids','style_ids','tone_ids')


def _document(workspace: Path,db,source_id: str,name: str) -> dict:
    rows=db.execute('''SELECT u.*,f.sha256 AS block_sha,s.path,s.file_sha256
        FROM material_units u JOIN fragments f ON f.id=u.fragment_id
        JOIN sources s ON s.id=f.source_id
        WHERE f.source_id=? AND f.kind='source_block' AND f.key=?
        AND u.kind='json_document' AND u.locator='' ''',(source_id,name)).fetchall()
    if len(rows)!=1:raise ValueError('MATERIAL_GOVERNANCE: missing/ambiguous original: '+name)
    row=dict(rows[0]);block=show_fragment(workspace,row['fragment_id'])
    if block['sha256']!=row['block_sha']:raise ValueError('MATERIAL_GOVERNANCE: original block changed')
    raw=show_fragment(workspace,row['id'])
    if sha256(raw['text'].encode('utf-8')).hexdigest()!=row['sha256']:
        raise ValueError('MATERIAL_GOVERNANCE: original document changed')
    problems=[];value=_original(json.loads(raw['text']),problems)
    if problems:raise ValueError('MATERIAL_GOVERNANCE: ambiguous original JSON')
    if source_id == SOURCE_ID and row['file_sha256'] == FILE_SHA256:
        embedded = material_document(name)
        if value != embedded:
            raise ValueError('MATERIAL_GOVERNANCE: embedded original differs from current source: '+name)
        value = embedded
    return {'name':name,'value':value,'source_ref':{'id':row['fragment_id'],'source_id':source_id,
        'sha256':row['block_sha'],'file_sha256':row['file_sha256'],'path':row['path']},
        'document_ref':{k:row[k] for k in ('id','sha256','byte_start','byte_end','locator')}}


def load_governance(workspace: Path) -> dict | None:
    """Small independent test catalogs lack this source; partial real sets fail closed."""
    if not (workspace/'materials/catalog.db').is_file():return None
    with closing(_connect(workspace,write=False)) as db:
        if db.execute('SELECT id FROM sources WHERE id=?',(SOURCE_ID,)).fetchone() is None:
            marks=','.join('?' for _ in NAMES)
            if db.execute(f'SELECT 1 FROM fragments WHERE kind=\'source_block\' AND key IN ({marks}) LIMIT 1',NAMES).fetchone():
                raise ValueError('MATERIAL_GOVERNANCE: governance originals exist under an unreviewed source version')
            return None
        documents=[_document(workspace,db,SOURCE_ID,name) for name in NAMES]
        enum=_document(workspace,db,SOURCE_ID,'类型连接枚举.json')
        limits=_document(workspace,db,DYNAMIC_LIMITS['source_id'],'类型动态传播限制.json')
    expected=CONNECTION_ENUMS
    checks=[{'document':'类型连接枚举.json','verified':
        enum['document_ref']['id']==expected['document_ref']['id']
        and enum['document_ref']['sha256']==expected['document_ref']['sha256']
        and enum['source_ref']['sha256']==expected['source_block_ref']['sha256']
        and enum['value']==expected['value']},
        {'document':'类型动态传播限制.json','verified':
         limits['document_ref']['id']==DYNAMIC_LIMITS['document_id']
         and limits['document_ref']['sha256']==DYNAMIC_LIMITS['document_sha256']
         and all(limits['value'].get('global_defaults',{}).get(k)==DYNAMIC_LIMITS[k] for k in
             ('max_activated_rules_per_scene','max_state_updates_per_scene','max_propagation_depth'))}]
    contract=compile_governance(documents)
    if contract['status']!='ready' or not all(r['verified'] for r in checks):
        raise ValueError('MATERIAL_GOVERNANCE: unreviewed or changed governance/dependency originals')
    return {'status':'ready','contract':contract,'dependency_checks':checks,
        'pins':[{'source_ref':d['source_ref'],'document_ref':d['document_ref']} for d in [*documents,enum,limits]]}


def _source_objects(value: object):
    if isinstance(value,dict):
        if any(k in value for k in GROUPS):yield value
        elif isinstance(value.get('items'),list):
            for row in value['items']:yield from _source_objects(row)
        elif isinstance(value.get('connections'),list):
            for row in value['connections']:yield from _source_objects(row)
    elif isinstance(value,list):
        for row in value:yield from _source_objects(row)


def stage_governance_inputs(stage: str,value: dict,products: dict,sources: list[dict],context: dict) -> dict:
    supplied=deepcopy(context.get('governance_inputs',{}).get(stage,{}))
    # Only the frozen request can provide review/registry authority, never model metadata.
    supplied.pop('subjects',None);supplied.pop('project_config',None)
    groups={kind:[] for kind in GROUPS.values()};bindings=[];versions=[]
    used={r['source_id'] for r in value.get('_uses',[])}
    for source in sources:
        if source['source']['id'] not in used:continue
        try:raw=json.loads(source['original_text'])
        except (ValueError,TypeError):continue
        for row in _source_objects(raw):
            kind=next(GROUPS[k] for k in GROUPS if k in row)
            groups[kind].append(deepcopy(row));bindings.append({'source_id':source['source']['id'],
                'kind':kind,'index':len(groups[kind])-1,'subject_sha256':fingerprint(row)})
            expected='TYPE_C-1.0.0' if kind=='connections' else 'H0D-1.0.0'
            if row.get('schema_version')!=expected:
                versions.append({'source_id':source['source']['id'],'kind':kind,
                    'actual_version':row.get('schema_version'),'governance_version':expected,
                    'reason':'缺少对象/父文档确切版本映射；不跨版本继承治理原义'})
    metadata=value.get('_governance');config=metadata.get('project_config') if isinstance(metadata,dict) else None
    supplied.update(scope={**supplied.get('scope',{}),'source_id':SOURCE_ID,
        'stage':'scene' if stage in ('state_transition','state_propagation','anchor_design','expression_design') else 'design',
        'workflow_stage':stage,'action':'use_stage_methods','target':'formal_active','document_names':NAMES},
        subjects=groups,source_bindings=bindings,
        source_version_issues=versions,
        stage_product_sha256=fingerprint({k:v for k,v in value.items() if k!='_governance'}))
    if stage=='type_selection':
        if isinstance(config,dict):supplied['project_config']=deepcopy(config)
    else:supplied['project_config']=[]  # Selection owns configuration; no guessed empty config.
    return supplied


def _adaptation_references(value: object, path: str) -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        if value.keys() & {'dynamic_rule_ids', 'source_rule_ids', 'source_refs'}:
            yield path, value
        for key, item in value.items():
            yield from _adaptation_references(item, path + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _adaptation_references(item, f'{path}/{index}')


def _check_adaptation_references(value: dict, inputs: dict, current_rules: dict) -> Iterator[dict]:
    for index, row in enumerate(value.get('adaptations', ())):
        for path, subject in _adaptation_references(row['parameters'], f'/adaptations/{index}/parameters'):
            if result := check_dynamic_references(inputs, subject, current_rules):
                status, findings, fields = result
                yield {**TDV_020, 'status': status, 'findings': findings, 'affected_fields': fields,
                       'checked_input': {'subject': {'kind': 'adaptation_parameters', 'id': row['id'],
                                                     'sha256': fingerprint(subject), 'path': path},
                                         'scope': inputs['scope']}}


def check_stage_governance(runtime: dict | None,stage: str,value: dict,products: dict,
                           sources: list[dict],context: dict) -> dict | None:
    if runtime is None:return None
    inputs=stage_governance_inputs(stage,value,products,sources,context)
    current_rules=context.get('verified_dynamic_rules',{}).get(stage,{})
    result=evaluate_governance(runtime['contract'],inputs,current_rules=current_rules)
    if stage == 'type_adaptation' and context.get('dynamic_reference_checks'):
        actual = list(_check_adaptation_references(value, inputs, current_rules))
        result['checks'].extend(actual)
        if any(check['status']=='failed' for check in actual):
            result['status']='failed'
        elif actual and result['status']=='not_applicable':
            result['status']='pass'
    for issue in inputs['source_version_issues']:
        result['checks'].append({'requirement_key':'source_schema_version:'+issue['source_id'],
            'rule_id':'source_schema_version','status':'waiting','findings':[issue['reason']],
            'source_binding':issue})
        if result['status']!='failed':result['status']='waiting'
    if stage=='type_selection' and isinstance(inputs.get('project_config'),dict):
        config=inputs['project_config'];actual={r['id'] for r in value.get('selection',[])}
        configured=[v for k in CONFIG for v in (config[k] if isinstance(config.get(k),list) else [])]
        if set(config)!=set(CONFIG) or set(configured)!=actual or len(set(configured))!=len(configured):
            result['checks'].append({'requirement_key':'configuration_binding','rule_id':'configuration_binding',
                'status':'failed','findings':['配置必须逐一绑定本步实际选择的ID，不得漏项或重复分类']})
            result['status']='failed'
    result['summary']=dict(Counter(r['status'] for r in result['checks']))
    return result


def freeze_report(report: dict | None) -> dict | None:
    if report is None:return None
    return {'contract_fingerprint':report['contract_fingerprint'],'status':report['status'],
        'summary':report['summary'],'input_sha256':fingerprint(report['input_snapshot']),
        'result_sha256':fingerprint(report),
        'pending_requirements':sorted({r['requirement_key'] for r in report['checks'] if r['status'] in ('waiting','failed')})}


def verify_stage_governance(runtime: dict | None,saved: dict | None,stage: str,value: dict,products: dict,
                            sources: list[dict],context: dict) -> dict | None:
    current=check_stage_governance(runtime,stage,value,products,sources,context)
    if freeze_report(current)!=saved:
        raise ValueError('MATERIAL_GOVERNANCE: frozen inputs/results changed or governance was omitted')
    if current and current['status']=='failed':
        raise ValueError('MATERIAL_GOVERNANCE: actual design violates source governance')
    return current


def require_governance_clear(report: dict | None) -> None:
    if report and report['status'] in ('failed','waiting'):
        pending=[r['rule_id'] for r in report['checks'] if r['status'] in ('failed','waiting')]
        raise ValueError('MATERIAL_GOVERNANCE: adoption requires resolved actual-scope checks: '+','.join(dict.fromkeys(pending)))


def verify_dynamic_registries(workspace: Path, by_stage: dict) -> dict[str, dict]:
    from nw.materials.dynamic_refs import current_rule_proofs

    return {stage: proof for stage, inputs in by_stage.items()
            if (proof := current_rule_proofs(workspace, inputs))}


def verify_session_governance(session: dict,workspace: Path,*,adopting: bool=False) -> None:
    runtime=load_governance(workspace)
    if runtime!=session.get('governance'):
        raise ValueError('MATERIAL_GOVERNANCE: source policies/dependencies changed or were removed')
    context = session['context']
    if screening := context.get('dynamic_screening'):
        from nw.materials.dynamic_screening import load_dynamic_screening

        if screening != load_dynamic_screening(workspace):
            raise ValueError('MATERIAL_GOVERNANCE: TDF_001 source evidence changed')
    if ('verified_dynamic_rules' in context and context['verified_dynamic_rules']
            != verify_dynamic_registries(workspace, context.get('governance_inputs', {}))):
        raise ValueError('MATERIAL_GOVERNANCE: pinned dynamic rule evidence changed')
    products={};pool={s['source']['id']:s for s in session['sources']}
    for record in session['stages']:
        report=verify_stage_governance(runtime,record.get('governance'),record['stage'],record['products'],
            products,[pool[i] for i in record['source_ids']],context)
        if adopting:require_governance_clear(report)
        products[record['stage']]=record
