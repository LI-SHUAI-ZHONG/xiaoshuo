"""Rule-specific proof at the adopted field, its actual action and the final scene result."""
import re

from nw.materials.commitment_semantics import KEYS as COMMITMENTS
from nw.materials.design_network_catalog import POLICY
from nw.materials.energy_semantics import RULES as ENERGY
from nw.models import Draft
from nw.materials.semantic_application import output_value, pointer_tokens, require

SPECIAL_WORLD = {'C00738', *ENERGY}
RULES = SPECIAL_WORLD | COMMITMENTS | {'C00025'}
DIRECTION_FIELDS = ('conflict', 'resistance', 'choice', 'cost', 'consequence', 'ending_direction')


def _handler(key: str):
    if key == 'C00738':
        from nw.materials import authority_semantics as module
    elif key in ENERGY:
        from nw.materials import energy_semantics as module
    elif key in COMMITMENTS:
        from nw.materials import commitment_semantics as module
    elif key == 'C00025':
        from nw.materials import action_consumption as module
    else:
        raise ValueError('unknown design rule: ' + key)
    return module


def world_eligible(key: str, rule: str, limit: str, body: dict) -> bool:
    return _handler(key).eligible(key, rule, limit, full_rule=body['rule'], full_limits=body['limits'])


def prepare(row: dict, match: dict) -> bool:
    if row['key'] in COMMITMENTS:
        if not match.get('commitment'):
            return False
        row['commitment'] = match['commitment']
    if row['key'] == 'C00025':
        from nw.materials.action_consumption import basis
        ability_limits = [e['value'] for e in row['evidence'] if '/capabilities/' in e['ref'] and '/limits/' in e['ref']]
        budget = basis(*row['excerpts'], row['ability'], '。'.join(ability_limits))
        if not budget:
            return False
        row['consumption'] = budget
    row['semantic_policy'] = POLICY
    return True


def verify_retained(row: dict) -> None:
    key = row['key']
    if key in SPECIAL_WORLD:
        rule, limit = row['excerpts']
        body = {kind: next((e['value'] for e in row['evidence'] if e['ref'].endswith('/body/' + kind)), '')
                for kind in ('rule', 'limits')}
        require(world_eligible(key, rule, limit, body), key + ' 已选父纲的世界规则缺少可复核的前置，请补该项设计')
        for receipt in row['deliveries']:
            verify_receipt(row, receipt)
        row['semantic_policy'] = POLICY


def validate_use(row: dict, text: str, *, operation: str, stage: str) -> None:
    _handler(row['key']).validate_use(row, text, operation=operation, stage=stage)


def _check(row: dict, values, stage: str) -> None:
    handler = _handler(row['key'])
    for text in dict.fromkeys(t for t in values if isinstance(t, str) and t):
        handler.check_conflict(row, text, stage=stage)


def writing_check(row: dict) -> str:
    check = row['check']
    if row.get('semantic_policy') != POLICY:
        return check
    if promise := row.get('commitment'):
        labels = {'actor': '承诺人', 'promisee': '向谁承诺', 'beneficiary': '受益者', 'action': '行动', 'subject': '事项', 'trigger': '触发或期限'}
        return check + '。' + '，'.join(label + '为' + str(promise[k]) for k, label in labels.items() if promise.get(k))
    rule, limit = row['excerpts']
    if row['key'] == 'C00738':
        from nw.materials.authority_semantics import project_limit
        limit = project_limit(row)
    description = check + '。本场采用的规则为' + rule + '。适用限制为' + limit
    if budget := row.get('consumption'):
        bound = '须低于' if budget['exclusive'] else '不得超过'
        description += f"。本次{row['ability']}的用量按每{budget['time_unit']}{budget['cost']}{budget['cost_unit']}计算，时长{bound}{budget['maximum']}{budget['time_unit']}。"
    return description


def check_review_evidence(rule: dict, spans: list[dict], draft: Draft) -> None:
    artifact = rule.get('method_artifact', {})
    if artifact.get('semantic_policy') != POLICY:
        return
    row = {**artifact, 'key': rule['network_design_key'], 'evidence': artifact['prerequisites']}
    # Check the narrator's observable facts in source order. A character's quoted
    # boast or an unfulfilled promise cannot establish a second, contradictory fact.
    quotes = [re.sub(r'“[^”]*”|「[^」]*」|‘[^’]*’|"[^"]*"', '', s['quote'])
              for s in sorted(spans, key=lambda s: s['start']) if s['id'] == draft.id]
    text = _sequence(*quotes)
    try:
        handler = _handler(row['key'])
        handler.check_conflict(row, text, stage='review')
        if row['key'] == 'C00025':
            handler.check_narrated_action(row, draft.text)
    except ValueError as error:
        raise ValueError('MATERIAL_EVIDENCE: 所引正文与本场采用的前置冲突，须重新审稿。' + str(error)) from error


def _action_fields(action: dict):
    yield from (action.get('action'), action.get('cost'))
    for step in action.get('steps', []):
        yield from (step.get('action'), step.get('response'), step.get('result'))


def _sequence(*parts: str | None) -> str:
    return '。'.join(t for t in parts if isinstance(t, str) and t)


def aftermath_field(key: str) -> str | None:
    if key in COMMITMENTS:
        return 'commitment_aftermath'
    if key == 'C00738':
        return 'authority_aftermath'
    return None


def verify_receipt(row: dict, receipt: dict) -> None:
    field = aftermath_field(row['key'])
    if field and field in receipt:
        row = {**row, field: receipt[field]}
    validate_use(row, receipt['value'], operation=receipt.get('operation', ''), stage='plot_design')
    outcomes = receipt.get('legacy_outcomes', [])
    _check(row, [*outcomes, _sequence(*outcomes)], 'plot_design')


def with_aftermath(row: dict, stage: str, value: dict, index: int) -> dict:
    field = aftermath_field(row['key'])
    if not field:
        return row
    if stage == 'scene_design':
        aftermath = value['members'][index]['body'].get('planned_result')
    elif stage == 'plot_design':
        direction = value['directions'][index]
        aftermath = _sequence(direction.get('consequence'), direction.get('cost'))
    elif stage == 'action_design':
        action = value['candidates'][index]
        aftermath = _sequence(action.get('cost'), *(s.get('result') for s in action.get('steps', [])))
    else:
        return row
    return {**row, field: aftermath}


def _relevant_action(row: dict, action: dict) -> bool:
    if row.get('ability'):
        return (row['actor'] == action.get('actor') and row['event'] == action.get('event')
                and row['ability'] in action.get('requires', []))
    return row['owner'] != 'character_design' or row['member'] == action.get('actor')


def check_product(row: dict, stage: str, value: dict, index: int, products: dict) -> None:
    if stage == 'plot_design':
        direction = value['directions'][index]
        fields = [direction.get(k) for k in DIRECTION_FIELDS]
        fields.append(_sequence(*fields))
    elif stage == 'action_design':
        fields = list(_action_fields(value['candidates'][index]))
    elif stage == 'scene_design':
        scene = value['members'][index]
        body = scene['body']
        fields = [body.get(k) for k in ('choice', 'planned_result')]
        fields.append(_sequence(body.get('entering_state'), body.get('conflict'), *fields))
        selected = {r['action'] for r in value.get('selected_actions', []) if r['scene'] == scene['key']}
        if products:
            for action in products.get('action_design', {}).get('products', {}).get('candidates', []):
                if action['id'] in selected and _relevant_action(row, action):
                    fields.extend(_action_fields(action))
                    fields.append(_sequence(body.get('conflict'), action.get('action'), body.get('planned_result')))
    else:
        return
    _check(row, fields, stage)


def scene_constraints(products: dict) -> dict[str, list[dict]]:
    record = products.get('scene_design', {})
    value = record.get('products', {})
    offered = {r['id']: r for r in record.get('network_design_candidates', []) if r.get('semantic_policy') == POLICY}
    by_scene = {}
    for use in value.get('_network_design_uses', []):
        if row := offered.get(use['id']):
            for path in use['output_refs']:
                scene = value['members'][int(pointer_tokens(path)[1])]['key']
                placed = by_scene.setdefault(scene, {}).setdefault(row['id'], {**row, 'scene_fields': []})
                placed['scene_fields'].append({'path': path, 'value': output_value(path, value)})
    return {scene: list(rows.values()) for scene, rows in by_scene.items()}


def check_patches(value: dict, products: dict) -> None:
    by_scene = scene_constraints(products)
    if not by_scene:
        return
    design = products['scene_design']['products']
    scenes = {m['key']: m['body'] for m in design['members']}
    actions = {a['id']: a for a in products.get('action_design', {}).get('products', {}).get('candidates', [])}
    for patch in value.get('patches', []):
        key = patch['scene']
        for row in by_scene.get(key, []):
            body = scenes[key]
            selected = [actions[s['action']]['action'] for s in design.get('selected_actions', [])
                        if s['scene'] == key and s['action'] in actions and _relevant_action(row, actions[s['action']])]
            placements = [item['value'] for item in row['scene_fields']]
            actual = _sequence(body.get('entering_state'), body.get('conflict'), *placements,
                               *selected, patch['choice'], patch['planned_result'])
            if field := aftermath_field(row['key']):
                row = {**row, field: patch['planned_result']}
            _check(row, (patch['choice'], patch['planned_result'], actual), 'state_transition')
    for change in value.get('transitions', []):
        for row in by_scene.get(change['scene'], []):
            subject = row.get('actor') or (row['member'] if row['owner'] == 'character_design' else None)
            if subject and subject != change.get('entity'):
                continue
            if field := aftermath_field(row['key']):
                row = {**row, field: _sequence(change.get('cost'), change.get('continuity'))}
            _check(row, (change.get('action'), change.get('cost'), change.get('continuity')), 'state_transition')
