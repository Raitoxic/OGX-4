"""Heuristic claim-to-source mapping.

This does NOT prove scientific correctness. It only associates generated
paragraphs with the references that were actually supplied to the model and
labels support honestly. Structural/heuristic support is never presented as
proof.

Labels:
- ``evidence_backed``: paragraph carries an inline ``[n]`` marker whose source
  supplied accessed content (an abstract / partial passage).
- ``partial``: paragraph cites a source that was only available as metadata
  (no accessed passage), so the claim cannot be fully corroborated.
- ``unverified``: paragraph has no supporting marker while used sources exist.
- ``stale``: a previously supported claim whose section was edited by a human
  and has not been re-verified.
- ``no_research``: no used sources at all — a general AI explanation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

LABELS = {
    "evidence_backed": "Evidence-backed by accessed material",
    "partial": "Partially supported",
    "unverified": "Unverified claim",
    "stale": "Stale after human editing",
    "no_research": "General AI-generated explanation (no external research used)",
}


def _paragraphs(content: str) -> List[str]:
    parts = re.split(r"\n\s*\n", content or "")
    out: List[str] = []
    for p in parts:
        t = p.strip()
        if not t:
            continue
        if t.startswith("#") or t.startswith("|") or t.startswith(">") or t.startswith("- "):
            continue
        if re.match(r"^\d+\.\s", t):
            continue
        out.append(t)
    return out


def _has_accessed_passage(source: Dict[str, Any]) -> bool:
    status = (source.get("access_status") or "").strip()
    if status in ("metadata_only", "demo_metadata_only", "unverified", "not_verified"):
        return False
    # abstract_accessed / retrieved_full / retrieved_partial / user_provided
    return bool((source.get("abstract") or "").strip()) or status in (
        "retrieved_full",
        "retrieved_partial",
        "abstract_accessed",
        "user_provided",
    )


def map_claims(
    content: str,
    used_sources: List[Dict[str, Any]],
    stale: bool = False,
) -> List[Dict[str, Any]]:
    """Map each paragraph to supporting used sources.

    Inline ``[n]`` markers in the text take precedence. Without markers, a
    paragraph is marked unverified unless there are no used sources at all, in
    which case it is a general explanation. When ``stale`` is True, previously
    supported claims are relabelled ``stale`` (human edit not yet re-verified).
    """
    used = [s for s in used_sources if s.get("used", True)]
    claims: List[Dict[str, Any]] = []
    for idx, para in enumerate(_paragraphs(content), start=1):
        markers = [int(m) for m in re.findall(r"\[(\d+)\]", para) if 1 <= int(m) <= len(used)]
        passage = ""
        if markers:
            primary = used[markers[0] - 1]
            support = "evidence_backed" if _has_accessed_passage(primary) else "partial"
            refs = markers
            passage = primary.get("abstract") or ""
        elif not used:
            support = "no_research"
            refs = []
        else:
            support = "unverified"
            refs = []

        if stale and support in ("evidence_backed", "partial"):
            support = "stale"

        claims.append(
            {
                "index": idx,
                "text": para[:280],
                "support": support,
                "support_label": LABELS[support],
                "ref_numbers": refs,
                "supporting_passage": passage[:400],
            }
        )
    return claims