"""Deterministic extraction, normalization, chunking, embedding, and verification."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from accos.modules.knowledge.public import (
    IngestionStatus,
    KnowledgeErrorCode,
    KnowledgePipelineError,
    SourceSnapshot,
    VerificationStatus,
)

_SUPPORTED_TEXT_TYPES = frozenset({"text/plain", "text/markdown"})
_WHITESPACE = re.compile(r"[\t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_MIN_CHUNK_CHARACTERS = 16
_FAKE_DIMENSIONS = 8


class TextMarkdownExtractor:
    """Strict UTF-8 extractor for the only configured first-release formats."""

    async def extract(self, source: SourceSnapshot, data: bytes) -> str:
        if source.media_type not in _SUPPORTED_TEXT_TYPES:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.EXTRACTOR_NOT_CONFIGURED,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.EXTRACTION_FAILED,
                IngestionStatus.EXTRACTING,
                retryable=False,
            ) from error
        if not text.strip():
            raise KnowledgePipelineError(
                KnowledgeErrorCode.EXTRACTION_FAILED,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        return text


class NotConfiguredExtractor:
    """Explicit placeholder for PDF, DOCX, and other deferred parsers."""

    async def extract(self, source: SourceSnapshot, data: bytes) -> str:
        del source, data
        raise KnowledgePipelineError(
            KnowledgeErrorCode.EXTRACTOR_NOT_CONFIGURED,
            IngestionStatus.EXTRACTING,
            retryable=False,
        )


class DeterministicNormalizer:
    """Normalize line endings and insignificant whitespace without inference."""

    async def normalize(self, text: str) -> str:
        canonical = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = (_WHITESPACE.sub(" ", line).strip() for line in canonical.split("\n"))
        normalized = _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
        if not normalized:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.NORMALIZATION_FAILED,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        return normalized


class DeterministicChunker:
    """Paragraph-first bounded chunker with no semantic or model decisions."""

    def __init__(self, *, max_characters: int = 512) -> None:
        if max_characters < _MIN_CHUNK_CHARACTERS:
            raise ValueError("chunk size must be at least 16 characters")
        self._max_characters = max_characters

    async def chunk(self, text: str) -> tuple[str, ...]:
        chunks = tuple(
            paragraph[offset : offset + self._max_characters]
            for paragraph in text.split("\n\n")
            if paragraph
            for offset in range(0, len(paragraph), self._max_characters)
        )
        if not chunks:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.CHUNKING_FAILED,
                IngestionStatus.NORMALIZED,
                retryable=False,
            )
        return chunks


class FakeEmbedder:
    """No-network embedder with deterministic, normalized SHA-256 vectors."""

    def __init__(
        self,
        embedder_id: str = "fake-embedder@1",
        *,
        dimensions: int = _FAKE_DIMENSIONS,
        failures_remaining: int = 0,
    ) -> None:
        if not embedder_id or dimensions != _FAKE_DIMENSIONS or failures_remaining < 0:
            raise ValueError("fake embedder requires an id, 8 dimensions, and valid failures")
        self._embedder_id = embedder_id
        self._dimensions = dimensions
        self.failures_remaining = failures_remaining

    @property
    def embedder_id(self) -> str:
        return self._embedder_id

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise KnowledgePipelineError(
                KnowledgeErrorCode.EMBEDDING_FAILED,
                IngestionStatus.CHUNKED,
                retryable=True,
            )
        return tuple(_vector(text, self._dimensions) for text in texts)


class NotConfiguredVerificationProvider:
    """Default verifier that never claims a source was checked."""

    async def verify(self, source: SourceSnapshot, normalized_text: str) -> VerificationStatus:
        del source, normalized_text
        return VerificationStatus.NOT_CONFIGURED


@dataclass(frozen=True, slots=True)
class FixedVerificationProvider:
    """Deterministic verification outcome for contract and failure tests."""

    status: VerificationStatus

    async def verify(self, source: SourceSnapshot, normalized_text: str) -> VerificationStatus:
        del source, normalized_text
        return self.status


def _vector(text: str, dimensions: int) -> tuple[float, ...]:
    digest = hashlib.sha256(text.encode()).digest()
    raw = tuple((digest[index] - 127.5) / 127.5 for index in range(dimensions))
    magnitude = math.sqrt(sum(value * value for value in raw)) or 1.0
    return tuple(value / magnitude for value in raw)
