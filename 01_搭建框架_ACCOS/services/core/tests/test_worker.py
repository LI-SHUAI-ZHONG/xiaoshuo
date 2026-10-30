from __future__ import annotations

import asyncio
import signal
import threading
from dataclasses import replace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from accos.adapters.persistence import RelayReport
from accos.composition import build_container
from accos.entrypoints.worker import TaskRegistry, WorkerRuntime, _handled_signals, _serve, main
from accos.kernel.errors import ConfigurationError
from accos.kernel.logging import configure_logging

if TYPE_CHECKING:
    from accos.kernel.settings import RuntimeSettings


class ImmediateRuntime:
    def __init__(self) -> None:
        self.saw_unset_event = False

    async def run(self, shutdown_event: asyncio.Event) -> None:
        self.saw_unset_event = not shutdown_event.is_set()
        shutdown_event.set()


class BlockingCeleryWorker:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.stopped = threading.Event()

    def start(self) -> None:
        self.started.set()
        assert self.stopped.wait(timeout=1)

    def stop(self) -> None:
        self.stopped.set()


def test_worker_runtime_starts_empty_and_explicit_task_registries(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    for tasks in (None, TaskRegistry(("fixture-task",))):
        container = build_container(runtime_settings, probes=())
        runtime = WorkerRuntime(container, tasks=tasks)
        shutdown_event = asyncio.Event()
        shutdown_event.set()

        asyncio.run(runtime.run(shutdown_event))

    stderr = capsys.readouterr().err
    assert '"event":"worker_started"' in stderr
    assert '"registered_tasks":0' in stderr
    assert '"registered_tasks":1' in stderr
    assert '"event":"worker_stopping"' in stderr


def test_worker_runtime_runs_relay_and_celery_until_shutdown(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def scenario() -> None:
        shutdown_event = asyncio.Event()
        controller = BlockingCeleryWorker()
        celery_app = MagicMock()
        celery_app.Worker.return_value = controller

        async def publish_one_batch() -> RelayReport:
            while not controller.started.is_set():
                await asyncio.sleep(0)
            shutdown_event.set()
            return RelayReport(1, 1, 0, 12)

        relay = MagicMock()
        relay.run_once = AsyncMock(side_effect=publish_one_batch)
        built = build_container(runtime_settings, probes=())
        container = replace(
            built,
            workflows=replace(built.workflows, relay=relay, celery_app=celery_app),
        )
        runtime = WorkerRuntime(
            container,
            tasks=TaskRegistry(("fixture-task",)),
            relay_interval_seconds=0.001,
        )

        await runtime.run(shutdown_event)

        relay.run_once.assert_awaited_once()
        celery_app.Worker.assert_called_once_with(
            loglevel="INFO",
            pool="solo",
            without_gossip=True,
            without_heartbeat=True,
            without_mingle=True,
        )
        assert controller.started.is_set()
        assert controller.stopped.is_set()

    configure_logging("INFO")
    asyncio.run(scenario())
    stderr = capsys.readouterr().err
    assert '"event":"outbox_relay_batch"' in stderr
    assert '"cursor":12' in stderr


def test_worker_runtime_retries_relay_outage_without_celery(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def scenario() -> None:
        shutdown_event = asyncio.Event()
        attempts = 0

        async def recover_relay() -> RelayReport:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError("fixture relay outage")
            shutdown_event.set()
            return RelayReport(0, 0, 0, None)

        relay = MagicMock()
        relay.run_once = AsyncMock(side_effect=recover_relay)
        built = build_container(runtime_settings, probes=())
        container = replace(built, workflows=replace(built.workflows, relay=relay, celery_app=None))

        await WorkerRuntime(container, relay_interval_seconds=0.001).run(shutdown_event)

        assert relay.run_once.await_count == 2

    configure_logging("INFO")
    asyncio.run(scenario())
    assert '"event":"outbox_relay_failed"' in capsys.readouterr().err


def test_worker_heartbeat_success_repeats_until_shutdown(
    runtime_settings: RuntimeSettings,
) -> None:
    async def scenario() -> None:
        shutdown_event = asyncio.Event()
        attempts = 0

        async def heartbeat() -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 2:
                shutdown_event.set()

        settings = replace(
            runtime_settings,
            observability=replace(
                runtime_settings.observability,
                runtime_heartbeat_seconds=0.001,
            ),
        )
        built = build_container(settings, probes=())
        monitor = MagicMock()
        monitor.heartbeat = AsyncMock(side_effect=heartbeat)
        container = replace(
            built,
            observability=replace(built.observability, monitor=monitor),
        )
        runtime = WorkerRuntime(container)

        await runtime._run_heartbeat(shutdown_event)  # noqa: SLF001

        assert monitor.heartbeat.await_count == 2
        assert (
            'accos_worker_heartbeat{state="active"} 1'
            in container.observability.telemetry.registry.render_prometheus()
        )

    asyncio.run(scenario())


def test_worker_heartbeat_failure_is_diagnostic_and_recovers(
    runtime_settings: RuntimeSettings,
) -> None:
    async def scenario() -> None:
        shutdown_event = asyncio.Event()
        attempts = 0

        async def heartbeat() -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError("fixture heartbeat outage")
            shutdown_event.set()

        settings = replace(
            runtime_settings,
            observability=replace(
                runtime_settings.observability,
                runtime_heartbeat_seconds=0.001,
            ),
        )
        built = build_container(settings, probes=())
        monitor = MagicMock()
        monitor.heartbeat = AsyncMock(side_effect=heartbeat)
        container = replace(
            built,
            observability=replace(built.observability, monitor=monitor),
        )

        with patch("accos.entrypoints.worker.runtime.log_event") as logged:
            await WorkerRuntime(container)._run_heartbeat(shutdown_event)  # noqa: SLF001

        assert monitor.heartbeat.await_count == 2
        logged.assert_called_once()
        assert logged.call_args.args[2] == "worker_heartbeat_failed"
        rendered = container.observability.telemetry.registry.render_prometheus()
        assert 'accos_worker_heartbeat{state="unavailable"} 1' in rendered
        assert 'accos_worker_heartbeat{state="active"} 1' in rendered

    asyncio.run(scenario())


def test_worker_runtime_stops_when_celery_worker_exits(
    runtime_settings: RuntimeSettings,
) -> None:
    async def scenario() -> None:
        shutdown_event = asyncio.Event()
        celery_app = MagicMock()
        celery_app.Worker.return_value.start.return_value = None
        relay = MagicMock()
        relay.run_once = AsyncMock(return_value=RelayReport(0, 0, 0, None))
        built = build_container(runtime_settings, probes=())
        container = replace(
            built,
            workflows=replace(built.workflows, relay=relay, celery_app=celery_app),
        )

        await WorkerRuntime(container, relay_interval_seconds=0.001).run(shutdown_event)

        assert shutdown_event.is_set()
        celery_app.Worker.return_value.start.assert_called_once_with()

    asyncio.run(scenario())


def test_worker_runtime_rejects_invalid_relay_interval(
    runtime_settings: RuntimeSettings,
) -> None:
    with pytest.raises(ValueError, match="relay interval"):
        WorkerRuntime(build_container(runtime_settings, probes=()), relay_interval_seconds=0)


def test_worker_serve_installs_signal_handlers() -> None:
    runtime = ImmediateRuntime()

    with patch("accos.entrypoints.worker.signal.signal") as install:
        asyncio.run(_serve(cast("WorkerRuntime", runtime)))

    assert runtime.saw_unset_event
    installed_signals = {call.args[0] for call in install.call_args_list}
    assert set(_handled_signals()).issubset(installed_signals)
    shutdown_handler = next(
        call.args[1] for call in install.call_args_list if call.args[0] == signal.SIGTERM
    )
    shutdown_handler(signal.SIGTERM, None)


def test_handled_signals_support_platforms_without_sigbreak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert signal.SIGINT in _handled_signals()
    monkeypatch.delattr(signal, "SIGBREAK")

    assert _handled_signals() == (signal.SIGINT, signal.SIGTERM)


def test_worker_main_fails_fast_or_runs_shared_composition(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "accos.entrypoints.worker.load_settings",
        side_effect=ConfigurationError("Missing required environment variables: FIXTURE"),
    ):
        assert main() == 2
    assert "configuration_error" in capsys.readouterr().err

    container = build_container(runtime_settings, probes=())
    serve = AsyncMock()
    with (
        patch("accos.entrypoints.worker.load_settings", return_value=runtime_settings),
        patch("accos.entrypoints.worker.build_container", return_value=container) as build,
        patch("accos.entrypoints.worker._serve", new=serve),
        patch("accos.entrypoints.worker.log_event") as logged,
    ):
        assert main() == 0

    build.assert_called_once_with(runtime_settings)
    serve.assert_awaited_once()
    logged.assert_called_once()
    assert logged.call_args.args[2] == "worker_configuration_loaded"
    assert "fixture-redis-secret" not in repr(logged.call_args.kwargs)

    with (
        patch("accos.entrypoints.worker.load_settings", return_value=runtime_settings),
        patch("accos.entrypoints.worker._serve", side_effect=KeyboardInterrupt),
        patch("accos.entrypoints.worker.log_event") as shutdown_logged,
    ):
        assert main() == 0
    assert shutdown_logged.call_args.args[2] == "worker_shutdown_requested"
