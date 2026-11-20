"""Exercise local cache ownership and deletion through production services on isolated books."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sqlite3

import pytest

from nw.call_control import execution_lock
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from nw.studio import novel_cache
from nw.studio import catalog
from test_studio_v3_production import wizard


@pytest.fixture
def service(tmp_path):
    studio = StudioService(tmp_path / 'data', config_path=tmp_path / 'no-config.toml',
                           projects_root=tmp_path / 'books')
    return ProductionService(studio, LibraryService(studio.workspace), test_mode=True)


def create(service):
    return service.create(wizard(service))['novel']


@pytest.mark.parametrize('status', ['writing', 'paused', 'done'])
def test_archive_moves_every_project_file_and_purge_keeps_tombstone_and_other_novels(service, status):
    book, other = create(service), create(service)
    root = service.studio.projects_root
    source, neighbor = (root / row['project_dir'] for row in (book, other))
    service.db.update(book['id'], status=status)
    (source / 'exports').mkdir(exist_ok=True)
    (source / 'exports' / '正文.txt').write_text('本书独有的稿件', encoding='utf8')
    (neighbor / 'other.txt').write_text('另一本书', encoding='utf8')
    with service.db.connect() as db:
        db.execute("INSERT INTO reviewed_adoptions VALUES(?, 's', 'hook', 'review', 'yesterday')", (book['id'],))
        db.execute("INSERT INTO reviewed_adoptions VALUES(?, 's', 'hook', 'review', 'yesterday')", (other['id'],))
    result = service.trash_novel(book['id'])
    assert result['cache_count'] == 1 and result['cache_path'] == str(root / '_novel_cache')
    assert not source.exists()
    payload, = Path(result['cache_path']).glob('*/project')
    assert (payload / 'exports' / '正文.txt').read_text(encoding='utf8') == '本书独有的稿件'
    assert novel_cache.project_identity(payload) == book['project_id']
    for method in (service.db.get, service.detail):
        with pytest.raises(FileNotFoundError):
            method(book['id'])
    assert [r['id'] for r in service.list()['novels']] == [other['id']]
    service.db.event(book['id'], 'reviewed', '延迟到达的记录')
    service.library.record_adoption(book['id'], 'late-scene', [next(iter(catalog.option_map()))], 'previous-review')
    with service.db.connect() as db:
        assert [r[0] for r in db.execute('SELECT novel_id FROM reviewed_adoptions')] == [other['id']]
        assert not db.execute('SELECT 1 FROM timeline_events WHERE novel_id=?', (book['id'],)).fetchone()
    restarted = ProductionService(service.studio, service.library, test_mode=True)
    assert restarted.trash_novel(book['id'])['cache_count'] == 1
    assert restarted.clear_novel_cache()['cleared_count'] == 1
    assert restarted.clear_novel_cache()['cache_count'] == 0
    assert not payload.exists() and (neighbor / 'other.txt').read_text(encoding='utf8') == '另一本书'
    assert not service.db.add(book['project_id'], book['project_dir'], '旧书', {'imported': True})


def test_live_job_lock_cannot_be_archived(service):
    book = create(service)
    with service.open_store(book) as store, execution_lock(store, f"novel:{book['job_id']}") as held:
        assert held
        with pytest.raises(ValueError, match='执行'):
            service.trash_novel(book['id'])
    assert service.db.get(book['id'])['title'] == book['title']
    assert service.trash_novel(book['id'])['cache_count'] == 1


def test_reused_project_directory_cannot_steal_another_books_data(service):
    first, other = create(service), create(service)
    root = service.studio.projects_root
    p, q = (root / row['project_dir'] for row in (first, other))
    p.rename(root / 'moved-away')
    q.rename(p)
    with pytest.raises(ValueError, match='身份'):
        service.trash_novel(first['id'])
    assert novel_cache.project_identity(p) == other['project_id']
    assert service.novel_cache()['cache_count'] == 0


def test_crash_after_moving_payload_recovers_metadata_on_restart(service, monkeypatch):
    book = create(service)
    with monkeypatch.context() as patch:
        def fail(db, entry):
            raise sqlite3.OperationalError('injected disk I/O error')
        patch.setattr(novel_cache, '_forget', fail)
        with pytest.raises(sqlite3.OperationalError):
            service.trash_novel(book['id'])
    assert service.db.get(book['id'])
    assert not (service.studio.projects_root / book['project_dir']).exists()
    restarted = ProductionService(service.studio, service.library, test_mode=True)
    assert restarted.novel_cache()['cache_count'] == 1
    with pytest.raises(FileNotFoundError):
        restarted.db.get(book['id'])
    assert restarted.clear_novel_cache()['cleared_count'] == 1


def test_interrupted_partial_purge_only_resumes_this_owned_entry(service, monkeypatch):
    book = create(service)
    result = service.trash_novel(book['id'])
    root = Path(result['cache_path'])
    (root / 'unowned').mkdir()
    (root / 'unowned' / 'preserve').touch()
    def fail(path):
        (path / 'nw.db').unlink()
        raise PermissionError('injected file busy')
    with monkeypatch.context() as patch:
        patch.setattr(novel_cache.shutil, 'rmtree', fail)
        with pytest.raises(PermissionError):
            service.clear_novel_cache()
    assert service.novel_cache()['cache_count'] == 1
    assert service.clear_novel_cache()['cleared_count'] == 1
    assert (root / 'unowned' / 'preserve').is_file()


def test_remote_archive_reuses_the_same_entry_and_rejects_wrong_identity(service):
    book = create(service)
    root = service.studio.projects_root
    args = (root, book['id'], book['project_dir'])
    with pytest.raises(ValueError, match='其他作品'):
        novel_cache.archive_deleted_project(*args, 'wrong', '标题', 'now')
    item = novel_cache.archive_deleted_project(*args, book['project_id'], '标题', 'now')
    assert novel_cache.archive_deleted_project(*args, book['project_id'], '标题', 'later') == item
    assert service.novel_cache()['entries'][0]['id'] == book['id']


def test_synced_deletion_finishes_its_interrupted_local_move(service):
    book = create(service)
    root = service.studio.projects_root
    result = service.trash_novel(book['id'])
    payload, = Path(result['cache_path']).glob('*/project')
    source = root / book['project_dir']
    payload.rename(source)
    assert service.novel_cache()['cache_count'] == 1
    assert not source.exists() and novel_cache.project_identity(payload) == book['project_id']


def test_concurrent_retries_of_trash_and_purge_return_one_owned_entry(service):
    book = create(service)
    with ThreadPoolExecutor(max_workers=3) as workers:
        counts = list(workers.map(lambda _: service.trash_novel(book['id'])['cache_count'], range(3)))
        cleared = list(workers.map(lambda _: service.clear_novel_cache()['cleared_count'], range(3)))
    assert counts == [1, 1, 1] and sorted(cleared) == [0, 0, 1]


def test_cache_root_link_cannot_redirect_archive(service, tmp_path):
    book = create(service)
    root = service.studio.projects_root
    target = tmp_path / 'outside'
    target.mkdir()
    try:
        (root / '_novel_cache').symlink_to(target, target_is_directory=True)
    except OSError as exc:
        if os.name == 'nt' and exc.winerror == 1314:
            import subprocess
            subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(root / '_novel_cache'), str(target)], check=True,
                           capture_output=True)
        else:
            raise
    with pytest.raises(ValueError, match='链接'):
        service.trash_novel(book['id'])
    assert not list(target.iterdir())
    assert (root / book['project_dir'] / 'nw.db').is_file()
