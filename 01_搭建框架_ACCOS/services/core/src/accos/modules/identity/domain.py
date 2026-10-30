"""Framework-free identity, workspace, role, and approval domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.security import ActorKind

POLICY_VERSION = "identity-rbac-v1"


class Role(StrEnum):
    """Fixed first-release workspace roles."""

    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
    SERVICE = "SERVICE"


class Permission(StrEnum):
    """Server-side action plus resource permissions."""

    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    MEMBERSHIP_MANAGE = "membership:manage"
    OWNERSHIP_TRANSFER = "ownership:transfer"
    DATA_EXPORT = "data:export"
    DATA_ARCHIVE = "data:archive"
    DATA_DELETE_REQUEST = "data:request-delete"
    APPROVAL_DECIDE = "approval:decide"
    AUDIT_READ = "audit:read"
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    FEATURE_MANAGE = "feature-flag:manage"
    EVOLUTION_APPLY = "evolution:apply"
    AGENT_RUN = "agent:run"
    MODEL_RUN = "model:run"
    TOOL_RUN = "tool:run"


_OWNER_PERMISSIONS = frozenset(Permission)
_EDITOR_PERMISSIONS = frozenset(
    {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.DATA_EXPORT,
        Permission.DATA_ARCHIVE,
        Permission.DATA_DELETE_REQUEST,
        Permission.AUDIT_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.AGENT_RUN,
        Permission.MODEL_RUN,
        Permission.TOOL_RUN,
    }
)
_VIEWER_PERMISSIONS = frozenset(
    {Permission.WORKSPACE_READ, Permission.AUDIT_READ, Permission.PROJECT_READ}
)
_SERVICE_CEILING = frozenset(
    {
        Permission.WORKSPACE_READ,
        Permission.PROJECT_READ,
        Permission.AGENT_RUN,
        Permission.MODEL_RUN,
        Permission.TOOL_RUN,
    }
)
ROLE_PERMISSIONS = MappingProxyType(
    {
        Role.OWNER: _OWNER_PERMISSIONS,
        Role.EDITOR: _EDITOR_PERMISSIONS,
        Role.VIEWER: _VIEWER_PERMISSIONS,
        Role.SERVICE: _SERVICE_CEILING,
    }
)


def permissions_for(role: Role, explicit: frozenset[Permission] | None = None) -> frozenset[str]:
    """Resolve an immutable snapshot; service grants can only narrow their ceiling."""
    selected = ROLE_PERMISSIONS[role]
    if role is Role.SERVICE:
        selected = selected.intersection(explicit or frozenset())
    return frozenset(permission.value for permission in selected)


@dataclass(frozen=True, slots=True)
class User:
    """Internal user mapped to one external issuer and subject."""

    id: UUID
    issuer: str
    subject: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class Workspace:
    """Creator-controlled top-level authorization and data boundary."""

    id: UUID
    owner_user_id: UUID
    archived: bool = False


@dataclass(frozen=True, slots=True)
class Membership:
    """A user role inside exactly one workspace."""

    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: Role
    active: bool = True


@dataclass(frozen=True, slots=True)
class ServiceIdentity:
    """Non-human principal with grants capped by the SERVICE role."""

    id: UUID
    workspace_id: UUID
    name: str
    permissions: frozenset[Permission]
    active: bool = True


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """Verified provider output before workspace membership resolution."""

    issuer: str
    subject: str
    actor_kind: ActorKind
    service_identity_id: UUID | None = None
    auth_method: str = "legacy"
    credential_id: UUID | None = None
    token_workspace_id: UUID | None = None
    token_permissions: tuple[str, ...] | None = None
    token_project_id: UUID | None = None


class ControlRequestKind(StrEnum):
    """Creator-control operations represented as recoverable requests."""

    OWNERSHIP_TRANSFER = "ownership_transfer"
    EXPORT = "export"
    ARCHIVE = "archive"
    DELETE = "delete"


class ControlRequestStatus(StrEnum):
    """Human-control lifecycle; physical deletion is intentionally absent."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalDecision(StrEnum):
    """Allowed decisions for a pending control request."""

    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ControlRequest:
    """Versioned request describing scope, expected change, and risk by stable codes."""

    id: UUID
    workspace_id: UUID
    requested_by: UUID
    kind: ControlRequestKind
    resource_type: str
    resource_id: str
    change_code: str
    risk_code: str
    status: ControlRequestStatus
    correlation_id: UUID
    requested_at: datetime
    approval_policy_ref: str = "legacy_dual_control"


@dataclass(frozen=True, slots=True)
class HumanApproval:
    """Append-only human decision linked to a control request."""

    id: UUID
    workspace_id: UUID
    request_id: UUID
    decided_by: UUID
    decision: ApprovalDecision
    correlation_id: UUID
    decided_at: datetime
