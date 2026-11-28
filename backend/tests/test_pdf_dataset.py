from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_pdf_test_")
_test_db_path = Path(_tmp_dir) / "test_pdf.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from backend.database.session import SessionLocal  # noqa: E402
from backend.database.init_db import init_db  # noqa: E402

init_db()

from backend.research import pdf_ingest  # noqa: E402
from backend.research.citations import (  # noqa: E402
    RESEARCH_REFERENCES_HEADING,
    build_references_markdown,
    format_reference,
)
from backend.research.providers import search_local_pdf  # noqa: E402

DATASET_DIR = pdf_ingest.DATASET_DIR


def test_dataset_pdfs_present_and_readable() -> None:
    pdfs = sorted(DATASET_DIR.glob("*.pdf"))
    assert len(pdfs) >= 1, "expected at least one PDF in the dataset folder"
    db = SessionLocal()
    try:
        docs = pdf_ingest.ingest_all(db)
    finally:
        db.close()
    assert len(docs) == len(pdfs)
    for d in docs:
        assert d["status"] == "indexed", d
        assert d["page_count"] > 0
        assert d["chunk_count"] > 0


def test_text_extraction_and_page_numbers() -> None:
    db = SessionLocal()
    try:
        pdf_ingest.ingest_all(db)
        from backend.models.pdf import PdfChunk

        chunks = db.query(PdfChunk).all()
        assert chunks, "no chunks extracted"
        assert all(c.page >= 1 for c in chunks)
        assert all(len(c.content.strip()) > 0 for c in chunks)
    finally:
        db.close()


def test_metadata_verified_only() -> None:
    db = SessionLocal()
    try:
        docs = pdf_ingest.ingest_all(db)
    finally:
        db.close()
    for d in docs:
        # Never fabricated: absent metadata stays None, never invented placeholders.
        if d["title"] is not None:
            assert d["title"].strip() != ""
        if d["doi"] is not None:
            assert d["doi"].startswith("10.")


def test_local_pdf_retrieval_returns_pages() -> None:
    db = SessionLocal()
    try:
        pdf_ingest.ingest_all(db)
    finally:
        db.close()
    records = asyncio.run(search_local_pdf("cloud intrusion detection survey", 5))
    assert records, "expected local PDF retrieval results"
    r = records[0]
    assert r.provider == "local_pdf"
    assert r.access_status == "pdf_excerpt"
    assert r.filename  # points to an actual uploaded document
    assert r.page is not None and r.page >= 1


def test_citation_includes_filename_and_page() -> None:
    src = {
        "title": "Intrusion Detection Survey",
        "authors": "Preeti Mishra",
        "year": "2016",
        "used": True,
        "provider": "local_pdf",
        "access_status": "pdf_excerpt",
        "filename": "cloud_intrusion_survey.pdf",
        "page": 12,
    }
    for style in ("ieee", "apa", "simple"):
        ref = format_reference(src, style, 1)
        assert "cloud_intrusion_survey.pdf" in ref
        assert "p. 12" in ref
    md = build_references_markdown([src], "simple")
    assert RESEARCH_REFERENCES_HEADING in md
    assert "cloud_intrusion_survey.pdf" in md


def test_retrieved_sources_point_to_actual_documents() -> None:
    db = SessionLocal()
    try:
        docs = pdf_ingest.ingest_all(db)
    finally:
        db.close()
    filenames = {d["filename"] for d in docs}
    records = asyncio.run(search_local_pdf("cloud computing security", 5))
    assert records
    for r in records:
        assert r.filename in filenames


def test_ingest_is_idempotent() -> None:
    db = SessionLocal()
    try:
        first = pdf_ingest.ingest_all(db)
        second = pdf_ingest.ingest_all(db)
    finally:
        db.close()
    assert len(first) == len(second)
    from backend.models.pdf import PdfDocument

    db = SessionLocal()
    try:
        assert db.query(PdfDocument).count() == len(first)
    finally:
        db.close()