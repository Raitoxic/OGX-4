"""Research dataset preparation pipeline (schemas A–E).

Builds versioned, reproducible datasets from REAL stored rows only. Nothing is
fabricated: when a source has no rows, that dataset is recorded with an honest
``empty`` quality status instead of invented samples.

Schemas
-------
A ``retrieval_eval``          query -> retrieved chunk/doc relevance (from RetrievalLog)
B ``supervision_classification`` prompt -> interaction mode / autonomy (from Task)
C ``citation_attribution``    task -> used research sources (from Task.research_used_json)
D ``artifact_qa``             section heading -> section content (from ArtifactSection)
E ``regression_golden``       completed task -> expected final status (from Task)

Splits
------
Deterministic, seed ``settings.dataset_split_seed`` (default 42), assigned by
GROUP KEY (document/task/artifact id) so all rows of one document land in a
single split. This prevents document-level leakage between train/val/test.
Ratios: 70% train / 15% val / 15% test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.artifact import ArtifactSection
from backend.models.dataset import DatasetRecord, DatasetSource, DatasetSplit
from backend.models.task import Task
from backend.models.dataset import RetrievalLog

DATASET_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "retrieval_eval",
        "description": "Query -> retrieved chunk/document relevance pairs for retrieval evaluation.",
        "group_key": "task_id",
    },
    "B": {
        "name": "supervision_classification",
        "description": "Task prompt -> interaction mode / autonomy label for the supervision classifier.",
        "group_key": "task_id",
    },
    "C": {
        "name": "citation_attribution",
        "description": "Task -> the research sources actually used (honest used flag + access status).",
        "group_key": "task_id",
    },
    "D": {
        "name": "artifact_qa",
        "description": "Artifact section heading -> section content (grounded QA pairs).",
        "group_key": "task_id",
    },
    "E": {
        "name": "regression_golden",
        "description": "Completed task -> expected final status, as a golden regression set.",
        "group_key": "task_id",
    },
}


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _split_for_group(group_key: str, seed: int) -> str:
    """Deterministically map a group key to train/val/test (no leakage)."""
    digest = hashlib.sha256(f"{seed}:{group_key}".encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "val"
    return "test"


# --- Builders: each returns list of (group_key, record_dict, source_document_id) ---

def _build_a(db: Session) -> List[Tuple[str, Dict[str, Any], Optional[str]]]:
    rows = db.query(RetrievalLog).order_by(RetrievalLog.created_at.asc()).limit(5000).all()
    out: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
    for r in rows:
        try:
            results = json.loads(r.results_json or "[]")
        except Exception:
            results = []
        out.append(
            (
                r.task_id or r.id,
                {
                    "query": r.query,
                    "backend": r.backend,
                    "top_score": r.top_score,
                    "result_count": len(results) if isinstance(results, list) else 0,
                },
                r.task_id,
            )
        )
    return out


def _build_b(db: Session) -> List[Tuple[str, Dict[str, Any], Optional[str]]]:
    rows = db.query(Task).order_by(Task.created_at.asc()).limit(5000).all()
    return [
        (
            t.id,
            {
                "prompt": t.prompt,
                "interaction_mode": t.interaction_mode,
                "autonomy_mode": t.autonomy_mode,
                "status": t.status,
            },
            t.id,
        )
        for t in rows
        if (t.prompt or "").strip()
    ]


def _build_c(db: Session) -> List[Tuple[str, Dict[str, Any], Optional[str]]]:
    rows = db.query(Task).filter(Task.research_used_json != "[]").limit(5000).all()
    out: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
    for t in rows:
        try:
            used = json.loads(t.research_used_json or "[]")
        except Exception:
            used = []
        if not isinstance(used, list) or not used:
            continue
        out.append((t.id, {"task_id": t.id, "used_sources": used, "used_count": len(used)}, t.id))
    return out


def _build_d(db: Session) -> List[Tuple[str, Dict[str, Any], Optional[str]]]:
    rows = db.query(ArtifactSection).order_by(ArtifactSection.task_id, ArtifactSection.section_order).limit(10000).all()
    return [
        (
            s.task_id,
            {
                "task_id": s.task_id,
                "heading": s.heading,
                "content": s.current_content or s.ai_content,
                "authorship": s.authorship,
            },
            s.task_id,
        )
        for s in rows
        if (s.current_content or s.ai_content or "").strip()
    ]


def _build_e(db: Session) -> List[Tuple[str, Dict[str, Any], Optional[str]]]:
    rows = db.query(Task).filter(Task.status == "COMPLETED").order_by(Task.created_at.asc()).limit(5000).all()
    return [
        (t.id, {"task_id": t.id, "prompt": t.prompt, "expected_status": "COMPLETED"}, t.id)
        for t in rows
        if (t.prompt or "").strip()
    ]


_BUILDERS: Dict[str, Callable[[Session], List[Tuple[str, Dict[str, Any], Optional[str]]]]] = {
    "A": _build_a,
    "B": _build_b,
    "C": _build_c,
    "D": _build_d,
    "E": _build_e,
}


def _quality_status(records: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    n = len(records)
    if n == 0:
        return "empty", {"record_count": 0, "duplicate_ratio": 0.0}
    hashes = [r.get("content_hash", "") for r in records]
    non_empty = [h for h in hashes if h]
    dup_ratio = 0.0
    if non_empty:
        dup_ratio = round(1.0 - (len(set(non_empty)) / len(non_empty)), 4)
    if n < 5:
        return "insufficient", {"record_count": n, "duplicate_ratio": dup_ratio}
    return "ok", {"record_count": n, "duplicate_ratio": dup_ratio}


def build_dataset(db: Session, key: str, dataset_version: str) -> Dict[str, Any]:
    """Materialize one dataset (A–E) into DatasetRecord/DatasetSplit rows."""
    schema = DATASET_SCHEMAS[key]
    builder = _BUILDERS[key]
    seed = settings.dataset_split_seed

    # Idempotent: clear prior rows for this (version, dataset).
    db.query(DatasetRecord).filter(
        DatasetRecord.dataset_version == dataset_version,
        DatasetRecord.dataset_name == key,
    ).delete(synchronize_session=False)
    db.query(DatasetSplit).filter(
        DatasetSplit.dataset_version == dataset_version,
        DatasetSplit.dataset_name == key,
    ).delete(synchronize_session=False)

    triples = builder(db)
    counts = {"train": 0, "val": 0, "test": 0}
    record_dicts: List[Dict[str, Any]] = []
    for group_key, payload, source_doc in triples:
        split = _split_for_group(group_key, seed)
        counts[split] += 1
        record = dict(payload)
        record["group_key"] = group_key
        chash = content_hash(json.dumps(payload, sort_keys=True, default=str))
        record["content_hash"] = chash
        record_dicts.append(record)
        db.add(
            DatasetRecord(
                dataset_version=dataset_version,
                dataset_name=key,
                split_name=split,
                record_json=json.dumps(payload, default=str),
                source_document_id=source_doc,
                content_hash=chash,
            )
        )

    quality_status, quality_detail = _quality_status(record_dicts)
    methodology = {
        "seed": seed,
        "ratios": {"train": 0.70, "val": 0.15, "test": 0.15},
        "group_key": schema["group_key"],
        "leakage_policy": "group-by-document (all rows of one group share a single split)",
        "quality": quality_detail,
    }
    db.add(
        DatasetSplit(
            dataset_version=dataset_version,
            dataset_name=key,
            seed=seed,
            train_count=counts["train"],
            val_count=counts["val"],
            test_count=counts["test"],
            methodology_json=json.dumps(methodology),
        )
    )

    # One provenance source row per dataset/version.
    existing = (
        db.query(DatasetSource)
        .filter(DatasetSource.name == schema["name"], DatasetSource.dataset_version == dataset_version)
        .first()
    )
    if existing is None:
        db.add(
            DatasetSource(
                name=schema["name"],
                provider="vyrox_local",
                source_url="",
                license_name="internal",
                dataset_version=dataset_version,
                record_count=len(record_dicts),
                content_type="jsonl",
                access_level="full_text",
                quality_status=quality_status,
                processing_status="ready",
            )
        )
    else:
        existing.record_count = len(record_dicts)
        existing.quality_status = quality_status
        existing.processing_status = "ready"

    db.commit()
    return {
        "dataset": key,
        "name": schema["name"],
        "record_count": len(record_dicts),
        "splits": counts,
        "quality_status": quality_status,
        "quality": quality_detail,
    }


def export_dataset(db: Session, dataset_version: str) -> Dict[str, Any]:
    """Write JSONL exports + manifest for a built dataset version."""
    out_dir = Path(settings.dataset_export_dir) / dataset_version
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, Any] = {"dataset_version": dataset_version, "files": {}}
    for key, schema in DATASET_SCHEMAS.items():
        rows = (
            db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_version == dataset_version, DatasetRecord.dataset_name == key)
            .all()
        )
        path = out_dir / f"{key}_{schema['name']}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(r.record_json + "\n")
        manifest["files"][key] = {"name": schema["name"], "path": str(path), "records": len(rows)}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["export_dir"] = str(out_dir)
    return manifest


def run_pipeline(db: Session, dataset_version: Optional[str] = None, export: bool = True) -> Dict[str, Any]:
    """Build all datasets A–E for a version and (optionally) export them."""
    version = dataset_version or f"v{settings.dataset_split_seed}"
    results = [build_dataset(db, key, version) for key in DATASET_SCHEMAS]
    summary = {
        "dataset_version": version,
        "datasets": results,
        "total_records": sum(r["record_count"] for r in results),
        "embedding_available": _embedding_available(),
    }
    if export:
        summary["export"] = export_dataset(db, version)
    return summary


def _embedding_available() -> bool:
    try:
        from backend.research.embedding_service import embedding_service

        return embedding_service.available()
    except Exception:
        return False


def dataset_status(db: Session) -> Dict[str, Any]:
    """Summarize built dataset versions without rebuilding."""
    versions = sorted({r.dataset_version for r in db.query(DatasetRecord).all()})
    out: List[Dict[str, Any]] = []
    for v in versions:
        splits = db.query(DatasetSplit).filter(DatasetSplit.dataset_version == v).all()
        out.append(
            {
                "dataset_version": v,
                "datasets": [
                    {
                        "dataset": s.dataset_name,
                        "name": DATASET_SCHEMAS.get(s.dataset_name, {}).get("name", s.dataset_name),
                        "train": s.train_count,
                        "val": s.val_count,
                        "test": s.test_count,
                        "seed": s.seed,
                    }
                    for s in splits
                ],
            }
        )
    return {"versions": out, "embedding_available": _embedding_available()}