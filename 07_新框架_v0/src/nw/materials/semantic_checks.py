"""Project per-clause applications into independent current-scene checks."""
from copy import deepcopy

from nw.materials.binding_reviews import model_review
from nw.materials.phase_lifecycle import CANDIDATE_SELECTION, writing_sources
from nw.materials.phase_routes import product_ref
from nw.materials.phase_context import visible_facts
from nw.materials.semantic_application import (contracts_for, output_value, pointer_tokens,
    input_value,require, resolve_pointer, unresolved_issues, validate_semantic_applications)
from nw.task_models import canonical, content_sha256
import json


def _merge_clauses(rows: list[dict]) -> list[dict]:
    """One original clause is reviewed once with all current-scene applications."""
    result=[];groups={}
    for row in rows:
        field=row['source_contract']['obligations'][0]
        key=(field['source_id'],field['id'],row['source_applicability'])
        if key not in groups:
            groups[key]=row;result.append(row);continue
        target=groups[key]
        if 'applications' not in target['method_artifact']:
            target['method_artifact']={'applications':[target['method_artifact']]}
        target['method_artifact']['applications'].append(row['method_artifact'])
        for name in ('observable','check'):
            body=json.loads(target['binding'][name]);incoming=json.loads(row['binding'][name])
            if 'applications' not in body:body={'applications':[body]}
            body['applications'].append(incoming);target['binding'][name]=canonical(body)
        if 'layer_contract' in row:
            if 'layer_contract' not in target:target['layer_contract']=row['layer_contract']
            else:target['layer_contract'].setdefault('additional_project_applications',[]).append(
                row['layer_contract']['layer_application'])
    return result


def _mapped(value: object, ids: dict) -> object:
    if isinstance(value, str): return ids.get(value, value)
    if isinstance(value, list): return [_mapped(v, ids) for v in value]
    if isinstance(value, dict): return {ids.get(k, k): _mapped(v, ids) for k, v in value.items()}
    return value


def _same_scene(value: object, scene: str, ids: dict) -> bool:
    return isinstance(value, str) and ids.get(value, value) == ids.get(scene, scene)


def _selected(stage: str, records: dict, scene: str, ids: dict) -> set[str] | None:
    if stage not in CANDIDATE_SELECTION:
        return None
    consumer, field, key, _ = CANDIDATE_SELECTION[stage]
    body = records.get(consumer, {}).get('products', {})
    return {row[key] for row in body.get(field, []) if _same_scene(row['scene'], scene, ids)}


def _scene_row(value: object, scene: str, ids: dict) -> bool:
    if not isinstance(value, dict):
        return True
    if 'scene' in value:
        return _same_scene(value['scene'], scene, ids)
    if value.get('kind') == 'scene':
        return _same_scene(value.get('key'), scene, ids)
    return True


def _chapter_output(products: dict, reference: str, tokens: list[str], scene: str, ids: dict) -> object:
    chapters = products['chapters']
    indices = range(len(chapters)) if len(tokens) == 1 else (int(tokens[1]),)
    scoped = []
    for index in indices:
        chapter = chapters[index]
        scenes = [row for row in chapter['scenes'] if _same_scene(row['card'], scene, ids)]
        if not scenes:
            continue
        if len(tokens) <= 2:
            scoped.append({**chapter, 'scenes': scenes})
        elif tokens[2:] == ['scenes']:
            return scenes
        elif tokens[2] != 'scenes' or _same_scene(chapter['scenes'][int(tokens[3])]['card'], scene, ids):
            return resolve_pointer(products, reference)
    if not scoped:
        return None
    return scoped if len(tokens) == 1 else scoped[0]


def current_scene_outputs(stage: str, products: dict, references: list[str], records: dict,
                          scene: str, ids: dict) -> list[dict]:
    result = []; selected = _selected(stage, records, scene, ids)
    for reference in references:
        tokens = pointer_tokens(reference)
        if stage == 'scene_design' and tokens[0] == 'chapters':
            current = _chapter_output(products, reference, tokens, scene, ids)
            if current is not None:
                result.append({'path': reference, 'value': _mapped(current, ids)})
            continue
        current: object = products
        for token in tokens:
            if isinstance(current, dict):
                current = current.get(token)
            elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
                current = current[int(token)]
            else:
                current = None
                break
            if not _scene_row(current, scene, ids):
                current = None
                break
        if isinstance(current, list):
            current = [row for row in current if _scene_row(row, scene, ids)] or None
        if selected is not None and tokens[0] == 'candidates':
            if tokens == ['candidates']:
                current = [row for row in current or [] if row['id'] in selected] or None
            elif products['candidates'][int(tokens[1])]['id'] not in selected:
                current = None
        if current is not None:
            result.append({'path': reference, 'value': _mapped(current, ids)})
    return result


def _layer(contract: dict, criterion: dict) -> dict:
    return {'policy': 'source-semantics-layer-v1', 'source_ref': deepcopy(contract.get('source_ref', {})),
            'source_text_sha256': contract['source_text_sha256'], 'contract_sha256': contract['sha256'],
            'execution': {'authority': 'current_project_translation_requires_independent_review'},
            'application_guidance': deepcopy(contract.get('application_guidance', [])),
            'layer_application': deepcopy(criterion['layer_application'])}


def make_semantic_checks(session: dict, scene: str, ids: dict | None = None) -> list[dict]:
    """Emit obligations, not pass statuses or automatic WORLD state changes."""
    ids = ids or {}; records = {row['stage']: row for row in session.get('stages', [])}
    sources = {row['source']['id']: row for row in session.get('sources', [])}
    context = deepcopy(session.get('context', {}))
    if 'semantic_contracts' in session: context['semantic_contracts'] = session['semantic_contracts']
    guides = [g for g in records.get('bind_scope', {}).get('products', {}).get('method_guidance', [])
              if _same_scene(g.get('scene'), scene, ids)]
    placed = {ident for guide in guides for ident in guide.get('source_ids', [])}
    active = writing_sources(records, []) & placed
    result = []; upstream = {};layer_checked=set();review_attached=set()
    for record in session.get('stages', []):
        stage = record['stage']; value = record['products']; product_ref(record)
        if '_criteria' not in value and not value.get('_uses'):
            upstream[stage] = record; continue
        step_context = {**context, **({'semantic_contracts': record['semantic_contracts']}
                                      if 'semantic_contracts' in record else {})}
        step_context['accepted_state']=visible_facts(stage,upstream,context)
        if 'inputs' in record:step_context['allowed_input_stages']=[r['stage'] for r in record['inputs']]
        step_sources=[sources[i] for i in record.get('source_ids',list(sources))]
        contracts = contracts_for(step_sources, step_context)
        validate_semantic_applications(stage, value, upstream, step_sources, step_context)
        for criterion in value.get('_criteria', []):
            ident = criterion['source_id']
            if ident not in active: continue
            contract = contracts[ident]; original = {o['id']: o for o in contract['obligations']}
            review = context.get('binding_reviews', {}).get(ident)
            reference_only = set()
            if review:
                reference_only = {row['id'] for row in model_review(review, contract, stage)['clause_decisions']
                                  if row['status'] == 'not_project_instruction'}
            for application in criterion['clauses']:
                field = original[application['id']]; mode = application['applicability']
                if mode == 'not_applicable' and field['id'] in reference_only:
                    continue
                outputs = current_scene_outputs(stage, value, application['output_refs'], records, scene, ids)
                if mode == 'applies' and not outputs: continue
                obligation = {'id': field['id'], 'text': field['value'] if isinstance(field['value'], str) else canonical(field['value']),
                              'kind': field['kind'], 'ref': deepcopy(field['source_ref']), 'source_id': ident}
                pending = unresolved_issues(contract, field['id'], review)
                scope = {'disposition': 'not_applicable' if mode in ('not_applicable','source_unresolved') else 'required',
                         'reason': application['reason']}
                if mode == 'applies':
                    visible = {'observable': application['observable'], 'actual_outputs': outputs}
                    check = {'criterion': application['check'], 'consumer': application['consumer'],
                             'verification': 'independent_prose_review_required'}
                else:
                    visible = {'applicability': mode, 'reason': application['reason'],
                               'source_issues': deepcopy(pending)}
                    check = {'consumer': application['consumer'], 'source_resolution': mode,
                             'verification': 'unverified_source_cannot_count_as_completed' if mode == 'source_unresolved'
                                             else 'verify_current_task_nonapplicability_without_claiming_source_repair'}
                proof = {'stage': stage, 'product_ref': product_ref(record),
                         'application': deepcopy(application), 'layer_application': deepcopy(criterion['layer_application']),
                         'actual_inputs':[{'path':ref,'value':_mapped(deepcopy(input_value(
                             ref,stage,upstream,step_context)),ids)} for ref in application['input_refs']],
                         'current_outputs': outputs, 'source_issues': deepcopy(pending)}
                if review:
                    proof['binding_review_sha256']=review['sha256']
                    if ident not in review_attached:
                        applied={r['stage'] for r in session['stages']
                            if any(u['source_id']==ident for u in r['products'].get('_uses',[]))}
                        proof['reviewed_use']={'review_sha256':review['sha256'],
                            'uses':[u for u in review['uses'] if u['stage'] in applied],
                            'effect_status':'not_verified_by_binding_review'}
                        review_attached.add(ident)
                key = {'session': session.get('id'), 'stage': stage, 'source_id': ident, 'clause_id': field['id'], 'scene': scene}
                row = {'id': 'work:semantic:' + content_sha256(key), 'profile': 'method_work' if mode=='applies' else 'prose_review',
                       'binding': {'observable': canonical(visible), 'check': canonical(check),
                                   'source_scope': {field['id']: scope}},
                       'source_contract': {'obligations': [obligation]},
                       'method_sources': [{'source': deepcopy(sources[ident]['source']),
                           'original_quotes': [obligation['text']],
                           'source_text_sha256': contract['source_text_sha256'],
                           'semantic_contract_ref':contract['sha256']}],
                       'method_operation': application['operation'], 'method_artifact': proof,
                       'source_applicability': mode,
                       'evidence_required': '逐条对照原义、真实输入和阶段产物核验本稿效果；计划、关键词和已读取不能通过。'
                           + ('原义缺项仍为未验证，不得补造或计为完成。' if mode == 'source_unresolved' else '')}
                if (stage,ident) not in layer_checked and (contract.get('application_guidance') or sources[ident].get('application_layers')):
                    row['layer_contract'] = _layer(contract, criterion)
                    layer_checked.add((stage,ident))
                result.append(row)
        upstream[stage] = record
    return _merge_clauses(result)
