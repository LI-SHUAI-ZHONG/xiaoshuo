"""Stage 28 domain acceptance contracts (registered now, executed in Stage 45)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from accos.modules.workflows.public import (
    ConditionExpression,
    ConditionOperator,
    InputResolutionStatus,
    MisfirePolicy,
    ReadReceipt,
    RequirementFreshness,
    ResolvedInput,
    RetryPolicy,
    ScheduleStatus,
    StageRequirement,
    StepDefinition,
    StepInputManifest,
    StepKind,
    StepRunStatus,
    WorkflowDefinition,
    WorkflowSchedule,
    condition_matches,
    manifest_digest,
    ready_step_keys,
    topological_steps,
)

NOW = datetime(2026, 10, 27, tzinfo=UTC)
HASH = "a" * 64


def step(
    key: str,
    position: int,
    *,
    depends_on: tuple[str, ...] = (),
    condition: ConditionExpression | None = None,
) -> StepDefinition:
    return StepDefinition(
        uuid4(),
        key,
        position,
        StepKind.REFERENCE,
        30.0,
        RetryPolicy(),
        executor_key=f"agent.{key}",
        depends_on=depends_on,
        condition=condition or ConditionExpression(),
    )


def definition(*steps: StepDefinition, graph_version: int = 2) -> WorkflowDefinition:
    return WorkflowDefinition(
        uuid4(),
        "stage28-fixture",
        1,
        tuple(steps),
        NOW,
        graph_version=graph_version,
    )


def test_t024_rejects_cycles_and_adapts_legacy_positions_to_linear_edges() -> None:
    with pytest.raises(ValueError, match="acyclic"):
        definition(
            step("a", 0, depends_on=("b",)),
            step("b", 1, depends_on=("a",)),
        )

    legacy = definition(step("a", 0), step("b", 1), step("c", 2), graph_version=1)
    assert [legacy.dependencies_for(item) for item in legacy.steps] == [(), ("a",), ("b",)]
    assert tuple(item.key for item in topological_steps(legacy)) == ("a", "b", "c")


def test_t024_diamond_join_waits_for_both_branches_and_records_condition_skip() -> None:
    graph = definition(
        step("root", 0),
        step("left", 1, depends_on=("root",)),
        step(
            "right",
            2,
            depends_on=("root",),
            condition=ConditionExpression(
                ConditionOperator.OUTPUT_REFERENCE_EQUALS,
                "root",
                "asset-version://approved",
            ),
        ),
        step("join", 3, depends_on=("left", "right")),
    )

    assert ready_step_keys(graph, {}) == ("root",)
    assert ready_step_keys(graph, {"root": StepRunStatus.SUCCEEDED}) == ("left", "right")
    assert ready_step_keys(
        graph,
        {
            "root": StepRunStatus.SUCCEEDED,
            "left": StepRunStatus.SUCCEEDED,
            "right": StepRunStatus.SKIPPED,
        },
    ) == ("join",)
    assert not condition_matches(
        graph.steps[2],
        dependency_statuses={"root": StepRunStatus.SUCCEEDED},
        dependency_outputs={"root": "asset-version://not-approved"},
    )


def test_t024_conditions_and_iterations_are_bounded_declarative_metadata() -> None:
    with pytest.raises(ValueError, match="direct dependency"):
        step(
            "unsafe",
            0,
            condition=ConditionExpression(ConditionOperator.STATUS_EQUALS, "other", "succeeded"),
        )
    with pytest.raises(ValueError, match="bounded"):
        replace(step("bounded", 0), max_iterations=101)
    with pytest.raises(ValueError, match="operation-key"):
        replace(step("side-effect", 0), external_side_effect=True)


def test_t025_manifest_freezes_exact_authorized_versions_and_digest() -> None:
    resolved = ResolvedInput(
        "canon",
        "artifact-version://canon/7",
        "7",
        HASH,
        3,
        InputResolutionStatus.READY,
        NOW,
        "grant-11",
        "consent-4",
    )
    manifest = StepInputManifest(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        4,
        uuid4(),
        "agent.writer",
        (resolved,),
        "prompt.writer@3",
        "model.policy@5",
        "workflow.policy@2",
        "rbac-9",
        "grant-11",
        "consent-4",
        "budget-reservation://fixture",
        "0" * 64,
        NOW,
    )
    frozen = replace(manifest, input_digest=manifest_digest(manifest))

    assert frozen.input_digest == manifest_digest(frozen)
    assert manifest_digest(replace(frozen, model_pin="model.policy@6")) != frozen.input_digest


def test_t025_unready_inputs_cannot_carry_partial_identity_or_fake_receipts() -> None:
    with pytest.raises(ValueError, match="partial identity"):
        ResolvedInput(
            "character",
            "artifact-version://character/2",
            None,
            None,
            None,
            InputResolutionStatus.STALE,
            NOW,
            "grant-1",
            "consent-1",
        )
    with pytest.raises(ValueError, match="byte/token"):
        ReadReceipt(
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            "artifact-version://canon/7",
            "7",
            HASH,
            "section://canon/scene-rules",
            0,
            0,
            HASH,
            NOW,
        )


def test_t025_stage_requirement_requires_explicit_freshness_contract() -> None:
    requirement = StageRequirement(
        "prior-scene",
        "scene_revision",
        "project",
        branch="main",
        freshness=RequirementFreshness.MAX_AGE,
        max_age_seconds=3_600,
    )
    assert requirement.mandatory
    with pytest.raises(ValueError, match="positive age"):
        replace(requirement, max_age_seconds=0)


def test_t028_schedule_requires_timezone_misfire_policy_and_pinned_definition() -> None:
    schedule = WorkflowSchedule(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        "daily-review",
        3,
        "0 9 * * *",
        "Asia/Shanghai",
        MisfirePolicy.FIRE_ONCE,
        ScheduleStatus.ACTIVE,
        "artifact-version://brief/9",
        NOW,
        uuid4(),
        "schedule-daily-review",
        NOW,
        NOW,
    )

    assert schedule.definition_version == 3
    assert schedule.misfire_policy is MisfirePolicy.FIRE_ONCE
    with pytest.raises(ValueError, match="non-empty"):
        replace(schedule, timezone="")
