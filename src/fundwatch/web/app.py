"""FastAPI application providing REST endpoints and serving the monochrome dashboard."""

from __future__ import annotations

import csv
import io
import logging
import smtplib
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from fundwatch import __version__
from fundwatch.db import Database
from fundwatch.fetcher import inspect_feed
from fundwatch.models import Settings
from fundwatch.notifiers import build_notifiers
from fundwatch.outreach import check_resume, generate_job_enquiry, send_outreach_email
from fundwatch.pipeline import run_cycle
from fundwatch.web.templates import get_dashboard_html

logger = logging.getLogger(__name__)


def create_app(settings: Settings, db: Database) -> FastAPI:
    """Create and configure the FastAPI web application."""
    app = FastAPI(
        title="fundwatch Dashboard",
        description="Clean monochrome web dashboard for monitoring startup funding rounds.",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    @app.head("/", response_class=HTMLResponse)
    def index() -> str:
        """Serve the single-page clean monochrome dashboard."""
        return get_dashboard_html()

    @app.get("/api/stats")
    def get_stats() -> dict[str, Any]:
        """Return total article counts, matched funding rounds, and feed breakdown."""
        stats_data = db.get_stats()
        states = db.get_all_feed_states()
        state_map = {s["url"]: s for s in states}

        feeds_summary: list[dict[str, Any]] = []
        healthy_count = 0
        for f in settings.feeds:
            st = state_map.get(f.url)
            failures = st.get("consecutive_failures", 0) if st else 0
            is_healthy = failures < 5
            if is_healthy:
                healthy_count += 1
            feeds_summary.append(
                {
                    "name": f.name,
                    "url": f.url,
                    "healthy": is_healthy,
                    "consecutive_failures": failures,
                    "last_ok_at": st.get("last_ok_at") if st else None,
                }
            )

        return {
            "total": stats_data["total"],
            "matched": stats_data["matched"],
            "notified": stats_data["notified"],
            "total_feeds": len(settings.feeds),
            "healthy_feeds": healthy_count,
            "by_feed": stats_data["by_feed"],
            "by_day": stats_data["by_day"],
            "feeds": feeds_summary,
        }

    @app.get("/api/articles")
    def list_articles(
        page: int = Query(1, ge=1),
        limit: int = Query(24, ge=1, le=100),
        matched_only: bool = Query(True),
        search: str | None = Query(None),
        feed: str | None = Query(None),
        stage: str | None = Query(None),
    ) -> dict[str, Any]:
        """Return paginated articles with extractions and filtering."""
        offset = (page - 1) * limit
        articles, total = db.get_articles_paged(
            limit=limit,
            offset=offset,
            matched_only=matched_only,
            search=search,
            feed_name=feed,
            stage=stage,
        )
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        return {
            "items": articles,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    @app.get("/api/feeds")
    def list_feeds() -> list[dict[str, Any]]:
        """List all configured feeds merged with their HTTP cache and health states."""
        states = db.get_all_feed_states()
        state_map = {s["url"]: s for s in states}

        result: list[dict[str, Any]] = []
        for f in settings.feeds:
            st = state_map.get(f.url)
            result.append(
                {
                    "name": f.name,
                    "url": f.url,
                    "etag": st.get("etag") if st else None,
                    "last_modified": st.get("last_modified") if st else None,
                    "last_ok_at": st.get("last_ok_at") if st else None,
                    "consecutive_failures": st.get("consecutive_failures", 0) if st else 0,
                    "healthy": (st.get("consecutive_failures", 0) < 5) if st else True,
                }
            )
        return result

    @app.post("/api/feeds/test")
    def test_single_feed(payload: dict[str, str]) -> dict[str, Any]:
        """Inspect and test a feed live."""
        url = payload.get("url")
        if not url:
            return {"ok": False, "error": "URL is required"}
        # Find feed config or create temporary
        matched_feed = next((f for f in settings.feeds if f.url == url), None)
        feed_name = matched_feed.name if matched_feed else "TestFeed"

        from fundwatch.models import Feed

        feed_obj = Feed(name=feed_name, url=url)
        return inspect_feed(feed_obj, settings.user_agent, timeout=settings.request_timeout_seconds)

    @app.get("/api/config")
    def get_config_summary() -> dict[str, Any]:
        """Return safe, non-secret configuration details."""
        return {
            "poll_interval_minutes": settings.poll_interval_minutes,
            "jitter_seconds": settings.jitter_seconds,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_items_per_feed": settings.max_items_per_feed,
            "max_article_age_days": settings.max_article_age_days,
            "user_agent": settings.user_agent,
            "feeds_count": len(settings.feeds),
            "funding_keywords": settings.filters.funding_keywords,
            "exclude_keywords": settings.filters.exclude_keywords,
            "sector_keywords": settings.filters.sector_keywords,
            "geo_keywords": settings.filters.geo_keywords,
            "match_in_summary": settings.filters.match_in_summary,
            "notifiers": [
                {"type": n.type, "enabled": n.enabled, "topic": n.topic} for n in settings.notifiers
            ],
            "llm_extraction_enabled": settings.llm_extraction.enabled,
            "llm_model": settings.llm_extraction.model,
            "db_path": settings.db_path,
            "candidate": {
                "name": settings.candidate_name,
                "title": settings.candidate_title,
                "email": settings.candidate_email,
                "phone": settings.candidate_phone,
                "location": settings.candidate_location,
                "portfolio": settings.candidate_portfolio,
                "github": settings.candidate_github,
                "linkedin": settings.candidate_linkedin,
                "resume_path": settings.resume_path,
            },
            "smtp": {
                "configured": bool(
                    settings.smtp_host and settings.smtp_user and settings.smtp_password
                ),
                "host": settings.smtp_host,
                "port": settings.smtp_port,
                "user": settings.smtp_user,
                "from_email": settings.smtp_from or settings.smtp_user or settings.candidate_email,
            },
        }

    # -------------------------------------------------------------------------
    # Outbox & Human-in-the-Loop Job Enquiry Endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/outbox")
    def list_outbox_drafts(
        status: str | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, Any]:
        """List email drafts and outbox statistics."""
        drafts = db.list_drafts(status=status, limit=limit)
        draft_stats = db.get_draft_stats()
        return {
            "items": [d.model_dump() for d in drafts],
            "stats": draft_stats,
        }

    @app.get("/api/outbox/resume/status")
    def get_resume_status() -> dict[str, Any]:
        """Check status and metadata for candidate's resume file."""
        return check_resume(settings.resume_path)

    @app.get("/api/outbox/resume/download")
    def download_resume() -> FileResponse:
        """Download or view the candidate's resume PDF."""
        p = Path(settings.resume_path)
        if not p.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume file not found at {settings.resume_path}",
            )
        return FileResponse(
            str(p),
            media_type="application/pdf",
            filename=f"{settings.candidate_name.replace(' ', '_')}_Resume.pdf",
        )

    @app.get("/api/outbox/{draft_id}")
    def get_draft_by_id(draft_id: str) -> dict[str, Any]:
        """Get single draft by ID."""
        draft = db.get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
        return draft.model_dump()

    @app.post("/api/outbox/generate")
    @app.post("/api/outbox/generate/{article_id:path}")
    def generate_draft_for_article(
        article_id: str | None = None,
        article_id_query: str | None = Query(None, alias="article_id"),
        force: bool = Query(False),
    ) -> dict[str, Any]:
        """Generate a personalized job enquiry draft for a funded startup article."""
        target_id = article_id or article_id_query
        if not target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="article_id is required",
            )

        article = db.get_article(target_id)
        if not article:
            from urllib.parse import unquote

            article = db.get_article(unquote(target_id))

        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

        # Check if already generated unless force=True
        if not force:
            existing = db.get_draft_by_article(target_id)
            if existing:
                return existing.model_dump()

        extraction = db.get_extraction(article.id)
        draft = generate_job_enquiry(article, extraction, settings)
        db.create_draft(draft)
        return draft.model_dump()

    @app.put("/api/outbox/{draft_id}")
    def update_draft_by_id(
        draft_id: str,
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        """Update draft subject, body, recipient, or attachment prior to sending."""
        updated = db.update_draft(
            draft_id=draft_id,
            company=payload.get("company"),
            recipient_name=payload.get("recipient_name"),
            recipient_email=payload.get("recipient_email"),
            subject=payload.get("subject"),
            body=payload.get("body"),
            resume_path=payload.get("resume_path"),
            attach_resume=payload.get("attach_resume"),
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
        return updated.model_dump()

    @app.delete("/api/outbox/{draft_id}")
    def delete_draft_by_id(draft_id: str) -> dict[str, Any]:
        """Delete an outbox draft."""
        success = db.delete_draft(draft_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
        return {"ok": True, "draft_id": draft_id}

    @app.post("/api/outbox/{draft_id}/send")
    def send_draft_via_smtp(draft_id: str) -> dict[str, Any]:
        """HUMAN-IN-THE-LOOP ACTION: Dispatch an email draft via SMTP."""
        draft = db.get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        if not draft.recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient email address is required. Please edit the draft before sending.",
            )

        try:
            send_outreach_email(draft, settings, timeout=settings.request_timeout_seconds)
            db.mark_draft_sent(draft.id)
            return {
                "ok": True,
                "status": "sent",
                "draft_id": draft.id,
                "recipient": draft.recipient_email,
                "message": f"Job enquiry successfully dispatched to {draft.recipient_email}!",
            }
        except Exception as exc:
            err_msg = str(exc)
            logger.error("Failed to send draft %s: %s", draft.id, err_msg)
            db.mark_draft_failed(draft.id, err_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            ) from exc

    @app.post("/api/outbox/smtp/config")
    def update_smtp_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Configure runtime SMTP settings and candidate profile."""
        if "smtp_host" in payload:
            settings.smtp_host = str(payload["smtp_host"]).strip() or None
        if "smtp_port" in payload:
            try:
                settings.smtp_port = int(payload["smtp_port"])
            except (ValueError, TypeError):
                pass
        if "smtp_user" in payload:
            settings.smtp_user = str(payload["smtp_user"]).strip() or None
        if "smtp_password" in payload:
            settings.smtp_password = str(payload["smtp_password"]).strip() or None
        if "smtp_from" in payload:
            settings.smtp_from = str(payload["smtp_from"]).strip() or None
        if "candidate_name" in payload:
            settings.candidate_name = str(payload["candidate_name"]).strip()
        if "candidate_email" in payload:
            settings.candidate_email = str(payload["candidate_email"]).strip()
        if "resume_path" in payload:
            settings.resume_path = str(payload["resume_path"]).strip()

        return {
            "ok": True,
            "smtp_configured": bool(
                settings.smtp_host and settings.smtp_user and settings.smtp_password
            ),
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_user": settings.smtp_user,
            "candidate_name": settings.candidate_name,
            "candidate_email": settings.candidate_email,
            "resume_path": settings.resume_path,
        }

    @app.post("/api/outbox/smtp/test")
    def test_smtp_connection() -> dict[str, Any]:
        """Test SMTP connection and credentials without sending an email."""
        if not settings.smtp_host:
            return {"ok": False, "error": "SMTP_HOST is not configured."}

        port = settings.smtp_port or 587
        try:
            with smtplib.SMTP(settings.smtp_host, port, timeout=10.0) as server:
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
            return {
                "ok": True,
                "message": (
                    f"Successfully connected and authenticated with {settings.smtp_host}:{port}!"
                ),
            }
        except Exception as exc:
            return {"ok": False, "error": f"SMTP connection failed: {exc}"}

    @app.post("/api/poll")
    def trigger_poll(dry_run: bool = Query(False)) -> dict[str, Any]:
        """Trigger an on-demand poll cycle."""
        notifiers = [] if dry_run else build_notifiers(settings)
        cycle_stats = run_cycle(
            settings=settings,
            db=db,
            notifiers=notifiers,
            dry_run=dry_run,
            delay_between_feeds=0.5,
        )
        return {
            "ok": True,
            "dry_run": dry_run,
            "fetched": cycle_stats.fetched,
            "new": cycle_stats.new,
            "matched": cycle_stats.matched,
            "notified": cycle_stats.notified,
            "errors": cycle_stats.errors,
        }

    @app.get("/api/export")
    def export_csv() -> StreamingResponse:
        """Stream matched articles joined with extractions as CSV."""
        rows = db.get_matched_articles_with_extractions()
        if not rows:
            output = io.StringIO()
            output.write("id,feed_name,title,link,published_at,first_seen_at,notified\n")
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=funding.csv"},
            )

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=funding.csv"},
        )

    @app.post("/api/test-notify")
    def test_notification() -> dict[str, Any]:
        """Dispatch a test alert through all configured notifiers."""
        notifiers = build_notifiers(settings)
        if not notifiers:
            return {"ok": False, "message": "No notifiers are enabled with required secrets."}

        results: list[dict[str, Any]] = []
        test_msg = "🧪 fundwatch test alert: web dashboard test notification."
        for n in notifiers:
            try:
                n.send_text(test_msg)
                results.append({"name": n.name, "success": True, "error": None})
            except Exception as exc:
                results.append({"name": n.name, "success": False, "error": str(exc)})

        all_ok = any(r["success"] for r in results)
        return {"ok": all_ok, "channels": results}

    return app
