"""Shared API and worker dependency assembly."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast

from accos import __version__
from accos.adapters.agents import SqlAlchemyAgentRepository
from accos.adapters.agents.jobs import SqlAgentJobStore
from accos.modules.agents.jobs import AgentJobService
from accos.adapters.assets import (
    MinioObjectStorage,
    ResilientObjectStorage,
    SqlAlchemyAssetRepository,
)
from accos.adapters.assets.retention import OrphanCollector
from accos.adapters.consistency import (
    CreativeFactRevisionAdapter,
    SqlAlchemyConsistencyRepository,
)
from accos.adapters.creative import (
    RepositoryPreferenceSignalIngestPort,
    SqlAlchemyCreativeRepository,
)
from accos.adapters.evolution import SqlAlchemyEvolutionMemory
from accos.adapters.extensions import SqlAlchemyExtensionGraphStore
from accos.adapters.feedback import SqlAlchemyFeedbackRepository
from accos.adapters.health import (
    AiProviderHealthProbe,
    RedisHealthProbe,
    S3HealthProbe,
)
from accos.adapters.identity import (
    DevelopmentIdentityProvider,
    IdentityRuntime,
    InMemoryRateLimiter,
    RejectingIdentityProvider,
    SqlAlchemyAuditStore,
    SqlAlchemyControlRequestStore,
    SqlAlchemyIdentityRepository,
)
from accos.adapters.identity.accounts import SqlAccountStore
from accos.adapters.identity.crypto import (
    CredentialCipher,
    external_secret,
    password_hash,
    password_matches,
)
from accos.adapters.identity.oidc import HttpOidcClient
from accos.adapters.knowledge import (
    AssetSourceReader,
    DeterministicChunker,
    DeterministicNormalizer,
    FakeEmbedder,
    NotConfiguredVerificationProvider,
    PgVectorIndex,
    SqlAlchemyGraphProjection,
    SqlAlchemyKnowledgeRepository,
    TextMarkdownExtractor,
)
from accos.adapters.memory import (
    RedisMemoryProjection,
    SqlAlchemyMemoryRepository,
)
from accos.adapters.models import (
    FakeModelProvider,
    NullModelProvider,
    SqlAlchemyUsageLedger,
)
from accos.adapters.models.content_tool import ContentReadTool, content_tool_descriptor
from accos.composition.models import build_model_runtime
from accos.modules.agents.real_executor import REAL_AGENT_BUDGET, RealAgentExecutor, real_descriptors
from accos.modules.models.domain import ModelCapability
from accos.modules.models.runtime import ModelRuntime
from accos.adapters.observability import OtlpHttpExporter
from accos.adapters.persistence import (
    DatabaseHealthProbe,
    DatabaseRuntime,
    EngineOptions,
    OutboxRelay,
    SqlAlchemyOutboxRepository,
)
from accos.adapters.projects import SqlAlchemyProjectRepository
from accos.adapters.projects.content import SqlAlchemyContentRepository
from accos.adapters.quality import SqlAlchemyQualityRepository
from accos.adapters.runtime_monitor import PostgresRedisRuntimeMonitor
from accos.adapters.tools import FakeToolExecutor, SqlAlchemyToolCallLedger
from accos.adapters.workflows import (
    CeleryEventPublisher,
    SqlAlchemyWorkflowRepository,
    create_celery_app,
    register_celery_consumer,
)
from accos.extensions import (
    CollaborationBoundary,
    DeferredBoundary,
    ExtensionCapability,
    ExtensionCatalog,
    MultimodalBoundary,
    NullAcquisitionProvider,
    NullCollaborationAdapter,
    NullExternalVerificationProvider,
    NullGraphStore,
    NullGrowthAdapter,
    NullMarketplaceAdapter,
    NullMultimodalAdapter,
    NullReputationAdapter,
    NullResearchTeamProvider,
    NullRightsAdapter,
    RightsBoundary,
    default_manifests,
)
from accos.kernel.clock import Clock, UtcClock
from accos.kernel.errors import ConfigurationError
from accos.kernel.health import HealthProbe, HealthService
from accos.kernel.lifecycle import ModuleRegistry
from accos.kernel.logging import get_logger, log_event
from accos.kernel.observability import MetricRegistry as TelemetryMetricRegistry
from accos.kernel.observability import RuntimeMonitor, TelemetryRuntime
from accos.kernel.resilience import ResilienceExecutor, ResiliencePolicy
from accos.modules.agents.public import (
    DEFAULT_AGENT_BUDGET,
    AgentBudget,
    AgentExecutor,
    AgentMetrics,
    AgentRegistry,
    AgentRepository,
    AgentSupervisor,
    AgentWorkflowExecutor,
    DefaultAgentSupervisor,
    FakeAgentExecutor,
    InMemoryAgentMetrics,
    InMemoryAgentRegistry,
    MasterOrchestrator,
    built_in_agent_descriptors,
)
from accos.modules.assets.downloads import VersionDownloadSigner
from accos.modules.assets.public import (
    AssetRepository,
    AssetService,
    DefaultUploadSecurityPolicy,
    ObjectStorage,
    UnconfiguredContentScanner,
)
from accos.modules.consistency.public import (
    CanonQualityWorkflowExecutor,
    ConsistencyAccess,
    ConsistencyRepository,
    ConsistencyService,
    PersistedCanonQualityGate,
    default_validator_registry,
)
from accos.modules.creative.public import (
    CharacterService,
    CreativeAccess,
    CreativeApplication,
    CreativeCatalog,
    CreativeExtensions,
    CreativeRepository,
    CreativeRevisionService,
    CreativeWorkflowExecutor,
    CreatorService,
    NovelService,
    WorldService,
    null_creative_extensions,
)
from accos.modules.evolution.public import (
    DeterministicAnalyzer,
    DiagnosticObserver,
    DryRunSimulationEnvironment,
    EvolutionAccess,
    EvolutionMemory,
    EvolutionService,
    ImmutableSafetyController,
    ProposalPlanner,
    ReadOnlyVersionManager,
)
from accos.modules.feedback.public import (
    FeedbackAccess,
    FeedbackRepository,
    FeedbackService,
    MetricRegistry,
    SystemDoctor,
    default_diagnostic_rules,
)
from accos.modules.identity.account_service import (
    AccountService,
    ApprovalPolicyResolver,
    LiveScopeAccess,
    PersistentIdentityProvider,
    WorkspaceSecretProvider,
)
from accos.modules.identity.application import (
    AuthorizationService,
    CreatorControlService,
    IdentityAuthenticator,
    IdentityQueryService,
)
from accos.modules.identity.public import Permission
from accos.modules.knowledge.public import (
    DefaultRetriever,
    GraphProjection,
    KnowledgeRepository,
    KnowledgeService,
    KnowledgeWorkflowExecutor,
    ResearchService,
    Retriever,
    VectorIndex,
)
from accos.modules.memory.public import (
    ContextBuilder,
    DefaultRetentionPolicy,
    DeterministicMemoryCompressor,
    FakeSemanticMemoryRanker,
    MemoryAccessPolicy,
    MemoryProjection,
    MemoryProjectionRebuilder,
    MemoryRepository,
    MemoryService,
    ProposalConflictResolver,
)
from accos.modules.models.public import (
    ModelGateway,
    ModelPolicy,
    ModelRegistry,
    SecretProvider,
    UsageLedger,
)
from accos.modules.projects.content_service import ContentService
from accos.modules.projects.public import ProjectRepository, ProjectService
from accos.modules.quality.public import (
    QualityAccess,
    QualityRepository,
    QualityService,
    StructuralQualityEvaluator,
)
from accos.modules.tools.public import (
    ToolCallLedger,
    ToolDescriptor,
    ToolGateway,
    ToolRegistry,
)
from accos.modules.workflows.public import (
    FrameworkSmokeExecutor,
    StepExecutor,
    WorkflowRepository,
    WorkflowService,
    WorkflowWorker,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.kernel.events import EventPublisher
    from accos.kernel.graph import GraphStore
    from accos.kernel.settings import RuntimeSettings
    from accos.modules.identity.ports import IdentityProvider, RateLimiter, UploadSecurityPolicy


@dataclass(slots=True)
class RuntimeMarkerModule:
    """Lifecycle marker until a module owns concrete long-lived resources."""

    name: str
    logger: logging.Logger

    async def startup(self) -> None:
        """Record module startup through the shared logger."""
        log_event(self.logger, logging.INFO, "module_started", module=self.name)

    async def shutdown(self) -> None:
        """Record module shutdown through the shared logger."""
        log_event(self.logger, logging.INFO, "module_stopped", module=self.name)


@dataclass(frozen=True, slots=True)
class IdentityServices:
    """Identity/security contracts shared by API, worker, and future modules."""

    authenticator: IdentityAuthenticator
    authorizer: AuthorizationService
    creator_control: CreatorControlService
    rate_limiter: RateLimiter
    upload_policy: UploadSecurityPolicy
    query: IdentityQueryService | None = None
    accounts: AccountService | None = None


@dataclass(frozen=True, slots=True)
class ProjectServices:
    """Project module public service and repository boundary."""

    service: ProjectService
    repository: ProjectRepository
    content: ContentService


@dataclass(frozen=True, slots=True)
class AssetServices:
    """Asset module public service and object boundary."""

    service: AssetService
    repository: AssetRepository
    storage: ObjectStorage
    orphan_collector: OrphanCollector
    downloads: VersionDownloadSigner


@dataclass(frozen=True, slots=True)
class ModelServices:
    """Model gateway, catalog, usage ledger, and isolated secret boundary."""

    gateway: ModelGateway
    registry: ModelRegistry
    ledger: UsageLedger
    secrets: SecretProvider
    runtime: ModelRuntime


@dataclass(frozen=True, slots=True)
class KnowledgeServices:
    """Knowledge ingestion, retrieval, research, and projection boundaries."""

    service: KnowledgeService
    research: ResearchService
    repository: KnowledgeRepository
    retriever: Retriever
    index: VectorIndex
    graph: GraphProjection


@dataclass(frozen=True, slots=True)
class MemoryServices:
    """Seven-scope facts, context assembly, grants, and disposable projection."""

    service: MemoryService
    context_builder: ContextBuilder
    repository: MemoryRepository
    projection: MemoryProjection
    rebuilder: MemoryProjectionRebuilder


@dataclass(frozen=True, slots=True)
class CreativeServices:
    """The four creative owners, their shared catalog, and optional ports."""

    novel: NovelService
    world: WorldService
    character: CharacterService
    creator: CreatorService
    catalog: CreativeCatalog
    repository: CreativeRepository
    extensions: CreativeExtensions
    revisions: CreativeRevisionService


@dataclass(frozen=True, slots=True)
class ConsistencyServices:
    """Canon, deterministic validators, findings, and human resolutions."""

    service: ConsistencyService
    repository: ConsistencyRepository


@dataclass(frozen=True, slots=True)
class QualityServices:
    """Schema-only rubric and evaluation lifecycle."""

    service: QualityService
    repository: QualityRepository


@dataclass(frozen=True, slots=True)
class FeedbackServices:
    """Consent, bounded metrics, read-only diagnostics, and smoke experiments."""

    service: FeedbackService
    repository: FeedbackRepository
    registry: MetricRegistry


@dataclass(frozen=True, slots=True)
class EvolutionServices:
    """Offline analysis and human-controlled improvement proposals."""

    service: EvolutionService
    memory: EvolutionMemory


@dataclass(frozen=True, slots=True)
class ExtensionServices:
    """Isolated parked capabilities and their secure runtime boundaries."""

    catalog: ExtensionCatalog
    multimodal: Mapping[ExtensionCapability, MultimodalBoundary]
    graph: GraphStore
    collaboration: CollaborationBoundary
    rights: RightsBoundary
    marketplace: DeferredBoundary
    reputation: DeferredBoundary
    growth: DeferredBoundary
    acquisition: DeferredBoundary
    research_team: DeferredBoundary
    verification: DeferredBoundary


@dataclass(frozen=True, slots=True)
class ObservabilityServices:
    """Process-local telemetry plus cross-process operational projections."""

    telemetry: TelemetryRuntime
    monitor: RuntimeMonitor


@dataclass(frozen=True, slots=True)
class ToolServices:
    """Tool gateway, registry, and append-only call ledger."""

    gateway: ToolGateway
    registry: ToolRegistry
    ledger: ToolCallLedger


@dataclass(frozen=True, slots=True)
class AgentServices:
    """Agent registry, bounded supervisor, persistence, and master orchestrator."""

    registry: AgentRegistry
    executor: AgentExecutor
    supervisor: AgentSupervisor
    repository: AgentRepository
    metrics: AgentMetrics
    master: MasterOrchestrator
    jobs: AgentJobService


@dataclass(frozen=True, slots=True)
class WorkflowServices:
    """Workflow application, Worker, persistence, and relay boundaries."""

    service: WorkflowService
    worker: WorkflowWorker
    repository: WorkflowRepository
    consumer_database: DatabaseRuntime
    executor: StepExecutor
    relay: OutboxRelay
    celery_app: Any | None


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Runtime services shared by the API and worker."""

    settings: RuntimeSettings
    health: HealthService
    database: DatabaseRuntime
    identity: IdentityServices
    projects: ProjectServices
    assets: AssetServices
    knowledge: KnowledgeServices
    memory: MemoryServices
    creative: CreativeServices
    consistency: ConsistencyServices
    quality: QualityServices
    feedback: FeedbackServices
    evolution: EvolutionServices
    extensions: ExtensionServices
    models: ModelServices
    tools: ToolServices
    agents: AgentServices
    workflows: WorkflowServices
    observability: ObservabilityServices
    modules: ModuleRegistry

    async def startup(self) -> None:
        """Start all registered runtime modules."""
        await self.modules.startup()

    async def shutdown(self) -> None:
        """Stop all registered runtime modules."""
        await self.modules.shutdown()


def build_container(  # noqa: PLR0912,PLR0915 - composition intentionally owns assembly.
    settings: RuntimeSettings,
    *,
    clock: Clock | None = None,
    probes: tuple[HealthProbe, ...] | None = None,
    identity_provider: IdentityProvider | None = None,
    event_publisher: EventPublisher | None = None,
) -> ApplicationContainer:
    """Instantiate concrete runtime adapters in the single composition root."""
    selected_clock = UtcClock() if clock is None else clock
    required = settings.required
    optional = settings.optional
    database = DatabaseRuntime.create(
        required.database_url,
        EngineOptions.from_settings(optional),
    )
    metric_registry = TelemetryMetricRegistry()
    observability_settings = settings.observability
    if observability_settings.otlp_endpoint is None:
        telemetry = TelemetryRuntime(registry=metric_registry)
    else:
        exporter = OtlpHttpExporter(
            observability_settings.otlp_endpoint,
            service="accos-core",
            environment=optional.environment,
            timeout_seconds=observability_settings.otlp_timeout_seconds,
            interval_seconds=observability_settings.otlp_export_interval_seconds,
            outcome=lambda signal, outcome: metric_registry.increment(
                "accos_telemetry_exports_total", signal=signal, outcome=outcome
            ),
        )
        telemetry = TelemetryRuntime(exporter, registry=metric_registry)
    runtime_monitor = PostgresRedisRuntimeMonitor(
        database.sessions,
        database.engine,
        required.redis_url,
        selected_clock,
        timeout_seconds=min(
            observability_settings.otlp_timeout_seconds,
            optional.health_timeout_seconds,
        ),
        heartbeat_ttl_seconds=observability_settings.runtime_heartbeat_ttl_seconds,
    )
    resilience_settings = settings.resilience
    resilience = ResilienceExecutor(
        ResiliencePolicy(
            timeout_seconds=resilience_settings.timeout_seconds,
            max_attempts=resilience_settings.max_attempts,
            backoff_seconds=resilience_settings.backoff_seconds,
            max_backoff_seconds=resilience_settings.max_backoff_seconds,
            circuit_failure_threshold=resilience_settings.circuit_failure_threshold,
            circuit_cooldown_seconds=resilience_settings.circuit_cooldown_seconds,
            concurrency_limit=resilience_settings.concurrency_limit,
        )
    )
    security = settings.security
    if identity_provider is None:
        if security.dev_identity_enabled:
            if security.dev_identity_token is None:
                raise ConfigurationError("Enabled development identity requires a credential.")
            if (security.dev_identity_approver_token is None) != (
                security.dev_identity_approver_actor_id is None
            ):
                raise ConfigurationError(
                    "Development approver requires both a credential and actor ID."
                )
            selected_identity_provider: IdentityProvider = DevelopmentIdentityProvider(
                security.dev_identity_token,
                security.dev_identity_approver_token,
            )
        else:
            selected_identity_provider = RejectingIdentityProvider()
    else:
        selected_identity_provider = identity_provider
    identity_repository = SqlAlchemyIdentityRepository(database.sessions)
    audit_store = SqlAlchemyAuditStore(database.sessions)
    account_store = SqlAccountStore(database.sessions)
    authorizer = AuthorizationService(
        audit_store,
        selected_clock,
        LiveScopeAccess(account_store, selected_clock, identity_repository),
    )
    accounts = AccountService(
        account_store,
        authorizer,
        selected_clock,
        settings.auth,
        CredentialCipher(settings.auth.secret_keys, settings.auth.active_key_id),
        password_hash,
        password_matches,
        external_secret,
        HttpOidcClient(settings.auth),
        audit_store,
    )
    approval_policies = ApprovalPolicyResolver(accounts)
    selected_identity_provider = PersistentIdentityProvider(
        account_store, selected_identity_provider
    )
    control_store = SqlAlchemyControlRequestStore(database.sessions)
    identity_runtime = IdentityRuntime(
        database.sessions,
        actor_id=security.dev_identity_actor_id,
        workspace_id=security.dev_identity_workspace_id,
        approver_actor_id=security.dev_identity_approver_actor_id,
        enabled=security.dev_identity_enabled,
    )
    upload_policy = DefaultUploadSecurityPolicy()
    identity = IdentityServices(
        authenticator=IdentityAuthenticator(
            selected_identity_provider, identity_repository, selected_clock
        ),
        authorizer=authorizer,
        creator_control=CreatorControlService(
            authorizer, control_store, selected_clock, approval_policies
        ),
        accounts=accounts,
        upload_policy=upload_policy,
        query=IdentityQueryService(identity_repository, authorizer),
        rate_limiter=InMemoryRateLimiter(
            max_requests=resilience_settings.rate_limit_requests,
            window_seconds=resilience_settings.rate_limit_window_seconds,
        ),
    )
    project_repository = SqlAlchemyProjectRepository(database.sessions)
    project_service = ProjectService(project_repository, authorizer, selected_clock)
    asset_repository = SqlAlchemyAssetRepository(database.sessions)
    raw_object_storage = MinioObjectStorage(
        endpoint=required.s3_endpoint,
        bucket=required.s3_bucket,
        access_key=required.s3_access_key,
        secret_key=required.s3_secret_key,
        secure=optional.s3_use_ssl,
        region=optional.s3_region,
        timeout_seconds=resilience_settings.timeout_seconds,
    )
    object_storage = ResilientObjectStorage(raw_object_storage, resilience, telemetry)
    assets = AssetServices(
        AssetService(
            asset_repository,
            projects=project_repository,
            storage=object_storage,
            scanner=UnconfiguredContentScanner(),
            legacy_bucket=required.s3_bucket,
            upload_policy=upload_policy,
            authorizer=authorizer,
            clock=selected_clock,
        ),
        asset_repository,
        object_storage,
        OrphanCollector(database.sessions, object_storage, selected_clock),
        VersionDownloadSigner(settings.auth, selected_clock),
    )
    projects = ProjectServices(
        project_service,
        project_repository,
        ContentService(
            SqlAlchemyContentRepository(database.sessions),
            project_service,
            assets.service,
            selected_clock,
        ),
    )
    knowledge_repository = SqlAlchemyKnowledgeRepository(database.sessions)
    knowledge_embedder = FakeEmbedder()
    knowledge_index = PgVectorIndex(database.sessions)
    knowledge_graph = SqlAlchemyGraphProjection(database.sessions)
    knowledge_retriever = DefaultRetriever(
        knowledge_repository, knowledge_embedder, knowledge_index
    )
    knowledge_service = KnowledgeService(
        knowledge_repository,
        source_reader=AssetSourceReader(asset_repository, object_storage),
        extractor=TextMarkdownExtractor(),
        normalizer=DeterministicNormalizer(),
        chunker=DeterministicChunker(),
        embedder=knowledge_embedder,
        index=knowledge_index,
        verifier=NotConfiguredVerificationProvider(),
        graph=knowledge_graph,
        retriever=knowledge_retriever,
        projects=project_repository,
        authorizer=authorizer,
        clock=selected_clock,
    )
    knowledge = KnowledgeServices(
        knowledge_service,
        ResearchService(knowledge_service),
        knowledge_repository,
        knowledge_retriever,
        knowledge_index,
        knowledge_graph,
    )
    memory_repository = SqlAlchemyMemoryRepository(database.sessions)
    memory_retention = DefaultRetentionPolicy()
    memory_projection = RedisMemoryProjection(
        required.redis_url, timeout_seconds=resilience_settings.timeout_seconds
    )
    memory = MemoryServices(
        MemoryService(
            memory_repository,
            project_repository,
            authorizer,
            DeterministicMemoryCompressor(),
            ProposalConflictResolver(),
            selected_clock,
        ),
        ContextBuilder(
            memory_repository,
            project_repository,
            authorizer,
            MemoryAccessPolicy(memory_repository, authorizer),
            FakeSemanticMemoryRanker(memory_retention),
            selected_clock,
        ),
        memory_repository,
        memory_projection,
        MemoryProjectionRebuilder(memory_repository, memory_projection),
    )
    creative_repository = SqlAlchemyCreativeRepository(database.sessions)
    creative_application = CreativeApplication(
        creative_repository,
        CreativeAccess(project_repository, authorizer),
        selected_clock,
    )
    creative_extensions = null_creative_extensions()
    creator_signal_ingest = RepositoryPreferenceSignalIngestPort(
        creative_repository, selected_clock
    )
    creative = CreativeServices(
        NovelService(creative_application),
        WorldService(creative_application),
        CharacterService(creative_application),
        CreatorService(creative_application, creator_signal_ingest),
        CreativeCatalog(creative_application),
        creative_repository,
        creative_extensions,
        CreativeRevisionService(creative_application),
    )
    consistency_repository = SqlAlchemyConsistencyRepository(database.sessions)
    consistency = ConsistencyServices(
        ConsistencyService(
            consistency_repository,
            ConsistencyAccess(project_repository, authorizer),
            default_validator_registry(),
            CreativeFactRevisionAdapter(creative.revisions),
            selected_clock,
        ),
        consistency_repository,
    )
    quality_repository = SqlAlchemyQualityRepository(database.sessions)
    quality = QualityServices(
        QualityService(
            quality_repository,
            QualityAccess(project_repository, authorizer),
            StructuralQualityEvaluator(),
            selected_clock,
        ),
        quality_repository,
    )
    feedback_repository = SqlAlchemyFeedbackRepository(database.sessions)
    feedback_registry = MetricRegistry()
    feedback = FeedbackServices(
        FeedbackService(
            feedback_repository,
            FeedbackAccess(project_repository, authorizer),
            feedback_registry,
            SystemDoctor(default_diagnostic_rules()),
            creator_signal_ingest,
            selected_clock,
        ),
        feedback_repository,
        feedback_registry,
    )
    evolution_memory = SqlAlchemyEvolutionMemory(database.sessions)
    evolution = EvolutionServices(
        EvolutionService(
            evolution_memory,
            EvolutionAccess(project_repository, authorizer),
            DiagnosticObserver(),
            DeterministicAnalyzer(),
            ProposalPlanner(),
            DryRunSimulationEnvironment(),
            ReadOnlyVersionManager(),
            ImmutableSafetyController(),
            selected_clock,
            approval_policies,
        ),
        evolution_memory,
    )
    extension_flags = settings.features.extension_values()
    if extension_flags["graph"]:
        extension_graph: GraphStore = SqlAlchemyExtensionGraphStore(database.sessions)
        configured_extensions = frozenset({ExtensionCapability.GRAPH})
    else:
        extension_graph = NullGraphStore()
        configured_extensions = frozenset()
    extensions = ExtensionServices(
        catalog=ExtensionCatalog(
            default_manifests(),
            MappingProxyType(extension_flags),
            configured_extensions,
        ),
        multimodal=MappingProxyType(
            {
                ExtensionCapability.MULTIMODAL_IMAGE: MultimodalBoundary(
                    extension_flags["multimodal_image"], NullMultimodalAdapter()
                ),
                ExtensionCapability.MULTIMODAL_AUDIO: MultimodalBoundary(
                    extension_flags["multimodal_audio"], NullMultimodalAdapter()
                ),
                ExtensionCapability.MULTIMODAL_VIDEO: MultimodalBoundary(
                    extension_flags["multimodal_video"], NullMultimodalAdapter()
                ),
                ExtensionCapability.MULTIMODAL_THREE_D: MultimodalBoundary(
                    extension_flags["multimodal_three_d"], NullMultimodalAdapter()
                ),
            }
        ),
        graph=extension_graph,
        collaboration=CollaborationBoundary(
            extension_flags["collaboration"], NullCollaborationAdapter()
        ),
        rights=RightsBoundary(extension_flags["rights"], NullRightsAdapter()),
        marketplace=DeferredBoundary(extension_flags["marketplace"], NullMarketplaceAdapter()),
        reputation=DeferredBoundary(extension_flags["reputation"], NullReputationAdapter()),
        growth=DeferredBoundary(extension_flags["growth"], NullGrowthAdapter()),
        acquisition=DeferredBoundary(
            extension_flags["knowledge_network"], NullAcquisitionProvider()
        ),
        research_team=DeferredBoundary(
            extension_flags["knowledge_network"], NullResearchTeamProvider()
        ),
        verification=DeferredBoundary(
            extension_flags["knowledge_network"], NullExternalVerificationProvider()
        ),
    )
    workflow_repository = SqlAlchemyWorkflowRepository(database.sessions)
    workflow_consumer_database = DatabaseRuntime.create_unpooled(
        required.database_url,
        name="workflow-consumer-persistence",
    )
    workflow_consumer_repository = SqlAlchemyWorkflowRepository(workflow_consumer_database.sessions)
    consumer_authorizer = AuthorizationService(
        SqlAlchemyAuditStore(workflow_consumer_database.sessions), selected_clock
    )
    consumer_projects = SqlAlchemyProjectRepository(workflow_consumer_database.sessions)
    consumer_assets = SqlAlchemyAssetRepository(workflow_consumer_database.sessions)
    consumer_knowledge_repository = SqlAlchemyKnowledgeRepository(
        workflow_consumer_database.sessions
    )
    consumer_memory_repository = SqlAlchemyMemoryRepository(workflow_consumer_database.sessions)
    consumer_creative_repository = SqlAlchemyCreativeRepository(workflow_consumer_database.sessions)
    consumer_consistency_repository = SqlAlchemyConsistencyRepository(
        workflow_consumer_database.sessions
    )
    consumer_quality_repository = SqlAlchemyQualityRepository(workflow_consumer_database.sessions)
    consumer_knowledge_index = PgVectorIndex(workflow_consumer_database.sessions)
    consumer_knowledge_graph = SqlAlchemyGraphProjection(workflow_consumer_database.sessions)
    consumer_knowledge_retriever = DefaultRetriever(
        consumer_knowledge_repository, knowledge_embedder, consumer_knowledge_index
    )
    consumer_knowledge_service = KnowledgeService(
        consumer_knowledge_repository,
        source_reader=AssetSourceReader(consumer_assets, object_storage),
        extractor=TextMarkdownExtractor(),
        normalizer=DeterministicNormalizer(),
        chunker=DeterministicChunker(),
        embedder=knowledge_embedder,
        index=consumer_knowledge_index,
        verifier=NotConfiguredVerificationProvider(),
        graph=consumer_knowledge_graph,
        retriever=consumer_knowledge_retriever,
        projects=consumer_projects,
        authorizer=consumer_authorizer,
        clock=selected_clock,
    )
    model_registry = ModelRegistry()
    fixture_mode = settings.models.mode in {"test", "demo"}
    if fixture_mode:
        model_registry.register(FakeModelProvider())
    else:
        model_registry.register(NullModelProvider("configuration-required", capabilities=frozenset({ModelCapability.TEXT, ModelCapability.EMBEDDING})))
    model_registry.register(NullModelProvider())
    model_ledger = SqlAlchemyUsageLedger(workflow_consumer_database.sessions)
    model_gateway = ModelGateway(
        model_registry,
        model_ledger,
        consumer_authorizer,
        selected_clock,
        ModelPolicy(
            ("fake-model" if fixture_mode else "configuration-required",),
            "fake-model" if fixture_mode else "configuration-required",
            timeout_seconds=resilience_settings.timeout_seconds,
            retries_per_provider=resilience_settings.max_attempts - 1,
            retry_backoff_seconds=resilience_settings.backoff_seconds,
            total_attempt_limit=resilience_settings.max_attempts,
            circuit_failure_threshold=resilience_settings.circuit_failure_threshold,
            circuit_cooldown_seconds=resilience_settings.circuit_cooldown_seconds,
            concurrency_limit=resilience_settings.concurrency_limit,
        ),
    )
    tool_registry = ToolRegistry()
    fixture_tool_descriptor = ToolDescriptor(
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
    if fixture_mode:
        tool_registry.register(fixture_tool_descriptor, FakeToolExecutor())
    model_runtime = build_model_runtime(settings, workflow_consumer_database.sessions, raw_object_storage, selected_clock)
    if not fixture_mode:
        tool_registry.register(content_tool_descriptor(), ContentReadTool(cast(AssetService, model_runtime.content)))
    tool_ledger = SqlAlchemyToolCallLedger(workflow_consumer_database.sessions)
    tool_gateway = ToolGateway(
        tool_registry,
        tool_ledger,
        model_runtime.accounts.authorizer,
        selected_clock,
    )
    models = ModelServices(
        model_gateway, model_registry, model_ledger, WorkspaceSecretProvider(accounts), model_runtime
    )
    tools = ToolServices(tool_gateway, tool_registry, tool_ledger)
    agent_registry = InMemoryAgentRegistry()
    for descriptor in (built_in_agent_descriptors() if fixture_mode else real_descriptors(tuple(model_runtime.prompts.builtins.values()))):
        agent_registry.register(descriptor)
    agent_repository = SqlAlchemyAgentRepository(workflow_consumer_database.sessions)
    agent_metrics = InMemoryAgentMetrics()
    agent_executor: AgentExecutor = FakeAgentExecutor(model_gateway, tool_gateway) if fixture_mode else RealAgentExecutor(model_runtime, tool_gateway, tool_registry)
    agent_supervisor = DefaultAgentSupervisor(
        agent_registry,
        agent_executor,
        agent_repository,
        consumer_projects,
        model_runtime.accounts.authorizer,
        agent_metrics,
        selected_clock,
        DEFAULT_AGENT_BUDGET if fixture_mode else REAL_AGENT_BUDGET,
        {item.tool_id: item.version for item in tool_registry.tools},
        consumer_memory_repository,
    )
    workflow_service = WorkflowService(
        workflow_repository,
        project_repository,
        authorizer,
        selected_clock,
        approval_policies,
    )
    consumer_creative_application = CreativeApplication(
        consumer_creative_repository,
        CreativeAccess(consumer_projects, consumer_authorizer),
        selected_clock,
    )
    consumer_consistency_service = ConsistencyService(
        consumer_consistency_repository,
        ConsistencyAccess(consumer_projects, consumer_authorizer),
        default_validator_registry(),
        CreativeFactRevisionAdapter(CreativeRevisionService(consumer_creative_application)),
        selected_clock,
    )
    consumer_quality_service = QualityService(
        consumer_quality_repository,
        QualityAccess(consumer_projects, consumer_authorizer),
        StructuralQualityEvaluator(),
        selected_clock,
    )
    workflow_executor = CanonQualityWorkflowExecutor(
        CreativeWorkflowExecutor(
            KnowledgeWorkflowExecutor(
                AgentWorkflowExecutor(
                    FrameworkSmokeExecutor(),
                    agent_supervisor,
                    AgentBudget(2, 1, 1, 10.0, 2, 64),
                ),
                consumer_knowledge_service,
            ),
            CreativeCatalog(consumer_creative_application),
        ),
        PersistedCanonQualityGate(
            consumer_consistency_service,
            consumer_quality_service,
        ),
    )
    workflow_worker = WorkflowWorker(
        workflow_consumer_repository,
        workflow_executor,
        selected_clock,
    )
    celery_app: Any | None = None
    if event_publisher is None:
        celery_app = create_celery_app(
            required.redis_url,
            timeout_seconds=resilience_settings.timeout_seconds,
            max_retries=resilience_settings.max_attempts - 1,
        )
        register_celery_consumer(celery_app, workflow_worker.handle)
        selected_publisher: EventPublisher = CeleryEventPublisher(celery_app)
    else:
        selected_publisher = event_publisher
    workflow_relay = OutboxRelay(
        SqlAlchemyOutboxRepository(database.sessions, selected_clock),
        selected_publisher,
    )
    workflows = WorkflowServices(
        workflow_service,
        workflow_worker,
        workflow_repository,
        workflow_consumer_database,
        workflow_executor,
        workflow_relay,
        celery_app,
    )
    agents = AgentServices(
        agent_registry,
        agent_executor,
        agent_supervisor,
        agent_repository,
        agent_metrics,
        MasterOrchestrator(agent_supervisor, workflow_service, agent_repository),
        AgentJobService(SqlAgentJobStore(workflow_consumer_database.sessions), model_runtime, agent_supervisor, agent_registry),
    )
    if probes is None:
        selected_probes: tuple[HealthProbe, ...] = (
            DatabaseHealthProbe(database.engine),
            RedisHealthProbe(required.redis_url, optional.health_timeout_seconds),
            S3HealthProbe(
                endpoint=required.s3_endpoint,
                bucket=required.s3_bucket,
                access_key=required.s3_access_key,
                secret_key=required.s3_secret_key,
                secure=optional.s3_use_ssl,
                region=optional.s3_region,
                timeout_seconds=optional.health_timeout_seconds,
            ),
            AiProviderHealthProbe(
                enabled=settings.features.real_provider_calls_enabled,
                provider=optional.ai_provider,
            ),
        )
    else:
        selected_probes = probes
    lifecycle_logger = get_logger("lifecycle")
    modules = ModuleRegistry(
        (
            telemetry,
            RuntimeMarkerModule("kernel", lifecycle_logger),
            database,
            workflow_consumer_database,
            identity_runtime,
            RuntimeMarkerModule("projects", lifecycle_logger),
            RuntimeMarkerModule("assets", lifecycle_logger),
            RuntimeMarkerModule("knowledge", lifecycle_logger),
            RuntimeMarkerModule("memory", lifecycle_logger),
            RuntimeMarkerModule("creative", lifecycle_logger),
            RuntimeMarkerModule("consistency", lifecycle_logger),
            RuntimeMarkerModule("quality", lifecycle_logger),
            RuntimeMarkerModule("feedback", lifecycle_logger),
            RuntimeMarkerModule("evolution", lifecycle_logger),
            RuntimeMarkerModule("extensions", lifecycle_logger),
            RuntimeMarkerModule("models", lifecycle_logger),
            RuntimeMarkerModule("tools", lifecycle_logger),
            RuntimeMarkerModule("agents", lifecycle_logger),
            RuntimeMarkerModule("workflows", lifecycle_logger),
            RuntimeMarkerModule("health", lifecycle_logger),
        )
    )
    health = HealthService(
        probes=selected_probes,
        clock=selected_clock,
        version=__version__,
        timeout_seconds=optional.health_timeout_seconds,
    )
    return ApplicationContainer(
        settings=settings,
        health=health,
        database=database,
        identity=identity,
        projects=projects,
        assets=assets,
        knowledge=knowledge,
        memory=memory,
        creative=creative,
        consistency=consistency,
        quality=quality,
        feedback=feedback,
        evolution=evolution,
        extensions=extensions,
        models=models,
        tools=tools,
        agents=agents,
        workflows=workflows,
        observability=ObservabilityServices(telemetry, runtime_monitor),
        modules=modules,
    )
