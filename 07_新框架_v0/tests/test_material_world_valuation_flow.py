"""Verify approved local prices in the plot fields a persisted valuation receipt cites."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from nw.materials.phase_projection import verify_chain
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from nw.tasks import read_input_manifest
from story_fixture import baseline
from test_material_workflow import choose
from test_material_world_conversion_flow import (
    SELECTED_GENRE, ApprovedWorldModel, WorldRuleCase, _approved_card, _catalog, assert_world_flow,
)
from test_novel_flow import config
from test_material_world_market import CASES


CHANGE = WorldRuleCase(
    kind='market', policy_key='world_market_policy', policy='world-market-prerequisites-v1',
    dynamic_key='C00429', static_key='18.2_资源产量减少 / 24.3_价值动态 / 转化', condition='产量减少→价值上升',
    effect='当起点成立并满足转化条件时，将起点状态转为终点状态。',
    rule=CASES['C00429'][0], limits=CASES['C00429'][1], waiting_reason='减产', title='封航期的灯盐减产',
    choice='[FAKE] 封航期，北港盐市的灯盐市价为每袋四枚铜铢。',
    observable='[FAKE] 盐商在北港市集核对本旬灯盐成交价与雾盐到货账。',
    check='[FAKE] 对照北港封航期的灯盐簿，检查减产前后按袋计价，保留铜铢币种。',
    changed_rule=CASES['C00429'][0].replace('每袋4枚铜铢', '每袋9枚铜铢'),
    changed_limits='灯盐估价仅适用于西港盐市封航期。',
    expected_evidence=(('market', '北港盐市'), ('resource', '灯盐'), ('period', '封航期')),
)
LEVEL = replace(
    CHANGE, dynamic_key='C00524', static_key='24.1_资源类型 / 24.2_资源价值 / 转化', condition='类型决定价值',
    rule=CASES['C00524'][0], limits=CASES['C00524'][1], waiting_reason='价值', title='封航期的灯盐估价',
    choice='[FAKE] 封航期，北港盐市的灯盐市价为每袋三枚铜铢。',
    changed_rule=CASES['C00524'][0].replace('每袋3枚铜铢', '每袋9枚铜铢'),
)


@pytest.mark.parametrize('case', [CHANGE, LEVEL], ids=['price-after-yield-loss', 'resource-value'])
def test_wrong_price_in_reopened_plot_field_is_rejected_even_after_rehash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: WorldRuleCase,
) -> None:
    assert_world_flow(tmp_path, monkeypatch, case, case.rule, SELECTED_GENRE, False)
    with Store(tmp_path / 'project', test_mode=True) as store:
        row = store.connection.execute(
            "SELECT id FROM input_manifests WHERE json_type(package_json,'$.material_work.stages')='array' "
            "ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        assert row
        _, package = read_input_manifest(store, row['id'])
    session = deepcopy(package['material_work'])
    plot = next(stage for stage in session['stages'] if stage['stage'] == 'plot_design')
    assert plot['products']['directions'][0]['choice'] == case.choice
    receipts = plot['products']['_receipts']
    assert receipts and all(r['output_refs'] == ['/directions/0/choice'] for r in receipts)
    wrong_claims = ['[FAKE] 封航期，北港盐市的灯盐市价为每袋九枚铜铢。']
    if case.dynamic_key == 'C00429':
        wrong_claims.extend((
            '[FAKE] 听说外地缺盐，但账册证实封航期，北港盐市的灯盐市价为每袋九枚铜铢。',
            '[FAKE] 封航期，北港盐市的灯盐市价为每袋九枚铜铢，船工否认那句传言。',
        ))
    for wrong in wrong_claims:
        plot['products']['directions'][0]['choice'] = wrong
        plot['sha256'] = content_sha256(plot['products'])
        with pytest.raises(ValueError, match=case.dynamic_key + ' 下游产物所述当地市价'):
            verify_chain(session)


def test_actual_plot_job_cannot_publish_an_invented_local_price(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = replace(CHANGE, choice='[FAKE] 封航期，北港盐市的灯盐市价为每袋九枚铜铢。')
    static, derived = _catalog(tmp_path, monkeypatch, (case,))[case.dynamic_key]
    model = ApprovedWorldModel(case, static, derived, genre=SELECTED_GENRE, eligible=True, waiting=False)
    path = tmp_path / 'project'
    with Store(path, create=True, test_mode=True) as store:
        store.init_project(case.title)
        store.add_brief('验证批准的灯盐估价能否限制剧情中的明确成交判断。')
        card = _approved_card(store, case.rule, case.limits, case.title)
        adopt_story(store, baseline(card_refs=[card]), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500)))
        result = resume_job(store, job.id, model, config(store), choose)
        assert result.status == 'BLOCKED' and 'C00429 下游产物所述当地市价' in result.reason
        assert 'proposal_id' not in result.outputs
    with Store(path, test_mode=True) as store:
        saved = store.connection.execute('SELECT status,reason FROM novel_jobs WHERE id=?', (job.id,)).fetchone()
        assert saved['status'] == result.status and saved['reason'] == result.reason


@pytest.mark.parametrize('claim', [
    '[FAKE] 封航期，南港盐市的灯盐市价为每袋九枚铜铢。',
    '[FAKE] 船工听说，封航期，北港盐市的灯盐市价为每袋九枚铜铢。',
], ids=['different-market', 'character-rumour'])
def test_other_market_and_unverified_price_are_not_the_approved_market_price(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claim: str,
) -> None:
    case = replace(CHANGE, choice=claim)
    assert_world_flow(tmp_path, monkeypatch, case, case.rule, SELECTED_GENRE, False)
