"""Versioned event and publisher contracts used by the transactional outbox."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Framework-neutral event persisted and later published by the relay."""

    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    aggregate_id: UUID
    event_type: str
    version: int
    payload: dict[str, object]
    occurred_at: datetime
    available_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.event_type or self.event_type.strip() != self.event_type:
            raise ValueError("event type must be non-empty and trimmed")
        if self.version < 1:
            raise ValueError("event version must be positive")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("event timestamp must be timezone-aware")
        if self.available_at is not None and (
            self.available_at.tzinfo is None or self.available_at.utcoffset() is None
        ):
            raise ValueError("event availability timestamp must be timezone-aware")


class EventPublisher(Protocol):
    """Transport-neutral publisher used only by the outbox relay."""

    async def publish(self, event: EventEnvelope) -> None:
        """Publish at least once; consumers must deduplicate by event ID."""
        ...


class OutboxWriter(Protocol):
    """Port for staging an event in the caller's current transaction."""

    async def append(self, event: EventEnvelope) -> int:
        """Persist an event and return its monotonic relay sequence."""
        ...
