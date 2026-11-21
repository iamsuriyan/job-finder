"""Slack notification channel via Incoming Webhook."""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fundwatch.models import Article, Extraction
from fundwatch.notifiers import format_article_message


class SlackNotifier:
    """Sends notifications to a Slack channel using an incoming webhook."""

    def __init__(self, webhook_url: str, timeout: float = 15.0) -> None:
        self.name = "slack"
        self.webhook_url = webhook_url
        self.timeout = timeout

    @retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
        reraise=True,
    )
    def _send_payload(self, text: str) -> None:
        payload = {"text": text}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.webhook_url, json=payload)
            resp.raise_for_status()

    def send(self, article: Article, extraction: Extraction | None = None) -> None:
        message = format_article_message(article, extraction)
        self._send_payload(message)

    def send_text(self, text: str) -> None:
        self._send_payload(text)
