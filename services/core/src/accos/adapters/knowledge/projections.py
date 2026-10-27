"""In-memory and PostgreSQL vector/graph projections for knowledge."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from sqlalchemy import delete, text

from accos.adapters.knowledge.persistence import KnowledgeEdgeRow, KnowledgeVectorRow
from accos.modules.knowledge.public import (
    IngestionStatus,
    KnowledgeErrorCode,
    KnowledgePipelineError,
    VectorMatch,
)

if TYPE_CHECKING:
    from uuid import UUID

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.modules.knowledge.public import EmbeddingRef, KnowledgeEdge

_VECTOR_DIMENSIONS = 8


class InMemoryVectorIndex:
    """Deterministic fake implementing the same replace/search contract as pgvector."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self._items: dict[tuple[UUID, UUID, UUID], EmbeddingRef] = {}

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
    ) -> None:
        self._require_available()
        if any(
            (
                item.workspace_id != workspace_id
                or item.project_id != project_id
                or item.document_version_id != document_version_id
            )
            for item in embeddings
        ):
            raise ValueError("embedding projection scope is inconsistent")
        self._items = {
            key: value
            for key, value in self._items.items()
            if key[:2] != (workspace_id, document_version_id)
        }
        for item in embeddings:
            self._items[(workspace_id, document_version_id, item.chunk_id)] = item

    async def search(
        self,
        workspace_id: UUID,
        project_id: UUID,
        query_vector: tuple[float, ...],
        *,
        allowed_version_ids: tuple[UUID, ...],
        top_k: int,
    ) -> tuple[VectorMatch, ...]:
        self._require_available()
        allowed = frozenset(allowed_version_ids)
        matches = [
            VectorMatch(item.chunk_id, _cosine(query_vector, item.vector))
            for (scope, version_id, _chunk_id), item in self._items.items()
            if scope == workspace_id and version_id in allowed and item.project_id == project_id
        ]
        return tuple(sorted(matches, key=lambda item: (-item.score, str(item.chunk_id)))[:top_k])

    def _require_available(self) -> None:
        if not self.available:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.INDEX_UNAVAILABLE,
                IngestionStatus.EMBEDDED,
                retryable=True,
            )


class InMemoryGraphProjection:
    """Replaceable fake relation projection."""

    def __init__(self) -> None:
        self.items: dict[tuple[UUID, UUID], tuple[KnowledgeEdge, ...]] = {}

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        edges: tuple[KnowledgeEdge, ...],
    ) -> None:
        if any(
            edge.workspace_id != workspace_id
            or edge.project_id != project_id
            or edge.document_version_id != document_version_id
            for edge in edges
        ):
            raise ValueError("graph projection scope is inconsistent")
        self.items[(workspace_id, document_version_id)] = edges


class PgVectorIndex:
    """pgvector cosine index isolated by workspace, project, and document version."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
    ) -> None:
        if any(
            item.workspace_id != workspace_id
            or item.project_id != project_id
            or item.document_version_id != document_version_id
            or item.dimensions != _VECTOR_DIMENSIONS
            for item in embeddings
        ):
            raise ValueError("pgvector projection requires consistent 8-dimensional values")
        try:
            async with self._sessions.begin() as session:
                await session.execute(
                    delete(KnowledgeVectorRow).where(
                        KnowledgeVectorRow.workspace_id == workspace_id,
                        KnowledgeVectorRow.project_id == project_id,
                        KnowledgeVectorRow.document_version_id == document_version_id,
                    )
                )
                session.add_all(
                    KnowledgeVectorRow(
                        embedding_ref_id=item.id,
                        workspace_id=item.workspace_id,
                        project_id=item.project_id,
                        document_version_id=item.document_version_id,
                        chunk_id=item.chunk_id,
                        embedding=_vector_literal(item.vector),
                    )
                    for item in embeddings
                )
        except Exception as error:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.INDEX_UNAVAILABLE,
                IngestionStatus.EMBEDDED,
                retryable=True,
            ) from error

    async def search(
        self,
        workspace_id: UUID,
        project_id: UUID,
        query_vector: tuple[float, ...],
        *,
        allowed_version_ids: tuple[UUID, ...],
        top_k: int,
    ) -> tuple[VectorMatch, ...]:
        if not allowed_version_ids:
            return ()
        if len(query_vector) != _VECTOR_DIMENSIONS:
            raise ValueError("pgvector query must have 8 dimensions")
        try:
            async with self._sessions() as session:
                native = bool(
                    await session.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_type "
                            "WHERE typname = 'vector' AND typtype = 'b')"
                        )
                    )
                )
                parameters = {
                    "query": _vector_literal(query_vector),
                    "workspace_id": workspace_id,
                    "project_id": project_id,
                    "version_ids": list(allowed_version_ids),
                    "top_k": top_k,
                }
                if native:
                    rows = (
                        await session.execute(
                            text(
                                "SELECT chunk_id, "
                                "1 - (embedding <=> CAST(:query AS vector)) AS score "
                                "FROM accos.knowledge_vector_index "
                                "WHERE workspace_id = :workspace_id "
                                "AND project_id = :project_id "
                                "AND document_version_id = ANY(:version_ids) "
                                "ORDER BY embedding <=> CAST(:query AS vector), chunk_id "
                                "LIMIT :top_k"
                            ),
                            parameters,
                        )
                    ).all()
                    return tuple(VectorMatch(row.chunk_id, float(row.score)) for row in rows)
                rows = (
                    await session.execute(
                        text(
                            "SELECT chunk_id, embedding::text AS embedding "
                            "FROM accos.knowledge_vector_index "
                            "WHERE workspace_id = :workspace_id "
                            "AND project_id = :project_id "
                            "AND document_version_id = ANY(:version_ids)"
                        ),
                        parameters,
                    )
                ).all()
        except Exception as error:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.INDEX_UNAVAILABLE,
                IngestionStatus.EMBEDDED,
                retryable=True,
            ) from error
        matches = (
            VectorMatch(row.chunk_id, _cosine(query_vector, _parse_vector(row.embedding)))
            for row in rows
        )
        return tuple(sorted(matches, key=lambda item: (-item.score, str(item.chunk_id)))[:top_k])


class SqlAlchemyGraphProjection:
    """Minimal PostgreSQL edge projection with replace semantics."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def replace(
        self,
        workspace_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
        edges: tuple[KnowledgeEdge, ...],
    ) -> None:
        if any(
            edge.workspace_id != workspace_id
            or edge.project_id != project_id
            or edge.document_version_id != document_version_id
            for edge in edges
        ):
            raise ValueError("graph projection scope is inconsistent")
        async with self._sessions.begin() as session:
            await session.execute(
                delete(KnowledgeEdgeRow).where(
                    KnowledgeEdgeRow.workspace_id == workspace_id,
                    KnowledgeEdgeRow.project_id == project_id,
                    KnowledgeEdgeRow.document_version_id == document_version_id,
                )
            )
            session.add_all(
                KnowledgeEdgeRow(
                    id=edge.id,
                    workspace_id=edge.workspace_id,
                    project_id=edge.project_id,
                    document_version_id=edge.document_version_id,
                    from_kind=edge.from_kind,
                    from_id=edge.from_id,
                    relation=edge.relation.value,
                    to_kind=edge.to_kind,
                    to_id=edge.to_id,
                )
                for edge in edges
            )


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions must match")
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    return (
        0.0
        if denominator == 0
        else sum(a * b for a, b in zip(left, right, strict=True)) / denominator
    )


def _vector_literal(vector: tuple[float, ...]) -> str:
    return "[" + ",".join(f"{value:.12f}" for value in vector) + "]"


def _parse_vector(value: str) -> tuple[float, ...]:
    return tuple(float(item) for item in value.removeprefix("[").removesuffix("]").split(","))
