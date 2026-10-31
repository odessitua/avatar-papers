# Proposal

## Why

Work has shifted from talking-head research to two related needs: organizing software development with AI, and building AI-powered product features such as text-to-chart generation, text animation, and screen recording with demo-video generation. This branch still searches, scores, and publishes as an avatar-paper radar, so the weekly Confluence feed matches neither. The collector stays an arXiv radar: blog posts and product docs remain out of scope.

## What Changes

- Replace avatar keyword groups with two topic families in one feed: **development process** (coding agents, spec/review/verification, repository context, human-AI workflow) and **AI product features** (chart and visualization generation, text and motion graphics, screen and demo video, GUI agents). Widen categories to cover both. Start from a fresh corpus (no avatar CSV carried over).
- **BREAKING** Replace the analysis rubric and body. A code router assembles one request from a shared prompt, a short lens for the paper's search group, and both track sections (`process` and `feature`). The model writes exactly one track, chosen by the paper's contribution rather than by the group. Each track has its own four score axes. Keep the machine-read `Recommendation`, `Tags`, `Summary`, and `Code` fields so CSV, Slack, and labels keep working.
- **BREAKING** Publish into a sibling Confluence tree titled `Papers AI Development` under the same parent as the existing `Papers` tree. Child page titles must be unique in the space so year, week, prompt, keywords, and RU pages do not collide with the avatar tree.
- Select a figure per track: workflow or system diagram for process papers, pipeline or representative output for feature papers. Retitle user-facing strings (README, CLI, Slack header, OpenRouter title) for this radar.
- Leave commands, PDF download, figure parsing, code search, EN/RU files, score threshold, and the `avatar-papers` worktree on `main` unchanged.

## Capabilities

### New Capabilities

- `ai-dev-search`: arXiv queries for the process and feature topic families, with a fresh date window and corpus.
- `ai-dev-analysis`: LLM analysis that classifies the track and scores whether a paper helps organize development with AI or build a target product feature.
- `confluence-page-tree`: Confluence hierarchy for this radar, with titles that can sit beside the avatar `Papers` tree in one space.

### Modified Capabilities

- None. `openspec/specs/` has no existing capabilities.

## Impact

- `config.yaml.example` and the local gitignored `config.yaml` in this worktree (keywords, categories, `date_from`, Confluence titles). Secrets stay in `.env`.
- Prompt files under `prompts/` (shared, two tracks, one lens per group) and the router in `src/llm_analyzer.py`. The Confluence prompt page is built from those files.
- Year and week title construction in `src/confluence_publisher.py` and `src/md_to_confluence.py` (topic label, index link labels).
- Slack header text in `src/slack_weekly.py`, CLI description in `main.py`, `README.md`, `USAGE.md`, `scripts/README.md`.
- Confluence space shared with the avatar radar: a duplicate child title fails or would attach to the wrong parent. This worktree's CSV, DB, and `publish_state.json` start empty so avatar rows are not published here.
- The screen-recorder roadmap was not readable (private repository). Feature phrases come from the chart and text-animation docs and the general screen and demo video area. They are config, so they can be tuned after the roadmap is available.
