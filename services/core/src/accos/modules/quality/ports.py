"""Quality evaluator and persistence ports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.modules.quality.domain import (
        EvaluationEvidence,
        EvaluationRun,
        EvaluatorReport,
        QualityResult,
        RubricVersion,
    )


class QualityEvaluator(Protocol):
    key: str
    version: str

    async def evaluate(self, evidence: EvaluationEvidence) -> EvaluatorReport: ...


class QualityRepository(Protocol):
    async def add_rubric(self, rubric: RubricVersion) -> RubricVersion: ...

    async def get_rubric(
        self, workspace_id: UUID, project_id: UUID, rubric_id: UUID
    ) -> RubricVersion | None: ...

    async def add_run(self, run: EvaluationRun, event: EventEnvelope) -> EvaluationRun: ...

    async def get_run(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> EvaluationRun | None: ...

    async def finish_run(
        self,
        run: EvaluationRun,
        result: QualityResult,
        event: EventEnvelope,
    ) -> tuple[EvaluationRun, QualityResult]: ...

    async def get_result(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> QualityResult | None: ...
