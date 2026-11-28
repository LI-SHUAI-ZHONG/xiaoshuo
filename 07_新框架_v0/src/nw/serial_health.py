"""Serial Health, Base-Compiled Strand Weave, Promise Rhythm-Debt & Foreshadowing Opportunity Engine.

Upgrades passive promise snapshots & static plot bases into a live serialization cockpit:
  1. Genre/Base-Compiled Strand Targets (Quest / Fire / Constellation ratios & max gap
     thresholds compiled per Plot Base + 5-tier length profile — never hardcoded to one genre!)
  2. Promise Rhythm Debt: automatically derives each active promise's `last_touched_chapter`
     from SQLite `story_events`/`state_deltas`, detects high-priority stalled promises and
     missed per-chapter promise touches (unless explicitly exempted in `override_ledger`).
  3. Hook & Strand Fatigue Monitor + Blind Cold-Read Trend integration -> outputs crisp
     2-4 line steering corrections automatically injected into `06 plot_design`.
  4. Signal-vs-Spoiler Outline Guard for `06 plot_design` / `09 scene_design`.
  5. Volume-End Long-Range Foreshadowing Opportunity Brief anchored to future book nodes.
"""
from __future__ import annotations

import json
from typing import Any

from nw.cards import read_card
from nw.cold_read import list_cold_reads
from nw.materials.promise_continuity import approved_promise_snapshot, continuation_reminder
from nw.override_ledger import list_overrides
from nw.plot_pacing_specs import compute_scale_profile, load_plot_pacing_spec
from nw.pre_review_gate import compute_prose_stats
from nw.store import Store, now
from nw.story_models import CardRef, StateHead
from nw.story_state import baseline_for, current_head, replay, revision_state, selected_operations

STRAND_LABELS: dict[str, str] = {
    'quest': '主线推进（Quest）',
    'fire': '情感关系（Fire）',
    'constellation': '世界格局（Constellation）',
}

# Base-compiled Strand profiles tailored to all 8 built-in Plot Bases (1+1>3 over fixed 60/20/20!)
STRAND_PROFILES_BY_PLOT_BASE: dict[str, dict[str, Any]] = {
    'PLOT_PRESSURE_BREAKTHROUGH': {
        'target_ratio': {'quest': 0.65, 'fire': 0.15, 'constellation': 0.20},
        'max_quest_streak': 5,
        'max_fire_gap': 10,
        'max_constellation_gap': 14,
        'strand_notes': '以升级破局为主轴，每 5 章内穿插一次关系互动或势力格局展露。',
    },
    'PLOT_CLUE_REVELATION': {
        'target_ratio': {'quest': 0.55, 'fire': 0.20, 'constellation': 0.25},
        'max_quest_streak': 4,
        'max_fire_gap': 8,
        'max_constellation_gap': 10,
        'strand_notes': '线索勘查与人物信任试探、背后规则揭示交替推进，忌连续纯推理会议。',
    },
    'PLOT_FACTION_CHESS': {
        'target_ratio': {'quest': 0.55, 'fire': 0.20, 'constellation': 0.25},
        'max_quest_streak': 5,
        'max_fire_gap': 9,
        'max_constellation_gap': 10,
        'strand_notes': '明面博弈、私下人情结盟与多方势力洗牌三线咬合。',
    },
    'PLOT_GOAL_MISSION_LOOP': {
        'target_ratio': {'quest': 0.65, 'fire': 0.15, 'constellation': 0.20},
        'max_quest_streak': 5,
        'max_fire_gap': 10,
        'max_constellation_gap': 12,
        'strand_notes': '副本/任务闯关高密度推进，间歇穿插队友羁绊与大世界规则真相。',
    },
    'PLOT_RESOURCE_GROWTH': {
        'target_ratio': {'quest': 0.50, 'fire': 0.25, 'constellation': 0.25},
        'max_quest_streak': 4,
        'max_fire_gap': 7,
        'max_constellation_gap': 10,
        'strand_notes': '经营建设与实利增长为主，适时穿插人情关系升温与外部市场/势力扩张。',
    },
    'PLOT_EMOTION_ESCALATION': {
        'target_ratio': {'quest': 0.35, 'fire': 0.50, 'constellation': 0.15},
        'max_quest_streak': 3,
        'max_fire_gap': 3,
        'max_constellation_gap': 12,
        'strand_notes': '情感拉扯与关系位移是核心引擎，最多隔 2–3 章必须出现实质关系变化。',
    },
    'PLOT_EPISODIC_ARC': {
        'target_ratio': {'quest': 0.50, 'fire': 0.25, 'constellation': 0.25},
        'max_quest_streak': 4,
        'max_fire_gap': 6,
        'max_constellation_gap': 8,
        'strand_notes': '单元事件、常驻群像关系与幕后长线暗潮三线均衡编织。',
    },
    'PLOT_HYBRID_BALANCED': {
        'target_ratio': {'quest': 0.60, 'fire': 0.20, 'constellation': 0.20},
        'max_quest_streak': 5,
        'max_fire_gap': 10,
        'max_constellation_gap': 14,
        'strand_notes': '复合题材稳健三线配比，防单线疲劳与副线断档。',
    },
}

DEFAULT_STRAND_PROFILE: dict[str, Any] = {
    'target_ratio': {'quest': 0.60, 'fire': 0.20, 'constellation': 0.20},
    'max_quest_streak': 5,
    'max_fire_gap': 10,
    'max_constellation_gap': 15,
    'strand_notes': '主线推进为主，适时穿插情感关系与世界格局调节阅读呼吸。',
}

# Concise Signal-vs-Spoiler directive for 06 plot_design / 09 scene_design
SIGNAL_VS_SPOILER_GUIDE = (
    '【章纲信号 vs 剧透护栏】严禁把后期大反转底牌（如“此人实为卧底/戒指里封印着大佬灵魂”）直接写成普通场景的行动节拍；'
    '底层真相仅留在作者/秘密卡中，普通章纲与场景卡只写角色当下可感知的具体「信号（Signal）」（如“老者袖口闪过异常旧印、态度反常热络”），'
    '唯有到达既定揭晓章时方可写明真相。'
)

# Max chapters a high-priority promise may stall without progress, by length tier
_STALL_LIMIT_BY_TIER: dict[str, int] = {
    'short': 5,
    'medium_short': 7,
    'medium': 10,
    'long': 13,
    'epic': 16,
}


def _tier_id_for_words(tw: int | None) -> str:
    if not isinstance(tw, int) or tw <= 0:
        return 'medium'
    if tw <= 399_999:
        return 'short'
    if tw <= 749_999:
        return 'medium_short'
    if tw <= 1_249_999:
        return 'medium'
    if tw <= 1_749_999:
        return 'long'
    return 'epic'


def strand_profile_for_spec(plot_spec: dict[str, Any] | None, *, target_words: int | None = None) -> dict[str, Any]:
    """Resolve genre- and length-compiled Strand Weave targets from the active Plot Spec."""
    base_id = str((plot_spec or {}).get('base_id') or '').strip()
    prof = dict(STRAND_PROFILES_BY_PLOT_BASE.get(base_id, DEFAULT_STRAND_PROFILE))
    scale = (plot_spec or {}).get('scale_profile') or compute_scale_profile(target_words)
    eff_words = target_words if isinstance(target_words, int) and target_words > 0 else scale.get('target_words')
    tier_id = str(scale.get('tier_id') or _tier_id_for_words(eff_words))
    # Compress gaps slightly for short novels, relax slightly for 1.5M-2M epic serials
    factor = {'short': 0.75, 'medium_short': 0.9, 'medium': 1.0, 'long': 1.15, 'epic': 1.25}.get(tier_id, 1.0)
    prof['tier_id'] = tier_id
    prof['tier_label'] = str(scale.get('tier_label') or tier_id)
    prof['base_id'] = base_id or 'DEFAULT'
    prof['max_fire_gap'] = max(3, round(prof['max_fire_gap'] * factor))
    prof['max_constellation_gap'] = max(5, round(prof['max_constellation_gap'] * factor))
    prof['promise_stall_limit'] = _STALL_LIMIT_BY_TIER.get(tier_id, 10)
    return prof


def _infer_chapter_telemetry_from_text(text: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic fallback classifier for chapters without explicit manual telemetry tags."""
    raw = (text or '').strip()
    stats = compute_prose_stats(raw)
    fire_kw = ('心动', '眼神', '牵手', '醋', '误会', '表白', '拥抱', '脸红', '师父', '情义', '背叛', '信任')
    const_kw = ('势力', '宗门', '王朝', '大陆', '规则', '世界', '禁区', '圣地', '古老', '纪元', '组织', '体系')
    fire_score = sum(raw.count(k) for k in fire_kw)
    const_score = sum(raw.count(k) for k in const_kw)
    if fire_score >= 4 and fire_score >= const_score + 2:
        strand = 'fire'
    elif const_score >= 4 and const_score > fire_score:
        strand = 'constellation'
    else:
        strand = 'quest'

    tail = raw[-280:] if raw else ''
    hook_type = 'mystery'
    hook_strength = 'medium'
    if any(k in tail for k in ('死', '杀', '血', '危', '刀', '剑', '围', '警报', '倒计时', '来不及')):
        hook_type, hook_strength = 'crisis', 'strong'
    elif any(k in tail for k in ('选择', '要么', '决定', '答应', '拒绝')):
        hook_type, hook_strength = 'choice', 'medium'
    elif any(k in tail for k in ('突破', '到手', '奖励', '明天', '大比', '翻盘', '筹码')):
        hook_type, hook_strength = 'desire', 'medium'
    elif any(k in tail for k in ('？', '?', '怎么会', '竟然', '原来', '却发现', '真相')):
        hook_type, hook_strength = 'mystery', 'strong'
    elif len(tail) < 60:
        hook_type, hook_strength = 'none', 'weak'

    promise_touched = any(
        op.get('predicate') == 'promise_stage' or op.get('op') in ('introduce_promise', 'advance_promise')
        for op in ops
    )
    return {
        'dominant_strand': strand,
        'hook_type': hook_type,
        'hook_strength': hook_strength,
        'micro_payoff_count': max(1, min(4, len(ops) or 1)),
        'promise_touched': 1 if promise_touched else 0,
        'stats': stats,
    }


def record_chapter_telemetry(
    store: Store,
    *,
    branch_id: str = 'main',
    chapter_index: int,
    dominant_strand: str = 'quest',
    hook_type: str = '',
    hook_strength: str = 'medium',
    micro_payoff_count: int = 1,
    promise_touched: bool = False,
    cold_read_want_next: str = '',
    cold_read_skip_count: int = 0,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert chapter serialization telemetry into `serial_chapter_metrics`."""
    strand = dominant_strand if dominant_strand in ('quest', 'fire', 'constellation') else 'quest'
    strength = hook_strength if hook_strength in ('strong', 'medium', 'weak', 'none') else 'medium'
    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''INSERT INTO serial_chapter_metrics(
                branch_id, chapter_index, dominant_strand, hook_type, hook_strength,
                micro_payoff_count, promise_touched, cold_read_want_next, cold_read_skip_count,
                stats_json, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(branch_id, chapter_index) DO UPDATE SET
                dominant_strand=excluded.dominant_strand,
                hook_type=excluded.hook_type,
                hook_strength=excluded.hook_strength,
                micro_payoff_count=excluded.micro_payoff_count,
                promise_touched=excluded.promise_touched,
                cold_read_want_next=CASE WHEN excluded.cold_read_want_next<>'' THEN excluded.cold_read_want_next ELSE serial_chapter_metrics.cold_read_want_next END,
                cold_read_skip_count=CASE WHEN excluded.cold_read_want_next<>'' THEN excluded.cold_read_skip_count ELSE serial_chapter_metrics.cold_read_skip_count END,
                stats_json=excluded.stats_json,
                updated_at=excluded.updated_at''',
            (branch_id, int(chapter_index), strand, str(hook_type or '')[:40], strength,
             max(0, int(micro_payoff_count)), 1 if promise_touched else 0,
             str(cold_read_want_next or '')[:20], max(0, int(cold_read_skip_count)),
             json.dumps(stats or {}, ensure_ascii=False), ts),
        )
    return {
        'branch_id': branch_id,
        'chapter_index': int(chapter_index),
        'dominant_strand': strand,
        'hook_type': str(hook_type or '')[:40],
        'hook_strength': strength,
        'micro_payoff_count': max(0, int(micro_payoff_count)),
        'promise_touched': bool(promise_touched),
        'cold_read_want_next': str(cold_read_want_next or ''),
        'cold_read_skip_count': max(0, int(cold_read_skip_count)),
        'updated_at': ts,
    }


def compute_promise_rhythm_debt(
    store: Store,
    head: StateHead,
    snapshot: dict[str, Any],
    current_chapter: int | None,
    *,
    stall_limit: int = 10,
) -> dict[str, Any]:
    """Upgrade promise_continuity with last_touched_chapter & Rhythm Debt detection."""
    settings = snapshot.get('settings') or []
    cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in settings]
    ops = selected_operations(store, snapshot)
    facts = replay(baseline_for(store, head.branch_id), ops)
    snap_rows = approved_promise_snapshot(store, settings, cards, facts, ops)
    reminder = continuation_reminder({}, {
        'promise_continuity': snap_rows,
        'current_chapter': current_chapter,
    }) if snap_rows else None

    # Derive last_advanced_chapter vs last_mentioned_chapter with strict `mention != advance` law
    from nw.promise_arbiter import parse_promise_op_semantics
    baseline_planted_ch: dict[str, int] = {}
    for raw_bf in (baseline_for(store, head.branch_id).get('facts') or ()):
        if raw_bf.get('predicate') == 'promise_stage' and raw_bf.get('entity_id'):
            disc = raw_bf.get('disclosure_order') or (0, 0, 0)
            bch = int(disc[0]) if isinstance(disc, (list, tuple)) and disc else 0
            if bch > 0:
                baseline_planted_ch[str(raw_bf['entity_id'])] = bch

    last_advanced: dict[str, int] = {}
    last_mentioned: dict[str, int] = {}
    for op in ops:
        if op.get('predicate') == 'promise_stage' or op.get('op') in ('introduce_promise', 'advance_promise'):
            ent = str(op.get('entity_id') or '')
            disc = op.get('disclosure_order') or (0, 0, 0)
            ch = int(disc[0]) if isinstance(disc, (list, tuple)) and disc else 0
            if not ent or ch <= 0:
                continue
            try:
                sem = parse_promise_op_semantics(op)
            except ValueError:
                sem = {'advances_progress': True, 'is_mention_only': False}
            if sem['advances_progress']:
                last_advanced[ent] = max(ch, last_advanced.get(ent, 0))
                last_mentioned[ent] = max(ch, last_mentioned.get(ent, 0))
            elif sem.get('is_mention_only'):
                last_mentioned[ent] = max(ch, last_mentioned.get(ent, 0))

    stalled: list[dict[str, Any]] = []
    enriched_items: list[dict[str, Any]] = []
    superseded_items: list[str] = []
    cur_ch = int(current_chapter) if isinstance(current_chapter, int) and current_chapter > 0 else 0
    latest_ch_touched = False

    for row in snap_rows:
        cid = row['card_id']
        stage = row.get('accepted_stage')
        if stage == 'superseded':
            superseded_items.append(cid)
            enriched_items.append({
                **row,
                'priority': 'archived',
                'last_touched_chapter': last_advanced.get(cid) or row.get('planted_chapter') or baseline_planted_ch.get(cid) or None,
                'last_advanced_chapter': last_advanced.get(cid) or row.get('planted_chapter') or baseline_planted_ch.get(cid) or None,
                'last_mentioned_chapter': last_mentioned.get(cid) or None,
                'mention_without_advance': False,
                'stalled_chapters': 0,
                'is_overdue': False,
                'is_superseded': True,
            })
            continue
        la = last_advanced.get(cid) or row.get('planted_chapter') or baseline_planted_ch.get(cid) or 0
        lm = last_mentioned.get(cid) or la
        if cur_ch and la == cur_ch:
            latest_ch_touched = True
        gap = max(0, cur_ch - la) if (cur_ch and la) else 0
        mention_only_stale = bool(lm > la and stage in ('planted', 'awake', 'sleeping'))
        sched = row.get('schedule') or {}
        payoff_ch = sched.get('payoff_chapter')
        is_overdue = bool(cur_ch and isinstance(payoff_ch, int) and cur_ch > payoff_ch and stage != 'paid_off')
        if is_overdue or (isinstance(payoff_ch, int) and cur_ch and payoff_ch - cur_ch <= 8):
            priority = 'high'
        elif stage in ('planted', 'awake', 'sleeping'):
            priority = 'medium'
        else:
            priority = 'low'

        enriched = {
            **row,
            'priority': priority,
            'last_touched_chapter': la or None,
            'last_advanced_chapter': la or None,
            'last_mentioned_chapter': lm or None,
            'mention_without_advance': mention_only_stale,
            'stalled_chapters': gap,
            'is_overdue': is_overdue,
            'is_superseded': False,
        }
        enriched_items.append(enriched)
        if stage in ('planted', 'sleeping', 'awake') and cur_ch and gap >= stall_limit:
            hint_extra = f'（第 {lm} 章仅顺口提及，未实质推进）' if mention_only_stale else ''
            stalled.append({
                'promise': cid,
                'title': row['title'][:96],
                'priority': priority,
                'last_touched_chapter': la,
                'last_advanced_chapter': la,
                'last_mentioned_chapter': lm,
                'mention_without_advance': mention_only_stale,
                'stalled_chapters': gap,
                'reason': f'已连续 {gap} 章未实质推进（超过当前篇幅档位 {stall_limit} 章阈值）{hint_extra}',
            })

    overdue = (reminder or {}).get('overdue_warnings') or []
    due = (reminder or {}).get('due_this_scene') or []
    return {
        'items': enriched_items,
        'lifecycle_counts': (reminder or {}).get('lifecycle_counts', {'unverified': 0, 'planted': 0, 'hinted': 0, 'paid_off': 0, 'superseded': 0}),
        'due': due,
        'overdue': overdue,
        'stalled': stalled,
        'superseded': superseded_items,
        'latest_chapter_touched_promise': latest_ch_touched,
        'rhythm_debt_count': len(overdue) + len(stalled),
    }


def build_serial_health_board(
    store: Store,
    *,
    branch: str = 'main',
    plot_spec: dict[str, Any] | None = None,
    target_words: int | None = None,
) -> dict[str, Any]:
    """Compute the full Serialization Cockpit & Pre-Chapter Decision Board (`章前盘面`)."""
    spec = plot_spec if plot_spec is not None else load_plot_pacing_spec(store)
    strand_prof = strand_profile_for_spec(spec, target_words=target_words)
    if not store.managed_story():
        return {
            'branch_id': branch,
            'latest_chapter': 0,
            'strand_profile': strand_prof,
            'strand_health': {'counts': {'quest': 0, 'fire': 0, 'constellation': 0}, 'alerts': []},
            'hook_health': {'weak_streak': 0, 'dominant_hook': '', 'alerts': []},
            'promise_debt': {'items': [], 'due': [], 'overdue': [], 'stalled': [], 'rhythm_debt_count': 0},
            'cold_read_trend': {'count': 0, 'want_next_yes_ratio': None, 'alerts': []},
            'rhythm_debt_score': 0,
            'status': 'healthy',
            'next_chapter_corrections': [],
        }

    head = current_head(store, branch)
    snapshot = revision_state(store, head)
    slots = snapshot.get('slots') or {}
    chapters = {c.id: c.index for c in store.list('chapter')}
    ops_all = selected_operations(store, snapshot)

    # Group accepted chapters and backfill missing telemetry deterministically
    ch_texts: dict[int, list[tuple[int, str]]] = {}
    for sc in store.list('scene'):
        slot = slots.get(sc.id)
        if not slot or not slot.get('draft_id'):
            continue
        ch_idx = chapters.get(sc.chapter_id)
        if ch_idx is None:
            continue
        d = store.get('draft', slot['draft_id'])
        if (d.text or '').strip():
            ch_texts.setdefault(ch_idx, []).append((sc.index, d.text.strip()))

    existing_rows = {
        int(row['chapter_index']): dict(row)
        for row in store.connection.execute(
            'SELECT * FROM serial_chapter_metrics WHERE branch_id=? ORDER BY chapter_index', (branch,)
        ).fetchall()
    }
    history: list[dict[str, Any]] = []
    for ch_idx in sorted(set(ch_texts.keys()) | set(existing_rows.keys())):
        if ch_idx in existing_rows:
            history.append(existing_rows[ch_idx])
        elif ch_idx in ch_texts:
            merged = '\n\n'.join(t for _, t in sorted(ch_texts[ch_idx]))
            ch_ops = [op for op in ops_all if (op.get('disclosure_order') or [0])[0] == ch_idx]
            inferred = _infer_chapter_telemetry_from_text(merged, ch_ops)
            history.append({'chapter_index': ch_idx, **inferred})

    latest_ch = max((int(r['chapter_index']) for r in history), default=0)

    # 1. Strand health
    counts = {'quest': 0, 'fire': 0, 'constellation': 0}
    last_seen = {'quest': 0, 'fire': 0, 'constellation': 0}
    quest_streak = 0
    for row in history:
        st = str(row.get('dominant_strand') or 'quest')
        ch = int(row['chapter_index'])
        if st in counts:
            counts[st] += 1
            last_seen[st] = ch
        quest_streak = (quest_streak + 1) if st == 'quest' else 0

    strand_alerts: list[str] = []
    if quest_streak >= strand_prof['max_quest_streak']:
        strand_alerts.append(f'已连续 {quest_streak} 章纯主线（阈值 {strand_prof["max_quest_streak"]} 章），建议下章穿插情感关系或世界格局线。')
    if latest_ch >= strand_prof['max_fire_gap'] and (latest_ch - last_seen['fire']) >= strand_prof['max_fire_gap']:
        strand_alerts.append(f'已连续 {latest_ch - last_seen["fire"]} 章未出现情感/关系线，建议下章安排角色互动或信任位移。')
    if latest_ch >= strand_prof['max_constellation_gap'] and (latest_ch - last_seen['constellation']) >= strand_prof['max_constellation_gap']:
        strand_alerts.append(f'已连续 {latest_ch - last_seen["constellation"]} 章未拓展世界/势力格局，建议下章露出一角新规则或新势力动向。')

    # 2. Hook fatigue & weak-hook streak
    weak_streak = 0
    recent_hooks: list[str] = []
    for row in history[-10:]:
        hs = str(row.get('hook_strength') or 'medium')
        ht = str(row.get('hook_type') or '')
        weak_streak = (weak_streak + 1) if hs in ('weak', 'none') else 0
        if ht and ht != 'none':
            recent_hooks.append(ht)
    hook_alerts: list[str] = []
    if weak_streak >= 3:
        hook_alerts.append(f'已连续 {weak_streak} 章弱钩/无钩，追读力亮红灯，下章必须设置高利害强钩子。')
    dominant_hook = ''
    if len(recent_hooks) >= 3 and len(set(recent_hooks[-3:])) == 1:
        dominant_hook = recent_hooks[-1]
        hook_alerts.append(f'近 3 章连续使用同类钩子「{dominant_hook}」，下章请切换异质钩子防止读者疲劳。')

    # 3. Promise Rhythm Debt
    promise_debt = compute_promise_rhythm_debt(
        store, head, snapshot, latest_ch or None,
        stall_limit=int(strand_prof['promise_stall_limit']),
    )
    active_overrides = list_overrides(store, branch_id=branch, status='active', limit=50)
    promise_exempted = any(
        o.get('constraint_code') == 'NO_PROMISE_TOUCH' and o.get('chapter_index') == latest_ch
        for o in active_overrides
    )
    promise_alerts: list[str] = []
    for ov in promise_debt['overdue'][:2]:
        promise_alerts.append(f'承诺超期：《{ov["title"]}》{ov.get("reason", "")}，下章须安排兑现或明确延期推进。')
    for st_item in promise_debt['stalled'][:2]:
        promise_alerts.append(f'承诺停滞债：《{st_item["title"]}》{st_item["reason"]}。')
    if latest_ch > 0 and promise_debt['items'] and not promise_debt['latest_chapter_touched_promise'] and not promise_exempted:
        promise_alerts.append(f'第 {latest_ch} 章未触达任何活跃承诺/伏笔，建议下章至少新埋、推进或兑现 1 条（如刻意留白可登记豁免）。')

    # 4. Blind Cold-Read trend
    cold_reports = list_cold_reads(store, limit=12)
    cr_wants = [
        str((r.get('parsed') or {}).get('keep_reading', {}).get('want_next') or 'unknown')
        for r in cold_reports
    ]
    valid_wants = [w for w in cr_wants if w in ('yes', 'weak', 'no')]
    yes_ratio = round(sum(1 for w in valid_wants if w == 'yes') / len(valid_wants), 2) if valid_wants else None
    skip_total = sum(len((r.get('parsed') or {}).get('skip_zones') or ()) for r in cold_reports[:5])
    cr_alerts: list[str] = []
    if len(valid_wants) >= 2 and sum(1 for w in valid_wants[:3] if w in ('weak', 'no')) >= 2:
        cr_alerts.append('近期盲态冷读连续反馈追读意愿偏弱，建议压缩铺垫并在章首 300 字内亮明本场阻力。')
    elif skip_total >= 4:
        cr_alerts.append(f'近 5 次盲态冷读累计出现 {skip_total} 处“想划走”区段，建议提高信息与冲突密度。')

    corrections = [*promise_alerts, *strand_alerts, *hook_alerts, *cr_alerts][:5]
    debt_score = (
        len(promise_debt['overdue']) * 3
        + len(promise_debt['stalled']) * 2
        + (2 if weak_streak >= 3 else 0)
        + len(strand_alerts)
        + len(cr_alerts)
    )
    status = 'alert' if debt_score >= 4 else ('watch' if debt_score >= 1 else 'healthy')

    return {
        'branch_id': branch,
        'latest_chapter': latest_ch,
        'chapters_tracked': len(history),
        'strand_profile': strand_prof,
        'strand_health': {
            'counts': counts,
            'quest_streak': quest_streak,
            'chapters_since_fire': max(0, latest_ch - last_seen['fire']) if latest_ch else 0,
            'chapters_since_constellation': max(0, latest_ch - last_seen['constellation']) if latest_ch else 0,
            'alerts': strand_alerts,
        },
        'hook_health': {
            'weak_streak': weak_streak,
            'dominant_hook': dominant_hook,
            'recent_hooks': recent_hooks[-5:],
            'alerts': hook_alerts,
        },
        'promise_debt': promise_debt,
        'cold_read_trend': {
            'count': len(cold_reports),
            'want_next_yes_ratio': yes_ratio,
            'recent_skip_zones': skip_total,
            'alerts': cr_alerts,
        },
        'rhythm_debt_score': debt_score,
        'status': status,
        'next_chapter_corrections': corrections,
        'signal_vs_spoiler_guide': SIGNAL_VS_SPOILER_GUIDE,
    }


def build_foreshadowing_opportunity_brief(store: Store, *, branch: str = 'main') -> dict[str, Any]:
    """Scan approved book/volume cards + open promises to prepare Volume-End Foreshadowing Opportunity prompts."""
    if not store.managed_story():
        return {'ready': False, 'future_anchors': [], 'open_promises': [], 'prompt_hint': ''}
    head = current_head(store, branch)
    snapshot = revision_state(store, head)
    future_anchors: list[dict[str, str]] = []
    open_promises: list[dict[str, str]] = []
    for ref in snapshot.get('settings') or ():
        card = read_card(store, CardRef(ref['card_id'], ref['version']))
        body = card.get('body') or {}
        if card['kind'] in ('volume', 'plot'):
            title = str(body.get('title') or card['card_id'])
            summary = '；'.join(
                str(body.get(k) or '').strip()
                for k in ('goal', 'turn', 'conflict', 'consequence', 'summary', 'climax', 'core_conflict')
                if str(body.get(k) or '').strip()
            )[:180]
            if summary:
                future_anchors.append({'card_id': card['card_id'], 'kind': card['kind'], 'title': title, 'anchor': summary})
        elif card['kind'] == 'promise':
            open_promises.append({'card_id': card['card_id'], 'title': str(body.get('title') or card['card_id'])[:96]})

    prompt_hint = ''
    if future_anchors:
        anchor_text = '；'.join(f'《{a["title"]}》:{a["anchor"][:60]}' for a in future_anchors[:5])
        prompt_hint = (
            '【卷级远期伏笔机会扫描】规划本卷时，对照全书远期锚点（'
            + anchor_text
            + '）与现有未回收承诺，主动提出 3–5 条「本卷可顺手自然埋设、未来指定卷/章引爆」的候选伏笔（每条必须指明对应远期锚点，杜绝悬空伏笔），交作者勾选入库。'
        )
    return {
        'ready': bool(future_anchors),
        'future_anchors': future_anchors[:8],
        'open_promises': open_promises[:12],
        'prompt_hint': prompt_hint,
    }
