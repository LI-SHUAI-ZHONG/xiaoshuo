"""Provider-neutral model gateway contracts and policy values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from accos.kernel.contracts import IdempotencyKey, VersionNumber

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
MODEL_PROTOCOL_VERSION: Literal["models.v1"] = "models.v1"
PROMPT_POLICY_METADATA_PROTOCOL_VERSION = "prompt-policy-metadata.v1"


class ModelCapability(StrEnum):
    """Capabilities understood by the internal model protocol."""

    TEXT = "text"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    THREE_D = "3d"


class ModelCallStatus(StrEnum):
    """Sanitized outcomes persisted in the model usage ledger."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    TIMED_OUT = "timed_out"
    NOT_CONFIGURED = "not_configured"
    BUDGET_DENIED = "budget_denied"
    CIRCUIT_OPEN = "circuit_open"


class ModelErrorCode(StrEnum):
    """Stable model boundary failures; values are safe for task references."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    TIMED_OUT = "TIMED_OUT"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class ProviderHealthState(StrEnum):
    """Observable provider state without credentials or vendor payloads."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    OPEN = "open"
    NOT_CONFIGURED = "not_configured"


class MetadataKind(StrEnum):
    """Versioned metadata kinds; actual prompt text is outside this stage."""

    PROMPT = "prompt"
    POLICY = "policy"


class MetadataStatus(StrEnum):
    """Lifecycle for prompt and policy metadata references."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class PromptPolicyMetadata:
    """Content-free prompt/policy identity, version, checksum, and state."""

    metadata_id: str
    kind: MetadataKind
    version: str
    checksum: str
    status: MetadataStatus

    def __post_init__(self) -> None:
        if not self.metadata_id or self.metadata_id.strip() != self.metadata_id:
            raise ValueError("metadata id must be non-empty and trimmed")
        VersionNumber(self.version)
        if _CHECKSUM.fullmatch(self.checksum) is None:
            raise ValueError("metadata checksum must be a lowercase SHA-256 value")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Metadata-only request passed to every model provider."""

    capability: ModelCapability
    input_reference: str
    max_tokens: int
    idempotency_key: str
    workflow_run_id: UUID
    task_run_id: UUID
    metadata: PromptPolicyMetadata | None = None

    def __post_init__(self) -> None:
        IdempotencyKey(self.idempotency_key)
        if _REFERENCE.fullmatch(self.input_reference) is None:
            raise ValueError("model input must be a bounded opaque reference")
        if self.max_tokens < 1:
            raise ValueError("model max_tokens must be positive")


@dataclass(frozen=True, slots=True)
class ModelPolicy:
    """Explicit routing, resilience, concurrency, and shared budget policy."""

    allowed_provider_ids: tuple[str, ...]
    primary_provider_id: str
    backup_provider_ids: tuple[str, ...] = ()
    timeout_seconds: float = 1.0
    retries_per_provider: int = 1
    retry_backoff_seconds: float = 0.01
    total_attempt_limit: int = 4
    circuit_failure_threshold: int = 2
    circuit_cooldown_seconds: float = 30.0
    concurrency_limit: int = 2
    workspace_token_budget: int = 100_000
    task_token_budget: int = 4_096
    workspace_call_limit: int = 1_000
    task_call_limit: int = 16
    max_tokens_per_call: int = 1_024

    def __post_init__(self) -> None:
        route = (self.primary_provider_id, *self.backup_provider_ids)
        if not self.allowed_provider_ids or not self.primary_provider_id:
            raise ValueError("model policy requires an allowlist and primary provider")
        if len(set(route)) != len(route) or any(
            item not in self.allowed_provider_ids for item in route
        ):
            raise ValueError("model route must be unique and contained in the allowlist")
        if (
            self.timeout_seconds <= 0
            or self.retries_per_provider < 0
            or self.retry_backoff_seconds < 0
            or self.total_attempt_limit < 1
            or self.circuit_failure_threshold < 1
            or self.circuit_cooldown_seconds <= 0
            or self.concurrency_limit < 1
        ):
            raise ValueError("model resilience policy values are invalid")
        if (
            min(
                self.workspace_token_budget,
                self.task_token_budget,
                self.workspace_call_limit,
                self.task_call_limit,
                self.max_tokens_per_call,
            )
            < 1
        ):
            raise ValueError("model budgets and limits must be positive")

    @property
    def route(self) -> tuple[str, ...]:
        """Return the ordered primary/fallback route."""
        return (self.primary_provider_id, *self.backup_provider_ids)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Validated provider output before gateway attribution."""

    output_reference: str
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if _REFERENCE.fullmatch(self.output_reference) is None:
            raise ValueError("model output must be a bounded opaque reference")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("model usage cannot be negative")

    @property
    def total_tokens(self) -> int:
        """Return provider-neutral total usage."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Successful gateway result with provider and usage attribution."""

    call_id: UUID
    provider_id: str
    output_reference: str
    input_tokens: int
    output_tokens: int
    attempt: int

    @property
    def total_tokens(self) -> int:
        """Return total accounted tokens."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class UsageRecord:
    """Append-only model attempt and budget/audit evidence."""

    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    workflow_run_id: UUID
    task_run_id: UUID
    actor_id: UUID
    correlation_id: UUID
    idempotency_key: str
    capability: ModelCapability
    provider_id: str | None
    status: ModelCallStatus
    error_code: ModelErrorCode | None
    attempted: bool
    attempt: int
    input_tokens: int
    output_tokens: int
    started_at: datetime
    completed_at: datetime

    @property
    def total_tokens(self) -> int:
        """Return billable usage recorded for this attempt."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Credential-free circuit and concurrency snapshot."""

    provider_id: str
    state: ProviderHealthState
    consecutive_failures: int
    in_flight: int
    circuit_open_until: datetime | None


class ModelGatewayError(Exception):
    """Stable gateway failure with no provider exception details."""

    def __init__(self, code: ModelErrorCode) -> None:
        super().__init__(code.value)
        self.code = code
