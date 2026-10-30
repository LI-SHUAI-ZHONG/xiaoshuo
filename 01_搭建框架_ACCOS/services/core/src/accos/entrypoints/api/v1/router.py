"""Authenticated version-one REST resources backed only by application use cases."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, Security, status
from fastapi.security import APIKeyCookie, HTTPBearer

from accos.composition import ApplicationContainer
from accos.entrypoints.api.v1.dependencies import (
    ApiPageRequest,
    api_context,
    application_container,
    enforce_rate_limit,
    etag,
    idempotency_key,
    if_match_version,
    pagination,
    require_selected_workspace,
)
from accos.entrypoints.api.v1.mappers import (
    artifact_response,
    asset_response,
    membership_response,
    page_metadata,
    project_response,
    revision_response,
    workspace_response,
)
from accos.entrypoints.api.v1.schemas import (
    ArtifactCollectionResponse,
    ArtifactCreateRequest,
    ArtifactResponse,
    AssetCollectionResponse,
    AssetResponse,
    AssetUploadRequest,
    ExtensionCapabilityStatusResponse,
    ExtensionConfigurationFieldResponse,
    ExtensionStatusCollectionResponse,
    FeatureFlagStatusResponse,
    IdentityMeResponse,
    MembershipCollectionResponse,
    ProjectCollectionResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    RevisionCollectionResponse,
    RevisionCreateRequest,
    RevisionResponse,
    RuntimeBoundaryStatusResponse,
    SystemHealthResponse,
    SystemObservabilityResponse,
    SystemSettingsResponse,
    WorkspaceCollectionResponse,
    WorkspaceResponse,
)
from accos.entrypoints.api.v1.stage17_router import router as stage17_router
from accos.kernel.errors import ConcurrencyConflictError, ErrorEnvelope
from accos.kernel.persistence import Page
from accos.kernel.security import SecurityContext
from accos.modules.assets.domain import AssetSort, AssetStatus
from accos.modules.identity.application import (
    AuthorizationRequest,
    IdentityQueryService,
    ResourceScope,
)
from accos.modules.identity.domain import Permission
from accos.modules.projects.domain import (
    ArtifactSort,
    ProjectSettings,
    ProjectSort,
    ProjectStatus,
)

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorEnvelope, "description": description}
    for code, description in {
        400: "Invalid request",
        401: "Authentication required",
        403: "Permission or scope denied",
        404: "Resource not found",
        409: "State, version, or idempotency conflict",
        415: "Unsupported media type",
        422: "Schema validation failed",
        428: "If-Match precondition required",
        429: "Request rate limit exceeded",
        500: "Safe internal error",
        503: "Dependency unavailable",
    }.items()
}
_bearer = HTTPBearer(auto_error=False)
_cookie = APIKeyCookie(name="accos_session", auto_error=False)

router = APIRouter(
    prefix="/api/v1",
    responses=_ERROR_RESPONSES,
    dependencies=[Security(_bearer), Security(_cookie), Depends(enforce_rate_limit)],
)

Context = Annotated[SecurityContext, Depends(api_context)]
Container = Annotated[ApplicationContainer, Depends(application_container)]
PageDependency = Annotated[ApiPageRequest, Depends(pagination)]
SelectedWorkspace = Annotated[UUID, Depends(require_selected_workspace)]
Idempotency = Annotated[str, Depends(idempotency_key)]
ExpectedVersion = Annotated[int, Depends(if_match_version)]


@router.get("/identity/me", response_model=IdentityMeResponse, operation_id="getIdentityMe")
async def identity_me(context: Context, container: Container) -> IdentityMeResponse:
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "workspace", str(context.workspace_id)),
        )
    )
    return IdentityMeResponse(
        actor_id=context.actor_id,
        actor_kind=context.actor_kind.value,
        auth_method=context.auth_method,
        workspace_id=context.workspace_id,
        permissions=sorted(context.permissions),
        policy_version=context.policy_version,
    )


@router.get(
    "/workspaces", response_model=WorkspaceCollectionResponse, operation_id="listWorkspaces"
)
async def list_workspaces(
    context: Context, container: Container, selected_page: PageDependency
) -> WorkspaceCollectionResponse:
    query = cast("IdentityQueryService", container.identity.query)
    workspace = await query.get_workspace(context, context.workspace_id)
    items = (workspace,) if selected_page.page.offset == 0 else ()
    page = Page(items, 1, selected_page.page)
    return WorkspaceCollectionResponse(
        items=[workspace_response(item) for item in page.items],
        page=page_metadata(page),
    )


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    operation_id="getWorkspace",
)
async def get_workspace(
    workspace_id: UUID,
    _selected: SelectedWorkspace,
    context: Context,
    container: Container,
) -> WorkspaceResponse:
    query = cast("IdentityQueryService", container.identity.query)
    return workspace_response(await query.get_workspace(context, workspace_id))


@router.get(
    "/workspaces/{workspace_id}/memberships",
    response_model=MembershipCollectionResponse,
    operation_id="listMemberships",
)
async def list_memberships(
    workspace_id: UUID,
    _selected: SelectedWorkspace,
    context: Context,
    container: Container,
    selected_page: PageDependency,
) -> MembershipCollectionResponse:
    query = cast("IdentityQueryService", container.identity.query)
    page = await query.list_memberships(context, workspace_id, selected_page.page)
    return MembershipCollectionResponse(
        items=[membership_response(item) for item in page.items],
        page=page_metadata(page),
    )


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createProject",
)
async def create_project(  # noqa: PLR0913, PLR0917
    workspace_id: UUID,
    body: ProjectCreateRequest,
    response: Response,
    _selected: SelectedWorkspace,
    context: Context,
    container: Container,
    key: Idempotency,
) -> ProjectResponse:
    del workspace_id
    project = await container.projects.service.create(
        context,
        name=body.name,
        settings=ProjectSettings(**body.settings.model_dump()),
        idempotency_key=key,
    )
    response.headers["Location"] = f"/api/v1/projects/{project.id}"
    response.headers["ETag"] = etag(project.version)
    return project_response(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectCollectionResponse,
    operation_id="listProjects",
)
async def list_projects(  # noqa: PLR0913, PLR0917
    workspace_id: UUID,
    _selected: SelectedWorkspace,
    context: Context,
    container: Container,
    selected_page: PageDependency,
    status_filter: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    sort: ProjectSort = ProjectSort.CREATED_AT_DESC,
) -> ProjectCollectionResponse:
    del workspace_id
    page = await container.projects.service.list(
        context, selected_page.page, status=status_filter, sort=sort
    )
    return ProjectCollectionResponse(
        items=[project_response(item) for item in page.items],
        page=page_metadata(page),
        sort=sort,
        status_filter=status_filter,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse, operation_id="getProject")
async def get_project(
    project_id: UUID, response: Response, context: Context, container: Container
) -> ProjectResponse:
    project = await container.projects.service.get(context, project_id)
    response.headers["ETag"] = etag(project.version)
    return project_response(project)


@router.patch(
    "/projects/{project_id}", response_model=ProjectResponse, operation_id="updateProject"
)
async def update_project(  # noqa: PLR0913, PLR0917
    project_id: UUID,
    body: ProjectUpdateRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ProjectResponse:
    project = await container.projects.service.update_settings(
        context,
        project_id,
        ProjectSettings(**body.settings.model_dump()),
        expected_version=expected_version,
    )
    response.headers["ETag"] = etag(project.version)
    return project_response(project)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectResponse,
    operation_id="archiveProject",
)
async def archive_project(
    project_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ProjectResponse:
    project = await container.projects.service.archive(
        context, project_id, expected_version=expected_version
    )
    response.headers["ETag"] = etag(project.version)
    return project_response(project)


@router.post(
    "/projects/{project_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createArtifact",
)
async def create_artifact(
    project_id: UUID,
    body: ArtifactCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ArtifactResponse:
    artifact = await container.projects.service.create_artifact(
        context, project_id, artifact_type=body.artifact_type, label=body.label
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/artifacts/{artifact.id}"
    response.headers["ETag"] = etag(artifact.version)
    return artifact_response(artifact)


@router.get(
    "/projects/{project_id}/artifacts",
    response_model=ArtifactCollectionResponse,
    operation_id="listArtifacts",
)
async def list_artifacts(
    project_id: UUID,
    context: Context,
    container: Container,
    selected_page: PageDependency,
    sort: ArtifactSort = ArtifactSort.CREATED_AT_DESC,
) -> ArtifactCollectionResponse:
    page = await container.projects.service.list_artifacts(
        context, project_id, selected_page.page, sort=sort
    )
    return ArtifactCollectionResponse(
        items=[artifact_response(item) for item in page.items],
        page=page_metadata(page),
        sort=sort,
    )


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}",
    response_model=ArtifactResponse,
    operation_id="getArtifact",
)
async def get_artifact(
    project_id: UUID,
    artifact_id: UUID,
    response: Response,
    context: Context,
    container: Container,
) -> ArtifactResponse:
    artifact = await container.projects.service.get_artifact(context, project_id, artifact_id)
    response.headers["ETag"] = etag(artifact.version)
    return artifact_response(artifact)


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/revisions",
    response_model=RevisionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createRevision",
)
async def create_revision(  # noqa: PLR0913, PLR0917
    project_id: UUID,
    artifact_id: UUID,
    body: RevisionCreateRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> RevisionResponse:
    revision = await container.projects.service.add_artifact_revision(
        context,
        project_id,
        artifact_id,
        content_reference=body.content_reference,
        content_hash=body.content_hash,
        expected_version=expected_version,
    )
    response.headers["Location"] = (
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions/"
        f"{revision.revision_number}"
    )
    return revision_response(revision)


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}/revisions",
    response_model=RevisionCollectionResponse,
    operation_id="listRevisions",
)
async def list_revisions(
    project_id: UUID,
    artifact_id: UUID,
    context: Context,
    container: Container,
    selected_page: PageDependency,
) -> RevisionCollectionResponse:
    page = await container.projects.service.list_revisions(
        context, project_id, artifact_id, selected_page.page
    )
    return RevisionCollectionResponse(
        items=[revision_response(item) for item in page.items], page=page_metadata(page)
    )


@router.post(
    "/projects/{project_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAsset",
)
async def create_asset(
    project_id: UUID,
    body: AssetUploadRequest,
    response: Response,
    context: Context,
    container: Container,
) -> AssetResponse:
    result = await container.assets.service.upload(
        context,
        project_id,
        filename=body.filename,
        media_type=body.media_type,
        data=body.content_base64,
        expected_sha256=body.expected_sha256,
        source=body.source,
    )
    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/projects/{project_id}/assets/{result.asset.id}"
    response.headers["ETag"] = etag(result.asset.version)
    return asset_response(result.asset, result.version, duplicate=result.duplicate)


@router.post(
    "/projects/{project_id}/assets/{asset_id}/versions",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAssetVersion",
)
async def create_asset_version(  # noqa: PLR0913, PLR0917
    project_id: UUID,
    asset_id: UUID,
    body: AssetUploadRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> AssetResponse:
    current, _current_version = await container.assets.service.get(context, project_id, asset_id)
    if current.version != expected_version:
        raise ConcurrencyConflictError(current.version)
    result = await container.assets.service.upload(
        context,
        project_id,
        filename=body.filename,
        media_type=body.media_type,
        data=body.content_base64,
        expected_sha256=body.expected_sha256,
        source=body.source,
        asset_id=asset_id,
        expected_version=expected_version,
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/assets/{asset_id}"
    response.headers["ETag"] = etag(result.asset.version)
    return asset_response(result.asset, result.version, duplicate=result.duplicate)


@router.get(
    "/projects/{project_id}/assets",
    response_model=AssetCollectionResponse,
    operation_id="listAssets",
)
async def list_assets(  # noqa: PLR0913, PLR0917
    project_id: UUID,
    context: Context,
    container: Container,
    selected_page: PageDependency,
    status_filter: Annotated[AssetStatus | None, Query(alias="status")] = None,
    sort: AssetSort = AssetSort.CREATED_AT_DESC,
) -> AssetCollectionResponse:
    page = await container.assets.service.list(
        context, project_id, selected_page.page, status=status_filter, sort=sort
    )
    return AssetCollectionResponse(
        items=[asset_response(asset, version) for asset, version in page.items],
        page=page_metadata(page),
        sort=sort,
        status_filter=status_filter,
    )


@router.get(
    "/projects/{project_id}/assets/{asset_id}",
    response_model=AssetResponse,
    operation_id="getAsset",
)
async def get_asset(
    project_id: UUID,
    asset_id: UUID,
    response: Response,
    context: Context,
    container: Container,
) -> AssetResponse:
    asset, version = await container.assets.service.get(context, project_id, asset_id)
    response.headers["ETag"] = etag(asset.version)
    return asset_response(asset, version)


@router.get(
    "/projects/{project_id}/assets/{asset_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
    operation_id="downloadAsset",
)
async def download_asset(
    project_id: UUID, asset_id: UUID, context: Context, container: Container
) -> Response:
    _asset, version = await container.assets.service.get(context, project_id, asset_id)
    data = await container.assets.service.download(context, project_id, asset_id)
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


@router.delete(
    "/projects/{project_id}/assets/{asset_id}",
    response_model=AssetResponse,
    operation_id="markAssetForDeletion",
)
async def mark_asset_for_deletion(  # noqa: PLR0913, PLR0917
    project_id: UUID,
    asset_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> AssetResponse:
    asset = await container.assets.service.mark_for_deletion(
        context, project_id, asset_id, expected_version=expected_version
    )
    _current, version = await container.assets.service.get(context, project_id, asset_id)
    response.headers["ETag"] = etag(asset.version)
    return asset_response(asset, version)


@router.get("/system/health", response_model=SystemHealthResponse, operation_id="getSystemHealth")
async def system_health(context: Context, container: Container) -> Response:
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "system", "health"),
        )
    )
    report = await container.health.readiness()
    return Response(
        content=SystemHealthResponse.model_validate(report.as_dict()).model_dump_json(),
        status_code=report.http_status,
        media_type="application/json",
    )


@router.get(
    "/system/settings",
    response_model=SystemSettingsResponse,
    response_model_exclude_none=True,
    operation_id="getSystemSettings",
)
async def system_settings(context: Context, container: Container) -> SystemSettingsResponse:
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "system", "settings"),
        )
    )
    settings = container.settings
    worker_configured = container.workflows.celery_app is not None
    runtime = await container.observability.monitor.snapshot()
    return SystemSettingsResponse(
        environment=settings.optional.environment,
        log_level=settings.optional.log_level,
        object_storage_region=settings.optional.s3_region,
        object_storage_tls=settings.optional.s3_use_ssl,
        ai_provider=settings.optional.ai_provider,
        development_identity_enabled=settings.security.dev_identity_enabled,
        feature_flags=[
            FeatureFlagStatusResponse(
                name="real_provider_calls",
                enabled=settings.features.real_provider_calls_enabled,
            ),
            *(
                FeatureFlagStatusResponse(name=name, enabled=enabled)
                for name, enabled in settings.features.extension_values().items()
            ),
        ],
        runtime_boundaries=[
            RuntimeBoundaryStatusResponse(
                name="worker",
                status=runtime.worker.state.value if worker_configured else "not_configured",
                detail=(
                    runtime.worker.detail
                    if worker_configured
                    else "queue_consumer_not_configured_in_api_process"
                ),
                observed_at=runtime.worker.last_seen_at if worker_configured else None,
            ),
            RuntimeBoundaryStatusResponse(
                name="outbox",
                status=runtime.outbox.state.value,
                detail=runtime.outbox.detail,
                backlog=runtime.outbox.backlog,
                oldest_age_seconds=runtime.outbox.oldest_age_seconds,
            ),
        ],
    )


@router.get(
    "/system/observability",
    response_model=SystemObservabilityResponse,
    response_model_exclude_none=True,
    operation_id="getSystemObservability",
)
async def system_observability(
    context: Context, container: Container
) -> SystemObservabilityResponse:
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "system", "observability"),
        )
    )
    snapshot = await container.observability.monitor.refresh_metrics(
        container.observability.telemetry
    )
    worker_configured = container.workflows.celery_app is not None
    return SystemObservabilityResponse(
        metrics_enabled=container.settings.observability.metrics_enabled,
        otlp_configured=container.settings.observability.otlp_endpoint is not None,
        metric_names=list(container.observability.telemetry.registry.names),
        runtime_boundaries=[
            RuntimeBoundaryStatusResponse(
                name="worker",
                status=snapshot.worker.state.value if worker_configured else "not_configured",
                detail=(
                    snapshot.worker.detail
                    if worker_configured
                    else "queue_consumer_not_configured_in_api_process"
                ),
                observed_at=snapshot.worker.last_seen_at if worker_configured else None,
            ),
            RuntimeBoundaryStatusResponse(
                name="outbox",
                status=snapshot.outbox.state.value,
                detail=snapshot.outbox.detail,
                backlog=snapshot.outbox.backlog,
                oldest_age_seconds=snapshot.outbox.oldest_age_seconds,
            ),
        ],
    )


@router.get(
    "/extensions/status",
    response_model=ExtensionStatusCollectionResponse,
    operation_id="listExtensionStatuses",
)
async def extension_statuses(
    context: Context,
    container: Container,
) -> ExtensionStatusCollectionResponse:
    """Expose only manifests and honest runtime availability for parked capabilities."""
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "system", "extensions"),
        )
    )
    return ExtensionStatusCollectionResponse(
        items=[
            ExtensionCapabilityStatusResponse(
                capability=item.manifest.capability.value,
                state=item.state.value,
                enabled=item.enabled,
                configured=item.configured,
                detail=item.detail,
                feature_flag=item.manifest.feature_flag,
                required_permissions=list(item.manifest.required_permissions),
                emitted_events=list(item.manifest.emitted_events),
                configuration_schema_version=item.manifest.configuration_schema_version,
                configuration_fields=[
                    ExtensionConfigurationFieldResponse(
                        name=field.name,
                        kind=field.kind.value,
                        required=field.required,
                    )
                    for field in item.manifest.configuration_fields
                ],
                promotion_criteria=[
                    criterion.value for criterion in item.manifest.promotion_criteria
                ],
            )
            for item in container.extensions.catalog.statuses()
        ]
    )


router.include_router(stage17_router)
