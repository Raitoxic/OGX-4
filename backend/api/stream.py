from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.tasks import get_owned_task
from backend.core.security import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.task import serialize_task_detail
from backend.streaming.broker import sse_broker

router = APIRouter(prefix="/api/tasks/{task_id}/stream", tags=["Real-Time Streaming"])


@router.get("")
async def stream_task_events(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    task = get_owned_task(db, task_id, current_user)
    initial_snapshot = serialize_task_detail(task)

    return StreamingResponse(
        sse_broker.stream(task.id, initial_payload=initial_snapshot),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
