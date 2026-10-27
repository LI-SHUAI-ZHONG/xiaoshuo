"""Shared authorization and state-transition mechanics for creative owners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError, ScopeViolationError
from accos.kernel.events import EventEnvelope
from accos.modules.creative.common import (
    CreativeContainer,
    CreativeDecision,
    CreativeOwner,
    CreativeRecord,
    CreativeRecordStatus,
    CreativeReference,
)
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.projects.public import ProjectStatus

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.creative.ports import CreativeRepository
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.projects.public import ProjectRepository


class CreativeAccess:
    """Enforce project scope and archived-write rules through public contracts."""

    def __init__(
        self,
        projects: ProjectRepository,
        authorizer: AuthorizationService,
    ) -> None:
        self._projects = projects
        self._authorizer = authorizer

    async def authorize(
        self,
        context: SecurityContext,
        project_id: UUID,
        permission: Permission,
    ) -> None:
        request = AuthorizationRequest(
            context,
            permission,
            ResourceScope(context.workspace_id, "project", str(project_id), project_id),
        )
        project = await self._projects.get(context.workspace_id, project_id)
        if project is None:
            await self._authorizer.reject(
                request, ScopeViolationError(), reason_code="project_unavailable"
            )
        if permission is Permission.PROJECT_WRITE and project.status is ProjectStatus.ARCHIVED:
            raise InvalidStateError("Archived projects cannot change creative state.")
        await self._authorizer.authorize(request)


class CreativeApplication:
    """Internal application helper; public services permanently bind an owner."""

    def __init__(
        self,
        repository: CreativeRepository,
        access: CreativeAccess,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._access = access
        self._clock = clock

    async def create_container(  # noqa: PLR0913, PLR0917
        self,
        context: SecurityContext,
        project_id: UUID,
        container_type: type[CreativeContainer],
        label: str,
        references: tuple[CreativeReference, ...],
        event_schema: str,
    ) -> CreativeContainer:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        now = self._clock.now()
        container = container_type(
            id=uuid4(),
            workspace_id=context.workspace_id,
            project_id=project_id,
            label=label,
            references=references,
            created_by=context.actor_id,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.add_container(
            container,
            _event(context, project_id, container.id, event_schema, now),
        )

    async def get_container(
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        container = await self._repository.get_container(
            context.workspace_id, project_id, owner, container_id
        )
        if container is None:
            raise ScopeViolationError
        return container

    async def propose(  # noqa: PLR0913
        self,
        context: SecurityContext,
        project_id: UUID,
        aggregate_id: UUID,
        record_type: type[CreativeRecord],
        *,
        logical_id: UUID | None,
        record_version: int,
        references: tuple[CreativeReference, ...],
        source_reference: str | None,
        sequence: int | None,
        event_schema: str,
        causation_id: UUID | None = None,
        source_event_id: UUID | None = None,
    ) -> tuple[CreativeRecord, bool]:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        container = await self._repository.get_container(
            context.workspace_id, project_id, record_type.owner, aggregate_id
        )
        if container is None:
            raise ScopeViolationError
        now = self._clock.now()
        record = record_type(
            id=uuid4(),
            logical_id=uuid4() if logical_id is None else logical_id,
            record_version=record_version,
            workspace_id=context.workspace_id,
            project_id=project_id,
            aggregate_id=aggregate_id,
            status=CreativeRecordStatus.PROPOSAL,
            current=False,
            references=references,
            source_reference=source_reference,
            sequence=sequence,
            created_by=context.actor_id,
            created_at=now,
            causation_id=causation_id,
            source_event_id=source_event_id,
        )
        payload: dict[str, object] = {
            "schema": event_schema,
            "entity_type": record.entity_type,
            "record_version": record.record_version,
        }
        if causation_id is not None:
            payload["causation_id"] = str(causation_id)
            payload["source_event_id"] = str(source_event_id)
        return await self._repository.add_proposal(
            record,
            _event(context, project_id, aggregate_id, event_schema, now, payload),
        )

    async def get_record(
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
    ) -> CreativeRecord:
        await self._access.authorize(context, project_id, Permission.PROJECT_READ)
        record = await self._repository.get_record(
            context.workspace_id, project_id, owner, record_id
        )
        if record is None:
            raise ScopeViolationError
        return record

    async def decide(  # noqa: PLR0913, PLR0917
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
        decision: CreativeDecision,
        expected_container_version: int,
        event_schema: str,
    ) -> CreativeRecord:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)
        record = await self._repository.get_record(
            context.workspace_id, project_id, owner, record_id
        )
        if record is None:
            raise ScopeViolationError
        now = self._clock.now()
        return await self._repository.decide_proposal(
            context.workspace_id,
            project_id,
            owner,
            record_id,
            decision=decision,
            expected_container_version=expected_container_version,
            decided_by=context.actor_id,
            decided_at=now,
            event=_event(
                context,
                project_id,
                record.aggregate_id,
                event_schema,
                now,
                {"schema": event_schema, "decision": decision.value},
            ),
        )

    async def authorize_write(self, context: SecurityContext, project_id: UUID) -> None:
        await self._access.authorize(context, project_id, Permission.PROJECT_WRITE)


class CreativeCatalog:
    """Read-only resolver used by Workflow through a public creative reference."""

    def __init__(self, application: CreativeApplication) -> None:
        self._application = application

    async def resolve(
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        container_id: UUID,
    ) -> CreativeContainer:
        return await self._application.get_container(context, project_id, owner, container_id)


@dataclass(frozen=True, slots=True)
class ApplyCreativeResolutionCommand:
    """Metadata-only request from an approved external resolution."""

    project_id: UUID
    owner: CreativeOwner
    current_record_id: UUID
    expected_record_version: int
    resolution_reference: str


class CreativeRevisionConflictError(ConcurrencyConflictError):
    """Creative owner conflict with the safe current record version."""

    def __init__(self, current_version: int) -> None:
        super().__init__()
        self.current_version = current_version
        self.details["current_version"] = current_version


class CreativeRevisionService:
    """Public owner use case used by Consistency instead of private-table writes."""

    def __init__(self, application: CreativeApplication) -> None:
        self._application = application

    async def current_version(
        self,
        context: SecurityContext,
        project_id: UUID,
        owner: CreativeOwner,
        record_id: UUID,
    ) -> int:
        record = await self._application.get_record(context, project_id, owner, record_id)
        current = await self._application._repository.get_current_record(  # noqa: SLF001
            context.workspace_id, project_id, owner, record.logical_id
        )
        if current is None:
            raise InvalidStateError("The creative fact has no current revision.")
        return current.record_version

    async def apply_resolution(
        self, context: SecurityContext, command: ApplyCreativeResolutionCommand
    ) -> CreativeRecord:
        await self._application.authorize_write(context, command.project_id)
        source = await self._application.get_record(
            context, command.project_id, command.owner, command.current_record_id
        )
        current = await self._application._repository.get_current_record(  # noqa: SLF001
            context.workspace_id, command.project_id, command.owner, source.logical_id
        )
        if current is None:
            raise InvalidStateError("The creative fact has no current revision.")
        if current.id != source.id or current.record_version != command.expected_record_version:
            raise CreativeRevisionConflictError(current.record_version)
        container = await self._application.get_container(
            context, command.project_id, command.owner, current.aggregate_id
        )
        proposed, _created = await self._application.propose(
            context,
            command.project_id,
            current.aggregate_id,
            type(current),
            logical_id=current.logical_id,
            record_version=current.record_version + 1,
            references=current.references,
            source_reference=command.resolution_reference,
            sequence=current.sequence,
            event_schema=f"creative.{command.owner.value}.resolution-proposed.v1",
        )
        try:
            return await self._application.decide(
                context,
                command.project_id,
                command.owner,
                proposed.id,
                CreativeDecision.APPROVE,
                container.version,
                f"creative.{command.owner.value}.resolution-applied.v1",
            )
        except ConcurrencyConflictError as error:
            latest = await self._application._repository.get_current_record(  # noqa: SLF001
                context.workspace_id, command.project_id, command.owner, current.logical_id
            )
            if latest is None:
                raise InvalidStateError("The creative fact has no current revision.") from error
            raise CreativeRevisionConflictError(latest.record_version) from error


def _event(  # noqa: PLR0913, PLR0917
    context: SecurityContext,
    project_id: UUID,
    aggregate_id: UUID,
    event_schema: str,
    occurred_at: datetime,
    payload: dict[str, object] | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        uuid4(),
        context.workspace_id,
        project_id,
        aggregate_id,
        event_schema.removesuffix(".v1"),
        1,
        {"schema": event_schema} if payload is None else payload,
        occurred_at,
    )
