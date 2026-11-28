"""Regression tests for audited Studio backend/frontend and workflow fixes."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import pytest

from nw.config import ROOT
from nw.novel_store import JobRequest, start_job
from nw.store import Store
from nw.story_state import adopt_story, current_head, revision_state
from nw.studio.api import StudioService
from nw.studio.corpus_methods import manual_method
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio.repository import RepositorySync
from nw.studio.repository_git import SyncError, shared_config_safe
from nw.studio.server import create_studio_server
from nw.task_models import Budget
from corpus_fixture import CorpusModel, make_book, start_analysis
from story_fixture import baseline


def test_save_author_card_applies_settings_and_handles_null_story_order(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    proj = studio.create_project('book1', '测试')
    with studio._open_store('book1') as store:
        adopt_story(store, baseline(), {})
        ch = store.add_chapter(1, '第一章')
        sc = store.add_scene(ch.id, 1, '{"title":"场1"}')
    saved_world = studio.save_author_card('book1', {
        'card_id': 'rule-1',
        'kind': 'world',
        'body': {'title': '法则', 'rule': '不能无凭施法', 'limits': '仅限白昼'},
        'auto_approve': True,
        'apply_to_branch': True,
    })
    assert saved_world['card_id'] == 'rule-1'
    with studio._open_store('book1') as store:
        snap = revision_state(store, current_head(store, 'main'))
        assert any(s['card_id'] == 'rule-1' for s in snap['settings'])
    saved_scene = studio.save_author_card('book1', {
        'card_id': 'scene-card-1',
        'kind': 'scene',
        'body': {'title': '场1卡', 'goal': '探查', 'pov': '沈砚'},
        'bind_scene_id': sc.id,
        'story_order': None,
    })
    link = studio.add_card_link('book1', 'rule-1', 1, 'depends_on', saved_scene['card_id'], 1)
    assert link['relation'] == 'depends_on'


def test_list_jobs_reads_novel_jobs_and_search_clamps_bounds(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    studio.create_project('book2', '任务列表')
    with studio._open_store('book2') as store:
        store.add_brief('需求')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', design_scope='book', budget=Budget(10, 8000, 1000)))
    listed = studio.list_jobs('book2')['jobs']
    assert len(listed) == 1 and listed[0]['id'] == job.id and listed[0]['scope'] == 'book'
    res = studio.search_f2_ledger(limit=-5, offset=-10)
    assert res['offset'] == 0 and res['limit'] == 1


def test_render_config_toml_validates_keys_timeouts_and_preserves_provider_overrides(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'studio.config.toml')
    with pytest.raises(ValueError, match='超时'):
        studio.render_config_toml({'model': {'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434',
                                             'model': 'qwen', 'timeout': 0}})
    with pytest.raises(ValueError, match='无效'):
        studio.render_config_toml({'model': {'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434',
                                             'model': 'qwen'}, 'params': {'bad\n[x]': 1}})
    toml_text = studio.render_config_toml({
        'model': {'provider': 'openai_compat', 'base_url': 'https://api.example.test/v1',
                  'model': 'main-m', 'api_key_env': 'TEST_KEY', 'timeout': 60},
        'stage_models': {'write': {'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434'}},
    })
    assert '[stage_models.write]' in toml_text and 'provider = "ollama"' in toml_text


def test_shared_config_safe_allows_ollama_params(tmp_path: Path) -> None:
    cfg = tmp_path / 'studio.config.toml'
    cfg.write_text(
        '[model]\nprovider = "ollama"\nbase_url = "http://127.0.0.1:11434"\nmodel = "qwen2.5:14b"\n'
        'api_key_env = ""\ntimeout = 120\n\n[params]\ntemperature = 0.3\nnum_predict = 2048\n\n'
        '[paths]\nworkspace = "workspace"\n\n[workflow]\nsource_driven = true\n',
        encoding='utf-8',
    )
    shared_config_safe(cfg)


def test_repository_mutation_blocks_when_git_init_failed(tmp_path: Path) -> None:
    proj = tmp_path / 'proj'
    ws = proj / 'workspace'
    ws.mkdir(parents=True)
    (proj / 'studio.repository.toml').write_text('[sync]\nenabled = true\nremote = "..bad"\n', encoding='utf-8')
    svc = StudioService(ws, config_path=proj / 'studio.config.toml')
    repo = RepositorySync(svc, project=proj)
    assert repo.enabled is True and repo.git is None
    with pytest.raises(SyncError, match='RESTART|尚未就绪'):
        with repo.mutation():
            pass


def test_manual_method_defaults_version_and_server_returns_400_on_type_error(tmp_path: Path, monkeypatch) -> None:
    lib = LibraryService(tmp_path / 'lib')
    provider = CorpusModel()
    book, _, _ = start_analysis(lib, monkeypatch, provider)
    rec = lib.get_corpus(book['id'])
    lib.review_corpus(book['id'], {'version': rec['version'], 'decision': 'approve',
                                   'note': '核对通过', 'accept_limitations': True})
    tid = lib.get_corpus(book['id'])['body']['threads'][0]['id']
    draft = manual_method(lib, book['id'], {'thread_ids': [tid]})
    assert draft['structure_origin']['structure_version'] == rec['version']

    server = create_studio_server(StudioService(tmp_path / 'srv'), port=0)
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        conn.request('POST', '/api/projects', json.dumps({'dir_name': 'p1', 'title': 't'}).encode(),
                     {'Content-Type': 'application/json'})
        assert conn.getresponse().status == 201
        conn.request('POST', '/api/projects/p1/scenes/s1/delta', json.dumps({'draft_id': 123, 'story_order': []}).encode(),
                     {'Content-Type': 'application/json'})
        resp = conn.getresponse()
        assert resp.status in (400, 404)
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=5)


def test_frontend_fixed_guards_present() -> None:
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    decisions = (js_root / 'pages' / 'studio-decisions.js').read_text(encoding='utf-8')
    assert "action==='reject'" in decisions
    settings = (js_root / 'pages' / 'settings.js').read_text(encoding='utf-8')
    assert "!old.provider||old.provider==='openai_compat'" not in settings
    timeline = (js_root / 'components' / 'Timeline.js').read_text(encoding='utf-8')
    for key in ('branch:', 'method_configuration:', 'confirmation:'):
        assert key in timeline
    corpus = (js_root / 'pages' / 'corpus.js').read_text(encoding='utf-8')
    assert 't?`<button' in corpus
    wizard = (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'planning_hierarchy:1' in wizard
    kb = (js_root / 'pages' / 'kb.js').read_text(encoding='utf-8')
    assert 'allSlot=await api.get' in kb


def test_book_directions_creation_input_forwards_length_hierarchy_and_methods(tmp_path: Path) -> None:
    from nw.book_directions import _creation_input
    from nw.novel_store import Journal

    with Store(tmp_path / 'dir', create=True, test_mode=True) as store:
        store.init_project('测试书')
        store.add_brief('主角追查失踪记录。')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest(
            'design',
            design_scope='book',
            budget=Budget(10, 32000, 2000),
            planning_hierarchy=True,
            production_method_policy={'policy': 'project-corpus-methods-v1', 'tasks': ['hook'],
                                      'type_ids': ['GENRE_XUANYI'], 'preferred_methods': {'m1': 1}},
            governance_inputs={
                'type_selection': {'creation_plan': {'types': [{'id': 'GENRE_XUANYI', 'name': '悬疑'}]}},
                'plot_design': {'length_policy': {'target_words': 300000, 'chapter_count': 60}},
                'world_design': {'cast_sample_reference': {'source': 'sample-1'}},
            },
        ))
        pkg = _creation_input(Journal(store, job.id))
        assert pkg['planning_hierarchy'] is True
        assert pkg['length_policy'] == {'target_words': 300000, 'chapter_count': 60}
        assert pkg['cast_sample_reference'] == {'source': 'sample-1'}
        assert pkg['production_methods']['preferred_methods'] == {'m1': 1}


def test_hierarchy_filters_out_of_scope_methods_and_scopes_volume_governance(tmp_path: Path) -> None:
    from nw.novel_flow import _scope_governance_inputs
    from nw.production_methods.policy import normalize
    from nw.studio.method_recommendations import uses

    body = {
        'tasks': ['main_plot'],
        'scopes': ['book'],
        'prerequisites': [{'key': 'i1', 'input_kind': 'brief', 'artifact': '立项', 'requirement': '明确目标'}],
        'operations': [{'key': 'op1', 'instruction': '建章', 'input_keys': ['i1'], 'output_keys': ['o1']}],
        'outputs': [{'key': 'o1', 'stage': 'plot_design', 'field': 'members',
                     'artifact_kind': 'chapter', 'description': '建立章卡'}],
    }
    assert uses(body, 'structure', planning_hierarchy=False)
    assert not uses(body, 'structure', planning_hierarchy=True)

    scoped = _scope_governance_inputs(
        {'world_design': {'x': 1}, 'scene_design': {'y': 2}}, 'volume', planning_hierarchy=True)
    assert scoped == {'world_design': {'x': 1}}

    pol = normalize({
        'tasks': ['world_rules'], 'type_ids': ['GENRE_XUANYI'],
        'world_selection': 'ai', 'recommendation_mode': 'auto',
        'recommended_slots': {
            'tone': {'scope': 'book', 'stage': 'type_adaptation', 'versions': {'m1': 1}},
            'style': {'scope': 'chapter', 'stage': 'expression_design', 'versions': {'m2': 1}},
            'narration': {'scope': 'chapter', 'stage': 'scene_design', 'versions': {'m3': 1}},
            'world': {'scope': 'book', 'stage': 'world_design', 'versions': {'m4': 1}},
            'character': {'scope': 'volume', 'stage': 'character_design', 'versions': {'m5': 1}},
            'structure': {'scope': 'volume', 'stage': 'plot_design', 'versions': {'m6': 1}},
            'hook': {'scope': 'book', 'stage': 'plot_design', 'versions': {'m7': 1}},
        },
    })
    assert pol['recommended_slots']['structure']['scope'] == 'volume'


def test_configure_methods_manual_to_auto_invokes_freeze_automatic_policy(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    app = ProductionService(studio, LibraryService(studio.workspace), test_mode=True)
    created = app.create({
        'title': '手动切自动', 'idea': '排查印记来源。',
        'genre_ids': ['GENRE_XUANYI'], 'design_mode': 'manual',
    })
    ident = created['novel']['id']
    with pytest.raises(ValueError, match='AUTO_RECOMMENDATIONS_MISSING'):
        app.configure_methods(ident, {'policy': {'recommendation_mode': 'auto', 'max_methods': 3},
                                      'reason': '切换为AI自动推荐'})


def test_progress_retains_book_design_tree_beyond_thirty_jobs(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    app = ProductionService(studio, LibraryService(studio.workspace), test_mode=True)
    created = app.create({
        'title': '长篇保留设计树', 'idea': '多章后仍可查看全书设计。',
        'genre_ids': ['GENRE_XUANYI'], 'design_mode': 'manual',
    })
    novel = created['novel']
    with app.open_store(novel) as store:
        ch = store.add_chapter(1, '第一章')
        sc = store.add_scene(ch.id, 1, '{"title":"场1"}')
        for _ in range(32):
            start_job(store, JobRequest('write', scene_ids=[sc.id], budget=Budget(4, 8000, 1000)))
    progress = app.progress(novel['id'])
    assert any(node.get('scope') == 'book' for node in progress['tree'])


def test_render_config_toml_empty_stage_window_and_frontend_branch_wizard_guards(tmp_path: Path) -> None:
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'studio.config.toml')
    toml_text = studio.render_config_toml({
        'model': {'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434', 'model': 'qwen'},
        'stage_models': {'write': {'model': 'qwen-writer', 'context_window_tokens': ''}},
    })
    assert 'qwen-writer' in toml_text and 'context_window_tokens' not in toml_text
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert 'wizardDirectionReview' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'prevBranch !== nextBranch' in (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'passage_sequences?.[sequence.kind]' in (js_root / 'pages' / 'corpus_view.js').read_text(encoding='utf-8')


def test_plan_remote_deletions_allows_removed_aux_files_on_matching_book(tmp_path: Path) -> None:
    from nw.studio.repository_books import plan_remote_deletions

    ws, staged = tmp_path / 'ws', tmp_path / 'staged'
    (ws / 'library').mkdir(parents=True)
    (staged / 'library').mkdir(parents=True)
    with Store(ws / 'b1', create=True, test_mode=True) as s:
        proj = s.init_project('同书')
    (staged / 'b1').mkdir()
    import shutil
    shutil.copy2(ws / 'b1' / 'nw.db', staged / 'b1' / 'nw.db')
    local = {'library/library.db', 'library/old.json', 'b1/nw.db', 'b1/exports/old.txt'}
    expected = {'library/library.db', 'b1/nw.db'}
    assert plan_remote_deletions(staged, ws, ws, local, expected) == []


def test_accept_scene_through_production_and_repo_writable_guard(tmp_path: Path) -> None:
    from types import SimpleNamespace

    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    app = ProductionService(studio, LibraryService(studio.workspace), test_mode=True)
    created = app.create({
        'title': '单场接受测试', 'idea': '检验事件和读写守卫。',
        'genre_ids': ['GENRE_XUANYI'], 'design_mode': 'manual',
    })
    ident, pdir = created['novel']['id'], created['novel']['project_dir']
    with app.open_store(created['novel']) as store:
        ch = store.add_chapter(1, '第一章')
        sc = store.add_scene(ch.id, 1, '{"title":"场1"}')
    draft = studio.save_manual_draft(pdir, sc.id, '手工撰写的一场正文。')['draft']
    delta = studio.save_manual_delta(pdir, {'draft_id': draft['id'], 'operations': []})['delta']
    res = app.accept_scene(ident, sc.id, {'draft_id': draft['id'], 'delta_id': delta['id'], 'reason': '手工审核通过'})
    assert res['head']['revision'] == 1
    assert any(ev['kind'] == 'confirmation' for ev in app.timeline(ident)['events'])

    studio.repository_sync = SimpleNamespace(enabled=True, _draining=False, restore_required=True,
                                            check_running_source=lambda: False)
    assert app._repo_writable() is False

    res_cfg = app.configure_methods(ident, {'policy': {'tasks': ['hook'], 'preferred_methods': {'m9': 2}},
                                            'reason': '人工指定方法偏好'})
    assert res_cfg['policy']['preferred_methods'] == {'m9': 2}


def test_corpus_not_observed_domain_and_nonstory_preamble_do_not_block_roster_approval(tmp_path: Path) -> None:
    from nw.studio.corpus_catalog import DOMAINS, OVERVIEW
    from nw.studio.corpus_checks import graph_issues
    from nw.studio.corpus_index import empty_document

    text = '书籍信息：神通者\n【简介】异骨设定。\n第0章 新书感言\n感谢支持！\n第1章 雷火馆\n林动推门而入，接过木牌。'
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': '前言测试', 'filename': 'preamble.txt', 'text': text})
    lib.review_book(book['id'], {'types': ['GENRE_XUANHUAN'], 'decompose': False})
    doc = empty_document(text, 'complete', '含简介与感言的完整文本')
    doc['overview'] = {k: '全书主线完整核对' for k in OVERVIEW}
    ch1 = next(u for u in doc['units'] if '第1章' in u['title'])
    ch0 = next(u for u in doc['units'] if '第0章' in u['title'])
    q1 = '林动推门而入，接过木牌。'
    q_head = '第0章 新书感言'
    doc['evidence'] = [
        {'id': 'e1', 'start': text.index(q1), 'end': text.index(q1) + len(q1), 'quote': q1, 'explanation': '第一章出场'},
        {'id': 'e0', 'start': ch0['start'], 'end': ch0['start'] + len(q_head), 'quote': q_head, 'explanation': '感言章名', 'text_role': 'heading'},
    ]
    doc['characters'] = [{'id': 'p1', 'name': '林动', 'canonical_id': None, 'role': '主角', 'goal': '入会', 'initial_state': '初入', 'final_state': '领牌', 'evidence_ids': ['e1']}]
    doc['events'] = [
        {'id': 'ov1', 'unit_id': ch1['id'], 'granularity': 'overview', 'parent_event_ids': [], 'story_order': 1,
         'summary': '入会领牌', 'characters': ['p1'], 'goal': '进馆', 'conflict': '门槛', 'choice': '推门', 'cost': '无', 'result': '领牌',
         'information_before': '', 'information_after': '', 'emotion_before': '', 'emotion_after': '', 'evidence_ids': ['e1']},
        {'id': 'ev1', 'unit_id': ch1['id'], 'granularity': 'detail', 'parent_event_ids': ['ov1'], 'story_order': 1,
         'summary': '推门领牌', 'characters': ['p1'], 'goal': '进馆', 'conflict': '门槛', 'choice': '推门', 'cost': '无', 'result': '领牌',
         'information_before': '', 'information_after': '', 'emotion_before': '', 'emotion_after': '', 'evidence_ids': ['e1']},
    ]
    doc['threads'] = [
        {'id': 'tr1', 'domain': 'cast_roster', 'title': '林动出场', 'status': 'resolved', 'characters': ['p1'], 'node_ids': ['ev1'],
         'initial_state': '馆外', 'final_state': '领牌', 'explanation': '主角出场',
         'details': {'presence': 'onstage', 'subject_kind': 'individual', 'standing': 'protagonist', 'function_kind': 'driver',
                     'chapter_function': '推动入会', 'appearance_evidence': 'e1', 'standing_evidence': 'e1'}, 'evidence_ids': ['e1']},
    ]
    doc['domains'] = [
        {'domain': d, 'status': 'observed' if d == 'cast_roster' else 'not_observed',
         'explanation': '已核实阵容' if d == 'cast_roster' else '本段未观察到',
         'evidence_ids': ['e1'] if d == 'cast_roster' else []}
        for d in DOMAINS
    ]
    saved = lib.save_corpus(book['id'], {'expected_version': 0, 'body': doc, 'reviewed_units': [u['id'] for u in doc['units'] if u['level'] == 'chapter']})
    assert not any(i['severity'] == 'error' for i in saved['issues']), saved['issues']
    assert graph_issues(saved['body'], len(text), saved['coverage'], content=text) == []
    approved = lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '非故事前言不阻断阵容核对'})
    assert approved['available'] is True


def test_corpus_calls_extract_fence_null_end_and_crlf_locate(tmp_path: Path) -> None:
    from nw.studio.corpus_calls import parse_result
    from nw.studio.corpus_merge import resolve_fragment
    from nw.studio.corpus_index import empty_document

    assert parse_result({'finish_reason': 'complete', 'text': '```json {"events":[]}```'}, lambda x: x) == {'events': []}
    assert parse_result({'finish_reason': 'complete', 'text': '说明如下：\n```json\n{"ok": 1}\n```'}, lambda x: x) == {'ok': 1}

    text = '第一章\r\n第一行正文。\r\n第二行正文。'
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': 'CRLF测试', 'filename': 'crlf.txt', 'text': text})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': False})

    located = lib.locate_method_evidence({'book_id': book['id'], 'quote': '第一行正文。\n第二行正文。', 'explanation': '跨行摘录'})
    assert located['quote'] == '第一行正文。\r\n第二行正文。'
    assert text[located['start']:located['end']] == located['quote']

    doc = empty_document(text)
    ch = next(u for u in doc['units'] if u['level'] == 'chapter')
    patch = resolve_fragment(
        {'characters': [], 'events': [{'id': 'M00001_ev1', 'unit_id': ch['id'], 'granularity': 'overview',
                                       'parent_event_ids': [], 'story_order': None, 'summary': '两行事件',
                                       'characters': [], 'goal': '', 'conflict': '', 'choice': '', 'cost': '',
                                       'result': '继续', 'information_before': '', 'information_after': '',
                                       'emotion_before': '', 'emotion_after': '', 'evidence_ids': ['M00001_q1']}],
         'evidence': [{'id': 'M00001_q1', 'start': None, 'end': None, 'quote': '第一行正文。', 'explanation': '唯一引文'}]},
        doc, text, span={'unit_id': ch['id'], 'start': ch['start'], 'end': ch['end']}, prefix='M00001', phase='survey',
    )
    assert patch['evidence'][0]['start'] == text.index('第一行正文。')


def test_kb_method_origin_binding_expression_narration_reclassify_and_downstream(tmp_path: Path) -> None:
    from nw.studio.corpus_catalog import DOMAINS, OVERVIEW
    from nw.studio.corpus_index import empty_document
    from nw.studio.corpus_methods import approved_structures_summary
    from nw.studio.method_recommendations import recommendations
    from nw.production_methods.sources import MethodReader

    text = '第1章 起步\n林渊紧握残玉，低声自语。'
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': '结构绑定测试书', 'filename': 'bind.txt', 'text': text})
    lib.review_book(book['id'], {'types': ['GENRE_XUANHUAN'], 'decompose': False})
    doc = empty_document(text, 'complete', '单章完整测试文本')
    doc['overview'] = {k: '主线核对' for k in OVERVIEW}
    ch = next(u for u in doc['units'] if u['level'] == 'chapter')
    q = '林渊紧握残玉，低声自语。'
    doc['evidence'] = [{'id': 'e1', 'start': text.index(q), 'end': text.index(q) + len(q), 'quote': q, 'explanation': '叙述细节'}]
    doc['characters'] = [{'id': 'p1', 'name': '林渊', 'canonical_id': None, 'role': '主角', 'goal': '求存', 'initial_state': '弱', 'final_state': '坚定', 'evidence_ids': ['e1']}]
    doc['events'] = [
        {'id': 'ov1', 'unit_id': ch['id'], 'granularity': 'overview', 'parent_event_ids': [], 'story_order': 1, 'summary': '握玉自语', 'characters': ['p1'], 'goal': '求存', 'conflict': '危境', 'choice': '握玉', 'cost': '无', 'result': '稳住心神', 'information_before': '', 'information_after': '', 'emotion_before': '', 'emotion_after': '', 'evidence_ids': ['e1']},
        {'id': 'ev1', 'unit_id': ch['id'], 'granularity': 'detail', 'parent_event_ids': ['ov1'], 'story_order': 1, 'summary': '林渊握玉', 'characters': ['p1'], 'goal': '求存', 'conflict': '危境', 'choice': '握玉', 'cost': '无', 'result': '稳住心神', 'information_before': '', 'information_after': '', 'emotion_before': '', 'emotion_after': '', 'evidence_ids': ['e1']},
    ]
    doc['threads'] = [
        {'id': 't_narr', 'domain': 'narration', 'title': '握玉呈现心理', 'status': 'resolved', 'characters': ['p1'], 'node_ids': ['ev1'],
         'initial_state': '紧张', 'final_state': '镇定', 'explanation': '以动作承载内心',
         'details': {'time_order': '当下即时', 'presentation': '动作与低语并呈', 'voice_access': '第三人称贴近林渊',
                     'claim_status': 'stated', 'causal_basis': '', 'character_response': '林渊自语稳心', 'reader_effect': '读者察觉残玉重要'},
         'evidence_ids': ['e1']},
        {'id': 't_roster', 'domain': 'cast_roster', 'title': '林渊在场', 'status': 'resolved', 'characters': ['p1'], 'node_ids': ['ev1'],
         'initial_state': '单独在场', 'final_state': '仍在场', 'explanation': '主角出场',
         'details': {'presence': 'onstage', 'subject_kind': 'individual', 'standing': 'protagonist', 'function_kind': 'driver',
                     'chapter_function': '推动自救', 'appearance_evidence': 'e1', 'standing_evidence': 'e1'}, 'evidence_ids': ['e1']},
    ]
    doc['domains'] = [
        {'domain': d, 'status': 'observed' if d in ('narration', 'cast_roster') else 'not_observed',
         'explanation': '已观察' if d in ('narration', 'cast_roster') else '本篇未见',
         'evidence_ids': ['e1'] if d in ('narration', 'cast_roster') else []}
        for d in DOMAINS
    ]
    lib.save_corpus(book['id'], {'expected_version': 0, 'body': doc, 'reviewed_units': [ch['id']]})
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '已批准结构'})

    summaries = approved_structures_summary(lib)
    assert len(summaries) == 1 and len(summaries[0]['threads']) == 2

    ev = lib.locate_method_evidence({'book_id': book['id'], 'quote': q, 'explanation': '表达指导证据'})
    method_body = {
        'title': '动作载体文风方法', 'tasks': ['expression'], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANHUAN'],
        'applicability': ['贴近视角下须通过细微动作展现心理压力'],
        'prerequisites': [{'key': 'i1', 'input_kind': 'scene_design', 'artifact': '场景卡', 'requirement': '已确定在场人物与心理压力'}],
        'operations': [{'key': 'op1', 'instruction': '用掌心物件动作代替直白心理描写', 'input_keys': ['i1'], 'output_keys': ['o1']}],
        'outputs': [{'key': 'o1', 'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product', 'description': '表达节拍指导'}],
        'downstream': [
            {'output_key': 'o1', 'consumer': 'writer', 'usage': '写入具体动作节拍'},
            {'output_key': 'o1', 'consumer': 'review', 'usage': '核查动作节拍可读性'},
        ],
        'acceptance': [{'output_key': 'o1', 'check': '动作与心理压力一致', 'evidence_required': '正文动作段落'}],
        'evidence': [ev], 'non_applicability': ['远景概览跳跃段不适用'],
    }
    standalone = lib.save_method({'body': method_body, 'expected_version': 0})
    assert standalone['runtime_integration'] == 'requires_approved_structure'
    bound = lib.bind_method_origin(standalone['id'], {'expected_version': 1, 'book_id': book['id'], 'thread_ids': ['t_narr']})
    assert bound['version'] == 2 and bound['runtime_integration'] == 'project_design_and_review'
    approved_method = lib.review_method(bound['id'], {'version': 2, 'decision': 'approve', 'note': '已绑定结构并独立批准'})
    assert approved_method['current_for_production'] is True

    recs = recommendations(MethodReader(lib.workspace), 'style', ['GENRE_XUANHUAN'], [], planning_hierarchy=True)
    assert any(r['id'] == approved_method['id'] for r in recs['recommendations'])

    with pytest.raises(ValueError, match='已有衍生方法依赖原确认类型'):
        lib.reclassify_book(book['id'], {'types': ['GENRE_XUANYI'], 'grade': 'A', 'note': '冲突缩减'})
    reclassified = lib.reclassify_book(book['id'], {'types': ['GENRE_XUANHUAN', 'GENRE_QIHUAN'], 'grade': 'S', 'note': '增补副类型'})
    assert set(reclassified['confirmed_types']) == {'GENRE_XUANHUAN', 'GENRE_QIHUAN'} and reclassified['grade'] == 'S'

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert 'deleteCorpusRecord' in (js_root / 'pages' / 'corpus_editor.js').read_text(encoding='utf-8')
    assert 'origin_book_id' in (js_root / 'pages' / 'methods.js').read_text(encoding='utf-8')
    assert 'reclassifyBookForm' in (js_root / 'pages' / 'staging.js').read_text(encoding='utf-8')
    assert 'materials/detail' in (js_root / 'pages' / 'kb.js').read_text(encoding='utf-8')
    assert 'planning_hierarchy:1' in (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')


def test_nonstory_preamble_preserves_cast_distribution_and_genre_samples(tmp_path: Path) -> None:
    from nw.studio.cast_samples import genre_cast_samples
    from nw.studio.corpus_cast import cast_distribution
    from nw.studio.corpus_catalog import DOMAINS, FIELDS, OVERVIEW
    from nw.studio.corpus_index import empty_document

    p1 = '阿霜递过路引，老许接过并核验印记。'
    p2 = '被称作小霜的阿霜登舟，秦师傅拦住船头。'
    text = f'书名简介内容。\n第0章 新书感言\n感谢读者支持。\n# 第一章 渡口\n{p1}\n# 第二章 登舟\n{p2}'
    lib = LibraryService(tmp_path / 'ws')
    book = lib.import_book({'title': '带感言完整样本', 'filename': 'preamble.txt', 'text': text})['id']
    lib.review_book(book, {'types': ['GENRE_XUANYI'], 'decompose': False})

    doc = empty_document(text, extent='complete', note='含简介与新书感言的完整文本')
    chapters = [u for u in doc['units'] if u['level'] == 'chapter']
    assert len(chapters) == 4  # preamble + 第0章 新书感言 + 第一章 + 第二章
    c1, c2 = chapters[2]['id'], chapters[3]['id']
    doc['overview'] = dict.fromkeys(OVERVIEW, '核对过全书主线')
    doc['evidence'] = [
        {'id': 'q0', 'start': text.index('感谢读者支持。'), 'end': text.index('感谢读者支持。') + len('感谢读者支持。'),
         'quote': '感谢读者支持。', 'explanation': '作者感言', 'text_role': 'reader_address'},
        {'id': 'q1', 'start': text.index(p1), 'end': text.index(p1) + len(p1), 'quote': p1, 'explanation': '第一章事件'},
        {'id': 'q2', 'start': text.index(p2), 'end': text.index(p2) + len(p2), 'quote': p2, 'explanation': '第二章事件'},
    ]
    for key, name, alias, q in [('a', '阿霜', None, 'q1'), ('x', '小霜', 'a', 'q2'), ('b', '老许', None, 'q1'), ('c', '秦师傅', None, 'q2')]:
        doc['characters'].append({**dict.fromkeys(FIELDS['characters'], ''), 'id': key, 'name': name,
                                  'canonical_id': alias, 'evidence_ids': [q]})
    doc['events'] = [
        {**dict.fromkeys(FIELDS['events'], ''), 'id': 'o1', 'unit_id': c1, 'granularity': 'overview',
         'parent_event_ids': [], 'story_order': 1, 'summary': p1, 'result': '完成核验', 'characters': ['a', 'b'], 'evidence_ids': ['q1']},
        {**dict.fromkeys(FIELDS['events'], ''), 'id': 'e1', 'unit_id': c1, 'granularity': 'detail',
         'parent_event_ids': ['o1'], 'story_order': 1, 'summary': p1, 'result': '完成核验', 'characters': ['a', 'b'], 'evidence_ids': ['q1']},
        {**dict.fromkeys(FIELDS['events'], ''), 'id': 'o2', 'unit_id': c2, 'granularity': 'overview',
         'parent_event_ids': [], 'story_order': 2, 'summary': p2, 'result': '船头受阻', 'characters': ['x', 'c'], 'evidence_ids': ['q2']},
        {**dict.fromkeys(FIELDS['events'], ''), 'id': 'e2', 'unit_id': c2, 'granularity': 'detail',
         'parent_event_ids': ['o2'], 'story_order': 2, 'summary': p2, 'result': '船头受阻', 'characters': ['x', 'c'], 'evidence_ids': ['q2']},
    ]
    for tid, person, ev_id, q, standing, fn in [
        ('ra', 'a', 'e1', 'q1', 'protagonist', 'driver'),
        ('rb', 'b', 'e1', 'q1', 'supporting', 'handoff'),
        ('rx', 'x', 'e2', 'q2', 'protagonist', 'driver'),
        ('rc', 'c', 'e2', 'q2', 'antagonist', 'opponent'),
    ]:
        doc['threads'].append({
            'id': tid, 'domain': 'cast_roster', 'title': '核对' + person, 'status': 'resolved',
            'characters': [person], 'node_ids': [ev_id], 'initial_state': '入场', 'final_state': '离场',
            'explanation': '按原句登记', 'evidence_ids': [q],
            'details': {'presence': 'onstage', 'subject_kind': 'individual', 'standing': standing,
                        'function_kind': fn, 'chapter_function': '推动/阻碍渡口事件',
                        'appearance_evidence': q, 'standing_evidence': q},
        })
    doc['domains'] = [
        {'domain': d, 'status': 'observed' if d == 'cast_roster' else 'not_observed',
         'explanation': '逐章核对' if d == 'cast_roster' else '本样本仅测阵容',
         'evidence_ids': ['q1'] if d == 'cast_roster' else []}
        for d in DOMAINS
    ]
    lib.save_corpus(book, {'expected_version': 0, 'body': doc, 'reviewed_units': [u['id'] for u in chapters]})
    lib.review_corpus(book, {'version': 1, 'decision': 'approve', 'note': '已核对含感言完整文本', 'accept_limitations': True})

    stats = cast_distribution(lib.get_corpus(book)['body'])
    assert [row['coverage'] for row in stats['chapters']] == ['non_story', 'non_story', 'verified', 'verified']
    assert stats['chapters'][2]['first_count'] == 2 and stats['chapters'][2]['returning_count'] == 0
    assert stats['chapters'][3]['first_count'] == 1 and stats['chapters'][3]['returning_count'] == 1
    assert stats['chapters'][3]['prior_appearance_unresolved_ids'] == []

    sample = genre_cast_samples(lib, ['GENRE_XUANYI'])
    assert sample['complete_count'] == 1 and sample['book_range'] == {'min': 3, 'max': 3}
    assert sample['sources'][0]['included_in_book_range'] is True
    assert sample['sources'][0]['coverage_gaps'] == []
    assert sample['chapter_bands']['opening']['chapter_count'] == 1
    assert sample['chapter_bands']['ending']['first'] == {'min': 1, 'max': 1}
    assert sample['chapter_bands']['ending']['returning'] == {'min': 1, 'max': 1}


def test_corpus_progress_timeout_resume_context_and_non_narration_expression(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace
    from corpus_fixture import CorpusModel, make_book, runtime, start_analysis, wait_job
    from nw.studio.corpus_catalog import DOMAINS, OVERVIEW, corpus_catalog
    from nw.studio.corpus_context import window_payload
    from nw.studio.corpus_index import empty_document
    from nw.studio.corpus_methods import check_narration_method
    from nw.studio.corpus_pipeline import save_state
    from nw.studio.corpus_prompts import INSTRUCTIONS, messages

    cat = corpus_catalog()
    assert 'analyst_inference' in cat['boundary_bases']
    assert 'overview_events为空' in INSTRUCTIONS['detail']
    rel_msg = messages('relations', {'domain': 'cast_entry', 'events': []}, version=5)[0]['content']
    assert '不得修改既有线索的details' in rel_msg

    # Verify window_payload propagates open_threads characters, canonical_id ancestors and character evidence.
    doc = {
        'schema_version': 5, 'source_extent': {'status': 'complete', 'note': 'ok'}, 'overview': dict.fromkeys(OVERVIEW, 'ok'),
        'units': [{'id': 'c1', 'level': 'chapter', 'title': 'c1', 'parent_id': 'book', 'start': 0, 'end': 40}],
        'characters': [
            {'id': 'p_root', 'name': '沈青', 'canonical_id': None, 'evidence_ids': ['e_root']},
            {'id': 'p_alias', 'name': '青衣客', 'canonical_id': 'p_root', 'evidence_ids': ['e_alias']},
            {'id': 'p_thread', 'name': '周掌柜', 'canonical_id': None, 'evidence_ids': ['e_thr']},
        ],
        'events': [
            {'id': 'ev1', 'unit_id': 'c1', 'granularity': 'detail', 'parent_event_ids': [],
             'characters': ['p_alias'], 'evidence_ids': ['e_ev1']},
        ],
        'threads': [
            {'id': 't1', 'domain': 'cast_entry', 'title': '登场', 'status': 'open', 'characters': ['p_thread'],
             'node_ids': ['ev1'], 'evidence_ids': ['e_ev1']},
        ],
        'evidence': [
            {'id': 'e_root', 'start': 0, 'end': 5, 'quote': '沈青出场。'},
            {'id': 'e_alias', 'start': 5, 'end': 10, 'quote': '人称青衣。'},
            {'id': 'e_thr', 'start': 10, 'end': 15, 'quote': '周掌柜道。'},
            {'id': 'e_ev1', 'start': 15, 'end': 25, 'quote': '青衣客递上信件。'},
        ],
    }
    payload = window_payload(doc, doc['events'], domain='cast_entry', prefix='R_1_00000', last=True)
    assert {c['id'] for c in payload['characters']} == {'p_root', 'p_alias', 'p_thread'}
    assert {'e_root', 'e_alias', 'e_thr', 'e_ev1'} <= {e['id'] for e in payload['evidence']}

    # Verify save_state updates staging_books.progress and timeout-only changes allow corpus resume.
    from corpus_fixture import SOURCE
    lib = LibraryService(tmp_path / 'ws')
    provider = CorpusModel()
    provider.fail_at = 2
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'filename': '[FAKE] queued.md', 'title': '[FAKE] 实时进度测试', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    assert lib.get_staging(book['id'])['progress'] == 0.0
    started = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 进度测试'}})
    job = wait_job(lib, book['id'], started['id'])
    assert job['status'] == 'paused'
    assert 0.0 < lib.get_staging(book['id'])['progress'] < 1.0

    provider.fail_at = None
    slower = SimpleNamespace(**{**runtime().__dict__, 'timeout': 300.0})
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (slower, provider))
    lib.control_corpus_job(book['id'], job['id'], {'action': 'resume', 'retry_failed': True})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    assert done['runtime']['timeout'] == 300.0
    assert lib.get_staging(book['id'])['progress'] == 1.0

    # Verify non-narration threads (e.g., pacing) can still derive expression (style) methods without being blocked.
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    pacing_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'pacing')
    ev_row = next(e for e in structure['body']['evidence'] if e['id'] in pacing_thread['evidence_ids'])
    pacing_expression_body = {
        'tasks': ['expression'], 'type_tags': ['GENRE_XUANYI'],
        'evidence': [{'book_id': book['id'], 'start': ev_row['start'], 'end': ev_row['end'], 'quote': ev_row['quote']}],
    }
    pacing_basis = {'thread_ids': [pacing_thread['id']], 'event_ids': pacing_thread['node_ids'], 'link_ids': []}
    check_narration_method(lib, structure, pacing_expression_body, pacing_basis)
    with pytest.raises(ValueError, match='叙述方法须使用已核实的叙述观察'):
        check_narration_method(lib, structure, {**pacing_expression_body, 'tasks': ['narration']}, pacing_basis)


def test_hierarchical_volume_refresh_followup_and_gate_labels(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.materials.network_followup import POLICY as FOLLOWUP_POLICY, merge_followup
    from nw.materials.network_workflow import POLICY as NETWORK_POLICY
    from nw.materials.phase_routes import phase_order
    from nw.production_methods.refresh import _prior_products
    from nw.store import Store
    from nw.studio.production_views import ProductionViews
    from nw.task_models import InputManifest, canonical, content_sha256
    from nw.tasks import freeze_manifest

    # Verify _prior_products handles planning_hierarchy=True on scope='volume' (7 stages),
    # static_relations followup delta merge, and source-step-cast-repair-v1 replacement.
    from nw.call_budget import create_budget
    from nw.task_models import Budget
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        project = store.init_project('分级刷新测试')
        job_id = create_budget(store, 'job-vol-1', Budget(20, 90000, 4000))
        base_manifest = 'plan:task-vol-1'
        vol_stages = phase_order('volume', planning_hierarchy=True)
        assert vol_stages[-1] == 'bind_scope' and len(vol_stages) == 7

        def record_stage(call_id: str, stage: str, products: dict, version: str = 'source-step-v4',
                         extra_input: dict | None = None) -> None:
            mid = f'm:{call_id}'
            study = {'stage': stage, 'scope': 'volume', **(extra_input or {})}
            pkg = {'base_plan_manifest': base_manifest, 'study_input': study}
            manifest = InputManifest(
                id=mid, purpose='material_work', branch_id='main', state_revision=0, story_order=0,
                disclosure_order=[0, 0, 0], dependency_refs=[], candidate_delta_refs=[],
                settings={'provider': 'fake', 'model': 'm', 'params': {}, 'prompt_version': version,
                          'base_url': None, 'timeout': 60.0, 'stream': False},
                context_sha256=content_sha256(pkg),
            )
            freeze_manifest(store, manifest, pkg)
            with store.connection:
                store.connection.execute(
                    "INSERT INTO task_calls(id,project_id,kind,manifest_id,manifest_json,request_json,messages_json,"
                    "budget_id,root_id,attempt,status,finish_reason,validation,result_json,reason,usage_json,started_at,ended_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (call_id, project.id, 'material_work', mid, canonical(asdict(manifest)), '{}', '[]',
                     job_id, call_id, 1, 'FINISHED', 'complete', 'VALID',
                     canonical({'stage': stage, 'products': products}), None, '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:01Z'),
                )

        record_stage('c1', 'type_selection', {'selection': [{'id': 'GENRE_XUANYI'}]})
        record_stage('c2', 'type_adaptation', {'adaptations': [{'type_refs': ['GENRE_XUANYI']}]})
        record_stage('c3', 'world_design', {'members': [{'key': 'w1', 'kind': 'world'}]})
        record_stage('c4', 'character_design', {'members': [{'key': 'p1', 'kind': 'character'}]})
        record_stage('c5', 'static_relations', {'relations': [{'source': 'p1', 'target': 'w1', 'relation': '受制', 'condition': '夜晚'}],
                                                'requirements': [], '_uses': [], '_excluded': [], '_criteria': []})
        # Simulate a static_relations follow-up delta call appending a requirement.
        record_stage('c5f', 'static_relations',
                     {'requirements': [{'id': 'r1', 'source_id': 's1', 'target_stage': 'plot_design', 'constraint': '夜晚触发限制', 'project_refs': ['member:p1']}],
                      '_uses': [{'source_id': 's1', 'output_refs': ['requirement:r1']}], '_excluded': [], '_criteria': []},
                     version='static-network-followup-v1',
                     extra_input={'static_relations_basis': {'ref': {'task_id': 'c5'}}})
        # Simulate cast_gap repair replacing character_design.
        record_stage('c4r', 'character_design', {'members': [{'key': 'p1', 'kind': 'character'}, {'key': 'p2', 'kind': 'character'}]},
                     version='source-step-cast-repair-v1')
        record_stage('c6', 'plot_design', {'directions': [{'title': '卷一'}], 'members': [{'key': 'v1', 'kind': 'volume'}]})

        prior = _prior_products(store, job_id, base_manifest, 'volume', 'bind_scope', planning_hierarchy=True)
        assert set(prior) == set(vol_stages[:-1])
        assert prior['character_design']['task_id'] == 'c4r'
        assert len(prior['character_design']['products']['members']) == 2
        assert prior['static_relations']['task_id'] == 'c5f'
        assert len(prior['static_relations']['products']['requirements']) == 1

    # Verify merge_followup respects planning_hierarchy=True on volume (rejects scene_design target_stage).
    basis_products = {'relations': [{'source': 'p1', 'target': 'w1', 'relation': '受制', 'condition': '夜'}],
                      'requirements': [], '_uses': [], '_excluded': [], '_criteria': []}
    basis = {'stage': 'static_relations', 'task_id': 't1', 'sha256': content_sha256(basis_products),
             'source_ids': ['base1'], 'products': basis_products}
    delta = {'requirements': [{'id': 'r1', 'source_id': 'dyn1', 'target_stage': 'scene_design',
                               'constraint': '具体到夜晚场景必须体现代价与制约', 'project_refs': ['member:p1', 'member:w1']}],
             '_uses': [{'source_id': 'dyn1', 'output_refs': ['requirement:r1']}],
             '_excluded': [], '_criteria': [{'source_id': 'dyn1', 'clauses': []}]}
    sources = [{'source': {'id': 'dyn1', 'key': 'dyn1', 'profile': 'dynamic_relation'}}]
    ctx = {'scope': 'volume', 'planning_hierarchy': True,
           'same_stage_network_policy': FOLLOWUP_POLICY, 'network_prerequisite_policy': NETWORK_POLICY}
    with pytest.raises(ValueError, match='later stage in scope'):
        merge_followup(basis, delta, sources, {}, ctx)

    # Verify gate summary and frontend labels for production_method_selection, keep action, and non_story coverage.
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert "production_method_selection" in (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert "keep:'保留当前草稿'" in (js_root / 'pages' / 'studio-decisions.js').read_text(encoding='utf-8')
    assert "c.coverage==='non_story'" in (js_root / 'pages' / 'corpus_view.js').read_text(encoding='utf-8')
    assert '制作方法待确认' in (ROOT / 'src' / 'nw' / 'studio' / 'production_views.py').read_text(encoding='utf-8')


def test_step_material_blueprint_covers_all_17_steps_and_live_library_coverage(tmp_path: Path, monkeypatch) -> None:
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.corpus_catalog import DOMAINS
    from nw.studio.step_material_blueprint import build_step_blueprint

    lib = LibraryService(tmp_path / 'ws')
    initial = build_step_blueprint(lib)
    assert initial['summary']['total_steps'] == 17
    assert initial['summary']['design_steps'] == 14
    assert initial['summary']['execution_steps'] == 3
    assert initial['summary']['covered_steps'] == 0
    assert len(initial['summary']['gap_steps']) == 17
    assert [m['step'] for m in initial['methodology']] == ['read', 'retrieve', 'judge_function', 'judge_method']
    assert len(initial['material_natures']) == 6
    assert set(initial['domain_bindings']) == set(DOMAINS)
    for step in initial['steps']:
        assert step['workflow_material_key_count'] > 0, step['step_id']
        assert step['need_categories'], step['step_id']
        assert step['material_natures'], step['step_id']
        guide = step['decomposition_guide']
        assert {'reading_target', 'retrieval_cues', 'functional_judgment', 'method_judgment'} <= set(guide)

    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'filename': '[FAKE] blueprint.md', 'title': '[FAKE] 步骤绑定闭环测试', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整样本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])

    # 1) Derive an anchors method (anchor_design.beats) from a narration thread.
    narration_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'narration')
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    nar_ev_ids = list(dict.fromkeys(narration_thread['evidence_ids']))
    anchor_method = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [narration_thread['id']]},
        'body': {
            'title': '具象感官节拍落点法',
            'tasks': ['anchors'],
            'type_tags': ['GENRE_XUANYI'],
            'scopes': ['chapter', 'scene'],
            'applicability': ['受限视角下需要外化情绪或警惕感'],
            'prerequisites': [{'key': 'in_scene', 'input_kind': 'scene_design',
                               'artifact': '场景设计与POV边界', 'requirement': '明确本场观察者视角与需外化的情绪转折'}],
            'operations': [{'key': 'op_beat', 'instruction': '先写观察者可见的动作停顿与物件触感，再用短句落点，不直接替人物下情绪结论。',
                            'input_keys': ['in_scene'], 'output_keys': ['out_beat']}],
            'outputs': [{'key': 'out_beat', 'stage': 'anchor_design', 'field': 'beats', 'artifact_kind': 'stage_product',
                         'description': '产出带观察者与触发时机的具象锚点节拍'}],
            'downstream': [
                {'output_key': 'out_beat', 'consumer': 'writer', 'usage': '落笔时逐拍写出可见动作与物件细节，不写抽象心理标签'},
                {'output_key': 'out_beat', 'consumer': 'review', 'usage': '检查正文是否存在可引用的具象感官与动作段落'},
            ],
            'acceptance': [{'output_key': 'out_beat',
                            'check': '正文存在观察者可见动作与感官细节承载情绪，未用直白心理总结替代',
                            'evidence_required': '正文锚点落点精确引文'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': ev_by_id[eid].get('explanation') or '原文叙述锚点依据'}
                for eid in nar_ev_ids
            ],
            'non_applicability': ['大段快速概述过渡段不需要逐拍展开感官细节'],
        },
    })
    lib.review_method(anchor_method['id'], {'version': 1, 'decision': 'approve', 'note': '验收通过'})

    # 2) Derive an action_chain method (action_design.candidates) from a chapter_progress thread.
    progress_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'chapter_progress')
    prog_ev_ids = list(dict.fromkeys(progress_thread['evidence_ids']))
    action_method = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [progress_thread['id']]},
        'body': {
            'title': '章场受阻试错行动链法',
            'tasks': ['action_chain'],
            'type_tags': ['GENRE_XUANYI'],
            'scopes': ['chapter', 'scene'],
            'applicability': ['单章行动推进需要真实博弈阻力与试错过程'],
            'prerequisites': [{'key': 'in_ev', 'input_kind': 'event_design',
                               'artifact': '事件候选', 'requirement': '明确前驱压力与当前阻碍条件'}],
            'operations': [{'key': 'op_act', 'instruction': '承接前场压力设计首要行动、遭遇阻力后的次级应对与明确代价，避免一步直达结果。',
                            'input_keys': ['in_ev'], 'output_keys': ['out_act']}],
            'outputs': [{'key': 'out_act', 'stage': 'action_design', 'field': 'candidates', 'artifact_kind': 'stage_product',
                         'description': '产出含障碍、应对与失败代价的候选行动链'}],
            'downstream': [
                {'output_key': 'out_act', 'consumer': 'scene_design', 'usage': '将行动受阻节点排入场内冲突与选择'},
                {'output_key': 'out_act', 'consumer': 'review', 'usage': '核验行动是否付出实际代价且推动局面位移'},
            ],
            'acceptance': [{'output_key': 'out_act',
                            'check': '行动链完整呈现尝试、受阻、改策与真实代价并改变局势',
                            'evidence_required': '正文行动受阻与付出代价片段引文'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': ev_by_id[eid].get('explanation') or '原文章场行动依据'}
                for eid in prog_ev_ids
            ],
            'non_applicability': ['纯过场衔接场景无博弈冲突'],
        },
    })
    lib.review_method(action_method['id'], {'version': 1, 'decision': 'approve', 'note': '验收通过'})

    # Verify derived_methods tracks thread_ids accurately for the UI badge.
    refreshed_corpus = lib.get_corpus(book['id'])
    tracked_threads = {tid for item in refreshed_corpus['derived_methods'] for tid in item.get('thread_ids', ())}
    assert {narration_thread['id'], progress_thread['id']} <= tracked_threads

    # Verify live blueprint coverage and stage filtering.
    after = build_step_blueprint(lib)
    by_step = {row['step_id']: row for row in after['steps']}
    assert by_step['anchor_design']['library_coverage']['status'] == 'covered'
    assert anchor_method['id'] in by_step['anchor_design']['library_coverage']['approved_method_ids']
    assert by_step['action_design']['library_coverage']['status'] == 'covered'
    assert action_method['id'] in by_step['action_design']['library_coverage']['approved_method_ids']
    assert by_step['writer']['library_coverage']['status'] == 'covered'
    assert by_step['review']['library_coverage']['status'] == 'covered'
    assert after['summary']['covered_steps'] >= 4

    assert {m['id'] for m in lib.list_methods(stage='anchor_design')['methods']} == {anchor_method['id']}
    assert {m['id'] for m in lib.list_methods(stage='action_design')['methods']} == {action_method['id']}
    assert {m['id'] for m in lib.list_methods(stage='writer')['methods']} == {anchor_method['id']}
    with pytest.raises(ValueError, match='方法筛选条件无效'):
        lib.list_methods(stage='bogus_stage')


def test_step_blueprint_http_routes_prompts_and_client_full_chain(tmp_path: Path) -> None:
    import threading
    from nw.studio.corpus_catalog import DOMAINS
    from nw.studio.corpus_prompts import messages, method_messages

    # 1) Verify relations prompt injects step-demand guide while staying craft=False clean.
    rel_no_craft = messages('relations', {'domain': 'narration', 'events': []}, version=5, craft=False)[0]['content']
    assert '【步骤资料需求绑定】' in rel_no_craft
    assert '读取→检索→判定作用性→判定方式性' in rel_no_craft
    assert 'sensory_evidence' not in rel_no_craft and 'reader_address' not in rel_no_craft

    # 2) Verify method_messages injects structured target_step_blueprint into payload.
    m_msgs = method_messages({'thread': {'id': 't1', 'domain': 'world_rules', 'title': '铁律'}, 'events': [], 'evidence': []})
    assert 'target_step_blueprint' in m_msgs[0]['content']
    user_payload = json.loads(m_msgs[1]['content'])
    bp_guide = user_payload['target_step_blueprint']
    assert bp_guide['source_domain'] == 'world_rules'
    assert any(t['step'] == 'world_design' for t in bp_guide['target_steps'])
    assert bp_guide['functional_role_check'] and bp_guide['method_pattern_check']

    # 3) Verify HTTP APIs: /api/kb/step-blueprint, /api/kb/methods?stage=..., /api/corpus/catalog, /api/config/routing.
    studio = StudioService(tmp_path / 'ws', config_path=tmp_path / 'missing.toml')
    vol_bp = studio.pipeline_blueprint('volume', planning_hierarchy=True)
    assert len(vol_bp['design_steps']) == 7 and vol_bp['design_steps'][-1]['stage'] == 'bind_scope'
    assert all(s['need_categories'] and s['material_natures'] and s['decomposition_guide'] for s in vol_bp['design_steps'])

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200 and body_bp['summary']['total_steps'] == 17 and set(body_bp['domain_bindings']) == set(DOMAINS)

        st_cat, body_cat = get_json('/api/corpus/catalog')
        assert st_cat == 200
        assert len(body_cat['decomposition_methodology']) == 4
        assert len(body_cat['material_natures']) == 6
        assert set(body_cat['domain_bindings']) == set(DOMAINS)

        st_m_ok, body_m_ok = get_json('/api/kb/methods?stage=anchor_design')
        assert st_m_ok == 200 and body_m_ok['methods'] == []
        st_m_bad, _ = get_json('/api/kb/methods?stage=invalid_stage')
        assert st_m_bad == 400

        st_cfg, body_cfg = get_json('/api/config/routing')
        assert st_cfg == 200 and any(r['stage'] == 'decompose' for r in body_cfg['runtime_stages'])
    finally:
        server.shutdown()
        server.server_close()

    # 4) Verify frontend full-chain enhancements are wired.
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert '/kb/step-blueprint' in (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'prerequisiteScope' in (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'decomposition_methodology' in (js_root / 'pages' / 'corpus_view.js').read_text(encoding='utf-8')
    assert 'pickFirst20Threads' in (js_root / 'pages' / 'corpus_jobs.js').read_text(encoding='utf-8')
    assert 'name="stage"' in (js_root / 'pages' / 'methods.js').read_text(encoding='utf-8')
    assert 'originStepHint' in (js_root / 'pages' / 'methods.js').read_text(encoding='utf-8')
    assert 'directionReview' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert "volume:'卷纲'" in (js_root / 'components' / 'CreationPlan.js').read_text(encoding='utf-8')
    assert 'state_propagation' in (js_root / 'pages' / 'project-methods.js').read_text(encoding='utf-8')
    assert 'renderToolbar()' in (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'in_branch_workbench' in (js_root / 'pages' / 'book.js').read_text(encoding='utf-8')


def test_downstream_handoff_audit_and_originality_advisory(tmp_path: Path, monkeypatch) -> None:
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.downstream_handoff import audit_downstream_handoff

    lib = LibraryService(tmp_path / 'ws')
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'filename': '[FAKE] handoff.md', 'title': '[FAKE] 下游接收体检样本', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}

    def make_ev(thread: dict, fallback: str) -> list[dict]:
        eids = list(dict.fromkeys([
            *thread['evidence_ids'],
            *(eid for ev in structure['body']['events'] if ev['id'] in thread['node_ids'] for eid in ev['evidence_ids']),
        ]))
        return [
            {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
             'quote': ev_by_id[eid]['quote'], 'explanation': ev_by_id[eid].get('explanation') or fallback}
            for eid in eids
        ]

    world_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'world_rules')
    nar_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'narration')
    prog_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'chapter_progress')

    # M1: Valid book world_rules method -> receivable at book.world_design
    m_world = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [world_thread['id']]},
        'body': {
            'title': '规则代价约束立卡法',
            'tasks': ['world_rules'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'applicability': ['悬疑题材需要硬性制度或物理约束驱动选择'],
            'prerequisites': [{'key': 'in_adapt', 'input_kind': 'type_adaptation',
                               'artifact': '类型适配参数', 'requirement': '已明确类型边界与适配限制'}],
            'operations': [{'key': 'op_w', 'instruction': '将制度门槛、例外条件与代价分别写入世界卡规则与限制。',
                            'input_keys': ['in_adapt'], 'output_keys': ['out_w']}],
            'outputs': [{'key': 'out_w', 'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world',
                         'description': '生成含规则主体与硬限制的世界卡'}],
            'downstream': [{'output_key': 'out_w', 'consumer': 'plot_design', 'usage': '剧情冲突必须体现该世界限制与代价'}],
            'acceptance': [{'output_key': 'out_w', 'check': '世界卡写明规则与代价且被剧情承接', 'evidence_required': '正文受限选择引文'}],
            'evidence': make_ev(world_thread, '原作世界规则依据'),
            'non_applicability': ['无规则限制的纯日常散文'],
        },
    })
    lib.review_method(m_world['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})

    # M2: Valid chapter anchors method -> receivable at chapter.anchor_design
    m_anchor = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [nar_thread['id']]},
        'body': {
            'title': '感官微动作情绪锚点法',
            'tasks': ['anchors'], 'scopes': ['chapter', 'scene'], 'type_tags': ['GENRE_XUANYI'],
            'applicability': ['需要以观察者可见细节外化警惕情绪'],
            'prerequisites': [{'key': 'in_sc', 'input_kind': 'scene_design',
                               'artifact': '场景设计', 'requirement': '明确本场观察者与动作节点'}],
            'operations': [{'key': 'op_a', 'instruction': '将情绪转折拆成观察者可见的动作停顿与物件触感节拍。',
                            'input_keys': ['in_sc'], 'output_keys': ['out_a']}],
            'outputs': [{'key': 'out_a', 'stage': 'anchor_design', 'field': 'beats', 'artifact_kind': 'stage_product',
                         'description': '产出可观察的具象锚点节拍'}],
            'downstream': [{'output_key': 'out_a', 'consumer': 'writer', 'usage': '落笔写出具象动作与感官细节'}],
            'acceptance': [{'output_key': 'out_a', 'check': '正文存在具象动作与感官细节', 'evidence_required': '正文片段引文'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': ev_by_id[eid].get('explanation') or '原作叙述依据'}
                for eid in dict.fromkeys(nar_thread['evidence_ids'])
            ],
            'non_applicability': ['大段快速概述过渡'],
        },
    })
    lib.review_method(m_anchor['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})

    # M3: Valid chapter action_chain method -> receivable at chapter.action_design
    m_action = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [prog_thread['id']]},
        'body': {
            'title': '受阻变通试错行动链法',
            'tasks': ['action_chain'], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI'],
            'applicability': ['单章行动推进存在明确阻碍与代价博弈'],
            'prerequisites': [{'key': 'in_ev', 'input_kind': 'event_design',
                               'artifact': '事件候选', 'requirement': '已具备前驱事件与阻碍条件'}],
            'operations': [{'key': 'op_act', 'instruction': '设计首要尝试、受阻折返、改策应对与真实代价。',
                            'input_keys': ['in_ev'], 'output_keys': ['out_act']}],
            'outputs': [{'key': 'out_act', 'stage': 'action_design', 'field': 'candidates', 'artifact_kind': 'stage_product',
                         'description': '产出带阻碍和代价的行动链候选'}],
            'downstream': [{'output_key': 'out_act', 'consumer': 'scene_design', 'usage': '纳入本场选择与冲突'}],
            'acceptance': [{'output_key': 'out_act', 'check': '行动体现受阻改策与代价', 'evidence_required': '正文行动片段'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': ev_by_id[eid].get('explanation') or '原文章场依据'}
                for eid in dict.fromkeys(prog_thread['evidence_ids'])
            ],
            'non_applicability': ['无博弈冲突的过场'],
        },
    })
    lib.review_method(m_action['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})

    # M4: Unapproved draft
    lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [prog_thread['id']]},
        'body': {'title': '未审核草稿方法', 'tasks': ['chapter_outline'], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI']},
    })

    # M5: Approved WITHOUT structure_origin -> blocked from production
    m_no_origin = lib.save_method({
        'expected_version': 0,
        'body': {
            'title': '未绑结构的悬疑节奏法',
            'tasks': ['pacing'], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI'],
            'applicability': ['章内快慢交替'],
            'prerequisites': [{'key': 'in_p', 'input_kind': 'plot_design', 'artifact': '章纲', 'requirement': '已有章纲节点'}],
            'operations': [{'key': 'op_p', 'instruction': '在紧张冲突前后插入短缓冲段拉大节奏对比。',
                            'input_keys': ['in_p'], 'output_keys': ['out_p']}],
            'outputs': [{'key': 'out_p', 'stage': 'plot_design', 'field': 'reader_plan', 'artifact_kind': 'stage_product',
                         'description': '节奏张弛安排'}],
            'downstream': [{'output_key': 'out_p', 'consumer': 'scene_design', 'usage': '控制各场长度'}],
            'acceptance': [{'output_key': 'out_p', 'check': '正文存在明显张弛交替', 'evidence_required': '正文段落'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': '原文摘录'}
                for eid in list(dict.fromkeys(prog_thread['evidence_ids']))[:1]
            ],
            'non_applicability': ['单段微小说'],
        },
    })
    lib.review_method(m_no_origin['id'], {'version': 1, 'decision': 'approve', 'note': '仅资料库批准'})

    # M6: Approved WITH structure_origin, but asks for unreachable later prerequisite `scene_design` at `book.world_design`
    m_bad_prereq = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [world_thread['id']]},
        'body': {
            'title': '前置倒挂世界法',
            'tasks': ['world_rules'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'applicability': ['用于测试不可达前置体检拦截'],
            'prerequisites': [
                {'key': 'in_adapt', 'input_kind': 'type_adaptation', 'artifact': '类型适配', 'requirement': '需先有类型适配'},
                {'key': 'in_scene', 'input_kind': 'scene_design', 'artifact': '场景设计', 'requirement': '错误要求全书世界步读取场景设计'},
            ],
            'operations': [{'key': 'op_w', 'instruction': '按类型适配与场景前置写入世界规则卡。',
                            'input_keys': ['in_adapt', 'in_scene'], 'output_keys': ['out_w']}],
            'outputs': [{'key': 'out_w', 'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world',
                         'description': '世界规则卡'}],
            'downstream': [{'output_key': 'out_w', 'consumer': 'plot_design', 'usage': '供剧情约束'}],
            'acceptance': [{'output_key': 'out_w', 'check': '世界卡有明确限制', 'evidence_required': '正文片段'}],
            'evidence': make_ev(world_thread, '原作世界依据'),
            'non_applicability': ['测试用途'],
        },
    })
    lib.review_method(m_bad_prereq['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})

    audit = audit_downstream_handoff(lib, types=['GENRE_XUANYI'], planning_hierarchy=True)
    assert audit['summary']['receivable_methods'] == 3
    assert audit['summary']['draft_methods'] == 1
    assert audit['summary']['blocked_methods'] == 2
    assert audit['summary']['book_world_ready'] is True
    assert audit['originality_audit']['distinct_source_books'] == 1
    assert any(w['code'] == 'TYPE_F_SINGLE_SOURCE_CONCENTRATION' for w in audit['originality_audit']['warnings'])

    by_id = {m['id']: m for m in audit['methods']}
    assert by_id[m_no_origin['id']]['status'] == 'blocked'
    assert any('未绑定已批准的 v5 参考作品结构' in r for r in by_id[m_no_origin['id']]['block_reasons'])
    assert by_id[m_bad_prereq['id']]['status'] == 'blocked'
    assert any('场景设计' in r for r in by_id[m_bad_prereq['id']]['block_reasons'])

    world_board = next(b for b in audit['auto_readiness']['boards'] if b['slot'] == 'world')
    assert world_board['ready'] is True
    assert audit['auto_readiness']['ready'] is False
    assert audit['auto_readiness']['missing_boards']

    # When active_tasks is restricted to ['world_rules'], M2 and M3 show up as inactive_by_policy.
    scoped = audit_downstream_handoff(lib, types=['GENRE_XUANYI'], planning_hierarchy=True, active_tasks=['world_rules'])
    assert scoped['summary']['receivable_methods'] == 1
    assert scoped['summary']['inactive_methods'] == 2


def test_book_directions_type_adaptation_portfolio_and_http_handoff_chain(tmp_path: Path, monkeypatch) -> None:
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.book_directions import _creation_input
    from nw.materials.phase_flow import _reference_method_portfolio
    from nw.novel_store import Journal

    ws = tmp_path / 'ws'
    studio = StudioService(ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'filename': '[FAKE] chain.md', 'title': '[FAKE] 全链路对接参考书', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    world_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'world_rules')
    nar_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'narration')
    prog_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'chapter_progress')

    def save_and_approve(title: str, task: str, scope: str, stage: str, field: str, kind: str,
                         in_kind: str, consumer: str, thread: dict) -> dict:
        eids = list(dict.fromkeys([
            *thread['evidence_ids'],
            *(eid for ev in structure['body']['events'] if ev['id'] in thread['node_ids'] for eid in ev['evidence_ids'])
        ])) if thread['domain'] == 'world_rules' else list(dict.fromkeys(thread['evidence_ids']))
        saved = lib.save_method({
            'expected_version': 0,
            'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [thread['id']]},
            'body': {
                'title': title, 'tasks': [task], 'scopes': [scope], 'type_tags': ['GENRE_XUANYI'],
                'applicability': [f'{title}适用语境'],
                'prerequisites': [{'key': 'in1', 'input_kind': in_kind, 'artifact': '上游设计', 'requirement': '具备前置输入'}],
                'operations': [{'key': 'op1', 'instruction': f'按本项目前置执行{title}并写出具体产物。',
                                'input_keys': ['in1'], 'output_keys': ['out1']}],
                'outputs': [{'key': 'out1', 'stage': stage, 'field': field, 'artifact_kind': kind,
                             'description': f'{title}目标产物'}],
                'downstream': [{'output_key': 'out1', 'consumer': consumer, 'usage': '下游承接使用'}],
                'acceptance': [{'output_key': 'out1', 'check': '正文具备可验证体现', 'evidence_required': '正文引文'}],
                'evidence': [
                    {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                     'quote': ev_by_id[eid]['quote'], 'explanation': '原文依据'}
                    for eid in eids
                ],
                'non_applicability': ['不适用非对应场景'],
            },
        })
        lib.review_method(saved['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
        return saved

    m1 = save_and_approve('渡口制度代价世界法', 'world_rules', 'book', 'world_design', 'members', 'world', 'type_adaptation', 'plot_design', world_thread)
    m2 = save_and_approve('受限视角具象节拍法', 'anchors', 'chapter', 'anchor_design', 'beats', 'stage_product', 'scene_design', 'writer', nar_thread)
    m3 = save_and_approve('章场阻力试错推进法', 'action_chain', 'chapter', 'action_design', 'candidates', 'stage_product', 'event_design', 'scene_design', prog_thread)

    # 1) Verify book_directions._creation_input resolves human-readable method_summaries (no raw prose quotes!).
    policy = {
        'policy': 'project-corpus-methods-v1',
        'tasks': ['world_rules', 'anchors', 'action_chain'],
        'type_ids': ['GENRE_XUANYI'],
        'max_methods': 6,
        'preferred_methods': {m1['id']: 1, m2['id']: 1, m3['id']: 1},
    }
    with Store(ws / 'novel-dir', create=True, test_mode=True) as store:
        store.init_project('方向对接书')
        store.add_brief('雾夜渡口失踪案')
        adopt_story(store, baseline(), {})
        dir_job = start_job(store, JobRequest(
            'design', design_scope='book', budget=Budget(10, 50000, 2000),
            production_method_policy=policy, direction_review=True, planning_hierarchy=True,
        ))
        creation_in = _creation_input(Journal(store, dir_job.id))
        summaries = creation_in['production_methods']['method_summaries']
        assert {row['title'] for row in summaries} == {'渡口制度代价世界法', '受限视角具象节拍法', '章场阻力试错推进法'}
        assert all('evidence' not in row and 'quote' not in json.dumps(row, ensure_ascii=False) for row in summaries)

    # 2) Verify phase_flow._reference_method_portfolio feeds type_adaptation with single-source originality warning.
    portfolio = _reference_method_portfolio(
        ws,
        {'production_method_policy': policy},
        {'type_selection': {'products': {'selection': [{'id': 'GENRE_XUANYI', 'basis': '悬疑主线'}]}}},
    )
    assert portfolio is not None
    assert len(portfolio['planned_methods']) == 3
    assert portfolio['distinct_source_books'] == 1
    assert any('TYPE_F/OR' in w for w in portfolio['originality_warnings'])
    # Verify phase_flow output_contract adds _method_applications/_method_receipts for any method_plan (incl. manual).
    pf_src = (ROOT / 'src' / 'nw' / 'materials' / 'phase_flow.py').read_text(encoding='utf-8')
    assert "if method_plan is not None:\n                payload['output_contract']['products'].update(_method_applications=[], _method_receipts=[])" in pf_src

    # 3) Verify HTTP APIs: /api/kb/handoff-audit, /api/kb/method-recommendations?limit=12, /api/novels/{id}/methods
    prod = ProductionService(studio, lib, test_mode=True)
    created = prod.create({
        'title': '悬疑接收验证书', 'idea': '暴雨夜孤岛证人失踪', 'genre_ids': ['GENRE_XUANYI'],
        'design_mode': 'manual', 'direction_review': True, 'planning_hierarchy': True,
        'method_preferences': [{'slot': 'world', 'id': m1['id'], 'version': 1}],
    })
    novel_id = created['novel']['id']

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_ha, body_ha = get_json('/api/kb/handoff-audit?types=GENRE_XUANYI&planning_hierarchy=1')
        assert st_ha == 200 and body_ha['summary']['receivable_methods'] == 3 and body_ha['summary']['book_world_ready'] is True

        st_bk, body_bk = get_json(f"/api/kb/handoff-audit?book_id={book['id']}")
        assert st_bk == 200 and body_bk['book']['id'] == book['id']

        st_rec, body_rec = get_json('/api/kb/method-recommendations?slot=world&types=GENRE_XUANYI&limit=12')
        assert st_rec == 200 and body_rec['total_available'] == 1 and len(body_rec['recommendations']) == 1
        st_rec_bad, _ = get_json('/api/kb/method-recommendations?slot=world&types=GENRE_XUANYI&limit=99')
        assert st_rec_bad == 400

        st_nm, body_nm = get_json(f'/api/novels/{novel_id}/methods')
        assert st_nm == 200 and body_nm['handoff_audit']['summary']['book_world_ready'] is True
        assert any(m['id'] == m1['id'] and m['handoff_status'] == 'receivable' and 'world_design' in m['stages']
                   for m in body_nm['available_methods'])
    finally:
        server.shutdown()
        server.server_close()

    # 4) Verify frontend downstream handoff UI hooks across corpus, prerequisites, wizard, methods, studio, PlanArtifacts.
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert 'corpusHandoffCard' in (js_root / 'pages' / 'corpus.js').read_text(encoding='utf-8')
    assert 'handoffAuditType' in (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'wizardAutoReadiness' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'syncWizardTasksFromMethods' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'type_choice' in (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'methodGateCount' in (js_root / 'pages' / 'project-methods.js').read_text(encoding='utf-8')
    assert 'projectHandoffAudit' in (js_root / 'pages' / 'project-methods.js').read_text(encoding='utf-8')
    assert 'noticeProjectMethods' in (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'methodApplicationsSection' in (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')


def test_world_materials_taxonomy_covers_all_35_genres_with_strict_boundaries(tmp_path: Path) -> None:
    from nw.studio import catalog
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard
    from nw.studio.world_materials import (
        GENRE_WORLD_PROFILES,
        WORLD_CATEGORIES,
        WORLD_STEP_BOUNDARY,
        classify_world_method,
        world_profile_for_types,
    )

    main_genres = [g['id'] for g in catalog.genres()]
    assert len(main_genres) == 35
    assert set(main_genres) == set(GENRE_WORLD_PROFILES)
    assert len(WORLD_CATEGORIES) == 9
    assert WORLD_STEP_BOUNDARY['step_id'] == 'world_design'
    assert WORLD_STEP_BOUNDARY['out_of_scope']

    # Verify all 9 world groups and legacy + newly wired keys exist and every option has valid meaning.
    world_groups = catalog.options('world')
    assert len(world_groups) == 9
    world_map = catalog.option_map('world')
    for expected_key in (
        'world.31.1', 'world.32.5', 'world.33.1', 'world.39.1', 'world.10.1',
        'world.124.9', 'world.125.1', 'world.20.1', 'world.25.1', 'world.28.2',
        'world.115.6', 'world.PLOT_MECHANISM_SYSTEM',
    ):
        assert expected_key in world_map, f'missing expected world key: {expected_key}'
    for key, opt in world_map.items():
        if opt.get('selectable', True):
            assert opt.get('definition') or opt.get('description') or opt.get('source_excerpt'), key

    # Genre differentiation: Xianxia activates power_energy; Xuanyi/Xianshi guard power_energy & race_construct.
    xianxia = world_profile_for_types(['GENRE_XIANXIA'])
    assert 'power_energy' in xianxia['primary_categories']
    assert 'resource_market' in xianxia['primary_categories']
    assert '灵石' in xianxia['resource_profile']['preferred_resources']

    xuanyi = world_profile_for_types(['GENRE_XUANYI'])
    assert 'institution' in xuanyi['primary_categories']
    assert 'items_props' in xuanyi['primary_categories']
    assert 'power_energy' in xuanyi['out_of_scope_categories']
    assert 'race_construct' in xuanyi['out_of_scope_categories']

    # Subgenre inherits parent profile; multi-genre crossover merges via max relevance.
    sub_profile = world_profile_for_types(['SUB_XUANHUAN_01'])
    assert 'power_energy' in sub_profile['primary_categories']
    crossover = world_profile_for_types(['GENRE_XUANYI', 'GENRE_LINGYI'])
    assert 'power_energy' in crossover['primary_categories']
    assert 'institution' in crossover['primary_categories']

    # Newly added world options freeze cleanly through freeze_wizard without breaking creation_plan.
    lib = LibraryService(tmp_path / 'ws')
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '边界验证', 'idea': '封闭档案馆失窃案',
        'design_mode': 'manual', 'world_ids': ['124.9', '28.2', '115.6', 'PLOT_MECHANISM_PARALLEL'],
    }, lib)
    assert set(wizard['world_ids']) == {'124.9', '28.2', '115.6', 'PLOT_MECHANISM_PARALLEL'}
    assert len(wizard['creation_plan']['preferences']) == 4

    # Method classification maps world methods to matching sub-categories.
    assert 'institution' in classify_world_method({
        'tasks': ['world_rules'], 'outputs': [{'stage': 'world_design', 'field': 'members'}],
        'title': '宗门执法与禁令约束', 'operations': [{'instruction': '确立律法执行机构与违规代价'}],
    })
    assert 'power_energy' in classify_world_method({
        'tasks': ['world_rules'], 'outputs': [{'stage': 'world_design', 'field': 'members'}],
        'title': '灵气潮汐与境界突破反噬', 'operations': [{'instruction': '按能量总量与突破代价限制角色'}],
    })


def test_world_design_upstream_decomposition_and_planning_replay_determinism(tmp_path: Path) -> None:
    from nw.config import Config
    from nw.planning import prepare_plan_task
    from nw.materials.stage_input import model_package
    from nw.store import Store
    from nw.studio.corpus_prompts import messages as corpus_messages, method_messages
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance
    from nw.task_models import Budget
    from nw.call_budget import create_budget

    # 1) Decomposition prompts inject genre-targeted world boundaries without craft=False leakage.
    rel_msgs = corpus_messages(
        'relations',
        {'domain': 'world_rules', 'events': [], 'evidence': [], 'prefix': 'R_0_00000'},
        version=5, passages=True, craft=False, confirmed_types=['GENRE_XUANYI'],
    )
    sys_rel = rel_msgs[0]['content']
    assert '03世界设计·按本书类型（悬疑）' in sys_rel
    assert '力量与能量' in sys_rel
    assert 'sensory_evidence' not in sys_rel and 'reader_address' not in sys_rel

    m_msgs = method_messages({
        'thread': {'id': 't1', 'domain': 'world_rules', 'details': {}},
        'events': [], 'links': [], 'evidence': [], 'confirmed_types': ['GENRE_XIANXIA'],
    }, version=5)
    assert '03世界设计·分类型资料边界（仙侠）' in m_msgs[0]['content']
    user_m = json.loads(m_msgs[1]['content'])
    assert len(user_m['target_step_blueprint']['world_categories']) == 9
    assert user_m['target_step_blueprint']['step_boundary']['out_of_scope']

    # 2) planning.prepare_plan_task freezes world_material_profile and replays deterministically.
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    brief_text = '暴雨夜孤岛档案馆停电，值班员必须在断联 12 小时内查明封条被换的真相。'
    studio.create_project('replay_world', '世界边界回放验证', brief_text=brief_text, constraints='现实悬疑无超自然')
    store = Store(ws / 'replay_world')
    brief = store.briefs()[-1]
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '封条', 'idea': brief.text, 'constraints': brief.constraints,
        'design_mode': 'manual', 'planning_hierarchy': True,
    }, lib)
    gov = governance(wizard, library=lib)
    budget_id = create_budget(store, 'plan:world-replay', Budget(max_calls=12, context_char_limit=120000, output_limit=4000))
    cfg = Config('ollama', 'http://localhost', '[FAKE] test', '', 30, {}, ws)

    class _DummyProvider:
        name = 'ollama'

    _, pkg1 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'world-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert 'world_material_profile' in pkg1
    assert 'power_energy' in [c['id'] for c in pkg1['world_material_profile']['out_of_scope_categories']]
    assert 'world_material_profile' not in model_package(pkg1)
    # Replaying the same manifest id must preserve the exact frozen world_material_profile without hash mismatch.
    _, pkg2 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'world-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert pkg2['world_material_profile'] == pkg1['world_material_profile']


def test_world_blueprint_options_http_and_client_workflow_step_order(tmp_path: Path, monkeypatch) -> None:
    import http.client
    import re
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio import catalog
    from nw.studio.api import StudioService
    from nw.studio.library import LibraryService
    from nw.studio.server import create_studio_server

    # 1) Verify backend SLOTS and frontend WizardStep.js STEPS follow the real novel workflow order.
    expected_slots = ('genre', 'world', 'character', 'structure', 'hook', 'narration', 'tone', 'style')
    assert catalog.SLOTS == expected_slots

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    wizard_step_js = (js_root / 'components' / 'WizardStep.js').read_text(encoding='utf-8')
    parsed_slots = re.findall(r"slot\s*:\s*'([a-z]+)'", wizard_step_js)
    assert tuple(parsed_slots) == (*expected_slots, 'confirm')
    assert 'outOfScopeOptions' in wizard_step_js

    wizard_js = (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'step === 6' not in wizard_js and 'step === 8' not in wizard_js
    assert 'wizardWorldGuide' in wizard_js
    assert '/kb/world-blueprint' in wizard_js
    assert 'worldStageHandoffBanner' in (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    assert 'worldBlueprintCategories' in (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'atlasWorldProfile' in (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')

    # 2) Verify live HTTP /api/options?slot=world&types=... and /api/kb/world-blueprint?types=...
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'title': '档案馆夜班', 'filename': 'archive.txt', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    world_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'world_rules')
    eids = list(dict.fromkeys([
        *world_thread['evidence_ids'],
        *(eid for ev in structure['body']['events'] if ev['id'] in world_thread['node_ids'] for eid in ev['evidence_ids']),
    ]))
    saved_m = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [world_thread['id']]},
        'body': {
            'title': '权限警报制度约束调查路径',
            'tasks': ['world_rules'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'prerequisites': [{'key': 'p1', 'input_kind': 'type_adaptation', 'artifact': '类型适配', 'requirement': '存在封闭机构与权限约束'}],
            'operations': [{'key': 'op1', 'instruction': '在世界卡写明权限核验制度、违规警报代价与合法旁路条件', 'input_keys': ['p1'], 'output_keys': ['out1']}],
            'outputs': [{'key': 'out1', 'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world', 'description': '权限与警报制度世界卡'}],
            'downstream': [{'output_key': 'out1', 'consumer': 'plot_design', 'usage': '据此设计受限后的调查行动'}],
            'acceptance': [{'output_key': 'out1', 'check': '世界卡含规则与违规代价', 'evidence_required': '世界卡正文'}],
            'evidence': [
                {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
                 'quote': ev_by_id[eid]['quote'], 'explanation': '原文制度约束'}
                for eid in eids
            ],
            'applicability': ['悬疑调查存在机构权限边界'], 'non_applicability': ['无制度约束的纯粹动作逃生'],
        },
    })
    lib.review_method(saved_m['id'], {'version': 1, 'decision': 'approve', 'note': '批准悬疑制度世界方法'})

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_xy, body_xy = get_json('/api/options?slot=world&types=GENRE_XUANYI')
        assert st_xy == 200 and len(body_xy['options']) == 9
        assert body_xy['options'][0]['relevance'] == 'primary'
        assert body_xy['options'][-1]['relevance'] == 'out_of_scope'
        by_cat_xy = {g['world_category']: g for g in body_xy['options']}
        assert by_cat_xy['institution']['relevance'] == 'primary'
        assert by_cat_xy['power_energy']['relevance'] == 'out_of_scope'
        assert body_xy['world_profile']['has_genre_binding'] is True

        st_xx, body_xx = get_json('/api/options?slot=world&types=GENRE_XIANXIA')
        assert st_xx == 200
        by_cat_xx = {g['world_category']: g for g in body_xx['options']}
        assert by_cat_xx['power_energy']['relevance'] == 'primary'

        st_wb, body_wb = get_json('/api/kb/world-blueprint?types=GENRE_XUANYI')
        assert st_wb == 200
        assert body_wb['coverage_summary']['book_world_ready'] is True
        assert body_wb['coverage_summary']['receivable_world_methods'] == 1
        inst_cat = next(c for c in body_wb['categories'] if c['id'] == 'institution')
        assert inst_cat['receivable_count'] == 1

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200
        wd_step = next(s for s in body_bp['steps'] if s['step_id'] == 'world_design')
        assert len(wd_step['world_categories']) == 9 and wd_step['step_boundary']['step_id'] == 'world_design'
    finally:
        server.shutdown()
        server.server_close()


def test_character_and_static_relations_taxonomy_and_strict_stage_routing(tmp_path: Path) -> None:
    from nw.materials.author_references import author_stage_input
    from nw.studio import catalog
    from nw.studio.character_materials import (
        CHARACTER_CATEGORIES,
        CHARACTER_STEP_BOUNDARY,
        GENRE_CHARACTER_PROFILES,
        STATIC_RELATIONS_STEP_BOUNDARY,
        character_profile_for_types,
        classify_character_method,
    )
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance

    main_genres = [g['id'] for g in catalog.genres()]
    assert len(main_genres) == 35
    assert set(main_genres) == set(GENRE_CHARACTER_PROFILES)
    assert len(CHARACTER_CATEGORIES) == 10
    assert CHARACTER_STEP_BOUNDARY['step_id'] == 'character_design'
    assert STATIC_RELATIONS_STEP_BOUNDARY['step_id'] == 'static_relations'

    char_groups = catalog.options('character')
    assert len(char_groups) == 10
    char_map = catalog.option_map('character')
    for expected_key in (
        'character.1.1', 'character.3.2', 'character.8.1', 'character.39.2',
        'character.121.1', 'character.123.20', 'character.block.144', 'character.block.146', 'character.block.151',
        'character.block.68.确认偏误', 'character.block.74.是非', 'character.block.81.抗争',
        'character.PLOT_MECHANISM_TEAM', 'character.PLOT_MECHANISM_BLOODLINE',
        'character.rel.1.7', 'character.rel.5.6', 'character.rel.117.4', 'character.rel.115.7',
        'character.rel.block.86.合作', 'character.rel.block.153', 'character.rel.36.4',
    ):
        assert expected_key in char_map, f'missing expected character/relation key: {expected_key}'
    for key, opt in char_map.items():
        if opt.get('selectable', True):
            assert opt.get('definition') or opt.get('description') or opt.get('source_excerpt'), key

    # Genre boundaries: Xuanyi guards supernatural_ability & racial_relation; Xuanhuan activates both.
    xuanyi = character_profile_for_types(['GENRE_XUANYI'])
    assert 'cognition_ethics' in xuanyi['primary_categories']
    assert 'relation_tension' in xuanyi['primary_categories']
    assert 'supernatural_ability' in xuanyi['out_of_scope_categories']
    assert 'racial_relation' in xuanyi['out_of_scope_categories']

    xuanhuan = character_profile_for_types(['GENRE_XUANHUAN'])
    assert 'supernatural_ability' in xuanhuan['primary_categories']
    assert 'racial_relation' in xuanhuan['primary_categories']

    crossover = character_profile_for_types(['GENRE_XUANYI', 'GENRE_XUANHUAN'])
    assert 'supernatural_ability' in crossover['primary_categories']
    assert 'cognition_ethics' in crossover['primary_categories']

    # Strict 04 vs 05 routing: character preferences only go to character_design, relation preferences only to static_relations.
    lib = LibraryService(tmp_path / 'ws')
    only_char = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '纯人物偏好', 'idea': '值夜员排查封条',
        'design_mode': 'manual', 'character_ids': ['1.1'],
    }, lib)
    gov_only_char = governance(only_char)
    assert 'character_design' in gov_only_char and 'static_relations' not in gov_only_char

    mixed = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '双步路由验证', 'idea': '孤岛档案馆封条失窃',
        'design_mode': 'manual',
        'character_ids': ['1.1', 'block.68.确认偏误', 'rel.5.6', 'rel.117.4', 'rel.block.153'],
    }, lib)
    gov_mixed = governance(mixed)
    pkg = {'governance_inputs': gov_mixed}
    c_in = author_stage_input(pkg, 'character_design')
    r_in = author_stage_input(pkg, 'static_relations')
    assert set(gov_mixed['character_design']['author_preferences']['character']) == {'1.1', 'block.68.确认偏误'}
    assert {p['id'] for p in c_in['creation_plan']['preferences']} == {'1.1', 'block.68.确认偏误'}
    assert set(gov_mixed['static_relations']['author_preferences']['character']) == {'rel.5.6', 'rel.117.4', 'rel.block.153'}
    assert {p['id'] for p in r_in['creation_plan']['preferences']} == {'rel.5.6', 'rel.117.4', 'rel.block.153'}

    assert 'cognition_ethics' in classify_character_method({
        'tasks': ['character_arc'], 'outputs': [{'stage': 'character_design', 'field': 'members'}],
        'title': '确认偏误与道德底线崩塌', 'operations': [{'instruction': '确立心智模型盲点与道德抉择'}],
    })
    assert 'relation_tension' in classify_character_method({
        'tasks': ['relationships'], 'outputs': [{'stage': 'static_relations', 'field': 'relations'}],
        'title': '信息不对称与情感错位对立', 'operations': [{'instruction': '建立权力差、情感债务与信任怀疑光谱'}],
    })


def test_character_relations_decomposition_prompts_and_planning_replay(tmp_path: Path) -> None:
    from nw.call_budget import create_budget
    from nw.config import Config
    from nw.materials.stage_input import model_package
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.studio.corpus_prompts import messages as corpus_messages, method_messages
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance
    from nw.task_models import Budget

    for dom in ('character_arc', 'cast_entry', 'cast_roster'):
        msgs = corpus_messages(
            'relations',
            {'domain': dom, 'events': [], 'evidence': [], 'prefix': 'R_0_00000'},
            version=5, passages=True, craft=False, confirmed_types=['GENRE_XUANYI'],
        )
        sys_txt = msgs[0]['content']
        assert f'04人物与05静态关系·按本书类型（悬疑）定向核对{dom}' in sys_txt
        assert 'sensory_evidence' not in sys_txt and 'reader_address' not in sys_txt

    m_msgs = method_messages({
        'thread': {'id': 't_char', 'domain': 'character_arc', 'details': {}},
        'events': [], 'links': [], 'evidence': [], 'confirmed_types': ['GENRE_XUANYI'],
    }, version=5)
    assert '04人物与05静态关系·分类型资料边界（悬疑）' in m_msgs[0]['content']
    user_m = json.loads(m_msgs[1]['content'])
    assert len(user_m['target_step_blueprint']['character_categories']) == 10
    assert set(user_m['target_step_blueprint']['step_boundaries']) == {'character_design', 'static_relations'}

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    studio.create_project('replay_char', '人物关系回放验证', brief_text='暴雨夜值夜员排查调包档案。', constraints='现实悬疑无超自然')
    store = Store(ws / 'replay_char')
    brief = store.briefs()[-1]
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '档案夜班', 'idea': brief.text, 'constraints': brief.constraints,
        'design_mode': 'manual', 'planning_hierarchy': True,
    }, lib)
    gov = governance(wizard, library=lib)
    budget_id = create_budget(store, 'plan:char-replay', Budget(max_calls=12, context_char_limit=120000, output_limit=4000))
    cfg = Config('ollama', 'http://localhost', '[FAKE] test', '', 30, {}, ws)

    class _DummyProvider:
        name = 'ollama'

    _, pkg1 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'char-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert 'character_material_profile' in pkg1
    assert 'supernatural_ability' in [c['id'] for c in pkg1['character_material_profile']['character_design']['out_of_scope_categories']]
    assert 'racial_relation' in [c['id'] for c in pkg1['character_material_profile']['static_relations']['out_of_scope_categories']]
    assert 'character_material_profile' not in model_package(pkg1)
    _, pkg2 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'char-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert pkg2['character_material_profile'] == pkg1['character_material_profile']


def test_character_blueprint_options_http_and_frontend_04_05_hooks(tmp_path: Path, monkeypatch) -> None:
    import http.client
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.api import StudioService
    from nw.studio.library import LibraryService
    from nw.studio.server import create_studio_server

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert 'target_stage_label' in (js_root / 'components' / 'WizardStep.js').read_text(encoding='utf-8')
    wizard_js = (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'wizardCharacterGuide' in wizard_js and '/kb/character-blueprint' in wizard_js
    plan_js = (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    assert 'characterStageHandoffBanner' in plan_js and 'staticRelationsStageHandoffBanner' in plan_js
    prereq_js = (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'characterBlueprintCategories' in prereq_js and 'staticRelationsBlueprintCategories' in prereq_js
    assert 'atlasCharacterProfile' in (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'title': '夜班嫌疑人', 'filename': 'suspect.txt', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    arc_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'character_arc')
    ev_ids = list(dict.fromkeys(arc_thread['evidence_ids']))[:2]
    ev_rows = [
        {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
         'quote': ev_by_id[eid]['quote'], 'explanation': '人物与关系原文依据'}
        for eid in ev_ids
    ]

    m_char = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [arc_thread['id']]},
        'body': {
            'title': '确认偏误与压力下信念动摇建卡法',
            'tasks': ['character_arc'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'prerequisites': [{'key': 'p1', 'input_kind': 'world_design', 'artifact': '世界规则', 'requirement': '已确立外部约束'}],
            'operations': [{'key': 'op1', 'instruction': '确立人物心智模型盲点、确认偏误与压力下的道德抉择底线', 'input_keys': ['p1'], 'output_keys': ['out1']}],
            'outputs': [{'key': 'out1', 'stage': 'character_design', 'field': 'members', 'artifact_kind': 'character', 'description': '含认知偏误与信念弧光的人物卡'}],
            'downstream': [{'output_key': 'out1', 'consumer': 'plot_design', 'usage': '按盲点设计误判冲突'}],
            'acceptance': [{'output_key': 'out1', 'check': '人物卡明确盲点与变化条件', 'evidence_required': '人物卡正文'}],
            'evidence': ev_rows,
            'applicability': ['悬疑推理中角色易因先入为主误判'], 'non_applicability': ['无心理博弈的纯打怪段落'],
        },
    })
    lib.review_method(m_char['id'], {'version': 1, 'decision': 'approve', 'note': '批准04人物方法'})

    m_rel = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [arc_thread['id']]},
        'body': {
            'title': '信息不对称与信任怀疑光谱对立构造法',
            'tasks': ['relationships'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'prerequisites': [{'key': 'p1', 'input_kind': 'character_design', 'artifact': '人物卡', 'requirement': '已确立双方人物'}],
            'operations': [{'key': 'op1', 'instruction': '标明双方的信息不对称、权力差、情感债务与信任怀疑光谱', 'input_keys': ['p1'], 'output_keys': ['out1']}],
            'outputs': [{'key': 'out1', 'stage': 'static_relations', 'field': 'relations', 'artifact_kind': 'stage_product', 'description': '含不对称张力的静态关系'}],
            'downstream': [{'output_key': 'out1', 'consumer': 'plot_design', 'usage': '据信息差推进试探与反转'}],
            'acceptance': [{'output_key': 'out1', 'check': '关系条含成立条件与不对称依据', 'evidence_required': '关系条目'}],
            'evidence': ev_rows,
            'applicability': ['悬疑双人/多人猜忌关系网'], 'non_applicability': ['无信息差的透明合作关系'],
        },
    })
    lib.review_method(m_rel['id'], {'version': 1, 'decision': 'approve', 'note': '批准05关系方法'})

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_xy, body_xy = get_json('/api/options?slot=character&types=GENRE_XUANYI')
        assert st_xy == 200 and len(body_xy['options']) == 10
        assert body_xy['options'][0]['relevance'] == 'primary'
        assert body_xy['options'][-1]['relevance'] == 'out_of_scope'
        by_cat_xy = {g['character_category']: g for g in body_xy['options']}
        assert by_cat_xy['cognition_ethics']['target_stage'] == 'character_design'
        assert by_cat_xy['relation_tension']['target_stage'] == 'static_relations'
        assert by_cat_xy['supernatural_ability']['relevance'] == 'out_of_scope'
        assert by_cat_xy['racial_relation']['relevance'] == 'out_of_scope'
        assert body_xy['character_profile']['has_genre_binding'] is True

        st_xh, body_xh = get_json('/api/options?slot=character&types=GENRE_XUANHUAN')
        assert st_xh == 200
        by_cat_xh = {g['character_category']: g for g in body_xh['options']}
        assert by_cat_xh['supernatural_ability']['relevance'] == 'primary'
        assert by_cat_xh['racial_relation']['relevance'] == 'primary'

        st_cb, body_cb = get_json('/api/kb/character-blueprint?types=GENRE_XUANYI')
        assert st_cb == 200
        assert body_cb['coverage_summary']['receivable_character_methods'] == 1
        assert body_cb['coverage_summary']['receivable_relation_methods'] == 1
        cog_cat = next(c for c in body_cb['categories'] if c['id'] == 'cognition_ethics')
        ten_cat = next(c for c in body_cb['categories'] if c['id'] == 'relation_tension')
        assert cog_cat['receivable_count'] == 1 and ten_cat['receivable_count'] == 1

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200
        ch_step = next(s for s in body_bp['steps'] if s['step_id'] == 'character_design')
        sr_step = next(s for s in body_bp['steps'] if s['step_id'] == 'static_relations')
        assert len(ch_step['character_categories']) == 6 and ch_step['step_boundary']['step_id'] == 'character_design'
        assert len(sr_step['relation_categories']) == 4 and sr_step['step_boundary']['step_id'] == 'static_relations'
    finally:
        server.shutdown()
        server.server_close()


def test_plot_and_event_taxonomy_item_level_ranking_and_strict_stage_routing(tmp_path: Path) -> None:
    from nw.materials.author_references import author_stage_input
    from nw.studio import catalog
    from nw.studio.library import LibraryService
    from nw.studio.plot_materials import (
        EVENT_STEP_BOUNDARY,
        GENRE_PLOT_PROFILES,
        PLOT_EVENT_CATEGORIES,
        PLOT_STEP_BOUNDARY,
        classify_plot_event_method,
        plot_profile_for_types,
    )
    from nw.studio.production_inputs import freeze_wizard, governance

    main_genres = [g['id'] for g in catalog.genres()]
    assert len(main_genres) == 35
    assert set(main_genres) == set(GENRE_PLOT_PROFILES)
    assert len(PLOT_EVENT_CATEGORIES) == 12
    assert PLOT_STEP_BOUNDARY['step_id'] == 'plot_design'
    assert EVENT_STEP_BOUNDARY['step_id'] == 'event_design'

    assert len(catalog.options('structure')) == 6
    assert len(catalog.options('hook')) == 6
    s_map = catalog.option_map('structure')
    h_map = catalog.option_map('hook')
    for k in ('structure.NARRATIVE_STRUCTURE_LINEAR', 'structure.41.1', 'structure.112.4',
              'structure.block.48.起承转合', 'structure.block.61.重章（快节奏）',
              'structure.120.8', 'structure.121.4', 'structure.125.17'):
        assert k in s_map, f'missing structure key: {k}'
    for k in ('hook.PLOT_MECHANISM_UPGRADE', 'hook.123.4', 'hook.block.45.伏笔埋设',
              'hook.116.2', 'hook.117.7', 'hook.111.1', 'hook.ev.104.1',
              'hook.ev.block.73.决策连锁反应', 'hook.PLOT_MECHANISM_DUNGEON'):
        assert k in h_map, f'missing hook key: {k}'
    for mapping in (s_map, h_map):
        for key, opt in mapping.items():
            if opt.get('selectable', True):
                assert opt.get('definition') or opt.get('description') or opt.get('source_excerpt'), key

    # Item-level ranking inside hook.group.types and event_crisis_mechanisms genre guard.
    xuanyi_hook = catalog.options('hook', types=['GENRE_XUANYI'])
    by_cat_xy = {g['plot_category']: g for g in xuanyi_hook}
    assert by_cat_xy['event_crisis_mechanisms']['relevance'] == 'out_of_scope'
    mechs_xy = by_cat_xy['plot_mechanism']['children']
    assert mechs_xy[0]['relevance'] == 'primary'
    mech_rel_xy = {m['id']: m['relevance'] for m in mechs_xy}
    assert mech_rel_xy['PLOT_MECHANISM_MYSTERY'] == 'primary'
    assert mech_rel_xy['PLOT_MECHANISM_INVESTIGATION'] == 'primary'
    assert mech_rel_xy['PLOT_MECHANISM_STAR'] == 'out_of_scope'

    kehuan_profile = plot_profile_for_types(['GENRE_KEHUAN'])
    assert 'event_crisis_mechanisms' in kehuan_profile['primary_categories']
    assert 'PLOT_MECHANISM_SPACE' in kehuan_profile['preferred_mechanisms']

    # Strict 06 vs 07 routing in freeze_wizard + governance.
    lib = LibraryService(tmp_path / 'ws')
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '悬案结构验证', 'idea': '暴雨夜孤岛失窃案',
        'design_mode': 'manual',
        'structure_ids': ['NARRATIVE_STRUCTURE_LINEAR', '112.4'],
        'mechanism_ids': ['PLOT_MECHANISM_MYSTERY', 'block.45.伏笔埋设', 'ev.104.1', 'PLOT_MECHANISM_DUNGEON'],
    }, lib)
    gov = governance(wizard)
    pkg = {'governance_inputs': gov}
    assert set(gov['plot_design']['author_preferences']['structure']) == {'NARRATIVE_STRUCTURE_LINEAR', '112.4'}
    assert set(gov['scene_design']['author_preferences']['structure']) == {'NARRATIVE_STRUCTURE_LINEAR'}
    assert set(gov['plot_design']['author_preferences']['hook']) == {'PLOT_MECHANISM_MYSTERY', 'block.45.伏笔埋设'}
    assert set(gov['event_design']['author_preferences']['hook']) == {'PLOT_MECHANISM_MYSTERY', 'ev.104.1', 'PLOT_MECHANISM_DUNGEON'}
    p_prefs = {p['id'] for p in author_stage_input(pkg, 'plot_design')['creation_plan']['preferences']}
    e_prefs = {p['id'] for p in author_stage_input(pkg, 'event_design')['creation_plan']['preferences']}
    assert p_prefs == {'NARRATIVE_STRUCTURE_LINEAR', '112.4', 'PLOT_MECHANISM_MYSTERY', 'block.45.伏笔埋设'}
    assert e_prefs == {'PLOT_MECHANISM_MYSTERY', 'ev.104.1', 'PLOT_MECHANISM_DUNGEON'}

    assert 'foreshadow_twist' in classify_plot_event_method({
        'tasks': ['foreshadow'], 'outputs': [{'stage': 'plot_design', 'field': 'promise_plan'}],
        'title': '深层掩体伏笔延迟解码与反转联动', 'operations': [{'instruction': '埋设伏笔并设置回收窗口'}],
    })
    assert 'event_chain_triggers' in classify_plot_event_method({
        'tasks': ['event_chain'], 'outputs': [{'stage': 'event_design', 'field': 'candidates'}],
        'title': '前驱完成门与决策连锁后继事件法', 'operations': [{'instruction': '引用前驱事件完成条件生成候选事件'}],
    })


def test_plot_event_decomposition_prompts_and_planning_replay_determinism(tmp_path: Path) -> None:
    from nw.call_budget import create_budget
    from nw.config import Config
    from nw.materials.stage_input import model_package
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.studio.corpus_prompts import messages as corpus_messages, method_messages
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance
    from nw.task_models import Budget

    for dom in ('main_plot', 'subplot', 'hook', 'foreshadow', 'information', 'chapter_progress'):
        msgs = corpus_messages(
            'relations',
            {'domain': dom, 'events': [], 'evidence': [], 'prefix': 'R_0_00000'},
            version=5, passages=True, craft=False, confirmed_types=['GENRE_XUANYI'],
        )
        sys_txt = msgs[0]['content']
        assert f'06剧情与07事件·按本书类型（悬疑）定向核对{dom}' in sys_txt
        assert 'sensory_evidence' not in sys_txt and 'reader_address' not in sys_txt

    m_msgs = method_messages({
        'thread': {'id': 't_fs', 'domain': 'foreshadow', 'details': {}},
        'events': [], 'links': [], 'evidence': [], 'confirmed_types': ['GENRE_XUANYI'],
    }, version=5)
    assert '06剧情与07事件·分类型资料边界（悬疑）' in m_msgs[0]['content']
    user_m = json.loads(m_msgs[1]['content'])
    assert len(user_m['target_step_blueprint']['plot_event_categories']) == 12
    assert set(user_m['target_step_blueprint']['step_boundaries']) == {'plot_design', 'event_design'}

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    studio.create_project('replay_plot', '剧情事件回放验证', brief_text='暴雨夜值夜员追查失窃档案。', constraints='现实悬疑无超自然')
    store = Store(ws / 'replay_plot')
    brief = store.briefs()[-1]
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '档案悬案', 'idea': brief.text, 'constraints': brief.constraints,
        'design_mode': 'manual', 'planning_hierarchy': True,
    }, lib)
    gov = governance(wizard, library=lib)
    budget_id = create_budget(store, 'plan:plot-replay', Budget(max_calls=12, context_char_limit=120000, output_limit=4000))
    cfg = Config('ollama', 'http://localhost', '[FAKE] test', '', 30, {}, ws)

    class _DummyProvider:
        name = 'ollama'

    _, pkg1 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'plot-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert 'plot_material_profile' in pkg1
    assert 'event_crisis_mechanisms' in [c['id'] for c in pkg1['plot_material_profile']['event_design']['out_of_scope_categories']]
    assert 'PLOT_MECHANISM_MYSTERY' in pkg1['plot_material_profile']['plot_design']['preferred_mechanisms']
    assert 'plot_material_profile' not in model_package(pkg1)
    _, pkg2 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'plot-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert pkg2['plot_material_profile'] == pkg1['plot_material_profile']


def test_plot_blueprint_options_http_and_frontend_06_07_hooks(tmp_path: Path, monkeypatch) -> None:
    import http.client
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.api import StudioService
    from nw.studio.library import LibraryService
    from nw.studio.server import create_studio_server

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    wizard_js = (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    assert 'wizardStructureGuide' in wizard_js and 'wizardHookGuide' in wizard_js
    assert 'drawerOutOfScopeOptions' in wizard_js and '/kb/plot-blueprint' in wizard_js
    plan_js = (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    assert 'plotStageHandoffBanner' in plan_js and 'eventStageHandoffBanner' in plan_js
    prereq_js = (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    assert 'plotBlueprintCategories' in prereq_js and 'eventBlueprintCategories' in prereq_js
    assert 'atlasPlotProfile' in (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'title': '夜班悬案', 'filename': 'case.txt', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    plot_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'main_plot')
    prog_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'chapter_progress')

    def ev_rows(thread: dict) -> list[dict]:
        eids = list(dict.fromkeys(thread['evidence_ids']))[:2]
        return [
            {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
             'quote': ev_by_id[eid]['quote'], 'explanation': '剧情与事件原文依据'}
            for eid in eids
        ]

    m_plot = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [plot_thread['id']]},
        'body': {
            'title': '深层掩体伏笔埋设与延迟回收窗口法',
            'tasks': ['foreshadow'], 'scopes': ['book'], 'type_tags': ['GENRE_XUANYI'],
            'prerequisites': [{'key': 'p1', 'input_kind': 'character_design', 'artifact': '人物卡', 'requirement': '已确立核心角色'}],
            'operations': [{'key': 'op1', 'instruction': '将核心伏笔藏在日常物件细节并登记2-10章回收窗口与反转前奏', 'input_keys': ['p1'], 'output_keys': ['out1']}],
            'outputs': [{'key': 'out1', 'stage': 'plot_design', 'field': 'promise_plan', 'artifact_kind': 'stage_product', 'description': '含埋设掩体与回收窗口的伏笔计划'}],
            'downstream': [{'output_key': 'out1', 'consumer': 'scene_design', 'usage': '按窗口在场景释放线索与兑现'}],
            'acceptance': [{'output_key': 'out1', 'check': '伏笔含埋设与回收窗口', 'evidence_required': '伏笔计划'}],
            'evidence': ev_rows(plot_thread),
            'applicability': ['悬疑主线需要多层伏笔反转'], 'non_applicability': ['无悬念直叙流水账'],
        },
    })
    lib.review_method(m_plot['id'], {'version': 1, 'decision': 'approve', 'note': '批准06伏笔方法'})

    m_event = lib.save_method({
        'expected_version': 0,
        'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [prog_thread['id']]},
        'body': {
            'title': '前驱完成门触发决策连锁后继事件法',
            'tasks': ['event_chain'], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI'],
            'prerequisites': [{'key': 'p1', 'input_kind': 'plot_design', 'artifact': '事件节点', 'requirement': '已确立前驱事件与完成条件'}],
            'operations': [{'key': 'op1', 'instruction': '原样沿用前事件完成条件作为完成门，派生多方连锁反应条件候选事件', 'input_keys': ['p1'], 'output_keys': ['out1']}],
            'outputs': [{'key': 'out1', 'stage': 'event_design', 'field': 'candidates', 'artifact_kind': 'stage_product', 'description': '含前驱完成门的条件候选事件'}],
            'downstream': [{'output_key': 'out1', 'consumer': 'action_design', 'usage': '据此设计应对行动与代价'}],
            'acceptance': [{'output_key': 'out1', 'check': '候选事件保留前驱完成门且状态为条件候选', 'evidence_required': '候选事件正文'}],
            'evidence': ev_rows(prog_thread),
            'applicability': ['章场细化需要严密因果事件链'], 'non_applicability': ['跳过前因直接跳结果的章节'],
        },
    })
    lib.review_method(m_event['id'], {'version': 1, 'decision': 'approve', 'note': '批准07事件方法'})

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_st, body_st = get_json('/api/options?slot=structure&types=GENRE_XUANYI')
        assert st_st == 200 and len(body_st['options']) == 6 and body_st['plot_profile']['has_genre_binding'] is True
        st_types = next(g for g in body_st['options'] if g['plot_category'] == 'narrative_structure')['children']
        assert st_types[0]['relevance'] == 'primary'

        st_hk, body_hk = get_json('/api/options?slot=hook&types=GENRE_XUANYI')
        assert st_hk == 200 and len(body_hk['options']) == 6
        hk_by_cat = {g['plot_category']: g for g in body_hk['options']}
        assert hk_by_cat['event_crisis_mechanisms']['relevance'] == 'out_of_scope'
        assert hk_by_cat['plot_mechanism']['children'][0]['relevance'] == 'primary'

        st_ms, body_ms = get_json('/api/options?slot=hook&types=GENRE_MOSHI')
        assert st_ms == 200
        ms_by_cat = {g['plot_category']: g for g in body_ms['options']}
        assert ms_by_cat['event_crisis_mechanisms']['relevance'] == 'primary'

        st_pb, body_pb = get_json('/api/kb/plot-blueprint?types=GENRE_XUANYI')
        assert st_pb == 200
        assert body_pb['coverage_summary']['receivable_plot_methods'] == 1
        assert body_pb['coverage_summary']['receivable_event_methods'] == 1
        fs_cat = next(c for c in body_pb['categories'] if c['id'] == 'foreshadow_twist')
        ev_cat = next(c for c in body_pb['categories'] if c['id'] == 'event_chain_triggers')
        assert fs_cat['receivable_count'] == 1 and ev_cat['receivable_count'] == 1

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200
        pl_step = next(s for s in body_bp['steps'] if s['step_id'] == 'plot_design')
        ev_step = next(s for s in body_bp['steps'] if s['step_id'] == 'event_design')
        assert len(pl_step['plot_categories']) == 10 and pl_step['step_boundary']['step_id'] == 'plot_design'
        assert len(ev_step['event_categories']) == 2 and ev_step['step_boundary']['step_id'] == 'event_design'
    finally:
        server.shutdown()
        server.server_close()


def test_execution_08_11_taxonomy_covers_all_35_genres_and_boundaries() -> None:
    from nw.studio import catalog
    from nw.studio.execution_materials import (
        ACTION_STEP_BOUNDARY,
        EXECUTION_CATEGORIES,
        GENRE_EXECUTION_PROFILES,
        SCENE_STEP_BOUNDARY,
        STATE_PROPAGATION_STEP_BOUNDARY,
        STATE_TRANSITION_STEP_BOUNDARY,
        classify_execution_method,
        execution_profile_for_types,
    )

    main_genres = [g['id'] for g in catalog.genres()]
    assert len(main_genres) == 35
    assert set(main_genres) == set(GENRE_EXECUTION_PROFILES)
    assert len(EXECUTION_CATEGORIES) == 12
    assert sum(1 for c in EXECUTION_CATEGORIES if c['target_stage'] == 'action_design') == 4
    assert sum(1 for c in EXECUTION_CATEGORIES if c['target_stage'] == 'scene_design') == 3
    assert sum(1 for c in EXECUTION_CATEGORIES if c['target_stage'] == 'state_transition') == 3
    assert sum(1 for c in EXECUTION_CATEGORIES if c['target_stage'] == 'state_propagation') == 2
    for bnd, sid in (
        (ACTION_STEP_BOUNDARY, 'action_design'),
        (SCENE_STEP_BOUNDARY, 'scene_design'),
        (STATE_TRANSITION_STEP_BOUNDARY, 'state_transition'),
        (STATE_PROPAGATION_STEP_BOUNDARY, 'state_propagation'),
    ):
        assert bnd['step_id'] == sid and bnd['out_of_scope']

    # Strict genre isolation: Xuanyi/Xianshi isolate supernatural craft, tech/mecha containment, breakthrough & energy construct.
    xuanyi = execution_profile_for_types(['GENRE_XUANYI'])
    assert set(xuanyi['out_of_scope_categories']) == {
        'action_supernatural_craft',
        'action_tech_containment',
        'scene_supernatural_breakthrough',
        'state_energy_construct',
    }
    assert 'action_chain_tactics' in xuanyi['primary_categories']
    assert 'scene_pov_disclosure' in xuanyi['primary_categories']
    assert 'state_causal_cost' in xuanyi['primary_categories']
    assert 'propagation_information_social' in xuanyi['primary_categories']

    # Xianxia activates supernatural categories while keeping sci-fi mecha/AI containment out_of_scope.
    xianxia = execution_profile_for_types(['GENRE_XIANXIA'])
    assert 'action_supernatural_craft' in xianxia['primary_categories']
    assert 'scene_supernatural_breakthrough' in xianxia['primary_categories']
    assert 'state_energy_construct' in xianxia['primary_categories']
    assert 'action_tech_containment' in xianxia['out_of_scope_categories']

    # Kehuan activates tech/AI/mecha/containment while keeping alchemy/array supernatural craft out_of_scope.
    kehuan = execution_profile_for_types(['GENRE_KEHUAN'])
    assert 'action_tech_containment' in kehuan['primary_categories']
    assert 'action_supernatural_craft' in kehuan['out_of_scope_categories']

    # Subgenre inheritance & crossover promotion.
    sub_profile = execution_profile_for_types(['SUB_XIANXIA_01'])
    assert 'action_supernatural_craft' in sub_profile['primary_categories']
    crossover = execution_profile_for_types(['GENRE_XUANYI', 'GENRE_LINGYI'])
    assert 'action_tech_containment' in crossover['primary_categories']
    assert 'scene_supernatural_breakthrough' in crossover['primary_categories']

    # Deterministic method classification across 08–11.
    assert 'action_cost_dilemma' in classify_execution_method({
        'tasks': ['action_chain'], 'outputs': [{'stage': 'action_design', 'field': 'candidates'}],
        'title': '能力门槛与试错失败代价行动链', 'operations': [{'instruction': '检验能力门槛、记录失败回撤与道德困境代价'}],
    })
    assert 'scene_pov_disclosure' in classify_execution_method({
        'tasks': ['scene_composition'], 'outputs': [{'stage': 'scene_design', 'field': 'members'}],
        'title': '受限POV知情差披露控场法', 'operations': [{'instruction': '锁定单场POV与allowed_disclosure边界，严防缺席者信息偷跑'}],
    })
    assert 'state_cognition_relation' in classify_execution_method({
        'tasks': ['state_change'], 'outputs': [{'stage': 'state_transition', 'field': 'transitions'}],
        'title': '信念崩溃与信任易崩难建迁移法', 'operations': [{'instruction': '围绕心智模型破裂、权力反转与活跃状态过载核对前后态'}],
    })
    assert 'propagation_information_social' in classify_execution_method({
        'tasks': ['state_propagation'], 'outputs': [{'stage': 'state_propagation', 'field': 'candidates'}],
        'title': '非全知流言传信三门传播法', 'operations': [{'instruction': '用目击与流言作为传播载体生成conditional_candidate并守住三门'}],
    })


def test_execution_08_11_planning_replay_determinism_and_phase_hooks(tmp_path: Path) -> None:
    from nw.call_budget import create_budget
    from nw.config import Config
    from nw.materials.stage_input import model_package
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.studio.corpus_prompts import method_messages
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance
    from nw.task_models import Budget

    # 1) Method derivation prompts inject 08–11 genre boundary guidance & target_step_blueprint cleanly.
    m_msgs = method_messages({
        'thread': {'id': 't_prog', 'domain': 'chapter_progress', 'details': {}},
        'events': [], 'links': [], 'evidence': [], 'confirmed_types': ['GENRE_XUANYI'],
    }, version=5)
    sys_m = m_msgs[0]['content']
    assert '08行动–11状态传播·分类型边界（悬疑）' in sys_m
    assert '禁止全员瞬间全知' in sys_m
    user_m = json.loads(m_msgs[1]['content'])
    assert len(user_m['target_step_blueprint']['execution_categories']) == 12
    assert set(user_m['target_step_blueprint']['execution_step_boundaries']) == {
        'action_design', 'scene_design', 'state_transition', 'state_propagation',
    }
    # Preserve existing Round-7 plot_event_categories in chapter_progress guide.
    assert len(user_m['target_step_blueprint']['plot_event_categories']) == 12

    # 2) planning.prepare_plan_task freezes execution_material_profile, excludes from model_package, replays deterministically.
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    brief_text = '雾夜封闭孤岛证人失踪，刑警必须在断联 12 小时内还原时间线与凶手真实动机。'
    studio.create_project('replay_exec', '08至11回放验证', brief_text=brief_text, constraints='现实悬疑无超自然')
    store = Store(ws / 'replay_exec')
    brief = store.briefs()[-1]
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '孤岛雾夜', 'idea': brief.text, 'constraints': brief.constraints,
        'design_mode': 'manual', 'planning_hierarchy': True,
    }, lib)
    gov = governance(wizard, library=lib)
    budget_id = create_budget(store, 'plan:exec-replay', Budget(max_calls=12, context_char_limit=120000, output_limit=4000))
    cfg = Config('ollama', 'http://localhost', '[FAKE] test', '', 30, {}, ws)

    class _DummyProvider:
        name = 'ollama'

    _, pkg1 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'exec-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert 'execution_material_profile' in pkg1
    assert set(pkg1['execution_material_profile']) == {
        'action_design', 'scene_design', 'state_transition', 'state_propagation',
    }
    assert 'action_supernatural_craft' in [
        c['id'] for c in pkg1['execution_material_profile']['action_design']['out_of_scope_categories']
    ]
    assert 'scene_supernatural_breakthrough' in [
        c['id'] for c in pkg1['execution_material_profile']['scene_design']['out_of_scope_categories']
    ]
    assert 'state_energy_construct' in [
        c['id'] for c in pkg1['execution_material_profile']['state_transition']['out_of_scope_categories']
    ]
    assert 'execution_material_profile' not in model_package(pkg1)
    _, pkg2 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'exec-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert pkg2['execution_material_profile'] == pkg1['execution_material_profile']

    # 3) phase_flow wires execution_material_profile into all four stages 08–11.
    pf_src = (ROOT / 'src' / 'nw' / 'materials' / 'phase_flow.py').read_text(encoding='utf-8')
    assert "if stage in ('action_design', 'scene_design', 'state_transition', 'state_propagation') and package.get('execution_material_profile'):" in pf_src
    assert "payload['execution_material_profile'] = exec_stage_profile" in pf_src


def test_execution_blueprint_http_and_frontend_08_11_hooks(tmp_path: Path, monkeypatch) -> None:
    import http.client
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.api import StudioService
    from nw.studio.library import LibraryService
    from nw.studio.server import create_studio_server

    # 1) Verify frontend UI hooks across PlanArtifacts, prerequisites, and atlas.
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    plan_js = (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    for token in (
        'actionStageHandoffBanner',
        'sceneStageHandoffBanner',
        'stateTransitionStageHandoffBanner',
        'statePropagationStageHandoffBanner',
        'executionStageExtras',
    ):
        assert token in plan_js, token
    prereq_js = (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    for token in (
        'actionBlueprintCategories',
        'sceneBlueprintCategories',
        'stateTransitionBlueprintCategories',
        'statePropagationBlueprintCategories',
        'executionCategoriesHtml',
    ):
        assert token in prereq_js, token
    atlas_js = (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')
    assert 'atlasExecutionProfile' in atlas_js and '/kb/execution-blueprint' in atlas_js

    # 2) Verify live HTTP /api/kb/execution-blueprint, /api/kb/step-blueprint, /api/kb/handoff-audit with approved 08–11 methods.
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'title': '夜渡案卷', 'filename': 'exec.txt', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    prog_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'chapter_progress')

    def ev_rows(thread: dict) -> list[dict]:
        eids = list(dict.fromkeys([
            *thread['evidence_ids'],
            *(eid for ev in structure['body']['events'] if ev['id'] in thread['node_ids'] for eid in ev['evidence_ids']),
        ]))
        return [
            {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
             'quote': ev_by_id[eid]['quote'], 'explanation': '原文执行链观察'}
            for eid in eids
        ]

    def approve_exec_method(title: str, task: str, stage: str, field: str, artifact: str,
                            in_kind: str, consumer: str, instruction: str) -> None:
        saved = lib.save_method({
            'expected_version': 0,
            'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [prog_thread['id']]},
            'body': {
                'title': title,
                'tasks': [task], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI'],
                'prerequisites': [{'key': 'p1', 'input_kind': in_kind, 'artifact': '上游设计产物', 'requirement': '已具备上游输入'}],
                'operations': [{'key': 'op1', 'instruction': instruction, 'input_keys': ['p1'], 'output_keys': ['out1']}],
                'outputs': [{'key': 'out1', 'stage': stage, 'field': field, 'artifact_kind': artifact, 'description': title}],
                'downstream': [{'output_key': 'out1', 'consumer': consumer, 'usage': '交接给下游执行'}],
                'acceptance': [{'output_key': 'out1', 'check': '产物完整满足步骤边界', 'evidence_required': '步骤设计产物'}],
                'evidence': ev_rows(prog_thread),
                'applicability': ['悬疑章场细化'], 'non_applicability': ['无因果跳步流水账'],
            },
        })
        lib.review_method(saved['id'], {'version': 1, 'decision': 'approve', 'note': '批准执行链方法'})

    approve_exec_method(
        '能力门槛与试错回撤行动链法', 'action_chain', 'action_design', 'candidates', 'stage_product',
        'event_design', 'scene_design', '核对能力门槛，记录障碍试错、失败回撤与真实代价',
    )
    approve_exec_method(
        '受限POV知情差披露控场法', 'scene_composition', 'scene_design', 'members', 'scene',
        'action_design', 'state_transition', '严守单场POV视角边界与allowed_disclosure披露范围',
    )
    approve_exec_method(
        '外部行动因果与代价延续迁移法', 'state_change', 'state_transition', 'transitions', 'stage_product',
        'scene_design', 'state_propagation', '原样核对before_state，仅由外部行动触发after_state差值并保留代价不消失',
    )
    approve_exec_method(
        '非全知流言传信三门传播法', 'state_propagation', 'state_propagation', 'candidates', 'stage_product',
        'state_transition', 'anchor_design', '通过目击与流言载体生成conditional_candidate并全部开启三门守卫',
    )

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_eb, body_eb = get_json('/api/kb/execution-blueprint?types=GENRE_XUANYI')
        assert st_eb == 200
        cov = body_eb['coverage_summary']
        assert cov['receivable_action_methods'] == 1
        assert cov['receivable_scene_methods'] == 1
        assert cov['receivable_transition_methods'] == 1
        assert cov['receivable_propagation_methods'] == 1
        assert cov['covered_primary_categories'] >= 4
        assert 'action_supernatural_craft' in body_eb['out_of_scope_categories']
        assert 'action_tech_containment' in body_eb['out_of_scope_categories']

        st_ha, body_ha = get_json('/api/kb/handoff-audit?types=GENRE_XUANYI&planning_hierarchy=1')
        assert st_ha == 200 and 'execution_profile' in body_ha
        assert len(body_ha['execution_profile']['categories']) == 12

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200
        by_sid = {s['step_id']: s for s in body_bp['steps']}
        assert len(by_sid['action_design']['action_categories']) == 4
        assert len(by_sid['scene_design']['scene_categories']) == 3
        assert len(by_sid['state_transition']['transition_categories']) == 3
        assert len(by_sid['state_propagation']['propagation_categories']) == 2
        for sid in ('action_design', 'scene_design', 'state_transition', 'state_propagation'):
            assert by_sid[sid]['step_boundary']['step_id'] == sid
    finally:
        server.shutdown()
        server.server_close()


def test_craft_12_17_taxonomy_covers_all_35_genres_and_narration_stage_routing(tmp_path: Path) -> None:
    from nw.studio import catalog
    from nw.studio.craft_materials import (
        ACCEPTANCE_STEP_BOUNDARY,
        ANCHOR_STEP_BOUNDARY,
        BIND_SCOPE_STEP_BOUNDARY,
        CRAFT_CATEGORIES,
        EXPRESSION_STEP_BOUNDARY,
        GENRE_CRAFT_PROFILES,
        REVIEW_STEP_BOUNDARY,
        WRITER_STEP_BOUNDARY,
        classify_craft_method,
        craft_profile_for_types,
    )
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance

    main_genres = [g['id'] for g in catalog.genres()]
    assert len(main_genres) == 35
    assert set(main_genres) == set(GENRE_CRAFT_PROFILES)
    assert len(CRAFT_CATEGORIES) == 12
    for bnd, sid in (
        (ANCHOR_STEP_BOUNDARY, 'anchor_design'),
        (EXPRESSION_STEP_BOUNDARY, 'expression_design'),
        (BIND_SCOPE_STEP_BOUNDARY, 'bind_scope'),
        (WRITER_STEP_BOUNDARY, 'writer'),
        (REVIEW_STEP_BOUNDARY, 'review'),
        (ACCEPTANCE_STEP_BOUNDARY, 'acceptance'),
    ):
        assert bnd['step_id'] == sid and bnd['out_of_scope']

    # Verify narration (7 groups), tone (10), style (20) parse cleanly with non-empty meanings.
    nar_groups = catalog.options('narration')
    assert len(nar_groups) == 7
    tone_children = catalog.options('tone')[0]['children']
    style_children = catalog.options('style')[0]['children']
    assert len(tone_children) == 10 and len(style_children) == 20
    for slot in ('narration', 'tone', 'style'):
        for key, opt in catalog.option_map(slot).items():
            if opt.get('selectable', True):
                assert opt.get('definition') or opt.get('description') or opt.get('source_excerpt'), key

    # Pick concrete anchor & expression narration IDs and verify strict per-option stage routing while preserving legacy 109.2.
    by_group = {g['key']: g for g in nar_groups}
    anc_id = by_group['narration.group.anchor_beats']['children'][0]['id']
    expr_id = by_group['narration.group.dialogue_subtext']['children'][0]['id']
    assert anc_id.startswith('anc.') and expr_id.startswith('expr.')

    lib = LibraryService(tmp_path / 'ws')
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '潜台词与锚点路由', 'idea': '档案员在审讯室察觉谎言微表情',
        'design_mode': 'manual',
        'narration_ids': ['109.2', anc_id, expr_id],
        'tone_ids': ['TONE_COLD'],
        'style_ids': ['STYLE_SUSPENSE'],
    }, lib)
    gov = governance(wizard, library=lib)
    assert gov['scene_design']['author_preferences']['narration'] == ['109.2']
    assert gov['anchor_design']['author_preferences']['narration'] == [anc_id]
    assert set(gov['expression_design']['author_preferences']['narration']) == {'109.2', expr_id}
    assert gov['expression_design']['author_preferences']['tone'] == ['TONE_COLD']
    assert gov['expression_design']['author_preferences']['style'] == ['STYLE_SUSPENSE']
    assert 'anchor_design' not in gov['type_selection']['project_config']
    assert gov['type_selection']['project_config']['tone_ids'] == ['TONE_COLD']
    assert gov['type_selection']['project_config']['style_ids'] == ['STYLE_SUSPENSE']

    # Item-level genre differentiation for tone & style.
    xy_styles = {c['id']: c['relevance'] for c in catalog.options('style', types=['GENRE_XUANYI'])[0]['children']}
    assert xy_styles['STYLE_SUSPENSE'] == 'primary' and xy_styles['STYLE_GRITTY'] == 'primary'
    assert xy_styles['STYLE_FANTASY'] == 'out_of_scope' and xy_styles['STYLE_ROMANTIC'] == 'out_of_scope'

    xx_styles = {c['id']: c['relevance'] for c in catalog.options('style', types=['GENRE_XIANXIA'])[0]['children']}
    assert xx_styles['STYLE_FANTASY'] == 'primary' and xx_styles['STYLE_POETIC'] == 'primary'
    assert xx_styles['STYLE_REALISTIC'] == 'out_of_scope' and xx_styles['STYLE_HORROR'] == 'out_of_scope'

    yq_tones = {c['id']: c['relevance'] for c in catalog.options('tone', types=['GENRE_YANQING'])[0]['children']}
    assert yq_tones['TONE_WARM'] == 'primary' and yq_tones['TONE_INTIMATE'] == 'primary'
    assert yq_tones['TONE_EPIC'] == 'out_of_scope'

    # Subgenre inheritance & crossover promotion.
    sub_p = craft_profile_for_types(['SUB_XIANXIA_01'])
    assert 'STYLE_FANTASY' in sub_p['preferred_styles']
    cross_p = craft_profile_for_types(['GENRE_XUANYI', 'GENRE_XIANXIA'])
    assert 'STYLE_SUSPENSE' in cross_p['preferred_styles'] and 'STYLE_FANTASY' in cross_p['preferred_styles']

    # Deterministic method classification across 12–17.
    assert 'anchor_body_camera' in classify_craft_method({
        'tasks': ['anchors'], 'outputs': [{'stage': 'anchor_design', 'field': 'beats'}],
        'title': '特写镜头与脉搏点身体微反应锚点', 'operations': [{'instruction': '围绕POV观察者安排身体反应与特写镜头节拍'}],
    })
    assert 'expr_dialogue_sensory' in classify_craft_method({
        'tasks': ['expression'], 'outputs': [{'stage': 'expression_design', 'field': 'guidance'}],
        'downstream': [{'consumer': 'writer'}, {'consumer': 'review'}],
        'title': '潜台词对白与快慢语言质感指导', 'operations': [{'instruction': '通过非直接回答与五感距离生成表达指导并交付写审'}],
    })
    assert 'bind_scope_contract' in classify_craft_method({
        'tasks': ['method_binding'], 'outputs': [{'stage': 'bind_scope', 'field': 'method_guidance'}],
        'downstream': [{'consumer': 'acceptance'}],
        'title': '三层精准筛选与方法落场收口', 'operations': [{'instruction': '汇总method_guidance并校验数据传递完整性'}],
    })


def test_craft_12_17_decomposition_planning_replay_and_phase_hooks(tmp_path: Path) -> None:
    from nw.call_budget import create_budget
    from nw.config import Config
    from nw.materials.stage_input import model_package
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.studio.corpus_prompts import messages as corpus_messages, method_messages
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance
    from nw.task_models import Budget

    # 1) Relations prompt with craft=False injects 12–17 genre guidance with zero craft-only leakage.
    rel_msgs = corpus_messages(
        'relations',
        {'domain': 'narration', 'events': [], 'evidence': [], 'prefix': 'R_0_00000'},
        version=5, passages=True, craft=False, confirmed_types=['GENRE_XUANYI'],
    )
    sys_rel = rel_msgs[0]['content']
    assert '12–17 锚点与表达·按本书类型（悬疑）' in sys_rel
    assert 'sensory_evidence' not in sys_rel and 'reader_address' not in sys_rel

    # 2) Method derivation prompt injects 12–17 boundary guidance & target_step_blueprint craft sections.
    m_msgs = method_messages({
        'thread': {'id': 't_nar', 'domain': 'narration', 'details': {}},
        'events': [], 'links': [], 'evidence': [], 'confirmed_types': ['GENRE_XUANYI'],
    }, version=5)
    assert '12锚点–17写审验收·分类型边界（悬疑）' in m_msgs[0]['content']
    user_m = json.loads(m_msgs[1]['content'])
    assert len(user_m['target_step_blueprint']['craft_categories']) == 12
    assert set(user_m['target_step_blueprint']['craft_step_boundaries']) == {
        'anchor_design', 'expression_design', 'bind_scope', 'writer', 'review', 'acceptance',
    }

    # 3) planning.prepare_plan_task freezes craft_material_profile, excludes from model_package, replays deterministically.
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    brief_text = '雾夜封闭孤岛证人失踪，刑警必须在断联 12 小时内还原时间线与凶手真实动机。'
    studio.create_project('replay_craft', '12至17回放验证', brief_text=brief_text, constraints='现实悬疑无超自然')
    store = Store(ws / 'replay_craft')
    brief = store.briefs()[-1]
    wizard = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '雾夜封条', 'idea': brief.text, 'constraints': brief.constraints,
        'design_mode': 'manual', 'planning_hierarchy': True,
    }, lib)
    gov = governance(wizard, library=lib)
    budget_id = create_budget(store, 'plan:craft-replay', Budget(max_calls=12, context_char_limit=120000, output_limit=4000))
    cfg = Config('ollama', 'http://localhost', '[FAKE] test', '', 30, {}, ws)

    class _DummyProvider:
        name = 'ollama'

    _, pkg1 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'craft-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert 'craft_material_profile' in pkg1
    assert set(pkg1['craft_material_profile']) == {'anchor_design', 'expression_design', 'bind_scope'}
    assert 'STYLE_SUSPENSE' in pkg1['craft_material_profile']['expression_design']['preferred_styles']
    assert 'TONE_COLD' in pkg1['craft_material_profile']['expression_design']['preferred_tones']
    assert 'craft_material_profile' not in model_package(pkg1)
    _, pkg2 = prepare_plan_task(
        store, brief.version, 'book', _DummyProvider(), cfg, budget_id, 'craft-replay',
        governance_inputs=gov, production_method_policy=wizard.get('production_methods'), planning_hierarchy=True,
    )
    assert pkg2['craft_material_profile'] == pkg1['craft_material_profile']

    # 4) phase_flow wires craft_material_profile into stages 12–14.
    pf_src = (ROOT / 'src' / 'nw' / 'materials' / 'phase_flow.py').read_text(encoding='utf-8')
    assert "if stage in ('anchor_design', 'expression_design', 'bind_scope') and package.get('craft_material_profile'):" in pf_src
    assert "payload['craft_material_profile'] = craft_stage_profile" in pf_src


def test_craft_blueprint_options_http_and_frontend_12_17_hooks(tmp_path: Path, monkeypatch) -> None:
    import http.client
    import threading
    from corpus_fixture import CorpusModel, SOURCE, runtime, wait_job
    from nw.studio.api import StudioService
    from nw.studio.library import LibraryService
    from nw.studio.server import create_studio_server

    # 1) Verify frontend UI hooks across WizardStep, wizard, PlanArtifacts, prerequisites, and atlas.
    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    assert "stage:'场景视角'" in (js_root / 'components' / 'WizardStep.js').read_text(encoding='utf-8')
    wizard_js = (js_root / 'pages' / 'wizard.js').read_text(encoding='utf-8')
    for token in ('wizardNarrationGuide', 'wizardToneGuide', 'wizardStyleGuide', '/kb/craft-blueprint'):
        assert token in wizard_js, token
    plan_js = (js_root / 'components' / 'PlanArtifacts.js').read_text(encoding='utf-8')
    for token in (
        'anchorStageHandoffBanner',
        'expressionStageHandoffBanner',
        'bindScopeStageHandoffBanner',
        'craftAndBindStageExtras',
    ):
        assert token in plan_js, token
    prereq_js = (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    for token in (
        'anchorBlueprintCategories',
        'expressionBlueprintCategories',
        'bindScopeBlueprintCategories',
        'writerBlueprintCategories',
        'reviewBlueprintCategories',
        'acceptanceBlueprintCategories',
        'craftCategoriesHtml',
    ):
        assert token in prereq_js, token
    atlas_js = (js_root / 'pages' / 'atlas.js').read_text(encoding='utf-8')
    assert 'atlasCraftProfile' in atlas_js and '/kb/craft-blueprint' in atlas_js

    # 2) Live HTTP verification of /api/options (narration/tone/style), /api/kb/craft-blueprint, /api/kb/handoff-audit, /api/kb/step-blueprint.
    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    provider = CorpusModel()
    monkeypatch.setattr(lib, '_corpus_runtime', lambda: (runtime(), provider))
    book = lib.import_book({'title': '潜台词案卷', 'filename': 'craft.txt', 'text': SOURCE})
    lib.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': True})
    job = lib.start_corpus_job(book['id'], {'options': {'extent': 'complete', 'note': '[FAKE] 完整文本'}})
    done = wait_job(lib, book['id'], job['id'])
    assert done['status'] == 'completed', done['error']
    lib.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'note': '通过'})
    structure = lib.get_corpus(book['id'])
    ev_by_id = {e['id']: e for e in structure['body']['evidence']}
    nar_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'narration')
    main_thread = next(t for t in structure['body']['threads'] if t['domain'] == 'main_plot')

    def ev_rows_for(thread: dict) -> list[dict]:
        eids = list(dict.fromkeys([
            *thread['evidence_ids'],
            *(eid for ev in structure['body']['events'] if ev['id'] in thread['node_ids'] for eid in ev['evidence_ids']),
        ]))
        return [
            {'book_id': book['id'], 'start': ev_by_id[eid]['start'], 'end': ev_by_id[eid]['end'],
             'quote': ev_by_id[eid]['quote'], 'explanation': '原文叙述与节拍观察'}
            for eid in eids
        ]

    def approve_craft_method(title: str, task: str, stage: str, field: str, in_kind: str,
                             consumers: list[str], instruction: str, thread_obj: dict) -> None:
        saved = lib.save_method({
            'expected_version': 0,
            'structure_origin': {'book_id': book['id'], 'structure_version': 1, 'thread_ids': [thread_obj['id']]},
            'body': {
                'title': title,
                'tasks': [task], 'scopes': ['chapter'], 'type_tags': ['GENRE_XUANYI'],
                'prerequisites': [{'key': 'p1', 'input_kind': in_kind, 'artifact': '上游设计', 'requirement': '已具备上游产物'}],
                'operations': [{'key': 'op1', 'instruction': instruction, 'input_keys': ['p1'], 'output_keys': ['out1']}],
                'outputs': [{'key': 'out1', 'stage': stage, 'field': field, 'artifact_kind': 'stage_product', 'description': title}],
                'downstream': [{'output_key': 'out1', 'consumer': c, 'usage': f'交接给 {c} 执行与核验'} for c in consumers],
                'acceptance': [{'output_key': 'out1', 'check': '正文引文清晰可核验', 'evidence_required': '正文具体段落'}],
                'evidence': ev_rows_for(thread_obj),
                'applicability': ['悬疑章场锚点与表达收口'], 'non_applicability': ['跳步流水账'],
            },
        })
        lib.review_method(saved['id'], {'version': 1, 'decision': 'approve', 'note': '批准收尾方法'})

    approve_craft_method(
        '特写镜头与脉搏点具象节拍法', 'anchors', 'anchor_design', 'beats',
        'scene_design', ['expression_design', 'writer'], '围绕POV观察者安排身体微反应与特写镜头节拍', nar_thread,
    )
    approve_craft_method(
        '潜台词非直接回答表达指导法', 'expression', 'expression_design', 'guidance',
        'anchor_design', ['writer', 'review'], '以潜台词与快慢语言质感输出分场表达指导与审稿判据', nar_thread,
    )
    approve_craft_method(
        '三层精准筛选与方法落场收口法', 'method_binding', 'bind_scope', 'method_guidance',
        'parent_outline', ['writer', 'review', 'acceptance'], '汇总本场method_guidance并核验数据传递完整性', main_thread,
    )

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_nar, body_nar = get_json('/api/options?slot=narration&types=GENRE_XUANYI')
        assert st_nar == 200 and len(body_nar['options']) == 7 and body_nar['craft_profile']['has_genre_binding'] is True

        st_tn, body_tn = get_json('/api/options?slot=tone&types=GENRE_XUANYI')
        assert st_tn == 200 and body_tn['options'][0]['children'][0]['relevance'] == 'primary'
        assert body_tn['options'][0]['children'][-1]['relevance'] == 'out_of_scope'

        st_st, body_st = get_json('/api/options?slot=style&types=GENRE_XUANYI')
        assert st_st == 200 and body_st['options'][0]['children'][0]['relevance'] == 'primary'
        assert body_st['options'][0]['children'][-1]['relevance'] == 'out_of_scope'

        st_xx, body_xx = get_json('/api/options?slot=style&parent=style.group.types&types=GENRE_XIANXIA')
        assert st_xx == 200 and body_xx['options'][0]['id'] == 'STYLE_FANTASY' and body_xx['options'][0]['relevance'] == 'primary'

        st_cb, body_cb = get_json('/api/kb/craft-blueprint?types=GENRE_XUANYI')
        assert st_cb == 200
        cov = body_cb['coverage_summary']
        assert cov['receivable_anchor_methods'] == 1
        assert cov['receivable_expression_methods'] == 1
        assert cov['receivable_bind_scope_methods'] == 1
        assert cov['receivable_writer_methods'] == 3
        assert cov['receivable_review_methods'] == 2
        assert cov['receivable_acceptance_methods'] == 1

        st_ha, body_ha = get_json('/api/kb/handoff-audit?types=GENRE_XUANYI&planning_hierarchy=1')
        assert st_ha == 200 and len(body_ha['craft_profile']['categories']) == 12

        st_bp, body_bp = get_json('/api/kb/step-blueprint')
        assert st_bp == 200
        by_sid = {s['step_id']: s for s in body_bp['steps']}
        assert len(by_sid['anchor_design']['anchor_categories']) == 2
        assert len(by_sid['expression_design']['expression_categories']) == 6
        assert len(by_sid['bind_scope']['bind_scope_categories']) == 1
        assert len(by_sid['writer']['writer_categories']) == 1
        assert len(by_sid['review']['review_categories']) == 1
        assert len(by_sid['acceptance']['acceptance_categories']) == 1
        for sid in ('world_design', 'character_design', 'static_relations', 'plot_design', 'event_design',
                    'action_design', 'scene_design', 'state_transition', 'state_propagation',
                    'anchor_design', 'expression_design', 'bind_scope', 'writer', 'review', 'acceptance'):
            assert by_sid[sid]['step_boundary']['step_id'] == sid
    finally:
        server.shutdown()
        server.server_close()


def test_writing_15_17_genre_guidance_prompts_and_legacy_zero_drift(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.cards import decide_card, save_card
    from nw.config import Config
    from nw.llm.base import GenResult
    from nw.llm.fake import FakeProvider
    from nw.models import Draft
    from nw.scene_messages import draft_messages
    from nw.store import Store
    from nw.story_extract import freeze_delta_input, prepare_delta
    from nw.story_state import adopt_story
    from nw.studio.craft_materials import (
        acceptance_genre_guidance,
        design_genre_ids,
        review_genre_guidance,
        writing_genre_guidance,
    )
    from story_fixture import baseline

    # 1) design_genre_ids extracts canonical IDs cleanly and returns [] for legacy/untyped designs.
    assert design_genre_ids(None) == []
    assert design_genre_ids({}) == []
    assert design_genre_ids({'work_session': {'stages': []}}) == []
    assert design_genre_ids({
        'work_session': {'stages': [{'stage': 'type_selection', 'products': {'selection': [{'id': 'GENRE_XUANYI'}]}}]}
    }) == ['GENRE_XUANYI']
    assert design_genre_ids({
        'work_session': {'production_method_policy': {'type_ids': ['GENRE_XIANXIA']}}
    }) == ['GENRE_XIANXIA']

    # 2) Empty genre list produces empty guidance (zero legacy drift).
    assert writing_genre_guidance([]) == ''
    assert review_genre_guidance([]) == ''
    assert acceptance_genre_guidance([]) == ''

    w_guide = writing_genre_guidance(['GENRE_XUANYI'])
    r_guide = review_genre_guidance(['GENRE_XUANYI'])
    a_guide = acceptance_genre_guidance(['GENRE_XUANYI'])
    assert '15正文写作·悬疑约束' in w_guide and 'allowed_disclosure' in w_guide
    assert '16独立审稿·悬疑红线' in r_guide
    assert '17状态提取与事实复核·悬疑口径' in a_guide and 'WORLD' in a_guide

    # 3) draft_messages appends system-only guidance without changing user payload bytes (evidence.py:336 invariant).
    pkg = {'scene': 's1', 'items': [{'source': 'scene:s1', 'text': '核验封条'}]}
    draft = Draft('d1', 's1', 'r1', 1, '沈砚借手电光看清封条边沿。', '2026-11-27T00:00:00Z', 'complete')
    rev_base, _ = draft_messages(pkg, 'review', draft, None, None, '', (), None, genre_ids=None)
    rev_xy, _ = draft_messages(pkg, 'review', draft, None, None, '', (), None, genre_ids=['GENRE_XUANYI'])
    assert rev_xy[-1]['content'] == rev_base[-1]['content']
    assert rev_base[0]['content'] in rev_xy[0]['content']
    assert '16独立审稿·悬疑红线' in rev_xy[0]['content']
    assert '16独立审稿·悬疑红线' not in rev_base[0]['content']

    rv_base, _ = draft_messages(pkg, 'revise', draft, {'notes': '补动作'}, None, '', (), None, genre_ids=None)
    rv_xy, _ = draft_messages(pkg, 'revise', draft, {'notes': '补动作'}, None, '', (), None, genre_ids=['GENRE_XUANYI'])
    assert rv_xy[-1]['content'] == rv_base[-1]['content']
    assert '15正文写作·悬疑约束' in rv_xy[0]['content']

    # 4) story_extract freezes genre_ids, strips it from model context JSON, and injects 17 guidance into both prompts.
    class _ExtractSpy(FakeProvider):
        def generate(self, messages, **params):
            self.calls.append(messages)
            prompt = messages[0]['content']
            if '{"operations"' in prompt:
                return GenResult(json.dumps({'operations': []}, ensure_ascii=False), 'complete', {}, 'test', {})
            return GenResult(json.dumps({'findings': []}, ensure_ascii=False), 'complete', {}, 'test', {})

    with Store(tmp_path / 'extract_book', create=True, test_mode=True) as store:
        store.init_project('提取测试')
        store.add_brief('雨夜档案室封条失窃')
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '核验封条', 'visibility': 'public'}}, None)
        c_dec = decide_card(store, c_ref, 'approved', '确认')
        s_ref = save_card(store, {'card_id': 'sc1', 'kind': 'scene', 'origin': 'author',
                                  'body': {'title': '封条', 'pov': 'yan', 'goal': '核验封条', 'story_time': '1'}}, None)
        s_dec = decide_card(store, s_ref, 'approved', '确认')
        ch = store.add_chapter(1, '封条')
        sc = store.add_scene(ch.id, 1, json.dumps({'story': {
            'scene_ref': {'card_id': 'sc1', 'version': 1}, 'story_order': 1}}))
        adopt_story(store, baseline(card_refs=[
            {**asdict(c_ref), 'decision_id': c_dec.id},
            {**asdict(s_ref), 'decision_id': s_dec.id},
        ]), {})
        from nw.call_budget import create_budget
        from nw.models import Run
        from nw.store import now as nw_now
        from nw.task_models import Budget
        store.add_run(Run('r-manual', sc.id, 'write', 'author', 'manual', '{}', '{}', '{}', '', 'error', '{}', nw_now(), ''))
        _, d_obj = store.finish_run('r-manual', GenResult('[FAKE] 沈砚借灯光核验门上封条。', 'complete', {}, 'test', {}))
        budget_id = create_budget(store, 'b-ext', Budget(max_calls=10, context_char_limit=60000, output_limit=2000))
        from nw.call_budget import prepare_call
        from nw.call_control import model_settings
        spy = _ExtractSpy()
        cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        scope = {'id': 'm-ext-1', 'branch_id': 'main', 'base_revision': 0, 'story_order': 1, 'candidate_delta_refs': []}
        ext_params, _ = prepare_call(store, budget_id, spy.name, cfg.params, [])
        freeze_delta_input(
            store, d_obj.id, scope,
            model_settings(spy, cfg.model, ext_params, 'state-extract-v1'),
            genre_ids=['GENRE_XUANYI'],
        )
        prepare_delta(store, d_obj.id, 'm-ext-1', spy, cfg, budget_id)
        assert len(spy.calls) == 2
        for call in spy.calls:
            assert '17状态提取与事实复核·悬疑口径' in call[0]['content']
            payload = json.loads(call[-1]['content'])
            assert 'genre_ids' not in payload.get('context', {})


def test_manual_author_draft_flows_through_independent_review_extract_and_accept(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.cards import decide_card, save_card
    from nw.config import Config
    from nw.llm.base import GenResult
    from nw.novel_flow import resume_job
    from nw.story_state import adopt_story, current_head, state_at
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from story_fixture import baseline
    from test_novel_flow import Model, author

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    prod = ProductionService(studio, lib, test_mode=True)

    # Create a managed novel project directly in the workspace with an approved character + scene.
    ident = 'manualclosure01'
    proj_dir = 'novel-manualclosure'
    assert prod.db.add(ident, proj_dir, '手动稿闭环', {
        'title': '手动稿闭环', 'genre_ids': ['GENRE_XUANYI'], 'idea': '值夜核验封条', 'constraints': '现实悬疑',
    })
    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        proj = store.init_project('手动稿闭环')
        prod.db.update(ident, project_id=proj.id)
        store.add_brief('值夜核验封条', '现实悬疑')
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '核验封条', 'visibility': 'public'}}, None)
        c_dec = decide_card(store, c_ref, 'approved', '确认')
        s_ref = save_card(store, {'card_id': 'sc-1-1', 'kind': 'scene', 'origin': 'author',
                                  'body': {'title': '封条夜查', 'pov': 'yan', 'goal': '核验门上封条',
                                           'conflict': '值夜人闪烁其词', 'allowed_disclosure': '仅限沈砚现场目击',
                                           'story_time': '1'}}, None)
        s_dec = decide_card(store, s_ref, 'approved', '确认')
        ch = store.add_chapter(1, '封条')
        scene = store.add_scene(ch.id, 1, json.dumps({'story': {
            'scene_ref': {'card_id': 'sc-1-1', 'version': 1}, 'story_order': 1}}))
        adopt_story(store, baseline(card_refs=[
            {**asdict(c_ref), 'decision_id': c_dec.id},
            {**asdict(s_ref), 'decision_id': s_dec.id},
        ]), {})

    class _ManualClosureProvider(Model):
        def __init__(self) -> None:
            super().__init__()
            self.write_or_revise_calls = 0

        def generate(self, messages, **params):
            prompt = messages[0]['content']
            payload = json.loads(messages[-1]['content'])
            if '{"recommendation"' in prompt:
                self.calls.append(messages)
                return GenResult(json.dumps({
                    'recommendation': 'pass', 'notes': '[FAKE] 手动稿通过独立审稿', 'core_changes': [],
                }, ensure_ascii=False), 'complete', {}, 'test', {})
            if '{"operations"' in prompt:
                self.calls.append(messages)
                txt = payload['draft']['text']
                value = '铜钥匙在手' if '铜钥匙' in txt else '封条破损'
                # Revising scene 1 replaces scene 1 at story_order=1, so the prior world state before scene 1 is None.
                ops = [{
                    'op': 'set', 'entity_id': 'seal', 'predicate': 'status',
                    'holder': 'WORLD', 'claim': 'fact',
                    'story_order': payload['story_order'],
                    'disclosure_order': payload['disclosure_order'],
                    'expected_old': None, 'new_value': value,
                    'evidence': [payload['evidence_format']],
                }]
                return GenResult(json.dumps({'operations': ops}, ensure_ascii=False), 'complete', {}, 'test', {})
            if '{"findings"' in prompt:
                self.calls.append(messages)
                return GenResult(json.dumps({'findings': []}, ensure_ascii=False), 'complete', {}, 'test', {})
            self.write_or_revise_calls += 1
            return super().generate(messages, **params)

    # Round A: Author writes a manual draft before first acceptance -> must NOT be overwritten by AI write!
    manual_v1 = '雨夜寂静，沈砚举起手电照向档案室木门，发现门上的封条已经破损。'
    saved_v1 = studio.save_manual_draft(proj_dir, scene.id, manual_v1, branch='main')
    assert saved_v1['draft']['text'] == manual_v1

    novel = prod.db.get(ident)
    provider = _ManualClosureProvider()
    with prod.open_store(novel) as store:
        job_id = prod._new_job(novel, {}, store)
        req = json.loads(store.connection.execute(
            'SELECT request_json FROM novel_jobs WHERE id=?', (job_id,)).fetchone()[0])
        assert req['mode'] == 'revise' and req['scene_ids'] == [scene.id]
        cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        pending = resume_job(store, job_id, provider, cfg)
        assert pending.status == 'WAITING' and pending.step == 'batch:confirm', pending.reason
        assert provider.write_or_revise_calls == 0
        # Verify independent review inspected the exact manual prose.
        review_payload = json.loads(provider.calls[0][-1]['content'])
        assert review_payload['draft']['text'] == manual_v1
        done = resume_job(store, job_id, provider, cfg, author('accept'))
        assert done.status == 'DONE', done.reason
        accepted_1 = store.get('draft', store.accepted(scene.id).draft_id)
        assert accepted_1.text == manual_v1
        head_1 = current_head(store)
        assert [f.value for f in state_at(store, 'main', head_1.revision, 1, 'WORLD').facts] == ['封条破损']

    # Round B: Author manually edits the ALREADY-accepted scene -> must trigger revise & close finish() deadlock!
    manual_v2 = '雨夜寂静，沈砚举起手电，不但发现封条破损，还在门缝下拾到一枚旧铜钥匙。'
    studio.save_manual_draft(proj_dir, scene.id, manual_v2, branch='main')
    novel = prod.db.get(ident)
    provider2 = _ManualClosureProvider()
    with prod.open_store(novel) as store:
        job_id2 = prod._new_job(novel, {}, store)
        req2 = json.loads(store.connection.execute(
            'SELECT request_json FROM novel_jobs WHERE id=?', (job_id2,)).fetchone()[0])
        assert req2['mode'] == 'revise' and req2['scene_ids'] == [scene.id]
        cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        pending2 = resume_job(store, job_id2, provider2, cfg)
        assert pending2.status == 'WAITING' and pending2.step == 'batch:confirm', pending2.reason
        assert provider2.write_or_revise_calls == 0
        done2 = resume_job(store, job_id2, provider2, cfg, author('accept'))
        assert done2.status == 'DONE', done2.reason
        accepted_2 = store.get('draft', store.accepted(scene.id).draft_id)
        assert accepted_2.text == manual_v2
        head_2 = current_head(store)
        assert [f.value for f in state_at(store, 'main', head_2.revision, 1, 'WORLD').facts] == ['铜钥匙在手']


def test_studio_quality_15_17_http_and_frontend_execution_hooks(tmp_path: Path) -> None:
    from dataclasses import asdict
    import http.client
    import threading
    from nw.cards import decide_card, save_card
    from nw.config import Config
    from nw.llm.base import GenResult
    from nw.novel_flow import resume_job
    from nw.story_state import adopt_story
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from nw.studio.server import create_studio_server
    from story_fixture import baseline
    from test_novel_flow import Model, author

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    inspector_js = (js_root / 'components' / 'Inspector.js').read_text(encoding='utf-8')
    assert 'inspectorExecutionStatus' in inspector_js and 'inspectorWritingContract' in inspector_js
    assert 'inspectorStateDelta' in inspector_js and 'inspectorReviewDraft' in inspector_js
    studio_js = (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'sceneExecutionRibbon' in studio_js and 'sceneWritingBrief' in studio_js
    assert 'reviewManualDraft' in studio_js and 'sceneExecutionRibbonBox' in studio_js
    decisions_js = (js_root / 'pages' / 'studio-decisions.js').read_text(encoding='utf-8')
    assert 'batchAcceptanceGate' in decisions_js and 'batchAcceptanceSummary' in decisions_js

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    prod = ProductionService(studio, lib, test_mode=True)
    ident = 'qualityhttp01'
    proj_dir = 'novel-qualityhttp'
    assert prod.db.add(ident, proj_dir, '质量接口验收', {
        'title': '质量接口验收', 'genre_ids': ['GENRE_XUANYI'], 'idea': '档案夜查', 'constraints': '现实悬疑',
    })
    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        proj = store.init_project('质量接口验收')
        prod.db.update(ident, project_id=proj.id)
        store.add_brief('档案夜查', '现实悬疑')
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '查找缺失页码', 'visibility': 'public'}}, None)
        c_dec = decide_card(store, c_ref, 'approved', '确认')
        s_ref = save_card(store, {'card_id': 'sc-q-1', 'kind': 'scene', 'origin': 'author',
                                  'body': {'title': '档案核验', 'pov': 'yan', 'goal': '查找缺失页码',
                                           'conflict': '门禁记录被改写', 'allowed_disclosure': '仅限现场所见',
                                           'story_time': '1'}}, None)
        s_dec = decide_card(store, s_ref, 'approved', '确认')
        ch = store.add_chapter(1, '档案')
        scene = store.add_scene(ch.id, 1, json.dumps({'story': {
            'scene_ref': {'card_id': 'sc-q-1', 'version': 1}, 'story_order': 1}}))
        adopt_story(store, baseline(card_refs=[
            {**asdict(c_ref), 'decision_id': c_dec.id},
            {**asdict(s_ref), 'decision_id': s_dec.id},
        ]), {})

    studio.save_manual_draft(proj_dir, scene.id, '沈砚翻开值班簿，确认第三页被人整页撕去。', branch='main')

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def get_json(path: str) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                conn.request('GET', path)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        # Before review: manual draft surfaced as needs_review with writing_contract & zero delta.
        st1, q1 = get_json(f'/api/novels/{ident}/quality?scene={scene.id}')
        assert st1 == 200
        assert q1['writing_contract']['pov'] == 'yan'
        assert q1['writing_contract']['allowed_disclosure'] == '仅限现场所见'
        assert q1['writing_contract']['writer_review_focus']
        assert q1['writing_contract']['acceptance_focus']
        assert q1['draft_status']['is_manual'] is True
        assert q1['draft_status']['is_accepted'] is False
        assert q1['draft_status']['needs_review'] is True
        assert q1['draft_status']['stage_label'] == '15 手动修改待独立审稿'
        assert q1['delta'] is None and q1['fact_findings'] == []

        # Run independent review + extract + accept on the manual draft.
        class _AcceptModel(Model):
            def generate(self, messages, **params):
                prompt = messages[0]['content']
                payload = json.loads(messages[-1]['content'])
                if '{"recommendation"' in prompt:
                    return GenResult(json.dumps({'recommendation': 'pass', 'notes': '通过', 'core_changes': []}, ensure_ascii=False), 'complete', {}, 'test', {})
                if '{"operations"' in prompt:
                    return GenResult(json.dumps({'operations': [{
                        'op': 'set', 'entity_id': 'logbook', 'predicate': 'page3',
                        'holder': 'WORLD', 'claim': 'fact',
                        'story_order': payload['story_order'],
                        'disclosure_order': payload['disclosure_order'],
                        'expected_old': None, 'new_value': '已撕毁',
                        'evidence': [payload['evidence_format']],
                    }]}, ensure_ascii=False), 'complete', {}, 'test', {})
                if '{"findings"' in prompt:
                    return GenResult(json.dumps({'findings': []}, ensure_ascii=False), 'complete', {}, 'test', {})
                return super().generate(messages, **params)

        novel = prod.db.get(ident)
        with prod.open_store(novel) as store:
            jid = prod._new_job(novel, {}, store)
            cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
            prov = _AcceptModel()
            wait_res = resume_job(store, jid, prov, cfg)
            assert wait_res.step == 'batch:confirm'
            assert resume_job(store, jid, prov, cfg, author('accept')).status == 'DONE'

        st2, q2 = get_json(f'/api/novels/{ident}/quality?scene={scene.id}')
        assert st2 == 200
        assert q2['draft_status']['is_accepted'] is True
        assert q2['draft_status']['needs_review'] is False
        assert q2['draft_status']['review_recommendation'] == 'pass'
        assert q2['draft_status']['has_delta'] is True
        assert q2['draft_status']['stage_label'] == '17 已接受入库'
        assert len(q2['delta']['world_operations']) == 1
        assert q2['delta']['world_operations'][0]['new_value'] == '已撕毁'
        assert q2['fact_findings'] == []
    finally:
        server.shutdown()
        server.server_close()


def test_post17_chapter_summary_and_periodic_reviews_feed_next_chapter_planning(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.acceptance import accept_batch
    from nw.call_budget import create_budget
    from nw.cards import decide_card, save_card
    from nw.config import Config
    from nw.llm.base import GenResult
    from nw.models import Run
    from nw.planning import prepare_plan_task
    from nw.store import now as nw_now
    from nw.story_state import adopt_story, current_head
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from nw.task_models import Budget
    from story_fixture import baseline, draft_for, proposal

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    prod = ProductionService(studio, lib, test_mode=True)
    ident = 'post17loop01'
    proj_dir = 'novel-post17loop'
    assert prod.db.add(ident, proj_dir, '三章复盘闭环', {
        'title': '三章复盘闭环', 'genre_ids': ['GENRE_XUANYI'], 'idea': '三章连查旧案', 'constraints': '现实悬疑',
    })

    scene_ids: list[str] = []
    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        proj = store.init_project('三章复盘闭环')
        prod.db.update(ident, project_id=proj.id)
        store.add_brief('三章连查旧案', '现实悬疑')
        approvals = []
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '追查旧案', 'visibility': 'public'}}, None)
        approvals.append({**asdict(c_ref), 'decision_id': decide_card(store, c_ref, 'approved', '确认').id})
        p_ref = save_card(store, {'card_id': 'p-key', 'kind': 'promise', 'origin': 'author',
                                  'body': {'title': '七道刻痕', 'setup': '钥匙上的七道刻痕对应七次查验',
                                           'payoff': '终章核验簿册揭晓第七次查验真相'}}, None)
        approvals.append({**asdict(p_ref), 'decision_id': decide_card(store, p_ref, 'approved', '确认').id})
        titles = {1: '夜查封条', 2: '值班簿裂页', 3: '档案室对质'}
        for ch_idx in (1, 2, 3):
            s_ref = save_card(store, {'card_id': f'sc-{ch_idx}-1', 'kind': 'scene', 'origin': 'author',
                                      'body': {'title': titles[ch_idx], 'pov': 'yan', 'goal': '核验线索', 'story_time': str(ch_idx)}}, None)
            approvals.append({**asdict(s_ref), 'decision_id': decide_card(store, s_ref, 'approved', '确认').id})
            ch = store.add_chapter(ch_idx, f'第{ch_idx}章案卷')
            sc = store.add_scene(ch.id, 1, json.dumps({'story': {
                'scene_ref': {'card_id': f'sc-{ch_idx}-1', 'version': 1}, 'story_order': ch_idx}}))
            scene_ids.append(sc.id)
        head = adopt_story(store, baseline(card_refs=approvals), {})

        # Before acceptance, saving chapter summary raises clean ValueError (never KeyError).
        with pytest.raises(ValueError, match='CHAPTER_SCOPE_INCOMPLETE'):
            studio.record_chapter_summary(proj_dir, 1, '未接受前尝试填写')
        with pytest.raises(ValueError, match='CHAPTER_SCOPE_INCOMPLETE'):
            prod.save_chapter_summary(ident, 1, {'summary': '未接受前尝试填写'})

        # Accept all 3 chapters with real WORLD facts, character beliefs, and promise planting.
        for ch_idx, sid in enumerate(scene_ids, start=1):
            head = current_head(store, 'main')
            txt = f'[FAKE] 第{ch_idx}章正文：沈砚查到钥匙上的七道刻痕，并怀疑值夜人撒谎。'
            draft = draft_for(store, sid, txt)
            ops = []
            if ch_idx == 1:
                ops.extend([
                    {'op': 'set', 'entity_id': 'p-key', 'predicate': 'promise_stage', 'holder': 'WORLD',
                     'claim': 'fact', 'story_order': 1, 'disclosure_order': [1, 1, 0],
                     'expected_old': None, 'new_value': 'planted',
                     'evidence': [{'draft_id': draft.id, 'text_sha256': '', 'start': 0, 'end': 10}]},
                    {'op': 'set', 'entity_id': 'guard', 'predicate': 'trust', 'holder': 'yan',
                     'claim': 'suspicion', 'story_order': 1, 'disclosure_order': [1, 1, 0],
                     'expected_old': None, 'new_value': '值夜人撒谎',
                     'evidence': [{'draft_id': draft.id, 'text_sha256': '', 'start': 0, 'end': 10}]},
                ])
            from nw.story_delta import draft_digest
            for op in ops:
                op['evidence'][0]['text_sha256'] = draft_digest(draft)
            req = proposal(store, head, draft, ops)
            accept_batch(store, [req], head, f'accept-ch-{ch_idx}')
            snap = {'messages': [{'content': json.dumps({'draft': {'id': draft.id}})}]}
            run = Run(f'rev-{sid}', sid, 'review', 'author', 'manual-review', '{}',
                      json.dumps(snap), '{}', '', 'error', '{}', nw_now(), '')
            store.add_run(run)
            store.finish_run(run.id, GenResult('{"recommendation":"pass"}', 'complete', {}, 'fixture', {}))

    # Versioned scene titles surface cleanly in project_overview and ProgressTree!
    overview = studio.project_overview(proj_dir)
    assert [s['title'] for s in overview['scenes']] == ['夜查封条', '值班簿裂页', '档案室对质']
    prog = prod.progress(ident)
    chapter_nodes = [n for n in prog['tree'] if n['label'].startswith('第1章')]
    assert chapter_nodes and chapter_nodes[0]['children'][0]['label'] == '场1 · 夜查封条'

    # Continuation overview surfaces all 3 chapters, due periodic reviews at ch3, promise snapshot, and knowledge matrix.
    cont = prod.continuation(ident)
    assert cont['managed_story'] is True and len(cont['chapters']) == 3
    ch3 = cont['chapters'][2]
    assert ch3['scope_complete'] is True and ch3['summary_status'] == 'ready'
    ch3_review_kinds = {r['kind'] for r in ch3['reviews']}
    assert {'resource-update', 'character', 'cost', 'commitment', 'resource-inventory', 'commitment-ending'} <= ch3_review_kinds
    assert cont['promises']['items'][0]['card_id'] == 'p-key'
    assert cont['promises']['items'][0]['accepted_stage'] == 'planted'
    assert cont['promises']['items'][0]['planted_chapter'] == 1
    assert set(cont['knowledge_matrix']['holders']) >= {'WORLD', 'READER', 'yan'}
    assert any(row['entity_id'] == 'guard' and 'yan' in row['cells'] for row in cont['knowledge_matrix']['matrix'])

    # Save chapter 3 summary and periodic character/cost reviews -> verify next-chapter planning receives them!
    prod.save_chapter_summary(ident, 3, {'summary': '沈砚在档案室与值夜人对质，锁定钥匙七道刻痕指向旧查验簿。'})
    prod.save_chapter_review(ident, 3, 'character', {'finding': '沈砚三章行为均符合谨慎求证的初始设定，无突变。'})
    prod.save_chapter_review(ident, 3, 'cost', {'finding': '三章累积了值夜人警惕与体力消耗代价，需在第四章延续。'})

    with prod.open_store({'project_dir': proj_dir}) as store:
        from nw.chapter_records import continuation_reviews, continuation_summary
        from nw.chapter_state import continuation_chapter_state
        from nw.models import Chapter
        from nw.story_state import revision_state

        head = current_head(store, 'main')
        handoff = continuation_chapter_state(store, head, revision_state(store, head))
        assert handoff is not None and handoff['chapter']['index'] == 3
        summ = continuation_summary(store, head, 3)
        assert summ is not None and summ['summary'] == '沈砚在档案室与值夜人对质，锁定钥匙七道刻痕指向旧查验簿。'
        revs = continuation_reviews(store, head, Chapter(**handoff['chapter']))
        findings = [r['finding'] for r in revs]
        assert any('沈砚三章行为' in f for f in findings)
        assert any('累积了值夜人警惕' in f for f in findings)


def test_post17_branch_continuation_signals_and_finish_check_lifecycle(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.acceptance import accept_batch
    from nw.cards import decide_card, save_card
    from nw.llm.base import GenResult
    from nw.models import Run
    from nw.store import now as nw_now
    from nw.story_state import adopt_story, apply_settings, current_head
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from story_fixture import baseline, draft_for, proposal

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    prod = ProductionService(studio, lib, test_mode=True)
    ident = 'post17finish01'
    proj_dir = 'novel-post17finish'
    assert prod.db.add(ident, proj_dir, '分支与完稿体检', {
        'title': '分支与完稿体检', 'genre_ids': ['GENRE_XUANYI'], 'idea': '一章短篇测试', 'constraints': '现实悬疑',
    })

    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        proj = store.init_project('分支与完稿体检')
        prod.db.update(ident, project_id=proj.id)
        store.add_brief('一章短篇测试', '现实悬疑')
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '核验', 'visibility': 'public'}}, None)
        s_ref = save_card(store, {'card_id': 'sc-1', 'kind': 'scene', 'origin': 'author',
                                  'body': {'title': '夜查封条', 'pov': 'yan', 'goal': '核验', 'story_time': '1'}}, None)
        ch = store.add_chapter(1, '封条')
        sc = store.add_scene(ch.id, 1, json.dumps({'story': {
            'scene_ref': {'card_id': 'sc-1', 'version': 1}, 'story_order': 1}}))
        head = adopt_story(store, baseline(card_refs=[
            {**asdict(c_ref), 'decision_id': decide_card(store, c_ref, 'approved', '确认').id},
            {**asdict(s_ref), 'decision_id': decide_card(store, s_ref, 'approved', '确认').id},
        ]), {})
        draft = draft_for(store, sc.id, '[FAKE] 沈砚查明封条真相。')
        accept_batch(store, [proposal(store, head, draft, [])], head, 'accept-1')
        snap = {'messages': [{'content': json.dumps({'draft': {'id': draft.id}})}]}
        run = Run('rev-1', sc.id, 'review', 'author', 'manual-review', '{}',
                  json.dumps(snap), '{}', '', 'error', '{}', nw_now(), '')
        store.add_run(run)
        store.finish_run(run.id, GenResult('{"recommendation":"pass"}', 'complete', {}, 'fixture', {}))

    # 1) On main with all scenes accepted: continuation signals needs_candidate_branch & finish_check passes all 9 gates!
    prog_main = prod.progress(ident)
    assert prog_main['continuation']['needs_candidate_branch'] is True
    assert prog_main['continuation']['summary_pending_chapters'] == [1]

    fc_main = prod.finish_check(ident)
    assert fc_main['ready'] is True and fc_main['blockers'] == []
    assert fc_main['summary']['passed_count'] == fc_main['summary']['total_checks'] == 9
    assert any(a['kind'] == 'chapter_summary' for a in fc_main['advisories'])

    # 2) Fork candidate branch and change approved setting -> human-readable revalidation labels + finish_check blocked on branch_main.
    prod.fork_branch(ident, {'name': '第二章候选'})
    with prod.open_store({'project_dir': proj_dir}) as store:
        w_ref = save_card(store, {'card_id': 'w-new', 'kind': 'world', 'origin': 'author',
                                  'body': {'title': '新规', 'rule': '夜间封锁档案库', 'limits': '限时进入'}}, None)
        w_dec = decide_card(store, w_ref, 'approved', '新增规则')
        apply_settings(store, current_head(store, '第二章候选'), [w_dec.id], 'apply-w-new')

    b_status = prod.branch_status(ident)
    assert b_status['needs_revalidation'] == [sc.id]
    assert b_status['revalidation_details'] == [{'id': sc.id, 'label': '第1章·场1 夜查封条'}]
    fc_cand = prod.finish_check(ident)
    assert fc_cand['ready'] is False
    assert any(c['id'] == 'branch_main' and not c['passed'] for c in fc_cand['checks'])

    # 3) Revalidate & accept on candidate branch -> progress signals can_promote, promote succeeds, finish() completes!
    with prod.open_store({'project_dir': proj_dir}) as store:
        cand_head = current_head(store, '第二章候选')
        new_draft = draft_for(store, sc.id, '[FAKE] 沈砚在封锁前查明封条真相。')
        accept_batch(store, [proposal(store, cand_head, new_draft, [])], cand_head, 'reval-1')
        snap2 = {'messages': [{'content': json.dumps({'draft': {'id': new_draft.id}})}]}
        run2 = Run('rev-2', sc.id, 'review', 'author', 'manual-review', '{}',
                   json.dumps(snap2), '{}', '', 'error', '{}', nw_now(), '')
        store.add_run(run2)
        store.finish_run(run2.id, GenResult('{"recommendation":"pass"}', 'complete', {}, 'fixture', {}))

    b_ready = prod.branch_status(ident)
    assert b_ready['can_promote'] is True
    assert b_ready['changed_scene_details'] == [{'id': sc.id, 'label': '第1章·场1 夜查封条'}]
    assert prod.progress(ident)['continuation']['can_promote'] is True

    promoted = prod.promote_branch(ident, {
        'expected_main': b_ready['main_head']['revision'],
        'expected_candidate': b_ready['candidate_head']['revision'],
        'reason': '旧稿复核完毕，确认合并回主线',
    })
    assert promoted['status'] == 'PROMOTED' and promoted['current_branch'] == 'main'
    assert prod.finish_check(ident)['ready'] is True
    assert prod.finish(ident)['status'] == 'DONE'


def test_post17_continuation_finish_check_http_and_frontend_hooks(tmp_path: Path) -> None:
    from dataclasses import asdict
    import http.client
    import threading
    from nw.acceptance import accept_batch
    from nw.cards import decide_card, save_card
    from nw.llm.base import GenResult
    from nw.models import Run
    from nw.store import now as nw_now
    from nw.story_state import adopt_story
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from nw.studio.server import create_studio_server
    from story_fixture import baseline, draft_for, proposal

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    bc_js = (js_root / 'components' / 'BookContinuation.js').read_text(encoding='utf-8')
    for tok in ('bookContinuationHub', 'chapterContinuationList', 'promiseContinuityPanel',
                'knowledgeMatrixPanel', 'finishReadinessPanel', 'finishReadinessDrawer',
                'confirmFinishBook', 'data-summary-form', 'data-review-form'):
        assert tok in bc_js
    book_js = (js_root / 'pages' / 'book.js').read_text(encoding='utf-8')
    assert 'renderContinuationHub' in book_js and '/continuation' in book_js and '/finish-check' in book_js
    studio_js = (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    for tok in ('studioContinuationNotice', 'branchBadge', 'quickOpenBranches', 'quickRevalidate', '建立候选以续写'):
        assert tok in studio_js
    decisions_js = (js_root / 'pages' / 'studio-decisions.js').read_text(encoding='utf-8')
    assert 'revalidation_details' in decisions_js and 'changed_scene_details' in decisions_js

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    lib = LibraryService(ws)
    prod = ProductionService(studio, lib, test_mode=True)
    ident = 'post17http01'
    proj_dir = 'novel-post17http'
    assert prod.db.add(ident, proj_dir, '续写接口测试', {
        'title': '续写接口测试', 'genre_ids': ['GENRE_XUANYI'], 'idea': '档案复盘', 'constraints': '现实悬疑',
    })
    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        proj = store.init_project('续写接口测试')
        prod.db.update(ident, project_id=proj.id)
        store.add_brief('档案复盘', '现实悬疑')
        c_ref = save_card(store, {'card_id': 'yan', 'kind': 'character', 'origin': 'author',
                                  'body': {'name': '沈砚', 'role': '主角', 'want': '核验', 'visibility': 'public'}}, None)
        s_ref = save_card(store, {'card_id': 'sc-h1', 'kind': 'scene', 'origin': 'author',
                                  'body': {'title': '初章验封', 'pov': 'yan', 'goal': '核验', 'story_time': '1'}}, None)
        ch = store.add_chapter(1, '初章')
        sc = store.add_scene(ch.id, 1, json.dumps({'story': {
            'scene_ref': {'card_id': 'sc-h1', 'version': 1}, 'story_order': 1}}))
        head = adopt_story(store, baseline(card_refs=[
            {**asdict(c_ref), 'decision_id': decide_card(store, c_ref, 'approved', '确认').id},
            {**asdict(s_ref), 'decision_id': decide_card(store, s_ref, 'approved', '确认').id},
        ]), {})
        draft = draft_for(store, sc.id, '[FAKE] 沈砚记录档案页码并收好钥匙。')
        accept_batch(store, [proposal(store, head, draft, [])], head, 'http-accept-1')
        snap = {'messages': [{'content': json.dumps({'draft': {'id': draft.id}})}]}
        run = Run('rev-h1', sc.id, 'review', 'author', 'manual-review', '{}',
                  json.dumps(snap), '{}', '', 'error', '{}', nw_now(), '')
        store.add_run(run)
        store.finish_run(run.id, GenResult('{"recommendation":"pass"}', 'complete', {}, 'fixture', {}))

    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def req_json(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                headers = {'Content-Type': 'application/json'} if body is not None else {}
                conn.request(method, path, body=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None, headers=headers)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_c, cont = req_json('GET', f'/api/novels/{ident}/continuation')
        assert st_c == 200 and cont['managed_story'] is True and len(cont['chapters']) == 1
        assert cont['chapters'][0]['summary_status'] == 'ready'

        st_s, saved_s = req_json('POST', f'/api/novels/{ident}/chapters/1/summary', {
            'summary': '沈砚核验档案并收好钥匙，锁定次日追查方向。',
            'input_sha256': cont['chapters'][0]['summary_input_sha256'],
        })
        assert st_s == 200 and saved_s['status'] == 'recorded'

        res_rev = next(r for r in cont['chapters'][0]['reviews'] if r['kind'] == 'resource-update')
        st_r, saved_r = req_json('POST', f'/api/novels/{ident}/chapters/1/reviews/resource-update', {
            'finding': '本章沈砚新增铜钥匙一件，其余资源无消耗。',
            'input_sha256': res_rev['input_sha256'],
        })
        assert st_r == 200 and saved_r['status'] == 'recorded'

        st_f, fc = req_json('GET', f'/api/novels/{ident}/finish-check')
        assert st_f == 200 and fc['ready'] is True and len(fc['checks']) == 9
        assert not any(a['kind'] == 'chapter_summary' for a in fc['advisories'])
    finally:
        server.shutdown()
        server.server_close()


def test_round12_material_key_noise_filter_and_stage_aware_joint_roles(tmp_path: Path, monkeypatch) -> None:
    from nw.cards import decide_card, save_card
    from nw.context.story import build_story_context, scene_scope
    from nw.materials.stage_input import extract_step_keys
    from nw.materials.step_guard import build_joint_material_plan
    from nw.store import Store
    from nw.story_state import adopt_story

    # 1) Noise field-name filtering in extract_step_keys (both synthetic markdown & real STAGE_MATERIALS)
    from nw.materials.phase_flow import STAGE_MATERIALS
    sample_material = (
        "### type\n【本步用法】\n噪声字段\n\n"
        "### visual\n【本步用法】\n噪声字段\n\n"
        "### 12\n【本步用法】\n噪声行号\n\n"
        "### 1.1_动机\n【本步用法】\n用于确立角色动机。\n\n"
        "### PLOT_MECHANISM_DUNGEON 迷宫副本\n【本步用法】\n用于副本危机事件。\n"
    )
    keys = extract_step_keys(sample_material)
    for bad in ('type', 'visual', '12'):
        assert bad not in keys
    assert {'1.1_动机', 'PLOT_MECHANISM_DUNGEON'} <= keys

    real_keys = set().union(*(extract_step_keys(mat) for mat in STAGE_MATERIALS.values()))
    assert real_keys
    for bad in ('type', 'concept', 'mechanism', 'structure', 'identity', 'relationship', 'expression', 'visual', '12'):
        assert bad not in real_keys

    # 2) Stage-aware joint material role assignment
    def mk_src(key: str, profile: str, state: str = 'design_ready') -> dict:
        return {'source': {'key': key, 'profile': profile}, 'source_state': state}

    wd_plan = build_joint_material_plan('world_design', [
        mk_src('30.1_世界边界', 'world'),
        mk_src('TE_悬疑基调', 'type_expression'),
        mk_src('AC_物证具象', 'anchor', 'reference'),
    ])
    assert wd_plan is not None
    assert wd_plan['drivers'] == ['30.1_世界边界']
    assert set(wd_plan['boundaries']) == {'TE_悬疑基调', 'AC_物证具象'}
    assert wd_plan.get('anchors_and_expression', []) == []
    assert '126.15' in wd_plan['creative_autonomy_rule']

    ed_plan = build_joint_material_plan('expression_design', [
        mk_src('109.2_受限叙述', 'type_expression'),
        mk_src('AC1.1_动作节拍', 'anchor'),
        mk_src('DR_动作博弈', 'dynamic_relation'),
        mk_src('1.1_人物动机', 'character'),
        mk_src('PL_伏笔结构', 'plot'),
    ])
    assert ed_plan is not None
    assert ed_plan['drivers'] == ['109.2_受限叙述']
    assert ed_plan['anchors_and_expression'] == ['AC1.1_动作节拍']
    assert set(ed_plan['boundaries']) == {'DR_动作博弈', '1.1_人物动机', 'PL_伏笔结构'}

    ad_plan = build_joint_material_plan('anchor_design', [
        mk_src('AC1.1_动作节拍', 'anchor'),
        mk_src('1.1_人物动机', 'character'),
    ])
    assert ad_plan is not None
    assert ad_plan['drivers'] == ['AC1.1_动作节拍']
    assert ad_plan['boundaries'] == ['1.1_人物动机']

    sd_plan = build_joint_material_plan('scene_design', [
        mk_src('1.1_动机', 'character'),
        mk_src('30.1_世界边界', 'world'),
        mk_src('AC1.1', 'anchor', 'reference'),
    ])
    assert sd_plan is not None
    assert sd_plan['drivers'] == ['1.1_动机']
    assert sd_plan['boundaries'] == ['30.1_世界边界']
    assert sd_plan['anchors_and_expression'] == ['AC1.1']

    # 3) Step-15 writing prompt receives cross-step continuity ledger + vitality guard without mutating work.package
    store = Store(tmp_path / 'story_proj', create=True)
    store.init_project('连续性守卫测试')
    store.add_brief('旧港刑警追查沉船真相', '单章单POV；禁止全知视角')
    ch = store.add_chapter(1, '夜潮')
    char_ref = save_card(store, {
        'card_id': 'char_lin', 'kind': 'character', 'origin': 'author',
        'body': {'name': '林沉', 'role': '刑警主角', 'want': '查明沉船真相', 'visibility': 'public'},
        'source_refs': [],
    }, None)
    char_dec = decide_card(store, char_ref, 'approved', '启用主角卡')
    sc_ref = save_card(store, {
        'card_id': 'sc_card_1', 'kind': 'scene', 'origin': 'author',
        'body': {
            'title': '栈桥验封', 'pov': 'char_lin', 'goal': '核验封条',
            'conflict': '涨潮封锁', 'allowed_disclosure': '仅限现场可见物证',
            'characters': ['char_lin'],
        },
        'source_refs': [],
    }, None)
    sc_dec = decide_card(store, sc_ref, 'approved', '启用场景卡')
    sc = store.add_scene(ch.id, 1, json.dumps({
        'story': {'scene_ref': {'card_id': sc_ref.card_id, 'version': sc_ref.version}, 'story_order': 1},
    }))
    adopt_story(store, {
        'as_of_story_order': 0, 'disclosure_order': [0, 0, 0],
        'coverage': {'entities': ['char_lin'], 'predicates': ['status']},
        'facts': [],
        'card_refs': [
            {'card_id': char_ref.card_id, 'version': char_ref.version, 'decision_id': char_dec.id},
            {'card_id': sc_ref.card_id, 'version': sc_ref.version, 'decision_id': sc_dec.id},
        ],
    }, {})
    design_payload = {
        'materials': [],
        'bindings': {},
        'material_key': 'sc_card_1',
        'work_session': {
            'stages': [
                {
                    'stage': 'character_design',
                    'products': {
                        'members': [{
                            'key': 'char_lin',
                            'body': {'name': '林沉', 'voice': '冷静简短', 'behavior': '先看物证再提问'},
                        }],
                        'capabilities': [{'entity': 'harbor_lock', 'can_act': False}],
                    },
                },
                {
                    'stage': 'plot_design',
                    'products': {
                        'promise_plan': [{'promise': 'p_watch', 'plant_event': 'ev_1', 'payoff_event': 'ev_3', 'setup': '停摆怀表'}],
                    },
                },
            ],
        },
    }
    monkeypatch.setattr('nw.context.story.scene_materials', lambda _s, _sid, _ref=None: design_payload)
    monkeypatch.setattr('nw.context.story.scene_checks', lambda _d, scoped=False: [])
    monkeypatch.setattr('nw.context.story.writer_checks', lambda _d: [])
    work = build_story_context(store, sc.id, scene_scope(store, sc.id, 'main'), 24000)
    assert work.prompt.startswith('按作者约束和本场任务写正文')
    assert '【15写作跨步连续性守卫】' in work.prompt
    assert '人物声线与基线' in work.prompt
    assert '叙事生命力原则' in work.prompt
    assert 'continuity_ledger' not in work.package
    store.connection.close()


def test_round12_wizard_option_stage_precision_and_macro_craft_compass(tmp_path: Path) -> None:
    from nw.materials.author_references import author_stage_input
    from nw.studio import catalog
    from nw.studio.creation_plan import for_stage
    from nw.studio.library import LibraryService
    from nw.studio.production_inputs import freeze_wizard, governance

    hook_map = catalog.option_map('hook')
    assert hook_map['hook.PLOT_MECHANISM_DUNGEON']['stages'] == ['event_design']
    assert hook_map['hook.PLOT_MECHANISM_RULE_TASK']['stages'] == ['event_design']

    nar_map = catalog.option_map('narration')
    assert nar_map['narration.109.2']['stages'] == ['scene_design', 'expression_design']
    for key, opt in nar_map.items():
        if key.startswith('narration.anc.'):
            assert opt['stages'] == ['anchor_design'], key
        elif key.startswith('narration.expr.'):
            assert opt['stages'] == ['expression_design'], key

    lib = LibraryService(tmp_path / 'ws')
    frozen = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'],
        'title': '跨步机制与宏观创作罗盘验证',
        'idea': '封闭海岛档案馆规则怪谈调查',
        'design_mode': 'manual',
        'world_ids': ['31.1', 'PLOT_MECHANISM_SYSTEM'],
        'character_ids': ['1.1', 'PLOT_MECHANISM_BLOODLINE'],
        'mechanism_ids': ['PLOT_MECHANISM_DUNGEON'],
        'narration_ids': ['109.2'],
        'tone_ids': ['TONE_SERIOUS'],
        'style_ids': ['STYLE_GRITTY'],
    }, lib)
    gov = governance(frozen)
    mechs = set(gov['type_selection']['project_config']['mechanism_ids'])
    assert {'PLOT_MECHANISM_SYSTEM', 'PLOT_MECHANISM_BLOODLINE', 'PLOT_MECHANISM_DUNGEON'} <= mechs
    assert 'PLOT_MECHANISM_DUNGEON' in gov['event_design']['author_preferences']['hook']
    assert 'hook' not in gov['plot_design'].get('author_preferences', {})

    plan = frozen['creation_plan']
    ta_slice = for_stage(plan, 'type_adaptation')
    pd_slice = for_stage(plan, 'plot_design')
    assert ta_slice is not None and 'macro_craft_compass' in ta_slice
    assert pd_slice is not None and 'macro_craft_compass' in pd_slice
    assert 'PLOT_MECHANISM_DUNGEON' in {c['id'] for c in pd_slice['macro_craft_compass']}
    assert 'preferences' not in ta_slice

    # Pure style/narration choices still must NOT leak into world_design
    style_only = freeze_wizard({
        'genre_ids': ['GENRE_XUANYI'], 'title': '纯文风隔离', 'idea': '夜班核查',
        'design_mode': 'manual', 'style_ids': ['STYLE_GRITTY'], 'narration_ids': ['109.2'],
    }, lib)
    assert 'creation_plan' not in author_stage_input({'governance_inputs': governance(style_only)}, 'world_design')


def test_round12_client_sandbox_context_cards_search_and_adopt_hooks(tmp_path: Path) -> None:
    import http.client
    import threading
    from nw.studio.api import StudioService
    from nw.studio.server import create_studio_server

    js_root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    prereq_js = (js_root / 'pages' / 'prerequisites.js').read_text(encoding='utf-8')
    kb_js = (js_root / 'pages' / 'kb.js').read_text(encoding='utf-8')
    studio_js = (js_root / 'pages' / 'studio.js').read_text(encoding='utf-8')
    inspector_js = (js_root / 'components' / 'Inspector.js').read_text(encoding='utf-8')
    cards_js = (js_root / 'components' / 'StoryCards.js').read_text(encoding='utf-8')
    book_js = (js_root / 'pages' / 'book.js').read_text(encoding='utf-8')
    cont_js = (js_root / 'components' / 'BookContinuation.js').read_text(encoding='utf-8')

    assert 'jointMaterialSandbox' in prereq_js and 'pipelineRuntimeBlueprint' in prereq_js
    assert 'data.sources' in prereq_js
    assert 'kbSearchFilters' in kb_js and 'kbSearchPagination' in kb_js
    assert 'sceneContextInspector' in studio_js and 'openManualDelta' in studio_js
    assert 'btnZenDiff' in studio_js and 'btnZenRead' in studio_js
    assert 'formatContractItem' in inspector_js
    assert 'storyCardsBrowser' in cards_js and 'newAuthorCardBtn' in cards_js
    assert 'editBriefBtn' in book_js and 'addBibleBtn' in book_js and "['cards','设定卡片']" in book_js
    assert 'adoptStoryBtn' in cont_js

    ws = tmp_path / 'ws'
    studio = StudioService(workspace=ws, config_path=tmp_path / 'missing.toml')
    server = create_studio_server(studio, host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]

        def req_json(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            try:
                headers = {'Content-Type': 'application/json'} if body is not None else {}
                raw = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
                conn.request(method, path, body=raw, headers=headers)
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode('utf-8'))
            finally:
                conn.close()

        st_bp, bp = req_json('GET', '/api/pipeline/blueprint?scope=chapter')
        assert st_bp == 200 and len(bp['design_steps']) == 14 and len(bp['runtime_steps']) >= 6

        st_sim, sim = req_json('POST', '/api/pipeline/simulate', {
            'scope': 'chapter', 'stage': 'expression_design', 'simulate_prior_products': True,
        })
        assert st_sim == 200 and 'rendered_prompt' in sim

        st_ms, ms = req_json('GET', '/api/materials/search?stage=world_design&limit=5&offset=0')
        assert st_ms == 200 and 'items' in ms
        st_ls, ls = req_json('GET', '/api/ledger/search?disposition=open&limit=5&offset=0')
        assert st_ls == 200 and 'facets' in ls

        st_n, created = req_json('POST', '/api/novels', {
            'genre_ids': ['GENRE_XUANYI'], 'title': '客户端全闭环验证',
            'idea': '旧港封条夜查', 'design_mode': 'manual',
        })
        assert st_n == 201
        novel = created['novel']
        ident = novel['id']
        proj = novel['project_dir']

        st_br, br = req_json('POST', f'/api/projects/{proj}/brief', {
            'text': '旧港刑警林沉夜查封条破口', 'constraints': '单章单POV；禁止机械降神',
        })
        assert st_br == 200 and br['version'] >= 2

        st_bi, bi = req_json('POST', f'/api/projects/{proj}/bible', {
            'kind': 'world', 'name': '潮汐锁港表', 'body': '每日23:00涨潮漫过北栈桥',
        })
        assert st_bi == 200 and bi['name'] == '潮汐锁港表'

        st_ch, ch = req_json('POST', f'/api/projects/{proj}/chapters', {'index': 1, 'title': '潮封栈桥'})
        assert st_ch == 200
        st_sc, sc = req_json('POST', f'/api/projects/{proj}/scenes', {
            'chapter_id': ch['id'], 'index': 1, 'card': {'title': '夜查封条'},
        })
        assert st_sc == 200

        st_c1, c1 = req_json('POST', f'/api/projects/{proj}/cards', {
            'card_id': 'char_lin', 'kind': 'character',
            'body': {'name': '林沉', 'role': '刑警主角', 'want': '查清封条破损真相', 'visibility': 'public'},
            'auto_approve': True, 'apply_to_branch': True, 'branch': 'main',
        })
        assert st_c1 == 200 and c1['status'] == 'approved'

        st_c2, c2 = req_json('POST', f'/api/projects/{proj}/cards', {
            'card_id': 'sc_card_01', 'kind': 'scene',
            'body': {
                'title': '夜查封条', 'pov': 'char_lin', 'goal': '核验封条完整性',
                'conflict': '涨潮倒计时', 'allowed_disclosure': '仅限手电可见物证',
                'characters': ['char_lin'],
            },
            'auto_approve': True, 'apply_to_branch': True, 'branch': 'main',
            'bind_scene_id': sc['id'], 'story_order': 1,
        })
        assert st_c2 == 200 and c2['status'] == 'approved'

        st_cl, cl = req_json('GET', f'/api/projects/{proj}/cards')
        assert st_cl == 200 and {c['card_id'] for c in cl['cards']} >= {'char_lin', 'sc_card_01'}

        # Legacy unmanaged project can also be adopted one-click via /api/projects/{dir}/adopt
        st_lp, _ = req_json('POST', '/api/projects', {
            'dir_name': 'legacy-adopt-proj', 'title': '历史未接管项目', 'brief_text': '旧稿导入',
        })
        assert st_lp == 201
        st_ad, ad = req_json('POST', '/api/projects/legacy-adopt-proj/adopt', {
            'include_approved_cards': True, 'entities': ['seal'], 'predicates': ['status'],
        })
        assert st_ad == 200 and ad['branch_id'] == 'main'

        st_ctx, ctx_data = req_json('GET', f'/api/projects/{proj}/scenes/{sc["id"]}/context?branch=main&char_limit=24000')
        assert st_ctx == 200 and ctx_data['total_chars'] > 0 and len(ctx_data['items']) >= 1

        draft_text = '林沉蹲在北栈桥边，借着手电筒看清封条已经断裂。'
        st_dr, dr = req_json('POST', f'/api/projects/{proj}/scenes/{sc["id"]}/draft', {
            'text': draft_text, 'branch': 'main',
        })
        assert st_dr == 200 and dr['draft']['id']
        quote = '封条已经断裂'
        q_start = draft_text.index(quote)
        q_end = q_start + len(quote)

        st_dl, dl = req_json('POST', f'/api/projects/{proj}/scenes/{sc["id"]}/delta', {
            'draft_id': dr['draft']['id'],
            'branch': 'main',
            'story_order': 1,
            'operations': [{
                'op': 'set',
                'entity_id': 'seal',
                'predicate': 'status',
                'holder': 'WORLD',
                'claim': 'fact',
                'story_order': 1,
                'disclosure_order': [1, 1, 0],
                'expected_old': None,
                'new_value': 'broken',
                'evidence': [{'start': q_start, 'end': q_end}],
            }],
        })
        assert st_dl == 200 and dl['findings'] == []

        st_q, q_res = req_json('GET', f'/api/novels/{ident}/quality?scene={sc["id"]}')
        assert st_q == 200
        assert q_res['writing_contract']['pov'] == 'char_lin'
        assert 'anchor_beats' in q_res['writing_contract']
        assert q_res['delta']['id'] == dl['delta']['id']
    finally:
        server.shutdown()
        server.server_close()


def test_round13_quarantine_unblocking_f2_closure_and_step_material_slimming() -> None:
    """Verify Round 13 raw-material unblocking, F2 closure, network prerequisites, and step slimming."""
    from collections import Counter
    from nw.materials import character_prerequisites, stage_input, world_prerequisites
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.work_catalog import SourceDesk
    from nw.studio import catalog as studio_catalog

    # 1. World & Character derived network prerequisites adjudicated and expanded
    assert len(world_prerequisites.SPECS) == 86
    assert {k for k, v in world_prerequisites.SPECS.items() if v['status'] == 'unresolved'} == set()
    for wid in ('C00045', 'C00110', 'C00062', 'C00116', 'C00415', 'C00419'):
        assert world_prerequisites.SPECS[wid]['status'] == 'conditional'
    assert len(character_prerequisites.SPECS) == 55
    for cid in ('C00616', 'C00618', 'C00619', 'C00627', 'C00856', 'C01235', 'C01304', 'C01707'):
        assert character_prerequisites.SPECS[cid]['status'] == 'conditional'

    # 2. Step modules slimmed, boilerplate stripped, parsers & explicit usage boundaries intact
    steps_dir = ROOT / 'src' / 'nw' / 'materials' / 'steps'
    total_step_bytes = sum(p.stat().st_size for p in steps_dir.glob('*.py'))
    assert total_step_bytes < 9_500_000, f'Expected slimmed steps/*.py < 9.5 MB, got {total_step_bytes}'

    for dyn_file in steps_dir.glob('*dynamic_network*.py'):
        assert '【追溯原值】' not in dyn_file.read_text(encoding='utf-8'), dyn_file.name
    for combo_file in steps_dir.glob('type_adaptation_type_combinations*.py'):
        assert '【现行裁定依据】' not in combo_file.read_text(encoding='utf-8'), combo_file.name

    studio_catalog.material.cache_clear()
    studio_catalog._genres.cache_clear()
    studio_catalog._options.cache_clear()
    studio_catalog.combinations.cache_clear()
    stage_input.step_uses.cache_clear()

    combos = studio_catalog.combinations()
    combo_counts = Counter(c['status'] for c in combos)
    assert len(combos) == 4200
    assert combo_counts['design_ready'] == 4095
    assert combo_counts['blocked'] == 105
    for slot in studio_catalog.SLOTS:
        assert studio_catalog.options(slot), slot

    world_uses = stage_input.step_uses(STAGE_MATERIALS['world_design'])
    assert '补充与边界：' in world_uses.get('18.1_能量浓度下降', '')
    assert '补充与边界：' in world_uses.get('15.1_进阶四条件', '') or any(
        '补充与边界：' in v for k, v in world_uses.items() if k.startswith('15.1_')
    )
    from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
    writing_uses = stage_input.step_uses(WRITING_MATERIAL)
    assert any('补充与边界：' in v for k, v in writing_uses.items() if '7.4' in k or '156.5' in k)

    # 3. Live workspace SourceDesk & F2 ledger verification (when workspace is mounted)
    ws = ROOT / 'workspace'
    if (ws / 'materials' / 'catalog.db').is_file() and (ws / 'materials' / 'adjudication.db').is_file():
        desk = SourceDesk(ws)
        states = Counter(r['state'] for r in desk.by_id.values())
        assert states['design_ready'] >= 15000, states
        assert states['blocked'] == 316, states
        blocked_profiles = {r['profile'] for r in desk.by_id.values() if r['state'] == 'blocked'}
        assert blocked_profiles == {'type_combination'}, f'Unexpected blocked profiles: {blocked_profiles}'

    ledger = ws / 'materials' / 'F2_统一问题台账.jsonl'
    if ledger.is_file():
        items = [json.loads(ln) for ln in ledger.read_text(encoding='utf-8').splitlines() if ln.strip()]
        assert sum(1 for x in items if x.get('status') == 'open') == 0
        assert sum(1 for x in items if x.get('status') == 'resolved') >= 2437
        assert (ws / 'materials' / 'F2_权威核定结项报告_batch38.md').is_file()












