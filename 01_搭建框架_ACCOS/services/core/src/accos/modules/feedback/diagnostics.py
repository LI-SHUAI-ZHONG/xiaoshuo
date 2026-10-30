"""Read-only deterministic System Doctor rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from accos.modules.feedback.domain import DiagnosticFinding, DiagnosticSeverity

if TYPE_CHECKING:
    from datetime import datetime

    from accos.modules.feedback.domain import MetricPoint


@dataclass(frozen=True, slots=True)
class DiagnosticRule:
    key: str
    version: str
    metric_name: str
    required_dimensions: tuple[tuple[str, str], ...]
    threshold: float
    finding_code: str
    severity: DiagnosticSeverity


def default_diagnostic_rules() -> tuple[DiagnosticRule, ...]:
    return (
        DiagnosticRule(
            "agent-failure",
            "1.0.0",
            "agent.outcome",
            (("status", "failure"),),
            1.0,
            "agent_execution_failed",
            DiagnosticSeverity.ERROR,
        ),
        DiagnosticRule(
            "agent-latency",
            "1.0.0",
            "agent.latency_ms",
            (),
            30_000.0,
            "agent_latency_high",
            DiagnosticSeverity.WARNING,
        ),
        DiagnosticRule(
            "agent-budget",
            "1.0.0",
            "agent.budget_utilization",
            (),
            1.0,
            "agent_budget_exhausted",
            DiagnosticSeverity.ERROR,
        ),
        DiagnosticRule(
            "memory-recall",
            "1.0.0",
            "memory.recall_status",
            (("status", "failure"),),
            1.0,
            "memory_recall_failed",
            DiagnosticSeverity.ERROR,
        ),
        DiagnosticRule(
            "workflow-failure",
            "1.0.0",
            "workflow.outcome",
            (("status", "failed"),),
            1.0,
            "workflow_failed",
            DiagnosticSeverity.ERROR,
        ),
        DiagnosticRule(
            "runtime-unhealthy",
            "1.0.0",
            "runtime.health",
            (("status", "unhealthy"),),
            1.0,
            "runtime_component_unhealthy",
            DiagnosticSeverity.CRITICAL,
        ),
    )


class SystemDoctor:
    """Inspect metric points and return findings; no mutation port is held."""

    def __init__(self, rules: tuple[DiagnosticRule, ...]) -> None:
        self._rules = rules

    def inspect(self, point: MetricPoint, now: datetime) -> tuple[DiagnosticFinding, ...]:
        dimensions = dict(point.dimensions)
        return tuple(
            DiagnosticFinding(
                uuid5(NAMESPACE_URL, f"accos:{point.id}:{rule.key}:{rule.version}"),
                point.workspace_id,
                point.project_id,
                point.id,
                rule.key,
                rule.version,
                rule.finding_code,
                rule.severity,
                point.value,
                rule.threshold,
                now,
            )
            for rule in self._rules
            if point.included
            and rule.metric_name == point.metric_name
            and point.value >= rule.threshold
            and all(dimensions.get(key) == value for key, value in rule.required_dimensions)
        )
