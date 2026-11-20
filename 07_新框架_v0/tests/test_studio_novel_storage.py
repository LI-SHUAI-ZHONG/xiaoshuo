import os
from pathlib import Path

import pytest

from nw.project_paths import FORMAL_BOOKS_ROOT, FORMAL_WORKSPACE, project_directory, projects_root_for
from nw.cli import main
from nw.store import Store
from nw.studio.api import StudioService


def test_formal_and_isolated_roots(tmp_path):
    expected = Path(r'D:\小说仓库') if os.name == 'nt' else Path.home() / '小说仓库'
    assert projects_root_for(FORMAL_WORKSPACE) == expected.resolve()
    assert projects_root_for(tmp_path) == tmp_path.resolve()
    # The production path may exist and contain real books. Refuse before writing anything there.
    with pytest.raises(ValueError, match='test store'):
        Store(tmp_path / 'isolated', projects_root=FORMAL_BOOKS_ROOT, create=True, test_mode=True)
    with pytest.raises(ValueError, match='Invalid project'):
        project_directory(tmp_path, '_NOVEL_CACHE')


def test_reserved_project_directory_applies_only_to_new_files_not_titles_or_existing_books(tmp_path):
    studio = StudioService(tmp_path, config_path=tmp_path / 'missing.toml')
    for reserved in ('_book', '.book', 'LIBRARY', 'MaTeRiaLs'):
        with pytest.raises(ValueError, match='作品目录名'):
            studio.create_project(reserved, '自选书名')
        assert not (tmp_path / reserved).exists()
    studio.create_project('existing', '_书名可以保留')
    (tmp_path / 'existing').rename(tmp_path / '_legacy')
    assert studio.project_overview('_legacy')['project']['name'] == '_书名可以保留'


def test_unconfigured_api_honors_isolated_workspace_for_studio_and_cli(tmp_path):
    config = tmp_path / 'studio.toml'
    config.write_text('[paths]\nworkspace = "isolated"\n', encoding='utf-8')
    studio = StudioService(config_path=config)
    assert studio.workspace == studio.projects_root == tmp_path / 'isolated'
    assert studio.ledger_path == studio.workspace / 'materials' / 'F2_统一问题台账.jsonl'
    assert studio._get_desk() is None and studio._get_ledger() == []
    studio.ledger_path.parent.mkdir()
    studio.ledger_path.write_text('{"status":"open","source":"隔离资料"}\n', encoding='utf-8')
    assert studio._get_ledger()[0]['source'] == '隔离资料'
    assert main(['--config', str(config), '--project', '未配置', 'init', '--name', '离线书']) == 0
    assert studio.list_projects()[0]['name'] == '离线书'


def test_isolated_writer_and_reopened_reader_use_same_book_directory(tmp_path):
    workspace, books = tmp_path / 'workflow', tmp_path / 'books'
    config = tmp_path / 'absent.toml'
    writer = StudioService(workspace, projects_root=books, config_path=config)
    project = writer.create_project('试读', '春雨', brief_text='一封家书')
    assert project['data_directory'] == str(books / '试读')
    assert writer.system_status()['projects_root'] == str(books)
    with writer._open_store('试读') as store:
        assert store.directory.parent == workspace
        assert store.data_directory == books / '试读'
        assert store.data_file('nw.db').is_file()
        with pytest.raises(ValueError, match='inside'):
            store.data_file('..', 'elsewhere')
    assert not (workspace / '试读').exists()
    reader = StudioService(workspace, projects_root=books, config_path=config)
    [listed] = reader.list_projects()
    assert listed['name'] == '春雨'
    assert listed['latest_brief']['text'] == '一封家书'
