from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from accos.adapters.consistency import InMemoryConsistencyRepository
from accos.adapters.consistency.facts import CreativeFactRevisionAdapter, _target
from accos.adapters.consistency.persistence import _report
from accos.adapters.creative import InMemoryCreativeRepository
from accos.adapters.quality import InMemoryQualityRepository
from accos.kernel.errors import (
    ConcurrencyConflictError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.consistency.application import _aggregate_status
from accos.modules.consistency.public import (
    ACCEPTED_REVISION_STEP,
    AppliedRevision,
    ApplyResolutionCommand,
    CanonChangeAssertion,
    CanonLevel,
    CanonQualityWorkflowExecutor,
    ConsistencyAccess,
    ConsistencyService,
    CreateCanonCommand,
    DecideResolutionCommand,
    DependencyEdge,
    EntityStateAssertion,
    EvidenceProjection,
    FactTarget,
    FindingSeverity,
    FindingType,
    NullSemanticValidator,
    PersistedCanonQualityGate,
    ProjectionRebuilder,
    ProposeResolutionCommand,
    RecordTimelineCommand,
    ReferenceAssertion,
    RequiredFieldAssertion,
    ResolutionDecision,
    ResolutionStatus,
    RunCheckCommand,
    StructuralValidator,
    TargetVersionConflictError,
    TimelineAssertion,
    ValidationBundle,
    ValidationStatus,
    ValidatorKind,
    ValidatorRegistry,
    ValidatorReport,
    VersionAssertion,
    canon_quality_definition,
    default_validator_registry,
)
from accos.modules.consistency.workflow import _applied_reference, _gate_reference
from accos.modules.creative.public import (
    ApplyCreativeResolutionCommand,
    CreateWorldCommand,
    CreativeAccess,
    CreativeApplication,
    CreativeContainer,
    CreativeDecision,
    CreativeRecord,
    CreativeRecordStatus,
    CreativeRevisionConflictError,
    CreativeRevisionService,
    DecideWorldRecordCommand,
    ProposeWorldRecordCommand,
    WorldService,
    WorldState,
)
from accos.modules.identity.public import AuthorizationService, Role, permissions_for
from accos.modules.projects.public import (
    Project,
    ProjectRepository,
    ProjectSettings,
    ProjectStatus,
)
from accos.modules.quality.public import (
    CreateRubricCommand,
    EvaluationEvidence,
    NullQualityEvaluator,
    QualityAccess,
    QualityEvaluator,
    QualityService,
    QualityStatus,
    StartEvaluationCommand,
    StructuralQualityEvaluator,
)
from accos.modules.workflows.public import (
    PermanentStepError,
    StepExecution,
    StepExecutionResult,
    StepKind,
)

if TYPE_CHECKING:
    from accos.modules.identity.ports import AuditEvent
    from accos.modules.workflows.public import StepExecutor

NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)
ACTOR_ID = UUID("e0000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("e0000000-0000-4000-8000-000000000002")
PROJECT_ID = UUID("e0000000-0000-4000-8000-000000000003")


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


class Facts:
    def __init__(self) -> None:
        self.versions: dict[str, int] = {"creative-record://world/fixture": 1}
        self.applied: list[str] = []

    async def current_version(
        self, context: SecurityContext, project_id: UUID, target: FactTarget
    ) -> int:
        assert context.workspace_id == WORKSPACE_ID and project_id == PROJECT_ID
        return self.versions[target.reference]

    async def apply(
        self,
        context: SecurityContext,
        project_id: UUID,
        target: FactTarget,
        resolution_reference: str,
    ) -> AppliedRevision:
        assert context.actor_id == ACTOR_ID and project_id == PROJECT_ID
        self.versions[target.reference] += 1
        self.applied.append(resolution_reference)
        return AppliedRevision("creative-record://world/result", self.versions[target.reference])


def context(*, role: Role = Role.OWNER, project_id: UUID | None = None) -> SecurityContext:
    correlation = uuid4()
    return SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        WORKSPACE_ID,
        permissions_for(role),
        "fixture-policy-v1",
        CorrelationIds(str(correlation), str(correlation)),
        project_id,
    )


def consistency_services() -> tuple[
    ConsistencyService, InMemoryConsistencyRepository, Facts, Projects, Audit
]:
    repository = InMemoryConsistencyRepository()
    projects = Projects()
    audit = Audit()
    service = ConsistencyService(
        repository,
        ConsistencyAccess(
            cast("ProjectRepository", projects), AuthorizationService(audit, Clock())
        ),
        default_validator_registry(),
        Facts(),
        Clock(),
    )
    return service, repository, cast("Facts", service._facts), projects, audit  # noqa: SLF001


def test_structural_validator_and_status_semantics_are_fail_honest() -> None:
    async def scenario() -> None:
        previous = NOW
        evidence = ValidationBundle(
            required_fields=(RequiredFieldAssertion("fixture://required", "id", False),),
            references=(ReferenceAssertion("fixture://missing", False),),
            timeline=(
                TimelineAssertion(
                    "fixture://event",
                    NOW - timedelta(seconds=1),
                    "fixture://previous",
                    previous,
                ),
            ),
            entity_states=(
                EntityStateAssertion("fixture://entity", "a", "fixture-group"),
                EntityStateAssertion("fixture://entity", "b", "fixture-group"),
                EntityStateAssertion("fixture://entity", "ignored", "fixture-group", False),
            ),
            versions=(VersionAssertion("fixture://version", 1, 2),),
            canon_changes=(
                CanonChangeAssertion("fixture://canon", CanonLevel.LEVEL_1, True, False),
            ),
            dependencies=(DependencyEdge(uuid4(), "fixture://source", "fixture://target", False),),
        )
        report = await StructuralValidator().validate(evidence)
        assert report.status is ValidationStatus.FINDINGS
        assert {item.finding_type for item in report.findings} == set(FindingType)
        assert (
            next(
                item for item in report.findings if item.finding_type is FindingType.PROTECTED_CANON
            ).severity
            is FindingSeverity.BLOCKER
        )
        assert (await StructuralValidator().validate(ValidationBundle())).status is (
            ValidationStatus.PASSED
        )

        registry = ValidatorRegistry()
        assert registry.not_run("fixture").status is ValidationStatus.NOT_RUN
        assert (await registry.run("missing", ValidationBundle())).status is (
            ValidationStatus.NOT_CONFIGURED
        )
        registry.register(NullSemanticValidator(ValidatorKind.CHARACTER))
        assert (await registry.run("character", ValidationBundle())).status is (
            ValidationStatus.NOT_CONFIGURED
        )
        with pytest.raises(ValueError, match="already registered"):
            registry.register(NullSemanticValidator(ValidatorKind.CHARACTER))

        class Broken:
            key = "broken"
            version = "1.2.3"

            async def validate(self, evidence: ValidationBundle) -> ValidatorReport:
                raise RuntimeError(evidence)

        registry.register(Broken())
        failed = await registry.run("broken", ValidationBundle())
        assert failed.status is ValidationStatus.RUN_FAILED
        assert failed.error_code == "validator_execution_failed"
        with pytest.raises(ValueError, match="must contain"):
            ValidatorReport("fixture", "1", ValidationStatus.FINDINGS)
        with pytest.raises(ValueError, match="only a findings"):
            ValidatorReport("fixture", "1", ValidationStatus.PASSED, report.findings)
        with pytest.raises(ValueError, match="error code"):
            ValidatorReport("fixture", "1", ValidationStatus.RUN_FAILED)
        with pytest.raises(ValueError, match="error code"):
            ValidatorReport("fixture", "1", ValidationStatus.PASSED, error_code="fixture")
        conflict = TargetVersionConflictError(7)
        assert conflict.current_version == 7 and conflict.details == {"current_version": 7}
        with pytest.raises(ValueError, match="must be a list"):
            _report(
                {
                    "validator_key": "fixture",
                    "validator_version": "1",
                    "status": "passed",
                    "error_code": None,
                    "findings": "invalid",
                }
            )
        assert _aggregate_status((ValidationStatus.RUN_FAILED,)) is ValidationStatus.RUN_FAILED
        assert _aggregate_status((ValidationStatus.NOT_CONFIGURED,)) is (
            ValidationStatus.NOT_CONFIGURED
        )
        assert _aggregate_status((ValidationStatus.NOT_RUN,)) is ValidationStatus.NOT_RUN

    asyncio.run(scenario())


def test_consistency_service_resolution_version_gate_trace_and_projection() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        service, repository, facts, projects, audit = consistency_services()
        ctx = context()
        canon = await service.create_canon(
            ctx,
            CreateCanonCommand(
                PROJECT_ID,
                uuid4(),
                "fixture-canon",
                CanonLevel.LEVEL_2,
                1,
                NOW,
                None,
                "fixture-source://canon",
            ),
        )
        assert canon.status.value == "proposal"
        assert await repository.add_canon(canon, repository.events[-1]) == canon
        for command in (
            replace(
                CreateCanonCommand(
                    PROJECT_ID,
                    uuid4(),
                    "fixture",
                    CanonLevel.LEVEL_2,
                    1,
                    NOW,
                    None,
                    "fixture://source",
                ),
                canon_key="",
            ),
            CreateCanonCommand(
                PROJECT_ID,
                uuid4(),
                "fixture",
                CanonLevel.LEVEL_2,
                0,
                NOW,
                None,
                "fixture://source",
            ),
            CreateCanonCommand(
                PROJECT_ID,
                uuid4(),
                "fixture",
                CanonLevel.LEVEL_2,
                1,
                NOW,
                NOW,
                "fixture://source",
            ),
        ):
            with pytest.raises(ValueError):
                await service.create_canon(ctx, command)

        timeline = await service.record_timeline(
            ctx,
            RecordTimelineCommand(
                PROJECT_ID,
                "creative-event://fixture",
                NOW,
                0,
                ("creative-record://character/fixture",),
                ("creative-record://world/fixture",),
            ),
        )
        assert await repository.add_timeline(timeline) == timeline
        with pytest.raises(ValueError):
            await service.record_timeline(
                ctx, RecordTimelineCommand(PROJECT_ID, "fixture://event", NOW, -1)
            )

        run, findings = await service.run_check(
            ctx,
            RunCheckCommand(
                PROJECT_ID,
                ValidationBundle(references=(ReferenceAssertion("fixture://missing", False),)),
                workflow_run_id=uuid4(),
            ),
        )
        assert run.status is ValidationStatus.FINDINGS and len(findings) == 1
        assert findings[0].reference.startswith("consistency-finding://")
        assert await service.get_check(ctx, PROJECT_ID, run.id) == run
        assert await service.get_check_with_findings(ctx, PROJECT_ID, run.id) == (
            run,
            findings,
        )
        passed, no_findings = await service.run_check(
            ctx, RunCheckCommand(PROJECT_ID, ValidationBundle())
        )
        assert passed.status is ValidationStatus.PASSED and no_findings == ()
        with pytest.raises(ValueError):
            await service.run_check(ctx, RunCheckCommand(PROJECT_ID, ValidationBundle(), ()))
        with pytest.raises(ValueError):
            await service.run_check(
                ctx, RunCheckCommand(PROJECT_ID, ValidationBundle(), ("structural", "structural"))
            )
        with pytest.raises(ScopeViolationError):
            await service.get_check(ctx, PROJECT_ID, uuid4())
        with pytest.raises(ScopeViolationError):
            await service.get_check_with_findings(ctx, PROJECT_ID, uuid4())

        target = FactTarget("creative-record://world/fixture", 1)
        with pytest.raises(ValueError):
            await service.propose_resolution(
                ctx,
                ProposeResolutionCommand(PROJECT_ID, (), "fixture-strategy", target, ()),
            )
        with pytest.raises(ScopeViolationError):
            await service.propose_resolution(
                ctx,
                ProposeResolutionCommand(PROJECT_ID, (uuid4(),), "fixture-strategy", target, ()),
            )
        proposal = await service.propose_resolution(
            ctx,
            ProposeResolutionCommand(
                PROJECT_ID,
                (findings[0].id,),
                "fixture-strategy",
                target,
                ("fixture-impact://one",),
                run.workflow_run_id,
            ),
        )
        assert proposal.status is ResolutionStatus.PROPOSED
        assert await repository.add_resolution(proposal, repository.events[-1]) == proposal
        with pytest.raises(InvalidStateError, match="approved"):
            await service.apply_resolution(ctx, ApplyResolutionCommand(PROJECT_ID, proposal.id, 1))
        with pytest.raises(ConcurrencyConflictError):
            await service.decide_resolution(
                ctx,
                DecideResolutionCommand(PROJECT_ID, proposal.id, ResolutionDecision.APPROVE, 2),
            )
        approved = await service.decide_resolution(
            ctx,
            DecideResolutionCommand(PROJECT_ID, proposal.id, ResolutionDecision.APPROVE, 1),
        )
        assert approved.status is ResolutionStatus.APPROVED and approved.approved_by == ACTOR_ID
        with pytest.raises(InvalidStateError):
            await service.decide_resolution(
                ctx,
                DecideResolutionCommand(
                    PROJECT_ID, proposal.id, ResolutionDecision.REJECT, approved.version
                ),
            )
        facts.versions[target.reference] = 2
        with pytest.raises(TargetVersionConflictError) as stale:
            await service.apply_resolution(
                ctx, ApplyResolutionCommand(PROJECT_ID, proposal.id, approved.version)
            )
        assert stale.value.current_version == 2
        facts.versions[target.reference] = 1
        applied = await service.apply_resolution(
            ctx, ApplyResolutionCommand(PROJECT_ID, proposal.id, approved.version)
        )
        assert applied.status is ResolutionStatus.APPLIED
        assert applied.result == AppliedRevision("creative-record://world/result", 2)
        trace = await service.trace(ctx, PROJECT_ID, proposal.id)
        assert trace.proposal == applied
        assert trace.findings[0].status.value == "resolved"
        with pytest.raises(TargetVersionConflictError):
            await service.apply_resolution(
                ctx, ApplyResolutionCommand(PROJECT_ID, proposal.id, applied.version)
            )
        with pytest.raises(ConcurrencyConflictError):
            await repository.claim_resolution(
                WORKSPACE_ID,
                PROJECT_ID,
                proposal.id,
                expected_version=1,
                actor_id=ACTOR_ID,
            )
        with pytest.raises(InvalidStateError, match="claimed"):
            await repository.claim_resolution(
                WORKSPACE_ID,
                PROJECT_ID,
                proposal.id,
                expected_version=applied.version,
                actor_id=ACTOR_ID,
            )
        with pytest.raises(ConcurrencyConflictError):
            await repository.finish_resolution(
                WORKSPACE_ID,
                PROJECT_ID,
                proposal.id,
                expected_version=1,
                result=applied.result,
                event=repository.events[-1],
            )
        with pytest.raises(InvalidStateError, match="finish"):
            await repository.finish_resolution(
                WORKSPACE_ID,
                PROJECT_ID,
                proposal.id,
                expected_version=applied.version,
                result=applied.result,
                event=repository.events[-1],
            )
        with pytest.raises(ScopeViolationError):
            await repository.claim_resolution(
                WORKSPACE_ID,
                PROJECT_ID,
                uuid4(),
                expected_version=1,
                actor_id=ACTOR_ID,
            )
        with pytest.raises(ScopeViolationError):
            await service.apply_resolution(ctx, ApplyResolutionCommand(PROJECT_ID, uuid4(), 1))
        with pytest.raises(ScopeViolationError):
            await service.trace(ctx, PROJECT_ID, uuid4())

        rejected_proposal = await service.propose_resolution(
            ctx,
            ProposeResolutionCommand(PROJECT_ID, (findings[0].id,), "fixture-reject", target, ()),
        )
        rejected = await service.decide_resolution(
            ctx,
            DecideResolutionCommand(PROJECT_ID, rejected_proposal.id, ResolutionDecision.REJECT, 1),
        )
        assert rejected.status is ResolutionStatus.REJECTED and rejected.approved_by is None

        projection = EvidenceProjection(
            "creative-record://world/result", "world", uuid4(), uuid4(), 2, NOW
        )

        class Reader:
            async def read_project(
                self, security: SecurityContext, project_id: UUID
            ) -> tuple[EvidenceProjection, ...]:
                assert security is ctx and project_id == PROJECT_ID
                return (projection,)

        rebuilt = await ProjectionRebuilder(repository, Reader()).rebuild(ctx, PROJECT_ID)
        assert rebuilt == (projection,)
        assert await repository.read_projection(WORKSPACE_ID, PROJECT_ID) == rebuilt
        assert await repository.read_projection(WORKSPACE_ID, uuid4()) == ()

        with pytest.raises(PermissionDeniedError):
            await service.create_canon(
                context(role=Role.VIEWER),
                CreateCanonCommand(
                    PROJECT_ID,
                    uuid4(),
                    "fixture",
                    CanonLevel.LEVEL_4,
                    1,
                    NOW,
                    None,
                    "fixture://source",
                ),
            )
        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ARCHIVED
        )
        with pytest.raises(InvalidStateError, match="Archived"):
            await service.record_timeline(
                ctx, RecordTimelineCommand(PROJECT_ID, "fixture://event", NOW, 1)
            )
        projects.items.clear()
        with pytest.raises(ScopeViolationError):
            await service.run_check(ctx, RunCheckCommand(PROJECT_ID, ValidationBundle()))
        assert audit.events

    asyncio.run(scenario())


def test_quality_lifecycle_null_failure_and_schema_only_rubric() -> None:  # noqa: PLR0915
    async def scenario() -> None:
        projects, audit = Projects(), Audit()
        repository = InMemoryQualityRepository()
        access = QualityAccess(
            cast("ProjectRepository", projects), AuthorizationService(audit, Clock())
        )
        ctx = context()
        service = QualityService(repository, access, StructuralQualityEvaluator(), Clock())
        rubric = await service.create_rubric(
            ctx,
            CreateRubricCommand(
                PROJECT_ID,
                "fixture-rubric",
                1,
                "fixture-schema-v1",
                ("structural-consistency",),
            ),
        )
        assert await repository.add_rubric(rubric) == rubric
        assert await repository.get_rubric(WORKSPACE_ID, PROJECT_ID, rubric.id) == rubric
        assert await repository.get_rubric(uuid4(), PROJECT_ID, rubric.id) is None
        invalid_rubrics = (
            replace(
                CreateRubricCommand(PROJECT_ID, "fixture", 1, "v1", ("dimension",)),
                rubric_key="",
            ),
            CreateRubricCommand(PROJECT_ID, "fixture", 0, "v1", ("dimension",)),
            CreateRubricCommand(PROJECT_ID, "fixture", 1, "", ("dimension",)),
            CreateRubricCommand(PROJECT_ID, "fixture", 1, "v1", ()),
            CreateRubricCommand(PROJECT_ID, "fixture", 1, "v1", ("same", "same")),
        )
        for command in invalid_rubrics:
            with pytest.raises(ValueError):
                await service.create_rubric(ctx, command)

        with pytest.raises(ScopeViolationError):
            await service.start(ctx, StartEvaluationCommand(PROJECT_ID, uuid4(), "fixture://input"))
        run = await service.start(
            ctx,
            StartEvaluationCommand(PROJECT_ID, rubric.id, "fixture://input", uuid4()),
        )
        assert run.status is QualityStatus.NOT_RUN and run.reference.startswith("quality-run://")
        assert await repository.add_run(run, repository.events[-1]) == run
        assert await repository.get_run(uuid4(), PROJECT_ID, run.id) is None
        completed, result = await service.evaluate(
            ctx,
            PROJECT_ID,
            run.id,
            EvaluationEvidence("fixture://input", "passed"),
        )
        assert completed.status is QualityStatus.PASSED
        assert result.dimensions[0].score is None
        assert await service.get_result(ctx, PROJECT_ID, run.id) == result
        with pytest.raises(InvalidStateError):
            await service.evaluate(
                ctx,
                PROJECT_ID,
                run.id,
                EvaluationEvidence("fixture://input", "passed"),
            )
        with pytest.raises(ScopeViolationError):
            await service.get_result(ctx, PROJECT_ID, uuid4())
        with pytest.raises(ScopeViolationError):
            await service.evaluate(
                ctx,
                PROJECT_ID,
                uuid4(),
                EvaluationEvidence("fixture://missing", "passed"),
            )

        failed_run = await service.start(
            ctx, StartEvaluationCommand(PROJECT_ID, rubric.id, "fixture://failed")
        )
        _, failed = await service.evaluate(
            ctx,
            PROJECT_ID,
            failed_run.id,
            EvaluationEvidence("fixture://failed", "findings"),
        )
        assert failed.status is QualityStatus.FAILED
        null_service = QualityService(repository, access, NullQualityEvaluator(), Clock())
        null_run = await null_service.start(
            ctx, StartEvaluationCommand(PROJECT_ID, rubric.id, "fixture://null")
        )
        _, not_configured = await null_service.evaluate(
            ctx,
            PROJECT_ID,
            null_run.id,
            EvaluationEvidence("fixture://null", "passed"),
        )
        assert not_configured.status is QualityStatus.NOT_CONFIGURED

        class BrokenEvaluator:
            key = "broken"
            version = "1"

            async def evaluate(self, evidence: EvaluationEvidence) -> object:
                raise RuntimeError(evidence)

        broken_service = QualityService(
            repository, access, cast("QualityEvaluator", BrokenEvaluator()), Clock()
        )
        broken_run = await broken_service.start(
            ctx, StartEvaluationCommand(PROJECT_ID, rubric.id, "fixture://broken")
        )
        _, broken = await broken_service.evaluate(
            ctx,
            PROJECT_ID,
            broken_run.id,
            EvaluationEvidence("fixture://broken", "passed"),
        )
        assert broken.status is QualityStatus.RUN_FAILED
        with pytest.raises(TypeError):
            await StructuralQualityEvaluator().evaluate(object())
        with pytest.raises(InvalidStateError):
            await repository.finish_run(completed, result, repository.events[-1])

        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ARCHIVED
        )
        with pytest.raises(InvalidStateError, match="Archived"):
            await service.start(
                ctx, StartEvaluationCommand(PROJECT_ID, rubric.id, "fixture://archived")
            )
        projects.items.clear()
        with pytest.raises(ScopeViolationError):
            await service.get_result(ctx, PROJECT_ID, run.id)

    asyncio.run(scenario())


def test_workflow_order_routes_owned_steps_and_fails_closed() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        definition = canon_quality_definition()
        assert [step.key for step in definition.steps] == [
            "draft",
            "consistency-check",
            "quality-check",
            "approval",
            "accepted-revision",
            "memory-update",
        ]
        assert definition.steps[3].kind is StepKind.APPROVAL

        class Fallback:
            def __init__(self) -> None:
                self.compensated = False

            async def execute(self, execution: StepExecution) -> StepExecutionResult:
                return StepExecutionResult(f"fallback://{execution.step_key}")

            async def compensate(self, execution: StepExecution, hook: str) -> None:
                assert execution.step_key == "fixture-other" and hook == "fixture-hook"
                self.compensated = True

        class Gate:
            async def execute_stage(self, execution: StepExecution) -> StepExecutionResult:
                return StepExecutionResult(f"gate://{execution.step_key}")

        def execution(step_key: str, security: SecurityContext | None) -> StepExecution:
            return StepExecution(
                uuid4(),
                uuid4(),
                step_key,
                StepKind.REFERENCE,
                1,
                f"fixture-{step_key}",
                "fixture://input",
                0,
                0,
                security,
            )

        fallback = Fallback()
        executor = CanonQualityWorkflowExecutor(cast("StepExecutor", fallback), Gate())
        result = await executor.execute(
            execution(ACCEPTED_REVISION_STEP, context(project_id=PROJECT_ID))
        )
        assert result.output_reference == "gate://accepted-revision"
        delegated = await executor.execute(execution("fixture-other", None))
        assert delegated.output_reference == "fallback://fixture-other"
        with pytest.raises(PermanentStepError, match="missing-context"):
            await executor.execute(execution("quality-check", None))
        await executor.compensate(execution("fixture-other", None), "fixture-hook")
        assert fallback.compensated

        check_id, quality_id, proposal_id = uuid4(), uuid4(), uuid4()
        gate_reference = f"canon-gate://{check_id}/{quality_id}/{proposal_id}/2"

        class PersistedConsistency:
            check_status = ValidationStatus.PASSED
            proposal_status = ResolutionStatus.APPLIED
            include_result = True

            async def get_check(self, *args: object) -> object:
                assert args
                return SimpleNamespace(status=self.check_status)

            async def apply_resolution(self, *args: object) -> object:
                assert args
                return SimpleNamespace(
                    id=proposal_id,
                    result=(
                        AppliedRevision("creative-record://world/result", 3)
                        if self.include_result
                        else None
                    ),
                )

            async def trace(self, *args: object) -> object:
                assert args
                return SimpleNamespace(proposal=SimpleNamespace(status=self.proposal_status))

        class PersistedQuality:
            status = QualityStatus.PASSED

            async def get_result(self, *args: object) -> object:
                assert args
                return SimpleNamespace(status=self.status)

        persisted_consistency = PersistedConsistency()
        persisted_quality = PersistedQuality()
        gate = PersistedCanonQualityGate(
            cast("ConsistencyService", persisted_consistency),
            cast("QualityService", persisted_quality),
        )
        secured = context(project_id=PROJECT_ID)
        draft_execution = replace(execution("draft", secured), input_reference=gate_reference)
        assert (await gate.execute_stage(draft_execution)).output_reference == gate_reference
        assert (
            await gate.execute_stage(replace(draft_execution, step_key="consistency-check"))
        ).output_reference == gate_reference
        persisted_consistency.check_status = ValidationStatus.FINDINGS
        with pytest.raises(PermanentStepError, match="blocked/findings"):
            await gate.execute_stage(replace(draft_execution, step_key="consistency-check"))
        persisted_consistency.check_status = ValidationStatus.PASSED
        assert (
            await gate.execute_stage(replace(draft_execution, step_key="quality-check"))
        ).output_reference == gate_reference
        persisted_quality.status = QualityStatus.FAILED
        with pytest.raises(PermanentStepError, match="quality-error://blocked/failed"):
            await gate.execute_stage(replace(draft_execution, step_key="quality-check"))
        persisted_quality.status = QualityStatus.PASSED
        accepted_result = await gate.execute_stage(
            replace(draft_execution, step_key="accepted-revision")
        )
        assert accepted_result.output_reference.endswith("/applied/3")
        persisted_consistency.include_result = False
        with pytest.raises(PermanentStepError, match="missing-applied"):
            await gate.execute_stage(replace(draft_execution, step_key="accepted-revision"))
        persisted_consistency.include_result = True
        memory_execution = replace(
            draft_execution,
            step_key="memory-update",
            input_reference=accepted_result.output_reference,
        )
        assert (await gate.execute_stage(memory_execution)).output_reference.startswith(
            "memory-update://no-content/"
        )
        persisted_consistency.proposal_status = ResolutionStatus.APPROVED
        with pytest.raises(PermanentStepError, match="not-applied"):
            await gate.execute_stage(memory_execution)
        with pytest.raises(PermanentStepError, match="unsupported-stage"):
            await gate.execute_stage(replace(draft_execution, step_key="unsupported"))
        with pytest.raises(PermanentStepError, match="missing-context"):
            await gate.execute_stage(execution("draft", None))
        for invalid in (
            "fixture://invalid",
            f"fixture://{check_id}/{quality_id}/{proposal_id}/1",
            f"canon-gate://{check_id}/{quality_id}/{proposal_id}/0",
            "canon-gate://invalid",
        ):
            with pytest.raises(PermanentStepError, match="invalid-gate"):
                _gate_reference(invalid)
        for invalid in (
            "fixture://invalid",
            f"consistency-resolution://{proposal_id}/pending/1",
            f"consistency-resolution://{proposal_id}/applied/0",
        ):
            with pytest.raises(PermanentStepError, match="invalid-resolution"):
                _applied_reference(invalid)

    asyncio.run(scenario())


def test_creative_fact_adapter_applies_only_through_public_revision_service() -> None:
    async def scenario() -> None:
        projects = Projects()
        creative_repository = InMemoryCreativeRepository()
        creative_application = CreativeApplication(
            creative_repository,
            CreativeAccess(
                cast("ProjectRepository", projects), AuthorizationService(Audit(), Clock())
            ),
            Clock(),
        )
        world_service = WorldService(creative_application)
        ctx = context()
        world = await world_service.create(ctx, CreateWorldCommand(PROJECT_ID, "fixture-world"))
        proposal, _ = await world_service.propose(
            ctx, ProposeWorldRecordCommand(PROJECT_ID, world.id, WorldState)
        )
        accepted = await world_service.decide(
            ctx,
            DecideWorldRecordCommand(PROJECT_ID, proposal.id, CreativeDecision.APPROVE, 1),
        )
        adapter = CreativeFactRevisionAdapter(CreativeRevisionService(creative_application))
        target = FactTarget(accepted.reference, 1)
        assert await adapter.current_version(ctx, PROJECT_ID, target) == 1
        applied = await adapter.apply(ctx, PROJECT_ID, target, "consistency-resolution://fixture")
        assert applied.version == 2
        assert creative_repository.records[accepted.id].current is False
        with pytest.raises(TargetVersionConflictError) as conflict:
            await adapter.apply(ctx, PROJECT_ID, target, "consistency-resolution://stale")
        assert conflict.value.current_version == 2
        with pytest.raises(ValueError, match="Creative record"):
            _target("fixture://invalid")

        pending, _ = await world_service.propose(
            ctx, ProposeWorldRecordCommand(PROJECT_ID, world.id, WorldState)
        )
        with pytest.raises(InvalidStateError, match="no current"):
            await CreativeRevisionService(creative_application).current_version(
                ctx, PROJECT_ID, pending.owner, pending.id
            )
        with pytest.raises(InvalidStateError, match="no current"):
            await CreativeRevisionService(creative_application).apply_resolution(
                ctx,
                ApplyCreativeResolutionCommand(
                    PROJECT_ID,
                    pending.owner,
                    pending.id,
                    pending.record_version,
                    "consistency-resolution://pending",
                ),
            )

        current = next(item for item in creative_repository.records.values() if item.current)
        queued = replace(
            current,
            id=uuid4(),
            record_version=current.record_version + 1,
            status=CreativeRecordStatus.PROPOSAL,
            current=False,
        )

        class RaceRepository:
            def __init__(self, latest: CreativeRecord | None) -> None:
                self.latest = latest

            async def get_current_record(
                self, *args: object, **kwargs: object
            ) -> CreativeRecord | None:
                assert args and not kwargs
                return self.latest

        class RaceApplication:
            def __init__(self, latest: CreativeRecord | None) -> None:
                self._repository = RaceRepository(current)
                self._raced = latest

            async def authorize_write(self, *args: object, **kwargs: object) -> None:
                assert args and not kwargs

            async def get_record(self, *args: object, **kwargs: object) -> CreativeRecord:
                assert args and not kwargs
                return current

            async def get_container(self, *args: object, **kwargs: object) -> CreativeContainer:
                assert args and not kwargs
                return world

            async def propose(self, *args: object, **kwargs: object) -> tuple[CreativeRecord, bool]:
                assert args and kwargs
                return queued, True

            async def decide(self, *args: object, **kwargs: object) -> CreativeRecord:
                assert args and not kwargs
                self._repository.latest = self._raced
                raise ConcurrencyConflictError

        latest = replace(
            current,
            id=uuid4(),
            record_version=current.record_version + 1,
        )
        race_command = ApplyCreativeResolutionCommand(
            PROJECT_ID,
            current.owner,
            current.id,
            current.record_version,
            "consistency-resolution://race",
        )
        with pytest.raises(CreativeRevisionConflictError) as race_conflict:
            await CreativeRevisionService(
                cast("CreativeApplication", RaceApplication(latest))
            ).apply_resolution(ctx, race_command)
        assert race_conflict.value.current_version == latest.record_version
        with pytest.raises(InvalidStateError, match="no current"):
            await CreativeRevisionService(
                cast("CreativeApplication", RaceApplication(None))
            ).apply_resolution(ctx, race_command)

        class ConflictingRevisions:
            async def current_version(
                self,
                security: SecurityContext,
                project_id: UUID,
                owner: object,
                record_id: UUID,
            ) -> int:
                assert security is ctx and project_id == PROJECT_ID and owner and record_id
                return 9

            async def apply_resolution(self, security: SecurityContext, command: object) -> object:
                assert security is ctx and command
                raise CreativeRevisionConflictError(9)

        conflict_adapter = CreativeFactRevisionAdapter(
            cast("CreativeRevisionService", ConflictingRevisions())
        )
        assert await conflict_adapter.current_version(ctx, PROJECT_ID, target) == 9
        with pytest.raises(TargetVersionConflictError) as mapped:
            await conflict_adapter.apply(
                ctx, PROJECT_ID, target, "consistency-resolution://conflict"
            )
        assert mapped.value.current_version == 9

        root = Path(__file__).resolve().parents[3]
        consistency_sources = tuple(
            (root / "services" / "core" / "src" / "accos" / "modules" / "consistency").glob("*.py")
        )
        assert all(
            "accos.adapters.creative" not in path.read_text(encoding="utf-8")
            for path in consistency_sources
        )

    asyncio.run(scenario())
