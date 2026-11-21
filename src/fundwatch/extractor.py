"""Optional LLM structured extraction using Anthropic API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fundwatch.db import Database
from fundwatch.models import Article, Extraction, Settings

logger = logging.getLogger(__name__)

CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Strip markdown json code fences if present."""
    match = CODE_FENCE_RE.search(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_funding_details(
    article: Article,
    settings: Settings,
    db: Database | None = None,
    client: Any = None,
) -> Extraction | None:
    """
    Extract structured funding round details using Anthropic model.
    Checks DB cache first. On failure, returns empty Extraction without blocking.
    """
    if not settings.llm_extraction.enabled:
        return None

    # Check cache in DB
    if db is not None:
        cached = db.get_extraction(article.id)
        if cached is not None:
            logger.info("Cache hit for article extraction: %s", article.id)
            return cached

    prompt = f"""You are a financial data extraction assistant.
Extract funding round details from the article headline and summary.
Article title: {article.title}
Article summary: {article.summary or "N/A"}

Return ONLY a JSON object with these exact keys:
- company: string name of company raising funds, or null
- amount: numeric amount raised (as a number e.g. 15.0 for $15M or null)
- currency: 3-letter currency code (e.g. USD, INR, EUR) or null
- stage: funding round stage (e.g. Seed, Pre-Seed, Series A, Series B, Series C), or null
- investors: list of strings of investor names, or null
- sector: industry/vertical (e.g. AI, Fintech, Healthtech, SaaS, Robotics), or null
- location: city or country where company is located, or null

Do not guess. If unknown, use null.
Return ONLY valid JSON.
"""

    raw_response_text = ""
    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model=settings.llm_extraction.model,
            max_tokens=settings.llm_extraction.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        content_blocks = response.content
        if content_blocks:
            first_block = content_blocks[0]
            raw_response_text = getattr(first_block, "text", str(first_block))

        cleaned_json = strip_code_fences(raw_response_text)
        parsed = json.loads(cleaned_json)

        extraction = Extraction(
            article_id=article.id,
            company=parsed.get("company"),
            amount=float(parsed["amount"]) if parsed.get("amount") is not None else None,
            currency=parsed.get("currency"),
            stage=parsed.get("stage"),
            investors=parsed.get("investors"),
            sector=parsed.get("sector"),
            location=parsed.get("location"),
            raw_json=raw_response_text,
        )

        if db is not None:
            db.save_extraction(extraction)

        return extraction

    except Exception as exc:
        logger.warning(
            "LLM extraction failed for article %s: %s (raw response: %s)",
            article.id,
            exc,
            raw_response_text,
        )
        empty_ext = Extraction(article_id=article.id, raw_json=raw_response_text or None)
        if db is not None:
            db.save_extraction(empty_ext)
        return empty_ext
