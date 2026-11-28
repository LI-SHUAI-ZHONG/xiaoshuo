"""End-to-end tests for Executable Voice Specifications (9 bases + 4 knobs + micro-contrasts),
multi-genre Voice Fingerprint auto-collection in Track 4 decomposition, cross-genre isolation,
Book Voice Spec compilation in Manual/AI Auto wizards, and 15/16 write-review loop wiring.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import threading
from urllib.request import Request, urlopen

from nw.cards import decide_card
from nw.config import Config
from nw.context.story import StoryScope, build_story_context
from nw.llm.base import GenResult
from nw.scene_messages import draft_messages
from nw.story_state import adopt_story
from nw.studio import catalog
from nw.studio.api import StudioService
from nw.studio.corpus_direct import run_targeted_job
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard
from nw.studio.server import create_studio_server
from nw.studio.wizard_setup import setup_profile_for_types
from nw.voice_specs import (
    VOICE_BASES,
    compile_book_voice_spec,
    excluded_types_for_genres,
    infer_scene_function,
    recommend_voice_bases,
    save_voice_fingerprint,
)
from story_fixture import baseline, draft_for
from test_selection import add_card


def test_all_35_genres_recommend_executable_voice_base_with_contrasts():
    all_main = [g['id'] for g in catalog.genres()]
    assert len(all_main) == 35
    for gid in all_main:
        ranked = recommend_voice_bases([gid])
        assert len(ranked) == len(VOICE_BASES) == 9
        top = ranked[0]
        assert len(top['dimensions']) == 6 and all(top['dimensions'].values())
        assert len(top['drift_redlines']) >= 3
        assert len(top['micro_contrasts']) == 3
        for mc in top['micro_contrasts']:
            assert mc['bad_ai'] and mc['target_voice'] and mc['why']
            assert mc['bad_ai'] != mc['target_voice']


def test_compile_book_voice_spec_knobs_and_cross_genre_fingerprint_firewall(tmp_path):
    lib = LibraryService(tmp_path)
    # Seed a xianxia staging book + voice fingerprint in library.db
    book = lib.import_book({
        'title': '太虚问道录',
        'filename': 'taixu.txt',
        'text': '第一章 问剑\n' + '青石阶上晨雾未散，剑修沉吟半晌才缓缓开口。' * 12,
    })
    lib.review_book(book['id'], {'action': 'confirm', 'types': ['GENRE_XIANXIA'], 'grade': 'A'})
    with lib.connect() as conn:
        fp = save_voice_fingerprint(
            conn,
            book_id=book['id'],
            structure_version=1,
            title='古典清雅机锋·语感指纹（太虚）',
            base_voice_id='VOICE_CLASSICAL_EDGE',
            type_tags=['GENRE_XIANXIA'],
            body={
                'dimensions': {'register': '半文半白清雅，禁用现代网络词'},
                'techniques': ['对话中用礼数称谓包裹利益试探，留半句给对手接招'],
                'drift_guards': ['严禁在宗门对话中混入现代口水梗'],
                'scene_functions': ['confrontation', 'opening_hook'],
                'scene_function_notes': {'confrontation': '对峙时先写静物与茶火停顿，再出机锋台词。'},
            },
        )
    assert 'GENRE_DUSHI' in fp['excluded_types']
    assert 'GENRE_DUSHI' in excluded_types_for_genres(['GENRE_XIANXIA'])

    # Compatible genre (xianxia) receives the fingerprint; incompatible genre (dushi) blocks it!
    xianxia_fps = lib.voice_fingerprints(types=['GENRE_XIANXIA'])
    dushi_fps = lib.voice_fingerprints(types=['GENRE_DUSHI'])
    assert len(xianxia_fps) == 1 and xianxia_fps[0]['id'] == fp['id']
    assert dushi_fps == []

    # Compile with orthogonal knob override + legacy tone/style hints + fingerprint
    spec_xianxia = compile_book_voice_spec(
        ['GENRE_XIANXIA'],
        base_voice_id='VOICE_CLASSICAL_EDGE',
        knobs={
            'register': 'semi_classical',
            'cadence': 'kinetic_sharp',
            'dialogue_mind': 'restrained_subtext',
            'anti_drift_bans': ['no_modern_slang', 'no_idiom_stacking', 'no_inventory_ledger'],
        },
        tone_ids=['TONE_COLD'],
        style_ids=['STYLE_POETIC'],
        fingerprints=[fp],
        custom_notes='师门长辈说话留三分余地。',
    )
    assert '短句' in spec_xianxia['dimensions']['cadence']
    assert any('冷峻≠无情绪面瘫' in h for h in spec_xianxia['legacy_tone_style_hints'])
    assert len(spec_xianxia['fingerprints']) == 1
    assert any('严禁在宗门对话中混入现代口水梗' in r for r in spec_xianxia['drift_redlines'])

    # Cross-genre firewall inside compile_book_voice_spec rejects xianxia fingerprint on dushi novel!
    spec_dushi = compile_book_voice_spec(
        ['GENRE_DUSHI'],
        fingerprints=[fp],
    )
    assert spec_dushi['fingerprints'] == []
    assert spec_dushi['base_voice_id'] == 'VOICE_NET_VERNACULAR'


def test_targeted_decomp_track4_auto_collects_voice_fingerprint_and_wizard_exposes_it(tmp_path):
    lib = LibraryService(tmp_path)
    ch1_text = '山门青石阶在暴雨里发滑，陆清河攥紧断剑，盯着高台上神色平静的执事，半晌才问：“这笔灵石账，长老打算怎么算？”'
    ch2_text = '三日后山风骤起，石壁剑痕隐隐透出寒意，他压住翻涌气血，一剑斜掠截断对手退路，精铁剑锋震出清越长鸣。'
    full_text = f'书籍信息\n书名：太虚剑录\n【简介】测试简介。\n\n第1章 暴雨山门\n{ch1_text * 3}\n\n第2章 寒石试剑\n{ch2_text * 3}\n'
    book = lib.import_book({'title': '太虚剑录', 'filename': 'taixu_jian.txt', 'text': full_text})
    lib.review_book(book['id'], {'action': 'confirm', 'types': ['GENRE_XIANXIA'], 'grade': 'A'})

    class MockTargetedProvider:
        name = 'mock_real'

        def generate(self, messages, *, model='', params=None, **kwargs):
            user = json.loads(messages[-1]['content'])
            if 'source_text' in user:
                quote = ch1_text[:60] if user['chapter_index'] == 1 else ch2_text[:60]
                return GenResult(
                    text=json.dumps({
                        'chapter_summary': f"第{user['chapter_index']}章冲突推进",
                        'key_characters': [{'name': '陆清河', 'role': '主角', 'quote': quote[:24]}],
                        'observations': [{
                            'track': 'scene_prose_craft',
                            'title': '克制对峙与动词收束写法',
                            'what_happened': '人物在压迫下以克制问句和具体动作回击',
                            'function_effect': '不喊口号却拉满对峙张力',
                            'reusable_pattern': '先写环境与手中物件触感，再用带利益指向的克制短句反问压场。',
                            'boundary': '适用于仙侠与古风对峙戏，不适用于轻快搞笑日常。',
                            'quotes': [quote],
                        }],
                        'voice_signals': {
                            'scene_function': 'confrontation' if user['chapter_index'] == 1 else 'action_reveal',
                            'register': '半文半白凝练，不用现代网梗',
                            'cadence': '铺垫平缓，交手骤切短句',
                            'dialogue_texture': '礼数下藏机锋，问句直指利害',
                            'psychic_distance': '贴身压抑克制，不直喊情绪词',
                            'quote': quote,
                        },
                    }, ensure_ascii=False),
                    finish_reason='complete',
                    usage={},
                    request_id='mock-ext',
                    raw={},
                )
            return GenResult(
                text=json.dumps({
                    'book_overview': {
                        'central_question': '底层修士如何在宗门规矩下破局',
                        'mainline': '借实利试探与斗法立威推进',
                        'character_arcs': '克制隐忍到当场反制',
                        'information_payoffs': '对白留半句引出后续冲突',
                        'structure': '压迫起手与动作收口交替',
                    },
                    'methods': [{
                        'track': 'scene_prose_craft',
                        'task': 'expression',
                        'title': '静物蓄压加克制机锋对白法',
                        'obs_ids': ['O001'],
                        'applicability': ['仙侠或古风宗门对峙场景'],
                        'non_applicability': ['不适用于现代都市轻喜剧'],
                        'operation': '开场先落一处冷硬环境与手中物件，再让主角以具体账目或规矩反问对手，禁用情绪抽象词。',
                        'output_desc': '本场表达指导须注明蓄压静物与反问落点',
                        'acceptance_check': '正文须同时具备具象物件动作与带利害指向的反问句',
                        'evidence_required': '正文引文呈现物件动作及对手受压反应',
                    }],
                    'voice_fingerprint': {
                        'title': '暴雨山门清冷机锋语感指纹',
                        'base_voice_id': 'VOICE_CLASSICAL_EDGE',
                        'scene_functions': ['confrontation', 'action_reveal'],
                        'dimensions': {
                            'register': '半文半白凝练，用词冷硬有骨力',
                            'cadence': '静处舒缓，拔剑与压迫瞬间骤切短句',
                            'psychic_distance': '紧贴视角克制隐忍，少旁白解释',
                            'dialogue_texture': '句短锋利，借规矩账目逼问对方底牌',
                            'imagery_budget': '雨石、寒意、断剑等冷色调实景克制点出',
                            'pacing_payoff': '章尾停在剑鸣或未答复的对峙悬念上',
                        },
                        'techniques': [
                            '用雨声/物件触感替代抽象“气氛紧张”旁白',
                            '对手戏先压住情绪再抛一句带具体筹码的反问',
                        ],
                        'drift_guards': ['严禁在冷清古风对峙里塞入现代网络吐槽'],
                        'scene_function_notes': {
                            'confrontation': '先写静物与微动作停顿，再用具体利益反问撕开客套。',
                            'action_reveal': '出招前写清气血与风势蓄力，收剑落到金属脆响。',
                        },
                    },
                }, ensure_ascii=False),
                finish_reason='complete',
                usage={},
                request_id='mock-syn',
                raw={},
            )

    cfg = Config('openai_compat', 'http://localhost', 'mock-model', '', 300.0, {}, tmp_path, True, {})
    prov = MockTargetedProvider()
    lib._corpus_runtime = lambda: (cfg, prov)

    job = lib.start_corpus_job(book['id'], {
        'kind': 'targeted',
        'options': {
            'extent': 'complete',
            'note': '测试样本',
            'sample_mode': 'key_chapters',
            'sample_count': 2,
            'tracks': ['scene_prose_craft'],
            'auto_approve': True,
            'max_calls': 10,
            'max_input_chars': 32000,
        },
    })
    # Wait for background worker thread
    worker = lib._tasks.get(job['id'])
    if worker:
        worker.join(timeout=15)

    done_job = lib.get_corpus_job(book['id'], job['id'])
    assert done_job['status'] == 'completed', done_job.get('error')
    pub_fp = done_job['progress'].get('published_voice_fingerprint')
    assert pub_fp is not None
    assert pub_fp['base_voice_id'] == 'VOICE_CLASSICAL_EDGE'
    assert 'GENRE_XIANXIA' in pub_fp['type_tags']
    assert 'GENRE_DUSHI' in pub_fp['excluded_types']

    # Setup profile exposes it for GENRE_XIANXIA and hides it for GENRE_DUSHI!
    prof_xx = setup_profile_for_types(['GENRE_XIANXIA'], library=lib)
    assert prof_xx['voice_setup']['recommended_base_id'] == 'VOICE_CLASSICAL_EDGE'
    assert len(prof_xx['voice_setup']['available_fingerprints']) == 1
    assert prof_xx['ai_auto_defaults']['voice_profile']['fingerprint_ids'] == [pub_fp['id']]

    prof_ds = setup_profile_for_types(['GENRE_DUSHI'], library=lib)
    assert prof_ds['voice_setup']['recommended_base_id'] == 'VOICE_NET_VERNACULAR'
    assert prof_ds['voice_setup']['available_fingerprints'] == []

    # AI Auto freeze_wizard automatically compiles voice_spec with the matching fingerprint!
    wiz = freeze_wizard({
        'design_mode': 'auto',
        'genre_ids': ['GENRE_XIANXIA'],
        'creative_workflow': True,
        'planning_hierarchy': True,
    }, lib)
    assert wiz['voice_spec']['base_voice_id'] == 'VOICE_CLASSICAL_EDGE'
    assert pub_fp['id'] in wiz['voice_spec']['fingerprint_ids']


def test_voice_spec_flows_through_http_creation_15_write_and_16_review(tmp_path):
    workspace = tmp_path / 'ws'
    cfg_path = tmp_path / 'studio.config.toml'
    cfg_path.write_text(
        '[model]\nprovider="ollama"\nbase_url="http://127.0.0.1:11434"\nmodel="mock"\ntimeout=60\n',
        encoding='utf-8',
    )
    service = StudioService(workspace, config_path=cfg_path)
    server = create_studio_server(service, host='127.0.0.1', port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def call(method: str, path: str, body: dict | None = None):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        headers = {'Content-Type': 'application/json'} if data is not None else {}
        req = Request(f'http://127.0.0.1:{port}{path}', data=data, headers=headers, method=method)
        with urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    try:
        # 1. KB voice fingerprints endpoint
        status, kb_fp = call('GET', '/api/kb/voice-fingerprints?types=GENRE_XIANXIA')
        assert status == 200
        assert len(kb_fp['voice_bases']) == 9
        assert kb_fp['voice_bases'][0]['id'] == 'VOICE_CLASSICAL_EDGE'
        assert set(kb_fp['knobs'].keys()) == {'register', 'cadence', 'dialogue_mind', 'anti_drift_bans'}

        # 2. Seed a novel & configure its Book Voice Spec via HTTP
        prod = server.production
        ident = 'voice-spec-http-novel'
        proj_dir = 'novel-voicespec'
        prod.db.add(ident, proj_dir, '问剑雨夜', {'title': '问剑雨夜', 'genre_ids': ['GENRE_XIANXIA']})
        with prod.open_store({'project_dir': proj_dir}, create=True) as store:
            project = store.init_project('问剑雨夜')
            prod.db.update(ident, project_id=project.id)
            store.add_brief('宗门账目疑案', '单POV')
            ch = store.add_chapter(1, '雨夜山门')
            sc_card = add_card(store, 'sc1', 'scene', {
                'title': '雨夜试探',
                'goal': '陆清河试探长老口风',
                'conflict': '长老拿门规压人，拒认欠账',
                'pov': 'lu',
                'characters': ['lu'],
                'story_time': '1',
                'visibility': 'public',
            })
            lu_card = add_card(store, 'lu', 'character', {'name': '陆清河', 'role': '主角', 'want': '查账', 'visibility': 'public'})
            d_sc = decide_card(store, sc_card, 'approved', 'ok')
            d_lu = decide_card(store, lu_card, 'approved', 'ok')
            adopt_story(store, baseline(card_refs=[
                {**asdict(sc_card), 'decision_id': d_sc.id},
                {**asdict(lu_card), 'decision_id': d_lu.id},
            ]), {})
            sc = store.add_scene(ch.id, 1, json.dumps({
                'story': {'scene_ref': asdict(sc_card), 'story_order': 1},
            }))
            scene_id = sc.id

        status, vs_saved = call('POST', f'/api/novels/{ident}/voice-spec', {
            'enabled': True,
            'base_voice_id': 'VOICE_CLASSICAL_EDGE',
            'knobs': {
                'register': 'semi_classical',
                'cadence': 'kinetic_sharp',
                'dialogue_mind': 'restrained_subtext',
                'anti_drift_bans': ['no_modern_slang', 'no_idiom_stacking'],
            },
            'custom_notes': '严守古典留白与茶烟意象。',
        })
        assert status == 200
        assert vs_saved['voice_spec']['base_voice_id'] == 'VOICE_CLASSICAL_EDGE'
        assert vs_saved['voice_spec']['enabled'] is True

        # 3. Inspect Step 15 context: voice-spec packet mounted with micro-contrasts & drift redlines
        status, ctx_data = call('GET', f'/api/projects/{proj_dir}/scenes/{scene_id}/context?branch=main')
        assert status == 200
        assert ctx_data['has_voice_spec'] is True
        vs_item = next(it for it in ctx_data['items'] if it['key'] == 'voice-spec')
        vs_pkt = json.loads(vs_item['content'])
        assert vs_pkt['voice_name'] == '古典清雅机锋流'
        assert len(vs_pkt['micro_contrasts']) == 2
        assert vs_pkt['author_voice_notes'] == '严守古典留白与茶烟意象。'

        # 4. Step 16 review & revise automatically pick up Book Voice Spec drift redlines from the frozen package!
        with prod.open_store({'project_dir': proj_dir}) as store:
            work = build_story_context(
                store, scene_id, StoryScope('main', 0, 1, {'card_id': 'sc1', 'version': 1}), 24000,
            )
            draft = draft_for(store, scene_id, '他垂眼拨了拨茶沫，笑了一声。')
            review_msgs, _ = draft_messages(work.package, 'review', draft, None, None, '', ())
            revise_msgs, _ = draft_messages(work.package, 'revise', draft, {'recommendation': 'revise', 'notes': '调整语感'}, None, '', ())
            assert '本书语感防漂移验收：古典清雅机锋流' in review_msgs[0]['content']
            assert '严禁在仙侠/历史对话中混入现代网梗' in review_msgs[0]['content']
            assert '本书语感防漂移验收：古典清雅机锋流' in revise_msgs[0]['content']

        # 5. Quality endpoint reports active voice_spec summary
        status, q = call('GET', f'/api/novels/{ident}/quality?scene={scene_id}')
        assert status == 200
        assert q['voice_spec']['enabled'] is True
        assert q['voice_spec']['base_voice_name'] == '古典清雅机锋流'
        assert infer_scene_function({'conflict': '长老拿门规压人'}, chapter_index=2, scene_index=1) == 'confrontation'
    finally:
        server.shutdown()
        server.server_close()
