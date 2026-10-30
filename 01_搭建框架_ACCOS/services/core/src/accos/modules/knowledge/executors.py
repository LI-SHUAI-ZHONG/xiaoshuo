"""Workflow integration for resumable knowledge ingestion."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from accos.modules.knowledge.definitions import KNOWLEDGE_INGESTION_STEP
from accos.modules.knowledge.domain import IngestionStatus
from accos.modules.workflows.public import (
    PermanentStepError,
    RetryableStepError,
    StepExecutionResult,
)

if TYPE_CHECKING:
    from accos.modules.knowledge.application import KnowledgeService
    from accos.modules.workflows.public import StepExecution, StepExecutor


class KnowledgeWorkflowExecutor:
    """Route only the knowledge step and delegate every existing workflow step."""

    def __init__(self, fallback: StepExecutor, knowledge: KnowledgeService) -> None:
        self._fallback = fallback
        self._knowledge = knowledge

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        if execution.step_key != KNOWLEDGE_INGESTION_STEP:
            return await self._fallback.execute(execution)
        if execution.context is None or not execution.input_reference.startswith(
            "knowledge-run://"
        ):
            raise PermanentStepError("knowledge-error://invalid-run-reference")
        try:
            run_id = UUID(execution.input_reference.removeprefix("knowledge-run://"))
        except ValueError as error:
            raise PermanentStepError("knowledge-error://invalid-run-reference") from error
        run = await self._knowledge.get(execution.context, run_id)
        if run.status is IngestionStatus.FAILED and run.retryable:
            run = await self._knowledge.retry(execution.context, run_id)
        else:
            run = await self._knowledge.process(execution.context, run_id)
        if run.status is IngestionStatus.FAILED:
            if run.error_code is None:
                raise PermanentStepError("knowledge-error://invalid-failure-state")
            reference = f"knowledge-error://{run.error_code.value.lower()}"
            if run.retryable:
                raise RetryableStepError(reference)
            raise PermanentStepError(reference)
        return StepExecutionResult(f"knowledge-result://{run.document_version_id}")

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        await self._fallback.compensate(execution, hook)
