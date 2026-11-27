from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InteractionEvent(Base):
    __tablename__ = "interaction_events"
    __table_args__ = (
        Index("ix_interaction_events_task_time", "task_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    step_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)  # human | agent | system
    summary: Mapped[str] = mapped_column(String(400), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    emitted_at_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)

    task = relationship("Task", back_populates="events")


class AutonomySignal(Base):
    __tablename__ = "autonomy_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)

    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    step_risk_level: Mapped[str] = mapped_column(String(16), default="low", nullable=False)
    previous_caution: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    new_caution: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)


class EvaluationResponse(Base):
    __tablename__ = "evaluation_responses"
    __table_args__ = (
        Index("ix_eval_responses_user_mode", "user_id", "interaction_mode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    interaction_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # vyrox | baseline
    scenario_key: Mapped[str] = mapped_column(String(100), default="custom", nullable=False)
    effort_rating: Mapped[int] = mapped_column(Integer, nullable=False)   # 1 (minimal) to 7 (very high)
    trust_rating: Mapped[int] = mapped_column(Integer, nullable=False)    # 1 (low) to 7 (high)
    control_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (low) to 7 (high)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), index=True, nullable=True)

    category: Mapped[str] = mapped_column(String(48), default="general", nullable=False)  # usability | autonomy | accuracy | bug | suggestion
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1..5
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
