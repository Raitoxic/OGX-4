from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.config import settings
from backend.core.rate_limit import client_ip_from_request, rate_limiter
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.ml_service import get_ml_status_and_monitoring, predict_supervision_for_task
from ml.inference.predictor import supervision_predictor
from ml.training.train import run_training_pipeline

router = APIRouter(prefix="/api/ml", tags=["Adaptive Supervision ML"])


@router.get("/status")
def ml_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_ml_status_and_monitoring(db, current_user)


@router.post("/predict/{task_id}")
def predict_for_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    return predict_supervision_for_task(db, current_user, task, log_prediction=True, commit=True)


@router.post("/retrain")
async def retrain_model(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"ml_retrain:{ip}", settings.ml_retrain_rate_limit_per_min, window_seconds=60)
    report = await asyncio.to_thread(run_training_pipeline, None, True, None)
    supervision_predictor.reload()
    return {
        "status": "retrained",
        "selected_model": report["selected_model"],
        "test_evaluation": report["test_evaluation"],
        "monitoring": get_ml_status_and_monitoring(db, current_user)["monitoring"],
    }
