"""Create the ACCOS persistence foundation.

Revision ID: 0001_persistence
Revises:
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_persistence"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create only extensions, schema metadata, idempotency, and Outbox tables."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "schema_metadata",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("revision", sa.String(length=64), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_schema_metadata_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_schema_metadata"),
        sa.UniqueConstraint("component", name="uq_schema_metadata_component"),
        schema=SCHEMA,
    )
    op.bulk_insert(
        sa.table(
            "schema_metadata",
            sa.column("id", sa.Uuid()),
            sa.column("component", sa.String()),
            sa.column("revision", sa.String()),
            schema=SCHEMA,
        ),
        [
            {
                "id": "7dd04b71-4470-438f-a1b8-ff6c933e2945",
                "component": "accos-core",
                "revision": revision,
            }
        ],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=128), nullable=False),
        sa.Column("result_reference", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_idempotency_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
        sa.UniqueConstraint(
            "workspace_id", "scope", "key", name="uq_idempotency_workspace_scope_key"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_idempotency_records_expiry",
        "idempotency_records",
        ["expires_at"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "sequence",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_outbox_attempt_count_non_negative"),
        sa.CheckConstraint("event_version > 0", name="ck_outbox_event_version_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'leased', 'published')", name="ck_outbox_status_valid"
        ),
        sa.CheckConstraint("version > 0", name="ck_outbox_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
        sa.UniqueConstraint("sequence", name="uq_outbox_events_sequence"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_outbox_events_relay",
        "outbox_events",
        ["status", "available_at", "lease_expires_at", "sequence"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Remove execution 05 structures; intended only for controlled rollback tests."""
    op.drop_index("ix_outbox_events_relay", table_name="outbox_events", schema=SCHEMA)
    op.drop_table("outbox_events", schema=SCHEMA)
    op.drop_index("ix_idempotency_records_expiry", table_name="idempotency_records", schema=SCHEMA)
    op.drop_table("idempotency_records", schema=SCHEMA)
    op.drop_table("schema_metadata", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
    op.execute("DROP EXTENSION IF EXISTS vector")
