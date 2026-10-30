from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from accos.adapters.creative import InMemoryCreativeRepository
from accos.adapters.creative.persistence import _CONTAINER_TYPES, _RECORD_TYPES
from accos.kernel.errors import (
    ConcurrencyConflictError,
    InvalidStateError,
    ScopeViolationError,
)
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.creative.character import CHARACTER_RECORD_TYPES
from accos.modules.creative.creator import CREATOR_RECORD_TYPES
from accos.modules.creative.novel import NOVEL_RECORD_TYPES
from accos.modules.creative.public import (
    BehaviorProposal,
    Chapter,
    CharacterService,
    CharacterState,
    ConceptRef,
    CreateCharacterCommand,
    CreateCreatorProfileCommand,
    CreateWorkCommand,
    CreateWorldCommand,
    CreativeAccess,
    CreativeApplication,
    CreativeCatalog,
    CreativeDecision,
    CreativeOwner,
    CreativeRecordStatus,
    CreativeReference,
    CreativeReferenceKind,
    CreativeWorkflowExecutor,
    CreatorProfile,
    CreatorService,
    DecideCharacterRecordCommand,
    DecideCreatorRecordCommand,
    DecideNovelRecordCommand,
    DecideWorldRecordCommand,
    ExtensionRequest,
    ExtensionStatus,
    GetCharacterQuery,
    GetCharacterRecordQuery,
    GetCreatorProfileQuery,
    GetCreatorRecordQuery,
    GetNovelRecordQuery,
    GetWorkQuery,
    GetWorldQuery,
    GetWorldRecordQuery,
    ImpactLink,
    NovelService,
    NullPreferenceSignalIngestPort,
    PreferenceSignal,
    ProposeCharacterImpactCommand,
    ProposeCharacterRecordCommand,
    ProposeCreatorRecordCommand,
    ProposeNovelRecordCommand,
    ProposeWorldImpactCommand,
    ProposeWorldRecordCommand,
    StyleProfile,
    Work,
    WorldService,
    WorldState,
    creative_reference_definition,
    null_creative_extensions,
)
from accos.modules.creative.world import WORLD_RECORD_TYPES
from accos.modules.identity.public import AuthorizationService, Role, permissions_for
from accos.modules.projects.public import (
    Project,
    ProjectRepository,
    ProjectSettings,
    ProjectStatus,
)
from accos.modules.workflows.public import (
    PermanentStepError,
    StepExecution,
    StepExecutionResult,
    StepKind,
)

if TYPE_CHECKING:
    from typing import Any

    from accos.modules.identity.ports import AuditEvent
    from accos.modules.workflows.public import StepExecutor

NOW = datetime(2026, 9, 6, 8, tzinfo=UTC)
ACTOR_ID = UUID("30000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("30000000-0000-4000-8000-000000000002")
PROJECT_ID = UUID("30000000-0000-4000-8000-000000000003")
OTHER_PROJECT_ID = UUID("30000000-0000-4000-8000-000000000004")


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


def context(*, project_id: UUID | None = None) -> SecurityContext:
    correlation = uuid4()
    return SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        WORKSPACE_ID,
        permissions_for(Role.OWNER),
        "fixture-policy-v1",
        CorrelationIds(str(correlation), str(correlation)),
        project_id,
    )


def services() -> tuple[
    NovelService,
    WorldService,
    CharacterService,
    CreatorService,
    CreativeCatalog,
    InMemoryCreativeRepository,
    Projects,
]:
    repository = InMemoryCreativeRepository()
    projects = Projects()
    access = CreativeAccess(
        cast("ProjectRepository", projects), AuthorizationService(Audit(), Clock())
    )
    application = CreativeApplication(repository, access, Clock())
    return (
        NovelService(application),
        WorldService(application),
        CharacterService(application),
        CreatorService(application, NullPreferenceSignalIngestPort()),
        CreativeCatalog(application),
        repository,
        projects,
    )


def record() -> BehaviorProposal:
    return BehaviorProposal(
        uuid4(),
        uuid4(),
        1,
        WORKSPACE_ID,
        PROJECT_ID,
        uuid4(),
        CreativeRecordStatus.PROPOSAL,
        False,
        (),
        "fixture-source://record",
        0,
        ACTOR_ID,
        NOW,
    )


def execution(
    security: SecurityContext | None, step_key: str, input_reference: str
) -> StepExecution:
    return StepExecution(
        uuid4(),
        uuid4(),
        step_key,
        StepKind.REFERENCE,
        1,
        "fixture-creative-step",
        input_reference,
        0,
        0,
        security,
    )


def test_content_free_domain_invariants_and_unique_owner_map() -> None:
    world_ref = CreativeReference(CreativeReferenceKind.WORLD, uuid4())
    work = Work(
        uuid4(),
        WORKSPACE_ID,
        PROJECT_ID,
        "fixture-work",
        (world_ref,),
        ACTOR_ID,
        NOW,
        NOW,
    )
    assert work.reference == f"creative://novel/{work.id}"
    assert record().reference.startswith("creative-record://character/")
    invalid_containers: tuple[dict[str, object], ...] = (
        {"label": ""},
        {"label": " fixture"},
        {"label": "x" * 201},
        {"references": (world_ref, world_ref)},
        {"version": 0},
        {"created_at": datetime(2026, 9, 6)},
        {"updated_at": datetime(2026, 9, 6)},
        {"updated_at": NOW - timedelta(seconds=1)},
        {"references": (CreativeReference(CreativeReferenceKind.MEMORY, uuid4()),)},
    )
    for update in invalid_containers:
        with pytest.raises(ValueError):
            replace(cast("Any", work), **update)

    creator = CreatorProfile(
        uuid4(),
        WORKSPACE_ID,
        PROJECT_ID,
        "fixture-creator",
        (CreativeReference(CreativeReferenceKind.CREATOR, ACTOR_ID),),
        ACTOR_ID,
        NOW,
        NOW,
    )
    assert creator.creator_id == ACTOR_ID
    with pytest.raises(ValueError):
        replace(creator, references=())
    with pytest.raises(ValueError):
        replace(creator, references=(world_ref,))

    proposal = record()
    invalid_records: tuple[dict[str, object], ...] = (
        {"record_version": 0},
        {"current": True},
        {"references": (world_ref, world_ref)},
        {"source_reference": "not-a-reference"},
        {"sequence": -1},
        {"causation_id": uuid4()},
        {"source_event_id": uuid4()},
        {"created_at": datetime(2026, 9, 6)},
        {"decided_at": datetime(2026, 9, 6), "decided_by": ACTOR_ID},
        {"decided_by": ACTOR_ID},
        {"decided_at": NOW},
    )
    for update in invalid_records:
        with pytest.raises(ValueError):
            replace(cast("Any", proposal), **update)

    owners = {item.owner for item in _CONTAINER_TYPES.values()}
    assert owners == set(CreativeOwner)
    assert len(_RECORD_TYPES) == 24
    assert all(key == (value.owner, value.entity_type) for key, value in _RECORD_TYPES.items())
    assert set(NOVEL_RECORD_TYPES).isdisjoint(WORLD_RECORD_TYPES)
    assert set(WORLD_RECORD_TYPES).isdisjoint(CHARACTER_RECORD_TYPES)
    assert set(CHARACTER_RECORD_TYPES).isdisjoint(CREATOR_RECORD_TYPES)
    root = Path(__file__).resolve().parents[3]
    assert not (root / "backend" / "world_engine").exists()
    assert not (root / "services" / "world").exists()


def test_four_services_approval_concurrency_scope_and_archive() -> None:  # noqa: PLR0915
    async def scenario() -> None:  # noqa: PLR0915
        novel, world, character, creator, catalog, repository, projects = services()
        ctx = context()
        world_container = await world.create(ctx, CreateWorldCommand(PROJECT_ID, "fixture-world"))
        character_container = await character.create(
            ctx,
            CreateCharacterCommand(
                PROJECT_ID,
                "fixture-character",
                (CreativeReference(CreativeReferenceKind.WORLD, world_container.id),),
            ),
        )
        work = await novel.create(
            ctx,
            CreateWorkCommand(
                PROJECT_ID,
                "fixture-work",
                (world_container.id,),
                (character_container.id,),
            ),
        )
        profile = await creator.create(
            ctx, CreateCreatorProfileCommand(PROJECT_ID, "fixture-creator")
        )
        assert (await novel.get(ctx, GetWorkQuery(PROJECT_ID, work.id))) == work
        assert (
            await world.get(ctx, GetWorldQuery(PROJECT_ID, world_container.id))
        ) == world_container
        assert (
            await character.get(ctx, GetCharacterQuery(PROJECT_ID, character_container.id))
        ) == character_container
        assert (await creator.get(ctx, GetCreatorProfileQuery(PROJECT_ID, profile.id))) == profile
        assert (await catalog.resolve(ctx, PROJECT_ID, CreativeOwner.NOVEL, work.id)) == work

        novel_record, _ = await novel.propose(
            ctx,
            ProposeNovelRecordCommand(
                PROJECT_ID,
                work.id,
                Chapter,
                source_reference="fixture-source://chapter",
                sequence=0,
            ),
        )
        world_record, _ = await world.propose(
            ctx,
            ProposeWorldRecordCommand(PROJECT_ID, world_container.id, WorldState),
        )
        character_record, _ = await character.propose(
            ctx,
            ProposeCharacterRecordCommand(PROJECT_ID, character_container.id, CharacterState),
        )
        creator_record, _ = await creator.propose(
            ctx,
            ProposeCreatorRecordCommand(PROJECT_ID, profile.id, StyleProfile),
        )
        assert not any(
            item.current for item in (novel_record, world_record, character_record, creator_record)
        )
        assert (
            await novel.get_record(ctx, GetNovelRecordQuery(PROJECT_ID, novel_record.id))
            == novel_record
        )
        assert (
            await world.get_record(ctx, GetWorldRecordQuery(PROJECT_ID, world_record.id))
            == world_record
        )
        assert (
            await character.get_record(
                ctx, GetCharacterRecordQuery(PROJECT_ID, character_record.id)
            )
            == character_record
        )
        assert (
            await creator.get_record(ctx, GetCreatorRecordQuery(PROJECT_ID, creator_record.id))
            == creator_record
        )

        approved = await world.decide(
            ctx,
            DecideWorldRecordCommand(PROJECT_ID, world_record.id, CreativeDecision.APPROVE, 1),
        )
        assert approved.current and approved.status is CreativeRecordStatus.CURRENT
        revision, _ = await world.propose(
            ctx,
            ProposeWorldRecordCommand(
                PROJECT_ID,
                world_container.id,
                WorldState,
                logical_id=approved.logical_id,
                record_version=2,
            ),
        )
        with pytest.raises(ConcurrencyConflictError):
            await world.decide(
                ctx,
                DecideWorldRecordCommand(PROJECT_ID, revision.id, CreativeDecision.APPROVE, 1),
            )
        replacement = await world.decide(
            ctx,
            DecideWorldRecordCommand(PROJECT_ID, revision.id, CreativeDecision.APPROVE, 2),
        )
        assert replacement.current
        assert repository.records[approved.id].status is CreativeRecordStatus.SUPERSEDED
        with pytest.raises(InvalidStateError):
            await world.decide(
                ctx,
                DecideWorldRecordCommand(PROJECT_ID, revision.id, CreativeDecision.REJECT, 3),
            )

        rejected = await novel.decide(
            ctx,
            DecideNovelRecordCommand(PROJECT_ID, novel_record.id, CreativeDecision.REJECT, 1),
        )
        assert rejected.status is CreativeRecordStatus.REJECTED and not rejected.current
        await character.decide(
            ctx,
            DecideCharacterRecordCommand(
                PROJECT_ID, character_record.id, CreativeDecision.APPROVE, 1
            ),
        )
        await creator.decide(
            ctx,
            DecideCreatorRecordCommand(PROJECT_ID, creator_record.id, CreativeDecision.APPROVE, 1),
        )

        with pytest.raises(ValueError, match="Novel"):
            await novel.propose(ctx, ProposeNovelRecordCommand(PROJECT_ID, work.id, WorldState))
        with pytest.raises(ValueError, match="World"):
            await world.propose(
                ctx,
                ProposeWorldRecordCommand(PROJECT_ID, world_container.id, CharacterState),
            )
        with pytest.raises(ValueError, match="Character"):
            await character.propose(
                ctx,
                ProposeCharacterRecordCommand(PROJECT_ID, character_container.id, ConceptRef),
            )
        with pytest.raises(ValueError, match="Creator"):
            await creator.propose(
                ctx,
                ProposeCreatorRecordCommand(PROJECT_ID, profile.id, PreferenceSignal),
            )

        scoped = context(project_id=PROJECT_ID)
        with pytest.raises(ScopeViolationError):
            await novel.get(scoped, GetWorkQuery(OTHER_PROJECT_ID, work.id))
        with pytest.raises(ScopeViolationError):
            await novel.get(ctx, GetWorkQuery(PROJECT_ID, uuid4()))
        with pytest.raises(ScopeViolationError):
            await novel.get_record(ctx, GetNovelRecordQuery(PROJECT_ID, uuid4()))
        with pytest.raises(ScopeViolationError):
            await novel.decide(
                ctx,
                DecideNovelRecordCommand(PROJECT_ID, uuid4(), CreativeDecision.APPROVE, 1),
            )
        with pytest.raises(ScopeViolationError):
            await novel.propose(ctx, ProposeNovelRecordCommand(PROJECT_ID, uuid4(), Chapter))

        projects.items[(WORKSPACE_ID, PROJECT_ID)] = replace(
            projects.items[(WORKSPACE_ID, PROJECT_ID)], status=ProjectStatus.ARCHIVED
        )
        assert (await novel.get(ctx, GetWorkQuery(PROJECT_ID, work.id))).id == work.id
        with pytest.raises(InvalidStateError):
            await novel.create(ctx, CreateWorkCommand(PROJECT_ID, "fixture-archived"))
        projects.items.pop((WORKSPACE_ID, OTHER_PROJECT_ID))
        with pytest.raises(ScopeViolationError):
            await world.create(ctx, CreateWorldCommand(OTHER_PROJECT_ID, "fixture-missing"))

        first_event = repository.events[0]
        assert (
            await repository.add_container(world_container, first_event)
        ).id == world_container.id
        duplicate, created = await repository.add_proposal(novel_record, first_event)
        assert duplicate.id == novel_record.id and not created
        assert (
            await repository.get_container(WORKSPACE_ID, PROJECT_ID, CreativeOwner.WORLD, uuid4())
            is None
        )
        assert (
            await repository.get_record(WORKSPACE_ID, PROJECT_ID, CreativeOwner.WORLD, uuid4())
            is None
        )
        orphan = record()
        repository.records[orphan.id] = orphan
        with pytest.raises(ScopeViolationError):
            await repository.decide_proposal(
                WORKSPACE_ID,
                PROJECT_ID,
                CreativeOwner.CHARACTER,
                orphan.id,
                decision=CreativeDecision.APPROVE,
                expected_container_version=1,
                decided_by=ACTOR_ID,
                decided_at=NOW,
                event=first_event,
            )
        with pytest.raises(ScopeViolationError):
            await repository.decide_proposal(
                WORKSPACE_ID,
                PROJECT_ID,
                CreativeOwner.CHARACTER,
                uuid4(),
                decision=CreativeDecision.APPROVE,
                expected_container_version=1,
                decided_by=ACTOR_ID,
                decided_at=NOW,
                event=first_event,
            )

    asyncio.run(scenario())


def test_causation_dedup_null_extensions_creator_signal_and_workflow() -> None:
    async def scenario() -> None:
        novel, world, character, creator, catalog, repository, _projects = services()
        ctx = context(project_id=PROJECT_ID)
        world_container = await world.create(ctx, CreateWorldCommand(PROJECT_ID, "fixture-world"))
        character_container = await character.create(
            ctx, CreateCharacterCommand(PROJECT_ID, "fixture-character")
        )
        profile = await creator.create(
            ctx, CreateCreatorProfileCommand(PROJECT_ID, "fixture-creator")
        )
        causation_id, source_event_id = uuid4(), uuid4()
        impact, created = await world.propose_character_action_impact(
            ctx,
            ProposeWorldImpactCommand(
                PROJECT_ID, world_container.id, causation_id, source_event_id
            ),
        )
        replay, replay_created = await world.propose_character_action_impact(
            ctx,
            ProposeWorldImpactCommand(
                PROJECT_ID, world_container.id, causation_id, source_event_id
            ),
        )
        character_impact, character_created = await character.propose_world_event_impact(
            ctx,
            ProposeCharacterImpactCommand(
                PROJECT_ID, character_container.id, causation_id, source_event_id
            ),
        )
        character_replay, character_replay_created = await character.propose_world_event_impact(
            ctx,
            ProposeCharacterImpactCommand(
                PROJECT_ID, character_container.id, causation_id, source_event_id
            ),
        )
        assert isinstance(impact, ImpactLink) and created
        assert replay == impact and not replay_created
        assert isinstance(character_impact, BehaviorProposal) and character_created
        assert character_replay == character_impact and not character_replay_created
        assert (
            len(
                [
                    item
                    for item in repository.events
                    if item.payload.get("causation_id") == str(causation_id)
                ]
            )
            == 2
        )

        request = ExtensionRequest(WORKSPACE_ID, PROJECT_ID, ("fixture-input://one",))
        extensions = null_creative_extensions()
        for port in (
            extensions.concept,
            extensions.theme,
            extensions.plot,
            extensions.emotion,
            extensions.style,
            extensions.chapter_generator,
            extensions.world_simulation,
            extensions.character_behavior,
            extensions.creator_learning,
            extensions.political,
            extensions.economic,
            extensions.technology,
            extensions.culture,
        ):
            result = await port.invoke(request)
            assert result.status is ExtensionStatus.NOT_CONFIGURED
            assert result.proposal_reference is None

        signal = PreferenceSignal(
            uuid4(),
            uuid4(),
            1,
            WORKSPACE_ID,
            PROJECT_ID,
            profile.id,
            CreativeRecordStatus.PROPOSAL,
            False,
            (CreativeReference(CreativeReferenceKind.CREATOR, ACTOR_ID),),
            "fixture-signal://explicit",
            None,
            ACTOR_ID,
            NOW,
        )
        assert (
            await creator.ingest_signal(ctx, PROJECT_ID, signal)
        ).status is ExtensionStatus.NOT_CONFIGURED
        with pytest.raises(ValueError, match="self-authorized"):
            await creator.ingest_signal(ctx, PROJECT_ID, replace(signal, project_id=uuid4()))

        fallback = Fallback()
        executor = CreativeWorkflowExecutor(cast("StepExecutor", fallback), catalog)
        ordinary = execution(ctx, "fixture-step", "fixture-input://one")
        assert (await executor.execute(ordinary)).output_reference == "fixture-output://fallback"
        await executor.compensate(ordinary, "fixture-hook")
        assert fallback.compensations == ["fixture-hook"]
        for invalid_context, reference in (
            (None, world_container.reference),
            (context(), world_container.reference),
            (ctx, "fixture://bad"),
            (ctx, f"creative://invalid/{world_container.id}"),
            (ctx, "creative://world/not-a-uuid"),
        ):
            with pytest.raises(PermanentStepError):
                await executor.execute(execution(invalid_context, "creative-reference", reference))
        workflow_result = await executor.execute(
            execution(ctx, "creative-reference", world_container.reference)
        )
        assert workflow_result.output_reference == f"creative-result://world/{world_container.id}"
        definition = creative_reference_definition()
        assert definition.name == "creative_reference"
        assert definition.steps[0].key == "creative-reference"
        assert await novel.create(ctx, CreateWorkCommand(PROJECT_ID, "fixture-work"))

    asyncio.run(scenario())


class Fallback:
    def __init__(self) -> None:
        self.compensations: list[str] = []

    async def execute(self, execution: StepExecution) -> StepExecutionResult:
        del execution
        return StepExecutionResult("fixture-output://fallback")

    async def compensate(self, execution: StepExecution, hook: str) -> None:
        del execution
        self.compensations.append(hook)
