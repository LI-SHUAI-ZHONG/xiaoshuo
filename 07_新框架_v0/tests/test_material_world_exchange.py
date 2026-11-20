"""Check that each world-economy rule is supported by the same approved exchange account."""
from fractions import Fraction
import re

import pytest

from nw.materials.world_exchange import NUMBER, amount_value, approved_exchange


RATE = '封航期，北港钱市每1枚灯币可兑换4枚潮币。'
PENDING = '北港钱市在封航期，灯币兑潮币的汇率待定。'
CURRENCIES = '灯币与潮币是北港钱市的通行货币。'
VALUES = '北港钱市按仓票面值计价，每枚灯币值4票点，每枚潮币值1票点。'
DEAL = '北港钱市采用灯币兑潮币的挂牌比例结算船料交易。'
LEDGER = '北港资源簿引用北港钱市的《封航兑价簿》登记灯币兑潮币，用于核算潮币的取得量。'
LIMIT = '仅持北港商票者可在北港钱市将灯币兑换为潮币。'
SETTLE = '北港钱市的灯币兑潮币须在当日闭市前凭商票结算。'
CASES = {
    'C00533': (RATE + VALUES, LIMIT),
    'C00542': (CURRENCIES + RATE, LIMIT),
    'C00546': (RATE + DEAL, LIMIT + SETTLE),
    'C00548': (RATE + LEDGER, LIMIT),
}


def prove(key, rule, limits=LIMIT, **overrides):
    card = {'card_id': 'harbor-rate', 'version': 3, 'kind': 'world', 'status': 'approved',
            'body': {'rule': rule, 'limits': limits}, **overrides}
    return approved_exchange(card, key)


@pytest.mark.parametrize('key', CASES)
def test_only_corresponding_rule_and_bounds_on_approved_card(key):
    rule, limits = CASES[key]
    proof = prove(key, rule, limits)
    assert proof['evidence']['quote'] == RATE[:-1]
    assert proof['evidence']['boundary'] == LIMIT[:-1]
    assert (proof['evidence']['from_unit'], proof['evidence']['to_unit']) == ('枚', '枚')
    assert (proof['evidence']['rate_numerator'], proof['evidence']['rate_denominator']) == (4, 1)
    assert (proof['rule'], proof['limits'], proof['version']) == (rule, limits, 3)
    assert set(k for k in CASES if prove(k, rule, limits)) == {key}
    assert not prove(key, rule, limits, status='proposed')


def test_shared_quote_all_four_domains():
    rule = CURRENCIES + RATE + VALUES + DEAL + LEDGER
    for key in CASES:
        p = prove(key, rule, LIMIT + SETTLE)
        assert p['evidence']['market'] == '北港钱市'
        assert p['evidence']['period'] == '封航期'
        assert (p['evidence']['from'], p['evidence']['to']) == ('灯币', '潮币')


def test_pending_exchange_documents_uncertainty_without_permitting_settlement():
    rule = CURRENCIES + PENDING + VALUES + DEAL + LEDGER
    proof = prove('C00542', rule, LIMIT + SETTLE)
    assert proof['evidence']['rate_status'] == 'pending' and proof['rule'] == rule
    assert {'from_unit', 'to_unit', 'rate_numerator', 'rate_denominator'}.isdisjoint(proof['evidence'])
    assert all(not prove(k, rule, LIMIT + SETTLE) for k in ('C00533', 'C00546', 'C00548'))


@pytest.mark.parametrize('rate', [
    '封航期，北港钱市每一枚灯币可兑四枚潮币。',
    '北港钱市在封航期，每二枚灯币兑换八枚潮币。',
    '封航期，北港钱市每0.5枚灯币可兑换2枚潮币。',
    '封航期，北港钱市每半枚灯币兑换两枚潮币。',
])
def test_equivalent_explicit_rates_are_preserved(rate):
    proof = prove('C00533', rate + VALUES)
    assert proof['evidence']['quote'] == rate[:-1]


@pytest.mark.parametrize(('key', 'old', 'new'), [
    ('C00533', '值4票点', '值5票点'), ('C00533', '值1票点', '值1灵格'),
    ('C00533', '每枚潮币值', '每袋潮币值'), ('C00533', '每枚潮币值', '每枚灰币值'),
    ('C00533', '北港钱市按仓票', '南港钱市按仓票'), ('C00533', '4枚潮币', '0枚潮币'),
    ('C00542', '通行货币', '展柜藏品'), ('C00542', '灯币与潮币', '灯币与海贝'),
    ('C00542', '北港钱市的通行', '北桥镇的通行'),
    ('C00546', '结算船料交易', '陈列账目'), ('C00546', '采用灯币兑潮币', '采用潮币兑灯币'),
    ('C00546', '北港钱市采用', '南港钱市采用'),
    ('C00548', '北港资源簿', '其他材料'), ('C00548', '取得量', '消耗量'),
    ('C00548', '引用北港钱市', '引用北湾钱市'), ('C00548', '登记灯币兑潮币', '登记潮币兑灯币'),
    ('C00548', '《封航兑价簿》', '《来源》'),
])
def test_changed_subject_basis_rate_or_role_is_rejected(key, old, new):
    rule, bounds = CASES[key]
    assert old in rule and not prove(key, rule.replace(old, new), bounds)


@pytest.mark.parametrize('key', CASES)
def test_rate_cannot_outlive_its_approved_market_direction_and_authority(key):
    rule, limits = CASES[key]
    assert not prove(key, rule, limits.replace('北港钱市', '北湾钱市'))
    assert not prove(key, rule, limits.replace('灯币兑换为潮币', '潮币兑换为灯币').replace('灯币兑潮币','潮币兑灯币'))
    assert not prove(key, rule + RATE.replace('4枚', '6枚'), limits)
    assert not prove(key, rule + '北港钱市的灯币兑潮币报价作废。', limits)
    assert not prove(key, rule, limits.replace('北港商票', '相关凭证').replace('凭商票','凭相关凭证'))


@pytest.mark.parametrize('change', ['当日闭市前', '凭商票', '灯币兑潮币'])
def test_settlement_receipt_requires_the_named_window_authority_and_direction(change):
    assert not prove('C00546', RATE + DEAL, LIMIT + SETTLE.replace(change, ''))

@pytest.mark.parametrize('heading', ['以下是示例。', '旧方案如下。', '仅供演示。', '假设：'])
@pytest.mark.parametrize('key', CASES)
def test_example_heading_does_not_authorize_the_following_quote(heading, key):
    rule, limits = CASES[key]
    assert not prove(key, heading + rule, limits)


@pytest.mark.parametrize('pending', [PENDING, '封航期，北港钱市灯币兑潮币的汇率待定。',
                                     '封航期，北港钱市的灯币兑潮币的汇率待公布。'])
@pytest.mark.parametrize('key', CASES)
def test_pending_and_known_quotes_for_same_scope_conflict(pending, key):
    rule, limits = CASES[key]
    assert prove('C00542', CURRENCIES + pending)['evidence']['rate_status'] == 'pending'
    assert not prove(key, pending + rule, limits)
    assert not prove(key, rule + pending, limits)


def test_project_value_ratio_can_define_price_without_an_external_currency():
    factors = '北港钱市按验银重量折价，每枚灯币的票面价值是每枚潮币的四倍。'
    assert prove('C00533', RATE + factors)['evidence']['valuation'] == factors[:-1]
    assert not prove('C00533', RATE + factors.replace('四倍', '八倍'))


def test_separately_confirmed_currencies_still_belong_to_the_same_market():
    currencies = '灯币是北港钱市的通行货币。潮币是北港钱市的结算货币。'
    assert prove('C00542', currencies + RATE)
    assert not prove('C00542', currencies.replace('潮币是北港', '潮币是西港') + RATE)


def test_a_specific_settlement_restriction_is_itself_a_boundary():
    assert prove('C00546', RATE + DEAL, SETTLE)['evidence']['boundary'] == SETTLE[:-1]
    assert not prove('C00546', RATE + DEAL, SETTLE.replace('当日闭市前', '有关时候'))


def test_withdrawal_after_quote_applies_to_identified_direction():
    assert not prove('C00542', CURRENCIES + RATE + '上述报价已废止。')
    assert prove('C00542', CURRENCIES + RATE + '南湾钱市的灯币兑潮币报价已废止。')

@pytest.mark.parametrize(('text', 'expected'), [
    ('半', '1/2'), ('零', '0'), ('十', '10'), ('三百二十七', '327'), ('一千零三十', '1030'),
    ('一万零三百零五', '10305'), ('两万三千', '23000'), ('十二点零五', '12.05'), ('１２．５０', '12.5'),
])
def test_authored_units_keep_exact_numeric_meaning(text, expected):
    assert re.fullmatch(NUMBER, text) and amount_value(text) == Fraction(expected)


@pytest.mark.parametrize('text', ['一百二', '一万三', '十十', '两百百', '三点', '一千零'])
def test_ambiguous_chinese_shorthand_cannot_be_counted_as_a_known_price(text):
    assert not re.fullmatch(NUMBER, text)

def test_value_facts_follow_named_currency_even_if_the_order_is_reversed():
    reverse = VALUES.replace('每枚灯币值4票点，每枚潮币值1票点', '每枚潮币值1票点，每枚灯币值4票点')
    assert prove('C00533', RATE + reverse)['evidence']['valuation'] == reverse[:-1]
    assert not prove('C00533', RATE + VALUES + reverse.replace('值4票点', '值6票点'))


def test_local_withdrawal_of_a_specific_quote_reopens_the_calculation():
    assert not prove('C00542', RATE + CURRENCIES + '该汇率仍待定。')


REVERSE = '封航期，北港钱市每5枚潮币可兑换1枚灯币。'
REVERSE_LIMIT = '仅持回兑银票者可在北港钱市将潮币兑换为灯币。'


def test_approved_settlement_records_separately_authorized_reverse_price_and_spread():
    rule = RATE + DEAL + REVERSE
    limits = LIMIT + SETTLE + REVERSE_LIMIT
    evidence = prove('C00546', rule, limits)['evidence']
    assert evidence['rate_numerator'] == 4
    assert evidence['reverse_quote'] == {
        'quote': REVERSE[:-1], 'boundary': REVERSE_LIMIT[:-1], 'market': '北港钱市', 'period': '封航期',
        'from': '潮币', 'to': '灯币', 'from_unit': '枚', 'to_unit': '枚', 'rate_status': 'quoted',
        'rate_numerator': 1, 'rate_denominator': 5,
    }
    # Both roles would fit the generic currency edge, so its adopted direction remains unresolved.
    assert not prove('C00542', CURRENCIES + rule, limits)


@pytest.mark.parametrize(('reverse', 'permit'), [
    (REVERSE, ''), ('', REVERSE_LIMIT), (REVERSE.replace('北港', '南港'), REVERSE_LIMIT),
    (REVERSE.replace('封航期', '开航期'), REVERSE_LIMIT),
    (REVERSE, REVERSE_LIMIT.replace('回兑银票', '相关条件')),
    (REVERSE + REVERSE.replace('每5枚', '每8枚'), REVERSE_LIMIT),
    (REVERSE + '北港钱市在封航期，潮币兑灯币的汇率待定。', REVERSE_LIMIT),
    (REVERSE + '北港钱市的潮币兑灯币已停兑。', REVERSE_LIMIT),
    (REVERSE, REVERSE_LIMIT + '北港钱市禁止将潮币兑换为灯币。'),
    ('北港钱市在封航期，潮币兑灯币的汇率待定。', REVERSE_LIMIT),
])
def test_forward_cash_right_does_not_supply_the_reverse_permission(reverse, permit):
    evidence = prove('C00546', RATE + DEAL + reverse, LIMIT + SETTLE + permit)['evidence']
    assert evidence['from'] == '灯币' and 'reverse_quote' not in evidence
