from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.agents.llm_provider import get_agent_provider
from backend.autonomy.service import apply_policy_to_pending_steps, record_signal_and_adapt
from backend.checkpoints.service import create_checkpoint
from backend.execution.runner import execution_manager
from backend.models.task import ExecutionStep, Task
from backend.models.user import User
from backend.orchestration.state_machine import (
    StepStatus,
    TaskStatus,
    validate_task_transition,
)
from backend.services.history_service import record_event
from backend.streaming.broker import sse_broker


def start_task_execution(db: Session, task: Task, user: User) -> Task:
    if task.interaction_mode == "baseline":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baseline tasks run as a single pass upon creation.",
        )
    if execution_manager.is_running(task.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is already executing.",
        )
    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed tasks cannot be started again without rolling back to a checkpoint.",
        )
    if task.status in (TaskStatus.INTERRUPTED, TaskStatus.PAUSED, TaskStatus.ROLLED_BACK, TaskStatus.FAILED):
        return resume_task_execution(db, task, user)

    validate_task_transition(task.status, TaskStatus.RUNNING)
    if not task.plan_approved:
        task.plan_approved = True
        record_event(
            db,
            task_id=task.id,
            user_id=user.id,
            event_type="PLAN_APPROVED",
            actor="human",
            summary="Approved execution plan and started task execution.",
        )

    # If the very first pending step was explicitly waiting approval, approve it when user clicks Start
    first_waiting = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.task_id == task.id, ExecutionStep.status == StepStatus.AWAITING_APPROVAL)
        .order_by(ExecutionStep.step_order.asc())
        .first()
    )
    if first_waiting:
        first_waiting.approved_by_user = True
        first_waiting.status = StepStatus.PENDING

    task.status = TaskStatus.RUNNING
    task.current_activity = "Starting execution..."
    db.commit()
    db.refresh(task)

    execution_manager.launch(task.id, user.id)
    return task


async def pause_task_execution(db: Session, task: Task, user: User) -> Task:
    if execution_manager.is_running(task.id):
        await execution_manager.request_pause(task.id)
        db.expire_all()
        refreshed = db.query(Task).filter(Task.id == task.id).first()
        return refreshed or task

    validate_task_transition(task.status, TaskStatus.PAUSED)
    task.status = TaskStatus.PAUSED
    task.current_activity = "Execution paused. Edit plan or click Resume to continue."
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="TASK_PAUSED",
        actor="human",
        summary="Paused task execution.",
    )
    create_checkpoint(db, task=task, user_id=user.id, trigger_type="pause", label="Manual pause checkpoint", commit=False)
    db.commit()
    db.refresh(task)
    sse_broker.publish(task.id, "task_state_changed", {"status": task.status, "current_activity": task.current_activity})
    return task


async def interrupt_task_execution(db: Session, task: Task, user: User) -> Dict[str, Any]:
    t0 = time.perf_counter()
    if execution_manager.is_running(task.id):
        result = await execution_manager.request_interrupt(task.id)
        elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
        db.expire_all()
        refreshed = db.query(Task).filter(Task.id == task.id).first()
        if refreshed:
            refreshed.interrupt_latency_ms_total += elapsed_ms
            refreshed.interrupt_latency_count += 1
            db.commit()
            db.refresh(refreshed)
        return {
            "task": refreshed or task,
            "deferred_atomic": result.get("deferred_atomic", False),
            "interrupt_latency_ms": elapsed_ms,
            "message": (
                f"Interrupt safely completed after atomic write ({elapsed_ms} ms); state preserved in checkpoint."
                if result.get("deferred_atomic")
                else f"Execution interrupted safely in {elapsed_ms} ms and saved to persistent checkpoint."
            ),
        }

    if task.status == TaskStatus.INTERRUPTED:
        return {"task": task, "deferred_atomic": False, "message": "Task is already interrupted."}

    validate_task_transition(task.status, TaskStatus.INTERRUPTED)
    task.status = TaskStatus.INTERRUPTED
    task.interruption_count += 1
    task.current_activity = "Task interrupted by user. Saved state to checkpoint."
    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="interrupt",
        step_risk_level="low",
        note="User triggered manual interrupt",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="TASK_INTERRUPTED",
        actor="human",
        summary="User interrupted task and saved checkpoint.",
    )
    create_checkpoint(
        db,
        task=task,
        user_id=user.id,
        trigger_type="interrupt",
        label="Manual interrupt checkpoint",
        commit=False,
    )
    db.commit()
    db.refresh(task)
    sse_broker.publish(task.id, "task_interrupted", {"status": task.status, "current_activity": task.current_activity})
    return {"task": task, "deferred_atomic": False, "message": "Task interrupted and checkpoint persisted."}


def resume_task_execution(db: Session, task: Task, user: User) -> Task:
    if execution_manager.is_running(task.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is already running.")
    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed task cannot be resumed directly. Restore an earlier checkpoint first.",
        )

    recovering = task.status in (TaskStatus.INTERRUPTED, TaskStatus.ROLLED_BACK, TaskStatus.FAILED)
    if task.status == TaskStatus.AWAITING_APPROVAL:
        validate_task_transition(task.status, TaskStatus.RUNNING)
        task.plan_approved = True
    else:
        validate_task_transition(task.status, TaskStatus.RESUMING)
        task.status = TaskStatus.RESUMING

    if recovering:
        task.recovery_count += 1

    # Reset any FAILED or INTERRUPTED/PAUSED step back to PENDING while keeping COMPLETED steps intact
    for step in task.steps:
        if step.status in (StepStatus.INTERRUPTED, StepStatus.PAUSED, StepStatus.FAILED):
            step.status = StepStatus.PENDING

    task.plan_approved = True
    task.current_activity = "Resuming from saved checkpoint without restarting completed steps..."
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="TASK_RESUMED",
        actor="human",
        summary="Resumed execution from saved state (preserving all completed steps).",
        payload={"recovered_from_interruption": recovering},
    )
    db.commit()
    db.refresh(task)

    sse_broker.publish(task.id, "task_resumed", {"status": task.status, "current_activity": task.current_activity})
    execution_manager.launch(task.id, user.id)
    return task


def approve_action(
    db: Session,
    task: Task,
    user: User,
    step_id: Optional[str] = None,
    auto_continue: bool = True,
) -> Task:
    if step_id:
        step = (
            db.query(ExecutionStep)
            .filter(ExecutionStep.id == step_id, ExecutionStep.task_id == task.id)
            .first()
        )
        if not step:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution step not found.")
        if step.status == StepStatus.COMPLETED:
            return task

        if step.approval_requested_at is not None:
            req_at = step.approval_requested_at
            if req_at.tzinfo is None:
                req_at = req_at.replace(tzinfo=timezone.utc)
            resp_ms = max(1, int((datetime.now(timezone.utc) - req_at).total_seconds() * 1000))
            task.approval_response_ms_total += resp_ms
            task.approval_response_count += 1
            step.approval_requested_at = None

        step.approved_by_user = True
        step.rejected_reason = None
        if step.status in (StepStatus.AWAITING_APPROVAL, StepStatus.REJECTED, StepStatus.PAUSED, StepStatus.INTERRUPTED):
            step.status = StepStatus.PENDING

        record_signal_and_adapt(
            db,
            user=user,
            task=task,
            signal_type="approve",
            step_risk_level=step.risk_level,
            note=f"Approved Step {step.step_order}: '{step.title}'",
        )
        record_event(
            db,
            task_id=task.id,
            user_id=user.id,
            step_id=step.id,
            event_type="STEP_APPROVED",
            actor="human",
            summary=f"Approved Step {step.step_order}: '{step.title}'",
            payload={"risk_level": step.risk_level},
        )
        task.plan_approved = True
        db.commit()
        db.refresh(task)
        sse_broker.publish(task.id, "step_updated", {"step_id": step.id, "approved_by_user": True, "status": step.status})

        if auto_continue and not execution_manager.is_running(task.id) and task.status in (
            TaskStatus.AWAITING_APPROVAL,
            TaskStatus.PAUSED,
            TaskStatus.INTERRUPTED,
            TaskStatus.ROLLED_BACK,
        ):
            return resume_task_execution(db, task, user)
        return task

    # Otherwise approve the overall plan OR the currently awaiting step
    awaiting_step = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.task_id == task.id, ExecutionStep.status == StepStatus.AWAITING_APPROVAL)
        .order_by(ExecutionStep.step_order.asc())
        .first()
    )
    if awaiting_step:
        return approve_action(db, task, user, step_id=awaiting_step.id, auto_continue=auto_continue)

    task.plan_approved = True
    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="approve",
        step_risk_level="low",
        note="Approved overall execution plan",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="PLAN_APPROVED",
        actor="human",
        summary="Approved execution plan.",
    )
    db.commit()
    db.refresh(task)

    if auto_continue and not execution_manager.is_running(task.id) and task.status != TaskStatus.COMPLETED:
        return start_task_execution(db, task, user)
    return task


async def reject_step_action(
    db: Session,
    task: Task,
    user: User,
    step_id: str,
    reason: str,
    generate_alternative: bool = True,
) -> ExecutionStep:
    step = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.id == step_id, ExecutionStep.task_id == task.id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution step not found.")
    if step.status == StepStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reject a completed step. Roll back to an earlier checkpoint instead.",
        )
    if step.status == StepStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interrupt active execution before rejecting the running step.",
        )

    step.approved_by_user = False
    step.rejected_reason = reason.strip() or "Declined by human collaborator"
    step.status = StepStatus.REJECTED

    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="reject",
        step_risk_level=step.risk_level,
        note=f"Rejected Step {step.step_order}: '{step.rejected_reason}'",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        step_id=step.id,
        event_type="STEP_REJECTED",
        actor="human",
        summary=f"Rejected Step {step.step_order} ('{step.title}'): {step.rejected_reason}",
        payload={"reason": step.rejected_reason, "generate_alternative": generate_alternative},
    )

    if generate_alternative:
        provider = get_agent_provider()
        alt = await provider.propose_alternative_step(
            prompt=task.prompt,
            topic=task.topic,
            rejected_step={
                "step_order": step.step_order,
                "title": step.title,
                "description": step.description,
                "risk_level": step.risk_level,
            },
            rejection_reason=step.rejected_reason,
        )
        step.title = alt.title
        step.description = alt.description
        step.rationale = alt.rationale
        step.expected_outcome = alt.expected_outcome
        step.risk_level = alt.risk_level
        step.confidence_basis = alt.confidence_basis
        step.uncertainty_notes = alt.uncertainty_notes
        step.sources_json = json.dumps(alt.sources)
        step.status = StepStatus.AWAITING_APPROVAL
        step.requires_approval = True
        step.approval_reason = "Alternative proposal generated after rejection — requires explicit approval."
        step.revision_number += 1
        step.completed_stages_json = "[]"
        step.partial_output = ""
        task.status = TaskStatus.AWAITING_APPROVAL
        task.current_activity = f"Proposed alternative for Step {step.step_order} after rejection. Review & approve to continue."
        record_event(
            db,
            task_id=task.id,
            user_id=user.id,
            step_id=step.id,
            event_type="STEP_APPROVAL_REQUESTED",
            actor="agent",
            summary=f"Proposed alternative Step {step.step_order}: '{step.title}' (v{step.revision_number})",
        )
    else:
        if task.status != TaskStatus.AWAITING_APPROVAL:
            task.status = TaskStatus.AWAITING_APPROVAL
        task.current_activity = f"Step {step.step_order} rejected. Edit or request replan before resuming."

    db.commit()
    db.refresh(step)
    sse_broker.publish(
        task.id,
        "step_updated",
        {
            "step_id": step.id,
            "status": step.status,
            "title": step.title,
            "revision_number": step.revision_number,
            "task_status": task.status,
        },
    )
    return step


def add_instruction_to_task(db: Session, task: Task, user: User, instruction_text: str) -> Dict[str, Any]:
    cleaned = instruction_text.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instruction cannot be empty.")

    instructions = json.loads(task.additional_instructions_json or "[]")
    # Prevent duplicate instructions: skip if identical to the most recent one.
    if instructions and str(instructions[-1].get("text", "")).strip().lower() == cleaned.lower():
        return instructions[-1]
    entry = {
        "id": str(uuid.uuid4()),
        "text": cleaned,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "step_index": task.current_step_index,
        "task_status_when_added": task.status,
    }
    instructions.append(entry)
    task.additional_instructions_json = json.dumps(instructions)
    task.plan_edits_count += 1

    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="INSTRUCTION_ADDED",
        actor="human",
        summary=f"Added mid-execution instruction: \"{cleaned[:160]}\"",
        payload=entry,
    )
    db.commit()
    db.refresh(task)

    sse_broker.publish(task.id, "instruction_added", entry)
    return entry


def update_task_autonomy_settings(
    db: Session,
    task: Task,
    user: User,
    autonomy_mode: Optional[str] = None,
    adaptive_enabled: Optional[bool] = None,
) -> Task:
    if autonomy_mode is not None:
        task.autonomy_mode = autonomy_mode
    if adaptive_enabled is not None:
        task.adaptive_enabled = adaptive_enabled
        if not adaptive_enabled:
            task.adaptive_reason = f"Adaptive autonomy paused — manual {task.autonomy_mode} policy enforced."

    apply_policy_to_pending_steps(task, user)
    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="mode_override",
        step_risk_level="low",
        note=f"User set autonomy mode='{task.autonomy_mode}', adaptive={task.adaptive_enabled}",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="AUTONOMY_ADJUSTED",
        actor="human",
        summary=f"Updated autonomy mode to '{task.autonomy_mode}' (adaptive={'on' if task.adaptive_enabled else 'off'}).",
        payload={"autonomy_mode": task.autonomy_mode, "adaptive_enabled": task.adaptive_enabled},
    )
    db.commit()
    db.refresh(task)

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
    return task
