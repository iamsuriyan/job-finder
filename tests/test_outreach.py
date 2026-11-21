"""Tests for cold job enquiry generation, outbox storage, and human-in-the-loop SMTP dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient
from typer.testing import CliRunner

from fundwatch.cli import app as cli_app
from fundwatch.db import Database
from fundwatch.models import Article, CandidateProfile, DraftEmail, Extraction, Settings
from fundwatch.outreach import (
    check_resume,
    generate_job_enquiry,
    resolve_recipient,
    send_outreach_email,
)
from fundwatch.web.app import create_app

runner = CliRunner()


@pytest.fixture
def sample_settings(tmp_path: Path) -> Settings:
    dummy_resume = tmp_path / "Suriyan_test.pdf"
    dummy_resume.write_bytes(b"%PDF-1.4 test dummy resume content")
    return Settings(
        poll_interval_minutes=20,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="suriyandhanapal@gmail.com",
        smtp_password="secretpassword",
        smtp_from="suriyandhanapal@gmail.com",
        candidate_name="Suriyan Dhanapal",
        candidate_email="suriyandhanapal@gmail.com",
        resume_path=str(dummy_resume),
        db_path=str(tmp_path / "test.db"),
    )


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "outreach_test.db")


@pytest.fixture
def sample_article() -> Article:
    return Article(
        id="art-101",
        feed_name="TechCrunch Startups",
        title="Agentic AI startup Nexus raises $12M Series A for compliance automation",
        link="https://techcrunch.com/nexus-12m",
        summary=(
            "Nexus has secured $12M in Series A funding to expand its agentic AI compliance tools."
        ),
        matched=1,
        notified=1,
    )


@pytest.fixture
def sample_extraction() -> Extraction:
    return Extraction(
        article_id="art-101",
        company="Nexus AI",
        amount=12.0,
        currency="USD",
        stage="Series A",
        investors=["Sequoia Capital"],
        sector="Enterprise AI / Compliance",
        location="Bengaluru",
        domain="nexusai.io",
        founders=[{"name": "Aravind Sharma", "role": "Co-founder & CEO"}],
        emails=[
            {
                "name": "Aravind Sharma",
                "role": "Co-founder & CEO",
                "email": "aravind@nexusai.io",
                "source": "pattern_permutation",
                "verified": True,
            }
        ],
    )


# -----------------------------------------------------------------------------
# 1. Candidate Profile & Resume Checker Tests
# -----------------------------------------------------------------------------


def test_check_resume_existing(tmp_path: Path) -> None:
    test_pdf = tmp_path / "Suriyan.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 sample content " + b"x" * 2048)
    res = check_resume(test_pdf)
    assert res["exists"] is True
    assert res["filename"] == "Suriyan.pdf"
    assert res["size_bytes"] > 0
    assert res["size_kb"] > 0


def test_check_resume_non_existing() -> None:
    res = check_resume("/non/existent/path/Suriyan.pdf")
    assert res["exists"] is False
    assert res["size_bytes"] == 0


def test_candidate_profile_defaults() -> None:
    profile = CandidateProfile()
    assert profile.name == "Suriyan Dhanapal"
    assert "suriyandhanapal@gmail.com" in profile.email
    assert "iamsuriyan" in profile.github


# -----------------------------------------------------------------------------
# 2. Template Generation & Human Review Safety Tests
# -----------------------------------------------------------------------------


def test_resolve_recipient_founder_email(sample_extraction: Extraction) -> None:
    name, email = resolve_recipient(sample_extraction)
    assert name == "Aravind Sharma"
    assert email == "aravind@nexusai.io"


def test_resolve_recipient_no_email_with_founder() -> None:
    extraction = Extraction(
        article_id="art-102",
        company="CloudScale",
        founders=[{"name": "Priya Nair", "role": "Founder"}],
        emails=[],
    )
    name, email = resolve_recipient(extraction)
    assert name == "Priya Nair"
    assert email is None


def test_resolve_recipient_none() -> None:
    name, email = resolve_recipient(None)
    assert name == "Founding Team"
    assert email is None


def test_generate_job_enquiry_human_review_guarantee(
    sample_article: Article,
    sample_extraction: Extraction,
    sample_settings: Settings,
) -> None:
    """CRITICAL TEST: Ensure generated job enquiry is STRICTLY saved as a draft and NOT sent."""
    draft = generate_job_enquiry(sample_article, sample_extraction, sample_settings)

    # Human review guarantee
    assert draft.status == "draft"
    assert draft.sent_at is None
    assert draft.error_message is None

    # Personalized content verification
    assert draft.company == "Nexus AI"
    assert draft.recipient_name == "Aravind Sharma"
    assert draft.recipient_email == "aravind@nexusai.io"

    # Subject line check
    assert "Nexus AI" not in draft.subject or "Series A" in draft.subject
    assert "Suriyan Dhanapal" in draft.subject

    # Body check for Suriyan's actual background and proof points
    assert "Cooper Compass" in draft.body
    assert "DGFT, GST, CBIC" in draft.body
    assert "Mindgryd" in draft.body
    assert "pgvector" in draft.body
    assert "FastAPI" in draft.body
    assert "iamsuriyan.github.io/Portfolio" in draft.body
    assert "suriyandhanapal@gmail.com" in draft.body
    assert draft.attach_resume is True
    assert draft.resume_path == sample_settings.resume_path


# -----------------------------------------------------------------------------
# 3. Database Outbox Operations Tests
# -----------------------------------------------------------------------------


def test_database_draft_crud(database: Database, sample_settings: Settings) -> None:
    draft = DraftEmail(
        id="draft_test_1",
        article_id="art-1",
        company="Acme Robotics",
        recipient_name="Elon",
        recipient_email="elon@acme.com",
        subject="Congrats on the Seed Round!",
        body="Hi Elon, huge congrats on the round...",
        resume_path=sample_settings.resume_path,
        attach_resume=True,
        status="draft",
        created_at="2026-11-21T21:00:00Z",
    )

    # 1. Create
    draft_id = database.create_draft(draft)
    assert draft_id == "draft_test_1"

    # 2. Get by ID
    loaded = database.get_draft("draft_test_1")
    assert loaded is not None
    assert loaded.company == "Acme Robotics"
    assert loaded.status == "draft"

    # 3. Get by article
    by_art = database.get_draft_by_article("art-1")
    assert by_art is not None
    assert by_art.id == "draft_test_1"

    # 4. Update
    updated = database.update_draft(
        draft_id="draft_test_1",
        subject="Updated Subject for Acme",
        recipient_email="new_email@acme.com",
    )
    assert updated is not None
    assert updated.subject == "Updated Subject for Acme"
    assert updated.recipient_email == "new_email@acme.com"

    # 5. List
    drafts = database.list_drafts(status="draft")
    assert len(drafts) == 1
    assert drafts[0].id == "draft_test_1"

    # 6. Mark Sent
    database.mark_draft_sent("draft_test_1")
    sent_draft = database.get_draft("draft_test_1")
    assert sent_draft is not None
    assert sent_draft.status == "sent"
    assert sent_draft.sent_at is not None

    # 7. Mark Failed
    database.mark_draft_failed("draft_test_1", "Connection timeout error")
    failed_draft = database.get_draft("draft_test_1")
    assert failed_draft is not None
    assert failed_draft.status == "failed"
    assert failed_draft.error_message == "Connection timeout error"

    # 8. Stats
    stats = database.get_draft_stats()
    assert stats["total"] == 1
    assert stats["failed"] == 1
    assert stats["draft"] == 0

    # 9. Delete
    deleted = database.delete_draft("draft_test_1")
    assert deleted is True
    assert database.get_draft("draft_test_1") is None


# -----------------------------------------------------------------------------
# 4. SMTP Dispatch Engine Tests (Mocked smtplib)
# -----------------------------------------------------------------------------


def test_send_outreach_email_success(sample_settings: Settings) -> None:
    draft = DraftEmail(
        id="draft_send_ok",
        company="HyperScale",
        recipient_name="Sarah",
        recipient_email="sarah@hyperscale.com",
        subject="Intro from Suriyan Dhanapal",
        body="Hi Sarah, would love to connect.",
        resume_path=sample_settings.resume_path,
        attach_resume=True,
        status="draft",
        created_at="2026-11-21T21:00:00Z",
    )

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        send_outreach_email(draft, sample_settings)

        # Verification
        mock_smtp_cls.assert_called_once_with(
            sample_settings.smtp_host, sample_settings.smtp_port, timeout=15.0
        )
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            sample_settings.smtp_user, sample_settings.smtp_password
        )
        mock_server.send_message.assert_called_once()

        # Check message content and attachment
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["Subject"] == "Intro from Suriyan Dhanapal"
        assert "sarah@hyperscale.com" in sent_msg["To"]
        assert "Suriyan Dhanapal" in sent_msg["From"]
        # Verify attachment was included
        attachments = list(sent_msg.iter_attachments())
        assert len(attachments) == 1
        assert "Resume.pdf" in attachments[0].get_filename()


def test_send_outreach_email_missing_recipient(sample_settings: Settings) -> None:
    draft = DraftEmail(
        id="draft_no_email",
        company="HyperScale",
        recipient_name="Sarah",
        recipient_email="",  # Missing email
        subject="Intro",
        body="Hi Sarah",
        created_at="2026-11-21T21:00:00Z",
    )
    with pytest.raises(ValueError, match="Recipient email is missing"):
        send_outreach_email(draft, sample_settings)


def test_send_outreach_email_missing_smtp_host(sample_settings: Settings) -> None:
    sample_settings.smtp_host = None
    draft = DraftEmail(
        id="draft_no_host",
        company="HyperScale",
        recipient_email="sarah@hyperscale.com",
        subject="Intro",
        body="Hi Sarah",
        created_at="2026-11-21T21:00:00Z",
    )
    with pytest.raises(ValueError, match="SMTP_HOST is not configured"):
        send_outreach_email(draft, sample_settings)


# -----------------------------------------------------------------------------
# 5. FastAPI REST API Outbox Endpoints Tests
# -----------------------------------------------------------------------------


def test_web_outbox_api_flow(
    database: Database,
    sample_settings: Settings,
    sample_article: Article,
    sample_extraction: Extraction,
) -> None:
    database.insert_article(sample_article)
    database.save_extraction(sample_extraction)

    app = create_app(settings=sample_settings, db=database)
    client = TestClient(app)

    # 1. Resume status check
    resp_res = client.get("/api/outbox/resume/status")
    assert resp_res.status_code == 200
    assert resp_res.json()["exists"] is True

    # 2. Download resume
    resp_dl = client.get("/api/outbox/resume/download")
    assert resp_dl.status_code == 200
    assert resp_dl.headers["content-type"] == "application/pdf"

    # 3. Generate draft for article
    resp_gen = client.post(f"/api/outbox/generate/{sample_article.id}")
    assert resp_gen.status_code == 200
    draft_data = resp_gen.json()
    draft_id = draft_data["id"]
    assert draft_data["status"] == "draft"  # Strictly draft
    assert draft_data["company"] == "Nexus AI"
    assert draft_data["recipient_email"] == "aravind@nexusai.io"

    # 4. List outbox
    resp_list = client.get("/api/outbox")
    assert resp_list.status_code == 200
    data = resp_list.json()
    assert len(data["items"]) == 1
    assert data["stats"]["draft"] == 1
    assert data["stats"]["sent"] == 0

    # 5. Update draft (human review edit)
    resp_up = client.put(
        f"/api/outbox/{draft_id}",
        json={
            "recipient_name": "Aravind",
            "subject": "Customized Subject Line",
            "body": "Updated customized cold pitch text.",
            "attach_resume": True,
        },
    )
    assert resp_up.status_code == 200
    assert resp_up.json()["subject"] == "Customized Subject Line"

    # 6. Human Review Send via SMTP (Mocked)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        resp_send = client.post(f"/api/outbox/{draft_id}/send")
        assert resp_send.status_code == 200
        assert resp_send.json()["ok"] is True
        assert resp_send.json()["status"] == "sent"

    # 7. Verify status changed to sent
    resp_check = client.get(f"/api/outbox/{draft_id}")
    assert resp_check.status_code == 200
    assert resp_check.json()["status"] == "sent"
    assert resp_check.json()["sent_at"] is not None

    # 8. Configure SMTP runtime
    resp_cfg = client.post(
        "/api/outbox/smtp/config",
        json={"smtp_host": "smtp.gmail.com", "smtp_port": 587},
    )
    assert resp_cfg.status_code == 200
    assert sample_settings.smtp_host == "smtp.gmail.com"

    # 9. Delete draft
    resp_del = client.delete(f"/api/outbox/{draft_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["ok"] is True


# -----------------------------------------------------------------------------
# 6. Typer CLI Outbox Commands Tests
# -----------------------------------------------------------------------------


def test_cli_outbox_commands(
    database: Database,
    sample_settings: Settings,
    sample_article: Article,
    sample_extraction: Extraction,
    tmp_path: Path,
) -> None:
    database.insert_article(sample_article)
    database.save_extraction(sample_extraction)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f"""
poll_interval_minutes: 20
db_path: "{database.db_path}"
smtp_host: "smtp.example.com"
smtp_port: 587
smtp_user: "user@example.com"
smtp_password: "pw"
resume_path: "{sample_settings.resume_path}"
"""
    )

    # 1. Check resume CLI
    res = runner.invoke(cli_app, ["outbox", "resume", "--config", str(config_file)])
    assert res.exit_code == 0
    assert "Resume found" in res.output

    # 2. Generate draft CLI
    res_gen = runner.invoke(
        cli_app,
        ["outbox", "generate", sample_article.id, "--config", str(config_file)],
    )
    assert res_gen.exit_code == 0
    assert "Created draft" in res_gen.output
    assert "Status is 'DRAFT'" in res_gen.output

    # 3. List outbox CLI
    res_list = runner.invoke(cli_app, ["outbox", "list", "--config", str(config_file)])
    assert res_list.exit_code == 0
    assert "Nexus AI" in res_list.output
    assert "DRAFT" in res_list.output

    # Fetch draft ID
    draft = database.get_draft_by_article(sample_article.id)
    assert draft is not None

    # 4. Show draft CLI
    res_show = runner.invoke(cli_app, ["outbox", "show", draft.id, "--config", str(config_file)])
    assert res_show.exit_code == 0
    assert "Nexus AI" in res_show.output
    assert "Mindgryd" in res_show.output or "Cooper" in res_show.output

    # 5. Send draft CLI with --yes (Human confirmation bypass)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        res_send = runner.invoke(
            cli_app,
            ["outbox", "send", draft.id, "--yes", "--config", str(config_file)],
        )
        assert res_send.exit_code == 0
        assert "Successfully dispatched" in res_send.output
