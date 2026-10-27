"""Default-deny tool registry, grant enforcement, schemas, and audit."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.tools.domain import (
    PluginManifest,
    PluginTrustStatus,
    ToolCallRecord,
    ToolCallStatus,
    ToolErrorCode,
    ToolExecution,
    ToolGatewayError,
)

if TYPE_CHECKING:
    from datetime import datetime
    from typing import NoReturn

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.tools.domain import ToolDescriptor, ToolGrant, ToolRequest, ToolResult
    from accos.modules.tools.ports import ToolCallLedger, ToolExecutor


@dataclass(frozen=True, slots=True)
class _CallOutcome:
    version: str | None
    status: ToolCallStatus
    code: ToolErrorCode | None
    started_at: datetime


class ToolRegistry:
    """In-process catalog of descriptors and explicitly supplied executors."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolDescriptor, ToolExecutor]] = {}
        self._plugins: dict[str, PluginManifest] = {}

    def register(self, descriptor: ToolDescriptor, executor: ToolExecutor) -> None:
        """Register one stable tool id/version pair."""
        if descriptor.tool_id in self._tools:
            raise ValueError("tool id is already registered")
        self._tools[descriptor.tool_id] = (descriptor, executor)

    def resolve(self, tool_id: str) -> tuple[ToolDescriptor, ToolExecutor] | None:
        """Resolve a tool without performing authorization."""
        return self._tools.get(tool_id)

    @property
    def tools(self) -> tuple[ToolDescriptor, ...]:
        """Return credential-free descriptors in registration order."""
        return tuple(descriptor for descriptor, _executor in self._tools.values())

    def register_plugin(self, manifest: PluginManifest) -> None:
        """Enable only locally trusted manifests; installation grants no tool access."""
        if not manifest.enabled or manifest.trust_status is not PluginTrustStatus.TRUSTED:
            raise ValueError("plugin must be enabled and locally trusted")
        if manifest.plugin_id in self._plugins:
            raise ValueError("plugin id is already registered")
        self._plugins[manifest.plugin_id] = manifest

    @property
    def plugins(self) -> tuple[PluginManifest, ...]:
        """Return loaded declarative manifests only."""
        return tuple(self._plugins.values())


class ToolGateway:
    """Authorize and constrain every tool call before an executor sees input."""

    def __init__(
        self,
        registry: ToolRegistry,
        ledger: ToolCallLedger,
        authorizer: AuthorizationService,
        clock: Clock,
    ) -> None:
        self._registry = registry
        self._ledger = ledger
        self._authorizer = authorizer
        self._clock = clock

    async def invoke(
        self,
        context: SecurityContext,
        grant: ToolGrant,
        request: ToolRequest,
    ) -> ToolResult:
        """Fail closed for unknown, ungranted, malformed, timed-out, or over-scoped calls."""
        started_at = self._clock.now()
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.TOOL_RUN,
                ResourceScope(
                    context.workspace_id,
                    "tool",
                    request.tool_id,
                    context.project_id,
                ),
            )
        )
        selected = self._registry.resolve(request.tool_id)
        if selected is None:
            await self._reject(
                context,
                request,
                _CallOutcome(None, ToolCallStatus.UNKNOWN, ToolErrorCode.UNKNOWN_TOOL, started_at),
            )
        descriptor, executor = selected
        if not self._grant_matches(context, grant, request, descriptor):
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.DENIED,
                    ToolErrorCode.PERMISSION_DENIED,
                    started_at,
                ),
            )
        if not self._scopes_allowed(grant, request, descriptor):
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.DENIED,
                    ToolErrorCode.SCOPE_VIOLATION,
                    started_at,
                ),
            )
        if not _matches_schema(request.input_data, descriptor.input_schema):
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.SCHEMA_REJECTED,
                    ToolErrorCode.SCHEMA_INVALID,
                    started_at,
                ),
            )
        try:
            async with asyncio.timeout(descriptor.timeout_seconds):
                result = await executor.execute(ToolExecution(descriptor, request))
        except TimeoutError:
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.TIMED_OUT,
                    ToolErrorCode.TIMED_OUT,
                    started_at,
                ),
            )
        except Exception:  # noqa: BLE001 - adapters cannot leak raw failures.
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.FAILED,
                    ToolErrorCode.EXECUTION_FAILED,
                    started_at,
                ),
            )
        if not _matches_schema(result.output_data, descriptor.output_schema):
            await self._reject(
                context,
                request,
                _CallOutcome(
                    descriptor.version,
                    ToolCallStatus.FAILED,
                    ToolErrorCode.INVALID_OUTPUT,
                    started_at,
                ),
            )
        await self._record(
            context,
            request,
            _CallOutcome(descriptor.version, ToolCallStatus.SUCCEEDED, None, started_at),
        )
        return result

    @staticmethod
    def _grant_matches(
        context: SecurityContext,
        grant: ToolGrant,
        request: ToolRequest,
        descriptor: ToolDescriptor,
    ) -> bool:
        return (
            grant.workspace_id == context.workspace_id
            and grant.project_id == context.project_id
            and grant.task_run_id == request.task_run_id
            and descriptor.tool_id in grant.allowed_tool_ids
            and descriptor.required_permissions.issubset(context.permissions)
            and descriptor.required_permissions.issubset(grant.allowed_permissions)
        )

    @staticmethod
    def _scopes_allowed(
        grant: ToolGrant,
        request: ToolRequest,
        descriptor: ToolDescriptor,
    ) -> bool:
        if not set(request.network_hosts).issubset(descriptor.allowed_network_hosts) or not set(
            request.network_hosts
        ).issubset(grant.allowed_network_hosts):
            return False
        if any(
            not _under_root(path, descriptor.allowed_file_roots)
            or not _under_root(path, grant.allowed_file_roots)
            for path in request.file_paths
        ):
            return False
        for resource in request.resources:
            resource_type, separator, _resource_id = resource.partition(":")
            if (
                not separator
                or resource_type not in descriptor.allowed_resource_types
                or resource not in grant.allowed_resources
            ):
                return False
        return True

    async def _reject(
        self,
        context: SecurityContext,
        request: ToolRequest,
        outcome: _CallOutcome,
    ) -> NoReturn:
        await self._record(context, request, outcome)
        raise ToolGatewayError(cast("ToolErrorCode", outcome.code))

    async def _record(
        self,
        context: SecurityContext,
        request: ToolRequest,
        outcome: _CallOutcome,
    ) -> None:
        await self._ledger.append(
            ToolCallRecord(
                uuid4(),
                context.workspace_id,
                context.project_id,
                request.workflow_run_id,
                request.task_run_id,
                context.actor_id,
                UUID(context.correlation.request_id),
                request.idempotency_key,
                request.tool_id,
                outcome.version,
                outcome.status,
                outcome.code,
                outcome.started_at,
                self._clock.now(),
            )
        )


def _under_root(path: str, roots: tuple[str, ...]) -> bool:
    candidate = PurePosixPath(path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    return any(
        candidate.parts[: len(root.parts)] == root.parts
        for value in roots
        if (root := PurePosixPath(value)).parts
    )


def _matches_schema(value: dict[str, object], schema: dict[str, object]) -> bool:
    """Validate the intentionally small object-schema subset used by tool contracts."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        return False
    if any(not isinstance(key, str) or key not in value for key in required):
        return False
    if schema.get("additionalProperties") is False and any(key not in properties for key in value):
        return False
    type_map: dict[str, type[object] | tuple[type[object], ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
    }
    for key, item in value.items():
        definition = properties.get(key)
        if not isinstance(definition, dict):
            return False
        kind = definition.get("type")
        expected = type_map.get(kind) if isinstance(kind, str) else None
        if expected is None or (
            not isinstance(item, expected) or (isinstance(item, bool) and expected is not bool)
        ):
            return False
    return True
