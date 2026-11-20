"""Apply a synced deletion only to the same local novel and project identity."""
from contextlib import closing
from pathlib import Path
import sqlite3

from nw.project_paths import project_directory
from nw.studio.novel_cache import project_identity
from nw.studio.project_migration import plain_path


def _rows(library: Path, table: str, fields: str) -> list[dict]:
    if not library.is_file():
        return []
    plain_path(library)
    with closing(sqlite3.connect(library.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            return []
        return [dict(row) for row in db.execute(f'SELECT {fields} FROM {table}')]


def plan_remote_deletions(staged: Path, workspace: Path, root: Path, local: set[str], expected: set[str]) -> list[dict]:
    remote = staged / 'library/library.db'
    tombstones = _rows(remote, 'novel_deletions', 'novel_id,project_dir,project_id,deleted_at')
    by_project = {(r['project_dir'], r['project_id']): r for r in tombstones if r['project_id']}
    active = {r['project_dir']: r for r in _rows(workspace / 'library/library.db', 'novels', 'id,project_dir,title')}
    extra = local - expected
    archives = []
    book_names = {p.split('/', 1)[0] for p in local | expected if not p.startswith('library/')}
    for name in sorted(book_names):
        folder = project_directory(root, name)
        db_name = f'{name}/nw.db'
        if db_name not in local:
            if folder.exists():
                raise ValueError('本地同名目录已存在，已保留：' + name)
            continue
        current_id = project_identity(folder)
        incoming = project_identity(staged / name) if db_name in expected else None
        tomb = by_project.get((name, current_id))
        if tomb:
            novel = active.get(name)
            if incoming == current_id or (novel and novel['id'] != tomb['novel_id']):
                raise ValueError('删除记录与本地或远端作品身份冲突，已保留：' + name)
            archives.append({**tomb, 'title': novel['title'] if novel else name})
            extra = {path for path in extra if not path.startswith(name + '/')}
        elif incoming != current_id:
            raise ValueError('本地有 Git 快照未包含的作品或同名不同身份的作品，已保留：' + name)
    if extra:
        raise ValueError('本地有 Git 快照未包含的作品文件，已保留；请先保存本地版本再同步')
    return archives
