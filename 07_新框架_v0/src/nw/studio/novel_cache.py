"""Move a single verified project into local storage; keep deletion identities in the shared library."""
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from uuid import uuid4

from nw.call_control import lock_file
from nw.project_paths import project_directory
from nw.store import now


def _direct(path: Path) -> Path:
    if os.path.lexists(path):
        info = path.lstat()
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f'作品或缓存路径是链接，不能操作：{path}')
    return path


def _source(root: Path, name: str) -> Path:
    if name.casefold() in {'library', 'materials', '_git_sync'}:
        raise ValueError('不能把公共资料目录当作作品')
    project_directory(root, name)
    return _direct(root / name)


def _db_read(path: Path):
    for suffix in ('-wal', '-shm', '-journal'):
        _direct(path / ('nw.db' + suffix))
    return closing(sqlite3.connect(_direct(path / 'nw.db').as_uri() + '?mode=ro', uri=True, timeout=8))


def project_identity(path: Path) -> str:
    """Read the internal project ID without opening the database for migrations."""
    with _db_read(_direct(path.absolute())) as conn:
        rows = conn.execute('SELECT id FROM projects LIMIT 2').fetchall()
    if len(rows) != 1 or not rows[0][0]:
        raise ValueError('作品目录没有可核对的唯一项目身份')
    return rows[0][0]


def _cache(root: Path) -> Path:
    return _direct(root / '_novel_cache')


def _key(ident: str) -> str:
    return hashlib.sha256(ident.encode('utf-8')).hexdigest()


@contextmanager
def _cache_lock(root: Path):
    folder = _cache(root)
    folder.mkdir(parents=True, exist_ok=True)
    lock = _direct(folder / '.maintenance.lock')
    with lock_file(lock) as acquired:
        if not acquired:
            raise ValueError('另一个客户端正在移动或清理作品缓存，请稍后重试')
        yield folder


def _read_entry(directory: Path) -> dict:
    _direct(directory)
    marker = _direct(directory / 'entry.json')
    data = json.loads(marker.read_text(encoding='utf-8'))
    keys = {'id', 'project_dir', 'project_id', 'title', 'deleted_at'}
    if (not isinstance(data, dict) or set(data) != keys or not all(isinstance(data[k], str) for k in keys)
            or not data['id'] or _key(data['id']) != directory.name):
        raise ValueError('缓存条目标识不一致')
    return data


def _entries(folder: Path):
    if not folder.is_dir():
        return
    for directory in sorted(folder.iterdir()):
        # Only cache entries made by this service are ever candidates for cleanup.
        if len(directory.name) == 64 and all(c in '0123456789abcdef' for c in directory.name):
            _direct(directory)
            if (directory / 'entry.json').is_file():
                yield directory, _read_entry(directory)


def _ensure_idle(project: Path) -> None:
    locks = _direct(project / 'locks')
    if not locks.is_dir():
        return
    for path in locks.glob('*.lock'):
        _direct(path)
        with lock_file(path) as free:
            if not free:
                raise ValueError('作品仍有制作任务在执行，请暂停并等当前调用结束后再删除')


def _archive(root: Path, folder: Path, entry: dict) -> dict:
    source = _source(root, entry['project_dir'])
    directory = _direct(folder / _key(entry['id']))
    payload = _direct(directory / 'project')
    if directory.exists():
        saved = _read_entry(directory)
        if any(saved[k] != entry[k] for k in ('id', 'project_dir', 'project_id')):
            raise ValueError('该缓存位置已属于另一份作品')
        entry = saved
        if payload.exists() or (directory / 'clearing').exists():
            if payload.exists() and project_identity(payload) != entry['project_id']:
                raise ValueError('缓存中的作品身份不一致')
            if source.exists() and project_identity(source) == entry['project_id']:
                raise ValueError('活动目录与缓存同时存在同一作品，请检查这两份数据')
            return entry
    if source.exists():
        if not entry['project_id'] or project_identity(source) != entry['project_id']:
            raise ValueError('目录现在属于其他作品，已保留原文件')
        _ensure_idle(source)
    if not directory.exists():
        install = folder / ('.new-' + uuid4().hex)
        install.mkdir()
        try:
            (install / 'entry.json').write_text(json.dumps(entry, ensure_ascii=False), encoding='utf-8')
            install.rename(directory)
        finally:
            if install.exists():
                (install / 'entry.json').unlink(missing_ok=True)
                install.rmdir()
    if source.exists():
        source.rename(payload)
    return entry


def archive_deleted_project(projects_root: Path, novel_id: str, project_dir: str, project_id: str,
                            title: str, deleted_at: str) -> dict:
    root = projects_root.resolve()
    entry = {'id': novel_id, 'project_dir': project_dir, 'project_id': project_id or '',
             'title': title, 'deleted_at': deleted_at}
    with _cache_lock(root) as folder:
        return _archive(root, folder, entry)


def _purge(directory: Path, entry: dict) -> None:
    payload, clearing = (_direct(directory / name) for name in ('project', 'clearing'))
    if {p.name for p in directory.iterdir()} - {'project', 'clearing', 'entry.json'}:
        raise ValueError('缓存条目包含其他文件，已保留')
    if payload.exists():
        if clearing.exists() or project_identity(payload) != entry['project_id']:
            raise ValueError('缓存中的作品身份不一致')
        payload.rename(clearing)
    if clearing.exists():
        # The identity was checked before this rename. If cleanup stopped halfway,
        # the DB may already have gone; resume only inside this same entry.
        if (clearing / 'nw.db').exists() and project_identity(clearing) != entry['project_id']:
            raise ValueError('待清理目录的作品身份不一致')
        shutil.rmtree(clearing)
    (directory / 'entry.json').unlink()
    directory.rmdir()


def _forget(db, entry: dict) -> None:
    ident = entry['id']
    db.execute('INSERT OR IGNORE INTO novel_deletions VALUES(?,?,?,?)',
               (ident, entry['project_dir'], entry['project_id'] or None, entry['deleted_at']))
    db.execute('DELETE FROM reviewed_adoptions WHERE novel_id=?', (ident,))
    db.execute('UPDATE usage_stats SET adopt_count=(SELECT count(*) FROM reviewed_adoptions a WHERE a.option_key=usage_stats.option_key)')
    db.execute('DELETE FROM timeline_events WHERE novel_id=?', (ident,))
    db.execute('DELETE FROM wizard_choices WHERE novel_id=?', (ident,))
    db.execute('DELETE FROM novels WHERE id=?', (ident,))


class NovelCacheMixin:
    def _cache_result(self, entries: list[dict]) -> dict:
        root = self.studio.projects_root
        return {'cache_count': len(entries), 'entries': sorted(entries, key=lambda r: r['deleted_at'], reverse=True),
                'storage_path': str(root), 'cache_path': str(_cache(root))}

    def _recover_cache(self, db, folder: Path) -> list[tuple[Path, dict]]:
        visible = []
        for directory, entry in _entries(folder):
            tomb = db.execute('SELECT project_dir,project_id FROM novel_deletions WHERE novel_id=?', (entry['id'],)).fetchone()
            if tomb:
                if (tomb['project_dir'], tomb['project_id'] or '') != (entry['project_dir'], entry['project_id']):
                    raise ValueError('缓存记录与作品删除记录不一致')
                if entry['project_id'] and not any(_direct(directory / part).exists() for part in ('project', 'clearing')):
                    source = _source(self.studio.projects_root, entry['project_dir'])
                    if source.is_dir() and project_identity(source) == entry['project_id']:
                        _archive(self.studio.projects_root, folder, entry)
                visible.append((directory, entry))
                continue
            row = db.execute('SELECT project_dir,project_id FROM novels WHERE id=?', (entry['id'],)).fetchone()
            if row is None or row['project_dir'] != entry['project_dir'] or row['project_id'] not in (None, entry['project_id']):
                continue
            payload = _direct(directory / 'project')
            if payload.is_dir() and project_identity(payload) == entry['project_id']:
                source = _source(self.studio.projects_root, entry['project_dir'])
                if source.is_dir() and project_identity(source) == entry['project_id']:
                    raise ValueError('活动目录与缓存同时存在同一作品，请检查这两份数据')
                _forget(db, entry)
                visible.append((directory, entry))
        return visible

    def novel_cache(self) -> dict:
        root = self.studio.projects_root
        if not _cache(root).is_dir():
            return self._cache_result([])
        with self._lock, self.db.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            with _cache_lock(root) as folder:
                return self._cache_result([e for _, e in self._recover_cache(db, folder)])

    def trash_novel(self, ident: str) -> dict:
        root = self.studio.projects_root
        with self._lock, self.db.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            with _cache_lock(root) as folder:
                visible = self._recover_cache(db, folder)
                tomb = db.execute('SELECT * FROM novel_deletions WHERE novel_id=?', (ident,)).fetchone()
                if tomb:
                    entry = next((e for _, e in visible if e['id'] == ident), {})
                    return {**self._cache_result([e for _, e in visible]), 'id': ident, 'title': entry.get('title', '')}
                row = db.execute('SELECT * FROM novels WHERE id=?', (ident,)).fetchone()
                if row is None:
                    raise FileNotFoundError('未找到这本小说')
                worker = self._workers.get(ident)
                if worker and worker.is_alive():
                    raise ValueError('作品仍有制作任务在执行，请暂停并等当前调用结束后再删除')
                project = _source(root, row['project_dir'])
                if db.execute('SELECT 1 FROM novels WHERE lower(project_dir)=lower(?) AND id<>?', (row['project_dir'], ident)).fetchone():
                    raise ValueError('另一本作品也登记了同一目录，请先核对目录归属')
                internal = row['project_id'] or ''
                if project.exists():
                    actual = project_identity(project)
                    if not internal:
                        # Legacy imports used the internal project ID; wizard novels
                        # kept their independently generated job ID in the project DB.
                        if actual == ident:
                            internal = actual
                        elif row['job_id']:
                            with _db_read(project) as source:
                                if source.execute('SELECT 1 FROM novel_jobs WHERE id=?', (row['job_id'],)).fetchone():
                                    internal = actual
                    if actual != internal:
                        raise ValueError('缺少与当前目录一致的作品身份，已保留原文件')
                entry = _archive(root, folder, {'id': ident, 'project_dir': row['project_dir'], 'project_id': internal,
                                                'title': row['title'], 'deleted_at': now()})
                _forget(db, entry)
                return {**self._cache_result([*[e for _, e in visible], entry]), 'id': ident, 'title': row['title']}

    def clear_novel_cache(self) -> dict:
        root = self.studio.projects_root
        if not _cache(root).is_dir():
            return {**self._cache_result([]), 'cleared_count': 0}
        with self._lock, self.db.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            with _cache_lock(root) as folder:
                entries = self._recover_cache(db, folder)
                db.commit()  # Recovered shelf tombstones must be durable before erasing the only local copy.
                for directory, entry in entries:
                    _purge(directory, entry)
                return {**self._cache_result([]), 'cleared_count': len(entries)}
