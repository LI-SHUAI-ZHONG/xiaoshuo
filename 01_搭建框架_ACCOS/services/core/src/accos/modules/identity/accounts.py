"""Identity administration values and storage ports. Secrets never appear in read models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from accos.modules.identity.domain import Role


class IdentityValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkspacePreferences(IdentityValue):
    name: Annotated[str, Field(min_length=1, max_length=100)] = "我的创作空间"
    approval_mode: Literal["human_owner", "dual_control"] = "dual_control"
    locale: Literal["zh-CN", "en"] = "zh-CN"
    timezone: Annotated[str, Field(min_length=1, max_length=100)] = "Asia/Shanghai"
    default_creation_mode: Literal["assisted", "collaborative", "delegated"] = "assisted"
    daily_token_budget: Annotated[int, Field(ge=0, le=100_000_000)] = 100_000
    cloud_content_allowed: bool = False


class WorkspaceSettings(IdentityValue):
    workspace_id: UUID
    version: int
    values: WorkspacePreferences


class MemberView(IdentityValue):
    id: UUID
    user_id: UUID
    role: Role
    active: bool
    version: int
    issuer: str
    subject: str


class WorkspaceChoice(IdentityValue):
    id: UUID
    name: str
    role: Role


class SessionView(IdentityValue):
    id: UUID
    user_id: UUID
    method: Literal["local", "oidc"]
    created_at: datetime
    expires_at: datetime
    revoked: bool


class SessionInfo(IdentityValue):
    authenticated: bool
    bootstrap_required: bool = False
    oidc_configured: bool = False
    user_id: UUID | None = None
    session_id: UUID | None = None
    expires_at: datetime | None = None
    csrf_token: str | None = None
    workspaces: tuple[WorkspaceChoice, ...] = ()


class TokenView(IdentityValue):
    id: UUID
    name: str
    scopes: tuple[str, ...]
    project_id: UUID | None
    created_at: datetime
    expires_at: datetime
    revoked: bool


class CredentialView(IdentityValue):
    id: UUID
    name: str
    version: int
    secret_ref: str
    storage: Literal["encrypted", "external"]
    active: bool
    key_id: str | None
    updated_at: datetime


class ScopeGrant(IdentityValue):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    scope_kind: Literal["project", "creator", "universe"]
    scope_id: UUID
    permissions: tuple[str, ...]
    active: bool = True
    version: int = 1


class CreatorAnchor(IdentityValue):
    memory_anchor_id: UUID
    id: UUID
    workspace_id: UUID
    user_id: UUID


class ApprovalPolicy(IdentityValue):
    reference: str
    mode: Literal["human_owner", "dual_control"]
    version: int


class ApprovalPolicyPort(Protocol):
    async def snapshot(self, workspace_id: UUID) -> str: ...

    async def require_decision(
        self, context: object, requested_by: UUID, policy_ref: str
    ) -> None: ...
