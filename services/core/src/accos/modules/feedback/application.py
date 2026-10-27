"""Consent-gated feedback, metrics, diagnostics, and technical experiments."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from accos.kernel.errors import InvalidStateError, PermissionDeniedError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.security import ActorKind
from accos.modules.creative.public import (
    CreativeRecordStatus,
    ExtensionStatus,
    PreferenceSignal,
)
from accos.modules.feedback.domain import (
    BehaviorConsent,
    ConsentStatus,
    Experiment,
    ExperimentSample,
    ExperimentStatus,
    FeedbackEvent,
    FeedbackSource,
    FeedbackStatus,
    MetricDefinition,
    MetricDimension,
    MetricPoint,
    MetricSensitivity,
    Variant,
    WithdrawalResult,
)
from accos.modules.feedback.registry import MetricRegistry, default_metric_definitions
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.creative.public import PreferenceSignalIngestPort
    from accos.modules.feedback.diagnostics import SystemDoctor
    from accos.modules.feedback.domain import DiagnosticFinding
    from accos.modules.feedback.ports import FeedbackRepository
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.projects.public import ProjectRepository

BEHAVIOR_CONSENT_POLICY_VERSION = "behavior-consent-v1"
TECHNICAL_SAMPLE_SCOPE = "technical-smoke"
_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,99}$")
_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")
_CREATOR_SIGNAL_SCHEMAS = frozenset({"creator-preference.v1", "creator-decision.v1"})
_MINIMUM_VARIANTS = 2


@dataclass(frozen=True, slots=True)
class CaptureFeedbackCommand:
    project_id: UUID
    source: FeedbackSource
    schema_version: str
    signal_code: str
    numeric_value: float | None = None
    source_reference: str | None = None
    consent_policy_version: str | None = None
    creator_profile_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RegisterMetricCommand:
    project_id: UUID
    name: str
    version: int
    unit: str
    dimensions: tuple[MetricDimension, ...]
    retention_days: int
    sensitivity: MetricSensitivity


@dataclass(frozen=True, slots=True)
class RecordMetricCommand:
    project_id: UUID
    name: str
    value: float
    dimensions: tuple[tuple[str, str], ...]
    source_reference: str
    source_feedback_event_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class VariantDraft:
    variant_key: str
    configuration_reference: str


@dataclass(frozen=True, slots=True)
class CreateExperimentCommand:
    project_id: UUID
    experiment_key: str
    protocol_version: str
    hypothesis_code: str
    primary_metric_name: str
    sample_scope: str
    starts_at: datetime
    ends_at: datetime
    stop_condition_codes: tuple[str, ...]
    variants: tuple[VariantDraft, ...]


@dataclass(frozen=True, slots=True)
class FinishExperimentCommand:
    project_id: UUID
    experiment_id: UUID
    status: ExperimentStatus
    result_code: str


class FeedbackAccess:
    def __init__(self, projects: ProjectRepository, authorizer: AuthorizationService) -> None:
        self._projects = projects
        self._authorizer = authorizer

    async def authorize(
        self, context: SecurityContext, project_id: UUID, permission: Permission
    ) -> None:
        request = AuthorizationRequest(
            context,
            permission,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        project = await self._projects.get(context.workspace_id, project_id)
        if project is None:
            await self._authorizer.reject(
                request, ScopeViolationError(), reason_code="project_unavailable"
            )
        if permission is Permission.PROJECT_WRITE and project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot change feedback state.")
        await self._authorizer.authorize(request)


class FeedbackService:
    """Own privacy enforcement before any raw or derived feedback is persisted."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        repository: FeedbackRepository,
        access: FeedbackAccess,
        registry: MetricRegistry,
        doctor: SystemDoctor,
        creator_signals: PreferenceSignalIngestPort,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._access = access
        self._registry = registry
        self._doctor = doctor
        self._creator_signals = creator_signals
        self._clock = clock

    async def grant_behavior_consent(
        self,
        context: SecurityContext,
        project_id: UUID,
        policy_version: str = BEHAVIOR_CONSENT_POLICY_VERSION,
    ) -> BehaviorConsent:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        if context.actor_kind is not ActorKind.USER:
            raise PermissionDeniedError
        if _CODE.fullmatch(policy_version) is None:
            raise ValueError("consent policy version is invalid")
        if (
            await self._repository.active_consent(
                context.workspace_id, project_id, context.actor_id
            )
            is not None
        ):
            raise InvalidStateError("Behavior feedback consent is already active.")
        now = self._clock.now()
        consent = BehaviorConsent(
            uuid4(),
            context.workspace_id,
            project_id,
            context.actor_id,
            policy_version,
            ConsentStatus.ACTIVE,
            now,
        )
        return await self._repository.add_consent(
            consent,
            _event(
                context,
                project_id,
                consent.id,
                "feedback.behavior-consent-granted",
                now,
                {"policy_version": policy_version},
            ),
        )

    async def withdraw_behavior_consent(
        self, context: SecurityContext, project_id: UUID
    ) -> WithdrawalResult:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        if context.actor_kind is not ActorKind.USER:
            raise PermissionDeniedError
        consent = await self._repository.active_consent(
            context.workspace_id, project_id, context.actor_id
        )
        if consent is None:
            raise InvalidStateError("Behavior feedback consent is not active.")
        now = self._clock.now()
        return await self._repository.withdraw_consent(
            context.workspace_id,
            project_id,
            context.actor_id,
            withdrawn_at=now,
            event=_event(
                context,
                project_id,
                consent.id,
                "feedback.behavior-consent-withdrawn",
                now,
                {"policy_version": consent.policy_version, "recompute_required": True},
            ),
        )

    async def get_behavior_consent(
        self, context: SecurityContext, project_id: UUID
    ) -> BehaviorConsent | None:
        """Return the current actor's active consent without exposing another actor's state."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        if context.actor_kind is not ActorKind.USER:
            raise PermissionDeniedError
        return await self._repository.active_consent(
            context.workspace_id, project_id, context.actor_id
        )

    async def capture(
        self, context: SecurityContext, command: CaptureFeedbackCommand
    ) -> FeedbackEvent:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        _validate_feedback(command)
        consent: BehaviorConsent | None = None
        if command.source is FeedbackSource.BEHAVIOR_CONSENTED:
            consent = await self._repository.active_consent(
                context.workspace_id, command.project_id, context.actor_id
            )
            if (
                consent is None
                or command.consent_policy_version is None
                or consent.policy_version != command.consent_policy_version
            ):
                raise InvalidStateError("Behavior feedback requires active matching consent.")
        event_id = uuid4()
        creator_signal_id = uuid4() if command.creator_profile_id is not None else None
        creator_signal_reference = (
            None if creator_signal_id is None else f"creative-record://creator/{creator_signal_id}"
        )
        now = self._clock.now()
        item = FeedbackEvent(
            event_id,
            context.workspace_id,
            command.project_id,
            context.actor_id,
            command.source,
            command.schema_version,
            command.signal_code,
            command.numeric_value,
            command.source_reference,
            None if consent is None else consent.id,
            FeedbackStatus.ACTIVE,
            now,
            creator_signal_reference,
        )
        stored = await self._repository.add_feedback(
            item,
            _event(context, command.project_id, item.id, "feedback.captured", now),
        )
        if command.creator_profile_id is not None:
            signal = PreferenceSignal(
                id=cast("UUID", creator_signal_id),
                logical_id=uuid4(),
                record_version=1,
                workspace_id=context.workspace_id,
                project_id=command.project_id,
                aggregate_id=command.creator_profile_id,
                status=CreativeRecordStatus.PROPOSAL,
                current=False,
                references=(),
                source_reference=item.reference,
                sequence=None,
                created_by=context.actor_id,
                created_at=now,
                causation_id=item.id,
                source_event_id=item.id,
            )
            result = await self._creator_signals.ingest(context, signal)
            if result.status is not ExtensionStatus.PROPOSED:
                raise InvalidStateError("Creator preference signal ingestion is unavailable.")
        return stored

    async def install_default_metrics(
        self, context: SecurityContext, project_id: UUID
    ) -> tuple[MetricDefinition, ...]:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        definitions = default_metric_definitions(
            context.workspace_id, project_id, context.actor_id, self._clock.now()
        )
        for definition in definitions:
            self._registry.register(definition)
            await self._repository.add_metric_definition(definition)
        return definitions

    async def register_metric(
        self, context: SecurityContext, command: RegisterMetricCommand
    ) -> MetricDefinition:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        definition = MetricDefinition(
            uuid4(),
            context.workspace_id,
            command.project_id,
            command.name,
            command.version,
            command.unit,
            command.dimensions,
            command.retention_days,
            command.sensitivity,
            context.actor_id,
            self._clock.now(),
        )
        self._registry.register(definition)
        return await self._repository.add_metric_definition(definition)

    async def record_metric(
        self, context: SecurityContext, command: RecordMetricCommand
    ) -> MetricPoint:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        definition = self._registry.validate_point(command.name, command.value, command.dimensions)
        if (definition.workspace_id, definition.project_id) != (
            context.workspace_id,
            command.project_id,
        ) or _REFERENCE.fullmatch(command.source_reference) is None:
            raise ValueError("metric scope or source reference is invalid")
        if command.source_feedback_event_id is not None:
            source = await self._repository.get_feedback(
                context.workspace_id, command.project_id, command.source_feedback_event_id
            )
            if source is None or source.status is not FeedbackStatus.ACTIVE:
                raise InvalidStateError("Metric source feedback is unavailable.")
        now = self._clock.now()
        point = MetricPoint(
            uuid4(),
            context.workspace_id,
            command.project_id,
            definition.id,
            definition.name,
            command.value,
            command.dimensions,
            now,
            command.source_reference,
            command.source_feedback_event_id,
        )
        return await self._repository.add_metric_point(
            point, _event(context, command.project_id, point.id, "feedback.metric-recorded", now)
        )

    async def diagnose(
        self, context: SecurityContext, project_id: UUID, point_id: UUID
    ) -> tuple[DiagnosticFinding, ...]:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        point = await self._repository.get_metric_point(context.workspace_id, project_id, point_id)
        if point is None:
            raise ScopeViolationError
        findings = self._doctor.inspect(point, self._clock.now())
        for finding in findings:
            await self._repository.add_diagnostic(
                finding,
                _event(
                    context,
                    project_id,
                    finding.id,
                    "feedback.diagnostic-created",
                    finding.created_at,
                ),
            )
        return findings

    async def get_feedback(
        self, context: SecurityContext, project_id: UUID, event_id: UUID
    ) -> FeedbackEvent:
        """Read one structured feedback event through project scope."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        item = await self._repository.get_feedback(context.workspace_id, project_id, event_id)
        if item is None:
            raise ScopeViolationError
        return item

    async def get_diagnostic(
        self, context: SecurityContext, project_id: UUID, finding_id: UUID
    ) -> DiagnosticFinding:
        """Read one deterministic diagnostic without exposing metric internals."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        item = await self._repository.get_diagnostic(context.workspace_id, project_id, finding_id)
        if item is None:
            raise ScopeViolationError
        return item

    async def get_metric_point(
        self, context: SecurityContext, project_id: UUID, point_id: UUID
    ) -> MetricPoint:
        """Read one bounded metric point without exposing raw behavior payloads."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        item = await self._repository.get_metric_point(context.workspace_id, project_id, point_id)
        if item is None:
            raise ScopeViolationError
        return item

    async def get_experiment(
        self, context: SecurityContext, project_id: UUID, experiment_id: UUID
    ) -> tuple[Experiment, tuple[Variant, ...]]:
        """Read one technical experiment and its immutable variant metadata."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        stored = await self._repository.get_experiment(
            context.workspace_id, project_id, experiment_id
        )
        if stored is None:
            raise ScopeViolationError
        return stored

    async def create_experiment(
        self, context: SecurityContext, command: CreateExperimentCommand
    ) -> tuple[Experiment, tuple[Variant, ...]]:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if (
            command.sample_scope != TECHNICAL_SAMPLE_SCOPE
            or self._registry.get(command.primary_metric_name) is None
            or command.ends_at <= command.starts_at
            or len(command.variants) < _MINIMUM_VARIANTS
            or not command.stop_condition_codes
            or any(
                _CODE.fullmatch(value) is None
                for value in (
                    command.experiment_key,
                    command.protocol_version,
                    command.hypothesis_code,
                    *command.stop_condition_codes,
                )
            )
            or len({item.variant_key for item in command.variants}) != len(command.variants)
            or any(
                _CODE.fullmatch(item.variant_key) is None
                or _REFERENCE.fullmatch(item.configuration_reference) is None
                for item in command.variants
            )
        ):
            raise ValueError("experiment protocol is invalid or not technical smoke data")
        now = self._clock.now()
        experiment = Experiment(
            uuid4(),
            context.workspace_id,
            command.project_id,
            command.experiment_key,
            command.protocol_version,
            command.hypothesis_code,
            command.primary_metric_name,
            command.sample_scope,
            command.starts_at,
            command.ends_at,
            command.stop_condition_codes,
            ExperimentStatus.PLANNED,
            context.actor_id,
            now,
        )
        variants = tuple(
            Variant(uuid4(), experiment.id, item.variant_key, item.configuration_reference)
            for item in command.variants
        )
        return await self._repository.add_experiment(
            experiment,
            variants,
            _event(context, command.project_id, experiment.id, "feedback.experiment-created", now),
        )

    async def add_experiment_sample(
        self,
        context: SecurityContext,
        project_id: UUID,
        experiment_id: UUID,
        variant_id: UUID,
        metric_point_id: UUID,
    ) -> ExperimentSample:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        experiment = await self._repository.get_experiment(
            context.workspace_id, project_id, experiment_id
        )
        point = await self._repository.get_metric_point(
            context.workspace_id, project_id, metric_point_id
        )
        if (
            experiment is None
            or point is None
            or not point.included
            or variant_id not in {variant.id for variant in experiment[1]}
            or experiment[0].primary_metric_name != point.metric_name
        ):
            raise InvalidStateError("Experiment sample inputs are unavailable or incompatible.")
        now = self._clock.now()
        sample = ExperimentSample(
            uuid4(),
            context.workspace_id,
            project_id,
            experiment_id,
            variant_id,
            metric_point_id,
            point.source_feedback_event_id,
            now,
        )
        return await self._repository.add_sample(
            sample, _event(context, project_id, sample.id, "feedback.experiment-sampled", now)
        )

    async def start_experiment(
        self, context: SecurityContext, project_id: UUID, experiment_id: UUID
    ) -> Experiment:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        stored = await self._repository.get_experiment(
            context.workspace_id, project_id, experiment_id
        )
        if stored is None:
            raise ScopeViolationError
        experiment = stored[0]
        if experiment.status is not ExperimentStatus.PLANNED:
            raise InvalidStateError("Only a planned experiment can start.")
        running = replace(experiment, status=ExperimentStatus.RUNNING)
        return await self._repository.transition_experiment(
            running,
            ExperimentStatus.PLANNED,
            _event(
                context,
                project_id,
                experiment.id,
                "feedback.experiment-started",
                self._clock.now(),
            ),
        )

    async def finish_experiment(
        self, context: SecurityContext, command: FinishExperimentCommand
    ) -> Experiment:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if command.status not in {ExperimentStatus.COMPLETED, ExperimentStatus.STOPPED} or (
            _CODE.fullmatch(command.result_code) is None
        ):
            raise ValueError("experiment result metadata is invalid")
        stored = await self._repository.get_experiment(
            context.workspace_id, command.project_id, command.experiment_id
        )
        if stored is None:
            raise ScopeViolationError
        experiment = stored[0]
        if experiment.status is not ExperimentStatus.RUNNING:
            raise InvalidStateError("Only a running experiment can finish.")
        finished = replace(experiment, status=command.status, result_code=command.result_code)
        return await self._repository.transition_experiment(
            finished,
            ExperimentStatus.RUNNING,
            _event(
                context,
                command.project_id,
                experiment.id,
                "feedback.experiment-finished",
                self._clock.now(),
            ),
        )


def _validate_feedback(command: CaptureFeedbackCommand) -> None:
    if (
        _CODE.fullmatch(command.schema_version) is None
        or _CODE.fullmatch(command.signal_code) is None
        or (
            command.source_reference is not None
            and _REFERENCE.fullmatch(command.source_reference) is None
        )
    ):
        raise ValueError("feedback event schema metadata is invalid")
    if command.source is not FeedbackSource.BEHAVIOR_CONSENTED and (
        command.consent_policy_version is not None
    ):
        raise ValueError("only behavior feedback may carry consent metadata")
    if command.creator_profile_id is not None and (
        command.source is FeedbackSource.SYSTEM
        or command.schema_version not in _CREATOR_SIGNAL_SCHEMAS
    ):
        raise ValueError("feedback event is not eligible for Creator signal ingestion")


def _event(  # noqa: PLR0913, PLR0917
    context: SecurityContext,
    project_id: UUID,
    aggregate_id: UUID,
    event_type: str,
    now: datetime,
    extra: dict[str, object] | None = None,
) -> EventEnvelope:
    payload: dict[str, object] = {
        "schema": f"{event_type}.v1",
        "actor_id": str(context.actor_id),
    }
    if extra is not None:
        payload.update(extra)
    return EventEnvelope(
        uuid4(), context.workspace_id, project_id, aggregate_id, event_type, 1, payload, now
    )
