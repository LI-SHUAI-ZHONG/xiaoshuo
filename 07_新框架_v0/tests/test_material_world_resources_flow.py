"""Carry the resource cycle through material selection, plot receipts and persisted review."""
from pathlib import Path

import pytest

from nw.materials import phase_flow

from test_material_world_conversion_flow import CONVERSION, OTHER_GENRE, SELECTED_GENRE, WorldRuleCase, assert_world_flow


PRODUCTION = '湿雾井中的游离态灵雾，经滤晶匣在封闭条件下摄取，转化为可储存的凝聚态灵液。'
STORAGE = '滤晶匣产出的灵液存入青瓷仓。'
CONSUMPTION = '灯塔从青瓷仓领用灵液点灯。'
RENEWAL = '回雾池用熄灯后的余汽再生灵液，送回青瓷仓。'
COMPLETE_CYCLE = PRODUCTION + STORAGE + CONSUMPTION + RENEWAL
CYCLE = WorldRuleCase(
    kind='resource', policy_key='world_resource_policy', policy='world-resource-prerequisites-v1',
    dynamic_key='C00066', static_key='11.4_能量转化路径 / 27.1_资源循环 / 嵌套', condition='转化是循环环节',
    effect='当起点成立时，终点作为起点的一部分参与当前状态。',
    rule=COMPLETE_CYCLE, limits='仅在井内封印完好且滤晶匣验标后使用，松封时停止摄取。', waiting_reason='再生',
    choice='[FAKE] 灯塔停灯后，主角从青瓷仓的领用记录追到回雾池，查验余汽再生的灵液是否送回青瓷仓。',
    observable='[FAKE] 回雾池交还的灵液出现在青瓷仓回补清册，灯塔持有同批领用记录。',
    check='[FAKE] 将回补清册和灯塔领用批次逐项核验，核对余汽最终进入同一仓的时间。',
    changed_rule=COMPLETE_CYCLE.replace('送回青瓷仓', '送往铜砂场'), changed_limits='松封时停止摄取。',
    expected_evidence=(('resource', '灵液'), ('path', PRODUCTION.rstrip('。')), ('attached_stage', STORAGE.rstrip('。')),
                       ('consumption', CONSUMPTION.rstrip('。')), ('regeneration', RENEWAL.rstrip('。'))),
)


@pytest.mark.parametrize(
    ('rule', 'genre', 'legacy'),
    [
        (COMPLETE_CYCLE, SELECTED_GENRE, False),
        (PRODUCTION + STORAGE + CONSUMPTION, SELECTED_GENRE, False),
        (COMPLETE_CYCLE.replace('再生灵液', '再生墨盐'), SELECTED_GENRE, False),
        (COMPLETE_CYCLE.replace('滤晶匣产出', '雾泵产出'), SELECTED_GENRE, False),
        (COMPLETE_CYCLE, OTHER_GENRE, False),
        (COMPLETE_CYCLE, SELECTED_GENRE, True),
    ],
    ids=['approved-cycle', 'missing-renewal', 'other-renewed-resource', 'other-producer',
         'wrong-type', 'checkpoint-without-policy'],
)
def test_world_resource_cycle_reaches_persisted_plot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str, genre: tuple[str, str], legacy: bool,
) -> None:
    assert_world_flow(tmp_path, monkeypatch, CYCLE, rule, genre, legacy)


def test_resource_match_outside_first_page_can_be_searched_and_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    initial_page = phase_flow._sources

    def limited_page(desk, stage, *args, **kwargs):
        page = initial_page(desk, stage, *args, **kwargs)
        if stage == 'world_design':
            assert any(item['source']['key'] == CYCLE.dynamic_key for item in page)
            return [item for item in page if item['source']['key'] != CYCLE.dynamic_key]
        return page

    monkeypatch.setattr(phase_flow, '_sources', limited_page)
    assert_world_flow(tmp_path, monkeypatch, CYCLE, COMPLETE_CYCLE, SELECTED_GENRE, False, lookup=True)


def test_resource_cycle_and_conversion_share_one_approved_card_and_plot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_world_flow(tmp_path, monkeypatch, CYCLE, COMPLETE_CYCLE, SELECTED_GENRE, False, lookup=True, also_adopt=(CONVERSION,))
