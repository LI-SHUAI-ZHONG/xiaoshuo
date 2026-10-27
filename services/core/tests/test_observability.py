from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Self
from unittest.mock import MagicMock, patch

import pytest

from accos.adapters.assets import InMemoryObjectStorage, ResilientObjectStorage
from accos.adapters.observability import OtlpHttpExporter, _send_http
from accos.adapters.runtime_monitor import PostgresRedisRuntimeMonitor
from accos.kernel.errors import DependencyUnavailableError
from accos.kernel.observability import (
    MetricDefinition,
    MetricKind,
    MetricPoint,
    MetricRegistry,
    NullTelemetryExporter,
    RuntimeBoundaryState,
    SpanRecord,
    TelemetryRuntime,
    safe_metric_label,
)
from accos.kernel.resilience import ResilienceExecutor, ResiliencePolicy

if TYPE_CHECKING:
    from collections.abc import Callable


class CaptureExporter:
    def __init__(self) -> None:
        self.metrics: list[MetricPoint] = []
        self.spans: list[SpanRecord] = []
        self.started = 0
        self.stopped = 0

    def enqueue_metric(self, point: MetricPoint) -> None:
        self.metrics.append(point)

    def enqueue_span(self, span: SpanRecord) -> None:
        self.spans.append(span)

    async def startup(self) -> None:
        self.started += 1

    async def shutdown(self) -> None:
        self.stopped += 1


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 18, 1, 2, 3, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value


class FakeRedis:
    def __init__(self) -> None:
        self.value: str | None = None
        self.failure: Exception | None = None
        self.closed = 0

    async def set(self, _key: str, value: str, *, ex: int) -> None:
        assert ex == 40
        self.value = value

    async def get(self, _key: str) -> str | None:
        if self.failure is not None:
            raise self.failure
        return self.value

    async def aclose(self) -> None:
        self.closed += 1


class FakeResult:
    def __init__(self, value: tuple[object, ...] | list[tuple[object, ...]]) -> None:
        self.value = value

    def one(self) -> tuple[object, ...]:
        assert isinstance(self.value, tuple)
        return self.value

    def all(self) -> list[tuple[object, ...]]:
        assert isinstance(self.value, list)
        return self.value


class FakeSession:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, statement: object) -> FakeResult:
        if self.fail:
            raise ConnectionError("fixture database unavailable")
        rendered = str(statement)
        if "outbox_events" in rendered:
            return FakeResult((2, datetime(2026, 9, 18, 1, 2, 1, tzinfo=UTC)))
        if "workflow_runs" in rendered:
            return FakeResult([("running", 2), ("succeeded", 3)])
        if "knowledge_ingestion_runs" in rendered:
            return FakeResult([("ready", 4)])
        if "model_usage_records" in rendered:
            return FakeResult([("fake-model", "succeeded", 5, 11, 7)])
        raise AssertionError(rendered)


class FakeSessions:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def __call__(self) -> FakeSession:
        return FakeSession(fail=self.fail)


def _engine() -> MagicMock:
    pool = MagicMock()
    pool.size.return_value = 5
    pool.checkedin.return_value = 3
    pool.checkedout.return_value = 2
    pool.overflow.return_value = 0
    engine = MagicMock()
    engine.sync_engine.pool = pool
    return engine


def _policy(**updates: object) -> ResiliencePolicy:
    values: dict[str, Any] = {
        "timeout_seconds": 0.1,
        "max_attempts": 3,
        "backoff_seconds": 0.01,
        "max_backoff_seconds": 0.02,
        "circuit_failure_threshold": 3,
        "circuit_cooldown_seconds": 1.0,
        "concurrency_limit": 1,
    }
    values.update(updates)
    return ResiliencePolicy(**values)


def test_metric_definition_registry_rendering_and_export_port() -> None:
    definition = MetricDefinition(
        "fixture_duration_seconds",
        "Fixture duration.",
        MetricKind.HISTOGRAM,
        ("outcome",),
        (0.1, 1.0),
    )
    registry = MetricRegistry(
        (
            MetricDefinition("fixture_total", "Fixture count.", MetricKind.COUNTER, ("outcome",)),
            MetricDefinition("fixture_gauge", "Fixture gauge.", MetricKind.GAUGE),
            definition,
            MetricDefinition(
                "fixture_other_seconds",
                "Other fixture duration.",
                MetricKind.HISTOGRAM,
                buckets=(1.0,),
            ),
        )
    )
    registry.increment("fixture_total", 2, outcome="success")
    registry.set_gauge("fixture_gauge", 3)
    assert registry.adjust_gauge("fixture_gauge", -1) == 2
    registry.observe("fixture_duration_seconds", 0.05, outcome="success")
    registry.observe("fixture_duration_seconds", 2.0, outcome="success")
    registry.observe("fixture_other_seconds", 0.5)

    rendered = registry.render_prometheus()
    assert registry.names == (
        "fixture_total",
        "fixture_gauge",
        "fixture_duration_seconds",
        "fixture_other_seconds",
    )
    assert 'fixture_total{outcome="success"} 2' in rendered
    assert "fixture_gauge 2" in rendered
    assert 'fixture_duration_seconds_bucket{outcome="success",le="0.1"} 1' in rendered
    assert 'fixture_duration_seconds_bucket{outcome="success",le="+Inf"} 2' in rendered
    assert 'fixture_duration_seconds_sum{outcome="success"} 2.05' in rendered

    exporter = CaptureExporter()
    ticks = iter((10, 11, 12, 13))
    telemetry = TelemetryRuntime(exporter, registry=MetricRegistry(), time_ns=lambda: next(ticks))
    asyncio.run(telemetry.startup())
    telemetry.increment(
        "accos_api_requests_total",
        method="GET",
        route="/fixture/{id}",
        status_class="2xx",
        outcome="success",
    )
    telemetry.set_gauge("accos_sse_connections", 1)
    telemetry.observe(
        "accos_api_request_duration_seconds", 0.25, method="GET", route="/fixture/{id}"
    )
    telemetry.adjust_gauge("accos_sse_connections", -1)
    span = SpanRecord("GET /fixture", "1" * 32, "2" * 16, 1, 2, "success", ())
    telemetry.record_span(span)
    asyncio.run(telemetry.shutdown())

    assert exporter.started == exporter.stopped == 1
    assert [point.timestamp_unix_nano for point in exporter.metrics[:3]] == [10, 11, 12]
    assert exporter.spans == [span]
    null_runtime = TelemetryRuntime(NullTelemetryExporter())
    asyncio.run(null_runtime.startup())
    asyncio.run(null_runtime.shutdown())


@pytest.mark.parametrize(
    "definition",
    [
        lambda: MetricDefinition("bad-name", "x", MetricKind.COUNTER),
        lambda: MetricDefinition("fixture", "", MetricKind.COUNTER),
        lambda: MetricDefinition("fixture", "x", MetricKind.COUNTER, ("status", "status")),
        lambda: MetricDefinition("fixture", "x", MetricKind.COUNTER, ("workspace",)),
        lambda: MetricDefinition("fixture", "x", MetricKind.HISTOGRAM),
        lambda: MetricDefinition("fixture", "x", MetricKind.HISTOGRAM, buckets=(1.0, 1.0)),
        lambda: MetricDefinition("fixture", "x", MetricKind.GAUGE, buckets=(1.0,)),
    ],
)
def test_metric_definitions_reject_unsafe_schemas(
    definition: Callable[[], MetricDefinition],
) -> None:
    with pytest.raises(ValueError):
        definition()


def test_metric_registry_and_spans_reject_invalid_updates() -> None:
    counter = MetricDefinition("fixture_total", "Fixture.", MetricKind.COUNTER, ("outcome",))
    with pytest.raises(ValueError, match="unique"):
        MetricRegistry((counter, counter))
    registry = MetricRegistry((counter,))
    invalid_calls: tuple[Callable[[], object], ...] = (
        lambda: registry.increment("missing", outcome="success"),
        lambda: registry.set_gauge("fixture_total", 1, outcome="success"),
        lambda: registry.increment("fixture_total"),
        lambda: registry.increment("fixture_total", outcome="unsafe value"),
        lambda: registry.increment("fixture_total", -1, outcome="success"),
        lambda: registry.increment("fixture_total", float("inf"), outcome="success"),
    )
    for call in invalid_calls:
        with pytest.raises(ValueError):
            call()
    gauge = MetricRegistry((MetricDefinition("fixture", "Fixture.", MetricKind.GAUGE),))
    with pytest.raises(ValueError):
        gauge.set_gauge("fixture", float("nan"))
    with pytest.raises(ValueError):
        gauge.adjust_gauge("fixture", float("inf"))
    histogram = MetricRegistry(
        (MetricDefinition("fixture", "Fixture.", MetricKind.HISTOGRAM, buckets=(1.0,)),)
    )
    with pytest.raises(ValueError):
        histogram.observe("fixture", -1)

    runtime = TelemetryRuntime()
    for span in (
        SpanRecord("", "1" * 32, "2" * 16, 1, 2, "success", ()),
        SpanRecord("x", "1", "2" * 16, 1, 2, "success", ()),
        SpanRecord("x", "1" * 32, "2", 1, 2, "success", ()),
        SpanRecord("x", "1" * 32, "2" * 16, 2, 1, "success", ()),
        SpanRecord("x", "1" * 32, "2" * 16, 1, 2, "unknown", ()),
    ):
        with pytest.raises(ValueError, match="span"):
            runtime.record_span(span)
    assert safe_metric_label("safe-value") == "safe-value"
    assert safe_metric_label("unsafe value", fallback="bounded") == "bounded"


def test_resilience_executor_retries_opens_circuit_and_recovers() -> None:
    async def scenario() -> None:
        now = 0.0
        sleeps: list[float] = []
        attempts = 0

        async def sleep(delay: float) -> None:
            sleeps.append(delay)

        async def flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("fixture")
            return "ok"

        executor = ResilienceExecutor(_policy(), monotonic=lambda: now, sleep=sleep)
        assert await executor.call("fixture", flaky) == "ok"
        assert sleeps == [0.01, 0.02]
        assert executor.snapshots()[0].consecutive_failures == 0

        async def failing() -> str:
            raise ConnectionError("fixture")

        with pytest.raises(DependencyUnavailableError):
            await executor.call("dependency", failing)
        snapshot = next(item for item in executor.snapshots() if item.operation == "dependency")
        assert snapshot.open is True
        with pytest.raises(DependencyUnavailableError, match="circuit"):
            await executor.call("dependency", failing)
        now = 2.0

        async def recovered() -> str:
            return "recovered"

        assert await executor.call("dependency", recovered) == "recovered"
        assert (
            next(item for item in executor.snapshots() if item.operation == "dependency").open
            is False
        )

        with pytest.raises(ValueError, match="operation"):
            await executor.call("", recovered)

        async def invalid() -> str:
            raise ValueError("invalid")

        with pytest.raises(ValueError, match="invalid"):
            await executor.call("nonretryable", invalid, retryable=lambda _error: False)

        async def slow() -> str:
            await asyncio.sleep(0.02)
            return "late"

        timeout_executor = ResilienceExecutor(_policy(timeout_seconds=0.001, max_attempts=1))
        with pytest.raises(DependencyUnavailableError):
            await timeout_executor.call("timeout", slow)

        state_executor = ResilienceExecutor(_policy())

        async def inspect_state() -> str:
            assert state_executor.snapshots()[0].in_flight == 1
            return "visible"

        assert await state_executor.call("visible", inspect_state) == "visible"

        zero_backoff = ResilienceExecutor(
            _policy(max_attempts=2, backoff_seconds=0, circuit_failure_threshold=3),
            sleep=sleep,
        )
        with pytest.raises(DependencyUnavailableError):
            await zero_backoff.call("zero-backoff", failing)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("timeout_seconds", 0),
        ("max_attempts", 0),
        ("backoff_seconds", -1),
        ("max_backoff_seconds", 0),
        ("max_backoff_seconds", 0.001),
        ("circuit_failure_threshold", 0),
        ("circuit_cooldown_seconds", 0),
        ("concurrency_limit", 0),
    ],
)
def test_resilience_policy_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="policy"):
        replace(_policy(), **{field: value})  # type: ignore[arg-type]


def test_resilient_object_storage_records_success_and_safe_failures() -> None:
    async def scenario() -> None:
        storage = InMemoryObjectStorage()
        telemetry = TelemetryRuntime()
        resilient = ResilientObjectStorage(storage, ResilienceExecutor(_policy()), telemetry)
        data = b"fixture"
        digest = hashlib.sha256(data).hexdigest()
        stored = await resilient.put(
            "fixture/object", data, media_type="text/plain", content_hash=digest
        )
        assert stored.content_hash == digest
        assert await resilient.get("fixture/object") == data
        assert await resilient.stat("fixture/object") == stored
        with pytest.raises(FileNotFoundError):
            await resilient.get("fixture/missing")
        rendered = telemetry.registry.render_prometheus()
        assert 'operation="put",outcome="success"} 1' in rendered
        assert 'operation="get",outcome="error"} 1' in rendered

    asyncio.run(scenario())


def test_otlp_exporter_batches_bounds_queue_and_fails_open(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sent: list[tuple[str, dict[str, object], float]] = []
    outcomes: list[tuple[str, str]] = []

    def sender(url: str, body: bytes, timeout: float) -> None:
        sent.append((url, json.loads(body), timeout))

    exporter = OtlpHttpExporter(
        "http://collector:4318/",
        service="fixture",
        environment="test",
        timeout_seconds=0.1,
        interval_seconds=60,
        max_queue_size=1,
        sender=sender,
        outcome=lambda signal, result: outcomes.append((signal, result)),
    )
    first = MetricPoint("first", MetricKind.GAUGE, 1, (), 1)
    second = MetricPoint("second", MetricKind.COUNTER, 2, (("outcome", "success"),), 2)
    exporter.enqueue_metric(first)
    exporter.enqueue_metric(second)
    exporter.enqueue_span(SpanRecord("fixture", "1" * 32, "2" * 16, 1, 2, "success", ()))
    assert exporter.queued == (1, 1)
    asyncio.run(exporter.flush())
    assert exporter.queued == (0, 0)
    assert {url.rsplit("/", 1)[-1] for url, _payload, _timeout in sent} == {
        "metrics",
        "traces",
    }
    metric_payload = next(payload for url, payload, _timeout in sent if url.endswith("metrics"))
    assert "second" in json.dumps(metric_payload)
    assert "first" not in json.dumps(metric_payload)
    assert outcomes == [("metrics", "succeeded"), ("traces", "succeeded")]

    exporter.enqueue_metric(MetricPoint("fixture-gauge", MetricKind.GAUGE, 3, (), 3))
    asyncio.run(exporter.flush())
    assert "fixture-gauge" in json.dumps(sent[-1][1])
    assert outcomes[-1] == ("metrics", "succeeded")

    def failing_sender(_url: str, _body: bytes, _timeout: float) -> None:
        raise OSError("fixture secret detail")

    failed = OtlpHttpExporter(
        "http://collector:4318",
        service="fixture",
        environment="test",
        timeout_seconds=0.1,
        interval_seconds=0.001,
        sender=failing_sender,
        outcome=lambda signal, result: outcomes.append((signal, result)),
    )
    failed.enqueue_metric(MetricPoint("fixture", MetricKind.HISTOGRAM, 0.5, (), 1))
    with caplog.at_level("WARNING", logger="accos.telemetry"):
        asyncio.run(failed.flush())
    assert outcomes[-1] == ("metrics", "failed")
    assert "fixture secret detail" not in caplog.text

    async def lifecycle() -> None:
        await failed._run()  # noqa: SLF001 - covers harmless pre-start branch.
        failed.enqueue_span(
            SpanRecord(
                "fixture",
                "1" * 32,
                "2" * 16,
                1,
                2,
                "error",
                (("bool", True), ("int", 2), ("float", 2.5), ("string", "x")),
            )
        )
        await failed.startup()
        await failed.startup()
        await asyncio.sleep(0.005)
        await failed.shutdown()
        await failed.shutdown()

    asyncio.run(lifecycle())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"endpoint": "ftp://collector"},
        {"timeout_seconds": 0},
        {"interval_seconds": 0},
        {"max_queue_size": 0},
        {"service": ""},
        {"environment": ""},
    ],
)
def test_otlp_exporter_rejects_invalid_configuration(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "endpoint": "http://collector",
        "service": "fixture",
        "environment": "test",
        "timeout_seconds": 1,
        "interval_seconds": 1,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match="OTLP"):
        OtlpHttpExporter(**values)  # type: ignore[arg-type]


def test_otlp_http_sender_accepts_success_and_rejects_error() -> None:
    response = MagicMock()
    response.__enter__.return_value.status = 204
    with patch("accos.adapters.observability.urlopen", return_value=response) as opened:
        _send_http("http://collector/v1/traces", b"{}", 1)
    assert opened.call_args.kwargs["timeout"] == 1

    rejected = MagicMock()
    rejected.__enter__.return_value.status = 500
    with (
        patch("accos.adapters.observability.urlopen", return_value=rejected),
        pytest.raises(RuntimeError, match="rejected"),
    ):
        _send_http("http://collector/v1/traces", b"{}", 1)


def test_runtime_monitor_reports_heartbeat_backlog_and_persistent_metrics() -> None:
    async def scenario() -> None:
        redis = FakeRedis()
        clock = MutableClock()
        monitor = PostgresRedisRuntimeMonitor(
            FakeSessions(),  # type: ignore[arg-type]
            _engine(),
            "redis://fixture",
            clock,
            timeout_seconds=0.1,
            heartbeat_ttl_seconds=20,
        )
        telemetry = TelemetryRuntime()
        with patch("accos.adapters.runtime_monitor.Redis.from_url", return_value=redis):
            await monitor.heartbeat()
            snapshot = await monitor.refresh_metrics(telemetry)
            assert snapshot.worker.state is RuntimeBoundaryState.ACTIVE
            assert snapshot.outbox.backlog == 2
            clock.value += timedelta(seconds=21)
            assert (await monitor.snapshot()).worker.state is RuntimeBoundaryState.STALE
            redis.value = None
            assert (await monitor.snapshot()).worker.state is RuntimeBoundaryState.NOT_STARTED
            redis.value = "invalid"
            assert (await monitor.snapshot()).worker.detail == "heartbeat_payload_invalid"
            redis.failure = ConnectionError("fixture")
            assert (await monitor.snapshot()).worker.state is RuntimeBoundaryState.UNAVAILABLE
        rendered = telemetry.registry.render_prometheus()
        assert 'accos_workflow_runs{status="running"} 2' in rendered
        assert 'accos_knowledge_ingestions{status="ready"} 4' in rendered
        assert 'accos_model_calls{provider="fake-model",outcome="succeeded"} 5' in rendered
        assert 'accos_database_pool_connections{state="active"} 2' in rendered

        failing = PostgresRedisRuntimeMonitor(
            FakeSessions(fail=True),  # type: ignore[arg-type]
            _engine(),
            "redis://fixture",
            clock,
            timeout_seconds=0.1,
            heartbeat_ttl_seconds=20,
        )
        redis.failure = None
        redis.value = None
        with patch("accos.adapters.runtime_monitor.Redis.from_url", return_value=redis):
            unavailable = await failing.refresh_metrics(TelemetryRuntime())
        assert unavailable.outbox.state is RuntimeBoundaryState.UNAVAILABLE

        no_pool_methods = PostgresRedisRuntimeMonitor(
            FakeSessions(),  # type: ignore[arg-type]
            SimpleNamespace(sync_engine=SimpleNamespace(pool=object())),  # type: ignore[arg-type]
            "redis://fixture",
            clock,
            timeout_seconds=0.1,
            heartbeat_ttl_seconds=20,
        )
        no_pool_methods._pool_metrics(TelemetryRuntime())  # noqa: SLF001

    asyncio.run(scenario())


def test_runtime_monitor_rejects_invalid_timing() -> None:
    with pytest.raises(ValueError, match="timing"):
        PostgresRedisRuntimeMonitor(
            FakeSessions(),  # type: ignore[arg-type]
            _engine(),
            "redis://fixture",
            MutableClock(),
            timeout_seconds=0,
            heartbeat_ttl_seconds=1,
        )
