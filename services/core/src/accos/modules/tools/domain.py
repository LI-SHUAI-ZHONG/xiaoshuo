"""Tool descriptors, grants, call records, and plugin manifests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from accos.kernel.contracts import IdempotencyKey, VersionNumber

TOOL_PROTOCOL_VERSION: Literal["tools.v1"] = "tools.v1"
PLUGIN_MANIFEST_PROTOCOL_VERSION = "plugin-manifest.v1"

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class ToolAuditPolicy(StrEnum):
    """Payload-free audit detail levels."""

    MINIMAL = "minimal"
    METADATA = "metadata"


class ToolCallStatus(StrEnum):
    """Stable persisted tool call outcomes."""

    SUCCEEDED = "succeeded"
    UNKNOWN = "unknown"
    DENIED = "denied"
    SCHEMA_REJECTED = "schema_rejected"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class ToolErrorCode(StrEnum):
    """Safe failure codes returned by the tool gateway."""

    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    TIMED_OUT = "TIMED_OUT"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    INVALID_OUTPUT = "INVALID_OUTPUT"


class PluginTrustStatus(StrEnum):
    """Trust established by the local loader, never by manifest self-assertion."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    UNSIGNED = "unsigned"


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Versioned least-privilege tool declaration."""

    tool_id: str
    version: str
    capabilities: tuple[str, ...]
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    required_permissions: frozenset[str]
    allowed_network_hosts: tuple[str, ...] = ()
    allowed_file_roots: tuple[str, ...] = ()
    allowed_resource_types: frozenset[str] = frozenset()
    timeout_seconds: float = 1.0
    idempotent: bool = True
    audit_policy: ToolAuditPolicy = ToolAuditPolicy.METADATA

    def __post_init__(self) -> None:
        if not self.tool_id or self.tool_id.strip() != self.tool_id:
            raise ValueError("tool id must be non-empty and trimmed")
        VersionNumber(self.version)
        if not self.capabilities or any(not item for item in self.capabilities):
            raise ValueError("tool descriptor requires named capabilities")
        if self.timeout_seconds <= 0:
            raise ValueError("tool timeout must be positive")
        if self.input_schema.get("type") != "object" or self.output_schema.get("type") != "object":
            raise ValueError("tool schemas must describe JSON objects")
        if any(not value or "://" in value for value in self.allowed_network_hosts):
            raise ValueError("network scope must contain host names only")
        if any(not value or value.startswith(("/", "\\")) for value in self.allowed_file_roots):
            raise ValueError("file roots must be relative and explicit")


@dataclass(frozen=True, slots=True)
class ToolGrant:
    """Explicit workspace/task capability grant that only narrows descriptors."""

    workspace_id: UUID
    project_id: UUID | None
    task_run_id: UUID
    allowed_tool_ids: frozenset[str]
    allowed_permissions: frozenset[str]
    allowed_network_hosts: frozenset[str] = frozenset()
    allowed_file_roots: tuple[str, ...] = ()
    allowed_resources: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """One traceable request with explicit requested side-effect scopes."""

    tool_id: str
    input_data: dict[str, object]
    idempotency_key: str
    workflow_run_id: UUID
    task_run_id: UUID
    network_hosts: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        IdempotencyKey(self.idempotency_key)
        if not self.tool_id or self.tool_id.strip() != self.tool_id:
            raise ValueError("tool id must be non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class ToolExecution:
    """Validated execution command containing only granted scopes."""

    descriptor: ToolDescriptor
    request: ToolRequest


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Validated fake/external tool result and opaque output reference."""

    output_data: dict[str, object]
    output_reference: str

    def __post_init__(self) -> None:
        if "://" not in self.output_reference or any(
            character.isspace() for character in self.output_reference
        ):
            raise ValueError("tool output must be an opaque reference")


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """Append-only tool authorization and execution evidence without payloads."""

    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    workflow_run_id: UUID
    task_run_id: UUID
    actor_id: UUID
    correlation_id: UUID
    idempotency_key: str
    tool_id: str
    tool_version: str | None
    status: ToolCallStatus
    error_code: ToolErrorCode | None
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Declarative plugin metadata; it never loads remote or executable code."""

    plugin_id: str
    version: str
    core_compatibility: str
    capabilities: tuple[str, ...]
    required_permissions: frozenset[str]
    signature: str | None
    trust_status: PluginTrustStatus
    enabled: bool

    def __post_init__(self) -> None:
        if not self.plugin_id or self.plugin_id.strip() != self.plugin_id:
            raise ValueError("plugin id must be non-empty and trimmed")
        VersionNumber(self.version)
        if not self.core_compatibility or not self.capabilities:
            raise ValueError("plugin compatibility and capabilities are required")


class ToolGatewayError(Exception):
    """Stable tool failure that never includes payload or adapter details."""

    def __init__(self, code: ToolErrorCode) -> None:
        super().__init__(code.value)
        self.code = code
