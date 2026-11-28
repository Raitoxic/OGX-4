from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_dataset_test_")
_test_db_path = Path(_tmp_dir) / "test_dataset.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["EMBEDDING_BACKEND"] = "blob"

from backend.database.session import SessionLocal  # noqa: E402
from backend.database.init_db import init_db  # noqa: E402

init_db()

from backend.models.dataset import DatasetRecord, DatasetSplit  # noqa: E402
from backend.models.task import Task  # noqa: E402
from backend.models.user import User  # noqa: E402
from backend.research import dataset_pipeline  # noqa: E402


def _seed_user_and_tasks() -> str:
    db = SessionLocal()
    try:
        user = User(email="dataset@test.local", password_hash="x", full_name="Dataset Test")
        db.add(user)
        db.flush()
        for i in range(20):
            db.add(
                Task(
                    user_id=user.id,
                    title=f"Task {i}",
                    prompt=f"Research cloud security topic number {i} with enough words to be real",
                    interaction_mode="vyrox" if i % 2 == 0 else "baseline",
                    status="COMPLETED" if i % 3 == 0 else "RUNNING",
                )
            )
        db.commit()
        return user.id
    finally:
        db.close()


def test_schemas_present() -> None:
    assert set(dataset_pipeline.DATASET_SCHEMAS.keys()) == {"A", "B", "C", "D", "E"}


def test_split_is_deterministic_and_grouped() -> None:
    a = dataset_pipeline._split_for_group("doc-123", 42)
    b = dataset_pipeline._split_for_group("doc-123", 42)
    assert a == b
    # Different groups can map to different splits; same group never leaks.
    splits = {dataset_pipeline._split_for_group(f"doc-{i}", 42) for i in range(50)}
    assert splits.issubset({"train", "val", "test"})


def test_build_produces_counts_and_no_duplicate_rows() -> None:
    _seed_user_and_tasks()
    db = SessionLocal()
    try:
        summary = dataset_pipeline.run_pipeline(db, dataset_version="vtest", export=False)
    finally:
        db.close()
    assert summary["dataset_version"] == "vtest"
    letters = {d["dataset"] for d in summary["datasets"]}
    assert letters == {"A", "B", "C", "D", "E"}
    # Dataset B is built from the 20 seeded tasks.
    b = next(d for d in summary["datasets"] if d["dataset"] == "B")
    assert b["record_count"] == 20
    assert sum(b["splits"].values()) == 20

    db = SessionLocal()
    try:
        records = (
            db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_version == "vtest", DatasetRecord.dataset_name == "B")
            .all()
        )
        assert len(records) == 20
        # Grouped split: each task id appears in exactly one split.
        by_group = {}
        for r in records:
            by_group.setdefault(r.source_document_id, set()).add(r.split_name)
        assert all(len(v) == 1 for v in by_group.values())
        splits = db.query(DatasetSplit).filter(DatasetSplit.dataset_version == "vtest").all()
        assert len(splits) == 5
    finally:
        db.close()


def test_empty_dataset_is_honest_not_fabricated() -> None:
    db = SessionLocal()
    try:
        # No retrieval logs seeded -> dataset A must be empty, not invented.
        res = dataset_pipeline.build_dataset(db, "A", "vempty")
    finally:
        db.close()
    assert res["record_count"] == 0
    assert res["quality_status"] == "empty"


def test_build_is_idempotent() -> None:
    db = SessionLocal()
    try:
        dataset_pipeline.build_dataset(db, "B", "videm")
        first = db.query(DatasetRecord).filter(DatasetRecord.dataset_version == "videm").count()
        dataset_pipeline.build_dataset(db, "B", "videm")
        second = db.query(DatasetRecord).filter(DatasetRecord.dataset_version == "videm").count()
    finally:
        db.close()
    assert first == second


def test_status_lists_versions() -> None:
    db = SessionLocal()
    try:
        dataset_pipeline.run_pipeline(db, dataset_version="vstatus", export=False)
        status = dataset_pipeline.dataset_status(db)
    finally:
        db.close()
    versions = {v["dataset_version"] for v in status["versions"]}
    assert "vstatus" in versions