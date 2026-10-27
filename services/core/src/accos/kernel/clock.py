"""UTC clock and timestamp serialization contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Clock port used by deterministic runtime services."""

    def now(self) -> datetime:
        """Return a timezone-aware instant."""
        ...


class UtcClock:
    """System implementation of the UTC clock port."""

    def now(self) -> datetime:
        """Return the current UTC instant."""
        return datetime.now(tz=UTC)


def format_utc(value: datetime) -> str:
    """Serialize an aware instant as RFC 3339 UTC text."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
