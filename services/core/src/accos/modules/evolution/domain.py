"""Framework-free controlled evolution contracts and state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from accos.kernel.errors import InvalidStateError

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class EvolutionState(StrEnum):
    OBSERVED = "observed"
    PROPOSED = "proposed"
    SIMULATED = "simulated"
    EVALUATED = "evaluated"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXTERNALLY_DEPLOYED = "externally_deployed"
    VERIFIED = "verified"
    ROLLED_BACK = "rolled_back"


class EvolutionDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ChangeAction(StrEnum):
    """Safe suggestions and immutable high-risk rejection categories."""

    SUGGEST_MODEL_ROUTING = "suggest-model-routing"
    SUGGEST_PROMPT = "suggest-prompt"
    SUGGEST_WORKFLOW = "suggest-workflow"
    SUGGEST_CONFIGURATION = "suggest-configuration"
    CHANGE_OWNERSHIP = "change-ownership"
    DISABLE_SAFETY = "disable-safety"
    ELEVATE_PERMISSION = "elevate-permission"
    BYPASS_APPROVAL = "bypass-approval"
    AUTO_COMMIT_CODE = "auto-commit-code"
    AUTO_DEPLOY = "auto-deploy"
    UNMIGRATED_SCHEMA = "unmigrated-schema"


@dataclass(frozen=True, slots=True)
class Observation:
    finding_id: UUID
    input_references: tuple[str, ...]
    observer_key: str
    observer_version: str


@dataclass(frozen=True, slots=True)
class Analysis:
    analysis_code: str
    analyzer_key: str
    analyzer_version: str


@dataclass(frozen=True, slots=True)
class ImprovementPlan:
    action: ChangeAction
    change_reference: str
    rollback_reference: str
    planner_key: str
    planner_version: str


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    allowed: bool
    policy_version: str
    rule_code: str


@dataclass(frozen=True, slots=True)
class SimulationEvidence:
    reference: str
    environment_key: str
    environment_version: str
    outcome_code: str


@dataclass(frozen=True, slots=True)
class ImprovementProposal:
    """Auditable suggestion; it contains no executable mutation capability."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    diagnostic_finding_ids: tuple[UUID, ...]
    input_references: tuple[str, ...]
    algorithm_versions: tuple[str, ...]
    state: EvolutionState
    requested_by: UUID
    created_at: datetime
    updated_at: datetime
    action: ChangeAction | None = None
    change_reference: str | None = None
    safety_policy_version: str | None = None
    safety_rule_code: str | None = None
    simulation_evidence: tuple[str, ...] = ()
    evaluation_code: str | None = None
    approved_by: UUID | None = None
    rollback_reference: str | None = None
    version: int = 1
    approval_policy_ref: str = "legacy_dual_control"

    @property
    def reference(self) -> str:
        return f"improvement-proposal://{self.id}"


@dataclass(frozen=True, slots=True)
class EvolutionAuditEntry:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    proposal_id: UUID
    from_state: EvolutionState | None
    to_state: EvolutionState
    actor_id: UUID
    algorithm_versions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    rollback_reference: str | None
    reason_code: str
    occurred_at: datetime


class EvolutionStateMachine:
    """The full state graph; application services expose no deployment transition."""

    _ALLOWED: ClassVar[dict[EvolutionState, frozenset[EvolutionState]]] = {
        EvolutionState.OBSERVED: frozenset({EvolutionState.PROPOSED, EvolutionState.REJECTED}),
        EvolutionState.PROPOSED: frozenset({EvolutionState.SIMULATED, EvolutionState.REJECTED}),
        EvolutionState.SIMULATED: frozenset({EvolutionState.EVALUATED, EvolutionState.REJECTED}),
        EvolutionState.EVALUATED: frozenset(
            {EvolutionState.AWAITING_APPROVAL, EvolutionState.REJECTED}
        ),
        EvolutionState.AWAITING_APPROVAL: frozenset(
            {EvolutionState.APPROVED, EvolutionState.REJECTED}
        ),
        EvolutionState.APPROVED: frozenset({EvolutionState.EXTERNALLY_DEPLOYED}),
        EvolutionState.EXTERNALLY_DEPLOYED: frozenset(
            {EvolutionState.VERIFIED, EvolutionState.ROLLED_BACK}
        ),
        EvolutionState.REJECTED: frozenset(),
        EvolutionState.VERIFIED: frozenset(),
        EvolutionState.ROLLED_BACK: frozenset(),
    }

    def require(self, current: EvolutionState, target: EvolutionState) -> None:
        if target not in self._ALLOWED[current]:
            raise InvalidStateError(
                f"Evolution transition {current.value} -> {target.value} is not allowed."
            )
