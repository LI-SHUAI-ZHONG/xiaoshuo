"""Framework-neutral liveness and dependency readiness aggregation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from accos.kernel.clock import Clock, format_utc


class CheckStatus(StrEnum):
    """State of one runtime dependency."""

    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"


class ReadinessStatus(StrEnum):
    """Process readiness derived from critical dependency checks."""

    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """Sanitized result from one dependency probe."""

    name: str
    status: CheckStatus
    critical: bool
    detail: str

    def as_dict(self) -> dict[str, str | bool]:
        """Serialize the public check contract."""
        return {
            "name": self.name,
            "status": self.status.value,
            "critical": self.critical,
            "detail": self.detail,
        }


class HealthProbe(Protocol):
    """Port implemented by concrete infrastructure health adapters."""

    @property
    def name(self) -> str:
        """Stable dependency name."""
        ...

    @property
    def critical(self) -> bool:
        """Whether failure must make the process not ready."""
        ...

    async def check(self) -> HealthCheck:
        """Check a dependency without leaking connection details."""
        ...


@dataclass(frozen=True, slots=True)
class LivenessReport:
    """Process-only liveness response."""

    status: str
    version: str
    timestamp: str

    def as_dict(self) -> dict[str, str]:
        """Serialize the liveness contract."""
        return {"status": self.status, "version": self.version, "timestamp": self.timestamp}


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregated critical and optional dependency state."""

    status: ReadinessStatus
    version: str
    timestamp: str
    checks: tuple[HealthCheck, ...]

    @property
    def http_status(self) -> int:
        """Translate readiness to the health endpoint status code."""
        return 200 if self.status is ReadinessStatus.READY else 503

    def as_dict(self) -> dict[str, object]:
        """Serialize the readiness contract."""
        return {
            "status": self.status.value,
            "version": self.version,
            "timestamp": self.timestamp,
            "checks": [check.as_dict() for check in self.checks],
        }


class HealthService:
    """Run dependency probes with a shared timeout and safe fallback."""

    def __init__(
        self,
        *,
        probes: tuple[HealthProbe, ...],
        clock: Clock,
        version: str,
        timeout_seconds: float,
    ) -> None:
        self._probes = probes
        self._clock = clock
        self._version = version
        self._timeout_seconds = timeout_seconds

    def liveness(self) -> LivenessReport:
        """Report only whether this process can answer requests."""
        return LivenessReport(
            status="alive",
            version=self._version,
            timestamp=format_utc(self._clock.now()),
        )

    async def readiness(self) -> ReadinessReport:
        """Aggregate all configured dependency probes."""
        checks = tuple(await asyncio.gather(*(self._safe_check(probe) for probe in self._probes)))
        ready = all(check.status is CheckStatus.HEALTHY for check in checks if check.critical)
        return ReadinessReport(
            status=ReadinessStatus.READY if ready else ReadinessStatus.NOT_READY,
            version=self._version,
            timestamp=format_utc(self._clock.now()),
            checks=checks,
        )

    async def _safe_check(self, probe: HealthProbe) -> HealthCheck:
        try:
            return await asyncio.wait_for(probe.check(), timeout=self._timeout_seconds)
        except TimeoutError:
            return HealthCheck(
                name=probe.name,
                status=CheckStatus.UNAVAILABLE,
                critical=probe.critical,
                detail="timeout",
            )
        except Exception:  # noqa: BLE001 - health boundaries must contain adapter failures.
            return HealthCheck(
                name=probe.name,
                status=CheckStatus.UNAVAILABLE,
                critical=probe.critical,
                detail="check_failed",
            )
