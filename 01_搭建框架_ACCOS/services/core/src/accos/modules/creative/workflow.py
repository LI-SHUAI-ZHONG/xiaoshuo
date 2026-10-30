"""Workflow adapter for resolving creative containers without reading private tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from accos.modules.creative.common import CreativeOwner
from accos.modules.workflows.public import (
    PermanentStepError,
    RetryPolicy,
    StepDefinition,
    StepExecutionResult,
    StepKind,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from accos.kernel.security import SecurityContext
    from accos.modules.creative.common import CreativeContainer
    from accos.modules.workflows.public import StepExecution, StepExecutor

CREATIVE_REFERENCE_NAME = "creative_reference"
CREATIVE_REFERENCE_STEP = "creative-reference"


class CreativeReferenceReader(Protocol):
    async def resolve(
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer: ...


def creative_reference_definition() -> WorkflowDefinition:
    """Return the metadata-only workflow definition for creative references."""
    return WorkflowDefinition(
        UUID("c1000000-0000-4000-8000-000000000001"),
        CREATIVE_REFERENCE_NAME,
        1,
        (
            StepDefinition(
                UUID("c1000000-0000-4000-8000-000000000011"),
                CREATIVE_REFERENCE_STEP,
                0,
                StepKind.REFERENCE,
                10.0,
                RetryPolicy(),
            ),
        ),
        datetime(2026, 9, 6, tzinfo=UTC),
    )


class CreativeWorkflowExecutor:
    """Resolve only creative reference steps and delegate all other work."""

    def __init__(self, fallback: StepExecutor, reader: CreativeReferenceReader) -> None:
        self._fallback = fallback
        self._reader = reader

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        if execution.step_key != CREATIVE_REFERENCE_STEP:
            return await self._fallback.execute(execution)
        if execution.context is None or execution.context.project_id is None:
            raise PermanentStepError("creative-error://missing-context")
        try:
            if not execution.input_reference.startswith("creative://"):
                raise ValueError
            owner_value, identifier = execution.input_reference.removeprefix("creative://").split(
                "/", maxsplit=1
            )
            owner = CreativeOwner(owner_value)
            container_id = UUID(identifier)
        except ValueError as error:
            raise PermanentStepError("creative-error://invalid-reference") from error
        container = await self._reader.resolve(
            execution.context,
            execution.context.project_id,
            owner,
            container_id,
        )
        return StepExecutionResult(f"creative-result://{owner.value}/{container.id}")

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        await self._fallback.compensate(execution, hook)
