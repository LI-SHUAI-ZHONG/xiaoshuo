"""Atomic PG accounting and Redis quotas shared by every API/Worker process."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import func, select

from accos.adapters.models.runtime_rows import BudgetReservationRow, ModelCallRow
from accos.adapters.models.runtime_store import call_event, record, settled_event, workspace_lock
from accos.adapters.persistence.database import AsyncSessionFactory
from accos.kernel.errors import InvalidStateError, ResourceNotFoundError
from accos.kernel.shared_contracts import ContentRef
from accos.modules.models.budgets import Reservation
from accos.modules.models.invocation import CallRecord, ModelRuntimeError, TokenUsage
from accos.modules.models.registry import BudgetSettings, ModelPolicyV2, ProviderProfile


class SqlBudgetLedger:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self.sessions = sessions

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
    ) -> Reservation:
        cost = profile.price.cost(estimate, reservation=True)
        if cost is None:
            cost = policy.unknown_price_hold_micro_usd
        if cost is None:
            raise ModelRuntimeError("PRICE_REQUIRED")
        async with self.sessions.begin() as session:
            await workspace_lock(session, call.workspace_id)
            daily = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(BudgetReservationRow.token_debit), 0),
                        func.coalesce(func.sum(BudgetReservationRow.money_debit), 0),
                        func.count(),
                    ).where(
                        BudgetReservationRow.workspace_id == call.workspace_id,
                        BudgetReservationRow.day == now.date().isoformat(),
                    )
                )
            ).one()
            task = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(BudgetReservationRow.token_debit), 0),
                        func.coalesce(func.sum(BudgetReservationRow.money_debit), 0),
                        func.count(),
                    ).where(
                        BudgetReservationRow.workspace_id == call.workspace_id,
                        BudgetReservationRow.task_id == task_id,
                    )
                )
            ).one()
            if (
                daily[0] + estimate.total > daily_tokens
                or daily[1] + cost > settings.daily_cost_limit_micro_usd
                or daily[2] >= settings.daily_call_limit
                or task[0] + estimate.total > policy.task_token_limit
                or task[1] + cost > policy.task_cost_limit_micro_usd
                or task[2] >= policy.task_call_limit
            ):
                raise ModelRuntimeError("BUDGET_EXHAUSTED")
            attempt = (
                int(
                    await session.scalar(
                        select(func.count())
                        .select_from(BudgetReservationRow)
                        .where(BudgetReservationRow.call_id == call.id)
                    )
                    or 0
                )
                + 1
            )
            reservation = Reservation(
                id=uuid4(),
                call_id=call.id,
                attempt=attempt,
                profile_id=profile.id,
                profile_version=profile.version,
                price_version=profile.price.version,
                status="reserved",
                reserved_tokens=estimate.total,
                reserved_micro_usd=cost,
                created_at=now,
                updated_at=now,
            )
            session.add(
                BudgetReservationRow(
                    id=reservation.id,
                    workspace_id=call.workspace_id,
                    project_id=call.project_id,
                    task_id=task_id,
                    call_id=call.id,
                    attempt=attempt,
                    day=now.date().isoformat(),
                    status="reserved",
                    token_debit=estimate.total,
                    money_debit=cost,
                    data=reservation.model_dump(mode="json"),
                )
            )
        return reservation

    async def settle(
        self,
        reservation: Reservation,
        usage: TokenUsage | None,
        cost: int | None,
        provider_request_id: str | None,
        error: str | None,
        *,
        released: bool = False,
    ) -> Reservation:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(BudgetReservationRow)
                .where(BudgetReservationRow.id == reservation.id)
                .with_for_update()
            )
            if row is None:
                raise ResourceNotFoundError
            if row.status != "reserved":
                return Reservation.model_validate(row.data)
            state = (
                "released"
                if released
                else "settled"
                if usage is not None and cost is not None
                else "unknown"
            )
            value = reservation.model_copy(
                update={
                    "status": state,
                    "usage": usage,
                    "cost_micro_usd": 0 if released else cost,
                    "provider_request_id": provider_request_id,
                    "error_code": error,
                    "updated_at": datetime.now(UTC),
                }
            )
            row.status, row.data = state, value.model_dump(mode="json")
            row.token_debit = (
                0 if released else usage.total if usage else reservation.reserved_tokens
            )
            row.money_debit = (
                0 if released else cost if cost is not None else reservation.reserved_micro_usd
            )
        return value

    async def reservations(self, workspace: UUID, call_id: UUID) -> tuple[Reservation, ...]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(BudgetReservationRow)
                    .where(
                        BudgetReservationRow.workspace_id == workspace,
                        BudgetReservationRow.call_id == call_id,
                    )
                    .order_by(BudgetReservationRow.attempt)
                )
            ).all()
        return tuple(Reservation.model_validate(row.data) for row in rows)

    async def reconcile(
        self,
        workspace: UUID,
        reservation_id: UUID,
        usage: TokenUsage,
        cost: int,
        evidence: ContentRef,
        actor: UUID,
    ) -> Reservation:
        if cost < 0:
            raise InvalidStateError("Reconciled cost cannot be negative.")
        async with self.sessions.begin() as session:
            await workspace_lock(session, workspace)
            row = await session.scalar(
                select(BudgetReservationRow)
                .where(
                    BudgetReservationRow.workspace_id == workspace,
                    BudgetReservationRow.id == reservation_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ResourceNotFoundError
            proof = {
                "evidence_ref": evidence.model_dump(mode="json"),
                "actor_id": str(actor),
                "usage": usage.model_dump(mode="json"),
                "cost_micro_usd": cost,
            }
            if row.status == "settled" and row.reconciliation == proof:
                value = Reservation.model_validate(row.data)
            elif row.status != "unknown":
                raise InvalidStateError("Only an unknown charge can be reconciled.")
            else:
                value = Reservation.model_validate(row.data).model_copy(
                    update={
                        "status": "settled",
                        "usage": usage,
                        "cost_micro_usd": cost,
                        "updated_at": datetime.now(UTC),
                    }
                )
                row.status, row.data, row.token_debit, row.money_debit, row.reconciliation = (
                    "settled",
                    value.model_dump(mode="json"),
                    usage.total,
                    cost,
                    proof,
                )
            await session.flush()
        # Separate lock order from call recovery (call -> reservations).
        await self._refresh_call(workspace, value.call_id)
        return value

    async def _refresh_call(self, workspace: UUID, call_id: UUID) -> None:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(ModelCallRow)
                .where(ModelCallRow.id == call_id, ModelCallRow.workspace_id == workspace)
                .with_for_update()
            )
            if row is None:
                return
            values = (
                await session.scalars(
                    select(BudgetReservationRow).where(BudgetReservationRow.call_id == call_id)
                )
            ).all()
            if any(r.status in {"unknown", "reserved"} for r in values):
                return
            # Reconciliation cannot turn an interrupted generation into completed output.
            usages = [Reservation.model_validate(r.data).usage for r in values]
            usage = TokenUsage(
                input_tokens=sum(u.input_tokens for u in usages if u),
                output_tokens=sum(u.output_tokens for u in usages if u),
                cached_input_tokens=sum(u.cached_input_tokens for u in usages if u),
            )
            updated = {
                **row.record,
                "billing_status": "settled",
                "cost_micro_usd": sum(r.money_debit for r in values),
                "usage": usage.model_dump(mode="json"),
                "reservation_ids": [str(r.id) for r in values],
            }
            if updated == row.record:
                return
            row.record = updated
            row.updated_at = datetime.now(UTC)
            row.sequence += 1
            call_event(session, row)
            settled_event(session, record(row))


_ACQUIRE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now - 60000)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[2]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[3]), ARGV[4])
redis.call('ZADD', KEYS[2], now, ARGV[4])
redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[3]) + 60000)
redis.call('PEXPIRE', KEYS[2], 120000)
return 1
"""


class RedisQuotaLease:
    def __init__(self, client: Redis, key: str, token: str) -> None:
        self.client, self.key, self.token = client, key, token

    async def release(self) -> None:
        try:
            await self.client.zrem(self.key, self.token)
        finally:
            await self.client.aclose()


class RedisModelQuota:
    def __init__(self, url: str) -> None:
        self.url = url

    async def acquire(
        self, workspace: UUID, profile_id: str, settings: BudgetSettings, seconds: float
    ) -> RedisQuotaLease:
        # Workspace-wide quota is shared across fallback profiles as well as workers.
        del profile_id
        prefix = "accos:model-quota:{" + hashlib.sha256(str(workspace).encode()).hexdigest() + "}"
        client = Redis.from_url(self.url, socket_timeout=3, socket_connect_timeout=3)
        token = str(uuid4())
        try:
            ok = await client.eval(
                _ACQUIRE,
                2,
                prefix + ":active",
                prefix + ":minute",
                settings.concurrent_calls,
                settings.requests_per_minute,
                int((seconds + 10) * 1000),
                token,
            )
            if not ok:
                raise ModelRuntimeError("SHARED_QUOTA_EXCEEDED", retryable=True)
        except Exception as error:
            await client.aclose()
            if isinstance(error, ModelRuntimeError):
                raise
            raise ModelRuntimeError("QUOTA_UNAVAILABLE") from None
        return RedisQuotaLease(client, prefix + ":active", token)
