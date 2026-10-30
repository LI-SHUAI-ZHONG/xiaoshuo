"""Add rebuildable knowledge ingestion, provenance, and pgvector projections.

Revision ID: 0007_knowledge_pipeline
Revises: 0006_agent_runtime
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

revision: str = "0007_knowledge_pipeline"
down_revision: str | None = "0006_agent_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "accos"


class Vector8(UserDefinedType[str]):
    """Migration-local vector base type compatible with the test shim."""

    cache_ok = True

    def get_col_spec(self, **_kw: object) -> str:
        return "vector"


def upgrade() -> None:
    """Create knowledge source-of-truth records and replaceable projections."""
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("asset_version_id", sa.Uuid(), nullable=False),
        sa.Column("asset_version_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("content_locator", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "asset_version_number > 0", name="ck_knowledge_sources_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_knowledge_sources_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_sources"),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "asset_version_id",
            name="uq_knowledge_sources_asset_version",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_sources_scope_asset",
        "knowledge_sources",
        ["workspace_id", "project_id", "asset_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="fk_knowledge_documents_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_documents"),
        sa.UniqueConstraint(
            "workspace_id", "project_id", "asset_id", name="uq_knowledge_documents_asset"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_documents_scope",
        "knowledge_documents",
        ["workspace_id", "project_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_knowledge_versions_number_positive"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'extracting', 'normalized', 'chunked', 'embedded', "
            "'indexed', 'verifying', 'ready', 'failed')",
            name="ck_knowledge_versions_status_valid",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'not_configured', 'rejected')",
            name="ck_knowledge_versions_verification_valid",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            [f"{SCHEMA}.knowledge_documents.id"],
            name="fk_knowledge_versions_document",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.knowledge_sources.id"],
            name="fk_knowledge_versions_source",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_document_versions"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_knowledge_versions_number"),
        sa.UniqueConstraint("source_id", name="uq_knowledge_versions_source"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_versions_scope_ready",
        "knowledge_document_versions",
        ["workspace_id", "project_id", "active", "status"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_knowledge_chunks_ordinal_non_negative"),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.knowledge_sources.id"],
            name="fk_knowledge_chunks_source",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            [f"{SCHEMA}.knowledge_document_versions.id"],
            name="fk_knowledge_chunks_version",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_chunks"),
        sa.UniqueConstraint(
            "document_version_id", "ordinal", name="uq_knowledge_chunks_version_ordinal"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_chunks_scope_version",
        "knowledge_chunks",
        ["workspace_id", "project_id", "document_version_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_embedding_refs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("embedder_id", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint("dimensions > 0", name="ck_knowledge_embeddings_dimensions_positive"),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            [f"{SCHEMA}.knowledge_chunks.id"],
            name="fk_knowledge_embeddings_chunk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_embedding_refs"),
        sa.UniqueConstraint("chunk_id", "embedder_id", name="uq_knowledge_embeddings_chunk_model"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_embeddings_scope_version",
        "knowledge_embedding_refs",
        ["workspace_id", "project_id", "document_version_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_vector_index",
        sa.Column("embedding_ref_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector8(), nullable=False),
        sa.ForeignKeyConstraint(
            ["embedding_ref_id"],
            [f"{SCHEMA}.knowledge_embedding_refs.id"],
            name="fk_knowledge_vectors_embedding",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("embedding_ref_id", name="pk_knowledge_vector_index"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_vectors_scope_version",
        "knowledge_vector_index",
        ["workspace_id", "project_id", "document_version_id"],
        schema=SCHEMA,
    )
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector' AND typtype = 'b') THEN "
        "ALTER TABLE accos.knowledge_vector_index ALTER COLUMN embedding "
        "TYPE vector(8) USING embedding::text::vector(8); "
        "CREATE INDEX ix_knowledge_vectors_cosine ON accos.knowledge_vector_index "
        "USING hnsw (embedding vector_cosine_ops); "
        "ELSE CREATE INDEX ix_knowledge_vectors_cosine "
        "ON accos.knowledge_vector_index (embedding); END IF; END $$"
    )
    op.create_table(
        "knowledge_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("asset_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("locator", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.knowledge_sources.id"],
            name="fk_knowledge_citations_source",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            [f"{SCHEMA}.knowledge_documents.id"],
            name="fk_knowledge_citations_document",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            [f"{SCHEMA}.knowledge_document_versions.id"],
            name="fk_knowledge_citations_version",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            [f"{SCHEMA}.knowledge_chunks.id"],
            name="fk_knowledge_citations_chunk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_citations"),
        sa.UniqueConstraint("chunk_id", name="uq_knowledge_citations_chunk_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_citations_scope_chunk",
        "knowledge_citations",
        ["workspace_id", "project_id", "chunk_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("from_kind", sa.String(length=40), nullable=False),
        sa.Column("from_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=40), nullable=False),
        sa.Column("to_kind", sa.String(length=40), nullable=False),
        sa.Column("to_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "relation IN ('source_of', 'contains', 'cites', 'derived_from')",
            name="ck_knowledge_edges_relation_valid",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_edges"),
        sa.UniqueConstraint(
            "document_version_id",
            "from_kind",
            "from_id",
            "relation",
            "to_kind",
            "to_id",
            name="uq_knowledge_edges_relation",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_edges_scope_version",
        "knowledge_edges",
        ["workspace_id", "project_id", "document_version_id"],
        schema=SCHEMA,
    )
    op.create_table(
        "knowledge_ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("verification_policy", sa.String(length=30), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("failed_stage", sa.String(length=30), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("attempt > 0", name="ck_knowledge_runs_attempt_positive"),
        sa.CheckConstraint("version > 0", name="ck_knowledge_runs_version_positive"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'extracting', 'normalized', 'chunked', 'embedded', "
            "'indexed', 'verifying', 'ready', 'failed')",
            name="ck_knowledge_runs_status_valid",
        ),
        sa.CheckConstraint(
            "verification_policy IN ('not_required', 'required')",
            name="ck_knowledge_runs_policy_valid",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'not_configured', 'rejected')",
            name="ck_knowledge_runs_verification_valid",
        ),
        sa.CheckConstraint(
            "(status = 'failed') = (failed_stage IS NOT NULL AND error_code IS NOT NULL)",
            name="ck_knowledge_runs_failure_details",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.knowledge_sources.id"],
            name="fk_knowledge_runs_source",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            [f"{SCHEMA}.knowledge_documents.id"],
            name="fk_knowledge_runs_document",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            [f"{SCHEMA}.knowledge_document_versions.id"],
            name="fk_knowledge_runs_version",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            [f"{SCHEMA}.workflow_runs.id"],
            name="fk_knowledge_runs_workflow",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_ingestion_runs"),
        sa.UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_knowledge_runs_idempotency"
        ),
        sa.UniqueConstraint("source_id", name="uq_knowledge_runs_source"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_knowledge_runs_scope_status",
        "knowledge_ingestion_runs",
        ["workspace_id", "project_id", "status"],
        schema=SCHEMA,
    )
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0007_knowledge_pipeline', "
        "updated_at = now() WHERE component = 'accos-core'"
    )


def downgrade() -> None:
    """Remove knowledge-owned tables while preserving assets and runtime modules."""
    op.execute(
        "UPDATE accos.schema_metadata SET revision = '0006_agent_runtime', "
        "updated_at = now() WHERE component = 'accos-core'"
    )
    op.drop_index(
        "ix_knowledge_runs_scope_status",
        table_name="knowledge_ingestion_runs",
        schema=SCHEMA,
    )
    op.drop_table("knowledge_ingestion_runs", schema=SCHEMA)
    op.drop_index("ix_knowledge_edges_scope_version", table_name="knowledge_edges", schema=SCHEMA)
    op.drop_table("knowledge_edges", schema=SCHEMA)
    op.drop_index(
        "ix_knowledge_citations_scope_chunk",
        table_name="knowledge_citations",
        schema=SCHEMA,
    )
    op.drop_table("knowledge_citations", schema=SCHEMA)
    op.drop_index("ix_knowledge_vectors_cosine", table_name="knowledge_vector_index", schema=SCHEMA)
    op.drop_index(
        "ix_knowledge_vectors_scope_version",
        table_name="knowledge_vector_index",
        schema=SCHEMA,
    )
    op.drop_table("knowledge_vector_index", schema=SCHEMA)
    op.drop_index(
        "ix_knowledge_embeddings_scope_version",
        table_name="knowledge_embedding_refs",
        schema=SCHEMA,
    )
    op.drop_table("knowledge_embedding_refs", schema=SCHEMA)
    op.drop_index("ix_knowledge_chunks_scope_version", table_name="knowledge_chunks", schema=SCHEMA)
    op.drop_table("knowledge_chunks", schema=SCHEMA)
    op.drop_index(
        "ix_knowledge_versions_scope_ready",
        table_name="knowledge_document_versions",
        schema=SCHEMA,
    )
    op.drop_table("knowledge_document_versions", schema=SCHEMA)
    op.drop_index("ix_knowledge_documents_scope", table_name="knowledge_documents", schema=SCHEMA)
    op.drop_table("knowledge_documents", schema=SCHEMA)
    op.drop_index("ix_knowledge_sources_scope_asset", table_name="knowledge_sources", schema=SCHEMA)
    op.drop_table("knowledge_sources", schema=SCHEMA)
