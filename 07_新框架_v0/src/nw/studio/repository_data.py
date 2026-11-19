"""Git-managed, deterministic snapshots of actual Studio books and library data."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4
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
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def runtime_files(workspace: Path) -> list[Path]:
    """Only actual top-level projects and the Studio library; never QA caches."""
    folders = [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith(('_', '.'))
               and (p.name == 'library' or (p / 'nw.db').is_file())]
    result = []
    for folder in folders:
        for path in sorted(folder.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(workspace)
            if (any(part in ('locks', '__pycache__', '.secrets', 'secrets') for part in relative.parts)
                    or path.name.endswith(('-wal', '-shm', '-journal', '.lock', '.tmp', '.log'))
                    or path.name in ('config.toml', '.env') or path.name.startswith('.env.')):
                continue
            if path.resolve() != path.absolute() or not path.resolve().is_relative_to(workspace.resolve()):
                raise ValueError('不能将指向工作区之外的资料别名上传 Git')
            result.append(path)
    return sorted(result)


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
        if len(Path(name).parts) < 2 or Path(name).parts[0].startswith(('_', '.')) or name in names:
            raise ValueError('快照包含无效或重复路径')
        if target.name.endswith(('-wal', '-shm', '-journal', '.lock')):
            raise ValueError('快照不能包含数据库日志或锁文件')
        names.add(name)
    signature = hashlib.sha256(json.dumps(data['entries'], sort_keys=True).encode()).hexdigest()
    if signature != data['content_sha256']:
        raise ValueError('小说资料清单校验不一致')
    return data


def verify_parts(folder: Path, data: dict) -> None:
    for part in data['parts']:
        path = inside(folder, part['path'])
        if path.stat().st_size != part['bytes'] or digest(path) != part['sha256']:
            raise ValueError('Git 小说资料分片损坏：' + part['path'])


def snapshot(workspace: Path, folder: Path, *, persist: bool = True) -> dict:
    build = workspace / '_git_sync' / 'snapshot-cache'
    build.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in runtime_files(workspace):
        name = path.relative_to(workspace).as_posix()
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
    return {'changed': True, **data}


def apply_files(staged: Path, workspace: Path, entries: list[dict]) -> None:
    """Preflight all files, keep prior local bytes, then replace while HTTP is locked."""
    backups = workspace / '_git_sync' / 'backups' / uuid4().hex
    changed = []
    for entry in entries:
        name = entry['path']
        source, target = inside(staged, name), inside(workspace, name)
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
            backup = inside(backups, name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
        changed.append((source, target))
    for source, target in changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.git-restore-' + uuid4().hex + '.tmp')
        shutil.copy2(source, temporary)
        temporary.replace(target)


def restore(folder: Path, workspace: Path) -> dict | None:
    data = load_manifest(folder)
    if data is None:
        return None
    verify_parts(folder, data)
    expected = {entry['path'] for entry in data['entries']}
    extra = {p.relative_to(workspace).as_posix() for p in runtime_files(workspace)} - expected
    if extra:
        raise ValueError('本地有 Git 快照未包含的作品文件，已保留；请先保存本地版本再同步')
    build = workspace / '_git_sync' / 'restores' / uuid4().hex
    build.mkdir(parents=True)
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
            if target.suffix == '.db':
                with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise ValueError('Git 小说数据库完整性检查失败')
    marker = workspace / '_git_sync/restore_pending.json'
    atomic_json(marker, {'content_sha256': data['content_sha256'], 'complete': False})
    apply_files(build, workspace, data['entries'])
    atomic_json(marker, {'content_sha256': data['content_sha256'], 'complete': True})
    return data
