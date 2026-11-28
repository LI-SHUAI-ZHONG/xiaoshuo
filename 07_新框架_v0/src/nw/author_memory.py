"""Two-Level Cross-Book Author Memory with Strict 2KB Writer-Line Budget (Fusion J).

Separates durable author craft/workflow preferences into two strictly scoped stores:
  1. Global Author Memory (`library.db::global_author_memory`, IDs `AP001...`):
     - `global` (applies across all books)
     - `genre` (applies when book's genres intersect `genre_tags`)
     - `workflow` (applies to a specific workflow stage like `writing` / `review` / `planning`)
  2. Book Author Memory (`nw.db::book_author_memory`, IDs `BP001...`):
     - Travels with the book's SQLite database; can explicitly override a specific `AP`
       preference via `overrides_global_id` without mutating the cross-book global store.

Explicit-only mutation (`remember`, `replace` in same store only, `forget` with audit trail).
Writer injection strictly measures UTF-8 bytes of rendered lines ONLY (`- <assertion>（<id>）\n`,
default 2,048 bytes), prioritizing `importance -> book override (BP) -> recency`, and ALWAYS
emits transparent `omitted_ids`, `omitted_summaries`, and `omission_notice` so preferences
are NEVER silently dropped!
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from nw.store import Store, now
from nw.studio.catalog import canonical_types

MEMORY_KINDS = frozenset({'prose', 'dialogue', 'pacing', 'character', 'world', 'workflow', 'taboo', 'other'})
GLOBAL_SCOPES = frozenset({'global', 'genre', 'workflow'})
DEFAULT_WRITER_BYTE_BUDGET = 2048

GLOBAL_AUTHOR_MEMORY_SCHEMA = '''
CREATE TABLE IF NOT EXISTS global_author_memory (
 id TEXT PRIMARY KEY,
 scope TEXT NOT NULL DEFAULT 'global' CHECK(scope IN ('global','genre','workflow')),
 genre_tags_json TEXT NOT NULL DEFAULT '[]',
 workflow_stage TEXT NOT NULL DEFAULT '',
 kind TEXT NOT NULL DEFAULT 'prose' CHECK(kind IN ('prose','dialogue','pacing','character','world','workflow','taboo','other')),
 assertion TEXT NOT NULL CHECK(length(trim(assertion))>0),
 importance INTEGER NOT NULL DEFAULT 3 CHECK(importance BETWEEN 1 AND 5),
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','replaced','forgotten')),
 replaced_by TEXT NOT NULL DEFAULT '',
 source TEXT NOT NULL DEFAULT 'author_explicit',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS global_author_memory_status ON global_author_memory(status,scope,importance);
'''


def ensure_global_author_memory_table(conn: sqlite3.Connection) -> None:
    conn.executescript(GLOBAL_AUTHOR_MEMORY_SCHEMA)


def _next_seq_id(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    rows = conn.execute(f'SELECT id FROM {table} WHERE id LIKE ?', (f'{prefix}%',)).fetchall()
    max_num = 0
    for row in rows:
        raw = str(row['id'] if isinstance(row, sqlite3.Row) else row[0])
        suffix = raw[len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f'{prefix}{max_num + 1:03d}'


def _clean_kind(kind: str) -> str:
    k = str(kind or 'prose').strip().lower()
    if k not in MEMORY_KINDS:
        raise ValueError(f'无效的作者偏好分类: {kind}')
    return k


def _clean_importance(importance: int | None) -> int:
    val = 3 if importance is None else int(importance)
    if not (1 <= val <= 5):
        raise ValueError('偏好重要度须在 1–5 之间')
    return val


def _clean_assertion(assertion: str) -> str:
    txt = str(assertion or '').strip()
    if not txt:
        raise ValueError('作者偏好内容不能为空')
    if len(txt) > 240:
        raise ValueError('单条作者偏好建议精炼控制在 240 字以内')
    return txt


def _global_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': row['id'],
        'level': 'global',
        'scope': row['scope'],
        'genre_tags': json.loads(row['genre_tags_json'] or '[]'),
        'workflow_stage': row['workflow_stage'],
        'kind': row['kind'],
        'assertion': row['assertion'],
        'importance': int(row['importance']),
        'status': row['status'],
        'replaced_by': row['replaced_by'],
        'source': row['source'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def _book_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': row['id'],
        'level': 'book',
        'scope': 'book',
        'genre_tags': [],
        'workflow_stage': '',
        'kind': row['kind'],
        'assertion': row['assertion'],
        'importance': int(row['importance']),
        'overrides_global_id': row['overrides_global_id'],
        'status': row['status'],
        'replaced_by': row['replaced_by'],
        'source': row['source'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def remember_global_preference(
    conn: sqlite3.Connection,
    *,
    assertion: str,
    kind: str = 'prose',
    scope: str = 'global',
    genre_tags: list[str] | tuple[str, ...] | None = None,
    workflow_stage: str = '',
    importance: int = 3,
    source: str = 'author_explicit',
) -> dict[str, Any]:
    """Explicitly store a cross-book global/genre/workflow author preference in `library.db`."""
    ensure_global_author_memory_table(conn)
    clean_scope = str(scope or 'global').strip().lower()
    if clean_scope not in GLOBAL_SCOPES:
        raise ValueError(f'无效的全局作用域: {scope}（须为 global / genre / workflow）')
    clean_kind = _clean_kind(kind)
    clean_text = _clean_assertion(assertion)
    clean_imp = _clean_importance(importance)
    norm_genres = canonical_types(list(genre_tags)) if genre_tags else []
    stage = str(workflow_stage or '').strip()[:40]
    if clean_scope == 'genre' and not norm_genres:
        raise ValueError('题材级全局偏好（scope=genre）必须至少指定 1 个题材标签')
    if clean_scope == 'workflow' and not stage:
        raise ValueError('工序级全局偏好（scope=workflow）必须指定阶段名（如 writing / review / planning）')

    ts = now()
    ident = _next_seq_id(conn, 'global_author_memory', 'AP')
    conn.execute(
        '''INSERT INTO global_author_memory
           (id, scope, genre_tags_json, workflow_stage, kind, assertion, importance, status, replaced_by, source, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,'active','',?,?,?)''',
        (ident, clean_scope, json.dumps(norm_genres, ensure_ascii=False), stage,
         clean_kind, clean_text, clean_imp, str(source or 'author_explicit')[:60], ts, ts),
    )
    row = conn.execute('SELECT * FROM global_author_memory WHERE id=?', (ident,)).fetchone()
    return _global_row_to_dict(row)


def remember_book_preference(
    store: Store,
    *,
    assertion: str,
    kind: str = 'prose',
    importance: int = 3,
    overrides_global_id: str = '',
    source: str = 'author_explicit',
) -> dict[str, Any]:
    """Explicitly store a book-local preference in `nw.db::book_author_memory` (`BP001...`)."""
    clean_kind = _clean_kind(kind)
    clean_text = _clean_assertion(assertion)
    clean_imp = _clean_importance(importance)
    ovr_id = str(overrides_global_id or '').strip().upper()
    if ovr_id and not ovr_id.startswith('AP'):
        raise ValueError('overrides_global_id 须指向跨书全局偏好编号（如 AP001）')

    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        ident = _next_seq_id(store.connection, 'book_author_memory', 'BP')
        store.connection.execute(
            '''INSERT INTO book_author_memory
               (id, kind, assertion, importance, overrides_global_id, status, replaced_by, source, created_at, updated_at)
               VALUES (?,?,?,?,?,'active','',?,?,?)''',
            (ident, clean_kind, clean_text, clean_imp, ovr_id, str(source or 'author_explicit')[:60], ts, ts),
        )
    row = store.connection.execute('SELECT * FROM book_author_memory WHERE id=?', (ident,)).fetchone()
    return _book_row_to_dict(row)


def list_global_preferences(
    conn: sqlite3.Connection,
    *,
    status: str | None = 'active',
    scope: str | None = None,
) -> list[dict[str, Any]]:
    ensure_global_author_memory_table(conn)
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append('status=?')
        params.append(status)
    if scope:
        clauses.append('scope=?')
        params.append(scope)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = conn.execute(
        f'SELECT * FROM global_author_memory {where} ORDER BY importance DESC, updated_at DESC, id DESC',
        params,
    ).fetchall()
    return [_global_row_to_dict(r) for r in rows]


def list_book_preferences(
    store: Store,
    *,
    status: str | None = 'active',
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append('status=?')
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = store.connection.execute(
        f'SELECT * FROM book_author_memory {where} ORDER BY importance DESC, updated_at DESC, id DESC',
        params,
    ).fetchall()
    return [_book_row_to_dict(r) for r in rows]


def replace_preference(
    target_id: str,
    *,
    new_assertion: str,
    importance: int | None = None,
    kind: str | None = None,
    library_conn: sqlite3.Connection | None = None,
    store: Store | None = None,
) -> dict[str, Any]:
    """Replace an existing preference strictly within its own store (`AP` in global, `BP` in book)."""
    tid = str(target_id or '').strip().upper()
    clean_text = _clean_assertion(new_assertion)
    ts = now()

    if tid.startswith('AP'):
        if library_conn is None:
            raise ValueError('替换跨书全局偏好（AP）需要传入 library.db 连接')
        ensure_global_author_memory_table(library_conn)
        old = library_conn.execute('SELECT * FROM global_author_memory WHERE id=?', (tid,)).fetchone()
        if old is None:
            raise ValueError(f'未找到跨书全局偏好: {tid}')
        if old['status'] != 'active':
            raise ValueError(f'偏好 {tid} 当前状态为 {old["status"]}，不可替换')
        new_imp = _clean_importance(old['importance'] if importance is None else importance)
        new_kind = _clean_kind(old['kind'] if kind is None else kind)
        new_id = _next_seq_id(library_conn, 'global_author_memory', 'AP')
        library_conn.execute(
            '''INSERT INTO global_author_memory
               (id, scope, genre_tags_json, workflow_stage, kind, assertion, importance, status, replaced_by, source, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,'active','',?,?,?)''',
            (new_id, old['scope'], old['genre_tags_json'], old['workflow_stage'],
             new_kind, clean_text, new_imp, old['source'], ts, ts),
        )
        library_conn.execute(
            "UPDATE global_author_memory SET status='replaced', replaced_by=?, updated_at=? WHERE id=?",
            (new_id, ts, tid),
        )
        row = library_conn.execute('SELECT * FROM global_author_memory WHERE id=?', (new_id,)).fetchone()
        return {'replaced_id': tid, 'new_item': _global_row_to_dict(row)}

    if tid.startswith('BP'):
        if store is None:
            raise ValueError('替换本书偏好（BP）需要传入本书 Store')
        with store.connection:
            store.connection.execute('BEGIN IMMEDIATE')
            old = store.connection.execute('SELECT * FROM book_author_memory WHERE id=?', (tid,)).fetchone()
            if old is None:
                raise ValueError(f'未找到本书偏好: {tid}')
            if old['status'] != 'active':
                raise ValueError(f'偏好 {tid} 当前状态为 {old["status"]}，不可替换')
            new_imp = _clean_importance(old['importance'] if importance is None else importance)
            new_kind = _clean_kind(old['kind'] if kind is None else kind)
            new_id = _next_seq_id(store.connection, 'book_author_memory', 'BP')
            store.connection.execute(
                '''INSERT INTO book_author_memory
                   (id, kind, assertion, importance, overrides_global_id, status, replaced_by, source, created_at, updated_at)
                   VALUES (?,?,?,?,?,'active','',?,?,?)''',
                (new_id, new_kind, clean_text, new_imp, old['overrides_global_id'], old['source'], ts, ts),
            )
            store.connection.execute(
                "UPDATE book_author_memory SET status='replaced', replaced_by=?, updated_at=? WHERE id=?",
                (new_id, ts, tid),
            )
        row = store.connection.execute('SELECT * FROM book_author_memory WHERE id=?', (new_id,)).fetchone()
        return {'replaced_id': tid, 'new_item': _book_row_to_dict(row)}

    raise ValueError(f'无法识别的偏好编号前缀（须为 AP 或 BP）: {target_id}')


def forget_preference(
    target_id: str,
    *,
    library_conn: sqlite3.Connection | None = None,
    store: Store | None = None,
) -> dict[str, Any]:
    """Soft-forget a preference (marks status='forgotten', preserving full audit trail)."""
    tid = str(target_id or '').strip().upper()
    ts = now()
    if tid.startswith('AP'):
        if library_conn is None:
            raise ValueError('遗忘跨书全局偏好（AP）需要传入 library.db 连接')
        ensure_global_author_memory_table(library_conn)
        old = library_conn.execute('SELECT id FROM global_author_memory WHERE id=?', (tid,)).fetchone()
        if old is None:
            raise ValueError(f'未找到跨书全局偏好: {tid}')
        library_conn.execute(
            "UPDATE global_author_memory SET status='forgotten', updated_at=? WHERE id=?",
            (ts, tid),
        )
        return {'id': tid, 'level': 'global', 'status': 'forgotten'}
    if tid.startswith('BP'):
        if store is None:
            raise ValueError('遗忘本书偏好（BP）需要传入本书 Store')
        with store.connection:
            store.connection.execute('BEGIN IMMEDIATE')
            old = store.connection.execute('SELECT id FROM book_author_memory WHERE id=?', (tid,)).fetchone()
            if old is None:
                raise ValueError(f'未找到本书偏好: {tid}')
            store.connection.execute(
                "UPDATE book_author_memory SET status='forgotten', updated_at=? WHERE id=?",
                (ts, tid),
            )
        return {'id': tid, 'level': 'book', 'status': 'forgotten'}
    raise ValueError(f'无法识别的偏好编号前缀（须为 AP 或 BP）: {target_id}')


def promote_book_preference_to_global(
    store: Store,
    library_conn: sqlite3.Connection,
    book_pref_id: str,
    *,
    scope: str = 'global',
    genre_tags: list[str] | tuple[str, ...] | None = None,
    workflow_stage: str = '',
) -> dict[str, Any]:
    """Promote a validated book-local preference (`BP...`) into cross-book global memory (`AP...`)."""
    bid = str(book_pref_id or '').strip().upper()
    row = store.connection.execute('SELECT * FROM book_author_memory WHERE id=?', (bid,)).fetchone()
    if row is None:
        raise ValueError(f'未找到本书偏好: {bid}')
    created = remember_global_preference(
        library_conn,
        assertion=row['assertion'],
        kind=row['kind'],
        scope=scope,
        genre_tags=genre_tags,
        workflow_stage=workflow_stage,
        importance=int(row['importance']),
        source=f'promoted_from:{bid}',
    )
    return {'promoted_from': bid, 'global_item': created}


def _short_summary(text: str, limit: int = 14) -> str:
    clean = str(text or '').strip()
    return clean if len(clean) <= limit else clean[:limit] + '…'


def render_memory_line(item: dict[str, Any]) -> str:
    """Canonical single-line writer representation measured strictly against the 2048-byte budget."""
    return f'- {item["assertion"]}（{item["id"]}）\n'


def query_merged_author_memory(
    library_conn: sqlite3.Connection | None,
    store: Store | None,
    *,
    kinds: list[str] | tuple[str, ...] | None = None,
    genre_ids: list[str] | tuple[str, ...] | None = None,
    workflow_stage: str = '',
    byte_budget: int = DEFAULT_WRITER_BYTE_BUDGET,
) -> dict[str, Any]:
    """Merge global (`AP`) and book (`BP`) preferences under an exact rendered-line UTF-8 byte budget.

    Priority order:
      1. Higher `importance` (5 -> 1)
      2. Book-level preference (`BP`) ahead of global (`AP`) at equal importance
      3. Most recently updated (`updated_at` DESC)

    Any book preference with `overrides_global_id` suppresses that specific global `AP` entry.
    Budget is measured STRICTLY on UTF-8 bytes of rendered writer lines (never JSON envelope).
    Omitted preferences are ALWAYS surfaced via `omitted_ids`, `omitted_summaries`, and `omission_notice`.
    """
    kind_filter = {str(k).strip().lower() for k in (kinds or ()) if str(k).strip()}
    norm_genres = set(canonical_types(list(genre_ids))) if genre_ids else set()
    stage = str(workflow_stage or '').strip()
    budget = max(64, int(byte_budget or DEFAULT_WRITER_BYTE_BUDGET))

    book_items: list[dict[str, Any]] = []
    overridden_global_ids: set[str] = set()
    if store is not None:
        try:
            for item in list_book_preferences(store, status='active'):
                if item.get('overrides_global_id'):
                    overridden_global_ids.add(str(item['overrides_global_id']).upper())
                if kind_filter and item['kind'] not in kind_filter:
                    continue
                book_items.append(item)
        except sqlite3.OperationalError:
            # Tolerate pre-v14 stores gracefully
            book_items = []

    global_items: list[dict[str, Any]] = []
    if library_conn is not None:
        for item in list_global_preferences(library_conn, status='active'):
            if item['id'] in overridden_global_ids:
                continue
            if kind_filter and item['kind'] not in kind_filter:
                continue
            sc = item['scope']
            if sc == 'genre':
                if not norm_genres or not (norm_genres & set(item.get('genre_tags') or ())):
                    continue
            elif sc == 'workflow':
                if not stage or item.get('workflow_stage') != stage:
                    continue
            global_items.append(item)

    merged = [*book_items, *global_items]
    # Deterministic priority: importance DESC, book(0) before global(1), updated_at DESC, id DESC
    merged.sort(key=lambda r: (r['updated_at'], r['id']), reverse=True)
    merged.sort(key=lambda r: (-int(r['importance']), 0 if r['level'] == 'book' else 1))

    selected: list[dict[str, Any]] = []
    lines: list[str] = []
    bytes_used = 0
    omitted_ids: list[str] = []
    omitted_summaries: list[str] = []

    for item in merged:
        line = render_memory_line(item)
        line_bytes = len(line.encode('utf-8'))
        if bytes_used + line_bytes <= budget:
            selected.append(item)
            lines.append(line)
            bytes_used += line_bytes
        else:
            omitted_ids.append(item['id'])
            omitted_summaries.append(f'{item["id"]}：{_short_summary(item["assertion"], 14)}')

    omission_notice = ''
    if omitted_ids:
        preview = '、'.join(omitted_summaries[:6])
        tail = f' 等共 {len(omitted_ids)} 条' if len(omitted_ids) > 6 else ''
        omission_notice = (
            f'另有 {len(omitted_ids)} 条低优先级作者偏好因 {budget} 字节写前预算未注入：'
            f'{preview}{tail}（可在作者跨书记忆面板调整重要度或精简旧条目）。'
        )

    return {
        'items': selected,
        'lines': lines,
        'rendered_text': ''.join(lines),
        'bytes_used': bytes_used,
        'byte_budget': budget,
        'global_count': len(global_items),
        'book_count': len(book_items),
        'overridden_global_ids': sorted(overridden_global_ids),
        'omitted_ids': omitted_ids,
        'omitted_summaries': omitted_summaries,
        'omission_notice': omission_notice,
    }
