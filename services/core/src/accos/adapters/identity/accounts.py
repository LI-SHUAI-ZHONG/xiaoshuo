"""Durable local accounts, sessions, settings histories, grants and encrypted credentials."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    delete,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.identity.persistence import MembershipRow, UserRow, WorkspaceRow
from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, PermissionDeniedError
from accos.modules.identity.account_ports import OidcFlow, StoredSecret, VerifiedCredential
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

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory


class BootstrapRow(Base):
    __tablename__ = "identity_bootstrap"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LocalAccountRow(Base):
    __tablename__ = "identity_local_accounts"
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("identity_users.id"), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)


class LoginSessionRow(Base):
    __tablename__ = "identity_login_sessions"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LoginAttemptRow(Base):
    __tablename__ = "identity_login_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceSettingsRow(Base):
    __tablename__ = "identity_settings_history"
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_workspaces.id"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)


class PersonalTokenRow(Base):
    __tablename__ = "identity_personal_tokens"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("identity_users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CredentialRow(Base):
    __tablename__ = "identity_credentials"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_workspaces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[str | None] = mapped_column(String(24000))
    external_ref: Mapped[str | None] = mapped_column(String(200))
    key_id: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_identity_credential_name"),
        {"schema": SCHEMA_NAME},
    )


class ScopeGrantRow(Base):
    __tablename__ = "identity_scope_grants"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("identity_users.id"), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", "scope_kind", "scope_id", name="uq_identity_scope_grant"
        ),
        {"schema": SCHEMA_NAME},
    )


class CreatorAnchorRow(Base):
    __tablename__ = "identity_creator_anchors"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identity_workspaces.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("identity_users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_identity_creator_anchor"),
        {"schema": SCHEMA_NAME},
    )


class OidcFlowRow(Base):
    __tablename__ = "identity_oidc_flows"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier: Mapped[str] = mapped_column(String(200), nullable=False)
    nonce: Mapped[str] = mapped_column(String(200), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SqlAccountStore:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def bootstrapped(self) -> bool:
        async with self._sessions() as session:
            row = await session.get(BootstrapRow, 1)
            return row is not None and row.consumed

    async def bootstrap(
        self,
        username: str,
        password: str,
        name: str,
        now: datetime,
        adopt_workspace_id: UUID | None = None,
    ) -> UUID:
        del now
        async with self._sessions.begin() as session:
            await session.execute(
                insert(BootstrapRow).values(id=1, consumed=False).on_conflict_do_nothing()
            )
            guard = await session.scalar(
                select(BootstrapRow).where(BootstrapRow.id == 1).with_for_update()
            )
            if guard is None or guard.consumed:
                raise InvalidStateError("Local owner has already been initialized.")
            candidates = (
                await session.scalars(
                    select(WorkspaceRow)
                    .join(UserRow, WorkspaceRow.owner_user_id == UserRow.id)
                    .where(
                        UserRow.issuer == "urn:accos:development", WorkspaceRow.archived.is_(False)
                    )
                    .with_for_update(of=WorkspaceRow)
                )
            ).all()
            if adopt_workspace_id is not None:
                candidates = [w for w in candidates if w.id == adopt_workspace_id]
                if not candidates:
                    raise InvalidStateError(
                        "The selected legacy development workspace cannot be adopted."
                    )
            if len(candidates) > 1:
                raise InvalidStateError(
                    "Select the legacy workspace through the local installer before setup."
                )
            if candidates:
                workspace = candidates[0]
                owner = await session.get(UserRow, workspace.owner_user_id)
                if owner is None:
                    raise InvalidStateError("Legacy creator identity is unavailable.")
                owner.issuer, owner.subject = "urn:accos:local", username
                session.add(
                    LocalAccountRow(user_id=owner.id, username=username, password_hash=password)
                )
                # Preserve actor/workspace IDs, all projects and legacy memory references.
                current_version = await session.scalar(
                    select(WorkspaceSettingsRow.version)
                    .where(WorkspaceSettingsRow.workspace_id == workspace.id)
                    .order_by(WorkspaceSettingsRow.version.desc())
                    .limit(1)
                )
                session.add(
                    WorkspaceSettingsRow(
                        workspace_id=workspace.id,
                        version=(current_version or 0) + 1,
                        payload=WorkspacePreferences(
                            name=name, approval_mode="human_owner"
                        ).model_dump(),
                    )
                )
                await session.execute(
                    insert(CreatorAnchorRow)
                    .values(id=uuid4(), workspace_id=workspace.id, user_id=owner.id)
                    .on_conflict_do_nothing()
                )
                guard.consumed = True
                return owner.id
            user_id, workspace_id = uuid4(), uuid4()
            session.add(UserRow(id=user_id, issuer="urn:accos:local", subject=username))
            await session.flush()
            session.add(WorkspaceRow(id=workspace_id, owner_user_id=user_id))
            await session.flush()
            session.add_all(
                [
                    LocalAccountRow(user_id=user_id, username=username, password_hash=password),
                    MembershipRow(
                        id=uuid4(), workspace_id=workspace_id, user_id=user_id, role="OWNER"
                    ),
                    CreatorAnchorRow(id=uuid4(), workspace_id=workspace_id, user_id=user_id),
                    WorkspaceSettingsRow(
                        workspace_id=workspace_id,
                        version=1,
                        payload=WorkspacePreferences(
                            name=name, approval_mode="human_owner"
                        ).model_dump(),
                    ),
                ]
            )
            guard.consumed = True
        return user_id

    async def password(self, username: str) -> tuple[UUID, str] | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(LocalAccountRow)
                .join(UserRow, UserRow.id == LocalAccountRow.user_id)
                .where(LocalAccountRow.username == username, UserRow.active.is_(True))
            )
            return None if row is None else (row.user_id, row.password_hash)

    async def check_login_limit(self, key: str, now: datetime) -> bool:
        async with self._sessions.begin() as session:
            await session.execute(
                insert(LoginAttemptRow)
                .values(key=key, attempts=0, window_end=now + timedelta(minutes=15))
                .on_conflict_do_nothing()
            )
            row = await session.scalar(
                select(LoginAttemptRow).where(LoginAttemptRow.key == key).with_for_update()
            )
            if row is None:
                return False
            if row.window_end <= now:
                row.attempts, row.window_end = 0, now + timedelta(minutes=15)
            row.attempts += 1
            return row.attempts <= 20

    async def add_session(
        self,
        user_id: UUID,
        token_hash: str,
        csrf_hash: str,
        method: str,
        now: datetime,
        expires: datetime,
    ) -> UUID:
        session_id = uuid4()
        async with self._sessions.begin() as session:
            session.add(
                LoginSessionRow(
                    id=session_id,
                    user_id=user_id,
                    token_hash=token_hash,
                    csrf_hash=csrf_hash,
                    method=method,
                    created_at=now,
                    expires_at=expires,
                    revoked=False,
                )
            )
        return session_id

    async def verify(self, digest: str, method: str, now: datetime) -> VerifiedCredential | None:
        async with self._sessions() as session:
            if method == "pat":
                token = await session.scalar(
                    select(PersonalTokenRow).where(
                        PersonalTokenRow.token_hash == digest,
                        PersonalTokenRow.revoked.is_(False),
                        PersonalTokenRow.expires_at > now,
                    )
                )
                if token is None:
                    return None
                user = await session.get(UserRow, token.user_id)
                if user is None or not user.active:
                    return None
                return VerifiedCredential(
                    user.id,
                    user.issuer,
                    user.subject,
                    "pat",
                    token.id,
                    token.expires_at,
                    token.workspace_id,
                    tuple(token.scopes),
                    token.project_id,
                )
            row = await session.scalar(
                select(LoginSessionRow).where(
                    LoginSessionRow.token_hash == digest,
                    LoginSessionRow.revoked.is_(False),
                    LoginSessionRow.expires_at > now,
                )
            )
            if row is None:
                return None
            user = await session.get(UserRow, row.user_id)
            if user is None or not user.active:
                return None
            return VerifiedCredential(
                user.id, user.issuer, user.subject, row.method, row.id, row.expires_at
            )

    async def token_active(
        self, token_id: UUID, workspace_id: UUID, user_id: UUID, now: datetime
    ) -> bool:
        async with self._sessions() as session:
            return (
                await session.scalar(
                    select(PersonalTokenRow.id).where(
                        PersonalTokenRow.id == token_id,
                        PersonalTokenRow.workspace_id == workspace_id,
                        PersonalTokenRow.user_id == user_id,
                        PersonalTokenRow.revoked.is_(False),
                        PersonalTokenRow.expires_at > now,
                    )
                )
                is not None
            )

    async def csrf_matches(self, session_id: UUID, digest: str) -> bool:
        async with self._sessions() as session:
            return (
                await session.scalar(
                    select(LoginSessionRow.id).where(
                        LoginSessionRow.id == session_id,
                        LoginSessionRow.csrf_hash == digest,
                        LoginSessionRow.revoked.is_(False),
                    )
                )
                is not None
            )

    async def session_active(self, session_id: UUID, user_id: UUID, now: datetime) -> bool:
        async with self._sessions() as session:
            return (
                await session.scalar(
                    select(LoginSessionRow.id)
                    .join(UserRow, UserRow.id == LoginSessionRow.user_id)
                    .where(
                        LoginSessionRow.id == session_id,
                        LoginSessionRow.user_id == user_id,
                        LoginSessionRow.revoked.is_(False),
                        LoginSessionRow.expires_at > now,
                        UserRow.active.is_(True),
                    )
                )
                is not None
            )

    async def list_sessions(self, user_id: UUID) -> tuple[SessionView, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(LoginSessionRow)
                    .where(LoginSessionRow.user_id == user_id)
                    .order_by(LoginSessionRow.created_at.desc())
                    .limit(100)
                )
            ).all()
            return tuple(
                SessionView(
                    id=r.id,
                    user_id=r.user_id,
                    method=cast("Literal['local', 'oidc']", r.method),
                    created_at=r.created_at,
                    expires_at=r.expires_at,
                    revoked=r.revoked,
                )
                for r in rows
            )

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(LoginSessionRow)
                .where(LoginSessionRow.id == session_id, LoginSessionRow.user_id == user_id)
                .values(revoked=True)
            )

    async def replace_password(self, user_id: UUID, password: str) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(LocalAccountRow, user_id)
            if row is None:
                raise InvalidStateError("This identity has no local password.")
            row.password_hash = password
            await session.execute(
                update(LoginSessionRow)
                .where(LoginSessionRow.user_id == user_id)
                .values(revoked=True)
            )

    async def workspaces(self, user_id: UUID) -> tuple[WorkspaceChoice, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(MembershipRow)
                    .join(WorkspaceRow, WorkspaceRow.id == MembershipRow.workspace_id)
                    .where(
                        MembershipRow.user_id == user_id,
                        MembershipRow.active.is_(True),
                        WorkspaceRow.archived.is_(False),
                    )
                    .order_by(MembershipRow.id)
                    .limit(100)
                )
            ).all()
        return tuple(
            [
                WorkspaceChoice(
                    id=r.workspace_id,
                    name=(await self.settings(r.workspace_id)).values.name,
                    role=Role(r.role),
                )
                for r in rows
            ]
        )

    async def settings(self, workspace_id: UUID, version: int | None = None) -> WorkspaceSettings:
        async with self._sessions() as session:
            query = select(WorkspaceSettingsRow).where(
                WorkspaceSettingsRow.workspace_id == workspace_id
            )
            if version is not None:
                query = query.where(WorkspaceSettingsRow.version == version)
            row = await session.scalar(query.order_by(WorkspaceSettingsRow.version.desc()).limit(1))
            if row is None:
                if version is not None and version != 0:
                    raise InvalidStateError("Frozen approval policy is unavailable.")
                return WorkspaceSettings(
                    workspace_id=workspace_id, version=0, values=WorkspacePreferences()
                )
            return WorkspaceSettings(
                workspace_id=workspace_id,
                version=row.version,
                values=WorkspacePreferences.model_validate(row.payload),
            )

    async def save_settings(
        self, workspace_id: UUID, expected: int, values: WorkspacePreferences
    ) -> WorkspaceSettings:
        async with self._sessions.begin() as session:
            workspace = await session.scalar(
                select(WorkspaceRow).where(WorkspaceRow.id == workspace_id).with_for_update()
            )
            if workspace is None:
                raise PermissionDeniedError
            current = await session.scalar(
                select(WorkspaceSettingsRow.version)
                .where(WorkspaceSettingsRow.workspace_id == workspace_id)
                .order_by(WorkspaceSettingsRow.version.desc())
                .limit(1)
            )
            if (current or 0) != expected:
                raise ConcurrencyConflictError
            session.add(
                WorkspaceSettingsRow(
                    workspace_id=workspace_id, version=expected + 1, payload=values.model_dump()
                )
            )
        return WorkspaceSettings(workspace_id=workspace_id, version=expected + 1, values=values)

    async def member(self, workspace_id: UUID, user_id: UUID) -> MemberView | None:
        return next((m for m in await self.members(workspace_id) if m.user_id == user_id), None)

    async def members(self, workspace_id: UUID) -> tuple[MemberView, ...]:
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(MembershipRow, UserRow)
                    .join(UserRow, UserRow.id == MembershipRow.user_id)
                    .where(MembershipRow.workspace_id == workspace_id)
                    .order_by(MembershipRow.id)
                )
            ).all()
            return tuple(
                MemberView(
                    id=m.id,
                    user_id=m.user_id,
                    role=Role(m.role),
                    active=m.active and u.active,
                    version=m.version,
                    issuer=u.issuer,
                    subject=u.subject,
                )
                for m, u in rows
            )

    async def put_member(
        self,
        workspace_id: UUID,
        issuer: str,
        subject: str,
        role: Role,
        active: bool,
        expected: int,
        password: str | None = None,
    ) -> MemberView:
        async with self._sessions.begin() as session:
            workspace = await session.scalar(
                select(WorkspaceRow).where(WorkspaceRow.id == workspace_id).with_for_update()
            )
            if workspace is None:
                raise PermissionDeniedError
            user = await session.scalar(
                select(UserRow).where(UserRow.issuer == issuer, UserRow.subject == subject)
            )
            if user is None:
                user = UserRow(id=uuid4(), issuer=issuer, subject=subject, active=True)
                session.add(user)
                await session.flush()
                if issuer == "urn:accos:local":
                    if password is None:
                        raise InvalidStateError("New local members require an initial password.")
                    session.add(
                        LocalAccountRow(user_id=user.id, username=subject, password_hash=password)
                    )
            elif password is not None:
                raise InvalidStateError("Existing accounts change their own password.")
            row = await session.scalar(
                select(MembershipRow).where(
                    MembershipRow.workspace_id == workspace_id, MembershipRow.user_id == user.id
                )
            )
            if (0 if row is None else row.version) != expected:
                raise ConcurrencyConflictError
            if workspace.owner_user_id == user.id and (not active or role != Role.OWNER):
                raise InvalidStateError("The workspace creator cannot be removed or demoted here.")
            if row is None:
                row = MembershipRow(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    user_id=user.id,
                    role=role.value,
                    active=active,
                )
                session.add(row)
                await session.execute(
                    insert(CreatorAnchorRow)
                    .values(id=uuid4(), workspace_id=workspace_id, user_id=user.id)
                    .on_conflict_do_nothing()
                )
            else:
                row.role, row.active = role.value, active
            await session.flush()
            return MemberView(
                id=row.id,
                user_id=user.id,
                role=role,
                active=active,
                version=row.version,
                issuer=issuer,
                subject=subject,
            )

    async def grants(self, workspace_id: UUID) -> tuple[ScopeGrant, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ScopeGrantRow).where(ScopeGrantRow.workspace_id == workspace_id)
                )
            ).all()
            return tuple(
                ScopeGrant.model_validate({key: getattr(r, key) for key in ScopeGrant.model_fields})
                for r in rows
            )

    async def put_grant(self, grant: ScopeGrant, expected: int) -> ScopeGrant:
        async with self._sessions.begin() as session:
            await session.scalar(
                select(WorkspaceRow).where(WorkspaceRow.id == grant.workspace_id).with_for_update()
            )
            row = await session.scalar(
                select(ScopeGrantRow).where(
                    ScopeGrantRow.workspace_id == grant.workspace_id, ScopeGrantRow.id == grant.id
                )
            )
            if (0 if row is None else row.version) != expected:
                raise ConcurrencyConflictError
            values = grant.model_dump()
            values["permissions"] = list(grant.permissions)
            values["version"] = expected + 1
            if row is None:
                session.add(ScopeGrantRow(**values))
            else:
                if (row.user_id, row.scope_kind, row.scope_id) != (
                    grant.user_id,
                    grant.scope_kind,
                    grant.scope_id,
                ):
                    raise InvalidStateError("A grant's subject and scope are immutable.")
                row.permissions, row.active, row.version = (
                    list(grant.permissions),
                    grant.active,
                    expected + 1,
                )
        return grant.model_copy(update={"version": expected + 1})

    async def anchor(self, workspace_id: UUID, user_id: UUID) -> CreatorAnchor:
        async with self._sessions.begin() as session:
            await session.execute(
                insert(CreatorAnchorRow)
                .values(id=uuid4(), workspace_id=workspace_id, user_id=user_id)
                .on_conflict_do_nothing()
            )
            row = await session.scalar(
                select(CreatorAnchorRow).where(
                    CreatorAnchorRow.workspace_id == workspace_id,
                    CreatorAnchorRow.user_id == user_id,
                )
            )
            if row is None:
                raise InvalidStateError("Creator anchor is unavailable.")
            return CreatorAnchor(
                id=row.id, workspace_id=workspace_id, user_id=user_id, memory_anchor_id=user_id
            )

    async def add_token(
        self, workspace_id: UUID, user_id: UUID, token_hash: str, view: TokenView
    ) -> None:
        async with self._sessions.begin() as session:
            session.add(
                PersonalTokenRow(
                    **view.model_dump(exclude={"scopes"}),
                    scopes=list(view.scopes),
                    workspace_id=workspace_id,
                    user_id=user_id,
                    token_hash=token_hash,
                )
            )

    async def tokens(self, workspace_id: UUID, user_id: UUID) -> tuple[TokenView, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(PersonalTokenRow)
                    .where(
                        PersonalTokenRow.workspace_id == workspace_id,
                        PersonalTokenRow.user_id == user_id,
                    )
                    .order_by(PersonalTokenRow.created_at.desc())
                    .limit(100)
                )
            ).all()
            return tuple(
                TokenView.model_validate({k: getattr(r, k) for k in TokenView.model_fields})
                for r in rows
            )

    async def revoke_token(self, workspace_id: UUID, user_id: UUID, token_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(PersonalTokenRow)
                .where(
                    PersonalTokenRow.workspace_id == workspace_id,
                    PersonalTokenRow.user_id == user_id,
                    PersonalTokenRow.id == token_id,
                )
                .values(revoked=True)
            )

    async def secrets(self, workspace_id: UUID) -> tuple[CredentialView, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(CredentialRow)
                    .where(CredentialRow.workspace_id == workspace_id)
                    .order_by(CredentialRow.name)
                )
            ).all()
            return tuple(_secret_view(row) for row in rows)

    async def secret(self, workspace_id: UUID, credential_id: UUID) -> StoredSecret | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(CredentialRow).where(
                    CredentialRow.workspace_id == workspace_id, CredentialRow.id == credential_id
                )
            )
            return (
                None
                if row is None
                else StoredSecret(_secret_view(row), row.ciphertext, row.external_ref)
            )

    async def put_secret(
        self, workspace_id: UUID, secret: StoredSecret, expected: int
    ) -> CredentialView:
        async with self._sessions.begin() as session:
            await session.scalar(
                select(WorkspaceRow).where(WorkspaceRow.id == workspace_id).with_for_update()
            )
            row = await session.scalar(
                select(CredentialRow).where(
                    CredentialRow.workspace_id == workspace_id, CredentialRow.id == secret.view.id
                )
            )
            if (0 if row is None else row.version) != expected:
                raise ConcurrencyConflictError
            values = secret.view.model_dump(exclude={"secret_ref", "storage"})
            values.update(
                ciphertext=secret.ciphertext,
                external_ref=secret.external_ref,
                workspace_id=workspace_id,
            )
            if row is None:
                session.add(CredentialRow(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
        return secret.view

    async def add_oidc_flow(self, flow: OidcFlow) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(OidcFlowRow).where(
                    OidcFlowRow.expires_at < flow.expires_at - timedelta(minutes=10)
                )
            )
            session.add(
                OidcFlowRow(
                    state_hash=flow.state_hash,
                    browser_hash=flow.browser_hash,
                    verifier=flow.verifier,
                    nonce=flow.nonce,
                    expires_at=flow.expires_at,
                )
            )

    async def consume_oidc_flow(
        self, state_hash: str, browser_hash: str, now: datetime
    ) -> OidcFlow | None:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(OidcFlowRow)
                .where(
                    OidcFlowRow.state_hash == state_hash,
                    OidcFlowRow.browser_hash == browser_hash,
                    OidcFlowRow.expires_at > now,
                )
                .with_for_update()
            )
            if row is None:
                return None
            flow = OidcFlow(
                row.state_hash, row.browser_hash, row.verifier, row.nonce, row.expires_at
            )
            await session.delete(row)
            return flow

    async def oidc_user(self, issuer: str, subject: str) -> UUID | None:
        async with self._sessions() as session:
            return cast(
                "UUID | None",
                await session.scalar(
                    select(UserRow.id).where(
                        UserRow.issuer == issuer,
                        UserRow.subject == subject,
                        UserRow.active.is_(True),
                    )
                ),
            )


def _secret_view(row: CredentialRow) -> CredentialView:
    return CredentialView(
        id=row.id,
        name=row.name,
        version=row.version,
        secret_ref=f"credential://{row.workspace_id}/{row.id}/{row.version}",
        storage="external" if row.external_ref else "encrypted",
        active=row.active,
        key_id=row.key_id,
        updated_at=row.updated_at,
    )
