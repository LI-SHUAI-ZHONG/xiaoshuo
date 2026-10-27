"""Public model content, persistence, provider and quota ports."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import ContentRef
from accos.modules.models.invocation import (
    CallEvent,
    CallPage,
    CallRecord,
    ModelInvocation,
    ProviderChunk,
    ProviderOutput,
)
from accos.modules.models.registry import BudgetSettings, BudgetView, ModelPolicyV2, ProviderProfile


class ContentStore(Protocol):
    async def read_snapshot(
        self, context: SecurityContext, project_id: UUID, ref: ContentRef
    ) -> bytes: ...
    async def put_snapshot(
        self, context: SecurityContext, project_id: UUID, data: bytes, *, media_type: str
    ) -> ContentRef: ...


class ContentProvider(Protocol):
    async def invoke(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput: ...
    def stream(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> AsyncIterator[ProviderChunk]: ...
    async def embed(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput: ...


class ModelStore(Protocol):
    async def profiles(self, workspace: UUID) -> tuple[ProviderProfile, ...]: ...
    async def profile(self, workspace: UUID, name: str, version: int) -> ProviderProfile: ...
    async def save_profile(
        self, context: SecurityContext, profile: ProviderProfile, expected: int
    ) -> ProviderProfile: ...
    async def policies(self, workspace: UUID) -> tuple[ModelPolicyV2, ...]: ...
    async def policy(self, workspace: UUID, name: str, version: int) -> ModelPolicyV2: ...
    async def save_policy(
        self, context: SecurityContext, policy: ModelPolicyV2, expected: int
    ) -> ModelPolicyV2: ...
    async def budget(self, workspace: UUID) -> BudgetSettings: ...
    async def save_budget(
        self, context: SecurityContext, value: BudgetSettings, expected: int
    ) -> BudgetSettings: ...
    async def budget_view(self, workspace: UUID, now: datetime) -> BudgetView: ...
    async def create_call(
        self,
        context: SecurityContext,
        call: CallRecord,
        digest: str,
        cache_key: str,
        headers: dict[str, str],
    ) -> CallRecord: ...
    async def find_operation(
        self, context: SecurityContext, project: UUID, key: str, digest: str
    ) -> CallRecord | None: ...
    async def get_call(self, workspace: UUID, project: UUID, call_id: UUID) -> CallRecord: ...
    async def calls(
        self, workspace: UUID, project: UUID, cursor: str | None, limit: int
    ) -> CallPage: ...
    async def claim(
        self, call_id: UUID | None, now: datetime, lease_seconds: int
    ) -> tuple[CallRecord, dict[str, str]] | None: ...
    async def update_call(self, call: CallRecord, *, event: bool = True) -> CallRecord: ...
    async def cancel(
        self, workspace: UUID, project: UUID, call_id: UUID, now: datetime
    ) -> CallRecord: ...
    async def events(
        self, workspace: UUID, project: UUID, call_id: UUID, after: int, limit: int
    ) -> tuple[CallEvent, ...]: ...
    async def cached(
        self, workspace: UUID, project: UUID, fingerprint: str, since: datetime
    ) -> CallRecord | None: ...
    async def recover_expired(self, now: datetime) -> int: ...
    async def publish_prompt(
        self, context: SecurityContext, data: dict[str, Any], expected: str | None
    ) -> dict[str, Any]: ...
    async def prompts(self, workspace: UUID) -> tuple[dict[str, Any], ...]: ...
    async def prompt(self, workspace: UUID, name: str, version: str) -> dict[str, Any] | None: ...
