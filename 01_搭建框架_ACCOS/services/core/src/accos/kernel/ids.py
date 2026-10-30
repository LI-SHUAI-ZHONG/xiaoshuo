"""UUID and correlation identifier contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

ID_FORMAT = "uuid4"
UUID4_VERSION = 4
CORRELATION_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
TASK_ID_HEADER = "X-Task-ID"


def new_id(*, factory: Callable[[], UUID] = uuid4) -> UUID:
    """Create the selected system identifier type."""
    return factory()


def serialize_id(identifier: UUID) -> str:
    """Serialize identifiers using canonical lowercase UUID text."""
    return str(identifier)


def parse_id(value: str) -> UUID:
    """Parse and enforce the UUIDv4 contract."""
    try:
        identifier = UUID(value)
    except (AttributeError, ValueError) as error:
        raise ValueError("identifier must be a canonical UUIDv4") from error
    if identifier.version != UUID4_VERSION or str(identifier) != value:
        raise ValueError("identifier must be a canonical UUIDv4")
    return identifier


@dataclass(frozen=True, slots=True)
class CorrelationIds:
    """Identifiers propagated across HTTP, task, and trace boundaries."""

    request_id: str
    trace_id: str
    task_id: str | None = None

    @classmethod
    def from_headers(
        cls,
        headers: Mapping[str, str],
        *,
        factory: Callable[[], UUID] = uuid4,
    ) -> CorrelationIds:
        """Accept canonical client identifiers or replace them safely."""
        request_value = headers.get(REQUEST_ID_HEADER) or headers.get(CORRELATION_HEADER)
        trace_value = headers.get(TRACE_ID_HEADER)
        return cls(
            request_id=_canonical_or_new(request_value, factory),
            trace_id=_canonical_or_new(trace_value, factory),
            task_id=_canonical_or_none(headers.get(TASK_ID_HEADER)),
        )


def _canonical_or_new(value: str | None, factory: Callable[[], UUID]) -> str:
    if value is not None:
        try:
            return serialize_id(parse_id(value))
        except ValueError:
            pass
    return serialize_id(new_id(factory=factory))


def _canonical_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return serialize_id(parse_id(value))
    except ValueError:
        return None
