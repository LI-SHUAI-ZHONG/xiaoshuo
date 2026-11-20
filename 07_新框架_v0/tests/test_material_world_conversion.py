"""Check conversion evidence preserved from an approved world card."""
from copy import deepcopy

import pytest

from nw.materials.world_conversion import RULES, approved_conversion


FREE = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
FREE_LIMIT = '仅在井内封印完好且滤晶匣验标后使用，松封时停止摄取。'
CONDENSED = '凝聚态灵液，经温差匣压制，转化为固化态赤曜晶。'
CONDENSED_LIMIT = '仅在温差匣验标后启动。'
SOLID = '矿卫持有的固化态赤曜晶，经寒熔炉熔解，转化为凝聚态赤曜液。'
SOLID_LIMIT = '仅在寒熔炉点火温度达标后启动，未领牌者不得持有赤曜晶。'
YIELD = '本路径转化效率按有效产出/投入计算。'
LOSS = '本路径转化损耗率按损耗量/投入量计。'
BALANCE = '本路径每批由湿雾井投入10灵值，灵液产出8灵值，剩余2灵值通过冷凝管回收。'


def _card(rule: str, limits: str = FREE_LIMIT, **extra: object) -> dict:
    return {'card_id': 'energy-world', 'kind': 'world', 'status': 'approved', 'version': 4,
            'body': {'rule': rule, 'limits': limits}, **extra}


@pytest.mark.parametrize(('key', 'rule', 'limits', 'evidence_key'), [
    ('C00050', FREE, FREE_LIMIT, 'environment'),
    ('C00058', CONDENSED, CONDENSED_LIMIT, 'path'),
    ('C00061', SOLID, SOLID_LIMIT, 'holding'),
    ('C00064', FREE + YIELD + LOSS, FREE_LIMIT, 'efficiency'),
    ('C00106', FREE + BALANCE, FREE_LIMIT, 'conservation'),
    ('C00409', FREE + BALANCE, FREE_LIMIT, 'conservation'),
])
def test_exact_approved_path_and_complete_boundary_survive_handoff(
        key: str, rule: str, limits: str, evidence_key: str) -> None:
    card = _card(rule, limits)
    snapshot = deepcopy(card)
    proof = approved_conversion(card, key)
    assert proof is not None, RULES[key]
    assert proof['card_id'] == 'energy-world' and proof['version'] == 4
    assert proof['rule'] == rule and proof['limits'] == limits
    assert proof['rule_ref'] == 'approved:energy-world:/body/rule'
    assert proof['limits_ref'] == 'approved:energy-world:/body/limits'
    assert evidence_key in proof['evidence']
    assert all(quote in rule or quote in limits for quote in proof['evidence'].values())
    assert snapshot == card


@pytest.mark.parametrize('measurements', [YIELD + BALANCE, BALANCE + YIELD, LOSS + BALANCE, BALANCE + LOSS])
def test_one_approved_path_can_supply_efficiency_and_both_conservation_edges(measurements: str) -> None:
    card = _card(FREE + measurements)
    for key in ('C00064', 'C00106', 'C00409'):
        proof = approved_conversion(card, key)
        assert proof is not None
        assert proof['evidence']['conservation'] == BALANCE.rstrip('。')
    rate = approved_conversion(card, 'C00064')['evidence']
    if LOSS in measurements:
        assert rate['loss_rate'] == LOSS.rstrip('。')
        assert 'efficiency' not in rate
    else:
        assert rate['efficiency'] == YIELD.rstrip('。')
        assert 'loss_rate' not in rate


def test_single_batch_conservation_preserves_exact_decimal_and_distinct_destinations() -> None:
    ledger = '本路径每次由湿雾井投入１．０灵值，灵液有效产出0.65灵值，余下0.15灵值经冷凝管回收，散失0.20灵值散入蓄热墙。'
    proof = approved_conversion(_card(FREE + ledger), 'C00409')
    assert proof is not None
    assert proof['evidence']['conservation'] == ledger.rstrip('。')


@pytest.mark.parametrize(('key', 'rule', 'limits'), [
    ('C00050', '游离态灵雾，经滤晶匣摄取，转化为凝聚态灵液。', FREE_LIMIT),
    ('C00050', FREE.replace('摄取', '记录'), FREE_LIMIT),
    ('C00050', FREE.replace('凝聚态灵液', '灵液'), FREE_LIMIT),
    ('C00050', FREE.replace('凝聚态灵液', '游离态青雾'), FREE_LIMIT),
    ('C00050', FREE.replace('湿雾井中的', '湿雾井中的能量并非'), FREE_LIMIT),
    ('C00050', FREE.replace('湿雾井中的', '宁可弃用湿雾井中的'), FREE_LIMIT),
    ('C00050', '游离态灵雾散布在湿雾井，滤晶匣用于记录风向。另一动作把固化晶片制成灵液。', FREE_LIMIT),
    ('C00050', CONDENSED, CONDENSED_LIMIT),
    ('C00050', FREE, '本作不采用这条路径。' + FREE_LIMIT),
    ('C00050', FREE.replace('湿雾井中的', '例如湿雾井中的'), FREE_LIMIT),
    ('C00050', FREE, '仅在滤晶匣达到待核条件后使用。'),
    ('C00050', FREE, '仅在滤晶匣验标后展示备选图纸。'),
    ('C00050', FREE, '滤晶匣仅在满足调用条件时使用。'),
    ('C00050', FREE, FREE_LIMIT + '滤晶匣永久封停，滤晶匣不得在本项目任何情形下使用。'),
    ('C00058', CONDENSED, '仅在温差匣关闭后启动档案馆。'),
    ('C00058', CONDENSED, '温差匣仅考虑用来恒温。'),
    ('C00058', CONDENSED.replace('温差匣压制', '某种装置'), CONDENSED_LIMIT),
    ('C00058', CONDENSED.replace('固化态赤曜晶', '某种新状态'), CONDENSED_LIMIT),
    ('C00061', SOLID, '仅在寒熔炉点火温度达标后启动。'),
    ('C00061', SOLID, '未领牌者不得持有赤曜晶。'),
    ('C00061', SOLID.replace('寒熔炉熔解', '寒熔炉'), SOLID_LIMIT),
    ('C00064', FREE + YIELD, FREE_LIMIT),
    ('C00064', FREE + LOSS, FREE_LIMIT),
    ('C00064', FREE + '转化效率按有效产出/投入计算。' + BALANCE, FREE_LIMIT),
    ('C00064', FREE + '染料蒸煮路径的转化效率按有效产出/投入计算。' + BALANCE, FREE_LIMIT),
    ('C00064', FREE + '本路径转化效率为80%。' + BALANCE, FREE_LIMIT),
    ('C00064', FREE + YIELD + '本路径转化效率按投入/有效产出计算。' + LOSS, FREE_LIMIT),
    ('C00064', FREE + '本路径转化效率按损耗量/投入量计算。' + BALANCE, FREE_LIMIT),
    ('C00106', FREE + '每批由另一口井投入10灵值，灵液产出8灵值，余下2灵值由冷凝管回收。', FREE_LIMIT),
    ('C00106', FREE + '另一口井每批投入10灵值，灵液产出8灵值，余下2灵值由冷凝管回收。', FREE_LIMIT),
    ('C00106', FREE + BALANCE.replace('灵液产出', '晶核产出'), FREE_LIMIT),
    ('C00106', FREE + BALANCE.replace('剩余2灵值', '剩余1灵值'), FREE_LIMIT),
    ('C00106', FREE + BALANCE.replace('通过冷凝管回收', '转入指定装置'), FREE_LIMIT),
    ('C00106', FREE + BALANCE.replace('通过冷凝管回收', '凭空消失'), FREE_LIMIT),
    ('C00106', FREE + BALANCE.replace('灵液产出', '每月灵液产出'), FREE_LIMIT),
    ('C00409', FREE + BALANCE.replace('由湿雾井投入10灵值', '由湿雾井投入10热格'), FREE_LIMIT),
    ('C00409', FREE + BALANCE.replace('，剩余2灵值通过冷凝管回收', ''), FREE_LIMIT),
    ('C00409', FREE + '例行巡检另有标准。' + BALANCE, FREE_LIMIT),
])
def test_incomplete_unapproved_or_unrelated_conversion_details_remain_waiting(
        key: str, rule: str, limits: str) -> None:
    assert approved_conversion(_card(rule, limits), key) is None


def test_proof_requires_a_valid_approved_world_card_and_does_not_borrow_fields() -> None:
    assert approved_conversion(_card(FREE, ''), 'C00050') is None
    assert approved_conversion(_card('', FREE_LIMIT), 'C00050') is None
    for invalid in ({'status': 'draft'}, {'kind': 'character'}, {'body': None},
                    {'card_id': ''}, {'version': True}, {'version': 0}):
        assert approved_conversion(_card(FREE, **invalid), 'C00050') is None
    assert approved_conversion(_card(FREE + BALANCE), 'C00066') is None
