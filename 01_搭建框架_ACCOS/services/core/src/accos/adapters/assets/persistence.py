"""Private SQLAlchemy asset models and compensation-aware repository."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - resolved by SQLAlchemy.
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - resolved by SQLAlchemy.

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import SCHEMA_NAME, Base, utc_now
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.cursors import decode_keyset, encode_keyset
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError
from accos.kernel.persistence import Page
from accos.modules.assets.domain import (
    Asset,
    AssetSort,
    AssetStatus,
    AssetVersion,
    ProcessingStatus,
    ScanStatus,
    UploadSession,
    UploadStatus,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.contracts import PageRequest
    from accos.kernel.events import EventEnvelope


class AssetRow(Base):
    """Private logical asset row."""

    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_assets_project"),
        nullable=False,
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    deletion_marked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("status IN ('active', 'pending_deletion')", name="ck_assets_status_valid"),
        CheckConstraint("current_version > 0", name="ck_assets_current_version_positive"),
        CheckConstraint("version > 0", name="ck_assets_version_positive"),
        CheckConstraint(
            "(status = 'pending_deletion') = "
            "(deletion_marked_at IS NOT NULL AND retention_until IS NOT NULL)",
            name="ck_assets_deletion_lifecycle",
        ),
        Index("ix_assets_workspace_project", "workspace_id", "project_id"),
        {"schema": SCHEMA_NAME},
    )


class AssetVersionRow(Base):
    """Private immutable object metadata plus mutable diagnosis state."""

    __tablename__ = "asset_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("assets.id", name="fk_asset_versions_asset"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(30), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("asset_id", "version_number", name="uq_asset_versions_number"),
        Index(
            "ix_asset_versions_project_hash",
            "workspace_id",
            "project_id",
            "content_hash",
        ),
        CheckConstraint("version_number > 0", name="ck_asset_versions_number_positive"),
        CheckConstraint("size_bytes >= 0", name="ck_asset_versions_size_positive"),
        CheckConstraint(
            "scan_status IN ('not_configured', 'clean', 'rejected', 'failed')",
            name="ck_asset_versions_scan_status_valid",
        ),
        CheckConstraint(
            "processing_status IN ('available', 'missing_object')",
            name="ck_asset_versions_processing_status_valid",
        ),
        Index("ix_asset_versions_scope", "workspace_id", "project_id", "asset_id"),
        {"schema": SCHEMA_NAME},
    )


class UploadSessionRow(Base):
    """Durable checkpoint capable of diagnosing object/database partial failure."""

    __tablename__ = "asset_upload_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_upload_sessions_size_positive"),
        CheckConstraint("version_number > 0", name="ck_upload_sessions_version_number_positive"),
        CheckConstraint("version > 0", name="ck_upload_sessions_version_positive"),
        CheckConstraint(
            "scan_status IN ('not_configured', 'clean', 'rejected', 'failed')",
            name="ck_upload_sessions_scan_status_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'object_stored', 'completed', 'failed', "
            "'compensation_required')",
            name="ck_upload_sessions_status_valid",
        ),
        Index("ix_upload_sessions_scope_status", "workspace_id", "status"),
        {"schema": SCHEMA_NAME},
    )


MODEL_REGISTRY = (AssetRow, AssetVersionRow, UploadSessionRow)


class SqlAlchemyAssetRepository:
    """Asset persistence with separate checkpoints around object writes."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def get_version(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID, version_id: UUID
    ) -> AssetVersion | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AssetVersionRow).where(
                    AssetVersionRow.workspace_id == workspace_id,
                    AssetVersionRow.project_id == project_id,
                    AssetVersionRow.asset_id == asset_id,
                    AssetVersionRow.id == version_id,
                )
            )
            return None if row is None else _version(row)

    async def versions(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID, before: int | None, limit: int
    ) -> tuple[AssetVersion, ...]:
        predicates = [
            AssetVersionRow.workspace_id == workspace_id,
            AssetVersionRow.project_id == project_id,
            AssetVersionRow.asset_id == asset_id,
        ]
        if before is not None:
            predicates.append(AssetVersionRow.version_number < before)
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AssetVersionRow)
                    .where(*predicates)
                    .order_by(AssetVersionRow.version_number.desc())
                    .limit(limit)
                )
            ).all()
            return tuple(_version(row) for row in rows)

    async def catalog(
        self, workspace_id: UUID, project_id: UUID, query: str, cursor: str | None, limit: int
    ) -> tuple[tuple[tuple[Asset, AssetVersion], ...], str | None]:
        scope = f"assets:{workspace_id}:{project_id}:{query}"
        predicates = [AssetRow.workspace_id == workspace_id, AssetRow.project_id == project_id]
        if query:
            predicates.append(AssetRow.filename.icontains(query, autoescape=True))
        if cursor:
            moment, identifier = decode_keyset(cursor, scope)
            predicates.append(tuple_(AssetRow.created_at, AssetRow.id) < (moment, identifier))
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(AssetRow, AssetVersionRow)
                    .join(
                        AssetVersionRow,
                        (AssetVersionRow.asset_id == AssetRow.id)
                        & (AssetVersionRow.version_number == AssetRow.current_version),
                    )
                    .where(*predicates)
                    .order_by(AssetRow.created_at.desc(), AssetRow.id.desc())
                    .limit(limit + 1)
                )
            ).all()
            next_cursor = (
                encode_keyset(rows[limit - 1][0].created_at, rows[limit - 1][0].id, scope)
                if len(rows) > limit
                else None
            )
            return tuple((_asset(a), _version(v)) for a, v in rows[:limit]), next_cursor

    async def find_version_by_hash(
        self, workspace_id: UUID, project_id: UUID, content_hash: str
    ) -> tuple[Asset, AssetVersion] | None:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(AssetRow, AssetVersionRow)
                    .join(AssetVersionRow, AssetVersionRow.asset_id == AssetRow.id)
                    .where(
                        AssetRow.workspace_id == workspace_id,
                        AssetRow.project_id == project_id,
                        AssetRow.status == AssetStatus.ACTIVE.value,
                        AssetVersionRow.content_hash == content_hash,
                    )
                    .order_by(AssetVersionRow.created_at, AssetVersionRow.id)
                    .limit(1)
                )
            ).one_or_none()
        return None if row is None else (_asset(row[0]), _version(row[1]))

    async def begin_upload(self, session: UploadSession) -> None:
        async with self._sessions.begin() as db:
            db.add(_upload_row(session))

    async def update_upload_status(
        self,
        workspace_id: UUID,
        upload_id: UUID,
        status: str,
        *,
        updated_at: datetime,
        error_code: str | None = None,
    ) -> UploadSession:
        selected = UploadStatus(status)
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(UploadSessionRow)
                .where(
                    UploadSessionRow.workspace_id == workspace_id,
                    UploadSessionRow.id == upload_id,
                    or_(
                        UploadSessionRow.error_code.is_(None),
                        UploadSessionRow.error_code != "orphan_collected",
                    ),
                )
                .values(
                    status=selected.value,
                    updated_at=updated_at,
                    error_code=None if error_code is None else error_code[:100],
                    version=UploadSessionRow.version + 1,
                )
                .returning(UploadSessionRow)
            )
            if row is None:
                raise InvalidStateError("Upload session is unavailable.")
            return _upload(row)

    async def finalize_upload(
        self,
        upload: UploadSession,
        asset: Asset,
        version: AssetVersion,
        event: EventEnvelope,
    ) -> tuple[Asset, AssetVersion, UploadSession]:
        async with self._sessions.begin() as session:
            upload_row = await session.scalar(
                select(UploadSessionRow)
                .where(
                    UploadSessionRow.workspace_id == upload.workspace_id,
                    UploadSessionRow.id == upload.id,
                )
                .with_for_update()
            )
            if upload_row is not None and upload_row.status == UploadStatus.COMPLETED.value:
                previous = await session.get(AssetVersionRow, upload.asset_version_id)
                current = await session.get(AssetRow, upload.asset_id)
                if previous is not None and current is not None:
                    return _asset(current), _version(previous), _upload(upload_row)
            if upload_row is None or upload_row.status not in {
                UploadStatus.OBJECT_STORED.value,
                UploadStatus.COMPENSATION_REQUIRED.value,
            }:
                raise InvalidStateError("Upload is not ready for metadata finalization.")
            if version.version_number == 1:
                session.add(_asset_row(asset))
            else:
                asset_row = await session.scalar(
                    update(AssetRow)
                    .where(
                        AssetRow.workspace_id == asset.workspace_id,
                        AssetRow.project_id == asset.project_id,
                        AssetRow.id == asset.id,
                        AssetRow.status == AssetStatus.ACTIVE.value,
                        AssetRow.current_version == version.version_number - 1,
                    )
                    .values(
                        current_version=version.version_number,
                        updated_at=asset.updated_at,
                        version=AssetRow.version + 1,
                    )
                    .returning(AssetRow)
                )
                if asset_row is None:
                    raise ConcurrencyConflictError
                asset = _asset(asset_row)
            session.add(_version_row(version))
            upload_row.status = UploadStatus.COMPLETED.value
            upload_row.error_code = None
            upload_row.updated_at = event.occurred_at
            await SqlAlchemyOutboxWriter(session).append(event)
            await session.flush()
            return asset, version, _upload(upload_row)

    async def get_upload(self, workspace_id: UUID, upload_id: UUID) -> UploadSession | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(UploadSessionRow).where(
                    UploadSessionRow.workspace_id == workspace_id,
                    UploadSessionRow.id == upload_id,
                )
            )
        return None if row is None else _upload(row)

    async def get(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID
    ) -> tuple[Asset, AssetVersion] | None:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(AssetRow, AssetVersionRow)
                    .join(
                        AssetVersionRow,
                        (AssetVersionRow.asset_id == AssetRow.id)
                        & (AssetVersionRow.version_number == AssetRow.current_version),
                    )
                    .where(
                        AssetRow.workspace_id == workspace_id,
                        AssetRow.project_id == project_id,
                        AssetRow.id == asset_id,
                    )
                )
            ).one_or_none()
        return None if row is None else (_asset(row[0]), _version(row[1]))

    async def list_assets(
        self,
        workspace_id: UUID,
        project_id: UUID,
        page: PageRequest,
        *,
        status: AssetStatus | None,
        sort: AssetSort,
    ) -> Page[tuple[Asset, AssetVersion]]:
        predicates = [
            AssetRow.workspace_id == workspace_id,
            AssetRow.project_id == project_id,
        ]
        if status is not None:
            predicates.append(AssetRow.status == status.value)
        order = {
            AssetSort.CREATED_AT: (AssetRow.created_at, AssetRow.id),
            AssetSort.CREATED_AT_DESC: (AssetRow.created_at.desc(), AssetRow.id.desc()),
            AssetSort.FILENAME: (AssetRow.filename, AssetRow.id),
            AssetSort.FILENAME_DESC: (AssetRow.filename.desc(), AssetRow.id.desc()),
        }[sort]
        current = AssetVersionRow.version_number == AssetRow.current_version
        async with self._sessions() as session:
            total = int(
                await session.scalar(select(func.count()).select_from(AssetRow).where(*predicates))
                or 0
            )
            rows = (
                await session.execute(
                    select(AssetRow, AssetVersionRow)
                    .join(AssetVersionRow, (AssetVersionRow.asset_id == AssetRow.id) & current)
                    .where(*predicates)
                    .order_by(*order)
                    .offset(page.offset)
                    .limit(page.limit)
                )
            ).all()
        return Page(tuple((_asset(row[0]), _version(row[1])) for row in rows), total, page)

    async def set_processing_status(
        self,
        workspace_id: UUID,
        version_id: UUID,
        status: str,
        *,
        updated_at: datetime,
    ) -> AssetVersion:
        selected = ProcessingStatus(status)
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(AssetVersionRow)
                .where(
                    AssetVersionRow.workspace_id == workspace_id,
                    AssetVersionRow.id == version_id,
                )
                .values(processing_status=selected.value, updated_at=updated_at)
                .returning(AssetVersionRow)
            )
            if row is None:
                raise InvalidStateError("Asset version is unavailable.")
            return _version(row)

    async def mark_for_deletion(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        *,
        expected_version: int,
        marked_at: datetime,
        retention_until: datetime,
        event: EventEnvelope,
    ) -> Asset:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(AssetRow)
                .where(
                    AssetRow.workspace_id == workspace_id,
                    AssetRow.project_id == project_id,
                    AssetRow.id == asset_id,
                    AssetRow.status == AssetStatus.ACTIVE.value,
                    AssetRow.version == expected_version,
                )
                .values(
                    status=AssetStatus.PENDING_DELETION.value,
                    deletion_marked_at=marked_at,
                    retention_until=retention_until,
                    updated_at=marked_at,
                    version=AssetRow.version + 1,
                )
                .returning(AssetRow)
            )
            if row is None:
                raise ConcurrencyConflictError
            await SqlAlchemyOutboxWriter(session).append(event)
            return _asset(row)


def _asset_row(asset: Asset) -> AssetRow:
    return AssetRow(
        id=asset.id,
        workspace_id=asset.workspace_id,
        project_id=asset.project_id,
        owner_id=asset.owner_id,
        filename=asset.filename,
        source=asset.source,
        status=asset.status.value,
        current_version=asset.current_version,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        deletion_marked_at=asset.deletion_marked_at,
        retention_until=asset.retention_until,
        version=asset.version,
    )


def _version_row(version: AssetVersion) -> AssetVersionRow:
    return AssetVersionRow(
        id=version.id,
        workspace_id=version.workspace_id,
        project_id=version.project_id,
        asset_id=version.asset_id,
        version_number=version.version_number,
        object_key=version.object_key,
        content_hash=version.content_hash,
        media_type=version.media_type,
        size_bytes=version.size_bytes,
        scan_status=version.scan_status.value,
        processing_status=version.processing_status.value,
        created_by=version.created_by,
        created_at=version.created_at,
        updated_at=version.created_at,
    )


def _upload_row(upload: UploadSession) -> UploadSessionRow:
    return UploadSessionRow(
        id=upload.id,
        workspace_id=upload.workspace_id,
        project_id=upload.project_id,
        asset_id=upload.asset_id,
        asset_version_id=upload.asset_version_id,
        version_number=upload.version_number,
        owner_id=upload.owner_id,
        filename=upload.filename,
        source=upload.source,
        object_key=upload.object_key,
        content_hash=upload.content_hash,
        media_type=upload.media_type,
        size_bytes=upload.size_bytes,
        scan_status=upload.scan_status.value,
        status=upload.status.value,
        error_code=upload.error_code,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
    )


def _asset(row: AssetRow) -> Asset:
    return Asset(
        row.id,
        row.workspace_id,
        row.project_id,
        row.owner_id,
        row.filename,
        row.source,
        AssetStatus(row.status),
        row.current_version,
        row.created_at,
        row.updated_at,
        row.deletion_marked_at,
        row.retention_until,
        row.version,
    )


def _version(row: AssetVersionRow) -> AssetVersion:
    return AssetVersion(
        row.id,
        row.workspace_id,
        row.project_id,
        row.asset_id,
        row.version_number,
        row.object_key,
        row.content_hash,
        row.media_type,
        row.size_bytes,
        ScanStatus(row.scan_status),
        ProcessingStatus(row.processing_status),
        row.created_by,
        row.created_at,
    )


def _upload(row: UploadSessionRow) -> UploadSession:
    return UploadSession(
        row.id,
        row.workspace_id,
        row.project_id,
        row.asset_id,
        row.asset_version_id,
        row.version_number,
        row.owner_id,
        row.filename,
        row.source,
        row.object_key,
        row.content_hash,
        row.media_type,
        row.size_bytes,
        ScanStatus(row.scan_status),
        UploadStatus(row.status),
        row.created_at,
        row.updated_at,
        row.error_code,
    )
