from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.execution.control_service import approve_action, reject_step_action
from backend.models.user import User
from backend.orchestration.planning_service import edit_step_instruction, set_step_lock
from backend.schemas.task import (
    ApproveRequest,
    EditStepRequest,
    LockStepRequest,
    RejectStepRequest,
    serialize_step,
    serialize_task_detail,
)

router = APIRouter(prefix="/api/tasks/{task_id}/steps", tags=["Execution Steps"])


@router.patch("/{step_id}")
def edit_step(
    task_id: str,
    step_id: str,
    payload: EditStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    step = edit_step_instruction(
        db=db,
        task=task,
        user=current_user,
        step_id=step_id,
        title=payload.title,
        description=payload.description,
        expected_outcome=payload.expected_outcome,
        edit_note=payload.edit_note,
    )
    db.refresh(task)
    return {"step": serialize_step(step), "task": serialize_task_detail(task)}


@router.post("/{step_id}/lock")
def lock_step(
    task_id: str,
    step_id: str,
    payload: LockStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    step = set_step_lock(db, task, current_user, step_id, payload.is_locked)
    db.refresh(task)
    return {"step": serialize_step(step), "task": serialize_task_detail(task)}


@router.post("/{step_id}/approve")
async def approve_step(
    task_id: str,
    step_id: str,
    payload: ApproveRequest = ApproveRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = approve_action(db, task, current_user, step_id=step_id, auto_continue=payload.auto_continue)
    return serialize_task_detail(updated)


@router.post("/{step_id}/reject")
async def reject_step(
    task_id: str,
    step_id: str,
    payload: RejectStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    step = await reject_step_action(
        db=db,
        task=task,
        user=current_user,
        step_id=step_id,
        reason=payload.reason,
        generate_alternative=payload.generate_alternative,
    )
    db.refresh(task)
    return {"step": serialize_step(step), "task": serialize_task_detail(task)}
