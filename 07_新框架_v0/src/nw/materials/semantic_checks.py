"""Project per-clause applications into independent current-scene checks."""
from copy import deepcopy

from nw.materials.binding_reviews import model_review
from nw.materials.phase_lifecycle import CANDIDATE_SELECTION, writing_sources
from nw.materials.phase_routes import product_ref
from nw.materials.phase_context import visible_facts
from nw.materials.scene_actions import MULTI_ACTION_POLICY, selected_action_ids
from nw.materials.semantic_application import (contracts_for, output_value, pointer_tokens,
    input_value,require, resolve_pointer, unresolved_issues, validate_semantic_applications)
from nw.task_models import canonical, content_sha256
import json


def _merge_clauses(rows: list[dict]) -> list[dict]:
    """Review each original clause once for a scene or for an individual action."""
    result=[];groups={}
    for row in rows:
        field=row['source_contract']['obligations'][0]
        key=(field['source_id'],field['id'],row['source_applicability'],row.get('action_ref'))
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
                          scene: str, ids: dict, *, action_ref: str | None = None) -> list[dict]:
    result = []; selected = _selected(stage, records, scene, ids)
    if stage == 'action_design' and action_ref is not None and selected is not None:
        selected &= {action_ref}
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
        if stage == 'anchor_design' and tokens[0] == 'beats' and action_ref is not None:
            if tokens == ['beats']:
                current = [row for row in current or [] if row.get('action_ref') == action_ref] or None
            elif current is not None and products['beats'][int(tokens[1])].get('action_ref') != action_ref:
                current = None
        if current is not None:
            result.append({'path': reference, 'value': _mapped(current, ids)})
    return result


def _output_groups(stage: str, products: dict, references: list[str], records: dict,
                   scene: str, ids: dict, actions: list[str]) -> list[tuple[str | None, list[dict]]]:
    field = {'action_design': 'candidates', 'anchor_design': 'beats'}.get(stage)
    if field is None or len(actions) < 2:
        return [(None, current_scene_outputs(stage, products, references, records, scene, ids))]
    action_paths = [ref for ref in references if pointer_tokens(ref)[0] == field]
    general_paths = [ref for ref in references if ref not in action_paths]
    groups = [(None, current_scene_outputs(stage, products, general_paths, records, scene, ids))]
    groups.extend((action, current_scene_outputs(stage, products, action_paths, records, scene, ids, action_ref=action))
                  for action in actions)
    return groups


def _layer(contract: dict, criterion: dict) -> dict:
    return {'policy': 'source-semantics-layer-v1', 'source_ref': deepcopy(contract.get('source_ref', {})),
            'source_text_sha256': contract['source_text_sha256'], 'contract_sha256': contract['sha256'],
            'execution': {'authority': 'current_project_translation_requires_independent_review'},
            'application_guidance': deepcopy(contract.get('application_guidance', [])),
            'layer_application': deepcopy(criterion['layer_application'])}


def _layer_field_checks(session_id: str, record: dict, source: dict, contract: dict, criterion: dict,
                        records: dict, upstream: dict, context: dict, scene: str, ids: dict) -> list[dict]:
    stage, value = record['stage'], record['products']
    clauses = {row['id']: row for row in criterion['clauses']}
    obligations = {row['id']: row for row in contract['obligations']}
    chosen = selected_action_ids(records.get('scene_design', {}).get('products', {}))
    selected = next((refs for key, refs in chosen.items() if _same_scene(key, scene, ids)), [])
    checks = []
    for use in criterion['layer_application']['bindings']:
        result_path = use['result_ref']
        outputs = current_scene_outputs(stage, value, [result_path], records, scene, ids)
        if not outputs:
            continue
        field, *tokens = pointer_tokens(result_path)
        action_ref = None
        if stage == 'action_design' and field == 'candidates':
            action_ref = value[field][int(tokens[0])]['id']
        elif stage == 'anchor_design' and field == 'beats':
            action_ref = value[field][int(tokens[0])].get('action_ref')
            if action_ref is not None and action_ref not in selected:
                continue
        action = {'action_ref': action_ref} if action_ref is not None else {}
        clause = clauses[use['clause_id']]
        original = obligations[use['clause_id']]
        trigger = {'path': use['trigger_ref'], 'value': _mapped(deepcopy(input_value(
            use['trigger_ref'], stage, upstream, context)), ids)}
        application = {'trigger': trigger, 'operation': clause['operation'], 'result': outputs[0],
                       'verification': clause['check']}
        layer = _layer(contract, {'layer_application': application})
        layer['policy'] = context['network_layer_policy']
        layer['original_clause'] = deepcopy(original)
        visible = {'observable': clause['observable'], 'result_path': result_path, **action}
        if stage == 'anchor_design' and field == 'beats' and tokens[1:] == ['observable']:
            visible['visible_result'] = outputs[0]['value']
        key = {'session': session_id, 'stage': stage, 'source_id': criterion['source_id'], 'scene': scene,
               'clause_id': use['clause_id'], 'result_ref': result_path}
        checks.append({'id': 'work:layer:' + content_sha256(key), 'profile': 'method_work', **action,
            'binding': {'observable': canonical(visible),
                        'check': canonical({'criterion': clause['check'], **action})},
            'layer_contract': layer,
            'method_sources': [{'source': deepcopy(source['source']),
                                'original_quotes': [original['value']] if isinstance(original['value'], str)
                                                    else [canonical(original['value'])],
                                'source_text_sha256': contract['source_text_sha256'],
                                'semantic_contract_ref': contract['sha256']}],
            'method_operation': clause['operation'],
            'method_artifact': {'stage': stage, 'product_ref': product_ref(record),
                                'clause_id': use['clause_id'], **action},
            'evidence_required': '独立核对这处产物对应的触发、操作、结果和可见效果，引用当前正文具体段落。'})
    return checks


def make_semantic_checks(session: dict, scene: str, ids: dict | None = None) -> list[dict]:
    """Emit obligations, not pass statuses or automatic WORLD state changes."""
    from nw.materials.network_followup import BASIS_STAGE, basis_inputs
    from nw.materials.network_layers import uses_fields

    ids = ids or {}; records = {row['stage']: row for row in session.get('stages', [])}
    sources = {row['source']['id']: row for row in session.get('sources', [])}
    context = deepcopy(session.get('context', {}))
    actions = []
    if context.get('multi_action_policy') == MULTI_ACTION_POLICY:
        scene_product = records.get('scene_design', {}).get('products', {})
        actions = next((refs for key, refs in selected_action_ids(scene_product).items() if _same_scene(key, scene, ids)), [])
    if 'semantic_contracts' in session: context['semantic_contracts'] = session['semantic_contracts']
    guides = [g for g in records.get('bind_scope', {}).get('products', {}).get('method_guidance', [])
              if _same_scene(g.get('scene'), scene, ids)]
    placed = {ident for guide in guides for ident in guide.get('source_ids', [])}
    active = writing_sources(records, []) & placed
    result = []; layer_fields = []; upstream = {};layer_checked=set();review_attached=set()
    for record in session.get('stages', []):
        stage = record['stage']; value = record['products']; product_ref(record)
        if '_criteria' not in value and not value.get('_uses'):
            upstream[stage] = record; continue
        step_context = {**context, **({'semantic_contracts': record['semantic_contracts']}
                                      if 'semantic_contracts' in record else {})}
        step_context['accepted_state']=visible_facts(stage,upstream,context)
        if 'inputs' in record:step_context['allowed_input_stages']=[r['stage'] for r in record['inputs']]
        step_upstream = upstream
        if basis := record.get('static_relations_basis'):
            step_upstream = basis_inputs(upstream, basis)
            step_context['allowed_input_stages'] = [*step_context['allowed_input_stages'], BASIS_STAGE]
        step_sources=[sources[i] for i in record.get('source_ids',list(sources))]
        contracts = contracts_for(step_sources, step_context)
        validate_semantic_applications(stage, value, step_upstream, step_sources, step_context)
        for criterion in value.get('_criteria', []):
            ident = criterion['source_id']
            if ident not in active: continue
            contract = contracts[ident]; original = {o['id']: o for o in contract['obligations']}
            structured = uses_fields(sources[ident], contract, context)
            if structured:
                layer_fields.extend(_layer_field_checks(session.get('id'), record, sources[ident], contract, criterion,
                                                        records, step_upstream, step_context, scene, ids))
            review = context.get('binding_reviews', {}).get(ident)
            reference_only = set()
            if review:
                reference_only = {row['id'] for row in model_review(review, contract, stage)['clause_decisions']
                                  if row['status'] == 'not_project_instruction'}
            for application in criterion['clauses']:
                field = original[application['id']]; mode = application['applicability']
                if mode == 'not_applicable' and field['id'] in reference_only:
                    continue
                groups = _output_groups(stage, value, application['output_refs'], records, scene, ids,
                                        actions if mode == 'applies' else [])
                obligation = {'id': field['id'], 'text': field['value'] if isinstance(field['value'], str) else canonical(field['value']),
                              'kind': field['kind'], 'ref': deepcopy(field['source_ref']), 'source_id': ident}
                pending = unresolved_issues(contract, field['id'], review)
                scope = {'disposition': 'not_applicable' if mode in ('not_applicable','source_unresolved') else 'required',
                         'reason': application['reason']}
                for action_ref, outputs in groups:
                    if mode == 'applies' and not outputs:
                        continue
                    if mode == 'applies':
                        visible = {'observable': application['observable'],
                                   'actual_outputs': [{'path': output['path']} for output in outputs] if structured else outputs}
                        check = {'criterion': application['check'], 'consumer': application['consumer'],
                                 'verification': 'independent_prose_review_required'}
                    else:
                        visible = {'applicability': mode, 'reason': application['reason'],
                                   'source_issues': deepcopy(pending)}
                        check = {'consumer': application['consumer'], 'source_resolution': mode,
                                 'verification': 'unverified_source_cannot_count_as_completed' if mode == 'source_unresolved'
                                                 else 'verify_current_task_nonapplicability_without_claiming_source_repair'}
                    proof = {'stage': stage, 'product_ref': product_ref(record),
                             'application': deepcopy(application),
                             **({} if structured else {'layer_application': deepcopy(criterion['layer_application'])}),
                             'actual_inputs':[{'path':ref,'value':_mapped(deepcopy(input_value(
                                 ref,stage,step_upstream,step_context)),ids)} for ref in application['input_refs']],
                             'current_outputs': outputs, 'source_issues': deepcopy(pending)}
                    key = {'session': session.get('id'), 'stage': stage, 'source_id': ident, 'clause_id': field['id'], 'scene': scene}
                    if action_ref is not None:
                        key['action_ref'] = proof['action_ref'] = visible['action_ref'] = check['action_ref'] = action_ref
                        proof['application']['output_refs'] = [output['path'] for output in outputs]
                    if review:
                        proof['binding_review_sha256']=review['sha256']
                        if (ident, action_ref) not in review_attached:
                            applied={r['stage'] for r in session['stages']
                                if any(u['source_id']==ident for u in r['products'].get('_uses',[]))}
                            proof['reviewed_use']={'review_sha256':review['sha256'],
                                'uses':[u for u in review['uses'] if u['stage'] in applied],
                                'effect_status':'not_verified_by_binding_review'}
                            review_attached.add((ident, action_ref))
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
                    if action_ref is not None:
                        row['action_ref'] = action_ref
                    if (not structured and (stage, ident, action_ref) not in layer_checked
                            and (contract.get('application_guidance') or sources[ident].get('application_layers'))):
                        row['layer_contract'] = _layer(contract, criterion)
                        layer_checked.add((stage, ident, action_ref))
                    result.append(row)
        upstream[stage] = record
    return _merge_clauses(result) + layer_fields
