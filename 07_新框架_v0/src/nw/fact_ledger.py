"""SQLite v15 Epistemic & Numeric Fact Ledger (Fusion O).

Tracks custom world terminology, hard numeric facts (ages, timelines, money, headcounts),
and planned foreshadow reveals with strict epistemic separation:
  - `first_chapter`: when a term/fact first appears (triggers inline clue rule!)
  - `reader_known`: what the reader is currently allowed to know
  - `full_truth`: author-side complete truth (NEVER leaked before `planned_reveal_chapter`)
  - `planned_reveal_chapter`: chapter where the reveal MUST pay off (`到期必兑`)
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from nw.store import Store, now

FACT_CATEGORIES = ('term', 'number', 'timeline', 'foreshadow')
FACT_STATUSES = ('active', 'revealed', 'retired')
CATEGORY_LABELS = {
    'term': '设定名词',
    'number': '硬数字事实',
    'timeline': '时间线锚点',
    'foreshadow': '伏笔/母题',
}


def _row_to_entry(row: Any) -> dict[str, Any]:
    return {
        'id': row['id'],
        'branch_id': row['branch_id'],
        'category': row['category'],
        'category_label': CATEGORY_LABELS.get(row['category'], row['category']),
        'name': row['name'],
        'first_chapter': int(row['first_chapter']),
        'reader_known': row['reader_known'],
        'full_truth': row['full_truth'],
        'planned_reveal_chapter': row['planned_reveal_chapter'],
        'status': row['status'],
        'source_scene_id': row['source_scene_id'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def upsert_fact_entry(
    store: Store,
    *,
    name: str,
    category: str = 'term',
    first_chapter: int = 1,
    reader_known: str = '',
    full_truth: str = '',
    planned_reveal_chapter: int | None = None,
    status: str = 'active',
    branch_id: str = 'main',
    source_scene_id: str = '',
    entry_id: str = '',
) -> dict[str, Any]:
    clean_name = str(name or '').strip()[:120]
    if not clean_name:
        raise ValueError('词典条目名称不能为空')
    cat = str(category or 'term').strip().lower()
    if cat not in FACT_CATEGORIES:
        raise ValueError(f'无效的事实类别: {category}（允许 term / number / timeline / foreshadow）')
    st = str(status or 'active').strip().lower()
    if st not in FACT_STATUSES:
        raise ValueError(f'无效的状态: {status}')
    fc = max(0, int(first_chapter or 0))
    prc = int(planned_reveal_chapter) if planned_reveal_chapter not in (None, '') else None
    ts = now()

    with store.connection:
        if entry_id:
            existing = store.connection.execute('SELECT id FROM fact_ledger WHERE id=?', (entry_id,)).fetchone()
        else:
            existing = store.connection.execute(
                'SELECT id FROM fact_ledger WHERE branch_id=? AND name=? AND category=?',
                (branch_id, clean_name, cat),
            ).fetchone()
        if existing:
            eid = existing['id']
            store.connection.execute(
                '''UPDATE fact_ledger
                   SET category=?, name=?, first_chapter=?, reader_known=?, full_truth=?,
                       planned_reveal_chapter=?, status=?, source_scene_id=?, updated_at=?
                   WHERE id=?''',
                (
                    cat, clean_name, fc, str(reader_known or '').strip()[:300],
                    str(full_truth or '').strip()[:400], prc, st, str(source_scene_id or ''), ts, eid,
                ),
            )
        else:
            eid = entry_id or f'fl-{uuid4().hex[:12]}'
            store.connection.execute(
                '''INSERT INTO fact_ledger
                   (id, branch_id, category, name, first_chapter, reader_known, full_truth,
                    planned_reveal_chapter, status, source_scene_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (
                    eid, branch_id, cat, clean_name, fc, str(reader_known or '').strip()[:300],
                    str(full_truth or '').strip()[:400], prc, st, str(source_scene_id or ''), ts, ts,
                ),
            )
    row = store.connection.execute('SELECT * FROM fact_ledger WHERE id=?', (eid,)).fetchone()
    return _row_to_entry(row)


def list_fact_entries(
    store: Store,
    *,
    branch_id: str = 'main',
    category: str = '',
    status: str = '',
) -> list[dict[str, Any]]:
    clauses = ['branch_id=?']
    params: list[Any] = [branch_id]
    if category:
        clauses.append('category=?')
        params.append(category)
    if status:
        clauses.append('status=?')
        params.append(status)
    rows = store.connection.execute(
        f'SELECT * FROM fact_ledger WHERE {" AND ".join(clauses)} ORDER BY first_chapter ASC, updated_at DESC',
        tuple(params),
    ).fetchall()
    return [_row_to_entry(r) for r in rows]


def delete_fact_entry(store: Store, entry_id: str) -> dict[str, Any]:
    with store.connection:
        cur = store.connection.execute('DELETE FROM fact_ledger WHERE id=?', (entry_id,))
    return {'deleted': cur.rowcount > 0, 'id': entry_id}


def build_writer_fact_ledger_packet(
    store: Store,
    *,
    branch_id: str = 'main',
    chapter_index: int = 1,
    max_chars: int = 900,
) -> dict[str, Any] | None:
    """Build POV-safe writer packet of hard numbers, first-appearance terms & due reveals.

    Critically: NEVER exposes `full_truth` before `planned_reveal_chapter`!
    """
    try:
        entries = list_fact_entries(store, branch_id=branch_id, status='active')
    except Exception:
        return None
    if not entries:
        return None

    hard_numbers: list[str] = []
    first_terms: list[str] = []
    known_terms: list[str] = []
    due_reveals: list[str] = []

    for e in entries:
        fc = e['first_chapter']
        prc = e['planned_reveal_chapter']
        rk = e['reader_known'] or '按正文自然呈现'
        if prc is not None and prc == chapter_index:
            truth_hint = f'（到期揭示要点：{e["full_truth"][:120]}）' if e['full_truth'] else ''
            due_reveals.append(f'【第{chapter_index}章到期必兑】{e["name"]}：当前读者已知「{rk}」{truth_hint}')
        elif e['category'] in ('number', 'timeline') and fc <= chapter_index:
            hard_numbers.append(f'{e["name"]} = {rk}（第{fc}章确立，禁止现场改数）')
        elif e['category'] == 'term':
            if fc == chapter_index:
                first_terms.append(f'【本章首现】「{e["name"]}」→ 读者应知：{rk}（首现须带类别与可感特征/角色反应/对话点透三选一，禁空抛黑话）')
            elif fc < chapter_index:
                known_terms.append(f'「{e["name"]}」：读者仅知「{rk}」（严禁越界提前剧透未揭示真相）')

    lines: list[str] = []
    for grp in (due_reveals[:4], first_terms[:4], hard_numbers[:8], known_terms[:6]):
        for item in grp:
            if sum(len(x) for x in lines) + len(item) + 4 <= max_chars:
                lines.append(item)
    if not lines:
        return None
    return {
        'chapter_index': chapter_index,
        'due_reveals_count': len(due_reveals),
        'first_terms_count': len(first_terms),
        'hard_numbers_count': len(hard_numbers),
        'lines': lines,
    }
