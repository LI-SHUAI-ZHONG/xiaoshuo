"""Authorized schema registration and quality evaluation lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus
from accos.modules.quality.domain import (
    EvaluationOutcome,
    EvaluationRun,
    EvaluatorReport,
    QualityResult,
    QualityStatus,
    RubricVersion,
)

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.projects.public import ProjectRepository
    from accos.modules.quality.domain import EvaluationEvidence
    from accos.modules.quality.ports import QualityEvaluator, QualityRepository


@dataclass(frozen=True, slots=True)
class CreateRubricCommand:
    project_id: UUID
    rubric_key: str
    version: int
    schema_version: str
    dimension_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StartEvaluationCommand:
    project_id: UUID
    rubric_id: UUID
    input_reference: str
    workflow_run_id: UUID | None = None


class QualityAccess:
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
            raise InvalidStateError("Archived projects cannot change quality state.")
        await self._authorizer.authorize(request)


class QualityService:
    def __init__(
        self,
        repository: QualityRepository,
        access: QualityAccess,
        evaluator: QualityEvaluator,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._access = access
        self._evaluator = evaluator
        self._clock = clock

    async def create_rubric(
        self, context: SecurityContext, command: CreateRubricCommand
    ) -> RubricVersion:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if (
            not command.rubric_key
            or command.rubric_key.strip() != command.rubric_key
            or command.version < 1
            or not command.schema_version
            or not command.dimension_keys
            or len(set(command.dimension_keys)) != len(command.dimension_keys)
        ):
            raise ValueError("rubric schema metadata is invalid")
        rubric = RubricVersion(
            uuid4(),
            context.workspace_id,
            command.project_id,
            command.rubric_key,
            command.version,
            command.schema_version,
            command.dimension_keys,
            context.actor_id,
            self._clock.now(),
        )
        return await self._repository.add_rubric(rubric)

    async def start(
        self, context: SecurityContext, command: StartEvaluationCommand
    ) -> EvaluationRun:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        rubric = await self._repository.get_rubric(
            context.workspace_id, command.project_id, command.rubric_id
        )
        if rubric is None:
            raise ScopeViolationError
        now = self._clock.now()
        run = EvaluationRun(
            uuid4(),
            context.workspace_id,
            command.project_id,
            rubric.id,
            command.input_reference,
            command.workflow_run_id,
            context.actor_id,
            QualityStatus.NOT_RUN,
            now,
        )
        return await self._repository.add_run(
            run, _event(context, command.project_id, run.id, "quality.evaluation-started", now)
        )

    async def evaluate(
        self,
        context: SecurityContext,
        project_id: UUID,
        run_id: UUID,
        evidence: EvaluationEvidence,
    ) -> tuple[EvaluationRun, QualityResult]:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        run = await self._repository.get_run(context.workspace_id, project_id, run_id)
        if run is None:
            raise ScopeViolationError
        if run.status is not QualityStatus.NOT_RUN:
            raise InvalidStateError("Only an evaluation that has not run can execute.")
        try:
            report = await self._evaluator.evaluate(evidence)
        except Exception:  # noqa: BLE001 - evaluator internals stay private.
            report = EvaluatorReport(
                self._evaluator.key,
                self._evaluator.version,
                EvaluationOutcome(
                    QualityStatus.RUN_FAILED,
                    (),
                    "quality-result://run-failed",
                ),
            )
        now = self._clock.now()
        completed = replace(run, status=report.outcome.status, completed_at=now)
        result = QualityResult(
            uuid4(),
            context.workspace_id,
            project_id,
            run.id,
            report.outcome.status,
            report.evaluator_key,
            report.evaluator_version,
            report.outcome.dimensions,
            report.outcome.result_reference,
            now,
        )
        return await self._repository.finish_run(
            completed,
            result,
            _event(context, project_id, run.id, "quality.evaluation-completed", now),
        )

    async def get_result(
        self, context: SecurityContext, project_id: UUID, run_id: UUID
    ) -> QualityResult:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        result = await self._repository.get_result(context.workspace_id, project_id, run_id)
        if result is None:
            raise ScopeViolationError
        return result


def _event(
    context: SecurityContext,
    project_id: UUID,
    aggregate_id: UUID,
    event_type: str,
    now: datetime,
) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        context.workspace_id,
        project_id,
        aggregate_id,
        event_type,
        1,
        {"schema": f"{event_type}.v1", "actor_id": str(context.actor_id)},
        now,
    )
