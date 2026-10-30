"""Real PostgreSQL/HTTP identity acceptance. Explicit isolated acceptance DB only; run at 45."""

from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Iterator
from uuid import UUID, uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from accos.adapters.identity.accounts import SqlAccountStore
from accos.adapters.identity.crypto import password_hash
from accos.adapters.identity.persistence import AuditEventRow, MembershipRow, WorkspaceRow
from accos.adapters.persistence import DatabaseRuntime
from accos.composition import build_container
from accos.entrypoints.api import create_app
from accos.kernel.auth_settings import AuthSettings
from accos.kernel.errors import (
    ConcurrencyConflictError,
    ConfigurationError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import SecurityContext
from accos.kernel.settings import RuntimeSettings
from accos.modules.identity.account_ports import OidcFlow
from accos.modules.identity.account_service import ApprovalPolicyResolver, digest
from accos.modules.identity.accounts import ScopeGrant, WorkspacePreferences
from accos.modules.identity.application import (
    AuthorizationRequest,
    ControlRequestDraft,
    ResourceScope,
)
from accos.modules.identity.domain import ApprovalDecision, ControlRequestKind, Permission, Role
from test_persistence import TemporaryDatabaseFactory, migration_config


@pytest.fixture
def account_database() -> Iterator[str]:
    url = os.environ.get("ACCOS_ACCEPTANCE_DATABASE_URL")
    if not url:
        pytest.skip("Stage 45: explicit isolated PostgreSQL admin URL is required.")
    # This existing fixture always creates/drops a new accos_test_<random> database.
    with TemporaryDatabaseFactory(url).create() as temporary_url:
        command.upgrade(migration_config(temporary_url), "head")
        yield temporary_url


@pytest.mark.integration
def test_t004_t009_cookie_pat_origin_csrf_revoke_and_audit(
    account_database: str, runtime_settings: RuntimeSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap = "acceptance-bootstrap-" + uuid4().hex
    settings = replace(
        runtime_settings,
        required=replace(runtime_settings.required, database_url=account_database),
        auth=AuthSettings(bootstrap_digest=digest(bootstrap)),
    )
    monkeypatch.setattr(
        DatabaseRuntime, "create", lambda url, options: DatabaseRuntime.create_unpooled(url)
    )
    runtime = build_container(settings, probes=())
    client = TestClient(
        create_app(settings, container=runtime, configure_logs=False),
        base_url="http://localhost:3000",
    )
    client.headers["Origin"] = "http://localhost:3000"
    try:
        assert client.get("/api/v1/auth/session").json()["bootstrap_required"]
        body = {
            "username": "author",
            "password": "acceptance-password-123",
            "bootstrap_token": bootstrap,
            "workspace_name": "验收工作区",
        }
        assert (
            client.post(
                "/api/v1/auth/bootstrap", json={**body, "bootstrap_token": "wrong" * 10}
            ).status_code
            == 401
        )
        response = client.post("/api/v1/auth/bootstrap", json=body)
        assert response.status_code == 201
        assert "HttpOnly" in response.headers["set-cookie"]
        session = response.json()
        workspace = session["workspaces"][0]["id"]
        client.headers.update({"X-Workspace-ID": workspace, "X-CSRF-Token": session["csrf_token"]})
        assert client.post("/api/v1/auth/bootstrap", json=body).status_code == 409
        assert client.get("/api/v1/identity/me").json()["auth_method"] == "local"
        assert (
            client.get("/api/v1/identity/me", headers={"Host": "evil.example"}).status_code == 401
        )
        patch = {"expected_version": 1, "values": {"name": "变更", "approval_mode": "human_owner"}}
        assert (
            client.put(
                "/api/v1/settings/workspace", json=patch, headers={"X-CSRF-Token": "forged"}
            ).status_code
            == 401
        )
        assert (
            client.put(
                "/api/v1/settings/workspace", json=patch, headers={"Origin": "https://evil.example"}
            ).status_code
            == 401
        )
        assert client.put("/api/v1/settings/workspace", json=patch).status_code == 428
        assert (
            client.put(
                "/api/v1/settings/workspace", json=patch, headers={"If-Match": '"2"'}
            ).status_code
            == 409
        )
        assert (
            client.put(
                "/api/v1/settings/workspace", json=patch, headers={"If-Match": '"1"'}
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/settings/workspace", json=patch, headers={"If-Match": '"1"'}
            ).status_code
            == 409
        )
        issued = client.post(
            "/api/v1/identity/tokens",
            json={"name": "reader", "scopes": ["workspace:read", "project:read"], "days": 1},
        ).json()
        token = issued["token"]
        assert token not in client.get("/api/v1/identity/tokens").text
        assert (
            client.get("/api/v1/identity/me", headers={"Authorization": "Bearer " + token}).json()[
                "actor_kind"
            ]
            == "service"
        )
        assert (
            client.post(
                "/api/v1/identity/tokens",
                json={"name": "forged", "scopes": ["approval:decide"], "days": 1},
            ).status_code
            == 400
        )
        assert (
            client.get(
                "/api/v1/auth/sessions", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 403
        )
        assert client.delete("/api/v1/identity/tokens/" + issued["record"]["id"]).status_code == 204
        assert (
            client.get(
                "/api/v1/identity/me", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 401
        )

        async def audit() -> None:
            async with runtime.database.sessions() as db:
                rows = (
                    await db.scalars(
                        select(AuditEventRow).where(AuditEventRow.workspace_id == UUID(workspace))
                    )
                ).all()
                assert any(r.payload.get("credential_id") == issued["record"]["id"] for r in rows)
                assert all(token not in str(r.payload) for r in rows)

        asyncio.run(audit())
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert not client.get("/api/v1/auth/session").json()["authenticated"]
        assert client.get("/api/v1/identity/me").status_code == 401
        login = client.post(
            "/api/v1/auth/login", json={"username": "author", "password": "acceptance-password-123"}
        )
        assert login.status_code == 200 and login.json()["session_id"] != session["session_id"]
        # A new container reads durable sessions rather than process memory.
        fresh = build_container(settings, probes=())

        async def restart() -> None:
            assert fresh.identity.accounts is not None
            info = await fresh.identity.accounts.session(
                client.cookies.get("accos_session"), client.cookies.get("accos_csrf")
            )
            assert info.authenticated
            await fresh.database.shutdown()

        asyncio.run(restart())
    finally:
        client.close()
        asyncio.run(runtime.database.shutdown())


@pytest.mark.integration
def test_t004_t005_t007_t008_t010_persistence_races_policies_and_secret_rotation(
    account_database: str, runtime_settings: RuntimeSettings
) -> None:
    runtime_db = DatabaseRuntime.create_unpooled(account_database)
    key = base64.b64encode(bytes(range(32))).decode()
    settings = replace(
        runtime_settings,
        required=replace(runtime_settings.required, database_url=account_database),
        auth=AuthSettings(secret_keys={"key1": key}, active_key_id="key1"),
    )
    runtime = build_container(settings, probes=())

    async def scenario() -> None:
        store = SqlAccountStore(runtime_db.sessions)
        now = datetime.now(UTC)
        results = await asyncio.gather(
            *(
                store.bootstrap(
                    "author-" + str(i), password_hash("acceptance-password-123"), "本地空间", now
                )
                for i in range(2)
            ),
            return_exceptions=True,
        )
        assert sum(isinstance(r, UUID) for r in results) == 1
        user_id = next(r for r in results if isinstance(r, UUID))
        accounts = runtime.identity.accounts
        assert accounts is not None
        issued = await accounts.issue_session(user_id, "local")
        workspace = issued.info.workspaces[0].id
        context = await runtime.identity.authenticator.authenticate(
            issued.token, workspace, CorrelationIds(str(uuid4()), str(uuid4()))
        )
        resolver = ApprovalPolicyResolver(accounts)
        frozen = await resolver.snapshot(workspace)
        await accounts.save_settings(context, 1, WorkspacePreferences(approval_mode="dual_control"))
        await resolver.require_decision(context, user_id, frozen)
        from accos.kernel.errors import PermissionDeniedError

        with pytest.raises(PermissionDeniedError):
            await resolver.require_decision(context, user_id, await resolver.snapshot(workspace))
        with pytest.raises(ConcurrencyConflictError):
            await accounts.save_settings(context, 1, WorkspacePreferences())
        await accounts.save_settings(context, 2, WorkspacePreferences(approval_mode="human_owner"))
        request = await runtime.identity.creator_control.request(
            context,
            ControlRequestDraft(
                ControlRequestKind.EXPORT, "workspace", str(workspace), "export", "local"
            ),
        )
        await runtime.identity.creator_control.decide(context, request.id, ApprovalDecision.APPROVE)
        secret = await accounts.put_credential(
            context, uuid4(), 0, "provider", "private-value", None, True
        )
        assert await accounts.resolve_secret(workspace, secret.secret_ref) == "private-value"
        rotated = await accounts.put_credential(
            context, secret.id, 1, "provider", "rotated-value", None, True
        )
        with pytest.raises(ConfigurationError):
            await accounts.resolve_secret(workspace, secret.secret_ref)
        assert await accounts.resolve_secret(workspace, rotated.secret_ref) == "rotated-value"
        assert "rotated-value" not in str(await store.secrets(workspace))
        flow = OidcFlow(
            digest("state"), digest("browser"), "verifier", "nonce", now + timedelta(minutes=5)
        )
        await store.add_oidc_flow(flow)
        assert await store.consume_oidc_flow(flow.state_hash, digest("wrong-browser"), now) is None
        consumed = await asyncio.gather(
            *(store.consume_oidc_flow(flow.state_hash, flow.browser_hash, now) for _ in range(2))
        )
        assert sum(v is not None for v in consumed) == 1
        await runtime_db.shutdown()
        await runtime.database.shutdown()

    asyncio.run(scenario())


@pytest.mark.integration
def test_t006_scopes_and_revocation_are_rechecked_with_persisted_memberships(
    account_database: str, runtime_settings: RuntimeSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        DatabaseRuntime, "create", lambda url, options: DatabaseRuntime.create_unpooled(url)
    )
    settings = replace(
        runtime_settings,
        required=replace(runtime_settings.required, database_url=account_database),
        auth=AuthSettings(),
    )
    runtime = build_container(settings, probes=())

    async def scenario() -> None:
        accounts = runtime.identity.accounts
        assert accounts is not None
        store = SqlAccountStore(runtime.database.sessions)
        owner = await store.bootstrap(
            "owner", password_hash("acceptance-owner-password"), "空间甲", datetime.now(UTC)
        )
        owner_session = await accounts.issue_session(owner, "local")
        workspace = owner_session.info.workspaces[0].id

        async def context(token: str) -> SecurityContext:
            return await runtime.identity.authenticator.authenticate(
                token, workspace, CorrelationIds(str(uuid4()), str(uuid4()))
            )

        owner_context = await context(owner_session.token)
        member = await accounts.put_member(
            owner_context,
            "urn:accos:local",
            "editor",
            Role.EDITOR,
            True,
            0,
            "acceptance-editor-password",
        )
        editor_session = await accounts.issue_session(member.user_id, "local")
        editor_context = await context(editor_session.token)
        project, other_workspace = uuid4(), uuid4()
        async with runtime.database.sessions.begin() as db:
            db.add(WorkspaceRow(id=other_workspace, owner_user_id=owner))
            await db.flush()
            db.add(
                MembershipRow(id=uuid4(), workspace_id=other_workspace, user_id=owner, role="OWNER")
            )
        with pytest.raises(PermissionDeniedError):
            await runtime.identity.authenticator.authenticate(
                editor_session.token, other_workspace, CorrelationIds(str(uuid4()), str(uuid4()))
            )
        grant = await accounts.put_grant(
            owner_context,
            ScopeGrant(
                id=uuid4(),
                workspace_id=workspace,
                user_id=member.user_id,
                scope_kind="project",
                scope_id=project,
                permissions=("project:read",),
            ),
            0,
        )
        resource = ResourceScope(workspace, "project", str(project), project)
        read = AuthorizationRequest(editor_context, Permission.PROJECT_READ, resource)
        await runtime.identity.authorizer.authorize(read)
        token, view = await accounts.create_token(
            editor_context, "scoped", ("project:read",), 1, project
        )
        held_token_context = await context(token)
        token_read = AuthorizationRequest(held_token_context, Permission.PROJECT_READ, resource)
        await runtime.identity.authorizer.authorize(token_read)
        with pytest.raises(ScopeViolationError):
            await runtime.identity.authorizer.authorize(
                AuthorizationRequest(
                    held_token_context,
                    Permission.PROJECT_READ,
                    ResourceScope(other_workspace, "project", str(project), project),
                )
            )
        await store.revoke_token(workspace, member.user_id, view.id)
        with pytest.raises(PermissionDeniedError):
            await runtime.identity.authorizer.authorize(token_read)
        revoked = await accounts.put_grant(
            owner_context, grant.model_copy(update={"active": False}), grant.version
        )
        with pytest.raises(PermissionDeniedError):
            await runtime.identity.authorizer.authorize(read)
        assert project in await runtime.identity.authorizer.hidden_projects(editor_context)
        await accounts.put_grant(
            owner_context, revoked.model_copy(update={"active": True}), revoked.version
        )
        await runtime.identity.authorizer.authorize(read)
        await accounts.put_member(
            owner_context, member.issuer, member.subject, member.role, False, member.version, None
        )
        with pytest.raises(PermissionDeniedError):
            await runtime.identity.authorizer.authorize(read)

    try:
        asyncio.run(scenario())
    finally:
        asyncio.run(runtime.database.shutdown())
