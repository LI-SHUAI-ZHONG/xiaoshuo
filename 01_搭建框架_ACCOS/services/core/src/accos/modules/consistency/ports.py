"""Ports for validators, persistence, fact application, and projection rebuilds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.kernel.security import SecurityContext
    from accos.modules.consistency.domain import (
        AppliedRevision,
        CanonEntry,
        ConsistencyCheckRun,
        EvidenceProjection,
        FactTarget,
        Finding,
        ResolutionDecision,
        ResolutionProposal,
        TimelineEvent,
        ValidationBundle,
        ValidatorReport,
    )


class ValidatorPort(Protocol):
    key: str
    version: str

    async def validate(self, evidence: ValidationBundle) -> ValidatorReport: ...


class ConsistencyRepository(Protocol):
    async def add_canon(self, entry: CanonEntry, event: EventEnvelope) -> CanonEntry: ...

    async def add_timeline(self, event: TimelineEvent) -> TimelineEvent: ...

    async def add_check(
        self,
        run: ConsistencyCheckRun,
        findings: tuple[Finding, ...],
        event: EventEnvelope,
    ) -> None: ...

    async def get_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> ConsistencyCheckRun | None: ...

    async def findings_for_check(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> tuple[Finding, ...]: ...

    async def add_resolution(
        self, proposal: ResolutionProposal, event: EventEnvelope
    ) -> ResolutionProposal: ...

    async def get_resolution(
        self, workspace_id: UUID, project_id: UUID, proposal_id: UUID
    ) -> ResolutionProposal | None: ...

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
    ) -> ResolutionProposal: ...

    async def claim_resolution(
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        actor_id: UUID,
    ) -> ResolutionProposal: ...

    async def finish_resolution(  # noqa: PLR0913
        self,
        workspace_id: UUID,
        project_id: UUID,
        proposal_id: UUID,
        *,
        expected_version: int,
        result: AppliedRevision,
        event: EventEnvelope,
    ) -> ResolutionProposal: ...

    async def findings_by_ids(
        self, workspace_id: UUID, project_id: UUID, finding_ids: tuple[UUID, ...]
    ) -> tuple[Finding, ...]: ...

    async def replace_projection(
        self,
        workspace_id: UUID,
        project_id: UUID,
        entries: tuple[EvidenceProjection, ...],
    ) -> None: ...

    async def read_projection(
        self, workspace_id: UUID, project_id: UUID
    ) -> tuple[EvidenceProjection, ...]: ...


class FactRevisionPort(Protocol):
    async def current_version(
        self, context: SecurityContext, project_id: UUID, target: FactTarget
    ) -> int: ...

    async def apply(
        self,
        context: SecurityContext,
        project_id: UUID,
        target: FactTarget,
        resolution_reference: str,
    ) -> AppliedRevision: ...


class AuthoritativeEvidenceReader(Protocol):
    async def read_project(
        self, context: SecurityContext, project_id: UUID
    ) -> tuple[EvidenceProjection, ...]: ...
