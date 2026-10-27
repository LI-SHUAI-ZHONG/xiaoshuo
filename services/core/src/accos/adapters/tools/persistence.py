"""In-memory and SQLAlchemy append-only tool call ledgers."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.

from sqlalchemy import DateTime, Index, String, Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import SCHEMA_NAME, Base
from accos.modules.tools.public import (
    ToolCallRecord,
    ToolCallStatus,
    ToolErrorCode,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory


class ToolCallRecordRow(Base):
    """Append-only payload-free tool execution evidence."""

    __tablename__ = "tool_call_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    workflow_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    task_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(150), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_tool_calls_workflow", "workspace_id", "workflow_run_id", "started_at"),
        Index("ix_tool_calls_task", "workspace_id", "task_run_id", "started_at"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryToolCallLedger:
    """Deterministic tool ledger for isolated fake execution."""

    def __init__(self) -> None:
        self.records: list[ToolCallRecord] = []

    async def append(self, record: ToolCallRecord) -> None:
        self.records.append(record)

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[ToolCallRecord, ...]:
        return tuple(
            item
            for item in self.records
            if item.workspace_id == workspace_id and item.workflow_run_id == workflow_run_id
        )


class SqlAlchemyToolCallLedger:
    """Workspace-scoped persistent tool call audit ledger."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def append(self, record: ToolCallRecord) -> None:
        async with self._sessions.begin() as session:
            session.add(_row(record))

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[ToolCallRecord, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ToolCallRecordRow)
                    .where(
                        ToolCallRecordRow.workspace_id == workspace_id,
                        ToolCallRecordRow.workflow_run_id == workflow_run_id,
                    )
                    .order_by(ToolCallRecordRow.started_at, ToolCallRecordRow.id)
                )
            ).all()
        return tuple(_record(item) for item in rows)


def _row(record: ToolCallRecord) -> ToolCallRecordRow:
    return ToolCallRecordRow(
        id=record.id,
        workspace_id=record.workspace_id,
        project_id=record.project_id,
        workflow_run_id=record.workflow_run_id,
        task_run_id=record.task_run_id,
        actor_id=record.actor_id,
        correlation_id=record.correlation_id,
        idempotency_key=record.idempotency_key,
        tool_id=record.tool_id,
        tool_version=record.tool_version,
        status=record.status.value,
        error_code=record.error_code.value if record.error_code else None,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


def _record(row: ToolCallRecordRow) -> ToolCallRecord:
    return ToolCallRecord(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.task_run_id,
        row.actor_id,
        row.correlation_id,
        row.idempotency_key,
        row.tool_id,
        row.tool_version,
        ToolCallStatus(row.status),
        ToolErrorCode(row.error_code) if row.error_code else None,
        row.started_at,
        row.completed_at,
    )
