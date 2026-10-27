"""Framework-free Agent descriptors, runs, snapshots, results, and limits."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.kernel.contracts import IdempotencyKey, VersionNumber

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.security import SecurityContext
    from accos.modules.models.invocation import ProfilePin, PromptPin

AGENT_PROTOCOL_VERSION = "agents.v1"
_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")


class AgentRunStatus(StrEnum):
    """Durable Agent invocation states with explicit bounded-failure outcomes."""

    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    BUDGET_EXHAUSTED = "budget_exhausted"
    LIMIT_EXCEEDED = "limit_exceeded"


class AgentResultKind(StrEnum):
    """Only metadata-bearing results may cross the Agent boundary."""

    WORKFLOW_SELECTION = "workflow_selection"
    WORKFLOW_PLAN_PROPOSAL = "workflow_plan_proposal"
    PROPOSAL = "proposal"
    DRAFT = "draft"
    PLAN = "plan"


class ProtectedOperation(StrEnum):
    """Operations that always require a durable human approval workflow step."""

    CANON = "canon"
    OWNERSHIP = "ownership"
    PERMISSION = "permission"
    PUBLISH = "publish"
    DELETE = "delete"


class RoleVersionStatus(StrEnum):
    """Lifecycle for editable and immutable workspace role versions."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class AgentErrorCode(StrEnum):
    """Stable, payload-free Agent failures."""

    UNKNOWN_AGENT = "UNKNOWN_AGENT"
    TOOL_DENIED = "TOOL_DENIED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    STEP_LIMIT_EXCEEDED = "STEP_LIMIT_EXCEEDED"
    RECURSION_LIMIT_EXCEEDED = "RECURSION_LIMIT_EXCEEDED"
    PARALLELISM_LIMIT_EXCEEDED = "PARALLELISM_LIMIT_EXCEEDED"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"
    LOOP_DETECTED = "LOOP_DETECTED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    CONTEXT_PACKAGE_INVALID = "CONTEXT_PACKAGE_INVALID"
    CONFIG_REQUIRED = "CONFIG_REQUIRED"
    MODEL_REFUSED = "MODEL_REFUSED"
    MODEL_INCOMPLETE = "MODEL_INCOMPLETE"
    MODEL_RESULT_UNKNOWN = "MODEL_RESULT_UNKNOWN"


@dataclass(frozen=True, slots=True)
class AgentBudget:
    """Hard execution ceiling; per-run values may only narrow it."""

    max_steps: int
    max_recursion_depth: int
    max_parallelism: int
    max_duration_seconds: float
    max_calls: int
    max_tokens: int

    def __post_init__(self) -> None:
        if (
            self.max_steps < 1
            or self.max_recursion_depth < 0
            or self.max_parallelism < 1
            or self.max_duration_seconds <= 0
            or self.max_calls < 1
            or self.max_tokens < 1
        ):
            raise ValueError("agent execution limits must be positive and bounded")

    def is_within(self, ceiling: AgentBudget) -> bool:
        """Return whether every value is no broader than the supplied ceiling."""
        return (
            self.max_steps <= ceiling.max_steps
            and self.max_recursion_depth <= ceiling.max_recursion_depth
            and self.max_parallelism <= ceiling.max_parallelism
            and self.max_duration_seconds <= ceiling.max_duration_seconds
            and self.max_calls <= ceiling.max_calls
            and self.max_tokens <= ceiling.max_tokens
        )

    def narrowed_with(self, other: AgentBudget) -> AgentBudget:
        """Intersect two trusted ceilings."""
        return AgentBudget(
            min(self.max_steps, other.max_steps),
            min(self.max_recursion_depth, other.max_recursion_depth),
            min(self.max_parallelism, other.max_parallelism),
            min(self.max_duration_seconds, other.max_duration_seconds),
            min(self.max_calls, other.max_calls),
            min(self.max_tokens, other.max_tokens),
        )


@dataclass(frozen=True, slots=True)
class PromptMetadataReference:
    """Content-free prompt metadata pinned into an Agent snapshot."""

    metadata_id: str
    version: str
    checksum: str

    def __post_init__(self) -> None:
        if not self.metadata_id or self.metadata_id.strip() != self.metadata_id:
            raise ValueError("prompt metadata id must be non-empty and trimmed")
        VersionNumber(self.version)
        if _CHECKSUM.fullmatch(self.checksum) is None:
            raise ValueError("prompt metadata checksum must be a lowercase SHA-256 value")


@dataclass(frozen=True, slots=True)
class AgentDescriptor:
    """Immutable content-free Agent registration contract."""

    agent_id: str
    version: str
    capabilities: tuple[str, ...]
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    allowed_tool_ids: tuple[str, ...]
    model_policy_id: str
    model_policy_version: str
    prompt_metadata: PromptMetadataReference
    budget_limit: AgentBudget

    def __post_init__(self) -> None:
        if not self.agent_id or self.agent_id.strip() != self.agent_id:
            raise ValueError("agent id must be non-empty and trimmed")
        VersionNumber(self.version)
        VersionNumber(self.model_policy_version)
        if not self.capabilities or any(
            not item or item.strip() != item for item in self.capabilities
        ):
            raise ValueError("agent descriptor requires named capabilities")
        if self.input_schema.get("type") != "object" or self.output_schema.get("type") != "object":
            raise ValueError("agent schemas must describe JSON objects")
        if not self.model_policy_id or self.model_policy_id.strip() != self.model_policy_id:
            raise ValueError("model policy id must be non-empty and trimmed")
        if len(set(self.allowed_tool_ids)) != len(self.allowed_tool_ids) or any(
            not item or item.strip() != item for item in self.allowed_tool_ids
        ):
            raise ValueError("allowed tool ids must be unique, non-empty, and trimmed")


@dataclass(frozen=True, slots=True)
class RoleDescriptorVersion:
    """Workspace-owned immutable role snapshot used only by newly started runs."""

    id: UUID
    workspace_id: UUID
    role_key: str
    role_version: int
    status: RoleVersionStatus
    descriptor: AgentDescriptor
    checksum: str
    created_by: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.role_key or self.role_key.strip() != self.role_key:
            raise ValueError("role key must be non-empty and trimmed")
        if self.role_version < 1:
            raise ValueError("role version must be positive")
        if self.descriptor.agent_id != self.role_key:
            raise ValueError("role key and Agent descriptor id must match")
        if _CHECKSUM.fullmatch(self.checksum) is None:
            raise ValueError("role checksum must be a lowercase SHA-256 value")


@dataclass(frozen=True, slots=True)
class RoleToolGrant:
    """Version-pinned tool authority for one published workspace role."""

    id: UUID
    workspace_id: UUID
    role_version_id: UUID
    tool_id: str
    tool_version: str
    permissions: tuple[str, ...]
    active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.tool_id or self.tool_id.strip() != self.tool_id:
            raise ValueError("role tool id must be non-empty and trimmed")
        VersionNumber(self.tool_version)
        if len(set(self.permissions)) != len(self.permissions) or any(
            not item or item.strip() != item for item in self.permissions
        ):
            raise ValueError("role tool permissions must be unique, non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class AgentInvocation:
    """One authorized request to a registered, stateless Agent."""

    agent_id: str
    input_data: dict[str, object]
    idempotency_key: str
    task_reference: str
    requested_budget: AgentBudget
    planned_steps: int = 1
    recursion_depth: int = 0
    requested_parallelism: int = 1
    planning_path: tuple[str, ...] = ()
    requested_tool_ids: tuple[str, ...] = ()
    workflow_run_id: UUID | None = None
    task_run_id: UUID | None = None
    context_package_reference: str | None = None
    model_policy: ProfilePin | None = None
    prompt: PromptPin | None = None

    def __post_init__(self) -> None:
        IdempotencyKey(self.idempotency_key)
        if not self.agent_id or self.agent_id.strip() != self.agent_id:
            raise ValueError("agent id must be non-empty and trimmed")
        if _REFERENCE.fullmatch(self.task_reference) is None:
            raise ValueError("agent task must be a bounded opaque reference")
        if self.planned_steps < 1 or self.recursion_depth < 0 or self.requested_parallelism < 1:
            raise ValueError("agent request bounds cannot be negative or zero")
        if len(set(self.requested_tool_ids)) != len(self.requested_tool_ids):
            raise ValueError("requested tools must be unique")
        if (
            self.context_package_reference is not None
            and not self.context_package_reference.startswith("memory-context://")
        ):
            raise ValueError("Agent context must be a Memory Context Package reference")


@dataclass(frozen=True, slots=True)
class AgentContextSnapshot:
    """Immutable replay evidence for an Agent execution."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    agent_id: str
    agent_version: str
    model_policy_id: str
    model_policy_version: str
    prompt_metadata_id: str
    prompt_metadata_version: str
    prompt_metadata_checksum: str
    tool_versions: tuple[str, ...]
    permission_snapshot: tuple[str, ...]
    input_digest: str
    created_at: datetime
    memory_context_package_id: UUID | None = None

    @property
    def reference(self) -> str:
        """Return the only context value passed outside Agent persistence."""
        return f"agent-context://{self.id}"


@dataclass(frozen=True, slots=True)
class WorkflowSelection:
    """Director output selecting one registered workflow version."""

    workflow_name: str
    workflow_version: int
    input_reference: str
    kind: AgentResultKind = AgentResultKind.WORKFLOW_SELECTION

    def __post_init__(self) -> None:
        if not self.workflow_name or self.workflow_name.strip() != self.workflow_name:
            raise ValueError("workflow selection name must be non-empty and trimmed")
        if self.workflow_version < 1 or _REFERENCE.fullmatch(self.input_reference) is None:
            raise ValueError("workflow selection version/reference is invalid")


@dataclass(frozen=True, slots=True)
class WorkflowPlanProposal:
    """Director proposal routed to approval before any protected operation."""

    workflow_name: str
    workflow_version: int
    input_reference: str
    protected_operations: tuple[ProtectedOperation, ...]
    approval_required: bool
    kind: AgentResultKind = AgentResultKind.WORKFLOW_PLAN_PROPOSAL

    def __post_init__(self) -> None:
        if not self.workflow_name or self.workflow_name.strip() != self.workflow_name:
            raise ValueError("workflow proposal name must be non-empty and trimmed")
        if self.workflow_version < 1 or _REFERENCE.fullmatch(self.input_reference) is None:
            raise ValueError("workflow proposal version/reference is invalid")
        if not self.protected_operations or len(set(self.protected_operations)) != len(
            self.protected_operations
        ):
            raise ValueError("workflow proposals require unique protected operations")
        if not self.approval_required:
            raise ValueError("protected workflow proposals must require human approval")


@dataclass(frozen=True, slots=True)
class AgentProposal:
    """Opaque proposal or draft returned by a non-Director Agent."""

    result_reference: str
    kind: AgentResultKind = AgentResultKind.PROPOSAL

    def __post_init__(self) -> None:
        if self.kind not in {AgentResultKind.PROPOSAL, AgentResultKind.DRAFT}:
            raise ValueError("agent result must be a proposal or draft")
        if _REFERENCE.fullmatch(self.result_reference) is None:
            raise ValueError("agent result must be a bounded opaque reference")


@dataclass(frozen=True, slots=True)
class AgentPlan:
    """A schema-validated DAG candidate in assets, consumed by the Workflow owner."""

    result_reference: str
    kind: AgentResultKind = AgentResultKind.PLAN

    def __post_init__(self) -> None:
        if _REFERENCE.fullmatch(self.result_reference) is None:
            raise ValueError("plan result must be an immutable content reference")


AgentResult = WorkflowSelection | WorkflowPlanProposal | AgentProposal | AgentPlan


@dataclass(frozen=True, slots=True)
class RawAgentResult:
    """Executor output validated and converted by the supervisor."""

    output_data: dict[str, object]
    result_reference: str
    model_calls: int
    tool_calls: int
    tokens: int

    def __post_init__(self) -> None:
        if _REFERENCE.fullmatch(self.result_reference) is None:
            raise ValueError("raw Agent result must be a bounded opaque reference")
        if min(self.model_calls, self.tool_calls, self.tokens) < 0:
            raise ValueError("Agent usage cannot be negative")

    @property
    def total_calls(self) -> int:
        """Count all external capability boundary calls."""
        return self.model_calls + self.tool_calls


@dataclass(frozen=True, slots=True)
class AgentExecution:
    """Trusted execution command passed to an AgentExecutor port."""

    run_id: UUID
    descriptor: AgentDescriptor
    snapshot: AgentContextSnapshot
    context: SecurityContext
    invocation: AgentInvocation
    budget: AgentBudget


@dataclass(frozen=True, slots=True)
class AgentRun:
    """Workspace-scoped durable Agent result and usage settlement."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    agent_id: str
    agent_version: str
    context_snapshot_id: UUID
    status: AgentRunStatus
    attempt: int
    idempotency_key: str
    task_reference: str
    requested_by: UUID
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime
    workflow_run_id: UUID | None = None
    result_kind: AgentResultKind | None = None
    result_reference: str | None = None
    workflow_name: str | None = None
    workflow_version: int | None = None
    protected_operations: tuple[ProtectedOperation, ...] = ()
    model_calls: int = 0
    tool_calls: int = 0
    tokens: int = 0
    error_code: AgentErrorCode | None = None


@dataclass(frozen=True, slots=True)
class AgentRunEvent:
    """Append-only Agent lifecycle event for audit and future SSE projection."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    agent_run_id: UUID
    sequence: int
    event_type: str
    version: int
    payload: dict[str, object]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class SupervisedAgentResult:
    """Supervisor response joining the durable run and typed safe result."""

    run: AgentRun
    result: AgentResult


class AgentRuntimeError(Exception):
    """Stable Agent boundary failure with no executor payload."""

    def __init__(self, code: AgentErrorCode) -> None:
        super().__init__(code.value)
        self.code = code
