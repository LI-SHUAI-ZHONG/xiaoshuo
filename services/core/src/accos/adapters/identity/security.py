"""Safe default adapters for rate limiting and pre-upload policy."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from accos.modules.identity.ports import RateLimitDecision

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from accos.kernel.security import SecurityContext


@dataclass(frozen=True, slots=True)
class DenyUploadsUntilAssetsStage:
    """Fail closed until execution 07 provides concrete upload validation."""

    async def permits(self, context: object, upload: object) -> bool:
        del context, upload
        return False


@dataclass(frozen=True, slots=True)
class DenyByDefaultRateLimiter:
    """Fail-closed adapter until a deployment configures concrete request budgets."""

    async def check(self, context: object, action: str) -> RateLimitDecision:
        del context, action
        return RateLimitDecision(allowed=False)


class InMemoryRateLimiter:
    """Bound one API process until the distributed limiter arrives in execution 22."""

    def __init__(
        self,
        *,
        max_requests: int = 120,
        window_seconds: float = 60.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_requests < 1 or window_seconds <= 0:
            raise ValueError("rate-limit budget and window must be positive")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._monotonic = monotonic
        self._buckets: dict[tuple[UUID, UUID, str], list[float]] = {}

    async def check(self, context: SecurityContext, action: str) -> RateLimitDecision:
        key = (context.actor_id, context.workspace_id, action)
        now = self._monotonic()
        active = [
            timestamp
            for timestamp in self._buckets.get(key, [])
            if now - timestamp < self._window_seconds
        ]
        if len(active) >= self._max_requests:
            retry_after = max(1, math.ceil(self._window_seconds - (now - active[0])))
            self._buckets[key] = active
            return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        active.append(now)
        self._buckets[key] = active
        return RateLimitDecision(allowed=True)
