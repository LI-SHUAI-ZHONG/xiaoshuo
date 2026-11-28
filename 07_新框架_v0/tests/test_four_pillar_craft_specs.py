"""End-to-end tests for the 4-Pillar Executable Craft Spec Pack:
  - World Rule-Engine Spec (`world_specs.py`, 7 bases)
  - Cast & Character Dynamics Spec (`cast_specs.py`, 7 bases)
  - Plot Engine, 5-Tier Length-Linked Pacing & Hook Spec (`plot_pacing_specs.py`, 8 bases)
  - Unified Facade & `craft_fingerprints` DB registry (`craft_specs_base.py`, `craft_specs.py`)
  - Track 1-4 automatic fingerprint collection in `corpus_direct.py` (0 extra LLM calls + cross-genre firewall)
  - Strict Step-Scoped Injection Matrix (00/03/04/05/06/07/08/09/15 lightweight 2-line beat / 16 same-source review)
  - HTTP API (`/api/novels/<id>/craft-specs`, `/api/kb/craft-fingerprints`, length-tier auto-sync).
"""
from __future__ import annotations

from dataclasses import asdict
import json
import threading
from urllib.request import Request, urlopen

from nw.cards import decide_card
from nw.cast_specs import CAST_BASES, CAST_MECHANISM_EXECUTION_HINTS, recommend_cast_bases
from nw.config import Config
from nw.context.story import StoryScope, build_story_context
from nw.craft_specs import (
    build_direction_specs_summary,
    build_review_craft_guards,
    build_stage_craft_spec_packet,
    compile_craft_spec,
    load_all_craft_specs,
    save_craft_spec,
)
from nw.length_settings import WORD_TIERS
from nw.llm.base import GenResult
from nw.plot_pacing_specs import (
    PLOT_BASES,
    PLOT_MECHANISM_EXECUTION_HINTS,
    STRUCTURE_EXECUTION_HINTS,
    compute_scale_profile,
    recommend_plot_bases,
)
from nw.scene_messages import draft_messages
from nw.story_state import adopt_story
from nw.studio import catalog
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.studio.server import create_studio_server
from nw.studio.wizard_setup import setup_profile_for_types
from nw.world_specs import WORLD_BASES, WORLD_MECHANISM_EXECUTION_HINTS, recommend_world_bases
from story_fixture import baseline, draft_for
from test_selection import add_card


def test_all_35_genres_recommend_complete_world_cast_and_plot_bases():
    all_main = [g['id'] for g in catalog.genres()]
    assert len(all_main) == 35
    for gid in all_main:
        w_ranked = recommend_world_bases([gid])
        c_ranked = recommend_cast_bases([gid])
        p_ranked = recommend_plot_bases([gid])
        assert len(w_ranked) == len(WORLD_BASES) == 7
        assert len(c_ranked) == len(CAST_BASES) == 7
        assert len(p_ranked) == len(PLOT_BASES) == 8
        for top in (w_ranked[0], c_ranked[0], p_ranked[0]):
            assert len(top['dimensions']) == 6 and all(top['dimensions'].values())
            assert len(top['anti_drift_redlines']) >= 3
            assert len(top['micro_contrasts']) == 3
            for mc in top['micro_contrasts']:
                assert mc['bad_ai'] and mc['target_craft'] and mc['why']
                assert mc['bad_ai'] != mc['target_craft']

    # Verify all 5 length tiers + auto compile distinct executable pacing scales
    labels = set()
    for tw in (*WORD_TIERS, None):
        for speed in ('fast_punchy', 'steady_wave', 'layered_build'):
            sc = compute_scale_profile(tw, pacing_speed=speed)
            assert sc['tier_label'] and sc['recommended_volumes'] and sc['chapter_weight_ratio']
            assert len(sc['small_climax_every_chapters']) == 2
            labels.add(sc['tier_label'])
    assert len(labels) == 6

    # Verify legacy structure & mechanism translation hints cover catalog items cleanly
    assert len(STRUCTURE_EXECUTION_HINTS) == 15
    assert len(PLOT_MECHANISM_EXECUTION_HINTS) == 23
    assert len(WORLD_MECHANISM_EXECUTION_HINTS) == 14
    assert len(CAST_MECHANISM_EXECUTION_HINTS) == 5


def test_targeted_decomp_all_4_tracks_auto_collect_isolated_craft_fingerprints(tmp_path):
    lib = LibraryService(tmp_path)
    ch1 = '山门青石阶在暴雨里发滑，外门杂役陆清河攥紧旧账册，灵气反噬灼痛经脉，却盯着执事沉声问：“这三百灵石的亏空，执事打算拿谁填？”'
    ch2 = '三日后执事设局借宗门戒律压人，陆清河亮出药童与牙人私下换丹的残契，反逼对方退步，却在赏赐令牌背面发现失踪师父的旧印。'
    full_text = f'书籍信息\n书名：太虚账录\n【简介】测试。\n\n第1章 暴雨旧账\n{ch1 * 3}\n\n第2章 残契反制\n{ch2 * 3}\n'
    book = lib.import_book({'title': '太虚账录', 'filename': 'taixu_zhang.txt', 'text': full_text})
    lib.review_book(book['id'], {'action': 'confirm', 'types': ['GENRE_XIANXIA'], 'grade': 'A'})

    call_count = {'n': 0}

    class MockFourTrackProvider:
        name = 'mock_real'

        def generate(self, messages, *, model='', params=None, **kwargs):
            call_count['n'] += 1
            user = json.loads(messages[-1]['content'])
            if 'source_text' in user:
                q = ch1[:55] if user['chapter_index'] == 1 else ch2[:55]
                return GenResult(
                    text=json.dumps({
                        'chapter_summary': f"第{user['chapter_index']}章推进",
                        'key_characters': [{'name': '陆清河', 'role': '主角', 'quote': q[:20]}],
                        'observations': [
                            {
                                'track': 'genre_world_rules',
                                'title': '灵气反噬与宗门账目双约束',
                                'what_happened': '超阶动用真气灼痛经脉且受戒律约束',
                                'function_effect': '逼主角靠规矩与账目破局而非无脑对轰',
                                'reusable_pattern': '把修行代价与宗门资源分配制度绑死在同场冲突里。',
                                'boundary': '适用于仙侠/玄幻阶层压迫题材，不适用于现代都市。',
                                'quotes': [q],
                            },
                            {
                                'track': 'character_conflict',
                                'title': '理性利害反派与配角独立暗线',
                                'what_happened': '执事为遮亏空施压，药童与牙人私下交易留下裂缝',
                                'function_effect': '反派不降智，配角暗线给主角提供借势支点',
                                'reusable_pattern': '为反派设计真实账目软肋，并安排两条不经主角的配角利益线。',
                                'boundary': '适用于宗门/权谋/悬疑，不适用于无厘头搞笑。',
                                'quotes': [q],
                            },
                            {
                                'track': 'opening_plot_hooks',
                                'title': '当场反制加赏赐物带新悬念',
                                'what_happened': '赢下退步后令牌背面现师父旧印',
                                'function_effect': '胜利成果落地同时自然长出下一章追读钩子',
                                'reusable_pattern': '先兑现眼前收益，再让战利品本身携带更深一层人物线索。',
                                'boundary': '适用于连载长篇，严禁硬截半句话断章。',
                                'quotes': [q],
                            },
                            {
                                'track': 'scene_prose_craft',
                                'title': '冷雨实景起手与利害反问收束',
                                'what_happened': '借石阶发滑与旧账册起手，短问句压场',
                                'function_effect': '克制古风下自带锋芒',
                                'reusable_pattern': '用冷硬物件和具体筹码问句替代抽象气氛旁白。',
                                'boundary': '适用于仙侠古风对峙，不适用于现代轻喜剧。',
                                'quotes': [q],
                            },
                        ],
                        'world_signals': {
                            'card_function': 'rule_limit',
                            'premise_law': '强催真气必灼经脉且留痕',
                            'scarcity_cost': '丹药与灵石受内堂额度垄断',
                            'institution_gate': '宗门戒律可借题压人也可反制',
                            'exposition_policy': '借亏空对峙自然带出规矩',
                            'quote': q,
                        },
                        'cast_signals': {
                            'card_function': 'antagonist_logic',
                            'protagonist_drive': '底层杂役借旧账求生破局',
                            'antagonist_logic': '执事护私账讲体面不亲自留把柄',
                            'relation_asymmetry': '强弱权力差下握有对方致命账目',
                            'supporting_roster': '药童与牙人私下换丹独立互动',
                            'quote': q,
                        },
                        'plot_signals': {
                            'plan_function': 'hook_aftermath',
                            'drive_loop': '栽赃压迫→查裂缝反制→新线索抬头',
                            'hook_contract': '赏赐物内侧旧印自然抛新钩',
                            'pacing_cadence': '首章压迫次章破局节奏紧凑',
                            'aftermath_carry': '退步成果真实改变地位并引出高阶对手',
                            'quote': q,
                        },
                        'voice_signals': {
                            'scene_function': 'confrontation',
                            'register': '半文半白凝练骨力',
                            'cadence': '静景舒缓问句骤收',
                            'dialogue_texture': '礼数下直指利害筹码',
                            'psychic_distance': '贴身克制不直喊情绪词',
                            'quote': q,
                        },
                    }, ensure_ascii=False),
                    finish_reason='complete', usage={}, request_id='m-ext', raw={},
                )
            return GenResult(
                text=json.dumps({
                    'book_overview': {
                        'central_question': '底层杂役如何在宗门亏空局中借势破局',
                        'mainline': '旧账反制逐步撬开内门秘案',
                        'character_arcs': '隐忍求生到主动控局',
                        'information_payoffs': '战利品自然引出下层线索',
                        'structure': '压迫起势与借势翻盘交替',
                    },
                    'methods': [{
                        'track': 'opening_plot_hooks',
                        'task': 'hook',
                        'title': '战利品带新线索章尾留钩法',
                        'obs_ids': ['O003'],
                        'applicability': ['长篇连载阶段破局收尾'],
                        'non_applicability': ['不适用于全书终章'],
                        'operation': '先完整兑现主角当场赢下的实利，再在战利品或赏赐细节中露出指向下一局的具体异常物证。',
                        'output_desc': 'reader_plan 标注收益兑现与新异常钩子',
                        'acceptance_check': '正文完整交付胜利成果并留下可追问具体异常',
                        'evidence_required': '正文引文同时体现成果落地与异常细节',
                    }],
                    'world_fingerprint': {
                        'title': '修行代价与宗门税账双锁指纹',
                        'base_id': 'WORLD_TRANSCENDENT_COST',
                        'target_functions': ['rule_limit', 'resource_cost'],
                        'dimensions': {'premise_law': '超阶施法留经脉反噬', 'scarcity_cost': '丹药额度受阶层垄断'},
                        'techniques': ['将能力物理反噬与宗门制度追责叠加在同一场抉择中'],
                        'drift_guards': ['严禁低阶越阶出手零代价且不被执法机构察觉'],
                    },
                    'cast_fingerprint': {
                        'title': '体面利害反派与独立暗线指纹',
                        'base_id': 'CAST_LONE_BREAKER',
                        'target_functions': ['antagonist_logic', 'supporting_relation'],
                        'dimensions': {'antagonist_logic': '反派靠制度体面压人绝不降智吼叫'},
                        'techniques': ['在反派阵营外围埋设不经主角的配角利益裂缝供借势'],
                        'drift_guards': ['严禁反派明知有账目把柄还主动自爆'],
                    },
                    'plot_pacing_fingerprint': {
                        'title': '实利落地接战利品异常钩指纹',
                        'base_id': 'PLOT_PRESSURE_BREAKTHROUGH',
                        'target_functions': ['golden_three', 'hook_aftermath'],
                        'dimensions': {'hook_contract': '兑现回报后借战利品细节抛新钩'},
                        'techniques': ['赢下筹码必改变下一章地位，并用赏赐物细节牵出高阶对手'],
                        'drift_guards': ['严禁刚赢成果下一段立刻被抢回清零'],
                    },
                    'voice_fingerprint': {
                        'title': '暴雨山门冷硬机锋语感指纹',
                        'base_voice_id': 'VOICE_CLASSICAL_EDGE',
                        'scene_functions': ['confrontation'],
                        'dimensions': {'register': '半文半白凝练骨力'},
                        'techniques': ['实景冷物起手加具体筹码短句反问'],
                        'drift_guards': ['严禁古风对峙塞现代网梗'],
                    },
                }, ensure_ascii=False),
                finish_reason='complete', usage={}, request_id='m-syn', raw={},
            )

    cfg = Config('openai_compat', 'http://localhost', 'mock-model', '', 300.0, {}, tmp_path, True, {})
    lib._corpus_runtime = lambda: (cfg, MockFourTrackProvider())
    job = lib.start_corpus_job(book['id'], {
        'kind': 'targeted',
        'options': {
            'extent': 'complete', 'note': '四轨测试', 'sample_mode': 'key_chapters',
            'sample_count': 2, 'auto_approve': True, 'max_calls': 10, 'max_input_chars': 32000,
        },
    })
    worker = lib._tasks.get(job['id'])
    if worker:
        worker.join(timeout=15)

    done = lib.get_corpus_job(book['id'], job['id'])
    assert done['status'] == 'completed', done.get('error')
    # Zero extra LLM calls: 2 chapters + 1 synthesis = 3 calls total!
    assert call_count['n'] == 3
    pub_fps = done['progress'].get('published_craft_fingerprints') or {}
    assert set(pub_fps.keys()) == {'world', 'cast', 'plot_pacing', 'voice'}
    for dom, info in pub_fps.items():
        assert 'GENRE_XIANXIA' in info['type_tags']
        assert 'GENRE_DUSHI' in info['excluded_types']

    # Setup profile exposes ALL 4 fingerprints + 100万字 pacing scale for GENRE_XIANXIA, blocks ALL 4 for GENRE_DUSHI!
    prof_xx = setup_profile_for_types(['GENRE_XIANXIA'], library=lib, target_words=1_000_000)
    assert prof_xx['craft_specs_setup']['plot_pacing']['scale_profile']['tier_label'] == '100 万字标准长篇档'
    for dom in ('world', 'cast', 'plot_pacing', 'voice'):
        assert len(prof_xx['craft_specs_setup'][dom]['available_fingerprints']) == 1

    prof_ds = setup_profile_for_types(['GENRE_DUSHI'], library=lib, target_words=300_000)
    assert prof_ds['craft_specs_setup']['plot_pacing']['scale_profile']['tier_label'] == '30 万字紧凑档'
    for dom in ('world', 'cast', 'plot_pacing', 'voice'):
        assert prof_ds['craft_specs_setup'][dom]['available_fingerprints'] == []

    # AI Auto freeze_wizard compiles all 4 specs with matching fingerprints!
    wiz = freeze_wizard({
        'design_mode': 'auto',
        'genre_ids': ['GENRE_XIANXIA'],
        'length_mode': 'tiered',
        'target_words': 1_000_000,
        'creative_workflow': True,
        'planning_hierarchy': True,
    }, lib)
    assert set(wiz['craft_specs'].keys()) == {'world', 'cast', 'plot_pacing', 'voice'}
    assert wiz['craft_specs']['plot_pacing']['scale_profile']['tier_label'] == '100 万字标准长篇档'
    for dom in ('world', 'cast', 'plot_pacing', 'voice'):
        assert pub_fps[dom]['id'] in wiz['craft_specs'][dom]['fingerprint_ids']


def test_step_scoped_injection_budgets_and_lightweight_15_writer_16_review(tmp_path):
    workspace = tmp_path / 'ws'
    cfg_path = tmp_path / 'studio.config.toml'
    cfg_path.write_text('[model]\nprovider="ollama"\nbase_url="http://127.0.0.1:11434"\nmodel="mock"\ntimeout=60\n', encoding='utf-8')
    service = StudioService(workspace, config_path=cfg_path)
    lib = LibraryService(workspace)
    prod = ProductionService(service, lib)
    ident = 'step-scoped-novel'
    proj_dir = 'novel-scoped'
    wiz = freeze_wizard({
        'design_mode': 'auto',
        'genre_ids': ['GENRE_XIANXIA'],
        'length_mode': 'tiered',
        'target_words': 500_000,
        'creative_workflow': True,
        'planning_hierarchy': True,
    }, lib)
    prod.db.add(ident, proj_dir, '问剑长阶', wiz)
    with prod.open_store({'project_dir': proj_dir}, create=True) as store:
        project = store.init_project('问剑长阶')
        prod.db.update(ident, project_id=project.id)
        for dom, sp in wiz['craft_specs'].items():
            save_craft_spec(store, dom, sp)

        specs = load_all_craft_specs(store)
        dir_summary = build_direction_specs_summary(specs)
        assert dir_summary and len(dir_summary) <= 300
        assert all(k in dir_summary for k in ('世界：', '人物：', '剧情节奏：', '语感：'))

        # Verify strict Step-Scoped Injection Matrix and hard char caps via governance()
        gov = governance(wiz, library=lib, store=store, scope='book')
        assert gov['world_design']['craft_spec']['domain'] == 'world'
        assert len(gov['world_design']['craft_spec']['prompt_block']) <= 900
        assert gov['action_design']['craft_spec']['domain'] == 'world'
        assert len(gov['action_design']['craft_spec']['prompt_block']) <= 260
        assert gov['character_design']['craft_spec']['domain'] == 'cast'
        assert len(gov['character_design']['craft_spec']['prompt_block']) <= 900
        assert gov['static_relations']['craft_spec']['domain'] == 'cast'
        assert len(gov['static_relations']['craft_spec']['prompt_block']) <= 400
        assert gov['plot_design']['craft_spec']['domain'] == 'plot_pacing'
        assert len(gov['plot_design']['craft_spec']['prompt_block']) <= 1100
        assert '50 万字中长篇档' in gov['plot_design']['craft_spec']['prompt_block']
        assert gov['event_design']['craft_spec']['domain'] == 'plot_pacing'
        assert len(gov['event_design']['craft_spec']['prompt_block']) <= 340
        assert gov['scene_design']['craft_spec']['domain'] == 'plot_pacing'
        assert len(gov['scene_design']['craft_spec']['prompt_block']) <= 340
        # Zero cross-domain leakage into wrong stages
        assert 'craft_spec' not in gov.get('type_selection', {})

        # Verify Step 15 Writer stays lightweight: ONLY voice-spec + compact 2-3 line scene-beat (<=150 chars), ZERO world/cast dumps!
        store.add_brief('宗门查账', '受限POV')
        ch = store.add_chapter(1, '雨夜山门')
        sc_card = add_card(store, 'sc1', 'scene', {
            'title': '雨夜试探对峙',
            'goal': '陆清河试探执事口风',
            'conflict': '执事拿门规压人',
            'pov': 'lu', 'characters': ['lu'], 'story_time': '1', 'visibility': 'public',
        })
        lu_card = add_card(store, 'lu', 'character', {'name': '陆清河', 'role': '主角', 'want': '查账', 'visibility': 'public'})
        d_sc = decide_card(store, sc_card, 'approved', 'ok')
        d_lu = decide_card(store, lu_card, 'approved', 'ok')
        adopt_story(store, baseline(card_refs=[
            {**asdict(sc_card), 'decision_id': d_sc.id},
            {**asdict(lu_card), 'decision_id': d_lu.id},
        ]), {})
        sc = store.add_scene(ch.id, 1, json.dumps({'story': {'scene_ref': {'card_id': 'sc1', 'version': 1}, 'story_order': 1}}))

        work = build_story_context(store, sc.id, StoryScope('main', 0, 1, {'card_id': 'sc1', 'version': 1}), 120000)
        sources = {item['source'] for item in work.package['items']}
        assert 'voice-spec' in sources
        assert 'scene-beat' in sources
        assert 'world-spec' not in sources and 'cast-spec' not in sources
        beat_item = next(item for item in work.package['items'] if item['source'] == 'scene-beat')
        beat_payload = json.loads(beat_item['text'])
        assert len(beat_payload['beat_hint']) <= 150
        assert '章尾落点' in beat_payload['beat_hint']

        # Verify Step 16 Review receives compact same-source redlines across pillars (<=450 chars guard)
        guard_text = build_review_craft_guards(work.package, specs=specs, max_chars=450)
        assert len(guard_text) <= 450
        assert '本书语感防漂移验收' in guard_text
        assert '剧情节奏防漂移' in guard_text
        rev_msgs, _ = draft_messages(
            work.package, 'review', draft_for(store, sc.id, '正文草稿'), None, None, '', (),
            genre_ids=['GENRE_XIANXIA'], craft_specs=specs,
        )
        assert '本书语感防漂移验收' in rev_msgs[0]['content']
        assert '剧情节奏防漂移' in rev_msgs[0]['content']


def test_http_craft_specs_endpoints_and_length_tier_auto_sync(tmp_path):
    workspace = tmp_path / 'ws'
    cfg_path = tmp_path / 'studio.config.toml'
    cfg_path.write_text('[model]\nprovider="ollama"\nbase_url="http://127.0.0.1:11434"\nmodel="mock"\ntimeout=60\n', encoding='utf-8')
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
        # 1. Wizard setup profile with target_words=300000 recommends GENRE_XUANYI 4 pillars + 30万字 scale!
        st, prof = call('GET', '/api/wizard/setup-profile?types=GENRE_XUANYI&target_words=300000')
        assert st == 200
        cs = prof['craft_specs_setup']
        assert cs['world']['recommended_base_id'] == 'WORLD_REALISTIC_INSTITUTION'
        assert cs['cast']['recommended_base_id'] == 'CAST_MYSTERY_SUSPECTS'
        assert cs['plot_pacing']['recommended_base_id'] == 'PLOT_CLUE_REVELATION'
        assert cs['voice']['recommended_base_id'] == 'VOICE_HARD_REALISM'
        assert cs['plot_pacing']['scale_profile']['tier_label'] == '30 万字紧凑档'

        # 2. KB craft fingerprints endpoint
        st, kb = call('GET', '/api/kb/craft-fingerprints?domain=plot_pacing&types=GENRE_XUANYI')
        assert st == 200
        assert kb['domain'] == 'plot_pacing'
        assert len(kb['setup']['plot_pacing']['bases']) == 8

        # 3. Seed a novel & test GET/POST craft-specs + length-tier auto-recompilation
        prod = server.production
        ident = 'http-four-pillar-novel'
        proj_dir = 'novel-4p'
        prod.db.add(ident, proj_dir, '旧案迷雾', {
            'title': '旧案迷雾', 'genre_ids': ['GENRE_XUANYI'],
            'length_mode': 'tiered', 'target_words': 300_000,
        })
        with prod.open_store({'project_dir': proj_dir}, create=True) as store:
            project = store.init_project('旧案迷雾')
            prod.db.update(ident, project_id=project.id)
            store.add_brief('旧案迷雾', '单POV')

        st, saved = call('POST', f'/api/novels/{ident}/craft-specs/plot_pacing', {
            'enabled': True,
            'base_id': 'PLOT_CLUE_REVELATION',
            'knobs': {'pacing_speed': 'fast_punchy', 'hook_style': 'reveal_twist', 'payoff_ratio': 'deep_foreshadow', 'plot_bans': ['no_fake_cliffhanger']},
            'custom_notes': '每三章必有新物证对撞。',
        })
        assert st == 200
        assert saved['specs']['plot_pacing']['scale_profile']['tier_label'] == '30 万字紧凑档'
        assert saved['specs']['plot_pacing']['custom_notes'] == '每三章必有新物证对撞。'

        st, saved_w = call('POST', f'/api/novels/{ident}/craft-specs/world', {
            'enabled': True, 'base_id': 'WORLD_REALISTIC_INSTITUTION',
        })
        assert st == 200 and saved_w['specs']['world']['enabled'] is True

        st, saved_c = call('POST', f'/api/novels/{ident}/craft-specs/cast', {
            'enabled': True, 'base_id': 'CAST_MYSTERY_SUSPECTS',
        })
        assert st == 200 and saved_c['specs']['cast']['enabled'] is True

        # Change target_words from 300k -> 2,000,000 via /length and verify plot_pacing_spec auto-syncs!
        st, _ = call('POST', f'/api/novels/{ident}/length', {'length_mode': 'tiered', 'target_words': 2_000_000})
        assert st == 200
        st, after = call('GET', f'/api/novels/{ident}/craft-specs')
        assert st == 200
        assert after['specs']['plot_pacing']['scale_profile']['tier_label'] == '200 万字超长篇档'

        # Quality view reports all 4 pillars cleanly
        st, q = call('GET', f'/api/novels/{ident}/quality')
        assert st == 200
        assert q['craft_specs']['world']['enabled'] is True
        assert q['craft_specs']['cast']['enabled'] is True
        assert q['craft_specs']['plot_pacing']['tier_label'] == '200 万字超长篇档'
    finally:
        server.shutdown()
        server.server_close()
