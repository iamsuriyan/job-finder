# 💼 FundWatch — AI-Powered Startup Funding Tracker & Founder Job Outreach Engine

A self-hosted, lightweight platform that monitors RSS/Atom feeds for startup funding announcements, filters noise with intelligent keyword and geographic filtering, automatically discovers founding team email addresses, and generates personalized, high-converting cold job enquiry email drafts for human-in-the-loop review and SMTP dispatch.

---

## ✨ Core Highlights & Features

### 1. 🔍 Automated Startup & Founding Team Email Discovery
- **Domain Resolution Engine**: Resolves company domains via article link scraping, smart slug & root permutation against live DNS MX checks, and Clearbit Autocomplete.
- **Mail Provider Identification**: Detects Google Workspace, Microsoft 365, Zoho Mail, Proton, and GoDaddy via DNS MX lookups.
- **Multi-Founder Extraction**: Regex heuristics extract human founder names from complex press releases (*"Founded in 2017 by Prabhat Shrivastava"*, *"Founded in late 2025 by Apoorva Kumar, Manish Atri and Cyril Treacy"*).
- **Pattern Permutations & Role Inboxes**: Generates high-probability founder email patterns (`first@domain`, `first.last@domain`, `firstlast@domain`) alongside executive inboxes (`founders@domain`, `ceo@domain`, `contact@domain`).
- **Instant Port 25 Pre-check**: Caches network port 25 availability to eliminate 30–60s socket timeout delays on cloud or residential networks.
- **Website Scraping & Hunter.io**: Scrapes public contact emails directly from company landing pages and enriches via Hunter.io API if configured.

### 2. ✉️ Human-in-the-Loop Job Enquiry Outreach
> [!IMPORTANT]
> **Strict Human-in-the-Loop Review**: Emails are **never** dispatched automatically upon discovery. They are saved in `status = 'draft'` for human inspection, personalization, and explicit approval before sending.

- **Candidate-Aligned Email Drafts**: Tailored cold email templates presenting actual engineering experience (2+ years Generative AI & Product Engineering at IIT Bombay-incubated Cooper Compass and Mindgryd).
- **Context-Aware Salutations**: Personalized greeting using the founder's first name (`Hi Prabhat,`, `Hi Dhruv,`) or company team (`Hi VitusCare Team,`).
- **Resume Attachment**: Automatically attaches candidate resume PDF (`Suriyan.pdf`) with live file verification, metadata inspection, and preview downloads.
- **Configurable SMTP Dispatcher**: Supports custom SMTP hosts, TLS/STARTTLS authentication, custom from-addresses, and live connection test utilities.

### 3. ⚛️ Modern React + Vite Animated SaaS Dashboard
- **Component Architecture**: Built with **React 18 + Vite + TypeScript + Tailwind CSS** with Lucide icons.
- **Animated Collapsible Sidebar**: Left-docked animated navigation with sliding active pills, collapse/expand toggles (288px wide <-> 80px compact), live pulse indicator, and attached resume badge.
- **Pure Light-Theme SaaS Aesthetic**: Designed with crisp white, slate/zinc surfaces, subtle shadows, and zero eye-strain.
- **Interactive Email Reader & Modal Editor**: Full modal with dual **Reader Mode** (pixel-perfect email preview as sent) and **Editor Mode** (live editing of recipient, subject, body, attachment toggle) with human confirmation safeguard before dispatch.
- **Live Deal Cards**: Deal stream with domain pills, extracted deal terms, and 1-click clipboard copy for founder emails.
- **Live Feed & SMTP Health Monitors**: Real-time RSS inspector with latency measurements and live SMTP handshake tester.

### 4. 🚀 Complete CLI & One-Click Runner Script (`./run.sh`)
- Executable bash launcher (`./run.sh`) for starting the UI, running poll cycles, continuous monitoring, outbox inspection, and test execution.
- Dedicated `fundwatch outbox` CLI commands to manage and review drafts straight from the terminal.

---

## ⚡ Quick Start

### 1. Clone & Set Up Environment

```bash
git clone git@github.com:iamsuriyan/job-finder.git
cd job-finder

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure Environment (`.env`)

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```ini
DB_PATH=./data/fundwatch.db
LOG_LEVEL=INFO

# Candidate Profile
CANDIDATE_NAME="Suriyan Dhanapal"
CANDIDATE_TITLE="Generative AI & Product Engineer"
CANDIDATE_EMAIL="suriyandhanapal@gmail.com"
RESUME_PATH="/home/viper/Downloads/Resumes/2+/Suriyan.pdf"

# SMTP Settings for Outbox Dispatch (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=suriyandhanapal@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=suriyandhanapal@gmail.com

# Optional Alerts & Enrichment
FIND_FOUNDER_EMAILS=true
HUNTER_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### 3. Launch Web Dashboard

Run using the launcher script:
```bash
./run.sh ui
```
Or with the CLI:
```bash
fundwatch ui --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 💻 Running with `./run.sh`

The `./run.sh` script automates common workflows:

```bash
./run.sh ui        # Start the clean light-theme dashboard on http://localhost:8000
./run.sh poll      # Fetch latest funding rounds from all feeds and discover emails
./run.sh monitor   # Run continuous background monitoring loop
./run.sh outbox    # Review and list generated cold email drafts in terminal
./run.sh test      # Run full unit and integration test suite (pytest)
./run.sh help      # Display command help
```

---

## ⌨️ CLI Command Reference

### Outbox & Outreach Commands

| Command | Description |
|---|---|
| `fundwatch outbox list` | List all pending, sent, and failed email drafts. |
| `fundwatch outbox show <draft_id>` | Inspect draft subject, recipient email, attachment status, and body. |
| `fundwatch outbox generate <article_id>` | Generate a personalized job enquiry draft for a funded startup. |
| `fundwatch outbox send <draft_id>` | Send an email draft via SMTP (prompts for human confirmation, or pass `--yes`). |
| `fundwatch outbox resume` | Check attached resume PDF existence, size, and metadata. |

### Monitoring & Feed Commands

| Command | Description |
|---|---|
| `fundwatch ui` | Launches the web dashboard at `http://localhost:8000`. |
| `fundwatch run` | Continuous monitoring loop with configured polling interval & jitter. |
| `fundwatch once` | Single poll cycle and exit (`--dry-run` to preview without notifying). |
| `fundwatch check-feeds` | Test all configured RSS feeds for HTTP health and latency. |
| `fundwatch stats` | Display article volumes and feed statistics. |
| `fundwatch export --out deals.csv` | Export verified funding rounds and founder metadata to CSV. |

---

## ⚙️ Configuration Reference (`config.yaml`)

```yaml
poll_interval_minutes: 20
jitter_seconds: 60
request_timeout_seconds: 15
max_items_per_feed: 50
max_article_age_days: 7
user_agent: "fundwatch/0.1 (personal startup tracker)"

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
    - series a
    - series b
    - series c
    - bags
    - secures
    - closes
  match_in_summary: true
  exclude_keywords:
    - webinar
    - podcast
    - opinion

candidate_name: "Suriyan Dhanapal"
candidate_title: "Generative AI & Product Engineer"
candidate_email: "suriyandhanapal@gmail.com"
resume_path: "/home/viper/Downloads/Resumes/2+/Suriyan.pdf"
find_founder_emails: true
```

---

## 🧪 Testing & Quality Assurance

The codebase maintains strict typing and 100% mocked external network tests:

```bash
# Run 92 unit and integration tests
pytest tests/

# Strict type checking with Mypy
mypy src tests

# Code style and formatting checks with Ruff
ruff check src tests
ruff format --check src tests
```

---

## 🔒 Security & Privacy

- **Human Review**: Cold emails are never dispatched automatically. Every draft requires human confirmation.
- **Credential Safety**: SMTP credentials, API tokens, and bot secrets are loaded strictly from `.env` and environment variables.
- **Local SQLite Storage**: Feed states, extractions, and draft copies remain on your local machine (`./data/fundwatch.db`).
