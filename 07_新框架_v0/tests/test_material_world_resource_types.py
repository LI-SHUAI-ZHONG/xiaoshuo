"""Regression coverage for named resource identities and their acquisition evidence."""
import pytest

from nw.materials.world_resource_types import RULES, approved_resource_type


LIMIT = '仅持井票的盐工可采集雾晶。'
CASES = {
    'C00060': ('凝聚态资源雾晶采自雾井，封蜡后储存在北仓冰柜，点灯时每次消耗一枚雾晶。', LIMIT),
    'C00467': ('雾晶属于照明资源，产自潮汐湿地的底栖层，只在东湾盐沼退潮后可采集雾晶。', LIMIT),
    'C00478': ('雾晶属于照明资源，从雾井沿北渠运往港仓，北渠闸门关闭时港仓无法取得雾晶。', LIMIT),
    'C00527': ('雾晶属于照明资源，产自东湾盐沼，凭井票才可用滤晶网采集雾晶。', LIMIT),
    'C00569': ('雾晶属于照明资源，在东湾盐沼通过采集取得雾晶，采集雾晶须持井票，'
               '每次采集耗用一片滤膜，采集时遇涨潮可能导致滤架倾覆。', LIMIT),
    'C00844': ('雾晶属于照明资源，只有盐工在东湾盐沼凭井票才可采集雾晶。', LIMIT),
}


def card(rule: str, limits: str) -> dict:
    return {'kind': 'world', 'status': 'approved', 'card_id': 'salt-marsh', 'version': 4,
            'body': {'rule': rule, 'limits': limits}}


@pytest.mark.parametrize('key', CASES)
def test_approved_resource_preserves_specific_card_fields(key: str) -> None:
    rule, limit = CASES[key]
    result = approved_resource_type(card(rule, limit), key)
    assert result and result['rule'] == rule and result['limits'] == limit and result['version'] == 4
    assert result['rule_ref'] == 'approved:salt-marsh:/body/rule'
    assert result['limits_ref'] == 'approved:salt-marsh:/body/limits'
    assert all(piece in rule or piece in limit for piece in result['evidence'].values())
    assert set(CASES) == set(RULES)


@pytest.mark.parametrize(('key', 'before', 'after'), [
    ('C00060', '凝聚态资源', '游离态资源'),
    ('C00060', '采自雾井', '采自某地'),
    ('C00060', '封蜡后', ''),
    ('C00060', '北仓冰柜', '指定容器'),
    ('C00060', '点灯时', ''),
    ('C00060', '一枚雾晶', '一枚灯芯'),
    ('C00060', '封蜡后', '另有灯芯，封蜡后'),
    ('C00467', '照明资源', '某种资源'),
    ('C00467', '潮汐湿地的底栖层', '南湾湿地'),
    ('C00467', '东湾盐沼', '某地'),
    ('C00467', '退潮后', ''),
    ('C00467', '可采集雾晶', '可采集芦芯'),
    ('C00478', '沿北渠', ''),
    ('C00478', '运往港仓', '运往雾井'),
    ('C00478', '北渠闸门关闭', '南城城门关闭'),
    ('C00478', '时港仓无法', '时南岭无法'),
    ('C00527', '产自东湾盐沼，', ''),
    ('C00527', '井票', '指定权限'),
    ('C00527', '滤晶网', '相应工具'),
    ('C00527', '采集雾晶', '采集芦芯'),
    ('C00569', '取得雾晶', '取得芦芯'),
    ('C00569', '须持井票', '须持相应凭证'),
    ('C00569', '每次采集', '每次购买'),
    ('C00569', '一片滤膜', '相应费用'),
    ('C00569', '采集时遇涨潮可能导致滤架倾覆', '采集情况待确认'),
    ('C00844', '只有盐工', '只有任何人'),
    ('C00844', '东湾盐沼', '某地'),
    ('C00844', '井票', '指定权限'),
    ('C00844', '采集雾晶', '采集芦芯'),
])
def test_missing_or_unrelated_resource_details_cannot_qualify(key: str, before: str, after: str) -> None:
    rule, limit = CASES[key]
    assert before in rule
    assert approved_resource_type(card(rule.replace(before, after), limit), key) is None


@pytest.mark.parametrize('limit', [
    '持井票者可以展示雾晶图纸。',
    '仅持井票的盐工可采集芦芯。',
    '仅持井票的盐工可采集雾晶。上述规则已取消。',
    '待定。',
    '仅符合条件者可采集雾晶。',
])
def test_boundaries_are_actual_permissions_for_this_resource(limit: str) -> None:
    for key, (rule, _) in CASES.items():
        assert approved_resource_type(card(rule, limit), key) is None


def test_multiple_contradictory_rules_or_unapproved_issuer_stay_pending() -> None:
    key = 'C00527'
    rule, limit = CASES[key]
    assert approved_resource_type(card(rule + rule.replace('井票', '矿票'), limit), key) is None
    assert approved_resource_type({**card(rule, limit), 'status': 'draft'}, key) is None


def test_same_item_can_be_described_in_several_sentences() -> None:
    rule = '雾晶属于照明资源。雾晶产自东湾盐沼。凭井票才可用滤晶网采集雾晶。'
    assert approved_resource_type(card(rule, LIMIT), 'C00527')
    assert approved_resource_type(card(rule.replace('雾晶产自', '芦芯产自'), LIMIT), 'C00527') is None
    assert approved_resource_type(card(rule.replace('雾晶产自', '该资源产自'), LIMIT), 'C00527')


def test_unquantified_cost_has_no_resource_basis() -> None:
    rule, limit = CASES['C00569']
    assert approved_resource_type(card(rule.replace('一片滤膜', '很多'), limit), 'C00569') is None


def test_another_items_storage_and_a_beneficial_result_are_not_resource_evidence() -> None:
    rule, limits = CASES['C00060']
    assert approved_resource_type(card(rule.replace('封蜡后', '芦芯封蜡后'), limits), 'C00060') is None
    rule, limits = CASES['C00569']
    assert approved_resource_type(card(rule.replace('滤架倾覆', '按时完工'), limits), 'C00569') is None


def test_named_unpriced_payment_and_author_named_harvest_condition() -> None:
    rule, limits = CASES['C00569']
    assert approved_resource_type(card(rule.replace('一片滤膜', '芦叶滤膜'), limits), 'C00569')
    rule, limits = CASES['C00467']
    assert approved_resource_type(card(rule.replace('东湾盐沼退潮后', '东湾盐沼待晶苔返青后'), limits), 'C00467')
