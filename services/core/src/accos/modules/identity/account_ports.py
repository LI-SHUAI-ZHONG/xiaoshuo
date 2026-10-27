"""Transactional identity persistence and cryptographic boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from accos.modules.identity.accounts import (
    CreatorAnchor,
    CredentialView,
    MemberView,
    ScopeGrant,
    SessionView,
    TokenView,
    WorkspaceChoice,
    WorkspacePreferences,
    WorkspaceSettings,
)
from accos.modules.identity.domain import Role


@dataclass(frozen=True, slots=True)
class VerifiedCredential:
    user_id: UUID
    issuer: str
    subject: str
    method: str
    credential_id: UUID
    expires_at: datetime
    workspace_id: UUID | None = None
    scopes: tuple[str, ...] | None = None
    project_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class StoredSecret:
    view: CredentialView
    ciphertext: str | None
    external_ref: str | None


@dataclass(frozen=True, slots=True)
class OidcFlow:
    state_hash: str
    browser_hash: str
    verifier: str
    nonce: str
    expires_at: datetime


class SecretCipher(Protocol):
    active: str

    @property
    def configured(self) -> bool: ...
    def encrypt(self, value: str, binding: str) -> str: ...
    def decrypt(self, value: str, key_id: str, binding: str) -> str: ...


class AccountStore(Protocol):
    async def bootstrapped(self) -> bool: ...
    async def bootstrap(
        self,
        username: str,
        password: str,
        name: str,
        now: datetime,
        adopt_workspace_id: UUID | None = None,
    ) -> UUID: ...
    async def password(self, username: str) -> tuple[UUID, str] | None: ...
    async def check_login_limit(self, key: str, now: datetime) -> bool: ...
    async def add_session(
        self,
        user_id: UUID,
        token_hash: str,
        csrf_hash: str,
        method: str,
        now: datetime,
        expires: datetime,
    ) -> UUID: ...
    async def verify(
        self, digest: str, method: str, now: datetime
    ) -> VerifiedCredential | None: ...
    async def token_active(
        self, token_id: UUID, workspace_id: UUID, user_id: UUID, now: datetime
    ) -> bool: ...
    async def csrf_matches(self, session_id: UUID, digest: str) -> bool: ...
    async def session_active(self, session_id: UUID, user_id: UUID, now: datetime) -> bool: ...
    async def list_sessions(self, user_id: UUID) -> tuple[SessionView, ...]: ...
    async def revoke_session(self, user_id: UUID, session_id: UUID) -> None: ...
    async def replace_password(self, user_id: UUID, password: str) -> None: ...
    async def workspaces(self, user_id: UUID) -> tuple[WorkspaceChoice, ...]: ...
    async def settings(
        self, workspace_id: UUID, version: int | None = None
    ) -> WorkspaceSettings: ...
    async def save_settings(
        self, workspace_id: UUID, expected: int, values: WorkspacePreferences
    ) -> WorkspaceSettings: ...
    async def member(self, workspace_id: UUID, user_id: UUID) -> MemberView | None: ...
    async def members(self, workspace_id: UUID) -> tuple[MemberView, ...]: ...
    async def put_member(
        self,
        workspace_id: UUID,
        issuer: str,
        subject: str,
        role: Role,
        active: bool,
        expected: int,
        password: str | None = None,
    ) -> MemberView: ...
    async def grants(self, workspace_id: UUID) -> tuple[ScopeGrant, ...]: ...
    async def put_grant(self, grant: ScopeGrant, expected: int) -> ScopeGrant: ...
    async def anchor(self, workspace_id: UUID, user_id: UUID) -> CreatorAnchor: ...
    async def add_token(
        self, workspace_id: UUID, user_id: UUID, token_hash: str, view: TokenView
    ) -> None: ...
    async def tokens(self, workspace_id: UUID, user_id: UUID) -> tuple[TokenView, ...]: ...
    async def revoke_token(self, workspace_id: UUID, user_id: UUID, token_id: UUID) -> None: ...
    async def secrets(self, workspace_id: UUID) -> tuple[CredentialView, ...]: ...
    async def secret(self, workspace_id: UUID, credential_id: UUID) -> StoredSecret | None: ...
    async def put_secret(
        self, workspace_id: UUID, secret: StoredSecret, expected: int
    ) -> CredentialView: ...
    async def add_oidc_flow(self, flow: OidcFlow) -> None: ...
    async def consume_oidc_flow(
        self, state_hash: str, browser_hash: str, now: datetime
    ) -> OidcFlow | None: ...
    async def oidc_user(self, issuer: str, subject: str) -> UUID | None: ...


class OidcClient(Protocol):
    def authorization_url(self, state: str, nonce: str, verifier: str) -> str: ...
    async def exchange(
        self, code: str, verifier: str, nonce: str, now: datetime
    ) -> tuple[str, str]: ...
