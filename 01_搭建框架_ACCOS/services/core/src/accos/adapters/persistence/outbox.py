"""Transactional Outbox writer, lease repository, relay, and deterministic publisher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import and_, or_, select, update

from accos.adapters.persistence.models import (
    LEASED_STATUS,
    PENDING_STATUS,
    PUBLISHED_STATUS,
    OutboxEventRow,
)
from accos.kernel.events import EventEnvelope
from accos.kernel.ids import new_id

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.clock import Clock
    from accos.kernel.events import EventPublisher


class SqlAlchemyOutboxWriter:
    """Append events using the caller's active SQLAlchemy transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: EventEnvelope) -> int:
        """Stage and flush an event without committing the transaction."""
        row = OutboxEventRow(
            id=event.id,
            workspace_id=event.workspace_id,
            project_id=event.project_id,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            event_version=event.version,
            payload=event.payload,
            occurred_at=event.occurred_at,
            available_at=event.available_at or event.occurred_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row.sequence


@dataclass(frozen=True, slots=True)
class ClaimedEvent:
    """One leased event and the token required to settle it."""

    event: EventEnvelope
    sequence: int
    lease_token: UUID


@dataclass(frozen=True, slots=True)
class RelayReport:
    """Observable result and high-water cursor for one bounded relay pass."""

    claimed: int
    published: int
    failed: int
    cursor: int | None


class OutboxRepository(Protocol):
    """Lease and settlement boundary consumed by the relay."""

    async def claim(self) -> tuple[ClaimedEvent, ...]:
        """Lease one bounded batch."""
        ...

    async def acknowledge(self, claimed: ClaimedEvent) -> bool:
        """Settle a successfully published lease."""
        ...

    async def fail(self, claimed: ClaimedEvent, *, error_code: str = "publish_failed") -> bool:
        """Release a failed lease for retry."""
        ...


class SqlAlchemyOutboxRepository:
    """Claim and settle outbox rows without exposing ORM models."""

    def __init__(
        self,
        sessions: AsyncSessionFactory,
        clock: Clock,
        *,
        batch_size: int = 100,
        lease_seconds: float = 30.0,
        retry_seconds: float = 5.0,
    ) -> None:
        if batch_size < 1 or lease_seconds <= 0 or retry_seconds <= 0:
            raise ValueError("outbox batch and timing values must be positive")
        self._sessions = sessions
        self._clock = clock
        self._batch_size = batch_size
        self._lease = timedelta(seconds=lease_seconds)
        self._retry = timedelta(seconds=retry_seconds)

    async def claim(self) -> tuple[ClaimedEvent, ...]:
        """Lease the oldest eligible rows with PostgreSQL skip-locked semantics."""
        now = self._clock.now()
        token = new_id()
        eligible_status = or_(
            OutboxEventRow.status == PENDING_STATUS,
            and_(
                OutboxEventRow.status == LEASED_STATUS,
                OutboxEventRow.lease_expires_at <= now,
            ),
        )
        statement = (
            select(OutboxEventRow)
            .where(
                OutboxEventRow.published_at.is_(None),
                OutboxEventRow.archived_at.is_(None),
                OutboxEventRow.available_at <= now,
                eligible_status,
            )
            .order_by(OutboxEventRow.sequence)
            .limit(self._batch_size)
            .with_for_update(skip_locked=True)
        )
        async with self._sessions.begin() as session:
            rows = tuple((await session.scalars(statement)).all())
            for row in rows:
                row.status = LEASED_STATUS
                row.lease_token = token
                row.lease_expires_at = now + self._lease
                row.attempt_count += 1
            await session.flush()
            return tuple(_claimed(row, token) for row in rows)

    async def acknowledge(self, claimed: ClaimedEvent) -> bool:
        """Mark a publication complete only when the caller still owns its lease."""
        now = self._clock.now()
        statement = (
            update(OutboxEventRow)
            .where(
                OutboxEventRow.id == claimed.event.id,
                OutboxEventRow.status == LEASED_STATUS,
                OutboxEventRow.lease_token == claimed.lease_token,
            )
            .values(
                status=PUBLISHED_STATUS,
                published_at=now,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=None,
            )
            .returning(OutboxEventRow.id)
        )
        async with self._sessions.begin() as session:
            result = await session.execute(statement)
            settled = result.scalar_one_or_none()
        return settled is not None

    async def fail(self, claimed: ClaimedEvent, *, error_code: str = "publish_failed") -> bool:
        """Release a lease and defer the next attempt using a stable error code."""
        now = self._clock.now()
        statement = (
            update(OutboxEventRow)
            .where(
                OutboxEventRow.id == claimed.event.id,
                OutboxEventRow.status == LEASED_STATUS,
                OutboxEventRow.lease_token == claimed.lease_token,
            )
            .values(
                status=PENDING_STATUS,
                available_at=now + self._retry,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code[:100],
            )
            .returning(OutboxEventRow.id)
        )
        async with self._sessions.begin() as session:
            result = await session.execute(statement)
            settled = result.scalar_one_or_none()
        return settled is not None


class OutboxRelay:
    """Publish only rows claimed through the dedicated outbox repository."""

    def __init__(self, repository: OutboxRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def run_once(self) -> RelayReport:
        """Process one bounded batch and retain failed rows for a later retry."""
        claimed = await self._repository.claim()
        published = 0
        failed = 0
        for item in claimed:
            try:
                await self._publisher.publish(item.event)
            except Exception:  # noqa: BLE001 - transport boundary records a stable failure.
                await self._repository.fail(item)
                failed += 1
            else:
                if await self._repository.acknowledge(item):
                    published += 1
                else:
                    failed += 1
        cursor = max((item.sequence for item in claimed), default=None)
        return RelayReport(len(claimed), published, failed, cursor)


class InMemoryPublisher:
    """Deterministic idempotent publisher for relay contract tests."""

    def __init__(self) -> None:
        self._seen: set[UUID] = set()
        self._events: list[EventEnvelope] = []

    @property
    def visible_events(self) -> tuple[EventEnvelope, ...]:
        """Return visible side effects in first-publication order."""
        return tuple(self._events)

    async def publish(self, event: EventEnvelope) -> None:
        """Deduplicate the visible effect using the durable event ID."""
        if event.id not in self._seen:
            self._seen.add(event.id)
            self._events.append(event)


def _claimed(row: OutboxEventRow, lease_token: UUID) -> ClaimedEvent:
    return ClaimedEvent(
        event=EventEnvelope(
            id=row.id,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            aggregate_id=row.aggregate_id,
            event_type=row.event_type,
            version=row.event_version,
            payload=dict(row.payload),
            occurred_at=row.occurred_at,
            available_at=(row.available_at if row.available_at != row.occurred_at else None),
        ),
        sequence=row.sequence,
        lease_token=lease_token,
    )
