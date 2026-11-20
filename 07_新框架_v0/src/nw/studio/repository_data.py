"""Git-managed, deterministic snapshots of actual Studio books and library data."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4

from nw.studio.project_migration import plain_path
import zipfile

PART_BYTES = 64 * 1024 * 1024


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def inside(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError('资料路径超出仓库目录')
    return target


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def runtime_sources(workspace: Path, projects_root: Path | None = None) -> dict[str, Path]:
    """Portable manifest names for shared library data and active physical novels."""
    root = projects_root or workspace
    folders = [workspace / 'library']
    if root.is_dir():
        folders.extend(p for p in root.iterdir() if p.is_dir() and p.name not in ('library', 'materials')
                       and not p.name.startswith(('_', '.')) and (p / 'nw.db').is_file())
    result = {}
    for folder in folders:
        plain_path(folder)
        for path in sorted(folder.rglob('*')):
            relative = path.relative_to(folder.parent)
            if (any(part in ('locks', '__pycache__', '.secrets', 'secrets', '_sync_backups') for part in relative.parts)
                    or path.name.endswith(('-wal', '-shm', '-journal', '.lock', '.tmp', '.log'))
                    or path.name in ('config.toml', '.env') or path.name.startswith('.env.')):
                continue
            plain_path(path)
            if path.is_file():
                result[relative.as_posix()] = path
    return dict(sorted(result.items(), key=lambda pair: Path(pair[0])))


def runtime_files(workspace: Path, projects_root: Path | None = None) -> list[Path]:
    return list(runtime_sources(workspace, projects_root).values())


def frozen_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == '.db':
        if source.resolve() == target.resolve():
            raise ValueError('资料快照不能覆盖正在读取的数据库')
        target.write_bytes(b'')
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as live, \
                closing(sqlite3.connect(target)) as saved:
            live.backup(saved)
            if saved.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('小说资料库完整性检查失败')
    else:
        shutil.copy2(source, target)


def load_manifest(folder: Path) -> dict | None:
    path = folder / 'current.json'
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format_version') != 1 or not isinstance(data.get('entries'), list):
        raise ValueError('不支持的小说资料快照格式')
    names = set()
    for entry in data['entries']:
        name = entry['path']
        target = inside(folder, name)
        parts = PurePosixPath(name).parts
        if (len(parts) < 2 or PurePosixPath(*parts).as_posix() != name
                or parts[0].startswith(('_', '.')) or parts[0].casefold() == 'materials'
                or (parts[0].casefold() == 'library' and parts[0] != 'library')
                or any(p in ('.', '..') or ':' in p or '\\' in p for p in parts)
                or name.casefold() in names):
            raise ValueError('快照包含无效或重复路径')
        if target.name.endswith(('-wal', '-shm', '-journal', '.lock')):
            raise ValueError('快照不能包含数据库日志或锁文件')
        names.add(name.casefold())
    signature = hashlib.sha256(json.dumps(data['entries'], sort_keys=True).encode()).hexdigest()
    if signature != data['content_sha256']:
        raise ValueError('小说资料清单校验不一致')
    return data


def verify_parts(folder: Path, data: dict) -> None:
    for index, part in enumerate(data['parts'], 1):
        if part['path'] != f'runtime.zip.part{index:03d}':
            raise ValueError('Git 小说资料分片名称无效')
        path = inside(folder, part['path'])
        if path.stat().st_size != part['bytes'] or digest(path) != part['sha256']:
            raise ValueError('Git 小说资料分片损坏：' + part['path'])


def cleanup_legacy_snapshot(workspace: Path, manifest: dict) -> None:
    """Retire old generated working copies only where a verified Git copy still exists."""
    build = workspace / '_git_sync' / 'snapshot-cache'
    plain_path(build)
    if not build.is_dir():
        return
    known = {r['path']: r['sha256'] for r in manifest['entries'] + manifest['parts']}
    known['runtime.zip'] = manifest['archive_sha256']
    for name, expected in known.items():
        path = inside(build, name)
        plain_path(build / name)
        if path.is_file() and digest(path) == expected:
            path.unlink()
    for directory in sorted((p for p in build.rglob('*') if p.is_dir()), reverse=True):
        plain_path(directory)
        if not any(directory.iterdir()):
            directory.rmdir()
    if not any(build.iterdir()):
        build.rmdir()


def snapshot(workspace: Path, folder: Path, *, persist: bool = True, projects_root: Path | None = None) -> dict:
    scratch = workspace / '_git_sync'
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix='snapshot-') as temp:
        return _snapshot(workspace, projects_root, folder, Path(temp), persist)


def _snapshot(workspace: Path, projects_root: Path | None, folder: Path, build: Path, persist: bool) -> dict:
    entries = []
    for name, path in runtime_sources(workspace, projects_root).items():
        target = inside(build, name)
        frozen_copy(path, target)
        entries.append({'path': name, 'bytes': target.stat().st_size, 'sha256': digest(target)})
    signature = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    previous = load_manifest(folder)
    if previous and previous['content_sha256'] == signature:
        verify_parts(folder, previous)
        return {'changed': False, **previous}
    if not persist:
        return {'changed': True, 'entries': entries, 'content_sha256': signature}
    archive = build / 'runtime.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for entry in entries:
            info = zipfile.ZipInfo(entry['path'], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with inside(build, entry['path']).open('rb') as source, zipped.open(info, 'w') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    with archive.open('rb') as stream:
        number = 1
        while chunk := stream.read(PART_BYTES):
            name = f'runtime.zip.part{number:03d}'
            path = folder / name
            temporary = build / name
            temporary.write_bytes(chunk)
            shutil.copyfile(temporary, path)
            parts.append({'path': name, 'bytes': len(chunk), 'sha256': digest(path)})
            number += 1
    data = {'format_version': 1, 'content_sha256': signature, 'entries': entries,
            'archive_sha256': digest(archive), 'parts': parts}
    atomic_json(folder / 'current.json', data)
    for old in folder.glob('runtime.zip.part*'):
        if re.fullmatch(r'runtime[.]zip[.]part[0-9]{3,}', old.name) and old.name not in {p['path'] for p in parts}:
            plain_path(old)
            old.unlink()
    return {'changed': True, **data}


def apply_files(staged: Path, workspace: Path, entries: list[dict], projects_root: Path | None = None) -> None:
    """Preflight all files, keep prior local bytes, then replace while HTTP is locked."""
    backups = workspace / '_git_sync' / 'backups' / uuid4().hex
    changed = []
    for entry in entries:
        name = entry['path']
        relative = Path(name)
        book = projects_root is not None and projects_root != workspace and relative.parts[0] != 'library'
        root = projects_root if book else workspace
        plain_path(root / relative)
        source, target = inside(staged, name), inside(root, name)
        if digest(source) != entry['sha256']:
            raise ValueError('解压资料校验失败：' + name)
        if target.is_file() and digest(target) == entry['sha256']:
            continue
        if target.exists():
            if not target.is_file():
                raise ValueError('资料目标不是文件：' + name)
            if target.suffix == '.db':
                with closing(sqlite3.connect(target)) as db:
                    if db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]:
                        raise ValueError('数据库仍在使用，稍后重试同步')
            if book:
                place = inside(root, relative.parts[0]) / '_sync_backups' / backups.name
                plain_path(place)
                backup = inside(place, str(Path(*relative.parts[1:])))
            else:
                backup = inside(backups, name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
        changed.append((source, target))
    for source, target in changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.git-restore-' + uuid4().hex + '.tmp')
        shutil.copy2(source, temporary)
        temporary.replace(target)


def restore(folder: Path, workspace: Path, projects_root: Path | None = None) -> dict | None:
    data = load_manifest(folder)
    if data is None:
        return None
    verify_parts(folder, data)
    expected = {entry['path'] for entry in data['entries']}
    scratch = workspace / '_git_sync'
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix='restore-') as temp:
        _restore(folder, workspace, projects_root or workspace, Path(temp), data, expected)
    return data


def _restore(folder: Path, workspace: Path, root: Path, build: Path, data: dict, expected: set[str]) -> None:
    archive = build / 'runtime.zip'
    with archive.open('wb') as target:
        for part in data['parts']:
            with inside(folder, part['path']).open('rb') as source:
                shutil.copyfileobj(source, target, 1024 * 1024)
    if digest(archive) != data['archive_sha256']:
        raise ValueError('Git 小说资料合并分片校验失败')
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.namelist()) != len(expected) or set(zipped.namelist()) != expected:
            raise ValueError('Git 小说资料内容与清单不符')
        for entry in data['entries']:
            target = inside(build, entry['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(entry['path']) as source, target.open('wb') as saved:
                shutil.copyfileobj(source, saved, 1024 * 1024)
            if digest(target) != entry['sha256']:
                raise ValueError('解压资料校验失败：' + entry['path'])
            if target.suffix == '.db':
                with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise ValueError('Git 小说数据库完整性检查失败')
    from nw.studio.repository_books import plan_remote_deletions
    from nw.studio.novel_cache import archive_deleted_project
    archives = plan_remote_deletions(build, workspace, root, set(runtime_sources(workspace, root)), expected)
    marker = workspace / '_git_sync/restore_pending.json'
    atomic_json(marker, {'content_sha256': data['content_sha256'], 'complete': False})
    for entry in archives:
        archive_deleted_project(root, **entry)
    if root == workspace:
        apply_files(build, workspace, data['entries'])
    else:
        apply_files(build, workspace, data['entries'], projects_root=root)
    atomic_json(marker, {'content_sha256': data['content_sha256'], 'complete': True})
