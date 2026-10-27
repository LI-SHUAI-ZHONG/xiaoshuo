"""Authorization-first memory writing, ranking, conflicts, and context assembly."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.kernel.errors import ScopeViolationError
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.memory.domain import (
    CREATOR_SCOPES,
    PROJECT_SCOPES,
    AllowedAnchor,
    CompressionDraft,
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
    RankedMemory,
    RetentionEvaluation,
    RetentionKind,
    RetentionRule,
)

if TYPE_CHECKING:
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.memory.ports import (
        ConflictResolver,
        MemoryCompressor,
        MemoryProjection,
        MemoryRanker,
        MemoryRepository,
        RetentionPolicy,
    )
    from accos.modules.projects.public import ProjectRepository


@dataclass(frozen=True, slots=True)
class MemoryDraft:
    """Trusted use-case input; constructing the record enforces anchor invariants."""

    scope: MemoryScope
    memory_type: str
    content: str
    valid_from: datetime
    observed_at: datetime
    importance: float
    confidence: float
    provenance: MemoryProvenance
    retention: RetentionRule = field(default_factory=RetentionRule)
    project_id: UUID | None = None
    universe_id: UUID | None = None
    creator_id: UUID | None = None
    valid_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class ContextRequest:
    """Project task and the maximum context authority/budget it may request."""

    task_reference: str
    project_id: UUID
    budget_chars: int
    scopes: frozenset[MemoryScope]
    memory_types: frozenset[str]
    budget_tokens: int | None = None

    def __post_init__(self) -> None:
        if not self.scopes or not self.memory_types or self.budget_chars < 1:
            raise ValueError("context request requires scopes, types, and a positive budget")
        if self.budget_tokens is not None and self.budget_tokens < 1:
            raise ValueError("context token budget must be positive")


class DefaultRetentionPolicy:
    """TTL excludes, decay lowers rank, and archive never physically deletes."""

    def evaluate(self, record: MemoryRecord, now: datetime) -> RetentionEvaluation:
        if record.status is not MemoryStatus.ACTIVE:
            return RetentionEvaluation(eligible=False, multiplier=0, reason=OmissionReason.ARCHIVED)
        rule = record.retention
        if rule.kind is RetentionKind.ARCHIVE:
            return RetentionEvaluation(
                eligible=False,
                multiplier=0,
                reason=OmissionReason.RETENTION_ARCHIVED,
            )
        age = max(0.0, (now - record.observed_at).total_seconds())
        if rule.kind is RetentionKind.TTL and age >= (rule.ttl_seconds or 0):
            return RetentionEvaluation(
                eligible=False, multiplier=0, reason=OmissionReason.TTL_EXPIRED
            )
        if rule.kind is RetentionKind.DECAY:
            return RetentionEvaluation(
                eligible=True,
                multiplier=0.5 ** (age / (rule.decay_half_life_seconds or 1)),
            )
        return RetentionEvaluation(eligible=True, multiplier=1)


_SCOPE_PRIORITY = {
    MemoryScope.WORKING: 7,
    MemoryScope.SESSION: 6,
    MemoryScope.PROJECT: 5,
    MemoryScope.UNIVERSE: 4,
    MemoryScope.CREATOR: 3,
    MemoryScope.EXPERIENCE: 2,
    MemoryScope.WISDOM: 1,
}
_PROVENANCE_PRIORITY = {"human": 3, "knowledge_citation": 2, "system": 1}


class DeterministicMemoryRanker:
    """Stable scope/time/importance/provenance ordering without an LLM."""

    def __init__(self, retention: RetentionPolicy) -> None:
        self._retention = retention

    def rank(
        self, records: tuple[MemoryRecord, ...], now: datetime
    ) -> tuple[tuple[RankedMemory, ...], tuple[tuple[MemoryRecord, str], ...]]:
        ranked: list[RankedMemory] = []
        excluded: list[tuple[MemoryRecord, str]] = []
        for record in records:
            if record.valid_from > now:
                excluded.append((record, OmissionReason.NOT_YET_VALID.value))
                continue
            if record.valid_until is not None and record.valid_until <= now:
                excluded.append((record, OmissionReason.NO_LONGER_VALID.value))
                continue
            evaluation = self._retention.evaluate(record, now)
            if not evaluation.eligible:
                reason = evaluation.reason or OmissionReason.ARCHIVED
                excluded.append((record, reason.value))
                continue
            score = record.importance * record.confidence * evaluation.multiplier
            ranked.append(RankedMemory(record, score))
        ranked.sort(
            key=lambda item: (
                -_SCOPE_PRIORITY[item.record.scope],
                -item.score,
                -_PROVENANCE_PRIORITY.get(item.record.provenance.kind, 0),
                -item.record.observed_at.timestamp(),
                str(item.record.id),
            )
        )
        return tuple(ranked), tuple(excluded)


class FakeSemanticMemoryRanker(DeterministicMemoryRanker):
    """Offline semantic-ranker adapter with a deterministic zero semantic contribution."""


class DeterministicMemoryCompressor:
    """Content-neutral deterministic compression placeholder with full lineage."""

    def compress(self, records: tuple[MemoryRecord, ...], budget_chars: int) -> CompressionDraft:
        if not records or budget_chars < 1:
            raise ValueError("compression requires records and a positive budget")
        content = "\n".join(record.content for record in records)[:budget_chars]
        return CompressionDraft(content, tuple(record.id for record in records))


class ProposalConflictResolver:
    """Expose choices; never decide or rewrite memory itself."""

    def candidate_resolutions(
        self, current: MemoryRecord, candidate: MemoryRecord
    ) -> tuple[str, ...]:
        if current.logical_id != candidate.logical_id or candidate.version != current.version + 1:
            raise ValueError("conflict candidate must be the next logical version")
        return ("keep_current", "accept_candidate")


class MemoryAccessPolicy:
    """Compute allowed anchors before any record query is issued."""

    def __init__(
        self, repository: MemoryRepository, authorizer: AuthorizationService | None = None
    ) -> None:
        self._repository = repository
        self._authorizer = authorizer

    async def allowed(
        self,
        context: SecurityContext,
        project_id: UUID,
        scopes: frozenset[MemoryScope],
    ) -> tuple[AllowedAnchor, ...]:
        anchors = {
            AllowedAnchor(context.workspace_id, scope, project_id)
            for scope in scopes.intersection(PROJECT_SCOPES)
        }
        for scope in scopes.intersection(CREATOR_SCOPES):
            anchors.add(AllowedAnchor(context.workspace_id, scope, context.actor_id))
        grants = await self._repository.grants_for(context.workspace_id, project_id)
        for grant in grants:
            if self._authorizer is not None and not await self._authorizer.can_access(
                AuthorizationRequest(
                    context,
                    Permission.PROJECT_READ,
                    ResourceScope(
                        grant.workspace_id, grant.anchor_kind.value, str(grant.anchor_id)
                    ),
                )
            ):
                continue
            if grant.anchor_kind is MemoryAnchorKind.UNIVERSE:
                if MemoryScope.UNIVERSE in scopes:
                    anchors.add(
                        AllowedAnchor(grant.workspace_id, MemoryScope.UNIVERSE, grant.anchor_id)
                    )
            else:
                anchors.update(
                    AllowedAnchor(grant.workspace_id, scope, grant.anchor_id)
                    for scope in scopes.intersection(CREATOR_SCOPES)
                )
        return tuple(sorted(anchors, key=lambda item: (item.scope.value, str(item.anchor_id))))


class MemoryService:
    """Authorized write, grant, conflict, compression, and soft-forget use cases."""

    def __init__(  # noqa: PLR0913,PLR0917 - explicit ports make policy visible.
        self,
        repository: MemoryRepository,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
        compressor: MemoryCompressor,
        conflicts: ConflictResolver,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._projects = projects
        self._authorizer = authorizer
        self._compressor = compressor
        self._conflicts = conflicts
        self._clock = clock

    async def write(self, context: SecurityContext, draft: MemoryDraft) -> MemoryRecord:
        await self._authorize_draft(context, draft, Permission.PROJECT_WRITE)
        now = self._clock.now()
        record = MemoryRecord(
            uuid4(),
            uuid4(),
            1,
            context.workspace_id,
            draft.scope,
            draft.memory_type,
            draft.content,
            draft.project_id,
            draft.universe_id,
            draft.creator_id,
            draft.valid_from,
            draft.valid_until,
            draft.observed_at,
            draft.importance,
            draft.confidence,
            draft.provenance,
            draft.retention,
            MemoryStatus.ACTIVE,
            current=True,
            created_by=context.actor_id,
            created_at=now,
        )
        await self._repository.add(record)
        return record

    async def grant(
        self,
        context: SecurityContext,
        project_id: UUID,
        anchor_kind: MemoryAnchorKind,
        anchor_id: UUID,
        *,
        can_write: bool = False,
    ) -> MemoryGrant:
        await self._authorize_project(context, project_id, Permission.PROJECT_WRITE)
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.MEMBERSHIP_MANAGE,
                ResourceScope(context.workspace_id, "memory_grant", str(anchor_id)),
            )
        )
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.PROJECT_WRITE if can_write else Permission.PROJECT_READ,
                ResourceScope(context.workspace_id, anchor_kind.value, str(anchor_id)),
            )
        )
        grant = MemoryGrant(
            uuid4(),
            context.workspace_id,
            project_id,
            anchor_kind,
            anchor_id,
            context.actor_id,
            can_write,
            self._clock.now(),
        )
        await self._repository.add_grant(grant)
        return grant

    async def propose_revision(
        self, context: SecurityContext, current_id: UUID, content: str
    ) -> MemoryConflict:
        current = await self._require_record(context.workspace_id, current_id)
        await self._authorize_record(context, current, Permission.PROJECT_WRITE)
        candidate = replace(
            current,
            id=uuid4(),
            version=current.version + 1,
            content=content,
            status=MemoryStatus.CANDIDATE,
            current=False,
            created_by=context.actor_id,
            created_at=self._clock.now(),
        )
        conflict = MemoryConflict(
            uuid4(),
            current.workspace_id,
            current.id,
            candidate.id,
            self._conflicts.candidate_resolutions(current, candidate),
            MemoryConflictStatus.PENDING,
            context.actor_id,
            self._clock.now(),
        )
        await self._repository.add_conflict(candidate, conflict)
        return conflict

    async def decide_conflict(
        self, context: SecurityContext, conflict_id: UUID, *, accept_candidate: bool
    ) -> MemoryConflict:
        conflict = await self._repository.get_conflict(context.workspace_id, conflict_id)
        if conflict is None:
            raise ScopeViolationError
        current = await self._require_record(context.workspace_id, conflict.current_record_id)
        await self._authorize_record(context, current, Permission.PROJECT_WRITE)
        return await self._repository.decide_conflict(
            context.workspace_id,
            conflict_id,
            accepted=accept_candidate,
            decided_by=context.actor_id,
            decided_at=self._clock.now(),
        )

    async def compress(
        self,
        context: SecurityContext,
        source_ids: tuple[UUID, ...],
        summary: MemoryDraft,
        *,
        budget_chars: int,
    ) -> MemoryRecord:
        sources = tuple(
            [
                await self._require_record(context.workspace_id, record_id)
                for record_id in source_ids
            ]
        )
        for source in sources:
            await self._authorize_record(context, source, Permission.PROJECT_READ)
        compressed = self._compressor.compress(sources, budget_chars)
        record = await self.write(context, replace(summary, content=compressed.content))
        links = tuple(
            MemoryLink(
                uuid4(), context.workspace_id, record.id, source_id, "summary_of", self._clock.now()
            )
            for source_id in compressed.source_record_ids
        )
        await self._repository.add(record, links)
        return record

    async def forget(self, context: SecurityContext, record_id: UUID) -> MemoryRecord:
        record = await self._require_record(context.workspace_id, record_id)
        await self._authorize_record(context, record, Permission.PROJECT_WRITE)
        return await self._repository.archive(
            context.workspace_id,
            record_id,
            actor_id=context.actor_id,
            archived_at=self._clock.now(),
        )

    async def get(self, context: SecurityContext, record_id: UUID) -> MemoryRecord:
        """Return one memory only after evaluating its authoritative anchor."""
        record = await self._require_record(context.workspace_id, record_id)
        await self._authorize_record(context, record, Permission.PROJECT_READ)
        return record

    async def get_conflict(self, context: SecurityContext, conflict_id: UUID) -> MemoryConflict:
        """Return an inert conflict through the current record's scope."""
        conflict = await self._repository.get_conflict(context.workspace_id, conflict_id)
        if conflict is None:
            raise ScopeViolationError
        current = await self._require_record(context.workspace_id, conflict.current_record_id)
        await self._authorize_record(context, current, Permission.PROJECT_READ)
        return conflict

    async def _require_record(self, workspace_id: UUID, record_id: UUID) -> MemoryRecord:
        record = await self._repository.get_record(workspace_id, record_id)
        if record is None:
            raise ScopeViolationError
        return record

    async def _authorize_draft(
        self, context: SecurityContext, draft: MemoryDraft, permission: Permission
    ) -> None:
        if draft.scope in PROJECT_SCOPES:
            if draft.project_id is None:
                raise ValueError("project memory requires project_id")
            await self._authorize_project(context, draft.project_id, permission)
            return
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                permission,
                ResourceScope(
                    context.workspace_id,
                    "universe" if draft.scope is MemoryScope.UNIVERSE else "creator",
                    str(
                        draft.universe_id
                        if draft.scope is MemoryScope.UNIVERSE
                        else draft.creator_id
                    ),
                ),
            )
        )

    async def _authorize_project(
        self, context: SecurityContext, project_id: UUID, permission: Permission
    ) -> None:
        project = await self._projects.get(context.workspace_id, project_id)
        request = AuthorizationRequest(
            context,
            permission,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        if project is None:
            await self._authorizer.reject(
                request, ScopeViolationError(), reason_code="memory_project_unavailable"
            )
        await self._authorizer.authorize(request)

    async def _authorize_record(
        self, context: SecurityContext, record: MemoryRecord, permission: Permission
    ) -> None:
        if record.scope in PROJECT_SCOPES:
            await self._authorize_project(context, record.anchor_id, permission)
            return
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                permission,
                ResourceScope(
                    record.workspace_id,
                    "universe" if record.scope is MemoryScope.UNIVERSE else "creator",
                    str(record.anchor_id),
                ),
            )
        )


class ContextBuilder:
    """Build and persist an authorization-first immutable package under budget."""

    def __init__(  # noqa: PLR0913,PLR0917 - explicit context boundaries.
        self,
        repository: MemoryRepository,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
        access: MemoryAccessPolicy,
        ranker: MemoryRanker,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._projects = projects
        self._authorizer = authorizer
        self._access = access
        self._ranker = ranker
        self._clock = clock

    async def build(self, context: SecurityContext, request: ContextRequest) -> ContextPackage:
        await self._authorize(context, request.project_id)
        anchors = await self._access.allowed(context, request.project_id, request.scopes)
        records = await self._repository.retrieve(anchors, request.scopes, request.memory_types)
        ranked, excluded = self._ranker.rank(records, self._clock.now())
        omissions = [
            ContextOmission(OmissionReason(reason), item.scope, item.memory_type, item.id)
            for item, reason in excluded
        ]
        anchored_scopes = {anchor.scope for anchor in anchors}
        omissions.extend(
            ContextOmission(OmissionReason.ANCHOR_UNAVAILABLE, scope, None, None)
            for scope in sorted(
                request.scopes.difference(anchored_scopes), key=lambda item: item.value
            )
        )
        items: list[ContextItem] = []
        used = 0
        used_tokens = 0
        for candidate in ranked:
            record = candidate.record
            size = len(record.content)
            tokens = max(1, (size + 3) // 4)
            if used + size > request.budget_chars or (
                request.budget_tokens is not None and used_tokens + tokens > request.budget_tokens
            ):
                omissions.append(
                    ContextOmission(
                        OmissionReason.BUDGET_EXCEEDED,
                        record.scope,
                        record.memory_type,
                        record.id,
                    )
                )
                continue
            items.append(
                ContextItem(
                    record.id,
                    record.scope,
                    record.memory_type,
                    record.content,
                    candidate.score,
                    record.provenance,
                )
            )
            used += size
            used_tokens += tokens
        checksum = hashlib.sha256(
            json.dumps(
                {
                    "anchors": [
                        (str(anchor.workspace_id), anchor.scope.value, str(anchor.anchor_id))
                        for anchor in anchors
                    ],
                    "items": [(str(item.record_id), item.content) for item in items],
                    "task": request.task_reference,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        package = ContextPackage(
            uuid4(),
            context.workspace_id,
            request.project_id,
            request.task_reference,
            request.budget_chars,
            used,
            anchors,
            tuple(items),
            tuple(omissions),
            checksum,
            context.actor_id,
            self._clock.now(),
            request.budget_tokens,
            used_tokens,
        )
        await self._repository.save_package(package)
        return package

    async def get(
        self, context: SecurityContext, project_id: UUID, package_id: UUID
    ) -> ContextPackage:
        """Read a saved immutable package through the same project boundary."""
        await self._authorize(context, project_id)
        package = await self._repository.get_package(context.workspace_id, project_id, package_id)
        if package is None:
            raise ScopeViolationError
        scopes = frozenset(anchor.scope for anchor in package.allowed_anchors)
        allowed = await self._access.allowed(context, project_id, scopes)
        if not set(package.allowed_anchors).issubset(allowed):
            raise ScopeViolationError
        return package

    async def _authorize(self, context: SecurityContext, project_id: UUID) -> None:
        project = await self._projects.get(context.workspace_id, project_id)
        request = AuthorizationRequest(
            context,
            Permission.PROJECT_READ,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        if project is None:
            await self._authorizer.reject(
                request, ScopeViolationError(), reason_code="memory_context_project_unavailable"
            )
        await self._authorizer.authorize(request)


class MemoryProjectionRebuilder:
    """Rebuild disposable Working/Session cache state from PostgreSQL facts."""

    def __init__(self, repository: MemoryRepository, projection: MemoryProjection) -> None:
        self._repository = repository
        self._projection = projection

    async def rebuild(self, workspace_id: UUID, project_id: UUID) -> tuple[MemoryRecord, ...]:
        scopes = frozenset({MemoryScope.WORKING, MemoryScope.SESSION})
        anchors = tuple(AllowedAnchor(workspace_id, scope, project_id) for scope in scopes)
        records = await self._repository.retrieve(anchors, scopes, frozenset())
        await self._projection.replace(workspace_id, project_id, records)
        return records
