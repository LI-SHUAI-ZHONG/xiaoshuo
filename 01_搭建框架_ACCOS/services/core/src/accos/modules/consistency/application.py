"""Authorized consistency checks, resolution gates, and projection rebuilds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.modules.consistency.domain import (
    CanonEntry,
    CanonLevel,
    CanonStatus,
    ConsistencyCheckRun,
    Finding,
    FindingStatus,
    ResolutionDecision,
    ResolutionProposal,
    ResolutionStatus,
    ResolutionTrace,
    TargetVersionConflictError,
    TimelineEvent,
    ValidationStatus,
)
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.consistency.domain import FactTarget, ValidationBundle
    from accos.modules.consistency.ports import (
        AuthoritativeEvidenceReader,
        ConsistencyRepository,
        FactRevisionPort,
    )
    from accos.modules.consistency.validators import ValidatorRegistry
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.projects.public import ProjectRepository


@dataclass(frozen=True, slots=True)
class CreateCanonCommand:
    project_id: UUID
    logical_id: UUID
    canon_key: str
    level: CanonLevel
    entry_version: int
    valid_from: datetime
    valid_until: datetime | None
    source_reference: str


@dataclass(frozen=True, slots=True)
class RecordTimelineCommand:
    project_id: UUID
    event_reference: str
    occurred_at: datetime
    sequence: int
    character_state_references: tuple[str, ...] = ()
    world_state_references: tuple[str, ...] = ()
    source_version: int = 1


@dataclass(frozen=True, slots=True)
class RunCheckCommand:
    project_id: UUID
    evidence: ValidationBundle
    validator_keys: tuple[str, ...] = ("structural",)
    workflow_run_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProposeResolutionCommand:
    project_id: UUID
    finding_ids: tuple[UUID, ...]
    strategy_code: str
    target: FactTarget
    impact_references: tuple[str, ...]
    workflow_run_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class DecideResolutionCommand:
    project_id: UUID
    proposal_id: UUID
    decision: ResolutionDecision
    expected_version: int


@dataclass(frozen=True, slots=True)
class ApplyResolutionCommand:
    project_id: UUID
    proposal_id: UUID
    expected_version: int


class ConsistencyAccess:
    """Project-scoped RBAC shared by consistency use cases."""

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
        if permission is not Permission.PROJECT_READ and project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot change consistency state.")
        await self._authorizer.authorize(request)


class ConsistencyService:
    """Persist evidence-derived findings and apply only approved repair proposals."""

    def __init__(
        self,
        repository: ConsistencyRepository,
        access: ConsistencyAccess,
        validators: ValidatorRegistry,
        facts: FactRevisionPort,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._access = access
        self._validators = validators
        self._facts = facts
        self._clock = clock

    async def create_canon(
        self, context: SecurityContext, command: CreateCanonCommand
    ) -> CanonEntry:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if (
            not command.canon_key
            or command.canon_key.strip() != command.canon_key
            or command.entry_version < 1
        ):
            raise ValueError("Canon key and version are invalid")
        if command.valid_until is not None and command.valid_until <= command.valid_from:
            raise ValueError("Canon validity window is invalid")
        now = self._clock.now()
        entry = CanonEntry(
            uuid4(),
            command.logical_id,
            context.workspace_id,
            command.project_id,
            command.canon_key,
            command.level,
            command.entry_version,
            command.valid_from,
            command.valid_until,
            command.source_reference,
            CanonStatus.PROPOSAL,
            context.actor_id,
            now,
        )
        return await self._repository.add_canon(
            entry, _event(context, command.project_id, entry.id, "consistency.canon-proposed", now)
        )

    async def record_timeline(
        self, context: SecurityContext, command: RecordTimelineCommand
    ) -> TimelineEvent:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if command.sequence < 0 or command.source_version < 1:
            raise ValueError("timeline sequence and version are invalid")
        timeline = TimelineEvent(
            uuid4(),
            context.workspace_id,
            command.project_id,
            command.event_reference,
            command.occurred_at,
            command.sequence,
            command.character_state_references,
            command.world_state_references,
            command.source_version,
        )
        return await self._repository.add_timeline(timeline)

    async def run_check(
        self, context: SecurityContext, command: RunCheckCommand
    ) -> tuple[ConsistencyCheckRun, tuple[Finding, ...]]:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_READ)
        if not command.validator_keys or len(set(command.validator_keys)) != len(
            command.validator_keys
        ):
            raise ValueError("validator keys must be non-empty and unique")
        reports = tuple(
            [await self._validators.run(key, command.evidence) for key in command.validator_keys]
        )
        status = _aggregate_status(tuple(report.status for report in reports))
        now = self._clock.now()
        run = ConsistencyCheckRun(
            uuid4(),
            context.workspace_id,
            command.project_id,
            command.workflow_run_id,
            context.actor_id,
            status,
            reports,
            now,
        )
        findings = tuple(
            Finding(
                uuid4(),
                context.workspace_id,
                command.project_id,
                run.id,
                draft.finding_type,
                draft.severity,
                draft.evidence_references,
                draft.message_code,
                report.validator_key,
                report.validator_version,
                FindingStatus.OPEN,
                command.workflow_run_id,
                context.actor_id,
                now,
            )
            for report in reports
            for draft in report.findings
        )
        await self._repository.add_check(
            run,
            findings,
            _event(context, command.project_id, run.id, "consistency.check-completed", now),
        )
        return run, findings

    async def get_check(
        self, context: SecurityContext, project_id: UUID, run_id: UUID
    ) -> ConsistencyCheckRun:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        run = await self._repository.get_check(context.workspace_id, project_id, run_id)
        if run is None:
            raise ScopeViolationError
        return run

    async def get_check_with_findings(
        self, context: SecurityContext, project_id: UUID, run_id: UUID
    ) -> tuple[ConsistencyCheckRun, tuple[Finding, ...]]:
        """Read one check and its durable findings through the same project scope."""
        run = await self.get_check(context, project_id, run_id)
        findings = await self._repository.findings_for_check(
            context.workspace_id, project_id, run_id
        )
        return run, findings

    async def propose_resolution(
        self, context: SecurityContext, command: ProposeResolutionCommand
    ) -> ResolutionProposal:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        if (
            not command.finding_ids
            or len(set(command.finding_ids)) != len(command.finding_ids)
            or not command.strategy_code
            or command.strategy_code.strip() != command.strategy_code
        ):
            raise ValueError("resolution findings and strategy are invalid")
        findings = await self._repository.findings_by_ids(
            context.workspace_id, command.project_id, command.finding_ids
        )
        if len(findings) != len(command.finding_ids):
            raise ScopeViolationError
        now = self._clock.now()
        proposal = ResolutionProposal(
            id=uuid4(),
            workspace_id=context.workspace_id,
            project_id=command.project_id,
            finding_ids=command.finding_ids,
            strategy_code=command.strategy_code,
            target=command.target,
            impact_references=command.impact_references,
            requires_approval=True,
            status=ResolutionStatus.PROPOSED,
            requested_by=context.actor_id,
            workflow_run_id=command.workflow_run_id,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.add_resolution(
            proposal,
            _event(
                context,
                command.project_id,
                proposal.id,
                "consistency.resolution-proposed",
                now,
            ),
        )

    async def decide_resolution(
        self, context: SecurityContext, command: DecideResolutionCommand
    ) -> ResolutionProposal:
        await self._access.authorize(context, command.project_id, Permission.APPROVAL_DECIDE)
        now = self._clock.now()
        return await self._repository.decide_resolution(
            context.workspace_id,
            command.project_id,
            command.proposal_id,
            decision=command.decision,
            expected_version=command.expected_version,
            actor_id=context.actor_id,
            event=_event(
                context,
                command.project_id,
                command.proposal_id,
                "consistency.resolution-decided",
                now,
            ),
        )

    async def apply_resolution(
        self, context: SecurityContext, command: ApplyResolutionCommand
    ) -> ResolutionProposal:
        await self._access.authorize(context, command.project_id, Permission.PROJECT_WRITE)
        proposal = await self._repository.get_resolution(
            context.workspace_id, command.project_id, command.proposal_id
        )
        if proposal is None:
            raise ScopeViolationError
        current_version = await self._facts.current_version(
            context, command.project_id, proposal.target
        )
        if current_version != proposal.target.expected_version:
            raise TargetVersionConflictError(current_version)
        if proposal.status is not ResolutionStatus.APPROVED:
            raise InvalidStateError("Only approved resolutions can be applied.")
        claimed = await self._repository.claim_resolution(
            context.workspace_id,
            command.project_id,
            command.proposal_id,
            expected_version=command.expected_version,
            actor_id=context.actor_id,
        )
        result = await self._facts.apply(
            context, command.project_id, claimed.target, claimed.reference
        )
        now = self._clock.now()
        return await self._repository.finish_resolution(
            context.workspace_id,
            command.project_id,
            command.proposal_id,
            expected_version=claimed.version,
            result=result,
            event=_event(
                context,
                command.project_id,
                command.proposal_id,
                "consistency.resolution-applied",
                now,
                {"result_reference": result.reference, "result_version": result.version},
            ),
        )

    async def trace(
        self, context: SecurityContext, project_id: UUID, proposal_id: UUID
    ) -> ResolutionTrace:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        proposal = await self._repository.get_resolution(
            context.workspace_id, project_id, proposal_id
        )
        if proposal is None:
            raise ScopeViolationError
        findings = await self._repository.findings_by_ids(
            context.workspace_id, project_id, proposal.finding_ids
        )
        return ResolutionTrace(proposal, findings)


class ProjectionRebuilder:
    """Rebuild disposable pointers through an authoritative read port only."""

    def __init__(
        self,
        repository: ConsistencyRepository,
        reader: AuthoritativeEvidenceReader,
    ) -> None:
        self._repository = repository
        self._reader = reader

    async def rebuild(self, context: SecurityContext, project_id: UUID) -> tuple[object, ...]:
        entries = await self._reader.read_project(context, project_id)
        await self._repository.replace_projection(context.workspace_id, project_id, entries)
        return entries


def _aggregate_status(statuses: tuple[ValidationStatus, ...]) -> ValidationStatus:
    for status in (
        ValidationStatus.RUN_FAILED,
        ValidationStatus.FINDINGS,
        ValidationStatus.NOT_CONFIGURED,
        ValidationStatus.NOT_RUN,
    ):
        if status in statuses:
            return status
    return ValidationStatus.PASSED


def _event(  # noqa: PLR0913, PLR0917
    context: SecurityContext,
    project_id: UUID,
    aggregate_id: UUID,
    event_type: str,
    now: datetime,
    payload: dict[str, object] | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        context.workspace_id,
        project_id,
        aggregate_id,
        event_type,
        1,
        {
            "schema": f"{event_type}.v1",
            "actor_id": str(context.actor_id),
            **(payload or {}),
        },
        now,
    )
