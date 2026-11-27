from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MLDataset(Base):
    __tablename__ = "ml_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="synthetic_demo", nullable=False)
    file_path: Mapped[str] = mapped_column(String(400), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    class_distribution_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    split_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    provenance_notes: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dataset_provenance: Mapped[str] = mapped_column(String(48), default="SYNTHETIC_DEMO_DATASET", nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(400), nullable=False)
    hyperparameters_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    feature_names_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    training_time_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    inference_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    evaluations = relationship("MLEvaluationResult", back_populates="model_rel", cascade="all, delete-orphan")


class MLEvaluationResult(Base):
    __tablename__ = "ml_evaluation_results"
    __table_args__ = (
        Index("ix_ml_eval_model_split", "model_version_id", "split_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ml_model_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    split_name: Mapped[str] = mapped_column(String(32), nullable=False)  # validation | test | rule_baseline_test
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    precision_macro: Mapped[float] = mapped_column(Float, nullable=False)
    recall_macro: Mapped[float] = mapped_column(Float, nullable=False)
    f1_macro: Mapped[float] = mapped_column(Float, nullable=False)
    roc_auc_ovr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confusion_matrix_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    class_report_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    baseline_comparison_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    model_rel = relationship("MLModelVersion", back_populates="evaluations")


class MLPredictionLog(Base):
    __tablename__ = "ml_prediction_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), index=True, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    predicted_autonomy: Mapped[str] = mapped_column(String(32), nullable=False)
    probabilities_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    features_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    user_actual_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    inference_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
