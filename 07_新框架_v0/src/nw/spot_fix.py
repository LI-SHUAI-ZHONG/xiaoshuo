"""Host-Bounded Spot-Fix Local Revision & Episode-Baseline Diff-Aware Review.

Solves full-scene rewrite churn during Step 16 revision:
  1. Routes findings into `local` (range-bounded spot-fix) vs `structural` (full scene revise).
  2. Slices prose into exact paragraph ranges preserving original separators byte-for-byte.
  3. Sends ONLY selected edit ranges + +-2 anchor paragraphs + remaining character budget to model.
  4. Splices model replacements back in host memory, cryptographically guaranteeing 100% intact
     preservation of all prose outside the authorized edit ranges.
  5. Computes episode-start baseline vs current version diffs so re-review verifies both fix
     effectiveness AND zero unauthorized scope drift across retry rounds.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from nw.story_delta import _PARAGRAPH_BREAK

DEFAULT_MAX_RANGES = 3
DEFAULT_MAX_AFFECTED_RATIO = 0.45

_STRUCTURAL_REVIEW_MARKERS = (
    '时间线', '因果', 'POV', '视角泄密', '整场', '结构性', '重构', '核心冲突',
    '人物动机崩', '主线目标', '重写全', '铺垫缺失', '情绪弧线',
)

_JSON_FENCE_RE = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL | re.IGNORECASE)


def split_paragraphs(text: str) -> list[dict[str, Any]]:
    """Split prose using the exact paragraph boundary convention of `nw.story_delta`."""
    if not text:
        return []
    breaks = list(_PARAGRAPH_BREAK.finditer(text))
    starts = [0, *(m.end() for m in breaks)]
    ends = [*(m.start() for m in breaks), len(text)]
    seps = [*(m.group(0) for m in breaks), '']
    out: list[dict[str, Any]] = []
    for idx, (s, e, sep) in enumerate(zip(starts, ends, seps)):
        out.append({
            'index': idx,
            'start': s,
            'end': e,
            'text': text[s:e],
            'sep_after': sep,
            'sha256': sha256(text[s:e].encode('utf-8')).hexdigest(),
        })
    return out


def _single_newline_paragraphs(text: str) -> list[dict[str, Any]]:
    """Fallback splitter when prose uses single-newline paragraphs without blank lines."""
    if not text:
        return []
    matches = list(re.finditer(r'\r?\n', text))
    starts = [0, *(m.end() for m in matches)]
    ends = [*(m.start() for m in matches), len(text)]
    seps = [*(m.group(0) for m in matches), '']
    return [
        {
            'index': idx,
            'start': s,
            'end': e,
            'text': text[s:e],
            'sep_after': sep,
            'sha256': sha256(text[s:e].encode('utf-8')).hexdigest(),
        }
        for idx, (s, e, sep) in enumerate(zip(starts, ends, seps))
    ]


def segment_prose(text: str) -> list[dict[str, Any]]:
    """Prefer blank-line paragraphs; fall back to single-newline lines when prose has 1 big block."""
    paras = split_paragraphs(text)
    if len(paras) <= 1 and '\n' in (text or ''):
        return _single_newline_paragraphs(text)
    return paras


def extract_paragraph_indices_from_pre_report(pre_report: dict[str, Any] | None, text: str) -> list[int]:
    """Map `pre_review_gate` issue locations/quotes onto 0-based paragraph indices."""
    if not isinstance(pre_report, dict):
        return []
    paras = segment_prose(text)
    if not paras:
        return []
    indices: set[int] = set()
    issues = [*(pre_report.get('hard_issues') or ()), *(pre_report.get('warnings') or ())]
    for issue in issues:
        loc = str(issue.get('location') or '')
        quote = str(issue.get('quote') or '').strip()
        matched = False
        if quote:
            needle = quote[:24]
            for p in paras:
                if needle and needle in p['text']:
                    indices.add(p['index'])
                    matched = True
                    break
        if not matched:
            m = re.search(r'第(\d+)段', loc)
            if m:
                idx = max(0, min(len(paras) - 1, int(m.group(1)) - 1))
                indices.add(idx)
    return sorted(indices)


def select_spot_fix_ranges(
    text: str,
    target_paragraphs: list[int] | tuple[int, ...],
    *,
    max_ranges: int = DEFAULT_MAX_RANGES,
    max_affected_ratio: float = DEFAULT_MAX_AFFECTED_RATIO,
) -> dict[str, Any]:
    """Validate and merge target paragraph indices into bounded non-overlapping edit ranges."""
    paras = segment_prose(text)
    total_chars = len(text or '')
    if not paras or total_chars == 0:
        return {
            'eligible': False,
            'fallback_reason': '正文为空，无法执行局部 Spot-Fix',
            'paragraphs': paras,
            'ranges': [],
            'affected_chars': 0,
            'protected_chars': 0,
            'affected_ratio': 1.0,
        }
    valid_idxs = sorted({int(i) for i in target_paragraphs if isinstance(i, int) and 0 <= i < len(paras)})
    if not valid_idxs:
        return {
            'eligible': False,
            'fallback_reason': '未提供有效的目标段落索引，升级为整场修订',
            'paragraphs': paras,
            'ranges': [],
            'affected_chars': 0,
            'protected_chars': total_chars,
            'affected_ratio': 0.0,
        }

    # Merge adjacent paragraph indices into contiguous ranges
    spans: list[tuple[int, int]] = []
    start = prev = valid_idxs[0]
    for idx in valid_idxs[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            spans.append((start, prev))
            start = prev = idx
    spans.append((start, prev))

    ranges: list[dict[str, Any]] = []
    affected_chars = 0
    for rank, (lo, hi) in enumerate(spans, 1):
        char_start = paras[lo]['start']
        char_end = paras[hi]['end']
        slice_text = text[char_start:char_end]
        affected_chars += len(slice_text)
        ranges.append({
            'range_id': f'R{rank}',
            'start_paragraph': lo,
            'end_paragraph': hi,
            'char_start': char_start,
            'char_end': char_end,
            'original_text': slice_text,
            'original_chars': len(slice_text),
        })

    protected_chars = max(0, total_chars - affected_chars)
    ratio = round(affected_chars / max(1, total_chars), 4)
    if len(ranges) > max_ranges:
        return {
            'eligible': False,
            'fallback_reason': f'待修区间数（{len(ranges)}）超过上限 {max_ranges}，自动升级为整场修订',
            'paragraphs': paras,
            'ranges': ranges,
            'affected_chars': affected_chars,
            'protected_chars': protected_chars,
            'affected_ratio': ratio,
        }
    if ratio > max_affected_ratio:
        return {
            'eligible': False,
            'fallback_reason': f'待修字符占比 {round(ratio * 100, 1)}% 超过阈值 {round(max_affected_ratio * 100)}%，自动升级为整场修订',
            'paragraphs': paras,
            'ranges': ranges,
            'affected_chars': affected_chars,
            'protected_chars': protected_chars,
            'affected_ratio': ratio,
        }
    return {
        'eligible': True,
        'fallback_reason': None,
        'paragraphs': paras,
        'ranges': ranges,
        'affected_chars': affected_chars,
        'protected_chars': protected_chars,
        'affected_ratio': ratio,
    }


def route_repair_scope(
    review: dict[str, Any] | None,
    *,
    draft_text: str,
    pre_report: dict[str, Any] | None = None,
    length_feedback: list[str] | None = None,
    max_ranges: int = DEFAULT_MAX_RANGES,
    max_affected_ratio: float = DEFAULT_MAX_AFFECTED_RATIO,
) -> dict[str, Any]:
    """Deterministically route revision to `local` (Spot-Fix) or `structural` (full rewrite)."""
    rev = review or {}
    if rev.get('core_changes'):
        return {'scope': 'structural', 'reason': '存在核心设定变更，需整场结构性修订', 'plan': None}
    if length_feedback:
        return {'scope': 'structural', 'reason': '篇幅偏差超标，需整场篇幅重平衡', 'plan': None}

    explicit_scope = str(rev.get('repair_scope') or '').strip().lower()
    if explicit_scope == 'structural':
        return {'scope': 'structural', 'reason': '审稿明确判定为结构性问题', 'plan': None}

    # Check if material checks failed on structural ordering/beats
    for chk in (rev.get('material_checks') or ()):
        if chk.get('status') != 'pass':
            cid = str(chk.get('id') or '')
            if cid.startswith('work:selected:action:') or cid.startswith('work:narration:'):
                return {'scope': 'structural', 'reason': f'结构性行动/叙述节拍未通过（{cid}）', 'plan': None}

    # Check for structural keywords in review notes unless explicitly tagged local
    notes = str(rev.get('notes') or '')
    if explicit_scope != 'local' and any(tok in notes for tok in _STRUCTURAL_REVIEW_MARKERS):
        return {'scope': 'structural', 'reason': '审稿意见涉及时间线/POV/结构级改动', 'plan': None}

    # Gather target paragraphs from explicit review field or pre_review_gate report
    target_paras: list[int] = []
    raw_targets = rev.get('target_paragraphs')
    if isinstance(raw_targets, list):
        target_paras.extend(int(i) for i in raw_targets if isinstance(i, int))
    if not target_paras and pre_report:
        target_paras.extend(extract_paragraph_indices_from_pre_report(pre_report, draft_text))

    if not target_paras:
        return {'scope': 'structural', 'reason': '无明确局部段落定位，默认整场修订', 'plan': None}

    plan = select_spot_fix_ranges(
        draft_text,
        target_paras,
        max_ranges=max_ranges,
        max_affected_ratio=max_affected_ratio,
    )
    if not plan['eligible']:
        return {'scope': 'structural', 'reason': plan['fallback_reason'], 'plan': plan}
    return {
        'scope': 'local',
        'reason': f'命中局部精准手术条件（{len(plan["ranges"])} 处区间，占全稿 {round(plan["affected_ratio"] * 100, 1)}%）',
        'plan': plan,
    }


def _protected_digest(text: str, ranges: list[dict[str, Any]]) -> str:
    """Hash all bytes OUTSIDE the selected edit ranges."""
    chunks: list[str] = []
    cursor = 0
    for r in ranges:
        chunks.append(text[cursor:r['char_start']])
        cursor = r['char_end']
    chunks.append(text[cursor:])
    return sha256('\x00'.join(chunks).encode('utf-8')).hexdigest()


def build_spot_fix_messages(
    draft_text: str,
    plan: dict[str, Any],
    *,
    instruction: str,
    mode: str = 'spot-fix',
    target_total_chars: int | None = None,
    voice_guidance: str = '',
    context_anchors: int = 2,
) -> list[dict[str, str]]:
    """Build a host-bounded Spot-Fix prompt containing ONLY edit ranges and +-2 anchor paragraphs."""
    paras = plan['paragraphs']
    ranges = plan['ranges']
    protected_chars = plan['protected_chars']
    replacement_budget = (
        max(80, int(target_total_chars) - protected_chars)
        if isinstance(target_total_chars, int) and target_total_chars > 0
        else int(plan['affected_chars'] * 1.25) + 120
    )

    blocks: list[str] = []
    for r in ranges:
        lo, hi = r['start_paragraph'], r['end_paragraph']
        before_paras = [f'[保护上文 P{i}] {paras[i]["text"]}' for i in range(max(0, lo - context_anchors), lo)]
        after_paras = [f'[保护下文 P{i}] {paras[i]["text"]}' for i in range(hi + 1, min(len(paras), hi + 1 + context_anchors))]
        block_lines = [
            f'### 待修区间 {r["range_id"]}（段落 P{lo}..P{hi}，原长 {r["original_chars"]} 字）',
            *before_paras,
            f'<<<EDIT_TARGET {r["range_id"]}>>>',
            r['original_text'],
            f'<<<END_EDIT_TARGET {r["range_id"]}>>>',
            *after_paras,
        ]
        blocks.append('\n'.join(block_lines))

    freeze_clause = (
        '【绝对冻结令（语义润色/去 AI 味模式）】严禁改变任何剧情事实、人物出场、物品归属、时间顺序、因果链与 POV 知情边界；只允许替换空洞情绪标签、套话与生硬句式。'
        if mode in ('polish', 'deslop')
        else '【宿主锁界契约】区间外的所有正文段落已由宿主字节级锁定，你只需重写指定的 EDIT_TARGET 区间，使之与前后保护段落无缝衔接。'
    )
    sys_prompt = (
        '你是精准局部修订编辑。'
        + freeze_clause
        + ' 只输出严格 JSON：{"edits":[{"range_id":"R1","replacement":"替换后的纯正文"}]}。'
        '每个 range_id 必须恰好出现一次，replacement 中不得包含 P编号、标签、解释或保护段落内容。'
        + (f'\n\n【语感与防漂移参照】\n{voice_guidance.strip()}' if voice_guidance.strip() else '')
    )
    user_prompt = (
        f'## 本次修订指令\n{instruction.strip()}\n\n'
        f'## 宿主预算约束\n'
        f'- 保护正文长度：{protected_chars} 字（宿主锁定，严禁改动）\n'
        f'- 所有待修区间合计建议替换上限：约 {replacement_budget} 字\n\n'
        + '\n\n'.join(blocks)
    )
    return [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]


def _parse_edits_json(raw_output: str) -> list[dict[str, str]]:
    text = (raw_output or '').strip()
    if not text:
        raise ValueError('Spot-Fix 模型返回为空')
    payload: Any = None
    try:
        payload = json.loads(text)
    except ValueError:
        m = _JSON_FENCE_RE.search(text)
        if m:
            payload = json.loads(m.group(1))
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                payload = json.loads(text[start:end + 1])
            else:
                raise ValueError('Spot-Fix 输出不是合法 JSON') from None
    edits = payload.get('edits') if isinstance(payload, dict) else None
    if not isinstance(edits, list) or not edits:
        raise ValueError('Spot-Fix JSON 缺少非空 edits 数组')
    normalized: list[dict[str, str]] = []
    for item in edits:
        if not isinstance(item, dict) or not isinstance(item.get('range_id'), str) or not isinstance(item.get('replacement'), str):
            raise ValueError('Spot-Fix edit 条目格式错误')
        rep = item['replacement'].strip()
        if not rep:
            raise ValueError(f'Spot-Fix 区间 {item["range_id"]} 替换文本为空')
        normalized.append({'range_id': item['range_id'].strip(), 'replacement': rep})
    return normalized


def apply_spot_fix_edits(
    original_text: str,
    plan: dict[str, Any],
    raw_output: str,
) -> dict[str, Any]:
    """Splice validated model replacements into original_text while guaranteeing protected bytes stay identical."""
    ranges = plan['ranges']
    if not ranges:
        raise ValueError('Spot-Fix 计划没有可替换区间')
    edits = _parse_edits_json(raw_output)
    by_id = {e['range_id']: e['replacement'] for e in edits}
    expected_ids = [r['range_id'] for r in ranges]
    if set(by_id) != set(expected_ids):
        raise ValueError(f'Spot-Fix 返回区间集合不匹配：期望 {expected_ids}，实际 {sorted(by_id)}')

    before_protected_sha = _protected_digest(original_text, ranges)

    rebuilt_parts: list[str] = []
    applied_ranges: list[dict[str, Any]] = []
    cursor = 0
    new_ranges_for_hash: list[dict[str, Any]] = []
    out_cursor = 0

    for r in ranges:
        protected_seg = original_text[cursor:r['char_start']]
        rebuilt_parts.append(protected_seg)
        out_cursor += len(protected_seg)

        replacement = by_id[r['range_id']]
        new_start = out_cursor
        rebuilt_parts.append(replacement)
        out_cursor += len(replacement)
        new_end = out_cursor

        new_ranges_for_hash.append({'char_start': new_start, 'char_end': new_end})
        applied_ranges.append({
            'range_id': r['range_id'],
            'start_paragraph': r['start_paragraph'],
            'end_paragraph': r['end_paragraph'],
            'before_chars': len(r['original_text']),
            'after_chars': len(replacement),
            'before_preview': r['original_text'][:120],
            'after_preview': replacement[:120],
        })
        cursor = r['char_end']

    tail = original_text[cursor:]
    rebuilt_parts.append(tail)
    spliced = ''.join(rebuilt_parts)
    after_protected_sha = _protected_digest(spliced, new_ranges_for_hash)
    if before_protected_sha != after_protected_sha:
        raise RuntimeError('Spot-Fix 保护区校验失败：未授权段落字节发生变动')

    return {
        'text': spliced,
        'applied_ranges': applied_ranges,
        'protected_sha256_before': before_protected_sha,
        'protected_sha256_after': after_protected_sha,
        'protected_intact': True,
        'delta_chars': len(spliced) - len(original_text),
    }


def compute_revision_diff(
    baseline_text: str,
    current_text: str,
    *,
    authorized_paragraphs: list[int] | set[int] | None = None,
) -> dict[str, Any]:
    """Compare episode-start baseline against current draft and detect scope drift."""
    base_paras = segment_prose(baseline_text)
    curr_paras = segment_prose(current_text)
    auth_set = set(authorized_paragraphs) if authorized_paragraphs is not None else None

    changed: list[dict[str, Any]] = []
    unchanged_count = 0
    scope_drift: list[int] = []

    max_len = max(len(base_paras), len(curr_paras))
    for i in range(max_len):
        b = base_paras[i]['text'] if i < len(base_paras) else None
        c = curr_paras[i]['text'] if i < len(curr_paras) else None
        if b == c:
            unchanged_count += 1
            continue
        changed.append({
            'paragraph': i,
            'kind': 'added' if b is None else ('removed' if c is None else 'modified'),
            'before': (b or '')[:140],
            'after': (c or '')[:140],
        })
        if auth_set is not None and i not in auth_set:
            scope_drift.append(i)

    lines = [
        f'【版本差异对照（对比本轮基线初稿）】总字数变化 {len(current_text) - len(baseline_text):+d} 字，'
        f'未改段落 {unchanged_count} 段，改动段落 {len(changed)} 段。',
    ]
    if scope_drift:
        lines.append(
            f'⚠ 检测到越界改动：段落 {scope_drift[:6]} 不在授权局部修改范围内，请核查是否意外破坏了未授权段落！'
        )
    for item in changed[:4]:
        lines.append(
            f'- P{item["paragraph"]}（{item["kind"]}）：原「{item["before"][:48]}」→ 现「{item["after"][:48]}」'
        )
    return {
        'baseline_paragraphs': len(base_paras),
        'current_paragraphs': len(curr_paras),
        'unchanged_paragraphs': unchanged_count,
        'changed_paragraphs': changed,
        'changed_indices': [c['paragraph'] for c in changed],
        'scope_drift_paragraphs': scope_drift,
        'has_scope_drift': bool(scope_drift),
        'char_delta': len(current_text) - len(baseline_text),
        'summary_for_review': '\n'.join(lines),
    }
