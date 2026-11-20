"""Verify actual approved gates for the six world-design advancement sources."""
from copy import deepcopy

import pytest

from nw.materials.world_advancement import POLICY, RULES, approved_advancement


LIMITS = '仅适用于完成验标的人；其他进阶条件仍待核。'
RULES_IN_USE = {
    'C00047': '本作力量公式 P=E×Q。力量值 P 至少达到82分才可进入凝纹境。',
    'C00099': '进阶凝纹境的门槛是实测灵压达到 30 灵格。',
    'C00195': '从聚气期进阶须天赋评级达到乙级。',
    'C00242': '晶核出现六角光纹是凝晶期的外显标志。该阶段进阶还须查验阵门试炼印号。',
    'C00736': '行会职位晋升须由评议人签署考核决议。能力进阶须测得灵压达到30灵格。两者均须出示守门试炼合格印。',
    'C00808': '符骨承载上限至少达到六十灵格才可进入凝纹境。',
}


def _card(rule: str, limits: str = LIMITS, **extra: object) -> dict:
    return {'card_id': 'approved-world', 'kind': 'world', 'version': 3, 'status': 'approved',
            'body': {'rule': rule, 'limits': limits}, **extra}


@pytest.mark.parametrize('key', RULES_IN_USE)
def test_each_rule_preserves_exact_approved_evidence_and_references(key: str) -> None:
    card = _card(RULES_IN_USE[key])
    snapshot = deepcopy(card)
    proof = approved_advancement(card, key)
    assert proof is not None, RULES[key]
    assert proof['card_id'] == 'approved-world' and proof['version'] == 3
    assert proof['rule'] == RULES_IN_USE[key] and proof['limits'] == LIMITS
    assert proof['rule_ref'] == 'approved:approved-world:/body/rule'
    assert proof['limits_ref'] == 'approved:approved-world:/body/limits'
    assert len(proof['evidence']) >= 2
    assert all(quote in proof['rule'] or quote in proof['limits'] for quote in proof['evidence'].values())
    assert snapshot == card


@pytest.mark.parametrize(('key', 'rule'), [
    ('C00047', '本作力量公式 P=E×Q。力量值 Q 至少达到82分才可进入凝纹境。'),
    ('C00047', '本作力量公式 P=E×Q。力量值 P ≥ 82分时免费扫卷，凝印进阶还须验标。'),
    ('C00047', '本作力量公式 P=E×Q。此后 P=3×E×Q。力量值 P ≥ 82分才可进入凝纹境。'),
    ('C00099', '装置校准时灵压达到30灵格，凝印进阶还须验标。'),
    ('C00099', '实测灵压达到30才可进入凝纹境。'),
    ('C00099', '实测灵压达到30神秘记号才可进入凝纹境。'),
    ('C00099', '凝纹进阶须年满30岁。'),
    ('C00099', '常规进阶需要实测灵压达到30灵格。'),
    ('C00099', '实测灵压达到30灵格并不是进阶门槛。'),
    ('C00099', '实测灵压达到30灵格才可进入凝纹境只是试行示例。'),
    ('C00195', '学徒天赋等级达到乙级可免修历史，从聚气期进阶还须验标。'),
    ('C00195', '从聚气期进阶须天赋较高。'),
    ('C00195', '所有人在此可进阶，天赋达到甲级可以免历史考核。'),
    ('C00242', '晶核出现六角光纹是凝晶期的外显标志。'),
    ('C00242', '晶核出现六角光纹是本阶段的标志。该阶段进阶还须查验试炼印号。'),
    ('C00242', '晶核出现六角光纹是凝晶期的外显标志。进入化灵期仍须查验阵门试炼印号。'),
    ('C00242', '晶核出现六角光纹是凝晶期的外显标志。进入裂魂期仍须查验阵门试炼印号。'),
    ('C00242', '晶核出现六角光纹是凝晶期的外显标志。该阶段进阶还须满足其他条件。'),
    ('C00736', '行会职位晋升须由评议人签署考核决议。能力进阶须通过工坊压力试炼。'),
    ('C00736', '行会职位晋升须通过工坊试炼。能力进阶须测得至少五十灵格。两者都须满足其他条件。'),
    ('C00736', '公会职位晋升须持白印。行会职位晋升须持黑印。能力进阶须通过压力试炼。两者均须出示合格凭记。'),
    ('C00736', '社会晋升与能力进阶都须出示守门试炼合格印。'),
    ('C00808', '符骨承载上限为六十灵格，可用记录仪监测，进阶还须核验印号。'),
    ('C00808', '当前资源储备至少为六十灵格才可进入凝纹境。'),
    ('C00808', '符骨承载上限尚未公布，要求合格才可进入凝纹境。'),
])
def test_unrelated_or_unconfirmed_premises_wait(key: str, rule: str) -> None:
    assert approved_advancement(_card(rule), key) is None


def test_a_continued_gate_and_known_boundary_keep_other_requirements_open() -> None:
    rule = '实测灵压达到30灵格，才可进入凝印期，其他进阶条件未定。'
    limits = '仅适用于通过验标的仪表；治疗术不采用这一计算规则。'
    proof = approved_advancement(_card(rule, limits), 'C00099')
    assert proof is not None and proof['rule'] == rule and proof['limits'] == limits
    assert proof['evidence']['gate'] == '实测灵压达到30灵格，才可进入凝印期'


def test_explicitly_named_promotion_and_ability_paths_can_share_one_real_item() -> None:
    rule = ('公会职位晋升须参加评议会的职级认定。能力进阶须通过工坊压力试炼。'
            '公会职位晋升与能力进阶均须出示守门试炼合格印。')
    proof = approved_advancement(_card(rule), 'C00736')
    assert proof is not None
    assert proof['evidence'] == {
        'social_gate': '公会职位晋升须参加评议会的职级认定',
        'ability_gate': '能力进阶须通过工坊压力试炼',
        'shared_prerequisite': '公会职位晋升与能力进阶均须出示守门试炼合格印',
    }


def test_cannot_borrow_authority_from_other_cards_or_world_output() -> None:
    formula = _card('本作力量公式 P=E×Q。')
    threshold = _card('力量值 P ≥ 82分才可进入凝纹境。')
    assert approved_advancement(formula, 'C00047') is None
    assert approved_advancement(threshold, 'C00047') is None
    for problem in ({'status': 'draft'}, {'kind': 'character'}, {'version': True}, {'version': 0}):
        card = {**_card(RULES_IN_USE['C00099']), **problem}
        assert approved_advancement(card, 'C00099') is None
    assert approved_advancement(_card(RULES_IN_USE['C00099'], '本作不采用这一规则。'), 'C00099') is None


def test_adopted_gate_and_parallel_conditions_cannot_be_rewritten_on_handoff() -> None:
    from nw.materials.semantic_handoff import handoffs_for
    from nw.materials.world_network import validate_world_network_use
    from test_material_world_network import _case, _record, _world

    source, _, value, products, context = _case()
    edge = {'source': '12.10_临界值', 'target': '15.1_进阶条件', 'type': '约束', 'condition': '临界值是进阶条件'}
    raw = {**edge, 'id': 'C00099', 'generated_from_static': True, 'valid_types': ['悬疑'],
           'condition': edge['condition'] + '；且当前故事明确采用该静态关系'}
    source['source']['key'] = raw['id']
    rule = '灵压达到 30 灵格才可进入凝印期。'
    limits = '还须通过验标，门槛只适用于持证衡灵者。'
    context['world_advancement_policy'] = POLICY
    context['approved_cards'] = [_world(rule, limits)]
    context['world_network_bases']['dynamic-demo']['edge'] = edge
    body = value['members'][0]['body']
    body.update(rule=rule, limits=limits)

    validate_world_network_use(source, raw, value, products, context)
    [delivery] = handoffs_for('plot_design', {'world_design': _record('world_design', value)})
    assert delivery['actual_inputs'] == [{'path': '/members/0/body/rule', 'value': rule},
                                         {'path': '/members/0/body/limits', 'value': limits}]

    body['rule'] = rule.replace('30', '20')
    with pytest.raises(ValueError, match='complete approved requirements and applicability limits'):
        validate_world_network_use(source, raw, value, products, context)
    body.update(rule=rule, limits='门槛只适用于持证衡灵者。')
    with pytest.raises(ValueError, match='complete approved requirements and applicability limits'):
        validate_world_network_use(source, raw, value, products, context)
