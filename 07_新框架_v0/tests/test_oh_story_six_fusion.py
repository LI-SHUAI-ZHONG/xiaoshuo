"""Comprehensive tests for Round 3 Six Dimensional Fusions (oh-story-claudecode):
  - Schema v14 (`book_author_memory`) & Library DB tables (`global_author_memory`, `verified_corpus_excerpts`)
  - Fusion G: 0-Token Outline-Copy Guard with surgical verbatim anchor excision
  - Fusion H: Degeneration Guard + Fixed-Point Punctuation Normalizer + Book-Local Style Whitelist
  - Fusion I: 150k-Chapter Empirical Calibration, 3-Tier Severity, & Prose Balance Drift
  - Fusion J: Two-Level Cross-Book Author Memory (`AP`/`BP`) + Exact 2KB Writer-Line Budget + Omission Notice
  - Fusion K: Machine-Verified Anonymized Real-Corpus Excerpts (3-check zero-alert admission)
  - Fusion L: Platform Publish Preflight + Whole-Book Sweep + Scene-vs-Summary + Position-Swapped Blind A/B Judge
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from nw.ab_judge import evaluate_scene_vs_summary, run_position_swapped_ab_judge
from nw.author_memory import (
    forget_preference,
    list_book_preferences,
    list_global_preferences,
    promote_book_preference_to_global,
    query_merged_author_memory,
    remember_book_preference,
    remember_global_preference,
    replace_preference,
)
from nw.cards import decide_card, save_card
from nw.context.briefing_compiler import compile_writer_briefing
from nw.context.story import StoryScope, build_story_context
from nw.craft_evolution import check_style_drift, pin_style_baseline
from nw.llm.base import GenResult, LLMProvider
from nw.models import Run
from nw.outline_copy_guard import check_outline_copy, extract_verbatim_anchors, split_by_anchors
from nw.override_ledger import is_overridable_code, list_overrides, record_override
from nw.pre_review_gate import compute_prose_stats, run_pre_review_gate
from nw.prose_normalizer import normalize_prose_punctuation
from nw.publish_preflight import sweep_book_for_publish, validate_publish_package, weighted_title_length
from nw.schema import VERSION
from nw.semantic_deslop import analyze_deslop_targets
from nw.store import Store, now
from nw.story_state import adopt_story, current_head, revision_state, write_revision
from nw.studio.author_shell import build_unified_review_view, translate_error
from nw.studio.library import LibraryService
from nw.task_models import canonical
from nw.verified_excerpts import (
    build_writer_verified_excerpts_packet,
    extract_and_verify_corpus_excerpt,
    save_verified_excerpt,
)
from nw.voice_specs import (
    compile_book_voice_spec,
    load_book_style_whitelist,
    save_book_style_whitelist,
    save_book_voice_spec,
)


class _ScriptedJudgeProvider(LLMProvider):
    name = 'scripted_judge'

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[list[dict]] = []

    def generate(self, messages: list[dict], **params) -> GenResult:
        self.calls.append(messages)
        reply = self._replies.pop(0)
        return GenResult(text=reply, finish_reason='complete', usage={'tokens': 42}, request_id='req-judge', raw={})


def _setup_managed_book_with_chapters(tmp_path: Path, chapter_texts: dict[int, str], name: str = 'book') -> Store:
    store = Store(tmp_path / name, create=True, test_mode=True)
    store.init_project('盐城暗流')
    store.add_brief('悬疑主线。', '不越界泄密。')
    ref_shen = save_card(store, {
        'card_id': 'char_shen', 'kind': 'character', 'origin': 'author',
        'body': {'name': '沈砚', 'role': '盐司小吏', 'want': '查清盐账真相', 'voice': '干脆克制', 'visibility': 'public'},
        'source_refs': [],
    }, None)
    dec_shen = decide_card(store, ref_shen, 'approved', 'ok')

    card_refs = [{'card_id': ref_shen.card_id, 'version': ref_shen.version, 'decision_id': dec_shen.id}]
    scenes = {}
    for ch_idx, txt in sorted(chapter_texts.items()):
        ch = store.add_chapter(ch_idx, f'风雪第{ch_idx}回')
        sc_cid = f'sc_card_{ch_idx}'
        sc_ref = save_card(store, {
            'card_id': sc_cid, 'kind': 'scene', 'origin': 'author',
            'body': {
                'title': f'第{ch_idx}场',
                'pov': 'char_shen',
                'characters': ['char_shen'],
                'location': '盐务旧库',
                'story_time': str(ch_idx),
                'goal': '推进调查并核实账册真伪',
                'conflict': '账房管事隐瞒缺页来历',
                'allowed_disclosure': '仅披露账本缺页',
                'visibility': 'public',
            },
            'source_refs': [],
        }, None)
        sc_dec = decide_card(store, sc_ref, 'approved', 'ok')
        card_refs.append({'card_id': sc_ref.card_id, 'version': sc_ref.version, 'decision_id': sc_dec.id})
        sc = store.add_scene(ch.id, 1, canonical({'story': {'scene_ref': {'card_id': sc_cid, 'version': 1}, 'story_order': ch_idx}}))
        scenes[ch_idx] = (sc, txt)

    adopt_story(store, {
        'as_of_story_order': 0,
        'disclosure_order': [0, 0, 0],
        'coverage': {'entities': ['char_shen'], 'predicates': ['location']},
        'facts': [{
            'entity_id': 'char_shen', 'predicate': 'location', 'holder': 'char_shen',
            'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0], 'value': '盐务旧库',
        }],
        'card_refs': card_refs,
    }, {})

    head = current_head(store, 'main')
    snap = revision_state(store, head)
    slots = dict(snap.get('slots') or {})
    for ch_idx, (sc, txt) in sorted(scenes.items()):
        rid = f'run-{ch_idx}'
        store.add_run(Run(
            rid, sc.id, 'write', 'author', 'test', '{}', '{}', '{}', '', 'complete', '{}', now(), now(),
        ))
        draft = store.add_draft(sc.id, txt, 'complete', rid)
        slots[sc.id] = {'draft_id': draft.id, 'delta_id': None}
    snap['slots'] = slots
    new_rev = head.revision + 1
    store.connection.execute(
        "INSERT INTO story_commits VALUES (?,'main',?,?,'h',?,?)",
        (f'c_test_{new_rev}', new_rev, head.revision, json.dumps(snap, ensure_ascii=False), now()),
    )
    store.connection.execute("UPDATE story_branches SET head_revision=? WHERE id='main'", (new_rev,))
    store.connection.commit()

    return store


# ── Schema v14 & Library DB Integrity ──

def test_schema_v14_and_library_tables(tmp_path: Path) -> None:
    assert VERSION >= 14
    with Store(tmp_path / 'fresh', create=True, test_mode=True) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == VERSION
        tables = {r[0] for r in store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert 'book_author_memory' in tables
        assert [r[0] for r in store.connection.execute('PRAGMA integrity_check')] == ['ok']

    lib = LibraryService(tmp_path / 'ws')
    with lib.connect() as conn:
        lib_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert 'global_author_memory' in lib_tables
        assert 'verified_corpus_excerpts' in lib_tables


# ── Fusion G: 0-Token Outline-Copy Guard ──

def test_fusion_g_outline_copy_guard_and_surgical_anchor_excision() -> None:
    outline = (
        '1. 沈砚带着缺了三页的盐账闯进后堂当面逼问周管事并把账册狠狠摔在桌上。\n'
        '原话：“欠账三百两，今天一个铜板也不能少，少一个字你就别想走出这道门。”\n'
        '2. 周管事脸色发青却死咬着不肯承认自己暗中扣下了腊月那批走私官盐的印鉴。'
    )
    anchors = extract_verbatim_anchors(outline)
    assert '欠账三百两，今天一个铜板也不能少，少一个字你就别想走出这道门。' in anchors

    # Draft uses authorized verbatim anchor ONLY (rest is genuinely dramatized) -> PASS
    clean_draft = (
        '后堂炭盆烧得正旺，沈砚反手插上门闩，把手里那本泛潮的薄册往红木案上一搁。\n'
        '他盯着周管事发虚的眼色，声音沉稳：“欠账三百两，今天一个铜板也不能少，少一个字你就别想走出这道门。”\n'
        '周管事端茶的手抖了一下，茶盖磕出清脆一响，嘴上却还硬撑着推说印鉴早交给仓房核验去了。'
    )
    ok_res = check_outline_copy(clean_draft, outline)
    assert ok_res['passed'] is True
    assert ok_res['anchors_excised'] == 1
    assert ok_res['hit_count'] == 0

    # Draft uses authorized anchor AND copies an unapproved 20+ Han sentence right next to it -> MUST CATCH!
    copied_draft = (
        '“欠账三百两，今天一个铜板也不能少，少一个字你就别想走出这道门。”\n'
        '周管事脸色发青，却死咬着不肯承认自己暗中扣下了腊月那批走私官盐的印鉴。'
    )
    bad_res = check_outline_copy(copied_draft, outline)
    assert bad_res['passed'] is False
    assert bad_res['anchors_excised'] == 1
    assert bad_res['max_overlap_han'] >= 16
    assert '周管事脸色发青' in bad_res['hits'][0]['draft_quote']

    # Verify surgical split_by_anchors keeps surrounding text intact
    segs, cnt = split_by_anchors('前句抄纲内容' + anchors[0] + '后句抄纲内容', anchors)
    assert cnt == 1
    assert [s for _, s in segs] == ['前句抄纲内容', '后句抄纲内容']

    # Integrated inside run_pre_review_gate
    gate = run_pre_review_gate(None, '', copied_draft, outline_text=outline)
    codes = {row['code'] for row in gate['issues']}
    assert 'PRE_OUTLINE_COPY' in codes


# ── Fusion H: Degeneration Guard + Empirical Punctuation Normalizer + Book-Local Style Whitelist ──

def test_fusion_h_normalizer_fixed_point_degeneration_and_book_local_whitelist(tmp_path: Path) -> None:
    # 1) Normalizer preserves valid `……` and `——`, fixes malformed forms, respects HTML comments & whitelist
    sample = (
        '<!-- keep --- ... 10--20 -->\n'
        '---\n'
        '沈砚停住脚步...抬头看向廊下——灯影摇晃，约莫有10--20名差役守在院外。\u200b\n'
        '“别动。。。”他压低声音，“再往前一步—后果自负———”\n'
        '他心里一沉.……..这批货的数量对不上。\n'
        '专属暗号...保留原样。\n'
    )
    norm1 = normalize_prose_punctuation(sample, quote_mode='keep', style_whitelist=['专属暗号...保留原样'])
    text1 = norm1['text']
    assert norm1['changed'] is True
    assert '<!-- keep --- ... 10--20 -->' in text1
    assert '专属暗号...保留原样' in text1
    assert '\u200b' not in text1
    assert '\n---\n' not in text1
    assert '10到20名差役' in text1
    assert '抬头看向廊下——灯影摇晃' in text1
    assert '沈砚停住脚步……抬头看向廊下' in text1
    assert '“别动……”' in text1
    assert '再往前一步——后果自负——' in text1
    assert '他心里一沉……这批货' in text1
    # Fixed-point guarantee
    norm2 = normalize_prose_punctuation(text1, quote_mode='keep', style_whitelist=['专属暗号...保留原样'])
    assert norm2['changed'] is False
    assert norm2['text'] == text1

    # Quote mode conversion
    yan = normalize_prose_punctuation('他说：“今晚动身。”', quote_mode='yan')
    assert yan['text'] == '他说：「今晚动身。」'
    curly = normalize_prose_punctuation('他说：「今晚动身。」', quote_mode='curly')
    assert curly['text'] == '他说：“今晚动身。”'

    # 2) Degeneration guard: verbatim repeat, bold leak, garbled, censored pinyin, author meta, tier-1 engineering
    degen_draft = (
        '作者有话说：新书启航求支持！\n'
        '沈砚检查了**密室机关**，发现那具尸ti旁掉着半枚铜钱，旁白提示这里需要拉满爽点密度。\n'
        '他慢慢推开木门走向院子中央的古井边查看。\n'
        '他慢慢推开木门走向院子中央的古井边查看。\n'
        '屋檐下飘来一丝异常气味\ufffd让人皱眉。'
    )
    rep = run_pre_review_gate(None, '', degen_draft)
    codes = {row['code'] for row in rep['issues']}
    assert 'PRE_AUTHOR_META_HEADER' in codes
    assert 'PRE_MARKDOWN_BOLD_LEAK' in codes
    assert 'PRE_CENSORED_PINYIN' in codes
    assert 'PRE_ENGINEERING_META_LEAK' in codes
    assert 'PRE_VERBATIM_REPEAT' in codes
    assert 'PRE_GARBLED_CHAR' in codes
    assert rep['passed'] is False
    assert rep['action'] == 'auto_rewrite'
    assert not is_overridable_code('PRE_VERBATIM_REPEAT')
    assert not is_overridable_code('PRE_MARKDOWN_BOLD_LEAK')
    assert translate_error('PRE_VERBATIM_REPEAT: dup')['code'] == 'PRE_VERBATIM_REPEAT'

    # Normal ASCII terms VIP/CEO/AI/PDF/5G and dialogue/system panels MUST NOT trigger false positives!
    modern_ok = (
        '林岚刷开VIP包厢门，把PDF合同递给对面的CEO，顺手看了一眼手机上的5G信号。\n'
        '对方笑道：“你这套说辞倒是很有爽点密度嘛。”\n'
        '【系统提示：当前爽点密度评估模块已关闭，请继续主线任务。】'
    )
    ok_rep = run_pre_review_gate(None, '', modern_ok)
    ok_codes = {row['code'] for row in ok_rep['issues']}
    assert 'PRE_CENSORED_PINYIN' not in ok_codes
    assert 'PRE_ENGINEERING_META_LEAK' not in ok_codes
    assert ok_rep['passed'] is True

    # 3) Book-local style whitelist isolation (Book A exempts catchphrase; Book B does NOT!)
    book_a = Store(tmp_path / 'book_a', create=True, test_mode=True)
    book_b = Store(tmp_path / 'book_b', create=True, test_mode=True)
    try:
        save_book_voice_spec(book_a, compile_book_voice_spec(['GENRE_XUANYI'], enabled=True))
        save_book_voice_spec(book_b, compile_book_voice_spec(['GENRE_XUANYI'], enabled=True))
        save_book_style_whitelist(book_a, ['命运的齿轮开始转动'])
        assert load_book_style_whitelist(book_a) == ['命运的齿轮开始转动']
        assert load_book_style_whitelist(book_b) == []

        sample_wl = '老钟楼敲过午夜，命运的齿轮开始转动，街角那盏油灯忽然熄了。'
        rep_a = run_pre_review_gate(book_a, '', sample_wl)
        rep_b = run_pre_review_gate(book_b, '', sample_wl)
        assert not any(i['code'] == 'PRE_CLICHE_DESTINY_GEAR' for i in rep_a['issues'])
        assert any(i['code'] == 'PRE_CLICHE_DESTINY_GEAR' for i in rep_b['issues'])
        assert analyze_deslop_targets(sample_wl, style_whitelist=['命运的齿轮开始转动'])['total_slop_hits'] == 0
    finally:
        book_a.connection.close()
        book_b.connection.close()


# ── Fusion I: 150k-Chapter Empirical Calibration & 3-Tier Severity ──

def test_fusion_i_empirical_calibration_three_tiers_and_prose_balance(tmp_path: Path) -> None:
    # 1) Review-required empirical AI rhetoric checks + advisory micro-action tics
    ai_rhetoric_prose = (
        '这不是一次简单的试探，而是蓄谋已久的清算。与其说是谈判，不如说是最后通牒。更像是一场猎杀，而不是交易。\n'
        '他声音不大，却字字砸在众人胸口。管事语气平淡，却透着彻骨寒意。\n'
        '屋里没有争吵，没有哭喊，也没有多余的解释。门外没有脚步，没有马蹄，也没有半点风声。\n'
        '他指腹轻轻摩挲着茶杯沿，慢慢拢住袖口，手往袖里缩了一寸，视线落在账册上停了半秒，唇角微不可察地扯了一下。\n'
        '他知道，这场较量，才刚刚开始。'
    )
    rep = run_pre_review_gate(None, '', ai_rhetoric_prose)
    codes = {row['code'] for row in rep['issues']}
    assert 'PRE_NOT_IS_CLUSTER' in codes
    assert 'PRE_VOICE_CONTRAST' in codes
    assert 'PRE_NEGATION_PARADE' in codes
    assert 'PRE_TRAILER_ENDING' in codes
    assert 'PRE_SLOW_MICRO_ACTION_TIC' in codes
    assert rep['hard_count'] == 0
    assert rep['review_required_count'] >= 4
    assert rep['action'] == 'review_required'
    assert rep['passed'] is False
    # All review_required items are overridable via Review-and-Ack!
    assert all(row['overridable'] for row in rep['review_required_items'])

    # Override clears review_required in 3-second Author Review View
    ovr_store = _setup_managed_book_with_chapters(tmp_path, {1: '占位。'}, name='ovr_book')
    try:
        for code in ('PRE_NOT_IS_CLUSTER', 'PRE_VOICE_CONTRAST', 'PRE_NEGATION_PARADE', 'PRE_TRAILER_ENDING', 'PRE_SLOW_MICRO_ACTION_TIC'):
            record_override(
                ovr_store, branch_id='main', constraint_kind='voice_soft',
                constraint_code=code, reason_tag='EDITORIAL_INTENT', reason_text='作者刻意保留节奏排比。',
            )
        view = build_unified_review_view(pre_review=rep, overrides=list_overrides(ovr_store, branch_id='main'))
        assert view['status'] == 'can_continue'
    finally:
        ovr_store.connection.close()

    # 2) Clean natural human prose with causal connectives & normal `——`/`……` passes cleanly!
    human_prose = (
        '沈砚把缺页的盐账往前推了半寸——反正这事拖过今夜也瞒不住，省得明天衙门来人再扯皮。\n'
        '他心里盘算着周管事八成会推到仓房头上，索性先截断退路：“腊月那批印鉴若真在仓房，我这就叫人把锁砸开验看。”\n'
        '周管事愣了一下，脸色立刻沉了下来，支吾着道：“沈大人，这……这可不合规矩。”'
    )
    h_stats = compute_prose_stats(human_prose)
    assert h_stats['causal_thought_sentence_ratio'] > 0.2
    assert h_stats['colloquial_connective_per_1k'] > 10.0
    h_rep = run_pre_review_gate(None, '', human_prose)
    assert h_rep['passed'] is True
    assert h_rep['action'] == 'pass'

    # 3) Empirical prose-balance drift detection in Living Craft Evolution
    base_ch = (
        '沈砚因为怕打草惊蛇，索性先把盐账收进暗格，省得管事起疑。他暗想今晚账房肯定有人来摸底，免得措手不及，便提前让小厮守住后门。\n'
        '好在夜里果然来了两个生面孔，他料到对方冲着印鉴来，偏偏不声张，只等他们进院。'
    )
    drifted_ch = (
        '他的指尖轻点桌面。他的指腹摩挲茶盏边缘。他的视线落在门缝上。他的喉结动了一下。\n'
        '他的眉心微皱。他的手指缓缓收拢。他的唇角微微抿紧。他的掌心渗出微汗。他的目光移向窗外。他的肩膀轻轻一沉。'
    )
    store = _setup_managed_book_with_chapters(tmp_path, {1: base_ch, 2: drifted_ch})
    try:
        pin_style_baseline(store, branch='main', start_chapter=1, end_chapter=1)
        drift = check_style_drift(store, branch='main', window_size=1)
        drift_metrics = {d['metric'] for d in drift['drifts']}
        assert 'body_action_sentence_ratio' in drift_metrics
        assert 'causal_thought_sentence_ratio' in drift_metrics
    finally:
        store.connection.close()


# ── Fusion J: Two-Level Cross-Book Author Memory + Exact 2KB Writer-Line Budget ──

def test_fusion_j_two_level_author_memory_budget_and_briefing(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'ws')
    store = _setup_managed_book_with_chapters(tmp_path, {1: '第一回干净正文。'})
    try:
        with lib.connect() as conn:
            ap1 = remember_global_preference(
                conn, assertion='普通对白少用书面感叹号，多用带脾气的短反问。',
                kind='dialogue', scope='global', importance=4,
            )
            ap2 = remember_global_preference(
                conn, assertion='悬疑线绝对不在章尾替读者剧透凶手真身。',
                kind='pacing', scope='genre', genre_tags=['GENRE_XUANYI'], importance=5,
            )
            ap3 = remember_global_preference(
                conn, assertion='修仙境界突破必须写清代价与异象，不可一笔带过。',
                kind='world', scope='genre', genre_tags=['GENRE_XIANXIA'], importance=5,
            )
            assert ap1['id'] == 'AP001'
            assert ap2['id'] == 'AP002'

            # Book preference overrides AP001 cleanly without mutating library.db!
            bp1 = remember_book_preference(
                store, assertion='本书男主嘴毒，对白允许短促反呛与口语打断。',
                kind='dialogue', importance=4, overrides_global_id='AP001',
            )
            bp2 = remember_book_preference(
                store, assertion='每场至少保留一处人物利害算账，拒绝全篇纯动作流水账。',
                kind='prose', importance=5,
            )
            assert bp1['id'] == 'BP001'

            # Query for GENRE_XUANYI: AP001 suppressed by BP001; AP003 filtered out by genre!
            merged = query_merged_author_memory(
                conn, store, genre_ids=['GENRE_XUANYI'], workflow_stage='writing', byte_budget=2048,
            )
            ids = [it['id'] for it in merged['items']]
            assert 'BP002' in ids and 'BP001' in ids and 'AP002' in ids
            assert 'AP001' not in ids  # Overridden by BP001!
            assert 'AP003' not in ids  # Different genre!
            assert 'AP001' in merged['overridden_global_ids']
            # AP001 still active in global store for other books!
            assert any(r['id'] == 'AP001' for r in list_global_preferences(conn, status='active'))

            # Exact rendered-line UTF-8 byte budget enforcement + transparent omission notice!
            for idx in range(6):
                remember_book_preference(
                    store, assertion=f'低优先级补充偏好第{idx}条：尽量精炼控制每段节奏并保持口语自然流畅。',
                    kind='prose', importance=2,
                )
            tight = query_merged_author_memory(
                conn, store, genre_ids=['GENRE_XUANYI'], workflow_stage='writing', byte_budget=220,
            )
            exact_bytes = sum(len(ln.encode('utf-8')) for ln in tight['lines'])
            assert tight['bytes_used'] == exact_bytes
            assert tight['bytes_used'] <= 220
            assert len(tight['omitted_ids']) >= 4
            assert len(tight['omitted_summaries']) == len(tight['omitted_ids'])
            assert '因 220 字节写前预算未注入' in tight['omission_notice']
            # Importance 5 items MUST survive tight budget ahead of importance 2
            top_ids = [it['id'] for it in tight['items']]
            assert 'BP002' in top_ids

            # Replace in same store & forget audit trail & promote BP -> AP
            rep = replace_preference('BP001', new_assertion='本书男主话少嘴毒，一句顶三句。', store=store)
            assert rep['new_item']['id'].startswith('BP')
            old_rows = list_book_preferences(store, status='replaced')
            assert any(r['id'] == 'BP001' and r['replaced_by'] == rep['new_item']['id'] for r in old_rows)
            promoted = promote_book_preference_to_global(store, conn, 'BP002', scope='global')
            assert promoted['global_item']['id'].startswith('AP')
            forgot = forget_preference(promoted['global_item']['id'], library_conn=conn)
            assert forgot['status'] == 'forgotten'

            # Verify writer context & natural briefing integration (0 leaked JSON keys)
            sc1 = store.list('scene')[0]
            scope = StoryScope('main', current_head(store, 'main').revision, 1, {'card_id': 'sc_card_1', 'version': 1})
            work = build_story_context(store, sc1.id, scope, 40000, library_conn=conn)
            briefing = compile_writer_briefing(work.package)
            assert '作者显式创作偏好' in briefing
            assert 'BP002' in briefing
    finally:
        store.connection.close()


# ── Fusion K: Machine-Verified Anonymized Real-Corpus Excerpts ──

def test_fusion_k_verified_anonymized_corpus_excerpts(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'ws')
    clean_chapter = (
        '清晨下过一阵小雨，盐司后院的青石板泛着暗光。顾长青把茶壶往灶边挪了挪，省得水烧干了味苦，'
        '顺手翻开案头那本旧账。头三页写得规规矩矩，墨色也新，可翻到第四页折角处，两笔银数的墨迹却比前头淡了半截。\n'
        '“赵管事，腊月二十三那车青盐，过卡的时候怎么少记了二十担？”顾长青没抬头，只用算盘珠子轻轻拨了一声。\n'
        '赵管事干笑两声，往门槛边退了半步：“大人瞧错了，那是年底折耗，库房里都有单子对得上。”'
    )
    start = 0
    end = len(clean_chapter)
    extracted = extract_and_verify_corpus_excerpt(
        clean_chapter, start, end,
        book_id='bk-real-01', chapter_index=3,
        type_tags=['GENRE_XUANYI'], scene_function='confrontation',
        learn_what='用具体账册破绽与日常口语推进对峙，不靠抽象氛围词。',
        do_not_copy='不照搬盐司账册和算盘桥段。',
        known_names={'顾长青': '甲', '赵管事': '乙'},
    )
    assert extracted['passed'] is True
    assert extracted['verification']['substr_match'] is True
    assert '顾长青' not in extracted['record']['anonymized_text']
    assert '赵管事' not in extracted['record']['anonymized_text']
    assert '甲' in extracted['record']['anonymized_text']

    with lib.connect() as conn:
        saved = save_verified_excerpt(conn, extracted)
        assert saved['status'] == 'verified'
        packet = build_writer_verified_excerpts_packet(conn, type_tags=['GENRE_XUANYI'], scene_function='confrontation')
        assert packet is not None and len(packet['excerpts']) == 1
        assert '甲' in packet['excerpts'][0]['text']

        # Polluted excerpt (censored pinyin + markdown bold + AI rhetoric) MUST BE REJECTED!
        polluted = (
            '这不是一场普通的**交易**，而是致命的陷阱。与其说是谈判，不如说是死局。更像是掠夺，而不是合作。'
            '他看了一眼地上的尸ti，语气平淡，却透着冷意，声音不大，却震慑全场，这场较量，才刚刚开始。'
        )
        bad_ex = extract_and_verify_corpus_excerpt(polluted, 0, len(polluted), min_chars=50)
        assert bad_ex['passed'] is False
        with pytest.raises(ValueError, match='EXCERPT_VERIFICATION_FAILED'):
            save_verified_excerpt(conn, bad_ex)


# ── Fusion L: Platform Publish Preflight + Scene-vs-Summary + Position-Swapped Blind A/B Judge ──

def test_fusion_l_publish_preflight_scene_vs_summary_and_position_swapped_ab_judge(tmp_path: Path) -> None:
    # 1) Platform metadata preflight (weighted length, banned symbols/spaces/emoji, synopsis & tags)
    assert weighted_title_length('AI觉醒1999', half_width_ascii=True) == 5.0  # 2 CJK + 6*0.5 ASCII
    assert weighted_title_length('AI觉醒1999', half_width_ascii=False) == 8.0

    bad_meta = validate_publish_package(
        'fanqie',
        title='【爆款】 盐城暗流🔥超级无敌长书名超出番茄上限',
        synopsis='太短且加群12345',
        tags=['悬疑', '推理', '官场', '反转', '权谋', '超限第六标签'],
    )
    assert bad_meta['passed'] is False
    bad_codes = {i['code'] for i in bad_meta['blocking_issues']}
    assert {'TITLE_TOO_LONG', 'TITLE_HAS_WHITESPACE', 'TITLE_FORBIDDEN_SYMBOL', 'TITLE_FORBIDDEN_EMOJI',
            'SYNOPSIS_TOO_SHORT', 'SYNOPSIS_EXTERNAL_CONTACT', 'TAGS_OVER_LIMIT'} <= bad_codes

    good_meta = validate_publish_package(
        'fanqie',
        title='盐城旧账',
        synopsis='一册缺了三页的腊月盐账，牵出江南十州沉埋十年的私盐血案。小吏沈砚从半枚残印查起，在步步杀机中撕开官商铁幕。',
        tags=['悬疑推理', '历史权谋', '强反转'],
        category='悬疑',
    )
    assert good_meta['passed'] is True
    assert good_meta['blocking_issues'] == []

    # 2) Whole-book sweep: cleans malformed punctuation AND blocks chapters with Markdown bold / verbatim repeat
    ch1_auto_cleanable = (
        '沈砚推开门...院里约有10--20人守着，他说：“别动。。。”\u200b\n'
        '管事赶紧把账本收进袖里，可风一吹，半页纸角还是露了出来。沈砚没急着抢，反正院外已经围稳了。'
    )
    ch2_blocked = '他走到门口，突然看见**系统加粗泄露**，然后继续往前走。\n同一句复读测试内容超过八个字。\n同一句复读测试内容超过八个字。'
    store = _setup_managed_book_with_chapters(tmp_path, {1: ch1_auto_cleanable, 2: ch2_blocked})
    try:
        sweep = sweep_book_for_publish(store, branch='main', platform='fanqie', quote_mode='curly')
        assert sweep['passed'] is False
        assert sweep['chapter_count'] == 2
        assert sweep['blocked_chapters'] == 1
        assert sweep['auto_cleaned_chapters'] == 1
        assert sweep['chapters'][0]['status'] == 'auto_cleanable'
        assert sweep['chapters'][1]['status'] == 'blocked'
        assert '10到20人' in sweep['clean_export_text']
        assert '\u200b' not in sweep['clean_export_text']
    finally:
        store.connection.close()

    # 3) Scene-vs-Summary strict beat evaluator
    svs_provider = _ScriptedJudgeProvider([
        json.dumps({
            'beats': [
                {'index': 1, 'beat': '沈砚亮出缺页账册逼问管事', 'status': 'scene',
                 'evidence': '沈砚把账本往案上一搁：“欠账三百两。”', 'reason': '有具体动作与当场对白交锋'},
                {'index': 2, 'beat': '后院伏兵突袭被反杀', 'status': 'summary',
                 'evidence': '经过一番激战，他们击退了伏兵。', 'reason': '仅一句概述带过未写过程'},
                {'index': 3, 'beat': '捡到刻字铜牌', 'status': 'missing',
                 'evidence': '', 'reason': '正文中未提及铜牌'},
            ],
            'summary': '第1拍展开充分，第2拍为概述带过，第3拍遗漏。',
        }, ensure_ascii=False)
    ])
    svs = evaluate_scene_vs_summary(
        ['沈砚亮出缺页账册逼问管事', '后院伏兵突袭被反杀', '捡到刻字铜牌'],
        '沈砚把账本往案上一搁：“欠账三百两。”经过一番激战，他们击退了伏兵。',
        svs_provider, 'judge-model',
    )
    assert svs['parsed_ok'] is True
    assert svs['scene_count'] == 1
    assert svs['summary_count'] == 1
    assert svs['missing_count'] == 1
    assert svs['all_dramatized'] is False

    # 4) Position-Swapped Blind A/B Judge — Consensus Winner vs Position-Bias Neutralization!
    # 4a) True consensus: Round 1 (A, B) picks slot "2" (=B); Round 2 (B, A) picks slot "1" (=B) -> Winner B!
    consensus_judge = _ScriptedJudgeProvider([
        json.dumps({'winner': '2', 'evidence_1': '稿一略平', 'evidence_2': '稿二对白有张力', 'rationale': '稿二胜出'}, ensure_ascii=False),
        json.dumps({'winner': '1', 'evidence_1': '稿一对白有张力', 'evidence_2': '稿二略平', 'rationale': '稿一胜出'}, ensure_ascii=False),
    ])
    res_win = run_position_swapped_ab_judge(
        '草稿A正文内容', '草稿B更生动正文内容',
        provider=consensus_judge, model='judge-cross-family',
        label_a='v1', label_b='v2',
    )
    assert res_win['winner'] == 'B'
    assert res_win['winner_label'] == 'v2'
    assert res_win['consensus'] is True
    assert res_win['position_bias_detected'] is False
    assert len(consensus_judge.calls) == 2

    # 4b) Position-biased judge: ALWAYS picks slot "1" -> Round 1 maps to A, Round 2 maps to B -> Forced TIE!
    biased_judge = _ScriptedJudgeProvider([
        json.dumps({'winner': '1', 'evidence_1': '排第一', 'evidence_2': '排第二', 'rationale': '偏爱第一稿'}, ensure_ascii=False),
        json.dumps({'winner': '1', 'evidence_1': '排第一', 'evidence_2': '排第二', 'rationale': '仍偏爱第一稿'}, ensure_ascii=False),
    ])
    res_tie = run_position_swapped_ab_judge(
        '草稿A正文内容', '草稿B正文内容',
        provider=biased_judge, model='judge-biased',
    )
    assert res_tie['winner'] == 'tie'
    assert res_tie['consensus'] is False
    assert res_tie['position_bias_detected'] is True
    assert '位置偏见' in res_tie['summary']
