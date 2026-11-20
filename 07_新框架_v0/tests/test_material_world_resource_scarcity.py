"""Project accounts distinguish production balance, scarcity grades and actual regeneration."""
import pytest

from nw.materials.world_resource_scarcity import approved_scarcity


LIMIT = '青盐的供需核算仅适用于北港封航期。'
PRODUCTION = '封航期，北港的青盐每旬产出30袋，消耗45袋，当地出现短缺'
ALTERNATIVE = '每袋青盐可用两袋灰盐替代'
REFILL = '仅在冰渠解冻后可从南埠盐田补充青盐'
MARKET = '北港在封航期，青盐每旬供给30袋，需求45袋，青盐属于灯用耗材'
GRADE = '青盐定为中度稀缺'
CHANNEL = '只能通过引盐所取得'
DORMANT = '本期青盐停止再生'
CASES = {
    'C00483': (PRODUCTION + '，' + ALTERNATIVE + '。', LIMIT),
    'C00529': ('，'.join((MARKET, GRADE, CHANNEL, REFILL)) + '。', LIMIT),
    'C00562': ('，'.join((PRODUCTION, DORMANT, REFILL)) + '。', LIMIT),
}


def proof(key, rule, limit=LIMIT):
    return approved_scarcity({'card_id': 'port-accounts', 'kind': 'world', 'version': 2,
                              'status': 'approved', 'body': {'rule': rule, 'limits': limit}}, key)


@pytest.mark.parametrize('key', CASES)
def test_adoption_keeps_original_scope_and_amounts(key):
    rule, limits = CASES[key]
    chosen = proof(key, rule, limits)
    assert (chosen['rule'], chosen['limits'], chosen['version']) == (rule, limits, 2)
    assert chosen['evidence']['account'] == rule.rstrip('。')
    assert chosen['evidence']['boundary'] == limits.rstrip('。')


@pytest.mark.parametrize(('level','basis'), [
    ('极端稀缺', '全书仅有三位持有者'), ('高度稀缺', '仅由顶层势力潮廷掌控'),
    ('中度稀缺', CHANNEL), ('轻度稀缺', '在北港市集流通但须出示盐票'),
    ('自由流通', '在北港市集自由买卖且无需许可'),
])
def test_published_grade_requires_corresponding_access_basis(level, basis):
    rule = '，'.join((MARKET, '青盐定为' + level, basis, REFILL))
    assert proof('C00529', rule)['evidence']['access'] == basis


@pytest.mark.parametrize(('key','old','changed'), [
    ('C00483', '消耗45袋', '消耗15袋'), ('C00483', '消耗45袋', '消耗45斤'),
    ('C00483', '消耗45袋', '灰盐消耗45袋'), ('C00483', '消耗45袋', '每年消耗45袋'),
    ('C00483', '两袋灰盐', '两袋青盐'), ('C00483', ALTERNATIVE, '可用其他资源代替'),
    ('C00529', '青盐属于灯用耗材', '灰盐属于灯用耗材'),
    ('C00529', '属于灯用耗材', '属于青盐'), ('C00529', '中度稀缺', '极端稀缺'), ('C00529', CHANNEL, '全书仅有两位持有者'),
    ('C00529', CHANNEL, '只有北港的集市准入制度'), ('C00529', '补充青盐', '补充灰盐'),
    ('C00562', '30袋', '50袋'), ('C00562', DORMANT, '本期灰盐停止再生'),
    ('C00562', REFILL, '以后予以补充'), ('C00562', '当地出现短缺', '当期盈余'),
])
def test_incomplete_or_contradictory_author_basis(key, old, changed):
    original = CASES[key][0]
    assert old in original
    assert proof(key, original.replace(old, changed)) is None


def test_relative_balance_and_isolated_periods():
    rule = '封航期，北港的青盐按袋核算，产量持续低于同期消耗量，当地出现短缺，' + ALTERNATIVE
    assert proof('C00483', rule)
    assert proof('C00483', rule.replace('低于', '高于')) is None
    assert proof('C00483', rule, LIMIT.replace('封航期', '开港期')) is None


def test_joint_balance_and_cycle_on_one_account_keep_both_bases():
    rule = '，'.join((PRODUCTION, ALTERNATIVE, DORMANT, REFILL))
    assert proof('C00483', rule)['evidence']['alternative'] == ALTERNATIVE
    assert proof('C00562', rule)['evidence']['regeneration'] == DORMANT
    assert proof('C00562', rule + '，青盐每旬再生80袋') is None


def test_separate_products_on_one_card_can_support_their_own_rules():
    supply, balance = CASES['C00529'][0], CASES['C00483'][0].replace('青盐', '黑盐')
    limits = LIMIT + LIMIT.replace('青盐', '黑盐')
    joined = supply + balance
    assert proof('C00483', joined, limits)['evidence']['account'] == balance.rstrip('。')
    assert proof('C00529', joined, limits)['evidence']['account'] == supply.rstrip('。')
    same_item = CASES['C00483'][0] + supply
    assert proof('C00529', same_item)
    assert proof('C00483', same_item)


def test_explicit_same_resource_across_sentences_and_foreign_scope():
    rule = PRODUCTION + '。' + ALTERNATIVE + '。'
    assert proof('C00483', rule)['evidence']['account'] == rule.rstrip('。')
    assert proof('C00483', rule.replace('。每袋', '。铁矿改道。每袋')) is None
    assert proof('C00529', '，'.join((MARKET, GRADE, '此处改述灰盐', CHANNEL, REFILL))) is None
    assert proof('C00529', '，'.join((MARKET, GRADE, CHANNEL, '直接自由买卖', REFILL))) is None


def test_cycle_scarcity_includes_effective_regeneration_in_the_same_period():
    rule = '封航期，北港的青盐每旬新产30袋，消耗45袋，青盐每旬再生5袋，当地出现短缺，' + REFILL
    assert proof('C00562', rule)['evidence']['regeneration'] == '青盐每旬再生5袋'
    assert proof('C00562', rule.replace('再生5袋', '再生20袋')) is None
    assert proof('C00562', rule.replace('每旬再生', '每年再生')) is None
    assert proof('C00562', rule.replace('当地出现短缺', DORMANT + '，当地出现短缺')) is None


@pytest.mark.parametrize('limit', ['青盐核算待定。', '灰盐的供需核算仅适用于北港封航期。',
                                    '青盐的供需核算仅适用于北港封航期。本规则已撤销。'])
def test_boundary_and_approval_must_cover_this_resource(limit):
    assert proof('C00483', CASES['C00483'][0], limit) is None
