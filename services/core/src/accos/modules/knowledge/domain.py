"""Framework-free knowledge ingestion, retrieval, and research contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.kernel.contracts import IdempotencyKey

_MAX_QUERY_LENGTH = 2_000
_MAX_TOP_K = 100

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class IngestionStatus(StrEnum):
    """Durable checkpoints for one asset-version ingestion."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    NORMALIZED = "normalized"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    VERIFYING = "verifying"
    READY = "ready"
    FAILED = "failed"


class VerificationStatus(StrEnum):
    """Truthful source verification state, independent from ingestion state."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    NOT_CONFIGURED = "not_configured"
    REJECTED = "rejected"


class VerificationPolicy(StrEnum):
    """Whether a successful verification decision is required for readiness."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"


class KnowledgeErrorCode(StrEnum):
    """Stable failures that never expose parser, model, or database details."""

    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SOURCE_NOT_CONFIGURED = "SOURCE_NOT_CONFIGURED"
    SOURCE_INTEGRITY_FAILED = "SOURCE_INTEGRITY_FAILED"
    EXTRACTOR_NOT_CONFIGURED = "EXTRACTOR_NOT_CONFIGURED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    NORMALIZATION_FAILED = "NORMALIZATION_FAILED"
    CHUNKING_FAILED = "CHUNKING_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    INDEX_UNAVAILABLE = "INDEX_UNAVAILABLE"
    VERIFICATION_NOT_CONFIGURED = "VERIFICATION_NOT_CONFIGURED"
    VERIFICATION_UNVERIFIED = "VERIFICATION_UNVERIFIED"
    VERIFICATION_REJECTED = "VERIFICATION_REJECTED"


class RelationKind(StrEnum):
    """Minimal PostgreSQL graph-projection relations."""

    SOURCE_OF = "source_of"
    CONTAINS = "contains"
    CITES = "cites"
    DERIVED_FROM = "derived_from"


class ResearchStatus(StrEnum):
    """Offline research skeleton outcomes."""

    COMPLETED = "completed"
    NO_RESULTS = "no_results"


class KnowledgePipelineError(Exception):
    """Provider-neutral ingestion failure with retry guidance."""

    def __init__(
        self,
        code: KnowledgeErrorCode,
        stage: IngestionStatus,
        *,
        retryable: bool,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        self.stage = stage
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """Immutable provenance for exactly one asset version."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    asset_version_number: int
    content_hash: str
    media_type: str
    content_locator: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Document:
    """Logical document shared by immutable asset-backed versions."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    """Normalized source-of-truth text and readiness for one source."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    document_id: UUID
    source_id: UUID
    version_number: int
    content_hash: str
    normalized_text: str | None
    status: IngestionStatus
    verification_status: VerificationStatus
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Chunk:
    """Deterministic, version-scoped text projection."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    source_id: UUID
    document_version_id: UUID
    ordinal: int
    content: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class EmbeddingRef:
    """Rebuildable embedding value plus its exact fake/model identity."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    chunk_id: UUID
    document_version_id: UUID
    embedder_id: str
    dimensions: int
    vector: tuple[float, ...]
    content_hash: str

    def __post_init__(self) -> None:
        if self.dimensions < 1 or len(self.vector) != self.dimensions:
            raise ValueError("embedding dimensions must match its vector")


@dataclass(frozen=True, slots=True)
class Citation:
    """Stable retrieval provenance down to an immutable asset and chunk."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    source_id: UUID
    document_id: UUID
    document_version_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    chunk_id: UUID
    locator: str
    verification_status: VerificationStatus


@dataclass(frozen=True, slots=True)
class IngestionRun:
    """Retryable state machine for one unique source version."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    source_id: UUID
    document_id: UUID
    document_version_id: UUID
    status: IngestionStatus
    verification_policy: VerificationPolicy
    verification_status: VerificationStatus
    idempotency_key: str
    requested_by: UUID
    correlation_id: UUID
    attempt: int
    created_at: datetime
    updated_at: datetime
    failed_stage: IngestionStatus | None = None
    error_code: KnowledgeErrorCode | None = None
    retryable: bool = False
    workflow_run_id: UUID | None = None

    def __post_init__(self) -> None:
        IdempotencyKey(self.idempotency_key)
        if self.attempt < 1:
            raise ValueError("ingestion attempt must be positive")
        failed = self.status is IngestionStatus.FAILED
        if failed != (self.failed_stage is not None and self.error_code is not None):
            raise ValueError("failed ingestion must retain stage and error code")
        if not failed and self.retryable:
            raise ValueError("only failed ingestion can be retryable")


@dataclass(frozen=True, slots=True)
class IngestionBundle:
    """Repository-owned aggregate snapshot used to resume at any checkpoint."""

    run: IngestionRun
    source: KnowledgeSource
    document: Document
    version: DocumentVersion
    chunks: tuple[Chunk, ...] = ()
    embeddings: tuple[EmbeddingRef, ...] = ()


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """Scoped vector lookup result before citation enrichment."""

    chunk_id: UUID
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalFilter:
    """Optional exact source/version/trust filters."""

    source_ids: tuple[UUID, ...] = ()
    document_version_ids: tuple[UUID, ...] = ()
    verification_statuses: tuple[VerificationStatus, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Bounded query contract; scope always comes from trusted context."""

    query: str
    top_k: int = 5
    filters: RetrievalFilter = RetrievalFilter()

    def __post_init__(self) -> None:
        if (
            not self.query
            or self.query.strip() != self.query
            or len(self.query) > _MAX_QUERY_LENGTH
        ):
            raise ValueError("retrieval query must be non-empty, trimmed, and bounded")
        if not 1 <= self.top_k <= _MAX_TOP_K:
            raise ValueError("retrieval top_k must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """One scored chunk with immutable source and verification evidence."""

    score: float
    chunk: Chunk
    citation: Citation


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Structured retrieval response; no hits is a normal result."""

    query: str
    hits: tuple[RetrievalHit, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeEdge:
    """Minimal, scoped relationship projection stored in PostgreSQL."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    document_version_id: UUID
    from_kind: str
    from_id: UUID
    relation: RelationKind
    to_kind: str
    to_id: UUID


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    """Offline research request expressed without question content leakage."""

    question_reference: str
    query: str
    top_k: int = 5

    def __post_init__(self) -> None:
        if not self.question_reference.startswith("research-question://"):
            raise ValueError("research question must use an opaque reference")


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """Technical plan/request/verification/report chain with citations only."""

    status: ResearchStatus
    question_reference: str
    plan_reference: str
    material_request_reference: str
    verification_status: VerificationStatus
    report_reference: str
    citations: tuple[Citation, ...]
