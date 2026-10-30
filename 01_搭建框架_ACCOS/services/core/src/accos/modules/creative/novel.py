"""Novel-owned structure models, commands, queries, events, and service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from accos.modules.creative.common import (
    CreativeContainer,
    CreativeDecision,
    CreativeOwner,
    CreativeRecord,
    CreativeReference,
    CreativeReferenceKind,
)

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.security import SecurityContext
    from accos.modules.creative.application import CreativeApplication

WORK_CREATED_SCHEMA = "creative.novel.work-created.v1"
NOVEL_PROPOSED_SCHEMA = "creative.novel.record-proposed.v1"
NOVEL_DECIDED_SCHEMA = "creative.novel.record-decided.v1"


@dataclass(frozen=True, slots=True)
class Work(CreativeContainer):
    """Novel-owned work structure referencing World/Character IDs only."""

    owner = CreativeOwner.NOVEL

    def __post_init__(self) -> None:
        CreativeContainer.__post_init__(self)
        if any(
            item.kind not in {CreativeReferenceKind.WORLD, CreativeReferenceKind.CHARACTER}
            for item in self.references
        ):
            raise ValueError("Work may reference only World and Character IDs")


@dataclass(frozen=True, slots=True)
class ConceptRef(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "concept_ref"


@dataclass(frozen=True, slots=True)
class ThemeRef(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "theme_ref"


@dataclass(frozen=True, slots=True)
class PlotPlan(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "plot_plan"


@dataclass(frozen=True, slots=True)
class Chapter(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "chapter"


@dataclass(frozen=True, slots=True)
class DraftRevision(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "draft_revision"


@dataclass(frozen=True, slots=True)
class EvaluationRequest(CreativeRecord):
    owner = CreativeOwner.NOVEL
    entity_type = "evaluation_request"


NOVEL_RECORD_TYPES: tuple[type[CreativeRecord], ...] = (
    ConceptRef,
    ThemeRef,
    PlotPlan,
    Chapter,
    DraftRevision,
    EvaluationRequest,
)
type NovelRecord = ConceptRef | ThemeRef | PlotPlan | Chapter | DraftRevision | EvaluationRequest


@dataclass(frozen=True, slots=True)
class CreateWorkCommand:
    project_id: UUID
    label: str
    world_ids: tuple[UUID, ...] = ()
    character_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class GetWorkQuery:
    project_id: UUID
    work_id: UUID


@dataclass(frozen=True, slots=True)
class ProposeNovelRecordCommand:
    project_id: UUID
    work_id: UUID
    record_type: type[CreativeRecord]
    logical_id: UUID | None = None
    record_version: int = 1
    references: tuple[CreativeReference, ...] = ()
    source_reference: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class GetNovelRecordQuery:
    project_id: UUID
    record_id: UUID


@dataclass(frozen=True, slots=True)
class DecideNovelRecordCommand:
    project_id: UUID
    record_id: UUID
    decision: CreativeDecision
    expected_work_version: int


class NovelService:
    """Application boundary that cannot address World or Character records."""

    def __init__(self, application: CreativeApplication) -> None:
        self._application = application

    async def create(self, context: SecurityContext, command: CreateWorkCommand) -> Work:
        references = tuple(
            [CreativeReference(CreativeReferenceKind.WORLD, item) for item in command.world_ids]
            + [
                CreativeReference(CreativeReferenceKind.CHARACTER, item)
                for item in command.character_ids
            ]
        )
        return cast(
            "Work",
            await self._application.create_container(
                context,
                command.project_id,
                Work,
                command.label,
                references,
                WORK_CREATED_SCHEMA,
            ),
        )

    async def get(self, context: SecurityContext, query: GetWorkQuery) -> Work:
        return cast(
            "Work",
            await self._application.get_container(
                context, query.project_id, CreativeOwner.NOVEL, query.work_id
            ),
        )

    async def propose(
        self, context: SecurityContext, command: ProposeNovelRecordCommand
    ) -> tuple[NovelRecord, bool]:
        if command.record_type not in NOVEL_RECORD_TYPES:
            raise ValueError("record type is not owned by Novel")
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.work_id,
            command.record_type,
            logical_id=command.logical_id,
            record_version=command.record_version,
            references=command.references,
            source_reference=command.source_reference,
            sequence=command.sequence,
            event_schema=NOVEL_PROPOSED_SCHEMA,
        )
        return cast("NovelRecord", record), created

    async def get_record(self, context: SecurityContext, query: GetNovelRecordQuery) -> NovelRecord:
        return cast(
            "NovelRecord",
            await self._application.get_record(
                context, query.project_id, CreativeOwner.NOVEL, query.record_id
            ),
        )

    async def decide(
        self, context: SecurityContext, command: DecideNovelRecordCommand
    ) -> NovelRecord:
        return cast(
            "NovelRecord",
            await self._application.decide(
                context,
                command.project_id,
                CreativeOwner.NOVEL,
                command.record_id,
                command.decision,
                command.expected_work_version,
                NOVEL_DECIDED_SCHEMA,
            ),
        )
