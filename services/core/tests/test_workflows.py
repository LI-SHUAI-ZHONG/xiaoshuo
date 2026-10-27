from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from accos.adapters.workflows import (
    CELERY_WORKFLOW_TASK,
    CeleryEventPublisher,
    InMemoryTaskQueue,
    create_celery_app,
    deserialize_event,
    register_celery_consumer,
    serialize_event,
)
from accos.kernel.errors import (
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.events import EventEnvelope
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.projects.public import Project, ProjectSettings, ProjectStatus
from accos.modules.workflows.public import (
    ApprovalRequest,
    ApprovalStatus,
    ClaimedTask,
    FailureSettlement,
    FrameworkSmokeExecutor,
    PermanentStepError,
    RetryableStepError,
    RetryPolicy,
    StepDefinition,
    StepExecution,
    StepExecutionResult,
    StepKind,
    StepRun,
    StepRunStatus,
    TaskRun,
    TaskRunStatus,
    WorkerDisposition,
    WorkflowApprovalDecision,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowService,
    WorkflowWorker,
    ensure_run_transition,
    framework_smoke_definition,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from accos.modules.identity.public import AuthorizationService

NOW = datetime(2026, 9, 4, tzinfo=UTC)


@dataclass(slots=True)
class MutableClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class RepositoryDouble:
    def __init__(self) -> None:
        self.ensure_definition = AsyncMock()
        self.submit = AsyncMock(side_effect=lambda run, _definition, **_kwargs: (run, True))
        self.get_run = AsyncMock()
        self.get_steps = AsyncMock(return_value=())
        self.get_tasks = AsyncMock(return_value=())
        self.get_events = AsyncMock(return_value=())
        self.pause = AsyncMock()
        self.resume = AsyncMock()
        self.cancel = AsyncMock()
        self.get_approval = AsyncMock()
        self.decide_approval = AsyncMock()
        self.expire_approval = AsyncMock()
        self.claim_task = AsyncMock()
        self.is_cancelling = AsyncMock(return_value=False)
        self.succeed_task = AsyncMock()
        self.fail_task = AsyncMock()
        self.cancel_task = AsyncMock()


class AuthorizerDouble:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def authorize(self, request: object) -> None:
        self.requests.append(request)

    async def reject(self, request: object, error: Exception, **_kwargs: object) -> None:
        self.requests.append(request)
        raise error


def context(*, actor_id: UUID | None = None, workspace_id: UUID | None = None) -> SecurityContext:
    return SecurityContext(
        actor_id or uuid4(),
        ActorKind.USER,
        workspace_id or uuid4(),
        frozenset({"agent:run", "approval:decide"}),
        "identity-rbac-v1",
        CorrelationIds(str(uuid4()), str(uuid4())),
    )


def project(security: SecurityContext, *, status: ProjectStatus = ProjectStatus.ACTIVE) -> Project:
    return Project(
        uuid4(),
        security.workspace_id,
        "fixture-project",
        status,
        ProjectSettings(),
        security.actor_id,
        NOW,
        NOW,
    )


def run(
    security: SecurityContext,
    project_id: UUID,
    *,
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING,
) -> WorkflowRun:
    return WorkflowRun(
        uuid4(),
        security.workspace_id,
        project_id,
        uuid4(),
        "fixture-workflow",
        1,
        status,
        "fixture-key",
        "fixture-token://input",
        security.actor_id,
        security.actor_kind.value,
        UUID(security.correlation.request_id),
        NOW,
        NOW,
    )


def claimed_task(
    *,
    attempt: int = 1,
    kind: StepKind = StepKind.REFERENCE,
    deadline: datetime | None = None,
    compensation_hook: str | None = None,
) -> ClaimedTask:
    security = context()
    project_id = uuid4()
    workflow_run = run(security, project_id, status=WorkflowRunStatus.RUNNING)
    step = StepDefinition(
        uuid4(),
        "fixture-step",
        0,
        kind,
        1.0,
        RetryPolicy(max_attempts=3),
        fail_until_attempt=(1 if kind is StepKind.CONTROLLED_FAILURE else 0),
        compensation_hook=compensation_hook,
    )
    step_run = StepRun(
        uuid4(),
        security.workspace_id,
        project_id,
        workflow_run.id,
        step.id,
        step.key,
        0,
        StepRunStatus.RUNNING,
        attempt,
        "fixture-token://input",
        NOW,
        NOW,
        deadline,
    )
    lease_token = uuid4()
    task = TaskRun(
        uuid4(),
        security.workspace_id,
        project_id,
        workflow_run.id,
        step_run.id,
        TaskRunStatus.RUNNING,
        attempt,
        f"{workflow_run.id}:{step.key}",
        "fixture-token://input",
        NOW,
        NOW,
        NOW,
        deadline,
        lease_token=lease_token,
        lease_expires_at=NOW + timedelta(seconds=30),
    )
    return ClaimedTask(task, workflow_run, step_run, step, lease_token)


def dispatched_event(task_id: UUID, *, available_at: datetime | None = None) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        "workflows.task-dispatched",
        1,
        {"schema": "task-dispatched.v1", "task_id": str(task_id)},
        NOW,
        available_at,
    )


def test_workflow_state_graph_accepts_only_declared_transitions() -> None:
    for source, target in (
        (WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING),
        (WorkflowRunStatus.RUNNING, WorkflowRunStatus.PAUSED),
        (WorkflowRunStatus.PAUSED, WorkflowRunStatus.WAITING_APPROVAL),
        (WorkflowRunStatus.WAITING_APPROVAL, WorkflowRunStatus.PAUSED),
        (WorkflowRunStatus.CANCELLING, WorkflowRunStatus.CANCELLED),
    ):
        ensure_run_transition(source, target)

    for terminal in (
        WorkflowRunStatus.SUCCEEDED,
        WorkflowRunStatus.FAILED,
        WorkflowRunStatus.CANCELLED,
    ):
        with pytest.raises(InvalidStateError, match="cannot transition"):
            ensure_run_transition(terminal, WorkflowRunStatus.RUNNING)
    with pytest.raises(InvalidStateError, match="pending to succeeded"):
        ensure_run_transition(WorkflowRunStatus.PENDING, WorkflowRunStatus.SUCCEEDED)


def test_retry_and_definition_value_validation() -> None:
    policy = RetryPolicy(4, 2.0, 5.0, 2.0)
    assert [policy.delay_after(attempt) for attempt in range(1, 5)] == [2.0, 4.0, 5.0, 5.0]
    with pytest.raises(ValueError, match="attempt must"):
        policy.delay_after(0)
    for values in ((0, 1, 2, 2), (1, 0, 2, 2), (1, 3, 2, 2), (1, 1, 2, 0.5)):
        with pytest.raises(ValueError):
            RetryPolicy(*values)

    valid = StepDefinition(uuid4(), "fixture-step", 0, StepKind.REFERENCE, 1, RetryPolicy())
    with pytest.raises(ValueError, match="step key"):
        replace(valid, key=" fixture")
    with pytest.raises(ValueError, match="position"):
        replace(valid, position=-1)
    with pytest.raises(ValueError, match="controlled failures"):
        replace(valid, fail_until_attempt=3)
    with pytest.raises(ValueError, match="approval steps"):
        replace(valid, kind=StepKind.APPROVAL)
    approval = replace(
        valid,
        id=uuid4(),
        kind=StepKind.APPROVAL,
        approval_expires_seconds=10,
    )
    with pytest.raises(ValueError, match="only approval"):
        replace(valid, approval_expires_seconds=10)
    with pytest.raises(ValueError, match="compensation hook"):
        replace(valid, compensation_hook=" hook")
    definition = WorkflowDefinition(uuid4(), "fixture", 1, (valid,), NOW)
    assert definition.steps == (valid,)
    for changed, match in (
        ({"name": " fixture"}, "workflow name"),
        ({"version": 0}, "positive version"),
        ({"steps": (replace(valid, position=1),)}, "contiguous"),
        ({"steps": (valid, replace(valid, id=uuid4(), position=1))}, "unique"),
    ):
        with pytest.raises(ValueError, match=match):
            replace(definition, **changed)
    assert approval.approval_expires_seconds == 10
    assert framework_smoke_definition().name == "framework_smoke"


def test_event_availability_and_queue_serialization_validation() -> None:
    event = dispatched_event(uuid4(), available_at=NOW + timedelta(seconds=3))
    restored = deserialize_event(serialize_event(event))
    assert restored == event
    without_project = replace(event, project_id=None, available_at=None)
    assert deserialize_event(serialize_event(without_project)) == without_project
    with pytest.raises(ValueError, match="availability"):
        replace(event, available_at=datetime(2026, 9, 4))
    payload = serialize_event(event)
    for key, value, match in (
        ("project_id", 1, "project identifier"),
        ("payload", "bad", "payload"),
        ("id", 1, "id"),
        ("version", True, "version"),
        ("available_at", 1, "available_at"),
    ):
        invalid = {**payload, key: value}
        with pytest.raises(ValueError, match=match):
            deserialize_event(invalid)


def test_memory_and_celery_queue_adapters_preserve_at_least_once_delivery() -> None:
    async def scenario() -> None:
        queue = InMemoryTaskQueue()
        event = dispatched_event(uuid4())
        await queue.publish(event)
        await queue.publish(event)
        handler = AsyncMock(return_value=WorkerDisposition.IGNORED)
        assert await queue.deliver(handler, index=1) is WorkerDisposition.IGNORED
        assert queue.deliveries == (event, event)
        queue.available = False
        with pytest.raises(ConnectionError, match="unavailable"):
            await queue.publish(event)

        client = MagicMock()
        publisher = CeleryEventPublisher(client)
        await publisher.publish(event)
        client.send_task.assert_called_once_with(
            CELERY_WORKFLOW_TASK,
            [serialize_event(event)],
            task_id=str(event.id),
            eta=None,
        )

    asyncio.run(scenario())


def test_celery_application_and_consumer_registration() -> None:
    app = create_celery_app("redis://:fixture-secret@127.0.0.1/0")
    assert app.conf.task_acks_late
    assert app.conf.task_ignore_result
    assert app.conf.worker_prefetch_multiplier == 1
    with pytest.raises(ValueError, match="resilience"):
        create_celery_app("redis://fixture", timeout_seconds=0)
    with pytest.raises(ValueError, match="resilience"):
        create_celery_app("redis://fixture", max_retries=-1)

    class FakeApp:
        def __init__(self) -> None:
            self.options: dict[str, object] = {}

        def task(
            self, *_args: object, **kwargs: object
        ) -> Callable[[Callable[..., object]], object]:
            self.options = kwargs
            return lambda function: function

        def send_task(
            self,
            _name: str,
            _args: list[object],
            *,
            task_id: str,
            eta: datetime | None,
        ) -> object:
            return (task_id, eta)

    event = dispatched_event(uuid4())
    handler = AsyncMock(return_value=WorkerDisposition.SUCCEEDED)
    fake = FakeApp()
    consumer = cast(
        "Callable[[dict[str, object]], object]", register_celery_consumer(fake, handler)
    )
    assert consumer(serialize_event(event)) is WorkerDisposition.SUCCEEDED
    assert fake.options["name"] == CELERY_WORKFLOW_TASK
    assert fake.options["shared"] is False
    handler.assert_awaited_once_with(event)


def test_framework_smoke_executor_is_idempotent_and_bounded() -> None:
    async def scenario() -> None:
        executor = FrameworkSmokeExecutor()
        base = StepExecution(
            uuid4(),
            uuid4(),
            "fixture-step",
            StepKind.CONTROLLED_FAILURE,
            1,
            "fixture-idempotency",
            "fixture-token://input",
            0,
            1,
        )
        with pytest.raises(RetryableStepError, match="controlled-failure"):
            await executor.execute(base)
        result = await executor.execute(replace(base, attempt=2))
        assert await executor.execute(replace(base, attempt=3)) == result
        delayed = replace(
            base,
            task_run_id=uuid4(),
            kind=StepKind.DELAY,
            attempt=1,
            idempotency_key="fixture-delay",
            delay_seconds=0.001,
            fail_until_attempt=0,
        )
        await executor.execute(delayed)
        await executor.compensate(base, "fixture-hook")
        await executor.compensate(base, "fixture-hook")
        assert executor.visible_effects == ("fixture-idempotency", "fixture-delay")
        assert executor.compensations == (("fixture-idempotency", "fixture-hook"),)

    asyncio.run(scenario())


def test_workflow_service_submit_query_control_and_scope_guards() -> None:
    async def scenario() -> None:
        security = context()
        owned_project = project(security)
        repository = RepositoryDouble()
        projects = MagicMock()
        projects.get = AsyncMock(return_value=owned_project)
        authorizer = AuthorizerDouble()
        clock = MutableClock()
        service = WorkflowService(
            repository, projects, cast("AuthorizationService", authorizer), clock
        )

        submitted = await service.submit_framework_smoke(
            security, owned_project.id, idempotency_key="fixture-submit"
        )
        assert submitted.status is WorkflowRunStatus.PENDING
        repository.ensure_definition.assert_awaited_once()
        repository.submit.assert_awaited_once()
        with pytest.raises(ValueError, match="reference"):
            await service.submit(
                security,
                owned_project.id,
                framework_smoke_definition(),
                idempotency_key="fixture",
                input_reference=" bad",
            )

        repository.get_run.return_value = submitted
        repository.pause.return_value = replace(submitted, status=WorkflowRunStatus.PAUSED)
        repository.resume.return_value = replace(submitted, status=WorkflowRunStatus.RUNNING)
        repository.cancel.return_value = replace(submitted, status=WorkflowRunStatus.CANCELLED)
        assert await service.get(security, submitted.id) == submitted
        assert await service.get_steps(security, submitted.id) == ()
        assert await service.get_tasks(security, submitted.id) == ()
        assert (await service.pause(security, submitted.id)).status is WorkflowRunStatus.PAUSED
        assert (await service.resume(security, submitted.id)).status is WorkflowRunStatus.RUNNING
        assert (await service.cancel(security, submitted.id)).status is WorkflowRunStatus.CANCELLED
        assert await service.get_events(security, submitted.id) == ()
        with pytest.raises(ValueError, match="cursor"):
            await service.get_events(security, submitted.id, after_sequence=-1)

        repository.get_run.return_value = None
        with pytest.raises(ScopeViolationError):
            await service.get(security, uuid4())
        projects.get.return_value = None
        with pytest.raises(ScopeViolationError):
            await service.submit_framework_smoke(
                security, uuid4(), idempotency_key="fixture-missing"
            )
        projects.get.return_value = project(security, status=ProjectStatus.ARCHIVED)
        with pytest.raises(InvalidStateError, match="Archived"):
            await service.submit_framework_smoke(
                security, uuid4(), idempotency_key="fixture-archived"
            )

    asyncio.run(scenario())


def test_workflow_service_approval_guards_and_decisions() -> None:
    async def scenario() -> None:
        requester = context()
        approver = context(workspace_id=requester.workspace_id)
        project_id = uuid4()
        workflow_run = run(requester, project_id, status=WorkflowRunStatus.WAITING_APPROVAL)
        approval = ApprovalRequest(
            uuid4(),
            requester.workspace_id,
            project_id,
            workflow_run.id,
            uuid4(),
            requester.actor_id,
            status=ApprovalStatus.PENDING,
            expires_at=NOW + timedelta(seconds=10),
            created_at=NOW,
        )
        repository = RepositoryDouble()
        repository.get_run.return_value = workflow_run
        repository.get_approval.return_value = approval
        repository.decide_approval.return_value = replace(
            workflow_run, status=WorkflowRunStatus.RUNNING
        )
        service = WorkflowService(
            repository,
            MagicMock(),
            cast("AuthorizationService", AuthorizerDouble()),
            MutableClock(),
        )
        assert await service.get_approval(approver, workflow_run.id) == approval
        result = await service.decide_approval(
            approver,
            workflow_run.id,
            WorkflowApprovalDecision.APPROVE,
            reason="fixture-reason",
        )
        assert result.status is WorkflowRunStatus.RUNNING
        with pytest.raises(ValueError, match="reason"):
            await service.decide_approval(
                approver,
                workflow_run.id,
                WorkflowApprovalDecision.REJECT,
                reason="",
            )
        repository.get_approval.return_value = None
        with pytest.raises(InvalidStateError, match="no approval request"):
            await service.get_approval(approver, workflow_run.id)
        with pytest.raises(InvalidStateError, match="no pending"):
            await service.decide_approval(
                approver,
                workflow_run.id,
                WorkflowApprovalDecision.APPROVE,
                reason="fixture",
            )
        repository.get_approval.return_value = approval
        with pytest.raises(PermissionDeniedError):
            await service.decide_approval(
                requester,
                workflow_run.id,
                WorkflowApprovalDecision.APPROVE,
                reason="fixture",
            )
        service_actor = replace(approver, actor_kind=ActorKind.SERVICE)
        with pytest.raises(PermissionDeniedError):
            await service.decide_approval(
                service_actor,
                workflow_run.id,
                WorkflowApprovalDecision.APPROVE,
                reason="fixture",
            )
        expired = replace(approval, expires_at=NOW)
        repository.get_approval.return_value = expired
        repository.expire_approval.return_value = replace(
            workflow_run, status=WorkflowRunStatus.FAILED
        )
        with pytest.raises(InvalidStateError, match="expired"):
            await service.decide_approval(
                approver,
                workflow_run.id,
                WorkflowApprovalDecision.APPROVE,
                reason="fixture",
            )
        assert (
            await service.expire_approval(requester.workspace_id, workflow_run.id)
        ).status is WorkflowRunStatus.FAILED

    asyncio.run(scenario())


class ResultExecutor:
    def __init__(
        self, result: StepExecutionResult | Exception, clock: MutableClock | None = None
    ) -> None:
        self.result = result
        self.clock = clock
        self.compensation_error = False
        self.compensated = 0

    async def execute(self, _execution: StepExecution) -> StepExecutionResult:
        if self.clock is not None:
            self.clock.advance(2)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def compensate(self, _execution: StepExecution, _hook: str) -> None:
        self.compensated += 1
        if self.compensation_error:
            raise RuntimeError("fixture compensation failure")


def test_worker_success_retry_failure_timeout_cancellation_and_duplicates() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        clock = MutableClock()
        repository = RepositoryDouble()
        claim = claimed_task(deadline=NOW + timedelta(seconds=1))
        event = dispatched_event(claim.task.id)
        repository.claim_task.return_value = claim
        repository.succeed_task.return_value = replace(
            claim.run, status=WorkflowRunStatus.SUCCEEDED
        )
        worker = WorkflowWorker(
            repository,
            ResultExecutor(StepExecutionResult("fixture-output://result")),
            clock,
        )
        assert await worker.handle(event) is WorkerDisposition.SUCCEEDED
        repository.succeed_task.assert_awaited_once()

        repository.claim_task.return_value = None
        assert await worker.handle(event) is WorkerDisposition.IGNORED
        unrelated = replace(event, event_type="fixture.unrelated")
        assert await worker.handle(unrelated) is WorkerDisposition.IGNORED
        assert await worker.handle(replace(event, payload={})) is WorkerDisposition.IGNORED
        assert (
            await worker.handle(replace(event, payload={"task_id": 1})) is WorkerDisposition.IGNORED
        )
        assert (
            await worker.handle(replace(event, payload={"task_id": "bad"}))
            is WorkerDisposition.IGNORED
        )

        retry_claim = claimed_task(kind=StepKind.CONTROLLED_FAILURE)
        repository.claim_task.return_value = retry_claim
        repository.fail_task.return_value = FailureSettlement(retry_claim.run, True)
        retry_worker = WorkflowWorker(
            repository,
            ResultExecutor(RetryableStepError("fixture-error://retry")),
            clock,
        )
        assert (
            await retry_worker.handle(dispatched_event(retry_claim.task.id))
            is WorkerDisposition.RETRY_SCHEDULED
        )

        dead_claim = claimed_task(attempt=3, compensation_hook="fixture-hook")
        repository.claim_task.return_value = dead_claim
        repository.fail_task.return_value = FailureSettlement(
            replace(dead_claim.run, status=WorkflowRunStatus.FAILED), False
        )
        permanent = ResultExecutor(PermanentStepError("fixture-error://permanent"))
        dead_worker = WorkflowWorker(repository, permanent, clock)
        assert (
            await dead_worker.handle(dispatched_event(dead_claim.task.id))
            is WorkerDisposition.DEAD_LETTERED
        )
        assert permanent.compensated == 1

        unknown = ResultExecutor(RuntimeError("private detail"))
        unknown.compensation_error = True
        unknown_worker = WorkflowWorker(repository, unknown, clock)
        assert (
            await unknown_worker.handle(dispatched_event(dead_claim.task.id))
            is WorkerDisposition.DEAD_LETTERED
        )
        failed_call = repository.fail_task.await_args
        assert failed_call is not None
        assert failed_call.kwargs["error_reference"] == "workflow-error://compensation-failed"

        timed_claim = claimed_task(deadline=NOW + timedelta(seconds=1))
        repository.claim_task.return_value = timed_claim
        repository.fail_task.return_value = FailureSettlement(timed_claim.run, True)
        advancing_clock = MutableClock()
        timed_worker = WorkflowWorker(
            repository,
            ResultExecutor(StepExecutionResult("fixture-output://late"), advancing_clock),
            advancing_clock,
        )
        assert (
            await timed_worker.handle(dispatched_event(timed_claim.task.id))
            is WorkerDisposition.RETRY_SCHEDULED
        )

        class SlowExecutor(ResultExecutor):
            async def execute(self, _execution: StepExecution) -> StepExecutionResult:
                await asyncio.sleep(0.02)
                return cast("StepExecutionResult", self.result)

        short_step = replace(timed_claim.step, timeout_seconds=0.001)
        repository.claim_task.return_value = replace(timed_claim, step=short_step)
        timeout_worker = WorkflowWorker(
            repository,
            SlowExecutor(StepExecutionResult("fixture-output://late")),
            clock,
        )
        assert (
            await timeout_worker.handle(dispatched_event(timed_claim.task.id))
            is WorkerDisposition.RETRY_SCHEDULED
        )

        repository.claim_task.return_value = claim
        repository.is_cancelling.return_value = True
        repository.cancel_task.return_value = replace(claim.run, status=WorkflowRunStatus.CANCELLED)
        cancelling_worker = WorkflowWorker(
            repository,
            ResultExecutor(StepExecutionResult("fixture-output://cancelled")),
            clock,
        )
        assert await cancelling_worker.handle(event) is WorkerDisposition.CANCELLED
        repository.cancel_task.assert_awaited()

        cancelling_failure = claimed_task(
            kind=StepKind.CONTROLLED_FAILURE,
            compensation_hook="fixture-hook",
        )
        repository.claim_task.return_value = cancelling_failure
        repository.cancel_task.reset_mock()
        fail_count = repository.fail_task.await_count
        cancelled_executor = ResultExecutor(PermanentStepError("fixture-error://cancelled"))
        cancelled_executor.compensation_error = True
        cancelled_worker = WorkflowWorker(repository, cancelled_executor, clock)
        assert (
            await cancelled_worker.handle(dispatched_event(cancelling_failure.task.id))
            is WorkerDisposition.CANCELLED
        )
        assert cancelled_executor.compensated == 1
        cancel_call = repository.cancel_task.await_args
        assert cancel_call is not None
        assert cancel_call.kwargs["error_reference"] == "workflow-error://compensation-failed"
        assert repository.fail_task.await_count == fail_count

        with pytest.raises(ValueError, match="lease"):
            WorkflowWorker(repository, permanent, clock, lease_seconds=0)

    asyncio.run(scenario())
