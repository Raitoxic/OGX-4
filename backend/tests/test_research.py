from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_research_test_")
_test_db_path = Path(_tmp_dir) / "test_research.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["DEMO_STEP_STAGE_DELAY_SEC"] = "0.02"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.rate_limit import rate_limiter  # noqa: E402
from backend.main import app  # noqa: E402
from backend.research import service as svc  # noqa: E402
from backend.research.classifier import should_research  # noqa: E402
from backend.research.claims import map_claims  # noqa: E402
from backend.research.providers import SourceRecord  # noqa: E402
from backend.schemas.task import normalize_sources  # noqa: E402


def _fake_records() -> list:
    return [
        SourceRecord(
            title="In Search of an Understandable Consensus Algorithm",
            authors="Diego Ongaro, John Ousterhout",
            year=2014,
            venue="USENIX ATC",
            doi="10.1/raft",
            url="https://www.usenix.org/raft",
            provider="openalex",
            access_status="abstract_accessed",
            abstract="Raft is a consensus algorithm designed to be understandable.",
        ),
        SourceRecord(
            title="Paxos Made Simple",
            authors="Leslie Lamport",
            year=2001,
            venue="ACM SIGACT",
            doi="10.1/paxos",
            url="https://lamport.azurewebsites.net/pubs/paxos-simple.pdf",
            provider="crossref",
            access_status="metadata_only",
            abstract="",
        ),
    ]


def _patch_providers() -> None:
    async def _fake(query, providers, limit):
        return _fake_records()

    svc.run_providers = _fake  # type: ignore[assignment]


def test_classifier_respects_intent_and_explicit() -> None:
    assert should_research("calculate 2 + 2 and format the result", False)[0] is False
    assert should_research("research and compare Raft and Paxos papers", False)[0] is True
    # Explicit enable overrides simple-task heuristic.
    assert should_research("format this", True)[0] is True


def test_service_splits_used_and_additional_and_builds_context() -> None:
    _patch_providers()
    bundle = asyncio.run(svc.research_service.run("research compare Raft and Paxos", True))
    assert bundle.status == "completed"
    assert bundle.used_count >= 1
    assert bundle.used[0]["used"] is True
    assert bundle.used[0]["access_status"] == "abstract_accessed"
    # Only top-K are "used"; the rest are additional (not used).
    for s in bundle.retrieved:
        assert s["used"] is False
    assert "[1]" in bundle.context_str
    assert bundle.duration_ms >= 0


def test_claim_mapping_labels() -> None:
    used = [{"title": "A", "used": True, "abstract": "passage A"}]
    claims = map_claims("Statement one [1].\n\nStatement two.", used)
    assert claims[0]["support"] == "evidence_backed"
    assert claims[0]["ref_numbers"] == [1]
    assert claims[1]["support"] == "unverified"
    # No used sources -> general explanation, not fabricated support.
    claims2 = map_claims("Some statement.", [])
    assert claims2[0]["support"] == "no_research"


def test_missing_metadata_and_used_flag_safe() -> None:
    parsed = normalize_sources('[{"title": "Only Title", "used": true, "access_status": "metadata_only"}]')
    assert parsed[0]["title"] == "Only Title"
    assert parsed[0]["authors"] is None
    assert parsed[0]["doi"] is None
    assert parsed[0]["used"] is True
    assert parsed[0]["access_status"] == "metadata_only"


def test_research_preview_requires_auth_and_returns_used(monkeypatch) -> None:
    _patch_providers()
    with TestClient(app) as client:
        # No auth -> 401/403.
        unauth = client.post("/api/research/preview", json={"prompt": "research Raft consensus", "enabled": True})
        assert unauth.status_code in (401, 403)

        rate_limiter.reset()
        reg = client.post(
            "/api/auth/register",
            json={"email": f"rs_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Ref User", "password": "SecurePassword123!"},
        )
        assert reg.status_code == 201, reg.text
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        resp = client.post(
            "/api/research/preview",
            headers=headers,
            json={"prompt": "research compare Raft and Paxos", "enabled": True},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body["used_count"] >= 1


def test_task_persists_research_flag() -> None:
    with TestClient(app) as client:
        rate_limiter.reset()
        reg = client.post(
            "/api/auth/register",
            json={"email": f"rt_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Ref User", "password": "SecurePassword123!"},
        )
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        created = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research and write a report on Raft consensus.", "research_enabled": True},
        )
        assert created.status_code in (200, 201), created.text
        body = created.json()
        assert body["research_enabled"] is True
        assert body["research_status"] == "pending"

        # Default is OFF.
        created2 = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research and write a report on Paxos."},
        )
        assert created2.json()["research_enabled"] is False
        assert created2.json()["research_status"] == "disabled"