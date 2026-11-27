"""Pipeline orchestrating one complete poll cycle."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from fundwatch.db import Database
from fundwatch.dedup import is_fuzzy_duplicate, normalize_title
from fundwatch.extractor import extract_funding_details
from fundwatch.fetcher import fetch_feed
from fundwatch.filters import is_funding_item
from fundwatch.models import Extraction, Settings
from fundwatch.notifiers import (
    Notifier,
    format_article_message,
    send_notification_to_all,
)

logger = logging.getLogger(__name__)


@dataclass
class CycleStats:
    """Summary statistics for a poll cycle."""

    fetched: int = 0
    new: int = 0
    matched: int = 0
    notified: int = 0
    errors: int = 0


def run_cycle(
    settings: Settings,
    db: Database,
    notifiers: list[Notifier] | None = None,
    is_bootstrap: bool | None = None,
    dry_run: bool = False,
    delay_between_feeds: float = 1.0,
    http_client: httpx.Client | None = None,
    print_callback: Any = None,
    feed_callback: Any = None,
    auto_generate_drafts: bool = True,
) -> CycleStats:
    """
    Execute one complete polling cycle across all configured feeds.

    Workflow per feed:
    1. Fetch entries using conditional GET.
    2. Iterate entries (oldest first).
    3. Skip if older than max_article_age_days.
    4. Skip if already exists in DB.
    5. In bootstrap mode: store all as seen (notified=1) without alerting.
    6. Store article (matched=0).
    7. If not funding item: continue.
    8. Mark matched=1.
    9. If fuzzy duplicate: mark notified=1; continue.
    10. Extract structured data if enabled.
    11. Send notification via all enabled notifiers.
    12. Mark notified=1 on success.
    """
    stats = CycleStats()

    # Detect bootstrap mode
    if is_bootstrap is None:
        bootstrap_mode = db.is_empty()
    else:
        bootstrap_mode = is_bootstrap

    if bootstrap_mode:
        logger.info(
            "Bootstrap mode active: indexing existing articles without sending notifications."
        )

    recent_titles = db.recent_titles(hours=48)
    warn_cb = None
    if notifiers:
        from fundwatch.notifiers import send_system_alert_to_all

        warn_cb = lambda msg: send_system_alert_to_all(notifiers, msg)  # noqa: E731

    for idx, feed in enumerate(settings.feeds):
        if feed_callback:
            try:
                feed_callback(idx + 1, len(settings.feeds), feed.name)
            except Exception:
                pass

        if idx > 0 and delay_between_feeds > 0:
            time.sleep(delay_between_feeds)

        articles = fetch_feed(
            feed=feed,
            settings=settings,
            db=db,
            client=http_client,
            warn_callback=warn_cb,
        )
        stats.fetched += len(articles)

        # Process oldest first
        for article in reversed(articles):
            # Age filter
            if settings.max_article_age_days > 0 and article.published_at:
                try:
                    pub_dt = datetime.fromisoformat(article.published_at)
                    age_days = (datetime.now(UTC) - pub_dt).total_seconds() / 86400.0
                    if age_days > settings.max_article_age_days:
                        continue
                except Exception:
                    pass

            # Dedup layer 1: exact ID
            if db.has_article(article.id):
                continue

            stats.new += 1
            article.title_norm = normalize_title(article.title)

            from fundwatch.filters import classify_stage_tier

            article.stage_tier = str(classify_stage_tier(article.title, article.summary or ""))

            # Check funding keywords and early-stage filter
            matches_funding = is_funding_item(article, settings.filters)

            if bootstrap_mode:
                # In bootstrap mode: index everything, mark notified=1 so no alerts are triggered
                article.matched = 1 if matches_funding else 0
                article.notified = 1
                db.insert_article(article)
                if matches_funding:
                    stats.matched += 1
                    if settings.find_founder_emails:
                        from fundwatch.email_finder import (
                            discover_founding_team_emails,
                            extract_company_name,
                        )

                        article_full_text = f"{article.title} {article.summary or ''}"
                        known_company = extract_company_name(article.title, article.summary or "")
                        domain, founders, emails = discover_founding_team_emails(
                            company_name=known_company,
                            article_text=article_full_text,
                            article_url=article.link,
                            hunter_api_key=settings.hunter_api_key,
                            http_client=http_client,
                        )
                        bootstrap_extraction = Extraction(
                            article_id=article.id,
                            company=known_company,
                            domain=domain,
                            founders=founders,
                            emails=emails,
                        )
                        db.save_extraction(bootstrap_extraction)
                continue

            # Regular run: store article
            db.insert_article(article)

            if not matches_funding:
                continue

            db.mark_matched(article.id, 1)
            stats.matched += 1

            # Dedup layer 2: fuzzy title similarity against recent 48h
            if is_fuzzy_duplicate(article.title, recent_titles):
                logger.info("Fuzzy duplicate detected for '%s' - skipping alert", article.title)
                db.mark_notified(article.id, 1)
                continue

            # Add to local cache for subsequent entries in same cycle
            if article.title_norm:
                recent_titles.append(article.title_norm)

            # Optional LLM extraction
            extraction = None
            if settings.llm_extraction.enabled:
                extraction = extract_funding_details(article, settings, db=db)

            # Mandatory founding team & email discovery
            if settings.find_founder_emails:
                from fundwatch.email_finder import (
                    discover_founding_team_emails,
                    extract_company_name,
                )

                article_full_text = f"{article.title} {article.summary or ''}"
                resolved_company: str = (
                    extraction.company if extraction and extraction.company else ""
                ) or extract_company_name(article.title, article.summary or "")

                domain, founders, emails = discover_founding_team_emails(
                    company_name=resolved_company,
                    article_text=article_full_text,
                    article_url=article.link,
                    known_domain=extraction.domain if extraction else None,
                    known_founders=extraction.founders if extraction else None,
                    hunter_api_key=settings.hunter_api_key,
                    http_client=http_client,
                )

                if extraction is None:
                    extraction = Extraction(
                        article_id=article.id,
                        company=resolved_company,
                        domain=domain,
                        founders=founders,
                        emails=emails,
                    )
                else:
                    extraction.company = resolved_company
                    extraction.domain = domain
                    extraction.founders = founders
                    extraction.emails = emails

                db.save_extraction(extraction)

            if dry_run:
                msg = format_article_message(article, extraction)
                if print_callback:
                    print_callback(msg)
                else:
                    print(f"\n--- DRY-RUN NOTIFICATION ---\n{msg}\n----------------------------\n")
                stats.notified += 1
            else:
                success = send_notification_to_all(notifiers or [], article, extraction)
                if success:
                    db.mark_notified(article.id, 1)
                    stats.notified += 1

            # Auto-generate personalized job enquiry draft for candidate
            if auto_generate_drafts and not bootstrap_mode and not dry_run:
                try:
                    from fundwatch.outreach import generate_job_enquiry

                    existing_draft = db.get_draft_by_article(article.id)
                    if not existing_draft:
                        cand_profile = db.get_candidate_profile("active")
                        draft = generate_job_enquiry(
                            article=article,
                            extraction=extraction,
                            settings=settings,
                            candidate=cand_profile,
                        )
                        db.create_draft(draft)
                        logger.info(
                            "Auto-generated job enquiry draft %s for %s",
                            draft.id,
                            draft.company,
                        )
                except Exception as draft_err:
                    logger.debug(
                        "Could not auto-generate draft for article %s: %s",
                        article.id,
                        draft_err,
                    )

    logger.info(
        "Cycle finished: fetched=%d, new=%d, matched=%d, notified=%d",
        stats.fetched,
        stats.new,
        stats.matched,
        stats.notified,
    )
    return stats


def auto_generate_missing_drafts(settings: Settings, db: Database, limit: int = 100) -> int:
    """Find matched funding articles that do not have an outbox draft, discover emails, and create job enquiries."""
    from fundwatch.email_finder import discover_founding_team_emails, extract_company_name
    from fundwatch.outreach import generate_job_enquiry

    articles, _ = db.get_articles_paged(limit=limit, matched_only=True)
    existing_drafts = db.list_drafts(limit=2000)
    draft_article_ids = {d.article_id for d in existing_drafts if d.article_id}
    draft_companies = {d.company.strip().lower() for d in existing_drafts if d.company}

    cand_profile = db.get_candidate_profile("active")
    created = 0

    for art_dict in articles:
        art_id = art_dict["id"]
        if art_id in draft_article_ids:
            continue

        raw_company = art_dict.get("company") or extract_company_name(
            art_dict["title"], art_dict.get("summary") or ""
        )
        if raw_company and raw_company.strip().lower() in draft_companies:
            continue

        article = db.get_article(art_id)
        if not article:
            continue

        extraction = db.get_extraction(art_id)
        if extraction is None or not extraction.emails:
            article_full_text = f"{article.title} {article.summary or ''}"
            domain, founders, emails = discover_founding_team_emails(
                company_name=raw_company,
                article_text=article_full_text,
                article_url=article.link,
                known_domain=extraction.domain if extraction else None,
                known_founders=extraction.founders if extraction else None,
                hunter_api_key=settings.hunter_api_key,
            )
            if extraction is None:
                extraction = Extraction(
                    article_id=article.id,
                    company=raw_company,
                    domain=domain,
                    founders=founders,
                    emails=emails,
                )
            else:
                extraction.company = raw_company or extraction.company
                extraction.domain = domain or extraction.domain
                extraction.founders = founders or extraction.founders
                extraction.emails = emails or extraction.emails
            db.save_extraction(extraction)

        draft = generate_job_enquiry(
            article=article,
            extraction=extraction,
            settings=settings,
            candidate=cand_profile,
        )
        db.create_draft(draft)
        draft_article_ids.add(article.id)
        if draft.company:
            draft_companies.add(draft.company.strip().lower())
        created += 1
        logger.info("Auto-generated job enquiry draft %s for %s", draft.id, draft.company)

    return created
