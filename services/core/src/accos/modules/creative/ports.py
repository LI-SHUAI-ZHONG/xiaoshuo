"""Repository ports for the four creative owners."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.events import EventEnvelope
    from accos.modules.creative.common import (
        CreativeContainer,
        CreativeDecision,
        CreativeOwner,
        CreativeRecord,
    )


class CreativeRepository(Protocol):
    """Shared storage shape whose owner discriminator is enforced in every call."""

    async def add_container(
        self, container: CreativeContainer, event: EventEnvelope
    ) -> CreativeContainer: ...

    async def get_container(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer | None: ...

    async def add_proposal(
        self, record: CreativeRecord, event: EventEnvelope
    ) -> tuple[CreativeRecord, bool]: ...

    async def get_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
    ) -> CreativeRecord | None: ...

    async def get_current_record(
        self,
        workspace_id: UUID,
        project_id: UUID,
        owner: CreativeOwner,
        logical_id: UUID,
    ) -> CreativeRecord | None: ...

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
    ) -> CreativeRecord: ...


class NovelRepository(CreativeRepository, Protocol):
    """Novel-owned storage port."""


class WorldRepository(CreativeRepository, Protocol):
    """World-owned storage port."""


class CharacterRepository(CreativeRepository, Protocol):
    """Character-owned storage port."""


class CreatorRepository(CreativeRepository, Protocol):
    """Creator-owned storage port."""
