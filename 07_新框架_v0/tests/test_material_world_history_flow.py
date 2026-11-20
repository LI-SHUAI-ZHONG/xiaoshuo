"""Verify that a frozen author history constrains the actual chosen plot direction."""
from dataclasses import replace

import pytest

from test_material_world_conversion_flow import OTHER_GENRE, SELECTED_GENRE, WorldRuleCase, assert_world_flow


HISTORY = '北港在创始期由港议会颁行《分仓令》。港历12年，港议会开通东栈航路，促使北港由创始期转入扩张期。'
TIMELINE = '该分期仅适用于北港的港历纪年。'
CANAL = '扩张期，北港因盐务司开凿支港，白沙航道由封闭改为通航。'
WATERS = '白沙航道的通行变更仅适用于北港扩张期。'
CHOICE = '[FAKE] 船工找出分仓令，将旧卷与港历十二年，北港由创始期转入扩张期的开港记录对照。'
ERR_YEAR = '已批准纪年不符'
WRONG = CHOICE.replace('十二年', '十五年')
MISSING = HISTORY.replace('港议会开通', '港议会计划开通')

TURN = WorldRuleCase(kind='history', policy_key='world_history_policy', policy='world-history-prerequisites-v1',
    dynamic_key='C00704', static_key='32.1_创始期 / 32.2_扩张期 / 演化', condition='创始→扩张',
    effect='当起点持续或变化时，推动终点按阶段发生状态变化。', rule=HISTORY, limits=TIMELINE, waiting_reason='创始',
    title='北港从创始到扩张的史实', choice=CHOICE, observable='[FAKE] 船工在港议会的旧令上找到开港记载。',
    check='[FAKE] 以分仓令的旧印和开通航路的纪年核对案卷。', changed_rule=MISSING, changed_limits='年表适用于南港。',
    expected_evidence=(('world','北港'), ('after','扩张期')))
ROUTE = replace(TURN, dynamic_key='C00708', static_key='32.2_扩张期 / 31.2_地理结构 / 转化',
    condition='扩张塑造地理', effect='当起点成立并满足转化条件时，将起点状态转为终点状态。',
    rule=CANAL, limits=WATERS, waiting_reason='扩张', title='北港白沙航道的变更',
    choice='[FAKE] 扩张期，北港的白沙航道已经通航。巡吏因此要求核对船工自称无路可走的证言。',
    observable='[FAKE] 巡吏找到白沙航道扩张期的领航簿。', check='[FAKE] 用北港的通航记录复核证人路线。',
    changed_rule=CANAL.replace('通航','禁行'), changed_limits=WATERS.replace('北港','南港'),
    expected_evidence=(('region','北港'), ('subject','白沙航道')))
CLOSED = '[FAKE] 扩张期，北港的白沙航道仍然封闭。巡吏据此排除船工乘船到场的可能。'


@pytest.mark.parametrize('rule,genre,legacy', [(MISSING, SELECTED_GENRE, False), (HISTORY, OTHER_GENRE, False),
                                             (HISTORY, SELECTED_GENRE, True)])
def test_unestablished_wrong_genre_or_legacy_history_stays_unavailable(tmp_path, monkeypatch, rule, genre, legacy):
    assert_world_flow(tmp_path, monkeypatch, TURN, rule, genre, legacy)


def test_world_timeline_reaches_the_actual_plot_and_cannot_change_in_a_sibling_field(tmp_path, monkeypatch):
    assert_world_flow(tmp_path, monkeypatch, TURN, HISTORY, SELECTED_GENRE, False,
                      altered_plot=(WRONG, ERR_YEAR), altered_sibling=(WRONG, ERR_YEAR))


@pytest.mark.parametrize('claim,reason', [
    (WRONG, ERR_YEAR),
    ('[FAKE] 主角决定改变计划，请船工带领众人到隔壁仓库翻找旧物。', '缺少本项目的历史依据'),
])
def test_history_receipt_cannot_claim_unrelated_or_altered_plot_as_actual_use(tmp_path, monkeypatch, claim, reason):
    case = replace(TURN, choice=claim)
    assert_world_flow(tmp_path, monkeypatch, case, HISTORY, SELECTED_GENRE, False, rejection=reason)


def test_adopt_founding_timeline_and_expanded_waterway_from_one_card(tmp_path, monkeypatch):
    rule, limits = HISTORY + CANAL, TIMELINE + WATERS
    start, geography = (replace(case, rule=rule, limits=limits) for case in (TURN, ROUTE))
    from nw.materials import phase_flow

    # Simulate an initial page already occupied by other sources, preserving real search and read.
    initial = phase_flow._sources
    def first_page(desk, stage, *args, **kwargs):
        rows = initial(desk, stage, *args, **kwargs)
        return [row for row in rows if row['source']['key'] != 'C00708'] if stage == 'world_design' else rows
    monkeypatch.setattr(phase_flow, '_sources', first_page)
    assert_world_flow(tmp_path, monkeypatch, geography, rule, SELECTED_GENRE, False, lookup=True,
                      also_adopt=(start,), altered_sibling=(CLOSED, 'C00708'))


def test_two_approved_dates_for_the_same_transition_stay_out_of_production(tmp_path, monkeypatch):
    case = replace(TURN, waiting_reason='冲突')
    assert_world_flow(tmp_path, monkeypatch, case, HISTORY, SELECTED_GENRE, False,
                      extra_card=(HISTORY.replace('12年', '15年'), TIMELINE), expected_ready=False)


def test_a_cited_geographical_change_cannot_be_reversed_in_an_actual_job(tmp_path, monkeypatch):
    case = replace(ROUTE, choice=CLOSED)
    assert_world_flow(tmp_path, monkeypatch, case, CANAL, SELECTED_GENRE, False, rejection='C00708')


@pytest.mark.parametrize('invented_year', [False, True])
def test_relative_turn_needs_no_calendar_and_can_only_be_used_with_its_actual_precision(tmp_path, monkeypatch, invented_year):
    from test_material_world_history_periods import RELATIVE_RULE, RELATIVE_LIMITS
    dated = '[FAKE] 港历十五年，雾港由创始期转入扩张期。巡吏准备调取分仓令。'
    original = '[FAKE] 巡吏按《分仓令》施行次年，雾港由创始期转入扩张期的记录查东栈航路。'
    case = replace(TURN, rule=RELATIVE_RULE, limits=RELATIVE_LIMITS, choice=dated if invented_year else original,
                   expected_evidence=(('calendar', ''), ('time_kind', 'relative')))
    reason = '绝对纪年'
    assert_world_flow(tmp_path, monkeypatch, case, case.rule, SELECTED_GENRE, False,
                      rejection=reason if invented_year else None, altered_sibling=(dated, reason))


def test_author_edits_a_year_new_job_reads_revision_two_and_previous_proposal_stays_replayable(tmp_path, monkeypatch):
    from nw.cards import save_card, decide_card
    from nw.materials.phase_projection import verify_chain
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.store import Store
    from nw.story_state import apply_settings, current_head
    from nw.task_models import Budget
    from nw.tasks import read_input_manifest
    from test_material_workflow import choose
    from test_material_world_conversion_flow import ApprovedWorldModel, CARD_ID
    from test_novel_flow import config

    assert_world_flow(tmp_path, monkeypatch, TURN, HISTORY, SELECTED_GENRE, False)
    case = replace(TURN, rule=HISTORY.replace('12年', '15年'), choice=WRONG)
    def frozen_session(store, manifest):
        return read_input_manifest(store, manifest)[1]['material_work']
    with Store(tmp_path / 'project', test_mode=True) as store:
        saved = store.connection.execute(
            "SELECT id FROM input_manifests WHERE json_type(package_json,'$.material_work.stages')='array' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()['id']
        previous = frozen_session(store, saved)
        static, dynamic = (next(s['source']['id'] for s in previous['sources'] if s['source']['key'] == key)
                           for key in (TURN.static_key, TURN.dynamic_key))
        revised = save_card(store, {'card_id': CARD_ID, 'kind': 'world', 'origin': 'author', 'body': {
            'title': case.title, 'rule': case.rule, 'limits': case.limits, 'visibility': 'public'}}, expected_version=1)
        approved = decide_card(store, revised, 'approved', '根据作者复核，将开港年调整至十五年')
        apply_settings(store, current_head(store), [approved.id], 'amend-founding-year')
        provider = ApprovedWorldModel(case, static, dynamic, genre=SELECTED_GENRE, eligible=True, waiting=False, version=2)
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(18, 90000, 4500))).id
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        manifest = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?',
                                            (result.outputs['proposal_id'],)).fetchone()['manifest_id']
    with Store(tmp_path / 'project', test_mode=True) as store:
        for ident, version, choice in ((saved, 1, CHOICE), (manifest, 2, WRONG)):
            session = frozen_session(store, ident)
            verify_chain(session)
            assert next(c['version'] for c in session['context']['approved_cards'] if c['card_id'] == CARD_ID) == version
            plot = next(s['products'] for s in session['stages'] if s['stage'] == 'plot_design')
            assert plot['directions'][0]['choice'] == choice
