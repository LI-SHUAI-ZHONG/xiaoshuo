"""Bounded timeout, retry, backoff, circuit-breaker, and bulkhead policy."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from accos.kernel.errors import DependencyUnavailableError

T = TypeVar("T")
_MAX_OPERATION_NAME = 100


@dataclass(frozen=True, slots=True)
class ResiliencePolicy:
    """Shared external-call limits; every loop and wait is finite."""

    timeout_seconds: float
    max_attempts: int
    backoff_seconds: float
    max_backoff_seconds: float
    circuit_failure_threshold: int
    circuit_cooldown_seconds: float
    concurrency_limit: int

    def __post_init__(self) -> None:
        if (
            self.timeout_seconds <= 0
            or self.max_attempts < 1
            or self.backoff_seconds < 0
            or self.max_backoff_seconds <= 0
            or self.max_backoff_seconds < self.backoff_seconds
            or self.circuit_failure_threshold < 1
            or self.circuit_cooldown_seconds <= 0
            or self.concurrency_limit < 1
        ):
            raise ValueError("resilience policy values are invalid")


@dataclass(frozen=True, slots=True)
class CircuitSnapshot:
    """Credential-free diagnostic state for one named dependency operation."""

    operation: str
    consecutive_failures: int
    open: bool
    in_flight: int


@dataclass(slots=True)
class _Circuit:
    failures: int = 0
    open_until: float | None = None
    in_flight: int = 0


class ResilienceExecutor:
    """Apply one centralized policy independently to each named operation."""

    def __init__(
        self,
        policy: ResiliencePolicy,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._policy = policy
        self._monotonic = monotonic
        self._sleep = sleep
        self._circuits: dict[str, _Circuit] = {}
        self._bulkheads: dict[str, asyncio.Semaphore] = {}

    async def call(
        self,
        operation: str,
        invoke: Callable[[], Awaitable[T]],
        *,
        retryable: Callable[[Exception], bool] = lambda _error: True,
    ) -> T:
        """Execute a call or raise a stable dependency error after bounded attempts."""
        if not operation or len(operation) > _MAX_OPERATION_NAME:
            raise ValueError("resilience operation name is invalid")
        state = self._circuits.setdefault(operation, _Circuit())
        now = self._monotonic()
        if state.open_until is not None and now < state.open_until:
            raise DependencyUnavailableError("The external dependency circuit is open.")
        if state.open_until is not None:
            state.open_until = None
            state.failures = 0

        semaphore = self._bulkheads.setdefault(
            operation, asyncio.Semaphore(self._policy.concurrency_limit)
        )
        last_error: Exception | None = None
        for attempt in range(self._policy.max_attempts):
            try:
                async with asyncio.timeout(self._policy.timeout_seconds):
                    async with semaphore:
                        state.in_flight += 1
                        try:
                            result = await invoke()
                        finally:
                            state.in_flight -= 1
            except Exception as error:
                if not retryable(error):
                    raise
                last_error = error
                state.failures += 1
                if state.failures >= self._policy.circuit_failure_threshold:
                    state.open_until = self._monotonic() + self._policy.circuit_cooldown_seconds
                    break
                if attempt + 1 < self._policy.max_attempts:
                    delay = min(
                        self._policy.backoff_seconds * (2**attempt),
                        self._policy.max_backoff_seconds,
                    )
                    if delay:
                        await self._sleep(delay)
            else:
                state.failures = 0
                return result
        raise DependencyUnavailableError(
            "The external dependency is temporarily unavailable."
        ) from last_error

    def snapshots(self) -> tuple[CircuitSnapshot, ...]:
        """Return stable state without provider errors, identifiers, or credentials."""
        now = self._monotonic()
        return tuple(
            CircuitSnapshot(
                operation=name,
                consecutive_failures=state.failures,
                open=state.open_until is not None and now < state.open_until,
                in_flight=state.in_flight,
            )
            for name, state in sorted(self._circuits.items())
        )
