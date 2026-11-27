"""VYRO-X initial complete relational schema (17 application tables, FKs, indexes)

Revision ID: 0001_vyrox_initial
Revises:
Create Date: 2026-11-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_vyrox_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("default_autonomy_mode", sa.String(32), nullable=False, server_default="balanced"),
        sa.Column("adaptive_autonomy_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_plan_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_high_risk_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("theme_preference", sa.String(16), nullable=False, server_default="light"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_jti", sa.String(64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(255), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_token_jti", "auth_sessions", ["token_jti"], unique=True)
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at"])

    op.create_table(
        "autonomy_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("default_mode", sa.String(32), nullable=False, server_default="balanced"),
        sa.Column("adaptive_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ml_recommendations_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("training_consent_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("require_plan_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_high_risk_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("caution_threshold_corrections", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("relax_threshold_approvals", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_autonomy_settings_user_id", "autonomy_settings", ["user_id"], unique=True)

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False, server_default=""),
        sa.Column("interaction_mode", sa.String(20), nullable=False, server_default="vyrox"),
        sa.Column("provider_mode", sa.String(20), nullable=False, server_default="demo"),
        sa.Column("provider_name", sa.String(64), nullable=False, server_default="vyrox-deterministic-v1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("autonomy_mode", sa.String(32), nullable=False, server_default="balanced"),
        sa.Column("adaptive_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("adaptive_caution_level", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("adaptive_reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("complexity_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("ml_recommended_autonomy", sa.String(32), nullable=True),
        sa.Column("ml_recommendation_confidence", sa.Float(), nullable=True),
        sa.Column("ml_model_version", sa.String(64), nullable=True),
        sa.Column("ml_recommendation_reason", sa.String(360), nullable=False, server_default=""),
        sa.Column("plan_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_activity", sa.String(300), nullable=False, server_default="Task created"),
        sa.Column("is_interruptible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("additional_instructions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_execution_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interruption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plan_edits_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plan_edits_honored_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approval_response_ms_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approval_response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupt_latency_ms_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupt_latency_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rollback_attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rollback_success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("artifact_updates_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("artifact_updates_success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sse_latency_samples_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_user_updated", "tasks", ["user_id", "updated_at"])
    op.create_index("ix_tasks_user_mode", "tasks", ["user_id", "interaction_mode"])

    op.create_table(
        "agent_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("summary", sa.String(300), nullable=False, server_default="Generated execution plan"),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(32), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_plans_task_id", "agent_plans", ["task_id"])
    op.create_index("ix_agent_plans_task_version", "agent_plans", ["task_id", "version_number"])

    op.create_table(
        "execution_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("agent_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="low"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approval_reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_basis", sa.String(300), nullable=False, server_default=""),
        sa.Column("uncertainty_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("sources_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("output_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("partial_output", sa.Text(), nullable=False, server_default=""),
        sa.Column("completed_stages_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("user_modified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_edit_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_execution_steps_task_id", "execution_steps", ["task_id"])
    op.create_index("ix_execution_steps_plan_id", "execution_steps", ["plan_id"])
    op.create_index("ix_execution_steps_task_order", "execution_steps", ["task_id", "step_order"])

    op.create_table(
        "artifact_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(36), nullable=True),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(200), nullable=False),
        sa.Column("ai_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("current_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("authorship", sa.String(24), nullable=False, server_default="ai"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_sections_task_id", "artifact_sections", ["task_id"])
    op.create_index("ix_artifact_sections_step_id", "artifact_sections", ["step_id"])
    op.create_index("ix_artifact_sections_task_order", "artifact_sections", ["task_id", "section_order"])

    op.create_table(
        "artifact_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("artifact_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_type", sa.String(16), nullable=False),
        sa.Column("summary", sa.String(240), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_revisions_task_id", "artifact_revisions", ["task_id"])
    op.create_index("ix_artifact_revisions_section_id", "artifact_revisions", ["section_id"])
    op.create_index("ix_artifact_revisions_section_ver", "artifact_revisions", ["section_id", "version"])

    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("task_status", sa.String(32), nullable=False),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_steps_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_steps_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_checkpoints_task_id", "checkpoints", ["task_id"])
    op.create_index("ix_checkpoints_task_version", "checkpoints", ["task_id", "version_number"])

    op.create_table(
        "interaction_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("summary", sa.String(400), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("emitted_at_ms", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interaction_events_task_id", "interaction_events", ["task_id"])
    op.create_index("ix_interaction_events_user_id", "interaction_events", ["user_id"])
    op.create_index("ix_interaction_events_event_type", "interaction_events", ["event_type"])
    op.create_index("ix_interaction_events_created_at", "interaction_events", ["created_at"])
    op.create_index("ix_interaction_events_task_time", "interaction_events", ["task_id", "created_at"])

    op.create_table(
        "autonomy_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_type", sa.String(32), nullable=False),
        sa.Column("step_risk_level", sa.String(16), nullable=False, server_default="low"),
        sa.Column("previous_caution", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("new_caution", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_autonomy_signals_user_id", "autonomy_signals", ["user_id"])
    op.create_index("ix_autonomy_signals_task_id", "autonomy_signals", ["task_id"])
    op.create_index("ix_autonomy_signals_created_at", "autonomy_signals", ["created_at"])

    op.create_table(
        "evaluation_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interaction_mode", sa.String(20), nullable=False),
        sa.Column("scenario_key", sa.String(100), nullable=False, server_default="custom"),
        sa.Column("effort_rating", sa.Integer(), nullable=False),
        sa.Column("trust_rating", sa.Integer(), nullable=False),
        sa.Column("control_rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_responses_task_id", "evaluation_responses", ["task_id"])
    op.create_index("ix_evaluation_responses_user_id", "evaluation_responses", ["user_id"])
    op.create_index("ix_eval_responses_user_mode", "evaluation_responses", ["user_id", "interaction_mode"])

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(48), nullable=False, server_default="general"),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])
    op.create_index("ix_user_feedback_task_id", "user_feedback", ["task_id"])

    op.create_table(
        "ml_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_version", sa.String(64), nullable=False, unique=True),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="synthetic_demo"),
        sa.Column("file_path", sa.String(400), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("class_distribution_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("split_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("provenance_notes", sa.Text(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_datasets_dataset_version", "ml_datasets", ["dataset_version"], unique=True)

    op.create_table(
        "ml_model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_version", sa.String(64), nullable=False, unique=True),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("dataset_version", sa.String(64), nullable=False),
        sa.Column("dataset_provenance", sa.String(48), nullable=False, server_default="SYNTHETIC_DEMO_DATASET"),
        sa.Column("artifact_path", sa.String(400), nullable=False),
        sa.Column("hyperparameters_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("feature_names_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("random_seed", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("training_time_sec", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("inference_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_model_versions_model_version", "ml_model_versions", ["model_version"], unique=True)
    op.create_index("ix_ml_model_versions_is_active", "ml_model_versions", ["is_active"])

    op.create_table(
        "ml_evaluation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_version_id", sa.String(36), sa.ForeignKey("ml_model_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("split_name", sa.String(32), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("precision_macro", sa.Float(), nullable=False),
        sa.Column("recall_macro", sa.Float(), nullable=False),
        sa.Column("f1_macro", sa.Float(), nullable=False),
        sa.Column("roc_auc_ovr", sa.Float(), nullable=True),
        sa.Column("confusion_matrix_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("class_report_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("baseline_comparison_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_eval_model_split", "ml_evaluation_results", ["model_version_id", "split_name"])

    op.create_table(
        "ml_prediction_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("predicted_autonomy", sa.String(32), nullable=False),
        sa.Column("probabilities_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("features_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("user_actual_mode", sa.String(32), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_prediction_logs_user_id", "ml_prediction_logs", ["user_id"])
    op.create_index("ix_ml_prediction_logs_model_version", "ml_prediction_logs", ["model_version"])


def downgrade() -> None:
    for table in [
        "ml_prediction_logs",
        "ml_evaluation_results",
        "ml_model_versions",
        "ml_datasets",
        "user_feedback",
        "evaluation_responses",
        "autonomy_signals",
        "interaction_events",
        "checkpoints",
        "artifact_revisions",
        "artifact_sections",
        "execution_steps",
        "agent_plans",
        "tasks",
        "autonomy_settings",
        "auth_sessions",
        "users",
    ]:
        op.drop_table(table)
