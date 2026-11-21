"""Unit tests for notifiers and message formatting."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import respx

from fundwatch.models import Article, Extraction, NotifierConfig, Settings
from fundwatch.notifiers import (
    build_notifiers,
    format_article_message,
    send_notification_to_all,
)
from fundwatch.notifiers.email_smtp import EmailNotifier
from fundwatch.notifiers.ntfy import NtfyNotifier
from fundwatch.notifiers.slack import SlackNotifier
from fundwatch.notifiers.telegram import TelegramNotifier


def test_format_article_message_without_extraction() -> None:
    art = Article(
        id="art-1",
        feed_name="TechCrunch",
        title="Cognition Raises $175M",
        link="https://techcrunch.com/cognition",
        published_at="2026-11-20T12:00:00+00:00",
    )
    msg = format_article_message(art, None)
    expected = (
        "💰 Cognition Raises $175M\n"
        "Source: TechCrunch · 2026-11-20\n"
        "https://techcrunch.com/cognition"
    )
    assert msg == expected


def test_format_article_message_with_extraction() -> None:
    art = Article(
        id="art-2",
        feed_name="Inc42",
        title="Fintech App Secures Funds",
        link="https://inc42.com/payz",
        published_at="2026-11-21T09:00:00+00:00",
    )
    ext = Extraction(
        article_id="art-2",
        company="PayZ",
        amount=15.0,
        currency="USD",
        stage="Series A",
        investors=["Peak XV", "Matrix"],
        sector="Fintech",
        location="Bengaluru",
    )
    msg = format_article_message(art, ext)
    assert "💰 PayZ" in msg
    assert "15 USD · Series A · Peak XV, Matrix" in msg
    assert "Fintech · Bengaluru" in msg
    assert "Source: Inc42 · 2026-11-21" in msg
    assert "https://inc42.com/payz" in msg


@respx.mock
def test_telegram_notifier() -> None:
    notifier = TelegramNotifier(token="fake-token", chat_id="123456", timeout=5.0)
    route = respx.post("https://api.telegram.org/botfake-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    art = Article(
        id="art-3",
        feed_name="Entrackr",
        title="AI co bags $2M",
        link="https://entrackr.com/3",
    )
    notifier.send(art)
    assert route.call_count == 1
    sent_payload = route.calls[0].request.content.decode("utf-8")
    assert "123456" in sent_payload
    assert "AI co bags $2M" in sent_payload


@respx.mock
def test_slack_notifier() -> None:
    webhook = "https://hooks.slack.com/services/T00/B00/X00"
    notifier = SlackNotifier(webhook_url=webhook, timeout=5.0)
    route = respx.post(webhook).mock(return_value=httpx.Response(200, text="ok"))

    notifier.send_text("Hello Slack!")
    assert route.call_count == 1
    sent_payload = route.calls[0].request.content.decode("utf-8")
    assert "Hello Slack!" in sent_payload


@respx.mock
def test_ntfy_notifier() -> None:
    notifier = NtfyNotifier(server="https://ntfy.sh", topic="test-topic", timeout=5.0)
    route = respx.post("https://ntfy.sh/test-topic").mock(
        return_value=httpx.Response(200, json={"id": "msg-1"})
    )

    art = Article(
        id="art-4",
        feed_name="Crunchbase",
        title="CleanTech raises $10M",
        link="https://cb.com/4",
    )
    notifier.send(art)
    assert route.call_count == 1
    assert route.calls[0].request.headers["Click"] == "https://cb.com/4"


@patch("smtplib.SMTP")
def test_email_notifier(mock_smtp_class: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_instance

    notifier = EmailNotifier(
        host="smtp.example.com",
        port=587,
        user="bot@example.com",
        password="secretpassword",
        to_email="alerts@example.com",
        timeout=5.0,
    )
    art = Article(
        id="art-5",
        feed_name="YourStory",
        title="BioTech Secures $8M",
        link="https://ys.com/5",
    )
    notifier.send(art)
    assert mock_smtp_class.called
    assert mock_instance.login.called
    assert mock_instance.send_message.called


def test_build_notifiers() -> None:
    settings = Settings(
        poll_interval_minutes=20,
        notifiers=[
            NotifierConfig(type="telegram", enabled=True),
            NotifierConfig(type="slack", enabled=False),
        ],
        telegram_bot_token="token-abc",
        telegram_chat_id="chat-123",
    )
    notifiers = build_notifiers(settings)
    assert len(notifiers) == 1
    assert notifiers[0].name == "telegram"


def test_send_notification_to_all_partial_failure() -> None:
    success_notifier = MagicMock()
    success_notifier.name = "success_mock"

    fail_notifier = MagicMock()
    fail_notifier.name = "fail_mock"
    fail_notifier.send.side_effect = RuntimeError("network down")

    art = Article(id="1", feed_name="F", title="T", link="L")
    result = send_notification_to_all([fail_notifier, success_notifier], art)
    assert result is True  # Succeeded because at least one channel sent

    all_fail = send_notification_to_all([fail_notifier], art)
    assert all_fail is False
