"""Unit tests for optional LLM extraction with mocked Anthropic client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fundwatch.db import Database
from fundwatch.extractor import extract_funding_details
from fundwatch.models import Article, LLMExtractionConfig, Settings


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        poll_interval_minutes=20,
        llm_extraction=LLMExtractionConfig(enabled=True, model="test-model"),
        anthropic_api_key="test-api-key",
    )


def test_llm_extraction_disabled() -> None:
    settings = Settings(poll_interval_minutes=20, llm_extraction=LLMExtractionConfig(enabled=False))
    art = Article(id="1", feed_name="F", title="Startup raises $10M", link="L")
    res = extract_funding_details(art, settings)
    assert res is None


def test_llm_extraction_valid_json(db: Database, settings: Settings) -> None:
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = """
    {
      "company": "Cognition",
      "amount": 175.0,
      "currency": "USD",
      "stage": "Series A",
      "investors": ["Founders Fund"],
      "sector": "AI",
      "location": "San Francisco"
    }
    """
    mock_resp = MagicMock()
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    art = Article(
        id="art-cognition", feed_name="TechCrunch", title="Cognition raises $175M", link="L"
    )
    ext = extract_funding_details(art, settings, db=db, client=mock_client)

    assert ext is not None
    assert ext.company == "Cognition"
    assert ext.amount == 175.0
    assert ext.currency == "USD"
    assert ext.investors == ["Founders Fund"]
    assert mock_client.messages.create.call_count == 1

    # Second call should hit DB cache and NOT call LLM client again
    ext_cached = extract_funding_details(art, settings, db=db, client=mock_client)
    assert ext_cached is not None
    assert ext_cached.company == "Cognition"
    assert mock_client.messages.create.call_count == 1  # Still 1, cache hit!


def test_llm_extraction_code_fenced_json(db: Database, settings: Settings) -> None:
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = """```json
    {
      "company": "PayQuick",
      "amount": 5.0,
      "currency": "USD",
      "stage": "Seed",
      "investors": ["Y Combinator"],
      "sector": "Fintech",
      "location": "Bengaluru"
    }
    ```"""
    mock_resp = MagicMock()
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    art = Article(id="art-payquick", feed_name="Inc42", title="PayQuick bags $5M", link="L")
    ext = extract_funding_details(art, settings, db=db, client=mock_client)

    assert ext is not None
    assert ext.company == "PayQuick"
    assert ext.amount == 5.0
    assert ext.stage == "Seed"


def test_llm_extraction_garbage_fallback(db: Database, settings: Settings) -> None:
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "I cannot provide JSON for this article."
    mock_resp = MagicMock()
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    art = Article(id="art-bad", feed_name="F", title="Weird headline", link="L")
    ext = extract_funding_details(art, settings, db=db, client=mock_client)

    assert ext is not None
    assert ext.company is None
    assert ext.amount is None
    assert ext.raw_json == "I cannot provide JSON for this article."
