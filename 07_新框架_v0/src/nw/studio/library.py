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
from nw.studio.method_migration import SCHEMA as METHOD_SCHEMA, migrate_legacy
from nw.studio.method_store import MethodMixin
from nw.studio.corpus_schema import SCHEMA as CORPUS_SCHEMA
from nw.studio.corpus_store import CorpusMixin
from nw.studio.corpus_jobs import CorpusJobsMixin, recover_corpus_jobs


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


class LibraryService(StagingMixin, KnowledgeMixin, RecommendationMixin, MethodMixin, CorpusMixin, CorpusJobsMixin):
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
            conn.executescript(METHOD_SCHEMA)
            conn.executescript(CORPUS_SCHEMA)
        migrate_legacy(self)
        recover_corpus_jobs(self)
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
        from nw.studio.corpus_catalog import DOMAINS, SCHEMA_VERSION

        rows = catalog.genres()
        books = []
        with self.connect() as conn:
            versions = conn.execute("""
                SELECT b.id, b.title, b.words, b.confirmed_types_json, v.version
                FROM corpus_structures h JOIN staging_books b ON b.id=h.book_id
                JOIN corpus_structure_versions v ON v.book_id=h.book_id AND v.version=h.approved_version
                WHERE b.status!='rejected' AND json_extract(v.body_json,'$.schema_version')=?
                ORDER BY b.title,b.id""", (SCHEMA_VERSION,))
            for book in versions:
                structure = self._corpus_row(book['id'], book['version'], conn)
                if structure['available']:
                    books.append({'id': book['id'], 'title': book['title'], 'words': book['words'],
                                  'version': book['version'], 'types': json.loads(book['confirmed_types_json']),
                                  'observed_domains': [d['domain'] for d in structure['body']['domains'] if d['status']=='observed'],
                                  'item_count': len(structure['body']['threads'])})
        for parent in rows:
            for row in [parent, *parent['children']]:
                related = [book for book in books if row['id'] in book['types']]
                row.update(book_count=len(related), item_count=sum(book['item_count'] for book in related),
                           coverage=len({d for book in related for d in book['observed_domains']}), coverage_total=len(DOMAINS))
        return {'genres': rows, 'combinations': catalog.combinations(),
                'approved_books': books, 'analysis_schema': SCHEMA_VERSION, 'analysis_domains': DOMAINS,
                'counts': {'main': len(rows), 'sub': sum(len(r['children']) for r in rows)},
                'slots': list(catalog.SLOTS),
                'notes': ['当前原表有 35 个主类型、33 个子类型分表，共 425 个子类型；层级以原 ID 为准。',
                          '原资料未提供男频、女频、出版频道归属，未推断频道。']}

    def options(self, slot: str, parent: str = '', types: list[str] | None = None) -> dict:
        result = {
            'slot': slot,
            'label': catalog.SLOT_LABELS.get(slot, slot),
            'options': catalog.options(slot, parent, types=types),
            'slots': list(catalog.SLOTS),
        }
        if slot == 'world':
            from nw.studio.world_materials import world_profile_for_types
            result['world_profile'] = world_profile_for_types(types)
        elif slot == 'character':
            from nw.studio.character_materials import character_profile_for_types
            result['character_profile'] = character_profile_for_types(types)
        elif slot in ('structure', 'hook'):
            from nw.studio.plot_materials import plot_profile_for_types
            result['plot_profile'] = plot_profile_for_types(types)
        elif slot in ('narration', 'tone', 'style'):
            from nw.studio.craft_materials import craft_profile_for_types
            result['craft_profile'] = craft_profile_for_types(types)
        return result

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
