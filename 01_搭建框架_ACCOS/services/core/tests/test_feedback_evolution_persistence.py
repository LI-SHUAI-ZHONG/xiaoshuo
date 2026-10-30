from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from accos.adapters.evolution import SqlAlchemyEvolutionMemory
from accos.adapters.feedback import SqlAlchemyFeedbackRepository
from accos.adapters.persistence import DatabaseRuntime, EngineOptions
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.settings import load_settings
from accos.modules.evolution.public import (
    ChangeAction,
    EvolutionAuditEntry,
    EvolutionState,
    ImprovementProposal,
)
from accos.modules.feedback.public import (
    ArtifactKind,
    BehaviorConsent,
    ConsentStatus,
    DiagnosticFinding,
    DiagnosticSeverity,
    Experiment,
    ExperimentSample,
    ExperimentStatus,
    FeedbackEvent,
    FeedbackSource,
    FeedbackStatus,
    MetricPoint,
    TombstoneAction,
    Variant,
    default_metric_definitions,
)
from test_persistence import seed_workflow_scope

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def stage15_database_url() -> Iterator[str]:
    source = make_url(load_settings().required.database_url)
    name = f"accos_test_{uuid4().hex}"
    admin_url = source.set(drivername="postgresql", database="postgres")
    admin_dsn = admin_url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    database_url = source.set(drivername="postgresql+psycopg", database=name).render_as_string(
        hide_password=False
    )
    config = Config(str(Path(__file__).resolve().parents[3] / "services/core/alembic.ini"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
    try:
        yield database_url
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_sql_feedback_withdrawal_and_evolution_concurrency(  # noqa: PLR0915
    stage15_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(stage15_database_url, EngineOptions(2, 1, 1, 60))
        feedback = SqlAlchemyFeedbackRepository(runtime.sessions)
        evolution = SqlAlchemyEvolutionMemory(runtime.sessions)
        now = datetime(2026, 9, 6, 15, tzinfo=UTC)
        actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, now)

        def event(aggregate_id: UUID, kind: str) -> EventEnvelope:
            return EventEnvelope(
                uuid4(),
                workspace_id,
                project_id,
                aggregate_id,
                kind,
                1,
                {"schema": f"{kind}.v1"},
                now,
            )

        consent = BehaviorConsent(
            uuid4(),
            workspace_id,
            project_id,
            actor_id,
            "behavior-consent-v1",
            ConsentStatus.ACTIVE,
            now,
        )
        assert await feedback.add_consent(consent, event(consent.id, "feedback.consent")) == consent
        assert await feedback.add_consent(consent, event(consent.id, "duplicate")) == consent
        assert await feedback.active_consent(workspace_id, project_id, actor_id) == consent
        assert await feedback.active_consent(uuid4(), project_id, actor_id) is None

        captured = FeedbackEvent(
            uuid4(),
            workspace_id,
            project_id,
            actor_id,
            FeedbackSource.BEHAVIOR_CONSENTED,
            "creator-preference.v1",
            "fixture-choice",
            1.0,
            "technical-event://fixture",
            consent.id,
            FeedbackStatus.ACTIVE,
            now,
            f"creative-record://creator/{uuid4()}",
        )
        assert (
            await feedback.add_feedback(captured, event(captured.id, "feedback.captured"))
            == captured
        )
        assert await feedback.add_feedback(captured, event(captured.id, "duplicate")) == captured
        assert await feedback.get_feedback(workspace_id, project_id, captured.id) == captured
        assert await feedback.get_feedback(uuid4(), project_id, captured.id) is None
        captured_without_creator = replace(
            captured,
            id=uuid4(),
            signal_code="fixture-technical",
            creator_signal_reference=None,
        )
        await feedback.add_feedback(
            captured_without_creator,
            event(captured_without_creator.id, "feedback.captured"),
        )

        definition = next(
            item
            for item in default_metric_definitions(workspace_id, project_id, actor_id, now)
            if item.name == "runtime.health"
        )
        assert await feedback.add_metric_definition(definition) == definition
        assert await feedback.add_metric_definition(definition) == definition
        point = MetricPoint(
            uuid4(),
            workspace_id,
            project_id,
            definition.id,
            definition.name,
            1.0,
            (("component", "worker"), ("status", "unhealthy")),
            now,
            "runtime-check://worker",
            captured.id,
        )
        assert await feedback.add_metric_point(point, event(point.id, "feedback.metric")) == point
        assert await feedback.add_metric_point(point, event(point.id, "duplicate")) == point
        assert await feedback.get_metric_point(workspace_id, project_id, point.id) == point
        assert await feedback.get_metric_point(uuid4(), project_id, point.id) is None
        finding = DiagnosticFinding(
            uuid4(),
            workspace_id,
            project_id,
            point.id,
            "runtime-unhealthy",
            "1.0.0",
            "runtime_component_unhealthy",
            DiagnosticSeverity.CRITICAL,
            1.0,
            1.0,
            now,
        )
        assert (
            await feedback.add_diagnostic(finding, event(finding.id, "feedback.diagnostic"))
            == finding
        )
        assert await feedback.add_diagnostic(finding, event(finding.id, "duplicate")) == finding
        assert await feedback.get_diagnostic(workspace_id, project_id, finding.id) == finding
        assert await feedback.get_diagnostic(uuid4(), project_id, finding.id) is None

        experiment = Experiment(
            uuid4(),
            workspace_id,
            project_id,
            "fixture-experiment",
            "protocol-v1",
            "worker-recovery",
            definition.name,
            "technical-smoke",
            now,
            now + timedelta(hours=1),
            ("stop-on-error",),
            ExperimentStatus.PLANNED,
            actor_id,
            now,
        )
        variants = (
            Variant(uuid4(), experiment.id, "candidate", "configuration://fixture/candidate"),
            Variant(uuid4(), experiment.id, "control", "configuration://fixture/control"),
        )
        stored_experiment = await feedback.add_experiment(
            experiment, variants, event(experiment.id, "feedback.experiment")
        )
        assert stored_experiment == (experiment, variants)
        duplicate_experiment = await feedback.add_experiment(
            experiment, variants, event(experiment.id, "duplicate")
        )
        assert duplicate_experiment == (experiment, variants)
        assert await feedback.get_experiment(workspace_id, project_id, experiment.id) == (
            experiment,
            variants,
        )
        assert await feedback.get_experiment(uuid4(), project_id, experiment.id) is None
        sample = ExperimentSample(
            uuid4(),
            workspace_id,
            project_id,
            experiment.id,
            variants[0].id,
            point.id,
            captured.id,
            now,
        )
        assert await feedback.add_sample(sample, event(sample.id, "feedback.sample")) == sample
        assert await feedback.add_sample(sample, event(sample.id, "duplicate")) == sample
        with pytest.raises(InvalidStateError):
            await feedback.transition_experiment(
                replace(experiment, status=ExperimentStatus.RUNNING),
                ExperimentStatus.RUNNING,
                event(experiment.id, "feedback.invalid-transition"),
            )
        running = replace(experiment, status=ExperimentStatus.RUNNING)
        assert (
            await feedback.transition_experiment(
                running,
                ExperimentStatus.PLANNED,
                event(experiment.id, "feedback.experiment-started"),
            )
            == running
        )
        completed = replace(running, status=ExperimentStatus.COMPLETED, result_code="no-regression")
        assert (
            await feedback.transition_experiment(
                completed,
                ExperimentStatus.RUNNING,
                event(experiment.id, "feedback.experiment-finished"),
            )
            == completed
        )

        withdrawn_at = now + timedelta(minutes=1)
        result = await feedback.withdraw_consent(
            workspace_id,
            project_id,
            actor_id,
            withdrawn_at=withdrawn_at,
            event=event(consent.id, "feedback.withdrawn"),
        )
        assert result.consent.status is ConsentStatus.WITHDRAWN
        assert set(result.anonymized_event_ids) == {captured.id, captured_without_creator.id}
        assert {item.artifact_kind for item in result.tombstones} == {
            ArtifactKind.METRIC_POINT,
            ArtifactKind.EXPERIMENT_SAMPLE,
            ArtifactKind.CREATOR_SIGNAL,
        }
        assert {item.action for item in result.tombstones} == {
            TombstoneAction.RECOMPUTE,
            TombstoneAction.EXCLUDE,
        }
        redacted = await feedback.get_feedback(workspace_id, project_id, captured.id)
        assert redacted is not None and redacted.status is FeedbackStatus.ANONYMIZED
        assert redacted.consent_id is None
        assert redacted.creator_signal_reference is None
        excluded = await feedback.get_metric_point(workspace_id, project_id, point.id)
        assert excluded is not None and not excluded.included
        assert await feedback.active_consent(workspace_id, project_id, actor_id) is None
        with pytest.raises(InvalidStateError):
            await feedback.withdraw_consent(
                workspace_id,
                project_id,
                actor_id,
                withdrawn_at=withdrawn_at,
                event=event(consent.id, "feedback.withdrawn"),
            )

        proposal = ImprovementProposal(
            uuid4(),
            workspace_id,
            project_id,
            (finding.id,),
            (finding.reference, point.reference),
            ("observer:diagnostic-observer@1.0.0",),
            EvolutionState.OBSERVED,
            actor_id,
            now,
            now,
        )
        observed_audit = EvolutionAuditEntry(
            uuid4(),
            workspace_id,
            project_id,
            proposal.id,
            None,
            EvolutionState.OBSERVED,
            actor_id,
            proposal.algorithm_versions,
            proposal.input_references,
            None,
            "finding-observed",
            now,
        )
        assert (
            await evolution.add(proposal, observed_audit, event(proposal.id, "evolution.observed"))
            == proposal
        )
        assert (
            await evolution.add(proposal, observed_audit, event(proposal.id, "duplicate"))
            == proposal
        )
        assert await evolution.get(workspace_id, project_id, proposal.id) == proposal
        assert await evolution.get(uuid4(), project_id, proposal.id) is None
        updated = replace(
            proposal,
            state=EvolutionState.PROPOSED,
            action=ChangeAction.SUGGEST_CONFIGURATION,
            change_reference="change://fixture/configuration",
            safety_policy_version="evolution-safety-v1",
            safety_rule_code="immutable-policy-allow",
            simulation_evidence=("simulation-evidence://fixture",),
            evaluation_code="simulation-evaluated",
            approved_by=actor_id,
            rollback_reference="rollback://fixture/configuration",
            updated_at=withdrawn_at,
            version=2,
        )
        transition_audit = EvolutionAuditEntry(
            uuid4(),
            workspace_id,
            project_id,
            proposal.id,
            EvolutionState.OBSERVED,
            EvolutionState.PROPOSED,
            actor_id,
            updated.algorithm_versions,
            updated.input_references,
            updated.rollback_reference,
            "immutable-policy-allow",
            withdrawn_at,
        )
        with pytest.raises(ScopeViolationError):
            await evolution.transition(
                replace(updated, id=uuid4()),
                1,
                transition_audit,
                event(uuid4(), "evolution.missing"),
            )
        with pytest.raises(ConcurrencyConflictError):
            await evolution.transition(
                replace(updated, version=3),
                1,
                transition_audit,
                event(proposal.id, "evolution.conflict"),
            )
        assert (
            await evolution.transition(
                updated,
                1,
                transition_audit,
                event(proposal.id, "evolution.proposed"),
            )
            == updated
        )
        assert await evolution.get(workspace_id, project_id, proposal.id) == updated
        await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)
