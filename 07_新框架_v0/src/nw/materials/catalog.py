"""Versioned, resumable local material indexing outside the project database."""
from bisect import bisect_left
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterator

from nw.materials.fragments import FAMILIES, Fragment, parse_fragments


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    family TEXT NOT NULL,
    layer TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fragments (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    kind TEXT NOT NULL,
    key TEXT,
    byte_start INTEGER NOT NULL,
    byte_end INTEGER NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    UNIQUE (source_id, byte_start)
);
CREATE INDEX IF NOT EXISTS fragment_key ON fragments(key);
"""
_DIGEST = re.compile(r'[0-9a-f]{64}')
_NEWLINES = re.compile(rb'\r\n|\r|\n')
_SOURCE_FIELDS = 'id AS source_id, path, file_sha256, family, layer, byte_size, status'
_FRAGMENT_FIELDS = 'id AS fragment_id, source_id, kind, key, byte_start, byte_end, line_start, line_end, sha256'


def _db_path(workspace: Path) -> Path:
    root = workspace.resolve()
    path = root / 'materials' / 'catalog.db'
    if path.resolve() != path:
        raise ValueError('Material catalog path must stay in the workspace without aliases')
    return path


def _connect(workspace: Path, *, write: bool) -> sqlite3.Connection:
    path = _db_path(workspace)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    mode = 'rwc' if write else 'ro'
    connection = sqlite3.connect(path.as_uri() + f'?mode={mode}', uri=True, timeout=30)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        if write:
            connection.executescript(_SCHEMA)
        else:
            from nw.materials.source_set import apply_source_set
            apply_source_set(connection,workspace)
    except BaseException:
        connection.close()
        raise
    return connection


def _manifest(path: Path, root: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('Unsupported material manifest schema')
    rows = data.get('catalog_inputs')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Material manifest requires catalog_inputs')
    seen = set()
    entries = []
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str)
                                            for k in ('path', 'family', 'layer', 'sha256')):
            raise ValueError('Invalid material input entry')
        relative = Path(row['path'])
        if relative.is_absolute() or relative.drive or relative.root or '..' in relative.parts:
            raise ValueError(f'Material path is outside the source root: {row["path"]}')
        actual = (root / relative).resolve()
        if not actual.is_relative_to(root):
            raise ValueError(f'Material path is outside the source root: {row["path"]}')
        if (row['family'] not in FAMILIES or row['layer'] not in {'baseline', 'derived', 'historical', 'legacy_contract'}
                or not _DIGEST.fullmatch(row['sha256']) or type(row.get('bytes')) is not int or row['bytes'] < 0):
            raise ValueError(f'Invalid material source metadata: {row["path"]}')
        if actual in seen:
            raise ValueError(f'Duplicate material path in manifest: {row["path"]}')
        seen.add(actual)
        entries.append(dict(row, resolved_path=actual, path=relative.as_posix()))
    return entries


def _fragment_rows(source_id: str, data: bytes, fragments: list[Fragment]) -> Iterator[tuple]:
    breaks = [m.end() - 1 for m in _NEWLINES.finditer(data)]
    previous = 0
    for fragment in fragments:
        start, end = fragment.start, fragment.end
        if start != previous or not start <= end <= len(data):
            raise ValueError('Fragments do not partition the source bytes')
        previous = end
        payload = data[start:end]
        start_line = bisect_left(breaks, start) + 1
        end_line = bisect_left(breaks, max(start, end - 1)) + 1
        fragment_id = sha256(f'{source_id}:{start}:{end}'.encode('ascii')).hexdigest()
        yield (fragment_id, source_id, fragment.kind, fragment.key, start, end,
               start_line, end_line, sha256(payload).hexdigest(), payload)
    if previous != len(data):
        raise ValueError('Fragments do not cover the end of the source')


def _status(connection: sqlite3.Connection, source_id: str) -> dict:
    data = dict(connection.execute(f'SELECT {_SOURCE_FIELDS} FROM sources WHERE id=?', (source_id,)).fetchone())
    data['counts'] = dict(connection.execute(
        'SELECT kind, count(*) FROM fragments WHERE source_id=? GROUP BY kind', (source_id,)).fetchall())
    return data


def build_catalog(workspace: Path, root: Path, manifest: Path) -> dict:
    root = root.resolve(strict=True)
    entries = _manifest(manifest, root)
    sources = []
    imported = 0
    with closing(_connect(workspace, write=True)) as connection:
        for row in entries:
            data = row['resolved_path'].read_bytes()
            digest = sha256(data).hexdigest()
            if digest != row['sha256'] or len(data) != row['bytes']:
                raise ValueError(f'Material size or SHA-256 differs from manifest: {row["path"]}')
            identity = json.dumps([row['path'], row['family'], row['layer'], digest], ensure_ascii=False)
            source_id = sha256(identity.encode('utf-8')).hexdigest()
            if connection.execute('SELECT 1 FROM sources WHERE id=?', (source_id,)).fetchone() is None:
                status, fragments = parse_fragments(data, row['family'])
                with connection:
                    created = connection.execute('INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?,?)', (
                        source_id, row['path'], digest, row['family'], row['layer'], len(data), status))
                    if created.rowcount:
                        connection.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)',
                                               _fragment_rows(source_id, data, fragments))
                        imported += 1
            sources.append(_status(connection, source_id))
    return {'imported': imported, 'reused': len(sources) - imported, 'sources': sources}


def list_catalog(workspace: Path, source_id: str | None, key: str | None) -> dict:
    with closing(_connect(workspace, write=False)) as connection:
        if source_id is None and key is None:
            ids = connection.execute('SELECT id FROM sources ORDER BY path, id').fetchall()
            result={'sources': [_status(connection, row['id']) for row in ids]}
            from nw.materials.source_set import selection_status
            selection=selection_status(workspace)
            if selection is not None:result['source_selection']=selection
            return result
        filters, values = [], []
        for column, value in (('source_id', source_id), ('key', key)):
            if value is not None:
                filters.append(f'{column}=?')
                values.append(value)
        where = ' AND '.join(filters)
        rows = connection.execute(f'SELECT {_FRAGMENT_FIELDS} FROM fragments WHERE {where} '
                                  'ORDER BY source_id, byte_start', values)
        return {'fragments': [dict(row) for row in rows]}


def show_fragment(workspace: Path, fragment_id: str) -> dict:
    with closing(_connect(workspace, write=False)) as connection:
        row = connection.execute(f'SELECT {_FRAGMENT_FIELDS}, payload FROM fragments WHERE id=?',
                                 (fragment_id,)).fetchone()
        if row is None:
            from nw.materials.unit_catalog import read_unit

            unit = read_unit(connection, fragment_id)
            if unit is None:
                raise ValueError('Material fragment or unit not found')
            return unit
        result = dict(row)
        payload = result.pop('payload')
        if sha256(payload).hexdigest() != result['sha256']:
            raise ValueError('Material fragment hash mismatch')
        if result['kind'] == 'quarantined':
            raise ValueError('Material fragment is quarantined')
        result['text'] = payload.decode('utf-8')
        return result
