"""In-memory and SQLAlchemy append-only model usage ledgers."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Uuid,
    case,
    func,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import SCHEMA_NAME, Base
from accos.modules.models.public import (
    ModelCallStatus,
    ModelCapability,
    ModelErrorCode,
    UsageRecord,
    UsageTotals,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory


class ModelUsageRecordRow(Base):
    """Append-only model attempt and usage row."""

    __tablename__ = "model_usage_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    workflow_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    task_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attempted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("attempt >= 0", name="ck_model_usage_attempt_non_negative"),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0",
            name="ck_model_usage_tokens_non_negative",
        ),
        Index("ix_model_usage_workspace_task", "workspace_id", "task_run_id", "started_at"),
        Index("ix_model_usage_workflow", "workspace_id", "workflow_run_id", "started_at"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryUsageLedger:
    """Deterministic ledger used by unit tests and isolated fake runtimes."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def totals(self, workspace_id: UUID, task_run_id: UUID) -> UsageTotals:
        billable = [
            item for item in self.records if item.workspace_id == workspace_id and item.attempted
        ]
        task = [item for item in billable if item.task_run_id == task_run_id]
        return UsageTotals(
            sum(item.total_tokens for item in billable),
            len(billable),
            sum(item.total_tokens for item in task),
            len(task),
        )

    async def append(self, record: UsageRecord) -> None:
        self.records.append(record)

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[UsageRecord, ...]:
        return tuple(
            item
            for item in self.records
            if item.workspace_id == workspace_id and item.workflow_run_id == workflow_run_id
        )


class SqlAlchemyUsageLedger:
    """Workspace-scoped persistent usage ledger."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def totals(self, workspace_id: UUID, task_run_id: UUID) -> UsageTotals:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        ModelUsageRecordRow.attempted,
                                        ModelUsageRecordRow.input_tokens
                                        + ModelUsageRecordRow.output_tokens,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                        func.count().filter(ModelUsageRecordRow.attempted),
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        ModelUsageRecordRow.attempted
                                        & (ModelUsageRecordRow.task_run_id == task_run_id),
                                        ModelUsageRecordRow.input_tokens
                                        + ModelUsageRecordRow.output_tokens,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                        func.count().filter(
                            ModelUsageRecordRow.attempted
                            & (ModelUsageRecordRow.task_run_id == task_run_id)
                        ),
                    ).where(ModelUsageRecordRow.workspace_id == workspace_id)
                )
            ).one()
        return UsageTotals(*(int(value) for value in row))

    async def append(self, record: UsageRecord) -> None:
        async with self._sessions.begin() as session:
            session.add(_row(record))

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[UsageRecord, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ModelUsageRecordRow)
                    .where(
                        ModelUsageRecordRow.workspace_id == workspace_id,
                        ModelUsageRecordRow.workflow_run_id == workflow_run_id,
                    )
                    .order_by(ModelUsageRecordRow.started_at, ModelUsageRecordRow.id)
                )
            ).all()
        return tuple(_record(item) for item in rows)


def _row(record: UsageRecord) -> ModelUsageRecordRow:
    return ModelUsageRecordRow(
        id=record.id,
        workspace_id=record.workspace_id,
        project_id=record.project_id,
        workflow_run_id=record.workflow_run_id,
        task_run_id=record.task_run_id,
        actor_id=record.actor_id,
        correlation_id=record.correlation_id,
        idempotency_key=record.idempotency_key,
        capability=record.capability.value,
        provider_id=record.provider_id,
        status=record.status.value,
        error_code=record.error_code.value if record.error_code else None,
        attempted=record.attempted,
        attempt=record.attempt,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


def _record(row: ModelUsageRecordRow) -> UsageRecord:
    return UsageRecord(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.task_run_id,
        row.actor_id,
        row.correlation_id,
        row.idempotency_key,
        ModelCapability(row.capability),
        row.provider_id,
        ModelCallStatus(row.status),
        ModelErrorCode(row.error_code) if row.error_code else None,
        row.attempted,
        row.attempt,
        row.input_tokens,
        row.output_tokens,
        row.started_at,
        row.completed_at,
    )
