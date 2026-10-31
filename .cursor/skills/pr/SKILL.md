---
name: pr
description: >-
  Opens this project's PR: one feature branch, PR base = main unless the branch
  is stacked on another open PR, keeping all committed work and leaving .cursor/
  skill files on their own branch. Also use when writing a PR body. Use when the
  user asks to create/open/ship a PR, push the feature branch, stack PRs, or /pr.
---

# PR

The project is a single repository (`avatar-papers`, remote `origin`). The
integration branch is `main`.

## 1. Scope and plan

```text
base_ref = origin/main   # if missing, origin/HEAD
ahead    = git rev-list --count <base_ref>..HEAD
dirty    = git status --porcelain
```

There is nothing to ship when `ahead == 0` and the tree is clean; say so and stop.

Announce the plan first. Base branch is the PR base from §5, not always `main`;
for a dirty tree it is the expected base, rechecked after the commit:

```text
| Base branch | Branch | Proposed title | Labels (§4) |
```

## 2. Branch

Name the branch `feature/<task-name>` (a fix is `fix/<task-name>`). The first
`/pr` argument is the task name; a separately stated branch name overrides the
default. If the push is rejected with a branch-name rule, rename the branch to
the pattern in that error and push the new name. Record the source `HEAD`
holding the implementation work before switching branches. After fetching,
resolve the target in this order: use the local branch if present; otherwise
track `origin/<target>` if present; otherwise create it from the source `HEAD`.
For an existing target, compare its base diff with the source and bring in every
missing agreed change while preserving commits already on the target. If the
source mixes unrelated commits, confirm which ones to cherry-pick.

## 3. Commit and open the PR

1. `git fetch origin`; confirm the branch is up to date with `origin/main`. If it
   is behind or conflicts, resolve that with the user first.
2. Resolve and switch to the target branch (§2).
3. Stage the agreed changes only. Local data, secrets, and unrelated dirty files
   stay out: `.env`, `config.yaml`, `data/`, `papers/originals/`,
   `papers/analysis*/`, `logs/`.
4. Include the task files from their current location. For OpenSpec this is
   `openspec/changes/<change>/`, or
   `openspec/changes/archive/YYYY-MM-DD-<change>/` after archival.
   `.cursor/` skill and command files stay on their skill branch.
5. Check `git diff origin/main...HEAD` holds the full intended change, commit,
   `git push -u origin HEAD`, then
   `gh pr create --base <PR base from §5> --label <label>...` (§4) with a HEREDOC
   body written per [BODY.md](./BODY.md), then stack it (§5) only when that base
   is a stack parent.

Every commit: write the message to a file, confirm the file exists, then
`git commit -F <file>`.

## 4. Labels

Every PR gets one review label and a `risk:*` label for each category its
diff changes. Apply a category when the change alters behaviour in that area,
not merely touches a file there; when unsure, apply it.

| Label | The diff changes |
| --- | --- |
| `risk:security` | secrets and credentials: `.env` handling, API tokens for Confluence, Slack, or LLM providers, what gets logged about them |
| `risk:data` | stored data: a `papers.csv` column or DB field renamed, removed or retyped, `publish_state.json` format, a deletion, a backfill |
| `risk:contract` | what cron jobs, operators, or readers rely on: `main.py` commands and flags, `config.yaml` keys, Confluence page titles and hierarchy, Slack message format |
| `risk:output` | how published content looks: Confluence tables and weekly pages, Slack reports, analysis markdown, `prompts/` that shape LLM output |
| `risk:infra` | what runs and what it costs: `scripts/*.sh` cron wrappers, schedules, LLM model, provider, or token limits |
| `risk:privacy` | personal data or private content reaching logs or third parties |
| `risk:performance` | hot paths: an API or LLM call in a per-paper loop, re-downloading or re-publishing unchanged content, unbounded searches |
| `risk:dependencies` | a new runtime dependency, a major bump, or a Python version change in `requirements.txt` |
| `risk:testing` | tests deleted, skipped or weakened, quality gates loosened |

The review label follows: any `risk:*` label means `review:deep`, none means
`review:light`. A `review:deep` PR stays deep. For `review:deep`, Merge Danger
names each risk label with the file that earned it.

These mark where the diff sits. They never change the review label.

| Label | When |
| --- | --- |
| `skills` | a file under `.cursor/skills/` or `.cursor/commands/` |
| `docs-only` | every changed file is documentation: `*.md`, or anything under `docs/` or `openspec/`. Any other file drops it |
| `tests-only` | every changed file is a test: `test_*.py`, `*_test.py`, or anything under a `tests/` directory. Any other file drops it. Not `risk:testing` |

Before `gh pr create`, run `gh label list` and create each missing label with
`gh label create <name> --color <color> --description "<the row above>"`:
`review:light` `0E8A16` ("Read the body, skim the diff, approve"),
`review:deep` `B60205` ("Read the full diff, sign off each risk label"),
`D93F0B` for every `risk:*`, and `1D76DB` for `skills`, `docs-only`, and
`tests-only`.

## 5. Base and stack

`main` is the PR base, and it is never a stack parent: an open PR whose head is
`main` does not qualify.

A stack parent is an open PR in this repo whose head branch is neither `main`
nor this branch, and which this branch forked from. After `git fetch origin`,
`<pr-head>` is `origin/<its head branch>` and `<integration>` is `origin/main`.
Skip a candidate when `git merge-base --is-ancestor HEAD <pr-head>` succeeds:
that PR already contains this branch, so it is this branch's own PR or one
stacked on top of it. `git merge-base HEAD <pr-head>` must be strictly ahead of
`git merge-base HEAD <integration>`: the integration merge-base is
`--is-ancestor` of the pr-head merge-base, and the two commits differ. The
parent's current tip need not be an ancestor of `HEAD`: commits landed on the
parent after the fork still leave the fork point ahead of `main`. When several
qualify, the parent is the nearest: `git rev-list --count <merge-base>..HEAD` is
smallest. Pass that head branch as `--base`. With no parent, `--base` is `main`
and this section stops.

Run these checks on the commit being pushed, after the §3 commit. Before it, a
branch holding only uncommitted work still sits on its parent's tip, and the
skip above would drop that parent.

Every stack call needs `-H "X-GitHub-Api-Version: 2026-03-10"`; without it the
API answers 404. Stop walking when the next base is `main`.

- The base PR is already in a stack
  (`gh api "repos/{owner}/{repo}/stacks?pull_request=<base PR>"`) and is its
  top: `gh api -X POST repos/{owner}/{repo}/stacks/<n>/add -F "pull_requests[]=<new PR>"`.
- No stack yet: walk down while each base is the head of an open PR, then
  `gh api -X POST repos/{owner}/{repo}/stacks -F "pull_requests[]=<bottom>" ... -F "pull_requests[]=<new PR>"`,
  numbers bottom to top.
- The base PR sits mid-stack: a stack is a straight line, so leave the PR
  unstacked and say so.

Done when the response carries a `number` and the output includes
`https://github.com/<owner>/<repo>/stack/<number>`.

## 6. Output

When the PR is up, paste the link (it gets copied into Slack):

```text
- `avatar-papers` (`<PR base>`): https://github.com/...
- `avatar-papers` (`<PR base>`): https://github.com/... (stack: https://github.com/<owner>/<repo>/stack/<number>)
```

If a pre-commit hook fails, fix the reported issue or show it to the user.
