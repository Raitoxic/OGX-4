"""VYRO-X research dataset + embedding pipeline

Adds corpus provenance columns and dataset/embedding/retrieval tables. Additive and
backward compatible. The pgvector column/index is created ONLY on PostgreSQL when
pgvector is available; SQLite uses the portable float32 blob in ``chunk_embeddings``.

Revision ID: 0006_dataset_pipeline
Revises: 0005_replan_change
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_dataset_pipeline"
down_revision: Union[str, None] = "0005_replan_change"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend the existing corpus tables (no duplicate document/chunk tables).
    op.add_column("pdf_documents", sa.Column("source_type", sa.String(length=24), nullable=False, server_default="local_pdf"))
    op.add_column("pdf_documents", sa.Column("url", sa.String(length=600), nullable=False, server_default=""))
    op.add_column("pdf_documents", sa.Column("license_name", sa.String(length=200), nullable=False, server_default=""))
    op.add_column("pdf_documents", sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("pdf_documents", sa.Column("access_level", sa.String(length=24), nullable=False, server_default="full_text"))

    op.create_table(
        "dataset_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_url", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("license_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("access_level", sa.String(length=24), nullable=False, server_default="metadata_only"),
        sa.Column("quality_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("processing_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_sources_name_version", "dataset_sources", ["name", "dataset_version"], unique=True)
    op.create_index("ix_dataset_sources_version", "dataset_sources", ["dataset_version"])

    op.create_table(
        "dataset_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("dataset_name", sa.String(length=32), nullable=False),
        sa.Column("split_name", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("record_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_records_version_split", "dataset_records", ["dataset_version", "split_name"])
    op.create_index("ix_dataset_records_version", "dataset_records", ["dataset_version"])
    op.create_index("ix_dataset_records_source_document_id", "dataset_records", ["source_document_id"])

    op.create_table(
        "dataset_splits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("dataset_name", sa.String(length=32), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("train_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("val_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("methodology_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_splits_version", "dataset_splits", ["dataset_version"])

    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("chunk_id", sa.String(length=36), sa.ForeignKey("pdf_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chunk_embeddings_chunk_id", "chunk_embeddings", ["chunk_id"])
    op.create_index("ix_chunk_embeddings_model", "chunk_embeddings", ["embedding_model", "embedding_dim"])

    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("query", sa.Text(), nullable=False, server_default=""),
        sa.Column("backend", sa.String(length=16), nullable=False, server_default="lexical"),
        sa.Column("results_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("top_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_logs_task_id", "retrieval_logs", ["task_id"])

    # pgvector (PostgreSQL only; never pretend SQLite supports it).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
            op.execute("ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS pgvector public.vector(384)")
        except Exception:
            # pgvector not installed — the portable blob column remains authoritative.
            pass


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute("ALTER TABLE chunk_embeddings DROP COLUMN IF EXISTS pgvector")
        except Exception:
            pass
    op.drop_index("ix_retrieval_logs_task_id", table_name="retrieval_logs")
    op.drop_table("retrieval_logs")
    op.drop_index("ix_chunk_embeddings_model", table_name="chunk_embeddings")
    op.drop_index("ix_chunk_embeddings_chunk_id", table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
    op.drop_index("ix_dataset_splits_version", table_name="dataset_splits")
    op.drop_table("dataset_splits")
    op.drop_index("ix_dataset_records_source_document_id", table_name="dataset_records")
    op.drop_index("ix_dataset_records_version", table_name="dataset_records")
    op.drop_index("ix_dataset_records_version_split", table_name="dataset_records")
    op.drop_table("dataset_records")
    op.drop_index("ix_dataset_sources_version", table_name="dataset_sources")
    op.drop_index("ix_dataset_sources_name_version", table_name="dataset_sources")
    op.drop_table("dataset_sources")
    op.drop_column("pdf_documents", "access_level")
    op.drop_column("pdf_documents", "content_hash")
    op.drop_column("pdf_documents", "license_name")
    op.drop_column("pdf_documents", "url")
    op.drop_column("pdf_documents", "source_type")