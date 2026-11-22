"""Table-driven unit tests for filters."""

from __future__ import annotations

import pytest

from fundwatch.filters import is_funding_item
from fundwatch.models import Article, FilterConfig

DEFAULT_FUNDING_KEYWORDS = [
    "raises",
    "raised",
    "funding",
    "seed round",
    "pre-seed",
    "pre-series a",
    "series a",
    "series b",
    "series c",
    "bags",
    "secures",
    "closes",
]

DEFAULT_EXCLUDE_KEYWORDS = ["webinar", "podcast", "opinion"]

# Table of test cases: (title, summary, expected_match, description)
FILTER_TEST_CASES = [
    # True positives (Funding rounds)
    ("AI startup Cognition raises $175M at $2B valuation", None, True, "Standard raises round"),
    ("Fintech platform PayZ secures $20M in Series A", None, True, "Secures series A"),
    ("Healthtech startup bags $5M seed round led by Peak XV", None, True, "Bags seed round"),
    ("SaaS tool closes $12M Series B funding", None, True, "Closes Series B funding"),
    ("DevOps company raised $3M in pre-seed", None, True, "Raised pre-seed"),
    ("Electric vehicle maker secures $50M Series C", None, True, "Secures Series C"),
    (
        "Agritech firm secures pre-series A funding from Omnivore",
        None,
        True,
        "Pre-series A funding",
    ),
    ("New crypto wallet raises $1.5M in fresh funding", None, True, "Raises fresh funding"),
    ("Logistics platform closes seed round from angel syndicate", None, True, "Closes seed round"),
    ("Edtech brand raised $8M to expand globally", None, True, "Raised $8M"),
    (
        "Stealth robotics company unveils new warehouse bot",
        "The company has raised $10M in seed funding.",
        True,
        "Funding keyword in summary when enabled",
    ),
    # False positives (Should be filtered out)
    (
        "Regulator raises concerns over fintech lending practices",
        None,
        False,
        "False positive: raises concerns",
    ),
    (
        "Economists raise questions about market stability",
        None,
        False,
        "False positive: raises questions",
    ),
    (
        "Government announces funding cuts for universities",
        None,
        False,
        "False positive: funding cuts",
    ),
    (
        "Startup ecosystem braces for winter funding crisis",
        None,
        False,
        "False positive: funding crisis",
    ),
    (
        "Report raises alarm over cybersecurity vulnerabilities",
        None,
        False,
        "False positive: raises alarm",
    ),
    (
        "Join our free webinar on scaling SaaS businesses",
        "Learn tips from founders",
        False,
        "Excluded: webinar",
    ),
    ("Episode 45 of TechTalk Podcast with Sarah Jenkins", None, False, "Excluded: podcast"),
    (
        "Opinion: Why artificial intelligence won't replace doctors",
        None,
        False,
        "Excluded: opinion",
    ),
    (
        "The President praises local business community",
        None,
        False,
        "Word boundary: praises != raises",
    ),
    (
        "A deep dive into modern cloud architecture",
        "Exploring distributed systems and Kubernetes.",
        False,
        "No funding keywords",
    ),
    (
        "Top 10 gadgets to look out for this holiday season",
        None,
        False,
        "Tech consumer news, no funding",
    ),
    (
        "Boba Bhai raises $18M from Left Lane to expand tea store network",
        "Fast food and bubble tea chain expands offline presence",
        False,
        "Non-tech: boba tea chain",
    ),
    (
        "Style Union raises $52M for fast-fashion offline apparel stores",
        "Fast fashion clothing retailer expands physical stores",
        False,
        "Non-tech: fast-fashion brand",
    ),
    (
        "Supply chain platform Blue Yonder raises fresh capital",
        "Automating enterprise warehouse logistics with cloud software",
        True,
        "Tech: supply chain software platform",
    ),
    (
        "Funding and acquisitions in Indian startups this week",
        "Weekly digest of startup investments",
        False,
        "Roundup digest",
    ),
    (
        "The Week’s 10 Biggest Funding Rounds: $400M For Neurotech Leads",
        None,
        False,
        "False positive: weekly roundup digest",
    ),
    (
        "Sarvam’s Token Factory Raises India’s AI Inference Stakes",
        "Sarvam AI announces Token Factory inference platform",
        False,
        "False positive: figurative raises stakes",
    ),
    (
        "Rooter’s revenue jumps over 2X to Rs 170 Cr in FY26; losses shrink 40%",
        "Operating revenue doubled in FY26 financial statements, raised $40M in past",
        False,
        "False positive: earnings report (revenue jumps, losses shrink)",
    ),
]


@pytest.mark.parametrize("title, summary, expected, desc", FILTER_TEST_CASES)
def test_filter_cases(title: str, summary: str | None, expected: bool, desc: str) -> None:
    cfg = FilterConfig(
        funding_keywords=DEFAULT_FUNDING_KEYWORDS,
        exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS,
        match_in_summary=True,
    )
    art = Article(
        id="test-1",
        feed_name="TestFeed",
        title=title,
        link="https://example.com/1",
        summary=summary,
    )
    assert is_funding_item(art, cfg) is expected, f"Failed for case: {desc} ('{title}')"


def test_sector_filtering() -> None:
    cfg = FilterConfig(
        funding_keywords=DEFAULT_FUNDING_KEYWORDS,
        sector_keywords=["fintech", "ai"],
    )
    art1 = Article(id="1", feed_name="F", title="AI startup raises $5M", link="L1")
    art2 = Article(id="2", feed_name="F", title="Fintech company closes $10M", link="L2")
    art3 = Article(id="3", feed_name="F", title="Biotech firm secures $15M", link="L3")

    assert is_funding_item(art1, cfg) is True
    assert is_funding_item(art2, cfg) is True
    assert is_funding_item(art3, cfg) is False


def test_geo_filtering() -> None:
    cfg = FilterConfig(
        funding_keywords=DEFAULT_FUNDING_KEYWORDS,
        geo_keywords=["india", "bengaluru"],
    )
    art1 = Article(
        id="1",
        feed_name="F",
        title="Startup raises $5M",
        summary="Based in Bengaluru, India",
        link="L1",
    )
    art2 = Article(
        id="2",
        feed_name="F",
        title="Berlin startup raises $10M",
        summary="Operating in Germany",
        link="L2",
    )

    assert is_funding_item(art1, cfg) is True
    assert is_funding_item(art2, cfg) is False
