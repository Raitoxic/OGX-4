from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.checkpoints.service import (
    compare_checkpoints,
    create_checkpoint,
    list_checkpoints,
    rollback_to_checkpoint,
)
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.execution.runner import execution_manager
from backend.models.user import User
from backend.schemas.task import CreateCheckpointRequest, serialize_checkpoint, serialize_task_detail

router = APIRouter(prefix="/api/tasks/{task_id}/checkpoints", tags=["Checkpoints & Rollback"])


@router.get("")
def get_checkpoints(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    cps = list_checkpoints(db, task.id)
    return {"checkpoints": [serialize_checkpoint(cp) for cp in cps]}


@router.post("")
def save_manual_checkpoint(
    task_id: str,
    payload: CreateCheckpointRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    cp = create_checkpoint(
        db=db,
        task=task,
        user_id=current_user.id,
        trigger_type="manual",
        label=payload.label,
        commit=True,
    )
    return serialize_checkpoint(cp)


@router.get("/compare")
def diff_checkpoints(
    task_id: str,
    from_id: str = Query(...),
    to_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    return compare_checkpoints(db, task.id, from_id, to_id)


@router.post("/{checkpoint_id}/rollback")
async def rollback_checkpoint(
    task_id: str,
    checkpoint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    await execution_manager.abort_for_rollback(task.id)
    db.refresh(task)
    restored = rollback_to_checkpoint(db, task, current_user, checkpoint_id)
    db.expire_all()
    refreshed = get_owned_task(db, task_id, current_user)
    return {
        "restored_checkpoint": serialize_checkpoint(restored),
        "task": serialize_task_detail(refreshed),
    }
