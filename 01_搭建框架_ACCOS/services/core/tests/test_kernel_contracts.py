from __future__ import annotations

import io
import json
import logging
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from accos.kernel.clock import UtcClock, format_utc
from accos.kernel.contracts import IdempotencyKey, PageRequest, VersionNumber
from accos.kernel.errors import (
    ConfigurationError,
    ErrorCode,
    InvalidStateError,
    KernelError,
    describe_exception,
)
from accos.kernel.ids import (
    CORRELATION_HEADER,
    ID_FORMAT,
    REQUEST_ID_HEADER,
    TASK_ID_HEADER,
    TRACE_ID_HEADER,
    CorrelationIds,
    new_id,
    parse_id,
    serialize_id,
)
from accos.kernel.logging import (
    StructuredFormatter,
    bind_correlation,
    configure_logging,
    current_correlation,
    get_logger,
    log_event,
    pseudonymous_ref,
    redact_fields,
    reset_correlation,
)
from accos.kernel.result import Failure, Result, Success

_REQUEST_ID = UUID("11111111-1111-4111-8111-111111111111")
_TRACE_ID = UUID("22222222-2222-4222-8222-222222222222")
_TASK_ID = UUID("33333333-3333-4333-8333-333333333333")


def test_uuid4_contract_and_serialization() -> None:
    identifier = new_id(factory=lambda: _REQUEST_ID)

    assert ID_FORMAT == "uuid4"
    assert identifier == _REQUEST_ID
    assert serialize_id(identifier) == str(_REQUEST_ID)
    assert parse_id(str(_REQUEST_ID)) == _REQUEST_ID


@pytest.mark.parametrize(
    "value",
    [
        "not-an-id",
        "00000000-0000-1000-8000-000000000000",
        "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
    ],
)
def test_uuid_parser_rejects_noncanonical_or_non_v4_values(value: str) -> None:
    with pytest.raises(ValueError, match="canonical UUIDv4"):
        parse_id(value)


def test_correlation_ids_preserve_valid_headers() -> None:
    correlation = CorrelationIds.from_headers(
        {
            REQUEST_ID_HEADER: str(_REQUEST_ID),
            TRACE_ID_HEADER: str(_TRACE_ID),
            TASK_ID_HEADER: str(_TASK_ID),
        }
    )

    assert correlation == CorrelationIds(str(_REQUEST_ID), str(_TRACE_ID), str(_TASK_ID))


def test_correlation_ids_use_alias_and_replace_invalid_values() -> None:
    generated = iter((_TRACE_ID, _TASK_ID))
    correlation = CorrelationIds.from_headers(
        {
            CORRELATION_HEADER: str(_REQUEST_ID),
            TRACE_ID_HEADER: "invalid",
            TASK_ID_HEADER: "invalid",
        },
        factory=lambda: next(generated),
    )

    assert correlation == CorrelationIds(str(_REQUEST_ID), str(_TRACE_ID), None)

    missing = CorrelationIds.from_headers({}, factory=lambda: _TASK_ID)
    assert missing == CorrelationIds(str(_TASK_ID), str(_TASK_ID), None)


def test_utc_clock_and_timestamp_contract() -> None:
    assert UtcClock().now().tzinfo is UTC
    source = datetime(2026, 9, 3, 12, 30, tzinfo=timezone(timedelta(hours=8)))

    assert format_utc(source) == "2026-09-03T04:30:00Z"
    with pytest.raises(ValueError, match="timezone-aware"):
        format_utc(datetime(2026, 9, 3))


def test_version_pagination_idempotency_and_result_contracts() -> None:
    assert VersionNumber("0.0.0").value == "0.0.0"
    assert PageRequest() == PageRequest(offset=0, limit=20)
    assert PageRequest(offset=2, limit=100).limit == 100
    assert IdempotencyKey("fixture-key").value == "fixture-key"
    results: tuple[Result[str, str], ...] = (
        Success("fixture-project"),
        Failure("fixture-error"),
    )
    assert isinstance(results[0], Success)
    assert results[0].value == "fixture-project"
    assert isinstance(results[1], Failure)
    assert results[1].error == "fixture-error"


@pytest.mark.parametrize("value", ["1", "01.2.3", "1.2.3-beta"])
def test_version_rejects_invalid_text(value: str) -> None:
    with pytest.raises(ValueError, match=r"major\.minor\.patch"):
        VersionNumber(value)


@pytest.mark.parametrize(
    ("offset", "limit", "message"),
    [(-1, 20, "offset"), (0, 0, "limit"), (0, 101, "limit")],
)
def test_pagination_rejects_invalid_bounds(offset: int, limit: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PageRequest(offset=offset, limit=limit)


@pytest.mark.parametrize("value", ["", " fixture", "x" * 129, "fixture-键"])
def test_idempotency_key_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="idempotency key"):
        IdempotencyKey(value)


def test_expected_and_unknown_error_descriptors() -> None:
    expected = KernelError(
        ErrorCode.DEPENDENCY_UNAVAILABLE,
        "Fixture dependency is unavailable.",
        status_code=503,
        details={"dependency": "fixture"},
    )
    expected_descriptor = describe_exception(expected)
    configuration = ConfigurationError("Fixture configuration is missing.")
    invalid_state = InvalidStateError("Fixture state is invalid.")
    unknown_descriptor = describe_exception(RuntimeError("sensitive implementation detail"))

    assert expected_descriptor.status_code == 503
    assert expected_descriptor.details == {"dependency": "fixture"}
    assert describe_exception(configuration).code is ErrorCode.CONFIGURATION_ERROR
    assert describe_exception(invalid_state).code is ErrorCode.INVALID_STATE
    assert unknown_descriptor.code is ErrorCode.INTERNAL_ERROR
    assert unknown_descriptor.message == "An unexpected error occurred."
    assert "sensitive" not in unknown_descriptor.message


def test_structured_logging_propagates_context_and_redacts_values() -> None:
    correlation = CorrelationIds(str(_REQUEST_ID), str(_TRACE_ID), str(_TASK_ID))
    tokens = bind_correlation(correlation)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("fixture-structured")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        assert current_correlation() == correlation
        log_event(
            logger,
            logging.INFO,
            "fixture_event",
            password="fixture-password",
            connection="redis://:fixture-secret@localhost/0",
            nested={"access_key": "fixture-access", "count": 2},
            values=(True, None),
            custom=VersionNumber("1.2.3"),
            actor_id=str(_REQUEST_ID),
            workspace_id=str(_TRACE_ID),
            prompt="fixture prompt",
        )
    finally:
        reset_correlation(tokens)

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "fixture_event"
    assert payload["request_id"] == str(_REQUEST_ID)
    assert payload["trace_id"] == str(_TRACE_ID)
    assert payload["task_id"] == str(_TASK_ID)
    assert payload["password"] == "<redacted>"
    assert "fixture-secret" not in stream.getvalue()
    assert payload["nested"] == {"access_key": "<redacted>", "count": 2}
    assert payload["values"] == [True, None]
    assert payload["actor_id"] == "<redacted>"
    assert payload["workspace_id"] == "<redacted>"
    assert payload["prompt"] == "<redacted>"
    assert "VersionNumber" in payload["custom"]
    assert current_correlation() == CorrelationIds("-", "-", None)


def test_logging_configuration_and_non_mapping_record_data() -> None:
    logger = configure_logging("WARNING", service="fixture-service", environment="test")
    child = get_logger("fixture")
    record = logging.LogRecord("fixture", logging.INFO, __file__, 1, "event", (), None)
    record.event_data = "not-a-mapping"

    assert logger.name == "accos"
    assert logger.level == logging.WARNING
    assert child.name == "accos.fixture"
    payload = json.loads(StructuredFormatter().format(record))
    assert payload["event"] == "event"
    assert payload["service"] == "fixture-service"
    assert payload["environment"] == "test"
    assert payload["workflow_id"] == "-"
    assert payload["duration_ms"] is None
    assert redact_fields({"authorization": "fixture", "value": 3.5}) == {
        "authorization": "<redacted>",
        "value": 3.5,
    }
    reference = pseudonymous_ref("workspace", _REQUEST_ID)
    assert reference.startswith("workspace:")
    assert str(_REQUEST_ID) not in reference
