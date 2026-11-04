from contextlib import closing
from pathlib import Path
import sqlite3

from nw.store import Store
from test_migration_v6 import _v5
from test_migration_v5 import snapshot


def test_v6_database_and_backup_preserve_sources_and_decisions(tmp_path: Path) -> None:
    from nw.schema import MIGRATE_V6

    _v5(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'nw.db')) as db:
        db.executescript(MIGRATE_V6)
        db.executescript("""
        INSERT INTO source_versions VALUES ('s','src',printf('%064d',1),1,'utf-8','READY');
        INSERT INTO source_spans VALUES ('span','s',1,1,printf('%064d',2),'原文');
        INSERT INTO cards VALUES ('c',1,'rule','author','{}','[]','stamp');
        INSERT INTO card_decisions VALUES ('d','c',1,'trial','试用','stamp');
        """)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = snapshot(db, tables)
    with Store(tmp_path) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 8
        assert snapshot(store.connection, tables) == before
        assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
    [backup] = tmp_path.glob('nw.v6.*.bak')
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as db:
        assert snapshot(db, tables) == before
