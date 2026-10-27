"""Fixed Canon-quality workflow and strict stage executor boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from accos.modules.consistency.application import ApplyResolutionCommand
from accos.modules.consistency.domain import ResolutionStatus, ValidationStatus
from accos.modules.quality.public import QualityStatus
from accos.modules.workflows.public import (
    PermanentStepError,
    RetryPolicy,
    StepDefinition,
    StepExecutionResult,
    StepKind,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from accos.modules.consistency.application import ConsistencyService
    from accos.modules.quality.public import QualityService
    from accos.modules.workflows.public import StepExecution, StepExecutor

CANON_QUALITY_NAME = "canon_quality_gate"
DRAFT_STEP = "draft"
CONSISTENCY_STEP = "consistency-check"
QUALITY_STEP = "quality-check"
APPROVAL_STEP = "approval"
ACCEPTED_REVISION_STEP = "accepted-revision"
MEMORY_UPDATE_STEP = "memory-update"


class CanonQualityGate(Protocol):
    """Durable stage operations supplied by owning public application services."""

    async def execute_stage(self, execution: StepExecution) -> StepExecutionResult: ...


def canon_quality_definition() -> WorkflowDefinition:
    """Draft -> checks -> human approval -> owner revision -> memory update."""
    retry = RetryPolicy(max_attempts=3, initial_delay_seconds=1.0)
    keys = (
        DRAFT_STEP,
        CONSISTENCY_STEP,
        QUALITY_STEP,
        APPROVAL_STEP,
        ACCEPTED_REVISION_STEP,
        MEMORY_UPDATE_STEP,
    )
    ids = tuple(UUID(f"d1000000-0000-4000-8000-{index:012d}") for index in range(11, 17))
    steps = tuple(
        StepDefinition(
            ids[position],
            key,
            position,
            StepKind.APPROVAL if key == APPROVAL_STEP else StepKind.REFERENCE,
            30.0,
            retry,
            approval_expires_seconds=3600.0 if key == APPROVAL_STEP else None,
        )
        for position, key in enumerate(keys)
    )
    return WorkflowDefinition(
        UUID("d1000000-0000-4000-8000-000000000001"),
        CANON_QUALITY_NAME,
        1,
        steps,
        datetime(2026, 9, 6, tzinfo=UTC),
    )


class CanonQualityWorkflowExecutor:
    """Route only owned stages; any gate failure is a real workflow failure."""

    def __init__(self, fallback: StepExecutor, gate: CanonQualityGate) -> None:
        self._fallback = fallback
        self._gate = gate

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        if execution.step_key not in {
            DRAFT_STEP,
            CONSISTENCY_STEP,
            QUALITY_STEP,
            ACCEPTED_REVISION_STEP,
            MEMORY_UPDATE_STEP,
        }:
            return await self._fallback.execute(execution)
        if execution.context is None or execution.context.project_id is None:
            raise PermanentStepError("consistency-error://missing-context")
        return await self._gate.execute_stage(execution)

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        await self._fallback.compensate(execution, hook)


class PersistedCanonQualityGate:
    """Verify persisted checks and approvals before the owner revision is called."""

    def __init__(self, consistency: ConsistencyService, quality: QualityService) -> None:
        self._consistency = consistency
        self._quality = quality

    async def execute_stage(self, execution: StepExecution) -> StepExecutionResult:
        context = execution.context
        if context is None or context.project_id is None:
            raise PermanentStepError("consistency-error://missing-context")
        project_id = context.project_id
        if execution.step_key == MEMORY_UPDATE_STEP:
            proposal_id = _applied_reference(execution.input_reference)
            trace = await self._consistency.trace(context, project_id, proposal_id)
            if trace.proposal.status is not ResolutionStatus.APPLIED:
                raise PermanentStepError("consistency-error://resolution-not-applied")
            return StepExecutionResult(f"memory-update://no-content/{proposal_id}")
        check_id, quality_id, proposal_id, proposal_version = _gate_reference(
            execution.input_reference
        )
        if execution.step_key == DRAFT_STEP:
            return StepExecutionResult(execution.input_reference)
        if execution.step_key == CONSISTENCY_STEP:
            check = await self._consistency.get_check(context, project_id, check_id)
            if check.status is not ValidationStatus.PASSED:
                raise PermanentStepError(f"consistency-error://blocked/{check.status.value}")
            return StepExecutionResult(execution.input_reference)
        if execution.step_key == QUALITY_STEP:
            result = await self._quality.get_result(context, project_id, quality_id)
            if result.status is not QualityStatus.PASSED:
                raise PermanentStepError(f"quality-error://blocked/{result.status.value}")
            return StepExecutionResult(execution.input_reference)
        if execution.step_key == ACCEPTED_REVISION_STEP:
            proposal = await self._consistency.apply_resolution(
                context,
                ApplyResolutionCommand(project_id, proposal_id, proposal_version),
            )
            if proposal.result is None:
                raise PermanentStepError("consistency-error://missing-applied-revision")
            return StepExecutionResult(
                f"consistency-resolution://{proposal.id}/applied/{proposal.result.version}"
            )
        raise PermanentStepError("consistency-error://unsupported-stage")


def _gate_reference(reference: str) -> tuple[UUID, UUID, UUID, int]:
    try:
        check, quality, proposal, version = reference.removeprefix("canon-gate://").split(
            "/", maxsplit=3
        )
        if not reference.startswith("canon-gate://"):
            raise ValueError
        parsed_version = int(version)
        if parsed_version < 1:
            raise ValueError
        return UUID(check), UUID(quality), UUID(proposal), parsed_version
    except (TypeError, ValueError) as error:
        raise PermanentStepError("consistency-error://invalid-gate-reference") from error


def _applied_reference(reference: str) -> UUID:
    try:
        proposal, state, version = reference.removeprefix("consistency-resolution://").split(
            "/", maxsplit=2
        )
        if (
            not reference.startswith("consistency-resolution://")
            or state != "applied"
            or int(version) < 1
        ):
            raise ValueError
        return UUID(proposal)
    except (TypeError, ValueError) as error:
        raise PermanentStepError("consistency-error://invalid-resolution-reference") from error
