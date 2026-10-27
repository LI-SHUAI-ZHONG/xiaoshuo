"""Framework-free Canon, evidence, finding, and resolution contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.kernel.errors import ConcurrencyConflictError

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class CanonLevel(StrEnum):
    """Protection tiers; level one is the hardest invariant."""

    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"


class CanonStatus(StrEnum):
    """Explicit Canon lifecycle."""

    PROPOSAL = "proposal"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class FindingType(StrEnum):
    """Deterministic structural violation categories."""

    REQUIRED_FIELD = "required_field"
    INVALID_REFERENCE = "invalid_reference"
    TIME_ORDER = "time_order"
    MUTEX_STATE = "mutex_state"
    VERSION_CONFLICT = "version_conflict"
    PROTECTED_CANON = "protected_canon"
    UNRESOLVED_DEPENDENCY = "unresolved_dependency"


class FindingSeverity(StrEnum):
    """Stable machine severity without prose scoring content."""

    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


class FindingStatus(StrEnum):
    """Finding disposition."""

    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ValidationStatus(StrEnum):
    """Never collapse absence, failure, findings, and a real pass."""

    NOT_RUN = "not_run"
    NOT_CONFIGURED = "not_configured"
    RUN_FAILED = "run_failed"
    FINDINGS = "findings"
    PASSED = "passed"


class ResolutionStatus(StrEnum):
    """Human-controlled proposal lifecycle."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLYING = "applying"
    APPLIED = "applied"
    REJECTED = "rejected"


class ResolutionDecision(StrEnum):
    """Allowed human decisions."""

    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CanonEntry:
    """Versioned cross-domain constraint, never a copy of an owner state."""

    id: UUID
    logical_id: UUID
    workspace_id: UUID
    project_id: UUID
    canon_key: str
    level: CanonLevel
    entry_version: int
    valid_from: datetime
    valid_until: datetime | None
    source_reference: str
    status: CanonStatus
    created_by: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """Normalized assertion pointing to an authoritative event or revision."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    event_reference: str
    occurred_at: datetime
    sequence: int
    character_state_references: tuple[str, ...]
    world_state_references: tuple[str, ...]
    source_version: int


@dataclass(frozen=True, slots=True)
class RuleConstraint:
    """Content-free rule relation owned by Canon."""

    id: UUID
    canon_entry_id: UUID
    constraint_code: str
    subject_reference: str
    object_reference: str | None


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """Directed dependency between two opaque evidence references."""

    id: UUID
    source_reference: str
    target_reference: str
    resolved: bool


@dataclass(frozen=True, slots=True)
class RequiredFieldAssertion:
    evidence_reference: str
    field_code: str
    present: bool


@dataclass(frozen=True, slots=True)
class ReferenceAssertion:
    evidence_reference: str
    exists: bool


@dataclass(frozen=True, slots=True)
class TimelineAssertion:
    event_reference: str
    occurred_at: datetime
    predecessor_reference: str | None = None
    predecessor_occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EntityStateAssertion:
    entity_reference: str
    state_code: str
    mutex_group: str
    current: bool = True


@dataclass(frozen=True, slots=True)
class VersionAssertion:
    evidence_reference: str
    expected_version: int
    current_version: int


@dataclass(frozen=True, slots=True)
class CanonChangeAssertion:
    canon_reference: str
    level: CanonLevel
    modifies_current: bool
    explicitly_authorized: bool


@dataclass(frozen=True, slots=True)
class ValidationBundle:
    """Bounded, page-sized read-only evidence projection."""

    required_fields: tuple[RequiredFieldAssertion, ...] = ()
    references: tuple[ReferenceAssertion, ...] = ()
    timeline: tuple[TimelineAssertion, ...] = ()
    entity_states: tuple[EntityStateAssertion, ...] = ()
    versions: tuple[VersionAssertion, ...] = ()
    canon_changes: tuple[CanonChangeAssertion, ...] = ()
    dependencies: tuple[DependencyEdge, ...] = ()
    cursor: str | None = None
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class FindingDraft:
    finding_type: FindingType
    severity: FindingSeverity
    evidence_references: tuple[str, ...]
    message_code: str


@dataclass(frozen=True, slots=True)
class ValidatorReport:
    validator_key: str
    validator_version: str
    status: ValidationStatus
    findings: tuple[FindingDraft, ...] = ()
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.status is ValidationStatus.FINDINGS and not self.findings:
            raise ValueError("a findings report must contain findings")
        if self.status is not ValidationStatus.FINDINGS and self.findings:
            raise ValueError("only a findings report may contain findings")
        if (self.status is ValidationStatus.RUN_FAILED) != (self.error_code is not None):
            raise ValueError("only a failed validator run has an error code")


@dataclass(frozen=True, slots=True)
class ConsistencyCheckRun:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    workflow_run_id: UUID | None
    requested_by: UUID
    status: ValidationStatus
    reports: tuple[ValidatorReport, ...]
    created_at: datetime

    @property
    def reference(self) -> str:
        return f"consistency-run://{self.id}"


@dataclass(frozen=True, slots=True)
class Finding:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    check_run_id: UUID
    finding_type: FindingType
    severity: FindingSeverity
    evidence_references: tuple[str, ...]
    message_code: str
    validator_key: str
    validator_version: str
    status: FindingStatus
    workflow_run_id: UUID | None
    detected_by: UUID
    detected_at: datetime

    @property
    def reference(self) -> str:
        return f"consistency-finding://{self.id}"


@dataclass(frozen=True, slots=True)
class EvidenceProjection:
    """Disposable pointer-only view rebuilt from authoritative public events."""

    reference: str
    owner: str
    entity_id: UUID
    revision_id: UUID
    revision_version: int
    projected_at: datetime


@dataclass(frozen=True, slots=True)
class FactTarget:
    """Target owned by Novel, World, or Character; Consistency never writes it."""

    reference: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class AppliedRevision:
    reference: str
    version: int


@dataclass(frozen=True, slots=True)
class ResolutionProposal:
    """Content-free repair strategy awaiting explicit approval and revalidation."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    finding_ids: tuple[UUID, ...]
    strategy_code: str
    target: FactTarget
    impact_references: tuple[str, ...]
    requires_approval: bool
    status: ResolutionStatus
    requested_by: UUID
    workflow_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    approved_by: UUID | None = None
    applied_by: UUID | None = None
    result: AppliedRevision | None = None
    version: int = 1

    @property
    def reference(self) -> str:
        return f"consistency-resolution://{self.id}"


@dataclass(frozen=True, slots=True)
class ResolutionTrace:
    proposal: ResolutionProposal
    findings: tuple[Finding, ...]


class TargetVersionConflictError(ConcurrencyConflictError):
    """Optimistic conflict that exposes only the safe current version."""

    def __init__(self, current_version: int) -> None:
        super().__init__()
        self.current_version = current_version
        self.details["current_version"] = current_version
