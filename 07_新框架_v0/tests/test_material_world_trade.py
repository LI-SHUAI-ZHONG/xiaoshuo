"""Exercise the five original trade edges against scoped author facts."""
import pytest

from nw.materials.world_trade import RULES, approved_trade


CASH = '在北港盐市进行现货买卖时，青盐商号接受买方用青铜钱支付盐款。'
CASH_LIMIT = '北港盐市的现货买卖只在铜印验真后接受青铜钱。'
SPOT = '在北港盐市进行现货买卖时，买方须出示盐引，每笔由买方支付两枚青钱作为手续费，争议由盐税房凭交割单裁定。'
CONSIGN = '在北港盐市进行寄售时，寄售人须提交仓单，每笔由寄售人支付三枚青钱作为佣金，争议由商会凭寄售契调解。'
SPOT_LIMIT = '北港盐市的现货买卖只在开市钟响后受理。'
CONSIGN_LIMIT = '北港盐市的寄售只在船队入港后受理。'
COST = '在北港盐市进行竞拍时，买方须等待三个时辰验货，卖方在仓单破损时承担货物退运的风险。'
COST_LIMIT = '北港盐市的竞拍仅在公仓放行后交割。'
RANK = '在北港盐市进行竞拍时，仅上籍盐户阶层的商户凭白盐引可竞买青盐。'
RANK_LIMIT = '北港盐市的竞拍仅在水患赈灾时允许民籍船户凭赈令竞买青盐。'
BARTER = '在北港盐市进行以物易物时，持潮引的船户可用一袋青盐换取两束灯芯，双方须在交割前核对潮印。'
BARTER_LIMIT = '北港盐市的以物易物仅在主航道封冻时允许船户凭缓运令延期交付灯芯。'
CASES = {
    'C00544': (CASH, CASH_LIMIT),
    'C00550': (SPOT + CONSIGN, SPOT_LIMIT + CONSIGN_LIMIT),
    'C00555': (COST, COST_LIMIT),
    'C00556': (RANK, RANK_LIMIT),
    'C01762': (BARTER, BARTER_LIMIT),
}


def proof(key, rule, limits, **changes):
    card = {'card_id': 'trade-ledger', 'version': 3, 'status': 'approved', 'kind': 'world',
            'body': {'rule': rule, 'limits': limits}, **changes}
    return approved_trade(card, key)


@pytest.mark.parametrize('key', CASES)
def test_complete_approved_terms_keep_verbatim_source_and_version(key):
    rule, limits = CASES[key]
    chosen = proof(key, rule, limits)
    assert chosen['card_id'] == 'trade-ledger' and chosen['version'] == 3
    assert chosen['rule'] == rule and chosen['limits'] == limits
    assert chosen['rule_ref'] == 'approved:trade-ledger:/body/rule'
    assert chosen['limits_ref'] == 'approved:trade-ledger:/body/limits'
    assert chosen['evidence']


@pytest.mark.parametrize(('field','value'), [('kind', 'plot'), ('status', 'draft'), ('card_id', ''), ('version', True)])
def test_requires_valid_world_approval(field, value):
    assert proof('C00544', CASH, CASH_LIMIT, **{field: value}) is None


@pytest.mark.parametrize(('key','example','old','new'), [
    ('C00544', 0, '青盐商号', '某个商号'), ('C00544', 0, '青铜钱', '盐块'), ('C00544', 0, '接受', '拒绝'),
    ('C00544', 1, '北港盐市', '东港盐市'), ('C00544', 1, '现货买卖', '寄售'),
    ('C00544', 1, '青铜钱', '白银币'), ('C00544', 1, '铜印验真', '满足要求'),
    ('C00544', 1, '接受青铜钱', '展示青铜钱'),
    ('C00550', 0, '提交仓单', '提交某种证明'), ('C00550', 0, '支付三枚青钱作为佣金', '询问其他手续费'),
    ('C00550', 0, '争议由商会凭寄售契调解', '争议处理待定'), ('C00550', 1, '寄售', '竞拍'),
    ('C00550', 0, '在北港盐市进行寄售时', '在东岸集市进行现货买卖时'),
    ('C00550', 0, '每笔由寄售人支付三枚青钱作为佣金', '另一条渠道，寄售人支付三枚青钱作为佣金'),
    ('C00555', 0, '买方须等待三个时辰验货，', ''),  # The risk itself is still valid.
    ('C00556', 0, '上籍盐户阶层', '上籍盐户'), ('C00556', 1, '竞买青盐', '竞买白铁'),
    ('C00556', 1, '赈令', '某种文件'), ('C01762', 0, '一袋青盐', '一袋灯芯'),
    ('C01762', 0, '持潮引的船户', '船户'), ('C01762', 0, '核对潮印', '旁观落潮'),
    ('C01762', 1, '船户', '药商'), ('C01762', 1, '交付灯芯', '交付红铜'),
])
def test_missing_or_crossed_terms(key, example, old, new):
    texts = list(CASES[key])
    assert old in texts[example]
    texts[example] = texts[example].replace(old, new)
    if key == 'C00555':
        assert proof(key, *texts)['evidence']['costs'] == ['卖方在仓单破损时承担货物退运的风险']
    else:
        assert proof(key, *texts) is None


def test_distinct_methods_keep_their_own_payers_dispute_offices_and_boundaries():
    evidence = proof('C00550', SPOT + CONSIGN, SPOT_LIMIT + CONSIGN_LIMIT)['evidence']
    spot, consign = evidence['transactions']
    assert (spot['method'], spot['fees'][0], spot['dispute'], spot['boundary']) == (
        '现货买卖', '每笔由买方支付两枚青钱作为手续费', '争议由盐税房凭交割单裁定', SPOT_LIMIT.rstrip('。'))
    assert (consign['method'], consign['fees'][0], consign['dispute']) == (
        '寄售', '每笔由寄售人支付三枚青钱作为佣金', '争议由商会凭寄售契调解')
    assert proof('C00550', SPOT, SPOT_LIMIT) is None
    assert proof('C00550', SPOT + SPOT, SPOT_LIMIT) is None


def test_named_cost_and_fee_exemption_distinguish_extra_costs_from_goods_prices():
    assert proof('C00555', SPOT, SPOT_LIMIT)['evidence']['costs'] == ['每笔由买方支付两枚青钱作为手续费']
    assert proof('C00555', SPOT.replace('每笔由买方支付两枚青钱作为手续费', '买方免缴手续费'), SPOT_LIMIT)
    for replacement in ('每笔由买方支付两枚青钱作为盐价', '每笔由码头付给车夫三枚钱', '手续费由买方承担'):
        assert proof('C00555', SPOT.replace('每笔由买方支付两枚青钱作为手续费', replacement), SPOT_LIMIT) is None


def test_explicit_quota_and_no_exception():
    quota = '在北港盐市进行竞拍时，上籍盐户阶层的商户持白盐引每日限竞买三袋青盐。'
    none = '北港盐市的竞拍对上述资格不设例外。'
    assert '三袋青盐' in proof('C00556', quota, none)['evidence']['qualification']
    assert proof('C01762', BARTER, '北港盐市的以物易物对上述交割不设例外。')
    assert proof('C01762', BARTER, '北港盐市的以物易物对上述资格不设例外。') is None


def test_stopped_or_unapproved_scope_remains_pending():
    assert proof('C00544', CASH, CASH_LIMIT + '北港盐市的现货买卖停办。') is None
    assert proof('C00544', '仅作示例。' + CASH, CASH_LIMIT) is None
    assert proof('C00544', CASH, CASH_LIMIT + '本卡已撤销。') is None
    assert proof('C00544', CASH, CASH_LIMIT + '东港盐市的现货买卖停办。')
    assert set(RULES) == set(CASES)


def test_percentage_cost_needs_payer_component_and_named_calculation_basis():
    rule = '在北港盐市进行现货买卖时，买方按本笔成交额的2.5%支付手续费。'
    assert proof('C00555', rule, SPOT_LIMIT)['evidence']['costs'] == ['买方按本笔成交额的2.5%支付手续费']
    assert proof('C00555', rule.replace('本笔成交额的', ''), SPOT_LIMIT) is None
    assert proof('C00555', rule.replace('本笔成交额', '邻市成交额'), SPOT_LIMIT) is None
    assert proof('C00555', rule.replace('买方', '旁观者'), SPOT_LIMIT) is None


def test_distinct_payers_and_cost_components_cannot_disguise_contradictions():
    first = '每笔由买方支付两枚青钱作为手续费'
    against = '卖方免缴手续费'
    other = '买方按本笔成交额的3%支付交易税'
    joint = SPOT.replace(first, '，'.join((first, against, other)))
    costs = proof('C00555', joint, SPOT_LIMIT)['evidence']['costs']
    assert set(costs) == {first, against, other}
    assert proof('C00555', joint.replace('卖方免缴', '买方免缴'), SPOT_LIMIT) is None
    assert proof('C00555', COST.replace('验货，', '验货，买方须等待五个时辰验货，'), COST_LIMIT) is None


def test_explicit_in_world_currency_and_scoped_cash_purchase():
    exotic = CASH.replace('用青铜钱', '用货币星砂')
    bounds = '在北港盐市进行现货买卖时，仅在铜印验真后接受星砂。'
    assert proof('C00544', exotic, bounds)['evidence']['currency'] == '星砂'
    assert proof('C00544', exotic.replace('货币', ''), bounds) is None
    purchase = BARTER.replace('以物易物', '现货买卖').replace('一袋青盐换取', '三枚青铜钱购买')
    exception = BARTER_LIMIT.replace('以物易物', '现货买卖')
    assert proof('C01762', purchase, exception)


def test_later_explicit_veto_targets_the_same_market_method_and_currency():
    assert proof('C00544', CASH, CASH_LIMIT + '北港盐市的现货买卖一律拒收青铜钱。') is None
    assert proof('C00544', CASH, CASH_LIMIT + '北港盐市的现货买卖禁止使用白银币。')
    assert proof('C00544', CASH, CASH_LIMIT + '南港盐市的现货买卖一律拒收青铜钱。')
    assert proof('C00544', CASH + '北港盐市的现货买卖已停办。', CASH_LIMIT) is None
    assert proof('C00544', CASH, CASH_LIMIT + '北港盐市的现货买卖不再收取白银币。')
    assert proof('C00544', CASH.rstrip('。') + '，青盐商号不接受白银币。', CASH_LIMIT)
    assert proof('C00544', CASH + '青盐商号不接受青铜钱。', CASH_LIMIT) is None


def test_foreign_cost_or_dispute_does_not_complete_a_second_method():
    for wrong in ('寄售人支付三枚青钱作为佣金', '争议由商会凭寄售契调解'):
        misrouted = CONSIGN.replace(wrong, '东港盐市的寄售中，' + wrong)
        assert proof('C00550', SPOT + misrouted, SPOT_LIMIT + CONSIGN_LIMIT) is None


def test_trade_limits_split_at_real_newlines_and_keep_latin_venue_names():
    limits = SPOT_LIMIT.rstrip('。') + '\r\n' + CONSIGN_LIMIT
    assert proof('C00550', SPOT + CONSIGN, limits)
    assert proof('C00550', (SPOT + CONSIGN).replace('北港盐市', 'Northmarket'),
                 limits.replace('北港盐市', 'Northmarket'))
