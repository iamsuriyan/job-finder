"""Unit tests for early-stage and first-funding stage classification and tailored pitches."""

from __future__ import annotations

import pytest

from fundwatch.filters import classify_stage_tier, is_funding_item
from fundwatch.models import Article, Extraction, FilterConfig, Settings, StageTier
from fundwatch.outreach import generate_job_enquiry

STAGE_TEST_CASES = [
    # First Funding / Pre-Seed / Angel / Stealth
    (
        "AI agent startup emerges from stealth with $3M pre-seed round",
        None,
        StageTier.FIRST_FUNDING,
    ),
    (
        "YC-backed workflow platform raises $500k angel round",
        None,
        StageTier.FIRST_FUNDING,
    ),
    (
        "Cybersecurity team secures debut round from techstars",
        None,
        StageTier.FIRST_FUNDING,
    ),
    # Seed Rounds
    (
        "Cognition secures $15M in seed funding to automate code generation",
        None,
        StageTier.SEED,
    ),
    (
        "Pedestal AI raises $4.7 million to agentify the supply chain",
        None,
        StageTier.SEED,
    ),
    (
        "Indian chip startup Bharat Semi lands $24M seed round",
        None,
        StageTier.SEED,
    ),
    # Series A
    (
        "DevOps tool closes $12M Series A led by Andreessen Horowitz",
        None,
        StageTier.SERIES_A,
    ),
    (
        "Disseqt AI raises $8 Mn led by Gresham House Ventures (pre-Series A)",
        None,
        StageTier.SERIES_A,
    ),
    # Late stage / Debt / PE / Series B+
    (
        "Logistics giant raises $200M Series D at $3B valuation",
        None,
        StageTier.LATE,
    ),
    (
        "Spacetech firm SatSure raises Rs 60 Cr Series B from Antariksh fund",
        None,
        StageTier.LATE,
    ),
    (
        "Fintech platform secures $50M debt financing facility",
        None,
        StageTier.LATE,
    ),
]


@pytest.mark.parametrize("title, summary, expected", STAGE_TEST_CASES)
def test_stage_classifier(title: str, summary: str | None, expected: StageTier) -> None:
    tier = classify_stage_tier(title, summary or "")
    assert tier == expected, f"Failed for '{title}', got {tier}, expected {expected}"


def test_early_stage_filter_rejects_late_stage() -> None:
    cfg = FilterConfig(
        funding_keywords=["raises", "secures"],
        early_stage_only=True,
    )
    late_article = Article(
        id="late-1",
        feed_name="TechCrunch",
        title="Enterprise CRM closes $150M Series D round",
        link="https://example.com/late",
    )
    early_article = Article(
        id="early-1",
        feed_name="TechCrunch",
        title="AI startup raises $3M seed round",
        link="https://example.com/early",
    )
    assert is_funding_item(late_article, cfg) is False
    assert is_funding_item(early_article, cfg) is True


def test_outreach_tailors_pitch_for_first_funding_and_seed() -> None:
    settings = Settings(
        candidate_name="Suriyan Dhanapal",
        candidate_title="Product Engineer / Gen AI",
        candidate_email="suriyan@example.com",
    )
    seed_article = Article(
        id="art-seed",
        feed_name="TechCrunch",
        title="AI devtool raises $3M seed round",
        link="https://example.com/seed",
        stage_tier=StageTier.SEED,
    )
    seed_ext = Extraction(company="DevTool AI", amount=3.0, currency="$", stage="Seed")
    draft = generate_job_enquiry(seed_article, seed_ext, settings)

    assert "Founding Product Engineer / Gen AI" in draft.subject
    assert "Congrats on the Seed Round!" in draft.subject
    assert "0-to-1 product engineering" in draft.body
