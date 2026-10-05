# Crash recovery (`/devforge:implement` PHASE 0)

This reference defines the interrupted-session recovery handled by PHASE 0 of `main.md`. A `/devforge:implement` run can be interrupted mid-task by a power loss, terminal crash, or network drop. Two artefacts make a mid-task interruption recoverable: the per-task empty checkpoint commit (`[checkpoint] pre-task NNN` in standalone mode, `[checkpoint]` in wrapper mode, PHASE 2 — created in the **source** repo) and the `.devforge/wip.md` marker (in the install root). The `**Checkpoint**` SHA the marker records is the source repo HEAD captured at task start, so recovery resets the source repo, not the wrapper.

## The WIP marker

`.devforge/wip.md` is written directly by the orchestrator: PHASE 2 writes it before each task starts, and PHASE 3 rewrites its `**Phase**` field once, when the implementing agent's dispatch returns (the `**Phase**` bullet below). PHASE 0 reads it back on the next run. `implement_helper wip-commit` clears it after the approved per-task commit, and the orchestrator removes it on `skip` / `rollback`; every other exit leaves it in place, including PHASE 7's `stop` and `fix-tooling` arms, PHASE 0's `manual`, PHASE 3's two HALTs, and any helper failure that ends the turn. It is human-readable markdown. No code parses or validates its fields: the fenced block below is the one statement of its layout, which the orchestrator follows as both writer and reader. The fields:

```markdown
# WIP Marker — /implement

**Command**: /implement
**Feature**: <feature_dir>
**Task**: <task_number>
**Title**: <task_title>
**Agent**: <agent_name>
**Phase**: <phase>
**Checkpoint**: <checkpoint_sha or "(none)">
```

- **`Command`** is MANDATORY and is always `/implement` when this command writes the marker. It is the discriminator that lets the recovery branch detect a marker left by a different command.
- **`Feature`** is the feature directory the interrupted task belongs to, held as the whole PATH — `main.md`'s `<feature_dir>`, exactly as the PHASE 1 that resolved that task reported it. The `skip` option below joins `tasks/` onto this value, so a bare directory name would not resolve. Two other artifacts carry a `**Feature**:` field holding a DIFFERENT value: the task file's, stamped by `breakdown_helper render-task-file --feature`, and `.devforge/session-state.md`'s, stamped by `implement_helper update-session-state --feature`. Both helpers stamp their flag value verbatim and join no path onto it, and both callers — `/devforge:breakdown` and this command's PHASE 7 — pass the directory's NAME. One field name, three artifacts, two values: do not unify them.
- **`Phase`** tells the `resume` option below where to re-enter the task. It holds one of exactly two values, `agent` / `verify` — this bullet is the one place that list lives, and `main.md` cites it. `agent` means PHASE 3's dispatch of the implementing agent has not returned; `verify` means it has. PHASE 2 writes `agent`; PHASE 3 rewrites it ONCE, to `verify`, when that dispatch returns — NEVER on PHASE 3's two HALTs (`main.md`'s architect guard and missing-agent fallback), which fire before any dispatch. That rewrite is the field's only advance: the later re-dispatches of the implementing agent (PHASE 5's self-repair, PHASE 6's repair leg, PHASE 7's repair arms) leave it at `verify`. The `agent` value is NOT the `**Agent**` field above, which holds the agent's name.
- **`Checkpoint`** is the **source** repo HEAD snapshotted at task start (`preflight`'s `head_sha`) — the rollback target for `rollback` and for the `skip` reset. In wrapper mode the source repo is the nested repo at `<install_root>/PROJECT_ROOT`; in standalone mode (`PROJECT_ROOT == "."`) it is the single repo. `wip.md` itself lives in the install root and records this source SHA alongside the source branch.

## Sole-detector rule

**PHASE 0 is the SOLE interrupted-session detector.** It runs once, at loop start, before the first `resolve-next-task`. Per-task preflight (PHASE 2) does NOT offer recovery — it only ASSERTS that no stale `wip.md` remains at per-task entry, and exits 2 pointing back to the recovery branch if one is unexpectedly present. This keeps recovery logic in one place; a `wip.md` reaching preflight means PHASE 0 either cleared it or ended the turn, so its presence there is an invariant violation, not a recovery opportunity.

## The four recovery options

When PHASE 0 reads a `wip.md` whose `**Command**:` is `/implement`, it asks via `AskUserQuestion` (single-line question, options `["resume", "rollback", "skip", "manual"]`):

- **`resume`** → re-enter the recorded task at the point its `**Phase**:` field selects. Rebuild context from the marker fields (`Feature`, `Task`, `Title`, `Agent`, `Checkpoint`), then continue the loop from that point: at `agent`, re-enter at PHASE 3 — a fresh dispatch of the implementing agent, handed the interrupted run's unverified working-tree edits (`rollback`, by contrast, resets to `Checkpoint` and discards those edits first); at `verify`, re-enter at PHASE 4 — the marker does not record `touched_files`, so re-capture them with `implement_helper capture-touched-files --checkpoint <Checkpoint>` — then run PHASE 5 onward, never re-entering directly at PHASE 5. Use when the interruption was transient and the working-tree edits are intact.
- **`rollback`** → `git -C <source_root> reset --hard <Checkpoint>` (in the **source** repo, discarding the empty checkpoint and any task edits), clear `wip.md`, then re-resolve from PHASE 1. Resolve `<source_root>` as `<install_root>/PROJECT_ROOT` from `.devforge/project-config.json` (`.` → standalone, source==install). Use to retry the task cleanly from its start state.
- **`skip`** → `git -C <source_root> reset --hard <Checkpoint>` in the **source** repo (so the partial edits do not bleed forward), mark the task skipped via `implement_helper mark-skipped --task-file <resolved-task-file> --index <feature>/tasks/README.md --number NNN` (the helper sets `**Status**: Skipped` in the task file and rewrites the matching `tasks/README.md` index row — it does NOT touch git or `wip.md`), then clear `wip.md`, advance to PHASE 1. PHASE 0 runs before `resolve-next-task`, so resolve the task file by globbing `<Feature>/tasks/<Task>-*.md` from the marker's `Feature` + `Task` number (match the number prefix; do not reconstruct the slug). `resolve-next-task` treats `Skipped` as satisfied for dependency resolution, so downstream tasks are not permanently blocked.
- **`manual`** → keep all state and `wip.md` in place; end the turn for hand inspection. Use when the working tree needs a human look before deciding.

A reply that picks none of these four options — one that hands the choice back to the orchestrator, or free text that names no option — is not a pick: PHASE 0 asks the same question once more, and if the second reply again picks none, it takes `manual` and touches nothing.

## Command-mismatch detection

When PHASE 0 reads a `wip.md` whose `**Command**:` is anything OTHER than `/implement` (a marker left by a different command), it does NOT proceed. It tells the user a previous session of a different command was interrupted and to resolve that session first, then ends the turn. Running `/devforge:implement` against another command's marker would corrupt that command's recovery state — the mismatch guard prevents it.
