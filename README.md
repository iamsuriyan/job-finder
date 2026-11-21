# 💰 fundwatch - Startup Funding Alert Bot

A lightweight, self-hosted application that polls RSS/Atom news feeds for startup funding announcements, filters noise with intelligent keyword and geographic filtering, eliminates duplicate coverage across outlets with fuzzy matching, and sends instant alerts via Telegram, Slack, ntfy, or Email.

---

## ✨ Features

- **RSS/Atom Feed Polling**: Polite, conditional HTTP GET (`ETag` / `If-Modified-Since`) with exponential backoff retries.
- **Funding Detection**: Accurate regex-based word-boundary filtering on titles and summaries (detects "raises", "funding", "seed round", "Series A/B/C", "bags", "secures", "closes", etc.).
- **False-Positive Guard**: Filters out non-funding news such as "funding cuts", "raises concerns", "raises questions", "webinar", "podcast", and "opinion".
- **Cross-Outlet Deduplication**:
  - *Layer 1*: Persistent unique article IDs in SQLite.
  - *Layer 2*: Fuzzy title matching via `rapidfuzz` (`token_set_ratio >= 90`) against articles seen in the past 48 hours. The same funding round reported by TechCrunch, Inc42, and Entrackr results in exactly **one** alert.
- **Bootstrap Mode**: On an empty database, indexes current feed items without flooding your channels with old alerts.
- **Pluggable Notifications**:
  - **Telegram** (Direct Bot API)
  - **Slack** (Incoming Webhooks)
  - **ntfy** (Self-hosted or https://ntfy.sh)
  - **Email** (SMTP with STARTTLS)
- **Optional LLM Extraction**: Extract structured fields (`company`, `amount`, `currency`, `stage`, `investors`, `sector`, `location`) using Claude Sonnet with local DB caching.
- **Built-in CLI**: Easily check feed health, preview alerts in dry-run mode, test notifiers, list stored articles, inspect stats, and export to CSV.
- **Self-Host Anywhere**: Run with Docker, Docker Compose, systemd, crontab, or GitHub Actions.

---

## 🚀 Quick Start (Under 10 Minutes)

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-username/fundwatch.git
cd fundwatch

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure Telegram (Recommended)

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the instructions to create your bot. Copy the **HTTP API token**.
3. Send a message to your new bot in Telegram.
4. Obtain your numeric Chat ID:
   - Message [@userinfobot](https://t.me/userinfobot) to get your ID, or
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and look for `"chat":{"id":123456789}`.
5. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```
6. Fill in your secrets in `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz
   TELEGRAM_CHAT_ID=123456789
   DB_PATH=./data/fundwatch.db
   LOG_LEVEL=INFO
   ```

### 3. Test Everything

```bash
# Verify feed sources are online and responsive
fundwatch check-feeds

# Send a test alert to your Telegram chat
fundwatch test-notify

# Preview formatted funding alerts without sending anything
fundwatch once --dry-run
```

### 4. Run the Daemon

```bash
fundwatch run
```

---

## 🛠️ Configuration (`config.yaml`)

```yaml
poll_interval_minutes: 20       # Minimum: 15 minutes
jitter_seconds: 60              # Random jitter added/subtracted to sleep
request_timeout_seconds: 15     # HTTP timeout in seconds
max_items_per_feed: 50          # Max entries processed per feed
max_article_age_days: 3         # Drop articles older than 3 days
user_agent: "fundwatch/0.1 (personal funding alert bot)"

feeds:
  - name: Entrackr
    url: https://entrackr.com/rss
  - name: Inc42
    url: https://inc42.com/feed/
  - name: YourStory
    url: https://yourstory.com/feed
  - name: Crunchbase News
    url: https://news.crunchbase.com/feed/
  - name: TechCrunch Startups
    url: https://techcrunch.com/category/startups/feed/

filters:
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
  sector_keywords: []          # Optional: e.g. [ai, fintech, robotics]
  geo_keywords: []             # Optional: e.g. [india, bengaluru]
  exclude_keywords:
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
    topic: my-fundwatch-alerts
  - type: email
    enabled: false

llm_extraction:
  enabled: false
  model: "claude-sonnet-5-5"
  max_tokens: 400
```

---

## 💻 CLI Commands

| Command | Description |
|---|---|
| `fundwatch ui` | Launches the clean monochrome web dashboard at `http://127.0.0.1:8000`. |
| `fundwatch run` | Runs continuous monitoring loop with configured interval & jitter. |
| `fundwatch once` | Runs a single poll cycle and exits (ideal for cron / CI). Supports `--dry-run` and `--no-bootstrap`. |
| `fundwatch check-feeds` | Tests all configured feed URLs, validates HTTP status and latest entry. |
| `fundwatch test-notify` | Sends a verification alert through all enabled notifiers. |
| `fundwatch list` | Displays stored articles table (`--limit 20`, `--matched-only`). |
| `fundwatch stats` | Shows article counts per feed and daily volumes. |
| `fundwatch export --out funding.csv` | Exports matched funding rounds joined with LLM extractions to CSV. |

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. Populate `.env` with your secrets.
2. Build and start the container in the background:
   ```bash
   docker compose up -d
   ```
3. View logs:
   ```bash
   docker compose logs -f
   ```

### Manual Docker Build

```bash
docker build -t fundwatch:latest .
docker run -d \
  --name fundwatch \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  fundwatch:latest
```

---

## ⏰ Cron & GitHub Actions Scheduling

### System Cron Example

To run every 30 minutes:
```crontab
*/30 * * * * cd /home/user/fundwatch && /home/user/fundwatch/.venv/bin/fundwatch once >> /var/log/fundwatch.log 2>&1
```

### GitHub Actions Workflow

A preconfigured workflow is included in `.github/workflows/poll.yml`. Add your secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, etc.) to **Settings > Secrets and variables > Actions**.

> **Note on State Persistence in GitHub Actions:**
> The included workflow caches `data/fundwatch.db` with `actions/cache`. GitHub Actions caches are purged after 7 days of inactivity. If you need 100% durable persistence without a server, store the SQLite database in an S3 bucket or commit it to a dedicated `state` branch.

---

## 🧪 Running Tests

```bash
# Run pytest with 100% mocked network calls
pytest

# Code style and formatting checks
ruff check .
ruff format --check .

# Strict type checking
mypy src tests
```

---

## ❓ Troubleshooting

- **Telegram 400 / 401 Unauthorized**: Ensure `TELEGRAM_BOT_TOKEN` does not contain leading/trailing spaces and that `TELEGRAM_CHAT_ID` is your numeric ID.
- **Feed 404 / 403 Forbidden**: Run `fundwatch check-feeds` to pinpoint failing URLs. Verify that the publisher has not changed their RSS path or blocked generic user agents (adjust `user_agent` in `config.yaml` if needed).
- **No Alerts Sent on First Run**: By design, `fundwatch` runs in **bootstrap mode** when initialized with an empty database to prevent spamming notifications for old articles. To force alerts on run 1, pass `--no-bootstrap`.
