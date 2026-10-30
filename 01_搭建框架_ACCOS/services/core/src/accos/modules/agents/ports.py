"""Ports owned by the Agent runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.security import SecurityContext
    from accos.modules.agents.domain import (
        AgentContextSnapshot,
        AgentDescriptor,
        AgentExecution,
        AgentInvocation,
        AgentResult,
        AgentRun,
        AgentRunEvent,
        AgentRunStatus,
        AgentRuntimeError,
        RawAgentResult,
        RoleDescriptorVersion,
        RoleToolGrant,
        SupervisedAgentResult,
    )


class AgentRegistry(Protocol):
    """Resolve immutable descriptors without granting execution authority."""

    def get(self, agent_id: str) -> AgentDescriptor | None: ...

    def all(self) -> tuple[AgentDescriptor, ...]: ...


class RoleRepository(Protocol):
    """Durable workspace role versions and revocable tool grants."""

    async def save_role(self, role: RoleDescriptorVersion) -> RoleDescriptorVersion: ...

    async def get_role(
        self, workspace_id: UUID, role_key: str, role_version: int
    ) -> RoleDescriptorVersion | None: ...

    async def list_roles(self, workspace_id: UUID) -> tuple[RoleDescriptorVersion, ...]: ...

    async def set_role_status(
        self, workspace_id: UUID, role_id: UUID, status: str
    ) -> RoleDescriptorVersion: ...

    async def save_grant(self, grant: RoleToolGrant) -> RoleToolGrant: ...

    async def list_grants(
        self, workspace_id: UUID, role_version_id: UUID
    ) -> tuple[RoleToolGrant, ...]: ...

    async def revoke_grant(
        self, workspace_id: UUID, grant_id: UUID
    ) -> RoleToolGrant: ...


class AgentExecutor(Protocol):
    """Stateless execution boundary; infrastructure is provided through gateways."""

    async def execute(self, execution: AgentExecution) -> RawAgentResult: ...


class AgentSupervisor(Protocol):
    """Authorize and bound exactly one Agent invocation."""

    async def run(
        self, context: SecurityContext, project_id: UUID, invocation: AgentInvocation
    ) -> SupervisedAgentResult: ...

    async def get(self, context: SecurityContext, run_id: UUID) -> AgentRun: ...


class AgentRepository(Protocol):
    """Persistent owner of Agent runs, immutable snapshots, and lifecycle events."""

    async def begin(
        self,
        run: AgentRun,
        snapshot: AgentContextSnapshot,
        *,
        request_digest: str,
    ) -> tuple[AgentRun, bool]: ...

    async def complete(
        self, run_id: UUID, result: AgentResult, raw: RawAgentResult
    ) -> AgentRun: ...

    async def fail(
        self, run_id: UUID, status: AgentRunStatus, error: AgentRuntimeError
    ) -> AgentRun: ...

    async def attach_workflow(
        self, workspace_id: UUID, run_id: UUID, workflow_run_id: UUID, *, waiting: bool
    ) -> AgentRun: ...

    async def settle_approval(
        self, workspace_id: UUID, run_id: UUID, *, approved: bool
    ) -> AgentRun: ...

    async def get(self, workspace_id: UUID, run_id: UUID) -> AgentRun | None: ...

    async def get_by_idempotency(
        self, workspace_id: UUID, idempotency_key: str
    ) -> AgentRun | None: ...

    async def get_snapshot(
        self, workspace_id: UUID, snapshot_id: UUID
    ) -> AgentContextSnapshot | None: ...

    async def get_events(
        self, workspace_id: UUID, run_id: UUID, *, after_sequence: int = 0
    ) -> tuple[AgentRunEvent, ...]: ...


class AgentMetrics(Protocol):
    """Minimal metric sink independent of a concrete telemetry backend."""

    def record(self, agent_id: str, status: AgentRunStatus) -> None: ...
