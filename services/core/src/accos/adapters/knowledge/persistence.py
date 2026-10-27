"""Private SQLAlchemy knowledge models and strictly scoped repository."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves this annotation.
from typing import TYPE_CHECKING
from uuid import UUID, uuid4, uuid5

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    delete,
    select,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.kernel.errors import IdempotencyConflictError, InvalidStateError
from accos.modules.knowledge.domain import (
    Chunk,
    Citation,
    Document,
    DocumentVersion,
    EmbeddingRef,
    IngestionBundle,
    IngestionRun,
    IngestionStatus,
    KnowledgeErrorCode,
    KnowledgeSource,
    RetrievalFilter,
    VerificationPolicy,
    VerificationStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.modules.knowledge.ports import SourceSnapshot


class Vector8(UserDefinedType[str]):
    """Portable vector base type; migration adds vector(8) on native pgvector."""

    cache_ok = True

    def get_col_spec(self, **_kw: object) -> str:
        return "vector"


class KnowledgeSourceRow(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_knowledge_sources_project"), nullable=False
    )
    asset_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    content_locator: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "asset_version_id",
            name="uq_knowledge_sources_asset_version",
        ),
        CheckConstraint("asset_version_number > 0", name="ck_knowledge_sources_version_positive"),
        Index("ix_knowledge_sources_scope_asset", "workspace_id", "project_id", "asset_id"),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeDocumentRow(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_knowledge_documents_project"), nullable=False
    )
    asset_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "project_id", "asset_id", name="uq_knowledge_documents_asset"
        ),
        Index("ix_knowledge_documents_scope", "workspace_id", "project_id"),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeDocumentVersionRow(Base):
    __tablename__ = "knowledge_document_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_documents.id", name="fk_knowledge_versions_document"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", name="fk_knowledge_versions_source"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_knowledge_versions_number"),
        UniqueConstraint("source_id", name="uq_knowledge_versions_source"),
        CheckConstraint("version_number > 0", name="ck_knowledge_versions_number_positive"),
        CheckConstraint(
            "status IN ('uploaded', 'extracting', 'normalized', 'chunked', 'embedded', "
            "'indexed', 'verifying', 'ready', 'failed')",
            name="ck_knowledge_versions_status_valid",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'not_configured', 'rejected')",
            name="ck_knowledge_versions_verification_valid",
        ),
        Index(
            "ix_knowledge_versions_scope_ready",
            "workspace_id",
            "project_id",
            "active",
            "status",
        ),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeChunkRow(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", name="fk_knowledge_chunks_source"),
        nullable=False,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "knowledge_document_versions.id",
            name="fk_knowledge_chunks_version",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_version_id", "ordinal", name="uq_knowledge_chunks_version_ordinal"
        ),
        CheckConstraint("ordinal >= 0", name="ck_knowledge_chunks_ordinal_non_negative"),
        Index(
            "ix_knowledge_chunks_scope_version", "workspace_id", "project_id", "document_version_id"
        ),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeEmbeddingRefRow(Base):
    __tablename__ = "knowledge_embedding_refs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_chunks.id", name="fk_knowledge_embeddings_chunk", ondelete="CASCADE"),
        nullable=False,
    )
    document_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    embedder_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_payload: Mapped[list[float]] = mapped_column(JSON_TYPE, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("chunk_id", "embedder_id", name="uq_knowledge_embeddings_chunk_model"),
        CheckConstraint("dimensions > 0", name="ck_knowledge_embeddings_dimensions_positive"),
        Index(
            "ix_knowledge_embeddings_scope_version",
            "workspace_id",
            "project_id",
            "document_version_id",
        ),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeVectorRow(Base):
    __tablename__ = "knowledge_vector_index"

    embedding_ref_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "knowledge_embedding_refs.id",
            name="fk_knowledge_vectors_embedding",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    embedding: Mapped[str] = mapped_column(Vector8(), nullable=False)

    __table_args__ = (
        Index(
            "ix_knowledge_vectors_scope_version",
            "workspace_id",
            "project_id",
            "document_version_id",
        ),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeCitationRow(Base):
    __tablename__ = "knowledge_citations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", name="fk_knowledge_citations_source"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_documents.id", name="fk_knowledge_citations_document"),
        nullable=False,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_document_versions.id", name="fk_knowledge_citations_version"),
        nullable=False,
    )
    asset_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    asset_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_chunks.id", name="fk_knowledge_citations_chunk", ondelete="CASCADE"),
        nullable=False,
    )
    locator: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_knowledge_citations_chunk_id"),
        Index("ix_knowledge_citations_scope_chunk", "workspace_id", "project_id", "chunk_id"),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeEdgeRow(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    from_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    from_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    relation: Mapped[str] = mapped_column(String(40), nullable=False)
    to_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    to_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "from_kind",
            "from_id",
            "relation",
            "to_kind",
            "to_id",
            name="uq_knowledge_edges_relation",
        ),
        CheckConstraint(
            "relation IN ('source_of', 'contains', 'cites', 'derived_from')",
            name="ck_knowledge_edges_relation_valid",
        ),
        Index(
            "ix_knowledge_edges_scope_version", "workspace_id", "project_id", "document_version_id"
        ),
        {"schema": SCHEMA_NAME},
    )


class KnowledgeIngestionRunRow(Base):
    __tablename__ = "knowledge_ingestion_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", name="fk_knowledge_runs_source"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_documents.id", name="fk_knowledge_runs_document"),
        nullable=False,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_document_versions.id", name="fk_knowledge_runs_version"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    verification_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", name="fk_knowledge_runs_workflow"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_knowledge_runs_idempotency"),
        UniqueConstraint("source_id", name="uq_knowledge_runs_source"),
        CheckConstraint("attempt > 0", name="ck_knowledge_runs_attempt_positive"),
        CheckConstraint("version > 0", name="ck_knowledge_runs_version_positive"),
        CheckConstraint(
            "status IN ('uploaded', 'extracting', 'normalized', 'chunked', 'embedded', "
            "'indexed', 'verifying', 'ready', 'failed')",
            name="ck_knowledge_runs_status_valid",
        ),
        CheckConstraint(
            "verification_policy IN ('not_required', 'required')",
            name="ck_knowledge_runs_policy_valid",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'not_configured', 'rejected')",
            name="ck_knowledge_runs_verification_valid",
        ),
        CheckConstraint(
            "(status = 'failed') = (failed_stage IS NOT NULL AND error_code IS NOT NULL)",
            name="ck_knowledge_runs_failure_details",
        ),
        Index("ix_knowledge_runs_scope_status", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


MODEL_REGISTRY = (
    KnowledgeSourceRow,
    KnowledgeDocumentRow,
    KnowledgeDocumentVersionRow,
    KnowledgeChunkRow,
    KnowledgeEmbeddingRefRow,
    KnowledgeVectorRow,
    KnowledgeCitationRow,
    KnowledgeEdgeRow,
    KnowledgeIngestionRunRow,
)


class SqlAlchemyKnowledgeRepository:
    """Transactional knowledge state with idempotent projection replacement."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def reserve(  # noqa: PLR0913
        self,
        snapshot: SourceSnapshot,
        *,
        verification_policy: VerificationPolicy,
        idempotency_key: str,
        requested_by: UUID,
        correlation_id: UUID,
        now: datetime,
    ) -> tuple[IngestionRun, bool]:
        async with self._sessions.begin() as session:
            keyed = await session.scalar(
                select(KnowledgeIngestionRunRow).where(
                    KnowledgeIngestionRunRow.workspace_id == snapshot.workspace_id,
                    KnowledgeIngestionRunRow.idempotency_key == idempotency_key,
                )
            )
            if keyed is not None:
                source = await session.get(KnowledgeSourceRow, keyed.source_id)
                if (
                    source is None
                    or source.asset_version_id != snapshot.asset_version_id
                    or keyed.verification_policy != verification_policy.value
                ):
                    raise IdempotencyConflictError
                return _run(keyed), False
            existing_source = await session.scalar(
                select(KnowledgeSourceRow).where(
                    KnowledgeSourceRow.workspace_id == snapshot.workspace_id,
                    KnowledgeSourceRow.project_id == snapshot.project_id,
                    KnowledgeSourceRow.asset_version_id == snapshot.asset_version_id,
                )
            )
            if existing_source is not None:
                existing_run = await session.scalar(
                    select(KnowledgeIngestionRunRow).where(
                        KnowledgeIngestionRunRow.source_id == existing_source.id
                    )
                )
                if existing_run is None:
                    raise InvalidStateError("Knowledge source has no ingestion run.")
                if existing_run.verification_policy != verification_policy.value:
                    raise IdempotencyConflictError
                return _run(existing_run), False
            document = await session.scalar(
                select(KnowledgeDocumentRow).where(
                    KnowledgeDocumentRow.workspace_id == snapshot.workspace_id,
                    KnowledgeDocumentRow.project_id == snapshot.project_id,
                    KnowledgeDocumentRow.asset_id == snapshot.asset_id,
                )
            )
            if document is None:
                document = KnowledgeDocumentRow(
                    id=uuid4(),
                    workspace_id=snapshot.workspace_id,
                    project_id=snapshot.project_id,
                    asset_id=snapshot.asset_id,
                    created_at=now,
                )
                session.add(document)
            source_id, version_id, run_id = uuid4(), uuid4(), uuid4()
            source = KnowledgeSourceRow(
                id=source_id,
                workspace_id=snapshot.workspace_id,
                project_id=snapshot.project_id,
                asset_id=snapshot.asset_id,
                asset_version_id=snapshot.asset_version_id,
                asset_version_number=snapshot.version_number,
                content_hash=snapshot.content_hash,
                media_type=snapshot.media_type,
                content_locator=snapshot.object_key,
                created_at=now,
            )
            version = KnowledgeDocumentVersionRow(
                id=version_id,
                workspace_id=snapshot.workspace_id,
                project_id=snapshot.project_id,
                document_id=document.id,
                source_id=source_id,
                version_number=snapshot.version_number,
                content_hash=snapshot.content_hash,
                normalized_text=None,
                status=IngestionStatus.UPLOADED.value,
                verification_status=VerificationStatus.NOT_CONFIGURED.value,
                active=False,
                created_at=now,
                updated_at=now,
            )
            run = KnowledgeIngestionRunRow(
                id=run_id,
                workspace_id=snapshot.workspace_id,
                project_id=snapshot.project_id,
                source_id=source_id,
                document_id=document.id,
                document_version_id=version_id,
                status=IngestionStatus.UPLOADED.value,
                verification_policy=verification_policy.value,
                verification_status=VerificationStatus.NOT_CONFIGURED.value,
                idempotency_key=idempotency_key,
                requested_by=requested_by,
                correlation_id=correlation_id,
                attempt=1,
                failed_stage=None,
                error_code=None,
                retryable=False,
                workflow_run_id=None,
                created_at=now,
                updated_at=now,
                version=1,
            )
            # These mappers intentionally expose no cross-aggregate ORM relationships.
            # Flush each FK layer explicitly so correctness does not depend on mapper
            # insertion order while all records still commit atomically.
            session.add(source)
            await session.flush()
            session.add(version)
            await session.flush()
            session.add(run)
            await session.flush()
            return _run(run), True

    async def load(self, workspace_id: UUID, run_id: UUID) -> IngestionBundle | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(KnowledgeIngestionRunRow).where(
                    KnowledgeIngestionRunRow.workspace_id == workspace_id,
                    KnowledgeIngestionRunRow.id == run_id,
                )
            )
            if row is None:
                return None
            source = await session.get(KnowledgeSourceRow, row.source_id)
            document = await session.get(KnowledgeDocumentRow, row.document_id)
            version = await session.get(KnowledgeDocumentVersionRow, row.document_version_id)
            if source is None or document is None or version is None:
                raise InvalidStateError("Knowledge ingestion aggregate is incomplete.")
            chunks = tuple(
                _chunk(item)
                for item in (
                    await session.scalars(
                        select(KnowledgeChunkRow)
                        .where(
                            KnowledgeChunkRow.workspace_id == workspace_id,
                            KnowledgeChunkRow.document_version_id == version.id,
                        )
                        .order_by(KnowledgeChunkRow.ordinal)
                    )
                ).all()
            )
            embeddings = tuple(
                _embedding(item)
                for item in (
                    await session.scalars(
                        select(KnowledgeEmbeddingRefRow)
                        .where(
                            KnowledgeEmbeddingRefRow.workspace_id == workspace_id,
                            KnowledgeEmbeddingRefRow.document_version_id == version.id,
                        )
                        .order_by(KnowledgeEmbeddingRefRow.chunk_id)
                    )
                ).all()
            )
            return IngestionBundle(
                _run(row),
                _source(source),
                _document(document),
                _document_version(version),
                chunks,
                embeddings,
            )

    async def get_document(
        self, workspace_id: UUID, project_id: UUID, document_id: UUID
    ) -> Document | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(KnowledgeDocumentRow).where(
                    KnowledgeDocumentRow.workspace_id == workspace_id,
                    KnowledgeDocumentRow.project_id == project_id,
                    KnowledgeDocumentRow.id == document_id,
                )
            )
        return None if row is None else _document(row)

    async def set_status(
        self,
        workspace_id: UUID,
        run_id: UUID,
        status: str,
        *,
        now: datetime,
    ) -> IngestionRun:
        selected = IngestionStatus(status)
        allowed = {
            IngestionStatus.UPLOADED: IngestionStatus.EXTRACTING,
            IngestionStatus.EMBEDDED: IngestionStatus.INDEXED,
            IngestionStatus.INDEXED: IngestionStatus.VERIFYING,
        }
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if allowed.get(IngestionStatus(row.status)) is not selected:
                raise InvalidStateError("Knowledge ingestion transition is invalid.")
            _advance(row, version, selected, now)
            await session.flush()
            return _run(row)

    async def save_normalized(
        self,
        workspace_id: UUID,
        run_id: UUID,
        text: str,
        *,
        now: datetime,
    ) -> IngestionRun:
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if row.status != IngestionStatus.EXTRACTING.value:
                raise InvalidStateError("Knowledge extraction checkpoint is invalid.")
            version.normalized_text = text
            _advance(row, version, IngestionStatus.NORMALIZED, now)
            await session.flush()
            return _run(row)

    async def replace_chunks(
        self,
        workspace_id: UUID,
        run_id: UUID,
        chunks: tuple[Chunk, ...],
        *,
        now: datetime,
    ) -> IngestionRun:
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if row.status != IngestionStatus.NORMALIZED.value:
                raise InvalidStateError("Knowledge chunk checkpoint is invalid.")
            source = await session.get(KnowledgeSourceRow, row.source_id)
            if source is None or any(
                item.workspace_id != workspace_id
                or item.project_id != row.project_id
                or item.document_version_id != version.id
                for item in chunks
            ):
                raise InvalidStateError("Knowledge chunks do not match the ingestion scope.")
            await _delete_chunk_projection(session, version.id)
            session.add_all(_chunk_row(item) for item in chunks)
            session.add_all(
                KnowledgeCitationRow(
                    id=uuid5(chunk.id, "citation"),
                    workspace_id=workspace_id,
                    project_id=row.project_id,
                    source_id=source.id,
                    document_id=row.document_id,
                    document_version_id=version.id,
                    asset_id=source.asset_id,
                    asset_version_id=source.asset_version_id,
                    chunk_id=chunk.id,
                    locator=f"asset-version://{source.asset_version_id}#chunk={chunk.ordinal}",
                )
                for chunk in chunks
            )
            _advance(row, version, IngestionStatus.CHUNKED, now)
            await session.flush()
            return _run(row)

    async def replace_embeddings(
        self,
        workspace_id: UUID,
        run_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
        *,
        now: datetime,
    ) -> IngestionRun:
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if row.status != IngestionStatus.CHUNKED.value or any(
                item.workspace_id != workspace_id
                or item.project_id != row.project_id
                or item.document_version_id != version.id
                for item in embeddings
            ):
                raise InvalidStateError("Knowledge embeddings do not match the checkpoint.")
            await _delete_embeddings(session, version.id)
            session.add_all(_embedding_row(item) for item in embeddings)
            _advance(row, version, IngestionStatus.EMBEDDED, now)
            await session.flush()
            return _run(row)

    async def complete(
        self,
        workspace_id: UUID,
        run_id: UUID,
        verification_status: VerificationStatus,
        *,
        now: datetime,
    ) -> IngestionRun:
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if row.status != IngestionStatus.VERIFYING.value:
                raise InvalidStateError("Knowledge verification checkpoint is invalid.")
            if (
                row.verification_policy == VerificationPolicy.REQUIRED.value
                and verification_status is not VerificationStatus.VERIFIED
            ):
                raise InvalidStateError("Required knowledge verification did not pass.")
            await session.execute(
                update(KnowledgeDocumentVersionRow)
                .where(
                    KnowledgeDocumentVersionRow.workspace_id == workspace_id,
                    KnowledgeDocumentVersionRow.document_id == row.document_id,
                    KnowledgeDocumentVersionRow.id != version.id,
                )
                .values(active=False)
            )
            row.verification_status = verification_status.value
            version.verification_status = verification_status.value
            version.active = True
            _advance(row, version, IngestionStatus.READY, now)
            await session.flush()
            return _run(row)

    async def fail(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        failed_stage: str,
        error_code: str,
        retryable: bool,
        now: datetime,
    ) -> IngestionRun:
        stage = IngestionStatus(failed_stage)
        code = KnowledgeErrorCode(error_code)
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            row.status = IngestionStatus.FAILED.value
            row.failed_stage = stage.value
            row.error_code = code.value
            row.retryable = retryable
            row.updated_at = now
            row.version += 1
            version.status = IngestionStatus.FAILED.value
            version.updated_at = now
            await session.flush()
            return _run(row)

    async def restart(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        rebuild: bool,
        now: datetime,
    ) -> IngestionRun:
        async with self._sessions.begin() as session:
            row, version = await _locked(session, workspace_id, run_id)
            if not rebuild and row.status != IngestionStatus.FAILED.value:
                raise InvalidStateError("Only failed ingestion can be retried.")
            target = (
                IngestionStatus.UPLOADED
                if rebuild
                else IngestionStatus(row.failed_stage or IngestionStatus.UPLOADED.value)
            )
            if rebuild:
                await _delete_chunk_projection(session, version.id)
                await session.execute(
                    delete(KnowledgeEdgeRow).where(
                        KnowledgeEdgeRow.document_version_id == version.id
                    )
                )
                version.normalized_text = None
                version.active = False
                version.verification_status = VerificationStatus.NOT_CONFIGURED.value
                row.verification_status = VerificationStatus.NOT_CONFIGURED.value
            row.status = target.value
            row.failed_stage = None
            row.error_code = None
            row.retryable = False
            row.attempt += 1
            row.updated_at = now
            row.version += 1
            version.status = target.value
            version.updated_at = now
            await session.flush()
            return _run(row)

    async def ready_version_ids(
        self,
        workspace_id: UUID,
        project_id: UUID,
        filters: RetrievalFilter,
    ) -> tuple[UUID, ...]:
        statement = (
            select(KnowledgeDocumentVersionRow.id)
            .join(
                KnowledgeSourceRow,
                KnowledgeSourceRow.id == KnowledgeDocumentVersionRow.source_id,
            )
            .where(
                KnowledgeDocumentVersionRow.workspace_id == workspace_id,
                KnowledgeDocumentVersionRow.project_id == project_id,
                KnowledgeDocumentVersionRow.status == IngestionStatus.READY.value,
                KnowledgeDocumentVersionRow.active.is_(True),
            )
        )
        if filters.source_ids:
            statement = statement.where(
                KnowledgeDocumentVersionRow.source_id.in_(filters.source_ids)
            )
        if filters.document_version_ids:
            statement = statement.where(
                KnowledgeDocumentVersionRow.id.in_(filters.document_version_ids)
            )
        if filters.verification_statuses:
            statement = statement.where(
                KnowledgeDocumentVersionRow.verification_status.in_(
                    tuple(item.value for item in filters.verification_statuses)
                )
            )
        async with self._sessions() as session:
            return tuple((await session.scalars(statement)).all())

    async def chunks_and_citations(
        self,
        workspace_id: UUID,
        project_id: UUID,
        chunk_ids: tuple[UUID, ...],
    ) -> tuple[tuple[Chunk, Citation], ...]:
        if not chunk_ids:
            return ()
        statement = (
            select(KnowledgeChunkRow, KnowledgeCitationRow, KnowledgeDocumentVersionRow)
            .join(KnowledgeCitationRow, KnowledgeCitationRow.chunk_id == KnowledgeChunkRow.id)
            .join(
                KnowledgeDocumentVersionRow,
                KnowledgeDocumentVersionRow.id == KnowledgeChunkRow.document_version_id,
            )
            .where(
                KnowledgeChunkRow.workspace_id == workspace_id,
                KnowledgeChunkRow.project_id == project_id,
                KnowledgeChunkRow.id.in_(chunk_ids),
                KnowledgeDocumentVersionRow.active.is_(True),
                KnowledgeDocumentVersionRow.status == IngestionStatus.READY.value,
            )
        )
        async with self._sessions() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            (
                _chunk(chunk),
                Citation(
                    citation.id,
                    citation.workspace_id,
                    citation.project_id,
                    citation.source_id,
                    citation.document_id,
                    citation.document_version_id,
                    citation.asset_id,
                    citation.asset_version_id,
                    citation.chunk_id,
                    citation.locator,
                    VerificationStatus(version.verification_status),
                ),
            )
            for chunk, citation, version in rows
        )


async def _locked(
    session: AsyncSession, workspace_id: UUID, run_id: UUID
) -> tuple[KnowledgeIngestionRunRow, KnowledgeDocumentVersionRow]:
    row = await session.scalar(
        select(KnowledgeIngestionRunRow)
        .where(
            KnowledgeIngestionRunRow.workspace_id == workspace_id,
            KnowledgeIngestionRunRow.id == run_id,
        )
        .with_for_update()
    )
    if row is None:
        raise InvalidStateError("Knowledge ingestion is unavailable.")
    version = await session.get(KnowledgeDocumentVersionRow, row.document_version_id)
    if version is None:
        raise InvalidStateError("Knowledge document version is unavailable.")
    return row, version


def _advance(
    row: KnowledgeIngestionRunRow,
    version: KnowledgeDocumentVersionRow,
    status: IngestionStatus,
    now: datetime,
) -> None:
    row.status = status.value
    row.failed_stage = None
    row.error_code = None
    row.retryable = False
    row.updated_at = now
    row.version += 1
    version.status = status.value
    version.updated_at = now


async def _delete_embeddings(session: AsyncSession, document_version_id: UUID) -> None:
    await session.execute(
        delete(KnowledgeVectorRow).where(
            KnowledgeVectorRow.document_version_id == document_version_id
        )
    )
    await session.execute(
        delete(KnowledgeEmbeddingRefRow).where(
            KnowledgeEmbeddingRefRow.document_version_id == document_version_id
        )
    )


async def _delete_chunk_projection(session: AsyncSession, document_version_id: UUID) -> None:
    await _delete_embeddings(session, document_version_id)
    await session.execute(
        delete(KnowledgeCitationRow).where(
            KnowledgeCitationRow.document_version_id == document_version_id
        )
    )
    await session.execute(
        delete(KnowledgeChunkRow).where(
            KnowledgeChunkRow.document_version_id == document_version_id
        )
    )


def _source(row: KnowledgeSourceRow) -> KnowledgeSource:
    return KnowledgeSource(
        row.id,
        row.workspace_id,
        row.project_id,
        row.asset_id,
        row.asset_version_id,
        row.asset_version_number,
        row.content_hash,
        row.media_type,
        row.content_locator,
        row.created_at,
    )


def _document(row: KnowledgeDocumentRow) -> Document:
    return Document(row.id, row.workspace_id, row.project_id, row.asset_id, row.created_at)


def _document_version(row: KnowledgeDocumentVersionRow) -> DocumentVersion:
    return DocumentVersion(
        row.id,
        row.workspace_id,
        row.project_id,
        row.document_id,
        row.source_id,
        row.version_number,
        row.content_hash,
        row.normalized_text,
        IngestionStatus(row.status),
        VerificationStatus(row.verification_status),
        row.active,
        row.created_at,
        row.updated_at,
    )


def _run(row: KnowledgeIngestionRunRow) -> IngestionRun:
    return IngestionRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.source_id,
        row.document_id,
        row.document_version_id,
        IngestionStatus(row.status),
        VerificationPolicy(row.verification_policy),
        VerificationStatus(row.verification_status),
        row.idempotency_key,
        row.requested_by,
        row.correlation_id,
        row.attempt,
        row.created_at,
        row.updated_at,
        None if row.failed_stage is None else IngestionStatus(row.failed_stage),
        None if row.error_code is None else KnowledgeErrorCode(row.error_code),
        row.retryable,
        row.workflow_run_id,
    )


def _chunk(row: KnowledgeChunkRow) -> Chunk:
    return Chunk(
        row.id,
        row.workspace_id,
        row.project_id,
        row.source_id,
        row.document_version_id,
        row.ordinal,
        row.content,
        row.content_hash,
    )


def _embedding(row: KnowledgeEmbeddingRefRow) -> EmbeddingRef:
    return EmbeddingRef(
        row.id,
        row.workspace_id,
        row.project_id,
        row.chunk_id,
        row.document_version_id,
        row.embedder_id,
        row.dimensions,
        tuple(row.vector_payload),
        row.content_hash,
    )


def _chunk_row(chunk: Chunk) -> KnowledgeChunkRow:
    return KnowledgeChunkRow(
        id=chunk.id,
        workspace_id=chunk.workspace_id,
        project_id=chunk.project_id,
        source_id=chunk.source_id,
        document_version_id=chunk.document_version_id,
        ordinal=chunk.ordinal,
        content=chunk.content,
        content_hash=chunk.content_hash,
    )


def _embedding_row(embedding: EmbeddingRef) -> KnowledgeEmbeddingRefRow:
    return KnowledgeEmbeddingRefRow(
        id=embedding.id,
        workspace_id=embedding.workspace_id,
        project_id=embedding.project_id,
        chunk_id=embedding.chunk_id,
        document_version_id=embedding.document_version_id,
        embedder_id=embedding.embedder_id,
        dimensions=embedding.dimensions,
        vector_payload=list(embedding.vector),
        content_hash=embedding.content_hash,
    )
