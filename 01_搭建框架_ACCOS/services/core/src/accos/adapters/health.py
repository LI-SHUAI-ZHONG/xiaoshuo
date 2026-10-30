"""Concrete dependency probes used only from the composition root."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlsplit

import redis
from minio import Minio
from urllib3 import PoolManager, Timeout

from accos.kernel.health import CheckStatus, HealthCheck


@dataclass(frozen=True, slots=True)
class RedisHealthProbe:
    """Verify Redis authentication and PING."""

    redis_url: str
    timeout_seconds: float
    name: str = "redis"
    critical: bool = True

    async def check(self) -> HealthCheck:
        """Run the blocking driver check outside the event loop."""
        await asyncio.to_thread(self._check_sync)
        return HealthCheck(self.name, CheckStatus.HEALTHY, self.critical, "pong")

    def _check_sync(self) -> None:
        client = redis.Redis.from_url(
            self.redis_url,
            socket_connect_timeout=self.timeout_seconds,
            socket_timeout=self.timeout_seconds,
            decode_responses=True,
        )
        try:
            if client.ping() is not True:
                raise RuntimeError("Redis health PING returned an invalid result")
        finally:
            client.close()


@dataclass(frozen=True, slots=True)
class S3HealthProbe:
    """Verify the configured S3 bucket is reachable with local credentials."""

    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    secure: bool
    region: str
    timeout_seconds: float = 2.0
    name: str = "object_storage"
    critical: bool = True

    async def check(self) -> HealthCheck:
        """Run the blocking client check outside the event loop."""
        await asyncio.to_thread(self._check_sync)
        return HealthCheck(self.name, CheckStatus.HEALTHY, self.critical, "bucket_ok")

    def _check_sync(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("object storage health timeout must be positive")
        parsed = urlsplit(self.endpoint)
        client = Minio(
            parsed.netloc,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            region=self.region,
            http_client=PoolManager(
                timeout=Timeout(
                    connect=self.timeout_seconds,
                    read=self.timeout_seconds,
                ),
                retries=False,
            ),
        )
        if not client.bucket_exists(self.bucket):
            raise RuntimeError("Configured S3 bucket is unavailable")


@dataclass(frozen=True, slots=True)
class AiProviderHealthProbe:
    """Describe optional provider state without making a real provider call."""

    enabled: bool
    provider: str | None
    name: str = "ai_provider"
    critical: bool = False

    async def check(self) -> HealthCheck:
        """Keep Fake mode ready while making optional state explicit."""
        if not self.enabled:
            return HealthCheck(
                self.name,
                CheckStatus.NOT_CONFIGURED,
                self.critical,
                "fake_mode",
            )
        if self.provider is None:
            return HealthCheck(
                self.name,
                CheckStatus.DEGRADED,
                self.critical,
                "provider_not_configured",
            )
        return HealthCheck(
            self.name,
            CheckStatus.DEGRADED,
            self.critical,
            "provider_probe_deferred",
        )
