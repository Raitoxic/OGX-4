from __future__ import annotations

from typing import List, Tuple

from sqlalchemy.orm import Session

from backend.models.task import ExecutionStep, Task
from backend.models.telemetry import AutonomySignal
from backend.models.user import User
from backend.orchestration.state_machine import StepStatus
from backend.services.history_service import record_event
from backend.streaming.broker import sse_broker

CORRECTIVE_SIGNALS = {"reject", "step_edit", "interrupt", "replan"}


def evaluate_step_approval(
    task: Task,
    step: ExecutionStep,
    user: User,
) -> Tuple[bool, str]:
    """
    Transparent rule-based autonomy gate.
    Always enforces safety invariants and respects manual user mode overrides.
    """
    if step.approved_by_user:
        return (False, "Already explicitly approved by user.")

    if step.status == StepStatus.REJECTED:
        return (True, "Previously rejected step requires explicit human review and approval.")

    if step.risk_level == "high":
        return (True, "Safety invariant: high-impact actions always require explicit human approval.")

    mode = task.autonomy_mode or user.default_autonomy_mode or "balanced"
    caution = task.adaptive_caution_level if task.adaptive_enabled else "normal"

    if mode == "supervised":
        return (True, "Supervised Mode: every execution step requires human approval.")

    if mode == "balanced":
        if caution == "elevated_caution":
            return (
                True,
                f"Adaptive Balanced Mode (elevated caution): {task.adaptive_reason or 'recent corrections increased check-ins'}.",
            )
        if step.risk_level == "medium":
            return (True, "Balanced Mode: medium-risk steps request human confirmation.")
        if caution == "relaxed":
            return (False, "Adaptive Balanced Mode: consecutive accepted low-risk steps allow smooth progression.")
        return (False, "Balanced Mode: low-risk step auto-proceeds with live interrupt available.")

    # higher_autonomy
    if caution == "elevated_caution" and step.risk_level == "medium":
        return (
            True,
            f"Higher Autonomy (adaptive caution): {task.adaptive_reason or 'recent corrections triggered confirmation for medium-risk step'}.",
        )
    return (False, "Higher Autonomy Mode: low/medium-risk step proceeds automatically; high-risk actions remain gated.")


def apply_policy_to_pending_steps(task: Task, user: User) -> None:
    for step in task.steps:
        if step.status in (StepStatus.COMPLETED, StepStatus.RUNNING):
            continue
        req, reason = evaluate_step_approval(task, step, user)
        step.requires_approval = req
        step.approval_reason = reason


def record_signal_and_adapt(
    db: Session,
    user: User,
    task: Task,
    signal_type: str,
    step_risk_level: str = "low",
    note: str = "",
) -> AutonomySignal:
    """
    Records behavioural interaction feedback (NOT assumed to equal user trust)
    and transparently updates adaptive caution policy when adaptive autonomy is enabled.
    """
    prev_caution = task.adaptive_caution_level
    new_caution = prev_caution
    reason = note or f"Recorded behavioural signal: {signal_type}"

    recent_signals: List[AutonomySignal] = (
        db.query(AutonomySignal)
        .filter(AutonomySignal.user_id == user.id)
        .order_by(AutonomySignal.created_at.desc())
        .limit(7)
        .all()
    )
    # Build window including the incoming signal
    window_types = [signal_type] + [s.signal_type for s in recent_signals]

    if task.adaptive_enabled:
        recent_5 = window_types[:5]
        corrective_in_5 = sum(1 for t in recent_5 if t in CORRECTIVE_SIGNALS)

        trailing_approvals = 0
        for t in window_types:
            if t == "approve":
                trailing_approvals += 1
            else:
                break

        if signal_type == "reject":
            new_caution = "elevated_caution"
            reason = "Step rejected — increased check-in frequency to verify upcoming proposals."
        elif corrective_in_5 >= 2:
            new_caution = "elevated_caution"
            reason = f"{corrective_in_5} recent corrections/interruptions detected — temporarily requesting confirmation on low-risk steps."
        elif prev_caution == "elevated_caution" and trailing_approvals >= 3:
            new_caution = "normal"
            reason = "3 consecutive unedited approvals — returning from elevated caution to normal balanced gating."
        elif prev_caution in ("normal", "relaxed") and trailing_approvals >= 3:
            new_caution = "relaxed"
            reason = "3+ consecutive accepted low-risk steps — reducing routine prompts while preserving high-risk gates."
    else:
        reason = f"Adaptive adjustment paused by user (manual {task.autonomy_mode} override active)."

    signal = AutonomySignal(
        user_id=user.id,
        task_id=task.id,
        signal_type=signal_type,
        step_risk_level=step_risk_level,
        previous_caution=prev_caution,
        new_caution=new_caution,
        reason=reason,
    )
    db.add(signal)

    if new_caution != prev_caution:
        task.adaptive_caution_level = new_caution
        task.adaptive_reason = reason
        apply_policy_to_pending_steps(task, user)
        record_event(
            db,
            task_id=task.id,
            user_id=user.id,
            event_type="AUTONOMY_ADJUSTED",
            actor="system",
            summary=f"Adaptive autonomy shifted from {prev_caution} to {new_caution}: {reason}",
            payload={
                "previous_caution": prev_caution,
                "new_caution": new_caution,
                "signal_type": signal_type,
                "reason": reason,
            },
        )
        sse_broker.publish(
            task.id,
            "autonomy_adjusted",
            {
                "autonomy_mode": task.autonomy_mode,
                "adaptive_enabled": task.adaptive_enabled,
                "adaptive_caution_level": task.adaptive_caution_level,
                "adaptive_reason": task.adaptive_reason,
            },
        )
    elif task.adaptive_enabled and not task.adaptive_reason:
        task.adaptive_reason = reason

    db.flush()
    return signal
