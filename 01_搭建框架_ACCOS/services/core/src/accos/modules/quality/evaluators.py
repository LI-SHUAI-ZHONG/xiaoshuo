"""Truthful Null and deterministic structural quality evaluators."""

from __future__ import annotations

from accos.modules.quality.domain import (
    DimensionStatus,
    EvaluationEvidence,
    EvaluationOutcome,
    EvaluatorReport,
    QualityStatus,
    ScoreDimension,
)


class NullQualityEvaluator:
    key = "semantic-quality"
    version = "0.0.0"

    async def evaluate(self, evidence: object) -> EvaluatorReport:  # noqa: ARG002
        return EvaluatorReport(
            self.key,
            self.version,
            EvaluationOutcome(
                QualityStatus.NOT_CONFIGURED,
                (),
                "quality-result://not-configured",
            ),
        )


class StructuralQualityEvaluator:
    """Evaluate only the upstream consistency gate, not creative quality."""

    key = "structural-quality"
    version = "1.0.0"

    async def evaluate(self, evidence: object) -> EvaluatorReport:
        if not isinstance(evidence, EvaluationEvidence):
            raise TypeError("structural quality requires evaluation evidence")
        passed = evidence.consistency_status == "passed"
        status = QualityStatus.PASSED if passed else QualityStatus.FAILED
        return EvaluatorReport(
            self.key,
            self.version,
            EvaluationOutcome(
                status,
                (
                    ScoreDimension(
                        "structural-consistency",
                        DimensionStatus.PASSED if passed else DimensionStatus.FAILED,
                    ),
                ),
                f"quality-result://{status.value}",
            ),
        )
