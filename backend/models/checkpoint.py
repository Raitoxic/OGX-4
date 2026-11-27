from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    __table_args__ = (
        Index("ix_checkpoints_task_version", "task_id", "version_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_steps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_steps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    task = relationship("Task", back_populates="checkpoints")
