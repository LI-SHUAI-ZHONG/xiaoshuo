from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.pool import NullPool

from accos.adapters.extensions import SqlAlchemyExtensionGraphStore
from accos.adapters.health import (
    AiProviderHealthProbe,
    RedisHealthProbe,
    S3HealthProbe,
)
from accos.adapters.persistence import DatabaseHealthProbe
from accos.composition import build_container
from accos.extensions import CapabilityState, ExtensionCapability, NullGraphStore
from accos.kernel.health import CheckStatus, HealthCheck

if TYPE_CHECKING:
    from accos.kernel.settings import RuntimeSettings


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 3, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class HealthyProbe:
    name: str = "fixture"
    critical: bool = True

    async def check(self) -> HealthCheck:
        return HealthCheck(self.name, CheckStatus.HEALTHY, self.critical, "ok")


def test_composition_builds_optional_otlp_exporter(
    runtime_settings: RuntimeSettings,
) -> None:
    settings = replace(
        runtime_settings,
        observability=replace(
            runtime_settings.observability,
            otlp_endpoint="http://collector:4318",
        ),
    )
    with patch("accos.composition.root.OtlpHttpExporter") as exporter:
        container = build_container(settings, probes=())

    exporter.assert_called_once()
    outcome = exporter.call_args.kwargs["outcome"]
    outcome("metrics", "succeeded")
    assert (
        'accos_telemetry_exports_total{signal="metrics",outcome="succeeded"} 1'
        in container.observability.telemetry.registry.render_prometheus()
    )


def test_database_probe_uses_async_engine_and_rejects_invalid_result() -> None:
    connection = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 1
    connection.execute = AsyncMock(return_value=result)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=None)
    engine = MagicMock()
    engine.connect.return_value = context
    probe = DatabaseHealthProbe(engine)

    health = asyncio.run(probe.check())

    assert health.status is CheckStatus.HEALTHY
    connection.execute.assert_awaited_once()

    result.scalar_one.return_value = 2
    with pytest.raises(RuntimeError, match="invalid result"):
        asyncio.run(probe.check())


def test_redis_probe_closes_client_on_success_and_failure() -> None:
    client = MagicMock()
    client.ping.return_value = True
    probe = RedisHealthProbe("redis://:secret@localhost/0", 0.5)

    with patch("accos.adapters.health.redis.Redis.from_url", return_value=client) as factory:
        result = asyncio.run(probe.check())

    assert result.detail == "pong"
    factory.assert_called_once_with(
        "redis://:secret@localhost/0",
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        decode_responses=True,
    )
    client.close.assert_called_once_with()

    client.reset_mock()
    client.ping.return_value = False
    with (
        patch("accos.adapters.health.redis.Redis.from_url", return_value=client),
        pytest.raises(RuntimeError, match="invalid result"),
    ):
        asyncio.run(probe.check())
    client.close.assert_called_once_with()


def test_s3_probe_checks_only_the_configured_bucket() -> None:
    client = MagicMock()
    client.bucket_exists.return_value = True
    probe = S3HealthProbe(
        endpoint="http://localhost:9000",
        bucket="fixture-project",
        access_key="fixture-access",
        secret_key="fixture-secret",
        secure=False,
        region="us-east-1",
    )

    with patch("accos.adapters.health.Minio", return_value=client) as factory:
        result = asyncio.run(probe.check())

    assert result.detail == "bucket_ok"
    factory.assert_called_once()
    assert factory.call_args.args == ("localhost:9000",)
    assert factory.call_args.kwargs["access_key"] == "fixture-access"
    assert factory.call_args.kwargs["secret_key"] == "fixture-secret"
    assert factory.call_args.kwargs["secure"] is False
    assert factory.call_args.kwargs["region"] == "us-east-1"
    assert factory.call_args.kwargs["http_client"] is not None
    client.bucket_exists.assert_called_once_with("fixture-project")

    client.bucket_exists.return_value = False
    with (
        patch("accos.adapters.health.Minio", return_value=client),
        pytest.raises(RuntimeError, match="bucket is unavailable"),
    ):
        asyncio.run(probe.check())

    with pytest.raises(ValueError, match="timeout"):
        replace(probe, timeout_seconds=0)._check_sync()  # noqa: SLF001


def test_optional_ai_probe_never_blocks_fake_mode() -> None:
    disabled = asyncio.run(AiProviderHealthProbe(False, None).check())
    missing = asyncio.run(AiProviderHealthProbe(True, None).check())
    deferred = asyncio.run(AiProviderHealthProbe(True, "fixture-provider").check())

    assert disabled.status is CheckStatus.NOT_CONFIGURED
    assert disabled.detail == "fake_mode"
    assert missing.status is CheckStatus.DEGRADED
    assert missing.detail == "provider_not_configured"
    assert deferred.status is CheckStatus.DEGRADED
    assert deferred.detail == "provider_probe_deferred"
    assert not disabled.critical


def test_composition_builds_default_and_injected_runtime_services(  # noqa: PLR0915
    runtime_settings: RuntimeSettings,
) -> None:
    default_container = build_container(runtime_settings)
    assert default_container.modules.names == (
        "observability",
        "kernel",
        "persistence",
        "workflow-consumer-persistence",
        "identity",
        "projects",
        "assets",
        "knowledge",
        "memory",
        "creative",
        "consistency",
        "quality",
        "feedback",
        "evolution",
        "extensions",
        "models",
        "tools",
        "agents",
        "workflows",
        "health",
    )
    assert default_container.projects.service
    assert default_container.assets.service
    assert default_container.knowledge.service
    assert default_container.knowledge.research
    assert default_container.knowledge.repository
    assert default_container.knowledge.retriever
    assert default_container.knowledge.index
    assert default_container.knowledge.graph
    assert default_container.memory.service
    assert default_container.memory.context_builder
    assert default_container.memory.repository
    assert default_container.memory.projection
    assert default_container.memory.rebuilder
    assert default_container.creative.novel
    assert default_container.creative.world
    assert default_container.creative.character
    assert default_container.creative.creator
    assert default_container.creative.catalog
    assert default_container.creative.repository
    assert default_container.creative.extensions.creator_learning
    assert default_container.creative.revisions
    assert default_container.consistency.service
    assert default_container.consistency.repository
    assert default_container.quality.service
    assert default_container.quality.repository
    assert default_container.feedback.service
    assert default_container.feedback.repository
    assert default_container.feedback.registry
    assert default_container.evolution.service
    assert default_container.evolution.memory
    assert isinstance(default_container.extensions.graph, NullGraphStore)
    assert all(
        item.state is CapabilityState.DISABLED
        for item in default_container.extensions.catalog.statuses()
    )
    assert len(default_container.extensions.multimodal) == 4
    assert default_container.models.gateway
    assert default_container.tools.gateway
    assert default_container.agents.supervisor
    assert len(default_container.agents.registry.all()) == 7
    assert default_container.workflows.service
    assert default_container.workflows.worker
    assert default_container.workflows.celery_app is not None
    assert (
        default_container.workflows.consumer_database.engine
        is not default_container.database.engine
    )
    assert isinstance(default_container.workflows.consumer_database.engine.pool, NullPool)
    asyncio.run(default_container.startup())
    asyncio.run(default_container.shutdown())

    publisher = MagicMock()
    injected_container = build_container(
        runtime_settings,
        clock=FixedClock(),
        probes=(HealthyProbe(),),
        event_publisher=publisher,
    )
    report = asyncio.run(injected_container.health.readiness())

    assert injected_container.settings is runtime_settings
    assert injected_container.workflows.celery_app is None
    assert report.status.value == "ready"
    assert report.timestamp == "2026-09-03T00:00:00Z"

    graph_container = build_container(
        replace(
            runtime_settings,
            features=replace(runtime_settings.features, graph_enabled=True),
        ),
        probes=(HealthyProbe(),),
        event_publisher=publisher,
    )
    graph_status = next(
        item
        for item in graph_container.extensions.catalog.statuses()
        if item.manifest.capability is ExtensionCapability.GRAPH
    )
    assert isinstance(graph_container.extensions.graph, SqlAlchemyExtensionGraphStore)
    assert graph_status.state is CapabilityState.AVAILABLE
    asyncio.run(graph_container.shutdown())
