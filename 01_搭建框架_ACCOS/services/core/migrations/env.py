"""Alembic environment using the explicit runtime URL and async psycopg engine."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import accos.adapters.agents.persistence
import accos.adapters.agents.jobs
import accos.adapters.assets.persistence
import accos.adapters.assets.retention
import accos.adapters.consistency.persistence
import accos.adapters.creative.persistence
import accos.adapters.evolution.persistence
import accos.adapters.extensions.graph
import accos.adapters.feedback.persistence
import accos.adapters.identity.accounts
import accos.adapters.identity.persistence
import accos.adapters.knowledge.persistence
import accos.adapters.memory.persistence
import accos.adapters.models.persistence
import accos.adapters.models.runtime_rows
import accos.adapters.projects.content
import accos.adapters.projects.persistence
import accos.adapters.quality.persistence
import accos.adapters.tools.persistence
import accos.adapters.workflows.persistence  # noqa: F401 - registers workflow ORM tables.
from accos.adapters.knowledge.persistence import Vector8
from accos.adapters.persistence.models import Base
from accos.kernel.settings import load_settings

if TYPE_CHECKING:
    from sqlalchemy import Connection

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_SAME_SCHEMA_FOREIGN_KEYS = frozenset(
    {
        "fk_human_approvals_request",
        "fk_memberships_user",
        "fk_memberships_workspace",
        "fk_service_identities_workspace",
        "fk_workspaces_owner_user",
        "fk_projects_workspace",
        "fk_artifacts_project",
        "fk_artifact_revisions_artifact",
        "fk_assets_project",
        "fk_creative_containers_project",
        "fk_creative_records_container_owner",
        "fk_evolution_audit_proposal",
        "fk_evolution_proposals_project",
        "fk_feedback_consents_project",
        "fk_feedback_diagnostics_point",
        "fk_feedback_events_consent",
        "fk_feedback_events_project",
        "fk_feedback_experiments_project",
        "fk_feedback_metric_definitions_project",
        "fk_feedback_points_definition",
        "fk_feedback_points_event",
        "fk_feedback_samples_event",
        "fk_feedback_samples_experiment",
        "fk_feedback_samples_point",
        "fk_feedback_samples_variant",
        "fk_feedback_tombstones_event",
        "fk_feedback_variants_experiment",
        "fk_consistency_canon_project",
        "fk_consistency_checks_project",
        "fk_consistency_findings_check",
        "fk_consistency_resolutions_project",
        "fk_consistency_timeline_project",
        "fk_asset_versions_asset",
        "fk_workflow_steps_definition",
        "fk_workflow_runs_project",
        "fk_workflow_runs_definition",
        "fk_step_runs_workflow_run",
        "fk_step_runs_definition",
        "fk_task_runs_workflow_run",
        "fk_task_runs_step_run",
        "fk_approval_requests_workflow_run",
        "fk_approval_requests_step_run",
        "fk_approval_decisions_request",
        "fk_run_events_workflow_run",
        "fk_agent_context_project",
        "fk_agent_context_memory_package",
        "fk_agent_runs_context",
        "fk_agent_runs_project",
        "fk_agent_runs_workflow",
        "fk_agent_events_run",
        "fk_knowledge_sources_project",
        "fk_knowledge_documents_project",
        "fk_knowledge_versions_document",
        "fk_knowledge_versions_source",
        "fk_knowledge_chunks_source",
        "fk_knowledge_chunks_version",
        "fk_knowledge_embeddings_chunk",
        "fk_knowledge_vectors_embedding",
        "fk_knowledge_citations_source",
        "fk_knowledge_citations_document",
        "fk_knowledge_citations_version",
        "fk_knowledge_citations_chunk",
        "fk_knowledge_runs_source",
        "fk_knowledge_runs_document",
        "fk_knowledge_runs_version",
        "fk_knowledge_runs_workflow",
        "fk_memory_conflicts_candidate",
        "fk_memory_conflicts_current",
        "fk_memory_context_project",
        "fk_memory_grants_project",
        "fk_memory_links_from",
        "fk_memory_links_to",
        "fk_memory_records_project",
        "fk_quality_results_run",
        "fk_quality_rubrics_project",
        "fk_quality_runs_rubric",
    }
)


def include_object(
    _object: object,
    name: str | None,
    object_type: str,
    _reflected: object,
    _compare_to: object | None,
) -> bool:
    """Exclude Alembic's own version table from application-model drift checks."""
    if object_type == "table" and name == "alembic_version":
        return False
    if object_type == "index" and name == "ix_knowledge_vectors_cosine":
        return False
    # PostgreSQL omits the remote schema when it matches a user search_path entry.
    # The migration integration test verifies these named constraints explicitly.
    return not (object_type == "foreign_key_constraint" and name in _SAME_SCHEMA_FOREIGN_KEYS)


def compare_column_type(
    _migration_context: object,
    _inspected_column: object,
    _metadata_column: object,
    inspected_type: object,
    metadata_type: object,
) -> bool | None:
    """Treat native vector(8) and the portable Vector8 model type as equivalent."""
    if isinstance(metadata_type, Vector8) and str(inspected_type).lower().startswith("vector"):
        return False
    return None


def database_url() -> str:
    """Prefer a test-supplied URL; otherwise load the normal redacted runtime config."""
    supplied = config.attributes.get("database_url")
    return str(supplied) if supplied is not None else load_settings().required.database_url


def run_migrations_offline() -> None:
    """Emit SQL without opening a database connection."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=compare_column_type,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: Connection) -> None:
    """Run revision functions on an async connection's sync facade."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=compare_column_type,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create a migration-only pool and dispose it deterministically."""
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_sync_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations(), loop_factory=asyncio.SelectorEventLoop)
