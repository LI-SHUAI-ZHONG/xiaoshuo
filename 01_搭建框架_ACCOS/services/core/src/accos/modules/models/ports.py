"""Ports owned by the model gateway module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.modules.models.domain import (
        ModelCapability,
        ModelRequest,
        ProviderResult,
        UsageRecord,
    )


class ProviderErrorCode(StrEnum):
    """Failures a provider adapter may safely expose to the gateway."""

    NOT_CONFIGURED = "not_configured"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


class ProviderError(Exception):
    """Provider-neutral failure without raw vendor details."""

    def __init__(self, code: ProviderErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class ModelProvider(Protocol):
    """Vendor-independent text/embedding/multimodal provider contract."""

    @property
    def provider_id(self) -> str: ...

    @property
    def capabilities(self) -> frozenset[ModelCapability]: ...

    async def invoke(self, request: ModelRequest) -> ProviderResult: ...


@dataclass(frozen=True, slots=True)
class UsageTotals:
    """Current billable usage for workspace and task budget checks."""

    workspace_tokens: int
    workspace_calls: int
    task_tokens: int
    task_calls: int


class UsageLedger(Protocol):
    """Append-only usage and model call audit store."""

    async def totals(self, workspace_id: UUID, task_run_id: UUID) -> UsageTotals: ...

    async def append(self, record: UsageRecord) -> None: ...

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[UsageRecord, ...]: ...


class SecretProvider(Protocol):
    """Read credentials by provider without exposing them to domain objects."""

    async def credential_for(self, provider_id: str) -> str | None: ...
