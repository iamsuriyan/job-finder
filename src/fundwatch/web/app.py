"""FastAPI application providing REST endpoints and serving the monochrome dashboard."""

from __future__ import annotations

import csv
import io
import logging
import os
import smtplib
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, set_key
from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from fundwatch import __version__
from fundwatch.db import Database, utc_now_iso
from fundwatch.fetcher import inspect_feed
from fundwatch.models import CandidateProfile, Extraction, Settings
from fundwatch.notifiers import build_notifiers
from fundwatch.outreach import check_resume, generate_job_enquiry, send_outreach_email
from fundwatch.pipeline import CycleStats, auto_generate_missing_drafts, run_cycle
from fundwatch.resume_parser import parse_resume_to_profile
from fundwatch.web.templates import get_assets_dir, get_dashboard_html

logger = logging.getLogger(__name__)

RESUMES_DIR = Path("data/resumes")


class ScraperManager:
    """Manages continuous background job discovery, feed scraping, and automatic job enquiry drafting."""

    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.mode: str = "continuous"
        self.is_scraping: bool = False
        self.current_feed: str | None = None
        self.feed_index: int = 0
        self.feed_total: int = len(settings.feeds)
        self.cycle_count: int = 0
        self.cooldown_seconds: int = 15
        self.last_polled_at: str | None = None
        self.last_poll_status: str | None = None
        self.last_poll_stats: dict[str, int] | None = None
        self.last_error: str | None = None
        self.next_poll_at: str | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            progress = 0
            if self.feed_total > 0 and self.is_scraping:
                progress = round((self.feed_index / self.feed_total) * 100)
            elif not self.is_scraping and self.last_polled_at:
                progress = 100

            draft_stats = self.db.get_draft_stats()
            total_jobs = draft_stats.get("total", 0)

            return {
                "is_scraping": self.is_scraping,
                "mode": self.mode,
                "current_feed": self.current_feed,
                "feed_index": self.feed_index,
                "feed_total": self.feed_total,
                "progress_percent": progress,
                "cycle_count": self.cycle_count,
                "total_jobs_ready": total_jobs,
                "last_polled_at": self.last_polled_at,
                "last_poll_status": self.last_poll_status,
                "last_poll_stats": self.last_poll_stats,
                "last_error": self.last_error,
                "next_poll_at": self.next_poll_at,
                "interval_minutes": self.settings.poll_interval_minutes,
                "cooldown_seconds": self.cooldown_seconds,
            }

    def _feed_progress(self, index: int, total: int, feed_name: str) -> None:
        with self._lock:
            self.feed_index = index
            self.feed_total = total
            self.current_feed = feed_name

    def execute_cycle(self, dry_run: bool = False) -> CycleStats:
        with self._lock:
            self.is_scraping = True
            self.feed_index = 0
            self.feed_total = len(self.settings.feeds)
            self.current_feed = "Scanning startup feeds for funding rounds..."
            self.last_poll_status = "running"
            self.last_error = None

        stats = CycleStats()
        try:
            notifiers = [] if dry_run else build_notifiers(self.settings)
            stats = run_cycle(
                settings=self.settings,
                db=self.db,
                notifiers=notifiers,
                dry_run=dry_run,
                delay_between_feeds=0.5,
                feed_callback=self._feed_progress,
                auto_generate_drafts=True,
            )

            # Backfill any existing matched articles that do not have outbox drafts yet
            if not dry_run:
                try:
                    new_drafts = auto_generate_missing_drafts(self.settings, self.db, limit=100)
                    if new_drafts > 0:
                        logger.info(
                            "Auto-generated %d new personalized job enquiry drafts", new_drafts
                        )
                except Exception as draft_err:
                    logger.debug("Backfill draft error: %s", draft_err)

            with self._lock:
                self.cycle_count += 1
                self.last_poll_status = "completed"
                self.last_error = None
        except Exception as exc:
            logger.exception("Continuous discovery cycle failed: %s", exc)
            with self._lock:
                self.last_poll_status = "error"
                self.last_error = str(exc)
        finally:
            now_utc = datetime.now(timezone.utc)
            with self._lock:
                self.is_scraping = False
                self.current_feed = None
                self.last_polled_at = now_utc.isoformat()
                self.last_poll_stats = {
                    "fetched": stats.fetched,
                    "new": stats.new,
                    "matched": stats.matched,
                    "notified": stats.notified,
                    "errors": stats.errors,
                }
                self.next_poll_at = (
                    now_utc + timedelta(seconds=self.cooldown_seconds)
                ).isoformat()
        return stats

    def trigger_poll(self, dry_run: bool = False) -> bool:
        """Trigger an on-demand poll in a background thread if not already running."""
        with self._lock:
            if self.is_scraping:
                return False

        worker = threading.Thread(
            target=self.execute_cycle,
            args=(dry_run,),
            daemon=True,
            name="ScraperWorkerThread",
        )
        worker.start()
        return True

    def start_scheduler(self) -> None:
        """Start continuous background discovery engine in a daemon thread."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        self._stop_event.clear()

        def _loop() -> None:
            logger.info(
                "Continuous job discovery engine started (running continuously, cooldown=%ds between cycles)",
                self.cooldown_seconds,
            )
            time.sleep(1.0)
            while not self._stop_event.is_set():
                try:
                    self.execute_cycle(dry_run=False)
                except Exception as exc:
                    logger.error("Continuous discovery cycle loop error: %s", exc)

                # Continuous mode: brief pause between full sweeps
                if self._stop_event.wait(self.cooldown_seconds):
                    break

        self._scheduler_thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="ContinuousJobDiscoveryLoop",
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        self._stop_event.set()


def create_app(
    settings: Settings,
    db: Database,
    auto_start_scraper: bool = True,
) -> FastAPI:
    """Create and configure the FastAPI web application."""
    scraper = ScraperManager(settings, db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if auto_start_scraper and "PYTEST_CURRENT_TEST" not in os.environ:
            scraper.start_scheduler()
        yield
        scraper.stop_scheduler()

    app = FastAPI(
        title="fundwatch Dashboard",
        description="Clean monochrome web dashboard for monitoring startup funding rounds.",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    assets_dir = get_assets_dir()
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

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
            "first_funding_count": stats_data.get("first_funding_count", 0),
            "seed_count": stats_data.get("seed_count", 0),
            "series_a_count": stats_data.get("series_a_count", 0),
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

    @app.get("/api/scraper/status")
    def get_scraper_status() -> dict[str, Any]:
        """Return real-time scraping state, active feed, and countdown."""
        return scraper.get_status()

    @app.post("/api/scraper/poll")
    def trigger_scraper_poll(dry_run: bool = Query(False)) -> dict[str, Any]:
        """Trigger an asynchronous poll cycle in the background."""
        started = scraper.trigger_poll(dry_run=dry_run)
        return {
            "ok": True,
            "status": "started" if started else "already_running",
            "message": (
                "Scrape cycle started in background"
                if started
                else "Scrape cycle is already in progress"
            ),
        }

    @app.get("/api/config")
    def get_config_summary() -> dict[str, Any]:
        """Return safe, non-secret configuration details."""
        has_pw = bool(settings.smtp_password)
        masked_pw = (
            ("•" * 12 + settings.smtp_password[-4:])
            if (settings.smtp_password and len(settings.smtp_password) >= 4)
            else ("••••••••" if has_pw else "")
        )
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
                "host": settings.smtp_host or "",
                "port": settings.smtp_port or 587,
                "user": settings.smtp_user or "",
                "from_email": settings.smtp_from or settings.smtp_user or settings.candidate_email or "",
                "has_password": has_pw,
                "password_masked": masked_pw,
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
        contacted = db.get_contacted_recipients_map()
        return {
            "items": [d.model_dump() for d in drafts],
            "stats": draft_stats,
            "contacted_recipients": contacted,
        }

    @app.get("/api/candidate/profile")
    def get_candidate_profile() -> dict[str, Any]:
        """Fetch active candidate profile and resume status."""
        profile = db.get_candidate_profile("active")
        if not profile:
            profile = CandidateProfile(
                id="active",
                name=settings.candidate_name,
                title=settings.candidate_title,
                email=settings.candidate_email,
                phone=settings.candidate_phone,
                location=settings.candidate_location,
                portfolio=settings.candidate_portfolio,
                github=settings.candidate_github,
                linkedin=settings.candidate_linkedin,
                resume_path=settings.resume_path,
                resume_filename=(
                    Path(settings.resume_path).name if settings.resume_path else "Resume.pdf"
                ),
            )
        return profile.model_dump()

    @app.post("/api/candidate/resume/upload")
    async def upload_candidate_resume(file: UploadFile = File(...)) -> dict[str, Any]:
        """Upload and deterministically parse candidate resume PDF."""
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF resume files (.pdf) are supported.",
            )

        RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        clean_name = Path(file.filename).name
        target_path = RESUMES_DIR / clean_name
        content = await file.read()
        target_path.write_bytes(content)

        profile = parse_resume_to_profile(
            pdf_source=content,
            resume_path=str(target_path),
            resume_filename=clean_name,
        )
        db.save_candidate_profile(profile)

        # Sync in-memory settings
        settings.resume_path = str(target_path)
        settings.candidate_name = profile.name
        settings.candidate_title = profile.title
        settings.candidate_email = profile.email
        settings.candidate_phone = profile.phone
        settings.candidate_location = profile.location
        settings.candidate_portfolio = profile.portfolio
        settings.candidate_github = profile.github
        settings.candidate_linkedin = profile.linkedin

        _sync_pending_drafts(profile)

        return profile.model_dump()

    def _sync_pending_drafts(cand_profile: CandidateProfile) -> int:
        """Update subject, body, and resume on all drafts currently in 'draft' status."""
        drafts = db.list_drafts(status="draft")
        count = 0
        for d in drafts:
            if not d.article_id:
                continue
            article = db.get_article(d.article_id)
            if not article:
                continue
            extraction = db.get_extraction(d.article_id)
            new_draft = generate_job_enquiry(article, extraction, settings, candidate=cand_profile)
            db.update_draft(
                draft_id=d.id,
                subject=new_draft.subject,
                body=new_draft.body,
                resume_path=new_draft.resume_path,
                recipient_name=new_draft.recipient_name,
                recipient_email=new_draft.recipient_email,
            )
            count += 1
        return count

    @app.put("/api/candidate/profile")
    def update_candidate_profile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Update active candidate profile fields and pitch bullets."""
        existing = db.get_candidate_profile("active")
        if not existing:
            existing = CandidateProfile(
                name=settings.candidate_name,
                title=settings.candidate_title,
                email=settings.candidate_email,
                phone=settings.candidate_phone,
                location=settings.candidate_location,
                portfolio=settings.candidate_portfolio,
                github=settings.candidate_github,
                linkedin=settings.candidate_linkedin,
                resume_path=settings.resume_path,
            )

        valid_fields = {k: v for k, v in payload.items() if hasattr(existing, k)}
        updated = existing.model_copy(update=valid_fields)
        updated.updated_at = utc_now_iso()
        db.save_candidate_profile(updated)

        # Sync in-memory settings
        settings.candidate_name = updated.name
        settings.candidate_title = updated.title
        settings.candidate_email = updated.email
        settings.candidate_phone = updated.phone
        settings.candidate_location = updated.location
        settings.candidate_portfolio = updated.portfolio
        settings.candidate_github = updated.github
        settings.candidate_linkedin = updated.linkedin
        if updated.resume_path:
            settings.resume_path = updated.resume_path

        # Automatically propagate title, bullets, and contact info to all pending drafts
        _sync_pending_drafts(updated)

        return updated.model_dump()

    @app.post("/api/candidate/regenerate-drafts")
    def regenerate_drafts_with_profile() -> dict[str, Any]:
        """Batch update all pending outbox drafts with the active candidate profile."""
        profile = db.get_candidate_profile("active")
        if not profile:
            profile = CandidateProfile(
                name=settings.candidate_name,
                title=settings.candidate_title,
                resume_path=settings.resume_path,
            )

        count = _sync_pending_drafts(profile)
        return {"updated_count": count}

    @app.get("/api/outbox/resume/status")
    def get_resume_status() -> dict[str, Any]:
        """Check status and metadata for candidate's resume file."""
        profile = db.get_candidate_profile("active")
        target_path = (
            profile.resume_path if profile and profile.resume_path else settings.resume_path
        )
        return check_resume(target_path)

    @app.get("/api/outbox/resume/download")
    def download_resume() -> FileResponse:
        """Download or view the candidate's resume PDF."""
        profile = db.get_candidate_profile("active")
        target_path = (
            profile.resume_path if profile and profile.resume_path else settings.resume_path
        )
        p = Path(target_path)
        if not p.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume file not found at {target_path}",
            )
        return FileResponse(
            str(p),
            media_type="application/pdf",
            filename=p.name,
            content_disposition_type="inline",
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
        existing = db.get_draft_by_article(target_id) or db.get_draft_by_article(article.id)
        if not existing:
            from fundwatch.email_finder import extract_company_name

            ext_meta = db.get_extraction(article.id)
            meta_comp = ext_meta.company if ext_meta and ext_meta.company else ""
            cand_comp = meta_comp or extract_company_name(
                article.title, article.summary or ""
            )
            existing = db.get_draft_by_company(cand_comp)

        active_profile = db.get_candidate_profile("active")
        if existing and not force and existing.recipient_email:
            # If candidate profile title or name has been updated, refresh the existing draft
            if existing.status == "draft" and active_profile and (
                active_profile.title not in existing.subject
                or active_profile.name not in existing.subject
            ):
                extraction = db.get_extraction(article.id)
                new_draft = generate_job_enquiry(
                    article, extraction, settings, candidate=active_profile
                )
                updated = db.update_draft(
                    draft_id=existing.id,
                    subject=new_draft.subject,
                    body=new_draft.body,
                    resume_path=new_draft.resume_path,
                )
                return (updated or existing).model_dump()
            return existing.model_dump()

        extraction = db.get_extraction(article.id)
        if extraction is None or not extraction.emails:
            from fundwatch.email_finder import (
                discover_founding_team_emails,
                extract_company_name,
            )

            article_full_text = f"{article.title} {article.summary or ''}"
            known_company = (
                extraction.company if extraction and extraction.company else ""
            ) or extract_company_name(article.title, article.summary or "")

            domain, founders, emails = discover_founding_team_emails(
                company_name=known_company,
                article_text=article_full_text,
                article_url=article.link,
                known_domain=extraction.domain if extraction else None,
                known_founders=extraction.founders if extraction else None,
                hunter_api_key=settings.hunter_api_key,
            )

            if extraction is None:
                extraction = Extraction(
                    article_id=article.id,
                    company=known_company,
                    domain=domain,
                    founders=founders,
                    emails=emails,
                )
            else:
                extraction.company = known_company or extraction.company
                extraction.domain = domain or extraction.domain
                extraction.founders = founders or extraction.founders
                extraction.emails = emails or extraction.emails

            db.save_extraction(extraction)

        active_profile = db.get_candidate_profile("active")
        draft = generate_job_enquiry(article, extraction, settings, candidate=active_profile)

        if existing:
            updated = db.update_draft(
                draft_id=existing.id,
                company=draft.company,
                recipient_name=draft.recipient_name,
                recipient_email=draft.recipient_email,
                subject=draft.subject,
                body=draft.body,
                resume_path=draft.resume_path,
                attach_resume=draft.attach_resume,
            )
            return (updated or draft).model_dump()

        db.create_draft(draft)
        return draft.model_dump()

    @app.post("/api/articles/{article_id:path}/dismiss")
    def dismiss_article_endpoint(article_id: str) -> dict[str, Any]:
        """Dismiss an article so it is removed from active deals."""
        db.dismiss_article(article_id)
        return {"success": True, "article_id": article_id}

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

    @app.get("/api/outbox/recipients/contacted")
    def get_contacted_recipients() -> dict[str, Any]:
        """List all recipients who have already been sent outreach emails."""
        return db.get_contacted_recipients_map()

    @app.post("/api/outbox/{draft_id}/send")
    def send_draft_via_smtp(
        draft_id: str,
        force: bool = Query(False),
    ) -> dict[str, Any]:
        """HUMAN-IN-THE-LOOP ACTION: Dispatch an email draft via SMTP."""
        draft = db.get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        if not draft.recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient email address is required. Please edit the draft before sending.",
            )

        # Recipient repetition protection: check if recipient was already emailed
        prior_sent = db.get_prior_sent_draft_for_recipient(
            draft.recipient_email, exclude_draft_id=draft.id
        )
        if prior_sent and not force:
            sent_date = prior_sent.sent_at[:10] if prior_sent.sent_at else "previously"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Recipient '{draft.recipient_email}' was already emailed on {sent_date} "
                    f"for '{prior_sent.company}'. Confirm resending to proceed."
                ),
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
        """Configure runtime SMTP settings and candidate profile, persisting to .env."""
        env_file = find_dotenv(usecwd=True) or ".env"

        if "smtp_host" in payload and payload["smtp_host"] is not None:
            val = str(payload["smtp_host"]).strip() or None
            settings.smtp_host = val
            if val:
                try:
                    set_key(env_file, "SMTP_HOST", val)
                except Exception as e:
                    logger.warning("Could not persist SMTP_HOST to .env: %s", e)

        if "smtp_port" in payload and payload["smtp_port"] is not None:
            try:
                port_val = int(payload["smtp_port"])
                settings.smtp_port = port_val
                set_key(env_file, "SMTP_PORT", str(port_val))
            except (ValueError, TypeError, Exception) as e:
                logger.warning("Could not persist SMTP_PORT to .env: %s", e)

        if "smtp_user" in payload and payload["smtp_user"] is not None:
            val = str(payload["smtp_user"]).strip() or None
            settings.smtp_user = val
            if val:
                try:
                    set_key(env_file, "SMTP_USER", val)
                except Exception as e:
                    logger.warning("Could not persist SMTP_USER to .env: %s", e)

        if "smtp_password" in payload and payload["smtp_password"] is not None:
            pw_val = str(payload["smtp_password"]).strip()
            # Only update password if a non-empty string was provided
            if pw_val:
                settings.smtp_password = pw_val
                try:
                    set_key(env_file, "SMTP_PASSWORD", pw_val)
                except Exception as e:
                    logger.warning("Could not persist SMTP_PASSWORD to .env: %s", e)

        if "smtp_from" in payload and payload["smtp_from"] is not None:
            val = str(payload["smtp_from"]).strip() or None
            settings.smtp_from = val
            if val:
                try:
                    set_key(env_file, "SMTP_FROM", val)
                except Exception as e:
                    logger.warning("Could not persist SMTP_FROM to .env: %s", e)

        if "candidate_name" in payload:
            settings.candidate_name = str(payload["candidate_name"]).strip()
        if "candidate_email" in payload:
            settings.candidate_email = str(payload["candidate_email"]).strip()
        if "resume_path" in payload:
            settings.resume_path = str(payload["resume_path"]).strip()

        has_pw = bool(settings.smtp_password)
        masked_pw = (
            ("•" * 12 + settings.smtp_password[-4:])
            if (settings.smtp_password and len(settings.smtp_password) >= 4)
            else ("••••••••" if has_pw else "")
        )

        return {
            "ok": True,
            "smtp_configured": bool(
                settings.smtp_host and settings.smtp_user and settings.smtp_password
            ),
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_user": settings.smtp_user,
            "has_password": has_pw,
            "password_masked": masked_pw,
            "candidate_name": settings.candidate_name,
            "candidate_email": settings.candidate_email,
            "resume_path": settings.resume_path,
        }

    @app.post("/api/outbox/smtp/test")
    def test_smtp_connection(payload: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
        """Test SMTP connection and credentials without sending an email."""
        req = payload or {}
        test_host = req.get("host") or settings.smtp_host
        test_port = req.get("port") or settings.smtp_port or 587
        test_user = req.get("user") or settings.smtp_user
        # Use provided password or fall back to configured settings.smtp_password from .env
        test_pw = req.get("password") or settings.smtp_password

        if not test_host:
            return {"ok": False, "error": "SMTP_HOST is not configured."}

        try:
            port_num = int(test_port)
        except (ValueError, TypeError):
            port_num = 587

        try:
            with smtplib.SMTP(test_host, port_num, timeout=10.0) as server:
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass
                if test_user and test_pw:
                    server.login(test_user, test_pw)
            return {
                "ok": True,
                "message": (
                    f"Successfully connected and authenticated with {test_host}:{port_num}!"
                ),
            }
        except Exception as exc:
            return {"ok": False, "error": f"SMTP connection failed: {exc}"}

    @app.post("/api/poll")
    def trigger_poll(
        dry_run: bool = Query(False),
        async_mode: bool = Query(True),
    ) -> dict[str, Any]:
        """Trigger an on-demand poll cycle (asynchronous by default)."""
        if async_mode:
            started = scraper.trigger_poll(dry_run=dry_run)
            return {
                "ok": True,
                "status": "started" if started else "already_running",
                "message": (
                    "Scrape cycle started in background"
                    if started
                    else "Scrape cycle is already in progress"
                ),
            }

        cycle_stats = scraper.execute_cycle(dry_run=dry_run)
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
