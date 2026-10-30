"""Persistence ports owned by the projects module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope
    from accos.kernel.persistence import Page
    from accos.modules.projects.domain import (
        Artifact,
        ArtifactRevision,
        ArtifactSort,
        Project,
        ProjectSettings,
        ProjectSort,
        ProjectStatus,
    )


class ProjectRepository(Protocol):
    """Workspace-scoped project and artifact persistence boundary."""

    async def catalog(
        self,
        workspace_id: UUID,
        query: str,
        archived: bool,
        cursor: str | None,
        limit: int,
        hidden_ids: frozenset[UUID],
    ) -> tuple[tuple[Project, ...], str | None]: ...

    async def revise_project(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        name: str,
        archived: bool,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project: ...

    async def create_idempotent(
        self,
        project: Project,
        *,
        idempotency_key: str,
        request_digest: str,
        event: EventEnvelope,
    ) -> tuple[Project, bool]:
        """Atomically create a project, idempotency record, and Outbox event."""
        ...

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        """Get a project only within the supplied workspace."""
        ...

    async def list_projects(
        self,
        workspace_id: UUID,
        page: PageRequest,
        *,
        status: ProjectStatus | None,
        sort: ProjectSort,
        hidden_ids: frozenset[UUID] = frozenset(),
    ) -> Page[Project]:
        """List projects using one workspace predicate and stable ordering."""
        ...

    async def update_settings(
        self,
        workspace_id: UUID,
        project_id: UUID,
        settings: ProjectSettings,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        """Apply an optimistic update and atomically append its event."""
        ...

    async def archive(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        """Soft-archive a project without deleting owned records."""
        ...

    async def add_artifact(self, artifact: Artifact, event: EventEnvelope) -> None:
        """Persist an empty artifact container and its Outbox event atomically."""
        ...

    async def get_artifact(
        self, workspace_id: UUID, project_id: UUID, artifact_id: UUID
    ) -> Artifact | None:
        """Get an artifact through both workspace and project scope."""
        ...

    async def list_artifacts(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        sort: ArtifactSort,
    ) -> Page[Artifact]:
        """List artifacts through both owning scopes."""
        ...

    async def list_revisions(
        self,
        workspace_id: UUID,
        project_id: UUID,
        artifact_id: UUID,
        page: PageRequest,
    ) -> Page[ArtifactRevision]:
        """List immutable revisions newest first through all ownership scopes."""
        ...

    async def add_revision(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> tuple[Artifact, ArtifactRevision]:
        """Append an immutable revision and advance the container atomically."""
        ...
