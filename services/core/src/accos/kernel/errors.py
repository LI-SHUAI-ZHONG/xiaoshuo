"""Safe structured error contracts independent of web frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    """Stable machine-readable error codes."""

    CONFIGURATION_ERROR = "configuration_error"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    CONCURRENCY_CONFLICT = "concurrency_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PERMISSION_DENIED = "permission_denied"
    SCOPE_VIOLATION = "scope_violation"
    RATE_LIMITED = "rate_limited"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PRECONDITION_REQUIRED = "precondition_required"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    EVENT_CURSOR_EXPIRED = "event_cursor_expired"
    INTERNAL_ERROR = "internal_error"


class ErrorBody(BaseModel):
    """Public error details returned by inbound adapters."""

    code: ErrorCode
    message: str
    correlation_id: str
    trace_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """Stable top-level error response."""

    error: ErrorBody


@dataclass(frozen=True, slots=True)
class ErrorDescriptor:
    """Framework-neutral description of a public error."""

    code: ErrorCode
    message: str
    status_code: int
    details: dict[str, object]


class KernelError(Exception):
    """Base class for expected runtime errors safe to expose."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.status_code = status_code
        self.details = {} if details is None else details


class ConfigurationError(KernelError):
    """Raised when runtime configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.CONFIGURATION_ERROR, message, status_code=500)


class InvalidRequestError(KernelError):
    """Raised when validated application input is unsafe or malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.INVALID_REQUEST, message, status_code=400)


class InvalidStateError(KernelError):
    """Raised when an operation violates a runtime state transition."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.INVALID_STATE, message, status_code=409)


class ConcurrencyConflictError(KernelError):
    """Raised when an optimistic-lock version no longer matches."""

    def __init__(self, current_version: int | None = None) -> None:
        details: dict[str, object] = {}
        if current_version is not None:
            details["current_version"] = current_version
        super().__init__(
            ErrorCode.CONCURRENCY_CONFLICT,
            "The record changed before this operation could be committed.",
            status_code=409,
            details=details,
        )


class IdempotencyConflictError(KernelError):
    """Raised when one scoped key is reused for a different request."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.IDEMPOTENCY_CONFLICT,
            "The idempotency key was already used for a different request.",
            status_code=409,
        )


class AuthenticationRequiredError(KernelError):
    """Raised when a protected boundary has no valid principal."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AUTHENTICATION_REQUIRED,
            "Valid authentication is required.",
            status_code=401,
        )


class PermissionDeniedError(KernelError):
    """Raised when the current actor lacks an explicitly granted permission."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.PERMISSION_DENIED,
            "The requested action is not permitted.",
            status_code=403,
        )


class ScopeViolationError(KernelError):
    """Raised when a resource falls outside the selected workspace or project."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.SCOPE_VIOLATION,
            "The requested resource is outside the authorized scope.",
            status_code=403,
        )


class RateLimitExceededError(KernelError):
    """Raised when the configured request budget is exhausted."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        details: dict[str, object] = {}
        if retry_after_seconds is not None:
            details["retry_after_seconds"] = retry_after_seconds
        super().__init__(
            ErrorCode.RATE_LIMITED,
            "The request rate limit was exceeded.",
            status_code=429,
            details=details,
        )


class ResourceNotFoundError(KernelError):
    """Raised for a missing route or a safely scoped unavailable resource."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.RESOURCE_NOT_FOUND,
            "The requested resource was not found.",
            status_code=404,
        )


class PreconditionRequiredError(KernelError):
    """Raised when a versioned write omits its If-Match precondition."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.PRECONDITION_REQUIRED,
            "An If-Match version is required for this operation.",
            status_code=428,
        )


class UnsupportedMediaTypeError(KernelError):
    """Raised when a request body is not encoded with the declared API media type."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            "Request bodies must use application/json.",
            status_code=415,
        )


class DependencyUnavailableError(KernelError):
    """Raised when a required external adapter cannot complete an operation."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.DEPENDENCY_UNAVAILABLE, message, status_code=503)


class EventCursorExpiredError(KernelError):
    """Raised when retained SSE history can no longer continue a client cursor."""

    def __init__(self, status_url: str) -> None:
        super().__init__(
            ErrorCode.EVENT_CURSOR_EXPIRED,
            "The event cursor is no longer available.",
            status_code=409,
            details={"recovery": "refetch_status", "status_url": status_url},
        )


def describe_exception(error: Exception) -> ErrorDescriptor:
    """Map any exception without exposing unknown implementation details."""
    if isinstance(error, KernelError):
        return ErrorDescriptor(
            code=error.code,
            message=error.public_message,
            status_code=error.status_code,
            details=error.details,
        )
    return ErrorDescriptor(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred.",
        status_code=500,
        details={},
    )
