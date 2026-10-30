from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from accos.kernel.errors import InvalidStateError
from accos.kernel.health import (
    CheckStatus,
    HealthCheck,
    HealthService,
    ReadinessStatus,
)
from accos.kernel.lifecycle import ModuleRegistry


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 3, 1, 2, 3, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class StaticProbe:
    name: str
    status: CheckStatus
    critical: bool

    async def check(self) -> HealthCheck:
        return HealthCheck(self.name, self.status, self.critical, "fixture")


@dataclass(frozen=True, slots=True)
class FailingProbe:
    name: str = "fixture-failing"
    critical: bool = True

    async def check(self) -> HealthCheck:
        raise RuntimeError("fixture-secret")


@dataclass(frozen=True, slots=True)
class SlowProbe:
    name: str = "fixture-slow"
    critical: bool = True

    async def check(self) -> HealthCheck:
        await asyncio.sleep(0.05)
        return HealthCheck(self.name, CheckStatus.HEALTHY, self.critical, "late")


@dataclass(slots=True)
class RecordingModule:
    name: str
    events: list[str]
    fail_startup: bool = False

    async def startup(self) -> None:
        self.events.append(f"start:{self.name}")
        if self.fail_startup:
            raise RuntimeError("fixture startup failure")

    async def shutdown(self) -> None:
        self.events.append(f"stop:{self.name}")


def test_liveness_and_ready_with_optional_not_configured() -> None:
    service = HealthService(
        probes=(
            StaticProbe("fixture-critical", CheckStatus.HEALTHY, True),
            StaticProbe("fixture-optional", CheckStatus.NOT_CONFIGURED, False),
        ),
        clock=FixedClock(),
        version="0.0.0",
        timeout_seconds=0.1,
    )

    live = service.liveness()
    ready = asyncio.run(service.readiness())

    assert live.as_dict() == {
        "status": "alive",
        "version": "0.0.0",
        "timestamp": "2026-09-03T01:02:03Z",
    }
    assert ready.status is ReadinessStatus.READY
    assert ready.http_status == 200
    assert ready.as_dict()["checks"] == [
        {
            "name": "fixture-critical",
            "status": "healthy",
            "critical": True,
            "detail": "fixture",
        },
        {
            "name": "fixture-optional",
            "status": "not_configured",
            "critical": False,
            "detail": "fixture",
        },
    ]


def test_readiness_contains_failures_and_timeouts_without_exception_text() -> None:
    service = HealthService(
        probes=(FailingProbe(), SlowProbe()),
        clock=FixedClock(),
        version="0.0.0",
        timeout_seconds=0.001,
    )

    report = asyncio.run(service.readiness())

    assert report.status is ReadinessStatus.NOT_READY
    assert report.http_status == 503
    assert [check.detail for check in report.checks] == ["check_failed", "timeout"]
    assert "fixture-secret" not in repr(report.as_dict())


def test_module_registry_orders_lifecycle_and_rejects_duplicate_or_double_start() -> None:
    events: list[str] = []
    registry = ModuleRegistry(
        (RecordingModule("kernel", events), RecordingModule("health", events))
    )

    assert registry.names == ("kernel", "health")
    asyncio.run(registry.startup())
    with pytest.raises(InvalidStateError, match="already started"):
        asyncio.run(registry.startup())
    asyncio.run(registry.shutdown())
    asyncio.run(registry.shutdown())

    assert events == ["start:kernel", "start:health", "stop:health", "stop:kernel"]
    with pytest.raises(ValueError, match="unique"):
        ModuleRegistry((RecordingModule("kernel", []), RecordingModule("kernel", [])))


def test_module_registry_rolls_back_partial_startup() -> None:
    events: list[str] = []
    registry = ModuleRegistry(
        (
            RecordingModule("kernel", events),
            RecordingModule("health", events, fail_startup=True),
        )
    )

    with pytest.raises(RuntimeError, match="startup failure"):
        asyncio.run(registry.startup())

    assert events == ["start:kernel", "start:health", "stop:kernel"]
