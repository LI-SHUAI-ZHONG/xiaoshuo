"""Stable cross-cutting contracts shared by ACCOS modules."""

from accos.kernel.errors import (
    AuthenticationRequiredError,
    ConcurrencyConflictError,
    ConfigurationError,
    ErrorCode,
    IdempotencyConflictError,
    InvalidStateError,
    KernelError,
    PermissionDeniedError,
    RateLimitExceededError,
    ScopeViolationError,
)
from accos.kernel.features import FeatureFlags
from accos.kernel.security import ActorKind, SecurityContext
from accos.kernel.settings import (
    OptionalSettings,
    RequiredSettings,
    RuntimeSettings,
    SecuritySettings,
    load_settings,
)

__all__ = [
    "ActorKind",
    "AuthenticationRequiredError",
    "ConcurrencyConflictError",
    "ConfigurationError",
    "ErrorCode",
    "FeatureFlags",
    "IdempotencyConflictError",
    "InvalidStateError",
    "KernelError",
    "OptionalSettings",
    "PermissionDeniedError",
    "RateLimitExceededError",
    "RequiredSettings",
    "RuntimeSettings",
    "ScopeViolationError",
    "SecurityContext",
    "SecuritySettings",
    "load_settings",
]
