"""Deterministic no-network fake tool executor."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.modules.tools.public import ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.modules.tools.public import ToolExecution


class FakeToolScenario(StrEnum):
    """Scriptable fake tool outcomes."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    FAILURE = "failure"
    INVALID_OUTPUT = "invalid_output"


@dataclass(frozen=True, slots=True)
class FakeToolBehavior:
    """One behavior selected by request idempotency key."""

    scenario: FakeToolScenario = FakeToolScenario.SUCCESS
    delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.delay_seconds < 0:
            raise ValueError("fake tool delay cannot be negative")


class FakeToolExecutor:
    """Return deterministic metadata without network, shell, or file access."""

    def __init__(self, behaviors: Mapping[str, FakeToolBehavior] | None = None) -> None:
        self._behaviors = dict(behaviors or {})
        self.calls: list[str] = []

    async def execute(self, execution: ToolExecution) -> ToolResult:
        request = execution.request
        self.calls.append(request.idempotency_key)
        behavior = self._behaviors.get(request.idempotency_key, FakeToolBehavior())
        if behavior.delay_seconds:
            await asyncio.sleep(behavior.delay_seconds)
        if behavior.scenario is FakeToolScenario.TIMEOUT:
            await asyncio.sleep(3_600)
        if behavior.scenario is FakeToolScenario.FAILURE:
            raise RuntimeError("fake tool configured failure")
        if behavior.scenario is FakeToolScenario.INVALID_OUTPUT:
            return ToolResult({"unexpected": True}, "tool-output://invalid")
        digest = hashlib.sha256(
            f"{execution.descriptor.tool_id}:{request.idempotency_key}".encode()
        ).hexdigest()[:24]
        reference = f"tool-output://{execution.descriptor.tool_id}/{digest}"
        return ToolResult({"reference": reference}, reference)
