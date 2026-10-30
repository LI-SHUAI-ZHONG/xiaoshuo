"""Celery/Redis event publisher, consumer registration, and in-memory queue fake."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from celery import Celery  # type: ignore[import-untyped]

from accos.kernel.asyncio import selector_loop_factory
from accos.kernel.events import EventEnvelope
from accos.kernel.ids import parse_id

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

CELERY_WORKFLOW_TASK = "accos.workflows.consume"


class CeleryClient(Protocol):
    """Narrow Celery surface required by the outbound adapter."""

    def send_task(
        self,
        name: str,
        args: list[object],
        *,
        task_id: str,
        eta: datetime | None,
    ) -> object: ...


class CeleryApplication(CeleryClient, Protocol):
    """Narrow registration surface required by the Worker adapter."""

    def task(
        self, *args: object, **kwargs: object
    ) -> Callable[[Callable[..., object]], object]: ...


class CeleryEventPublisher:
    """Publish Outbox envelopes to Celery without treating Redis as state."""

    def __init__(self, client: CeleryClient, *, task_name: str = CELERY_WORKFLOW_TASK) -> None:
        self._client = client
        self._task_name = task_name

    async def publish(self, event: EventEnvelope) -> None:
        """Use the event ID as transport identity and preserve scheduled availability."""
        await asyncio.to_thread(
            self._client.send_task,
            self._task_name,
            [serialize_event(event)],
            task_id=str(event.id),
            eta=event.available_at,
        )


class InMemoryTaskQueue:
    """At-least-once queue fake that deliberately retains duplicate deliveries."""

    def __init__(self) -> None:
        self._events: list[EventEnvelope] = []
        self.available = True

    @property
    def deliveries(self) -> tuple[EventEnvelope, ...]:
        """Return all published envelopes in transport order."""
        return tuple(self._events)

    async def publish(self, event: EventEnvelope) -> None:
        """Append a delivery or simulate a temporary broker outage."""
        if not self.available:
            raise ConnectionError("fixture queue unavailable")
        self._events.append(event)

    async def deliver(
        self,
        handler: Callable[[EventEnvelope], Awaitable[object]],
        *,
        index: int = 0,
    ) -> object:
        """Deliver without removing so tests can model redelivery after interruption."""
        return await handler(self._events[index])


def serialize_event(event: EventEnvelope) -> dict[str, object]:
    """Serialize one trusted Outbox envelope into JSON-compatible Celery arguments."""
    return {
        "id": str(event.id),
        "workspace_id": str(event.workspace_id),
        "project_id": None if event.project_id is None else str(event.project_id),
        "aggregate_id": str(event.aggregate_id),
        "event_type": event.event_type,
        "version": event.version,
        "payload": event.payload,
        "occurred_at": event.occurred_at.isoformat(),
        "available_at": None if event.available_at is None else event.available_at.isoformat(),
    }


def deserialize_event(payload: dict[str, object]) -> EventEnvelope:
    """Restore and validate the server-produced queue envelope."""
    project_value = payload.get("project_id")
    raw_payload = payload.get("payload")
    if project_value is not None and not isinstance(project_value, str):
        raise ValueError("queue project identifier is invalid")
    if not isinstance(raw_payload, dict):
        raise ValueError("queue event payload is invalid")
    available_value = payload.get("available_at")
    return EventEnvelope(
        parse_id(_required_string(payload, "id")),
        parse_id(_required_string(payload, "workspace_id")),
        None if project_value is None else parse_id(project_value),
        parse_id(_required_string(payload, "aggregate_id")),
        _required_string(payload, "event_type"),
        _required_int(payload, "version"),
        cast("dict[str, object]", raw_payload),
        datetime.fromisoformat(_required_string(payload, "occurred_at")),
        (
            None
            if available_value is None
            else datetime.fromisoformat(_typed_string(available_value, "available_at"))
        ),
    )


def create_celery_app(
    redis_url: str,
    *,
    timeout_seconds: float = 5.0,
    max_retries: int = 2,
) -> Celery:
    """Build the real Celery application with late acknowledgement and no result backend."""
    if timeout_seconds <= 0 or max_retries < 0:
        raise ValueError("queue resilience values are invalid")
    app = Celery("accos", broker=redis_url, set_as_current=False)
    app.conf.update(
        task_ignore_result=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        broker_connection_timeout=timeout_seconds,
        broker_connection_max_retries=max_retries,
        broker_transport_options={
            "socket_connect_timeout": timeout_seconds,
            "socket_timeout": timeout_seconds,
        },
        task_serializer="json",
        accept_content=("json",),
    )
    return app


def register_celery_consumer(
    app: CeleryApplication,
    handler: Callable[[EventEnvelope], Awaitable[object]],
) -> object:
    """Register the trusted Celery inbound adapter around the shared Worker handler."""

    @app.task(
        name=CELERY_WORKFLOW_TASK,
        shared=False,
        acks_late=True,
        reject_on_worker_lost=True,
        ignore_result=True,
    )
    def consume(payload: dict[str, object]) -> object:
        return asyncio.run(
            _invoke(handler, deserialize_event(payload)), loop_factory=selector_loop_factory
        )

    return consume


async def _invoke(
    handler: Callable[[EventEnvelope], Awaitable[object]], event: EventEnvelope
) -> object:
    return await handler(event)


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return _typed_string(value, key)


def _typed_string(value: object, key: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"queue event {key} is invalid")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"queue event {key} is invalid")
    return value
