"""Private SQLAlchemy models and atomic workflow state transitions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.idempotency import SqlAlchemyIdempotencyStore
from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.persistence import IdempotencyRecord
from accos.modules.workflows.domain import (
    ApprovalRecord,
    ApprovalRequest,
    ApprovalStatus,
    ClaimedTask,
    CompensationRecord,
    CompensationStatus,
    ConditionExpression,
    ConditionOperator,
    DependencyEdge,
    InputResolutionStatus,
    MisfirePolicy,
    ReadReceipt,
    RequirementFreshness,
    ResolvedInput,
    RetryPolicy,
    ScheduleStatus,
    StageRequirement,
    StepDefinition,
    StepInputManifest,
    StepKind,
    StepRun,
    StepRunStatus,
    TaskRun,
    TaskRunStatus,
    WorkflowApprovalDecision,
    WorkflowDefinition,
    WorkflowDefinitionStatus,
    WorkflowRun,
    WorkflowRunEvent,
    WorkflowRunStatus,
    WorkflowSchedule,
    ensure_run_transition,
)
from accos.modules.workflows.ports import FailureSettlement
from accos.modules.workflows.validation import condition_matches, manifest_digest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory


class WorkflowDefinitionRow(Base):
    """Immutable versioned workflow definition."""

    __tablename__ = "workflow_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkflowDefinitionStatus.PUBLISHED.value
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "definition_version", name="uq_workflow_definitions_name_version"),
        CheckConstraint("definition_version > 0", name="ck_workflow_definitions_version_positive"),
        CheckConstraint("graph_version IN (1, 2)", name="ck_workflow_definitions_graph_version"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflow_definitions_status_valid",
        ),
        {"schema": SCHEMA_NAME},
    )


class WorkflowStepDefinitionRow(Base):
    """Immutable ordered step within one definition version."""

    __tablename__ = "workflow_step_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_definitions.id", name="fk_workflow_steps_definition"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_delay_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_delay_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    retry_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    delay_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fail_until_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_expires_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    compensation_hook: Mapped[str | None] = mapped_column(String(200), nullable=True)
    executor_key: Mapped[str] = mapped_column(
        String(150), nullable=False, default="framework.default"
    )
    depends_on: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    input_schema: Mapped[dict[str, object]] = mapped_column(
        JSON_TYPE, nullable=False, default=lambda: {"type": "object"}
    )
    output_schema: Mapped[dict[str, object]] = mapped_column(
        JSON_TYPE, nullable=False, default=lambda: {"type": "object"}
    )
    requirements: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    condition: Mapped[dict[str, object]] = mapped_column(
        JSON_TYPE, nullable=False, default=lambda: {"operator": "always"}
    )
    budget_limit_microusd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    budget_reservation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    approval_policy_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    external_side_effect: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    operation_key_template: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("definition_id", "step_key", name="uq_workflow_steps_key"),
        UniqueConstraint("definition_id", "position", name="uq_workflow_steps_position"),
        CheckConstraint("position >= 0", name="ck_workflow_steps_position_non_negative"),
        CheckConstraint("timeout_seconds > 0", name="ck_workflow_steps_timeout_positive"),
        CheckConstraint("max_attempts > 0", name="ck_workflow_steps_attempts_positive"),
        CheckConstraint("initial_delay_seconds > 0", name="ck_workflow_steps_delay_positive"),
        CheckConstraint(
            "maximum_delay_seconds >= initial_delay_seconds",
            name="ck_workflow_steps_delay_order",
        ),
        CheckConstraint("retry_multiplier >= 1", name="ck_workflow_steps_multiplier_valid"),
        CheckConstraint("delay_seconds >= 0", name="ck_workflow_steps_controlled_delay_valid"),
        CheckConstraint("max_iterations BETWEEN 1 AND 100", name="ck_workflow_steps_iterations"),
        CheckConstraint(
            "budget_limit_microusd IS NULL OR budget_limit_microusd > 0",
            name="ck_workflow_steps_budget_positive",
        ),
        CheckConstraint(
            "fail_until_attempt >= 0 AND fail_until_attempt < max_attempts",
            name="ck_workflow_steps_failure_count_valid",
        ),
        CheckConstraint(
            "kind IN ('reference', 'delay', 'controlled_failure', 'approval')",
            name="ck_workflow_steps_kind_valid",
        ),
        {"schema": SCHEMA_NAME},
    )


class WorkflowRunRow(Base):
    """Workspace/project-scoped workflow aggregate root."""

    __tablename__ = "workflow_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_workflow_runs_project"),
        nullable=False,
    )
    definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_definitions.id", name="fk_workflow_runs_definition"),
        nullable=False,
    )
    definition_name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    input_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    output_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    permission_snapshot: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    auth_method: Mapped[str] = mapped_column(String(20), nullable=False, default="legacy")
    credential_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    parent_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_workflow_runs_parent"),
        nullable=True,
    )
    previous_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_workflow_runs_previous"),
        nullable=True,
    )
    schedule_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workflow_schedules.id", name="fk_workflow_runs_schedule"),
        nullable=True,
    )
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approval_policy_ref: Mapped[str] = mapped_column(
        String(100), nullable=False, default="legacy_dual_control"
    )
    current_step_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pause_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'paused', 'waiting_approval', "
            "'waiting_resource', 'waiting_configuration', 'waiting_budget', "
            "'awaiting_external_result', 'succeeded', 'failed', 'cancelling', 'cancelled')",
            name="ck_workflow_runs_status_valid",
        ),
        CheckConstraint("current_step_position >= 0", name="ck_workflow_runs_step_valid"),
        CheckConstraint("event_sequence >= 0", name="ck_workflow_runs_event_sequence_valid"),
        CheckConstraint("version > 0", name="ck_workflow_runs_version_positive"),
        CheckConstraint("iteration BETWEEN 1 AND 100", name="ck_workflow_runs_iteration"),
        Index("ix_workflow_runs_scope_status", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowStepRunRow(Base):
    """One durable workflow step execution."""

    __tablename__ = "workflow_step_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", name="fk_step_runs_workflow_run"), nullable=False
    )
    step_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_step_definitions.id", name="fk_step_runs_definition"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    output_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_manifest_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    blocked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    condition_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "position", name="uq_step_runs_run_position"),
        CheckConstraint("position >= 0", name="ck_step_runs_position_non_negative"),
        CheckConstraint("attempt >= 0", name="ck_step_runs_attempt_non_negative"),
        CheckConstraint("version > 0", name="ck_step_runs_version_positive"),
        CheckConstraint("iteration BETWEEN 1 AND 100", name="ck_step_runs_iteration"),
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting_approval', 'blocked', 'skipped', "
            "'stale', 'awaiting_external_result', 'succeeded', 'failed', 'cancelled')",
            name="ck_step_runs_status_valid",
        ),
        Index("ix_step_runs_scope_run", "workspace_id", "project_id", "workflow_run_id"),
        {"schema": SCHEMA_NAME},
    )


class TaskRunRow(Base):
    """Leased queue task whose idempotency key is globally unique per workspace."""

    __tablename__ = "workflow_task_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", name="fk_task_runs_workflow_run"), nullable=False
    )
    step_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_step_runs.id", name="fk_task_runs_step_run"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    input_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    output_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_delivery_event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_task_runs_idempotency"),
        CheckConstraint("attempt >= 0", name="ck_task_runs_attempt_non_negative"),
        CheckConstraint("version > 0", name="ck_task_runs_version_positive"),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled', "
            "'dead_letter', 'unknown')",
            name="ck_task_runs_status_valid",
        ),
        Index("ix_task_runs_claim", "status", "available_at", "lease_expires_at"),
        Index("ix_task_runs_scope_run", "workspace_id", "project_id", "workflow_run_id"),
        UniqueConstraint("workspace_id", "operation_key", name="uq_task_runs_operation_key"),
        {"schema": SCHEMA_NAME},
    )


class ApprovalRequestRow(Base):
    """Durable approval gate; no adapter can auto-approve it."""

    __tablename__ = "workflow_approval_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_approval_requests_workflow_run"),
        nullable=False,
    )
    step_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_step_runs.id", name="fk_approval_requests_step_run"),
        nullable=False,
    )
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    approval_policy_ref: Mapped[str] = mapped_column(
        String(100), nullable=False, default="legacy_dual_control"
    )
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("workflow_run_id", "step_run_id", name="uq_approval_requests_step"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')",
            name="ck_approval_requests_status_valid",
        ),
        Index("ix_approval_requests_scope_status", "workspace_id", "status", "expires_at"),
        {"schema": SCHEMA_NAME},
    )


class ApprovalDecisionRow(Base):
    """Append-only human approval decision."""

    __tablename__ = "workflow_approval_decisions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_approval_requests.id", name="fk_approval_decisions_request"),
        nullable=False,
    )
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    approval_policy_ref: Mapped[str] = mapped_column(
        String(100), nullable=False, default="legacy_dual_control"
    )
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("request_id", name="uq_approval_decisions_request"),
        CheckConstraint(
            "decision IN ('approve', 'reject')", name="ck_approval_decisions_value_valid"
        ),
        {"schema": SCHEMA_NAME},
    )


class WorkflowRunEventRow(Base):
    """Append-only versioned event stream reserved for resumable SSE."""

    __tablename__ = "workflow_run_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_run_events_workflow_run"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("workflow_run_id", "sequence", name="uq_run_events_sequence"),
        CheckConstraint("sequence > 0", name="ck_run_events_sequence_positive"),
        CheckConstraint("event_version > 0", name="ck_run_events_version_positive"),
        Index("ix_run_events_scope_cursor", "workspace_id", "workflow_run_id", "sequence"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowInputManifestRow(Base):
    """Immutable pins and authorized inputs frozen for one materialized step."""

    __tablename__ = "workflow_input_manifests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", name="fk_input_manifests_run"), nullable=False
    )
    step_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_step_runs.id", name="fk_input_manifests_step_run"),
        nullable=False,
    )
    definition_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    step_definition_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    executor_key: Mapped[str] = mapped_column(String(150), nullable=False)
    resolved_inputs: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    prompt_pin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_pin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    policy_pin: Mapped[str] = mapped_column(String(200), nullable=False)
    permission_version: Mapped[str] = mapped_column(String(100), nullable=False)
    grant_version: Mapped[str] = mapped_column(String(100), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(100), nullable=False)
    budget_reservation_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("workflow_run_id", "step_run_id", name="uq_input_manifests_step"),
        CheckConstraint("definition_version > 0", name="ck_input_manifests_definition_version"),
        Index("ix_input_manifests_scope_run", "workspace_id", "project_id", "workflow_run_id"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowReadReceiptRow(Base):
    """Append-only proof of source spans actually loaded for a step."""

    __tablename__ = "workflow_read_receipts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", name="fk_read_receipts_run"), nullable=False
    )
    step_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_step_runs.id", name="fk_read_receipts_step_run"),
        nullable=False,
    )
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_revision: Mapped[str] = mapped_column(String(200), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    section_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    loaded_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    token_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "step_run_id",
            "source_reference",
            "source_revision",
            "section_reference",
            name="uq_read_receipts_span",
        ),
        CheckConstraint("loaded_bytes > 0", name="ck_read_receipts_loaded_bytes"),
        CheckConstraint("token_count >= 0", name="ck_read_receipts_token_count"),
        Index("ix_read_receipts_scope_run", "workspace_id", "project_id", "workflow_run_id"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowDependencyEdgeRow(Base):
    """Frozen producer identity used to invalidate downstream runs."""

    __tablename__ = "workflow_dependency_edges"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    consumer_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", name="fk_dependency_edges_run"), nullable=False
    )
    consumer_step_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_step_runs.id", name="fk_dependency_edges_step_run"),
        nullable=False,
    )
    producer_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    producer_revision: Mapped[str] = mapped_column(String(200), nullable=False)
    producer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_key: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "consumer_step_run_id", "requirement_key", name="uq_dependency_edges_requirement"
        ),
        Index("ix_dependency_edges_producer", "workspace_id", "producer_reference"),
        Index("ix_dependency_edges_consumer", "workspace_id", "consumer_run_id"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowCompensationRecordRow(Base):
    """Durable outcome for a bounded compensation attempt."""

    __tablename__ = "workflow_compensation_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    task_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workflow_task_runs.id", name="fk_compensation_task"), nullable=False
    )
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    hook: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    result_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("task_run_id", "hook", name="uq_compensation_task_hook"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'unknown')",
            name="ck_compensation_status_valid",
        ),
        Index("ix_compensation_scope_run", "workspace_id", "project_id", "workflow_run_id"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowScheduleRow(Base):
    """Database-backed schedule with an in-row unique due claim lease."""

    __tablename__ = "workflow_schedules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_workflow_schedules_project"), nullable=False
    )
    definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_definitions.id", name="fk_workflow_schedules_definition"),
        nullable=False,
    )
    definition_name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    misfire_policy: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    input_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_prefix: Mapped[str] = mapped_column(String(128), nullable=False)
    last_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_prefix", name="uq_schedules_prefix"),
        CheckConstraint("definition_version > 0", name="ck_schedules_definition_version"),
        CheckConstraint("version > 0", name="ck_schedules_version"),
        CheckConstraint(
            "misfire_policy IN ('catch_up', 'fire_once', 'skip')",
            name="ck_schedules_misfire_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'archived')", name="ck_schedules_status_valid"
        ),
        Index("ix_schedules_due", "status", "next_due_at", "lease_until"),
        Index("ix_schedules_scope", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowDispatchLeaseRow(Base):
    """Fencing token for scheduler and maintenance claims beyond task leases."""

    __tablename__ = "workflow_dispatch_leases"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    resource_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fence_token: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("resource_kind", "resource_id", name="uq_dispatch_lease_resource"),
        Index("ix_dispatch_leases_expiry", "resource_kind", "lease_until"),
        {"schema": SCHEMA_NAME},
    )


class WorkflowInboxEventRow(Base):
    """Durable queue inbox preventing duplicate event application."""

    __tablename__ = "workflow_inbox_events"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    consumer: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    aggregate_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("aggregate_version > 0", name="ck_workflow_inbox_version"),
        Index("ix_workflow_inbox_aggregate", "consumer", "aggregate_id", "aggregate_version"),
        {"schema": SCHEMA_NAME},
    )


MODEL_REGISTRY = (
    WorkflowDefinitionRow,
    WorkflowStepDefinitionRow,
    WorkflowRunRow,
    WorkflowStepRunRow,
    TaskRunRow,
    ApprovalRequestRow,
    ApprovalDecisionRow,
    WorkflowRunEventRow,
    WorkflowInputManifestRow,
    WorkflowReadReceiptRow,
    WorkflowDependencyEdgeRow,
    WorkflowCompensationRecordRow,
    WorkflowScheduleRow,
    WorkflowDispatchLeaseRow,
    WorkflowInboxEventRow,
)


class SqlAlchemyWorkflowRepository:
    """Atomic workflow repository with mandatory Workspace scope on public queries."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def ensure_definition(self, definition: WorkflowDefinition) -> None:
        """Insert an immutable definition once and reject version mutation."""
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(WorkflowDefinitionRow).where(
                    WorkflowDefinitionRow.name == definition.name,
                    WorkflowDefinitionRow.definition_version == definition.version,
                )
            )
            if row is not None:
                steps = tuple(
                    (
                        await session.scalars(
                            select(WorkflowStepDefinitionRow)
                            .where(WorkflowStepDefinitionRow.definition_id == row.id)
                            .order_by(WorkflowStepDefinitionRow.position)
                        )
                    ).all()
                )
                if _definition(row, steps) != definition:
                    raise InvalidStateError("A workflow definition version is immutable.")
                return
            session.add(
                WorkflowDefinitionRow(
                    id=definition.id,
                    name=definition.name,
                    definition_version=definition.version,
                    graph_version=definition.graph_version,
                    status=definition.status.value,
                    description=definition.description,
                    checksum=definition.checksum,
                    created_at=definition.created_at,
                )
            )
            session.add_all(
                [_step_definition_row(definition.id, step) for step in definition.steps]
            )

    async def get_definition(self, definition_id: UUID) -> WorkflowDefinition | None:
        """Return one immutable definition by its exact version identity."""
        async with self._sessions() as session:
            row = await session.get(WorkflowDefinitionRow, definition_id)
            if row is None:
                return None
            steps = tuple(
                (
                    await session.scalars(
                        select(WorkflowStepDefinitionRow)
                        .where(WorkflowStepDefinitionRow.definition_id == definition_id)
                        .order_by(WorkflowStepDefinitionRow.position)
                    )
                ).all()
            )
            return _definition(row, steps)

    async def submit(  # noqa: PLR0913 - implements the durable submission contract.
        self,
        run: WorkflowRun,
        definition: WorkflowDefinition,
        *,
        request_digest: str,
        resolved_inputs: dict[str, tuple[ResolvedInput, ...]] | None = None,
        prompt_pin: str | None = None,
        model_pin: str | None = None,
        budget_reservation_refs: dict[str, str] | None = None,
    ) -> tuple[WorkflowRun, bool]:
        """Atomically reserve idempotency, create state, and append first dispatch."""
        async with self._sessions.begin() as session:
            record, created = await SqlAlchemyIdempotencyStore(session).reserve(
                IdempotencyRecord(
                    uuid4(),
                    run.workspace_id,
                    run.project_id,
                    f"workflows.submit:{definition.name}",
                    run.idempotency_key,
                    request_digest,
                    str(run.id),
                    run.created_at + timedelta(days=1),
                )
            )
            if not created:
                existing = await session.scalar(
                    select(WorkflowRunRow).where(
                        WorkflowRunRow.workspace_id == run.workspace_id,
                        WorkflowRunRow.id == UUID(record.result_reference),
                    )
                )
                if existing is None:
                    raise InvalidStateError("Idempotent workflow result is unavailable.")
                return _run(existing), False
            run_row = _run_row(run)
            session.add(run_row)
            await session.flush()
            await _append_run_event(
                session,
                run_row,
                "workflows.run-submitted",
                run.created_at,
                {"schema": "run-submitted.v1", "actor_id": str(run.requested_by)},
            )
            if definition.graph_version == 1:
                await _schedule_step(
                    session, run_row, definition.steps[0], run.input_reference, run.created_at
                )
            else:
                await _initialize_graph(
                    session,
                    run_row,
                    definition,
                    resolved_inputs or {},
                    prompt_pin=prompt_pin,
                    model_pin=model_pin,
                    budget_reservation_refs=budget_reservation_refs or {},
                    now=run.created_at,
                )
            return _run(run_row), True

    async def get_run(self, workspace_id: UUID, run_id: UUID) -> WorkflowRun | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(WorkflowRunRow).where(
                    WorkflowRunRow.workspace_id == workspace_id,
                    WorkflowRunRow.id == run_id,
                )
            )
        return None if row is None else _run(row)

    async def get_steps(self, workspace_id: UUID, run_id: UUID) -> tuple[StepRun, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowStepRunRow)
                        .where(
                            WorkflowStepRunRow.workspace_id == workspace_id,
                            WorkflowStepRunRow.workflow_run_id == run_id,
                        )
                        .order_by(WorkflowStepRunRow.position, WorkflowStepRunRow.id)
                    )
                ).all()
            )
        return tuple(_step_run(row) for row in rows)

    async def get_tasks(self, workspace_id: UUID, run_id: UUID) -> tuple[TaskRun, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(TaskRunRow)
                        .where(
                            TaskRunRow.workspace_id == workspace_id,
                            TaskRunRow.workflow_run_id == run_id,
                        )
                        .order_by(TaskRunRow.created_at, TaskRunRow.id)
                    )
                ).all()
            )
        return tuple(_task(row) for row in rows)

    async def get_events(
        self, workspace_id: UUID, run_id: UUID, *, after_sequence: int = 0
    ) -> tuple[WorkflowRunEvent, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowRunEventRow)
                        .where(
                            WorkflowRunEventRow.workspace_id == workspace_id,
                            WorkflowRunEventRow.workflow_run_id == run_id,
                            WorkflowRunEventRow.sequence > after_sequence,
                        )
                        .order_by(WorkflowRunEventRow.sequence)
                    )
                ).all()
            )
        return tuple(_run_event(row) for row in rows)

    async def get_input_manifests(
        self, workspace_id: UUID, run_id: UUID
    ) -> tuple[StepInputManifest, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowInputManifestRow)
                        .where(
                            WorkflowInputManifestRow.workspace_id == workspace_id,
                            WorkflowInputManifestRow.workflow_run_id == run_id,
                        )
                        .order_by(WorkflowInputManifestRow.created_at, WorkflowInputManifestRow.id)
                    )
                ).all()
            )
        return tuple(_input_manifest(row) for row in rows)

    async def get_read_receipts(self, workspace_id: UUID, run_id: UUID) -> tuple[ReadReceipt, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowReadReceiptRow)
                        .where(
                            WorkflowReadReceiptRow.workspace_id == workspace_id,
                            WorkflowReadReceiptRow.workflow_run_id == run_id,
                        )
                        .order_by(WorkflowReadReceiptRow.created_at, WorkflowReadReceiptRow.id)
                    )
                ).all()
            )
        return tuple(_read_receipt(row) for row in rows)

    async def append_read_receipts(
        self,
        workspace_id: UUID,
        run_id: UUID,
        step_run_id: UUID,
        receipts: tuple[ReadReceipt, ...],
    ) -> None:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            step = await session.scalar(
                select(WorkflowStepRunRow).where(
                    WorkflowStepRunRow.id == step_run_id,
                    WorkflowStepRunRow.workflow_run_id == run.id,
                )
            )
            if step is None or step.input_manifest_id is None:
                raise InvalidStateError("Workflow step input manifest is unavailable.")
            manifest = await session.get(WorkflowInputManifestRow, step.input_manifest_id)
            if manifest is None:
                raise InvalidStateError("Workflow step input manifest is unavailable.")
            for receipt in receipts:
                if (
                    receipt.workspace_id != workspace_id
                    or receipt.workflow_run_id != run_id
                    or receipt.step_run_id != step_run_id
                    or receipt.input_digest != manifest.input_digest
                ):
                    raise InvalidStateError(
                        "Read receipt does not match the frozen input manifest."
                    )
                session.add(_read_receipt_row(receipt))

    async def get_dependency_edges(
        self, workspace_id: UUID, run_id: UUID
    ) -> tuple[DependencyEdge, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowDependencyEdgeRow)
                        .where(
                            WorkflowDependencyEdgeRow.workspace_id == workspace_id,
                            WorkflowDependencyEdgeRow.consumer_run_id == run_id,
                        )
                        .order_by(
                            WorkflowDependencyEdgeRow.created_at,
                            WorkflowDependencyEdgeRow.id,
                        )
                    )
                ).all()
            )
        return tuple(_dependency_edge(row) for row in rows)

    async def invalidate_dependencies(
        self,
        workspace_id: UUID,
        producer_reference: str,
        *,
        replacement_hash: str,
        now: datetime,
    ) -> tuple[UUID, ...]:
        async with self._sessions.begin() as session:
            edges = tuple(
                (
                    await session.scalars(
                        select(WorkflowDependencyEdgeRow)
                        .where(
                            WorkflowDependencyEdgeRow.workspace_id == workspace_id,
                            WorkflowDependencyEdgeRow.producer_reference == producer_reference,
                            WorkflowDependencyEdgeRow.producer_hash != replacement_hash,
                            WorkflowDependencyEdgeRow.invalidated_at.is_(None),
                        )
                        .with_for_update()
                    )
                ).all()
            )
            affected: set[UUID] = set()
            for edge in edges:
                edge.invalidated_at = now
                affected.add(edge.consumer_run_id)
                step = await session.get(WorkflowStepRunRow, edge.consumer_step_run_id)
                if step is not None and step.status in {
                    StepRunStatus.BLOCKED.value,
                    StepRunStatus.PENDING.value,
                }:
                    step.status = StepRunStatus.STALE.value
                    step.error_reference = "workflow-input://stale"
                    step.updated_at = now
                    task = await session.scalar(
                        select(TaskRunRow).where(
                            TaskRunRow.step_run_id == step.id,
                            TaskRunRow.status == TaskRunStatus.PENDING.value,
                        )
                    )
                    if task is not None:
                        task.status = TaskRunStatus.CANCELLED.value
                        task.error_reference = step.error_reference
                        task.updated_at = now
                run = await session.get(WorkflowRunRow, edge.consumer_run_id)
                if run is not None:
                    await _append_run_event(
                        session,
                        run,
                        "workflows.input-invalidated",
                        now,
                        {
                            "schema": "input-invalidated.v1",
                            "producer_reference": producer_reference,
                            "replacement_hash": replacement_hash,
                        },
                    )
            return tuple(sorted(affected, key=str))

    async def save_schedule(self, schedule: WorkflowSchedule) -> WorkflowSchedule:
        async with self._sessions.begin() as session:
            row = await session.get(WorkflowScheduleRow, schedule.id)
            if row is None:
                row = _schedule_row(schedule)
                session.add(row)
            else:
                if (row.workspace_id, row.definition_id, row.definition_version) != (
                    schedule.workspace_id,
                    schedule.definition_id,
                    schedule.definition_version,
                ):
                    raise InvalidStateError("A schedule cannot switch its frozen definition.")
                row.schedule_expression = schedule.schedule_expression
                row.timezone = schedule.timezone
                row.misfire_policy = schedule.misfire_policy.value
                row.status = schedule.status.value
                row.input_reference = schedule.input_reference
                row.next_due_at = schedule.next_due_at
                row.updated_at = schedule.updated_at
            await session.flush()
            return _schedule(row)

    async def get_schedule(self, workspace_id: UUID, schedule_id: UUID) -> WorkflowSchedule | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(WorkflowScheduleRow).where(
                    WorkflowScheduleRow.workspace_id == workspace_id,
                    WorkflowScheduleRow.id == schedule_id,
                )
            )
        return None if row is None else _schedule(row)

    async def list_schedules(
        self, workspace_id: UUID, project_id: UUID | None = None
    ) -> tuple[WorkflowSchedule, ...]:
        statement = select(WorkflowScheduleRow).where(
            WorkflowScheduleRow.workspace_id == workspace_id
        )
        if project_id is not None:
            statement = statement.where(WorkflowScheduleRow.project_id == project_id)
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        statement.order_by(WorkflowScheduleRow.next_due_at, WorkflowScheduleRow.id)
                    )
                ).all()
            )
        return tuple(_schedule(row) for row in rows)

    async def claim_due_schedules(
        self,
        *,
        now: datetime,
        lease: timedelta,
        worker_id: str,
        limit: int = 25,
    ) -> tuple[WorkflowSchedule, ...]:
        maximum_claim_batch = 100
        if limit < 1 or limit > maximum_claim_batch:
            raise ValueError("schedule claim limit must be between 1 and 100")
        async with self._sessions.begin() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(WorkflowScheduleRow)
                        .where(
                            WorkflowScheduleRow.status == ScheduleStatus.ACTIVE.value,
                            WorkflowScheduleRow.next_due_at <= now,
                            (
                                (WorkflowScheduleRow.lease_until.is_(None))
                                | (WorkflowScheduleRow.lease_until <= now)
                            ),
                        )
                        .order_by(WorkflowScheduleRow.next_due_at, WorkflowScheduleRow.id)
                        .limit(limit)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            claimed: list[WorkflowSchedule] = []
            for row in rows:
                token = uuid4()
                row.lease_token = token
                row.lease_until = now + lease
                row.last_claimed_at = now
                row.updated_at = now
                lease_row = await session.scalar(
                    select(WorkflowDispatchLeaseRow)
                    .where(
                        WorkflowDispatchLeaseRow.resource_kind == "schedule",
                        WorkflowDispatchLeaseRow.resource_id == row.id,
                    )
                    .with_for_update()
                )
                if lease_row is None:
                    session.add(
                        WorkflowDispatchLeaseRow(
                            id=uuid4(),
                            workspace_id=row.workspace_id,
                            resource_kind="schedule",
                            resource_id=row.id,
                            fence_token=token,
                            worker_id=worker_id,
                            claimed_at=now,
                            lease_until=now + lease,
                        )
                    )
                else:
                    lease_row.fence_token = token
                    lease_row.worker_id = worker_id
                    lease_row.claimed_at = now
                    lease_row.lease_until = now + lease
                claimed.append(_schedule(row))
            return tuple(claimed)

    async def settle_schedule_claim(
        self,
        schedule_id: UUID,
        lease_token: UUID,
        *,
        next_due_at: datetime,
        last_run_id: UUID | None,
        now: datetime,
    ) -> WorkflowSchedule:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(WorkflowScheduleRow)
                .where(
                    WorkflowScheduleRow.id == schedule_id,
                    WorkflowScheduleRow.lease_token == lease_token,
                )
                .with_for_update()
            )
            if row is None:
                raise InvalidStateError("Schedule claim is no longer owned by this Worker.")
            lease_row = await session.scalar(
                select(WorkflowDispatchLeaseRow).where(
                    WorkflowDispatchLeaseRow.resource_kind == "schedule",
                    WorkflowDispatchLeaseRow.resource_id == schedule_id,
                    WorkflowDispatchLeaseRow.fence_token == lease_token,
                )
            )
            if lease_row is None:
                raise InvalidStateError("Schedule fencing token is unavailable.")
            await session.delete(lease_row)
            row.next_due_at = next_due_at
            row.last_run_id = last_run_id
            row.lease_token = None
            row.lease_until = None
            row.updated_at = now
            await session.flush()
            return _schedule(row)

    async def pause(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        actor_id: UUID,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            active_tasks = await _active_tasks(session, run)
            if run.status == WorkflowRunStatus.RUNNING.value and (
                any(task.status == TaskRunStatus.RUNNING.value for task in active_tasks)
            ):
                run.pause_requested_at = now
                event_type = "workflows.run-pause-requested"
            else:
                ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.PAUSED)
                run.status = WorkflowRunStatus.PAUSED.value
                run.pause_requested_at = now
                event_type = "workflows.run-paused"
            run.updated_at = now
            await _append_run_event(
                session,
                run,
                event_type,
                now,
                {"schema": "run-paused.v1", "actor_id": str(actor_id)},
            )
            return _run(run)

    async def resume(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        actor_id: UUID,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            if run.status == WorkflowRunStatus.RUNNING.value and run.pause_requested_at is not None:
                run.pause_requested_at = None
            else:
                approval = await _pending_approval(session, run.id)
                if approval is not None:
                    ensure_run_transition(
                        WorkflowRunStatus(run.status), WorkflowRunStatus.WAITING_APPROVAL
                    )
                    run.status = WorkflowRunStatus.WAITING_APPROVAL.value
                else:
                    ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.RUNNING)
                    run.status = WorkflowRunStatus.RUNNING.value
                tasks = await _active_tasks(session, run)
                pending_tasks = tuple(
                    task for task in tasks if task.status == TaskRunStatus.PENDING.value
                )
                if not pending_tasks and approval is None:
                    raise InvalidStateError("Paused workflow has no resumable task.")
                for task in pending_tasks:
                    await _dispatch(session, run, task, now, max(now, task.available_at))
                run.pause_requested_at = None
            run.updated_at = now
            await _append_run_event(
                session,
                run,
                "workflows.run-resumed",
                now,
                {"schema": "run-resumed.v1", "actor_id": str(actor_id)},
            )
            return _run(run)

    async def cancel(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        actor_id: UUID,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            tasks = await _active_tasks(session, run)
            active_lease = any(task.status == TaskRunStatus.RUNNING.value for task in tasks)
            target = WorkflowRunStatus.CANCELLING if active_lease else WorkflowRunStatus.CANCELLED
            ensure_run_transition(WorkflowRunStatus(run.status), target)
            run.status = target.value
            run.cancel_requested_at = now
            run.updated_at = now
            if not active_lease:
                await _cancel_current_records(session, run, tasks, now)
            await _append_run_event(
                session,
                run,
                "workflows.run-cancelling" if active_lease else "workflows.run-cancelled",
                now,
                {"schema": "run-cancelled.v1", "actor_id": str(actor_id)},
            )
            return _run(run)

    async def get_approval(self, workspace_id: UUID, run_id: UUID) -> ApprovalRequest | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ApprovalRequestRow).where(
                    ApprovalRequestRow.workspace_id == workspace_id,
                    ApprovalRequestRow.workflow_run_id == run_id,
                    ApprovalRequestRow.status == ApprovalStatus.PENDING.value,
                )
            )
        return None if row is None else _approval(row)

    async def decide_approval(
        self,
        workspace_id: UUID,
        run_id: UUID,
        record: ApprovalRecord,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            request = await session.scalar(
                select(ApprovalRequestRow)
                .where(
                    ApprovalRequestRow.id == record.request_id,
                    ApprovalRequestRow.workspace_id == workspace_id,
                    ApprovalRequestRow.workflow_run_id == run_id,
                    ApprovalRequestRow.status == ApprovalStatus.PENDING.value,
                )
                .with_for_update()
            )
            if request is None or run.status != WorkflowRunStatus.WAITING_APPROVAL.value:
                raise InvalidStateError("Only a pending workflow approval can be decided.")
            if request.expires_at <= record.decided_at or (
                request.approval_policy_ref,
                request.input_digest,
            ) != (record.approval_policy_ref, record.input_digest):
                raise InvalidStateError("Approval expired or the frozen gate input changed.")
            session.add(_approval_decision_row(record))
            step_run = await session.get(WorkflowStepRunRow, request.step_run_id)
            if step_run is None:
                raise InvalidStateError("Workflow approval step is unavailable.")
            if record.decision is WorkflowApprovalDecision.REJECT:
                request.status = ApprovalStatus.REJECTED.value
                step_run.status = StepRunStatus.FAILED.value
                step_run.error_reference = "workflow-error://approval-rejected"
                step_run.updated_at = record.decided_at
                ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.FAILED)
                run.status = WorkflowRunStatus.FAILED.value
                run.error_reference = step_run.error_reference
                event_type = "workflows.approval-rejected"
            else:
                request.status = ApprovalStatus.APPROVED.value
                step_run.status = StepRunStatus.SUCCEEDED.value
                step_run.output_reference = step_run.input_reference
                step_run.updated_at = record.decided_at
                ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.RUNNING)
                run.status = WorkflowRunStatus.RUNNING.value
                await _advance(session, run, step_run.output_reference, record.decided_at)
                event_type = "workflows.approval-approved"
            run.updated_at = record.decided_at
            await _append_run_event(
                session,
                run,
                event_type,
                record.decided_at,
                {
                    "schema": "approval-decision.v1",
                    "actor_id": str(record.actor_id),
                    "decision": record.decision.value,
                    "reason": record.reason,
                },
            )
            return _run(run)

    async def expire_approval(
        self, workspace_id: UUID, run_id: UUID, *, now: datetime
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            run = await _locked_run(session, workspace_id, run_id)
            request = await _pending_approval(session, run.id, lock=True)
            if (
                request is None
                or run.status != WorkflowRunStatus.WAITING_APPROVAL.value
                or request.expires_at > now
            ):
                raise InvalidStateError("Workflow approval is not expired.")
            request.status = ApprovalStatus.EXPIRED.value
            step_run = await session.get(WorkflowStepRunRow, request.step_run_id)
            if step_run is None:
                raise InvalidStateError("Workflow approval step is unavailable.")
            step_run.status = StepRunStatus.FAILED.value
            step_run.error_reference = "workflow-error://approval-expired"
            step_run.updated_at = now
            ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.FAILED)
            run.status = WorkflowRunStatus.FAILED.value
            run.error_reference = step_run.error_reference
            run.updated_at = now
            await _append_run_event(
                session,
                run,
                "workflows.approval-expired",
                now,
                {"schema": "approval-expired.v1"},
            )
            return _run(run)

    async def claim_task(
        self,
        task_id: UUID,
        delivery_event_id: UUID,
        *,
        now: datetime,
        lease: timedelta,
    ) -> ClaimedTask | None:
        async with self._sessions.begin() as session:
            task = await session.scalar(
                select(TaskRunRow).where(TaskRunRow.id == task_id).with_for_update()
            )
            if task is None:
                return None
            run = await session.scalar(
                select(WorkflowRunRow)
                .where(WorkflowRunRow.id == task.workflow_run_id)
                .with_for_update()
            )
            if run is None:
                raise InvalidStateError("Workflow task has no owning run.")
            if run.status == WorkflowRunStatus.CANCELLING.value:
                await _settle_cancelled(session, run, task, now, "workflow-error://cancelled")
                return None
            eligible_pending = (
                task.status == TaskRunStatus.PENDING.value and task.available_at <= now
            )
            eligible_recovery = (
                task.status == TaskRunStatus.RUNNING.value
                and task.lease_expires_at is not None
                and task.lease_expires_at <= now
            )
            if run.status not in {
                WorkflowRunStatus.PENDING.value,
                WorkflowRunStatus.RUNNING.value,
                WorkflowRunStatus.WAITING_APPROVAL.value,
            } or not (eligible_pending or eligible_recovery):
                return None
            step_run = await session.get(WorkflowStepRunRow, task.step_run_id)
            if step_run is None:
                raise InvalidStateError("Workflow task has no owning step.")
            step_row = await session.get(WorkflowStepDefinitionRow, step_run.step_definition_id)
            if step_row is None:
                raise InvalidStateError("Workflow task definition is unavailable.")
            step = _step_definition(step_row)
            if task.attempt >= step.retry_policy.max_attempts:
                await _settle_dead_letter(
                    session, run, task, step_run, now, "workflow-error://lease-attempts-exhausted"
                )
                return None
            token = uuid4()
            deadline = now + timedelta(seconds=step.timeout_seconds)
            task.status = TaskRunStatus.RUNNING.value
            task.attempt += 1
            task.deadline = deadline
            task.lease_token = token
            task.lease_expires_at = now + lease
            task.last_delivery_event_id = delivery_event_id
            task.updated_at = now
            step_run.status = StepRunStatus.RUNNING.value
            step_run.attempt = task.attempt
            step_run.deadline = deadline
            step_run.updated_at = now
            if run.status == WorkflowRunStatus.PENDING.value:
                ensure_run_transition(WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING)
                run.status = WorkflowRunStatus.RUNNING.value
            run.updated_at = now
            await _append_run_event(
                session,
                run,
                "workflows.task-started",
                now,
                {
                    "schema": "task-started.v1",
                    "task_id": str(task.id),
                    "attempt": task.attempt,
                    "delivery_event_id": str(delivery_event_id),
                },
            )
            return ClaimedTask(_task(task), _run(run), _step_run(step_run), step, token)

    async def is_cancelling(self, task_id: UUID, lease_token: UUID) -> bool:
        async with self._sessions() as session:
            status = await session.scalar(
                select(WorkflowRunRow.status)
                .join(TaskRunRow, TaskRunRow.workflow_run_id == WorkflowRunRow.id)
                .where(
                    TaskRunRow.id == task_id,
                    TaskRunRow.lease_token == lease_token,
                    TaskRunRow.status == TaskRunStatus.RUNNING.value,
                )
            )
        return status == WorkflowRunStatus.CANCELLING.value

    async def is_manifest_current(self, task_id: UUID, lease_token: UUID) -> bool:
        async with self._sessions() as session:
            invalidated = await session.scalar(
                select(WorkflowDependencyEdgeRow.id)
                .join(
                    TaskRunRow,
                    TaskRunRow.step_run_id == WorkflowDependencyEdgeRow.consumer_step_run_id,
                )
                .where(
                    TaskRunRow.id == task_id,
                    TaskRunRow.lease_token == lease_token,
                    WorkflowDependencyEdgeRow.invalidated_at.is_not(None),
                )
            )
        return invalidated is None

    async def succeed_task(
        self,
        claimed: ClaimedTask,
        *,
        output_reference: str,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            task, run, step_run = await _locked_claim(session, claimed)
            task.status = TaskRunStatus.SUCCEEDED.value
            task.output_reference = output_reference
            task.error_reference = None
            _release_task(task, now)
            step_run.status = StepRunStatus.SUCCEEDED.value
            step_run.output_reference = output_reference
            step_run.error_reference = None
            step_run.updated_at = now
            await _record_inbox(session, task, now)
            await _append_run_event(
                session,
                run,
                "workflows.task-succeeded",
                now,
                {"schema": "task-succeeded.v1", "task_id": str(task.id)},
            )
            if run.status not in {
                WorkflowRunStatus.SUCCEEDED.value,
                WorkflowRunStatus.FAILED.value,
                WorkflowRunStatus.CANCELLED.value,
            }:
                await _advance(session, run, output_reference, now)
            return _run(run)

    async def fail_task(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        now: datetime,
        retry_at: datetime | None,
    ) -> FailureSettlement:
        async with self._sessions.begin() as session:
            task, run, step_run = await _locked_claim(session, claimed)
            if retry_at is not None:
                task.status = TaskRunStatus.PENDING.value
                task.available_at = retry_at
                task.error_reference = error_reference
                _release_task(task, now)
                step_run.status = StepRunStatus.PENDING.value
                step_run.error_reference = error_reference
                step_run.updated_at = now
                if run.pause_requested_at is not None:
                    ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.PAUSED)
                    run.status = WorkflowRunStatus.PAUSED.value
                else:
                    await _dispatch(session, run, task, now, retry_at)
                event_type = "workflows.task-retry-scheduled"
                retry_scheduled = True
            else:
                await _settle_dead_letter(session, run, task, step_run, now, error_reference)
                event_type = "workflows.task-dead-lettered"
                retry_scheduled = False
            await _record_inbox(session, task, now)
            run.updated_at = now
            await _append_run_event(
                session,
                run,
                event_type,
                now,
                {
                    "schema": "task-failed.v1",
                    "task_id": str(task.id),
                    "attempt": task.attempt,
                    "error_reference": error_reference,
                },
            )
            return FailureSettlement(_run(run), retry_scheduled)

    async def cancel_task(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            task, run, _step_run_row = await _locked_claim(session, claimed)
            await _settle_cancelled(session, run, task, now, error_reference)
            await _record_inbox(session, task, now)
            await _append_run_event(
                session,
                run,
                "workflows.run-cancelled",
                now,
                {"schema": "run-cancelled.v1", "task_id": str(task.id)},
            )
            return _run(run)

    async def mark_task_unknown(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        provider_job_id: str | None,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            task, run, step_run = await _locked_claim(session, claimed)
            task.status = TaskRunStatus.UNKNOWN.value
            task.error_reference = error_reference
            task.provider_job_id = provider_job_id
            _release_task(task, now)
            step_run.status = StepRunStatus.AWAITING_EXTERNAL_RESULT.value
            step_run.error_reference = error_reference
            step_run.updated_at = now
            ensure_run_transition(
                WorkflowRunStatus(run.status), WorkflowRunStatus.AWAITING_EXTERNAL_RESULT
            )
            run.status = WorkflowRunStatus.AWAITING_EXTERNAL_RESULT.value
            run.error_reference = error_reference
            run.updated_at = now
            await _record_inbox(session, task, now)
            await _append_run_event(
                session,
                run,
                "workflows.task-result-unknown",
                now,
                {
                    "schema": "task-result-unknown.v1",
                    "task_id": str(task.id),
                    "provider_job_id": provider_job_id,
                    "error_reference": error_reference,
                },
            )
            return _run(run)

    async def mark_task_stale(
        self,
        claimed: ClaimedTask,
        *,
        now: datetime,
    ) -> WorkflowRun:
        async with self._sessions.begin() as session:
            task, run, step_run = await _locked_claim(session, claimed)
            task.status = TaskRunStatus.CANCELLED.value
            task.error_reference = "workflow-input://stale"
            _release_task(task, now)
            step_run.status = StepRunStatus.STALE.value
            step_run.error_reference = task.error_reference
            step_run.updated_at = now
            ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.WAITING_RESOURCE)
            run.status = WorkflowRunStatus.WAITING_RESOURCE.value
            run.error_reference = task.error_reference
            run.updated_at = now
            await _record_inbox(session, task, now)
            await _append_run_event(
                session,
                run,
                "workflows.step-stale",
                now,
                {"schema": "step-stale.v1", "step_key": step_run.step_key},
            )
            return _run(run)

    async def begin_compensation(
        self,
        claimed: ClaimedTask,
        hook: str,
        *,
        now: datetime,
    ) -> tuple[CompensationRecord, bool]:
        async with self._sessions.begin() as session:
            task, run, _step_run = await _locked_claim(session, claimed)
            existing = await session.scalar(
                select(WorkflowCompensationRecordRow).where(
                    WorkflowCompensationRecordRow.task_run_id == task.id,
                    WorkflowCompensationRecordRow.hook == hook,
                )
            )
            if existing is not None:
                return _compensation(existing), False
            row = WorkflowCompensationRecordRow(
                id=uuid4(),
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                workflow_run_id=run.id,
                task_run_id=task.id,
                operation_key=f"{task.operation_key}:compensate:{hook}",
                hook=hook,
                status=CompensationStatus.PENDING.value,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.flush()
            await _append_run_event(
                session,
                run,
                "workflows.compensation-started",
                now,
                {
                    "schema": "compensation-started.v1",
                    "task_id": str(task.id),
                    "hook": hook,
                    "operation_key": row.operation_key,
                },
            )
            return _compensation(row), True

    async def settle_compensation(  # noqa: PLR0913 - explicit durable settlement fields.
        self,
        claimed: ClaimedTask,
        record_id: UUID,
        status: CompensationStatus,
        *,
        result_reference: str | None,
        error_reference: str | None,
        now: datetime,
    ) -> CompensationRecord:
        if status is CompensationStatus.PENDING:
            raise ValueError("compensation settlement must be terminal")
        async with self._sessions.begin() as session:
            task, run, _step_run = await _locked_claim(session, claimed)
            row = await session.scalar(
                select(WorkflowCompensationRecordRow)
                .where(
                    WorkflowCompensationRecordRow.id == record_id,
                    WorkflowCompensationRecordRow.task_run_id == task.id,
                )
                .with_for_update()
            )
            if row is None:
                raise InvalidStateError("Compensation record is unavailable.")
            if row.status != CompensationStatus.PENDING.value:
                return _compensation(row)
            row.status = status.value
            row.result_reference = result_reference
            row.error_reference = error_reference
            row.updated_at = now
            await _append_run_event(
                session,
                run,
                "workflows.compensation-settled",
                now,
                {
                    "schema": "compensation-settled.v1",
                    "task_id": str(task.id),
                    "status": status.value,
                },
            )
            return _compensation(row)


async def _locked_run(session: AsyncSession, workspace_id: UUID, run_id: UUID) -> WorkflowRunRow:
    row = await session.scalar(
        select(WorkflowRunRow)
        .where(WorkflowRunRow.workspace_id == workspace_id, WorkflowRunRow.id == run_id)
        .with_for_update()
    )
    if row is None:
        raise ScopeViolationError
    return row


async def _record_inbox(session: AsyncSession, task: TaskRunRow, now: datetime) -> None:
    event_id = task.last_delivery_event_id
    if event_id is None or await session.get(WorkflowInboxEventRow, event_id) is not None:
        return
    session.add(
        WorkflowInboxEventRow(
            event_id=event_id,
            workspace_id=task.workspace_id,
            consumer="workflow-worker",
            aggregate_id=task.workflow_run_id,
            aggregate_version=max(task.attempt, 1),
            processed_at=now,
        )
    )


async def _locked_claim(
    session: AsyncSession, claimed: ClaimedTask
) -> tuple[TaskRunRow, WorkflowRunRow, WorkflowStepRunRow]:
    task = await session.scalar(
        select(TaskRunRow)
        .where(
            TaskRunRow.id == claimed.task.id,
            TaskRunRow.status == TaskRunStatus.RUNNING.value,
            TaskRunRow.lease_token == claimed.lease_token,
        )
        .with_for_update()
    )
    if task is None:
        raise InvalidStateError("Workflow task lease is no longer owned by this Worker.")
    run = await session.scalar(
        select(WorkflowRunRow).where(WorkflowRunRow.id == task.workflow_run_id).with_for_update()
    )
    step_run = await session.get(WorkflowStepRunRow, task.step_run_id)
    if run is None or step_run is None:
        raise InvalidStateError("Workflow task ownership state is unavailable.")
    return task, run, step_run


async def _current_task(session: AsyncSession, run: WorkflowRunRow) -> TaskRunRow | None:
    return cast(
        "TaskRunRow | None",
        await session.scalar(
            select(TaskRunRow)
            .join(WorkflowStepRunRow, WorkflowStepRunRow.id == TaskRunRow.step_run_id)
            .where(
                TaskRunRow.workflow_run_id == run.id,
                WorkflowStepRunRow.position == run.current_step_position,
            )
        ),
    )


async def _active_tasks(session: AsyncSession, run: WorkflowRunRow) -> tuple[TaskRunRow, ...]:
    return tuple(
        (
            await session.scalars(
                select(TaskRunRow)
                .where(
                    TaskRunRow.workflow_run_id == run.id,
                    TaskRunRow.status.in_(
                        (TaskRunStatus.PENDING.value, TaskRunStatus.RUNNING.value)
                    ),
                )
                .order_by(TaskRunRow.created_at, TaskRunRow.id)
            )
        ).all()
    )


async def _pending_approval(
    session: AsyncSession, run_id: UUID, *, lock: bool = False
) -> ApprovalRequestRow | None:
    statement = select(ApprovalRequestRow).where(
        ApprovalRequestRow.workflow_run_id == run_id,
        ApprovalRequestRow.status == ApprovalStatus.PENDING.value,
    )
    if lock:
        statement = statement.with_for_update()
    return cast("ApprovalRequestRow | None", await session.scalar(statement))


async def _cancel_current_records(
    session: AsyncSession,
    run: WorkflowRunRow,
    tasks: tuple[TaskRunRow, ...],
    now: datetime,
) -> None:
    for task in tasks:
        if task.status != TaskRunStatus.PENDING.value:
            continue
        task.status = TaskRunStatus.CANCELLED.value
        task.error_reference = "workflow-error://cancelled"
        task.updated_at = now
        step = await session.get(WorkflowStepRunRow, task.step_run_id)
        if step is not None:
            step.status = StepRunStatus.CANCELLED.value
            step.error_reference = task.error_reference
            step.updated_at = now
    approvals = tuple(
        (
            await session.scalars(
                select(ApprovalRequestRow)
                .where(
                    ApprovalRequestRow.workflow_run_id == run.id,
                    ApprovalRequestRow.status == ApprovalStatus.PENDING.value,
                )
                .with_for_update()
            )
        ).all()
    )
    for approval in approvals:
        approval.status = ApprovalStatus.CANCELLED.value
        step = await session.get(WorkflowStepRunRow, approval.step_run_id)
        if step is not None:
            step.status = StepRunStatus.CANCELLED.value
            step.error_reference = "workflow-error://cancelled"
            step.updated_at = now
    blocked_steps = tuple(
        (
            await session.scalars(
                select(WorkflowStepRunRow).where(
                    WorkflowStepRunRow.workflow_run_id == run.id,
                    WorkflowStepRunRow.status.in_(
                        (StepRunStatus.BLOCKED.value, StepRunStatus.PENDING.value)
                    ),
                )
            )
        ).all()
    )
    for step in blocked_steps:
        step.status = StepRunStatus.CANCELLED.value
        step.error_reference = "workflow-error://cancelled"
        step.updated_at = now


async def _settle_cancelled(
    session: AsyncSession,
    run: WorkflowRunRow,
    task: TaskRunRow,
    now: datetime,
    error_reference: str,
) -> None:
    task.status = TaskRunStatus.CANCELLED.value
    task.error_reference = error_reference
    _release_task(task, now)
    step = await session.get(WorkflowStepRunRow, task.step_run_id)
    if step is not None:
        step.status = StepRunStatus.CANCELLED.value
        step.error_reference = error_reference
        step.updated_at = now
    if run.status != WorkflowRunStatus.CANCELLING.value:
        ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.CANCELLING)
        run.status = WorkflowRunStatus.CANCELLING.value
    remaining = await session.scalar(
        select(TaskRunRow.id).where(
            TaskRunRow.workflow_run_id == run.id,
            TaskRunRow.id != task.id,
            TaskRunRow.status == TaskRunStatus.RUNNING.value,
        )
    )
    if remaining is not None:
        run.updated_at = now
        return
    ensure_run_transition(WorkflowRunStatus.CANCELLING, WorkflowRunStatus.CANCELLED)
    run.status = WorkflowRunStatus.CANCELLED.value
    run.error_reference = error_reference
    run.updated_at = now


async def _settle_dead_letter(
    _session: AsyncSession,
    run: WorkflowRunRow,
    task: TaskRunRow,
    step_run: WorkflowStepRunRow,
    now: datetime,
    error_reference: str,
) -> None:
    task.status = TaskRunStatus.DEAD_LETTER.value
    task.error_reference = error_reference
    _release_task(task, now)
    step_run.status = StepRunStatus.FAILED.value
    step_run.error_reference = error_reference
    step_run.updated_at = now
    ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.FAILED)
    run.status = WorkflowRunStatus.FAILED.value
    run.error_reference = error_reference
    run.updated_at = now


def _release_task(task: TaskRunRow, now: datetime) -> None:
    task.lease_token = None
    task.lease_expires_at = None
    task.updated_at = now


async def _advance(
    session: AsyncSession, run: WorkflowRunRow, output_reference: str, now: datetime
) -> None:
    definition = await _definition_for_run(session, run)
    dag_graph_version = 2
    if definition.graph_version == dag_graph_version:
        await _activate_ready_graph_steps(session, run, definition, now)
        return
    await _advance_linear(session, run, output_reference, now)


async def _advance_linear(
    session: AsyncSession, run: WorkflowRunRow, output_reference: str, now: datetime
) -> None:
    next_position = run.current_step_position + 1
    next_step = await session.scalar(
        select(WorkflowStepDefinitionRow).where(
            WorkflowStepDefinitionRow.definition_id == run.definition_id,
            WorkflowStepDefinitionRow.position == next_position,
        )
    )
    if next_step is None:
        ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.SUCCEEDED)
        run.status = WorkflowRunStatus.SUCCEEDED.value
        run.output_reference = output_reference
        run.error_reference = None
        run.updated_at = now
        await _append_run_event(
            session, run, "workflows.run-succeeded", now, {"schema": "run-succeeded.v1"}
        )
        return
    run.current_step_position = next_position
    await _schedule_step(session, run, _step_definition(next_step), output_reference, now)
    if run.pause_requested_at is not None:
        if run.status == WorkflowRunStatus.WAITING_APPROVAL.value:
            run.status = WorkflowRunStatus.PAUSED.value
        elif run.status == WorkflowRunStatus.RUNNING.value:  # pragma: no branch - state invariant.
            ensure_run_transition(WorkflowRunStatus.RUNNING, WorkflowRunStatus.PAUSED)
            run.status = WorkflowRunStatus.PAUSED.value
    run.updated_at = now


async def _initialize_graph(  # noqa: PLR0913 - assembles one immutable graph snapshot.
    session: AsyncSession,
    run: WorkflowRunRow,
    definition: WorkflowDefinition,
    resolved_inputs: dict[str, tuple[ResolvedInput, ...]],
    *,
    prompt_pin: str | None,
    model_pin: str | None,
    budget_reservation_refs: dict[str, str],
    now: datetime,
) -> None:
    for step in definition.steps:
        step_run_id = uuid4()
        supplied = {item.requirement_key: item for item in resolved_inputs.get(step.key, ())}
        inputs = tuple(
            supplied.get(requirement.key)
            or ResolvedInput(
                requirement.key,
                None,
                None,
                None,
                None,
                InputResolutionStatus.MISSING,
                now,
                "not-resolved",
                "not-resolved",
            )
            for requirement in step.requirements
        )
        manifest = _new_input_manifest(
            run,
            definition,
            step,
            step_run_id,
            inputs,
            prompt_pin=prompt_pin,
            model_pin=model_pin,
            budget_reservation_ref=budget_reservation_refs.get(step.key),
            now=now,
        )
        step_run = WorkflowStepRunRow(
            id=step_run_id,
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            workflow_run_id=run.id,
            step_definition_id=step.id,
            step_key=step.key,
            position=step.position,
            status=StepRunStatus.BLOCKED.value,
            attempt=0,
            input_reference=f"workflow-input-manifest://{manifest.id}",
            input_manifest_id=manifest.id,
            iteration=run.iteration,
            created_at=now,
            updated_at=now,
            version=1,
        )
        session.add(step_run)
        session.add(_input_manifest_row(manifest, run.workspace_id, run.project_id))
        for item in inputs:
            if item.status is not InputResolutionStatus.READY:
                continue
            session.add(
                WorkflowDependencyEdgeRow(
                    id=uuid4(),
                    workspace_id=run.workspace_id,
                    project_id=run.project_id,
                    consumer_run_id=run.id,
                    consumer_step_run_id=step_run_id,
                    producer_reference=item.reference or "",
                    producer_revision=item.revision or "",
                    producer_hash=item.content_hash or "",
                    requirement_key=item.requirement_key,
                    created_at=now,
                )
            )
    await session.flush()
    await _activate_ready_graph_steps(session, run, definition, now)


async def _activate_ready_graph_steps(  # noqa: PLR0912,PLR0915 - state-machine coordinator.
    session: AsyncSession,
    run: WorkflowRunRow,
    definition: WorkflowDefinition,
    now: datetime,
) -> None:
    step_rows = tuple(
        (
            await session.scalars(
                select(WorkflowStepRunRow)
                .where(WorkflowStepRunRow.workflow_run_id == run.id)
                .order_by(WorkflowStepRunRow.position)
            )
        ).all()
    )
    rows_by_key = {row.step_key: row for row in step_rows}
    changed = True
    while changed:
        changed = False
        for step in definition.steps:
            row = rows_by_key[step.key]
            if row.status != StepRunStatus.BLOCKED.value:
                continue
            manifest = (
                await session.get(WorkflowInputManifestRow, row.input_manifest_id)
                if row.input_manifest_id is not None
                else None
            )
            if manifest is None:
                row.blocked_reason = "workflow-input://manifest-missing"
                continue
            blocking = _blocking_input(step, _input_manifest(manifest).resolved_inputs)
            if blocking is not None:
                row.blocked_reason = f"workflow-input://{blocking.status.value}"
                continue
            dependencies = definition.dependencies_for(step)
            dependency_rows = tuple(rows_by_key[key] for key in dependencies)
            if not all(
                item.status in {StepRunStatus.SUCCEEDED.value, StepRunStatus.SKIPPED.value}
                for item in dependency_rows
            ):
                row.blocked_reason = "workflow-dependency://waiting"
                continue
            matches = condition_matches(
                step,
                dependency_statuses={
                    item.step_key: StepRunStatus(item.status) for item in dependency_rows
                },
                dependency_outputs={
                    item.step_key: item.output_reference for item in dependency_rows
                },
            )
            row.condition_result = matches
            row.blocked_reason = None
            row.updated_at = now
            if not matches:
                row.status = StepRunStatus.SKIPPED.value
                await _append_run_event(
                    session,
                    run,
                    "workflows.step-skipped",
                    now,
                    {
                        "schema": "step-skipped.v1",
                        "step_key": step.key,
                        "reason": "condition_false",
                    },
                )
                changed = True
                continue
            await _activate_existing_step(session, run, row, step, now)
            changed = True

    statuses = tuple(StepRunStatus(row.status) for row in step_rows)
    non_terminal = tuple(
        row
        for row in step_rows
        if StepRunStatus(row.status)
        not in {
            StepRunStatus.SUCCEEDED,
            StepRunStatus.SKIPPED,
            StepRunStatus.FAILED,
            StepRunStatus.CANCELLED,
            StepRunStatus.STALE,
        }
    )
    if non_terminal:
        run.current_step_position = min(row.position for row in non_terminal)
    if all(status in {StepRunStatus.SUCCEEDED, StepRunStatus.SKIPPED} for status in statuses):
        if run.status != WorkflowRunStatus.RUNNING.value:
            current = WorkflowRunStatus(run.status)
            if current is not WorkflowRunStatus.RUNNING:
                ensure_run_transition(current, WorkflowRunStatus.RUNNING)
                run.status = WorkflowRunStatus.RUNNING.value
        ensure_run_transition(WorkflowRunStatus.RUNNING, WorkflowRunStatus.SUCCEEDED)
        run.status = WorkflowRunStatus.SUCCEEDED.value
        completed = tuple(row for row in step_rows if row.output_reference is not None)
        run.output_reference = (
            max(completed, key=lambda row: row.position).output_reference
            if completed
            else run.input_reference
        )
        run.error_reference = None
        await _append_run_event(
            session, run, "workflows.run-succeeded", now, {"schema": "run-succeeded.v1"}
        )
    elif run.status not in {
        WorkflowRunStatus.PAUSED.value,
        WorkflowRunStatus.CANCELLING.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.FAILED.value,
    }:
        approvals = await _pending_approval(session, run.id)
        tasks = await _active_tasks(session, run)
        if approvals is not None:
            _move_run_to_waiting_approval(run)
        elif tasks:
            if run.status in {
                WorkflowRunStatus.WAITING_RESOURCE.value,
                WorkflowRunStatus.WAITING_CONFIGURATION.value,
                WorkflowRunStatus.WAITING_BUDGET.value,
            }:
                ensure_run_transition(WorkflowRunStatus(run.status), WorkflowRunStatus.PENDING)
                run.status = WorkflowRunStatus.PENDING.value
        else:
            target = WorkflowRunStatus.WAITING_RESOURCE
            if run.status != target.value:
                ensure_run_transition(WorkflowRunStatus(run.status), target)
                run.status = target.value
    run.updated_at = now


async def _activate_existing_step(
    session: AsyncSession,
    run: WorkflowRunRow,
    step_run: WorkflowStepRunRow,
    step: StepDefinition,
    now: datetime,
) -> None:
    if step.kind is StepKind.APPROVAL:
        step_run.status = StepRunStatus.WAITING_APPROVAL.value
        manifest = (
            await session.get(WorkflowInputManifestRow, step_run.input_manifest_id)
            if step_run.input_manifest_id is not None
            else None
        )
        if manifest is None:
            raise InvalidStateError("Workflow step input manifest is unavailable.")
        session.add(
            ApprovalRequestRow(
                id=uuid4(),
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                workflow_run_id=run.id,
                step_run_id=step_run.id,
                requested_by=run.requested_by,
                status=ApprovalStatus.PENDING.value,
                approval_policy_ref=step.approval_policy_ref or run.approval_policy_ref,
                input_digest=manifest.input_digest,
                expires_at=now + timedelta(seconds=step.approval_expires_seconds or 0),
                created_at=now,
            )
        )
        await _append_run_event(
            session,
            run,
            "workflows.approval-requested",
            now,
            {"schema": "approval-requested.v1", "step_key": step.key},
        )
        return
    step_run.status = StepRunStatus.PENDING.value
    operation_key = _operation_key(run, step, step_run.iteration)
    task = TaskRunRow(
        id=uuid4(),
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        workflow_run_id=run.id,
        step_run_id=step_run.id,
        status=TaskRunStatus.PENDING.value,
        attempt=0,
        idempotency_key=operation_key,
        operation_key=operation_key,
        input_reference=step_run.input_reference,
        available_at=now,
        created_at=now,
        updated_at=now,
        version=1,
    )
    session.add(task)
    await session.flush()
    if run.pause_requested_at is None:
        await _dispatch(session, run, task, now, now)


def _blocking_input(
    step: StepDefinition, resolved_inputs: tuple[ResolvedInput, ...]
) -> ResolvedInput | None:
    by_key = {item.requirement_key: item for item in resolved_inputs}
    for requirement in step.requirements:
        item = by_key.get(requirement.key)
        if requirement.mandatory and (
            item is None or item.status is not InputResolutionStatus.READY
        ):
            return item or ResolvedInput(
                requirement.key,
                None,
                None,
                None,
                None,
                InputResolutionStatus.MISSING,
                datetime.min.replace(tzinfo=UTC),
                "not-resolved",
                "not-resolved",
            )
    return None


def _move_run_to_waiting_approval(run: WorkflowRunRow) -> None:
    current = WorkflowRunStatus(run.status)
    if current is WorkflowRunStatus.WAITING_APPROVAL:
        return
    if current is not WorkflowRunStatus.RUNNING:
        ensure_run_transition(current, WorkflowRunStatus.RUNNING)
        run.status = WorkflowRunStatus.RUNNING.value
    ensure_run_transition(WorkflowRunStatus.RUNNING, WorkflowRunStatus.WAITING_APPROVAL)
    run.status = WorkflowRunStatus.WAITING_APPROVAL.value


def _operation_key(run: WorkflowRunRow, step: StepDefinition, iteration: int) -> str:
    template = step.operation_key_template
    if template is None:
        return f"{run.id}:{step.key}:{iteration}"
    return (
        template.replace("{run_id}", str(run.id))
        .replace("{step_key}", step.key)
        .replace("{iteration}", str(iteration))
    )


async def _definition_for_run(session: AsyncSession, run: WorkflowRunRow) -> WorkflowDefinition:
    definition_row = await session.get(WorkflowDefinitionRow, run.definition_id)
    if definition_row is None:
        raise InvalidStateError("Workflow definition is unavailable.")
    step_rows = tuple(
        (
            await session.scalars(
                select(WorkflowStepDefinitionRow)
                .where(WorkflowStepDefinitionRow.definition_id == run.definition_id)
                .order_by(WorkflowStepDefinitionRow.position)
            )
        ).all()
    )
    return _definition(definition_row, step_rows)


async def _schedule_step(
    session: AsyncSession,
    run: WorkflowRunRow,
    step: StepDefinition,
    input_reference: str,
    now: datetime,
) -> None:
    step_run = WorkflowStepRunRow(
        id=uuid4(),
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        workflow_run_id=run.id,
        step_definition_id=step.id,
        step_key=step.key,
        position=step.position,
        status=(
            StepRunStatus.WAITING_APPROVAL.value
            if step.kind is StepKind.APPROVAL
            else StepRunStatus.PENDING.value
        ),
        attempt=0,
        input_reference=input_reference,
        created_at=now,
        updated_at=now,
        version=1,
    )
    session.add(step_run)
    await session.flush()
    if step.kind is StepKind.APPROVAL:
        current = WorkflowRunStatus(run.status)
        if current is WorkflowRunStatus.PENDING:
            run.status = WorkflowRunStatus.RUNNING.value
            current = WorkflowRunStatus.RUNNING
        ensure_run_transition(current, WorkflowRunStatus.WAITING_APPROVAL)
        run.status = WorkflowRunStatus.WAITING_APPROVAL.value
        session.add(
            ApprovalRequestRow(
                id=uuid4(),
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                workflow_run_id=run.id,
                step_run_id=step_run.id,
                requested_by=run.requested_by,
                status=ApprovalStatus.PENDING.value,
                approval_policy_ref=run.approval_policy_ref,
                input_digest=hashlib.sha256(
                    f"{run.definition_id}:{run.definition_version}:{step_run.input_reference}".encode()
                ).hexdigest(),
                expires_at=now + timedelta(seconds=step.approval_expires_seconds or 0),
                created_at=now,
            )
        )
        await _append_run_event(
            session,
            run,
            "workflows.approval-requested",
            now,
            {"schema": "approval-requested.v1", "step_key": step.key},
        )
        return
    task = TaskRunRow(
        id=uuid4(),
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        workflow_run_id=run.id,
        step_run_id=step_run.id,
        status=TaskRunStatus.PENDING.value,
        attempt=0,
        idempotency_key=f"{run.id}:{step.key}",
        operation_key=f"{run.id}:{step.key}:1",
        input_reference=input_reference,
        available_at=now,
        created_at=now,
        updated_at=now,
        version=1,
    )
    session.add(task)
    await session.flush()
    if run.pause_requested_at is None:
        await _dispatch(session, run, task, now, now)


async def _dispatch(
    session: AsyncSession,
    run: WorkflowRunRow,
    task: TaskRunRow,
    now: datetime,
    available_at: datetime,
) -> None:
    event = EventEnvelope(
        uuid4(),
        run.workspace_id,
        run.project_id,
        run.id,
        "workflows.task-dispatched",
        1,
        {
            "schema": "task-dispatched.v1",
            "workflow_run_id": str(run.id),
            "task_id": str(task.id),
            "task_idempotency_key": task.idempotency_key,
        },
        now,
        available_at,
    )
    await SqlAlchemyOutboxWriter(session).append(event)


async def _append_run_event(
    session: AsyncSession,
    run: WorkflowRunRow,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, object],
) -> None:
    run.event_sequence += 1
    session.add(
        WorkflowRunEventRow(
            id=uuid4(),
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            workflow_run_id=run.id,
            sequence=run.event_sequence,
            event_type=event_type,
            event_version=1,
            payload=payload,
            occurred_at=occurred_at,
        )
    )
    await session.flush()


def _run_row(run: WorkflowRun) -> WorkflowRunRow:
    return WorkflowRunRow(
        id=run.id,
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        definition_id=run.definition_id,
        definition_name=run.definition_name,
        definition_version=run.definition_version,
        status=run.status.value,
        idempotency_key=run.idempotency_key,
        input_reference=run.input_reference,
        output_reference=run.output_reference,
        error_reference=run.error_reference,
        requested_by=run.requested_by,
        actor_kind=run.actor_kind,
        correlation_id=run.correlation_id,
        permission_snapshot=list(run.permission_snapshot),
        policy_version=run.policy_version,
        approval_policy_ref=run.approval_policy_ref,
        auth_method=run.auth_method,
        credential_id=run.credential_id,
        parent_run_id=run.parent_run_id,
        previous_run_id=run.previous_run_id,
        schedule_id=run.schedule_id,
        iteration=run.iteration,
        current_step_position=run.current_step_position,
        event_sequence=0,
        pause_requested_at=run.pause_requested_at,
        cancel_requested_at=run.cancel_requested_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        version=run.version,
    )


def _run(row: WorkflowRunRow) -> WorkflowRun:
    return WorkflowRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.definition_id,
        row.definition_name,
        row.definition_version,
        WorkflowRunStatus(row.status),
        row.idempotency_key,
        row.input_reference,
        row.requested_by,
        row.actor_kind,
        row.correlation_id,
        row.created_at,
        row.updated_at,
        row.current_step_position,
        row.output_reference,
        row.error_reference,
        row.pause_requested_at,
        row.cancel_requested_at,
        row.version,
        tuple(row.permission_snapshot),
        row.policy_version,
        row.approval_policy_ref,
        row.auth_method,
        row.credential_id,
        row.parent_run_id,
        row.previous_run_id,
        row.schedule_id,
        row.iteration,
    )


def _step_definition_row(definition_id: UUID, step: StepDefinition) -> WorkflowStepDefinitionRow:
    return WorkflowStepDefinitionRow(
        id=step.id,
        definition_id=definition_id,
        step_key=step.key,
        position=step.position,
        kind=step.kind.value,
        timeout_seconds=step.timeout_seconds,
        max_attempts=step.retry_policy.max_attempts,
        initial_delay_seconds=step.retry_policy.initial_delay_seconds,
        maximum_delay_seconds=step.retry_policy.maximum_delay_seconds,
        retry_multiplier=step.retry_policy.multiplier,
        delay_seconds=step.delay_seconds,
        fail_until_attempt=step.fail_until_attempt,
        approval_expires_seconds=step.approval_expires_seconds,
        compensation_hook=step.compensation_hook,
        executor_key=step.executor_key,
        depends_on=list(step.depends_on),
        input_schema=dict(step.input_schema),
        output_schema=dict(step.output_schema),
        requirements=[_stage_requirement_data(item) for item in step.requirements],
        condition={
            "operator": step.condition.operator.value,
            "source_step_key": step.condition.source_step_key,
            "expected_value": step.condition.expected_value,
        },
        budget_limit_microusd=step.budget_limit_microusd,
        budget_reservation_required=step.budget_reservation_required,
        approval_policy_ref=step.approval_policy_ref,
        max_iterations=step.max_iterations,
        external_side_effect=step.external_side_effect,
        operation_key_template=step.operation_key_template,
    )


def _step_definition(row: WorkflowStepDefinitionRow) -> StepDefinition:
    return StepDefinition(
        row.id,
        row.step_key,
        row.position,
        StepKind(row.kind),
        row.timeout_seconds,
        RetryPolicy(
            row.max_attempts,
            row.initial_delay_seconds,
            row.maximum_delay_seconds,
            row.retry_multiplier,
        ),
        row.delay_seconds,
        row.fail_until_attempt,
        row.approval_expires_seconds,
        row.compensation_hook,
        row.executor_key,
        tuple(row.depends_on),
        dict(row.input_schema),
        dict(row.output_schema),
        tuple(_stage_requirement(item) for item in row.requirements),
        _condition(row.condition),
        row.budget_limit_microusd,
        row.budget_reservation_required,
        row.approval_policy_ref,
        row.max_iterations,
        row.external_side_effect,
        row.operation_key_template,
    )


def _definition(
    row: WorkflowDefinitionRow, steps: tuple[WorkflowStepDefinitionRow, ...]
) -> WorkflowDefinition:
    return WorkflowDefinition(
        row.id,
        row.name,
        row.definition_version,
        tuple(_step_definition(step) for step in steps),
        row.created_at,
        row.graph_version,
        WorkflowDefinitionStatus(row.status),
        row.description,
        row.checksum,
    )


def _step_run(row: WorkflowStepRunRow) -> StepRun:
    return StepRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.step_definition_id,
        row.step_key,
        row.position,
        StepRunStatus(row.status),
        row.attempt,
        row.input_reference,
        row.created_at,
        row.updated_at,
        row.deadline,
        row.output_reference,
        row.error_reference,
        row.version,
        row.input_manifest_id,
        row.iteration,
        row.blocked_reason,
        row.condition_result,
    )


def _task(row: TaskRunRow) -> TaskRun:
    return TaskRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.step_run_id,
        TaskRunStatus(row.status),
        row.attempt,
        row.idempotency_key,
        row.input_reference,
        row.available_at,
        row.created_at,
        row.updated_at,
        row.deadline,
        row.output_reference,
        row.error_reference,
        row.lease_token,
        row.lease_expires_at,
        row.last_delivery_event_id,
        row.version,
        row.operation_key,
        row.provider_job_id,
    )


def _approval(row: ApprovalRequestRow) -> ApprovalRequest:
    return ApprovalRequest(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.step_run_id,
        row.requested_by,
        ApprovalStatus(row.status),
        row.expires_at,
        row.created_at,
        row.approval_policy_ref,
        row.input_digest,
    )


def _approval_decision_row(record: ApprovalRecord) -> ApprovalDecisionRow:
    return ApprovalDecisionRow(
        id=record.id,
        workspace_id=record.workspace_id,
        request_id=record.request_id,
        actor_id=record.actor_id,
        decision=record.decision.value,
        reason=record.reason,
        decided_at=record.decided_at,
        approval_policy_ref=record.approval_policy_ref,
        input_digest=record.input_digest,
    )


def _run_event(row: WorkflowRunEventRow) -> WorkflowRunEvent:
    return WorkflowRunEvent(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.sequence,
        row.event_type,
        row.event_version,
        dict(row.payload),
        row.occurred_at,
    )


def _stage_requirement_data(requirement: StageRequirement) -> dict[str, object]:
    return {
        "key": requirement.key,
        "artifact_type": requirement.artifact_type,
        "scope": requirement.scope,
        "branch": requirement.branch,
        "accepted_required": requirement.accepted_required,
        "min_schema": requirement.min_schema,
        "mandatory": requirement.mandatory,
        "freshness": requirement.freshness.value,
        "max_age_seconds": requirement.max_age_seconds,
    }


def _stage_requirement(value: dict[str, object]) -> StageRequirement:
    return StageRequirement(
        cast("str", value["key"]),
        cast("str", value["artifact_type"]),
        cast("str", value["scope"]),
        cast("str | None", value.get("branch")),
        cast("bool", value.get("accepted_required", True)),
        cast("int", value.get("min_schema", 1)),
        cast("bool", value.get("mandatory", True)),
        RequirementFreshness(cast("str", value.get("freshness", "current"))),
        cast("int | None", value.get("max_age_seconds")),
    )


def _condition(value: dict[str, object]) -> ConditionExpression:
    return ConditionExpression(
        ConditionOperator(cast("str", value.get("operator", "always"))),
        cast("str | None", value.get("source_step_key")),
        cast("str | None", value.get("expected_value")),
    )


def _resolved_input_data(item: ResolvedInput) -> dict[str, object]:
    return {
        "requirement_key": item.requirement_key,
        "reference": item.reference,
        "revision": item.revision,
        "content_hash": item.content_hash,
        "schema_version": item.schema_version,
        "status": item.status.value,
        "resolved_at": item.resolved_at.isoformat(),
        "grant_version": item.grant_version,
        "consent_version": item.consent_version,
    }


def _resolved_input(value: dict[str, object]) -> ResolvedInput:
    return ResolvedInput(
        cast("str", value["requirement_key"]),
        cast("str | None", value.get("reference")),
        cast("str | None", value.get("revision")),
        cast("str | None", value.get("content_hash")),
        cast("int | None", value.get("schema_version")),
        InputResolutionStatus(cast("str", value["status"])),
        datetime.fromisoformat(cast("str", value["resolved_at"])),
        cast("str", value["grant_version"]),
        cast("str", value["consent_version"]),
    )


def _new_input_manifest(  # noqa: PLR0913 - manifest pins span distinct trust domains.
    run: WorkflowRunRow,
    definition: WorkflowDefinition,
    step: StepDefinition,
    step_run_id: UUID,
    resolved_inputs: tuple[ResolvedInput, ...],
    *,
    prompt_pin: str | None,
    model_pin: str | None,
    budget_reservation_ref: str | None,
    now: datetime,
) -> StepInputManifest:
    manifest = StepInputManifest(
        uuid4(),
        run.id,
        step_run_id,
        definition.id,
        definition.version,
        step.id,
        step.executor_key,
        resolved_inputs,
        prompt_pin,
        model_pin,
        run.approval_policy_ref,
        run.policy_version or "legacy-policy",
        "not-applicable",
        "not-applicable",
        budget_reservation_ref,
        "0" * 64,
        now,
    )
    return StepInputManifest(
        manifest.id,
        manifest.workflow_run_id,
        manifest.step_run_id,
        manifest.definition_id,
        manifest.definition_version,
        manifest.step_definition_id,
        manifest.executor_key,
        manifest.resolved_inputs,
        manifest.prompt_pin,
        manifest.model_pin,
        manifest.policy_pin,
        manifest.permission_version,
        manifest.grant_version,
        manifest.consent_version,
        manifest.budget_reservation_ref,
        manifest_digest(manifest),
        manifest.created_at,
    )


def _input_manifest_row(
    manifest: StepInputManifest, workspace_id: UUID, project_id: UUID
) -> WorkflowInputManifestRow:
    return WorkflowInputManifestRow(
        id=manifest.id,
        workspace_id=workspace_id,
        project_id=project_id,
        workflow_run_id=manifest.workflow_run_id,
        step_run_id=manifest.step_run_id,
        definition_id=manifest.definition_id,
        definition_version=manifest.definition_version,
        step_definition_id=manifest.step_definition_id,
        executor_key=manifest.executor_key,
        resolved_inputs=[_resolved_input_data(item) for item in manifest.resolved_inputs],
        prompt_pin=manifest.prompt_pin,
        model_pin=manifest.model_pin,
        policy_pin=manifest.policy_pin,
        permission_version=manifest.permission_version,
        grant_version=manifest.grant_version,
        consent_version=manifest.consent_version,
        budget_reservation_ref=manifest.budget_reservation_ref,
        input_digest=manifest.input_digest,
        created_at=manifest.created_at,
    )


def _input_manifest(row: WorkflowInputManifestRow) -> StepInputManifest:
    return StepInputManifest(
        row.id,
        row.workflow_run_id,
        row.step_run_id,
        row.definition_id,
        row.definition_version,
        row.step_definition_id,
        row.executor_key,
        tuple(_resolved_input(item) for item in row.resolved_inputs),
        row.prompt_pin,
        row.model_pin,
        row.policy_pin,
        row.permission_version,
        row.grant_version,
        row.consent_version,
        row.budget_reservation_ref,
        row.input_digest,
        row.created_at,
    )


def _read_receipt_row(receipt: ReadReceipt) -> WorkflowReadReceiptRow:
    return WorkflowReadReceiptRow(
        id=receipt.id,
        workspace_id=receipt.workspace_id,
        project_id=receipt.project_id,
        workflow_run_id=receipt.workflow_run_id,
        step_run_id=receipt.step_run_id,
        source_reference=receipt.source_reference,
        source_revision=receipt.source_revision,
        source_hash=receipt.source_hash,
        section_reference=receipt.section_reference,
        loaded_bytes=receipt.loaded_bytes,
        token_count=receipt.token_count,
        input_digest=receipt.input_digest,
        created_at=receipt.created_at,
    )


def _read_receipt(row: WorkflowReadReceiptRow) -> ReadReceipt:
    return ReadReceipt(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.step_run_id,
        row.source_reference,
        row.source_revision,
        row.source_hash,
        row.section_reference,
        row.loaded_bytes,
        row.token_count,
        row.input_digest,
        row.created_at,
    )


def _dependency_edge(row: WorkflowDependencyEdgeRow) -> DependencyEdge:
    return DependencyEdge(
        row.id,
        row.workspace_id,
        row.project_id,
        row.consumer_run_id,
        row.consumer_step_run_id,
        row.producer_reference,
        row.producer_revision,
        row.producer_hash,
        row.requirement_key,
        row.created_at,
        row.invalidated_at,
    )


def _compensation(row: WorkflowCompensationRecordRow) -> CompensationRecord:
    return CompensationRecord(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.task_run_id,
        row.operation_key,
        row.hook,
        CompensationStatus(row.status),
        row.created_at,
        row.updated_at,
        row.result_reference,
        row.error_reference,
    )


def _schedule_row(schedule: WorkflowSchedule) -> WorkflowScheduleRow:
    return WorkflowScheduleRow(
        id=schedule.id,
        workspace_id=schedule.workspace_id,
        project_id=schedule.project_id,
        definition_id=schedule.definition_id,
        definition_name=schedule.definition_name,
        definition_version=schedule.definition_version,
        schedule_expression=schedule.schedule_expression,
        timezone=schedule.timezone,
        misfire_policy=schedule.misfire_policy.value,
        status=schedule.status.value,
        input_reference=schedule.input_reference,
        next_due_at=schedule.next_due_at,
        requested_by=schedule.requested_by,
        idempotency_prefix=schedule.idempotency_prefix,
        last_claimed_at=schedule.last_claimed_at,
        last_run_id=schedule.last_run_id,
        lease_token=schedule.lease_token,
        lease_until=schedule.lease_until,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        version=schedule.version,
    )


def _schedule(row: WorkflowScheduleRow) -> WorkflowSchedule:
    return WorkflowSchedule(
        row.id,
        row.workspace_id,
        row.project_id,
        row.definition_id,
        row.definition_name,
        row.definition_version,
        row.schedule_expression,
        row.timezone,
        MisfirePolicy(row.misfire_policy),
        ScheduleStatus(row.status),
        row.input_reference,
        row.next_due_at,
        row.requested_by,
        row.idempotency_prefix,
        row.created_at,
        row.updated_at,
        row.last_claimed_at,
        row.last_run_id,
        row.lease_token,
        row.lease_until,
        row.version,
    )
