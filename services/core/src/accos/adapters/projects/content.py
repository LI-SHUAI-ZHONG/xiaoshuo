"""Revision transactions serialize on the artifact and never wait on object I/O."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, cast
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.adapters.projects.persistence import ArtifactRevisionRow, ArtifactRow, ProjectRow
from accos.kernel.errors import (
    IdempotencyConflictError,
    InvalidRequestError,
    InvalidStateError,
    ResourceNotFoundError,
)
from accos.kernel.shared_contracts import ContentRef
from accos.modules.projects.content import Branch, ContentRevision, main_branch
from accos.modules.projects.content_ports import BranchPage, Patch, RevisionPage
from accos.modules.projects.content_service import content_conflict

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope
    from accos.kernel.security import SecurityContext


class BranchRow(Base):
    __tablename__ = "artifact_branches"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid)
    project_id: Mapped[UUID] = mapped_column(Uuid)
    artifact_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("project_artifacts.id"))
    name: Mapped[str] = mapped_column(String(100))
    base_revision_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("artifact_id", "name", name="uq_branch_name"),
        Index("ix_branch_scope", "workspace_id", "project_id", "artifact_id"),
        {"schema": SCHEMA_NAME},
    )


class WorkingCopyRow(Base):
    __tablename__ = "artifact_working_copies"
    branch_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("artifact_branches.id"), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(Uuid)
    project_id: Mapped[UUID] = mapped_column(Uuid)
    artifact_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("project_artifacts.id"))
    head_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("project_artifact_revisions.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=0)
    document_epoch: Mapped[int] = mapped_column(Integer, default=1)
    editing_mode: Mapped[str] = mapped_column(String(20), default="solo")
    __table_args__ = (
        Index("ix_working_copy_scope", "workspace_id", "project_id", "artifact_id"),
        {"schema": SCHEMA_NAME},
    )


class RevisionEdgeRow(Base):
    __tablename__ = "revision_edges"
    revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("project_artifact_revisions.id"), primary_key=True
    )
    parent_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("project_artifact_revisions.id"), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(Uuid)
    project_id: Mapped[UUID] = mapped_column(Uuid)
    artifact_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("project_artifacts.id"))
    __table_args__ = (
        Index("ix_revision_edge_scope", "workspace_id", "project_id", "artifact_id"),
        {"schema": SCHEMA_NAME},
    )


class RevisionPatchRow(Base):
    __tablename__ = "revision_patches"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid)
    project_id: Mapped[UUID] = mapped_column(Uuid)
    artifact_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("project_artifacts.id"))
    branch_id: Mapped[UUID] = mapped_column(Uuid)
    base_revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("project_artifact_revisions.id")
    )
    document_ref: Mapped[dict[str, object]] = mapped_column(JSON_TYPE)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        Index("ix_revision_patch_scope", "workspace_id", "project_id", "artifact_id"),
        {"schema": SCHEMA_NAME},
    )


class SqlAlchemyContentRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def _head(
        self, session: AsyncSession, workspace: UUID, project: UUID, artifact: UUID, branch: UUID
    ) -> Branch:
        row = await session.scalar(
            select(BranchRow).where(
                BranchRow.id == branch,
                BranchRow.workspace_id == workspace,
                BranchRow.project_id == project,
                BranchRow.artifact_id == artifact,
            )
        )
        if row is None:
            if branch != main_branch(artifact):
                raise ResourceNotFoundError()
            latest = await session.scalar(
                select(ArtifactRevisionRow)
                .where(
                    ArtifactRevisionRow.workspace_id == workspace,
                    ArtifactRevisionRow.project_id == project,
                    ArtifactRevisionRow.artifact_id == artifact,
                    ArtifactRevisionRow.branch_id.is_(None),
                )
                .order_by(ArtifactRevisionRow.revision_number.desc())
                .limit(1)
            )
            return Branch(
                id=branch,
                artifact_id=artifact,
                name="主稿",
                head_revision_id=latest.id if latest else None,
            )
        copy = await session.get(WorkingCopyRow, branch)
        if copy is None:
            raise InvalidStateError("Working copy is missing.")
        return Branch(
            id=row.id,
            artifact_id=artifact,
            name=row.name,
            head_revision_id=copy.head_revision_id,
            version=copy.version,
            document_epoch=copy.document_epoch,
            editing_mode=cast(Literal["solo", "collaborative"], copy.editing_mode),
            archived=row.archived,
        )

    async def head(self, workspace: UUID, project: UUID, artifact: UUID, branch: UUID) -> Branch:
        async with self._sessions() as session:
            return await self._head(session, workspace, project, artifact, branch)

    async def _revision(self, session: AsyncSession, row: ArtifactRevisionRow) -> ContentRevision:
        parents = tuple(
            (
                await session.scalars(
                    select(RevisionEdgeRow.parent_id)
                    .where(
                        RevisionEdgeRow.revision_id == row.id,
                        RevisionEdgeRow.workspace_id == row.workspace_id,
                        RevisionEdgeRow.project_id == row.project_id,
                        RevisionEdgeRow.artifact_id == row.artifact_id,
                    )
                    .order_by(RevisionEdgeRow.parent_id)
                )
            ).all()
        )
        status = row.content_status
        if row.document_ref is None:
            status = (
                "legacy_content_unavailable"
                if (row.content_reference or "").startswith("studio-input://")
                else "legacy_unverified"
                if row.content_reference
                else "empty"
            )
        return ContentRevision(
            id=row.id,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            artifact_id=row.artifact_id,
            revision_number=row.revision_number,
            branch_id=row.branch_id,
            content_status=cast(
                Literal["available", "empty", "legacy_content_unavailable", "legacy_unverified"],
                status,
            ),
            document_ref=ContentRef.model_validate(row.document_ref) if row.document_ref else None,
            text_ref=ContentRef.model_validate(row.text_ref) if row.text_ref else None,
            content_hash=row.content_hash,
            content_reference=row.content_reference,
            editor_schema_version=row.editor_schema_version,
            parents=parents,
            operation=row.operation,
            created_by=row.created_by,
            created_at=row.created_at,
            working_version=row.working_version,
            document_epoch=row.document_epoch,
        )

    async def revision(
        self, workspace: UUID, project: UUID, artifact: UUID, revision: UUID
    ) -> ContentRevision:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ArtifactRevisionRow).where(
                    ArtifactRevisionRow.id == revision,
                    ArtifactRevisionRow.workspace_id == workspace,
                    ArtifactRevisionRow.project_id == project,
                    ArtifactRevisionRow.artifact_id == artifact,
                )
            )
            if row is None:
                raise ResourceNotFoundError()
            return await self._revision(session, row)

    async def revisions(
        self, workspace: UUID, project: UUID, artifact: UUID, cursor: str | None, limit: int
    ) -> RevisionPage:
        predicates = [
            ArtifactRevisionRow.workspace_id == workspace,
            ArtifactRevisionRow.project_id == project,
            ArtifactRevisionRow.artifact_id == artifact,
        ]
        if cursor is not None:
            try:
                number = int(cursor)
                if number < 1 or str(number) != cursor:
                    raise ValueError
            except ValueError:
                raise InvalidRequestError("Invalid revision cursor.") from None
            predicates.append(ArtifactRevisionRow.revision_number < number)
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ArtifactRevisionRow)
                    .where(*predicates)
                    .order_by(ArtifactRevisionRow.revision_number.desc())
                    .limit(limit + 1)
                )
            ).all()
            items = tuple([await self._revision(session, row) for row in rows[:limit]])
            return RevisionPage(
                items=items,
                next_cursor=str(rows[limit - 1].revision_number) if len(rows) > limit else None,
            )

    async def branches(
        self, workspace: UUID, project: UUID, artifact: UUID, cursor: str | None, limit: int
    ) -> BranchPage:
        # Main is virtual until the first write; persist nothing during a GET.
        predicates = [
            BranchRow.workspace_id == workspace,
            BranchRow.project_id == project,
            BranchRow.artifact_id == artifact,
        ]
        if cursor:
            try:
                predicates.append(BranchRow.id > UUID(cursor))
            except ValueError:
                raise InvalidRequestError("Invalid branch cursor.") from None
        async with self._sessions() as session:
            ids = list(
                (
                    await session.scalars(
                        select(BranchRow.id)
                        .where(*predicates)
                        .order_by(BranchRow.id)
                        .limit(limit + 1)
                    )
                ).all()
            )
            main = main_branch(artifact)
            if (cursor is None or main > UUID(cursor)) and main not in ids:
                if await session.get(BranchRow, main) is None:
                    ids = sorted([*ids, main])
            return BranchPage(
                items=tuple(
                    [
                        await self._head(session, workspace, project, artifact, b)
                        for b in ids[:limit]
                    ]
                ),
                next_cursor=str(ids[limit - 1]) if len(ids) > limit else None,
            )

    async def _lock(
        self, session: AsyncSession, workspace: UUID, project: UUID, artifact: UUID
    ) -> ArtifactRow:
        parent = await session.scalar(
            select(ProjectRow)
            .where(ProjectRow.id == project, ProjectRow.workspace_id == workspace)
            .with_for_update()
        )
        if parent is None or parent.status != "active":
            raise InvalidStateError("Project is unavailable or archived.")
        row = await session.scalar(
            select(ArtifactRow)
            .where(
                ArtifactRow.id == artifact,
                ArtifactRow.workspace_id == workspace,
                ArtifactRow.project_id == project,
            )
            .with_for_update()
        )
        if row is None:
            raise ResourceNotFoundError()
        return row

    async def create_branch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: Branch,
        base: UUID | None,
        now: datetime,
    ) -> Branch:
        async with self._sessions.begin() as session:
            await self._lock(session, context.workspace_id, project, artifact)
            existing = await session.get(BranchRow, branch.id)
            if existing is not None:
                if existing.name != branch.name or existing.base_revision_id != base:
                    raise IdempotencyConflictError()
                return await self._head(session, context.workspace_id, project, artifact, branch.id)
            duplicate = await session.scalar(
                select(BranchRow.id).where(
                    BranchRow.artifact_id == artifact, BranchRow.name == branch.name
                )
            )
            if duplicate is not None or branch.name == "主稿":
                raise InvalidStateError("Branch name is already in use.")
            self._add_branch(session, context, project, artifact, branch, now)
            await session.flush([obj for obj in session.new if isinstance(obj, BranchRow)])
            await session.flush()
            return branch

    def _add_branch(
        self,
        session: AsyncSession,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: Branch,
        now: datetime,
    ) -> None:
        session.add(
            BranchRow(
                id=branch.id,
                workspace_id=context.workspace_id,
                project_id=project,
                artifact_id=artifact,
                name=branch.name,
                base_revision_id=branch.head_revision_id,
                created_by=context.actor_id,
                created_at=now,
                archived=False,
            )
        )
        session.add(
            WorkingCopyRow(
                branch_id=branch.id,
                workspace_id=context.workspace_id,
                project_id=project,
                artifact_id=artifact,
                head_revision_id=branch.head_revision_id,
                version=branch.version,
                document_epoch=branch.document_epoch,
                editing_mode=branch.editing_mode,
            )
        )

    async def _replay(
        self,
        session: AsyncSession,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        change: UUID,
        digest: str,
    ) -> ContentRevision | None:
        row = await session.scalar(
            select(ArtifactRevisionRow).where(
                ArtifactRevisionRow.workspace_id == context.workspace_id,
                ArtifactRevisionRow.project_id == project,
                ArtifactRevisionRow.artifact_id == artifact,
                ArtifactRevisionRow.branch_id == branch,
                ArtifactRevisionRow.created_by == context.actor_id,
                ArtifactRevisionRow.client_change_id == change,
            )
        )
        if row is None:
            return None
        if row.request_digest != digest:
            raise IdempotencyConflictError()
        return await self._revision(session, row)

    async def replay(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        change: UUID,
        digest: str,
    ) -> ContentRevision | None:
        async with self._sessions() as session:
            return await self._replay(session, context, project, artifact, branch, change, digest)

    async def commit(
        self,
        context: SecurityContext,
        revision: ContentRevision,
        expected: Branch,
        change: UUID,
        digest: str,
        event: EventEnvelope,
    ) -> ContentRevision:
        async with self._sessions.begin() as session:
            artifact = await self._lock(
                session, context.workspace_id, revision.project_id, revision.artifact_id
            )
            replay = await self._replay(
                session, context, revision.project_id, artifact.id, expected.id, change, digest
            )
            if replay is not None:
                return replay
            current = await self._head(
                session, context.workspace_id, revision.project_id, artifact.id, expected.id
            )
            if current != expected:
                raise content_conflict(current)
            if current.editing_mode != "solo" or current.archived:
                raise InvalidStateError("Branch does not accept REST writes.")
            if await session.get(BranchRow, current.id) is None:
                self._add_branch(
                    session, context, revision.project_id, artifact.id, current, event.occurred_at
                )
                # Explicit ordering: SQLAlchemy has no relationship between these private models.
                await session.flush([obj for obj in session.new if isinstance(obj, BranchRow)])
                await session.flush()
            saved = revision.model_copy(update={"revision_number": artifact.current_revision + 1})
            row = ArtifactRevisionRow(
                **saved.model_dump(exclude={"parents", "document_ref", "text_ref"}),
                document_ref=saved.document_ref.model_dump(mode="json")
                if saved.document_ref
                else None,
                text_ref=saved.text_ref.model_dump(mode="json") if saved.text_ref else None,
                client_change_id=change,
                request_digest=digest,
            )
            session.add(row)
            await session.flush([row])
            for parent in saved.parents:
                found = await session.scalar(
                    select(ArtifactRevisionRow.id).where(
                        ArtifactRevisionRow.id == parent,
                        ArtifactRevisionRow.workspace_id == context.workspace_id,
                        ArtifactRevisionRow.project_id == revision.project_id,
                        ArtifactRevisionRow.artifact_id == artifact.id,
                    )
                )
                if found is None:
                    raise InvalidStateError("Revision parent is outside this artifact.")
                session.add(
                    RevisionEdgeRow(
                        revision_id=saved.id,
                        parent_id=parent,
                        workspace_id=context.workspace_id,
                        project_id=revision.project_id,
                        artifact_id=artifact.id,
                    )
                )
            copy = await session.get(WorkingCopyRow, current.id)
            if copy is None:
                raise InvalidStateError("Working copy is missing.")
            copy.head_revision_id, copy.version = saved.id, saved.working_version
            artifact.current_revision = saved.revision_number
            artifact.version += 1
            artifact.updated_at = event.occurred_at
            await SqlAlchemyOutboxWriter(session).append(event)
            return saved

    async def merge_base(
        self, workspace: UUID, project: UUID, artifact: UUID, left: UUID, right: UUID
    ) -> UUID | None:
        await self.revision(workspace, project, artifact, left)
        await self.revision(workspace, project, artifact, right)
        async with self._sessions() as session:
            edges = (
                await session.execute(
                    select(RevisionEdgeRow.revision_id, RevisionEdgeRow.parent_id).where(
                        RevisionEdgeRow.workspace_id == workspace,
                        RevisionEdgeRow.project_id == project,
                        RevisionEdgeRow.artifact_id == artifact,
                    )
                )
            ).all()
        parents: dict[UUID, set[UUID]] = {}
        for child, parent in edges:
            parents.setdefault(child, set()).add(parent)

        def ancestors(start: UUID) -> set[UUID]:
            visited: set[UUID] = set()
            pending = [start]
            while pending:
                item = pending.pop()
                if item not in visited:
                    visited.add(item)
                    pending.extend(parents.get(item, ()))
            return visited

        common = ancestors(left) & ancestors(right)
        best = common - {ancestor for child in common for ancestor in ancestors(child) - {child}}
        if len(best) > 1:
            raise InvalidStateError("Multiple merge bases require an explicit author revision.")
        return next(iter(best), None)

    async def put_patch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        patch: Patch,
        key: str,
        digest: str,
        now: datetime,
    ) -> Patch:
        del key
        async with self._sessions.begin() as session:
            await self._lock(session, context.workspace_id, project, artifact)
            row = await session.get(RevisionPatchRow, patch.id)
            if row is not None:
                if row.request_digest != digest:
                    raise IdempotencyConflictError()
                return _patch(row)
            session.add(
                RevisionPatchRow(
                    **patch.model_dump(exclude={"document_ref"}),
                    workspace_id=context.workspace_id,
                    project_id=project,
                    artifact_id=artifact,
                    document_ref=patch.document_ref.model_dump(mode="json"),
                    created_at=now,
                    request_digest=digest,
                )
            )
            return patch

    async def patch(self, workspace: UUID, project: UUID, artifact: UUID, patch: UUID) -> Patch:
        async with self._sessions() as session:
            row = await session.scalar(
                select(RevisionPatchRow).where(
                    RevisionPatchRow.id == patch,
                    RevisionPatchRow.workspace_id == workspace,
                    RevisionPatchRow.project_id == project,
                    RevisionPatchRow.artifact_id == artifact,
                )
            )
            if row is None:
                raise ResourceNotFoundError()
            return _patch(row)

    async def archive_branch(
        self,
        context: SecurityContext,
        project: UUID,
        artifact: UUID,
        branch: UUID,
        expected: int,
        archived: bool,
    ) -> Branch:
        async with self._sessions.begin() as session:
            await self._lock(session, context.workspace_id, project, artifact)
            current = await self._head(session, context.workspace_id, project, artifact, branch)
            if current.version != expected:
                raise content_conflict(current)
            if branch == main_branch(artifact):
                raise InvalidStateError("The main branch is retained.")
            row, copy = (
                await session.get(BranchRow, branch),
                await session.get(WorkingCopyRow, branch),
            )
            if row is None or copy is None:
                raise ResourceNotFoundError()
            row.archived, copy.version = archived, copy.version + 1
            return current.model_copy(update={"archived": archived, "version": copy.version})


def _patch(row: RevisionPatchRow) -> Patch:
    return Patch(
        id=row.id,
        branch_id=row.branch_id,
        base_revision_id=row.base_revision_id,
        document_ref=ContentRef.model_validate(row.document_ref),
        created_by=row.created_by,
    )
