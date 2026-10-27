"""PostgreSQL and deterministic in-memory consistency repositories."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves annotations at runtime.
from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    delete,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.modules.consistency.domain import (
    AppliedRevision,
    CanonEntry,
    CanonLevel,
    CanonStatus,
    ConsistencyCheckRun,
    EvidenceProjection,
    FactTarget,
    Finding,
    FindingDraft,
    FindingSeverity,
    FindingStatus,
    FindingType,
    ResolutionDecision,
    ResolutionProposal,
    ResolutionStatus,
    TimelineEvent,
    ValidationStatus,
    ValidatorReport,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope


class CanonEntryRow(Base):
    __tablename__ = "consistency_canon_entries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    logical_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_consistency_canon_project"), nullable=False
    )
    canon_key: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_version: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("entry_version > 0", name="ck_consistency_canon_version"),
        Index(
            "uq_consistency_canon_version",
            "workspace_id",
            "project_id",
            "logical_id",
            "entry_version",
            unique=True,
        ),
        {"schema": SCHEMA_NAME},
    )


class TimelineEventRow(Base):
    __tablename__ = "consistency_timeline_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_consistency_timeline_project"), nullable=False
    )
    event_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    character_state_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    world_state_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("sequence >= 0", name="ck_consistency_timeline_sequence"),
        CheckConstraint("source_version > 0", name="ck_consistency_timeline_version"),
        Index(
            "ix_consistency_timeline_scope",
            "workspace_id",
            "project_id",
            "occurred_at",
            "sequence",
        ),
        {"schema": SCHEMA_NAME},
    )


class ConsistencyCheckRunRow(Base):
    __tablename__ = "consistency_check_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_consistency_checks_project"), nullable=False
    )
    workflow_run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reports: Mapped[list[dict[str, object]]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_consistency_checks_scope", "workspace_id", "project_id", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class FindingRow(Base):
    __tablename__ = "consistency_findings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    check_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("consistency_check_runs.id", name="fk_consistency_findings_check"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    message_code: Mapped[str] = mapped_column(String(100), nullable=False)
    validator_key: Mapped[str] = mapped_column(String(100), nullable=False)
    validator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    workflow_run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    detected_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_consistency_findings_scope", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class ResolutionProposalRow(Base):
    __tablename__ = "consistency_resolution_proposals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_consistency_resolutions_project"), nullable=False
    )
    finding_ids: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    strategy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    target_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    expected_target_version: Mapped[int] = mapped_column(Integer, nullable=False)
    impact_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    applied_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    result_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("expected_target_version > 0", name="ck_consistency_target_version"),
        CheckConstraint("version > 0", name="ck_consistency_resolution_version"),
        Index("ix_consistency_resolutions_scope", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class EvidenceProjectionRow(Base):
    __tablename__ = "consistency_evidence_projection"

    workspace_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    reference: Mapped[str] = mapped_column(String(500), primary_key=True)
    owner: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revision_version: Mapped[int] = mapped_column(Integer, nullable=False)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("revision_version > 0", name="ck_consistency_projection_version"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryConsistencyRepository:
    def __init__(self) -> None:
        self.canon: dict[UUID, CanonEntry] = {}
        self.timeline: dict[UUID, TimelineEvent] = {}
        self.checks: dict[UUID, ConsistencyCheckRun] = {}
        self.findings: dict[UUID, Finding] = {}
        self.resolutions: dict[UUID, ResolutionProposal] = {}
        self.projections: dict[tuple[UUID, UUID], tuple[EvidenceProjection, ...]] = {}
        self.events: list[EventEnvelope] = []

    async def add_canon(self, entry: CanonEntry, event: EventEnvelope) -> CanonEntry:
        existing = self.canon.get(entry.id)
        if existing is not None:
            return existing
        self.canon[entry.id] = entry
        self.events.append(event)
        return entry

    async def add_timeline(self, event: TimelineEvent) -> TimelineEvent:
        existing = self.timeline.get(event.id)
        if existing is not None:
            return existing
        self.timeline[event.id] = event
        return event

    async def add_check(
        self,
        run: ConsistencyCheckRun,
        findings: tuple[Finding, ...],
        event: EventEnvelope,
    ) -> None:
        self.checks[run.id] = run
        self.findings.update((item.id, item) for item in findings)
        self.events.append(event)

    async def get_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> ConsistencyCheckRun | None:
        run = self.checks.get(run_id)
        if run is None or (run.workspace_id, run.project_id) != (workspace_id, project_id):
            return None
        return run

    async def findings_for_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> tuple[Finding, ...]:
        return tuple(
            item
            for item in self.findings.values()
            if (item.workspace_id, item.project_id, item.check_run_id)
            == (workspace_id, project_id, run_id)
        )

    async def add_resolution(
        self, proposal: ResolutionProposal, event: EventEnvelope
    ) -> ResolutionProposal:
        existing = self.resolutions.get(proposal.id)
        if existing is not None:
            return existing
        self.resolutions[proposal.id] = proposal
        self.events.append(event)
        return proposal

    async def get_resolution(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ResolutionProposal | None:
        proposal = self.resolutions.get(proposal_id)
        if proposal is None or (proposal.workspace_id, proposal.project_id) != (
            workspace_id,
            project_id,
        ):
            return None
        return proposal

    async def decide_resolution(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        decision: ResolutionDecision,
        expected_version: int,
        actor_id: UUID,
        event: EventEnvelope,
    ) -> ResolutionProposal:
        proposal = await self._require_resolution(workspace_id, project_id, proposal_id)
        if proposal.version != expected_version:
            raise ConcurrencyConflictError
        if proposal.status is not ResolutionStatus.PROPOSED:
            raise InvalidStateError("Only proposed resolutions can be decided.")
        decided = replace(
            proposal,
            status=(
                ResolutionStatus.APPROVED
                if decision is ResolutionDecision.APPROVE
                else ResolutionStatus.REJECTED
            ),
            approved_by=actor_id if decision is ResolutionDecision.APPROVE else None,
            updated_at=event.occurred_at,
            version=proposal.version + 1,
        )
        self.resolutions[proposal.id] = decided
        self.events.append(event)
        return decided

    async def claim_resolution(
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        actor_id: UUID,
    ) -> ResolutionProposal:
        proposal = await self._require_resolution(workspace_id, project_id, proposal_id)
        if proposal.version != expected_version:
            raise ConcurrencyConflictError
        if proposal.status is not ResolutionStatus.APPROVED:
            raise InvalidStateError("Only approved resolutions can be claimed.")
        claimed = replace(
            proposal,
            status=ResolutionStatus.APPLYING,
            applied_by=actor_id,
            version=proposal.version + 1,
        )
        self.resolutions[proposal.id] = claimed
        return claimed

    async def finish_resolution(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        result: AppliedRevision,
        event: EventEnvelope,
    ) -> ResolutionProposal:
        proposal = await self._require_resolution(workspace_id, project_id, proposal_id)
        if proposal.version != expected_version:
            raise ConcurrencyConflictError
        if proposal.status is not ResolutionStatus.APPLYING:
            raise InvalidStateError("Only a claimed resolution can finish.")
        applied = replace(
            proposal,
            status=ResolutionStatus.APPLIED,
            result=result,
            updated_at=event.occurred_at,
            version=proposal.version + 1,
        )
        self.resolutions[proposal.id] = applied
        for finding_id in proposal.finding_ids:
            finding = self.findings[finding_id]
            self.findings[finding_id] = replace(finding, status=FindingStatus.RESOLVED)
        self.events.append(event)
        return applied

    async def findings_by_ids(
        self, workspace_id: UUID, project_id: UUID, finding_ids: tuple[UUID, ...]
    ) -> tuple[Finding, ...]:
        return tuple(
            item
            for identifier in finding_ids
            if (item := self.findings.get(identifier)) is not None
            and (item.workspace_id, item.project_id) == (workspace_id, project_id)
        )

    async def replace_projection(
        self,
        workspace_id: UUID,
        project_id: UUID,
        entries: tuple[EvidenceProjection, ...],
    ) -> None:
        self.projections[(workspace_id, project_id)] = entries

    async def read_projection(
        self, workspace_id: UUID, project_id: UUID
    ) -> tuple[EvidenceProjection, ...]:
        return self.projections.get((workspace_id, project_id), ())

    async def _require_resolution(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ResolutionProposal:
        proposal = await self.get_resolution(workspace_id, project_id, proposal_id)
        if proposal is None:
            raise ScopeViolationError
        return proposal


class SqlAlchemyConsistencyRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add_canon(self, entry: CanonEntry, event: EventEnvelope) -> CanonEntry:
        async with self._sessions.begin() as session:
            existing = await session.get(CanonEntryRow, entry.id)
            if existing is not None:
                return _canon(existing)
            session.add(_canon_row(entry))
            await SqlAlchemyOutboxWriter(session).append(event)
        return entry

    async def add_timeline(self, event: TimelineEvent) -> TimelineEvent:
        async with self._sessions.begin() as session:
            existing = await session.get(TimelineEventRow, event.id)
            if existing is not None:
                return _timeline(existing)
            session.add(_timeline_row(event))
        return event

    async def add_check(
        self,
        run: ConsistencyCheckRun,
        findings: tuple[Finding, ...],
        event: EventEnvelope,
    ) -> None:
        async with self._sessions.begin() as session:
            session.add(_check_row(run))
            session.add_all(_finding_row(item) for item in findings)
            await SqlAlchemyOutboxWriter(session).append(event)

    async def get_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> ConsistencyCheckRun | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ConsistencyCheckRunRow).where(
                    ConsistencyCheckRunRow.workspace_id == workspace_id,
                    ConsistencyCheckRunRow.project_id == project_id,
                    ConsistencyCheckRunRow.id == run_id,
                )
            )
        return None if row is None else _check(row)

    async def findings_for_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> tuple[Finding, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(FindingRow)
                    .where(
                        FindingRow.workspace_id == workspace_id,
                        FindingRow.project_id == project_id,
                        FindingRow.check_run_id == run_id,
                    )
                    .order_by(FindingRow.detected_at, FindingRow.id)
                )
            ).all()
        return tuple(_finding(row) for row in rows)

    async def add_resolution(
        self, proposal: ResolutionProposal, event: EventEnvelope
    ) -> ResolutionProposal:
        async with self._sessions.begin() as session:
            existing = await session.get(ResolutionProposalRow, proposal.id)
            if existing is not None:
                return _resolution(existing)
            session.add(_resolution_row(proposal))
            await SqlAlchemyOutboxWriter(session).append(event)
        return proposal

    async def get_resolution(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ResolutionProposal | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ResolutionProposalRow).where(
                    ResolutionProposalRow.workspace_id == workspace_id,
                    ResolutionProposalRow.project_id == project_id,
                    ResolutionProposalRow.id == proposal_id,
                )
            )
        return None if row is None else _resolution(row)

    async def decide_resolution(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        decision: ResolutionDecision,
        expected_version: int,
        actor_id: UUID,
        event: EventEnvelope,
    ) -> ResolutionProposal:
        async with self._sessions.begin() as session:
            row = await _locked_resolution(session, workspace_id, project_id, proposal_id)
            if row.version != expected_version:
                raise ConcurrencyConflictError
            if row.status != ResolutionStatus.PROPOSED.value:
                raise InvalidStateError("Only proposed resolutions can be decided.")
            row.status = (
                ResolutionStatus.APPROVED.value
                if decision is ResolutionDecision.APPROVE
                else ResolutionStatus.REJECTED.value
            )
            row.approved_by = actor_id if decision is ResolutionDecision.APPROVE else None
            row.updated_at = event.occurred_at
            row.version += 1
            await SqlAlchemyOutboxWriter(session).append(event)
            await session.flush()
            return _resolution(row)

    async def claim_resolution(
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        actor_id: UUID,
    ) -> ResolutionProposal:
        async with self._sessions.begin() as session:
            row = await _locked_resolution(session, workspace_id, project_id, proposal_id)
            if row.version != expected_version:
                raise ConcurrencyConflictError
            if row.status != ResolutionStatus.APPROVED.value:
                raise InvalidStateError("Only approved resolutions can be claimed.")
            row.status = ResolutionStatus.APPLYING.value
            row.applied_by = actor_id
            row.version += 1
            await session.flush()
            return _resolution(row)

    async def finish_resolution(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        result: AppliedRevision,
        event: EventEnvelope,
    ) -> ResolutionProposal:
        async with self._sessions.begin() as session:
            row = await _locked_resolution(session, workspace_id, project_id, proposal_id)
            if row.version != expected_version:
                raise ConcurrencyConflictError
            if row.status != ResolutionStatus.APPLYING.value:
                raise InvalidStateError("Only a claimed resolution can finish.")
            row.status = ResolutionStatus.APPLIED.value
            row.result_reference = result.reference
            row.result_version = result.version
            row.updated_at = event.occurred_at
            row.version += 1
            finding_rows = (
                await session.scalars(
                    select(FindingRow).where(
                        FindingRow.workspace_id == workspace_id,
                        FindingRow.project_id == project_id,
                        FindingRow.id.in_([UUID(item) for item in row.finding_ids]),
                    )
                )
            ).all()
            for finding in finding_rows:
                finding.status = FindingStatus.RESOLVED.value
            await SqlAlchemyOutboxWriter(session).append(event)
            await session.flush()
            return _resolution(row)

    async def findings_by_ids(
        self, workspace_id: UUID, project_id: UUID, finding_ids: tuple[UUID, ...]
    ) -> tuple[Finding, ...]:
        if not finding_ids:
            return ()
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(FindingRow).where(
                        FindingRow.workspace_id == workspace_id,
                        FindingRow.project_id == project_id,
                        FindingRow.id.in_(finding_ids),
                    )
                )
            ).all()
        by_id = {row.id: _finding(row) for row in rows}
        return tuple(by_id[item] for item in finding_ids if item in by_id)

    async def replace_projection(
        self,
        workspace_id: UUID,
        project_id: UUID,
        entries: tuple[EvidenceProjection, ...],
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(EvidenceProjectionRow).where(
                    EvidenceProjectionRow.workspace_id == workspace_id,
                    EvidenceProjectionRow.project_id == project_id,
                )
            )
            session.add_all(_projection_row(workspace_id, project_id, item) for item in entries)

    async def read_projection(
        self, workspace_id: UUID, project_id: UUID
    ) -> tuple[EvidenceProjection, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(EvidenceProjectionRow)
                    .where(
                        EvidenceProjectionRow.workspace_id == workspace_id,
                        EvidenceProjectionRow.project_id == project_id,
                    )
                    .order_by(EvidenceProjectionRow.reference)
                )
            ).all()
        return tuple(_projection(row) for row in rows)


async def _locked_resolution(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, proposal_id: UUID
) -> ResolutionProposalRow:
    row = cast(
        "ResolutionProposalRow | None",
        await session.scalar(
            select(ResolutionProposalRow)
            .where(
                ResolutionProposalRow.workspace_id == workspace_id,
                ResolutionProposalRow.project_id == project_id,
                ResolutionProposalRow.id == proposal_id,
            )
            .with_for_update()
        ),
    )
    if row is None:
        raise ScopeViolationError
    return row


def _canon_row(item: CanonEntry) -> CanonEntryRow:
    return CanonEntryRow(**{field: getattr(item, field) for field in item.__dataclass_fields__})


def _canon(row: CanonEntryRow) -> CanonEntry:
    return CanonEntry(
        row.id,
        row.logical_id,
        row.workspace_id,
        row.project_id,
        row.canon_key,
        CanonLevel(row.level),
        row.entry_version,
        row.valid_from,
        row.valid_until,
        row.source_reference,
        CanonStatus(row.status),
        row.created_by,
        row.created_at,
    )


def _timeline_row(item: TimelineEvent) -> TimelineEventRow:
    return TimelineEventRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        event_reference=item.event_reference,
        occurred_at=item.occurred_at,
        sequence=item.sequence,
        character_state_references=list(item.character_state_references),
        world_state_references=list(item.world_state_references),
        source_version=item.source_version,
    )


def _timeline(row: TimelineEventRow) -> TimelineEvent:
    return TimelineEvent(
        row.id,
        row.workspace_id,
        row.project_id,
        row.event_reference,
        row.occurred_at,
        row.sequence,
        tuple(row.character_state_references),
        tuple(row.world_state_references),
        row.source_version,
    )


def _report_json(report: ValidatorReport) -> dict[str, object]:
    return {
        "validator_key": report.validator_key,
        "validator_version": report.validator_version,
        "status": report.status.value,
        "error_code": report.error_code,
        "findings": [
            {
                "finding_type": item.finding_type.value,
                "severity": item.severity.value,
                "evidence_references": list(item.evidence_references),
                "message_code": item.message_code,
            }
            for item in report.findings
        ],
    }


def _report(value: dict[str, object]) -> ValidatorReport:
    raw_findings = value["findings"]
    if not isinstance(raw_findings, list):
        raise ValueError("stored validator findings must be a list")
    findings = tuple(
        FindingDraft(
            FindingType(str(item["finding_type"])),
            FindingSeverity(str(item["severity"])),
            tuple(str(value) for value in item["evidence_references"]),
            str(item["message_code"]),
        )
        for item in raw_findings
    )
    error_code = value["error_code"]
    return ValidatorReport(
        str(value["validator_key"]),
        str(value["validator_version"]),
        ValidationStatus(str(value["status"])),
        findings,
        None if error_code is None else str(error_code),
    )


def _check_row(item: ConsistencyCheckRun) -> ConsistencyCheckRunRow:
    return ConsistencyCheckRunRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        workflow_run_id=item.workflow_run_id,
        requested_by=item.requested_by,
        status=item.status.value,
        reports=[_report_json(report) for report in item.reports],
        created_at=item.created_at,
    )


def _check(row: ConsistencyCheckRunRow) -> ConsistencyCheckRun:
    return ConsistencyCheckRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.workflow_run_id,
        row.requested_by,
        ValidationStatus(row.status),
        tuple(_report(item) for item in row.reports),
        row.created_at,
    )


def _finding_row(item: Finding) -> FindingRow:
    return FindingRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        check_run_id=item.check_run_id,
        finding_type=item.finding_type.value,
        severity=item.severity.value,
        evidence_references=list(item.evidence_references),
        message_code=item.message_code,
        validator_key=item.validator_key,
        validator_version=item.validator_version,
        status=item.status.value,
        workflow_run_id=item.workflow_run_id,
        detected_by=item.detected_by,
        detected_at=item.detected_at,
    )


def _finding(row: FindingRow) -> Finding:
    return Finding(
        row.id,
        row.workspace_id,
        row.project_id,
        row.check_run_id,
        FindingType(row.finding_type),
        FindingSeverity(row.severity),
        tuple(row.evidence_references),
        row.message_code,
        row.validator_key,
        row.validator_version,
        FindingStatus(row.status),
        row.workflow_run_id,
        row.detected_by,
        row.detected_at,
    )


def _resolution_row(item: ResolutionProposal) -> ResolutionProposalRow:
    return ResolutionProposalRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        finding_ids=[str(value) for value in item.finding_ids],
        strategy_code=item.strategy_code,
        target_reference=item.target.reference,
        expected_target_version=item.target.expected_version,
        impact_references=list(item.impact_references),
        requires_approval=item.requires_approval,
        status=item.status.value,
        requested_by=item.requested_by,
        workflow_run_id=item.workflow_run_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        approved_by=item.approved_by,
        applied_by=item.applied_by,
        result_reference=None if item.result is None else item.result.reference,
        result_version=None if item.result is None else item.result.version,
        version=item.version,
    )


def _resolution(row: ResolutionProposalRow) -> ResolutionProposal:
    result = (
        None
        if row.result_reference is None or row.result_version is None
        else AppliedRevision(row.result_reference, row.result_version)
    )
    return ResolutionProposal(
        row.id,
        row.workspace_id,
        row.project_id,
        tuple(UUID(value) for value in row.finding_ids),
        row.strategy_code,
        FactTarget(row.target_reference, row.expected_target_version),
        tuple(row.impact_references),
        row.requires_approval,
        ResolutionStatus(row.status),
        row.requested_by,
        row.workflow_run_id,
        row.created_at,
        row.updated_at,
        row.approved_by,
        row.applied_by,
        result,
        row.version,
    )


def _projection_row(
    workspace_id: UUID, project_id: UUID, item: EvidenceProjection
) -> EvidenceProjectionRow:
    return EvidenceProjectionRow(
        workspace_id=workspace_id,
        project_id=project_id,
        reference=item.reference,
        owner=item.owner,
        entity_id=item.entity_id,
        revision_id=item.revision_id,
        revision_version=item.revision_version,
        projected_at=item.projected_at,
    )


def _projection(row: EvidenceProjectionRow) -> EvidenceProjection:
    return EvidenceProjection(
        row.reference,
        row.owner,
        row.entity_id,
        row.revision_id,
        row.revision_version,
        row.projected_at,
    )


MODEL_REGISTRY = (
    CanonEntryRow,
    TimelineEventRow,
    ConsistencyCheckRunRow,
    FindingRow,
    ResolutionProposalRow,
    EvidenceProjectionRow,
)
