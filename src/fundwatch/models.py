"""Pydantic data models for fundwatch."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Feed(BaseModel):
    """Configuration for an RSS/Atom feed source."""

    model_config = ConfigDict(frozen=True)

    name: str
    url: str


class Article(BaseModel):
    """Normalized article representation from a feed."""

    id: str
    feed_name: str
    title: str
    link: str
    summary: str | None = None
    published_at: str | None = None  # ISO8601 UTC string
    first_seen_at: str | None = None  # ISO8601 UTC string
    matched: int = 0
    notified: int = 0
    title_norm: str | None = None


class Extraction(BaseModel):
    """Structured extraction of funding round details."""

    article_id: str | None = None
    company: str | None = None
    amount: float | None = None
    currency: str | None = None
    stage: str | None = None
    investors: list[str] | None = None
    sector: str | None = None
    location: str | None = None
    raw_json: str | None = None
    domain: str | None = None
    founders: list[dict[str, str]] | None = None
    emails: list[dict[str, Any]] | None = None


class FilterConfig(BaseModel):
    """Keyword and topic filtering configuration."""

    funding_keywords: list[str] = Field(default_factory=list)
    match_in_summary: bool = True
    sector_keywords: list[str] = Field(default_factory=list)
    geo_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)


class NotifierConfig(BaseModel):
    """Configuration for a specific notification destination."""

    type: str  # telegram, slack, ntfy, email
    enabled: bool = False
    topic: str | None = None


class LLMExtractionConfig(BaseModel):
    """Configuration for optional LLM extraction."""

    enabled: bool = False
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 400


class Settings(BaseModel):
    """Global configuration settings for fundwatch."""

    poll_interval_minutes: int = 20
    jitter_seconds: int = 60
    request_timeout_seconds: float = 15.0
    max_items_per_feed: int = 50
    max_article_age_days: int = 3
    user_agent: str = "fundwatch/0.1 (personal funding alert bot)"

    feeds: list[Feed] = Field(default_factory=list)
    filters: FilterConfig = Field(default_factory=FilterConfig)
    notifiers: list[NotifierConfig] = Field(default_factory=list)
    llm_extraction: LLMExtractionConfig = Field(default_factory=LLMExtractionConfig)

    # Runtime / Environment settings
    db_path: str = "./data/fundwatch.db"
    log_level: str = "INFO"
    find_founder_emails: bool = True

    # Secrets overlayed from environment
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    slack_webhook_url: str | None = None
    ntfy_server: str = "https://ntfy.sh"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_to: str | None = None
    anthropic_api_key: str | None = None
    hunter_api_key: str | None = None

    @field_validator("poll_interval_minutes")
    @classmethod
    def validate_poll_interval(cls, v: int) -> int:
        if v < 15:
            raise ValueError(f"poll_interval_minutes must be at least 15, got {v}")
        return v
