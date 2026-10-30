"""Cookie-authenticated identity lifecycle and scoped administration HTTP boundary."""

from __future__ import annotations

import re
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import RedirectResponse

from accos.composition import ApplicationContainer
from accos.entrypoints.api.v1.account_schemas import (
    BootstrapInput,
    ControlDecisionInput,
    ControlRequestView,
    CredentialInput,
    GrantInput,
    IssuedTokenResponse,
    LoginInput,
    MemberInput,
    PasswordInput,
    SettingsExport,
    SettingsInput,
    TokenInput,
)
from accos.entrypoints.api.v1.dependencies import api_context, enforce_rate_limit
from accos.kernel.errors import (
    AuthenticationRequiredError,
    ConfigurationError,
    ConcurrencyConflictError,
    InvalidRequestError,
    PermissionDeniedError,
    PreconditionRequiredError,
)
from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import CapabilityStatus
from accos.modules.identity.account_service import AccountService, IssuedSession
from accos.modules.identity.accounts import (
    CreatorAnchor,
    CredentialView,
    MemberView,
    ScopeGrant,
    SessionInfo,
    SessionView,
    TokenView,
    WorkspaceSettings,
)
from accos.modules.identity.domain import ApprovalDecision, Permission

router = APIRouter(prefix="/api/v1", tags=["identity-administration"])
Context = Annotated[SecurityContext, Depends(api_context)]
Protected = [Depends(enforce_rate_limit)]


def accounts(request: Request) -> AccountService:
    value = cast("ApplicationContainer", request.app.state.container).identity.accounts
    if value is None:
        raise ConfigurationError("Identity runtime is not configured.")
    return value


Accounts = Annotated[AccountService, Depends(accounts)]


def account_version(value: Annotated[str | None, Header(alias="If-Match")] = None) -> int:
    if value is None:
        raise PreconditionRequiredError
    if re.fullmatch(r'"(0|[1-9][0-9]*)"', value) is None:
        raise InvalidRequestError('If-Match must be a strong integer ETag; use "0" for creation.')
    return int(value[1:-1])


ExpectedAccountVersion = Annotated[int, Depends(account_version)]


def match_body_version(header: int, body: int) -> int:
    if header != body:
        raise ConcurrencyConflictError
    return header


def peer(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def set_session(response: Response, issued: IssuedSession, service: AccountService) -> None:
    options = {
        "secure": service.config.secure_cookie,
        "samesite": "lax",
        "path": "/api/v1",
        "max_age": service.config.session_hours * 3600,
    }
    response.set_cookie("accos_session", issued.token, httponly=True, **options)  # type: ignore[arg-type]
    response.set_cookie("accos_csrf", issued.csrf, httponly=True, **options)  # type: ignore[arg-type]


@router.get("/auth/session", response_model=SessionInfo)
async def session_info(request: Request, service: Accounts) -> SessionInfo:
    return await service.session(
        request.cookies.get("accos_session"), request.cookies.get("accos_csrf")
    )


@router.post("/auth/bootstrap", response_model=SessionInfo, status_code=201)
async def bootstrap(
    body: BootstrapInput, request: Request, response: Response, service: Accounts
) -> SessionInfo:
    result = await service.bootstrap(
        body.bootstrap_token.get_secret_value(),
        body.username,
        body.password.get_secret_value(),
        body.workspace_name,
        peer(request),
    )
    set_session(response, result, service)
    return result.info


@router.post("/auth/login", response_model=SessionInfo)
async def login(
    body: LoginInput, request: Request, response: Response, service: Accounts
) -> SessionInfo:
    result = await service.login(body.username, body.password.get_secret_value(), peer(request))
    set_session(response, result, service)
    return result.info


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, service: Accounts) -> Response:
    verified = await service.require_cookie(
        request.cookies.get("accos_session", ""), request.headers.get("X-CSRF-Token", "")
    )
    await service.store.revoke_session(verified.user_id, verified.credential_id)
    response = Response(status_code=204)
    for name in ("accos_session", "accos_csrf", "accos_oidc"):
        response.delete_cookie(
            name, path="/api/v1", secure=service.config.secure_cookie, httponly=True, samesite="lax"
        )
    return response


@router.get("/auth/oidc/start", response_class=RedirectResponse, status_code=303)
async def oidc_start(request: Request, service: Accounts) -> RedirectResponse:
    url, browser = await service.oidc_start(peer(request))
    response = RedirectResponse(url, status_code=303)
    response.set_cookie(
        "accos_oidc",
        browser,
        path="/api/v1",
        max_age=300,
        secure=service.config.secure_cookie,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/auth/oidc/callback", response_class=RedirectResponse, status_code=303)
async def oidc_callback(
    request: Request,
    service: Accounts,
    state: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    code: Annotated[str | None, Query(min_length=1, max_length=4096)] = None,
    provider_error: Annotated[
        str | None, Query(alias="error", min_length=1, max_length=200)
    ] = None,
) -> RedirectResponse:
    result = None
    failure = "failed"
    try:
        if state is None or (code is None) == (provider_error is None):
            raise AuthenticationRequiredError
        browser = request.cookies.get("accos_oidc", "")
        if provider_error is not None:
            await service.oidc_cancel(state, browser)
            failure = "cancelled" if provider_error == "access_denied" else "provider_failed"
        elif code is not None:
            result = await service.oidc_callback(state, code, browser)
    except AuthenticationRequiredError:
        failure = "failed"
    except PermissionDeniedError:
        failure = "membership_required"
    except ConfigurationError:
        failure = "configuration_required"
    # Only fixed local error codes leave this boundary; never echo provider text, code or state.
    destination = "/dashboard" if result else "/login?auth_error=" + failure
    response = RedirectResponse(service.config.public_origin + destination, status_code=303)
    if result is not None:
        set_session(response, result, service)
    response.delete_cookie(
        "accos_oidc",
        path="/api/v1",
        secure=service.config.secure_cookie,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/auth/sessions", response_model=tuple[SessionView, ...], dependencies=Protected)
async def list_sessions(context: Context, service: Accounts) -> tuple[SessionView, ...]:
    await service.human(context)
    return await service.store.list_sessions(context.actor_id)


@router.delete("/auth/sessions/{session_id}", status_code=204, dependencies=Protected)
async def revoke_session(session_id: UUID, context: Context, service: Accounts) -> Response:
    await service.human(context)
    await service.authorize(context, Permission.WORKSPACE_READ, "session", str(session_id))
    await service.store.revoke_session(context.actor_id, session_id)
    return Response(status_code=204)


@router.post("/auth/password", status_code=204, dependencies=Protected)
async def change_password(body: PasswordInput, context: Context, service: Accounts) -> Response:
    await service.human(context)
    await service.authorize(context, Permission.WORKSPACE_READ, "password", str(context.actor_id))
    await service.change_password(
        context,
        body.username,
        body.password.get_secret_value(),
        body.new_password.get_secret_value(),
    )
    return Response(status_code=204)


@router.get("/identity/members", response_model=tuple[MemberView, ...], dependencies=Protected)
async def list_members(context: Context, service: Accounts) -> tuple[MemberView, ...]:
    await service.authorize(context, Permission.MEMBERSHIP_MANAGE, "members", "list")
    return await service.store.members(context.workspace_id)


@router.put("/identity/members", response_model=MemberView, dependencies=Protected)
async def put_member(
    body: MemberInput, context: Context, service: Accounts, expected: ExpectedAccountVersion
) -> MemberView:
    return await service.put_member(
        context,
        body.issuer,
        body.subject,
        body.role,
        body.active,
        match_body_version(expected, body.expected_version),
        None if body.password is None else body.password.get_secret_value(),
    )


@router.get("/identity/grants", response_model=tuple[ScopeGrant, ...], dependencies=Protected)
async def list_grants(context: Context, service: Accounts) -> tuple[ScopeGrant, ...]:
    await service.authorize(context, Permission.MEMBERSHIP_MANAGE, "scope_grants", "list")
    return await service.store.grants(context.workspace_id)


@router.put("/identity/grants", response_model=ScopeGrant, dependencies=Protected)
async def put_grant(
    body: GrantInput, context: Context, service: Accounts, expected: ExpectedAccountVersion
) -> ScopeGrant:
    return await service.put_grant(
        context, body.grant, match_body_version(expected, body.expected_version)
    )


@router.get("/identity/creator", response_model=CreatorAnchor, dependencies=Protected)
async def creator(context: Context, service: Accounts) -> CreatorAnchor:
    await service.human(context)
    await service.authorize(
        context, Permission.WORKSPACE_READ, "creator_identity", str(context.actor_id)
    )
    return await service.store.anchor(context.workspace_id, context.actor_id)


@router.get("/identity/tokens", response_model=tuple[TokenView, ...], dependencies=Protected)
async def tokens(context: Context, service: Accounts) -> tuple[TokenView, ...]:
    await service.human(context)
    return await service.store.tokens(context.workspace_id, context.actor_id)


@router.post(
    "/identity/tokens", response_model=IssuedTokenResponse, status_code=201, dependencies=Protected
)
async def create_token(
    body: TokenInput, context: Context, service: Accounts
) -> IssuedTokenResponse:
    token, record = await service.create_token(
        context, body.name, body.scopes, body.days, body.project_id
    )
    return IssuedTokenResponse(token=token, record=record)


@router.delete("/identity/tokens/{token_id}", status_code=204, dependencies=Protected)
async def revoke_token(token_id: UUID, context: Context, service: Accounts) -> Response:
    await service.human(context)
    await service.authorize(context, Permission.WORKSPACE_READ, "personal_token", str(token_id))
    await service.store.revoke_token(context.workspace_id, context.actor_id, token_id)
    return Response(status_code=204)


@router.get("/settings/workspace", response_model=WorkspaceSettings, dependencies=Protected)
async def settings(context: Context, service: Accounts, response: Response) -> WorkspaceSettings:
    result = await service.read_settings(context)
    response.headers["ETag"] = f'"{result.version}"'
    return result


@router.put("/settings/workspace", response_model=WorkspaceSettings, dependencies=Protected)
async def save_settings(
    body: SettingsInput,
    context: Context,
    service: Accounts,
    response: Response,
    expected: ExpectedAccountVersion,
) -> WorkspaceSettings:
    result = await service.save_settings(
        context, match_body_version(expected, body.expected_version), body.values
    )
    response.headers["ETag"] = f'"{result.version}"'
    return result


@router.get("/settings/export", response_model=SettingsExport, dependencies=Protected)
async def export_settings(context: Context, service: Accounts) -> SettingsExport:
    await service.authorize(context, Permission.MEMBERSHIP_MANAGE, "settings", "export")
    return SettingsExport(
        values=(await service.read_settings(context)).values,
        credentials=await service.store.secrets(context.workspace_id),
    )


@router.post("/settings/import", response_model=WorkspaceSettings, dependencies=Protected)
async def import_settings(
    body: SettingsInput, context: Context, service: Accounts, expected: ExpectedAccountVersion
) -> WorkspaceSettings:
    # Strict settings schema rejects secrets, arbitrary endpoints and unknown privilege settings.
    return await service.save_settings(
        context, match_body_version(expected, body.expected_version), body.values
    )


@router.get(
    "/settings/credentials", response_model=tuple[CredentialView, ...], dependencies=Protected
)
async def credentials(context: Context, service: Accounts) -> tuple[CredentialView, ...]:
    await service.authorize(context, Permission.MEMBERSHIP_MANAGE, "credentials", "list")
    return await service.store.secrets(context.workspace_id)


@router.put("/settings/credentials", response_model=CredentialView, dependencies=Protected)
async def put_credential(
    body: CredentialInput, context: Context, service: Accounts, expected: ExpectedAccountVersion
) -> CredentialView:
    return await service.put_credential(
        context,
        body.id,
        match_body_version(expected, body.expected_version),
        body.name,
        None if body.value is None else body.value.get_secret_value(),
        body.external_ref,
        body.active,
    )


@router.post(
    "/settings/credentials/rewrap",
    response_model=tuple[CredentialView, ...],
    dependencies=Protected,
)
async def rewrap_credentials(context: Context, service: Accounts) -> tuple[CredentialView, ...]:
    return await service.rewrap_credentials(context)


@router.get("/capabilities", response_model=tuple[CapabilityStatus, ...], dependencies=Protected)
async def capabilities(context: Context, service: Accounts, request: Request) -> tuple[CapabilityStatus, ...]:
    values = await service.capabilities(context)
    model = await cast("ApplicationContainer", request.app.state.container).models.runtime.capability(context)
    return tuple(model if value.capability == "models.real" else value for value in values)


@router.get(
    "/identity/control-requests",
    response_model=tuple[ControlRequestView, ...],
    dependencies=Protected,
)
async def control_requests(
    request: Request, context: Context, service: Accounts
) -> tuple[ControlRequestView, ...]:
    await service.authorize(context, Permission.APPROVAL_DECIDE, "control_requests", "list")
    runtime = cast("ApplicationContainer", request.app.state.container)
    rows = await runtime.identity.creator_control.list_requests(context)
    return tuple(
        ControlRequestView(
            id=r.id,
            requested_by=r.requested_by,
            kind=r.kind.value,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            status=r.status.value,
            approval_policy_ref=r.approval_policy_ref,
        )
        for r in rows
    )


@router.post(
    "/identity/control-requests/{request_id}/decision", status_code=204, dependencies=Protected
)
async def decide_control(
    request_id: UUID, body: ControlDecisionInput, request: Request, context: Context
) -> Response:
    runtime = cast("ApplicationContainer", request.app.state.container)
    await runtime.identity.creator_control.decide(
        context, request_id, ApprovalDecision(body.decision)
    )
    return Response(status_code=204)
