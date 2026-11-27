from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.models.ml_registry import MLDataset, MLEvaluationResult, MLModelVersion, MLPredictionLog
from backend.models.task import ExecutionStep, Task
from backend.models.telemetry import InteractionEvent
from backend.models.user import User
from backend.orchestration.state_machine import TaskStatus
from ml.inference.predictor import supervision_predictor

RISK_ENCODING = {"low": 0, "medium": 1, "high": 2}


def estimate_task_complexity(prompt: str, step_count: int = 5) -> float:
    words = len(prompt.split())
    score = 0.25 + min(0.45, words / 90.0) + min(0.30, max(0, step_count - 2) * 0.06)
    return round(min(1.0, max(0.1, score)), 3)


def extract_live_features(db: Session, user: User, task: Task) -> Dict[str, Any]:
    """Extracts the 10 model input features strictly from persisted user & task database records."""
    user_tasks: List[Task] = db.query(Task).filter(Task.user_id == user.id).all()
    events: List[InteractionEvent] = (
        db.query(InteractionEvent).filter(InteractionEvent.user_id == user.id).all()
    )

    approvals = sum(1 for e in events if e.event_type in ("STEP_APPROVED", "PLAN_APPROVED"))
    rejections = sum(1 for e in events if e.event_type == "STEP_REJECTED")
    corrections = sum(1 for e in events if e.event_type in ("ARTIFACT_USER_EDITED", "REPLAN_EXECUTED", "INSTRUCTION_ADDED"))
    interruptions = sum(t.interruption_count for t in user_tasks)
    step_edits = sum(1 for e in events if e.event_type == "STEP_EDITED")

    finished = [t for t in user_tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)]
    completed = [t for t in finished if t.status == TaskStatus.COMPLETED]
    prev_completion_rate = round(len(completed) / len(finished), 4) if finished else 0.85

    total_recovered = sum(t.recovery_count for t in user_tasks)
    historical_recovery_rate = (
        round(min(1.0, total_recovered / interruptions), 4) if interruptions > 0 else 0.90
    )

    intervention_types = {
        "TASK_INTERRUPTED",
        "TASK_PAUSED",
        "STEP_EDITED",
        "STEP_REJECTED",
        "INSTRUCTION_ADDED",
        "REPLAN_EXECUTED",
        "CHECKPOINT_RESTORED",
    }
    total_interventions = sum(1 for e in events if e.event_type in intervention_types)
    n_tasks = max(1, len(user_tasks))
    intervention_frequency = round(total_interventions / n_tasks, 4)

    steps = (
        db.query(ExecutionStep).filter(ExecutionStep.task_id == task.id).all()
    )
    max_risk = max((RISK_ENCODING.get(s.risk_level, 1) for s in steps), default=1)
    complexity = task.complexity_score or estimate_task_complexity(task.prompt, len(steps) or 5)

    return {
        "prev_approvals": approvals,
        "prev_rejections": rejections,
        "user_corrections": corrections,
        "interruptions_count": interruptions,
        "manual_step_edits": step_edits,
        "task_complexity": complexity,
        "task_risk_level": max_risk,
        "prev_completion_rate": prev_completion_rate,
        "intervention_frequency": intervention_frequency,
        "historical_recovery_rate": historical_recovery_rate,
    }


def predict_supervision_for_task(
    db: Session,
    user: User,
    task: Task,
    log_prediction: bool = True,
    commit: bool = True,
) -> Dict[str, Any]:
    """Runs serialized ML inference and logs advisory prediction without overriding manual user settings."""
    features = extract_live_features(db, user, task)
    pred = supervision_predictor.predict(features)

    task.ml_recommended_autonomy = pred["recommended_autonomy"]
    task.ml_recommendation_confidence = pred["confidence"]
    task.ml_model_version = pred["model_version"]
    task.ml_recommendation_reason = pred["explanation"][:350]

    if log_prediction and pred["available"]:
        db.add(
            MLPredictionLog(
                user_id=user.id,
                task_id=task.id,
                model_version=pred["model_version"],
                predicted_autonomy=pred["recommended_autonomy"],
                probabilities_json=json.dumps(pred["probabilities"]),
                features_json=json.dumps(features),
                user_actual_mode=task.autonomy_mode,
                inference_latency_ms=pred["inference_latency_ms"],
            )
        )

    if commit:
        db.commit()
    else:
        db.flush()

    return {**pred, "features_used": features}


def get_ml_status_and_monitoring(db: Session, user: User) -> Dict[str, Any]:
    report = supervision_predictor.get_latest_report()
    active_mv = (
        db.query(MLModelVersion)
        .filter(MLModelVersion.is_active.is_(True))
        .order_by(MLModelVersion.created_at.desc())
        .first()
    )
    all_versions = (
        db.query(MLModelVersion)
        .order_by(MLModelVersion.created_at.desc())
        .limit(10)
        .all()
    )
    datasets = db.query(MLDataset).order_by(MLDataset.created_at.desc()).limit(5).all()
    logs = (
        db.query(MLPredictionLog)
        .filter(MLPredictionLog.user_id == user.id)
        .order_by(MLPredictionLog.created_at.desc())
        .limit(50)
        .all()
    )

    total_preds = len(logs)
    agreements = sum(1 for l in logs if l.user_actual_mode and l.predicted_autonomy == l.user_actual_mode)
    avg_live_latency = (
        round(sum(l.inference_latency_ms for l in logs) / total_preds, 3) if total_preds else None
    )

    db_eval_rows = []
    if active_mv:
        evals = (
            db.query(MLEvaluationResult)
            .filter(MLEvaluationResult.model_version_id == active_mv.id)
            .all()
        )
        db_eval_rows = [
            {
                "split_name": e.split_name,
                "accuracy": e.accuracy,
                "precision_macro": e.precision_macro,
                "recall_macro": e.recall_macro,
                "f1_macro": e.f1_macro,
                "roc_auc_ovr": e.roc_auc_ovr,
                "confusion_matrix": json.loads(e.confusion_matrix_json or "[]"),
                "class_report": json.loads(e.class_report_json or "{}"),
            }
            for e in evals
        ]

    return {
        "model_available": bool(report and report.get("selected_model")),
        "dataset_provenance": report["dataset"]["dataset_provenance"] if report else "UNAVAILABLE",
        "provenance_disclosure": (
            "Trained and evaluated on a clearly labelled synthetic demonstration dataset (SYNTHETIC_DEMO_DATASET). "
            "Not validated on real-world production users. Predictions are advisory only."
        ),
        "latest_report": report,
        "db_evaluations": db_eval_rows,
        "registered_versions": [
            {
                "model_version": mv.model_version,
                "algorithm": mv.algorithm,
                "dataset_version": mv.dataset_version,
                "dataset_provenance": mv.dataset_provenance,
                "training_time_sec": mv.training_time_sec,
                "inference_latency_ms": mv.inference_latency_ms,
                "is_active": mv.is_active,
                "created_at": mv.created_at.isoformat() if mv.created_at else None,
            }
            for mv in all_versions
        ],
        "registered_datasets": [
            {
                "dataset_version": ds.dataset_version,
                "source_type": ds.source_type,
                "sample_count": ds.sample_count,
                "class_distribution": json.loads(ds.class_distribution_json or "{}"),
                "sha256_hash": ds.sha256_hash,
                "provenance_notes": ds.provenance_notes,
            }
            for ds in datasets
        ],
        "monitoring": {
            "total_predictions_logged": total_preds,
            "user_agreement_rate_pct": round((agreements / total_preds) * 100, 1) if total_preds else None,
            "avg_live_inference_latency_ms": avg_live_latency,
            "recent_predictions": [
                {
                    "id": l.id,
                    "task_id": l.task_id,
                    "model_version": l.model_version,
                    "predicted_autonomy": l.predicted_autonomy,
                    "user_actual_mode": l.user_actual_mode,
                    "probabilities": json.loads(l.probabilities_json or "{}"),
                    "inference_latency_ms": l.inference_latency_ms,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs[:15]
            ],
        },
    }
