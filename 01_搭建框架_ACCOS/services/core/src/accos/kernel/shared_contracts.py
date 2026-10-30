"""Versioned content, capability and release contracts, independent of runtime wiring.

This is the source of generated JSON Schema and TypeScript. A valid reference is
not proof of authorization, existence, availability or successful verification.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = "1.0.0"
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
VersionTag = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")]
NonBlank = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^\S(?:.*\S)?$")]


class SharedContract(BaseModel):
    """Closed, immutable boundary values; major changes need a new contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DataOwner(StrEnum):
    IDENTITY = "identity"
    PROJECTS = "projects"
    ASSETS = "assets"
    MODELS = "models"
    TOOLS = "tools"
    WORKFLOWS = "workflows"
    AGENTS = "agents"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    NOVEL = "creative.novel"
    WORLD = "creative.world"
    CHARACTER = "creative.character"
    CREATOR = "creative.creator"
    CONSISTENCY = "consistency"
    QUALITY = "quality"
    FEEDBACK = "feedback"
    EVOLUTION = "evolution"
    IP = "ip"
    PUBLISHING = "publishing"
    MEDIA = "media"
    COLLABORATION = "collaboration"
    ECOSYSTEM = "ecosystem"


class ScopeRef(SharedContract):
    """Explicit anchor; the server must resolve grants before using this value."""

    workspace_id: UUID
    kind: Literal["workspace", "project", "universe", "creator"]
    anchor_id: UUID

    @model_validator(mode="after")
    def workspace_anchor_matches(self) -> Self:
        if self.kind == "workspace" and self.anchor_id != self.workspace_id:
            raise ValueError("A workspace anchor must identify its own workspace")
        return self


class ContentRef(SharedContract):
    """Immutable bytes owned by assets; hash is computed by the server."""

    asset_id: UUID
    asset_version_id: UUID
    sha256: Sha256
    media_type: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*$")]
    byte_length: Annotated[int, Field(ge=0)]


class EntityRevisionRef(SharedContract):
    owner: DataOwner
    entity_type: NonBlank
    id: UUID
    revision_id: UUID
    version: Annotated[int, Field(ge=1)]
    branch_id: UUID | None


class SourceSpan(SharedContract):
    """Offsets use Unicode code points, with an exclusive end, not UTF-8 bytes."""

    block_id: str | None = None
    page: Annotated[int, Field(ge=1)] | None = None
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def ordered_offsets(self) -> Self:
        if self.end < self.start:
            raise ValueError("Source span end precedes start")
        return self


class SourceRef(SharedContract):
    revision: EntityRevisionRef
    content: ContentRef | None = None
    span: SourceSpan | None = None


class Provenance(SharedContract):
    source_refs: tuple[SourceRef, ...]
    authority: Literal[
        "author_statement", "accepted_fact", "source_claim", "candidate", "inference"
    ]
    run_id: UUID | None = None
    step_id: UUID | None = None
    prompt_version: str | None = None
    model_profile_version: str | None = None
    extraction_version: str | None = None
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    license_ref: EntityRevisionRef | None = None


class CursorPageRequest(SharedContract):
    """Keyset pagination for new collections; legacy offset endpoints stay valid."""

    cursor: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 20


class CapabilityRequirement(SharedContract):
    code: NonBlank
    kind: Literal["configuration", "permission", "dependency", "data"]
    message: Annotated[str, Field(min_length=1, max_length=500)]
    configuration_path: str | None = None

    @field_validator("configuration_path")
    @classmethod
    def local_configuration_link(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.startswith("/")
            or value.startswith("//")
            or "\\" in value
            or any(ord(char) < 32 for char in value)
        ):
            raise ValueError("Configuration links must be local application paths")
        return value


class CapabilityStatus(SharedContract):
    """V2 adds independent axes; it does not replace legacy extension flags."""

    schema_version: Literal[2] = 2
    capability: NonBlank
    enabled: bool
    implementation: Literal["absent", "port_only", "implemented"]
    implementation_version: VersionTag | None
    configuration: Literal["missing", "configured"]
    health: Literal["unknown", "ready", "degraded", "unavailable"]
    verification: Literal["untested", "verified", "failed"]
    data: Literal["empty", "sufficient", "insufficient"]
    requirements: tuple[CapabilityRequirement, ...] = ()
    evidence_refs: tuple[NonBlank, ...] = ()
    verified_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def evidence_is_explicit(self) -> Self:
        if self.implementation == "implemented" and self.implementation_version is None:
            raise ValueError("Implemented capabilities need an implementation version")
        if self.verification == "verified" and (not self.evidence_refs or self.verified_at is None):
            raise ValueError("Verified capabilities need evidence and its timestamp")
        return self


def package_relative_path(value: str) -> str:
    """Portable paths without traversal, drive names, or Windows device aliases."""
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(10)),
        *(f"lpt{i}" for i in range(10)),
    }
    parts = value.split("/")
    if (
        not value
        or "\\" in value
        or ":" in value
        or len(value) > 500
        or any(ord(char) < 32 for char in value)
        or any(
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".", maxsplit=1)[0].casefold() in reserved
            for part in parts
        )
    ):
        raise ValueError("Package path must be a safe relative path")
    return value


class RuntimePackageFile(SharedContract):
    path: str
    sha256: Sha256
    byte_length: Annotated[int, Field(ge=0)]
    kind: Literal["prompt", "workflow", "rubric", "schema", "documentation", "code", "static_asset"]

    @field_validator("path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        return package_relative_path(value)


class RuntimePackageDependency(SharedContract):
    package_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,199}$")]
    version: VersionTag
    manifest_sha256: Sha256


class RuntimePackageManifest(SharedContract):
    """Every runtime file is hashed; dependencies pin exact manifests, never latest."""

    schema_version: Literal[1] = 1
    package_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,199}$")]
    version: VersionTag
    owner: DataOwner
    package_type: Literal[
        "prompt",
        "workflow",
        "rubric",
        "tool",
        "agent",
        "knowledge",
        "content",
        "ui-module",
        "core-change",
    ]
    minimum_contract_version: VersionTag
    files: Annotated[tuple[RuntimePackageFile, ...], Field(min_length=1)]
    entrypoints: Annotated[dict[str, str], Field(min_length=1)]
    dependencies: tuple[RuntimePackageDependency, ...] = ()
    required_permissions: tuple[NonBlank, ...] = ()
    input_schema: str | None = None
    output_schema: str | None = None

    @model_validator(mode="after")
    def all_entrypoints_are_manifested(self) -> Self:
        paths = {file.path for file in self.files}
        if len({path.casefold() for path in paths}) != len(self.files):
            raise ValueError("Duplicate or case-colliding package path")
        for path in (*self.entrypoints.values(), self.input_schema, self.output_schema):
            if path is not None and package_relative_path(path) not in paths:
                raise ValueError("Every entrypoint and schema must be a manifested file")
        dependencies = [item.package_id for item in self.dependencies]
        if len(set(dependencies)) != len(dependencies) or self.package_id in dependencies:
            raise ValueError("Duplicate or self-referencing package dependency")
        return self


SHARED_CONTRACTS = (
    ScopeRef,
    ContentRef,
    EntityRevisionRef,
    SourceSpan,
    SourceRef,
    Provenance,
    CursorPageRequest,
    CapabilityStatus,
    RuntimePackageManifest,
)
