"""Creator-owned authorized signal and preference metadata skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from accos.modules.creative.common import (
    CreativeContainer,
    CreativeDecision,
    CreativeOwner,
    CreativeRecord,
    CreativeReference,
    CreativeReferenceKind,
)
from accos.modules.creative.extensions import ExtensionResult, ExtensionStatus

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.security import SecurityContext
    from accos.modules.creative.application import CreativeApplication

CREATOR_PROFILE_CREATED_SCHEMA = "creative.creator.profile-created.v1"
CREATOR_PROPOSED_SCHEMA = "creative.creator.record-proposed.v1"
CREATOR_DECIDED_SCHEMA = "creative.creator.record-decided.v1"
PREFERENCE_SIGNAL_INGESTED_SCHEMA = "creative.creator.preference-signal-ingested.v1"


@dataclass(frozen=True, slots=True)
class CreatorProfile(CreativeContainer):
    owner = CreativeOwner.CREATOR

    def __post_init__(self) -> None:
        CreativeContainer.__post_init__(self)
        if (
            len(self.references) != 1
            or self.references[0].kind is not CreativeReferenceKind.CREATOR
        ):
            raise ValueError("CreatorProfile requires exactly one Creator reference")

    @property
    def creator_id(self) -> UUID:
        """Return the self-authorized creator anchor."""
        return self.references[0].id


@dataclass(frozen=True, slots=True)
class PreferenceSignal(CreativeRecord):
    owner = CreativeOwner.CREATOR
    entity_type = "preference_signal"


@dataclass(frozen=True, slots=True)
class StyleProfile(CreativeRecord):
    owner = CreativeOwner.CREATOR
    entity_type = "style_profile"


@dataclass(frozen=True, slots=True)
class DecisionRecord(CreativeRecord):
    owner = CreativeOwner.CREATOR
    entity_type = "decision_record"


@dataclass(frozen=True, slots=True)
class EvaluationPreference(CreativeRecord):
    owner = CreativeOwner.CREATOR
    entity_type = "evaluation_preference"


CREATOR_RECORD_TYPES: tuple[type[CreativeRecord], ...] = (
    StyleProfile,
    DecisionRecord,
    EvaluationPreference,
)
type CreatorRecord = StyleProfile | DecisionRecord | EvaluationPreference


class PreferenceSignalIngestPort(Protocol):
    """Execution 15 may bind Feedback events to this explicit boundary."""

    async def ingest(
        self, context: SecurityContext, signal: PreferenceSignal
    ) -> ExtensionResult: ...


class NullPreferenceSignalIngestPort:
    """No signal is captured until an authorized adapter is configured."""

    async def ingest(self, context: SecurityContext, signal: PreferenceSignal) -> ExtensionResult:
        del context, signal
        return ExtensionResult(ExtensionStatus.NOT_CONFIGURED)


@dataclass(frozen=True, slots=True)
class CreateCreatorProfileCommand:
    project_id: UUID
    label: str


@dataclass(frozen=True, slots=True)
class GetCreatorProfileQuery:
    project_id: UUID
    profile_id: UUID


@dataclass(frozen=True, slots=True)
class ProposeCreatorRecordCommand:
    project_id: UUID
    profile_id: UUID
    record_type: type[CreativeRecord]
    logical_id: UUID | None = None
    record_version: int = 1
    references: tuple[CreativeReference, ...] = ()
    source_reference: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class GetCreatorRecordQuery:
    project_id: UUID
    record_id: UUID


@dataclass(frozen=True, slots=True)
class DecideCreatorRecordCommand:
    project_id: UUID
    record_id: UUID
    decision: CreativeDecision
    expected_profile_version: int


class CreatorService:
    """Persist approved profile metadata without observing prose or behavior."""

    def __init__(
        self,
        application: CreativeApplication,
        signal_ingest: PreferenceSignalIngestPort,
    ) -> None:
        self._application = application
        self._signal_ingest = signal_ingest

    async def create(
        self, context: SecurityContext, command: CreateCreatorProfileCommand
    ) -> CreatorProfile:
        return cast(
            "CreatorProfile",
            await self._application.create_container(
                context,
                command.project_id,
                CreatorProfile,
                command.label,
                (CreativeReference(CreativeReferenceKind.CREATOR, context.actor_id),),
                CREATOR_PROFILE_CREATED_SCHEMA,
            ),
        )

    async def get(self, context: SecurityContext, query: GetCreatorProfileQuery) -> CreatorProfile:
        return cast(
            "CreatorProfile",
            await self._application.get_container(
                context, query.project_id, CreativeOwner.CREATOR, query.profile_id
            ),
        )

    async def propose(
        self, context: SecurityContext, command: ProposeCreatorRecordCommand
    ) -> tuple[CreatorRecord, bool]:
        if command.record_type not in CREATOR_RECORD_TYPES:
            raise ValueError("record type is not an authorized Creator proposal")
        record, created = await self._application.propose(
            context,
            command.project_id,
            command.profile_id,
            command.record_type,
            logical_id=command.logical_id,
            record_version=command.record_version,
            references=command.references,
            source_reference=command.source_reference,
            sequence=command.sequence,
            event_schema=CREATOR_PROPOSED_SCHEMA,
        )
        return cast("CreatorRecord", record), created

    async def get_record(
        self, context: SecurityContext, query: GetCreatorRecordQuery
    ) -> CreatorRecord:
        return cast(
            "CreatorRecord",
            await self._application.get_record(
                context, query.project_id, CreativeOwner.CREATOR, query.record_id
            ),
        )

    async def decide(
        self, context: SecurityContext, command: DecideCreatorRecordCommand
    ) -> CreatorRecord:
        return cast(
            "CreatorRecord",
            await self._application.decide(
                context,
                command.project_id,
                CreativeOwner.CREATOR,
                command.record_id,
                command.decision,
                command.expected_profile_version,
                CREATOR_DECIDED_SCHEMA,
            ),
        )

    async def ingest_signal(
        self,
        context: SecurityContext,
        project_id: UUID,
        signal: PreferenceSignal,
    ) -> ExtensionResult:
        """Delegate only an explicit, self-scoped signal; Null stores nothing."""
        await self._application.authorize_write(context, project_id)
        profile = await self._application.get_container(
            context, project_id, CreativeOwner.CREATOR, signal.aggregate_id
        )
        if (
            signal.workspace_id != context.workspace_id
            or signal.project_id != project_id
            or cast("CreatorProfile", profile).creator_id != context.actor_id
        ):
            raise ValueError("preference signal is not self-authorized for this profile")
        return await self._signal_ingest.ingest(context, signal)
