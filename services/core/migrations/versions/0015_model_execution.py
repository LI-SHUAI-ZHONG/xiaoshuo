"""Append real model configuration, content calls and atomic budget reservations.

No seed credentials, profiles, user content or automatic execution. Stage 45 only.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_model_execution"
down_revision = "0014_artifact_content"
branch_labels = None
depends_on = None
SCHEMA = "accos"


def upgrade() -> None:
    for name, constraint in (("model_profiles", "ck_model_profile_version"), ("model_policies", "ck_model_policy_version")):
        op.create_table(name,
            sa.Column("workspace_id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(100), primary_key=True),
            sa.Column("version", sa.Integer(), primary_key=True),
            sa.Column("data", postgresql.JSONB(), nullable=False),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("version > 0", name=constraint), schema=SCHEMA)
    op.create_table("model_budget_settings",
        sa.Column("workspace_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_model_budget_version"), schema=SCHEMA)
    op.create_table("prompt_versions",
        sa.Column("workspace_id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), primary_key=True),
        sa.Column("version", sa.String(30), primary_key=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), schema=SCHEMA)
    op.create_table("model_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("operation_key", sa.String(128), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("record", postgresql.JSONB(), nullable=False),
        sa.Column("security_headers", postgresql.JSONB(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "project_id", "actor_id", "operation_key", name="uq_model_call_operation"),
        sa.ForeignKeyConstraint(["project_id"], ["accos.projects.id"], name="fk_model_call_project"),
        sa.CheckConstraint("sequence >= 0", name="ck_model_call_sequence"), schema=SCHEMA)
    op.create_index("ix_model_call_history", "model_calls", ["workspace_id", "project_id", "created_at", "id"], schema=SCHEMA)
    op.create_index("ix_model_call_queue", "model_calls", ["status", "lease_until", "created_at"], schema=SCHEMA)
    op.create_index("ix_model_call_cache", "model_calls", ["workspace_id", "project_id", "cache_key", "created_at"], schema=SCHEMA)
    op.create_table("model_call_events",
        sa.Column("call_id", sa.Uuid(), primary_key=True),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["accos.model_calls.id"], name="fk_model_event_call"), schema=SCHEMA)
    op.create_index("ix_model_event_scope", "model_call_events", ["workspace_id", "project_id", "call_id", "sequence"], schema=SCHEMA)
    op.create_table("budget_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("token_debit", sa.BigInteger(), nullable=False),
        sa.Column("money_debit", sa.BigInteger(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("reconciliation", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("call_id", "attempt", name="uq_model_attempt_reservation"),
        sa.ForeignKeyConstraint(["call_id"], ["accos.model_calls.id"], name="fk_budget_call"),
        sa.CheckConstraint("token_debit >= 0 AND money_debit >= 0 AND attempt > 0", name="ck_budget_debits"),
        sa.CheckConstraint("status IN ('reserved','settled','released','unknown')", name="ck_budget_state"), schema=SCHEMA)
    op.create_index("ix_budget_workspace_day", "budget_reservations", ["workspace_id", "day"], schema=SCHEMA)
    op.create_index("ix_budget_workspace_task", "budget_reservations", ["workspace_id", "task_id"], schema=SCHEMA)
    op.create_table("agent_execution_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("operation_key", sa.String(128), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("headers", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "project_id", "actor_id", "operation_key", name="uq_agent_job_operation"),
        sa.ForeignKeyConstraint(["project_id"], ["accos.projects.id"], name="fk_agent_job_project"), schema=SCHEMA)
    op.create_index("ix_agent_job_queue", "agent_execution_jobs", ["status", "lease_until", "created_at"], schema=SCHEMA)


def downgrade() -> None:
    raise RuntimeError("Model calls and budget evidence are retained. Restore an isolated verified backup instead of destructive downgrade.")
