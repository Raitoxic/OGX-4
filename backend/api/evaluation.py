from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.task import SubmitEvaluationRequest, UserFeedbackRequest
from backend.services.evaluation_service import (
    get_evaluation_dashboard,
    submit_evaluation_rating,
    submit_user_feedback,
)

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation & Feedback"])


@router.get("")
def evaluation_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_evaluation_dashboard(db, current_user.id)


@router.post("/rate")
def rate_task(
    payload: SubmitEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, payload.task_id, current_user)
    record = submit_evaluation_rating(
        db=db,
        user_id=current_user.id,
        task=task,
        effort_rating=payload.effort_rating,
        trust_rating=payload.trust_rating,
        control_rating=payload.control_rating,
        scenario_key=payload.scenario_key,
        notes=payload.notes,
    )
    return {
        "id": record.id,
        "task_id": record.task_id,
        "interaction_mode": record.interaction_mode,
        "effort_rating": record.effort_rating,
        "trust_rating": record.trust_rating,
        "control_rating": record.control_rating,
        "notes": record.notes,
    }


@router.post("/feedback")
def create_feedback(
    payload: UserFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.task_id:
        get_owned_task(db, payload.task_id, current_user)
    fb = submit_user_feedback(
        db=db,
        user_id=current_user.id,
        comment=payload.comment,
        category=payload.category,
        rating=payload.rating,
        task_id=payload.task_id,
    )
    return {
        "id": fb.id,
        "task_id": fb.task_id,
        "category": fb.category,
        "rating": fb.rating,
        "comment": fb.comment,
        "created_at": fb.created_at.isoformat() if fb.created_at else None,
    }
