"""Adapter from consistency fact port to the public Creative revision use case."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from accos.modules.consistency.public import (
    AppliedRevision,
    FactTarget,
    TargetVersionConflictError,
)
from accos.modules.creative.public import (
    ApplyCreativeResolutionCommand,
    CreativeOwner,
    CreativeRevisionConflictError,
    CreativeRevisionService,
)

if TYPE_CHECKING:
    from accos.kernel.security import SecurityContext


class CreativeFactRevisionAdapter:
    """Call Creative's public application service; never import its persistence adapter."""

    def __init__(self, revisions: CreativeRevisionService) -> None:
        self._revisions = revisions

    async def current_version(
        self, context: SecurityContext, project_id: UUID, target: FactTarget
    ) -> int:
        owner, record_id = _target(target.reference)
        return await self._revisions.current_version(context, project_id, owner, record_id)

    async def apply(
        self,
        context: SecurityContext,
        project_id: UUID,
        target: FactTarget,
        resolution_reference: str,
    ) -> AppliedRevision:
        owner, record_id = _target(target.reference)
        try:
            revision = await self._revisions.apply_resolution(
                context,
                ApplyCreativeResolutionCommand(
                    project_id,
                    owner,
                    record_id,
                    target.expected_version,
                    resolution_reference,
                ),
            )
        except CreativeRevisionConflictError as error:
            raise TargetVersionConflictError(error.current_version) from error
        return AppliedRevision(revision.reference, revision.record_version)


def _target(reference: str) -> tuple[CreativeOwner, UUID]:
    try:
        owner_value, identifier = reference.removeprefix("creative-record://").split("/", 1)
        if not reference.startswith("creative-record://"):
            raise ValueError
        return CreativeOwner(owner_value), UUID(identifier)
    except ValueError as error:
        raise ValueError("resolution target must be a Creative record reference") from error
