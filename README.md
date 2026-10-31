# AI Dev Papers

Collect arXiv papers by keywords, store metadata in CSV, optional analysis markdown, publish to Confluence.

## Quick start

1. `pip install -r requirements.txt`
2. Copy `config.yaml.example` to `config.yaml` and set `confluence.space_key`, `confluence.parent_page_id`, and `arxiv.date_from` (use today's date for newest submissions).
3. Copy `.env.example` to `.env` and set Confluence URL, email, and API token.
4. See [USAGE.md](USAGE.md) for commands (`update`, `search`, `download`, `sync`, `publish`, …).

## Search

Two families, eight groups, from `2025-01-01`:

- Process: `coding_agents`, `spec_review_verify`, `repo_context`, `human_ai_workflow`
- Features: `chart_generation`, `text_motion`, `screen_video`, `gui_agents`

Categories: `cs.SE`, `cs.AI`, `cs.CL`, `cs.HC`, `cs.GR`, `cs.CV`, `cs.MM`. One search returns at most 200 papers per group, so backfill by quarter with `search --date-from` and `--date-to`.

## Configuration

- **Secrets** (tokens): `.env` — not committed.
- **Non-secrets** (keywords, paths, Confluence page IDs): `config.yaml` — not committed; use `config.yaml.example` as a template.

## License

See project owner for license terms.
