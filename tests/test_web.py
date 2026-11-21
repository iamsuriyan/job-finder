"""Unit tests for the FastAPI web application and endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from fundwatch.db import Database
from fundwatch.models import Article, Extraction, Feed, Settings
from fundwatch.web.app import create_app


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "web_test.db")
    # Insert sample articles
    database.insert_article(
        Article(
            id="web-1",
            feed_name="TechCrunch Startups",
            title="Everful raises $48.5M for retail logistics",
            link="https://techcrunch.com/everful",
            summary="A company raises fresh capital.",
            matched=1,
            notified=1,
        )
    )
    database.save_extraction(
        Extraction(
            article_id="web-1",
            company="Everful",
            amount=48.5,
            currency="USD",
            stage="Series A",
            investors=["Benchmark"],
            sector="Logistics",
            location="San Francisco",
        )
    )
    database.insert_article(
        Article(
            id="web-2",
            feed_name="Inc42",
            title="Regular non-funding tech news article",
            link="https://inc42.com/non-funding",
            matched=0,
            notified=0,
        )
    )
    return database


@pytest.fixture
def settings() -> Settings:
    return Settings(
        poll_interval_minutes=20,
        feeds=[Feed(name="SampleFeed", url="https://example.com/rss")],
        user_agent="test-agent/1.0",
        request_timeout_seconds=5.0,
    )


@pytest.fixture
def client(settings: Settings, db: Database) -> TestClient:
    app = create_app(settings=settings, db=db)
    return TestClient(app)


def test_index_html(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "fundwatch" in resp.text
    assert "dark" in resp.text


def test_api_stats(client: TestClient) -> None:
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["matched"] == 1
    assert data["notified"] == 1
    assert len(data["feeds"]) == 1


def test_api_articles_filter_and_search(client: TestClient) -> None:
    # Matched only
    resp = client.get("/api/articles?matched_only=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["company"] == "Everful"
    assert data["items"][0]["amount"] == 48.5

    # All articles
    resp_all = client.get("/api/articles?matched_only=false")
    assert resp_all.status_code == 200
    assert resp_all.json()["total"] == 2

    # Search filter
    resp_search = client.get("/api/articles?search=Everful&matched_only=false")
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] == 1

    # Search unmatched
    resp_none = client.get("/api/articles?search=NonExistentCompany")
    assert resp_none.status_code == 200
    assert resp_none.json()["total"] == 0


def test_api_feeds(client: TestClient) -> None:
    resp = client.get("/api/feeds")
    assert resp.status_code == 200
    feeds = resp.json()
    assert len(feeds) == 1
    assert feeds[0]["name"] == "SampleFeed"
    assert feeds[0]["healthy"] is True


def test_api_config(client: TestClient) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["poll_interval_minutes"] == 20
    assert "funding_keywords" in cfg


def test_api_export_csv(client: TestClient) -> None:
    resp = client.get("/api/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert "Everful" in content
    assert "48.5" in content


def test_api_test_notify_no_notifiers(client: TestClient) -> None:
    resp = client.post("/api/test-notify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
