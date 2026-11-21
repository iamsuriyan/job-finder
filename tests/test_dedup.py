"""Unit tests for deduplication: normalization and rapidfuzz similarity."""

from __future__ import annotations

from fundwatch.dedup import is_fuzzy_duplicate, normalize_title


def test_normalize_title() -> None:
    assert (
        normalize_title("AI Startup Cognition Raises $175M - TechCrunch")
        == "ai startup cognition raises 175m"
    )
    assert normalize_title("PayZ Bags $20M in Series A | Inc42") == "payz bags 20m in series a"
    assert normalize_title("RoboTech Secures $5M — Entrackr") == "robotech secures 5m"


def test_is_fuzzy_duplicate_same_story_different_outlet() -> None:
    recent = [
        "ai startup cognition raises 175m at 2b valuation",
        "fintech app payz closes 10m seed round",
    ]

    # Same story from another outlet with outlet suffix
    cand1 = "Cognition Raises $175M at $2B Valuation - Crunchbase News"
    assert is_fuzzy_duplicate(cand1, recent) is True

    # Same story slight variation
    cand2 = "Cognition raises $175M at $2B valuation - Entrackr"
    assert is_fuzzy_duplicate(cand2, recent) is True

    # Completely different story
    cand3 = "Robotics firm BotCo raises $175M - TechCrunch"
    assert is_fuzzy_duplicate(cand3, recent) is False


def test_is_fuzzy_duplicate_empty_or_no_match() -> None:
    recent = ["clean energy startup secures 30m"]
    assert is_fuzzy_duplicate("", recent) is False
    assert is_fuzzy_duplicate("unrelated title", []) is False
