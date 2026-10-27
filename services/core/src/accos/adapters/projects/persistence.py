"""Private SQLAlchemy models and scoped repositories for projects."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    select,
    tuple_,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.idempotency import SqlAlchemyIdempotencyStore
from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base, utc_now
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.cursors import decode_keyset, encode_keyset
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError
from accos.kernel.persistence import IdempotencyRecord, Page
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
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope


class ProjectRow(Base):
    """Private project aggregate row."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("identity_workspaces.id", name="fk_projects_workspace"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    settings: Mapped[dict[str, int]] = mapped_column(JSON_TYPE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_projects_status_valid"),
        CheckConstraint("version > 0", name="ck_projects_version_positive"),
        Index("ix_projects_workspace_status", "workspace_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class ArtifactRow(Base):
    """Private versioned artifact container row."""

    __tablename__ = "project_artifacts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_artifacts_project"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('chapter', 'world', 'character', 'timeline', 'document', 'other')",
            name="ck_artifacts_type_valid",
        ),
        CheckConstraint("current_revision >= 0", name="ck_artifacts_current_revision_non_negative"),
        CheckConstraint("version > 0", name="ck_artifacts_version_positive"),
        Index("ix_artifacts_workspace_project", "workspace_id", "project_id"),
        {"schema": SCHEMA_NAME},
    )


class ArtifactRevisionRow(Base):
    """Private immutable artifact-revision metadata row."""

    __tablename__ = "project_artifact_revisions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("project_artifacts.id", name="fk_artifact_revisions_artifact"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    branch_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    content_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="legacy_unverified", server_default="legacy_unverified"
    )
    document_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_TYPE, nullable=True)
    text_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_TYPE, nullable=True)
    editor_schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False, default="legacy", server_default="legacy"
    )
    working_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    document_epoch: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    client_change_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    request_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("artifact_id", "revision_number", name="uq_artifact_revisions_number"),
        UniqueConstraint(
            "artifact_id", "branch_id", "created_by", "client_change_id", name="uq_content_change"
        ),
        CheckConstraint("revision_number > 0", name="ck_artifact_revisions_number_positive"),
        CheckConstraint(
            "(content_reference IS NULL) = (content_hash IS NULL)",
            name="ck_artifact_revisions_content_pair",
        ),
        Index(
            "ix_artifact_revisions_scope",
            "workspace_id",
            "project_id",
            "artifact_id",
        ),
        {"schema": SCHEMA_NAME},
    )


MODEL_REGISTRY = (ProjectRow, ArtifactRow, ArtifactRevisionRow)


class SqlAlchemyProjectRepository:
    """Transactional project repository with mandatory workspace predicates."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def catalog(
        self,
        workspace_id: UUID,
        query: str,
        archived: bool,
        cursor: str | None,
        limit: int,
        hidden_ids: frozenset[UUID],
    ) -> tuple[tuple[Project, ...], str | None]:
        scope = f"projects:{workspace_id}:{archived}:{query}"
        predicates = [
            ProjectRow.workspace_id == workspace_id,
            ProjectRow.id.not_in(hidden_ids),
            ProjectRow.status == ("archived" if archived else "active"),
        ]
        if query:
            predicates.append(ProjectRow.name.icontains(query, autoescape=True))
        if cursor:
            moment, identifier = decode_keyset(cursor, scope)
            predicates.append(tuple_(ProjectRow.created_at, ProjectRow.id) < (moment, identifier))
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ProjectRow)
                    .where(*predicates)
                    .order_by(ProjectRow.created_at.desc(), ProjectRow.id.desc())
                    .limit(limit + 1)
                )
            ).all()
            next_cursor = (
                encode_keyset(rows[limit - 1].created_at, rows[limit - 1].id, scope)
                if len(rows) > limit
                else None
            )
            return tuple(_project(row) for row in rows[:limit]), next_cursor

    async def revise_project(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        name: str,
        archived: bool,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(ProjectRow)
                .where(
                    ProjectRow.workspace_id == workspace_id,
                    ProjectRow.id == project_id,
                    ProjectRow.version == expected_version,
                )
                .values(
                    name=name,
                    status="archived" if archived else "active",
                    archived_at=event.occurred_at if archived else None,
                    version=ProjectRow.version + 1,
                    updated_at=event.occurred_at,
                )
                .returning(ProjectRow)
            )
            if row is None:
                raise ConcurrencyConflictError()
            await SqlAlchemyOutboxWriter(session).append(event)
            return _project(row)

    async def create_idempotent(
        self,
        project: Project,
        *,
        idempotency_key: str,
        request_digest: str,
        event: EventEnvelope,
    ) -> tuple[Project, bool]:
        async with self._sessions.begin() as session:
            record, created = await SqlAlchemyIdempotencyStore(session).reserve(
                IdempotencyRecord(
                    event.id,
                    project.workspace_id,
                    project.id,
                    "projects.create",
                    idempotency_key,
                    request_digest,
                    str(project.id),
                    project.created_at + timedelta(days=1),
                )
            )
            if not created:
                row = await session.scalar(
                    select(ProjectRow).where(
                        ProjectRow.workspace_id == project.workspace_id,
                        ProjectRow.id == UUID(record.result_reference),
                    )
                )
                if row is None:
                    raise InvalidStateError("Idempotent project result is unavailable.")
                return _project(row), False
            session.add(_project_row(project))
            await SqlAlchemyOutboxWriter(session).append(event)
        return project, True

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ProjectRow).where(
                    ProjectRow.workspace_id == workspace_id,
                    ProjectRow.id == project_id,
                )
            )
        return None if row is None else _project(row)

    async def list_projects(
        self,
        workspace_id: UUID,
        page: PageRequest,
        *,
        status: ProjectStatus | None,
        sort: ProjectSort,
        hidden_ids: frozenset[UUID] = frozenset(),
    ) -> Page[Project]:
        predicates = [ProjectRow.workspace_id == workspace_id, ProjectRow.id.not_in(hidden_ids)]
        if status is not None:
            predicates.append(ProjectRow.status == status.value)
        order = {
            ProjectSort.CREATED_AT: (ProjectRow.created_at, ProjectRow.id),
            ProjectSort.CREATED_AT_DESC: (ProjectRow.created_at.desc(), ProjectRow.id.desc()),
            ProjectSort.NAME: (ProjectRow.name, ProjectRow.id),
            ProjectSort.NAME_DESC: (ProjectRow.name.desc(), ProjectRow.id.desc()),
        }[sort]
        async with self._sessions() as session:
            total = int(
                await session.scalar(
                    select(func.count()).select_from(ProjectRow).where(*predicates)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(ProjectRow)
                    .where(*predicates)
                    .order_by(*order)
                    .offset(page.offset)
                    .limit(page.limit)
                )
            ).all()
        return Page(tuple(_project(row) for row in rows), total, page)

    async def update_settings(
        self,
        workspace_id: UUID,
        project_id: UUID,
        settings: ProjectSettings,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(ProjectRow)
                .where(
                    ProjectRow.workspace_id == workspace_id,
                    ProjectRow.id == project_id,
                    ProjectRow.status == ProjectStatus.ACTIVE.value,
                    ProjectRow.version == expected_version,
                )
                .values(
                    settings=_settings_json(settings),
                    updated_at=event.occurred_at,
                    version=ProjectRow.version + 1,
                )
                .returning(ProjectRow)
            )
            if row is None:
                raise ConcurrencyConflictError
            await SqlAlchemyOutboxWriter(session).append(event)
            return _project(row)

    async def archive(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> Project:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(ProjectRow)
                .where(
                    ProjectRow.workspace_id == workspace_id,
                    ProjectRow.id == project_id,
                    ProjectRow.status == ProjectStatus.ACTIVE.value,
                    ProjectRow.version == expected_version,
                )
                .values(
                    status=ProjectStatus.ARCHIVED.value,
                    archived_at=event.occurred_at,
                    updated_at=event.occurred_at,
                    version=ProjectRow.version + 1,
                )
                .returning(ProjectRow)
            )
            if row is None:
                raise ConcurrencyConflictError
            await SqlAlchemyOutboxWriter(session).append(event)
            return _project(row)

    async def add_artifact(self, artifact: Artifact, event: EventEnvelope) -> None:
        async with self._sessions.begin() as session:
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    workspace_id=artifact.workspace_id,
                    project_id=artifact.project_id,
                    artifact_type=artifact.artifact_type.value,
                    label=artifact.label,
                    current_revision=artifact.current_revision,
                    created_by=artifact.created_by,
                    created_at=artifact.created_at,
                    updated_at=artifact.updated_at,
                    version=artifact.version,
                )
            )
            await SqlAlchemyOutboxWriter(session).append(event)

    async def get_artifact(
        self, workspace_id: UUID, project_id: UUID, artifact_id: UUID
    ) -> Artifact | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ArtifactRow).where(
                    ArtifactRow.workspace_id == workspace_id,
                    ArtifactRow.project_id == project_id,
                    ArtifactRow.id == artifact_id,
                )
            )
        return None if row is None else _artifact(row)

    async def list_artifacts(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        sort: ArtifactSort,
    ) -> Page[Artifact]:
        predicates = (
            ArtifactRow.workspace_id == workspace_id,
            ArtifactRow.project_id == project_id,
        )
        order = {
            ArtifactSort.CREATED_AT: (ArtifactRow.created_at, ArtifactRow.id),
            ArtifactSort.CREATED_AT_DESC: (ArtifactRow.created_at.desc(), ArtifactRow.id.desc()),
            ArtifactSort.LABEL: (ArtifactRow.label, ArtifactRow.id),
            ArtifactSort.LABEL_DESC: (ArtifactRow.label.desc(), ArtifactRow.id.desc()),
        }[sort]
        async with self._sessions() as session:
            total = int(
                await session.scalar(
                    select(func.count()).select_from(ArtifactRow).where(*predicates)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(ArtifactRow)
                    .where(*predicates)
                    .order_by(*order)
                    .offset(page.offset)
                    .limit(page.limit)
                )
            ).all()
        return Page(tuple(_artifact(row) for row in rows), total, page)

    async def list_revisions(
        self,
        workspace_id: UUID,
        project_id: UUID,
        artifact_id: UUID,
        page: PageRequest,
    ) -> Page[ArtifactRevision]:
        predicates = (
            ArtifactRevisionRow.workspace_id == workspace_id,
            ArtifactRevisionRow.project_id == project_id,
            ArtifactRevisionRow.artifact_id == artifact_id,
        )
        async with self._sessions() as session:
            total = int(
                await session.scalar(
                    select(func.count()).select_from(ArtifactRevisionRow).where(*predicates)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(ArtifactRevisionRow)
                    .where(*predicates)
                    .order_by(
                        ArtifactRevisionRow.revision_number.desc(),
                        ArtifactRevisionRow.id.desc(),
                    )
                    .offset(page.offset)
                    .limit(page.limit)
                )
            ).all()
        return Page(tuple(_revision(row) for row in rows), total, page)

    async def add_revision(
        self,
        artifact: Artifact,
        revision: ArtifactRevision,
        *,
        expected_version: int,
        event: EventEnvelope,
    ) -> tuple[Artifact, ArtifactRevision]:
        from accos.adapters.projects.content import WorkingCopyRow

        async with self._sessions.begin() as session:
            # Use the same lock order as content commits. Once a document has a
            # working copy, the legacy metadata endpoint cannot become a second
            # write channel or bypass its document epoch.
            await session.scalar(
                select(ProjectRow)
                .where(
                    ProjectRow.workspace_id == artifact.workspace_id,
                    ProjectRow.id == artifact.project_id,
                )
                .with_for_update()
            )
            await session.scalar(
                select(ArtifactRow)
                .where(
                    ArtifactRow.workspace_id == artifact.workspace_id,
                    ArtifactRow.id == artifact.id,
                )
                .with_for_update()
            )
            if (
                await session.scalar(
                    select(WorkingCopyRow.branch_id)
                    .where(
                        WorkingCopyRow.artifact_id == artifact.id,
                        WorkingCopyRow.workspace_id == artifact.workspace_id,
                    )
                    .limit(1)
                )
                is not None
            ):
                raise InvalidStateError("Use the working-copy endpoint for versioned content.")
            row = await session.scalar(
                update(ArtifactRow)
                .where(
                    ArtifactRow.workspace_id == artifact.workspace_id,
                    ArtifactRow.project_id == artifact.project_id,
                    ArtifactRow.id == artifact.id,
                    ArtifactRow.version == expected_version,
                )
                .values(
                    current_revision=artifact.current_revision,
                    updated_at=artifact.updated_at,
                    version=ArtifactRow.version + 1,
                )
                .returning(ArtifactRow)
            )
            if row is None:
                raise ConcurrencyConflictError
            session.add(
                ArtifactRevisionRow(
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
            )
            await SqlAlchemyOutboxWriter(session).append(event)
            return _artifact(row), revision


def _settings_json(settings: ProjectSettings) -> dict[str, int]:
    return {
        "revision_retention_limit": settings.revision_retention_limit,
        "asset_retention_days": settings.asset_retention_days,
    }


def _project_row(project: Project) -> ProjectRow:
    return ProjectRow(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        status=project.status.value,
        settings=_settings_json(project.settings),
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
        version=project.version,
    )


def _project(row: ProjectRow) -> Project:
    return Project(
        row.id,
        row.workspace_id,
        row.name,
        ProjectStatus(row.status),
        ProjectSettings(**row.settings),
        row.created_by,
        row.created_at,
        row.updated_at,
        row.version,
        row.archived_at,
    )


def _artifact(row: ArtifactRow) -> Artifact:
    return Artifact(
        row.id,
        row.workspace_id,
        row.project_id,
        ArtifactType(row.artifact_type),
        row.label,
        row.created_by,
        row.created_at,
        row.updated_at,
        row.current_revision,
        row.version,
    )


def _revision(row: ArtifactRevisionRow) -> ArtifactRevision:
    return ArtifactRevision(
        row.id,
        row.workspace_id,
        row.project_id,
        row.artifact_id,
        row.revision_number,
        row.content_reference,
        row.content_hash,
        row.created_by,
        row.created_at,
    )
