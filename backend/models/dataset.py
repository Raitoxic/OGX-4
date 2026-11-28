from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DatasetSource(Base):
    """Provenance record for a collected dataset/source (license, version, counts)."""

    __tablename__ = "dataset_sources"
    __table_args__ = (Index("ix_dataset_sources_name_version", "name", "dataset_version", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(String(600), default="", nullable=False)
    license_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    access_level: Mapped[str] = mapped_column(String(24), default="metadata_only", nullable=False)
    quality_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    processing_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DatasetRecord(Base):
    """A single versioned dataset row (schema documented per dataset A–E)."""

    __tablename__ = "dataset_records"
    __table_args__ = (Index("ix_dataset_records_version_split", "dataset_version", "split_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(32), nullable=False)  # A | B | C | D | E
    split_name: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    record_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DatasetSplit(Base):
    """Split methodology + counts for a dataset version (leakage documentation)."""

    __tablename__ = "dataset_splits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(32), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    train_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    val_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    methodology_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ChunkEmbedding(Base):
    """Portable embedding storage (float32 blob). Works on SQLite and PostgreSQL.

    When PostgreSQL + pgvector is configured, a parallel ``Vector`` column/index is
    created by the migration; this blob remains the source of truth for portability.
    """

    __tablename__ = "chunk_embeddings"
    __table_args__ = (Index("ix_chunk_embeddings_model", "embedding_model", "embedding_dim"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pdf_chunks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(200), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class RetrievalLog(Base):
    """Logged retrieval results for evaluation and auditing."""

    __tablename__ = "retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text, default="", nullable=False)
    backend: Mapped[str] = mapped_column(String(16), default="lexical", nullable=False)  # lexical | semantic
    results_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    top_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)