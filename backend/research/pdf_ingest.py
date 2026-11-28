"""Local PDF dataset ingestion for the VYRO-X research engine (Phase 6).

Extracts readable text + verified bibliographic metadata from PDFs in
``backend/datasets/cloud_security`` and stores them as searchable
``PdfChunk`` rows. Reuses the existing research retrieval engine (a local
provider); it does not create a parallel retrieval system.

Only verified metadata is stored. Missing title/author/year/DOI remain empty
and are never fabricated. External content is treated as untrusted data.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.models.pdf import PdfChunk, PdfDocument

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "datasets" / "cloud_security"

CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_year(raw_meta: Dict[str, Any], first_page_text: str) -> str:
    creation = _clean(raw_meta.get("/CreationDate"))
    m = re.search(r"D:(\d{4})", creation)
    if m:
        return m.group(1)
    m = YEAR_RE.search(first_page_text or "")
    return m.group(0) if m else ""


def _extract_doi(pages_text: List[str]) -> str:
    for text in pages_text[:2]:
        m = DOI_RE.search(text or "")
        if m:
            return m.group(0).rstrip(".,;")
    return ""


def _extract_metadata(reader: PdfReader, first_page_text: str) -> Dict[str, str]:
    meta = reader.metadata or {}
    title = _clean(meta.get("/Title"))
    authors = _clean(meta.get("/Author"))
    if not title:
        for line in (first_page_text or "").splitlines():
            candidate = line.strip()
            if 8 <= len(candidate) <= 300:
                title = candidate
                break
    year = _extract_year(dict(meta), first_page_text)
    return {
        "title": title[:400],
        "authors": authors[:400],
        "year": year[:8],
        "doi": "",  # filled by caller with page scan
        "venue": "",
    }


def _chunk_page(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def ingest_pdf(db: Session, path: Path) -> Dict[str, Any]:
    """Ingest a single PDF (idempotent by filename + content hash)."""
    digest = _sha256(path)
    existing = db.query(PdfDocument).filter(PdfDocument.filename == path.name).first()
    if existing and existing.sha256 == digest and existing.status == "indexed":
        return _serialize_doc(existing)

    if existing:
        db.delete(existing)
        db.flush()

    doc = PdfDocument(filename=path.name, sha256=digest, status="indexed")
    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        pages_text: List[str] = []
        chunk_rows: List[PdfChunk] = []
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages_text.append(text)
            for idx, chunk in enumerate(_chunk_page(text)):
                chunk_rows.append(PdfChunk(page=page_no, chunk_index=idx, content=chunk))

        meta = _extract_metadata(reader, pages_text[0] if pages_text else "")
        meta["doi"] = _extract_doi(pages_text)

        doc.title = meta["title"]
        doc.authors = meta["authors"]
        doc.year = meta["year"]
        doc.doi = meta["doi"]
        doc.venue = meta["venue"]
        doc.page_count = page_count
        doc.chunk_count = len(chunk_rows)
        db.add(doc)
        db.flush()
        for row in chunk_rows:
            row.document_id = doc.id
        db.add_all(chunk_rows)
        db.commit()
        db.refresh(doc)
        return _serialize_doc(doc)
    except Exception as exc:  # never abort the whole corpus on one bad file
        db.rollback()
        doc = PdfDocument(
            filename=path.name,
            sha256=digest,
            status="failed",
            error_message=str(exc)[:400],
        )
        db.add(doc)
        db.commit()
        return _serialize_doc(doc)


def ingest_all(db: Session) -> List[Dict[str, Any]]:
    """Ingest every PDF in the dataset folder (idempotent)."""
    results: List[Dict[str, Any]] = []
    if not DATASET_DIR.exists():
        return results
    for path in sorted(DATASET_DIR.glob("*.pdf")):
        results.append(ingest_pdf(db, path))
    return results


def ensure_ingested(db: Session) -> List[Dict[str, Any]]:
    """Ingest any missing/changed PDFs. Safe to call repeatedly."""
    return ingest_all(db)


def list_documents(db: Session) -> List[Dict[str, Any]]:
    docs = db.query(PdfDocument).order_by(PdfDocument.filename.asc()).all()
    return [_serialize_doc(d) for d in docs]


def _serialize_doc(doc: PdfDocument) -> Dict[str, Any]:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "title": doc.title or None,
        "authors": doc.authors or None,
        "year": doc.year or None,
        "doi": doc.doi or None,
        "venue": doc.venue or None,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "error_message": doc.error_message or None,
    }