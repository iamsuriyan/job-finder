"""Integration tests for pipeline poll cycle and bootstrap mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from fundwatch.db import Database
from fundwatch.models import Feed, FilterConfig, Settings
from fundwatch.pipeline import run_cycle

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test_pipeline.db")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        poll_interval_minutes=20,
        feeds=[Feed(name="SampleFeed", url="https://example.com/rss")],
        filters=FilterConfig(
            funding_keywords=["raises", "funding", "seed round", "series a"],
            match_in_summary=True,
        ),
        user_agent="test-bot/1.0",
        request_timeout_seconds=5.0,
        max_article_age_days=7,
    )


@respx.mock
def test_pipeline_bootstrap_then_new_article_then_rerun(db: Database, settings: Settings) -> None:
    """
    Test Phase 6 verification requirements:
    1. Run 1 (bootstrap mode on empty DB): notifies nothing.
    2. Run 2 (modified fixture with 1 new funding article): notifies exactly once.
    3. Run 3 (rerun with same data): notifies nothing.
    """
    # Fixture 1: 3 articles (2 are funding articles)
    xml_v1 = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")
    route = respx.get("https://example.com/rss")
    route.mock(return_value=httpx.Response(200, text=xml_v1))

    fake_notifier = MagicMock()
    fake_notifier.name = "fake"

    # --- Run 1: Empty DB triggers bootstrap mode ---
    assert db.is_empty() is True
    stats1 = run_cycle(
        settings=settings,
        db=db,
        notifiers=[fake_notifier],
        delay_between_feeds=0,
    )
    assert stats1.fetched == 3
    assert stats1.new == 3
    assert stats1.matched == 2
    assert stats1.notified == 0  # Bootstrap mode must notify 0!
    assert fake_notifier.send.call_count == 0
    assert db.is_empty() is False

    # --- Run 2: New funding article arrives ---
    xml_v2 = xml_v1.replace(
        "</channel>",
        """
        <item>
          <title>GenAI co Cognition raises $100M in Series B</title>
          <link>https://example.com/item-new-999</link>
          <guid>https://example.com/item-new-999</guid>
          <description>Cognition raises fresh capital.</description>
          <pubDate>Sat, 21 Nov 2026 10:00:00 GMT</pubDate>
        </item>
      </channel>
        """,
    )
    route.mock(return_value=httpx.Response(200, text=xml_v2))

    stats2 = run_cycle(
        settings=settings,
        db=db,
        notifiers=[fake_notifier],
        delay_between_feeds=0,
    )
    assert stats2.fetched == 4
    assert stats2.new == 1
    assert stats2.matched == 1
    assert stats2.notified == 1
    assert fake_notifier.send.call_count == 1
    sent_article = fake_notifier.send.call_args[0][0]
    assert sent_article.id == "https://example.com/item-new-999"
    assert "Cognition raises $100M" in sent_article.title

    # --- Run 3: Rerun with same data (no changes) ---
    stats3 = run_cycle(
        settings=settings,
        db=db,
        notifiers=[fake_notifier],
        delay_between_feeds=0,
    )
    assert stats3.fetched == 4
    assert stats3.new == 0
    assert stats3.matched == 0
    assert stats3.notified == 0
    assert fake_notifier.send.call_count == 1  # Still 1, nothing new sent!


@respx.mock
def test_pipeline_dry_run_mode(db: Database, settings: Settings) -> None:
    xml = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")
    respx.get("https://example.com/rss").mock(return_value=httpx.Response(200, text=xml))

    printed: list[str] = []

    def mock_print(msg: str) -> None:
        printed.append(msg)

    stats = run_cycle(
        settings=settings,
        db=db,
        is_bootstrap=False,
        dry_run=True,
        delay_between_feeds=0,
        print_callback=mock_print,
    )
    assert stats.matched == 2
    assert stats.notified == 2
    assert len(printed) == 2
    assert any("💰 Robotics Startup Raises $15M in Series A" in p for p in printed)
    assert any("💰 Fintech App Closes $5M Seed Round" in p for p in printed)
