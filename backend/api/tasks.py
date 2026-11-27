from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.execution.control_service import (
    add_instruction_to_task,
    approve_action,
    interrupt_task_execution,
    pause_task_execution,
    resume_task_execution,
    start_task_execution,
    update_task_autonomy_settings,
)
from backend.execution.runner import execution_manager
from backend.models.task import Task
from backend.models.user import User
from backend.orchestration.planning_service import create_task_and_generate_plan, replan_unlocked_steps
from backend.schemas.task import (
    AddInstructionRequest,
    ApproveRequest,
    CreateTaskRequest,
    ReplanRequest,
    SseLatencyRequest,
    UpdateAutonomyRequest,
    serialize_event,
    serialize_task_detail,
    serialize_task_summary,
)
from backend.services.history_service import list_task_events

router = APIRouter(prefix="/api/tasks", tags=["Tasks & Execution"])


def get_owned_task(db: Session, task_id: str, user: User) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.get("")
def list_tasks(
    interaction_mode: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if interaction_mode in ("vyrox", "hai"):
        query = query.filter(Task.interaction_mode != "baseline")
    elif interaction_mode == "baseline":
        query = query.filter(Task.interaction_mode == "baseline")
    tasks = query.order_by(Task.updated_at.desc()).all()
    return {"tasks": [serialize_task_summary(t) for t in tasks]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = await create_task_and_generate_plan(
        db=db,
        user=current_user,
        prompt=payload.prompt,
        title=payload.title,
        interaction_mode=payload.interaction_mode,
        autonomy_mode=payload.autonomy_mode,
        adaptive_enabled=payload.adaptive_enabled,
    )
    return serialize_task_detail(task)


@router.get("/{task_id}")
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    return serialize_task_detail(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    await execution_manager.abort_for_rollback(task.id)
    db.delete(task)
    db.commit()
    return {"status": "deleted", "task_id": task_id}


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = start_task_execution(db, task, current_user)
    return serialize_task_detail(updated)


@router.post("/{task_id}/pause")
async def pause_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = await pause_task_execution(db, task, current_user)
    return serialize_task_detail(updated)


@router.post("/{task_id}/interrupt")
async def interrupt_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    outcome = await interrupt_task_execution(db, task, current_user)
    return {
        "message": outcome["message"],
        "deferred_atomic": outcome["deferred_atomic"],
        "task": serialize_task_detail(outcome["task"]),
    }


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = resume_task_execution(db, task, current_user)
    return serialize_task_detail(updated)


@router.post("/{task_id}/approve")
async def approve_task(
    task_id: str,
    payload: ApproveRequest = ApproveRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = approve_action(db, task, current_user, step_id=payload.step_id, auto_continue=payload.auto_continue)
    return serialize_task_detail(updated)


@router.post("/{task_id}/replan")
async def replan_task(
    task_id: str,
    payload: ReplanRequest = ReplanRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = await replan_unlocked_steps(db, task, current_user, reason=payload.reason)
    return serialize_task_detail(updated)


@router.post("/{task_id}/instructions")
def add_instruction(
    task_id: str,
    payload: AddInstructionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    entry = add_instruction_to_task(db, task, current_user, payload.instruction)
    return {"instruction": entry, "task": serialize_task_detail(task)}


@router.patch("/{task_id}/autonomy")
def update_autonomy(
    task_id: str,
    payload: UpdateAutonomyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    updated = update_task_autonomy_settings(
        db,
        task,
        current_user,
        autonomy_mode=payload.autonomy_mode,
        adaptive_enabled=payload.adaptive_enabled,
    )
    return serialize_task_detail(updated)


@router.get("/{task_id}/history")
def get_task_history(
    task_id: str,
    event_type: Optional[str] = Query(default=None),
    actor: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    events = list_task_events(db, task.id, event_type=event_type, actor=actor)
    return {"task_id": task.id, "events": [serialize_event(ev) for ev in events]}


@router.post("/{task_id}/telemetry/sse-latency")
def record_sse_latency(
    task_id: str,
    payload: SseLatencyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    import json

    task = get_owned_task(db, task_id, current_user)
    samples = json.loads(task.sse_latency_samples_json or "[]")
    samples.append(round(float(payload.latency_ms), 2))
    task.sse_latency_samples_json = json.dumps(samples[-100:])
    db.commit()
    return {"recorded": True, "sample_count": len(samples)}
