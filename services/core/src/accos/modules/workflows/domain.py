"""Framework-free workflow definitions, runs, tasks, approvals, and state rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.kernel.errors import InvalidStateError

SHA256_HEX_LENGTH = 64
MAX_STEP_ITERATIONS = 100

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.security import SecurityContext


class WorkflowRunStatus(StrEnum):
    """Durable workflow lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_RESOURCE = "waiting_resource"
    WAITING_CONFIGURATION = "waiting_configuration"
    WAITING_BUDGET = "waiting_budget"
    AWAITING_EXTERNAL_RESULT = "awaiting_external_result"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class StepRunStatus(StrEnum):
    """Durable step lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    STALE = "stale"
    AWAITING_EXTERNAL_RESULT = "awaiting_external_result"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunStatus(StrEnum):
    """Durable task lifecycle including manual dead-letter handling."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    UNKNOWN = "unknown"


class WorkflowDefinitionStatus(StrEnum):
    """Lifecycle for editable drafts and immutable published definitions."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ConditionOperator(StrEnum):
    """Bounded declarative conditions; no code or property traversal is allowed."""

    ALWAYS = "always"
    REFERENCE_PRESENT = "reference_present"
    STATUS_EQUALS = "status_equals"
    OUTPUT_REFERENCE_EQUALS = "output_reference_equals"


class RequirementFreshness(StrEnum):
    """How a required artifact version is compared at run preflight."""

    PINNED = "pinned"
    CURRENT = "current"
    MAX_AGE = "max_age"


class InputResolutionStatus(StrEnum):
    """Server-derived result of resolving one stage requirement."""

    READY = "ready"
    MISSING = "missing"
    UNAUTHORIZED = "unauthorized"
    STALE = "stale"
    NOT_ACCEPTED = "not_accepted"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


class ScheduleStatus(StrEnum):
    """Persistent schedule lifecycle."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class MisfirePolicy(StrEnum):
    """Explicit behavior when the application was unavailable at due time."""

    CATCH_UP = "catch_up"
    FIRE_ONCE = "fire_once"
    SKIP = "skip"


class CompensationStatus(StrEnum):
    """Durable outcome of one stable compensation operation."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class StepKind(StrEnum):
    """Technical step kinds available before domain workflows are introduced."""

    REFERENCE = "reference"
    DELAY = "delay"
    CONTROLLED_FAILURE = "controlled_failure"
    APPROVAL = "approval"


class ApprovalStatus(StrEnum):
    """Approval request lifecycle."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WorkflowApprovalDecision(StrEnum):
    """Explicit human decisions; absence never means approval."""

    APPROVE = "approve"
    REJECT = "reject"


class WorkerDisposition(StrEnum):
    """Observable result of one at-least-once queue delivery."""

    SUCCEEDED = "succeeded"
    RETRY_SCHEDULED = "retry_scheduled"
    DEAD_LETTERED = "dead_lettered"
    AWAITING_EXTERNAL_RESULT = "awaiting_external_result"
    CANCELLED = "cancelled"
    IGNORED = "ignored"


_RUN_TRANSITIONS: dict[WorkflowRunStatus, frozenset[WorkflowRunStatus]] = {
    WorkflowRunStatus.PENDING: frozenset(
        {
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.WAITING_RESOURCE,
            WorkflowRunStatus.WAITING_CONFIGURATION,
            WorkflowRunStatus.WAITING_BUDGET,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.RUNNING: frozenset(
        {
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.WAITING_APPROVAL,
            WorkflowRunStatus.WAITING_RESOURCE,
            WorkflowRunStatus.WAITING_CONFIGURATION,
            WorkflowRunStatus.WAITING_BUDGET,
            WorkflowRunStatus.AWAITING_EXTERNAL_RESULT,
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.PAUSED: frozenset(
        {
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.WAITING_APPROVAL,
            WorkflowRunStatus.WAITING_RESOURCE,
            WorkflowRunStatus.WAITING_CONFIGURATION,
            WorkflowRunStatus.WAITING_BUDGET,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.WAITING_APPROVAL: frozenset(
        {
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.AWAITING_EXTERNAL_RESULT,
            WorkflowRunStatus.WAITING_RESOURCE,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.WAITING_RESOURCE: frozenset(
        {
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.WAITING_CONFIGURATION: frozenset(
        {
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.WAITING_BUDGET: frozenset(
        {
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.AWAITING_EXTERNAL_RESULT: frozenset(
        {
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
        }
    ),
    WorkflowRunStatus.CANCELLING: frozenset({WorkflowRunStatus.CANCELLED}),
    WorkflowRunStatus.SUCCEEDED: frozenset(),
    WorkflowRunStatus.FAILED: frozenset(),
    WorkflowRunStatus.CANCELLED: frozenset(),
}


def ensure_run_transition(current: WorkflowRunStatus, target: WorkflowRunStatus) -> None:
    """Reject every transition not present in the explicit state graph."""
    if target not in _RUN_TRANSITIONS[current]:
        raise InvalidStateError(f"Workflow run cannot transition from {current} to {target}.")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded exponential retry policy."""

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    maximum_delay_seconds: float = 60.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if (
            self.max_attempts < 1
            or self.initial_delay_seconds <= 0
            or self.maximum_delay_seconds <= 0
            or self.multiplier < 1
        ):
            raise ValueError("retry policy values must be positive and bounded")
        if self.initial_delay_seconds > self.maximum_delay_seconds:
            raise ValueError("initial retry delay cannot exceed its maximum")

    def delay_after(self, attempt: int) -> float:
        """Return the capped delay after a failed one-based attempt."""
        if attempt < 1:
            raise ValueError("attempt must be positive")
        delay = self.initial_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(delay, self.maximum_delay_seconds)


@dataclass(frozen=True, slots=True)
class ConditionExpression:
    """One restricted predicate over a direct dependency's durable metadata."""

    operator: ConditionOperator = ConditionOperator.ALWAYS
    source_step_key: str | None = None
    expected_value: str | None = None

    def __post_init__(self) -> None:
        if self.operator is ConditionOperator.ALWAYS:
            if self.source_step_key is not None or self.expected_value is not None:
                raise ValueError("the always condition cannot reference a step or value")
            return
        if (
            self.source_step_key is None
            or not self.source_step_key
            or self.source_step_key.strip() != self.source_step_key
        ):
            raise ValueError("a conditional step requires a trimmed dependency key")
        if self.operator is ConditionOperator.REFERENCE_PRESENT:
            if self.expected_value is not None:
                raise ValueError("reference-present conditions do not accept an expected value")
            return
        if (
            self.expected_value is None
            or not self.expected_value
            or self.expected_value.strip() != self.expected_value
        ):
            raise ValueError("metadata equality conditions require a trimmed expected value")


@dataclass(frozen=True, slots=True)
class StageRequirement:
    """One server-resolved prerequisite for a workflow step."""

    key: str
    artifact_type: str
    scope: str
    branch: str | None = None
    accepted_required: bool = True
    min_schema: int = 1
    mandatory: bool = True
    freshness: RequirementFreshness = RequirementFreshness.CURRENT
    max_age_seconds: int | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.key, "key"),
            (self.artifact_type, "artifact type"),
            (self.scope, "scope"),
        ):
            if not value or value.strip() != value:
                raise ValueError(f"stage requirement {label} must be non-empty and trimmed")
        if self.branch is not None and (not self.branch or self.branch.strip() != self.branch):
            raise ValueError("stage requirement branch must be trimmed when present")
        if self.min_schema < 1:
            raise ValueError("stage requirement schema version must be positive")
        if self.freshness is RequirementFreshness.MAX_AGE:
            if self.max_age_seconds is None or self.max_age_seconds < 1:
                raise ValueError("max-age requirements require a positive age")
        elif self.max_age_seconds is not None:
            raise ValueError("only max-age requirements accept an age")


@dataclass(frozen=True, slots=True)
class ResolvedInput:
    """Authorized immutable artifact identity selected for one requirement."""

    requirement_key: str
    reference: str | None
    revision: str | None
    content_hash: str | None
    schema_version: int | None
    status: InputResolutionStatus
    resolved_at: datetime
    grant_version: str
    consent_version: str

    def __post_init__(self) -> None:
        if not self.requirement_key or self.requirement_key.strip() != self.requirement_key:
            raise ValueError("resolved input requirement key must be non-empty and trimmed")
        if self.status is InputResolutionStatus.READY:
            if not self.reference or not self.revision or self.schema_version is None:
                raise ValueError("ready inputs require a reference, revision and schema version")
            if (
                self.content_hash is None
                or len(self.content_hash) != SHA256_HEX_LENGTH
                or any(character not in "0123456789abcdef" for character in self.content_hash)
            ):
                raise ValueError("ready inputs require a lowercase SHA-256 content hash")
        elif any(
            value is not None
            for value in (self.reference, self.revision, self.content_hash, self.schema_version)
        ):
            raise ValueError("unresolved inputs cannot expose an untrusted partial identity")
        if not self.grant_version or not self.consent_version:
            raise ValueError("input resolution must snapshot grant and consent versions")


@dataclass(frozen=True, slots=True)
class StepInputManifest:
    """Immutable run-time pins and resolved references for one step."""

    id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    definition_id: UUID
    definition_version: int
    step_definition_id: UUID
    executor_key: str
    resolved_inputs: tuple[ResolvedInput, ...]
    prompt_pin: str | None
    model_pin: str | None
    policy_pin: str
    permission_version: str
    grant_version: str
    consent_version: str
    budget_reservation_ref: str | None
    input_digest: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.definition_version < 1:
            raise ValueError("input manifest definition version must be positive")
        if not self.executor_key or self.executor_key.strip() != self.executor_key:
            raise ValueError("input manifest executor key must be non-empty and trimmed")
        if len({item.requirement_key for item in self.resolved_inputs}) != len(
            self.resolved_inputs
        ):
            raise ValueError("input manifest requirements must be unique")
        if any(
            not value or value.strip() != value
            for value in (
                self.policy_pin,
                self.permission_version,
                self.grant_version,
                self.consent_version,
            )
        ):
            raise ValueError("input manifest policy and authorization pins are required")
        if len(self.input_digest) != SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in self.input_digest
        ):
            raise ValueError("input manifest digest must be a lowercase SHA-256 value")


@dataclass(frozen=True, slots=True)
class ReadReceipt:
    """Evidence that a pinned source span was actually loaded into model input."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    source_reference: str
    source_revision: str
    source_hash: str
    section_reference: str
    loaded_bytes: int
    token_count: int
    input_digest: str
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not value or value.strip() != value
            for value in (
                self.source_reference,
                self.source_revision,
                self.section_reference,
            )
        ):
            raise ValueError("read receipt references must be non-empty and trimmed")
        for value, label in (
            (self.source_hash, "source hash"),
            (self.input_digest, "input digest"),
        ):
            if len(value) != SHA256_HEX_LENGTH or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise ValueError(f"read receipt {label} must be a lowercase SHA-256 value")
        if self.loaded_bytes < 1 or self.token_count < 0:
            raise ValueError("read receipt byte/token counts are invalid")


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """Frozen producer-to-consumer relationship used for invalidation."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    consumer_run_id: UUID
    consumer_step_run_id: UUID
    producer_reference: str
    producer_revision: str
    producer_hash: str
    requirement_key: str
    created_at: datetime
    invalidated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CompensationRecord:
    """Idempotent compensation attempt linked to one task lease."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    task_run_id: UUID
    operation_key: str
    hook: str
    status: CompensationStatus
    created_at: datetime
    updated_at: datetime
    result_reference: str | None = None
    error_reference: str | None = None

    def __post_init__(self) -> None:
        if any(
            not value or value.strip() != value for value in (self.operation_key, self.hook)
        ):
            raise ValueError("compensation operation key and hook are required")


@dataclass(frozen=True, slots=True)
class WorkflowSchedule:
    """Persistent trigger for one published Workflow definition version."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    definition_id: UUID
    definition_name: str
    definition_version: int
    schedule_expression: str
    timezone: str
    misfire_policy: MisfirePolicy
    status: ScheduleStatus
    input_reference: str
    next_due_at: datetime
    requested_by: UUID
    idempotency_prefix: str
    created_at: datetime
    updated_at: datetime
    last_claimed_at: datetime | None = None
    last_run_id: UUID | None = None
    lease_token: UUID | None = None
    lease_until: datetime | None = None
    version: int = 1

    def __post_init__(self) -> None:
        if self.definition_version < 1 or self.version < 1:
            raise ValueError("schedule versions must be positive")
        if any(
            not value or value.strip() != value
            for value in (
                self.definition_name,
                self.schedule_expression,
                self.timezone,
                self.input_reference,
                self.idempotency_prefix,
            )
        ):
            raise ValueError("schedule string fields must be non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class StepDefinition:
    """One immutable step inside a versioned workflow definition."""

    id: UUID
    key: str
    position: int
    kind: StepKind
    timeout_seconds: float
    retry_policy: RetryPolicy
    delay_seconds: float = 0.0
    fail_until_attempt: int = 0
    approval_expires_seconds: float | None = None
    compensation_hook: str | None = None
    executor_key: str = "framework.default"
    depends_on: tuple[str, ...] = ()
    input_schema: dict[str, object] = field(default_factory=lambda: {"type": "object"})
    output_schema: dict[str, object] = field(default_factory=lambda: {"type": "object"})
    requirements: tuple[StageRequirement, ...] = ()
    condition: ConditionExpression = field(default_factory=ConditionExpression)
    budget_limit_microusd: int | None = None
    budget_reservation_required: bool = False
    approval_policy_ref: str | None = None
    max_iterations: int = 1
    external_side_effect: bool = False
    operation_key_template: str | None = None

    def __post_init__(self) -> None:  # noqa: PLR0912 - validates one immutable contract.
        maximum_name_length = 100
        if not self.key or self.key.strip() != self.key or len(self.key) > maximum_name_length:
            raise ValueError("step key must be non-empty, trimmed, and at most 100 characters")
        if self.position < 0 or self.timeout_seconds <= 0 or self.delay_seconds < 0:
            raise ValueError("step position and timing values are invalid")
        if not 0 <= self.fail_until_attempt < self.retry_policy.max_attempts:
            raise ValueError("controlled failures must remain below the maximum attempts")
        if self.kind is StepKind.APPROVAL:
            if self.approval_expires_seconds is None or self.approval_expires_seconds <= 0:
                raise ValueError("approval steps require a positive expiry")
        elif self.approval_expires_seconds is not None:
            raise ValueError("only approval steps can define an approval expiry")
        if self.compensation_hook is not None and (
            not self.compensation_hook or self.compensation_hook.strip() != self.compensation_hook
        ):
            raise ValueError("compensation hook must be trimmed when configured")
        if not self.executor_key or self.executor_key.strip() != self.executor_key:
            raise ValueError("step executor key must be non-empty and trimmed")
        if len(set(self.depends_on)) != len(self.depends_on) or any(
            not item or item.strip() != item for item in self.depends_on
        ):
            raise ValueError("step dependencies must be unique, non-empty and trimmed")
        if self.input_schema.get("type") != "object" or self.output_schema.get("type") != "object":
            raise ValueError("step input and output schemas must describe JSON objects")
        if len({item.key for item in self.requirements}) != len(self.requirements):
            raise ValueError("step requirement keys must be unique")
        if self.condition.source_step_key is not None and (
            self.condition.source_step_key not in self.depends_on
        ):
            raise ValueError("step condition source must be a direct dependency")
        if self.budget_limit_microusd is not None and self.budget_limit_microusd < 1:
            raise ValueError("step budget limit must be positive")
        if self.budget_reservation_required and self.budget_limit_microusd is None:
            raise ValueError("budget reservations require a step budget limit")
        if self.approval_policy_ref is not None and (
            not self.approval_policy_ref
            or self.approval_policy_ref.strip() != self.approval_policy_ref
        ):
            raise ValueError("approval policy reference must be trimmed when configured")
        if not 1 <= self.max_iterations <= MAX_STEP_ITERATIONS:
            raise ValueError("step iterations must be bounded between 1 and 100")
        if self.external_side_effect != (self.operation_key_template is not None):
            raise ValueError("external side effects require exactly one operation-key template")
        if self.operation_key_template is not None and (
            not self.operation_key_template
            or self.operation_key_template.strip() != self.operation_key_template
        ):
            raise ValueError("operation-key template must be trimmed")


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Immutable named definition whose version is part of its identity."""

    id: UUID
    name: str
    version: int
    steps: tuple[StepDefinition, ...]
    created_at: datetime
    graph_version: int = 1
    status: WorkflowDefinitionStatus = WorkflowDefinitionStatus.PUBLISHED
    description: str = ""
    checksum: str = ""

    def __post_init__(self) -> None:
        maximum_name_length = 100
        if not self.name or self.name.strip() != self.name or len(self.name) > maximum_name_length:
            raise ValueError("workflow name must be non-empty, trimmed, and at most 100 characters")
        if self.version < 1 or not self.steps:
            raise ValueError(
                "workflow definitions require a positive version and at least one step"
            )
        positions = tuple(step.position for step in self.steps)
        if positions != tuple(range(len(self.steps))):
            raise ValueError("workflow step positions must be contiguous and ordered")
        if len({step.key for step in self.steps}) != len(self.steps):
            raise ValueError("workflow step keys must be unique")
        if self.graph_version not in {1, 2}:
            raise ValueError("workflow graph version must be 1 or 2")
        if self.description.strip() != self.description:
            raise ValueError("workflow description must be trimmed")
        if self.checksum and (
            len(self.checksum) != SHA256_HEX_LENGTH
            or any(character not in "0123456789abcdef" for character in self.checksum)
        ):
            raise ValueError("workflow checksum must be a lowercase SHA-256 value")
        _validate_definition_graph(self)

    def dependencies_for(self, step: StepDefinition) -> tuple[str, ...]:
        """Return explicit v2 dependencies or the legacy linear adapter edge."""
        if self.graph_version == 1 and step.position > 0:
            return (self.steps[step.position - 1].key,)
        return step.depends_on


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    """Workspace/project-scoped durable workflow run."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    definition_id: UUID
    definition_name: str
    definition_version: int
    status: WorkflowRunStatus
    idempotency_key: str
    input_reference: str
    requested_by: UUID
    actor_kind: str
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime
    current_step_position: int = 0
    output_reference: str | None = None
    error_reference: str | None = None
    pause_requested_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    version: int = 1
    permission_snapshot: tuple[str, ...] = ()
    policy_version: str = ""
    approval_policy_ref: str = "legacy_dual_control"
    auth_method: str = "legacy"
    credential_id: UUID | None = None
    parent_run_id: UUID | None = None
    previous_run_id: UUID | None = None
    schedule_id: UUID | None = None
    iteration: int = 1


@dataclass(frozen=True, slots=True)
class StepRun:
    """Durable execution state for one definition step."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    step_definition_id: UUID
    step_key: str
    position: int
    status: StepRunStatus
    attempt: int
    input_reference: str
    created_at: datetime
    updated_at: datetime
    deadline: datetime | None = None
    output_reference: str | None = None
    error_reference: str | None = None
    version: int = 1
    input_manifest_id: UUID | None = None
    iteration: int = 1
    blocked_reason: str | None = None
    condition_result: bool | None = None


@dataclass(frozen=True, slots=True)
class TaskRun:
    """At-least-once queue task guarded by an idempotency key and lease."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    status: TaskRunStatus
    attempt: int
    idempotency_key: str
    input_reference: str
    available_at: datetime
    created_at: datetime
    updated_at: datetime
    deadline: datetime | None = None
    output_reference: str | None = None
    error_reference: str | None = None
    lease_token: UUID | None = None
    lease_expires_at: datetime | None = None
    last_delivery_event_id: UUID | None = None
    version: int = 1
    operation_key: str | None = None
    provider_job_id: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """Pending human approval with an explicit expiry and requester."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    requested_by: UUID
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    approval_policy_ref: str = "legacy_dual_control"
    input_digest: str = ""


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    """Append-only human approval decision and reason."""

    id: UUID
    workspace_id: UUID
    request_id: UUID
    actor_id: UUID
    decision: WorkflowApprovalDecision
    reason: str
    decided_at: datetime
    approval_policy_ref: str = "legacy_dual_control"
    input_digest: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowRunEvent:
    """Versioned run event with a per-run monotonically increasing sequence."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID
    sequence: int
    event_type: str
    version: int
    payload: dict[str, object]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ClaimedTask:
    """Task, run, and definition snapshot protected by one worker lease."""

    task: TaskRun
    run: WorkflowRun
    step_run: StepRun
    step: StepDefinition
    lease_token: UUID


@dataclass(frozen=True, slots=True)
class StepExecution:
    """Transport-neutral command passed to a technical step executor."""

    workflow_run_id: UUID
    task_run_id: UUID
    step_key: str
    kind: StepKind
    attempt: int
    idempotency_key: str
    input_reference: str
    delay_seconds: float
    fail_until_attempt: int
    context: SecurityContext | None = None
    operation_key: str | None = None
    input_manifest_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    """Metadata-only result of a technical step."""

    output_reference: str


class RetryableStepError(Exception):
    """Stable technical failure that may follow the bounded retry policy."""

    def __init__(self, error_reference: str) -> None:
        super().__init__(error_reference)
        self.error_reference = error_reference


class PermanentStepError(Exception):
    """Stable technical failure that must enter dead-letter handling immediately."""

    def __init__(self, error_reference: str) -> None:
        super().__init__(error_reference)
        self.error_reference = error_reference


class UnknownStepResultError(Exception):
    """External side effect may have happened and requires reconciliation."""

    def __init__(self, error_reference: str, provider_job_id: str | None = None) -> None:
        super().__init__(error_reference)
        self.error_reference = error_reference
        self.provider_job_id = provider_job_id


def _validate_definition_graph(definition: WorkflowDefinition) -> None:
    keys = {step.key for step in definition.steps}
    dependencies = {step.key: definition.dependencies_for(step) for step in definition.steps}
    for step_key, required in dependencies.items():
        if step_key in required or any(item not in keys for item in required):
            raise ValueError("workflow dependencies must reference other steps in the definition")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_key: str) -> None:
        if step_key in visiting:
            raise ValueError("workflow definition must be acyclic")
        if step_key in visited:
            return
        visiting.add(step_key)
        for dependency in dependencies[step_key]:
            visit(dependency)
        visiting.remove(step_key)
        visited.add(step_key)

    for key in keys:
        visit(key)
