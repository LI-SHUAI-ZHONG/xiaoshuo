"""T004–T010. Construction writes these tests; execution is deferred to stage 45."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from accos.adapters.identity.crypto import CredentialCipher, password_hash, password_matches
from accos.adapters.identity.oidc import HttpOidcClient
from accos.kernel.auth_settings import AUTH_DEFAULTS, AuthSettings
from accos.kernel.errors import (
    AuthenticationRequiredError,
    ConfigurationError,
    PermissionDeniedError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.identity.account_service import (
    AccountService,
    ApprovalPolicyResolver,
    LiveScopeAccess,
)
from accos.modules.identity.accounts import (
    MemberView,
    ScopeGrant,
    WorkspacePreferences,
    WorkspaceSettings,
)
from accos.modules.identity.application import ResourceScope
from accos.modules.identity.domain import Role, Workspace, permissions_for

NOW = datetime(2026, 9, 25, tzinfo=UTC)


def test_t004_password_hash_is_salted_and_rejects_bad_passwords() -> None:
    first = password_hash("acceptance-only-password-1")
    second = password_hash("acceptance-only-password-1")
    assert first != second and first.startswith("$argon2id$")
    assert password_matches(first, "acceptance-only-password-1")
    assert not password_matches(first, "wrong-password")
    assert not password_matches("invalid-hash", "wrong-password")


def test_t008_cipher_authenticates_workspace_version_and_master_key() -> None:
    key = base64.b64encode(bytes(range(32))).decode()
    cipher = CredentialCipher({"old": key}, "old")
    sealed = cipher.encrypt("acceptance-only-provider-secret", "workspace:a:credential:1")
    assert "provider-secret" not in sealed
    assert (
        cipher.decrypt(sealed, "old", "workspace:a:credential:1")
        == "acceptance-only-provider-secret"
    )
    with pytest.raises(ConfigurationError):
        cipher.decrypt(sealed, "old", "workspace:b:credential:1")
    with pytest.raises(ConfigurationError):
        cipher.decrypt(sealed, "old", "workspace:a:credential:2")
    with pytest.raises(ConfigurationError):
        CredentialCipher({}, "missing").encrypt("never-plaintext", "binding")
    with pytest.raises(ConfigurationError):
        CredentialCipher(
            {"old": base64.b64encode(bytes(reversed(range(32)))).decode()}, "old"
        ).decrypt(sealed, "old", "workspace:a:credential:1")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _signed(key: Any, claims: dict[str, Any], kid: str = "one", alg: str = "RS256") -> str:
    message = (
        _b64(json.dumps({"alg": alg, "kid": kid}).encode())
        + "."
        + _b64(json.dumps(claims).encode())
    )
    signature = pkcs1_15.new(key).sign(SHA256.new(message.encode()))
    return message + "." + _b64(signature)


def _jwk(key: Any, kid: str) -> dict[str, str]:
    return {
        "kid": kid,
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": _b64(key.n.to_bytes((key.n.bit_length() + 7) // 8, "big")),
        "e": _b64(key.e.to_bytes(3, "big")),
    }


def test_t005_pkce_rfc_vector_and_signed_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    key = RSA.generate(2048)
    config = AuthSettings(
        oidc_issuer="https://idp.example",
        oidc_client_id="studio",
        oidc_authorization_endpoint="https://idp.example/auth",
        oidc_token_endpoint="https://idp.example/token",
        oidc_jwks_uri="https://idp.example/keys",
    )
    client = HttpOidcClient(config)
    query = parse_qs(
        urlsplit(
            client.authorization_url(
                "state", "nonce", "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
            )
        ).query
    )
    assert query["code_challenge"] == ["E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"]
    assert query["code_challenge_method"] == ["S256"]
    monkeypatch.setattr(
        "accos.adapters.identity.oidc._fetch_json", lambda *_: {"keys": [_jwk(key, "one")]}
    )
    claims = {
        "iss": config.oidc_issuer,
        "sub": "subject-one",
        "aud": "studio",
        "iat": NOW.timestamp(),
        "exp": (NOW + timedelta(minutes=5)).timestamp(),
        "nonce": "nonce",
    }

    async def scenario() -> None:
        assert await client.verify_id_token(_signed(key, claims), "nonce", NOW) == (
            config.oidc_issuer,
            "subject-one",
        )
        for overrides in (
            {"iss": "https://wrong.example"},
            {"aud": "another-client"},
            {"exp": NOW.timestamp()},
            {"nonce": "replay"},
            {"aud": ["studio", "other"], "azp": "other"},
            {"nbf": NOW.timestamp() + 1000},
            {"exp": float("nan")},
        ):
            with pytest.raises(AuthenticationRequiredError):
                await client.verify_id_token(_signed(key, {**claims, **overrides}), "nonce", NOW)
        with pytest.raises(AuthenticationRequiredError):
            await client.verify_id_token(_signed(key, claims, alg="none"), "nonce", NOW)

    asyncio.run(scenario())


def test_t005_jwks_rotation_refreshes_unknown_signing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = RSA.generate(2048), RSA.generate(2048)
    client = HttpOidcClient(
        AuthSettings(
            oidc_issuer="https://idp.example",
            oidc_client_id="studio",
            oidc_jwks_uri="https://idp.example/keys",
        )
    )
    client._keys = [_jwk(old, "old")]
    client._refresh_at = time.monotonic() + 300
    calls: list[str] = []

    def fetch(url: str) -> dict[str, object]:
        calls.append(url)
        return {"keys": [_jwk(new, "new")]}

    monkeypatch.setattr("accos.adapters.identity.oidc._fetch_json", fetch)
    token = _signed(
        new,
        {
            "iss": "https://idp.example",
            "aud": "studio",
            "sub": "user",
            "nonce": "nonce",
            "iat": NOW.timestamp(),
            "exp": NOW.timestamp() + 60,
        },
        "new",
    )
    assert asyncio.run(client.verify_id_token(token, "nonce", NOW))[1] == "user"
    assert len(calls) == 1


def test_t005_authorization_endpoint_query_cannot_override_pkce_or_state() -> None:
    client = HttpOidcClient(
        AuthSettings(
            oidc_issuer="https://idp.example",
            oidc_client_id="studio",
            oidc_authorization_endpoint=(
                "https://idp.example/auth?tenant=writers&state=obsolete&client_id=wrong"
                "&redirect_uri=https%3A%2F%2Fevil.example&code_challenge=old"
            ),
            oidc_token_endpoint="https://idp.example/token",
            oidc_jwks_uri="https://idp.example/keys",
        )
    )
    query = parse_qs(urlsplit(client.authorization_url("fresh", "nonce", "verifier")).query)
    assert query["tenant"] == ["writers"]
    assert query["state"] == ["fresh"]
    assert query["client_id"] == ["studio"]
    assert query["redirect_uri"] == ["http://localhost:3000/api/v1/auth/oidc/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] != ["old"]


class PolicyFixture:
    def __init__(self) -> None:
        self.user, self.workspace, self.session = uuid4(), uuid4(), uuid4()
        self.active, self.session_valid = True, True
        self.role = Role.OWNER
        self.current_version = 1
        self.scope_grants: tuple[ScopeGrant, ...] = ()

    async def member(self, workspace: object, user: object) -> MemberView | None:
        if workspace != self.workspace or user != self.user:
            return None
        return MemberView(
            id=self.user,
            user_id=self.user,
            role=self.role,
            active=self.active,
            version=1,
            issuer="urn:accos:local",
            subject="author",
        )

    async def session_active(self, session: object, user: object, now: object) -> bool:
        return session == self.session and user == self.user and self.session_valid

    async def settings(self, workspace: Any, version: int | None = None) -> WorkspaceSettings:
        return WorkspaceSettings(
            workspace_id=workspace,
            version=self.current_version if version is None else version,
            values=WorkspacePreferences(
                approval_mode="human_owner"
                if (self.current_version if version is None else version) == 1
                else "dual_control"
            ),
        )

    async def get_workspace(self, workspace: Any) -> Workspace | None:
        return Workspace(workspace, self.user) if workspace == self.workspace else None

    async def grants(self, workspace: Any) -> tuple[ScopeGrant, ...]:
        return self.scope_grants if workspace == self.workspace else ()

    def context(self) -> SecurityContext:
        return SecurityContext(
            self.user,
            ActorKind.USER,
            self.workspace,
            permissions_for(self.role),
            "identity-auth-v2",
            CorrelationIds(str(uuid4()), str(uuid4())),
            auth_method="local",
            session_id=self.session,
        )


def test_t007_frozen_personal_team_legacy_and_machine_approval_policies() -> None:
    fixture = PolicyFixture()
    accounts = object.__new__(AccountService)
    accounts.store = cast(Any, fixture)
    accounts.clock = cast(Any, SimpleNamespace(now=lambda: NOW))
    resolver = ApprovalPolicyResolver(accounts)

    async def scenario() -> None:
        context = fixture.context()
        personal = await resolver.snapshot(fixture.workspace)
        await resolver.require_decision(context, fixture.user, personal)
        for reference in ("legacy_dual_control", f"workspace:{fixture.workspace}:v0"):
            with pytest.raises(PermissionDeniedError):
                await resolver.require_decision(context, fixture.user, reference)
        fixture.current_version = 2
        await resolver.require_decision(context, fixture.user, personal)
        team = await resolver.snapshot(fixture.workspace)
        with pytest.raises(PermissionDeniedError):
            await resolver.require_decision(context, fixture.user, team)
        await resolver.require_decision(context, uuid4(), team)
        for machine in (
            replace(context, actor_kind=ActorKind.SERVICE, auth_method="pat"),
            replace(context, auth_method="pat"),
            SecurityContext.from_task_headers(context.as_task_headers()),
        ):
            with pytest.raises(PermissionDeniedError):
                await resolver.require_decision(machine, uuid4(), personal)
        fixture.active = False
        with pytest.raises(PermissionDeniedError):
            await resolver.require_decision(context, uuid4(), personal)
        fixture.session_valid = False
        with pytest.raises(AuthenticationRequiredError):
            await resolver.require_decision(context, uuid4(), personal)

    asyncio.run(scenario())


def test_t006_project_and_creator_revocation_is_checked_on_every_read() -> None:
    fixture = PolicyFixture()
    fixture.role = Role.EDITOR
    policy = LiveScopeAccess(
        cast(Any, fixture), cast(Any, SimpleNamespace(now=lambda: NOW)), cast(Any, fixture)
    )
    project, creator = uuid4(), uuid4()
    grant = ScopeGrant(
        id=uuid4(),
        workspace_id=fixture.workspace,
        user_id=fixture.user,
        scope_kind="project",
        scope_id=project,
        permissions=("project:read",),
    )

    async def scenario() -> None:
        context = fixture.context()
        fixture.scope_grants = (grant,)
        assert await policy.allows(
            context,
            ResourceScope(fixture.workspace, "project", str(project), project),
            "project:read",
        )
        fixture.scope_grants = (grant.model_copy(update={"active": False}),)
        assert not await policy.allows(
            context,
            ResourceScope(fixture.workspace, "project", str(project), project),
            "project:read",
        )
        assert project in await policy.hidden_projects(context)
        assert not await policy.allows(
            context, ResourceScope(fixture.workspace, "creator", str(creator)), "project:read"
        )
        assert await policy.allows(
            context, ResourceScope(fixture.workspace, "creator", str(fixture.user)), "project:read"
        )
        fixture.active = False
        assert not await policy.allows(
            context, ResourceScope(fixture.workspace, "creator", str(fixture.user)), "project:read"
        )

    asyncio.run(scenario())


def test_t010_secret_values_are_not_workspace_preferences_and_hosts_are_explicit() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WorkspacePreferences.model_validate({"api_key": "must-not-be-plaintext"})
    with pytest.raises(ConfigurationError):
        AuthSettings.from_values(
            {**AUTH_DEFAULTS, "ACCOS_PUBLIC_ORIGIN": "http://192.168.1.20:3000"}
        )
    settings = AuthSettings.from_values(AUTH_DEFAULTS)
    assert not settings.oidc_configured and not settings.secure_cookie
