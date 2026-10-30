"""Durable local identity, settings histories and frozen approval policies.

Revision ID: 0013_identity_accounts
Revises: 0012_extension_graph_projection
No application imports, network calls or destructive backfill.
"""

from __future__ import annotations
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_identity_accounts"
down_revision = "0012_extension_graph_projection"
branch_labels = None
depends_on = None
SCHEMA = "accos"
POLICY_TABLES = (
    "identity_control_requests",
    "workflow_runs",
    "workflow_approval_requests",
    "workflow_approval_decisions",
    "evolution_improvement_proposals",
)


def upgrade() -> None:
    op.create_table(
        "identity_bootstrap",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "identity_local_accounts",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("accos.identity_users.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(500), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "identity_login_sessions",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("accos.identity_users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identity_login_sessions_user_id", "identity_login_sessions", ["user_id"], schema=SCHEMA
    )
    op.create_table(
        "identity_login_limits",
        sa.Column("key", sa.String(64), nullable=False, primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "identity_settings_history",
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("accos.identity_workspaces.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "identity_personal_tokens",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("accos.identity_workspaces.id"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("accos.identity_users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identity_personal_tokens_workspace_id",
        "identity_personal_tokens",
        ["workspace_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_credentials",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("accos.identity_workspaces.id"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ciphertext", sa.String(24000), nullable=True),
        sa.Column("external_ref", sa.String(200), nullable=True),
        sa.Column("key_id", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "name", name="uq_identity_credential_name"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identity_credentials_workspace_id",
        "identity_credentials",
        ["workspace_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_scope_grants",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("accos.identity_workspaces.id"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("accos.identity_users.id"), nullable=False),
        sa.Column("scope_kind", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "user_id", "scope_kind", "scope_id", name="uq_identity_scope_grant"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identity_scope_grants_workspace_id",
        "identity_scope_grants",
        ["workspace_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "identity_creator_anchors",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("accos.identity_workspaces.id"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("accos.identity_users.id"), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_identity_creator_anchor"),
        schema=SCHEMA,
    )

    op.create_table(
        "identity_oidc_flows",
        sa.Column("state_hash", sa.String(64), nullable=False, primary_key=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("verifier", sa.String(200), nullable=False),
        sa.Column("nonce", sa.String(200), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )

    op.execute("INSERT INTO accos.identity_bootstrap (id, consumed) VALUES (1, false)")
    op.execute(
        "INSERT INTO accos.identity_creator_anchors (id, workspace_id, user_id) SELECT md5(workspace_id::text || ':' || user_id::text)::uuid, workspace_id, user_id FROM accos.identity_memberships ON CONFLICT DO NOTHING"
    )
    for table in POLICY_TABLES:
        op.add_column(
            table,
            sa.Column(
                "approval_policy_ref",
                sa.String(100),
                nullable=False,
                server_default="legacy_dual_control",
            ),
            schema=SCHEMA,
        )
    for table in ("workflow_approval_requests", "workflow_approval_decisions"):
        op.add_column(
            table,
            sa.Column("input_digest", sa.String(64), nullable=False, server_default=""),
            schema=SCHEMA,
        )
    op.add_column(
        "workflow_runs",
        sa.Column("auth_method", sa.String(20), nullable=False, server_default="legacy"),
        schema=SCHEMA,
    )
    op.add_column(
        "workflow_runs", sa.Column("credential_id", sa.Uuid(), nullable=True), schema=SCHEMA
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision='0013_identity_accounts', updated_at=now() WHERE component='accos-core'"
    )


def downgrade() -> None:
    raise RuntimeError(
        "Identity downgrade is intentionally blocked: restore a verified pre-migration backup into an isolated database; never discard credentials or approval history."
    )
