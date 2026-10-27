"""In-memory and SQLAlchemy persistence for Agent runs and replay snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.idempotency import SqlAlchemyIdempotencyStore
from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import IdempotencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.persistence import IdempotencyRecord
from accos.modules.agents.domain import (
    AgentBudget,
    AgentContextSnapshot,
    AgentDescriptor,
    AgentErrorCode,
    AgentProposal,
    AgentResultKind,
    AgentRun,
    AgentRunEvent,
    AgentRunStatus,
    AgentRuntimeError,
    PromptMetadataReference,
    ProtectedOperation,
    RawAgentResult,
    RoleDescriptorVersion,
    RoleToolGrant,
    RoleVersionStatus,
    WorkflowPlanProposal,
    WorkflowSelection,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.modules.agents.domain import AgentResult


class AgentContextSnapshotRow(Base):
    """Immutable replay evidence with no prompt or input content."""

    __tablename__ = "agent_context_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_agent_context_project"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(30), nullable=False)
    model_policy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_policy_version: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt_metadata_id: Mapped[str] = mapped_column(String(150), nullable=False)
    prompt_metadata_version: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt_metadata_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_versions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    permission_snapshot: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    memory_context_package_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("memory_context_packages.id", name="fk_agent_context_memory_package"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_agent_context_scope", "workspace_id", "project_id", "agent_id"),
        {"schema": SCHEMA_NAME},
    )


class AgentRunRow(Base):
    """Mutable Agent aggregate with one immutable usage/result settlement."""

    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_agent_runs_project"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(30), nullable=False)
    context_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_context_snapshots.id", name="fk_agent_runs_context"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    task_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_agent_runs_workflow"),
        nullable=True,
    )
    result_kind: Mapped[str | None] = mapped_column(String(40), nullable=True)
    result_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    workflow_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    workflow_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protected_operations: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    model_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_agent_runs_idempotency"),
        CheckConstraint("attempt > 0", name="ck_agent_runs_attempt_positive"),
        CheckConstraint(
            "model_calls >= 0 AND tool_calls >= 0 AND tokens >= 0",
            name="ck_agent_runs_usage_non_negative",
        ),
        CheckConstraint("event_sequence >= 0", name="ck_agent_runs_event_sequence_valid"),
        CheckConstraint("version > 0", name="ck_agent_runs_version_positive"),
        CheckConstraint(
            "status IN ('running', 'waiting_approval', 'succeeded', 'failed', "
            "'rejected', 'budget_exhausted', 'limit_exceeded')",
            name="ck_agent_runs_status_valid",
        ),
        Index("ix_agent_runs_scope_status", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class AgentRunEventRow(Base):
    """Append-only Agent state event."""

    __tablename__ = "agent_run_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    agent_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_runs.id", name="fk_agent_events_run"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("agent_run_id", "sequence", name="uq_agent_events_sequence"),
        CheckConstraint("sequence > 0", name="ck_agent_events_sequence_positive"),
        CheckConstraint("event_version > 0", name="ck_agent_events_version_positive"),
        Index("ix_agent_events_scope_cursor", "workspace_id", "agent_run_id", "sequence"),
        {"schema": SCHEMA_NAME},
    )


class AgentRoleVersionRow(Base):
    """Workspace-owned role descriptor version; published payloads are immutable."""

    __tablename__ = "agent_role_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role_key: Mapped[str] = mapped_column(String(100), nullable=False)
    role_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    descriptor: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "role_key", "role_version", name="uq_agent_role_version"),
        CheckConstraint("role_version > 0", name="ck_agent_role_version_positive"),
        CheckConstraint(
            "status IN ('draft','published','disabled','archived')",
            name="ck_agent_role_status_valid",
        ),
        Index("ix_agent_roles_scope_status", "workspace_id", "status", "role_key"),
        {"schema": SCHEMA_NAME},
    )


class AgentRoleToolGrantRow(Base):
    """Revocable tool grant attached to one exact role version."""

    __tablename__ = "agent_role_tool_grants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_role_versions.id", name="fk_agent_role_grant_role"),
        nullable=False,
    )
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_version: Mapped[str] = mapped_column(String(30), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("role_version_id", "tool_id", name="uq_agent_role_tool_grant"),
        Index("ix_agent_role_grants_scope", "workspace_id", "role_version_id", "active"),
        {"schema": SCHEMA_NAME},
    )


class SqlAlchemyRoleRepository:
    """Persist exact role versions and fail closed after grant revocation."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save_role(self, role: RoleDescriptorVersion) -> RoleDescriptorVersion:
        async with self._sessions.begin() as session:
            existing = await session.scalar(
                select(AgentRoleVersionRow).where(
                    AgentRoleVersionRow.workspace_id == role.workspace_id,
                    AgentRoleVersionRow.role_key == role.role_key,
                    AgentRoleVersionRow.role_version == role.role_version,
                )
            )
            if existing is not None:
                if existing.checksum != role.checksum:
                    raise InvalidStateError("Role version is immutable after first persistence.")
                return _role(existing)
            row = AgentRoleVersionRow(
                id=role.id,
                workspace_id=role.workspace_id,
                role_key=role.role_key,
                role_version=role.role_version,
                status=role.status.value,
                descriptor=_descriptor_payload(role.descriptor),
                checksum=role.checksum,
                created_by=role.created_by,
                created_at=role.created_at,
            )
            session.add(row)
            await session.flush()
            return _role(row)

    async def get_role(
        self, workspace_id: UUID, role_key: str, role_version: int
    ) -> RoleDescriptorVersion | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AgentRoleVersionRow).where(
                    AgentRoleVersionRow.workspace_id == workspace_id,
                    AgentRoleVersionRow.role_key == role_key,
                    AgentRoleVersionRow.role_version == role_version,
                )
            )
            return _role(row) if row is not None else None

    async def list_roles(self, workspace_id: UUID) -> tuple[RoleDescriptorVersion, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AgentRoleVersionRow)
                    .where(AgentRoleVersionRow.workspace_id == workspace_id)
                    .order_by(AgentRoleVersionRow.role_key, AgentRoleVersionRow.role_version.desc())
                )
            ).all()
            return tuple(_role(row) for row in rows)

    async def set_role_status(
        self, workspace_id: UUID, role_id: UUID, status: str
    ) -> RoleDescriptorVersion:
        target = RoleVersionStatus(status)
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(AgentRoleVersionRow)
                .where(
                    AgentRoleVersionRow.workspace_id == workspace_id,
                    AgentRoleVersionRow.id == role_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if RoleVersionStatus(row.status) is RoleVersionStatus.ARCHIVED:
                raise InvalidStateError("Archived role versions cannot be reactivated.")
            row.status = target.value
            return _role(row)

    async def save_grant(self, grant: RoleToolGrant) -> RoleToolGrant:
        async with self._sessions.begin() as session:
            role = await session.scalar(
                select(AgentRoleVersionRow).where(
                    AgentRoleVersionRow.id == grant.role_version_id,
                    AgentRoleVersionRow.workspace_id == grant.workspace_id,
                )
            )
            if role is None:
                raise ScopeViolationError
            if role.status != RoleVersionStatus.PUBLISHED.value:
                raise InvalidStateError("Tool grants require a published role version.")
            row = AgentRoleToolGrantRow(
                id=grant.id,
                workspace_id=grant.workspace_id,
                role_version_id=grant.role_version_id,
                tool_id=grant.tool_id,
                tool_version=grant.tool_version,
                permissions=list(grant.permissions),
                active=grant.active,
                created_at=grant.created_at,
            )
            session.add(row)
            await session.flush()
            return _grant(row)

    async def list_grants(
        self, workspace_id: UUID, role_version_id: UUID
    ) -> tuple[RoleToolGrant, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AgentRoleToolGrantRow)
                    .where(
                        AgentRoleToolGrantRow.workspace_id == workspace_id,
                        AgentRoleToolGrantRow.role_version_id == role_version_id,
                    )
                    .order_by(AgentRoleToolGrantRow.tool_id)
                )
            ).all()
            return tuple(_grant(row) for row in rows)

    async def revoke_grant(
        self, workspace_id: UUID, grant_id: UUID
    ) -> RoleToolGrant:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(AgentRoleToolGrantRow)
                .where(
                    AgentRoleToolGrantRow.workspace_id == workspace_id,
                    AgentRoleToolGrantRow.id == grant_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            row.active = False
            return _grant(row)


class InMemoryAgentRepository:
    """Deterministic repository used by unit and boundary tests."""

    def __init__(self) -> None:
        self.runs: dict[UUID, AgentRun] = {}
        self.snapshots: dict[UUID, AgentContextSnapshot] = {}
        self.events: list[AgentRunEvent] = []
        self._idempotency: dict[tuple[UUID, str], tuple[str, UUID]] = {}

    async def begin(
        self,
        run: AgentRun,
        snapshot: AgentContextSnapshot,
        *,
        request_digest: str,
    ) -> tuple[AgentRun, bool]:
        key = (run.workspace_id, run.idempotency_key)
        existing = self._idempotency.get(key)
        if existing is not None:
            if existing[0] != request_digest:
                raise IdempotencyConflictError
            return self.runs[existing[1]], False
        self._idempotency[key] = (request_digest, run.id)
        self.snapshots[snapshot.id] = snapshot
        self.runs[run.id] = run
        self._append(run, "agents.run-started", {"schema": "agent-run-started.v1"})
        return self.runs[run.id], True

    async def complete(self, run_id: UUID, result: AgentResult, raw: RawAgentResult) -> AgentRun:
        run = self._require(run_id)
        if run.status is not AgentRunStatus.RUNNING:
            return run
        completed = _completed_run(run, result, raw, run.updated_at)
        self.runs[run_id] = completed
        self._append(
            completed,
            "agents.run-succeeded",
            {"schema": "agent-run-succeeded.v1", "result_kind": result.kind.value},
        )
        return self.runs[run_id]

    async def fail(
        self, run_id: UUID, status: AgentRunStatus, error: AgentRuntimeError
    ) -> AgentRun:
        run = self._require(run_id)
        if run.status is not AgentRunStatus.RUNNING:
            return run
        failed = replace(run, status=status, error_code=error.code)
        self.runs[run_id] = failed
        self._append(
            failed,
            "agents.run-failed",
            {"schema": "agent-run-failed.v1", "error_code": error.code.value},
        )
        return self.runs[run_id]

    async def attach_workflow(
        self, workspace_id: UUID, run_id: UUID, workflow_run_id: UUID, *, waiting: bool
    ) -> AgentRun:
        run = self._scoped(workspace_id, run_id)
        if run.workflow_run_id not in {None, workflow_run_id}:
            raise InvalidStateError("Agent run is already attached to another Workflow.")
        if run.workflow_run_id == workflow_run_id:
            return run
        attached = replace(
            run,
            workflow_run_id=workflow_run_id,
            status=AgentRunStatus.WAITING_APPROVAL if waiting else run.status,
        )
        self.runs[run_id] = attached
        self._append(
            attached,
            "agents.workflow-attached",
            {"schema": "agent-workflow-attached.v1", "waiting_approval": waiting},
        )
        return self.runs[run_id]

    async def settle_approval(
        self, workspace_id: UUID, run_id: UUID, *, approved: bool
    ) -> AgentRun:
        run = self._scoped(workspace_id, run_id)
        target = AgentRunStatus.SUCCEEDED if approved else AgentRunStatus.REJECTED
        if (
            run.status is target
            and run.result_kind is AgentResultKind.WORKFLOW_PLAN_PROPOSAL
            and run.workflow_run_id is not None
        ):
            return run
        if run.status is not AgentRunStatus.WAITING_APPROVAL or run.workflow_run_id is None:
            raise InvalidStateError("Agent run is not waiting for approval.")
        settled = replace(run, status=target)
        self.runs[run_id] = settled
        self._append(
            settled,
            "agents.approval-decided",
            {"schema": "agent-approval-decided.v1", "approved": approved},
        )
        return self.runs[run_id]

    async def get(self, workspace_id: UUID, run_id: UUID) -> AgentRun | None:
        run = self.runs.get(run_id)
        return run if run is not None and run.workspace_id == workspace_id else None

    async def get_by_idempotency(self, workspace_id: UUID, idempotency_key: str) -> AgentRun | None:
        found = self._idempotency.get((workspace_id, idempotency_key))
        return None if found is None else self.runs[found[1]]

    async def get_snapshot(
        self, workspace_id: UUID, snapshot_id: UUID
    ) -> AgentContextSnapshot | None:
        snapshot = self.snapshots.get(snapshot_id)
        return snapshot if snapshot is not None and snapshot.workspace_id == workspace_id else None

    async def get_events(
        self, workspace_id: UUID, run_id: UUID, *, after_sequence: int = 0
    ) -> tuple[AgentRunEvent, ...]:
        return tuple(
            item
            for item in self.events
            if item.workspace_id == workspace_id
            and item.agent_run_id == run_id
            and item.sequence > after_sequence
        )

    def _require(self, run_id: UUID) -> AgentRun:
        run = self.runs.get(run_id)
        if run is None:
            raise InvalidStateError("Agent run is unavailable.")
        return run

    def _scoped(self, workspace_id: UUID, run_id: UUID) -> AgentRun:
        run = self._require(run_id)
        if run.workspace_id != workspace_id:
            raise ScopeViolationError
        return run

    def _append(self, run: AgentRun, event_type: str, payload: dict[str, object]) -> None:
        sequence = sum(1 for item in self.events if item.agent_run_id == run.id) + 1
        self.events.append(
            AgentRunEvent(
                uuid4(),
                run.workspace_id,
                run.project_id,
                run.id,
                sequence,
                event_type,
                1,
                payload,
                run.updated_at,
            )
        )


class SqlAlchemyAgentRepository:
    """Atomic, workspace-scoped Agent repository."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def begin(
        self,
        run: AgentRun,
        snapshot: AgentContextSnapshot,
        *,
        request_digest: str,
    ) -> tuple[AgentRun, bool]:
        async with self._sessions.begin() as session:
            record, created = await SqlAlchemyIdempotencyStore(session).reserve(
                IdempotencyRecord(
                    uuid4(),
                    run.workspace_id,
                    run.project_id,
                    "agents.run",
                    run.idempotency_key,
                    request_digest,
                    str(run.id),
                    run.created_at + timedelta(days=1),
                )
            )
            if not created:
                existing = await session.scalar(
                    select(AgentRunRow).where(
                        AgentRunRow.workspace_id == run.workspace_id,
                        AgentRunRow.id == UUID(record.result_reference),
                    )
                )
                if existing is None:
                    raise InvalidStateError("Idempotent Agent result is unavailable.")
                return _run(existing), False
            session.add(_snapshot_row(snapshot))
            row = _run_row(run)
            session.add(row)
            await session.flush()
            await _append_event(
                session,
                row,
                "agents.run-started",
                {"schema": "agent-run-started.v1"},
                run.created_at,
            )
            return _run(row), True

    async def complete(self, run_id: UUID, result: AgentResult, raw: RawAgentResult) -> AgentRun:
        async with self._sessions.begin() as session:
            row = await _locked_run(session, run_id)
            if AgentRunStatus(row.status) is not AgentRunStatus.RUNNING:
                return _run(row)
            completed = _completed_run(_run(row), result, raw, row.updated_at)
            _apply_run(row, completed)
            await _append_event(
                session,
                row,
                "agents.run-succeeded",
                {"schema": "agent-run-succeeded.v1", "result_kind": result.kind.value},
                completed.updated_at,
            )
            return _run(row)

    async def fail(
        self, run_id: UUID, status: AgentRunStatus, error: AgentRuntimeError
    ) -> AgentRun:
        async with self._sessions.begin() as session:
            row = await _locked_run(session, run_id)
            if AgentRunStatus(row.status) is not AgentRunStatus.RUNNING:
                return _run(row)
            row.status = status.value
            row.error_code = error.code.value
            await _append_event(
                session,
                row,
                "agents.run-failed",
                {"schema": "agent-run-failed.v1", "error_code": error.code.value},
                row.updated_at,
            )
            return _run(row)

    async def attach_workflow(
        self, workspace_id: UUID, run_id: UUID, workflow_run_id: UUID, *, waiting: bool
    ) -> AgentRun:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(AgentRunRow)
                .where(AgentRunRow.workspace_id == workspace_id, AgentRunRow.id == run_id)
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if row.workflow_run_id not in {None, workflow_run_id}:
                raise InvalidStateError("Agent run is already attached to another Workflow.")
            if row.workflow_run_id == workflow_run_id:
                return _run(row)
            row.workflow_run_id = workflow_run_id
            if waiting:
                row.status = AgentRunStatus.WAITING_APPROVAL.value
            await _append_event(
                session,
                row,
                "agents.workflow-attached",
                {"schema": "agent-workflow-attached.v1", "waiting_approval": waiting},
                row.updated_at,
            )
            return _run(row)

    async def settle_approval(
        self, workspace_id: UUID, run_id: UUID, *, approved: bool
    ) -> AgentRun:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(AgentRunRow)
                .where(AgentRunRow.workspace_id == workspace_id, AgentRunRow.id == run_id)
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            target = AgentRunStatus.SUCCEEDED if approved else AgentRunStatus.REJECTED
            if (
                AgentRunStatus(row.status) is target
                and row.result_kind == AgentResultKind.WORKFLOW_PLAN_PROPOSAL.value
                and row.workflow_run_id is not None
            ):
                return _run(row)
            if (
                AgentRunStatus(row.status) is not AgentRunStatus.WAITING_APPROVAL
                or row.workflow_run_id is None
            ):
                raise InvalidStateError("Agent run is not waiting for approval.")
            row.status = target.value
            await _append_event(
                session,
                row,
                "agents.approval-decided",
                {"schema": "agent-approval-decided.v1", "approved": approved},
                row.updated_at,
            )
            return _run(row)

    async def get(self, workspace_id: UUID, run_id: UUID) -> AgentRun | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AgentRunRow).where(
                    AgentRunRow.workspace_id == workspace_id,
                    AgentRunRow.id == run_id,
                )
            )
        return None if row is None else _run(row)

    async def get_by_idempotency(self, workspace_id: UUID, idempotency_key: str) -> AgentRun | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AgentRunRow).where(
                    AgentRunRow.workspace_id == workspace_id,
                    AgentRunRow.idempotency_key == idempotency_key,
                )
            )
        return None if row is None else _run(row)

    async def get_snapshot(
        self, workspace_id: UUID, snapshot_id: UUID
    ) -> AgentContextSnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AgentContextSnapshotRow).where(
                    AgentContextSnapshotRow.workspace_id == workspace_id,
                    AgentContextSnapshotRow.id == snapshot_id,
                )
            )
        return None if row is None else _snapshot(row)

    async def get_events(
        self, workspace_id: UUID, run_id: UUID, *, after_sequence: int = 0
    ) -> tuple[AgentRunEvent, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AgentRunEventRow)
                    .where(
                        AgentRunEventRow.workspace_id == workspace_id,
                        AgentRunEventRow.agent_run_id == run_id,
                        AgentRunEventRow.sequence > after_sequence,
                    )
                    .order_by(AgentRunEventRow.sequence)
                )
            ).all()
        return tuple(_event(row) for row in rows)


async def _locked_run(session: AsyncSession, run_id: UUID) -> AgentRunRow:
    row = await session.scalar(
        select(AgentRunRow).where(AgentRunRow.id == run_id).with_for_update()
    )
    if row is None:
        raise InvalidStateError("Agent run is unavailable.")
    return row


async def _append_event(
    session: AsyncSession,
    run: AgentRunRow,
    event_type: str,
    payload: dict[str, object],
    occurred_at: datetime,
) -> None:
    run.event_sequence += 1
    event_id = uuid4()
    session.add(
        AgentRunEventRow(
            id=event_id,
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            agent_run_id=run.id,
            sequence=run.event_sequence,
            event_type=event_type,
            event_version=1,
            payload=payload,
            occurred_at=occurred_at,
        )
    )
    await SqlAlchemyOutboxWriter(session).append(
        EventEnvelope(
            event_id,
            run.workspace_id,
            run.project_id,
            run.id,
            event_type,
            1,
            {**payload, "agent_run_id": str(run.id)},
            occurred_at,
        )
    )
    await session.flush()


def _completed_run(
    run: AgentRun, result: AgentResult, raw: RawAgentResult, updated_at: datetime
) -> AgentRun:
    workflow_name: str | None = None
    workflow_version: int | None = None
    operations: tuple[ProtectedOperation, ...] = ()
    result_reference = raw.result_reference
    if isinstance(result, (WorkflowSelection, WorkflowPlanProposal)):
        workflow_name = result.workflow_name
        workflow_version = result.workflow_version
        result_reference = result.input_reference
    if isinstance(result, WorkflowPlanProposal):
        operations = result.protected_operations
    if isinstance(result, AgentProposal):
        result_reference = result.result_reference
    return replace(
        run,
        status=AgentRunStatus.SUCCEEDED,
        result_kind=result.kind,
        result_reference=result_reference,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        protected_operations=operations,
        model_calls=raw.model_calls,
        tool_calls=raw.tool_calls,
        tokens=raw.tokens,
        updated_at=updated_at,
    )


def _descriptor_payload(descriptor: AgentDescriptor) -> dict[str, object]:
    return {
        "agent_id": descriptor.agent_id,
        "version": descriptor.version,
        "capabilities": list(descriptor.capabilities),
        "input_schema": descriptor.input_schema,
        "output_schema": descriptor.output_schema,
        "allowed_tool_ids": list(descriptor.allowed_tool_ids),
        "model_policy_id": descriptor.model_policy_id,
        "model_policy_version": descriptor.model_policy_version,
        "prompt_metadata": {
            "metadata_id": descriptor.prompt_metadata.metadata_id,
            "version": descriptor.prompt_metadata.version,
            "checksum": descriptor.prompt_metadata.checksum,
        },
        "budget_limit": {
            "max_steps": descriptor.budget_limit.max_steps,
            "max_recursion_depth": descriptor.budget_limit.max_recursion_depth,
            "max_parallelism": descriptor.budget_limit.max_parallelism,
            "max_duration_seconds": descriptor.budget_limit.max_duration_seconds,
            "max_calls": descriptor.budget_limit.max_calls,
            "max_tokens": descriptor.budget_limit.max_tokens,
        },
    }


def _descriptor(payload: dict[str, object]) -> AgentDescriptor:
    prompt = cast("dict[str, object]", payload["prompt_metadata"])
    budget = cast("dict[str, object]", payload["budget_limit"])
    return AgentDescriptor(
        cast("str", payload["agent_id"]),
        cast("str", payload["version"]),
        tuple(cast("list[str]", payload["capabilities"])),
        cast("dict[str, object]", payload["input_schema"]),
        cast("dict[str, object]", payload["output_schema"]),
        tuple(cast("list[str]", payload["allowed_tool_ids"])),
        cast("str", payload["model_policy_id"]),
        cast("str", payload["model_policy_version"]),
        PromptMetadataReference(
            cast("str", prompt["metadata_id"]),
            cast("str", prompt["version"]),
            cast("str", prompt["checksum"]),
        ),
        AgentBudget(
            cast("int", budget["max_steps"]),
            cast("int", budget["max_recursion_depth"]),
            cast("int", budget["max_parallelism"]),
            cast("float", budget["max_duration_seconds"]),
            cast("int", budget["max_calls"]),
            cast("int", budget["max_tokens"]),
        ),
    )


def _role(row: AgentRoleVersionRow) -> RoleDescriptorVersion:
    return RoleDescriptorVersion(
        row.id,
        row.workspace_id,
        row.role_key,
        row.role_version,
        RoleVersionStatus(row.status),
        _descriptor(row.descriptor),
        row.checksum,
        row.created_by,
        row.created_at,
    )


def _grant(row: AgentRoleToolGrantRow) -> RoleToolGrant:
    return RoleToolGrant(
        row.id,
        row.workspace_id,
        row.role_version_id,
        row.tool_id,
        row.tool_version,
        tuple(row.permissions),
        row.active,
        row.created_at,
    )


def _snapshot_row(snapshot: AgentContextSnapshot) -> AgentContextSnapshotRow:
    return AgentContextSnapshotRow(
        id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        project_id=snapshot.project_id,
        agent_id=snapshot.agent_id,
        agent_version=snapshot.agent_version,
        model_policy_id=snapshot.model_policy_id,
        model_policy_version=snapshot.model_policy_version,
        prompt_metadata_id=snapshot.prompt_metadata_id,
        prompt_metadata_version=snapshot.prompt_metadata_version,
        prompt_metadata_checksum=snapshot.prompt_metadata_checksum,
        tool_versions=list(snapshot.tool_versions),
        permission_snapshot=list(snapshot.permission_snapshot),
        input_digest=snapshot.input_digest,
        memory_context_package_id=snapshot.memory_context_package_id,
        created_at=snapshot.created_at,
    )


def _run_row(run: AgentRun) -> AgentRunRow:
    return AgentRunRow(
        id=run.id,
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        agent_id=run.agent_id,
        agent_version=run.agent_version,
        context_snapshot_id=run.context_snapshot_id,
        status=run.status.value,
        attempt=run.attempt,
        idempotency_key=run.idempotency_key,
        task_reference=run.task_reference,
        requested_by=run.requested_by,
        correlation_id=run.correlation_id,
        workflow_run_id=run.workflow_run_id,
        result_kind=run.result_kind.value if run.result_kind else None,
        result_reference=run.result_reference,
        workflow_name=run.workflow_name,
        workflow_version=run.workflow_version,
        protected_operations=[item.value for item in run.protected_operations],
        model_calls=run.model_calls,
        tool_calls=run.tool_calls,
        tokens=run.tokens,
        error_code=run.error_code.value if run.error_code else None,
        event_sequence=0,
        created_at=run.created_at,
        updated_at=run.updated_at,
        version=1,
    )


def _apply_run(row: AgentRunRow, run: AgentRun) -> None:
    row.status = run.status.value
    row.result_kind = run.result_kind.value if run.result_kind else None
    row.result_reference = run.result_reference
    row.workflow_name = run.workflow_name
    row.workflow_version = run.workflow_version
    row.protected_operations = [item.value for item in run.protected_operations]
    row.model_calls = run.model_calls
    row.tool_calls = run.tool_calls
    row.tokens = run.tokens
    row.error_code = run.error_code.value if run.error_code else None
    row.updated_at = run.updated_at


def _run(row: AgentRunRow) -> AgentRun:
    return AgentRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.agent_id,
        row.agent_version,
        row.context_snapshot_id,
        AgentRunStatus(row.status),
        row.attempt,
        row.idempotency_key,
        row.task_reference,
        row.requested_by,
        row.correlation_id,
        row.created_at,
        row.updated_at,
        row.workflow_run_id,
        AgentResultKind(row.result_kind) if row.result_kind else None,
        row.result_reference,
        row.workflow_name,
        row.workflow_version,
        tuple(ProtectedOperation(item) for item in row.protected_operations),
        row.model_calls,
        row.tool_calls,
        row.tokens,
        AgentErrorCode(row.error_code) if row.error_code else None,
    )


def _snapshot(row: AgentContextSnapshotRow) -> AgentContextSnapshot:
    return AgentContextSnapshot(
        row.id,
        row.workspace_id,
        row.project_id,
        row.agent_id,
        row.agent_version,
        row.model_policy_id,
        row.model_policy_version,
        row.prompt_metadata_id,
        row.prompt_metadata_version,
        row.prompt_metadata_checksum,
        tuple(row.tool_versions),
        tuple(row.permission_snapshot),
        row.input_digest,
        row.created_at,
        row.memory_context_package_id,
    )


def _event(row: AgentRunEventRow) -> AgentRunEvent:
    return AgentRunEvent(
        row.id,
        row.workspace_id,
        row.project_id,
        row.agent_run_id,
        row.sequence,
        row.event_type,
        row.event_version,
        dict(row.payload),
        row.occurred_at,
    )


MODEL_REGISTRY = (
    AgentContextSnapshotRow,
    AgentRoleToolGrantRow,
    AgentRoleVersionRow,
    AgentRunEventRow,
    AgentRunRow,
)
