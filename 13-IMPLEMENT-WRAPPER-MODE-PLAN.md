# 13-IMPLEMENT-WRAPPER-MODE-PLAN

**Status**: **DONE / SHIPPED in code (verified 2026-06-18)** on `develop-2.0-init`. The prior "DRAFTED, NOT STARTED" / "follow-on — see plan for status" framing was stale: wrapper mode is a fully shipped cross-cutting feature, not a pending follow-on. Evidence in the live tree (verify on read): the resolver `src/devforge/lib/_implement/_workspace.py` is real (`resolve_workspace(install_root) -> Workspace` with `install_root` / `source_root` / `is_wrapper`, fail-soft to standalone), and there are 75 wrapper references across `_implement/` (`_cmds_capture` / `_cmds_preflight` / `_cmds_verify` / `_cmds_commit` / `_cli` thread the source-vs-install split). `src/devforge/lib/_configure/_render.py` actually POPULATES `{{WRAPPER_MODE_SECTION}}` (template emitted when `workspace_mode == "wrapper"`). The pipeline preflights detect the wrapper marker (`_review` / `_grill` / `_summarize` / `_generate_docs` / `_verify` `_preflight.py`). `src/commands/implement/main.md` wires wrapper mode (9 mentions). The per-phase boards below are retained as the build record; only the user-driven testForge20 wrapper e2e (Phase 9) remains the standing manual gate.
**Branch**: `develop-2.0-init`
**Driver**: `/implement` (built in `07-EXECUTE-TASK-REDESIGN-PLAN.md`, Phases 0–12 shipped) assumes a **single git repo**. The first live wrapper-mode run on testForge20 (2026-06-02) hit a hard wall: the source code lives in a **separate nested git repo** (`db-cse-ui-strata/`, branch `bugfix/MIG-123`), while the wrapper/install repo (`testForge20`, branch `spec/001-…`) tracks only forge artifacts (`.devforge/`, `specs/`, `audits/`). `/implement`'s checkpoint, `capture-touched-files`, `verify-touched`, and `wip-commit` all targeted the **wrapper** repo — so capture returned ~80 pre-existing forge-artifact files + `db-cse-ui-strata` as one untracked dir entry (never the actual changed source file), verify would run over the wrong file set, and commit would stage unrelated forge churn while never committing the source change. The run correctly stopped before verify. This plan adds the **two-repo split** so `/implement` works in wrapper mode while preserving standalone behavior.

## What the live run proved (the precise gap)

`07` half-implemented wrapper mode:
- ✅ `_cmds_commit.py` — wrapper commit-message format (`[TICKET-ID] - …`) + `WORKSPACE_MODE`/`COMMIT_ATTRIBUTION` read.
- ✅ `_cmds_verify.py` — referenced a "baked `cd SOURCE_ROOT &&` prefix" assumption.
- ❌ **Repo targeting** — checkpoint, `capture-touched-files`, the verify cwd, and the stage/commit target all use the install/wrapper root, never the source repo.
- ❌ The "baked prefix" assumption is **false for this config**: `PACKAGE_STACKS[*].type_check_command` is bare (`"npm run check"`, path `"."`) — no `cd` prefix. Verify must run these with **cwd = source root**, not re-prefix.

Config ground truth (testForge20 `.devforge/project-config.json`):
- `PROJECT_ROOT = "db-cse-ui-strata"` — the source root, **relative to the install root**. (Standalone installs have `PROJECT_ROOT = "."`.)
- `PACKAGE_STACKS` paths are **source-root-relative** (e.g. `"."`, package subpaths).
- `WRAPPER_MODE_SECTION` present; CLAUDE.md "Source code lives at `db-cse-ui-strata/`".

## Design

### The two-repo split (responsibility table)

| Operation | Repo / root |
|---|---|
| pre-task checkpoint (`git commit --allow-empty`) + rollback target | **source** repo (`<install>/<PROJECT_ROOT>`) |
| `capture-touched-files` (`git -C <source> diff`) | **source** repo; returns **source-relative** paths |
| `verify-touched` (tsc/lint/build) | run with **cwd = source root**; file list + `PACKAGE_STACKS` both source-relative |
| per-task WIP commit of the code | **source** repo, on its branch (`bugfix/MIG-123`) |
| preflight branch check (refuse main/default) | **source** repo (that's where code commits land) |
| `mark-complete` (task `Status`, `README` index) | **wrapper** repo (`specs/` are wrapper artifacts) — file edits only |
| `.devforge/wip.md` marker, session-state, memory | **wrapper** repo |
| `resolve-next-task` (reads `specs/`, breakdown-handoff) | **wrapper** repo — unchanged |
| CBM `detect_changes` refresh | **source** code (the indexed project); stamp in `.devforge` (wrapper) |

**Standalone is the degenerate case**: when `PROJECT_ROOT == "."`, source root == install root, single repo — exactly today's behavior. The resolver makes wrapper a generalization; **standalone must not regress** (the existing 447 `_implement` tests are the guard).

### Settled decisions (2026-06-02)

- **D1 — per-task commit stream**: on `approve`, only the **source** change commits (to the source repo on its branch). The **wrapper artifact updates** (`mark-complete`'s `Status: Complete` + index) are written to disk but **NOT committed per task** — the wrapper tree is already heavily dirty from `/specify`//`plan`//`breakdown`//`audit`, and auto-committing it per task would sweep all that in. (User-confirmed via "draft".) Source WIP commits accumulate on the source branch and are squashed by `/finalize` (source repo), matching the legacy `execute-task` "Source Repo Auto-Commit" model.
- **D2 — ticket-id source**: in wrapper mode the `[TICKET-ID]` for the commit message derives from the **source** repo's branch (`bugfix/MIG-123` → `MIG-123`), not the wrapper's `spec/001-…` branch.
- **D3 — checkpoint_sha semantics**: `wip.md`'s checkpoint SHA is the **source** repo HEAD (the rollback target). Rollback (`skip`/recovery) runs `git -C <source> reset --hard <sha>`.

### Ported from the proven 1.x design (`main:.claude/commands/execute-task.md`)

1.x handled wrapper mode correctly because it was **prose-driven**: the command instructed the LLM to run `git -C $SOURCE_ROOT …` for every source op (checkpoint / `add` / commit / reset / `rev-parse` / `branch`). 2.0's helper-ization dropped that. This plan ports the 1.x model **into the helpers** (keeping 2.0's testable, deterministic helper-owns-shape architecture rather than reverting to unfalsifiable prose). Three 1.x safeguards my first draft was missing, now folded in:

- **Dirty-source-repo warning at preflight** (1.x line 153): if the source repo has pre-existing uncommitted changes at task start, warn the user before proceeding — otherwise the checkpoint baseline is muddied. → Phase 3.
- **Wrapper-isolation check at verify** (1.x line 259): after the agent edits, verify NO Claude artifacts (`.claude/`, `specs/`, `docs/`, `constitution.md`, `CLAUDE.md`, `.mcp.json`, …) were written *inside* the source root (the agent must not pollute the source repo with forge files). → Phase 4.
- **`git add -A` in source vs precise staging** (1.x line 38 used `git -C $SOURCE_ROOT add -A`): 1.x committed everything in the otherwise-clean source repo. This plan keeps **precise `touched_files` staging** (D1) instead — it is *superior* to `add -A` here because it stages only the task's files even if the source repo is dirty (the dirty-source warning then becomes advisory, not a correctness dependency). The 1.x `add -A` model is the documented fallback if precise capture ever proves unreliable.

### The resolver (single source of truth for repo targeting)

New `src/devforge/lib/_implement/_workspace.py`:
- `resolve_workspace(install_root) -> Workspace` where `Workspace` = `{install_root: Path, source_root: Path, is_wrapper: bool}`.
- Reads `<install_root>/.devforge/project-config.json` → `PROJECT_ROOT`. `source_root = install_root / PROJECT_ROOT` (resolves to `install_root` when `PROJECT_ROOT == "."`). `is_wrapper = (PROJECT_ROOT.strip() not in ("", "."))`.
- Fail-soft: if config is missing/unreadable, return standalone (`source_root == install_root`, `is_wrapper False`) — so a non-configured repo behaves as today, not a crash.
- Every repo-targeting command (`capture`, `verify`, `commit`, plus the orchestrator's checkpoint/rollback) goes through this — no ad-hoc `PROJECT_ROOT` reads scattered across helpers (DRY; mirrors how `_cmds_gate` imports `RULE_TO_VERB` from one place).

---

## Phase 0 — Confirm gap + freeze decisions

**Owner**: orchestrator (done 2026-06-02; recorded above). No code.

- Gap confirmed via live testForge20 run + config inspection. D1–D3 settled. Standalone-no-regress is the hard constraint.

---

## Phase 1 — `_workspace.py` resolver

**Owner**: python-engineer → python-reviewer.

### Files
- `src/devforge/lib/_implement/_workspace.py` — `Workspace` dataclass (frozen) + `resolve_workspace(install_root) -> Workspace`. Stdlib only; 3.8+ typing. Fail-soft to standalone on missing/bad config.
- `tests/lib/_implement/test_workspace.py` — standalone (`PROJECT_ROOT="."` → source==install, is_wrapper False); wrapper (`PROJECT_ROOT="db-cse-ui-strata"` → source==install/db-cse-ui-strata, is_wrapper True); missing config → standalone fail-soft; `PROJECT_ROOT` absent/empty → standalone.

### Verify
```bash
python3 -m pytest tests/lib/_implement/test_workspace.py -v
```

---

## Phase 2 — `capture-touched-files` → source repo

**Owner**: python-engineer → python-reviewer.

### Files
- `src/devforge/lib/_implement/_cmds_capture.py` — resolve the workspace; run `git -C <source_root> diff --name-only <checkpoint-sha>` + `git -C <source_root> status --porcelain` for untracked. Emit **source-root-relative** paths (the form `PACKAGE_STACKS` + `verify` + `wip-commit` all expect). `--root` stays the install root (the helper resolves source from it).
- `tests/lib/_implement/test_cmds_capture.py` — extend: a **wrapper fixture** (install repo with a nested source git repo at `PROJECT_ROOT`); a source-file change + an unrelated install-root change → capture returns ONLY the source-relative changed file, NOT the install/forge churn nor the nested dir as one entry. Keep the standalone tests green.

### Verify
```bash
python3 -m pytest tests/lib/_implement/test_cmds_capture.py -v
```

---

## Phase 3 — `preflight` → source HEAD + source branch check

**Owner**: python-engineer → python-reviewer.

### Files
- `src/devforge/lib/_implement/_cmds_preflight.py` — in wrapper mode: snapshot the **source** repo HEAD as `head_sha`; run the branch-refuse check (main/master/trunk + origin default) against the **source** repo (where commits land). **Dirty-source warning** (ported from 1.x line 153): if `git -C <source> status --porcelain` shows pre-existing uncommitted changes, emit a warning in the preflight JSON/stderr (advisory, not a hard stop — precise staging means it won't corrupt the commit, but the user should know the source repo wasn't clean at task start). Constitution + memory digests stay read from the install root (`.devforge/`, `constitution.md` are wrapper artifacts). Standalone: unchanged (source==install).
- `tests/lib/_implement/test_cmds_preflight.py` — wrapper fixture: source repo on a feature branch → preflight passes + `head_sha` is the source HEAD; source repo on `main` → refused (even if the wrapper is on a feature branch); pre-existing uncommitted source changes → dirty-source warning present in output; standalone cases unchanged.

### Verify
```bash
python3 -m pytest tests/lib/_implement/test_cmds_preflight.py -v
```

---

## Phase 4 — `verify-touched` → run in source root (correct the baked-prefix assumption)

**Owner**: python-engineer → python-reviewer.

### Files
- `src/devforge/lib/_implement/_cmds_verify.py` — resolve the workspace; run each `PACKAGE_STACKS` command with **cwd = source_root** (the config commands are bare, e.g. `npm run check`, path `.` — NOT pre-prefixed). Longest-path-prefix match the source-relative touched files against `PACKAGE_STACKS` (source-relative paths). Drop / correct the "prefix already baked" comment + logic. **Wrapper-isolation check** (ported from 1.x line 259): in wrapper mode, scan the source root for forge artifacts that must NOT be there (`.claude/`, `specs/`, `docs/overview.md`, `docs/architecture.md`, `constitution.md`, `CLAUDE.md`, `bugs/`, `research/`, `.mcp.json`) — if the agent wrote any into the source repo, flag a verification failure (the agent polluted the source tree). Self-repair counter unchanged. Standalone: cwd == install root, isolation check skipped (no separate source root).
- `tests/lib/_implement/test_cmds_verify.py` — wrapper fixture: a source file under package `.` → its command runs with cwd=source_root (assert via an echo-cwd fake command); non-package source file → primary-stack fallback run in source_root; a forge artifact (e.g. `CLAUDE.md` / `specs/`) planted in the source root → wrapper-isolation check flags a verification failure. Standalone tests green (isolation check skipped).

### Verify
```bash
python3 -m pytest tests/lib/_implement/test_cmds_verify.py -v
```

---

## Phase 5 — `wip-commit` → source repo, source-only staging

**Owner**: python-engineer → python-reviewer.

### Files
- `src/devforge/lib/_implement/_cmds_commit.py` — resolve the workspace. In wrapper mode: stage ONLY the source `touched_files` in the **source** repo (`git -C <source> add -- <files>`); commit in the source repo; ticket-id from the **source** branch (D2); clear `wip.md` in the install root. **Do NOT stage the task file / index** in wrapper mode (D1 — those are wrapper artifacts, left uncommitted; `mark-complete` already wrote them to disk). Standalone: unchanged (single repo stages source + task file + index together, as today). Capture new **source** HEAD into the emitted JSON.
- `tests/lib/_implement/test_cmds_commit.py` — wrapper fixture: only the source file lands in the source repo's commit; the install/forge churn + task file stay uncommitted in the wrapper; message uses the source-branch ticket-id; standalone message+staging unchanged.

### Verify
```bash
python3 -m pytest tests/lib/_implement/test_cmds_commit.py -v
```

---

## Phase 6 — Recovery / rollback → source repo

**Owner**: instruction-author → instruction-reviewer (spec); python-engineer → python-reviewer (if a rollback helper is added beyond raw git).

### Files
- `src/commands/implement/main.md` — Phase 0 recovery branch + Stage-B/Stage-A `skip` paths: `git reset --hard <checkpoint_sha>` runs in the **source** repo (`git -C <source_root>`). `wip.md` (install root) records the source checkpoint SHA + the source branch; the `Command` mismatch logic is unchanged. State which repo each git op targets.
- `src/commands/implement/references/crash-recovery.md` — note the source-repo rollback target in wrapper mode.

### Verify
```bash
grep -nE "source repo|<source_root>|git -C" src/commands/implement/main.md src/commands/implement/references/crash-recovery.md
```

---

## Phase 7 — Orchestration spec (`main.md`): checkpoint, dispatch paths, CBM on source

**Owner**: instruction-author → instruction-reviewer.

### Files
- `src/commands/implement/main.md`:
  - **Checkpoint** (Phase 2 step): create `git -C <source_root> commit --allow-empty -m "[checkpoint] pre-task NNN"`; record the **source** SHA. (Resolve `<source_root>` = install-root `/` `PROJECT_ROOT` from config; state how.)
  - **Agent dispatch** (Phase 3): the implementing agent edits **source** files — give it source-rooted paths (`<source_root>/<touched_file>`). The `touched_files` from the handoff are source-relative; the agent operates under the source root. (In testForge20 the architect correctly edited the source file already — formalize that the brief is source-rooted.)
  - **CBM refresh** (Phase 8 step): `mcp__codebase-memory-mcp__detect_changes` targets the **source** code (the indexed project); `cbm_sync_helper write` stamp stays in `.devforge` (install root).
  - A short **Workspace resolution** preamble: at loop start (after preflight), resolve `source_root` from `.devforge/project-config.json` `PROJECT_ROOT` (`.` → standalone, source==install) and use it for all source-repo git/verify ops; `specs/` + `.devforge/` ops stay at the install root.
- Sentence-level discipline; every git op names its repo.

### Verify
```bash
grep -nE "source_root|PROJECT_ROOT|Workspace resolution|git -C" src/commands/implement/main.md
```

---

## Phase 8 — Re-copy into testForge20 (surgical, additive)

**Owner**: orchestrator.

### Procedure
- Copy verbatim: `src/devforge/lib/_implement/` (now incl. `_workspace.py` + the updated capture/verify/commit) → `~/Projects/private/testForge20/.devforge/lib/_implement/` (exclude `__pycache__`).
- Re-emit + copy the command: `generate.sh` to tmp → `implement.md` (+ `implement/references/`) → testForge20 (0-placeholder check first, as in `07` Phase 11).
- **Pre-clean the stranded state** (per the live run): drop the empty `[checkpoint] pre-task 001` commit in the wrapper repo + remove `~/Projects/private/testForge20/.devforge/wip.md`, so a fresh `/implement` starts clean.

### Verify
```bash
T=~/Projects/private/testForge20
python3 "$T/.devforge/lib/implement_helper.py" --help >/dev/null && echo "helper ok"
python3 -c "import sys; sys.path.insert(0,'$T/.devforge/lib'); from _implement._workspace import resolve_workspace; print(resolve_workspace('$T'))"
# expect: Workspace(... source_root=.../db-cse-ui-strata, is_wrapper=True)
```

---

## Phase 9 — testForge20 wrapper e2e smoke (empirical stop)

**Owner**: user-driven manual e2e.

### Procedure
1. Restart Claude Code in testForge20; run `/implement` (2 tasks pending from the existing breakdown).
2. Observe:
   - Workspace resolves source_root = `db-cse-ui-strata`; preflight checks the **source** branch (`bugfix/MIG-123`), snapshots source HEAD; empty checkpoint lands in the **source** repo.
   - Agent edits the source file; `capture-touched-files` returns the single source-relative file (NOT forge churn).
   - `verify-touched` runs `npm run check`/`lint` with cwd = `db-cse-ui-strata`.
   - Hard gate shows the **source** diff; on `approve` the per-task commit lands in the **source** repo on `bugfix/MIG-123` (message `[MIG-123] - …`); the wrapper's `specs/…` task `Status: Complete` is written but **uncommitted**.
   - CBM `detect_changes` refreshes the source index; loop advances to task 002; then the all-complete message.
3. Document at `IMPLEMENT-WRAPPER-SMOKE-2026-MM-DD.md`.

### Stop criteria
- Source change commits to the source repo on its branch; wrapper forge churn never swept into it.
- Standalone behavior unaffected (spot-check the 447 `_implement` tests still green).
- The full 2-task loop drains with the hard gate pausing each task.

---

## Out of scope
- `/finalize` wrapper-mode squash of the source repo's accumulated WIP commits — `/finalize` is a separate command (own plan); this plan only ensures `/implement` produces the per-task source WIP commits it will squash.
- Committing wrapper artifacts (task status/index) — deliberately left uncommitted per D1; if a future need arises, a separate "wrapper-artifact commit" step is its own decision.
- Multi-source-repo wrappers (more than one nested source repo) — current model assumes one `PROJECT_ROOT`.
- Re-deriving the `PACKAGE_STACKS` path convention — taken as-is (source-root-relative).

## When resuming work
1. Read this plan + `07-EXECUTE-TASK-REDESIGN-PLAN.md` "Wrapper-mode awareness" + the testForge20 config (`PROJECT_ROOT`, `PACKAGE_STACKS`, `WRAPPER_MODE_SECTION`).
2. Build Phase 1 (`_workspace.py`) first — everything else threads through it.
3. Each helper phase: python-engineer → python-reviewer; the wrapper fixture (install repo + nested source git repo) is the key new test shape. **Standalone tests must stay green at every phase** (no regression — that's the safety net).
4. Phases 6–7 (spec): instruction-author → instruction-reviewer.
5. Phase 8 re-copy mirrors `07` Phase 11/12 (surgical, additive, 0-placeholder check, lib glob ships helpers).
6. Phase 9 is the empirical stop — not DONE until the testForge20 source commit lands on `bugfix/MIG-123` with no forge churn.

## Related plans
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` — builds `/implement` (single-repo); this plan completes its wrapper-mode support. Once shipped, update `07`'s "Wrapper-mode awareness" note to point here.
- Legacy `src/_pending/commands/execute-task.md` "Source Repo Auto-Commit (Wrapper Mode)" — pattern reference for the two-repo commit model (the design this plan restores).
</content>
</invoke>
