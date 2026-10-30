"""Storage, scanning, and persistence ports owned by assets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope
    from accos.kernel.persistence import Page
    from accos.modules.assets.domain import (
        Asset,
        AssetSort,
        AssetStatus,
        AssetVersion,
        ScanResult,
        UploadSession,
    )


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Provider-neutral object metadata used for integrity checks."""

    object_key: str
    content_hash: str
    media_type: str
    size_bytes: int


class ObjectStorage(Protocol):
    """Binary object boundary; keys must be service-generated."""

    async def put(
        self,
        object_key: str,
        data: bytes,
        *,
        media_type: str,
        content_hash: str,
    ) -> StoredObject:
        """Write exactly one verified object."""
        ...

    async def get(self, object_key: str) -> bytes:
        """Read one object or raise ObjectNotFoundError."""
        ...

    async def stat(self, object_key: str) -> StoredObject | None:
        """Return integrity metadata, or None when the object is absent."""
        ...

    async def delete_orphan(self, object_key: str) -> None:
        """Called only after assets atomically proves that no version references this key."""
        ...


class ContentScanner(Protocol):
    """Optional malware-scanning hook."""

    async def scan(self, data: bytes, *, media_type: str) -> ScanResult:
        """Return a truthful clean, rejected, failed, or unconfigured result."""
        ...


class AssetRepository(Protocol):
    """Strictly scoped asset and upload-session persistence boundary."""

    async def get_version(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID, version_id: UUID
    ) -> AssetVersion | None: ...

    async def versions(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID, before: int | None, limit: int
    ) -> tuple[AssetVersion, ...]: ...

    async def catalog(
        self, workspace_id: UUID, project_id: UUID, query: str, cursor: str | None, limit: int
    ) -> tuple[tuple[tuple[Asset, AssetVersion], ...], str | None]: ...

    async def find_version_by_hash(
        self, workspace_id: UUID, project_id: UUID, content_hash: str
    ) -> tuple[Asset, AssetVersion] | None:
        """Find an active duplicate inside exactly one project."""
        ...

    async def begin_upload(self, session: UploadSession) -> None:
        """Persist the compensation anchor before object I/O."""
        ...

    async def update_upload_status(
        self,
        workspace_id: UUID,
        upload_id: UUID,
        status: str,
        *,
        updated_at: datetime,
        error_code: str | None = None,
    ) -> UploadSession:
        """Move an upload checkpoint using a separate durable transaction."""
        ...

    async def finalize_upload(
        self,
        session: UploadSession,
        asset: Asset,
        version: AssetVersion,
        event: EventEnvelope,
    ) -> tuple[Asset, AssetVersion, UploadSession]:
        """Atomically write metadata, complete the session, and append Outbox."""
        ...

    async def get_upload(self, workspace_id: UUID, upload_id: UUID) -> UploadSession | None:
        """Load a compensation record only inside one workspace."""
        ...

    async def get(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID
    ) -> tuple[Asset, AssetVersion] | None:
        """Load an asset and current version through both scopes."""
        ...

    async def list_assets(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        status: AssetStatus | None,
        sort: AssetSort,
    ) -> Page[tuple[Asset, AssetVersion]]:
        """List current asset metadata through both owning scopes."""
        ...

    async def set_processing_status(
        self,
        workspace_id: UUID,
        version_id: UUID,
        status: str,
        *,
        updated_at: datetime,
    ) -> AssetVersion:
        """Persist a diagnostic object reconciliation state."""
        ...

    async def mark_for_deletion(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        *,
        expected_version: int,
        marked_at: datetime,
        retention_until: datetime,
        event: EventEnvelope,
    ) -> Asset:
        """Mark and retain; this port intentionally exposes no permanent delete."""
        ...
