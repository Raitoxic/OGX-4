from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_updated", "user_id", "updated_at"),
        Index("ix_tasks_user_mode", "user_id", "interaction_mode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    # 'vyrox' (collaborative) or 'baseline' (conventional prompt-and-wait); 'hai' accepted as legacy alias
    interaction_mode: Mapped[str] = mapped_column(String(20), default="vyrox", nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(20), default="demo", nullable=False)  # demo | live
    provider_name: Mapped[str] = mapped_column(String(64), default="vyrox-deterministic-v1", nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True, nullable=False)
    autonomy_mode: Mapped[str] = mapped_column(String(32), default="balanced", nullable=False)
    adaptive_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    adaptive_caution_level: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    adaptive_reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)

    # ML Supervision Prediction advisory fields (never overrides manual controls or high-risk gates)
    complexity_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    ml_recommended_autonomy: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ml_recommendation_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ml_recommendation_reason: Mapped[str] = mapped_column(String(360), default="", nullable=False)

    plan_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_activity: Mapped[str] = mapped_column(String(300), default="Task created", nullable=False)
    is_interruptible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    additional_instructions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Research attribution state (Phase 2). Disabled by default.
    research_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    research_status: Mapped[str] = mapped_column(String(32), default="disabled", nullable=False)
    research_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    research_used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    research_retrieved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Full research provenance (additive, backward compatible). Stored as JSON so
    # used vs. retrieved-but-unused sources and their honest access status survive
    # across edits, replanning, checkpoints, and export. Never fabricated.
    research_used_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    research_retrieved_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    citation_style: Mapped[str] = mapped_column(String(16), default="simple", nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_execution_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scientific evaluation operational telemetry
    interruption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recovery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plan_edits_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plan_edits_honored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    approval_response_ms_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approval_response_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interrupt_latency_ms_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interrupt_latency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rollback_attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rollback_success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    artifact_updates_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    artifact_updates_success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sse_latency_samples_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="tasks")
    plans = relationship(
        "AgentPlan",
        back_populates="task",
        order_by="AgentPlan.version_number",
        cascade="all, delete-orphan",
    )
    steps = relationship(
        "ExecutionStep",
        back_populates="task",
        order_by="ExecutionStep.step_order",
        cascade="all, delete-orphan",
    )
    artifact_sections = relationship(
        "ArtifactSection",
        back_populates="task",
        order_by="ArtifactSection.section_order",
        cascade="all, delete-orphan",
    )
    checkpoints = relationship(
        "Checkpoint",
        back_populates="task",
        order_by="Checkpoint.version_number",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "InteractionEvent",
        back_populates="task",
        order_by="InteractionEvent.created_at",
        cascade="all, delete-orphan",
    )


class AgentPlan(Base):
    __tablename__ = "agent_plans"
    __table_args__ = (
        Index("ix_agent_plans_task_version", "task_id", "version_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active | superseded | rolled_back
    summary: Mapped[str] = mapped_column(String(300), default="Generated execution plan", nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(32), default="agent", nullable=False)  # agent | replan | rollback
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    task = relationship("Task", back_populates="plans")
    steps = relationship("ExecutionStep", back_populates="plan")


class ExecutionStep(Base):
    __tablename__ = "execution_steps"
    __table_args__ = (
        Index("ix_execution_steps_task_order", "task_id", "step_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("agent_plans.id", ondelete="SET NULL"), index=True, nullable=True
    )

    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), default="low", nullable=False)  # low | medium | high

    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    approval_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    confidence_basis: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    uncertainty_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    output_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    partial_output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    completed_stages_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    user_modified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_edit_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Replan diff marker: "" | added | modified | removed | unchanged
    replan_change: Mapped[str] = mapped_column(String(16), default="", nullable=False)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    task = relationship("Task", back_populates="steps")
    plan = relationship("AgentPlan", back_populates="steps")
