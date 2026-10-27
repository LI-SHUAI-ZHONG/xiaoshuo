"""Bounded role-meeting plans materialized as ordinary acyclic Workflows."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from accos.kernel.errors import InvalidStateError
from accos.modules.agents.domain import RoleVersionStatus
from accos.modules.workflows.domain import (
    RetryPolicy,
    StepDefinition,
    StepKind,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.agents.ports import RoleRepository
    from accos.modules.workflows.application import WorkflowService
    from accos.modules.workflows.domain import WorkflowRun

_MEETING_NAMESPACE = UUID("a2800000-0000-4000-8000-000000000001")
_MAX_ROUNDS = 4
_MAX_PARTICIPANTS = 8
_MAX_CALLS = 24


@dataclass(frozen=True, slots=True)
class MeetingRole:
    """Exact published role version participating in a bounded meeting."""

    role_key: str
    role_version: int

    def __post_init__(self) -> None:
        if not self.role_key or self.role_key.strip() != self.role_key:
            raise ValueError("meeting role key must be non-empty and trimmed")
        if self.role_version < 1:
            raise ValueError("meeting role version must be positive")


@dataclass(frozen=True, slots=True)
class RoleMeetingRequest:
    """Content-free limits and references for a Workflow-backed meeting."""

    roles: tuple[MeetingRole, ...]
    rounds: int
    max_parallelism: int
    max_calls: int
    goal_reference: str

    def __post_init__(self) -> None:
        if not self.roles or len(self.roles) > _MAX_PARTICIPANTS:
            raise ValueError("meeting participant count is outside the allowed bound")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("meeting roles must be unique")
        if not 1 <= self.rounds <= _MAX_ROUNDS:
            raise ValueError("meeting rounds are outside the allowed bound")
        if not 1 <= self.max_parallelism <= min(len(self.roles), _MAX_PARTICIPANTS):
            raise ValueError("meeting parallelism is outside the allowed bound")
        required_calls = len(self.roles) * self.rounds + 1
        if not required_calls <= self.max_calls <= _MAX_CALLS:
            raise ValueError("meeting call limit cannot cover the bounded plan")
        if not self.goal_reference or self.goal_reference.strip() != self.goal_reference:
            raise ValueError("meeting goal reference must be non-empty and trimmed")


class RoleMeetingService:
    """Validate role/grant snapshots and submit an unrolled meeting DAG."""

    def __init__(
        self,
        roles: RoleRepository,
        workflows: WorkflowService,
        clock: Clock,
    ) -> None:
        self._roles = roles
        self._workflows = workflows
        self._clock = clock

    async def submit(
        self,
        context: SecurityContext,
        project_id: UUID,
        request: RoleMeetingRequest,
        *,
        idempotency_key: str,
    ) -> WorkflowRun:
        """Freeze published roles and active grants before submitting the meeting DAG."""
        for participant in request.roles:
            role = await self._roles.get_role(
                context.workspace_id,
                participant.role_key,
                participant.role_version,
            )
            if role is None or role.status is not RoleVersionStatus.PUBLISHED:
                raise InvalidStateError("Meeting roles must resolve to published versions.")
            grants = await self._roles.list_grants(context.workspace_id, role.id)
            active_tools = {grant.tool_id for grant in grants if grant.active}
            if not set(role.descriptor.allowed_tool_ids).issubset(active_tools):
                raise InvalidStateError("Meeting role has a missing or revoked tool grant.")
        definition = meeting_definition(request, idempotency_key, self._clock)
        return await self._workflows.submit(
            context,
            project_id,
            definition,
            idempotency_key=idempotency_key,
            input_reference=request.goal_reference,
        )


def meeting_definition(
    request: RoleMeetingRequest,
    idempotency_key: str,
    clock: Clock,
) -> WorkflowDefinition:
    """Unroll rounds into an acyclic graph whose outputs are opaque proposal references."""
    seed = hashlib.sha256(idempotency_key.encode()).hexdigest()
    definition_id = uuid5(_MEETING_NAMESPACE, f"definition:{seed}")
    steps: list[StepDefinition] = []
    previous_round: tuple[str, ...] = ()
    retry = RetryPolicy(max_attempts=2, maximum_delay_seconds=8.0)
    for round_number in range(1, request.rounds + 1):
        current_round: list[str] = []
        for participant in request.roles:
            key = f"round-{round_number}-{participant.role_key}"
            current_round.append(key)
            steps.append(
                StepDefinition(
                    uuid5(definition_id, key),
                    key,
                    len(steps),
                    StepKind.REFERENCE,
                    180.0,
                    retry,
                    executor_key=(
                        f"agent.{participant.role_key}@{participant.role_version}"
                    ),
                    depends_on=previous_round,
                    input_schema={"type": "object"},
                    output_schema={
                        "type": "object",
                        "required": ["proposal_reference", "summary_reference"],
                    },
                )
            )
        previous_round = tuple(current_round)
    summary_key = "decision-summary"
    steps.append(
        StepDefinition(
            uuid5(definition_id, summary_key),
            summary_key,
            len(steps),
            StepKind.REFERENCE,
            180.0,
            retry,
            executor_key="agent.director.meeting_summary",
            depends_on=previous_round,
            input_schema={"type": "object"},
            output_schema={
                "type": "object",
                "required": ["decision_summary_reference"],
            },
        )
    )
    return WorkflowDefinition(
        definition_id,
        f"role_meeting_{seed[:16]}",
        1,
        tuple(steps),
        clock.now(),
        graph_version=2,
        description=(
            "Bounded role meeting; persisted outputs contain proposal and decision references only."
        ),
    )
