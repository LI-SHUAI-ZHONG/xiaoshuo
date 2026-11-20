"""Resolve novel storage separately from the workspace that owns workflow materials."""
import os
from pathlib import Path
import re

FORMAL_WORKSPACE = Path(__file__).resolve().parents[2] / 'workspace'
FORMAL_BOOKS_ROOT = Path(r'D:\小说仓库') if os.name == 'nt' else Path.home() / '小说仓库'


def projects_root_for(workspace: Path, override: Path | None = None) -> Path:
    workspace = workspace.resolve()
    if override is not None:
        return override.resolve()
    if workspace == FORMAL_WORKSPACE.resolve():
        return FORMAL_BOOKS_ROOT.resolve()
    return workspace


def contained_file(root: Path, *parts: str) -> Path:
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Project output must stay inside its data directory')
    return path


def project_directory(root: Path, name: str) -> Path:
    """Accept a single Windows-compatible project name, including for old CLI callers."""
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)}
    if (not name or name in ('.', '..') or name.casefold() == '_novel_cache'
            or name.endswith((' ', '.')) or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.split('.')[0].upper() in reserved):
        raise ValueError('Invalid project directory name')
    root = root.resolve()
    directory = (root / name).resolve()
    if directory.parent != root or directory.name.casefold() != name.casefold():
        raise ValueError('Project directory must stay inside workspace')
    return directory
