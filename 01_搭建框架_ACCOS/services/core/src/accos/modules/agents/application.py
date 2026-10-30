"""Authorized Agent supervision and Director-to-Workflow orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.modules.agents.definitions import (
    DIRECTOR_AGENT_ID,
    agent_plan_review_definition,
)
from accos.modules.agents.domain import (
    AgentContextSnapshot,
    AgentErrorCode,
    AgentExecution,
    AgentInvocation,
    AgentPlan,
    AgentProposal,
    AgentResultKind,
    AgentRun,
    AgentRunStatus,
    AgentRuntimeError,
    ProtectedOperation,
    SupervisedAgentResult,
    WorkflowPlanProposal,
    WorkflowSelection,
)
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus
from accos.modules.workflows.public import (
    FRAMEWORK_SMOKE_NAME,
    PermanentStepError,
    StepExecution,
    StepExecutionResult,
    StepDefinition,
    StepKind,
    WorkflowApprovalDecision,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.agents.domain import (
        AgentBudget,
        AgentDescriptor,
        AgentResult,
    )
    from accos.modules.agents.ports import (
        AgentExecutor,
        AgentMetrics,
        AgentRegistry,
        AgentRepository,
        AgentSupervisor,
    )
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.memory.public import ContextPackageReader
    from accos.modules.projects.public import ProjectRepository
    from accos.modules.workflows.public import StepExecutor, WorkflowRun, WorkflowService


class InMemoryAgentRegistry:
    """Process-local immutable descriptor catalog."""

    def __init__(self) -> None:
        self._descriptors: dict[str, AgentDescriptor] = {}

    def register(self, descriptor: AgentDescriptor) -> None:
        """Register one stable Agent id exactly once."""
        if descriptor.agent_id in self._descriptors:
            raise ValueError("agent id is already registered")
        self._descriptors[descriptor.agent_id] = descriptor

    def get(self, agent_id: str) -> AgentDescriptor | None:
        """Resolve an exact Agent id without granting execution authority."""
        return self._descriptors.get(agent_id)

    def all(self) -> tuple[AgentDescriptor, ...]:
        """Return descriptors in registration order."""
        return tuple(self._descriptors.values())


class InMemoryAgentMetrics:
    """Deterministic metric sink pending the shared telemetry adapter stage."""

    def __init__(self) -> None:
        self.transitions: list[tuple[str, AgentRunStatus]] = []

    def record(self, agent_id: str, status: AgentRunStatus) -> None:
        """Count only stable Agent id and state labels."""
        self.transitions.append((agent_id, status))


class DefaultAgentSupervisor:
    """Validate, authorize, bound, execute, and durably settle one stateless Agent."""

    def __init__(  # noqa: PLR0913,PLR0917 - explicit security boundaries.
        self,
        registry: AgentRegistry,
        executor: AgentExecutor,
        repository: AgentRepository,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
        metrics: AgentMetrics,
        clock: Clock,
        hard_budget: AgentBudget,
        tool_versions: Mapping[str, str],
        context_packages: ContextPackageReader | None = None,
    ) -> None:
        self._registry = registry
        self._executor = executor
        self._repository = repository
        self._projects = projects
        self._authorizer = authorizer
        self._metrics = metrics
        self._clock = clock
        self._hard_budget = hard_budget
        self._tool_versions = dict(tool_versions)
        self._context_packages = context_packages

    async def run(
        self, context: SecurityContext, project_id: UUID, invocation: AgentInvocation
    ) -> SupervisedAgentResult:
        """Run once per scoped idempotency key and return the persisted result on redelivery."""
        descriptor = self._registry.get(invocation.agent_id)
        if descriptor is None:
            raise AgentRuntimeError(AgentErrorCode.UNKNOWN_AGENT)
        await self._authorize(context, project_id)
        package_id = await self._context_package_id(
            context, project_id, invocation.context_package_reference
        )
        snapshot = self._snapshot(
            context, project_id, descriptor, invocation.input_data, package_id, invocation
        )
        now = self._clock.now()
        pending = AgentRun(
            uuid4(),
            context.workspace_id,
            project_id,
            descriptor.agent_id,
            descriptor.version,
            snapshot.id,
            AgentRunStatus.RUNNING,
            1,
            invocation.idempotency_key,
            invocation.task_reference,
            context.actor_id,
            UUID(context.correlation.request_id),
            now,
            now,
            workflow_run_id=invocation.workflow_run_id,
        )
        stored, created = await self._repository.begin(
            pending,
            snapshot,
            request_digest=_request_digest(descriptor, invocation, snapshot.input_digest),
        )
        if not created:
            return SupervisedAgentResult(stored, _stored_result(stored))
        self._metrics.record(descriptor.agent_id, AgentRunStatus.RUNNING)
        try:
            budget = self._preflight(context, descriptor, invocation)
            execution = AgentExecution(stored.id, descriptor, snapshot, context, invocation, budget)
            async with asyncio.timeout(budget.max_duration_seconds):
                raw = await self._executor.execute(execution)
            _validate_schema(raw.output_data, descriptor.output_schema)
            result = _typed_result(descriptor.agent_id, raw.output_data)
            if raw.total_calls > budget.max_calls or raw.tokens > budget.max_tokens:
                raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
        except TimeoutError:
            await self._settle_failure(
                stored, AgentRuntimeError(AgentErrorCode.DURATION_LIMIT_EXCEEDED)
            )
            raise AgentRuntimeError(AgentErrorCode.DURATION_LIMIT_EXCEEDED) from None
        except asyncio.CancelledError:
            await asyncio.shield(self._settle_failure(stored, AgentRuntimeError(AgentErrorCode.MODEL_RESULT_UNKNOWN)))
            raise
        except AgentRuntimeError as error:
            await self._settle_failure(stored, error)
            raise
        except Exception:  # noqa: BLE001 - executor details never cross this boundary.
            internal_error = AgentRuntimeError(AgentErrorCode.EXECUTION_FAILED)
            await self._settle_failure(stored, internal_error)
            raise internal_error from None
        completed = await self._repository.complete(stored.id, result, raw)
        self._metrics.record(descriptor.agent_id, AgentRunStatus.SUCCEEDED)
        return SupervisedAgentResult(completed, result)

    async def get(self, context: SecurityContext, run_id: UUID) -> AgentRun:
        """Return one persisted Agent run through its project read boundary."""
        run = await self._repository.get(context.workspace_id, run_id)
        if run is None:
            raise ScopeViolationError
        project = await self._projects.get(context.workspace_id, run.project_id)
        request = AuthorizationRequest(
            context,
            Permission.PROJECT_READ,
            ResourceScope(context.workspace_id, "agent_run", str(run_id), run.project_id),
        )
        if project is None:
            await self._authorizer.reject(
                request,
                ScopeViolationError(),
                reason_code="agent_project_unavailable",
            )
        await self._authorizer.authorize(request)
        return run

    async def _authorize(self, context: SecurityContext, project_id: UUID) -> None:
        project = await self._projects.get(context.workspace_id, project_id)
        request = AuthorizationRequest(
            context,
            Permission.AGENT_RUN,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        if project is None:
            await self._authorizer.reject(
                request,
                ScopeViolationError(),
                reason_code="agent_project_unavailable",
            )
        if project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot start Agent runs.")
        await self._authorizer.authorize(request)

    def _snapshot(
        self,
        context: SecurityContext,
        project_id: UUID,
        descriptor: AgentDescriptor,
        input_data: dict[str, object],
        package_id: UUID | None,
        invocation: AgentInvocation,
    ) -> AgentContextSnapshot:
        tools: list[str] = []
        for tool_id in descriptor.allowed_tool_ids:
            version = self._tool_versions.get(tool_id)
            if version is None:
                raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
            tools.append(f"{tool_id}@{version}")
        return AgentContextSnapshot(
            uuid4(),
            context.workspace_id,
            project_id,
            descriptor.agent_id,
            descriptor.version,
            invocation.model_policy.id if invocation.model_policy else descriptor.model_policy_id,
            f"{invocation.model_policy.version}.0.0" if invocation.model_policy else descriptor.model_policy_version,
            invocation.prompt.id if invocation.prompt else descriptor.prompt_metadata.metadata_id,
            invocation.prompt.version if invocation.prompt else descriptor.prompt_metadata.version,
            invocation.prompt.checksum if invocation.prompt else descriptor.prompt_metadata.checksum,
            tuple(tools),
            tuple(sorted(context.permissions)),
            hashlib.sha256(_canonical_json(input_data)).hexdigest(),
            self._clock.now(),
            package_id,
        )

    async def _context_package_id(
        self, context: SecurityContext, project_id: UUID, reference: str | None
    ) -> UUID | None:
        if reference is None:
            return None
        try:
            package_id = UUID(reference.removeprefix("memory-context://"))
        except ValueError:
            raise AgentRuntimeError(AgentErrorCode.CONTEXT_PACKAGE_INVALID) from None
        if (
            self._context_packages is None
            or await self._context_packages.get_package(
                context.workspace_id, project_id, package_id
            )
            is None
        ):
            raise AgentRuntimeError(AgentErrorCode.CONTEXT_PACKAGE_INVALID)
        return package_id

    def _preflight(
        self,
        context: SecurityContext,
        descriptor: AgentDescriptor,
        invocation: AgentInvocation,
    ) -> AgentBudget:
        _validate_schema(invocation.input_data, descriptor.input_schema)
        if not invocation.requested_budget.is_within(descriptor.budget_limit) or not (
            invocation.requested_budget.is_within(self._hard_budget)
        ):
            raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
        budget = descriptor.budget_limit.narrowed_with(self._hard_budget).narrowed_with(
            invocation.requested_budget
        )
        if invocation.planned_steps > budget.max_steps:
            raise AgentRuntimeError(AgentErrorCode.STEP_LIMIT_EXCEEDED)
        if invocation.recursion_depth > budget.max_recursion_depth:
            raise AgentRuntimeError(AgentErrorCode.RECURSION_LIMIT_EXCEEDED)
        if invocation.requested_parallelism > budget.max_parallelism:
            raise AgentRuntimeError(AgentErrorCode.PARALLELISM_LIMIT_EXCEEDED)
        path = (*invocation.planning_path, invocation.agent_id)
        if len(set(path)) != len(path):
            raise AgentRuntimeError(AgentErrorCode.LOOP_DETECTED)
        if not set(invocation.requested_tool_ids).issubset(descriptor.allowed_tool_ids):
            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
        if invocation.requested_tool_ids and Permission.TOOL_RUN.value not in context.permissions:
            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
        expected_calls = 1 + len(invocation.requested_tool_ids)
        if (
            expected_calls > budget.max_calls
            or Permission.MODEL_RUN.value not in context.permissions
        ):
            raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
        return budget

    async def _settle_failure(self, run: AgentRun, error: AgentRuntimeError) -> None:
        status = _failure_status(error.code)
        await self._repository.fail(run.id, status, error)
        self._metrics.record(run.agent_id, status)


@dataclass(frozen=True, slots=True)
class OrchestratedRun:
    """Director decision joined to the Workflow that exclusively schedules it."""

    agent_run: AgentRun
    workflow_run: WorkflowRun


class MasterOrchestrator:
    """Interpret a technical goal once, then delegate all durable scheduling to Workflow."""

    def __init__(
        self,
        supervisor: AgentSupervisor,
        workflows: WorkflowService,
        repository: AgentRepository,
        registry: AgentRegistry | None = None,
    ) -> None:
        self._supervisor = supervisor
        self._workflows = workflows
        self._repository = repository
        self._registry = registry

    async def submit_plan(
        self,
        context: SecurityContext,
        project_id: UUID,
        definition: WorkflowDefinition,
        *,
        idempotency_key: str,
        input_reference: str,
        candidate_references: dict[str, str] | None = None,
    ) -> WorkflowRun:
        """Validate a typed Director DAG and delegate its execution to Workflow."""
        if definition.graph_version != 2 or self._registry is None:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        by_key = {step.key: step for step in definition.steps}
        for step in definition.steps:
            if step.executor_key.startswith("agent."):
                agent_id = (
                    step.executor_key.removeprefix("agent.").split("@", maxsplit=1)[0].split(".")[0]
                )
                if self._registry.get(agent_id) is None:
                    raise AgentRuntimeError(AgentErrorCode.UNKNOWN_AGENT)
            elif not step.executor_key.startswith(("workflow.", "framework.")):
                raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
            if step.external_side_effect and not _has_approval_ancestor(
                step.key, by_key, definition
            ):
                raise AgentRuntimeError(AgentErrorCode.APPROVAL_REQUIRED)
        workflow = await self._workflows.submit(
            context,
            project_id,
            definition,
            idempotency_key=idempotency_key,
            input_reference=input_reference,
            candidate_references=candidate_references,
        )
        return workflow

    async def submit_goal(
        self,
        context: SecurityContext,
        project_id: UUID,
        *,
        idempotency_key: str,
        goal_reference: str,
        budget: AgentBudget,
    ) -> OrchestratedRun:
        """Run Director and submit only its typed, allowlisted Workflow decision."""
        supervised = await self._supervisor.run(
            context,
            project_id,
            AgentInvocation(
                DIRECTOR_AGENT_ID,
                {"input_reference": goal_reference},
                idempotency_key,
                f"agent-task://director/{idempotency_key}",
                budget,
            ),
        )
        result = supervised.result
        waiting = isinstance(result, WorkflowPlanProposal)
        if isinstance(result, WorkflowSelection):
            if result.workflow_name != FRAMEWORK_SMOKE_NAME or result.workflow_version != 1:
                raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
            definition = None
        elif isinstance(result, WorkflowPlanProposal):
            definition = agent_plan_review_definition()
        else:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        workflow = (
            await self._workflows.submit_framework_smoke(
                context,
                project_id,
                idempotency_key=idempotency_key,
                input_reference=result.input_reference,
            )
            if definition is None
            else await self._workflows.submit(
                context,
                project_id,
                definition,
                idempotency_key=idempotency_key,
                input_reference=result.input_reference,
            )
        )
        agent_run = await self._repository.attach_workflow(
            context.workspace_id,
            supervised.run.id,
            workflow.id,
            waiting=waiting,
        )
        return OrchestratedRun(agent_run, workflow)

    async def decide_plan(
        self,
        context: SecurityContext,
        agent_run_id: UUID,
        decision: WorkflowApprovalDecision,
        *,
        reason: str,
    ) -> OrchestratedRun:
        """Delegate the human decision to Workflow, then project its terminal result."""
        agent_run = await self._repository.get(context.workspace_id, agent_run_id)
        if agent_run is None:
            raise ScopeViolationError
        if agent_run.workflow_run_id is None:
            raise InvalidStateError("Agent plan has no approval Workflow.")
        workflow = await self._workflows.decide_approval(
            context,
            agent_run.workflow_run_id,
            decision,
            reason=reason,
        )
        settled = await self._repository.settle_approval(
            context.workspace_id,
            agent_run.id,
            approved=decision is WorkflowApprovalDecision.APPROVE,
        )
        return OrchestratedRun(settled, workflow)


class AgentWorkflowExecutor:
    """Invoke a bounded Agent at a Workflow task boundary and delegate other steps."""

    def __init__(
        self,
        base: StepExecutor,
        supervisor: AgentSupervisor,
        budget: AgentBudget,
    ) -> None:
        self._base = base
        self._supervisor = supervisor
        self._budget = budget

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        """Run the content-free Quality Agent only for the smoke entry step."""
        if execution.step_key != "pass-token":
            return await self._base.execute(execution)
        if execution.context is None or execution.context.project_id is None:
            raise PermanentStepError("agent-error://security-context-missing")
        try:
            supervised = await self._supervisor.run(
                execution.context,
                execution.context.project_id,
                AgentInvocation(
                    "quality",
                    {"input_reference": execution.input_reference},
                    f"{execution.idempotency_key}-agent",
                    f"agent-task://workflow/{execution.task_run_id}",
                    self._budget,
                    recursion_depth=1,
                    planning_path=(DIRECTOR_AGENT_ID,),
                    requested_tool_ids=("fixture.reference",),
                    workflow_run_id=execution.workflow_run_id,
                    task_run_id=execution.task_run_id,
                ),
            )
        except AgentRuntimeError as error:
            raise PermanentStepError(f"agent-error://{error.code.value.lower()}") from None
        if not isinstance(supervised.result, AgentProposal):
            raise PermanentStepError("agent-error://schema-mismatch")
        return StepExecutionResult(supervised.result.result_reference)

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        """Delegate compensation; Agent results are immutable proposals only."""
        await self._base.compensate(execution, hook)


def _has_approval_ancestor(
    step_key: str,
    by_key: dict[str, StepDefinition],
    definition: WorkflowDefinition,
) -> bool:
    pending = list(definition.dependencies_for(by_key[step_key]))
    visited: set[str] = set()
    while pending:
        dependency_key = pending.pop()
        if dependency_key in visited:
            continue
        visited.add(dependency_key)
        dependency = by_key[dependency_key]
        if dependency.kind is StepKind.APPROVAL:
            return True
        pending.extend(definition.dependencies_for(dependency))
    return False


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _request_digest(
    descriptor: AgentDescriptor, invocation: AgentInvocation, input_digest: str
) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "agent_id": descriptor.agent_id,
                "agent_version": descriptor.version,
                "input_digest": input_digest,
                "task_reference": invocation.task_reference,
                "workflow_run_id": (
                    str(invocation.workflow_run_id) if invocation.workflow_run_id else None
                ),
                "task_run_id": str(invocation.task_run_id) if invocation.task_run_id else None,
                "context_package_reference": invocation.context_package_reference,
                "model_policy": invocation.model_policy.model_dump(mode="json") if invocation.model_policy else None,
                "prompt": invocation.prompt.model_dump(mode="json") if invocation.prompt else None,
                "requested_tool_ids": invocation.requested_tool_ids,
                "budget": {
                    "steps": invocation.requested_budget.max_steps,
                    "depth": invocation.requested_budget.max_recursion_depth,
                    "parallel": invocation.requested_budget.max_parallelism,
                    "duration": invocation.requested_budget.max_duration_seconds,
                    "calls": invocation.requested_budget.max_calls,
                    "tokens": invocation.requested_budget.max_tokens,
                },
            }
        )
    ).hexdigest()


def _validate_schema(value: dict[str, object], schema: dict[str, object]) -> None:
    properties = schema.get("properties")
    required = schema.get("required", [])
    if (
        schema.get("type") != "object"
        or not isinstance(properties, dict)
        or not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
    ):
        raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
    if any(item not in value for item in required):
        raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
    if schema.get("additionalProperties") is False and set(value).difference(properties):
        raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
    for key, item in value.items():
        rule = properties.get(key)
        if not isinstance(rule, dict):
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        expected = rule.get("type")
        valid = (
            (expected == "string" and isinstance(item, str))
            or (expected == "integer" and isinstance(item, int) and not isinstance(item, bool))
            or (expected == "boolean" and isinstance(item, bool))
            or (expected == "array" and isinstance(item, list))
        )
        if not valid:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)


def _typed_result(agent_id: str, output: dict[str, object]) -> AgentResult:
    try:
        kind = AgentResultKind(cast("str", output["kind"]))
        if kind is AgentResultKind.PLAN:
            return AgentPlan(cast("str", output["result_reference"]))
        if "result_reference" in output and kind in {AgentResultKind.PROPOSAL, AgentResultKind.DRAFT}:
            return AgentProposal(cast("str", output["result_reference"]), kind)
        if agent_id == DIRECTOR_AGENT_ID:
            workflow_name = cast("str", output["workflow_name"])
            workflow_version = cast("int", output["workflow_version"])
            input_reference = cast("str", output["input_reference"])
            if kind is AgentResultKind.WORKFLOW_SELECTION:
                return WorkflowSelection(workflow_name, workflow_version, input_reference)
            if kind is AgentResultKind.WORKFLOW_PLAN_PROPOSAL:
                raw_operations = cast("list[object]", output.get("protected_operations"))
                operations = tuple(ProtectedOperation(cast("str", item)) for item in raw_operations)
                return WorkflowPlanProposal(
                    workflow_name,
                    workflow_version,
                    input_reference,
                    operations,
                    cast("bool", output.get("approval_required")),
                )
            raise ValueError
        if kind not in {AgentResultKind.PROPOSAL, AgentResultKind.DRAFT}:
            raise ValueError
        return AgentProposal(cast("str", output["result_reference"]), kind)
    except (KeyError, TypeError, ValueError):
        raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH) from None


def _stored_result(run: AgentRun) -> AgentResult:
    if run.status not in {AgentRunStatus.SUCCEEDED, AgentRunStatus.WAITING_APPROVAL}:
        raise AgentRuntimeError(run.error_code or AgentErrorCode.EXECUTION_FAILED)
    if run.result_kind is None or run.result_reference is None:
        raise AgentRuntimeError(AgentErrorCode.EXECUTION_FAILED)
    if run.result_kind is AgentResultKind.PLAN:
        return AgentPlan(run.result_reference)
    if run.result_kind is AgentResultKind.WORKFLOW_SELECTION:
        return WorkflowSelection(
            run.workflow_name or "",
            run.workflow_version or 0,
            run.result_reference,
        )
    if run.result_kind is AgentResultKind.WORKFLOW_PLAN_PROPOSAL:
        return WorkflowPlanProposal(
            run.workflow_name or "",
            run.workflow_version or 0,
            run.result_reference,
            run.protected_operations,
            approval_required=True,
        )
    return AgentProposal(run.result_reference, run.result_kind)


def _failure_status(code: AgentErrorCode) -> AgentRunStatus:
    if code is AgentErrorCode.BUDGET_EXHAUSTED:
        return AgentRunStatus.BUDGET_EXHAUSTED
    if code in {
        AgentErrorCode.STEP_LIMIT_EXCEEDED,
        AgentErrorCode.RECURSION_LIMIT_EXCEEDED,
        AgentErrorCode.PARALLELISM_LIMIT_EXCEEDED,
        AgentErrorCode.DURATION_LIMIT_EXCEEDED,
        AgentErrorCode.LOOP_DETECTED,
    }:
        return AgentRunStatus.LIMIT_EXCEEDED
    if code in {AgentErrorCode.TOOL_DENIED, AgentErrorCode.APPROVAL_REQUIRED}:
        return AgentRunStatus.REJECTED
    return AgentRunStatus.FAILED
