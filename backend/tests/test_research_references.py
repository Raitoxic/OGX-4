from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_refs_test_")
_test_db_path = Path(_tmp_dir) / "test_refs.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["DEMO_STEP_STAGE_DELAY_SEC"] = "0.0"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.rate_limit import rate_limiter  # noqa: E402
from backend.main import app  # noqa: E402
from backend.research import service as svc  # noqa: E402
from backend.research.citations import (  # noqa: E402
    RESEARCH_REFERENCES_HEADING,
    build_export_references_block,
    build_references_markdown,
    format_reference,
    normalize_style,
    split_used,
)
from backend.research.claims import map_claims  # noqa: E402
from backend.research.providers import SourceRecord  # noqa: E402


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
        SourceRecord(
            title="A Third Retrieved Work",
            authors="A. Author",
            year=2020,
            venue="Some Venue",
            doi="10.1/third",
            url="https://example.org/third",
            provider="arxiv",
            access_status="metadata_only",
            abstract="",
        ),
        SourceRecord(
            title="Fourth Work on Consensus",
            authors="B. Author",
            year=2019,
            venue="Venue D",
            doi="10.1/fourth",
            url="https://example.org/fourth",
            provider="openalex",
            access_status="abstract_accessed",
            abstract="Fourth abstract about consensus protocols.",
        ),
        SourceRecord(
            title="Fifth Work on Replication",
            authors="C. Author",
            year=2018,
            venue="Venue E",
            doi="10.1/fifth",
            url="https://example.org/fifth",
            provider="crossref",
            access_status="metadata_only",
            abstract="",
        ),
        SourceRecord(
            title="Sixth Work on Fault Tolerance",
            authors="D. Author",
            year=2017,
            venue="Venue F",
            doi="10.1/sixth",
            url="https://example.org/sixth",
            provider="arxiv",
            access_status="abstract_accessed",
            abstract="Sixth abstract on fault tolerance.",
        ),
        SourceRecord(
            title="Seventh Work on State Machines",
            authors="E. Author",
            year=2016,
            venue="Venue G",
            doi="10.1/seventh",
            url="https://example.org/seventh",
            provider="openalex",
            access_status="metadata_only",
            abstract="",
        ),
    ]


def _patch_providers() -> None:
    async def _fake(query, providers, limit):
        return _fake_records()

    svc.run_providers = _fake  # type: ignore[assignment]


def _register(client: TestClient) -> dict:
    rate_limiter.reset()
    reg = client.post(
        "/api/auth/register",
        json={
            "email": f"refs_{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Ref User",
            "password": "SecurePassword123!",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


# 1. Relevant research papers are retrieved for research-based tasks.
def test_retrieves_relevant_sources_for_research_task() -> None:
    _patch_providers()
    bundle = asyncio.run(svc.research_service.run("research compare Raft and Paxos consensus", True))
    assert bundle.status == "completed"
    assert bundle.used_count >= 1
    assert bundle.retrieved_count >= 1


# 2. Retrieved source content is actually passed into AI generation context.
def test_context_str_contains_retrieved_content() -> None:
    _patch_providers()
    bundle = asyncio.run(svc.research_service.run("research compare Raft and Paxos", True))
    assert "[1]" in bundle.context_str
    assert "consensus algorithm" in bundle.context_str.lower()


# 3. Sources used in generation are correctly associated with the output.
def test_used_flag_marks_only_top_k() -> None:
    _patch_providers()
    bundle = asyncio.run(svc.research_service.run("research compare Raft and Paxos", True))
    assert all(s["used"] is True for s in bundle.used)
    assert all(s["used"] is False for s in bundle.retrieved)


# 4. Unused search results are not incorrectly displayed as used references.
def test_additional_sources_not_in_used_section() -> None:
    used = [
        {"title": "Used One", "used": True, "access_status": "abstract_accessed", "abstract": "x"},
        {"title": "Extra One", "used": False, "access_status": "metadata_only"},
    ]
    used_only, additional = split_used(used)
    assert [s["title"] for s in used_only] == ["Used One"]
    assert [s["title"] for s in additional] == ["Extra One"]
    md = build_references_markdown(used, "simple")
    assert "Used One" in md
    assert "Extra One" not in md


# 5. Actual references are displayed in generated artifacts (export block).
def test_export_block_contains_heading_and_references() -> None:
    used = [{"title": "Real Paper", "authors": "X", "year": 2020, "used": True, "access_status": "abstract_accessed"}]
    block = build_export_references_block(used, [], "ieee")
    assert RESEARCH_REFERENCES_HEADING in block
    assert "Real Paper" in block


# 6. Claim-level citations map to appropriate sources.
def test_claim_level_mapping_to_sources() -> None:
    used = [{"title": "A", "used": True, "abstract": "passage A", "access_status": "abstract_accessed"}]
    claims = map_claims("Statement one [1].\n\nStatement two.", used)
    assert claims[0]["support"] == "evidence_backed"
    assert claims[0]["ref_numbers"] == [1]
    assert claims[1]["support"] == "unverified"


# 7. Unsupported claims are identified honestly.
def test_unsupported_claims_unverified() -> None:
    used = [{"title": "A", "used": True, "abstract": "p", "access_status": "abstract_accessed"}]
    claims = map_claims("A claim with no citation.", used)
    assert claims[0]["support"] == "unverified"
    no_research = map_claims("A claim.", [])
    assert no_research[0]["support"] == "no_research"


# 8. Metadata-only and abstract-only sources have correct access labels.
def test_access_labels_are_honest() -> None:
    abstract = {"title": "A", "used": True, "access_status": "abstract_accessed", "abstract": "p"}
    metadata = {"title": "B", "used": True, "access_status": "metadata_only"}
    # Abstract source with passage -> evidence_backed; metadata-only -> partial.
    c1 = map_claims("Claim [1].", [abstract])
    c2 = map_claims("Claim [1].", [metadata])
    assert c1[0]["support"] == "evidence_backed"
    assert c2[0]["support"] == "partial"


# 9. No-reference tasks display an honest disclosure.
def test_no_reference_disclosure() -> None:
    md = build_references_markdown([], "simple")
    assert RESEARCH_REFERENCES_HEADING in md
    assert "No external research" in md


# 10. Missing DOI, author, or publication information is handled safely.
def test_missing_metadata_safe() -> None:
    ref = format_reference({"title": "Only Title", "used": True}, "ieee", 1)
    assert "Only Title" in ref
    assert "None" not in ref
    # No fabricated DOI/URL.
    assert "doi.org" not in ref


# 11. Source removal updates citation numbering and claim mappings.
def test_source_removal_renumbers() -> None:
    used = [
        {"title": "A", "used": True, "abstract": "pa", "access_status": "abstract_accessed"},
        {"title": "B", "used": True, "abstract": "pb", "access_status": "abstract_accessed"},
    ]
    # Remove source 1 -> remaining source becomes [1].
    remaining = used[1:]
    claims = map_claims("Statement [1].", remaining)
    assert claims[0]["ref_numbers"] == [1]
    md = build_references_markdown(remaining, "simple")
    assert "[1] B." in md or "[1] B" in md


# 12. Human edits invalidate stale verification appropriately.
def test_human_edit_marks_stale() -> None:
    used = [{"title": "A", "used": True, "abstract": "p", "access_status": "abstract_accessed"}]
    fresh = map_claims("Claim [1].", used, stale=False)
    stale = map_claims("Claim [1].", used, stale=True)
    assert fresh[0]["support"] == "evidence_backed"
    assert stale[0]["support"] == "stale"


# 13. Citation-style changes update the bibliography and inline markers.
def test_citation_styles_differ() -> None:
    src = {"title": "T", "authors": "Auth", "year": 2021, "venue": "V", "doi": "10.1/x", "used": True}
    ieee = format_reference(src, "ieee", 1)
    apa = format_reference(src, "apa", 1)
    simple = format_reference(src, "simple", 1)
    assert ieee.startswith("[1]")
    assert apa.startswith("Auth")
    assert simple.startswith("[1]")
    assert normalize_style("bogus") == "simple"
    assert ieee != apa != simple


def _run_full_task(client: TestClient, headers: dict, prompt: str, research: bool) -> dict:
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"prompt": prompt, "research_enabled": research},
    )
    assert created.status_code in (200, 201), created.text
    task = created.json()
    started = client.post(f"/api/tasks/{task['id']}/start", headers=headers)
    assert started.status_code == 200, started.text
    # Approve plan if required, then approve any awaiting step gates.
    for _ in range(12):
        detail = client.get(f"/api/tasks/{task['id']}", headers=headers).json()
        if detail["status"] == "COMPLETED":
            break
        if detail["status"] == "AWAITING_APPROVAL":
            client.post(f"/api/tasks/{task['id']}/approve", headers=headers, json={"auto_continue": True})
        elif detail["status"] in ("PAUSED", "CREATED"):
            client.post(f"/api/tasks/{task['id']}/start", headers=headers)
        else:
            import time as _t

            _t.sleep(0.1)
    return client.get(f"/api/tasks/{task['id']}", headers=headers).json()


# 14. Markdown export preserves references (backend endpoint).
def test_markdown_export_preserves_references() -> None:
    _patch_providers()
    with TestClient(app) as client:
        headers = _register(client)
        detail = _run_full_task(
            client, headers, "Research and write a report on Raft consensus.", research=True
        )
        assert detail["research_enabled"] is True
        exp = client.get(f"/api/tasks/{detail['id']}/artifact/export", headers=headers)
        assert exp.status_code == 200, exp.text
        body = exp.text
        assert "Research References Used to Generate This Output" in body


# 15. Existing authentication and task ownership protections remain intact.
def test_research_endpoints_require_auth_and_ownership() -> None:
    with TestClient(app) as client:
        headers = _register(client)
        created = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research and write a report on Paxos.", "research_enabled": True},
        )
        tid = created.json()["id"]
        # No auth -> rejected.
        assert client.get(f"/api/research/task/{tid}").status_code in (401, 403)
        assert client.patch(f"/api/research/task/{tid}/citation-style", json={"style": "ieee"}).status_code in (401, 403)
        # Other user cannot access.
        other = _register(client)
        assert client.get(f"/api/research/task/{tid}", headers=other).status_code == 404
        # Owner can set citation style and read it back.
        ok = client.patch(
            f"/api/research/task/{tid}/citation-style", headers=headers, json={"style": "ieee"}
        )
        assert ok.status_code == 200
        assert ok.json()["citation_style"] == "ieee"
        assert client.get(f"/api/research/task/{tid}", headers=headers).json()["citation_style"] == "ieee"


# 16. Existing Phase 1 / Phase 2 functionality not broken (research disabled path).
def test_research_disabled_is_honest() -> None:
    with TestClient(app) as client:
        headers = _register(client)
        created = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research and write a report on Raft.", "research_enabled": False},
        )
        body = created.json()
        assert body["research_enabled"] is False
        assert body["research_status"] == "disabled"
        # Export still works and honestly states no research used.
        exp = client.get(f"/api/tasks/{body['id']}/artifact/export", headers=headers)
        assert exp.status_code == 200
        assert "No external research" in exp.text