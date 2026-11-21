"""Tests for feed fetching, conditional GET, retries, and normalization."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from fundwatch.db import Database
from fundwatch.fetcher import clean_html, fetch_feed, inspect_feed, normalize_entry
from fundwatch.models import Feed, Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        poll_interval_minutes=20,
        user_agent="test-agent/1.0",
        request_timeout_seconds=5.0,
        max_items_per_feed=10,
    )


def test_clean_html() -> None:
    raw = "<p>Hello <b>World</b> &amp; everyone!</p>"
    assert clean_html(raw) == "Hello World & everyone!"
    assert clean_html(None) is None


def test_normalize_entry() -> None:
    entry = {
        "id": "item-101",
        "link": "https://example.com/101",
        "title": "Startup &amp; Co Raises $5M",
        "summary": "<div>Summary details here</div>",
        "published_parsed": (2026, 11, 20, 10, 0, 0, 4, 324, 0),
    }
    art = normalize_entry(entry, feed_name="TechDaily")
    assert art.id == "item-101"
    assert art.feed_name == "TechDaily"
    assert art.title == "Startup & Co Raises $5M"
    assert art.summary == "Summary details here"
    assert art.published_at == "2026-11-20T10:00:00+00:00"


@respx.mock
def test_fetch_feed_200(db: Database, settings: Settings) -> None:
    feed = Feed(name="Sample", url="https://example.com/rss")
    xml_content = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")

    respx.get("https://example.com/rss").mock(
        return_value=httpx.Response(
            200,
            text=xml_content,
            headers={"ETag": "tag-v1", "Last-Modified": "Fri, 20 Nov 2026 12:00:00 GMT"},
        )
    )

    articles = fetch_feed(feed, settings, db)
    assert len(articles) == 3
    assert articles[0].title == "Robotics Startup Raises $15M in Series A"
    assert articles[0].id == "https://example.com/item-1"

    # Verify feed state in DB
    state = db.get_feed_state(feed.url)
    assert state is not None
    assert state["etag"] == "tag-v1"
    assert state["consecutive_failures"] == 0


@respx.mock
def test_fetch_feed_304_not_modified(db: Database, settings: Settings) -> None:
    feed = Feed(name="Sample", url="https://example.com/rss")
    db.record_feed_success(feed.url, etag="tag-v1", last_modified=None)

    respx.get("https://example.com/rss").mock(return_value=httpx.Response(304))

    articles = fetch_feed(feed, settings, db)
    assert articles == []
    state = db.get_feed_state(feed.url)
    assert state is not None
    assert state["etag"] == "tag-v1"


@respx.mock
def test_fetch_feed_retry_500_then_200(db: Database, settings: Settings) -> None:
    feed = Feed(name="Sample", url="https://example.com/rss")
    xml_content = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")

    route = respx.get("https://example.com/rss")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200, text=xml_content, headers={"ETag": "tag-v2"}),
    ]

    articles = fetch_feed(feed, settings, db)
    assert len(articles) == 3
    assert route.call_count == 2
    state = db.get_feed_state(feed.url)
    assert state is not None
    assert state["etag"] == "tag-v2"
    assert state["consecutive_failures"] == 0


@respx.mock
def test_fetch_feed_malformed_xml(db: Database, settings: Settings) -> None:
    feed = Feed(name="Malformed", url="https://example.com/bad.xml")
    malformed_content = (FIXTURES_DIR / "malformed_feed.xml").read_text(encoding="utf-8")

    respx.get("https://example.com/bad.xml").mock(
        return_value=httpx.Response(200, text=malformed_content)
    )

    articles = fetch_feed(feed, settings, db)
    # Feedparser handles malformed gracefully with 0 entries
    assert articles == []
    state = db.get_feed_state(feed.url)
    assert state is not None
    assert state["consecutive_failures"] == 0


@respx.mock
def test_fetch_feed_consecutive_failures_warn_callback(db: Database, settings: Settings) -> None:
    feed = Feed(name="FailFeed", url="https://example.com/fail")
    respx.get("https://example.com/fail").mock(return_value=httpx.Response(500))

    warn_messages: list[str] = []

    def warn_cb(msg: str) -> None:
        warn_messages.append(msg)

    # 4 failures: no warning
    for _ in range(4):
        fetch_feed(feed, settings, db, warn_callback=warn_cb)
    assert len(warn_messages) == 0

    # 5th failure: warning triggered
    fetch_feed(feed, settings, db, warn_callback=warn_cb)
    assert len(warn_messages) == 1
    assert "has failed 5 consecutive times" in warn_messages[0]


@respx.mock
def test_inspect_feed(settings: Settings) -> None:
    feed = Feed(name="Sample", url="https://example.com/rss")
    xml_content = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")
    respx.get("https://example.com/rss").mock(return_value=httpx.Response(200, text=xml_content))

    res = inspect_feed(feed, settings.user_agent)
    assert res["ok"] is True
    assert res["entries"] == 3
    assert res["latest_title"] == "Robotics Startup Raises $15M in Series A"
