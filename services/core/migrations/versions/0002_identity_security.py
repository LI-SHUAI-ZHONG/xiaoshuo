"""Add identity, workspace RBAC, creator control, and append-only audit.

Revision ID: 0002_identity_security
Revises: 0001_persistence
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_identity_security"
down_revision: str | None = "0001_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def _timestamps_and_version() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )


def upgrade() -> None:
    """Create only execution 06 identity-owned tables and immutable audit guards."""
    op.create_table(
        "identity_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps_and_version(),
        sa.CheckConstraint("version > 0", name="ck_identity_users_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_identity_users"),
        sa.UniqueConstraint("issuer", "subject", name="uq_identity_users_issuer_subject"),
        schema=SCHEMA,
    )
    op.create_table(
        "identity_workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps_and_version(),
        sa.CheckConstraint("version > 0", name="ck_identity_workspaces_version_positive"),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], [f"{SCHEMA}.identity_users.id"], name="fk_workspaces_owner_user"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_workspaces"),
        schema=SCHEMA,
    )
    op.create_table(
        "identity_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps_and_version(),
        sa.CheckConstraint(
            "role IN ('OWNER', 'EDITOR', 'VIEWER', 'SERVICE')",
            name="ck_memberships_role_valid",
        ),
        sa.CheckConstraint("version > 0", name="ck_memberships_version_positive"),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.identity_users.id"], name="fk_memberships_user"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{SCHEMA}.identity_workspaces.id"],
            name="fk_memberships_workspace",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_memberships"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_memberships_workspace_user"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_memberships_workspace_active",
        "identity_memberships",
        ["workspace_id", "active"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_service_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps_and_version(),
        sa.CheckConstraint("version > 0", name="ck_service_identities_version_positive"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{SCHEMA}.identity_workspaces.id"],
            name="fk_service_identities_workspace",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_service_identities"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_service_identities_workspace_name"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_service_identities_workspace_active",
        "identity_service_identities",
        ["workspace_id", "active"],
        schema=SCHEMA,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_kind", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("result IN ('allowed', 'denied')", name="ck_audit_result_valid"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.UniqueConstraint("sequence", name="uq_audit_events_sequence"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_workspace_sequence",
        "audit_events",
        ["workspace_id", "sequence"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_control_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("change_code", sa.String(length=100), nullable=False),
        sa.Column("risk_code", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('ownership_transfer', 'export', 'archive', 'delete')",
            name="ck_control_requests_kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_control_requests_status_valid",
        ),
        sa.CheckConstraint("version > 0", name="ck_control_requests_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_identity_control_requests"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_control_requests_workspace_status",
        "identity_control_requests",
        ["workspace_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_human_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')", name="ck_human_approvals_decision_valid"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            [f"{SCHEMA}.identity_control_requests.id"],
            name="fk_human_approvals_request",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_human_approvals"),
        sa.UniqueConstraint("request_id", name="uq_human_approvals_request"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_human_approvals_workspace",
        "identity_human_approvals",
        ["workspace_id"],
        schema=SCHEMA,
    )

    op.execute(
        f"""
        CREATE FUNCTION {SCHEMA}.reject_append_only_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only records cannot be modified' USING ERRCODE = '23000';
        END;
        $$
        """
    )
    for table in ("audit_events", "identity_human_approvals"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {SCHEMA}.{table}
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.reject_append_only_mutation()
            """
        )
    op.execute(
        sa.text(
            "UPDATE accos.schema_metadata SET revision = :revision, "
            "updated_at = now(), version = version + 1 WHERE component = 'accos-core'"
        ).bindparams(revision=revision)
    )


def downgrade() -> None:
    """Remove execution 06 structures while leaving execution 05 intact."""
    op.execute(
        sa.text(
            "UPDATE accos.schema_metadata SET revision = :revision, "
            "updated_at = now(), version = version + 1 WHERE component = 'accos-core'"
        ).bindparams(revision=down_revision)
    )
    op.execute(
        f"DROP TRIGGER trg_identity_human_approvals_append_only "
        f"ON {SCHEMA}.identity_human_approvals"
    )
    op.execute(f"DROP TRIGGER trg_audit_events_append_only ON {SCHEMA}.audit_events")
    op.execute(f"DROP FUNCTION {SCHEMA}.reject_append_only_mutation()")
    op.drop_index(
        "ix_human_approvals_workspace", table_name="identity_human_approvals", schema=SCHEMA
    )
    op.drop_table("identity_human_approvals", schema=SCHEMA)
    op.drop_index(
        "ix_control_requests_workspace_status",
        table_name="identity_control_requests",
        schema=SCHEMA,
    )
    op.drop_table("identity_control_requests", schema=SCHEMA)
    op.drop_index("ix_audit_workspace_sequence", table_name="audit_events", schema=SCHEMA)
    op.drop_table("audit_events", schema=SCHEMA)
    op.drop_index(
        "ix_service_identities_workspace_active",
        table_name="identity_service_identities",
        schema=SCHEMA,
    )
    op.drop_table("identity_service_identities", schema=SCHEMA)
    op.drop_index(
        "ix_memberships_workspace_active", table_name="identity_memberships", schema=SCHEMA
    )
    op.drop_table("identity_memberships", schema=SCHEMA)
    op.drop_table("identity_workspaces", schema=SCHEMA)
    op.drop_table("identity_users", schema=SCHEMA)
