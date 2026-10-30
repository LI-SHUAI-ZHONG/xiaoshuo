"""Background Worker runtime for the durable Outbox and Celery delivery loop."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from accos.kernel.logging import get_logger, log_event

if TYPE_CHECKING:
    from accos.composition import ApplicationContainer


class CeleryWorkerController(Protocol):
    """Blocking Celery worker surface used by the process runtime."""

    def start(self) -> None: ...

    def stop(self) -> None: ...


@dataclass(frozen=True, slots=True)
class TaskRegistry:
    """Names of background tasks registered by the concrete queue adapter."""

    task_names: tuple[str, ...] = ()


class WorkerRuntime:
    """Run the Celery consumer and the only Outbox relay until explicit shutdown."""

    def __init__(
        self,
        container: ApplicationContainer,
        *,
        tasks: TaskRegistry | None = None,
        relay_interval_seconds: float = 0.25,
    ) -> None:
        if relay_interval_seconds <= 0:
            raise ValueError("relay interval must be positive")
        self._container = container
        self._tasks = tasks or TaskRegistry()
        self._relay_interval_seconds = relay_interval_seconds
        self._logger = get_logger("worker")

    async def run(self, shutdown_event: asyncio.Event) -> None:
        """Start shared resources, relay committed events, and consume queue tasks."""
        await self._container.startup()
        log_event(
            self._logger,
            logging.INFO,
            "worker_started",
            registered_tasks=len(self._tasks.task_names),
        )
        relay_task: asyncio.Task[None] | None = None
        heartbeat_task: asyncio.Task[None] | None = None
        retention_task: asyncio.Task[None] | None = None
        model_task: asyncio.Task[None] | None = None
        agent_task: asyncio.Task[None] | None = None
        celery_task: asyncio.Task[None] | None = None
        celery_worker: CeleryWorkerController | None = None
        try:
            if not shutdown_event.is_set():
                relay_task = asyncio.create_task(self._run_relay(shutdown_event))
                heartbeat_task = asyncio.create_task(self._run_heartbeat(shutdown_event))
                retention_task = asyncio.create_task(self._run_retention(shutdown_event))
                model_task = asyncio.create_task(self._run_models(shutdown_event))
                agent_task = asyncio.create_task(self._run_agents(shutdown_event))
                celery_app = self._container.workflows.celery_app
                if celery_app is None:
                    await shutdown_event.wait()
                else:
                    celery_worker = cast(
                        "CeleryWorkerController",
                        celery_app.Worker(
                            loglevel=self._container.settings.optional.log_level,
                            pool="solo",
                            without_gossip=True,
                            without_heartbeat=True,
                            without_mingle=True,
                        ),
                    )
                    celery_task = asyncio.create_task(asyncio.to_thread(celery_worker.start))
                    shutdown_wait = asyncio.create_task(shutdown_event.wait())
                    done, _pending = await asyncio.wait(
                        {celery_task, shutdown_wait}, return_when=asyncio.FIRST_COMPLETED
                    )
                    if celery_task in done:
                        await celery_task
                        shutdown_event.set()
                    else:
                        celery_worker.stop()
                    await shutdown_wait
        finally:
            log_event(self._logger, logging.INFO, "worker_stopping")
            shutdown_event.set()
            if celery_worker is not None and celery_task is not None and not celery_task.done():
                celery_worker.stop()
                await celery_task
            if relay_task is not None:
                await relay_task
            if heartbeat_task is not None:
                await heartbeat_task
            if retention_task is not None:
                await retention_task
            if model_task is not None:
                await model_task
            if agent_task is not None:
                await agent_task
            await self._container.shutdown()

    async def _run_agents(self, shutdown_event: asyncio.Event) -> None:
        while not shutdown_event.is_set():
            try:
                worked = await self._container.agents.jobs.run_next()
            except Exception:
                worked = False
                log_event(self._logger, logging.ERROR, "agent_worker_failed", error_code="agent_worker_failed")
            if not worked:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=1)
                except TimeoutError:
                    continue

    async def _run_models(self, shutdown_event: asyncio.Event) -> None:
        while not shutdown_event.is_set():
            try:
                worked = await self._container.models.runtime.run_next()
            except Exception:
                worked = False
                log_event(self._logger, logging.ERROR, "model_worker_failed", error_code="model_worker_failed")
            if not worked:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=1)
                except TimeoutError:
                    continue

    async def _run_retention(self, shutdown_event: asyncio.Event) -> None:
        while not shutdown_event.is_set():
            try:
                await self._container.assets.orphan_collector.run_once()
            except Exception:  # noqa: BLE001 - maintenance must not kill writing or the worker.
                log_event(
                    self._logger,
                    logging.ERROR,
                    "asset_orphan_collection_failed",
                    error_code="asset_orphan_collection_failed",
                )
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
            except TimeoutError:
                continue

    async def _run_relay(self, shutdown_event: asyncio.Event) -> None:
        while not shutdown_event.is_set():
            try:
                report = await self._container.workflows.relay.run_once()
            except Exception:  # noqa: BLE001 - a dependency outage must not kill the Worker.
                self._container.observability.telemetry.increment(
                    "accos_worker_lease_events_total", outcome="failed"
                )
                log_event(
                    self._logger,
                    logging.ERROR,
                    "outbox_relay_failed",
                    outcome="error",
                    error_code="outbox_relay_failed",
                )
            else:
                if report.claimed:
                    self._container.observability.telemetry.increment(
                        "accos_worker_lease_events_total",
                        float(report.published),
                        outcome="published",
                    )
                    self._container.observability.telemetry.increment(
                        "accos_worker_lease_events_total",
                        float(report.failed),
                        outcome="failed",
                    )
                    log_event(
                        self._logger,
                        logging.WARNING if report.failed else logging.INFO,
                        "outbox_relay_batch",
                        claimed=report.claimed,
                        published=report.published,
                        failed=report.failed,
                        cursor=report.cursor,
                        outcome="error" if report.failed else "success",
                        error_code="outbox_publish_failed" if report.failed else "-",
                    )
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=self._relay_interval_seconds)
            except TimeoutError:
                continue

    async def _run_heartbeat(self, shutdown_event: asyncio.Event) -> None:
        interval = self._container.settings.observability.runtime_heartbeat_seconds
        while not shutdown_event.is_set():
            try:
                await self._container.observability.monitor.heartbeat()
            except Exception:  # noqa: BLE001 - reporting must not stop durable work.
                self._container.observability.telemetry.set_gauge(
                    "accos_worker_heartbeat", 1.0, state="unavailable"
                )
                log_event(
                    self._logger,
                    logging.WARNING,
                    "worker_heartbeat_failed",
                    outcome="error",
                    error_code="heartbeat_store_unavailable",
                )
            else:
                self._container.observability.telemetry.set_gauge(
                    "accos_worker_heartbeat", 1.0, state="active"
                )
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
            except TimeoutError:
                continue
