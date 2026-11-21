# Startup Funding Alert Bot: Build Plan

> Instructions for the coding agent: Build the entire application described below, end to end. Work through the phases in order. After each phase, run the tests/verification listed for it before moving on. Do not ask for clarification unless blocked; where this plan says "verify", check it yourself (for example, by fetching a feed URL) and adapt. Keep the code simple, typed, and well-commented.

## 1. Goal

Build a small, self-hosted application that:

1. Polls a configurable list of RSS/Atom feeds (startup and funding news) on a schedule.
2. Detects **new** articles about startups raising funding (keywords such as "raises", "funding", "seed", "Series A/B/C", "pre-Series A").
3. Optionally filters by sector and geography keywords from config.
4. Optionally uses an LLM to extract structured data (company, amount, currency, stage, investors, sector, location).
5. Sends each new matching item as a notification (Telegram first, with pluggable alternatives: Slack webhook, ntfy, email).
6. Never sends the same item twice (persistent dedup).
7. Stores everything in a local SQLite database and can export to CSV.

Non-goals: scraping sites that forbid it, bypassing paywalls or logins, scraping LinkedIn/Wellfound/X, building a web UI (a CLI is enough).

## 2. Tech Stack

- Python 3.11+
- Dependencies: `feedparser`, `httpx`, `pydantic` (v2), `pydantic-settings`, `pyyaml`, `python-dotenv`, `typer` (CLI), `rich` (logging/output), `tenacity` (retries), `rapidfuzz` (fuzzy dedup of the same story across outlets)
- Optional: `anthropic` SDK for LLM extraction (guarded behind a config flag and an env var)
- Dev: `pytest`, `pytest-mock`, `respx` (httpx mocking), `ruff`, `mypy`
- Storage: SQLite via the standard-library `sqlite3`
- Packaging: `pyproject.toml`, run as `python -m fundwatch`
- Container: `Dockerfile` + `docker-compose.yml`
- Scheduling: built-in loop (`fundwatch run`), plus sample cron entry and a GitHub Actions workflow

## 3. Project Structure

```
fundwatch/
├── pyproject.toml
├── README.md
├── .env.example
├── config.yaml
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/poll.yml
├── src/fundwatch/
│   ├── __init__.py
│   ├── __main__.py            # python -m fundwatch -> CLI
│   ├── cli.py                 # typer commands
│   ├── config.py              # load config.yaml + env
│   ├── models.py              # pydantic models
│   ├── db.py                  # sqlite access layer
│   ├── fetcher.py             # feed fetching (conditional GET, retries)
│   ├── filters.py             # keyword/sector/geo matching
│   ├── dedup.py               # id + fuzzy title dedup
│   ├── extractor.py           # optional LLM extraction
│   ├── pipeline.py            # orchestrates one poll cycle
│   ├── scheduler.py           # loop with interval + jitter
│   └── notifiers/
│       ├── __init__.py        # Notifier protocol + factory
│       ├── telegram.py
│       ├── slack.py
│       ├── ntfy.py
│       └── email_smtp.py
└── tests/
    ├── fixtures/              # sample RSS XML files
    ├── test_filters.py
    ├── test_dedup.py
    ├── test_db.py
    ├── test_fetcher.py
    ├── test_pipeline.py
    └── test_notifiers.py
```

## 4. Configuration

### 4.1 `config.yaml` (committed, no secrets)

```yaml
poll_interval_minutes: 20
jitter_seconds: 60
request_timeout_seconds: 15
max_items_per_feed: 50
max_article_age_days: 3          # ignore older entries on first run to avoid a flood
user_agent: "fundwatch/0.1 (personal funding alert bot)"

feeds:
  - name: Entrackr
    url: https://entrackr.com/feed        # verify; fix or remove if invalid
  - name: Inc42
    url: https://inc42.com/feed/          # verify
  - name: YourStory
    url: https://yourstory.com/feed       # verify
  - name: Crunchbase News
    url: https://news.crunchbase.com/feed/  # verify
  - name: TechCrunch Startups
    url: https://techcrunch.com/category/startups/feed/  # verify
  # Add Google Alerts RSS feeds here (create alerts with "Deliver to: RSS feed")

filters:
  # An item must match at least one funding keyword in title (or summary if enabled)
  funding_keywords:
    - raises
    - raised
    - funding
    - seed round
    - pre-seed
    - pre-series a
    - series a
    - series b
    - series c
    - bags
    - secures
    - closes
  match_in_summary: true

  # Optional narrowing. Empty list = no restriction.
  sector_keywords: []        # e.g. [ai, saas, fintech, "agent"]
  geo_keywords: []           # e.g. [india, bengaluru, chennai, coimbatore]
  exclude_keywords:          # drop noise
    - webinar
    - podcast
    - opinion

notifiers:
  - type: telegram
    enabled: true
  - type: slack
    enabled: false
  - type: ntfy
    enabled: false
    topic: my-fundwatch-topic
  - type: email
    enabled: false

llm_extraction:
  enabled: false
  model: "claude-sonnet-5-5"
  max_tokens: 400
```

### 4.2 `.env.example` (secrets only)

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SLACK_WEBHOOK_URL=
NTFY_SERVER=https://ntfy.sh
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_TO=
ANTHROPIC_API_KEY=
DB_PATH=./data/fundwatch.db
LOG_LEVEL=INFO
```

Config loading: `config.py` reads `config.yaml`, validates with pydantic, and overlays env vars. Fail fast with a clear message if an enabled notifier lacks its required secret.

## 5. Data Model

### SQLite schema (`db.py` creates on startup, idempotent)

```sql
CREATE TABLE IF NOT EXISTS articles (
  id            TEXT PRIMARY KEY,      -- feed entry id, else sha256(link)
  feed_name     TEXT NOT NULL,
  title         TEXT NOT NULL,
  link          TEXT NOT NULL,
  summary       TEXT,
  published_at  TEXT,                  -- ISO8601 UTC, nullable
  first_seen_at TEXT NOT NULL,         -- ISO8601 UTC
  matched       INTEGER NOT NULL DEFAULT 0,
  notified      INTEGER NOT NULL DEFAULT 0,
  title_norm    TEXT                   -- normalized title for fuzzy dedup
);

CREATE TABLE IF NOT EXISTS extractions (
  article_id  TEXT PRIMARY KEY REFERENCES articles(id),
  company     TEXT,
  amount      REAL,
  currency    TEXT,
  stage       TEXT,
  investors   TEXT,                    -- JSON array
  sector      TEXT,
  location    TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS feed_state (
  url           TEXT PRIMARY KEY,
  etag          TEXT,
  last_modified TEXT,
  last_ok_at    TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_first_seen ON articles(first_seen_at);
```

### Pydantic models (`models.py`)
- `Feed(name, url)`
- `Article(id, feed_name, title, link, summary, published_at)`
- `Extraction(company, amount, currency, stage, investors, sector, location)`; all optional
- `Settings` (full validated config)

## 6. Module Specs

### 6.1 `fetcher.py`
- Use `httpx` with timeout and the configured User-Agent.
- Send conditional GET headers (`If-None-Match`, `If-Modified-Since`) using the stored `etag`/`last_modified`; handle `304` as "no new data".
- Retry transient errors (timeouts, 5xx) with `tenacity`: 3 attempts, exponential backoff.
- Parse with `feedparser.parse(response.content)`.
- Normalize entries to `Article`: id = `entry.id` or `entry.guid`, else `sha256(link)`; strip HTML from summary; parse the date to UTC.
- One feed failing must never break the cycle. Log the error, increment `consecutive_failures`, and warn via a notifier once when a feed hits 5 consecutive failures.
- Respect `max_items_per_feed`.

### 6.2 `filters.py`
- `is_funding_item(article, cfg) -> bool`:
  - Lowercase title (and summary if `match_in_summary`).
  - Must match at least one `funding_keywords` entry using word-boundary regex.
  - If `sector_keywords` is non-empty, must match at least one.
  - If `geo_keywords` is non-empty, must match at least one.
  - Must match none of `exclude_keywords`.
- Pure functions, fully unit-tested with table-driven tests.

### 6.3 `dedup.py`
- Layer 1: exact, by `articles.id`.
- Layer 2: fuzzy. Normalize the title (lowercase, strip punctuation and outlet suffixes like "- Entrackr"). If `rapidfuzz.fuzz.token_set_ratio` against titles first seen in the last 48 hours is >= 90, treat it as the same story: store it with `notified=1` and skip notifying. This stops the same funding round arriving from five outlets as five alerts.

### 6.4 `extractor.py` (optional, behind `llm_extraction.enabled`)
- Input: title + summary. Output: `Extraction`.
- Prompt the model to return **only JSON** with keys `company, amount, currency, stage, investors, sector, location`; use null when unknown; no guessing.
- Parse defensively (strip code fences, `json.loads`, validate with pydantic). On any failure, return an empty `Extraction` and log. Never block notification on extraction failure.
- Cache results in the `extractions` table; never call the LLM twice for the same article.
- Only run on articles that already passed the keyword filter and dedup (keeps cost near zero).

### 6.5 `notifiers/`
- `Notifier` protocol: `send(article, extraction | None) -> None`, plus `send_text(text)` for system alerts.
- Message format (plain text/Markdown-safe):
  ```
  💰 {company or title}
  {amount currency} · {stage} · {investors}
  {sector} · {location}
  Source: {feed_name} · {published date}
  {link}
  ```
  Omit lines whose fields are unknown. If no extraction is available, send the title, the source, and the link.
- `telegram.py`: POST to `https://api.telegram.org/bot{token}/sendMessage` with `disable_web_page_preview=false`. Escape text correctly for the chosen parse mode, or use plain text.
- `slack.py`: incoming webhook POST.
- `ntfy.py`: POST to `{server}/{topic}` with a `Title` header and a `Click` header set to the article link.
- `email_smtp.py`: `smtplib` with STARTTLS.
- Each notifier retries 3 times on failure. A failure in one notifier must not stop the others. Mark an article `notified=1` only if at least one notifier succeeded.

### 6.6 `pipeline.py` (one poll cycle)
```
for each feed (sequentially, with small delay between):
    articles = fetch(feed)
    for article in articles (oldest first):
        skip if older than max_article_age_days
        skip if id exists in DB
        store article (matched=0)
        if not is_funding_item: continue
        mark matched=1
        if fuzzy duplicate: mark notified=1; continue
        extraction = extract(article) if enabled else None
        send via all enabled notifiers
        mark notified=1 on success
return summary stats (fetched, new, matched, notified, errors)
```

**First-run behaviour:** on an empty DB, run in "bootstrap" mode: store all current items as seen but do NOT notify, so the user doesn't get a flood. Offer `--no-bootstrap` to override.

### 6.7 `scheduler.py`
- `run_forever()`: loop calling the pipeline, sleep `poll_interval_minutes` plus random jitter.
- Handle SIGINT/SIGTERM gracefully (finish the current cycle, then exit).
- Catch and log all exceptions per cycle so the loop never dies.

### 6.8 `cli.py` (typer)
Commands:
- `fundwatch run`: run the loop forever.
- `fundwatch once`: run a single cycle and exit (for cron/GitHub Actions). Flags: `--no-bootstrap`, `--dry-run` (print what would be sent, send nothing).
- `fundwatch check-feeds`: fetch every feed, print status (OK/failed, number of entries, latest title). Used to validate URLs.
- `fundwatch test-notify`: send a test message through every enabled notifier.
- `fundwatch list --limit 20 [--matched-only]`: show recent stored articles.
- `fundwatch export --out funding.csv`: export matched articles joined with extractions.
- `fundwatch stats`: counts per feed, per day.

## 7. Phased Build Order

Complete each phase and run its verification before continuing.

**Phase 1: Skeleton and config**
- Scaffold the repo, `pyproject.toml`, ruff/mypy config, `config.py`, `models.py`.
- Verify: `python -m fundwatch --help` works; config validation errors are readable.

**Phase 2: Storage**
- Implement `db.py` with schema creation and helpers (`has_article`, `insert_article`, `mark_matched`, `mark_notified`, `recent_titles`, feed_state get/set).
- Verify: `pytest tests/test_db.py` passes using a temp-file DB.

**Phase 3: Fetching**
- Implement `fetcher.py` and `check-feeds`. Run it against the real feeds listed in config; for any feed that is invalid, search for the site's correct feed URL or remove it, and record the final working list in `config.yaml`.
- Verify: `fundwatch check-feeds` shows at least 3 working feeds; unit tests use `respx` + fixture XML to cover 200, 304, 500-then-200, and malformed XML.

**Phase 4: Filtering and dedup**
- Implement `filters.py` and `dedup.py` with table-driven tests (at least 20 title examples, including false-positive cases like "funding cuts" or "raises concerns").
- Verify: tests pass.

**Phase 5: Notifiers**
- Implement the notifier interface, Telegram first, then Slack, ntfy, and email. Add `test-notify`.
- Verify: tests with mocked HTTP; `--dry-run` prints correctly formatted messages.

**Phase 6: Pipeline and CLI**
- Implement `pipeline.py` (including bootstrap mode) and the `once`, `run`, `list`, `stats`, `export` commands.
- Verify: an integration test feeds fixture XML through the whole pipeline with a fake notifier. Assert that run 1 (bootstrap) notifies nothing, a modified fixture with one new funding article notifies exactly once, and a re-run notifies nothing.

**Phase 7: LLM extraction (optional module)**
- Implement `extractor.py`, wire it behind the config flag, and add caching.
- Verify: tests with a mocked LLM client cover valid JSON, code-fenced JSON, garbage output (falls back to empty), and cache hit (no second call).

**Phase 8: Packaging and deployment**
- Write the `Dockerfile` (slim Python image, non-root user, volume for `/app/data`), `docker-compose.yml` (restart: unless-stopped, env_file, volume), and `.github/workflows/poll.yml` (cron every 30 minutes running `fundwatch once`; persist the SQLite DB between runs using `actions/cache` or by committing it to a dedicated `state` branch; document the tradeoffs).
- Write `README.md`: setup (creating a Telegram bot via BotFather and getting the chat id), running locally, Docker, cron example, config reference, and troubleshooting.
- Verify: `docker compose build` succeeds; `fundwatch once --dry-run` runs inside the container.

## 8. Quality Requirements

- Type hints everywhere; `mypy --strict` clean on `src/`; `ruff check` and `ruff format` clean.
- Test coverage of at least 80% on `filters`, `dedup`, `db`, `pipeline`, `fetcher`.
- Structured logging with `rich`; log level from env. Never log secrets.
- No hardcoded secrets or tokens anywhere; `.env` in `.gitignore`.
- Polite polling: custom User-Agent, conditional GET, interval of at least 15 minutes (enforce a minimum in config validation), sequential fetching with a 1-2 second delay between feeds. Do not scrape HTML pages; RSS/Atom feeds only.
- All network calls have timeouts. All notifier and feed failures are isolated.

## 9. Acceptance Criteria

The project is done when all of the following are true:

1. `fundwatch check-feeds` reports at least 3 working feeds.
2. `fundwatch once --dry-run` prints formatted alerts for recent funding articles without sending anything.
3. `fundwatch test-notify` delivers a message to the configured Telegram chat.
4. Running `fundwatch once` twice in a row sends no duplicate notifications.
5. The same funding story from two different feeds produces one notification.
6. Killing the network mid-cycle does not crash `fundwatch run`; it recovers on the next cycle.
7. `pytest` passes; `ruff` and `mypy` are clean.
8. `docker compose up -d` starts the bot and it keeps running across restarts without losing seen-article state.
9. The README lets a new user go from clone to first alert in under 15 minutes.

## 10. Future Enhancements (do not build now)

- Weekly digest email summarizing the week's rounds.
- Company-name watchlist and investor watchlist alerts.
- Cross-check careers pages for open roles at newly funded companies.
- Simple web dashboard over the SQLite DB.
- Additional sources: SEC Form D (US), government/MCA filing feeds, and VC firm blog feeds.
