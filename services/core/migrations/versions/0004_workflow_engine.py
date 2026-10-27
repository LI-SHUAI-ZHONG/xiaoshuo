"""Add durable workflow definitions, runs, tasks, approvals, and run events.

Revision ID: 0004_workflow_engine
Revises: 0003_projects_assets
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_workflow_engine"
down_revision: str | None = "0003_projects_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create execution 08 workflow-owned tables and append-only guards."""
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "definition_version > 0", name="ck_workflow_definitions_version_positive"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_definitions"),
        sa.UniqueConstraint(
            "name", "definition_version", name="uq_workflow_definitions_name_version"
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_step_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("initial_delay_seconds", sa.Float(), nullable=False),
        sa.Column("maximum_delay_seconds", sa.Float(), nullable=False),
        sa.Column("retry_multiplier", sa.Float(), nullable=False),
        sa.Column("delay_seconds", sa.Float(), server_default="0", nullable=False),
        sa.Column("fail_until_attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("approval_expires_seconds", sa.Float(), nullable=True),
        sa.Column("compensation_hook", sa.String(length=200), nullable=True),
        sa.CheckConstraint("position >= 0", name="ck_workflow_steps_position_non_negative"),
        sa.CheckConstraint("timeout_seconds > 0", name="ck_workflow_steps_timeout_positive"),
        sa.CheckConstraint("max_attempts > 0", name="ck_workflow_steps_attempts_positive"),
        sa.CheckConstraint("initial_delay_seconds > 0", name="ck_workflow_steps_delay_positive"),
        sa.CheckConstraint(
            "maximum_delay_seconds >= initial_delay_seconds",
            name="ck_workflow_steps_delay_order",
        ),
        sa.CheckConstraint("retry_multiplier >= 1", name="ck_workflow_steps_multiplier_valid"),
        sa.CheckConstraint("delay_seconds >= 0", name="ck_workflow_steps_controlled_delay_valid"),
        sa.CheckConstraint(
            "fail_until_attempt >= 0 AND fail_until_attempt < max_attempts",
            name="ck_workflow_steps_failure_count_valid",
        ),
        sa.CheckConstraint(
            "kind IN ('reference', 'delay', 'controlled_failure', 'approval')",
            name="ck_workflow_steps_kind_valid",
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            [f"{SCHEMA}.workflow_definitions.id"],
            name="fk_workflow_steps_definition",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_step_definitions"),
        sa.UniqueConstraint("definition_id", "step_key", name="uq_workflow_steps_key"),
        sa.UniqueConstraint("definition_id", "position", name="uq_workflow_steps_position"),
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("definition_name", sa.String(length=100), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("input_reference", sa.String(length=500), nullable=False),
        sa.Column("output_reference", sa.String(length=500), nullable=True),
        sa.Column("error_reference", sa.String(length=500), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("actor_kind", sa.String(length=20), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("current_step_position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("event_sequence", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("pause_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'paused', 'waiting_approval', "
            "'succeeded', 'failed', 'cancelling', 'cancelled')",
            name="ck_workflow_runs_status_valid",
        ),
        sa.CheckConstraint("current_step_position >= 0", name="ck_workflow_runs_step_valid"),
        sa.CheckConstraint("event_sequence >= 0", name="ck_workflow_runs_event_sequence_valid"),
        sa.CheckConstraint("version > 0", name="ck_workflow_runs_version_positive"),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_workflow_runs_project"
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            [f"{SCHEMA}.workflow_definitions.id"],
            name="fk_workflow_runs_definition",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_workflow_runs_scope_status",
        "workflow_runs",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_step_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_definition_id", sa.Uuid(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_reference", sa.String(length=500), nullable=False),
        sa.Column("output_reference", sa.String(length=500), nullable=True),
        sa.Column("error_reference", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_step_runs_position_non_negative"),
        sa.CheckConstraint("attempt >= 0", name="ck_step_runs_attempt_non_negative"),
        sa.CheckConstraint("version > 0", name="ck_step_runs_version_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'waiting_approval', 'succeeded', 'failed', "
            "'cancelled')",
            name="ck_step_runs_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_step_runs_workflow_run",
        ),
        sa.ForeignKeyConstraint(
            ["step_definition_id"],
            [f"{SCHEMA}.workflow_step_definitions.id"],
            name="fk_step_runs_definition",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_step_runs"),
        sa.UniqueConstraint("workflow_run_id", "position", name="uq_step_runs_run_position"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_step_runs_scope_run",
        "workflow_step_runs",
        ["workspace_id", "project_id", "workflow_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_task_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("input_reference", sa.String(length=500), nullable=False),
        sa.Column("output_reference", sa.String(length=500), nullable=True),
        sa.Column("error_reference", sa.String(length=500), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_event_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("attempt >= 0", name="ck_task_runs_attempt_non_negative"),
        sa.CheckConstraint("version > 0", name="ck_task_runs_version_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled', 'dead_letter')",
            name="ck_task_runs_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_task_runs_workflow_run",
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"],
            [f"{SCHEMA}.workflow_step_runs.id"],
            name="fk_task_runs_step_run",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_task_runs"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_task_runs_idempotency"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_task_runs_claim",
        "workflow_task_runs",
        ["status", "available_at", "lease_expires_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_task_runs_scope_run",
        "workflow_task_runs",
        ["workspace_id", "project_id", "workflow_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_run_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')",
            name="ck_approval_requests_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_approval_requests_workflow_run",
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"],
            [f"{SCHEMA}.workflow_step_runs.id"],
            name="fk_approval_requests_step_run",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_approval_requests"),
        sa.UniqueConstraint("workflow_run_id", "step_run_id", name="uq_approval_requests_step"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_approval_requests_scope_status",
        "workflow_approval_requests",
        ["workspace_id", "status", "expires_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_approval_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')", name="ck_approval_decisions_value_valid"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            [f"{SCHEMA}.workflow_approval_requests.id"],
            name="fk_approval_decisions_request",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_approval_decisions"),
        sa.UniqueConstraint("request_id", name="uq_approval_decisions_request"),
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_run_events_sequence_positive"),
        sa.CheckConstraint("event_version > 0", name="ck_run_events_version_positive"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_run_events_workflow_run",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_run_events"),
        sa.UniqueConstraint("workflow_run_id", "sequence", name="uq_run_events_sequence"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_run_events_scope_cursor",
        "workflow_run_events",
        ["workspace_id", "workflow_run_id", "sequence"],
        schema=SCHEMA,
    )
    for table in (
        "workflow_definitions",
        "workflow_step_definitions",
        "workflow_approval_decisions",
        "workflow_run_events",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {SCHEMA}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.reject_append_only_mutation()"
        )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0004_workflow_engine', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only execution 08 structures during controlled rollback."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0003_projects_assets', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    for table in (
        "workflow_run_events",
        "workflow_approval_decisions",
        "workflow_step_definitions",
        "workflow_definitions",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_append_only ON {SCHEMA}.{table}")
    op.drop_index("ix_run_events_scope_cursor", table_name="workflow_run_events", schema=SCHEMA)
    op.drop_table("workflow_run_events", schema=SCHEMA)
    op.drop_table("workflow_approval_decisions", schema=SCHEMA)
    op.drop_index(
        "ix_approval_requests_scope_status",
        table_name="workflow_approval_requests",
        schema=SCHEMA,
    )
    op.drop_table("workflow_approval_requests", schema=SCHEMA)
    op.drop_index("ix_task_runs_scope_run", table_name="workflow_task_runs", schema=SCHEMA)
    op.drop_index("ix_task_runs_claim", table_name="workflow_task_runs", schema=SCHEMA)
    op.drop_table("workflow_task_runs", schema=SCHEMA)
    op.drop_index("ix_step_runs_scope_run", table_name="workflow_step_runs", schema=SCHEMA)
    op.drop_table("workflow_step_runs", schema=SCHEMA)
    op.drop_index("ix_workflow_runs_scope_status", table_name="workflow_runs", schema=SCHEMA)
    op.drop_table("workflow_runs", schema=SCHEMA)
    op.drop_table("workflow_step_definitions", schema=SCHEMA)
    op.drop_table("workflow_definitions", schema=SCHEMA)
