"""Finite-cardinality metric registry and built-in technical metrics."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from accos.modules.feedback.domain import MetricDefinition, MetricDimension, MetricSensitivity

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,99}$")
_FORBIDDEN_DIMENSIONS = frozenset(
    {
        "actor_id",
        "content",
        "correlation_id",
        "document_id",
        "object_id",
        "project_id",
        "prompt",
        "request_id",
        "secret",
        "user_id",
        "workspace_id",
    }
)
MAX_DIMENSIONS = 4
MAX_VALUES_PER_DIMENSION = 32
MAX_RETENTION_DAYS = 400


class MetricRegistry:
    """Register immutable metric schemas and validate every emitted point."""

    def __init__(self) -> None:
        self._definitions: dict[str, MetricDefinition] = {}

    def register(self, definition: MetricDefinition) -> None:
        _validate_definition(definition)
        existing = self._definitions.get(definition.name)
        if existing is not None and existing != definition:
            raise ValueError("metric definition is immutable")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> MetricDefinition | None:
        return self._definitions.get(name)

    def all(self) -> tuple[MetricDefinition, ...]:
        return tuple(self._definitions[name] for name in sorted(self._definitions))

    def validate_point(
        self, name: str, value: float, dimensions: tuple[tuple[str, str], ...]
    ) -> MetricDefinition:
        definition = self.get(name)
        if definition is None:
            raise ValueError("metric is not registered")
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")
        supplied = dict(dimensions)
        if len(supplied) != len(dimensions):
            raise ValueError("metric dimensions must be unique")
        expected = {item.key: item.allowed_values for item in definition.dimensions}
        if supplied.keys() != expected.keys() or any(
            supplied[key] not in allowed for key, allowed in expected.items()
        ):
            raise ValueError("metric dimensions violate the registered finite vocabulary")
        return definition


def default_metric_definitions(
    workspace_id: UUID, project_id: UUID, actor_id: UUID, now: datetime
) -> tuple[MetricDefinition, ...]:
    """Return the first-release Agent/Memory/Workflow/runtime metric registry."""
    specs = (
        ("agent.outcome", "count", (MetricDimension("status", ("success", "failure")),)),
        ("agent.latency_ms", "milliseconds", ()),
        (
            "agent.budget_utilization",
            "ratio",
            (
                MetricDimension(
                    "resource", ("steps", "model-calls", "tool-calls", "time", "tokens")
                ),
            ),
        ),
        (
            "memory.recall_status",
            "count",
            (MetricDimension("status", ("hit", "miss", "not-configured", "failure")),),
        ),
        (
            "workflow.outcome",
            "count",
            (MetricDimension("status", ("completed", "failed", "recovered")),),
        ),
        (
            "runtime.health",
            "count",
            (
                MetricDimension("component", ("api", "worker")),
                MetricDimension("status", ("healthy", "degraded", "unhealthy")),
            ),
        ),
    )
    return tuple(
        MetricDefinition(
            uuid5(NAMESPACE_URL, f"accos:{workspace_id}:{project_id}:{name}:v1"),
            workspace_id,
            project_id,
            name,
            1,
            unit,
            dimensions,
            30,
            MetricSensitivity.INTERNAL,
            actor_id,
            now,
        )
        for name, unit, dimensions in specs
    )


def _validate_definition(definition: MetricDefinition) -> None:
    if (
        _CODE.fullmatch(definition.name) is None
        or _CODE.fullmatch(definition.unit) is None
        or definition.version < 1
        or not 1 <= definition.retention_days <= MAX_RETENTION_DAYS
        or len(definition.dimensions) > MAX_DIMENSIONS
    ):
        raise ValueError("metric definition metadata is invalid")
    keys = [dimension.key for dimension in definition.dimensions]
    if len(set(keys)) != len(keys):
        raise ValueError("metric dimension keys must be unique")
    for dimension in definition.dimensions:
        if (
            _CODE.fullmatch(dimension.key) is None
            or dimension.key in _FORBIDDEN_DIMENSIONS
            or not 1 <= len(dimension.allowed_values) <= MAX_VALUES_PER_DIMENSION
            or len(set(dimension.allowed_values)) != len(dimension.allowed_values)
            or any(_CODE.fullmatch(value) is None for value in dimension.allowed_values)
        ):
            raise ValueError("metric dimension must use a bounded safe vocabulary")
