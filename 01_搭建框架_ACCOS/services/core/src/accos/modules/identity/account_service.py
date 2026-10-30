"""Real local/session/PAT identity and creator-owned administration use cases."""

from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Callable
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from accos.kernel.errors import (
    AuthenticationRequiredError,
    ConfigurationError,
    InvalidRequestError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from accos.kernel.logging import current_correlation
from accos.kernel.security import ActorKind
from accos.kernel.shared_contracts import CapabilityRequirement, CapabilityStatus
from accos.modules.identity.account_ports import OidcFlow, StoredSecret
from accos.modules.identity.accounts import (
    CredentialView,
    MemberView,
    ScopeGrant,
    SessionInfo,
    TokenView,
    WorkspacePreferences,
    WorkspaceSettings,
)
from accos.modules.identity.application import AuthorizationRequest, ResourceScope
from accos.modules.identity.domain import AuthenticatedIdentity, Permission, Role, permissions_for
from accos.modules.identity.ports import AuditEvent

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.auth_settings import AuthSettings
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.account_ports import (
        AccountStore,
        OidcClient,
        SecretCipher,
        VerifiedCredential,
    )
    from accos.modules.identity.application import AuthorizationService
    from accos.modules.identity.ports import AuditRecorder, IdentityProvider, IdentityReader

PAT_SCOPES = frozenset(
    {
        "workspace:read",
        "project:read",
        "project:write",
        "data:export",
        "agent:run",
        "model:run",
        "tool:run",
    }
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def username_value(value: str) -> str:
    result = value.strip().casefold()
    if re.fullmatch(r"[a-z0-9][a-z0-9_.@-]{2,99}", result) is None:
        raise InvalidRequestError(
            "Usernames require 3–100 letters, digits, dots, @, hyphens or underscores."
        )
    return result


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    csrf: str
    info: SessionInfo


class AccountService:
    def __init__(
        self,
        store: AccountStore,
        authorizer: AuthorizationService,
        clock: Clock,
        settings: AuthSettings,
        cipher: SecretCipher,
        hash_password: Callable[[str], str],
        verify_password: Callable[[str, str], bool],
        external_secret: Callable[[str], str],
        oidc: OidcClient,
        audit: AuditRecorder | None = None,
    ) -> None:
        self.store, self.authorizer, self.clock = store, authorizer, clock
        self.config, self.cipher = settings, cipher
        self._hash_password, self._verify_password = hash_password, verify_password
        self._external_secret, self._oidc = external_secret, oidc
        self._audit = audit

    async def _record_auth(
        self,
        action: str,
        result: str,
        resource: str,
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> None:
        if self._audit is not None:
            await self._audit.append(
                AuditEvent(
                    uuid4(),
                    workspace_id or UUID(int=0),
                    user_id,
                    "user",
                    action,
                    "authentication",
                    resource,
                    result,
                    action,
                    "identity-auth-v2",
                    UUID(current_correlation().request_id),
                    self.clock.now(),
                    {},
                )
            )

    async def login_limit(self, client: str, username: str) -> None:
        # Both per-peer and per-account windows; supplied forwarding headers are never trusted.
        for key in ("peer:" + client, "account:" + username):
            if not await self.store.check_login_limit(digest(key), self.clock.now()):
                raise RateLimitExceededError(900)

    async def bootstrap(
        self, token: str, username: str, password: str, name: str, client: str
    ) -> IssuedSession:
        normalized = username_value(username)
        await self.login_limit(client, "bootstrap")
        if not self.config.bootstrap_digest:
            raise ConfigurationError(
                "Create the one-time bootstrap credential through the local installer."
            )
        if not secrets.compare_digest(digest(token), self.config.bootstrap_digest):
            await self._record_auth("auth.bootstrap", "denied", "bootstrap")
            raise AuthenticationRequiredError
        encoded = await asyncio.to_thread(self._hash_password, password)
        user_id = await self.store.bootstrap(
            normalized, encoded, name, self.clock.now(), self.config.adopt_workspace_id
        )
        return await self.issue_session(user_id, "local")

    async def login(self, username: str, password: str, client: str) -> IssuedSession:
        normalized = username_value(username)
        await self.login_limit(client, normalized)
        account = await self.store.password(normalized)
        if account is None:
            # Run the same expensive primitive without storing or logging the supplied password.
            await asyncio.to_thread(self._hash_password, secrets.token_urlsafe(24))
            await self._record_auth("auth.login", "denied", digest(normalized))
            raise AuthenticationRequiredError
        if not await asyncio.to_thread(self._verify_password, account[1], password):
            await self._record_auth("auth.login", "denied", digest(normalized))
            raise AuthenticationRequiredError
        return await self.issue_session(account[0], "local")

    async def issue_session(self, user_id: UUID, method: str) -> IssuedSession:
        token, csrf = "accos_session_" + secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = self.clock.now()
        expires = now + timedelta(hours=self.config.session_hours)
        session_id = await self.store.add_session(
            user_id, digest(token), digest(csrf), method, now, expires
        )
        choices = await self.store.workspaces(user_id)
        await self._record_auth(
            "auth.login", "allowed", str(session_id), user_id, choices[0].id if choices else None
        )
        return IssuedSession(
            token,
            csrf,
            SessionInfo(
                authenticated=True,
                oidc_configured=self.config.oidc_configured,
                user_id=user_id,
                session_id=session_id,
                expires_at=expires,
                csrf_token=csrf,
                workspaces=choices,
            ),
        )

    async def session(self, token: str | None, csrf: str | None) -> SessionInfo:
        verified = (
            None
            if not token
            else await self.store.verify(digest(token), "session", self.clock.now())
        )
        if verified is None:
            return SessionInfo(
                authenticated=False,
                bootstrap_required=not await self.store.bootstrapped(),
                oidc_configured=self.config.oidc_configured,
            )
        csrf_value = (
            csrf
            if csrf and await self.store.csrf_matches(verified.credential_id, digest(csrf))
            else None
        )
        return SessionInfo(
            authenticated=True,
            oidc_configured=self.config.oidc_configured,
            user_id=verified.user_id,
            session_id=verified.credential_id,
            expires_at=verified.expires_at,
            csrf_token=csrf_value,
            workspaces=await self.store.workspaces(verified.user_id),
        )

    async def require_cookie(self, token: str, csrf: str | None = None) -> VerifiedCredential:
        identity = await self.store.verify(digest(token), "session", self.clock.now())
        if identity is None or (
            csrf is not None
            and not await self.store.csrf_matches(identity.credential_id, digest(csrf))
        ):
            raise AuthenticationRequiredError
        return identity

    async def human(self, context: SecurityContext) -> None:
        if (
            context.actor_kind is not ActorKind.USER
            or context.auth_method not in {"local", "oidc"}
            or context.session_id is None
        ):
            raise PermissionDeniedError
        if not await self.store.session_active(
            context.session_id, context.actor_id, self.clock.now()
        ):
            raise AuthenticationRequiredError

    async def authorize(
        self, context: SecurityContext, permission: Permission, kind: str, identifier: str
    ) -> None:
        await self.authorizer.authorize(
            AuthorizationRequest(
                context, permission, ResourceScope(context.workspace_id, kind, identifier)
            )
        )

    async def read_settings(self, context: SecurityContext) -> WorkspaceSettings:
        await self.authorize(
            context, Permission.WORKSPACE_READ, "settings", str(context.workspace_id)
        )
        return await self.store.settings(context.workspace_id)

    async def save_settings(
        self, context: SecurityContext, expected: int, values: WorkspacePreferences
    ) -> WorkspaceSettings:
        await self.human(context)
        await self.authorize(
            context, Permission.MEMBERSHIP_MANAGE, "settings", str(context.workspace_id)
        )
        try:
            ZoneInfo(values.timezone)
        except ZoneInfoNotFoundError:
            raise InvalidRequestError("Unknown time zone.") from None
        return await self.store.save_settings(context.workspace_id, expected, values)

    async def change_password(
        self, context: SecurityContext, username: str, old: str, new: str
    ) -> None:
        await self.human(context)
        await self.login_limit(str(context.actor_id), username_value(username))
        account = await self.store.password(username_value(username))
        if (
            account is None
            or account[0] != context.actor_id
            or not await asyncio.to_thread(self._verify_password, account[1], old)
        ):
            raise AuthenticationRequiredError
        await self.store.replace_password(
            context.actor_id, await asyncio.to_thread(self._hash_password, new)
        )

    async def put_member(
        self,
        context: SecurityContext,
        issuer: str,
        subject: str,
        role: Role,
        active: bool,
        expected: int,
        password: str | None,
    ) -> MemberView:
        await self.human(context)
        await self.authorize(
            context, Permission.MEMBERSHIP_MANAGE, "member", digest(issuer + ":" + subject)
        )
        if role is Role.SERVICE:
            raise InvalidRequestError("Use scoped API tokens for machine access.")
        if issuer == "urn:accos:local":
            subject = username_value(subject)
        elif issuer != self.config.oidc_issuer or not self.config.oidc_configured or password:
            raise InvalidRequestError(
                "Members must use local accounts or the configured OIDC issuer."
            )
        encoded = (
            None if password is None else await asyncio.to_thread(self._hash_password, password)
        )
        return await self.store.put_member(
            context.workspace_id, issuer, subject, role, active, expected, encoded
        )

    async def put_grant(
        self, context: SecurityContext, grant: ScopeGrant, expected: int
    ) -> ScopeGrant:
        await self.human(context)
        await self.authorize(context, Permission.MEMBERSHIP_MANAGE, "scope_grant", str(grant.id))
        member = await self.store.member(context.workspace_id, grant.user_id)
        if grant.workspace_id != context.workspace_id or member is None or not member.active:
            raise PermissionDeniedError
        if not set(grant.permissions).issubset(permissions_for(member.role)):
            raise InvalidRequestError("A grant cannot exceed the member role.")
        return await self.store.put_grant(grant, expected)

    async def create_token(
        self,
        context: SecurityContext,
        name: str,
        scopes: tuple[str, ...],
        days: int,
        project_id: UUID | None,
    ) -> tuple[str, TokenView]:
        await self.human(context)
        await self.authorize(context, Permission.WORKSPACE_READ, "personal_token", "create")
        if (
            not scopes
            or not set(scopes).issubset(PAT_SCOPES & context.permissions)
            or not 1 <= days <= 90
        ):
            raise InvalidRequestError(
                "Choose explicit permitted scopes and a lifetime of 1–90 days."
            )
        now = self.clock.now()
        view = TokenView(
            id=uuid4(),
            name=name,
            scopes=tuple(sorted(set(scopes))),
            project_id=project_id,
            created_at=now,
            expires_at=now + timedelta(days=days),
            revoked=False,
        )
        token = "accos_pat_" + secrets.token_urlsafe(32)
        await self.store.add_token(context.workspace_id, context.actor_id, digest(token), view)
        return token, view

    async def put_credential(
        self,
        context: SecurityContext,
        credential_id: UUID,
        expected: int,
        name: str,
        value: str | None,
        external_ref: str | None,
        active: bool,
    ) -> CredentialView:
        await self.human(context)
        await self.authorize(
            context, Permission.MEMBERSHIP_MANAGE, "credential", str(credential_id)
        )
        version = expected + 1
        binding = f"credential://{context.workspace_id}/{credential_id}/{version}"
        ciphertext, key_id = None, None
        if active:
            if bool(value) == bool(external_ref):
                raise InvalidRequestError("Provide exactly one secret value or external reference.")
            if external_ref:
                self._external_secret(external_ref)
            else:
                ciphertext, key_id = self.cipher.encrypt(value or "", binding), self.cipher.active
        view = CredentialView(
            id=credential_id,
            name=name,
            version=version,
            secret_ref=binding,
            storage="external" if external_ref else "encrypted",
            active=active,
            key_id=key_id,
            updated_at=self.clock.now(),
        )
        return await self.store.put_secret(
            context.workspace_id, StoredSecret(view, ciphertext, external_ref), expected
        )

    async def resolve_secret(self, workspace_id: UUID, reference: str) -> str:
        match = re.fullmatch(
            r"credential://([0-9a-f-]{36})/([0-9a-f-]{36})/([1-9][0-9]*)", reference
        )
        if match is None or UUID(match[1]) != workspace_id:
            raise PermissionDeniedError
        secret = await self.store.secret(workspace_id, UUID(match[2]))
        if secret is None or not secret.view.active or secret.view.version != int(match[3]):
            raise ConfigurationError("Credential reference is missing, revoked or superseded.")
        if secret.external_ref:
            return self._external_secret(secret.external_ref)
        return self.cipher.decrypt(secret.ciphertext or "", secret.view.key_id or "", reference)

    async def rewrap_credentials(self, context: SecurityContext) -> tuple[CredentialView, ...]:
        await self.human(context)
        await self.authorize(context, Permission.MEMBERSHIP_MANAGE, "credentials", "rewrap")
        for view in await self.store.secrets(context.workspace_id):
            if view.active and view.storage == "encrypted" and view.key_id != self.cipher.active:
                value = await self.resolve_secret(context.workspace_id, view.secret_ref)
                # CAS per credential; resumable on conflict/failure, old key retained by installer.
                await self.put_credential(
                    context, view.id, view.version, view.name, value, None, True
                )
        return await self.store.secrets(context.workspace_id)

    async def oidc_start(self, client: str) -> tuple[str, str]:
        if not self.config.oidc_configured:
            raise ConfigurationError("OIDC is not configured; local login remains available.")
        await self.login_limit(client, "oidc")
        state, browser, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
        await self.store.add_oidc_flow(
            OidcFlow(
                digest(state),
                digest(browser),
                verifier,
                nonce,
                self.clock.now() + timedelta(minutes=5),
            )
        )
        return self._oidc.authorization_url(state, nonce, verifier), browser

    async def oidc_callback(self, state: str, code: str, browser: str) -> IssuedSession:
        flow = await self._consume_oidc_flow(state, browser)
        issuer, subject = await self._oidc.exchange(
            code, flow.verifier, flow.nonce, self.clock.now()
        )
        user_id = await self.store.oidc_user(issuer, subject)
        # Membership is provisioned by a local Owner; no email-based account linking or auto-Owner.
        if user_id is None or not await self.store.workspaces(user_id):
            raise PermissionDeniedError
        return await self.issue_session(user_id, "oidc")

    async def oidc_cancel(self, state: str, browser: str) -> None:
        """Consume only this browser's flow, including an IdP denial; never issue a session."""
        await self._consume_oidc_flow(state, browser)
        await self._record_auth("auth.oidc", "denied", "oidc_callback")

    async def _consume_oidc_flow(self, state: str, browser: str) -> OidcFlow:
        flow = await self.store.consume_oidc_flow(digest(state), digest(browser), self.clock.now())
        if flow is None:
            raise AuthenticationRequiredError
        return flow

    async def capabilities(self, context: SecurityContext) -> tuple[CapabilityStatus, ...]:
        await self.authorize(context, Permission.WORKSPACE_READ, "capabilities", "list")
        definitions = (
            ("identity.local", True, True),
            ("identity.oidc", True, self.config.oidc_configured),
            ("identity.credentials", True, self.cipher.configured),
            ("identity.pat", True, True),
            ("identity.approval", True, True),
            ("settings", True, True),
            ("models.real", False, False),
            ("evolution.promotion", False, False),
            ("collaboration", False, False),
            ("marketplace", False, False),
            ("media", False, False),
        )
        return tuple(
            CapabilityStatus(
                capability=name,
                enabled=implemented and configured,
                implementation="implemented" if implemented else "port_only",
                implementation_version="25.1.0" if implemented else None,
                configuration="configured" if configured else "missing",
                health="unknown",
                verification="untested",
                data="sufficient" if name == "identity.local" else "empty",
                requirements=()
                if configured
                else (
                    CapabilityRequirement(
                        code="CONFIG_REQUIRED" if implemented else "IMPLEMENTATION_PENDING",
                        kind="configuration" if implemented else "dependency",
                        message="请在设置中完成配置" if implemented else "后续施工步骤尚未完成",
                        configuration_path="/settings",
                    ),
                ),
            )
            for name, implemented, configured in definitions
        )


class PersistentIdentityProvider:
    def __init__(self, store: AccountStore, fallback: IdentityProvider) -> None:
        self._store, self._fallback = store, fallback

    async def authenticate(self, credential: str, *, now: datetime) -> AuthenticatedIdentity:
        if not credential.startswith(("accos_pat_", "accos_session_")):
            if await self._store.bootstrapped():
                raise AuthenticationRequiredError
            return await self._fallback.authenticate(credential, now=now)
        method = "pat" if credential.startswith("accos_pat_") else "session"
        verified = await self._store.verify(digest(credential), method, now)
        if verified is None:
            raise AuthenticationRequiredError
        return AuthenticatedIdentity(
            verified.issuer,
            verified.subject,
            ActorKind.SERVICE if method == "pat" else ActorKind.USER,
            auth_method=verified.method,
            credential_id=verified.credential_id,
            token_workspace_id=verified.workspace_id,
            token_permissions=verified.scopes,
            token_project_id=verified.project_id,
        )


class WorkspaceSecretProvider:
    """Existing model gateway port backed by the selected workspace's credential vault."""

    def __init__(self, accounts: AccountService) -> None:
        self._accounts = accounts

    async def credential_for(self, provider_id: str) -> str | None:
        from accos.kernel.security import current_security_context

        context = current_security_context()
        await self._accounts.authorize(
            context, Permission.MODEL_RUN, "model_credential", provider_id
        )
        if provider_id.startswith("credential://"):
            return await self._accounts.resolve_secret(context.workspace_id, provider_id)
        for view in await self._accounts.store.secrets(context.workspace_id):
            if view.name == provider_id and view.active:
                return await self._accounts.resolve_secret(context.workspace_id, view.secret_ref)
        return None


class ApprovalPolicyResolver:
    def __init__(self, accounts: AccountService) -> None:
        self._accounts = accounts

    async def snapshot(self, workspace_id: UUID) -> str:
        settings = await self._accounts.store.settings(workspace_id)
        return f"workspace:{workspace_id}:v{settings.version}"

    async def require_decision(self, context: object, requested_by: UUID, policy_ref: str) -> None:
        from accos.kernel.security import SecurityContext

        if not isinstance(context, SecurityContext):
            raise PermissionDeniedError
        await self._accounts.human(context)
        member = await self._accounts.store.member(context.workspace_id, context.actor_id)
        if member is None or not member.active or member.role is not Role.OWNER:
            raise PermissionDeniedError
        mode = "dual_control"
        if policy_ref != "legacy_dual_control":
            match = re.fullmatch(r"workspace:([0-9a-f-]{36}):v([0-9]+)", policy_ref)
            if match is None or UUID(match[1]) != context.workspace_id:
                raise PermissionDeniedError
            mode = (
                await self._accounts.store.settings(context.workspace_id, int(match[2]))
            ).values.approval_mode
        if mode == "dual_control" and context.actor_id == requested_by:
            raise PermissionDeniedError


class LiveScopeAccess:
    """Re-read membership and explicit restricted-scope grants before domain access."""

    def __init__(self, store: AccountStore, clock: Clock, identities: IdentityReader) -> None:
        self._store, self._clock, self._identities = store, clock, identities

    async def allows(
        self, context: SecurityContext, resource: ResourceScope, permission: str
    ) -> bool:
        workspace = await self._identities.get_workspace(context.workspace_id)
        if workspace is None or workspace.archived:
            return False
        if context.auth_method in {"local", "oidc"} and (
            context.session_id is None
            or not await self._store.session_active(
                context.session_id, context.actor_id, self._clock.now()
            )
        ):
            return False
        if context.actor_kind is ActorKind.SERVICE and context.auth_method != "pat":
            service = await self._identities.get_service_identity(
                context.workspace_id, context.actor_id
            )
            return (
                service is not None
                and service.active
                and permission in permissions_for(Role.SERVICE, service.permissions)
            )
        if context.auth_method == "pat" and (
            context.credential_id is None
            or not await self._store.token_active(
                context.credential_id, context.workspace_id, context.actor_id, self._clock.now()
            )
        ):
            return False
        member = await self._store.member(context.workspace_id, context.actor_id)
        if member is None or not member.active or permission not in permissions_for(member.role):
            return False
        if resource.resource_type in {"creator", "universe"}:
            kind, identifier = resource.resource_type, resource.resource_id
        elif resource.project_id is not None:
            kind, identifier = "project", str(resource.project_id)
        else:
            return True
        if kind == "creator" and identifier == str(context.actor_id):
            return True
        grants = await self._store.grants(context.workspace_id)
        applicable = [g for g in grants if g.scope_kind == kind and str(g.scope_id) == identifier]
        if kind == "project" and (member.role is Role.OWNER or not applicable):
            return True
        return any(
            g.active and g.user_id == context.actor_id and permission in g.permissions
            for g in applicable
        )

    async def hidden_projects(self, context: SecurityContext) -> frozenset[UUID]:
        member = await self._store.member(context.workspace_id, context.actor_id)
        grants = await self._store.grants(context.workspace_id)
        if member is not None and member.active and member.role is Role.OWNER:
            return frozenset()
        restricted = {g.scope_id for g in grants if g.scope_kind == "project"}
        readable = {
            g.scope_id
            for g in grants
            if g.scope_kind == "project"
            and g.user_id == context.actor_id
            and g.active
            and "project:read" in g.permissions
        }
        return frozenset(restricted - readable)
