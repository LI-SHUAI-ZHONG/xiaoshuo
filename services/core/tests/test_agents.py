from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from accos.adapters.agents import InMemoryAgentRepository
from accos.adapters.models import FakeModelProvider, InMemoryUsageLedger
from accos.adapters.tools import FakeToolExecutor, InMemoryToolCallLedger
from accos.kernel.errors import (
    IdempotencyConflictError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.agents import public as agent_public
from accos.modules.agents.application import _stored_result, _typed_result, _validate_schema
from accos.modules.agents.public import (
    AGENT_PLAN_REVIEW_NAME,
    AGENT_PROTOCOL_VERSION,
    DEFAULT_AGENT_BUDGET,
    DIRECTOR_AGENT_ID,
    AgentBudget,
    AgentDescriptor,
    AgentErrorCode,
    AgentInvocation,
    AgentProposal,
    AgentResultKind,
    AgentRunStatus,
    AgentRuntimeError,
    AgentWorkflowExecutor,
    DefaultAgentSupervisor,
    FakeAgentBehavior,
    FakeAgentExecutor,
    InMemoryAgentMetrics,
    InMemoryAgentRegistry,
    MasterOrchestrator,
    PromptMetadataReference,
    ProtectedOperation,
    RawAgentResult,
    SupervisedAgentResult,
    WorkflowPlanProposal,
    WorkflowSelection,
    agent_plan_review_definition,
    built_in_agent_descriptors,
)
from accos.modules.identity.public import AuthorizationService, Permission
from accos.modules.models.public import ModelGateway, ModelPolicy, ModelRegistry
from accos.modules.projects.public import Project, ProjectSettings, ProjectStatus
from accos.modules.tools.public import ToolDescriptor, ToolGateway, ToolRegistry
from accos.modules.workflows.public import (
    FRAMEWORK_SMOKE_NAME,
    FrameworkSmokeExecutor,
    PermanentStepError,
    StepExecution,
    StepKind,
    WorkflowApprovalDecision,
    WorkflowRunStatus,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.modules.identity.ports import AuditEvent
    from accos.modules.memory.public import ContextPackageReader
    from accos.modules.projects.public import ProjectRepository

NOW = datetime(2026, 9, 5, 3, tzinfo=UTC)
ACTOR_ID = UUID("10000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("10000000-0000-4000-8000-000000000002")
PROJECT_ID = UUID("10000000-0000-4000-8000-000000000003")
CORRELATION_ID = UUID("10000000-0000-4000-8000-000000000004")


@dataclass(slots=True)
class FixedClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value


class MemoryAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class ProjectRepositoryDouble:
    def __init__(self, item: Project | None) -> None:
        self.item = item

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        if (
            self.item is None
            or self.item.workspace_id != workspace_id
            or self.item.id != project_id
        ):
            return None
        return self.item


class ContextPackages:
    def __init__(self, package_id: UUID) -> None:
        self.package_id = package_id

    async def get_package(
        self, workspace_id: UUID, project_id: UUID, package_id: UUID
    ) -> object | None:
        if (
            workspace_id == WORKSPACE_ID
            and project_id == PROJECT_ID
            and package_id == self.package_id
        ):
            return object()
        return None


@dataclass(slots=True)
class RuntimeHarness:
    supervisor: DefaultAgentSupervisor
    registry: InMemoryAgentRegistry
    repository: InMemoryAgentRepository
    executor: FakeAgentExecutor
    model_ledger: InMemoryUsageLedger
    tool_ledger: InMemoryToolCallLedger
    metrics: InMemoryAgentMetrics
    audit: MemoryAudit
    project_repository: ProjectRepositoryDouble


def context(*, permissions: frozenset[str] | None = None) -> SecurityContext:
    return SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        WORKSPACE_ID,
        permissions
        or frozenset(
            {
                Permission.AGENT_RUN.value,
                Permission.MODEL_RUN.value,
                Permission.TOOL_RUN.value,
                Permission.APPROVAL_DECIDE.value,
            }
        ),
        "fixture-policy-v1",
        CorrelationIds(str(CORRELATION_ID), str(CORRELATION_ID)),
        PROJECT_ID,
    )


def project(*, status: ProjectStatus = ProjectStatus.ACTIVE) -> Project:
    return Project(
        PROJECT_ID,
        WORKSPACE_ID,
        "fixture-project",
        status,
        ProjectSettings(),
        ACTOR_ID,
        NOW,
        NOW,
    )


def invocation(
    key: str = "fixture-agent",
    *,
    agent_id: str = DIRECTOR_AGENT_ID,
    budget: AgentBudget = DEFAULT_AGENT_BUDGET,
    **updates: object,
) -> AgentInvocation:
    values: dict[str, object] = {
        "agent_id": agent_id,
        "input_data": {"input_reference": "fixture-token://agent-input"},
        "idempotency_key": key,
        "task_reference": f"agent-task://{agent_id}/{key}",
        "requested_budget": budget,
    }
    values.update(updates)
    return AgentInvocation(**values)  # type: ignore[arg-type]


def build_runtime(
    behaviors: Mapping[str, FakeAgentBehavior] | None = None,
    *,
    selected_project: Project | None = None,
    hard_budget: AgentBudget = DEFAULT_AGENT_BUDGET,
    tool_versions: Mapping[str, str] | None = None,
    context_packages: ContextPackageReader | None = None,
) -> RuntimeHarness:
    clock = FixedClock()
    audit = MemoryAudit()
    authorizer = AuthorizationService(audit, clock)
    model_registry = ModelRegistry()
    model_registry.register(FakeModelProvider())
    model_ledger = InMemoryUsageLedger()
    model_gateway = ModelGateway(
        model_registry,
        model_ledger,
        authorizer,
        clock,
        ModelPolicy(("fake-model",), "fake-model"),
    )
    descriptor = ToolDescriptor(
        "fixture.reference",
        "1.0.0",
        ("reference",),
        {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
        frozenset({Permission.TOOL_RUN.value}),
    )
    tool_registry = ToolRegistry()
    tool_registry.register(descriptor, FakeToolExecutor())
    tool_ledger = InMemoryToolCallLedger()
    tool_gateway = ToolGateway(tool_registry, tool_ledger, authorizer, clock)
    registry = InMemoryAgentRegistry()
    for item in built_in_agent_descriptors():
        registry.register(item)
    repository = InMemoryAgentRepository()
    metrics = InMemoryAgentMetrics()
    fake = FakeAgentExecutor(model_gateway, tool_gateway, behaviors)
    projects = ProjectRepositoryDouble(selected_project or project())
    supervisor = DefaultAgentSupervisor(
        registry,
        fake,
        repository,
        cast("ProjectRepository", projects),
        authorizer,
        metrics,
        clock,
        hard_budget,
        ({descriptor.tool_id: descriptor.version} if tool_versions is None else tool_versions),
        context_packages,
    )
    return RuntimeHarness(
        supervisor,
        registry,
        repository,
        fake,
        model_ledger,
        tool_ledger,
        metrics,
        audit,
        projects,
    )


def test_builtin_registry_contracts_and_approval_definition() -> None:
    descriptors = built_in_agent_descriptors()
    assert AGENT_PROTOCOL_VERSION == "agents.v1"
    assert tuple(item.agent_id for item in descriptors) == (
        "director",
        "research",
        "world",
        "character",
        "writer",
        "editor",
        "quality",
    )
    assert all("prompt" not in item.input_schema for item in descriptors)
    assert agent_public.AgentDescriptor is AgentDescriptor
    registry = InMemoryAgentRegistry()
    registry.register(descriptors[0])
    assert registry.get("director") is descriptors[0]
    assert registry.get("missing") is None
    assert registry.all() == (descriptors[0],)
    with pytest.raises(ValueError, match="already"):
        registry.register(descriptors[0])
    approval = agent_plan_review_definition()
    assert approval.name == AGENT_PLAN_REVIEW_NAME
    assert approval.steps[0].kind is StepKind.APPROVAL


def test_director_success_replay_and_snapshot_are_deterministic() -> None:
    harness = build_runtime()
    first = asyncio.run(harness.supervisor.run(context(), PROJECT_ID, invocation()))
    second = asyncio.run(harness.supervisor.run(context(), PROJECT_ID, invocation()))
    read_context = context(
        permissions=context().permissions | frozenset({Permission.PROJECT_READ.value})
    )
    assert asyncio.run(harness.supervisor.get(read_context, first.run.id)) == first.run
    with pytest.raises(ScopeViolationError):
        asyncio.run(harness.supervisor.get(replace(context(), workspace_id=uuid4()), first.run.id))
    assert isinstance(first.result, WorkflowSelection)
    assert first.result.workflow_name == FRAMEWORK_SMOKE_NAME
    assert second.run == first.run
    assert harness.executor.calls == ["fixture-agent"]
    assert len(harness.model_ledger.records) == 1
    snapshot = asyncio.run(
        harness.repository.get_snapshot(WORKSPACE_ID, first.run.context_snapshot_id)
    )
    assert snapshot is not None
    assert snapshot.reference == f"agent-context://{snapshot.id}"
    assert snapshot.permission_snapshot == tuple(sorted(context().permissions))
    assert snapshot.tool_versions == ()
    assert len(snapshot.input_digest) == 64
    assert asyncio.run(harness.repository.get_snapshot(uuid4(), snapshot.id)) is None
    assert asyncio.run(harness.repository.get(WORKSPACE_ID, first.run.id)) == first.run
    assert asyncio.run(harness.repository.get(uuid4(), first.run.id)) is None
    assert (
        asyncio.run(harness.repository.get_by_idempotency(WORKSPACE_ID, "fixture-agent"))
        == first.run
    )
    events = asyncio.run(harness.repository.get_events(WORKSPACE_ID, first.run.id))
    assert [item.sequence for item in events] == [1, 2]
    assert asyncio.run(
        harness.repository.get_events(WORKSPACE_ID, first.run.id, after_sequence=1)
    ) == (events[1],)
    assert harness.metrics.transitions == [
        ("director", AgentRunStatus.RUNNING),
        ("director", AgentRunStatus.SUCCEEDED),
    ]
    assert harness.audit.events[0].action == Permission.AGENT_RUN.value
    harness.project_repository.item = None
    with pytest.raises(ScopeViolationError):
        asyncio.run(harness.supervisor.get(read_context, first.run.id))


def test_agent_snapshot_traces_only_valid_context_package_references() -> None:
    async def scenario() -> None:
        package_id = uuid4()
        packages = ContextPackages(package_id)
        runtime = build_runtime(context_packages=cast("ContextPackageReader", packages))
        supervised = await runtime.supervisor.run(
            context(),
            PROJECT_ID,
            invocation(
                "fixture-agent-context",
                context_package_reference=f"memory-context://{package_id}",
            ),
        )
        snapshot = runtime.repository.snapshots[supervised.run.context_snapshot_id]
        assert snapshot.memory_context_package_id == package_id

        with pytest.raises(AgentRuntimeError) as malformed:
            await runtime.supervisor.run(
                context(),
                PROJECT_ID,
                invocation(
                    "fixture-agent-context-malformed",
                    context_package_reference="memory-context://bad",
                ),
            )
        assert malformed.value.code is AgentErrorCode.CONTEXT_PACKAGE_INVALID

        with pytest.raises(AgentRuntimeError) as unavailable:
            await runtime.supervisor.run(
                context(),
                PROJECT_ID,
                invocation(
                    "fixture-agent-context-unavailable",
                    context_package_reference=f"memory-context://{uuid4()}",
                ),
            )
        assert unavailable.value.code is AgentErrorCode.CONTEXT_PACKAGE_INVALID

        without_reader = build_runtime()
        with pytest.raises(AgentRuntimeError):
            await without_reader.supervisor.run(
                context(),
                PROJECT_ID,
                invocation(
                    "fixture-agent-context-no-reader",
                    context_package_reference=f"memory-context://{package_id}",
                ),
            )
        with pytest.raises(ValueError, match="Memory Context Package"):
            invocation(
                "fixture-agent-context-invalid-scheme",
                context_package_reference="fixture-context://value",
            )

    asyncio.run(scenario())


def test_quality_agent_uses_only_explicit_model_tool_gateways_and_replays() -> None:
    harness = build_runtime()
    request = invocation(
        "fixture-quality",
        agent_id="quality",
        budget=AgentBudget(2, 1, 1, 10.0, 2, 64),
        recursion_depth=1,
        planning_path=(DIRECTOR_AGENT_ID,),
        requested_tool_ids=("fixture.reference",),
    )
    result = asyncio.run(harness.supervisor.run(context(), PROJECT_ID, request))
    replay = asyncio.run(harness.supervisor.run(context(), PROJECT_ID, request))
    assert isinstance(result.result, AgentProposal)
    assert result.result.kind is AgentResultKind.PROPOSAL
    assert replay.run == result.run
    assert result.run.model_calls == result.run.tool_calls == 1
    assert result.run.tokens == 5
    assert len(harness.model_ledger.records) == len(harness.tool_ledger.records) == 1
    snapshot = asyncio.run(
        harness.repository.get_snapshot(WORKSPACE_ID, result.run.context_snapshot_id)
    )
    assert snapshot is not None
    assert snapshot.tool_versions == ("fixture.reference@1.0.0",)


@pytest.mark.parametrize(
    ("key", "updates", "expected", "status"),
    [
        (
            "fixture-budget",
            {"budget": AgentBudget(17, 3, 4, 30.0, 8, 2_048)},
            AgentErrorCode.BUDGET_EXHAUSTED,
            AgentRunStatus.BUDGET_EXHAUSTED,
        ),
        (
            "fixture-step",
            {"planned_steps": 17},
            AgentErrorCode.STEP_LIMIT_EXCEEDED,
            AgentRunStatus.LIMIT_EXCEEDED,
        ),
        (
            "fixture-depth",
            {"recursion_depth": 4},
            AgentErrorCode.RECURSION_LIMIT_EXCEEDED,
            AgentRunStatus.LIMIT_EXCEEDED,
        ),
        (
            "fixture-parallel",
            {"requested_parallelism": 5},
            AgentErrorCode.PARALLELISM_LIMIT_EXCEEDED,
            AgentRunStatus.LIMIT_EXCEEDED,
        ),
        (
            "fixture-loop",
            {"planning_path": (DIRECTOR_AGENT_ID,)},
            AgentErrorCode.LOOP_DETECTED,
            AgentRunStatus.LIMIT_EXCEEDED,
        ),
        (
            "fixture-tool",
            {"requested_tool_ids": ("unknown",)},
            AgentErrorCode.TOOL_DENIED,
            AgentRunStatus.REJECTED,
        ),
        (
            "fixture-input-schema",
            {"input_data": {"unexpected": "fixture"}},
            AgentErrorCode.SCHEMA_MISMATCH,
            AgentRunStatus.FAILED,
        ),
    ],
)
def test_supervisor_rejects_limits_loops_tools_and_input_schema(
    key: str,
    updates: dict[str, object],
    expected: AgentErrorCode,
    status: AgentRunStatus,
) -> None:
    harness = build_runtime()
    request = invocation(key, **updates)  # type: ignore[arg-type]
    with pytest.raises(AgentRuntimeError) as captured:
        asyncio.run(harness.supervisor.run(context(), PROJECT_ID, request))
    assert captured.value.code is expected
    stored = asyncio.run(harness.repository.get_by_idempotency(WORKSPACE_ID, key))
    assert stored is not None
    assert stored.status is status
    assert stored.error_code is expected


def test_unknown_agent_missing_permissions_tools_and_projects_fail_closed() -> None:
    harness = build_runtime()
    with pytest.raises(AgentRuntimeError) as unknown:
        asyncio.run(
            harness.supervisor.run(
                context(), PROJECT_ID, invocation("fixture-unknown", agent_id="missing")
            )
        )
    assert unknown.value.code is AgentErrorCode.UNKNOWN_AGENT

    no_tool_permission = context(
        permissions=frozenset({Permission.AGENT_RUN.value, Permission.MODEL_RUN.value})
    )
    request = invocation(
        "fixture-tool-permission",
        agent_id="quality",
        requested_tool_ids=("fixture.reference",),
    )
    with pytest.raises(AgentRuntimeError) as tool_error:
        asyncio.run(harness.supervisor.run(no_tool_permission, PROJECT_ID, request))
    assert tool_error.value.code is AgentErrorCode.TOOL_DENIED

    no_model_permission = context(permissions=frozenset({Permission.AGENT_RUN.value}))
    with pytest.raises(AgentRuntimeError) as model_error:
        asyncio.run(
            build_runtime().supervisor.run(
                no_model_permission, PROJECT_ID, invocation("fixture-model-permission")
            )
        )
    assert model_error.value.code is AgentErrorCode.BUDGET_EXHAUSTED

    missing_project = build_runtime()
    missing_project.project_repository.item = None
    with pytest.raises(ScopeViolationError):
        asyncio.run(
            missing_project.supervisor.run(
                context(), PROJECT_ID, invocation("fixture-project-missing")
            )
        )
    archived = build_runtime(selected_project=project(status=ProjectStatus.ARCHIVED))
    with pytest.raises(InvalidStateError, match="Archived"):
        asyncio.run(archived.supervisor.run(context(), PROJECT_ID, invocation("fixture-archived")))
    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            build_runtime().supervisor.run(
                context(permissions=frozenset({Permission.MODEL_RUN.value})),
                PROJECT_ID,
                invocation("fixture-agent-permission"),
            )
        )


def test_schema_mismatch_duration_and_executor_failure_are_terminal() -> None:
    invalid = build_runtime(
        {
            "fixture-invalid-output": FakeAgentBehavior(
                {"kind": "workflow_selection", "workflow_name": "framework_smoke"}
            )
        }
    )
    with pytest.raises(AgentRuntimeError) as schema:
        asyncio.run(
            invalid.supervisor.run(context(), PROJECT_ID, invocation("fixture-invalid-output"))
        )
    assert schema.value.code is AgentErrorCode.SCHEMA_MISMATCH

    delayed = build_runtime({"fixture-duration": FakeAgentBehavior(delay_seconds=0.02)})
    short = AgentBudget(1, 0, 1, 0.001, 1, 16)
    with pytest.raises(AgentRuntimeError) as duration:
        asyncio.run(
            delayed.supervisor.run(
                context(), PROJECT_ID, invocation("fixture-duration", budget=short)
            )
        )
    assert duration.value.code is AgentErrorCode.DURATION_LIMIT_EXCEEDED

    broken = build_runtime()
    broken.executor.execute = AsyncMock(side_effect=RuntimeError("fixture-private"))  # type: ignore[method-assign]
    with pytest.raises(AgentRuntimeError) as failure:
        asyncio.run(broken.supervisor.run(context(), PROJECT_ID, invocation("fixture-failure")))
    assert failure.value.code is AgentErrorCode.EXECUTION_FAILED

    over_usage = build_runtime()
    over_usage.executor.execute = AsyncMock(  # type: ignore[method-assign]
        return_value=RawAgentResult(
            {
                "kind": "workflow_selection",
                "workflow_name": "framework_smoke",
                "workflow_version": 1,
                "input_reference": "fixture://result",
            },
            "fixture://result",
            2,
            0,
            5,
        )
    )
    with pytest.raises(AgentRuntimeError) as usage:
        asyncio.run(
            over_usage.supervisor.run(
                context(),
                PROJECT_ID,
                invocation(
                    "fixture-over-usage",
                    budget=AgentBudget(1, 0, 1, 1, 1, 16),
                ),
            )
        )
    assert usage.value.code is AgentErrorCode.BUDGET_EXHAUSTED

    missing_tool_version = build_runtime(tool_versions={})
    with pytest.raises(AgentRuntimeError) as version:
        asyncio.run(
            missing_tool_version.supervisor.run(
                context(),
                PROJECT_ID,
                invocation("fixture-tool-version", agent_id="quality"),
            )
        )
    assert version.value.code is AgentErrorCode.TOOL_DENIED


def test_master_selects_smoke_and_routes_protected_proposal_to_approval() -> None:
    harness = build_runtime()
    workflows = AsyncMock()
    selected_workflow = AsyncMock(status=WorkflowRunStatus.PENDING)
    selected_workflow.id = uuid4()
    workflows.submit_framework_smoke.return_value = selected_workflow
    master = MasterOrchestrator(harness.supervisor, workflows, harness.repository)
    selected = asyncio.run(
        master.submit_goal(
            context(),
            PROJECT_ID,
            idempotency_key="fixture-master",
            goal_reference="fixture-goal://technical",
            budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
        )
    )
    assert selected.workflow_run is selected_workflow
    assert selected.agent_run.workflow_run_id == selected_workflow.id
    workflows.submit_framework_smoke.assert_awaited_once()

    plan_output = {
        "kind": AgentResultKind.WORKFLOW_PLAN_PROPOSAL.value,
        "workflow_name": "fixture-protected",
        "workflow_version": 1,
        "input_reference": "proposal://fixture-plan",
        "protected_operations": [ProtectedOperation.CANON.value, ProtectedOperation.PUBLISH.value],
        "approval_required": True,
    }
    planned_harness = build_runtime({"fixture-plan": FakeAgentBehavior(plan_output)})
    planned_workflows = AsyncMock()
    approval_workflow = AsyncMock(status=WorkflowRunStatus.WAITING_APPROVAL)
    approval_workflow.id = uuid4()
    planned_workflows.submit.return_value = approval_workflow
    planned_master = MasterOrchestrator(
        planned_harness.supervisor,
        planned_workflows,
        planned_harness.repository,
    )
    planned = asyncio.run(
        planned_master.submit_goal(
            context(),
            PROJECT_ID,
            idempotency_key="fixture-plan",
            goal_reference="fixture-goal://protected",
            budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
        )
    )
    assert planned.agent_run.status is AgentRunStatus.WAITING_APPROVAL
    definition = planned_workflows.submit.await_args.args[2]
    assert definition.steps[0].kind is StepKind.APPROVAL
    planned_replay = asyncio.run(
        planned_master.submit_goal(
            context(),
            PROJECT_ID,
            idempotency_key="fixture-plan",
            goal_reference="fixture-goal://protected",
            budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
        )
    )
    assert planned_replay.agent_run == planned.agent_run

    wrong_harness = build_runtime(
        {
            "fixture-wrong-workflow": FakeAgentBehavior(
                {
                    "kind": "workflow_selection",
                    "workflow_name": "fixture-unknown",
                    "workflow_version": 1,
                    "input_reference": "fixture://selection",
                }
            )
        }
    )
    with pytest.raises(AgentRuntimeError) as wrong:
        asyncio.run(
            MasterOrchestrator(
                wrong_harness.supervisor, AsyncMock(), wrong_harness.repository
            ).submit_goal(
                context(),
                PROJECT_ID,
                idempotency_key="fixture-wrong-workflow",
                goal_reference="fixture-goal://wrong",
                budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
            )
        )
    assert wrong.value.code is AgentErrorCode.SCHEMA_MISMATCH

    proposal_harness = build_runtime()
    proposal_result = asyncio.run(
        proposal_harness.supervisor.run(
            context(),
            PROJECT_ID,
            invocation("fixture-master-proposal", agent_id="world"),
        )
    )
    proposal_supervisor = AsyncMock()
    proposal_supervisor.run.return_value = proposal_result
    with pytest.raises(AgentRuntimeError) as proposal_error:
        asyncio.run(
            MasterOrchestrator(
                proposal_supervisor, AsyncMock(), proposal_harness.repository
            ).submit_goal(
                context(),
                PROJECT_ID,
                idempotency_key="fixture-master-proposal",
                goal_reference="fixture-goal://proposal",
                budget=DEFAULT_AGENT_BUDGET,
            )
        )
    assert proposal_error.value.code is AgentErrorCode.SCHEMA_MISMATCH


def test_master_projects_human_approval_and_rejection_back_to_agent_state() -> None:
    plan_output = {
        "kind": AgentResultKind.WORKFLOW_PLAN_PROPOSAL.value,
        "workflow_name": "fixture-protected",
        "workflow_version": 1,
        "input_reference": "proposal://fixture-plan",
        "protected_operations": [ProtectedOperation.DELETE.value],
        "approval_required": True,
    }
    harness = build_runtime(
        {
            "fixture-reject-plan": FakeAgentBehavior(plan_output),
            "fixture-approve-plan": FakeAgentBehavior(plan_output),
        }
    )
    workflows = AsyncMock()
    workflow = AsyncMock(status=WorkflowRunStatus.WAITING_APPROVAL)
    workflow.id = uuid4()
    workflows.submit.return_value = workflow
    workflows.decide_approval.return_value = workflow
    master = MasterOrchestrator(harness.supervisor, workflows, harness.repository)

    rejected_plan = asyncio.run(
        master.submit_goal(
            context(),
            PROJECT_ID,
            idempotency_key="fixture-reject-plan",
            goal_reference="fixture-goal://reject",
            budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
        )
    )
    rejected = asyncio.run(
        master.decide_plan(
            context(),
            rejected_plan.agent_run.id,
            WorkflowApprovalDecision.REJECT,
            reason="fixture-reject",
        )
    )
    assert rejected.agent_run.status is AgentRunStatus.REJECTED

    workflow.id = uuid4()
    approved_plan = asyncio.run(
        master.submit_goal(
            context(),
            PROJECT_ID,
            idempotency_key="fixture-approve-plan",
            goal_reference="fixture-goal://approve",
            budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
        )
    )
    approved = asyncio.run(
        master.decide_plan(
            context(),
            approved_plan.agent_run.id,
            WorkflowApprovalDecision.APPROVE,
            reason="fixture-approve",
        )
    )
    assert approved.agent_run.status is AgentRunStatus.SUCCEEDED
    assert (
        asyncio.run(
            harness.repository.settle_approval(WORKSPACE_ID, approved.agent_run.id, approved=True)
        )
        == approved.agent_run
    )
    with pytest.raises(ScopeViolationError):
        asyncio.run(
            master.decide_plan(
                context(), uuid4(), WorkflowApprovalDecision.REJECT, reason="fixture"
            )
        )
    unattached = asyncio.run(
        harness.supervisor.run(context(), PROJECT_ID, invocation("fixture-unattached-plan"))
    )
    with pytest.raises(InvalidStateError, match="no approval"):
        asyncio.run(
            master.decide_plan(
                context(),
                unattached.run.id,
                WorkflowApprovalDecision.REJECT,
                reason="fixture",
            )
        )
    with pytest.raises(InvalidStateError, match="not waiting"):
        asyncio.run(
            harness.repository.settle_approval(WORKSPACE_ID, unattached.run.id, approved=False)
        )
    with pytest.raises(ScopeViolationError):
        asyncio.run(
            harness.repository.settle_approval(uuid4(), approved.agent_run.id, approved=True)
        )


def test_agent_workflow_executor_delegation_retry_and_failures() -> None:
    harness = build_runtime()
    base = FrameworkSmokeExecutor()
    executor = AgentWorkflowExecutor(base, harness.supervisor, AgentBudget(2, 1, 1, 10, 2, 64))
    execution = StepExecution(
        uuid4(),
        uuid4(),
        "pass-token",
        StepKind.REFERENCE,
        1,
        "fixture-workflow-agent",
        "fixture-token://workflow-input",
        0,
        0,
        context(),
    )
    first = asyncio.run(executor.execute(execution))
    second = asyncio.run(executor.execute(execution))
    assert first == second
    assert len(harness.model_ledger.records) == len(harness.tool_ledger.records) == 1

    delegated = replace(execution, step_key="controlled-delay", kind=StepKind.DELAY)
    assert asyncio.run(executor.execute(delegated)).output_reference.startswith(
        "workflow-output://"
    )
    asyncio.run(executor.compensate(delegated, "fixture-hook.v1"))
    assert base.compensations == ((delegated.idempotency_key, "fixture-hook.v1"),)
    with pytest.raises(PermanentStepError, match="security-context-missing"):
        asyncio.run(executor.execute(replace(execution, context=None)))

    failing = build_runtime()
    failing.executor.execute = AsyncMock(  # type: ignore[method-assign]
        side_effect=AgentRuntimeError(AgentErrorCode.EXECUTION_FAILED)
    )
    failing_executor = AgentWorkflowExecutor(
        FrameworkSmokeExecutor(), failing.supervisor, AgentBudget(2, 1, 1, 10, 2, 64)
    )
    with pytest.raises(PermanentStepError, match="execution_failed"):
        asyncio.run(failing_executor.execute(replace(execution, idempotency_key="fixture-bad")))

    selection_supervisor = AsyncMock()
    selection_supervisor.run.return_value = SupervisedAgentResult(
        asyncio.run(harness.supervisor.run(context(), PROJECT_ID, invocation())).run,
        WorkflowSelection("framework_smoke", 1, "fixture://selection"),
    )
    invalid_result_executor = AgentWorkflowExecutor(
        FrameworkSmokeExecutor(), selection_supervisor, AgentBudget(2, 1, 1, 10, 2, 64)
    )
    with pytest.raises(PermanentStepError, match="schema-mismatch"):
        asyncio.run(
            invalid_result_executor.execute(
                replace(execution, idempotency_key="fixture-selection-result")
            )
        )


def test_domain_guards_and_in_memory_repository_conflicts() -> None:  # noqa: PLR0915
    budget = AgentBudget(2, 1, 1, 2.0, 2, 20)
    assert budget.is_within(DEFAULT_AGENT_BUDGET)
    assert DEFAULT_AGENT_BUDGET.narrowed_with(budget) == budget
    for values in (
        (0, 1, 1, 1, 1, 1),
        (1, -1, 1, 1, 1, 1),
        (1, 1, 0, 1, 1, 1),
        (1, 1, 1, 0, 1, 1),
        (1, 1, 1, 1, 0, 1),
        (1, 1, 1, 1, 1, 0),
    ):
        with pytest.raises(ValueError, match="limits"):
            AgentBudget(*values)
    with pytest.raises(ValueError, match="prompt metadata id"):
        PromptMetadataReference("", "1.0.0", "0" * 64)
    with pytest.raises(ValueError, match="checksum"):
        PromptMetadataReference("fixture", "1.0.0", "bad")
    with pytest.raises(ValueError, match="workflow selection"):
        WorkflowSelection("", 1, "fixture://result")
    with pytest.raises(ValueError, match="version/reference"):
        WorkflowSelection("fixture", 0, "not-reference")
    with pytest.raises(ValueError, match="protected operations"):
        WorkflowPlanProposal("fixture", 1, "fixture://result", (), True)
    with pytest.raises(ValueError, match="human approval"):
        WorkflowPlanProposal("fixture", 1, "fixture://result", (ProtectedOperation.DELETE,), False)
    with pytest.raises(ValueError, match="proposal or draft"):
        AgentProposal("fixture://result", AgentResultKind.WORKFLOW_SELECTION)
    with pytest.raises(ValueError, match="bounded opaque"):
        AgentProposal("not-reference")
    with pytest.raises(ValueError, match="raw Agent result"):
        RawAgentResult({}, "bad", 0, 0, 0)
    with pytest.raises(ValueError, match="usage"):
        RawAgentResult({}, "fixture://result", -1, 0, 0)
    assert RawAgentResult({}, "fixture://result", 1, 2, 3).total_calls == 3
    with pytest.raises(ValueError, match="delay"):
        FakeAgentBehavior(delay_seconds=-1)

    descriptor = built_in_agent_descriptors()[0]
    descriptor_cases: tuple[tuple[dict[str, object], str], ...] = (
        ({"agent_id": ""}, "agent id"),
        ({"capabilities": ()}, "capabilities"),
        ({"input_schema": {"type": "string"}}, "schemas"),
        ({"model_policy_id": ""}, "model policy"),
        ({"allowed_tool_ids": ("fixture", "fixture")}, "allowed tool"),
    )
    for updates, message in descriptor_cases:
        with pytest.raises(ValueError, match=message):
            replace(descriptor, **updates)  # type: ignore[arg-type]
    invocation_cases: tuple[tuple[dict[str, object], str], ...] = (
        ({"agent_id": ""}, "agent id"),
        ({"task_reference": "invalid"}, "task"),
        ({"planned_steps": 0}, "bounds"),
        ({"requested_tool_ids": ("fixture", "fixture")}, "unique"),
    )
    for updates, message in invocation_cases:
        with pytest.raises(ValueError, match=message):
            replace(invocation(), **updates)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="workflow proposal name"):
        WorkflowPlanProposal("", 1, "fixture://result", (ProtectedOperation.DELETE,), True)
    with pytest.raises(ValueError, match="version/reference"):
        WorkflowPlanProposal("fixture", 0, "invalid", (ProtectedOperation.DELETE,), True)

    schema_cases: tuple[tuple[dict[str, object], dict[str, object]], ...] = (
        ({"type": "string"}, {}),
        (
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            {"unexpected": "fixture"},
        ),
        (
            {"type": "object", "properties": {"field": "bad"}, "required": []},
            {"field": "fixture"},
        ),
        (
            {
                "type": "object",
                "properties": {"field": {"type": "integer"}},
                "required": [],
            },
            {"field": True},
        ),
    )
    for schema, value in schema_cases:
        with pytest.raises(AgentRuntimeError) as schema_error:
            _validate_schema(value, schema)
        assert schema_error.value.code is AgentErrorCode.SCHEMA_MISMATCH
    result_cases: tuple[tuple[str, dict[str, object]], ...] = (
        (
            "director",
            {
                "kind": "proposal",
                "workflow_name": "fixture",
                "workflow_version": 1,
                "input_reference": "fixture://result",
            },
        ),
        (
            "world",
            {"kind": "workflow_selection", "result_reference": "fixture://result"},
        ),
        ("world", {"kind": "unknown", "result_reference": "fixture://result"}),
    )
    for agent_id, output in result_cases:
        with pytest.raises(AgentRuntimeError) as result_error:
            _typed_result(agent_id, output)
        assert result_error.value.code is AgentErrorCode.SCHEMA_MISMATCH

    harness = build_runtime()
    result = asyncio.run(harness.supervisor.run(context(), PROJECT_ID, invocation()))
    with pytest.raises(IdempotencyConflictError):
        asyncio.run(
            harness.supervisor.run(
                context(),
                PROJECT_ID,
                invocation(input_data={"input_reference": "fixture-token://different"}),
            )
        )
    with pytest.raises(ScopeViolationError):
        asyncio.run(
            harness.repository.attach_workflow(uuid4(), result.run.id, uuid4(), waiting=False)
        )
    workflow_id = uuid4()
    asyncio.run(
        harness.repository.attach_workflow(WORKSPACE_ID, result.run.id, workflow_id, waiting=False)
    )
    assert (
        asyncio.run(
            harness.repository.attach_workflow(
                WORKSPACE_ID, result.run.id, workflow_id, waiting=False
            )
        ).workflow_run_id
        == workflow_id
    )
    with pytest.raises(InvalidStateError, match="another"):
        asyncio.run(
            harness.repository.attach_workflow(WORKSPACE_ID, result.run.id, uuid4(), waiting=False)
        )
    assert asyncio.run(harness.repository.get_by_idempotency(uuid4(), "fixture-agent")) is None
    with pytest.raises(InvalidStateError, match="unavailable"):
        asyncio.run(
            harness.repository.complete(
                uuid4(),
                AgentProposal("fixture://result"),
                RawAgentResult({}, "fixture://result", 0, 0, 0),
            )
        )
    assert (
        asyncio.run(
            harness.repository.complete(
                result.run.id,
                AgentProposal("fixture://result"),
                RawAgentResult({}, "fixture://result", 0, 0, 0),
            )
        ).status
        is AgentRunStatus.SUCCEEDED
    )
    assert (
        asyncio.run(
            harness.repository.fail(
                result.run.id,
                AgentRunStatus.FAILED,
                AgentRuntimeError(AgentErrorCode.EXECUTION_FAILED),
            )
        ).status
        is AgentRunStatus.SUCCEEDED
    )
    with pytest.raises(AgentRuntimeError) as stored_terminal:
        _stored_result(
            replace(
                result.run,
                status=AgentRunStatus.FAILED,
                error_code=AgentErrorCode.EXECUTION_FAILED,
            )
        )
    assert stored_terminal.value.code is AgentErrorCode.EXECUTION_FAILED
    with pytest.raises(AgentRuntimeError) as stored_empty:
        _stored_result(replace(result.run, result_kind=None))
    assert stored_empty.value.code is AgentErrorCode.EXECUTION_FAILED


def test_fake_executor_rejects_non_string_input_after_trusted_boundary() -> None:
    harness = build_runtime()
    supervised = asyncio.run(
        harness.supervisor.run(context(), PROJECT_ID, invocation("fixture-execution-source"))
    )
    snapshot = asyncio.run(
        harness.repository.get_snapshot(WORKSPACE_ID, supervised.run.context_snapshot_id)
    )
    assert snapshot is not None
    descriptor = harness.registry.get("director")
    assert descriptor is not None
    execution = agent_public.AgentExecution(
        uuid4(),
        descriptor,
        snapshot,
        context(),
        invocation("fixture-direct-invalid", input_data={"input_reference": 3}),
        AgentBudget(1, 0, 1, 1, 1, 16),
    )
    with pytest.raises(ValueError, match="unavailable"):
        asyncio.run(harness.executor.execute(execution))
