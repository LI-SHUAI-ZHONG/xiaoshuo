"""Framework-free seven-scope memory, conflict, and context contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,79}$")
_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")


class MemoryScope(StrEnum):
    """The seven retention/visibility layers; independent from memory type."""

    WORKING = "working"
    SESSION = "session"
    PROJECT = "project"
    UNIVERSE = "universe"
    CREATOR = "creator"
    EXPERIENCE = "experience"
    WISDOM = "wisdom"


PROJECT_SCOPES = frozenset({MemoryScope.WORKING, MemoryScope.SESSION, MemoryScope.PROJECT})
CREATOR_SCOPES = frozenset({MemoryScope.CREATOR, MemoryScope.EXPERIENCE, MemoryScope.WISDOM})


class MemoryStatus(StrEnum):
    """Version state; candidates never replace the current version implicitly."""

    ACTIVE = "active"
    CANDIDATE = "candidate"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class RetentionKind(StrEnum):
    """Deterministic first-release retention behavior."""

    KEEP = "keep"
    TTL = "ttl"
    DECAY = "decay"
    ARCHIVE = "archive"


class MemoryAnchorKind(StrEnum):
    """Only these durable grants can enable cross-project context."""

    UNIVERSE = "universe"
    CREATOR = "creator"


class MemoryConflictStatus(StrEnum):
    """Human-controlled conflict lifecycle."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class OmissionReason(StrEnum):
    """Stable reasons emitted without exposing unauthorized records."""

    ANCHOR_UNAVAILABLE = "anchor_unavailable"
    NOT_YET_VALID = "not_yet_valid"
    NO_LONGER_VALID = "no_longer_valid"
    TTL_EXPIRED = "ttl_expired"
    ARCHIVED = "archived"
    RETENTION_ARCHIVED = "retention_archived"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass(frozen=True, slots=True)
class RetentionRule:
    """Retention metadata stored with every record version."""

    kind: RetentionKind = RetentionKind.KEEP
    ttl_seconds: int | None = None
    decay_half_life_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.kind is RetentionKind.TTL and (self.ttl_seconds is None or self.ttl_seconds < 1):
            raise ValueError("TTL retention requires positive ttl_seconds")
        if self.kind is RetentionKind.DECAY and (
            self.decay_half_life_seconds is None or self.decay_half_life_seconds < 1
        ):
            raise ValueError("decay retention requires a positive half life")
        if self.kind is not RetentionKind.TTL and self.ttl_seconds is not None:
            raise ValueError("ttl_seconds is only valid for TTL retention")
        if self.kind is not RetentionKind.DECAY and self.decay_half_life_seconds is not None:
            raise ValueError("half life is only valid for decay retention")


@dataclass(frozen=True, slots=True)
class MemoryProvenance:
    """Opaque source reference; Knowledge internals never cross this boundary."""

    kind: str
    reference: str

    def __post_init__(self) -> None:
        if _TYPE.fullmatch(self.kind) is None or _REFERENCE.fullmatch(self.reference) is None:
            raise ValueError("memory provenance must use a named kind and opaque reference")


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """One immutable version across the orthogonal scope and type dimensions."""

    id: UUID
    logical_id: UUID
    version: int
    workspace_id: UUID
    scope: MemoryScope
    memory_type: str
    content: str
    project_id: UUID | None
    universe_id: UUID | None
    creator_id: UUID | None
    valid_from: datetime
    valid_until: datetime | None
    observed_at: datetime
    importance: float
    confidence: float
    provenance: MemoryProvenance
    retention: RetentionRule
    status: MemoryStatus
    current: bool
    created_by: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        anchors = (self.project_id, self.universe_id, self.creator_id)
        expected = (
            (self.project_id is not None and anchors[1:] == (None, None))
            if self.scope in PROJECT_SCOPES
            else (
                self.universe_id is not None and self.project_id is None and self.creator_id is None
                if self.scope is MemoryScope.UNIVERSE
                else self.creator_id is not None
                and self.project_id is None
                and self.universe_id is None
            )
        )
        if not expected:
            raise ValueError("memory scope requires exactly its canonical anchor")
        if _TYPE.fullmatch(self.memory_type) is None:
            raise ValueError("memory type must be an extensible lower-case identifier")
        if self.version < 1 or not self.content or self.content.strip() != self.content:
            raise ValueError("memory version and content must be non-empty")
        if not 0 <= self.importance <= 1 or not 0 <= self.confidence <= 1:
            raise ValueError("memory importance and confidence must be within 0..1")
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must follow valid_from")
        if self.current != (self.status is MemoryStatus.ACTIVE):
            raise ValueError("only active memory versions can be current")

    @property
    def anchor_id(self) -> UUID:
        """Return the non-null canonical anchor."""
        return self.project_id or self.universe_id or self.creator_id  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class MemoryLink:
    """Auditable relation between record versions, including compression lineage."""

    id: UUID
    workspace_id: UUID
    from_record_id: UUID
    to_record_id: UUID
    relation: str
    created_at: datetime

    def __post_init__(self) -> None:
        if _TYPE.fullmatch(self.relation) is None or self.from_record_id == self.to_record_id:
            raise ValueError("memory links require a named relation between distinct records")


@dataclass(frozen=True, slots=True)
class MemoryGrant:
    """Explicit Universe/Creator anchor grant to one workspace project."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    anchor_kind: MemoryAnchorKind
    anchor_id: UUID
    granted_by: UUID
    can_write: bool
    created_at: datetime
    revoked_at: datetime | None = None

    @property
    def active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True, slots=True)
class AllowedAnchor:
    """Precomputed authorization input accepted by repository retrieval."""

    workspace_id: UUID
    scope: MemoryScope
    anchor_id: UUID


@dataclass(frozen=True, slots=True)
class MemoryConflict:
    """Candidate revision that remains inert until an authorized decision."""

    id: UUID
    workspace_id: UUID
    current_record_id: UUID
    candidate_record_id: UUID
    candidate_resolutions: tuple[str, ...]
    status: MemoryConflictStatus
    proposed_by: UUID
    proposed_at: datetime
    decided_by: UUID | None = None
    decided_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetentionEvaluation:
    """Eligibility and deterministic score multiplier."""

    eligible: bool
    multiplier: float
    reason: OmissionReason | None = None


@dataclass(frozen=True, slots=True)
class RankedMemory:
    """Authorized eligible record plus its stable score."""

    record: MemoryRecord
    score: float


@dataclass(frozen=True, slots=True)
class ContextOmission:
    """Machine-readable excluded item; record id is absent for denied anchors."""

    reason: OmissionReason
    scope: MemoryScope
    memory_type: str | None
    record_id: UUID | None


@dataclass(frozen=True, slots=True)
class ContextItem:
    """One immutable context selection with source lineage."""

    record_id: UUID
    scope: MemoryScope
    memory_type: str
    content: str
    score: float
    provenance: MemoryProvenance


@dataclass(frozen=True, slots=True)
class ContextPackage:
    """Budgeted snapshot consumed by Agents instead of raw memory tables."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    task_reference: str
    budget_chars: int
    used_chars: int
    allowed_anchors: tuple[AllowedAnchor, ...]
    items: tuple[ContextItem, ...]
    omissions: tuple[ContextOmission, ...]
    checksum: str
    created_by: UUID
    created_at: datetime
    budget_tokens: int | None = None
    used_tokens: int = 0

    def __post_init__(self) -> None:
        if _REFERENCE.fullmatch(self.task_reference) is None:
            raise ValueError("context task must be an opaque reference")
        if self.budget_chars < 1 or not 0 <= self.used_chars <= self.budget_chars:
            raise ValueError("context package must respect a positive character budget")
        if self.budget_tokens is not None and (
            self.budget_tokens < 1 or not 0 <= self.used_tokens <= self.budget_tokens
        ):
            raise ValueError("context package must respect its positive token budget")

    @property
    def reference(self) -> str:
        return f"memory-context://{self.id}"


@dataclass(frozen=True, slots=True)
class CompressionDraft:
    """Deterministic compressor output with complete source lineage."""

    content: str
    source_record_ids: tuple[UUID, ...]
