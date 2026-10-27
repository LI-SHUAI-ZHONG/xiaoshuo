"""Identity authentication, default-deny RBAC, and creator-control use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.errors import (
    AuthenticationRequiredError,
    InvalidStateError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ScopeViolationError,
)
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.identity.domain import (
    POLICY_VERSION,
    ApprovalDecision,
    ControlRequest,
    ControlRequestKind,
    ControlRequestStatus,
    HumanApproval,
    Permission,
    Role,
    permissions_for,
)
from accos.modules.identity.ports import AuditEvent

if TYPE_CHECKING:
    from typing import NoReturn

    from accos.kernel.clock import Clock
    from accos.kernel.contracts import PageRequest
    from accos.kernel.errors import KernelError
    from accos.kernel.ids import CorrelationIds
    from accos.kernel.persistence import Page
    from accos.modules.identity.accounts import ApprovalPolicyPort
    from accos.modules.identity.domain import Membership, Workspace
    from accos.modules.identity.ports import (
        AuditRecorder,
        ControlRequestStore,
        IdentityProvider,
        IdentityReader,
        ScopeAccess,
    )


@dataclass(frozen=True, slots=True)
class ResourceScope:
    """Trusted ownership scope loaded with a protected resource."""

    workspace_id: UUID
    resource_type: str
    resource_id: str
    project_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """One explicit action checked against a trusted resource scope."""

    context: SecurityContext
    permission: Permission
    resource: ResourceScope


@dataclass(frozen=True, slots=True)
class ControlRequestDraft:
    """Sanitized request input containing stable change and risk codes only."""

    kind: ControlRequestKind
    resource_type: str
    resource_id: str
    change_code: str
    risk_code: str


class IdentityAuthenticator:
    """Combine provider verification with server-owned membership state."""

    def __init__(
        self,
        provider: IdentityProvider,
        identities: IdentityReader,
        clock: Clock,
    ) -> None:
        self._provider = provider
        self._identities = identities
        self._clock = clock

    async def authenticate(
        self,
        credential: str,
        workspace_id: UUID,
        correlation: CorrelationIds,
    ) -> SecurityContext:
        """Create an immutable context from verified identity plus scoped membership."""
        identity = await self._provider.authenticate(credential, now=self._clock.now())
        workspace = await self._identities.get_workspace(workspace_id)
        if workspace is None or workspace.archived:
            raise PermissionDeniedError
        if identity.token_workspace_id is not None and identity.token_workspace_id != workspace_id:
            raise ScopeViolationError
        if identity.actor_kind is ActorKind.SERVICE and identity.auth_method != "pat":
            if identity.service_identity_id is None:
                raise AuthenticationRequiredError
            service = await self._identities.get_service_identity(
                workspace_id, identity.service_identity_id
            )
            if service is None or not service.active:
                raise AuthenticationRequiredError
            actor_id = service.id
            permissions = permissions_for(Role.SERVICE, service.permissions)
        else:
            user = await self._identities.find_user(identity.issuer, identity.subject)
            if user is None or not user.active:
                raise AuthenticationRequiredError
            membership = await self._identities.get_membership(workspace_id, user.id)
            if membership is None or not membership.active:
                raise PermissionDeniedError
            actor_id = user.id
            permissions = permissions_for(membership.role)
        if identity.token_permissions is not None:
            permissions = permissions.intersection(identity.token_permissions)
        return SecurityContext(
            actor_id=actor_id,
            actor_kind=identity.actor_kind,
            workspace_id=workspace_id,
            permissions=permissions,
            policy_version=POLICY_VERSION,
            correlation=correlation,
            project_id=identity.token_project_id,
            auth_method=identity.auth_method,
            session_id=identity.credential_id
            if identity.auth_method in {"local", "oidc"}
            else None,
            credential_id=identity.credential_id,
        )


class AuthorizationService:
    """Single fail-closed authorization service used by every capability."""

    def __init__(
        self, audit: AuditRecorder, clock: Clock, scope_access: ScopeAccess | None = None
    ) -> None:
        self._audit = audit
        self._clock = clock
        self._scope_access = scope_access

    async def authorize(self, request: AuthorizationRequest) -> None:
        """Record and enforce scope before permission; audit failure blocks the action."""
        context = request.context
        resource = request.resource
        if context.workspace_id != resource.workspace_id or (
            context.project_id is not None and context.project_id != resource.project_id
        ):
            await self.reject(request, ScopeViolationError(), reason_code="scope_mismatch")
        if request.permission.value not in context.permissions:
            await self.reject(request, PermissionDeniedError(), reason_code="permission_missing")
        if self._scope_access is not None and not await self._scope_access.allows(
            context, resource, request.permission.value
        ):
            await self.reject(request, PermissionDeniedError(), reason_code="live_scope_denied")
        await self._record(request, "allowed", "policy_allow")

    async def can_access(self, request: AuthorizationRequest) -> bool:
        context, resource = request.context, request.resource
        if context.workspace_id != resource.workspace_id or (
            context.project_id is not None and context.project_id != resource.project_id
        ):
            return False
        if request.permission.value not in context.permissions:
            return False
        return self._scope_access is None or await self._scope_access.allows(
            context, resource, request.permission.value
        )

    async def hidden_projects(self, context: SecurityContext) -> frozenset[UUID]:
        return (
            frozenset()
            if self._scope_access is None
            else await self._scope_access.hidden_projects(context)
        )

    async def reject(
        self,
        request: AuthorizationRequest,
        error: KernelError,
        *,
        reason_code: str,
    ) -> NoReturn:
        """Fail closed with one explicit denied audit decision."""
        await self._record(request, "denied", reason_code)
        raise error

    async def _record(self, request: AuthorizationRequest, result: str, reason_code: str) -> None:
        context = request.context
        correlation_id = UUID(context.correlation.request_id)
        await self._audit.append(
            AuditEvent(
                id=uuid4(),
                workspace_id=request.resource.workspace_id,
                actor_id=context.actor_id,
                actor_kind=context.actor_kind.value,
                action=request.permission.value,
                resource_type=request.resource.resource_type,
                resource_id=request.resource.resource_id,
                result=result,
                reason_code=reason_code,
                policy_version=context.policy_version,
                correlation_id=correlation_id,
                occurred_at=self._clock.now(),
                metadata={
                    "auth_method": context.auth_method,
                    "credential_id": str(context.credential_id) if context.credential_id else "-",
                },
            )
        )


class IdentityQueryService:
    """Expose authenticated workspace and membership reads through application policy."""

    def __init__(self, identities: IdentityReader, authorizer: AuthorizationService) -> None:
        self._identities = identities
        self._authorizer = authorizer

    async def get_workspace(self, context: SecurityContext, workspace_id: UUID) -> Workspace:
        """Read only the selected authenticated workspace."""
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.WORKSPACE_READ,
                ResourceScope(workspace_id, "workspace", str(workspace_id)),
            )
        )
        workspace = await self._identities.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError
        return workspace

    async def list_memberships(
        self, context: SecurityContext, workspace_id: UUID, page: PageRequest
    ) -> Page[Membership]:
        """Return a bounded page after server-owned workspace authorization."""
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.WORKSPACE_READ,
                ResourceScope(workspace_id, "workspace", str(workspace_id)),
            )
        )
        return await self._identities.list_memberships(workspace_id, page)


_CONTROL_PERMISSIONS = {
    ControlRequestKind.OWNERSHIP_TRANSFER: Permission.OWNERSHIP_TRANSFER,
    ControlRequestKind.EXPORT: Permission.DATA_EXPORT,
    ControlRequestKind.ARCHIVE: Permission.DATA_ARCHIVE,
    ControlRequestKind.DELETE: Permission.DATA_DELETE_REQUEST,
}


class CreatorControlService:
    """Create and decide recoverable ownership/data-control requests."""

    def __init__(
        self,
        authorizer: AuthorizationService,
        requests: ControlRequestStore,
        clock: Clock,
        approval_policies: ApprovalPolicyPort | None = None,
    ) -> None:
        self._authorizer = authorizer
        self._requests = requests
        self._clock = clock
        self._approval_policies = approval_policies

    async def list_requests(self, context: SecurityContext) -> tuple[ControlRequest, ...]:
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.APPROVAL_DECIDE,
                ResourceScope(context.workspace_id, "control_requests", "list"),
            )
        )
        return await self._requests.list_requests(context.workspace_id)

    async def request(self, context: SecurityContext, draft: ControlRequestDraft) -> ControlRequest:
        """Persist intent only; this stage performs no destructive operation."""
        await self._authorizer.authorize(
            AuthorizationRequest(
                context=context,
                permission=_CONTROL_PERMISSIONS[draft.kind],
                resource=ResourceScope(
                    context.workspace_id, draft.resource_type, draft.resource_id
                ),
            )
        )
        created = ControlRequest(
            id=uuid4(),
            workspace_id=context.workspace_id,
            requested_by=context.actor_id,
            kind=draft.kind,
            resource_type=draft.resource_type,
            resource_id=draft.resource_id,
            change_code=draft.change_code,
            risk_code=draft.risk_code,
            status=ControlRequestStatus.PENDING,
            correlation_id=UUID(context.correlation.request_id),
            requested_at=self._clock.now(),
            approval_policy_ref=(await self._approval_policies.snapshot(context.workspace_id))
            if self._approval_policies
            else "legacy_dual_control",
        )
        await self._requests.add_request(created)
        return created

    async def decide(
        self,
        context: SecurityContext,
        request_id: UUID,
        decision: ApprovalDecision,
    ) -> HumanApproval:
        """Require an authorized human distinct from the request creator."""
        existing = await self._requests.get_request(context.workspace_id, request_id)
        authorization = AuthorizationRequest(
            context=context,
            permission=Permission.APPROVAL_DECIDE,
            resource=ResourceScope(
                context.workspace_id if existing is None else existing.workspace_id,
                "control_request",
                str(request_id),
            ),
        )
        if existing is None:
            await self._authorizer.reject(
                authorization,
                ScopeViolationError(),
                reason_code="control_request_unavailable",
            )
        if context.actor_kind is not ActorKind.USER:
            await self._authorizer.reject(
                authorization,
                PermissionDeniedError(),
                reason_code="human_actor_required",
            )
        if self._approval_policies is not None:
            await self._approval_policies.require_decision(
                context, existing.requested_by, existing.approval_policy_ref
            )
        if self._approval_policies is None and context.actor_id == existing.requested_by:
            await self._authorizer.reject(
                authorization,
                PermissionDeniedError(),
                reason_code="separation_of_duties",
            )
        if existing.status is not ControlRequestStatus.PENDING:
            await self._authorizer.reject(
                authorization,
                InvalidStateError("Only pending control requests can be decided."),
                reason_code="control_request_not_pending",
            )
        await self._authorizer.authorize(authorization)
        approval = HumanApproval(
            id=uuid4(),
            workspace_id=context.workspace_id,
            request_id=request_id,
            decided_by=context.actor_id,
            decision=decision,
            correlation_id=UUID(context.correlation.request_id),
            decided_at=self._clock.now(),
        )
        await self._requests.add_approval(approval)
        return approval
