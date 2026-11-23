"""Production v3 regressions: real HTTP, persistent author choices and workflow gates."""
from dataclasses import asdict
import http.client
import json
import threading
import time

import pytest

from nw.config import Config
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, Journal, JobPaused, show_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio.production_inputs import freeze_wizard, governance, SLOTS
from nw.studio.server import create_studio_server
from nw.task_models import Budget
from story_fixture import baseline
from test_novel_flow import Model


@pytest.fixture
def app(tmp_path):
    studio = StudioService(tmp_path / 'data', config_path=tmp_path / 'missing.toml')
    library = LibraryService(studio.workspace)
    return ProductionService(studio, library)


def wizard(app):
    genre = app.library.genres()['genres'][0]
    return {'title': '回声', 'idea': '一个抄书员发现昨日的档案被改写。',
            'genre_ids': [genre['id'], genre['children'][0]['id']],
            'tone_ids': ['tone.TONE_SERIOUS'],
            'choices': [{'slot': 'tone', 'option_key': 'tone.TONE_SERIOUS'}]}


def test_wizard_creates_real_brief_and_book_job_without_fake_output(app):
    created = app.create(wizard(app))
    assert created['run']['status'] == 'CONFIG_REQUIRED'
    novel = app.db.get(created['novel']['id'])
    assert novel['status'] == 'paused'
    assert novel['wizard']['tone_ids'] == ['TONE_SERIOUS']
    assert novel['wizard']['upgrade_snapshot']['version'] == 0
    with app.open_store(novel) as store:
        assert '抄书员' in store.briefs()[0].text
        assert not store.list('draft')
        row = store.connection.execute('SELECT request_json FROM novel_jobs').fetchone()
        request = json.loads(row[0])
        assert request['design_scope'] == 'book'
        assert request['governance_inputs']['type_selection']['project_config']['genre_ids'] == wizard(app)['genre_ids']
    progress = app.progress(novel['id'])
    assert progress['status'] == 'CONFIG_REQUIRED'
    assert len(progress['tree']) == 1
    assert all(row['status'] == 'pending' for row in progress['tree'][0]['children'])
    assert app.timeline(novel['id'])['events']
    with pytest.raises(ValueError, match='接受'):
        app.export(novel['id'])


@pytest.mark.parametrize('change', [
    {'idea': ''}, {'genre_ids': ['UNKNOWN']}, {'tone_ids': ['invented.tone']},
    {'choices': [{'slot': 'tone', 'option_key': 'tone.TONE_COMIC'}]},
    {'choices': [{'slot': 'tone', 'option_key': 'tone.TONE_SERIOUS', 'recommended': True}]},
])
def test_invalid_wizard_does_not_create_projects(app, change):
    with pytest.raises(ValueError):
        app.create({**wizard(app), **change})
    assert app.studio.list_projects() == []


def test_wrong_parent_and_three_secondary_types_are_rejected(app):
    genres = app.library.genres()['genres']
    for ids in ([genres[0]['id'], genres[1]['children'][0]['id']], [row['id'] for row in genres[:4]]):
        with pytest.raises(ValueError):
            freeze_wizard({**wizard(app), 'genre_ids': ids}, app.library)


@pytest.mark.parametrize('change,limit', [
    ({'tone_ids': ['TONE_SERIOUS', 'TONE_LIGHT', 'TONE_HUMOROUS'], 'choices': []}, '最多选 2 项'),
    ({'genre_ids': ['GENRE_XUANYI', 'SUB_XUANYI_02', 'GENRE_DUSHI', 'GENRE_XUANHUAN']}, '最多选 3 项'),
])
def test_wizard_enforces_the_same_selection_limits_before_creating(app, change, limit):
    with pytest.raises(ValueError, match=limit):
        app.create({**wizard(app), **change, 'design_mode':'manual'})
    assert not app.studio.list_projects()


@pytest.mark.parametrize('mode',['manual','auto'])
def test_wizard_starts_book_design_with_its_saved_mode_and_new_default_budget(app, mode):
    created = app.create({**wizard(app), 'design_mode':mode})
    novel = app.db.get(created['novel']['id'])
    assert novel['wizard']['design_mode'] == mode
    assert novel['wizard']['tone_ids'] == ['TONE_SERIOUS']
    with app.open_store(novel) as store:
        job = show_job(store, novel['job_id'])
        request = json.loads(store.connection.execute('SELECT request_json FROM novel_jobs').fetchone()[0])
        assert job.outputs['budget']['context_char_limit'] == 150000
        assert request['design_scope'] == 'book'
        assert request['production_method_policy']['recommendation_mode'] == mode
        assert request['production_method_policy']['tasks'] == ['world_rules']


def test_creation_and_concurrent_shelf_discovery_preserve_one_identity(app, monkeypatch):
    real_start = start_job
    def discover_during_creation(store, request):
        # This is after nw.db becomes readable, before create() returns.
        listing = app.list()['novels']
        assert len(listing) == 1
        assert listing[0]['wizard']['tone_ids'] == ['TONE_SERIOUS']
        project = app.studio.list_projects()[0]
        # Another process may have captured an older list of registered dirs.
        assert app.db.add(project['id'], project['dir_name'], '旧快照的导入标题', {'imported': True}) is False
        return real_start(store, request)
    monkeypatch.setattr('nw.studio.production.start_job', discover_during_creation)
    created = app.create(wizard(app))
    novels = app.list()['novels']
    assert len(novels) == 1 and novels[0]['id'] == created['novel']['id']
    assert novels[0]['wizard']['idea'] == wizard(app)['idea']
    assert novels[0]['wizard']['tone_ids'] == ['TONE_SERIOUS']


def test_book_scope_stops_after_book_and_pause_is_checkpoint_safe(tmp_path):
    with Store(tmp_path / 'isolated', create=True, test_mode=True) as store:
        store.init_project('[FAKE] workflow acceptance fixture')
        store.add_brief('[FAKE] 追查封条')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(30, 45000, 2000)))
        config = Config('fake', 'http://localhost', 'test', '', 5, {}, tmp_path, source_driven=False)
        model = Model()
        first = resume_job(store, job.id, model, config)
        assert first.status == 'WAITING' and first.step == 'plan:book:confirm'
        result = resume_job(store, job.id, model, config, lambda step, gate: {
            'action': 'approve', 'reason': '[FAKE] isolated author approval',
            'root': gate['candidates'][0]['root']['card_id']})
        assert result.status == 'DONE' and result.step == 'plan:book:apply'
        assert not store.list('chapter')
        assert len(model.calls) == 1
        next_job = start_job(store, JobRequest('design', design_scope='chapter',
            parent_id=result.outputs['proposal_id'], budget=Budget(30, 45000, 2000)))
        with store.connection:
            store.connection.execute("UPDATE novel_jobs SET status='BLOCKED',reason='AUTHOR_PAUSED' WHERE id=?", (next_job.id,))
        with pytest.raises(JobPaused, match='AUTHOR_PAUSED'):
            Journal(store, next_job.id).check_active('test')
        Journal(store, next_job.id).move('RUNNING', 'test')
        assert show_job(store, next_job.id).reason == 'AUTHOR_PAUSED'


def test_source_governance_is_not_bypassed_by_offline_test_provider(tmp_path):
    studio = StudioService(tmp_path / 'data', config_path=tmp_path / 'missing.toml')
    library = LibraryService(studio.workspace)
    model = Model()
    cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, studio.workspace, source_driven=False)
    production = ProductionService(studio, library, test_mode=True, runtime_factory=lambda: (cfg, model))
    created = production.create(wizard(production))
    production._workers[created['novel']['id']].join(timeout=10)
    state = production.progress(created['novel']['id'])
    assert state['status'] == 'BLOCKED'
    assert 'MATERIAL_CATALOG_REQUIRED' in state['reason']
    assert not model.calls


def test_existing_project_is_visible_and_manual_drafts_are_archived(app):
    project = app.studio.create_project('existing', '旧书', brief_text='旧立项\n\n立项参数：\n{"target_words":120000}')
    chapter = app.studio.create_chapter('existing', 1, '初章')
    scene = app.studio.create_scene('existing', chapter['id'], 1, {'title': '开场'})
    draft = app.studio.save_manual_draft('existing', scene['id'], '作者手工正文。')
    listing = app.list()['novels']
    assert len(listing) == 1 and listing[0]['title'] == '旧书'
    assert listing[0]['words'] == 7
    assert app.detail(listing[0]['id'])['length_plan']['effective_target_words'] == 120000
    events = app.timeline(listing[0]['id'])['events']
    assert any(row['ref'].get('draft_id') == draft['draft']['id'] for row in events)
    assert len(app.list()['novels']) == 1
    other = app.studio.create_scene('existing', chapter['id'], 2, {'title': '另一场'})
    with pytest.raises(ValueError, match='不属于'):
        app.studio.get_draft('existing', other['id'], draft['draft']['id'])


def test_isolated_source_backed_book_chapter_scene_acceptance_and_export(tmp_path, monkeypatch):
    """Real coordinator + 7/14 source stages; the LLM is visibly fake in an isolated store."""
    from test_material_phase_flow import template_catalog, PhaseModel
    from test_material_stage_roundtrip import StageModel
    from nw.materials.phase_routes import phase_order
    workspace = tmp_path / 'data'
    workspace.mkdir()
    template_catalog(workspace)
    books = tmp_path / 'novels'
    with Store(workspace / 'test-book', projects_root=books, create=True, test_mode=True) as store:
        store.init_project('[FAKE] 端到端隔离验收')
        store.add_brief('[FAKE] 调查封条和钥匙的来源')
        adopt_story(store, baseline(), {})
    class IsolatedStudio(StudioService):
        def _open_store(self, project_name, *, create=False):
            return Store(self.workspace / project_name, projects_root=self.projects_root, create=create, test_mode=True)
    studio = IsolatedStudio(workspace, projects_root=books, config_path=tmp_path / 'absent.toml')
    library = LibraryService(workspace)
    from test_material_governance_runtime import runtime
    from test_studio_cast_samples import add_reference
    monkeypatch.setattr('nw.materials.governance_runtime.load_governance', lambda _: runtime())
    add_reference(library, '两章渡口参考', ['GENRE_XUANYI'])
    class ClientModel(PhaseModel, StageModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if '[MATERIAL_STEP]' in messages[0]['content']:
                if payload['stage'] == 'type_selection':
                    raw = json.loads(result.text)
                    products = raw['products']
                    [genre] = payload['governance']['selected_genre_ids']
                    products['selection'][0]['id'] = genre
                    products['concepts'][0]['type_refs'] = [genre]
                    products['_governance'] = {'project_config': {
                        'genre_ids': [genre], 'mechanism_ids': [], 'structure_ids': [], 'style_ids': [], 'tone_ids': []}}
                    result.text = json.dumps(raw, ensure_ascii=False)
                if context := payload.get('length_context'):
                    raw = json.loads(result.text)
                    products = raw['products']
                    expected = context['policy'].get('target_words', 36)
                    if payload['stage'] == 'plot_design':
                        for direction in products['directions']:
                            direction['length_plan'] = {'target_words': expected, 'chapter_count': 1,
                                                        'reason': '[FAKE] 一章查明证据'}
                    for member in products.get('members', []):
                        if member['kind'] in ('chapter', 'scene'):
                            member['body']['word_budget'] = {'target_words': expected, 'min_words': 25,
                                                             'max_words': 48, 'reason': '[FAKE] 查清一项证据'}
                    result.text = json.dumps(raw, ensure_ascii=False)
            if 'material_review' in payload:
                raw = json.loads(result.text)
                checks = {c['id']: c for c in payload['material_review']['checks']}
                for row in raw['material_checks']:
                    if roster := checks[row['id']].get('roster'):
                        row['people'] = [{'actor': actor, 'mode': 'action', 'span': 0, 'cue': '借灯查看封条',
                                          'reason': f'{name}亲自借灯检查印痕。'} for actor, name in roster.items()]
                result.text = json.dumps(raw, ensure_ascii=False)
            if '{"operations"' in messages[0]['content']:
                raw = json.loads(result.text)
                for op in raw['operations']:
                    op.setdefault('expected_old', None)
                result.text = json.dumps(raw, ensure_ascii=False)
            return result
    model = ClientModel('client-fixture')
    config = Config('fake', 'http://localhost', 'isolated-test', '', 5, {}, workspace, source_driven=True)
    app = ProductionService(studio, library, test_mode=True, runtime_factory=lambda: (config, model))
    novel = app.list()['novels'][0]
    ident = novel['id']
    with app.db.connect() as db:
        wizard_values = {**novel['wizard'], 'auto_length': True, 'genre_ids': ['GENRE_XUANYI']}
        db.execute('UPDATE novels SET wizard_json=? WHERE id=?', (json.dumps(wizard_values), ident))
    def settled():
        app._workers[ident].join(timeout=40)
        assert not app._workers[ident].is_alive()
        return app.progress(ident)
    def approval_body(gate):
        body = {'token': gate['token'], 'action': 'approve' if 'approve' in gate['actions'] else 'accept',
                'reason': '[FAKE] 隔离测试作者确认'}
        if gate['target'].get('candidates'):
            body['root'] = gate['target']['candidates'][0]['root']['card_id']
        return body
    def approve(gate):
        app.decide(ident, gate['id'], approval_body(gate))
        return settled()
    archive_started, archive_release = threading.Event(), threading.Event()
    done_archive_started, done_archive_release = threading.Event(), threading.Event()
    archive_calls = 0
    original_sync = app.sync_history
    def delayed_archive(novel_id):
        nonlocal archive_calls
        archive_calls += 1
        if archive_calls == 1:
            archive_started.set()
            archive_release.wait(timeout=10)
        elif archive_calls == 2:
            done_archive_started.set()
            done_archive_release.wait(timeout=10)
        original_sync(novel_id)
    app.sync_history = delayed_archive
    app.run(ident, {'mode': 'design', 'scope': 'book'})
    assert archive_started.wait(timeout=40)
    book_waiting = app.progress(ident)
    assert book_waiting['status'] == 'WAITING', book_waiting['reason']
    assert len(book_waiting['tree'][0]['children']) == len(phase_order('book'))
    assert all(node['status'] == 'done' for node in book_waiting['tree'][0]['children'])
    calls_before = len(model.calls)
    with pytest.raises(ValueError, match='未完成任务|仍在运行'):
        app.run(ident, {'mode': 'write', 'scene_ids': ['not-yet-created']})
    assert len(model.calls) == calls_before
    assert app._workers[ident].is_alive()
    release_timer = threading.Timer(0.2, archive_release.set)
    release_timer.start()
    app.decide(ident, book_waiting['gates'][0]['id'], approval_body(book_waiting['gates'][0]))
    release_timer.join()
    assert done_archive_started.wait(timeout=40)
    book_done = app.progress(ident)
    assert book_done['status'] == 'DONE'
    assert app._workers[ident].is_alive()
    assert app.db.get(ident)['status'] != 'done'
    release_timer = threading.Timer(0.2, done_archive_release.set)
    release_timer.start()
    # A long book's approved direction can outlive the studio's recent-job display.
    from unittest.mock import patch
    with patch.object(app.studio, '_list_jobs', return_value=[]):
        app.run(ident, {'mode': 'design', 'scope': 'chapter'})
    with app.open_store(novel) as history:
        job = history.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?',
                                         (app.db.get(ident)['job_id'],)).fetchone()
        assert json.loads(job[0])['parent_id'] == book_done['job']['outputs']['proposal_id']
    release_timer.join()
    app.sync_history = original_sync
    chapter_waiting = settled()
    assert chapter_waiting['status'] == 'WAITING', chapter_waiting['reason']
    chapter = next(node for node in chapter_waiting['tree'] if node.get('scope') == 'chapter')
    assert len(chapter['children']) == 14
    assert all(node['status'] == 'done' for node in chapter['children'])
    approve(chapter_waiting['gates'][0])
    app.run(ident, {})
    written = settled()
    with app.open_store(novel) as inspect:
        invalid = [dict(row) for row in inspect.connection.execute('SELECT kind,reason FROM task_calls WHERE validation=\'INVALID\'')]
    assert written['status'] == 'WAITING', (written['reason'], invalid)
    with app.open_store(novel) as inspect:
        from nw.length_plan import approved_book_plan, approved_length_budgets
        from nw.story_state import current_head, revision_state
        state = revision_state(inspect, current_head(inspect, 'main'))
        assert approved_book_plan(inspect, state)['target_words'] == 36
        assert [target['target_words'] for target in approved_length_budgets(inspect, state)['scenes'].values()] == [36]
    accepted = approve(written['gates'][0])
    assert accepted['status'] == 'DONE', accepted['reason']
    text, filename = app.export(ident, 'md')
    assert '[FAKE]' in text and filename.endswith('.md')
    assert '第1章' in text
    book_dir = books / novel['project_dir']
    assert (book_dir / 'nw.db').is_file()
    assert next((book_dir / '正文').glob('*.md'))
    assert not (workspace / novel['project_dir']).exists()
    assert (book_dir / '成品' / '全书.md').read_bytes() == text.encode('utf-8')
    chapter_text, _ = app.export(ident, 'txt', 'chapter:1')
    assert (book_dir / '成品' / '第1章.txt').read_bytes() == chapter_text.encode('utf-8')
    assert app.detail(ident)['project']['data_directory'] == str(book_dir)
    quality = app.quality(ident)
    assert quality['review']['recommendation'] == 'pass'
    plan = quality['cast']['plan']
    assert plan['chapter'] == 1 and [p['name'] for p in plan['people']] == ['沈砚']
    actual = quality['cast']['accepted']
    assert actual['complete'] and [(p['presence'], p['name']) for p in actual['people']] == [('onstage','沈砚')]
    assert actual['people'][0]['cue'] in text
    # A frozen preference is not adoption. The passing review must accompany
    # an actual selected product (or explicitly checked option).
    from unittest.mock import patch
    preferences = app.db.get(ident)['wizard']
    preferences['choices'] = [{'slot': 'tone', 'option_key': 'tone.TONE_SERIOUS'}]
    with app.db.connect() as db:
        db.execute('UPDATE novels SET wizard_json=? WHERE id=?', (json.dumps(preferences), ident))
    product = {'selection': [], '_governance': {'project_config': {'tone_ids': ['TONE_SERIOUS']}}}
    scene_design = {'work_session': {'stages': [{'stage': 'type_selection', 'products': product}]}}
    with patch('nw.materials.evidence.scene_materials', return_value=scene_design):
        app.sync_adoptions(ident)
        with library.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM reviewed_adoptions').fetchone()[0] == 0
        product['selection'] = [{'id': 'TONE_SERIOUS'}]
        app.sync_adoptions(ident)
        app.sync_adoptions(ident)
        with library.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM reviewed_adoptions').fetchone()[0] == 1
    calls_before = len(model.calls)
    with pytest.raises(ValueError, match='候选分支'):
        app.run(ident, {'mode': 'design', 'scope': 'chapter'})
    assert len(model.calls) == calls_before
    app.studio.create_chapter(novel['project_dir'], 2, '[FAKE] 空章不能充数')
    updated_wizard = app.db.get(ident)['wizard']
    updated_wizard['chapter_count'] = 2
    with app.db.connect() as db:
        db.execute('UPDATE novels SET wizard_json=? WHERE id=?', (json.dumps(updated_wizard), ident))
    with pytest.raises(ValueError, match='空章'):
        app.finish(ident)
    updated_wizard['chapter_count'] = 1
    with app.db.connect() as db:
        db.execute('UPDATE novels SET wizard_json=? WHERE id=?', (json.dumps(updated_wizard), ident))
    # Completion compares only accepted main prose. An arbitrarily high target can't pass.
    limits = app.configure_length(ident, {'target_words': 160000})['length_plan']
    assert 0 < limits['accepted_words'] < 160000
    with pytest.raises(ValueError, match='全书篇幅未达标'):
        app.finish(ident)
    assert app.db.get(ident)['status'] != 'done'
    app.configure_length(ident, {'target_words': limits['accepted_words']})
    # A failed final file cannot publish a completed project. The same job is retryable.
    full_txt = book_dir / '成品' / '全书.txt'
    full_md = book_dir / '成品' / '全书.md'
    full_md.unlink()
    full_txt.mkdir()
    with pytest.raises(OSError):
        app.finish(ident)
    assert app.db.get(ident)['status'] != 'done'
    full_txt.rmdir()
    app.finish(ident)
    assert full_txt.read_bytes() == chapter_text.encode('utf-8')
    assert full_md.read_bytes() == text.encode('utf-8')
    assert app.list('done')['novels'][0]['id'] == ident
    assert any(event['kind'] == 'write' for event in app.timeline(ident)['events'])
    with pytest.raises(ValueError, match='卷方案'):
        app.export(ident, 'md', 'volume:unassigned')
    scene = app.detail(ident)['project']['scenes'][0]
    app.studio.save_manual_draft(novel['project_dir'], scene['id'], '[FAKE] 新增但尚未审稿的手动版本')
    scene_node = next(child for node in app.progress(ident)['tree'] for child in node['children']
                      if child.get('scene_id') == scene['id'])
    assert scene_node['status'] == 'pending'
    assert scene_node['segments'] == {'write': True, 'review': False, 'accept': False}
    with pytest.raises(ValueError, match='较新草稿'):
        app.finish(ident)


def test_quality_does_not_apply_previous_review_to_new_manual_draft(app):
    from nw.models import Run
    from nw.store import now
    from nw.llm.base import GenResult
    app.studio.create_project('manual', '人工版本', brief_text='作者稿')
    chapter = app.studio.create_chapter('manual', 1, '第一章')
    scene = app.studio.create_scene('manual', chapter['id'], 1, {'title': '试稿'})
    old = app.studio.save_manual_draft('manual', scene['id'], '第一版作者稿')['draft']
    with app.studio._open_store('manual') as store:
        run = Run('review-fixture', scene['id'], 'review', 'author', 'manual-review-fixture', '{}',
                  json.dumps({'messages': [{'content': json.dumps({'draft': old})}]}), '{}', '', 'error', '{}', now(), '')
        store.add_run(run)
        store.finish_run(run.id, GenResult(json.dumps({'recommendation': 'pass', 'notes': '[FAKE] fixture'}),
                                          'complete', {}, 'isolated-review-fixture', {}))
    novel = app.list()['novels'][0]
    assert app.quality(novel['id'], scene['id'])['review']['draft_id'] == old['id']
    new = app.studio.save_manual_draft('manual', scene['id'], '第二版，尚未审稿')['draft']
    quality = app.quality(novel['id'], scene['id'])
    assert quality['draft_id'] == new['id'] and quality['review'] is None


def test_http_wizard_sse_and_mutation_origin(app):
    server = create_studio_server(app.studio, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    def call(method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
        connection.request(method, path, json.dumps(body) if body is not None else None,
                           headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result
    stream = None
    try:
        status, genres = call('GET', '/api/genres')
        assert status == 200 and genres['counts']['sub'] == 425
        assert genres['selection_limits'] == dict(genre=3, tone=2, style=3, narration=30, world=30,
                                                   character=30, structure=2, hook=5)
        assert genres['default_budget']['context_char_limit'] == 150000
        status, created = call('POST', '/api/novels', wizard(app))
        assert status == 201, created
        ident = created['novel']['id']
        assert call('GET', f'/api/novels/{ident}/progress')[1]['status'] == 'CONFIG_REQUIRED'
        bad = {'Content-Type': 'application/json', 'Origin': 'https://untrusted.example'}
        assert call('POST', f'/api/novels/{ident}/cancel', {}, bad)[0] == 403
        assert call('POST', f'/api/novels/{ident}/cancel', {}, {'Content-Type': 'text/plain'})[0] == 415
        stream = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
        stream.request('GET', f'/api/novels/{ident}/events')
        response = stream.getresponse()
        assert response.getheader('Content-Type').startswith('text/event-stream')
        assert response.readline().strip() == b'event: progress'
        first = json.loads(response.readline().decode().removeprefix('data: '))
        assert first['novel_id'] == ident
        response.readline()
        started = time.monotonic()
        call('POST', f'/api/novels/{ident}/pause', {})
        assert response.readline().strip() == b'event: progress'
        changed = json.loads(response.readline().decode().removeprefix('data: '))
        assert changed['status'] == 'PAUSED'
        assert time.monotonic() - started < 1
    finally:
        if stream:
            stream.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
