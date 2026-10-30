"""PostgreSQL idempotency-record adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from accos.adapters.persistence.models import IdempotencyRecordRow
from accos.kernel.errors import IdempotencyConflictError
from accos.kernel.persistence import IdempotencyRecord

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyIdempotencyStore:
    """Reserve keys atomically inside the caller's existing transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve(self, record: IdempotencyRecord) -> tuple[IdempotencyRecord, bool]:
        """Insert once, returning an equivalent existing record on safe retry."""
        row = IdempotencyRecordRow(
            id=record.id,
            workspace_id=record.workspace_id,
            project_id=record.project_id,
            scope=record.scope,
            key=record.key,
            request_digest=record.request_digest,
            result_reference=record.result_reference,
            expires_at=record.expires_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            existing = await self.get(
                workspace_id=record.workspace_id,
                scope=record.scope,
                key=record.key,
            )
            if existing is None or existing.request_digest != record.request_digest:
                raise IdempotencyConflictError from None
            return existing, False
        return record, True

    async def get(self, *, workspace_id: UUID, scope: str, key: str) -> IdempotencyRecord | None:
        """Read one non-archived record from an explicit workspace."""
        statement = select(IdempotencyRecordRow).where(
            IdempotencyRecordRow.workspace_id == workspace_id,
            IdempotencyRecordRow.scope == scope,
            IdempotencyRecordRow.key == key,
            IdempotencyRecordRow.archived_at.is_(None),
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return None if row is None else _to_record(row)


def _to_record(row: IdempotencyRecordRow) -> IdempotencyRecord:
    return IdempotencyRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        scope=row.scope,
        key=row.key,
        request_digest=row.request_digest,
        result_reference=row.result_reference,
        expires_at=row.expires_at,
    )
