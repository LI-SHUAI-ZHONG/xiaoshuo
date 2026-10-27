"""Bounded timezone-aware schedule calculation and durable due-claim processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from accos.modules.workflows.domain import MisfirePolicy, WorkflowSchedule

if TYPE_CHECKING:
    from uuid import UUID

    from accos.modules.workflows.ports import WorkflowScheduleRepository

_FIELD_LIMITS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
_MAX_SEARCH_MINUTES = 527_040
_MAX_CATCH_UP_RUNS = 32


class ScheduledRunStarter(Protocol):
    """Reauthorize and start one run through the normal Workflow submission path."""

    async def start(
        self,
        schedule: WorkflowSchedule,
        *,
        scheduled_for: datetime,
        idempotency_key: str,
    ) -> UUID: ...


@dataclass(frozen=True, slots=True)
class ScheduleTick:
    """Content-free maintenance result suitable for health and audit projections."""

    claimed: int
    started: int
    skipped: int


class WorkflowScheduler:
    """Claim due schedules with DB fencing and feed the existing Workflow runtime."""

    def __init__(
        self,
        repository: WorkflowScheduleRepository,
        starter: ScheduledRunStarter,
        *,
        worker_id: str,
        lease_seconds: float = 30.0,
    ) -> None:
        if not worker_id or worker_id.strip() != worker_id or lease_seconds <= 0:
            raise ValueError("scheduler worker id and positive lease are required")
        self._repository = repository
        self._starter = starter
        self._worker_id = worker_id
        self._lease = timedelta(seconds=lease_seconds)

    async def tick(self, now: datetime) -> ScheduleTick:
        """Process one bounded batch; an unhandled start failure leaves the lease recoverable."""
        _require_aware(now)
        claimed = await self._repository.claim_due_schedules(
            now=now,
            lease=self._lease,
            worker_id=self._worker_id,
        )
        started = 0
        skipped = 0
        for schedule in claimed:
            if schedule.lease_token is None:
                continue
            due_times, next_due = due_occurrences(schedule, now)
            last_run_id: UUID | None = None
            for due_at in due_times:
                last_run_id = await self._starter.start(
                    schedule,
                    scheduled_for=due_at,
                    idempotency_key=(
                        f"{schedule.idempotency_prefix}:{due_at.astimezone(UTC).isoformat()}"
                    ),
                )
                started += 1
            if not due_times:
                skipped += 1
            await self._repository.settle_schedule_claim(
                schedule.id,
                schedule.lease_token,
                next_due_at=next_due,
                last_run_id=last_run_id,
                now=now,
            )
        return ScheduleTick(len(claimed), started, skipped)


def due_occurrences(
    schedule: WorkflowSchedule,
    now: datetime,
) -> tuple[tuple[datetime, ...], datetime]:
    """Apply explicit misfire semantics and return the next future due instant."""
    _require_aware(now)
    if schedule.next_due_at > now:
        return (), schedule.next_due_at
    cursor = schedule.next_due_at
    due: list[datetime] = []
    while cursor <= now:
        if schedule.misfire_policy is MisfirePolicy.CATCH_UP:
            due.append(cursor)
            if len(due) >= _MAX_CATCH_UP_RUNS:
                cursor = next_occurrence(schedule.schedule_expression, schedule.timezone, cursor)
                break
        elif schedule.misfire_policy is MisfirePolicy.FIRE_ONCE and not due:
            due.append(cursor)
        cursor = next_occurrence(schedule.schedule_expression, schedule.timezone, cursor)
    while cursor <= now:
        cursor = next_occurrence(schedule.schedule_expression, schedule.timezone, cursor)
    return tuple(due), cursor


def next_occurrence(expression: str, timezone: str, after: datetime) -> datetime:
    """Return the next matching minute for a restricted standard five-field cron."""
    _require_aware(after)
    fields = parse_cron(expression)
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise ValueError("schedule timezone is unknown") from None
    candidate = after.astimezone(UTC).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(_MAX_SEARCH_MINUTES):
        local = candidate.astimezone(zone)
        weekday = (local.weekday() + 1) % 7
        values = (local.minute, local.hour, local.day, local.month, weekday)
        if all(value in allowed for value, allowed in zip(values, fields, strict=True)):
            return candidate
        candidate += timedelta(minutes=1)
    raise ValueError("schedule has no occurrence within the bounded search horizon")


def parse_cron(expression: str) -> tuple[frozenset[int], ...]:
    """Parse bounded lists, ranges and steps; names and executable extensions are rejected."""
    raw_fields = expression.split()
    if len(raw_fields) != len(_FIELD_LIMITS):
        raise ValueError("schedule expression must contain five cron fields")
    return tuple(
        _parse_field(raw, minimum, maximum)
        for raw, (minimum, maximum) in zip(raw_fields, _FIELD_LIMITS, strict=True)
    )


def _parse_field(raw: str, minimum: int, maximum: int) -> frozenset[int]:
    values: set[int] = set()
    for part in raw.split(","):
        base, separator, raw_step = part.partition("/")
        step = _bounded_int(raw_step, 1, maximum - minimum + 1) if separator else 1
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            raw_start, raw_end = base.split("-", maxsplit=1)
            start = _bounded_int(raw_start, minimum, maximum)
            end = _bounded_int(raw_end, minimum, maximum)
            if end < start:
                raise ValueError("cron ranges must be ascending")
        else:
            start = _bounded_int(base, minimum, maximum)
            end = start
        values.update(range(start, end + 1, step))
    if not values:
        raise ValueError("cron field cannot be empty")
    return frozenset(values)


def _bounded_int(raw: str, minimum: int, maximum: int) -> int:
    if not raw.isascii() or not raw.isdecimal():
        raise ValueError("cron fields accept decimal values only")
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ValueError("cron field value is out of range")
    return value


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("schedule instants must be timezone-aware")
