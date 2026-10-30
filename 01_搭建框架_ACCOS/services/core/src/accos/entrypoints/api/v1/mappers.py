"""Explicit domain-to-DTO mappings for the public v1 boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accos.entrypoints.api.v1.dependencies import encode_cursor
from accos.entrypoints.api.v1.schemas import (
    ArtifactResponse,
    AssetResponse,
    AssetVersionResponse,
    MembershipResponse,
    PageMetadata,
    ProjectResponse,
    ProjectSettingsDto,
    RevisionResponse,
    WorkspaceResponse,
)

if TYPE_CHECKING:
    from accos.kernel.persistence import Page
    from accos.modules.assets.domain import Asset, AssetVersion
    from accos.modules.identity.domain import Membership, Workspace
    from accos.modules.projects.domain import Artifact, ArtifactRevision, Project


def workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        owner_user_id=workspace.owner_user_id,
        archived=workspace.archived,
    )


def membership_response(membership: Membership) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        role=membership.role.value,
        active=membership.active,
    )


def project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        status=project.status,
        settings=ProjectSettingsDto(
            revision_retention_limit=project.settings.revision_retention_limit,
            asset_retention_days=project.settings.asset_retention_days,
        ),
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
        version=project.version,
    )


def artifact_response(artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id,
        workspace_id=artifact.workspace_id,
        project_id=artifact.project_id,
        artifact_type=artifact.artifact_type,
        label=artifact.label,
        created_by=artifact.created_by,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        current_revision=artifact.current_revision,
        version=artifact.version,
    )


def revision_response(revision: ArtifactRevision) -> RevisionResponse:
    return RevisionResponse(
        id=revision.id,
        workspace_id=revision.workspace_id,
        project_id=revision.project_id,
        artifact_id=revision.artifact_id,
        revision_number=revision.revision_number,
        content_reference=revision.content_reference,
        content_hash=revision.content_hash,
        created_by=revision.created_by,
        created_at=revision.created_at,
    )


def asset_response(
    asset: Asset, version: AssetVersion, *, duplicate: bool | None = None
) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        workspace_id=asset.workspace_id,
        project_id=asset.project_id,
        owner_id=asset.owner_id,
        filename=asset.filename,
        source=asset.source,
        status=asset.status,
        current_version=asset.current_version,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        deletion_marked_at=asset.deletion_marked_at,
        retention_until=asset.retention_until,
        version=asset.version,
        current=AssetVersionResponse(
            id=version.id,
            version_number=version.version_number,
            content_hash=version.content_hash,
            media_type=version.media_type,
            size_bytes=version.size_bytes,
            scan_status=version.scan_status.value,
            processing_status=version.processing_status.value,
            created_by=version.created_by,
            created_at=version.created_at,
        ),
        duplicate=duplicate,
    )


def page_metadata[ItemT](page: Page[ItemT]) -> PageMetadata:
    return PageMetadata(
        total=page.total,
        limit=page.request.limit,
        next_cursor=(None if page.next_offset is None else encode_cursor(page.next_offset)),
    )
