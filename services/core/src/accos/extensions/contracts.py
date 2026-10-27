"""Framework-free contracts for deferred extension capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class ExtensionCapability(StrEnum):
    """Stable names exposed by the extension status API."""

    MULTIMODAL_IMAGE = "multimodal.image"
    MULTIMODAL_AUDIO = "multimodal.audio"
    MULTIMODAL_VIDEO = "multimodal.video"
    MULTIMODAL_THREE_D = "multimodal.three_d"
    GRAPH = "graph.relationship_projection"
    COLLABORATION = "collaboration.workspace"
    RIGHTS = "rights.metadata"
    MARKETPLACE = "ecosystem.marketplace"
    REPUTATION = "ecosystem.reputation"
    GROWTH = "ecosystem.growth"
    KNOWLEDGE_ACQUISITION = "knowledge_network.acquisition"
    KNOWLEDGE_RESEARCH_TEAM = "knowledge_network.research_team"
    KNOWLEDGE_VERIFICATION = "knowledge_network.verification"


class CapabilityState(StrEnum):
    """Non-aspirational runtime state for an optional capability."""

    DISABLED = "DISABLED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    AVAILABLE = "AVAILABLE"


class ConfigurationValueKind(StrEnum):
    """Credential-free configuration field types advertised to operators."""

    STRING = "string"
    OPAQUE_REFERENCE = "opaque_reference"


class PromotionCriterion(StrEnum):
    """Evidence required before a parked capability becomes a real module."""

    USER_DEMAND = "user_demand"
    DATA_OWNER = "data_owner"
    THREAT_MODEL = "threat_model"
    SLO = "slo"
    COST = "cost"
    MIGRATION = "migration"
    EXIT_PLAN = "exit_plan"


PROMOTION_CRITERIA = tuple(PromotionCriterion)


@dataclass(frozen=True, slots=True)
class ConfigurationField:
    """One field in a versioned, value-free extension configuration schema."""

    name: str
    kind: ConfigurationValueKind
    required: bool


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Permission, event, configuration, and promotion contract for one capability."""

    capability: ExtensionCapability
    feature_flag: str
    required_permissions: tuple[str, ...]
    emitted_events: tuple[str, ...]
    configuration_schema_version: str
    configuration_fields: tuple[ConfigurationField, ...]
    promotion_criteria: tuple[PromotionCriterion, ...] = PROMOTION_CRITERIA


@dataclass(frozen=True, slots=True)
class CapabilityStatus:
    """Runtime status that cannot be confused with completed business functionality."""

    manifest: CapabilityManifest
    state: CapabilityState
    enabled: bool
    configured: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """Content-free scoped request for deferred ecosystem capabilities."""

    workspace_id: UUID
    project_id: UUID
    input_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """Stable closed/not-configured result with no invented output or usage."""

    state: CapabilityState
    output_references: tuple[str, ...] = ()
    usage_reference: str | None = None


class DeferredCapabilityPort(Protocol):
    """Generic port for parked capabilities that do not yet own business state."""

    @property
    def configured(self) -> bool: ...

    async def invoke(self, request: CapabilityRequest) -> CapabilityResult: ...


class MediaKind(StrEnum):
    """Deferred multimodal asset families."""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    THREE_D = "three_d"


class MultimodalJobState(StrEnum):
    """Portable job states for a future provider adapter."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AssetReference:
    """Versioned asset reference; bytes remain owned by the core asset module."""

    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    owner_id: UUID
    media_type: str


@dataclass(frozen=True, slots=True)
class SafetyMetadata:
    """Provider-neutral safety decision metadata."""

    policy_version: str
    scan_status: str
    classification_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProvenanceMetadata:
    """Traceable origin without embedding source content."""

    provider_id: str
    provider_job_reference: str
    source_asset_ids: tuple[UUID, ...]
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class UsageMetadata:
    """Provider-neutral metering facts; absent for disabled and Null adapters."""

    input_units: int
    output_units: int
    compute_milliseconds: int
    billable_units: int


@dataclass(frozen=True, slots=True)
class MultimodalJob:
    """Future asynchronous job contract carrying only references and metadata."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    capability: ExtensionCapability
    state: MultimodalJobState
    input_assets: tuple[AssetReference, ...]
    output_assets: tuple[AssetReference, ...]
    provenance: ProvenanceMetadata | None
    usage: UsageMetadata | None
    safety: SafetyMetadata | None


@dataclass(frozen=True, slots=True)
class MultimodalRequest:
    """Reference-only multimodal request."""

    workspace_id: UUID
    project_id: UUID
    capability: ExtensionCapability
    input_assets: tuple[AssetReference, ...]
    output_media_type: str


@dataclass(frozen=True, slots=True)
class MultimodalResult:
    """Submission result; Null adapters never fabricate a job."""

    state: CapabilityState
    job: MultimodalJob | None = None


class MultimodalPort(Protocol):
    """Provider-neutral image, audio, video, and 3D job boundary."""

    @property
    def configured(self) -> bool: ...

    async def submit(self, request: MultimodalRequest) -> MultimodalResult: ...


class TeamRole(StrEnum):
    """Deferred collaboration roles; they do not replace core workspace RBAC."""

    COORDINATOR = "coordinator"
    CONTRIBUTOR = "contributor"
    OBSERVER = "observer"


@dataclass(frozen=True, slots=True)
class TeamReference:
    workspace_id: UUID
    team_id: UUID
    member_actor_ids: tuple[UUID, ...]
    roles: tuple[TeamRole, ...]


@dataclass(frozen=True, slots=True)
class CollaborationTaskReference:
    workspace_id: UUID
    project_id: UUID
    task_id: UUID
    assignee_actor_id: UUID | None


@dataclass(frozen=True, slots=True)
class CommentReference:
    workspace_id: UUID
    project_id: UUID
    comment_id: UUID
    target_reference: str


@dataclass(frozen=True, slots=True)
class PresenceReference:
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID
    document_reference: str


@dataclass(frozen=True, slots=True)
class CollaborationRequest:
    """Reference-only team/task/comment/presence/editor capability request."""

    workspace_id: UUID
    project_id: UUID
    team: TeamReference | None = None
    task: CollaborationTaskReference | None = None
    comment: CommentReference | None = None
    presence: PresenceReference | None = None
    collaborative_editor_requested: bool = False


class CollaborationPort(Protocol):
    @property
    def configured(self) -> bool: ...

    async def invoke(self, request: CollaborationRequest) -> CapabilityResult: ...


@dataclass(frozen=True, slots=True)
class OwnedAssetReference:
    """Core-owned identity that an extension is forbidden to rewrite."""

    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class RightsMetadata:
    """Descriptive metadata only; it is not a legal copyright determination."""

    workspace_id: UUID
    asset_id: UUID
    owner_id: UUID
    contributor_ids: tuple[UUID, ...]
    license_code: str | None
    permission_codes: tuple[str, ...]
    provenance_references: tuple[str, ...]
    audit_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RightsRequest:
    asset: OwnedAssetReference
    proposed_metadata: RightsMetadata


@dataclass(frozen=True, slots=True)
class RightsResult:
    state: CapabilityState
    metadata: RightsMetadata | None = None


class RightsPort(Protocol):
    @property
    def configured(self) -> bool: ...

    async def evaluate(self, request: RightsRequest) -> RightsResult: ...


class AcquisitionProvider(DeferredCapabilityPort, Protocol):
    """External acquisition boundary; no network access exists in the Null adapter."""


class ResearchTeamProvider(DeferredCapabilityPort, Protocol):
    """External research-team boundary."""


class ExternalVerificationProvider(DeferredCapabilityPort, Protocol):
    """External verification boundary distinct from the core deterministic checks."""
