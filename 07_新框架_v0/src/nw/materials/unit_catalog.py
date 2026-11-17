"""Create a derived detail index without replacing existing fragment identities."""
from bisect import bisect_left
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import re
import sqlite3
from typing import Iterator

from nw.materials.catalog import _connect, _db_path
from nw.materials.units import units_for_fragment


_SCHEMA = """
CREATE TABLE IF NOT EXISTS material_units (
    id TEXT PRIMARY KEY,
    fragment_id TEXT NOT NULL REFERENCES fragments(id),
    kind TEXT NOT NULL,
    key TEXT,
    label TEXT,
    locator TEXT NOT NULL,
    origin TEXT NOT NULL,
    byte_start INTEGER NOT NULL,
    byte_end INTEGER NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS unit_fragment ON material_units(fragment_id, byte_start);
CREATE INDEX IF NOT EXISTS unit_kind ON material_units(kind);
CREATE INDEX IF NOT EXISTS unit_key ON material_units(key);
CREATE TABLE IF NOT EXISTS unit_checkpoints (
    source_id TEXT PRIMARY KEY REFERENCES sources(id)
);
"""
_FIELDS = """u.id AS unit_id, u.fragment_id, f.source_id, u.kind, u.key, u.label, u.locator,
             u.origin, u.byte_start, u.byte_end, u.line_start, u.line_end, u.sha256"""
_NEWLINES = re.compile(rb'\r\n|\r|\n')
_FRAGMENT_FILTER = """kind IN ('source_block', 'library_block', 'library_entry', 'library_upgrade',
                    'anchor', 'anchor_upgrade', 'network_edge', 'network_upgrade', 'network_residual',
                    'unclassified', 'support_json')"""


def _row_units(row: sqlite3.Row) -> Iterator[tuple]:
    fragment_id, kind, key, base, first_line, digest, data = row
    if sha256(data).hexdigest() != digest:
        raise ValueError(f'Material fragment hash mismatch: {fragment_id}')
    text = data.decode('utf-8')
    units = list(units_for_fragment(text, kind, key))
    positions = sorted({i for unit in units for i in (unit.start, unit.end)})
    offsets = {}
    previous = byte_position = 0
    for position in positions:
        byte_position += len(text[previous:position].encode('utf-8'))
        offsets[position] = byte_position
        previous = position
    breaks = [m.end()-1 for m in _NEWLINES.finditer(data)]
    for unit in units:
        left, right = offsets[unit.start], offsets[unit.end]
        if not 0 <= left < right <= len(data):
            raise ValueError(f'Material unit out of bounds: {fragment_id}')
        stable_id = sha256(f'{fragment_id}:{left}:{right}:{unit.kind}:{unit.locator}'.encode()).hexdigest()
        yield (stable_id, fragment_id, unit.kind, unit.key, unit.label, unit.locator, unit.origin,
               base + left, base + right, first_line + bisect_left(breaks, left),
               first_line + bisect_left(breaks, right - 1), sha256(data[left:right]).hexdigest())


def index_units(workspace: Path, source_id: str | None, *, refresh: bool = False) -> dict:
    if not _db_path(workspace).is_file():
        raise ValueError('Build the material catalog before indexing units')
    indexed = 0
    with closing(_connect(workspace, write=True)) as connection:
        connection.executescript(_SCHEMA)
        if source_id is None:
            sources = [row[0] for row in connection.execute('SELECT id FROM sources ORDER BY path, id')]
        else:
            if connection.execute('SELECT 1 FROM sources WHERE id=?', (source_id,)).fetchone() is None:
                raise ValueError('Material source version not found')
            sources = [source_id]
        for sid in sources:
            with connection:
                created = connection.execute('INSERT OR IGNORE INTO unit_checkpoints VALUES (?)', (sid,))
                if not created.rowcount and not refresh:
                    continue
                fragments = connection.execute(f'''
                    SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments
                    WHERE source_id=? AND {_FRAGMENT_FILTER} ORDER BY byte_start
                ''', (sid,))
                for row in fragments:
                    connection.executemany('''INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(id) DO UPDATE SET key=excluded.key,label=excluded.label
                        WHERE material_units.sha256=excluded.sha256
                          AND (material_units.key IS NOT excluded.key OR material_units.label IS NOT excluded.label)''',
                                           _row_units(row))
                indexed += 1
        where, args = ('', ()) if source_id is None else ('WHERE f.source_id=?', (source_id,))
        counts = dict(connection.execute(f'''
            SELECT u.kind, count(*) FROM material_units u JOIN fragments f ON f.id=u.fragment_id
            {where} GROUP BY u.kind
        ''', args).fetchall())
    return {'indexed': indexed, 'reused': len(sources)-indexed, 'counts': counts}


def refresh_fragment_units(workspace: Path, fragment_id: str) -> dict:
    with closing(_connect(workspace, write=True)) as connection:
        connection.executescript(_SCHEMA)
        row = connection.execute("""SELECT id,kind,key,byte_start,line_start,sha256,payload
                                    FROM fragments WHERE id=?""", (fragment_id,)).fetchone()
        if row is None:
            raise ValueError('Material fragment not found')
        with connection:
            before = connection.total_changes
            connection.executemany('''INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET key=excluded.key,label=excluded.label
                WHERE material_units.sha256=excluded.sha256
                  AND (material_units.key IS NOT excluded.key OR material_units.label IS NOT excluded.label)''',
                                   _row_units(row))
            added = connection.total_changes - before
    return {'fragment_id': fragment_id, 'added_units': added}


def list_units(workspace: Path, *, source_id: str | None, fragment_id: str | None, key: str | None,
               kind: str | None, limit: int, offset: int) -> dict:
    if not 1 <= limit <= 1000 or offset < 0:
        raise ValueError('Unit list limit must be 1–1000 and offset must be nonnegative')
    conditions, values = [], []
    for field, value in (('f.source_id', source_id), ('u.fragment_id', fragment_id),
                         ('u.key', key), ('u.kind', kind)):
        if value is not None:
            conditions.append(f'{field}=?')
            values.append(value)
    where = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
    with closing(_connect(workspace, write=False)) as connection:
        if not _has_units(connection):
            raise ValueError('Run materials index-units to build the detail index')
        rows = connection.execute(f'''
            SELECT {_FIELDS} FROM material_units u JOIN fragments f ON f.id=u.fragment_id {where}
            ORDER BY f.source_id, u.byte_start, u.byte_end, u.kind, u.id LIMIT ? OFFSET ?
        ''', (*values, limit+1, offset)).fetchall()
    return {'units': [dict(row) for row in rows[:limit]],
            'next_offset': offset + limit if len(rows) > limit else None}


def _has_units(connection: sqlite3.Connection) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE name='material_units'").fetchone() is not None


def read_unit(connection: sqlite3.Connection, unit_id: str) -> dict | None:
    if not _has_units(connection):
        return None
    row = connection.execute(f'''
        SELECT {_FIELDS}, substr(f.payload, u.byte_start-f.byte_start+1,
                                u.byte_end-u.byte_start) AS payload
        FROM material_units u JOIN fragments f ON f.id=u.fragment_id WHERE u.id=?
    ''', (unit_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    payload = result.pop('payload')
    if sha256(payload).hexdigest() != result['sha256']:
        raise ValueError('Material unit hash mismatch')
    result['text'] = payload.decode('utf-8')
    return result
