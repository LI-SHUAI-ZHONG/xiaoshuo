from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4, uuid5

import pytest

from accos.adapters.assets import InMemoryObjectStorage
from accos.adapters.knowledge import (
    AssetSourceReader,
    DeterministicChunker,
    DeterministicNormalizer,
    FakeEmbedder,
    FixedVerificationProvider,
    InMemoryGraphProjection,
    InMemoryVectorIndex,
    NotConfiguredExternalSourceReader,
    NotConfiguredExtractor,
    NotConfiguredVerificationProvider,
    PgVectorIndex,
    TextMarkdownExtractor,
)
from accos.kernel.errors import IdempotencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.assets.public import (
    Asset,
    AssetRepository,
    AssetStatus,
    AssetVersion,
    ProcessingStatus,
    ScanStatus,
)
from accos.modules.identity.application import AuthorizationService
from accos.modules.identity.domain import POLICY_VERSION, Role, permissions_for
from accos.modules.knowledge.public import (
    Chunk,
    Chunker,
    Citation,
    DefaultRetriever,
    Document,
    DocumentVersion,
    Embedder,
    EmbeddingRef,
    Extractor,
    IngestionBundle,
    IngestionRun,
    IngestionStatus,
    KnowledgeEdge,
    KnowledgeErrorCode,
    KnowledgePipelineError,
    KnowledgeRepository,
    KnowledgeService,
    KnowledgeSource,
    KnowledgeWorkflowExecutor,
    Normalizer,
    RelationKind,
    ResearchRequest,
    ResearchService,
    ResearchStatus,
    RetrievalFilter,
    RetrievalRequest,
    SourceReader,
    SourceSnapshot,
    VectorIndex,
    VectorMatch,
    VerificationPolicy,
    VerificationProvider,
    VerificationStatus,
    knowledge_ingestion_definition,
)
from accos.modules.projects.public import (
    Project,
    ProjectRepository,
    ProjectSettings,
    ProjectStatus,
)
from accos.modules.workflows.public import (
    PermanentStepError,
    RetryableStepError,
    StepExecution,
    StepExecutionResult,
    StepExecutor,
    StepKind,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.modules.identity.ports import AuditEvent

NOW = datetime(2026, 9, 5, tzinfo=UTC)


@dataclass(slots=True)
class Clock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value


class Audit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class Projects:
    def __init__(self, *items: Project) -> None:
        self.items = {(item.workspace_id, item.id): item for item in items}

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        return self.items.get((workspace_id, project_id))


class Sources:
    def __init__(self, snapshot: SourceSnapshot, data: bytes) -> None:
        self.current = snapshot
        self.data = {snapshot.object_key: data}
        self.read_error: KnowledgePipelineError | None = None

    async def resolve(self, workspace_id: UUID, project_id: UUID, asset_id: UUID) -> SourceSnapshot:
        if (
            self.current.workspace_id != workspace_id
            or self.current.project_id != project_id
            or self.current.asset_id != asset_id
        ):
            raise KnowledgePipelineError(
                KnowledgeErrorCode.SOURCE_UNAVAILABLE,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        return self.current

    async def read(self, source: SourceSnapshot) -> bytes:
        if self.read_error is not None:
            raise self.read_error
        return self.data[source.object_key]


class Repository:
    def __init__(self) -> None:
        self.bundles: dict[UUID, IngestionBundle] = {}
        self.keys: dict[tuple[UUID, str], UUID] = {}
        self.sources: dict[tuple[UUID, UUID], UUID] = {}
        self.documents: dict[tuple[UUID, UUID, UUID], UUID] = {}

    async def reserve(  # noqa: PLR0913
        self,
        snapshot: SourceSnapshot,
        *,
        verification_policy: VerificationPolicy,
        idempotency_key: str,
        requested_by: UUID,
        correlation_id: UUID,
        now: datetime,
    ) -> tuple[IngestionRun, bool]:
        key = (snapshot.workspace_id, idempotency_key)
        if key in self.keys:
            bundle = self.bundles[self.keys[key]]
            if (
                bundle.source.asset_version_id != snapshot.asset_version_id
                or bundle.run.verification_policy is not verification_policy
            ):
                raise IdempotencyConflictError
            return bundle.run, False
        source_key = (snapshot.workspace_id, snapshot.asset_version_id)
        if source_key in self.sources:
            bundle = self.bundles[self.sources[source_key]]
            if bundle.run.verification_policy is not verification_policy:
                raise IdempotencyConflictError
            return bundle.run, False
        document_key = (snapshot.workspace_id, snapshot.project_id, snapshot.asset_id)
        document_id = self.documents.setdefault(document_key, uuid4())
        source_id, version_id, run_id = uuid4(), uuid4(), uuid4()
        source = _source(snapshot, source_id, now)
        document = _document(snapshot, document_id, now)
        version = _version(snapshot, document_id, source_id, version_id, now)
        run = IngestionRun(
            run_id,
            snapshot.workspace_id,
            snapshot.project_id,
            source_id,
            document_id,
            version_id,
            IngestionStatus.UPLOADED,
            verification_policy,
            VerificationStatus.NOT_CONFIGURED,
            idempotency_key,
            requested_by,
            correlation_id,
            1,
            now,
            now,
        )
        self.bundles[run_id] = IngestionBundle(run, source, document, version)
        self.keys[key] = run_id
        self.sources[source_key] = run_id
        return run, True

    async def load(self, workspace_id: UUID, run_id: UUID) -> IngestionBundle | None:
        bundle = self.bundles.get(run_id)
        return bundle if bundle is not None and bundle.run.workspace_id == workspace_id else None

    async def get_document(
        self, workspace_id: UUID, project_id: UUID, document_id: UUID
    ) -> Document | None:
        return next(
            (
                bundle.document
                for bundle in self.bundles.values()
                if (bundle.document.workspace_id, bundle.document.project_id, bundle.document.id)
                == (workspace_id, project_id, document_id)
            ),
            None,
        )

    async def set_status(
        self,
        workspace_id: UUID,
        run_id: UUID,
        status: str,
        *,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        selected = IngestionStatus(status)
        return self._store(
            bundle,
            replace(bundle.run, status=selected, updated_at=now),
            replace(bundle.version, status=selected, updated_at=now),
        ).run

    async def save_normalized(
        self,
        workspace_id: UUID,
        run_id: UUID,
        text: str,
        *,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        return self._store(
            bundle,
            replace(bundle.run, status=IngestionStatus.NORMALIZED, updated_at=now),
            replace(
                bundle.version,
                status=IngestionStatus.NORMALIZED,
                normalized_text=text,
                updated_at=now,
            ),
        ).run

    async def replace_chunks(
        self,
        workspace_id: UUID,
        run_id: UUID,
        chunks: tuple[Chunk, ...],
        *,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        updated = self._store(
            bundle,
            replace(bundle.run, status=IngestionStatus.CHUNKED, updated_at=now),
            replace(bundle.version, status=IngestionStatus.CHUNKED, updated_at=now),
        )
        self.bundles[run_id] = replace(updated, chunks=chunks, embeddings=())
        return self.bundles[run_id].run

    async def replace_embeddings(
        self,
        workspace_id: UUID,
        run_id: UUID,
        embeddings: tuple[EmbeddingRef, ...],
        *,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        updated = self._store(
            bundle,
            replace(bundle.run, status=IngestionStatus.EMBEDDED, updated_at=now),
            replace(bundle.version, status=IngestionStatus.EMBEDDED, updated_at=now),
        )
        self.bundles[run_id] = replace(updated, embeddings=embeddings)
        return self.bundles[run_id].run

    async def complete(
        self,
        workspace_id: UUID,
        run_id: UUID,
        verification_status: VerificationStatus,
        *,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        if (
            bundle.run.verification_policy is VerificationPolicy.REQUIRED
            and verification_status is not VerificationStatus.VERIFIED
        ):
            raise InvalidStateError("Required knowledge verification did not pass.")
        for other_id, other in tuple(self.bundles.items()):
            if other.document.id == bundle.document.id and other_id != run_id:
                self.bundles[other_id] = replace(
                    other, version=replace(other.version, active=False)
                )
        return self._store(
            bundle,
            replace(
                bundle.run,
                status=IngestionStatus.READY,
                verification_status=verification_status,
                updated_at=now,
            ),
            replace(
                bundle.version,
                status=IngestionStatus.READY,
                verification_status=verification_status,
                active=True,
                updated_at=now,
            ),
        ).run

    async def fail(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        failed_stage: str,
        error_code: str,
        retryable: bool,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        stage = IngestionStatus(failed_stage)
        return self._store(
            bundle,
            replace(
                bundle.run,
                status=IngestionStatus.FAILED,
                failed_stage=stage,
                error_code=KnowledgeErrorCode(error_code),
                retryable=retryable,
                updated_at=now,
            ),
            replace(bundle.version, status=IngestionStatus.FAILED, updated_at=now),
        ).run

    async def restart(
        self,
        workspace_id: UUID,
        run_id: UUID,
        *,
        rebuild: bool,
        now: datetime,
    ) -> IngestionRun:
        bundle = self._bundle(workspace_id, run_id)
        target = IngestionStatus.UPLOADED if rebuild else bundle.run.failed_stage
        if target is None:
            raise InvalidStateError("missing failed stage")
        run = replace(
            bundle.run,
            status=target,
            failed_stage=None,
            error_code=None,
            retryable=False,
            attempt=bundle.run.attempt + 1,
            updated_at=now,
        )
        version = replace(
            bundle.version,
            status=target,
            normalized_text=None if rebuild else bundle.version.normalized_text,
            active=False if rebuild else bundle.version.active,
            verification_status=(
                VerificationStatus.NOT_CONFIGURED if rebuild else bundle.version.verification_status
            ),
            updated_at=now,
        )
        self.bundles[run_id] = IngestionBundle(
            run,
            bundle.source,
            bundle.document,
            version,
            () if rebuild else bundle.chunks,
            () if rebuild else bundle.embeddings,
        )
        return run

    async def ready_version_ids(
        self,
        workspace_id: UUID,
        project_id: UUID,
        filters: RetrievalFilter,
    ) -> tuple[UUID, ...]:
        return tuple(
            bundle.version.id
            for bundle in self.bundles.values()
            if bundle.run.workspace_id == workspace_id
            and bundle.run.project_id == project_id
            and bundle.version.status is IngestionStatus.READY
            and bundle.version.active
            and (not filters.source_ids or bundle.source.id in filters.source_ids)
            and (
                not filters.document_version_ids
                or bundle.version.id in filters.document_version_ids
            )
            and (
                not filters.verification_statuses
                or bundle.version.verification_status in filters.verification_statuses
            )
        )

    async def chunks_and_citations(
        self,
        workspace_id: UUID,
        project_id: UUID,
        chunk_ids: tuple[UUID, ...],
    ) -> tuple[tuple[Chunk, Citation], ...]:
        selected = frozenset(chunk_ids)
        result: list[tuple[Chunk, Citation]] = []
        for bundle in self.bundles.values():
            if (
                bundle.run.workspace_id != workspace_id
                or bundle.run.project_id != project_id
                or not bundle.version.active
            ):
                continue
            result.extend(
                (chunk, _citation(bundle, chunk)) for chunk in bundle.chunks if chunk.id in selected
            )
        return tuple(result)

    def _bundle(self, workspace_id: UUID, run_id: UUID) -> IngestionBundle:
        bundle = self.bundles[run_id]
        if bundle.run.workspace_id != workspace_id:
            raise InvalidStateError("wrong scope")
        return bundle

    def _store(
        self,
        bundle: IngestionBundle,
        run: IngestionRun,
        version: DocumentVersion,
    ) -> IngestionBundle:
        updated = replace(bundle, run=run, version=version)
        self.bundles[run.id] = updated
        return updated


class FallbackExecutor:
    def __init__(self) -> None:
        self.executions: list[StepExecution] = []
        self.compensations: list[str] = []

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        self.executions.append(execution)
        return StepExecutionResult("workflow-output://fallback")

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        del execution
        self.compensations.append(hook)


def _fixture() -> tuple[
    SecurityContext,
    Project,
    SourceSnapshot,
    bytes,
]:
    actor_id, workspace_id, project_id, asset_id, version_id = (uuid4() for _ in range(5))
    context = SecurityContext(
        actor_id,
        ActorKind.USER,
        workspace_id,
        permissions_for(Role.OWNER),
        POLICY_VERSION,
        CorrelationIds(str(uuid4()), str(uuid4())),
        project_id=project_id,
    )
    project = Project(
        project_id,
        workspace_id,
        "fixture-project",
        ProjectStatus.ACTIVE,
        ProjectSettings(),
        actor_id,
        NOW,
        NOW,
    )
    data = b"fixture-alpha\n\nfixture-beta"
    snapshot = SourceSnapshot(
        workspace_id,
        project_id,
        asset_id,
        version_id,
        1,
        "assets/fixture.txt",
        hashlib.sha256(data).hexdigest(),
        "text/plain",
    )
    return context, project, snapshot, data


def _services(  # noqa: PLR0913
    *,
    verifier: VerificationProvider | None = None,
    embedder: Embedder | None = None,
    index: VectorIndex | None = None,
    extractor: Extractor | None = None,
    normalizer: Normalizer | None = None,
    chunker: Chunker | None = None,
    source_reader: SourceReader | None = None,
) -> tuple[
    KnowledgeService,
    Repository,
    Sources,
    VectorIndex,
    InMemoryGraphProjection,
    SecurityContext,
    Project,
]:
    context, project, snapshot, data = _fixture()
    repository = Repository()
    sources = Sources(snapshot, data)
    selected_embedder = embedder or FakeEmbedder()
    selected_index = index or InMemoryVectorIndex()
    graph = InMemoryGraphProjection()
    retriever = DefaultRetriever(repository, selected_embedder, selected_index)
    clock = Clock()
    service = KnowledgeService(
        cast("KnowledgeRepository", repository),
        source_reader=source_reader if source_reader is not None else cast("SourceReader", sources),
        extractor=extractor if extractor is not None else TextMarkdownExtractor(),
        normalizer=normalizer if normalizer is not None else DeterministicNormalizer(),
        chunker=chunker if chunker is not None else DeterministicChunker(max_characters=64),
        embedder=selected_embedder,
        index=selected_index,
        verifier=verifier if verifier is not None else NotConfiguredVerificationProvider(),
        graph=graph,
        retriever=retriever,
        projects=cast("ProjectRepository", Projects(project)),
        authorizer=AuthorizationService(Audit(), clock),
        clock=clock,
    )
    return service, repository, sources, selected_index, graph, context, project


def test_processors_and_in_memory_projection_contracts() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        _context, _project, snapshot, data = _fixture()
        extractor = TextMarkdownExtractor()
        assert await extractor.extract(snapshot, data) == data.decode()
        with pytest.raises(KnowledgePipelineError) as unsupported:
            await extractor.extract(replace(snapshot, media_type="application/pdf"), data)
        assert unsupported.value.code is KnowledgeErrorCode.EXTRACTOR_NOT_CONFIGURED
        for invalid in (b"", b"\xff"):
            with pytest.raises(KnowledgePipelineError) as extraction:
                await extractor.extract(snapshot, invalid)
            assert extraction.value.code is KnowledgeErrorCode.EXTRACTION_FAILED
        for media_type in (
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            with pytest.raises(KnowledgePipelineError) as deferred_parser:
                await NotConfiguredExtractor().extract(
                    replace(snapshot, media_type=media_type), data
                )
            assert deferred_parser.value.code is KnowledgeErrorCode.EXTRACTOR_NOT_CONFIGURED
            assert not deferred_parser.value.retryable
        external = NotConfiguredExternalSourceReader()
        with pytest.raises(KnowledgePipelineError) as deferred_source:
            await external.resolve(snapshot.workspace_id, snapshot.project_id, snapshot.asset_id)
        assert deferred_source.value.code is KnowledgeErrorCode.SOURCE_NOT_CONFIGURED
        with pytest.raises(KnowledgePipelineError) as deferred_read:
            await external.read(snapshot)
        assert deferred_read.value.code is KnowledgeErrorCode.SOURCE_NOT_CONFIGURED

        normalizer = DeterministicNormalizer()
        assert await normalizer.normalize(" fixture\tvalue\r\n\r\n\r\nnext ") == (
            "fixture value\n\nnext"
        )
        with pytest.raises(KnowledgePipelineError):
            await normalizer.normalize(" \t ")
        with pytest.raises(ValueError, match="at least"):
            DeterministicChunker(max_characters=4)
        chunks = await DeterministicChunker(max_characters=16).chunk("a" * 20 + "\n\nb")
        assert chunks == ("a" * 16, "a" * 4, "b")
        with pytest.raises(KnowledgePipelineError):
            await DeterministicChunker().chunk("")

        with pytest.raises(ValueError, match="8 dimensions"):
            FakeEmbedder(dimensions=3)
        failing = FakeEmbedder(failures_remaining=1)
        with pytest.raises(KnowledgePipelineError) as embedding:
            await failing.embed(("fixture",))
        assert embedding.value.retryable
        vectors = await failing.embed(("fixture", "fixture-other"))
        assert len(vectors) == 2 and len(vectors[0]) == 8
        assert vectors[0] == (await failing.embed(("fixture",)))[0]

        assert (
            await NotConfiguredVerificationProvider().verify(snapshot, "fixture")
            is VerificationStatus.NOT_CONFIGURED
        )
        fixed = FixedVerificationProvider(VerificationStatus.VERIFIED)
        assert await fixed.verify(snapshot, "fixture") is VerificationStatus.VERIFIED

        chunk = Chunk(
            uuid4(),
            snapshot.workspace_id,
            snapshot.project_id,
            uuid4(),
            uuid4(),
            0,
            "fixture",
            hashlib.sha256(b"fixture").hexdigest(),
        )
        embedding_ref = EmbeddingRef(
            uuid4(),
            snapshot.workspace_id,
            snapshot.project_id,
            chunk.id,
            chunk.document_version_id,
            failing.embedder_id,
            8,
            vectors[0],
            chunk.content_hash,
        )
        with pytest.raises(ValueError, match="dimensions"):
            replace(embedding_ref, dimensions=7)
        index = InMemoryVectorIndex()
        await index.replace(
            snapshot.workspace_id,
            snapshot.project_id,
            chunk.document_version_id,
            (embedding_ref,),
        )
        matches = await index.search(
            snapshot.workspace_id,
            snapshot.project_id,
            vectors[0],
            allowed_version_ids=(chunk.document_version_id,),
            top_k=1,
        )
        assert matches[0].score == pytest.approx(1)
        assert (
            await index.search(
                uuid4(),
                snapshot.project_id,
                vectors[0],
                allowed_version_ids=(chunk.document_version_id,),
                top_k=1,
            )
            == ()
        )
        with pytest.raises(ValueError, match="scope"):
            await index.replace(
                snapshot.workspace_id,
                snapshot.project_id,
                chunk.document_version_id,
                (replace(embedding_ref, project_id=uuid4()),),
            )
        with pytest.raises(ValueError, match="dimensions"):
            await index.search(
                snapshot.workspace_id,
                snapshot.project_id,
                (1.0,),
                allowed_version_ids=(chunk.document_version_id,),
                top_k=1,
            )
        index.available = False
        with pytest.raises(KnowledgePipelineError):
            await index.replace(
                snapshot.workspace_id,
                snapshot.project_id,
                chunk.document_version_id,
                (),
            )

        graph = InMemoryGraphProjection()
        await graph.replace(
            snapshot.workspace_id, snapshot.project_id, chunk.document_version_id, ()
        )
        assert graph.items[(snapshot.workspace_id, chunk.document_version_id)] == ()
        with pytest.raises(ValueError, match="scope"):
            await graph.replace(
                snapshot.workspace_id,
                snapshot.project_id,
                chunk.document_version_id,
                (
                    KnowledgeEdge(
                        uuid4(),
                        uuid4(),
                        snapshot.project_id,
                        chunk.document_version_id,
                        "document_version",
                        chunk.document_version_id,
                        RelationKind.CONTAINS,
                        "chunk",
                        chunk.id,
                    ),
                ),
            )

    asyncio.run(scenario())


def test_pgvector_native_query_and_provider_failures_are_stable() -> None:
    def async_context(value: object) -> MagicMock:
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=value)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    async def scenario() -> None:
        workspace_id, project_id, version_id, chunk_id = (uuid4() for _ in range(4))
        query = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        native_result = MagicMock()
        native_result.all.return_value = (SimpleNamespace(chunk_id=chunk_id, score=0.75),)
        native_session = MagicMock()
        native_session.scalar = AsyncMock(return_value=True)
        native_session.execute = AsyncMock(return_value=native_result)
        native_sessions = MagicMock(return_value=async_context(native_session))
        native_index = PgVectorIndex(cast("AsyncSessionFactory", native_sessions))
        matches = await native_index.search(
            workspace_id,
            project_id,
            query,
            allowed_version_ids=(version_id,),
            top_k=1,
        )
        assert matches == (VectorMatch(chunk_id, 0.75),)
        assert "<=>" in str(native_session.execute.await_args.args[0])

        replace_session = MagicMock()
        replace_session.execute = AsyncMock(side_effect=RuntimeError("fixture-private"))
        replace_sessions = MagicMock()
        replace_sessions.begin.return_value = async_context(replace_session)
        failing_replace = PgVectorIndex(cast("AsyncSessionFactory", replace_sessions))
        with pytest.raises(KnowledgePipelineError) as replace_error:
            await failing_replace.replace(workspace_id, project_id, version_id, ())
        assert replace_error.value.code is KnowledgeErrorCode.INDEX_UNAVAILABLE

        search_session = MagicMock()
        search_session.scalar = AsyncMock(side_effect=RuntimeError("fixture-private"))
        search_sessions = MagicMock(return_value=async_context(search_session))
        failing_search = PgVectorIndex(cast("AsyncSessionFactory", search_sessions))
        with pytest.raises(KnowledgePipelineError) as search_error:
            await failing_search.search(
                workspace_id,
                project_id,
                query,
                allowed_version_ids=(version_id,),
                top_k=1,
            )
        assert search_error.value.code is KnowledgeErrorCode.INDEX_UNAVAILABLE

    asyncio.run(scenario())


def test_full_pipeline_dedup_rebuild_versions_retrieval_and_research() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        service, repository, sources, _index, graph, context, project = _services()
        run = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-ingest"
        )
        duplicate = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-duplicate"
        )
        assert duplicate.id == run.id
        ready = await service.process(context, run.id)
        assert ready.status is IngestionStatus.READY
        assert ready.verification_status is VerificationStatus.NOT_CONFIGURED
        bundle = repository.bundles[run.id]
        assert len(bundle.chunks) == 2
        assert len(bundle.embeddings) == 2
        assert len(graph.items[(context.workspace_id, bundle.version.id)]) == 6
        assert (await service.get(context, run.id)).id == run.id
        assert (
            await service.get_document(context, project.id, bundle.document.id) == bundle.document
        )
        with pytest.raises(ScopeViolationError):
            await service.get_document(context, project.id, uuid4())
        result = await service.retrieve(
            context, project.id, RetrievalRequest("fixture-alpha", top_k=1)
        )
        assert len(result.hits) == 1
        assert result.hits[0].citation.asset_version_id == sources.current.asset_version_id
        assert result.hits[0].citation.verification_status is VerificationStatus.NOT_CONFIGURED
        report = await ResearchService(service).execute(
            context,
            project.id,
            ResearchRequest("research-question://fixture", "fixture-alpha", 1),
        )
        assert report.status is ResearchStatus.COMPLETED
        assert report.citations
        assert report.material_request_reference.startswith("research-material-request://offline/")
        empty = await repository.ready_version_ids(uuid4(), project.id, RetrievalFilter())
        assert empty == ()
        empty_service, _repo, _sources, _idx, _graph, empty_context, empty_project = _services()
        empty_report = await ResearchService(empty_service).execute(
            empty_context,
            empty_project.id,
            ResearchRequest("research-question://empty", "not-indexed", 1),
        )
        assert empty_report.status is ResearchStatus.NO_RESULTS

        rebuilt = await service.rebuild(context, run.id)
        assert rebuilt.status is IngestionStatus.READY
        assert rebuilt.attempt == 2
        assert len(repository.bundles[run.id].chunks) == 2

        old_version_id = repository.bundles[run.id].version.id
        new_data = b"fixture-gamma"
        sources.current = replace(
            sources.current,
            asset_version_id=uuid4(),
            version_number=2,
            object_key="assets/fixture-v2.txt",
            content_hash=hashlib.sha256(new_data).hexdigest(),
        )
        sources.data[sources.current.object_key] = new_data
        second = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-ingest-v2"
        )
        assert second.document_id == run.document_id
        await service.process(context, second.id)
        assert not repository.bundles[run.id].version.active
        assert repository.bundles[second.id].version.active
        assert (
            await service.retrieve(
                context,
                project.id,
                RetrievalRequest(
                    "fixture-alpha",
                    filters=RetrievalFilter(document_version_ids=(old_version_id,)),
                ),
            )
        ).hits == ()
        new_result = await service.retrieve(
            context, project.id, RetrievalRequest("fixture-gamma", top_k=1)
        )
        assert new_result.hits[0].citation.asset_version_id == sources.current.asset_version_id

        sources.current = replace(sources.current, asset_version_id=uuid4(), version_number=3)
        with pytest.raises(IdempotencyConflictError):
            await service.submit(
                context, project.id, sources.current.asset_id, idempotency_key="fixture-ingest"
            )

        other_context = replace(context, workspace_id=uuid4())
        with pytest.raises(ScopeViolationError):
            await service.get(other_context, run.id)
        archived = replace(project, status=ProjectStatus.ARCHIVED)
        archived_service, *_rest = _services()
        archived_service._projects = cast(  # noqa: SLF001
            "ProjectRepository", Projects(archived)
        )
        with pytest.raises(InvalidStateError, match="Archived"):
            await archived_service.retrieve(context, archived.id, RetrievalRequest("fixture"))

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("verification", "expected"),
    [
        (VerificationStatus.NOT_CONFIGURED, KnowledgeErrorCode.VERIFICATION_NOT_CONFIGURED),
        (VerificationStatus.UNVERIFIED, KnowledgeErrorCode.VERIFICATION_UNVERIFIED),
        (VerificationStatus.REJECTED, KnowledgeErrorCode.VERIFICATION_REJECTED),
    ],
)
def test_failure_states_retry_and_verification_are_distinct(
    verification: VerificationStatus,
    expected: KnowledgeErrorCode,
) -> None:
    async def scenario() -> None:
        provider = FixedVerificationProvider(verification)
        service, _repository, sources, _index, _graph, context, project = _services(
            verifier=provider
        )
        run = await service.submit(
            context,
            project.id,
            sources.current.asset_id,
            idempotency_key=f"fixture-verify-{verification.value}",
            verification_policy=VerificationPolicy.REQUIRED,
        )
        failed = await service.process(context, run.id)
        assert failed.status is IngestionStatus.FAILED
        assert failed.failed_stage is IngestionStatus.VERIFYING
        assert failed.error_code is expected
        assert not failed.retryable

    asyncio.run(scenario())


def test_parser_embedding_and_index_failures_are_stable_and_retryable_as_specified() -> None:
    async def scenario() -> None:
        pdf_service, _repo, pdf_sources, _idx, _graph, context, project = _services()
        pdf_sources.current = replace(pdf_sources.current, media_type="application/pdf")
        pdf_run = await pdf_service.submit(
            context, project.id, pdf_sources.current.asset_id, idempotency_key="fixture-pdf"
        )
        pdf_failed = await pdf_service.process(context, pdf_run.id)
        assert pdf_failed.error_code is KnowledgeErrorCode.EXTRACTOR_NOT_CONFIGURED
        assert not pdf_failed.retryable
        with pytest.raises(ScopeViolationError):
            await pdf_service.retry(context, uuid4())

        embedder = FakeEmbedder(failures_remaining=1)
        service, repository, sources, _index, _graph, context, project = _services(
            embedder=embedder
        )
        run = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-embedding"
        )
        failed = await service.process(context, run.id)
        assert failed.error_code is KnowledgeErrorCode.EMBEDDING_FAILED
        assert failed.retryable
        chunk_ids = tuple(item.id for item in repository.bundles[run.id].chunks)
        retried = await service.retry(context, run.id)
        assert retried.status is IngestionStatus.READY and retried.attempt == 2
        assert tuple(item.id for item in repository.bundles[run.id].chunks) == chunk_ids
        with pytest.raises(InvalidStateError, match="Only failed"):
            await service.retry(context, run.id)
        embed_context = context

        index = InMemoryVectorIndex(available=False)
        indexed_service, _repo, indexed_sources, _idx, _graph, context, project = _services(
            index=index
        )
        indexed_run = await indexed_service.submit(
            context,
            project.id,
            indexed_sources.current.asset_id,
            idempotency_key="fixture-index",
        )
        index_failed = await indexed_service.process(context, indexed_run.id)
        assert index_failed.error_code is KnowledgeErrorCode.INDEX_UNAVAILABLE
        index.available = True
        assert (
            await indexed_service.retry(context, indexed_run.id)
        ).status is IngestionStatus.READY

        sources.read_error = KnowledgePipelineError(
            KnowledgeErrorCode.SOURCE_INTEGRITY_FAILED,
            IngestionStatus.EXTRACTING,
            retryable=False,
        )
        integrity = await service.rebuild(embed_context, run.id)
        assert integrity.error_code is KnowledgeErrorCode.SOURCE_INTEGRITY_FAILED

    asyncio.run(scenario())


def test_service_defensive_paths_and_unexpected_provider_failures() -> None:
    class MismatchedSource:
        def __init__(self, snapshot: SourceSnapshot, data: bytes) -> None:
            self.snapshot = replace(snapshot, workspace_id=uuid4())
            self.data = data

        async def resolve(
            self, workspace_id: UUID, project_id: UUID, asset_id: UUID
        ) -> SourceSnapshot:
            del workspace_id, project_id, asset_id
            return self.snapshot

        async def read(self, source: SourceSnapshot) -> bytes:
            del source
            return self.data

    class ExplodingExtractor:
        async def extract(self, source: SourceSnapshot, data: bytes) -> str:
            del source, data
            raise RuntimeError("fixture-private")

    class ExplodingChunker:
        async def chunk(self, text: str) -> tuple[str, ...]:
            del text
            raise RuntimeError("fixture-private")

    class ExplodingEmbedder:
        @property
        def embedder_id(self) -> str:
            return "fixture-exploding@1"

        @property
        def dimensions(self) -> int:
            return 8

        async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
            del texts
            raise RuntimeError("fixture-private")

    class EmptyEmbedder(ExplodingEmbedder):
        async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
            del texts
            return ()

    class ExplodingIndex:
        async def replace(
            self,
            workspace_id: UUID,
            project_id: UUID,
            document_version_id: UUID,
            embeddings: tuple[EmbeddingRef, ...],
        ) -> None:
            del workspace_id, project_id, document_version_id, embeddings
            raise RuntimeError("fixture-private")

        async def search(
            self,
            workspace_id: UUID,
            project_id: UUID,
            query_vector: tuple[float, ...],
            *,
            allowed_version_ids: tuple[UUID, ...],
            top_k: int,
        ) -> tuple[VectorMatch, ...]:
            del workspace_id, project_id, query_vector, allowed_version_ids, top_k
            return ()

    class ExplodingVerifier:
        async def verify(self, source: SourceSnapshot, normalized_text: str) -> VerificationStatus:
            del source, normalized_text
            raise RuntimeError("fixture-private")

    async def scenario() -> None:
        _context, _project, snapshot, data = _fixture()
        mismatch_service, _repository, _sources, _index, _graph, context, project = _services(
            source_reader=MismatchedSource(snapshot, data)
        )
        with pytest.raises(ScopeViolationError):
            await mismatch_service.submit(
                context,
                project.id,
                snapshot.asset_id,
                idempotency_key="fixture-mismatched-source",
            )

        service, repository, sources, _index, _graph, context, project = _services()
        run = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-defensive"
        )
        with pytest.raises(ScopeViolationError):
            await service.get(replace(context, project_id=uuid4()), run.id)
        ready = await service.process(context, run.id)
        assert (await service.process(context, run.id)) == ready
        empty_matches = await DefaultRetriever(
            cast("KnowledgeRepository", repository), FakeEmbedder(), InMemoryVectorIndex()
        ).retrieve(context.workspace_id, project.id, RetrievalRequest("fixture"))
        assert empty_matches.hits == ()

        service._projects = cast("ProjectRepository", Projects())  # noqa: SLF001
        with pytest.raises(ScopeViolationError):
            await service.retrieve(context, project.id, RetrievalRequest("fixture"))

        (
            verified_service,
            _repo,
            verified_sources,
            _idx,
            _graph,
            verified_context,
            verified_project,
        ) = _services(verifier=FixedVerificationProvider(VerificationStatus.VERIFIED))
        verified_run = await verified_service.submit(
            verified_context,
            verified_project.id,
            verified_sources.current.asset_id,
            idempotency_key="fixture-verified",
            verification_policy=VerificationPolicy.REQUIRED,
        )
        verified = await verified_service.process(verified_context, verified_run.id)
        assert verified.verification_status is VerificationStatus.VERIFIED

        (
            missing_text_service,
            missing_repository,
            missing_sources,
            _missing_index,
            _missing_graph,
            missing_context,
            missing_project,
        ) = _services()
        missing_run = await missing_text_service.submit(
            missing_context,
            missing_project.id,
            missing_sources.current.asset_id,
            idempotency_key="fixture-missing-normalized-text",
        )
        missing_bundle = missing_repository.bundles[missing_run.id]
        missing_repository.bundles[missing_run.id] = replace(
            missing_bundle,
            run=replace(missing_bundle.run, status=IngestionStatus.NORMALIZED),
            version=replace(
                missing_bundle.version,
                status=IngestionStatus.NORMALIZED,
                normalized_text=None,
            ),
        )
        missing_failed = await missing_text_service.process(missing_context, missing_run.id)
        assert missing_failed.error_code is KnowledgeErrorCode.NORMALIZATION_FAILED

        empty_service, _repo, empty_sources, _idx, _graph, empty_context, empty_project = _services(
            embedder=EmptyEmbedder()
        )
        empty_run = await empty_service.submit(
            empty_context,
            empty_project.id,
            empty_sources.current.asset_id,
            idempotency_key="fixture-empty-embedding-result",
        )
        empty_failed = await empty_service.process(empty_context, empty_run.id)
        assert empty_failed.error_code is KnowledgeErrorCode.EMBEDDING_FAILED

        cases: tuple[
            tuple[
                dict[str, object],
                VerificationPolicy,
                KnowledgeErrorCode,
                IngestionStatus,
                bool,
            ],
            ...,
        ] = (
            (
                {"extractor": ExplodingExtractor()},
                VerificationPolicy.NOT_REQUIRED,
                KnowledgeErrorCode.EXTRACTION_FAILED,
                IngestionStatus.EXTRACTING,
                False,
            ),
            (
                {"chunker": ExplodingChunker()},
                VerificationPolicy.NOT_REQUIRED,
                KnowledgeErrorCode.CHUNKING_FAILED,
                IngestionStatus.NORMALIZED,
                False,
            ),
            (
                {"embedder": ExplodingEmbedder()},
                VerificationPolicy.NOT_REQUIRED,
                KnowledgeErrorCode.EMBEDDING_FAILED,
                IngestionStatus.CHUNKED,
                True,
            ),
            (
                {"index": ExplodingIndex()},
                VerificationPolicy.NOT_REQUIRED,
                KnowledgeErrorCode.INDEX_UNAVAILABLE,
                IngestionStatus.EMBEDDED,
                True,
            ),
            (
                {"verifier": ExplodingVerifier()},
                VerificationPolicy.REQUIRED,
                KnowledgeErrorCode.VERIFICATION_UNVERIFIED,
                IngestionStatus.VERIFYING,
                False,
            ),
        )
        for position, (overrides, policy, code, stage, retryable) in enumerate(cases):
            (
                failing_service,
                _repo,
                failing_sources,
                _idx,
                _graph,
                failing_context,
                failing_project,
            ) = _services(**overrides)  # type: ignore[arg-type]
            failing_run = await failing_service.submit(
                failing_context,
                failing_project.id,
                failing_sources.current.asset_id,
                idempotency_key=f"fixture-unexpected-{position}",
                verification_policy=policy,
            )
            failed = await failing_service.process(failing_context, failing_run.id)
            assert failed.error_code is code
            assert failed.failed_stage is stage
            assert failed.retryable is retryable
            assert await failing_service.process(failing_context, failing_run.id) == failed

    asyncio.run(scenario())


def test_asset_source_reader_and_contract_validation() -> None:
    class Assets:
        def __init__(self, pair: tuple[Asset, AssetVersion] | None) -> None:
            self.pair = pair

        async def get(
            self, workspace_id: UUID, project_id: UUID, asset_id: UUID
        ) -> tuple[Asset, AssetVersion] | None:
            del workspace_id, project_id, asset_id
            return self.pair

    async def scenario() -> None:
        context, project, snapshot, data = _fixture()
        asset = Asset(
            snapshot.asset_id,
            snapshot.workspace_id,
            snapshot.project_id,
            context.actor_id,
            "fixture.txt",
            "fixture",
            AssetStatus.ACTIVE,
            1,
            NOW,
            NOW,
        )
        version = AssetVersion(
            snapshot.asset_version_id,
            snapshot.workspace_id,
            snapshot.project_id,
            snapshot.asset_id,
            1,
            snapshot.object_key,
            snapshot.content_hash,
            "text/plain",
            len(data),
            ScanStatus.NOT_CONFIGURED,
            ProcessingStatus.AVAILABLE,
            context.actor_id,
            NOW,
        )
        storage = InMemoryObjectStorage()
        await storage.put(
            snapshot.object_key,
            data,
            media_type="text/plain",
            content_hash=snapshot.content_hash,
        )
        reader = AssetSourceReader(cast("AssetRepository", Assets((asset, version))), storage)
        resolved = await reader.resolve(context.workspace_id, project.id, asset.id)
        assert await reader.read(resolved) == data
        for pair in (
            None,
            (replace(asset, status=AssetStatus.PENDING_DELETION), version),
            (asset, replace(version, processing_status=ProcessingStatus.MISSING_OBJECT)),
        ):
            unavailable = AssetSourceReader(cast("AssetRepository", Assets(pair)), storage)
            with pytest.raises(KnowledgePipelineError):
                await unavailable.resolve(context.workspace_id, project.id, asset.id)
        storage.simulate_corruption(snapshot.object_key, b"corrupt")
        with pytest.raises(KnowledgePipelineError) as corrupt:
            await reader.read(resolved)
        assert corrupt.value.code is KnowledgeErrorCode.SOURCE_INTEGRITY_FAILED
        storage.simulate_missing(snapshot.object_key)
        with pytest.raises(KnowledgePipelineError) as missing:
            await reader.read(resolved)
        assert missing.value.retryable

        with pytest.raises(ValueError, match="failed ingestion"):
            IngestionRun(
                uuid4(),
                context.workspace_id,
                project.id,
                uuid4(),
                uuid4(),
                uuid4(),
                IngestionStatus.FAILED,
                VerificationPolicy.NOT_REQUIRED,
                VerificationStatus.NOT_CONFIGURED,
                "fixture-invalid-run",
                context.actor_id,
                uuid4(),
                1,
                NOW,
                NOW,
            )
        with pytest.raises(ValueError, match="positive"):
            replace(
                next(iter((await _reserve_fixture_run()).bundles.values())).run,
                attempt=0,
            )
        with pytest.raises(ValueError, match="only failed"):
            replace(
                next(iter((await _reserve_fixture_run()).bundles.values())).run,
                retryable=True,
            )
        for request in (
            lambda: RetrievalRequest(""),
            lambda: RetrievalRequest("fixture", top_k=0),
            lambda: ResearchRequest("fixture", "fixture"),
        ):
            with pytest.raises(ValueError):
                request()

    asyncio.run(scenario())


def test_workflow_executor_routes_resumes_and_rejects_invalid_references() -> None:
    async def scenario() -> None:
        service, _repository, sources, _index, _graph, context, project = _services()
        run = await service.submit(
            context, project.id, sources.current.asset_id, idempotency_key="fixture-workflow"
        )
        fallback = FallbackExecutor()
        executor = KnowledgeWorkflowExecutor(cast("StepExecutor", fallback), service)
        ordinary = _execution(context, "fixture-step", "fixture-token://input")
        assert (await executor.execute(ordinary)).output_reference == "workflow-output://fallback"
        await executor.compensate(ordinary, "fixture-hook")
        assert fallback.compensations == ["fixture-hook"]
        with pytest.raises(PermanentStepError, match="invalid-run-reference"):
            await executor.execute(_execution(None, "knowledge-ingest", "fixture-token://input"))
        with pytest.raises(PermanentStepError, match="invalid-run-reference"):
            await executor.execute(_execution(context, "knowledge-ingest", "knowledge-run://bad"))
        result = await executor.execute(
            _execution(context, "knowledge-ingest", f"knowledge-run://{run.id}")
        )
        assert result.output_reference.endswith(str(run.document_version_id))
        assert knowledge_ingestion_definition().steps[0].key == "knowledge-ingest"

        pdf_service, _repo, pdf_sources, _idx, _graph, pdf_context, pdf_project = _services()
        pdf_sources.current = replace(pdf_sources.current, media_type="application/pdf")
        pdf_run = await pdf_service.submit(
            pdf_context,
            pdf_project.id,
            pdf_sources.current.asset_id,
            idempotency_key="fixture-workflow-pdf",
        )
        pdf_executor = KnowledgeWorkflowExecutor(cast("StepExecutor", fallback), pdf_service)
        with pytest.raises(PermanentStepError, match="extractor_not_configured"):
            await pdf_executor.execute(
                _execution(
                    pdf_context,
                    "knowledge-ingest",
                    f"knowledge-run://{pdf_run.id}",
                )
            )
        with pytest.raises(PermanentStepError, match="extractor_not_configured"):
            await pdf_executor.execute(
                _execution(
                    pdf_context,
                    "knowledge-ingest",
                    f"knowledge-run://{pdf_run.id}",
                )
            )

        retry_embedder = FakeEmbedder(failures_remaining=1)
        retry_service, _repo, retry_sources, _idx, _graph, retry_context, retry_project = _services(
            embedder=retry_embedder
        )
        retry_run = await retry_service.submit(
            retry_context,
            retry_project.id,
            retry_sources.current.asset_id,
            idempotency_key="fixture-workflow-retry",
        )
        assert (await retry_service.process(retry_context, retry_run.id)).retryable
        retry_executor = KnowledgeWorkflowExecutor(cast("StepExecutor", fallback), retry_service)
        retry_result = await retry_executor.execute(
            _execution(
                retry_context,
                "knowledge-ingest",
                f"knowledge-run://{retry_run.id}",
            )
        )
        assert retry_result.output_reference.endswith(str(retry_run.document_version_id))

        unavailable_index = InMemoryVectorIndex(available=False)
        (
            unavailable_service,
            _repo,
            unavailable_sources,
            _idx,
            _graph,
            unavailable_context,
            unavailable_project,
        ) = _services(index=unavailable_index)
        unavailable_run = await unavailable_service.submit(
            unavailable_context,
            unavailable_project.id,
            unavailable_sources.current.asset_id,
            idempotency_key="fixture-workflow-index-retry",
        )
        assert (
            await unavailable_service.process(unavailable_context, unavailable_run.id)
        ).retryable
        unavailable_executor = KnowledgeWorkflowExecutor(
            cast("StepExecutor", fallback), unavailable_service
        )
        with pytest.raises(RetryableStepError, match="index_unavailable"):
            await unavailable_executor.execute(
                _execution(
                    unavailable_context,
                    "knowledge-ingest",
                    f"knowledge-run://{unavailable_run.id}",
                )
            )

        corrupt_service = MagicMock()
        corrupt_service.get = AsyncMock(
            return_value=SimpleNamespace(status=IngestionStatus.FAILED, retryable=False)
        )
        corrupt_service.process = AsyncMock(
            return_value=SimpleNamespace(
                status=IngestionStatus.FAILED,
                retryable=False,
                error_code=None,
            )
        )
        corrupt_executor = KnowledgeWorkflowExecutor(
            cast("StepExecutor", fallback), cast("KnowledgeService", corrupt_service)
        )
        with pytest.raises(PermanentStepError, match="invalid-failure-state"):
            await corrupt_executor.execute(
                _execution(context, "knowledge-ingest", f"knowledge-run://{run.id}")
            )

    asyncio.run(scenario())


async def _reserve_fixture_run() -> Repository:
    context, _project, snapshot, _data = _fixture()
    repository = Repository()
    await repository.reserve(
        snapshot,
        verification_policy=VerificationPolicy.NOT_REQUIRED,
        idempotency_key="fixture-reserved",
        requested_by=context.actor_id,
        correlation_id=UUID(context.correlation.request_id),
        now=NOW,
    )
    return repository


def _source(snapshot: SourceSnapshot, source_id: UUID, now: datetime) -> KnowledgeSource:
    return KnowledgeSource(
        source_id,
        snapshot.workspace_id,
        snapshot.project_id,
        snapshot.asset_id,
        snapshot.asset_version_id,
        snapshot.version_number,
        snapshot.content_hash,
        snapshot.media_type,
        snapshot.object_key,
        now,
    )


def _document(snapshot: SourceSnapshot, document_id: UUID, now: datetime) -> Document:
    return Document(
        document_id,
        snapshot.workspace_id,
        snapshot.project_id,
        snapshot.asset_id,
        now,
    )


def _version(
    snapshot: SourceSnapshot,
    document_id: UUID,
    source_id: UUID,
    version_id: UUID,
    now: datetime,
) -> DocumentVersion:
    return DocumentVersion(
        version_id,
        snapshot.workspace_id,
        snapshot.project_id,
        document_id,
        source_id,
        snapshot.version_number,
        snapshot.content_hash,
        None,
        IngestionStatus.UPLOADED,
        VerificationStatus.NOT_CONFIGURED,
        False,
        now,
        now,
    )


def _citation(bundle: IngestionBundle, chunk: Chunk) -> Citation:
    return Citation(
        uuid5(chunk.id, "citation"),
        bundle.run.workspace_id,
        bundle.run.project_id,
        bundle.source.id,
        bundle.document.id,
        bundle.version.id,
        bundle.source.asset_id,
        bundle.source.asset_version_id,
        chunk.id,
        f"asset-version://{bundle.source.asset_version_id}#chunk={chunk.ordinal}",
        bundle.version.verification_status,
    )


def _execution(context: SecurityContext | None, step_key: str, reference: str) -> StepExecution:
    return StepExecution(
        uuid4(),
        uuid4(),
        step_key,
        StepKind.REFERENCE,
        1,
        "fixture-task-key",
        reference,
        0,
        0,
        context,
    )
