"""Content-bearing models.v2 contracts. V1 remains an explicit fixture protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from accos.kernel.errors import ErrorCode, KernelError
from accos.kernel.shared_contracts import ContentRef, SharedContract

Name = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$")]
OperationKey = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
CallStatus = Literal[
    "queued",
    "running",
    "completed",
    "refused",
    "incomplete",
    "cancelled",
    "failed",
    "unknown",
    "configuration_required",
    "budget_denied",
]
TERMINAL = frozenset(
    {
        "completed",
        "refused",
        "incomplete",
        "cancelled",
        "failed",
        "unknown",
        "configuration_required",
        "budget_denied",
    }
)


class ModelRuntimeError(KernelError):
    """Only stable codes cross the HTTP boundary; never include a vendor payload."""

    def __init__(self, reason: str, *, uncertain: bool = False, retryable: bool = False) -> None:
        super().__init__(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "Model execution could not complete.",
            status_code=503,
            details={"reason": reason, "billing_unknown": uncertain},
        )
        self.reason, self.uncertain, self.retryable = reason, uncertain, retryable


class ToolDefinition(SharedContract):
    name: Name
    description: Annotated[str, Field(max_length=2000)]
    parameters: dict[str, Any]


class ToolCall(SharedContract):
    call_id: Annotated[str, Field(min_length=1, max_length=200)]
    name: Name
    arguments: dict[str, Any]


class ModelMessage(SharedContract):
    role: Literal["system", "user", "assistant", "tool"]
    text: Annotated[str, Field(max_length=2_000_000)] | None = None
    content_ref: ContentRef | None = None
    call_id: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    provider_items: tuple[dict[str, Any], ...] = ()

    @model_validator(mode="after")
    def valid_message(self) -> Self:
        if self.text is not None and self.content_ref is not None:
            raise ValueError("Choose inline content or an immutable content reference")
        if self.text is None and self.content_ref is None and not self.tool_calls:
            raise ValueError("A message needs content")
        if (self.role == "tool") != (self.call_id is not None):
            raise ValueError("Tool results must carry their corresponding call ID")
        if self.tool_calls and self.role != "assistant":
            raise ValueError("Only assistant messages contain tool calls")
        if self.provider_items and (
            self.role != "assistant"
            or any(item.get("type") != "reasoning" for item in self.provider_items)
        ):
            raise ValueError("Only assistant reasoning continuation items are supported")
        return self


class ProfilePin(SharedContract):
    id: Name
    version: Annotated[int, Field(ge=1)]


class PromptPin(SharedContract):
    id: Name
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$", max_length=30)]
    checksum: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ModelInvocation(SharedContract):
    schema_version: Literal[2] = 2
    operation_key: OperationKey
    policy: ProfilePin
    messages: Annotated[tuple[ModelMessage, ...], Field(min_length=1, max_length=256)]
    task_kind: Name = "agent.task"
    prompt: PromptPin | None = None
    output_schema: dict[str, Any] | None = None
    tools: Annotated[tuple[ToolDefinition, ...], Field(max_length=32)] = ()
    max_output_tokens: Annotated[int, Field(ge=1, le=1_000_000)] = 2048
    parameters: dict[str, Any] = Field(default_factory=dict)
    privacy: Literal["local_only", "workspace"] = "local_only"
    stream: bool = False
    cache: bool = False
    workflow_run_id: UUID | None = None
    task_run_id: UUID | None = None
    context_package_id: UUID | None = None
    task_token_limit: Annotated[int, Field(ge=1, le=100_000_000)] | None = None
    task_call_limit: Annotated[int, Field(ge=1, le=1000)] | None = None
    continuation_profile: ProfilePin | None = None
    # Embeddings share authorization, quota, history and object persistence.
    kind: Literal["generate", "embed"] = "generate"

    @model_validator(mode="after")
    def tool_associations(self) -> Self:
        pending: set[str] = set()
        seen: set[str] = set()
        for message in self.messages:
            if pending and message.role != "tool":
                raise ValueError("Every tool call must have a result before the next message")
            for call in message.tool_calls:
                if call.call_id in seen:
                    raise ValueError("Duplicate tool call ID")
                seen.add(call.call_id)
                pending.add(call.call_id)
            if message.role == "tool":
                if message.call_id not in pending:
                    raise ValueError("Unmatched tool result")
                pending.remove(message.call_id)
        if pending or len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("Incomplete or duplicate tool declarations")
        if self.kind == "embed" and (self.tools or self.output_schema or self.stream):
            raise ValueError("Embedding requests do not use generation options")
        if any(m.provider_items for m in self.messages) and self.continuation_profile is None:
            raise ValueError("Provider continuation items require the original profile pin")
        return self


class TokenUsage(SharedContract):
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)] = 0
    cached_input_tokens: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def valid_cached_tokens(self) -> Self:
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("Cached tokens exceed input tokens")
        return self

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class ProviderOutput(SharedContract):
    status: Literal["completed", "refused", "incomplete"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    embeddings: tuple[tuple[float, ...], ...] = ()
    usage: TokenUsage | None = None
    provider_request_id: str | None = None

    finish_reason: str | None = None
    # Responses reasoning items (including encrypted content) remain in scoped assets,
    # only round-tripped to the same provider, never exposed as reasoning explanations.
    continuation: tuple[dict[str, Any], ...] = ()


class ProviderChunk(SharedContract):
    text: str = ""
    result: ProviderOutput | None = None
    provider_request_id: str | None = None


class CallRecord(SharedContract):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID
    status: CallStatus
    operation_key: str
    input_ref: ContentRef
    output_ref: ContentRef | None = None
    partial_ref: ContentRef | None = None
    policy: ProfilePin
    profile: ProfilePin | None = None
    prompt: PromptPin | None = None
    task_kind: str
    kind: Literal["generate", "embed"]
    created_at: datetime
    updated_at: datetime
    attempt_count: int = 0
    sequence: int = 0
    error_code: str | None = None
    usage: TokenUsage | None = None
    cost_micro_usd: int | None = None
    billing_status: Literal["not_started", "reserved", "settled", "unknown", "cached"] = (
        "not_started"
    )
    cache_source_id: UUID | None = None
    cancel_requested: bool = False
    duration_ms: int | None = None
    provider_request_id: str | None = None
    reservation_ids: tuple[UUID, ...] = ()
    workflow_run_id: UUID | None = None
    task_run_id: UUID | None = None


class CallEvent(SharedContract):
    call_id: UUID
    sequence: int
    status: CallStatus
    content_ref: ContentRef | None = None
    created_at: datetime


class CallPage(SharedContract):
    items: tuple[CallRecord, ...]
    next_cursor: str | None = None
