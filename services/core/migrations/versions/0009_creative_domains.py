"""Add the unified Novel, World, Character, and Creator metadata skeleton.

Revision ID: 0009_creative_domains
Revises: 0008_memory_context
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0009_creative_domains"
down_revision: str | None = "0008_memory_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create content-free aggregate and proposal metadata tables."""
    op.create_table(
        "creative_containers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "owner IN ('novel','world','character','creator')",
            name="ck_creative_containers_owner",
        ),
        sa.CheckConstraint("version > 0", name="ck_creative_containers_version"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            [f"{SCHEMA}.projects.id"],
            name="fk_creative_containers_project",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_creative_containers"),
        sa.UniqueConstraint(
            "id",
            "owner",
            "workspace_id",
            "project_id",
            name="uq_creative_containers_owner_scope",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_creative_containers_scope",
        "creative_containers",
        ["workspace_id", "project_id", "owner"],
        schema=SCHEMA,
    )
    op.create_table(
        "creative_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("logical_id", sa.Uuid(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("owner", sa.String(length=20), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("causation_id", sa.Uuid(), nullable=True),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "owner IN ('novel','world','character','creator')",
            name="ck_creative_records_owner",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_creative_records_version"),
        sa.CheckConstraint(
            "status IN ('proposal','current','superseded','rejected','archived')",
            name="ck_creative_records_status",
        ),
        sa.CheckConstraint(
            "(current AND status = 'current') OR (NOT current AND status <> 'current')",
            name="ck_creative_records_current",
        ),
        sa.CheckConstraint(
            "sequence IS NULL OR sequence >= 0", name="ck_creative_records_sequence"
        ),
        sa.CheckConstraint(
            "(causation_id IS NULL) = (source_event_id IS NULL)",
            name="ck_creative_records_causation_pair",
        ),
        sa.CheckConstraint(
            "(decided_by IS NULL) = (decided_at IS NULL)",
            name="ck_creative_records_decision_pair",
        ),
        sa.ForeignKeyConstraint(
            ["aggregate_id", "owner", "workspace_id", "project_id"],
            [
                f"{SCHEMA}.creative_containers.id",
                f"{SCHEMA}.creative_containers.owner",
                f"{SCHEMA}.creative_containers.workspace_id",
                f"{SCHEMA}.creative_containers.project_id",
            ],
            name="fk_creative_records_container_owner",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_creative_records"),
        sa.UniqueConstraint("logical_id", "record_version", name="uq_creative_records_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_creative_records_scope",
        "creative_records",
        ["workspace_id", "project_id", "owner"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_creative_records_current",
        "creative_records",
        ["logical_id"],
        unique=True,
        postgresql_where=sa.text("current"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_creative_records_causation",
        "creative_records",
        ["workspace_id", "project_id", "owner", "causation_id"],
        unique=True,
        postgresql_where=sa.text("causation_id IS NOT NULL"),
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0009_creative_domains', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only creative-owned metadata."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0008_memory_context', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index("uq_creative_records_causation", table_name="creative_records", schema=SCHEMA)
    op.drop_index("uq_creative_records_current", table_name="creative_records", schema=SCHEMA)
    op.drop_index("ix_creative_records_scope", table_name="creative_records", schema=SCHEMA)
    op.drop_table("creative_records", schema=SCHEMA)
    op.drop_index("ix_creative_containers_scope", table_name="creative_containers", schema=SCHEMA)
    op.drop_table("creative_containers", schema=SCHEMA)
