"""T005: browser callback recovery with explicit IdP/store doubles. Run only at 45.

These HTTP boundary cases do not replace the real IdP and PostgreSQL acceptance.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from accos.entrypoints.api.v1.account_router import accounts, router
from accos.kernel.auth_settings import AuthSettings
from accos.kernel.errors import AuthenticationRequiredError, ConfigurationError
from accos.modules.identity.account_ports import OidcFlow
from accos.modules.identity.account_service import AccountService, digest
from accos.modules.identity.accounts import WorkspaceChoice
from accos.modules.identity.domain import Role

NOW = datetime(2026, 9, 26, tzinfo=UTC)


@pytest.fixture
def callback() -> Iterator[SimpleNamespace]:
    user, workspace = uuid4(), uuid4()
    state, browser = "acceptance-state", "acceptance-browser"
    flow = OidcFlow(digest(state), digest(browser), "verifier", "nonce", NOW + timedelta(minutes=5))
    flows = {(flow.state_hash, flow.browser_hash): flow}

    async def consume(state_hash: str, browser_hash: str, now: datetime) -> OidcFlow | None:
        found = flows.get((state_hash, browser_hash))
        if found is None or found.expires_at <= now:
            return None
        return flows.pop((state_hash, browser_hash))

    store = SimpleNamespace(
        consume_oidc_flow=consume,
        oidc_user=AsyncMock(return_value=user),
        workspaces=AsyncMock(
            return_value=(WorkspaceChoice(id=workspace, name="验收", role=Role.OWNER),)
        ),
        add_session=AsyncMock(return_value=uuid4()),
    )
    service = object.__new__(AccountService)
    service.store = store
    service.config = AuthSettings(public_origin="https://studio.example")
    service.clock = SimpleNamespace(now=lambda: NOW)
    service._audit = None
    service._oidc = SimpleNamespace(
        exchange=AsyncMock(return_value=("https://idp.example", "author"))
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[accounts] = lambda: service
    with TestClient(app, base_url="https://studio.example", follow_redirects=False) as client:
        client.cookies.set("accos_oidc", browser, domain="studio.example", path="/api/v1")
        yield SimpleNamespace(
            client=client, service=service, store=store, state=state, browser=browser, flows=flows
        )


def test_t005_denial_consumes_flow_and_never_reflects_provider_description(
    callback: SimpleNamespace,
) -> None:
    response = callback.client.get(
        "/api/v1/auth/oidc/callback",
        params={
            "state": callback.state,
            "error": "access_denied",
            "error_description": "untrusted-secret-description",
        },
    )
    assert response.status_code == 303
    assert response.headers["location"] == "https://studio.example/login?auth_error=cancelled"
    assert "untrusted-secret-description" not in str(response.headers) + response.text
    assert not callback.flows
    assert callback.client.cookies.get("accos_oidc") is None
    assert (
        "HttpOnly" in response.headers["set-cookie"] and "Secure" in response.headers["set-cookie"]
    )
    callback.store.add_session.assert_not_awaited()
    callback.service._oidc.exchange.assert_not_awaited()
    replay = callback.client.get(
        "/api/v1/auth/oidc/callback", params={"state": callback.state, "code": "replay"}
    )
    assert replay.headers["location"].endswith("auth_error=failed")
    callback.store.add_session.assert_not_awaited()


def test_t005_wrong_browser_cannot_cancel_another_flow(callback: SimpleNamespace) -> None:
    callback.client.cookies.clear()
    response = callback.client.get(
        "/api/v1/auth/oidc/callback", params={"state": callback.state, "error": "access_denied"}
    )
    assert response.headers["location"].endswith("auth_error=failed")
    assert callback.flows
    callback.store.add_session.assert_not_awaited()


@pytest.mark.parametrize(
    "params", [{}, {"code": "orphan"}, {"state": "state", "code": "code", "error": "access_denied"}]
)
def test_t005_malformed_callback_returns_to_login(
    callback: SimpleNamespace, params: dict[str, str]
) -> None:
    response = callback.client.get("/api/v1/auth/oidc/callback", params=params)
    assert response.status_code == 303
    assert response.headers["location"].endswith("auth_error=failed")
    callback.store.add_session.assert_not_awaited()


@pytest.mark.parametrize(
    "error,reason",
    [
        (AuthenticationRequiredError(), "failed"),
        (ConfigurationError("private configuration detail"), "configuration_required"),
    ],
)
def test_t005_exchange_failures_clear_browser_flow(
    callback: SimpleNamespace, error: Exception, reason: str
) -> None:
    callback.service._oidc.exchange.side_effect = error
    response = callback.client.get(
        "/api/v1/auth/oidc/callback", params={"state": callback.state, "code": "secret-code"}
    )
    assert response.headers["location"] == "https://studio.example/login?auth_error=" + reason
    assert not callback.flows
    assert callback.client.cookies.get("accos_oidc") is None
    assert "secret-code" not in str(response.headers) + response.text
    callback.store.add_session.assert_not_awaited()


def test_t005_unprovisioned_identity_is_not_automatically_enrolled(
    callback: SimpleNamespace,
) -> None:
    callback.store.oidc_user.return_value = None
    response = callback.client.get(
        "/api/v1/auth/oidc/callback", params={"state": callback.state, "code": "unbound"}
    )
    assert response.headers["location"].endswith("auth_error=membership_required")
    callback.store.add_session.assert_not_awaited()


def test_t005_success_creates_session_and_redirects_to_dashboard(callback: SimpleNamespace) -> None:
    response = callback.client.get(
        "/api/v1/auth/oidc/callback", params={"state": callback.state, "code": "valid-code"}
    )
    assert response.headers["location"] == "https://studio.example/dashboard"
    callback.store.add_session.assert_awaited_once()
    assert callback.client.cookies.get("accos_session", "").startswith("accos_session_")
    assert callback.client.cookies.get("accos_oidc") is None
