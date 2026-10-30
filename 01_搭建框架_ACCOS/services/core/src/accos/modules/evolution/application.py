"""Authorized proposal lifecycle capped at human approval."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.errors import InvalidStateError, PermissionDeniedError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.kernel.security import ActorKind
from accos.modules.evolution.domain import (
    ChangeAction,
    EvolutionAuditEntry,
    EvolutionDecision,
    EvolutionState,
    EvolutionStateMachine,
    ImprovementProposal,
    Observation,
    SimulationEvidence,
)
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.evolution.ports import (
        Analyzer,
        EvolutionMemory,
        Observer,
        Planner,
        SafetyController,
        SimulationEnvironment,
        VersionManager,
    )
    from accos.modules.feedback.public import DiagnosticFinding
    from accos.modules.identity.public import ApprovalPolicyPort, AuthorizationService
    from accos.modules.projects.public import ProjectRepository

_REFERENCE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]{1,470}$")


class EvolutionAccess:
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
            raise InvalidStateError("Archived projects cannot change evolution proposals.")
        await self._authorizer.authorize(request)


class EvolutionService:
    """Coordinate read-only analysis and persist suggestions, never apply them."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        memory: EvolutionMemory,
        access: EvolutionAccess,
        observer: Observer,
        analyzer: Analyzer,
        planner: Planner,
        simulation: SimulationEnvironment,
        versions: VersionManager,
        safety: SafetyController,
        clock: Clock,
        approval_policies: ApprovalPolicyPort | None = None,
    ) -> None:
        self._memory = memory
        self._access = access
        self._observer = observer
        self._analyzer = analyzer
        self._planner = planner
        self._simulation = simulation
        self._versions = versions
        self._safety = safety
        self._clock = clock
        self._approval_policies = approval_policies
        self._states = EvolutionStateMachine()

    async def observe(
        self, context: SecurityContext, project_id: UUID, finding: DiagnosticFinding
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        if (finding.workspace_id, finding.project_id) != (context.workspace_id, project_id):
            raise ScopeViolationError
        observation = self._observer.observe(finding)
        now = self._clock.now()
        proposal = ImprovementProposal(
            uuid4(),
            context.workspace_id,
            project_id,
            (finding.id,),
            observation.input_references,
            (f"observer:{observation.observer_key}@{observation.observer_version}",),
            EvolutionState.OBSERVED,
            context.actor_id,
            now,
            now,
            approval_policy_ref=(await self._approval_policies.snapshot(context.workspace_id))
            if self._approval_policies
            else "legacy_dual_control",
        )
        audit = _audit(context, proposal, None, EvolutionState.OBSERVED, "finding-observed", now)
        return await self._memory.add(
            proposal,
            audit,
            _event(context, project_id, proposal.id, "evolution.observed", now),
        )

    async def propose(  # noqa: PLR0913, PLR0917
        self,
        context: SecurityContext,
        project_id: UUID,
        proposal_id: UUID,
        expected_version: int,
        action: ChangeAction,
        change_reference: str,
        rollback_reference: str,
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        if (
            _REFERENCE.fullmatch(change_reference) is None
            or _REFERENCE.fullmatch(rollback_reference) is None
        ):
            raise ValueError("proposal change and rollback references must be opaque URIs")
        proposal = await self._require(context, project_id, proposal_id)
        observation = Observation(
            proposal.diagnostic_finding_ids[0],
            proposal.input_references,
            self._observer.key,
            self._observer.version,
        )
        analysis = self._analyzer.analyze(observation)
        plan = self._planner.plan(analysis, action, change_reference, rollback_reference)
        safety = self._safety.review(plan)
        target = EvolutionState.PROPOSED if safety.allowed else EvolutionState.REJECTED
        self._states.require(proposal.state, target)
        now = self._clock.now()
        algorithms = (
            *proposal.algorithm_versions,
            f"analyzer:{analysis.analyzer_key}@{analysis.analyzer_version}",
            f"planner:{plan.planner_key}@{plan.planner_version}",
            *self._versions.snapshot(plan),
        )
        updated = replace(
            proposal,
            state=target,
            action=plan.action,
            change_reference=plan.change_reference,
            rollback_reference=plan.rollback_reference,
            safety_policy_version=safety.policy_version,
            safety_rule_code=safety.rule_code,
            algorithm_versions=algorithms,
            updated_at=now,
            version=proposal.version + 1,
        )
        return await self._transition(
            context, proposal, updated, expected_version, safety.rule_code, now
        )

    async def simulate(
        self,
        context: SecurityContext,
        project_id: UUID,
        proposal_id: UUID,
        expected_version: int,
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        proposal = await self._require(context, project_id, proposal_id)
        self._states.require(proposal.state, EvolutionState.SIMULATED)
        if (
            proposal.action is None
            or proposal.change_reference is None
            or proposal.rollback_reference is None
        ):
            raise InvalidStateError("Proposed improvement has no complete plan.")
        analysis = self._analyzer.analyze(
            Observation(
                proposal.diagnostic_finding_ids[0],
                proposal.input_references,
                self._observer.key,
                self._observer.version,
            )
        )
        plan = self._planner.plan(
            analysis, proposal.action, proposal.change_reference, proposal.rollback_reference
        )
        evidence = await self._simulation.simulate(proposal.id, plan)
        now = self._clock.now()
        updated = replace(
            proposal,
            state=EvolutionState.SIMULATED,
            simulation_evidence=(evidence.reference,),
            algorithm_versions=(
                *proposal.algorithm_versions,
                f"simulation:{evidence.environment_key}@{evidence.environment_version}",
            ),
            updated_at=now,
            version=proposal.version + 1,
        )
        return await self._transition(
            context, proposal, updated, expected_version, evidence.outcome_code, now
        )

    async def evaluate(
        self,
        context: SecurityContext,
        project_id: UUID,
        proposal_id: UUID,
        expected_version: int,
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        proposal = await self._require(context, project_id, proposal_id)
        self._states.require(proposal.state, EvolutionState.EVALUATED)
        if not proposal.simulation_evidence:
            raise InvalidStateError("Simulation evidence is required before evaluation.")
        evidence = SimulationEvidence(
            proposal.simulation_evidence[0],
            self._simulation.key,
            self._simulation.version,
            "dry-run-passed",
        )
        result = self._analyzer.evaluate(evidence)
        now = self._clock.now()
        updated = replace(
            proposal,
            state=EvolutionState.EVALUATED,
            evaluation_code=result,
            updated_at=now,
            version=proposal.version + 1,
        )
        return await self._transition(context, proposal, updated, expected_version, result, now)

    async def request_approval(
        self,
        context: SecurityContext,
        project_id: UUID,
        proposal_id: UUID,
        expected_version: int,
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        proposal = await self._require(context, project_id, proposal_id)
        self._states.require(proposal.state, EvolutionState.AWAITING_APPROVAL)
        now = self._clock.now()
        updated = replace(
            proposal,
            state=EvolutionState.AWAITING_APPROVAL,
            updated_at=now,
            version=proposal.version + 1,
        )
        return await self._transition(
            context, proposal, updated, expected_version, "human-approval-required", now
        )

    async def decide(
        self,
        context: SecurityContext,
        project_id: UUID,
        proposal_id: UUID,
        expected_version: int,
        decision: EvolutionDecision,
    ) -> ImprovementProposal:
        await self._access.authorize(context, project_id, Permission.APPROVAL_DECIDE)
        proposal = await self._require(context, project_id, proposal_id)
        if self._approval_policies is not None:
            await self._approval_policies.require_decision(
                context, proposal.requested_by, proposal.approval_policy_ref
            )
        elif context.actor_kind is not ActorKind.USER or context.actor_id == proposal.requested_by:
            raise PermissionDeniedError
        target = (
            EvolutionState.APPROVED
            if decision is EvolutionDecision.APPROVE
            else EvolutionState.REJECTED
        )
        self._states.require(proposal.state, target)
        now = self._clock.now()
        updated = replace(
            proposal,
            state=target,
            approved_by=context.actor_id if target is EvolutionState.APPROVED else None,
            updated_at=now,
            version=proposal.version + 1,
        )
        return await self._transition(
            context, proposal, updated, expected_version, f"human-{decision.value}", now
        )

    async def get(
        self, context: SecurityContext, project_id: UUID, proposal_id: UUID
    ) -> ImprovementProposal:
        """Read a proposal through the project authorization boundary."""
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        return await self._require(context, project_id, proposal_id)

    async def _require(
        self, context: SecurityContext, project_id: UUID, proposal_id: UUID
    ) -> ImprovementProposal:
        proposal = await self._memory.get(context.workspace_id, project_id, proposal_id)
        if proposal is None:
            raise ScopeViolationError
        return proposal

    async def _transition(  # noqa: PLR0913, PLR0917
        self,
        context: SecurityContext,
        before: ImprovementProposal,
        after: ImprovementProposal,
        expected_version: int,
        reason: str,
        now: datetime,
    ) -> ImprovementProposal:
        audit = _audit(context, after, before.state, after.state, reason, now)
        return await self._memory.transition(
            after,
            expected_version,
            audit,
            _event(context, after.project_id, after.id, f"evolution.{after.state.value}", now),
        )


def _audit(  # noqa: PLR0913, PLR0917
    context: SecurityContext,
    proposal: ImprovementProposal,
    from_state: EvolutionState | None,
    to_state: EvolutionState,
    reason: str,
    now: datetime,
) -> EvolutionAuditEntry:
    return EvolutionAuditEntry(
        uuid4(),
        proposal.workspace_id,
        proposal.project_id,
        proposal.id,
        from_state,
        to_state,
        context.actor_id,
        proposal.algorithm_versions,
        proposal.input_references + proposal.simulation_evidence,
        proposal.rollback_reference,
        reason,
        now,
    )


def _event(
    context: SecurityContext,
    project_id: UUID,
    proposal_id: UUID,
    event_type: str,
    now: datetime,
) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        context.workspace_id,
        project_id,
        proposal_id,
        event_type,
        1,
        {"schema": f"{event_type}.v1", "actor_id": str(context.actor_id)},
        now,
    )
