"""Framework-free feedback, metric, diagnostic, and experiment contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class FeedbackSource(StrEnum):
    """The four explicit origins accepted by the feedback boundary."""

    USER = "user"
    SYSTEM = "system"
    CREATIVE_RESULT = "creative-result"
    BEHAVIOR_CONSENTED = "behavior-consented"


class ConsentStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class FeedbackStatus(StrEnum):
    ACTIVE = "active"
    ANONYMIZED = "anonymized"


class MetricSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class DiagnosticSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExperimentStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class ArtifactKind(StrEnum):
    METRIC_POINT = "metric-point"
    EXPERIMENT_SAMPLE = "experiment-sample"
    CREATOR_SIGNAL = "creator-signal"


class TombstoneAction(StrEnum):
    RECOMPUTE = "recompute"
    EXCLUDE = "exclude"


@dataclass(frozen=True, slots=True)
class BehaviorConsent:
    """Consent audit metadata; it intentionally contains no behavior payload."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID
    policy_version: str
    status: ConsentStatus
    granted_at: datetime
    withdrawn_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """Bounded structured signal; prose and raw prompts are not accepted fields."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID | None
    source: FeedbackSource
    schema_version: str
    signal_code: str
    numeric_value: float | None
    source_reference: str | None
    consent_id: UUID | None
    status: FeedbackStatus
    occurred_at: datetime
    creator_signal_reference: str | None = None

    @property
    def reference(self) -> str:
        return f"feedback-event://{self.id}"


@dataclass(frozen=True, slots=True)
class MetricDimension:
    """Finite dimension vocabulary that prevents unbounded label cardinality."""

    key: str
    allowed_values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    name: str
    version: int
    unit: str
    dimensions: tuple[MetricDimension, ...]
    retention_days: int
    sensitivity: MetricSensitivity
    created_by: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MetricPoint:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    metric_definition_id: UUID
    metric_name: str
    value: float
    dimensions: tuple[tuple[str, str], ...]
    observed_at: datetime
    source_reference: str
    source_feedback_event_id: UUID | None = None
    included: bool = True
    tombstoned_at: datetime | None = None

    @property
    def reference(self) -> str:
        return f"metric-point://{self.id}"


@dataclass(frozen=True, slots=True)
class DiagnosticFinding:
    """Deterministic System Doctor output with no mutating capability."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    metric_point_id: UUID
    rule_key: str
    rule_version: str
    finding_code: str
    severity: DiagnosticSeverity
    observed_value: float
    threshold_value: float
    created_at: datetime

    @property
    def reference(self) -> str:
        return f"diagnostic-finding://{self.id}"


@dataclass(frozen=True, slots=True)
class Experiment:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    experiment_key: str
    protocol_version: str
    hypothesis_code: str
    primary_metric_name: str
    sample_scope: str
    starts_at: datetime
    ends_at: datetime
    stop_condition_codes: tuple[str, ...]
    status: ExperimentStatus
    created_by: UUID
    created_at: datetime
    result_code: str | None = None


@dataclass(frozen=True, slots=True)
class Variant:
    id: UUID
    experiment_id: UUID
    variant_key: str
    configuration_reference: str


@dataclass(frozen=True, slots=True)
class ExperimentSample:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    experiment_id: UUID
    variant_id: UUID
    metric_point_id: UUID
    source_feedback_event_id: UUID | None
    observed_at: datetime
    included: bool = True
    tombstoned_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DerivedArtifactTombstone:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    source_feedback_event_id: UUID
    artifact_kind: ArtifactKind
    artifact_reference: str
    action: TombstoneAction
    reason_code: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WithdrawalResult:
    consent: BehaviorConsent
    anonymized_event_ids: tuple[UUID, ...]
    tombstones: tuple[DerivedArtifactTombstone, ...]
