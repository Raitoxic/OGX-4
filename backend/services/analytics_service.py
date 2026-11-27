from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.models.task import Task
from backend.models.telemetry import AutonomySignal, InteractionEvent
from backend.orchestration.state_machine import TaskStatus


def compute_user_analytics(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Computes Agent Analytics strictly from actual recorded database interactions.
    Returns explicit zeros / empty distributions when no data exists (never fabricated).
    """
    tasks: List[Task] = db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.asc()).all()
    events: List[InteractionEvent] = (
        db.query(InteractionEvent)
        .filter(InteractionEvent.user_id == user_id)
        .order_by(InteractionEvent.created_at.desc())
        .all()
    )
    signals: List[AutonomySignal] = (
        db.query(AutonomySignal)
        .filter(AutonomySignal.user_id == user_id)
        .order_by(AutonomySignal.created_at.desc())
        .limit(50)
        .all()
    )

    total_tasks = len(tasks)
    collaborative_tasks = [t for t in tasks if t.interaction_mode != "baseline"]
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    task_completion_rate = round((len(completed_tasks) / total_tasks) * 100, 1) if total_tasks else 0.0

    event_counts = Counter(e.event_type for e in events)
    approvals = event_counts["STEP_APPROVED"] + event_counts["PLAN_APPROVED"]
    rejections = event_counts["STEP_REJECTED"]
    decisions = approvals + rejections
    approval_rate = round((approvals / decisions) * 100, 1) if decisions else 0.0
    rejection_rate = round((rejections / decisions) * 100, 1) if decisions else 0.0

    plan_edits = event_counts["STEP_EDITED"] + event_counts["INSTRUCTION_ADDED"]
    artifact_edits = event_counts["ARTIFACT_USER_EDITED"]
    total_modifications = plan_edits + artifact_edits
    modification_freq = round(total_modifications / len(collaborative_tasks), 2) if collaborative_tasks else 0.0

    interventions = (
        event_counts["TASK_INTERRUPTED"]
        + event_counts["TASK_PAUSED"]
        + event_counts["STEP_EDITED"]
        + event_counts["STEP_REJECTED"]
        + event_counts["INSTRUCTION_ADDED"]
        + event_counts["REPLAN_EXECUTED"]
        + event_counts["CHECKPOINT_RESTORED"]
    )
    intervention_freq = round(interventions / len(collaborative_tasks), 2) if collaborative_tasks else 0.0

    autonomy_shifts = [s for s in signals if s.previous_caution != s.new_caution]

    # Daily interaction trend from real events
    by_day: Dict[str, Dict[str, int]] = defaultdict(lambda: {"approvals": 0, "modifications": 0, "interventions": 0})
    for ev in events:
        day_key = ev.created_at.strftime("%Y-%m-%d") if ev.created_at else "unknown"
        if ev.event_type in ("STEP_APPROVED", "PLAN_APPROVED"):
            by_day[day_key]["approvals"] += 1
        if ev.event_type in ("STEP_EDITED", "ARTIFACT_USER_EDITED", "INSTRUCTION_ADDED"):
            by_day[day_key]["modifications"] += 1
        if ev.event_type in ("TASK_INTERRUPTED", "STEP_REJECTED", "REPLAN_EXECUTED", "CHECKPOINT_RESTORED"):
            by_day[day_key]["interventions"] += 1

    timeline = [{"date": k, **v} for k, v in sorted(by_day.items())[-14:]]

    # Event distribution for bar chart
    tracked_types = [
        ("STEP_APPROVED", "Step Approvals"),
        ("STEP_REJECTED", "Step Rejections"),
        ("STEP_EDITED", "Plan Edits"),
        ("TASK_INTERRUPTED", "Interrupts"),
        ("TASK_RESUMED", "Resumes"),
        ("CHECKPOINT_RESTORED", "Rollbacks"),
        ("ARTIFACT_USER_EDITED", "Artifact Edits"),
        ("REPLAN_EXECUTED", "Replans"),
    ]
    event_distribution = [
        {"category": label, "count": event_counts[key]}
        for key, label in tracked_types
    ]

    return {
        "has_data": total_tasks > 0,
        "summary": {
            "total_tasks": total_tasks,
            "vyrox_tasks": len(collaborative_tasks),
            "baseline_tasks": total_tasks - len(collaborative_tasks),
            "completed_tasks": len(completed_tasks),
            "task_completion_rate": task_completion_rate,
            "approvals_count": approvals,
            "rejections_count": rejections,
            "approval_rate": approval_rate,
            "rejection_rate": rejection_rate,
            "total_modifications": total_modifications,
            "modification_frequency_per_task": modification_freq,
            "total_interventions": interventions,
            "intervention_frequency_per_task": intervention_freq,
            "autonomy_adjustments_count": len(autonomy_shifts),
        },
        "event_distribution": event_distribution,
        "timeline": timeline,
        "recent_autonomy_signals": [
            {
                "id": s.id,
                "task_id": s.task_id,
                "signal_type": s.signal_type,
                "step_risk_level": s.step_risk_level,
                "previous_caution": s.previous_caution,
                "new_caution": s.new_caution,
                "reason": s.reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals[:20]
        ],
        "epistemic_note": (
            "All metrics above are calculated exclusively from persisted interaction records. "
            "Approval counts represent behavioural feedback, not proof of user satisfaction or blind trust."
        ),
    }
