"""Expand immutable content and branches; preserve legacy metadata without inventing bytes.

Only run in the isolated stage-45 migration acceptance environment before deployment.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_artifact_content"
down_revision = "0013_identity_accounts"
branch_labels = None
depends_on = None
SCHEMA = "accos"


def scope() -> list[sa.Column]:
    return [
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "artifact_id", sa.Uuid(), sa.ForeignKey("accos.project_artifacts.id"), nullable=False
        ),
    ]


def upgrade() -> None:
    # Equal bytes may occur in distinct logical files, MIME types or restored
    # versions. Hash deduplication is an optimization, not an ownership key.
    op.drop_constraint(
        "uq_asset_versions_project_hash", "asset_versions", type_="unique", schema=SCHEMA
    )
    op.create_index(
        "ix_asset_versions_project_hash",
        "asset_versions",
        ["workspace_id", "project_id", "content_hash"],
        schema=SCHEMA,
    )
    for column in [
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column(
            "content_status", sa.String(40), nullable=False, server_default="legacy_unverified"
        ),
        sa.Column("document_ref", postgresql.JSONB(), nullable=True),
        sa.Column("text_ref", postgresql.JSONB(), nullable=True),
        sa.Column("editor_schema_version", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(20), nullable=False, server_default="legacy"),
        sa.Column("working_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("document_epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("client_change_id", sa.Uuid(), nullable=True),
        sa.Column("request_digest", sa.String(64), nullable=True),
    ]:
        op.add_column("project_artifact_revisions", column, schema=SCHEMA)
    op.create_unique_constraint(
        "uq_content_change",
        "project_artifact_revisions",
        ["artifact_id", "branch_id", "created_by", "client_change_id"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.project_artifact_revisions SET content_status = CASE "
        "WHEN content_reference LIKE 'studio-input://%' THEN 'legacy_content_unavailable' "
        "WHEN content_reference IS NULL THEN 'empty' ELSE 'legacy_unverified' END"
    )
    op.create_table(
        "artifact_branches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *scope(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_revision_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("artifact_id", "name", name="uq_branch_name"),
        schema=SCHEMA,
    )
    op.create_table(
        "artifact_working_copies",
        sa.Column(
            "branch_id", sa.Uuid(), sa.ForeignKey("accos.artifact_branches.id"), primary_key=True
        ),
        *scope(),
        sa.Column(
            "head_revision_id",
            sa.Uuid(),
            sa.ForeignKey("accos.project_artifact_revisions.id"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document_epoch", sa.Integer(), nullable=False),
        sa.Column("editing_mode", sa.String(20), nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "revision_edges",
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("accos.project_artifact_revisions.id"),
            primary_key=True,
        ),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("accos.project_artifact_revisions.id"),
            primary_key=True,
        ),
        *scope(),
        schema=SCHEMA,
    )
    op.execute(
        "INSERT INTO accos.revision_edges (revision_id,parent_id,workspace_id,project_id,artifact_id) "
        "SELECT id,parent,workspace_id,project_id,artifact_id FROM (SELECT id,workspace_id,project_id,artifact_id, "
        "lag(id) OVER (PARTITION BY artifact_id ORDER BY revision_number) AS parent "
        "FROM accos.project_artifact_revisions) r WHERE parent IS NOT NULL"
    )
    op.create_table(
        "revision_patches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *scope(),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column(
            "base_revision_id",
            sa.Uuid(),
            sa.ForeignKey("accos.project_artifact_revisions.id"),
            nullable=False,
        ),
        sa.Column("document_ref", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        schema=SCHEMA,
    )
    for table, index in [
        ("artifact_branches", "ix_branch_scope"),
        ("artifact_working_copies", "ix_working_copy_scope"),
        ("revision_edges", "ix_revision_edge_scope"),
        ("revision_patches", "ix_revision_patch_scope"),
    ]:
        op.create_index(index, table, ["workspace_id", "project_id", "artifact_id"], schema=SCHEMA)
    for table, name in [
        ("asset_versions", "ck_asset_versions_size_positive"),
        ("asset_upload_sessions", "ck_upload_sessions_size_positive"),
    ]:
        op.drop_constraint(name, table, type_="check", schema=SCHEMA)
        op.create_check_constraint(name, table, "size_bytes >= 0", schema=SCHEMA)
    op.create_table(
        "asset_retention_holds",
        sa.Column("object_key", sa.String(500), primary_key=True),
        sa.Column("owner_reference", sa.String(200), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_asset_hold_scope", "asset_retention_holds", ["workspace_id"], schema=SCHEMA)


def downgrade() -> None:
    raise RuntimeError(
        "Content history cannot be discarded; restore a verified backup into an isolated namespace."
    )
