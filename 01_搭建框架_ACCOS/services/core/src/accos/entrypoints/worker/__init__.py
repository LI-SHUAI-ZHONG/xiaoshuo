"""Background worker inbound adapter."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import TYPE_CHECKING

from accos.composition import CELERY_WORKFLOW_TASK, build_container
from accos.entrypoints.worker.runtime import TaskRegistry, WorkerRuntime
from accos.kernel.asyncio import selector_loop_factory
from accos.kernel.errors import ConfigurationError
from accos.kernel.logging import configure_logging, get_logger, log_event
from accos.kernel.settings import load_settings

if TYPE_CHECKING:
    from types import FrameType

__all__ = ["TaskRegistry", "WorkerRuntime", "main"]


async def _serve(runtime: WorkerRuntime) -> None:
    shutdown_event = asyncio.Event()

    def request_shutdown(_signal_number: int, _frame: FrameType | None) -> None:
        shutdown_event.set()

    for handled_signal in _handled_signals():
        signal.signal(handled_signal, request_shutdown)
    await runtime.run(shutdown_event)


def _handled_signals() -> tuple[signal.Signals, ...]:
    handled = [signal.SIGINT, signal.SIGTERM]
    break_signal = getattr(signal, "SIGBREAK", None)
    if isinstance(break_signal, signal.Signals):
        handled.append(break_signal)
    return tuple(handled)


def main() -> int:
    """Load shared settings and run the durable workflow consumer and relay."""
    try:
        settings = load_settings()
    except ConfigurationError as error:
        sys.stderr.write(f"{error.code.value}: {error.public_message}\n")
        return 2
    configure_logging(
        settings.optional.log_level,
        service="accos-worker",
        environment=settings.optional.environment,
    )
    log_event(
        get_logger("startup"),
        logging.INFO,
        "worker_configuration_loaded",
        settings=settings.safe_summary(),
    )
    runtime = WorkerRuntime(build_container(settings), tasks=TaskRegistry((CELERY_WORKFLOW_TASK,)))
    try:
        asyncio.run(_serve(runtime), loop_factory=selector_loop_factory)
    except KeyboardInterrupt:
        log_event(get_logger("startup"), logging.INFO, "worker_shutdown_requested")
    return 0
