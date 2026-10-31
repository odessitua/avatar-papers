# Retarget the arXiv radar to AI development and AI features

Point this branch's search, analysis, and Confluence tree at papers about organizing software development with AI and about AI-powered product features.

## TL;DR

The `ai-development` worktree still behaves as the avatar-paper radar. This change gives it one feed with two topic families. For each paper a router assembles a shared prompt, a short lens for the search group, and both track sections. The model writes one track. The year table shows each group as two icons, with a legend above the table. Confluence child titles get an `AI Dev` marker so `Papers AI Development` does not collide with `Papers`. Blogs and product docs stay out of the collector.

Modules touched: `config.yaml` / `config.yaml.example`, `prompts/shared.md`, `prompts/tracks/`, `prompts/groups/`, `src/llm_analyzer.py`, `src/config.py`, `src/confluence_publisher.py`, `src/md_to_confluence.py`, `src/slack_weekly.py`, `main.py`, `README.md`, `USAGE.md`, `scripts/README.md`.

## How to read this change

1. [proposal.md](proposal.md) — why the radar changes subject and what stays an arXiv pipeline.
2. [specs/ai-dev-search/spec.md](specs/ai-dev-search/spec.md) — both topic families, categories, one topic per paper, fresh corpus, arXiv ids only.
3. [specs/ai-dev-analysis/spec.md](specs/ai-dev-analysis/spec.md) — prompt assembly, track classification, scores, sections, figure, Russian identifiers.
4. [specs/confluence-page-tree/spec.md](specs/confluence-page-tree/spec.md) — `Papers AI Development` beside `Papers`, child titles, and the Topic cell.
5. [design.md](design.md) — phrases per group, title marker, prompt template, corpus and backfill.
6. [tasks.md](tasks.md) — implementation and verification steps.

## Design decisions at a glance

| # | Decision | Choice |
| --- | --- | --- |
| 1 | Topics | Eight config groups in two families; process first, broadest last; one global category list |
| 2 | Avoid the avatar tree | `title_marker: AI Dev` on year and week titles; other titles are config fields |
| 3 | Analysis | Router joins `shared`, the group lens, and both tracks; the model writes one track |
| 4 | Corpus | This worktree's gitignored data; backfill by quarter with existing `search` flags |
| 5 | Year table | Topic cell is a family mark plus a group mark; a legend names them |

## Key files to touch

| File | Change |
| --- | --- |
| `config.yaml.example`, `config.yaml` | Eight groups, seven categories, `date_from: 2025-01-01`, Confluence titles and marker. Keep local `space_key` and `parent_page_id`. |
| `prompts/shared.md`, `prompts/tracks/`, `prompts/groups/` | Shared contract, two track bodies, eight lenses. Remove `prompts/analyze_paper.md`. |
| `src/llm_analyzer.py` | Router concatenates those files from the CSV topic. Translation keeps track, fit, and tags. |
| `src/config.py` | `title_marker` property. Blank marker keeps today's titles. |
| `src/confluence_publisher.py`, `src/md_to_confluence.py` | Year and week titles, index link text, Topic cell marks, prompt page from the same concatenation. |
| `src/slack_weekly.py`, `main.py`, `README.md`, `USAGE.md`, `scripts/README.md` | Name `AI Dev Papers` and the new page tree. |

## Verification checklist

- Config lists four process groups before four feature groups, seven categories, `date_from` `2025-01-01`, and `title_marker` `AI Dev`, with no avatar phrases.
- `/home/oleksiik/avatar-papers/config.yaml` is unchanged.
- One process paper and one feature paper analyze with one track body each, and `sync`, tags, and the Slack summary still parse.
- A `coding_agents` row renders ⚙️ and 🤖, and a `chart_generation` row renders 🎯 and 📊. The cell does not contain the group key.
- Marker titles match the spec; a blank marker keeps the old titles.
- Index link text and the Slack header use the new names.
- A current-quarter search returns both families with one row per paper.
- First publish creates `Papers AI Development` beside `Papers` without changing the `Papers` page.

## External references

- Feature domains: `/home/oleksiik/web-local-env/repos/ai-charts/docs/README.md`, `/home/oleksiik/web-local-env/repos/ai-charts/docs/text-animation/README.md`. The screen-recorder roadmap was not readable.
- Sibling worktree on `main`: `/home/oleksiik/avatar-papers`.
- Machine-read fields: `_SCORE_RE`, `_CODE_RE`, `_TAGS_RE` in `src/csv_manager.py`; `_extract_summary` in `src/slack_weekly.py`.
- First-topic-wins search: `seen_ids` in `src/arxiv_search.py`. Space-wide title lookup: `_find_or_create` in `src/confluence_publisher.py`.
