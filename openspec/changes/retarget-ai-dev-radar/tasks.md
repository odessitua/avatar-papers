# Tasks

## 1. Search configuration

- [x] 1.1 Update `config.yaml.example` with the eight keyword groups in the order from design.md Decision 1, the seven categories, and `date_from: 2025-01-01`. Set `papers_page_title`, `ru_page_title`, `prompt_page_title`, `keywords_page_title`, and `title_marker` to the values in Decision 2. Verify the file lists the four process groups before the four feature groups, contains no talking-head, lip-sync, portrait, face-reenactment, or face-reconstruction phrase, and repeats no phrase across groups.
- [x] 1.2 Update this worktree's gitignored `config.yaml` the same way. Keep its existing `space_key` and `parent_page_id`. Do not edit `/home/oleksiik/avatar-papers/config.yaml`. Verify this worktree's keywords and `title_marker` match the example, and the avatar worktree file still has its previous keyword groups.
- [x] 1.3 Print the query for each group with `_build_query` and the loaded config. Verify every query ORs only that group's phrases on `abs`, includes all seven categories, and carries the `20250101` lower bound.
- [x] 1.4 Update the search sections of `README.md` and `USAGE.md`: two families, eight groups, categories, date window, and quarter-by-quarter backfill from Decision 4. Verify those sections name both families and no longer tell the operator to search for talking-head papers.

## 2. Analysis prompt

- [x] 2.1 Replace `prompts/analyze_paper.md` with `prompts/shared.md`, `prompts/tracks/process.md`, `prompts/tracks/feature.md`, and `prompts/groups/<topic>.md` for the eight groups. Put the reader profile, classification rule, header, tail, tag rules, and no-LaTeX rule in `shared.md`. Put each track's body, fit values, figure rule, and score axes in its track file. Write each lens from the intent table in design.md Decision 3. Verify the old prompt file is gone, every group file exists, and the pieces together contain `Code`, `Track`, `## Recommendation:`, `## Tags`, `## Where it fits`, `## Summary`, `## Takeaway`, both track bodies, `## Limitations`, `## What you need to run it`, both fit value sets, and both four-axis rubrics.
- [x] 2.2 Assemble the request in `build_analysis_messages` from shared, the lens for the CSV `topic`, and both track files. Pass `topic` through from the analyze command. Omit and log a missing lens. Update `build_translation_messages` to keep the score, `Track`, fit values, and tag values untranslated. Verify a call with topic `chart_generation` contains that lens and both track headings, a call with an unknown topic still contains both tracks, and `architecture`, SadTalker, FID, and Sync-C do not appear in `src/llm_analyzer.py`.

## 3. Confluence titles and reader-facing names

- [x] 3.1 Add a `title_marker` property on `Config`. When it is non-empty, build year and week titles as in design.md Decision 2. When it is missing or blank, keep today's titles. Verify that marker `AI Dev` yields `2026 · AI Dev`, `2026 · AI Dev (RU)`, `AI Dev: Feb 16 - Feb 22, 2026`, and `AI Dev: Feb 16 - Feb 22, 2026 (RU)`, and a blank marker still yields `2026` and `Feb 16 - Feb 22, 2026`.
- [x] 3.2 Pass the configured prompt and keywords titles into `build_index_html` as link text. Verify the index HTML renders `Analysis Prompt · AI Dev` and `Search Keywords · AI Dev`.
- [x] 3.3 Render the year-table Topic cell as `process · {topic}` or `feature · {topic}` from the group family in design.md Decision 1. An emoji may prefix the words. Verify a `coding_agents` row contains `process · coding_agents` and a `chart_generation` row contains `feature · chart_generation`.
- [x] 3.4 Build the Confluence prompt page from the same concatenation as the router, with a heading per file. Verify the page source includes `shared`, both track names, and all eight group lenses, and that the publisher no longer reads `prompts/analyze_paper.md`.
- [x] 3.5 Set the Slack header in both report builders to `AI Dev Papers: {start} — {end}`, keeping the score filter. Set the CLI description, OpenRouter `X-Title`, `README.md` title, `USAGE.md` title, and `scripts/README.md` cron comments to `AI Dev Papers`. Verify those files no longer say Avatar Papers, and the Confluence tree section in `USAGE.md` shows `papers-ai-dev` with the child titles from the confluence-page-tree spec and the Topic cell form `family · group`.

## 4. Integration check

- [x] 4.1 Confirm `data/papers.csv` and `data/publish_state.json` are absent or empty before the first search. Run `python main.py search` for the current quarter and verify rows exist for at least one process group and one feature group, each paper appears once, and none is dated before 2025-01-01. Confirm `/home/oleksiik/avatar-papers/config.yaml` is unchanged.
- [x] 4.2 Download, then run `python main.py analyze --arxiv-id <id>` on one paper from `coding_agents` and one from a feature group. Verify each English file has the correct `Track` and only that track's body, `python main.py sync` fills `score` and `code_url` in the CSV, `parse_tags` returns the tags, and the Slack summary extractor returns the summary paragraph. Verify the Russian file keeps the score line, track, fit value, and tag values in English. Verify the year-table HTML for those rows contains `process · coding_agents` and `feature · {group}`. Process: `2610.38214` (`coding_agents`, Track `process`). Feature: `2610.26071` CUA-Lite (`gui_agents`, Track `feature`, fit `gui-agent`). The first feature attempt, `2610.35316`, is a harness and correctly stayed `process`.
- [x] 4.3 Before publishing, confirm the configured `parent_page_id` is the parent of the avatar `Papers` page and that the `Papers` page version is recorded. Run `python main.py publish` and verify `papers-ai-dev` exists beside `Papers` with the titled children from the spec, and the `Papers` page version did not change.

## Workflow follow-up

- Apply the tasks, then verify and review.
- Archive only after that review.
