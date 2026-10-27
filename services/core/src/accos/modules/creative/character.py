"""Character-owned state, psychology, relationship, growth, and behavior contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from accos.modules.creative.common import (
    CreativeContainer,
    CreativeDecision,
    CreativeOwner,
    CreativeRecord,
    CreativeReference,
)

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.security import SecurityContext
    from accos.modules.creative.application import CreativeApplication

CHARACTER_CREATED_SCHEMA = "creative.character.character-created.v1"
CHARACTER_PROPOSED_SCHEMA = "creative.character.record-proposed.v1"
CHARACTER_DECIDED_SCHEMA = "creative.character.record-decided.v1"
WORLD_EVENT_SCHEMA = "creative.world.event-recorded.v1"
CHARACTER_IMPACT_PROPOSED_SCHEMA = "creative.character.impact-proposed.v1"


@dataclass(frozen=True, slots=True)
class Character(CreativeContainer):
    owner = CreativeOwner.CHARACTER


@dataclass(frozen=True, slots=True)
class CharacterState(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "character_state"


@dataclass(frozen=True, slots=True)
class PsychologyState(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "psychology_state"


@dataclass(frozen=True, slots=True)
class Relationship(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "relationship"


@dataclass(frozen=True, slots=True)
class GrowthArc(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "growth_arc"


@dataclass(frozen=True, slots=True)
class GrowthEvent(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "growth_event"


@dataclass(frozen=True, slots=True)
class Motivation(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "motivation"


@dataclass(frozen=True, slots=True)
class BehaviorProposal(CreativeRecord):
    owner = CreativeOwner.CHARACTER
    entity_type = "behavior_proposal"


CHARACTER_RECORD_TYPES: tuple[type[CreativeRecord], ...] = (
    CharacterState,
    PsychologyState,
    Relationship,
    GrowthArc,
    GrowthEvent,
    Motivation,
    BehaviorProposal,
)
type CharacterRecord = (
    CharacterState
    | PsychologyState
    | Relationship
    | GrowthArc
    | GrowthEvent
    | Motivation
    | BehaviorProposal
)


@dataclass(frozen=True, slots=True)
class CreateCharacterCommand:
    project_id: UUID
    label: str
    references: tuple[CreativeReference, ...] = ()


@dataclass(frozen=True, slots=True)
class GetCharacterQuery:
    project_id: UUID
    character_id: UUID


@dataclass(frozen=True, slots=True)
class ProposeCharacterRecordCommand:
    project_id: UUID
    character_id: UUID
    record_type: type[CreativeRecord]
    logical_id: UUID | None = None
    record_version: int = 1
    references: tuple[CreativeReference, ...] = ()
    source_reference: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class ProposeCharacterImpactCommand:
    project_id: UUID
    character_id: UUID
    causation_id: UUID
    source_event_id: UUID
    references: tuple[CreativeReference, ...] = ()


@dataclass(frozen=True, slots=True)
class GetCharacterRecordQuery:
    project_id: UUID
    record_id: UUID


@dataclass(frozen=True, slots=True)
class DecideCharacterRecordCommand:
    project_id: UUID
    record_id: UUID
    decision: CreativeDecision
    expected_character_version: int


class CharacterService:
    """Own Character facts and produce inert impacts from WorldEvent events."""

    def __init__(self, application: CreativeApplication) -> None:
        self._application = application

    async def create(self, context: SecurityContext, command: CreateCharacterCommand) -> Character:
        return cast(
            "Character",
            await self._application.create_container(
                context,
                command.project_id,
                Character,
                command.label,
                command.references,
                CHARACTER_CREATED_SCHEMA,
            ),
        )

    async def get(self, context: SecurityContext, query: GetCharacterQuery) -> Character:
        return cast(
            "Character",
            await self._application.get_container(
                context, query.project_id, CreativeOwner.CHARACTER, query.character_id
            ),
        )

    async def propose(
        self, context: SecurityContext, command: ProposeCharacterRecordCommand
    ) -> tuple[CharacterRecord, bool]:
        if command.record_type not in CHARACTER_RECORD_TYPES:
            raise ValueError("record type is not owned by Character")
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.character_id,
            command.record_type,
            logical_id=command.logical_id,
            record_version=command.record_version,
            references=command.references,
            source_reference=command.source_reference,
            sequence=command.sequence,
            event_schema=CHARACTER_PROPOSED_SCHEMA,
        )
        return cast("CharacterRecord", record), created

    async def propose_world_event_impact(
        self, context: SecurityContext, command: ProposeCharacterImpactCommand
    ) -> tuple[BehaviorProposal, bool]:
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.character_id,
            BehaviorProposal,
            logical_id=None,
            record_version=1,
            references=command.references,
            source_reference=None,
            sequence=None,
            event_schema=CHARACTER_IMPACT_PROPOSED_SCHEMA,
            causation_id=command.causation_id,
            source_event_id=command.source_event_id,
        )
        return cast("BehaviorProposal", record), created

    async def get_record(
        self, context: SecurityContext, query: GetCharacterRecordQuery
    ) -> CharacterRecord:
        return cast(
            "CharacterRecord",
            await self._application.get_record(
                context, query.project_id, CreativeOwner.CHARACTER, query.record_id
            ),
        )

    async def decide(
        self, context: SecurityContext, command: DecideCharacterRecordCommand
    ) -> CharacterRecord:
        return cast(
            "CharacterRecord",
            await self._application.decide(
                context,
                command.project_id,
                CreativeOwner.CHARACTER,
                command.record_id,
                command.decision,
                command.expected_character_version,
                CHARACTER_DECIDED_SCHEMA,
            ),
        )
