---
name: /opsx-refine
id: opsx-refine
category: Workflow
description: Refine completed OpenSpec artifacts against the current codebase before implementation
---

Refine an OpenSpec change after planning and before implementation:

```text
planning artifacts → refine → apply
```

Follow `.cursor/skills/openspec-refine-change/SKILL.md` in full.

**Input**: Optional change name, for example `/opsx-refine add-auth`. If the
change cannot be inferred unambiguously, prompt using `openspec list --json`.
