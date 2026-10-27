"""Built-in technical workflow definitions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from accos.modules.workflows.domain import (
    RetryPolicy,
    StepDefinition,
    StepKind,
    WorkflowDefinition,
)

FRAMEWORK_SMOKE_NAME = "framework_smoke"


def framework_smoke_definition() -> WorkflowDefinition:
    """Return the immutable v1 smoke definition with no creative behavior."""
    retry = RetryPolicy(max_attempts=3, initial_delay_seconds=1.0, maximum_delay_seconds=8.0)
    return WorkflowDefinition(
        id=UUID("a1000000-0000-4000-8000-000000000001"),
        name=FRAMEWORK_SMOKE_NAME,
        version=1,
        steps=(
            StepDefinition(
                UUID("a1000000-0000-4000-8000-000000000011"),
                "pass-token",
                0,
                StepKind.REFERENCE,
                10.0,
                retry,
            ),
            StepDefinition(
                UUID("a1000000-0000-4000-8000-000000000012"),
                "controlled-retry",
                1,
                StepKind.CONTROLLED_FAILURE,
                10.0,
                retry,
                fail_until_attempt=1,
                compensation_hook="framework-smoke-compensation.v1",
            ),
            StepDefinition(
                UUID("a1000000-0000-4000-8000-000000000013"),
                "controlled-delay",
                2,
                StepKind.DELAY,
                10.0,
                retry,
                delay_seconds=0.01,
            ),
        ),
        created_at=datetime(2026, 9, 4, tzinfo=UTC),
    )
