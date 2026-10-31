# Design

## Context

See proposal.md for why this branch changes subject. The collector is one Python CLI. Search phrases, one global category list, and dates come from `config.yaml`. `_build_query` in `src/arxiv_search.py` ORs one group's quoted phrases on `abs`, ANDs the categories and `submittedDate`, and stops after `max_results_per_topic` (200) newest results per group. A paper keeps the topic of the first group that returned it (`seen_ids`).

Analysis instructions live in `prompts/analyze_paper.md`. `build_analysis_messages` and `build_translation_messages` in `src/llm_analyzer.py` wrap that file and repeat figure and naming rules that still describe neural-net papers. Downstream code reads four fields from each English file: the score heading (`_SCORE_RE`), the `- **Code:** url` line (`_CODE_RE`), the `## Tags` paragraph that must follow the heading after one blank line (`_TAGS_RE`), and the `## Summary` paragraph up to the next heading or `---` (`_extract_summary` in Slack). The weekly Confluence page renders the whole file.

Confluence root, RU, prompt, and keywords titles are config fields. Year titles are the bare year, and week titles come from `format_weekly_title`. `_find_or_create` looks up titles across the whole space. Confluence treats a title as unique per space, so a second `2026` or `Feb 16 - Feb 22, 2026` fails. This directory is a git worktree of `avatar-papers` on branch `ai-development`. `config.yaml`, the CSV, and the DB are gitignored per worktree. There is no test suite.

## Goals / Non-Goals

**Goals:**

- One feed with two topic families, driven by config.
- One assembled request per paper: shared instructions, the group's lens, and both tracks. The model writes one track. The four machine-read fields stay unchanged.
- The year-table Topic cell shows a family mark and a group mark. A legend above the table names them.
- Year and week titles that match the confluence-page-tree spec when the marker is `AI Dev`.

**Non-Goals:**

- A second intake for blogs or product docs.
- Per-group categories, a track column in the CSV, or track filtering in Slack.
- New CLI commands, a new local `papers/` layout, or edits in the `avatar-papers` worktree.
- Refreshing Confluence reference pages after creation.
- A test framework. Checks are targeted command runs and reading generated output.

## Decisions

### 1. Two families in one config map, ordered by priority

Keep the existing query builder. Replace the keyword map with eight groups. Order is the tie-break when a paper matches several groups: process before feature, and the broadest group last within each family.

| Key | Family | Phrases |
| --- | --- | --- |
| `coding_agents` | process | `coding agent`, `agentic coding`, `software engineering agent`, `SWE-bench`, `issue resolution`, `repository-level code generation` |
| `spec_review_verify` | process | `code review agent`, `test generation agent`, `specification-driven development`, `requirements to code`, `software verification agent` |
| `repo_context` | process | `repository context`, `codebase understanding`, `context engineering`, `retrieval-augmented code generation` |
| `human_ai_workflow` | process | `AI-assisted programming`, `AI pair programming`, `human-AI programming`, `vibe coding` |
| `chart_generation` | feature | `text-to-visualization`, `natural language to visualization`, `chart generation`, `visualization generation`, `data video` |
| `text_motion` | feature | `kinetic typography`, `text animation`, `animated text`, `motion graphics generation` |
| `screen_video` | feature | `screen recording`, `screencast`, `tutorial video generation`, `presentation video generation`, `demo video generation` |
| `gui_agents` | feature | `GUI agent`, `computer-use agent`, `web agent`, `GUI grounding` |

Categories: `cs.SE`, `cs.AI`, `cs.CL`, `cs.HC`, `cs.GR`, `cs.CV`, `cs.MM`. `search_field` stays `abs`. `date_from` is `2025-01-01`, `date_to` unset. Do not reuse a phrase across groups. Avoid phrases that match without AI, such as `developer productivity`.

`TOPIC_EMOJI` in `src/md_to_confluence.py` maps these eight keys. Slack already imports that map.

Alternatives:

- Per-group categories, so process groups skip `cs.CV`. Rejected: needs a config schema and query change for a small noise gain. The phrases already carry the topic, and the score filters the rest.
- Process groups only, with features as reader context. Rejected by the user. Feature work is part of the job.
- A separate feed for features. Rejected by the user. One tree and one weekly report.

### 2. One title marker produces the child titles the spec names

Add `confluence.title_marker: "AI Dev"` and set the existing title fields:

| Field | Value |
| --- | --- |
| `papers_page_title` | `Papers AI Development` |
| `ru_page_title` | `RU · AI Dev` |
| `prompt_page_title` | `Analysis Prompt · AI Dev` |
| `keywords_page_title` | `Search Keywords · AI Dev` |
| `parent_page_id` | the same parent the avatar `Papers` page uses |

`Config` exposes the marker. When it is non-empty, the publisher builds:

- English year `{year} · {marker}`, Russian year `{year} · {marker} (RU)`
- English week `{marker}: {format_weekly_title(...)}`, Russian week the same plus ` (RU)`

A blank marker keeps today's titles. `build_index_html` takes the configured prompt and keywords titles as link text.

Alternative: a separate Confluence space. Rejected: the requested layout is a folder next to `Papers`.

### 3. A router assembles shared text, a group lens, and both tracks

Replace `prompts/analyze_paper.md` with:

```text
prompts/shared.md
prompts/tracks/process.md
prompts/tracks/feature.md
prompts/groups/<topic>.md     one file per keyword group
```

`build_analysis_messages` receives the CSV `topic` and concatenates shared, `prompts/groups/{topic}.md`, then both track files. A missing lens is omitted and logged. The model still sees both tracks and writes one. The router does not drop a track because of the group: `topic` is the first matched phrase and can mislabel the contribution.

`shared.md` holds the reader profile, the classification rule, the header and tail template, the tag rules, and the no-LaTeX rule. Each track file holds that track's body headings, fit values, figure rule, and four score axes. A group lens is a short note of what a hit looks like for that group. It is an instruction, not a section of the analysis.

Lens intent:

| Group | What the lens points at |
| --- | --- |
| `coding_agents` | issue-to-change loop, repository tools, SWE-bench-style evaluation |
| `spec_review_verify` | spec before code, review gate, generated tests |
| `repo_context` | what fits in context, retrieval against a long window |
| `human_ai_workflow` | who writes, who edits, where the human stays |
| `chart_generation` | text to a chart, SVG or a structured representation, edit after generation |
| `text_motion` | text in, animation description out, canvas runtime |
| `screen_video` | capture or a generated demo, tutorial, or presentation video |
| `gui_agents` | operating a GUI, grounding, computer use |

The published prompt page is the same concatenation, with a heading per file, so it is not only `shared.md`. Update the publisher path that now reads `prompts/analyze_paper.md`.

The output contract stays one analysis per paper.

**Reader profile.** Instructions only, never copied into the output. The reader builds features for an AI video product: LLM-generated charts rendered as SVG from a structured intermediate representation, kinetic text where an LLM produces an animation JSON rendered on canvas, and a screen recorder. The reader also organizes development with an agentic IDE, spec-driven planning, and PR review. The takeaway and the integration sections judge papers against this profile.

**Classification.** Pick `process` or `feature` by primary contribution, not by search topic. A process paper changes how software is built with AI. A feature paper gives end users a capability. When both apply, pick the one the paper evaluates.

**Template.**

```text
# {title}
- arXiv / Date / Authors
- Code: {url or "not available"}
- Track: process | feature

## Recommendation: N/10
## Tags
{one comma-separated line}
## Where it fits
  process: discover | specify | implement | review | verify | context
  feature: charts | text-motion | screen-video | gui-agent
![figure](url)            optional, one
## Summary                one paragraph, 2–4 sentences
## Takeaway               adopt or try: ... / skip: ...

process body                        feature body
## Method (workflow loop)           ## Capability (what the user gets)
## Evaluation                       ## Pipeline (input -> models -> output)
## What changed in practice         ## Output and integration
## Adjacent systems                 ## Evaluation
## Human in the loop                ## Competitors
                                    ## Latency and cost

## Limitations
## What you need to run it
```

Output and integration covers output format (SVG, JSON spec, canvas, video), editability after generation, and whether an API LLM can drive it. Latency and cost covers inference time, hardware, and real-time viability.

**Scoring guide.** Four equal axes per track, about 2.5 points each.

| Track | Axes |
| --- | --- |
| process | process relevance, actionability, evidence, transfer outside the authors' scaffold |
| feature | feature relevance, novelty, result quality, product integrability |

Bands for both tracks: 9–10 change something this month, 7–8 worth reading this week, 5–6 adjacent, 3–4 weak, 1–2 off topic. Slack keeps a minimum of 7 for both tracks.

**Tags.** System name, track, stage or feature area, benchmarks, competitors, output format. For example `swe-agent`, `swe-bench`, `spec-driven`, `text-to-vis`, `svg`, `kinetic-typography`. No talking-head vocabulary.

Keep the headings exactly as named, the tags as one line directly after the heading, and the summary as one paragraph. Those are what the parsers read. `Track` stays in the analysis and is not a CSV column. The CSV `topic` stays the search group.

The year-table Topic cell is built in `src/md_to_confluence.py` from that group. The cell shows ⚙️ or 🎯 plus the group emoji, with the short name in a title hint. A legend above the table is two nested lists: each family mark is explained, then its group marks. Slack can keep using the emoji alone.

`build_analysis_messages` tells the model to follow the assembled template, pick the figure by the track it writes, and omit the image when none fits. `build_translation_messages` keeps tag values, the score line, the `Track` and fit values, URLs, and names such as SWE-bench and nvBench untranslated. Remove SadTalker, FID, and Sync-C examples.

Alternatives:

- Eight full prompts, one per group. Rejected: the body and the score axes are shared inside a family, and eight copies drift.
- Router drops the other track based on `topic`. Rejected: the first matched phrase can label a chart paper as `coding_agents`, and the analysis would then score the wrong contribution.
- One body for every paper. Rejected: process sections such as human in the loop are empty for a chart model, and feature sections such as output format are empty for an agent study.
- A `track` CSV column. Rejected: the table distinguishes rows by the search group, which is known before analysis. The written `Track` line shows the model's choice inside the analysis.

The first publish creates the prompt page from that concatenation because the title is new.

### 4. This worktree is the corpus boundary; backfill is by quarter

Keep paths `data/papers.csv`, `data/papers.db`, `data/publish_state.json`, and `papers/`. Do not copy avatar data in. If those files contain avatar rows, replace them with empty files.

With 200 results per group per run, one search from `2025-01-01` returns only the newest 200 matches for broad groups. Backfill with the existing `search --date-from --date-to` by quarter, newest first, as in USAGE.md. Do not raise `max_results_per_topic` for this.

User-facing name on this branch: `AI Dev Papers` in README and USAGE titles, `main.py` description, OpenRouter `X-Title`, and the Slack header `AI Dev Papers: {start} — {end}` in both report builders.

Alternative: a `papers-ai-dev/` local directory. Rejected: that name is the Confluence root, and two worktrees already separate the files.

## Risks / Trade-offs

- [Broad phrases such as `web agent`, `text animation`, or `screen recording` pull adjacent work] → Categories, the 2025 bound, and the score filter limit what reaches Slack. Phrases are config and can be tuned after the first run.
- [Feature phrases were chosen without the private screen-recorder roadmap] → Tune `screen_video` and `gui_agents` once the roadmap is available. No code change needed.
- [The model picks the wrong track on mixed papers] → The prompt gives the primary-contribution rule and the spec has a mixed-paper scenario. Tags still show both areas.
- [Scores from two rubrics share one Slack threshold] → Both rubrics use the same bands. Adjust the threshold only if one track floods the report.
- [A child title collides if the marker is empty] → Example and local config set `AI Dev`.
- [Create-once prompt page captures a stale prompt] → Update the prompt before the first publish on this branch.
- [Local `config.yaml` stays on avatar keywords because it is gitignored] → Implementation updates this worktree's file and does not open the `avatar-papers` worktree.

## Migration Plan

1. Update `config.yaml.example` and this worktree's `config.yaml`. Leave `.env` and the other worktree alone.
2. Ship the prompt files, the router, LLM messages, title construction, topic labels, and user-facing strings on `ai-development`.
3. If this worktree's CSV or publish state has avatar rows, replace them with empty files.
4. Search by quarter from the current quarter back to 2025-01-01, then download and analyze.
5. First `publish` creates `Papers AI Development` and its children without touching the avatar tree.
6. Rollback is reverting this branch. Pages under `Papers AI Development` can stay.
