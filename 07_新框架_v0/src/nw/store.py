"""SQLite is authoritative; accepted Markdown exports are recoverable projections."""

from dataclasses import astuple
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from types import TracebackType
from typing import Any, Callable
from uuid import uuid4

from nw import models as m
from nw.migrations import upgrade
from nw.project_paths import FORMAL_BOOKS_ROOT, FORMAL_WORKSPACE, contained_file, project_directory, projects_root_for
from nw.llm.base import GenResult

RECORDS = {
    'project': ('projects', m.Project), 'brief': ('briefs', m.Brief),
    'bible': ('bible_entries', m.BibleEntry), 'chapter': ('chapters', m.Chapter),
    'scene': ('scenes', m.Scene), 'draft': ('drafts', m.Draft),
    'run': ('runs', m.Run), 'accepted': ('accepted', m.Accepted),
    'note': ('state_notes', m.StateNote),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory: Path, *, create: bool = False, test_mode: bool = False,
                 projects_root: Path | None = None) -> None:
        # The logical workspace is also the immutable source of materials and methods.
        self.directory = Path(directory)
        root = projects_root_for(self.directory.parent, projects_root)
        self.data_directory = (self.directory.resolve() if projects_root is None and root == self.directory.parent.resolve()
                               else project_directory(root, self.directory.name))
        self.test_mode = test_mode
        if test_mode and (self.directory.resolve().is_relative_to(FORMAL_WORKSPACE.resolve())
                          or self.data_directory.is_relative_to(FORMAL_BOOKS_ROOT.resolve())
                          or 'projects' in [p.lower() for p in self.data_directory.parts]):
            raise ValueError('test store cannot use production workspace or projects directories')
        db = self.data_file('nw.db')
        name = self.directory.name
        if create and not db.is_file() and (name.startswith(('_', '.')) or name.casefold() in ('library', 'materials')):
            raise ValueError('作品目录名不能以 _ 或 . 开头，也不能使用系统保留的 library、materials')
        if not create and not db.is_file():
            raise FileNotFoundError(f'Project database does not exist: {db}')
        if create:
            self.data_directory.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(db)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA recursive_triggers=ON')
        try:
            upgrade(self.connection, db)
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                for accepted in self.list('accepted'):
                    self._export(self.get('draft', accepted.draft_id))
        except BaseException:
            self.connection.close()
            raise

    def data_file(self, *parts: str) -> Path:
        return contained_file(self.data_directory, *parts)

    def __enter__(self) -> 'Store':
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc: BaseException | None, traceback: TracebackType | None) -> None:
        self.connection.close()

    def _insert(self, kind: str, record: Any) -> Any:
        table = RECORDS[kind][0]
        values = astuple(record)
        self.connection.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in values)})', values)
        return record

    def list(self, kind: str) -> list[Any]:
        table, record = RECORDS[kind]
        return [record(*row) for row in self.connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]

    def get(self, kind: str, record_id: str) -> Any:
        if kind not in ('project', 'chapter', 'scene', 'draft', 'run'):
            raise ValueError(f'{kind} does not have an id')
        table, record = RECORDS[kind]
        row = self.connection.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
        if row is None:
            raise ValueError(f'{kind} not found: {record_id}')
        return record(*row)

    def project(self) -> m.Project:
        projects = self.list('project')
        if len(projects) != 1:
            raise ValueError('Project is not initialized')
        return projects[0]

    def init_project(self, name: str) -> m.Project:
        if not name.strip():
            raise ValueError('Project name is required')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            if self.list('project'):
                raise ValueError('Project already exists')
            return self._insert('project', m.Project(uuid4().hex, name, now()))

    def add_brief(self, text: str, constraints: str = '') -> m.Brief:
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            prior = self.briefs()
            project_id = self.project().id
            if self.managed_story() and prior:
                from nw.story_dependencies import invalidate_input, legacy_ref
                invalidate_input(self, legacy_ref('brief', project_id, prior[-1]))
            return self._insert('brief', m.Brief(project_id, text, constraints, len(prior) + 1))

    def briefs(self) -> list[m.Brief]:
        return self.list('brief')

    def add_bible(self, kind: str, name: str, body: str) -> m.BibleEntry:
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            versions = [b for b in self.bible() if b.kind == kind and b.name == name]
            previous = max(versions, key=lambda b: b.version, default=None)
            if self.managed_story() and previous is not None:
                from nw.story_dependencies import invalidate_input, legacy_ref
                invalidate_input(self, legacy_ref('bible', json.dumps([kind, name], ensure_ascii=False), previous))
            version = 1 if previous is None else previous.version + 1
            return self._insert('bible', m.BibleEntry(self.project().id, kind, name, body, version))

    def bible(self) -> list[m.BibleEntry]:
        return self.list('bible')

    def add_chapter(self, index: int, title: str) -> m.Chapter:
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            self._invalidate_outline()
            return self._insert('chapter', m.Chapter(uuid4().hex, self.project().id, index, title))

    def add_scene(self, chapter_id: str, index: int, card_json: str) -> m.Scene:
        if not isinstance(json.loads(card_json), dict):
            raise ValueError('Scene card must be a JSON object')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            self._invalidate_outline()
            return self._insert('scene', m.Scene(uuid4().hex, chapter_id, index, card_json))

    def _invalidate_outline(self) -> None:
        if self.managed_story():
            from nw.story_dependencies import invalidate_input, outline_ref
            invalidate_input(self, outline_ref(self))

    def add_run(self, run: m.Run) -> m.Run:
        with self.connection:
            return self._insert('run', run)

    def finish_run(self, run_id: str, result: GenResult, *,
                   settle: Callable[[], None] | None = None) -> tuple[m.Run, m.Draft | None]:
        if result.finish_reason not in ('complete', 'truncated', 'error', 'refused'):
            raise ValueError('Invalid generation finish reason')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            run = self.get('run', run_id)
            if run.ended_at:
                raise ValueError('Run already finalized')
            self.connection.execute(
                'UPDATE runs SET output_text=?, finish_reason=?, usage_json=?, ended_at=? WHERE id=?',
                (result.text, result.finish_reason, json.dumps(result.usage, ensure_ascii=False), now(), run_id))
            self.connection.execute('INSERT INTO run_outputs VALUES (?,?,?)',
                                    (run_id, result.request_id, json.dumps(result.raw, ensure_ascii=False)))
            draft = None
            if run.kind in ('write', 'revise') and result.finish_reason in ('complete', 'truncated') and result.text:
                version = self.connection.execute('SELECT COALESCE(MAX(version),0)+1 FROM drafts WHERE scene_id=?', (run.scene_id,)).fetchone()[0]
                draft = self._insert('draft', m.Draft(uuid4().hex, run.scene_id, version, result.text,
                                                    result.finish_reason, run_id, now()))
            if settle is not None:
                settle()
            return self.get('run', run_id), draft

    def run_output(self, run_id: str) -> dict:
        self.get('run', run_id)
        row = self.connection.execute('SELECT request_id,raw_json FROM run_outputs WHERE run_id=?', (run_id,)).fetchone()
        return {'request_id': row[0], 'raw': json.loads(row[1])} if row else {}

    def add_draft(self, scene_id: str, text: str, status: str, run_id: str) -> m.Draft:
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            version = self.connection.execute(
                'SELECT COALESCE(MAX(version),0)+1 FROM drafts WHERE scene_id=?', (scene_id,)
            ).fetchone()[0]
            return self._insert('draft', m.Draft(uuid4().hex, scene_id, version, text, status, run_id, now()))

    def drafts(self, scene_id: str) -> list[m.Draft]:
        return [m.Draft(*row) for row in self.connection.execute(
            'SELECT * FROM drafts WHERE scene_id=? ORDER BY version', (scene_id,))]

    def accepted(self, scene_id: str) -> m.Accepted | None:
        row = self.connection.execute('SELECT * FROM accepted WHERE scene_id=?', (scene_id,)).fetchone()
        return m.Accepted(*row) if row else None

    def _export_path(self, draft: m.Draft) -> Path:
        scene = self.get('scene', draft.scene_id)
        chapter = self.get('chapter', scene.chapter_id)
        return self.data_file('正文', f'ch{chapter.index:02d}_s{scene.index:02d}.md')

    def _export(self, draft: m.Draft) -> None:
        if self.get('run', draft.run_id).provider == 'fake' and not self.test_mode:
            raise ValueError('fake output may be exported only in isolated test stores')
        path = self._export_path(draft)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding='utf-8') != draft.text:
            path.write_text(draft.text, encoding='utf-8', newline='')

    def managed_story(self) -> bool:
        return self.connection.execute("SELECT 1 FROM story_branches WHERE id='main' AND enabled=1").fetchone() is not None

    def check_legacy_flow(self, scene_id: str) -> None:
        if self.managed_story():
            raise ValueError('MANAGED_STORY: use story commands for this project')
        if self.connection.execute("""
            SELECT 1 FROM story_decisions WHERE action='abandon' AND json_extract(targets_json,'$.scene_id')=?
        """, (scene_id,)).fetchone():
            raise ValueError('Legacy flow was explicitly abandoned')

    def _check_acceptable(self, draft_id: str) -> m.Draft:
        draft = self.get('draft', draft_id)
        run = self.get('run', draft.run_id)
        if run.provider == 'fake' and not self.test_mode:
            raise ValueError('fake output may be accepted only in isolated test stores')
        if draft.status != 'complete' or run.finish_reason != 'complete':
            raise ValueError('Acceptance requires complete draft and run')
        return draft

    def _accept_in_transaction(self, draft_id: str) -> m.Accepted:
        draft = self._check_acceptable(draft_id)
        accepted = m.Accepted(draft.scene_id, draft.id, now())
        self.connection.execute(
            'INSERT INTO accepted VALUES (?,?,?) ON CONFLICT(scene_id) DO UPDATE '
            'SET draft_id=excluded.draft_id, accepted_at=excluded.accepted_at', astuple(accepted))
        return accepted

    def _export_accepted(self, scene_ids: list[str]) -> None:
        if not scene_ids:
            return
        try:
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                for scene_id in scene_ids:
                    # Another process may have accepted a newer version meanwhile.
                    current = self.accepted(scene_id)
                    self._export(self.get('draft', current.draft_id))
        except (OSError, sqlite3.Error) as exc:
            raise OSError('Acceptance recorded and committed in SQLite; export failed. Reopen project to retry.') from exc

    def accept(self, draft_id: str, *, legacy_flow_scene: str | None = None) -> m.Accepted:
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            if legacy_flow_scene is not None:
                self.check_legacy_flow(legacy_flow_scene)
            if self.managed_story():
                raise ValueError('DELTA_REQUIRED: accept reviewed prose with accept --batch')
            # The traditional command treats a blocked destination directory as a preflight failure.
            self._export_path(self._check_acceptable(draft_id)).parent.mkdir(parents=True, exist_ok=True)
            accepted = self._accept_in_transaction(draft_id)
        self._export_accepted([accepted.scene_id])
        return accepted

    def add_note(self, scene_id: str, kind: str, text: str) -> m.StateNote:
        with self.connection:
            if self.accepted(scene_id) is None:
                raise ValueError('State notes require an accepted scene')
            return self._insert('note', m.StateNote(scene_id, kind, text))

    def notes(self, scene_id: str) -> list[m.StateNote]:
        return [n for n in self.list('note') if n.scene_id == scene_id]
