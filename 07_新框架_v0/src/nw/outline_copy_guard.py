"""Zero-Token Deterministic Outline-Copy Guard (Fusion G).

Detects when a drafted scene copies contiguous prose (>= 16 Chinese characters after
stripping punctuation and whitespace) directly from the scene card, beat outline, or
situation card — while surgically excising ONLY exact explicitly authorized verbatim
anchors (e.g., locked key lines or dialogue anchors) so adjacent unapproved copying
is never pardoned.
"""
from __future__ import annotations

import re
from typing import Any

_HAN_RE = re.compile(r'[\u4e00-\u9fff]')

# Explicit markers in an outline / scene card that authorize a verbatim line or quote
_ANCHOR_LINE_RE = re.compile(
    r'(?:原话|原句|金句|必须原样保留|原样保留|台词锚点|保留原句|指定台词|锚点原句)\s*[:：]\s*([^\n]{4,180})'
)
_QUOTED_SPAN_RE = re.compile(r'“([^”\n]{4,160})”|「([^」\n]{4,160})」|『([^』\n]{4,160})』|"([^"\n]{4,160})"')


def han_with_positions(text: str) -> tuple[str, list[int]]:
    """Extract only CJK ideographs along with each character's original offset."""
    chars: list[str] = []
    positions: list[int] = []
    for idx, ch in enumerate(text or ''):
        if '\u4e00' <= ch <= '\u9fff':
            chars.append(ch)
            positions.append(idx)
    return ''.join(chars), positions


def extract_verbatim_anchors(
    outline_text: str,
    extra_anchors: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Extract explicitly authorized verbatim anchor strings from an outline or scene card."""
    anchors: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        cleaned = str(raw or '').strip().strip('“”「」『』"\' ')
        if len(cleaned) >= 4 and cleaned not in seen:
            seen.add(cleaned)
            anchors.append(cleaned)

    for item in (extra_anchors or ()):
        _add(item)

    if outline_text:
        for m in _ANCHOR_LINE_RE.finditer(outline_text):
            clause = m.group(1).strip()
            quoted_found = False
            for qm in _QUOTED_SPAN_RE.finditer(clause):
                q = next((g for g in qm.groups() if g), '')
                if q:
                    _add(q)
                    quoted_found = True
            if not quoted_found:
                # Strip trailing parenthetical annotations like （此处必出）
                plain = re.sub(r'[（(][^）)]{1,40}[）)]\s*$', '', clause).strip()
                _add(plain)

    # Sort longest first so longer anchors are excised before shorter substrings
    anchors.sort(key=len, reverse=True)
    return anchors


def split_by_anchors(text: str, anchors: list[str]) -> tuple[list[tuple[int, str]], int]:
    """Surgically excise ONLY exact occurrences of authorized anchors from `text`.

    Returns:
      - segments: list of (original_start_offset, unanchored_substring)
      - excised_count: number of exact anchor spans excised

    Never pardons a whole sentence or paragraph around an anchor: any text before or
    after the exact anchor span remains intact as a separate segment to be audited.
    """
    if not text:
        return [], 0
    if not anchors:
        return [(0, text)], 0

    occupied: list[tuple[int, int]] = []
    for anchor in sorted({a for a in anchors if len(a) >= 4}, key=len, reverse=True):
        start = 0
        alen = len(anchor)
        while True:
            pos = text.find(anchor, start)
            if pos < 0:
                break
            end = pos + alen
            if not any(pos < b and a < end for a, b in occupied):
                occupied.append((pos, end))
            start = pos + 1

    if not occupied:
        return [(0, text)], 0

    occupied.sort()
    segments: list[tuple[int, str]] = []
    cursor = 0
    for a, b in occupied:
        if a > cursor:
            segments.append((cursor, text[cursor:a]))
        cursor = max(cursor, b)
    if cursor < len(text):
        segments.append((cursor, text[cursor:]))
    return segments, len(occupied)


def _find_overlap_of_len(han_a: str, han_b: str, length: int) -> tuple[int, int] | None:
    """Return first (pos_a, pos_b) where han_a and han_b share a substring of exact `length`."""
    if length <= 0 or len(han_a) < length or len(han_b) < length:
        return None
    index_b: dict[str, int] = {}
    limit_b = len(han_b) - length + 1
    for j in range(limit_b):
        sub = han_b[j:j + length]
        if sub not in index_b:
            index_b[sub] = j
    limit_a = len(han_a) - length + 1
    for i in range(limit_a):
        sub = han_a[i:i + length]
        if sub in index_b:
            return i, index_b[sub]
    return None


def _longest_common_han_substring(han_a: str, han_b: str, min_han: int) -> tuple[int, int, int] | None:
    """Binary-search the longest common substring of length >= min_han.

    Returns (pos_a, pos_b, length) or None.
    """
    max_possible = min(len(han_a), len(han_b))
    if max_possible < min_han:
        return None
    if _find_overlap_of_len(han_a, han_b, min_han) is None:
        return None

    lo, hi = min_han, max_possible
    best: tuple[int, int, int] | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        found = _find_overlap_of_len(han_a, han_b, mid)
        if found is not None:
            best = (found[0], found[1], mid)
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _extract_non_overlapping_hits(
    seg_text: str,
    seg_offset: int,
    full_draft: str,
    outline_text: str,
    outline_han: str,
    outline_pos: list[int],
    *,
    min_han: int,
    max_hits: int,
) -> list[dict[str, Any]]:
    seg_han, seg_pos = han_with_positions(seg_text)
    if len(seg_han) < min_han or len(outline_han) < min_han:
        return []

    hits: list[dict[str, Any]] = []
    # Recursively inspect remaining non-overlapping ranges inside this segment
    work_ranges: list[tuple[int, int]] = [(0, len(seg_han))]
    while work_ranges and len(hits) < max_hits:
        r_start, r_end = work_ranges.pop(0)
        if r_end - r_start < min_han:
            continue
        sub_han = seg_han[r_start:r_end]
        found = _longest_common_han_substring(sub_han, outline_han, min_han)
        if found is None:
            continue
        rel_a, pos_b, match_len = found
        abs_han_a = r_start + rel_a
        draft_char_start = seg_offset + seg_pos[abs_han_a]
        draft_char_end = seg_offset + seg_pos[abs_han_a + match_len - 1] + 1
        out_char_start = outline_pos[pos_b]
        out_char_end = outline_pos[pos_b + match_len - 1] + 1
        para_idx = full_draft[:draft_char_start].count('\n') + 1
        hits.append({
            'han_length': match_len,
            'draft_start': draft_char_start,
            'draft_end': draft_char_end,
            'draft_location': f'第{para_idx}段',
            'draft_quote': full_draft[draft_char_start:draft_char_end].replace('\n', ' ').strip()[:120],
            'outline_quote': outline_text[out_char_start:out_char_end].replace('\n', ' ').strip()[:120],
        })
        # Split around the matched Han range so we catch additional independent copied spans
        if abs_han_a - r_start >= min_han:
            work_ranges.append((r_start, abs_han_a))
        if r_end - (abs_han_a + match_len) >= min_han:
            work_ranges.append((abs_han_a + match_len, r_end))

    return hits


def check_outline_copy(
    draft_text: str,
    outline_text: str,
    *,
    extra_anchors: list[str] | tuple[str, ...] | None = None,
    min_han: int = 16,
    max_hits: int = 6,
) -> dict[str, Any]:
    """Audit `draft_text` for contiguous >= `min_han` Chinese-char overlap with `outline_text`.

    Authorized verbatim anchors are excised surgically (`split_by_anchors`) before scanning.
    """
    draft = (draft_text or '').strip()
    outline = (outline_text or '').strip()
    if not draft or not outline:
        return {
            'passed': True,
            'hit_count': 0,
            'max_overlap_han': 0,
            'anchors_authorized': [],
            'anchors_excised': 0,
            'hits': [],
        }

    anchors = extract_verbatim_anchors(outline, extra_anchors=extra_anchors)
    segments, excised_count = split_by_anchors(draft, anchors)
    outline_han, outline_pos = han_with_positions(outline)
    if len(outline_han) < min_han:
        return {
            'passed': True,
            'hit_count': 0,
            'max_overlap_han': 0,
            'anchors_authorized': anchors,
            'anchors_excised': excised_count,
            'hits': [],
        }

    all_hits: list[dict[str, Any]] = []
    for seg_offset, seg_text in segments:
        if len(all_hits) >= max_hits:
            break
        remaining = max_hits - len(all_hits)
        seg_hits = _extract_non_overlapping_hits(
            seg_text, seg_offset, draft, outline, outline_han, outline_pos,
            min_han=min_han, max_hits=remaining,
        )
        all_hits.extend(seg_hits)

    all_hits.sort(key=lambda h: (-h['han_length'], h['draft_start']))
    max_overlap = max((h['han_length'] for h in all_hits), default=0)
    return {
        'passed': len(all_hits) == 0,
        'hit_count': len(all_hits),
        'max_overlap_han': max_overlap,
        'anchors_authorized': anchors,
        'anchors_excised': excised_count,
        'hits': all_hits,
    }


def extract_outline_text_from_scene_card(scene_card_body: dict[str, Any] | None) -> tuple[str, list[str]]:
    """Build a combined outline reference string and explicit anchors from a scene card body."""
    if not isinstance(scene_card_body, dict):
        return '', []
    parts: list[str] = []
    anchors: list[str] = []
    for key in ('goal', 'conflict', 'entering_state', 'planned_result', 'outcome', 'turning_point', 'summary', 'outline'):
        val = scene_card_body.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    beats = scene_card_body.get('beats') or scene_card_body.get('playable_beats')
    if isinstance(beats, list):
        for b in beats:
            if isinstance(b, str) and b.strip():
                parts.append(b.strip())
            elif isinstance(b, dict):
                for bk in ('beat', 'description', 'action', 'summary'):
                    if isinstance(b.get(bk), str) and b[bk].strip():
                        parts.append(b[bk].strip())
                for ak in ('verbatim_anchor', 'anchor_line', 'quote'):
                    if isinstance(b.get(ak), str) and b[ak].strip():
                        anchors.append(b[ak].strip())
    for ak in ('verbatim_anchors', 'anchor_quotes'):
        raw = scene_card_body.get(ak)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    anchors.append(item.strip())
    return '\n'.join(parts), anchors
