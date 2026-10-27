"""Add seven-scope memory, grants, conflicts, and immutable context packages.

Revision ID: 0008_memory_context
Revises: 0007_knowledge_pipeline
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_memory_context"
down_revision: str | None = "0007_knowledge_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create memory facts, explicit grants, decisions, and context snapshots."""
    op.create_table(
        "memory_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("logical_id", sa.Uuid(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("memory_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("universe_id", sa.Uuid(), nullable=True),
        sa.Column("creator_id", sa.Uuid(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance_kind", sa.String(length=80), nullable=False),
        sa.Column("provenance_reference", sa.String(length=500), nullable=False),
        sa.Column("retention_kind", sa.String(length=20), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("decay_half_life_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("record_version > 0", name="ck_memory_records_version_positive"),
        sa.CheckConstraint(
            "importance >= 0 AND importance <= 1 AND confidence >= 0 AND confidence <= 1",
            name="ck_memory_records_scores_bounded",
        ),
        sa.CheckConstraint(
            "(scope IN ('working','session','project') AND project_id IS NOT NULL "
            "AND universe_id IS NULL AND creator_id IS NULL) OR "
            "(scope = 'universe' AND project_id IS NULL AND universe_id IS NOT NULL "
            "AND creator_id IS NULL) OR (scope IN ('creator','experience','wisdom') "
            "AND project_id IS NULL AND universe_id IS NULL AND creator_id IS NOT NULL)",
            name="ck_memory_records_canonical_anchor",
        ),
        sa.CheckConstraint(
            "(current AND status = 'active') OR (NOT current AND status <> 'active')",
            name="ck_memory_records_current_active",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_memory_records_valid_time",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_memory_records_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memory_records"),
        sa.UniqueConstraint("logical_id", "record_version", name="uq_memory_records_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_records_scope_anchor",
        "memory_records",
        ["workspace_id", "scope", "project_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_memory_records_current",
        "memory_records",
        ["logical_id"],
        unique=True,
        postgresql_where=sa.text("current"),
        schema=SCHEMA,
    )
    op.create_table(
        "memory_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("from_record_id", sa.Uuid(), nullable=False),
        sa.Column("to_record_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("from_record_id <> to_record_id", name="ck_memory_links_distinct"),
        sa.ForeignKeyConstraint(
            ["from_record_id"],
            [f"{SCHEMA}.memory_records.id"],
            name="fk_memory_links_from",
        ),
        sa.ForeignKeyConstraint(
            ["to_record_id"],
            [f"{SCHEMA}.memory_records.id"],
            name="fk_memory_links_to",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memory_links"),
        sa.UniqueConstraint(
            "from_record_id", "to_record_id", "relation", name="uq_memory_links_relation"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_links_scope",
        "memory_links",
        ["workspace_id", "from_record_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "memory_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("anchor_kind", sa.String(length=20), nullable=False),
        sa.Column("anchor_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("can_write", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("anchor_kind IN ('universe','creator')", name="ck_memory_grants_kind"),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_memory_grants_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memory_grants"),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "anchor_kind",
            "anchor_id",
            name="uq_memory_grants_anchor",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_grants_target",
        "memory_grants",
        ["workspace_id", "project_id", "revoked_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "memory_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("current_record_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_record_id", sa.Uuid(), nullable=False),
        sa.Column(
            "candidate_resolutions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected')", name="ck_memory_conflicts_status"
        ),
        sa.ForeignKeyConstraint(
            ["current_record_id"],
            [f"{SCHEMA}.memory_records.id"],
            name="fk_memory_conflicts_current",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_record_id"],
            [f"{SCHEMA}.memory_records.id"],
            name="fk_memory_conflicts_candidate",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memory_conflicts"),
        sa.UniqueConstraint("candidate_record_id", name="uq_memory_conflicts_candidate"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_conflicts_scope",
        "memory_conflicts",
        ["workspace_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "memory_context_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_reference", sa.String(length=500), nullable=False),
        sa.Column("budget_chars", sa.Integer(), nullable=False),
        sa.Column("used_chars", sa.Integer(), nullable=False),
        sa.Column("budget_tokens", sa.Integer(), nullable=True),
        sa.Column("used_tokens", sa.Integer(), nullable=False),
        sa.Column("allowed_anchors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("omissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "budget_chars > 0 AND used_chars >= 0 AND used_chars <= budget_chars",
            name="ck_memory_context_budget",
        ),
        sa.CheckConstraint(
            "used_tokens >= 0 AND (budget_tokens IS NULL OR "
            "(budget_tokens > 0 AND used_tokens <= budget_tokens))",
            name="ck_memory_context_token_budget",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_memory_context_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memory_context_packages"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_context_scope",
        "memory_context_packages",
        ["workspace_id", "project_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "memory_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_memory_events"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memory_events_scope",
        "memory_events",
        ["workspace_id", "aggregate_id", "occurred_at"],
        schema=SCHEMA,
    )
    op.add_column(
        "agent_context_snapshots",
        sa.Column("memory_context_package_id", sa.Uuid(), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_agent_context_memory_package",
        "agent_context_snapshots",
        "memory_context_packages",
        ["memory_context_package_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    for table in ("memory_links", "memory_context_packages", "memory_events"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {SCHEMA}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.reject_append_only_mutation()"
        )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0008_memory_context', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove memory-owned state and restore the Knowledge-only schema."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0007_knowledge_pipeline', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_constraint(
        "fk_agent_context_memory_package",
        "agent_context_snapshots",
        type_="foreignkey",
        schema=SCHEMA,
    )
    op.drop_column("agent_context_snapshots", "memory_context_package_id", schema=SCHEMA)
    op.execute("DROP TRIGGER trg_memory_events_append_only ON accos.memory_events")
    op.drop_index("ix_memory_events_scope", table_name="memory_events", schema=SCHEMA)
    op.drop_table("memory_events", schema=SCHEMA)
    op.execute(
        "DROP TRIGGER trg_memory_context_packages_append_only ON accos.memory_context_packages"
    )
    op.drop_index("ix_memory_context_scope", table_name="memory_context_packages", schema=SCHEMA)
    op.drop_table("memory_context_packages", schema=SCHEMA)
    op.drop_index("ix_memory_conflicts_scope", table_name="memory_conflicts", schema=SCHEMA)
    op.drop_table("memory_conflicts", schema=SCHEMA)
    op.drop_index("ix_memory_grants_target", table_name="memory_grants", schema=SCHEMA)
    op.drop_table("memory_grants", schema=SCHEMA)
    op.execute("DROP TRIGGER trg_memory_links_append_only ON accos.memory_links")
    op.drop_index("ix_memory_links_scope", table_name="memory_links", schema=SCHEMA)
    op.drop_table("memory_links", schema=SCHEMA)
    op.drop_index("uq_memory_records_current", table_name="memory_records", schema=SCHEMA)
    op.drop_index("ix_memory_records_scope_anchor", table_name="memory_records", schema=SCHEMA)
    op.drop_table("memory_records", schema=SCHEMA)
