"""Dataset preparation, embedding index, and retrieval-log API.

Additive and read-mostly. Build/index endpoints are rate limited and require
authentication. All data is derived from real stored rows; empty sources are
reported honestly rather than fabricated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.rate_limit import client_ip_from_request, rate_limiter
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.research.dataset_pipeline import dataset_status, export_dataset, run_pipeline
from backend.research.embedding_service import embedding_service
from backend.research.retrieval_log import recent_logs

router = APIRouter(prefix="/api/datasets", tags=["Research Datasets"])


@router.get("/status")
def get_dataset_status(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    status = dataset_status(db)
    status["embedding"] = {
        "available": embedding_service.available(),
        "model": embedding_service.model_name,
        "dim": embedding_service.dim,
        "backend": settings.embedding_backend,
    }
    return status


@router.post("/build")
async def build_datasets(
    request: Request,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"dataset_build:{ip}", 6, window_seconds=60)
    return run_pipeline(db)


@router.post("/embeddings/index")
async def index_embeddings(
    request: Request,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"embedding_index:{ip}", 6, window_seconds=60)
    result = embedding_service.index_chunks(db)
    result["embedding"] = {
        "available": embedding_service.available(),
        "model": embedding_service.model_name,
        "dim": embedding_service.dim,
    }
    return result


@router.get("/retrieval-logs")
def get_retrieval_logs(
    limit: int = 50,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"logs": recent_logs(db, limit)}


@router.post("/export/{dataset_version}")
async def export_datasets(
    dataset_version: str,
    request: Request,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"dataset_export:{ip}", 6, window_seconds=60)
    return export_dataset(db, dataset_version)