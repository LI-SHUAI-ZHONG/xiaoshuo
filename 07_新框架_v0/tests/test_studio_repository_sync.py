"""Real local Git transports and SQLite snapshots; no GitHub or model requests."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request

import pytest

from nw.studio.api import StudioService
from nw.studio import repository_data as data
from nw.studio.repository import RepositorySync
from nw.studio.repository_git import GitRepository, SyncError
from nw.store import Store


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode('utf-8').strip()


def identity(root: Path) -> None:
    git(root, 'config', 'user.name', 'Isolated Studio Test')
    git(root, 'config', 'user.email', 'studio-test@example.test')


def api_payload(model: str) -> dict:
    return {'model': {'provider': 'openai_compat', 'base_url': 'https://writing.example.test/v1',
                      'model': model, 'api_key_env': 'ISOLATED_WRITING_KEY', 'timeout': 30},
            'params': {'temperature': 0.4}, 'source_driven': True}


def make_environment(tmp_path: Path) -> tuple[Path, Path, RepositorySync]:
    remote, root = tmp_path / 'remote.git', tmp_path / 'author'
    remote.mkdir(); root.mkdir()
    git(remote, 'init', '--bare', '--initial-branch=master')
    git(root, 'init', '--initial-branch=master'); identity(root)
    project = root / '07_新框架_v0'; project.mkdir()
    workspace = project / 'workspace'; workspace.mkdir()
    (root / '.gitignore').write_text('workspace/\n*.db\n', encoding='utf-8')
    (root / 'README.md').write_text('[FAKE] Isolated Git synchronization test\n', encoding='utf-8')
    (root / '00_资料说明.md').write_text(
        '> 最后更新：2026-11-19\n\n| 07 | project | test | 0 | 0 | test |\n\n## 8. 更新规则\n', encoding='utf-8')
    (project / 'studio.repository.toml').write_text(
        '[sync]\nenabled=true\nremote="origin"\nbranch="master"\ninterval_seconds=5\n', encoding='utf-8')
    service = StudioService(workspace, config_path=project / 'studio.config.toml')
    service.save_routing_config(api_payload('isolated-model'))
    with Store(workspace / 'test-book', create=True, test_mode=True) as store:
        store.init_project('[FAKE] Git snapshot test')
        store.add_brief('[FAKE] Original author notes')
    library = workspace / 'library'; library.mkdir()
    with closing(sqlite3.connect(library / 'library.db')) as db:
        db.execute('CREATE TABLE evidence (text TEXT)')
        db.execute('INSERT INTO evidence VALUES (?)', ('[FAKE] Original reference',)); db.commit()
    qa = workspace / '_qa_old' / 'fake-book'; qa.mkdir(parents=True)
    (qa / 'nw.db').write_bytes(b'[FAKE] old QA file, must not be shipped')
    (workspace / 'test-book' / '.env').write_text('isolated placeholder, no credential', encoding='utf-8')
    git(root, 'add', '.'); git(root, 'commit', '-m', 'isolated baseline')
    git(root, 'remote', 'add', 'origin', str(remote)); git(root, 'push', '-u', 'origin', 'master')
    transport = GitRepository(project, 'origin', 'master', allow_local=True)
    manager = RepositorySync(service, project=project, git=transport)
    manager.prepare()
    assert manager.status()['state'] != 'error', manager.status()
    return remote, root, manager


def clone_client(remote: Path, target: Path) -> tuple[Path, RepositorySync]:
    git(remote.parent, 'clone', '--quiet', '--no-hardlinks', str(remote), str(target)); identity(target)
    project = target / '07_新框架_v0'
    service = StudioService(project / 'workspace', config_path=project / 'studio.config.toml')
    transport = GitRepository(project, 'origin', 'master', allow_local=True)
    manager = RepositorySync(service, project=project, git=transport)
    manager.prepare()
    assert not manager.restore_required, manager.status()
    return project, manager


def add_note(manager: RepositorySync, note: str) -> None:
    with Store(manager.workspace / 'test-book', test_mode=True) as store:
        store.add_brief('[FAKE] ' + note)


def notes(manager: RepositorySync) -> list[str]:
    with closing(sqlite3.connect(manager.workspace / 'test-book/nw.db')) as db:
        return [row[0] for row in db.execute('SELECT text FROM briefs ORDER BY rowid')]


def test_actual_library_and_novel_roundtrip_and_no_empty_commits(tmp_path: Path) -> None:
    remote, root, manager = make_environment(tmp_path)
    result = manager.sync_once()
    assert result['state'] == 'synced', result
    head = git(root, 'rev-parse', 'HEAD')
    assert head == git(remote, 'rev-parse', 'master')
    manifest = data.load_manifest(manager.folder)
    names = {entry['path'] for entry in manifest['entries']}
    assert {'library/library.db', 'test-book/nw.db'} <= names
    assert not any('_qa_old' in name or '.env' in name for name in names)
    assert manager.sync_once()['state'] == 'synced'
    assert git(root, 'rev-parse', 'HEAD') == head, 'Unchanged data must not create endless commits'
    project, restored = clone_client(remote, tmp_path / 'other-machine')
    assert notes(restored) == ['[FAKE] Original author notes']
    with closing(sqlite3.connect(project / 'workspace/library/library.db')) as db:
        assert db.execute('SELECT text FROM evidence').fetchone()[0] == '[FAKE] Original reference'


def test_remote_settings_and_actual_novel_changes_are_pulled_and_applied(tmp_path: Path) -> None:
    remote, root, writer = make_environment(tmp_path)
    assert writer.sync_once()['state'] == 'synced'
    project, reader = clone_client(remote, tmp_path / 'reader')
    writer.service.save_routing_config(api_payload('new-shared-model'))
    add_note(writer, 'Remote author revision')
    assert writer.sync_once()['state'] == 'synced'
    result = reader.sync_once()
    assert result['state'] == 'synced', result
    assert git(project, 'rev-parse', 'HEAD') == git(root, 'rev-parse', 'HEAD')
    assert reader.service.get_routing_config()['current']['model'] == 'new-shared-model'
    assert notes(reader)[-1] == '[FAKE] Remote author revision'
    assert list((reader.workspace / '_git_sync/backups').rglob('nw.db'))


def test_divergence_preserves_both_authors_and_does_not_force_push(tmp_path: Path) -> None:
    remote, root, writer = make_environment(tmp_path)
    assert writer.sync_once()['state'] == 'synced'
    project, reader = clone_client(remote, tmp_path / 'reader')
    add_note(writer, 'Remote changed independently')
    assert writer.sync_once()['state'] == 'synced'
    remote_head = git(remote, 'rev-parse', 'master')
    add_note(reader, 'Local changed independently')
    result = reader.sync_once()
    assert result['error_code'] == 'DIVERGED', result
    assert git(remote, 'rev-parse', 'master') == remote_head
    assert notes(reader)[-1] == '[FAKE] Local changed independently'
    assert notes(writer)[-1] == '[FAKE] Remote changed independently'
    assert git(project, 'rev-parse', 'HEAD') != remote_head


def test_unrelated_source_changes_are_never_committed_by_client(tmp_path: Path) -> None:
    remote, root, manager = make_environment(tmp_path)
    before = git(root, 'rev-parse', 'HEAD')
    (root / 'README.md').write_text('[FAKE] unfinished developer edit\n', encoding='utf-8')
    manager.service.save_routing_config(api_payload('local-unsynced-model'))
    result = manager.sync_once()
    assert result['error_code'] == 'LOCAL_CHANGES', result
    assert git(root, 'rev-parse', 'HEAD') == before == git(remote, 'rev-parse', 'master')
    assert not git(root, 'diff', '--cached', '--name-only')


def test_embedded_api_credentials_cannot_enter_a_git_commit(tmp_path: Path) -> None:
    remote, root, manager = make_environment(tmp_path)
    before = git(root, 'rev-parse', 'HEAD')
    config = manager.project / 'studio.config.toml'
    config.write_text(config.read_text(encoding='utf-8').replace('[model]', '[model]\napi_key="[FAKE] forbidden value"'), encoding='utf-8')
    result = manager.sync_once()
    assert result['error_code'] == 'CONFIG_SECRET', result
    assert git(root, 'rev-parse', 'HEAD') == before == git(remote, 'rev-parse', 'master')
    assert not git(root, 'diff', '--cached', '--name-only')


def test_wal_snapshot_includes_committed_rows_and_corruption_never_overwrites(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'; library = workspace / 'library'; library.mkdir(parents=True)
    folder = tmp_path / 'git-runtime'
    with closing(sqlite3.connect(library / 'library.db')) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE evidence (text TEXT)')
        db.execute('INSERT INTO evidence VALUES (?)', ('[FAKE] committed in WAL',)); db.commit()
        manifest = data.snapshot(workspace, folder)
        restored = tmp_path / 'restored'; restored.mkdir()
        data.restore(folder, restored)
        with closing(sqlite3.connect(restored / 'library/library.db')) as copied:
            assert copied.execute('SELECT text FROM evidence').fetchone()[0] == '[FAKE] committed in WAL'
        before = data.digest(restored / 'library/library.db')
        part = folder / manifest['parts'][0]['path']
        part.write_bytes(b'[FAKE] corrupt snapshot')
        with pytest.raises(ValueError, match='分片损坏'):
            data.restore(folder, restored)
        assert data.digest(restored / 'library/library.db') == before


def test_api_save_automatically_pushes_shared_settings_without_model_call(tmp_path: Path, monkeypatch) -> None:
    remote, root, manager = make_environment(tmp_path)
    def factory(service: StudioService) -> RepositorySync:
        return manager
    def no_model_call(*args: object, **kwargs: object) -> None:
        raise AssertionError('Settings/Git synchronization must not call a model')
    monkeypatch.setattr('nw.studio.repository.RepositorySync', factory)
    monkeypatch.setattr('nw.llm.openai_compat.post', no_model_call)
    monkeypatch.setenv('ISOLATED_WRITING_KEY', 'isolated-test-env-value-never-persist')
    from nw.studio.server import create_studio_server
    server = create_studio_server(manager.service, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        request = urllib.request.Request(url + '/api/config/save',
            data=json.dumps(api_payload('automatic-shared-model')).encode(), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:
            assert json.load(response)['saved']
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = manager.status()
            if result['state'] == 'synced':
                shared = git(remote, 'show', 'master:07_新框架_v0/studio.config.toml')
                if 'automatic-shared-model' in shared:
                    break
            time.sleep(.1)
        else:
            pytest.fail(repr(manager.status()))
        assert 'isolated-test-env-value-never-persist' not in shared
        assert 'workspace = "workspace"' in shared
        hostile = urllib.request.Request(url + '/api/repository/sync', data=b'{}',
            headers={'Content-Type':'application/json', 'Origin':'https://unrelated.example.test'})
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(hostile)
        assert refused.value.code == 403
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_interrupted_remote_restore_resumes_without_overwriting_local_history(tmp_path: Path, monkeypatch) -> None:
    remote, root, writer = make_environment(tmp_path)
    assert writer.sync_once()['state'] == 'synced'
    project, reader = clone_client(remote, tmp_path / 'reader')
    add_note(writer, 'New remote note')
    with closing(sqlite3.connect(writer.workspace / 'library/library.db')) as db:
        db.execute('INSERT INTO evidence VALUES (?)', ('[FAKE] New remote reference',)); db.commit()
    assert writer.sync_once()['state'] == 'synced'
    reader.git.integrate(reader.git.fetch())
    apply = data.apply_files
    def interrupted(stage: Path, workspace: Path, entries: list[dict]) -> None:
        apply(stage, workspace, entries[:1])
        raise OSError('isolated simulated interruption')
    with monkeypatch.context() as context:
        context.setattr(data, 'apply_files', interrupted)
        with pytest.raises(OSError, match='simulated interruption'):
            data.restore(reader.folder, reader.workspace)
    reader.prepare()
    assert reader.restore_required is False, reader.status()
    assert notes(reader)[-1] == '[FAKE] New remote note'
    recovery = json.loads((reader.workspace / '_git_sync/restore_pending.json').read_text(encoding='utf-8'))
    assert recovery['complete'] is True


def test_pulled_program_update_requires_restart_before_new_production(tmp_path: Path) -> None:
    remote, root, writer = make_environment(tmp_path)
    assert writer.sync_once()['state'] == 'synced'
    project, reader = clone_client(remote, tmp_path / 'reader')
    add_note(writer, 'New instructions for the updated workflow')
    assert writer.sync_once()['state'] == 'synced'
    source = writer.project / 'src/steps.jsonl'; source.parent.mkdir(parents=True)
    source.write_text('{"instructions":"isolated update"}\n', encoding='utf-8')
    git(root, 'add', '.'); git(root, 'commit', '-m', 'isolated program update')
    git(root, 'push', 'origin', 'master')
    result = reader.sync_once()
    assert result['restart_required'] is True, result
    assert notes(reader) == ['[FAKE] Original author notes']
    with pytest.raises(SyncError, match='重启客户端'):
        with reader.mutation():
            raise AssertionError('Production must not run against newly pulled program code')
    replacement = RepositorySync(reader.service, project=reader.project, git=reader.git)
    replacement.prepare()
    assert not replacement.restore_required, replacement.status()
    assert notes(replacement)[-1] == '[FAKE] New instructions for the updated workflow'


def test_edits_during_push_remain_pending_until_saved_next_cycle(tmp_path: Path, monkeypatch) -> None:
    remote, root, manager = make_environment(tmp_path)
    push = manager.git.push
    def edit_during_push() -> None:
        push()
        with manager.mutation():
            add_note(manager, 'Arrived while pushing')
    with monkeypatch.context() as context:
        context.setattr(manager.git, 'push', edit_during_push)
        result = manager.sync_once()
    assert result['state'] == 'pending', result
    manager._wake.clear()
    assert manager.sync_once()['state'] == 'synced'
    project, restored = clone_client(remote, tmp_path / 'reader')
    assert notes(restored)[-1] == '[FAKE] Arrived while pushing'


def test_studio_cli_uses_shared_default_and_keeps_explicit_override(tmp_path: Path, monkeypatch) -> None:
    from nw.cli import main
    shared = tmp_path / 'studio.config.toml'
    StudioService(tmp_path / 'workspace', config_path=shared).save_routing_config(api_payload('shared-default'))
    monkeypatch.setattr('nw.studio.api.ROOT', tmp_path)
    selected = []
    def launch(**kwargs: object) -> None:
        client = StudioService(tmp_path / 'workspace', config_path=kwargs['config_path'])
        selected.append(client.config_path)
    monkeypatch.setattr('nw.studio.server.run_studio', launch)
    assert main(['studio', '--port', '0']) == 0
    override = tmp_path / 'explicit.toml'
    assert main(['--config', str(override), 'studio', '--port', '0']) == 0
    assert selected == [shared, override]
