"""Versioned source and card references used by the novel workflow."""
from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True)
class StateHead:
    branch_id: str
    revision: int


@dataclass(frozen=True)
class Evidence:
    draft_id: str
    text_sha256: str
    start: int
    end: int


@dataclass(frozen=True)
class Fact:
    entity_id: str
    predicate: str
    value: Any
    holder: str
    claim: str
    story_order: int
    disclosure_order: tuple[int, int, int]
    evidence: tuple[dict, ...]


@dataclass(frozen=True)
class StateView:
    branch_id: str
    revision: int
    story_order: int
    holder: str
    facts: list[Fact]
    settings: list[dict]
    coverage: dict
    omissions: list[dict]
    legacy_notes: list[dict]


@dataclass(frozen=True)
class StateDelta:
    id: str
    branch_id: str
    base_revision: int
    draft_id: str
    manifest_id: str
    operations: list[dict]
    findings: list[dict]
    sha256: str
    extraction_task_id: str | None = None
    review_task_id: str | None = None
    candidate_delta_refs: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AcceptanceRequest:
    branch_id: str
    scene_id: str
    draft_id: str
    delta_id: str
    decision_id: str
    manifest_id: str
