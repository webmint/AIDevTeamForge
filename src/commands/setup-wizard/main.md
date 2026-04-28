---
name: setup-wizard
description: Project initialization wizard
disable-model-invocation: true
---

# /setup-wizard — Project Initialization Wizard

## Execution Flow

Execute Preflight, then each phase in order. When a phase points to a reference file, **read it fully before executing.** Do not attempt any step from memory or guesses.

### Preflight — Reset helper state

```bash
.devforge/lib/detect_report reset
.devforge/lib/wizard_render reset
```

### Phase 1 — Detection

**Read `references/detect.md` and follow it** to scan the target project and produce the detection report for downstream phases.

### Phase 2 — Questions

**Read `references/questions.md` and follow it** to ask the project's setup questions and capture the answers for downstream phases.

### Phase 3 — Population

**Read `references/populate.md` and follow it** to substitute the gathered answers and detection values into template files.

### Phase 4 — Agent Curation

**Read `references/agents.md` and follow it** to select and populate agents from the gathered answers and detection values.
