---
name: retro
description: Retrospective on a coding session that proposes improvements to the agent's environment. User-invoked via /retro.
disable-model-invocation: true
---

# Retro

The user has asked for a **retrospective**. You suggest improvements to the coding agent's **environment** so future runs go better. You change the environment, not the code: for a shipped bug, a file that took twenty tool calls to find, or a rule the reviewer missed, ask what in the project let it happen and propose the pointer, check, or standard that prevents it next time.

You **propose**. Nothing changes until the user picks a candidate.

## Steps

### 1. Load the writing style

Read `.cursor/skills/writing-for-agents/SKILL.md`. Every rule, skill, standard, or steering line you propose follows it.

### 2. Read the session's primary sources

Default to the **current** session: its struggles are still in your context. Otherwise use the session the user names (uuid, title, or topic).

Past sessions live in the agent-transcripts folder named in your system context (`~/.cursor/projects/<workspace-slug>/agent-transcripts`):

- `<uuid>/<uuid>.jsonl` is the main session; `<uuid>/subagents/<id>.jsonl` are its subagent runs.
- One JSON object per line: `role` is `user` or `assistant`, `message.content[]` holds `text` items and `tool_use` items (`name`, `input`); `{"type":"turn_ended"}` closes a turn.
- Files are UTF-8: read them with the Read tool or `rg` (PowerShell needs `Get-Content -Encoding UTF8`). Find a session by topic with `rg` for a distinctive phrase across the folder.

Transcripts record tool **calls**, not their results or the agent's thinking. Reconstruct struggles from what is recorded: repeated or near-identical calls, one file read many times, searches that widen step by step, retried commands, the agent's own text ("that failed", "trying another approach"), user corrections and pushback. When an outcome matters and is cheap to reproduce (a lint or test command, a search), re-run it read-only to confirm.

Done when you hold a list of **struggle moments**, each tied to a turn plus a tool call or quote. A smooth session yields few or none: say so and stop there, with the categories left unfilled.

### 3. Map the environment the session ran in

Read the project's own sources for the parts the struggle moments touch:

- **Repo**: this single repository (`main.py`, `src/`, `scripts/`, `prompts/`, `openspec/`).
- **Checks**: `.github/workflows/`, pre-commit config, `scripts/`, `pyproject.toml` / `setup.cfg` / `mypy.ini`, `requirements.txt`.
- **Always-loaded steering**: Cursor user rules (in Cursor settings, visible in your system context), `.cursor/rules/*.mdc` with `alwaysApply: true`, any `CLAUDE.md` / `AGENTS.md`, and every skill `description` in `.cursor/skills/*/SKILL.md`.
- **On-demand steering**: skill bodies, `.cursor/commands/*.md`, glob-scoped rules, `docs/`, `openspec/`, repo READMEs.
- **Review stage**: `.cursor/skills/spec-implementation-review/SKILL.md` (`/opsx-review`) is the project's **reviewer agent**, alongside the Bugbot and `qa-reviewer` subagents. Note which standards files it actually reads.

### 4. Find candidates

Walk every struggle moment through the categories in [Categories](#categories). A moment can yield one candidate, several, or none.

### 5. Present, most severe first

Rank by the cost of the mistake recurring. A quiet, expensive mistake (silently wrong output, a check nobody notices is broken) outranks a loud, cheap one.

For each candidate:

- **Category** and a one-line title.
- **Evidence**: the session moment (turn, tool call, or quote). Cite past sessions as `[<title>](<uuid>)`.
- **Fix**: the exact file and change; for a check, the command and where it gets wired (CI job, pre-commit hook, reviewer step).
- **Load**: what it costs: an always-loaded line, CI time, hook latency, or human memory.

Drop every candidate you cannot trace to a specific moment. Write the report in the user's language, then ask with `AskQuestion` (multi-select) which candidates to apply.

### 6. Apply the chosen candidates

Apply only what the user picked, and leave the changes uncommitted. Run a new check against the whole repo before making it blocking, and report existing violations to the user for a decision.

## Reference

### Categories

- **Navigation**: how easy was it for the agent to find the right files? Are there hidden dependencies between files (a cron script that drives a `main.py` command, a prompt file consumed by `src/llm_analyzer.py`)? Would a **navigation pointer** from a file the agent already reads make it easier? _Use when_ the session took a long time to find a piece of information.
- **Automated checks**: could a lint rule, type check, test, or filesystem linter have caught the agent's mistake? Read the repo's own check commands first (step 3), so a check that already exists but sits unwired (missing from CI or from pre-commit) or silently broken is the finding, not a reinvention. A repo with no **guardrail** (no pre-commit hook and no CI job running its lint, typecheck, and test commands) is itself a finding: an un-linted repo is a standing missed opportunity, not a neutral default. When the session shows a check firing on correct code, propose loosening or removing it. _Use when_ the agent made a mistake a check could have caught, a check misfired, or a repo has no guardrail at all.
- **Coding standards**: should the reviewer agent enforce a new rule, or drop or clarify an existing one? Classify the violation first. A **mechanical** one (a fixed syntactic pattern, a banned API, an import shape, a file-location rule) gets a deterministic check, full stop: a custom rule in the repo's own linter, a mypy setting, a pre-commit hook, or a CI job, whichever the repo's language and existing guardrail make cheapest. Default to building the check over writing the rule. Reserve `CODING_STANDARDS.md` for genuine **judgement calls** (cross-file consistency, "matches the surrounding style," anything no guardrail could substitute for), placed at the repo root. Creating that file includes adding a pointer to it in `spec-implementation-review`, because a standard the reviewer never reads is a no-op. _Use when_ the reviewer agent failed to catch a mistake.
- **Always-loaded steering**: do user rules, `alwaysApply` rules, `CLAUDE.md` / `AGENTS.md`, or skill descriptions carry instructions that belong in coding standards, checks, or on-demand docs? User rules live in Cursor settings: propose the replacement text for the user to paste. _Use when_ one of these is large, or the session paid for a rule that did not apply to its task.
- **Skills and workflow**: did a project skill or command (OpenSpec, `pr`, `spec-implementation-review`) steer the agent wrong through a stale step, a vague completion criterion, or a missing branch? Propose the edit to that skill. _Use when_ the agent followed a skill and still struggled.
- **Tool economy**: did the agent make expensive tool calls that could be streamlined: oversized shell output, whole large files read for one fact, browser snapshots, token-heavy MCP calls, subagents repeating exploration already done? Propose a narrower command, a script in `scripts/`, or a pointer to the right entry point. _Use when_ the agent made an expensive tool call.
- **No-ops**: find instructions in steering files that do not change the agent's behaviour versus its default. Judge each against this one session, so present it as a candidate for the deletion test, not a verdict. _Use when_ the steering files are large and unwieldy.
- **Information access**: could the agent have reached a crucial fact it lacked? Examples: service logs of the local Docker stack, a dev server log teed to a file, CI logs through `gh`, read-only access to a third-party service. _Use when_ a crucial piece of information was not available to the agent.

### Implementation vs review

All work goes through two stages: implementation and review. The implementation agent carries the most **context pressure**: it explores, writes code, and debugs failures. The review agent carries the least: it receives a diff, needs no exploration, and rarely writes code or debugs.

So the review agent imposes coding standards, not the implementation agent.

### Where each fix lives

- Always-loaded files (`CLAUDE.md` / `AGENTS.md`, `alwaysApply` rules, user rules) enter every agent's context window. Use them very sparingly, mostly for **navigation pointers** to other files.
- `CODING_STANDARDS.md` is read during review, not implementation. Add navigation pointers to docs folders once it grows past 1,000 lines.
- Docs are reference files pointed to by other files. Look for existing ones (`docs/`, `openspec/specs/`, repo READMEs) before writing new ones.
- Skills hold docs (their description enters the agent's context window) or user-invoked commands (`disable-model-invocation: true` plus a `.cursor/commands/` wrapper, as this project does). Write them per `writing-for-agents`.
