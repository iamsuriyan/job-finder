"""RSS/Atom feed fetching with conditional GET, exponential retries, and normalization."""

from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from fundwatch.db import Database
from fundwatch.models import Article, Feed, Settings

logger = logging.getLogger(__name__)

HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(raw_html: str | None) -> str | None:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return None
    cleaned = HTML_TAG_RE.sub(" ", raw_html)
    cleaned = html.unescape(cleaned)
    # Collapse multiple spaces
    cleaned = " ".join(cleaned.split())
    return cleaned.strip() or None


def parse_entry_date(entry: Any) -> str | None:
    """Extract and parse published or updated date to ISO 8601 UTC string."""
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if st:
        try:
            year = getattr(st, "tm_year", st[0])
            month = getattr(st, "tm_mon", st[1])
            day = getattr(st, "tm_mday", st[2])
            hour = getattr(st, "tm_hour", st[3])
            minute = getattr(st, "tm_min", st[4])
            second = getattr(st, "tm_sec", st[5])
            return datetime(year, month, day, hour, minute, second, tzinfo=UTC).isoformat()
        except Exception:
            pass
    return None


def normalize_entry(entry: Any, feed_name: str) -> Article:
    """Normalize a raw feedparser entry into an Article model."""
    link = str(entry.get("link", "")).strip()

    raw_id = entry.get("id") or entry.get("guid")
    if raw_id:
        article_id = str(raw_id).strip()
    else:
        article_id = hashlib.sha256(link.encode("utf-8")).hexdigest()

    title = clean_html(str(entry.get("title", ""))) or "Untitled"

    raw_summary = entry.get("summary") or entry.get("description")
    summary = clean_html(raw_summary)

    published_at = parse_entry_date(entry)

    return Article(
        id=article_id,
        feed_name=feed_name,
        title=title,
        link=link,
        summary=summary,
        published_at=published_at,
    )


def is_transient_error(exc: BaseException) -> bool:
    """Check if an exception is transient (network timeout, 5xx server error)."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {500, 502, 503, 504}
    return False


@retry(
    retry=retry_if_exception(is_transient_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
    reraise=True,
)
def fetch_http_response(
    url: str,
    headers: dict[str, str],
    timeout: float,
    client: httpx.Client | None = None,
) -> httpx.Response:
    """Fetch HTTP response with conditional headers and automatic retries for transient errors."""
    if client is not None:
        resp = client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        if resp.status_code != 304:
            resp.raise_for_status()
        return resp
    with httpx.Client(timeout=timeout, follow_redirects=True) as local_client:
        resp = local_client.get(url, headers=headers)
        if resp.status_code != 304:
            resp.raise_for_status()
        return resp


def fetch_feed(
    feed: Feed,
    settings: Settings,
    db: Database,
    client: httpx.Client | None = None,
    warn_callback: Any = None,
) -> list[Article]:
    """
    Fetch articles for a feed using conditional GET.
    Records success/failure in DB. Returns newly fetched articles up to max_items_per_feed.
    Never crashes on single feed failure.
    """
    headers = {"User-Agent": settings.user_agent}

    # Conditional GET headers from feed_state
    state = db.get_feed_state(feed.url)
    if state:
        if state.get("etag"):
            headers["If-None-Match"] = str(state["etag"])
        if state.get("last_modified"):
            headers["If-Modified-Since"] = str(state["last_modified"])

    try:
        response = fetch_http_response(
            url=feed.url,
            headers=headers,
            timeout=settings.request_timeout_seconds,
            client=client,
        )

        if response.status_code == 304:
            logger.info("Feed %s returned 304 Not Modified", feed.name)
            # Re-record success to refresh last_ok_at
            etag = state.get("etag") if state else None
            last_mod = state.get("last_modified") if state else None
            db.record_feed_success(feed.url, etag=etag, last_modified=last_mod)
            return []

        etag = response.headers.get("etag")
        last_modified = response.headers.get("last-modified")

        parsed = feedparser.parse(response.content)
        db.record_feed_success(feed.url, etag=etag, last_modified=last_modified)

        articles: list[Article] = []
        for entry in parsed.entries[: settings.max_items_per_feed]:
            articles.append(normalize_entry(entry, feed.name))

        logger.info(
            "Fetched %d articles from %s (%s)",
            len(articles),
            feed.name,
            feed.url,
        )
        return articles

    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", feed.name, feed.url, exc)
        fail_count = db.record_feed_failure(feed.url)
        if fail_count == 5:
            msg = f"⚠️ Feed '{feed.name}' ({feed.url}) has failed 5 consecutive times. Error: {exc}"
            logger.error(msg)
            if warn_callback is not None:
                try:
                    warn_callback(msg)
                except Exception as cb_err:
                    logger.warning("Failed to deliver feed failure warning: %s", cb_err)
        return []


def inspect_feed(feed: Feed, user_agent: str, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch feed directly for check-feeds command without updating DB."""
    headers = {"User-Agent": user_agent}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(feed.url, headers=headers)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            entries_count = len(parsed.entries)
            first_title = parsed.entries[0].get("title", "N/A") if entries_count > 0 else "None"
            return {
                "ok": True,
                "status_code": resp.status_code,
                "entries": entries_count,
                "latest_title": clean_html(str(first_title)),
                "error": None,
            }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": getattr(getattr(exc, "response", None), "status_code", None),
            "entries": 0,
            "latest_title": None,
            "error": str(exc),
        }
