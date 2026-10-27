"""Framework-free asset, version, and upload-session contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class AssetStatus(StrEnum):
    """Recoverable asset lifecycle states."""

    ACTIVE = "active"
    PENDING_DELETION = "pending_deletion"


class AssetSort(StrEnum):
    """Stable asset collection ordering exposed at application boundaries."""

    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    FILENAME = "filename"
    FILENAME_DESC = "-filename"


class ProcessingStatus(StrEnum):
    """Whether a version can be reconciled with object storage."""

    AVAILABLE = "available"
    MISSING_OBJECT = "missing_object"


class ScanStatus(StrEnum):
    """Truthful malware-scanning result."""

    NOT_CONFIGURED = "not_configured"
    CLEAN = "clean"
    REJECTED = "rejected"
    FAILED = "failed"


class UploadStatus(StrEnum):
    """Durable checkpoints around the database/object-store boundary."""

    PENDING = "pending"
    OBJECT_STORED = "object_stored"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATION_REQUIRED = "compensation_required"


@dataclass(frozen=True, slots=True)
class Asset:
    """Project-owned logical file across one or more immutable versions."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    owner_id: UUID
    filename: str
    source: str
    status: AssetStatus
    current_version: int
    created_at: datetime
    updated_at: datetime
    deletion_marked_at: datetime | None = None
    retention_until: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class AssetVersion:
    """Immutable content-addressed object metadata."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    version_number: int
    object_key: str
    content_hash: str
    media_type: str
    size_bytes: int
    scan_status: ScanStatus
    processing_status: ProcessingStatus
    created_by: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UploadSession:
    """Durable compensation record for a single generated object key."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    version_number: int
    owner_id: UUID
    filename: str
    source: str
    object_key: str
    content_hash: str
    media_type: str
    size_bytes: int
    scan_status: ScanStatus
    status: UploadStatus
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Stable scanner decision without provider-specific details."""

    status: ScanStatus
    reason_code: str
