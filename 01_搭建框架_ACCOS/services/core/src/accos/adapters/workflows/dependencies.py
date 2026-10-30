"""Project-content dependency resolution for frozen Workflow inputs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from accos.kernel.errors import ResourceNotFoundError
from accos.modules.workflows.domain import (
    InputResolutionStatus,
    RequirementFreshness,
    ResolvedInput,
    StageRequirement,
)

if TYPE_CHECKING:
    from accos.kernel.security import SecurityContext
    from accos.modules.projects.content_ports import ContentRepository
    from accos.modules.projects.ports import ProjectRepository

_REFERENCE_PREFIX = "content-revision://"
_REFERENCE_PARTS = 2


class ProjectContentDependencyResolver:
    """Resolve explicit immutable project revisions without loading their bodies."""

    def __init__(
        self,
        projects: ProjectRepository,
        content: ContentRepository,
    ) -> None:
        self._projects = projects
        self._content = content

    async def resolve(
        self,
        context: SecurityContext,
        project_id: UUID,
        requirements: tuple[StageRequirement, ...],
        candidate_references: dict[str, str],
        *,
        now: datetime,
    ) -> tuple[ResolvedInput, ...]:
        """Return one fail-closed result per requirement in declaration order."""
        if context.project_id is not None and context.project_id != project_id:
            return tuple(
                _unresolved(requirement, InputResolutionStatus.UNAUTHORIZED, context, now)
                for requirement in requirements
            )
        results: list[ResolvedInput] = []
        for requirement in requirements:
            reference = candidate_references.get(requirement.key)
            identity = _parse_reference(reference)
            if identity is None:
                results.append(
                    _unresolved(requirement, InputResolutionStatus.MISSING, context, now)
                )
                continue
            artifact_id, revision_id = identity
            artifact = await self._projects.get_artifact(
                context.workspace_id,
                project_id,
                artifact_id,
            )
            if artifact is None or artifact.artifact_type.value != requirement.artifact_type:
                results.append(
                    _unresolved(requirement, InputResolutionStatus.MISSING, context, now)
                )
                continue
            try:
                revision = await self._content.revision(
                    context.workspace_id,
                    project_id,
                    artifact_id,
                    revision_id,
                )
            except ResourceNotFoundError:
                results.append(
                    _unresolved(requirement, InputResolutionStatus.MISSING, context, now)
                )
                continue
            status = _revision_status(requirement, artifact.current_revision, revision, now)
            if status is not InputResolutionStatus.READY:
                results.append(_unresolved(requirement, status, context, now))
                continue
            results.append(
                ResolvedInput(
                    requirement.key,
                    reference,
                    str(revision.id),
                    revision.content_hash,
                    revision.editor_schema_version,
                    InputResolutionStatus.READY,
                    now,
                    context.policy_version,
                    f"workspace-consent:{context.policy_version}",
                )
            )
        return tuple(results)


def _parse_reference(value: str | None) -> tuple[UUID, UUID] | None:
    if value is None or not value.startswith(_REFERENCE_PREFIX):
        return None
    parts = value.removeprefix(_REFERENCE_PREFIX).split("/")
    if len(parts) != _REFERENCE_PARTS:
        return None
    try:
        return UUID(parts[0]), UUID(parts[1])
    except ValueError:
        return None


def _revision_status(
    requirement: StageRequirement,
    current_revision: int,
    revision: object,
    now: datetime,
) -> InputResolutionStatus:
    content_status = getattr(revision, "content_status", None)
    content_hash = getattr(revision, "content_hash", None)
    schema_version = getattr(revision, "editor_schema_version", None)
    revision_number = getattr(revision, "revision_number", None)
    branch_id = getattr(revision, "branch_id", None)
    created_at = getattr(revision, "created_at", None)
    if requirement.accepted_required and content_status != "available":
        return InputResolutionStatus.NOT_ACCEPTED
    if content_hash is None or schema_version is None or schema_version < requirement.min_schema:
        return InputResolutionStatus.SCHEMA_INCOMPATIBLE
    if requirement.branch is not None and str(branch_id) != requirement.branch:
        return InputResolutionStatus.STALE
    if (
        requirement.freshness is RequirementFreshness.CURRENT
        and revision_number != current_revision
    ):
        return InputResolutionStatus.STALE
    if requirement.freshness is RequirementFreshness.MAX_AGE and (
        not isinstance(created_at, datetime)
        or requirement.max_age_seconds is None
        or (now - created_at).total_seconds() > requirement.max_age_seconds
    ):
        return InputResolutionStatus.STALE
    return InputResolutionStatus.READY


def _unresolved(
    requirement: StageRequirement,
    status: InputResolutionStatus,
    context: SecurityContext,
    now: datetime,
) -> ResolvedInput:
    return ResolvedInput(
        requirement.key,
        None,
        None,
        None,
        None,
        status,
        now,
        context.policy_version,
        f"workspace-consent:{context.policy_version}",
    )
