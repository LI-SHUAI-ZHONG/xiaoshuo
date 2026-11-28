"""Explicit Soft-Override Ledger with Non-Negotiable Hard Invariants.

Design rules:
  - Hard invariants (fact/timeline contradictions, dead character resurrection, POV secret
    leaks, empty/placeholder prose, unresolved core changes) can NEVER be overridden.
  - Soft guidance (transitional pacing, delayed hook, mild word-budget drift, formal
    character dialogue, skipping a promise touch in one breather chapter) MAY be explicitly
    overridden by the author with a mandatory rationale tag and explanation.
  - Recurring overrides/rejections (>= 3 hits of the same pattern) automatically feed into
    Living Craft Evolution (`craft_evolution.py`) as rule-promotion proposals!
"""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from nw.store import Store, now

# Codes/prefixes that are HARD invariants and MUST NEVER be overridden
HARD_NON_OVERRIDABLE_CODES: frozenset[str] = frozenset({
    'HARD_FACT_FINDINGS',
    'FACT_FINDING',
    'CORE_CHANGE',
    'PRE_EMPTY_DRAFT',
    'PRE_META_LEAK',
    'PRE_BROKEN_TAIL',
    'PRE_POV_SECRET_LEAK',
    'PRE_VERBATIM_REPEAT',
    'PRE_MARKDOWN_BOLD_LEAK',
    'PRE_GARBLED_CHAR',
    'PRE_ENGINEERING_META_LEAK',
    'MATERIAL_EVIDENCE',
    'TIMELINE_CONFLICT',
    'ENTITY_DEAD_RESURRECTED',
    'SETTING_CONFLICT',
    'CONTINUITY_BREAK',
})

HARD_NON_OVERRIDABLE_PREFIXES: tuple[str, ...] = (
    'PRE_PLACEHOLDER_',
    'STALE_',
    'CORE_',
    'HARD_',
)

OVERRIDE_RATIONALE_TAGS: dict[str, dict[str, Any]] = {
    'TRANSITIONAL_SETUP': {
        'label': '铺垫与过渡需要',
        'debt_weight': 1.0,
        'description': '本章刻意放缓以铺垫氛围、转场或消化前文高潮。',
    },
    'LOGIC_INTEGRITY': {
        'label': '剧情逻辑与悬疑公平性优先',
        'debt_weight': 0.5,
        'description': '为保证推理公平或因果严密，暂不强塞廉价反转或爽点。',
    },
    'CHARACTER_CREDIBILITY': {
        'label': '人物可信度与性格优先',
        'debt_weight': 0.5,
        'description': '该角色设定本身决定其说话书面/克制或行动谨慎。',
    },
    'WORLD_RULE_CONSTRAINT': {
        'label': '世界硬规则限制',
        'debt_weight': 0.5,
        'description': '受已确认的世界观/代价规则制约，本章无法直接兑现。',
    },
    'ARC_TIMING': {
        'label': '长线大回收蓄力窗口',
        'debt_weight': 1.0,
        'description': '该承诺或高潮安排在后续指定卷/章集中引爆。',
    },
    'EDITORIAL_INTENT': {
        'label': '作者主观品味与艺术意图',
        'debt_weight': 1.5,
        'description': '作者明确有意为之的风格或节奏选择（触发 3 次同因可升格为本书红线）。',
    },
    'REJECTION_PATTERN': {
        'label': '审稿驳回/返工归因',
        'debt_weight': 1.0,
        'description': '记录作者因某类固定毛病打回 AI 草稿，累计 3 次自动提议写入本书工艺红线。',
    },
}

_CONSTRAINT_TO_DOMAIN: dict[str, str] = {
    'PRE_AI_CLICHE_OVERLOAD': 'voice',
    'PRE_MODERN_SLANG_BAN': 'voice',
    'PRE_NARRATOR_PREACHING': 'voice',
    'PRE_IDIOM_STACKING': 'voice',
    'PRE_TELEGRAPH_CHOP': 'voice',
    'PRE_PARAGRAPH_WALL': 'voice',
    'PRE_UNCLOSED_QUOTES': 'voice',
    'PRE_NOT_IS_CLUSTER': 'voice',
    'PRE_VOICE_CONTRAST': 'voice',
    'PRE_NEGATION_PARADE': 'voice',
    'PRE_TRAILER_ENDING': 'voice',
    'PRE_NARRATION_EM_DASH_OVERLOAD': 'voice',
    'PRE_CENSORED_PINYIN': 'voice',
    'PRE_AUTHOR_META_HEADER': 'voice',
    'PRE_SLOW_MICRO_ACTION_TIC': 'voice',
    'PRE_ACTION_LIST_CAMERA': 'voice',
    'PRE_NEGATION_PAIR_TIC': 'voice',
    'PRE_EXCLAMATION_ROAR': 'voice',
    'PRE_DRAMATIC_CLICHE_TIC': 'voice',
    'PRE_IDLE_PROP_DECORATION': 'voice',
    'PRE_DRY_NARRATION': 'voice',
    'PRE_OUTLINE_COPY': 'plot_pacing',
    'PRE_NEAR_REPEAT': 'voice',
    'VOICE_STYLE_DRIFT': 'voice',
    'WORD_BUDGET': 'plot_pacing',
    'NO_PROMISE_TOUCH': 'plot_pacing',
    'WEAK_HOOK_STREAK': 'plot_pacing',
    'STRAND_IMBALANCE': 'plot_pacing',
    'PACING_SLOW': 'plot_pacing',
    'CHARACTER_VOICE_SOFT': 'cast',
    'CAST_TOOL_RISK': 'cast',
    'WORLD_EXPOSITION_HEAVY': 'world',
    'SOFT_REVIEW_REVISE': 'voice',
}


def is_overridable_code(constraint_code: str) -> bool:
    code = str(constraint_code or '').strip().upper()
    if not code:
        return False
    if code in HARD_NON_OVERRIDABLE_CODES:
        return False
    if any(code.startswith(prefix) for prefix in HARD_NON_OVERRIDABLE_PREFIXES):
        return False
    return True


def record_override(
    store: Store,
    *,
    branch_id: str = 'main',
    constraint_kind: str,
    constraint_code: str,
    reason_tag: str,
    reason_text: str,
    scene_id: str | None = None,
    chapter_index: int | None = None,
    draft_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist an explicit author soft-override decision in SQLite `override_ledger`."""
    code = str(constraint_code or '').strip()
    if not is_overridable_code(code):
        raise ValueError(
            f'HARD_INVARIANT: 「{code}」属于事实/时间线/视角泄密或完整性硬红线，禁止豁免，请修正正文后继续。'
        )
    tag = str(reason_tag or '').strip().upper()
    if tag not in OVERRIDE_RATIONALE_TAGS:
        raise ValueError(f'无效的豁免理由标签: {reason_tag}')
    text = str(reason_text or '').strip()
    if not text:
        raise ValueError('登记显式豁免必须填写具体理由说明')
    kind = str(constraint_kind or 'soft_gate').strip() or 'soft_gate'
    ident = f'ovr-{uuid4().hex[:12]}'
    ts = now()
    details_json = json.dumps(details or {}, ensure_ascii=False)
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''INSERT INTO override_ledger(
                id, branch_id, scene_id, chapter_index, draft_id,
                constraint_kind, constraint_code, reason_tag, reason_text,
                details_json, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (ident, branch_id, scene_id, chapter_index, draft_id,
             kind, code, tag, text[:400], details_json, 'active', ts),
        )
    return {
        'id': ident,
        'branch_id': branch_id,
        'scene_id': scene_id,
        'chapter_index': chapter_index,
        'draft_id': draft_id,
        'constraint_kind': kind,
        'constraint_code': code,
        'reason_tag': tag,
        'reason_label': OVERRIDE_RATIONALE_TAGS[tag]['label'],
        'reason_text': text[:400],
        'details': details or {},
        'status': 'active',
        'created_at': ts,
    }


def list_overrides(
    store: Store,
    *,
    branch_id: str = 'main',
    scene_id: str | None = None,
    draft_id: str | None = None,
    status: str | None = 'active',
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses = ['branch_id=?']
    params: list[Any] = [branch_id]
    if scene_id:
        clauses.append('scene_id=?')
        params.append(scene_id)
    if draft_id:
        clauses.append('draft_id=?')
        params.append(draft_id)
    if status:
        clauses.append('status=?')
        params.append(status)
    sql = f"SELECT * FROM override_ledger WHERE {' AND '.join(clauses)} ORDER BY rowid DESC LIMIT ?"
    params.append(max(1, int(limit)))
    rows = store.connection.execute(sql, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        tag = row['reason_tag']
        try:
            details = json.loads(row['details_json'])
        except ValueError:
            details = {}
        out.append({
            'id': row['id'],
            'branch_id': row['branch_id'],
            'scene_id': row['scene_id'],
            'chapter_index': row['chapter_index'],
            'draft_id': row['draft_id'],
            'constraint_kind': row['constraint_kind'],
            'constraint_code': row['constraint_code'],
            'reason_tag': tag,
            'reason_label': OVERRIDE_RATIONALE_TAGS.get(tag, {}).get('label', tag),
            'reason_text': row['reason_text'],
            'details': details,
            'status': row['status'],
            'created_at': row['created_at'],
        })
    return out


def revoke_override(store: Store, override_id: str) -> dict[str, Any]:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        row = store.connection.execute('SELECT * FROM override_ledger WHERE id=?', (override_id,)).fetchone()
        if row is None:
            raise ValueError(f'未找到豁免记录: {override_id}')
        store.connection.execute("UPDATE override_ledger SET status='revoked' WHERE id=?", (override_id,))
    return {'id': override_id, 'status': 'revoked'}


def mark_overrides_promoted(store: Store, override_ids: list[str]) -> int:
    clean_ids = [str(i).strip() for i in (override_ids or ()) if str(i).strip()]
    if not clean_ids:
        return 0
    placeholders = ','.join('?' for _ in clean_ids)
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        cur = store.connection.execute(
            f"UPDATE override_ledger SET status='promoted' WHERE id IN ({placeholders}) AND status='active'",
            clean_ids,
        )
        return max(0, int(cur.rowcount))


def _infer_target_domain(constraint_code: str, constraint_kind: str) -> str:
    code = str(constraint_code or '').upper()
    if code in _CONSTRAINT_TO_DOMAIN:
        return _CONSTRAINT_TO_DOMAIN[code]
    if code.startswith('PRE_CLICHE_') or 'VOICE' in code or 'STYLE' in code:
        return 'voice'
    if 'CAST' in code or 'CHAR' in code:
        return 'cast'
    if 'WORLD' in code or 'RULE' in code:
        return 'world'
    if 'PACING' in code or 'HOOK' in code or 'PROMISE' in code or 'STRAND' in code:
        return 'plot_pacing'
    if constraint_kind in ('voice_soft', 'review_rejection'):
        return 'voice'
    return 'plot_pacing'


def summarize_recurring_patterns(
    store: Store,
    *,
    branch_id: str = 'main',
    min_count: int = 3,
) -> list[dict[str, Any]]:
    """Cluster repeated active overrides & rejections (>= min_count) into rule-promotion proposals."""
    rows = list_overrides(store, branch_id=branch_id, status='active', limit=200)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row['constraint_code'], row['reason_tag'])
        buckets.setdefault(key, []).append(row)

    proposals: list[dict[str, Any]] = []
    for (code, tag), items in buckets.items():
        if len(items) < max(1, int(min_count)):
            continue
        chapters = sorted({int(it['chapter_index']) for it in items if isinstance(it.get('chapter_index'), int)})
        latest_reason = items[0]['reason_text']
        domain = _infer_target_domain(code, items[0]['constraint_kind'])
        is_rejection = (tag == 'REJECTION_PATTERN' or items[0]['constraint_kind'] == 'review_rejection')
        proposed_redline = (
            f'避免反复触发【{latest_reason}】（源自作者连续 {len(items)} 次打回校准）'
            if is_rejection
            else f'作者明确风格/节奏偏好【{OVERRIDE_RATIONALE_TAGS.get(tag, {}).get("label", tag)}】：{latest_reason}'
        )
        proposals.append({
            'pattern_key': f'{code}:{tag}',
            'constraint_code': code,
            'reason_tag': tag,
            'reason_label': OVERRIDE_RATIONALE_TAGS.get(tag, {}).get('label', tag),
            'count': len(items),
            'chapters': chapters,
            'target_domain': domain,
            'proposed_redline': proposed_redline[:180],
            'sample_reasons': [it['reason_text'] for it in items[:3]],
            'override_ids': [it['id'] for it in items],
        })
    proposals.sort(key=lambda r: r['count'], reverse=True)
    return proposals
