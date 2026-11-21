"""Notifiers protocol, message formatting, and dispatcher."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from fundwatch.models import Article, Extraction, Settings

logger = logging.getLogger(__name__)


@runtime_checkable
class Notifier(Protocol):
    """Protocol that all notification channels must implement."""

    name: str

    def send(self, article: Article, extraction: Extraction | None = None) -> None:
        """Send formatted alert for a new funding round article."""
        ...

    def send_text(self, text: str) -> None:
        """Send a plain text system alert."""
        ...


def format_article_message(article: Article, extraction: Extraction | None = None) -> str:
    """
    Format message according to PLAN spec:
    💰 {company or title}
    {amount currency} · {stage} · {investors}
    {sector} · {location}
    Source: {feed_name} · {published date}
    {link}
    """
    lines: list[str] = []

    # Line 1: Header
    company_name = extraction.company if (extraction and extraction.company) else None
    headline = company_name or article.title
    lines.append(f"💰 {headline}")

    # Line 2: Funding details (amount, stage, investors)
    if extraction:
        details_parts: list[str] = []
        if extraction.amount is not None:
            curr = extraction.currency or ""
            # Format amount cleanly
            if extraction.amount.is_integer():
                amt_str = f"{int(extraction.amount):,}"
            else:
                amt_str = f"{extraction.amount:,.2f}"
            amount_display = f"{amt_str} {curr}".strip()
            details_parts.append(amount_display)

        if extraction.stage:
            details_parts.append(extraction.stage)

        if extraction.investors:
            inv_str = ", ".join(extraction.investors)
            details_parts.append(inv_str)

        if details_parts:
            lines.append(" · ".join(details_parts))

        # Line 3: Sector & Location
        meta_parts: list[str] = []
        if extraction.sector:
            meta_parts.append(extraction.sector)
        if extraction.location:
            meta_parts.append(extraction.location)
        if meta_parts:
            lines.append(" · ".join(meta_parts))

        # Line 4: Website / Domain
        if extraction.domain:
            lines.append(f"🌐 Website: {extraction.domain}")

        # Line 5: Founding team emails & contacts
        if extraction.emails:
            email_lines = ["✉️ Founding Team & Contacts:"]
            for em in extraction.emails[:3]:
                name_role = em.get("name") or "Contact"
                role_str = (
                    f" ({em['role']})"
                    if em.get("role") and em["role"] not in {"General Contact", "General"}
                    else ""
                )
                verified_tag = " [Verified]" if em.get("verified") else ""
                email_lines.append(f"   • {name_role}{role_str}: {em['email']}{verified_tag}")
            lines.append("\n".join(email_lines))
        elif extraction.founders:
            founder_names = [f["name"] for f in extraction.founders if f.get("name")]
            if founder_names:
                lines.append(f"👤 Founders: {', '.join(founder_names)}")

    # Line: Source & date
    source_parts = [f"Source: {article.feed_name}"]
    if article.published_at:
        # Show YYYY-MM-DD or readable prefix
        date_str = article.published_at.split("T")[0]
        source_parts.append(date_str)
    lines.append(" · ".join(source_parts))

    # Line 5: Link
    if article.link:
        lines.append(article.link)

    return "\n".join(lines)


def build_notifiers(settings: Settings) -> list[Notifier]:
    """Instantiate all enabled notifiers from settings."""
    notifiers: list[Notifier] = []

    for cfg in settings.notifiers:
        if not cfg.enabled:
            continue
        ntype = cfg.type.lower()
        if ntype == "telegram":
            from fundwatch.notifiers.telegram import TelegramNotifier

            if settings.telegram_bot_token and settings.telegram_chat_id:
                notifiers.append(
                    TelegramNotifier(
                        token=settings.telegram_bot_token,
                        chat_id=settings.telegram_chat_id,
                        timeout=settings.request_timeout_seconds,
                    )
                )
        elif ntype == "slack":
            from fundwatch.notifiers.slack import SlackNotifier

            if settings.slack_webhook_url:
                notifiers.append(
                    SlackNotifier(
                        webhook_url=settings.slack_webhook_url,
                        timeout=settings.request_timeout_seconds,
                    )
                )
        elif ntype == "ntfy":
            from fundwatch.notifiers.ntfy import NtfyNotifier

            topic = cfg.topic or "fundwatch"
            notifiers.append(
                NtfyNotifier(
                    server=settings.ntfy_server,
                    topic=topic,
                    timeout=settings.request_timeout_seconds,
                )
            )
        elif ntype == "email":
            from fundwatch.notifiers.email_smtp import EmailNotifier

            if (
                settings.smtp_host
                and settings.smtp_user
                and settings.smtp_password
                and settings.email_to
            ):
                notifiers.append(
                    EmailNotifier(
                        host=settings.smtp_host,
                        port=settings.smtp_port,
                        user=settings.smtp_user,
                        password=settings.smtp_password,
                        to_email=settings.email_to,
                        timeout=settings.request_timeout_seconds,
                    )
                )
    return notifiers


def send_notification_to_all(
    notifiers: list[Notifier],
    article: Article,
    extraction: Extraction | None = None,
) -> bool:
    """
    Send article alert to all enabled notifiers.
    Isolates failures across channels. Returns True if at least one notifier succeeded.
    """
    if not notifiers:
        return False

    success_count = 0
    for notifier in notifiers:
        try:
            notifier.send(article, extraction)
            success_count += 1
            logger.info("Notification sent via %s for %s", notifier.name, article.id)
        except Exception as exc:
            logger.error("Notifier %s failed to send %s: %s", notifier.name, article.id, exc)

    return success_count > 0


def send_system_alert_to_all(notifiers: list[Notifier], text: str) -> None:
    """Send system text alert to all enabled notifiers, isolating failures."""
    for notifier in notifiers:
        try:
            notifier.send_text(text)
        except Exception as exc:
            logger.error("Notifier %s failed to send system alert: %s", notifier.name, exc)
