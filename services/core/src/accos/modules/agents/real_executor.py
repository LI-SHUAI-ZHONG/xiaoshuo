"""One real bounded Agent executor; specialized templates register in later steps."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from typing import Any
from uuid import UUID

from accos.kernel.errors import InvalidRequestError
from accos.kernel.security import bind_security_context, reset_security_context
from accos.kernel.shared_contracts import ContentRef
from accos.modules.agents.domain import (
    AgentBudget,
    AgentDescriptor,
    AgentErrorCode,
    AgentExecution,
    AgentRuntimeError,
    PromptMetadataReference,
    RawAgentResult,
)
from accos.modules.identity.public import Permission
from accos.modules.models.invocation import (
    ModelInvocation,
    ModelMessage,
    ModelRuntimeError,
    ProfilePin,
    ToolDefinition,
)
from accos.modules.models.prompts import PromptVersion
from accos.modules.models.runtime import ModelRuntime, canonical
from accos.modules.models.schema import validate_value
from accos.modules.tools.public import ToolGateway, ToolGrant, ToolRegistry, ToolRequest

REAL_AGENT_BUDGET = AgentBudget(16, 3, 1, 600, 24, 128_000)


def real_descriptors(prompts: tuple[PromptVersion, ...]) -> tuple[AgentDescriptor, ...]:
    result = []
    for prompt in prompts:
        name = (
            "director"
            if prompt.id == "director.plan"
            else "assistant"
            if prompt.id == "agent.task"
            else prompt.id
        )
        result.append(
            AgentDescriptor(
                name,
                "2.0.0",
                (prompt.id,),
                {
                    "type": "object",
                    "properties": {
                        "input_reference": {"type": "string"},
                        "task": {"type": "string"},
                        "content_refs": {"type": "array"},
                        "constraints": {"type": "string"},
                        "privacy": {"type": "string"},
                    },
                    "required": [],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "result_reference": {"type": "string"},
                    },
                    "required": ["kind", "result_reference"],
                    "additionalProperties": False,
                },
                ("content.read",),
                "default",
                "1.0.0",
                PromptMetadataReference(prompt.id, prompt.version, prompt.checksum),
                REAL_AGENT_BUDGET,
            )
        )
    return tuple(result)


class RealAgentExecutor:
    def __init__(self, runtime: ModelRuntime, tools: ToolGateway, registry: ToolRegistry) -> None:
        self.runtime, self.tools, self.registry = runtime, tools, registry
        # The Workflow owner extends this registration when actual executors are ready.
        self.task_kinds = tuple(p.id for p in runtime.prompts.builtins.values())

    async def execute(self, execution: AgentExecution) -> RawAgentResult:
        context = replace(execution.context, project_id=execution.snapshot.project_id)
        data, budget = execution.invocation.input_data, execution.budget
        prompt = await self.runtime.prompts.get(
            context,
            execution.snapshot.prompt_metadata_id,
            execution.snapshot.prompt_metadata_version,
        )
        if prompt.id not in execution.descriptor.capabilities:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        if prompt.checksum != execution.snapshot.prompt_metadata_checksum:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        task = data.get("task", "")
        if not isinstance(task, str):
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        raw_refs = data.get("content_refs", [])
        if not isinstance(raw_refs, list):
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        refs = tuple(ContentRef.model_validate(value) for value in raw_refs)
        if not task and not refs:
            # Legacy hash-only input cannot be magically resolved into original prose.
            raise AgentRuntimeError(AgentErrorCode.CONTEXT_PACKAGE_INVALID)
        sources: dict[str, ContentRef] = {
            f"content://{r.asset_id}/{r.asset_version_id}": r for r in refs
        }
        sections = []
        for reference, ref in sources.items():
            content = await self.runtime.content.read_snapshot(
                context, execution.snapshot.project_id, ref
            )
            sections.append({"source_ref": reference, "content": content.decode("utf-8")})
        package_id = execution.snapshot.memory_context_package_id
        if package_id:
            package = await self.runtime.contexts.get(
                context, execution.snapshot.project_id, package_id
            )
            sections.extend(
                {"source_ref": f"memory://{i.record_id}", "content": i.content}
                for i in package.items
            )
        allowed_sources = {str(item["source_ref"]) for item in sections}
        requested_tools = set(execution.invocation.requested_tool_ids)
        if not requested_tools.issubset(prompt.allowed_tools):
            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
        tool_definitions = []
        for tool_id in sorted(requested_tools):
            selected = self.registry.resolve(tool_id)
            if selected is None or not selected[0].idempotent:
                raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
            descriptor = selected[0]
            tool_definitions.append(
                ToolDefinition(
                    name=tool_id,
                    description="Read only an explicitly supplied immutable content reference.",
                    parameters=descriptor.input_schema,
                )
            )
        messages = list(
            prompt.render(
                {
                    "task": task,
                    "context": json.dumps(sections, ensure_ascii=False),
                    "constraints": str(data.get("constraints", "")),
                    "available_tools": sorted(requested_tools),
                    "available_workflows": list(self.task_kinds),
                },
                prompt.id,
            )
        )
        model_calls = tool_calls = tokens = 0
        continuation_profile = None
        context_token = bind_security_context(context)
        try:
            for turn in range(budget.max_steps):
                if model_calls + tool_calls >= budget.max_calls:
                    raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
                available = budget.max_tokens - tokens
                estimate = (
                    len(canonical([m.model_dump(mode="json") for m in messages]))
                    + len(messages) * 64
                    + 2048
                )
                if available <= estimate:
                    raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
                operation = hashlib.sha256(f"{execution.run_id}:model:{turn}".encode()).hexdigest()
                privacy = data.get("privacy", "local_only")
                if privacy not in {"local_only", "workspace"}:
                    raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
                request = ModelInvocation(
                    operation_key=operation,
                    policy=ProfilePin(
                        id=execution.snapshot.model_policy_id,
                        version=int(execution.snapshot.model_policy_version.split(".")[0]),
                    ),
                    messages=tuple(messages),
                    prompt=prompt.pin,
                    task_kind=prompt.id,
                    output_schema=prompt.output_schema,
                    tools=tuple(tool_definitions),
                    max_output_tokens=min(2048, available - estimate),
                    privacy=privacy,
                    workflow_run_id=execution.invocation.workflow_run_id or execution.run_id,
                    task_run_id=execution.invocation.task_run_id or execution.run_id,
                    context_package_id=package_id,
                    task_token_limit=budget.max_tokens,
                    task_call_limit=budget.max_calls - tool_calls,
                    continuation_profile=continuation_profile,
                )
                try:
                    call, output = await self.runtime.invoke(
                        context, execution.snapshot.project_id, request
                    )
                except ModelRuntimeError as error:
                    code = (
                        AgentErrorCode.CONFIG_REQUIRED
                        if error.reason
                        in {
                            "CONFIG_REQUIRED",
                            "PRICE_REQUIRED",
                            "BUDGET_CONFIGURATION_REQUIRED",
                            "TASK_POLICY_DENIED",
                            "CLOUD_CONTENT_DENIED",
                        }
                        else AgentErrorCode.MODEL_RESULT_UNKNOWN
                        if error.uncertain
                        else AgentErrorCode.MODEL_REFUSED
                        if error.reason == "REFUSED"
                        else AgentErrorCode.MODEL_INCOMPLETE
                        if error.reason == "INCOMPLETE"
                        else AgentErrorCode.EXECUTION_FAILED
                    )
                    raise AgentRuntimeError(code) from None
                model_calls += call.attempt_count
                tokens += call.usage.total if call.usage else estimate * max(1, call.attempt_count)
                if output.tool_calls:
                    if output.continuation:
                        continuation_profile = call.profile
                    if model_calls + tool_calls + len(output.tool_calls) + 1 > budget.max_calls:
                        raise AgentRuntimeError(AgentErrorCode.BUDGET_EXHAUSTED)
                    # A local synthetic ID is scoped to the turn and never reused.
                    calls = tuple(
                        c.model_copy(update={"call_id": f"{turn}-{c.call_id}"})
                        if c.call_id.startswith("ollama-")
                        else c
                        for c in output.tool_calls
                    )
                    messages.append(
                        ModelMessage(
                            role="assistant",
                            text=output.text or None,
                            tool_calls=calls,
                            provider_items=output.continuation,
                        )
                    )
                    for item in calls:
                        if (
                            item.name not in requested_tools
                            or item.name != "content.read"
                            or item.arguments.get("reference") not in sources
                        ):
                            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
                        selected = self.registry.resolve(item.name)
                        if selected is None:
                            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
                        validate_value(item.arguments, selected[0].input_schema)
                        reference = str(item.arguments["reference"])
                        tool_key = hashlib.sha256(
                            f"{execution.run_id}:{turn}:{item.call_id}".encode()
                        ).hexdigest()
                        result = await self.tools.invoke(
                            context,
                            ToolGrant(
                                context.workspace_id,
                                context.project_id,
                                execution.invocation.task_run_id or execution.run_id,
                                frozenset(requested_tools),
                                frozenset({Permission.TOOL_RUN.value}),
                            ),
                            ToolRequest(
                                item.name,
                                {"reference": reference},
                                tool_key,
                                execution.invocation.workflow_run_id or execution.run_id,
                                execution.invocation.task_run_id or execution.run_id,
                            ),
                        )
                        tool_calls += 1
                        messages.append(
                            ModelMessage(
                                role="tool",
                                call_id=item.call_id,
                                text=json.dumps(result.output_data, ensure_ascii=False),
                            )
                        )
                    continue
                document = json.loads(output.text)
                validate_value(document, prompt.output_schema)
                if set(document.get("source_refs", [])) - allowed_sources:
                    raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
                kind = document["kind"]
                if kind == "plan":
                    self._validate_plan(document, allowed_sources, budget.max_steps)
                # Store the substantive structured candidate in the existing asset owner.
                ref = await self.runtime.content.put_snapshot(
                    context,
                    execution.snapshot.project_id,
                    canonical(document),
                    media_type="application/json",
                )
                reference = f"content://{ref.asset_id}/{ref.asset_version_id}"
                result_kind = (
                    "plan" if kind == "plan" else "draft" if kind == "draft" else "proposal"
                )
                return RawAgentResult(
                    {"kind": result_kind, "result_reference": reference},
                    reference,
                    model_calls,
                    tool_calls,
                    tokens,
                )
            raise AgentRuntimeError(AgentErrorCode.STEP_LIMIT_EXCEEDED)
        except InvalidRequestError:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH) from None
        finally:
            reset_security_context(context_token)

    def _validate_plan(self, document: dict[str, Any], sources: set[str], limit: int) -> None:
        nodes = document["nodes"]
        ids = {node["id"] for node in nodes}
        if (
            len(nodes) > limit
            or len(ids) != len(nodes)
            or any(not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", identifier) for identifier in ids)
        ):
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        pending = {node["id"]: set(node["depends_on"]) for node in nodes}
        for node in nodes:
            if (
                node["task_kind"] not in self.task_kinds
                or set(node["input_refs"]) - sources
                or set(node["depends_on"]) - ids
            ):
                raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        while pending:
            ready = {key for key, dependencies in pending.items() if not dependencies}
            if not ready:
                raise AgentRuntimeError(AgentErrorCode.LOOP_DETECTED)
            pending = {
                key: dependencies - ready
                for key, dependencies in pending.items()
                if key not in ready
            }
