"""Add model usage, tool calls, and durable workflow permission snapshots.

Revision ID: 0005_model_tool_gateways
Revises: 0004_workflow_engine
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_model_tool_gateways"
down_revision: str | None = "0004_workflow_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create append-only stage-09 ledgers and trusted workflow snapshots."""
    op.add_column(
        "workflow_runs",
        sa.Column(
            "permission_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_runs",
        sa.Column("policy_version", sa.String(length=100), server_default="", nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "model_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("task_run_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("capability", sa.String(length=30), nullable=False),
        sa.Column("provider_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("attempted", sa.Boolean(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt >= 0", name="ck_model_usage_attempt_non_negative"),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0",
            name="ck_model_usage_tokens_non_negative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_usage_records"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_model_usage_workspace_task",
        "model_usage_records",
        ["workspace_id", "task_run_id", "started_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_model_usage_workflow",
        "model_usage_records",
        ["workspace_id", "workflow_run_id", "started_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "tool_call_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("task_run_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("tool_id", sa.String(length=150), nullable=False),
        sa.Column("tool_version", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tool_call_records"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tool_calls_workflow",
        "tool_call_records",
        ["workspace_id", "workflow_run_id", "started_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tool_calls_task",
        "tool_call_records",
        ["workspace_id", "task_run_id", "started_at"],
        schema=SCHEMA,
    )
    for table in ("model_usage_records", "tool_call_records"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {SCHEMA}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.reject_append_only_mutation()"
        )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0005_model_tool_gateways', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only stage-09 ledgers and workflow snapshot columns."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0004_workflow_engine', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    for table in ("tool_call_records", "model_usage_records"):
        op.execute(f"DROP TRIGGER trg_{table}_append_only ON {SCHEMA}.{table}")
    op.drop_index("ix_tool_calls_task", table_name="tool_call_records", schema=SCHEMA)
    op.drop_index("ix_tool_calls_workflow", table_name="tool_call_records", schema=SCHEMA)
    op.drop_table("tool_call_records", schema=SCHEMA)
    op.drop_index("ix_model_usage_workflow", table_name="model_usage_records", schema=SCHEMA)
    op.drop_index("ix_model_usage_workspace_task", table_name="model_usage_records", schema=SCHEMA)
    op.drop_table("model_usage_records", schema=SCHEMA)
    op.drop_column("workflow_runs", "policy_version", schema=SCHEMA)
    op.drop_column("workflow_runs", "permission_snapshot", schema=SCHEMA)
