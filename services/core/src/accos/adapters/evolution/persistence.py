"""Optimistic in-memory and PostgreSQL evolution memory."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves annotations at runtime.
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import ConcurrencyConflictError, ScopeViolationError
from accos.modules.evolution.domain import (
    ChangeAction,
    EvolutionAuditEntry,
    EvolutionState,
    ImprovementProposal,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope


class ImprovementProposalRow(Base):
    __tablename__ = "evolution_improvement_proposals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_evolution_proposals_project"), nullable=False
    )
    diagnostic_finding_ids: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    input_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    algorithm_versions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str | None] = mapped_column(String(40), nullable=True)
    change_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approval_policy_ref: Mapped[str] = mapped_column(
        String(100), nullable=False, default="legacy_dual_control"
    )
    safety_policy_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safety_rule_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    simulation_evidence: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    evaluation_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    rollback_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_evolution_proposals_scope", "workspace_id", "project_id", "state"),
        {"schema": SCHEMA_NAME},
    )


class EvolutionAuditRow(Base):
    __tablename__ = "evolution_audit_entries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    proposal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evolution_improvement_proposals.id", name="fk_evolution_audit_proposal"),
        nullable=False,
    )
    from_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_state: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    algorithm_versions: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    evidence_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    rollback_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_evolution_audit_scope", "workspace_id", "project_id", "proposal_id", "occurred_at"
        ),
        {"schema": SCHEMA_NAME},
    )


class InMemoryEvolutionMemory:
    def __init__(self) -> None:
        self.proposals: dict[UUID, ImprovementProposal] = {}
        self.audit: list[EvolutionAuditEntry] = []
        self.events: list[EventEnvelope] = []

    async def add(
        self,
        proposal: ImprovementProposal,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal:
        existing = self.proposals.get(proposal.id)
        if existing is not None:
            return existing
        self.proposals[proposal.id] = proposal
        self.audit.append(audit)
        self.events.append(event)
        return proposal

    async def get(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ImprovementProposal | None:
        proposal = self.proposals.get(proposal_id)
        if proposal is None or (proposal.workspace_id, proposal.project_id) != (
            workspace_id,
            project_id,
        ):
            return None
        return proposal

    async def transition(
        self,
        proposal: ImprovementProposal,
        expected_version: int,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal:
        existing = self.proposals.get(proposal.id)
        if existing is None:
            raise ScopeViolationError
        if existing.version != expected_version or proposal.version != expected_version + 1:
            raise ConcurrencyConflictError
        self.proposals[proposal.id] = proposal
        self.audit.append(audit)
        self.events.append(event)
        return proposal


class SqlAlchemyEvolutionMemory:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add(
        self,
        proposal: ImprovementProposal,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal:
        async with self._sessions.begin() as session:
            existing = await session.get(ImprovementProposalRow, proposal.id)
            if existing is not None:
                return _proposal(existing)
            session.add(_proposal_row(proposal))
            await session.flush()
            session.add(_audit_row(audit))
            await SqlAlchemyOutboxWriter(session).append(event)
        return proposal

    async def get(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ImprovementProposal | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ImprovementProposalRow).where(
                    ImprovementProposalRow.workspace_id == workspace_id,
                    ImprovementProposalRow.project_id == project_id,
                    ImprovementProposalRow.id == proposal_id,
                )
            )
        return None if row is None else _proposal(row)

    async def transition(
        self,
        proposal: ImprovementProposal,
        expected_version: int,
        audit: EvolutionAuditEntry,
        event: EventEnvelope,
    ) -> ImprovementProposal:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(ImprovementProposalRow)
                .where(
                    ImprovementProposalRow.workspace_id == proposal.workspace_id,
                    ImprovementProposalRow.project_id == proposal.project_id,
                    ImprovementProposalRow.id == proposal.id,
                )
                .with_for_update()
            )
            if row is None:
                raise ScopeViolationError
            if row.version != expected_version or proposal.version != expected_version + 1:
                raise ConcurrencyConflictError
            _update_proposal_row(row, proposal)
            session.add(_audit_row(audit))
            await SqlAlchemyOutboxWriter(session).append(event)
        return proposal


def _proposal_row(item: ImprovementProposal) -> ImprovementProposalRow:
    return ImprovementProposalRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        diagnostic_finding_ids=[str(value) for value in item.diagnostic_finding_ids],
        input_references=list(item.input_references),
        algorithm_versions=list(item.algorithm_versions),
        state=item.state.value,
        requested_by=item.requested_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
        action=None if item.action is None else item.action.value,
        change_reference=item.change_reference,
        safety_policy_version=item.safety_policy_version,
        safety_rule_code=item.safety_rule_code,
        simulation_evidence=list(item.simulation_evidence),
        evaluation_code=item.evaluation_code,
        approved_by=item.approved_by,
        rollback_reference=item.rollback_reference,
        version=item.version,
        approval_policy_ref=item.approval_policy_ref,
    )


def _update_proposal_row(row: ImprovementProposalRow, item: ImprovementProposal) -> None:
    fresh = _proposal_row(item)
    for attribute in (
        "diagnostic_finding_ids",
        "input_references",
        "algorithm_versions",
        "state",
        "updated_at",
        "action",
        "change_reference",
        "approval_policy_ref",
        "safety_policy_version",
        "safety_rule_code",
        "simulation_evidence",
        "evaluation_code",
        "approved_by",
        "rollback_reference",
        "version",
    ):
        setattr(row, attribute, getattr(fresh, attribute))


def _proposal(row: ImprovementProposalRow) -> ImprovementProposal:
    return ImprovementProposal(
        row.id,
        row.workspace_id,
        row.project_id,
        tuple(UUID(value) for value in row.diagnostic_finding_ids),
        tuple(row.input_references),
        tuple(row.algorithm_versions),
        EvolutionState(row.state),
        row.requested_by,
        row.created_at,
        row.updated_at,
        None if row.action is None else ChangeAction(row.action),
        row.change_reference,
        row.safety_policy_version,
        row.safety_rule_code,
        tuple(row.simulation_evidence),
        row.evaluation_code,
        row.approved_by,
        row.rollback_reference,
        row.version,
        row.approval_policy_ref,
    )


def _audit_row(item: EvolutionAuditEntry) -> EvolutionAuditRow:
    return EvolutionAuditRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        proposal_id=item.proposal_id,
        from_state=None if item.from_state is None else item.from_state.value,
        to_state=item.to_state.value,
        actor_id=item.actor_id,
        algorithm_versions=list(item.algorithm_versions),
        evidence_references=list(item.evidence_references),
        rollback_reference=item.rollback_reference,
        reason_code=item.reason_code,
        occurred_at=item.occurred_at,
    )


MODEL_REGISTRY = (ImprovementProposalRow, EvolutionAuditRow)
