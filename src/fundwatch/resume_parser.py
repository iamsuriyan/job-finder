"""Deterministic resume parser extracting candidate profile and high-impact email bullets."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pypdf import PdfReader

from fundwatch.models import CandidateProfile

logger = logging.getLogger(__name__)

# Common action verbs used in impactful resume bullets
ACTION_VERBS = {
    "built", "designed", "scaled", "developed", "integrated", "engineered",
    "architected", "automated", "deployed", "implemented", "created", "led",
    "optimized", "shipped", "managed", "spearheaded", "accelerated", "reduced",
    "improved", "migrated", "launched", "standardized", "delivered",
}


def extract_text_from_pdf(pdf_source: bytes | str | Path) -> str:
    """Extract raw text from PDF file path or bytes using pypdf."""
    try:
        if isinstance(pdf_source, (str, Path)):
            reader = PdfReader(str(pdf_source))
        else:
            import io
            reader = PdfReader(io.BytesIO(pdf_source))

        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text)
    except Exception as exc:
        logger.warning("Failed to extract text from PDF: %s", exc)
        return ""


def clean_text_lines(text: str) -> list[str]:
    """Split and clean non-empty text lines."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line:
            lines.append(line)
    return lines


def extract_email(text: str) -> str | None:
    """Extract primary email address."""
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    """Extract phone number including international prefixes."""
    # Matches +91 81100 44608, +1 (555) 123-4567, 81100-44608, etc.
    match = re.search(r"(?:\+\d{1,3}[-\s]?)?\(?\d{2,5}\)?[-\s]?\d{3,5}[-\s]?\d{4,5}", text)
    if match:
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 15:
            return raw
    return None


def extract_links(text: str) -> dict[str, str]:
    """Extract portfolio, GitHub, and LinkedIn URLs."""
    links: dict[str, str] = {}

    li_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+", text, re.IGNORECASE)
    if li_match:
        url = li_match.group(0)
        links["linkedin"] = url if url.startswith("http") else f"https://{url}"

    gh_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+", text, re.IGNORECASE)
    if gh_match:
        url = gh_match.group(0)
        # Avoid matching generic github.com/features or similar
        username = url.split("github.com/")[-1].strip("/")
        if username.lower() not in ("features", "pricing", "enterprise", "about"):
            links["github"] = url if url.startswith("http") else f"https://{url}"

    pf_match = re.search(r"(?:https?://)?[\w-]+\.github\.io(?:/[\w-]+)?", text, re.IGNORECASE)
    if pf_match:
        url = pf_match.group(0)
        links["portfolio"] = url if url.startswith("http") else f"https://{url}"
    else:
        # Match personal domains or portfolios (e.g. .dev, .me, .io) excluding social links
        for m in re.finditer(r"https?://[^\s/$.?#].[^\s]*", text):
            candidate_url = m.group(0).rstrip(".,;")
            cand_lower = candidate_url.lower()
            excluded = ["github.com", "linkedin.com", "twitter.com", "x.com", "gmail.com"]
            if not any(ex in cand_lower for ex in excluded):
                links["portfolio"] = candidate_url
                break

    return links


def extract_name_and_title(lines: list[str]) -> tuple[str, str]:
    """Extract candidate name and detected title from the top lines of resume."""
    name = "Product Engineer"
    title = "Product Engineer"

    if not lines:
        return name, title

    # Look through first 4 lines for candidate name
    for line in lines[:4]:
        # Filter out lines that look like contact info, URLs, or labels
        skip_terms = ["@", "http", "linkedin", "github", "phone", "curriculum", "resume", "page"]
        if any(term in line.lower() for term in skip_terms):
            continue
        cleaned = re.sub(r"[|/•-].*$", "", line).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
            name = cleaned
            break

    # Look for candidate title in lines 1-6
    title_keywords = [
        "product engineer", "generative ai", "full stack", "backend", "software engineer",
        "frontend", "ai engineer", "systems engineer", "platform engineer", "data engineer",
    ]
    for line in lines[:6]:
        line_lower = line.lower()
        if any(kw in line_lower for kw in title_keywords):
            # Prefer concise clean title
            if "product engineer" in line_lower:
                title = "Product Engineer"
            elif "full stack" in line_lower:
                title = "Full-Stack Engineer"
            elif "backend" in line_lower:
                title = "Backend Engineer"
            elif "software engineer" in line_lower:
                title = "Software Engineer"
            elif "ai engineer" in line_lower or "generative ai" in line_lower:
                title = "AI & Product Engineer"
            else:
                title = line.split("|")[0].strip()
            break

    return name, title


def extract_bullets(lines: list[str], max_bullets: int = 3) -> list[str]:
    """
    Extract the top experience accomplishments formatted as punchy cold email pitch bullets.
    Scores bullets based on action verbs, scale metrics, and technical keywords.
    """
    candidates: list[tuple[int, str]] = []

    for line in lines:
        cleaned = line.lstrip("•-* \t")
        if not cleaned or len(cleaned) < 30 or len(cleaned) > 280:
            continue

        # Skip headers / labels
        is_header = (
            cleaned.isupper()
            or cleaned.endswith(":")
            or "experience" in cleaned.lower()
            or "education" in cleaned.lower()
        )
        if is_header:
            continue

        words = cleaned.split()
        first_word = words[0].lower() if words else ""

        score = 0
        if first_word in ACTION_VERBS:
            score += 10
        elif line.startswith("•") or line.startswith("-"):
            score += 5

        # Check for numbers / scale metrics (%, $, numbers, latency, calls, users)
        if re.search(r"\b(?:\d+[%kKmMbB]?|\$\d+)\b", cleaned):
            score += 8
        scale_terms = ["scale", "latency", "pipeline", "end to end", "production", "infrastructure"]
        if any(term in cleaned.lower() for term in scale_terms):
            score += 5
        tech_terms = ["api", "database", "service", "model", "platform", "agent"]
        if any(term in cleaned.lower() for term in tech_terms):
            score += 3

        if score >= 5:
            candidates.append((score, cleaned))

    # Sort candidates by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    selected: list[str] = []
    seen: set[str] = set()

    for _, bullet in candidates:
        # Avoid near duplicate bullets
        key = " ".join(bullet.split()[:4]).lower()
        if key not in seen:
            seen.add(key)
            # Ensure ends with period
            b = bullet.rstrip(".") + "."
            selected.append(b)
            if len(selected) >= max_bullets:
                break

    # Fallback default bullets if extraction found fewer than 3
    if len(selected) < 3:
        fallbacks = [
            "Built core product features and end-to-end services with production architecture.",
            "Designed and deployed scalable backend APIs, database models, and automated queues.",
            "Full-stack development experience taking products from prototype to production.",
        ]
        for fb in fallbacks:
            if len(selected) < 3:
                selected.append(fb)

    return selected[:max_bullets]


def parse_resume_to_profile(
    pdf_source: bytes | str | Path,
    resume_path: str,
    resume_filename: str = "Resume.pdf",
) -> CandidateProfile:
    """Parse PDF resume into a structured CandidateProfile."""
    text = extract_text_from_pdf(pdf_source)
    lines = clean_text_lines(text)

    name, title = extract_name_and_title(lines)
    email = extract_email(text)
    phone = extract_phone(text)
    links = extract_links(text)
    bullets = extract_bullets(lines)

    # Location heuristic (e.g. city, country line)
    location = "Remote / Available Globally"
    geo_markers = [
        ", India", ", USA", ", UK", ", Canada", ", Germany",
        "Coimbatore", "Bangalore", "San Francisco",
    ]
    for line in lines[:5]:
        if any(c in line for c in geo_markers):
            location = line.split("|")[0].strip()
            break

    from fundwatch.db import utc_now_iso

    return CandidateProfile(
        id="active",
        name=name,
        title=title,
        email=email or "contact@candidate.com",
        phone=phone or "",
        location=location,
        portfolio=links.get("portfolio", ""),
        github=links.get("github", ""),
        linkedin=links.get("linkedin", ""),
        resume_path=str(resume_path),
        resume_filename=resume_filename,
        bullets=bullets,
        skills=[],
        raw_text=text[:4000] if text else None,
        updated_at=utc_now_iso(),
    )
