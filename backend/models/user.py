from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # User preferences & autonomy defaults (synchronized with AutonomySetting)
    default_autonomy_mode: Mapped[str] = mapped_column(String(32), default="balanced", nullable=False)
    adaptive_autonomy_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_plan_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_high_risk_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    theme_preference: Mapped[str] = mapped_column(String(16), default="light", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    autonomy_setting = relationship(
        "AutonomySetting",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_active", "user_id", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")


class AutonomySetting(Base):
    __tablename__ = "autonomy_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    default_mode: Mapped[str] = mapped_column(String(32), default="balanced", nullable=False)
    adaptive_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ml_recommendations_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Explicit opt-in consent required before private user interactions can ever be included in ML training
    training_consent_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_plan_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_high_risk_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    caution_threshold_corrections: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    relax_threshold_approvals: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="autonomy_setting")
