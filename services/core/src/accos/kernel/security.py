"""Stable actor and scope context propagated across request and task boundaries."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.kernel.errors import AuthenticationRequiredError
from accos.kernel.ids import CorrelationIds, parse_id

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID


class ActorKind(StrEnum):
    """Kinds of principals accepted by the common authorization boundary."""

    USER = "user"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Immutable permission snapshot for exactly one actor and workspace."""

    actor_id: UUID
    actor_kind: ActorKind
    workspace_id: UUID
    permissions: frozenset[str]
    policy_version: str
    correlation: CorrelationIds
    project_id: UUID | None = None
    auth_method: str = "legacy"
    session_id: UUID | None = None
    credential_id: UUID | None = None

    def as_task_headers(self) -> dict[str, str]:
        """Serialize the context for a trusted task envelope, never for client input."""
        headers = {
            "actor_id": str(self.actor_id),
            "actor_kind": self.actor_kind.value,
            "workspace_id": str(self.workspace_id),
            "permissions": ",".join(sorted(self.permissions)),
            "policy_version": self.policy_version,
            "request_id": self.correlation.request_id,
            "trace_id": self.correlation.trace_id,
        }
        if self.auth_method == "pat" and self.credential_id is not None:
            headers["auth_method"] = "pat"
            headers["credential_id"] = str(self.credential_id)
        if self.project_id is not None:
            headers["project_id"] = str(self.project_id)
        if self.correlation.task_id is not None:
            headers["task_id"] = self.correlation.task_id
        return headers

    @classmethod
    def from_task_headers(cls, headers: Mapping[str, str]) -> SecurityContext:
        """Restore a server-signed task envelope after transport verification."""
        return cls(
            actor_id=parse_id(headers["actor_id"]),
            actor_kind=ActorKind(headers["actor_kind"]),
            auth_method="pat" if headers.get("auth_method") == "pat" else "task",
            credential_id=parse_id(headers["credential_id"])
            if "credential_id" in headers
            else None,
            workspace_id=parse_id(headers["workspace_id"]),
            project_id=(parse_id(headers["project_id"]) if "project_id" in headers else None),
            permissions=frozenset(filter(None, headers.get("permissions", "").split(","))),
            policy_version=headers["policy_version"],
            correlation=CorrelationIds(
                request_id=str(parse_id(headers["request_id"])),
                trace_id=str(parse_id(headers["trace_id"])),
                task_id=(str(parse_id(headers["task_id"])) if "task_id" in headers else None),
            ),
        )


_security_context: ContextVar[SecurityContext | None] = ContextVar("security_context", default=None)


def bind_security_context(context: SecurityContext) -> Token[SecurityContext | None]:
    """Bind a verified context to the current asynchronous execution chain."""
    return _security_context.set(context)


def reset_security_context(token: Token[SecurityContext | None]) -> None:
    """Restore the context active before the current request or task."""
    _security_context.reset(token)


def current_security_context() -> SecurityContext:
    """Return the verified context or fail closed."""
    context = _security_context.get()
    if context is None:
        raise AuthenticationRequiredError
    return context
