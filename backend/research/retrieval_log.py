"""Persist retrieval results for evaluation and auditing (never fabricated)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.dataset import RetrievalLog


def log_retrieval(
    db: Session,
    query: str,
    backend: str,
    results: List[Dict[str, Any]],
    top_score: float = 0.0,
    task_id: Optional[str] = None,
    commit: bool = True,
) -> RetrievalLog:
    """Record one retrieval event. ``backend`` is ``lexical`` or ``semantic``."""
    row = RetrievalLog(
        task_id=task_id,
        query=query or "",
        backend=backend if backend in ("lexical", "semantic") else "lexical",
        results_json=json.dumps(results, default=str)[:20000],
        top_score=float(top_score or 0.0),
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def recent_logs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = (
        db.query(RetrievalLog)
        .order_by(RetrievalLog.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            results = json.loads(r.results_json or "[]")
        except Exception:
            results = []
        out.append(
            {
                "id": r.id,
                "task_id": r.task_id,
                "query": r.query,
                "backend": r.backend,
                "top_score": r.top_score,
                "result_count": len(results) if isinstance(results, list) else 0,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return out