## Implementation review: retarget-ai-dev-radar

### Scope
| Base | HEAD | Ahead | Dirty | Diff |
| --- | --- | --- | --- | --- |
| `origin/main` (1477245) | `ai-development` | 0 | yes (10 modified, 1 deleted, new `prompts/shared.md`, `prompts/tracks/`, `prompts/groups/`, `openspec/`, `.cursor/`) | uncommitted (`git diff origin/main` + untracked prompt files); `origin/main...HEAD` is empty |

### Sources
- OpenSpec: `openspec/changes/retarget-ai-dev-radar/` — `proposal.md`, `design.md`, `tasks.md`, `README.md`, delta specs `ai-dev-search`, `ai-dev-analysis`, `confluence-page-tree`.
- Feature specification: none @-mentioned; the OpenSpec change is the source of truth.
- Deferred / non-goals (out of scope): blog or product-doc intake, per-group categories, a `track` CSV column, Slack track filtering, new CLI commands, edits in the `avatar-papers` worktree, refreshing Confluence reference pages after creation (the prompt page is create-once), a test framework.
- Not findings: `.cursor/` and `openspec/` untracked directories (PR skill owns branch layout); the `avatar-papers` User-Agent / `HTTP-Referer` strings in `src/code_finder.py`, `src/downloader.py`, `src/figure_parser.py`, `src/llm_analyzer.py` (task 3.5 names only `X-Title`).
- Verified against data: local `config.yaml` has the eight groups and `title_marker: "AI Dev"`; `/home/oleksiik/avatar-papers/config.yaml` still has `talking_head` and was last modified 2026-09-30; the CSV holds 376 rows over all eight groups; two EN and two RU analyses exist.

### Findings tracker
| Finding | Severity | Disposition | Origin | Modules | Status | Where it landed |
| --- | --- | --- | --- | --- | --- | --- |
| W1 Feature track never produced; task 4.2 marked done | WARNING | fix pass | introduced by diff | `openspec/changes/retarget-ai-dev-radar/tasks.md`, `prompts/shared.md` | **done** | `papers/analysis/2610.26071.md` L7, L21–L23, L40–L62; `tasks.md` L26 |
| I1 Group family table duplicates the config group list | IMPROVEMENT | fix pass | introduced by diff | `src/md_to_confluence.py` | **done** | `src/md_to_confluence.py` L13–L24, L175–L191 |
| I2 Dead `prompt_title` / `keywords_title` params on the year table | IMPROVEMENT | fix pass | introduced by diff | `src/md_to_confluence.py` | **done** | `src/md_to_confluence.py` L271–L275 |
| L1 Track files use output-level `##` headings for instructions | LATER | deferred | introduced by diff | — | **open** | — |

### Findings
#### CRITICAL
None.

#### WARNING
- **W1 Feature track never produced; task 4.2 marked done** — **done** — fix pass — modules: `tasks.md`, `prompts/shared.md`
  `papers/analysis/2610.35316.md` (topic `chart_generation`, "RSIV-Harness … Conversational Text-to-Visualization") was written as `Track: process`, fit `verify`, with the process body. Both saved analyses are process, so the feature body, the feature fit values, the feature figure rule, and the feature rubric have never been produced by the model. Task 4.2 is checked and says "Verify each English file has the correct `Track`", and the design's verification checklist says "One process paper and one feature paper analyze with one track body each". The data does not support that claim. The process call is defensible because the paper's contribution is a harness self-improvement loop. But the spec scenario "Chart generation paper found by a process phrase → feature" and the whole feature path are still unexercised.
  Root cause: the paper picked for the feature check was a mixed paper, and the check accepted the track without confirming that the feature path ran.
  Fix: analyze one clear feature paper (for example a `chart_generation` or `text_motion` row whose contribution is end-user output). Confirm `Track: feature`, a fit value from `charts | text-motion | screen-video | gui-agent`, the six feature headings and none of the process headings, and that `sync`, `parse_tags`, and `_extract_summary` work. Then correct the 4.2 note in `tasks.md` so it records which paper covered the feature track. If a clear text-to-vis paper also comes back as `process`, tighten the classification rule in `prompts/shared.md`, for example "a harness or agent whose output is an end-user chart is `feature` unless the paper evaluates the development loop itself".
  Larger problem it may hide: the model may lean toward `process` for any agentic paper, which would empty the feature family in the weekly report. Watch the track distribution after the first backfill.

#### IMPROVEMENT
- **I1 Group family table duplicates the config group list** — **done** — fix pass — modules: `src/md_to_confluence.py`
  `src/md_to_confluence.py` `TOPIC_FAMILY` and `TOPIC_EMOJI` are two parallel dicts keyed by the same eight group keys. The keys also appear in `config.yaml.example` and as `prompts/groups/*.md`. Adding a group means editing four places. If someone misses `TOPIC_FAMILY`, the Topic cell silently falls back to the bare group (`format_topic_cell` drops the family), and that breaks the confluence-page-tree "Topic cell names the group" requirement with no error.
  Root cause: per-group display metadata is split across two module constants.
  Fix: merge them into one map, `TOPIC_META = {"coding_agents": ("process", "🤖"), …}`, and derive `TOPIC_EMOJI` from it for `slack_weekly.py`. Optionally log a warning in `format_topic_cell` when a non-empty topic has no family. No test framework exists, so the check is to run `build_papers_table_html` on rows for every configured key and confirm each cell contains `process · ` or `feature · `.
  Larger problem it may hide: none found. Today all eight keys are present in both maps.
- **I2 Dead `prompt_title` / `keywords_title` params on the year table** — **done** — fix pass — modules: `src/md_to_confluence.py`
  `build_papers_table_html` gained `prompt_title` / `keywords_title`, but both callers in `src/confluence_publisher.py` (`_publish_year`, around L192 and L243) pass neither `prompt_url` nor `keywords_url`. The new parameters, and the reference-link branch they feed, never run. Only `build_index_html` needs the configured titles, and it gets them.
  Root cause: the index change was copied to the year-table builder speculatively.
  Fix: remove the two new parameters from `build_papers_table_html`, or pass the URLs and titles from `_publish_year` if year pages should carry reference links. Nothing in the spec asks for that, so removing them is the obvious answer.
  Larger problem it may hide: the pre-existing `prompt_url` / `keywords_url` parameters on that function are also unused. Remove them too if that stays local.

#### LATER
- **L1 Track files use output-level `##` headings for instructions** — **open** — deferred
  `prompts/tracks/process.md` and `feature.md` use `## Where it fits`, `## Figure`, `## Score`, and `## Body` as instruction headings. Those sit at the same level as the output headings listed under them (`## Method`, `## Capability`, …), and `## Where it fits` is also a real output heading. A model could echo `## Score` or `## Body` into the analysis, or emit `## Where it fits` twice. Fix: demote the instruction headings to `###` or plain bold labels, and keep only emitted headings at `##`. Deferred because the two real outputs are clean: no extra headings, and the tags, score, and summary all parse. No current input reaches the problem.

### Coverage gaps
- No lint or type-check is configured: no `mypy.ini`, `setup.cfg`, `pyproject.toml`, `.flake8`, or pre-commit config, and mypy, flake8, and ruff are not installed in the shared venv. The only gate run was `py_compile` on `main.py` and `src/*.py`, which passed. No tooling gate exists for the touched files.
- No automated tests (a stated non-goal). These checks rely on manual runs:
  - The marker title values: `2026 · AI Dev`, `AI Dev: Feb 16 - Feb 22, 2026`, the `(RU)` variants, and blank-marker fallback.
  - Topic cell distinguishability: `process · coding_agents` vs `feature · chart_generation`.
  - Router contents for a known topic vs an unknown topic.
- Real-service evidence exists: a live search (376 rows, all eight groups), analyses plus RU translations (including feature paper `2610.26071`), and a publish that created `AI Dev: Oct 26 - Nov 01, 2026` pages (the URLs are in the CSV). The parent reports that the `Papers` version stayed at 192.
- The model's track choice is visible only by reading the generated output. No gate catches a skew toward one track.

### Manual check checklist
- Analyze one clear feature paper and confirm `Track: feature`, a feature fit value, only the six feature headings, and that `sync`, tags, Slack summary, and the RU file keep the track, fit, and tag values in English (W1).
- Open the `papers-ai-dev` index in Confluence. Confirm the link text reads `Analysis Prompt · AI Dev` and `Search Keywords · AI Dev` and that the links target this tree.
- Open `2026 · AI Dev`. Confirm the Topic cells read `🤖 process · coding_agents` and `📊 feature · chart_generation`.
- Open the prompt page. Confirm it contains shared, both tracks, and all eight lenses under per-file headings.
- Confirm the avatar `Papers` page and its children are unchanged (version 192).
- Send or dry-run the weekly Slack report. Confirm the header reads `AI Dev Papers: {start} — {end}` and the score ≥ 7 filter is unchanged.

### Rounds
#### Round 1 — 2026-10-31 — initial review
- Found: W1 Feature track never produced; task 4.2 marked done; I1 Group family table duplicates the config group list; I2 Dead `prompt_title` / `keywords_title` params on the year table; L1 Track files use output-level `##` headings for instructions.

#### Round 2 — 2026-10-31 — fix pass
- Fixed: W1, I1, I2. L1 left deferred.
- W1: analyzed `2610.26071` (CUA-Lite, group `gui_agents`). English output is `Track: feature`, fit `gui-agent`, feature headings only. `sync` stored score `6` and `https://cua-lite.github.io`. `parse_tags` returned 12 tags; the Slack summary extractor returned the summary paragraph. The Russian file keeps `feature`, `gui-agent`, the score line, and the English tags. Task 4.2 now names this paper. Classification in `prompts/shared.md` was left as written: this paper did not come back as `process`.
- I1: `TOPIC_FAMILY` and `TOPIC_EMOJI` are one `TOPIC_META` map; `TOPIC_EMOJI` is derived for Slack. `format_topic_cell` warns when a non-empty topic has no family. `build_papers_table_html` on one row per configured key contains `process · ` or `feature · ` in every cell.
- I2: `build_papers_table_html` no longer takes `prompt_url`, `keywords_url`, `prompt_title`, or `keywords_title`. The index builder still does, and the publisher still passes those titles there.
