
from contextlib import closing
import sqlite3

import pytest

from nw import migrations
from nw.store import Store
from test_migration_v5 import snapshot
from test_novel_flow import setup_story


def test_v7_job_upgrade_preserves_story_and_rolls_back_failed_ddl(tmp_path, monkeypatch):
    monkeypatch.setattr(migrations, 'VERSION', 7)
    with Store(tmp_path, create=True) as store:
        setup_story(store, 1)
        tables = [row[0] for row in store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = snapshot(store.connection, tables)
    monkeypatch.setattr(migrations, 'VERSION', 8)
    script = migrations.MIGRATIONS[7]
    monkeypatch.setitem(migrations.MIGRATIONS, 7, script.replace('PRAGMA user_version=8;',
        'INSERT INTO absent_table VALUES (1);\nPRAGMA user_version=8;'))
    with pytest.raises(sqlite3.OperationalError, match='absent_table'):
        Store(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 7
        assert snapshot(db, tables) == before
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='novel_jobs'").fetchone()
    monkeypatch.setitem(migrations.MIGRATIONS, 7, script)
    with Store(tmp_path) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 8
        assert snapshot(store.connection, tables) == before
        assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            store.connection.execute("UPDATE story_decisions SET reason='changed'")
    for backup in tmp_path.glob('nw.v7.*.bak'):
        with closing(sqlite3.connect(backup)) as db:
            assert snapshot(db, tables) == before
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
