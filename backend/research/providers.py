"""Normalized research providers (OpenAlex, Crossref, arXiv).

Each provider returns ``SourceRecord`` objects with honest ``access_status``:
- ``abstract_accessed`` when an abstract/summary was retrieved.
- ``metadata_only`` when only bibliographic metadata is available.

Full text is never claimed. No fabricated authors/DOI/years/URLs.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from backend.core.config import settings
from backend.research.security import safe_fetch, safe_fetch_json


@dataclass
class SourceRecord:
    title: str
    authors: str = ""
    year: Optional[Any] = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    provider: str = ""
    access_status: str = "metadata_only"
    abstract: str = ""
    used: bool = False
    filename: str = ""
    page: Optional[int] = None

    def to_source_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "type": "research_paper",
            "reference": self.url or (f"https://doi.org/{self.doi}" if self.doi else ""),
            "reliability_note": f"Retrieved via {self.provider}; {self.access_status.replace('_', ' ')}.",
            "authors": self.authors or None,
            "year": self.year,
            "venue": self.venue or None,
            "doi": self.doi or None,
            "url": self.url or None,
            "provider": self.provider,
            "access_status": self.access_status,
            "used": self.used,
            "filename": self.filename or None,
            "page": self.page,
        }


def _clean_authors(names: List[str]) -> str:
    return ", ".join(n.strip() for n in names if n and n.strip())


async def search_openalex(query: str, limit: int) -> List[SourceRecord]:
    url = (
        "https://api.openalex.org/works?search="
        + quote(query)
        + f"&per-page={limit}&mailto=research@vyrox.local"
    )
    data = await safe_fetch_json(url)
    if not isinstance(data, dict):
        return []
    out: List[SourceRecord] = []
    for w in data.get("results", [])[:limit]:
        authorships = w.get("authorships") or []
        authors = _clean_authors([a.get("author", {}).get("display_name", "") for a in authorships])
        abstract = _reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
        loc = w.get("primary_location") or {}
        source = loc.get("source") or {}
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        out.append(
            SourceRecord(
                title=(w.get("title") or "Untitled").strip(),
                authors=authors,
                year=w.get("publication_year"),
                venue=source.get("display_name", "") or "",
                doi=doi,
                url=(w.get("id") or (f"https://doi.org/{doi}" if doi else "")),
                provider="openalex",
                access_status="abstract_accessed" if abstract else "metadata_only",
                abstract=abstract,
            )
        )
    return out


def _reconstruct_openalex_abstract(inv: Optional[Dict[str, Any]]) -> str:
    if not isinstance(inv, dict) or not inv:
        return ""
    positions: List[tuple] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in positions)[:1200]


async def search_crossref(query: str, limit: int) -> List[SourceRecord]:
    url = f"https://api.crossref.org/works?query={quote(query)}&rows={limit}"
    data = await safe_fetch_json(url)
    if not isinstance(data, dict):
        return []
    message = data.get("message") or {}
    out: List[SourceRecord] = []
    for it in message.get("items", [])[:limit]:
        authors = _clean_authors(
            [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", []) or []]
        )
        issued = (it.get("issued") or {}).get("date-parts") or [[None]]
        year = issued[0][0] if issued and issued[0] else None
        title = (it.get("title") or ["Untitled"])[0]
        venue = (it.get("container-title") or [""])[0]
        doi = it.get("DOI", "")
        abstract = _strip_jats(it.get("abstract", ""))
        out.append(
            SourceRecord(
                title=(title or "Untitled").strip(),
                authors=authors,
                year=year,
                venue=venue or "",
                doi=doi,
                url=it.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
                provider="crossref",
                access_status="abstract_accessed" if abstract else "metadata_only",
                abstract=abstract,
            )
        )
    return out


def _strip_jats(raw: str) -> str:
    if not raw:
        return ""
    try:
        return " ".join(ET.fromstring(f"<x>{raw}</x>").itertext())[:1200]
    except ET.ParseError:
        return raw[:1200]


async def search_arxiv(query: str, limit: int) -> List[SourceRecord]:
    url = (
        "http://export.arxiv.org/api/query?search_query=all:"
        + quote(query)
        + f"&start=0&max_results={limit}"
    )
    try:
        status, body, _ = await safe_fetch(url)
    except Exception:
        return []
    if status != 200:
        return []
    try:
        root = ET.fromstring(body.decode("utf-8", errors="replace"))
    except ET.ParseError:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: List[SourceRecord] = []
    for entry in root.findall("a:entry", ns)[:limit]:
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        authors = _clean_authors(
            [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)]
        )
        published = entry.findtext("a:published", default="", namespaces=ns)
        year = published[:4] if published[:4].isdigit() else None
        url_val = entry.findtext("a:id", default="", namespaces=ns).strip()
        doi = ""
        out.append(
            SourceRecord(
                title=title or "Untitled",
                authors=authors,
                year=year,
                venue="arXiv",
                doi=doi,
                url=url_val,
                provider="arxiv",
                access_status="abstract_accessed" if summary else "metadata_only",
                abstract=summary[:1200],
            )
        )
    return out


PROVIDERS = {
    "openalex": search_openalex,
    "crossref": search_crossref,
    "arxiv": search_arxiv,
    "local_pdf": None,  # populated below (DB-backed local corpus)
}


async def search_local_pdf(query: str, limit: int) -> List[SourceRecord]:
    """Search the ingested local PDF corpus (DB-backed), returning page-level chunks.

    Reuses the same ``SourceRecord``/ranking pipeline as remote providers. The
    chunk text becomes the ``abstract`` so it flows into the generation context.
    """
    from sqlalchemy import or_

    from backend.database.session import SessionLocal
    from backend.models.pdf import PdfChunk, PdfDocument
    from backend.research.pdf_ingest import ensure_ingested

    tokens = [t for t in (query or "").lower().split() if t]
    if not tokens:
        return []
    db = SessionLocal()
    try:
        ensure_ingested(db)
        clauses = [PdfChunk.content.ilike(f"%{t}%") for t in tokens]
        rows = (
            db.query(PdfChunk, PdfDocument)
            .join(PdfDocument, PdfChunk.document_id == PdfDocument.id)
            .filter(or_(*clauses))
            .limit(max(limit * 4, 8))
            .all()
        )
        scored = []
        for chunk, doc in rows:
            hay = (chunk.content or "").lower()
            score = sum(1 for t in tokens if t in hay)
            if score > 0:
                scored.append((score, chunk, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: List[SourceRecord] = []
        for _score, chunk, doc in scored[:limit]:
            out.append(
                SourceRecord(
                    title=doc.title or doc.filename,
                    authors=doc.authors or "",
                    year=doc.year or None,
                    venue=doc.venue or "",
                    doi=doc.doi or "",
                    url="",
                    provider="local_pdf",
                    access_status="pdf_excerpt",
                    abstract=chunk.content or "",
                    filename=doc.filename,
                    page=chunk.page,
                )
            )
        return out
    finally:
        db.close()


PROVIDERS["local_pdf"] = search_local_pdf


async def run_providers(query: str, providers: List[str], limit: int) -> List[SourceRecord]:
    results: List[SourceRecord] = []
    for name in providers:
        fn = PROVIDERS.get(name)
        if not fn:
            continue
        try:
            results.extend(await fn(query, limit))
        except Exception:
            # A failing provider must never abort the whole research step.
            continue
    return results