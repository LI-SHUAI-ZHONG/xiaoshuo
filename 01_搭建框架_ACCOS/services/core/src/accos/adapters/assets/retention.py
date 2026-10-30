"""Delayed orphan collection cannot delete any registered immutable asset version."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, exists, or_, select
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.assets.persistence import AssetVersionRow, UploadSessionRow
from accos.adapters.persistence.models import SCHEMA_NAME, Base

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.clock import Clock
    from accos.modules.assets.ports import ObjectStorage


class RetentionHoldRow(Base):
    __tablename__ = "asset_retention_holds"
    object_key: Mapped[str] = mapped_column(String(500), primary_key=True)
    owner_reference: Mapped[str] = mapped_column(String(200), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_asset_hold_scope", "workspace_id"), {"schema": SCHEMA_NAME})


class OrphanCollector:
    """One bounded maintenance pass; serializes with finalization/resume on upload rows."""

    def __init__(self, sessions: AsyncSessionFactory, storage: ObjectStorage, clock: Clock) -> None:
        self._sessions, self._storage, self._clock = sessions, storage, clock

    async def run_once(self) -> int:
        now = self._clock.now()
        async with self._sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(UploadSessionRow)
                    .where(
                        UploadSessionRow.status.in_(
                            ["failed", "pending", "object_stored", "compensation_required"]
                        ),
                        UploadSessionRow.updated_at < now - timedelta(days=30),
                        or_(
                            UploadSessionRow.error_code.is_(None),
                            UploadSessionRow.error_code != "orphan_collected",
                        ),
                        ~exists(
                            select(AssetVersionRow.id).where(
                                AssetVersionRow.object_key == UploadSessionRow.object_key
                            )
                        ),
                        ~exists(
                            select(RetentionHoldRow.object_key).where(
                                RetentionHoldRow.object_key == UploadSessionRow.object_key,
                                or_(
                                    RetentionHoldRow.expires_at.is_(None),
                                    RetentionHoldRow.expires_at > now,
                                ),
                            )
                        ),
                    )
                    .order_by(UploadSessionRow.updated_at)
                    .limit(20)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                await self._storage.delete_orphan(row.object_key)
                row.status, row.error_code, row.updated_at = "failed", "orphan_collected", now
            return len(rows)

    async def hold(
        self,
        workspace_id: UUID,
        upload_id: UUID,
        owner_reference: str,
        expires_at: datetime | None = None,
    ) -> None:
        """Internal backup/in-flight port, never an unauthenticated public HTTP command."""
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(UploadSessionRow)
                .where(
                    UploadSessionRow.workspace_id == workspace_id, UploadSessionRow.id == upload_id
                )
                .with_for_update()
            )
            if row is None or row.error_code == "orphan_collected":
                raise ValueError("Upload is unavailable for retention")
            record = await session.get(RetentionHoldRow, (row.object_key, owner_reference))
            if record is None:
                session.add(
                    RetentionHoldRow(
                        object_key=row.object_key,
                        owner_reference=owner_reference,
                        workspace_id=workspace_id,
                        expires_at=expires_at,
                    )
                )
            else:
                record.expires_at = expires_at
