from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from accos.adapters.creative import (
    InMemoryCreativeRepository,
    RepositoryPreferenceSignalIngestPort,
)
from accos.adapters.evolution import InMemoryEvolutionMemory
from accos.adapters.feedback import InMemoryFeedbackRepository
from accos.kernel.errors import (
    ConcurrencyConflictError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.events import EventEnvelope
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.creative.public import (
    CreativeRecordStatus,
    CreativeReference,
    CreativeReferenceKind,
    CreatorProfile,
    ExtensionResult,
    ExtensionStatus,
    PreferenceSignal,
)
from accos.modules.evolution.public import (
    ChangeAction,
    DeterministicAnalyzer,
    DiagnosticObserver,
    DryRunSimulationEnvironment,
    EvolutionAccess,
    EvolutionAuditEntry,
    EvolutionDecision,
    EvolutionService,
    EvolutionState,
    EvolutionStateMachine,
    ImmutableSafetyController,
    ImprovementProposal,
    ProposalPlanner,
    ReadOnlyVersionManager,
    SimulationEvidence,
)
from accos.modules.feedback.public import (
    BEHAVIOR_CONSENT_POLICY_VERSION,
    TECHNICAL_SAMPLE_SCOPE,
    ArtifactKind,
    CaptureFeedbackCommand,
    CreateExperimentCommand,
    DiagnosticFinding,
    DiagnosticSeverity,
    ExperimentStatus,
    FeedbackAccess,
    FeedbackEvent,
    FeedbackService,
    FeedbackSource,
    FeedbackStatus,
    FinishExperimentCommand,
    MetricDimension,
    MetricPoint,
    MetricRegistry,
    MetricSensitivity,
    RecordMetricCommand,
    RegisterMetricCommand,
    SystemDoctor,
    TombstoneAction,
    VariantDraft,
    default_diagnostic_rules,
    default_metric_definitions,
)
from accos.modules.identity.public import AuthorizationService, Role, permissions_for
from accos.modules.projects.public import Project, ProjectRepository, ProjectSettings, ProjectStatus

if TYPE_CHECKING:
    from accos.modules.identity.ports import AuditEvent

NOW = datetime(2026, 9, 6, 14, tzinfo=UTC)
ACTOR_ID = UUID("f0000000-0000-4000-8000-000000000001")
APPROVER_ID = UUID("f0000000-0000-4000-8000-000000000002")
WORKSPACE_ID = UUID("f0000000-0000-4000-8000-000000000003")
PROJECT_ID = UUID("f0000000-0000-4000-8000-000000000004")


@dataclass(slots=True)
class Clock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value


class Audit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class Projects:
    def __init__(self) -> None:
        self.items = {
            (WORKSPACE_ID, PROJECT_ID): Project(
                PROJECT_ID,
                WORKSPACE_ID,
                "fixture-project",
                ProjectStatus.ACTIVE,
                ProjectSettings(),
                ACTOR_ID,
                NOW,
                NOW,
            )
        }

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        return self.items.get((workspace_id, project_id))


def context(
    *,
    actor_id: UUID = ACTOR_ID,
    role: Role = Role.OWNER,
    actor_kind: ActorKind = ActorKind.USER,
    workspace_id: UUID = WORKSPACE_ID,
) -> SecurityContext:
    correlation = uuid4()
    return SecurityContext(
        actor_id,
        actor_kind,
        workspace_id,
        permissions_for(role),
        "fixture-policy-v1",
        CorrelationIds(str(correlation), str(correlation)),
    )


def event(aggregate_id: UUID, event_type: str) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        WORKSPACE_ID,
        PROJECT_ID,
        aggregate_id,
        event_type,
        1,
        {"schema": f"{event_type}.v1"},
        NOW,
    )


def feedback_services() -> tuple[
    FeedbackService,
    InMemoryFeedbackRepository,
    InMemoryCreativeRepository,
    UUID,
    Projects,
]:
    projects = Projects()
    audit = Audit()
    creative = InMemoryCreativeRepository()
    profile_id = uuid4()
    creative.containers[profile_id] = CreatorProfile(
        profile_id,
        WORKSPACE_ID,
        PROJECT_ID,
        "fixture-creator",
        (CreativeReference(CreativeReferenceKind.CREATOR, ACTOR_ID),),
        ACTOR_ID,
        NOW,
        NOW,
    )
    repository = InMemoryFeedbackRepository()
    service = FeedbackService(
        repository,
        FeedbackAccess(cast("ProjectRepository", projects), AuthorizationService(audit, Clock())),
        MetricRegistry(),
        SystemDoctor(default_diagnostic_rules()),
        RepositoryPreferenceSignalIngestPort(creative, Clock()),
        Clock(),
    )
    return service, repository, creative, profile_id, projects


def evolution_service(
    projects: Projects | None = None,
) -> tuple[EvolutionService, InMemoryEvolutionMemory]:
    selected_projects = Projects() if projects is None else projects
    memory = InMemoryEvolutionMemory()
    service = EvolutionService(
        memory,
        EvolutionAccess(
            cast("ProjectRepository", selected_projects), AuthorizationService(Audit(), Clock())
        ),
        DiagnosticObserver(),
        DeterministicAnalyzer(),
        ProposalPlanner(),
        DryRunSimulationEnvironment(),
        ReadOnlyVersionManager(),
        ImmutableSafetyController(),
        Clock(),
    )
    return service, memory


def diagnostic(*, workspace_id: UUID = WORKSPACE_ID) -> DiagnosticFinding:
    return DiagnosticFinding(
        uuid4(),
        workspace_id,
        PROJECT_ID,
        uuid4(),
        "runtime-unhealthy",
        "1.0.0",
        "runtime_component_unhealthy",
        DiagnosticSeverity.CRITICAL,
        1.0,
        1.0,
        NOW,
    )


def test_metric_registry_has_bounded_default_technical_coverage() -> None:
    definitions = default_metric_definitions(WORKSPACE_ID, PROJECT_ID, ACTOR_ID, NOW)
    assert {item.name for item in definitions} == {
        "agent.outcome",
        "agent.latency_ms",
        "agent.budget_utilization",
        "memory.recall_status",
        "workflow.outcome",
        "runtime.health",
    }
    assert all(item.retention_days == 30 for item in definitions)
    registry = MetricRegistry()
    for item in definitions:
        registry.register(item)
        registry.register(item)
    assert registry.all() == tuple(sorted(definitions, key=lambda item: item.name))
    runtime = registry.validate_point(
        "runtime.health", 1.0, (("component", "worker"), ("status", "unhealthy"))
    )
    assert registry.get("runtime.health") is runtime

    with pytest.raises(ValueError, match="immutable"):
        registry.register(replace(runtime, retention_days=31))
    with pytest.raises(ValueError, match="not registered"):
        registry.validate_point("missing.metric", 1.0, ())
    with pytest.raises(ValueError, match="finite"):
        registry.validate_point("agent.latency_ms", float("inf"), ())
    with pytest.raises(ValueError, match="unique"):
        registry.validate_point(
            "runtime.health",
            1.0,
            (("component", "worker"), ("component", "api"), ("status", "healthy")),
        )
    with pytest.raises(ValueError, match="finite vocabulary"):
        registry.validate_point(
            "runtime.health", 1.0, (("component", "fixture-id"), ("status", "healthy"))
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": "Bad Name"}, "metadata"),
        ({"unit": "Bad Unit"}, "metadata"),
        ({"version": 0}, "metadata"),
        ({"retention_days": 0}, "metadata"),
        ({"retention_days": 401}, "metadata"),
        (
            {
                "dimensions": tuple(
                    MetricDimension(f"key-{index}", ("value",)) for index in range(5)
                )
            },
            "metadata",
        ),
        (
            {
                "dimensions": (
                    MetricDimension("status", ("ok",)),
                    MetricDimension("status", ("failed",)),
                )
            },
            "unique",
        ),
        ({"dimensions": (MetricDimension("user_id", ("value",)),)}, "bounded"),
        ({"dimensions": (MetricDimension("status", ()),)}, "bounded"),
        (
            {"dimensions": (MetricDimension("status", tuple(f"v-{i}" for i in range(33))),)},
            "bounded",
        ),
        ({"dimensions": (MetricDimension("status", ("ok", "ok")),)}, "bounded"),
        ({"dimensions": (MetricDimension("status", ("Bad Value",)),)}, "bounded"),
    ],
)
def test_metric_registry_rejects_unbounded_or_invalid_definitions(
    changes: dict[str, object], message: str
) -> None:
    base = default_metric_definitions(WORKSPACE_ID, PROJECT_ID, ACTOR_ID, NOW)[0]
    with pytest.raises(ValueError, match=message):
        MetricRegistry().register(replace(base, **changes))  # type: ignore[arg-type]


def test_feedback_consent_creator_signal_metric_experiment_and_withdrawal(  # noqa: PLR0915
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        service, repository, creative, profile_id, _projects = feedback_services()
        ctx = context()
        behavior = CaptureFeedbackCommand(
            PROJECT_ID,
            FeedbackSource.BEHAVIOR_CONSENTED,
            "creator-preference.v1",
            "fixture-choice",
            1.0,
            "technical-event://fixture",
            BEHAVIOR_CONSENT_POLICY_VERSION,
            profile_id,
        )
        with pytest.raises(InvalidStateError, match="active matching consent"):
            await service.capture(ctx, behavior)

        consent = await service.grant_behavior_consent(ctx, PROJECT_ID)
        assert consent.policy_version == BEHAVIOR_CONSENT_POLICY_VERSION
        assert await service.get_behavior_consent(ctx, PROJECT_ID) == consent
        with pytest.raises(InvalidStateError, match="already active"):
            await service.grant_behavior_consent(ctx, PROJECT_ID)
        with pytest.raises(PermissionDeniedError):
            await service.get_behavior_consent(context(actor_kind=ActorKind.SERVICE), PROJECT_ID)
        with pytest.raises(PermissionDeniedError):
            await service.withdraw_behavior_consent(
                context(actor_kind=ActorKind.SERVICE), PROJECT_ID
            )
        captured = await service.capture(ctx, behavior)
        assert captured.source is FeedbackSource.BEHAVIOR_CONSENTED
        assert await service.get_feedback(ctx, PROJECT_ID, captured.id) == captured
        with pytest.raises(ScopeViolationError):
            await service.get_feedback(ctx, PROJECT_ID, uuid4())
        assert captured.creator_signal_reference is not None
        creator_signal = next(iter(creative.records.values()))
        assert isinstance(creator_signal, PreferenceSignal)
        assert creator_signal.source_event_id == captured.id
        assert creator_signal.status is CreativeRecordStatus.PROPOSAL

        defaults = await service.install_default_metrics(ctx, PROJECT_ID)
        assert len(defaults) == 6
        point = await service.record_metric(
            ctx,
            RecordMetricCommand(
                PROJECT_ID,
                "runtime.health",
                1.0,
                (("component", "worker"), ("status", "unhealthy")),
                "runtime-check://worker",
                captured.id,
            ),
        )
        findings = await service.diagnose(ctx, PROJECT_ID, point.id)
        assert len(findings) == 1
        assert findings[0].finding_code == "runtime_component_unhealthy"
        assert await service.get_metric_point(ctx, PROJECT_ID, point.id) == point
        with pytest.raises(ScopeViolationError):
            await service.get_metric_point(ctx, PROJECT_ID, uuid4())
        assert await service.diagnose(ctx, PROJECT_ID, point.id) == findings
        assert await service.get_diagnostic(ctx, PROJECT_ID, findings[0].id) == findings[0]
        with pytest.raises(ScopeViolationError):
            await service.get_diagnostic(ctx, PROJECT_ID, uuid4())

        experiment, variants = await service.create_experiment(
            ctx,
            CreateExperimentCommand(
                PROJECT_ID,
                "fixture-experiment",
                "protocol-v1",
                "worker-recovery",
                "runtime.health",
                TECHNICAL_SAMPLE_SCOPE,
                NOW,
                NOW + timedelta(hours=1),
                ("stop-on-error",),
                (
                    VariantDraft("control", "configuration://fixture/control"),
                    VariantDraft("candidate", "configuration://fixture/candidate"),
                ),
            ),
        )
        assert await service.get_experiment(ctx, PROJECT_ID, experiment.id) == (
            experiment,
            tuple(sorted(variants, key=lambda item: item.variant_key)),
        )
        with pytest.raises(ScopeViolationError):
            await service.get_experiment(ctx, PROJECT_ID, uuid4())
        sample = await service.add_experiment_sample(
            ctx, PROJECT_ID, experiment.id, variants[0].id, point.id
        )
        running = await service.start_experiment(ctx, PROJECT_ID, experiment.id)
        finished = await service.finish_experiment(
            ctx,
            FinishExperimentCommand(
                PROJECT_ID, experiment.id, ExperimentStatus.COMPLETED, "no-regression"
            ),
        )
        assert running.status is ExperimentStatus.RUNNING
        assert finished.result_code == "no-regression"
        with pytest.raises(InvalidStateError, match="planned"):
            await service.start_experiment(ctx, PROJECT_ID, experiment.id)
        result = await service.withdraw_behavior_consent(ctx, PROJECT_ID)
        assert result.consent.status.value == "withdrawn"
        assert await service.get_behavior_consent(ctx, PROJECT_ID) is None
        assert result.anonymized_event_ids == (captured.id,)
        assert {item.artifact_kind for item in result.tombstones} == {
            ArtifactKind.METRIC_POINT,
            ArtifactKind.EXPERIMENT_SAMPLE,
            ArtifactKind.CREATOR_SIGNAL,
        }
        assert {item.action for item in result.tombstones} == {
            TombstoneAction.RECOMPUTE,
            TombstoneAction.EXCLUDE,
        }
        redacted = repository.feedback[captured.id]
        assert redacted.status is FeedbackStatus.ANONYMIZED
        assert redacted.actor_id is None
        assert redacted.numeric_value is None
        assert redacted.source_reference is None
        assert redacted.consent_id is None
        assert redacted.creator_signal_reference is None
        assert redacted.signal_code == "withdrawn"
        assert not repository.points[point.id].included
        assert not repository.samples[sample.id].included
        withdrawal_event = repository.events[-1]
        assert withdrawal_event.payload == {
            "schema": "feedback.behavior-consent-withdrawn.v1",
            "actor_id": str(ACTOR_ID),
            "policy_version": BEHAVIOR_CONSENT_POLICY_VERSION,
            "recompute_required": True,
        }
        with pytest.raises(InvalidStateError, match="not active"):
            await service.withdraw_behavior_consent(ctx, PROJECT_ID)
        with pytest.raises(InvalidStateError, match="active matching consent"):
            await service.capture(ctx, behavior)
        assert (await service.grant_behavior_consent(ctx, PROJECT_ID)).status.value == "active"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "command",
    [
        CaptureFeedbackCommand(PROJECT_ID, FeedbackSource.USER, "Bad schema", "valid"),
        CaptureFeedbackCommand(PROJECT_ID, FeedbackSource.USER, "schema-v1", "Bad signal"),
        CaptureFeedbackCommand(
            PROJECT_ID, FeedbackSource.USER, "schema-v1", "valid", source_reference="not-uri"
        ),
        CaptureFeedbackCommand(
            PROJECT_ID,
            FeedbackSource.USER,
            "schema-v1",
            "valid",
            consent_policy_version=BEHAVIOR_CONSENT_POLICY_VERSION,
        ),
        CaptureFeedbackCommand(
            PROJECT_ID,
            FeedbackSource.SYSTEM,
            "creator-preference.v1",
            "valid",
            creator_profile_id=uuid4(),
        ),
        CaptureFeedbackCommand(
            PROJECT_ID,
            FeedbackSource.USER,
            "schema-v1",
            "valid",
            creator_profile_id=uuid4(),
        ),
    ],
)
def test_feedback_rejects_invalid_or_ineligible_event_metadata(
    command: CaptureFeedbackCommand,
) -> None:
    service = feedback_services()[0]
    with pytest.raises(ValueError):
        asyncio.run(service.capture(context(), command))


def test_feedback_authorization_scope_sources_and_failure_guards() -> None:
    async def scenario() -> None:
        service, repository, _creative, profile_id, projects = feedback_services()
        with pytest.raises(PermissionDeniedError):
            await service.grant_behavior_consent(context(actor_kind=ActorKind.SERVICE), PROJECT_ID)
        with pytest.raises(ValueError, match="policy"):
            await service.grant_behavior_consent(context(), PROJECT_ID, "Bad policy")
        with pytest.raises(PermissionDeniedError):
            await service.grant_behavior_consent(context(role=Role.VIEWER), PROJECT_ID)
        with pytest.raises(ScopeViolationError):
            await service.install_default_metrics(context(), uuid4())
        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ARCHIVED
        )
        with pytest.raises(InvalidStateError, match="Archived"):
            await service.install_default_metrics(context(), PROJECT_ID)
        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ACTIVE
        )

        for source in (
            FeedbackSource.USER,
            FeedbackSource.SYSTEM,
            FeedbackSource.CREATIVE_RESULT,
        ):
            item = await service.capture(
                context(), CaptureFeedbackCommand(PROJECT_ID, source, "schema-v1", "fixture")
            )
            assert item.source is source
        defaults = await service.install_default_metrics(context(), PROJECT_ID)
        assert defaults
        with pytest.raises(ValueError, match="scope or source"):
            await service.record_metric(
                context(),
                RecordMetricCommand(PROJECT_ID, "agent.latency_ms", 1.0, (), "bad"),
            )
        with pytest.raises(InvalidStateError, match="source feedback"):
            await service.record_metric(
                context(),
                RecordMetricCommand(
                    PROJECT_ID,
                    "agent.latency_ms",
                    1.0,
                    (),
                    "technical-event://fixture",
                    uuid4(),
                ),
            )
        point = await service.record_metric(
            context(),
            RecordMetricCommand(
                PROJECT_ID, "agent.latency_ms", 1.0, (), "technical-event://fixture"
            ),
        )
        assert await service.diagnose(context(), PROJECT_ID, point.id) == ()
        with pytest.raises(ScopeViolationError):
            await service.diagnose(context(), PROJECT_ID, uuid4())

        custom = await service.register_metric(
            context(),
            RegisterMetricCommand(
                PROJECT_ID,
                "fixture.metric",
                1,
                "count",
                (),
                7,
                MetricSensitivity.PUBLIC,
            ),
        )
        assert repository.definitions[custom.id] == custom

        class UnavailableSink:
            async def ingest(
                self, _context: SecurityContext, _signal: PreferenceSignal
            ) -> ExtensionResult:
                return ExtensionResult(ExtensionStatus.NOT_CONFIGURED)

        unavailable = FeedbackService(
            repository,
            service._access,  # noqa: SLF001 - negative adapter wiring test.
            service._registry,  # noqa: SLF001
            SystemDoctor(default_diagnostic_rules()),
            UnavailableSink(),
            Clock(),
        )
        with pytest.raises(InvalidStateError, match="ingestion is unavailable"):
            await unavailable.capture(
                context(),
                CaptureFeedbackCommand(
                    PROJECT_ID,
                    FeedbackSource.USER,
                    "creator-preference.v1",
                    "fixture",
                    creator_profile_id=profile_id,
                ),
            )

    asyncio.run(scenario())


def experiment_command(**changes: object) -> CreateExperimentCommand:
    base: dict[str, object] = {
        "project_id": PROJECT_ID,
        "experiment_key": "fixture-experiment",
        "protocol_version": "protocol-v1",
        "hypothesis_code": "worker-recovery",
        "primary_metric_name": "runtime.health",
        "sample_scope": TECHNICAL_SAMPLE_SCOPE,
        "starts_at": NOW,
        "ends_at": NOW + timedelta(hours=1),
        "stop_condition_codes": ("stop-on-error",),
        "variants": (
            VariantDraft("control", "configuration://fixture/control"),
            VariantDraft("candidate", "configuration://fixture/candidate"),
        ),
    }
    base.update(changes)
    return CreateExperimentCommand(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"sample_scope": "author-content"},
        {"primary_metric_name": "missing.metric"},
        {"ends_at": NOW},
        {"variants": (VariantDraft("one", "configuration://fixture/one"),)},
        {"stop_condition_codes": ()},
        {"experiment_key": "Bad Key"},
        {
            "variants": (
                VariantDraft("same", "configuration://fixture/one"),
                VariantDraft("same", "configuration://fixture/two"),
            )
        },
        {
            "variants": (
                VariantDraft("Bad Key", "configuration://fixture/one"),
                VariantDraft("two", "configuration://fixture/two"),
            )
        },
        {
            "variants": (
                VariantDraft("one", "not-uri"),
                VariantDraft("two", "configuration://fixture/two"),
            )
        },
    ],
)
def test_experiments_are_versioned_technical_smoke_only(changes: dict[str, object]) -> None:
    async def scenario() -> None:
        service = feedback_services()[0]
        await service.install_default_metrics(context(), PROJECT_ID)
        with pytest.raises(ValueError, match="technical smoke"):
            await service.create_experiment(context(), experiment_command(**changes))

    asyncio.run(scenario())


def test_experiment_samples_fail_closed_for_incompatible_inputs() -> None:
    async def scenario() -> None:
        service = feedback_services()[0]
        await service.install_default_metrics(context(), PROJECT_ID)
        experiment, variants = await service.create_experiment(context(), experiment_command())
        with pytest.raises(ScopeViolationError):
            await service.start_experiment(context(), PROJECT_ID, uuid4())
        with pytest.raises(ScopeViolationError):
            await service.finish_experiment(
                context(),
                FinishExperimentCommand(PROJECT_ID, uuid4(), ExperimentStatus.COMPLETED, "result"),
            )
        with pytest.raises(ValueError, match="result metadata"):
            await service.finish_experiment(
                context(),
                FinishExperimentCommand(
                    PROJECT_ID, experiment.id, ExperimentStatus.PLANNED, "result"
                ),
            )
        with pytest.raises(ValueError, match="result metadata"):
            await service.finish_experiment(
                context(),
                FinishExperimentCommand(
                    PROJECT_ID, experiment.id, ExperimentStatus.COMPLETED, "Bad Result"
                ),
            )
        with pytest.raises(InvalidStateError, match="running"):
            await service.finish_experiment(
                context(),
                FinishExperimentCommand(
                    PROJECT_ID, experiment.id, ExperimentStatus.COMPLETED, "result"
                ),
            )
        latency = await service.record_metric(
            context(),
            RecordMetricCommand(
                PROJECT_ID, "agent.latency_ms", 1.0, (), "technical-event://latency"
            ),
        )
        for experiment_id, variant_id, point_id in (
            (uuid4(), variants[0].id, latency.id),
            (experiment.id, uuid4(), latency.id),
            (experiment.id, variants[0].id, uuid4()),
            (experiment.id, variants[0].id, latency.id),
        ):
            with pytest.raises(InvalidStateError, match="sample inputs"):
                await service.add_experiment_sample(
                    context(), PROJECT_ID, experiment_id, variant_id, point_id
                )

    asyncio.run(scenario())


def test_creator_signal_adapter_rejects_cross_scope_and_wrong_actor() -> None:
    async def scenario() -> None:
        _service, _feedback, creative, profile_id, _projects = feedback_services()
        adapter = RepositoryPreferenceSignalIngestPort(creative, Clock())
        signal = PreferenceSignal(
            uuid4(),
            uuid4(),
            1,
            WORKSPACE_ID,
            PROJECT_ID,
            profile_id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            "feedback-event://fixture",
            None,
            ACTOR_ID,
            NOW,
            uuid4(),
            uuid4(),
        )
        with pytest.raises(ValueError, match="not authorized"):
            await adapter.ingest(context(actor_id=APPROVER_ID), signal)
        with pytest.raises(ValueError, match="not authorized"):
            await adapter.ingest(context(workspace_id=uuid4()), signal)
        with pytest.raises(ValueError, match="not authorized"):
            await adapter.ingest(context(), replace(signal, aggregate_id=uuid4()))

    asyncio.run(scenario())


def test_system_doctor_is_deterministic_and_read_only() -> None:
    definitions = default_metric_definitions(WORKSPACE_ID, PROJECT_ID, ACTOR_ID, NOW)
    runtime = next(item for item in definitions if item.name == "runtime.health")
    point = MetricPoint(
        uuid4(),
        WORKSPACE_ID,
        PROJECT_ID,
        runtime.id,
        runtime.name,
        1.0,
        (("component", "api"), ("status", "unhealthy")),
        NOW,
        "runtime-check://api",
    )
    doctor = SystemDoctor(default_diagnostic_rules())
    assert doctor.inspect(point, NOW) == doctor.inspect(point, NOW)
    assert doctor.inspect(replace(point, included=False), NOW) == ()
    assert doctor.inspect(replace(point, value=0.0), NOW) == ()
    assert (
        doctor.inspect(
            replace(point, dimensions=(("component", "api"), ("status", "healthy"))), NOW
        )
        == ()
    )
    assert not any(
        hasattr(doctor, name) for name in ("apply", "deploy", "write_config", "run_shell")
    )


def test_evolution_safe_flow_reaches_only_human_approval_and_keeps_config_unchanged() -> None:
    async def scenario() -> None:
        service, memory = evolution_service()
        mutable_configuration = {"route": "fixture-original"}
        observed = await service.observe(context(), PROJECT_ID, diagnostic())
        assert observed.reference == f"improvement-proposal://{observed.id}"
        assert await service.get(context(), PROJECT_ID, observed.id) == observed
        with pytest.raises(ScopeViolationError):
            await service.get(context(), PROJECT_ID, uuid4())
        proposed = await service.propose(
            context(),
            PROJECT_ID,
            observed.id,
            observed.version,
            ChangeAction.SUGGEST_CONFIGURATION,
            "configuration-proposal://fixture/change",
            "rollback://fixture/original",
        )
        simulated = await service.simulate(context(), PROJECT_ID, proposed.id, proposed.version)
        evaluated = await service.evaluate(context(), PROJECT_ID, simulated.id, simulated.version)
        awaiting = await service.request_approval(
            context(), PROJECT_ID, evaluated.id, evaluated.version
        )
        assert awaiting.state is EvolutionState.AWAITING_APPROVAL
        assert mutable_configuration == {"route": "fixture-original"}
        with pytest.raises(PermissionDeniedError):
            await service.decide(
                context(),
                PROJECT_ID,
                awaiting.id,
                awaiting.version,
                EvolutionDecision.APPROVE,
            )
        approved = await service.decide(
            context(actor_id=APPROVER_ID),
            PROJECT_ID,
            awaiting.id,
            awaiting.version,
            EvolutionDecision.APPROVE,
        )
        assert approved.state is EvolutionState.APPROVED
        assert approved.approved_by == APPROVER_ID
        assert approved.rollback_reference == "rollback://fixture/original"
        assert len(memory.audit) == 6
        assert all(item.algorithm_versions for item in memory.audit[1:])
        assert not any(
            hasattr(service, name) for name in ("deploy", "commit", "write_file", "run_shell")
        )

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("action", "rule"),
    [
        (ChangeAction.CHANGE_OWNERSHIP, "immutable-no-ownership-change"),
        (ChangeAction.DISABLE_SAFETY, "immutable-no-safety-disable"),
        (ChangeAction.ELEVATE_PERMISSION, "immutable-no-permission-escalation"),
        (ChangeAction.BYPASS_APPROVAL, "immutable-no-approval-bypass"),
        (ChangeAction.AUTO_COMMIT_CODE, "immutable-no-auto-commit"),
        (ChangeAction.AUTO_DEPLOY, "immutable-no-auto-deploy"),
        (ChangeAction.UNMIGRATED_SCHEMA, "immutable-no-unmigrated-schema"),
    ],
)
def test_immutable_safety_rules_reject_and_audit(action: ChangeAction, rule: str) -> None:
    async def scenario() -> None:
        service, memory = evolution_service()
        observed = await service.observe(context(), PROJECT_ID, diagnostic())
        rejected = await service.propose(
            context(),
            PROJECT_ID,
            observed.id,
            observed.version,
            action,
            "change://fixture/unsafe",
            "rollback://fixture/original",
        )
        assert rejected.state is EvolutionState.REJECTED
        assert rejected.safety_rule_code == rule
        assert memory.audit[-1].reason_code == rule
        with pytest.raises(InvalidStateError):
            await service.simulate(context(), PROJECT_ID, rejected.id, rejected.version)

    asyncio.run(scenario())


def test_evolution_state_machine_forbids_shortcuts_and_models_external_attestation() -> None:
    machine = EvolutionStateMachine()
    allowed = (
        (EvolutionState.OBSERVED, EvolutionState.PROPOSED),
        (EvolutionState.PROPOSED, EvolutionState.SIMULATED),
        (EvolutionState.SIMULATED, EvolutionState.EVALUATED),
        (EvolutionState.EVALUATED, EvolutionState.AWAITING_APPROVAL),
        (EvolutionState.AWAITING_APPROVAL, EvolutionState.APPROVED),
        (EvolutionState.APPROVED, EvolutionState.EXTERNALLY_DEPLOYED),
        (EvolutionState.EXTERNALLY_DEPLOYED, EvolutionState.VERIFIED),
        (EvolutionState.EXTERNALLY_DEPLOYED, EvolutionState.ROLLED_BACK),
    )
    for current, target in allowed:
        machine.require(current, target)
    for terminal in (EvolutionState.REJECTED, EvolutionState.VERIFIED, EvolutionState.ROLLED_BACK):
        with pytest.raises(InvalidStateError):
            machine.require(terminal, EvolutionState.PROPOSED)
    with pytest.raises(InvalidStateError, match="not allowed"):
        machine.require(EvolutionState.PROPOSED, EvolutionState.EXTERNALLY_DEPLOYED)


def test_evolution_rejects_scope_invalid_state_concurrency_and_nonhuman_approval() -> None:
    async def scenario() -> None:
        projects = Projects()
        service, memory = evolution_service(projects)
        with pytest.raises(ScopeViolationError):
            await service.observe(context(), uuid4(), diagnostic())
        with pytest.raises(ScopeViolationError):
            await service.observe(context(), PROJECT_ID, diagnostic(workspace_id=uuid4()))
        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ARCHIVED
        )
        with pytest.raises(InvalidStateError, match="Archived"):
            await service.observe(context(), PROJECT_ID, diagnostic())
        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ACTIVE
        )
        with pytest.raises(ScopeViolationError):
            await service.simulate(context(), PROJECT_ID, uuid4(), 1)
        observed = await service.observe(context(), PROJECT_ID, diagnostic())
        for change, rollback in (("bad", "rollback://ok"), ("change://ok", "bad")):
            with pytest.raises(ValueError, match="opaque URIs"):
                await service.propose(
                    context(),
                    PROJECT_ID,
                    observed.id,
                    observed.version,
                    ChangeAction.SUGGEST_PROMPT,
                    change,
                    rollback,
                )
        with pytest.raises(ConcurrencyConflictError):
            await service.propose(
                context(),
                PROJECT_ID,
                observed.id,
                2,
                ChangeAction.SUGGEST_PROMPT,
                "change://fixture/prompt",
                "rollback://fixture/prompt",
            )
        proposed = await service.propose(
            context(),
            PROJECT_ID,
            observed.id,
            observed.version,
            ChangeAction.SUGGEST_PROMPT,
            "change://fixture/prompt",
            "rollback://fixture/prompt",
        )
        incomplete = replace(
            proposed,
            id=uuid4(),
            action=None,
            change_reference=None,
            rollback_reference=None,
        )
        memory.proposals[incomplete.id] = incomplete
        with pytest.raises(InvalidStateError, match="complete plan"):
            await service.simulate(context(), PROJECT_ID, incomplete.id, incomplete.version)
        simulated_without_evidence = replace(
            proposed, id=uuid4(), state=EvolutionState.SIMULATED, version=3
        )
        memory.proposals[simulated_without_evidence.id] = simulated_without_evidence
        with pytest.raises(InvalidStateError, match="Simulation evidence"):
            await service.evaluate(context(), PROJECT_ID, simulated_without_evidence.id, 3)

        simulated = await service.simulate(context(), PROJECT_ID, proposed.id, proposed.version)
        evaluated = await service.evaluate(context(), PROJECT_ID, simulated.id, simulated.version)
        awaiting = await service.request_approval(
            context(), PROJECT_ID, evaluated.id, evaluated.version
        )
        with pytest.raises(PermissionDeniedError):
            await service.decide(
                context(actor_id=APPROVER_ID, actor_kind=ActorKind.SERVICE),
                PROJECT_ID,
                awaiting.id,
                awaiting.version,
                EvolutionDecision.APPROVE,
            )
        rejected = await service.decide(
            context(actor_id=APPROVER_ID),
            PROJECT_ID,
            awaiting.id,
            awaiting.version,
            EvolutionDecision.REJECT,
        )
        assert rejected.state is EvolutionState.REJECTED
        assert rejected.approved_by is None

        analysis = DeterministicAnalyzer()
        assert (
            analysis.evaluate(SimulationEvidence("simulation://fixture", "fixture", "1", "failed"))
            == "simulation-rejected"
        )

    asyncio.run(scenario())


def test_in_memory_repositories_idempotency_scope_and_direct_guards() -> None:
    async def scenario() -> None:
        service, feedback, _creative, _profile, _projects = feedback_services()
        consent = await service.grant_behavior_consent(context(), PROJECT_ID)
        assert await feedback.add_consent(consent, event(consent.id, "duplicate")) == consent
        user_event = await service.capture(
            context(),
            CaptureFeedbackCommand(PROJECT_ID, FeedbackSource.USER, "schema-v1", "fixture"),
        )
        assert (
            await feedback.add_feedback(user_event, event(user_event.id, "duplicate")) == user_event
        )
        assert await feedback.get_feedback(uuid4(), PROJECT_ID, user_event.id) is None
        definitions = await service.install_default_metrics(context(), PROJECT_ID)
        definition = definitions[0]
        assert await feedback.add_metric_definition(definition) == definition
        point = await service.record_metric(
            context(),
            RecordMetricCommand(
                PROJECT_ID,
                definition.name,
                1.0,
                (("status", "success"),),
                "technical-event://fixture",
            ),
        )
        assert await feedback.add_metric_point(point, event(point.id, "duplicate")) == point
        assert await feedback.get_metric_point(uuid4(), PROJECT_ID, point.id) is None
        finding = DiagnosticFinding(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            point.id,
            "fixture",
            "1",
            "fixture",
            DiagnosticSeverity.WARNING,
            1.0,
            1.0,
            NOW,
        )
        assert await feedback.add_diagnostic(finding, event(finding.id, "finding")) == finding
        assert await feedback.add_diagnostic(finding, event(finding.id, "duplicate")) == finding
        experiment, variants = await service.create_experiment(context(), experiment_command())
        duplicate = await feedback.add_experiment(
            experiment, variants, event(experiment.id, "duplicate")
        )
        assert duplicate == (
            experiment,
            tuple(sorted(variants, key=lambda item: item.variant_key)),
        )
        assert await feedback.get_experiment(uuid4(), PROJECT_ID, experiment.id) is None
        runtime = await service.record_metric(
            context(),
            RecordMetricCommand(
                PROJECT_ID,
                "runtime.health",
                1.0,
                (("component", "api"), ("status", "healthy")),
                "technical-event://health",
            ),
        )
        sample = await service.add_experiment_sample(
            context(), PROJECT_ID, experiment.id, variants[0].id, runtime.id
        )
        assert await feedback.add_sample(sample, event(sample.id, "duplicate")) == sample
        with pytest.raises(InvalidStateError):
            await feedback.transition_experiment(
                replace(experiment, status=ExperimentStatus.RUNNING),
                ExperimentStatus.RUNNING,
                event(experiment.id, "invalid-transition"),
            )
        behavior = FeedbackEvent(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            ACTOR_ID,
            FeedbackSource.BEHAVIOR_CONSENTED,
            "schema-v1",
            "fixture-behavior",
            None,
            None,
            consent.id,
            FeedbackStatus.ACTIVE,
            NOW,
        )
        await feedback.add_feedback(behavior, event(behavior.id, "behavior"))
        direct_withdrawal = await feedback.withdraw_consent(
            WORKSPACE_ID,
            PROJECT_ID,
            ACTOR_ID,
            withdrawn_at=NOW,
            event=event(consent.id, "withdraw"),
        )
        assert direct_withdrawal.anonymized_event_ids == (behavior.id,)
        assert direct_withdrawal.tombstones == ()
        empty = InMemoryFeedbackRepository()
        with pytest.raises(InvalidStateError):
            await empty.withdraw_consent(
                WORKSPACE_ID,
                PROJECT_ID,
                ACTOR_ID,
                withdrawn_at=NOW,
                event=event(uuid4(), "withdraw"),
            )

        evolution = InMemoryEvolutionMemory()
        proposal = ImprovementProposal(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            (uuid4(),),
            ("finding://fixture",),
            ("observer@1",),
            EvolutionState.OBSERVED,
            ACTOR_ID,
            NOW,
            NOW,
        )
        audit = EvolutionAuditEntry(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            proposal.id,
            None,
            EvolutionState.OBSERVED,
            ACTOR_ID,
            proposal.algorithm_versions,
            proposal.input_references,
            None,
            "observed",
            NOW,
        )
        assert await evolution.add(proposal, audit, event(proposal.id, "observed")) == proposal
        assert await evolution.add(proposal, audit, event(proposal.id, "duplicate")) == proposal
        assert await evolution.get(uuid4(), PROJECT_ID, proposal.id) is None
        with pytest.raises(ScopeViolationError):
            await evolution.transition(
                replace(proposal, id=uuid4(), version=2), 1, audit, event(uuid4(), "missing")
            )
        with pytest.raises(ConcurrencyConflictError):
            await evolution.transition(
                replace(proposal, version=3), 1, audit, event(proposal.id, "conflict")
            )

    asyncio.run(scenario())
