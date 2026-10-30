"""Projects owns revision pointers; assets owns bytes and their retention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from accos.kernel.shared_contracts import ContentRef, SharedContract
from accos.modules.projects.content import Branch, ContentRevision

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.events import EventEnvelope
    from accos.kernel.security import SecurityContext


class RevisionPage(SharedContract):
    items: tuple[ContentRevision, ...]
    next_cursor: str | None = None


class BranchPage(SharedContract):
    items: tuple[Branch, ...]
    next_cursor: str | None = None


class Patch(SharedContract):
    id: UUID
    branch_id: UUID
    base_revision_id: UUID
    document_ref: ContentRef
    created_by: UUID


class ContentRepository(Protocol):
    async def head(
        self, workspace: UUID, project: UUID, artifact: UUID, branch: UUID
    ) -> Branch: ...

    async def revision(
        self, workspace: UUID, project: UUID, artifact: UUID, revision: UUID
    ) -> ContentRevision: ...

    async def revisions(
        self, workspace: UUID, project: UUID, artifact: UUID, cursor: str | None, limit: int
    ) -> RevisionPage: ...

    async def branches(
        self, workspace: UUID, project: UUID, artifact: UUID, cursor: str | None, limit: int
    ) -> BranchPage: ...

    async def create_branch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: Branch,
        base: UUID | None,
        now: datetime,
    ) -> Branch: ...

    async def replay(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        change: UUID,
        digest: str,
    ) -> ContentRevision | None: ...

    async def commit(
        self,
        context: SecurityContext,
        revision: ContentRevision,
        expected: Branch,
        change: UUID,
        digest: str,
        event: EventEnvelope,
    ) -> ContentRevision: ...

    async def merge_base(
        self, workspace: UUID, project: UUID, artifact: UUID, left: UUID, right: UUID
    ) -> UUID | None: ...

    async def put_patch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        patch: Patch,
        key: str,
        digest: str,
        now: datetime,
    ) -> Patch: ...

    async def patch(self, workspace: UUID, project: UUID, artifact: UUID, patch: UUID) -> Patch: ...

    async def archive_branch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        expected: int,
        archived: bool,
    ) -> Branch: ...
