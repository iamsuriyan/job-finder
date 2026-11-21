"""Job enquiry email template generation and human-in-the-loop SMTP dispatch."""

from __future__ import annotations

import logging
import re
import smtplib
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from fundwatch.db import utc_now_iso
from fundwatch.models import Article, DraftEmail, Extraction, Settings

logger = logging.getLogger(__name__)

DEFAULT_RESUME_PATH = "/home/viper/Downloads/Resumes/2+/Suriyan.pdf"


def check_resume(resume_path: str | Path | None = None) -> dict[str, Any]:
    """Inspect resume file existence, size, and metadata."""
    target_path = Path(resume_path or DEFAULT_RESUME_PATH)
    exists = target_path.is_file()
    size_bytes = target_path.stat().st_size if exists else 0
    size_kb = max(round(size_bytes / 1024, 1), 0.1) if size_bytes > 0 else 0.0

    return {
        "exists": exists,
        "path": str(target_path),
        "filename": target_path.name,
        "size_bytes": size_bytes,
        "size_kb": size_kb,
    }


def resolve_recipient(
    extraction: Extraction | None,
) -> tuple[str, str | None]:
    """Extract best candidate recipient name and email from extraction metadata."""
    if not extraction:
        return "Founding Team", None

    # 1. Search discovered emails for a founder/co-founder or CEO
    if extraction.emails:
        for em in extraction.emails:
            role = str(em.get("role", "")).lower()
            if any(k in role for k in ("founder", "ceo", "co-founder")):
                return str(em.get("name") or "Founder"), str(em.get("email"))

        # Fallback to the first email found
        first_em = extraction.emails[0]
        return str(first_em.get("name") or "Team"), str(first_em.get("email"))

    # 2. Search extracted founder names if no email yet discovered
    if extraction.founders and len(extraction.founders) > 0:
        first_founder = extraction.founders[0]
        name = first_founder.get("name") if isinstance(first_founder, dict) else str(first_founder)
        if name:
            return name, None

    return "Founding Team", None


def generate_job_enquiry(
    article: Article,
    extraction: Extraction | None,
    settings: Settings,
) -> DraftEmail:
    """Generate a highly personalized job enquiry cold email draft for a funded startup.

    HUMAN REVIEW GUARANTEE:
    This function strictly saves the email as a 'draft' status. It is NEVER sent automatically.
    """
    company = (extraction.company if extraction and extraction.company else "").strip()
    if not company:
        match = re.search(
            r"^(?:exclusive:\s*)?([A-Za-z0-9\s\.\-_&]+?)\s+(?:raises|bags|secures|closes|gets|nabs|lands|collects)",
            article.title,
            re.IGNORECASE,
        )
        if match:
            company = match.group(1).strip()
        else:
            words = article.title.split()
            company = words[0] if words else "Startup"

    recipient_name, recipient_email = resolve_recipient(extraction)

    # Determine round and details description
    round_parts: list[str] = []
    if extraction and extraction.amount:
        curr = extraction.currency or "$"
        round_parts.append(
            f"{curr}{extraction.amount:g}M"
            if extraction.amount < 1000
            else f"{curr}{extraction.amount:g}"
        )
    if extraction and extraction.stage:
        round_parts.append(extraction.stage)
    round_desc = " ".join(round_parts) if round_parts else "recent funding round"

    sector_desc = extraction.sector if (extraction and extraction.sector) else "your space"

    # Crisp, high-converting subject line
    subject = f"Congrats on the {round_desc} — Product & GenAI Engineer ({settings.candidate_name})"

    # Highly personalized body showcasing Suriyan Dhanapal's actual achievements from his resume
    salutation = (
        f"Hi {recipient_name},"
        if recipient_name and recipient_name != "Founding Team"
        else f"Hi {company} Team,"
    )

    p1 = (
        f"Huge congratulations on {company}'s {round_desc}! Seeing your progress in {sector_desc} "
        "is exciting, and with the fresh momentum, you're likely scaling your core product and "
        "engineering infrastructure."
    )
    p2 = (
        f"I'm reaching out because I would love to contribute to {company} as a Product / "
        "Generative AI Engineer. Over the last 2+ years, I’ve specialized in taking LLM products "
        "from 0 to 1 and scaling them for production:"
    )
    b1 = (
        "• Production AI Systems & Agents: Built an end-to-end compliance agent grounded in "
        "official Indian regulatory data (DGFT, GST, CBIC) using hybrid retrieval, "
        "cheapest-path-first document extraction (vision OCR + deterministic parsers), and "
        "human-in-the-loop review controls at an IIT Bombay-incubated startup (Cooper Compass)."
    )
    b2 = (
        "• Scaled Infrastructure & Multi-Tenancy: Integrated 25+ LLM, voice, STT, and TTS "
        "providers behind a unified connector layer serving live calls (~100 calls/day), and "
        "designed metadata-isolated multi-tenant RAG pipelines on pgvector & Weaviate at Mindgryd."
    )
    b3 = (
        "• Full-Stack Ownership: Deep background in Python, FastAPI, async queues (Redis/RQ), "
        "LangGraph, and Docker, with production experience building web dashboards in React, "
        "Next.js, and TypeScript."
    )
    ask = (
        "Would you be open to a brief 10–15 minute conversation sometime next week to see if my "
        "background aligns with technical roles you’re opening up?"
    )

    body = (
        f"{salutation}\n\n"
        f"{p1}\n\n"
        f"{p2}\n\n"
        f"{b1}\n"
        f"{b2}\n"
        f"{b3}\n\n"
        "I’ve attached my resume for your review. You can also explore my portfolio and "
        "open-source work:\n"
        f"• Portfolio: {settings.candidate_portfolio}\n"
        f"• GitHub: {settings.candidate_github}\n"
        f"• LinkedIn: {settings.candidate_linkedin}\n\n"
        f"{ask}\n\n"
        "Thanks for your time, and congrats once again on the round!\n\n"
        "Best regards,\n"
        f"{settings.candidate_name}\n"
        f"{settings.candidate_phone} | {settings.candidate_email}\n"
    )

    draft_id = f"draft_{uuid.uuid4().hex[:12]}"

    return DraftEmail(
        id=draft_id,
        article_id=article.id,
        company=company,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        resume_path=settings.resume_path or DEFAULT_RESUME_PATH,
        attach_resume=True,
        status="draft",
        created_at=utc_now_iso(),
        sent_at=None,
        error_message=None,
    )


def send_outreach_email(
    draft: DraftEmail,
    settings: Settings,
    timeout: float = 15.0,
) -> None:
    """Send an outreach email via SMTP with resume attachment.

    Raises:
        ValueError: If recipient email or SMTP settings are missing/invalid.
        smtplib.SMTPException / OSError: If network or authentication fails.
    """
    if not draft.recipient_email or "@" not in draft.recipient_email:
        raise ValueError(
            "Recipient email is missing or invalid. Please specify a valid email address."
        )

    if not settings.smtp_host:
        raise ValueError(
            "SMTP_HOST is not configured. Please set SMTP_HOST in settings or environment."
        )

    sender_email = settings.smtp_from or settings.smtp_user or settings.candidate_email
    if not sender_email:
        raise ValueError("Sender email is not configured. Please set SMTP_USER or SMTP_FROM.")

    # Build MIME message
    msg = EmailMessage()
    msg["Subject"] = draft.subject
    msg["From"] = f"{settings.candidate_name} <{sender_email}>"
    to_name = (
        draft.recipient_name
        if draft.recipient_name and draft.recipient_name != "Founding Team"
        else ""
    )
    if to_name:
        msg["To"] = f"{to_name} <{draft.recipient_email}>"
    else:
        msg["To"] = draft.recipient_email

    msg["Reply-To"] = settings.candidate_email
    msg.set_content(draft.body)

    # Attach resume if selected
    if draft.attach_resume and draft.resume_path:
        resume_file = Path(draft.resume_path)
        if resume_file.is_file():
            content = resume_file.read_bytes()
            # Clean filename for recipient
            filename = f"{settings.candidate_name.replace(' ', '_')}_Resume.pdf"
            msg.add_attachment(
                content,
                maintype="application",
                subtype="pdf",
                filename=filename,
            )
            logger.info(
                "Attached resume %s (%d bytes) to draft %s", resume_file, len(content), draft.id
            )
        else:
            logger.warning(
                "Resume file not found at %s; sending email without attachment.", draft.resume_path
            )

    # Dispatch via SMTP
    port = settings.smtp_port or 587
    logger.info(
        "Connecting to SMTP %s:%d to send draft %s to %s",
        settings.smtp_host,
        port,
        draft.id,
        draft.recipient_email,
    )

    with smtplib.SMTP(settings.smtp_host, port, timeout=timeout) as server:
        try:
            server.starttls()
        except smtplib.SMTPNotSupportedError:
            pass

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.send_message(msg)

    logger.info("Draft %s successfully dispatched to %s via SMTP", draft.id, draft.recipient_email)
