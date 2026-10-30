"""In-memory and SQLAlchemy persistence for memory facts and context snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves mapped annotations.
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    and_,
    or_,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.modules.memory.domain import (
    AllowedAnchor,
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
    RetentionKind,
    RetentionRule,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory


class MemoryRecordRow(Base):
    __tablename__ = "memory_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    logical_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_memory_records_project"), nullable=True
    )
    universe_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    creator_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    provenance_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    retention_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decay_half_life_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("logical_id", "record_version", name="uq_memory_records_version"),
        CheckConstraint("record_version > 0", name="ck_memory_records_version_positive"),
        CheckConstraint(
            "importance >= 0 AND importance <= 1 AND confidence >= 0 AND confidence <= 1",
            name="ck_memory_records_scores_bounded",
        ),
        CheckConstraint(
            "(scope IN ('working','session','project') AND project_id IS NOT NULL "
            "AND universe_id IS NULL AND creator_id IS NULL) OR "
            "(scope = 'universe' AND project_id IS NULL AND universe_id IS NOT NULL "
            "AND creator_id IS NULL) OR (scope IN ('creator','experience','wisdom') "
            "AND project_id IS NULL AND universe_id IS NULL AND creator_id IS NOT NULL)",
            name="ck_memory_records_canonical_anchor",
        ),
        CheckConstraint(
            "(current AND status = 'active') OR (NOT current AND status <> 'active')",
            name="ck_memory_records_current_active",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_memory_records_valid_time",
        ),
        Index("ix_memory_records_scope_anchor", "workspace_id", "scope", "project_id"),
        Index(
            "uq_memory_records_current",
            "logical_id",
            unique=True,
            postgresql_where=current,
        ),
        {"schema": SCHEMA_NAME},
    )


class MemoryLinkRow(Base):
    __tablename__ = "memory_links"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    from_record_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("memory_records.id", name="fk_memory_links_from"), nullable=False
    )
    to_record_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("memory_records.id", name="fk_memory_links_to"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "from_record_id", "to_record_id", "relation", name="uq_memory_links_relation"
        ),
        CheckConstraint("from_record_id <> to_record_id", name="ck_memory_links_distinct"),
        Index("ix_memory_links_scope", "workspace_id", "from_record_id"),
        {"schema": SCHEMA_NAME},
    )


class MemoryGrantRow(Base):
    __tablename__ = "memory_grants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_memory_grants_project"), nullable=False
    )
    anchor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    anchor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    granted_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    can_write: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "anchor_kind",
            "anchor_id",
            name="uq_memory_grants_anchor",
        ),
        CheckConstraint("anchor_kind IN ('universe','creator')", name="ck_memory_grants_kind"),
        Index("ix_memory_grants_target", "workspace_id", "project_id", "revoked_at"),
        {"schema": SCHEMA_NAME},
    )


class MemoryConflictRow(Base):
    __tablename__ = "memory_conflicts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    current_record_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("memory_records.id", name="fk_memory_conflicts_current"), nullable=False
    )
    candidate_record_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("memory_records.id", name="fk_memory_conflicts_candidate"),
        nullable=False,
    )
    candidate_resolutions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    proposed_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("candidate_record_id", name="uq_memory_conflicts_candidate"),
        CheckConstraint(
            "status IN ('pending','accepted','rejected')", name="ck_memory_conflicts_status"
        ),
        Index("ix_memory_conflicts_scope", "workspace_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class MemoryContextPackageRow(Base):
    __tablename__ = "memory_context_packages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_memory_context_project"), nullable=False
    )
    task_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    budget_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    used_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_anchors: Mapped[list[dict[str, str]]] = mapped_column(JSON_TYPE, nullable=False)
    items: Mapped[list[dict[str, object]]] = mapped_column(JSON_TYPE, nullable=False)
    omissions: Mapped[list[dict[str, str | None]]] = mapped_column(JSON_TYPE, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "budget_chars > 0 AND used_chars >= 0 AND used_chars <= budget_chars",
            name="ck_memory_context_budget",
        ),
        CheckConstraint(
            "used_tokens >= 0 AND (budget_tokens IS NULL OR "
            "(budget_tokens > 0 AND used_tokens <= budget_tokens))",
            name="ck_memory_context_token_budget",
        ),
        Index("ix_memory_context_scope", "workspace_id", "project_id", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class MemoryEventRow(Base):
    __tablename__ = "memory_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_memory_events_scope", "workspace_id", "aggregate_id", "occurred_at"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryMemoryRepository:
    """Deterministic adapter used for unit tests and disconnected development."""

    def __init__(self) -> None:
        self.records: dict[UUID, MemoryRecord] = {}
        self.links: dict[UUID, MemoryLink] = {}
        self.grants: dict[UUID, MemoryGrant] = {}
        self.conflicts: dict[UUID, MemoryConflict] = {}
        self.packages: dict[UUID, ContextPackage] = {}
        self.events: list[tuple[str, UUID]] = []

    async def add(self, record: MemoryRecord, links: tuple[MemoryLink, ...] = ()) -> None:
        if record.id not in self.records:
            self.records[record.id] = record
            self.events.append(("memory.record-created", record.id))
        self.links.update({link.id: link for link in links})

    async def get_record(self, workspace_id: UUID, record_id: UUID) -> MemoryRecord | None:
        record = self.records.get(record_id)
        return record if record is not None and record.workspace_id == workspace_id else None

    async def retrieve(
        self,
        allowed_anchors: tuple[AllowedAnchor, ...],
        scopes: frozenset[MemoryScope],
        memory_types: frozenset[str],
    ) -> tuple[MemoryRecord, ...]:
        allowed = {(item.workspace_id, item.scope, item.anchor_id) for item in allowed_anchors}
        return tuple(
            record
            for record in self.records.values()
            if (record.workspace_id, record.scope, record.anchor_id) in allowed
            and record.scope in scopes
            and (not memory_types or record.memory_type in memory_types)
        )

    async def add_grant(self, grant: MemoryGrant) -> None:
        self.grants[grant.id] = grant
        self.events.append(("memory.grant-created", grant.id))

    async def grants_for(self, workspace_id: UUID, project_id: UUID) -> tuple[MemoryGrant, ...]:
        return tuple(
            grant
            for grant in self.grants.values()
            if grant.workspace_id == workspace_id
            and grant.project_id == project_id
            and grant.active
        )

    async def add_conflict(self, candidate: MemoryRecord, conflict: MemoryConflict) -> None:
        self.records[candidate.id] = candidate
        self.conflicts[conflict.id] = conflict
        self.events.append(("memory.conflict-proposed", conflict.id))

    async def get_conflict(self, workspace_id: UUID, conflict_id: UUID) -> MemoryConflict | None:
        conflict = self.conflicts.get(conflict_id)
        return conflict if conflict is not None and conflict.workspace_id == workspace_id else None

    async def decide_conflict(
        self,
        workspace_id: UUID,
        conflict_id: UUID,
        *,
        accepted: bool,
        decided_by: UUID,
        decided_at: datetime,
    ) -> MemoryConflict:
        conflict = self.conflicts.get(conflict_id)
        if conflict is None or conflict.workspace_id != workspace_id:
            raise ScopeViolationError
        if conflict.status is not MemoryConflictStatus.PENDING:
            raise InvalidStateError("Only pending memory conflicts can be decided.")
        current = self.records[conflict.current_record_id]
        candidate = self.records[conflict.candidate_record_id]
        if accepted:
            self.records[current.id] = replace(
                current, status=MemoryStatus.SUPERSEDED, current=False
            )
            self.records[candidate.id] = replace(
                candidate, status=MemoryStatus.ACTIVE, current=True
            )
            status = MemoryConflictStatus.ACCEPTED
        else:
            self.records[candidate.id] = replace(candidate, status=MemoryStatus.ARCHIVED)
            status = MemoryConflictStatus.REJECTED
        decided = replace(
            conflict,
            status=status,
            decided_by=decided_by,
            decided_at=decided_at,
        )
        self.conflicts[conflict.id] = decided
        self.events.append(("memory.conflict-decided", conflict.id))
        return decided

    async def archive(
        self, workspace_id: UUID, record_id: UUID, *, actor_id: UUID, archived_at: datetime
    ) -> MemoryRecord:
        del actor_id, archived_at
        record = await self.get_record(workspace_id, record_id)
        if record is None:
            raise ScopeViolationError
        if record.status is MemoryStatus.ARCHIVED:
            return record
        archived = replace(record, status=MemoryStatus.ARCHIVED, current=False)
        self.records[record_id] = archived
        self.events.append(("memory.record-archived", record_id))
        return archived

    async def save_package(self, package: ContextPackage) -> None:
        self.packages[package.id] = package
        self.events.append(("memory.context-built", package.id))

    async def get_package(
        self, workspace_id: UUID, project_id: UUID, package_id: UUID
    ) -> ContextPackage | None:
        package = self.packages.get(package_id)
        if (
            package is None
            or package.workspace_id != workspace_id
            or package.project_id != project_id
        ):
            return None
        return package


class SqlAlchemyMemoryRepository:
    """Atomic persistence whose retrieval entry point accepts only allowed anchors."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add(self, record: MemoryRecord, links: tuple[MemoryLink, ...] = ()) -> None:
        async with self._sessions.begin() as session:
            exists = await session.get(MemoryRecordRow, record.id)
            if exists is None:
                session.add(_record_row(record))
                await session.flush()
                session.add(
                    _event_row(
                        record.workspace_id,
                        record.id,
                        "memory.record-created",
                        record.created_by,
                        record.created_at,
                    )
                )
            session.add_all(_link_row(link) for link in links)

    async def get_record(self, workspace_id: UUID, record_id: UUID) -> MemoryRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MemoryRecordRow).where(
                    MemoryRecordRow.workspace_id == workspace_id, MemoryRecordRow.id == record_id
                )
            )
        return None if row is None else _record(row)

    async def retrieve(
        self,
        allowed_anchors: tuple[AllowedAnchor, ...],
        scopes: frozenset[MemoryScope],
        memory_types: frozenset[str],
    ) -> tuple[MemoryRecord, ...]:
        if not allowed_anchors:
            return ()
        anchor_clauses = []
        for anchor in allowed_anchors:
            column = (
                MemoryRecordRow.project_id
                if anchor.scope in {MemoryScope.WORKING, MemoryScope.SESSION, MemoryScope.PROJECT}
                else MemoryRecordRow.universe_id
                if anchor.scope is MemoryScope.UNIVERSE
                else MemoryRecordRow.creator_id
            )
            anchor_clauses.append(
                and_(
                    MemoryRecordRow.workspace_id == anchor.workspace_id,
                    MemoryRecordRow.scope == anchor.scope.value,
                    column == anchor.anchor_id,
                )
            )
        statement = select(MemoryRecordRow).where(
            or_(*anchor_clauses), MemoryRecordRow.scope.in_(item.value for item in scopes)
        )
        if memory_types:
            statement = statement.where(MemoryRecordRow.memory_type.in_(memory_types))
        async with self._sessions() as session:
            rows = (await session.scalars(statement.order_by(MemoryRecordRow.created_at))).all()
        return tuple(_record(row) for row in rows)

    async def add_grant(self, grant: MemoryGrant) -> None:
        async with self._sessions.begin() as session:
            session.add(_grant_row(grant))
            session.add(
                _event_row(
                    grant.workspace_id,
                    grant.id,
                    "memory.grant-created",
                    grant.granted_by,
                    grant.created_at,
                )
            )

    async def grants_for(self, workspace_id: UUID, project_id: UUID) -> tuple[MemoryGrant, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(MemoryGrantRow).where(
                        MemoryGrantRow.workspace_id == workspace_id,
                        MemoryGrantRow.project_id == project_id,
                        MemoryGrantRow.revoked_at.is_(None),
                    )
                )
            ).all()
        return tuple(_grant(row) for row in rows)

    async def add_conflict(self, candidate: MemoryRecord, conflict: MemoryConflict) -> None:
        async with self._sessions.begin() as session:
            session.add(_record_row(candidate))
            await session.flush()
            session.add(_conflict_row(conflict))
            session.add(
                _event_row(
                    conflict.workspace_id,
                    conflict.id,
                    "memory.conflict-proposed",
                    conflict.proposed_by,
                    conflict.proposed_at,
                )
            )

    async def get_conflict(self, workspace_id: UUID, conflict_id: UUID) -> MemoryConflict | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MemoryConflictRow).where(
                    MemoryConflictRow.workspace_id == workspace_id,
                    MemoryConflictRow.id == conflict_id,
                )
            )
        return None if row is None else _conflict(row)

    async def decide_conflict(
        self,
        workspace_id: UUID,
        conflict_id: UUID,
        *,
        accepted: bool,
        decided_by: UUID,
        decided_at: datetime,
    ) -> MemoryConflict:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(MemoryConflictRow)
                .where(
                    MemoryConflictRow.workspace_id == workspace_id,
                    MemoryConflictRow.id == conflict_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if MemoryConflictStatus(row.status) is not MemoryConflictStatus.PENDING:
                raise InvalidStateError("Only pending memory conflicts can be decided.")
            current = await _locked_record(session, row.current_record_id)
            candidate = await _locked_record(session, row.candidate_record_id)
            if accepted:
                current.status = MemoryStatus.SUPERSEDED.value
                current.current = False
                await session.flush([current])
                candidate.status = MemoryStatus.ACTIVE.value
                candidate.current = True
                status = MemoryConflictStatus.ACCEPTED
            else:
                candidate.status = MemoryStatus.ARCHIVED.value
                status = MemoryConflictStatus.REJECTED
            row.status = status.value
            row.decided_by = decided_by
            row.decided_at = decided_at
            session.add(
                _event_row(workspace_id, row.id, "memory.conflict-decided", decided_by, decided_at)
            )
            await session.flush()
            return _conflict(row)

    async def archive(
        self, workspace_id: UUID, record_id: UUID, *, actor_id: UUID, archived_at: datetime
    ) -> MemoryRecord:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(MemoryRecordRow)
                .where(
                    MemoryRecordRow.workspace_id == workspace_id, MemoryRecordRow.id == record_id
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if MemoryStatus(row.status) is MemoryStatus.ARCHIVED:
                return _record(row)
            row.status = MemoryStatus.ARCHIVED.value
            row.current = False
            session.add(
                _event_row(workspace_id, record_id, "memory.record-archived", actor_id, archived_at)
            )
            await session.flush()
            return _record(row)

    async def save_package(self, package: ContextPackage) -> None:
        async with self._sessions.begin() as session:
            session.add(_package_row(package))
            session.add(
                _event_row(
                    package.workspace_id,
                    package.id,
                    "memory.context-built",
                    package.created_by,
                    package.created_at,
                )
            )

    async def get_package(
        self, workspace_id: UUID, project_id: UUID, package_id: UUID
    ) -> ContextPackage | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MemoryContextPackageRow).where(
                    MemoryContextPackageRow.workspace_id == workspace_id,
                    MemoryContextPackageRow.project_id == project_id,
                    MemoryContextPackageRow.id == package_id,
                )
            )
        return None if row is None else _package(row)


async def _locked_record(session: AsyncSession, record_id: UUID) -> MemoryRecordRow:
    row = await session.scalar(
        select(MemoryRecordRow).where(MemoryRecordRow.id == record_id).with_for_update()
    )
    if row is None:
        raise InvalidStateError("Memory conflict record is unavailable.")
    return row


def _record_row(record: MemoryRecord) -> MemoryRecordRow:
    return MemoryRecordRow(
        id=record.id,
        logical_id=record.logical_id,
        record_version=record.version,
        workspace_id=record.workspace_id,
        scope=record.scope.value,
        memory_type=record.memory_type,
        content=record.content,
        project_id=record.project_id,
        universe_id=record.universe_id,
        creator_id=record.creator_id,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        observed_at=record.observed_at,
        importance=record.importance,
        confidence=record.confidence,
        provenance_kind=record.provenance.kind,
        provenance_reference=record.provenance.reference,
        retention_kind=record.retention.kind.value,
        ttl_seconds=record.retention.ttl_seconds,
        decay_half_life_seconds=record.retention.decay_half_life_seconds,
        status=record.status.value,
        current=record.current,
        created_by=record.created_by,
        created_at=record.created_at,
    )


def _record(row: MemoryRecordRow) -> MemoryRecord:
    return MemoryRecord(
        row.id,
        row.logical_id,
        row.record_version,
        row.workspace_id,
        MemoryScope(row.scope),
        row.memory_type,
        row.content,
        row.project_id,
        row.universe_id,
        row.creator_id,
        row.valid_from,
        row.valid_until,
        row.observed_at,
        row.importance,
        row.confidence,
        MemoryProvenance(row.provenance_kind, row.provenance_reference),
        RetentionRule(
            RetentionKind(row.retention_kind), row.ttl_seconds, row.decay_half_life_seconds
        ),
        MemoryStatus(row.status),
        row.current,
        row.created_by,
        row.created_at,
    )


def _link_row(link: MemoryLink) -> MemoryLinkRow:
    return MemoryLinkRow(
        id=link.id,
        workspace_id=link.workspace_id,
        from_record_id=link.from_record_id,
        to_record_id=link.to_record_id,
        relation=link.relation,
        created_at=link.created_at,
    )


def _grant_row(grant: MemoryGrant) -> MemoryGrantRow:
    return MemoryGrantRow(
        id=grant.id,
        workspace_id=grant.workspace_id,
        project_id=grant.project_id,
        anchor_kind=grant.anchor_kind.value,
        anchor_id=grant.anchor_id,
        granted_by=grant.granted_by,
        can_write=grant.can_write,
        created_at=grant.created_at,
        revoked_at=grant.revoked_at,
    )


def _grant(row: MemoryGrantRow) -> MemoryGrant:
    return MemoryGrant(
        row.id,
        row.workspace_id,
        row.project_id,
        MemoryAnchorKind(row.anchor_kind),
        row.anchor_id,
        row.granted_by,
        row.can_write,
        row.created_at,
        row.revoked_at,
    )


def _conflict_row(conflict: MemoryConflict) -> MemoryConflictRow:
    return MemoryConflictRow(
        id=conflict.id,
        workspace_id=conflict.workspace_id,
        current_record_id=conflict.current_record_id,
        candidate_record_id=conflict.candidate_record_id,
        candidate_resolutions=list(conflict.candidate_resolutions),
        status=conflict.status.value,
        proposed_by=conflict.proposed_by,
        proposed_at=conflict.proposed_at,
        decided_by=conflict.decided_by,
        decided_at=conflict.decided_at,
    )


def _conflict(row: MemoryConflictRow) -> MemoryConflict:
    return MemoryConflict(
        row.id,
        row.workspace_id,
        row.current_record_id,
        row.candidate_record_id,
        tuple(row.candidate_resolutions),
        MemoryConflictStatus(row.status),
        row.proposed_by,
        row.proposed_at,
        row.decided_by,
        row.decided_at,
    )


def _package_row(package: ContextPackage) -> MemoryContextPackageRow:
    return MemoryContextPackageRow(
        id=package.id,
        workspace_id=package.workspace_id,
        project_id=package.project_id,
        task_reference=package.task_reference,
        budget_chars=package.budget_chars,
        used_chars=package.used_chars,
        budget_tokens=package.budget_tokens,
        used_tokens=package.used_tokens,
        allowed_anchors=[
            {
                "workspace_id": str(item.workspace_id),
                "scope": item.scope.value,
                "anchor_id": str(item.anchor_id),
            }
            for item in package.allowed_anchors
        ],
        items=[
            {
                "record_id": str(item.record_id),
                "scope": item.scope.value,
                "memory_type": item.memory_type,
                "content": item.content,
                "score": item.score,
                "provenance_kind": item.provenance.kind,
                "provenance_reference": item.provenance.reference,
            }
            for item in package.items
        ],
        omissions=[
            {
                "reason": item.reason.value,
                "scope": item.scope.value,
                "memory_type": item.memory_type,
                "record_id": str(item.record_id) if item.record_id else None,
            }
            for item in package.omissions
        ],
        checksum=package.checksum,
        created_by=package.created_by,
        created_at=package.created_at,
    )


def _package(row: MemoryContextPackageRow) -> ContextPackage:
    return ContextPackage(
        row.id,
        row.workspace_id,
        row.project_id,
        row.task_reference,
        row.budget_chars,
        row.used_chars,
        tuple(
            AllowedAnchor(
                UUID(item["workspace_id"]), MemoryScope(item["scope"]), UUID(item["anchor_id"])
            )
            for item in row.allowed_anchors
        ),
        tuple(
            ContextItem(
                UUID(str(item["record_id"])),
                MemoryScope(str(item["scope"])),
                str(item["memory_type"]),
                str(item["content"]),
                cast("float", item["score"]),
                MemoryProvenance(str(item["provenance_kind"]), str(item["provenance_reference"])),
            )
            for item in row.items
        ),
        tuple(
            ContextOmission(
                OmissionReason(str(item["reason"])),
                MemoryScope(str(item["scope"])),
                str(item["memory_type"]) if item["memory_type"] is not None else None,
                UUID(str(item["record_id"])) if item["record_id"] is not None else None,
            )
            for item in row.omissions
        ),
        row.checksum,
        row.created_by,
        row.created_at,
        row.budget_tokens,
        row.used_tokens,
    )


def _event_row(
    workspace_id: UUID,
    aggregate_id: UUID,
    event_type: str,
    actor_id: UUID,
    occurred_at: datetime,
) -> MemoryEventRow:
    return MemoryEventRow(
        id=uuid4(),
        workspace_id=workspace_id,
        aggregate_id=aggregate_id,
        event_type=event_type,
        actor_id=actor_id,
        payload={"schema": f"{event_type}.v1"},
        occurred_at=occurred_at,
    )


MODEL_REGISTRY = (
    MemoryRecordRow,
    MemoryLinkRow,
    MemoryGrantRow,
    MemoryConflictRow,
    MemoryContextPackageRow,
    MemoryEventRow,
)
