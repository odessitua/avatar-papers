---
name: /opsx-review
id: opsx-review
category: Workflow
description: Review (or re-review) implementation against OpenSpec + a feature specification, scoped to the diff against origin/main
---

Review implementation against OpenSpec change artifacts and any `@`-mentioned feature specification.

**Follow** the project skill `.cursor/skills/spec-implementation-review/SKILL.md` in full.

**Input**: Optional OpenSpec change name and/or feature-specification path (e.g. `/opsx-review weekly-slack-digest`). If omitted, infer from context or the only active change; if ambiguous, prompt. If `review.md` already exists, run the next re-review round.
