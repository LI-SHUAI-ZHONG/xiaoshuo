"""Move legacy working novels to their configured physical shelf on startup."""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory

from nw.project_paths import project_directory


def plain_path(path: Path) -> None:
    if path.is_symlink() or path.absolute() != path.resolve():
        raise ValueError(f'作品路径含有链接，已保留原文件：{path}')


def migrate_legacy_projects(workspace: Path, root: Path) -> None:
    if workspace.resolve() == root.resolve():
        return
    plain_path(root)
    root.mkdir(parents=True, exist_ok=True)
    moves = []
    for source in workspace.iterdir():
        if (source.name.startswith(('_', '.')) or source.name in ('library', 'materials')
                or not (source / 'nw.db').is_file()):
            continue
        plain_path(source)
        for entry in source.rglob('*'):
            plain_path(entry)
        with closing(sqlite3.connect((source / 'nw.db').as_uri() + '?mode=ro', uri=True)) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'").fetchone():
                continue
        target = project_directory(root, source.name)
        if target.exists():
            raise ValueError(f'新旧小说目录同时存在，请核对两个版本：{source}、{target}')
        moves.append((source, target))
    for source, target in moves:
        if source.stat().st_dev == root.stat().st_dev:
            source.rename(target)
        else:
            from nw.studio.repository_data import digest
            with TemporaryDirectory(dir=root, prefix='_migration_') as tmp:
                staged = Path(tmp) / 'project'
                shutil.copytree(source, staged)
                def inventory(folder: Path) -> dict:
                    return {p.relative_to(folder): digest(p) for p in folder.rglob('*') if p.is_file()}
                if inventory(source) != inventory(staged):
                    raise ValueError(f'跨盘迁移期间作品文件有变化，已保留原文件：{source}')
                os.rename(staged, target)
                if source.resolve().parent != workspace.resolve():
                    raise ValueError('旧作品不在原工作区')
                shutil.rmtree(source)
