from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.telemetry import InteractionEvent
from backend.streaming.broker import sse_broker


def record_event(
    db: Session,
    *,
    task_id: str,
    user_id: str,
    event_type: str,
    actor: str,
    summary: str,
    step_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    emit_sse: bool = True,
    commit: bool = False,
) -> InteractionEvent:
    event = InteractionEvent(
        task_id=task_id,
        user_id=user_id,
        step_id=step_id,
        event_type=event_type,
        actor=actor,
        summary=summary,
        payload_json=json.dumps(payload or {}, default=str),
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()

    if emit_sse:
        sse_broker.publish(
            task_id,
            "activity_event",
            {
                "id": event.id,
                "task_id": event.task_id,
                "step_id": event.step_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "summary": event.summary,
                "payload": payload or {},
                "created_at": event.created_at.isoformat() if event.created_at else None,
            },
        )
    return event


def list_task_events(
    db: Session,
    task_id: str,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 200,
) -> List[InteractionEvent]:
    query = db.query(InteractionEvent).filter(InteractionEvent.task_id == task_id)
    if event_type:
        query = query.filter(InteractionEvent.event_type == event_type)
    if actor:
        query = query.filter(InteractionEvent.actor == actor)
    return query.order_by(InteractionEvent.created_at.desc()).limit(limit).all()
