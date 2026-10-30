from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from accos.adapters.memory import (
    InMemoryMemoryProjection,
    InMemoryMemoryRepository,
    RedisMemoryProjection,
)
from accos.adapters.memory.persistence import _locked_record
from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.identity.public import AuthorizationService, Role, permissions_for
from accos.modules.memory.public import (
    CREATOR_SCOPES,
    PROJECT_SCOPES,
    ContextBuilder,
    ContextPackage,
    ContextRequest,
    DefaultRetentionPolicy,
    DeterministicMemoryCompressor,
    DeterministicMemoryRanker,
    MemoryAccessPolicy,
    MemoryAnchorKind,
    MemoryConflictStatus,
    MemoryDraft,
    MemoryGrant,
    MemoryLink,
    MemoryProjectionRebuilder,
    MemoryProvenance,
    MemoryRecord,
    MemoryScope,
    MemoryService,
    MemoryStatus,
    OmissionReason,
    ProposalConflictResolver,
    RetentionKind,
    RetentionRule,
)
from accos.modules.projects.public import Project, ProjectSettings, ProjectStatus

if TYPE_CHECKING:
    from accos.modules.identity.ports import AuditEvent
    from accos.modules.projects.public import ProjectRepository

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
ACTOR_ID = UUID("20000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("20000000-0000-4000-8000-000000000002")
PROJECT_ID = UUID("20000000-0000-4000-8000-000000000003")
OTHER_PROJECT_ID = UUID("20000000-0000-4000-8000-000000000004")
UNIVERSE_ID = UUID("20000000-0000-4000-8000-000000000005")
OTHER_CREATOR_ID = UUID("20000000-0000-4000-8000-000000000006")


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
    def __init__(self) -> None:
        self.items = {
            (WORKSPACE_ID, project_id): Project(
                project_id,
                WORKSPACE_ID,
                "fixture-project",
                ProjectStatus.ACTIVE,
                ProjectSettings(),
                ACTOR_ID,
                NOW,
                NOW,
            )
            for project_id in (PROJECT_ID, OTHER_PROJECT_ID)
        }

    async def get(self, workspace_id: UUID, project_id: UUID) -> Project | None:
        return self.items.get((workspace_id, project_id))


def context(*, workspace_id: UUID = WORKSPACE_ID) -> SecurityContext:
    correlation_id = uuid4()
    return SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        workspace_id,
        permissions_for(Role.OWNER),
        "fixture-policy-v1",
        CorrelationIds(str(correlation_id), str(correlation_id)),
    )


def draft(  # noqa: PLR0913 - fixture exposes the record matrix explicitly.
    scope: MemoryScope = MemoryScope.PROJECT,
    *,
    content: str = "fixture-memory",
    memory_type: str = "system",
    project_id: UUID | None = PROJECT_ID,
    universe_id: UUID | None = None,
    creator_id: UUID | None = None,
    retention: RetentionRule | None = None,
    valid_from: datetime = NOW - timedelta(hours=1),
    valid_until: datetime | None = None,
    observed_at: datetime = NOW - timedelta(hours=1),
    importance: float = 0.8,
    confidence: float = 1,
) -> MemoryDraft:
    return MemoryDraft(
        scope,
        memory_type,
        content,
        valid_from,
        observed_at,
        importance,
        confidence,
        MemoryProvenance("human", f"fixture-source://{scope.value}"),
        retention or RetentionRule(),
        project_id,
        universe_id,
        creator_id,
        valid_until,
    )


def services() -> tuple[
    MemoryService,
    ContextBuilder,
    InMemoryMemoryRepository,
    InMemoryMemoryProjection,
    Audit,
]:
    repository = InMemoryMemoryRepository()
    projection = InMemoryMemoryProjection()
    projects = cast("ProjectRepository", Projects())
    audit = Audit()
    authorizer = AuthorizationService(audit, Clock())
    retention = DefaultRetentionPolicy()
    service = MemoryService(
        repository,
        projects,
        authorizer,
        DeterministicMemoryCompressor(),
        ProposalConflictResolver(),
        Clock(),
    )
    builder = ContextBuilder(
        repository,
        projects,
        authorizer,
        MemoryAccessPolicy(repository),
        DeterministicMemoryRanker(retention),
        Clock(),
    )
    return service, builder, repository, projection, audit


def test_scope_type_anchor_and_value_contracts() -> None:
    base = MemoryRecord(
        uuid4(),
        uuid4(),
        1,
        WORKSPACE_ID,
        MemoryScope.PROJECT,
        "system",
        "fixture-memory",
        PROJECT_ID,
        None,
        None,
        NOW,
        None,
        NOW,
        1,
        1,
        MemoryProvenance("human", "fixture-source://record"),
        RetentionRule(),
        MemoryStatus.ACTIVE,
        True,
        ACTOR_ID,
        NOW,
    )
    assert base.anchor_id == PROJECT_ID
    assert PROJECT_SCOPES.isdisjoint(CREATOR_SCOPES)
    universe = replace(
        base,
        id=uuid4(),
        logical_id=uuid4(),
        scope=MemoryScope.UNIVERSE,
        project_id=None,
        universe_id=UNIVERSE_ID,
    )
    creator = replace(
        base,
        id=uuid4(),
        logical_id=uuid4(),
        scope=MemoryScope.WISDOM,
        project_id=None,
        creator_id=ACTOR_ID,
    )
    assert universe.anchor_id == UNIVERSE_ID and creator.anchor_id == ACTOR_ID

    invalid_updates = (
        {"project_id": None},
        {"memory_type": "Bad Type"},
        {"version": 0},
        {"content": " fixture"},
        {"importance": 2},
        {"confidence": -1},
        {"valid_until": NOW},
        {"status": MemoryStatus.ARCHIVED},
    )
    for updates in invalid_updates:
        with pytest.raises(ValueError):
            replace(base, **updates)
    with pytest.raises(ValueError):
        MemoryProvenance("Bad", "not-a-reference")
    with pytest.raises(ValueError):
        MemoryLink(uuid4(), WORKSPACE_ID, base.id, base.id, "summary_of", NOW)
    with pytest.raises(ValueError):
        MemoryLink(uuid4(), WORKSPACE_ID, base.id, universe.id, "Bad Relation", NOW)
    with pytest.raises(ValueError):
        RetentionRule(RetentionKind.TTL)
    with pytest.raises(ValueError):
        RetentionRule(RetentionKind.DECAY)
    with pytest.raises(ValueError):
        RetentionRule(RetentionKind.KEEP, ttl_seconds=1)
    with pytest.raises(ValueError):
        RetentionRule(RetentionKind.KEEP, decay_half_life_seconds=1)
    with pytest.raises(ValueError):
        ContextRequest("fixture-task://x", PROJECT_ID, 0, frozenset(), frozenset())
    with pytest.raises(ValueError, match="token budget"):
        ContextRequest(
            "fixture-task://x",
            PROJECT_ID,
            1,
            frozenset({MemoryScope.PROJECT}),
            frozenset({"system"}),
            0,
        )
    with pytest.raises(ValueError):
        ContextPackage(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            "invalid",
            1,
            0,
            (),
            (),
            (),
            "0" * 64,
            ACTOR_ID,
            NOW,
        )
    with pytest.raises(ValueError, match="positive character budget"):
        ContextPackage(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            "fixture-task://invalid-budget",
            1,
            2,
            (),
            (),
            (),
            "0" * 64,
            ACTOR_ID,
            NOW,
        )
    with pytest.raises(ValueError, match="token budget"):
        ContextPackage(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            "fixture-task://invalid-token-budget",
            1,
            0,
            (),
            (),
            (),
            "0" * 64,
            ACTOR_ID,
            NOW,
            0,
            0,
        )


def test_authorization_first_context_isolation_grants_ranking_and_budget() -> None:  # noqa: PLR0915
    async def scenario() -> None:
        service, builder, repository, _projection, _audit = services()
        ctx = context()
        current = await service.write(ctx, draft(content="AAAA", importance=0.9))
        decayed = await service.write(
            ctx,
            draft(
                content="BB",
                importance=0.9,
                observed_at=NOW - timedelta(hours=2),
                retention=RetentionRule(RetentionKind.DECAY, decay_half_life_seconds=3600),
            ),
        )
        expired_ttl = await service.write(
            ctx,
            draft(
                MemoryScope.WORKING,
                content="ttl",
                retention=RetentionRule(RetentionKind.TTL, ttl_seconds=1),
            ),
        )
        future = await service.write(
            ctx,
            draft(MemoryScope.SESSION, content="future", valid_from=NOW + timedelta(hours=1)),
        )
        elapsed = await service.write(
            ctx,
            draft(
                MemoryScope.SESSION,
                content="elapsed",
                valid_until=NOW - timedelta(minutes=1),
                valid_from=NOW - timedelta(hours=2),
            ),
        )
        retained_archive = await service.write(
            ctx,
            draft(
                MemoryScope.SESSION,
                content="archive",
                retention=RetentionRule(RetentionKind.ARCHIVE),
            ),
        )
        other_project = await service.write(
            ctx, draft(content="cross-project", project_id=OTHER_PROJECT_ID)
        )
        universe = await service.write(
            ctx,
            draft(
                MemoryScope.UNIVERSE,
                content="universe",
                project_id=None,
                universe_id=UNIVERSE_ID,
            ),
        )
        other_creator = await service.write(
            ctx,
            draft(
                MemoryScope.CREATOR,
                content="creator",
                project_id=None,
                creator_id=OTHER_CREATOR_ID,
            ),
        )
        self_wisdom = await service.write(
            ctx,
            draft(
                MemoryScope.WISDOM,
                content="self",
                project_id=None,
                creator_id=ACTOR_ID,
            ),
        )
        scopes = frozenset(MemoryScope)
        request = ContextRequest(
            "fixture-task://context", PROJECT_ID, 6, scopes, frozenset({"system"})
        )
        package = await builder.build(ctx, request)
        assert await service.get(ctx, current.id) == current
        assert await builder.get(ctx, PROJECT_ID, package.id) == package
        with pytest.raises(ScopeViolationError):
            await builder.get(ctx, PROJECT_ID, uuid4())
        assert package.used_chars == 6
        assert package.reference == f"memory-context://{package.id}"
        assert [item.record_id for item in package.items] == [current.id, decayed.id]
        omitted = {(item.record_id, item.reason) for item in package.omissions}
        assert (expired_ttl.id, OmissionReason.TTL_EXPIRED) in omitted
        assert (future.id, OmissionReason.NOT_YET_VALID) in omitted
        assert (elapsed.id, OmissionReason.NO_LONGER_VALID) in omitted
        assert (retained_archive.id, OmissionReason.RETENTION_ARCHIVED) in omitted
        assert (self_wisdom.id, OmissionReason.BUDGET_EXCEEDED) in omitted
        assert any(
            item.scope is MemoryScope.UNIVERSE
            and item.reason is OmissionReason.ANCHOR_UNAVAILABLE
            and item.record_id is None
            for item in package.omissions
        )
        assert other_project.id not in {item.record_id for item in package.items}
        assert universe.id not in {item.record_id for item in package.items}
        assert other_creator.id not in {item.record_id for item in package.items}
        archived_evaluation = DefaultRetentionPolicy().evaluate(
            replace(current, status=MemoryStatus.ARCHIVED, current=False), NOW
        )
        assert archived_evaluation.reason is OmissionReason.ARCHIVED
        assert await repository.get_package(WORKSPACE_ID, PROJECT_ID, package.id) == package
        assert await repository.get_package(uuid4(), PROJECT_ID, package.id) is None

        await service.grant(ctx, PROJECT_ID, MemoryAnchorKind.UNIVERSE, UNIVERSE_ID)
        await service.grant(ctx, PROJECT_ID, MemoryAnchorKind.CREATOR, OTHER_CREATOR_ID)
        granted = await builder.build(
            ctx,
            ContextRequest(
                "fixture-task://granted", PROJECT_ID, 100, scopes, frozenset({"system"})
            ),
        )
        selected = {item.record_id for item in granted.items}
        assert universe.id in selected and other_creator.id in selected
        assert other_project.id not in selected
        assert {item.scope for item in granted.allowed_anchors}.issuperset(
            {MemoryScope.UNIVERSE, MemoryScope.CREATOR, MemoryScope.EXPERIENCE, MemoryScope.WISDOM}
        )

        only_project = await builder.build(
            ctx,
            ContextRequest(
                "fixture-task://filter",
                PROJECT_ID,
                100,
                frozenset({MemoryScope.PROJECT}),
                frozenset({"system"}),
            ),
        )
        assert {item.scope for item in only_project.items} == {MemoryScope.PROJECT}
        token_limited = await builder.build(
            ctx,
            ContextRequest(
                "fixture-task://token-budget",
                PROJECT_ID,
                100,
                frozenset({MemoryScope.PROJECT}),
                frozenset({"system"}),
                1,
            ),
        )
        assert token_limited.used_tokens == 1
        assert len(token_limited.items) == 1
        assert any(
            item.reason is OmissionReason.BUDGET_EXCEEDED for item in token_limited.omissions
        )
        assert await repository.retrieve((), scopes, frozenset()) == ()

    asyncio.run(scenario())


def test_conflicts_compression_soft_forget_and_repository_boundaries() -> None:
    async def scenario() -> None:
        service, _builder, repository, _projection, _audit = services()
        ctx = context()
        current = await service.write(ctx, draft(content="fixture-current"))
        conflict = await service.propose_revision(ctx, current.id, "fixture-candidate")
        assert await service.get_conflict(ctx, conflict.id) == conflict
        with pytest.raises(ScopeViolationError):
            await service.get_conflict(ctx, uuid4())
        candidate = repository.records[conflict.candidate_record_id]
        assert conflict.candidate_resolutions == ("keep_current", "accept_candidate")
        assert repository.records[current.id].current and not candidate.current
        decided = await service.decide_conflict(ctx, conflict.id, accept_candidate=True)
        assert decided.status is MemoryConflictStatus.ACCEPTED
        assert repository.records[conflict.candidate_record_id].current
        assert repository.records[current.id].status is MemoryStatus.SUPERSEDED
        with pytest.raises(InvalidStateError):
            await service.decide_conflict(ctx, conflict.id, accept_candidate=True)

        second = await service.write(ctx, draft(content="fixture-second"))
        rejected = await service.propose_revision(ctx, second.id, "fixture-rejected")
        await service.decide_conflict(ctx, rejected.id, accept_candidate=False)
        assert repository.records[rejected.candidate_record_id].status is MemoryStatus.ARCHIVED
        with pytest.raises(ScopeViolationError):
            await service.decide_conflict(ctx, uuid4(), accept_candidate=False)

        summary = await service.compress(
            ctx,
            (repository.records[conflict.candidate_record_id].id, second.id),
            draft(content="fixture-placeholder", memory_type="decision"),
            budget_chars=20,
        )
        assert summary.content == "fixture-candidate\nfi"
        assert {link.to_record_id for link in repository.links.values()} == {
            conflict.candidate_record_id,
            second.id,
        }
        universe = await service.write(
            ctx,
            draft(
                MemoryScope.UNIVERSE,
                content="fixture-universe-source",
                project_id=None,
                universe_id=UNIVERSE_ID,
            ),
        )
        await service.compress(
            ctx,
            (universe.id,),
            draft(content="fixture-placeholder", memory_type="decision"),
            budget_chars=10,
        )
        archived = await service.forget(ctx, summary.id)
        assert archived.status is MemoryStatus.ARCHIVED and not archived.current
        assert await service.forget(ctx, summary.id) == archived

        assert await repository.get_record(uuid4(), current.id) is None
        with pytest.raises(ScopeViolationError):
            await repository.archive(uuid4(), current.id, actor_id=ACTOR_ID, archived_at=NOW)
        with pytest.raises(ScopeViolationError):
            await repository.decide_conflict(
                uuid4(), rejected.id, accepted=True, decided_by=ACTOR_ID, decided_at=NOW
            )
        with pytest.raises(ValueError):
            DeterministicMemoryCompressor().compress((), 1)
        with pytest.raises(ValueError):
            ProposalConflictResolver().candidate_resolutions(
                current, replace(current, id=uuid4(), logical_id=uuid4(), version=2)
            )

    asyncio.run(scenario())


def test_disposable_projection_clear_and_rebuild_preserves_facts() -> None:
    async def scenario() -> None:
        service, _builder, repository, projection, _audit = services()
        ctx = context()
        working = await service.write(ctx, draft(MemoryScope.WORKING, content="fixture-working"))
        session = await service.write(ctx, draft(MemoryScope.SESSION, content="fixture-session"))
        await service.write(ctx, draft(MemoryScope.PROJECT, content="fixture-project"))
        rebuilder = MemoryProjectionRebuilder(repository, projection)
        first = await rebuilder.rebuild(WORKSPACE_ID, PROJECT_ID)
        assert {item.id for item in first} == {working.id, session.id}
        await projection.clear(WORKSPACE_ID, PROJECT_ID)
        assert await projection.load(WORKSPACE_ID, PROJECT_ID) == ()
        rebuilt = await rebuilder.rebuild(WORKSPACE_ID, PROJECT_ID)
        assert rebuilt == first
        assert await projection.load(WORKSPACE_ID, PROJECT_ID) == tuple(item.id for item in first)
        assert await repository.get_record(WORKSPACE_ID, working.id) == working

    asyncio.run(scenario())


def test_redis_projection_contains_only_ids_and_closes_every_client() -> None:
    async def scenario() -> None:
        service, _builder, _repository, _projection, _audit = services()
        record = await service.write(context(), draft(MemoryScope.WORKING))
        client = MagicMock()
        client.set = AsyncMock()
        client.get = AsyncMock(side_effect=[None, f'["{record.id}"]'])
        client.delete = AsyncMock()
        client.aclose = AsyncMock()
        projection = RedisMemoryProjection("redis://fixture", ttl_seconds=60)
        with patch(
            "accos.adapters.memory.projection.Redis.from_url", return_value=client
        ) as factory:
            await projection.replace(WORKSPACE_ID, PROJECT_ID, (record,))
            assert await projection.load(WORKSPACE_ID, PROJECT_ID) == ()
            assert await projection.load(WORKSPACE_ID, PROJECT_ID) == (record.id,)
            await projection.clear(WORKSPACE_ID, PROJECT_ID)
        assert factory.call_count == 4
        assert client.aclose.await_count == 4
        client.set.assert_awaited_once()
        client.delete.assert_awaited_once()
        with pytest.raises(ValueError, match="TTL"):
            RedisMemoryProjection("redis://fixture", ttl_seconds=0)

    asyncio.run(scenario())


def test_missing_project_and_cross_workspace_fail_closed() -> None:
    async def scenario() -> None:
        service, builder, repository, _projection, _audit = services()
        ctx = context()
        with pytest.raises(ScopeViolationError):
            await service.write(ctx, draft(project_id=uuid4()))
        with pytest.raises(ValueError):
            await service.write(ctx, draft(project_id=None))
        with pytest.raises(ScopeViolationError):
            await builder.build(
                ctx,
                ContextRequest(
                    "fixture-task://missing",
                    uuid4(),
                    10,
                    frozenset({MemoryScope.PROJECT}),
                    frozenset({"system"}),
                ),
            )
        record = await service.write(ctx, draft())
        with pytest.raises(ScopeViolationError):
            await service.propose_revision(context(workspace_id=uuid4()), record.id, "fixture")
        revoked = MemoryGrant(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            MemoryAnchorKind.UNIVERSE,
            UNIVERSE_ID,
            ACTOR_ID,
            False,
            NOW,
            NOW,
        )
        await repository.add_grant(revoked)
        assert revoked.active is False
        assert revoked not in await repository.grants_for(WORKSPACE_ID, PROJECT_ID)

        class MissingSession:
            async def scalar(self, _statement: object) -> None:
                return None

        with pytest.raises(InvalidStateError, match="unavailable"):
            await _locked_record(cast("object", MissingSession()), uuid4())  # type: ignore[arg-type]

    asyncio.run(scenario())
