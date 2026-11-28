"""Research API: preview retrieval, persisted provenance, and citation style.

All task-scoped endpoints require authentication and enforce task ownership via
``get_owned_task``. External documents remain untrusted; this module only reads
already-stored, sanitized provenance and never fabricates sources.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.security import get_current_user, get_current_user_and_token
from backend.database.session import get_db
from backend.models.user import User
from backend.research.citations import VALID_STYLES, normalize_style
from backend.research.pdf_ingest import ensure_ingested, list_documents
from backend.research.service import research_service
from backend.schemas.task import normalize_sources

router = APIRouter(prefix="/api/research", tags=["Research"])


class ResearchPreviewRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    enabled: Optional[bool] = None


class CitationStyleRequest(BaseModel):
    style: str = Field(default="simple")


@router.post("/preview")
async def preview_research(
    payload: ResearchPreviewRequest,
    _user: User = Depends(get_current_user_and_token),
    _db: Session = Depends(get_db),
) -> dict:
    bundle = await research_service.run(payload.prompt, bool(payload.enabled))
    return {
        "status": bundle.status,
        "reason": bundle.reason,
        "query": bundle.query,
        "providers": bundle.providers,
        "duration_ms": bundle.duration_ms,
        "used_count": bundle.used_count,
        "retrieved_count": bundle.retrieved_count,
        "used": bundle.used,
        "retrieved": bundle.retrieved,
    }


@router.get("/task/{task_id}")
def get_task_research(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Persisted research provenance for a task (used vs. additional sources)."""
    task = get_owned_task(db, task_id, current_user)
    used = normalize_sources(task.research_used_json)
    retrieved = normalize_sources(task.research_retrieved_json)
    return {
        "task_id": task.id,
        "research_enabled": task.research_enabled,
        "status": task.research_status,
        "duration_ms": task.research_duration_ms,
        "used_count": task.research_used_count,
        "retrieved_count": task.research_retrieved_count,
        "citation_style": normalize_style(task.citation_style),
        "used": used,
        "retrieved": retrieved,
    }


@router.patch("/task/{task_id}/citation-style")
def set_citation_style(
    task_id: str,
    payload: CitationStyleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Persist the chosen citation style so it survives reloads and export."""
    task = get_owned_task(db, task_id, current_user)
    style = payload.style.strip().lower()
    if style not in VALID_STYLES:
        style = "simple"
    task.citation_style = style
    db.commit()
    return {"task_id": task.id, "citation_style": normalize_style(task.citation_style)}


@router.get("/pdfs")
def list_pdfs(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List ingested local PDF dataset documents and processing status."""
    ensure_ingested(db)
    docs = list_documents(db)
    indexed = [d for d in docs if d["status"] == "indexed"]
    return {
        "documents": docs,
        "indexed_count": len(indexed),
        "total_count": len(docs),
        "total_chunks": sum(d["chunk_count"] for d in indexed),
    }


@router.post("/pdfs/ingest")
def ingest_pdfs(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger (re)ingestion of the local PDF dataset. Idempotent."""
    docs = ensure_ingested(db)
    indexed = [d for d in docs if d["status"] == "indexed"]
    return {
        "documents": docs,
        "indexed_count": len(indexed),
        "total_count": len(docs),
        "total_chunks": sum(d["chunk_count"] for d in indexed),
    }