"""Exercise approved exchange and settlement rules in persisted world and plot stages."""
from dataclasses import replace
from pathlib import Path

import pytest

from test_material_world_conversion_flow import OTHER_GENRE, SELECTED_GENRE, WorldRuleCase, assert_world_flow


CURRENCIES = '灯币与潮币是北港钱市的通行货币。'
RATE = '封航期，北港钱市每1枚灯币可兑换4枚潮币。'
PENDING = '北港钱市在封航期，灯币兑潮币的汇率待定。'
SETTLEMENT = '北港钱市采用灯币兑潮币的挂牌比例结算船料交易。'
PERMIT = '仅持北港商票者可在北港钱市将灯币兑换为潮币。'
DEADLINE = '北港钱市的灯币兑潮币须在当日闭市前凭商票结算。'
RULE = CURRENCIES + RATE + SETTLEMENT
LIMITS = PERMIT + DEADLINE
REVERSED_RATE = RULE.replace('每1枚灯币可兑换4枚潮币', '每1枚潮币可兑换4枚灯币')

SETTLE = WorldRuleCase(
    kind='market', policy_key='world_market_policy', policy='world-market-prerequisites-v1',
    dynamic_key='C00546', static_key='25.2_汇率 / 26.2_交易规则 / 嵌套', condition='汇率是交易规则',
    effect='当起点成立时，终点作为起点的一部分参与当前状态。',
    rule=RULE, limits=LIMITS, waiting_reason='结算', title='北港钱市的船料结算',
    choice='[FAKE] 船工带商票赶在北港闭市前结算船料，核对兑入潮币与挂牌方向。',
    observable='[FAKE] 船料结单上有北港钱市的商票号、当日结算刻和潮币的收款记录。',
    check='[FAKE] 将封航期挂牌账与船料结单的两种币额及闭市时刻逐一核对。',
    changed_rule=REVERSED_RATE, changed_limits=PERMIT,
)
CURRENCY = replace(
    SETTLE, dynamic_key='C00542', static_key='25.1_货币类型 / 25.2_汇率 / 转化', condition='类型决定汇率',
    effect='当起点成立并满足转化条件时，将起点状态转为终点状态。', waiting_reason='货币',
    choice='[FAKE] 船工在北港凭商票出示一枚灯币，从钱市取回四枚潮币后复核挂牌。',
    observable='[FAKE] 商票对应的兑付簿同时记有灯币支出和四枚潮币的收入。',
    check='[FAKE] 对照北港封航期币种、挂牌方向及商票权限检查记账。',
)


TRADE = WorldRuleCase(
    kind='market', policy_key='world_market_policy', policy='world-market-prerequisites-v1',
    dynamic_key='C00544', static_key='25.1_货币类型 / 26.1_交易类型 / 转化', condition='货币决定交易',
    effect='当起点成立并满足转化条件时，将起点状态转为终点状态。',
    rule='在北港盐市进行现货买卖时，青盐商号接受买方用青铜钱支付盐款。',
    limits='北港盐市的现货买卖只在铜印验真后接受青铜钱。', waiting_reason='货币', title='北港盐市的现货交收',
    choice='[FAKE] 买方带青铜钱到北港盐市验铜印，通过后才向青盐商号付盐款。',
    observable='[FAKE] 青盐商号在铜印旁签收现货盐款，买方持青铜钱和领盐收据。',
    check='[FAKE] 核验现货交易地点、青盐商号的验印记录与买方付款币种。',
    changed_rule='在北港盐市进行现货买卖时，青盐商号接受买方用白铜钱支付盐款。',
    changed_limits='北港盐市的现货买卖接受青铜钱。',
    expected_evidence=(('market', '北港盐市'), ('method', '现货买卖'), ('currency', '青铜钱')),
)


@pytest.mark.parametrize(
    ('rule', 'genre', 'legacy'),
    [(RULE, SELECTED_GENRE, False), (CURRENCIES + RATE, SELECTED_GENRE, False),
     (CURRENCIES + PENDING + SETTLEMENT, SELECTED_GENRE, False), (REVERSED_RATE, SELECTED_GENRE, False),
     (RULE.replace('北港钱市采用', '云峡钱市采用'), SELECTED_GENRE, False),
     (RULE, OTHER_GENRE, False), (RULE, SELECTED_GENRE, True)],
    ids=['approved-settlement', 'no-transaction', 'price-unset', 'opposite-direction', 'other-market',
         'wrong-type', 'old-checkpoint'],
)
def test_settlement_admission_receipt_and_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str, genre: tuple[str, str], legacy: bool,
) -> None:
    assert_world_flow(tmp_path, monkeypatch, SETTLE, rule, genre, legacy)


@pytest.mark.parametrize(
    'case', [SETTLE, replace(CURRENCY, limits=PERMIT, changed_limits='只需在任意钱市登记。')],
    ids=['settlement-waits', 'currency-allowed'],
)
def test_missing_deadline_is_specific_to_settlement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: WorldRuleCase) -> None:
    assert_world_flow(tmp_path, monkeypatch, case, RULE, SELECTED_GENRE, False, input_limits=PERMIT)


def test_currency_and_settlement_adopted_from_one_card(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_world_flow(tmp_path, monkeypatch, CURRENCY, RULE, SELECTED_GENRE, False, lookup=True, also_adopt=(SETTLE,))


@pytest.mark.parametrize('limits', [TRADE.limits, TRADE.limits.replace('青铜钱', '白铜钱')], ids=['approved', 'wrong-currency'])
def test_trade_method_preserves_recipient_payment_and_clearance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limits: str) -> None:
    assert_world_flow(tmp_path, monkeypatch, TRADE, TRADE.rule, SELECTED_GENRE, False, input_limits=limits)


@pytest.mark.parametrize('invented_price', [False, True], ids=['pending-preserved', 'invented-price-blocked'])
def test_currency_can_carry_pending_quote_to_plot_without_settling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invented_price: bool,
) -> None:
    pending = replace(
        CURRENCY, rule=CURRENCIES + PENDING, changed_rule=CURRENCIES + RATE,
        choice='[FAKE] 钱市尚未挂牌，船工持商票约定下次询价，暂缓兑换。',
        observable='[FAKE] 钱市账册记明灯币兑潮币尚待挂牌，船工仍持有灯币。',
        check='[FAKE] 核对询价回条保留待挂牌状态，票据上没有擅填比率。',
        expected_evidence=(('rate_status', 'pending'), ('quote', PENDING.rstrip('。'))),
    )
    invented = '[FAKE] 船工在封航期的北港钱市按每1枚灯币兑换9枚潮币，钱庄照此挂牌比例当日结清船料款。'
    reason = '待定汇率'
    if invented_price:
        pending = replace(pending, choice=invented)
    assert_world_flow(tmp_path, monkeypatch, pending, pending.rule, SELECTED_GENRE, False,
                      rejection=reason if invented_price else None, altered_plot=(invented, reason))


@pytest.mark.parametrize('invented_sale', [False, True], ids=['approved-trade', 'changed-trade-blocked'])
def test_known_settlement_checks_the_actual_plot_price(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invented_sale: bool,
) -> None:
    correct = '[FAKE] 账房在封航期的北港钱市按每1枚灯币兑换4枚潮币结清船料款。'
    changed = correct.replace('4枚潮币', '9枚潮币')
    case = replace(SETTLE, choice=changed if invented_sale else correct)
    reason = '批准报价不符'
    assert_world_flow(tmp_path, monkeypatch, case, RULE, SELECTED_GENRE, False,
                      rejection=reason if invented_sale else None, altered_plot=(changed, reason))


def test_reverse_settlement_preserves_its_independent_quote_after_reopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rule = RATE + SETTLEMENT + '封航期，北港钱市每5枚潮币可兑换1枚灯币。'
    limits = LIMITS + '仅持回兑银票者可在北港钱市将潮币兑换为灯币。'
    sale = '[FAKE] 持回兑银票的船工在封航期的北港钱市按每5枚潮币换取1枚灯币成交。'
    case = replace(SETTLE, rule=rule, limits=limits, choice=sale)
    assert_world_flow(tmp_path, monkeypatch, case, rule, SELECTED_GENRE, False,
                      altered_plot=(sale.replace('5枚潮币', '4枚潮币'), '批准报价不符'))
