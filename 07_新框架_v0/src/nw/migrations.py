"""Serialize schema upgrades and keep a readable SQLite snapshot per old version."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from nw.schema import MIGRATIONS, VERSION


def _backup(path: Path, version: int) -> None:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = path.with_name(f'nw.v{version}.{stamp}.{uuid4().hex[:8]}.bak')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(target)) as backup:
                source.backup(backup)
                if (backup.execute('PRAGMA user_version').fetchone()[0] != version or
                        [row[0] for row in backup.execute('PRAGMA integrity_check')] != ['ok']):
                    raise ValueError(f'Cannot verify database backup: {target}')
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _apply(connection: sqlite3.Connection, script: str) -> None:
    # executescript would commit the transaction before applying the DDL.
    statement = ''
    for line in script.splitlines(keepends=True):
        if line.strip() in ('BEGIN IMMEDIATE;', 'COMMIT;'):
            continue
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ''
    if statement.strip():
        raise ValueError('Incomplete migration statement')


def _step(connection: sqlite3.Connection, version: int) -> int:
    if version not in MIGRATIONS:
        raise ValueError(f'Unsupported database version: {version}')
    _apply(connection, MIGRATIONS[version])
    next_version = connection.execute('PRAGMA user_version').fetchone()[0]
    if next_version != version + 1:
        raise ValueError(f'Migration from v{version} did not advance one version')
    return next_version


def upgrade(connection: sqlite3.Connection, path: Path) -> None:
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    while version != VERSION:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version == VERSION:
                return
            if version == 0:
                # A fresh database has no previous project data to back up.
                while version != VERSION:
                    version = _step(connection, version)
                return
            if version not in MIGRATIONS:
                raise ValueError(f'Unsupported database version: {version}')
            _backup(path.resolve(), version)
            version = _step(connection, version)
