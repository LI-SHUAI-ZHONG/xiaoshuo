"""Authorized, resumable knowledge ingestion, retrieval, and offline research."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.knowledge.domain import (
    Chunk,
    Document,
    EmbeddingRef,
    IngestionBundle,
    IngestionRun,
    IngestionStatus,
    KnowledgeEdge,
    KnowledgeErrorCode,
    KnowledgePipelineError,
    RelationKind,
    ResearchReport,
    ResearchRequest,
    ResearchStatus,
    RetrievalHit,
    RetrievalRequest,
    RetrievalResult,
    VerificationPolicy,
    VerificationStatus,
)
from accos.modules.knowledge.ports import SourceSnapshot
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.knowledge.ports import (
        Chunker,
        Embedder,
        Extractor,
        GraphProjection,
        KnowledgeRepository,
        Normalizer,
        Retriever,
        SourceReader,
        VectorIndex,
        VerificationProvider,
    )
    from accos.modules.projects.public import ProjectRepository


class DefaultRetriever:
    """Embed a query, search a scoped projection, and enrich hits with citations."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        embedder: Embedder,
        index: VectorIndex,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._index = index

    async def retrieve(
        self,
        workspace_id: UUID,
        project_id: UUID,
        request: RetrievalRequest,
    ) -> RetrievalResult:
        """Return an empty structure when no ready version or match exists."""
        allowed = await self._repository.ready_version_ids(
            workspace_id, project_id, request.filters
        )
        if not allowed:
            return RetrievalResult(request.query, ())
        vectors = await self._embedder.embed((request.query,))
        matches = await self._index.search(
            workspace_id,
            project_id,
            vectors[0],
            allowed_version_ids=allowed,
            top_k=request.top_k,
        )
        if not matches:
            return RetrievalResult(request.query, ())
        pairs = await self._repository.chunks_and_citations(
            workspace_id,
            project_id,
            tuple(item.chunk_id for item in matches),
        )
        by_chunk = {chunk.id: (chunk, citation) for chunk, citation in pairs}
        hits = tuple(
            RetrievalHit(match.score, *by_chunk[match.chunk_id])
            for match in matches
            if match.chunk_id in by_chunk
        )
        return RetrievalResult(request.query, hits)


class KnowledgeService:
    """Own the ingestion state machine and its scoped public operations."""

    def __init__(  # noqa: PLR0913
        self,
        repository: KnowledgeRepository,
        *,
        source_reader: SourceReader,
        extractor: Extractor,
        normalizer: Normalizer,
        chunker: Chunker,
        embedder: Embedder,
        index: VectorIndex,
        verifier: VerificationProvider,
        graph: GraphProjection,
        retriever: Retriever,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._source_reader = source_reader
        self._extractor = extractor
        self._normalizer = normalizer
        self._chunker = chunker
        self._embedder = embedder
        self._index = index
        self._verifier = verifier
        self._graph = graph
        self._retriever = retriever
        self._projects = projects
        self._authorizer = authorizer
        self._clock = clock

    async def submit(
        self,
        context: SecurityContext,
        project_id: UUID,
        asset_id: UUID,
        *,
        idempotency_key: str,
        verification_policy: VerificationPolicy = VerificationPolicy.NOT_REQUIRED,
    ) -> IngestionRun:
        """Reserve exactly one effective ingestion for the current asset version."""
        await self._authorize_project(context, project_id, Permission.PROJECT_WRITE)
        snapshot = await self._source_reader.resolve(context.workspace_id, project_id, asset_id)
        if snapshot.workspace_id != context.workspace_id or snapshot.project_id != project_id:
            raise ScopeViolationError
        run, _created = await self._repository.reserve(
            snapshot,
            verification_policy=verification_policy,
            idempotency_key=idempotency_key,
            requested_by=context.actor_id,
            correlation_id=UUID(context.correlation.request_id),
            now=self._clock.now(),
        )
        return run

    async def get(self, context: SecurityContext, run_id: UUID) -> IngestionRun:
        """Load one run without revealing whether another workspace owns its id."""
        bundle = await self._require_bundle(context, run_id)
        await self._authorize_project(context, bundle.run.project_id, Permission.PROJECT_READ)
        return bundle.run

    async def get_document(
        self, context: SecurityContext, project_id: UUID, document_id: UUID
    ) -> Document:
        """Load one document through its trusted project scope."""
        await self._authorize_project(context, project_id, Permission.PROJECT_READ)
        document = await self._repository.get_document(
            context.workspace_id, project_id, document_id
        )
        if document is None:
            raise ScopeViolationError
        return document

    async def process(self, context: SecurityContext, run_id: UUID) -> IngestionRun:
        """Resume from the last durable checkpoint and settle failures safely."""
        bundle = await self._require_bundle(context, run_id)
        await self._authorize_project(context, bundle.run.project_id, Permission.PROJECT_READ)
        if bundle.run.status in {IngestionStatus.READY, IngestionStatus.FAILED}:
            return bundle.run
        while True:
            bundle = await self._require_bundle(context, run_id)
            stage = bundle.run.status
            try:
                if stage is IngestionStatus.UPLOADED:
                    await self._repository.set_status(
                        context.workspace_id,
                        run_id,
                        IngestionStatus.EXTRACTING.value,
                        now=self._clock.now(),
                    )
                elif stage is IngestionStatus.EXTRACTING:
                    await self._extract_and_normalize(context.workspace_id, bundle)
                elif stage is IngestionStatus.NORMALIZED:
                    await self._chunk(context.workspace_id, bundle)
                elif stage is IngestionStatus.CHUNKED:
                    await self._embed(context.workspace_id, bundle)
                elif stage is IngestionStatus.EMBEDDED:
                    await self._index_embeddings(context.workspace_id, bundle)
                elif stage is IngestionStatus.INDEXED:
                    await self._repository.set_status(
                        context.workspace_id,
                        run_id,
                        IngestionStatus.VERIFYING.value,
                        now=self._clock.now(),
                    )
                else:
                    # READY/FAILED returned above, so VERIFYING is the only
                    # remaining member of the closed IngestionStatus enum.
                    return await self._verify(context.workspace_id, bundle)
            except KnowledgePipelineError as error:
                return await self._repository.fail(
                    context.workspace_id,
                    run_id,
                    failed_stage=error.stage.value,
                    error_code=error.code.value,
                    retryable=error.retryable,
                    now=self._clock.now(),
                )
            except Exception:  # noqa: BLE001 - provider details must not cross the boundary.
                failure = _unexpected_failure(stage)
                return await self._repository.fail(
                    context.workspace_id,
                    run_id,
                    failed_stage=failure.stage.value,
                    error_code=failure.code.value,
                    retryable=failure.retryable,
                    now=self._clock.now(),
                )

    async def retry(self, context: SecurityContext, run_id: UUID) -> IngestionRun:
        """Explicitly restart a failed stage without duplicating projections."""
        bundle = await self._require_bundle(context, run_id)
        await self._authorize_project(context, bundle.run.project_id, Permission.PROJECT_WRITE)
        if bundle.run.status is not IngestionStatus.FAILED:
            raise InvalidStateError("Only failed ingestion can be retried.")
        await self._repository.restart(
            context.workspace_id, run_id, rebuild=False, now=self._clock.now()
        )
        return await self.process(context, run_id)

    async def rebuild(self, context: SecurityContext, run_id: UUID) -> IngestionRun:
        """Recreate projections from the preserved source locator and metadata."""
        bundle = await self._require_bundle(context, run_id)
        await self._authorize_project(context, bundle.run.project_id, Permission.PROJECT_WRITE)
        await self._repository.restart(
            context.workspace_id, run_id, rebuild=True, now=self._clock.now()
        )
        return await self.process(context, run_id)

    async def retrieve(
        self,
        context: SecurityContext,
        project_id: UUID,
        request: RetrievalRequest,
    ) -> RetrievalResult:
        """Search only the trusted workspace/project scope."""
        await self._authorize_project(context, project_id, Permission.PROJECT_READ)
        return await self._retriever.retrieve(context.workspace_id, project_id, request)

    async def _extract_and_normalize(self, workspace_id: UUID, bundle: IngestionBundle) -> None:
        snapshot = _snapshot(bundle)
        data = await self._source_reader.read(snapshot)
        text = await self._extractor.extract(snapshot, data)
        normalized = await self._normalizer.normalize(text)
        await self._repository.save_normalized(
            workspace_id,
            bundle.run.id,
            normalized,
            now=self._clock.now(),
        )

    async def _chunk(self, workspace_id: UUID, bundle: IngestionBundle) -> None:
        text = bundle.version.normalized_text
        if text is None:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.NORMALIZATION_FAILED,
                IngestionStatus.NORMALIZED,
                retryable=False,
            )
        values = await self._chunker.chunk(text)
        chunks = tuple(
            Chunk(
                uuid5(bundle.version.id, f"chunk:{index}:{_digest(value)}"),
                bundle.run.workspace_id,
                bundle.run.project_id,
                bundle.source.id,
                bundle.version.id,
                index,
                value,
                _digest(value),
            )
            for index, value in enumerate(values)
        )
        await self._repository.replace_chunks(
            workspace_id,
            bundle.run.id,
            chunks,
            now=self._clock.now(),
        )
        await self._graph.replace(
            workspace_id,
            bundle.run.project_id,
            bundle.version.id,
            _edges(bundle, chunks),
        )

    async def _embed(self, workspace_id: UUID, bundle: IngestionBundle) -> None:
        vectors = await self._embedder.embed(tuple(chunk.content for chunk in bundle.chunks))
        if len(vectors) != len(bundle.chunks):
            raise KnowledgePipelineError(
                KnowledgeErrorCode.EMBEDDING_FAILED,
                IngestionStatus.CHUNKED,
                retryable=True,
            )
        embeddings = tuple(
            EmbeddingRef(
                uuid5(chunk.id, f"embedding:{self._embedder.embedder_id}"),
                bundle.run.workspace_id,
                bundle.run.project_id,
                chunk.id,
                bundle.version.id,
                self._embedder.embedder_id,
                self._embedder.dimensions,
                vector,
                chunk.content_hash,
            )
            for chunk, vector in zip(bundle.chunks, vectors, strict=True)
        )
        await self._repository.replace_embeddings(
            workspace_id,
            bundle.run.id,
            embeddings,
            now=self._clock.now(),
        )

    async def _index_embeddings(self, workspace_id: UUID, bundle: IngestionBundle) -> None:
        await self._index.replace(
            workspace_id,
            bundle.run.project_id,
            bundle.version.id,
            bundle.embeddings,
        )
        await self._repository.set_status(
            workspace_id,
            bundle.run.id,
            IngestionStatus.INDEXED.value,
            now=self._clock.now(),
        )

    async def _verify(self, workspace_id: UUID, bundle: IngestionBundle) -> IngestionRun:
        text = bundle.version.normalized_text or ""
        if bundle.run.verification_policy is VerificationPolicy.NOT_REQUIRED:
            verification = VerificationStatus.NOT_CONFIGURED
        else:
            verification = await self._verifier.verify(_snapshot(bundle), text)
            if verification is not VerificationStatus.VERIFIED:
                code = {
                    VerificationStatus.NOT_CONFIGURED: (
                        KnowledgeErrorCode.VERIFICATION_NOT_CONFIGURED
                    ),
                    VerificationStatus.UNVERIFIED: KnowledgeErrorCode.VERIFICATION_UNVERIFIED,
                    VerificationStatus.REJECTED: KnowledgeErrorCode.VERIFICATION_REJECTED,
                }[verification]
                raise KnowledgePipelineError(code, IngestionStatus.VERIFYING, retryable=False)
        return await self._repository.complete(
            workspace_id,
            bundle.run.id,
            verification,
            now=self._clock.now(),
        )

    async def _require_bundle(self, context: SecurityContext, run_id: UUID) -> IngestionBundle:
        bundle = await self._repository.load(context.workspace_id, run_id)
        if bundle is None:
            raise ScopeViolationError
        if context.project_id is not None and context.project_id != bundle.run.project_id:
            raise ScopeViolationError
        return bundle

    async def _authorize_project(
        self,
        context: SecurityContext,
        project_id: UUID,
        permission: Permission,
    ) -> None:
        project = await self._projects.get(context.workspace_id, project_id)
        request = AuthorizationRequest(
            context,
            permission,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        if project is None:
            await self._authorizer.reject(
                request,
                ScopeViolationError(),
                reason_code="project_unavailable",
            )
        if project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot use knowledge ingestion.")
        await self._authorizer.authorize(request)


class ResearchService:
    """Offline question-to-report skeleton that never requests external material."""

    def __init__(self, knowledge: KnowledgeService) -> None:
        self._knowledge = knowledge

    async def execute(
        self,
        context: SecurityContext,
        project_id: UUID,
        request: ResearchRequest,
    ) -> ResearchReport:
        """Return technical state and persisted citations only."""
        result = await self._knowledge.retrieve(
            context,
            project_id,
            RetrievalRequest(request.query, request.top_k),
        )
        token = _digest(f"{request.question_reference}:{request.query}")[:24]
        citations = tuple(hit.citation for hit in result.hits)
        verification = (
            VerificationStatus.UNVERIFIED
            if not citations
            else (
                VerificationStatus.VERIFIED
                if all(
                    citation.verification_status is VerificationStatus.VERIFIED
                    for citation in citations
                )
                else VerificationStatus.NOT_CONFIGURED
            )
        )
        return ResearchReport(
            ResearchStatus.COMPLETED if citations else ResearchStatus.NO_RESULTS,
            request.question_reference,
            f"research-plan://{token}",
            f"research-material-request://offline/{token}",
            verification,
            f"research-report://{token}",
            citations,
        )


def _snapshot(bundle: IngestionBundle) -> SourceSnapshot:
    return SourceSnapshot(
        bundle.source.workspace_id,
        bundle.source.project_id,
        bundle.source.asset_id,
        bundle.source.asset_version_id,
        bundle.source.asset_version_number,
        bundle.source.content_locator,
        bundle.source.content_hash,
        bundle.source.media_type,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _edges(bundle: IngestionBundle, chunks: tuple[Chunk, ...]) -> tuple[KnowledgeEdge, ...]:
    edges = [
        KnowledgeEdge(
            uuid5(bundle.version.id, "edge:source"),
            bundle.run.workspace_id,
            bundle.run.project_id,
            bundle.version.id,
            "source",
            bundle.source.id,
            RelationKind.SOURCE_OF,
            "document_version",
            bundle.version.id,
        ),
        KnowledgeEdge(
            uuid5(bundle.version.id, "edge:derived"),
            bundle.run.workspace_id,
            bundle.run.project_id,
            bundle.version.id,
            "document_version",
            bundle.version.id,
            RelationKind.DERIVED_FROM,
            "asset_version",
            bundle.source.asset_version_id,
        ),
    ]
    for chunk in chunks:
        edges.extend(
            (
                KnowledgeEdge(
                    uuid5(chunk.id, "edge:contains"),
                    bundle.run.workspace_id,
                    bundle.run.project_id,
                    bundle.version.id,
                    "document_version",
                    bundle.version.id,
                    RelationKind.CONTAINS,
                    "chunk",
                    chunk.id,
                ),
                KnowledgeEdge(
                    uuid5(chunk.id, "edge:cites"),
                    bundle.run.workspace_id,
                    bundle.run.project_id,
                    bundle.version.id,
                    "chunk",
                    chunk.id,
                    RelationKind.CITES,
                    "source",
                    bundle.source.id,
                ),
            )
        )
    return tuple(edges)


def _unexpected_failure(stage: IngestionStatus) -> KnowledgePipelineError:
    if stage in {IngestionStatus.UPLOADED, IngestionStatus.EXTRACTING}:
        return KnowledgePipelineError(
            KnowledgeErrorCode.EXTRACTION_FAILED,
            IngestionStatus.EXTRACTING,
            retryable=False,
        )
    if stage is IngestionStatus.NORMALIZED:
        code, retryable = KnowledgeErrorCode.CHUNKING_FAILED, False
    elif stage is IngestionStatus.CHUNKED:
        code, retryable = KnowledgeErrorCode.EMBEDDING_FAILED, True
    elif stage is IngestionStatus.EMBEDDED:
        code, retryable = KnowledgeErrorCode.INDEX_UNAVAILABLE, True
    else:
        code, retryable = KnowledgeErrorCode.VERIFICATION_UNVERIFIED, False
    return KnowledgePipelineError(code, stage, retryable=retryable)
