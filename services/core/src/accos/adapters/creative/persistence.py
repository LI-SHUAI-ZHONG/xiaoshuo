"""Scoped in-memory and PostgreSQL persistence for creative metadata."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations.
from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.modules.creative.character import (
    BehaviorProposal,
    Character,
    CharacterState,
    GrowthArc,
    GrowthEvent,
    Motivation,
    PsychologyState,
    Relationship,
)
from accos.modules.creative.common import (
    CreativeContainer,
    CreativeDecision,
    CreativeOwner,
    CreativeRecord,
    CreativeRecordStatus,
    CreativeReference,
    CreativeReferenceKind,
)
from accos.modules.creative.creator import (
    CreatorProfile,
    DecisionRecord,
    EvaluationPreference,
    PreferenceSignal,
    StyleProfile,
)
from accos.modules.creative.novel import (
    Chapter,
    ConceptRef,
    DraftRevision,
    EvaluationRequest,
    PlotPlan,
    ThemeRef,
    Work,
)
from accos.modules.creative.world import (
    Civilization,
    ImpactLink,
    Location,
    ScenarioRequest,
    World,
    WorldEvent,
    WorldRule,
    WorldState,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope


class CreativeContainerRow(Base):
    """One of four empty creative aggregate roots."""

    __tablename__ = "creative_containers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner: Mapped[str] = mapped_column(String(20), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_creative_containers_project"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    references: Mapped[list[dict[str, str]]] = mapped_column(JSON_TYPE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "id",
            "owner",
            "workspace_id",
            "project_id",
            name="uq_creative_containers_owner_scope",
        ),
        CheckConstraint(
            "owner IN ('novel','world','character','creator')",
            name="ck_creative_containers_owner",
        ),
        CheckConstraint("version > 0", name="ck_creative_containers_version"),
        Index("ix_creative_containers_scope", "workspace_id", "project_id", "owner"),
        {"schema": SCHEMA_NAME},
    )


class CreativeRecordRow(Base):
    """Versioned state metadata; proposals remain separate until decided."""

    __tablename__ = "creative_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    logical_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    owner: Mapped[str] = mapped_column(String(20), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    references: Mapped[list[dict[str, str]]] = mapped_column(JSON_TYPE, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    causation_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    source_event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    decided_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["aggregate_id", "owner", "workspace_id", "project_id"],
            [
                "creative_containers.id",
                "creative_containers.owner",
                "creative_containers.workspace_id",
                "creative_containers.project_id",
            ],
            name="fk_creative_records_container_owner",
        ),
        UniqueConstraint("logical_id", "record_version", name="uq_creative_records_version"),
        CheckConstraint(
            "owner IN ('novel','world','character','creator')",
            name="ck_creative_records_owner",
        ),
        CheckConstraint("record_version > 0", name="ck_creative_records_version"),
        CheckConstraint(
            "status IN ('proposal','current','superseded','rejected','archived')",
            name="ck_creative_records_status",
        ),
        CheckConstraint(
            "(current AND status = 'current') OR (NOT current AND status <> 'current')",
            name="ck_creative_records_current",
        ),
        CheckConstraint("sequence IS NULL OR sequence >= 0", name="ck_creative_records_sequence"),
        CheckConstraint(
            "(causation_id IS NULL) = (source_event_id IS NULL)",
            name="ck_creative_records_causation_pair",
        ),
        CheckConstraint(
            "(decided_by IS NULL) = (decided_at IS NULL)",
            name="ck_creative_records_decision_pair",
        ),
        Index("ix_creative_records_scope", "workspace_id", "project_id", "owner"),
        Index(
            "uq_creative_records_current",
            "logical_id",
            unique=True,
            postgresql_where=current,
        ),
        Index(
            "uq_creative_records_causation",
            "workspace_id",
            "project_id",
            "owner",
            "causation_id",
            unique=True,
            postgresql_where=causation_id.is_not(None),
        ),
        {"schema": SCHEMA_NAME},
    )


_CONTAINER_TYPES: dict[CreativeOwner, type[CreativeContainer]] = {
    CreativeOwner.NOVEL: Work,
    CreativeOwner.WORLD: World,
    CreativeOwner.CHARACTER: Character,
    CreativeOwner.CREATOR: CreatorProfile,
}
_RECORD_TYPES: dict[tuple[CreativeOwner, str], type[CreativeRecord]] = {
    (record_type.owner, record_type.entity_type): record_type
    for record_type in (
        ConceptRef,
        ThemeRef,
        PlotPlan,
        Chapter,
        DraftRevision,
        EvaluationRequest,
        WorldState,
        WorldRule,
        Civilization,
        Location,
        WorldEvent,
        ImpactLink,
        ScenarioRequest,
        CharacterState,
        PsychologyState,
        Relationship,
        GrowthArc,
        GrowthEvent,
        Motivation,
        BehaviorProposal,
        PreferenceSignal,
        StyleProfile,
        DecisionRecord,
        EvaluationPreference,
    )
}


class InMemoryCreativeRepository:
    """Deterministic adapter for unit tests and disconnected development."""

    def __init__(self) -> None:
        self.containers: dict[UUID, CreativeContainer] = {}
        self.records: dict[UUID, CreativeRecord] = {}
        self.events: list[EventEnvelope] = []

    async def add_container(
        self, container: CreativeContainer, event: EventEnvelope
    ) -> CreativeContainer:
        existing = self.containers.get(container.id)
        if existing is not None:
            return existing
        self.containers[container.id] = container
        self.events.append(event)
        return container

    async def get_container(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer | None:
        container = self.containers.get(container_id)
        if container is None or (
            container.workspace_id,
            container.project_id,
            container.owner,
        ) != (workspace_id, project_id, owner):
            return None
        return container

    async def add_proposal(
        self, record: CreativeRecord, event: EventEnvelope
    ) -> tuple[CreativeRecord, bool]:
        if record.causation_id is not None:
            existing = next(
                (
                    item
                    for item in self.records.values()
                    if (
                        item.workspace_id,
                        item.project_id,
                        item.owner,
                        item.causation_id,
                    )
                    == (
                        record.workspace_id,
                        record.project_id,
                        record.owner,
                        record.causation_id,
                    )
                ),
                None,
            )
            if existing is not None:
                return existing, False
        existing = self.records.get(record.id)
        if existing is not None:
            return existing, False
        self.records[record.id] = record
        self.events.append(event)
        return record, True

    async def get_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
    ) -> CreativeRecord | None:
        record = self.records.get(record_id)
        if record is None or (record.workspace_id, record.project_id, record.owner) != (
            workspace_id,
            project_id,
            owner,
        ):
            return None
        return record

    async def get_current_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        logical_id: UUID,
    ) -> CreativeRecord | None:
        return next(
            (
                item
                for item in self.records.values()
                if (
                    item.workspace_id,
                    item.project_id,
                    item.owner,
                    item.logical_id,
                    item.current,
                )
                == (workspace_id, project_id, owner, logical_id, True)
            ),
            None,
        )

    async def decide_proposal(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
        *,
        decision: CreativeDecision,
        expected_container_version: int,
        decided_by: UUID,
        decided_at: datetime,
        event: EventEnvelope,
    ) -> CreativeRecord:
        record = await self.get_record(workspace_id, project_id, owner, record_id)
        if record is None:
            raise ScopeViolationError
        if record.status is not CreativeRecordStatus.PROPOSAL:
            raise InvalidStateError("Only creative proposals can be decided.")
        container = await self.get_container(workspace_id, project_id, owner, record.aggregate_id)
        if container is None:
            raise ScopeViolationError
        if container.version != expected_container_version:
            raise ConcurrencyConflictError
        if decision is CreativeDecision.APPROVE:
            for item in tuple(self.records.values()):
                if item.logical_id == record.logical_id and item.current:
                    self.records[item.id] = replace(
                        item, status=CreativeRecordStatus.SUPERSEDED, current=False
                    )
            status, current = CreativeRecordStatus.CURRENT, True
        else:
            status, current = CreativeRecordStatus.REJECTED, False
        decided = replace(
            record,
            status=status,
            current=current,
            decided_by=decided_by,
            decided_at=decided_at,
        )
        self.records[record.id] = decided
        self.containers[container.id] = replace(
            container, updated_at=decided_at, version=container.version + 1
        )
        self.events.append(event)
        return decided


class SqlAlchemyCreativeRepository:
    """One physical adapter with mandatory owner, workspace, and project predicates."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add_container(
        self, container: CreativeContainer, event: EventEnvelope
    ) -> CreativeContainer:
        async with self._sessions.begin() as session:
            existing = await session.get(CreativeContainerRow, container.id)
            if existing is not None:
                return _container(existing)
            session.add(_container_row(container))
            await SqlAlchemyOutboxWriter(session).append(event)
        return container

    async def get_container(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(CreativeContainerRow).where(
                    CreativeContainerRow.workspace_id == workspace_id,
                    CreativeContainerRow.project_id == project_id,
                    CreativeContainerRow.owner == owner.value,
                    CreativeContainerRow.id == container_id,
                )
            )
        return None if row is None else _container(row)

    async def add_proposal(
        self, record: CreativeRecord, event: EventEnvelope
    ) -> tuple[CreativeRecord, bool]:
        async with self._sessions.begin() as session:
            if record.causation_id is not None:
                causal = await session.scalar(
                    select(CreativeRecordRow).where(
                        CreativeRecordRow.workspace_id == record.workspace_id,
                        CreativeRecordRow.project_id == record.project_id,
                        CreativeRecordRow.owner == record.owner.value,
                        CreativeRecordRow.causation_id == record.causation_id,
                    )
                )
                if causal is not None:
                    return _record(causal), False
            existing = await session.get(CreativeRecordRow, record.id)
            if existing is not None:
                return _record(existing), False
            session.add(_record_row(record))
            await SqlAlchemyOutboxWriter(session).append(event)
        return record, True

    async def get_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
    ) -> CreativeRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(CreativeRecordRow).where(
                    CreativeRecordRow.workspace_id == workspace_id,
                    CreativeRecordRow.project_id == project_id,
                    CreativeRecordRow.owner == owner.value,
                    CreativeRecordRow.id == record_id,
                )
            )
        return None if row is None else _record(row)

    async def get_current_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        logical_id: UUID,
    ) -> CreativeRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(CreativeRecordRow).where(
                    CreativeRecordRow.workspace_id == workspace_id,
                    CreativeRecordRow.project_id == project_id,
                    CreativeRecordRow.owner == owner.value,
                    CreativeRecordRow.logical_id == logical_id,
                    CreativeRecordRow.current.is_(True),
                )
            )
        return None if row is None else _record(row)

    async def decide_proposal(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
        *,
        decision: CreativeDecision,
        expected_container_version: int,
        decided_by: UUID,
        decided_at: datetime,
        event: EventEnvelope,
    ) -> CreativeRecord:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(CreativeRecordRow)
                .where(
                    CreativeRecordRow.workspace_id == workspace_id,
                    CreativeRecordRow.project_id == project_id,
                    CreativeRecordRow.owner == owner.value,
                    CreativeRecordRow.id == record_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if row.status != CreativeRecordStatus.PROPOSAL.value:
                raise InvalidStateError("Only creative proposals can be decided.")
            container = cast(
                "CreativeContainerRow",
                await session.scalar(
                    select(CreativeContainerRow)
                    .where(
                        CreativeContainerRow.workspace_id == workspace_id,
                        CreativeContainerRow.project_id == project_id,
                        CreativeContainerRow.owner == owner.value,
                        CreativeContainerRow.id == row.aggregate_id,
                    )
                    .with_for_update()
                ),
            )
            if container.version != expected_container_version:
                raise ConcurrencyConflictError
            if decision is CreativeDecision.APPROVE:
                current = await session.scalar(
                    select(CreativeRecordRow).where(
                        CreativeRecordRow.logical_id == row.logical_id,
                        CreativeRecordRow.current.is_(True),
                    )
                )
                if current is not None:
                    current.status = CreativeRecordStatus.SUPERSEDED.value
                    current.current = False
                    await session.flush()
                row.status = CreativeRecordStatus.CURRENT.value
                row.current = True
            else:
                row.status = CreativeRecordStatus.REJECTED.value
                row.current = False
            row.decided_by = decided_by
            row.decided_at = decided_at
            container.updated_at = decided_at
            container.version += 1
            await SqlAlchemyOutboxWriter(session).append(event)
            await session.flush()
            return _record(row)


def _references_json(references: tuple[CreativeReference, ...]) -> list[dict[str, str]]:
    return [{"kind": item.kind.value, "id": str(item.id)} for item in references]


def _references(value: list[dict[str, str]]) -> tuple[CreativeReference, ...]:
    return tuple(
        CreativeReference(CreativeReferenceKind(item["kind"]), UUID(item["id"])) for item in value
    )


def _container_row(container: CreativeContainer) -> CreativeContainerRow:
    return CreativeContainerRow(
        id=container.id,
        owner=container.owner.value,
        workspace_id=container.workspace_id,
        project_id=container.project_id,
        label=container.label,
        references=_references_json(container.references),
        created_by=container.created_by,
        created_at=container.created_at,
        updated_at=container.updated_at,
        version=container.version,
    )


def _container(row: CreativeContainerRow) -> CreativeContainer:
    return _CONTAINER_TYPES[CreativeOwner(row.owner)](
        row.id,
        row.workspace_id,
        row.project_id,
        row.label,
        _references(row.references),
        row.created_by,
        row.created_at,
        row.updated_at,
        row.version,
    )


def _record_row(record: CreativeRecord) -> CreativeRecordRow:
    return CreativeRecordRow(
        id=record.id,
        logical_id=record.logical_id,
        record_version=record.record_version,
        workspace_id=record.workspace_id,
        project_id=record.project_id,
        owner=record.owner.value,
        aggregate_id=record.aggregate_id,
        entity_type=record.entity_type,
        status=record.status.value,
        current=record.current,
        references=_references_json(record.references),
        source_reference=record.source_reference,
        sequence=record.sequence,
        created_by=record.created_by,
        created_at=record.created_at,
        causation_id=record.causation_id,
        source_event_id=record.source_event_id,
        decided_by=record.decided_by,
        decided_at=record.decided_at,
    )


def _record(row: CreativeRecordRow) -> CreativeRecord:
    owner = CreativeOwner(row.owner)
    return _RECORD_TYPES[(owner, row.entity_type)](
        row.id,
        row.logical_id,
        row.record_version,
        row.workspace_id,
        row.project_id,
        row.aggregate_id,
        CreativeRecordStatus(row.status),
        row.current,
        _references(row.references),
        row.source_reference,
        row.sequence,
        row.created_by,
        row.created_at,
        row.causation_id,
        row.source_event_id,
        row.decided_by,
        row.decided_at,
    )


MODEL_REGISTRY = (CreativeContainerRow, CreativeRecordRow)
