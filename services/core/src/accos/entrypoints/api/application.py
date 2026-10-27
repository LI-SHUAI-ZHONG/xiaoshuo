"""FastAPI application factory and process-level HTTP contracts."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHttpException

from accos.composition import ApplicationContainer, build_container
from accos.entrypoints.api.v1 import router as v1_router
from accos.kernel.errors import (
    AuthenticationRequiredError,
    ErrorBody,
    ErrorCode,
    ErrorEnvelope,
    KernelError,
    ResourceNotFoundError,
    UnsupportedMediaTypeError,
    describe_exception,
)
from accos.kernel.ids import (
    CORRELATION_HEADER,
    REQUEST_ID_HEADER,
    TASK_ID_HEADER,
    TRACE_ID_HEADER,
    CorrelationIds,
    parse_id,
)
from accos.kernel.logging import (
    bind_correlation,
    configure_logging,
    current_correlation,
    get_logger,
    log_event,
    pseudonymous_ref,
    reset_correlation,
)
from accos.kernel.observability import SpanRecord, safe_metric_label
from accos.kernel.security import (
    bind_security_context,
    current_security_context,
    reset_security_context,
)
from accos.kernel.settings import RuntimeSettings, load_settings
from accos.modules.identity.application import AuthorizationRequest, ResourceScope
from accos.modules.identity.domain import Permission

RequestHandler = Callable[[Request], Awaitable[Response]]


class LiveResponse(BaseModel):
    """Stable liveness response model."""

    status: Literal["alive"]
    version: str
    timestamp: str


class DependencyCheckResponse(BaseModel):
    """Public state of one readiness dependency."""

    name: str
    status: str
    critical: bool
    detail: str


class ReadyResponse(BaseModel):
    """Stable readiness response model."""

    status: Literal["ready", "not_ready"]
    version: str
    timestamp: str
    checks: list[DependencyCheckResponse]


class IdentityContextResponse(BaseModel):
    """Non-secret current actor, workspace, and immutable permission snapshot."""

    actor_id: UUID
    actor_kind: str
    workspace_id: UUID
    permissions: list[str]
    policy_version: str


def create_app(  # noqa: PLR0915
    settings: RuntimeSettings | None = None,
    *,
    container: ApplicationContainer | None = None,
    configure_logs: bool = True,
    schema_only: bool = False,
) -> FastAPI:
    """Build an isolated application around the shared composition root."""
    selected_settings = settings or load_settings()
    runtime = (
        cast("ApplicationContainer", None)
        if schema_only
        else (container or build_container(selected_settings))
    )
    if configure_logs:
        configure_logging(
            selected_settings.optional.log_level,
            service="accos-api",
            environment=selected_settings.optional.environment,
        )
    logger = get_logger("http")

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        await runtime.startup()
        try:
            yield
        finally:
            await runtime.shutdown()

    app = FastAPI(
        title="ACCOS Core API",
        version="0.0.0",
        summary="Versioned creator-workspace API",
        description=(
            "The ACCOS modular-monolith HTTP boundary. All /api/v1 resource routes require "
            "a verified bearer identity and an X-Workspace-ID scope."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.container = runtime

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestHandler) -> Response:
        correlation = CorrelationIds.from_headers(request.headers)
        tokens = bind_correlation(correlation)
        security_token = None
        started_at = time.perf_counter()
        started_ns = time.time_ns()
        try:
            try:
                if request.url.path.startswith("/api/v1/"):
                    _require_host(request, selected_settings)
                    _require_json_content_type(request)
                    public_auth = request.url.path in PUBLIC_AUTH_PATHS
                    bearer = request.headers.get("Authorization")
                    cookie = request.cookies.get("accos_session")
                    if request.method not in {"GET", "HEAD", "OPTIONS"} and (cookie or public_auth):
                        _require_origin(request, selected_settings)
                    if not public_auth:
                        credential = _bearer_credential(request) if bearer else cookie
                        if not credential or (bearer and credential.startswith("accos_session_")):
                            raise AuthenticationRequiredError
                        if not bearer and request.method not in {"GET", "HEAD", "OPTIONS"}:
                            if runtime.identity.accounts is None:
                                raise AuthenticationRequiredError
                            await runtime.identity.accounts.require_cookie(
                                credential, request.headers.get("X-CSRF-Token", "")
                            )
                        context = await runtime.identity.authenticator.authenticate(
                            credential, _workspace_id(request), correlation
                        )
                        security_token = bind_security_context(context)
                response = await call_next(request)
            except Exception as error:  # noqa: BLE001 - outer HTTP boundary maps unknown failures.
                log_event(
                    logger,
                    logging.ERROR,
                    "unhandled_request_error",
                    error_type=type(error).__name__,
                )
                response = _error_response(error)
            _apply_response_headers(response, correlation)
            duration_seconds = time.perf_counter() - started_at
            route = _route_template(request)
            outcome = "success" if response.status_code < status.HTTP_400_BAD_REQUEST else "error"
            error_code = "-" if outcome == "success" else f"http_{response.status_code}"
            telemetry = runtime.observability.telemetry
            telemetry.increment(
                "accos_api_requests_total",
                method=safe_metric_label(request.method),
                route=safe_metric_label(route),
                status_class=f"{response.status_code // 100}xx",
                outcome=outcome,
            )
            telemetry.observe(
                "accos_api_request_duration_seconds",
                duration_seconds,
                method=safe_metric_label(request.method),
                route=safe_metric_label(route),
            )
            telemetry.record_span(
                SpanRecord(
                    name=f"{request.method} {route}",
                    trace_id=UUID(correlation.trace_id).hex,
                    span_id=secrets.token_hex(8),
                    start_unix_nano=started_ns,
                    end_unix_nano=time.time_ns(),
                    outcome=outcome,
                    attributes=(
                        ("http.request.method", request.method),
                        ("http.route", route),
                        ("http.response.status_code", response.status_code),
                        ("error.type", error_code),
                    ),
                )
            )
            log_event(
                logger,
                logging.INFO,
                "request_completed",
                method=request.method,
                path=route,
                status_code=response.status_code,
                duration_ms=round(duration_seconds * 1000, 3),
                outcome=outcome,
                error_code=error_code,
                workspace_ref=_workspace_ref(request),
                project_ref=_project_ref(request),
            )
            return response
        finally:
            if security_token is not None:
                reset_security_context(security_token)
            reset_correlation(tokens)

    @app.exception_handler(KernelError)
    async def kernel_error_handler(_request: Request, error: KernelError) -> JSONResponse:
        return _error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        validation_error = KernelError(
            ErrorCode.INVALID_REQUEST,
            "Request validation failed.",
            status_code=422,
            details={"issue_count": len(error.errors())},
        )
        return _error_response(validation_error)

    @app.exception_handler(StarletteHttpException)
    async def http_error_handler(_request: Request, error: StarletteHttpException) -> JSONResponse:
        if error.status_code == 404:  # noqa: PLR2004 - Starlette's not-found status.
            return _error_response(ResourceNotFoundError())
        validation_error = KernelError(
            ErrorCode.INVALID_REQUEST,
            "The HTTP method is not supported for this resource.",
            status_code=error.status_code,
        )
        return _error_response(validation_error)

    @app.get("/live", response_model=LiveResponse)
    async def live() -> dict[str, str]:
        return runtime.health.liveness().as_dict()

    @app.get(
        "/ready",
        response_model=ReadyResponse,
        responses={503: {"model": ReadyResponse}},
    )
    async def ready() -> JSONResponse:
        report = await runtime.health.readiness()
        return JSONResponse(status_code=report.http_status, content=report.as_dict())

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        if not selected_settings.observability.metrics_enabled:
            return Response(status_code=404)
        await runtime.observability.monitor.refresh_metrics(runtime.observability.telemetry)
        return Response(
            runtime.observability.telemetry.registry.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get(
        "/api/v1/identity/context",
        response_model=IdentityContextResponse,
        deprecated=True,
    )
    async def identity_context(response: Response) -> IdentityContextResponse:
        context = current_security_context()
        await runtime.identity.authorizer.authorize(
            AuthorizationRequest(
                context=context,
                permission=Permission.WORKSPACE_READ,
                resource=ResourceScope(
                    context.workspace_id, "workspace", str(context.workspace_id)
                ),
            )
        )
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = '</api/v1/identity/me>; rel="successor-version"'
        return IdentityContextResponse(
            actor_id=context.actor_id,
            actor_kind=context.actor_kind.value,
            workspace_id=context.workspace_id,
            permissions=sorted(context.permissions),
            policy_version=context.policy_version,
        )

    from accos.entrypoints.api.v1.account_router import router as account_router
    from accos.entrypoints.api.v1.content_collections import router as content_router
    from accos.entrypoints.api.v1.model_router import router as model_router

    app.include_router(account_router)
    app.include_router(content_router)
    app.include_router(model_router)
    app.include_router(v1_router)
    return app


def _error_response(error: Exception) -> JSONResponse:
    descriptor = describe_exception(error)
    correlation = current_correlation()
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=descriptor.code,
            message=descriptor.message,
            correlation_id=correlation.request_id,
            trace_id=correlation.trace_id,
            details=descriptor.details,
        )
    )
    response = JSONResponse(
        status_code=descriptor.status_code,
        content=envelope.model_dump(mode="json"),
    )
    if descriptor.code is ErrorCode.AUTHENTICATION_REQUIRED:
        response.headers["WWW-Authenticate"] = "Bearer"
    retry_after = descriptor.details.get("retry_after_seconds")
    if isinstance(retry_after, int):
        response.headers["Retry-After"] = str(retry_after)
    return response


def _require_json_content_type(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return
    if request.headers.get("Content-Length") in {None, "0"}:
        return
    media_type = request.headers.get("Content-Type", "").partition(";")[0].lower()
    if media_type != "application/json":
        raise UnsupportedMediaTypeError


PUBLIC_AUTH_PATHS = frozenset(
    {
        "/api/v1/auth/session",
        "/api/v1/auth/bootstrap",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/oidc/start",
        "/api/v1/auth/oidc/callback",
    }
)


def _require_host(request: Request, settings: RuntimeSettings) -> None:
    host = urlsplit("//" + request.headers.get("host", "")).hostname
    if host is None or host.lower() not in {h.strip("[]") for h in settings.auth.allowed_hosts}:
        raise AuthenticationRequiredError


def _require_origin(request: Request, settings: RuntimeSettings) -> None:
    if request.headers.get("origin") != settings.auth.public_origin:
        raise AuthenticationRequiredError


def _bearer_credential(request: Request) -> str:
    scheme, separator, credential = request.headers.get("Authorization", "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not credential:
        raise AuthenticationRequiredError
    return credential


def _workspace_id(request: Request) -> UUID:
    try:
        return parse_id(request.headers.get("X-Workspace-ID", ""))
    except ValueError:
        raise AuthenticationRequiredError from None


def _apply_response_headers(response: Response, correlation: CorrelationIds) -> None:
    response.headers[CORRELATION_HEADER] = correlation.request_id
    response.headers[REQUEST_ID_HEADER] = correlation.request_id
    response.headers[TRACE_ID_HEADER] = correlation.trace_id
    if correlation.task_id is not None:
        response.headers[TASK_ID_HEADER] = correlation.task_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def _workspace_ref(request: Request) -> str:
    try:
        workspace_id = parse_id(request.headers.get("X-Workspace-ID", ""))
    except ValueError:
        return "-"
    return pseudonymous_ref("workspace", workspace_id)


def _project_ref(request: Request) -> str:
    project_id = request.path_params.get("project_id")
    return "-" if project_id is None else pseudonymous_ref("project", project_id)
