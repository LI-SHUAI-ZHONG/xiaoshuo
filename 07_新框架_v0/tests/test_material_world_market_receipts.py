"""Actual receiving fields must not turn a pending or different rate into a project fact."""
import pytest

from nw.materials.world_market_receipts import _assert_quote


SCOPE = '在封航期的北港钱市'
PENDING = {'from': '灯币', 'to': '潮币', 'market': '北港钱市', 'period': '封航期', 'rate_status': 'pending'}
QUOTED = dict(PENDING, rate_status='quoted', from_unit='枚', to_unit='枚', rate_numerator=4, rate_denominator=1)


@pytest.mark.parametrize('written', [
    '钱庄' + SCOPE + '挂牌每1枚灯币可兑换4枚潮币。',
    SCOPE + '按每4枚潮币折合1枚灯币记账。',
    SCOPE + '对账时按潮币兑灯币汇率为4:1折算。',
    SCOPE + '用八枚潮币折合两枚灯币记账。',
    SCOPE + '申请复核商票后再兑付。',
])
def test_approved_rate_equivalent_and_action_without_new_numbers(written: str) -> None:
    _assert_quote(QUOTED, written)


@pytest.mark.parametrize('evidence,written,reason', [
    (QUOTED, SCOPE + '按每1枚灯币兑换9枚潮币结清货款。', '批准报价不符'),
    (QUOTED, '北港钱市在封航期，实际对账每一枚潮币折合九枚灯币。', '批准报价不符'),
    (QUOTED, '封航期，北港钱市对账时按潮币兑灯币的汇率为1：4。', '批准报价不符'),
    (QUOTED, '封航期北港钱市，船工付出一枚灯币，当即兑回九枚潮币。', '批准报价不符'),
    (QUOTED, SCOPE + '柜台挂牌每1枚灯币可兑换9枚潮币。', '批准报价不符'),
    (QUOTED, SCOPE + '向当地钱庄付出一枚灯币，当即兑回九枚潮币。', '批准报价不符'),
    (QUOTED, SCOPE + '按每1盒灯币兑换4枚潮币成交。', '未经批准的计量单位'),
    (QUOTED, SCOPE + '按每4枚潮币换取1枚灯币成交。', '反向汇率与权限'),
    (QUOTED, SCOPE + '按每4枚潮币折合1枚灯币的比例反向兑付。', '反向汇率与权限'),
    (QUOTED, SCOPE + '潮币兑灯币的牌价为4:1。', '反向汇率与权限'),
    (QUOTED, '调查员听说行情有变，但账册证实封航期北港钱市每1枚灯币兑换9枚潮币。', '批准报价不符'),
    (QUOTED, SCOPE + '实际按每1枚灯币兑换9枚潮币，而另一桩传言仍待查证。', '批准报价不符'),
    (PENDING, SCOPE + '按每一枚灯币换四枚潮币成交。', '待定汇率'),
    (PENDING, SCOPE + '灯币兑潮币的牌价为一比四。', '待定汇率'),
])
def test_receipt_rejects_an_explicit_conflicting_local_sale_or_posted_rate(evidence, written, reason):
    with pytest.raises(ValueError, match=reason):
        _assert_quote(evidence, written)


@pytest.mark.parametrize('written', [
    '在开航期的北港钱市挂牌每1枚灯币兑换9枚潮币。',
    '在封航期的南港钱市挂牌每1枚灯币兑换9枚潮币。',
    SCOPE + '听到每1枚灯币换9枚潮币的传言。',
    SCOPE + '每1枚灯币兑换9枚潮币，这只是谣言。',
    SCOPE + '巡吏查证是否每1枚灯币可兑换9枚潮币。',
    SCOPE + '若按每1枚灯币换9枚潮币会怎样？',
    SCOPE + '并未按每1枚灯币换9枚潮币结清。',
    SCOPE + '后转至南港钱市，每1枚灯币换9枚潮币。',
    SCOPE + '，入开航期后每1枚灯币兑换9枚潮币。',
    SCOPE + '按每1枚盐币兑换9枚潮币成交。',
    SCOPE + '按每1枚灯币兑换9枚潮币券成交。',
    SCOPE + '持有一百二枚灯币兑换9枚潮币的手写便条。',
    '主角没有向钱庄出示商票。',
])
def test_other_scope_or_nonfactual_statement_cannot_be_called_a_conflict(written: str) -> None:
    _assert_quote(QUOTED, written)


def test_reverse_cash_sale_uses_separately_approved_spread_and_units():
    reverse = dict(from_unit='枚', to_unit='枚', rate_numerator=1, rate_denominator=5)
    both = dict(QUOTED, reverse_quote=reverse)
    _assert_quote(both, SCOPE + '按每5枚潮币换取1枚灯币成交。')
    with pytest.raises(ValueError, match='批准报价不符'):
        _assert_quote(both, SCOPE + '按每4枚潮币换取1枚灯币成交。')
