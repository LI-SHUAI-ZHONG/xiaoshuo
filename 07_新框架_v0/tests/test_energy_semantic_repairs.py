"""Project evidence for a single conversion batch or a bounded energy account."""
import pytest

from nw.materials.energy_semantics import check_conflict, eligible, validate_use
from nw.materials.world_conversion import approved_conversion
from test_material_world_conversion import BALANCE, FREE, FREE_LIMIT, _card

BATCH = '船坞用同批原料试烧时，转化效率决定了输出雾晶的纯度。'
BATCH_LIMIT = '只限这一批雾晶原料。'
WHEEL = '港闸验算以封闭水轮为界，守恒账把船工收回的余热也按实际去向记入总量。'
WHEEL_LIMIT = '只有同一水轮和蓄热槽内的转移才能合并入账。'
ACCOUNT = '封闭水轮转移余热后，船工将回收的热量也计入水轮总账。'


def row(key, rule, limit):
    return {'key': key, 'excerpts': [rule, limit], 'evidence': []}


@pytest.mark.parametrize('key', ['C00106', 'C00409'])
def test_literal_origin_in_prefixed_conservation_ledger(key):
    limits = FREE_LIMIT + '此路径的全部投入只取自湿雾井，西漠孤塔的材料严禁进入这口井。'
    assert approved_conversion(_card(FREE + BALANCE, limits), key)
    for name in ('西漠孤塔', '西漠孤塔的灵雾'):
        changed = BALANCE.replace('由湿雾井投入', f'由{name}投入')
        assert approved_conversion(_card(FREE + changed, limits), key) is None
        assert approved_conversion(_card(FREE + changed, limits), key, strict=False)
    assert not approved_conversion(_card(FREE + BALANCE.replace('剩余2', '剩余1'), limits), key)


@pytest.mark.parametrize('good', [BATCH_LIMIT, '仅对同一炉雾晶原料有效。', '不同批次不得混算。', '仅在北港适用，超过该区须重新核验。'])
def test_purity_accepts_scope_which_belongs_to_the_trial(good):
    assert eligible('C00035', BATCH, good)


@pytest.mark.parametrize('bad', ['月末只准登记食堂的柴火。', '只限食堂的采购。', '只准记入另一批的原料。'])
def test_purity_rejects_limits_on_other_operations_and_batches(bad):
    assert not eligible('C00035', BATCH, bad)


def test_efficiency_can_affect_impurities_in_either_project_defined_direction():
    observed = '同一炉铜砂精炼时收率越高，所得铜锭的杂质越少。'
    limit = '只限同一炉铜砂。'
    assert eligible('C00035', observed, limit)
    frozen = row('C00035', observed, limit)
    validate_use(frozen, '同炉铜砂精炼的收率越高，所得铜锭的纯度越高，工匠逐批取样。')
    with pytest.raises(ValueError):
        validate_use(frozen, '同炉铜砂精炼的收率越高，所得铜锭的纯度越低。')
    assert not eligible('C00035', '同一炉铜砂精炼时，铜锭的纯度决定了转化效率。', limit)


def test_adoption_and_sibling_outcomes_cannot_reverse_cause_or_change_the_batch():
    frozen = row('C00035', BATCH, BATCH_LIMIT)
    validate_use(frozen, '匠人按同一批雾晶的转化效率变化，核验它所影响的纯度再决定交货。')
    with pytest.raises(ValueError):
        validate_use(frozen, '雾晶的纯度决定了转化效率，船坞据此交付首批。')
    with pytest.raises(ValueError):
        check_conflict(frozen, '船坞把另一批雾晶代替本批雾晶登记。')
    check_conflict(frozen, '木匠查出柴房起火，库内木料另行登记。')


@pytest.mark.parametrize('key', ['C00107', 'C00410'])
@pytest.mark.parametrize('bad', ['封闭水轮总能量由100灵值升到150灵值。',
                                 '水轮转移前总量为100灵值，转移后总量为150灵值。',
                                 '该系统转移前100灵值，转移后150灵值。',
                                 '封闭系统的起始能量为100单位，转移后能量变为150单位。',
                                 '同一边界中的水轮总量由100升为150。',
                                 '封闭水轮总量从一百份降到五十份。',
                                 '水轮总量凭空翻倍，余热照常登记。'])
def test_conservation_checks_numeric_and_qualitative_contradictions_in_card_and_downstream(key, bad):
    assert not eligible(key, WHEEL, WHEEL_LIMIT, full_rule=WHEEL + bad)
    assert not eligible(key, WHEEL, WHEEL_LIMIT, full_limits=WHEEL_LIMIT + bad)
    frozen = row(key, WHEEL, WHEEL_LIMIT)
    with pytest.raises(ValueError):
        validate_use(frozen, ACCOUNT + bad)
    with pytest.raises(ValueError):
        check_conflict(frozen, bad)


@pytest.mark.parametrize('key', ['C00107', 'C00410'])
def test_transfer_between_components_can_change_local_stores_at_constant_total(key):
    value = '水轮总量由100灵值变为100灵值，局部总量由20灵值升到45灵值。'
    assert eligible(key, WHEEL, WHEEL_LIMIT, full_rule=WHEEL + value)
    validate_use(row(key, WHEEL, WHEEL_LIMIT), ACCOUNT + value)
    check_conflict(row(key, WHEEL, WHEEL_LIMIT), '另一座开放水池的总量从10灵值增加到23灵值。')
    with pytest.raises(ValueError):
        validate_use(row(key, WHEEL, WHEEL_LIMIT), '港闸船工出海向木匠打听下一批潮汐预报。')


def test_repeating_a_fixed_total_in_another_field_requires_the_frozen_value():
    fixed = '封闭水轮的总量恒为100灵值，守恒账将转移到船体的热量也计入总账。'
    frozen = row('C00410', fixed, WHEEL_LIMIT)
    check_conflict(frozen, '船工核实封闭水轮总量为100灵值。')
    with pytest.raises(ValueError):
        check_conflict(frozen, '船工核实封闭水轮总量为150灵值。')


def test_open_system_can_gain_accounted_energy_from_outside_its_boundary():
    rule = '港闸水轮是开放系统，守恒账把闸外锅炉输入50灵值登记到水轮总量。'
    limit = '仅在水轮与闸外锅炉的计量边界内结算。'
    correct = '锅炉向水轮转移热量后，水轮总量从100灵值升至150灵值，按闸外锅炉输入50灵值入账。'
    assert eligible('C00107', rule, limit, full_rule=rule + correct)
    validate_use(row('C00107', rule, limit), correct)
    for wrong in (correct.replace('150', '160'), correct.replace('输入50', '输入5')):
        with pytest.raises(ValueError):
            validate_use(row('C00107', rule, limit), wrong)
    assert not eligible('C00107', rule, limit, full_rule=rule + correct.replace('150', '160'))


def test_a_rate_and_a_quantity_cannot_be_used_as_the_same_total():
    assert not eligible('C00107', WHEEL, WHEEL_LIMIT, full_rule=WHEEL + '封闭水轮总量从100灵值变为100灵值/秒。')
    assert eligible('C00107', WHEEL, WHEEL_LIMIT, full_rule=WHEEL + '封闭水轮总量从1000焦耳变为1千焦。')
    validate_use(row('C00107', WHEEL, WHEEL_LIMIT), ACCOUNT + '船工当场识破“水轮总量从100灵值升至150灵值”的假账。')


def test_later_fixed_amount_from_the_same_project_card_survives_handoff():
    frozen = row('C00107', WHEEL, WHEEL_LIMIT)
    frozen['evidence'] = [{'ref': 'input:world_design:/members/0/body/rule',
                           'value': WHEEL + '该系统总量恒为100灵值。'}]
    check_conflict(frozen, '封闭水轮转化后总量为100灵值。')
    with pytest.raises(ValueError):
        validate_use(frozen, ACCOUNT + '封闭水轮总量为200灵值。')


def rehearsal(key, rule, limits, policy):
    from nw.materials.design_network import candidates
    from nw.task_models import content_sha256
    body = {'members': [{'key': 'wheel', 'kind': 'world', 'body': {'rule': rule, 'limits': limits}}]}
    world = {'stage': 'world_design', 'task_id': 'isolation', 'sha256': content_sha256(body), 'products': body}
    pins = {'owner': 'world_design', 'basis_stage': 'world_design', 'source': {'id': key}, 'static': {'id': 'edge'},
            'valid_types': ['悬疑']}
    context = {'scope': 'book', 'design_network_policy': policy, 'design_network_catalog': {key: pins},
               'network_type_scope': {'GENRE_XUANYI': ['悬疑']}}
    return candidates('plot_design', {'world_design': world}, context), context


def test_production_candidate_and_validation_preserve_legacy_policy_and_detect_unrelated_field():
    from nw.materials import design_network
    from nw.materials.design_network_catalog import POLICY
    old = 'frozen-design-prerequisites-v1'
    assert rehearsal('C00035', BATCH, '月末只准登记食堂的柴火。', old)[0]
    assert not rehearsal('C00035', BATCH, '月末只准登记食堂的柴火。', POLICY)[0]
    assert rehearsal('C00035', BATCH, BATCH_LIMIT, POLICY)[0]
    bad = '封闭水轮转移后，系统总能量由100灵值升至150灵值。'
    assert rehearsal('C00107', WHEEL + bad, WHEEL_LIMIT, old)[0]
    assert not rehearsal('C00107', WHEEL + bad, WHEEL_LIMIT, POLICY)[0]
    offered, context = rehearsal('C00107', WHEEL, WHEEL_LIMIT, POLICY)
    [item] = offered
    value = {'directions': [{'choice': ACCOUNT, 'consequence': bad}],
             '_network_design_uses': [{'id': item['id'], 'operation': ACCOUNT, 'output_refs': ['/directions/0/choice']}]}
    with pytest.raises(ValueError):
        design_network.validate('plot_design', value, offered, {}, context)
    value['directions'][0]['consequence'] = '封闭水轮转移后，系统总能量从100灵值变为100灵值。'
    design_network.validate('plot_design', value, offered, {}, context)
