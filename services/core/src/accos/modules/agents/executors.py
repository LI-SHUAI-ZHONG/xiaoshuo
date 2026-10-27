"""Deterministic Fake Agent executor backed only by public model/tool gateways."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from accos.modules.agents.definitions import DIRECTOR_AGENT_ID
from accos.modules.agents.domain import AgentResultKind, RawAgentResult
from accos.modules.identity.public import Permission
from accos.modules.models.public import (
    MetadataKind,
    MetadataStatus,
    ModelCapability,
    ModelRequest,
    PromptPolicyMetadata,
)
from accos.modules.tools.public import ToolGrant, ToolRequest

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.modules.agents.domain import AgentExecution
    from accos.modules.models.public import ModelGateway
    from accos.modules.tools.public import ToolGateway


@dataclass(frozen=True, slots=True)
class FakeAgentBehavior:
    """Optional fixed schema output or delay for boundary tests."""

    output_data: dict[str, object] | None = None
    delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.delay_seconds < 0:
            raise ValueError("fake Agent delay cannot be negative")


class FakeAgentExecutor:
    """Invoke only gateways, then emit deterministic references and typed metadata."""

    def __init__(
        self,
        models: ModelGateway,
        tools: ToolGateway,
        behaviors: Mapping[str, FakeAgentBehavior] | None = None,
    ) -> None:
        self._models = models
        self._tools = tools
        self._behaviors = dict(behaviors or {})
        self.calls: list[str] = []

    async def execute(self, execution: AgentExecution) -> RawAgentResult:
        """Exercise Fake Model and explicitly requested Fake Tools without content access."""
        self.calls.append(execution.invocation.idempotency_key)
        behavior = self._behaviors.get(execution.invocation.idempotency_key, FakeAgentBehavior())
        if behavior.delay_seconds:
            await asyncio.sleep(behavior.delay_seconds)
        input_reference = execution.invocation.input_data["input_reference"]
        if not isinstance(input_reference, str):
            raise ValueError("validated Agent input reference is unavailable")
        metadata = execution.descriptor.prompt_metadata
        workflow_run_id = execution.invocation.workflow_run_id or execution.run_id
        task_run_id = execution.invocation.task_run_id or execution.run_id
        model = await self._models.invoke(
            execution.context,
            ModelRequest(
                ModelCapability.TEXT,
                input_reference,
                min(16, execution.budget.max_tokens),
                f"{execution.invocation.idempotency_key}-model",
                workflow_run_id,
                task_run_id,
                PromptPolicyMetadata(
                    metadata.metadata_id,
                    MetadataKind.PROMPT,
                    metadata.version,
                    metadata.checksum,
                    MetadataStatus.ACTIVE,
                ),
            ),
        )
        result_reference = model.output_reference
        for index, tool_id in enumerate(execution.invocation.requested_tool_ids):
            tool = await self._tools.invoke(
                execution.context,
                ToolGrant(
                    execution.context.workspace_id,
                    execution.context.project_id,
                    task_run_id,
                    frozenset(execution.invocation.requested_tool_ids),
                    frozenset({Permission.TOOL_RUN.value}),
                ),
                ToolRequest(
                    tool_id,
                    {"reference": result_reference},
                    f"{execution.invocation.idempotency_key}-tool-{index}",
                    workflow_run_id,
                    task_run_id,
                ),
            )
            result_reference = tool.output_reference
        output = behavior.output_data or self._default_output(execution, result_reference)
        return RawAgentResult(
            dict(output),
            result_reference,
            1,
            len(execution.invocation.requested_tool_ids),
            model.total_tokens,
        )

    @staticmethod
    def _default_output(execution: AgentExecution, result_reference: str) -> dict[str, object]:
        if execution.descriptor.agent_id == DIRECTOR_AGENT_ID:
            return {
                "kind": AgentResultKind.WORKFLOW_SELECTION.value,
                "workflow_name": "framework_smoke",
                "workflow_version": 1,
                "input_reference": result_reference,
            }
        return {
            "kind": AgentResultKind.PROPOSAL.value,
            "result_reference": result_reference,
        }
