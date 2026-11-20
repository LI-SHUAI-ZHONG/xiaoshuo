"""Independent client metadata; workflow and accepted text remain in each project."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from nw.store import now
from nw.task_models import canonical


class ProductionStore:
    def __init__(self, workspace: Path) -> None:
        self.path = workspace / 'library' / 'library.db'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS novels (
                    id TEXT PRIMARY KEY, project_dir TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
                    status TEXT NOT NULL, wizard_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    finished_at TEXT, updated_at TEXT NOT NULL, job_id TEXT,
                    runtime_status TEXT NOT NULL DEFAULT 'READY', reason TEXT);
                CREATE TABLE IF NOT EXISTS novel_deletions (
                    novel_id TEXT PRIMARY KEY, project_dir TEXT NOT NULL, project_id TEXT, deleted_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS novel_deleted_project ON novel_deletions(project_id);
                CREATE TABLE IF NOT EXISTS wizard_choices (
                    novel_id TEXT NOT NULL, step INTEGER, slot TEXT NOT NULL, option_key TEXT NOT NULL,
                    recommended INTEGER NOT NULL DEFAULT 0, rec_rank INTEGER, rec_level TEXT,
                    PRIMARY KEY(novel_id,slot,option_key));
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, novel_id TEXT NOT NULL,
                    ts TEXT NOT NULL, kind TEXT NOT NULL, ref_json TEXT NOT NULL,
                    summary TEXT NOT NULL, dedup_key TEXT UNIQUE);
                CREATE INDEX IF NOT EXISTS timeline_novel ON timeline_events(novel_id,id);
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(novels)')}
            if 'project_id' not in columns:
                db.execute('ALTER TABLE novels ADD COLUMN project_id TEXT')
            if 'current_branch' not in columns:
                db.execute("ALTER TABLE novels ADD COLUMN current_branch TEXT NOT NULL DEFAULT 'main'")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _novel(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item['wizard'] = json.loads(item.pop('wizard_json'))
        return item

    def get(self, ident: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute('SELECT * FROM novels WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise FileNotFoundError('未找到这本小说')
        return self._novel(row)

    def list(self, status: str = '') -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute('SELECT * FROM novels ORDER BY updated_at DESC').fetchall()
        return [self._novel(row) for row in rows if not status or row['status'] == status]

    def add(self, ident: str, directory: str, title: str, wizard: dict) -> bool:
        timestamp = now()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM novel_deletions WHERE novel_id=? OR project_id=?', (ident, ident)).fetchone():
                return False
            inserted = db.execute('''INSERT INTO novels
                (id,project_dir,title,status,wizard_json,created_at,updated_at)
                VALUES (?,?,?,'designing',?,?,?) ON CONFLICT(project_dir) DO NOTHING''',
                                  (ident, directory, title, canonical(wizard), timestamp, timestamp))
            if inserted.rowcount == 0:
                return False
            if wizard.get('imported'):
                db.execute('UPDATE novels SET project_id=? WHERE id=?', (ident, ident))
            for choice in wizard.get('choices', []):
                db.execute('INSERT OR IGNORE INTO wizard_choices VALUES (?,?,?,?,?,?,?)', (
                    ident, choice.get('step'), choice['slot'], choice['option_key'],
                    int(choice.get('recommended', False)), choice.get('rec_rank'), choice.get('rec_level')))
        return True

    def update(self, ident: str, **fields: Any) -> None:
        if not fields or set(fields) - {'status', 'job_id', 'runtime_status', 'reason', 'finished_at', 'current_branch', 'project_id'}:
            raise ValueError('无效的制作状态更新')
        fields['updated_at'] = now()
        with self.connect() as db:
            db.execute('UPDATE novels SET ' + ','.join(f'{key}=?' for key in fields) + ' WHERE id=?',
                       (*fields.values(), ident))

    def event(self, ident: str, kind: str, summary: str, ref: dict | None = None, *, dedup: str | None = None,
              timestamp: str | None = None) -> None:
        with self.connect() as db:
            db.execute('''INSERT OR IGNORE INTO timeline_events
                (novel_id,ts,kind,ref_json,summary,dedup_key) SELECT ?,?,?,?,?,? WHERE EXISTS
                (SELECT 1 FROM novels WHERE id=?)''',
                       (ident, timestamp or now(), kind, canonical(ref or {}), summary, dedup, ident))

    def timeline(self, ident: str) -> dict[str, Any]:
        self.get(ident)
        with self.connect() as db:
            rows = db.execute('SELECT * FROM timeline_events WHERE novel_id=? ORDER BY ts,id', (ident,)).fetchall()
        return {'events': [{**dict(row), 'ref': json.loads(row['ref_json'])} for row in rows]}
