"""Reservation contracts: an unknown external charge is never a free call."""

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from accos.kernel.shared_contracts import ContentRef, SharedContract
from accos.modules.models.invocation import CallRecord, TokenUsage
from accos.modules.models.registry import BudgetSettings, ModelPolicyV2, ProviderProfile


class Reservation(SharedContract):
    id: UUID
    call_id: UUID
    attempt: int
    profile_id: str
    profile_version: int
    price_version: str
    status: Literal["reserved", "settled", "released", "unknown"]
    reserved_tokens: int
    reserved_micro_usd: int
    usage: TokenUsage | None = None
    cost_micro_usd: int | None = None
    provider_request_id: str | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class BudgetLedger(Protocol):
    async def reserve(
        self,
        call: CallRecord,
        profile: ProviderProfile,
        policy: ModelPolicyV2,
        settings: BudgetSettings,
        daily_tokens: int,
        task_id: UUID,
        estimate: TokenUsage,
        now: datetime,
    ) -> Reservation: ...
    async def settle(
        self,
        reservation: Reservation,
        usage: TokenUsage | None,
        cost: int | None,
        provider_request_id: str | None,
        error: str | None,
        *,
        released: bool = False,
    ) -> Reservation: ...
    async def reservations(self, workspace: UUID, call_id: UUID) -> tuple[Reservation, ...]: ...
    async def reconcile(
        self,
        workspace: UUID,
        reservation_id: UUID,
        usage: TokenUsage,
        cost: int,
        evidence: ContentRef,
        actor: UUID,
    ) -> Reservation: ...


class QuotaLease(Protocol):
    async def release(self) -> None: ...


class SharedQuota(Protocol):
    async def acquire(
        self, workspace: UUID, profile_id: str, settings: BudgetSettings, seconds: float
    ) -> QuotaLease: ...
