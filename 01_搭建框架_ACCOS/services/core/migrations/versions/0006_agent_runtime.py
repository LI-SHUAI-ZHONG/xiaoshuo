"""Add bounded Agent runs, immutable replay snapshots, and state events.

Revision ID: 0006_agent_runtime
Revises: 0005_model_tool_gateways
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_agent_runtime"
down_revision: str | None = "0005_model_tool_gateways"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create Agent-owned durable state and immutable replay evidence."""
    op.create_table(
        "agent_context_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("agent_version", sa.String(length=30), nullable=False),
        sa.Column("model_policy_id", sa.String(length=100), nullable=False),
        sa.Column("model_policy_version", sa.String(length=30), nullable=False),
        sa.Column("prompt_metadata_id", sa.String(length=150), nullable=False),
        sa.Column("prompt_metadata_version", sa.String(length=30), nullable=False),
        sa.Column("prompt_metadata_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "tool_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "permission_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_agent_context_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_context_snapshots"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_context_scope",
        "agent_context_snapshots",
        ["workspace_id", "project_id", "agent_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("agent_version", sa.String(length=30), nullable=False),
        sa.Column("context_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("task_reference", sa.String(length=500), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("result_kind", sa.String(length=40), nullable=True),
        sa.Column("result_reference", sa.String(length=500), nullable=True),
        sa.Column("workflow_name", sa.String(length=100), nullable=True),
        sa.Column("workflow_version", sa.Integer(), nullable=True),
        sa.Column(
            "protected_operations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("model_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tool_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("event_sequence", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("attempt > 0", name="ck_agent_runs_attempt_positive"),
        sa.CheckConstraint(
            "model_calls >= 0 AND tool_calls >= 0 AND tokens >= 0",
            name="ck_agent_runs_usage_non_negative",
        ),
        sa.CheckConstraint("event_sequence >= 0", name="ck_agent_runs_event_sequence_valid"),
        sa.CheckConstraint("version > 0", name="ck_agent_runs_version_positive"),
        sa.CheckConstraint(
            "status IN ('running', 'waiting_approval', 'succeeded', 'failed', "
            "'rejected', 'budget_exhausted', 'limit_exceeded')",
            name="ck_agent_runs_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["context_snapshot_id"],
            [f"{SCHEMA}.agent_context_snapshots.id"],
            name="fk_agent_runs_context",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_agent_runs_project"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_agent_runs_workflow",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_agent_runs_idempotency"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_runs_scope_status",
        "agent_runs",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_agent_events_sequence_positive"),
        sa.CheckConstraint("event_version > 0", name="ck_agent_events_version_positive"),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], [f"{SCHEMA}.agent_runs.id"], name="fk_agent_events_run"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_run_events"),
        sa.UniqueConstraint("agent_run_id", "sequence", name="uq_agent_events_sequence"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_events_scope_cursor",
        "agent_run_events",
        ["workspace_id", "agent_run_id", "sequence"],
        schema=SCHEMA,
    )
    for table in ("agent_context_snapshots", "agent_run_events"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {SCHEMA}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.reject_append_only_mutation()"
        )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0006_agent_runtime', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only Agent-owned runtime state."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0005_model_tool_gateways', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.execute("DROP TRIGGER trg_agent_run_events_append_only ON accos.agent_run_events")
    op.drop_index("ix_agent_events_scope_cursor", table_name="agent_run_events", schema=SCHEMA)
    op.drop_table("agent_run_events", schema=SCHEMA)
    op.drop_index("ix_agent_runs_scope_status", table_name="agent_runs", schema=SCHEMA)
    op.drop_table("agent_runs", schema=SCHEMA)
    op.execute(
        "DROP TRIGGER trg_agent_context_snapshots_append_only ON accos.agent_context_snapshots"
    )
    op.drop_index("ix_agent_context_scope", table_name="agent_context_snapshots", schema=SCHEMA)
    op.drop_table("agent_context_snapshots", schema=SCHEMA)
