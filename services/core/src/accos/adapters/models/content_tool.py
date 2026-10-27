"""Read-only tool bound to the existing asset authorization boundary."""

from uuid import UUID

from accos.kernel.security import current_security_context
from accos.kernel.shared_contracts import ContentRef
from accos.modules.assets.public import AssetService
from accos.modules.identity.public import Permission
from accos.modules.tools.public import ToolDescriptor, ToolExecution, ToolResult


def content_tool_descriptor() -> ToolDescriptor:
    return ToolDescriptor(
        "content.read",
        "1.0.0",
        ("content.read",),
        {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"reference": {"type": "string"}, "content": {"type": "string"}},
            "required": ["reference", "content"],
            "additionalProperties": False,
        },
        frozenset({Permission.TOOL_RUN.value}),
        timeout_seconds=30,
    )


class ContentReadTool:
    def __init__(self, assets: AssetService) -> None:
        self.assets = assets

    async def execute(self, execution: ToolExecution) -> ToolResult:
        reference = str(execution.request.input_data["reference"])
        context = current_security_context()
        if context.project_id is None or not reference.startswith("content://"):
            raise ValueError("Scoped content reference required")
        asset, version_id = reference.removeprefix("content://").split("/")
        version = await self.assets.version(
            context, context.project_id, UUID(asset), UUID(version_id)
        )
        ref = ContentRef(
            asset_id=UUID(asset),
            asset_version_id=version.id,
            sha256=version.content_hash,
            media_type=version.media_type,
            byte_length=version.size_bytes,
        )
        data = await self.assets.read_snapshot(context, context.project_id, ref)
        if len(data) > 1_000_000 or version.media_type not in {
            "text/plain",
            "text/markdown",
            "application/json",
        }:
            raise ValueError("Content is not bounded text")
        return ToolResult({"reference": reference, "content": data.decode("utf-8")}, reference)
