"""Built-in metadata-only knowledge workflow definition."""

from datetime import UTC, datetime
from uuid import UUID

from accos.modules.workflows.public import (
    RetryPolicy,
    StepDefinition,
    StepKind,
    WorkflowDefinition,
)

KNOWLEDGE_INGESTION_NAME = "knowledge_ingestion"
KNOWLEDGE_INGESTION_STEP = "knowledge-ingest"


def knowledge_ingestion_definition() -> WorkflowDefinition:
    """Return the immutable single-step ingestion driver."""
    return WorkflowDefinition(
        UUID("b1000000-0000-4000-8000-000000000001"),
        KNOWLEDGE_INGESTION_NAME,
        1,
        (
            StepDefinition(
                UUID("b1000000-0000-4000-8000-000000000011"),
                KNOWLEDGE_INGESTION_STEP,
                0,
                StepKind.REFERENCE,
                30.0,
                RetryPolicy(max_attempts=3, initial_delay_seconds=1.0),
            ),
        ),
        datetime(2026, 9, 5, tzinfo=UTC),
    )
