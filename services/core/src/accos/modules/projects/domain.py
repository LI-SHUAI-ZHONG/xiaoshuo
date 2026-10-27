"""Framework-free project and artifact domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

MAX_REVISION_RETENTION = 10_000
MAX_ASSET_RETENTION_DAYS = 3650


class ProjectStatus(StrEnum):
    """Recoverable project lifecycle states."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectSort(StrEnum):
    """Stable project collection ordering exposed at application boundaries."""

    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    NAME = "name"
    NAME_DESC = "-name"


class ArtifactSort(StrEnum):
    """Stable artifact collection ordering exposed at application boundaries."""

    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    LABEL = "label"
    LABEL_DESC = "-label"


class ArtifactType(StrEnum):
    """Reserved versioned creation-container kinds."""

    CHAPTER = "chapter"
    WORLD = "world"
    CHARACTER = "character"
    TIMELINE = "timeline"
    DOCUMENT = "document"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    """Small persistence policy set; it contains no creative preferences."""

    revision_retention_limit: int = 100
    asset_retention_days: int = 30

    def __post_init__(self) -> None:
        if not 1 <= self.revision_retention_limit <= MAX_REVISION_RETENTION:
            raise ValueError("revision retention limit must be between 1 and 10000")
        if not 1 <= self.asset_retention_days <= MAX_ASSET_RETENTION_DAYS:
            raise ValueError("asset retention days must be between 1 and 3650")


@dataclass(frozen=True, slots=True)
class Project:
    """Workspace-owned empty project aggregate."""

    id: UUID
    workspace_id: UUID
    name: str
    status: ProjectStatus
    settings: ProjectSettings
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    version: int = 1
    archived_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    """Versioned creative container without embedded domain content."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    artifact_type: ArtifactType
    label: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    current_revision: int = 0
    version: int = 1


@dataclass(frozen=True, slots=True)
class ArtifactRevision:
    """Immutable reference to one artifact version."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    artifact_id: UUID
    revision_number: int
    content_reference: str | None
    content_hash: str | None
    created_by: UUID
    created_at: datetime
