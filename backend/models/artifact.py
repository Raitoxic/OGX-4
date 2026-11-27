from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactSection(Base):
    __tablename__ = "artifact_sections"
    __table_args__ = (
        Index("ix_artifact_sections_task_order", "task_id", "section_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    step_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(200), nullable=False)
    ai_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    current_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    authorship: Mapped[str] = mapped_column(String(24), default="ai", nullable=False)  # ai | human | collaborative
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    task = relationship("Task", back_populates="artifact_sections")
    revisions = relationship(
        "ArtifactRevision",
        back_populates="section",
        order_by="ArtifactRevision.version",
        cascade="all, delete-orphan",
    )


class ArtifactRevision(Base):
    __tablename__ = "artifact_revisions"
    __table_args__ = (
        Index("ix_artifact_revisions_section_ver", "section_id", "version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    section_id: Mapped[str] = mapped_column(String(36), ForeignKey("artifact_sections.id", ondelete="CASCADE"), index=True, nullable=False)

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)  # ai | human | rollback | restore
    summary: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    section = relationship("ArtifactSection", back_populates="revisions")
