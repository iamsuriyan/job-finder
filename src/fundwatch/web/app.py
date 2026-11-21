"""FastAPI application providing REST endpoints and serving the monochrome dashboard."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from fundwatch import __version__
from fundwatch.db import Database
from fundwatch.fetcher import inspect_feed
from fundwatch.models import Settings
from fundwatch.notifiers import build_notifiers
from fundwatch.pipeline import run_cycle
from fundwatch.web.templates import DASHBOARD_HTML

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
    def index() -> str:
        """Serve the single-page clean monochrome dashboard."""
        return DASHBOARD_HTML

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
        }

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
