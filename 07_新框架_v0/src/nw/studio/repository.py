"""Bind the real client workspace to a GitHub checkout and synchronize it."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import threading
import tomllib
from typing import Any, Iterator
from uuid import uuid4

from nw.studio import repository_data as data
from nw.studio.project_migration import migrate_legacy_projects
from nw.studio.repository_git import GitRepository, SyncError
from nw.studio.runtime import source_digest

PROJECT = Path(__file__).resolve().parents[3]


class RepositorySync:
    def __init__(self, service: Any, *, project: Path = PROJECT,
                 git: GitRepository | None = None) -> None:
        self.service, self.project = service, project.resolve()
        self.loaded_source = source_digest(self.project)
        self._draining = False
        self.workspace = service.workspace.resolve()
        self.projects_root = service.projects_root
        self.folder = self.project / 'studio_data/runtime'
        self.marker = self.workspace / '_git_sync/state.json'
        self.data_lock = threading.RLock()
        self._lock, self._cycle = threading.RLock(), threading.Lock()
        self._wake, self._stop = threading.Event(), threading.Event()
        self._thread: threading.Thread | None = None
        self.production, self.library = None, None
        self.git, self.enabled, self.restore_required = git, False, False
        self.interval = 60
        self._state = {'state': 'disabled', 'message': '此启动配置未启用 GitHub 同步',
                       'error': '', 'error_code': '', 'last_synced_at': '',
                       'local_commit': '', 'remote_commit': '', 'restart_required': False}
        self.saved = json.loads(self.marker.read_text(encoding='utf-8')) if self.marker.is_file() else {}
        settings = self.project / 'studio.repository.toml'
        if (service.config_path != self.project / 'studio.config.toml'
                or self.workspace != self.project / 'workspace' or not settings.is_file()):
            return
        try:
            self.settings = tomllib.loads(settings.read_text(encoding='utf-8'))
            self.enabled = self.settings.get('sync', {}).get('enabled', False) is True
            if not self.enabled:
                return
            cfg = self.settings['sync']
            self.interval = max(5, min(3600, int(cfg.get('interval_seconds', 60))))
            self.git = git or GitRepository(self.project, cfg.get('remote', 'origin'), cfg.get('branch', 'master'))
            self._state.update(state='pending', message='正在准备仓库资料',
                               last_synced_at=self.saved.get('last_synced_at', ''))
        except (OSError, ValueError, KeyError) as exc:
            self._fail(exc)

    def _set(self, state: str, message: str, **extra: Any) -> None:
        with self._lock:
            self._state.update(state=state, message=message, error='', error_code='', **extra)

    def _fail(self, exc: Exception) -> None:
        with self._lock:
            self._state.update(state='error', message='GitHub 同步尚未完成',
                               error=str(exc), error_code=getattr(exc, 'code', 'DATA'))

    def status(self) -> dict:
        with self._lock:
            result = dict(self._state)
        result.update(enabled=self.enabled, interval_seconds=self.interval,
                      repository=str(self.git.root) if self.git else '',
                      github_url=self.git.url if self.git else '', branch=self.git.branch if self.git else '',
                      config_path=str(self.service.config_path),
                      original_materials=str(self.git.root / '02_原版资料') if self.git else '',
                      runtime_materials=str(self.workspace / 'materials'),
                      runtime_workspace=str(self.workspace), novel_storage_path=str(self.projects_root),
                      git_runtime_snapshot=str(self.folder),
                      runtime_snapshot=self.saved.get('runtime_sha', ''),
                      materials_snapshot=self.saved.get('materials_sha', ''))
        return result

    def _save_marker(self) -> None:
        data.atomic_json(self.marker, self.saved)

    def _materials(self) -> None:
        relative = self.settings.get('data', {}).get('materials_baseline', '')
        if not relative and self.git and self.git.local_transport:
            return  # Only injected, isolated local Git integration tests.
        baseline = data.inside(self.project, relative)
        tool_path = self.project / 'tools/materials_baseline.py'
        spec = importlib.util.spec_from_file_location('_studio_material_restore', tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = module.verify(baseline)
        signature = manifest['archive']['sha256']
        existing = all((self.workspace / 'materials' / name).is_file()
                       for name in ('catalog.db', 'adjudication.db'))
        if not existing or (self.saved.get('materials_sha') and self.saved['materials_sha'] != signature):
            stage = self.workspace / '_git_sync' / 'material-restore' / uuid4().hex
            module.restore(baseline, stage)
            data.apply_files(stage, self.workspace, manifest['entries'])
            self.service._desk = None
        else:
            from nw.materials.adjudication import adjudication_status
            from nw.materials.source_set import selection_status
            if adjudication_status(self.workspace)['status'] != 'current' or selection_status(self.workspace) is None:
                raise SyncError('MATERIALS', '本地资料缓存与仓库版本不一致，已暂停写入；原数据已保留')
        self.saved['materials_sha'] = signature

    def prepare(self) -> None:
        migrate_legacy_projects(self.workspace, self.projects_root)
        if not self.enabled or self.git is None:
            return
        try:
            with self.data_lock:
                self._materials()
                stored = data.load_manifest(self.folder)
                if stored:
                    if (self.workspace / '_git_sync/snapshot-cache').is_dir():
                        data.verify_parts(self.folder, stored)
                        data.cleanup_legacy_snapshot(self.workspace, stored)
                    files = data.runtime_files(self.workspace, self.projects_root)
                    previous = self.saved.get('runtime_sha')
                    recovery = self.workspace / '_git_sync/restore_pending.json'
                    interrupted = json.loads(recovery.read_text(encoding='utf-8')) if recovery.is_file() else {}
                    resuming = (not interrupted.get('complete', True)
                                and interrupted.get('content_sha256') == stored['content_sha256'])
                    if not files or resuming:
                        data.restore(self.folder, self.workspace, self.projects_root)
                    elif previous and previous != stored['content_sha256']:
                        local = data.snapshot(self.workspace, self.folder, projects_root=self.projects_root, persist=False)
                        if local['content_sha256'] == previous:
                            data.restore(self.folder, self.workspace, self.projects_root)
                        elif local['content_sha256'] != stored['content_sha256']:
                            raise SyncError('LOCAL_DATA_CONFLICT', 'Git 与本机作品资料都已改变，已保留双方版本；请先处理资料冲突')
                    self.saved['runtime_sha'] = stored['content_sha256']
                self._save_marker()
                self.restore_required = False
                self._set('pending', '仓库资料已就绪，等待与 GitHub 同步')
        except Exception as exc:
            self.restore_required = True
            self._fail(exc)

    def attach(self, production: Any, library: Any) -> None:
        self.production, self.library = production, library

    def _idle(self) -> bool:
        if self.production is not None:
            with self.production._lock:
                if any(worker.is_alive() for worker in self.production._workers.values()):
                    return False
        if self.library is not None:
            with self.library._task_lock:
                if any(worker.is_alive() for worker in self.library._tasks.values()):
                    return False
        return True

    def check_running_source(self) -> bool:
        current = source_digest(self.project)
        with self._lock:
            if current != self.loaded_source:
                self._state.update(restart_required=True, message='仓库程序已更新，请从桌面快捷方式重新打开客户端')
            return self._state['restart_required']

    def release_for_reload(self, body: dict) -> None:
        if not self._cycle.acquire(blocking=False):
            raise SyncError('BUSY', 'GitHub 正在同步，请在同步完成后重新打开客户端。')
        try:
            with self.data_lock:
                if not self._idle():
                    raise SyncError('BUSY', '制作或拆解正在运行，请在任务完成后重新打开客户端。')
                if (not self.check_running_source() or body.get('loaded') != self.loaded_source
                        or body.get('target') != source_digest(self.project)):
                    raise SyncError('VERSION', '请求的后台版本与本仓库不一致，请重新打开快捷方式。')
                self._draining = True
                self._stop.set()
                self._wake.set()
        finally:
            self._cycle.release()

    @contextmanager
    def mutation(self) -> Iterator[None]:
        with self.data_lock:
            if self._draining or self.check_running_source() or (self.enabled and self.restore_required):
                raise SyncError('RESTART', '仓库资料尚未就绪或程序已更新，请查看 GitHub 同步状态并重启客户端')
            try:
                yield
            finally:
                if self.enabled:
                    self._wake.set()

    def trigger(self) -> dict:
        if self.enabled:
            self._wake.set()
        return self.status()

    def _capture(self) -> None:
        self.git.check_workspace()
        current = data.snapshot(self.workspace, self.folder, projects_root=self.projects_root)
        self.git.commit_data()
        self.saved['runtime_sha'] = current['content_sha256']
        self._save_marker()

    def sync_once(self) -> dict:
        if not self.enabled or self.git is None or not self._cycle.acquire(blocking=False):
            return self.status()
        try:
            if self._draining or self.check_running_source():
                return self.status()
            with self.git.exclusive(self.workspace):
                if self.restore_required:
                    self.prepare()
                    if self.restore_required:
                        return self.status()
                with self.data_lock:
                    if not self._idle():
                        self._set('pending', '正在制作或拆解，完成后自动同步')
                        return self.status()
                    self._set('syncing', '正在保存本机配置与作品资料')
                    self._capture()
                self._set('syncing', '正在检查 GitHub 更新')
                remote = self.git.fetch()
                with self.data_lock:
                    if self.check_running_source():
                        return self.status()
                    if not self._idle():
                        self._set('pending', '正在制作或拆解，完成后自动同步')
                        return self.status()
                    self._capture()  # Also preserves edits made during the network request.
                    self._wake.clear()
                    changed = self.git.integrate(remote)
                    if changed:
                        self.restore_required = True
                        if self.check_running_source():
                            self._set('pending', '已取得 GitHub 新版，请重新打开客户端以加载程序和配套资料',
                                      local_commit=remote, remote_commit=remote)
                            return self.status()
                        self._materials()
                        stored = data.restore(self.folder, self.workspace, self.projects_root)
                        if stored:
                            self.saved['runtime_sha'] = stored['content_sha256']
                        self.restore_required = False
                        self._save_marker()
                self._set('syncing', '正在推送到 GitHub')
                self.git.push()
                head = self.git.run('rev-parse', 'HEAD')
                now = datetime.now(timezone.utc).isoformat()
                self.saved['last_synced_at'] = now
                self._save_marker()
                pending = self._wake.is_set()
                self._set('pending' if pending else 'synced',
                          '上一版已同步，本机还有更新等待保存' if pending else '已与 GitHub 同步',
                          local_commit=head, remote_commit=head,
                          last_synced_at=now)
        except Exception as exc:
            self._fail(exc)
        finally:
            self._cycle.release()
        return self.status()

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        def loop() -> None:
            while not self._stop.is_set():
                self._wake.wait(self.interval)
                self._wake.clear()
                if self._stop.wait(2):
                    break
                self.sync_once()
        self._thread = threading.Thread(target=loop, name='studio-github-sync', daemon=True)
        self._thread.start()
        self._wake.set()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
