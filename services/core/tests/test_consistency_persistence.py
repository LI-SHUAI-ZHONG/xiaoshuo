from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from accos.adapters.consistency import SqlAlchemyConsistencyRepository
from accos.adapters.persistence import DatabaseRuntime, EngineOptions
from accos.adapters.quality import SqlAlchemyQualityRepository
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.settings import load_settings
from accos.modules.consistency.public import (
    AppliedRevision,
    CanonEntry,
    CanonLevel,
    CanonStatus,
    ConsistencyCheckRun,
    EvidenceProjection,
    FactTarget,
    Finding,
    FindingSeverity,
    FindingStatus,
    FindingType,
    ResolutionDecision,
    ResolutionProposal,
    ResolutionStatus,
    TimelineEvent,
    ValidationStatus,
    ValidatorReport,
)
from accos.modules.quality.public import (
    DimensionStatus,
    EvaluationRun,
    QualityResult,
    QualityStatus,
    RubricVersion,
    ScoreDimension,
)
from test_persistence import seed_workflow_scope

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def stage14_database_url() -> Iterator[str]:
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


def test_sql_consistency_quality_round_trip_and_concurrency(  # noqa: PLR0915
    stage14_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(stage14_database_url, EngineOptions(2, 1, 1, 60))
        consistency = SqlAlchemyConsistencyRepository(runtime.sessions)
        quality = SqlAlchemyQualityRepository(runtime.sessions)
        now = datetime(2026, 9, 6, 13, tzinfo=UTC)
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

        canon = CanonEntry(
            uuid4(),
            uuid4(),
            workspace_id,
            project_id,
            "fixture-canon",
            CanonLevel.LEVEL_2,
            1,
            now,
            None,
            "fixture-source://canon",
            CanonStatus.PROPOSAL,
            actor_id,
            now,
        )
        assert await consistency.add_canon(canon, event(canon.id, "consistency.canon")) == canon
        assert await consistency.add_canon(canon, event(canon.id, "consistency.canon")) == canon
        timeline = TimelineEvent(
            uuid4(),
            workspace_id,
            project_id,
            "creative-event://fixture",
            now,
            0,
            ("creative-record://character/fixture",),
            ("creative-record://world/fixture",),
            1,
        )
        assert await consistency.add_timeline(timeline) == timeline
        assert await consistency.add_timeline(timeline) == timeline

        report = ValidatorReport("structural", "1.0.0", ValidationStatus.PASSED)
        check = ConsistencyCheckRun(
            uuid4(),
            workspace_id,
            project_id,
            uuid4(),
            actor_id,
            ValidationStatus.PASSED,
            (report,),
            now,
        )
        finding = Finding(
            uuid4(),
            workspace_id,
            project_id,
            check.id,
            FindingType.VERSION_CONFLICT,
            FindingSeverity.ERROR,
            ("creative-record://world/fixture",),
            "evidence_version_changed",
            "structural",
            "1.0.0",
            FindingStatus.OPEN,
            check.workflow_run_id,
            actor_id,
            now,
        )
        await consistency.add_check(check, (finding,), event(check.id, "consistency.check"))
        assert await consistency.get_check(workspace_id, project_id, check.id) == check
        assert await consistency.get_check(uuid4(), project_id, check.id) is None
        assert await consistency.findings_for_check(workspace_id, project_id, check.id) == (
            finding,
        )
        assert await consistency.findings_for_check(uuid4(), project_id, check.id) == ()
        assert await consistency.findings_by_ids(workspace_id, project_id, ()) == ()
        assert await consistency.findings_by_ids(
            workspace_id, project_id, (finding.id, uuid4())
        ) == (finding,)

        proposal = ResolutionProposal(
            uuid4(),
            workspace_id,
            project_id,
            (finding.id,),
            "fixture-strategy",
            FactTarget("creative-record://world/fixture", 1),
            ("fixture-impact://one",),
            True,
            ResolutionStatus.PROPOSED,
            actor_id,
            check.workflow_run_id,
            now,
            now,
        )
        assert (
            await consistency.add_resolution(proposal, event(proposal.id, "consistency.resolution"))
            == proposal
        )
        assert (
            await consistency.add_resolution(proposal, event(proposal.id, "consistency.resolution"))
            == proposal
        )
        assert await consistency.get_resolution(workspace_id, project_id, proposal.id) == proposal
        assert await consistency.get_resolution(uuid4(), project_id, proposal.id) is None
        with pytest.raises(ScopeViolationError):
            await consistency.decide_resolution(
                workspace_id,
                project_id,
                uuid4(),
                decision=ResolutionDecision.APPROVE,
                expected_version=1,
                actor_id=actor_id,
                event=event(proposal.id, "consistency.decided"),
            )
        with pytest.raises(ConcurrencyConflictError):
            await consistency.decide_resolution(
                workspace_id,
                project_id,
                proposal.id,
                decision=ResolutionDecision.APPROVE,
                expected_version=2,
                actor_id=actor_id,
                event=event(proposal.id, "consistency.decided"),
            )
        approved = await consistency.decide_resolution(
            workspace_id,
            project_id,
            proposal.id,
            decision=ResolutionDecision.APPROVE,
            expected_version=1,
            actor_id=actor_id,
            event=event(proposal.id, "consistency.decided"),
        )
        with pytest.raises(InvalidStateError):
            await consistency.decide_resolution(
                workspace_id,
                project_id,
                proposal.id,
                decision=ResolutionDecision.REJECT,
                expected_version=approved.version,
                actor_id=actor_id,
                event=event(proposal.id, "consistency.decided"),
            )
        with pytest.raises(ConcurrencyConflictError):
            await consistency.claim_resolution(
                workspace_id,
                project_id,
                proposal.id,
                expected_version=1,
                actor_id=actor_id,
            )
        claimed = await consistency.claim_resolution(
            workspace_id,
            project_id,
            proposal.id,
            expected_version=approved.version,
            actor_id=actor_id,
        )
        with pytest.raises(InvalidStateError):
            await consistency.claim_resolution(
                workspace_id,
                project_id,
                proposal.id,
                expected_version=claimed.version,
                actor_id=actor_id,
            )
        with pytest.raises(ConcurrencyConflictError):
            await consistency.finish_resolution(
                workspace_id,
                project_id,
                proposal.id,
                expected_version=approved.version,
                result=AppliedRevision("creative-record://world/result", 2),
                event=event(proposal.id, "consistency.applied"),
            )
        applied = await consistency.finish_resolution(
            workspace_id,
            project_id,
            proposal.id,
            expected_version=claimed.version,
            result=AppliedRevision("creative-record://world/result", 2),
            event=event(proposal.id, "consistency.applied"),
        )
        assert applied.status is ResolutionStatus.APPLIED
        with pytest.raises(InvalidStateError):
            await consistency.finish_resolution(
                workspace_id,
                project_id,
                proposal.id,
                expected_version=applied.version,
                result=AppliedRevision("creative-record://world/result", 2),
                event=event(proposal.id, "consistency.applied"),
            )
        assert (await consistency.findings_by_ids(workspace_id, project_id, (finding.id,)))[
            0
        ].status is FindingStatus.RESOLVED

        projection = EvidenceProjection(
            "creative-record://world/result", "world", uuid4(), uuid4(), 2, now
        )
        await consistency.replace_projection(workspace_id, project_id, (projection,))
        assert await consistency.read_projection(workspace_id, project_id) == (projection,)
        await consistency.replace_projection(workspace_id, project_id, ())
        assert await consistency.read_projection(workspace_id, project_id) == ()

        rubric = RubricVersion(
            uuid4(),
            workspace_id,
            project_id,
            "fixture-rubric",
            1,
            "fixture-schema-v1",
            ("structural-consistency",),
            actor_id,
            now,
        )
        assert await quality.add_rubric(rubric) == rubric
        assert await quality.add_rubric(rubric) == rubric
        assert await quality.get_rubric(workspace_id, project_id, rubric.id) == rubric
        assert await quality.get_rubric(uuid4(), project_id, rubric.id) is None
        run = EvaluationRun(
            uuid4(),
            workspace_id,
            project_id,
            rubric.id,
            check.reference,
            check.workflow_run_id,
            actor_id,
            QualityStatus.NOT_RUN,
            now,
        )
        assert await quality.add_run(run, event(run.id, "quality.started")) == run
        assert await quality.add_run(run, event(run.id, "quality.started")) == run
        assert await quality.get_run(workspace_id, project_id, run.id) == run
        assert await quality.get_run(uuid4(), project_id, run.id) is None
        completed = replace(run, status=QualityStatus.PASSED, completed_at=now)
        result = QualityResult(
            uuid4(),
            workspace_id,
            project_id,
            run.id,
            QualityStatus.PASSED,
            "structural-quality",
            "1.0.0",
            (ScoreDimension("structural-consistency", DimensionStatus.PASSED),),
            "quality-result://passed",
            now,
        )
        assert await quality.finish_run(completed, result, event(run.id, "quality.completed")) == (
            completed,
            result,
        )
        assert await quality.get_result(workspace_id, project_id, run.id) == result
        assert await quality.get_result(uuid4(), project_id, run.id) is None
        with pytest.raises(InvalidStateError):
            await quality.finish_run(completed, result, event(run.id, "quality.completed"))
        await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)
