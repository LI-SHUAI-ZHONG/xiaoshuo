"""End-to-end verification for the 6 Dimensional Fusion Upgrades (P0 + P1 + P2).

Covers:
  - SQLite v12 migration & integrity
  - Fusion 1: 0-Token Pre-Review Script Gate (POV secret leak, AI cliches, typos, completeness, auto-rewrite)
  - Fusion 2: Living Craft Evolution (Author-edit Diff contrast harvester, 3-rejection rule promotion, style drift)
  - Fusion 3: Serial Health Cockpit (Base-compiled Strand Weave, Promise Rhythm Debt, hook fatigue, Signal-vs-Spoiler, volume foreshadowing)
  - Fusion 4: POV-Safe Tiered Long-Term Memory Orchestrator, Replay Cache & Volume Summaries
  - Fusion 5: 0-Token 5-Section Natural-Language Briefing Compiler + 4-Lens Unified Review View
  - Fusion 6: Author Shell Error Catalog, Explicit Soft-Override Ledger (with Hard Invariants), Project Doctor & Studio APIs
  - Reference Deconstruction Track 3: conditional_framework, do_not_copy, differentiation_hint & golden_three_metrics
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import urllib.error
import urllib.request

import pytest

from nw.cards import decide_card, save_card
from nw.context.briefing_compiler import compile_writer_briefing, should_use_natural_briefing
from nw.context.memory_orchestrator import (
    cached_replay_facts,
    clear_replay_cache,
    draft_volume_summary_from_chapters,
    orchestrate_scene_memory,
    rank_pov_facts,
    save_volume_summary,
)
from nw.context.story import StoryScope, build_story_context
from nw.craft_evolution import (
    accept_learned_contrast,
    check_style_drift,
    detect_author_edit_candidates,
    extract_author_edit_contrasts,
    list_promotion_proposals,
    pin_style_baseline,
    promote_pattern_to_craft_spec,
)
from nw.craft_specs import compile_craft_spec, save_craft_spec
from nw.craft_specs_base import save_craft_fingerprint
from nw.llm.base import GenResult
from nw.override_ledger import is_overridable_code, list_overrides, record_override, revoke_override
from nw.pre_review_gate import compute_prose_stats, format_pre_review_rewrite_feedback, run_pre_review_gate
from nw.project_doctor import run_project_doctor
from nw.schema import VERSION
from nw.serial_health import (
    SIGNAL_VS_SPOILER_GUIDE,
    build_foreshadowing_opportunity_brief,
    build_serial_health_board,
    record_chapter_telemetry,
    strand_profile_for_spec,
)
from nw.store import Store, now
from nw.story_state import adopt_story, apply_settings, current_head
from nw.studio.author_shell import build_unified_review_view, translate_error
from nw.voice_specs import build_writer_voice_packet, compile_book_voice_spec, save_book_voice_spec


def _add_and_approve(store: Store, card_id: str, kind: str, body: dict):
    ref = save_card(store, {'card_id': card_id, 'kind': kind, 'origin': 'author', 'body': body, 'source_refs': []}, None)
    dec = decide_card(store, ref, 'approved', 'ok')
    return ref, dec.id


def _setup_managed_project(tmp_path: Path):
    """Create a managed project with POV character, hidden secret character, world card, promise card, and 2 scenes."""
    store = Store(tmp_path / 'book1', create=True, test_mode=True)
    store.init_project('测试长篇')
    store.add_brief('主角沈砚在旧城查案。', '禁止机械降神')
    ch1 = store.add_chapter(1, '雨夜查账')
    ch2 = store.add_chapter(2, '港口暗线')

    _, d_pov = _add_and_approve(store, 'char_shen', 'character', {
        'name': '沈砚', 'role': '主角/账房查验员', 'want': '查明盐引失踪真相',
        'voice': '冷静克制、短句追问', 'visibility': 'public',
    })
    _, d_hidden = _add_and_approve(store, 'char_mole', 'character', {
        'name': '夜枭尊者', 'role': '幕后黑手', 'want': '掌控潮汐旧城私盐通道',
        'visibility': 'holders', 'holders': ['char_other'],
    })
    _, d_world = _add_and_approve(store, 'world_main', 'world', {
        'title': '潮汐旧城', 'rule': '入夜后不得私闯盐库', 'limits': '违者当场缉拿问罪', 'visibility': 'public',
    })
    _, d_prom = _add_and_approve(store, 'prom_ledger', 'promise', {
        'title': '失踪盐引印鉴之谜', 'setup': '盐账缺了三页', 'payoff': '查清私盐真正买家', 'visibility': 'public',
    })
    _, d_sc1 = _add_and_approve(store, 'sc_card_1', 'scene', {
        'title': '账房对峙', 'pov': 'char_shen', 'characters': ['char_shen'],
        'location': '盐务旧库', 'goal': '逼问管事交出账本', 'conflict': '管事拒不认账',
        'allowed_disclosure': '仅披露账本缺页', 'story_time': '1', 'visibility': 'public',
    })
    _, d_sc2 = _add_and_approve(store, 'sc_card_2', 'scene', {
        'title': '港口追踪', 'pov': 'char_shen', 'characters': ['char_shen'],
        'location': '旧港栈桥', 'goal': '顺着缺页编号查到货船', 'conflict': '大雾封港',
        'allowed_disclosure': '发现半枚旧印', 'story_time': '2', 'visibility': 'public',
    })

    sc1 = store.add_scene(ch1.id, 1, json.dumps({
        'title': '账房对峙', 'pov': 'char_shen',
        'story': {'scene_ref': {'card_id': 'sc_card_1', 'version': 1}, 'story_order': 1},
    }, ensure_ascii=False))
    sc2 = store.add_scene(ch2.id, 1, json.dumps({
        'title': '港口追踪', 'pov': 'char_shen',
        'story': {'scene_ref': {'card_id': 'sc_card_2', 'version': 1}, 'story_order': 2},
    }, ensure_ascii=False))

    adopt_story(store, {
        'as_of_story_order': 0,
        'disclosure_order': [0, 0, 0],
        'coverage': {'entities': ['char_shen', 'char_mole', 'prom_ledger'], 'predicates': ['location', 'promise_stage', 'identity_status:secret']},
        'facts': [
            {
                'entity_id': 'char_shen', 'predicate': 'location', 'holder': 'char_shen',
                'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0], 'value': '盐务旧库',
            },
            {
                'entity_id': 'char_mole', 'predicate': 'identity_status:secret', 'holder': 'WORLD',
                'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0],
                'value': {'identity': '黑市头目', 'permissions': ['调动私船'], 'social_expectations': ['隐藏行踪']},
            },
            {
                'entity_id': 'prom_ledger', 'predicate': 'promise_stage', 'holder': 'WORLD',
                'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0], 'value': 'planted',
            },
        ],
        'card_refs': [
            {'card_id': 'char_shen', 'version': 1, 'decision_id': d_pov},
            {'card_id': 'char_mole', 'version': 1, 'decision_id': d_hidden},
            {'card_id': 'world_main', 'version': 1, 'decision_id': d_world},
            {'card_id': 'prom_ledger', 'version': 1, 'decision_id': d_prom},
            {'card_id': 'sc_card_1', 'version': 1, 'decision_id': d_sc1},
            {'card_id': 'sc_card_2', 'version': 1, 'decision_id': d_sc2},
        ],
    }, {})
    return store, ch1, ch2, sc1, sc2


def test_schema_v12_tables_and_integrity(tmp_path: Path) -> None:
    with Store(tmp_path / 'fresh', create=True, test_mode=True) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == VERSION
        assert VERSION >= 12
        tables = {
            r[0] for r in store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for needed in ('override_ledger', 'serial_chapter_metrics', 'volume_summaries',
                       'state_replay_cache', 'style_drift_snapshots'):
            assert needed in tables
        assert [r[0] for r in store.connection.execute('PRAGMA integrity_check')] == ['ok']


def test_fusion1_pre_review_gate_pov_leak_cliche_and_typo(tmp_path: Path) -> None:
    store, _, _, sc1, _ = _setup_managed_project(tmp_path)
    try:
        vspec = compile_book_voice_spec(['GENRE_XIANXIA'], base_voice_id='VOICE_CLASSICAL_EDGE', enabled=True)
        save_book_voice_spec(store, vspec)

        # 1) Hard completeness + modern slang + POV secret leak + canonical name typo + AI cliches
        bad_text = (
            '沈研道：“这破事真是yyds，[待补地名]那边查不出名堂。”\n'
            '他嘴角勾起一抹冷笑，瞳孔骤然一缩，一股寒意顺着脊背爬上，空气瞬间凝固，内心掀起了惊涛骇浪。\n'
            '沈砚心想，幕后的夜枭尊者和黑市头目恐怕早已逃走，'
        )
        rep = run_pre_review_gate(store, sc1.id, bad_text, branch='main')
        codes = {row['code'] for row in rep['issues']}
        assert rep['passed'] is False
        assert rep['action'] == 'auto_rewrite'
        assert 'PRE_PLACEHOLDER_BRACKET_TODO' in codes
        assert 'PRE_BROKEN_TAIL' in codes
        assert 'PRE_AI_CLICHE_OVERLOAD' in codes
        assert 'PRE_MODERN_SLANG_BAN' in codes
        assert 'PRE_POV_SECRET_LEAK' in codes
        assert 'PRE_ENTITY_SPELLING_DRIFT' in codes
        # POV secret leak MUST NOT be marked overridable!
        pov_issues = [row for row in rep['issues'] if row['code'] == 'PRE_POV_SECRET_LEAK']
        assert all(not row['overridable'] for row in pov_issues)
        assert '【0-Token 写后机检线索' in rep['review_handoff_note']
        assert '必须修正的硬问题' in format_pre_review_rewrite_feedback(rep)

        # 2) Clean prose passes cleanly with 0 hard issues
        clean_text = (
            '灯影在潮湿的木桌上晃了一下。沈砚把那本缺了三页的盐账往前推了半寸，声音平稳：“管事，腊月那批货的印鉴去哪儿了？”\n'
            '管事手里的茶杯一歪，褐色的茶水泼在袖口上，却愣是没敢伸手去擦。'
        )
        ok_rep = run_pre_review_gate(store, sc1.id, clean_text, branch='main')
        assert ok_rep['passed'] is True
        assert ok_rep['action'] == 'pass'
        assert ok_rep['hard_count'] == 0
    finally:
        store.connection.close()


def test_fusion5_natural_briefing_compiler_and_author_contrast_priority(tmp_path: Path) -> None:
    store, _, _, sc1, _ = _setup_managed_project(tmp_path)
    try:
        vspec = compile_book_voice_spec(['GENRE_XUANYI'], base_voice_id='VOICE_HARD_REALISM', enabled=True)
        save_book_voice_spec(store, vspec)
        # Add an author-edited learned contrast for confrontation
        accept_learned_contrast(store, {
            'scene_function': 'confrontation',
            'label': '作者亲改示范 · 账房对峙',
            'bad_ai': '他冷笑一声说道，你最好老实交代。',
            'target_voice': '沈砚把墨笔搁在砚台沿上，抬头看他：“你打算什么时候把缺的那三页交出来？”',
            'why': '用具体动作替代冷笑套话。',
            'chapter_index': 1,
        })
        reloaded = store.data_file('voice_spec.json')
        assert reloaded.is_file()
        vpack = build_writer_voice_packet(json.loads(reloaded.read_text(encoding='utf-8')), scene_function='confrontation')
        assert vpack['micro_contrasts'][0]['source'] == 'author_edit'
        assert '沈砚把墨笔搁在砚台沿上' in vpack['micro_contrasts'][0]['target_voice']

        # Save a volume summary so L2 episodic memory flows into briefing
        save_volume_summary(
            store, branch_id='main', volume_index=1, title='旧城迷案',
            chapter_start=1, chapter_end=1, summary_text='第一卷查清盐库缺页指向旧港走私链。',
        )
        scope = StoryScope('main', current_head(store, 'main').revision, 2, {'card_id': 'sc_card_2', 'version': 1})
        # Use sc2 (chapter 2) so volume summary (ch 1) strictly precedes ch 2!
        sc2 = [s for s in store.list('scene') if s.id != sc1.id][0]
        work = build_story_context(store, sc2.id, scope, 40000)
        briefing = compile_writer_briefing(work.package)

        assert '## 一、本场硬约束与眼前处境' in briefing
        assert '## 二、此人此刻所知与认知边界' in briefing
        assert '## 三、本场出场人物与世界规则' in briefing
        assert '## 四、本书语感规范与本场微对照' in briefing
        assert '## 五、前文紧邻承接与近期脉络' in briefing
        assert '作者亲改示范' in briefing
        assert '旧城迷案' in briefing
        # Zero internal machine keys leaked into writer prose briefing
        for raw_key in ('"card_id"', '"disclosure_order"', '"sha256"', '"decision_id"'):
            assert raw_key not in briefing
        assert should_use_natural_briefing('openai') is True
        assert should_use_natural_briefing('fake') is False
    finally:
        store.connection.close()


def test_fusion6_author_shell_override_ledger_and_3sec_review_view(tmp_path: Path) -> None:
    store, _, _, sc1, _ = _setup_managed_project(tmp_path)
    try:
        err = translate_error('STALE_HEAD: branch moved')
        assert err['code'] == 'STALE_HEAD'
        assert '刷新' in err['action_label']
        assert err['technical_detail'] == 'STALE_HEAD: branch moved'

        # Hard invariants MUST NEVER be overridable
        assert not is_overridable_code('HARD_FACT_FINDINGS')
        assert not is_overridable_code('PRE_POV_SECRET_LEAK')
        assert not is_overridable_code('PRE_PLACEHOLDER_BRACKET_TODO')
        with pytest.raises(ValueError, match='HARD_INVARIANT'):
            record_override(
                store, branch_id='main', constraint_kind='hard',
                constraint_code='PRE_POV_SECRET_LEAK', reason_tag='EDITORIAL_INTENT', reason_text='强行放行',
            )

        # Soft constraint override succeeds and clears warning from 3-second Author Review View
        pre_rep = {
            'issues': [
                {'code': 'PRE_PARAGRAPH_WALL', 'severity': 'warning', 'overridable': True,
                 'message': '存在超长段落墙', 'quote': '', 'fix_hint': '拆分段落'},
            ],
        }
        cold_rep = {
            'latest_for_draft': {
                'parsed': {
                    'verdict_summary': '开篇节奏略慢，但悬念立住了。',
                    'keep_reading': {'want_next': 'yes'},
                    'skip_zones': [{'location': '第2段', 'reason': '铺垫稍长', 'quote': '雨一直下'}],
                    'confusion_or_mismatch': [],
                },
            },
        }
        before_view = build_unified_review_view(pre_review=pre_rep, cold_read=cold_rep, overrides=[])
        assert before_view['status'] == 'suggest_fix'
        assert before_view['verdict'] == '⚠️ 建议改'
        assert before_view['lenses']['reader_lens']['want_next'] == 'yes'

        ovr = record_override(
            store, branch_id='main', scene_id=sc1.id, chapter_index=1,
            constraint_kind='voice_soft', constraint_code='PRE_PARAGRAPH_WALL',
            reason_tag='TRANSITIONAL_SETUP', reason_text='本段为连续心理长镜头，刻意不分段。',
        )
        after_view = build_unified_review_view(
            pre_review=pre_rep, cold_read=cold_rep,
            overrides=list_overrides(store, branch_id='main', scene_id=sc1.id),
        )
        assert after_view['status'] == 'can_continue'
        assert after_view['verdict'] == '✅ 可以继续'
        assert after_view['overridden_count'] == 1

        # Cold read alone NEVER triggers must_fix / blocking!
        cold_bad = {
            'latest_for_draft': {
                'parsed': {
                    'verdict_summary': '有点平淡',
                    'keep_reading': {'want_next': 'no'},
                    'skip_zones': [{'location': '第1段', 'reason': '太拖沓', 'quote': '...'}],
                    'confusion_or_mismatch': [],
                },
            },
        }
        cr_only = build_unified_review_view(cold_read=cold_bad)
        assert cr_only['status'] == 'can_continue'
        assert cr_only['hard_count'] == 0

        # Revoke works cleanly
        revoke_override(store, ovr['id'])
        assert len(list_overrides(store, branch_id='main', scene_id=sc1.id, status='active')) == 0
    finally:
        store.connection.close()


def test_fusion2_living_craft_evolution_diff_harvest_promotion_and_drift(tmp_path: Path) -> None:
    store, ch1, ch2, sc1, sc2 = _setup_managed_project(tmp_path)
    try:
        # 1) Author-edit Diff Contrast Harvester
        ai_prose = (
            '林青听到管事的辩解后微微眯起眼睛，心中暗想此人必定有问题，嘴角勾起一抹冷笑说道：“你最好老实交代，否则后果自负。”'
        )
        author_prose = (
            '林青听完管事的辩解，把缺页账本往桌上一扣，抬头盯着他袖口沾的红泥：“你最好老实交代，这印泥是哪间库房的？”'
        )
        cands = extract_author_edit_contrasts(ai_prose, author_prose, scene_function='confrontation', chapter_index=1)
        assert len(cands) == 1
        assert 0.25 <= cands[0]['change_ratio'] <= 0.72
        assert '冷笑' in cands[0]['bad_ai']
        assert '红泥' in cands[0]['target_voice']

        # Tiny 1-char typo edit is ignored (not noisy)
        tiny = extract_author_edit_contrasts(author_prose, author_prose.replace('红泥', '朱泥'))
        assert tiny == []

        # 2) Recurring 3x override/rejection -> promotion into craft spec redline
        for ch_i in (1, 2, 3):
            record_override(
                store, branch_id='main', chapter_index=ch_i,
                constraint_kind='review_rejection', constraint_code='VOICE_STYLE_DRIFT',
                reason_tag='REJECTION_PATTERN', reason_text='配角台词过于书面且爱替主角解释局势',
            )
        proposals = list_promotion_proposals(store, branch='main', min_count=3)
        assert len(proposals) == 1
        assert proposals[0]['count'] == 3
        assert proposals[0]['target_domain'] == 'voice'

        promo = promote_pattern_to_craft_spec(
            store,
            target_domain=proposals[0]['target_domain'],
            redline_text=proposals[0]['proposed_redline'],
            override_ids=proposals[0]['override_ids'],
            chapters=proposals[0]['chapters'],
            pattern_key=proposals[0]['pattern_key'],
        )
        assert promo['overrides_marked_promoted'] == 3
        assert list_promotion_proposals(store, branch='main', min_count=3) == []
        vspec = json.loads(store.data_file('voice_spec.json').read_text(encoding='utf-8'))
        assert any('配角台词过于书面' in r for r in vspec['drift_redlines'])

        # 3) Style Drift Monitor (accept ch1 concise dialogue prose vs ch2 long narration prose)
        from nw.models import Run
        r1 = store.add_run(Run('r1', sc1.id, 'write', 'fake', 'm', '{}', '{}', '{}', '', 'complete', '{}', now(), now()))
        d1 = store.add_draft(sc1.id, '“走吗？”\n“走。”\n“去哪？”\n“港口。”\n“带刀了？”\n“带着。”\n他转身出门。', 'complete', r1.id)
        r2 = store.add_run(Run('r2', sc2.id, 'write', 'fake', 'm', '{}', '{}', '{}', '', 'complete', '{}', now(), now()))
        d2 = store.add_draft(
            sc2.id,
            '潮湿的海风夹杂着咸涩的盐雾与陈年渔船腐朽木板的复杂气味，缓缓吹过整个寂静无声、笼罩在浓厚灰雾里的旧港长街，'
            '沈砚独自一人沿着湿滑不堪的青石板路缓慢前行，仔细回忆着从三天前开始陆续浮出水面的所有账目疑点与人物关联。' * 3,
            'complete', r2.id,
        )
        # Attach accepted slots directly on branch revision for drift test
        snap = json.loads(store.connection.execute(
            "SELECT state_json FROM story_commits WHERE branch_id='main' ORDER BY revision DESC LIMIT 1"
        ).fetchone()[0])
        snap['slots'] = {
            sc1.id: {'draft_id': d1.id, 'delta_id': None},
            sc2.id: {'draft_id': d2.id, 'delta_id': None},
        }
        store.connection.execute(
            "INSERT INTO story_commits VALUES ('c_drift','main',1,0,'h',?,?)",
            (json.dumps(snap, ensure_ascii=False), now()),
        )
        store.connection.execute("UPDATE story_branches SET head_revision=1 WHERE id='main'")
        store.connection.commit()

        pin_style_baseline(store, branch='main', start_chapter=1, end_chapter=1)
        drift = check_style_drift(store, branch='main', window_size=1, drift_threshold=0.25)
        assert drift['status'] == 'drift_detected'
        assert any(d['metric'] == 'avg_sentence_len' for d in drift['drifts'])
    finally:
        store.connection.close()


def test_fusion3_serial_health_strand_debt_and_volume_foreshadowing(tmp_path: Path) -> None:
    from nw.plot_pacing_specs import PLOT_BASES
    from nw.serial_health import STRAND_PROFILES_BY_PLOT_BASE
    assert {b['id'] for b in PLOT_BASES} == set(STRAND_PROFILES_BY_PLOT_BASE.keys())

    store, _, _, _, _ = _setup_managed_project(tmp_path)
    try:
        # Base-compiled Strand differs properly across genres!
        rom_spec = compile_craft_spec('plot_pacing', ['GENRE_YANQING'], base_id='PLOT_EMOTION_ESCALATION', target_words=300000)
        xuan_spec = compile_craft_spec('plot_pacing', ['GENRE_XUANHUAN'], base_id='PLOT_PRESSURE_BREAKTHROUGH', target_words=2000000)
        rom_strand = strand_profile_for_spec(rom_spec, target_words=300000)
        xuan_strand = strand_profile_for_spec(xuan_spec, target_words=2000000)
        assert rom_strand['target_ratio']['fire'] == 0.50
        assert rom_strand['max_fire_gap'] <= 3
        assert xuan_strand['target_ratio']['quest'] == 0.65
        assert xuan_strand['promise_stall_limit'] > rom_strand['promise_stall_limit']

        save_craft_spec(store, 'plot_pacing', xuan_spec)
        # Simulate 5 consecutive Quest chapters with weak identical hooks
        for ch_i in range(1, 6):
            record_chapter_telemetry(
                store, branch_id='main', chapter_index=ch_i,
                dominant_strand='quest', hook_type='crisis', hook_strength='weak',
                micro_payoff_count=1, promise_touched=False,
            )
        board = build_serial_health_board(store, branch='main', plot_spec=xuan_spec, target_words=2000000)
        assert board['status'] in ('watch', 'alert')
        assert board['strand_health']['quest_streak'] == 5
        assert board['hook_health']['weak_streak'] == 5
        assert board['hook_health']['dominant_hook'] == 'crisis'
        assert any('纯主线' in c for c in board['next_chapter_corrections'])
        assert any('弱钩' in c for c in board['next_chapter_corrections'])
        assert any('同类钩子' in c for c in board['next_chapter_corrections'])
        assert SIGNAL_VS_SPOILER_GUIDE == board['signal_vs_spoiler_guide']

        # Add a future volume card and verify foreshadowing opportunity scanner picks it up
        _, d_vol = _add_and_approve(store, 'vol_3', 'volume', {
            'title': '第三卷·盐海决战', 'goal': '彻底端掉跨海私盐走私网', 'turn': '幕后黑手夺取跨海盐路控制权', 'visibility': 'public',
        })
        apply_settings(store, current_head(store, 'main'), [d_vol], 'commit_vol3')
        opp = build_foreshadowing_opportunity_brief(store, branch='main')
        assert opp['ready'] is True
        assert any('盐海决战' in a['title'] for a in opp['future_anchors'])
        assert '卷级远期伏笔机会扫描' in opp['prompt_hint']
    finally:
        store.connection.close()


def test_fusion4_tiered_memory_orchestrator_replay_cache_and_2m_word_ranking(tmp_path: Path) -> None:
    store, _, _, _, sc2 = _setup_managed_project(tmp_path)
    try:
        head = current_head(store, 'main')
        facts1, hit1 = cached_replay_facts(store, 'main', head.revision, 1, 'char_shen', (1, 1, 0))
        facts2, hit2 = cached_replay_facts(store, 'main', head.revision, 1, 'char_shen', (1, 1, 0))
        assert hit1 is False
        assert hit2 is True
        assert [f.predicate for f in facts1] == [f.predicate for f in facts2]
        assert clear_replay_cache(store) >= 1

        # Simulate 120 POV-visible facts across 120 chapters -> verify Top-40 ranking pins active entities & drops ancient noise
        synthetic_facts = [
            {
                'entity_id': f'npc_{i}', 'predicate': 'minor_note', 'holder': 'char_shen',
                'claim': 'fact', 'story_order': i, 'disclosure_order': [i, 1, 0], 'value': f'远期路人琐事{i}',
            }
            for i in range(1, 115)
        ]
        # Add pinned active scene entity & active promise from Chapter 2 (ancient chapter, MUST still survive!)
        synthetic_facts.append({
            'entity_id': 'char_shen', 'predicate': 'injury', 'holder': 'char_shen',
            'claim': 'fact', 'story_order': 2, 'disclosure_order': [2, 1, 0], 'value': '左腕旧伤未愈',
        })
        synthetic_facts.append({
            'entity_id': 'prom_ledger', 'predicate': 'promise_stage', 'holder': 'char_shen',
            'claim': 'fact', 'story_order': 3, 'disclosure_order': [3, 1, 0], 'value': 'planted',
        })
        selected, omitted = rank_pov_facts(
            synthetic_facts,
            current_chapter=120,
            pov_holder='char_shen',
            scene_body={'characters': ['char_shen'], 'goal': '查验港口货单'},
            active_promise_ids=('prom_ledger',),
            max_facts=40,
        )
        assert len(selected) == 40
        assert omitted == len(synthetic_facts) - 40
        selected_ids = {(f['entity_id'], f['predicate']) for f in selected}
        assert ('char_shen', 'injury') in selected_ids
        assert ('prom_ledger', 'promise_stage') in selected_ids
        # Recent chapter 114 beats ancient chapter 1
        assert ('npc_114', 'minor_note') in selected_ids
        assert ('npc_1', 'minor_note') not in selected_ids

        # Volume summaries integrate into orchestrate_scene_memory strictly before current_chapter
        save_volume_summary(store, branch_id='main', volume_index=1, title='第一卷', chapter_start=1, chapter_end=30, summary_text='卷一完结摘要。')
        save_volume_summary(store, branch_id='main', volume_index=2, title='第二卷', chapter_start=31, chapter_end=60, summary_text='卷二完结摘要。')
        pack = orchestrate_scene_memory(
            store, branch_id='main', current_chapter=45, pov_holder='char_shen',
            scene_body={'characters': ['char_shen']}, pov_facts=synthetic_facts,
            active_promise_ids=('prom_ledger',), max_semantic_facts=40,
        )
        assert len(pack['volume_summaries']) == 1  # only Vol 1 (< ch 45), NOT future Vol 2!
        assert pack['volume_summaries'][0]['volume_index'] == 1
        assert pack['omitted_distant_facts_count'] == omitted
    finally:
        store.connection.close()


def test_deconstruction_anti_contamination_and_project_doctor(tmp_path: Path) -> None:
    # 1) Deconstruction fingerprint preserves conditional_framework + do_not_copy + differentiation_hint + golden_three_metrics
    db = sqlite3.connect(tmp_path / 'lib.db')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE staging_books(id TEXT PRIMARY KEY, title TEXT, status TEXT)')
    db.execute("INSERT INTO staging_books VALUES ('b1', '示例参考书', 'archived')")
    fp = save_craft_fingerprint(
        db,
        domain='plot_pacing',
        book_id='b1',
        structure_version=1,
        title='压迫倒计时破局指纹',
        base_id='PLOT_PRESSURE_BREAKTHROUGH',
        type_tags=['GENRE_XUANHUAN'],
        body={
            'dimensions': {'drive_loop': '倒计时压迫+借规则反杀'},
            'techniques': ['前三章用死线倒计时绑定切身危局'],
            'drift_guards': ['避免开篇说明书式背景介绍'],
            'conditional_framework': '低位处境 + 公开规则漏洞 + 可量化筹码差 -> 当场翻盘爽感',
            'do_not_copy': ['废丹炉吸灵残骨', '三年之约退婚桥段'],
            'differentiation_hint': '新书请替换势力舞台与代价机制，不可照搬退婚或宗门大比模板。',
            'golden_three_metrics': '第1章前400字抛出倒计时危局，铺放比3:4，反应层2层。',
        },
    )
    assert fp['body']['conditional_framework'].startswith('低位处境')
    assert '废丹炉吸灵残骨' in fp['body']['do_not_copy']
    assert '新书请替换' in fp['body']['differentiation_hint']
    assert '400字' in fp['body']['golden_three_metrics']
    db.close()

    # 2) Project Doctor runs all 8 diagnostic checks & safe cache rebuild
    store, _, _, _, _ = _setup_managed_project(tmp_path)
    try:
        doc = run_project_doctor(store, branch='main', repair_cache=True)
        assert doc['overall_status'] in ('healthy', 'attention', 'blocked')
        assert len(doc['checks']) == 8
        ids = {c['id'] for c in doc['checks']}
        assert {'db_integrity', 'branch_health', 'jobs_health', 'chapter_summaries',
                'serial_rhythm', 'style_drift', 'evolution_proposals', 'craft_specs'} <= ids
        assert doc['stats']['schema_version'] == VERSION
    finally:
        store.connection.close()


def test_studio_http_fusion_apis_and_author_shell_errors(tmp_path: Path) -> None:
    from nw.studio.api import StudioService
    from nw.studio.server import create_studio_server
    import threading

    ws = tmp_path / 'ws'
    ws.mkdir()
    svc = StudioService(workspace=ws)
    server = create_studio_server(svc, host='127.0.0.1', port=0)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f'http://127.0.0.1:{port}/api'

    def _req(method: str, path: str, body: dict | None = None):
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        headers = {'Content-Type': 'application/json'} if body is not None else {}
        req = urllib.request.Request(base + path, data=raw, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    try:
        # Create a minimal book in production DB
        st, created = _req('POST', '/novels', {
            'title': '融合测试书',
            'idea': '一名账房小吏在潮汐旧城追查失踪盐引的故事。',
            'genre_ids': ['GENRE_XUANYI'],
            'target_words': 500000,
        })
        assert st == 201
        nid = created['novel']['id']

        st, health = _req('GET', f'/novels/{nid}/serial-health')
        assert st == 200 and 'board' in health and 'volume_summaries' in health

        st, vs = _req('POST', f'/novels/{nid}/volume-summaries', {
            'volume_index': 1, 'title': '初探旧城', 'chapter_start': 1, 'chapter_end': 10,
            'summary_text': '卷一查出旧港走私暗线。',
        })
        assert st == 200 and vs['saved']['volume_index'] == 1

        # Hard invariant override returns 400 WITH Author Shell `author_error`!
        st, err_body = _req('POST', f'/novels/{nid}/overrides', {
            'constraint_code': 'HARD_FACT_FINDINGS',
            'reason_tag': 'EDITORIAL_INTENT',
            'reason_text': '试图强行跳过硬冲突',
        })
        assert st == 400
        assert 'HARD_INVARIANT' in err_body['error']
        assert isinstance(err_body.get('author_error'), dict)
        assert err_body['author_error']['title']

        # Soft override succeeds
        st, ovr = _req('POST', f'/novels/{nid}/overrides', {
            'constraint_code': 'PRE_PARAGRAPH_WALL',
            'reason_tag': 'TRANSITIONAL_SETUP',
            'reason_text': '长段氛围铺陈',
        })
        assert st == 200 and ovr['override']['status'] == 'active'

        st, evo = _req('GET', f'/novels/{nid}/craft-evolution')
        assert st == 200 and 'style_drift' in evo and 'promotion_proposals' in evo

        st, doc = _req('GET', f'/novels/{nid}/doctor?repair_cache=1')
        assert st == 200 and doc['score'] >= 0 and len(doc['checks']) >= 7

        st, q = _req('GET', f'/novels/{nid}/quality')
        assert st == 200 and 'craft_specs' in q
    finally:
        server.shutdown()
        server.server_close()
