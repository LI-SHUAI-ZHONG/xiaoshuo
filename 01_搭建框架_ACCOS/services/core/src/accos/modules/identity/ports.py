"""Ports owned by the identity and security module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.contracts import PageRequest
    from accos.kernel.persistence import Page
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.application import ResourceScope
    from accos.modules.identity.domain import (
        AuthenticatedIdentity,
        ControlRequest,
        HumanApproval,
        Membership,
        ServiceIdentity,
        User,
        Workspace,
    )


class ScopeAccess(Protocol):
    async def hidden_projects(self, context: SecurityContext) -> frozenset[UUID]: ...

    async def allows(
        self, context: SecurityContext, resource: ResourceScope, permission: str
    ) -> bool: ...


class IdentityProvider(Protocol):
    """Verify an OIDC/JWT-like credential without owning membership policy."""

    async def authenticate(self, credential: str, *, now: datetime) -> AuthenticatedIdentity:
        """Return verified provider claims or raise a safe authentication error."""
        ...


class IdentityReader(Protocol):
    """Scoped identity lookups used when constructing permission snapshots."""

    async def find_user(self, issuer: str, subject: str) -> User | None:
        """Resolve an external identity to its internal user."""
        ...

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> Membership | None:
        """Resolve active membership within the supplied workspace only."""
        ...

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """Load exactly one selected workspace."""
        ...

    async def list_memberships(self, workspace_id: UUID, page: PageRequest) -> Page[Membership]:
        """List role bindings inside exactly one workspace."""
        ...

    async def get_service_identity(
        self, workspace_id: UUID, identity_id: UUID
    ) -> ServiceIdentity | None:
        """Resolve an active service principal within the supplied workspace only."""
        ...


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Sanitized append-only authorization evidence."""

    id: UUID
    workspace_id: UUID
    actor_id: UUID | None
    actor_kind: str
    action: str
    resource_type: str
    resource_id: str
    result: str
    reason_code: str
    policy_version: str
    correlation_id: UUID
    occurred_at: datetime
    metadata: dict[str, str]


class AuditRecorder(Protocol):
    """Append authorization evidence; update and delete are intentionally absent."""

    async def append(self, event: AuditEvent) -> None:
        """Durably append one sanitized event."""
        ...


class ControlRequestStore(Protocol):
    """Workspace-scoped creator-control request persistence."""

    async def list_requests(self, workspace_id: UUID) -> tuple[ControlRequest, ...]: ...

    async def add_request(self, request: ControlRequest) -> None:
        """Persist a pending request."""
        ...

    async def get_request(self, workspace_id: UUID, request_id: UUID) -> ControlRequest | None:
        """Read only inside the caller's workspace."""
        ...

    async def add_approval(self, approval: HumanApproval) -> None:
        """Append a human decision and transition its request atomically."""
        ...


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Provider-neutral result of one rate-limit check."""

    allowed: bool
    retry_after_seconds: int | None = None


class RateLimiter(Protocol):
    """Rate-limit port shared by protected inbound boundaries."""

    async def check(self, context: SecurityContext, action: str) -> RateLimitDecision:
        """Fail closed when the actor's configured request budget is exhausted."""
        ...


@dataclass(frozen=True, slots=True)
class UploadDescriptor:
    """Metadata-only upload description; payload inspection belongs to execution 07."""

    media_type: str
    size_bytes: int
    filename: str


class UploadSecurityPolicy(Protocol):
    """Upload policy boundary introduced before object ingestion exists."""

    async def permits(self, context: SecurityContext, upload: UploadDescriptor) -> bool:
        """Return a policy decision without reading or storing the upload body."""
        ...
