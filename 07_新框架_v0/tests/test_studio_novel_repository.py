"""Exercise old workspaces, a D-style external shelf, and a second client's delete sync."""
from pathlib import Path
import shutil

import pytest

from nw.store import Store
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio.project_migration import migrate_legacy_projects
from nw.studio import repository_data as data


def make_client(base: Path):
    studio = StudioService(base / 'workspace', projects_root=base / 'books')
    return ProductionService(studio, LibraryService(studio.workspace), test_mode=True)


def seed(client, name: str):
    with client.open_store({'project_dir': name}, create=True) as store:
        internal = store.init_project('[FAKE] ' + name).id
    assert client.db.add(internal, name, name, {'imported': True, 'choices': []})
    path = client.studio.projects_root / name / '成品' / '全书.txt'
    path.parent.mkdir()
    path.write_text('[FAKE] test output ' + name, encoding='utf-8')
    return internal, path


def test_deletion_propagates_to_another_disk_and_clone_restores_only_live_books(tmp_path):
    author = make_client(tmp_path / 'author')
    ident, old = seed(author, 'to-delete')
    other_id, keep = seed(author, 'keep')
    folder = tmp_path / 'published'
    data.snapshot(author.studio.workspace, folder, projects_root=author.studio.projects_root)
    reader = make_client(tmp_path / 'reader')
    root = reader.studio.projects_root
    data.restore(folder, reader.studio.workspace, root)
    assert (root / 'to-delete/成品/全书.txt').read_bytes() == old.read_bytes()
    author.trash_novel(ident)
    published = data.snapshot(author.studio.workspace, folder, projects_root=author.studio.projects_root)
    assert {r['path'].split('/')[0] for r in published['entries']} == {'library', 'keep'}
    assert not (author.studio.workspace / '_git_sync/snapshot-cache').exists()
    data.restore(folder, reader.studio.workspace, root)
    data.restore(folder, reader.studio.workspace, root)
    assert not (root / 'to-delete').exists()
    assert reader.novel_cache()['entries'][0]['id'] == ident
    assert reader.db.get(other_id)['project_dir'] == 'keep'
    cached, = root.glob('_novel_cache/*/project/成品/全书.txt')
    assert 'to-delete' in cached.read_text(encoding='utf-8')
    assert reader.clear_novel_cache()['cleared_count'] == 1
    assert not cached.exists()
    assert (root / 'keep/成品/全书.txt').read_bytes() == keep.read_bytes()
    clone = make_client(tmp_path / 'fresh')
    data.restore(folder, clone.studio.workspace, clone.studio.projects_root)
    assert clone.novel_cache()['cache_count'] == 0
    assert [n['id'] for n in clone.list()['novels']] == [other_id]


def test_remote_tombstone_cannot_remove_same_named_replacement(tmp_path):
    author, reader = (make_client(tmp_path / n) for n in ['author', 'reader'])
    ident, _ = seed(author, 'reused')
    distinct, protected = seed(reader, 'reused')
    assert distinct != ident
    author.trash_novel(ident)
    folder = tmp_path / 'remote'
    data.snapshot(author.studio.workspace, folder, projects_root=author.studio.projects_root)
    with pytest.raises(ValueError, match='身份|已保留'):
        data.restore(folder, reader.studio.workspace, reader.studio.projects_root)
    assert protected.exists() and not reader.novel_cache()['entries']
    assert reader.db.get(distinct)['id'] == distinct


def test_legacy_migration_preflights_collisions_and_preserves_complete_project(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    root = tmp_path / 'new'
    for name in ('old-one', 'old-two'):
        with Store(workspace / name, create=True, test_mode=True) as store:
            store.init_project('[FAKE] legacy')
        (workspace / name / '正文.txt').write_text('迁移前的正文', encoding='utf-8')
    conflict = root / 'old-two'
    conflict.mkdir(parents=True)
    with pytest.raises(ValueError, match='同时存在'):
        migrate_legacy_projects(workspace, root)
    assert (workspace / 'old-one/正文.txt').is_file() and not (root / 'old-one').exists()
    conflict.rmdir()
    migrate_legacy_projects(workspace, root)
    migrate_legacy_projects(workspace, root)
    for name in ('old-one', 'old-two'):
        assert not (workspace / name).exists()
        assert (root / name / '正文.txt').read_text(encoding='utf-8') == '迁移前的正文'


def test_removes_only_verified_retired_snapshot_files(tmp_path):
    app = make_client(tmp_path)
    seed(app, 'book')
    manifest = data.snapshot(app.studio.workspace, tmp_path / 'git', projects_root=app.studio.projects_root)
    cache = app.studio.workspace / '_git_sync/snapshot-cache'
    scratch = cache / 'book/成品/全书.txt'
    scratch.parent.mkdir(parents=True)
    shutil.copyfile(app.studio.projects_root / 'book/成品/全书.txt', scratch)
    unrecognized = scratch.with_name('私藏笔记.txt')
    unrecognized.write_text('保留', encoding='utf-8')
    data.cleanup_legacy_snapshot(app.studio.workspace, manifest)
    assert not scratch.exists() and unrecognized.read_text(encoding='utf-8') == '保留'


def test_two_git_clients_sync_deletion_with_external_project_roots(tmp_path):
    from nw.studio.repository import RepositorySync
    from nw.studio.repository_git import GitRepository
    from test_studio_repository_sync import make_environment, git, identity

    remote, checkout, baseline = make_environment(tmp_path)
    def connect(project, disk):
        studio = StudioService(project / 'workspace', config_path=project / 'studio.config.toml', projects_root=disk)
        sync = RepositorySync(studio, project=project, git=GitRepository(project, 'origin', 'master', allow_local=True))
        sync.prepare()
        assert not sync.restore_required, sync.status()
        app = ProductionService(studio, LibraryService(studio.workspace), test_mode=True)
        return sync, app

    writer, author = connect(baseline.project, tmp_path / 'disk-a')
    ident, _ = seed(author, 'shared')
    assert writer.sync_once()['state'] == 'synced'
    checkout2 = tmp_path / 'clone'
    git(tmp_path, 'clone', '--quiet', '--no-hardlinks', str(remote), str(checkout2))
    identity(checkout2)
    reader, recipient = connect(checkout2 / baseline.project.name, tmp_path / 'disk-b')
    assert recipient.db.get(ident)['project_dir'] == 'shared'
    author.trash_novel(ident)
    assert writer.sync_once()['state'] == 'synced'
    pulled = reader.sync_once()
    assert pulled['state'] == 'synced', pulled
    assert git(checkout2, 'rev-parse', 'HEAD') == git(checkout, 'rev-parse', 'HEAD')
    assert recipient.novel_cache()['entries'][0]['id'] == ident
    assert not (recipient.studio.projects_root / 'shared').exists()
    assert (recipient.studio.projects_root / 'test-book/nw.db').is_file()


def test_capture_before_marker_write_recovers_already_matching_deletion(tmp_path):
    from test_studio_repository_sync import make_environment
    _, _, manager = make_environment(tmp_path)
    assert manager.sync_once()['state'] == 'synced'
    app = ProductionService(manager.service, LibraryService(manager.workspace), test_mode=True)
    ident, _ = seed(app, 'delete-before-marker')
    app.trash_novel(ident)
    saved = data.snapshot(manager.workspace, manager.folder)
    assert saved['content_sha256'] != manager.saved['runtime_sha']
    manager.prepare()
    assert not manager.restore_required, manager.status()
    assert manager.saved['runtime_sha'] == saved['content_sha256']
    assert app.novel_cache()['cache_count'] == 1
