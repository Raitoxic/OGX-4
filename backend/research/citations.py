"""Single shared citation-formatting engine (IEEE / APA 7th / Simple Numbered).

This is the ONLY citation formatter in the codebase. The artifact renderer, the
Markdown/PDF export, and any server-side references section all call into this
module so citation style stays consistent across the entire workflow.

It never fabricates metadata: missing authors / year / venue / DOI / URL are
simply omitted. It does not prove scientific correctness — it only formats the
bibliographic records that were actually retrieved and supplied to generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

RESEARCH_REFERENCES_HEADING = "Research References Used to Generate This Output"
ADDITIONAL_HEADING = "Additional Sources Retrieved"

VALID_STYLES = ("simple", "ieee", "apa")
DEFAULT_STYLE = "simple"

# Honest, non-conflating access-status labels. ``abstract_accessed`` is NOT
# full-text verification and is labelled as such.
ACCESS_STATUS_LABELS: Dict[str, str] = {
    "retrieved_full": "Full text accessed",
    "retrieved_partial": "Abstract / partial accessed",
    "abstract_accessed": "Abstract accessed (not full text)",
    "metadata_only": "Metadata only — not retrieved",
    "demo_metadata_only": "Demo metadata — not retrieved",
    "user_provided": "User-provided",
    "internal_trace": "Internal trace (not external)",
    "unverified": "Unverified",
    "not_verified": "Not verified",
}


def normalize_style(style: Optional[str]) -> str:
    s = (style or "").strip().lower()
    return s if s in VALID_STYLES else DEFAULT_STYLE


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _authors(source: Dict[str, Any]) -> str:
    return _clean(source.get("authors"))


def _title(source: Dict[str, Any]) -> str:
    return _clean(source.get("title")) or "Untitled source"


def _year(source: Dict[str, Any]) -> str:
    y = source.get("year")
    return _clean(y)


def _venue(source: Dict[str, Any]) -> str:
    return _clean(source.get("venue"))


def _doi(source: Dict[str, Any]) -> str:
    return _clean(source.get("doi"))


def _url(source: Dict[str, Any]) -> str:
    url = _clean(source.get("url"))
    if url:
        return url
    ref = _clean(source.get("reference"))
    if ref.lower().startswith("http"):
        return ref
    return ""


def _doi_line(source: Dict[str, Any]) -> str:
    doi = _doi(source)
    if not doi:
        return ""
    return f" DOI: {doi if doi.lower().startswith('http') else f'https://doi.org/{doi}'}."


def _url_line(source: Dict[str, Any]) -> str:
    if _doi(source):
        return ""
    url = _url(source)
    return f" Available: {url}" if url else ""


def format_reference(source: Dict[str, Any], style: Optional[str], n: int) -> str:
    """Format one source as a numbered reference string in the chosen style."""
    style = normalize_style(style)
    authors = _authors(source)
    title = _title(source)
    year = _year(source)
    venue = _venue(source)
    doi_line = _doi_line(source)
    url_line = _url_line(source)

    if style == "ieee":
        a = f"{authors}, " if authors else ""
        v = f"{venue}, " if venue else ""
        y = f"{year}." if year else ""
        raw = f'[{n}] {a}"{title}," {v}{y}{doi_line}{url_line}'
    elif style == "apa":
        a = f"{authors} " if authors else ""
        y = f"({year}). " if year else ""
        v = f"{venue}. " if venue else ""
        raw = f"{a}{y}{title}. {v}{doi_line}{url_line}"
    else:  # simple numbered
        v = f"{venue}, " if venue else ""
        y = f"{year}." if year else ""
        raw = f"[{n}] {title}. {v}{y}{doi_line}{url_line}"

    return " ".join(raw.split()).strip()


def access_label(source: Dict[str, Any]) -> str:
    key = _clean(source.get("access_status"))
    if key in ACCESS_STATUS_LABELS:
        return ACCESS_STATUS_LABELS[key]
    stype = _clean(source.get("type"))
    if stype == "demo_reference":
        return ACCESS_STATUS_LABELS["demo_metadata_only"]
    if stype == "user_input":
        return ACCESS_STATUS_LABELS["user_provided"]
    if stype == "internal_trace":
        return ACCESS_STATUS_LABELS["internal_trace"]
    return ACCESS_STATUS_LABELS["not_verified"]


def is_used(source: Dict[str, Any]) -> bool:
    """A source counts as 'used' only when explicitly flagged and not disabled."""
    return source.get("used") is not False


def split_used(used_sources: List[Dict[str, Any]]):
    used = [s for s in used_sources if is_used(s)]
    additional = [s for s in used_sources if not is_used(s)]
    return used, additional


def build_references_markdown(used_sources: List[Dict[str, Any]], style: Optional[str]) -> str:
    """Markdown block for the 'Research References Used' section (used only)."""
    style = normalize_style(style)
    used, _ = split_used(used_sources)
    lines = [f"## {RESEARCH_REFERENCES_HEADING}", ""]
    if not used:
        lines.append(
            "_No external research was used to generate this output "
            "(research disabled, not requested, or no relevant sources retrieved)._"
        )
        return "\n".join(lines)
    for i, s in enumerate(used, start=1):
        lines.append(format_reference(s, style, i))
        detail = []
        if _authors(s):
            detail.append(f"Authors: {_authors(s)}")
        if _year(s):
            detail.append(f"Year: {_year(s)}")
        if _venue(s):
            detail.append(f"Venue: {_venue(s)}")
        if _clean(s.get("provider")):
            detail.append(f"Provider: {_clean(s.get('provider'))}")
        detail.append(f"Access: {access_label(s)}")
        if _doi(s):
            doi = _doi(s)
            detail.append(f"DOI: {doi if doi.lower().startswith('http') else f'https://doi.org/{doi}'}")
        elif _url(s):
            detail.append(f"Original publication: {_url(s)}")
        lines.append("  " + " · ".join(detail))
    return "\n".join(lines)


def build_additional_markdown(retrieved_sources: List[Dict[str, Any]]) -> str:
    _, additional = split_used(retrieved_sources)
    if not additional:
        return ""
    lines = [f"### {ADDITIONAL_HEADING}", ""]
    for s in additional:
        provider = _clean(s.get("provider"))
        lines.append(f"- {_title(s)}{f' — {provider}' if provider else ''} ({access_label(s)})")
    return "\n".join(lines)


def build_export_references_block(
    used_sources: List[Dict[str, Any]],
    retrieved_sources: List[Dict[str, Any]],
    style: Optional[str],
    provider_mode: Optional[str] = None,
) -> str:
    """Consolidated references block for Markdown / PDF export."""
    parts = [build_references_markdown(used_sources, style)]
    additional = build_additional_markdown(retrieved_sources)
    if additional:
        parts.append("")
        parts.append(additional)
    if provider_mode == "demo":
        parts.append("")
        parts.append(
            "_Note: generated in Deterministic Demo Mode; live external research context "
            "is not consumed by the offline generator._"
        )
    return "\n".join(parts).strip()