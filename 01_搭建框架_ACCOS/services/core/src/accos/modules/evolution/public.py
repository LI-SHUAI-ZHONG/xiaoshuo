"""Stable public controlled-evolution proposal API."""

from accos.modules.evolution.application import EvolutionAccess, EvolutionService
from accos.modules.evolution.components import (
    DeterministicAnalyzer,
    DiagnosticObserver,
    DryRunSimulationEnvironment,
    ImmutableSafetyController,
    ProposalPlanner,
    ReadOnlyVersionManager,
)
from accos.modules.evolution.domain import (
    Analysis,
    ChangeAction,
    EvolutionAuditEntry,
    EvolutionDecision,
    EvolutionState,
    EvolutionStateMachine,
    ImprovementPlan,
    ImprovementProposal,
    Observation,
    SafetyDecision,
    SimulationEvidence,
)
from accos.modules.evolution.ports import (
    Analyzer,
    EvolutionMemory,
    Observer,
    Planner,
    SafetyController,
    SimulationEnvironment,
    VersionManager,
)

__all__ = [
    "Analysis",
    "Analyzer",
    "ChangeAction",
    "DeterministicAnalyzer",
    "DiagnosticObserver",
    "DryRunSimulationEnvironment",
    "EvolutionAccess",
    "EvolutionAuditEntry",
    "EvolutionDecision",
    "EvolutionMemory",
    "EvolutionService",
    "EvolutionState",
    "EvolutionStateMachine",
    "ImmutableSafetyController",
    "ImprovementPlan",
    "ImprovementProposal",
    "Observation",
    "Observer",
    "Planner",
    "ProposalPlanner",
    "ReadOnlyVersionManager",
    "SafetyController",
    "SafetyDecision",
    "SimulationEnvironment",
    "SimulationEvidence",
    "VersionManager",
]
