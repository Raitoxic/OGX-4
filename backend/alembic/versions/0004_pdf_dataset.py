"""VYRO-X local PDF dataset tables

Adds ``pdf_documents`` and ``pdf_chunks`` for the local PDF research corpus.
Additive and backward compatible.

Revision ID: 0004_pdf_dataset
Revises: 0003_research_references
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_pdf_dataset"
down_revision: Union[str, None] = "0003_research_references"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pdf_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("authors", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("year", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("doi", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("venue", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="indexed"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pdf_documents_filename", "pdf_documents", ["filename"], unique=True)
    op.create_table(
        "pdf_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pdf_chunks_document_id", "pdf_chunks", ["document_id"])
    op.create_index("ix_pdf_chunks_document_page", "pdf_chunks", ["document_id", "page"])


def downgrade() -> None:
    op.drop_index("ix_pdf_chunks_document_page", table_name="pdf_chunks")
    op.drop_index("ix_pdf_chunks_document_id", table_name="pdf_chunks")
    op.drop_table("pdf_chunks")
    op.drop_index("ix_pdf_documents_filename", table_name="pdf_documents")
    op.drop_table("pdf_documents")