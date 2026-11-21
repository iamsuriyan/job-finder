"""ntfy.sh push notification channel."""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fundwatch.models import Article, Extraction
from fundwatch.notifiers import format_article_message


class NtfyNotifier:
    """Sends push notifications via ntfy HTTP API."""

    def __init__(self, server: str, topic: str, timeout: float = 15.0) -> None:
        self.name = "ntfy"
        server_clean = server.rstrip("/")
        self.endpoint = f"{server_clean}/{topic}"
        self.timeout = timeout

    @retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
        reraise=True,
    )
    def _send_payload(
        self, body: str, title: str | None = None, click_url: str | None = None
    ) -> None:
        headers: dict[str, str] = {"Tags": "moneybag"}
        if title:
            # HTTP headers must be ASCII-safe
            clean_title = title.encode("ascii", "ignore").decode("ascii").strip()
            if clean_title:
                headers["Title"] = clean_title
        if click_url:
            headers["Click"] = click_url

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                self.endpoint,
                content=body.encode("utf-8"),
                headers=headers,
            )
            resp.raise_for_status()

    def send(self, article: Article, extraction: Extraction | None = None) -> None:
        message = format_article_message(article, extraction)
        headline = extraction.company if (extraction and extraction.company) else article.title
        self._send_payload(
            body=message,
            title=f"💰 {headline}",
            click_url=article.link,
        )

    def send_text(self, text: str) -> None:
        self._send_payload(body=text, title="fundwatch Alert")
