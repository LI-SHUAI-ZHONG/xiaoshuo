"""Searchable keyset libraries and exact-version authorized downloads."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Query, Response
from pydantic import Field

from accos.entrypoints.api.v1.content_router import Container, Context, Cursor, Limit, Version
from accos.entrypoints.api.v1.content_router import router as router
from accos.entrypoints.api.v1.mappers import asset_response, project_response
from accos.entrypoints.api.v1.schemas import (
    ApiModel,
    AssetResponse,
    AssetVersionResponse,
    ProjectResponse,
)
from accos.kernel.errors import InvalidRequestError, ScopeViolationError
from accos.kernel.shared_contracts import ContentRef


class ProjectCatalog(ApiModel):
    items: tuple[ProjectResponse, ...]
    next_cursor: str | None


class AssetCatalog(ApiModel):
    items: tuple[AssetResponse, ...]
    next_cursor: str | None


class AssetHistory(ApiModel):
    items: tuple[AssetVersionResponse, ...]
    next_cursor: str | None


class ProjectEdit(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    archived: bool


class DownloadTicket(ApiModel):
    url: str
    expires_in: int = 300


@router.get("/workspaces/{workspace_id}/projects/page", response_model=ProjectCatalog)
async def project_catalog(
    workspace_id: UUID,
    context: Context,
    container: Container,
    query: Annotated[str, Query(max_length=200)] = "",
    archived: bool = False,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> ProjectCatalog:
    if workspace_id != context.workspace_id:
        raise ScopeViolationError()
    items, next_cursor = await container.projects.service.catalog(
        context, query, archived, cursor, limit
    )
    return ProjectCatalog(
        items=tuple(project_response(item) for item in items), next_cursor=next_cursor
    )


@router.put("/projects/{project_id}/details", response_model=ProjectResponse)
async def update_project(
    project_id: UUID, body: ProjectEdit, context: Context, container: Container, expected: Version
) -> ProjectResponse:
    return project_response(
        await container.projects.service.revise_project(
            context, project_id, body.name, body.archived, expected
        )
    )


@router.get("/projects/{project_id}/assets/page", response_model=AssetCatalog)
async def asset_catalog(
    project_id: UUID,
    context: Context,
    container: Container,
    query: Annotated[str, Query(max_length=200)] = "",
    cursor: Cursor = None,
    limit: Limit = 20,
) -> AssetCatalog:
    items, next_cursor = await container.assets.service.catalog(
        context, project_id, query, cursor, limit
    )
    return AssetCatalog(
        items=tuple(asset_response(a, v) for a, v in items), next_cursor=next_cursor
    )


@router.get("/projects/{project_id}/assets/{asset_id}/versions", response_model=AssetHistory)
async def asset_history(
    project_id: UUID,
    asset_id: UUID,
    context: Context,
    container: Container,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> AssetHistory:
    try:
        before = int(cursor) if cursor is not None else None
        if before is not None and before < 1:
            raise ValueError
    except ValueError:
        raise InvalidRequestError("Invalid asset version cursor.") from None
    values = await container.assets.service.versions(
        context, project_id, asset_id, before, limit + 1
    )
    return AssetHistory(
        items=tuple(AssetVersionResponse.model_validate(v) for v in values[:limit]),
        next_cursor=str(values[limit - 1].version_number) if len(values) > limit else None,
    )


@router.post(
    "/projects/{project_id}/assets/{asset_id}/versions/{version_id}/download-ticket",
    response_model=DownloadTicket,
)
async def download_ticket(
    project_id: UUID, asset_id: UUID, version_id: UUID, context: Context, container: Container
) -> DownloadTicket:
    await container.assets.service.version(context, project_id, asset_id, version_id)
    ticket = container.assets.downloads.issue(context, project_id, asset_id, version_id)
    return DownloadTicket(
        url=f"/api/v1/projects/{project_id}/assets/{asset_id}/versions/{version_id}/content?ticket={ticket}"
    )


@router.get(
    "/projects/{project_id}/assets/{asset_id}/versions/{version_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def download_version(
    project_id: UUID,
    asset_id: UUID,
    version_id: UUID,
    context: Context,
    container: Container,
    ticket: Annotated[str | None, Query(max_length=2048)] = None,
) -> Response:
    if ticket is not None:
        container.assets.downloads.verify(ticket, context, project_id, asset_id, version_id)
    version = await container.assets.service.version(context, project_id, asset_id, version_id)
    ref = ContentRef(
        asset_id=asset_id,
        asset_version_id=version_id,
        sha256=version.content_hash,
        media_type=version.media_type,
        byte_length=version.size_bytes,
    )
    data = await container.assets.service.read_snapshot(context, project_id, ref)
    return Response(
        data,
        media_type=version.media_type,
        headers={
            "ETag": f'"sha256:{version.content_hash}"',
            "Cache-Control": "private, no-store",
            "Content-Disposition": 'attachment; filename="asset-download"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
