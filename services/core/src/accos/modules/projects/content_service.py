"""Authorized object-first, CAS protected manual writing and candidate application."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4, uuid5

from accos.kernel.errors import ConcurrencyConflictError, InvalidRequestError, InvalidStateError
from accos.kernel.events import EventEnvelope
from accos.kernel.shared_contracts import ContentRef
from accos.modules.projects.content import (
    Branch,
    BlockAttributes,
    ContentRevision,
    EditorBlock,
    EditorDocument,
    MergeResult,
    SaveContent,
    TextNode,
    WorkingCopy,
    main_branch,
    merge_documents,
    require_unlocked_patch,
)
from accos.modules.projects.content_ports import Patch

if TYPE_CHECKING:
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.assets.public import AssetService
    from accos.modules.projects.application import ProjectService
    from accos.modules.projects.content_ports import ContentRepository


class ContentService:
    def __init__(
        self,
        repository: ContentRepository,
        projects: ProjectService,
        assets: AssetService,
        clock: Clock,
    ) -> None:
        self.repository = repository
        self.projects = projects
        self.assets = assets
        self.clock = clock

    async def authorize(
        self, ctx: SecurityContext, project: UUID, artifact: UUID, *, write: bool = False
    ) -> None:
        await self.projects.get_artifact(ctx, project, artifact)
        if write:
            await self.projects.require_writable(ctx, project)

    async def document(
        self, ctx: SecurityContext, project: UUID, revision: ContentRevision
    ) -> EditorDocument:
        if revision.content_status != "available" or revision.document_ref is None:
            raise InvalidStateError(
                "Legacy content is unavailable or unverified; no text was recovered."
            )
        data = await self.assets.read_snapshot(ctx, project, revision.document_ref)
        return EditorDocument.model_validate_json(data)

    async def working_copy(
        self, ctx: SecurityContext, project: UUID, artifact: UUID, branch_id: UUID | None = None
    ) -> WorkingCopy:
        await self.authorize(ctx, project, artifact)
        branch = await self.repository.head(
            ctx.workspace_id, project, artifact, branch_id or main_branch(artifact)
        )
        if branch.head_revision_id is None:
            return WorkingCopy(
                branch=branch,
                revision=None,
                document=EditorDocument(),
                text="",
                content_status="empty",
            )
        revision = await self.repository.revision(
            ctx.workspace_id, project, artifact, branch.head_revision_id
        )
        doc = (
            await self.document(ctx, project, revision)
            if revision.content_status == "available"
            else None
        )
        return WorkingCopy(
            branch=branch,
            revision=revision,
            document=doc,
            text=doc.plain_text() if doc else None,
            content_status=revision.content_status,
        )

    async def save(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch_id: UUID,
        body: SaveContent,
        expected_version: int,
        *,
        operation: str = "save",
        extra_parent: UUID | None = None,
        request_extra: str = "",
    ) -> ContentRevision:
        await self.authorize(ctx, project, artifact, write=True)
        digest = hashlib.sha256(
            (
                body.model_dump_json()
                + str(expected_version)
                + operation
                + str(extra_parent)
                + request_extra
            ).encode()
        ).hexdigest()
        replay = await self.repository.replay(
            ctx, project, artifact, branch_id, body.client_change_id, digest
        )
        if replay is not None:
            return replay
        head = await self.repository.head(ctx.workspace_id, project, artifact, branch_id)
        if (
            head.version != expected_version
            or head.head_revision_id != body.base_revision_id
            or head.document_epoch != body.document_epoch
        ):
            raise content_conflict(head)
        if head.editing_mode != "solo" or head.archived:
            raise InvalidStateError("This branch does not accept solo REST writes.")
        document_ref = await self.assets.put_snapshot(
            ctx, project, body.document.to_bytes(), media_type="application/json"
        )
        text_ref = await self.assets.put_snapshot(
            ctx, project, body.document.plain_text().encode(), media_type="text/plain"
        )
        # Object I/O may outlive a permission grant. Recheck before committing a
        # revision; uploaded immutable assets remain retained if access changed.
        await self.authorize(ctx, project, artifact, write=True)
        now = self.clock.now()
        parents = tuple(dict.fromkeys(p for p in (head.head_revision_id, extra_parent) if p))
        revision = ContentRevision(
            id=uuid4(),
            workspace_id=ctx.workspace_id,
            project_id=project,
            artifact_id=artifact,
            revision_number=1,
            branch_id=branch_id,
            content_status="available",
            document_ref=document_ref,
            text_ref=text_ref,
            content_hash=document_ref.sha256,
            content_reference=f"asset://{document_ref.asset_id}/{document_ref.asset_version_id}",
            editor_schema_version=1,
            parents=parents,
            operation=operation,
            created_by=ctx.actor_id,
            created_at=now,
            working_version=head.version + 1,
            document_epoch=head.document_epoch,
        )
        event = EventEnvelope(
            uuid4(),
            ctx.workspace_id,
            project,
            artifact,
            "projects.artifact-content-saved",
            1,
            {
                "schema": "ArtifactContentSaved.v1",
                "revision_id": str(revision.id),
                "branch_id": str(branch_id),
                "sha256": revision.content_hash,
                "document_ref": document_ref.model_dump(mode="json"),
                "text_ref": text_ref.model_dump(mode="json"),
                "aggregate_version": revision.working_version,
                "correlation_id": ctx.correlation.request_id,
            },
            now,
        )
        return await self.repository.commit(
            ctx, revision, head, body.client_change_id, digest, event
        )

    async def restore(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch_id: UUID,
        source: UUID,
        change: UUID,
        base: UUID | None,
        epoch: int,
        expected: int,
    ) -> ContentRevision:
        await self.authorize(ctx, project, artifact, write=True)
        revision = await self.repository.revision(ctx.workspace_id, project, artifact, source)
        return await self.save(
            ctx,
            project,
            artifact,
            branch_id,
            SaveContent(
                document=await self.document(ctx, project, revision),
                client_change_id=change,
                base_revision_id=base,
                document_epoch=epoch,
            ),
            expected,
            operation="restore",
            extra_parent=source,
        )

    async def recover_legacy(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        source: UUID,
        ref: ContentRef,
        branch: UUID,
        base: UUID | None,
        epoch: int,
        change: UUID,
        expected: int,
    ) -> ContentRevision:
        """Stage-45 import verifies original bytes and appends a new revision.

        Historical hashes/references are never rewritten or fabricated. A reviewed
        asset mapping is required for legacy S3 records lacking registered content.
        """
        await self.authorize(ctx, project, artifact, write=True)
        legacy = await self.repository.revision(ctx.workspace_id, project, artifact, source)
        if (
            legacy.content_status != "legacy_unverified"
            or not legacy.content_reference
            or legacy.content_hash != ref.sha256
        ):
            raise InvalidRequestError("A matching, verifiable legacy S3 record is required.")
        data = await self.assets.read_legacy_snapshot(ctx, project, ref, legacy.content_reference)
        try:
            if ref.media_type == "application/json":
                document = EditorDocument.model_validate_json(data)
            elif ref.media_type in {"text/plain", "text/markdown"}:
                document = EditorDocument(
                    content=tuple(
                        EditorBlock(
                            attrs=BlockAttributes(id=uuid5(source, f"legacy-line:{index}")),
                            content=(TextNode(text=line),) if line else (),
                        )
                        for index, line in enumerate(data.decode("utf-8").split("\n"))
                    )
                )
            else:
                raise ValueError("Unsupported legacy content type")
        except (ValueError, UnicodeError) as error:
            raise InvalidRequestError(
                "Legacy bytes do not match the supported document format."
            ) from error
        return await self.save(
            ctx,
            project,
            artifact,
            branch,
            SaveContent(
                document=document,
                client_change_id=change,
                base_revision_id=base,
                document_epoch=epoch,
            ),
            expected,
            operation="legacy_import",
            extra_parent=source,
            request_extra=ref.model_dump_json(),
        )

    async def create_branch(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        name: str,
        base: UUID | None,
        key: str,
    ) -> Branch:
        await self.authorize(ctx, project, artifact, write=True)
        if base is not None:
            await self.repository.revision(ctx.workspace_id, project, artifact, base)
        identifier = uuid5(artifact, f"branch:{ctx.actor_id}:{key}")
        branch = Branch(id=identifier, artifact_id=artifact, name=name, head_revision_id=base)
        return await self.repository.create_branch(
            ctx, project, artifact, branch, base, self.clock.now()
        )

    async def compare(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        base: UUID | None,
        ours: UUID | None,
        theirs: UUID,
        choices: dict[str, Literal["ours", "theirs"]] | None = None,
        *,
        protect_locks: bool = False,
    ) -> MergeResult:
        await self.authorize(ctx, project, artifact)

        async def load(identifier: UUID | None) -> EditorDocument:
            if identifier is None:
                return EditorDocument()
            revision = await self.repository.revision(
                ctx.workspace_id, project, artifact, identifier
            )
            return await self.document(ctx, project, revision)

        return merge_documents(
            await load(base),
            await load(ours),
            await load(theirs),
            choices,
            protect_locks=protect_locks,
        )

    async def merge(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch_id: UUID,
        source: UUID,
        target: UUID,
        change: UUID,
        epoch: int,
        expected: int,
        choices: dict[str, Literal["ours", "theirs"]],
    ) -> ContentRevision:
        await self.authorize(ctx, project, artifact, write=True)
        base = await self.repository.merge_base(ctx.workspace_id, project, artifact, target, source)
        result = await self.compare(ctx, project, artifact, base, target, source, choices)
        require_resolved(result)
        return await self.save(
            ctx,
            project,
            artifact,
            branch_id,
            SaveContent(
                document=result.document,
                client_change_id=change,
                base_revision_id=target,
                document_epoch=epoch,
            ),
            expected,
            operation="merge",
            extra_parent=source,
            request_extra=json.dumps(choices, sort_keys=True),
        )

    async def propose_patch(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        base: UUID,
        document: EditorDocument,
        key: str,
    ) -> Patch:
        await self.authorize(ctx, project, artifact, write=True)
        await self.repository.head(ctx.workspace_id, project, artifact, branch)
        revision = await self.repository.revision(ctx.workspace_id, project, artifact, base)
        require_unlocked_patch(await self.document(ctx, project, revision), document)
        ref = await self.assets.put_snapshot(
            ctx, project, document.to_bytes(), media_type="application/json"
        )
        patch = Patch(
            id=uuid5(artifact, f"patch:{ctx.actor_id}:{key}"),
            branch_id=branch,
            base_revision_id=base,
            document_ref=ref,
            created_by=ctx.actor_id,
        )
        digest = hashlib.sha256(f"{branch}:{base}:{document.digest()}".encode()).hexdigest()
        return await self.repository.put_patch(
            ctx, project, artifact, patch, key, digest, self.clock.now()
        )

    async def apply_patch(
        self,
        ctx: SecurityContext,
        project: UUID,
        artifact: UUID,
        patch_id: UUID,
        target: UUID,
        change: UUID,
        epoch: int,
        expected: int,
        choices: dict[str, Literal["ours", "theirs"]],
    ) -> ContentRevision:
        await self.authorize(ctx, project, artifact, write=True)
        patch = await self.repository.patch(ctx.workspace_id, project, artifact, patch_id)
        base = await self.repository.revision(
            ctx.workspace_id, project, artifact, patch.base_revision_id
        )
        current = await self.repository.revision(ctx.workspace_id, project, artifact, target)
        candidate = EditorDocument.model_validate_json(
            await self.assets.read_snapshot(ctx, project, patch.document_ref)
        )
        result = merge_documents(
            await self.document(ctx, project, base),
            await self.document(ctx, project, current),
            candidate,
            choices,
            protect_locks=True,
        )
        require_resolved(result)
        return await self.save(
            ctx,
            project,
            artifact,
            patch.branch_id,
            SaveContent(
                document=result.document,
                client_change_id=change,
                base_revision_id=target,
                document_epoch=epoch,
            ),
            expected,
            operation="patch",
            request_extra=str(patch_id) + json.dumps(choices, sort_keys=True),
        )


def content_conflict(branch: Branch) -> ConcurrencyConflictError:
    error = ConcurrencyConflictError(branch.version)
    error.details.update(
        {
            "head_revision_id": str(branch.head_revision_id) if branch.head_revision_id else None,
            "branch_id": str(branch.id),
            "document_epoch": branch.document_epoch,
        }
    )
    return error


def require_resolved(result: MergeResult) -> None:
    if result.conflicts:
        error = ConcurrencyConflictError()
        error.details["conflicting_blocks"] = [c.block_id for c in result.conflicts]
        raise error
