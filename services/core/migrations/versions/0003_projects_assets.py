"""Add projects, artifacts, assets, upload checkpoints, and object metadata.

Revision ID: 0003_projects_assets
Revises: 0002_identity_security
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_projects_assets"
down_revision: str | None = "0002_identity_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


def upgrade() -> None:
    """Create execution 07 records without introducing permanent deletion."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_projects_status_valid"),
        sa.CheckConstraint("version > 0", name="ck_projects_version_positive"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{SCHEMA}.identity_workspaces.id"],
            name="fk_projects_workspace",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_projects_workspace_status",
        "projects",
        ["workspace_id", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "project_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_type", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("current_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "artifact_type IN ('chapter', 'world', 'character', 'timeline', 'document', 'other')",
            name="ck_artifacts_type_valid",
        ),
        sa.CheckConstraint(
            "current_revision >= 0", name="ck_artifacts_current_revision_non_negative"
        ),
        sa.CheckConstraint("version > 0", name="ck_artifacts_version_positive"),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_artifacts_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_artifacts"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_artifacts_workspace_project",
        "project_artifacts",
        ["workspace_id", "project_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "project_artifact_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("content_reference", sa.String(length=500), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_artifact_revisions_number_positive"),
        sa.CheckConstraint(
            "(content_reference IS NULL) = (content_hash IS NULL)",
            name="ck_artifact_revisions_content_pair",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            [f"{SCHEMA}.project_artifacts.id"],
            name="fk_artifact_revisions_artifact",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_artifact_revisions"),
        sa.UniqueConstraint("artifact_id", "revision_number", name="uq_artifact_revisions_number"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_artifact_revisions_scope",
        "project_artifact_revisions",
        ["workspace_id", "project_id", "artifact_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deletion_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'pending_deletion')", name="ck_assets_status_valid"
        ),
        sa.CheckConstraint("current_version > 0", name="ck_assets_current_version_positive"),
        sa.CheckConstraint("version > 0", name="ck_assets_version_positive"),
        sa.CheckConstraint(
            "(status = 'pending_deletion') = "
            "(deletion_marked_at IS NOT NULL AND retention_until IS NOT NULL)",
            name="ck_assets_deletion_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_assets_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_assets_workspace_project",
        "assets",
        ["workspace_id", "project_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "asset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("scan_status", sa.String(length=30), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_asset_versions_number_positive"),
        sa.CheckConstraint("size_bytes > 0", name="ck_asset_versions_size_positive"),
        sa.CheckConstraint(
            "scan_status IN ('not_configured', 'clean', 'rejected', 'failed')",
            name="ck_asset_versions_scan_status_valid",
        ),
        sa.CheckConstraint(
            "processing_status IN ('available', 'missing_object')",
            name="ck_asset_versions_processing_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], [f"{SCHEMA}.assets.id"], name="fk_asset_versions_asset"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_versions"),
        sa.UniqueConstraint("object_key", name="uq_asset_versions_object_key"),
        sa.UniqueConstraint("asset_id", "version_number", name="uq_asset_versions_number"),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "content_hash",
            name="uq_asset_versions_project_hash",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_asset_versions_scope",
        "asset_versions",
        ["workspace_id", "project_id", "asset_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "asset_upload_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("asset_version_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("scan_status", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_upload_sessions_size_positive"),
        sa.CheckConstraint("version_number > 0", name="ck_upload_sessions_version_number_positive"),
        sa.CheckConstraint("version > 0", name="ck_upload_sessions_version_positive"),
        sa.CheckConstraint(
            "scan_status IN ('not_configured', 'clean', 'rejected', 'failed')",
            name="ck_upload_sessions_scan_status_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'object_stored', 'completed', 'failed', "
            "'compensation_required')",
            name="ck_upload_sessions_status_valid",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_upload_sessions"),
        sa.UniqueConstraint("object_key", name="uq_upload_sessions_object_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_upload_sessions_scope_status",
        "asset_upload_sessions",
        ["workspace_id", "status"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0003_projects_assets', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove only execution 07 structures during controlled rollback."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0002_identity_security', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index(
        "ix_upload_sessions_scope_status", table_name="asset_upload_sessions", schema=SCHEMA
    )
    op.drop_table("asset_upload_sessions", schema=SCHEMA)
    op.drop_index("ix_asset_versions_scope", table_name="asset_versions", schema=SCHEMA)
    op.drop_table("asset_versions", schema=SCHEMA)
    op.drop_index("ix_assets_workspace_project", table_name="assets", schema=SCHEMA)
    op.drop_table("assets", schema=SCHEMA)
    op.drop_index(
        "ix_artifact_revisions_scope",
        table_name="project_artifact_revisions",
        schema=SCHEMA,
    )
    op.drop_table("project_artifact_revisions", schema=SCHEMA)
    op.drop_index("ix_artifacts_workspace_project", table_name="project_artifacts", schema=SCHEMA)
    op.drop_table("project_artifacts", schema=SCHEMA)
    op.drop_index("ix_projects_workspace_status", table_name="projects", schema=SCHEMA)
    op.drop_table("projects", schema=SCHEMA)
