# 49 — DEVFORGE RUNTIME STATE DISPOSITION

**Status:** **PHASES 0–5 SHIPPED (working tree) 2026-07-04 — only Phase 6 (consumer/testForge20 e2e) remains, user-driven.** Delivered: **P1** dedicated `src/files/devforge.gitignore` template + `manifest.json` `mergeFiles[".gitignore"].templateSource` + `update.sh` `merge_src()` source resolver (filters + union call + copy re-pointed, `.mcp.json` `union_keys` fallback preserved) + `install.sh` inline union block (fresh-install coverage, OQ-5). **P2** fail-soft / tracked-only / install-repo-only `git rm --cached` migration in `update.sh` (untracks the ephemeral set incl. the tracked pointers, deletes the dead `.claude/session-state.md` line, VERSIONED `memory.md` preserved). **P3** `/finalize` PHASE-2 safety-net extended to stage `memory.md` + `spec-stamps.jsonl` via `commit-artifacts --paths` (D3 back-pointer inline; `instruction-reviewer`-clean, 0 findings). **P4** 3-class disposition table + scratch-vs-record trap in `storage-rules.md`. **P5** repo-root `CLAUDE.md` active-work entry + Where-to-find row, `CHANGELOG.md` `[Unreleased]`, `manifest.json:40` `projectOwned` dead-path fixed, cross-ref sweep clean, both scripts `bash -n` OK. Tests: 26 Phase-1 + 11 Phase-2 scratch tests green (37 total). Ratified: OQ-4 = feature-squash; OQ-1 = config VERSIONED; OQ-2 = report scratch gitignored; OQ-5 = install.sh covered. Maintainer sign-off: OQ-4 = **(a) ride the feature squash** (versioned deltas fold into the `/finalize` safety-net, no extra commit); OQ-1 = **VERSIONED, no action** (config/identity files change only on reconfigure); OQ-2 = **gitignore the single-slot report scratch** (durable record is the dated `research/`+`discover/` layouts). Classification table (D1), D2–D8, and reuse-only constraint all confirmed. This plan gives every `.devforge/` runtime-state file exactly ONE disposition — VERSIONED / EPHEMERAL / FEATURE-SCOPED — so that a full pipeline cycle (`/research → /specify → /plan → /breakdown → /implement → /review → /verify → /summarize → /finalize`) leaves the consumer install's git tree CLEAN automatically, instead of dirty with runtime-state churn the maintainer must hand-commit every cycle. It reuses existing machinery only (the `manifest.json` `union_lines` gitignore merge + the `/finalize` PHASE-2 safety-net commit); it designs no new Python helper. Six phases, each independently verifiable; Phase 0 is a maintainer decision gate.

## Problem — the tree is left dirty every cycle, and one ignore rule points at a dead path

After a full spec-driven pipeline cycle, the consumer install's git tree is left dirty with `.devforge/` runtime-state files. Two mechanisms conspire:

- **`/finalize` blanket-EXCLUDES all runtime state from the feature squash.** Per plan 33 / plan 37 Decision D3, runtime state (`memory.md`, `session-state.md`, `*-state.json`, stamps) is treated as global, not feature-scoped, and excluded from the squash. No pipeline step reconciles these files to a committed-or-ignored terminal state, so the maintainer must manually `git add .devforge/ && git commit` every cycle.

- **The one gitignore rule that tries to suppress session state points at a DEAD path.** A consumer install's `.gitignore` ignores `.claude/session-state.md` — the PRE-plan-22 path. Plan 22 (finding F, the memory-path migration) moved the file to `.devforge/session-state.md`. So the ignore rule targets a file that no longer exists, while the real churners (`.devforge/session-state.md`, `.devforge/*-state.json`, stamps, tracked `*.lock`) sit tracked-and-dirty.

Root cause: **`.devforge/` holds THREE different storage classes under one directory with NO per-file disposition policy.** Setup identity, per-cycle working state, and feature-scoped records all coexist there, and nothing decides which of them git should track, ignore, or fold into a feature commit.

There is a further structural gap behind the dead ignore rule: **there is no DEDICATED consumer gitignore template — the merge reuses the forge repo's OWN root `.gitignore` as its source.** The merge mechanism is `src/manifest.json` → `mergeFiles[".gitignore"]` with strategy `"union_lines"` (`src/manifest.json:57-60`, "Add new template lines, keep existing project lines"), and `merge_union_lines` (`update.sh:827`) reads that source from `$TEMPLATE_DIR/.gitignore` where `TEMPLATE_DIR` is the forge repo root (`update.sh:47`). So the forge's own `.gitignore` doubles as the consumer template — which is precisely how the dead `.claude/session-state.md` line (literally `<forge-root>/.gitignore:3`) has been unioned into every consumer, and how forge-internal `src/devforge/...` lines leak in as inert clutter. Phase 1 (Option B, ratified) introduces a dedicated `src/files/devforge.gitignore` template and re-points the merge at it — see Phase 1 for the full verified mechanism, including the fact that `install.sh` does not currently merge `.gitignore` at all.

## The `.devforge/` file inventory + three-class classification

Verified full inventory of a real consumer install's `.devforge/` top-level files (excluding `lib/`, `template/`, `bin/`), each assigned exactly one of three dispositions. This table is the organizing artifact of the plan (D1). Phase 4 persists it into `src/devforge/storage-rules.md` (which currently documents NONE of these files).

| File | Class | Action |
|---|---|---|
| `memory.md` | VERSIONED | Stay tracked; per-feature DELTA rides the feature squash (D3) |
| `spec-stamps.jsonl` | VERSIONED | Stay tracked; per-feature DELTA rides the feature squash (D3) |
| `init.yaml` | VERSIONED | Stay tracked; setup identity, changes only on reconfigure (OQ-1) |
| `configure.yaml` | VERSIONED | Stay tracked; setup identity (OQ-1) |
| `constitute.json` | VERSIONED | Stay tracked; setup identity (OQ-1) |
| `project-config.json` | VERSIONED | Stay tracked; render/index artifact, stable across cycles — borderline (OQ-1) |
| `index.json` | VERSIONED | Stay tracked; render/index artifact, stable across cycles — borderline (OQ-1) |
| `storage-rules.md` | VERSIONED | Stay tracked; installed framework file |
| `session-state.md` | EPHEMERAL | gitignore + `git rm --cached` migration (was tracked; the dead-rule victim) |
| `specify-state.json` | EPHEMERAL | gitignore + `git rm --cached` migration |
| `research-state.json` | EPHEMERAL | gitignore + `git rm --cached` migration |
| `research-report.json` | EPHEMERAL | gitignore + `git rm --cached` migration (OQ-2) |
| `discover-scope.json` | EPHEMERAL | gitignore + `git rm --cached` migration |
| `discover-report.json` | EPHEMERAL | gitignore + `git rm --cached` migration (OQ-2) |
| `.preflight-stamp` | EPHEMERAL | gitignore + `git rm --cached` migration; pure timestamp/pointer (currently TRACKED) |
| `cbm-last-indexed-sha` | EPHEMERAL | gitignore + `git rm --cached` migration; pure pointer (currently TRACKED) |
| `.generate-docs-trace.log` | EPHEMERAL | gitignore; log (already untracked — ensure the rule covers it) |
| `cbm-usage.log` | EPHEMERAL | gitignore; log (already untracked — ensure the rule covers it) |
| `*.lock` (all) | EPHEMERAL | gitignore + `git rm --cached` migration for the tracked ones |
| `research/<date>-<slug>/*` | FEATURE-SCOPED | NO action — already committed per-step by plan 37; document the distinction |
| `discover/<date>-<slug>.*` | FEATURE-SCOPED | NO action — already committed per-step by plan 37; document the distinction |
| `specs/<feature>/*` | FEATURE-SCOPED | NO action — already committed per-step by plan 37; document the distinction |

Class definitions:

- **VERSIONED** — stay tracked because they carry valuable history or setup identity. They are NOT the churn problem. The only two whose per-feature delta is feature-caused (`memory.md`, `spec-stamps.jsonl`) ride the feature squash (D3); the rest change only on reconfigure and need no per-cycle action.
- **EPHEMERAL** — the actual churn: per-cycle working state, single-slot scratch outputs, pointers, timestamps, logs, and locks. `session-state.md` and the `*-state.json` files are read from DISK for crash recovery, not from git, so versioning them only helps rare cross-machine recovery. Treatment: gitignore (D2) plus a one-time `git rm --cached` migration for the ones currently tracked (D6).
- **FEATURE-SCOPED** — the DATED persistent records and per-feature planning artifacts. Already committed per-step by plan 37 and folded into `/finalize`'s squash; NO action here. **CRITICAL distinction to document (D7):** `.devforge/research-report.json` (EPHEMERAL single-slot scratch) is NOT the same file as `research/<date>-<slug>/handoff.json` (FEATURE-SCOPED persistent artifact). The two are trivially conflated; the classification table and `storage-rules.md` must call this out explicitly. `.devforge/discover-report.json` vs `discover/<date>-<slug>.handoff.json` is the same trap.

The `.lock` files (`configure.yaml.lock`, `constitute.json.lock`, `discover-report.json.lock`, `discover-scope.json.lock`, `research-report.json.lock`, `research-state.json.lock`, `specify-state.json.lock`) are the subtlest case: a consumer `.gitignore` line `.devforge/**.lock` already exists, but a gitignore rule does NOT untrack already-tracked files — the tracked locks need `git rm --cached` in the Phase-2 migration to actually leave the tree.

## Decisions

- **D1 — Three-class disposition model.** Every `.devforge/` file gets exactly one disposition: VERSIONED / EPHEMERAL / FEATURE-SCOPED. This is the organizing principle; the classification table above is its authoritative form. Rationale: the churn exists precisely because three storage classes share one directory with no per-file policy — naming the class per file is what makes each file's git treatment decidable rather than ad-hoc.
- **D2 — EPHEMERAL files are gitignored, NOT swept into a chore commit.** Delete the noise from git's view rather than committing timestamp/pointer/scratch churn every cycle. Rationale: the rejected alternative ("Strategy 2" — `/finalize` commits all dirty `.devforge/`) produces churny history AND persists confusing single-slot drift (e.g. `research-report.json` holding another feature's content on this branch would be committed as if it belonged to this feature). gitignore makes the churn structurally invisible; committing it makes the churn permanent.
- **D3 — VERSIONED runtime deltas (`memory.md` + `spec-stamps.jsonl`) ride the FEATURE squash** via the existing `/finalize` PHASE-2 safety-net commit (extend its path set). This is a deliberate, NARROW, FILE-LEVEL REVISIT of plan 33 / plan 37's blanket D3 ("runtime state is global, exclude all"). Rationale: these two files' per-feature DELTA is FEATURE-CAUSED — a feature's work is what appends to `memory.md` and `spec-stamps.jsonl` — so that delta belongs on the feature commit, not stranded as uncommitted global state. (Mechanically the safety-net `git add`s the whole file, capturing its current uncommitted state — which equals the feature delta in the steady-state case where the prior cycle already committed its own delta, the normal case since every cycle finalizes; a genuinely global edit made mid-feature would also fold in, an acceptable rarity.) This narrows the plan-33/37 exclusion for exactly two files; it does NOT reopen the exclusion for `session-state.md`/`*-state.json`/stamps (those stay EPHEMERAL per D2). **The Phase-3 edit MUST carry a back-pointer note** so a future session does not read the extended path set as contradicting plan 33/37 D3 — it is a scoped file-level revisit, recorded as such. (The feature-squash-vs-trailing-chore fork is OQ-4.)
- **D4 — Reuse, don't build.** gitignore via the existing `manifest.json` `union_lines` merge plus a new canonical gitignore source in `src/`. Versioned-file commit via the existing `/finalize` PHASE-2 safety-net `git add` (the `artifact_helper commit-artifacts` verb is the alternative staging mechanism — the phase decides which). NO new Python helper module is designed in this plan.
- **D5 — The canonical gitignore becomes framework-owned.** A new source file in `src/` (merged into consumers by the install/update `union_lines` strategy) supplies the `.devforge/` ephemeral rules. The migration REPLACES the dead `.claude/session-state.md` legacy line with the correct `.devforge/session-state.md` rule, so the ignore mechanism finally points at a live path.
- **D6 — Migration home = `update.sh`.** The `git rm --cached` of the now-ephemeral tracked files lives in `update.sh` (fail-soft, guarded to run only when the file is actually tracked, install-repo-only). Existing installs converge on their next update; a fresh install starts clean because the ephemeral files are never committed in the first place.
- **D7 — `storage-rules.md` documents the three-class model.** The `.devforge/` runtime-state disposition is currently undocumented (`src/devforge/storage-rules.md`'s Directory Structure lists `bugs/`, `research/`, `discover/`, `audits/`, `specs/`, `docs/` — none of the `.devforge/` runtime files). Phase 4 adds the table plus the ephemeral-scratch-vs-persistent-record distinction.
- **D8 — install-repo-only / wrapper-safe by construction.** `.devforge/` only ever exists in the install/wrapper root, never the source/product repo (plan 25 D5, traceless source). So every gitignore change and every commit/`rm --cached` in this plan is install-repo-only automatically; the source repo is never touched. No wrapper-specific branching is required to guarantee this — it is a property of where `.devforge/` lives.

## Open Questions (Phase-0 ratification items — NOT resolved here)

- **OQ-1 — Config/identity files disposition.** `init.yaml`, `configure.yaml`, `constitute.json`, `project-config.json`, `index.json`: confirm VERSIONED with no action. `project-config.json` and `index.json` are REGENERATED on re-runs — do they churn enough to be noise worth ephemeral-izing? Recommendation: VERSIONED (they change only on reconfigure / re-generate-docs, not per feature cycle, so they are not part of the per-cycle churn). Maintainer confirms or reclassifies at Phase 0.
- **OQ-2 — EPHEMERAL-izing the single-slot report outputs.** Confirm `.devforge/research-report.json` and `.devforge/discover-report.json` are safe to gitignore, given the persistent record lives in the dated `research/<date>-<slug>/` and `discover/<date>-<slug>.*` layouts (plan-37-committed, FEATURE-SCOPED). Recommendation: gitignore them (the durable record is elsewhere; the `.devforge/` copy is single-slot scratch). Maintainer confirms the persistent record fully supersedes the scratch copy at Phase 0.
- **OQ-3 — Migration guard mechanics in `update.sh`.** The exact guard so `git rm --cached` is fail-soft and only touches tracked ephemeral files — never erroring a fresh install where none are tracked, never touching a file the user legitimately tracks for their own reasons. Resolve the guard shape at Phase 2 authoring (candidate: `git ls-files --error-unmatch <path>` presence test before each `rm --cached`, all wrapped fail-soft).
- **OQ-4 — Versioned-file commit HOME.** Ride the feature squash (D3 — no extra commit, but couples the cross-feature `memory.md` delta to one feature's commit) vs a separate trailing `chore(forge):` commit (clean separation of global-state delta from feature code, but one extra commit per cycle). Recommendation: feature-squash (fewer commits, and the delta IS feature-caused per D3). **RESOLVED 2026-07-04 = (a) feature-squash.**
- **OQ-5 — `install.sh` fresh-install coverage** (discovered 2026-07-04). The `.gitignore` merge lives ONLY in `update.sh`; `install.sh` does not merge it (deferred to the retired wizard, plan 30). So fresh installs currently get no forge gitignore rules until their first `update.sh` — dirty from cycle 1. Recommendation: add the union merge to `install.sh` (Phase 1 step 4) so fresh installs are clean immediately. **RESOLVED 2026-07-04 = yes, cover install.sh** (folded into Phase 1).

## Phase 0 — Maintainer ratification (decision gate, no code)

Present this plan. The maintainer confirms: (a) the three-class disposition model (D1) and the full classification table; (b) EPHEMERAL → gitignore, not chore-commit (D2); (c) the narrow file-level revisit of plan 33/37 D3 for `memory.md` + `spec-stamps.jsonl` (D3), and the OQ-4 commit-home fork; (d) reuse-not-build (D4), framework-owned gitignore (D5), and migration in `update.sh` (D6); (e) the four open questions OQ-1..OQ-4, resolving each or deferring to its named phase. Until ratification, no build phase is authored.

### Verify

- Maintainer has signed off on the classification table, the three decisions with live forks (D3 / OQ-4, OQ-1), and the reuse-only constraint. Record the sign-off inline here when it happens.
- No build phase below has started before this gate clears.

---

## Phase 1 — Dedicated consumer gitignore template + merge wiring

**Verified mechanism (2026-07-04 — corrects an earlier draft assumption).** The `union_lines` merge (`merge_union_lines`, `update.sh:827`) reads its source from `$TEMPLATE_DIR/.gitignore`, and `TEMPLATE_DIR` is the FORGE REPO's OWN root (`update.sh:47`, `$(cd "$(dirname "$0")" && pwd)`). So the merge template today IS the forge repo's own root `.gitignore` — which is exactly why the dead `.claude/session-state.md` line propagates into consumers: it is literally `<forge-root>/.gitignore:3`, unioned into every target. Two further verified facts reshape this phase:

- **(A) `install.sh` does NOT merge `.gitignore` at all.** The mergeFiles/`union_lines` logic lives ONLY in `update.sh` (the `merge_union_lines` fn + the `MERGE_ACTUAL`/`MERGE_ADD` filters). `install.sh:15` defers gitignore to "the wizard", which was RETIRED (plan 30). So a FRESH install currently gets ZERO forge gitignore rules until its first `update.sh` — its tree is dirty from cycle 1. Closing the clean-tree goal for fresh installs REQUIRES adding the merge to `install.sh` (OQ-5).
- **(B) `install.sh:232` does `cp -R src/devforge/. → target/.devforge/`.** So the template file MUST NOT live under `src/devforge/`, or it would be copied wholesale into every consumer's `.devforge/`. Correct home: `src/files/devforge.gitignore`.

**Chosen mechanism (Option B, ratified 2026-07-04):** a DEDICATED consumer gitignore template, separate from the forge repo's own `.gitignore`, so forge-repo hygiene and the consumer template stop being conflated and the forge-internal lines (`src/devforge/init.yaml`, …) stop leaking into consumers.

Steps:
1. Create `src/files/devforge.gitignore` (NOT under `src/devforge/` — fact B) carrying ONLY the `.devforge/` EPHEMERAL rules from the classification table (`session-state.md`, `specify-state.json`, `research-state.json`, `research-report.json`, `discover-scope.json`, `discover-report.json`, `.preflight-stamp`, `cbm-last-indexed-sha`, `.generate-docs-trace.log`, `cbm-usage.log`, and a `.devforge/**.lock` glob covering every lock in the table) plus the correct `.devforge/session-state.md` line.
2. Add a `templateSource` field to `manifest.json` `mergeFiles[".gitignore"]` pointing at `src/files/devforge.gitignore`.
3. Change the source resolution in `update.sh` — both `merge_union_lines`'s call site AND the `MERGE_ACTUAL`/`MERGE_ADD` existence filters — to read `templateSource` when present, falling back to `$TEMPLATE_DIR/$f` when absent (back-compat: the `.mcp.json` `union_keys` entry has no `templateSource` and must be untouched).
4. Add the same `.gitignore` union merge to `install.sh` so FRESH installs are clean from cycle 1 (OQ-5).

The shell merge-logic change + a scratch-repo test go in the SAME turn (test both the union onto a pre-existing consumer `.gitignore` and the fresh-copy path); the plan's python-engineer → python-reviewer loop applies to any Python logic, and shell guards are proven by the phase's own scratch-repo run.

### Verify

- A fresh `install.sh` into a scratch target produces a `.gitignore` containing the `.devforge/` ephemeral rules AND the correct `.devforge/session-state.md` line, with NO forge-internal `src/devforge/...` lines leaking in (proves the dedicated template, not forge-root, is the source).
- `update.sh` on a scratch target with a pre-existing custom `.gitignore` unions the new rules in AND keeps the custom lines (`union_lines` additive).
- The `.mcp.json` `union_keys` merge still works (the `templateSource`-absent fallback holds).
- No EPHEMERAL file from the classification table is missing a covering rule (cross-check the template against the table).

---

## Phase 2 — Migration in `update.sh` (`git rm --cached` the tracked ephemeral files)

Add a fail-soft, tracked-only, install-repo-only migration to `update.sh`: for each EPHEMERAL file the classification table marks as currently tracked (`session-state.md`, `specify-state.json`, `research-state.json`, `research-report.json`, `discover-scope.json`, `discover-report.json`, `.preflight-stamp`, `cbm-last-indexed-sha`, and the tracked `*.lock` files), `git rm --cached` it so the now-present gitignore rule takes effect, and DELETE the dead `.claude/session-state.md` legacy `.gitignore` line. The `union_lines` merge (Phase 1) only ADDS lines — it never removes one — so the dead line will persist forever unless this migration deletes it explicitly; the correct `.devforge/session-state.md` rule is supplied by the Phase-1 merge, and this step removes the orphan. The migration MUST NOT error on a fresh install where none of these are tracked (OQ-3 guard). It targets the install/wrapper root only (D8 — the source/product repo has no `.devforge/`, so no branching is needed).

Any Python helper logic this migration calls routes through python-engineer → python-reviewer with a test in the same turn; a shell-only guard is verified by the Phase's own scratch-repo run.

### Verify

- Run `update.sh` on a scratch install that has the ephemeral files TRACKED and dirty → after the run they are untracked and ignored, and `git status` is clean of them.
- Run `update.sh` on a FRESH scratch install where none of the ephemeral files are tracked → the migration is a clean no-op, exits 0, errors nothing (OQ-3 guard holds).
- The dead `.claude/session-state.md` line is DELETED by the migration (the `union_lines` merge cannot remove it); the correct `.devforge/session-state.md` rule is present.
- A file the user legitimately tracks for their own reasons and that is NOT in the ephemeral set is untouched.

---

## Phase 3 — Extend the `/finalize` PHASE-2 safety-net to fold the versioned deltas into the squash

Extend the existing UNCONDITIONAL PHASE-2 "Artifact safety-net commit (before the squash)" in `src/commands/finalize/main.md` (the block at `main.md:152-160`, labeled "37-D4", which already `git add`s `specs/<feature>/` and commits a `[WIP]` BEFORE the PHASE-3 squash) so its path set ALSO stages `.devforge/memory.md` + `.devforge/spec-stamps.jsonl`. Because the PHASE-3 squash is `git reset --soft` to the squash base (plan 25 `_squash.py`), anything committed after the base folds into the single clean feature commit — so the two versioned deltas ride the squash and the tree is left clean of them, with the final PR byte-unchanged (the two files fold INTO the existing feature commit; they do not add a commit).

Reuse the existing staging mechanism — either extend the safety-net's `git add` path set directly or pass the two files through the same `artifact_helper commit-artifacts --paths` call already used at `main.md:157` (whose `git add -- <path>` staging + fail-soft + install-repo-only guard are exactly the required behavior — D8). No new helper.

**The edit MUST carry an inline back-pointer note** recording that staging these two `.devforge/` files is a DELIBERATE, narrow, file-level revisit of plan 33/37's blanket D3 runtime-state exclusion (D3 above) — so a future session does not read it as an accidental contradiction of "runtime state is excluded from the squash."

This file ships into a target project's `.claude/` directory, so the edit routes through instruction-author → instruction-reviewer + claude-code-guide (per the framework's Claude-Code-authoring discipline).

### Verify

- A `/finalize` run on a feature whose cycle appended to `memory.md` and `spec-stamps.jsonl` folds both files into the feature squash; after the squash neither is left dirty in `git status`.
- The final squashed feature commit contains the two files' deltas; the PR is byte-unchanged relative to committing them separately (they are inside the one feature commit, not an extra commit).
- The inline back-pointer note to plan 33/37 D3 is present in the edited block.
- The `.devforge/` staging is install-repo-only — a wrapper-mode `/finalize` never stages into the source/product repo (guaranteed by construction, D8; confirmed because `.devforge/` does not exist there).

---

## Phase 4 — Document the three-class model in `storage-rules.md`

Add the classification table and the three class definitions to `src/devforge/storage-rules.md`, which currently documents none of the `.devforge/` runtime-state files. Include the EPHEMERAL-scratch-vs-FEATURE-SCOPED-record distinction explicitly (D7) — in particular that `.devforge/research-report.json` (single-slot scratch, EPHEMERAL) is a DIFFERENT file from `research/<date>-<slug>/handoff.json` (persistent record, FEATURE-SCOPED), and the same for the discover pair — so a future reader does not conflate them.

### Verify

- Every `.devforge/` file in the classification table appears in `storage-rules.md` with its disposition.
- The scratch-vs-record distinction (`.devforge/research-report.json` ≠ `research/<slug>/handoff.json`) is stated explicitly.
- No sentence claims a file is committed/ignored in a way that contradicts the gitignore template (Phase 1) or the finalize extension (Phase 3).

---

## Phase 5 — Docs reconcile + cross-ref sweep

Reconcile the repo-root docs to the new disposition model and sweep for dangling references:

- Repo-root `CLAUDE.md` — add the runtime-state-disposition entry to the "Where to find what" table and an active-work entry to the plan list.
- `CHANGELOG.md` — record the gitignore template + migration + finalize extension.
- Grep for dangling references to the dead `.claude/session-state.md` path, to `.devforge/` runtime files, and to the plan-33/37 D3 exclusion, and reconcile any that now mislead.

### Verify

- The cross-ref sweep is clean: no doc still cites `.claude/session-state.md` as a live path; no doc describes `.devforge/` runtime state in a way the new model contradicts without a reconciling note.
- The repo-root `CLAUDE.md` table + plan list and `CHANGELOG.md` carry the change.

---

## Phase 6 — Consumer / testForge20 e2e (user-driven HARD GATE)

Run a full pipeline cycle on a consumer install (testForge20) after Phases 1–5 are delivered, and confirm the git tree is CLEAN at the end of the cycle with no manual `.devforge/` commit required. Cover both a standalone install and a wrapper-mode install (to confirm D8 install-repo-only holds — the source/product repo stays clean).

### Verify

- After `/research → … → /finalize`, `git status` shows no dirty `.devforge/` EPHEMERAL files (they are ignored) and no uncommitted VERSIONED deltas (`memory.md` / `spec-stamps.jsonl` folded into the squash).
- The wrapper-mode run leaves the source/product repo untouched by any `.devforge/` change.
- No manual `git add .devforge/` was required to reach a clean tree.

---

## Context for next session

This plan makes a consumer install's git tree CLEAN automatically at the end of a full pipeline cycle. Today it is left dirty with `.devforge/` runtime state because `/finalize` blanket-excludes all runtime state from the feature squash (plan 33/37 D3) AND the one gitignore rule meant to suppress session state points at a DEAD path (`.claude/session-state.md`, the pre-plan-22 location; the file moved to `.devforge/session-state.md` in plan 22 finding F). Root cause: `.devforge/` holds THREE storage classes under one directory with no per-file disposition policy, and there is no framework-owned gitignore template (`src/` has no `.gitignore`; the merge is `manifest.json` `mergeFiles[".gitignore"]` `union_lines`, `src/manifest.json:57-60`). The fix assigns every `.devforge/` file exactly one disposition — VERSIONED / EPHEMERAL / FEATURE-SCOPED (the classification table is the plan's core artifact) — then: EPHEMERAL → a new canonical gitignore source in `src/` merged by `union_lines` + a fail-soft tracked-only `git rm --cached` migration in `update.sh`; VERSIONED deltas `memory.md` + `spec-stamps.jsonl` → folded into the feature squash by extending the existing `/finalize` PHASE-2 safety-net commit (`src/commands/finalize/main.md:152-160`, which already `git add`s `specs/<feature>/` before the `git reset --soft` squash, so anything committed after the base folds in and the PR is byte-unchanged); FEATURE-SCOPED files are already committed per-step by plan 37 — no action, only a documented warning that `.devforge/research-report.json` (scratch) is NOT `research/<slug>/handoff.json` (record). Reuse only — no new helper; reuse `artifact_helper commit-artifacts` and/or the finalize safety-net `git add`, and the existing `manifest.json` merge. Install-repo-only / wrapper-safe by construction: `.devforge/` only exists in the install/wrapper root, never the source/product repo (plan 25 D5). The D3 extension is a DELIBERATE narrow file-level revisit of the plan-33/37 blanket exclusion — the Phase-3 edit carries a back-pointer so a future session does not read it as a contradiction.

## When resuming work

1. **Do not build before Phase 0 ratifies.** The classification table (D1), the OQ-4 commit-home fork, and OQ-1 (config-file disposition) are live maintainer decisions; the recommendations are recorded but not settled.
2. **Re-confirm the live anchors before editing** — line numbers drift. Re-check `src/manifest.json:57-60` (the `union_lines` gitignore merge), `src/commands/finalize/main.md:152-160` (the safety-net commit block), and that `src/` still has no `.gitignore`, before authoring Phase 1 or Phase 3.
3. **Phase 1 CREATES the framework-owned gitignore source** — there is none today; the merge has nothing correct to add until it exists.
4. **Phase 2's migration is fail-soft, tracked-only, install-repo-only** — a fresh install with nothing tracked must be a clean no-op (OQ-3 guard). Prove it on a fresh scratch install, not just a dirty one.
5. **Phase 3 carries the plan-33/37 D3 back-pointer note** — the two-file squash-fold is a narrow revisit, not a contradiction; record it inline so a future session cannot misread it.
6. **Reuse only — design no new helper.** Stage the versioned deltas through the existing finalize `git add` or `artifact_helper commit-artifacts`; ignore the ephemeral files through the existing `union_lines` merge.
7. Route every Python/shell-logic edit (Phase 1/2 merge + migration) through python-engineer → python-reviewer with a test in the same turn, and the Phase-3 `finalize/main.md` edit (ships into `.claude/`) through instruction-author → instruction-reviewer + claude-code-guide.
