"""Read, analysis, planning, simulation, safety, version, and memory ports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.modules.evolution.domain import (
        Analysis,
        EvolutionAuditEntry,
        ImprovementPlan,
        ImprovementProposal,
        Observation,
        SafetyDecision,
        SimulationEvidence,
    )
    from accos.modules.feedback.public import DiagnosticFinding


class Observer(Protocol):
    key: str
    version: str

    def observe(self, finding: DiagnosticFinding) -> Observation: ...


class Analyzer(Protocol):
    key: str
    version: str

    def analyze(self, observation: Observation) -> Analysis: ...

    def evaluate(self, evidence: SimulationEvidence) -> str: ...


class Planner(Protocol):
    key: str
    version: str

    def plan(
        self,
        analysis: Analysis,
        action: object,
        change_reference: str,
        rollback_reference: str,
    ) -> ImprovementPlan: ...


class SimulationEnvironment(Protocol):
    key: str
    version: str

    async def simulate(self, proposal_id: UUID, plan: ImprovementPlan) -> SimulationEvidence: ...


class VersionManager(Protocol):
    version: str

    def snapshot(self, plan: ImprovementPlan) -> tuple[str, ...]: ...


class SafetyController(Protocol):
    policy_version: str

    def review(self, plan: ImprovementPlan) -> SafetyDecision: ...


class EvolutionMemory(Protocol):
    async def add(
        self,
        proposal: ImprovementProposal,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal: ...

    async def get(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ImprovementProposal | None: ...

    async def transition(
        self,
        proposal: ImprovementProposal,
        expected_version: int,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal: ...
