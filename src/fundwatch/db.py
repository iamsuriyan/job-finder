"""SQLite database storage layer for fundwatch."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fundwatch.models import Article, Extraction

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
  id            TEXT PRIMARY KEY,
  feed_name     TEXT NOT NULL,
  title         TEXT NOT NULL,
  link          TEXT NOT NULL,
  summary       TEXT,
  published_at  TEXT,
  first_seen_at TEXT NOT NULL,
  matched       INTEGER NOT NULL DEFAULT 0,
  notified      INTEGER NOT NULL DEFAULT 0,
  title_norm    TEXT
);

CREATE TABLE IF NOT EXISTS extractions (
  article_id  TEXT PRIMARY KEY REFERENCES articles(id),
  company     TEXT,
  amount      REAL,
  currency    TEXT,
  stage       TEXT,
  investors   TEXT,
  sector      TEXT,
  location    TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS feed_state (
  url                  TEXT PRIMARY KEY,
  etag                 TEXT,
  last_modified        TEXT,
  last_ok_at           TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_first_seen ON articles(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_articles_matched ON articles(matched);
"""


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


class Database:
    """SQLite database client with helpers for articles, feed state, and extractions."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a transactional database connection with Row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize SQLite tables and indexes."""
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)

    def is_empty(self) -> bool:
        """Check if articles table is empty (used for first-run bootstrap detection)."""
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM articles").fetchone()
            return bool(row["cnt"] == 0) if row else True

    def has_article(self, article_id: str) -> bool:
        """Check whether an article id already exists."""
        with self.connection() as conn:
            row = conn.execute("SELECT 1 FROM articles WHERE id = ?", (article_id,)).fetchone()
            return row is not None

    def insert_article(self, article: Article) -> bool:
        """Insert a new article. Returns True if inserted, False if already exists."""
        first_seen = article.first_seen_at or utc_now_iso()
        with self.connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO articles (
                        id, feed_name, title, link, summary, published_at,
                        first_seen_at, matched, notified, title_norm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article.id,
                        article.feed_name,
                        article.title,
                        article.link,
                        article.summary,
                        article.published_at,
                        first_seen,
                        article.matched,
                        article.notified,
                        article.title_norm,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def mark_matched(self, article_id: str, matched: int = 1) -> None:
        """Update article matched status."""
        with self.connection() as conn:
            conn.execute(
                "UPDATE articles SET matched = ? WHERE id = ?",
                (matched, article_id),
            )

    def mark_notified(self, article_id: str, notified: int = 1) -> None:
        """Update article notified status."""
        with self.connection() as conn:
            conn.execute(
                "UPDATE articles SET notified = ? WHERE id = ?",
                (notified, article_id),
            )

    def get_article(self, article_id: str) -> Article | None:
        """Retrieve an article by id."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            if not row:
                return None
            return Article(
                id=row["id"],
                feed_name=row["feed_name"],
                title=row["title"],
                link=row["link"],
                summary=row["summary"],
                published_at=row["published_at"],
                first_seen_at=row["first_seen_at"],
                matched=row["matched"],
                notified=row["notified"],
                title_norm=row["title_norm"],
            )

    def recent_titles(self, hours: int = 48) -> list[str]:
        """Return list of normalized titles (or titles) seen within the last N hours."""
        with self.connection() as conn:
            # SQLite datetime comparison using modifier
            modifier = f"-{hours} hours"
            rows = conn.execute(
                """
                SELECT COALESCE(title_norm, title) AS t
                FROM articles
                WHERE first_seen_at >= datetime('now', ?)
                """,
                (modifier,),
            ).fetchall()
            return [str(row["t"]) for row in rows if row["t"]]

    def get_feed_state(self, url: str) -> dict[str, Any] | None:
        """Get cached HTTP caching metadata and failure count for a feed URL."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM feed_state WHERE url = ?", (url,)).fetchone()
            if not row:
                return None
            return dict(row)

    def record_feed_success(self, url: str, etag: str | None, last_modified: str | None) -> None:
        """Record successful fetch: resets consecutive_failures, updates last_ok_at."""
        now = utc_now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO feed_state (url, etag, last_modified, last_ok_at, consecutive_failures)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(url) DO UPDATE SET
                    etag = COALESCE(excluded.etag, feed_state.etag),
                    last_modified = COALESCE(excluded.last_modified, feed_state.last_modified),
                    last_ok_at = excluded.last_ok_at,
                    consecutive_failures = 0
                """,
                (url, etag, last_modified, now),
            )

    def record_feed_failure(self, url: str) -> int:
        """Record failed fetch: increments consecutive_failures. Returns new failure count."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO feed_state (url, consecutive_failures)
                VALUES (?, 1)
                ON CONFLICT(url) DO UPDATE SET
                    consecutive_failures = feed_state.consecutive_failures + 1
                """,
                (url,),
            )
            row = conn.execute(
                "SELECT consecutive_failures FROM feed_state WHERE url = ?",
                (url,),
            ).fetchone()
            return int(row["consecutive_failures"]) if row else 1

    def save_extraction(self, extraction: Extraction) -> None:
        """Save or update structured extraction for an article."""
        if not extraction.article_id:
            raise ValueError("Extraction article_id cannot be None")

        investors_json = (
            json.dumps(extraction.investors) if extraction.investors is not None else None
        )
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO extractions (
                    article_id, company, amount, currency, stage,
                    investors, sector, location, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    company = excluded.company,
                    amount = excluded.amount,
                    currency = excluded.currency,
                    stage = excluded.stage,
                    investors = excluded.investors,
                    sector = excluded.sector,
                    location = excluded.location,
                    raw_json = excluded.raw_json
                """,
                (
                    extraction.article_id,
                    extraction.company,
                    extraction.amount,
                    extraction.currency,
                    extraction.stage,
                    investors_json,
                    extraction.sector,
                    extraction.location,
                    extraction.raw_json,
                ),
            )

    def get_extraction(self, article_id: str) -> Extraction | None:
        """Retrieve extraction details for an article."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM extractions WHERE article_id = ?", (article_id,)
            ).fetchone()
            if not row:
                return None
            investors = json.loads(row["investors"]) if row["investors"] else None
            return Extraction(
                article_id=row["article_id"],
                company=row["company"],
                amount=row["amount"],
                currency=row["currency"],
                stage=row["stage"],
                investors=investors,
                sector=row["sector"],
                location=row["location"],
                raw_json=row["raw_json"],
            )

    def get_recent_articles(self, limit: int = 20, matched_only: bool = False) -> list[Article]:
        """Fetch recent articles ordered by first_seen_at DESC."""
        query = "SELECT * FROM articles"
        params: list[Any] = []
        if matched_only:
            query += " WHERE matched = 1"
        query += " ORDER BY first_seen_at DESC LIMIT ?"
        params.append(limit)

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Article(
                    id=r["id"],
                    feed_name=r["feed_name"],
                    title=r["title"],
                    link=r["link"],
                    summary=r["summary"],
                    published_at=r["published_at"],
                    first_seen_at=r["first_seen_at"],
                    matched=r["matched"],
                    notified=r["notified"],
                    title_norm=r["title_norm"],
                )
                for r in rows
            ]

    def get_matched_articles_with_extractions(self) -> list[dict[str, Any]]:
        """Fetch all matched articles joined with extractions for export."""
        query = """
        SELECT
            a.id,
            a.feed_name,
            a.title,
            a.link,
            a.published_at,
            a.first_seen_at,
            a.notified,
            e.company,
            e.amount,
            e.currency,
            e.stage,
            e.investors,
            e.sector,
            e.location
        FROM articles a
        LEFT JOIN extractions e ON a.id = e.article_id
        WHERE a.matched = 1
        ORDER BY a.first_seen_at DESC
        """
        with self.connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        """Fetch summary statistics: totals, per-feed counts, per-day counts."""
        with self.connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) AS matched,
                    SUM(CASE WHEN notified = 1 THEN 1 ELSE 0 END) AS notified
                FROM articles
                """
            ).fetchone()

            feed_counts = conn.execute(
                """
                SELECT feed_name, COUNT(*) AS count
                FROM articles
                GROUP BY feed_name
                ORDER BY count DESC
                """
            ).fetchall()

            daily_counts = conn.execute(
                """
                SELECT substr(first_seen_at, 1, 10) AS day, COUNT(*) AS count
                FROM articles
                GROUP BY day
                ORDER BY day DESC
                LIMIT 14
                """
            ).fetchall()

            return {
                "total": totals["total"] if totals else 0,
                "matched": totals["matched"] if totals and totals["matched"] else 0,
                "notified": totals["notified"] if totals and totals["notified"] else 0,
                "by_feed": [dict(r) for r in feed_counts],
                "by_day": [dict(r) for r in daily_counts],
            }
