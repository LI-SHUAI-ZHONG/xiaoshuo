"""Add the disposable extension graph projection.

Revision ID: 0012_extension_graph_projection
Revises: 0011_feedback_evolution
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0012_extension_graph_projection"
down_revision: str | None = "0011_feedback_evolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create rebuildable node and edge projection tables with no domain ownership."""
    op.create_table(
        "extension_graph_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("projection_owner", sa.String(length=100), nullable=False),
        sa.Column("node_owner", sa.String(length=100), nullable=False),
        sa.Column("node_kind", sa.String(length=100), nullable=False),
        sa.Column("node_identifier", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_extension_graph_nodes"),
        sa.UniqueConstraint(
            "workspace_id",
            "projection_owner",
            "node_owner",
            "node_kind",
            "node_identifier",
            name="uq_extension_graph_node",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_extension_graph_nodes_scope",
        "extension_graph_nodes",
        ["workspace_id", "projection_owner", "node_kind"],
        schema=SCHEMA,
    )
    op.create_table(
        "extension_graph_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("projection_owner", sa.String(length=100), nullable=False),
        sa.Column("source_owner", sa.String(length=100), nullable=False),
        sa.Column("source_kind", sa.String(length=100), nullable=False),
        sa.Column("source_identifier", sa.Uuid(), nullable=False),
        sa.Column("target_owner", sa.String(length=100), nullable=False),
        sa.Column("target_kind", sa.String(length=100), nullable=False),
        sa.Column("target_identifier", sa.Uuid(), nullable=False),
        sa.Column("relationship", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_extension_graph_edges"),
        sa.UniqueConstraint(
            "workspace_id",
            "projection_owner",
            "source_owner",
            "source_kind",
            "source_identifier",
            "target_owner",
            "target_kind",
            "target_identifier",
            "relationship",
            name="uq_extension_graph_edge",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_extension_graph_edges_source",
        "extension_graph_edges",
        ["workspace_id", "projection_owner", "source_identifier"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_extension_graph_edges_target",
        "extension_graph_edges",
        ["workspace_id", "projection_owner", "target_identifier"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0012_extension_graph_projection', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only disposable extension projections and restore the stage-15 marker."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0011_feedback_evolution', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index(
        "ix_extension_graph_edges_target", table_name="extension_graph_edges", schema=SCHEMA
    )
    op.drop_index(
        "ix_extension_graph_edges_source", table_name="extension_graph_edges", schema=SCHEMA
    )
    op.drop_table("extension_graph_edges", schema=SCHEMA)
    op.drop_index(
        "ix_extension_graph_nodes_scope", table_name="extension_graph_nodes", schema=SCHEMA
    )
    op.drop_table("extension_graph_nodes", schema=SCHEMA)
