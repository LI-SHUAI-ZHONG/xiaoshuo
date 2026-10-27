"""Knowledge module adapters."""

from accos.adapters.knowledge.persistence import (
    MODEL_REGISTRY,
    KnowledgeChunkRow,
    KnowledgeCitationRow,
    KnowledgeDocumentRow,
    KnowledgeDocumentVersionRow,
    KnowledgeEdgeRow,
    KnowledgeEmbeddingRefRow,
    KnowledgeIngestionRunRow,
    KnowledgeSourceRow,
    KnowledgeVectorRow,
    SqlAlchemyKnowledgeRepository,
)
from accos.adapters.knowledge.processors import (
    DeterministicChunker,
    DeterministicNormalizer,
    FakeEmbedder,
    FixedVerificationProvider,
    NotConfiguredExtractor,
    NotConfiguredVerificationProvider,
    TextMarkdownExtractor,
)
from accos.adapters.knowledge.projections import (
    InMemoryGraphProjection,
    InMemoryVectorIndex,
    PgVectorIndex,
    SqlAlchemyGraphProjection,
)
from accos.adapters.knowledge.source import AssetSourceReader, NotConfiguredExternalSourceReader

__all__ = [
    "MODEL_REGISTRY",
    "AssetSourceReader",
    "DeterministicChunker",
    "DeterministicNormalizer",
    "FakeEmbedder",
    "FixedVerificationProvider",
    "InMemoryGraphProjection",
    "InMemoryVectorIndex",
    "KnowledgeChunkRow",
    "KnowledgeCitationRow",
    "KnowledgeDocumentRow",
    "KnowledgeDocumentVersionRow",
    "KnowledgeEdgeRow",
    "KnowledgeEmbeddingRefRow",
    "KnowledgeIngestionRunRow",
    "KnowledgeSourceRow",
    "KnowledgeVectorRow",
    "NotConfiguredExternalSourceReader",
    "NotConfiguredExtractor",
    "NotConfiguredVerificationProvider",
    "PgVectorIndex",
    "SqlAlchemyGraphProjection",
    "SqlAlchemyKnowledgeRepository",
    "TextMarkdownExtractor",
]
