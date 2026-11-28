from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PdfDocument(Base):
    """An ingested local PDF dataset document (Phase 6).

    Stores only verified bibliographic metadata; unknown fields stay ``None`` and
    are never fabricated. Extracted text is split into ``PdfChunk`` rows.
    """

    __tablename__ = "pdf_documents"
    __table_args__ = (Index("ix_pdf_documents_filename", "filename", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    authors: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    year: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    doi: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    venue: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="indexed", nullable=False)  # indexed | failed
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    chunks = relationship(
        "PdfChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class PdfChunk(Base):
    """A searchable text chunk from a PDF page (page number preserved)."""

    __tablename__ = "pdf_chunks"
    __table_args__ = (Index("ix_pdf_chunks_document_page", "document_id", "page"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pdf_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    document = relationship("PdfDocument", back_populates="chunks")