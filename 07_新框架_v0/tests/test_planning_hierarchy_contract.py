"""Outline responsibilities and the chapter approval boundary."""
from copy import deepcopy
import json

import pytest

from nw.materials.phase_projection import expand_output, verify_chain
from nw.materials.phase_routes import phase_order
from nw.materials.work_session import drive_plan
from nw.novel_store import JobPaused, JobRequest, Journal, start_job
from nw.plan_contract import validate_plan
from nw.planning import _run_plan, prepare_plan_task
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from story_fixture import baseline
from test_material_stage_integration import pins_for
from test_novel_flow import Model, config
from test_planning import Planner, apply, propose
from test_studio_project_methods import client, seven_automatic_methods


def test_volume_outline_has_a_turn_and_no_prose_coordinates():
    body = Planner('book').output['candidate_cards'][0]['body']
    charter = {'key': 'volume', 'kind': 'volume', 'body': {'title': '[FAKE] 旧印调查',
        'goal': '[FAKE] 查出换印手法', 'turn': '[FAKE] 调查人被罢黜',
        'ending_direction': '[FAKE] 取得失物名单供下卷核查'}}
    candidate = {'kind': 'plot', 'body': body, 'members': [charter], 'chapters': [], 'open_world_rules': []}
    output = {'scope': 'volume', 'candidate_cards': [candidate]}
    validate_plan(output, 'volume', {}, planning_hierarchy=True)
    assert phase_order('volume', planning_hierarchy=True) == phase_order('book')
    assert 'scene_design' in phase_order('volume')
    broken = deepcopy(output)
    del broken['candidate_cards'][0]['members'][0]['body']['ending_direction']
    with pytest.raises(ValueError, match='卷末'):
        validate_plan(broken, 'volume', {}, planning_hierarchy=True)


def test_book_trajectory_leaves_lower_level_cards_for_their_own_scope():
    output = Planner('book').output
    output['candidate_cards'][0]['members'].append({'kind': 'chapter', 'key': 'ch', 'body': {
        'title': '[FAKE] 旧印调查', 'goal': '[FAKE] 查出来源', 'consequence': '[FAKE] 守卫离场'}})
    validate_plan(output, 'book', {})
    with pytest.raises(ValueError, match='相应步骤'):
        validate_plan(output, 'book', {}, planning_hierarchy=True)


def test_hierarchical_auto_does_not_fill_book_board_with_a_chapter_card(client, monkeypatch):
    from nw.production_methods.sources import MethodReader
    from nw.studio.method_recommendations import automatic_requirements

    _, _, server, source = client
    rows = seven_automatic_methods(source)
    main_plot = next(row for row in rows if row['id'] == 'main_plot')
    main_plot['body']['outputs'][0].update(field='members', artifact_kind='chapter')
    monkeypatch.setattr(MethodReader, 'current_methods', lambda _: rows)
    monkeypatch.setattr(MethodReader, 'world_source', lambda *_: (None, None))
    reader = MethodReader(server.production.library.workspace)
    assert 'structure' in automatic_requirements(reader, ['GENRE_XUANYI'])
    with pytest.raises(ValueError, match='AUTO_RECOMMENDATIONS_MISSING.*超出本级规划职责'):
        automatic_requirements(reader, ['GENRE_XUANYI'], planning_hierarchy=True)


def test_chapter_gate_targets_actual_plot_and_scene_keeps_its_chapter_identity():
    from nw.materials.planning_hierarchy import chapter_target, validate_scene_handoff

    member = {'kind': 'chapter', 'key': 'chapter', 'body': {'title': '[FAKE] 印坊问证',
        'goal': '[FAKE] 找到原印铸造者', 'consequence': '[FAKE] 印匠在盘问后逃走'}}
    output = {'members': [member], 'directions': [Planner('book').output['candidate_cards'][0]['body']],
              'event_nodes': [{'id': 'query', 'goal': '[FAKE] 问清铸印合同'}]}
    plot = {'stage': 'plot_design', 'task_id': 'plot-task', 'sha256': content_sha256(output), 'products': output}
    lineage = [{'scope': 'volume', 'proposal_id': 'volume'}]
    target = chapter_target(plot, lineage)
    assert target['kind'] == 'chapter_outline_approval' and target['chapter'] == member
    assert target['plot_ref']['sha256'] == plot['sha256'] and target['event_nodes'] == output['event_nodes']
    context = {'planning_hierarchy': True, 'scope': 'chapter', 'approved_chapter': {'target': target}}
    validate_scene_handoff({'chapters': [{'index': 1, 'card': 'chapter', 'scenes': []}]}, context)
    with pytest.raises(ValueError, match='已批准章纲'):
        validate_scene_handoff({'chapters': [{'index': 1, 'card': None, 'scenes': []}]}, context)


def test_new_chapter_is_pinned_to_next_published_number_after_accepted_predecessor(tmp_path):
    from nw.acceptance import accept_batch
    from nw.materials.planning_hierarchy import next_chapter_index, chapter_target, validate_scene_handoff
    from nw.story_state import current_head, revision_state
    from story_fixture import draft_for, proposal
    from test_chapter_state import prepare_story

    with Store(tmp_path / 'next-chapter', create=True, test_mode=True) as store:
        _, scenes = prepare_story(store)
        head = current_head(store)
        with pytest.raises(ValueError, match='尚有未接受'):
            next_chapter_index(store, revision_state(store, head))
        pending = [proposal(store, head, draft_for(store, scene, '[FAKE] 各场均完成。'), []) for scene in scenes]
        accepted = accept_batch(store, pending, head, 'phase-four-chapter')
        assert next_chapter_index(store, revision_state(store, accepted)) == 2

    member = {'kind': 'chapter', 'key': 'chapter', 'body': {'title': '[FAKE] 续查',
        'goal': '[FAKE] 核查日簿', 'consequence': '[FAKE] 获得签名'}}
    output = {'members': [member], 'directions': [Planner('book').output['candidate_cards'][0]['body']],
              'event_nodes': [{'id': 'query'}]}
    plot = {'stage': 'plot_design', 'task_id': 'plot-task', 'sha256': content_sha256(output), 'products': output}
    target = chapter_target(plot, [], chapter_index=2)
    assert target['chapter_index'] == 2
    context = {'planning_hierarchy': True, 'scope': 'chapter', 'approved_chapter': {'target': target},
               'chapter_target_index': 2}
    with pytest.raises(ValueError, match='第 2 章'):
        validate_scene_handoff({'chapters': [{'index': 1, 'card': 'chapter', 'scenes': []}]}, context)
    validate_scene_handoff({'chapters': [{'index': 2, 'card': 'chapter', 'scenes': []}]}, context)


class HierarchyModel(Model):
    def generate(self, messages: list[dict], **params):
        reply = super().generate(messages, **params)
        packet = json.loads(messages[-1]['content'])
        if packet.get('scope') == 'volume' and packet.get('stage') == 'plot_design':
            raw = json.loads(reply.text)
            members = raw['products']['members']
            members[:] = [row for row in members if row['kind'] not in ('volume', 'chapter')]
            members.append({'key': 'volume_1', 'kind': 'volume', 'body': {
                'title': '[FAKE] 查封条', 'goal': '[FAKE] 找到拓片', 'turn': '[FAKE] 换印案牵连巡查人',
                'ending_direction': '[FAKE] 向印坊查证拓片的原始编号'}})
            reply.text = json.dumps(raw, ensure_ascii=False)
        return reply


def _prepare(store: Store, job_id: str, scope: str, model: Model, parent: object, lineage: list) -> tuple:
    return prepare_plan_task(store, 1, scope, model, config(store), job_id, 'hierarchy-' + scope,
                             parent_id=parent.id, planning_hierarchy=True, outline_lineage=lineage)


def test_staged_volume_then_chapter_approval_precedes_scene_generation(tmp_path, monkeypatch):
    with Store(tmp_path / 'project', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 暗井层级')
        store.add_brief('[FAKE] 核对封条')
        adopt_story(store, baseline(), {})
        book = propose(store)
        apply(store, book)
        key = '1.1_行动动机'
        pins_for(tmp_path, monkeypatch, f'### {key}\n【定义】用实际目标安排人物行动。\n【指令】先写行动目标。\n', [key])
        model = HierarchyModel()
        budget = Budget(36, 150000, 8000)
        volume_job = start_job(store, JobRequest('design', design_scope='volume', parent_id=book.id, budget=budget))
        book_root = book.materialization[0]['root']
        lineage = [{'scope': 'book', 'proposal_id': book.id, 'root': book_root}]
        task, package = _prepare(store, volume_job.id, 'volume', model, book, lineage)
        volume = _run_plan(store, task, package, model, config(store))
        assert not volume.materialization[0]['chapters']
        assert not any(json.loads(messages[-1]['content']).get('stage') == 'scene_design' for messages in model.calls)
        apply(store, volume)
        assert not store.list('chapter') and not store.list('scene')
        lineage.append({'scope': 'volume', 'proposal_id': volume.id, 'root': volume.materialization[0]['root'],
                        'artifact': {'kind': 'volume', 'body': {'goal': '[FAKE] 找到拓片'}}})
        chapter_job = start_job(store, JobRequest('design', design_scope='chapter', parent_id=volume.id, budget=budget))
        task, package = _prepare(store, chapter_job.id, 'chapter', model, volume, lineage)
        journal = Journal(store, chapter_job.id)
        gate_key = 'plan:chapter:outline:confirm'

        def decide(target: dict, approve: bool = False) -> dict:
            def respond(_key, _gate):
                return {'action': 'approve', 'reason': '[FAKE] 确认本章目标和章末变化'} if approve else None
            choice = journal.gate(gate_key, target, respond, {'approve': 'novel_confirm'})
            return {'decision_id': chapter_job.id + ':' + gate_key, 'choice': choice}

        before = len(model.calls)
        with pytest.raises(JobPaused) as stopped:
            drive_plan(store, task, package, model, config(store), chapter_decision=decide)
        assert stopped.value.status == 'WAITING'
        calls = [json.loads(call[-1]['content']) for call in model.calls[before:]]
        assert any(row.get('stage') == 'plot_design' for row in calls)
        assert not any(row.get('stage') == 'event_design' for row in calls)
        assert not store.list('chapter')
        target = stopped.value.outputs['gate']
        assert target['chapter']['body']['goal'] and target['outline_lineage'][-1]['artifact']
        before = len(model.calls)
        task, staged = drive_plan(store, task, package, model, config(store),
                                  chapter_decision=lambda target: decide(target, True))
        calls = [json.loads(call[-1]['content']) for call in model.calls[before:]]
        assert all(not row.get('stage') or row['approved_chapter']['target']['chapter'] == target['chapter']
                   for row in calls)
        assert any(row.get('stage') == 'scene_design' for row in calls)
        session = staged['material_work']
        final = expand_output(json.loads(task.payload['messages'][-1]['content'])['output_contract'], staged)
        assert final['candidate_cards'][0]['chapters'][0]['card'] == target['chapter']['key']
        tampered = deepcopy(session)
        tampered['context']['approved_chapter']['target']['chapter']['body']['goal'] = '更改章目标'
        with pytest.raises(ValueError, match='章纲'):
            verify_chain(tampered)
