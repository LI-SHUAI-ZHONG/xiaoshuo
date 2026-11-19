"""Archive/verify/restore the material runtime baseline using only the stdlib.

The archive never includes API configuration, novel project databases or temp
semantic indexes. Existing runtime files are never overwritten on restore.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from uuid import uuid4
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
DEFAULT_BASELINE = PROJECT / 'fixtures/materials_runtime_baseline/v3-20261119'
PART_BYTES = 64 * 1024 * 1024
DATABASES = ('catalog.db', 'adjudication.db')


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def record(path: Path, relative: str) -> dict:
    return {'path': relative, 'bytes': path.stat().st_size, 'sha256': digest(path)}


def contained(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError(f'Path outside archive root: {relative}')
    return target


def core_hash() -> str:
    sys.path.insert(0, str(PROJECT / 'src'))
    from nw.materials.adjudication import _code_hash
    return _code_hash()


def scratch(label: str) -> Path:
    root = PROJECT / 'build' / 'materials-baseline'
    target = contained(root, f'{label}-{uuid4().hex}')
    target.mkdir(parents=True)
    return target


def snapshot(workspace: Path, output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError('Choose a new snapshot directory; existing snapshots are immutable')
    folder = workspace.resolve() / 'materials'
    if any(not (folder / name).is_file() for name in DATABASES):
        raise FileNotFoundError('Both catalog.db and adjudication.db are required')
    output.mkdir(parents=True)
    build = scratch('snapshot')
    source_manifest = PROJECT / 'fixtures/material_semantics/current_version_manifest.json'
    inputs = json.loads(source_manifest.read_text(encoding='utf-8'))['catalog_inputs']
    originals = []
    for item in inputs:
        source = contained(REPOSITORY, item['path'])
        entry = record(source, item['path'])
        if entry['sha256'] != item['sha256'] or entry['bytes'] != item['bytes']:
            raise ValueError(f'Original material version mismatch: {item["path"]}')
        originals.append(entry)
    selected, excluded = [], []
    for file in sorted(folder.iterdir()):
        if not file.is_file():
            continue
        if file.name in DATABASES:
            target = build / file.name
            with closing(sqlite3.connect(file.resolve().as_uri() + '?mode=ro', uri=True)) as source, \
                 closing(sqlite3.connect(target)) as saved:
                source.backup(saved)
                if saved.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError(f'Invalid SQLite snapshot: {file.name}')
            selected.append((target, 'materials/' + file.name))
            print(f'Frozen SQLite snapshot: {file.name}', flush=True)
        elif file.suffix in ('.json', '.jsonl', '.md') and file.stat().st_size <= 16 * 1024 * 1024:
            target = build / file.name
            shutil.copy2(file, target)
            selected.append((target, 'materials/' + file.name))
        else:
            excluded.append({'path': file.name, 'bytes': file.stat().st_size,
                             'reason': 'generated semantic cache, historical full audit, or interrupted temporary file'})
    archive = build / 'materials.zip'
    entries = [record(file, relative) for file, relative in selected]
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipped:
        for file, relative in selected:
            zipped.write(file, relative)
            print(f'Archived: {relative}', flush=True)
    parts = []
    with archive.open('rb') as stream:
        number = 1
        while block := stream.read(PART_BYTES):
            name = f'materials.zip.part{number:03d}'
            file = output / name
            file.write_bytes(block)
            parts.append(record(file, name))
            number += 1
    manifest = {'format_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'current material runtime baseline; no API secrets or novel projects',
                'protected_core_sha256': core_hash(), 'originals': originals, 'entries': entries,
                'archive': record(archive, 'materials.zip'), 'parts': parts, 'excluded_caches': excluded}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'output': str(output), 'entries': len(entries), 'parts': len(parts),
            'compressed_bytes': archive.stat().st_size}


def verify(baseline: Path) -> dict:
    baseline = baseline.resolve()
    data = json.loads((baseline / 'manifest.json').read_text(encoding='utf-8'))
    if data.get('format_version') != 1:
        raise ValueError('Unsupported baseline manifest')
    if data['protected_core_sha256'] != core_hash():
        raise ValueError('Core adjudication code changed; rebuild the baseline instead of restoring stale adjudications')
    for entry in data['originals']:
        file = contained(REPOSITORY, entry['path'])
        if record(file, entry['path']) != entry:
            raise ValueError(f'Original material mismatch: {entry["path"]}')
    for entry in data['parts']:
        file = contained(baseline, entry['path'])
        if record(file, entry['path']) != entry:
            raise ValueError(f'Archive part mismatch: {entry["path"]}')
    expected = set()
    for entry in data['entries']:
        relative = entry['path']
        if len(Path(relative).parts) != 2 or Path(relative).parts[0] != 'materials' or relative in expected:
            raise ValueError(f'Invalid or duplicate archive member: {relative}')
        contained(baseline, relative)
        expected.add(relative)
    return data


def restore(baseline: Path, workspace: Path) -> dict:
    data = verify(baseline)
    workspace = workspace.resolve()
    # Preflight every destination before creating any runtime files.
    for entry in data['entries']:
        target = contained(workspace, entry['path'])
        if target.exists() and (not target.is_file() or digest(target) != entry['sha256']):
            raise FileExistsError(f'Existing runtime file differs; choose an empty workspace: {target}')
    build = scratch('restore')
    archive = build / 'materials.zip'
    with archive.open('wb') as target:
        for part in data['parts']:
            with contained(baseline.resolve(), part['path']).open('rb') as source:
                shutil.copyfileobj(source, target, 1024 * 1024)
    if record(archive, 'materials.zip') != data['archive']:
        raise ValueError('Combined archive digest mismatch')
    with zipfile.ZipFile(archive) as zipped:
        if set(zipped.namelist()) != {entry['path'] for entry in data['entries']}:
            raise ValueError('Archive member list differs from manifest')
        for entry in data['entries']:
            target = contained(build, entry['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(entry['path']) as source, target.open('wb') as saved:
                shutil.copyfileobj(source, saved, 1024 * 1024)
            if record(target, entry['path']) != entry:
                raise ValueError(f'Extracted material mismatch: {entry["path"]}')
            if target.name in DATABASES:
                with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise ValueError('SQLite snapshot failed integrity check')
    for entry in data['entries']:
        target = contained(workspace, entry['path'])
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(contained(build, entry['path']), target)
    return {'workspace': str(workspace), 'restored_files': len(data['entries']), 'verified': True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'verify', 'restore'))
    parser.add_argument('--workspace', type=Path, default=PROJECT / 'workspace')
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    if args.action == 'snapshot':
        result = snapshot(args.workspace, args.baseline)
    elif args.action == 'restore':
        result = restore(args.baseline, args.workspace)
    else:
        data = verify(args.baseline)
        result = {'verified': True, 'entries': len(data['entries']), 'parts': len(data['parts'])}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
