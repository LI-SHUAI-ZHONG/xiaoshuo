from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from accos.composition import build_container
from accos.entrypoints.api import create_app, main
from accos.kernel.asyncio import selector_loop_factory
from accos.kernel.errors import ConfigurationError, InvalidStateError
from accos.kernel.health import CheckStatus, HealthCheck
from accos.kernel.ids import (
    CORRELATION_HEADER,
    REQUEST_ID_HEADER,
    TASK_ID_HEADER,
    TRACE_ID_HEADER,
    parse_id,
)

if TYPE_CHECKING:
    import pytest

    from accos.kernel.settings import RuntimeSettings

_REQUEST_ID = "11111111-1111-4111-8111-111111111111"
_TRACE_ID = "22222222-2222-4222-8222-222222222222"
_TASK_ID = "33333333-3333-4333-8333-333333333333"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 3, 1, 2, 3, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class StaticProbe:
    name: str
    status: CheckStatus
    critical: bool

    async def check(self) -> HealthCheck:
        return HealthCheck(self.name, self.status, self.critical, "fixture")


def test_live_ready_headers_and_logs_share_correlation(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    container = build_container(
        runtime_settings,
        clock=FixedClock(),
        probes=(
            StaticProbe("postgresql", CheckStatus.HEALTHY, True),
            StaticProbe("ai_provider", CheckStatus.NOT_CONFIGURED, False),
        ),
    )
    app = create_app(runtime_settings, container=container)

    with TestClient(app) as client:
        live = client.get(
            "/live",
            headers={
                REQUEST_ID_HEADER: _REQUEST_ID,
                TRACE_ID_HEADER: _TRACE_ID,
                TASK_ID_HEADER: _TASK_ID,
            },
        )
        ready = client.get("/ready")
        metrics = client.get("/metrics")
        openapi = client.get("/openapi.json")

    assert live.status_code == 200
    assert live.json() == {
        "status": "alive",
        "version": "0.0.0",
        "timestamp": "2026-09-03T01:02:03Z",
    }
    assert live.headers[CORRELATION_HEADER] == _REQUEST_ID
    assert live.headers[REQUEST_ID_HEADER] == _REQUEST_ID
    assert live.headers[TRACE_ID_HEADER] == _TRACE_ID
    assert live.headers[TASK_ID_HEADER] == _TASK_ID
    assert live.headers["cache-control"] == "no-store"
    assert live.headers["content-security-policy"].startswith("default-src")
    assert live.headers["permissions-policy"].startswith("camera=()")
    assert live.headers["referrer-policy"] == "no-referrer"
    assert live.headers["x-content-type-options"] == "nosniff"
    assert live.headers["x-frame-options"] == "DENY"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"][1]["status"] == "not_configured"
    assert metrics.status_code == 200
    assert "accos_api_request_duration_seconds" in metrics.text
    assert metrics.headers["content-type"].startswith("text/plain")
    assert openapi.status_code == 200
    assert openapi.json()["info"]["title"] == "ACCOS Core API"

    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    request_event = next(
        event
        for event in events
        if event["event"] == "request_completed" and event["path"] == "/live"
    )
    assert request_event["request_id"] == _REQUEST_ID
    assert request_event["trace_id"] == _TRACE_ID
    assert request_event["status_code"] == 200


def test_metrics_endpoint_can_be_explicitly_disabled(runtime_settings: RuntimeSettings) -> None:
    settings = replace(
        runtime_settings,
        observability=replace(runtime_settings.observability, metrics_enabled=False),
    )
    container = build_container(settings, probes=())
    with TestClient(create_app(settings, container=container, configure_logs=False)) as client:
        response = client.get("/metrics")

    assert response.status_code == 404


def test_ready_returns_503_when_a_critical_dependency_is_unavailable(
    runtime_settings: RuntimeSettings,
) -> None:
    container = build_container(
        runtime_settings,
        clock=FixedClock(),
        probes=(StaticProbe("redis", CheckStatus.UNAVAILABLE, True),),
    )

    with TestClient(
        create_app(runtime_settings, container=container, configure_logs=False)
    ) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_expected_validation_and_unknown_errors_use_safe_envelopes(
    runtime_settings: RuntimeSettings,
) -> None:
    app = create_app(
        runtime_settings,
        container=build_container(runtime_settings, clock=FixedClock(), probes=()),
        configure_logs=False,
    )

    @app.get("/fixture-configuration")
    async def configuration_error() -> None:
        raise ConfigurationError("Fixture configuration is missing.")

    @app.get("/fixture-state")
    async def state_error() -> None:
        raise InvalidStateError("Fixture state is invalid.")

    @app.get("/fixture-unknown")
    async def unknown_error() -> None:
        raise RuntimeError("fixture-sensitive-stack-detail")

    @app.get("/fixture-validation")
    async def validation(value: int) -> dict[str, int]:
        return {"value": value}

    with TestClient(app, raise_server_exceptions=False) as client:
        configuration = client.get(
            "/fixture-configuration", headers={CORRELATION_HEADER: _REQUEST_ID}
        )
        state = client.get("/fixture-state")
        unknown = client.get("/fixture-unknown")
        invalid = client.get("/fixture-validation", params={"value": "invalid"})

    assert configuration.status_code == 500
    assert configuration.json()["error"]["code"] == "configuration_error"
    assert configuration.json()["error"]["correlation_id"] == _REQUEST_ID
    assert configuration.headers[CORRELATION_HEADER] == _REQUEST_ID
    assert state.status_code == 409
    assert state.json()["error"]["code"] == "invalid_state"
    assert unknown.status_code == 500
    assert unknown.json()["error"]["code"] == "internal_error"
    assert "fixture-sensitive" not in unknown.text
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"
    assert invalid.json()["error"]["details"] == {"issue_count": 1}


def test_invalid_correlation_headers_are_replaced(runtime_settings: RuntimeSettings) -> None:
    app = create_app(
        runtime_settings,
        container=build_container(runtime_settings, clock=FixedClock(), probes=()),
        configure_logs=False,
    )

    with TestClient(app) as client:
        response = client.get(
            "/live",
            headers={
                REQUEST_ID_HEADER: "invalid",
                TRACE_ID_HEADER: "invalid",
                TASK_ID_HEADER: "invalid",
            },
        )

    assert parse_id(response.headers[REQUEST_ID_HEADER]).version == 4
    assert parse_id(response.headers[TRACE_ID_HEADER]).version == 4
    assert TASK_ID_HEADER not in response.headers


def test_application_factory_can_load_settings_and_build_container(
    runtime_settings: RuntimeSettings,
) -> None:
    container = build_container(runtime_settings, clock=FixedClock(), probes=())
    with (
        patch("accos.entrypoints.api.application.load_settings", return_value=runtime_settings),
        patch("accos.entrypoints.api.application.build_container", return_value=container) as build,
    ):
        app = create_app(configure_logs=False)

    assert isinstance(app, FastAPI)
    build.assert_called_once_with(runtime_settings)


def test_api_main_fails_fast_or_starts_uvicorn_safely(
    runtime_settings: RuntimeSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "accos.entrypoints.api.load_settings",
        side_effect=ConfigurationError("Missing required environment variables: FIXTURE"),
    ):
        assert main() == 2
    assert "configuration_error" in capsys.readouterr().err

    with (
        patch("accos.entrypoints.api.load_settings", return_value=runtime_settings),
        patch("accos.entrypoints.api.uvicorn.run") as run,
    ):
        assert main() == 0

    assert run.call_args.kwargs == {
        "host": "127.0.0.1",
        "port": 8000,
        "log_config": None,
        "access_log": False,
        "loop": "accos.kernel.asyncio:selector_loop_factory",
    }
    stderr = capsys.readouterr().err
    assert "api_configuration_loaded" in stderr
    assert "fixture-database-secret" not in stderr
    assert "fixture-object-secret" not in stderr

    with (
        patch("accos.entrypoints.api.load_settings", return_value=runtime_settings),
        patch("accos.entrypoints.api.uvicorn.run", side_effect=KeyboardInterrupt),
    ):
        assert main() == 0
    assert "api_shutdown_requested" in capsys.readouterr().err


def test_selector_loop_factory_is_compatible_with_async_psycopg() -> None:
    event_loop = selector_loop_factory()
    try:
        assert "Selector" in type(event_loop).__name__
    finally:
        event_loop.close()
