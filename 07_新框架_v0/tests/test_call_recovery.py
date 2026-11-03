"""Exercise process death and concurrent resume against the same project directory."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from threading import Event
from time import monotonic, sleep

import pytest

from nw.flow.engine import FlowEngine
from nw.llm.base import GenResult
from nw.llm.fake import FakeProvider
from nw.store import Store
from nw.tasks import run_task
from test_flow import NOTES, seed, yes
from test_tasks import Model, setup_task


def test_process_death_releases_lock_and_keeps_reservation(tmp_path: Path) -> None:
    worker = r"""
import sys
from pathlib import Path
from time import sleep
from nw.config import Config
from nw.store import Store
from nw.task_models import TaskRequest
from nw.tasks import run_task

class NeverReturns:
    name = 'fake'
    def generate(self, messages, **params):
        Path(sys.argv[1], 'entered').touch()
        sleep(60)

with Store(Path(sys.argv[1]), test_mode=True) as store:
    request = TaskRequest('first', store.project().id, 'plan', 'frozen',
                          {'messages':[{'role':'user','content':'设计一个关于代价的故事'}]}, 'budget')
    run_task(store, request, NeverReturns(), Config('fake', '', 'test-model', '', 3, {}, store.directory))
"""
    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store, max_calls=2)
    with subprocess.Popen([sys.executable, '-c', worker, str(tmp_path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            until = monotonic() + 10
            while not (tmp_path / 'entered').exists() and process.poll() is None and monotonic() < until:
                sleep(.025)
            assert (tmp_path / 'entered').exists(), (process.stderr.read() if process.poll() is not None else '')
            provider = Model()
            with Store(tmp_path, test_mode=True) as store:
                assert run_task(store, request, provider, config).status == 'RUNNING'
                retry = replace(request, id='while-active', attempt=2, retry_of=request.id)
                assert run_task(store, retry, provider, config).status == 'RUNNING'
                assert provider.calls == []
        finally:
            process.kill()
            process.communicate(timeout=5)
    with Store(tmp_path, test_mode=True) as store:
        assert run_task(store, request, provider, config).status == 'UNKNOWN'
        retry = replace(request, id='after-death', attempt=2, retry_of=request.id)
        assert run_task(store, retry, provider, config).validation == 'VALID'
        assert len(provider.calls) == 1


def test_legacy_flow_retry_during_active_call_does_not_send(tmp_path: Path) -> None:
    entered, release = Event(), Event()

    class Waiting(FakeProvider):
        def generate(self, messages: list[dict], **params: object) -> GenResult:
            entered.set()
            assert release.wait(10)
            return super().generate(messages, **params)

    with Store(tmp_path, create=True, test_mode=True) as store:
        scene = seed(store)

    def start() -> dict:
        with Store(tmp_path, test_mode=True) as store:
            return FlowEngine(store, Waiting(), 'm', {}).run(scene, yes, notes=NOTES)

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(start)
        try:
            assert entered.wait(5)
            with Store(tmp_path, test_mode=True) as store:
                provider = FakeProvider()
                result = FlowEngine(store, provider, 'm', {}).run(scene, yes, resume=True, retry_failed=True)
                assert result['reason'] == 'Model call already running'
                assert provider.calls == []
        finally:
            release.set()
        assert future.result(timeout=5)['status'] == 'DONE'


def test_fresh_database_does_not_make_empty_upgrade_backups(tmp_path: Path) -> None:
    with Store(tmp_path, create=True):
        assert not list(tmp_path.glob('nw.v*.bak'))


def test_context_limit_does_not_truncate_or_send(tmp_path: Path) -> None:
    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store)
        provider = Model()
        too_long = replace(request, payload={'messages': [{'role': 'user', 'content': '潮' * 4001}]})
        result = run_task(store, too_long, provider, config)
        assert result.reason == 'CONTEXT_TOO_LARGE'
        assert provider.calls == []
        assert store.connection.execute('SELECT COUNT(*) FROM call_reservations').fetchone()[0] == 0


def test_legacy_explicit_retry_marks_old_reservation_unknown(tmp_path: Path) -> None:
    class Interrupted(FakeProvider):
        def generate(self, messages: list[dict], **params: object) -> GenResult:
            raise KeyboardInterrupt()

    with Store(tmp_path, create=True, test_mode=True) as store:
        scene = seed(store)
        with pytest.raises(KeyboardInterrupt):
            FlowEngine(store, Interrupted(), 'm', {}).run(scene, yes, notes=NOTES)
        original = store.list('run')[0].id
    with Store(tmp_path, test_mode=True) as store:
        provider = FakeProvider()
        result = FlowEngine(store, provider, 'm', {}).run(scene, yes, resume=True, retry_failed=True)
        assert result['status'] == 'DONE'
        status = store.connection.execute("SELECT status FROM call_reservations WHERE call_id=?", (original,)).fetchone()
        assert status[0] == 'UNKNOWN'
        assert len(provider.calls) == 2
