"""Expand the single Workflow runtime into versioned DAG orchestration.

Revision ID: 0016_workflow_dag
Revises: 0015_model_execution
No schedules, roles, user content or jobs are seeded or executed by this migration.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_workflow_dag"
down_revision = "0015_model_execution"
branch_labels = None
depends_on = None
SCHEMA = "accos"
JSON = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column(
        "workflow_definitions",
        sa.Column("graph_version", sa.Integer(), nullable=False, server_default="1"),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("status", sa.String(20), nullable=False, server_default="published"),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("checksum", sa.String(64), nullable=False, server_default=""),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workflow_definitions_graph_version",
        "workflow_definitions",
        "graph_version IN (1, 2)",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workflow_definitions_status_valid",
        "workflow_definitions",
        "status IN ('draft', 'published', 'archived')",
        schema=SCHEMA,
    )

    step_columns = (
        sa.Column(
            "executor_key", sa.String(150), nullable=False, server_default="framework.default"
        ),
        sa.Column("depends_on", JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "input_schema",
            JSON,
            nullable=False,
            server_default=sa.text('\'{"type":"object"}\'::jsonb'),
        ),
        sa.Column(
            "output_schema",
            JSON,
            nullable=False,
            server_default=sa.text('\'{"type":"object"}\'::jsonb'),
        ),
        sa.Column("requirements", JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "condition",
            JSON,
            nullable=False,
            server_default=sa.text('\'{"operator":"always"}\'::jsonb'),
        ),
        sa.Column("budget_limit_microusd", sa.BigInteger(), nullable=True),
        sa.Column(
            "budget_reservation_required", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("approval_policy_ref", sa.String(100), nullable=True),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("external_side_effect", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("operation_key_template", sa.String(200), nullable=True),
    )
    for column in step_columns:
        op.add_column("workflow_step_definitions", column, schema=SCHEMA)
    op.create_check_constraint(
        "ck_workflow_steps_iterations",
        "workflow_step_definitions",
        "max_iterations BETWEEN 1 AND 100",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workflow_steps_budget_positive",
        "workflow_step_definitions",
        "budget_limit_microusd IS NULL OR budget_limit_microusd > 0",
        schema=SCHEMA,
    )

    op.create_table(
        "workflow_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("definition_name", sa.String(100), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("schedule_expression", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("misfire_policy", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_reference", sa.String(500), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("idempotency_prefix", sa.String(128), nullable=False),
        sa.Column("last_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", sa.Uuid(), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["accos.projects.id"], name="fk_workflow_schedules_project"
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["accos.workflow_definitions.id"],
            name="fk_workflow_schedules_definition",
        ),
        sa.UniqueConstraint("workspace_id", "idempotency_prefix", name="uq_schedules_prefix"),
        sa.CheckConstraint("definition_version > 0", name="ck_schedules_definition_version"),
        sa.CheckConstraint("version > 0", name="ck_schedules_version"),
        sa.CheckConstraint(
            "misfire_policy IN ('catch_up', 'fire_once', 'skip')",
            name="ck_schedules_misfire_valid",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'archived')", name="ck_schedules_status_valid"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_schedules_due",
        "workflow_schedules",
        ["status", "next_due_at", "lease_until"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_schedules_scope",
        "workflow_schedules",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )

    op.drop_constraint("ck_workflow_runs_status_valid", "workflow_runs", schema=SCHEMA)
    for column in (
        sa.Column("parent_run_id", sa.Uuid(), nullable=True),
        sa.Column("previous_run_id", sa.Uuid(), nullable=True),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="1"),
    ):
        op.add_column("workflow_runs", column, schema=SCHEMA)
    op.create_foreign_key(
        "fk_workflow_runs_parent",
        "workflow_runs",
        "workflow_runs",
        ["parent_run_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_workflow_runs_previous",
        "workflow_runs",
        "workflow_runs",
        ["previous_run_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_workflow_runs_schedule",
        "workflow_runs",
        "workflow_schedules",
        ["schedule_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workflow_runs_status_valid",
        "workflow_runs",
        "status IN ('pending','running','paused','waiting_approval','waiting_resource',"
        "'waiting_configuration','waiting_budget','awaiting_external_result','succeeded',"
        "'failed','cancelling','cancelled')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workflow_runs_iteration", "workflow_runs", "iteration BETWEEN 1 AND 100", schema=SCHEMA
    )

    op.drop_constraint("ck_step_runs_status_valid", "workflow_step_runs", schema=SCHEMA)
    for column in (
        sa.Column("input_manifest_id", sa.Uuid(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("blocked_reason", sa.String(200), nullable=True),
        sa.Column("condition_result", sa.Boolean(), nullable=True),
    ):
        op.add_column("workflow_step_runs", column, schema=SCHEMA)
    op.create_check_constraint(
        "ck_step_runs_status_valid",
        "workflow_step_runs",
        "status IN ('pending','running','waiting_approval','blocked','skipped','stale',"
        "'awaiting_external_result','succeeded','failed','cancelled')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_step_runs_iteration", "workflow_step_runs", "iteration BETWEEN 1 AND 100", schema=SCHEMA
    )

    op.drop_constraint("ck_task_runs_status_valid", "workflow_task_runs", schema=SCHEMA)
    op.add_column(
        "workflow_task_runs",
        sa.Column("operation_key", sa.String(200), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_task_runs",
        sa.Column("provider_job_id", sa.String(200), nullable=True),
        schema=SCHEMA,
    )
    op.execute("UPDATE accos.workflow_task_runs SET operation_key = idempotency_key")
    op.alter_column("workflow_task_runs", "operation_key", nullable=False, schema=SCHEMA)
    op.create_unique_constraint(
        "uq_task_runs_operation_key",
        "workflow_task_runs",
        ["workspace_id", "operation_key"],
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_task_runs_status_valid",
        "workflow_task_runs",
        "status IN ('pending','running','succeeded','failed','cancelled','dead_letter','unknown')",
        schema=SCHEMA,
    )

    _create_workflow_evidence_tables()
    _create_role_tables()
    op.create_foreign_key(
        "fk_step_runs_input_manifest",
        "workflow_step_runs",
        "workflow_input_manifests",
        ["input_manifest_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision='0016_workflow_dag', updated_at=now() "
        "WHERE component='accos-core'"
    )


def _create_workflow_evidence_tables() -> None:
    op.create_table(
        "workflow_input_manifests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_run_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("step_definition_id", sa.Uuid(), nullable=False),
        sa.Column("executor_key", sa.String(150), nullable=False),
        sa.Column("resolved_inputs", JSON, nullable=False),
        sa.Column("prompt_pin", sa.String(200), nullable=True),
        sa.Column("model_pin", sa.String(200), nullable=True),
        sa.Column("policy_pin", sa.String(200), nullable=False),
        sa.Column("permission_version", sa.String(100), nullable=False),
        sa.Column("grant_version", sa.String(100), nullable=False),
        sa.Column("consent_version", sa.String(100), nullable=False),
        sa.Column("budget_reservation_ref", sa.String(500), nullable=True),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["accos.workflow_runs.id"], name="fk_input_manifests_run"
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"], ["accos.workflow_step_runs.id"], name="fk_input_manifests_step_run"
        ),
        sa.UniqueConstraint("workflow_run_id", "step_run_id", name="uq_input_manifests_step"),
        sa.CheckConstraint("definition_version > 0", name="ck_input_manifests_definition_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_input_manifests_scope_run",
        "workflow_input_manifests",
        ["workspace_id", "project_id", "workflow_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_read_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_revision", sa.String(200), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("section_reference", sa.String(500), nullable=False),
        sa.Column("loaded_bytes", sa.BigInteger(), nullable=False),
        sa.Column("token_count", sa.BigInteger(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["accos.workflow_runs.id"], name="fk_read_receipts_run"
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"], ["accos.workflow_step_runs.id"], name="fk_read_receipts_step_run"
        ),
        sa.UniqueConstraint(
            "step_run_id",
            "source_reference",
            "source_revision",
            "section_reference",
            name="uq_read_receipts_span",
        ),
        sa.CheckConstraint("loaded_bytes > 0", name="ck_read_receipts_loaded_bytes"),
        sa.CheckConstraint("token_count >= 0", name="ck_read_receipts_token_count"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_read_receipts_scope_run",
        "workflow_read_receipts",
        ["workspace_id", "project_id", "workflow_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_dependency_edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_run_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_step_run_id", sa.Uuid(), nullable=False),
        sa.Column("producer_reference", sa.String(500), nullable=False),
        sa.Column("producer_revision", sa.String(200), nullable=False),
        sa.Column("producer_hash", sa.String(64), nullable=False),
        sa.Column("requirement_key", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["consumer_run_id"], ["accos.workflow_runs.id"], name="fk_dependency_edges_run"
        ),
        sa.ForeignKeyConstraint(
            ["consumer_step_run_id"],
            ["accos.workflow_step_runs.id"],
            name="fk_dependency_edges_step_run",
        ),
        sa.UniqueConstraint(
            "consumer_step_run_id", "requirement_key", name="uq_dependency_edges_requirement"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dependency_edges_producer",
        "workflow_dependency_edges",
        ["workspace_id", "producer_reference"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dependency_edges_consumer",
        "workflow_dependency_edges",
        ["workspace_id", "consumer_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_compensation_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("task_run_id", sa.Uuid(), nullable=False),
        sa.Column("operation_key", sa.String(200), nullable=False),
        sa.Column("hook", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result_reference", sa.String(500), nullable=True),
        sa.Column("error_reference", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_run_id"], ["accos.workflow_task_runs.id"], name="fk_compensation_task"
        ),
        sa.UniqueConstraint("task_run_id", "hook", name="uq_compensation_task_hook"),
        sa.CheckConstraint(
            "status IN ('pending','succeeded','failed','unknown')",
            name="ck_compensation_status_valid",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_compensation_scope_run",
        "workflow_compensation_records",
        ["workspace_id", "project_id", "workflow_run_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_dispatch_leases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("resource_kind", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("fence_token", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.String(100), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource_kind", "resource_id", name="uq_dispatch_lease_resource"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dispatch_leases_expiry",
        "workflow_dispatch_leases",
        ["resource_kind", "lease_until"],
        schema=SCHEMA,
    )
    op.create_table(
        "workflow_inbox_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("consumer", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("aggregate_version > 0", name="ck_workflow_inbox_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_workflow_inbox_aggregate",
        "workflow_inbox_events",
        ["consumer", "aggregate_id", "aggregate_version"],
        schema=SCHEMA,
    )


def _create_role_tables() -> None:
    op.create_table(
        "agent_role_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("role_key", sa.String(100), nullable=False),
        sa.Column("role_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("descriptor", JSON, nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "role_key", "role_version", name="uq_agent_role_version"
        ),
        sa.CheckConstraint("role_version > 0", name="ck_agent_role_version_positive"),
        sa.CheckConstraint(
            "status IN ('draft','published','disabled','archived')",
            name="ck_agent_role_status_valid",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_roles_scope_status",
        "agent_role_versions",
        ["workspace_id", "status", "role_key"],
        schema=SCHEMA,
    )
    op.create_table(
        "agent_role_tool_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("role_version_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.String(100), nullable=False),
        sa.Column("tool_version", sa.String(30), nullable=False),
        sa.Column("permissions", JSON, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_version_id"], ["accos.agent_role_versions.id"], name="fk_agent_role_grant_role"
        ),
        sa.UniqueConstraint("role_version_id", "tool_id", name="uq_agent_role_tool_grant"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_role_grants_scope",
        "agent_role_tool_grants",
        ["workspace_id", "role_version_id", "active"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Workflow DAG, input evidence and schedule history are retained. Restore an isolated "
        "verified backup instead of destructive downgrade."
    )
