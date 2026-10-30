"""Redis heartbeat and PostgreSQL-backed low-cardinality runtime projections."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from redis.asyncio import Redis
from sqlalchemy import func, select

from accos.adapters.knowledge.persistence import KnowledgeIngestionRunRow
from accos.adapters.models.persistence import ModelUsageRecordRow
from accos.adapters.persistence.models import OutboxEventRow
from accos.adapters.workflows.persistence import WorkflowRunRow
from accos.kernel.clock import format_utc
from accos.kernel.observability import (
    OutboxRuntimeSnapshot,
    RuntimeBoundaryState,
    RuntimeSnapshot,
    WorkerRuntimeSnapshot,
    safe_metric_label,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from accos.adapters.persistence import AsyncSessionFactory
    from accos.kernel.clock import Clock
    from accos.kernel.observability import TelemetryRuntime

_HEARTBEAT_KEY = "accos:runtime:worker:heartbeat:v1"
_MINIMUM_HEARTBEAT_TTL_SECONDS = 2
_WORKFLOW_STATUSES = (
    "pending",
    "running",
    "paused",
    "waiting_approval",
    "succeeded",
    "failed",
    "cancelling",
    "cancelled",
)
_KNOWLEDGE_STATUSES = (
    "uploaded",
    "extracting",
    "normalized",
    "chunked",
    "embedded",
    "indexed",
    "verifying",
    "ready",
    "failed",
)


class PostgresRedisRuntimeMonitor:
    """Report worker liveness and authoritative backlog without treating Redis as truth."""

    def __init__(  # noqa: PLR0913
        self,
        sessions: AsyncSessionFactory,
        engine: AsyncEngine,
        redis_url: str,
        clock: Clock,
        *,
        timeout_seconds: float,
        heartbeat_ttl_seconds: int,
    ) -> None:
        if timeout_seconds <= 0 or heartbeat_ttl_seconds < _MINIMUM_HEARTBEAT_TTL_SECONDS:
            raise ValueError("runtime monitor timing values are invalid")
        self._sessions = sessions
        self._engine = engine
        self._redis_url = redis_url
        self._clock = clock
        self._timeout_seconds = timeout_seconds
        self._heartbeat_ttl_seconds = heartbeat_ttl_seconds

    async def heartbeat(self) -> None:
        client = self._redis()
        payload = json.dumps({"last_seen_at": format_utc(self._clock.now()), "version": 1})
        try:
            await client.set(_HEARTBEAT_KEY, payload, ex=self._heartbeat_ttl_seconds * 2)
        finally:
            await client.aclose()

    async def snapshot(self) -> RuntimeSnapshot:
        worker = await self._worker_snapshot()
        outbox = await self._outbox_snapshot()
        return RuntimeSnapshot(worker, outbox)

    async def refresh_metrics(self, telemetry: TelemetryRuntime) -> RuntimeSnapshot:
        snapshot = await self.snapshot()
        for state in RuntimeBoundaryState:
            telemetry.set_gauge(
                "accos_worker_heartbeat",
                1.0 if snapshot.worker.state is state else 0.0,
                state=state.value,
            )
        if snapshot.outbox.backlog is not None:
            telemetry.set_gauge("accos_outbox_backlog", float(snapshot.outbox.backlog))
        if snapshot.outbox.oldest_age_seconds is not None:
            telemetry.set_gauge(
                "accos_outbox_oldest_age_seconds", snapshot.outbox.oldest_age_seconds
            )
        self._pool_metrics(telemetry)
        await self._persistent_metrics(telemetry)
        return snapshot

    async def _worker_snapshot(self) -> WorkerRuntimeSnapshot:
        client = self._redis()
        try:
            raw = await client.get(_HEARTBEAT_KEY)
        except Exception:  # noqa: BLE001 - status remains diagnostic and fail-open.
            return WorkerRuntimeSnapshot(
                RuntimeBoundaryState.UNAVAILABLE,
                "heartbeat_store_unavailable",
                None,
            )
        finally:
            await client.aclose()
        if raw is None:
            return WorkerRuntimeSnapshot(
                RuntimeBoundaryState.NOT_STARTED,
                "heartbeat_not_observed",
                None,
            )
        try:
            parsed = json.loads(raw)
            last_seen_at = datetime.fromisoformat(
                str(parsed["last_seen_at"]).replace("Z", "+00:00")
            )
            age = (self._clock.now() - last_seen_at).total_seconds()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return WorkerRuntimeSnapshot(
                RuntimeBoundaryState.UNAVAILABLE,
                "heartbeat_payload_invalid",
                None,
            )
        if age > self._heartbeat_ttl_seconds:
            return WorkerRuntimeSnapshot(
                RuntimeBoundaryState.STALE,
                "heartbeat_stale",
                last_seen_at,
            )
        return WorkerRuntimeSnapshot(
            RuntimeBoundaryState.ACTIVE,
            "heartbeat_fresh",
            last_seen_at,
        )

    async def _outbox_snapshot(self) -> OutboxRuntimeSnapshot:
        try:
            async with self._sessions() as session:
                backlog, oldest = (
                    await session.execute(
                        select(func.count(), func.min(OutboxEventRow.occurred_at)).where(
                            OutboxEventRow.published_at.is_(None),
                            OutboxEventRow.archived_at.is_(None),
                        )
                    )
                ).one()
        except Exception:  # noqa: BLE001 - status remains diagnostic and fail-open.
            return OutboxRuntimeSnapshot(
                RuntimeBoundaryState.UNAVAILABLE,
                "backlog_query_unavailable",
                None,
                None,
            )
        oldest_age = (
            None if oldest is None else max(0.0, (self._clock.now() - oldest).total_seconds())
        )
        return OutboxRuntimeSnapshot(
            RuntimeBoundaryState.ACTIVE,
            "backlog_reported",
            int(backlog),
            oldest_age,
        )

    async def _persistent_metrics(self, telemetry: TelemetryRuntime) -> None:
        try:
            async with self._sessions() as session:
                workflow_rows = (
                    await session.execute(
                        select(WorkflowRunRow.status, func.count()).group_by(WorkflowRunRow.status)
                    )
                ).all()
                knowledge_rows = (
                    await session.execute(
                        select(KnowledgeIngestionRunRow.status, func.count()).group_by(
                            KnowledgeIngestionRunRow.status
                        )
                    )
                ).all()
                model_rows = (
                    await session.execute(
                        select(
                            ModelUsageRecordRow.provider_id,
                            ModelUsageRecordRow.status,
                            func.count(),
                            func.coalesce(func.sum(ModelUsageRecordRow.input_tokens), 0),
                            func.coalesce(func.sum(ModelUsageRecordRow.output_tokens), 0),
                        ).group_by(
                            ModelUsageRecordRow.provider_id,
                            ModelUsageRecordRow.status,
                        )
                    )
                ).all()
        except Exception:  # noqa: BLE001 - scrape remains available during DB outages.
            return

        workflow_counts = {str(status): int(count) for status, count in workflow_rows}
        for status in _WORKFLOW_STATUSES:
            telemetry.set_gauge(
                "accos_workflow_runs", float(workflow_counts.get(status, 0)), status=status
            )
        knowledge_counts = {str(status): int(count) for status, count in knowledge_rows}
        for status in _KNOWLEDGE_STATUSES:
            telemetry.set_gauge(
                "accos_knowledge_ingestions",
                float(knowledge_counts.get(status, 0)),
                status=status,
            )
        for provider, status, count, input_tokens, output_tokens in model_rows:
            provider_label = safe_metric_label(provider or "unconfigured")
            outcome = safe_metric_label(status)
            telemetry.set_gauge(
                "accos_model_calls",
                float(count),
                provider=provider_label,
                outcome=outcome,
            )
            telemetry.set_gauge(
                "accos_model_tokens",
                float(input_tokens),
                provider=provider_label,
                direction="input",
            )
            telemetry.set_gauge(
                "accos_model_tokens",
                float(output_tokens),
                provider=provider_label,
                direction="output",
            )

    def _pool_metrics(self, telemetry: TelemetryRuntime) -> None:
        pool = self._engine.sync_engine.pool
        for state, attribute in (
            ("size", "size"),
            ("idle", "checkedin"),
            ("active", "checkedout"),
            ("overflow", "overflow"),
        ):
            method = getattr(pool, attribute, None)
            if callable(method):
                telemetry.set_gauge("accos_database_pool_connections", float(method()), state=state)

    def _redis(self) -> Redis:
        return Redis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=self._timeout_seconds,
            socket_timeout=self._timeout_seconds,
        )
