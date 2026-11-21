"""Article filtering by funding, sector, geo, and exclusion keywords."""

from __future__ import annotations

import re
from re import Pattern

from fundwatch.models import Article, FilterConfig

# Compile cache for keyword patterns
_PATTERN_CACHE: dict[str, Pattern[str]] = {}


def _compile_keyword_pattern(keyword: str) -> Pattern[str]:
    """Compile a case-insensitive regex for a keyword or phrase with word boundaries."""
    if keyword not in _PATTERN_CACHE:
        # Escape keyword and wrap with boundary checks
        escaped = re.escape(keyword.strip().lower())
        # Support word boundaries for words and alphanumeric phrases
        pattern_str = rf"(?:\b|\A){escaped}(?:\b|\Z)"
        _PATTERN_CACHE[keyword] = re.compile(pattern_str, re.IGNORECASE)
    return _PATTERN_CACHE[keyword]


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    """Return True if text matches at least one keyword using word boundaries."""
    if not text or not keywords:
        return False
    return any(
        _compile_keyword_pattern(kw).search(text) is not None for kw in keywords if kw.strip()
    )


# Default negative / false-positive phrases that indicate non-funding news
DEFAULT_FALSE_POSITIVE_PHRASES = [
    "raises concerns",
    "raises questions",
    "raises alarm",
    "raises doubts",
    "raises eyebrows",
    "raises fears",
    "funding cuts",
    "funding cut",
    "funding freeze",
    "funding crisis",
    "funding slashed",
    "funding drops",
    "funding dry",
]


def is_funding_item(article: Article, cfg: FilterConfig) -> bool:
    """
    Check if an article matches funding criteria and passes sector, geo, and exclude filters.

    Rules:
    1. Must match at least one exclude_keywords (or default false positive phrases) -> False.
    2. Must match at least one funding_keywords in title (or summary if match_in_summary) -> True.
    3. If sector_keywords is non-empty, must match at least one -> otherwise False.
    4. If geo_keywords is non-empty, must match at least one -> otherwise False.
    """
    title = article.title or ""
    summary = article.summary or ""

    # Text for funding keyword matching
    if cfg.match_in_summary and summary:
        funding_search_text = f"{title} {summary}"
    else:
        funding_search_text = title

    # Combined text for sector, geo, and exclusion
    full_text = f"{title} {summary}".strip()

    # 1. Check exclusions (user-configured + common false-positives)
    all_exclusions = list(cfg.exclude_keywords) + DEFAULT_FALSE_POSITIVE_PHRASES
    if _matches_any_keyword(full_text, all_exclusions):
        return False

    # 2. Check funding keywords
    if not cfg.funding_keywords:
        return False
    if not _matches_any_keyword(funding_search_text, cfg.funding_keywords):
        return False

    # 3. Check sector keywords (if configured)
    if cfg.sector_keywords and not _matches_any_keyword(full_text, cfg.sector_keywords):
        return False

    # 4. Check geo keywords (if configured)
    if cfg.geo_keywords and not _matches_any_keyword(full_text, cfg.geo_keywords):
        return False

    return True
