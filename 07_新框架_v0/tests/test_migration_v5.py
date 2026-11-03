"""A v4 fixture built from the historical DDL, never from a live project."""
from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from nw.schema import MIGRATE_V2, MIGRATE_V3, MIGRATE_V4, SCHEMA
from nw.store import Store


FIXTURE = """
INSERT INTO projects VALUES ('p','潮痕','stamp');
INSERT INTO briefs VALUES ('p','作品目标','限制',1);
INSERT INTO bible_entries VALUES ('p','character','沈砚','设定',1);
INSERT INTO chapters VALUES ('c','p',1,'第一章');
INSERT INTO scenes VALUES ('s','c',1,'{"pov":"沈砚"}');
INSERT INTO runs VALUES ('r1','s','write','ollama','m','{}','{"messages":[]}','{}','初稿','complete','{}','start','end');
INSERT INTO runs VALUES ('r2','s','revise','ollama','m','{}','{}','{}','二稿','complete','{}','start','end');
INSERT INTO runs VALUES ('r3','s','revise','ollama','m','{}','{}','{}','三稿','complete','{}','start','end');
INSERT INTO runs VALUES ('r4','s','review','ollama','m','{}','{}','{}','','error','{}','start','');
INSERT INTO run_outputs VALUES ('r1','rid','{"original":"初稿"}');
INSERT INTO drafts VALUES ('d1','s',1,'初稿','complete','r1','stamp');
INSERT INTO drafts VALUES ('d2','s',2,'二稿','complete','r2','stamp');
INSERT INTO drafts VALUES ('d3','s',3,'三稿','complete','r3','stamp');
INSERT INTO accepted VALUES ('s','d2','stamp');
INSERT INTO state_notes VALUES ('s','fact','待兑现');
INSERT INTO flow_meta VALUES ('s','{"model":"m"}','[]');
INSERT INTO flow_nodes VALUES ('s','N5','IN_PROGRESS','{}','{"round":1}');
INSERT INTO ab_experiments VALUES ('ab','s','{"1":{"run_id":"r1"},"2":{"run_id":"r3"}}','seal','READY',1,1,'stamp');
"""


def snapshot(db: sqlite3.Connection, tables: list[str]) -> dict:
    return {table: [tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in tables}


def v4_fixture(directory: Path) -> tuple[list[str], dict]:
    with closing(sqlite3.connect(directory / 'nw.db')) as db:
        db.executescript(SCHEMA + MIGRATE_V2 + MIGRATE_V3 + MIGRATE_V4 + FIXTURE)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return tables, snapshot(db, tables)


def test_v4_full_fixture_migrates_without_loss(tmp_path: Path) -> None:
    tables, before = v4_fixture(tmp_path)
    with Store(tmp_path) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 5
        assert snapshot(store.connection, tables) == before
        assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
        assert store.run_output('r1') == {'request_id': 'rid', 'raw': {'original': '初稿'}}
        assert store.accepted('s').draft_id == 'd2'
    backups = list(tmp_path.glob('nw.v4.*.bak'))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0].as_uri() + '?mode=ro', uri=True)) as backup:
        assert backup.execute('PRAGMA user_version').fetchone()[0] == 4
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert snapshot(backup, tables) == before
    with Store(tmp_path):
        assert list(tmp_path.glob('nw.v4.*.bak')) == backups


def test_failed_ddl_leaves_old_schema_and_readable_backup(tmp_path: Path) -> None:
    v4_fixture(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        db.execute('CREATE TABLE task_calls(collides INTEGER)')
    with pytest.raises(sqlite3.OperationalError, match='task_calls'):
        Store(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        assert db.execute("SELECT name FROM sqlite_master WHERE name='input_manifests'").fetchone() is None
        assert db.execute('SELECT draft_id FROM accepted').fetchone()[0] == 'd2'
    assert len(list(tmp_path.glob('nw.v4.*.bak'))) == 1
