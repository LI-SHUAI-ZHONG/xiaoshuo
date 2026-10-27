"""Public API DTOs; no ORM or adapter types are allowed in this module."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID  # noqa: TC003 - Pydantic resolves public schema annotations.

from pydantic import AwareDatetime, Base64Bytes, BaseModel, ConfigDict, Field, model_validator

from accos.modules.assets.domain import (  # noqa: TC001 - Pydantic resolves enum schemas.
    AssetSort,
    AssetStatus,
)
from accos.modules.projects.domain import (  # noqa: TC001 - Pydantic resolves enum schemas.
    ArtifactSort,
    ArtifactType,
    ProjectSort,
    ProjectStatus,
)

Name = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^\S(?:.*\S)?$")]
BoundedReference = Annotated[str, Field(min_length=1, max_length=500)]


class ApiModel(BaseModel):
    """Reject transport fields that are not part of the published contract."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PageMetadata(ApiModel):
    """Opaque cursor pagination metadata."""

    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    next_cursor: str | None = None


class IdentityMeResponse(ApiModel):
    actor_id: UUID
    actor_kind: Literal["user", "service"]
    auth_method: str = "legacy"
    workspace_id: UUID
    permissions: list[str]
    policy_version: str


class WorkspaceResponse(ApiModel):
    id: UUID
    owner_user_id: UUID
    archived: bool


class WorkspaceCollectionResponse(ApiModel):
    items: list[WorkspaceResponse]
    page: PageMetadata


class MembershipResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: Literal["OWNER", "EDITOR", "VIEWER", "SERVICE"]
    active: bool


class MembershipCollectionResponse(ApiModel):
    items: list[MembershipResponse]
    page: PageMetadata


class ProjectSettingsDto(ApiModel):
    revision_retention_limit: int = Field(default=100, ge=1, le=10_000)
    asset_retention_days: int = Field(default=30, ge=1, le=3650)


class ProjectCreateRequest(ApiModel):
    name: Name
    settings: ProjectSettingsDto = Field(default_factory=ProjectSettingsDto)


class ProjectUpdateRequest(ApiModel):
    settings: ProjectSettingsDto


class ProjectResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    name: str
    status: ProjectStatus
    settings: ProjectSettingsDto
    created_by: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    archived_at: AwareDatetime | None
    version: int = Field(ge=1)


class ProjectCollectionResponse(ApiModel):
    items: list[ProjectResponse]
    page: PageMetadata
    sort: ProjectSort
    status_filter: ProjectStatus | None


class ArtifactCreateRequest(ApiModel):
    artifact_type: ArtifactType
    label: Name


class ArtifactResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    artifact_type: ArtifactType
    label: str
    created_by: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    current_revision: int = Field(ge=0)
    version: int = Field(ge=1)


class ArtifactCollectionResponse(ApiModel):
    items: list[ArtifactResponse]
    page: PageMetadata
    sort: ArtifactSort


class RevisionCreateRequest(ApiModel):
    content_reference: BoundedReference | None = None
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None

    @model_validator(mode="after")
    def references_are_paired(self) -> RevisionCreateRequest:
        if (self.content_reference is None) != (self.content_hash is None):
            raise ValueError("content_reference and content_hash must be provided together")
        return self


class RevisionResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    artifact_id: UUID
    revision_number: int = Field(ge=1)
    content_reference: str | None
    content_hash: str | None
    created_by: UUID
    created_at: AwareDatetime


class RevisionCollectionResponse(ApiModel):
    items: list[RevisionResponse]
    page: PageMetadata


class AssetUploadRequest(ApiModel):
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Annotated[str, Field(min_length=1, max_length=100)]
    content_base64: Base64Bytes
    expected_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source: Annotated[str, Field(min_length=1, max_length=100)] = "user_upload"


class AssetVersionResponse(ApiModel):
    id: UUID
    version_number: int = Field(ge=1)
    content_hash: str
    media_type: str
    size_bytes: int = Field(ge=0)
    scan_status: str
    processing_status: str
    created_by: UUID
    created_at: AwareDatetime


class AssetResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    owner_id: UUID
    filename: str
    source: str
    status: AssetStatus
    current_version: int = Field(ge=1)
    created_at: AwareDatetime
    updated_at: AwareDatetime
    deletion_marked_at: AwareDatetime | None
    retention_until: AwareDatetime | None
    version: int = Field(ge=1)
    current: AssetVersionResponse
    duplicate: bool | None = None


class AssetCollectionResponse(ApiModel):
    items: list[AssetResponse]
    page: PageMetadata
    sort: AssetSort
    status_filter: AssetStatus | None


class DependencyCheckResponse(ApiModel):
    name: str
    status: str
    critical: bool
    detail: str


class SystemHealthResponse(ApiModel):
    status: Literal["ready", "not_ready"]
    version: str
    timestamp: str
    checks: list[DependencyCheckResponse]


class RuntimeBoundaryStatusResponse(ApiModel):
    name: Literal["worker", "outbox"]
    status: Literal[
        "configured",
        "not_configured",
        "active",
        "not_started",
        "stale",
        "unavailable",
    ]
    detail: str
    observed_at: AwareDatetime | None = None
    backlog: int | None = Field(default=None, ge=0)
    oldest_age_seconds: float | None = Field(default=None, ge=0)


class FeatureFlagStatusResponse(ApiModel):
    name: str
    enabled: bool


class ExtensionConfigurationFieldResponse(ApiModel):
    name: str
    kind: Literal["string", "opaque_reference"]
    required: bool


class ExtensionCapabilityStatusResponse(ApiModel):
    capability: str
    state: Literal["DISABLED", "NOT_CONFIGURED", "AVAILABLE"]
    enabled: bool
    configured: bool
    detail: str
    feature_flag: str
    required_permissions: list[str]
    emitted_events: list[str]
    configuration_schema_version: str
    configuration_fields: list[ExtensionConfigurationFieldResponse]
    promotion_criteria: list[str]


class ExtensionStatusCollectionResponse(ApiModel):
    items: list[ExtensionCapabilityStatusResponse]


class SystemSettingsResponse(ApiModel):
    environment: str
    log_level: str
    object_storage_region: str
    object_storage_tls: bool
    ai_provider: str | None
    development_identity_enabled: bool
    feature_flags: list[FeatureFlagStatusResponse]
    runtime_boundaries: list[RuntimeBoundaryStatusResponse]


class SystemObservabilityResponse(ApiModel):
    metrics_enabled: bool
    otlp_configured: bool
    metric_names: list[str]
    runtime_boundaries: list[RuntimeBoundaryStatusResponse]


class AsyncOperationReference(ApiModel):
    """Stable 202 contract reserved for execution 17 task resources."""

    task_id: UUID
    status_url: str
    accepted_at: AwareDatetime
