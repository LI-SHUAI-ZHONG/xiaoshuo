"""Living Craft Evolution Engine — 5th Dynamic Layer of the 4-Pillar Craft Specs.

Turns static pre-writing craft specifications into a living self-evolving system:
  1. Author-Edit Diff Auto-Contrast Harvester: compares AI drafts vs manual author edits,
     extracting high-value polish paragraphs (25%-72% diff) as `❌ AI原稿 / ✅ 作者亲改`
     micro-contrasts tagged by `scene_function` (confirmed by author before promotion).
  2. Recurring Rejection/Override -> Craft Redline Promoter: surfaces >=3 repeated
     rejections/overrides as 1-click proposals to codify into `craft_specs` with provenance.
  3. Periodic Style Fingerprint Drift Monitor: tracks 6 objective prose metrics across
     accepted chapters vs the baseline window (Ch 1-10 or author-pinned peak chapters)
     to catch slow multi-dozen-chapter drift before the book loses its voice.
"""
from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import json
import re
from typing import Any
from uuid import uuid4

from nw.craft_specs import load_craft_spec, save_craft_spec
from nw.craft_specs_base import CRAFT_DOMAINS, DOMAIN_META
from nw.override_ledger import mark_overrides_promoted, summarize_recurring_patterns
from nw.pre_review_gate import compute_prose_stats
from nw.store import Store, now
from nw.story_state import current_head, revision_state
from nw.voice_specs import SCENE_FUNCTION_LABELS, infer_scene_function, load_book_voice_spec, save_book_voice_spec

_MAX_LEARNED_CONTRASTS = 12
_MAX_LEARNED_REDLINES = 15
_PHRASE_RE = re.compile(r'[\u4e00-\u9fff]{2,4}')
_PHRASE_STOP = frozenset({
    '自己', '没有', '不是', '什么', '知道', '时候', '已经', '可以', '不能', '一个', '这个', '那个',
    '他们', '她们', '我们', '你们', '虽然', '但是', '因为', '所以', '不过', '还是', '只是', '就是',
    '看着', '说道', '问道', '笑了', '点了', '摇了', '微微', '轻轻', '缓缓', '慢慢', '突然', '忽然',
})


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r'\n+', (text or '').strip()) if p.strip()]


def _infer_polish_why(bad_ai: str, good_author: str) -> str:
    b_stats = compute_prose_stats(bad_ai)
    g_stats = compute_prose_stats(good_author)
    reasons: list[str] = []
    if b_stats['cliche_hits'] > g_stats['cliche_hits']:
        reasons.append('删去了 AI 套话与抽象情绪标签')
    if g_stats['dialogue_ratio'] - b_stats['dialogue_ratio'] >= 0.15:
        reasons.append('增强了对白现场感与人物脾气')
    if b_stats['avg_sentence_len'] - g_stats['avg_sentence_len'] >= 5.0:
        reasons.append('收紧了句长与动作节奏')
    elif g_stats['avg_sentence_len'] - b_stats['avg_sentence_len'] >= 5.0:
        reasons.append('理顺了碎短句，改为更连贯的人话语流')
    if len(good_author) < len(bad_ai) * 0.85:
        reasons.append('砍掉了冗余解释，信息更利落')
    if not reasons:
        reasons.append('作者亲改优化了用词质感与现场节奏')
    return '；'.join(reasons[:2]) + '。'


def extract_author_edit_contrasts(
    ai_text: str,
    author_text: str,
    *,
    scene_function: str = 'dialogue_daily',
    chapter_index: int | None = None,
    scene_id: str = '',
    max_candidates: int = 2,
) -> list[dict[str, Any]]:
    """Extract high-signal ❌ AI draft vs ✅ Author-edited micro-contrast candidates."""
    ai_paras = _split_paragraphs(ai_text)
    au_paras = _split_paragraphs(author_text)
    if not ai_paras or not au_paras:
        return []

    sf = scene_function if scene_function in SCENE_FUNCTION_LABELS else 'dialogue_daily'
    candidates: list[dict[str, Any]] = []
    used_ai: set[int] = set()

    # Align each author paragraph to its best matching AI paragraph
    for au_idx, au_p in enumerate(au_paras):
        if not (25 <= len(au_p) <= 280):
            continue
        best_idx = -1
        best_sim = 0.0
        for ai_idx, ai_p in enumerate(ai_paras):
            if ai_idx in used_ai or not (25 <= len(ai_p) <= 300):
                continue
            sim = SequenceMatcher(None, ai_p, au_p).ratio()
            if sim > best_sim:
                best_sim = sim
                best_idx = ai_idx
        # Sweet spot: 25%-72% edit distance (0.28 <= similarity <= 0.75) -> real polish, not typo or unrelated text
        if best_idx >= 0 and 0.28 <= best_sim <= 0.75:
            used_ai.add(best_idx)
            ai_p = ai_paras[best_idx]
            change_ratio = round(1.0 - best_sim, 3)
            candidates.append({
                'candidate_id': f'alc-{uuid4().hex[:10]}',
                'scene_function': sf,
                'scene_function_label': SCENE_FUNCTION_LABELS.get(sf, sf),
                'label': f'作者亲改示范 · {SCENE_FUNCTION_LABELS.get(sf, sf)}',
                'bad_ai': ai_p[:240],
                'target_voice': au_p[:240],
                'why': _infer_polish_why(ai_p, au_p),
                'change_ratio': change_ratio,
                'chapter_index': chapter_index,
                'scene_id': scene_id,
                'source': 'author_edit',
            })

    # Prefer candidates closest to ~45% edit ratio (strongest polish signal)
    candidates.sort(key=lambda c: abs(c['change_ratio'] - 0.45))
    return candidates[:max(1, int(max_candidates))]


def detect_author_edit_candidates(
    store: Store,
    *,
    scene_id: str,
    branch: str = 'main',
    max_candidates: int = 2,
) -> list[dict[str, Any]]:
    """Inspect a scene's draft history and return harvestable contrasts if the latest draft is a manual author edit."""
    drafts = store.drafts(scene_id)
    if len(drafts) < 2:
        return []
    latest = drafts[-1]
    latest_run = store.get('run', latest.run_id)
    if latest_run.provider != 'author':
        return []
    # Find most recent non-author AI draft before latest
    ai_draft = None
    for d in reversed(drafts[:-1]):
        r = store.get('run', d.run_id)
        if r.provider != 'author' and (d.text or '').strip():
            ai_draft = d
            break
    if ai_draft is None:
        return []
    scene = store.get('scene', scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    try:
        card_body = json.loads(scene.card_json)
    except ValueError:
        card_body = {}
    sf = infer_scene_function(card_body, chapter_index=chapter.index, scene_index=scene.index)
    return extract_author_edit_contrasts(
        ai_draft.text, latest.text,
        scene_function=sf,
        chapter_index=chapter.index,
        scene_id=scene_id,
        max_candidates=max_candidates,
    )


def accept_learned_contrast(store: Store, candidate: dict[str, Any]) -> dict[str, Any]:
    """Persist an author-confirmed ❌ AI / ✅ Author contrast into `voice_spec.json`."""
    bad = str(candidate.get('bad_ai') or '').strip()[:240]
    good = str(candidate.get('target_voice') or '').strip()[:240]
    if not bad or not good:
        raise ValueError('语感微对照必须同时包含 AI 原句与作者亲改句')
    sf = str(candidate.get('scene_function') or 'dialogue_daily').strip()
    if sf not in SCENE_FUNCTION_LABELS:
        sf = 'dialogue_daily'
    spec = load_book_voice_spec(store)
    if spec is None:
        from nw.voice_specs import compile_book_voice_spec
        spec = compile_book_voice_spec((), enabled=True)
    learned = list(spec.get('learned_contrasts') or [])
    # Deduplicate by target_voice
    learned = [row for row in learned if isinstance(row, dict) and row.get('target_voice') != good]
    entry = {
        'id': str(candidate.get('candidate_id') or f'alc-{uuid4().hex[:10]}'),
        'scene_function': sf,
        'label': str(candidate.get('label') or f'作者亲改示范 · {SCENE_FUNCTION_LABELS[sf]}')[:60],
        'bad_ai': bad,
        'target_voice': good,
        'why': str(candidate.get('why') or _infer_polish_why(bad, good))[:160],
        'chapter_index': candidate.get('chapter_index'),
        'source': 'author_edit',
        'learned_at': now(),
    }
    learned.insert(0, entry)
    spec['learned_contrasts'] = learned[:_MAX_LEARNED_CONTRASTS]
    save_book_voice_spec(store, spec)
    return {'entry': entry, 'learned_count': len(spec['learned_contrasts']), 'voice_spec': spec}


def remove_learned_contrast(store: Store, contrast_id: str) -> dict[str, Any]:
    spec = load_book_voice_spec(store)
    if spec is None:
        return {'removed': False, 'learned_count': 0}
    before = list(spec.get('learned_contrasts') or [])
    after = [row for row in before if isinstance(row, dict) and row.get('id') != contrast_id]
    spec['learned_contrasts'] = after
    save_book_voice_spec(store, spec)
    return {'removed': len(after) < len(before), 'learned_count': len(after)}


def list_promotion_proposals(store: Store, *, branch: str = 'main', min_count: int = 3) -> list[dict[str, Any]]:
    """List repeated author override/rejection patterns eligible for promotion into craft specs."""
    return summarize_recurring_patterns(store, branch_id=branch, min_count=min_count)


def promote_pattern_to_craft_spec(
    store: Store,
    *,
    target_domain: str,
    redline_text: str,
    override_ids: list[str] | None = None,
    chapters: list[int] | None = None,
    pattern_key: str = '',
) -> dict[str, Any]:
    """Promote a recurring author calibration into the target domain's executable craft spec."""
    dom = str(target_domain or 'voice').strip()
    if dom not in CRAFT_DOMAINS:
        raise ValueError(f'未知的工艺基座域: {dom}')
    rule = str(redline_text or '').strip()[:200]
    if not rule:
        raise ValueError('升格红线文本不能为空')

    spec = load_craft_spec(store, dom)
    if spec is None:
        from nw.craft_specs import compile_craft_spec
        spec = compile_craft_spec(dom, (), enabled=True)

    learned_redlines = list(spec.get('learned_redlines') or [])
    entry = {
        'id': f'lrl-{uuid4().hex[:10]}',
        'rule': rule,
        'pattern_key': pattern_key,
        'chapters': list(chapters or ()),
        'promoted_at': now(),
    }
    learned_redlines = [r for r in learned_redlines if isinstance(r, dict) and r.get('rule') != rule]
    learned_redlines.insert(0, entry)
    spec['learned_redlines'] = learned_redlines[:_MAX_LEARNED_REDLINES]

    # Also append directly to active redlines list so Steps 00-16 consume it immediately
    redline_field = 'drift_redlines' if dom == 'voice' else 'anti_drift_redlines'
    active_list = list(spec.get(redline_field) or [])
    if rule not in active_list:
        active_list.append(rule)
    spec[redline_field] = active_list[:14]

    save_craft_spec(store, dom, spec)
    promoted_count = mark_overrides_promoted(store, list(override_ids or ()))
    return {
        'domain': dom,
        'domain_name': DOMAIN_META[dom]['name'],
        'entry': entry,
        'overrides_marked_promoted': promoted_count,
        'learned_redlines_count': len(spec['learned_redlines']),
    }


def _accepted_chapter_texts(store: Store, branch: str = 'main') -> dict[int, str]:
    """Collect accepted prose concatenated by chapter index on the selected branch."""
    if not store.managed_story():
        return {}
    head = current_head(store, branch)
    snapshot = revision_state(store, head)
    slots = snapshot.get('slots') or {}
    chapters = {c.id: c.index for c in store.list('chapter')}
    by_ch: dict[int, list[tuple[int, str]]] = {}
    for sc in store.list('scene'):
        slot = slots.get(sc.id)
        if not slot or not slot.get('draft_id'):
            continue
        ch_idx = chapters.get(sc.chapter_id)
        if ch_idx is None:
            continue
        draft = store.get('draft', slot['draft_id'])
        if (draft.text or '').strip():
            by_ch.setdefault(ch_idx, []).append((sc.index, draft.text.strip()))
    return {
        ch_idx: '\n\n'.join(text for _, text in sorted(parts, key=lambda r: r[0]))
        for ch_idx, parts in sorted(by_ch.items())
    }


def compute_chapter_range_fingerprint(
    store: Store,
    branch: str = 'main',
    *,
    start_chapter: int,
    end_chapter: int,
) -> dict[str, Any]:
    """Compute objective statistical prose fingerprint across an accepted chapter window."""
    ch_texts = _accepted_chapter_texts(store, branch)
    selected = [(idx, txt) for idx, txt in ch_texts.items() if start_chapter <= idx <= end_chapter]
    if not selected:
        return {
            'range_start': start_chapter,
            'range_end': end_chapter,
            'chapter_count': 0,
            'metrics': compute_prose_stats(''),
            'top_phrases': [],
        }
    combined = '\n\n'.join(txt for _, txt in selected)
    metrics = compute_prose_stats(combined)
    tokens = [t for t in _PHRASE_RE.findall(combined) if t not in _PHRASE_STOP]
    top_phrases = [{'phrase': p, 'count': c} for p, c in Counter(tokens).most_common(15)]
    return {
        'range_start': selected[0][0],
        'range_end': selected[-1][0],
        'chapter_count': len(selected),
        'metrics': metrics,
        'top_phrases': top_phrases,
    }


def pin_style_baseline(
    store: Store,
    *,
    branch: str = 'main',
    start_chapter: int = 1,
    end_chapter: int = 10,
) -> dict[str, Any]:
    """Compute and pin a chapter range as the authoritative style baseline in SQLite."""
    fp = compute_chapter_range_fingerprint(store, branch, start_chapter=start_chapter, end_chapter=end_chapter)
    if fp['chapter_count'] == 0:
        raise ValueError(f'第 {start_chapter}–{end_chapter} 章范围内尚无已接受正文，无法锁定文体基线')
    ident = f'sds-{uuid4().hex[:12]}'
    ts = now()
    payload = {'metrics': fp['metrics'], 'top_phrases': fp['top_phrases'], 'chapter_count': fp['chapter_count']}
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute('UPDATE style_drift_snapshots SET is_baseline=0 WHERE branch_id=?', (branch,))
        store.connection.execute(
            '''INSERT INTO style_drift_snapshots(id, branch_id, range_start, range_end, is_baseline, metrics_json, created_at)
               VALUES (?,?,?,?,1,?,?)''',
            (ident, branch, fp['range_start'], fp['range_end'], json.dumps(payload, ensure_ascii=False), ts),
        )
    return {'id': ident, 'branch_id': branch, 'is_baseline': True, **fp, 'created_at': ts}


def check_style_drift(
    store: Store,
    *,
    branch: str = 'main',
    window_size: int = 10,
    drift_threshold: float = 0.25,
) -> dict[str, Any]:
    """Compare recent accepted chapters against the pinned (or early auto) style baseline."""
    ch_texts = _accepted_chapter_texts(store, branch)
    chapter_indices = sorted(ch_texts.keys())
    if len(chapter_indices) < 2:
        return {
            'status': 'insufficient_data',
            'chapter_count': len(chapter_indices),
            'baseline': None,
            'current_window': None,
            'drifts': [],
            'summary': '已接受章节不足 2 章，积累更多正文后将自动监测文体漂移。',
        }

    row = store.connection.execute(
        'SELECT * FROM style_drift_snapshots WHERE branch_id=? AND is_baseline=1 ORDER BY rowid DESC LIMIT 1',
        (branch,),
    ).fetchone()
    if row is not None:
        base_payload = json.loads(row['metrics_json'])
        baseline = {
            'id': row['id'],
            'pinned': True,
            'range_start': row['range_start'],
            'range_end': row['range_end'],
            'chapter_count': base_payload.get('chapter_count', 0),
            'metrics': base_payload.get('metrics') or {},
            'top_phrases': base_payload.get('top_phrases') or [],
        }
    else:
        # Auto early baseline: first half up to window_size chapters
        base_end_idx = min(len(chapter_indices) // 2, max(1, window_size))
        b_start, b_end = chapter_indices[0], chapter_indices[max(0, base_end_idx - 1)]
        fp = compute_chapter_range_fingerprint(store, branch, start_chapter=b_start, end_chapter=b_end)
        baseline = {'id': None, 'pinned': False, **fp}

    # Recent window: latest `window_size` chapters (or second half if short book)
    rec_start_pos = max(len(chapter_indices) - window_size, len(chapter_indices) // 2)
    c_start, c_end = chapter_indices[rec_start_pos], chapter_indices[-1]
    current = compute_chapter_range_fingerprint(store, branch, start_chapter=c_start, end_chapter=c_end)

    bm = baseline['metrics']
    cm = current['metrics']
    drifts: list[dict[str, Any]] = []
    comparisons = (
        ('avg_sentence_len', '平均句长', '字'),
        ('dialogue_ratio', '对白占比', ''),
        ('avg_paragraph_chars', '段均字数', '字'),
        ('short_sentence_ratio', '短句占比', ''),
    )
    for key, label, unit in comparisons:
        bv = float(bm.get(key) or 0.0)
        cv = float(cm.get(key) or 0.0)
        if bv <= 0.01:
            continue
        rel = (cv - bv) / bv
        if abs(rel) >= drift_threshold:
            direction = '上升' if rel > 0 else '下降'
            pct = abs(round(rel * 100))
            if key in ('dialogue_ratio', 'short_sentence_ratio'):
                b_str, c_str = f'{bv * 100:.0f}%', f'{cv * 100:.0f}%'
            else:
                b_str, c_str = f'{bv:.1f}{unit}', f'{cv:.1f}{unit}'
            drifts.append({
                'metric': key,
                'label': label,
                'baseline': bv,
                'current': cv,
                'delta_pct': round(rel * 100, 1),
                'message': f'近期{label}较基线{direction} {pct}%（{b_str} → {c_str}）。',
            })

    b_cliche = float(bm.get('cliche_density_per_1k') or 0.0)
    c_cliche = float(cm.get('cliche_density_per_1k') or 0.0)
    if c_cliche >= 1.5 and c_cliche > b_cliche + 0.8:
        drifts.append({
            'metric': 'cliche_density_per_1k',
            'label': 'AI 套话密度',
            'baseline': b_cliche,
            'current': c_cliche,
            'delta_pct': round(((c_cliche - b_cliche) / max(0.2, b_cliche)) * 100, 1),
            'message': f'近期千字 AI 套话密度升高（{b_cliche:.2f} → {c_cliche:.2f}/千字），建议回拉语感校准。',
        })

    status = 'drift_detected' if drifts else 'stable'
    summary = (
        f'检测到 {len(drifts)} 项文体指标漂移（第 {c_start}–{c_end} 章 vs 基线第 {baseline["range_start"]}–{baseline["range_end"]} 章），'
        '可选择加强语感红线回拉，或更新基线承认风格演进。'
        if drifts else
        f'第 {c_start}–{c_end} 章文体指纹与基线（第 {baseline["range_start"]}–{baseline["range_end"]} 章）保持稳定。'
    )
    return {
        'status': status,
        'chapter_count': len(chapter_indices),
        'baseline': baseline,
        'current_window': current,
        'drifts': drifts,
        'summary': summary,
    }
