"""World cards must support every participating resource and actual hand-off."""
import pytest

from nw.materials.world_resource_cycle import RULES, approved_resource_cycle


PATH = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
PRODUCTION = '滤晶匣产出的灵液存入青瓷仓。'
USE = '灯塔从青瓷仓领用灵液点灯。'
RENEW = '回雾池用熄灯后的余汽再生灵液，送回青瓷仓。'
CYCLE = PRODUCTION + USE + RENEW
CONVERSION_RULE = PATH + CYCLE
CONVERSION_LIMITS = '仅在井内封印完好且滤晶匣验标后使用，松封时停止摄取。'
FLOW = '灵液从滤晶匣沿雾渠运至青瓷仓。'
FLOW_RULE = CYCLE + FLOW
FLOW_LIMITS = '仅在东闸验封后才可沿雾渠运送灵液。'
LOSS = '灵液在青瓷仓每夜蒸散一成。'
STORAGE_RULE = CYCLE + LOSS
STORAGE_LIMITS = '仅凭港务灯票方可从青瓷仓支取灵液。'


def card(rule: str, limits: str) -> dict:
    return {'card_id': 'harbor', 'version': 2, 'kind': 'world', 'status': 'approved',
            'body': {'rule': rule, 'limits': limits}}


@pytest.mark.parametrize(('key', 'rule', 'limits', 'detail'), [
    ('C00066', CONVERSION_RULE, CONVERSION_LIMITS, 'path'),
    ('C00479', FLOW_RULE, FLOW_LIMITS, 'route'),
    ('C01763', STORAGE_RULE, STORAGE_LIMITS, 'loss'),
])
def test_preserve_cycle_and_distinct_source_evidence(key, rule, limits, detail):
    result = approved_resource_cycle(card(rule, limits), key)
    assert result['rule'] == rule and result['limits'] == limits
    assert result['rule_ref'] == 'approved:harbor:/body/rule'
    assert result['limits_ref'] == 'approved:harbor:/body/limits' and result['version'] == 2
    evidence = result['evidence']
    assert evidence['resource'] == '灵液' and evidence[detail] in rule
    for part in ('production', 'storage', 'consumption', 'regeneration'):
        assert evidence[part] in rule
    assert evidence['boundary'] in limits


@pytest.mark.parametrize('key', list(RULES))
def test_joint_card_passes_and_retains_separate_source_proofs(key):
    rule = CONVERSION_RULE + FLOW + LOSS
    limits = CONVERSION_LIMITS + FLOW_LIMITS + STORAGE_LIMITS
    assert approved_resource_cycle(card(rule, limits), key)['rule'] == rule


@pytest.mark.parametrize(('before', 'after'), [
    (PRODUCTION, '工人只在巡查时讨论过灵液。'), (USE, ''), (RENEW, ''),
    ('滤晶匣产出', '盐井口产出'), ('领用灵液', '领用金砂'),
    ('再生灵液', '再生青盐'), ('送回青瓷仓', '送回别处仓'),
    ('灯塔从青瓷仓', '灯塔从黑盐仓'), ('回雾池用', '反例：回雾池用'),
    ('转化为可储存的凝聚态灵液', '尚未确定最后产物'),
    ('灵雾，经滤晶匣', '灵雾，拟议经滤晶匣'), ('游离态灵雾', '凝聚态灵雾'),
])
def test_conversion_cannot_fill_missing_parts_or_join_foreign_resource(before, after):
    rule = CONVERSION_RULE.replace(before, after)
    assert approved_resource_cycle(card(rule, CONVERSION_LIMITS), 'C00066') is None


def test_ordinary_separate_sentences_and_a_transformation_at_consumption():
    rule = ('雾坊生产灵液。灵液存入青瓷仓。灯塔从青瓷仓领用灵液供温差匣转化为赤曜晶。'
            + RENEW + '凝聚态灵液，经温差匣压制，转化为固化态赤曜晶。')
    result = approved_resource_cycle(card(rule, '仅在温差匣验标后启动。'), 'C00066')
    assert result['evidence']['attached_stage'] == '灯塔从青瓷仓领用灵液供温差匣转化为赤曜晶'


@pytest.mark.parametrize(('route', 'limits'), [
    (FLOW.replace('青瓷仓', '染坊仓'), FLOW_LIMITS),
    (FLOW.replace('滤晶匣沿雾渠运至青瓷仓', '青瓷仓沿雾渠运至滤晶匣'), FLOW_LIMITS),
    (FLOW.replace('雾渠', '指定路线'), FLOW_LIMITS.replace('雾渠', '指定路线')),
    (FLOW.replace('灵液从', '红砂从'), FLOW_LIMITS),
    (FLOW, FLOW_LIMITS.replace('灵液', '红砂')), (FLOW, FLOW_LIMITS.replace('雾渠', '西渠')),
    (FLOW, '仅在雾渠验标后展示灵液路线图。'), (FLOW, '仅在符合条件后才可沿雾渠运送灵液。'),
])
def test_flow_keeps_same_resource_route_condition_and_direction(route, limits):
    assert approved_resource_cycle(card(CYCLE + route, limits), 'C00479') is None


@pytest.mark.parametrize(('rule', 'limits'), [
    (CYCLE, STORAGE_LIMITS), (CYCLE + LOSS.replace('灵液', '青盐'), STORAGE_LIMITS),
    (CYCLE + LOSS.replace('青瓷仓', '白瓷仓'), STORAGE_LIMITS),
    (CYCLE + LOSS.replace('一成', '若干'), STORAGE_LIMITS),
    (STORAGE_RULE, STORAGE_LIMITS.replace('灵液', '盐晶')),
    (STORAGE_RULE, STORAGE_LIMITS.replace('青瓷仓', '盐井仓')),
    (STORAGE_RULE, '仅凭港务灯票方可从青瓷仓展示灵液。'),
    (STORAGE_RULE.replace('熄灯后的余汽', '材料'), STORAGE_LIMITS),
    (STORAGE_RULE.replace('送回青瓷仓', '补入南盐仓'), STORAGE_LIMITS),
])
def test_storage_requires_exact_loss_location_withdrawal_and_refill(rule, limits):
    assert approved_resource_cycle(card(rule, limits), 'C01763') is None


def test_approval_version_and_limits_come_from_same_card():
    valid = card(CONVERSION_RULE, CONVERSION_LIMITS)
    for change in ({'kind': 'character'}, {'version': True}, {'status': 'draft'}, {'card_id': ''},
                   {'body': {'rule': valid['body']['rule'], 'limits': ''}}):
        assert approved_resource_cycle({**valid, **change}, 'C00066') is None
    assert approved_resource_cycle(card(CONVERSION_RULE, FLOW_LIMITS), 'C00066') is None
    assert approved_resource_cycle(card(CONVERSION_RULE, CONVERSION_LIMITS), 'C00562') is None


@pytest.mark.parametrize('revoked', ['回雾池已经停止再生灵液。', '本项目已取消回雾池再生灵液。',
                                      '青瓷仓已经停止储存灵液。', '滤晶匣不再生产灵液。'])
def test_revoked_leg_blocks_even_when_earlier_sentences_still_describe_it(revoked):
    assert approved_resource_cycle(card(CONVERSION_RULE + revoked, CONVERSION_LIMITS), 'C00066') is None


def test_temporary_or_unrelated_withdrawal_preserves_approved_path():
    limits = CONVERSION_LIMITS + '封印破裂时停止回雾池再生灵液。回雾池已经停止再生红砂。'
    assert approved_resource_cycle(card(CONVERSION_RULE, limits), 'C00066')


def test_explicit_storage_link_can_place_transformation_between_production_and_storage():
    rule = (CONVERSION_RULE.replace('滤晶匣产出', '雾坊产出')
            + '灵液存入青瓷仓前须由滤晶匣将灵雾转化为灵液。')
    assert approved_resource_cycle(card(rule, CONVERSION_LIMITS), 'C00066')['evidence']['attached_stage'].endswith('转化为灵液')


def test_marked_example_cannot_supply_the_cycle():
    assert approved_resource_cycle(card('示例：雾坊的记述。' + STORAGE_RULE, STORAGE_LIMITS), 'C01763') is None


def test_explicit_refill_condition_anchors_non_temporal_regeneration_feed():
    rule = STORAGE_RULE.replace('熄灯后的余汽', '红杉木屑')
    limits = STORAGE_LIMITS + '仅在木料检验后才可将灵液补入青瓷仓。'
    assert approved_resource_cycle(card(rule, limits), 'C01763')['evidence']['refill'] in limits


@pytest.mark.parametrize('purpose', ['存放在陈列台', '用于展示点灯规章', '用于讨论', '暂存'])
def test_a_withdrawal_without_actual_consumption_does_not_complete_the_cycle(purpose):
    rule = CONVERSION_RULE.replace('领用灵液点灯', '领用灵液' + purpose)
    assert approved_resource_cycle(card(rule, CONVERSION_LIMITS), 'C00066') is None


def test_flow_accepts_punctuation_between_the_permit_and_the_operation():
    limits = '仅在东闸验封后，才可沿雾渠运送灵液。'
    assert approved_resource_cycle(card(FLOW_RULE, limits), 'C00479')['evidence']['boundary'] in limits


def test_resource_cannot_replenish_itself_as_its_only_named_input():
    rule = CONVERSION_RULE.replace('用熄灯后的余汽再生', '用灵液再生')
    assert approved_resource_cycle(card(rule, CONVERSION_LIMITS), 'C00066') is None


def test_withdrawn_transport_blocks_only_its_named_route():
    closed = '雾渠已经停止运送灵液。'
    assert approved_resource_cycle(card(FLOW_RULE + closed, FLOW_LIMITS), 'C00479') is None
    other_depot = '盐仓永久封存矿砂。'
    assert approved_resource_cycle(card(FLOW_RULE + other_depot, FLOW_LIMITS), 'C00479')


def test_explicit_rules_before_an_example_remain_verifiable():
    rule = FLOW_RULE + '示例：灵液从盐场沿西渠运至东宫。'
    result = approved_resource_cycle(card(rule, FLOW_LIMITS), 'C00479')
    assert result['rule'] == rule and result['evidence']['route'] in FLOW_RULE
