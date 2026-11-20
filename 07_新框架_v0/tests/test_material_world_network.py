"""Verify the three world formula uses against pinned projects and exact outputs."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from nw.materials.semantic_handoff import handoffs_for, validate_handoffs
from nw.materials.world_network import POLICY, RULES, availability, validate_world_network_use
from nw.task_models import content_sha256


LIMITS = '仅限验标后的衡灵装置，不适用于治疗术。'
RULE = ('本作力量公式 P=E×Q×T。总量 E 以灵值计，范围为 0 至 100 灵值。'
        '纯度 Q 以百分比计，只比较同批材料。技巧 T 按四级标准计分。')
RULE_PATH = 'approved:power:/body/rule'
LIMITS_PATH = 'approved:power:/body/limits'
TYPE_PATH = 'input:type_selection:/selection/0/basis'


def _record(stage: str, products: dict) -> dict:
    return {'stage': stage, 'task_id': stage, 'products': products, 'sha256': content_sha256(products)}


def _world(rule: str = RULE, limits: str = LIMITS, **override) -> dict:
    return {'kind': 'world', 'card_id': 'power', 'version': 2, 'status': 'approved',
            'body': {'title': '衡灵力量公式', 'rule': rule, 'limits': limits}, **override}


def _case(key: str = 'C00029') -> tuple[dict, dict, dict, dict, dict]:
    factor, _ = RULES[key]
    index = dict(C00029=1, C00034=2, C00039=3)[key]
    edge = {'source': f'10.{index}_{factor}', 'target': '10.5_力量公式', 'type': '嵌套',
            'condition': f'{factor}是公式变量'}
    raw = {**edge, 'id': key, 'generated_from_static': True,
           'condition': edge['condition'] + '；且当前故事明确采用该静态关系', 'valid_types': ['悬疑']}
    source = {'source': {'id': 'dynamic-demo', 'key': key}, 'related_sources': ['static-demo']}
    products = {'type_selection': _record('type_selection', {
        'selection': [{'id': 'GENRE_XUANYI', 'basis': '按正式立项悬疑类型选定'}],
    })}
    context = {'world_network_policy': POLICY, 'scope': 'book', 'network_type_scope': {'GENRE_XUANYI': ['悬疑']},
               'approved_cards': [_world()], 'world_network_bases': {
                   'dynamic-demo': {'static_id': 'static-demo', 'edge': edge,
                                    'source': {'id': 'static-demo', 'profile': 'static_relation',
                                               'path': '静态网络.txt', 'sha256': 'row', 'file_sha256': 'file'}},
               }}
    value = {'members': [{'key': 'power-design', 'kind': 'world', 'body': {'rule': RULE, 'limits': LIMITS}}],
             '_uses': [{'source_id': 'dynamic-demo', 'output_refs': ['member:power-design']}],
             '_criteria': [{'source_id': 'dynamic-demo', 'contract_sha256': 'source-hash', 'clauses': [{
                 'id': 'clause', 'applicability': 'applies', 'consumer': 'plot_design',
                 'input_refs': [TYPE_PATH, RULE_PATH, LIMITS_PATH],
                 'output_refs': ['/members/0/body/rule', '/members/0/body/limits'],
             }]}]}
    return source, raw, value, products, context


@pytest.mark.parametrize(('key', 'symbol'), [('C00029', 'E'), ('C00034', 'Q'), ('C00039', 'T')])
def test_each_variable_adopts_actual_approved_formula_scale_limits_and_handoff(key: str, symbol: str) -> None:
    source, raw, value, products, context = _case(key)
    ready, missing = availability(key, raw['valid_types'], products, context)
    assert not missing and ready['type_ids'] == ['GENRE_XUANYI']
    [proof] = ready['cards']
    assert (proof['formula'], proof['variable'], proof['version']) == ('P=E×Q×T', symbol, 2)
    assert proof['definition'] in RULE and proof['limits'] == LIMITS
    validate_world_network_use(source, raw, value, products, context)

    [receipt] = handoffs_for('plot_design', {'world_design': _record('world_design', value)})
    assert [item['value'] for item in receipt['actual_inputs']] == [RULE, LIMITS]
    with pytest.raises(ValueError, match='disappeared at their named consumer'):
        validate_handoffs('plot_design', {}, {'world_design': _record('world_design', value)})


@pytest.mark.parametrize('rule', [
    '本作力量公式 P=E。总量 E，单位为灵值。',
    '力量评分 = 能量总量 × 纯度。能量总量按灵值计量。',
    '本作力量公式：P＝(Ｅ＋Q) ÷ 2.5。总量 E 以灵值计。',
])
def test_explicit_arithmetic_and_a_local_variable_measure_are_enough(rule: str) -> None:
    _, raw, _, products, context = _case()
    context['approved_cards'] = [_world(rule)]
    ready, missing = availability(raw['id'], raw['valid_types'], products, context)
    assert not missing and ready['cards']


@pytest.mark.parametrize('rule', [
    '本作力量公式 P=这是 E 的替代设计。总量 E 以灵值计。',
    '本作力量公式 P=这是E的替代设计。总量 E 以灵值计。',
    '本作力量公式 P=round(E×Q)。总量 E 以灵值计。',
    '本作力量公式 P=E×Q。总量 E 由装置显示，纯度 Q 以百分比计。',
    '本作力量公式 P=E×Q。总量 E 和纯度 Q 分别显示，单位为百分比。',
    '本作力量公式 P=Q×T。总量 E 以灵值计。',
    '本作且暂未采用力量公式 P=E×Q。总量 E 以灵值计。',
    '本作力量公式 P=E×Q。另有力量公式 P=E×T。总量 E 以灵值计。',
])
def test_missing_actual_formula_or_own_variable_scale_waits(rule: str) -> None:
    _, raw, _, products, context = _case()
    context['approved_cards'] = [_world(rule)]
    ready, missing = availability(raw['id'], raw['valid_types'], products, context)
    assert ready is None and '能量总量' in missing[0]


def test_authority_does_not_combine_cards_or_treat_new_world_output_as_an_input() -> None:
    _, raw, value, products, context = _case()
    context['approved_cards'] = [_world('力量公式 P=E×Q。'), _world('总量 E 以灵值计。', card_id='second'),
                                 _world(status='proposal', card_id='draft')]
    products['world_design'] = _record('world_design', value)
    ready, missing = availability(raw['id'], raw['valid_types'], products, context)
    assert ready is None and '已批准' in missing[0]


def test_explicit_exclusion_is_an_approved_scope_boundary() -> None:
    source, raw, value, products, context = _case()
    actual_limits = '只用于验标后的衡灵装置，治疗术不采用本公式。'
    context['approved_cards'][0]['body']['limits'] = actual_limits
    value['members'][0]['body']['limits'] = actual_limits
    validate_world_network_use(source, raw, value, products, context)


@pytest.mark.parametrize(('defect', 'message'), [
    ('foreign_static', 'same pinned static original'),
    ('wrong_type_ref', 'actually selected type'),
    ('wrong_card', 'one approved world card'),
    ('additional_card', 'cannot mix calculation cards'),
    ('future_stage', 'later stage in scope'),
    ('wrong_output', 'exact rule or limits field'),
    ('one_output', 'hand off both'),
    ('changed_formula', 'approved formula'),
    ('extra_formula', 'approved formula'),
    ('changed_scale', 'approved variable definition'),
    ('changed_limits', 'approved variable definition'),
])
def test_adoption_rejects_improper_reference_missing_output_and_changed_basis(defect: str, message: str) -> None:
    source, raw, value, products, context = _case()
    body = value['members'][0]['body']
    clause = value['_criteria'][0]['clauses'][0]
    if defect == 'foreign_static':
        context['world_network_bases']['dynamic-demo']['edge']['type'] = '驱动'
    elif defect == 'wrong_type_ref':
        clause['input_refs'][0] = 'input:type_selection:/selection/1/basis'
    elif defect == 'wrong_card':
        clause['input_refs'][2] = 'approved:other:/body/limits'
    elif defect == 'additional_card':
        context['approved_cards'].append(_world('另一项目的比较值另行认定。', card_id='other'))
        clause['input_refs'].append('approved:other:/body/rule')
    elif defect == 'future_stage':
        clause['consumer'] = 'action_design'
    elif defect == 'wrong_output':
        clause['output_refs'][1] = '/members/0/body/cost'
    elif defect == 'one_output':
        clause['output_refs'].pop()
    elif defect == 'changed_formula':
        body['rule'] = RULE.replace('P=E×Q×T', 'P=2×E×Q×T')
    elif defect == 'extra_formula':
        body['rule'] = RULE + '调整后 P=2×E×Q×T。'
    elif defect == 'changed_scale':
        body['rule'] = RULE.replace('100 灵值', '200 灵值')
    elif defect == 'changed_limits':
        body['limits'] = LIMITS + '此后也能用于治疗。'
    with pytest.raises(ValueError, match=message):
        validate_world_network_use(source, raw, value, products, context)


def test_actual_selected_type_and_legacy_policy_still_control_the_pool() -> None:
    _, raw, _, products, context = _case()
    unauthorized = deepcopy(context)
    unauthorized['network_type_scope'] = {'GENRE_XUANYI': ['二次元']}
    assert availability(raw['id'], raw['valid_types'], products, unauthorized)[0] is None
    del context['world_network_policy']
    assert availability(raw['id'], raw['valid_types'], products, context) == (None, [])


def test_world_formula_still_checks_rejected_original_runtime_fields() -> None:
    from nw.materials.network_layers import POLICY as LAYER_POLICY
    from nw.materials.network_workflow import POLICY as NETWORK_POLICY
    from nw.materials.semantic_application import unresolved_issues, validate_semantic_applications
    from nw.materials.semantic_products import validate_dynamic_dependencies
    from nw.materials.source_semantics import compile_semantics
    from test_material_semantic_clauses import criterion, source as draft_source

    _, raw, value, products, context = _case()
    snapshot = draft_source('dynamic-demo', original=json.dumps(raw, ensure_ascii=False))
    snapshot['source'].update(key=raw['id'], profile='dynamic_relation', path='原始资料/动态网络.txt')
    snapshot['related_sources'] = ['static-demo']
    rejected = '任何能力一律扣除固定体力作为统一消耗'
    text = json.dumps({'unsafe': rejected}, ensure_ascii=False)
    snapshot['application_layers'] = [{'source_ref': {'id': 'runtime', 'sha256': sha256(text.encode()).hexdigest()},
        'text': text, 'aligned_fields': [], 'rejected_fields': [{'field': 'unsafe', 'reason': '改变原义'}]}]
    contract = compile_semantics(snapshot)
    application = criterion(contract)
    bindings = []
    for clause in application['clauses']:
        if issues := unresolved_issues(contract, clause['id']):
            clause.update(applicability='source_unresolved', reason='待核 ' + issues[0]['kind'],
                          input_refs=[], output_refs=[], consumer='plot_design')
            continue
        clause.update(input_refs=[TYPE_PATH, RULE_PATH, LIMITS_PATH], consumer='plot_design',
                      output_refs=['/members/0/body/rule', '/members/0/body/limits'])
        bindings.extend({'clause_id': clause['id'], 'trigger_ref': RULE_PATH, 'result_ref': path}
                        for path in clause['output_refs'])
    assert bindings
    application['layer_application'] = {'bindings': bindings}
    value['_criteria'] = [application]
    context.update(network_layer_policy=LAYER_POLICY, network_prerequisite_policy=NETWORK_POLICY,
                   semantic_contracts=[contract], allowed_input_stages=['type_selection'])
    validate_semantic_applications('world_design', value, products, [snapshot], context)
    validate_dynamic_dependencies('world_design', value, products, [snapshot], context)

    clause = next(row for row in application['clauses'] if row['applicability'] == 'applies')
    clause['operation'] = rejected
    with pytest.raises(ValueError, match='rejected runtime field'):
        validate_semantic_applications('world_design', value, products, [snapshot], context)
