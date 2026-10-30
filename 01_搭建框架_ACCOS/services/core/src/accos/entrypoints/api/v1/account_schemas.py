"""Write-only identity inputs and safe read responses used by OpenAPI and Studio."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, SecretStr

from accos.modules.identity.accounts import (
    CredentialView,
    IdentityValue,
    ScopeGrant,
    TokenView,
    WorkspacePreferences,
)
from accos.modules.identity.domain import Role

Name = Annotated[str, Field(min_length=1, max_length=100)]


class LoginInput(IdentityValue):
    username: Name
    password: Annotated[SecretStr, Field(min_length=1, max_length=256)]


class BootstrapInput(LoginInput):
    bootstrap_token: Annotated[SecretStr, Field(min_length=32, max_length=200)]
    workspace_name: Name = "我的创作空间"


class PasswordInput(LoginInput):
    new_password: Annotated[SecretStr, Field(min_length=12, max_length=256)]


class SettingsInput(IdentityValue):
    expected_version: Annotated[int, Field(ge=0)]
    values: WorkspacePreferences


class MemberInput(IdentityValue):
    issuer: Annotated[str, Field(min_length=1, max_length=500)] = "urn:accos:local"
    subject: Annotated[str, Field(min_length=1, max_length=500)]
    role: Role
    active: bool = True
    expected_version: Annotated[int, Field(ge=0)] = 0
    password: Annotated[SecretStr | None, Field(min_length=12, max_length=256)] = None


class GrantInput(IdentityValue):
    grant: ScopeGrant
    expected_version: Annotated[int, Field(ge=0)]


class TokenInput(IdentityValue):
    name: Name
    scopes: Annotated[tuple[str, ...], Field(min_length=1, max_length=8)]
    days: Annotated[int, Field(ge=1, le=90)] = 30
    project_id: UUID | None = None


class IssuedTokenResponse(IdentityValue):
    token: str
    record: TokenView


class CredentialInput(IdentityValue):
    id: UUID
    name: Name
    expected_version: Annotated[int, Field(ge=0)]
    value: Annotated[SecretStr | None, Field(min_length=1, max_length=8192)] = None
    external_ref: Annotated[str | None, Field(max_length=200)] = None
    active: bool = True


class SettingsExport(IdentityValue):
    schema_version: Literal[1] = 1
    values: WorkspacePreferences
    credentials: tuple[CredentialView, ...]
    redacted: Literal[True] = True


class ControlRequestView(IdentityValue):
    id: UUID
    requested_by: UUID
    kind: str
    resource_type: str
    resource_id: str
    status: str
    approval_policy_ref: str


class ControlDecisionInput(IdentityValue):
    decision: Literal["approve", "reject"]
