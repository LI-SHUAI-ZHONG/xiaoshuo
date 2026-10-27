"""Creator-owned persistence adapter for authorized Feedback preference signals."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import uuid4

from accos.kernel.events import EventEnvelope
from accos.modules.creative.extensions import ExtensionResult, ExtensionStatus

if TYPE_CHECKING:
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.creative.creator import CreatorProfile, PreferenceSignal
    from accos.modules.creative.ports import CreativeRepository


class RepositoryPreferenceSignalIngestPort:
    """Persist inert Creator proposals without importing the Feedback repository."""

    def __init__(self, repository: CreativeRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def ingest(self, context: SecurityContext, signal: PreferenceSignal) -> ExtensionResult:
        profile = await self._repository.get_container(
            signal.workspace_id, signal.project_id, signal.owner, signal.aggregate_id
        )
        if (
            signal.workspace_id != context.workspace_id
            or signal.created_by != context.actor_id
            or profile is None
            or cast("CreatorProfile", profile).creator_id != context.actor_id
        ):
            raise ValueError("preference signal is not authorized for the Creator profile")
        now = self._clock.now()
        stored, _created = await self._repository.add_proposal(
            signal,
            EventEnvelope(
                uuid4(),
                signal.workspace_id,
                signal.project_id,
                signal.aggregate_id,
                "creative.creator.preference-signal-ingested",
                1,
                {
                    "schema": "creative.creator.preference-signal-ingested.v1",
                    "source_event_id": str(signal.source_event_id),
                },
                now,
            ),
        )
        return ExtensionResult(ExtensionStatus.PROPOSED, stored.reference)
