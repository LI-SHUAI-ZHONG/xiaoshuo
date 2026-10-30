"""Deterministic Fake/Null model and secret provider adapters."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.modules.models.public import (
    ModelCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.modules.models.public import ModelRequest


class FakeModelScenario(StrEnum):
    """Deterministic behavior selectable by request idempotency key."""

    SUCCESS = "success"
    DELAY = "delay"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class FakeModelBehavior:
    """One configured fake outcome and fixed, bounded usage."""

    scenario: FakeModelScenario = FakeModelScenario.SUCCESS
    delay_seconds: float = 0.0
    input_tokens: int = 2
    output_tokens: int = 3

    def __post_init__(self) -> None:
        if self.delay_seconds < 0 or self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("fake model behavior values cannot be negative")


class FakeModelProvider:
    """No-network provider with deterministic references and scripted failures."""

    def __init__(
        self,
        provider_id: str = "fake-model",
        *,
        capabilities: frozenset[ModelCapability] | None = None,
        behaviors: Mapping[str, FakeModelBehavior] | None = None,
        default_behavior: FakeModelBehavior | None = None,
    ) -> None:
        if not provider_id:
            raise ValueError("fake provider id is required")
        self._provider_id = provider_id
        self._capabilities = capabilities or frozenset(
            {ModelCapability.TEXT, ModelCapability.EMBEDDING}
        )
        self._behaviors = dict(behaviors or {})
        self._default = default_behavior or FakeModelBehavior()
        self.calls: list[str] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def capabilities(self) -> frozenset[ModelCapability]:
        return self._capabilities

    async def invoke(self, request: ModelRequest) -> ProviderResult:
        """Execute one configured result without inspecting referenced content."""
        self.calls.append(request.idempotency_key)
        behavior = self._behaviors.get(request.idempotency_key, self._default)
        if behavior.delay_seconds:
            await asyncio.sleep(behavior.delay_seconds)
        if behavior.scenario is FakeModelScenario.TIMEOUT:
            await asyncio.sleep(3_600)
        if behavior.scenario is FakeModelScenario.RATE_LIMITED:
            raise ProviderError(ProviderErrorCode.RATE_LIMITED)
        if behavior.scenario is FakeModelScenario.FAILURE:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE)
        digest = hashlib.sha256(
            f"{self.provider_id}:{request.idempotency_key}:{request.capability.value}".encode()
        ).hexdigest()[:24]
        return ProviderResult(
            f"model-output://{self.provider_id}/{digest}",
            behavior.input_tokens,
            behavior.output_tokens,
        )


class NullModelProvider:
    """Explicitly unconfigured adapter for deferred multimodal capabilities."""

    def __init__(
        self,
        provider_id: str = "null-multimodal",
        *,
        capabilities: frozenset[ModelCapability] | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._capabilities = capabilities or frozenset(
            {
                ModelCapability.IMAGE,
                ModelCapability.AUDIO,
                ModelCapability.VIDEO,
                ModelCapability.THREE_D,
            }
        )

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def capabilities(self) -> frozenset[ModelCapability]:
        return self._capabilities

    async def invoke(self, request: ModelRequest) -> ProviderResult:
        """Return stable NOT_CONFIGURED through the shared provider failure contract."""
        del request
        raise ProviderError(ProviderErrorCode.NOT_CONFIGURED)


class NullSecretProvider:
    """Default secret adapter: no real provider credentials are configured."""

    async def credential_for(self, provider_id: str) -> str | None:
        del provider_id
        return None


class MappingSecretProvider:
    """In-memory adapter used to verify that credentials stay behind the port."""

    def __init__(self, credentials: Mapping[str, str]) -> None:
        self._credentials = dict(credentials)

    async def credential_for(self, provider_id: str) -> str | None:
        return self._credentials.get(provider_id)
