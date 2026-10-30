"""Shared authenticated request dependencies for every v1 resource router."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, cast
from uuid import UUID  # noqa: TC003 - FastAPI resolves dependency annotations at runtime.

from fastapi import Depends, Header, Query, Request

from accos.kernel.contracts import DEFAULT_PAGE_LIMIT, IdempotencyKey, PageRequest
from accos.kernel.errors import (
    InvalidRequestError,
    PreconditionRequiredError,
    RateLimitExceededError,
    ScopeViolationError,
)
from accos.kernel.security import SecurityContext, current_security_context

if TYPE_CHECKING:
    from accos.composition import ApplicationContainer

_ETAG = re.compile(r'^"([1-9]\d*)"$')
_CURSOR_BYTES = 8


@dataclass(frozen=True, slots=True)
class ApiPageRequest:
    page: PageRequest
    cursor: str | None


def application_container(request: Request) -> object:
    """Return the composition root selected by the application factory."""
    return request.app.state.container


def api_context(
    x_workspace_id: Annotated[UUID, Header(alias="X-Workspace-ID")],
) -> SecurityContext:
    """Bind the documented workspace header to the verified server context."""
    context = current_security_context()
    if x_workspace_id != context.workspace_id:
        raise ScopeViolationError
    return context


async def enforce_rate_limit(
    request: Request,
    context: Annotated[SecurityContext, Depends(api_context)],
    container: Annotated[object, Depends(application_container)],
) -> None:
    """Apply the configured limiter to the route template, never a raw resource ID."""
    route = request.scope.get("route")
    action = getattr(route, "path", "/api/v1")
    runtime = cast("ApplicationContainer", container)
    decision = await runtime.identity.rate_limiter.check(context, f"{request.method} {action}")
    if not decision.allowed:
        raise RateLimitExceededError(decision.retry_after_seconds)


def require_selected_workspace(
    workspace_id: UUID,
    context: Annotated[SecurityContext, Depends(api_context)],
) -> UUID:
    """Reject a forged path scope before any use case is invoked."""
    if workspace_id != context.workspace_id:
        raise ScopeViolationError
    return workspace_id


def pagination(
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = DEFAULT_PAGE_LIMIT,
) -> ApiPageRequest:
    """Decode the opaque transport cursor into the framework-neutral page contract."""
    offset = 0 if cursor is None else decode_cursor(cursor)
    return ApiPageRequest(PageRequest(offset, limit), cursor)


def encode_cursor(offset: int) -> str:
    """Encode a non-negative offset without exposing it as an API parameter."""
    if offset < 0:
        raise ValueError("cursor offset must be non-negative")
    raw = offset.to_bytes(_CURSOR_BYTES, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_cursor(value: str) -> int:
    """Decode only canonical eight-byte cursor values."""
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError):
        raise InvalidRequestError("The pagination cursor is invalid.") from None
    if len(raw) != _CURSOR_BYTES or encode_cursor(int.from_bytes(raw, "big")) != value:
        raise InvalidRequestError("The pagination cursor is invalid.")
    return int.from_bytes(raw, "big")


def idempotency_key(
    value: Annotated[str, Header(alias="Idempotency-Key")],
) -> str:
    """Validate the common scoped idempotency header."""
    try:
        return IdempotencyKey(value).value
    except ValueError as error:
        raise InvalidRequestError(str(error)) from None


def if_match_version(
    value: Annotated[str | None, Header(alias="If-Match")] = None,
) -> int:
    """Require a strong integer ETag for every versioned mutation."""
    if value is None:
        raise PreconditionRequiredError
    match = _ETAG.fullmatch(value)
    if match is None:
        raise InvalidRequestError('If-Match must contain a strong integer ETag such as "1".')
    return int(match.group(1))


def etag(version: int) -> str:
    """Serialize an aggregate version as a strong ETag."""
    return f'"{version}"'
