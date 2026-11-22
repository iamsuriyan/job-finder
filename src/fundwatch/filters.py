"""Article filtering by funding, sector, geo, and exclusion keywords."""

from __future__ import annotations

import re
from re import Pattern

from fundwatch.models import Article, FilterConfig, StageTier

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

# Patterns indicating general weekly roundups rather than a single funding deal
ROUNDUP_PATTERNS = [
    r"\bfunding roundup\b",
    r"\bstartups raised over\b",
    r"\bstartups this week\b",
    r"\bfunding and acquisitions in\b",
    r"\bweekly funding\b",
    r"\bbiggest funding rounds\b",
    r"\bweekly recap\b",
]

# Patterns indicating financial earnings reports rather than venture capital funding
EARNINGS_PATTERNS = [
    r"\brevenue\s+(?:jumps|surges|grows|drops|up|down)\b",
    r"\blosses\s+(?:shrink|widen|narrow)\b",
    r"\bfinancial\s+results\b",
    r"\bquarterly\s+results\b",
    r"\bfy2[0-9]\b",
]

# Patterns for figurative non-capital uses of "raises" (e.g. "raises stakes", "raises the bar")
FIGURATIVE_RAISES_PATTERNS = [
    r"\braises\s+(?:(?:\w+['’]?s?|\b)\s+){0,5}(?:stakes|bar|doubts|concerns|questions|alarm|eyebrows|fears|hackles)\b",
]

# Pure offline / physical non-tech consumer businesses (fashion, apparel, food)
NON_TECH_PATTERNS = [
    r"\bfashion\b",
    r"\bapparel\b",
    r"\bclothing\b",
    r"\bfootwear\b",
    r"\bfast-fashion\b",
    r"\bathleisure\b",
    r"\bethnic wear\b",
    r"\bjewelry\b",
    r"\bjewellery\b",
    r"\bgarment\b",
    r"\btextile\b",
    r"\bboba\b",
    r"\bbubble tea\b",
    r"\bstreet food\b",
    r"\btea brand\b",
    r"\bcafe chain\b",
    r"\bcoffee chain\b",
    r"\brestaurant chain\b",
    r"\bquick service restaurant\b",
    r"\bqsr\b",
    r"\bcloud kitchen\b",
    r"\bfast food\b",
    r"\bbeverage brand\b",
    r"\bbakery\b",
    r"\bsnack brand\b",
    r"\bpackaged food\b",
    r"\bcosmetics brand\b",
    r"\bsalon chain\b",
    r"\balma mater\b",
    r"\bdonation\b",
]

# Explicit software / SaaS / AI / developer core platform keywords that override a non-tech phrase
SOFTWARE_PLATFORM_OVERRIDES = [
    r"\bsaas\b",
    r"\bsoftware\b",
    r"\bai platform\b",
    r"\bdeveloper tool\b",
    r"\bapi platform\b",
    r"\bcloud platform\b",
]

# Stage classification regex patterns
FIRST_FUNDING_PATTERNS = [
    r"\bpre-?seed\b",
    r"\bangel\s+(?:round|funding|investment|investor)\b",
    r"\bfirst\s+(?:funding|round|check|institutional)\b",
    r"\b(?:emerges?\s+from\s+stealth|out\s+of\s+stealth|stealth\s+(?:round|mode|startup))\b",
    r"\bdebut\s+round\b",
    r"\baccelerator\b",
    r"\by\s+combinator\b",
    r"\byc\b",
]

SEED_PATTERNS = [
    r"\bseed\s+(?:round|funding|capital|extension|investment)\b",
    r"\b(?:raises?|raised|bags?|bagged|secures?|secured|closes?|closed)\s+.*?\bseed\b",
    r"\bseed-stage\b",
]

SERIES_A_PATTERNS = [
    r"\bpre[- ]?series\s*a\b",
    r"\bseries[- ]?a\b",
]

LATE_PATTERNS = [
    r"\bseries[- ]?[c-z]\b",
    r"\bgrowth\s+(?:round|capital|equity)\b",
    r"\bdebt\s+(?:financing|round|facility)\b",
    r"\bcredit\s+facility\b",
    r"\bprivate\s+equity\b",
    r"\bipo\b",
    r"\bbuyout\b",
    r"\bsecondary\s+(?:sale|transaction|round)\b",
]

SERIES_B_PATTERNS = [
    r"\bseries[- ]?b\b",
]

AMOUNT_HEURISTIC_RE = re.compile(
    r"([\$€£₹])\s*(\d+(?:\.\d+)?)\s*(?:million|m|mn|cr|crore)\b",
    re.IGNORECASE,
)


def classify_stage_tier(title: str, summary: str = "") -> StageTier:
    """Classify the funding stage tier of an article, prioritizing the headline round."""
    t_low = title.lower()

    # 1. Headline Stage Checks (highest precision for current round)
    if any(re.search(pat, t_low) for pat in FIRST_FUNDING_PATTERNS):
        return StageTier.FIRST_FUNDING
    if any(re.search(pat, t_low) for pat in SEED_PATTERNS):
        return StageTier.SEED
    if any(re.search(pat, t_low) for pat in SERIES_A_PATTERNS):
        return StageTier.SERIES_A
    if any(re.search(pat, t_low) for pat in SERIES_B_PATTERNS):
        return StageTier.LATE
    if any(re.search(pat, t_low) for pat in LATE_PATTERNS):
        return StageTier.LATE

    # 2. Check headline amount heuristic ($ <= 6M is Seed, <= 20M is Series A)
    m_amt = AMOUNT_HEURISTIC_RE.search(title)
    if m_amt:
        try:
            amt = float(m_amt.group(2))
            is_cr = "cr" in m_amt.group(0).lower()
            limit_seed = 50.0 if is_cr else 6.0
            limit_series_a = 160.0 if is_cr else 20.0
            if amt <= limit_seed:
                return StageTier.SEED
            elif amt <= limit_series_a:
                return StageTier.SERIES_A
            else:
                return StageTier.LATE
        except Exception:
            pass

    # 3. Fallback: check summary only if title had no stage indicator
    s_low = summary.lower() if summary else ""
    if s_low:
        is_historical = bool(
            re.search(r"\b(?:previously|earlier|past|founded in \d{4})\b.*?\braised\b", s_low)
        )
        if not is_historical:
            if any(re.search(pat, s_low) for pat in FIRST_FUNDING_PATTERNS):
                return StageTier.FIRST_FUNDING
            if any(re.search(pat, s_low) for pat in SEED_PATTERNS):
                return StageTier.SEED
            if any(re.search(pat, s_low) for pat in SERIES_A_PATTERNS):
                return StageTier.SERIES_A
            if any(re.search(pat, s_low) for pat in SERIES_B_PATTERNS or LATE_PATTERNS):
                return StageTier.LATE

    return StageTier.UNKNOWN


def is_funding_item(article: Article, cfg: FilterConfig) -> bool:
    """
    Check if an article matches funding criteria and passes sector, geo, and exclude filters.

    Rules:
    0. Must NOT match general weekly roundup patterns.
    1. Must match at least one exclude_keywords (or default false positive phrases) -> False.
    2. Must NOT be pure non-tech consumer/food/fashion brand (unless software platform override).
    3. Must match at least one funding_keywords in title (or summary if match_in_summary) -> True.
    4. If sector_keywords is non-empty, must match at least one -> otherwise False.
    5. If geo_keywords is non-empty, must match at least one -> otherwise False.
    """
    title = article.title or ""
    summary = article.summary or ""

    # Combined text for sector, geo, and exclusion
    full_text = f"{title} {summary}".strip()

    # 0. Exclude weekly roundups / digests
    if any(re.search(pat, title, re.IGNORECASE) for pat in ROUNDUP_PATTERNS):
        return False

    # 0b. Exclude financial earnings / revenue reports
    if any(re.search(pat, title, re.IGNORECASE) for pat in EARNINGS_PATTERNS):
        return False

    # 0c. Exclude figurative non-capital uses of "raises" (e.g. raises stakes/bar)
    if any(re.search(pat, title, re.IGNORECASE) for pat in FIGURATIVE_RAISES_PATTERNS):
        return False

    # 0d. Exclude late-stage enterprise / debt rounds when early_stage_only is active
    if cfg.early_stage_only:
        stage = classify_stage_tier(title, summary)
        if stage == StageTier.LATE:
            return False

    # 1. Check exclusions (user-configured + common false-positives)
    all_exclusions = list(cfg.exclude_keywords) + DEFAULT_FALSE_POSITIVE_PHRASES
    if _matches_any_keyword(full_text, all_exclusions):
        return False

    # 2. Non-tech retail / food / fashion filter (unless explicit software platform override)
    has_non_tech = any(re.search(pat, full_text, re.IGNORECASE) for pat in NON_TECH_PATTERNS)
    if has_non_tech:
        has_software_override = any(
            re.search(pat, full_text, re.IGNORECASE) for pat in SOFTWARE_PLATFORM_OVERRIDES
        )
        if not has_software_override:
            return False

    # Text for funding keyword matching
    if cfg.match_in_summary and summary:
        funding_search_text = f"{title} {summary}"
    else:
        funding_search_text = title

    # 3. Check funding keywords
    if not cfg.funding_keywords:
        return False
    if not _matches_any_keyword(funding_search_text, cfg.funding_keywords):
        return False

    # 4. Check sector keywords (if configured)
    if cfg.sector_keywords and not _matches_any_keyword(full_text, cfg.sector_keywords):
        return False

    # 5. Check geo keywords (if configured)
    if cfg.geo_keywords and not _matches_any_keyword(full_text, cfg.geo_keywords):
        return False

    return True
