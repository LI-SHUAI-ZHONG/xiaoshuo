"""Content resources use live project authorization, strong CAS and immutable versions."""

from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import Field

from accos.composition import ApplicationContainer
from accos.entrypoints.api.v1.dependencies import (
    api_context,
    application_container,
    enforce_rate_limit,
    idempotency_key,
)
from accos.entrypoints.api.v1.schemas import ApiModel
from accos.kernel.errors import ErrorEnvelope, InvalidRequestError, PreconditionRequiredError
from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import ContentRef
from accos.modules.projects.content import (
    Branch,
    ContentRevision,
    EditorDocument,
    MergeResult,
    SaveContent,
    WorkingCopy,
    main_branch,
)
from accos.modules.projects.content_ports import BranchPage, Patch, RevisionPage

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(enforce_rate_limit)],
    responses={code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 428, 503)},
)
Context = Annotated[SecurityContext, Depends(api_context)]
Container = Annotated[ApplicationContainer, Depends(application_container)]
Key = Annotated[str, Depends(idempotency_key)]
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=2048)]


def content_version(value: Annotated[str | None, Header(alias="If-Match")] = None) -> int:
    if value is None:
        raise PreconditionRequiredError()
    if re.fullmatch(r'"(0|[1-9][0-9]*)"', value) is None:
        raise InvalidRequestError("If-Match requires a strong integer ETag.")
    return int(value[1:-1])


Version = Annotated[int, Depends(content_version)]


class BranchInput(ApiModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^\S(?:.*\S)?$")
    base_revision_id: UUID | None = None


class RestoreInput(ApiModel):
    branch_id: UUID
    base_revision_id: UUID | None
    document_epoch: int = Field(ge=1)
    client_change_id: UUID


class MergeInput(RestoreInput):
    source_revision_id: UUID
    resolutions: dict[str, Literal["ours", "theirs"]] = Field(
        default_factory=dict, max_length=50_001
    )


class LegacyImportInput(RestoreInput):
    source_asset: ContentRef


class PatchInput(ApiModel):
    branch_id: UUID
    base_revision_id: UUID
    document: EditorDocument


class PatchApplyInput(RestoreInput):
    resolutions: dict[str, Literal["ours", "theirs"]] = Field(
        default_factory=dict, max_length=50_001
    )


class ReconcileInput(ApiModel):
    base_revision_id: UUID | None
    current_revision_id: UUID | None
    document: EditorDocument
    resolutions: dict[str, Literal["ours", "theirs"]] = Field(
        default_factory=dict, max_length=50_001
    )


class RevisionContent(ApiModel):
    revision: ContentRevision
    document: EditorDocument | None
    text: str | None


def match_change(key: str, change: UUID) -> None:
    if key != str(change):
        raise InvalidRequestError("Idempotency-Key must equal client_change_id for content writes.")


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}/working-copy", response_model=WorkingCopy
)
async def get_working_copy(
    project_id: UUID,
    artifact_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    branch_id: UUID | None = None,
) -> WorkingCopy:
    value = await container.projects.content.working_copy(
        context, project_id, artifact_id, branch_id
    )
    response.headers.update(
        {"ETag": f'"{value.branch.version}"', "Cache-Control": "private, no-store"}
    )
    return value


@router.put(
    "/projects/{project_id}/artifacts/{artifact_id}/working-copy", response_model=ContentRevision
)
async def save_working_copy(
    project_id: UUID,
    artifact_id: UUID,
    body: SaveContent,
    response: Response,
    context: Context,
    container: Container,
    expected: Version,
    key: Key,
    branch_id: UUID | None = None,
) -> ContentRevision:
    match_change(key, body.client_change_id)
    value = await container.projects.content.save(
        context, project_id, artifact_id, branch_id or main_branch(artifact_id), body, expected
    )
    response.headers["ETag"] = f'"{value.working_version}"'
    return value


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}/content", response_model=RevisionContent
)
async def get_content(
    project_id: UUID,
    artifact_id: UUID,
    revision_id: UUID,
    context: Context,
    container: Container,
    response: Response,
) -> RevisionContent:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id)
    revision = await service.repository.revision(
        context.workspace_id, project_id, artifact_id, revision_id
    )
    document = (
        await service.document(context, project_id, revision)
        if revision.content_status == "available"
        else None
    )
    response.headers["Cache-Control"] = "private, no-store"
    return RevisionContent(
        revision=revision, document=document, text=document.plain_text() if document else None
    )


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}/revision-history", response_model=RevisionPage
)
async def revision_history(
    project_id: UUID,
    artifact_id: UUID,
    context: Context,
    container: Container,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> RevisionPage:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id)
    return await service.repository.revisions(
        context.workspace_id, project_id, artifact_id, cursor, limit
    )


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/revisions/{revision_id}/restore",
    response_model=ContentRevision,
)
async def restore_revision(
    project_id: UUID,
    artifact_id: UUID,
    revision_id: UUID,
    body: RestoreInput,
    context: Context,
    container: Container,
    expected: Version,
    key: Key,
) -> ContentRevision:
    match_change(key, body.client_change_id)
    return await container.projects.content.restore(
        context,
        project_id,
        artifact_id,
        body.branch_id,
        revision_id,
        body.client_change_id,
        body.base_revision_id,
        body.document_epoch,
        expected,
    )


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/revisions/{revision_id}/import-legacy",
    response_model=ContentRevision,
)
async def import_legacy_content(
    project_id: UUID,
    artifact_id: UUID,
    revision_id: UUID,
    body: LegacyImportInput,
    context: Context,
    container: Container,
    expected: Version,
    key: Key,
) -> ContentRevision:
    match_change(key, body.client_change_id)
    return await container.projects.content.recover_legacy(
        context,
        project_id,
        artifact_id,
        revision_id,
        body.source_asset,
        body.branch_id,
        body.base_revision_id,
        body.document_epoch,
        body.client_change_id,
        expected,
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/branches", response_model=BranchPage)
async def list_branches(
    project_id: UUID,
    artifact_id: UUID,
    context: Context,
    container: Container,
    cursor: Cursor = None,
    limit: Limit = 20,
) -> BranchPage:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id)
    return await service.repository.branches(
        context.workspace_id, project_id, artifact_id, cursor, limit
    )


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/branches",
    response_model=Branch,
    status_code=201,
)
async def create_branch(
    project_id: UUID,
    artifact_id: UUID,
    body: BranchInput,
    context: Context,
    container: Container,
    key: Key,
) -> Branch:
    return await container.projects.content.create_branch(
        context, project_id, artifact_id, body.name, body.base_revision_id, key
    )


@router.put(
    "/projects/{project_id}/artifacts/{artifact_id}/branches/{branch_id}/archive",
    response_model=Branch,
)
async def archive_branch(
    project_id: UUID,
    artifact_id: UUID,
    branch_id: UUID,
    archived: bool,
    context: Context,
    container: Container,
    expected: Version,
) -> Branch:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id, write=True)
    return await service.repository.archive_branch(
        context, project_id, artifact_id, branch_id, expected, archived
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/diffs", response_model=MergeResult)
async def compare_revisions(
    project_id: UUID,
    artifact_id: UUID,
    ours: UUID,
    theirs: UUID,
    context: Context,
    container: Container,
) -> MergeResult:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id)
    base = await service.repository.merge_base(
        context.workspace_id, project_id, artifact_id, ours, theirs
    )
    return await service.compare(context, project_id, artifact_id, base, ours, theirs)


@router.post("/projects/{project_id}/artifacts/{artifact_id}/reconcile", response_model=MergeResult)
async def reconcile_local(
    project_id: UUID,
    artifact_id: UUID,
    body: ReconcileInput,
    context: Context,
    container: Container,
) -> MergeResult:
    from accos.modules.projects.content import merge_documents

    service = container.projects.content
    await service.authorize(context, project_id, artifact_id, write=True)

    async def load(identifier: UUID | None) -> EditorDocument:
        if identifier is None:
            return EditorDocument()
        rev = await service.repository.revision(
            context.workspace_id, project_id, artifact_id, identifier
        )
        return await service.document(context, project_id, rev)

    return merge_documents(
        await load(body.base_revision_id),
        await load(body.current_revision_id),
        body.document,
        body.resolutions,
    )


@router.post("/projects/{project_id}/artifacts/{artifact_id}/merge", response_model=ContentRevision)
async def merge_branch(
    project_id: UUID,
    artifact_id: UUID,
    body: MergeInput,
    context: Context,
    container: Container,
    expected: Version,
    key: Key,
) -> ContentRevision:
    match_change(key, body.client_change_id)
    if body.base_revision_id is None:
        raise InvalidRequestError("Merge target must identify the current revision.")
    return await container.projects.content.merge(
        context,
        project_id,
        artifact_id,
        body.branch_id,
        body.source_revision_id,
        body.base_revision_id,
        body.client_change_id,
        body.document_epoch,
        expected,
        body.resolutions,
    )


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/patches", response_model=Patch, status_code=201
)
async def propose_patch(
    project_id: UUID,
    artifact_id: UUID,
    body: PatchInput,
    context: Context,
    container: Container,
    key: Key,
) -> Patch:
    return await container.projects.content.propose_patch(
        context, project_id, artifact_id, body.branch_id, body.base_revision_id, body.document, key
    )


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}/patches/{patch_id}", response_model=Patch
)
async def get_patch(
    project_id: UUID, artifact_id: UUID, patch_id: UUID, context: Context, container: Container
) -> Patch:
    service = container.projects.content
    await service.authorize(context, project_id, artifact_id)
    return await service.repository.patch(context.workspace_id, project_id, artifact_id, patch_id)


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/patches/{patch_id}/apply",
    response_model=ContentRevision,
)
async def apply_patch(
    project_id: UUID,
    artifact_id: UUID,
    patch_id: UUID,
    body: PatchApplyInput,
    context: Context,
    container: Container,
    expected: Version,
    key: Key,
) -> ContentRevision:
    match_change(key, body.client_change_id)
    if body.base_revision_id is None:
        raise InvalidRequestError("A patch needs a current revision.")
    patch = await container.projects.content.repository.patch(
        context.workspace_id, project_id, artifact_id, patch_id
    )
    if patch.branch_id != body.branch_id:
        raise InvalidRequestError("Patch belongs to another branch.")
    return await container.projects.content.apply_patch(
        context,
        project_id,
        artifact_id,
        patch_id,
        body.base_revision_id,
        body.client_change_id,
        body.document_epoch,
        expected,
        body.resolutions,
    )
