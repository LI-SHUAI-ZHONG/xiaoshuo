"""Content-free contracts shared by the four creative data owners."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")
MAX_LABEL_LENGTH = 200


class CreativeOwner(StrEnum):
    """The only four owners permitted inside the unified creative package."""

    NOVEL = "novel"
    WORLD = "world"
    CHARACTER = "character"
    CREATOR = "creator"


class CreativeReferenceKind(StrEnum):
    """Opaque cross-boundary identifiers; referenced entities are never copied."""

    WORLD = "world"
    CHARACTER = "character"
    CREATOR = "creator"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    AGENT = "agent"
    WORKFLOW = "workflow"


class CreativeRecordStatus(StrEnum):
    """Approval lifecycle separating inert proposals from accepted facts."""

    PROPOSAL = "proposal"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CreativeDecision(StrEnum):
    """Explicit decisions supported by the skeleton."""

    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CreativeReference:
    """A typed identifier pointing at another public aggregate."""

    kind: CreativeReferenceKind
    id: UUID


@dataclass(frozen=True, slots=True)
class CreativeContainer:
    """Common metadata for an empty, project-scoped creative container."""

    owner: ClassVar[CreativeOwner]
    id: UUID
    workspace_id: UUID
    project_id: UUID
    label: str
    references: tuple[CreativeReference, ...]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    version: int = 1

    def __post_init__(self) -> None:
        if not self.label or self.label.strip() != self.label or len(self.label) > MAX_LABEL_LENGTH:
            raise ValueError(
                "creative label must be non-empty, trimmed, and at most 200 characters"
            )
        if len(set(self.references)) != len(self.references):
            raise ValueError("creative references must be unique")
        if self.version < 1:
            raise ValueError("creative container version must be positive")
        if not _aware(self.created_at) or not _aware(self.updated_at):
            raise ValueError("creative timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("creative updated_at cannot precede created_at")

    @property
    def reference(self) -> str:
        """Return the stable Workflow-safe reference for this container."""
        return f"creative://{self.owner.value}/{self.id}"


@dataclass(frozen=True, slots=True)
class CreativeRecord:
    """Versioned state metadata with no prose, prompt, or generated content."""

    owner: ClassVar[CreativeOwner]
    entity_type: ClassVar[str]
    id: UUID
    logical_id: UUID
    record_version: int
    workspace_id: UUID
    project_id: UUID
    aggregate_id: UUID
    status: CreativeRecordStatus
    current: bool
    references: tuple[CreativeReference, ...]
    source_reference: str | None
    sequence: int | None
    created_by: UUID
    created_at: datetime
    causation_id: UUID | None = None
    source_event_id: UUID | None = None
    decided_by: UUID | None = None
    decided_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.record_version < 1:
            raise ValueError("creative record version must be positive")
        if self.current != (self.status is CreativeRecordStatus.CURRENT):
            raise ValueError("only accepted current records may be current")
        if len(set(self.references)) != len(self.references):
            raise ValueError("creative record references must be unique")
        if (
            self.source_reference is not None
            and _REFERENCE.fullmatch(self.source_reference) is None
        ):
            raise ValueError("source_reference must be an opaque URI")
        if self.sequence is not None and self.sequence < 0:
            raise ValueError("creative sequence cannot be negative")
        if (self.causation_id is None) != (self.source_event_id is None):
            raise ValueError("causation_id and source_event_id must be supplied together")
        if not _aware(self.created_at) or (
            self.decided_at is not None and not _aware(self.decided_at)
        ):
            raise ValueError("creative record timestamps must be timezone-aware")
        if (self.decided_by is None) != (self.decided_at is None):
            raise ValueError("creative decision actor and timestamp must be supplied together")

    @property
    def reference(self) -> str:
        """Return a stable record reference without exposing persistence details."""
        return f"creative-record://{self.owner.value}/{self.id}"


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
