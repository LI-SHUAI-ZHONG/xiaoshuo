"""Market valuations are grounded in one project's approved local supply and demand."""
import pytest

from nw.materials.world_market import approved_valuation, check_valuation_claims


LIMITS = '灯盐估价仅适用于北港盐市封航期。'
SCOPE = '封航期，北港盐市的灯盐'
FLOW = '灯盐每旬供应25袋，当地每旬需求45袋，'
LEVEL = SCOPE + '属于照明耗材，用于给港灯续火，' + FLOW + '灯盐市价按每袋3枚铜铢。'
CHANGE = (SCOPE + '每旬产量由60袋减至30袋，' + FLOW
          + '灯盐可用雾盐替代，本期雾盐只到货5袋，减产使灯盐市价由每袋2枚铜铢涨至每袋4枚铜铢。')
CASES = {'C00429': (CHANGE, LIMITS), 'C00524': (LEVEL, LIMITS)}


def read(rule, key, limits=LIMITS, **fields):
    card = {'card_id': 'harbor-valuation', 'kind': 'world', 'status': 'approved', 'version': 3,
            'body': {'rule': rule, 'limits': limits}}
    return approved_valuation({**card, **fields}, key)


@pytest.mark.parametrize('key', CASES)
def test_price_evidence_is_exact_and_can_be_reopened(key):
    rule, limits = CASES[key]
    result = read(rule, key, limits)
    assert (result['version'], result['rule'], result['limits']) == (3, rule, limits)
    evidence = result['evidence']
    assert evidence['market'] == '北港盐市'
    assert evidence['resource'] == '灯盐' and evidence['period'] == '封航期'
    assert all(evidence[k] in rule for k in ('supply', 'demand', 'valuation'))
    assert evidence['boundary'] in limits
    assert read(rule, key, status='draft') is None


@pytest.mark.parametrize(('key','old','replacement'), [
    ('C00429', '60袋减至30袋', '20袋减至30袋'), ('C00429', '减至30袋', '减至30箱'),
    ('C00429', '灯盐每旬供应', '炭盐每旬供应'), ('C00429', '每旬需求', '每月需求'),
    ('C00429', '需求45袋', '需求45箱'), ('C00429', '可用雾盐', '可用灯盐'),
    ('C00429', '雾盐只到货', '草盐只到货'), ('C00429', '本期雾盐只到货5袋，', ''),
    ('C00429', '涨至每袋4枚铜铢', '涨至每袋1枚铜铢'), ('C00429', '涨至每袋4枚铜铢', '涨至每箱4枚铜铢'),
    ('C00429', '涨至每袋4枚铜铢', '涨至每袋4枚银铢'), ('C00429', '灯盐市价由', '雾盐市价由'),
    ('C00524', '照明耗材', '资源'), ('C00524', '给港灯续火', '用途'),
    ('C00524', '给港灯续火', '待定'), ('C00524', '灯盐市价按', '雾盐市价按'),
    ('C00524', '灯盐市价按每袋', '灯盐市价按每桶'), ('C00524', '当地每旬需求45袋，', ''),
])
def test_unmatched_or_contradictory_claims_stay_waiting(key, old, replacement):
    rule, limits = CASES[key]
    assert old in rule
    assert read(rule.replace(old, replacement), key, limits) is None


@pytest.mark.parametrize('lim', [LIMITS.replace('北港', '西港'), LIMITS.replace('封航', '开航'),
                                LIMITS.replace('灯盐', '雾盐'), '本市通用。'])
def test_quote_and_bounds_must_refer_to_the_same_item_market_and_period(lim):
    assert read(LEVEL, 'C00524', lim) is None


def test_falling_or_flat_market_does_not_activate_the_derived_price_increase():
    for change in ('跌至每袋1枚铜铢', '持平于每袋2枚铜铢'):
        rule = CHANGE.replace('涨至每袋4枚铜铢', change)
        assert read(rule, 'C00429') is None
    assert read(CHANGE.replace('减产使', '庆典使'), 'C00429') is None


def test_named_market_supply_and_demand_can_ground_value_without_inventing_quantities():
    supply = '盐帮从雾井运入灯盐，灯塔守夜人每夜领用灯盐，'
    for key, (rule, limits) in CASES.items():
        actual = rule.replace(FLOW, supply)
        assert read(actual, key, limits)['evidence']['supply'] == '盐帮从雾井运入灯盐'
        assert read(actual.replace('运入灯盐', '运入草盐'), key, limits) is None
    separated_cause = CHANGE.replace('减产使', '受本次减产影响，')
    assert read(separated_cause, 'C00429')['evidence']['valuation'] in separated_cause


def test_pending_currency_pair_can_share_a_card_with_an_independently_approved_resource_price():
    from nw.materials.world_exchange import approved_exchange

    pending = '北港钱市在封航期，灯币兑潮币的汇率待定。'
    rule = LEVEL + '灯币与潮币是北港钱市的通行货币。' + pending
    limits = LIMITS + '仅持北港商票者可在北港钱市将灯币兑换为潮币。'
    card = {'card_id': 'joint-market', 'kind': 'world', 'status': 'approved', 'version': 1,
            'body': {'rule': rule, 'limits': limits}}
    assert approved_exchange(card, 'C00542')['evidence']['rate_status'] == 'pending'
    assert approved_valuation(card, 'C00524')['evidence']['price'] == '3'
    assert approved_valuation(card, 'C00524')['rule'] == rule
    with pytest.raises(ValueError, match='C00524'):
        check_valuation_claims('C00524', rule, limits, ['封航期，北港盐市的灯盐市价为每袋九枚铜铢。'])
    assert read(rule + '灯盐估价待定。', 'C00524', limits) is None


def test_value_rank_uses_author_scale_and_stays_separate_from_price_movement():
    rule = LEVEL.replace('灯盐市价按每袋3枚铜铢', '灯盐以每旬供灯时长为尺度列为乙等')
    assert read(rule, 'C00524')['evidence']['valuation'] in rule
    assert read(rule, 'C00429') is None
    assert read(CHANGE, 'C00524') is None


@pytest.mark.parametrize('claim', [
    '封航期，北港盐市的灯盐市价为每袋 4 枚铜铢。',
    '账册证实在封航期的北港盐市，灯盐每袋售价为四枚铜铢。',
    '封航期，北港盐市的灯盐每两袋报价八枚铜铢。',
    '账册证实封航期，北港盐市的灯盐市价由每袋两枚铜铢涨至每两袋八枚铜铢。',
    '据说封航期，北港盐市的灯盐市价为每袋九枚铜铢。',
    '封航期，北港盐市的灯盐市价为每袋九枚铜铢？',
    '开航期，北港盐市的灯盐市价为每袋九枚铜铢。',
    '封航期，南港盐市的灯盐市价为每袋九枚铜铢。',
    '封航期，北港盐市的海盐市价为每袋九枚铜铢。',
    '船工前往北港核查盐票，未确认账面市价。',
])
def test_downstream_receipt_respects_quotation_scope_and_speaker(claim):
    check_valuation_claims('C00429', CHANGE, LIMITS, [claim])


@pytest.mark.parametrize('claim', [
    '封航期，北港盐市的灯盐市价为每袋九枚铜铢。',
    '封航期，北港盐市的灯盐市价为每箱四枚铜铢。',
    '账册证实在封航期的北港盐市，灯盐每袋售价九枚铜铢。',
    '北港盐市在封航期，灯盐每两袋现价为四枚铜铢。',
    '封航期，北港盐市的灯盐市价为每袋四枚银币。',
    '北港盐市在封航期，灯盐市价由每袋三枚铜铢涨至每袋四枚铜铢。',
    '北港盐市在封航期，灯盐市价由每袋两枚铜铢降至每袋四枚铜铢。',
])
def test_receipt_rejects_an_altered_market_quote(claim):
    with pytest.raises(ValueError, match='C00429'):
        check_valuation_claims('C00429', CHANGE, LIMITS, [claim])


def test_grade_cannot_supply_a_price_at_the_same_market():
    graded = LEVEL.replace('灯盐市价按每袋3枚铜铢', '灯盐以每旬供灯时长为尺度列为乙等')
    with pytest.raises(ValueError, match='C00524'):
        check_valuation_claims('C00524', graded, LIMITS, ['封航期，北港盐市的灯盐市价为每袋3枚铜铢。'])


def test_a_separate_rule_on_the_same_card_does_not_dilute_the_price_evidence():
    other_rule = '船厂在退潮后重新开放东门。'
    assert read(LEVEL + other_rule, 'C00524')['evidence']['price'] == '3'
    assert read(LEVEL + '实际市价变更为每袋九枚铜铢。', 'C00524') is None
    assert read(LEVEL + LEVEL, 'C00524') is None


@pytest.mark.parametrize('word', ['枚', '枚货币'])
def test_value_requires_a_named_tender_or_an_explicit_currency_unit(word):
    assert read(LEVEL.replace('枚铜铢', word), 'C00524') is None
