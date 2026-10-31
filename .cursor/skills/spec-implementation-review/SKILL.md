---
name: spec-implementation-review
description: >-
  Reviews implementation against OpenSpec + feature specification (module split, reuse,
  duplication, values and special cases, optimization, test coverage), scoped to
  what this branch changed vs origin/main. Recommended right after
  /opsx-apply finishes. Use when the user asks for an implementation review, a
  review of a port/transfer, a review against a feature specification/OpenSpec,
  a re-review of fixes, or /opsx-review.
---

# Spec implementation review

Architecture/quality review of **our** work against a feature specification and OpenSpec. `/opsx-verify` covers archive readiness and checkbox completeness separately.

## Where to run

Run the review in a **fresh context**: a new chat window or a subagent (`Task`) on the
**latest Claude Opus** model from the available subagent models (pick the newest
Opus slug at run time). When `/opsx-apply` finishes, the implementing agent
recommends this and, if the user agrees, launches the subagent with the change
name and feature specification path.

## Recommended pipeline after `/opsx-apply`

1. **Review** (round 1) — findings go to `review.md`, all **open**, each with a
   severity and a disposition (§3). Report, then wait only for the user to settle
   **user decision** rows. Record deferred rows without offering them as work.
2. **Fix** — implement every **must fix** and **fix pass** row, the settled **user
   decision** rows, and any deferred rows the user explicitly selected. Update the
   tracker.
3. **Manual check** — the user tests by hand; each bug found becomes a new finding
   in the same `review.md` (§5) and is fixed like the others.
4. **Re-review** (round N) — review what changed since the previous round (§5).
5. Closing steps: sync specs, archive, PRs (`.cursor/skills/pr/SKILL.md`), …

## 1. Resolve sources of truth

Priority:

1. OpenSpec change the user named, or the only active change (`openspec list --json`). If archived, find `openspec/changes/archive/YYYY-MM-DD-<change-name>/` and load `proposal.md`, `design.md`, `tasks.md`, delta specs, and `README.md` from there.
2. Feature specification they `@`-mentioned (a feature document, issue, or prompt file such as `prompts/analyze_paper.md`).
3. Existing code to reuse.

**Deferred tasks** (`- [ ]` left for later, optional groups) and the change's stated **non-goals** are out of scope. Name them under Sources and, when they are manual checks, in the manual checklist. They are not findings.

If the feature specification and OpenSpec conflict, flag it for the user.
Also check each document against itself and against the data: a heading that names one
rule while the table under it carries an exception, or a task claiming "default
fixtures unchanged" while the golden/fixture diff shows changes, is a finding.

**Persisted review report.** Active change: `openspec/changes/<change>/review.md`.
Archived change: `review.md` inside its existing archive directory. Review against
a feature specification only (no OpenSpec change): report in chat.

## 2. Scope the diff

The project is a single repository; the base is `main` unless the user names
another one.

```text
base_ref    = origin/main if it exists, else main   # or the user's base
HEAD_branch = git rev-parse --abbrev-ref HEAD
dirty       = git status --porcelain
ahead       = git rev-list --count <base_ref>..HEAD
```

| Situation | Diff to review |
| --- | --- |
| `ahead == 0`, clean | Nothing to review — stop |
| `HEAD_branch == main`, dirty and/or `ahead > 0` | Uncommitted + `git diff <base_ref>` |
| `HEAD_branch != main`, `ahead > 0` or dirty | `git diff <base_ref>...HEAD` plus uncommitted |

Announce a **scope line** before reading code:

```text
| Base | HEAD | Ahead | Dirty | Diff |
```

If there is nothing to review, stop: "No changes vs `<base_ref>`."

## 3. Review method and axes

The **diff defines accountability; reading goes as far as needed** to judge whether
the delta is correct in the real system.

### Required context pass

For each changed file or public symbol:

1. Read the complete enclosing module/class and the relevant callers/callees.
2. Search for all usages of changed exports, events, modifiers, API payloads,
   persisted fields, and shared constants.
3. Search sibling/shared modules for equivalent behavior, including different
   names that implement the same state transition, formula, request, or UI flow.
4. Trace the affected path end-to-end across module and external-service
   boundaries (CLI command → fetch → store → analyze → publish).
5. Read the nearest tests and fixtures and compare them with the production path
   to catch integration mismatches hidden by mocks.
6. For each invariant the change introduces or relies on (mutually exclusive
   modes, "flag only together with X", allowed value ranges), list **every
   writer** of that state — CLI flags, `config.yaml`, CSV/DB rows, publish state,
   LLM output parsing, defaults — and check each one.

For **reuse and duplication**, search both identifiers and domain concepts from the
specification, then compare responsibility and behavior. Record which existing
implementation was considered for reuse, or state that no equivalent was found.

Unchanged code becomes a finding when the in-scope change duplicates or depends on
it, exposes its failure through a touched-file gate, makes it newly reachable, or
needs it changed to be correct. Label such findings `pre-existing, surfaced by this change`.

Against the feature specification + OpenSpec design decisions + tasks, review:

1. **Module responsibility** — right layer owns the logic: CLI wiring in `main.py`, domain modules in `src/`, operational wrappers in `scripts/`, prompts in `prompts/`.
2. **Reuse** — old methods reused where they should be; one copy of each formula/FSM.
3. **Duplication** — same logic in two modules is a finding, except what `tasks.md` explicitly deferred.
4. **Values and special cases** — the design's own values are under review too.
   - For every new or changed constant, default, range, anchor point, or table row:
     compute the output at min, default, and max (or the table's edge rows). Check
     that inputs meant to behave differently produce distinguishable results, and
     that all results stay inside the design's constraints (valid ranges, date
     windows, score scales, API limits).
   - For every exception to a general rule — a separate divisor/offset for one call
     site, a bare number, a branch for one variant, or "except X" in the spec/table —
     ask whether changing the inputs (data, anchor points, parameters) would let the
     general rule cover it. If yes, that is a finding with the concrete input change.
5. **Optimization** — repeated network or LLM calls, re-downloading or re-publishing unchanged content, ignored overrides, work the old path already did cheaper.
6. **Tests** — ask what the automated gate structurally cannot see (mocked API
   responses vs real payloads, fixture vs production data, formatting visible only
   in Confluence or Slack).
   For the values checked in axis 4, name the test that locks in their
   distinguishability; if none exists, record it under **Coverage gaps** with a
   manual check.
7. **External integrations** — calls to arXiv, Confluence, Slack, and LLM providers match their APIs, handle rate limits and failures, and keep secrets in `.env`; `config.yaml.example` documents every new config key.
8. **Pre-existing errors surfaced by touching the file** — for every file the diff
   touches, run the project's lint/type-check (mypy, flake8, or whatever is
   configured) against the **whole file**. A pre-existing error that breaks the
   build or the pre-commit gate is CRITICAL. An accepted warning is IMPROVEMENT only
   when its fix is local, mechanical, and low-risk; otherwise it is LATER. Checkout
   line-ending churn, mass formatting, byte-identical vendored files, and complexity
   that needs a structural refactor are not automatic fix-pass work. This axis
   covers tooling errors only; unreported style taste is out of scope.

Design deferred by OpenSpec or `tasks.md` is out of scope; decisions made inside this
change are reviewed like code. When a fix was already prescribed (by the prompt or an
earlier review), check that it removes the cause and look for a simpler alternative,
such as changing inputs instead of adding an exception; report it as a separate
non-blocking finding.

### Severity and disposition

Every finding carries two independent labels. **Severity** says how wrong the
result is. **Disposition** says when it gets fixed. The size of the fix never sets
the severity: a one-line bug the user sees is still a WARNING.

**Severity:**

- **CRITICAL** — a user scenario does not work on a path a user hits.
- **WARNING** — observable wrong behavior, or a violation of the spec or design.
  Two code paths that break one invariant count, even when only one path is wrong
  today: a flag that offers what the action then refuses, one command writing a
  CSV field that another reads differently, a run that reports failure while the
  work goes on.
- **IMPROVEMENT** — no wrong result today, and a local, low-risk edit inside this
  change's own code or documents makes it cleaner: performance, duplication,
  conflicting sources of truth, dead or ambiguous configuration, a stale statement,
  a simpler contract. Having no current user effect does not make an item LATER.
  "Local and low-risk" excludes a product choice, a cross-module migration, mass
  formatting, environment-only churn, a byte-sensitive generated or vendored file,
  and a structural refactor.
- **LATER** — record it when real inputs do not reach the problematic path, the next
  feature owns the model, the fix needs a product decision or wider scope, or the
  remaining effect is negligible and no gate can observe it. State which of those
  reasons applies. LATER is not shorthand for "small", "optional", or "the gate is
  green".

**Not a finding:** a deferred task, a stated non-goal, and a note another pipeline
step already owns. Spec sync owns Purpose lines edited early. The PR skill owns
branch layout. List these under Sources or the manual checklist.

**Calibration examples:**

- WARNING: an HTTP error reported as success, a weekly page locked while some of
  its analyses are missing, or a run that reports failure while work continues.
- IMPROVEMENT: duplicate helpers or contracts, an LLM or API call repeated per
  paper where one per batch suffices, dead wiring, stale documentation, or a local
  unused import.
- LATER: a threshold that needs a product choice, a field owned by a future
  feature, an input that real arXiv data never produces, or floating-point noise
  rounded away by every gate.
- Not a finding: PR/branch layout, unrelated working-tree dirt, deferred manual
  tasks, and stated non-goals.

**Disposition:**

| Disposition | Rows | Who acts |
| --- | --- | --- |
| **must fix** | CRITICAL | fixed before merge |
| **fix pass** | WARNING and IMPROVEMENT whose fix is local and has one obvious answer | done in the next fix pass without asking |
| **user decision** | WARNING whose fix needs a product or design choice | the user picks an option the finding names |
| **deferred** | LATER | left undone unless the user picks it |

**Every finding** states the root cause, a concrete fix that addresses that cause,
and whether the symptom may hide a larger problem. A LATER finding adds why it is
deferred, so the user can weigh picking it. If the cause is unclear, ask the user
and keep the severity.

**A missing check is part of the fix.** When the root cause includes a missing test
or a mock that hid the defect, the fix names the test that would fail on that cause.
The row is **done** only when that test exists and goes red without the fix;
otherwise it is **partial**.

## 4. Report

Post the report in chat using this format, and write the same structure to `review.md` (§1).

```markdown
## Implementation review: <change or feature specification>

### Scope
| Base | HEAD | Diff |
| ... | ... | `base...HEAD` / uncommitted |

### Sources
- OpenSpec: ...
- Feature specification: ...
- Deferred (out of scope): ...

### Findings tracker
| Finding | Severity | Disposition | Origin | Modules | Status | Where it landed |
| C1 <short title> | CRITICAL | must fix | introduced by diff | `src/<module>.py` | **open** | — |

### Findings
#### CRITICAL
- **C1 Title** — **open** — must fix — modules: `src/<module>.py`
  `path` — why it violates the feature specification/design — root cause —
  what to do, including the test that fails on that cause — larger problem it may
  hide (or "none found")

#### WARNING
- **W1 Title** — **open** — fix pass | user decision (options: …) — modules: `<module>`
  ...

#### IMPROVEMENT
- **I1 Title** — **open** — fix pass — modules: `<module>`
  `path` — root cause — what to do — larger problem it may hide (or "none found")

#### LATER
- **L1 Title** — **open** — deferred
  root cause — what to do — why it is deferred

### Coverage gaps
What automated tests cannot catch; whether a manual run against real services exists.

### Manual check checklist
What the user should verify by hand before the re-review.

### Rounds
#### Round 1 — <date> — initial review
- Found: <finding titles>
```

**Ids.** Prefix each finding with its severity letter and a number: C, W, I, L. A
re-classified finding takes a new id, and that round's entry under **Rounds** maps
the old id to the new one.

**Modules column.** Each CRITICAL, WARNING, and IMPROVEMENT lists the module(s) that must change (`main.py`, `src/<module>.py`, `scripts/<script>`, `prompts/<file>`). LATER rows may leave it as `—`.

**Origin column.** `introduced by diff`, `pre-existing, surfaced by this change`,
`integration gap`, `found in manual check`, or `introduced by fix`.

**Status.** Initial review: every row **open**, `Where it landed` is `—`.

**After fixes**, keeping the original finding text, update `review.md`:

- Status → **done** / **partial** / **open**.
- `Where it landed` → file + line or range a human can check, one pointer per
  touched file (e.g. `` `src/<module>.py` L<a>–<b>; `main.py` L<n> ``).
- Under **Rounds**, append what was fixed in this pass (finding → status).

## 5. Manual-check bugs and re-review

**Manual-check bugs.** Each bug the user reports from manual testing becomes a new
tracker row and finding (Origin `found in manual check`, **open**) with the same
root cause / fix / larger-problem fields, noted under the current round.

**Re-review round.** Scope = changes since the previous round, within the diff
from §2. For each:

- Check the fix removes the root cause, and that the check named by a missing-test
  cause exists (§3); set status **done** / **partial** / **open**.
- Apply the axes (§3) to the fix diff; a new defect is a new finding with Origin
  `introduced by fix`.
- Append `#### Round N — <date> — re-review` under **Rounds**: what was checked,
  found, and fixed. Earlier rounds stay as written — they are the history.

The review is closed when no **must fix**, **fix pass**, or **user decision** row is **open** or **partial**, or the user accepts the rest. **Deferred** rows stay **open** and do not block closing.
