"""Framework-free rubric metadata and quality result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class QualityStatus(StrEnum):
    """Distinct absence, configuration, execution, pass, and issue states."""

    NOT_RUN = "not_run"
    NOT_CONFIGURED = "not_configured"
    RUN_FAILED = "run_failed"
    PASSED = "passed"
    FAILED = "failed"


class DimensionStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RubricVersion:
    """Versioned schema metadata with no weights or creative criteria."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    rubric_key: str
    version: int
    schema_version: str
    dimension_keys: tuple[str, ...]
    created_by: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    rubric_id: UUID
    input_reference: str
    workflow_run_id: UUID | None
    requested_by: UUID
    status: QualityStatus
    created_at: datetime
    completed_at: datetime | None = None

    @property
    def reference(self) -> str:
        return f"quality-run://{self.id}"


@dataclass(frozen=True, slots=True)
class ScoreDimension:
    """Machine result for one schema key; score remains optional."""

    key: str
    status: DimensionStatus
    score: float | None = None


@dataclass(frozen=True, slots=True)
class QualityResult:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    evaluation_run_id: UUID
    status: QualityStatus
    evaluator_key: str
    evaluator_version: str
    dimensions: tuple[ScoreDimension, ...]
    result_reference: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    input_reference: str
    consistency_status: str


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    status: QualityStatus
    dimensions: tuple[ScoreDimension, ...]
    result_reference: str


@dataclass(frozen=True, slots=True)
class EvaluatorReport:
    evaluator_key: str
    evaluator_version: str
    outcome: EvaluationOutcome
