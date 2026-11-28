from __future__ import annotations

import os
import tempfile
import time
import uuid
from pathlib import Path

# Isolated SQLite DB & fast stage timing BEFORE app import
_tmp_dir = tempfile.mkdtemp(prefix="vyrox_ref_test_")
_test_db_path = Path(_tmp_dir) / "test_refs.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["DEMO_STEP_STAGE_DELAY_SEC"] = "0.02"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.rate_limit import rate_limiter  # noqa: E402
from backend.main import app  # noqa: E402
from backend.schemas.task import StepSource, normalize_sources  # noqa: E402


def _auth_headers(client: TestClient, email: str) -> dict:
    rate_limiter.reset()
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Ref Tester", "password": "SecurePassword123!"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_step_source_missing_metadata_is_none_not_fabricated() -> None:
    # Only the conventional four fields are present; no author/year/doi invented.
    src = StepSource(
        title="User Task Specification",
        type="user_input",
        reference="Original prompt",
        reliability_note="Primary source.",
    )
    assert src.authors is None
    assert src.year is None
    assert src.doi is None
    assert src.venue is None
    assert src.provider is None
    assert src.access_status is None


def test_normalize_sources_handles_partial_and_malformed_safely() -> None:
    # Partial entry: missing bibliographic metadata stays None (no fabrication).
    partial = normalize_sources('[{"title": "Only Title"}]')
    assert len(partial) == 1
    assert partial[0]["title"] == "Only Title"
    assert partial[0]["authors"] is None
    assert partial[0]["doi"] is None
    # Malformed JSON and non-list payloads degrade to empty list, never raise.
    assert normalize_sources("not-json") == []
    assert normalize_sources("{}") == []
    # Non-dict items are skipped.
    assert normalize_sources("[1, 2, 3]") == []


def test_generated_output_exposes_sources_without_fabrication() -> None:
    email = f"ref_{uuid.uuid4().hex[:8]}@example.com"
    # Context manager triggers app lifespan (init_db creates schema in the temp DB).
    with TestClient(app) as client:
        headers = _auth_headers(client, email)

        created = client.post(
            "/api/tasks",
            headers=headers,
            json={
                "prompt": "Research and write a structured technical report on Distributed Consensus (Raft vs Paxos).",
                "interaction_mode": "vyrox",
                "autonomy_mode": "higher_autonomy",
            },
        )
        assert created.status_code in (200, 201), created.text
        task_id = created.json()["id"]

        started = client.post(f"/api/tasks/{task_id}/start", headers=headers)
        assert started.status_code in (200, 201), started.text

        deadline = time.time() + 20
        detail = None
        while time.time() < deadline:
            detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
            if any(s.get("sources") for s in detail["steps"]):
                break
            time.sleep(0.2)

    assert detail is not None
    steps_with_sources = [s for s in detail["steps"] if s.get("sources")]
    assert steps_with_sources, "expected at least one step to carry sources"

    for step in steps_with_sources:
        for src in step["sources"]:
            # Honest attribution: demo mode must not fabricate bibliographic metadata.
            assert src.get("authors") is None
            assert src.get("doi") is None
            assert src.get("year") is None
            # A title always exists to render a citation.
            assert src.get("title")


def test_no_sources_section_is_honestly_empty() -> None:
    # A step with no recorded sources serializes to an empty list (honest disclosure).
    assert normalize_sources("[]") == []
    assert normalize_sources("") == []