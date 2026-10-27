from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from accos.adapters.assets import InMemoryObjectStorage
from accos.adapters.identity import DevelopmentIdentityProvider, InMemoryRateLimiter
from accos.composition import AssetServices, IdentityServices, ProjectServices, build_container
from accos.entrypoints.api import create_app
from accos.entrypoints.api.v1 import stage17_router
from accos.entrypoints.api.v1.dependencies import (
    api_context,
    decode_cursor,
    encode_cursor,
    enforce_rate_limit,
    etag,
)
from accos.entrypoints.api.v1.schemas import AsyncOperationReference
from accos.kernel.errors import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
    InvalidRequestError,
    InvalidStateError,
    ResourceNotFoundError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.observability import (
    OutboxRuntimeSnapshot,
    RuntimeBoundaryState,
    RuntimeSnapshot,
    TelemetryRuntime,
    WorkerRuntimeSnapshot,
)
from accos.kernel.persistence import Page
from accos.kernel.security import (
    ActorKind,
    SecurityContext,
    bind_security_context,
    reset_security_context,
)
from accos.modules.assets.public import (
    Asset,
    AssetService,
    AssetSort,
    AssetStatus,
    AssetVersion,
    DefaultUploadSecurityPolicy,
    UnconfiguredContentScanner,
    UploadSession,
    UploadStatus,
)
from accos.modules.creative.common import CreativeRecordStatus
from accos.modules.creative.novel import DraftRevision
from accos.modules.identity.public import (
    POLICY_VERSION,
    AuditEvent,
    AuthorizationService,
    IdentityAuthenticator,
    IdentityQueryService,
    Membership,
    RateLimitDecision,
    Role,
    ServiceIdentity,
    User,
    Workspace,
    permissions_for,
)
from accos.modules.projects.public import (
    Artifact,
    ArtifactRevision,
    ArtifactSort,
    Project,
    ProjectService,
    ProjectSettings,
    ProjectSort,
    ProjectStatus,
)

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

    from accos.composition import AgentServices, ApplicationContainer, WorkflowServices
    from accos.composition.root import (
        ConsistencyServices,
        CreativeServices,
        EvolutionServices,
        FeedbackServices,
        KnowledgeServices,
        MemoryServices,
        QualityServices,
    )
    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope
    from accos.kernel.settings import RuntimeSettings
    from accos.modules.workflows.public import WorkflowRun, WorkflowRunEvent, WorkflowService

ACTOR_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_ACTOR_ID = UUID("22222222-2222-4222-8222-222222222222")
WORKSPACE_ID = UUID("33333333-3333-4333-8333-333333333333")
OTHER_WORKSPACE_ID = UUID("44444444-4444-4444-8444-444444444444")
MEMBERSHIP_ID = UUID("55555555-5555-4555-8555-555555555555")
NOW = datetime(2026, 9, 6, 8, 9, 10, tzinfo=UTC)
AUTH = {"Authorization": "Bearer fixture-token", "X-Workspace-ID": str(WORKSPACE_ID)}


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class IdentityReader:
    def __init__(self, role: Role) -> None:
        self.user = User(ACTOR_ID, "urn:accos:development", "local-development")
        self.workspace: Workspace | None = Workspace(WORKSPACE_ID, ACTOR_ID)
        self.membership = Membership(MEMBERSHIP_ID, WORKSPACE_ID, ACTOR_ID, role)

    async def find_user(self, issuer: str, subject: str) -> User | None:
        return self.user if (issuer, subject) == (self.user.issuer, self.user.subject) else None

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> Membership | None:
        if (workspace_id, user_id) == (WORKSPACE_ID, ACTOR_ID):
            return self.membership
        return None

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return self.workspace if workspace_id == WORKSPACE_ID else None

    async def list_memberships(self, workspace_id: UUID, page: PageRequest) -> Page[Membership]:
        values = (self.membership,) if workspace_id == WORKSPACE_ID else ()
        return Page(values[page.offset : page.offset + page.limit], len(values), page)

    async def get_service_identity(
        self, workspace_id: UUID, identity_id: UUID
    ) -> ServiceIdentity | None:
        del workspace_id, identity_id
        return None


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
        if sort in {ProjectSort.NAME, ProjectSort.NAME_DESC}:
            values.sort(key=lambda item: (item.name, item.id), reverse=reverse)
        else:
            values.sort(key=lambda item: (item.created_at, item.id), reverse=reverse)
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
        current = self.projects[(workspace_id, project_id)]
        if current.version != expected_version:
            raise ConcurrencyConflictError(current.version)
        changed = replace(current, settings=settings, updated_at=event.occurred_at, version=2)
        self.projects[(workspace_id, project_id)] = changed
        self.events.append(event)
        return changed

    async def archive(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        current = self.projects[(workspace_id, project_id)]
        if current.version != expected_version:
            raise ConcurrencyConflictError(current.version)
        changed = replace(
            current,
            status=ProjectStatus.ARCHIVED,
            updated_at=event.occurred_at,
            archived_at=event.occurred_at,
            version=current.version + 1,
        )
        self.projects[(workspace_id, project_id)] = changed
        self.events.append(event)
        return changed

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
            item
            for (workspace, project, _identifier), item in self.artifacts.items()
            if workspace == workspace_id and project == project_id
        ]
        reverse = sort in {ArtifactSort.CREATED_AT_DESC, ArtifactSort.LABEL_DESC}
        if sort in {ArtifactSort.LABEL, ArtifactSort.LABEL_DESC}:
            values.sort(key=lambda item: (item.label, item.id), reverse=reverse)
        else:
            values.sort(key=lambda item: (item.created_at, item.id), reverse=reverse)
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def list_revisions(
        self,
        workspace_id: UUID,
        project_id: UUID,
        artifact_id: UUID,
        page: PageRequest,
    ) -> Page[ArtifactRevision]:
        values = tuple(
            item
            for item in reversed(self.revisions)
            if (item.workspace_id, item.project_id, item.artifact_id)
            == (workspace_id, project_id, artifact_id)
        )
        return Page(values[page.offset : page.offset + page.limit], len(values), page)

    async def add_revision(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> tuple[Artifact, ArtifactRevision]:
        key = (artifact.workspace_id, artifact.project_id, artifact.id)
        if self.artifacts[key].version != expected_version:
            raise ConcurrencyConflictError(self.artifacts[key].version)
        self.artifacts[key] = artifact
        self.revisions.append(revision)
        self.events.append(event)
        return artifact, revision


class MemoryAssets:
    def __init__(self) -> None:
        self.assets: dict[tuple[UUID, UUID, UUID], tuple[Asset, AssetVersion]] = {}
        self.uploads: dict[tuple[UUID, UUID], UploadSession] = {}
        self.events: list[EventEnvelope] = []

    async def find_version_by_hash(
        self, workspace_id: UUID, project_id: UUID, content_hash: str
    ) -> tuple[Asset, AssetVersion] | None:
        return next(
            (
                pair
                for (workspace, project, _identifier), pair in self.assets.items()
                if (workspace, project, pair[1].content_hash)
                == (workspace_id, project_id, content_hash)
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
        changed = replace(
            self.uploads[key],
            status=UploadStatus(status),
            updated_at=updated_at,
            error_code=error_code,
        )
        self.uploads[key] = changed
        return changed

    async def finalize_upload(
        self,
        session: UploadSession,
        asset: Asset,
        version: AssetVersion,
        event: EventEnvelope,
    ) -> tuple[Asset, AssetVersion, UploadSession]:
        completed = replace(session, status=UploadStatus.COMPLETED)
        self.uploads[(session.workspace_id, session.id)] = completed
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
        if sort in {AssetSort.FILENAME, AssetSort.FILENAME_DESC}:
            values.sort(key=lambda pair: (pair[0].filename, pair[0].id), reverse=reverse)
        else:
            values.sort(key=lambda pair: (pair[0].created_at, pair[0].id), reverse=reverse)
        return Page(tuple(values[page.offset : page.offset + page.limit]), len(values), page)

    async def set_processing_status(
        self,
        workspace_id: UUID,
        version_id: UUID,
        status: str,
        *,
        updated_at: datetime,
    ) -> AssetVersion:
        del workspace_id, version_id, status, updated_at
        raise InvalidStateError("fixture unused")

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
            updated_at=marked_at,
            deletion_marked_at=marked_at,
            retention_until=retention_until,
            version=asset.version + 1,
        )
        self.assets[key] = (changed, version)
        self.events.append(event)
        return changed


@dataclass(frozen=True, slots=True)
class DeniedLimiter:
    async def check(self, context: object, action: str) -> RateLimitDecision:
        del context, action
        return RateLimitDecision(allowed=False, retry_after_seconds=7)


class UnavailableRuntimeMonitor:
    """Keep API unit tests independent from locally running Redis/PostgreSQL."""

    snapshot_value = RuntimeSnapshot(
        WorkerRuntimeSnapshot(
            RuntimeBoundaryState.UNAVAILABLE,
            "heartbeat_store_unavailable",
            None,
        ),
        OutboxRuntimeSnapshot(
            RuntimeBoundaryState.UNAVAILABLE,
            "backlog_query_unavailable",
            None,
            None,
        ),
    )

    async def heartbeat(self) -> None:
        return None

    async def snapshot(self) -> RuntimeSnapshot:
        return self.snapshot_value

    async def refresh_metrics(self, telemetry: TelemetryRuntime) -> RuntimeSnapshot:
        del telemetry
        return self.snapshot_value


def configured_app(
    runtime_settings: RuntimeSettings,
    *,
    role: Role = Role.OWNER,
    denied: bool = False,
) -> tuple[FastAPI, MemoryProjects, MemoryAssets, MemoryAudit]:
    container = build_container(runtime_settings, clock=FixedClock(), probes=())
    container = replace(
        container,
        observability=replace(
            container.observability,
            monitor=UnavailableRuntimeMonitor(),
        ),
    )
    identities = IdentityReader(role)
    audit = MemoryAudit()
    authorizer = AuthorizationService(audit, FixedClock())
    identity = IdentityServices(
        authenticator=IdentityAuthenticator(
            DevelopmentIdentityProvider("fixture-token"), identities, FixedClock()
        ),
        authorizer=authorizer,
        creator_control=container.identity.creator_control,
        rate_limiter=DeniedLimiter() if denied else InMemoryRateLimiter(max_requests=1000),
        upload_policy=DefaultUploadSecurityPolicy(max_bytes=1024),
        query=IdentityQueryService(identities, authorizer),
    )
    projects_repository = MemoryProjects()
    projects = ProjectServices(
        ProjectService(projects_repository, authorizer, FixedClock()), projects_repository
    )
    assets_repository = MemoryAssets()
    storage = InMemoryObjectStorage()
    assets = AssetServices(
        AssetService(
            assets_repository,
            projects=projects_repository,
            storage=storage,
            scanner=UnconfiguredContentScanner(),
            upload_policy=identity.upload_policy,
            authorizer=authorizer,
            clock=FixedClock(),
        ),
        assets_repository,
        storage,
    )
    app = create_app(
        runtime_settings,
        container=replace(container, identity=identity, projects=projects, assets=assets),
        configure_logs=False,
    )
    return app, projects_repository, assets_repository, audit


def test_v1_identity_workspace_errors_and_shared_contracts(
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, _assets, audit = configured_app(runtime_settings)
    with TestClient(app) as client:
        missing = client.get("/api/v1/identity/me")
        me = client.get("/api/v1/identity/me", headers=AUTH)
        old = client.get("/api/v1/identity/context", headers=AUTH)
        workspaces = client.get("/api/v1/workspaces?limit=1", headers=AUTH)
        empty = client.get(f"/api/v1/workspaces?cursor={encode_cursor(1)}&limit=1", headers=AUTH)
        workspace = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}", headers=AUTH)
        memberships = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/memberships", headers=AUTH)
        forged = client.get(f"/api/v1/workspaces/{OTHER_WORKSPACE_ID}", headers=AUTH)
        bad_cursor = client.get("/api/v1/workspaces?cursor=bad", headers=AUTH)
        not_found = client.get("/api/v1/missing", headers=AUTH)
        wrong_method = client.post("/api/v1/identity/me", headers=AUTH)

    assert missing.status_code == 401
    assert me.status_code == 200, me.text
    assert me.json()["actor_id"] == str(ACTOR_ID)
    assert UUID(me.headers["x-correlation-id"]).version == 4
    assert old.headers["deprecation"] == "true"
    assert "successor-version" in old.headers["link"]
    assert workspaces.json()["page"] == {"total": 1, "limit": 1, "next_cursor": None}
    assert empty.json()["items"] == []
    assert workspace.json()["owner_user_id"] == str(ACTOR_ID)
    assert memberships.json()["items"][0]["role"] == "OWNER"
    assert forged.status_code == 403
    assert bad_cursor.status_code == 400
    assert not_found.status_code == 404
    assert wrong_method.status_code == 405
    assert audit.events
    assert decode_cursor(encode_cursor(42)) == 42
    assert etag(3) == '"3"'
    assert (
        AsyncOperationReference(
            task_id=ACTOR_ID,
            status_url="/api/v1/tasks/fixture",
            accepted_at=NOW,
        ).task_id
        == ACTOR_ID
    )


def test_v1_project_artifact_revision_flow_and_negative_matrix(
    runtime_settings: RuntimeSettings,
) -> None:
    app, projects, _assets, _audit = configured_app(runtime_settings)
    create_body = {
        "name": "fixture-project",
        "settings": {"revision_retention_limit": 5, "asset_retention_days": 2},
    }
    headers = {**AUTH, "Idempotency-Key": "fixture-create"}
    with TestClient(app) as client:
        created = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects", headers=headers, json=create_body
        )
        replay = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects", headers=headers, json=create_body
        )
        conflict = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects",
            headers=headers,
            json={**create_body, "name": "fixture-other"},
        )
        bad_key = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects",
            headers={**AUTH, "Idempotency-Key": " "},
            json=create_body,
        )
        second = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects",
            headers={**AUTH, "Idempotency-Key": "fixture-second"},
            json={**create_body, "name": "fixture-z"},
        )
        project_id = created.json()["id"]
        listing = client.get(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects?status=active&sort=name&limit=1",
            headers=AUTH,
        )
        fetched = client.get(f"/api/v1/projects/{project_id}", headers=AUTH)
        missing_match = client.patch(
            f"/api/v1/projects/{project_id}", headers=AUTH, json={"settings": {}}
        )
        malformed_match = client.patch(
            f"/api/v1/projects/{project_id}",
            headers={**AUTH, "If-Match": "1"},
            json={"settings": {}},
        )
        stale = client.patch(
            f"/api/v1/projects/{project_id}",
            headers={**AUTH, "If-Match": '"9"'},
            json={"settings": {}},
        )
        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            headers={**AUTH, "If-Match": '"1"'},
            json={"settings": {"revision_retention_limit": 7, "asset_retention_days": 3}},
        )
        forged_actor = client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            headers=AUTH,
            json={
                "artifact_type": "other",
                "label": "fixture-artifact",
                "actor_id": str(OTHER_ACTOR_ID),
            },
        )
        artifact = client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            headers=AUTH,
            json={"artifact_type": "other", "label": "fixture-artifact"},
        )
        artifact_id = artifact.json()["id"]
        artifacts = client.get(f"/api/v1/projects/{project_id}/artifacts?sort=label", headers=AUTH)
        fetched_artifact = client.get(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}", headers=AUTH
        )
        invalid_revision = client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions",
            headers={**AUTH, "If-Match": '"1"'},
            json={"content_reference": "fixture-ref"},
        )
        revision = client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions",
            headers={**AUTH, "If-Match": '"1"'},
            json={"content_reference": "fixture-ref", "content_hash": "0" * 64},
        )
        revisions = client.get(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions",
            headers=AUTH,
        )
        archived = client.post(
            f"/api/v1/projects/{project_id}/archive",
            headers={**AUTH, "If-Match": '"2"'},
        )

    assert created.status_code == 201
    assert created.headers["etag"] == '"1"'
    assert replay.json()["id"] == project_id
    assert conflict.status_code == 409
    assert bad_key.status_code == 400
    assert second.status_code == 201
    assert listing.json()["items"][0]["id"] == project_id
    assert listing.json()["page"]["next_cursor"] is not None
    assert fetched.headers["etag"] == '"1"'
    assert missing_match.status_code == 428
    assert malformed_match.status_code == 400
    assert stale.json()["error"]["details"] == {"current_version": 1}
    assert updated.headers["etag"] == '"2"'
    assert forged_actor.status_code == 422
    assert artifact.status_code == 201
    assert artifacts.json()["items"][0]["id"] == artifact_id
    assert fetched_artifact.headers["etag"] == '"1"'
    assert invalid_revision.status_code == 422
    assert revision.json()["revision_number"] == 1
    assert revisions.json()["items"][0]["content_reference"] == "fixture-ref"
    assert archived.json()["status"] == "archived"
    assert projects.events[0].payload["correlation_id"]
    assert any(event.event_type == "projects.artifact-created" for event in projects.events)


def test_v1_asset_and_health_flow(  # noqa: PLR0915
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, assets, _audit = configured_app(runtime_settings)
    data = b"fixture-asset"
    digest = hashlib.sha256(data).hexdigest()
    body = {
        "filename": "fixture.txt",
        "media_type": "text/plain",
        "content_base64": base64.b64encode(data).decode(),
        "expected_sha256": digest,
    }
    with TestClient(app) as client:
        project = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects",
            headers={**AUTH, "Idempotency-Key": "fixture-asset-project"},
            json={"name": "fixture-project"},
        )
        project_id = project.json()["id"]
        media_error = client.post(
            f"/api/v1/projects/{project_id}/assets",
            headers={**AUTH, "Content-Type": "text/plain"},
            content="fixture",
        )
        created = client.post(f"/api/v1/projects/{project_id}/assets", headers=AUTH, json=body)
        asset_id = created.json()["id"]
        replay = client.post(f"/api/v1/projects/{project_id}/assets", headers=AUTH, json=body)
        listing = client.get(
            f"/api/v1/projects/{project_id}/assets?status=active&sort=filename",
            headers=AUTH,
        )
        fetched = client.get(f"/api/v1/projects/{project_id}/assets/{asset_id}", headers=AUTH)
        missing_asset = client.get(
            f"/api/v1/projects/{project_id}/assets/{OTHER_ACTOR_ID}", headers=AUTH
        )
        content = client.get(
            f"/api/v1/projects/{project_id}/assets/{asset_id}/content", headers=AUTH
        )
        stale_version = client.post(
            f"/api/v1/projects/{project_id}/assets/{asset_id}/versions",
            headers={**AUTH, "If-Match": '"7"'},
            json={**body, "content_base64": base64.b64encode(b"fixture-next").decode()},
        )
        next_data = b"fixture-next"
        next_body = {
            **body,
            "content_base64": base64.b64encode(next_data).decode(),
            "expected_sha256": hashlib.sha256(next_data).hexdigest(),
        }
        version = client.post(
            f"/api/v1/projects/{project_id}/assets/{asset_id}/versions",
            headers={**AUTH, "If-Match": '"1"'},
            json=next_body,
        )
        stale_delete = client.delete(
            f"/api/v1/projects/{project_id}/assets/{asset_id}",
            headers={**AUTH, "If-Match": '"1"'},
        )
        deleted = client.delete(
            f"/api/v1/projects/{project_id}/assets/{asset_id}",
            headers={**AUTH, "If-Match": '"2"'},
        )
        health = client.get("/api/v1/system/health", headers=AUTH)
        settings = client.get("/api/v1/system/settings", headers=AUTH)
        observability = client.get("/api/v1/system/observability", headers=AUTH)
        extensions = client.get("/api/v1/extensions/status", headers=AUTH)
        base_container = cast("ApplicationContainer", app.state.container)
        app.state.container = replace(
            base_container,
            workflows=replace(base_container.workflows, celery_app=None),
        )
        unconfigured_settings = client.get("/api/v1/system/settings", headers=AUTH)

    assert media_error.status_code == 415
    assert created.status_code == 201
    assert replay.status_code == 200
    assert listing.json()["items"][0]["id"] == asset_id
    assert fetched.headers["etag"] == '"1"'
    assert missing_asset.status_code == 403
    assert content.content == data
    assert content.headers["content-type"].startswith("text/plain")
    assert stale_version.status_code == 409
    assert version.json()["current"]["version_number"] == 2
    assert stale_delete.status_code == 409
    assert deleted.json()["status"] == "pending_deletion"
    assert health.json()["status"] == "ready"
    assert settings.json()["feature_flags"][0] == {
        "name": "real_provider_calls",
        "enabled": False,
    }
    assert len(settings.json()["feature_flags"]) == 12
    assert {item["name"] for item in settings.json()["feature_flags"][1:]} == set(
        runtime_settings.features.extension_values()
    )
    assert extensions.status_code == 200
    assert len(extensions.json()["items"]) == 13
    assert all(item["state"] == "DISABLED" for item in extensions.json()["items"])
    assert extensions.json()["items"][0]["configuration_schema_version"] == "1.0.0"
    assert extensions.json()["items"][0]["promotion_criteria"] == [
        "user_demand",
        "data_owner",
        "threat_model",
        "slo",
        "cost",
        "migration",
        "exit_plan",
    ]
    assert settings.json()["runtime_boundaries"] == [
        {
            "name": "worker",
            "status": "unavailable",
            "detail": "heartbeat_store_unavailable",
        },
        {
            "name": "outbox",
            "status": "unavailable",
            "detail": "backlog_query_unavailable",
        },
    ]
    assert observability.status_code == 200
    assert observability.json()["metrics_enabled"] is True
    assert observability.json()["otlp_configured"] is False
    assert "accos_api_request_duration_seconds" in observability.json()["metric_names"]
    assert observability.json()["runtime_boundaries"] == settings.json()["runtime_boundaries"]
    assert unconfigured_settings.json()["runtime_boundaries"][0] == {
        "name": "worker",
        "status": "not_configured",
        "detail": "queue_consumer_not_configured_in_api_process",
    }
    assert assets.events[0].payload["correlation_id"]


def test_v1_viewer_rate_limit_and_safe_validation_matrix(
    runtime_settings: RuntimeSettings,
) -> None:
    viewer_app, _projects, _assets, _audit = configured_app(runtime_settings, role=Role.VIEWER)
    denied_app, _projects, _assets, _audit = configured_app(runtime_settings, denied=True)
    with TestClient(viewer_app) as viewer:
        denied_write = viewer.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/projects",
            headers={**AUTH, "Idempotency-Key": "fixture-viewer"},
            json={"name": "fixture-project"},
        )
        invalid = viewer.get(f"/api/v1/workspaces/{WORKSPACE_ID}/projects?limit=0", headers=AUTH)
    with TestClient(denied_app) as denied:
        limited = denied.get("/api/v1/identity/me", headers=AUTH)

    assert denied_write.status_code == 403
    assert invalid.status_code == 422
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "7"
    assert "fixture" not in limited.text


def test_cursor_and_rate_limiter_defensive_branches(
    runtime_settings: RuntimeSettings,
) -> None:
    for invalid in ("%", "bad", "AAAAAAAAAAA=", ""):
        with pytest.raises(InvalidRequestError):
            decode_cursor(invalid)
    with pytest.raises(ValueError, match="non-negative"):
        encode_cursor(-1)

    values = iter((0.0, 0.0, 2.0))
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1, monotonic=lambda: next(values))
    context = SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        WORKSPACE_ID,
        permissions_for(Role.OWNER),
        POLICY_VERSION,
        CorrelationIds(str(ACTOR_ID), str(OTHER_ACTOR_ID)),
    )

    async def scenario() -> None:
        assert (await limiter.check(context, "fixture")).allowed
        assert not (await limiter.check(context, "fixture")).allowed
        assert (await limiter.check(context, "fixture")).allowed

        reader = IdentityReader(Role.OWNER)
        reader.workspace = None
        query = IdentityQueryService(reader, AuthorizationService(MemoryAudit(), FixedClock()))
        with pytest.raises(ResourceNotFoundError):
            await query.get_workspace(context, WORKSPACE_ID)

        app, _projects, _assets, _audit = configured_app(runtime_settings)
        request = cast("Request", SimpleNamespace(scope={}, method="GET"))
        await enforce_rate_limit(request, context, app.state.container)

    asyncio.run(scenario())
    token = bind_security_context(context)
    try:
        with pytest.raises(ScopeViolationError):
            api_context(OTHER_WORKSPACE_ID)
    finally:
        reset_security_context(token)
    for max_requests, window in ((0, 1), (1, 0)):
        with pytest.raises(ValueError, match="positive"):
            InMemoryRateLimiter(max_requests=max_requests, window_seconds=window)


@dataclass(frozen=True, slots=True)
class Stage17Doubles:
    ids: dict[str, UUID]
    workflow: SimpleNamespace
    knowledge: SimpleNamespace
    creative: SimpleNamespace


def install_stage17_doubles(app: FastAPI) -> Stage17Doubles:  # noqa: PLR0915
    ids: dict[str, UUID] = {}

    def identifier(name: str) -> UUID:
        value = uuid4()
        ids[name] = value
        return value

    project_id = identifier("project")
    workflow_run = SimpleNamespace(
        id=identifier("workflow_run"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        definition_name="framework-smoke",
        definition_version=1,
        status="pending",
        input_reference="fixture-token://framework-smoke",
        requested_by=ACTOR_ID,
        correlation_id=ACTOR_ID,
        created_at=NOW,
        updated_at=NOW,
        current_step_position=0,
        output_reference=None,
        error_reference=None,
        version=1,
    )
    step = SimpleNamespace(
        id=identifier("step"),
        workflow_run_id=workflow_run.id,
        step_key="fixture-step",
        position=0,
        status="pending",
        attempt=0,
        created_at=NOW,
        updated_at=NOW,
        version=1,
    )
    task = SimpleNamespace(
        id=identifier("task"),
        workflow_run_id=workflow_run.id,
        step_run_id=step.id,
        status="pending",
        attempt=0,
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        version=1,
    )
    approval = SimpleNamespace(
        id=identifier("approval"),
        workflow_run_id=workflow_run.id,
        step_run_id=step.id,
        requested_by=OTHER_ACTOR_ID,
        status="pending",
        expires_at=NOW,
        created_at=NOW,
    )
    event = SimpleNamespace(
        id=identifier("event"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        workflow_run_id=workflow_run.id,
        sequence=1,
        event_type="workflows.run-submitted",
        version=1,
        payload={"schema": "run-submitted.v1"},
        occurred_at=NOW,
    )
    workflow = SimpleNamespace(
        submit=AsyncMock(return_value=workflow_run),
        get=AsyncMock(return_value=workflow_run),
        get_steps=AsyncMock(return_value=(step,)),
        get_tasks=AsyncMock(return_value=(task,)),
        pause=AsyncMock(return_value=workflow_run),
        resume=AsyncMock(return_value=workflow_run),
        cancel=AsyncMock(return_value=workflow_run),
        get_approval=AsyncMock(return_value=approval),
        decide_approval=AsyncMock(return_value=workflow_run),
        get_events=AsyncMock(return_value=(event,)),
    )
    agent_run = SimpleNamespace(
        id=identifier("agent_run"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        agent_id="director",
        agent_version="1.0.0",
        status="succeeded",
        attempt=1,
        requested_by=ACTOR_ID,
        correlation_id=ACTOR_ID,
        created_at=NOW,
        updated_at=NOW,
        workflow_run_id=workflow_run.id,
        result_kind="workflow_selection",
        result_reference="workflow-selection://fixture",
        protected_operations=(),
        model_calls=1,
        tool_calls=1,
        tokens=8,
        error_code=None,
    )
    agent_supervisor = SimpleNamespace(get=AsyncMock(return_value=agent_run))
    agent_master = SimpleNamespace(
        submit_goal=AsyncMock(
            return_value=SimpleNamespace(workflow_run=workflow_run, agent_run=agent_run)
        )
    )
    document = SimpleNamespace(
        id=identifier("document"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        asset_id=identifier("asset"),
        created_at=NOW,
    )
    ingestion = SimpleNamespace(
        id=identifier("ingestion"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        document_id=document.id,
        document_version_id=identifier("document_version"),
        status="uploaded",
        verification_policy="not_required",
        verification_status="unverified",
        requested_by=ACTOR_ID,
        correlation_id=ACTOR_ID,
        attempt=1,
        created_at=NOW,
        updated_at=NOW,
        failed_stage=None,
        error_code=None,
        retryable=False,
        workflow_run_id=workflow_run.id,
    )
    citation = SimpleNamespace(
        id=identifier("citation"),
        document_id=document.id,
        document_version_id=ingestion.document_version_id,
        asset_id=document.asset_id,
        asset_version_id=identifier("asset_version"),
        chunk_id=identifier("chunk"),
        locator="fixture:1",
        verification_status="unverified",
    )
    knowledge = SimpleNamespace(
        submit=AsyncMock(return_value=ingestion),
        get=AsyncMock(return_value=ingestion),
        retry=AsyncMock(return_value=ingestion),
        get_document=AsyncMock(return_value=document),
        retrieve=AsyncMock(
            return_value=SimpleNamespace(
                query="fixture-query",
                hits=(
                    SimpleNamespace(
                        score=1.0,
                        chunk=SimpleNamespace(content="fixture-content"),
                        citation=citation,
                    ),
                ),
            )
        ),
    )
    memory = SimpleNamespace(
        id=identifier("memory"),
        logical_id=identifier("memory_logical"),
        version=1,
        workspace_id=WORKSPACE_ID,
        scope="project",
        memory_type="fixture",
        content="fixture-memory",
        project_id=project_id,
        valid_from=NOW,
        valid_until=None,
        observed_at=NOW,
        importance=0.5,
        confidence=0.5,
        provenance=SimpleNamespace(
            kind="fixture",
            reference="fixture-memory://source",
        ),
        status="active",
        current=True,
        created_by=ACTOR_ID,
        created_at=NOW,
    )
    conflict = SimpleNamespace(
        id=identifier("memory_conflict"),
        current_record_id=memory.id,
        candidate_record_id=identifier("memory_candidate"),
        candidate_resolutions=("keep_current", "accept_candidate"),
        status="pending",
        proposed_by=ACTOR_ID,
        proposed_at=NOW,
        decided_by=None,
        decided_at=None,
    )
    context_item = SimpleNamespace(
        record_id=memory.id,
        scope="project",
        memory_type="fixture",
        content="fixture-memory",
        score=1.0,
    )
    context_package = SimpleNamespace(
        id=identifier("context_package"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        task_reference="fixture-task://context",
        budget_chars=100,
        used_chars=14,
        items=(context_item,),
        checksum="0" * 64,
        created_by=ACTOR_ID,
        created_at=NOW,
        budget_tokens=None,
        used_tokens=4,
    )
    memory_service = SimpleNamespace(
        write=AsyncMock(return_value=memory),
        get=AsyncMock(return_value=memory),
        propose_revision=AsyncMock(return_value=conflict),
        get_conflict=AsyncMock(return_value=conflict),
        decide_conflict=AsyncMock(return_value=conflict),
    )
    context_builder = SimpleNamespace(
        build=AsyncMock(return_value=context_package),
        get=AsyncMock(return_value=context_package),
    )

    def creative(owner: str, name: str) -> SimpleNamespace:
        return SimpleNamespace(
            owner=owner,
            id=identifier(name),
            workspace_id=WORKSPACE_ID,
            project_id=project_id,
            label=f"fixture-{name}",
            created_by=ACTOR_ID,
            created_at=NOW,
            updated_at=NOW,
            version=1,
        )

    world = creative("world", "world")
    character = creative("character", "character")
    work = creative("novel", "work")
    draft = DraftRevision(
        identifier("draft"),
        identifier("draft_logical"),
        1,
        WORKSPACE_ID,
        project_id,
        work.id,
        CreativeRecordStatus.PROPOSAL,
        False,
        (),
        "fixture-draft://source",
        0,
        ACTOR_ID,
        NOW,
    )
    creative_services = SimpleNamespace(
        world=SimpleNamespace(
            create=AsyncMock(return_value=world), get=AsyncMock(return_value=world)
        ),
        character=SimpleNamespace(
            create=AsyncMock(return_value=character), get=AsyncMock(return_value=character)
        ),
        novel=SimpleNamespace(
            create=AsyncMock(return_value=work),
            get=AsyncMock(return_value=work),
            propose=AsyncMock(return_value=(draft, True)),
            get_record=AsyncMock(return_value=draft),
            decide=AsyncMock(return_value=draft),
        ),
    )
    finding = SimpleNamespace(
        id=identifier("finding"),
        check_run_id=identifier("check"),
        finding_type="required_field",
        severity="error",
        evidence_references=("fixture-evidence://required",),
        message_code="fixture_missing",
        validator_key="fixture-validator",
        validator_version="1",
        status="open",
        workflow_run_id=workflow_run.id,
        detected_at=NOW,
    )
    check_run = SimpleNamespace(
        id=finding.check_run_id,
        project_id=project_id,
        status="findings",
        workflow_run_id=workflow_run.id,
        created_at=NOW,
    )
    resolution = SimpleNamespace(
        id=identifier("resolution"),
        project_id=project_id,
        finding_ids=(finding.id,),
        strategy_code="fixture-strategy",
        requires_approval=True,
        status="proposed",
        requested_by=ACTOR_ID,
        workflow_run_id=workflow_run.id,
        created_at=NOW,
        updated_at=NOW,
        approved_by=None,
        applied_by=None,
        version=1,
    )
    consistency = SimpleNamespace(
        run_check=AsyncMock(return_value=(check_run, (finding,))),
        get_check=AsyncMock(return_value=check_run),
        get_check_with_findings=AsyncMock(return_value=(check_run, (finding,))),
        propose_resolution=AsyncMock(return_value=resolution),
        trace=AsyncMock(return_value=SimpleNamespace(proposal=resolution)),
        decide_resolution=AsyncMock(return_value=resolution),
    )
    rubric = SimpleNamespace(
        id=identifier("rubric"),
        project_id=project_id,
        rubric_key="fixture-rubric",
        version=1,
        schema_version="quality.v1",
        dimension_keys=("fixture-dimension",),
        created_by=ACTOR_ID,
        created_at=NOW,
    )
    evaluation = SimpleNamespace(
        id=identifier("evaluation"),
        project_id=project_id,
        rubric_id=rubric.id,
        input_reference="fixture-quality://input",
        workflow_run_id=workflow_run.id,
        requested_by=ACTOR_ID,
        status="not_run",
        created_at=NOW,
        completed_at=None,
    )
    quality_result = SimpleNamespace(
        id=identifier("quality_result"),
        evaluation_run_id=evaluation.id,
        status="passed",
        evaluator_key="structural",
        evaluator_version="1",
        dimensions=(SimpleNamespace(key="fixture-dimension", status="passed", score=1.0),),
        result_reference="quality-result://fixture",
        created_at=NOW,
    )
    quality = SimpleNamespace(
        create_rubric=AsyncMock(return_value=rubric),
        start=AsyncMock(return_value=evaluation),
        evaluate=AsyncMock(return_value=(evaluation, quality_result)),
        get_result=AsyncMock(return_value=quality_result),
    )
    feedback = SimpleNamespace(
        id=identifier("feedback"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        actor_id=ACTOR_ID,
        source="user",
        schema_version="feedback.v1",
        signal_code="fixture-signal",
        numeric_value=1.0,
        source_reference="fixture-feedback://source",
        status="active",
        occurred_at=NOW,
        creator_signal_reference=None,
    )
    metric_definition = SimpleNamespace(
        id=identifier("metric_definition"),
        project_id=project_id,
        name="fixture.metric",
        version=1,
        unit="count",
        retention_days=7,
        created_by=ACTOR_ID,
        created_at=NOW,
    )
    metric_point = SimpleNamespace(
        id=identifier("metric_point"),
        project_id=project_id,
        metric_name="fixture.metric",
        value=1.0,
        dimensions=(("status", "ok"),),
        observed_at=NOW,
        source_reference="fixture-metric://source",
        source_feedback_event_id=feedback.id,
        included=True,
        tombstoned_at=None,
    )
    diagnostic = SimpleNamespace(
        id=identifier("diagnostic"),
        project_id=project_id,
        metric_point_id=metric_point.id,
        rule_key="fixture-rule",
        rule_version="1",
        finding_code="fixture-finding",
        severity="warning",
        observed_value=1.0,
        threshold_value=0.5,
        created_at=NOW,
    )
    consent = SimpleNamespace(
        id=identifier("consent"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        actor_id=ACTOR_ID,
        policy_version="behavior-consent-v1",
        status="active",
        granted_at=NOW,
        withdrawn_at=None,
    )
    withdrawn_consent = SimpleNamespace(
        **{**vars(consent), "status": "withdrawn", "withdrawn_at": NOW}
    )
    experiment = SimpleNamespace(
        id=identifier("experiment"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        experiment_key="fixture-experiment",
        protocol_version="protocol-v1",
        hypothesis_code="fixture-hypothesis",
        primary_metric_name="fixture.metric",
        sample_scope="technical-smoke",
        starts_at=NOW,
        ends_at=NOW + timedelta(hours=1),
        stop_condition_codes=("fixture-stop",),
        status="planned",
        created_by=ACTOR_ID,
        created_at=NOW,
        result_code=None,
    )
    variant = SimpleNamespace(
        id=identifier("variant"),
        experiment_id=experiment.id,
        variant_key="control",
        configuration_reference="fixture-config://control",
    )
    candidate = SimpleNamespace(
        id=identifier("variant_candidate"),
        experiment_id=experiment.id,
        variant_key="candidate",
        configuration_reference="fixture-config://candidate",
    )
    experiment_sample = SimpleNamespace(
        id=identifier("experiment_sample"),
        workspace_id=WORKSPACE_ID,
        project_id=project_id,
        experiment_id=experiment.id,
        variant_id=variant.id,
        metric_point_id=metric_point.id,
        source_feedback_event_id=feedback.id,
        observed_at=NOW,
        included=True,
        tombstoned_at=None,
    )
    feedback_service = SimpleNamespace(
        capture=AsyncMock(return_value=feedback),
        get_feedback=AsyncMock(return_value=feedback),
        get_behavior_consent=AsyncMock(return_value=consent),
        grant_behavior_consent=AsyncMock(return_value=consent),
        withdraw_behavior_consent=AsyncMock(
            return_value=SimpleNamespace(
                consent=withdrawn_consent,
                anonymized_event_ids=(feedback.id,),
                tombstones=(SimpleNamespace(),),
            )
        ),
        register_metric=AsyncMock(return_value=metric_definition),
        record_metric=AsyncMock(return_value=metric_point),
        get_metric_point=AsyncMock(return_value=metric_point),
        diagnose=AsyncMock(return_value=(diagnostic,)),
        get_diagnostic=AsyncMock(return_value=diagnostic),
        create_experiment=AsyncMock(return_value=(experiment, (variant, candidate))),
        get_experiment=AsyncMock(return_value=(experiment, (variant, candidate))),
        start_experiment=AsyncMock(return_value=experiment),
        add_experiment_sample=AsyncMock(return_value=experiment_sample),
        finish_experiment=AsyncMock(return_value=experiment),
    )
    proposal = SimpleNamespace(
        id=identifier("proposal"),
        project_id=project_id,
        diagnostic_finding_ids=(diagnostic.id,),
        input_references=("diagnostic://fixture",),
        algorithm_versions=("observer@1",),
        state="observed",
        requested_by=ACTOR_ID,
        created_at=NOW,
        updated_at=NOW,
        action=None,
        change_reference=None,
        safety_policy_version=None,
        safety_rule_code=None,
        simulation_evidence=(),
        evaluation_code=None,
        approved_by=None,
        rollback_reference=None,
        version=1,
    )
    evolution = SimpleNamespace(
        observe=AsyncMock(return_value=proposal),
        get=AsyncMock(return_value=proposal),
        propose=AsyncMock(return_value=proposal),
        simulate=AsyncMock(return_value=proposal),
        evaluate=AsyncMock(return_value=proposal),
        request_approval=AsyncMock(return_value=proposal),
        decide=AsyncMock(return_value=proposal),
    )
    base = cast("ApplicationContainer", app.state.container)
    app.state.container = replace(
        base,
        workflows=cast("WorkflowServices", SimpleNamespace(service=workflow)),
        agents=cast(
            "AgentServices",
            SimpleNamespace(
                registry=base.agents.registry,
                supervisor=agent_supervisor,
                master=agent_master,
            ),
        ),
        knowledge=cast("KnowledgeServices", SimpleNamespace(service=knowledge)),
        memory=cast(
            "MemoryServices",
            SimpleNamespace(service=memory_service, context_builder=context_builder),
        ),
        creative=cast("CreativeServices", creative_services),
        consistency=cast("ConsistencyServices", SimpleNamespace(service=consistency)),
        quality=cast("QualityServices", SimpleNamespace(service=quality)),
        feedback=cast("FeedbackServices", SimpleNamespace(service=feedback_service)),
        evolution=cast("EvolutionServices", SimpleNamespace(service=evolution)),
    )
    return Stage17Doubles(ids, workflow, knowledge, creative_services)


def test_v1_stage17_workflow_agent_status_and_contract_matrix(
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, _assets, _audit = configured_app(runtime_settings)
    doubles = install_stage17_doubles(app)
    project_id = doubles.ids["project"]
    run_id = doubles.ids["workflow_run"]
    with TestClient(app) as client:
        definitions = client.get("/api/v1/workflows", headers=AUTH)
        workflow_name = definitions.json()["items"][0]["name"]
        missing = client.post(
            f"/api/v1/projects/{project_id}/workflows/missing/runs",
            headers={**AUTH, "Idempotency-Key": "fixture-missing"},
            json={},
        )
        accepted = client.post(
            f"/api/v1/projects/{project_id}/workflows/{workflow_name}/runs",
            headers={**AUTH, "Idempotency-Key": "fixture-workflow"},
            json={},
        )
        replay = client.post(
            f"/api/v1/projects/{project_id}/workflows/{workflow_name}/runs",
            headers={**AUTH, "Idempotency-Key": "fixture-workflow"},
            json={},
        )
        fetched = client.get(f"/api/v1/workflow-runs/{run_id}", headers=AUTH)
        steps = client.get(f"/api/v1/workflow-runs/{run_id}/steps", headers=AUTH)
        tasks = client.get(f"/api/v1/workflow-runs/{run_id}/tasks", headers=AUTH)
        paused = client.post(f"/api/v1/workflow-runs/{run_id}/pause", headers=AUTH)
        resumed = client.post(f"/api/v1/workflow-runs/{run_id}/resume", headers=AUTH)
        cancelled = client.post(f"/api/v1/workflow-runs/{run_id}/cancel", headers=AUTH)
        approval = client.get(f"/api/v1/workflow-runs/{run_id}/approval", headers=AUTH)
        decision = client.post(
            f"/api/v1/workflow-runs/{run_id}/approval/decision",
            headers=AUTH,
            json={"decision": "approve", "reason": "fixture-reason"},
        )
        agents = client.get("/api/v1/agents", headers=AUTH)
        agent = client.post(
            f"/api/v1/projects/{project_id}/agents/director/runs",
            headers={**AUTH, "Idempotency-Key": "fixture-agent"},
            json={"goal_reference": "fixture-goal://run"},
        )
        agent_run = client.get(f"/api/v1/agent-runs/{doubles.ids['agent_run']}", headers=AUTH)
        models = client.get("/api/v1/models/status", headers=AUTH)
        tools = client.get("/api/v1/tools/status", headers=AUTH)

    assert definitions.status_code == 200
    assert missing.status_code == 404
    assert accepted.status_code == replay.status_code == 202
    assert accepted.json()["run_id"] == replay.json()["run_id"]
    assert accepted.headers["location"] == f"/api/v1/workflow-runs/{run_id}"
    assert 'rel="monitor"' in accepted.headers["link"]
    assert fetched.headers["etag"] == '"1"'
    assert steps.json()["items"][0]["step_key"] == "fixture-step"
    assert tasks.json()["items"][0]["id"] == str(doubles.ids["task"])
    assert all(item.status_code == 200 for item in (paused, resumed, cancelled, decision))
    assert approval.json()["status"] == "pending"
    assert len(agents.json()["items"]) == 7
    assert agents.json()["items"][0]["budget_limit"]["max_tokens"] == 2048
    assert agent.status_code == 202 and agent_run.status_code == 200
    assert agent_run.json()["model_calls"] == 1
    assert models.json()["protocol_version"] == "models.v1"
    assert {item["provider_id"] for item in models.json()["providers"]} == {
        "fake-model",
        "null-multimodal",
    }
    assert tools.json()["protocol_version"] == "tools.v1"
    assert tools.json()["tools"][0]["configured"] is True


def test_v1_stage17_knowledge_memory_and_creative_resources(
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, _assets, _audit = configured_app(runtime_settings)
    doubles = install_stage17_doubles(app)
    ids = doubles.ids
    project_id = ids["project"]
    memory_body = {
        "memory_type": "fixture",
        "content": "fixture-memory",
        "valid_from": NOW.isoformat(),
        "observed_at": NOW.isoformat(),
        "importance": 0.5,
        "confidence": 0.5,
        "provenance_kind": "fixture",
        "provenance_reference": "fixture-memory://source",
    }
    with TestClient(app) as client:
        ingestion = client.post(
            f"/api/v1/projects/{project_id}/knowledge/ingestion-runs",
            headers={**AUTH, "Idempotency-Key": "fixture-ingestion"},
            json={"asset_id": str(ids["asset"])},
        )
        fetched_ingestion = client.get(
            f"/api/v1/knowledge/ingestion-runs/{ids['ingestion']}", headers=AUTH
        )
        retry = client.post(
            f"/api/v1/knowledge/ingestion-runs/{ids['ingestion']}/retry", headers=AUTH
        )
        document = client.get(
            f"/api/v1/projects/{project_id}/knowledge/documents/{ids['document']}",
            headers=AUTH,
        )
        search = client.post(
            f"/api/v1/projects/{project_id}/knowledge/search",
            headers=AUTH,
            json={"query": "fixture-query"},
        )
        doubles.knowledge.retrieve.return_value = SimpleNamespace(query="fixture-empty", hits=())
        empty_search = client.post(
            f"/api/v1/projects/{project_id}/knowledge/search",
            headers=AUTH,
            json={"query": "fixture-empty"},
        )
        memory = client.post(
            f"/api/v1/projects/{project_id}/memories", headers=AUTH, json=memory_body
        )
        fetched_memory = client.get(
            f"/api/v1/projects/{project_id}/memories/{ids['memory']}", headers=AUTH
        )
        cross_project = client.get(
            f"/api/v1/projects/{uuid4()}/memories/{ids['memory']}", headers=AUTH
        )
        cross_project_revision = client.post(
            f"/api/v1/projects/{uuid4()}/memories/{ids['memory']}/revisions",
            headers=AUTH,
            json={"content": "fixture-next"},
        )
        conflict = client.post(
            f"/api/v1/projects/{project_id}/memories/{ids['memory']}/revisions",
            headers=AUTH,
            json={"content": "fixture-next"},
        )
        fetched_conflict = client.get(
            f"/api/v1/memory-conflicts/{ids['memory_conflict']}", headers=AUTH
        )
        decided_conflict = client.post(
            f"/api/v1/memory-conflicts/{ids['memory_conflict']}/decision",
            headers=AUTH,
            json={"accept_candidate": True},
        )
        package = client.post(
            f"/api/v1/projects/{project_id}/context-packages",
            headers=AUTH,
            json={
                "task_reference": "fixture-task://context",
                "budget_chars": 100,
                "scopes": ["project"],
                "memory_types": ["fixture"],
            },
        )
        fetched_package = client.get(
            f"/api/v1/projects/{project_id}/context-packages/{ids['context_package']}",
            headers=AUTH,
        )
        world = client.post(
            f"/api/v1/projects/{project_id}/creative/worlds",
            headers=AUTH,
            json={"label": "fixture-world"},
        )
        fetched_world = client.get(
            f"/api/v1/projects/{project_id}/creative/worlds/{ids['world']}", headers=AUTH
        )
        character = client.post(
            f"/api/v1/projects/{project_id}/creative/characters",
            headers=AUTH,
            json={"label": "fixture-character"},
        )
        fetched_character = client.get(
            f"/api/v1/projects/{project_id}/creative/characters/{ids['character']}",
            headers=AUTH,
        )
        work = client.post(
            f"/api/v1/projects/{project_id}/creative/works",
            headers=AUTH,
            json={
                "label": "fixture-work",
                "world_ids": [str(ids["world"])],
                "character_ids": [str(ids["character"])],
            },
        )
        fetched_work = client.get(
            f"/api/v1/projects/{project_id}/creative/works/{ids['work']}", headers=AUTH
        )
        draft = client.post(
            f"/api/v1/projects/{project_id}/creative/works/{ids['work']}/drafts",
            headers=AUTH,
            json={"source_reference": "fixture-draft://source", "sequence": 0},
        )
        doubles.creative.novel.get_record.return_value = doubles.creative.world.get.return_value
        wrong_draft = client.get(
            f"/api/v1/projects/{project_id}/creative/drafts/{ids['draft']}", headers=AUTH
        )
        doubles.creative.novel.get_record.return_value = doubles.creative.novel.decide.return_value
        fetched_draft = client.get(
            f"/api/v1/projects/{project_id}/creative/drafts/{ids['draft']}", headers=AUTH
        )
        draft_decision = client.post(
            f"/api/v1/projects/{project_id}/creative/drafts/{ids['draft']}/decision",
            headers={**AUTH, "If-Match": '"1"'},
            json={"decision": "approve"},
        )

    assert ingestion.status_code == retry.status_code == 202
    assert ingestion.json()["workflow_run_id"] == str(ids["workflow_run"])
    assert fetched_ingestion.status_code == document.status_code == 200
    assert search.json()["hits"][0]["citation"]["document_id"] == str(ids["document"])
    assert empty_search.json()["hits"] == []
    assert (
        memory.status_code == 201
        and fetched_memory.status_code == 200
        and fetched_memory.json()["provenance"]
        == {"kind": "fixture", "reference": "fixture-memory://source"}
    )
    assert cross_project.status_code == cross_project_revision.status_code == 404
    assert conflict.status_code == 201
    assert fetched_conflict.status_code == decided_conflict.status_code == 200
    assert package.status_code == 201 and fetched_package.json()["used_tokens"] == 4
    assert (
        world.status_code == character.status_code == work.status_code == draft.status_code == 201
    )
    assert fetched_world.json()["owner"] == "world"
    assert fetched_character.json()["owner"] == "character"
    assert wrong_draft.status_code == 404
    assert fetched_work.json()["owner"] == fetched_draft.json()["owner"] == "novel"
    assert draft_decision.headers["etag"] == '"2"'


def test_v1_stage17_consistency_quality_feedback_and_evolution(  # noqa: PLR0915
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, _assets, _audit = configured_app(runtime_settings)
    ids = install_stage17_doubles(app).ids
    project_id = ids["project"]
    match = {**AUTH, "If-Match": '"1"'}
    with TestClient(app) as client:
        check = client.post(
            f"/api/v1/projects/{project_id}/consistency/checks",
            headers=AUTH,
            json={
                "required_fields": [
                    {
                        "evidence_reference": "fixture-evidence://required",
                        "field_code": "fixture-field",
                        "present": False,
                    }
                ],
                "references": [
                    {"evidence_reference": "fixture-evidence://reference", "exists": False}
                ],
                "versions": [
                    {
                        "evidence_reference": "fixture-evidence://version",
                        "expected_version": 2,
                        "current_version": 1,
                    }
                ],
                "canon_changes": [
                    {
                        "canon_reference": "fixture-canon://record",
                        "level": "level_1",
                        "modifies_current": True,
                        "explicitly_authorized": False,
                    }
                ],
                "workflow_run_id": str(ids["workflow_run"]),
            },
        )
        fetched_check = client.get(
            f"/api/v1/projects/{project_id}/consistency/checks/{ids['check']}", headers=AUTH
        )
        resolution = client.post(
            f"/api/v1/projects/{project_id}/consistency/resolutions",
            headers=AUTH,
            json={
                "finding_ids": [str(ids["finding"])],
                "strategy_code": "fixture-strategy",
                "target_reference": "fixture-target://record",
                "target_expected_version": 1,
                "impact_references": ["fixture-impact://record"],
                "workflow_run_id": str(ids["workflow_run"]),
            },
        )
        fetched_resolution = client.get(
            f"/api/v1/projects/{project_id}/consistency/resolutions/{ids['resolution']}",
            headers=AUTH,
        )
        resolution_decision = client.post(
            f"/api/v1/projects/{project_id}/consistency/resolutions/{ids['resolution']}/decision",
            headers=match,
            json={"decision": "approve"},
        )
        rubric = client.post(
            f"/api/v1/projects/{project_id}/quality/rubrics",
            headers=AUTH,
            json={
                "rubric_key": "fixture-rubric",
                "version": 1,
                "schema_version": "quality.v1",
                "dimension_keys": ["fixture-dimension"],
            },
        )
        evaluation = client.post(
            f"/api/v1/projects/{project_id}/quality/evaluations",
            headers=AUTH,
            json={
                "rubric_id": str(ids["rubric"]),
                "input_reference": "fixture-quality://input",
                "workflow_run_id": str(ids["workflow_run"]),
            },
        )
        executed = client.post(
            f"/api/v1/projects/{project_id}/quality/evaluations/{ids['evaluation']}/execute",
            headers=AUTH,
            json={
                "input_reference": "fixture-quality://input",
                "consistency_status": "passed",
            },
        )
        fetched_evaluation = client.get(
            f"/api/v1/projects/{project_id}/quality/evaluations/{ids['evaluation']}",
            headers=AUTH,
        )
        feedback = client.post(
            f"/api/v1/projects/{project_id}/feedback",
            headers=AUTH,
            json={
                "source": "user",
                "schema_version": "feedback.v1",
                "signal_code": "fixture-signal",
                "numeric_value": 1.0,
                "source_reference": "fixture-feedback://source",
            },
        )
        fetched_feedback = client.get(
            f"/api/v1/projects/{project_id}/feedback/{ids['feedback']}", headers=AUTH
        )
        consent_status = client.get(
            f"/api/v1/projects/{project_id}/feedback/behavior-consent", headers=AUTH
        )
        granted_consent = client.post(
            f"/api/v1/projects/{project_id}/feedback/behavior-consent",
            headers=AUTH,
            json={},
        )
        withdrawn_consent = client.delete(
            f"/api/v1/projects/{project_id}/feedback/behavior-consent", headers=AUTH
        )
        metric = client.post(
            f"/api/v1/projects/{project_id}/metrics",
            headers=AUTH,
            json={
                "name": "fixture.metric",
                "version": 1,
                "unit": "count",
                "dimensions": [{"key": "status", "allowed_values": ["ok"]}],
                "retention_days": 7,
                "sensitivity": "internal",
            },
        )
        point = client.post(
            f"/api/v1/projects/{project_id}/metric-points",
            headers=AUTH,
            json={
                "name": "fixture.metric",
                "value": 1.0,
                "dimensions": {"status": "ok"},
                "source_reference": "fixture-metric://source",
                "source_feedback_event_id": str(ids["feedback"]),
            },
        )
        fetched_point = client.get(
            f"/api/v1/projects/{project_id}/metric-points/{ids['metric_point']}",
            headers=AUTH,
        )
        diagnostics = client.post(
            f"/api/v1/projects/{project_id}/metric-points/{ids['metric_point']}/diagnostics",
            headers=AUTH,
        )
        diagnostic = client.get(
            f"/api/v1/projects/{project_id}/diagnostics/{ids['diagnostic']}", headers=AUTH
        )
        experiment = client.post(
            f"/api/v1/projects/{project_id}/experiments",
            headers=AUTH,
            json={
                "experiment_key": "fixture-experiment",
                "protocol_version": "protocol-v1",
                "hypothesis_code": "fixture-hypothesis",
                "primary_metric_name": "fixture.metric",
                "starts_at": NOW.isoformat(),
                "ends_at": (NOW + timedelta(hours=1)).isoformat(),
                "stop_condition_codes": ["fixture-stop"],
                "variants": [
                    {
                        "variant_key": "control",
                        "configuration_reference": "fixture-config://control",
                    },
                    {
                        "variant_key": "candidate",
                        "configuration_reference": "fixture-config://candidate",
                    },
                ],
            },
        )
        fetched_experiment = client.get(
            f"/api/v1/projects/{project_id}/experiments/{ids['experiment']}",
            headers=AUTH,
        )
        started_experiment = client.post(
            f"/api/v1/projects/{project_id}/experiments/{ids['experiment']}/start",
            headers=AUTH,
        )
        experiment_sample = client.post(
            f"/api/v1/projects/{project_id}/experiments/{ids['experiment']}/samples",
            headers=AUTH,
            json={
                "variant_id": str(ids["variant"]),
                "metric_point_id": str(ids["metric_point"]),
            },
        )
        finished_experiment = client.post(
            f"/api/v1/projects/{project_id}/experiments/{ids['experiment']}/finish",
            headers=AUTH,
            json={"status": "completed", "result_code": "fixture-result"},
        )
        proposal = client.post(
            f"/api/v1/projects/{project_id}/diagnostics/{ids['diagnostic']}/improvement-proposals",
            headers=AUTH,
        )
        fetched_proposal = client.get(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}",
            headers=AUTH,
        )
        planned = client.post(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}/plan",
            headers=match,
            json={
                "action": "suggest-configuration",
                "change_reference": "fixture-change://proposal",
                "rollback_reference": "fixture-rollback://proposal",
            },
        )
        simulated = client.post(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}/simulate",
            headers=match,
        )
        evaluated = client.post(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}/evaluate",
            headers=match,
        )
        approval = client.post(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}/request-approval",
            headers=match,
        )
        decided = client.post(
            f"/api/v1/projects/{project_id}/improvement-proposals/{ids['proposal']}/decision",
            headers=match,
            json={"decision": "approve"},
        )

    assert check.status_code == 201 and len(check.json()["findings"]) == 1
    assert len(fetched_check.json()["findings"]) == 1
    assert resolution.status_code == 201 and fetched_resolution.status_code == 200
    assert resolution_decision.headers["etag"] == '"1"'
    assert rubric.status_code == evaluation.status_code == 201
    assert executed.json()["dimensions"][0]["status"] == "passed"
    assert fetched_evaluation.status_code == 200
    assert feedback.status_code == 201 and fetched_feedback.status_code == 200
    assert consent_status.json()["active"] is True
    assert granted_consent.status_code == 201
    assert withdrawn_consent.json()["tombstone_count"] == 1
    assert metric.status_code == point.status_code == diagnostics.status_code == 201
    assert fetched_point.json()["included"] is True
    assert diagnostic.status_code == 200
    assert experiment.status_code == experiment_sample.status_code == 201
    assert all(
        item.status_code == 200
        for item in (fetched_experiment, started_experiment, finished_experiment)
    )
    assert len(fetched_experiment.json()["variants"]) == 2
    assert proposal.status_code == 201 and fetched_proposal.status_code == 200
    assert all(
        item.status_code == 200 for item in (planned, simulated, evaluated, approval, decided)
    )
    assert decided.headers["etag"] == '"1"'


def test_v1_stage17_sse_cursor_recovery_and_projection(
    runtime_settings: RuntimeSettings,
) -> None:
    app, _projects, _assets, _audit = configured_app(runtime_settings)
    doubles = install_stage17_doubles(app)
    run_id = doubles.ids["workflow_run"]
    event = doubles.workflow.get_events.return_value[0]
    with TestClient(app) as client:
        malformed = client.get(
            f"/api/v1/events?run_id={run_id}",
            headers={**AUTH, "Last-Event-ID": "bad"},
        )
        wrong_run = client.get(
            f"/api/v1/events?run_id={run_id}",
            headers={**AUTH, "Last-Event-ID": f"{uuid4()}:1"},
        )
        negative = client.get(
            f"/api/v1/events?run_id={run_id}",
            headers={**AUTH, "Last-Event-ID": f"{run_id}:-1"},
        )
        doubles.workflow.get_events.return_value = (
            SimpleNamespace(**{**vars(event), "sequence": 3}),
        )
        expired = client.get(
            f"/api/v1/events?run_id={run_id}",
            headers={**AUTH, "Last-Event-ID": f"{run_id}:1"},
        )
        doubles.workflow.get_events.side_effect = ((), (event,))
        ahead = client.get(
            f"/api/v1/events?run_id={run_id}",
            headers={**AUTH, "Last-Event-ID": f"{run_id}:9"},
        )

    assert malformed.status_code == wrong_run.status_code == negative.status_code == 400
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "event_cursor_expired"
    assert expired.json()["error"]["details"]["recovery"] == "refetch_status"
    assert ahead.status_code == 400

    async def scenario() -> None:
        request = cast("Request", SimpleNamespace(is_disconnected=AsyncMock(return_value=True)))
        context = SecurityContext(
            ACTOR_ID,
            ActorKind.USER,
            WORKSPACE_ID,
            permissions_for(Role.OWNER),
            POLICY_VERSION,
            CorrelationIds(str(ACTOR_ID), str(OTHER_ACTOR_ID)),
        )
        service = cast("WorkflowService", SimpleNamespace(get_events=AsyncMock(return_value=())))
        run = cast("WorkflowRun", doubles.workflow.get.return_value)
        initial = cast("tuple[WorkflowRunEvent, ...]", (event,))
        telemetry = TelemetryRuntime()
        chunks = [
            chunk
            async for chunk in stage17_router._event_stream(  # noqa: SLF001
                request,
                context,
                service,
                run,
                initial,
                0,
                poll_seconds=0,
                telemetry=telemetry,
            )
        ]
        assert chunks[0] == "retry: 3000\n\n"
        assert f"id: {run_id}:1" in chunks[1]
        assert '"schema_version":1' in chunks[1]
        assert "accos_sse_connections 0" in telemetry.registry.render_prometheus()
        assert stage17_router._parse_event_cursor(None, run_id) == 0  # noqa: SLF001
        assert stage17_router._parse_event_cursor(f"{run_id}:1", run_id) == 1  # noqa: SLF001

        gap = SimpleNamespace(**{**vars(event), "sequence": 3})
        reconnect_request = cast(
            "Request", SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        )
        reconnect_service = cast(
            "WorkflowService", SimpleNamespace(get_events=AsyncMock(return_value=(gap,)))
        )
        reconnect = [
            chunk
            async for chunk in stage17_router._event_stream(  # noqa: SLF001
                reconnect_request, context, reconnect_service, run, (), 1, poll_seconds=0
            )
        ]
        assert reconnect[1].startswith(": heartbeat")
        assert "event: stream.reset" in reconnect[2]

        container = cast("ApplicationContainer", app.state.container)
        doubles.workflow.get_events.side_effect = None
        doubles.workflow.get_events.return_value = (event,)
        response = await stage17_router.stream_workflow_events(
            request, run_id, context, container, f"{run_id}:0"
        )
        assert response.media_type == "text/event-stream"
        doubles.workflow.get_events.side_effect = ((), (event,))
        resumed_response = await stage17_router.stream_workflow_events(
            request, run_id, context, container, f"{run_id}:1"
        )
        assert resumed_response.headers["x-accel-buffering"] == "no"

    asyncio.run(scenario())
