"""Authorized workflow use cases and the durable Worker task handler."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.contracts import IdempotencyKey
from accos.kernel.errors import (
    AuthenticationRequiredError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds, parse_id
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus
from accos.modules.workflows.definitions import framework_smoke_definition
from accos.modules.workflows.domain import (
    ApprovalRecord,
    CompensationStatus,
    MisfirePolicy,
    PermanentStepError,
    RetryableStepError,
    ScheduleStatus,
    StepExecution,
    UnknownStepResultError,
    WorkerDisposition,
    WorkflowApprovalDecision,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowSchedule,
)
from accos.modules.workflows.scheduling import next_occurrence

_MAX_REFERENCE_LENGTH = 500

if TYPE_CHECKING:
    from accos.kernel.clock import Clock
    from accos.kernel.events import EventEnvelope
    from accos.modules.identity.public import ApprovalPolicyPort, AuthorizationService
    from accos.modules.projects.public import ProjectRepository
    from accos.modules.workflows.domain import (
        ApprovalRequest,
        ClaimedTask,
        DependencyEdge,
        ReadReceipt,
        ResolvedInput,
        StepInputManifest,
        StepRun,
        TaskRun,
        WorkflowRunEvent,
    )
    from accos.modules.workflows.ports import (
        ContextBuilderPort,
        DependencyResolver,
        StepExecutor,
        WorkflowRepository,
    )


class WorkflowService:
    """Submit and control the only durable long-running orchestration mechanism."""

    def __init__(  # noqa: PLR0913,PLR0917 - explicit authorization dependencies.
        self,
        repository: WorkflowRepository,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
        clock: Clock,
        approval_policies: ApprovalPolicyPort | None = None,
        dependency_resolver: DependencyResolver | None = None,
    ) -> None:
        self._repository = repository
        self._projects = projects
        self._authorizer = authorizer
        self._clock = clock
        self._approval_policies = approval_policies
        self._dependency_resolver = dependency_resolver

    async def submit_framework_smoke(
        self,
        context: SecurityContext,
        project_id: UUID,
        *,
        idempotency_key: str,
        input_reference: str = "fixture-token://framework-smoke",
    ) -> WorkflowRun:
        """Submit the built-in metadata-only smoke workflow."""
        return await self.submit(
            context,
            project_id,
            framework_smoke_definition(),
            idempotency_key=idempotency_key,
            input_reference=input_reference,
        )

    async def submit(  # noqa: PLR0913 - explicit frozen-run submission contract.
        self,
        context: SecurityContext,
        project_id: UUID,
        definition: WorkflowDefinition,
        *,
        idempotency_key: str,
        input_reference: str,
        candidate_references: dict[str, str] | None = None,
        prompt_pin: str | None = None,
        model_pin: str | None = None,
        budget_reservation_refs: dict[str, str] | None = None,
    ) -> WorkflowRun:
        """Persist a versioned definition and idempotent run before dispatch."""
        key = IdempotencyKey(idempotency_key)
        reference = _validated_reference(input_reference)
        await self._authorize_project(context, project_id)
        now = self._clock.now()
        resolved_inputs = await self._resolve_inputs(
            context,
            project_id,
            definition,
            candidate_references or {},
            now=now,
        )
        await self._repository.ensure_definition(definition)
        run = WorkflowRun(
            uuid4(),
            context.workspace_id,
            project_id,
            definition.id,
            definition.name,
            definition.version,
            WorkflowRunStatus.PENDING,
            key.value,
            reference,
            context.actor_id,
            context.actor_kind.value,
            UUID(context.correlation.request_id),
            now,
            now,
            permission_snapshot=tuple(sorted(context.permissions)),
            policy_version=context.policy_version,
            auth_method=context.auth_method,
            credential_id=context.credential_id,
            approval_policy_ref=(await self._approval_policies.snapshot(context.workspace_id))
            if self._approval_policies
            else "legacy_dual_control",
        )
        digest = hashlib.sha256(
            json.dumps(
                {
                    "definition": definition.name,
                    "version": definition.version,
                    "project_id": str(project_id),
                    "input_reference": reference,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        stored, _created = await self._repository.submit(
            run,
            definition,
            request_digest=digest,
            resolved_inputs=resolved_inputs,
            prompt_pin=prompt_pin,
            model_pin=model_pin,
            budget_reservation_refs=budget_reservation_refs,
        )
        return stored

    async def retry(
        self,
        context: SecurityContext,
        run_id: UUID,
        *,
        idempotency_key: str,
    ) -> WorkflowRun:
        """Create a linked run from the original immutable definition and input pins."""
        original = await self._require_run(context, run_id)
        await self._authorize_run(context, original)
        if original.status not in {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
        }:
            raise InvalidStateError("Only terminal workflow runs can be retried.")
        definition = await self._repository.get_definition(original.definition_id)
        if definition is None:
            raise InvalidStateError("The immutable workflow definition is unavailable.")
        manifests = await self._repository.get_input_manifests(context.workspace_id, run_id)
        by_step_definition = {item.step_definition_id: item for item in manifests}
        resolved_inputs = {
            step.key: by_step_definition[step.id].resolved_inputs
            for step in definition.steps
            if step.id in by_step_definition
        }
        key = IdempotencyKey(idempotency_key)
        now = self._clock.now()
        retry_run = replace(
            original,
            id=uuid4(),
            status=WorkflowRunStatus.PENDING,
            idempotency_key=key.value,
            correlation_id=UUID(context.correlation.request_id),
            created_at=now,
            updated_at=now,
            current_step_position=0,
            output_reference=None,
            error_reference=None,
            pause_requested_at=None,
            cancel_requested_at=None,
            version=1,
            previous_run_id=original.id,
        )
        digest = hashlib.sha256(
            f"retry:{original.id}:{definition.id}:{key.value}".encode()
        ).hexdigest()
        stored, _created = await self._repository.submit(
            retry_run,
            definition,
            request_digest=digest,
            resolved_inputs=resolved_inputs,
            prompt_pin=manifests[0].prompt_pin if manifests else None,
            model_pin=manifests[0].model_pin if manifests else None,
            budget_reservation_refs={
                step.key: manifest.budget_reservation_ref
                for step in definition.steps
                if (manifest := by_step_definition.get(step.id)) is not None
                and manifest.budget_reservation_ref is not None
            },
        )
        return stored

    async def get_inputs(
        self, context: SecurityContext, run_id: UUID
    ) -> tuple[StepInputManifest, ...]:
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_input_manifests(context.workspace_id, run_id)

    async def get_receipts(
        self, context: SecurityContext, run_id: UUID
    ) -> tuple[ReadReceipt, ...]:
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_read_receipts(context.workspace_id, run_id)

    async def get_dependencies(
        self, context: SecurityContext, run_id: UUID
    ) -> tuple[DependencyEdge, ...]:
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_dependency_edges(context.workspace_id, run_id)

    async def create_schedule(
        self,
        context: SecurityContext,
        project_id: UUID,
        definition_id: UUID,
        *,
        expression: str,
        timezone: str,
        misfire_policy: MisfirePolicy,
        input_reference: str,
        idempotency_prefix: str,
    ) -> WorkflowSchedule:
        """Persist a schedule for a published requirement-free definition version."""
        await self._authorize_project(context, project_id)
        definition = await self._repository.get_definition(definition_id)
        if definition is None:
            raise ScopeViolationError
        if definition.status.value != "published":
            raise InvalidStateError("Only published workflow definitions can be scheduled.")
        if any(step.requirements for step in definition.steps):
            raise InvalidStateError(
                "Scheduled definitions with required inputs need an explicit resolver binding."
            )
        now = self._clock.now()
        schedule = WorkflowSchedule(
            uuid4(),
            context.workspace_id,
            project_id,
            definition.id,
            definition.name,
            definition.version,
            expression,
            timezone,
            misfire_policy,
            ScheduleStatus.ACTIVE,
            _validated_reference(input_reference),
            next_occurrence(expression, timezone, now),
            context.actor_id,
            IdempotencyKey(idempotency_prefix).value,
            now,
            now,
        )
        return await self._repository.save_schedule(schedule)

    async def list_schedules(
        self, context: SecurityContext, project_id: UUID
    ) -> tuple[WorkflowSchedule, ...]:
        await self._authorize_project(context, project_id)
        return await self._repository.list_schedules(context.workspace_id, project_id)

    async def get(self, context: SecurityContext, run_id: UUID) -> WorkflowRun:
        """Return one run only within its workspace and project scope."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return run

    async def get_steps(self, context: SecurityContext, run_id: UUID) -> tuple[StepRun, ...]:
        """Return the ordered durable steps for an authorized run."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_steps(context.workspace_id, run_id)

    async def get_tasks(self, context: SecurityContext, run_id: UUID) -> tuple[TaskRun, ...]:
        """Return the ordered queue-task attempts for an authorized run."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_tasks(context.workspace_id, run_id)

    async def get_approval(self, context: SecurityContext, run_id: UUID) -> ApprovalRequest:
        """Return the current approval without weakening project authorization."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        approval = await self._repository.get_approval(context.workspace_id, run_id)
        if approval is None:
            raise InvalidStateError("The workflow run has no approval request.")
        return approval

    async def pause(self, context: SecurityContext, run_id: UUID) -> WorkflowRun:
        """Pause scheduling at a durable task boundary."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.pause(
            context.workspace_id,
            run_id,
            actor_id=context.actor_id,
            now=self._clock.now(),
        )

    async def can_decide(self, context: SecurityContext, approval: ApprovalRequest) -> bool:
        if Permission.APPROVAL_DECIDE.value not in context.permissions:
            return False
        if self._approval_policies is None:
            return False
        try:
            await self._approval_policies.require_decision(
                context, approval.requested_by, approval.approval_policy_ref
            )
        except (PermissionDeniedError, AuthenticationRequiredError):
            return False
        return self._clock.now() < approval.expires_at

    async def resume(self, context: SecurityContext, run_id: UUID) -> WorkflowRun:
        """Resume a paused task by writing a fresh dispatch event to the Outbox."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.resume(
            context.workspace_id,
            run_id,
            actor_id=context.actor_id,
            now=self._clock.now(),
        )

    async def cancel(self, context: SecurityContext, run_id: UUID) -> WorkflowRun:
        """Request cancellation and settle immediately when no task owns a lease."""
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.cancel(
            context.workspace_id,
            run_id,
            actor_id=context.actor_id,
            now=self._clock.now(),
        )

    async def get_events(
        self,
        context: SecurityContext,
        run_id: UUID,
        *,
        after_sequence: int = 0,
    ) -> tuple[WorkflowRunEvent, ...]:
        """Read ordered versioned run events for future SSE projection."""
        if after_sequence < 0:
            raise ValueError("event cursor cannot be negative")
        run = await self._require_run(context, run_id)
        await self._authorize_run(context, run)
        return await self._repository.get_events(
            context.workspace_id, run_id, after_sequence=after_sequence
        )

    async def decide_approval(
        self,
        context: SecurityContext,
        run_id: UUID,
        decision: WorkflowApprovalDecision,
        *,
        reason: str,
    ) -> WorkflowRun:
        """Append one explicit human decision; approvals are never implicit."""
        normalized_reason = _validated_reason(reason)
        run = await self._require_run(context, run_id)
        approval = await self._repository.get_approval(context.workspace_id, run_id)
        authorization = AuthorizationRequest(
            context,
            Permission.APPROVAL_DECIDE,
            ResourceScope(run.workspace_id, "workflow_run", str(run.id), run.project_id),
        )
        if approval is None:
            await self._authorizer.reject(
                authorization,
                InvalidStateError("The workflow run has no pending approval."),
                reason_code="workflow_approval_unavailable",
            )
        if context.actor_kind is not ActorKind.USER:
            await self._authorizer.reject(
                authorization,
                PermissionDeniedError(),
                reason_code="human_actor_required",
            )
        if self._approval_policies is not None:
            await self._approval_policies.require_decision(
                context, approval.requested_by, approval.approval_policy_ref
            )
        if self._approval_policies is None and context.actor_id == approval.requested_by:
            await self._authorizer.reject(
                authorization,
                PermissionDeniedError(),
                reason_code="separation_of_duties",
            )
        if self._clock.now() >= approval.expires_at:
            await self._repository.expire_approval(
                context.workspace_id, run_id, now=self._clock.now()
            )
            raise InvalidStateError("The workflow approval request expired.")
        await self._authorizer.authorize(authorization)
        return await self._repository.decide_approval(
            context.workspace_id,
            run_id,
            ApprovalRecord(
                uuid4(),
                context.workspace_id,
                approval.id,
                context.actor_id,
                decision,
                normalized_reason,
                self._clock.now(),
                approval.approval_policy_ref,
                approval.input_digest,
            ),
        )

    async def expire_approval(self, workspace_id: UUID, run_id: UUID) -> WorkflowRun:
        """Settle one known expired request; callers must not scan another module's tables."""
        return await self._repository.expire_approval(workspace_id, run_id, now=self._clock.now())

    async def _resolve_inputs(
        self,
        context: SecurityContext,
        project_id: UUID,
        definition: WorkflowDefinition,
        candidates: dict[str, str],
        *,
        now: datetime,
    ) -> dict[str, tuple[ResolvedInput, ...]]:
        if self._dependency_resolver is None:
            if any(step.requirements for step in definition.steps):
                raise InvalidStateError("Workflow dependency resolution is not configured.")
            return {}
        return {
            step.key: await self._dependency_resolver.resolve(
                context,
                project_id,
                step.requirements,
                candidates,
                now=now,
            )
            for step in definition.steps
        }

    async def _authorize_project(self, context: SecurityContext, project_id: UUID) -> None:
        project = await self._projects.get(context.workspace_id, project_id)
        if project is None:
            await self._authorizer.reject(
                AuthorizationRequest(
                    context,
                    Permission.AGENT_RUN,
                    ResourceScope(context.workspace_id, "project", str(project_id), project_id),
                ),
                ScopeViolationError(),
                reason_code="project_unavailable",
            )
        if project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot start workflows.")
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.AGENT_RUN,
                ResourceScope(project.workspace_id, "project", str(project.id), project.id),
            )
        )

    async def _require_run(self, context: SecurityContext, run_id: UUID) -> WorkflowRun:
        run = await self._repository.get_run(context.workspace_id, run_id)
        if run is None:
            await self._authorizer.reject(
                AuthorizationRequest(
                    context,
                    Permission.AGENT_RUN,
                    ResourceScope(context.workspace_id, "workflow_run", str(run_id)),
                ),
                ScopeViolationError(),
                reason_code="workflow_run_unavailable",
            )
        return run

    async def _authorize_run(self, context: SecurityContext, run: WorkflowRun) -> None:
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.AGENT_RUN,
                ResourceScope(run.workspace_id, "workflow_run", str(run.id), run.project_id),
            )
        )


class WorkflowWorker:
    """Consume task dispatches and settle all business state in PostgreSQL."""

    def __init__(
        self,
        repository: WorkflowRepository,
        executor: StepExecutor,
        clock: Clock,
        *,
        lease_seconds: float = 30.0,
        context_builder: ContextBuilderPort | None = None,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("worker lease must be positive")
        self._repository = repository
        self._executor = executor
        self._clock = clock
        self._lease = timedelta(seconds=lease_seconds)
        self._context_builder = context_builder

    async def handle(self, event: EventEnvelope) -> WorkerDisposition:  # noqa: PLR0911
        """Handle one at-least-once delivery, safely ignoring unrelated events."""
        if event.event_type != "workflows.task-dispatched":
            return WorkerDisposition.IGNORED
        raw_task_id = event.payload.get("task_id")
        if not isinstance(raw_task_id, str):
            return WorkerDisposition.IGNORED
        try:
            task_id = parse_id(raw_task_id)
        except ValueError:
            return WorkerDisposition.IGNORED
        claimed = await self._repository.claim_task(
            task_id,
            event.id,
            now=self._clock.now(),
            lease=self._lease,
        )
        if claimed is None:
            return WorkerDisposition.IGNORED
        if not await self._repository.is_manifest_current(
            claimed.task.id, claimed.lease_token
        ):
            await self._repository.mark_task_stale(claimed, now=self._clock.now())
            return WorkerDisposition.CANCELLED
        execution = _execution(claimed)
        try:
            execution = await self._build_context(claimed, execution)
            async with asyncio.timeout(claimed.step.timeout_seconds):
                result = await self._executor.execute(execution)
        except TimeoutError:
            return await self._fail(claimed, execution, "workflow-error://timeout", retryable=True)
        except RetryableStepError as error:
            return await self._fail(claimed, execution, error.error_reference, retryable=True)
        except PermanentStepError as error:
            return await self._fail(claimed, execution, error.error_reference, retryable=False)
        except UnknownStepResultError as error:
            await self._repository.mark_task_unknown(
                claimed,
                error_reference=error.error_reference,
                provider_job_id=error.provider_job_id,
                now=self._clock.now(),
            )
            return WorkerDisposition.AWAITING_EXTERNAL_RESULT
        except Exception:  # noqa: BLE001 - unknown executor details never cross the boundary.
            return await self._fail(
                claimed, execution, "workflow-error://internal", retryable=False
            )
        now = self._clock.now()
        if claimed.task.deadline is not None and now >= claimed.task.deadline:
            return await self._fail(claimed, execution, "workflow-error://timeout", retryable=True)
        if await self._repository.is_cancelling(claimed.task.id, claimed.lease_token):
            return await self._cancel(claimed, execution, now=now)
        await self._repository.succeed_task(
            claimed,
            output_reference=result.output_reference,
            now=now,
        )
        return WorkerDisposition.SUCCEEDED

    async def _build_context(
        self,
        claimed: ClaimedTask,
        execution: StepExecution,
    ) -> StepExecution:
        if self._context_builder is None or claimed.step_run.input_manifest_id is None:
            return execution
        manifests = await self._repository.get_input_manifests(
            claimed.run.workspace_id, claimed.run.id
        )
        manifest = next(
            (
                item
                for item in manifests
                if item.id == claimed.step_run.input_manifest_id
            ),
            None,
        )
        if manifest is None or execution.context is None:
            raise PermanentStepError("workflow-input://manifest-missing")
        context_reference, receipts = await self._context_builder.build(
            execution.context,
            claimed.run.project_id,
            manifest,
        )
        if receipts:
            await self._repository.append_read_receipts(
                claimed.run.workspace_id,
                claimed.run.id,
                claimed.step_run.id,
                receipts,
            )
        return replace(execution, input_reference=context_reference)

    async def _fail(
        self,
        claimed: ClaimedTask,
        execution: StepExecution,
        error_reference: str,
        *,
        retryable: bool,
    ) -> WorkerDisposition:
        now = self._clock.now()
        if await self._repository.is_cancelling(claimed.task.id, claimed.lease_token):
            return await self._cancel(claimed, execution, now=now)
        can_retry = retryable and claimed.task.attempt < claimed.step.retry_policy.max_attempts
        retry_at = (
            now + timedelta(seconds=claimed.step.retry_policy.delay_after(claimed.task.attempt))
            if can_retry
            else None
        )
        if retry_at is None:
            compensation_error = await self._compensate(claimed, execution)
            if compensation_error is not None:
                error_reference = compensation_error
        result = await self._repository.fail_task(
            claimed,
            error_reference=error_reference,
            now=now,
            retry_at=retry_at,
        )
        return (
            WorkerDisposition.RETRY_SCHEDULED
            if result.retry_scheduled
            else WorkerDisposition.DEAD_LETTERED
        )

    async def _cancel(
        self,
        claimed: ClaimedTask,
        execution: StepExecution,
        *,
        now: datetime,
    ) -> WorkerDisposition:
        compensation_error = await self._compensate(claimed, execution)
        await self._repository.cancel_task(
            claimed,
            error_reference=compensation_error or "workflow-error://cancelled",
            now=now,
        )
        return WorkerDisposition.CANCELLED

    async def _compensate(self, claimed: ClaimedTask, execution: StepExecution) -> str | None:
        hook = claimed.step.compensation_hook
        if hook is None:
            return None
        record, created = await self._repository.begin_compensation(
            claimed,
            hook,
            now=self._clock.now(),
        )
        if not created:
            if record.status is CompensationStatus.SUCCEEDED:
                return None
            return record.error_reference or "workflow-error://compensation-result-unknown"
        try:
            await self._executor.compensate(execution, hook)
        except asyncio.CancelledError:
            await asyncio.shield(
                self._repository.settle_compensation(
                    claimed,
                    record.id,
                    CompensationStatus.UNKNOWN,
                    result_reference=None,
                    error_reference="workflow-error://compensation-result-unknown",
                    now=self._clock.now(),
                )
            )
            raise
        except Exception:  # noqa: BLE001 - the durable state signals manual intervention.
            await self._repository.settle_compensation(
                claimed,
                record.id,
                CompensationStatus.FAILED,
                result_reference=None,
                error_reference="workflow-error://compensation-failed",
                now=self._clock.now(),
            )
            return "workflow-error://compensation-failed"
        await self._repository.settle_compensation(
            claimed,
            record.id,
            CompensationStatus.SUCCEEDED,
            result_reference=f"workflow-compensation://{record.id}",
            error_reference=None,
            now=self._clock.now(),
        )
        return None


def _execution(claimed: ClaimedTask) -> StepExecution:
    return StepExecution(
        claimed.run.id,
        claimed.task.id,
        claimed.step.key,
        claimed.step.kind,
        claimed.task.attempt,
        claimed.task.idempotency_key,
        claimed.task.input_reference,
        claimed.step.delay_seconds,
        claimed.step.fail_until_attempt,
        SecurityContext(
            actor_id=claimed.run.requested_by,
            actor_kind=ActorKind(claimed.run.actor_kind),
            workspace_id=claimed.run.workspace_id,
            project_id=claimed.run.project_id,
            permissions=frozenset(claimed.run.permission_snapshot),
            policy_version=claimed.run.policy_version,
            auth_method="pat" if claimed.run.auth_method == "pat" else "task",
            credential_id=claimed.run.credential_id,
            correlation=CorrelationIds(
                request_id=str(claimed.run.correlation_id),
                trace_id=str(claimed.run.correlation_id),
                task_id=str(claimed.task.id),
            ),
        ),
        claimed.task.operation_key,
        claimed.step_run.input_manifest_id,
    )


def _validated_reference(value: str) -> str:
    if not value or value.strip() != value or len(value) > _MAX_REFERENCE_LENGTH:
        raise ValueError(
            "workflow reference must be non-empty, trimmed, and at most 500 characters"
        )
    return value


def _validated_reason(value: str) -> str:
    if not value or value.strip() != value or len(value) > _MAX_REFERENCE_LENGTH:
        raise ValueError("approval reason must be non-empty, trimmed, and at most 500 characters")
    return value
