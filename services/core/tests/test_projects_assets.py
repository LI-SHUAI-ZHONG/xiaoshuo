from __future__ import annotations

import asyncio
import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from minio.error import S3Error

from accos.adapters.assets import InMemoryObjectStorage, MinioObjectStorage
from accos.adapters.assets.storage import validate_object_key
from accos.kernel.errors import (
    ConcurrencyConflictError,
    DependencyUnavailableError,
    IdempotencyConflictError,
    InvalidRequestError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.persistence import Page
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.assets.public import (
    Asset,
    AssetService,
    AssetSort,
    AssetStatus,
    AssetVersion,
    DefaultUploadSecurityPolicy,
    ProcessingStatus,
    ScanResult,
    ScanStatus,
    StoredObject,
    UnconfiguredContentScanner,
    UploadSession,
    UploadStatus,
    object_key_for,
)
from accos.modules.identity.public import (
    POLICY_VERSION,
    AuditEvent,
    AuthorizationService,
    Role,
    UploadDescriptor,
    permissions_for,
)
from accos.modules.projects.public import (
    Artifact,
    ArtifactRevision,
    ArtifactSort,
    ArtifactType,
    Project,
    ProjectService,
    ProjectSettings,
    ProjectSort,
    ProjectStatus,
)

if TYPE_CHECKING:
    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope

NOW = datetime(2026, 9, 3, 10, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


def context(role: Role, *, workspace_id: UUID | None = None) -> SecurityContext:
    return SecurityContext(
        uuid4(),
        ActorKind.USER,
        workspace_id or uuid4(),
        permissions_for(role),
        POLICY_VERSION,
        CorrelationIds(str(uuid4()), str(uuid4())),
    )


class MemoryProjects:
    def __init__(self) -> None:
        self.projects: dict[tuple[UUID, UUID], Project] = {}
        self.keys: dict[tuple[UUID, str], tuple[str, UUID]] = {}
        self.artifacts: dict[tuple[UUID, UUID, UUID], Artifact] = {}
        self.revisions: list[ArtifactRevision] = []
        self.events: list[EventEnvelope] = []

    async def create_idempotent(
        self,
        project: Project,
        *,
        idempotency_key: str,
        request_digest: str,
        event: EventEnvelope,
    ) -> tuple[Project, bool]:
        key = (project.workspace_id, idempotency_key)
        existing = self.keys.get(key)
        if existing is not None:
            if existing[0] != request_digest:
                raise IdempotencyConflictError
            return self.projects[(project.workspace_id, existing[1])], False
        self.keys[key] = (request_digest, project.id)
        self.projects[(project.workspace_id, project.id)] = project
        self.events.append(event)
        return project, True

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        return self.projects.get((workspace_id, project_id))

    async def list_projects(
        self,
        workspace_id: UUID,
        page: PageRequest,
        *,
        status: ProjectStatus | None,
        sort: ProjectSort,
        hidden_ids: frozenset[UUID] = frozenset(),
    ) -> Page[Project]:
        values = [
            project
            for (workspace, _identifier), project in self.projects.items()
            if workspace == workspace_id and project.id not in hidden_ids and (status is None or project.status is status)
        ]
        reverse = sort in {ProjectSort.CREATED_AT_DESC, ProjectSort.NAME_DESC}
        key = (
            (lambda project: (project.name, project.id))
            if sort in {ProjectSort.NAME, ProjectSort.NAME_DESC}
            else (lambda project: (project.created_at, project.id))
        )
        values.sort(key=key, reverse=reverse)
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def update_settings(
        self,
        workspace_id: UUID,
        project_id: UUID,
        settings: ProjectSettings,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        project = self.projects[(workspace_id, project_id)]
        if project.version != expected_version:
            raise ConcurrencyConflictError
        stored = replace(project, settings=settings, version=project.version + 1)
        self.projects[(workspace_id, project_id)] = stored
        self.events.append(event)
        return stored

    async def archive(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        project = self.projects[(workspace_id, project_id)]
        if project.version != expected_version:
            raise ConcurrencyConflictError
        stored = replace(
            project,
            status=ProjectStatus.ARCHIVED,
            version=project.version + 1,
            archived_at=event.occurred_at,
        )
        self.projects[(workspace_id, project_id)] = stored
        self.events.append(event)
        return stored

    async def add_artifact(self, artifact: Artifact, event: EventEnvelope) -> None:
        self.artifacts[(artifact.workspace_id, artifact.project_id, artifact.id)] = artifact
        self.events.append(event)

    async def get_artifact(
        self, workspace_id: UUID, project_id: UUID, artifact_id: UUID
    ) -> Artifact | None:
        return self.artifacts.get((workspace_id, project_id, artifact_id))

    async def list_artifacts(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        sort: ArtifactSort,
    ) -> Page[Artifact]:
        values = [
            artifact
            for (workspace, project, _identifier), artifact in self.artifacts.items()
            if workspace == workspace_id and project == project_id
        ]
        reverse = sort in {ArtifactSort.CREATED_AT_DESC, ArtifactSort.LABEL_DESC}
        key = (
            (lambda artifact: (artifact.label, artifact.id))
            if sort in {ArtifactSort.LABEL, ArtifactSort.LABEL_DESC}
            else (lambda artifact: (artifact.created_at, artifact.id))
        )
        values.sort(key=key, reverse=reverse)
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def list_revisions(
        self,
        workspace_id: UUID,
        project_id: UUID,
        artifact_id: UUID,
        page: PageRequest,
    ) -> Page[ArtifactRevision]:
        values = sorted(
            (
                revision
                for revision in self.revisions
                if revision.workspace_id == workspace_id
                and revision.project_id == project_id
                and revision.artifact_id == artifact_id
            ),
            key=lambda revision: (revision.revision_number, revision.id),
            reverse=True,
        )
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def add_revision(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> tuple[Artifact, ArtifactRevision]:
        key = (artifact.workspace_id, artifact.project_id, artifact.id)
        current = self.artifacts[key]
        if current.version != expected_version:
            raise ConcurrencyConflictError
        self.artifacts[key] = artifact
        self.revisions.append(revision)
        self.events.append(event)
        return artifact, revision


class MemoryAssets:
    def __init__(self) -> None:
        self.assets: dict[tuple[UUID, UUID, UUID], tuple[Asset, AssetVersion]] = {}
        self.uploads: dict[tuple[UUID, UUID], UploadSession] = {}
        self.events: list[EventEnvelope] = []
        self.fail_finalize_once = False

    async def find_version_by_hash(
        self, workspace_id: UUID, project_id: UUID, content_hash: str
    ) -> tuple[Asset, AssetVersion] | None:
        return next(
            (
                pair
                for (workspace, project, _identifier), pair in self.assets.items()
                if workspace == workspace_id
                and project == project_id
                and pair[1].content_hash == content_hash
                and pair[0].status is AssetStatus.ACTIVE
            ),
            None,
        )

    async def begin_upload(self, session: UploadSession) -> None:
        self.uploads[(session.workspace_id, session.id)] = session

    async def update_upload_status(
        self,
        workspace_id: UUID,
        upload_id: UUID,
        status: str,
        *,
        updated_at: datetime,
        error_code: str | None = None,
    ) -> UploadSession:
        key = (workspace_id, upload_id)
        if key not in self.uploads:
            raise InvalidStateError("Upload session is unavailable.")
        stored = replace(
            self.uploads[key],
            status=UploadStatus(status),
            updated_at=updated_at,
            error_code=error_code,
        )
        self.uploads[key] = stored
        return stored

    async def finalize_upload(
        self,
        session: UploadSession,
        asset: Asset,
        version: AssetVersion,
        event: EventEnvelope,
    ) -> tuple[Asset, AssetVersion, UploadSession]:
        if self.fail_finalize_once:
            self.fail_finalize_once = False
            raise RuntimeError("fixture metadata failure")
        key = (session.workspace_id, session.id)
        completed = replace(session, status=UploadStatus.COMPLETED, error_code=None)
        self.uploads[key] = completed
        self.assets[(asset.workspace_id, asset.project_id, asset.id)] = (asset, version)
        self.events.append(event)
        return asset, version, completed

    async def get_upload(self, workspace_id: UUID, upload_id: UUID) -> UploadSession | None:
        return self.uploads.get((workspace_id, upload_id))

    async def get(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID
    ) -> tuple[Asset, AssetVersion] | None:
        return self.assets.get((workspace_id, project_id, asset_id))

    async def list_assets(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        status: AssetStatus | None,
        sort: AssetSort,
    ) -> Page[tuple[Asset, AssetVersion]]:
        values = [
            pair
            for (workspace, project, _identifier), pair in self.assets.items()
            if workspace == workspace_id
            and project == project_id
            and (status is None or pair[0].status is status)
        ]
        reverse = sort in {AssetSort.CREATED_AT_DESC, AssetSort.FILENAME_DESC}
        key = (
            (lambda pair: (pair[0].filename, pair[0].id))
            if sort in {AssetSort.FILENAME, AssetSort.FILENAME_DESC}
            else (lambda pair: (pair[0].created_at, pair[0].id))
        )
        values.sort(key=key, reverse=reverse)
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def set_processing_status(
        self,
        workspace_id: UUID,
        version_id: UUID,
        status: str,
        *,
        updated_at: datetime,
    ) -> AssetVersion:
        for key, (asset, version) in self.assets.items():
            if key[0] == workspace_id and version.id == version_id:
                changed = replace(version, processing_status=ProcessingStatus(status))
                self.assets[key] = (replace(asset, updated_at=updated_at), changed)
                return changed
        raise InvalidStateError("Asset version is unavailable.")

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
        key = (workspace_id, project_id, asset_id)
        asset, version = self.assets[key]
        if asset.version != expected_version:
            raise ConcurrencyConflictError(asset.version)
        changed = replace(
            asset,
            status=AssetStatus.PENDING_DELETION,
            deletion_marked_at=marked_at,
            retention_until=retention_until,
            version=asset.version + 1,
        )
        self.assets[key] = (changed, version)
        self.events.append(event)
        return changed


class StaticScanner:
    def __init__(self, status: ScanStatus) -> None:
        self.status = status

    async def scan(self, data: bytes, *, media_type: str) -> ScanResult:
        del data, media_type
        return ScanResult(self.status, f"fixture-{self.status.value}")


class FailingStorage(InMemoryObjectStorage):
    async def put(
        self,
        object_key: str,
        data: bytes,
        *,
        media_type: str,
        content_hash: str,
    ) -> StoredObject:
        del object_key, data, media_type, content_hash
        raise RuntimeError("fixture object failure")


def services(
    *,
    role: Role = Role.OWNER,
    scanner: StaticScanner | UnconfiguredContentScanner | None = None,
    storage: InMemoryObjectStorage | None = None,
) -> tuple[
    SecurityContext,
    MemoryProjects,
    MemoryAssets,
    InMemoryObjectStorage,
    ProjectService,
    AssetService,
    MemoryAudit,
]:
    selected_context = context(role)
    projects = MemoryProjects()
    assets = MemoryAssets()
    objects = storage or InMemoryObjectStorage()
    audit = MemoryAudit()
    authorizer = AuthorizationService(audit, FixedClock())
    project_service = ProjectService(projects, authorizer, FixedClock())
    asset_service = AssetService(
        assets,
        projects=projects,
        storage=objects,
        scanner=scanner or UnconfiguredContentScanner(),
        upload_policy=DefaultUploadSecurityPolicy(max_bytes=32),
        authorizer=authorizer,
        clock=FixedClock(),
    )
    return (
        selected_context,
        projects,
        assets,
        objects,
        project_service,
        asset_service,
        audit,
    )


def test_project_use_cases_are_idempotent_versioned_scoped_and_archived() -> None:  # noqa: PLR0915
    async def scenario() -> None:
        owner, repo, _assets, _storage, projects, _service, audit = services()
        settings = ProjectSettings(4, 2)
        project = await projects.create(
            owner, name="fixture-project", settings=settings, idempotency_key="fixture-key"
        )
        replay = await projects.create(
            owner, name="fixture-project", settings=settings, idempotency_key="fixture-key"
        )
        assert replay.id == project.id
        assert [event.event_type for event in repo.events] == ["projects.project-created"]
        with pytest.raises(IdempotencyConflictError):
            await projects.create(
                owner,
                name="fixture-other",
                settings=settings,
                idempotency_key="fixture-key",
            )
        assert await projects.get(owner, project.id) == project
        outsider = context(Role.OWNER)
        with pytest.raises(ScopeViolationError):
            await projects.get(outsider, project.id)
        with pytest.raises(ScopeViolationError):
            await projects.archive(owner, uuid4(), expected_version=1)
        with pytest.raises(ScopeViolationError):
            await projects.create_artifact(
                owner, uuid4(), artifact_type=ArtifactType.OTHER, label="fixture"
            )
        viewer = context(Role.VIEWER, workspace_id=owner.workspace_id)
        with pytest.raises(PermissionDeniedError):
            await projects.create(
                viewer,
                name="fixture-denied",
                settings=settings,
                idempotency_key="fixture-denied",
            )
        with pytest.raises(ConcurrencyConflictError):
            await projects.update_settings(owner, project.id, settings, expected_version=2)
        updated = await projects.update_settings(
            owner, project.id, ProjectSettings(5, 3), expected_version=1
        )
        assert updated.version == 2
        with pytest.raises(ValueError, match="artifact label"):
            await projects.create_artifact(
                owner, project.id, artifact_type=ArtifactType.OTHER, label=" "
            )
        artifact = await projects.create_artifact(
            owner, project.id, artifact_type=ArtifactType.DOCUMENT, label="fixture-document"
        )
        with pytest.raises(ScopeViolationError):
            await projects.get_artifact(owner, project.id, uuid4())
        with pytest.raises(ValueError, match="provided together"):
            await projects.add_artifact_revision(
                owner,
                project.id,
                artifact.id,
                content_reference="fixture-reference",
                expected_version=1,
            )
        revision = await projects.add_artifact_revision(
            owner, project.id, artifact.id, expected_version=1
        )
        assert revision.revision_number == 1
        assert repo.events[-1].payload["schema"] == "artifact-revision-created.v1"
        with pytest.raises(ConcurrencyConflictError):
            await projects.add_artifact_revision(owner, project.id, artifact.id, expected_version=1)
        with pytest.raises(ScopeViolationError):
            await projects.add_artifact_revision(owner, project.id, uuid4(), expected_version=1)
        with pytest.raises(ConcurrencyConflictError):
            await projects.archive(owner, project.id, expected_version=1)
        archived = await projects.archive(owner, project.id, expected_version=2)
        assert archived.status is ProjectStatus.ARCHIVED
        with pytest.raises(InvalidStateError, match="Archived"):
            await projects.archive(owner, project.id, expected_version=3)
        with pytest.raises(InvalidStateError, match="Archived"):
            await projects.update_settings(owner, project.id, settings, expected_version=3)
        with pytest.raises(InvalidStateError, match="Archived"):
            await projects.create_artifact(
                owner, project.id, artifact_type=ArtifactType.OTHER, label="fixture"
            )
        assert audit.events[-1].result == "allowed"

    asyncio.run(scenario())

    with pytest.raises(ValueError, match="revision retention"):
        ProjectSettings(0, 30)
    with pytest.raises(ValueError, match="asset retention"):
        ProjectSettings(1, 0)
    assert {kind.value for kind in ArtifactType} == {
        "chapter",
        "world",
        "character",
        "timeline",
        "document",
        "other",
    }


@pytest.mark.parametrize(
    ("descriptor", "allowed"),
    [
        (UploadDescriptor("text/plain", 1, "fixture.txt"), True),
        (UploadDescriptor("text/plain", 1, ""), False),
        (UploadDescriptor("text/plain", 1, " fixture.txt"), False),
        (UploadDescriptor("text/plain", 1, f"{'x' * 252}.txt"), False),
        (UploadDescriptor("text/plain", 1, "path/fixture.txt"), False),
        (UploadDescriptor("text/plain", 1, "path\\fixture.txt"), False),
        (UploadDescriptor("text/plain", 1, "fixture\x00.txt"), False),
        (UploadDescriptor("text/plain", 1, "."), False),
        (UploadDescriptor("text/plain", 1, ".."), False),
        (UploadDescriptor("text/plain", 0, "fixture.txt"), False),
        (UploadDescriptor("text/plain", 33, "fixture.txt"), False),
        (UploadDescriptor("text/plain", 1, "fixture"), False),
        (UploadDescriptor("image/png", 1, "fixture.txt"), False),
        (UploadDescriptor("text/markdown", 1, "fixture.MD"), True),
    ],
)
def test_upload_policy_rejects_unsafe_filename_size_and_mime_combinations(
    descriptor: UploadDescriptor, *, allowed: bool
) -> None:
    selected = DefaultUploadSecurityPolicy(max_bytes=32)
    assert asyncio.run(selected.permits(context(Role.OWNER), descriptor)) is allowed


def test_upload_policy_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="positive"):
        DefaultUploadSecurityPolicy(max_bytes=0)


def test_asset_upload_download_dedup_missing_recovery_and_retention() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        owner, _repo, assets, storage, projects, service, audit = services()
        project = await projects.create(
            owner,
            name="fixture-project",
            settings=ProjectSettings(asset_retention_days=2),
            idempotency_key="fixture-project",
        )
        data = b"fixture-document"
        digest = hashlib.sha256(data).hexdigest()
        uploaded = await service.upload(
            owner,
            project.id,
            filename="fixture.txt",
            media_type="text/plain",
            data=data,
            expected_sha256=digest,
        )
        assert uploaded.version.scan_status is ScanStatus.NOT_CONFIGURED
        assert "fixture.txt" not in uploaded.version.object_key
        assert uploaded.upload is not None
        assert uploaded.upload.status is UploadStatus.COMPLETED
        assert await service.download(owner, project.id, uploaded.asset.id) == data
        duplicate = await service.upload(
            owner,
            project.id,
            filename="fixture.txt",
            media_type="text/plain",
            data=data,
            expected_sha256=digest,
        )
        assert duplicate.duplicate and duplicate.upload is None

        with pytest.raises(InvalidRequestError, match="logical filename"):
            await service.upload(
                owner,
                project.id,
                filename="other.txt",
                media_type="text/plain",
                data=b"fixture-revision",
                expected_sha256=hashlib.sha256(b"fixture-revision").hexdigest(),
                asset_id=uploaded.asset.id,
            )
        revision_data = b"fixture-revision"
        revision_digest = hashlib.sha256(revision_data).hexdigest()
        uploaded = await service.upload(
            owner,
            project.id,
            filename="fixture.txt",
            media_type="text/plain",
            data=revision_data,
            expected_sha256=revision_digest,
            asset_id=uploaded.asset.id,
        )
        assert uploaded.asset.current_version == uploaded.version.version_number == 2
        assert await service.download(owner, project.id, uploaded.asset.id) == revision_data
        data, digest = revision_data, revision_digest

        storage.simulate_missing(uploaded.version.object_key)
        with pytest.raises(InvalidStateError, match="object is missing"):
            await service.upload(
                owner,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=digest,
            )
        stored_pair = await assets.get(owner.workspace_id, project.id, uploaded.asset.id)
        assert stored_pair is not None
        assert stored_pair[1].processing_status is ProcessingStatus.MISSING_OBJECT
        await storage.put(
            uploaded.version.object_key,
            data,
            media_type="text/plain",
            content_hash=digest,
        )
        assert await service.download(owner, project.id, uploaded.asset.id) == data
        restored_pair = await assets.get(owner.workspace_id, project.id, uploaded.asset.id)
        assert restored_pair is not None
        assert restored_pair[1].processing_status is ProcessingStatus.AVAILABLE

        storage.simulate_corruption(uploaded.version.object_key, b"broken")
        with pytest.raises(InvalidStateError, match="integrity"):
            await service.download(owner, project.id, uploaded.asset.id)
        storage.simulate_missing(uploaded.version.object_key)
        with pytest.raises(InvalidStateError, match="object is missing"):
            await service.download(owner, project.id, uploaded.asset.id)

        marked = await service.mark_for_deletion(owner, project.id, uploaded.asset.id)
        assert marked.status is AssetStatus.PENDING_DELETION
        assert marked.retention_until == NOW.replace(day=5)
        with pytest.raises(InvalidStateError, match="already marked"):
            await service.mark_for_deletion(owner, project.id, uploaded.asset.id)
        outsider = context(Role.OWNER)
        with pytest.raises(ScopeViolationError):
            await service.download(outsider, project.id, uploaded.asset.id)
        with pytest.raises(ScopeViolationError):
            await service.download(owner, project.id, uuid4())
        with pytest.raises(ScopeViolationError):
            await service.mark_for_deletion(owner, project.id, uuid4())
        with pytest.raises(InvalidStateError, match="active assets"):
            await service.upload(
                owner,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=b"fixture-third",
                expected_sha256=hashlib.sha256(b"fixture-third").hexdigest(),
                asset_id=uploaded.asset.id,
            )
        with pytest.raises(ScopeViolationError):
            await service.upload(
                owner,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=b"fixture-unknown",
                expected_sha256=hashlib.sha256(b"fixture-unknown").hexdigest(),
                asset_id=uuid4(),
            )
        assert [event.event_type for event in assets.events] == [
            "assets.asset-uploaded",
            "assets.asset-uploaded",
            "assets.asset-deletion-marked",
        ]
        assert any(event.result == "denied" for event in audit.events)

    asyncio.run(scenario())


def test_asset_validation_scanning_and_partial_failure_states() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        owner, repo, assets, storage, projects, service, _audit = services()
        project = await projects.create(
            owner,
            name="fixture-project",
            settings=ProjectSettings(),
            idempotency_key="fixture-project",
        )
        data = b"fixture"
        digest = hashlib.sha256(data).hexdigest()

        async def upload_fixture(
            target: AssetService, expected_sha256: str, *, source: str = "user_upload"
        ) -> object:
            return await target.upload(
                owner,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=expected_sha256,
                source=source,
            )

        with pytest.raises(InvalidRequestError, match="lowercase"):
            await upload_fixture(service, "BAD")
        with pytest.raises(InvalidRequestError, match="does not match"):
            await upload_fixture(service, "0" * 64)
        with pytest.raises(InvalidRequestError, match="source"):
            await upload_fixture(service, digest, source=" ")
        with pytest.raises(InvalidRequestError, match="filename"):
            await service.upload(
                owner,
                project.id,
                filename="../fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=digest,
            )

        for scan_status, error_type in (
            (ScanStatus.REJECTED, InvalidRequestError),
            (ScanStatus.FAILED, DependencyUnavailableError),
        ):
            rejected = AssetService(
                assets,
                projects=repo,
                storage=storage,
                scanner=StaticScanner(scan_status),
                upload_policy=DefaultUploadSecurityPolicy(max_bytes=32),
                authorizer=service._authorizer,  # noqa: SLF001 - white-box boundary test.
                clock=FixedClock(),
            )
            with pytest.raises(error_type):
                await upload_fixture(rejected, digest)

        failing_objects = FailingStorage()
        failing = AssetService(
            assets,
            projects=repo,
            storage=failing_objects,
            scanner=StaticScanner(ScanStatus.CLEAN),
            upload_policy=DefaultUploadSecurityPolicy(max_bytes=32),
            authorizer=service._authorizer,  # noqa: SLF001
            clock=FixedClock(),
        )
        with pytest.raises(DependencyUnavailableError, match="write failed"):
            await upload_fixture(failing, digest)
        failed_upload = next(iter(assets.uploads.values()))
        assert failed_upload.status is UploadStatus.FAILED
        with pytest.raises(InvalidStateError, match="stored partial"):
            await failing.resume_upload(owner, failed_upload.id)

        assets.fail_finalize_once = True
        with pytest.raises(RuntimeError, match="metadata failure"):
            await upload_fixture(service, digest)
        partial = next(
            upload
            for upload in assets.uploads.values()
            if upload.status is UploadStatus.COMPENSATION_REQUIRED
        )
        resumed = await service.resume_upload(owner, partial.id)
        assert resumed.upload is not None
        assert resumed.upload.status is UploadStatus.COMPLETED
        with pytest.raises(InvalidStateError, match="stored partial"):
            await service.resume_upload(owner, partial.id)
        with pytest.raises(ScopeViolationError):
            await service.resume_upload(context(Role.OWNER), partial.id)

        other_data = b"fixture-other"
        other_digest = hashlib.sha256(other_data).hexdigest()
        assets.fail_finalize_once = True
        with pytest.raises(RuntimeError):
            await service.upload(
                owner,
                project.id,
                filename="other.txt",
                media_type="text/plain",
                data=other_data,
                expected_sha256=other_digest,
            )
        invalid_partial = next(
            upload for upload in assets.uploads.values() if upload.content_hash == other_digest
        )
        storage.simulate_missing(invalid_partial.object_key)
        with pytest.raises(InvalidStateError, match="cannot satisfy"):
            await service.resume_upload(owner, invalid_partial.id)
        failed = assets.uploads[(owner.workspace_id, invalid_partial.id)]
        assert failed.status is UploadStatus.FAILED

        version_data = b"fixture-version-two"
        version_digest = hashlib.sha256(version_data).hexdigest()
        assets.fail_finalize_once = True
        with pytest.raises(RuntimeError):
            await service.upload(
                owner,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=version_data,
                expected_sha256=version_digest,
                asset_id=resumed.asset.id,
            )
        version_partial = next(
            upload for upload in assets.uploads.values() if upload.content_hash == version_digest
        )
        asset_key = (owner.workspace_id, project.id, resumed.asset.id)
        existing_pair = assets.assets.pop(asset_key)
        with pytest.raises(InvalidStateError, match="metadata is unavailable"):
            await service.resume_upload(owner, version_partial.id)
        assets.assets[asset_key] = (
            replace(existing_pair[0], status=AssetStatus.PENDING_DELETION),
            existing_pair[1],
        )
        with pytest.raises(InvalidStateError, match="state changed"):
            await service.resume_upload(owner, version_partial.id)

        archived = await projects.archive(owner, project.id, expected_version=1)
        assert archived.status is ProjectStatus.ARCHIVED
        with pytest.raises(InvalidStateError, match="Archived"):
            await upload_fixture(service, digest)

    asyncio.run(scenario())


def test_in_memory_storage_enforces_hash_key_and_collision_contracts() -> None:
    async def scenario() -> None:
        storage = InMemoryObjectStorage()
        data = b"fixture"
        digest = hashlib.sha256(data).hexdigest()
        key = object_key_for(uuid4(), uuid4(), uuid4(), uuid4())
        stored = await storage.put(key, data, media_type="text/plain", content_hash=digest)
        assert await storage.get(key) == data
        assert await storage.stat(key) == stored
        assert await storage.put(key, data, media_type="text/plain", content_hash=digest) == stored
        with pytest.raises(ValueError, match="hash"):
            await storage.put(
                object_key_for(uuid4(), uuid4(), uuid4(), uuid4()),
                data,
                media_type="text/plain",
                content_hash="0" * 64,
            )
        with pytest.raises(ValueError, match="different"):
            await storage.put(
                key,
                data,
                media_type="application/octet-stream",
                content_hash=digest,
            )
        storage.simulate_missing(key)
        assert await storage.stat(key) is None
        with pytest.raises(FileNotFoundError):
            await storage.get(key)

    asyncio.run(scenario())
    for key in ("", "/fixture", "fixture\\value", "fixture//value", "fixture/../value"):
        with pytest.raises(ValueError, match="canonical"):
            validate_object_key(key)


def s3_error(code: str) -> S3Error:
    return S3Error(None, code, "fixture", "fixture", "fixture", "fixture")  # type: ignore[arg-type]


def test_minio_adapter_put_get_stat_and_missing_mapping() -> None:
    client = MagicMock()
    response = MagicMock()
    response.read.return_value = b"fixture"
    client.get_object.return_value = response
    client.stat_object.return_value = SimpleNamespace(
        metadata={"x-amz-meta-sha256": hashlib.sha256(b"fixture").hexdigest()},
        content_type="text/plain",
        size=7,
    )
    with patch("accos.adapters.assets.storage.Minio", return_value=client) as factory:
        storage = MinioObjectStorage(
            endpoint="http://localhost:9000",
            bucket="fixture-project",
            access_key="fixture-access",
            secret_key="fixture-secret",
            secure=False,
            region="us-east-1",
        )
    factory.assert_called_once()
    assert factory.call_args.args == ("localhost:9000",)
    assert factory.call_args.kwargs["access_key"] == "fixture-access"
    assert factory.call_args.kwargs["secret_key"] == "fixture-secret"
    assert factory.call_args.kwargs["secure"] is False
    assert factory.call_args.kwargs["region"] == "us-east-1"
    assert factory.call_args.kwargs["http_client"] is not None
    key = object_key_for(uuid4(), uuid4(), uuid4(), uuid4())
    digest = hashlib.sha256(b"fixture").hexdigest()
    stored = asyncio.run(
        storage.put(
            key,
            b"fixture",
            media_type="text/plain",
            content_hash=digest,
        )
    )
    assert stored.size_bytes == 7
    assert asyncio.run(storage.get(key)) == b"fixture"
    assert asyncio.run(storage.stat(key)) == stored
    response.close.assert_called_once_with()
    response.release_conn.assert_called_once_with()
    with pytest.raises(ValueError, match="hash"):
        asyncio.run(
            storage.put(
                key,
                b"fixture",
                media_type="text/plain",
                content_hash="0" * 64,
            )
        )

    client.get_object.side_effect = s3_error("NoSuchKey")
    with pytest.raises(FileNotFoundError):
        asyncio.run(storage.get(key))
    client.stat_object.side_effect = s3_error("NoSuchObject")
    assert asyncio.run(storage.stat(key)) is None
    client.get_object.side_effect = s3_error("AccessDenied")
    with pytest.raises(S3Error):
        asyncio.run(storage.get(key))
    client.stat_object.side_effect = s3_error("AccessDenied")
    with pytest.raises(S3Error):
        asyncio.run(storage.stat(key))
    with pytest.raises(ValueError, match="endpoint"):
        MinioObjectStorage(
            endpoint="invalid",
            bucket="fixture",
            access_key="fixture",
            secret_key="fixture",
            secure=False,
            region="fixture",
        )
    with pytest.raises(ValueError, match="timeout"):
        MinioObjectStorage(
            endpoint="http://localhost:9000",
            bucket="fixture",
            access_key="fixture",
            secret_key="fixture",
            secure=False,
            region="fixture",
            timeout_seconds=0,
        )


def test_minio_stat_defaults_missing_provider_metadata() -> None:
    client = MagicMock()
    client.stat_object.return_value = SimpleNamespace(metadata=None, content_type=None, size=None)
    with patch("accos.adapters.assets.storage.Minio", return_value=client):
        storage = MinioObjectStorage(
            endpoint="https://localhost",
            bucket="fixture",
            access_key="fixture",
            secret_key="fixture",
            secure=True,
            region="fixture",
        )
    value = asyncio.run(storage.stat("fixture/key"))
    assert value == StoredObject("fixture/key", "", "application/octet-stream", 0)
