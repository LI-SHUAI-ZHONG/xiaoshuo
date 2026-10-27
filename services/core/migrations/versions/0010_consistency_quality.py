"""Add Canon consistency and schema-only quality evaluation metadata.

Revision ID: 0010_consistency_quality
Revises: 0009_creative_domains
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0010_consistency_quality"
down_revision: str | None = "0009_creative_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    """Create pointer-only consistency data and schema-only quality data."""
    op.create_table(
        "consistency_canon_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("logical_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("canon_key", sa.String(length=120), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("entry_version", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("entry_version > 0", name="ck_consistency_canon_version"),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_consistency_canon_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consistency_canon_entries"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_consistency_canon_version",
        "consistency_canon_entries",
        ["workspace_id", "project_id", "logical_id", "entry_version"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_table(
        "consistency_timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("event_reference", sa.String(length=500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("character_state_references", JSONB, nullable=False),
        sa.Column("world_state_references", JSONB, nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence >= 0", name="ck_consistency_timeline_sequence"),
        sa.CheckConstraint("source_version > 0", name="ck_consistency_timeline_version"),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_consistency_timeline_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consistency_timeline_events"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_consistency_timeline_scope",
        "consistency_timeline_events",
        ["workspace_id", "project_id", "occurred_at", "sequence"],
        schema=SCHEMA,
    )
    op.create_table(
        "consistency_check_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reports", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_consistency_checks_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consistency_check_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_consistency_checks_scope",
        "consistency_check_runs",
        ["workspace_id", "project_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "consistency_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("check_run_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("evidence_references", JSONB, nullable=False),
        sa.Column("message_code", sa.String(length=100), nullable=False),
        sa.Column("validator_key", sa.String(length=100), nullable=False),
        sa.Column("validator_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("detected_by", sa.Uuid(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["check_run_id"],
            [f"{SCHEMA}.consistency_check_runs.id"],
            name="fk_consistency_findings_check",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consistency_findings"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_consistency_findings_scope",
        "consistency_findings",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "consistency_resolution_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("finding_ids", JSONB, nullable=False),
        sa.Column("strategy_code", sa.String(length=100), nullable=False),
        sa.Column("target_reference", sa.String(length=500), nullable=False),
        sa.Column("expected_target_version", sa.Integer(), nullable=False),
        sa.Column("impact_references", JSONB, nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("applied_by", sa.Uuid(), nullable=True),
        sa.Column("result_reference", sa.String(length=500), nullable=True),
        sa.Column("result_version", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("expected_target_version > 0", name="ck_consistency_target_version"),
        sa.CheckConstraint("version > 0", name="ck_consistency_resolution_version"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            [f"{SCHEMA}.projects.id"],
            name="fk_consistency_resolutions_project",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consistency_resolution_proposals"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_consistency_resolutions_scope",
        "consistency_resolution_proposals",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "consistency_evidence_projection",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=500), nullable=False),
        sa.Column("owner", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("revision_version", sa.Integer(), nullable=False),
        sa.Column("projected_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_version > 0", name="ck_consistency_projection_version"),
        sa.PrimaryKeyConstraint(
            "workspace_id", "project_id", "reference", name="pk_consistency_evidence_projection"
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "quality_rubric_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("rubric_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("dimension_keys", JSONB, nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_quality_rubrics_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quality_rubric_versions"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_quality_rubric_version",
        "quality_rubric_versions",
        ["workspace_id", "project_id", "rubric_key", "version"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_table(
        "quality_evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("input_reference", sa.String(length=500), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["rubric_id"],
            [f"{SCHEMA}.quality_rubric_versions.id"],
            name="fk_quality_runs_rubric",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quality_evaluation_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_quality_runs_scope",
        "quality_evaluation_runs",
        ["workspace_id", "project_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "quality_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("evaluator_key", sa.String(length=100), nullable=False),
        sa.Column("evaluator_version", sa.String(length=40), nullable=False),
        sa.Column("dimensions", JSONB, nullable=False),
        sa.Column("result_reference", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            [f"{SCHEMA}.quality_evaluation_runs.id"],
            name="fk_quality_results_run",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quality_results"),
        sa.UniqueConstraint("evaluation_run_id", name="uq_quality_results_run"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_quality_results_scope",
        "quality_results",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0010_consistency_quality', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only stage-14 metadata and restore the stage-13 marker."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0009_creative_domains', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index("ix_quality_results_scope", table_name="quality_results", schema=SCHEMA)
    op.drop_table("quality_results", schema=SCHEMA)
    op.drop_index("ix_quality_runs_scope", table_name="quality_evaluation_runs", schema=SCHEMA)
    op.drop_table("quality_evaluation_runs", schema=SCHEMA)
    op.drop_index("uq_quality_rubric_version", table_name="quality_rubric_versions", schema=SCHEMA)
    op.drop_table("quality_rubric_versions", schema=SCHEMA)
    op.drop_table("consistency_evidence_projection", schema=SCHEMA)
    op.drop_index(
        "ix_consistency_resolutions_scope",
        table_name="consistency_resolution_proposals",
        schema=SCHEMA,
    )
    op.drop_table("consistency_resolution_proposals", schema=SCHEMA)
    op.drop_index("ix_consistency_findings_scope", table_name="consistency_findings", schema=SCHEMA)
    op.drop_table("consistency_findings", schema=SCHEMA)
    op.drop_index("ix_consistency_checks_scope", table_name="consistency_check_runs", schema=SCHEMA)
    op.drop_table("consistency_check_runs", schema=SCHEMA)
    op.drop_index(
        "ix_consistency_timeline_scope", table_name="consistency_timeline_events", schema=SCHEMA
    )
    op.drop_table("consistency_timeline_events", schema=SCHEMA)
    op.drop_index(
        "uq_consistency_canon_version", table_name="consistency_canon_entries", schema=SCHEMA
    )
    op.drop_table("consistency_canon_entries", schema=SCHEMA)
