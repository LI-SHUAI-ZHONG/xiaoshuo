"""Versioned source and card references used by the novel workflow."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    start_line: int
    end_line: int
    span_sha256: str


@dataclass(frozen=True)
class SourceVersion:
    id: str
    relative_path: str
    file_sha256: str
    byte_size: int
    encoding: str | None
    status: str


@dataclass(frozen=True)
class CardRef:
    card_id: str
    version: int


@dataclass(frozen=True)
class DecisionRef:
    id: str
    card_ref: CardRef
    decision: str


@dataclass(frozen=True)
class DecisionRecord:
    ref: DecisionRef
    reason: str
    created_at: str


@dataclass(frozen=True)
class CardLink:
    source: CardRef
    target: CardRef
    relation: str
