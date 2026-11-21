"""Deduplication logic: exact ID check and rapidfuzz title similarity."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

# Outlet suffixes commonly appended to feed titles
OUTLET_SUFFIX_RE = re.compile(
    r"\s*[-|–—]\s*(?:"
    r"entrackr|inc42|yourstory|crunchbase news|techcrunch|venturebeat|reuters|bloomberg"
    r").*$",
    re.IGNORECASE,
)

# Strip non-alphanumeric characters (keeping spaces)
PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_title(title: str) -> str:
    """
    Normalize title for fuzzy comparison:
    1. Lowercase.
    2. Strip outlet name suffixes.
    3. Strip punctuation.
    4. Collapse whitespace.
    """
    if not title:
        return ""

    lowered = title.strip().lower()

    # Remove outlet suffix
    stripped_suffix = OUTLET_SUFFIX_RE.sub("", lowered)

    # Remove punctuation
    stripped_punct = PUNCTUATION_RE.sub(" ", stripped_suffix)

    # Normalize whitespace
    normalized = " ".join(stripped_punct.split())
    return normalized


def is_fuzzy_duplicate(
    candidate_title: str,
    recent_titles: list[str],
    threshold: float = 90.0,
) -> bool:
    """
    Check if a candidate title is a fuzzy duplicate of any recently seen title.
    Uses rapidfuzz.fuzz.token_set_ratio with default threshold 90.0.
    """
    norm_candidate = normalize_title(candidate_title)
    if not norm_candidate:
        return False

    for existing in recent_titles:
        norm_existing = normalize_title(existing)
        if not norm_existing:
            continue

        score = fuzz.token_set_ratio(norm_candidate, norm_existing)
        if score >= threshold:
            return True

    return False
