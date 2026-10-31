---
name: openspec-refine-change
description: Refines completed OpenSpec planning artifacts against the current codebase before implementation and chooses the best project-fitting solution at each stage (scope, behavior, design, tasks). Use when the user asks to review, analyze, improve, or refine an OpenSpec change or invokes /opsx-refine.
license: MIT
compatibility: Requires openspec CLI.
---

# Refine an OpenSpec change

Check completed planning artifacts against the actual codebase, choose the best
solution this project supports at every planning stage, then improve the
artifacts before implementation:

```text
planning artifacts → refine → apply
```

Refinement edits OpenSpec planning files only; code and tests change in apply.

## 1. Select and load the change

Use the supplied change name. Otherwise infer it only from unambiguous context
or when exactly one active change exists. If ambiguous, run
`openspec list --json` and ask the user to select.

Run:

```bash
openspec status --change "<name>" --json
openspec instructions apply --change "<name>" --json
```

Use the returned paths and `contextFiles` as the source of the repository layout.
If required planning artifacts are missing, stop and direct the user to
`/opsx-continue <name>`.

Read every planning artifact in `contextFiles`. For delta specs, also read the
corresponding main specs so refinement does not remove existing requirements.

## 2. Load project constraints

The best solution is relative to this project, so collect its constraints
before judging the plan:

- For each artifact id in the status `artifacts` list, run
  `openspec instructions <artifact-id> --change "<name>" --json` and read
  `context`, `rules`, and `instruction`. The context carries project facts such
  as area ownership, change-size limits, and workflow; rules and instructions
  define what each artifact must contain.
- Read project guidance for the affected areas: agent rules, contributing
  guides, and area READMEs.
- Note the tooling each area actually has: test runners, lint and type-check
  commands, browser or rendering harnesses, and packaging and release flow.
- Check other active changes for overlapping areas or conflicting decisions,
  and recent archived changes in the same capabilities for decisions and
  deferred follow-ups this change must honor.

A plan that violates a project constraint needs either a correction or an
explicit justification in the artifact that owns the choice.

## 3. Inspect relevant code

Derive the affected areas from the artifacts and discover workspace boundaries
from the available project configuration.

For each affected area:

1. Read the relevant implementation and its important callers and callees.
2. Find usages of changed APIs, events, persisted fields, and shared constants.
3. Look for existing behavior that should be reused instead of duplicated.
   Search domain concepts as well as identifiers.
4. Trace every data flow the change touches from producer to final consumer,
   across packages or services, and note who builds each input the new code
   receives.
5. Enumerate entry paths into the changed behavior, including rare ones:
   multi-selection, empty input, missing versus unknown values, defaults,
   repeated or concurrent actions, failures, and destructive operations.
6. For shared or published interfaces, list the real consumers, how they pin
   versions, and how they are deployed.
7. Read nearby tests and compare their setup with the production path.

Code is evidence about architecture and constraints, not the source of product
requirements; a requirement keeps its strength when current code differs.

## 4. Evaluate the solution at each stage

Go through the stages in order — proposal, specs, design, tasks — because an
earlier choice constrains the later ones. At each stage:

1. State the plan's current choice in one sentence.
2. Build candidates from the evidence in steps 2–3: the current choice, the
   smallest change that still delivers the intent, reuse of an existing
   mechanism when one exists, and any materially different option the code
   suggests. Every candidate is a real option implementable in this codebase.
3. Compare the candidates against the criteria below.
4. Keep, adjust, or replace the current choice. When the evidence cannot pick
   a winner and the choice changes intent, scope, or architecture, note it as
   a blocking decision for step 5 and continue with the remaining stages.

Scale the depth to the change: a single-area fix may need one sentence per
stage; a cross-area change needs explicit candidates for every material
decision.

Criteria, in priority order:

1. **Fit** — satisfies every requirement and scenario, including the edge paths
   from step 3.
2. **Project fit** — respects the constraints from step 2. In areas the project
   marks as owned by others or change-restricted, prefer the smallest diff that
   follows upstream conventions.
3. **Reuse** — extends the implementation that already owns the responsibility
   instead of adding a parallel one, in the layer that owns it.
4. **Footprint** — fewest areas, files, public interfaces, and new abstractions.
   A new abstraction needs callers in this change.
5. **Verifiability** — testable at the real integration boundary with tooling
   the area already has.
6. **Risk** — compatibility, migration, rollout, and rollback. Version and
   release choices match the real consumers from step 3.

Stage checks:

- **Proposal** — Does the problem exist in current code? Is the scope the
  minimum that delivers the intent? Could an existing feature, setting, or
  asset solve it? Is every touched area necessary?
- **Specs** — Is each requirement observable and testable? Are defaults,
  missing versus unknown input, failures, compatibility, and the edge paths
  from step 3 specified? Does any requirement force an implementation choice
  that belongs in design?
- **Design** — Does each decision name the chosen option, the rejected
  alternatives, and code-grounded reasons? Is logic placed in the owning layer?
  Does one-time tooling drive a permanent interface? Are version and release
  choices justified by real consumers?
- **Tasks** — Are tasks ordered by dependency, with producers before consumers
  and behavior-neutral steps before behavior changes? Does every requirement
  and scenario have implementation and verification tasks? Do tests exercise
  the new code with inputs built by the production producer, not only
  hand-built fixtures? Are manual checks listed for what automation cannot see?

## 5. Ask only blocking questions

Questions are a last resort, not an interview. Ask only when both hold:

- the evidence from steps 2–4 cannot settle the decision; and
- the answer would change the specs, the approach, or the task breakdown.

Typical blocking decisions: product intent or scope, a choice between
materially different architectures, discarding or weakening a requirement, and
behavior the requirements leave open that the code does not decide.

Settle without asking:

- what code, specs, project guidance, or archived changes already answer —
  look it up;
- what an earlier refinement or an artifact decision already settled, unless
  new evidence contradicts it;
- a clear, evidence-backed correction — make it and report it;
- naming, wording, file layout, or other choices that leave behavior unchanged;
- a preference when one candidate clearly wins on the step 4 criteria.

If nothing is blocking, ask nothing and go to step 6. Otherwise:

1. Collect every blocking decision from all stages first. Drop the ones another
   answer would settle, and order the rest by stage.
2. Ask one decision per question, with two or three concrete options, the
   evidence for each, and the recommended option first. Use the structured
   question tool when one is available.
3. Ask independent questions together in a single round. Ask a dependent
   question only after its prerequisite is answered, and only if it is still
   blocking. A second round is the exception; a third needs a new blocking
   decision that an answer opened.
4. Record each answer in the artifact that owns it — a design decision with the
   rejected options, or a requirement and its scenarios — not as a Q&A log.

A skipped or unanswered question stays an unresolved decision with its
recommendation, and the change stays `BLOCKED` until it is settled.

## 6. Refine the artifacts

Check and correct:

- ambiguous, conflicting, duplicated, or untestable requirements;
- inconsistencies between intent, specifications, design, and tasks;
- designs that conflict with current architecture or duplicate existing logic;
- missing API, persistence, compatibility, failure, or default behavior;
- requirements and scenarios not covered by implementation or test tasks;
- unclear task ownership, ordering, dependencies, or verification;
- every choice step 4 adjusted or replaced.

For the `spec-driven` schema, put:

- intent and scope in `proposal.md`;
- observable behavior and scenarios in delta specs;
- architecture, trade-offs, and excluded options in `design.md`, with each
  decision recording the chosen option and the rejected alternatives in the
  decision format the change already uses;
- implementation and verification work in `tasks.md`.

For other schemas, follow the ownership described by their OpenSpec artifact
instructions.

Correct the source artifacts directly; a separate findings file exists only if
the selected schema defines one. Keep any index the
change maintains, such as a change-root README, consistent with the refined
artifacts. When a document outside the change that the artifacts cite as a
source becomes stale, add a task to update it instead of editing it.

Every edit traces to a finding. When the change
was refined before, change only what new evidence contradicts.

Make clear, evidence-backed corrections without asking. Change product intent
or scope, pick between materially different architectures, or discard a
requirement only as answered in step 5.

## 7. Validate and report

Re-read the changed artifacts, verify requirement-to-task coverage, and run:

```bash
openspec validate "<name>" --type change --strict --no-interactive
```

Inspect the diff and confirm all writes are limited to planning artifacts for
the selected change.

The change is `READY` when validation passes, every requirement and scenario
maps to tasks, and no unresolved decision would change the specs, the
approach, or the task breakdown. Otherwise it is `BLOCKED`; state what
unblocks it.

Report:

- a plain-language summary: the problem, the chosen solution, and why it beats
  the strongest alternative, readable without opening the code;
- code areas inspected;
- stage evaluation: for each stage, the current choice, the strongest
  alternative considered, the verdict (kept, adjusted, replaced, or needs a
  decision), and the evidence;
- artifacts changed and material corrections;
- decisions settled by the user in step 5 and where each is recorded;
- unresolved decisions, each with options and a recommendation;
- validation result;
- `READY` or `BLOCKED` for `/opsx-apply <name>`.

Keep the report in chat unless the selected schema defines a report artifact.
