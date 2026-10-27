"""Ports owned by the workflows module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime, timedelta
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.kernel.security import SecurityContext
    from accos.modules.workflows.domain import (
        ApprovalRecord,
        ApprovalRequest,
        ClaimedTask,
        CompensationRecord,
        CompensationStatus,
        DependencyEdge,
        ReadReceipt,
        ResolvedInput,
        StageRequirement,
        StepExecution,
        StepExecutionResult,
        StepInputManifest,
        StepRun,
        TaskRun,
        WorkflowDefinition,
        WorkflowRun,
        WorkflowRunEvent,
        WorkflowSchedule,
    )


@dataclass(frozen=True, slots=True)
class FailureSettlement:
    """Repository result for a failed attempt."""

    run: WorkflowRun
    retry_scheduled: bool


class WorkflowRepository(Protocol):
    """Persistent workflow state and atomic transition boundary."""

    async def ensure_definition(self, definition: WorkflowDefinition) -> None: ...

    async def get_definition(self, definition_id: UUID) -> WorkflowDefinition | None: ...

    async def submit(  # noqa: PLR0913 - mirrors the durable submission contract.
        self,
        run: WorkflowRun,
        definition: WorkflowDefinition,
        *,
        request_digest: str,
        resolved_inputs: dict[str, tuple[ResolvedInput, ...]] | None = None,
        prompt_pin: str | None = None,
        model_pin: str | None = None,
        budget_reservation_refs: dict[str, str] | None = None,
    ) -> tuple[WorkflowRun, bool]: ...

    async def get_run(self, workspace_id: UUID, run_id: UUID) -> WorkflowRun | None: ...

    async def get_steps(self, workspace_id: UUID, run_id: UUID) -> tuple[StepRun, ...]: ...

    async def get_tasks(self, workspace_id: UUID, run_id: UUID) -> tuple[TaskRun, ...]: ...

    async def get_events(
        self, workspace_id: UUID, run_id: UUID, *, after_sequence: int = 0
    ) -> tuple[WorkflowRunEvent, ...]: ...

    async def get_input_manifests(
        self, workspace_id: UUID, run_id: UUID
    ) -> tuple[StepInputManifest, ...]: ...

    async def get_read_receipts(
        self, workspace_id: UUID, run_id: UUID
    ) -> tuple[ReadReceipt, ...]: ...

    async def append_read_receipts(
        self,
        workspace_id: UUID,
        run_id: UUID,
        step_run_id: UUID,
        receipts: tuple[ReadReceipt, ...],
    ) -> None: ...

    async def get_dependency_edges(
        self, workspace_id: UUID, run_id: UUID
    ) -> tuple[DependencyEdge, ...]: ...

    async def invalidate_dependencies(
        self,
        workspace_id: UUID,
        producer_reference: str,
        *,
        replacement_hash: str,
        now: datetime,
    ) -> tuple[UUID, ...]: ...

    async def pause(
        self, workspace_id: UUID, run_id: UUID, *, actor_id: UUID, now: datetime
    ) -> WorkflowRun: ...

    async def resume(
        self, workspace_id: UUID, run_id: UUID, *, actor_id: UUID, now: datetime
    ) -> WorkflowRun: ...

    async def cancel(
        self, workspace_id: UUID, run_id: UUID, *, actor_id: UUID, now: datetime
    ) -> WorkflowRun: ...

    async def get_approval(self, workspace_id: UUID, run_id: UUID) -> ApprovalRequest | None: ...

    async def decide_approval(
        self,
        workspace_id: UUID,
        run_id: UUID,
        record: ApprovalRecord,
    ) -> WorkflowRun: ...

    async def expire_approval(
        self, workspace_id: UUID, run_id: UUID, *, now: datetime
    ) -> WorkflowRun: ...

    async def claim_task(
        self,
        task_id: UUID,
        delivery_event_id: UUID,
        *,
        now: datetime,
        lease: timedelta,
    ) -> ClaimedTask | None: ...

    async def is_cancelling(self, task_id: UUID, lease_token: UUID) -> bool: ...

    async def is_manifest_current(self, task_id: UUID, lease_token: UUID) -> bool: ...

    async def succeed_task(
        self,
        claimed: ClaimedTask,
        *,
        output_reference: str,
        now: datetime,
    ) -> WorkflowRun: ...

    async def fail_task(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        now: datetime,
        retry_at: datetime | None,
    ) -> FailureSettlement: ...

    async def cancel_task(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        now: datetime,
    ) -> WorkflowRun: ...

    async def mark_task_unknown(
        self,
        claimed: ClaimedTask,
        *,
        error_reference: str,
        provider_job_id: str | None,
        now: datetime,
    ) -> WorkflowRun: ...

    async def mark_task_stale(
        self,
        claimed: ClaimedTask,
        *,
        now: datetime,
    ) -> WorkflowRun: ...

    async def save_schedule(self, schedule: WorkflowSchedule) -> WorkflowSchedule: ...

    async def get_schedule(
        self, workspace_id: UUID, schedule_id: UUID
    ) -> WorkflowSchedule | None: ...

    async def list_schedules(
        self, workspace_id: UUID, project_id: UUID | None = None
    ) -> tuple[WorkflowSchedule, ...]: ...

    async def begin_compensation(
        self,
        claimed: ClaimedTask,
        hook: str,
        *,
        now: datetime,
    ) -> tuple[CompensationRecord, bool]: ...

    async def settle_compensation(  # noqa: PLR0913 - explicit durable settlement fields.
        self,
        claimed: ClaimedTask,
        record_id: UUID,
        status: CompensationStatus,
        *,
        result_reference: str | None,
        error_reference: str | None,
        now: datetime,
    ) -> CompensationRecord: ...


class StepExecutor(Protocol):
    """Idempotent technical side-effect boundary used by the Worker."""

    async def execute(self, execution: StepExecution) -> StepExecutionResult: ...

    async def compensate(self, execution: StepExecution, hook: str) -> None: ...


class DependencyResolver(Protocol):
    """Resolve and authorize immutable content references without constructing context."""

    async def resolve(
        self,
        context: SecurityContext,
        project_id: UUID,
        requirements: tuple[StageRequirement, ...],
        candidate_references: dict[str, str],
        *,
        now: datetime,
    ) -> tuple[ResolvedInput, ...]: ...


class ContextBuilderPort(Protocol):
    """Stage 30 hook for the sole context builder and its actual-read evidence."""

    async def build(
        self,
        context: SecurityContext,
        project_id: UUID,
        manifest: StepInputManifest,
    ) -> tuple[str, tuple[ReadReceipt, ...]]: ...


class WorkflowScheduleRepository(Protocol):
    """Persistent schedule operations consumed by the shared Worker scheduler."""

    async def save_schedule(self, schedule: WorkflowSchedule) -> WorkflowSchedule: ...

    async def get_schedule(
        self, workspace_id: UUID, schedule_id: UUID
    ) -> WorkflowSchedule | None: ...

    async def list_schedules(
        self, workspace_id: UUID, project_id: UUID | None = None
    ) -> tuple[WorkflowSchedule, ...]: ...

    async def claim_due_schedules(
        self,
        *,
        now: datetime,
        lease: timedelta,
        worker_id: str,
        limit: int = 25,
    ) -> tuple[WorkflowSchedule, ...]: ...

    async def settle_schedule_claim(
        self,
        schedule_id: UUID,
        lease_token: UUID,
        *,
        next_due_at: datetime,
        last_run_id: UUID | None,
        now: datetime,
    ) -> WorkflowSchedule: ...


class QueueDeliveryHandler(Protocol):
    """Inbound worker handler shared by fake and Celery transports."""

    async def handle(self, event: EventEnvelope) -> object: ...
