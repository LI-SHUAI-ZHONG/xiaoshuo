"""Workflow step executor that exercises the model and tool gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accos.modules.identity.public import Permission
from accos.modules.models.public import ModelCapability, ModelRequest
from accos.modules.tools.public import ToolGrant, ToolRequest
from accos.modules.workflows.domain import PermanentStepError, StepExecution, StepExecutionResult

if TYPE_CHECKING:
    from accos.modules.models.public import ModelGateway
    from accos.modules.tools.public import ToolGateway
    from accos.modules.workflows.ports import StepExecutor


class GatewayWorkflowExecutor:
    """Use both gateways on the smoke entry step and delegate all other steps."""

    def __init__(
        self,
        base: StepExecutor,
        model_gateway: ModelGateway,
        tool_gateway: ToolGateway,
    ) -> None:
        self._base = base
        self._model_gateway = model_gateway
        self._tool_gateway = tool_gateway

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        """Exercise model/tool controls once inside the technical smoke workflow."""
        if execution.step_key != "pass-token":
            return await self._base.execute(execution)
        if execution.context is None:
            raise PermanentStepError("workflow-error://security-context-missing")
        model = await self._model_gateway.invoke(
            execution.context,
            ModelRequest(
                ModelCapability.TEXT,
                execution.input_reference,
                16,
                f"{execution.idempotency_key}-model",
                execution.workflow_run_id,
                execution.task_run_id,
            ),
        )
        result = await self._tool_gateway.invoke(
            execution.context,
            ToolGrant(
                execution.context.workspace_id,
                execution.context.project_id,
                execution.task_run_id,
                frozenset({"fixture.reference"}),
                frozenset({Permission.TOOL_RUN.value}),
            ),
            ToolRequest(
                "fixture.reference",
                {"reference": model.output_reference},
                f"{execution.idempotency_key}-tool",
                execution.workflow_run_id,
                execution.task_run_id,
            ),
        )
        return StepExecutionResult(result.output_reference)

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        """Delegate deterministic compensation to the stage-08 executor."""
        await self._base.compensate(execution, hook)
