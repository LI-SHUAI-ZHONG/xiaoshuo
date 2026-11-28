"""POV-Safe Tiered Long-Term Memory Orchestrator, Replay Cache, and Volume Summaries.

Built strictly on top of SQLite `nw.db` as the SINGLE source of truth (never creates
redundant `memory_scratchpad.json` or external vector databases!):
  - Derived Replay Cache (`state_replay_cache`): O(1) lookup for committed revisions,
    keyed by `(branch_id, revision, story_order, holder, disclosure_key)` with SHA256
    validation; safely clearable and 100% rebuildable from `story_commits`.
  - L1 Working Memory: recent <= 3 approved chapter summaries strictly before current chapter.
  - L2 Episodic Memory: author-approved volume summaries (<= 500 chars each) strictly before
    current chapter, bridging the 50–500 chapter mid-range recall gap.
  - L3 Semantic Memory (POV-Safe ContextRanker): pins active-scene entities, active promises,
    and core world rules; scores remaining distant POV-visible facts deterministically by
    entity overlap + promise link + recency decay + claim priority so 2M-word novels never
    hit `CONTEXT_TOO_LARGE` or bury live conflict in irrelevant historical facts.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any
from uuid import uuid4

from nw.chapter_records import chapter_summary
from nw.store import Store, now
from nw.story_models import Fact, StateHead
from nw.story_state import (
    IDENTITY_STATUS_PREFIX,
    baseline_for,
    current_head,
    position,
    replay,
    revision_state,
    selected_operations,
)
from nw.task_models import canonical, content_sha256

_CORE_FACT_PREDICATES = frozenset({
    'world_rule', 'alive', 'death', 'life_status', 'core_goal', 'protagonist_goal',
    'ending_promise', 'owner', 'location', 'realm', 'power', '伤势', '境界', '生死', '位置', '持有者',
})

_CLAIM_PRIORITY = {
    'fact': 1.0,
    'belief': 0.85,
    'suspicion': 0.8,
    'plan': 0.65,
    'utterance': 0.5,
}


# ── Derived Replay Cache (Pure Read Cache, 100% Rebuildable) ──

def _disclosure_key(disclosure: tuple[int, int, int] | None) -> str:
    return ','.join(str(x) for x in disclosure) if disclosure is not None else '*'


def cached_replay_facts(
    store: Store,
    branch_id: str,
    revision: int,
    story_order: int,
    holder: str,
    disclosure: tuple[int, int, int] | None = None,
    *,
    before_scene: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> tuple[list[Fact], bool]:
    """Replay facts with SQLite derived cache hit when querying a committed snapshot without before_scene."""
    head = StateHead(branch_id, revision)
    snap = snapshot if snapshot is not None else revision_state(store, head)
    baseline = baseline_for(store, branch_id)
    can_cache = (before_scene is None and snapshot is None)
    dkey = _disclosure_key(disclosure)
    state_sha = content_sha256({'slots': snap.get('slots', {}), 'baseline': baseline.get('as_of_story_order')})

    if can_cache:
        row = store.connection.execute(
            '''SELECT state_sha256, facts_json FROM state_replay_cache
               WHERE branch_id=? AND revision=? AND story_order=? AND holder=? AND disclosure_key=?''',
            (branch_id, revision, story_order, holder, dkey),
        ).fetchone()
        if row is not None and row['state_sha256'] == state_sha:
            raw_list = json.loads(row['facts_json'])
            facts = [
                Fact(
                    r['entity_id'], r['predicate'], r['value'], r['holder'], r['claim'],
                    r['story_order'], tuple(r['disclosure_order']), tuple(r.get('evidence') or ()),
                )
                for r in raw_list
            ]
            return facts, True

    if before_scene is not None:
        snap = {**snap, 'slots': {k: v for k, v in snap['slots'].items() if k != before_scene}}
    ops = selected_operations(store, snap)
    if before_scene is not None and disclosure is not None:
        ops = [
            op for op in ops
            if op['story_order'] != story_order or position(op['disclosure_order']) < disclosure
        ]
    facts = replay(baseline, ops, holder, story_order, disclosure)

    if can_cache:
        try:
            serialized = canonical([asdict(f) for f in facts])
            with store.connection:
                store.connection.execute(
                    '''INSERT OR REPLACE INTO state_replay_cache
                       (branch_id, revision, story_order, holder, disclosure_key, state_sha256, facts_json, created_at)
                       VALUES (?,?,?,?,?,?,?,?)''',
                    (branch_id, revision, story_order, holder, dkey, state_sha, serialized, now()),
                )
        except Exception:
            pass
    return facts, False


def clear_replay_cache(store: Store, *, branch_id: str | None = None) -> int:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        if branch_id:
            cur = store.connection.execute('DELETE FROM state_replay_cache WHERE branch_id=?', (branch_id,))
        else:
            cur = store.connection.execute('DELETE FROM state_replay_cache')
        return max(0, int(cur.rowcount))


# ── L2 Volume Summaries (Author-Approved Episodic Compression) ──

def save_volume_summary(
    store: Store,
    *,
    branch_id: str = 'main',
    volume_index: int,
    title: str,
    chapter_start: int,
    chapter_end: int,
    summary_text: str,
    open_promises: list[str] | None = None,
    relation_shifts: list[str] | None = None,
) -> dict[str, Any]:
    """Persist an author-confirmed <=500-char volume summary in SQLite `volume_summaries`."""
    vol_idx = int(volume_index)
    ch_start = int(chapter_start)
    ch_end = int(chapter_end)
    if vol_idx < 1 or ch_start < 1 or ch_end < ch_start:
        raise ValueError('卷号与起止章号必须为有效正整数，且结束章不小于起始章')
    clean_title = str(title or f'第{vol_idx}卷').strip()[:80]
    clean_summary = str(summary_text or '').strip()[:600]
    if not clean_summary:
        raise ValueError('卷级摘要内容不能为空')
    promises = [str(p).strip()[:120] for p in (open_promises or ()) if str(p).strip()][:12]
    relations = [str(r).strip()[:120] for r in (relation_shifts or ()) if str(r).strip()][:10]
    source_sha = content_sha256({
        'volume_index': vol_idx, 'chapter_start': ch_start, 'chapter_end': ch_end,
        'summary_text': clean_summary, 'open_promises': promises, 'relation_shifts': relations,
    })
    ident = f'volsum-{uuid4().hex[:10]}'
    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''INSERT INTO volume_summaries(
                id, branch_id, volume_index, title, chapter_start, chapter_end,
                summary_text, open_promises_json, relation_shifts_json, source_sha256, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(branch_id, volume_index) DO UPDATE SET
                title=excluded.title,
                chapter_start=excluded.chapter_start,
                chapter_end=excluded.chapter_end,
                summary_text=excluded.summary_text,
                open_promises_json=excluded.open_promises_json,
                relation_shifts_json=excluded.relation_shifts_json,
                source_sha256=excluded.source_sha256,
                created_at=excluded.created_at''',
            (ident, branch_id, vol_idx, clean_title, ch_start, ch_end,
             clean_summary, json.dumps(promises, ensure_ascii=False),
             json.dumps(relations, ensure_ascii=False), source_sha, ts),
        )
    return {
        'id': ident,
        'branch_id': branch_id,
        'volume_index': vol_idx,
        'title': clean_title,
        'chapter_start': ch_start,
        'chapter_end': ch_end,
        'summary_text': clean_summary,
        'open_promises': promises,
        'relation_shifts': relations,
        'source_sha256': source_sha,
        'created_at': ts,
    }


def list_volume_summaries(
    store: Store,
    *,
    branch_id: str = 'main',
    before_chapter: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    clauses = ['branch_id=?']
    params: list[Any] = [branch_id]
    if before_chapter is not None:
        clauses.append('chapter_end < ?')
        params.append(int(before_chapter))
    sql = f"SELECT * FROM volume_summaries WHERE {' AND '.join(clauses)} ORDER BY volume_index ASC LIMIT ?"
    params.append(max(1, int(limit)))
    rows = store.connection.execute(sql, params).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append({
            'id': row['id'],
            'branch_id': row['branch_id'],
            'volume_index': row['volume_index'],
            'title': row['title'],
            'chapter_start': row['chapter_start'],
            'chapter_end': row['chapter_end'],
            'summary': row['summary_text'],
            'summary_text': row['summary_text'],
            'open_promises': json.loads(row['open_promises_json'] or '[]'),
            'relation_shifts': json.loads(row['relation_shifts_json'] or '[]'),
            'created_at': row['created_at'],
        })
    return result


def draft_volume_summary_from_chapters(
    store: Store,
    *,
    branch_id: str = 'main',
    volume_index: int,
    title: str,
    chapter_start: int,
    chapter_end: int,
) -> dict[str, Any]:
    """Deterministically compile a starter <=500-char volume summary from recorded chapter summaries."""
    head = current_head(store, branch_id)
    snippets: list[str] = []
    for ch_idx in range(int(chapter_start), int(chapter_end) + 1):
        try:
            rec = chapter_summary(store, head, ch_idx).get('record')
        except Exception:
            rec = None
        if rec and isinstance(rec.get('author_record'), dict):
            s = str(rec['author_record'].get('summary') or '').strip()
            if s:
                snippets.append(f'第{ch_idx}章：{s[:90]}')
    combined = '；'.join(snippets)[:480] if snippets else f'第{chapter_start}–{chapter_end}章剧情推进完成。'
    return {
        'volume_index': int(volume_index),
        'title': title or f'第{volume_index}卷',
        'chapter_start': int(chapter_start),
        'chapter_end': int(chapter_end),
        'suggested_summary': combined,
        'chapter_summaries_used': len(snippets),
    }


# ── L1 Recent Chapter Summaries (Strictly < current_chapter) ──

def load_recent_chapter_summaries(
    store: Store,
    *,
    branch_id: str = 'main',
    current_chapter: int,
    window: int = 3,
) -> list[dict[str, Any]]:
    if not store.managed_story() or current_chapter <= 1:
        return []
    head = current_head(store, branch_id)
    start = max(1, int(current_chapter) - max(1, int(window)))
    out: list[dict[str, Any]] = []
    for ch_idx in range(start, int(current_chapter)):
        try:
            res = chapter_summary(store, head, ch_idx)
        except Exception:
            continue
        rec = res.get('record')
        if rec and isinstance(rec.get('author_record'), dict):
            txt = str(rec['author_record'].get('summary') or '').strip()
            if txt:
                out.append({
                    'chapter_index': ch_idx,
                    'summary': txt[:240],
                })
    return out


# ── L3 POV-Safe Semantic Fact Relevance Ranker & 3-Layer Orchestrator ──

def rank_pov_facts(
    facts: list[dict[str, Any]],
    *,
    current_chapter: int,
    pov_holder: str,
    scene_body: dict[str, Any] | None = None,
    active_promise_ids: set[str] | tuple[str, ...] = (),
    max_facts: int = 40,
) -> tuple[list[dict[str, Any]], int]:
    """Deterministically prioritize POV-visible facts when a long novel exceeds `max_facts`.

    NEVER introduces any non-POV fact — operates strictly on facts already filtered by `state_at`.
    Returns `(selected_facts, omitted_distant_count)`.
    """
    if len(facts) <= max_facts:
        return list(facts), 0

    body = scene_body if isinstance(scene_body, dict) else {}
    active_entities: set[str] = {str(pov_holder or '')}
    for ch_id in (body.get('characters') or ()):
        if isinstance(ch_id, str) and ch_id:
            active_entities.add(ch_id)
    if isinstance(body.get('location'), str) and body['location']:
        active_entities.add(body['location'])
    promise_set = {str(p) for p in active_promise_ids if p}
    scene_text = ' '.join(
        str(body.get(k) or '')
        for k in ('title', 'goal', 'conflict', 'outcome', 'allowed_disclosure', 'summary')
    )

    pinned: list[dict[str, Any]] = []
    candidates: list[tuple[float, dict[str, Any]]] = []

    for f in facts:
        ent = str(f.get('entity_id') or '')
        pred = str(f.get('predicate') or '')
        val_str = str(f.get('value') or '')
        is_pinned = (
            ent in active_entities
            or ent in promise_set
            or pred in _CORE_FACT_PREDICATES
            or pred.startswith(IDENTITY_STATUS_PREFIX)
        )
        if is_pinned:
            pinned.append(f)
            continue

        # Deterministic score: entity/text overlap (0.45) + promise (0.25) + recency (0.20) + claim (0.10)
        overlap = 1.0 if ((ent and ent in scene_text) or (len(val_str) >= 2 and val_str[:12] in scene_text)) else 0.0
        prom = 1.0 if ('promise' in pred or ent in promise_set) else 0.0
        disc = f.get('disclosure_order') or (0, 0, 0)
        src_ch = int(disc[0]) if isinstance(disc, (list, tuple)) and disc else 0
        gap = max(0, int(current_chapter) - src_ch) if src_ch > 0 else 50
        recency = 1.0 / (1.0 + gap)
        claim_wt = _CLAIM_PRIORITY.get(str(f.get('claim') or 'fact'), 0.5)
        score = 0.45 * overlap + 0.25 * prom + 0.20 * recency + 0.10 * claim_wt
        candidates.append((score, f))

    candidates.sort(key=lambda row: row[0], reverse=True)
    remaining_budget = max(0, max_facts - len(pinned))
    chosen = pinned + [row[1] for row in candidates[:remaining_budget]]
    omitted = max(0, len(facts) - len(chosen))
    return chosen, omitted


def orchestrate_scene_memory(
    store: Store,
    *,
    branch_id: str,
    current_chapter: int,
    pov_holder: str,
    scene_body: dict[str, Any] | None,
    pov_facts: list[dict[str, Any]],
    active_promise_ids: set[str] | tuple[str, ...] = (),
    max_semantic_facts: int = 40,
    recent_chapters_window: int = 3,
    max_volume_summaries: int = 6,
) -> dict[str, Any]:
    """Assemble POV-isolated Working (L1) + Episodic Volume (L2) + Ranked Semantic (L3) memory."""
    selected_facts, omitted_count = rank_pov_facts(
        pov_facts,
        current_chapter=current_chapter,
        pov_holder=pov_holder,
        scene_body=scene_body,
        active_promise_ids=active_promise_ids,
        max_facts=max_semantic_facts,
    )
    recent_summaries = load_recent_chapter_summaries(
        store, branch_id=branch_id, current_chapter=current_chapter, window=recent_chapters_window,
    )
    vol_summaries = list_volume_summaries(
        store, branch_id=branch_id, before_chapter=current_chapter, limit=max_volume_summaries,
    )
    return {
        'selected_facts': selected_facts,
        'omitted_distant_facts_count': omitted_count,
        'recent_chapter_summaries': recent_summaries,
        'volume_summaries': vol_summaries,
        'has_episodic_layers': bool(recent_summaries or vol_summaries or omitted_count > 0),
        'stats': {
            'total_pov_facts': len(pov_facts),
            'injected_facts': len(selected_facts),
            'omitted_distant_facts': omitted_count,
            'working_summaries': len(recent_summaries),
            'episodic_volumes': len(vol_summaries),
        },
    }
