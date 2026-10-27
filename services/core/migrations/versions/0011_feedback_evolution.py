"""Add consent-aware feedback and controlled evolution metadata.

Revision ID: 0011_feedback_evolution
Revises: 0010_consistency_quality
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0011_feedback_evolution"
down_revision: str | None = "0010_consistency_quality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    """Create privacy-governed feedback and proposal-only evolution tables."""
    op.create_table(
        "feedback_behavior_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_feedback_consents_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_behavior_consents"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_consents_scope",
        "feedback_behavior_consents",
        ["workspace_id", "project_id", "actor_id", "granted_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("signal_code", sa.String(length=100), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("consent_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("creator_signal_reference", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            [f"{SCHEMA}.feedback_behavior_consents.id"],
            name="fk_feedback_events_consent",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_feedback_events_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_events"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_events_scope",
        "feedback_events",
        ["workspace_id", "project_id", "source", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_metric_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=100), nullable=False),
        sa.Column("dimensions", JSONB, nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("sensitivity", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            [f"{SCHEMA}.projects.id"],
            name="fk_feedback_metric_definitions_project",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_metric_definitions"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_feedback_metric_definition",
        "feedback_metric_definitions",
        ["workspace_id", "project_id", "name", "version"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_metric_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("dimensions", JSONB, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=False),
        sa.Column("source_feedback_event_id", sa.Uuid(), nullable=True),
        sa.Column("included", sa.Boolean(), nullable=False),
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["metric_definition_id"],
            [f"{SCHEMA}.feedback_metric_definitions.id"],
            name="fk_feedback_points_definition",
        ),
        sa.ForeignKeyConstraint(
            ["source_feedback_event_id"],
            [f"{SCHEMA}.feedback_events.id"],
            name="fk_feedback_points_event",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_metric_points"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_points_scope",
        "feedback_metric_points",
        ["workspace_id", "project_id", "metric_name", "observed_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_diagnostic_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("metric_point_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=40), nullable=False),
        sa.Column("finding_code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["metric_point_id"],
            [f"{SCHEMA}.feedback_metric_points.id"],
            name="fk_feedback_diagnostics_point",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_diagnostic_findings"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_diagnostics_scope",
        "feedback_diagnostic_findings",
        ["workspace_id", "project_id", "severity"],
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_key", sa.String(length=100), nullable=False),
        sa.Column("protocol_version", sa.String(length=40), nullable=False),
        sa.Column("hypothesis_code", sa.String(length=100), nullable=False),
        sa.Column("primary_metric_name", sa.String(length=100), nullable=False),
        sa.Column("sample_scope", sa.String(length=40), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stop_condition_codes", JSONB, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_code", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_feedback_experiments_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_experiments"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_feedback_experiment_version",
        "feedback_experiments",
        ["workspace_id", "project_id", "experiment_key", "protocol_version"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_experiment_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("variant_key", sa.String(length=100), nullable=False),
        sa.Column("configuration_reference", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            [f"{SCHEMA}.feedback_experiments.id"],
            name="fk_feedback_variants_experiment",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_experiment_variants"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_feedback_variant_key",
        "feedback_experiment_variants",
        ["experiment_id", "variant_key"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_experiment_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("metric_point_id", sa.Uuid(), nullable=False),
        sa.Column("source_feedback_event_id", sa.Uuid(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False),
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            [f"{SCHEMA}.feedback_experiments.id"],
            name="fk_feedback_samples_experiment",
        ),
        sa.ForeignKeyConstraint(
            ["metric_point_id"],
            [f"{SCHEMA}.feedback_metric_points.id"],
            name="fk_feedback_samples_point",
        ),
        sa.ForeignKeyConstraint(
            ["source_feedback_event_id"],
            [f"{SCHEMA}.feedback_events.id"],
            name="fk_feedback_samples_event",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            [f"{SCHEMA}.feedback_experiment_variants.id"],
            name="fk_feedback_samples_variant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_experiment_samples"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_samples_scope",
        "feedback_experiment_samples",
        ["workspace_id", "project_id", "experiment_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "feedback_tombstones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_feedback_event_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_kind", sa.String(length=30), nullable=False),
        sa.Column("artifact_reference", sa.String(length=500), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_feedback_event_id"],
            [f"{SCHEMA}.feedback_events.id"],
            name="fk_feedback_tombstones_event",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback_tombstones"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_feedback_tombstones_scope",
        "feedback_tombstones",
        ["workspace_id", "project_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "evolution_improvement_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("diagnostic_finding_ids", JSONB, nullable=False),
        sa.Column("input_references", JSONB, nullable=False),
        sa.Column("algorithm_versions", JSONB, nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=True),
        sa.Column("change_reference", sa.String(length=500), nullable=True),
        sa.Column("safety_policy_version", sa.String(length=100), nullable=True),
        sa.Column("safety_rule_code", sa.String(length=100), nullable=True),
        sa.Column("simulation_evidence", JSONB, nullable=False),
        sa.Column("evaluation_code", sa.String(length=100), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("rollback_reference", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_evolution_proposals_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evolution_improvement_proposals"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_evolution_proposals_scope",
        "evolution_improvement_proposals",
        ["workspace_id", "project_id", "state"],
        schema=SCHEMA,
    )
    op.create_table(
        "evolution_audit_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(length=30), nullable=True),
        sa.Column("to_state", sa.String(length=30), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("algorithm_versions", JSONB, nullable=False),
        sa.Column("evidence_references", JSONB, nullable=False),
        sa.Column("rollback_reference", sa.String(length=500), nullable=True),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            [f"{SCHEMA}.evolution_improvement_proposals.id"],
            name="fk_evolution_audit_proposal",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evolution_audit_entries"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_evolution_audit_scope",
        "evolution_audit_entries",
        ["workspace_id", "project_id", "proposal_id", "occurred_at"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0011_feedback_evolution', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only stage-15 state and restore the stage-14 marker."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0010_consistency_quality', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index("ix_evolution_audit_scope", table_name="evolution_audit_entries", schema=SCHEMA)
    op.drop_table("evolution_audit_entries", schema=SCHEMA)
    op.drop_index(
        "ix_evolution_proposals_scope", table_name="evolution_improvement_proposals", schema=SCHEMA
    )
    op.drop_table("evolution_improvement_proposals", schema=SCHEMA)
    op.drop_index("ix_feedback_tombstones_scope", table_name="feedback_tombstones", schema=SCHEMA)
    op.drop_table("feedback_tombstones", schema=SCHEMA)
    op.drop_index(
        "ix_feedback_samples_scope", table_name="feedback_experiment_samples", schema=SCHEMA
    )
    op.drop_table("feedback_experiment_samples", schema=SCHEMA)
    op.drop_index(
        "uq_feedback_variant_key", table_name="feedback_experiment_variants", schema=SCHEMA
    )
    op.drop_table("feedback_experiment_variants", schema=SCHEMA)
    op.drop_index(
        "uq_feedback_experiment_version", table_name="feedback_experiments", schema=SCHEMA
    )
    op.drop_table("feedback_experiments", schema=SCHEMA)
    op.drop_index(
        "ix_feedback_diagnostics_scope", table_name="feedback_diagnostic_findings", schema=SCHEMA
    )
    op.drop_table("feedback_diagnostic_findings", schema=SCHEMA)
    op.drop_index("ix_feedback_points_scope", table_name="feedback_metric_points", schema=SCHEMA)
    op.drop_table("feedback_metric_points", schema=SCHEMA)
    op.drop_index(
        "uq_feedback_metric_definition", table_name="feedback_metric_definitions", schema=SCHEMA
    )
    op.drop_table("feedback_metric_definitions", schema=SCHEMA)
    op.drop_index("ix_feedback_events_scope", table_name="feedback_events", schema=SCHEMA)
    op.drop_table("feedback_events", schema=SCHEMA)
    op.drop_index(
        "ix_feedback_consents_scope", table_name="feedback_behavior_consents", schema=SCHEMA
    )
    op.drop_table("feedback_behavior_consents", schema=SCHEMA)
