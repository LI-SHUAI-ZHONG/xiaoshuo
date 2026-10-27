"""Framework-neutral transaction, repository, and idempotency contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from datetime import datetime
    from types import TracebackType
    from uuid import UUID

    from accos.kernel.contracts import PageRequest


@dataclass(frozen=True, slots=True)
class Page[EntityT]:
    """A stable offset page that never exposes ORM query objects."""

    items: tuple[EntityT, ...]
    total: int
    request: PageRequest

    def __post_init__(self) -> None:
        if self.total < 0 or self.total < len(self.items):
            raise ValueError("page total must cover all returned items")

    @property
    def next_offset(self) -> int | None:
        """Return the next offset when another page exists."""
        candidate = self.request.offset + len(self.items)
        return candidate if candidate < self.total else None


class Repository[EntityT, IdentifierT](Protocol):
    """Minimum module-owned repository boundary."""

    async def get(self, identifier: IdentifierT, *, workspace_id: UUID) -> EntityT | None:
        """Load one entity from the explicit workspace scope."""
        ...

    async def add(self, entity: EntityT) -> None:
        """Stage a new entity in the current unit of work."""
        ...

    async def list(self, *, workspace_id: UUID, page: PageRequest) -> Page[EntityT]:
        """List entities from one workspace using stable pagination."""
        ...


class UnitOfWork(Protocol):
    """Application-controlled transaction boundary."""

    async def __aenter__(self) -> Self:
        """Open one transaction."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back unfinished work and release resources."""
        ...

    async def commit(self) -> None:
        """Commit explicitly from the application layer."""
        ...

    async def rollback(self) -> None:
        """Roll back explicitly from the application layer."""
        ...


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """ORM-independent representation of one scoped idempotency decision."""

    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    scope: str
    key: str
    request_digest: str
    result_reference: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.scope or not self.key or not self.request_digest or not self.result_reference:
            raise ValueError("idempotency fields must be non-empty")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("idempotency expiry must be timezone-aware")


class IdempotencyStore(Protocol):
    """Port for atomic idempotency-key reservation."""

    async def reserve(self, record: IdempotencyRecord) -> tuple[IdempotencyRecord, bool]:
        """Return the durable record and whether this call created it."""
        ...

    async def get(self, *, workspace_id: UUID, scope: str, key: str) -> IdempotencyRecord | None:
        """Load one scoped record without crossing a workspace boundary."""
        ...
