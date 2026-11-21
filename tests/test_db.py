"""Tests for SQLite database storage layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from fundwatch.db import Database
from fundwatch.models import Article, Extraction


@pytest.fixture
def db(tmp_path: Path) -> Database:
    db_file = tmp_path / "test_fundwatch.db"
    return Database(db_file)


def test_init_and_is_empty(db: Database) -> None:
    assert db.is_empty() is True


def test_insert_and_has_article(db: Database) -> None:
    art = Article(
        id="art-1",
        feed_name="TechCrunch",
        title="Startup Raises $10M",
        link="https://techcrunch.com/art-1",
        summary="A great startup raised seed round.",
        published_at="2026-03-01T10:00:00Z",
        first_seen_at="2026-03-01T10:05:00Z",
        title_norm="startup raises 10m",
    )
    inserted = db.insert_article(art)
    assert inserted is True
    assert db.is_empty() is False
    assert db.has_article("art-1") is True
    assert db.has_article("art-2") is False

    # Second insert should return False (ignore duplicate)
    assert db.insert_article(art) is False

    # Retrieve article
    retrieved = db.get_article("art-1")
    assert retrieved is not None
    assert retrieved.title == "Startup Raises $10M"
    assert retrieved.matched == 0
    assert retrieved.notified == 0


def test_mark_matched_and_notified(db: Database) -> None:
    art = Article(
        id="art-2",
        feed_name="Entrackr",
        title="Fintech secures funding",
        link="https://entrackr.com/art-2",
    )
    db.insert_article(art)

    db.mark_matched("art-2")
    db.mark_notified("art-2")

    retrieved = db.get_article("art-2")
    assert retrieved is not None
    assert retrieved.matched == 1
    assert retrieved.notified == 1


def test_recent_titles(db: Database) -> None:
    art = Article(
        id="art-3",
        feed_name="Inc42",
        title="AI Startup Bags $5M",
        link="https://inc42.com/art-3",
        title_norm="ai startup bags 5m",
    )
    db.insert_article(art)

    titles = db.recent_titles(hours=48)
    assert "ai startup bags 5m" in titles


def test_feed_state_tracking(db: Database) -> None:
    url = "https://example.com/feed"
    assert db.get_feed_state(url) is None

    # Record success
    db.record_feed_success(url, etag="tag-123", last_modified="Mon, 01 Mar 2026")
    state = db.get_feed_state(url)
    assert state is not None
    assert state["etag"] == "tag-123"
    assert state["consecutive_failures"] == 0

    # Record failure increments count
    count1 = db.record_feed_failure(url)
    assert count1 == 1
    count2 = db.record_feed_failure(url)
    assert count2 == 2

    # Reset on success
    db.record_feed_success(url, etag="tag-124", last_modified=None)
    state = db.get_feed_state(url)
    assert state is not None
    assert state["etag"] == "tag-124"
    assert state["consecutive_failures"] == 0


def test_extractions_and_export(db: Database) -> None:
    art = Article(
        id="art-4",
        feed_name="YourStory",
        title="Robotics co raises $2M",
        link="https://yourstory.com/art-4",
        matched=1,
    )
    db.insert_article(art)

    ext = Extraction(
        article_id="art-4",
        company="RoboTech",
        amount=2.0,
        currency="USD",
        stage="Seed",
        investors=["Peak XV", "Blume"],
        sector="Robotics",
        location="Bengaluru",
        raw_json='{"company": "RoboTech"}',
    )
    db.save_extraction(ext)

    retrieved_ext = db.get_extraction("art-4")
    assert retrieved_ext is not None
    assert retrieved_ext.company == "RoboTech"
    assert retrieved_ext.investors == ["Peak XV", "Blume"]

    exported = db.get_matched_articles_with_extractions()
    assert len(exported) == 1
    assert exported[0]["id"] == "art-4"
    assert exported[0]["company"] == "RoboTech"


def test_stats_and_recent_articles(db: Database) -> None:
    db.insert_article(
        Article(
            id="a1",
            feed_name="F1",
            title="T1",
            link="L1",
            matched=1,
            notified=1,
        )
    )
    db.insert_article(
        Article(
            id="a2",
            feed_name="F1",
            title="T2",
            link="L2",
            matched=0,
            notified=0,
        )
    )

    stats = db.get_stats()
    assert stats["total"] == 2
    assert stats["matched"] == 1
    assert stats["notified"] == 1
    assert len(stats["by_feed"]) == 1
    assert stats["by_feed"][0]["feed_name"] == "F1"
    assert stats["by_feed"][0]["count"] == 2

    recent = db.get_recent_articles(limit=10, matched_only=True)
    assert len(recent) == 1
    assert recent[0].id == "a1"
