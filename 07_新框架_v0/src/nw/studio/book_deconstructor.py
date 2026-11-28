"""Enhanced Multi-Level Book Deconstructor (Golden-3 Anatomy, Quantitative Web-Feel Exam,
Reusable RH/TR Rhythm & EM Emotion Module Registries, Verified Excerpt Auto-Harvester,
and Topic-Decision Verification Backfill).

Fuses:
  - oh-story `story-long-analyze` & `story-short-analyze` (0-token deterministic vertical-screen
    & Golden-3 metrics, `RH-*` payoff loops, `TR-*` emotional triggers, `EM-*` plot-free reusable
    emotion module cards, short-fiction lead/section metrics, topic backfill)
  - InkOS 8-Layer Long-Form Analysis Lens (promise, story engine, failure conditions, recombination)
  - Our Round 3 `verified_excerpts` (3-check zero-alert real-prose auto-harvesting) &
    150k-chapter empirical prose-balance metrics (`body_action` vs `causal_thought`).
"""
from __future__ import annotations

from collections import Counter
import json
import re
import sqlite3
from statistics import median
from typing import Any

from nw.call_control import send_model
from nw.llm.base import LLMProvider
from nw.pre_review_gate import compute_prose_stats
from nw.studio.chart_radar import backfill_topic_verification
from nw.studio.corpus_direct import classify_story_units
from nw.studio.library_util import encode, timestamp
from nw.verified_excerpts import extract_and_verify_corpus_excerpt, save_verified_excerpt

BOOK_DECONSTRUCT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS book_deconstruct_artifacts (
 book_id TEXT PRIMARY KEY REFERENCES staging_books(id),
 book_scale TEXT NOT NULL DEFAULT 'long' CHECK(book_scale IN ('long','short')),
 quantitative_json TEXT NOT NULL DEFAULT '{}',
 golden_three_json TEXT NOT NULL DEFAULT '{}',
 rhythm_registry_json TEXT NOT NULL DEFAULT '{}',
 emotion_modules_json TEXT NOT NULL DEFAULT '[]',
 harvested_excerpts_json TEXT NOT NULL DEFAULT '[]',
 backfilled_topic_ids_json TEXT NOT NULL DEFAULT '[]',
 updated_at TEXT NOT NULL);
'''

_AUTHOR_NOTE_RE = re.compile(r'(?:【作者有话说】|作者有话说[:：]|PS[:：]|求月票|求推荐票|求五星好评)[\s\S]{0,600}$')
_DIALOGUE_SPAN_RE = re.compile(r'(“[^”\n]*”|「[^」\n]*」|『[^』\n]*』|"[^"\n]*")|(【[^】\n]*】)')
_HOOK_CONFLICT_RE = re.compile(r'(?:退婚|杀|死|债|滚|赔|抓|跪|休书|离婚|破产|举报|查封|围住|拔剑|枪|血|毒|审)')
_HOOK_SYSTEM_RE = re.compile(r'(?:叮[！!]|【[^】]{2,30}系统|面板|属性|觉醒|绑定|签到|倒计时)')
_HOOK_SUSPENSE_RE = re.compile(r'(?:不对劲|消失|失踪|尸体|血迹|秘密|究竟|到底|是谁|为何|奇怪|诡异|纸条|日记)')
_CLIFFHANGER_END_RE = re.compile(r'(?:[？?!！……]|就在这时|下一秒|门开了|突然|猛地|忽然|竟然|赫然|——)')
_LEAD_SEP_RE = re.compile(r'^(?:(?:…\s*){2,}|(?:\.\s*){3,}|[—\-]{2,}|0?1\.?)$')
_COMMON_NON_NAMES = frozenset({
    '自己', '这里', '那里', '什么', '没有', '不是', '知道', '时候', '现在', '已经', '可以', '不能',
    '一个', '这个', '那个', '他们', '她们', '我们', '你们', '虽然', '但是', '因为', '所以', '不过',
    '突然', '忽然', '看着', '说道', '问道', '笑道', '冷笑', '抬头', '低头', '转身', '起身', '点头',
    '摇头', '声音', '目光', '眼神', '脸色', '心里', '心中', '大家', '众人', '男人', '女人', '老人',
    '此时', '这时', '话音', '门外', '门口', '外面', '里面', '桌上', '地上', '身旁', '背后', '眼前',
    '刚才', '片刻', '就在', '然而', '可是', '只是', '还是', '终于', '猛地', '立刻', '马上', '随即',
    '接着', '然后', '于是', '同时', '原来', '其实', '毕竟', '果然', '竟然', '居然', '赫然', '几乎',
    '仿佛', '似乎', '大概', '也许', '肯定', '必须', '应该', '能够', '不要', '不会', '不敢', '不知',
    '不想', '无法', '玻璃', '柜台', '抽屉', '手机', '电话', '账本', '欠条', '钥匙', '名片', '卷帘门',
    '下一秒', '所有人', '两个人', '三个人', '玻璃门', '卷帘', '黑夹克', '两名', '三个', '那张', '这间',
})

DEEP_DECONSTRUCT_SYSTEM_PROMPT = (
    '你是顶级商业网文拆书结构分析师。基于给出的【量化体检表】与【黄金三章/核心章节原文】，'
    '严格依据原文证据输出高密度结构化拆解 JSON（绝不虚构原文未出现的情节，绝不把原书专名写进可复用模块模板）。\n'
    '严格输出一个 JSON 对象，结构如下：\n'
    '{\n'
    '  "golden_three": {\n'
    '    "overall_verdict": "两句白话总结开篇前三章最抓人/最薄弱之处",\n'
    '    "golden_finger_chapter": 1,\n'
    '    "opening_hook_type": "冲突/悬念/反差/系统亮牌/信息差/奇观",\n'
    '    "chapters": [\n'
    '      {"chapter": 1, "core_event": "一句话", "hook_method": "开篇手法", "payoff_type": "爽点/反转形态",\n'
    '       "reaction_layers": ["反应层级描述"], "cliffhanger": "章尾卡点与追读问题", "transferable": "可复用写法"}\n'
    '    ]\n'
    '  },\n'
    '  "rhythm_registry": {\n'
    '    "story_framework": "升级流/复仇线/多线交织/悬疑破局/情感拉扯/经营种田",\n'
    '    "core_engine": "全书持续驱动读者追读的核心引擎",\n'
    '    "rh_loops": [\n'
    '      {"id": "RH-001", "chapters": "第1-3章", "setup": "铺垫层缺口/压抑", "release": "释放层打脸/兑现",\n'
    '       "reaction": "反应层他人/权威重评", "next_hook": "衔接层新钩子", "escalation": "升级方式"}\n'
    '    ],\n'
    '    "tr_triggers": [\n'
    '      {"id": "TR-001", "chapter": 1, "event": "触发事件", "target_emotion": "期待/爽/愤怒/心疼/紧张/好奇",\n'
    '       "peak": "情绪爆发点", "aftermath": "余波与冷却", "reuse_tip": "留情绪链不搬事件"}\n'
    '    ]\n'
    '  },\n'
    '  "emotion_modules": [\n'
    '    {\n'
    '      "id": "EM-001",\n'
    '      "name": "模块名（去剧情抽象名）",\n'
    '      "reader_want": "读者想看什么（一句话）",\n'
    '      "emotion_chain": "缺口 → 加压 → 触发 → 爆发 → 余波",\n'
    '      "dramatic_unit": "去素材后的核心戏剧结构",\n'
    '      "replaceable_slots": ["功能位1（如被轻视者身份）", "功能位2（如验证筹码）"],\n'
    '      "do_not_copy": ["不可照搬的原书专名/标志台词/具体事件顺序"],\n'
    '      "failure_conditions": "在什么条件下会失效或翻车",\n'
    '      "related_rhythm": "RH-001 / TR-001"\n'
    '    }\n'
    '  ]\n'
    '}'
)


def ensure_book_deconstruct_table(conn: sqlite3.Connection) -> None:
    conn.executescript(BOOK_DECONSTRUCT_SCHEMA)


def _visible_chars(text: str) -> int:
    return len(re.sub(r'\s+', '', text or ''))


def _strip_author_notes(text: str) -> tuple[str, bool]:
    cleaned = _AUTHOR_NOTE_RE.sub('', text or '').strip()
    return cleaned, (len(cleaned) != len((text or '').strip()))


def _is_single_sentence_para(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # If sentence-ending punctuation appears before non-closing content, it has >=2 sentences
    return re.search(r'[。！？!?]+[”’」』"\'）】]*(?=[^\s”’」』"\'）】])', s) is None


def _measure_block_metrics(text: str) -> dict[str, Any]:
    """Deterministic zero-token vertical-screen & empirical prose-balance metrics."""
    clean, stripped_note = _strip_author_notes(text)
    lines = [
        ln.strip() for ln in clean.splitlines()
        if ln.strip() and not re.match(r'^(?:#{1,6}\s|-{3,}$|第[〇零一二三四五六七八九十百千万两\d]+[卷部篇章回节](?:[\s：:·\-].*)?$)', ln.strip())
    ]
    para_lens = [_visible_chars(ln) for ln in lines if _visible_chars(ln) > 0]
    body_chars = sum(para_lens)

    med_para = round(float(median(para_lens)), 1) if para_lens else 0.0
    mean_para = round(body_chars / max(1, len(para_lens)), 1) if para_lens else 0.0
    max_para = max(para_lens, default=0)
    short_30 = round(sum(1 for n in para_lens if n <= 30) / max(1, len(para_lens)), 4)
    over_80 = round(sum(1 for n in para_lens if n > 80) / max(1, len(para_lens)), 4)
    single_sent_rate = round(sum(1 for ln in lines if _is_single_sentence_para(ln)) / max(1, len(lines)), 4)

    quoted_chars = 0
    bracket_chars = 0
    spans = 0
    short_15 = 0
    curly_cnt = corner_cnt = straight_cnt = 0
    first_dialogue_char: int | None = None
    running = 0

    narration_chars = 0
    first_person_cnt = 0
    third_person_cnt = 0
    narr_em_dashes = 0

    for ln in lines:
        for m in _DIALOGUE_SPAN_RE.finditer(ln):
            if m.group(1):
                sp = m.group(1)
                inner_len = _visible_chars(sp[1:-1])
                if first_dialogue_char is None and inner_len > 0:
                    first_dialogue_char = running + _visible_chars(ln[:m.start()]) + 1
                quoted_chars += inner_len
                spans += 1
                if inner_len <= 15:
                    short_15 += 1
                if sp.startswith('“'):
                    curly_cnt += 1
                elif sp.startswith(('「', '『')):
                    corner_cnt += 1
                elif sp.startswith('"'):
                    straight_cnt += 1
            elif m.group(2):
                bracket_chars += _visible_chars(m.group(2)[1:-1])
        running += _visible_chars(ln)

        narr = _DIALOGUE_SPAN_RE.sub('', ln)
        narration_chars += _visible_chars(narr)
        first_person_cnt += narr.count('我')
        third_person_cnt += narr.count('他') + narr.count('她')
        narr_em_dashes += len(re.findall(r'(?<!—)——(?!—)', narr))

    total_quotes = curly_cnt + corner_cnt + straight_cnt
    if total_quotes == 0:
        quote_style = 'none'
    elif curly_cnt / total_quotes >= 0.85:
        quote_style = 'curly (“”)'
    elif corner_cnt / total_quotes >= 0.85:
        quote_style = 'corner (「」)'
    elif straight_cnt / total_quotes >= 0.85:
        quote_style = 'straight ("")'
    else:
        quote_style = 'mixed'

    first_per_k = round(first_person_cnt * 1000.0 / max(1, narration_chars), 2)
    pov_label = '第一人称「我」' if (first_per_k >= 6.0 or (first_person_cnt >= 10 and first_person_cnt >= third_person_cnt * 0.6)) else '第三人称'

    full_body = '\n'.join(lines)
    no_brackets = re.sub(r'【[^】\n]*】', '', full_body)
    excl_cnt = no_brackets.count('！') + no_brackets.count('!')
    quest_cnt = full_body.count('？') + full_body.count('?')
    ellipsis_cnt = len(re.findall(r'……|\.{3,}', full_body))
    prose_bal = compute_prose_stats(full_body)

    tail = full_body[-220:] if full_body else ''
    has_cliffhanger = bool(_CLIFFHANGER_END_RE.search(tail))
    hook_signals = []
    head = full_body[:700]
    if _HOOK_SYSTEM_RE.search(head):
        hook_signals.append('系统/面板亮牌')
    if _HOOK_CONFLICT_RE.search(head):
        hook_signals.append('正面冲突压迫')
    if _HOOK_SUSPENSE_RE.search(head):
        hook_signals.append('悬念/异常线索')

    return {
        'chars': body_chars,
        'stripped_author_note': stripped_note,
        'paragraphs': {
            'count': len(para_lens),
            'median_chars': med_para,
            'mean_chars': mean_para,
            'max_chars': max_para,
            'short_30_ratio': short_30,
            'over_80_ratio': over_80,
            'single_sentence_rate': single_sent_rate,
            'first_para_chars': para_lens[0] if para_lens else 0,
        },
        'dialogue': {
            'ratio': round((quoted_chars + bracket_chars) / max(1, body_chars), 4),
            'spans': spans,
            'short_15_ratio': round(short_15 / max(1, spans), 4) if spans else 0.0,
            'quote_style': quote_style,
            'first_dialogue_char': first_dialogue_char,
            'bracket_chars': bracket_chars,
        },
        'pov': {
            'label': pov_label,
            'first_person_per_k': first_per_k,
        },
        'punctuation': {
            'exclaim_question_per_1k': round((excl_cnt + quest_cnt) * 1000.0 / max(1, body_chars), 2),
            'narration_em_dash_per_1k': round(narr_em_dashes * 1000.0 / max(1, body_chars), 2),
            'ellipsis_per_1k': round(ellipsis_cnt * 1000.0 / max(1, body_chars), 2),
        },
        'prose_balance': {
            'body_action_sentence_ratio': prose_bal['body_action_sentence_ratio'],
            'causal_thought_sentence_ratio': prose_bal['causal_thought_sentence_ratio'],
            'colloquial_connective_per_1k': prose_bal['colloquial_connective_per_1k'],
            'narration_sentence_median': prose_bal['narration_sentence_median'],
        },
        'hook_signals': hook_signals,
        'has_cliffhanger_end': has_cliffhanger,
    }


def _detect_short_lead(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in (text or '').splitlines() if ln.strip()]
    chars = 0
    for idx, ln in enumerate(lines[:25], start=1):
        if _LEAD_SEP_RE.match(ln) and 20 <= chars <= 600:
            return {'placement': 'ch1-top-embedded', 'chars': chars, 'separator': ln, 'line': idx}
        chars += _visible_chars(ln)
    return {'placement': 'none', 'chars': 0, 'separator': '', 'line': None}


def analyze_book_quantitative_metrics(
    raw_text: str,
    chapters: list[dict[str, Any]] | None = None,
    *,
    title: str = '',
) -> dict[str, Any]:
    """Run 0-token deterministic Golden-3 & vertical-screen quantitative medical exam on any book."""
    text = raw_text or ''
    total_chars = _visible_chars(text)

    units: list[dict[str, Any]] = []
    if chapters:
        for idx, ch in enumerate(chapters, start=1):
            units.append({
                'id': f'U{idx:04d}',
                'level': 'chapter',
                'title': str(ch.get('title') or f'第{idx}章'),
                'start': int(ch.get('start', 0)),
                'end': int(ch.get('end', len(text))),
                'boundary_basis': 'source_heading',
            })
    else:
        matches = list(re.finditer(r'(?m)^[ \t]*(?:#{1,6}[ \t]+[^\r\n]+|第[〇零一二三四五六七八九十百千万两\d]+[卷部篇章回节][^\r\n]*)', text))
        if matches:
            for idx, m in enumerate(matches):
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                units.append({
                    'id': f'U{idx + 1:04d}',
                    'level': 'chapter',
                    'title': m.group(0).strip(),
                    'start': m.start(),
                    'end': end,
                    'boundary_basis': 'source_heading',
                })
        else:
            units = [{'id': 'U0001', 'level': 'chapter', 'title': '全文', 'start': 0, 'end': len(text), 'boundary_basis': 'source_file'}]

    story_units, paratext_units = classify_story_units(units, text)
    book_scale = 'short' if (total_chars < 25_000 and len(story_units) <= 15) else 'long'

    g3_units = story_units[:3]
    g3_chapters: list[dict[str, Any]] = []
    g3_texts: list[str] = []
    gf_reveal_ch: int | None = None

    for idx, u in enumerate(g3_units, start=1):
        ch_body = text[u['start']:u['end']]
        g3_texts.append(ch_body)
        m = _measure_block_metrics(ch_body)
        if gf_reveal_ch is None and '系统/面板亮牌' in m['hook_signals']:
            gf_reveal_ch = idx
        g3_chapters.append({
            'chapter_index': idx,
            'unit_id': u['id'],
            'title': u['title'],
            'start': u['start'],
            'end': u['end'],
            **m,
        })

    combined_g3 = _measure_block_metrics('\n\n'.join(g3_texts)) if g3_texts else _measure_block_metrics(text[:12000])
    cliff_hits = sum(1 for c in g3_chapters if c['has_cliffhanger_end'])

    # Empirical commercial benchmark deviation checks
    deviations: list[str] = []
    med_p = combined_g3['paragraphs']['median_chars']
    if med_p > 55:
        deviations.append(f'段长中位数偏长（{med_p} 字，竖屏网文常模 20–35 字），手机端可能显得密')
    elif med_p < 14 and med_p > 0:
        deviations.append(f'段长中位数极短（{med_p} 字），属超短句快切流')
    if combined_g3['paragraphs']['over_80_ratio'] > 0.25:
        deviations.append(f'>80 字长段占比达 {round(combined_g3["paragraphs"]["over_80_ratio"]*100, 1)}%，存在文字墙倾向')
    dial_r = combined_g3['dialogue']['ratio']
    if dial_r < 0.14:
        deviations.append(f'对话占比偏低（{round(dial_r*100, 1)}%，常模 18%–38%），偏叙述独白型')
    elif dial_r > 0.50:
        deviations.append(f'对话占比极高（{round(dial_r*100, 1)}%），属高密度对白驱动流')
    if g3_chapters and g3_chapters[0]['dialogue']['first_dialogue_char'] and g3_chapters[0]['dialogue']['first_dialogue_char'] > 600:
        deviations.append(f'第1章首对话出现偏晚（第 {g3_chapters[0]["dialogue"]["first_dialogue_char"]} 字）')
    if g3_chapters and cliff_hits < len(g3_chapters):
        deviations.append(f'黄金三章章尾卡点率 {cliff_hits}/{len(g3_chapters)}，建议留意未卡点章的追读转化')

    return {
        'title': title,
        'book_scale': book_scale,
        'total_visible_chars': total_chars,
        'story_chapters_count': len(story_units),
        'skipped_paratext_count': len(paratext_units),
        'golden_three_summary': combined_g3,
        'golden_three_chapters': g3_chapters,
        'golden_finger_signal_chapter': gf_reveal_ch,
        'golden_three_cliffhanger_rate': f'{cliff_hits}/{len(g3_chapters)}' if g3_chapters else '0/0',
        'short_lead': _detect_short_lead(g3_texts[0] if g3_texts else text) if book_scale == 'short' else None,
        'benchmark_deviations': deviations,
    }


def _guess_top_character_names(text: str, limit: int = 5) -> list[str]:
    """Heuristically spot frequent 2-3 char Chinese character names in subject position."""
    strict_pat = re.compile(
        r'(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?=(?:说道|笑道|问道|冷笑道|开口|皱眉|抬头|低头|看向|转身|伸手|一愣|沉默|心里|暗想))'
    )
    broad_pat = re.compile(
        r'(?:^|[\n，。！？：“”「」\s])([\u4e00-\u9fff]{2,3})(?=(?:把|没|不|抬|退|拉|推|走|站|坐|拿|摸|盯|扫|看|说|笑|问|冷|咬|皱|低|转|伸|沉|指|眉|眼|手|脚|脸|嘴|轻|缓|猛|忽|微|径|顺|反|刚|正|便|却|只))'
    )
    sample = (text or '')[:30000]
    counts: Counter[str] = Counter()
    for m in strict_pat.finditer(sample):
        nm = m.group(1)
        if nm not in _COMMON_NON_NAMES:
            counts[nm] += 2
    for m in broad_pat.finditer(sample):
        nm = m.group(1)
        if nm not in _COMMON_NON_NAMES:
            counts[nm] += 1
    return [nm for nm, c in counts.most_common(limit) if c >= 3]


def _pick_contiguous_slice(chapter_text: str, *, target_len: int = 260, prefer_tail: bool = False) -> tuple[int, int] | None:
    """Pick a clean paragraph-aligned 160–340 char contiguous slice from a chapter."""
    raw = chapter_text or ''
    if len(raw) < 140:
        return None
    # Split into paragraph spans with exact offsets
    spans: list[tuple[int, int]] = []
    pos = 0
    for m in re.finditer(r'[^\n]+', raw):
        s, e = m.start(), m.end()
        line = raw[s:e].strip()
        if not line or re.match(r'^(?:#{1,6}\s|第[〇零一二三四五六七八九十百千万两\d]+[章节回])', line):
            continue
        spans.append((s, e))
        pos = e
    if not spans:
        return None

    order = list(range(len(spans) - 1, -1, -1)) if prefer_tail else list(range(len(spans)))
    for start_idx in order:
        if prefer_tail:
            # Build backward window ending at start_idx
            s_off = spans[start_idx][0]
            e_off = spans[start_idx][1]
            cur = start_idx - 1
            while cur >= 0 and (e_off - s_off) < 180:
                cand_s = spans[cur][0]
                if (e_off - cand_s) > 360:
                    break
                s_off = cand_s
                cur -= 1
            if 130 <= (e_off - s_off) <= 380:
                return s_off, e_off
        else:
            s_off = spans[start_idx][0]
            e_off = spans[start_idx][1]
            cur = start_idx + 1
            while cur < len(spans) and (e_off - s_off) < target_len:
                cand_e = spans[cur][1]
                if (cand_e - s_off) > 380:
                    break
                e_off = cand_e
                cur += 1
            if 130 <= (e_off - s_off) <= 380:
                return s_off, e_off
    return None


def harvest_verified_excerpts_from_book(
    conn: sqlite3.Connection,
    *,
    book_id: str,
    raw_text: str,
    chapters: list[dict[str, Any]] | None,
    type_tags: list[str] | tuple[str, ...],
    known_names: list[str] | tuple[str, ...] | None = None,
    max_excerpts: int = 3,
) -> list[dict[str, Any]]:
    """Zero-token harvester: extracts 1–3 verbatim slices from Ch1–3, anonymizes names,
    gates them through 3-check zero-alert verification, and saves clean slices to `library.db`!
    """
    units = [
        {'id': f'U{i:04d}', 'level': 'chapter', 'title': str(c.get('title') or f'第{i}章'),
         'start': int(c.get('start', 0)), 'end': int(c.get('end', len(raw_text))), 'boundary_basis': 'source_heading'}
        for i, c in enumerate(chapters or (), start=1)
    ] or [{'id': 'U0001', 'level': 'chapter', 'title': '全文', 'start': 0, 'end': len(raw_text), 'boundary_basis': 'source_file'}]

    story_units, _ = classify_story_units(units, raw_text)
    names = list(known_names) if known_names else _guess_top_character_names(raw_text)

    plans = [
        (0, False, 'opening_hook', '学习开篇入局节奏、竖屏断行与前段信息推进方式'),
        (min(1, len(story_units) - 1), False, 'confrontation', '学习现场对白推拉、人物利害交锋与情绪节奏'),
        (min(2, len(story_units) - 1), True, 'emotional_shock', '学习章末转折力度与断章钩子收束节奏'),
    ]
    saved: list[dict[str, Any]] = []
    used_hashes: set[str] = set()

    for unit_idx, prefer_tail, sf, learn in plans:
        if len(saved) >= max_excerpts or unit_idx >= len(story_units):
            break
        u = story_units[unit_idx]
        ch_text = raw_text[u['start']:u['end']]
        span = _pick_contiguous_slice(ch_text, prefer_tail=prefer_tail)
        if span is None:
            continue
        abs_start = u['start'] + span[0]
        abs_end = u['start'] + span[1]
        extracted = extract_and_verify_corpus_excerpt(
            raw_text, abs_start, abs_end,
            book_id=book_id,
            chapter_index=unit_idx + 1,
            type_tags=list(type_tags),
            scene_function=sf,
            learn_what=learn,
            do_not_copy='仅学习句式呼吸、口语衔接与段落节奏，严禁照搬原段设定、物件与具体事件。',
            known_names=names,
            min_chars=120,
            max_chars=420,
        )
        if not extracted['passed']:
            continue
        sha = extracted['record']['source_sha256']
        if sha in used_hashes:
            continue
        used_hashes.add(sha)
        saved.append(save_verified_excerpt(conn, extracted))

    return saved


def _build_offline_deconstruct_pack(quant: dict[str, Any], book_title: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Deterministic zero-token structural skeleton when running fast exam without LLM calls."""
    g3_ch = quant.get('golden_three_chapters') or []
    chapters_out = []
    for ch in g3_ch:
        sigs = '、'.join(ch.get('hook_signals') or ()) or '实景切入'
        chapters_out.append({
            'chapter': ch['chapter_index'],
            'title': ch['title'],
            'chars': ch['chars'],
            'hook_method': sigs,
            'cliffhanger': '检测到章尾硬卡点信号' if ch.get('has_cliffhanger_end') else '章尾较平缓',
            'dialogue_ratio': ch['dialogue']['ratio'],
            'median_para_chars': ch['paragraphs']['median_chars'],
            'transferable': f'单章 {ch["chars"]} 字、段均中位 {ch["paragraphs"]["median_chars"]} 字、对话占比 {round(ch["dialogue"]["ratio"]*100)}%。',
        })
    golden_three = {
        'mode': 'deterministic_exam',
        'overall_verdict': (
            f'《{book_title}》量化体检完成（{quant["book_scale"]}体量，正文 {quant["story_chapters_count"]} 章，'
            f'黄金三章卡点率 {quant["golden_three_cliffhanger_rate"]}）。'
        ),
        'golden_finger_chapter': quant.get('golden_finger_signal_chapter'),
        'chapters': chapters_out,
    }
    rhythm = {
        'mode': 'deterministic_exam',
        'story_framework': '短篇强反转结构' if quant['book_scale'] == 'short' else '长篇黄金三章递进结构',
        'core_engine': '以客观量化体检为基线；可点击「AI 黄金三章深拆与情绪模块」抽取完整 RH 爽点循环与 EM 模块卡。',
        'rh_loops': [],
        'tr_triggers': [],
    }
    return golden_three, rhythm, []


def run_book_deconstruct_pack(
    conn: sqlite3.Connection,
    *,
    book_id: str,
    book_title: str,
    raw_text: str,
    chapters: list[dict[str, Any]] | None,
    confirmed_types: list[str] | tuple[str, ...],
    harvest_excerpts: bool = True,
    backfill_topics: bool = True,
    provider: LLMProvider | None = None,
    model: str = '',
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run upgraded book deconstruction (0-token quantitative exam + verified excerpt harvest +
    optional LLM Golden-3 / RH-TR rhythm / EM emotion module extraction + topic verification backfill).
    """
    ensure_book_deconstruct_table(conn)
    quant = analyze_book_quantitative_metrics(raw_text, chapters, title=book_title)
    harvested = (
        harvest_verified_excerpts_from_book(
            conn, book_id=book_id, raw_text=raw_text, chapters=chapters, type_tags=confirmed_types,
        )
        if harvest_excerpts else []
    )
    golden_three, rhythm_registry, emotion_modules = _build_offline_deconstruct_pack(quant, book_title)

    # Optional LLM deep Golden-3 + RH/TR + EM-card extraction
    if provider is not None and model:
        g3_chunks = []
        for ch in (quant.get('golden_three_chapters') or ())[:3]:
            chunk_txt = raw_text[ch['start']:min(ch['end'], ch['start'] + 4500)]
            g3_chunks.append(f'### 第{ch["chapter_index"]}章 {ch["title"]}（{ch["chars"]}字）\n{chunk_txt}')
        user_msg = (
            f'书名：《{book_title}》｜体量：{quant["book_scale"]}｜正文总章数：{quant["story_chapters_count"]}\n'
            f'【0-Token 量化体检摘要】\n{json.dumps(quant["golden_three_summary"], ensure_ascii=False)}\n'
            f'偏离提醒：{"；".join(quant["benchmark_deviations"]) or "无明显偏离"}\n\n'
            f'【黄金三章/核心原文】\n' + '\n\n'.join(g3_chunks)
        )
        gen = send_model(
            provider,
            [
                {'role': 'system', 'content': DEEP_DECONSTRUCT_SYSTEM_PROMPT},
                {'role': 'user', 'content': user_msg[:18000]},
            ],
            model,
            dict(params or {}),
            allow_continuation=False,
            max_empty_retries=(1 if provider.name != 'fake' else 0),
        )
        m = re.search(r'\{[\s\S]*\}', gen.text or '')
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed.get('golden_three'), dict):
                    golden_three = {**parsed['golden_three'], 'mode': 'llm_deep'}
                if isinstance(parsed.get('rhythm_registry'), dict):
                    rhythm_registry = {**parsed['rhythm_registry'], 'mode': 'llm_deep'}
                if isinstance(parsed.get('emotion_modules'), list):
                    emotion_modules = [row for row in parsed['emotion_modules'] if isinstance(row, dict)][:10]
            except ValueError:
                pass

    # Backfill any pending Market Radar Topic Decisions matching this benchmark book or genre!
    ev_summary = (
        f'{quant["book_scale"]}篇实测段长中位 {quant["golden_three_summary"]["paragraphs"]["median_chars"]} 字、'
        f'对话占 {round(quant["golden_three_summary"]["dialogue"]["ratio"]*100)}%、'
        f'黄金三章卡点率 {quant["golden_three_cliffhanger_rate"]}，'
        f'采摘三检实文范例 {len(harvested)} 段、提炼 EM 情绪模块 {len(emotion_modules)} 张。'
    )
    backfilled = (
        backfill_topic_verification(
            conn,
            book_id=book_id,
            book_title=book_title,
            confirmed_types=list(confirmed_types),
            evidence_summary=ev_summary,
            verified=True,
        )
        if backfill_topics else []
    )

    ts = timestamp()
    conn.execute(
        '''INSERT OR REPLACE INTO book_deconstruct_artifacts
           (book_id, book_scale, quantitative_json, golden_three_json, rhythm_registry_json,
            emotion_modules_json, harvested_excerpts_json, backfilled_topic_ids_json, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (
            book_id, quant['book_scale'], encode(quant), encode(golden_three),
            encode(rhythm_registry), encode(emotion_modules),
            encode([{'id': h['id'], 'scene_function': h['scene_function'], 'scene_function_label': h['scene_function_label']} for h in harvested]),
            encode([t['id'] for t in backfilled]), ts,
        ),
    )
    return {
        'book_id': book_id,
        'book_scale': quant['book_scale'],
        'quantitative': quant,
        'golden_three': golden_three,
        'rhythm_registry': rhythm_registry,
        'emotion_modules': emotion_modules,
        'harvested_excerpts': harvested,
        'backfilled_topics': backfilled,
        'updated_at': ts,
    }


def get_book_deconstruct_artifact(conn: sqlite3.Connection, book_id: str) -> dict[str, Any] | None:
    ensure_book_deconstruct_table(conn)
    row = conn.execute('SELECT * FROM book_deconstruct_artifacts WHERE book_id=?', (book_id,)).fetchone()
    if row is None:
        return None
    return {
        'book_id': row['book_id'],
        'book_scale': row['book_scale'],
        'quantitative': json.loads(row['quantitative_json'] or '{}'),
        'golden_three': json.loads(row['golden_three_json'] or '{}'),
        'rhythm_registry': json.loads(row['rhythm_registry_json'] or '{}'),
        'emotion_modules': json.loads(row['emotion_modules_json'] or '[]'),
        'harvested_excerpts': json.loads(row['harvested_excerpts_json'] or '[]'),
        'backfilled_topic_ids': json.loads(row['backfilled_topic_ids_json'] or '[]'),
        'updated_at': row['updated_at'],
    }
