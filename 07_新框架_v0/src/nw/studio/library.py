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
from nw.craft_specs_base import (
    CRAFT_FINGERPRINT_SCHEMA,
    get_craft_fingerprints_by_ids as _get_craft_fingerprints_by_ids,
    list_craft_fingerprints as _list_craft_fingerprints,
)
from nw.voice_specs import (
    VOICE_FINGERPRINT_SCHEMA,
    get_voice_fingerprints_by_ids,
    list_voice_fingerprints as _list_voice_fingerprints,
)
from nw.author_memory import (
    GLOBAL_AUTHOR_MEMORY_SCHEMA,
    forget_preference as _forget_preference,
    list_global_preferences as _list_global_preferences,
    remember_global_preference as _remember_global_preference,
    replace_preference as _replace_preference,
)
from nw.verified_excerpts import (
    VERIFIED_EXCERPT_SCHEMA,
    build_writer_verified_excerpts_packet as _build_writer_verified_excerpts_packet,
    extract_and_verify_corpus_excerpt as _extract_and_verify_corpus_excerpt,
    list_verified_excerpts as _list_verified_excerpts,
    save_verified_excerpt as _save_verified_excerpt,
)
from nw.studio.chart_radar import (
    CHART_RADAR_SCHEMA,
    PLATFORMS as RADAR_PLATFORMS,
    aggregate_chart_snapshots as _aggregate_chart_snapshots,
    diff_chart_snapshots as _diff_chart_snapshots,
    fetch_live_chart as _fetch_live_chart,
    generate_topic_decisions as _generate_topic_decisions,
    get_chart_snapshot as _get_chart_snapshot,
    list_chart_snapshots as _list_chart_snapshots,
    list_topic_decisions as _list_topic_decisions,
    parse_chart_import as _parse_chart_import,
    save_chart_snapshot as _save_chart_snapshot,
)
from nw.studio.book_deconstructor import (
    BOOK_DECONSTRUCT_SCHEMA,
    get_book_deconstruct_artifact as _get_book_deconstruct_artifact,
    run_book_deconstruct_pack as _run_book_deconstruct_pack,
)


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
            conn.executescript(VOICE_FINGERPRINT_SCHEMA)
            conn.executescript(CRAFT_FINGERPRINT_SCHEMA)
            conn.executescript(GLOBAL_AUTHOR_MEMORY_SCHEMA)
            conn.executescript(VERIFIED_EXCERPT_SCHEMA)
            conn.executescript(CHART_RADAR_SCHEMA)
            conn.executescript(BOOK_DECONSTRUCT_SCHEMA)
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

    def voice_fingerprints(
        self,
        *,
        types: list[str] | tuple[str, ...] | None = None,
        status: str = 'approved',
        include_incompatible: bool = False,
    ) -> list[dict]:
        with self.connect() as conn:
            return _list_voice_fingerprints(
                conn, types=types, status=status, include_incompatible=include_incompatible,
            )

    def voice_fingerprints_by_ids(self, ids: list[str] | tuple[str, ...]) -> list[dict]:
        with self.connect() as conn:
            return get_voice_fingerprints_by_ids(conn, ids)

    def craft_fingerprints(
        self,
        *,
        domain: str | None = None,
        types: list[str] | tuple[str, ...] | None = None,
        status: str = 'approved',
        include_incompatible: bool = False,
    ) -> list[dict]:
        from nw.craft_specs import all_base_name_map
        with self.connect() as conn:
            return _list_craft_fingerprints(
                conn,
                domain=domain,
                types=types,
                status=status,
                include_incompatible=include_incompatible,
                base_names=all_base_name_map(),
            )

    def craft_fingerprints_by_ids(
        self,
        ids: list[str] | tuple[str, ...],
        *,
        domain: str | None = None,
    ) -> list[dict]:
        from nw.craft_specs import all_base_name_map
        with self.connect() as conn:
            return _get_craft_fingerprints_by_ids(conn, ids, domain=domain, base_names=all_base_name_map())

    def list_global_author_memory(self, *, status: str | None = 'active', scope: str | None = None) -> list[dict]:
        with self.connect() as conn:
            return _list_global_preferences(conn, status=status, scope=scope)

    def remember_global_author_memory(self, body: dict) -> dict:
        with self.connect() as conn:
            return _remember_global_preference(
                conn,
                assertion=str(body.get('assertion') or ''),
                kind=str(body.get('kind') or 'prose'),
                scope=str(body.get('scope') or 'global'),
                genre_tags=body.get('genre_tags') if isinstance(body.get('genre_tags'), list) else None,
                workflow_stage=str(body.get('workflow_stage') or ''),
                importance=int(body.get('importance') or 3),
                source=str(body.get('source') or 'author_explicit'),
            )

    def replace_global_author_memory(self, pref_id: str, body: dict) -> dict:
        with self.connect() as conn:
            return _replace_preference(
                pref_id,
                new_assertion=str(body.get('assertion') or body.get('new_assertion') or ''),
                importance=(int(body['importance']) if body.get('importance') is not None else None),
                kind=(str(body['kind']) if body.get('kind') else None),
                library_conn=conn,
            )

    def forget_global_author_memory(self, pref_id: str) -> dict:
        with self.connect() as conn:
            return _forget_preference(pref_id, library_conn=conn)

    def list_verified_excerpts(
        self,
        *,
        types: list[str] | tuple[str, ...] | None = None,
        scene_function: str = '',
        limit: int = 20,
    ) -> list[dict]:
        with self.connect() as conn:
            return _list_verified_excerpts(conn, type_tags=types, scene_function=scene_function, limit=limit)

    def add_verified_excerpt(self, body: dict) -> dict:
        raw_text = str(body.get('raw_chapter_text') or body.get('text') or '')
        start = int(body.get('start', 0))
        end = int(body.get('end', len(raw_text)))
        extracted = _extract_and_verify_corpus_excerpt(
            raw_text, start, end,
            book_id=str(body.get('book_id') or ''),
            chapter_index=int(body.get('chapter_index') or 0),
            type_tags=body.get('type_tags') if isinstance(body.get('type_tags'), list) else None,
            scene_function=str(body.get('scene_function') or 'confrontation'),
            learn_what=str(body.get('learn_what') or ''),
            do_not_copy=str(body.get('do_not_copy') or ''),
            known_names=body.get('known_names'),
        )
        with self.connect() as conn:
            saved = _save_verified_excerpt(conn, extracted)
        return {'excerpt': saved, 'verification': extracted['verification']}

    def verified_excerpts_packet(
        self,
        *,
        types: list[str] | tuple[str, ...] | None = None,
        scene_function: str = 'confrontation',
        limit: int = 2,
    ) -> dict | None:
        with self.connect() as conn:
            return _build_writer_verified_excerpts_packet(conn, type_tags=types, scene_function=scene_function, limit=limit)

    # ---------- Chart Radar & Market Intelligence ----------

    def radar_overview(self, *, platform: str = '') -> dict:
        from nw.platform_playbooks import list_platform_playbooks, recommend_monetization_platforms
        with self.connect() as conn:
            snapshots = _list_chart_snapshots(conn, platform=platform, limit=40)
            aggregation = _aggregate_chart_snapshots(conn, platform=platform) if snapshots else {'snapshot_count': 0, 'skipped_duplicates': [], 'platforms': []}
            topics = _list_topic_decisions(conn, limit=30)
        return {
            'platforms': list(RADAR_PLATFORMS.values()),
            'playbooks': list_platform_playbooks(),
            'beginner_recommendations': recommend_monetization_platforms(scale='long', experience='beginner'),
            'snapshots': snapshots,
            'aggregation': aggregation,
            'topics': topics,
        }

    def radar_playbooks(self, *, scale: str = 'long', experience: str = 'beginner', types: list[str] | None = None) -> dict:
        from nw.platform_playbooks import PLAYBOOK_UPDATED_PERIOD, list_platform_playbooks, recommend_monetization_platforms
        return {
            'updated_period': PLAYBOOK_UPDATED_PERIOD,
            'playbooks': list_platform_playbooks(),
            'recommendations': recommend_monetization_platforms(
                scale=scale or 'long',
                experience=experience or 'beginner',
                genre_ids=types,
            ),
        }

    def radar_snapshot_detail(self, snapshot_id: str) -> dict:
        with self.connect() as conn:
            return _get_chart_snapshot(conn, snapshot_id)

    def radar_fetch_live(self, body: dict) -> dict:
        platform = str(body.get('platform') or 'qidian').strip()
        rank_type = str(body.get('rank_type') or '').strip()
        pages = int(body.get('pages') or 2)
        fetched = _fetch_live_chart(platform, rank_type, pages=pages)
        if not fetched.get('ok'):
            return {'fetched': fetched, 'saved': None}
        with self.connect() as conn:
            saved = _save_chart_snapshot(conn, fetched)
        return {'fetched': {'ok': True, 'entry_count': len(fetched['entries'])}, 'saved': saved}

    def radar_import_chart(self, body: dict) -> dict:
        parsed = _parse_chart_import(
            str(body.get('text') or ''),
            platform=str(body.get('platform') or ''),
            list_name=str(body.get('list_name') or ''),
            fmt=str(body.get('format') or 'auto'),
        )
        with self.connect() as conn:
            saved = _save_chart_snapshot(conn, parsed, captured_date=str(body.get('captured_date') or ''))
        return {'saved': saved}

    def radar_diff_snapshots(self, body: dict) -> dict:
        cur_ids = [str(x) for x in (body.get('current_snapshot_ids') or ()) if str(x).strip()]
        base_ids = [str(x) for x in (body.get('baseline_snapshot_ids') or ()) if str(x).strip()]
        if not cur_ids or not base_ids:
            raise ValueError('趋势对比必须同时指定当前快照与基线快照')
        with self.connect() as conn:
            return _diff_chart_snapshots(conn, current_snapshot_ids=cur_ids, baseline_snapshot_ids=base_ids)

    def radar_generate_topics(self, body: dict, *, provider: object | None = None, model: str = '', params: dict | None = None) -> dict:
        snap_ids = [str(x) for x in (body.get('snapshot_ids') or ()) if str(x).strip()] or None
        with self.connect() as conn:
            return _generate_topic_decisions(
                conn,
                snapshot_ids=snap_ids,
                platform=str(body.get('platform') or ''),
                author_focus=str(body.get('author_focus') or ''),
                provider=provider if bool(body.get('use_llm')) else None,
                model=model,
                params=params,
                max_topics=int(body.get('max_topics') or 3),
            )

    # ---------- Enhanced Book Deconstruction Pack ----------

    def get_book_anatomy(self, book_id: str) -> dict:
        row = self._staging_row(book_id)
        with self.connect() as conn:
            art = _get_book_deconstruct_artifact(conn, book_id)
            if art is None:
                text = self._book_text(row)
                art = _run_book_deconstruct_pack(
                    conn,
                    book_id=book_id,
                    book_title=row['title'],
                    raw_text=text,
                    chapters=json.loads(row['chapters_json'] or '[]'),
                    confirmed_types=json.loads(row['confirmed_types_json'] or '[]'),
                    harvest_excerpts=False,
                    backfill_topics=False,
                )
        return art

    def run_book_anatomy(self, book_id: str, body: dict, *, provider: object | None = None, model: str = '', params: dict | None = None) -> dict:
        row = self._staging_row(book_id)
        text = self._book_text(row)
        use_llm = bool(body.get('use_llm', False))
        harvest = bool(body.get('harvest_excerpts', True))
        with self.connect() as conn:
            return _run_book_deconstruct_pack(
                conn,
                book_id=book_id,
                book_title=row['title'],
                raw_text=text,
                chapters=json.loads(row['chapters_json'] or '[]'),
                confirmed_types=json.loads(row['confirmed_types_json'] or '[]'),
                harvest_excerpts=harvest,
                provider=(provider if use_llm else None),
                model=model,
                params=params,
            )
