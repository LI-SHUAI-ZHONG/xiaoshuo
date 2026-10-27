"""Structured logging with correlation context and redaction."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from accos.kernel.ids import CorrelationIds

_REDACTED = "<redacted>"
_SENSITIVE_KEY_PARTS = (
    "access_key",
    "api_key",
    "authorization",
    "actor_id",
    "content",
    "credential",
    "database_url",
    "memory",
    "password",
    "project_id",
    "prompt",
    "redis_url",
    "secret",
    "token",
    "user_id",
    "workspace_id",
)
_URL_CREDENTIALS = re.compile(r"(?<=://)[^/@\s]+@")
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")
_task_id: ContextVar[str] = ContextVar("task_id", default="-")
_runtime_context = {"service": "accos", "environment": "unknown"}


@dataclass(frozen=True, slots=True)
class CorrelationTokens:
    """Context tokens required to restore the prior logging context."""

    request: Token[str]
    trace: Token[str]
    task: Token[str]


def bind_correlation(correlation: CorrelationIds) -> CorrelationTokens:
    """Bind correlation identifiers for the current async context."""
    return CorrelationTokens(
        request=_request_id.set(correlation.request_id),
        trace=_trace_id.set(correlation.trace_id),
        task=_task_id.set(correlation.task_id or "-"),
    )


def reset_correlation(tokens: CorrelationTokens) -> None:
    """Restore the logging context that preceded a request or task."""
    _request_id.reset(tokens.request)
    _trace_id.reset(tokens.trace)
    _task_id.reset(tokens.task)


def current_correlation() -> CorrelationIds:
    """Read correlation identifiers from the current async context."""
    task_id = _task_id.get()
    return CorrelationIds(
        request_id=_request_id.get(),
        trace_id=_trace_id.get(),
        task_id=None if task_id == "-" else task_id,
    )


def redact_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Recursively remove common secret fields and URL user information."""
    return {key: _redact_value(key, value) for key, value in fields.items()}


def pseudonymous_ref(kind: str, value: object) -> str:
    """Return a stable non-reversible short reference for scoped identifiers."""
    digest = sha256(f"accos:{kind}:{value}".encode()).hexdigest()[:12]
    return f"{kind}:{digest}"


def _redact_value(key: str, value: object) -> object:
    normalized_key = key.lower()
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return _REDACTED
    if isinstance(value, Mapping):
        return redact_fields(
            {str(nested_key): nested_value for nested_key, nested_value in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return [_redact_value(key, item) for item in value]
    if isinstance(value, str):
        return _URL_CREDENTIALS.sub(f"{_REDACTED}@", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


class StructuredFormatter(logging.Formatter):
    """Emit one compact JSON object per runtime event."""

    def format(self, record: logging.LogRecord) -> str:
        event_data = getattr(record, "event_data", {})
        fields = redact_fields(event_data) if isinstance(event_data, Mapping) else {}
        payload: dict[str, object] = {
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": _runtime_context["service"],
            "environment": _runtime_context["environment"],
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": _request_id.get(),
            "trace_id": _trace_id.get(),
            "task_id": _task_id.get(),
            "workflow_id": "-",
            "agent_id": "-",
            "model_call_id": "-",
            "workspace_ref": "-",
            "project_ref": "-",
            "duration_ms": None,
            "outcome": "-",
            "error_code": "-",
            **fields,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(
    level: str,
    *,
    service: str = "accos",
    environment: str = "unknown",
) -> logging.Logger:
    """Configure the ACCOS logger without mutating unrelated application loggers."""
    _runtime_context.update(service=service, environment=environment)
    logger = logging.getLogger("accos")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.disabled = False
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child of the shared structured logger."""
    return logging.getLogger(f"accos.{name}")


def log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    """Log a named event after sanitizing structured fields."""
    logger.log(level, event, extra={"event_data": redact_fields(fields)})
