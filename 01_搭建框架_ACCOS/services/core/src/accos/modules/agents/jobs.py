"""Durable Agent execution requests consumed by the existing Worker process."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import Field

from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import ContentRef, SharedContract
from accos.modules.agents.domain import (
    AgentBudget,
    AgentErrorCode,
    AgentInvocation,
    AgentRuntimeError,
)
from accos.modules.agents.ports import AgentRegistry, AgentSupervisor
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.models.invocation import Name, OperationKey, ProfilePin, PromptPin
from accos.modules.models.runtime import ModelRuntime, canonical


class AgentTaskInput(SharedContract):
    operation_key: OperationKey
    agent_id: Name
    task: Annotated[str, Field(min_length=1, max_length=100_000)]
    content_refs: Annotated[tuple[ContentRef, ...], Field(max_length=32)] = ()
    constraints: Annotated[str, Field(max_length=20_000)] = ""
    privacy: Literal["local_only", "workspace"] = "local_only"
    policy: ProfilePin
    prompt: PromptPin | None = None
    context_package_id: UUID | None = None
    tools: tuple[Name, ...] = ()
    max_steps: Annotated[int, Field(ge=1, le=16)] = 8
    max_calls: Annotated[int, Field(ge=1, le=24)] = 12
    max_tokens: Annotated[int, Field(ge=1024, le=128_000)] = 32_000
    timeout_seconds: Annotated[int, Field(ge=1, le=600)] = 300


class AgentJob(SharedContract):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    actor_id: UUID
    input_ref: ContentRef
    status: Literal["queued", "running", "completed", "failed", "unknown"] = "queued"
    agent_run_id: UUID | None = None
    result_reference: str | None = None
    result_kind: str | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentJobPage(SharedContract):
    items: tuple[AgentJob, ...]
    next_cursor: str | None = None


class AgentJobStore(Protocol):
    async def create(
        self, job: AgentJob, key: str, digest: str, headers: dict[str, str]
    ) -> AgentJob: ...
    async def claim(self, now: datetime) -> tuple[AgentJob, dict[str, str]] | None: ...
    async def finish(self, job: AgentJob) -> AgentJob: ...
    async def get(self, workspace: UUID, project: UUID, identifier: UUID) -> AgentJob: ...
    async def recover(self, now: datetime) -> None: ...
    async def list(
        self, workspace: UUID, project: UUID, cursor: str | None, limit: int
    ) -> AgentJobPage: ...


class AgentJobService:
    def __init__(
        self,
        store: AgentJobStore,
        runtime: ModelRuntime,
        supervisor: AgentSupervisor,
        registry: AgentRegistry,
    ) -> None:
        self.store, self.runtime, self.supervisor, self.registry = (
            store,
            runtime,
            supervisor,
            registry,
        )

    async def submit(
        self, context: SecurityContext, project: UUID, task: AgentTaskInput
    ) -> AgentJob:
        context = await self.runtime.authorize(context, project, write=True)
        await self.runtime.accounts.authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.AGENT_RUN,
                ResourceScope(context.workspace_id, "project", str(project), project),
            )
        )
        digest = hashlib.sha256(canonical(task.model_dump(mode="json"))).hexdigest()
        descriptor = self.registry.get(task.agent_id)
        if descriptor is None:
            raise AgentRuntimeError(AgentErrorCode.UNKNOWN_AGENT)
        pin = task.prompt or PromptPin(
            id=descriptor.prompt_metadata.metadata_id,
            version=descriptor.prompt_metadata.version,
            checksum=descriptor.prompt_metadata.checksum,
        )
        prompt = await self.runtime.prompts.get(context, pin.id, pin.version)
        if prompt.pin != pin or prompt.id not in descriptor.capabilities:
            raise AgentRuntimeError(AgentErrorCode.SCHEMA_MISMATCH)
        if not set(task.tools).issubset(
            set(prompt.allowed_tools) & set(descriptor.allowed_tool_ids)
        ):
            raise AgentRuntimeError(AgentErrorCode.TOOL_DENIED)
        task = task.model_copy(update={"prompt": pin})
        if task.context_package_id:
            await self.runtime.contexts.get(context, project, task.context_package_id)
        for ref in task.content_refs:
            await self.runtime.content.read_snapshot(context, project, ref)
        data = canonical(task.model_dump(mode="json"))
        ref = await self.runtime.content.put_snapshot(
            context, project, data, media_type="application/json"
        )
        now = self.runtime.clock.now()
        job = AgentJob(
            id=uuid4(),
            workspace_id=context.workspace_id,
            project_id=project,
            actor_id=context.actor_id,
            input_ref=ref,
            created_at=now,
            updated_at=now,
        )
        return await self.store.create(job, task.operation_key, digest, context.as_task_headers())

    async def get(self, context: SecurityContext, project: UUID, identifier: UUID) -> AgentJob:
        await self.runtime.authorize(context, project)
        return await self.store.get(context.workspace_id, project, identifier)

    async def list(
        self, context: SecurityContext, project: UUID, cursor: str | None, limit: int
    ) -> AgentJobPage:
        await self.runtime.authorize(context, project)
        return await self.store.list(context.workspace_id, project, cursor, limit)

    async def run_next(self) -> bool:
        await self.store.recover(self.runtime.clock.now())
        claimed = await self.store.claim(self.runtime.clock.now())
        if not claimed:
            return False
        job, headers = claimed
        try:
            context = SecurityContext.from_task_headers(headers)
            await self.runtime.authorize(context, job.project_id, write=True)
            task = AgentTaskInput.model_validate_json(
                await self.runtime.content.read_snapshot(context, job.project_id, job.input_ref)
            )
            result = await self.supervisor.run(
                context,
                job.project_id,
                AgentInvocation(
                    task.agent_id,
                    {
                        "task": task.task,
                        "content_refs": [r.model_dump(mode="json") for r in task.content_refs],
                        "constraints": task.constraints,
                        "privacy": task.privacy,
                    },
                    f"agent-job-{job.id}",
                    f"agent-task://{job.id}",
                    AgentBudget(
                        task.max_steps, 0, 1, task.timeout_seconds, task.max_calls, task.max_tokens
                    ),
                    requested_tool_ids=task.tools,
                    task_run_id=job.id,
                    context_package_reference=f"memory-context://{task.context_package_id}"
                    if task.context_package_id
                    else None,
                    model_policy=task.policy,
                    prompt=task.prompt,
                ),
            )
            job = job.model_copy(
                update={
                    "status": "completed",
                    "agent_run_id": result.run.id,
                    "result_reference": result.run.result_reference,
                    "result_kind": result.run.result_kind.value if result.run.result_kind else None,
                }
            )
        except AgentRuntimeError as error:
            job = job.model_copy(update={"status": "failed", "error_code": error.code.value})
        except Exception:
            job = job.model_copy(
                update={"status": "failed", "error_code": "AGENT_EXECUTION_FAILED"}
            )
        await self.store.finish(job.model_copy(update={"updated_at": self.runtime.clock.now()}))
        return True
