"""Deterministic technical executor used before real capability adapters exist."""

from __future__ import annotations

import asyncio

from accos.modules.workflows.domain import (
    RetryableStepError,
    StepExecution,
    StepExecutionResult,
    StepKind,
)


class FrameworkSmokeExecutor:
    """Execute only fixed token, controlled failure, and controlled delay behavior."""

    def __init__(self) -> None:
        self._results: dict[str, StepExecutionResult] = {}
        self._effects: list[str] = []
        self._compensations: list[tuple[str, str]] = []

    @property
    def visible_effects(self) -> tuple[str, ...]:
        """Expose first execution per idempotency key for contract tests."""
        return tuple(self._effects)

    @property
    def compensations(self) -> tuple[tuple[str, str], ...]:
        """Expose invoked technical compensation hooks for contract tests."""
        return tuple(self._compensations)

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        """Return cached metadata on redelivery and never create duplicate effects."""
        existing = self._results.get(execution.idempotency_key)
        if existing is not None:
            return existing
        if (
            execution.kind is StepKind.CONTROLLED_FAILURE
            and execution.attempt <= execution.fail_until_attempt
        ):
            raise RetryableStepError("workflow-error://controlled-failure")
        if execution.kind is StepKind.DELAY and execution.delay_seconds:
            await asyncio.sleep(execution.delay_seconds)
        result = StepExecutionResult(
            f"workflow-output://{execution.workflow_run_id}/{execution.step_key}"
        )
        self._results[execution.idempotency_key] = result
        self._effects.append(execution.idempotency_key)
        return result

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        """Record a deterministic hook call; real compensators arrive with owning modules."""
        marker = (execution.idempotency_key, hook)
        if marker not in self._compensations:
            self._compensations.append(marker)
