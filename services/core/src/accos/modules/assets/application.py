"""Authorized, integrity-checked asset upload and compensation use cases."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, replace
from datetime import timedelta
from io import BytesIO
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from accos.kernel.errors import (
    ConcurrencyConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    InvalidStateError,
    ScopeViolationError,
)
from accos.kernel.events import EventEnvelope
from accos.kernel.shared_contracts import ContentRef
from accos.modules.assets.domain import (
    Asset,
    AssetSort,
    AssetStatus,
    AssetVersion,
    ProcessingStatus,
    ScanResult,
    ScanStatus,
    UploadSession,
    UploadStatus,
)
from accos.modules.identity.public import (
    AuthorizationRequest,
    Permission,
    ResourceScope,
    UploadDescriptor,
)
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from datetime import datetime
    from typing import NoReturn

    from accos.kernel.clock import Clock
    from accos.kernel.contracts import PageRequest
    from accos.kernel.persistence import Page
    from accos.kernel.security import SecurityContext
    from accos.modules.assets.ports import AssetRepository, ContentScanner, ObjectStorage
    from accos.modules.identity.public import AuthorizationService, UploadSecurityPolicy
    from accos.modules.projects.public import Project, ProjectRepository

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_SOURCE_LENGTH = 100
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MIME_BY_EXTENSION = {
    ".bin": frozenset({"application/octet-stream"}),
    ".json": frozenset({"application/json"}),
    ".md": frozenset({"text/markdown", "text/plain"}),
    ".txt": frozenset({"text/plain"}),
    ".pdf": frozenset({"application/pdf"}),
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
    ".jpg": frozenset({"image/jpeg"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".png": frozenset({"image/png"}),
}


class DefaultUploadSecurityPolicy:
    """Bounded filename, size, and MIME/extension policy."""

    def __init__(self, *, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
        if max_bytes < 1:
            raise ValueError("maximum upload size must be positive")
        self._max_bytes = max_bytes

    async def permits(self, context: SecurityContext, upload: UploadDescriptor) -> bool:
        """Reject user paths, ambiguous names, oversize data, and MIME mismatches."""
        del context
        filename = upload.filename
        if (
            not filename
            or filename.strip() != filename
            or len(filename) > MAX_FILENAME_LENGTH
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
            or filename in {".", ".."}
            or upload.size_bytes < 0
            or upload.size_bytes > self._max_bytes
        ):
            return False
        dot = filename.rfind(".")
        extension = filename[dot:].lower() if dot >= 0 else ""
        return upload.media_type in _MIME_BY_EXTENSION.get(extension, frozenset())


class UnconfiguredContentScanner:
    """Explicit scanner placeholder that never claims content was scanned."""

    async def scan(self, data: bytes, *, media_type: str) -> ScanResult:
        del data, media_type
        return ScanResult(ScanStatus.NOT_CONFIGURED, "scanner_not_configured")


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Upload result including whether content deduplication was used."""

    asset: Asset
    version: AssetVersion
    upload: UploadSession | None
    duplicate: bool


class AssetService:
    """Coordinate scoped project policy, storage, compensation, and metadata."""

    def __init__(  # noqa: PLR0913
        self,
        repository: AssetRepository,
        *,
        projects: ProjectRepository,
        storage: ObjectStorage,
        scanner: ContentScanner,
        upload_policy: UploadSecurityPolicy,
        authorizer: AuthorizationService,
        clock: Clock,
        legacy_bucket: str | None = None,
    ) -> None:
        self._repository = repository
        self._projects = projects
        self._storage = storage
        self._scanner = scanner
        self._upload_policy = upload_policy
        self._authorizer = authorizer
        self._clock = clock
        self._legacy_bucket = legacy_bucket

    async def upload(  # noqa: PLR0913
        self,
        context: SecurityContext,
        project_id: UUID,
        *,
        filename: str,
        media_type: str,
        data: bytes,
        expected_sha256: str,
        source: str = "user_upload",
        asset_id: UUID | None = None,
        expected_version: int | None = None,
    ) -> UploadResult:
        """Persist one verified object and its transactional metadata."""
        project = await self._require_project(context, project_id, Permission.PROJECT_WRITE)
        existing_asset: Asset | None = None
        version_number = 1
        selected_asset_id = uuid4() if asset_id is None else asset_id
        if asset_id is not None:
            existing = await self._repository.get(context.workspace_id, project_id, asset_id)
            if existing is None:
                await self._reject_unavailable(context, "asset", asset_id, project_id)
            existing_asset, _current = existing
            if expected_version is not None and existing_asset.version != expected_version:
                raise ConcurrencyConflictError(existing_asset.version)
            if existing_asset.status is not AssetStatus.ACTIVE:
                raise InvalidStateError("Only active assets can receive a new version.")
            if filename != existing_asset.filename:
                raise InvalidRequestError("An asset version must keep its logical filename.")
            version_number = existing_asset.current_version + 1
        descriptor = UploadDescriptor(media_type, len(data), filename)
        if not await self._upload_policy.permits(context, descriptor):
            raise InvalidRequestError("The upload filename, size, or media type is invalid.")
        digest = _validate_digest(data, expected_sha256)
        _validate_media(data, media_type)
        duplicate = await self._repository.find_version_by_hash(
            context.workspace_id, project_id, digest
        )
        if (
            duplicate is not None
            and duplicate[1].media_type == media_type
            and duplicate[0].filename == filename
            and duplicate[0].source == source
            and (
                asset_id is None
                or (
                    duplicate[0].id == asset_id
                    and existing_asset is not None
                    and duplicate[1].version_number == existing_asset.current_version
                )
            )
        ):
            asset, version = duplicate
            stored = await self._storage.stat(version.object_key)
            if (
                stored is None
                or stored.content_hash != digest
                or stored.size_bytes != len(data)
                or stored.media_type != media_type
            ):
                await self._repository.set_processing_status(
                    context.workspace_id,
                    version.id,
                    ProcessingStatus.MISSING_OBJECT.value,
                    updated_at=self._clock.now(),
                )
                raise InvalidStateError("Asset metadata exists but its object is missing.")
            return UploadResult(asset, version, None, duplicate=True)
        scan = await self._scanner.scan(data, media_type=media_type)
        if scan.status is ScanStatus.REJECTED:
            raise InvalidRequestError("The upload was rejected by content scanning.")
        if scan.status is ScanStatus.FAILED:
            raise DependencyUnavailableError("Content scanning is unavailable.")
        now = self._clock.now()
        version_id, upload_id = uuid4(), uuid4()
        object_key = object_key_for(context.workspace_id, project_id, selected_asset_id, version_id)
        upload = UploadSession(
            upload_id,
            context.workspace_id,
            project_id,
            selected_asset_id,
            version_id,
            version_number,
            context.actor_id,
            filename,
            _validated_source(source),
            object_key,
            digest,
            media_type,
            len(data),
            scan.status,
            UploadStatus.PENDING,
            now,
            now,
        )
        await self._repository.begin_upload(upload)
        try:
            await self._storage.put(
                object_key,
                data,
                media_type=media_type,
                content_hash=digest,
            )
            stored = await self._storage.stat(object_key)
            if (
                stored is None
                or stored.content_hash != digest
                or stored.size_bytes != len(data)
                or stored.media_type != media_type
            ):
                raise InvalidStateError("Stored object could not be confirmed.")
        except Exception as error:
            await self._repository.update_upload_status(
                context.workspace_id,
                upload.id,
                UploadStatus.FAILED.value,
                updated_at=self._clock.now(),
                error_code="object_write_failed",
            )
            raise DependencyUnavailableError("Object storage write failed.") from error
        try:
            checkpoint = await self._repository.update_upload_status(
                context.workspace_id,
                upload.id,
                UploadStatus.OBJECT_STORED.value,
                updated_at=self._clock.now(),
            )
            return await self._finalize(context, project, checkpoint)
        except Exception:
            await self._repository.update_upload_status(
                context.workspace_id,
                upload.id,
                UploadStatus.COMPENSATION_REQUIRED.value,
                updated_at=self._clock.now(),
                error_code="metadata_finalize_failed",
            )
            raise

    async def resume_upload(self, context: SecurityContext, upload_id: UUID) -> UploadResult:
        """Compensate an object-first partial failure without deleting the object."""
        session = await self._repository.get_upload(context.workspace_id, upload_id)
        if session is None:
            await self._reject_unavailable(context, "upload_session", upload_id)
        project = await self._require_project(context, session.project_id, Permission.PROJECT_WRITE)
        if session.status not in {
            UploadStatus.OBJECT_STORED,
            UploadStatus.COMPENSATION_REQUIRED,
        }:
            raise InvalidStateError("Only stored partial uploads can be resumed.")
        stored = await self._storage.stat(session.object_key)
        if (
            stored is None
            or stored.content_hash != session.content_hash
            or stored.size_bytes != session.size_bytes
            or stored.media_type != session.media_type
        ):
            await self._repository.update_upload_status(
                context.workspace_id,
                session.id,
                UploadStatus.FAILED.value,
                updated_at=self._clock.now(),
                error_code="stored_object_invalid",
            )
            raise InvalidStateError("Stored object cannot satisfy the upload session.")
        return await self._finalize(context, project, session)

    async def download(self, context: SecurityContext, project_id: UUID, asset_id: UUID) -> bytes:
        """Read and hash-check a current version without crossing project scope."""
        await self._require_project(context, project_id, Permission.PROJECT_READ)
        pair = await self._repository.get(context.workspace_id, project_id, asset_id)
        if pair is None:
            await self._reject_unavailable(context, "asset", asset_id, project_id)
        _asset, version = pair
        try:
            data = await self._storage.get(version.object_key)
        except Exception as error:
            await self._repository.set_processing_status(
                context.workspace_id,
                version.id,
                ProcessingStatus.MISSING_OBJECT.value,
                updated_at=self._clock.now(),
            )
            raise InvalidStateError("Asset metadata exists but its object is missing.") from error
        if hashlib.sha256(data).hexdigest() != version.content_hash:
            await self._repository.set_processing_status(
                context.workspace_id,
                version.id,
                ProcessingStatus.MISSING_OBJECT.value,
                updated_at=self._clock.now(),
            )
            raise InvalidStateError("Stored object failed its integrity check.")
        if version.processing_status is ProcessingStatus.MISSING_OBJECT:
            await self._repository.set_processing_status(
                context.workspace_id,
                version.id,
                ProcessingStatus.AVAILABLE.value,
                updated_at=self._clock.now(),
            )
        return data

    async def get(
        self, context: SecurityContext, project_id: UUID, asset_id: UUID
    ) -> tuple[Asset, AssetVersion]:
        """Read current metadata without exposing the storage adapter."""
        await self._require_project(context, project_id, Permission.PROJECT_READ)
        pair = await self._repository.get(context.workspace_id, project_id, asset_id)
        if pair is None:
            await self._reject_unavailable(context, "asset", asset_id, project_id)
        return pair

    async def put_snapshot(
        self, context: SecurityContext, project_id: UUID, data: bytes, *, media_type: str
    ) -> ContentRef:
        """Immutable content storage used by projects; the server owns the digest."""
        result = await self.upload(
            context,
            project_id,
            filename="document.json" if media_type == "application/json" else "projection.txt",
            media_type=media_type,
            data=data,
            expected_sha256=hashlib.sha256(data).hexdigest(),
            source="artifact_snapshot",
        )
        return ContentRef(
            asset_id=result.asset.id,
            asset_version_id=result.version.id,
            sha256=result.version.content_hash,
            media_type=result.version.media_type,
            byte_length=result.version.size_bytes,
        )

    async def version(
        self, context: SecurityContext, project_id: UUID, asset_id: UUID, version_id: UUID
    ) -> AssetVersion:
        await self._require_project(context, project_id, Permission.PROJECT_READ)
        value = await self._repository.get_version(
            context.workspace_id, project_id, asset_id, version_id
        )
        if value is None:
            await self._reject_unavailable(context, "asset_version", version_id, project_id)
        return value

    async def versions(
        self,
        context: SecurityContext,
        project_id: UUID,
        asset_id: UUID,
        before: int | None,
        limit: int,
    ) -> tuple[AssetVersion, ...]:
        await self.get(context, project_id, asset_id)
        return await self._repository.versions(
            context.workspace_id, project_id, asset_id, before, limit
        )

    async def catalog(
        self, context: SecurityContext, project_id: UUID, query: str, cursor: str | None, limit: int
    ) -> tuple[tuple[tuple[Asset, AssetVersion], ...], str | None]:
        await self._require_project(context, project_id, Permission.PROJECT_READ)
        return await self._repository.catalog(
            context.workspace_id, project_id, query, cursor, limit
        )

    async def read_snapshot(
        self, context: SecurityContext, project_id: UUID, ref: ContentRef
    ) -> bytes:
        version = await self.version(context, project_id, ref.asset_id, ref.asset_version_id)
        if (
            version.content_hash != ref.sha256
            or version.media_type != ref.media_type
            or version.size_bytes != ref.byte_length
        ):
            raise InvalidStateError("Content reference does not match the immutable asset version.")
        try:
            data = await self._storage.get(version.object_key)
        except FileNotFoundError as error:
            raise InvalidStateError("Referenced content is missing from object storage.") from error
        if len(data) != ref.byte_length or hashlib.sha256(data).hexdigest() != ref.sha256:
            raise InvalidStateError("Referenced content failed its integrity check.")
        return data

    async def read_legacy_snapshot(
        self, context: SecurityContext, project_id: UUID, ref: ContentRef, reference: str
    ) -> bytes:
        """Read a reviewed mapping to an existing scoped asset, never an arbitrary URL."""
        version = await self.version(context, project_id, ref.asset_id, ref.asset_version_id)
        location = urlsplit(reference)
        if (
            location.scheme != "s3"
            or location.netloc != self._legacy_bucket
            or location.path != "/" + version.object_key
            or location.query
            or location.fragment
        ):
            raise InvalidRequestError(
                "Legacy location does not match this installation's scoped asset."
            )
        return await self.read_snapshot(context, project_id, ref)

    async def list(
        self,
        context: SecurityContext,
        project_id: UUID,
        page: PageRequest,
        *,
        status: AssetStatus | None,
        sort: AssetSort,
    ) -> Page[tuple[Asset, AssetVersion]]:
        """List a bounded metadata page inside one authorized project."""
        await self._require_project(context, project_id, Permission.PROJECT_READ)
        return await self._repository.list_assets(
            context.workspace_id, project_id, page, status=status, sort=sort
        )

    async def mark_for_deletion(
        self,
        context: SecurityContext,
        project_id: UUID,
        asset_id: UUID,
        *,
        expected_version: int | None = None,
    ) -> Asset:
        """Mark an asset and set a retention deadline; never delete its object."""
        project = await self._require_project(context, project_id, Permission.DATA_DELETE_REQUEST)
        pair = await self._repository.get(context.workspace_id, project_id, asset_id)
        if pair is None:
            await self._reject_unavailable(context, "asset", asset_id, project_id)
        asset, _version = pair
        selected_version = asset.version if expected_version is None else expected_version
        if selected_version != asset.version:
            raise ConcurrencyConflictError(asset.version)
        if asset.status is AssetStatus.PENDING_DELETION:
            raise InvalidStateError("Asset is already marked for deletion.")
        now = self._clock.now()
        retention_until = now + timedelta(days=project.settings.asset_retention_days)
        return await self._repository.mark_for_deletion(
            context.workspace_id,
            project_id,
            asset_id,
            expected_version=selected_version,
            marked_at=now,
            retention_until=retention_until,
            event=_asset_event(
                context,
                project_id,
                asset_id,
                "assets.asset-deletion-marked",
                now,
                {
                    "schema": "asset-deletion-marked.v1",
                    "retention_until": retention_until.isoformat(),
                },
            ),
        )

    async def _finalize(
        self, context: SecurityContext, project: Project, session: UploadSession
    ) -> UploadResult:
        now = self._clock.now()
        if session.version_number == 1:
            asset = Asset(
                session.asset_id,
                session.workspace_id,
                session.project_id,
                session.owner_id,
                session.filename,
                session.source,
                AssetStatus.ACTIVE,
                1,
                session.created_at,
                now,
            )
        else:
            existing = await self._repository.get(
                session.workspace_id, session.project_id, session.asset_id
            )
            if existing is None:
                raise InvalidStateError("Versioned asset metadata is unavailable.")
            current, _version = existing
            if (
                current.status is not AssetStatus.ACTIVE
                or current.current_version + 1 != session.version_number
            ):
                raise InvalidStateError("Versioned asset state changed before finalization.")
            asset = replace(
                current,
                current_version=session.version_number,
                updated_at=now,
                version=current.version + 1,
            )
        version = AssetVersion(
            session.asset_version_id,
            session.workspace_id,
            session.project_id,
            session.asset_id,
            session.version_number,
            session.object_key,
            session.content_hash,
            session.media_type,
            session.size_bytes,
            session.scan_status,
            ProcessingStatus.AVAILABLE,
            session.owner_id,
            now,
        )
        stored_asset, stored_version, stored_upload = await self._repository.finalize_upload(
            session,
            asset,
            version,
            _asset_event(
                context,
                project.id,
                asset.id,
                "assets.asset-uploaded",
                now,
                {
                    "schema": "asset-uploaded.v1",
                    "version_number": session.version_number,
                    "scan_status": session.scan_status.value,
                },
            ),
        )
        return UploadResult(stored_asset, stored_version, stored_upload, duplicate=False)

    async def _require_project(
        self, context: SecurityContext, project_id: UUID, permission: Permission
    ) -> Project:
        project = await self._projects.get(context.workspace_id, project_id)
        if project is None:
            await self._reject_unavailable(context, "project", project_id, project_id)
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                permission,
                ResourceScope(project.workspace_id, "project", str(project.id), project.id),
            )
        )
        if permission is not Permission.PROJECT_READ and project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot be changed.")
        return project

    async def _reject_unavailable(
        self,
        context: SecurityContext,
        resource_type: str,
        identifier: UUID,
        project_id: UUID | None = None,
    ) -> NoReturn:
        await self._authorizer.reject(
            AuthorizationRequest(
                context,
                Permission.PROJECT_READ,
                ResourceScope(
                    context.workspace_id,
                    resource_type,
                    str(identifier),
                    project_id,
                ),
            ),
            ScopeViolationError(),
            reason_code=f"{resource_type}_unavailable",
        )


def object_key_for(workspace_id: UUID, project_id: UUID, asset_id: UUID, version_id: UUID) -> str:
    """Build an opaque, service-owned key containing no user filename."""
    return (
        f"workspaces/{workspace_id}/projects/{project_id}/assets/{asset_id}/versions/{version_id}"
    )


def _validate_digest(data: bytes, expected: str) -> str:
    if _SHA256_PATTERN.fullmatch(expected) is None:
        raise InvalidRequestError("Expected SHA-256 must be lowercase hexadecimal.")
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise InvalidRequestError("Uploaded content does not match its SHA-256.")
    return actual


def _validate_media(data: bytes, media_type: str) -> None:
    try:
        if media_type in {"text/plain", "text/markdown", "application/json"}:
            decoded = data.decode("utf-8")
            if "\x00" in decoded:
                raise ValueError
            if media_type == "application/json":
                json.loads(decoded)
        signatures = {
            "application/pdf": b"%PDF-",
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/jpeg": b"\xff\xd8\xff",
        }
        if media_type in signatures and not data.startswith(signatures[media_type]):
            raise ValueError
        if media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            with zipfile.ZipFile(BytesIO(data)) as bundle:
                entries = bundle.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > 50 * 1024 * 1024:
                    raise ValueError
                for entry in entries:
                    path = PurePosixPath(entry.filename)
                    if (
                        path.is_absolute()
                        or ".." in path.parts
                        or "\\" in entry.filename
                        or ":" in entry.filename
                        or entry.flag_bits & 1
                        or entry.file_size > max(1, entry.compress_size) * 1000
                    ):
                        raise ValueError
                if (
                    "word/document.xml" not in bundle.namelist()
                    or "[Content_Types].xml" not in bundle.namelist()
                ):
                    raise ValueError
    except (ValueError, UnicodeError, zipfile.BadZipFile):
        raise InvalidRequestError(
            "File bytes do not match the declared type or safe archive limits."
        ) from None


def _validated_source(source: str) -> str:
    if not source or source.strip() != source or len(source) > MAX_SOURCE_LENGTH:
        raise InvalidRequestError("Asset source must be non-empty, trimmed, and bounded.")
    return source


def _asset_event(  # noqa: PLR0913, PLR0917
    context: SecurityContext,
    project_id: UUID,
    aggregate_id: UUID,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, object],
) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        context.workspace_id,
        project_id,
        aggregate_id,
        event_type,
        1,
        {**payload, "correlation_id": context.correlation.request_id},
        occurred_at,
    )
