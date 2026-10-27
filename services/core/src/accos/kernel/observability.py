"""Low-cardinality metrics, trace records, and exporter-neutral telemetry ports."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from types import MappingProxyType
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_./:{}-]{1,120}$")
_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_TRACE_ID_LENGTH = 32
_SPAN_ID_LENGTH = 16
_FORBIDDEN_LABEL_PARTS = frozenset(
    {
        "actor",
        "content",
        "correlation",
        "memory",
        "object_id",
        "project",
        "prompt",
        "request",
        "secret",
        "token",
        "trace",
        "user",
        "workspace",
    }
)


class MetricKind(StrEnum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """One bounded metric family and its exact low-cardinality dimensions."""

    name: str
    description: str
    kind: MetricKind
    label_names: tuple[str, ...] = ()
    buckets: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if _METRIC_NAME.fullmatch(self.name) is None or not self.description:
            raise ValueError("metric definition name or description is invalid")
        if len(set(self.label_names)) != len(self.label_names) or any(
            any(part in name.lower() for part in _FORBIDDEN_LABEL_PARTS)
            for name in self.label_names
        ):
            raise ValueError("metric labels must be unique and low-cardinality")
        if self.kind is MetricKind.HISTOGRAM:
            if not self.buckets or tuple(sorted(set(self.buckets))) != self.buckets:
                raise ValueError("histogram buckets must be unique and increasing")
        elif self.buckets:
            raise ValueError("only histograms may define buckets")


_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
DEFAULT_METRICS = (
    MetricDefinition(
        "accos_api_requests_total",
        "Completed API requests.",
        MetricKind.COUNTER,
        ("method", "route", "status_class", "outcome"),
    ),
    MetricDefinition(
        "accos_api_request_duration_seconds",
        "API request duration in seconds.",
        MetricKind.HISTOGRAM,
        ("method", "route"),
        _LATENCY_BUCKETS,
    ),
    MetricDefinition(
        "accos_worker_heartbeat",
        "Worker heartbeat state (one for the current state).",
        MetricKind.GAUGE,
        ("state",),
    ),
    MetricDefinition(
        "accos_worker_queue_events_total",
        "Worker queue outcomes.",
        MetricKind.COUNTER,
        ("outcome",),
    ),
    MetricDefinition(
        "accos_worker_lease_events_total",
        "Worker lease and relay outcomes.",
        MetricKind.COUNTER,
        ("outcome",),
    ),
    MetricDefinition(
        "accos_workflow_runs",
        "Current workflow runs by bounded status.",
        MetricKind.GAUGE,
        ("status",),
    ),
    MetricDefinition(
        "accos_outbox_backlog",
        "Unpublished durable Outbox records.",
        MetricKind.GAUGE,
    ),
    MetricDefinition(
        "accos_outbox_oldest_age_seconds",
        "Age of the oldest unpublished Outbox record.",
        MetricKind.GAUGE,
    ),
    MetricDefinition(
        "accos_model_calls",
        "Persisted model calls by provider and outcome.",
        MetricKind.GAUGE,
        ("provider", "outcome"),
    ),
    MetricDefinition(
        "accos_model_tokens",
        "Persisted model token usage by provider and direction.",
        MetricKind.GAUGE,
        ("provider", "direction"),
    ),
    MetricDefinition(
        "accos_database_pool_connections",
        "Database pool connections by state.",
        MetricKind.GAUGE,
        ("state",),
    ),
    MetricDefinition(
        "accos_knowledge_ingestions",
        "Current knowledge ingestion runs by bounded status.",
        MetricKind.GAUGE,
        ("status",),
    ),
    MetricDefinition(
        "accos_sse_connections",
        "Active server-sent event streams.",
        MetricKind.GAUGE,
    ),
    MetricDefinition(
        "accos_object_storage_operations_total",
        "Object storage outcomes.",
        MetricKind.COUNTER,
        ("operation", "outcome"),
    ),
    MetricDefinition(
        "accos_telemetry_exports_total",
        "Optional OTLP export outcomes.",
        MetricKind.COUNTER,
        ("signal", "outcome"),
    ),
)


@dataclass(frozen=True, slots=True)
class MetricPoint:
    """One exporter-neutral metric update, never carrying business identifiers."""

    name: str
    kind: MetricKind
    value: float
    labels: tuple[tuple[str, str], ...]
    timestamp_unix_nano: int


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """Minimal OpenTelemetry-compatible span payload with bounded attributes."""

    name: str
    trace_id: str
    span_id: str
    start_unix_nano: int
    end_unix_nano: int
    outcome: str
    attributes: tuple[tuple[str, str | int | float | bool], ...]


class TelemetryExporter(Protocol):
    """Optional OTLP adapter port. Disabled exporters must remain harmless."""

    def enqueue_metric(self, point: MetricPoint) -> None: ...

    def enqueue_span(self, span: SpanRecord) -> None: ...

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...


class RuntimeBoundaryState(StrEnum):
    ACTIVE = "active"
    NOT_STARTED = "not_started"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class WorkerRuntimeSnapshot:
    state: RuntimeBoundaryState
    detail: str
    last_seen_at: datetime | None


@dataclass(frozen=True, slots=True)
class OutboxRuntimeSnapshot:
    state: RuntimeBoundaryState
    detail: str
    backlog: int | None
    oldest_age_seconds: float | None


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    worker: WorkerRuntimeSnapshot
    outbox: OutboxRuntimeSnapshot


class RuntimeMonitor(Protocol):
    """Cross-process heartbeat and persistent operational projection port."""

    async def heartbeat(self) -> None: ...

    async def snapshot(self) -> RuntimeSnapshot: ...

    async def refresh_metrics(self, telemetry: TelemetryRuntime) -> RuntimeSnapshot: ...


class NullTelemetryExporter:
    """No-op default that performs no I/O and cannot affect readiness."""

    def enqueue_metric(self, point: MetricPoint) -> None:
        del point

    def enqueue_span(self, span: SpanRecord) -> None:
        del span

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None


@dataclass(slots=True)
class _Histogram:
    bucket_counts: list[int]
    count: int = 0
    total: float = 0.0


class MetricRegistry:
    """Thread-safe registry with an explicit schema and Prometheus exposition."""

    def __init__(self, definitions: tuple[MetricDefinition, ...] = DEFAULT_METRICS) -> None:
        if len({item.name for item in definitions}) != len(definitions):
            raise ValueError("metric definitions must be unique")
        self._definitions = MappingProxyType({item.name: item for item in definitions})
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], _Histogram] = {}
        self._lock = Lock()

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        definition, normalized = self._validated(name, labels, MetricKind.COUNTER)
        del definition
        if not math.isfinite(value) or value < 0:
            raise ValueError("counter increments must be finite and non-negative")
        key = (name, normalized)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        _definition, normalized = self._validated(name, labels, MetricKind.GAUGE)
        if not math.isfinite(value):
            raise ValueError("gauge values must be finite")
        with self._lock:
            self._values[(name, normalized)] = value

    def adjust_gauge(self, name: str, delta: float, **labels: str) -> float:
        _definition, normalized = self._validated(name, labels, MetricKind.GAUGE)
        if not math.isfinite(delta):
            raise ValueError("gauge deltas must be finite")
        key = (name, normalized)
        with self._lock:
            value = self._values.get(key, 0.0) + delta
            self._values[key] = value
        return value

    def observe(self, name: str, value: float, **labels: str) -> None:
        definition, normalized = self._validated(name, labels, MetricKind.HISTOGRAM)
        if not math.isfinite(value) or value < 0:
            raise ValueError("histogram observations must be finite and non-negative")
        key = (name, normalized)
        with self._lock:
            histogram = self._histograms.setdefault(
                key, _Histogram([0 for _bucket in definition.buckets])
            )
            histogram.count += 1
            histogram.total += value
            for index, boundary in enumerate(definition.buckets):
                if value <= boundary:
                    histogram.bucket_counts[index] += 1

    def render_prometheus(self) -> str:
        """Render deterministic text without user, workspace, project, or content labels."""
        lines: list[str] = []
        with self._lock:
            for name, definition in self._definitions.items():
                lines.append(f"# HELP {name} {definition.description}")
                lines.append(f"# TYPE {name} {definition.kind.value}")
                if definition.kind is MetricKind.HISTOGRAM:
                    self._render_histograms(lines, definition)
                else:
                    for (metric_name, labels), value in sorted(self._values.items()):
                        if metric_name == name:
                            lines.append(f"{name}{_format_labels(labels)} {_number(value)}")
        return "\n".join(lines) + "\n"

    def _render_histograms(self, lines: list[str], definition: MetricDefinition) -> None:
        for (metric_name, labels), histogram in sorted(self._histograms.items()):
            if metric_name != definition.name:
                continue
            for boundary, count in zip(definition.buckets, histogram.bucket_counts, strict=True):
                bucket_labels = (*labels, ("le", _number(boundary)))
                lines.append(f"{definition.name}_bucket{_format_labels(bucket_labels)} {count}")
            infinity_labels = (*labels, ("le", "+Inf"))
            lines.append(
                f"{definition.name}_bucket{_format_labels(infinity_labels)} {histogram.count}"
            )
            lines.append(
                f"{definition.name}_sum{_format_labels(labels)} {_number(histogram.total)}"
            )
            lines.append(f"{definition.name}_count{_format_labels(labels)} {histogram.count}")

    def _validated(
        self,
        name: str,
        labels: dict[str, str],
        expected: MetricKind,
    ) -> tuple[MetricDefinition, tuple[tuple[str, str], ...]]:
        try:
            definition = self._definitions[name]
        except KeyError as error:
            raise ValueError("metric is not registered") from error
        if definition.kind is not expected:
            raise ValueError("metric operation does not match its registered kind")
        if set(labels) != set(definition.label_names):
            raise ValueError("metric labels do not match the registered schema")
        normalized = tuple((key, labels[key]) for key in definition.label_names)
        if any(_SAFE_LABEL.fullmatch(value) is None for _key, value in normalized):
            raise ValueError("metric label value is unsafe or unbounded")
        return definition, normalized


class TelemetryRuntime:
    """Lifecycle owner combining local metrics with an optional fail-open exporter."""

    name = "observability"

    def __init__(
        self,
        exporter: TelemetryExporter | None = None,
        *,
        registry: MetricRegistry | None = None,
        time_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        self.registry = registry or MetricRegistry()
        self._exporter = exporter or NullTelemetryExporter()
        self._time_ns = time_ns

    async def startup(self) -> None:
        await self._exporter.startup()

    async def shutdown(self) -> None:
        await self._exporter.shutdown()

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        self.registry.increment(name, value, **labels)
        self._exporter.enqueue_metric(
            MetricPoint(
                name,
                MetricKind.COUNTER,
                value,
                tuple(labels.items()),
                self._time_ns(),
            )
        )

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        self.registry.set_gauge(name, value, **labels)
        self._exporter.enqueue_metric(
            MetricPoint(name, MetricKind.GAUGE, value, tuple(labels.items()), self._time_ns())
        )

    def adjust_gauge(self, name: str, delta: float, **labels: str) -> None:
        value = self.registry.adjust_gauge(name, delta, **labels)
        self._exporter.enqueue_metric(
            MetricPoint(name, MetricKind.GAUGE, value, tuple(labels.items()), self._time_ns())
        )

    def observe(self, name: str, value: float, **labels: str) -> None:
        self.registry.observe(name, value, **labels)
        self._exporter.enqueue_metric(
            MetricPoint(
                name,
                MetricKind.HISTOGRAM,
                value,
                tuple(labels.items()),
                self._time_ns(),
            )
        )

    def record_span(self, span: SpanRecord) -> None:
        if (
            not span.name
            or len(span.trace_id) != _TRACE_ID_LENGTH
            or len(span.span_id) != _SPAN_ID_LENGTH
            or span.end_unix_nano < span.start_unix_nano
            or span.outcome not in {"success", "error"}
        ):
            raise ValueError("span record is invalid")
        self._exporter.enqueue_span(span)


def safe_metric_label(value: object, *, fallback: str = "other") -> str:
    """Keep adapter-provided enum/provider labels bounded and injection-safe."""
    candidate = str(value)
    return candidate if _SAFE_LABEL.fullmatch(candidate) is not None else fallback


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    rendered = ",".join(
        f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for key, value in labels
    )
    return "{" + rendered + "}"


def _number(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".15g")
