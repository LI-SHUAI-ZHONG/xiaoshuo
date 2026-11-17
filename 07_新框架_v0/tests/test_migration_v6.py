from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from nw.store import Store
from test_migration_v5 import snapshot, v4_fixture


def _v5(directory: Path) -> tuple[list[str], dict]:
    from nw.schema import MIGRATE_V5

    v4_fixture(directory)
    with closing(sqlite3.connect(directory / 'nw.db')) as db:
        db.executescript(MIGRATE_V5)
        db.executescript("""
        INSERT INTO input_manifests VALUES ('m','{}','{}','hash');
        INSERT INTO budgets(id,limits_json,used_calls) VALUES ('b','{}',1);
        INSERT INTO task_calls(id,project_id,kind,manifest_id,manifest_json,request_json,messages_json,
         budget_id,root_id,attempt,status,raw_json,started_at)
         VALUES ('t','p','plan','m','{}','{}','[]','b','t',1,'FINISHED','{"raw":"保留"}','stamp');
        INSERT INTO call_reservations(id,budget_id,call_kind,call_id,status,estimate_json)
         VALUES ('r','b','task','t','FINISHED','{}');
        """)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return tables, snapshot(db, tables)


def test_v5_database_and_backup_keep_all_old_rows(tmp_path: Path) -> None:
    tables, before = _v5(tmp_path)
    with Store(tmp_path) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 10
        assert snapshot(store.connection, tables) == before
        assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
    [backup] = tmp_path.glob('nw.v5.*.bak')
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 5
        assert snapshot(db, tables) == before


def test_v6_failed_ddl_rolls_back_v6_only(tmp_path: Path) -> None:
    _v5(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        db.execute('CREATE TABLE cards(conflict INTEGER)')
    with pytest.raises(sqlite3.OperationalError, match='cards'):
        Store(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 5
        assert db.execute("SELECT name FROM sqlite_master WHERE name='source_spans'").fetchone() is None
