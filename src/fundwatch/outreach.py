"""Job enquiry email template generation and human-in-the-loop SMTP dispatch."""

from __future__ import annotations

import logging
import smtplib
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from fundwatch.db import utc_now_iso
from fundwatch.email_finder import extract_company_name
from fundwatch.filters import classify_stage_tier
from fundwatch.models import Article, CandidateProfile, DraftEmail, Extraction, Settings, StageTier

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
    """Extract best candidate recipient name and email from extraction metadata.

    Guarantees that unverified role-inboxes (founders@, etc.) are never blindly chosen.
    Priority:
    1. Verified founder personal email (hunter_api, smtp_probe)
    2. Real website-scraped company contact email (e.g. info@domain, contact@domain)
    3. Founder pattern email on a verified company domain
    4. Identified founder name with None (prompting review/manual entry to avoid bounce)
    5. 'Founding Team' with None
    """
    if not extraction:
        return "Founding Team", None

    # Priority 1: Verified personal founder/executive email
    if extraction.emails:
        for em in extraction.emails:
            role = str(em.get("role", "")).lower()
            source = str(em.get("source", "")).lower()
            is_founder = any(k in role for k in ("founder", "ceo", "co-founder")) and "inbox" not in role
            if is_founder and em.get("verified") is True and "role_inbox" not in source:
                return str(em.get("name") or "Founder"), str(em.get("email"))

    # Priority 2: Real website-scraped company contact email (deliverable mailbox on domain)
    if extraction.emails:
        for em in extraction.emails:
            source = str(em.get("source", "")).lower()
            if source == "website_scrape" and em.get("verified") is True:
                return str(em.get("name") or "Team"), str(em.get("email"))

    # Priority 3: Founder pattern email on verified company domain
    if extraction.emails:
        for em in extraction.emails:
            role = str(em.get("role", "")).lower()
            source = str(em.get("source", "")).lower()
            is_founder = any(k in role for k in ("founder", "ceo", "co-founder")) and "inbox" not in role
            if is_founder and source in ("pattern_mx", "pattern_permutation"):
                return str(em.get("name") or "Founder"), str(em.get("email"))

    # Priority 4: Any verified email in extraction.emails
    if extraction.emails:
        for em in extraction.emails:
            if em.get("verified") is True and em.get("email"):
                return str(em.get("name") or "Team"), str(em.get("email"))

    # Priority 5: Search extracted founder names if no verified email yet discovered
    if extraction.founders and len(extraction.founders) > 0:
        first_founder = extraction.founders[0]
        name = first_founder.get("name") if isinstance(first_founder, dict) else str(first_founder)
        if name:
            return name, None

    # Priority 6: Fallback to first email only if verified or not an unverified role_inbox guess
    if extraction.emails and len(extraction.emails) > 0:
        for em in extraction.emails:
            if em.get("email") and (em.get("verified") is True or em.get("source") != "role_inbox"):
                return str(em.get("name") or "Team"), str(em.get("email"))

    return "Founding Team", None


def generate_job_enquiry(
    article: Article,
    extraction: Extraction | None,
    settings: Settings,
    candidate: CandidateProfile | None = None,
) -> DraftEmail:
    """Generate a highly personalized job enquiry cold email draft for a funded startup.

    HUMAN REVIEW GUARANTEE:
    This function strictly saves the email as a 'draft' status. It is NEVER sent automatically.
    """
    company = (extraction.company if extraction and extraction.company else "").strip()
    if not company:
        company = extract_company_name(article.title, article.summary or "")

    recipient_name, recipient_email = resolve_recipient(extraction)

    cand_name = candidate.name if candidate and candidate.name else settings.candidate_name
    cand_title = candidate.title if candidate and candidate.title else settings.candidate_title
    cand_email = candidate.email if candidate and candidate.email else settings.candidate_email
    cand_phone = candidate.phone if candidate and candidate.phone else settings.candidate_phone
    cand_portfolio = (
        candidate.portfolio if candidate and candidate.portfolio else settings.candidate_portfolio
    )
    cand_github = candidate.github if candidate and candidate.github else settings.candidate_github
    cand_linkedin = (
        candidate.linkedin if candidate and candidate.linkedin else settings.candidate_linkedin
    )
    cand_resume_path = (
        candidate.resume_path
        if candidate and candidate.resume_path
        else (settings.resume_path or DEFAULT_RESUME_PATH)
    )

    # Determine stage tier for early-stage tailored messaging
    stage_tier = getattr(article, "stage_tier", None)
    if not stage_tier:
        stage_tier = str(classify_stage_tier(article.title, article.summary or ""))

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
    elif stage_tier == StageTier.FIRST_FUNDING:
        round_parts.append("first funding round")
    elif stage_tier == StageTier.SEED:
        round_parts.append("seed round")
    elif stage_tier == StageTier.SERIES_A:
        round_parts.append("Series A")
    round_desc = " ".join(round_parts) if round_parts else "recent funding round"

    sector_desc = extraction.sector if (extraction and extraction.sector) else "your space"

    # Salutation: use first name if recipient is a human person
    is_generic = (
        recipient_name in ("Founding Team", "Team", "Company Contact")
        or recipient_name.endswith(" Team")
        or recipient_name.endswith(" CEO")
    )
    if not is_generic and recipient_name:
        first_name = recipient_name.split()[0]
        salutation = f"Hi {first_name},"
    else:
        salutation = f"Hi {company} Team,"

    # Tailored 0-to-1 Founding Pitch for Early-Stage Startups
    founding_title = (
        cand_title if cand_title.lower().startswith("founding") else f"Founding {cand_title}"
    )

    if stage_tier == StageTier.FIRST_FUNDING:
        subject = f"Congrats on the first round! — {founding_title} ({cand_name})"
        p1 = (
            f"Huge congratulations on {company}'s first funding round! Taking a startup "
            "from 0 to 1 is the most exciting phase, and with the fresh runway, you're "
            "likely architecting your foundational product and core AI infrastructure."
        )
        p2 = (
            f"I'm reaching out because I would love to contribute to {company} as a "
            f"{founding_title}. Over the last 2+ years, I’ve specialized in 0-to-1 building: "
            "taking systems from idea to production without needing a 10-person team:"
        )
        ask = (
            "Would you be open to a brief 10–15 minute conversation sometime next week to "
            "see if my background aligns with your foundational engineering needs?"
        )
    elif stage_tier == StageTier.SEED:
        subject = f"Congrats on the Seed Round! — {founding_title} ({cand_name})"
        p1 = (
            f"Huge congratulations on {company}'s Seed round! Securing seed funding gives "
            "you the runway to accelerate from prototype to production, and you're likely "
            "locking down your core engineering architecture."
        )
        p2 = (
            f"I'm reaching out because I would love to contribute to {company} as a "
            f"{founding_title}. Over the last 2+ years, I’ve specialized in 0-to-1 product "
            "engineering and scaling:"
        )
        ask = (
            "Would you be open to a brief 10–15 minute conversation sometime next week to "
            "see if my background aligns with your core engineering roles?"
        )
    else:
        subject = f"Congrats on the {round_desc} — {cand_title} ({cand_name})"
        p1 = (
            f"Huge congratulations on {company}'s {round_desc}! Seeing your progress in "
            f"{sector_desc} is exciting, and with the fresh momentum, you're likely "
            "scaling your core product and engineering infrastructure."
        )
        p2 = (
            f"I'm reaching out because I would love to contribute to {company} as a "
            f"{cand_title}. Over the last 2+ years, I’ve specialized in taking products from "
            "0 to 1 and scaling them for production:"
        )
        ask = (
            "Would you be open to a brief 10–15 minute conversation sometime next week to "
            "see if my background aligns with technical roles you’re opening up?"
        )

    if candidate and candidate.bullets:
        cand_bullets = [f"• {b.lstrip('•- ')}" for b in candidate.bullets]
    else:
        cand_bullets = [
            "• Production AI Systems & Agents: Built an end-to-end compliance agent grounded in "
            "official Indian regulatory data (DGFT, GST, CBIC) using hybrid retrieval, "
            "cheapest-path-first document extraction (vision OCR + deterministic parsers), and "
            "human-in-the-loop review controls at an IIT Bombay startup (Cooper Compass).",
            "• Scaled Infrastructure & Multi-Tenancy: Integrated 25+ LLM, voice, STT, and TTS "
            "providers behind a unified connector layer serving live calls (~100 calls/day), "
            "and designed metadata-isolated multi-tenant RAG pipelines on pgvector & "
            "Weaviate at Mindgryd.",
            "• Full-Stack Ownership: Deep background in Python, FastAPI, async queues (Redis/RQ), "
            "LangGraph, and Docker, with production experience building web dashboards in React, "
            "Next.js, and TypeScript.",
        ]
    bullets_text = "\n".join(cand_bullets)

    links_list: list[str] = []
    if cand_portfolio:
        links_list.append(f"• Portfolio: {cand_portfolio}")
    if cand_github:
        links_list.append(f"• GitHub: {cand_github}")
    if cand_linkedin:
        links_list.append(f"• LinkedIn: {cand_linkedin}")
    links_block = ("\n" + "\n".join(links_list)) if links_list else ""

    ask = (
        "Would you be open to a brief 10–15 minute conversation sometime next week to see if my "
        "background aligns with technical roles you’re opening up?"
    )

    contact_line = (
        f"{cand_phone} | {cand_email}"
        if cand_phone and cand_email
        else (cand_email or cand_phone or "")
    )

    body = (
        f"{salutation}\n\n"
        f"{p1}\n\n"
        f"{p2}\n\n"
        f"{bullets_text}\n\n"
        "I’ve attached my resume for your review. You can also explore my portfolio and "
        f"open-source work:{links_block}\n\n"
        f"{ask}\n\n"
        "Thanks for your time, and congrats once again on the round!\n\n"
        "Best regards,\n"
        f"{cand_name}\n"
        f"{contact_line}\n"
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
        resume_path=cand_resume_path,
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

    # Attach resume (strictly mandatory)
    if not draft.attach_resume or not draft.resume_path:
        raise ValueError(
            "Resume attachment is mandatory to send outreach emails. Please attach your resume PDF."
        )

    resume_file = Path(draft.resume_path)
    if not resume_file.is_file():
        raise ValueError(
            f"Mandatory resume file not found at {draft.resume_path}. "
            "Please upload a valid resume PDF before sending."
        )

    content = resume_file.read_bytes()
    filename = f"{settings.candidate_name.replace(' ', '_')}_Resume.pdf"
    msg.add_attachment(
        content,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )
    logger.info(
        "Attached mandatory resume %s (%d bytes) to draft %s", resume_file, len(content), draft.id
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
