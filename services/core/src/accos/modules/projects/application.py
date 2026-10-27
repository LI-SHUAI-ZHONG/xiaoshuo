"""Authorized project and artifact application use cases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import uuid4

from accos.kernel.contracts import IdempotencyKey
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.modules.identity.public import (
    AuthorizationRequest,
    Permission,
    ResourceScope,
)
from accos.modules.projects.domain import (
    Artifact,
    ArtifactRevision,
    ArtifactSort,
    ArtifactType,
    Project,
    ProjectSettings,
    ProjectSort,
    ProjectStatus,
)

if TYPE_CHECKING:
    from datetime import datetime
    from typing import NoReturn
    from uuid import UUID

    from accos.kernel.clock import Clock
    from accos.kernel.contracts import PageRequest
    from accos.kernel.persistence import Page
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.projects.ports import ProjectRepository


class ProjectService:
    """Coordinate scoped authorization, project state, and persistence."""

    def __init__(
        self,
        repository: ProjectRepository,
        authorizer: AuthorizationService,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._authorizer = authorizer
        self._clock = clock

    async def create(
        self,
        context: SecurityContext,
        *,
        name: str,
        settings: ProjectSettings,
        idempotency_key: str,
    ) -> Project:
        """Create exactly one empty project for a scoped idempotency key."""
        key = IdempotencyKey(idempotency_key)
        normalized_name = _validated_label(name, "project name")
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.PROJECT_WRITE,
                ResourceScope(context.workspace_id, "workspace", str(context.workspace_id)),
            )
        )
        now = self._clock.now()
        project = Project(
            uuid4(),
            context.workspace_id,
            normalized_name,
            ProjectStatus.ACTIVE,
            settings,
            context.actor_id,
            now,
            now,
        )
        digest = hashlib.sha256(
            json.dumps(
                {
                    "name": normalized_name,
                    "revision_retention_limit": settings.revision_retention_limit,
                    "asset_retention_days": settings.asset_retention_days,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        stored, _created = await self._repository.create_idempotent(
            project,
            idempotency_key=key.value,
            request_digest=digest,
            event=_event(
                context,
                project.id,
                project.id,
                "projects.project-created",
                now,
                {"schema": "project-created.v1", "status": project.status.value},
            ),
        )
        return stored

    async def get(self, context: SecurityContext, project_id: UUID) -> Project:
        """Read a project without revealing cross-workspace existence."""
        project = await self._repository.get(context.workspace_id, project_id)
        if project is None:
            await self._reject_unavailable(context, project_id)
        await self._authorize(context, project, Permission.PROJECT_READ)
        return project

    async def list(
        self,
        context: SecurityContext,
        page: PageRequest,
        *,
        status: ProjectStatus | None,
        sort: ProjectSort,
    ) -> Page[Project]:
        """List a stable page inside the authenticated workspace."""
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.PROJECT_READ,
                ResourceScope(context.workspace_id, "workspace", str(context.workspace_id)),
            )
        )
        return await self._repository.list_projects(
            context.workspace_id,
            page,
            status=status,
            sort=sort,
            hidden_ids=await self._authorizer.hidden_projects(context),
        )

    async def update_settings(
        self,
        context: SecurityContext,
        project_id: UUID,
        settings: ProjectSettings,
        *,
        expected_version: int,
    ) -> Project:
        """Update settings only when the caller holds the current version."""
        project = await self._require_writable(context, project_id)
        if expected_version != project.version:
            raise ConcurrencyConflictError(project.version)
        now = self._clock.now()
        return await self._repository.update_settings(
            context.workspace_id,
            project_id,
            settings,
            expected_version=expected_version,
            event=_event(
                context,
                project_id,
                project_id,
                "projects.project-settings-updated",
                now,
                {"schema": "project-settings-updated.v1"},
            ),
        )

    async def archive(
        self,
        context: SecurityContext,
        project_id: UUID,
        *,
        expected_version: int,
    ) -> Project:
        """Mark a project archived; no child data is physically removed."""
        project = await self._repository.get(context.workspace_id, project_id)
        if project is None:
            await self._reject_unavailable(context, project_id)
        await self._authorize(context, project, Permission.DATA_ARCHIVE)
        if project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot be changed.")
        if expected_version != project.version:
            raise ConcurrencyConflictError(project.version)
        now = self._clock.now()
        return await self._repository.archive(
            context.workspace_id,
            project_id,
            expected_version=expected_version,
            event=_event(
                context,
                project_id,
                project_id,
                "projects.project-archived",
                now,
                {"schema": "project-archived.v1"},
            ),
        )

    async def create_artifact(
        self,
        context: SecurityContext,
        project_id: UUID,
        *,
        artifact_type: ArtifactType,
        label: str,
    ) -> Artifact:
        """Create an empty versioned container in an active project."""
        await self._require_writable(context, project_id)
        now = self._clock.now()
        artifact = Artifact(
            uuid4(),
            context.workspace_id,
            project_id,
            artifact_type,
            _validated_label(label, "artifact label"),
            context.actor_id,
            now,
            now,
        )
        await self._repository.add_artifact(
            artifact,
            _event(
                context,
                project_id,
                artifact.id,
                "projects.artifact-created",
                now,
                {"schema": "artifact-created.v1", "artifact_type": artifact_type.value},
            ),
        )
        return artifact

    async def get_artifact(
        self, context: SecurityContext, project_id: UUID, artifact_id: UUID
    ) -> Artifact:
        """Read an artifact through its owning project scope."""
        project = await self.get(context, project_id)
        artifact = await self._repository.get_artifact(
            context.workspace_id, project.id, artifact_id
        )
        if artifact is None:
            await self._authorizer.reject(
                AuthorizationRequest(
                    context,
                    Permission.PROJECT_READ,
                    ResourceScope(context.workspace_id, "artifact", str(artifact_id), project_id),
                ),
                ScopeViolationError(),
                reason_code="artifact_unavailable",
            )
        return artifact

    async def list_artifacts(
        self,
        context: SecurityContext,
        project_id: UUID,
        page: PageRequest,
        *,
        sort: ArtifactSort,
    ) -> Page[Artifact]:
        """List artifact containers without loading content."""
        project = await self.get(context, project_id)
        return await self._repository.list_artifacts(
            context.workspace_id, project.id, page, sort=sort
        )

    async def list_revisions(
        self,
        context: SecurityContext,
        project_id: UUID,
        artifact_id: UUID,
        page: PageRequest,
    ) -> Page[ArtifactRevision]:
        """List immutable revision metadata after artifact authorization."""
        await self.get_artifact(context, project_id, artifact_id)
        return await self._repository.list_revisions(
            context.workspace_id, project_id, artifact_id, page
        )

    async def add_artifact_revision(  # noqa: PLR0913
        self,
        context: SecurityContext,
        project_id: UUID,
        artifact_id: UUID,
        *,
        content_reference: str | None = None,
        content_hash: str | None = None,
        expected_version: int,
    ) -> ArtifactRevision:
        """Append immutable revision metadata; creative content remains outside this module."""
        await self._require_writable(context, project_id)
        artifact = await self._repository.get_artifact(
            context.workspace_id, project_id, artifact_id
        )
        if artifact is None:
            await self._authorizer.reject(
                AuthorizationRequest(
                    context,
                    Permission.PROJECT_WRITE,
                    ResourceScope(context.workspace_id, "artifact", str(artifact_id), project_id),
                ),
                ScopeViolationError(),
                reason_code="artifact_unavailable",
            )
        if expected_version != artifact.version:
            raise ConcurrencyConflictError(artifact.version)
        if (content_reference is None) != (content_hash is None):
            raise ValueError("content reference and hash must be provided together")
        now = self._clock.now()
        revision = ArtifactRevision(
            uuid4(),
            context.workspace_id,
            project_id,
            artifact_id,
            artifact.current_revision + 1,
            content_reference,
            content_hash,
            context.actor_id,
            now,
        )
        updated = replace(
            artifact,
            current_revision=revision.revision_number,
            updated_at=now,
            version=artifact.version + 1,
        )
        _stored_artifact, stored_revision = await self._repository.add_revision(
            updated,
            revision,
            expected_version=expected_version,
            event=_event(
                context,
                project_id,
                artifact_id,
                "projects.artifact-revision-created",
                now,
                {
                    "schema": "artifact-revision-created.v1",
                    "artifact_type": artifact.artifact_type.value,
                    "revision_number": revision.revision_number,
                },
            ),
        )
        return stored_revision

    async def _require_writable(self, context: SecurityContext, project_id: UUID) -> Project:
        project = await self._repository.get(context.workspace_id, project_id)
        if project is None:
            await self._reject_unavailable(context, project_id)
        await self._authorize(context, project, Permission.PROJECT_WRITE)
        if project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot be changed.")
        return project

    async def require_writable(self, context: SecurityContext, project_id: UUID) -> Project:
        """Public authorization boundary shared by content commands."""
        return await self._require_writable(context, project_id)

    async def catalog(
        self, context: SecurityContext, query: str, archived: bool, cursor: str | None, limit: int
    ) -> tuple[tuple[Project, ...], str | None]:
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.PROJECT_READ,
                ResourceScope(context.workspace_id, "workspace", str(context.workspace_id)),
            )
        )
        return await self._repository.catalog(
            context.workspace_id,
            query,
            archived,
            cursor,
            limit,
            await self._authorizer.hidden_projects(context),
        )

    async def revise_project(
        self,
        context: SecurityContext,
        project_id: UUID,
        name: str,
        archived: bool,
        expected_version: int,
    ) -> Project:
        project = await self.get(context, project_id)
        await self._authorize(context, project, Permission.PROJECT_WRITE)
        if archived or project.status is ProjectStatus.ARCHIVED:
            await self._authorize(context, project, Permission.DATA_ARCHIVE)
        now = self._clock.now()
        return await self._repository.revise_project(
            context.workspace_id,
            project_id,
            name=_validated_label(name, "project name"),
            archived=archived,
            expected_version=expected_version,
            event=_event(
                context,
                project_id,
                project_id,
                "projects.project-updated",
                now,
                {"schema": "project-updated.v1", "archived": archived},
            ),
        )

    async def _authorize(
        self, context: SecurityContext, project: Project, permission: Permission
    ) -> None:
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                permission,
                ResourceScope(project.workspace_id, "project", str(project.id), project.id),
            )
        )

    async def _reject_unavailable(self, context: SecurityContext, project_id: UUID) -> NoReturn:
        await self._authorizer.reject(
            AuthorizationRequest(
                context,
                Permission.PROJECT_READ,
                ResourceScope(context.workspace_id, "project", str(project_id), project_id),
            ),
            ScopeViolationError(),
            reason_code="project_unavailable",
        )


def _validated_label(value: str, field: str) -> str:
    max_label_length = 200
    if not value or value.strip() != value or len(value) > max_label_length:
        raise ValueError(f"{field} must be non-empty, trimmed, and at most 200 characters")
    return value


def _event(  # noqa: PLR0913, PLR0917
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
