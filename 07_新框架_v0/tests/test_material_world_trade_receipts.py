"""Verify the fees and accepted tender in the cited downstream transaction."""
import pytest

from nw.materials.world_trade_receipts import check_trade_claims
from test_material_world_conversion_flow import SELECTED_GENRE, WorldRuleCase, assert_world_flow
from test_material_world_trade import CASH, CASH_LIMIT, CONSIGN, CONSIGN_LIMIT, SPOT, SPOT_LIMIT


FEE = '每笔由买方支付两枚青钱作为手续费'
SCOPE = '北港盐市的现货买卖，'
RATE = '买方按本笔成交额的2.5%支付手续费'


def check(key, clause, fee=FEE):
    rule = SPOT.replace(FEE, fee)
    if key == 'C00550':
        rule += CONSIGN
    check_trade_claims(key, rule, SPOT_LIMIT + CONSIGN_LIMIT, [clause])


@pytest.mark.parametrize('key', ('C00550', 'C00555'))
@pytest.mark.parametrize('claim', (
    FEE.replace('两枚', '九枚'), FEE.replace('买方', '卖方'), '买方免缴手续费',
    FEE.replace('青钱', '白银'), FEE.replace('两枚', '两锭'),
))
def test_explicit_same_transaction_conflict(key, claim):
    with pytest.raises(ValueError, match=key + ' 下游交易费用'):
        check(key, SCOPE + claim)


@pytest.mark.parametrize('claim', (
    SCOPE + FEE.replace('两枚', '2枚'), SCOPE.replace('北港', '西港') + FEE.replace('两枚', '九枚'),
    SCOPE.replace('现货买卖', '寄售') + FEE.replace('两枚', '九枚'),
    SCOPE + FEE.replace('两枚', '九枚').replace('手续费', '鉴定费'),
    '船工听说，' + SCOPE + FEE.replace('两枚', '九枚'), SCOPE + FEE.replace('两枚', '九枚') + '？',
    '特批期间，' + SCOPE + FEE.replace('两枚', '九枚'),
    '封航期，' + SCOPE + FEE.replace('两枚', '九枚'),
    SCOPE + '夜市开放时，' + FEE.replace('两枚', '九枚'),
    SCOPE + '卖方免缴手续费', SCOPE + '买方实际支付两枚青钱作为手续费',
    SCOPE + '买方不必支付九枚青钱作为手续费',
))
def test_quantity_equivalent_or_different_context(claim):
    check('C00550', claim)


@pytest.mark.parametrize('claim', (
    '船工听说佣金有变，但账册证实' + SCOPE + FEE.replace('两枚', '九枚'),
    '开市钟响后，' + SCOPE + FEE.replace('两枚', '九枚'),
    SCOPE + '开市钟响后，' + FEE.replace('两枚', '九枚'),
    SCOPE + '买方实际支付九枚青钱作为手续费',
    SCOPE.rstrip('，') + '每笔手续费由买方实际支付九枚青钱',
    SPOT.replace('两枚', '九枚'),
))
def test_confirmed_payment_or_approved_condition_remains_binding(claim):
    with pytest.raises(ValueError, match='C00555 下游交易费用'):
        check('C00555', claim)


def test_percentage_amounts_and_waivers():
    check('C00555', SCOPE + RATE.replace('成交额的2.5%', '成交金额的2.50％'), fee=RATE)
    check('C00555', SCOPE + '买方支付九枚青钱作为手续费', fee=RATE)
    for fee, claim in ((RATE, RATE.replace('2.5%', '5%')), (RATE, RATE.replace('成交额', '货值')),
                       (RATE, '买方免付手续费'), (RATE, FEE), ('买方免付手续费', FEE)):
        with pytest.raises(ValueError, match='C00555 下游交易费用'):
            check('C00555', SCOPE + claim, fee=fee)
    check('C00555', SCOPE + FEE.replace('两枚', '零枚'), fee='买方免缴手续费')
    check('C00555', SCOPE + FEE.replace('买方', '卖方'), fee='买方免缴手续费')


def test_tender_refusal_and_exclusive_exchange_terms():
    changed = '青盐商号接受买方用白银币支付盐款'
    exclusive = CASH.replace('接受', '仅接受')
    for rule, claim in ((CASH, '青盐商号拒收青铜钱'), (exclusive, changed),
                        (exclusive, '青盐商号接受卖方用青铜钱支付盐款')):
        with pytest.raises(ValueError, match='C00544 下游'):
            check_trade_claims('C00544', rule, CASH_LIMIT, [SCOPE + claim])
    for rule, claim in ((CASH, changed), (exclusive, changed.replace('青盐商号', '黄盐商号')),
                        (exclusive, changed.replace('盐款', '船款')), (CASH, '黄盐商号拒收青铜钱')):
        check_trade_claims('C00544', rule, CASH_LIMIT, [SCOPE + claim])


def test_reopened_plot_uses_the_approved_fee_from_its_world_handoff(tmp_path, monkeypatch):
    case = WorldRuleCase(
        kind='market', policy_key='world_market_policy', policy='world-market-prerequisites-v1',
        dynamic_key='C00555', static_key='26.2_交易规则 / 26.3_交易成本 / 转化', condition='规则决定成本',
        effect='当起点成立并满足转化条件时，将起点状态转为终点状态。',
        rule=SPOT, limits=SPOT_LIMIT, waiting_reason='成本', title='北港盐市的交割费',
        choice='[FAKE] ' + SCOPE + FEE + '。',
        observable='[FAKE] 盐税房在交割单上列出买方实付的两枚青钱和出示的盐引。',
        check='[FAKE] 对照北港现货交割单确认收费人、承担方及金额。',
        changed_rule=SPOT.replace('两枚青钱', '九枚青钱'), changed_limits=SPOT_LIMIT.replace('开市钟响', '外船归港'),
        expected_evidence=(('market', '北港盐市'), ('method', '现货买卖')),
    )
    assert_world_flow(tmp_path, monkeypatch, case, case.rule, SELECTED_GENRE, False,
                      altered_plot=(case.choice.replace('两枚', '九枚'), 'C00555 下游交易费用'))
