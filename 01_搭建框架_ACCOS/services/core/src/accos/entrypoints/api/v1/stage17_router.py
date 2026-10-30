"""Execution-17 intelligent resource routes and resumable SSE projection."""

# ruff: noqa: PLR0913, PLR0917, TC001, TC003

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.responses import StreamingResponse

from accos.composition import ApplicationContainer
from accos.entrypoints.api.v1.dependencies import (
    api_context,
    application_container,
    etag,
    idempotency_key,
    if_match_version,
)
from accos.entrypoints.api.v1.stage17_schemas import (
    AgentBudgetResponse,
    AgentCollectionResponse,
    AgentDescriptorResponse,
    AgentRunCreateRequest,
    AgentRunResponse,
    ApprovalDecisionRequest,
    ApprovalResponse,
    AsyncRunReference,
    BehaviorConsentGrantRequest,
    BehaviorConsentResponse,
    BehaviorConsentStatusResponse,
    BehaviorConsentWithdrawalResponse,
    CanonChangeAssertionRequest,
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
    ContextItemResponse,
    ContextPackageCreateRequest,
    ContextPackageResponse,
    CreativeContainerResponse,
    CreativeCreateRequest,
    CreativeDecisionRequest,
    DiagnosticCollectionResponse,
    DiagnosticResponse,
    DraftCreateRequest,
    DraftResponse,
    EvaluationCreateRequest,
    EvaluationExecuteRequest,
    EvaluationRunResponse,
    ExperimentCreateRequest,
    ExperimentFinishRequest,
    ExperimentResponse,
    ExperimentSampleCreateRequest,
    ExperimentSampleResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
    FindingResponse,
    ImprovementDecisionRequest,
    ImprovementPlanRequest,
    ImprovementProposalResponse,
    IngestionAcceptedResponse,
    IngestionCreateRequest,
    IngestionRunResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    MemoryConflictDecisionRequest,
    MemoryConflictResponse,
    MemoryResponse,
    MemoryRevisionRequest,
    MemoryWriteRequest,
    MetricDefinitionCreateRequest,
    MetricDefinitionResponse,
    MetricPointResponse,
    MetricRecordRequest,
    ModelProviderStatusResponse,
    ModelStatusResponse,
    QualityResultResponse,
    ReferenceAssertionRequest,
    RequiredFieldAssertionRequest,
    ResolutionCreateRequest,
    ResolutionDecisionRequest,
    ResolutionResponse,
    RetrievalCitationResponse,
    RetrievalHitResponse,
    RubricCreateRequest,
    RubricResponse,
    ScoreDimensionResponse,
    SseEventData,
    StepRunCollectionResponse,
    StepRunResponse,
    TaskRunCollectionResponse,
    TaskRunResponse,
    ToolStatusItem,
    ToolStatusResponse,
    VariantResponse,
    VersionAssertionRequest,
    WorkCreateRequest,
    WorkflowDefinitionCollectionResponse,
    WorkflowDefinitionResponse,
    WorkflowRunCreateRequest,
    WorkflowRunResponse,
)
from accos.kernel.errors import (
    EventCursorExpiredError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from accos.kernel.observability import TelemetryRuntime
from accos.kernel.security import SecurityContext
from accos.modules.agents.definitions import agent_plan_review_definition
from accos.modules.agents.domain import AgentBudget
from accos.modules.consistency.domain import (
    CanonChangeAssertion,
    ConsistencyCheckRun,
    FactTarget,
    Finding,
    ReferenceAssertion,
    RequiredFieldAssertion,
    ValidationBundle,
    VersionAssertion,
)
from accos.modules.consistency.public import (
    DecideResolutionCommand,
    ProposeResolutionCommand,
    RunCheckCommand,
)
from accos.modules.consistency.workflow import canon_quality_definition
from accos.modules.creative.character import CreateCharacterCommand, GetCharacterQuery
from accos.modules.creative.novel import (
    CreateWorkCommand,
    DecideNovelRecordCommand,
    DraftRevision,
    GetNovelRecordQuery,
    GetWorkQuery,
    ProposeNovelRecordCommand,
)
from accos.modules.creative.workflow import creative_reference_definition
from accos.modules.creative.world import CreateWorldCommand, GetWorldQuery
from accos.modules.feedback.application import (
    CaptureFeedbackCommand,
    CreateExperimentCommand,
    FinishExperimentCommand,
    RecordMetricCommand,
    RegisterMetricCommand,
    VariantDraft,
)
from accos.modules.feedback.domain import Experiment, ExperimentStatus, MetricDimension, Variant
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.knowledge.definitions import knowledge_ingestion_definition
from accos.modules.knowledge.domain import RetrievalFilter, RetrievalRequest
from accos.modules.memory.application import ContextRequest, MemoryDraft
from accos.modules.memory.domain import (
    ContextPackage,
    MemoryProvenance,
    MemoryScope,
    RetentionRule,
)
from accos.modules.models.domain import MODEL_PROTOCOL_VERSION
from accos.modules.quality.application import CreateRubricCommand, StartEvaluationCommand
from accos.modules.quality.domain import EvaluationEvidence, QualityResult
from accos.modules.tools.domain import TOOL_PROTOCOL_VERSION
from accos.modules.workflows.definitions import framework_smoke_definition
from accos.modules.workflows.domain import WorkflowRunEvent
from accos.modules.workflows.public import WorkflowDefinition, WorkflowRun, WorkflowService

router = APIRouter()

_LOCATION_HEADER = {
    "description": "Canonical URL for the accepted run resource.",
    "schema": {"type": "string"},
}
_LINK_HEADER = {
    "description": "Typed task and SSE monitor links for the accepted run.",
    "schema": {"type": "string"},
}
_RUN_ACCEPTED_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_202_ACCEPTED: {
        "description": "Accepted",
        "headers": {"Location": _LOCATION_HEADER, "Link": _LINK_HEADER},
    }
}
_RETRY_ACCEPTED_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_202_ACCEPTED: {
        "description": "Retry accepted",
        "headers": {"Location": _LOCATION_HEADER},
    }
}

Context = Annotated[SecurityContext, Depends(api_context)]
Container = Annotated[ApplicationContainer, Depends(application_container)]
Idempotency = Annotated[str, Depends(idempotency_key)]
ExpectedVersion = Annotated[int, Depends(if_match_version)]


def _definitions() -> dict[str, WorkflowDefinition]:
    definitions = (
        framework_smoke_definition(),
        agent_plan_review_definition(),
        knowledge_ingestion_definition(),
        creative_reference_definition(),
        canon_quality_definition(),
    )
    return {definition.name: definition for definition in definitions}


async def _authorize_workspace_read(
    context: SecurityContext, container: ApplicationContainer
) -> None:
    await container.identity.authorizer.authorize(
        AuthorizationRequest(
            context,
            Permission.WORKSPACE_READ,
            ResourceScope(context.workspace_id, "workspace", str(context.workspace_id)),
        )
    )


@router.get(
    "/workflows",
    response_model=WorkflowDefinitionCollectionResponse,
    operation_id="listWorkflowDefinitions",
)
async def list_workflow_definitions(
    context: Context, container: Container
) -> WorkflowDefinitionCollectionResponse:
    await _authorize_workspace_read(context, container)
    return WorkflowDefinitionCollectionResponse(
        items=[
            WorkflowDefinitionResponse(
                name=item.name,
                version=item.version,
                step_keys=[step.key for step in item.steps],
            )
            for item in _definitions().values()
        ]
    )


@router.post(
    "/projects/{project_id}/workflows/{workflow_name}/runs",
    response_model=AsyncRunReference,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_RUN_ACCEPTED_RESPONSES,
    operation_id="createWorkflowRun",
)
async def create_workflow_run(
    project_id: UUID,
    workflow_name: str,
    body: WorkflowRunCreateRequest,
    response: Response,
    context: Context,
    container: Container,
    key: Idempotency,
) -> AsyncRunReference:
    definition = _definitions().get(workflow_name)
    if definition is None:
        raise ResourceNotFoundError
    run = await container.workflows.service.submit(
        context,
        project_id,
        definition,
        idempotency_key=key,
        input_reference=body.input_reference,
    )
    status_url = f"/api/v1/workflow-runs/{run.id}"
    task_url = f"{status_url}/tasks"
    events_url = f"/api/v1/events?run_id={run.id}"
    response.headers["Location"] = status_url
    response.headers["Link"] = f'<{task_url}>; rel="tasks", <{events_url}>; rel="monitor"'
    return AsyncRunReference(
        run_id=run.id,
        task_url=task_url,
        status_url=status_url,
        events_url=events_url,
        accepted_at=run.created_at,
    )


@router.get(
    "/workflow-runs/{run_id}",
    response_model=WorkflowRunResponse,
    operation_id="getWorkflowRun",
)
async def get_workflow_run(
    run_id: UUID, response: Response, context: Context, container: Container
) -> WorkflowRunResponse:
    run = await container.workflows.service.get(context, run_id)
    response.headers["ETag"] = etag(run.version)
    return WorkflowRunResponse.model_validate(run)


@router.get(
    "/workflow-runs/{run_id}/steps",
    response_model=StepRunCollectionResponse,
    operation_id="listWorkflowSteps",
)
async def list_workflow_steps(
    run_id: UUID, context: Context, container: Container
) -> StepRunCollectionResponse:
    items = await container.workflows.service.get_steps(context, run_id)
    return StepRunCollectionResponse(items=[StepRunResponse.model_validate(item) for item in items])


@router.get(
    "/workflow-runs/{run_id}/tasks",
    response_model=TaskRunCollectionResponse,
    operation_id="listWorkflowTasks",
)
async def list_workflow_tasks(
    run_id: UUID, context: Context, container: Container
) -> TaskRunCollectionResponse:
    items = await container.workflows.service.get_tasks(context, run_id)
    return TaskRunCollectionResponse(items=[TaskRunResponse.model_validate(item) for item in items])


@router.post(
    "/workflow-runs/{run_id}/pause",
    response_model=WorkflowRunResponse,
    operation_id="pauseWorkflowRun",
)
async def pause_workflow_run(
    run_id: UUID, response: Response, context: Context, container: Container
) -> WorkflowRunResponse:
    run = await container.workflows.service.pause(context, run_id)
    response.headers["ETag"] = etag(run.version)
    return WorkflowRunResponse.model_validate(run)


@router.post(
    "/workflow-runs/{run_id}/resume",
    response_model=WorkflowRunResponse,
    operation_id="resumeWorkflowRun",
)
async def resume_workflow_run(
    run_id: UUID, response: Response, context: Context, container: Container
) -> WorkflowRunResponse:
    run = await container.workflows.service.resume(context, run_id)
    response.headers["ETag"] = etag(run.version)
    return WorkflowRunResponse.model_validate(run)


@router.post(
    "/workflow-runs/{run_id}/cancel",
    response_model=WorkflowRunResponse,
    operation_id="cancelWorkflowRun",
)
async def cancel_workflow_run(
    run_id: UUID, response: Response, context: Context, container: Container
) -> WorkflowRunResponse:
    run = await container.workflows.service.cancel(context, run_id)
    response.headers["ETag"] = etag(run.version)
    return WorkflowRunResponse.model_validate(run)


@router.get(
    "/workflow-runs/{run_id}/approval",
    response_model=ApprovalResponse,
    operation_id="getWorkflowApproval",
)
async def get_workflow_approval(
    run_id: UUID, context: Context, container: Container
) -> ApprovalResponse:
    approval = await container.workflows.service.get_approval(context, run_id)
    return ApprovalResponse.model_validate(approval).model_copy(
        update={"can_decide": await container.workflows.service.can_decide(context, approval)}
    )


@router.post(
    "/workflow-runs/{run_id}/approval/decision",
    response_model=WorkflowRunResponse,
    operation_id="decideWorkflowApproval",
)
async def decide_workflow_approval(
    run_id: UUID,
    body: ApprovalDecisionRequest,
    response: Response,
    context: Context,
    container: Container,
) -> WorkflowRunResponse:
    run = await container.workflows.service.decide_approval(
        context, run_id, body.decision, reason=body.reason
    )
    response.headers["ETag"] = etag(run.version)
    return WorkflowRunResponse.model_validate(run)


@router.get("/agents", response_model=AgentCollectionResponse, operation_id="listAgents")
async def list_agents(context: Context, container: Container) -> AgentCollectionResponse:
    await _authorize_workspace_read(context, container)
    return AgentCollectionResponse(
        items=[
            AgentDescriptorResponse(
                agent_id=item.agent_id,
                version=item.version,
                capabilities=list(item.capabilities),
                allowed_tool_ids=list(item.allowed_tool_ids),
                model_policy_id=item.model_policy_id,
                model_policy_version=item.model_policy_version,
                budget_limit=AgentBudgetResponse.model_validate(item.budget_limit),
            )
            for item in container.agents.registry.all()
        ]
    )


@router.post(
    "/projects/{project_id}/agents/director/runs",
    response_model=AsyncRunReference,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_RUN_ACCEPTED_RESPONSES,
    operation_id="createDirectorAgentRun",
)
async def create_director_agent_run(
    project_id: UUID,
    body: AgentRunCreateRequest,
    response: Response,
    context: Context,
    container: Container,
    key: Idempotency,
) -> AsyncRunReference:
    result = await container.agents.master.submit_goal(
        context,
        project_id,
        idempotency_key=key,
        goal_reference=body.goal_reference,
        budget=AgentBudget(body.max_steps, 1, 1, 30.0, body.max_calls, body.max_tokens),
    )
    run = result.workflow_run
    status_url = f"/api/v1/agent-runs/{result.agent_run.id}"
    task_url = f"/api/v1/workflow-runs/{run.id}/tasks"
    events_url = f"/api/v1/events?run_id={run.id}"
    response.headers["Location"] = status_url
    response.headers["Link"] = f'<{task_url}>; rel="tasks", <{events_url}>; rel="monitor"'
    return AsyncRunReference(
        run_id=result.agent_run.id,
        task_url=task_url,
        status_url=status_url,
        events_url=events_url,
        accepted_at=result.agent_run.created_at,
    )


@router.get("/agent-runs/{run_id}", response_model=AgentRunResponse, operation_id="getAgentRun")
async def get_agent_run(run_id: UUID, context: Context, container: Container) -> AgentRunResponse:
    return AgentRunResponse.model_validate(await container.agents.supervisor.get(context, run_id))


@router.get("/models/status", response_model=ModelStatusResponse, operation_id="getModelStatus")
async def get_model_status(context: Context, container: Container) -> ModelStatusResponse:
    await _authorize_workspace_read(context, container)
    capabilities = container.models.registry.capabilities()
    return ModelStatusResponse(
        protocol_version=MODEL_PROTOCOL_VERSION,
        providers=[
            ModelProviderStatusResponse(
                provider_id=item.provider_id,
                state=item.state,
                capabilities=sorted(capabilities.get(item.provider_id, frozenset())),
                consecutive_failures=item.consecutive_failures,
                in_flight=item.in_flight,
                circuit_open_until=item.circuit_open_until,
            )
            for item in container.models.gateway.health()
        ],
    )


@router.get("/tools/status", response_model=ToolStatusResponse, operation_id="getToolStatus")
async def get_tool_status(context: Context, container: Container) -> ToolStatusResponse:
    await _authorize_workspace_read(context, container)
    return ToolStatusResponse(
        protocol_version=TOOL_PROTOCOL_VERSION,
        tools=[
            ToolStatusItem(
                tool_id=item.tool_id,
                version=item.version,
                capabilities=list(item.capabilities),
                idempotent=item.idempotent,
            )
            for item in container.tools.registry.tools
        ],
    )


@router.post(
    "/projects/{project_id}/knowledge/ingestion-runs",
    response_model=IngestionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_RUN_ACCEPTED_RESPONSES,
    operation_id="createKnowledgeIngestionRun",
)
async def create_knowledge_ingestion_run(
    project_id: UUID,
    body: IngestionCreateRequest,
    response: Response,
    context: Context,
    container: Container,
    key: Idempotency,
) -> IngestionAcceptedResponse:
    ingestion = await container.knowledge.service.submit(
        context,
        project_id,
        body.asset_id,
        idempotency_key=key,
        verification_policy=body.verification_policy,
    )
    workflow = await container.workflows.service.submit(
        context,
        project_id,
        knowledge_ingestion_definition(),
        idempotency_key=key,
        input_reference=f"knowledge-run://{ingestion.id}",
    )
    status_url = f"/api/v1/knowledge/ingestion-runs/{ingestion.id}"
    task_url = f"/api/v1/workflow-runs/{workflow.id}/tasks"
    events_url = f"/api/v1/events?run_id={workflow.id}"
    response.headers["Location"] = status_url
    response.headers["Link"] = f'<{task_url}>; rel="tasks", <{events_url}>; rel="monitor"'
    return IngestionAcceptedResponse(
        ingestion_run_id=ingestion.id,
        workflow_run_id=workflow.id,
        status_url=status_url,
        task_url=task_url,
        events_url=events_url,
        accepted_at=workflow.created_at,
    )


@router.get(
    "/knowledge/ingestion-runs/{run_id}",
    response_model=IngestionRunResponse,
    operation_id="getKnowledgeIngestionRun",
)
async def get_knowledge_ingestion_run(
    run_id: UUID, context: Context, container: Container
) -> IngestionRunResponse:
    return IngestionRunResponse.model_validate(
        await container.knowledge.service.get(context, run_id)
    )


@router.post(
    "/knowledge/ingestion-runs/{run_id}/retry",
    response_model=IngestionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_RETRY_ACCEPTED_RESPONSES,
    operation_id="retryKnowledgeIngestionRun",
)
async def retry_knowledge_ingestion_run(
    run_id: UUID, response: Response, context: Context, container: Container
) -> IngestionRunResponse:
    run = await container.knowledge.service.retry(context, run_id)
    response.headers["Location"] = f"/api/v1/knowledge/ingestion-runs/{run.id}"
    return IngestionRunResponse.model_validate(run)


@router.get(
    "/projects/{project_id}/knowledge/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
    operation_id="getKnowledgeDocument",
)
async def get_knowledge_document(
    project_id: UUID, document_id: UUID, context: Context, container: Container
) -> KnowledgeDocumentResponse:
    document = await container.knowledge.service.get_document(context, project_id, document_id)
    return KnowledgeDocumentResponse.model_validate(document)


@router.post(
    "/projects/{project_id}/knowledge/search",
    response_model=KnowledgeSearchResponse,
    operation_id="searchKnowledge",
)
async def search_knowledge(
    project_id: UUID,
    body: KnowledgeSearchRequest,
    context: Context,
    container: Container,
) -> KnowledgeSearchResponse:
    result = await container.knowledge.service.retrieve(
        context,
        project_id,
        RetrievalRequest(
            body.query,
            body.top_k,
            RetrievalFilter(
                tuple(body.source_ids),
                tuple(body.document_version_ids),
                tuple(body.verification_statuses),
            ),
        ),
    )
    return KnowledgeSearchResponse(
        query=result.query,
        hits=[
            RetrievalHitResponse(
                score=item.score,
                content=item.chunk.content,
                citation=RetrievalCitationResponse.model_validate(item.citation),
            )
            for item in result.hits
        ],
    )


@router.post(
    "/projects/{project_id}/memories",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMemory",
)
async def create_memory(
    project_id: UUID,
    body: MemoryWriteRequest,
    response: Response,
    context: Context,
    container: Container,
) -> MemoryResponse:
    record = await container.memory.service.write(
        context,
        MemoryDraft(
            scope=MemoryScope(body.scope),
            memory_type=body.memory_type,
            content=body.content,
            project_id=project_id,
            valid_from=body.valid_from,
            valid_until=body.valid_until,
            observed_at=body.observed_at,
            importance=body.importance,
            confidence=body.confidence,
            provenance=MemoryProvenance(body.provenance_kind, body.provenance_reference),
            retention=RetentionRule(
                body.retention_kind, body.ttl_seconds, body.decay_half_life_seconds
            ),
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/memories/{record.id}"
    return MemoryResponse.model_validate(record)


@router.get(
    "/projects/{project_id}/memories/{memory_id}",
    response_model=MemoryResponse,
    operation_id="getMemory",
)
async def get_memory(
    project_id: UUID, memory_id: UUID, context: Context, container: Container
) -> MemoryResponse:
    record = await container.memory.service.get(context, memory_id)
    if record.project_id != project_id:
        raise ResourceNotFoundError
    return MemoryResponse.model_validate(record)


@router.post(
    "/projects/{project_id}/memories/{memory_id}/revisions",
    response_model=MemoryConflictResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="proposeMemoryRevision",
)
async def propose_memory_revision(
    project_id: UUID,
    memory_id: UUID,
    body: MemoryRevisionRequest,
    response: Response,
    context: Context,
    container: Container,
) -> MemoryConflictResponse:
    current = await container.memory.service.get(context, memory_id)
    if current.project_id != project_id:
        raise ResourceNotFoundError
    conflict = await container.memory.service.propose_revision(context, memory_id, body.content)
    response.headers["Location"] = f"/api/v1/memory-conflicts/{conflict.id}"
    return MemoryConflictResponse.model_validate(conflict)


@router.get(
    "/memory-conflicts/{conflict_id}",
    response_model=MemoryConflictResponse,
    operation_id="getMemoryConflict",
)
async def get_memory_conflict(
    conflict_id: UUID, context: Context, container: Container
) -> MemoryConflictResponse:
    return MemoryConflictResponse.model_validate(
        await container.memory.service.get_conflict(context, conflict_id)
    )


@router.post(
    "/memory-conflicts/{conflict_id}/decision",
    response_model=MemoryConflictResponse,
    operation_id="decideMemoryConflict",
)
async def decide_memory_conflict(
    conflict_id: UUID,
    body: MemoryConflictDecisionRequest,
    context: Context,
    container: Container,
) -> MemoryConflictResponse:
    conflict = await container.memory.service.decide_conflict(
        context, conflict_id, accept_candidate=body.accept_candidate
    )
    return MemoryConflictResponse.model_validate(conflict)


@router.post(
    "/projects/{project_id}/context-packages",
    response_model=ContextPackageResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createContextPackage",
)
async def create_context_package(
    project_id: UUID,
    body: ContextPackageCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ContextPackageResponse:
    package = await container.memory.context_builder.build(
        context,
        ContextRequest(
            body.task_reference,
            project_id,
            body.budget_chars,
            frozenset(body.scopes),
            frozenset(body.memory_types),
            body.budget_tokens,
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/context-packages/{package.id}"
    return _context_package_response(package)


@router.get(
    "/projects/{project_id}/context-packages/{package_id}",
    response_model=ContextPackageResponse,
    operation_id="getContextPackage",
)
async def get_context_package(
    project_id: UUID, package_id: UUID, context: Context, container: Container
) -> ContextPackageResponse:
    package = await container.memory.context_builder.get(context, project_id, package_id)
    return _context_package_response(package)


def _context_package_response(package: ContextPackage) -> ContextPackageResponse:
    raw = ContextPackageResponse.model_validate(package)
    return raw.model_copy(
        update={"items": [ContextItemResponse.model_validate(item) for item in package.items]}
    )


@router.post(
    "/projects/{project_id}/creative/worlds",
    response_model=CreativeContainerResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createWorld",
)
async def create_world(
    project_id: UUID,
    body: CreativeCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> CreativeContainerResponse:
    item = await container.creative.world.create(
        context, CreateWorldCommand(project_id, body.label)
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/creative/worlds/{item.id}"
    return CreativeContainerResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/creative/worlds/{world_id}",
    response_model=CreativeContainerResponse,
    operation_id="getWorld",
)
async def get_world(
    project_id: UUID, world_id: UUID, context: Context, container: Container
) -> CreativeContainerResponse:
    return CreativeContainerResponse.model_validate(
        await container.creative.world.get(context, GetWorldQuery(project_id, world_id))
    )


@router.post(
    "/projects/{project_id}/creative/characters",
    response_model=CreativeContainerResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createCharacter",
)
async def create_character(
    project_id: UUID,
    body: CreativeCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> CreativeContainerResponse:
    item = await container.creative.character.create(
        context, CreateCharacterCommand(project_id, body.label)
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/creative/characters/{item.id}"
    return CreativeContainerResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/creative/characters/{character_id}",
    response_model=CreativeContainerResponse,
    operation_id="getCharacter",
)
async def get_character(
    project_id: UUID, character_id: UUID, context: Context, container: Container
) -> CreativeContainerResponse:
    return CreativeContainerResponse.model_validate(
        await container.creative.character.get(context, GetCharacterQuery(project_id, character_id))
    )


@router.post(
    "/projects/{project_id}/creative/works",
    response_model=CreativeContainerResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createWork",
)
async def create_work(
    project_id: UUID,
    body: WorkCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> CreativeContainerResponse:
    item = await container.creative.novel.create(
        context,
        CreateWorkCommand(project_id, body.label, tuple(body.world_ids), tuple(body.character_ids)),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/creative/works/{item.id}"
    return CreativeContainerResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/creative/works/{work_id}",
    response_model=CreativeContainerResponse,
    operation_id="getWork",
)
async def get_work(
    project_id: UUID, work_id: UUID, context: Context, container: Container
) -> CreativeContainerResponse:
    return CreativeContainerResponse.model_validate(
        await container.creative.novel.get(context, GetWorkQuery(project_id, work_id))
    )


@router.post(
    "/projects/{project_id}/creative/works/{work_id}/drafts",
    response_model=DraftResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createDraft",
)
async def create_draft(
    project_id: UUID,
    work_id: UUID,
    body: DraftCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> DraftResponse:
    item, created = await container.creative.novel.propose(
        context,
        ProposeNovelRecordCommand(
            project_id,
            work_id,
            DraftRevision,
            body.logical_id,
            body.record_version,
            source_reference=body.source_reference,
            sequence=body.sequence,
        ),
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/projects/{project_id}/creative/drafts/{item.id}"
    return DraftResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/creative/drafts/{draft_id}",
    response_model=DraftResponse,
    operation_id="getDraft",
)
async def get_draft(
    project_id: UUID, draft_id: UUID, context: Context, container: Container
) -> DraftResponse:
    item = await container.creative.novel.get_record(
        context, GetNovelRecordQuery(project_id, draft_id)
    )
    if not isinstance(item, DraftRevision):
        raise ResourceNotFoundError
    return DraftResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/creative/drafts/{draft_id}/decision",
    response_model=DraftResponse,
    operation_id="decideDraft",
)
async def decide_draft(
    project_id: UUID,
    draft_id: UUID,
    body: CreativeDecisionRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> DraftResponse:
    item = await container.creative.novel.decide(
        context,
        DecideNovelRecordCommand(project_id, draft_id, body.decision, expected_version),
    )
    response.headers["ETag"] = etag(expected_version + 1)
    return DraftResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/consistency/checks",
    response_model=ConsistencyCheckResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createConsistencyCheck",
)
async def create_consistency_check(
    project_id: UUID,
    body: ConsistencyCheckRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ConsistencyCheckResponse:
    run, findings = await container.consistency.service.run_check(
        context,
        RunCheckCommand(
            project_id,
            ValidationBundle(
                required_fields=tuple(_required_field(item) for item in body.required_fields),
                references=tuple(_reference(item) for item in body.references),
                versions=tuple(_version(item) for item in body.versions),
                canon_changes=tuple(_canon_change(item) for item in body.canon_changes),
            ),
            workflow_run_id=body.workflow_run_id,
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/consistency/checks/{run.id}"
    return _consistency_response(run, findings)


@router.get(
    "/projects/{project_id}/consistency/checks/{run_id}",
    response_model=ConsistencyCheckResponse,
    operation_id="getConsistencyCheck",
)
async def get_consistency_check(
    project_id: UUID, run_id: UUID, context: Context, container: Container
) -> ConsistencyCheckResponse:
    run, findings = await container.consistency.service.get_check_with_findings(
        context, project_id, run_id
    )
    return _consistency_response(run, findings)


def _required_field(item: RequiredFieldAssertionRequest) -> RequiredFieldAssertion:
    return RequiredFieldAssertion(item.evidence_reference, item.field_code, item.present)


def _reference(item: ReferenceAssertionRequest) -> ReferenceAssertion:
    return ReferenceAssertion(item.evidence_reference, item.exists)


def _version(item: VersionAssertionRequest) -> VersionAssertion:
    return VersionAssertion(item.evidence_reference, item.expected_version, item.current_version)


def _canon_change(item: CanonChangeAssertionRequest) -> CanonChangeAssertion:
    return CanonChangeAssertion(
        item.canon_reference,
        item.level,
        item.modifies_current,
        item.explicitly_authorized,
    )


def _consistency_response(
    run: ConsistencyCheckRun, findings: tuple[Finding, ...]
) -> ConsistencyCheckResponse:
    return ConsistencyCheckResponse(
        id=run.id,
        project_id=run.project_id,
        status=run.status,
        workflow_run_id=run.workflow_run_id,
        created_at=run.created_at,
        findings=[FindingResponse.model_validate(item) for item in findings],
    )


@router.post(
    "/projects/{project_id}/consistency/resolutions",
    response_model=ResolutionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createConsistencyResolution",
)
async def create_consistency_resolution(
    project_id: UUID,
    body: ResolutionCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ResolutionResponse:
    item = await container.consistency.service.propose_resolution(
        context,
        ProposeResolutionCommand(
            project_id,
            tuple(body.finding_ids),
            body.strategy_code,
            FactTarget(body.target_reference, body.target_expected_version),
            tuple(body.impact_references),
            body.workflow_run_id,
        ),
    )
    response.headers["Location"] = (
        f"/api/v1/projects/{project_id}/consistency/resolutions/{item.id}"
    )
    response.headers["ETag"] = etag(item.version)
    return ResolutionResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/consistency/resolutions/{proposal_id}",
    response_model=ResolutionResponse,
    operation_id="getConsistencyResolution",
)
async def get_consistency_resolution(
    project_id: UUID, proposal_id: UUID, context: Context, container: Container
) -> ResolutionResponse:
    trace = await container.consistency.service.trace(context, project_id, proposal_id)
    return ResolutionResponse.model_validate(trace.proposal)


@router.post(
    "/projects/{project_id}/consistency/resolutions/{proposal_id}/decision",
    response_model=ResolutionResponse,
    operation_id="decideConsistencyResolution",
)
async def decide_consistency_resolution(
    project_id: UUID,
    proposal_id: UUID,
    body: ResolutionDecisionRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ResolutionResponse:
    item = await container.consistency.service.decide_resolution(
        context,
        DecideResolutionCommand(project_id, proposal_id, body.decision, expected_version),
    )
    response.headers["ETag"] = etag(item.version)
    return ResolutionResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/quality/rubrics",
    response_model=RubricResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createQualityRubric",
)
async def create_quality_rubric(
    project_id: UUID,
    body: RubricCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> RubricResponse:
    item = await container.quality.service.create_rubric(
        context,
        CreateRubricCommand(
            project_id,
            body.rubric_key,
            body.version,
            body.schema_version,
            tuple(body.dimension_keys),
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/quality/rubrics/{item.id}"
    return RubricResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/quality/evaluations",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createQualityEvaluation",
)
async def create_quality_evaluation(
    project_id: UUID,
    body: EvaluationCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> EvaluationRunResponse:
    item = await container.quality.service.start(
        context,
        StartEvaluationCommand(
            project_id, body.rubric_id, body.input_reference, body.workflow_run_id
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/quality/evaluations/{item.id}"
    return EvaluationRunResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/quality/evaluations/{run_id}/execute",
    response_model=QualityResultResponse,
    operation_id="executeQualityEvaluation",
)
async def execute_quality_evaluation(
    project_id: UUID,
    run_id: UUID,
    body: EvaluationExecuteRequest,
    context: Context,
    container: Container,
) -> QualityResultResponse:
    _run, result = await container.quality.service.evaluate(
        context,
        project_id,
        run_id,
        EvaluationEvidence(body.input_reference, body.consistency_status),
    )
    return _quality_result_response(result)


@router.get(
    "/projects/{project_id}/quality/evaluations/{run_id}",
    response_model=QualityResultResponse,
    operation_id="getQualityEvaluation",
)
async def get_quality_evaluation(
    project_id: UUID, run_id: UUID, context: Context, container: Container
) -> QualityResultResponse:
    result = await container.quality.service.get_result(context, project_id, run_id)
    return _quality_result_response(result)


def _quality_result_response(result: QualityResult) -> QualityResultResponse:
    return QualityResultResponse(
        id=result.id,
        evaluation_run_id=result.evaluation_run_id,
        status=result.status,
        evaluator_key=result.evaluator_key,
        evaluator_version=result.evaluator_version,
        dimensions=[ScoreDimensionResponse.model_validate(item) for item in result.dimensions],
        result_reference=result.result_reference,
        created_at=result.created_at,
    )


@router.post(
    "/projects/{project_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createFeedback",
)
async def create_feedback(
    project_id: UUID,
    body: FeedbackCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> FeedbackResponse:
    item = await container.feedback.service.capture(
        context,
        CaptureFeedbackCommand(
            project_id,
            body.source,
            body.schema_version,
            body.signal_code,
            body.numeric_value,
            body.source_reference,
            body.consent_policy_version,
            body.creator_profile_id,
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/feedback/{item.id}"
    return FeedbackResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/feedback/behavior-consent",
    response_model=BehaviorConsentStatusResponse,
    operation_id="getBehaviorConsent",
)
async def get_behavior_consent(
    project_id: UUID, context: Context, container: Container
) -> BehaviorConsentStatusResponse:
    item = await container.feedback.service.get_behavior_consent(context, project_id)
    return BehaviorConsentStatusResponse(
        active=item is not None,
        consent=(BehaviorConsentResponse.model_validate(item) if item is not None else None),
    )


@router.post(
    "/projects/{project_id}/feedback/behavior-consent",
    response_model=BehaviorConsentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="grantBehaviorConsent",
)
async def grant_behavior_consent(
    project_id: UUID,
    body: BehaviorConsentGrantRequest,
    response: Response,
    context: Context,
    container: Container,
) -> BehaviorConsentResponse:
    item = await container.feedback.service.grant_behavior_consent(
        context, project_id, body.policy_version
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/feedback/behavior-consent"
    return BehaviorConsentResponse.model_validate(item)


@router.delete(
    "/projects/{project_id}/feedback/behavior-consent",
    response_model=BehaviorConsentWithdrawalResponse,
    operation_id="withdrawBehaviorConsent",
)
async def withdraw_behavior_consent(
    project_id: UUID, context: Context, container: Container
) -> BehaviorConsentWithdrawalResponse:
    result = await container.feedback.service.withdraw_behavior_consent(context, project_id)
    return BehaviorConsentWithdrawalResponse(
        consent=BehaviorConsentResponse.model_validate(result.consent),
        anonymized_event_ids=list(result.anonymized_event_ids),
        tombstone_count=len(result.tombstones),
    )


@router.get(
    "/projects/{project_id}/feedback/{event_id}",
    response_model=FeedbackResponse,
    operation_id="getFeedback",
)
async def get_feedback(
    project_id: UUID, event_id: UUID, context: Context, container: Container
) -> FeedbackResponse:
    item = await container.feedback.service.get_feedback(context, project_id, event_id)
    return FeedbackResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/metrics",
    response_model=MetricDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMetricDefinition",
)
async def create_metric_definition(
    project_id: UUID,
    body: MetricDefinitionCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> MetricDefinitionResponse:
    item = await container.feedback.service.register_metric(
        context,
        RegisterMetricCommand(
            project_id,
            body.name,
            body.version,
            body.unit,
            tuple(
                MetricDimension(dimension.key, tuple(dimension.allowed_values))
                for dimension in body.dimensions
            ),
            body.retention_days,
            body.sensitivity,
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/metrics/{item.id}"
    return MetricDefinitionResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/metric-points",
    response_model=MetricPointResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMetricPoint",
)
async def create_metric_point(
    project_id: UUID,
    body: MetricRecordRequest,
    response: Response,
    context: Context,
    container: Container,
) -> MetricPointResponse:
    item = await container.feedback.service.record_metric(
        context,
        RecordMetricCommand(
            project_id,
            body.name,
            body.value,
            tuple(sorted(body.dimensions.items())),
            body.source_reference,
            body.source_feedback_event_id,
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/metric-points/{item.id}"
    return MetricPointResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/metric-points/{point_id}",
    response_model=MetricPointResponse,
    operation_id="getMetricPoint",
)
async def get_metric_point(
    project_id: UUID, point_id: UUID, context: Context, container: Container
) -> MetricPointResponse:
    item = await container.feedback.service.get_metric_point(context, project_id, point_id)
    return MetricPointResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/metric-points/{point_id}/diagnostics",
    response_model=DiagnosticCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createDiagnostics",
)
async def create_diagnostics(
    project_id: UUID, point_id: UUID, context: Context, container: Container
) -> DiagnosticCollectionResponse:
    items = await container.feedback.service.diagnose(context, project_id, point_id)
    return DiagnosticCollectionResponse(
        items=[DiagnosticResponse.model_validate(item) for item in items]
    )


@router.get(
    "/projects/{project_id}/diagnostics/{finding_id}",
    response_model=DiagnosticResponse,
    operation_id="getDiagnostic",
)
async def get_diagnostic(
    project_id: UUID, finding_id: UUID, context: Context, container: Container
) -> DiagnosticResponse:
    item = await container.feedback.service.get_diagnostic(context, project_id, finding_id)
    return DiagnosticResponse.model_validate(item)


def _experiment_response(
    experiment: Experiment, variants: tuple[Variant, ...]
) -> ExperimentResponse:
    return ExperimentResponse(
        id=experiment.id,
        workspace_id=experiment.workspace_id,
        project_id=experiment.project_id,
        experiment_key=experiment.experiment_key,
        protocol_version=experiment.protocol_version,
        hypothesis_code=experiment.hypothesis_code,
        primary_metric_name=experiment.primary_metric_name,
        sample_scope=experiment.sample_scope,
        starts_at=experiment.starts_at,
        ends_at=experiment.ends_at,
        stop_condition_codes=list(experiment.stop_condition_codes),
        status=experiment.status,
        created_by=experiment.created_by,
        created_at=experiment.created_at,
        result_code=experiment.result_code,
        variants=[VariantResponse.model_validate(item) for item in variants],
    )


@router.post(
    "/projects/{project_id}/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createExperiment",
)
async def create_experiment(
    project_id: UUID,
    body: ExperimentCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ExperimentResponse:
    experiment, variants = await container.feedback.service.create_experiment(
        context,
        CreateExperimentCommand(
            project_id,
            body.experiment_key,
            body.protocol_version,
            body.hypothesis_code,
            body.primary_metric_name,
            body.sample_scope,
            body.starts_at,
            body.ends_at,
            tuple(body.stop_condition_codes),
            tuple(
                VariantDraft(item.variant_key, item.configuration_reference)
                for item in body.variants
            ),
        ),
    )
    response.headers["Location"] = f"/api/v1/projects/{project_id}/experiments/{experiment.id}"
    return _experiment_response(experiment, variants)


@router.get(
    "/projects/{project_id}/experiments/{experiment_id}",
    response_model=ExperimentResponse,
    operation_id="getExperiment",
)
async def get_experiment(
    project_id: UUID, experiment_id: UUID, context: Context, container: Container
) -> ExperimentResponse:
    experiment, variants = await container.feedback.service.get_experiment(
        context, project_id, experiment_id
    )
    return _experiment_response(experiment, variants)


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/start",
    response_model=ExperimentResponse,
    operation_id="startExperiment",
)
async def start_experiment(
    project_id: UUID, experiment_id: UUID, context: Context, container: Container
) -> ExperimentResponse:
    experiment = await container.feedback.service.start_experiment(
        context, project_id, experiment_id
    )
    _stored, variants = await container.feedback.service.get_experiment(
        context, project_id, experiment_id
    )
    return _experiment_response(experiment, variants)


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/samples",
    response_model=ExperimentSampleResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createExperimentSample",
)
async def create_experiment_sample(
    project_id: UUID,
    experiment_id: UUID,
    body: ExperimentSampleCreateRequest,
    response: Response,
    context: Context,
    container: Container,
) -> ExperimentSampleResponse:
    item = await container.feedback.service.add_experiment_sample(
        context,
        project_id,
        experiment_id,
        body.variant_id,
        body.metric_point_id,
    )
    response.headers["Location"] = (
        f"/api/v1/projects/{project_id}/experiments/{experiment_id}/samples/{item.id}"
    )
    return ExperimentSampleResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/finish",
    response_model=ExperimentResponse,
    operation_id="finishExperiment",
)
async def finish_experiment(
    project_id: UUID,
    experiment_id: UUID,
    body: ExperimentFinishRequest,
    context: Context,
    container: Container,
) -> ExperimentResponse:
    experiment = await container.feedback.service.finish_experiment(
        context,
        FinishExperimentCommand(
            project_id,
            experiment_id,
            ExperimentStatus(body.status),
            body.result_code,
        ),
    )
    _stored, variants = await container.feedback.service.get_experiment(
        context, project_id, experiment_id
    )
    return _experiment_response(experiment, variants)


@router.post(
    "/projects/{project_id}/diagnostics/{finding_id}/improvement-proposals",
    response_model=ImprovementProposalResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createImprovementProposal",
)
async def create_improvement_proposal(
    project_id: UUID,
    finding_id: UUID,
    response: Response,
    context: Context,
    container: Container,
) -> ImprovementProposalResponse:
    finding = await container.feedback.service.get_diagnostic(context, project_id, finding_id)
    item = await container.evolution.service.observe(context, project_id, finding)
    response.headers["Location"] = f"/api/v1/projects/{project_id}/improvement-proposals/{item.id}"
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/improvement-proposals/{proposal_id}",
    response_model=ImprovementProposalResponse,
    operation_id="getImprovementProposal",
)
async def get_improvement_proposal(
    project_id: UUID, proposal_id: UUID, context: Context, container: Container
) -> ImprovementProposalResponse:
    item = await container.evolution.service.get(context, project_id, proposal_id)
    return ImprovementProposalResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/improvement-proposals/{proposal_id}/plan",
    response_model=ImprovementProposalResponse,
    operation_id="planImprovementProposal",
)
async def plan_improvement_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: ImprovementPlanRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ImprovementProposalResponse:
    item = await container.evolution.service.propose(
        context,
        project_id,
        proposal_id,
        expected_version,
        body.action,
        body.change_reference,
        body.rollback_reference,
    )
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/improvement-proposals/{proposal_id}/simulate",
    response_model=ImprovementProposalResponse,
    operation_id="simulateImprovementProposal",
)
async def simulate_improvement_proposal(
    project_id: UUID,
    proposal_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ImprovementProposalResponse:
    item = await container.evolution.service.simulate(
        context, project_id, proposal_id, expected_version
    )
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/improvement-proposals/{proposal_id}/evaluate",
    response_model=ImprovementProposalResponse,
    operation_id="evaluateImprovementProposal",
)
async def evaluate_improvement_proposal(
    project_id: UUID,
    proposal_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ImprovementProposalResponse:
    item = await container.evolution.service.evaluate(
        context, project_id, proposal_id, expected_version
    )
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/improvement-proposals/{proposal_id}/request-approval",
    response_model=ImprovementProposalResponse,
    operation_id="requestImprovementApproval",
)
async def request_improvement_approval(
    project_id: UUID,
    proposal_id: UUID,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ImprovementProposalResponse:
    item = await container.evolution.service.request_approval(
        context, project_id, proposal_id, expected_version
    )
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.post(
    "/projects/{project_id}/improvement-proposals/{proposal_id}/decision",
    response_model=ImprovementProposalResponse,
    operation_id="decideImprovementProposal",
)
async def decide_improvement_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: ImprovementDecisionRequest,
    response: Response,
    context: Context,
    container: Container,
    expected_version: ExpectedVersion,
) -> ImprovementProposalResponse:
    item = await container.evolution.service.decide(
        context,
        project_id,
        proposal_id,
        expected_version,
        body.decision,
    )
    response.headers["ETag"] = etag(item.version)
    return ImprovementProposalResponse.model_validate(item)


@router.get(
    "/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Resumable workflow event stream.",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "x-accos-event-data-schema": {"$ref": "#/components/schemas/SseEventData"},
                }
            },
        }
    },
    operation_id="streamWorkflowEvents",
)
async def stream_workflow_events(
    request: Request,
    run_id: UUID,
    context: Context,
    container: Container,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    run = await container.workflows.service.get(context, run_id)
    after_sequence = _parse_event_cursor(last_event_id, run_id)
    initial = await container.workflows.service.get_events(
        context, run_id, after_sequence=after_sequence
    )
    _ensure_contiguous(initial, after_sequence, run_id)
    if not initial and after_sequence:
        history = await container.workflows.service.get_events(context, run_id)
        if not history or after_sequence > history[-1].sequence:
            raise InvalidRequestError("Last-Event-ID is ahead of the retained event stream.")
    return StreamingResponse(
        _event_stream(
            request,
            context,
            container.workflows.service,
            run,
            initial,
            after_sequence,
            telemetry=container.observability.telemetry,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _parse_event_cursor(value: str | None, run_id: UUID) -> int:
    if value is None:
        return 0
    raw_run_id, separator, raw_sequence = value.partition(":")
    try:
        cursor_run_id = UUID(raw_run_id)
        sequence = int(raw_sequence)
    except ValueError:
        raise InvalidRequestError("Last-Event-ID is invalid.") from None
    if not separator or cursor_run_id != run_id or sequence < 0:
        raise InvalidRequestError("Last-Event-ID does not match the requested run.")
    return sequence


def _ensure_contiguous(
    events: tuple[WorkflowRunEvent, ...], after_sequence: int, run_id: UUID
) -> None:
    if events and events[0].sequence != after_sequence + 1:
        raise EventCursorExpiredError(f"/api/v1/workflow-runs/{run_id}")


async def _event_stream(
    request: Request,
    context: SecurityContext,
    service: WorkflowService,
    run: WorkflowRun,
    initial: tuple[WorkflowRunEvent, ...],
    after_sequence: int,
    *,
    poll_seconds: float = 10.0,
    telemetry: TelemetryRuntime | None = None,
) -> AsyncIterator[str]:
    if telemetry is not None:
        telemetry.adjust_gauge("accos_sse_connections", 1.0)
    try:
        sequence = after_sequence
        yield "retry: 3000\n\n"
        pending = initial
        while True:
            for event in pending:
                sequence = event.sequence
                yield _serialize_sse_event(run, event)
            if await request.is_disconnected():
                return
            yield f": heartbeat run={run.id} sequence={sequence}\n\n"
            await asyncio.sleep(poll_seconds)
            pending = await service.get_events(context, run.id, after_sequence=sequence)
            try:
                _ensure_contiguous(pending, sequence, run.id)
            except EventCursorExpiredError:
                yield (
                    "event: stream.reset\n"
                    f'data: {{"reason":"cursor_expired","status_url":'
                    f'"/api/v1/workflow-runs/{run.id}"}}\n\n'
                )
                return
    finally:
        if telemetry is not None:
            telemetry.adjust_gauge("accos_sse_connections", -1.0)


def _serialize_sse_event(run: WorkflowRun, event: WorkflowRunEvent) -> str:
    data = SseEventData(
        event_id=event.id,
        sequence=event.sequence,
        type=event.event_type,
        schema_version=event.version,
        correlation_id=run.correlation_id,
        run_id=run.id,
        project_id=run.project_id,
        occurred_at=event.occurred_at,
        payload=event.payload,
    )
    return (
        f"id: {run.id}:{event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {data.model_dump_json()}\n\n"
    )
