"""Ports owned by the knowledge module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.modules.knowledge.domain import (
        Chunk,
        Citation,
        Document,
        EmbeddingRef,
        IngestionBundle,
        IngestionRun,
        KnowledgeEdge,
        RetrievalFilter,
        RetrievalRequest,
        RetrievalResult,
        VectorMatch,
        VerificationPolicy,
        VerificationStatus,
    )


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Asset-owned metadata and locator needed for a rebuildable source."""

    workspace_id: UUID
    project_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    version_number: int
    object_key: str
    content_hash: str
    media_type: str


class SourceReader(Protocol):
    """Read assets only through their public repository/storage contracts."""

    async def resolve(
        self, workspace_id: UUID, project_id: UUID, asset_id: UUID
    ) -> SourceSnapshot: ...

    async def read(self, source: SourceSnapshot) -> bytes: ...


class Extractor(Protocol):
    """Extract bounded text from one supported source type."""

    async def extract(self, source: SourceSnapshot, data: bytes) -> str: ...


class Normalizer(Protocol):
    """Normalize extracted text deterministically."""

    async def normalize(self, text: str) -> str: ...


class Chunker(Protocol):
    """Split normalized text into deterministic bounded chunks."""

    async def chunk(self, text: str) -> tuple[str, ...]: ...


class Embedder(Protocol):
    """Return deterministic or gateway-backed vectors."""

    @property
    def embedder_id(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...


class VectorIndex(Protocol):
    """Rebuildable vector projection; never owns source metadata."""

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
    ) -> None: ...

    async def search(
        self,
        workspace_id: UUID,
        project_id: UUID,
        query_vector: tuple[float, ...],
        *,
        allowed_version_ids: tuple[UUID, ...],
        top_k: int,
    ) -> tuple[VectorMatch, ...]: ...


class Retriever(Protocol):
    """Scoped retrieval boundary consumed by research, Agents, and future API."""

    async def retrieve(
        self,
        workspace_id: UUID,
        project_id: UUID,
        request: RetrievalRequest,
    ) -> RetrievalResult: ...


class VerificationProvider(Protocol):
    """Optional source verifier that must report its truthful state."""

    async def verify(self, source: SourceSnapshot, normalized_text: str) -> VerificationStatus: ...


class GraphProjection(Protocol):
    """Minimal replaceable relation projection; not an independent graph store."""

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        edges: tuple[KnowledgeEdge, ...],
    ) -> None: ...


class KnowledgeRepository(Protocol):
    """Durable state, provenance, and normalized-text owner."""

    async def reserve(  # noqa: PLR0913
        self,
        snapshot: SourceSnapshot,
        *,
        verification_policy: VerificationPolicy,
        idempotency_key: str,
        requested_by: UUID,
        correlation_id: UUID,
        now: datetime,
    ) -> tuple[IngestionRun, bool]: ...

    async def load(self, workspace_id: UUID, run_id: UUID) -> IngestionBundle | None: ...

    async def get_document(
        self, workspace_id: UUID, project_id: UUID, document_id: UUID
    ) -> Document | None: ...

    async def set_status(
        self,
        workspace_id: UUID,
        run_id: UUID,
        status: str,
        *,
        now: datetime,
    ) -> IngestionRun: ...

    async def save_normalized(
        self,
        workspace_id: UUID,
        run_id: UUID,
        text: str,
        *,
        now: datetime,
    ) -> IngestionRun: ...

    async def replace_chunks(
        self,
        workspace_id: UUID,
        run_id: UUID,
        chunks: tuple[Chunk, ...],
        *,
        now: datetime,
    ) -> IngestionRun: ...

    async def replace_embeddings(
        self,
        workspace_id: UUID,
        run_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
        *,
        now: datetime,
    ) -> IngestionRun: ...

    async def complete(
        self,
        workspace_id: UUID,
        run_id: UUID,
        verification_status: VerificationStatus,
        *,
        now: datetime,
    ) -> IngestionRun: ...

    async def fail(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        failed_stage: str,
        error_code: str,
        retryable: bool,
        now: datetime,
    ) -> IngestionRun: ...

    async def restart(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        rebuild: bool,
        now: datetime,
    ) -> IngestionRun: ...

    async def ready_version_ids(
        self,
        workspace_id: UUID,
        project_id: UUID,
        filters: RetrievalFilter,
    ) -> tuple[UUID, ...]: ...

    async def chunks_and_citations(
        self,
        workspace_id: UUID,
        project_id: UUID,
        chunk_ids: tuple[UUID, ...],
    ) -> tuple[tuple[Chunk, Citation], ...]: ...
