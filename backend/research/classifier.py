"""Conditional research classifier.

Research is only performed when the task plausibly needs external sources and
the user has not explicitly disabled it. Simple coding/formatting/calculation
tasks skip retrieval.
"""

from __future__ import annotations

import re
from typing import Tuple

_RESEARCH_HINTS = (
    "research",
    "survey",
    "literature",
    "state of the art",
    "compare",
    "comparison",
    "trade-off",
    "tradeoff",
    "paper",
    "papers",
    "study",
    "studies",
    "evidence",
    "citation",
    "references",
    "report on",
    "write a report",
    "technical report",
    "findings",
    "benchmark",
)

_SIMPLE_HINTS = (
    "calculate",
    "compute",
    "format",
    "convert",
    "regex",
    "rename",
    "sort these",
    "fix this code",
    "write a function",
    "unit test",
)


def should_research(prompt: str, explicit: bool) -> Tuple[bool, str]:
    """Return (enabled, reason).

    ``explicit`` reflects an explicit user toggle. When explicitly disabled we
    never research; when explicitly enabled we research unless the task is an
    obvious simple utility task.
    """
    text = (prompt or "").lower()
    if explicit is False and _looks_simple(text):
        return False, "Simple utility task; external research skipped."
    if explicit:
        return True, "Research explicitly enabled by user."
    if any(h in text for h in _SIMPLE_HINTS) and not any(h in text for h in _RESEARCH_HINTS):
        return False, "Simple utility task; external research skipped."
    if any(h in text for h in _RESEARCH_HINTS):
        return True, "Task appears to require external research."
    return False, "No research intent detected; skipped."


def _looks_simple(text: str) -> bool:
    return any(h in text for h in _SIMPLE_HINTS) and not any(h in text for h in _RESEARCH_HINTS)


def extract_keywords(prompt: str, limit: int = 8) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]{2,}", prompt or "")
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "into", "your",
        "their", "there", "when", "what", "which", "while", "about", "would",
        "should", "could", "write", "report", "research", "structured",
    }
    seen = []
    for w in words:
        lw = w.lower()
        if lw in stop:
            continue
        if lw not in seen:
            seen.append(lw)
        if len(seen) >= limit:
            break
    return " ".join(seen) or (prompt or "")[:120]