"""Strict Promise Lifecycle Semantics (`mention != advance` + `superseded` archival),
Host Canonical PromiseArbiter, and Zero-Token Numeric Resource Delta Ledger.

Closes three subtle serialization bugs discovered in long-form state projection:
  1. Mentioning/recalling a promise (`mention`) or postponing it (`defer`) must NEVER reset
     `last_advanced_chapter` or clear Promise Rhythm Debt.
  2. Withdrawn/retconned premises can be archived as `superseded` (with explicit reason,
     strictly forbidden on already `paid_off` promises) so retired threads stop nagging as
     false overdue debt without deleting audit history.
  3. Numeric resource changes (gold, spirit stones, HP, lifespan, countdown days, etc.) are
     deterministically cross-checked against opening + explicit delta == closing.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Any

PROMISE_ACTION_KINDS = frozenset({'plant', 'advance', 'mention', 'defer', 'payoff', 'supersede'})
PROMISE_TERMINAL_STAGES = frozenset({'paid_off', 'superseded'})

NUMERIC_RESOURCE_PREDICATES = frozenset({
    'gold', 'money', 'cash', 'coins', 'spirit_stones', 'stones', 'credits', 'balance',
    'hp', 'mp', 'energy', 'stamina', 'lifespan', 'days_left', 'countdown', 'troops',
    'army', 'score', 'points', 'inventory_count', 'ammo',
    '灵石', '金币', '银两', '铜钱', '余额', '资产', '资金', '寿元', '寿命', '生命',
    '血量', '法力', '灵力', '体力', '天数', '倒计时', '兵力', '人数', '点数', '积分', '贡献', '库存',
})

_DELTA_MINUS_RE = re.compile(
    r'(?:花了|花费|消耗|扣除|扣掉|减少|失去|付出|支付|用掉|损毁|损失|折损|减了)\s*(\d+(?:\.\d+)?)',
)
_DELTA_PLUS_RE = re.compile(
    r'(?:获得|得到|赚了|赚取|收入|增加|新增|补回|奖励|进账|捡到|到手|加了)\s*(\d+(?:\.\d+)?)',
)


def parse_promise_op_semantics(op: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy string and enriched structured promise operations into canonical semantics.

    Returns:
      {
        'stage': 'planted'|'sleeping'|'awake'|'paid_off'|'superseded'|...,
        'action_kind': 'plant'|'advance'|'mention'|'defer'|'payoff'|'supersede',
        'advances_progress': bool,   # True ONLY for plant/advance/payoff; False for mention/defer/supersede!
        'is_mention_only': bool,
        'is_superseded': bool,
        'reason': str,
        'authority_ref': str,
      }
    """
    op_type = str(op.get('op') or '')
    old_val = op.get('expected_old')
    new_val = op.get('new_value')

    old_stage = old_val.get('stage') if isinstance(old_val, dict) else (str(old_val) if isinstance(old_val, str) else '')
    reason = ''
    authority_ref = ''

    if isinstance(new_val, dict):
        stage = str(new_val.get('stage') or new_val.get('status') or old_stage or 'awake').strip()
        action_kind = str(new_val.get('action_kind') or new_val.get('kind') or '').strip().lower()
        reason = str(new_val.get('reason') or new_val.get('note') or '').strip()
        authority_ref = str(new_val.get('authority_ref') or new_val.get('decision_id') or '').strip()
    else:
        stage = str(new_val or '').strip()
        action_kind = ''

    if not action_kind:
        if op_type == 'introduce_promise' or (old_val is None and stage == 'planted'):
            action_kind = 'plant'
        elif stage == 'paid_off':
            action_kind = 'payoff'
        elif stage == 'superseded':
            action_kind = 'supersede'
        elif stage == 'sleeping' and old_stage in ('planted', 'sleeping', 'awake'):
            # Marking/keeping a promise sleeping without raising stakes is a defer/dormant hold, not advancement.
            action_kind = 'defer'
        elif old_stage and stage == old_stage:
            # Touching a promise without changing stage or providing explicit action_kind='advance' is a mention.
            action_kind = 'mention'
        else:
            action_kind = 'advance'

    if action_kind not in PROMISE_ACTION_KINDS:
        raise ValueError(f'PROMISE_LIFECYCLE: unsupported action_kind {action_kind!r}')

    if action_kind == 'supersede' or stage == 'superseded':
        stage = 'superseded'
        action_kind = 'supersede'
        if old_stage == 'paid_off':
            raise ValueError('PROMISE_LIFECYCLE: 已兑现（paid_off）的历史承诺禁止标为 superseded 废止')
        if not reason:
            raise ValueError('PROMISE_LIFECYCLE: 将承诺标为 superseded 废止必须提供明确依据说明（reason）')

    advances_progress = action_kind in ('plant', 'advance', 'payoff')
    return {
        'stage': stage,
        'action_kind': action_kind,
        'advances_progress': advances_progress,
        'is_mention_only': action_kind == 'mention',
        'is_deferred': action_kind == 'defer',
        'is_superseded': stage == 'superseded',
        'reason': reason,
        'authority_ref': authority_ref,
    }


def validate_promise_operation(op: dict[str, Any]) -> dict[str, Any] | None:
    """Validate promise lifecycle invariants on any promise op; returns semantics or None if not a promise op."""
    if op.get('predicate') != 'promise_stage' and op.get('op') not in ('introduce_promise', 'advance_promise'):
        return None
    return parse_promise_op_semantics(op)


def _norm_title(text: str) -> str:
    return re.sub(r'[\s\W_]+', '', (text or '').lower())


def arbitrate_promise_operations(
    existing_promises: list[dict[str, Any]],
    candidate_ops: list[dict[str, Any]],
    *,
    similarity_threshold: float = 0.72,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Host-enforced canonical PromiseArbiter preventing duplicate/ghost promise IDs.

    `existing_promises` items look like `{'card_id': str, 'title': str, 'accepted_stage': str|None}`.
    Returns `(normalized_ops, arbitration_notes)`.
    """
    canonical_by_id = {str(p['card_id']): p for p in existing_promises if p.get('card_id')}
    open_titles: list[tuple[str, str, str]] = [
        (str(p['card_id']), str(p.get('title') or ''), _norm_title(str(p.get('title') or '')))
        for p in existing_promises
        if p.get('card_id') and p.get('accepted_stage') not in PROMISE_TERMINAL_STAGES
    ]

    normalized: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []

    for op in candidate_ops:
        if op.get('predicate') != 'promise_stage' and op.get('op') not in ('introduce_promise', 'advance_promise'):
            normalized.append(op)
            continue

        sem = parse_promise_op_semantics(op)
        ent = str(op.get('entity_id') or '').strip()
        if ent in canonical_by_id:
            normalized.append(op)
            continue

        # Check if model tried to invent a duplicate promise matching an existing active promise title/id
        new_val = op.get('new_value')
        cand_title = ''
        if isinstance(new_val, dict):
            cand_title = str(new_val.get('title') or new_val.get('summary') or new_val.get('note') or '').strip()
        probe = _norm_title(cand_title or ent)

        matched_id = None
        best_sim = 0.0
        for cid, raw_title, norm_t in open_titles:
            if not norm_t or not probe:
                continue
            sim = SequenceMatcher(None, probe, norm_t).ratio()
            if probe in norm_t or norm_t in probe:
                sim = max(sim, 0.85)
            if sim >= similarity_threshold and sim > best_sim:
                best_sim = sim
                matched_id = cid

        if matched_id is not None:
            fixed_op = {**op, 'entity_id': matched_id}
            if fixed_op.get('op') == 'introduce_promise' and canonical_by_id[matched_id].get('accepted_stage'):
                fixed_op['op'] = 'advance_promise'
                fixed_op['expected_old'] = canonical_by_id[matched_id]['accepted_stage']
            normalized.append(fixed_op)
            notes.append({
                'action': 'deduplicated_to_canonical',
                'original_entity_id': ent,
                'canonical_entity_id': matched_id,
                'similarity': round(best_sim, 3),
                'action_kind': sem['action_kind'],
            })
        else:
            normalized.append(op)

    return normalized, notes


def _as_number(val: Any) -> float | None:
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    if isinstance(val, dict):
        for k in ('amount', 'value', 'balance', 'count'):
            v = val.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def _declared_delta(val: Any) -> float | None:
    if isinstance(val, dict):
        d = val.get('delta')
        if isinstance(d, (int, float)) and not isinstance(d, bool):
            return float(d)
    return None


def _is_numeric_predicate(predicate: str) -> bool:
    p = (predicate or '').strip().lower()
    if p in NUMERIC_RESOURCE_PREDICATES:
        return True
    return any(tok in p for tok in ('灵石', '金币', '银两', '余额', '寿元', '倒计时', '兵力', 'gold', 'money', 'balance', 'lifespan', 'hp', 'mp'))


def check_numeric_resource_ledger(
    operations: list[dict[str, Any]],
    draft_text: str,
    target_ref: dict[str, Any],
) -> list[dict[str, Any]]:
    """Zero-token arithmetic balance check for numeric resource state operations.

    Checks:
      1. Explicit `delta` field balance: `expected_old + delta == new_value`
      2. Negative balance violation on non-negative resource predicates (gold/spirit_stones/lifespan/troops)
      3. Evidence-span explicit +/- arithmetic mismatch when prose states a single clear delta
    """
    findings: list[dict[str, Any]] = []
    for op in operations:
        pred = str(op.get('predicate') or '')
        if not _is_numeric_predicate(pred):
            continue
        old_num = _as_number(op.get('expected_old'))
        new_num = _as_number(op.get('new_value'))
        if new_num is None:
            continue
        ev_list = op.get('evidence') if isinstance(op.get('evidence'), list) else []

        # 1. Negative balance guard on physical resources
        if new_num < 0 and any(tok in pred.lower() for tok in ('灵石', '金币', '银两', '寿元', '生命', '兵力', '人数', '库存', 'gold', 'spirit_stones', 'lifespan', 'troops', 'hp', 'ammo')):
            findings.append({
                'code': 'NUMERIC_LEDGER_NEGATIVE',
                'severity': 'hard',
                'target_ref': target_ref,
                'evidence': ev_list,
                'explanation': f'数值资源「{pred}」实体 {op.get("entity_id")} 结算后为负数（{new_num:g}），违背物理下限。',
                'suggested_action': '核对正文消耗量或补充借贷/透支说明后重新结算数值。',
                'status': 'OPEN',
            })

        if old_num is None:
            continue

        # 2. Explicit structured delta mismatch
        decl_delta = _declared_delta(op.get('new_value'))
        if decl_delta is not None and abs((old_num + decl_delta) - new_num) > 1e-6:
            findings.append({
                'code': 'NUMERIC_LEDGER_MISMATCH',
                'severity': 'hard',
                'target_ref': target_ref,
                'evidence': ev_list,
                'explanation': (
                    f'数值资源「{pred}」双边账不平：期初 {old_num:g} + 声明增减 {decl_delta:+g} '
                    f'= {old_num + decl_delta:g}，但期末结算为 {new_num:g}。'
                ),
                'suggested_action': '修正正文消耗/收益数字或修正状态结算的期末数值使双边平账。',
                'status': 'OPEN',
            })
            continue

        # 3. Single clear prose arithmetic delta check within cited evidence spans
        if ev_list and draft_text:
            snippets = [
                draft_text[int(e['start']):int(e['end'])]
                for e in ev_list
                if isinstance(e, dict) and isinstance(e.get('start'), int) and isinstance(e.get('end'), int)
            ]
            joined = ' '.join(snippets)
            minus_hits = [float(m.group(1)) for m in _DELTA_MINUS_RE.finditer(joined)]
            plus_hits = [float(m.group(1)) for m in _DELTA_PLUS_RE.finditer(joined)]
            # Only trigger when prose evidence states a single unambiguous transaction (avoids false positives on multi-step narratives)
            if len(minus_hits) + len(plus_hits) == 1:
                prose_delta = plus_hits[0] if plus_hits else -minus_hits[0]
                expected_closing = old_num + prose_delta
                if abs(expected_closing - new_num) > 1e-6:
                    findings.append({
                        'code': 'NUMERIC_LEDGER_MISMATCH',
                        'severity': 'hard',
                        'target_ref': target_ref,
                        'evidence': ev_list,
                        'explanation': (
                            f'数值资源「{pred}」正文算术与期末状态不平：期初 {old_num:g}，'
                            f'正文证据显示变动 {prose_delta:+g}（应为 {expected_closing:g}），'
                            f'但结算为 {new_num:g}。'
                        ),
                        'suggested_action': '核对正文中的具体数额与状态变更，确保期初+增减=期末。',
                        'status': 'OPEN',
                    })
    return findings
