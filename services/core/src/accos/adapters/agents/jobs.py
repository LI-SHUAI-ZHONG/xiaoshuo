"""Agent-owned queued requests; crashed executions require an explicit new operation."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    literal,
    select,
    tuple_,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.database import AsyncSessionFactory
from accos.adapters.persistence.models import Base, JSON_TYPE, SCHEMA_NAME
from accos.kernel.errors import IdempotencyConflictError, InvalidRequestError, ResourceNotFoundError
from accos.modules.agents.jobs import AgentJob, AgentJobPage


class AgentJobRow(Base):
    __tablename__ = "agent_execution_jobs"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    headers: Mapped[dict[str, str]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "project_id", "actor_id", "operation_key", name="uq_agent_job_operation"
        ),
        ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA_NAME}.projects.id"], name="fk_agent_job_project"
        ),
        Index("ix_agent_job_queue", "status", "lease_until", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class SqlAgentJobStore:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self.sessions = sessions

    async def create(
        self, job: AgentJob, key: str, digest: str, headers: dict[str, str]
    ) -> AgentJob:
        from sqlalchemy.dialects.postgresql import insert

        async with self.sessions.begin() as session:
            await session.execute(
                insert(AgentJobRow)
                .values(
                    id=job.id,
                    workspace_id=job.workspace_id,
                    project_id=job.project_id,
                    actor_id=job.actor_id,
                    operation_key=key,
                    digest=digest,
                    status=job.status,
                    data=job.model_dump(mode="json"),
                    headers=headers,
                    created_at=job.created_at,
                )
                .on_conflict_do_nothing(constraint="uq_agent_job_operation")
            )
            row = await session.scalar(
                select(AgentJobRow).where(
                    AgentJobRow.workspace_id == job.workspace_id,
                    AgentJobRow.project_id == job.project_id,
                    AgentJobRow.actor_id == job.actor_id,
                    AgentJobRow.operation_key == key,
                )
            )
            if row is None:
                raise ResourceNotFoundError
            if row.digest != digest:
                raise IdempotencyConflictError
            return AgentJob.model_validate(row.data)

    async def claim(self, now: datetime) -> tuple[AgentJob, dict[str, str]] | None:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(AgentJobRow)
                .where(AgentJobRow.status == "queued")
                .order_by(AgentJobRow.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if row is None:
                return None
            row.status, row.lease_until = "running", now + timedelta(seconds=700)
            row.data = {**row.data, "status": "running", "updated_at": now.isoformat()}
            return AgentJob.model_validate(row.data), row.headers

    async def finish(self, job: AgentJob) -> AgentJob:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(AgentJobRow).where(AgentJobRow.id == job.id).with_for_update()
            )
            if row is None:
                raise ResourceNotFoundError
            if row.status == "running":
                row.status, row.data, row.lease_until = (
                    job.status,
                    job.model_dump(mode="json"),
                    None,
                )
            return AgentJob.model_validate(row.data)

    async def get(self, workspace: UUID, project: UUID, identifier: UUID) -> AgentJob:
        async with self.sessions() as session:
            row = await session.scalar(
                select(AgentJobRow).where(
                    AgentJobRow.id == identifier,
                    AgentJobRow.workspace_id == workspace,
                    AgentJobRow.project_id == project,
                )
            )
            if row is None:
                raise ResourceNotFoundError
            return AgentJob.model_validate(row.data)

    async def recover(self, now: datetime) -> None:
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(AgentJobRow)
                    .where(AgentJobRow.status == "running", AgentJobRow.lease_until < now)
                    .with_for_update(skip_locked=True)
                    .limit(100)
                )
            ).all()
            for row in rows:
                row.status = "unknown"
                row.data = {
                    **row.data,
                    "status": "unknown",
                    "error_code": "WORKER_INTERRUPTED",
                    "updated_at": now.isoformat(),
                }

    async def list(
        self, workspace: UUID, project: UUID, cursor: str | None, limit: int
    ) -> AgentJobPage:
        query = select(AgentJobRow).where(
            AgentJobRow.workspace_id == workspace, AgentJobRow.project_id == project
        )
        if cursor:
            try:
                stamp, identifier = cursor.rsplit("|", 1)
                query = query.where(
                    tuple_(AgentJobRow.created_at, AgentJobRow.id)
                    < tuple_(literal(datetime.fromisoformat(stamp)), literal(UUID(identifier)))
                )
            except ValueError:
                raise InvalidRequestError("Invalid agent history cursor.") from None
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    query.order_by(AgentJobRow.created_at.desc(), AgentJobRow.id.desc()).limit(
                        limit + 1
                    )
                )
            ).all()
        page = rows[:limit]
        return AgentJobPage(
            items=tuple(AgentJob.model_validate(row.data) for row in page),
            next_cursor=f"{page[-1].created_at.isoformat()}|{page[-1].id}"
            if len(rows) > limit
            else None,
        )
