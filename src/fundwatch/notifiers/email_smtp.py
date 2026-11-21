"""Email notification channel via SMTP with STARTTLS."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fundwatch.models import Article, Extraction
from fundwatch.notifiers import format_article_message


class EmailNotifier:
    """Sends notification emails via SMTP."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        to_email: str,
        timeout: float = 15.0,
    ) -> None:
        self.name = "email"
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.to_email = to_email
        self.timeout = timeout

    @retry(
        retry=retry_if_exception_type((smtplib.SMTPException, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
        reraise=True,
    )
    def _send_email(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = self.to_email
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            try:
                server.starttls()
            except smtplib.SMTPNotSupportedError:
                pass
            server.login(self.user, self.password)
            server.send_message(msg)

    def send(self, article: Article, extraction: Extraction | None = None) -> None:
        message = format_article_message(article, extraction)
        headline = extraction.company if (extraction and extraction.company) else article.title
        subject = f"💰 {headline}"
        self._send_email(subject, message)

    def send_text(self, text: str) -> None:
        self._send_email("fundwatch Alert", text)
