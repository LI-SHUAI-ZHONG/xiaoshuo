"""Optional fail-open OTLP/HTTP JSON exporter."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from threading import Lock
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

from accos.kernel.logging import get_logger, log_event
from accos.kernel.observability import MetricKind

if TYPE_CHECKING:
    from accos.kernel.observability import MetricPoint, SpanRecord

Sender = Callable[[str, bytes, float], None]
OutcomeCallback = Callable[[str, str], None]


class OtlpHttpExporter:
    """Buffer OTLP signals and export them without affecting application success."""

    def __init__(  # noqa: PLR0913
        self,
        endpoint: str,
        *,
        service: str,
        environment: str,
        timeout_seconds: float,
        interval_seconds: float,
        max_queue_size: int = 4096,
        sender: Sender | None = None,
        outcome: OutcomeCallback | None = None,
    ) -> None:
        if (
            not endpoint.startswith(("http://", "https://"))
            or timeout_seconds <= 0
            or interval_seconds <= 0
            or max_queue_size < 1
            or not service
            or not environment
        ):
            raise ValueError("OTLP exporter configuration is invalid")
        self._endpoint = endpoint.rstrip("/")
        self._service = service
        self._environment = environment
        self._timeout_seconds = timeout_seconds
        self._interval_seconds = interval_seconds
        self._max_queue_size = max_queue_size
        self._sender = sender or _send_http
        self._outcome = outcome or (lambda _signal, _result: None)
        self._metrics: deque[MetricPoint] = deque()
        self._spans: deque[SpanRecord] = deque()
        self._lock = Lock()
        self._stop: asyncio.Event | None = None
        self._task: asyncio.Task[None] | None = None
        self._logger = get_logger("telemetry")

    @property
    def queued(self) -> tuple[int, int]:
        with self._lock:
            return len(self._metrics), len(self._spans)

    def enqueue_metric(self, point: MetricPoint) -> None:
        with self._lock:
            _bounded_append(self._metrics, point, self._max_queue_size)

    def enqueue_span(self, span: SpanRecord) -> None:
        with self._lock:
            _bounded_append(self._spans, span, self._max_queue_size)

    async def startup(self) -> None:
        if self._task is not None:
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="accos-otlp-export")

    async def shutdown(self) -> None:
        if self._task is None or self._stop is None:
            return
        self._stop.set()
        await self._task
        self._task = None
        self._stop = None

    async def flush(self) -> None:
        metrics, spans = self._drain()
        if metrics:
            await self._export(
                "metrics", "/v1/metrics", _metric_payload(metrics, self._resource_attributes())
            )
        if spans:
            await self._export(
                "traces", "/v1/traces", _trace_payload(spans, self._resource_attributes())
            )

    async def _run(self) -> None:
        stop = self._stop
        if stop is None:
            return
        while not stop.is_set():
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=self._interval_seconds)
            await self.flush()

    def _drain(self) -> tuple[tuple[MetricPoint, ...], tuple[SpanRecord, ...]]:
        with self._lock:
            metrics = tuple(self._metrics)
            spans = tuple(self._spans)
            self._metrics.clear()
            self._spans.clear()
        return metrics, spans

    async def _export(self, signal: str, path: str, payload: dict[str, object]) -> None:
        try:
            body = json.dumps(payload, separators=(",", ":")).encode()
            await asyncio.to_thread(
                self._sender,
                self._endpoint + path,
                body,
                self._timeout_seconds,
            )
        except Exception as error:  # noqa: BLE001 - telemetry must fail open.
            self._outcome(signal, "failed")
            log_event(
                self._logger,
                logging.WARNING,
                "telemetry_export_failed",
                signal=signal,
                outcome="error",
                error_code="otlp_export_failed",
                error_type=type(error).__name__,
            )
        else:
            self._outcome(signal, "succeeded")

    def _resource_attributes(self) -> list[dict[str, object]]:
        return [
            _attribute("service.name", self._service),
            _attribute("deployment.environment.name", self._environment),
        ]


def _bounded_append[T](queue: deque[T], value: T, maximum: int) -> None:
    if len(queue) >= maximum:
        queue.popleft()
    queue.append(value)


def _send_http(url: str, body: bytes, timeout_seconds: float) -> None:
    request = Request(  # noqa: S310 - URL is validated application configuration.
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "accos-otlp/1",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        if not 200 <= response.status < 300:  # noqa: PLR2004
            raise RuntimeError("OTLP endpoint rejected the export")


def _metric_payload(
    points: tuple[MetricPoint, ...], resource_attributes: list[dict[str, object]]
) -> dict[str, object]:
    metrics: list[dict[str, object]] = []
    for point in points:
        metric: dict[str, object]
        data_point = {
            "attributes": [_attribute(key, value) for key, value in point.labels],
            "timeUnixNano": str(point.timestamp_unix_nano),
            "asDouble": point.value,
        }
        if point.kind is MetricKind.COUNTER:
            metric = {
                "name": point.name,
                "sum": {
                    "aggregationTemporality": 1,
                    "isMonotonic": True,
                    "dataPoints": [data_point],
                },
            }
        elif point.kind is MetricKind.HISTOGRAM:
            histogram_point = {
                "attributes": data_point["attributes"],
                "timeUnixNano": data_point["timeUnixNano"],
                "count": "1",
                "sum": point.value,
                "bucketCounts": ["0", "1"],
                "explicitBounds": [point.value],
            }
            metric = {
                "name": point.name,
                "histogram": {
                    "aggregationTemporality": 1,
                    "dataPoints": [histogram_point],
                },
            }
        else:
            metric = {"name": point.name, "gauge": {"dataPoints": [data_point]}}
        metrics.append(metric)
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": resource_attributes},
                "scopeMetrics": [{"scope": {"name": "accos", "version": "1"}, "metrics": metrics}],
            }
        ]
    }


def _trace_payload(
    spans: tuple[SpanRecord, ...], resource_attributes: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": resource_attributes},
                "scopeSpans": [
                    {
                        "scope": {"name": "accos", "version": "1"},
                        "spans": [
                            {
                                "traceId": span.trace_id,
                                "spanId": span.span_id,
                                "name": span.name,
                                "kind": 2,
                                "startTimeUnixNano": str(span.start_unix_nano),
                                "endTimeUnixNano": str(span.end_unix_nano),
                                "attributes": [
                                    _attribute(key, value) for key, value in span.attributes
                                ],
                                "status": {"code": 1 if span.outcome == "success" else 2},
                            }
                            for span in spans
                        ],
                    }
                ],
            }
        ]
    }


def _attribute(key: str, value: object) -> dict[str, object]:
    if isinstance(value, bool):
        encoded: dict[str, object] = {"boolValue": value}
    elif isinstance(value, int):
        encoded = {"intValue": str(value)}
    elif isinstance(value, float):
        encoded = {"doubleValue": value}
    else:
        encoded = {"stringValue": str(value)}
    return {"key": key, "value": encoded}
