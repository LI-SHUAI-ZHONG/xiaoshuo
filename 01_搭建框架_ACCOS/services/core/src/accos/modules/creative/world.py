"""World-owned state, component, impact, command, query, and event contracts."""

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

WORLD_CREATED_SCHEMA = "creative.world.world-created.v1"
WORLD_PROPOSED_SCHEMA = "creative.world.record-proposed.v1"
WORLD_DECIDED_SCHEMA = "creative.world.record-decided.v1"
CHARACTER_ACTION_SCHEMA = "creative.character.action-recorded.v1"
WORLD_IMPACT_PROPOSED_SCHEMA = "creative.world.impact-proposed.v1"


@dataclass(frozen=True, slots=True)
class World(CreativeContainer):
    owner = CreativeOwner.WORLD


@dataclass(frozen=True, slots=True)
class WorldState(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "world_state"


@dataclass(frozen=True, slots=True)
class WorldRule(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "world_rule"


@dataclass(frozen=True, slots=True)
class Civilization(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "civilization"


@dataclass(frozen=True, slots=True)
class Location(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "location"


@dataclass(frozen=True, slots=True)
class WorldEvent(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "world_event"


@dataclass(frozen=True, slots=True)
class ImpactLink(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "impact_link"


@dataclass(frozen=True, slots=True)
class ScenarioRequest(CreativeRecord):
    owner = CreativeOwner.WORLD
    entity_type = "scenario_request"


WORLD_RECORD_TYPES: tuple[type[CreativeRecord], ...] = (
    WorldState,
    WorldRule,
    Civilization,
    Location,
    WorldEvent,
    ImpactLink,
    ScenarioRequest,
)
type WorldRecord = (
    WorldState | WorldRule | Civilization | Location | WorldEvent | ImpactLink | ScenarioRequest
)


@dataclass(frozen=True, slots=True)
class CreateWorldCommand:
    project_id: UUID
    label: str
    references: tuple[CreativeReference, ...] = ()


@dataclass(frozen=True, slots=True)
class GetWorldQuery:
    project_id: UUID
    world_id: UUID


@dataclass(frozen=True, slots=True)
class ProposeWorldRecordCommand:
    project_id: UUID
    world_id: UUID
    record_type: type[CreativeRecord]
    logical_id: UUID | None = None
    record_version: int = 1
    references: tuple[CreativeReference, ...] = ()
    source_reference: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class ProposeWorldImpactCommand:
    project_id: UUID
    world_id: UUID
    causation_id: UUID
    source_event_id: UUID
    references: tuple[CreativeReference, ...] = ()


@dataclass(frozen=True, slots=True)
class GetWorldRecordQuery:
    project_id: UUID
    record_id: UUID


@dataclass(frozen=True, slots=True)
class DecideWorldRecordCommand:
    project_id: UUID
    record_id: UUID
    decision: CreativeDecision
    expected_world_version: int


class WorldService:
    """Own World facts and produce inert impacts from CharacterAction events."""

    def __init__(self, application: CreativeApplication) -> None:
        self._application = application

    async def create(self, context: SecurityContext, command: CreateWorldCommand) -> World:
        return cast(
            "World",
            await self._application.create_container(
                context,
                command.project_id,
                World,
                command.label,
                command.references,
                WORLD_CREATED_SCHEMA,
            ),
        )

    async def get(self, context: SecurityContext, query: GetWorldQuery) -> World:
        return cast(
            "World",
            await self._application.get_container(
                context, query.project_id, CreativeOwner.WORLD, query.world_id
            ),
        )

    async def propose(
        self, context: SecurityContext, command: ProposeWorldRecordCommand
    ) -> tuple[WorldRecord, bool]:
        if command.record_type not in WORLD_RECORD_TYPES:
            raise ValueError("record type is not owned by World")
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.world_id,
            command.record_type,
            logical_id=command.logical_id,
            record_version=command.record_version,
            references=command.references,
            source_reference=command.source_reference,
            sequence=command.sequence,
            event_schema=WORLD_PROPOSED_SCHEMA,
        )
        return cast("WorldRecord", record), created

    async def propose_character_action_impact(
        self, context: SecurityContext, command: ProposeWorldImpactCommand
    ) -> tuple[ImpactLink, bool]:
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.world_id,
            ImpactLink,
            logical_id=None,
            record_version=1,
            references=command.references,
            source_reference=None,
            sequence=None,
            event_schema=WORLD_IMPACT_PROPOSED_SCHEMA,
            causation_id=command.causation_id,
            source_event_id=command.source_event_id,
        )
        return cast("ImpactLink", record), created

    async def get_record(self, context: SecurityContext, query: GetWorldRecordQuery) -> WorldRecord:
        return cast(
            "WorldRecord",
            await self._application.get_record(
                context, query.project_id, CreativeOwner.WORLD, query.record_id
            ),
        )

    async def decide(
        self, context: SecurityContext, command: DecideWorldRecordCommand
    ) -> WorldRecord:
        return cast(
            "WorldRecord",
            await self._application.decide(
                context,
                command.project_id,
                CreativeOwner.WORLD,
                command.record_id,
                command.decision,
                command.expected_world_version,
                WORLD_DECIDED_SCHEMA,
            ),
        )
