from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from celery.contrib.testing.worker import start_worker  # type: ignore[import-untyped]
from psycopg import sql
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from accos.adapters.agents import (
    AgentContextSnapshotRow,
    AgentRunEventRow,
    AgentRunRow,
    SqlAlchemyAgentRepository,
)
from accos.adapters.assets import (
    AssetVersionRow,
    InMemoryObjectStorage,
    SqlAlchemyAssetRepository,
    UploadSessionRow,
)
from accos.adapters.creative import (
    CreativeContainerRow,
    CreativeRecordRow,
    SqlAlchemyCreativeRepository,
)
from accos.adapters.extensions import (
    ExtensionGraphEdgeRow,
    ExtensionGraphNodeRow,
    SqlAlchemyExtensionGraphStore,
)
from accos.adapters.identity import (
    AuditEventRow,
    ControlRequestRow,
    HumanApprovalRow,
    IdentityRuntime,
    MembershipRow,
    ServiceIdentityRow,
    SqlAlchemyAuditStore,
    SqlAlchemyControlRequestStore,
    SqlAlchemyIdentityRepository,
    UserRow,
    WorkspaceRow,
)
from accos.adapters.knowledge import (
    AssetSourceReader,
    DeterministicChunker,
    DeterministicNormalizer,
    FakeEmbedder,
    InMemoryVectorIndex,
    KnowledgeChunkRow,
    KnowledgeCitationRow,
    KnowledgeDocumentRow,
    KnowledgeDocumentVersionRow,
    KnowledgeEdgeRow,
    KnowledgeEmbeddingRefRow,
    KnowledgeIngestionRunRow,
    KnowledgeSourceRow,
    KnowledgeVectorRow,
    NotConfiguredVerificationProvider,
    PgVectorIndex,
    SqlAlchemyGraphProjection,
    SqlAlchemyKnowledgeRepository,
    TextMarkdownExtractor,
)
from accos.adapters.memory import (
    MemoryConflictRow,
    MemoryContextPackageRow,
    MemoryEventRow,
    MemoryGrantRow,
    MemoryLinkRow,
    MemoryRecordRow,
    SqlAlchemyMemoryRepository,
)
from accos.adapters.models import (
    FakeModelProvider,
    ModelUsageRecordRow,
    SqlAlchemyUsageLedger,
)
from accos.adapters.persistence import (
    ClaimedEvent,
    DatabaseHealthProbe,
    DatabaseRuntime,
    EngineOptions,
    InMemoryPublisher,
    OutboxRelay,
    RelayReport,
    SqlAlchemyIdempotencyStore,
    SqlAlchemyOutboxRepository,
    SqlAlchemyOutboxWriter,
    SqlAlchemyUnitOfWork,
)
from accos.adapters.persistence.models import (
    PUBLISHED_STATUS,
    IdempotencyRecordRow,
    OutboxEventRow,
)
from accos.adapters.projects import (
    ArtifactRevisionRow,
    ProjectRow,
    SqlAlchemyProjectRepository,
)
from accos.adapters.tools import (
    FakeToolExecutor,
    SqlAlchemyToolCallLedger,
    ToolCallRecordRow,
)
from accos.adapters.workflows import (
    CeleryEventPublisher,
    InMemoryTaskQueue,
    SqlAlchemyWorkflowRepository,
    TaskRunRow,
    WorkflowRunEventRow,
    WorkflowStepRunRow,
    create_celery_app,
    register_celery_consumer,
)
from accos.kernel.contracts import PageRequest
from accos.kernel.errors import (
    ConcurrencyConflictError,
    ConfigurationError,
    IdempotencyConflictError,
    InvalidStateError,
    PermissionDeniedError,
    ScopeViolationError,
)
from accos.kernel.events import EventEnvelope
from accos.kernel.graph import (
    GraphDirection,
    GraphEdge,
    GraphNodeRef,
    GraphProjectionEvent,
    GraphProjectionOperation,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.persistence import IdempotencyRecord, Page
from accos.kernel.security import ActorKind, SecurityContext
from accos.kernel.settings import load_settings
from accos.modules.agents.public import (
    DEFAULT_AGENT_BUDGET,
    AgentBudget,
    AgentContextSnapshot,
    AgentErrorCode,
    AgentInvocation,
    AgentProposal,
    AgentResultKind,
    AgentRun,
    AgentRunStatus,
    AgentRuntimeError,
    AgentWorkflowExecutor,
    DefaultAgentSupervisor,
    FakeAgentBehavior,
    FakeAgentExecutor,
    InMemoryAgentMetrics,
    InMemoryAgentRegistry,
    MasterOrchestrator,
    ProtectedOperation,
    RawAgentResult,
    built_in_agent_descriptors,
)
from accos.modules.assets.public import (
    AssetService,
    AssetSort,
    AssetStatus,
    DefaultUploadSecurityPolicy,
    ProcessingStatus,
    UnconfiguredContentScanner,
    UploadStatus,
)
from accos.modules.creative.public import (
    BehaviorProposal,
    Chapter,
    Character,
    CreativeDecision,
    CreativeOwner,
    CreativeRecordStatus,
    CreativeReference,
    CreativeReferenceKind,
    CreatorProfile,
    ImpactLink,
    StyleProfile,
    Work,
    World,
    WorldState,
)
from accos.modules.identity.application import (
    AuthorizationRequest,
    AuthorizationService,
    ResourceScope,
)
from accos.modules.identity.domain import (
    POLICY_VERSION,
    ApprovalDecision,
    ControlRequest,
    ControlRequestKind,
    ControlRequestStatus,
    HumanApproval,
    Permission,
    Role,
    permissions_for,
)
from accos.modules.identity.ports import AuditEvent
from accos.modules.knowledge.public import (
    Chunk,
    DefaultRetriever,
    EmbeddingRef,
    IngestionStatus,
    KnowledgeEdge,
    KnowledgeErrorCode,
    KnowledgeService,
    KnowledgeWorkflowExecutor,
    RelationKind,
    RetrievalFilter,
    RetrievalRequest,
    SourceSnapshot,
    VerificationPolicy,
    VerificationStatus,
    knowledge_ingestion_definition,
)
from accos.modules.memory.public import (
    CREATOR_SCOPES,
    PROJECT_SCOPES,
    AllowedAnchor,
    ContextItem,
    ContextOmission,
    ContextPackage,
    MemoryAnchorKind,
    MemoryConflict,
    MemoryConflictStatus,
    MemoryGrant,
    MemoryLink,
    MemoryProvenance,
    MemoryRecord,
    MemoryScope,
    MemoryStatus,
    OmissionReason,
    RetentionKind,
    RetentionRule,
)
from accos.modules.models.public import (
    ModelCallStatus,
    ModelCapability,
    ModelGateway,
    ModelPolicy,
    ModelRegistry,
    UsageRecord,
)
from accos.modules.projects.public import (
    ArtifactSort,
    ArtifactType,
    ProjectService,
    ProjectSettings,
    ProjectSort,
    ProjectStatus,
)
from accos.modules.tools.public import (
    ToolCallRecord,
    ToolCallStatus,
    ToolDescriptor,
    ToolGateway,
    ToolRegistry,
)
from accos.modules.workflows.public import (
    ApprovalRecord,
    FrameworkSmokeExecutor,
    PermanentStepError,
    RetryableStepError,
    RetryPolicy,
    StepDefinition,
    StepExecution,
    StepExecutionResult,
    StepKind,
    TaskRunStatus,
    WorkerDisposition,
    WorkflowApprovalDecision,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowService,
    WorkflowWorker,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = ROOT / "services" / "core" / "alembic.ini"


@dataclass(slots=True)
class MutableClock:
    value: datetime

    def now(self) -> datetime:
        return self.value

    def advance(self, *, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


async def seed_workflow_scope(runtime: DatabaseRuntime, now: datetime) -> tuple[UUID, UUID, UUID]:
    """Create the minimum relational scope required by workflow persistence tests."""
    actor_id, workspace_id, project_id = uuid4(), uuid4(), uuid4()
    async with runtime.sessions.begin() as session:
        session.add(UserRow(id=actor_id, issuer="fixture-issuer", subject=f"fixture-{actor_id}"))
    async with runtime.sessions.begin() as session:
        session.add(WorkspaceRow(id=workspace_id, owner_user_id=actor_id))
    async with runtime.sessions.begin() as session:
        session.add(
            ProjectRow(
                id=project_id,
                workspace_id=workspace_id,
                name="fixture-project",
                status="active",
                settings={},
                created_by=actor_id,
                created_at=now,
                updated_at=now,
                version=1,
            )
        )
    return actor_id, workspace_id, project_id


async def submit_workflow_run(  # noqa: PLR0913
    repository: SqlAlchemyWorkflowRepository,
    *,
    actor_id: UUID,
    workspace_id: UUID,
    project_id: UUID,
    definition: WorkflowDefinition,
    key: str,
    now: datetime,
) -> WorkflowRun:
    """Persist one definition and run without exercising authorization again."""
    await repository.ensure_definition(definition)
    workflow_run = WorkflowRun(
        uuid4(),
        workspace_id,
        project_id,
        definition.id,
        definition.name,
        definition.version,
        WorkflowRunStatus.PENDING,
        key,
        "fixture-token://input",
        actor_id,
        ActorKind.USER.value,
        uuid4(),
        now,
        now,
    )
    stored, created = await repository.submit(
        workflow_run,
        definition,
        request_digest=hashlib.sha256(key.encode()).hexdigest(),
    )
    assert created
    return stored


async def workflow_task(runtime: DatabaseRuntime, run_id: UUID) -> TaskRunRow:
    """Load the task for a single-step fixture run."""
    async with runtime.sessions() as session:
        task = await session.scalar(
            select(TaskRunRow)
            .where(TaskRunRow.workflow_run_id == run_id)
            .order_by(TaskRunRow.created_at.desc())
        )
    assert task is not None
    return task


def technical_definition(
    name: str,
    now: datetime,
    *steps: tuple[StepKind, float | None],
) -> WorkflowDefinition:
    """Build a unique metadata-only definition for persistence edge tests."""
    return WorkflowDefinition(
        uuid4(),
        name,
        1,
        tuple(
            StepDefinition(
                uuid4(),
                f"fixture-step-{position}",
                position,
                kind,
                5,
                RetryPolicy(),
                approval_expires_seconds=approval_expiry,
            )
            for position, (kind, approval_expiry) in enumerate(steps)
        ),
        now,
    )


@dataclass(frozen=True, slots=True)
class TemporaryDatabaseFactory:
    source_url: str

    @contextmanager
    def create(self) -> Iterator[str]:
        source = make_url(self.source_url)
        name = f"accos_test_{uuid4().hex}"
        admin_url = source.set(drivername="postgresql", database="postgres")
        admin_dsn = admin_url.render_as_string(hide_password=False)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield source.set(drivername="postgresql+psycopg", database=name).render_as_string(
                hide_password=False
            )
        finally:
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture(scope="session")
def database_factory() -> TemporaryDatabaseFactory:
    return TemporaryDatabaseFactory(load_settings().required.database_url)


def migration_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_CONFIG))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture
def migrated_database_url(database_factory: TemporaryDatabaseFactory) -> Iterator[str]:
    with database_factory.create() as database_url:
        command.upgrade(migration_config(database_url), "head")
        yield database_url


def test_empty_database_upgrade_is_repeatable_and_has_no_model_drift(
    database_factory: TemporaryDatabaseFactory,
) -> None:
    with database_factory.create() as database_url:
        config = migration_config(database_url)
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.check(config)

        sync_url = make_url(database_url).set(drivername="postgresql")
        with psycopg.connect(sync_url.render_as_string(hide_password=False)) as connection:
            tables = connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'accos' ORDER BY table_name"
            ).fetchall()
            extension = connection.execute(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
            metadata = connection.execute(
                "SELECT component, revision FROM accos.schema_metadata"
            ).fetchone()
            foreign_keys = connection.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE contype = 'f' AND connamespace = 'accos'::regnamespace "
                "ORDER BY conname"
            ).fetchall()

        assert tables == [
            ("agent_context_snapshots",),
            ("agent_run_events",),
            ("agent_runs",),
            ("asset_upload_sessions",),
            ("asset_versions",),
            ("assets",),
            ("audit_events",),
            ("consistency_canon_entries",),
            ("consistency_check_runs",),
            ("consistency_evidence_projection",),
            ("consistency_findings",),
            ("consistency_resolution_proposals",),
            ("consistency_timeline_events",),
            ("creative_containers",),
            ("creative_records",),
            ("evolution_audit_entries",),
            ("evolution_improvement_proposals",),
            ("extension_graph_edges",),
            ("extension_graph_nodes",),
            ("feedback_behavior_consents",),
            ("feedback_diagnostic_findings",),
            ("feedback_events",),
            ("feedback_experiment_samples",),
            ("feedback_experiment_variants",),
            ("feedback_experiments",),
            ("feedback_metric_definitions",),
            ("feedback_metric_points",),
            ("feedback_tombstones",),
            ("idempotency_records",),
            ("identity_control_requests",),
            ("identity_human_approvals",),
            ("identity_memberships",),
            ("identity_service_identities",),
            ("identity_users",),
            ("identity_workspaces",),
            ("knowledge_chunks",),
            ("knowledge_citations",),
            ("knowledge_document_versions",),
            ("knowledge_documents",),
            ("knowledge_edges",),
            ("knowledge_embedding_refs",),
            ("knowledge_ingestion_runs",),
            ("knowledge_sources",),
            ("knowledge_vector_index",),
            ("memory_conflicts",),
            ("memory_context_packages",),
            ("memory_events",),
            ("memory_grants",),
            ("memory_links",),
            ("memory_records",),
            ("model_usage_records",),
            ("outbox_events",),
            ("project_artifact_revisions",),
            ("project_artifacts",),
            ("projects",),
            ("quality_evaluation_runs",),
            ("quality_results",),
            ("quality_rubric_versions",),
            ("schema_metadata",),
            ("tool_call_records",),
            ("workflow_approval_decisions",),
            ("workflow_approval_requests",),
            ("workflow_definitions",),
            ("workflow_run_events",),
            ("workflow_runs",),
            ("workflow_step_definitions",),
            ("workflow_step_runs",),
            ("workflow_task_runs",),
        ]
        assert extension == ("vector",)
        assert metadata == ("accos-core", "0012_extension_graph_projection")
        assert foreign_keys == [
            ("fk_agent_context_memory_package",),
            ("fk_agent_context_project",),
            ("fk_agent_events_run",),
            ("fk_agent_runs_context",),
            ("fk_agent_runs_project",),
            ("fk_agent_runs_workflow",),
            ("fk_approval_decisions_request",),
            ("fk_approval_requests_step_run",),
            ("fk_approval_requests_workflow_run",),
            ("fk_artifact_revisions_artifact",),
            ("fk_artifacts_project",),
            ("fk_asset_versions_asset",),
            ("fk_assets_project",),
            ("fk_consistency_canon_project",),
            ("fk_consistency_checks_project",),
            ("fk_consistency_findings_check",),
            ("fk_consistency_resolutions_project",),
            ("fk_consistency_timeline_project",),
            ("fk_creative_containers_project",),
            ("fk_creative_records_container_owner",),
            ("fk_evolution_audit_proposal",),
            ("fk_evolution_proposals_project",),
            ("fk_feedback_consents_project",),
            ("fk_feedback_diagnostics_point",),
            ("fk_feedback_events_consent",),
            ("fk_feedback_events_project",),
            ("fk_feedback_experiments_project",),
            ("fk_feedback_metric_definitions_project",),
            ("fk_feedback_points_definition",),
            ("fk_feedback_points_event",),
            ("fk_feedback_samples_event",),
            ("fk_feedback_samples_experiment",),
            ("fk_feedback_samples_point",),
            ("fk_feedback_samples_variant",),
            ("fk_feedback_tombstones_event",),
            ("fk_feedback_variants_experiment",),
            ("fk_human_approvals_request",),
            ("fk_knowledge_chunks_source",),
            ("fk_knowledge_chunks_version",),
            ("fk_knowledge_citations_chunk",),
            ("fk_knowledge_citations_document",),
            ("fk_knowledge_citations_source",),
            ("fk_knowledge_citations_version",),
            ("fk_knowledge_documents_project",),
            ("fk_knowledge_embeddings_chunk",),
            ("fk_knowledge_runs_document",),
            ("fk_knowledge_runs_source",),
            ("fk_knowledge_runs_version",),
            ("fk_knowledge_runs_workflow",),
            ("fk_knowledge_sources_project",),
            ("fk_knowledge_vectors_embedding",),
            ("fk_knowledge_versions_document",),
            ("fk_knowledge_versions_source",),
            ("fk_memberships_user",),
            ("fk_memberships_workspace",),
            ("fk_memory_conflicts_candidate",),
            ("fk_memory_conflicts_current",),
            ("fk_memory_context_project",),
            ("fk_memory_grants_project",),
            ("fk_memory_links_from",),
            ("fk_memory_links_to",),
            ("fk_memory_records_project",),
            ("fk_projects_workspace",),
            ("fk_quality_results_run",),
            ("fk_quality_rubrics_project",),
            ("fk_quality_runs_rubric",),
            ("fk_run_events_workflow_run",),
            ("fk_service_identities_workspace",),
            ("fk_step_runs_definition",),
            ("fk_step_runs_workflow_run",),
            ("fk_task_runs_step_run",),
            ("fk_task_runs_workflow_run",),
            ("fk_workflow_runs_definition",),
            ("fk_workflow_runs_project",),
            ("fk_workflow_steps_definition",),
            ("fk_workspaces_owner_user",),
        ]


def test_extension_graph_projection_is_scoped_bounded_and_rebuildable(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 1, 1.0, 60),
        )
        try:
            store = SqlAlchemyExtensionGraphStore(runtime.sessions)
            workspace_id = uuid4()
            other_workspace_id = uuid4()
            first = GraphNodeRef(workspace_id, "fixture-owner", "fixture-kind", uuid4())
            second = GraphNodeRef(workspace_id, "fixture-owner", "fixture-kind", uuid4())
            third = GraphNodeRef(workspace_id, "fixture-owner", "fixture-kind", uuid4())
            incoming = GraphNodeRef(workspace_id, "fixture-owner", "fixture-kind", uuid4())
            edge_one = GraphEdge(first, second, "fixture-next")
            edge_two = GraphEdge(second, third, "fixture-next")
            edge_three = GraphEdge(incoming, first, "fixture-parent")
            projection_owner = "fixture-projection"

            await store.replace_edges(
                workspace_id,
                projection_owner=projection_owner,
                edges=(edge_one, edge_two, edge_three, edge_one),
            )
            assert await store.neighbors(
                first,
                projection_owner=projection_owner,
                direction=GraphDirection.OUTGOING,
                limit=10,
            ) == (edge_one,)
            assert await store.neighbors(
                first,
                projection_owner=projection_owner,
                direction=GraphDirection.INCOMING,
                limit=10,
            ) == (edge_three,)
            assert set(
                await store.neighbors(
                    first,
                    projection_owner=projection_owner,
                    direction=GraphDirection.BOTH,
                    limit=10,
                )
            ) == {edge_one, edge_three}

            traversal = await store.traverse(
                first,
                projection_owner=projection_owner,
                direction=GraphDirection.OUTGOING,
                max_depth=2,
                limit=10,
            )
            assert traversal.start == first
            assert traversal.nodes == (first, second, third)
            assert traversal.edges == (edge_one, edge_two)
            assert not traversal.truncated

            bounded = await store.traverse(
                first,
                projection_owner=projection_owner,
                direction=GraphDirection.OUTGOING,
                max_depth=2,
                limit=1,
            )
            assert bounded.edges == (edge_one,)
            assert bounded.truncated

            for invalid_limit in (0, 1001):
                with pytest.raises(ValueError, match="graph limit"):
                    await store.neighbors(
                        first,
                        projection_owner=projection_owner,
                        direction=GraphDirection.BOTH,
                        limit=invalid_limit,
                    )
            for invalid_depth in (0, 11):
                with pytest.raises(ValueError, match="max_depth"):
                    await store.traverse(
                        first,
                        projection_owner=projection_owner,
                        direction=GraphDirection.BOTH,
                        max_depth=invalid_depth,
                        limit=10,
                    )

            wrong_scope_edge = GraphEdge(
                GraphNodeRef(
                    other_workspace_id,
                    "fixture-owner",
                    "fixture-kind",
                    uuid4(),
                ),
                second,
                "fixture-invalid",
            )
            with pytest.raises(ValueError, match="edge scope"):
                await store.replace_edges(
                    workspace_id,
                    projection_owner=projection_owner,
                    edges=(wrong_scope_edge,),
                )

            events = (
                GraphProjectionEvent(
                    uuid4(),
                    3,
                    workspace_id,
                    projection_owner,
                    GraphProjectionOperation.REMOVE,
                    edge_one,
                ),
                GraphProjectionEvent(
                    uuid4(),
                    1,
                    workspace_id,
                    projection_owner,
                    GraphProjectionOperation.UPSERT,
                    edge_two,
                ),
                GraphProjectionEvent(
                    uuid4(),
                    2,
                    workspace_id,
                    projection_owner,
                    GraphProjectionOperation.UPSERT,
                    edge_one,
                ),
            )
            await store.rebuild(
                workspace_id,
                projection_owner=projection_owner,
                events=events,
            )
            assert await store.neighbors(
                second,
                projection_owner=projection_owner,
                direction=GraphDirection.OUTGOING,
                limit=10,
            ) == (edge_two,)
            assert (
                await store.neighbors(
                    first,
                    projection_owner=projection_owner,
                    direction=GraphDirection.BOTH,
                    limit=10,
                )
                == ()
            )

            with pytest.raises(ValueError, match="event scope"):
                await store.rebuild(
                    workspace_id,
                    projection_owner=projection_owner,
                    events=(replace(events[0], projection_owner="fixture-other"),),
                )

            await store.replace_edges(
                workspace_id,
                projection_owner="fixture-other",
                edges=(edge_three,),
            )
            await store.drop_projection(workspace_id, projection_owner=projection_owner)
            assert await store.neighbors(
                incoming,
                projection_owner="fixture-other",
                direction=GraphDirection.OUTGOING,
                limit=10,
            ) == (edge_three,)
            async with runtime.sessions() as session:
                assert (
                    await session.scalar(select(func.count()).select_from(ExtensionGraphNodeRow))
                    == 2
                )
                assert (
                    await session.scalar(select(func.count()).select_from(ExtensionGraphEdgeRow))
                    == 1
                )
        finally:
            await runtime.shutdown()

    asyncio.run(exercise(), loop_factory=asyncio.SelectorEventLoop)


def test_upgrade_downgrade_upgrade_round_trip(
    database_factory: TemporaryDatabaseFactory,
) -> None:
    with database_factory.create() as database_url:
        config = migration_config(database_url)
        command.upgrade(config, "head")
        command.downgrade(config, "base")

        sync_url = make_url(database_url).set(drivername="postgresql")
        with psycopg.connect(sync_url.render_as_string(hide_password=False)) as connection:
            schema = connection.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'accos'"
            ).fetchone()
            extension = connection.execute(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
        assert schema is None
        assert extension is None

        command.upgrade(config, "head")
        command.check(config)


def test_creative_sql_repository_scopes_proposals_causation_and_versions(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1, 60))
        repository = SqlAlchemyCreativeRepository(runtime.sessions)
        now = datetime(2026, 9, 6, tzinfo=UTC)
        actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, now)

        def event(
            aggregate_id: UUID, event_type: str, *, event_project_id: UUID = project_id
        ) -> EventEnvelope:
            return EventEnvelope(
                uuid4(),
                workspace_id,
                event_project_id,
                aggregate_id,
                event_type,
                1,
                {"schema": f"{event_type}.v1"},
                now,
            )

        container_types = (Work, World, Character, CreatorProfile)
        containers = []
        for container_type in container_types:
            references = (
                (CreativeReference(CreativeReferenceKind.CREATOR, actor_id),)
                if container_type is CreatorProfile
                else ()
            )
            created_container = container_type(
                uuid4(),
                workspace_id,
                project_id,
                f"fixture-{container_type.owner.value}",
                references,
                actor_id,
                now,
                now,
            )
            containers.append(
                await repository.add_container(
                    created_container,
                    event(
                        created_container.id,
                        f"creative.{created_container.owner.value}.created",
                    ),
                )
            )
        work, world, character, profile = containers
        for stored_container in containers:
            assert (
                await repository.get_container(
                    workspace_id,
                    project_id,
                    stored_container.owner,
                    stored_container.id,
                )
            ) == stored_container
        assert (
            await repository.add_container(work, event(work.id, "creative.novel.created")) == work
        )
        assert (
            await repository.get_container(uuid4(), project_id, CreativeOwner.NOVEL, work.id)
            is None
        )

        state = WorldState(
            uuid4(),
            uuid4(),
            1,
            workspace_id,
            project_id,
            world.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            None,
            None,
            actor_id,
            now,
        )
        stored, created = await repository.add_proposal(
            state, event(world.id, "creative.world.record-proposed")
        )
        assert stored == state and created
        duplicate, duplicate_created = await repository.add_proposal(
            state, event(world.id, "creative.world.record-proposed")
        )
        assert duplicate == state and not duplicate_created
        assert (
            await repository.get_record(workspace_id, project_id, CreativeOwner.WORLD, state.id)
        ) == state
        assert (
            await repository.get_record(uuid4(), project_id, CreativeOwner.WORLD, state.id) is None
        )
        with pytest.raises(ScopeViolationError):
            await repository.decide_proposal(
                workspace_id,
                project_id,
                CreativeOwner.WORLD,
                uuid4(),
                decision=CreativeDecision.APPROVE,
                expected_container_version=1,
                decided_by=actor_id,
                decided_at=now,
                event=event(world.id, "creative.world.record-decided"),
            )
        with pytest.raises(ConcurrencyConflictError):
            await repository.decide_proposal(
                workspace_id,
                project_id,
                CreativeOwner.WORLD,
                state.id,
                decision=CreativeDecision.APPROVE,
                expected_container_version=2,
                decided_by=actor_id,
                decided_at=now,
                event=event(world.id, "creative.world.record-decided"),
            )
        accepted = await repository.decide_proposal(
            workspace_id,
            project_id,
            CreativeOwner.WORLD,
            state.id,
            decision=CreativeDecision.APPROVE,
            expected_container_version=1,
            decided_by=actor_id,
            decided_at=now,
            event=event(world.id, "creative.world.record-decided"),
        )
        assert accepted.current
        assert (
            await repository.get_current_record(
                workspace_id,
                project_id,
                CreativeOwner.WORLD,
                accepted.logical_id,
            )
            == accepted
        )
        assert (
            await repository.get_current_record(
                uuid4(), project_id, CreativeOwner.WORLD, accepted.logical_id
            )
            is None
        )
        with pytest.raises(InvalidStateError):
            await repository.decide_proposal(
                workspace_id,
                project_id,
                CreativeOwner.WORLD,
                state.id,
                decision=CreativeDecision.REJECT,
                expected_container_version=2,
                decided_by=actor_id,
                decided_at=now,
                event=event(world.id, "creative.world.record-decided"),
            )

        revision = replace(
            state,
            id=uuid4(),
            record_version=2,
            source_reference="fixture-state://revision",
        )
        await repository.add_proposal(revision, event(world.id, "creative.world.record-proposed"))
        replacement = await repository.decide_proposal(
            workspace_id,
            project_id,
            CreativeOwner.WORLD,
            revision.id,
            decision=CreativeDecision.APPROVE,
            expected_container_version=2,
            decided_by=actor_id,
            decided_at=now,
            event=event(world.id, "creative.world.record-decided"),
        )
        assert replacement.current
        assert not cast(
            "WorldState",
            await repository.get_record(workspace_id, project_id, CreativeOwner.WORLD, state.id),
        ).current

        chapter = Chapter(
            uuid4(),
            uuid4(),
            1,
            workspace_id,
            project_id,
            work.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            "fixture-chapter://one",
            0,
            actor_id,
            now,
        )
        await repository.add_proposal(chapter, event(work.id, "creative.novel.record-proposed"))
        rejected = await repository.decide_proposal(
            workspace_id,
            project_id,
            CreativeOwner.NOVEL,
            chapter.id,
            decision=CreativeDecision.REJECT,
            expected_container_version=1,
            decided_by=actor_id,
            decided_at=now,
            event=event(work.id, "creative.novel.record-decided"),
        )
        assert rejected.status is CreativeRecordStatus.REJECTED

        causation_id, source_event_id = uuid4(), uuid4()
        impact = ImpactLink(
            uuid4(),
            uuid4(),
            1,
            workspace_id,
            project_id,
            world.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            None,
            None,
            actor_id,
            now,
            causation_id,
            source_event_id,
        )
        first_impact, first_created = await repository.add_proposal(
            impact, event(world.id, "creative.world.impact-proposed")
        )
        replay_impact, replay_created = await repository.add_proposal(
            replace(impact, id=uuid4(), logical_id=uuid4()),
            event(world.id, "creative.world.impact-proposed"),
        )
        assert first_created and first_impact == replay_impact and not replay_created

        behavior = BehaviorProposal(
            uuid4(),
            uuid4(),
            1,
            workspace_id,
            project_id,
            character.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            None,
            None,
            actor_id,
            now,
        )
        style = StyleProfile(
            uuid4(),
            uuid4(),
            1,
            workspace_id,
            project_id,
            profile.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (),
            None,
            None,
            actor_id,
            now,
        )
        for item in (behavior, style):
            persisted, item_created = await repository.add_proposal(
                item,
                event(item.aggregate_id, f"creative.{item.owner.value}.record-proposed"),
            )
            assert item_created and persisted == item

        invalid_scope = replace(
            behavior,
            id=uuid4(),
            logical_id=uuid4(),
            project_id=uuid4(),
        )
        with pytest.raises(DBAPIError):
            await repository.add_proposal(
                invalid_scope,
                event(
                    invalid_scope.aggregate_id,
                    "creative.character.record-proposed",
                    event_project_id=invalid_scope.project_id,
                ),
            )

        async with runtime.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(CreativeContainerRow)) == 4
            assert await session.scalar(select(func.count()).select_from(CreativeRecordRow)) == 6
        await runtime.shutdown()

    asyncio.run(exercise(), loop_factory=asyncio.SelectorEventLoop)


def test_model_and_tool_ledgers_are_scoped_append_only_and_payload_free(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 1, 1, 60),
        )
        model_ledger = SqlAlchemyUsageLedger(runtime.sessions)
        tool_ledger = SqlAlchemyToolCallLedger(runtime.sessions)
        workspace_id, other_workspace = uuid4(), uuid4()
        workflow_id, task_id, actor_id, correlation_id = uuid4(), uuid4(), uuid4(), uuid4()
        model_record = UsageRecord(
            uuid4(),
            workspace_id,
            uuid4(),
            workflow_id,
            task_id,
            actor_id,
            correlation_id,
            "fixture-model-ledger",
            ModelCapability.TEXT,
            "fake-model",
            ModelCallStatus.SUCCEEDED,
            None,
            True,
            1,
            2,
            3,
            datetime(2026, 9, 5, tzinfo=UTC),
            datetime(2026, 9, 5, tzinfo=UTC),
        )
        denied_record = replace(
            model_record,
            id=uuid4(),
            idempotency_key="fixture-model-denied",
            attempted=False,
            status=ModelCallStatus.BUDGET_DENIED,
            provider_id=None,
            input_tokens=0,
            output_tokens=0,
        )
        await model_ledger.append(model_record)
        await model_ledger.append(denied_record)
        totals = await model_ledger.totals(workspace_id, task_id)
        assert totals.workspace_tokens == 5
        assert totals.workspace_calls == 1
        assert totals.task_tokens == 5
        assert totals.task_calls == 1
        stored_models = await model_ledger.for_workflow(workspace_id, workflow_id)
        assert {item.id for item in stored_models} == {model_record.id, denied_record.id}
        assert {item.status for item in stored_models} == {
            ModelCallStatus.SUCCEEDED,
            ModelCallStatus.BUDGET_DENIED,
        }
        assert await model_ledger.for_workflow(other_workspace, workflow_id) == ()

        tool_record = ToolCallRecord(
            uuid4(),
            workspace_id,
            uuid4(),
            workflow_id,
            task_id,
            actor_id,
            correlation_id,
            "fixture-tool-ledger",
            "fixture.reference",
            "1.0.0",
            ToolCallStatus.SUCCEEDED,
            None,
            datetime(2026, 9, 5, tzinfo=UTC),
            datetime(2026, 9, 5, tzinfo=UTC),
        )
        await tool_ledger.append(tool_record)
        assert await tool_ledger.for_workflow(workspace_id, workflow_id) == (tool_record,)
        assert await tool_ledger.for_workflow(other_workspace, workflow_id) == ()

        assert "credential" not in ModelUsageRecordRow.__table__.columns
        assert "input_data" not in ToolCallRecordRow.__table__.columns
        async with runtime.sessions.begin() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    text("UPDATE accos.model_usage_records SET status = 'failed' WHERE id = :id"),
                    {"id": model_record.id},
                )
        async with runtime.sessions.begin() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    text("DELETE FROM accos.tool_call_records WHERE id = :id"),
                    {"id": tool_record.id},
                )
        await runtime.shutdown()

    asyncio.run(exercise(), loop_factory=asyncio.SelectorEventLoop)


def test_agent_director_framework_smoke_persists_runtime_gateway_and_workflow_trace(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(3, 1, 1, 60))
        clock = MutableClock(datetime(2026, 9, 5, 1, tzinfo=UTC))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, clock.now())
            permissions = permissions_for(Role.OWNER)
            security = SecurityContext(
                actor_id,
                ActorKind.USER,
                workspace_id,
                permissions,
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
                project_id,
            )
            authorizer = AuthorizationService(SqlAlchemyAuditStore(runtime.sessions), clock)
            project_repository = SqlAlchemyProjectRepository(runtime.sessions)
            workflow_repository = SqlAlchemyWorkflowRepository(runtime.sessions)
            model_registry = ModelRegistry()
            model_registry.register(FakeModelProvider())
            model_ledger = SqlAlchemyUsageLedger(runtime.sessions)
            model_gateway = ModelGateway(
                model_registry,
                model_ledger,
                authorizer,
                clock,
                ModelPolicy(("fake-model",), "fake-model"),
            )
            tool_registry = ToolRegistry()
            tool_descriptor = ToolDescriptor(
                "fixture.reference",
                "1.0.0",
                ("reference",),
                {
                    "type": "object",
                    "properties": {"reference": {"type": "string"}},
                    "required": ["reference"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {"reference": {"type": "string"}},
                    "required": ["reference"],
                    "additionalProperties": False,
                },
                frozenset({Permission.TOOL_RUN.value}),
            )
            tool_registry.register(tool_descriptor, FakeToolExecutor())
            tool_ledger = SqlAlchemyToolCallLedger(runtime.sessions)
            tool_gateway = ToolGateway(tool_registry, tool_ledger, authorizer, clock)
            agent_registry = InMemoryAgentRegistry()
            for descriptor in built_in_agent_descriptors():
                agent_registry.register(descriptor)
            agent_repository = SqlAlchemyAgentRepository(runtime.sessions)
            agent_metrics = InMemoryAgentMetrics()
            agent_executor = FakeAgentExecutor(model_gateway, tool_gateway)
            agent_supervisor = DefaultAgentSupervisor(
                agent_registry,
                agent_executor,
                agent_repository,
                project_repository,
                authorizer,
                agent_metrics,
                clock,
                DEFAULT_AGENT_BUDGET,
                {tool_descriptor.tool_id: tool_descriptor.version},
            )
            worker = WorkflowWorker(
                workflow_repository,
                AgentWorkflowExecutor(
                    FrameworkSmokeExecutor(),
                    agent_supervisor,
                    AgentBudget(2, 1, 1, 10.0, 2, 64),
                ),
                clock,
            )
            service = WorkflowService(workflow_repository, project_repository, authorizer, clock)
            master = MasterOrchestrator(agent_supervisor, service, agent_repository)
            queue = InMemoryTaskQueue()
            relay = OutboxRelay(
                SqlAlchemyOutboxRepository(runtime.sessions, clock),
                queue,
            )
            orchestrated = await master.submit_goal(
                security,
                project_id,
                idempotency_key="fixture-stage10-smoke",
                goal_reference="fixture-goal://technical",
                budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
            )
            replay = await master.submit_goal(
                security,
                project_id,
                idempotency_key="fixture-stage10-smoke",
                goal_reference="fixture-goal://technical",
                budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
            )
            run = orchestrated.workflow_run
            assert replay.agent_run.id == orchestrated.agent_run.id
            assert replay.workflow_run.id == run.id
            delivered = 0
            for _ in range(5):
                await relay.run_once()
                new_events = queue.deliveries[delivered:]
                delivered = len(queue.deliveries)
                for event in new_events:
                    disposition = await worker.handle(event)
                    if disposition is WorkerDisposition.RETRY_SCHEDULED:
                        clock.advance(seconds=1)
                current = await service.get(security, run.id)
                if current.status is WorkflowRunStatus.SUCCEEDED:
                    break

            completed = await service.get(security, run.id)
            assert completed.status is WorkflowRunStatus.SUCCEEDED
            assert completed.permission_snapshot == tuple(sorted(permissions))
            assert completed.policy_version == POLICY_VERSION
            director = await agent_repository.get(workspace_id, orchestrated.agent_run.id)
            assert director is not None
            assert director.workflow_run_id == run.id
            assert director.status is AgentRunStatus.SUCCEEDED
            director_snapshot = await agent_repository.get_snapshot(
                workspace_id, director.context_snapshot_id
            )
            assert director_snapshot is not None
            assert director_snapshot.agent_version == "1.0.0"
            assert director_snapshot.model_policy_version == "1.0.0"
            assert len(director_snapshot.input_digest) == 64
            assert (
                await agent_repository.get_snapshot(uuid4(), director.context_snapshot_id) is None
            )
            quality = await agent_repository.get_by_idempotency(
                workspace_id, f"{run.id}:pass-token-agent"
            )
            assert quality is not None
            assert quality.status is AgentRunStatus.SUCCEEDED
            replay_quality = await agent_supervisor.run(
                security,
                project_id,
                AgentInvocation(
                    "quality",
                    {"input_reference": run.input_reference},
                    quality.idempotency_key,
                    quality.task_reference,
                    AgentBudget(2, 1, 1, 10.0, 2, 64),
                    recursion_depth=1,
                    planning_path=("director",),
                    requested_tool_ids=("fixture.reference",),
                    workflow_run_id=run.id,
                    task_run_id=UUID(quality.task_reference.rsplit("/", maxsplit=1)[1]),
                ),
            )
            assert replay_quality.run == quality
            agent_events = await agent_repository.get_events(workspace_id, quality.id)
            assert [event.sequence for event in agent_events] == [1, 2]
            assert await agent_repository.get_events(uuid4(), quality.id) == ()
            model_calls = await model_ledger.for_workflow(workspace_id, run.id)
            tool_calls = await tool_ledger.for_workflow(workspace_id, run.id)
            assert len(model_calls) == 1
            assert model_calls[0].status is ModelCallStatus.SUCCEEDED
            assert len(tool_calls) == 1
            assert tool_calls[0].status is ToolCallStatus.SUCCEEDED
            assert model_calls[0].task_run_id == tool_calls[0].task_run_id
            assert model_calls[0].correlation_id == run.correlation_id
            assert tool_calls[0].correlation_id == run.correlation_id
            assert len(agent_executor.calls) == 2
            assert agent_metrics.transitions.count(("quality", AgentRunStatus.SUCCEEDED)) == 1

            def pending_agent(key: str) -> tuple[AgentRun, AgentContextSnapshot]:
                snapshot_id = uuid4()
                snapshot = AgentContextSnapshot(
                    snapshot_id,
                    workspace_id,
                    project_id,
                    "world",
                    "1.0.0",
                    "fake-agent-model-policy",
                    "1.0.0",
                    "agent.world.metadata",
                    "1.0.0",
                    "0" * 64,
                    (),
                    tuple(sorted(permissions)),
                    "1" * 64,
                    clock.now(),
                )
                return (
                    AgentRun(
                        uuid4(),
                        workspace_id,
                        project_id,
                        "world",
                        "1.0.0",
                        snapshot_id,
                        AgentRunStatus.RUNNING,
                        1,
                        key,
                        f"agent-task://world/{key}",
                        actor_id,
                        run.correlation_id,
                        clock.now(),
                        clock.now(),
                    ),
                    snapshot,
                )

            raw = RawAgentResult(
                {"kind": "proposal", "result_reference": "proposal://fixture"},
                "proposal://fixture",
                0,
                0,
                0,
            )
            assert (
                await agent_repository.complete(
                    director.id, AgentProposal("proposal://fixture"), raw
                )
            ).status is AgentRunStatus.SUCCEEDED
            failed_run, failed_snapshot = pending_agent("fixture-agent-failed")
            await agent_repository.begin(
                failed_run, failed_snapshot, request_digest="fixture-agent-failed-digest"
            )
            failed = await agent_repository.fail(
                failed_run.id,
                AgentRunStatus.FAILED,
                AgentRuntimeError(AgentErrorCode.EXECUTION_FAILED),
            )
            assert failed.error_code is AgentErrorCode.EXECUTION_FAILED
            assert (
                await agent_repository.fail(
                    failed_run.id,
                    AgentRunStatus.REJECTED,
                    AgentRuntimeError(AgentErrorCode.TOOL_DENIED),
                )
            ) == failed
            assert (
                await agent_repository.complete(
                    failed_run.id, AgentProposal("proposal://fixture"), raw
                )
            ) == failed
            waiting_run, waiting_snapshot = pending_agent("fixture-agent-waiting")
            await agent_repository.begin(
                waiting_run, waiting_snapshot, request_digest="fixture-agent-waiting-digest"
            )
            waiting = await agent_repository.attach_workflow(
                workspace_id, waiting_run.id, run.id, waiting=True
            )
            assert waiting.status is AgentRunStatus.WAITING_APPROVAL
            with pytest.raises(ScopeViolationError):
                await agent_repository.attach_workflow(uuid4(), director.id, run.id, waiting=False)
            with pytest.raises(InvalidStateError, match="another"):
                await agent_repository.attach_workflow(
                    workspace_id, quality.id, uuid4(), waiting=False
                )
            with pytest.raises(InvalidStateError, match="unavailable"):
                await agent_repository.complete(uuid4(), AgentProposal("proposal://fixture"), raw)
            assert await agent_repository.get(workspace_id, uuid4()) is None
            assert await agent_repository.get_by_idempotency(workspace_id, "missing") is None

            orphan_id = uuid4()
            async with runtime.sessions.begin() as session:
                await SqlAlchemyIdempotencyStore(session).reserve(
                    IdempotencyRecord(
                        uuid4(),
                        workspace_id,
                        project_id,
                        "agents.run",
                        "fixture-agent-orphan",
                        "fixture-agent-orphan-digest",
                        str(orphan_id),
                        clock.now() + timedelta(days=1),
                    )
                )
            orphan_run, orphan_snapshot = pending_agent("fixture-agent-orphan")
            with pytest.raises(InvalidStateError, match="Idempotent Agent"):
                await agent_repository.begin(
                    orphan_run,
                    orphan_snapshot,
                    request_digest="fixture-agent-orphan-digest",
                )

            plan_executor = FakeAgentExecutor(
                model_gateway,
                tool_gateway,
                {
                    "fixture-agent-plan-reject": FakeAgentBehavior(
                        {
                            "kind": AgentResultKind.WORKFLOW_PLAN_PROPOSAL.value,
                            "workflow_name": "fixture-protected",
                            "workflow_version": 1,
                            "input_reference": "proposal://fixture-protected",
                            "protected_operations": [ProtectedOperation.DELETE.value],
                            "approval_required": True,
                        }
                    )
                },
            )
            plan_supervisor = DefaultAgentSupervisor(
                agent_registry,
                plan_executor,
                agent_repository,
                project_repository,
                authorizer,
                agent_metrics,
                clock,
                DEFAULT_AGENT_BUDGET,
                {tool_descriptor.tool_id: tool_descriptor.version},
            )
            plan_master = MasterOrchestrator(plan_supervisor, service, agent_repository)
            plan = await plan_master.submit_goal(
                security,
                project_id,
                idempotency_key="fixture-agent-plan-reject",
                goal_reference="fixture-goal://protected",
                budget=AgentBudget(2, 1, 1, 10.0, 1, 64),
            )
            assert plan.workflow_run.status is WorkflowRunStatus.WAITING_APPROVAL
            approver = replace(
                security,
                actor_id=uuid4(),
                correlation=CorrelationIds(str(uuid4()), str(uuid4())),
            )
            rejected = await plan_master.decide_plan(
                approver,
                plan.agent_run.id,
                WorkflowApprovalDecision.REJECT,
                reason="fixture-rejected",
            )
            assert rejected.workflow_run.status is WorkflowRunStatus.FAILED
            assert rejected.agent_run.status is AgentRunStatus.REJECTED
            assert (
                await agent_repository.settle_approval(
                    workspace_id, plan.agent_run.id, approved=False
                )
            ) == rejected.agent_run
            with pytest.raises(ScopeViolationError):
                await agent_repository.settle_approval(uuid4(), plan.agent_run.id, approved=False)
            with pytest.raises(InvalidStateError, match="not waiting"):
                await agent_repository.settle_approval(workspace_id, director.id, approved=True)

            async with runtime.sessions() as session:
                assert await row_count(session, AgentRunRow) == 5
                assert await row_count(session, AgentContextSnapshotRow) == 5
                assert await row_count(session, AgentRunEventRow) == 13
            async with runtime.sessions.begin() as session:
                with pytest.raises(DBAPIError):
                    await session.execute(
                        text(
                            "UPDATE accos.agent_context_snapshots "
                            "SET agent_version = '2.0.0' WHERE id = :id"
                        ),
                        {"id": director.context_snapshot_id},
                    )
            async with runtime.sessions.begin() as session:
                with pytest.raises(DBAPIError):
                    await session.execute(
                        text("DELETE FROM accos.agent_run_events WHERE agent_run_id = :id"),
                        {"id": quality.id},
                    )
        finally:
            await runtime.shutdown()

    asyncio.run(exercise(), loop_factory=asyncio.SelectorEventLoop)


def event(*, occurred_at: datetime, identifier: UUID | None = None) -> EventEnvelope:
    return EventEnvelope(
        id=identifier or uuid4(),
        workspace_id=uuid4(),
        project_id=uuid4(),
        aggregate_id=uuid4(),
        event_type="fixture.created",
        version=1,
        payload={"value": "fixture-document"},
        occurred_at=occurred_at,
    )


def idempotency_record(*, workspace_id: UUID, digest: str = "fixture-digest") -> IdempotencyRecord:
    return IdempotencyRecord(
        id=uuid4(),
        workspace_id=workspace_id,
        project_id=uuid4(),
        scope="fixture-scope",
        key="fixture-key",
        request_digest=digest,
        result_reference="fixture-result",
        expires_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


async def row_count(session: AsyncSession, model: type[object]) -> int:
    return int((await session.scalar(select(func.count()).select_from(model))) or 0)


def test_uow_commit_rollback_and_outbox_share_one_transaction(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 1, 1.0, 60),
        )
        workspace_id = uuid4()
        committed_event = event(occurred_at=datetime(2026, 9, 3, tzinfo=UTC))
        rolled_back_event = event(occurred_at=datetime(2026, 9, 3, tzinfo=UTC))
        try:
            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                stored, created = await SqlAlchemyIdempotencyStore(uow.session).reserve(
                    idempotency_record(workspace_id=workspace_id)
                )
                sequence = await SqlAlchemyOutboxWriter(uow.session).append(committed_event)
                assert stored.workspace_id == workspace_id
                assert created
                assert sequence == 1
                await uow.commit()

            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                await SqlAlchemyOutboxWriter(uow.session).append(rolled_back_event)

            async with runtime.sessions() as session:
                assert await row_count(session, IdempotencyRecordRow) == 1
                assert await row_count(session, OutboxEventRow) == 1
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_unit_of_work_guards_state_and_supports_explicit_rollback(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(1, 0, 1.0, 60),
        )
        uow = SqlAlchemyUnitOfWork(runtime.sessions)
        try:
            with pytest.raises(InvalidStateError, match="not active"):
                _ = uow.session
            async with uow:
                with pytest.raises(InvalidStateError, match="already active"):
                    await uow.__aenter__()
                await SqlAlchemyOutboxWriter(uow.session).append(
                    event(occurred_at=datetime(2026, 9, 3, tzinfo=UTC))
                )
                await uow.rollback()
            async with runtime.sessions() as session:
                assert await row_count(session, OutboxEventRow) == 0
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_idempotency_replay_conflict_and_workspace_scope(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(1, 0, 1.0, 60),
        )
        workspace_id = uuid4()
        record = idempotency_record(workspace_id=workspace_id)
        try:
            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                store = SqlAlchemyIdempotencyStore(uow.session)
                first, first_created = await store.reserve(record)
                replay, replay_created = await store.reserve(replace(record, id=uuid4()))
                assert first == replay
                assert first_created
                assert not replay_created
                assert (
                    await store.get(workspace_id=uuid4(), scope=record.scope, key=record.key)
                    is None
                )
                with pytest.raises(IdempotencyConflictError):
                    await store.reserve(
                        replace(record, id=uuid4(), request_digest="different-digest")
                    )
                await uow.commit()
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_optimistic_concurrency_conflict_is_stable(migrated_database_url: str) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 0, 1.0, 60),
        )
        identifier = uuid4()
        workspace_id = uuid4()
        try:
            async with SqlAlchemyUnitOfWork(runtime.sessions) as seed:
                await SqlAlchemyIdempotencyStore(seed.session).reserve(
                    replace(idempotency_record(workspace_id=workspace_id), id=identifier)
                )
                await seed.commit()

            async with (
                SqlAlchemyUnitOfWork(runtime.sessions) as first,
                SqlAlchemyUnitOfWork(runtime.sessions) as second,
            ):
                first_row = await first.session.get(IdempotencyRecordRow, identifier)
                second_row = await second.session.get(IdempotencyRecordRow, identifier)
                assert first_row is not None and second_row is not None
                first_row.result_reference = "fixture-first"
                second_row.result_reference = "fixture-second"
                await first.commit()
                with pytest.raises(ConcurrencyConflictError):
                    await second.commit()
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_relay_recovers_expired_lease_without_duplicate_visible_effect(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 0, 1.0, 60),
        )
        clock = MutableClock(datetime(2026, 9, 3, tzinfo=UTC))
        publisher = InMemoryPublisher()
        repository = SqlAlchemyOutboxRepository(
            runtime.sessions,
            clock,
            batch_size=10,
            lease_seconds=5,
            retry_seconds=2,
        )
        envelope = event(occurred_at=clock.now())
        try:
            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                await SqlAlchemyOutboxWriter(uow.session).append(envelope)
                await uow.commit()

            interrupted_claim = (await repository.claim())[0]
            await publisher.publish(interrupted_claim.event)
            clock.advance(seconds=6)

            report = await OutboxRelay(repository, publisher).run_once()
            empty_report = await OutboxRelay(repository, publisher).run_once()

            assert report.published == 1
            assert report.cursor == interrupted_claim.sequence
            assert publisher.visible_events == (envelope,)
            assert empty_report.claimed == 0
            assert empty_report.cursor is None
            async with runtime.sessions() as session:
                row = await session.get(OutboxEventRow, envelope.id)
                assert row is not None
                assert row.status == PUBLISHED_STATUS
                assert row.attempt_count == 2
                assert row.published_at == clock.now()
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_relay_failure_retry_and_lease_token_protection(migrated_database_url: str) -> None:
    class FailOncePublisher:
        def __init__(self) -> None:
            self.calls = 0

        async def publish(self, _event: EventEnvelope) -> None:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("fixture transport failure")

    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(2, 0, 1.0, 60),
        )
        clock = MutableClock(datetime(2026, 9, 3, tzinfo=UTC))
        repository = SqlAlchemyOutboxRepository(
            runtime.sessions,
            clock,
            batch_size=1,
            lease_seconds=5,
            retry_seconds=2,
        )
        envelope = event(occurred_at=clock.now())
        try:
            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                await SqlAlchemyOutboxWriter(uow.session).append(envelope)
                await uow.commit()

            claimed = (await repository.claim())[0]
            wrong_claim = replace(claimed, lease_token=uuid4())
            assert not await repository.acknowledge(wrong_claim)
            assert not await repository.fail(wrong_claim)
            assert await repository.fail(claimed, error_code="x" * 150)

            clock.advance(seconds=2)
            publisher = FailOncePublisher()
            first_report = await OutboxRelay(repository, publisher).run_once()
            assert first_report.failed == 1
            clock.advance(seconds=2)
            second_report = await OutboxRelay(repository, publisher).run_once()
            assert second_report.published == 1

            async with runtime.sessions() as session:
                row = await session.get(OutboxEventRow, envelope.id)
                assert row is not None
                assert row.status == PUBLISHED_STATUS
                assert row.last_error_code is None
                assert row.attempt_count == 3
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_database_readiness_and_contract_value_validation(migrated_database_url: str) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(
            migrated_database_url,
            EngineOptions(1, 0, 1.0, 60),
        )
        try:
            await runtime.startup()
            result = await DatabaseHealthProbe(runtime.engine).check()
            assert result.detail == "query_ok"
            with pytest.raises(ValueError, match="positive"):
                SqlAlchemyOutboxRepository(
                    runtime.sessions,
                    MutableClock(datetime.now(tz=UTC)),
                    batch_size=0,
                )
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)

    page = Page(("fixture",), 2, PageRequest(limit=1))
    assert page.next_offset == 1
    assert Page(("fixture",), 1, PageRequest(limit=1)).next_offset is None
    with pytest.raises(ValueError, match="page total"):
        Page(("one", "two"), 1, PageRequest())

    with pytest.raises(ValueError, match="event type"):
        replace(event(occurred_at=datetime.now(tz=UTC)), event_type=" ")
    with pytest.raises(ValueError, match="event version"):
        replace(event(occurred_at=datetime.now(tz=UTC)), version=0)
    with pytest.raises(ValueError, match="event timestamp"):
        event(occurred_at=datetime(2026, 9, 3))

    valid_record = idempotency_record(workspace_id=uuid4())
    with pytest.raises(ValueError, match="fields"):
        replace(valid_record, scope="")
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(valid_record, expires_at=datetime(2026, 9, 4))

    source = GraphNodeRef(uuid4(), "fixture-owner", "fixture-kind", uuid4())
    target = GraphNodeRef(source.workspace_id, "fixture-owner", "fixture-kind", uuid4())
    assert GraphEdge(source, target, "fixture-related").source == source


def test_relay_does_not_count_a_stale_acknowledgement_as_published() -> None:
    claimed = event(occurred_at=datetime(2026, 9, 3, tzinfo=UTC))

    class StaleLeaseRepository:
        async def claim(self) -> tuple[ClaimedEvent, ...]:
            return (ClaimedEvent(claimed, 1, uuid4()),)

        async def acknowledge(self, _claimed: ClaimedEvent) -> bool:
            return False

        async def fail(self, _claimed: ClaimedEvent, *, error_code: str = "publish_failed") -> bool:
            del error_code
            raise AssertionError("failure settlement is not expected")

    report = asyncio.run(OutboxRelay(StaleLeaseRepository(), InMemoryPublisher()).run_once())

    assert report == RelayReport(claimed=1, published=0, failed=1, cursor=1)


def test_identity_repositories_enforce_workspace_scope_and_append_only_audit(
    migrated_database_url: str,
) -> None:
    async def scenario() -> tuple[UUID, UUID]:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1.0, 60))
        user_a, user_b = uuid4(), uuid4()
        workspace_a, workspace_b = uuid4(), uuid4()
        service_id = uuid4()
        try:
            async with runtime.sessions.begin() as session:
                session.add_all(
                    [
                        UserRow(
                            id=user_a,
                            issuer="fixture-issuer",
                            subject="fixture-a",
                            active=True,
                        ),
                        UserRow(
                            id=user_b,
                            issuer="fixture-issuer",
                            subject="fixture-b",
                            active=True,
                        ),
                        WorkspaceRow(id=workspace_a, owner_user_id=user_a),
                        WorkspaceRow(id=workspace_b, owner_user_id=user_b),
                    ]
                )
            async with runtime.sessions.begin() as session:
                session.add_all(
                    [
                        MembershipRow(
                            id=uuid4(),
                            workspace_id=workspace_a,
                            user_id=user_a,
                            role=Role.OWNER,
                        ),
                        MembershipRow(
                            id=uuid4(),
                            workspace_id=workspace_b,
                            user_id=user_b,
                            role=Role.VIEWER,
                        ),
                        ServiceIdentityRow(
                            id=service_id,
                            workspace_id=workspace_a,
                            name="fixture-service",
                            permissions=[
                                Permission.AGENT_RUN.value,
                                Permission.OWNERSHIP_TRANSFER.value,
                            ],
                        ),
                    ]
                )

            identities = SqlAlchemyIdentityRepository(runtime.sessions)
            assert await identities.find_user("fixture-issuer", "fixture-a") is not None
            assert await identities.find_user("fixture-issuer", "missing") is None
            assert await identities.get_membership(workspace_a, user_a) is not None
            assert await identities.get_membership(workspace_a, user_b) is None
            assert (await identities.get_workspace(workspace_a)).owner_user_id == user_a  # type: ignore[union-attr]
            assert await identities.get_workspace(uuid4()) is None
            membership_page = await identities.list_memberships(workspace_a, PageRequest(0, 1))
            assert membership_page.total == 1
            assert membership_page.items[0].user_id == user_a
            service = await identities.get_service_identity(workspace_a, service_id)
            assert service is not None
            assert service.permissions == {
                Permission.AGENT_RUN,
                Permission.OWNERSHIP_TRANSFER,
            }
            assert await identities.get_service_identity(workspace_b, service_id) is None

            audit = SqlAlchemyAuditStore(runtime.sessions)
            for workspace_id, actor_id in ((workspace_a, user_a), (workspace_b, user_b)):
                await audit.append(
                    AuditEvent(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        actor_id=actor_id,
                        actor_kind=ActorKind.USER,
                        action=Permission.WORKSPACE_READ,
                        resource_type="workspace",
                        resource_id=str(workspace_id),
                        result="allowed",
                        reason_code="policy_allow",
                        policy_version=POLICY_VERSION,
                        correlation_id=uuid4(),
                        occurred_at=datetime(2026, 9, 3, tzinfo=UTC),
                        metadata={
                            "operation_code": "x" * 120,
                            "password": "fixture-secret",
                        },
                    )
                )
            events_a = await audit.list_for_workspace(workspace_a)
            events_b = await audit.list_for_workspace(workspace_b)
            assert len(events_a) == len(events_b) == 1
            assert events_a[0].workspace_id == workspace_a
            assert events_b[0].workspace_id == workspace_b
            assert events_a[0].metadata == {"operation_code": "x" * 100}
            return events_a[0].id, workspace_a
        finally:
            await runtime.shutdown()

    audit_id, workspace_id = asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)
    sync_url = make_url(migrated_database_url).set(drivername="postgresql")
    with psycopg.connect(sync_url.render_as_string(hide_password=False)) as connection:
        with pytest.raises(psycopg.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE accos.audit_events SET result = 'denied' WHERE id = %s",
                (audit_id,),
            )
        connection.rollback()
        with pytest.raises(psycopg.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM accos.audit_events WHERE workspace_id = %s",
                (workspace_id,),
            )


def test_authorization_denial_has_only_sanitized_audit_side_effect(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1.0, 60))
        workspace_id, actor_id, correlation_id = uuid4(), uuid4(), uuid4()
        security_context = SecurityContext(
            actor_id,
            ActorKind.USER,
            workspace_id,
            permissions_for(Role.VIEWER),
            POLICY_VERSION,
            CorrelationIds(str(correlation_id), str(uuid4())),
        )
        authorizer = AuthorizationService(
            SqlAlchemyAuditStore(runtime.sessions),
            MutableClock(datetime(2026, 9, 3, tzinfo=UTC)),
        )
        try:
            with pytest.raises(PermissionDeniedError):
                await authorizer.authorize(
                    AuthorizationRequest(
                        security_context,
                        Permission.WORKSPACE_WRITE,
                        ResourceScope(workspace_id, "workspace", str(workspace_id)),
                    )
                )
            async with runtime.sessions() as session:
                assert await row_count(session, AuditEventRow) == 1
                assert await row_count(session, ControlRequestRow) == 0
                assert await row_count(session, OutboxEventRow) == 0
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_control_requests_are_scoped_and_human_decisions_are_one_time(
    migrated_database_url: str,
) -> None:
    async def scenario() -> tuple[UUID, UUID]:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1.0, 60))
        store = SqlAlchemyControlRequestStore(runtime.sessions)
        workspace_id, request_id = uuid4(), uuid4()
        request = ControlRequest(
            request_id,
            workspace_id,
            uuid4(),
            ControlRequestKind.DELETE,
            "workspace",
            str(workspace_id),
            "request-delete",
            "irreversible",
            ControlRequestStatus.PENDING,
            uuid4(),
            datetime(2026, 9, 3, tzinfo=UTC),
        )
        try:
            await store.add_request(request)
            assert await store.get_request(workspace_id, request_id) == request
            assert await store.get_request(uuid4(), request_id) is None
            approval = HumanApproval(
                uuid4(),
                workspace_id,
                request_id,
                uuid4(),
                ApprovalDecision.APPROVE,
                uuid4(),
                datetime(2026, 9, 3, 1, tzinfo=UTC),
            )
            await store.add_approval(approval)
            decided = await store.get_request(workspace_id, request_id)
            assert decided is not None
            assert decided.status is ControlRequestStatus.APPROVED
            with pytest.raises(InvalidStateError, match="pending"):
                await store.add_approval(replace(approval, id=uuid4()))
            with pytest.raises(InvalidStateError, match="unavailable"):
                await store.add_approval(replace(approval, id=uuid4(), request_id=uuid4()))

            rejected_request = replace(
                request,
                id=uuid4(),
                kind=ControlRequestKind.ARCHIVE,
                status=ControlRequestStatus.PENDING,
            )
            await store.add_request(rejected_request)
            await store.add_approval(
                replace(
                    approval,
                    id=uuid4(),
                    request_id=rejected_request.id,
                    decision=ApprovalDecision.REJECT,
                )
            )
            rejected = await store.get_request(workspace_id, rejected_request.id)
            assert rejected is not None
            assert rejected.status is ControlRequestStatus.REJECTED
            async with runtime.sessions() as session:
                assert await row_count(session, HumanApprovalRow) == 2
            return approval.id, workspace_id
        finally:
            await runtime.shutdown()

    approval_id, workspace_id = asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)
    sync_url = make_url(migrated_database_url).set(drivername="postgresql")
    with (
        psycopg.connect(sync_url.render_as_string(hide_password=False)) as connection,
        pytest.raises(psycopg.IntegrityError, match="append-only"),
    ):
        connection.execute(
            "DELETE FROM accos.identity_human_approvals WHERE id = %s AND workspace_id = %s",
            (approval_id, workspace_id),
        )


def test_development_identity_runtime_is_explicit_idempotent_and_fail_closed(
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1.0, 60))
        actor_id, approver_id, workspace_id = uuid4(), uuid4(), uuid4()
        disabled = IdentityRuntime(runtime.sessions)
        try:
            await disabled.startup()
            async with runtime.sessions() as session:
                assert await row_count(session, UserRow) == 0
            await disabled.shutdown()

            enabled = IdentityRuntime(
                runtime.sessions,
                actor_id=actor_id,
                workspace_id=workspace_id,
                approver_actor_id=approver_id,
                enabled=True,
            )
            await enabled.startup()
            await enabled.startup()
            identities = SqlAlchemyIdentityRepository(runtime.sessions)
            user = await identities.find_user("urn:accos:development", "local-development")
            membership = await identities.get_membership(workspace_id, actor_id)
            approver = await identities.find_user(
                "urn:accos:development", "local-development-approver"
            )
            approver_membership = await identities.get_membership(workspace_id, approver_id)
            assert user is not None and user.id == actor_id
            assert membership is not None and membership.role is Role.OWNER
            assert approver is not None and approver.id == approver_id
            assert approver_membership is not None and approver_membership.role is Role.OWNER
            await enabled.shutdown()

            primary_only = IdentityRuntime(
                runtime.sessions,
                actor_id=actor_id,
                workspace_id=workspace_id,
                enabled=True,
            )
            await primary_only.startup()
            await primary_only.shutdown()

            with pytest.raises(ConfigurationError, match="IDs must be configured"):
                await IdentityRuntime(runtime.sessions, enabled=True).startup()
            with pytest.raises(ConfigurationError, match="approver actor ID must differ"):
                await IdentityRuntime(
                    runtime.sessions,
                    actor_id=actor_id,
                    workspace_id=workspace_id,
                    approver_actor_id=actor_id,
                    enabled=True,
                ).startup()
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_memory_repository_is_scoped_versioned_audited_and_agent_traceable(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> tuple[UUID, UUID, UUID]:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(2, 1, 1.0, 60))
        repository = SqlAlchemyMemoryRepository(runtime.sessions)
        now = datetime(2026, 9, 5, 12, tzinfo=UTC)
        actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, now)
        universe_id, creator_id = uuid4(), uuid4()

        def record(  # noqa: PLR0913 - fixture exposes version state explicitly.
            scope: MemoryScope,
            *,
            logical_id: UUID | None = None,
            version: int = 1,
            status: MemoryStatus = MemoryStatus.ACTIVE,
            current: bool = True,
            content: str = "fixture-memory",
        ) -> MemoryRecord:
            return MemoryRecord(
                uuid4(),
                logical_id or uuid4(),
                version,
                workspace_id,
                scope,
                "system",
                content,
                project_id if scope in PROJECT_SCOPES else None,
                universe_id if scope is MemoryScope.UNIVERSE else None,
                creator_id if scope in CREATOR_SCOPES else None,
                now - timedelta(hours=1),
                None,
                now,
                0.8,
                1,
                MemoryProvenance("knowledge_citation", f"knowledge-citation://{uuid4()}"),
                RetentionRule(RetentionKind.KEEP),
                status,
                current,
                actor_id,
                now,
            )

        try:
            project_record = record(MemoryScope.PROJECT, content="fixture-project-memory")
            linked_record = record(MemoryScope.WORKING, content="fixture-working-memory")
            universe_record = record(MemoryScope.UNIVERSE, content="fixture-universe-memory")
            creator_record = record(MemoryScope.CREATOR, content="fixture-creator-memory")
            for item in (project_record, linked_record, universe_record, creator_record):
                await repository.add(item)
            await repository.add(project_record)
            link = MemoryLink(
                uuid4(), workspace_id, project_record.id, linked_record.id, "derived_from", now
            )
            await repository.add(project_record, (link,))
            assert await repository.get_record(workspace_id, project_record.id) == project_record
            assert await repository.get_record(uuid4(), project_record.id) is None
            assert await repository.retrieve((), frozenset(MemoryScope), frozenset()) == ()
            anchors = (
                AllowedAnchor(workspace_id, MemoryScope.PROJECT, project_id),
                AllowedAnchor(workspace_id, MemoryScope.UNIVERSE, universe_id),
                AllowedAnchor(workspace_id, MemoryScope.CREATOR, creator_id),
            )
            selected = await repository.retrieve(
                anchors, frozenset(MemoryScope), frozenset({"system"})
            )
            assert {item.id for item in selected} == {
                project_record.id,
                universe_record.id,
                creator_record.id,
            }
            assert len(await repository.retrieve(anchors, frozenset(MemoryScope), frozenset())) == 3

            grant = MemoryGrant(
                uuid4(),
                workspace_id,
                project_id,
                MemoryAnchorKind.UNIVERSE,
                universe_id,
                actor_id,
                False,
                now,
            )
            await repository.add_grant(grant)
            assert await repository.grants_for(workspace_id, project_id) == (grant,)
            assert await repository.grants_for(uuid4(), project_id) == ()

            candidate = record(
                MemoryScope.PROJECT,
                logical_id=project_record.logical_id,
                version=2,
                status=MemoryStatus.CANDIDATE,
                current=False,
                content="fixture-candidate",
            )
            conflict = MemoryConflict(
                uuid4(),
                workspace_id,
                project_record.id,
                candidate.id,
                ("keep_current", "accept_candidate"),
                MemoryConflictStatus.PENDING,
                actor_id,
                now,
            )
            await repository.add_conflict(candidate, conflict)
            assert await repository.get_conflict(workspace_id, conflict.id) == conflict
            assert await repository.get_conflict(uuid4(), conflict.id) is None
            accepted = await repository.decide_conflict(
                workspace_id,
                conflict.id,
                accepted=True,
                decided_by=actor_id,
                decided_at=now,
            )
            assert accepted.status is MemoryConflictStatus.ACCEPTED
            assert (await repository.get_record(workspace_id, candidate.id)).current  # type: ignore[union-attr]
            with pytest.raises(InvalidStateError, match="pending"):
                await repository.decide_conflict(
                    workspace_id,
                    conflict.id,
                    accepted=True,
                    decided_by=actor_id,
                    decided_at=now,
                )
            with pytest.raises(ScopeViolationError):
                await repository.decide_conflict(
                    workspace_id,
                    uuid4(),
                    accepted=True,
                    decided_by=actor_id,
                    decided_at=now,
                )

            rejected_current = record(MemoryScope.PROJECT, content="fixture-current-two")
            await repository.add(rejected_current)
            rejected_candidate = record(
                MemoryScope.PROJECT,
                logical_id=rejected_current.logical_id,
                version=2,
                status=MemoryStatus.CANDIDATE,
                current=False,
                content="fixture-candidate-two",
            )
            rejected_conflict = replace(
                conflict,
                id=uuid4(),
                current_record_id=rejected_current.id,
                candidate_record_id=rejected_candidate.id,
            )
            await repository.add_conflict(rejected_candidate, rejected_conflict)
            rejected = await repository.decide_conflict(
                workspace_id,
                rejected_conflict.id,
                accepted=False,
                decided_by=actor_id,
                decided_at=now,
            )
            assert rejected.status is MemoryConflictStatus.REJECTED

            archived = await repository.archive(
                workspace_id, linked_record.id, actor_id=actor_id, archived_at=now
            )
            assert archived.status is MemoryStatus.ARCHIVED
            assert (
                await repository.archive(
                    workspace_id, linked_record.id, actor_id=actor_id, archived_at=now
                )
                == archived
            )
            with pytest.raises(ScopeViolationError):
                await repository.archive(workspace_id, uuid4(), actor_id=actor_id, archived_at=now)

            package = ContextPackage(
                uuid4(),
                workspace_id,
                project_id,
                "fixture-task://sql-context",
                100,
                len(candidate.content),
                anchors,
                (
                    ContextItem(
                        candidate.id,
                        candidate.scope,
                        candidate.memory_type,
                        candidate.content,
                        0.8,
                        candidate.provenance,
                    ),
                ),
                (
                    ContextOmission(
                        OmissionReason.BUDGET_EXCEEDED,
                        universe_record.scope,
                        universe_record.memory_type,
                        universe_record.id,
                    ),
                    ContextOmission(
                        OmissionReason.ANCHOR_UNAVAILABLE,
                        MemoryScope.WISDOM,
                        None,
                        None,
                    ),
                ),
                "1" * 64,
                actor_id,
                now,
            )
            await repository.save_package(package)
            assert await repository.get_package(workspace_id, project_id, package.id) == package
            assert await repository.get_package(uuid4(), project_id, package.id) is None

            snapshot = AgentContextSnapshot(
                uuid4(),
                workspace_id,
                project_id,
                "world",
                "1.0.0",
                "fixture-model-policy",
                "1.0.0",
                "agent.world.metadata",
                "1.0.0",
                "0" * 64,
                (),
                (),
                "2" * 64,
                now,
                package.id,
            )
            agent_run = AgentRun(
                uuid4(),
                workspace_id,
                project_id,
                "world",
                "1.0.0",
                snapshot.id,
                AgentRunStatus.RUNNING,
                1,
                "fixture-memory-context-agent",
                "agent-task://memory-context",
                actor_id,
                uuid4(),
                now,
                now,
            )
            agent_repository = SqlAlchemyAgentRepository(runtime.sessions)
            await agent_repository.begin(
                agent_run, snapshot, request_digest="fixture-memory-context-agent-digest"
            )
            stored_snapshot = await agent_repository.get_snapshot(workspace_id, snapshot.id)
            assert stored_snapshot is not None
            assert stored_snapshot.memory_context_package_id == package.id

            async with runtime.sessions() as session:
                assert await row_count(session, MemoryRecordRow) == 7
                assert await row_count(session, MemoryLinkRow) == 1
                assert await row_count(session, MemoryGrantRow) == 1
                assert await row_count(session, MemoryConflictRow) == 2
                assert await row_count(session, MemoryContextPackageRow) == 1
                assert await row_count(session, MemoryEventRow) >= 12
            return package.id, link.id, workspace_id
        finally:
            await runtime.shutdown()

    package_id, link_id, workspace_id = asyncio.run(
        scenario(), loop_factory=asyncio.SelectorEventLoop
    )
    sync_url = make_url(migrated_database_url).set(drivername="postgresql")
    with psycopg.connect(sync_url.render_as_string(hide_password=False)) as connection:
        for statement, parameters in (
            (
                "UPDATE accos.memory_context_packages SET checksum = %s WHERE id = %s",
                ("2" * 64, package_id),
            ),
            ("DELETE FROM accos.memory_links WHERE id = %s", (link_id,)),
            ("DELETE FROM accos.memory_events WHERE workspace_id = %s", (workspace_id,)),
        ):
            with pytest.raises(psycopg.IntegrityError, match="append-only"):
                connection.execute(statement, parameters)
            connection.rollback()


def test_projects_assets_real_repository_chain_is_scoped_versioned_and_audited(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(3, 1, 1.0, 60))
        clock = MutableClock(datetime(2026, 9, 3, 12, tzinfo=UTC))
        actor_a, actor_b = uuid4(), uuid4()
        workspace_a, workspace_b = uuid4(), uuid4()
        try:
            async with runtime.sessions.begin() as session:
                session.add_all(
                    [
                        UserRow(
                            id=actor_a,
                            issuer="fixture-issuer",
                            subject="fixture-project-a",
                        ),
                        UserRow(
                            id=actor_b,
                            issuer="fixture-issuer",
                            subject="fixture-project-b",
                        ),
                    ]
                )
            async with runtime.sessions.begin() as session:
                session.add_all(
                    [
                        WorkspaceRow(id=workspace_a, owner_user_id=actor_a),
                        WorkspaceRow(id=workspace_b, owner_user_id=actor_b),
                    ]
                )
            audit = SqlAlchemyAuditStore(runtime.sessions)
            authorizer = AuthorizationService(audit, clock)
            repository = SqlAlchemyProjectRepository(runtime.sessions)
            projects = ProjectService(repository, authorizer, clock)
            context_a = SecurityContext(
                actor_a,
                ActorKind.USER,
                workspace_a,
                permissions_for(Role.OWNER),
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
            )
            context_b = SecurityContext(
                actor_b,
                ActorKind.USER,
                workspace_b,
                permissions_for(Role.OWNER),
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
            )
            project = await projects.create(
                context_a,
                name="fixture-project",
                settings=ProjectSettings(5, 2),
                idempotency_key="fixture-project-key",
            )
            replay = await projects.create(
                context_a,
                name="fixture-project",
                settings=ProjectSettings(5, 2),
                idempotency_key="fixture-project-key",
            )
            assert replay.id == project.id
            project_page = await repository.list_projects(
                workspace_a,
                PageRequest(0, 1),
                status=ProjectStatus.ACTIVE,
                sort=ProjectSort.NAME,
            )
            assert project_page.items == (project,)
            assert (
                await repository.list_projects(
                    workspace_a,
                    PageRequest(0, 1),
                    status=None,
                    sort=ProjectSort.CREATED_AT_DESC,
                )
            ).total == 1
            assert await repository.get(workspace_b, project.id) is None
            with pytest.raises(ScopeViolationError):
                await projects.get(context_b, project.id)

            updated = await projects.update_settings(
                context_a, project.id, ProjectSettings(6, 2), expected_version=1
            )
            stale_event = EventEnvelope(
                uuid4(),
                workspace_a,
                project.id,
                project.id,
                "projects.project-settings-updated",
                1,
                {"schema": "project-settings-updated.v1"},
                clock.now(),
            )
            with pytest.raises(ConcurrencyConflictError):
                await repository.update_settings(
                    workspace_a,
                    project.id,
                    ProjectSettings(),
                    expected_version=1,
                    event=stale_event,
                )
            artifact = await projects.create_artifact(
                context_a,
                project.id,
                artifact_type=ArtifactType.OTHER,
                label="fixture-document",
            )
            assert await repository.get_artifact(workspace_b, project.id, artifact.id) is None
            revision = await projects.add_artifact_revision(
                context_a,
                project.id,
                artifact.id,
                content_reference="fixture-reference",
                content_hash="0" * 64,
                expected_version=1,
            )
            assert (
                await repository.list_artifacts(
                    workspace_a,
                    project.id,
                    PageRequest(0, 1),
                    sort=ArtifactSort.LABEL,
                )
            ).items[0].id == artifact.id
            assert (
                await repository.list_revisions(
                    workspace_a, project.id, artifact.id, PageRequest(0, 1)
                )
            ).items == (revision,)
            with pytest.raises(ConcurrencyConflictError):
                await repository.add_revision(
                    artifact,
                    revision,
                    expected_version=1,
                    event=EventEnvelope(
                        uuid4(),
                        workspace_a,
                        project.id,
                        artifact.id,
                        "projects.artifact-revision-created",
                        1,
                        {"schema": "artifact-revision-created.v1"},
                        clock.now(),
                    ),
                )

            asset_repository = SqlAlchemyAssetRepository(runtime.sessions)
            storage = InMemoryObjectStorage()
            assets = AssetService(
                asset_repository,
                projects=repository,
                storage=storage,
                scanner=UnconfiguredContentScanner(),
                upload_policy=DefaultUploadSecurityPolicy(max_bytes=64),
                authorizer=authorizer,
                clock=clock,
            )
            data = b"fixture-asset"
            digest = hashlib.sha256(data).hexdigest()
            uploaded = await assets.upload(
                context_a,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=digest,
            )
            assert uploaded.upload is not None
            assert uploaded.upload.status is UploadStatus.COMPLETED
            assert (
                await asset_repository.list_assets(
                    workspace_a,
                    project.id,
                    PageRequest(0, 1),
                    status=AssetStatus.ACTIVE,
                    sort=AssetSort.FILENAME,
                )
            ).items[0][0].id == uploaded.asset.id
            assert (
                await asset_repository.list_assets(
                    workspace_a,
                    project.id,
                    PageRequest(0, 1),
                    status=None,
                    sort=AssetSort.CREATED_AT_DESC,
                )
            ).total == 1
            assert await assets.download(context_a, project.id, uploaded.asset.id) == data
            assert await asset_repository.get(workspace_b, project.id, uploaded.asset.id) is None
            assert await asset_repository.get_upload(workspace_b, uploaded.upload.id) is None
            duplicate = await assets.upload(
                context_a,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=digest,
            )
            assert duplicate.duplicate

            data = b"fixture-asset-version"
            digest = hashlib.sha256(data).hexdigest()
            uploaded = await assets.upload(
                context_a,
                project.id,
                filename="fixture.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=digest,
                asset_id=uploaded.asset.id,
            )
            assert uploaded.asset.current_version == 2
            assert uploaded.version.version_number == 2
            assert uploaded.upload is not None

            storage.simulate_missing(uploaded.version.object_key)
            with pytest.raises(InvalidStateError, match="object is missing"):
                await assets.download(context_a, project.id, uploaded.asset.id)
            await storage.put(
                uploaded.version.object_key,
                data,
                media_type="text/plain",
                content_hash=digest,
            )
            assert await assets.download(context_a, project.id, uploaded.asset.id) == data
            marked = await assets.mark_for_deletion(context_a, project.id, uploaded.asset.id)
            assert marked.status is AssetStatus.PENDING_DELETION
            assert (
                await asset_repository.find_version_by_hash(workspace_a, project.id, digest) is None
            )
            with pytest.raises(ConcurrencyConflictError):
                await asset_repository.mark_for_deletion(
                    workspace_a,
                    project.id,
                    uploaded.asset.id,
                    expected_version=marked.version,
                    marked_at=clock.now(),
                    retention_until=clock.now() + timedelta(days=2),
                    event=stale_event,
                )
            with pytest.raises(InvalidStateError, match="version is unavailable"):
                await asset_repository.set_processing_status(
                    workspace_a,
                    uuid4(),
                    ProcessingStatus.MISSING_OBJECT.value,
                    updated_at=clock.now(),
                )
            with pytest.raises(InvalidStateError, match="session is unavailable"):
                await asset_repository.update_upload_status(
                    workspace_a,
                    uuid4(),
                    UploadStatus.FAILED.value,
                    updated_at=clock.now(),
                )
            with pytest.raises(InvalidStateError, match="not ready"):
                await asset_repository.finalize_upload(
                    uploaded.upload,
                    uploaded.asset,
                    uploaded.version,
                    stale_event,
                )
            stale_upload = replace(
                uploaded.upload,
                id=uuid4(),
                asset_version_id=uuid4(),
                object_key=f"{uploaded.version.object_key}/stale",
                status=UploadStatus.OBJECT_STORED,
            )
            await asset_repository.begin_upload(stale_upload)
            with pytest.raises(ConcurrencyConflictError):
                await asset_repository.finalize_upload(
                    stale_upload,
                    uploaded.asset,
                    replace(
                        uploaded.version,
                        id=stale_upload.asset_version_id,
                        object_key=stale_upload.object_key,
                        content_hash="f" * 64,
                    ),
                    stale_event,
                )

            orphan_project_id = uuid4()
            orphan_settings = ProjectSettings()
            orphan_digest = hashlib.sha256(
                json.dumps(
                    {
                        "name": "fixture-orphan",
                        "revision_retention_limit": orphan_settings.revision_retention_limit,
                        "asset_retention_days": orphan_settings.asset_retention_days,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            async with SqlAlchemyUnitOfWork(runtime.sessions) as uow:
                await SqlAlchemyIdempotencyStore(uow.session).reserve(
                    IdempotencyRecord(
                        uuid4(),
                        workspace_a,
                        orphan_project_id,
                        "projects.create",
                        "fixture-orphan-key",
                        orphan_digest,
                        str(orphan_project_id),
                        clock.now() + timedelta(days=1),
                    )
                )
                await uow.commit()
            with pytest.raises(InvalidStateError, match="result is unavailable"):
                await projects.create(
                    context_a,
                    name="fixture-orphan",
                    settings=orphan_settings,
                    idempotency_key="fixture-orphan-key",
                )

            archived = await projects.archive(
                context_a, project.id, expected_version=updated.version
            )
            assert archived.archived_at == clock.now()
            with pytest.raises(ConcurrencyConflictError):
                await repository.archive(
                    workspace_a,
                    project.id,
                    expected_version=updated.version,
                    event=stale_event,
                )
            async with runtime.sessions() as session:
                event_types = tuple(
                    await session.scalars(
                        select(OutboxEventRow.event_type).order_by(OutboxEventRow.sequence)
                    )
                )
                assert event_types == (
                    "projects.project-created",
                    "projects.project-settings-updated",
                    "projects.artifact-created",
                    "projects.artifact-revision-created",
                    "assets.asset-uploaded",
                    "assets.asset-uploaded",
                    "assets.asset-deletion-marked",
                    "projects.project-archived",
                )
                assert await row_count(session, ArtifactRevisionRow) == 1
                assert await row_count(session, AssetVersionRow) == 2
                assert await row_count(session, UploadSessionRow) == 3
            audit_events = await audit.list_for_workspace(workspace_a)
            assert any(item.resource_type == "project" for item in audit_events)
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_knowledge_repository_and_pgvector_are_scoped_and_rebuildable(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(3, 1, 1.0, 60))
        now = datetime(2026, 9, 5, 8, tzinfo=UTC)
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, now)
            repository = SqlAlchemyKnowledgeRepository(runtime.sessions)
            index = PgVectorIndex(runtime.sessions)
            graph = SqlAlchemyGraphProjection(runtime.sessions)
            asset_id = uuid4()
            first_snapshot = SourceSnapshot(
                workspace_id,
                project_id,
                asset_id,
                uuid4(),
                1,
                "assets/fixture-knowledge-v1.txt",
                hashlib.sha256(b"fixture-alpha\n\nfixture-beta").hexdigest(),
                "text/plain",
            )
            run, created = await repository.reserve(
                first_snapshot,
                verification_policy=VerificationPolicy.NOT_REQUIRED,
                idempotency_key="fixture-knowledge-v1",
                requested_by=actor_id,
                correlation_id=uuid4(),
                now=now,
            )
            assert created
            replay, replay_created = await repository.reserve(
                first_snapshot,
                verification_policy=VerificationPolicy.NOT_REQUIRED,
                idempotency_key="fixture-knowledge-v1",
                requested_by=actor_id,
                correlation_id=uuid4(),
                now=now,
            )
            assert replay.id == run.id and not replay_created
            source_replay, source_replay_created = await repository.reserve(
                first_snapshot,
                verification_policy=VerificationPolicy.NOT_REQUIRED,
                idempotency_key="fixture-knowledge-v1-alias",
                requested_by=actor_id,
                correlation_id=uuid4(),
                now=now,
            )
            assert source_replay.id == run.id and not source_replay_created
            with pytest.raises(IdempotencyConflictError):
                await repository.reserve(
                    replace(first_snapshot, asset_version_id=uuid4()),
                    verification_policy=VerificationPolicy.NOT_REQUIRED,
                    idempotency_key="fixture-knowledge-v1",
                    requested_by=actor_id,
                    correlation_id=uuid4(),
                    now=now,
                )
            with pytest.raises(IdempotencyConflictError):
                await repository.reserve(
                    first_snapshot,
                    verification_policy=VerificationPolicy.REQUIRED,
                    idempotency_key="fixture-knowledge-v1",
                    requested_by=actor_id,
                    correlation_id=uuid4(),
                    now=now,
                )
            with pytest.raises(IdempotencyConflictError):
                await repository.reserve(
                    first_snapshot,
                    verification_policy=VerificationPolicy.REQUIRED,
                    idempotency_key="fixture-knowledge-v1-stricter-alias",
                    requested_by=actor_id,
                    correlation_id=uuid4(),
                    now=now,
                )
            assert await repository.load(uuid4(), run.id) is None
            with pytest.raises(InvalidStateError, match="transition"):
                await repository.set_status(
                    workspace_id, run.id, IngestionStatus.INDEXED.value, now=now
                )
            extracting = await repository.set_status(
                workspace_id, run.id, IngestionStatus.EXTRACTING.value, now=now
            )
            assert extracting.status is IngestionStatus.EXTRACTING
            with pytest.raises(InvalidStateError, match="transition"):
                await repository.set_status(
                    workspace_id, run.id, IngestionStatus.EXTRACTING.value, now=now
                )
            normalized = await repository.save_normalized(
                workspace_id, run.id, "fixture-alpha\n\nfixture-beta", now=now
            )
            assert normalized.status is IngestionStatus.NORMALIZED
            with pytest.raises(InvalidStateError, match="extraction checkpoint"):
                await repository.save_normalized(workspace_id, run.id, "fixture", now=now)

            chunks = tuple(
                Chunk(
                    uuid4(),
                    workspace_id,
                    project_id,
                    run.source_id,
                    run.document_version_id,
                    ordinal,
                    value,
                    hashlib.sha256(value.encode()).hexdigest(),
                )
                for ordinal, value in enumerate(("fixture-alpha", "fixture-beta"))
            )
            with pytest.raises(InvalidStateError, match="scope"):
                await repository.replace_chunks(
                    workspace_id,
                    run.id,
                    (replace(chunks[0], project_id=uuid4()),),
                    now=now,
                )
            chunked = await repository.replace_chunks(workspace_id, run.id, chunks, now=now)
            assert chunked.status is IngestionStatus.CHUNKED
            with pytest.raises(InvalidStateError, match="checkpoint"):
                await repository.replace_chunks(workspace_id, run.id, chunks, now=now)

            vectors = (
                (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            )
            embeddings = tuple(
                EmbeddingRef(
                    uuid4(),
                    workspace_id,
                    project_id,
                    chunk.id,
                    run.document_version_id,
                    "fake-embedder@1",
                    8,
                    vector,
                    chunk.content_hash,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            )
            with pytest.raises(InvalidStateError, match="checkpoint"):
                await repository.replace_embeddings(
                    workspace_id,
                    run.id,
                    (replace(embeddings[0], project_id=uuid4()),),
                    now=now,
                )
            embedded = await repository.replace_embeddings(
                workspace_id, run.id, embeddings, now=now
            )
            assert embedded.status is IngestionStatus.EMBEDDED
            with pytest.raises(InvalidStateError, match="checkpoint"):
                await repository.replace_embeddings(workspace_id, run.id, embeddings, now=now)
            bundle = await repository.load(workspace_id, run.id)
            assert bundle is not None
            assert bundle.source.asset_version_id == first_snapshot.asset_version_id
            assert bundle.document.asset_id == asset_id
            assert bundle.version.normalized_text == "fixture-alpha\n\nfixture-beta"
            assert bundle.chunks == chunks
            assert {item.id for item in bundle.embeddings} == {item.id for item in embeddings}

            with pytest.raises(ValueError, match="8-dimensional"):
                await index.replace(
                    workspace_id,
                    project_id,
                    run.document_version_id,
                    (replace(embeddings[0], dimensions=1, vector=(1.0,)),),
                )
            for vector_index in (InMemoryVectorIndex(), index):
                await vector_index.replace(
                    workspace_id, project_id, run.document_version_id, embeddings
                )
                await vector_index.replace(
                    workspace_id, project_id, run.document_version_id, embeddings
                )
                assert (
                    await vector_index.search(
                        workspace_id,
                        project_id,
                        vectors[0],
                        allowed_version_ids=(),
                        top_k=1,
                    )
                    == ()
                )
                matches = await vector_index.search(
                    workspace_id,
                    project_id,
                    vectors[0],
                    allowed_version_ids=(run.document_version_id,),
                    top_k=2,
                )
                assert matches[0].chunk_id == chunks[0].id
                assert matches[0].score == pytest.approx(1)
                assert (
                    await vector_index.search(
                        uuid4(),
                        project_id,
                        vectors[0],
                        allowed_version_ids=(run.document_version_id,),
                        top_k=2,
                    )
                    == ()
                )
            with pytest.raises(ValueError, match="8 dimensions"):
                await index.search(
                    workspace_id,
                    project_id,
                    (1.0,),
                    allowed_version_ids=(run.document_version_id,),
                    top_k=1,
                )

            edges = (
                KnowledgeEdge(
                    uuid4(),
                    workspace_id,
                    project_id,
                    run.document_version_id,
                    "document_version",
                    run.document_version_id,
                    RelationKind.CONTAINS,
                    "chunk",
                    chunks[0].id,
                ),
            )
            with pytest.raises(ValueError, match="scope"):
                await graph.replace(
                    workspace_id,
                    project_id,
                    run.document_version_id,
                    (replace(edges[0], workspace_id=uuid4()),),
                )
            await graph.replace(workspace_id, project_id, run.document_version_id, edges)
            await graph.replace(workspace_id, project_id, run.document_version_id, edges)

            await repository.set_status(
                workspace_id, run.id, IngestionStatus.INDEXED.value, now=now
            )
            await repository.set_status(
                workspace_id, run.id, IngestionStatus.VERIFYING.value, now=now
            )
            completed = await repository.complete(
                workspace_id, run.id, VerificationStatus.NOT_CONFIGURED, now=now
            )
            assert completed.status is IngestionStatus.READY
            with pytest.raises(InvalidStateError, match="verification checkpoint"):
                await repository.complete(
                    workspace_id, run.id, VerificationStatus.NOT_CONFIGURED, now=now
                )
            assert await repository.ready_version_ids(
                workspace_id, project_id, RetrievalFilter()
            ) == (run.document_version_id,)
            assert await repository.ready_version_ids(
                workspace_id,
                project_id,
                RetrievalFilter(
                    source_ids=(run.source_id,),
                    document_version_ids=(run.document_version_id,),
                    verification_statuses=(VerificationStatus.NOT_CONFIGURED,),
                ),
            ) == (run.document_version_id,)
            assert (
                await repository.ready_version_ids(
                    workspace_id,
                    project_id,
                    RetrievalFilter(source_ids=(uuid4(),)),
                )
                == ()
            )
            assert await repository.ready_version_ids(uuid4(), project_id, RetrievalFilter()) == ()
            assert await repository.chunks_and_citations(workspace_id, project_id, ()) == ()
            pairs = await repository.chunks_and_citations(
                workspace_id, project_id, tuple(item.id for item in chunks)
            )
            assert {item[0].id for item in pairs} == {item.id for item in chunks}
            assert all(
                citation.asset_version_id == first_snapshot.asset_version_id
                and citation.verification_status is VerificationStatus.NOT_CONFIGURED
                for _chunk, citation in pairs
            )
            assert (
                await repository.chunks_and_citations(
                    uuid4(), project_id, tuple(item.id for item in chunks)
                )
                == ()
            )

            second_snapshot = replace(
                first_snapshot,
                asset_version_id=uuid4(),
                version_number=2,
                object_key="assets/fixture-knowledge-v2.txt",
                content_hash=hashlib.sha256(b"fixture-gamma").hexdigest(),
            )
            second, second_created = await repository.reserve(
                second_snapshot,
                verification_policy=VerificationPolicy.REQUIRED,
                idempotency_key="fixture-knowledge-v2",
                requested_by=actor_id,
                correlation_id=uuid4(),
                now=now,
            )
            assert second_created and second.document_id == run.document_id
            failed = await repository.fail(
                workspace_id,
                second.id,
                failed_stage=IngestionStatus.EXTRACTING.value,
                error_code=KnowledgeErrorCode.EXTRACTION_FAILED.value,
                retryable=False,
                now=now,
            )
            assert failed.status is IngestionStatus.FAILED
            restarted = await repository.restart(workspace_id, second.id, rebuild=False, now=now)
            assert restarted.status is IngestionStatus.EXTRACTING and restarted.attempt == 2
            await repository.fail(
                workspace_id,
                second.id,
                failed_stage=IngestionStatus.EXTRACTING.value,
                error_code=KnowledgeErrorCode.SOURCE_UNAVAILABLE.value,
                retryable=True,
                now=now,
            )
            rebuilt = await repository.restart(workspace_id, second.id, rebuild=True, now=now)
            assert rebuilt.status is IngestionStatus.UPLOADED and rebuilt.attempt == 3
            with pytest.raises(InvalidStateError, match="Only failed"):
                await repository.restart(workspace_id, second.id, rebuild=False, now=now)
            await repository.set_status(
                workspace_id, second.id, IngestionStatus.EXTRACTING.value, now=now
            )
            await repository.save_normalized(workspace_id, second.id, "fixture-gamma", now=now)
            second_chunk = replace(
                chunks[0],
                id=uuid4(),
                source_id=second.source_id,
                document_version_id=second.document_version_id,
                content="fixture-gamma",
                content_hash=hashlib.sha256(b"fixture-gamma").hexdigest(),
            )
            await repository.replace_chunks(workspace_id, second.id, (second_chunk,), now=now)
            second_embedding = replace(
                embeddings[0],
                id=uuid4(),
                chunk_id=second_chunk.id,
                document_version_id=second.document_version_id,
                content_hash=second_chunk.content_hash,
            )
            await repository.replace_embeddings(
                workspace_id, second.id, (second_embedding,), now=now
            )
            await index.replace(
                workspace_id, project_id, second.document_version_id, (second_embedding,)
            )
            await repository.set_status(
                workspace_id, second.id, IngestionStatus.INDEXED.value, now=now
            )
            await repository.set_status(
                workspace_id, second.id, IngestionStatus.VERIFYING.value, now=now
            )
            with pytest.raises(InvalidStateError, match="did not pass"):
                await repository.complete(
                    workspace_id,
                    second.id,
                    VerificationStatus.NOT_CONFIGURED,
                    now=now,
                )
            await repository.complete(workspace_id, second.id, VerificationStatus.VERIFIED, now=now)
            assert await repository.ready_version_ids(
                workspace_id, project_id, RetrievalFilter()
            ) == (second.document_version_id,)
            assert (
                await repository.ready_version_ids(
                    workspace_id,
                    project_id,
                    RetrievalFilter(document_version_ids=(run.document_version_id,)),
                )
                == ()
            )
            with pytest.raises(InvalidStateError, match="unavailable"):
                await repository.set_status(
                    workspace_id, uuid4(), IngestionStatus.EXTRACTING.value, now=now
                )

            orphan_snapshot = replace(
                first_snapshot,
                asset_id=uuid4(),
                asset_version_id=uuid4(),
                object_key="assets/fixture-orphan.txt",
            )
            async with runtime.sessions.begin() as session:
                session.add(
                    KnowledgeSourceRow(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        project_id=project_id,
                        asset_id=orphan_snapshot.asset_id,
                        asset_version_id=orphan_snapshot.asset_version_id,
                        asset_version_number=1,
                        content_hash=orphan_snapshot.content_hash,
                        media_type=orphan_snapshot.media_type,
                        content_locator=orphan_snapshot.object_key,
                        created_at=now,
                    )
                )
            with pytest.raises(InvalidStateError, match="no ingestion run"):
                await repository.reserve(
                    orphan_snapshot,
                    verification_policy=VerificationPolicy.NOT_REQUIRED,
                    idempotency_key="fixture-knowledge-orphan",
                    requested_by=actor_id,
                    correlation_id=uuid4(),
                    now=now,
                )

            async with runtime.sessions() as session:
                assert await row_count(session, KnowledgeSourceRow) == 3
                assert await row_count(session, KnowledgeDocumentRow) == 1
                assert await row_count(session, KnowledgeDocumentVersionRow) == 2
                assert await row_count(session, KnowledgeIngestionRunRow) == 2
                assert await row_count(session, KnowledgeChunkRow) == 3
                assert await row_count(session, KnowledgeEmbeddingRefRow) == 3
                assert await row_count(session, KnowledgeCitationRow) == 3
                assert await row_count(session, KnowledgeVectorRow) == 3
                assert await row_count(session, KnowledgeEdgeRow) == 1
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_knowledge_repository_rejects_incomplete_persisted_aggregates() -> None:
    def async_context(value: object) -> MagicMock:
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=value)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    async def scenario() -> None:
        now = datetime(2026, 9, 5, 9, tzinfo=UTC)
        workspace_id, project_id, source_id, document_id, version_id, run_id = (
            uuid4() for _ in range(6)
        )
        row = KnowledgeIngestionRunRow(
            id=run_id,
            workspace_id=workspace_id,
            project_id=project_id,
            source_id=source_id,
            document_id=document_id,
            document_version_id=version_id,
            status=IngestionStatus.UPLOADED.value,
            verification_policy=VerificationPolicy.NOT_REQUIRED.value,
            verification_status=VerificationStatus.NOT_CONFIGURED.value,
            idempotency_key="fixture-incomplete-knowledge",
            requested_by=uuid4(),
            correlation_id=uuid4(),
            attempt=1,
            failed_stage=None,
            error_code=None,
            retryable=False,
            workflow_run_id=None,
            created_at=now,
            updated_at=now,
            version=1,
        )

        load_session = MagicMock()
        load_session.scalar = AsyncMock(return_value=row)
        load_session.get = AsyncMock(return_value=None)
        load_sessions = MagicMock(return_value=async_context(load_session))
        repository = SqlAlchemyKnowledgeRepository(cast("AsyncSessionFactory", load_sessions))
        with pytest.raises(InvalidStateError, match="aggregate is incomplete"):
            await repository.load(workspace_id, run_id)

        locked_session = MagicMock()
        locked_session.scalar = AsyncMock(return_value=row)
        locked_session.get = AsyncMock(return_value=None)
        locked_sessions = MagicMock()
        locked_sessions.begin.return_value = async_context(locked_session)
        repository = SqlAlchemyKnowledgeRepository(cast("AsyncSessionFactory", locked_sessions))
        with pytest.raises(InvalidStateError, match="document version is unavailable"):
            await repository.set_status(
                workspace_id, run_id, IngestionStatus.EXTRACTING.value, now=now
            )

    asyncio.run(scenario())


def test_knowledge_workflow_resumes_persisted_checkpoint_after_worker_restart(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(4, 1, 1.0, 60))
        clock = MutableClock(datetime(2026, 9, 5, 10, tzinfo=UTC))
        restarted_runtime: DatabaseRuntime | None = None
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, clock.now())
            context = SecurityContext(
                actor_id,
                ActorKind.USER,
                workspace_id,
                permissions_for(Role.OWNER),
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
                project_id=project_id,
            )
            authorizer = AuthorizationService(SqlAlchemyAuditStore(runtime.sessions), clock)
            projects = SqlAlchemyProjectRepository(runtime.sessions)
            assets_repository = SqlAlchemyAssetRepository(runtime.sessions)
            storage = InMemoryObjectStorage()
            assets = AssetService(
                assets_repository,
                projects=projects,
                storage=storage,
                scanner=UnconfiguredContentScanner(),
                upload_policy=DefaultUploadSecurityPolicy(max_bytes=128),
                authorizer=authorizer,
                clock=clock,
            )
            data = b"fixture-alpha\n\nfixture-beta"
            uploaded = await assets.upload(
                context,
                project_id,
                filename="fixture-knowledge.txt",
                media_type="text/plain",
                data=data,
                expected_sha256=hashlib.sha256(data).hexdigest(),
            )
            knowledge_repository = SqlAlchemyKnowledgeRepository(runtime.sessions)
            embedder = FakeEmbedder()
            index = PgVectorIndex(runtime.sessions)
            retriever = DefaultRetriever(knowledge_repository, embedder, index)
            knowledge = KnowledgeService(
                knowledge_repository,
                source_reader=AssetSourceReader(assets_repository, storage),
                extractor=TextMarkdownExtractor(),
                normalizer=DeterministicNormalizer(),
                chunker=DeterministicChunker(max_characters=64),
                embedder=embedder,
                index=index,
                verifier=NotConfiguredVerificationProvider(),
                graph=SqlAlchemyGraphProjection(runtime.sessions),
                retriever=retriever,
                projects=projects,
                authorizer=authorizer,
                clock=clock,
            )
            ingestion = await knowledge.submit(
                context,
                project_id,
                uploaded.asset.id,
                idempotency_key="fixture-knowledge-workflow-ingestion",
            )

            workflows = SqlAlchemyWorkflowRepository(runtime.sessions)
            workflow_service = WorkflowService(workflows, projects, authorizer, clock)
            workflow = await workflow_service.submit(
                context,
                project_id,
                knowledge_ingestion_definition(),
                idempotency_key="fixture-knowledge-workflow",
                input_reference=f"knowledge-run://{ingestion.id}",
            )
            queue = InMemoryTaskQueue()
            relay = OutboxRelay(
                SqlAlchemyOutboxRepository(
                    runtime.sessions,
                    clock,
                    batch_size=100,
                    lease_seconds=5,
                    retry_seconds=1,
                ),
                queue,
            )
            await relay.run_once()
            delivery = next(
                item for item in queue.deliveries if item.event_type == "workflows.task-dispatched"
            )
            task_id = UUID(cast("str", delivery.payload["task_id"]))
            claim = await workflows.claim_task(
                task_id,
                delivery.id,
                now=clock.now(),
                lease=timedelta(seconds=1),
            )
            assert claim is not None
            checkpoint = await knowledge_repository.set_status(
                workspace_id,
                ingestion.id,
                IngestionStatus.EXTRACTING.value,
                now=clock.now(),
            )
            assert checkpoint.status is IngestionStatus.EXTRACTING

            clock.advance(seconds=2)
            restarted_runtime = DatabaseRuntime.create_unpooled(
                migrated_database_url,
                name="fixture-knowledge-restarted-consumer",
            )
            restarted_projects = SqlAlchemyProjectRepository(restarted_runtime.sessions)
            restarted_assets = SqlAlchemyAssetRepository(restarted_runtime.sessions)
            restarted_authorizer = AuthorizationService(
                SqlAlchemyAuditStore(restarted_runtime.sessions), clock
            )
            restarted_repository = SqlAlchemyKnowledgeRepository(restarted_runtime.sessions)
            restarted_embedder = FakeEmbedder()
            restarted_index = PgVectorIndex(restarted_runtime.sessions)
            restarted_retriever = DefaultRetriever(
                restarted_repository, restarted_embedder, restarted_index
            )
            restarted_knowledge = KnowledgeService(
                restarted_repository,
                source_reader=AssetSourceReader(restarted_assets, storage),
                extractor=TextMarkdownExtractor(),
                normalizer=DeterministicNormalizer(),
                chunker=DeterministicChunker(max_characters=64),
                embedder=restarted_embedder,
                index=restarted_index,
                verifier=NotConfiguredVerificationProvider(),
                graph=SqlAlchemyGraphProjection(restarted_runtime.sessions),
                retriever=restarted_retriever,
                projects=restarted_projects,
                authorizer=restarted_authorizer,
                clock=clock,
            )
            restarted_workflows = SqlAlchemyWorkflowRepository(restarted_runtime.sessions)
            worker = WorkflowWorker(
                restarted_workflows,
                KnowledgeWorkflowExecutor(FrameworkSmokeExecutor(), restarted_knowledge),
                clock,
                lease_seconds=1,
            )
            assert await worker.handle(delivery) is WorkerDisposition.SUCCEEDED

            completed_workflow = await restarted_workflows.get_run(workspace_id, workflow.id)
            completed_ingestion = await restarted_repository.load(workspace_id, ingestion.id)
            assert completed_workflow is not None
            assert completed_workflow.status is WorkflowRunStatus.SUCCEEDED
            assert completed_ingestion is not None
            assert completed_ingestion.run.status is IngestionStatus.READY
            assert completed_ingestion.run.attempt == 1
            assert (
                await restarted_knowledge.get_document(
                    context, project_id, completed_ingestion.document.id
                )
                == completed_ingestion.document
            )
            assert (
                await restarted_repository.get_document(
                    uuid4(), project_id, completed_ingestion.document.id
                )
                is None
            )
            result = await restarted_knowledge.retrieve(
                context, project_id, RetrievalRequest("fixture-alpha", top_k=1)
            )
            assert len(result.hits) == 1
            assert result.hits[0].citation.asset_version_id == uploaded.version.id
            assert result.hits[0].citation.locator.startswith("asset-version://")
        finally:
            if restarted_runtime is not None:
                await restarted_runtime.shutdown()
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_workflow_engine_persists_retry_recovery_control_and_approval(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    class AlwaysRetryExecutor:
        def __init__(self) -> None:
            self.compensations = 0

        async def execute(self, _execution: StepExecution) -> StepExecutionResult:
            raise RetryableStepError("workflow-error://fixture-retry")

        async def compensate(self, _execution: StepExecution, _hook: str) -> None:
            self.compensations += 1

    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(5, 2, 1.0, 60))
        clock = MutableClock(datetime(2026, 9, 4, 8, tzinfo=UTC))
        requester_id, approver_id, workspace_id = uuid4(), uuid4(), uuid4()
        try:
            async with runtime.sessions.begin() as session:
                session.add_all(
                    [
                        UserRow(
                            id=requester_id,
                            issuer="fixture-issuer",
                            subject="fixture-workflow-requester",
                        ),
                        UserRow(
                            id=approver_id,
                            issuer="fixture-issuer",
                            subject="fixture-workflow-approver",
                        ),
                    ]
                )
            async with runtime.sessions.begin() as session:
                session.add(WorkspaceRow(id=workspace_id, owner_user_id=requester_id))
            authorizer = AuthorizationService(SqlAlchemyAuditStore(runtime.sessions), clock)
            project_repository = SqlAlchemyProjectRepository(runtime.sessions)
            projects = ProjectService(project_repository, authorizer, clock)
            requester = SecurityContext(
                requester_id,
                ActorKind.USER,
                workspace_id,
                permissions_for(Role.OWNER),
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
            )
            approver = SecurityContext(
                approver_id,
                ActorKind.USER,
                workspace_id,
                permissions_for(Role.OWNER),
                POLICY_VERSION,
                CorrelationIds(str(uuid4()), str(uuid4())),
            )
            project = await projects.create(
                requester,
                name="fixture-project",
                settings=ProjectSettings(),
                idempotency_key="fixture-workflow-project",
            )
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)
            service = WorkflowService(repository, project_repository, authorizer, clock)
            queue = InMemoryTaskQueue()
            relay = OutboxRelay(
                SqlAlchemyOutboxRepository(
                    runtime.sessions,
                    clock,
                    batch_size=100,
                    lease_seconds=5,
                    retry_seconds=1,
                ),
                queue,
            )
            executor = FrameworkSmokeExecutor()
            worker = WorkflowWorker(repository, executor, clock, lease_seconds=5)
            delivered = 0

            async def relay_events() -> tuple[EventEnvelope, ...]:
                nonlocal delivered
                await relay.run_once()
                new_events = queue.deliveries[delivered:]
                delivered = len(queue.deliveries)
                return tuple(
                    item for item in new_events if item.event_type == "workflows.task-dispatched"
                )

            smoke = await service.submit_framework_smoke(
                requester,
                project.id,
                idempotency_key="fixture-framework-smoke",
            )
            replay = await service.submit_framework_smoke(
                requester,
                project.id,
                idempotency_key="fixture-framework-smoke",
            )
            assert replay.id == smoke.id
            with pytest.raises(IdempotencyConflictError):
                await service.submit_framework_smoke(
                    requester,
                    project.id,
                    idempotency_key="fixture-framework-smoke",
                    input_reference="fixture-token://different",
                )
            first = (await relay_events())[0]
            assert await worker.handle(first) is WorkerDisposition.SUCCEEDED
            second = (await relay_events())[0]
            assert await worker.handle(second) is WorkerDisposition.RETRY_SCHEDULED
            assert (await relay.run_once()).claimed == 0
            clock.advance(seconds=1)
            second_retry = (await relay_events())[0]
            assert await worker.handle(second_retry) is WorkerDisposition.SUCCEEDED
            third = (await relay_events())[0]
            assert await worker.handle(third) is WorkerDisposition.SUCCEEDED
            assert await worker.handle(first) is WorkerDisposition.IGNORED
            completed = await service.get(requester, smoke.id)
            assert completed.status is WorkflowRunStatus.SUCCEEDED
            assert len(executor.visible_effects) == 3
            steps = await service.get_steps(requester, smoke.id)
            tasks = await service.get_tasks(requester, smoke.id)
            assert tuple(step.position for step in steps) == (0, 1, 2)
            assert len(tasks) == 3
            events = await service.get_events(requester, smoke.id)
            assert tuple(event.sequence for event in events) == tuple(range(1, len(events) + 1))
            assert (
                await service.get_events(requester, smoke.id, after_sequence=events[-2].sequence)
            ) == (events[-1],)
            assert await repository.get_run(uuid4(), smoke.id) is None
            assert await repository.get_steps(uuid4(), smoke.id) == ()
            assert await repository.get_tasks(uuid4(), smoke.id) == ()
            assert await repository.get_events(uuid4(), smoke.id) == ()

            simple_definition = WorkflowDefinition(
                uuid4(),
                "fixture_simple",
                1,
                (
                    StepDefinition(
                        uuid4(),
                        "fixture-pass",
                        0,
                        StepKind.REFERENCE,
                        5,
                        RetryPolicy(),
                    ),
                ),
                clock.now(),
            )
            await repository.ensure_definition(simple_definition)
            await repository.ensure_definition(simple_definition)
            with pytest.raises(InvalidStateError, match="immutable"):
                await repository.ensure_definition(
                    replace(
                        simple_definition,
                        steps=(replace(simple_definition.steps[0], timeout_seconds=6),),
                    )
                )

            paused = await service.submit(
                requester,
                project.id,
                simple_definition,
                idempotency_key="fixture-paused",
                input_reference="fixture-token://paused",
            )
            assert (await service.pause(requester, paused.id)).status is WorkflowRunStatus.PAUSED
            paused_delivery = (await relay_events())[0]
            assert await worker.handle(paused_delivery) is WorkerDisposition.IGNORED
            assert (await service.resume(requester, paused.id)).status is WorkflowRunStatus.RUNNING
            resumed_delivery = (await relay_events())[0]
            assert await worker.handle(resumed_delivery) is WorkerDisposition.SUCCEEDED
            assert (await service.get(requester, paused.id)).status is WorkflowRunStatus.SUCCEEDED
            with pytest.raises(InvalidStateError):
                await service.resume(requester, paused.id)

            cancelled = await service.submit(
                requester,
                project.id,
                simple_definition,
                idempotency_key="fixture-cancelled",
                input_reference="fixture-token://cancelled",
            )
            assert (
                await service.cancel(requester, cancelled.id)
            ).status is WorkflowRunStatus.CANCELLED
            cancelled_delivery = (await relay_events())[0]
            assert await worker.handle(cancelled_delivery) is WorkerDisposition.IGNORED
            with pytest.raises(InvalidStateError):
                await service.cancel(requester, cancelled.id)

            crash = await service.submit(
                requester,
                project.id,
                simple_definition,
                idempotency_key="fixture-crash",
                input_reference="fixture-token://crash",
            )
            crash_delivery = (await relay_events())[0]
            crash_task_id = UUID(cast("str", crash_delivery.payload["task_id"]))
            claimed = await repository.claim_task(
                crash_task_id,
                crash_delivery.id,
                now=clock.now(),
                lease=timedelta(seconds=5),
            )
            assert claimed is not None
            execution = StepExecution(
                claimed.run.id,
                claimed.task.id,
                claimed.step.key,
                claimed.step.kind,
                claimed.task.attempt,
                claimed.task.idempotency_key,
                claimed.task.input_reference,
                claimed.step.delay_seconds,
                claimed.step.fail_until_attempt,
            )
            await executor.execute(execution)
            before_recovery = len(executor.visible_effects)
            clock.advance(seconds=6)
            assert await worker.handle(crash_delivery) is WorkerDisposition.SUCCEEDED
            assert len(executor.visible_effects) == before_recovery
            assert (await service.get(requester, crash.id)).status is WorkflowRunStatus.SUCCEEDED

            restart = await service.submit(
                requester,
                project.id,
                simple_definition,
                idempotency_key="fixture-process-restart",
                input_reference="fixture-token://process-restart",
            )
            restart_delivery = (await relay_events())[0]
            restart_task_id = UUID(cast("str", restart_delivery.payload["task_id"]))
            assert (
                await repository.claim_task(
                    restart_task_id,
                    restart_delivery.id,
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )
                is not None
            )
            clock.advance(seconds=6)
            restarted_runtime = DatabaseRuntime.create(
                migrated_database_url, EngineOptions(5, 2, 1.0, 60)
            )
            restarted_executor = FrameworkSmokeExecutor()
            restarted_repository = SqlAlchemyWorkflowRepository(restarted_runtime.sessions)
            restarted_worker = WorkflowWorker(
                restarted_repository,
                restarted_executor,
                clock,
                lease_seconds=5,
            )
            try:
                assert (
                    await restarted_worker.handle(restart_delivery) is WorkerDisposition.SUCCEEDED
                )
                assert len(restarted_executor.visible_effects) == 1
                restarted_run = await restarted_repository.get_run(workspace_id, restart.id)
                assert restarted_run is not None
                assert restarted_run.status is WorkflowRunStatus.SUCCEEDED
            finally:
                await restarted_runtime.shutdown()

            cancelling = await service.submit(
                requester,
                project.id,
                simple_definition,
                idempotency_key="fixture-cancelling",
                input_reference="fixture-token://cancelling",
            )
            cancelling_delivery = (await relay_events())[0]
            cancelling_task_id = UUID(cast("str", cancelling_delivery.payload["task_id"]))
            cancelling_claim = await repository.claim_task(
                cancelling_task_id,
                cancelling_delivery.id,
                now=clock.now(),
                lease=timedelta(seconds=5),
            )
            assert cancelling_claim is not None
            assert (
                await service.pause(requester, cancelling.id)
            ).status is WorkflowRunStatus.RUNNING
            assert (
                await service.resume(requester, cancelling.id)
            ).status is WorkflowRunStatus.RUNNING
            assert (
                await service.cancel(requester, cancelling.id)
            ).status is WorkflowRunStatus.CANCELLING
            assert await repository.is_cancelling(cancelling_task_id, cancelling_claim.lease_token)
            cancelled_run = await repository.cancel_task(
                cancelling_claim,
                error_reference="workflow-error://cancelled",
                now=clock.now(),
            )
            assert cancelled_run.status is WorkflowRunStatus.CANCELLED

            cancel_failure_definition = replace(
                simple_definition,
                id=uuid4(),
                name="fixture_cancel_during_failure",
                steps=(
                    replace(
                        simple_definition.steps[0],
                        id=uuid4(),
                        compensation_hook="fixture-cancel-compensation.v1",
                    ),
                ),
            )
            cancel_failure_run = await service.submit(
                requester,
                project.id,
                cancel_failure_definition,
                idempotency_key="fixture-cancel-during-failure",
                input_reference="fixture-token://cancel-during-failure",
            )

            class CancelThenFailExecutor:
                def __init__(self) -> None:
                    self.compensations = 0

                async def execute(self, execution: StepExecution) -> StepExecutionResult:
                    await repository.cancel(
                        workspace_id,
                        execution.workflow_run_id,
                        actor_id=requester_id,
                        now=clock.now(),
                    )
                    raise PermanentStepError("workflow-error://fixture-failed-after-cancel")

                async def compensate(self, _execution: StepExecution, _hook: str) -> None:
                    self.compensations += 1

            cancel_failure_executor = CancelThenFailExecutor()
            cancel_failure_worker = WorkflowWorker(
                repository,
                cancel_failure_executor,
                clock,
                lease_seconds=5,
            )
            cancel_failure_delivery = (await relay_events())[0]
            assert (
                await cancel_failure_worker.handle(cancel_failure_delivery)
                is WorkerDisposition.CANCELLED
            )
            assert cancel_failure_executor.compensations == 1
            assert (
                await service.get(requester, cancel_failure_run.id)
            ).status is WorkflowRunStatus.CANCELLED

            approval_definition = WorkflowDefinition(
                uuid4(),
                "fixture_approval",
                1,
                (
                    StepDefinition(
                        uuid4(),
                        "fixture-approval",
                        0,
                        StepKind.APPROVAL,
                        5,
                        RetryPolicy(),
                        approval_expires_seconds=10,
                    ),
                    replace(
                        simple_definition.steps[0],
                        id=uuid4(),
                        key="fixture-after-approval",
                        position=1,
                    ),
                ),
                clock.now(),
            )
            approved = await service.submit(
                requester,
                project.id,
                approval_definition,
                idempotency_key="fixture-approved",
                input_reference="fixture-token://approval",
            )
            assert approved.status is WorkflowRunStatus.WAITING_APPROVAL
            assert await repository.get_approval(uuid4(), approved.id) is None
            assert (await service.pause(requester, approved.id)).status is WorkflowRunStatus.PAUSED
            assert (
                await service.resume(requester, approved.id)
            ).status is WorkflowRunStatus.WAITING_APPROVAL
            approved = await service.decide_approval(
                approver,
                approved.id,
                WorkflowApprovalDecision.APPROVE,
                reason="fixture-approved",
            )
            assert approved.status is WorkflowRunStatus.RUNNING
            approval_delivery = (await relay_events())[0]
            assert await worker.handle(approval_delivery) is WorkerDisposition.SUCCEEDED
            with pytest.raises(InvalidStateError, match="no pending"):
                await service.decide_approval(
                    approver,
                    approved.id,
                    WorkflowApprovalDecision.APPROVE,
                    reason="fixture-duplicate",
                )

            rejected = await service.submit(
                requester,
                project.id,
                replace(
                    approval_definition,
                    id=uuid4(),
                    name="fixture_rejection",
                    steps=tuple(replace(step, id=uuid4()) for step in approval_definition.steps),
                ),
                idempotency_key="fixture-rejected",
                input_reference="fixture-token://rejected",
            )
            rejected = await service.decide_approval(
                approver,
                rejected.id,
                WorkflowApprovalDecision.REJECT,
                reason="fixture-rejected",
            )
            assert rejected.status is WorkflowRunStatus.FAILED

            expiring_definition = replace(
                approval_definition,
                id=uuid4(),
                name="fixture_expiry",
                steps=(
                    replace(
                        approval_definition.steps[0],
                        id=uuid4(),
                        approval_expires_seconds=1,
                    ),
                ),
            )
            expiring = await service.submit(
                requester,
                project.id,
                expiring_definition,
                idempotency_key="fixture-expired",
                input_reference="fixture-token://expired",
            )
            with pytest.raises(InvalidStateError, match="not expired"):
                await service.expire_approval(workspace_id, expiring.id)
            clock.advance(seconds=1)
            expired = await service.expire_approval(workspace_id, expiring.id)
            assert expired.status is WorkflowRunStatus.FAILED

            failure_definition = WorkflowDefinition(
                uuid4(),
                "fixture_dead_letter",
                1,
                (
                    StepDefinition(
                        uuid4(),
                        "fixture-failure",
                        0,
                        StepKind.CONTROLLED_FAILURE,
                        5,
                        RetryPolicy(2, 1, 2),
                        fail_until_attempt=1,
                        compensation_hook="fixture-compensation.v1",
                    ),
                ),
                clock.now(),
            )
            failed = await service.submit(
                requester,
                project.id,
                failure_definition,
                idempotency_key="fixture-failed",
                input_reference="fixture-token://failed",
            )
            failure_executor = AlwaysRetryExecutor()
            failure_worker = WorkflowWorker(repository, failure_executor, clock)
            failure_delivery = (await relay_events())[0]
            assert (
                await failure_worker.handle(failure_delivery) is WorkerDisposition.RETRY_SCHEDULED
            )
            clock.advance(seconds=1)
            retry_delivery = (await relay_events())[0]
            assert await failure_worker.handle(retry_delivery) is WorkerDisposition.DEAD_LETTERED
            assert failure_executor.compensations == 1
            assert (await service.get(requester, failed.id)).status is WorkflowRunStatus.FAILED

            celery_app = create_celery_app(load_settings().required.redis_url)
            celery_app.conf.task_default_queue = f"fixture-workflow-{uuid4().hex}"
            real_worker_runtime = DatabaseRuntime.create_unpooled(
                migrated_database_url,
                name="fixture-celery-consumer-persistence",
            )
            real_queue_worker = WorkflowWorker(
                SqlAlchemyWorkflowRepository(real_worker_runtime.sessions),
                FrameworkSmokeExecutor(),
                clock,
                lease_seconds=5,
            )
            register_celery_consumer(celery_app, real_queue_worker.handle)
            real_relay = OutboxRelay(
                SqlAlchemyOutboxRepository(
                    runtime.sessions,
                    clock,
                    batch_size=100,
                    lease_seconds=5,
                    retry_seconds=1,
                ),
                CeleryEventPublisher(celery_app),
            )
            real_smoke = await service.submit_framework_smoke(
                requester,
                project.id,
                idempotency_key="fixture-real-celery",
                input_reference="fixture-token://real-celery",
            )
            try:
                with start_worker(
                    celery_app,
                    perform_ping_check=False,
                    pool="solo",
                    concurrency=1,
                    loglevel="INFO",
                ):
                    for _attempt in range(100):
                        await real_relay.run_once()
                        current = await repository.get_run(workspace_id, real_smoke.id)
                        assert current is not None
                        if current.status is WorkflowRunStatus.SUCCEEDED:
                            break
                        clock.advance(seconds=0.5)
                        await asyncio.sleep(0.1)
                    else:
                        pytest.fail("real Celery/Redis framework_smoke did not finish")
            finally:
                celery_app.close()
                await real_worker_runtime.shutdown()

            async with runtime.sessions() as session:
                task_rows = tuple((await session.scalars(select(TaskRunRow))).all())
                step_runs = tuple((await session.scalars(select(WorkflowStepRunRow))).all())
                run_events = tuple((await session.scalars(select(WorkflowRunEventRow))).all())
            assert any(task.status == TaskRunStatus.DEAD_LETTER.value for task in task_rows)
            assert any(step.attempt == 2 for step in step_runs)
            assert run_events
            assert (
                await repository.claim_task(
                    uuid4(), uuid4(), now=clock.now(), lease=timedelta(seconds=1)
                )
                is None
            )
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_workflow_repository_handles_pause_cancel_and_advance_edges(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(5, 2, 1.0, 60))
        clock = MutableClock(datetime(2026, 9, 4, 9, tzinfo=UTC))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, clock.now())
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)

            retry_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_pause_retry", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-pause-retry",
                now=clock.now(),
            )
            retry_task = await workflow_task(runtime, retry_run.id)
            retry_claim = await repository.claim_task(
                retry_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert retry_claim is not None
            pause_requested = await repository.pause(
                workspace_id, retry_run.id, actor_id=actor_id, now=clock.now()
            )
            assert pause_requested.status is WorkflowRunStatus.RUNNING
            retry_settlement = await repository.fail_task(
                retry_claim,
                error_reference="workflow-error://fixture-retry",
                now=clock.now(),
                retry_at=clock.now() + timedelta(seconds=1),
            )
            assert retry_settlement.run.status is WorkflowRunStatus.PAUSED

            approval_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_cancel_approval", clock.now(), (StepKind.APPROVAL, 10)
                ),
                key="fixture-cancel-approval",
                now=clock.now(),
            )
            cancelled_approval = await repository.cancel(
                workspace_id, approval_run.id, actor_id=actor_id, now=clock.now()
            )
            assert cancelled_approval.status is WorkflowRunStatus.CANCELLED

            direct_cancel_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_direct_cancel", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-direct-cancel",
                now=clock.now(),
            )
            direct_cancel_task = await workflow_task(runtime, direct_cancel_run.id)
            direct_cancel_claim = await repository.claim_task(
                direct_cancel_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert direct_cancel_claim is not None
            directly_cancelled = await repository.cancel_task(
                direct_cancel_claim,
                error_reference="workflow-error://fixture-cancelled",
                now=clock.now(),
            )
            assert directly_cancelled.status is WorkflowRunStatus.CANCELLED

            paused_next_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_pause_next_task",
                    clock.now(),
                    (StepKind.REFERENCE, None),
                    (StepKind.REFERENCE, None),
                ),
                key="fixture-pause-next-task",
                now=clock.now(),
            )
            paused_next_task = await workflow_task(runtime, paused_next_run.id)
            paused_next_claim = await repository.claim_task(
                paused_next_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert paused_next_claim is not None
            await repository.pause(
                workspace_id, paused_next_run.id, actor_id=actor_id, now=clock.now()
            )
            paused_next = await repository.succeed_task(
                paused_next_claim,
                output_reference="fixture-output://first",
                now=clock.now(),
            )
            assert paused_next.status is WorkflowRunStatus.PAUSED
            async with runtime.sessions.begin() as session:
                stored_second = await session.scalar(
                    select(TaskRunRow).where(
                        TaskRunRow.workflow_run_id == paused_next_run.id,
                        TaskRunRow.id != paused_next_task.id,
                    )
                )
                assert stored_second is not None
                stored_second.status = TaskRunStatus.SUCCEEDED.value
            with pytest.raises(InvalidStateError, match="no resumable task"):
                await repository.resume(
                    workspace_id, paused_next_run.id, actor_id=actor_id, now=clock.now()
                )
            cancelled_inconsistent = await repository.cancel(
                workspace_id, paused_next_run.id, actor_id=actor_id, now=clock.now()
            )
            assert cancelled_inconsistent.status is WorkflowRunStatus.CANCELLED

            paused_approval_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_pause_next_approval",
                    clock.now(),
                    (StepKind.REFERENCE, None),
                    (StepKind.APPROVAL, 10),
                ),
                key="fixture-pause-next-approval",
                now=clock.now(),
            )
            paused_approval_task = await workflow_task(runtime, paused_approval_run.id)
            paused_approval_claim = await repository.claim_task(
                paused_approval_task.id,
                uuid4(),
                now=clock.now(),
                lease=timedelta(seconds=5),
            )
            assert paused_approval_claim is not None
            await repository.pause(
                workspace_id, paused_approval_run.id, actor_id=actor_id, now=clock.now()
            )
            paused_approval = await repository.succeed_task(
                paused_approval_claim,
                output_reference="fixture-output://approval-input",
                now=clock.now(),
            )
            assert paused_approval.status is WorkflowRunStatus.PAUSED
            resumed_approval = await repository.resume(
                workspace_id, paused_approval_run.id, actor_id=actor_id, now=clock.now()
            )
            assert resumed_approval.status is WorkflowRunStatus.WAITING_APPROVAL
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)


def test_workflow_repository_defensive_guards_and_lease_exhaustion(  # noqa: PLR0915
    migrated_database_url: str,
) -> None:
    async def scenario() -> None:  # noqa: PLR0915
        runtime = DatabaseRuntime.create(migrated_database_url, EngineOptions(5, 2, 1.0, 60))
        clock = MutableClock(datetime(2026, 9, 4, 10, tzinfo=UTC))
        try:
            actor_id, workspace_id, project_id = await seed_workflow_scope(runtime, clock.now())
            repository = SqlAlchemyWorkflowRepository(runtime.sessions)

            ghost_definition = technical_definition(
                "fixture_missing_idempotent_result",
                clock.now(),
                (StepKind.REFERENCE, None),
            )
            ghost_key = "fixture-missing-idempotent-result"
            ghost_digest = hashlib.sha256(ghost_key.encode()).hexdigest()
            ghost_run = WorkflowRun(
                uuid4(),
                workspace_id,
                project_id,
                ghost_definition.id,
                ghost_definition.name,
                ghost_definition.version,
                WorkflowRunStatus.PENDING,
                ghost_key,
                "fixture-token://input",
                actor_id,
                ActorKind.USER.value,
                uuid4(),
                clock.now(),
                clock.now(),
            )
            await repository.ensure_definition(ghost_definition)
            async with runtime.sessions.begin() as session:
                await SqlAlchemyIdempotencyStore(session).reserve(
                    IdempotencyRecord(
                        uuid4(),
                        workspace_id,
                        project_id,
                        f"workflows.submit:{ghost_definition.name}",
                        ghost_key,
                        ghost_digest,
                        str(uuid4()),
                        clock.now() + timedelta(days=1),
                    )
                )
            with pytest.raises(InvalidStateError, match="result is unavailable"):
                await repository.submit(ghost_run, ghost_definition, request_digest=ghost_digest)

            invalid_decision_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_invalid_decision", clock.now(), (StepKind.APPROVAL, 10)
                ),
                key="fixture-invalid-decision",
                now=clock.now(),
            )
            invalid_decision_request = await repository.get_approval(
                workspace_id, invalid_decision_run.id
            )
            assert invalid_decision_request is not None
            await repository.pause(
                workspace_id, invalid_decision_run.id, actor_id=actor_id, now=clock.now()
            )
            with pytest.raises(InvalidStateError, match="Only a pending"):
                await repository.decide_approval(
                    workspace_id,
                    invalid_decision_run.id,
                    ApprovalRecord(
                        uuid4(),
                        workspace_id,
                        invalid_decision_request.id,
                        actor_id,
                        WorkflowApprovalDecision.APPROVE,
                        "fixture-reason",
                        clock.now(),
                    ),
                )

            async def corrupt_reference(statement: str, **parameters: object) -> None:
                async with runtime.sessions.begin() as session:
                    await session.execute(text("SET LOCAL session_replication_role = 'replica'"))
                    await session.execute(text(statement), parameters)

            missing_approval_step_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_approval_step", clock.now(), (StepKind.APPROVAL, 10)
                ),
                key="fixture-missing-approval-step",
                now=clock.now(),
            )
            missing_approval_step = await repository.get_approval(
                workspace_id, missing_approval_step_run.id
            )
            assert missing_approval_step is not None
            await corrupt_reference(
                "UPDATE accos.workflow_approval_requests SET step_run_id = :missing "
                "WHERE id = :request_id",
                missing=uuid4(),
                request_id=missing_approval_step.id,
            )
            with pytest.raises(InvalidStateError, match="step is unavailable"):
                await repository.decide_approval(
                    workspace_id,
                    missing_approval_step_run.id,
                    ApprovalRecord(
                        uuid4(),
                        workspace_id,
                        missing_approval_step.id,
                        actor_id,
                        WorkflowApprovalDecision.APPROVE,
                        "fixture-reason",
                        clock.now(),
                    ),
                )

            missing_expiry_step_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_expiry_step", clock.now(), (StepKind.APPROVAL, 1)
                ),
                key="fixture-missing-expiry-step",
                now=clock.now(),
            )
            missing_expiry_step = await repository.get_approval(
                workspace_id, missing_expiry_step_run.id
            )
            assert missing_expiry_step is not None
            await corrupt_reference(
                "UPDATE accos.workflow_approval_requests SET step_run_id = :missing "
                "WHERE id = :request_id",
                missing=uuid4(),
                request_id=missing_expiry_step.id,
            )
            clock.advance(seconds=1)
            with pytest.raises(InvalidStateError, match="step is unavailable"):
                await repository.expire_approval(
                    workspace_id, missing_expiry_step_run.id, now=clock.now()
                )

            missing_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_task_run", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-missing-task-run",
                now=clock.now(),
            )
            missing_run_task = await workflow_task(runtime, missing_run.id)
            await corrupt_reference(
                "UPDATE accos.workflow_task_runs SET workflow_run_id = :missing "
                "WHERE id = :task_id",
                missing=uuid4(),
                task_id=missing_run_task.id,
            )
            with pytest.raises(InvalidStateError, match="no owning run"):
                await repository.claim_task(
                    missing_run_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )

            cancelling_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_claim_cancelling", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-claim-cancelling",
                now=clock.now(),
            )
            cancelling_task = await workflow_task(runtime, cancelling_run.id)
            cancelling_claim = await repository.claim_task(
                cancelling_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert cancelling_claim is not None
            cancelling = await repository.cancel(
                workspace_id, cancelling_run.id, actor_id=actor_id, now=clock.now()
            )
            assert cancelling.status is WorkflowRunStatus.CANCELLING
            assert (
                await repository.claim_task(
                    cancelling_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )
                is None
            )

            missing_step_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_task_step", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-missing-task-step",
                now=clock.now(),
            )
            missing_step_task = await workflow_task(runtime, missing_step_run.id)
            await corrupt_reference(
                "UPDATE accos.workflow_task_runs SET step_run_id = :missing WHERE id = :task_id",
                missing=uuid4(),
                task_id=missing_step_task.id,
            )
            with pytest.raises(InvalidStateError, match="no owning step"):
                await repository.claim_task(
                    missing_step_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )

            missing_definition_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_definition", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-missing-definition",
                now=clock.now(),
            )
            missing_definition_task = await workflow_task(runtime, missing_definition_run.id)
            async with runtime.sessions() as session:
                missing_definition_step_id = await session.scalar(
                    select(TaskRunRow.step_run_id).where(
                        TaskRunRow.id == missing_definition_task.id
                    )
                )
            assert missing_definition_step_id is not None
            await corrupt_reference(
                "UPDATE accos.workflow_step_runs SET step_definition_id = :missing "
                "WHERE id = :step_run_id",
                missing=uuid4(),
                step_run_id=missing_definition_step_id,
            )
            with pytest.raises(InvalidStateError, match="definition is unavailable"):
                await repository.claim_task(
                    missing_definition_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )

            exhausted_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_exhausted_lease", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-exhausted-lease",
                now=clock.now(),
            )
            exhausted_task = await workflow_task(runtime, exhausted_run.id)
            for _attempt in range(3):
                assert (
                    await repository.claim_task(
                        exhausted_task.id,
                        uuid4(),
                        now=clock.now(),
                        lease=timedelta(seconds=1),
                    )
                    is not None
                )
                clock.advance(seconds=1)
            assert (
                await repository.claim_task(
                    exhausted_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=1),
                )
                is None
            )
            assert (
                await repository.get_run(workspace_id, exhausted_run.id)
            ).status is WorkflowRunStatus.FAILED  # type: ignore[union-attr]

            with pytest.raises(ScopeViolationError):
                await repository.pause(
                    uuid4(), exhausted_run.id, actor_id=actor_id, now=clock.now()
                )

            lost_lease_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_lost_lease", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-lost-lease",
                now=clock.now(),
            )
            lost_lease_task = await workflow_task(runtime, lost_lease_run.id)
            lost_lease_claim = await repository.claim_task(
                lost_lease_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert lost_lease_claim is not None
            with pytest.raises(InvalidStateError, match="lease is no longer owned"):
                await repository.succeed_task(
                    replace(lost_lease_claim, lease_token=uuid4()),
                    output_reference="fixture-output://lost",
                    now=clock.now(),
                )

            missing_claim_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_missing_claim_owner", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-missing-claim-owner",
                now=clock.now(),
            )
            missing_claim_task = await workflow_task(runtime, missing_claim_run.id)
            missing_claim = await repository.claim_task(
                missing_claim_task.id, uuid4(), now=clock.now(), lease=timedelta(seconds=5)
            )
            assert missing_claim is not None
            await corrupt_reference(
                "UPDATE accos.workflow_task_runs SET workflow_run_id = :missing "
                "WHERE id = :task_id",
                missing=uuid4(),
                task_id=missing_claim_task.id,
            )
            with pytest.raises(InvalidStateError, match="ownership state is unavailable"):
                await repository.succeed_task(
                    missing_claim,
                    output_reference="fixture-output://missing-owner",
                    now=clock.now(),
                )

            cancel_missing_step_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_cancel_missing_step", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-cancel-missing-step",
                now=clock.now(),
            )
            cancel_missing_step_task = await workflow_task(runtime, cancel_missing_step_run.id)
            await corrupt_reference(
                "UPDATE accos.workflow_task_runs SET step_run_id = :missing WHERE id = :task_id",
                missing=uuid4(),
                task_id=cancel_missing_step_task.id,
            )
            cancelled_missing_step = await repository.cancel(
                workspace_id, cancel_missing_step_run.id, actor_id=actor_id, now=clock.now()
            )
            assert cancelled_missing_step.status is WorkflowRunStatus.CANCELLED

            cancelling_missing_step_run = await submit_workflow_run(
                repository,
                actor_id=actor_id,
                workspace_id=workspace_id,
                project_id=project_id,
                definition=technical_definition(
                    "fixture_cancelling_missing_step", clock.now(), (StepKind.REFERENCE, None)
                ),
                key="fixture-cancelling-missing-step",
                now=clock.now(),
            )
            cancelling_missing_step_task = await workflow_task(
                runtime, cancelling_missing_step_run.id
            )
            assert (
                await repository.claim_task(
                    cancelling_missing_step_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )
                is not None
            )
            await repository.cancel(
                workspace_id,
                cancelling_missing_step_run.id,
                actor_id=actor_id,
                now=clock.now(),
            )
            await corrupt_reference(
                "UPDATE accos.workflow_task_runs SET step_run_id = :missing WHERE id = :task_id",
                missing=uuid4(),
                task_id=cancelling_missing_step_task.id,
            )
            assert (
                await repository.claim_task(
                    cancelling_missing_step_task.id,
                    uuid4(),
                    now=clock.now(),
                    lease=timedelta(seconds=5),
                )
                is None
            )
        finally:
            await runtime.shutdown()

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)
