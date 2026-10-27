"""PostgreSQL model configuration CAS, operation deduplication and recoverable queue."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, literal, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from accos.adapters.models.runtime_rows import (
    BudgetReservationRow,
    ModelBudgetSettingsRow,
    ModelCallEventRow,
    ModelCallRow,
    ModelPolicyRow,
    ModelProfileRow,
    PromptVersionRow,
)
from accos.adapters.persistence.database import AsyncSessionFactory
from accos.adapters.persistence.models import OutboxEventRow
from accos.kernel.errors import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from accos.kernel.security import SecurityContext
from accos.modules.models.invocation import TERMINAL, CallEvent, CallPage, CallRecord
from accos.modules.models.registry import BudgetSettings, BudgetView, ModelPolicyV2, ProviderProfile


async def workspace_lock(session: AsyncSession, workspace: UUID) -> None:
    key = int.from_bytes(
        hashlib.sha256(f"models:{workspace}".encode()).digest()[:8], "big", signed=True
    )
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def record(row: ModelCallRow) -> CallRecord:
    return CallRecord.model_validate(
        {
            **row.record,
            "status": row.status,
            "sequence": row.sequence,
            "cancel_requested": row.cancel_requested,
            "updated_at": row.updated_at,
        }
    )


def call_event(session: AsyncSession, row: ModelCallRow) -> None:
    value = record(row)
    session.add(
        ModelCallEventRow(
            call_id=row.id,
            sequence=row.sequence,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            data=CallEvent(
                call_id=row.id,
                sequence=row.sequence,
                status=value.status,
                content_ref=value.output_ref or value.partial_ref,
                created_at=row.updated_at,
            ).model_dump(mode="json"),
        )
    )


def settled_event(session: AsyncSession, call: CallRecord) -> None:
    session.add(
        OutboxEventRow(
            id=uuid4(),
            workspace_id=call.workspace_id,
            project_id=call.project_id,
            aggregate_id=call.id,
            event_type="models.call-settled",
            event_version=1,
            payload={
                "schema": "ModelCallSettled.v1",
                "payload_schema_version": 1,
                "aggregate_version": call.sequence,
                "reservation_ids": [str(value) for value in call.reservation_ids],
                "usage_ref": f"model-call://{call.id}/attempts",
                "call_id": str(call.id),
                "status": call.status,
                "billing_status": call.billing_status,
                "output_ref": call.output_ref.model_dump(mode="json") if call.output_ref else None,
            },
            occurred_at=call.updated_at,
            available_at=call.updated_at,
            created_at=call.updated_at,
            updated_at=call.updated_at,
        )
    )


class SqlModelStore:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self.sessions = sessions

    async def _configurations(
        self, workspace: UUID, table: type[ModelProfileRow] | type[ModelPolicyRow]
    ) -> tuple[dict[str, Any], ...]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(table)
                    .where(table.workspace_id == workspace)
                    .order_by(table.name, table.version.desc())
                )
            ).all()
        return tuple(cast(ModelProfileRow | ModelPolicyRow, row).data for row in rows)

    async def profiles(self, workspace: UUID) -> tuple[ProviderProfile, ...]:
        return tuple(
            ProviderProfile.model_validate(v)
            for v in await self._configurations(workspace, ModelProfileRow)
        )

    async def policies(self, workspace: UUID) -> tuple[ModelPolicyV2, ...]:
        return tuple(
            ModelPolicyV2.model_validate(v)
            for v in await self._configurations(workspace, ModelPolicyRow)
        )

    async def _configuration(
        self,
        workspace: UUID,
        name: str,
        version: int,
        table: type[ModelProfileRow] | type[ModelPolicyRow],
    ) -> dict[str, Any]:
        async with self.sessions() as session:
            row = await session.get(table, (workspace, name, version))
            if row is None:
                raise ResourceNotFoundError
            return cast(ModelProfileRow | ModelPolicyRow, row).data

    async def profile(self, workspace: UUID, name: str, version: int) -> ProviderProfile:
        return ProviderProfile.model_validate(
            await self._configuration(workspace, name, version, ModelProfileRow)
        )

    async def policy(self, workspace: UUID, name: str, version: int) -> ModelPolicyV2:
        return ModelPolicyV2.model_validate(
            await self._configuration(workspace, name, version, ModelPolicyRow)
        )

    async def _save(
        self,
        context: SecurityContext,
        value: ProviderProfile | ModelPolicyV2,
        expected: int,
        table: type[ModelProfileRow] | type[ModelPolicyRow],
    ) -> None:
        async with self.sessions.begin() as session:
            await workspace_lock(session, context.workspace_id)
            current = (
                await session.scalar(
                    select(func.max(table.version)).where(
                        table.workspace_id == context.workspace_id, table.name == value.id
                    )
                )
                or 0
            )
            previous = cast(
                ModelProfileRow | ModelPolicyRow | None,
                await session.get(table, (context.workspace_id, value.id, value.version)),
            )
            if previous is not None and value.version == expected + 1:
                if previous.data != value.model_dump(mode="json"):
                    raise IdempotencyConflictError
                return
            if current != expected or value.version != current + 1:
                raise ConcurrencyConflictError(current)
            session.add(
                table(
                    workspace_id=context.workspace_id,
                    name=value.id,
                    version=value.version,
                    data=value.model_dump(mode="json"),
                    created_by=context.actor_id,
                    created_at=datetime.now(UTC),
                )
            )

    async def save_profile(
        self, context: SecurityContext, profile: ProviderProfile, expected: int
    ) -> ProviderProfile:
        await self._save(context, profile, expected, ModelProfileRow)
        return profile

    async def save_policy(
        self, context: SecurityContext, policy: ModelPolicyV2, expected: int
    ) -> ModelPolicyV2:
        for pin in policy.route:
            await self.profile(context.workspace_id, pin.id, pin.version)
        await self._save(context, policy, expected, ModelPolicyRow)
        return policy

    async def budget(self, workspace: UUID) -> BudgetSettings:
        async with self.sessions() as session:
            row = await session.get(ModelBudgetSettingsRow, workspace)
            return BudgetSettings.model_validate(row.data) if row else BudgetSettings()

    async def save_budget(
        self, context: SecurityContext, value: BudgetSettings, expected: int
    ) -> BudgetSettings:
        async with self.sessions.begin() as session:
            await workspace_lock(session, context.workspace_id)
            row = await session.get(ModelBudgetSettingsRow, context.workspace_id)
            current = row.version if row else 0
            if expected != current:
                raise ConcurrencyConflictError(current)
            value = value.model_copy(update={"version": current + 1})
            if row is None:
                row = ModelBudgetSettingsRow(workspace_id=context.workspace_id)
                session.add(row)
            row.version, row.data, row.updated_by, row.updated_at = (
                value.version,
                value.model_dump(mode="json"),
                context.actor_id,
                datetime.now(UTC),
            )
        return value

    async def budget_view(self, workspace: UUID, now: datetime) -> BudgetView:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(BudgetReservationRow).where(
                        BudgetReservationRow.workspace_id == workspace,
                        BudgetReservationRow.day == now.date().isoformat(),
                    )
                )
            ).all()
        held = [r for r in rows if r.status in {"reserved", "unknown"}]
        spent = [r for r in rows if r.status == "settled"]
        return BudgetView(
            settings=await self.budget(workspace),
            day=now.date().isoformat(),
            reserved_tokens=sum(r.token_debit for r in held),
            spent_tokens=sum(r.token_debit for r in spent),
            reserved_micro_usd=sum(r.money_debit for r in held),
            spent_micro_usd=sum(r.money_debit for r in spent),
            unknown_count=sum(r.status == "unknown" for r in rows),
            calls=len(rows),
        )

    async def create_call(
        self,
        context: SecurityContext,
        call: CallRecord,
        digest: str,
        cache_key: str,
        headers: dict[str, str],
    ) -> CallRecord:
        async with self.sessions.begin() as session:
            await workspace_lock(session, context.workspace_id)
            row = await session.scalar(
                select(ModelCallRow).where(
                    ModelCallRow.workspace_id == call.workspace_id,
                    ModelCallRow.project_id == call.project_id,
                    ModelCallRow.actor_id == call.actor_id,
                    ModelCallRow.operation_key == call.operation_key,
                )
            )
            if row:
                if row.digest != digest:
                    raise IdempotencyConflictError
                return record(row)
            row = ModelCallRow(
                id=call.id,
                workspace_id=call.workspace_id,
                project_id=call.project_id,
                actor_id=call.actor_id,
                operation_key=call.operation_key,
                digest=digest,
                cache_key=cache_key,
                status=call.status,
                record=call.model_dump(mode="json"),
                security_headers=headers,
                sequence=1,
                cancel_requested=False,
                created_at=call.created_at,
                updated_at=call.updated_at,
            )
            session.add(row)
            await session.flush()
            call_event(session, row)
            return record(row)

    async def find_operation(
        self, context: SecurityContext, project: UUID, key: str, digest: str
    ) -> CallRecord | None:
        async with self.sessions() as session:
            row = await session.scalar(
                select(ModelCallRow).where(
                    ModelCallRow.workspace_id == context.workspace_id,
                    ModelCallRow.project_id == project,
                    ModelCallRow.actor_id == context.actor_id,
                    ModelCallRow.operation_key == key,
                )
            )
            if row and row.digest != digest:
                raise IdempotencyConflictError
            return record(row) if row else None

    async def get_call(self, workspace: UUID, project: UUID, call_id: UUID) -> CallRecord:
        async with self.sessions() as session:
            row = await session.scalar(
                select(ModelCallRow).where(
                    ModelCallRow.id == call_id,
                    ModelCallRow.workspace_id == workspace,
                    ModelCallRow.project_id == project,
                )
            )
            if row is None:
                raise ResourceNotFoundError
            return record(row)

    async def calls(
        self, workspace: UUID, project: UUID, cursor: str | None, limit: int
    ) -> CallPage:
        query = select(ModelCallRow).where(
            ModelCallRow.workspace_id == workspace, ModelCallRow.project_id == project
        )
        if cursor:
            try:
                stamp, identifier = cursor.rsplit("|", 1)
                query = query.where(
                    tuple_(ModelCallRow.created_at, ModelCallRow.id)
                    < tuple_(literal(datetime.fromisoformat(stamp)), literal(UUID(identifier)))
                )
            except ValueError:
                raise InvalidRequestError("Invalid model history cursor.") from None
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    query.order_by(ModelCallRow.created_at.desc(), ModelCallRow.id.desc()).limit(
                        min(100, max(1, limit)) + 1
                    )
                )
            ).all()
        page = rows[:limit]
        return CallPage(
            items=tuple(record(row) for row in page),
            next_cursor=f"{page[-1].created_at.isoformat()}|{page[-1].id}"
            if len(rows) > limit
            else None,
        )

    async def claim(
        self, call_id: UUID | None, now: datetime, lease_seconds: int
    ) -> tuple[CallRecord, dict[str, str]] | None:
        async with self.sessions.begin() as session:
            query = select(ModelCallRow).where(
                ModelCallRow.status == "queued", ModelCallRow.cancel_requested.is_(False)
            )
            if call_id:
                query = query.where(ModelCallRow.id == call_id)
            row = await session.scalar(
                query.order_by(ModelCallRow.created_at).with_for_update(skip_locked=True).limit(1)
            )
            if row is None:
                return None
            row.status, row.updated_at, row.lease_until = (
                "running",
                now,
                now + timedelta(seconds=lease_seconds),
            )
            row.sequence += 1
            call_event(session, row)
            return record(row), row.security_headers

    async def update_call(self, call: CallRecord, *, event: bool = True) -> CallRecord:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(ModelCallRow)
                .where(ModelCallRow.id == call.id, ModelCallRow.workspace_id == call.workspace_id)
                .with_for_update()
            )
            if row is None:
                raise ResourceNotFoundError
            if row.status in TERMINAL:
                return record(row)
            row.status, row.record, row.updated_at = (
                call.status,
                call.model_dump(mode="json"),
                call.updated_at,
            )
            if event:
                row.sequence += 1
                call_event(session, row)
            if call.status in TERMINAL:
                row.lease_until = None
                settled_event(session, record(row))
            return record(row)

    async def cancel(
        self, workspace: UUID, project: UUID, call_id: UUID, now: datetime
    ) -> CallRecord:
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(ModelCallRow)
                .where(
                    ModelCallRow.workspace_id == workspace,
                    ModelCallRow.project_id == project,
                    ModelCallRow.id == call_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ResourceNotFoundError
            if row.status not in TERMINAL:
                row.cancel_requested, row.updated_at = True, now
                if row.status == "queued":
                    row.status = "cancelled"
                    settled_event(session, record(row))
                row.sequence += 1
                call_event(session, row)
            return record(row)

    async def events(
        self, workspace: UUID, project: UUID, call_id: UUID, after: int, limit: int
    ) -> tuple[CallEvent, ...]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(ModelCallEventRow)
                    .where(
                        ModelCallEventRow.workspace_id == workspace,
                        ModelCallEventRow.project_id == project,
                        ModelCallEventRow.call_id == call_id,
                        ModelCallEventRow.sequence > after,
                    )
                    .order_by(ModelCallEventRow.sequence)
                    .limit(min(100, limit))
                )
            ).all()
        return tuple(CallEvent.model_validate(row.data) for row in rows)

    async def cached(
        self, workspace: UUID, project: UUID, fingerprint: str, since: datetime
    ) -> CallRecord | None:
        async with self.sessions() as session:
            row = await session.scalar(
                select(ModelCallRow)
                .where(
                    ModelCallRow.workspace_id == workspace,
                    ModelCallRow.project_id == project,
                    ModelCallRow.cache_key == fingerprint,
                    ModelCallRow.status == "completed",
                    ModelCallRow.created_at >= since,
                )
                .order_by(ModelCallRow.created_at.desc())
                .limit(1)
            )
            return record(row) if row else None

    async def recover_expired(self, now: datetime) -> int:
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(ModelCallRow)
                    .where(ModelCallRow.status == "running", ModelCallRow.lease_until < now)
                    .order_by(ModelCallRow.lease_until)
                    .with_for_update(skip_locked=True)
                    .limit(100)
                )
            ).all()
            for row in rows:
                value = record(row).model_copy(
                    update={
                        "status": "unknown",
                        "error_code": "WORKER_INTERRUPTED",
                        "billing_status": "unknown",
                        "updated_at": now,
                    }
                )
                row.status, row.record, row.updated_at, row.lease_until = (
                    value.status,
                    value.model_dump(mode="json"),
                    now,
                    None,
                )
                row.sequence += 1
                reservations = (
                    await session.scalars(
                        select(BudgetReservationRow)
                        .where(
                            BudgetReservationRow.call_id == row.id,
                            BudgetReservationRow.status == "reserved",
                        )
                        .with_for_update()
                    )
                ).all()
                for reservation in reservations:
                    reservation.status = "unknown"
                    reservation.data = {
                        **reservation.data,
                        "status": "unknown",
                        "error_code": "WORKER_INTERRUPTED",
                        "updated_at": now.isoformat(),
                    }
                call_event(session, row)
                settled_event(session, value)
            return len(rows)

    async def prompts(self, workspace: UUID) -> tuple[dict[str, Any], ...]:
        async with self.sessions() as session:
            return tuple(
                (
                    await session.scalars(
                        select(PromptVersionRow.data)
                        .where(PromptVersionRow.workspace_id == workspace)
                        .order_by(PromptVersionRow.name, PromptVersionRow.created_at)
                    )
                ).all()
            )

    async def prompt(self, workspace: UUID, name: str, version: str) -> dict[str, Any] | None:
        async with self.sessions() as session:
            row = await session.get(PromptVersionRow, (workspace, name, version))
            return row.data if row else None

    async def publish_prompt(
        self, context: SecurityContext, data: dict[str, Any], expected: str | None
    ) -> dict[str, Any]:
        async with self.sessions.begin() as session:
            await workspace_lock(session, context.workspace_id)
            versions = (
                await session.scalars(
                    select(PromptVersionRow.version).where(
                        PromptVersionRow.workspace_id == context.workspace_id,
                        PromptVersionRow.name == data["id"],
                    )
                )
            ).all()

            def key(v: str) -> tuple[int, ...]:
                return tuple(int(n) for n in v.split("."))

            latest = max(versions, key=key) if versions else None
            if (
                data["version"] in versions
                or (latest is not None and expected != latest)
                or (expected and key(data["version"]) <= key(expected))
            ):
                raise ConcurrencyConflictError
            session.add(
                PromptVersionRow(
                    workspace_id=context.workspace_id,
                    name=data["id"],
                    version=data["version"],
                    data=data,
                    created_by=context.actor_id,
                    created_at=datetime.now(UTC),
                )
            )
        return data
