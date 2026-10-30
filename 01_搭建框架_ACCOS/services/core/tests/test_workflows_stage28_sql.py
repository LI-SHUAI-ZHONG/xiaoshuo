"""Stage 28 PostgreSQL contracts (registered now, executed in Stage 45)."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from accos.adapters.persistence import DatabaseRuntime, EngineOptions
from accos.adapters.workflows import SqlAlchemyWorkflowRepository
from accos.kernel.errors import InvalidStateError
from accos.modules.workflows.public import (
    InputResolutionStatus,
    MisfirePolicy,
    ResolvedInput,
    RetryPolicy,
    ScheduleStatus,
    StageRequirement,
    StepDefinition,
    StepKind,
    TaskRunStatus,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowSchedule,
)
from test_persistence import migrated_database_url, seed_workflow_scope  # noqa: F401

NOW = datetime(2026, 10, 27, tzinfo=UTC)
HASH = "b" * 64


def _step(key: str, position: int, depends_on: tuple[str, ...] = ()) -> StepDefinition:
    return StepDefinition(
        uuid4(),
        key,
        position,
        StepKind.REFERENCE,
        30.0,
        RetryPolicy(),
        executor_key=f"agent.{key}",
        depends_on=depends_on,
    )


def _definition(*steps: StepDefinition) -> WorkflowDefinition:
    return WorkflowDefinition(
        uuid4(),
        f"stage28-{uuid4().hex}",
        1,
        tuple(steps),
        NOW,
        graph_version=2,
    )


def _run(
    actor_id: UUID,
    workspace_id: UUID,
    project_id: UUID,
    definition: WorkflowDefinition,
) -> WorkflowRun:
    return WorkflowRun(
        uuid4(),
        workspace_id,
        project_id,
        definition.id,
        definition.name,
        definition.version,
        WorkflowRunStatus.PENDING,
        f"stage28-{uuid4().hex}",
        "artifact-version://stage28/input/1",
        actor_id,
        "user",
        uuid4(),
        NOW,
        NOW,
        permission_snapshot=("agent:run", "model:run"),
        policy_version="identity-rbac-v1",
    )


def test_t024_sql_diamond_dispatches_join_once_after_both_branches(
    migrated_database_url: str,  # noqa: F811 - imported pytest fixture.
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(5, 2, 1, 60))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, NOW)
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)
            graph = _definition(
                _step("root", 0),
                _step("left", 1, ("root",)),
                _step("right", 2, ("root",)),
                _step("join", 3, ("left", "right")),
            )
            run = _run(actor_id, workspace_id, project_id, graph)
            await repository.ensure_definition(graph)
            await repository.submit(run, graph, request_digest=HASH)

            tasks = await repository.get_tasks(workspace_id, run.id)
            assert [task.status for task in tasks] == [TaskRunStatus.PENDING]
            root = await repository.claim_task(
                tasks[0].id, uuid4(), now=NOW, lease=timedelta(seconds=30)
            )
            assert root is not None
            await repository.succeed_task(
                root, output_reference="artifact-version://root/1", now=NOW
            )

            branches = [
                task
                for task in await repository.get_tasks(workspace_id, run.id)
                if task.status is TaskRunStatus.PENDING
            ]
            assert len(branches) == 2
            first = await repository.claim_task(
                branches[0].id, uuid4(), now=NOW, lease=timedelta(seconds=30)
            )
            second = await repository.claim_task(
                branches[1].id, uuid4(), now=NOW, lease=timedelta(seconds=30)
            )
            assert first is not None and second is not None
            await repository.succeed_task(
                first, output_reference="artifact-version://branch/left", now=NOW
            )
            assert len(await repository.get_tasks(workspace_id, run.id)) == 3
            await repository.succeed_task(
                second, output_reference="artifact-version://branch/right", now=NOW
            )
            join_tasks = [
                task
                for task in await repository.get_tasks(workspace_id, run.id)
                if task.status is TaskRunStatus.PENDING
            ]
            assert len(join_tasks) == 1
            assert len(await repository.get_input_manifests(workspace_id, run.id)) == 4
        finally:
            await runtime.dispose()

    asyncio.run(scenario())


def test_t025_and_t027_sql_stale_inputs_and_lost_leases_are_fenced(
    migrated_database_url: str,  # noqa: F811 - imported pytest fixture.
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(3, 1, 1, 60))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, NOW)
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)
            requirement = StageRequirement("canon", "canon_revision", "project")
            only = replace(_step("generate", 0), requirements=(requirement,))
            graph = _definition(only)
            run = _run(actor_id, workspace_id, project_id, graph)
            resolved = ResolvedInput(
                "canon",
                "artifact-version://canon/4",
                "4",
                HASH,
                2,
                InputResolutionStatus.READY,
                NOW,
                "grant-4",
                "consent-2",
            )
            await repository.ensure_definition(graph)
            await repository.submit(
                run,
                graph,
                request_digest=HASH,
                resolved_inputs={"generate": (resolved,)},
            )
            task = (await repository.get_tasks(workspace_id, run.id))[0]
            claimed = await repository.claim_task(
                task.id, uuid4(), now=NOW, lease=timedelta(seconds=30)
            )
            assert claimed is not None
            with pytest.raises(InvalidStateError, match="lease"):
                await repository.succeed_task(
                    replace(claimed, lease_token=uuid4()),
                    output_reference="artifact-version://draft/1",
                    now=NOW,
                )

            affected = await repository.invalidate_dependencies(
                workspace_id,
                resolved.reference or "",
                replacement_hash="c" * 64,
                now=NOW,
            )
            assert affected == (run.id,)
            assert not await repository.is_manifest_current(task.id, claimed.lease_token)
            stale = await repository.mark_task_stale(claimed, now=NOW)
            assert stale.status is WorkflowRunStatus.WAITING_RESOURCE
        finally:
            await runtime.dispose()

    asyncio.run(scenario())


def test_t028_sql_due_schedule_claim_is_unique_and_fenced(
    migrated_database_url: str,  # noqa: F811 - imported pytest fixture.
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(3, 1, 1, 60))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, NOW)
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)
            graph = _definition(_step("scheduled", 0))
            await repository.ensure_definition(graph)
            schedule = WorkflowSchedule(
                uuid4(),
                workspace_id,
                project_id,
                graph.id,
                graph.name,
                graph.version,
                "0 9 * * *",
                "Asia/Shanghai",
                MisfirePolicy.FIRE_ONCE,
                ScheduleStatus.ACTIVE,
                "artifact-version://schedule/input/1",
                NOW,
                actor_id,
                f"schedule-{uuid4().hex}",
                NOW,
                NOW,
            )
            await repository.save_schedule(schedule)
            first = await repository.claim_due_schedules(
                now=NOW, lease=timedelta(seconds=30), worker_id="worker-a"
            )
            second = await repository.claim_due_schedules(
                now=NOW, lease=timedelta(seconds=30), worker_id="worker-b"
            )
            assert len(first) == 1 and second == ()
            assert first[0].lease_token is not None
            with pytest.raises(InvalidStateError, match="no longer owned"):
                await repository.settle_schedule_claim(
                    schedule.id,
                    uuid4(),
                    next_due_at=NOW + timedelta(days=1),
                    last_run_id=None,
                    now=NOW,
                )
        finally:
            await runtime.dispose()

    asyncio.run(scenario())
