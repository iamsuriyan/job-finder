"""Unit tests for deterministic resume parser, candidate profiles, and API endpoints."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from pypdf import PdfWriter
from starlette.testclient import TestClient

from fundwatch.db import Database
from fundwatch.models import (
    Article,
    CandidateProfile,
    DraftEmail,
    Extraction,
    Settings,
)
from fundwatch.outreach import generate_job_enquiry, send_outreach_email
from fundwatch.resume_parser import (
    clean_text_lines,
    extract_bullets,
    extract_email,
    extract_links,
    extract_name_and_title,
    extract_phone,
    parse_resume_to_profile,
)
from fundwatch.web.app import create_app


def create_dummy_pdf_bytes(text_lines: list[str]) -> bytes:
    """Helper to generate a minimal valid PDF in memory for parser tests."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    # Note: pypdf blank page doesn't have text stream unless added or loaded.
    # But PdfWriter can write a valid PDF file.
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_parse_resume_to_profile(tmp_path: Path) -> None:
    pdf_bytes = create_dummy_pdf_bytes(["Sample text"])
    pdf_file = tmp_path / "sample_resume.pdf"
    pdf_file.write_bytes(pdf_bytes)

    profile = parse_resume_to_profile(
        pdf_source=pdf_file,
        resume_path=str(pdf_file),
        resume_filename="sample_resume.pdf",
    )
    assert profile.resume_filename == "sample_resume.pdf"
    assert profile.resume_path == str(pdf_file)
    assert len(profile.bullets) >= 1


def test_clean_text_lines() -> None:
    raw = "   \n  Line 1   \n\n\n Line 2 \t \n"
    lines = clean_text_lines(raw)
    assert lines == ["Line 1", "Line 2"]


def test_extract_email_and_phone() -> None:
    text = "John Doe | john.doe@example.com | +1 555-123-4567 | San Francisco, CA"
    assert extract_email(text) == "john.doe@example.com"
    assert extract_phone(text) == "+1 555-123-4567"


def test_extract_links() -> None:
    text = (
        "Check out my portfolio https://johndoe.dev and github https://github.com/johndoe "
        "and linkedin https://linkedin.com/in/johndoe"
    )
    links = extract_links(text)
    assert links["github"] == "https://github.com/johndoe"
    assert links["linkedin"] == "https://linkedin.com/in/johndoe"
    assert links["portfolio"] == "https://johndoe.dev"


def test_extract_name_and_title() -> None:
    lines = [
        "Jane Smith",
        "Senior Product Engineer | Backend & Distributed Systems",
        "jane@example.com | +1 123 456 7890",
        "San Francisco, CA",
    ]
    name, title = extract_name_and_title(lines)
    assert name == "Jane Smith"
    assert title == "Product Engineer"


def test_extract_bullets() -> None:
    lines = [
        "EXPERIENCE",
        "• Scaled API infrastructure to handle 50,000 requests per minute with sub-50ms latency.",
        "• Designed and built multi-tenant search indexing pipeline using pgvector and Redis.",
        "• Led cross-functional team of 4 engineers delivering product features on time.",
        "Random note that should not be chosen.",
    ]
    bullets = extract_bullets(lines, max_bullets=3)
    assert len(bullets) == 3
    assert any("50,000" in b for b in bullets)
    assert any("multi-tenant" in b for b in bullets)


def test_generate_job_enquiry_with_candidate_profile() -> None:
    article = Article(
        id="art-test-1",
        feed_name="TechCrunch",
        title="Acme Corp raises $20M Series A",
        link="https://techcrunch.com/acme",
    )
    extraction = Extraction(
        article_id="art-test-1",
        company="Acme Corp",
        amount=20.0,
        currency="USD",
        stage="Series A",
        investors=["Sequoia"],
        founders=[{"name": "Jane Doe", "role": "Founder & CEO"}],
    )
    settings = Settings()
    candidate = CandidateProfile(
        name="Alex Rivera",
        title="Product Engineer",
        email="alex@rivera.dev",
        phone="+1 415 555 0199",
        location="San Francisco, CA",
        portfolio="https://alexrivera.dev",
        github="https://github.com/arivera",
        linkedin="https://linkedin.com/in/alexrivera",
        bullets=[
            "Architected low-latency microservices serving 10M daily requests.",
            "Built distributed background processing engine using Redis and Python.",
        ],
    )

    draft = generate_job_enquiry(article, extraction, settings, candidate=candidate)
    assert "Alex Rivera" in draft.body
    assert "alex@rivera.dev" in draft.body
    assert "Architected low-latency microservices" in draft.body
    assert "https://alexrivera.dev" in draft.body
    assert "Product Engineer" in draft.body


def test_send_outreach_email_mandatory_resume_enforcement(tmp_path: Path) -> None:
    settings = Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="password",
    )

    # Case 1: attach_resume is False -> raises ValueError
    draft_no_resume = DraftEmail(
        id="d1",
        company="Acme",
        recipient_name="Founder",
        recipient_email="founder@acme.com",
        subject="Congratulations",
        body="Pitch text",
        resume_path=str(tmp_path / "resume.pdf"),
        attach_resume=False,
        created_at="2026-11-22T05:00:00Z",
    )
    with pytest.raises(ValueError, match="Resume attachment is mandatory"):
        send_outreach_email(draft_no_resume, settings)

    # Case 2: resume_path does not exist on disk -> raises ValueError
    draft_missing_file = DraftEmail(
        id="d2",
        company="Acme",
        recipient_name="Founder",
        recipient_email="founder@acme.com",
        subject="Congratulations",
        body="Pitch text",
        resume_path=str(tmp_path / "non_existent_resume.pdf"),
        attach_resume=True,
        created_at="2026-11-22T05:00:00Z",
    )
    with pytest.raises(ValueError, match="Mandatory resume file not found"):
        send_outreach_email(draft_missing_file, settings)


def test_candidate_api_endpoints(tmp_path: Path) -> None:
    db = Database(tmp_path / "candidate_test.db")
    settings = Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="test@example.com",
    )
    app = create_app(settings=settings, db=db)
    client = TestClient(app)

    # 1. Get initial candidate profile
    resp = client.get("/api/candidate/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == settings.candidate_name

    # 2. Update candidate profile fields
    update_payload = {
        "name": "Sarah Connor",
        "title": "Lead Product Engineer",
        "location": "Los Angeles, CA",
        "bullets": [
            "Built autonomous resilient infrastructure.",
            "Scaled distributed sensor networks.",
        ],
    }
    put_resp = client.put("/api/candidate/profile", json=update_payload)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["name"] == "Sarah Connor"
    assert updated_data["title"] == "Lead Product Engineer"
    assert updated_data["location"] == "Los Angeles, CA"
    assert len(updated_data["bullets"]) == 2

    # Verify persistent retrieval
    get_again = client.get("/api/candidate/profile")
    assert get_again.json()["name"] == "Sarah Connor"

    # 3. Upload a resume file
    pdf_bytes = create_dummy_pdf_bytes(["Test resume text"])
    files = {"file": ("Sarah_Connor_Resume.pdf", pdf_bytes, "application/pdf")}
    upload_resp = client.post("/api/candidate/resume/upload", files=files)
    assert upload_resp.status_code == 200
    parsed = upload_resp.json()
    assert parsed["resume_filename"] == "Sarah_Connor_Resume.pdf"
    assert Path(parsed["resume_path"]).is_file()

    # 4. Resume status endpoint
    status_resp = client.get("/api/outbox/resume/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["exists"] is True

    # 5. Resume download/preview endpoint
    download_resp = client.get("/api/outbox/resume/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "inline" in download_resp.headers.get("content-disposition", "")
