"""Independent, stdlib-only library database for Studio v3."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
from typing import Iterator

from nw.studio import catalog
from nw.studio.kb import KnowledgeMixin
from nw.studio.recommend import RecommendationMixin
from nw.studio.staging import StagingMixin
from nw.studio.library_util import encode, timestamp


SCHEMA = '''
CREATE TABLE IF NOT EXISTS staging_books (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, file_path TEXT NOT NULL,
 sha256 TEXT NOT NULL UNIQUE, words INTEGER NOT NULL, filename TEXT NOT NULL,
 detected_types_json TEXT NOT NULL, confirmed_types_json TEXT NOT NULL DEFAULT '[]',
 grade TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
 error TEXT NOT NULL DEFAULT '', chapters_json TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS decomp_items (
 id TEXT PRIMARY KEY, book_id TEXT NOT NULL REFERENCES staging_books(id),
 slot TEXT NOT NULL, option_key TEXT NOT NULL, type_tags_json TEXT NOT NULL,
 stages_json TEXT NOT NULL, usage_text TEXT NOT NULL, evidence_json TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 origin TEXT NOT NULL DEFAULT 'manual');
CREATE INDEX IF NOT EXISTS decomp_slot_status ON decomp_items(slot,status);
CREATE TABLE IF NOT EXISTS type_kb (
 type_id TEXT PRIMARY KEY, definition TEXT NOT NULL DEFAULT '',
 includes TEXT NOT NULL DEFAULT '[]', excludes TEXT NOT NULL DEFAULT '[]',
 features_json TEXT NOT NULL DEFAULT '[]', examples_json TEXT NOT NULL DEFAULT '[]',
 counterexamples_json TEXT NOT NULL DEFAULT '[]', version INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS upgrade_candidates (
 id TEXT PRIMARY KEY, decomp_item_id TEXT NOT NULL UNIQUE REFERENCES decomp_items(id),
 target_source_key TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
 reason TEXT NOT NULL, created_at TEXT NOT NULL, decided_at TEXT);
CREATE TABLE IF NOT EXISTS upgrade_versions (
 version INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL UNIQUE,
 snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviewed_adoptions (
 novel_id TEXT NOT NULL, scene_id TEXT NOT NULL, option_key TEXT NOT NULL,
 reviewed_ref TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(novel_id,scene_id,option_key));
CREATE TABLE IF NOT EXISTS usage_stats (
 option_key TEXT NOT NULL, slot TEXT NOT NULL, type_key TEXT NOT NULL,
 corpus_count INTEGER NOT NULL, adopt_count INTEGER NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(option_key,slot,type_key));
'''


class LibraryService(StagingMixin, KnowledgeMixin, RecommendationMixin):
    def __init__(self, workspace_root: Path, *, config_path: Path | None = None,
                 ledger_path: Path | None = None) -> None:
        self.workspace = Path(workspace_root).resolve()
        self.root = self.workspace / 'library'
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / 'library.db'
        self.config_path = config_path
        self.ledger_path = ledger_path
        self._tasks: dict[str, threading.Thread] = {}
        self._task_lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(staging_books)')}
            if 'decomposition_requested' not in columns:
                conn.execute('ALTER TABLE staging_books ADD COLUMN decomposition_requested INTEGER NOT NULL DEFAULT 1')
        from nw.studio.staging_model import recover_decompositions
        recover_decompositions(self)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def genres(self) -> dict:
        rows = catalog.genres()
        with self.connect() as conn:
            approved = conn.execute("SELECT d.type_tags_json,d.slot,d.book_id FROM decomp_items d "
                                    "JOIN staging_books b ON b.id=d.book_id "
                                    "WHERE d.status='approved' AND b.status='archived'").fetchall()
        for parent in rows:
            for row in [parent, *parent['children']]:
                related = [r for r in approved if row['id'] in json.loads(r['type_tags_json'])]
                row.update(book_count=len({r['book_id'] for r in related}), item_count=len(related),
                           coverage=len({r['slot'] for r in related}), coverage_total=len(catalog.SLOTS))
        return {'genres': rows, 'combinations': catalog.combinations(),
                'counts': {'main': len(rows), 'sub': sum(len(r['children']) for r in rows)},
                'slots': list(catalog.SLOTS),
                'notes': ['当前原表有 35 个主类型、33 个子类型分表，共 425 个子类型；层级以原 ID 为准。',
                          '原资料未提供男频、女频、出版频道归属，未推断频道。']}

    def options(self, slot: str, parent: str = '') -> dict:
        return {'slot': slot, 'label': catalog.SLOT_LABELS.get(slot, slot),
                'options': catalog.options(slot, parent), 'slots': list(catalog.SLOTS)}

    def _item(self, row: sqlite3.Row | dict) -> dict:
        result = dict(row)
        for stored, public in [('type_tags_json', 'type_tags'), ('stages_json', 'stages'), ('evidence_json', 'evidence')]:
            result[public] = json.loads(result.pop(stored))
        option = catalog.option_map(result['slot']).get(result['option_key'], {})
        result['name'] = option.get('name', result['option_key'])
        return result

    def _book(self, row: sqlite3.Row | dict) -> dict:
        result = dict(row)
        result['decomposition_requested'] = bool(result.get('decomposition_requested', True))
        for stored, public in [('detected_types_json', 'detected_types'), ('confirmed_types_json', 'confirmed_types'),
                               ('chapters_json', 'chapters')]:
            result[public] = json.loads(result.pop(stored))
        result.pop('file_path', None)
        return result
