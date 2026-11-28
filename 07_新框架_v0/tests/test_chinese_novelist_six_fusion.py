"""Tests for Round 4 Dimensional Fusion Upgrades (Fusion M-R, SQLite v15).

Covers:
  - SQLite v14 -> v15 incremental migration (`fact_ledger` table).
  - Fusion M: 0-Token Whole-Book 12-Dimension Mechanical Audit Engine (`book_audit.py`)
    (character presence + long-name masking + >=4-chapter gap + tail-25% disappearance,
     interrupted-dialogue catchphrase stitching, O(N) repeated phrases, quote imbalance,
     rhythm & dialogue plunge, steering feedback into `compute_serial_health`).
  - Fusion N: Automatic Chapter-1 Self-Calibration Anchor (`craft_evolution.py`) +
    Prose-Last Priming Order in `compile_writer_briefing` (live prose always at prompt tail!).
  - Fusion O: SQLite v15 Epistemic & Numeric Fact Ledger (`fact_ledger.py`, hides `full_truth`
    until `planned_reveal_chapter`, enforces first-appearance term clue) +
    0-Token Self-Stated Count Auditor in `pre_review_gate.py`.
  - Fusion P: 0-Token Diagnostic Anti-Padding Expansion (`expansion_advisor.py` + `scene_messages.py`) +
    7-Mode Opener / 13-Mode Hook variety rotation.
  - Fusion Q: Commercial Title Workshop (5 techniques, anti-AI cliché guard, 6-platform length check,
    live Radar `title_bigrams`) + `GET /wizard/preferences`.
  - Fusion R: `micro_short` (0.5–3万字短篇快变现模式) in `length_settings.py` & `plot_pacing_specs.py`
    without disrupting existing 5-tier long-form rules!
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nw.book_audit import (
    build_book_audit_steering_lines,
    compute_catchphrase_stats,
    compute_presence,
    detect_presence_gaps,
    repeated_phrases,
    run_whole_book_audit,
)
from nw.context.briefing_compiler import compile_writer_briefing
from nw.craft_evolution import auto_extract_chapter1_calibration_anchor, load_book_calibration_anchor
from nw.expansion_advisor import (
    HOOK_MODES_13,
    OPENING_MODES_7,
    diagnose_and_advise_expansion,
    generate_title_candidates,
    recommend_chapter_opener_and_hook,
)
from nw.fact_ledger import build_writer_fact_ledger_packet, delete_fact_entry, list_fact_entries, upsert_fact_entry
from nw.length_settings import WORD_TIERS, parse_length_changes
from nw.llm.base import GenResult
from nw.models import Draft, Run
from nw.plot_pacing_specs import compute_scale_profile
from nw.pre_review_gate import run_pre_review_gate
from nw.scene_messages import draft_messages
from nw.schema import VERSION
from nw.store import Store, now
from nw.cards import save_card
from nw.studio.chart_radar import parse_chart_import, save_chart_snapshot
from nw.studio.library import LibraryService
from nw.studio.production_routes import ProductionRoutes


def _accept_chapter(store: Store, ch_index: int, title: str, text: str) -> str:
    ch = store.add_chapter(ch_index, title)
    card_json = json.dumps(
        {'title': title, 'pov': 'char_mc', 'location': '旧城', 'goal': '破局', 'conflict': '受阻', 'allowed_disclosure': ''},
        ensure_ascii=False,
    )
    sc = store.add_scene(ch.id, 1, card_json)
    rid = f'run-ch{ch_index}'
    store.add_run(Run(rid, sc.id, 'write', 'fake', 'fake-m', '{}', '{}', '{}', '', 'error', '{}', now(), ''))
    _, draft = store.finish_run(rid, GenResult(text=text, finish_reason='complete', usage={}, request_id='r', raw=None))
    store.accept(draft.id)
    return sc.id


# ── SQLite v15 & Fusion O: Fact Ledger + 0-Token Self-Stated Count Auditor ────

def test_sqlite_v15_fact_ledger_and_self_stated_count_auditor(tmp_path: Path) -> None:
    assert VERSION == 15
    with Store(tmp_path / 'proj', create=True, test_mode=True) as store:
        store.init_project('测试书')
        store.add_brief('构想', '')
        ver = store.connection.execute('PRAGMA user_version').fetchone()[0]
        assert ver == 15

        e1 = upsert_fact_entry(
            store, name='蓝晶', category='term', first_chapter=2,
            reader_known='黑市极贵重的冷光晶体', full_truth='封印上古记忆的载体',
            planned_reveal_chapter=8,
        )
        upsert_fact_entry(
            store, name='北凉灭国年限', category='timeline', first_chapter=1,
            reader_known='十一年前',
        )
        assert len(list_fact_entries(store)) == 2

        # At Ch2: term is first appearance (demands inline clue), full_truth MUST NOT leak!
        p2 = build_writer_fact_ledger_packet(store, chapter_index=2)
        assert p2 is not None
        joined2 = '\n'.join(p2['lines'])
        assert '本章首现' in joined2 and '蓝晶' in joined2
        assert '十一年前' in joined2
        assert '封印上古记忆' not in joined2

        # At Ch8: planned_reveal_chapter reached -> due reveal appears with full_truth!
        p8 = build_writer_fact_ledger_packet(store, chapter_index=8)
        assert p8 is not None and p8['due_reveals_count'] == 1
        assert '封印上古记忆' in '\n'.join(p8['lines'])

        assert delete_fact_entry(store, e1['id'])['deleted'] is True

    # 0-Token Self-Stated Count Auditor catches miscounted quote & list items!
    bad_prose = (
        '他拆开密折，上面只有六个字：“速回京城，切莫声张，违者斩。”\n'
        '桌上摆着三件物证：一把铜钥匙、一封染血信件、一枚玉佩、半块干粮。'
    )
    gate = run_pre_review_gate(None, '', bad_prose)
    codes = {i['code'] for i in gate['issues']}
    assert 'PRE_SELF_STATED_CHAR_COUNT_MISMATCH' in codes
    assert 'PRE_SELF_STATED_LIST_COUNT_MISMATCH' in codes

    # Accurate counts pass cleanly with zero count errors
    good_prose = '他拆开密折，上面只有八个字：“速回京城，切莫声张。”\n桌上摆着三件物证：一把铜钥匙、一封信、一枚玉佩。'
    gate_ok = run_pre_review_gate(None, '', good_prose)
    ok_codes = {i['code'] for i in gate_ok['issues']}
    assert 'PRE_SELF_STATED_CHAR_COUNT_MISMATCH' not in ok_codes
    assert 'PRE_SELF_STATED_LIST_COUNT_MISMATCH' not in ok_codes


# ── Fusion M: 0-Token Whole-Book 12-Dimension Mechanical Audit ────────────────

def test_whole_book_12d_mechanical_audit_and_interrupted_catchphrases(tmp_path: Path) -> None:
    # Interrupted dialogue catchphrase stitching ("孩子，"他说，"坐下谈。")
    cast = [
        {'name': '苏晚', 'role': '主角', 'aliases': ['阿晚'], 'catchphrases': []},
        {'name': '周明', 'role': '配角', 'aliases': [], 'catchphrases': ['孩子坐下谈', '别多问']},
        {'name': '苏晚晴', 'role': '配角', 'aliases': [], 'catchphrases': []},
    ]
    ch_texts = [
        '苏晚走进客厅，苏晚晴冷笑。周明开口：“孩子，”他倒了杯茶，“坐下谈。”',
        '苏晚和周明商议对策。周明叹气，周明又摇了摇头。',
        '苏晚独自查案，寒意顺着脊背爬上来。寒意顺着脊背爬上来。',
        '苏晚翻找旧档，寒意顺着脊背爬上来。寒意顺着脊背爬上来。',
        '苏晚夜探仓库，寒意顺着脊背爬上来。寒意顺着脊背爬上来。',
        '苏晚对峙黑衣人，寒意顺着脊背爬上来。寒意顺着脊背爬上来。',
        '周明终于现身救场。苏晚松了口气。',
    ]
    # Presence: long-name masking prevents `苏晚` inside `苏晚晴` from double counting!
    pres = compute_presence(cast, ch_texts)
    by_name = {m['name']: m for m in pres}
    assert by_name['苏晚']['counts'][0] == 1  # only standalone 苏晚, NOT 苏晚晴!
    gaps = detect_presence_gaps(pres, gap=4, prior_mentions=3)
    assert any(g['name'] == '周明' and g['chapters'] == 4 for g in gaps)

    # Interrupted dialogue catchphrase matched! Unfulfilled catchphrase (`别多问`) == 0!
    cps = compute_catchphrase_stats(cast, ch_texts)
    cp_map = {r['phrase']: r['total'] for r in cps}
    assert cp_map['孩子坐下谈'] == 1
    assert cp_map['别多问'] == 0

    # O(N) repeated phrases catches cross-chapter tic (>=8 times)
    reps = repeated_phrases(ch_texts, floor=4)
    assert any('寒意顺着脊背爬上来' in r['phrase'] and r['count'] == 8 for r in reps)

    # End-to-end Store audit
    with Store(tmp_path / 'book_audit', create=True, test_mode=True) as store:
        store.init_project('审读测试书')
        store.add_brief('构想', '')
        save_card(store, {'card_id': 'char_mc', 'kind': 'character', 'origin': 'author', 'body': {'name': '陆寒', 'role': '主角', 'want': '破案'}}, None)
        save_card(store, {'card_id': 'char_ally', 'kind': 'character', 'origin': 'author', 'body': {'name': '老陈', 'role': '配角', 'want': '护友', 'voice': '总爱说「稳住别慌」'}}, None)
        _accept_chapter(store, 1, '开篇', '陆寒推开门。“老陈？”他低声喊道。' + '老陈点头说：“稳住，”他压低声音，“别慌。”' + '窗外雨声哗哗落了下来。' * 15)
        _accept_chapter(store, 2, '失衡', '陆寒独自翻账本，“这里少了一页。')  # Unbalanced quote + low word count!
        audit = run_whole_book_audit(store, min_chapter_words=100)
        assert len(audit['checks']) == 12
        kinds = {f['kind'] for f in audit['findings']}
        assert 'quote' in kinds and 'words' in kinds
        assert audit['catchphrases'][0]['total'] == 1
        assert len(build_book_audit_steering_lines(audit)) >= 1


# ── Fusion N: Chapter-1 Self-Calibration Anchor & Prose-Last Priming ──────────

def test_chapter1_calibration_anchor_and_prose_last_briefing(tmp_path: Path) -> None:
    ch1_prose = (
        '“欠条拿来。”陆寒把擦柜台的湿布甩在木桌上，指节敲了敲玻璃板。\n'
        '刀疤脸往地上吐了口烟灰，把泛黄的借据拍在柜台正中，冷笑一声：“三十万本金加利滚利九十万，今天不按手印，铺子就换姓。”\n'
        '陆寒没低头看字，只盯着对方左手虎口那块刚结痂的烫伤，伸手按下柜台底下的老铜铃。\n'
        '“周管事，我爹去年七月早就没了，这鲜红的指印是谁替他按上去的？”话音落地，门外忽地响起急促的刹车声。\n'
        '两名壮汉下意识往门口偏头，刀疤脸手掌猛地拍回借据上想往袖里塞，陆寒早一步拿铁尺压住了纸角。'
    )
    with Store(tmp_path / 'cal_proj', create=True, test_mode=True) as store:
        store.init_project('锚段测试书')
        store.add_brief('构想', '')
        _accept_chapter(store, 1, '典当行欠条', ch1_prose)
        anchor = auto_extract_chapter1_calibration_anchor(store)
        assert anchor is not None
        assert anchor['chapter_index'] == 1 and '陆寒' in anchor['excerpt']
        assert load_book_calibration_anchor(store)['excerpt'] == anchor['excerpt']

    # Prose-Last Priming: Section 6 MUST appear AFTER structured constraints/rules/summaries!
    pkg = {
        'items': [
            {'source': 'scene:s2', 'text': json.dumps({'title': '第二章对峙', 'goal': '拆穿伪证', 'conflict': '对手反扑'}, ensure_ascii=False)},
            {'source': 'fact-ledger', 'text': json.dumps({'lines': ['【本章首现】「鉴伪印」→ 老铺信物']}, ensure_ascii=False)},
            {'source': 'calibration-anchor', 'text': json.dumps({'chapter_index': 1, 'excerpt': ch1_prose[:320]}, ensure_ascii=False)},
            {'source': 'previous:s1', 'text': '玻璃门被人从外猛地推开，带队的赵队长扫过满桌狼藉。'},
            {'source': 'rule:r1', 'text': json.dumps({'rule': '保持受限视角'}, ensure_ascii=False)},
        ],
    }
    compiled = compile_writer_briefing(pkg)
    pos_rules = compiled.find('本场适用的写法检验要点')
    pos_anchor = compiled.find('本书第1章文风自校准锚段')
    pos_prev = compiled.find('紧邻前文尾段')
    assert pos_rules < pos_anchor < pos_prev
    assert '鉴伪印' in compiled


# ── Fusion P, Q & R: Diagnostic Expansion, 7/13 Hooks, Title Workshop & Micro-Short ─

def test_expansion_advisor_hooks_title_workshop_and_micro_short(tmp_path: Path) -> None:
    # Fusion P1: Diagnostic anti-padding expansion
    thin_draft = '他走进房间，发现桌子上有封信，于是立刻明白了真相并冲了出去。'
    exp = diagnose_and_advise_expansion(thin_draft, min_words=2000)
    assert exp['word_gap'] > 1900
    assert any('对话' in d['strategy'] for d in exp['diagnoses'])
    assert '防注水铁律' in exp['prompt_block']

    # Also auto-injected into revise prompt when length_feedback flags short draft!
    d = Draft('d1', 's1', 1, thin_draft, 'complete', 'r1', now())
    msgs, _ = draft_messages({}, 'revise', d, {'notes': '字数不足'}, None, '', (), length_feedback=['当前字数不足，低于 2000 字下限'])
    assert '诊断式定向扩充指令' in msgs[0]['content']

    # Fusion P2: 7 Opener & 13 Hook rotation avoids recent duplicates
    assert len(OPENING_MODES_7) == 7 and len(HOOK_MODES_13) == 13
    rec1 = recommend_chapter_opener_and_hook(1)
    rec2 = recommend_chapter_opener_and_hook(2, recent_hooks=[rec1['hook']['id']])
    assert rec2['hook']['id'] != rec1['hook']['id']

    # Fusion Q: 5-technique Commercial Title Workshop with platform limits + Radar bigrams
    lib = LibraryService(tmp_path / 'lib')
    with lib.connect() as conn:
        save_chart_snapshot(conn, parse_chart_import(json.dumps({
            'platform': '番茄', 'list_name': '黑马新书榜',
            'entries': [
                {'rank': 1, 'title': '怪谈当铺老板', 'author': 'A', 'genre': '悬疑', '在读': '15万'},
                {'rank': 2, 'title': '怪谈契约师', 'author': 'B', 'genre': '悬疑', '在读': '12万'},
            ],
        }, ensure_ascii=False)))

    ws = lib.radar_title_workshop({
        'platform': 'jjwxc', 'genre_name': '悬疑言情', 'idea': '在古董当铺识破伪造欠条反杀家族仇敌',
        'protagonist': '当铺掌柜', 'conflict': '退婚夺产', 'use_llm': False,
    })
    assert len(ws['candidates']) == 5
    assert ws['max_title_length'] == 14.0
    assert all(c['weighted_length'] <= 14.0 and c['passed'] for c in ws['candidates'])

    # Fusion R: micro_short (0.5–3万字短篇快变现) coexists with 5-tier long-form without breaking WORD_TIERS!
    assert WORD_TIERS == (300_000, 500_000, 1_000_000, 1_500_000, 2_000_000)
    parsed_short = parse_length_changes({'length_mode': 'micro_short', 'target_words': 15_000, 'chapter_count': 6})
    assert parsed_short['length_mode'] == 'micro_short' and parsed_short['target_words'] == 15_000
    with pytest.raises(ValueError):
        parse_length_changes({'length_mode': 'micro_short', 'target_words': 80_000})

    scale_short = compute_scale_profile(15_000)
    assert scale_short['tier_id'] == 'micro_short'
    assert '导语' in scale_short['golden_three_target'] and '免转付' in scale_short['golden_three_target']


# ── HTTP Route Integration for Title Workshop & Fact Ledger ───────────────────

def test_round4_studio_http_routes(tmp_path: Path) -> None:
    lib = LibraryService(tmp_path / 'lib')

    class _StubH:
        def __init__(self) -> None:
            self.status = 0
            self.payload: Any = None

        def _send_json(self, status: int, data: Any) -> None:
            self.status = status
            self.payload = data

    class _StubProd:
        def wizard_preferences(self) -> dict:
            return {'favorite_genre_ids': ['GENRE_XUANYI'], 'taboos': ['禁无脑后宫']}

    routes = ProductionRoutes(_StubProd(), lib)
    h1 = _StubH()
    assert routes.get(h1, ['wizard', 'preferences'], {})
    assert h1.status == 200 and h1.payload['favorite_genre_ids'] == ['GENRE_XUANYI']

    h2 = _StubH()
    assert routes.post(h2, ['radar', 'title-workshop'], {
        'platform': 'zhihu_yanyan', 'genre_name': '现代言情', 'idea': '大婚当夜拆穿未婚夫阴谋反杀夺产', 'use_llm': False,
    })
    assert h2.status == 200 and len(h2.payload['candidates']) == 5
    assert h2.payload['platform'] == 'zhihu_yanyan'
