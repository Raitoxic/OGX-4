from __future__ import annotations

from typing import Dict, Set

from fastapi import HTTPException, status


class TaskStatus:
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    INTERRUPTED = "INTERRUPTED"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class StepStatus:
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


ALLOWED_TASK_TRANSITIONS: Dict[str, Set[str]] = {
    TaskStatus.CREATED: {
        TaskStatus.PLANNING,
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
    },
    TaskStatus.PLANNING: {
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.RUNNING,
        TaskStatus.PAUSED,
        TaskStatus.INTERRUPTED,
        TaskStatus.FAILED,
    },
    TaskStatus.AWAITING_APPROVAL: {
        TaskStatus.RUNNING,
        TaskStatus.PLANNING,
        TaskStatus.PAUSED,
        TaskStatus.INTERRUPTED,
        TaskStatus.ROLLED_BACK,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.PAUSED,
        TaskStatus.INTERRUPTED,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.ROLLED_BACK,
    },
    TaskStatus.PAUSED: {
        TaskStatus.RESUMING,
        TaskStatus.PLANNING,
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.INTERRUPTED,
        TaskStatus.ROLLED_BACK,
        TaskStatus.FAILED,
    },
    TaskStatus.INTERRUPTED: {
        TaskStatus.RESUMING,
        TaskStatus.PLANNING,
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.ROLLED_BACK,
        TaskStatus.FAILED,
    },
    TaskStatus.RESUMING: {
        TaskStatus.RUNNING,
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.INTERRUPTED,
        TaskStatus.PAUSED,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
    },
    TaskStatus.ROLLED_BACK: {
        TaskStatus.RESUMING,
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.PLANNING,
        TaskStatus.RUNNING,
        TaskStatus.ROLLED_BACK,
    },
    TaskStatus.COMPLETED: {
        TaskStatus.ROLLED_BACK,
    },
    TaskStatus.FAILED: {
        TaskStatus.RESUMING,
        TaskStatus.PLANNING,
        TaskStatus.ROLLED_BACK,
    },
}


def can_transition_task(current_state: str, target_state: str) -> bool:
    if current_state == target_state:
        return True
    return target_state in ALLOWED_TASK_TRANSITIONS.get(current_state, set())


def validate_task_transition(current_state: str, target_state: str, context: str = "") -> None:
    if not can_transition_task(current_state, target_state):
        msg = f"Invalid task state transition from '{current_state}' to '{target_state}'."
        if context:
            msg = f"{msg} {context}"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)


def ensure_step_mutable_by_agent(is_locked: bool, step_title: str) -> None:
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step '{step_title}' is locked by the user and cannot be modified by the agent.",
        )


def ensure_step_not_rejected(step_status: str, step_title: str) -> None:
    if step_status == StepStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step '{step_title}' was rejected. Edit, replace, or explicitly approve it before execution.",
        )
