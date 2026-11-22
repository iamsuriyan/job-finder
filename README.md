# 💼 FundWatch — Startup Funding Tracker & Founder Job Outreach Engine

A self-hosted, lightweight platform that monitors RSS/Atom feeds for startup funding announcements, filters noise with intelligent keyword and geographic filtering, automatically discovers founding team email addresses, and generates personalized, high-converting cold job enquiry email drafts for human-in-the-loop review and SMTP dispatch.

Now featuring **Universal Resume Upload & Deterministic Parsing**: anyone can drop in their PDF resume without needing an LLM API key. FundWatch deterministically extracts contact info, portfolio/social links, technical skills, and scores the top 3 cold outreach pitch accomplishments to dynamically populate all outreach emails.

---

## ✨ Core Highlights & Features

### 1. 📄 Universal Resume Upload & Deterministic Pitch Engine
- **Zero-LLM Deterministic Parser**: Powered by `pypdf` and heuristic scoring algorithms. Extracts candidate profile, contact details, links, and technical competencies with 100% deterministic accuracy and zero external API dependencies or costs.
- **Automated Cold Pitch Extraction**: Analyzes resume accomplishment bullets and scores them based on action verbs, scale metrics (`%`, `k`, `$`, latency, volume, user scale), and architecture keywords to select the top 3 high-impact pitch points.
- **Customizable Candidate Profile**: Edit candidate name, title (e.g., *Product Engineer*), email, phone, location, portfolio website, GitHub, and LinkedIn profiles directly in the dashboard.
- **Instant Draft Batch Regeneration**: 1-click regeneration button updates all pending outbox drafts with the active candidate's profile, pitch bullets, links, and resume attachment.
- **Mandatory Resume Attachment Safeguard**: Enforces that a valid resume PDF file exists on disk and is attached before any cold outreach email can be dispatched via SMTP.

### 2. 🔍 Automated Startup & Founding Team Email Discovery
- **Domain Resolution Engine**: Resolves company domains via article link scraping, smart slug & root permutations against live DNS MX checks, and Clearbit Autocomplete.
- **Mail Provider Identification**: Detects Google Workspace, Microsoft 365, Zoho Mail, Proton, and GoDaddy via DNS MX lookups.
- **Multi-Founder Extraction**: Regex heuristics extract human founder names from press releases (*"Founded in 2017 by Prabhat Shrivastava"*, *"Founded in late 2025 by Apoorva Kumar, Manish Atri and Cyril Treacy"*).
- **Pattern Permutations & Role Inboxes**: Generates high-probability founder email patterns (`first@domain`, `first.last@domain`, `firstlast@domain`) alongside executive inboxes (`founders@domain`, `ceo@domain`, `contact@domain`).
- **Instant Port 25 Pre-check**: Caches network port 25 availability to eliminate 30–60s socket timeout delays on cloud or residential networks.
- **Website Scraping & Hunter.io**: Scrapes public contact emails directly from company landing pages and enriches via Hunter.io API if configured.

### 3. ✉️ Human-in-the-Loop Job Enquiry Outreach
> [!IMPORTANT]
> **Strict Human-in-the-Loop Review**: Emails are **never** dispatched automatically upon discovery. They are saved in `status = 'draft'` for human inspection, personalization, and explicit approval before sending. Both a valid resume PDF attachment and proper SMTP credentials are strictly mandatory.

- **Candidate-Aligned Email Drafts**: Tailored cold email templates presenting proven engineering accomplishments taking products from 0 to 1 and scaling backend and infrastructure systems.
- **Context-Aware Salutations**: Personalized greeting using the founder's first name (`Hi Prabhat,`, `Hi Dhruv,`) or company team (`Hi VitusCare Team,`).
- **Inline Resume PDF Preview**: View active resume directly in a browser new tab via native PDF viewer (`Content-Disposition: inline`) without forced download prompts.
- **Configurable SMTP Dispatcher**: Supports custom SMTP hosts, TLS/STARTTLS authentication, custom from-addresses, and live connection test utilities.

### 4. ⚛️ Modern React + Vite Animated SaaS Dashboard
- **Component Architecture**: Built with **React 18 + Vite + TypeScript + Tailwind CSS** with Lucide icons.
- **Linear/Vercel Light-Theme Aesthetic**: Crisp white and zinc surfaces, subtle borders, responsive typography, and consistent card dimensions.
- **Resume Upload Dropzone**: Drag-and-drop PDF upload with instant parsing feedback and live status indicator.
- **Interactive Email Reader & Modal Editor**: Smooth-transitioning modal with **Reader Mode** (pixel-perfect email preview as sent) and **Editor Mode** (live editing of recipient, subject, body, attachment toggle) with human confirmation safeguard before dispatch.
- **Full Card Interaction**: Outbox cards and deals feature clickable surfaces, clean hover states, and smooth modal entry/exit transitions.
- **Live Feed & SMTP Health Monitors**: Real-time RSS inspector with latency measurements and live SMTP handshake tester.

### 5. 🚀 Complete CLI & One-Click Runner Script (`./run.sh`)
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

# Candidate Profile (or upload your resume via the Web UI)
CANDIDATE_NAME="Suriyan Dhanapal"
CANDIDATE_TITLE="Product Engineer"
CANDIDATE_EMAIL="suriyandhanapal@gmail.com"
RESUME_PATH="/home/viper/Downloads/Resumes/2+/Suriyan.pdf"

# SMTP Settings for Outbox Dispatch (Mandatory to send emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com

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

Upload your resume under **My Profile** to automatically parse your accomplishments and synchronize your outreach email templates.

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

## 🌐 REST API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/candidate/profile` | `GET` | Retrieve the active candidate profile details, bullets, and skills. |
| `/api/candidate/profile` | `PUT` | Update candidate fields, contact information, and pitch bullets. |
| `/api/candidate/resume/upload` | `POST` | Upload and deterministically parse a resume PDF file (`multipart/form-data`). |
| `/api/candidate/regenerate-drafts` | `POST` | Batch regenerate pending outbox drafts with the active profile. |
| `/api/outbox/resume/status` | `GET` | Check resume attachment existence, file size, and path metadata. |
| `/api/outbox/resume/download` | `GET` | Preview or download active resume PDF with inline browser support. |
| `/api/articles` | `GET` | List funding deals with search, pagination, and feed filters. |
| `/api/outbox` | `GET` | List email outreach drafts and stats (draft, sent, failed). |
| `/api/outbox/{id}` | `GET` / `PUT` / `DELETE` | Retrieve, update, or remove a specific email draft. |
| `/api/outbox/{id}/send` | `POST` | Dispatch draft via SMTP (requires resume attachment & SMTP configuration). |
| `/api/outbox/smtp/test` | `POST` | Test SMTP server handshake and credentials. |
| `/api/feeds` | `GET` | Check RSS feed sources and health status. |

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
candidate_title: "Product Engineer"
candidate_email: "suriyandhanapal@gmail.com"
resume_path: "/home/viper/Downloads/Resumes/2+/Suriyan.pdf"
find_founder_emails: true
```

---

## 🧪 Testing & Quality Assurance

The codebase maintains strict typing, linting standards, and 100% mocked external network tests:

```bash
# Run all 102 unit and integration tests
pytest tests/

# Strict type checking with Mypy
mypy src tests

# Code style and formatting checks with Ruff
ruff check src tests
ruff format --check src tests

# Compile frontend React TypeScript assets
npm run build --prefix frontend
```

---

## 🔒 Security & Privacy

- **Human Review**: Cold emails are never dispatched automatically. Every draft requires human confirmation.
- **Mandatory Safeguards**: Prevents sending emails without an attached resume PDF or unconfigured SMTP credentials.
- **Credential Safety**: SMTP credentials, API tokens, and bot secrets are loaded strictly from `.env` and environment variables.
- **Local SQLite Storage**: Feed states, extractions, uploaded resumes (`data/resumes/`), and draft copies remain on your local machine (`./data/fundwatch.db`).
