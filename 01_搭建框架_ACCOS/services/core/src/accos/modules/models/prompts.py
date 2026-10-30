"""Immutable prompt releases, bounded rendering and packaged default protocols."""

from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from accos.kernel.errors import ConcurrencyConflictError, InvalidRequestError
from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import RuntimePackageManifest, SharedContract
from accos.modules.models.invocation import ModelMessage, Name, PromptPin
from accos.modules.models.runtime_ports import ModelStore
from accos.modules.models.schema import validate_schema, validate_value

_VARIABLE = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")


class PromptVersion(SharedContract):
    id: Name
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$", max_length=30)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    system_template: Annotated[str, Field(min_length=100, max_length=40_000)]
    user_template: Annotated[str, Field(min_length=1, max_length=40_000)]
    variables_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_tasks: Annotated[tuple[Name, ...], Field(min_length=1)]
    allowed_tools: tuple[Name, ...] = ()
    status: Literal["published"] = "published"
    checksum: str = ""

    def checked(self) -> PromptVersion:
        validate_schema(self.variables_schema)
        validate_schema(self.output_schema)
        required = set(self.variables_schema.get("required", []))
        declared = set(self.variables_schema.get("properties", {}))
        names = set(_VARIABLE.findall(self.system_template + "\n" + self.user_template))
        if (
            names != required
            or declared != required
            or self.variables_schema.get("additionalProperties") is not False
        ):
            raise InvalidRequestError(
                "Template placeholders must match exactly the required variables."
            )
        data = self.model_dump(mode="json", exclude={"checksum"})
        checksum = hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        if self.checksum and self.checksum != checksum:
            raise InvalidRequestError("Prompt checksum does not match its release content.")
        return self.model_copy(update={"checksum": checksum})

    @property
    def pin(self) -> PromptPin:
        return PromptPin(id=self.id, version=self.version, checksum=self.checksum)

    def render(self, variables: dict[str, Any], task_kind: str) -> tuple[ModelMessage, ...]:
        if task_kind not in self.allowed_tasks:
            raise InvalidRequestError("This prompt release does not support the task.")
        validate_value(variables, self.variables_schema)

        def render_text(template: str) -> str:
            # A single substitution pass: content cannot introduce new placeholders.
            return _VARIABLE.sub(
                lambda match: json.dumps(variables[match[1]], ensure_ascii=False), template
            )

        return (
            ModelMessage(role="system", text=render_text(self.system_template)),
            ModelMessage(role="user", text=render_text(self.user_template)),
        )


def packaged_prompts() -> tuple[PromptVersion, ...]:
    root = files("accos").joinpath("resources", "prompts")
    if not root.joinpath("manifest.json").is_file():
        root = Path(__file__).resolve().parents[4] / "resources" / "prompts"
    manifest = RuntimePackageManifest.model_validate_json(
        root.joinpath("manifest.json").read_bytes()
    )
    result = []
    for entry in manifest.files:
        content = root.joinpath(entry.path).read_bytes()
        if len(content) != entry.byte_length or hashlib.sha256(content).hexdigest() != entry.sha256:
            raise InvalidRequestError("Packaged prompt checksum mismatch.")
        if entry.kind == "prompt":
            result.append(PromptVersion.model_validate_json(content).checked())
    return tuple(result)


class PromptRegistry:
    def __init__(self, store: ModelStore, builtins: tuple[PromptVersion, ...]) -> None:
        self.store = store
        self.builtins = {(p.id, p.version): p for p in builtins}

    async def list(self, context: SecurityContext) -> tuple[PromptVersion, ...]:
        values = dict(self.builtins)
        for raw in await self.store.prompts(context.workspace_id):
            prompt = PromptVersion.model_validate(raw).checked()
            values[(prompt.id, prompt.version)] = prompt
        return tuple(
            sorted(
                values.values(), key=lambda p: (p.id, tuple(int(v) for v in p.version.split(".")))
            )
        )

    async def get(self, context: SecurityContext, name: str, version: str) -> PromptVersion:
        raw = await self.store.prompt(context.workspace_id, name, version)
        value = (
            PromptVersion.model_validate(raw).checked()
            if raw
            else self.builtins.get((name, version))
        )
        if value is None:
            raise InvalidRequestError("Prompt release is unavailable.")
        return value

    async def publish(
        self, context: SecurityContext, value: PromptVersion, expected: str | None
    ) -> PromptVersion:
        value = value.checked()
        if (value.id, value.version) in self.builtins:
            raise ConcurrencyConflictError
        existing = await self.store.prompt(context.workspace_id, value.id, value.version)
        if existing is not None:
            released = PromptVersion.model_validate(existing).checked()
            if released != value:
                raise ConcurrencyConflictError
            return released
        versions = [p.version for p in await self.list(context) if p.id == value.id]

        def semantic(version: str) -> tuple[int, ...]:
            return tuple(int(part) for part in version.split("."))

        latest = max(versions, key=semantic) if versions else None
        if expected != latest or (
            latest is not None and semantic(value.version) <= semantic(latest)
        ):
            raise ConcurrencyConflictError
        return PromptVersion.model_validate(
            await self.store.publish_prompt(context, value.model_dump(mode="json"), expected)
        )
