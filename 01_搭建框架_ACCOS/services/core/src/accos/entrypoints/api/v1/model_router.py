"""Authorized model configuration, immutable prompts and durable call control."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import Field

from accos.composition import ApplicationContainer
from accos.entrypoints.api.v1.account_router import ExpectedAccountVersion
from accos.entrypoints.api.v1.dependencies import api_context, enforce_rate_limit, idempotency_key
from accos.kernel.errors import InvalidRequestError, PreconditionRequiredError, ScopeViolationError
from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import ContentRef, SharedContract
from accos.modules.agents.jobs import AgentJob, AgentJobPage, AgentTaskInput
from accos.modules.agents.domain import AgentRuntimeError
from accos.modules.models.budgets import Reservation
from accos.modules.models.invocation import (
    TERMINAL,
    CallPage,
    CallRecord,
    ModelInvocation,
    ModelMessage,
    TokenUsage,
)
from accos.modules.models.prompts import PromptVersion
from accos.modules.models.registry import BudgetSettings, BudgetView, ModelPolicyV2, ProviderProfile
from accos.modules.models.runtime import ModelRuntime

router = APIRouter(prefix="/api/v1", tags=["models-v2"], dependencies=[Depends(enforce_rate_limit)])
Context = Annotated[SecurityContext, Depends(api_context)]
Key = Annotated[str, Depends(idempotency_key)]


def container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


def runtime(request: Request) -> ModelRuntime:
    return container(request).models.runtime


Runtime = Annotated[ModelRuntime, Depends(runtime)]


def workspace_scope(context: SecurityContext, workspace_id: UUID) -> None:
    if context.workspace_id != workspace_id:
        raise ScopeViolationError


class ProfilePage(SharedContract):
    items: tuple[ProviderProfile, ...]
    next_cursor: str | None = None


class PolicyPage(SharedContract):
    items: tuple[ModelPolicyV2, ...]
    next_cursor: str | None = None


class PromptPage(SharedContract):
    items: tuple[PromptVersion, ...]
    next_cursor: str | None = None


def page_values(values: Any, after: str | None, limit: int) -> tuple[Any, str | None]:
    items = sorted(values, key=lambda value: f"{value.id}@{value.version}")
    items = [v for v in items if after is None or f"{v.id}@{v.version}" > after]
    page = items[:limit]
    return tuple(page), f"{page[-1].id}@{page[-1].version}" if len(items) > limit else None


@router.get("/workspaces/{workspace_id}/model-profiles", response_model=ProfilePage)
async def list_profiles(
    workspace_id: UUID,
    context: Context,
    service: Runtime,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> ProfilePage:
    workspace_scope(context, workspace_id)
    await service.configuration_access(context)
    items, next_cursor = page_values(await service.store.profiles(workspace_id), cursor, limit)
    return ProfilePage(items=items, next_cursor=next_cursor)


@router.post(
    "/workspaces/{workspace_id}/model-profiles", response_model=ProviderProfile, status_code=201
)
async def publish_profile(
    workspace_id: UUID,
    body: ProviderProfile,
    context: Context,
    service: Runtime,
    expected: ExpectedAccountVersion,
    key: Key,
) -> ProviderProfile:
    del key  # Immutable name/version plus If-Match is the operation identity.
    workspace_scope(context, workspace_id)
    await service.configuration_access(context, write=True)
    if body.locality == "local" and body.endpoint not in service.local_endpoints:
        raise InvalidRequestError(
            "Local endpoint must be added to the installation allowlist first."
        )
    if body.secret_ref and body.secret_ref not in {
        v.secret_ref for v in await service.accounts.store.secrets(workspace_id) if v.active
    }:
        raise InvalidRequestError("Credential reference is unavailable in this workspace.")
    return await service.store.save_profile(context, body, expected)


@router.get("/workspaces/{workspace_id}/model-policies", response_model=PolicyPage)
async def list_policies(
    workspace_id: UUID,
    context: Context,
    service: Runtime,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PolicyPage:
    workspace_scope(context, workspace_id)
    await service.configuration_access(context)
    items, next_cursor = page_values(await service.store.policies(workspace_id), cursor, limit)
    return PolicyPage(items=items, next_cursor=next_cursor)


@router.post(
    "/workspaces/{workspace_id}/model-policies", response_model=ModelPolicyV2, status_code=201
)
async def publish_policy(
    workspace_id: UUID,
    body: ModelPolicyV2,
    context: Context,
    service: Runtime,
    expected: ExpectedAccountVersion,
    key: Key,
) -> ModelPolicyV2:
    del key
    workspace_scope(context, workspace_id)
    await service.configuration_access(context, write=True)
    return await service.store.save_policy(context, body, expected)


@router.get("/workspaces/{workspace_id}/budgets", response_model=BudgetView)
async def get_budget(workspace_id: UUID, context: Context, service: Runtime) -> BudgetView:
    workspace_scope(context, workspace_id)
    await service.configuration_access(context)
    return await service.store.budget_view(workspace_id, service.clock.now())


@router.put("/workspaces/{workspace_id}/budgets", response_model=BudgetSettings)
async def save_budget(
    workspace_id: UUID,
    body: BudgetSettings,
    context: Context,
    service: Runtime,
    expected: ExpectedAccountVersion,
    key: Key,
) -> BudgetSettings:
    del key
    workspace_scope(context, workspace_id)
    await service.configuration_access(context, write=True)
    if body.version != expected:
        raise InvalidRequestError("Budget body and If-Match version must agree.")
    return await service.store.save_budget(context, body, expected)


@router.get("/workspaces/{workspace_id}/prompt-templates", response_model=PromptPage)
async def list_prompts(
    workspace_id: UUID,
    context: Context,
    service: Runtime,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PromptPage:
    workspace_scope(context, workspace_id)
    await service.configuration_access(context)
    items, next_cursor = page_values(await service.prompts.list(context), cursor, limit)
    return PromptPage(items=items, next_cursor=next_cursor)


@router.post(
    "/workspaces/{workspace_id}/prompt-templates", response_model=PromptVersion, status_code=201
)
async def publish_prompt(
    workspace_id: UUID,
    body: PromptVersion,
    context: Context,
    service: Runtime,
    key: Key,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> PromptVersion:
    del key
    workspace_scope(context, workspace_id)
    await service.configuration_access(context, write=True)
    if if_match is None:
        raise PreconditionRequiredError
    if not if_match.startswith('"') or not if_match.endswith('"'):
        raise InvalidRequestError("Expected a quoted prompt version.")
    expected = if_match[1:-1]
    return await service.prompts.publish(context, body, None if expected == "0" else expected)


class PromptPreviewInput(SharedContract):
    prompt: PromptVersion
    task_kind: str
    variables: dict[str, Any]


@router.post("/workspaces/{workspace_id}/prompt-preview", response_model=tuple[ModelMessage, ...])
async def preview_prompt(
    workspace_id: UUID, body: PromptPreviewInput, context: Context, service: Runtime
) -> tuple[ModelMessage, ...]:
    workspace_scope(context, workspace_id)
    await service.configuration_access(context)
    return body.prompt.checked().render(body.variables, body.task_kind)


class AcceptedCall(SharedContract):
    operation_id: UUID
    run_id: UUID
    status_url: str
    events_url: str
    call: CallRecord


@router.post("/projects/{project_id}/model-calls", response_model=AcceptedCall, status_code=202)
async def create_call(
    project_id: UUID,
    body: ModelInvocation,
    context: Context,
    service: Runtime,
    key: Key,
    response: Response,
) -> AcceptedCall:
    if key != body.operation_key:
        raise InvalidRequestError("Idempotency-Key must match operation_key.")
    call = await service.submit(context, project_id, body)
    url = f"/api/v1/projects/{project_id}/model-calls/{call.id}"
    response.headers["Location"] = url
    return AcceptedCall(
        operation_id=call.id, run_id=call.id, status_url=url, events_url=url + "/events", call=call
    )


@router.get("/projects/{project_id}/model-calls", response_model=CallPage)
async def list_calls(
    project_id: UUID,
    context: Context,
    service: Runtime,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CallPage:
    await service.authorize(context, project_id)
    return await service.store.calls(context.workspace_id, project_id, cursor, limit)


@router.get("/projects/{project_id}/model-calls/{call_id}", response_model=CallRecord)
async def get_call(
    project_id: UUID, call_id: UUID, context: Context, service: Runtime
) -> CallRecord:
    return await service.get(context, project_id, call_id)


class CallContent(SharedContract):
    content_ref: ContentRef
    text: str
    partial: bool


@router.get("/projects/{project_id}/model-calls/{call_id}/content", response_model=CallContent)
async def get_content(
    project_id: UUID,
    call_id: UUID,
    context: Context,
    service: Runtime,
    response: Response,
    kind: Literal["input", "output", "partial"] = "output",
) -> CallContent:
    call = await service.get(context, project_id, call_id)
    ref = (
        call.input_ref
        if kind == "input"
        else call.partial_ref
        if kind == "partial"
        else call.output_ref
    )
    if ref is None:
        raise InvalidRequestError("Requested content is not available.")
    response.headers["Cache-Control"] = "private, no-store"
    return CallContent(
        content_ref=ref,
        text=(await service.content.read_snapshot(context, project_id, ref)).decode("utf-8"),
        partial=kind == "partial",
    )


@router.post("/projects/{project_id}/model-calls/{call_id}/cancel", response_model=CallRecord)
async def cancel_call(
    project_id: UUID, call_id: UUID, context: Context, service: Runtime, key: Key
) -> CallRecord:
    del key
    await service.authorize(context, project_id, write=True)
    return await service.store.cancel(
        context.workspace_id, project_id, call_id, service.clock.now()
    )


@router.get("/projects/{project_id}/model-calls/{call_id}/events")
async def stream_events(
    project_id: UUID,
    call_id: UUID,
    context: Context,
    service: Runtime,
    request: Request,
    after: Annotated[int, Query(ge=0)] = 0,
    last_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    await service.get(context, project_id, call_id)
    if last_id:
        try:
            after = max(after, int(last_id))
        except ValueError:
            raise InvalidRequestError("Invalid model event cursor.") from None

    async def events() -> AsyncIterator[str]:
        cursor = after
        for _ in range(120):
            if await request.is_disconnected():
                return
            call = await service.get(context, project_id, call_id)
            values = await service.store.events(
                context.workspace_id, project_id, call_id, cursor, 100
            )
            for event in values:
                cursor = event.sequence
                yield f"id: {event.sequence}\nevent: model_call\ndata: {event.model_dump_json()}\n\n"
            if call.status in TERMINAL and cursor >= call.sequence:
                return
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/projects/{project_id}/model-calls/{call_id}/attempts", response_model=tuple[Reservation, ...]
)
async def list_attempts(
    project_id: UUID, call_id: UUID, context: Context, service: Runtime
) -> tuple[Reservation, ...]:
    await service.get(context, project_id, call_id)
    return await service.ledger.reservations(context.workspace_id, call_id)


class ModelReconcileInput(SharedContract):
    usage: TokenUsage
    cost_micro_usd: Annotated[int, Field(ge=0, le=10**12)]
    evidence_ref: ContentRef


@router.post(
    "/projects/{project_id}/model-calls/{call_id}/attempts/{reservation_id}/reconcile",
    response_model=Reservation,
)
async def reconcile(
    project_id: UUID,
    call_id: UUID,
    reservation_id: UUID,
    body: ModelReconcileInput,
    context: Context,
    service: Runtime,
    key: Key,
) -> Reservation:
    del key
    await service.configuration_access(context, write=True)
    await service.get(context, project_id, call_id)
    if reservation_id not in {
        r.id for r in await service.ledger.reservations(context.workspace_id, call_id)
    }:
        raise ScopeViolationError
    await service.content.read_snapshot(context, project_id, body.evidence_ref)
    return await service.ledger.reconcile(
        context.workspace_id,
        reservation_id,
        body.usage,
        body.cost_micro_usd,
        body.evidence_ref,
        context.actor_id,
    )


@router.post("/projects/{project_id}/agent-tasks", response_model=AgentJob, status_code=202)
async def submit_agent_task(
    project_id: UUID,
    body: AgentTaskInput,
    context: Context,
    request: Request,
    response: Response,
    key: Key,
) -> AgentJob:
    if key != body.operation_key:
        raise InvalidRequestError("Idempotency-Key must match operation_key.")
    try:
        job = await container(request).agents.jobs.submit(context, project_id, body)
    except AgentRuntimeError as error:
        raise InvalidRequestError(error.code.value) from None
    response.headers["Location"] = f"/api/v1/projects/{project_id}/agent-tasks/{job.id}"
    return job


@router.get("/projects/{project_id}/agent-tasks/{job_id}", response_model=AgentJob)
async def get_agent_task(
    project_id: UUID, job_id: UUID, context: Context, request: Request
) -> AgentJob:
    return await container(request).agents.jobs.get(context, project_id, job_id)


@router.get("/projects/{project_id}/agent-tasks", response_model=AgentJobPage)
async def list_agent_tasks(
    project_id: UUID,
    context: Context,
    request: Request,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AgentJobPage:
    return await container(request).agents.jobs.list(context, project_id, cursor, limit)


@router.get("/projects/{project_id}/agent-tasks/{job_id}/content", response_model=CallContent)
async def agent_task_content(
    project_id: UUID,
    job_id: UUID,
    context: Context,
    request: Request,
    response: Response,
    kind: Literal["input", "output"] = "output",
) -> CallContent:
    app = container(request)
    job = await app.agents.jobs.get(context, project_id, job_id)
    ref = job.input_ref
    if kind == "output":
        if not job.result_reference or not job.result_reference.startswith("content://"):
            raise InvalidRequestError("No finalized agent result is available.")
        asset, version_id = job.result_reference.removeprefix("content://").split("/")
        version = await app.assets.service.version(
            context, project_id, UUID(asset), UUID(version_id)
        )
        ref = ContentRef(
            asset_id=UUID(asset),
            asset_version_id=version.id,
            sha256=version.content_hash,
            media_type=version.media_type,
            byte_length=version.size_bytes,
        )
    response.headers["Cache-Control"] = "private, no-store"
    return CallContent(
        content_ref=ref,
        text=(await app.models.runtime.content.read_snapshot(context, project_id, ref)).decode(
            "utf-8"
        ),
        partial=False,
    )
