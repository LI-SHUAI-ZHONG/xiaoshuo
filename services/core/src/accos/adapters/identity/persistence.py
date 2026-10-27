"""Private SQLAlchemy identity models and strictly scoped repository adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base, utc_now
from accos.kernel.errors import ConfigurationError, InvalidStateError
from accos.kernel.logging import get_logger, log_event
from accos.kernel.persistence import Page
from accos.modules.identity.domain import (
    ApprovalDecision,
    ControlRequest,
    ControlRequestKind,
    ControlRequestStatus,
    HumanApproval,
    Membership,
    Permission,
    Role,
    ServiceIdentity,
    User,
    Workspace,
)
from accos.modules.identity.ports import AuditEvent

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.contracts import PageRequest

_AUDIT_METADATA_KEYS = frozenset({"operation_code", "state_code", "auth_method", "credential_id"})
_AUDIT_METADATA_MAX_LENGTH = 100


class UserRow(Base):
    """Private global mapping from external subject to internal actor."""

    __tablename__ = "identity_users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_identity_users_issuer_subject"),
        CheckConstraint("version > 0", name="ck_identity_users_version_positive"),
        {"schema": SCHEMA_NAME},
    )


class WorkspaceRow(Base):
    """Private workspace ownership record."""

    __tablename__ = "identity_workspaces"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_users.id", name="fk_workspaces_owner_user"),
        nullable=False,
    )
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_identity_workspaces_version_positive"),
        {"schema": SCHEMA_NAME},
    )


class MembershipRow(Base):
    """Private workspace-scoped role binding."""

    __tablename__ = "identity_memberships"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_workspaces.id", name="fk_memberships_workspace"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_users.id", name="fk_memberships_user"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_memberships_workspace_user"),
        CheckConstraint(
            "role IN ('OWNER', 'EDITOR', 'VIEWER', 'SERVICE')",
            name="ck_memberships_role_valid",
        ),
        CheckConstraint("version > 0", name="ck_memberships_version_positive"),
        Index("ix_memberships_workspace_active", "workspace_id", "active"),
        {"schema": SCHEMA_NAME},
    )


class ServiceIdentityRow(Base):
    """Private service principal with an explicitly narrowed grant list."""

    __tablename__ = "identity_service_identities"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_workspaces.id", name="fk_service_identities_workspace"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_service_identities_workspace_name"),
        CheckConstraint("version > 0", name="ck_service_identities_version_positive"),
        Index("ix_service_identities_workspace_active", "workspace_id", "active"),
        {"schema": SCHEMA_NAME},
    )


class AuditEventRow(Base):
    """Append-only security decision record with no mutable lifecycle columns."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False, unique=True
    )
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(200), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("result IN ('allowed', 'denied')", name="ck_audit_result_valid"),
        Index("ix_audit_workspace_sequence", "workspace_id", "sequence"),
        {"schema": SCHEMA_NAME},
    )


class ControlRequestRow(Base):
    """Recoverable request for ownership and data-control operations."""

    __tablename__ = "identity_control_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(200), nullable=False)
    change_code: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_code: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approval_policy_ref: Mapped[str] = mapped_column(
        String(100), nullable=False, default="legacy_dual_control"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint(
            "kind IN ('ownership_transfer', 'export', 'archive', 'delete')",
            name="ck_control_requests_kind_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_control_requests_status_valid",
        ),
        CheckConstraint("version > 0", name="ck_control_requests_version_positive"),
        Index("ix_control_requests_workspace_status", "workspace_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class HumanApprovalRow(Base):
    """Append-only human approval or rejection decision."""

    __tablename__ = "identity_human_approvals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_control_requests.id", name="fk_human_approvals_request"),
        nullable=False,
        unique=True,
    )
    decided_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve', 'reject')", name="ck_human_approvals_decision_valid"
        ),
        Index("ix_human_approvals_workspace", "workspace_id"),
        {"schema": SCHEMA_NAME},
    )


MODEL_REGISTRY = (
    UserRow,
    WorkspaceRow,
    MembershipRow,
    ServiceIdentityRow,
    AuditEventRow,
    ControlRequestRow,
    HumanApprovalRow,
)


def sanitize_audit_metadata(metadata: dict[str, str]) -> dict[str, str]:
    """Allowlist short operational codes; drop bodies, credentials, and arbitrary text."""
    return {
        key: value[:_AUDIT_METADATA_MAX_LENGTH]
        for key, value in metadata.items()
        if key in _AUDIT_METADATA_KEYS
    }


class SqlAlchemyIdentityRepository:
    """All membership and service queries require an explicit workspace scope."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def find_user(self, issuer: str, subject: str) -> User | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(UserRow).where(UserRow.issuer == issuer, UserRow.subject == subject)
            )
        return None if row is None else User(row.id, row.issuer, row.subject, row.active)

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> Membership | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MembershipRow).where(
                    MembershipRow.workspace_id == workspace_id,
                    MembershipRow.user_id == user_id,
                )
            )
        return (
            None
            if row is None
            else Membership(row.id, row.workspace_id, row.user_id, Role(row.role), row.active)
        )

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        async with self._sessions() as session:
            row = await session.scalar(select(WorkspaceRow).where(WorkspaceRow.id == workspace_id))
        return None if row is None else Workspace(row.id, row.owner_user_id, row.archived)

    async def list_memberships(self, workspace_id: UUID, page: PageRequest) -> Page[Membership]:
        async with self._sessions() as session:
            total = int(
                await session.scalar(
                    select(func.count())
                    .select_from(MembershipRow)
                    .where(MembershipRow.workspace_id == workspace_id)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(MembershipRow)
                    .where(MembershipRow.workspace_id == workspace_id)
                    .order_by(MembershipRow.id)
                    .offset(page.offset)
                    .limit(page.limit)
                )
            ).all()
        return Page(
            tuple(
                Membership(row.id, row.workspace_id, row.user_id, Role(row.role), row.active)
                for row in rows
            ),
            total,
            page,
        )

    async def get_service_identity(
        self, workspace_id: UUID, identity_id: UUID
    ) -> ServiceIdentity | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ServiceIdentityRow).where(
                    ServiceIdentityRow.workspace_id == workspace_id,
                    ServiceIdentityRow.id == identity_id,
                )
            )
        return (
            None
            if row is None
            else ServiceIdentity(
                row.id,
                row.workspace_id,
                row.name,
                frozenset(Permission(value) for value in row.permissions),
                row.active,
            )
        )


class SqlAlchemyAuditStore:
    """Append and workspace-scoped read adapter for immutable audit events."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def append(self, event: AuditEvent) -> None:
        async with self._sessions.begin() as session:
            session.add(
                AuditEventRow(
                    id=event.id,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    actor_kind=event.actor_kind,
                    action=event.action,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    result=event.result,
                    reason_code=event.reason_code,
                    policy_version=event.policy_version,
                    correlation_id=event.correlation_id,
                    occurred_at=event.occurred_at,
                    payload=sanitize_audit_metadata(event.metadata),
                )
            )

    async def list_for_workspace(self, workspace_id: UUID) -> tuple[AuditEvent, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AuditEventRow)
                    .where(AuditEventRow.workspace_id == workspace_id)
                    .order_by(AuditEventRow.sequence)
                )
            ).all()
        return tuple(
            AuditEvent(
                row.id,
                row.workspace_id,
                row.actor_id,
                row.actor_kind,
                row.action,
                row.resource_type,
                row.resource_id,
                row.result,
                row.reason_code,
                row.policy_version,
                row.correlation_id,
                row.occurred_at,
                {str(key): str(value) for key, value in row.payload.items()},
            )
            for row in rows
        )


class SqlAlchemyControlRequestStore:
    """Workspace-scoped control requests with atomic one-time human decisions."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def list_requests(self, workspace_id: UUID) -> tuple[ControlRequest, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ControlRequestRow)
                    .where(ControlRequestRow.workspace_id == workspace_id)
                    .order_by(ControlRequestRow.requested_at.desc())
                    .limit(100)
                )
            ).all()
        return tuple(_control_request_from_row(row) for row in rows)

    async def add_request(self, request: ControlRequest) -> None:
        async with self._sessions.begin() as session:
            session.add(
                ControlRequestRow(
                    id=request.id,
                    workspace_id=request.workspace_id,
                    requested_by=request.requested_by,
                    kind=request.kind.value,
                    resource_type=request.resource_type,
                    resource_id=request.resource_id,
                    change_code=request.change_code,
                    risk_code=request.risk_code,
                    status=request.status.value,
                    correlation_id=request.correlation_id,
                    requested_at=request.requested_at,
                    approval_policy_ref=request.approval_policy_ref,
                )
            )

    async def get_request(self, workspace_id: UUID, request_id: UUID) -> ControlRequest | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ControlRequestRow).where(
                    ControlRequestRow.workspace_id == workspace_id,
                    ControlRequestRow.id == request_id,
                )
            )
        return None if row is None else _control_request_from_row(row)

    async def add_approval(self, approval: HumanApproval) -> None:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(ControlRequestRow)
                .where(
                    ControlRequestRow.workspace_id == approval.workspace_id,
                    ControlRequestRow.id == approval.request_id,
                )
                .with_for_update()
            )
            if row is None:
                raise InvalidStateError("Control request is unavailable.")
            if row.status != ControlRequestStatus.PENDING:
                raise InvalidStateError("Only pending control requests can be decided.")
            row.status = (
                ControlRequestStatus.APPROVED
                if approval.decision is ApprovalDecision.APPROVE
                else ControlRequestStatus.REJECTED
            )
            row.resolved_at = approval.decided_at
            session.add(
                HumanApprovalRow(
                    id=approval.id,
                    workspace_id=approval.workspace_id,
                    request_id=approval.request_id,
                    decided_by=approval.decided_by,
                    decision=approval.decision.value,
                    correlation_id=approval.correlation_id,
                    decided_at=approval.decided_at,
                )
            )


def _control_request_from_row(row: ControlRequestRow) -> ControlRequest:
    return ControlRequest(
        row.id,
        row.workspace_id,
        row.requested_by,
        ControlRequestKind(row.kind),
        row.resource_type,
        row.resource_id,
        row.change_code,
        row.risk_code,
        ControlRequestStatus(row.status),
        row.correlation_id,
        row.requested_at,
        row.approval_policy_ref,
    )


@dataclass(slots=True)
class IdentityRuntime:
    """Optionally provisions only the explicitly enabled local development identity."""

    sessions: AsyncSessionFactory
    actor_id: UUID | None = None
    workspace_id: UUID | None = None
    approver_actor_id: UUID | None = None
    enabled: bool = False
    name: str = field(default="identity", init=False)
    logger: logging.Logger = field(default_factory=lambda: get_logger("lifecycle"), repr=False)

    async def startup(self) -> None:
        if self.enabled:
            await self._provision()
        log_event(self.logger, logging.INFO, "module_started", module=self.name)

    async def shutdown(self) -> None:
        log_event(self.logger, logging.INFO, "module_stopped", module=self.name)

    async def _provision(self) -> None:
        actor_id = self.actor_id
        workspace_id = self.workspace_id
        if actor_id is None or workspace_id is None:
            raise ConfigurationError("Development identity IDs must be configured.")
        if self.approver_actor_id == actor_id:
            raise ConfigurationError("Development approver actor ID must differ.")
        async with self.sessions.begin() as session:
            await session.execute(
                insert(UserRow)
                .values(
                    id=actor_id,
                    issuer="urn:accos:development",
                    subject="local-development",
                    active=True,
                )
                .on_conflict_do_nothing()
            )
            await session.execute(
                insert(WorkspaceRow)
                .values(id=workspace_id, owner_user_id=actor_id, archived=False)
                .on_conflict_do_nothing()
            )
            await session.execute(
                insert(MembershipRow)
                .values(
                    id=actor_id,
                    workspace_id=workspace_id,
                    user_id=actor_id,
                    role=Role.OWNER.value,
                    active=True,
                )
                .on_conflict_do_nothing()
            )
            if self.approver_actor_id is not None:
                await session.execute(
                    insert(UserRow)
                    .values(
                        id=self.approver_actor_id,
                        issuer="urn:accos:development",
                        subject="local-development-approver",
                        active=True,
                    )
                    .on_conflict_do_nothing()
                )
                await session.execute(
                    insert(MembershipRow)
                    .values(
                        id=self.approver_actor_id,
                        workspace_id=workspace_id,
                        user_id=self.approver_actor_id,
                        role=Role.OWNER.value,
                        active=True,
                    )
                    .on_conflict_do_nothing()
                )
