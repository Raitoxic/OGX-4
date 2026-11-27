from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.models.artifact import ArtifactRevision, ArtifactSection
from backend.models.user import User
from backend.schemas.task import (
    CreateArtifactSectionRequest,
    UpdateArtifactSectionRequest,
    serialize_section,
)
from backend.services.artifact_service import (
    apply_user_section_edit,
    compute_section_diff,
    create_user_section,
)

router = APIRouter(prefix="/api/tasks/{task_id}/artifact", tags=["Shared Artifact"])


@router.get("")
def get_artifact(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    sections = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.task_id == task.id)
        .order_by(ArtifactSection.section_order.asc())
        .all()
    )
    return {"task_id": task.id, "title": task.title, "sections": [serialize_section(s) for s in sections]}


@router.post("/sections", status_code=status.HTTP_201_CREATED)
def add_section(
    task_id: str,
    payload: CreateArtifactSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    section = create_user_section(db, task, current_user, payload.heading, payload.content)
    return serialize_section(section)


@router.patch("/sections/{section_id}")
def edit_section(
    task_id: str,
    section_id: str,
    payload: UpdateArtifactSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    section = apply_user_section_edit(
        db=db,
        task=task,
        user=current_user,
        section_id=section_id,
        new_content=payload.current_content,
        new_heading=payload.heading,
    )
    return serialize_section(section)


@router.get("/sections/{section_id}/diff")
def get_section_diff(
    task_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    section = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.id == section_id, ArtifactSection.task_id == task.id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact section not found.")
    return compute_section_diff(section)


@router.get("/sections/{section_id}/revisions")
def get_section_revisions(
    task_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = get_owned_task(db, task_id, current_user)
    revs = (
        db.query(ArtifactRevision)
        .filter(ArtifactRevision.task_id == task.id, ArtifactRevision.section_id == section_id)
        .order_by(ArtifactRevision.version.desc())
        .all()
    )
    return {
        "revisions": [
            {
                "id": r.id,
                "version": r.version,
                "author_type": r.author_type,
                "summary": r.summary,
                "content": r.content,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in revs
        ]
    }
