"""Client candidate branches preserve the existing promotion/acceptance rules."""
from pathlib import Path
import threading

import pytest

from nw.acceptance import accept_batch
from nw.cards import decide_card, save_card
from nw.novel_store import JobRequest, start_job
from nw.store import Store
from nw.story_state import adopt_story, apply_settings, current_head, revision_state
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio.production_branches import BranchMixin, latest_branch_draft_id
from nw.studio.production_store import ProductionStore
from nw.task_models import Budget
from story_fixture import baseline, draft_for, proposal, seed_book


class Client(BranchMixin):
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.db = ProductionStore(workspace)
        self._lock = threading.RLock()
        self._workers = {}
        self.changed = threading.Event()

    def open_store(self, novel: dict) -> Store:
        return Store(self.workspace / novel['project_dir'], test_mode=True)


@pytest.fixture
def client(tmp_path: Path) -> Client:
    instance = Client(tmp_path / 'workspace')
    with Store(instance.workspace / 'project', create=True, test_mode=True) as store:
        scenes = seed_book(store)
        store.add_brief('[FAKE] 仅验证客户端分支接线', '')
        head = adopt_story(store, baseline(), {})
        drafts = [draft_for(store, scene.id, f'[FAKE] 初始第 {i + 1} 场') for i, scene in enumerate(scenes)]
        accept_batch(store, [proposal(store, head, draft, []) for draft in drafts], head, 'initial')
    instance.db.add('novel', 'project', '测试', {})
    return instance


def promote_body(client: Client) -> dict:
    status = client.branch_status('novel')
    return {'expected_main': status['main_head']['revision'],
            'expected_candidate': status['candidate_head']['revision'],
            'reason': '作者已核对候选正文及分支状态'}


def test_fork_persists_selection_and_leaves_main_unchanged(client: Client) -> None:
    before = client.branch_status('novel')
    result = client.fork_branch('novel', {'name': '第二章候选', 'expected_main': before['main_head']['revision']})
    assert result['current_branch'] == '第二章候选'
    assert result['main_head'] == before['main_head']
    assert result['active_snapshot'] == before['active_snapshot']
    assert result['can_promote'] is False
    reopened = Client(client.workspace)
    assert reopened.db.get('novel')['current_branch'] == '第二章候选'
    assert reopened.branch_status('novel')['candidate_head']['revision'] == 0


@pytest.mark.parametrize('body', [{'name': 'main'}, {'name': '../../outside'}, {'expected_main': -1}])
def test_fork_rejects_invalid_name_or_stale_main(client: Client, body: dict) -> None:
    with pytest.raises(ValueError):
        client.fork_branch('novel', body)
    assert len(client.branch_status('novel')['branches']) == 1


def test_no_change_promotion_blocks_without_writing_author_decision(client: Client) -> None:
    client.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        before = store.connection.execute('SELECT COUNT(*) FROM story_decisions').fetchone()[0]
    result = client.promote_branch('novel', promote_body(client))
    assert result['status'] == 'BLOCKED' and '尚无' in result['blockers'][0]
    with client.open_store(client.db.get('novel')) as store:
        assert store.connection.execute('SELECT COUNT(*) FROM story_decisions').fetchone()[0] == before


def test_explicit_versioned_promotion_is_the_only_main_pointer_change(client: Client) -> None:
    client.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        scene = store.list('scene')[-1]
        old = store.accepted(scene.id).draft_id
        branch = current_head(store, 'candidate')
        changed = draft_for(store, scene.id, '[FAKE] 候选末场已重新验收')
        accept_batch(store, [proposal(store, branch, changed, [])], branch, 'candidate-change')
        assert store.accepted(scene.id).draft_id == old
    assert client.branch_status('novel')['can_promote'] is True
    with pytest.raises(ValueError, match='理由'):
        client.promote_branch('novel', {**promote_body(client), 'reason': ''})
    with pytest.raises(ValueError, match='版本'):
        client.promote_branch('novel', {'reason': '没有确认具体版本'})
    with pytest.raises(ValueError, match='STALE_HEAD'):
        client.promote_branch('novel', {**promote_body(client), 'expected_candidate': 0})
    result = client.promote_branch('novel', promote_body(client))
    assert result['status'] == 'PROMOTED' and result['current_branch'] == 'main'
    with client.open_store(client.db.get('novel')) as store:
        assert store.accepted(scene.id).draft_id == changed.id
        decisions = store.connection.execute("SELECT * FROM story_decisions WHERE action='promote'").fetchall()
        assert len(decisions) == 1


def test_new_chapter_settings_require_old_scene_revalidation(client: Client) -> None:
    client.fork_branch('novel', {'name': 'chapter-two'})
    with client.open_store(client.db.get('novel')) as store:
        old_main = current_head(store)
        scenes = store.list('scene')
        ref = save_card(store, {'card_id': 'new-rule', 'kind': 'world', 'origin': 'author',
                               'body': {'title': '第二章条件', 'rule': '需要新钥匙', 'limits': '只限第二章'}}, None)
        approval = decide_card(store, ref, 'approved', '作者确认新增章条件')
        branch = apply_settings(store, current_head(store, 'chapter-two'), [approval.id], 'new-setting')
    status = client.branch_status('novel')
    assert set(status['needs_revalidation']) == {s.id for s in scenes}
    blocked = client.promote_branch('novel', promote_body(client))
    assert blocked['status'] == 'BLOCKED'
    with client.open_store(client.db.get('novel')) as store:
        assert current_head(store) == old_main
        for index, scene in enumerate(scenes):
            branch = current_head(store, 'chapter-two')
            request = proposal(store, branch, store.get('draft', store.accepted(scene.id).draft_id), [])
            accept_batch(store, [request], branch, f'revalidated-old-scene-{index}')
    status = client.branch_status('novel')
    assert status['needs_revalidation'] == [] and status['can_promote'] is True
    promoted = client.promote_branch('novel', promote_body(client))
    assert promoted['status'] == 'PROMOTED'


def test_legacy_scene_length_and_export_follow_accepted_main_until_promotion(client: Client) -> None:
    studio = StudioService(client.workspace, config_path=client.workspace / 'missing.toml')
    app = ProductionService(studio, LibraryService(client.workspace), test_mode=True)
    original = ['[FAKE] 初始第 1 场', '[FAKE] 初始第 2 场']
    revised = [original[0], '档 案已还。\n' * 8]

    def check(selected_texts: list[str], main_texts: list[str]) -> None:
        # The length tab always measures the accepted main manuscript. Exports follow the selected branch.
        length = app.detail('novel')['length_plan']
        counts = [len(''.join(text.split())) for text in main_texts]
        assert length['accepted_words'] == sum(counts)
        chapter, = length['chapters']
        assert chapter['accepted_words'] == sum(counts)
        assert [scene['accepted_words'] for scene in chapter['scenes']] == counts
        exported, _ = app.export('novel', 'txt')
        assert exported == '测试\n\n第1章 章\n\n' + '\n\n'.join(selected_texts) + '\n'

    check(original, original)
    app.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        branch = current_head(store, 'candidate')
        draft = draft_for(store, store.list('scene')[-1].id, revised[-1])
        accept_batch(store, [proposal(store, branch, draft, [])], branch, 'length-replacement')
    check(revised, original)
    app.select_branch('novel', {'branch_id': 'main'})
    check(original, original)
    app.select_branch('novel', {'branch_id': 'candidate'})
    assert app.promote_branch('novel', promote_body(client))['status'] == 'PROMOTED'
    check(revised, revised)


@pytest.mark.parametrize('main_source', ['manual', 'legacy'])
def test_finish_ignores_candidate_versions_but_detects_earlier_pending_main(client: Client, main_source: str) -> None:
    import json
    from nw.llm.base import GenResult
    from nw.models import Run
    from nw.store import now

    studio = StudioService(client.workspace, config_path=client.workspace / 'missing.toml')
    app = ProductionService(studio, LibraryService(client.workspace), test_mode=True)
    app.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        for scene in store.list('scene'):
            draft_id = store.accepted(scene.id).draft_id
            snapshot = {'messages': [{'content': json.dumps({'draft': {'id': draft_id}})}]}
            run = Run('review-' + scene.id, scene.id, 'review', 'author', 'manual-review', '{}',
                      json.dumps(snapshot), '{}', '', 'error', '{}', now(), '')
            store.add_run(run)
            store.finish_run(run.id, GenResult('{"recommendation":"pass"}', 'complete', {}, 'fixture', {}))
        # Older clients did not record the writing branch on their runs.
        changed = draft_for(store, scene.id, '旧客户端候选新稿')
        head = current_head(store, 'candidate')
        accept_batch(store, [proposal(store, head, changed, [])], head, 'candidate-only')
    def check_current(draft_id: str, accepted: bool, branch: str) -> None:
        item = next(row for row in app.project(client.db.get('novel'))['scenes'] if row['id'] == scene.id)
        assert item['latest_draft_id'] == draft_id
        node = next(child for parent in app.progress('novel')['tree'] for child in parent['children']
                    if child.get('scene_id') == scene.id)
        assert node['draft_id'] == draft_id and node['segments']['accept'] is accepted
        assert app.quality('novel', scene.id)['draft_id'] == draft_id
        workbench = studio.scene_workbench('project', scene.id, branch=branch)
        assert workbench['latest_draft_id'] == draft_id
        assert changed.id in {d['id'] for d in workbench['drafts']}  # explicit version comparison retains history
        assert all(entry['delta']['branch_id'] == branch for entry in workbench['deltas'])

    candidate = studio.save_manual_draft('project', scene.id, '候选分支里的未审改稿', branch='candidate')['draft']
    check_current(candidate['id'], False, 'candidate')
    app.select_branch('novel', {'branch_id': 'main'})
    check_current(draft_id, True, 'main')
    assert app.finish('novel')['status'] == 'DONE'
    text, _ = app.export('novel')
    assert '初始第 2 场' in text and '候选' not in text

    if main_source == 'manual':
        pending = studio.save_manual_draft('project', scene.id, '主线的待审稿')['draft']['id']
    else:
        with client.open_store(client.db.get('novel')) as store:
            pending = draft_for(store, scene.id, '旧版创作的未归属草稿').id
    studio.save_manual_draft('project', scene.id, '比主线更晚保存的候选稿', branch='candidate')
    check_current(pending, False, 'main')
    with pytest.raises(ValueError, match='较新草稿'):
        app.finish('novel')


def test_early_candidate_replacement_reports_downstream_scene(client: Client) -> None:
    client.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        scenes = store.list('scene')
        branch = current_head(store, 'candidate')
        changed = draft_for(store, scenes[0].id, '[FAKE] 前场变化')
        accept_batch(store, [proposal(store, branch, changed, [])], branch, 'first-scene-change')
    status = client.branch_status('novel')
    assert scenes[1].id in status['needs_revalidation'] and not status['can_promote']
    assert client.promote_branch('novel', promote_body(client))['status'] == 'BLOCKED'


def test_main_advancing_after_fork_cannot_be_overwritten(client: Client) -> None:
    client.fork_branch('novel', {'name': 'candidate'})
    with client.open_store(client.db.get('novel')) as store:
        scene = store.list('scene')[-1]
        main = current_head(store)
        change = draft_for(store, scene.id, '[FAKE] 主线后来另有修改')
        accept_batch(store, [proposal(store, main, change, [])], main, 'external-main-change')
    status = client.branch_status('novel')
    assert any('STALE_HEAD' in reason for reason in status['blockers'])
    assert client.promote_branch('novel', promote_body(client))['status'] == 'BLOCKED'
    with client.open_store(client.db.get('novel')) as store:
        assert store.accepted(scene.id).draft_id == change.id


def test_unfinished_job_and_running_worker_block_branch_switch(client: Client) -> None:
    class Running:
        def is_alive(self) -> bool:
            return True
    client._workers['novel'] = Running()
    with pytest.raises(ValueError, match='仍在运行'):
        client.fork_branch('novel', {'name': 'worker-conflict'})
    client._workers.clear()
    with client.open_store(client.db.get('novel')) as store:
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(40, 32000, 4096)))
    client.db.update('novel', job_id=job.id)
    with pytest.raises(ValueError, match='完成或取消'):
        client.fork_branch('novel', {'name': 'unfinished-conflict'})


def test_existing_candidate_can_be_reopened(client: Client) -> None:
    client.fork_branch('novel', {'name': 'candidate'})
    client.select_branch('novel', {'branch_id': 'main'})
    assert client.db.get('novel')['current_branch'] == 'main'
    result = client.select_branch('novel', {'branch_id': 'candidate'})
    assert result['current_branch'] == 'candidate'
    assert len(result['branches']) == 2


def test_real_next_chapter_plan_revise_write_and_explicit_promote(tmp_path: Path, monkeypatch) -> None:
    """Exercise the actual planner/coordinator through chapter two in a test store."""
    import json
    from nw.config import Config
    from nw.llm.base import GenResult
    from nw.novel_flow import resume_job
    from test_novel_flow import Model
    from test_planning import propose, apply

    class NoFactsModel(Model):
        def generate(self, messages, **params):
            if '{"operations"' in messages[0]['content']:
                return GenResult(json.dumps({'operations': []}), 'complete', {}, '[FAKE]', {'isolated_test': True})
            return super().generate(messages, **params)

    client = Client(tmp_path / 'workspace')
    with Store(client.workspace / 'project', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 次章接线验收')
        store.add_brief('[FAKE] 追查封条，分两章')
        adopt_story(store, baseline(), {})
        direction = propose(store, 'book')
        apply(store, direction)
        first = propose(store, 'chapter', parent=direction.id, chapter=1)
        apply(store, first)
        first_scene = store.list('scene')[0].id
        config = Config('fake', 'http://localhost', 'test', '', 5, {}, client.workspace, source_driven=False)
        model = NoFactsModel()

        def run_scene(branch: str, scene_id: str, mode: str = 'write') -> None:
            job = start_job(store, JobRequest(mode, branch_id=branch, scene_ids=[scene_id], budget=Budget(30, 64000, 4096)))
            outcome = resume_job(store, job.id, model, config)
            assert outcome.status == 'WAITING', outcome.reason
            main_draft = store.accepted(scene_id)
            if branch != 'main' and main_draft:
                assert latest_branch_draft_id(store, scene_id, 'main', main_draft.draft_id) == main_draft.draft_id
            outcome = resume_job(store, job.id, model, config,
                                 lambda step, gate: {'action': 'accept', 'reason': '[FAKE] 核对冻结稿件及状态证据'})
            assert outcome.status == 'DONE', outcome.reason

        run_scene('main', first_scene)
        main_before = current_head(store)
        original = store.accepted(first_scene).draft_id
        client.db.add('novel', 'project', '测试第二章', {})
        client.fork_branch('novel', {'name': 'chapter-two'})
        second = propose(store, 'chapter', parent=direction.id, chapter=2, branch='chapter-two')
        apply(store, second)
        status = client.branch_status('novel')
        assert first_scene in status['needs_revalidation']
        assert current_head(store) == main_before
        # Revalidate existing prose first so the new chapter consumes its current version.
        run_scene('chapter-two', first_scene, 'revise')
        second_scene = store.list('scene')[-1].id
        run_scene('chapter-two', second_scene)
        assert store.accepted(first_scene).draft_id == original
        assert store.accepted(second_scene) is None
    app = ProductionService(StudioService(client.workspace, config_path=client.workspace / 'missing.toml'),
                            LibraryService(client.workspace), test_mode=True)
    monkeypatch.setattr(app.studio, '_open_store', lambda name: Store(client.workspace / name, test_mode=True))

    def scene_nodes() -> set[str]:
        return {child['scene_id'] for node in app.progress('novel')['tree'] for child in node['children']
                if child.get('scene_id')}
    assert scene_nodes() == {first_scene, second_scene}
    app.select_branch('novel', {'branch_id': 'main'})
    assert scene_nodes() == {first_scene}
    app.select_branch('novel', {'branch_id': 'chapter-two'})
    ready = client.branch_status('novel')
    assert ready['can_promote'], ready['blockers']
    result = client.promote_branch('novel', promote_body(client))
    assert result['status'] == 'PROMOTED'
    with client.open_store(client.db.get('novel')) as store:
        assert len(store.list('accepted')) == 2
        assert store.accepted(first_scene).draft_id != original
