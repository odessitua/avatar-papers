---
name: /pr
id: pr
category: Workflow
description: Open a PR from the feature branch against origin/main
---

**Follow** the project skill `.cursor/skills/pr/SKILL.md` in full.

**Input**: Optional task name (e.g. `/pr weekly-slack-digest`). That argument is the task, and the branch is `feature/<task-name>`. An explicit branch name applies only when the user states one separately. If the task name is omitted, infer it from context; if ambiguous, prompt.
