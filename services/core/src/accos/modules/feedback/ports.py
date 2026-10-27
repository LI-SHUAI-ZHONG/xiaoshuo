"""Persistence and Creator signal ports for the feedback boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.modules.feedback.domain import (
        BehaviorConsent,
        DiagnosticFinding,
        Experiment,
        ExperimentSample,
        ExperimentStatus,
        FeedbackEvent,
        MetricDefinition,
        MetricPoint,
        Variant,
        WithdrawalResult,
    )


class FeedbackRepository(Protocol):
    async def add_consent(
        self, consent: BehaviorConsent, event: EventEnvelope
    ) -> BehaviorConsent: ...

    async def active_consent(
        self, workspace_id: UUID, project_id: UUID, actor_id: UUID
    ) -> BehaviorConsent | None: ...

    async def withdraw_consent(
        self,
        workspace_id: UUID,
        project_id: UUID,
        actor_id: UUID,
        *,
        withdrawn_at: datetime,
        event: EventEnvelope,
    ) -> WithdrawalResult: ...

    async def add_feedback(self, item: FeedbackEvent, event: EventEnvelope) -> FeedbackEvent: ...

    async def get_feedback(
        self, workspace_id: UUID, project_id: UUID, event_id: UUID
    ) -> FeedbackEvent | None: ...

    async def add_metric_definition(self, item: MetricDefinition) -> MetricDefinition: ...

    async def add_metric_point(self, item: MetricPoint, event: EventEnvelope) -> MetricPoint: ...

    async def get_metric_point(
        self, workspace_id: UUID, project_id: UUID, point_id: UUID
    ) -> MetricPoint | None: ...

    async def add_diagnostic(
        self, item: DiagnosticFinding, event: EventEnvelope
    ) -> DiagnosticFinding: ...

    async def get_diagnostic(
        self, workspace_id: UUID, project_id: UUID, finding_id: UUID
    ) -> DiagnosticFinding | None: ...

    async def add_experiment(
        self, item: Experiment, variants: tuple[Variant, ...], event: EventEnvelope
    ) -> tuple[Experiment, tuple[Variant, ...]]: ...

    async def get_experiment(
        self, workspace_id: UUID, project_id: UUID, experiment_id: UUID
    ) -> tuple[Experiment, tuple[Variant, ...]] | None: ...

    async def transition_experiment(
        self,
        item: Experiment,
        expected_status: ExperimentStatus,
        event: EventEnvelope,
    ) -> Experiment: ...

    async def add_sample(
        self, item: ExperimentSample, event: EventEnvelope
    ) -> ExperimentSample: ...
