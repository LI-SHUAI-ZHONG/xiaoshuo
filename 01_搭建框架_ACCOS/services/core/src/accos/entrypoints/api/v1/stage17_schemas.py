"""Typed execution-17 resource and realtime-event transport contracts."""

# ruff: noqa: TC001 - Pydantic resolves the public enum annotations at runtime.

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID  # noqa: TC003 - Pydantic resolves public annotations.

from pydantic import AwareDatetime, Field

from accos.entrypoints.api.v1.schemas import ApiModel, Name
from accos.modules.agents.domain import (
    AgentErrorCode,
    AgentResultKind,
    AgentRunStatus,
    ProtectedOperation,
)
from accos.modules.consistency.domain import (
    CanonLevel,
    FindingSeverity,
    FindingStatus,
    FindingType,
    ResolutionDecision,
    ResolutionStatus,
    ValidationStatus,
)
from accos.modules.creative.common import CreativeDecision, CreativeOwner, CreativeRecordStatus
from accos.modules.evolution.domain import ChangeAction, EvolutionDecision, EvolutionState
from accos.modules.feedback.domain import (
    ConsentStatus,
    DiagnosticSeverity,
    ExperimentStatus,
    FeedbackSource,
    FeedbackStatus,
    MetricSensitivity,
)
from accos.modules.knowledge.domain import (
    IngestionStatus,
    KnowledgeErrorCode,
    VerificationPolicy,
    VerificationStatus,
)
from accos.modules.memory.domain import (
    MemoryConflictStatus,
    MemoryScope,
    MemoryStatus,
    RetentionKind,
)
from accos.modules.models.domain import ModelCapability, ProviderHealthState
from accos.modules.quality.domain import DimensionStatus, QualityStatus
from accos.modules.workflows.domain import (
    ApprovalStatus,
    StepRunStatus,
    TaskRunStatus,
    WorkflowApprovalDecision,
    WorkflowRunStatus,
)

Code = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_.-]*$")]
OpaqueReference = Annotated[
    str,
    Field(min_length=4, max_length=500, pattern=r"^[a-z][a-z0-9+.-]*://\S+$"),
]


class WorkflowDefinitionResponse(ApiModel):
    name: str
    version: int = Field(ge=1)
    step_keys: list[str]


class WorkflowDefinitionCollectionResponse(ApiModel):
    items: list[WorkflowDefinitionResponse]


class WorkflowRunCreateRequest(ApiModel):
    input_reference: OpaqueReference = "fixture-token://framework-smoke"


class WorkflowRunResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    definition_name: str
    definition_version: int
    status: WorkflowRunStatus
    input_reference: str
    requested_by: UUID
    correlation_id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    current_step_position: int
    output_reference: str | None
    error_reference: str | None
    version: int


class AsyncRunReference(ApiModel):
    run_id: UUID
    task_url: str
    status_url: str
    events_url: str | None = None
    accepted_at: AwareDatetime


class StepRunResponse(ApiModel):
    id: UUID
    workflow_run_id: UUID
    step_key: str
    position: int
    status: StepRunStatus
    attempt: int
    created_at: AwareDatetime
    updated_at: AwareDatetime
    version: int


class StepRunCollectionResponse(ApiModel):
    items: list[StepRunResponse]


class TaskRunResponse(ApiModel):
    id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    status: TaskRunStatus
    attempt: int
    available_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    version: int


class TaskRunCollectionResponse(ApiModel):
    items: list[TaskRunResponse]


class ApprovalResponse(ApiModel):
    id: UUID
    workflow_run_id: UUID
    step_run_id: UUID
    requested_by: UUID
    status: ApprovalStatus
    expires_at: AwareDatetime
    created_at: AwareDatetime
    approval_policy_ref: str = "legacy_dual_control"
    input_digest: str = ""
    can_decide: bool = False


class ApprovalDecisionRequest(ApiModel):
    decision: WorkflowApprovalDecision
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class AgentBudgetResponse(ApiModel):
    max_steps: int = Field(ge=1)
    max_recursion_depth: int = Field(ge=0)
    max_parallelism: int = Field(ge=1)
    max_duration_seconds: float = Field(gt=0)
    max_calls: int = Field(ge=1)
    max_tokens: int = Field(ge=1)


class AgentDescriptorResponse(ApiModel):
    agent_id: str
    version: str
    capabilities: list[str]
    allowed_tool_ids: list[str]
    model_policy_id: str
    model_policy_version: str
    budget_limit: AgentBudgetResponse


class AgentCollectionResponse(ApiModel):
    items: list[AgentDescriptorResponse]


class AgentRunCreateRequest(ApiModel):
    goal_reference: OpaqueReference
    max_steps: int = Field(default=4, ge=1, le=100)
    max_calls: int = Field(default=8, ge=1, le=1000)
    max_tokens: int = Field(default=2048, ge=1, le=1_000_000)


class AgentRunResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    agent_id: str
    agent_version: str
    status: AgentRunStatus
    attempt: int
    requested_by: UUID
    correlation_id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    workflow_run_id: UUID | None
    result_kind: AgentResultKind | None
    result_reference: str | None
    protected_operations: list[ProtectedOperation]
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    tokens: int = Field(ge=0)
    error_code: AgentErrorCode | None


class ModelProviderStatusResponse(ApiModel):
    provider_id: str
    state: ProviderHealthState
    capabilities: list[ModelCapability]
    consecutive_failures: int
    in_flight: int
    circuit_open_until: AwareDatetime | None


class ModelStatusResponse(ApiModel):
    protocol_version: Literal["models.v1"] = "models.v1"
    providers: list[ModelProviderStatusResponse]


class ToolStatusItem(ApiModel):
    tool_id: str
    version: str
    capabilities: list[str]
    idempotent: bool
    configured: bool = True


class ToolStatusResponse(ApiModel):
    protocol_version: Literal["tools.v1"] = "tools.v1"
    tools: list[ToolStatusItem]


class IngestionCreateRequest(ApiModel):
    asset_id: UUID
    verification_policy: VerificationPolicy = VerificationPolicy.NOT_REQUIRED


class IngestionRunResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    document_id: UUID
    document_version_id: UUID
    status: IngestionStatus
    verification_policy: VerificationPolicy
    verification_status: VerificationStatus
    requested_by: UUID
    correlation_id: UUID
    attempt: int
    created_at: AwareDatetime
    updated_at: AwareDatetime
    failed_stage: IngestionStatus | None
    error_code: KnowledgeErrorCode | None
    retryable: bool
    workflow_run_id: UUID | None


class IngestionAcceptedResponse(ApiModel):
    ingestion_run_id: UUID
    workflow_run_id: UUID
    status_url: str
    task_url: str
    events_url: str
    accepted_at: AwareDatetime


class KnowledgeDocumentResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    created_at: AwareDatetime


class KnowledgeSearchRequest(ApiModel):
    query: Annotated[str, Field(min_length=1, max_length=2000)]
    top_k: int = Field(default=5, ge=1, le=100)
    source_ids: list[UUID] = Field(default_factory=list, max_length=100)
    document_version_ids: list[UUID] = Field(default_factory=list, max_length=100)
    verification_statuses: list[VerificationStatus] = Field(default_factory=list)


class RetrievalCitationResponse(ApiModel):
    id: UUID
    document_id: UUID
    document_version_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    chunk_id: UUID
    locator: str
    verification_status: VerificationStatus


class RetrievalHitResponse(ApiModel):
    score: float
    content: str
    citation: RetrievalCitationResponse


class KnowledgeSearchResponse(ApiModel):
    query: str
    hits: list[RetrievalHitResponse]


class MemoryWriteRequest(ApiModel):
    scope: Literal["working", "session", "project"] = "project"
    memory_type: Code
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    valid_from: AwareDatetime
    valid_until: AwareDatetime | None = None
    observed_at: AwareDatetime
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    provenance_kind: Code
    provenance_reference: OpaqueReference
    retention_kind: RetentionKind = RetentionKind.KEEP
    ttl_seconds: int | None = Field(default=None, ge=1)
    decay_half_life_seconds: int | None = Field(default=None, ge=1)


class MemoryProvenanceResponse(ApiModel):
    kind: str
    reference: str


class MemoryResponse(ApiModel):
    id: UUID
    logical_id: UUID
    version: int
    workspace_id: UUID
    scope: MemoryScope
    memory_type: str
    content: str
    project_id: UUID | None
    valid_from: AwareDatetime
    valid_until: AwareDatetime | None
    observed_at: AwareDatetime
    importance: float
    confidence: float
    provenance: MemoryProvenanceResponse
    status: MemoryStatus
    current: bool
    created_by: UUID
    created_at: AwareDatetime


class MemoryRevisionRequest(ApiModel):
    content: Annotated[str, Field(min_length=1, max_length=20_000)]


class MemoryConflictResponse(ApiModel):
    id: UUID
    current_record_id: UUID
    candidate_record_id: UUID
    candidate_resolutions: list[str]
    status: MemoryConflictStatus
    proposed_by: UUID
    proposed_at: AwareDatetime
    decided_by: UUID | None
    decided_at: AwareDatetime | None


class MemoryConflictDecisionRequest(ApiModel):
    accept_candidate: bool


class ContextPackageCreateRequest(ApiModel):
    task_reference: OpaqueReference
    budget_chars: int = Field(ge=1, le=1_000_000)
    scopes: list[MemoryScope] = Field(min_length=1, max_length=7)
    memory_types: list[Code] = Field(min_length=1, max_length=100)
    budget_tokens: int | None = Field(default=None, ge=1, le=1_000_000)


class ContextItemResponse(ApiModel):
    record_id: UUID
    scope: MemoryScope
    memory_type: str
    content: str
    score: float


class ContextPackageResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    task_reference: str
    budget_chars: int
    used_chars: int
    items: list[ContextItemResponse]
    checksum: str
    created_by: UUID
    created_at: AwareDatetime
    budget_tokens: int | None
    used_tokens: int


class CreativeCreateRequest(ApiModel):
    label: Name


class WorkCreateRequest(CreativeCreateRequest):
    world_ids: list[UUID] = Field(default_factory=list, max_length=100)
    character_ids: list[UUID] = Field(default_factory=list, max_length=100)


class CreativeContainerResponse(ApiModel):
    owner: CreativeOwner
    id: UUID
    workspace_id: UUID
    project_id: UUID
    label: str
    created_by: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    version: int


class DraftCreateRequest(ApiModel):
    logical_id: UUID | None = None
    record_version: int = Field(default=1, ge=1)
    source_reference: OpaqueReference | None = None
    sequence: int | None = Field(default=None, ge=0)


class DraftResponse(ApiModel):
    owner: CreativeOwner
    id: UUID
    logical_id: UUID
    record_version: int
    workspace_id: UUID
    project_id: UUID
    aggregate_id: UUID
    status: CreativeRecordStatus
    current: bool
    source_reference: str | None
    sequence: int | None
    created_by: UUID
    created_at: AwareDatetime


class CreativeDecisionRequest(ApiModel):
    decision: CreativeDecision


class RequiredFieldAssertionRequest(ApiModel):
    evidence_reference: OpaqueReference
    field_code: Code
    present: bool


class ReferenceAssertionRequest(ApiModel):
    evidence_reference: OpaqueReference
    exists: bool


class VersionAssertionRequest(ApiModel):
    evidence_reference: OpaqueReference
    expected_version: int = Field(ge=1)
    current_version: int = Field(ge=0)


class CanonChangeAssertionRequest(ApiModel):
    canon_reference: OpaqueReference
    level: CanonLevel
    modifies_current: bool
    explicitly_authorized: bool


class ConsistencyCheckRequest(ApiModel):
    required_fields: list[RequiredFieldAssertionRequest] = Field(default_factory=list)
    references: list[ReferenceAssertionRequest] = Field(default_factory=list)
    versions: list[VersionAssertionRequest] = Field(default_factory=list)
    canon_changes: list[CanonChangeAssertionRequest] = Field(default_factory=list)
    workflow_run_id: UUID | None = None


class FindingResponse(ApiModel):
    id: UUID
    check_run_id: UUID
    finding_type: FindingType
    severity: FindingSeverity
    evidence_references: list[str]
    message_code: str
    validator_key: str
    validator_version: str
    status: FindingStatus
    workflow_run_id: UUID | None
    detected_at: AwareDatetime


class ConsistencyCheckResponse(ApiModel):
    id: UUID
    project_id: UUID
    status: ValidationStatus
    workflow_run_id: UUID | None
    created_at: AwareDatetime
    findings: list[FindingResponse]


class ResolutionCreateRequest(ApiModel):
    finding_ids: list[UUID] = Field(min_length=1, max_length=100)
    strategy_code: Code
    target_reference: OpaqueReference
    target_expected_version: int = Field(ge=1)
    impact_references: list[OpaqueReference] = Field(default_factory=list, max_length=100)
    workflow_run_id: UUID | None = None


class ResolutionResponse(ApiModel):
    id: UUID
    project_id: UUID
    finding_ids: list[UUID]
    strategy_code: str
    requires_approval: bool
    status: ResolutionStatus
    requested_by: UUID
    workflow_run_id: UUID | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    approved_by: UUID | None
    applied_by: UUID | None
    version: int


class ResolutionDecisionRequest(ApiModel):
    decision: ResolutionDecision


class RubricCreateRequest(ApiModel):
    rubric_key: Code
    version: int = Field(ge=1)
    schema_version: Code
    dimension_keys: list[Code] = Field(min_length=1, max_length=100)


class RubricResponse(ApiModel):
    id: UUID
    project_id: UUID
    rubric_key: str
    version: int
    schema_version: str
    dimension_keys: list[str]
    created_by: UUID
    created_at: AwareDatetime


class EvaluationCreateRequest(ApiModel):
    rubric_id: UUID
    input_reference: OpaqueReference
    workflow_run_id: UUID | None = None


class EvaluationRunResponse(ApiModel):
    id: UUID
    project_id: UUID
    rubric_id: UUID
    input_reference: str
    workflow_run_id: UUID | None
    requested_by: UUID
    status: QualityStatus
    created_at: AwareDatetime
    completed_at: AwareDatetime | None


class EvaluationExecuteRequest(ApiModel):
    input_reference: OpaqueReference
    consistency_status: Code


class ScoreDimensionResponse(ApiModel):
    key: str
    status: DimensionStatus
    score: float | None


class QualityResultResponse(ApiModel):
    id: UUID
    evaluation_run_id: UUID
    status: QualityStatus
    evaluator_key: str
    evaluator_version: str
    dimensions: list[ScoreDimensionResponse]
    result_reference: str
    created_at: AwareDatetime


class FeedbackCreateRequest(ApiModel):
    source: FeedbackSource
    schema_version: Code
    signal_code: Code
    numeric_value: float | None = None
    source_reference: OpaqueReference | None = None
    consent_policy_version: Code | None = None
    creator_profile_id: UUID | None = None


class BehaviorConsentGrantRequest(ApiModel):
    policy_version: Code = "behavior-consent-v1"


class BehaviorConsentResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID
    policy_version: str
    status: ConsentStatus
    granted_at: AwareDatetime
    withdrawn_at: AwareDatetime | None


class BehaviorConsentStatusResponse(ApiModel):
    active: bool
    consent: BehaviorConsentResponse | None


class BehaviorConsentWithdrawalResponse(ApiModel):
    consent: BehaviorConsentResponse
    anonymized_event_ids: list[UUID]
    tombstone_count: int = Field(ge=0)


class FeedbackResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID | None
    source: FeedbackSource
    schema_version: str
    signal_code: str
    numeric_value: float | None
    source_reference: str | None
    status: FeedbackStatus
    occurred_at: AwareDatetime
    creator_signal_reference: str | None


class MetricRecordRequest(ApiModel):
    name: Code
    value: float
    dimensions: dict[Code, Code] = Field(default_factory=dict, max_length=20)
    source_reference: OpaqueReference
    source_feedback_event_id: UUID | None = None


class MetricDimensionRequest(ApiModel):
    key: Code
    allowed_values: list[Code] = Field(min_length=1, max_length=100)


class MetricDefinitionCreateRequest(ApiModel):
    name: Code
    version: int = Field(ge=1)
    unit: Code
    dimensions: list[MetricDimensionRequest] = Field(default_factory=list, max_length=20)
    retention_days: int = Field(ge=1, le=3650)
    sensitivity: MetricSensitivity


class MetricDefinitionResponse(ApiModel):
    id: UUID
    project_id: UUID
    name: str
    version: int
    unit: str
    retention_days: int
    created_by: UUID
    created_at: AwareDatetime


class MetricDefinitionCollectionResponse(ApiModel):
    items: list[MetricDefinitionResponse]


class MetricPointResponse(ApiModel):
    id: UUID
    project_id: UUID
    metric_name: str
    value: float
    dimensions: list[tuple[str, str]]
    observed_at: AwareDatetime
    source_reference: str
    source_feedback_event_id: UUID | None
    included: bool
    tombstoned_at: AwareDatetime | None


class VariantDraftRequest(ApiModel):
    variant_key: Code
    configuration_reference: OpaqueReference


class ExperimentCreateRequest(ApiModel):
    experiment_key: Code
    protocol_version: Code
    hypothesis_code: Code
    primary_metric_name: Code
    sample_scope: Literal["technical-smoke"] = "technical-smoke"
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    stop_condition_codes: list[Code] = Field(min_length=1, max_length=20)
    variants: list[VariantDraftRequest] = Field(min_length=2, max_length=20)


class VariantResponse(ApiModel):
    id: UUID
    experiment_id: UUID
    variant_key: str
    configuration_reference: str


class ExperimentResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    experiment_key: str
    protocol_version: str
    hypothesis_code: str
    primary_metric_name: str
    sample_scope: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    stop_condition_codes: list[str]
    status: ExperimentStatus
    created_by: UUID
    created_at: AwareDatetime
    result_code: str | None
    variants: list[VariantResponse]


class ExperimentSampleCreateRequest(ApiModel):
    variant_id: UUID
    metric_point_id: UUID


class ExperimentSampleResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    experiment_id: UUID
    variant_id: UUID
    metric_point_id: UUID
    source_feedback_event_id: UUID | None
    observed_at: AwareDatetime
    included: bool
    tombstoned_at: AwareDatetime | None


class ExperimentFinishRequest(ApiModel):
    status: Literal["completed", "stopped"]
    result_code: Code


class DiagnosticResponse(ApiModel):
    id: UUID
    project_id: UUID
    metric_point_id: UUID
    rule_key: str
    rule_version: str
    finding_code: str
    severity: DiagnosticSeverity
    observed_value: float
    threshold_value: float
    created_at: AwareDatetime


class DiagnosticCollectionResponse(ApiModel):
    items: list[DiagnosticResponse]


class ImprovementPlanRequest(ApiModel):
    action: ChangeAction
    change_reference: OpaqueReference
    rollback_reference: OpaqueReference


class ImprovementDecisionRequest(ApiModel):
    decision: EvolutionDecision


class ImprovementProposalResponse(ApiModel):
    id: UUID
    project_id: UUID
    diagnostic_finding_ids: list[UUID]
    input_references: list[str]
    algorithm_versions: list[str]
    state: EvolutionState
    requested_by: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    action: ChangeAction | None
    change_reference: str | None
    safety_policy_version: str | None
    safety_rule_code: str | None
    simulation_evidence: list[str]
    evaluation_code: str | None
    approved_by: UUID | None
    rollback_reference: str | None
    version: int


class SseEventData(ApiModel):
    event_id: UUID
    sequence: int = Field(ge=1)
    type: str
    schema_version: int = Field(ge=1)
    correlation_id: UUID
    run_id: UUID
    project_id: UUID
    occurred_at: AwareDatetime
    payload: dict[str, object]
