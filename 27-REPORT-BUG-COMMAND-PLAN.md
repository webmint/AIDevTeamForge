# 27 — `/report-bug` Command (the defer arm) PLAN

**Status:** BUILD COMPLETE (uncommitted; full-suite confirm + user go on commits pending) — 2026-06-19 on `develop-2.0-init` via agent workflow. Phases 0–3 built behind engineer/author→reviewer loops (emitter Python edit got its own python-reviewer pass after a mid-run script fix). Carried-forward findings closed: stale `src/_pending/commands/report-bug.md` deleted; `src/CLAUDE.md:58` "or the user declines" hallucination reworded; unused `Optional` import removed from `_shared/bug_file.py`; slug-contract test strengthened to a full-filename assertion; CHANGELOG `[Unreleased]` entry added. Phase 4 = full `tests/` suite (running) + install-ride; Phase 5 testForge20 e2e = user-driven HARD GATE (deferred). Pre-existing out-of-scope finding surfaced: `DEVELOPMENT-STATUS.md` is systemically stale (its `report-bug.md` entry + the redesigned-command entries describe pre-pivot drafts) — a separate refresh, not this plan's scope.

## Why this exists

The framework already assumes a "file a bug to defer" arm but never built it:

- `src/CLAUDE.md` "Conversational fix-or-file offer" and `/fix` (plan 26, D4) both say filing is a **separate** command — `/fix` writes NO `bugs/` file.
- `src/devforge/storage-rules.md` already documents `bugs/`, the bug-file format (lines ~267–310), the `Open → In Progress → Fixed` lifecycle, and lists `report-bug → creates bugs/NNN-description.md` (line 158).
- A working bug-writer already exists at `src/devforge/lib/_verify/_bugs.py::file_bugs(...)` (used by `verify_helper file-bugs`) — but it **hardcodes `**Source**: verify`** (line 185).
- Only a stale draft sits in `src/_pending/commands/report-bug.md`; nothing is emitted, so the offered "file" arm has no command behind it.

This plan builds `/report-bug` as that defer arm, reusing the existing writer.

## Settled decisions

- **D1** — command name `/report-bug` (matches `storage-rules.md` + the draft; zero rename churn).
- **D2** — pure capture, **agent-free at runtime**; `/research` owns diagnosis. The command only records the bug and points forward to `/research`/`/specify`.
- **D3** — the system PROPOSES filing **by routing state, not a size metric**: any real, code-confirmed defect that won't be remediated now (out-of-fix-window defects → file-only; in-window defects the user declines to `/fix`; `/fix` scope-bounces the user declines to `/specify`). No LOC/file-count threshold. Reuses the existing `fix_helper in-fix-window` window check; `/report-bug` is the always-available file-only fallback.
- **D4** — reuse the writer by **extracting `file_bugs` into `src/devforge/lib/_shared/bug_file.py`** and adding a `source="verify"` default param (replaces the hardcoded Source line). `/verify` stays byte-identical (defaults to `verify`); `/report-bug` passes `source="manual"`. Avoids a cross-command import (`_report_bug` → `_verify`); `_shared/` is the established home (flat layout: `feature_scope.py`, `findings_schema.py`, …). Mirrors plan 22 Phase 0.

## Phases

### Phase 0 — Extract the shared bug-writer
- Move `file_bugs` (+ helpers `_scan_highest_bug_number`, `_slugify`, `_format_bug`) from `src/devforge/lib/_verify/_bugs.py` → `src/devforge/lib/_shared/bug_file.py`.
- Add `source="verify"` parameter to `file_bugs` and thread it into `_format_bug`, replacing the hardcoded `**Source**: verify`.
- **Delete** `_verify/_bugs.py`; re-point `_verify/_cli.py` import (`from ._bugs import file_bugs` → `from .._shared.bug_file import file_bugs`).
- Find ALL importers of `_verify._bugs` / `file_bugs` (grep) and update them. Relocate any `tests/lib/_verify/test_bugs.py` to `tests/lib/_shared/test_bug_file.py`, update imports.
- Add tests for the new `source` param in `tests/lib/_shared/`.
- **Verify:** `tests/lib/_shared` green; `tests/lib/_verify` green (no regression — verify defaults to `source="verify"`, byte-identical output); a `source="manual"` test renders `**Source**: manual`.

### Phase 1 — `_report_bug/` helper subpackage + launcher
- `src/devforge/lib/_report_bug/_cli.py` with two verbs:
  - `preflight` — resolve the `bugs/` dir under the correct root using the wrapper-mode resolver (`_implement/_workspace.resolve_workspace`, same as `/fix`); bugs/ is an artifact → lives under `install_root` (wrapper root in wrapper mode). Emit JSON `{bugs_dir, root, is_wrapper}`.
  - `write-bug` — args `--bugs-dir`, `--date YYYY-MM-DD` (required; never call the clock), `--description` (required), `--title` (default = description), `--severity` (Critical|Warning|Info, default Warning), `--file` (optional; if missing on disk, warn to stderr but continue). Build a single issue dict and call `_shared.bug_file.file_bugs(bugs_dir, [issue], feature_spec_path="N/A", date, source="manual")`. Emit the written path as JSON.
- `src/devforge/lib/report_bug_helper.py` + `src/devforge/lib/report_bug_helper` (POSIX shim) — mirror `fix_helper{,.py}` exactly (swap `_fix._cli` → `_report_bug._cli`, `fix_helper.py` → `report_bug_helper.py`).
- Tests in `tests/lib/_report_bug/` for both verbs (round-trip `write-bug` through the real shared writer; assert numbering, slug, Source: manual, file-table row, default severity).
- **Verify:** `tests/lib/_report_bug` green; `report_bug_helper write-bug` produces a correct `bugs/NNN-*.md`.

### Phase 2 — Command spec `src/commands/report-bug/main.md`
- Rewrite the `_pending` draft to live shape. Frontmatter (`disable-model-invocation: true`, `allowed-tools` listing `report_bug_helper preflight` + `write-bug`), modeled on `src/commands/fix/main.md`.
- Phases: parse `$ARGUMENTS` (description + `--file` + `--severity`) → `preflight` (resolve bugs-dir) → `write-bug` (orchestrator supplies today's date) → confirm + forward-pointer to `/research`/`/specify`. Pure capture, NO diagnosis, NO agents.
- **claude-code-guide** verifies current command-authoring conventions first; **instruction-author** writes; **instruction-reviewer** reviews.
- **Verify:** no `{{` leaks; frontmatter valid; cites only real helper verbs; instruction-reviewer clean.

### Phase 3 — Wire the offer + emit + reconcile docs
- `scripts/emitters/claude.py`: `_PROMOTED += "report-bug"`.
- `src/CLAUDE.md`: add `/report-bug` to the standalone group + a Command Details one-liner; in the "Conversational fix-or-file offer" section, name `/report-bug` as the command the "file" arm runs.
- `src/commands/fix/main.md`: the out-of-window file-only path → name `/report-bug` explicitly.
- `src/devforge/storage-rules.md`: reconcile (the `report-bug` row + `Source: manual` already exist; confirm consistency, note the route-by-state trigger if needed).
- **Delete** the superseded `src/_pending/commands/report-bug.md`.
- Mandatory cross-ref sweep: grep `report-bug` / `report_bug` repo-wide; no dangling refs.
- **python-engineer** does the emitter edit + an emit-verification run; **instruction-author** does the markdown; **instruction-reviewer** reviews.
- **Verify:** emitter emits `report-bug` (command + installed executable helper, 0 `{{` leaks); cross-ref sweep clean.

### Phase 4 — Install ride + full suite (orchestrator, post-workflow)
- Run the emitter/install path; confirm `/report-bug` emits cleanly + helper installed executable.
- Full `tests/lib` suite green.
- Per-phase commits (specific paths, no AI attribution) after verification.

### Phase 5 — testForge20 e2e (user-driven HARD GATE) — deferred
- Surgically deliver, run `/report-bug "..."`, confirm `bugs/NNN-*.md` with Source: manual; confirm the fix-or-file offer names `/report-bug`.

## Context for next session

- Build runs behind an agent workflow: python-engineer→python-reviewer (Phases 0,1, emitter), instruction-author→instruction-reviewer + claude-code-guide (Phases 2,3 markdown).
- Workflow agents do NOT commit; the orchestrator commits per phase after Phase 4 verification.
- Single source of truth for bug-writing is `_shared/bug_file.py` after Phase 0 — never re-introduce a `_verify/_bugs.py` or a `_report_bug` copy.

## When resuming work

Read this plan in full. Check whether `src/devforge/lib/_shared/bug_file.py`, `src/devforge/lib/_report_bug/`, and `src/commands/report-bug/main.md` exist to determine which phase to resume from. Verify `tests/lib/_verify` still passes (the Phase 0 regression net).
