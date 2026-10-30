"""Deterministic, offline implementations of the evolution component ports."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, cast
from uuid import NAMESPACE_URL, uuid5

from accos.modules.evolution.domain import (
    Analysis,
    ChangeAction,
    ImprovementPlan,
    Observation,
    SafetyDecision,
    SimulationEvidence,
)

if TYPE_CHECKING:
    from uuid import UUID

    from accos.modules.feedback.public import DiagnosticFinding


class DiagnosticObserver:
    key = "diagnostic-observer"
    version = "1.0.0"

    def observe(self, finding: DiagnosticFinding) -> Observation:
        return Observation(
            finding.id,
            (finding.reference, f"metric-point://{finding.metric_point_id}"),
            self.key,
            self.version,
        )


class DeterministicAnalyzer:
    key = "deterministic-analyzer"
    version = "1.0.0"

    def analyze(self, observation: Observation) -> Analysis:
        del observation
        return Analysis("technical-fault-observed", self.key, self.version)

    def evaluate(self, evidence: SimulationEvidence) -> str:
        return (
            "simulation-evaluated"
            if evidence.outcome_code == "dry-run-passed"
            else "simulation-rejected"
        )


class ProposalPlanner:
    key = "proposal-planner"
    version = "1.0.0"

    def plan(
        self,
        analysis: Analysis,
        action: object,
        change_reference: str,
        rollback_reference: str,
    ) -> ImprovementPlan:
        del analysis
        return ImprovementPlan(
            cast("ChangeAction", action),
            change_reference,
            rollback_reference,
            self.key,
            self.version,
        )


class DryRunSimulationEnvironment:
    """Produce deterministic evidence without writing files, code, or configuration."""

    key = "offline-dry-run"
    version = "1.0.0"

    async def simulate(self, proposal_id: UUID, plan: ImprovementPlan) -> SimulationEvidence:
        reference = uuid5(NAMESPACE_URL, f"accos:{proposal_id}:{plan.action.value}")
        return SimulationEvidence(
            f"simulation-evidence://{reference}", self.key, self.version, "dry-run-passed"
        )


class ReadOnlyVersionManager:
    """Return immutable version pointers; there is no commit or deployment method."""

    version = "1.0.0"

    def snapshot(self, plan: ImprovementPlan) -> tuple[str, ...]:
        return (f"planner:{plan.planner_key}@{plan.planner_version}", f"versions@{self.version}")


_FORBIDDEN_RULES = MappingProxyType(
    {
        ChangeAction.CHANGE_OWNERSHIP: "immutable-no-ownership-change",
        ChangeAction.DISABLE_SAFETY: "immutable-no-safety-disable",
        ChangeAction.ELEVATE_PERMISSION: "immutable-no-permission-escalation",
        ChangeAction.BYPASS_APPROVAL: "immutable-no-approval-bypass",
        ChangeAction.AUTO_COMMIT_CODE: "immutable-no-auto-commit",
        ChangeAction.AUTO_DEPLOY: "immutable-no-auto-deploy",
        ChangeAction.UNMIGRATED_SCHEMA: "immutable-no-unmigrated-schema",
    }
)


class ImmutableSafetyController:
    policy_version = "evolution-safety-v1"

    def review(self, plan: ImprovementPlan) -> SafetyDecision:
        rule = _FORBIDDEN_RULES.get(plan.action)
        return SafetyDecision(
            rule is None,
            self.policy_version,
            "immutable-policy-allow" if rule is None else rule,
        )
