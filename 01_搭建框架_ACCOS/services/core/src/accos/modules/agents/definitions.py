"""Built-in content-free Agent descriptors and approval workflow metadata."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from accos.modules.agents.domain import (
    AgentBudget,
    AgentDescriptor,
    PromptMetadataReference,
)
from accos.modules.workflows.public import (
    RetryPolicy,
    StepDefinition,
    StepKind,
    WorkflowDefinition,
)

DIRECTOR_AGENT_ID = "director"
RESEARCH_AGENT_ID = "research"
WORLD_AGENT_ID = "world"
CHARACTER_AGENT_ID = "character"
WRITER_AGENT_ID = "writer"
EDITOR_AGENT_ID = "editor"
QUALITY_AGENT_ID = "quality"
AGENT_PLAN_REVIEW_NAME = "agent_plan_review"
DEFAULT_AGENT_BUDGET = AgentBudget(16, 3, 4, 30.0, 8, 2_048)

_INPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"input_reference": {"type": "string"}},
    "required": ["input_reference"],
    "additionalProperties": False,
}
_DIRECTOR_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string"},
        "workflow_name": {"type": "string"},
        "workflow_version": {"type": "integer"},
        "input_reference": {"type": "string"},
        "protected_operations": {"type": "array"},
        "approval_required": {"type": "boolean"},
    },
    "required": ["kind", "workflow_name", "workflow_version", "input_reference"],
    "additionalProperties": False,
}
_AGENT_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string"},
        "result_reference": {"type": "string"},
    },
    "required": ["kind", "result_reference"],
    "additionalProperties": False,
}


def built_in_agent_descriptors() -> tuple[AgentDescriptor, ...]:
    """Return the seven versioned descriptors without prompts or creative rules."""
    roles = (
        (DIRECTOR_AGENT_ID, ("workflow.select", "workflow.propose"), (), _DIRECTOR_OUTPUT_SCHEMA),
        (RESEARCH_AGENT_ID, ("research.propose",), ("fixture.reference",), _AGENT_OUTPUT_SCHEMA),
        (WORLD_AGENT_ID, ("world.propose",), (), _AGENT_OUTPUT_SCHEMA),
        (CHARACTER_AGENT_ID, ("character.propose",), (), _AGENT_OUTPUT_SCHEMA),
        (WRITER_AGENT_ID, ("writing.draft",), (), _AGENT_OUTPUT_SCHEMA),
        (EDITOR_AGENT_ID, ("editing.propose",), (), _AGENT_OUTPUT_SCHEMA),
        (QUALITY_AGENT_ID, ("quality.propose",), ("fixture.reference",), _AGENT_OUTPUT_SCHEMA),
    )
    return tuple(
        AgentDescriptor(
            agent_id,
            "1.0.0",
            capabilities,
            dict(_INPUT_SCHEMA),
            dict(output_schema),
            allowed_tools,
            "fake-agent-model-policy",
            "1.0.0",
            PromptMetadataReference(
                f"agent.{agent_id}.metadata",
                "1.0.0",
                hashlib.sha256(f"agent-metadata:{agent_id}:1.0.0".encode()).hexdigest(),
            ),
            DEFAULT_AGENT_BUDGET,
        )
        for agent_id, capabilities, allowed_tools, output_schema in roles
    )


def agent_plan_review_definition() -> WorkflowDefinition:
    """Return a fixed approval-only workflow that performs no protected mutation."""
    return WorkflowDefinition(
        UUID("a2000000-0000-4000-8000-000000000001"),
        AGENT_PLAN_REVIEW_NAME,
        1,
        (
            StepDefinition(
                UUID("a2000000-0000-4000-8000-000000000011"),
                "human-review",
                0,
                StepKind.APPROVAL,
                10.0,
                RetryPolicy(max_attempts=1),
                approval_expires_seconds=86_400.0,
            ),
        ),
        datetime(2026, 9, 5, tzinfo=UTC),
    )
