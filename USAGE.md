# AI Dev Papers — Usage Guide

## Prerequisites

1. Python environment with dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. `.env` file in the project root with Confluence credentials (and optionally Slack):
   ```
   CONFLUENCE_URL=https://your-instance.atlassian.net/wiki
   CONFLUENCE_EMAIL=your@email.com
   CONFLUENCE_TOKEN=your_api_token
   # Optional: for weekly reports to Slack (use one of the two)
   # Option A — Incoming Webhook (needs channel admin to add it):
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   # Option B — Slack App Bot (if you only have "View" in channel integrations):
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL=#your-channel
   ```

3. `config.yaml` — copy from `config.yaml.example`. Default search covers two families from `2025-01-01`: development process (`coding_agents`, `spec_review_verify`, `repo_context`, `human_ai_workflow`) and product features (`chart_generation`, `text_motion`, `screen_video`, `gui_agents`). Categories are `cs.SE`, `cs.AI`, `cs.CL`, `cs.HC`, `cs.GR`, `cs.CV`, and `cs.MM`. Set Confluence `space_key` and `parent_page_id`.

---

## Commands

### `update` — Daily cron job (search + download + publish)

Automatically detects the date range (from latest paper in CSV minus 3 days
to today), searches for new papers, downloads PDFs, and publishes updated
tables to Confluence.

```bash
python main.py update
```

Best used as a daily cron job (see `scripts/daily_update.sh`):
```
0 22 * * * /path/to/ai-dev-papers/scripts/daily_update.sh
```

---

### `search` — Search arXiv for papers

Searches arXiv using the eight keyword groups in `config.yaml` and adds new papers to `data/papers.csv`. Process groups are queried before feature groups. A paper that matches more than one group is stored once, under the first group. Uses `date_from` / `date_to` from config unless overridden. The default window starts on 2025-01-01.

Each run returns at most `max_results_per_topic` papers per group (200). Backfill older quarters with `--date-from` and `--date-to`, newest quarter first, instead of raising that limit.

```bash
# Use dates from config.yaml
python main.py search

# Override date range
python main.py search --date-from 2025-01-01 --date-to 2025-03-31
```

Duplicates are automatically skipped. Safe to run multiple times.

---

### `download` — Download PDFs

Downloads PDFs for all papers in the CSV that haven't been downloaded yet.
Files are saved to `papers/originals/{arxiv_id}.pdf`.

```bash
python main.py download
```

- 3-second delay between requests (configurable in `config.yaml`)
- Can be interrupted and resumed — already downloaded files are skipped
- ~10 minutes for 200 papers

---

### `sync` — Sync analysis status

Scans the `papers/analysis/` directory for completed analysis files and
updates `processed` and `score` fields in the CSV.

```bash
python main.py sync
```

Run this after completing paper analyses to update the CSV before publishing.

---

### `publish` — Publish to Confluence

Publishes the papers table and weekly analysis pages to Confluence.
Organized by year: Papers → 2026 → weekly pages.

```bash
# Normal publish (skips unchanged content)
python main.py publish

# Force re-publish everything (ignore locks and hashes)
python main.py publish --force
```

**Smart caching:**
- Weekly pages with all papers analyzed are **locked** — never re-published
- Year tables are only updated when content changes (hash-based)
- State is tracked in `data/publish_state.json`
- Use `--force` to bypass all caching

---

### `slack-weekly` — Send weekly report to Slack

Builds a report for a given week (papers from CSV + Summary from analysis files)
and posts it to a Slack channel.

**Setup (choose one):**

- **Option A — Incoming Webhook:** Channel → Integrations → Add apps → Incoming Webhooks → Add to Slack. (If you only see "View" and no "Add", you don’t have permission; use Option B.)
- **Option B — Slack App Bot:** Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch. Add a **Bot** (OAuth & Permissions → Bot Token Scopes → `chat:write`), then **Install to Workspace**. In your channel, run `/invite @YourBotName`. In `.env` set `SLACK_BOT_TOKEN=xoxb-...` (from OAuth & Permissions) and `SLACK_CHANNEL=#channel-name` (or channel ID).

```bash
# Report for last week (Mon–Sun), only papers with score ≥ 7 (default)
python main.py slack-weekly --week last

# Report for current week
python main.py slack-weekly --week current

# Include papers with score ≥ 6
python main.py slack-weekly --week last --min-score 6
```

**Message format in Slack:** A header with the week range (e.g. "Papers: 2026-03-09 — 2026-03-15"), a line like "N papers (score ≥ 7)", then for each paper: clickable title (link to arXiv), score badge, and the Summary paragraph from the analysis.

Run once per week via cron (see `scripts/weekly_slack.sh`):
```
0 9 * * 4 /path/to/ai-dev-papers/scripts/weekly_slack.sh
```

---

### `collect` — Search + download (no publish)

Convenience command that runs `search` followed by `download`.

```bash
python main.py collect
python main.py collect --date-from 2025-07-01 --date-to 2025-09-30
```

---

## Typical Workflows

### Initial backfill (historical data)

```bash
# Search by quarter, newest first, from the current quarter back to 2025-01-01
python main.py search --date-from 2026-10-01 --date-to 2026-12-31
python main.py search --date-from 2026-07-01 --date-to 2026-09-30
python main.py search --date-from 2026-04-01 --date-to 2026-06-30
python main.py search --date-from 2026-01-01 --date-to 2026-03-31
python main.py search --date-from 2025-10-01 --date-to 2025-12-31
python main.py search --date-from 2025-07-01 --date-to 2025-09-30
python main.py search --date-from 2025-04-01 --date-to 2025-06-30
python main.py search --date-from 2025-01-01 --date-to 2025-03-31

# Download all PDFs
python main.py download

# Publish tables to Confluence
python main.py publish
```

### Daily operation (cron)

```
0 22 * * * /path/to/ai-dev-papers/scripts/daily_update.sh
0 9 * * 4 /path/to/ai-dev-papers/scripts/weekly_slack.sh
```

### After analyzing papers

```bash
# 1. Analyze with `python main.py analyze` (prompts/shared.md plus the group lens and both tracks)
#    Save EN analysis to papers/analysis/{arxiv_id}.md
#    Save RU translation to papers/analysis_ru/{arxiv_id}.md

# 2. Sync analysis status to CSV
python main.py sync

# 3. Publish updated weekly pages and tables
python main.py publish
```

---

## Confluence Page Structure

```
Papers AI Development
├── Analysis Prompt · AI Dev
├── Search Keywords · AI Dev
├── 2026 · AI Dev
│   ├── AI Dev: Feb 16 - Feb 22, 2026
│   └── AI Dev: Feb 16 - Feb 22, 2026 (RU)
└── RU · AI Dev
    └── 2026 · AI Dev (RU)
```

The year table Topic cell is two icons: a family mark and the group mark. A legend above the table is two lists. ⚙️ process is how software is built with AI. 🎯 feature is a product capability. Each list names the group marks under that family. Hovering a cell shows the short group name.

---

## Global Options

| Flag | Description |
|------|-------------|
| `--config FILE` | Path to config file (default: `config.yaml`) |
| `--date-from YYYY-MM-DD` | Override search start date |
| `--date-to YYYY-MM-DD` | Override search end date |
| `--force` | Force re-publish (publish command only) |
| `--week` | Week for `slack-weekly`: `last` or `current` (default: last) |
| `--min-score` | Min score for `slack-weekly` (default: 7) |
