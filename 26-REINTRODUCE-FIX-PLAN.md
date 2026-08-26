# 26 — REINTRODUCE /fix PLAN

**Status**: DONE (build) 2026-06-19 on `develop-2.0-init` — Phases 0–4 built, reviewed, and committed (`efa16e4`, `154c2c4`, `f91e1b4`, `cd7c688`, `26ae580`); install ride passed (fix command emits, executable `fix_helper`, 0 placeholder leaks). **Phase 5 (testForge20 e2e) WAIVED by maintainer 2026-06-19 — NOT executed.** `/fix` is build-verified (unit tests + install ride) but not runtime-e2e-validated; opportunistic e2e validation deferred.

Reintroduces a `/fix` command to AIDevTeamForge — a thin, gated, **remediation** command OFFERED (never auto-invoked) as the "remediate now" arm of a two-arm fix-or-file offer in exactly three post-`/implement`/pre-`/summarize` situations: when `/review` surfaces findings, when `/verify` returns NEEDS WORK, or conversationally when the user raises a defect the model code-confirms in-window (D2). `/fix` is NOT a general cold bug-fixer; every other moment gets the file-a-bug arm only. When invoked it consumes the surfaced findings (`/review`'s `specs/[feature]/review.md`, `/verify`'s NEEDS WORK issues) or the case-3 confirmed defect, triages and scopes them, then delegates to `/implement`'s already-shipped back-half engine (scope-aware verify → four-reviewer panel → forcing-functions gate → two-stage hard gate → WIP commit) — it CALLS the existing `implement_helper` verbs, it never copies their machinery. This plan **supersedes ONLY plan 21's D1** ("no fast-path command or tier"); every other plan-21 decision (the `/refactor` drop, D2–D6) stands. This file DESCRIBES the work and performs no change; the file:line references below are pre-edit starting points gathered this session — re-confirm each before writing the edit instruction for that site.

## Scope & assumptions

These are decided, not open (except the OQs in `## Open questions`):

1. **`/fix` is a conditional remediation loop OFFERED in the post-`/implement`/pre-`/summarize` window, NOT a pipeline-chain step.** It is OFFERED (PROPOSED — never auto-invoked) by `/review`'s findings report, by `/verify`'s NEEDS WORK verdict, and conversationally (the case-3 user-raised + code-confirmed in-window defect, D2); it is not inserted into the linear `… /implement → /review → /verify → /summarize → /finalize` Workflow chain (verified against the "Spec-Driven Development Flow" code block in `src/CLAUDE.md`, the SSOT for pipeline position). Its representation in `src/CLAUDE.md` is OQ-3.
2. **The target is a NEW live command tree** at `src/commands/fix/` (`main.md` + `references/*.md`), a NEW helper subpackage `src/devforge/lib/_fix/`, and a NEW launcher `src/devforge/lib/fix_helper{,.py}`. **There is NO stale draft to rewrite** — plan 21 Phase 1 deleted `src/_pending/commands/fix.md` (verified: plan 21 blast-radius A; the v1.28 draft is gone). This plan builds `/fix` fresh from the shared-engine pattern, NOT by resurrecting the deleted 23.5K copy-the-back-half draft (D6 forbids copying).
3. **Every file path, config key, and identifier in this plan is verified against the live tree this session.** The `main.md` / helper line numbers cited are pre-edit; after a phase edits a file, re-read it from scratch rather than navigating by these numbers.
4. **Build on the already-shipped back-half engine; do NOT change `/implement`.** `/fix` reuses the installed `implement_helper` verbs `verify-touched`, `merge-review-panel`, and `run-forcing-functions-gate` (verified: `src/commands/implement/main.md:10–13` allowed-tools — all three are live binaries) report-and-loop exactly as `/implement` PHASES 5–7 wire them. NO `/implement` behavior change, and the only `implement_helper` change is the one additive `wip-commit` task-less mode discovered during build (see `## Implementation notes / discovered constraints`, 2026-06-19; `/implement` stays byte-identical).
5. **`/review` and `/verify` ship in the working tree (uncommitted) per plans 20/22** — `src/commands/review/main.md` (writes `specs/[feature]/review.md`) and `src/commands/verify/main.md` (renders NEEDS WORK + files bugs) both exist this session. `/fix`'s inputs (`review.md` findings, `verification.md` NEEDS WORK issues) are therefore real artifacts, not hypothetical.

## Command mission (what /fix is for)

`/fix` exists to own the ONE workflow moment nothing else owns cleanly: **remediate a known, already-diagnosed, already-scoped defect that the pipeline itself surfaced — with `/implement`'s full per-task gates — without re-running spec → plan → breakdown.** When `/review` finds an emergent cross-task issue or `/verify` returns NEEDS WORK, the defect is already diagnosed (the finding names it), already located (the finding cites files + evidence), and already scoped (it is one feature's already-implemented diff). What is missing is a GATED way to apply the fix that restores the two things a bare hand-fix loses (plan 21 §5): the forced regression-test / verify gate, and the clean attributed commit. `/fix` supplies exactly that and nothing more — it is the back-half engine pointed at a finding instead of at a fresh task.

**The boundary, stated explicitly (this is D2):** the model presents a **two-arm fix-or-file OFFER** ((A) run `/fix` now / (B) file a bug to defer) in exactly THREE in-window situations — `/review` surfaces findings, `/verify` returns NEEDS WORK, or conversationally when the USER raises a defect that the model code-confirms while the active feature is post-`/implement`/pre-`/summarize`. The model NEVER auto-invokes `/fix` (every forge command sets `disable-model-invocation: true`). In every other moment the model offers ONLY to file a bug — never `/fix`. `/fix` is NOT a cold general bug-fixer and does NOT accept a free-form "describe a bug" input: a standalone cold bug a developer notices independently still goes hand-fix / full-chain — exactly the boundary plan 21 drew (§4). A future session must NOT add a free-text intake to `/fix` by analogy with `/research` or `/specify`. See D2 for the full three-case scope + the in-window-WIP-vs-sealed rationale.

### The /implement-vs-/fix invariant

`/fix` reuses `/implement`'s back half but is a distinct command surface for a distinct workflow moment — the same pattern the framework already converged on for `/review` vs `/verify` (shared `_shared/` engine, distinct surface) and for `/verify` reusing `verify-touched`. This table is the invariant the plan must preserve:

| Axis | `/implement` | `/fix` |
|---|---|---|
| **Trigger** | in-pipeline, after `/breakdown` approves tasks | OFFERED (never auto-invoked) in 3 in-window situations: `/review` findings, `/verify` NEEDS WORK, or a user-raised + code-confirmed conversational defect (D2) |
| **Input** | a feature's APPROVED breakdown TASKS (`breakdown-handoff.json`) | a pipeline-produced FINDING set (`review.md` / `verification.md` NEEDS-WORK issues) |
| **Front half** | resolve next dependency-ready task; dispatch the assigned agent | read findings; lightweight triage; scope-estimate (with the D7 `/specify` bounce) |
| **Back half** | verify-touched → review panel → forcing-functions → hard gate → WIP commit | **the SAME** — verify-touched → review panel → forcing-functions → hard gate → WIP commit (D3) |
| **Loops the feature?** | YES — drains every task | NO — remediates the surfaced finding set, then stops |
| **Writes `bugs/`?** | no | **no** (D4 — `/fix` is the "remediate now" path; `bugs/` is the "defer" path) |

## Why supersede plan 21 D1 (the anti-future-hallucination payload)

This section is the record that the reintroduction is DELIBERATE, not an oversight or a re-litigation of a settled decision. A future session reading plan 21's `## Why DROP, not rework` (§1–§5) and its D1 ("No fast-path command or tier") must find HERE the reasoning that reverses D1 specifically, so it does not "re-drop" `/fix` as a phantom.

**Plan 21 D1's reasoning was:** every fast-path shape "duplicates a piece the full chain already owns" (§1), so "the duplication-free option set has exactly two members: the full chain (accept the overhead), or hand-fix (no framework machinery)." Four fast-path shapes were rejected; the relevant one is the second — "a thin command on a shared engine → the command itself becomes a wrapper duplicate (a second entry point over the same engine, kept in sync by hand)" (plan 21 §1, second bullet).

**Why that reasoning no longer holds — 2.0's own architecture contradicts it.** Since plan 21 was drafted, the framework deliberately built MULTIPLE thin commands over shared engines and judged each one correct, not a duplicate:

- `/review`, `/verify`, `/grill`, and `/audit` ALL run over the same extracted `src/devforge/lib/_shared/` refutation engine (verified: repo-root `CLAUDE.md` helper-locations table — `/grill` "reuses the `src/devforge/lib/_shared/` refutation engine … same as `/audit` + `/review`"; plan 22 Phase 0 + plan 20 Phase 0 + plan 23 Phase 0 are the extractions). By plan 21 D1's logic `/review` should have folded into `/audit` (a second entry point over the same engine) — yet the framework split them, because the WORKFLOW MOMENTS differ (`/review` = in-pipeline emergent cross-task findings; `/audit` = standalone periodic whole-codebase sweep).
- `/verify` ALREADY reuses `/implement`'s `verify-touched` engine report-only (verified: plan 22 D2 + `src/commands/verify/main.md` PHASE 4 wires `implement_helper verify-touched --iteration 0` as a report). By plan 21 D1's logic `/verify` shouldn't reuse `verify-touched` (a second caller of `/implement`'s machinery) — yet it does, and plan 22 calls it the correct HYBRID-reuse design.

The framework converged on a pattern plan 21 D1 did not anticipate: **shared engine underneath, distinct command surface per distinct workflow moment.** `/fix` fits that pattern exactly. Its moment — remediate a known, pipeline-surfaced, already-scoped defect WITH the gates, WITHOUT re-running spec → plan → breakdown — is as distinct from `/implement`'s moment ("drain a feature's APPROVED TASKS") as `/review`'s moment is from `/verify`'s.

**The staleness fear is a property of the COPY, not of a thin caller.** Plan 21 §1's "kept in sync by hand" objection was true of the v1.28 `/fix` draft (a 23.5K file that COPIED `/implement`'s back-half machinery verbatim — verified: plan 21 §1, first bullet "re-implement machinery the live `/implement` already owns"). It is NOT true of a thin surface that CALLS `implement_helper verify-touched` / `merge-review-panel` / `run-forcing-functions-gate` — those are single source-of-truth binaries; a caller of them cannot drift from them (D6 is the anti-staleness guarantee).

**Plan 21 §5 read honestly argues FOR a gated `/fix`.** Plan 21 §5 (the knowingly-accepted cost of the drop) records that hand-fixes "lose two things a command would have given: the forced regression-test / verify gate; the clean attributed commit + memory entry." A GATED `/fix` RESTORES both — that is precisely its mission. The §5 cost was accepted in plan 21 only because the duplication tax of ANY fast path (§1) was judged worse; once the thin-caller design dissolves the duplication tax (above), the §5 ledger flips and the cost no longer needs accepting.

**What this does NOT reopen.** This supersession is surgical — ONLY plan 21 D1. It does NOT reopen what plan 21 correctly killed:

- **A cold, standalone bug** the developer notices on their own still goes hand-fix / full-chain. The boundary plan 21 §4 drew survives intact — `/fix` is never a free-text cold bug-fixer (D2): the conversational offer fires ONLY when the USER raises a defect the model code-confirms inside the post-`/implement`/pre-`/summarize` window, and every out-of-window or model-originated defect is offered the file-a-bug path only.
- **`/refactor` stays dropped** (D5). Plan 21 §2's argument (front = `/audit`, back = `/implement`, no uncovered slice) is sound and untouched.
- **Plan 21 D2–D6 stand** — the `wip.md` discriminator mechanism, the `_pending`-tail dereferencing, the CHANGELOG/DEVELOPMENT-STATUS conventions, the `/audit` survival (`/security` was subsequently dropped 2026-06-19 — see `CHANGELOG.md`; `/audit` is now the sole surviving standalone command), and the recorded-rationale requirement are all unchanged.

## Reuse architecture (confirmed decisions)

**Thin caller over the shipped back-half engine; the `_shared/` engine reused only where applicable.**

**1. Reuse the installed `implement_helper` back-half verbs unchanged (D3).** `/fix`'s back half is byte-for-byte the same flow `/implement` PHASES 5–7 wire (verified pre-edit):

- `implement_helper verify-touched --files '<json>' --iteration 0` → scope-aware static/build/test with the helper-owned self-repair cap; statuses `{pass, self_repair, failed, isolation_failure, tooling_unavailable}` (verified: `src/commands/implement/main.md:160–172`). `/fix` loops self-repair exactly as `/implement` does (unlike `/verify`, which calls it report-only — `/fix` is a write-path command, so it repairs).
- `implement_helper merge-review-panel --iteration N --reviewer <agent>:<path> …` → the four-reviewer panel (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) merged to one `{clean, escalate, …}` verdict (verified: `src/commands/implement/main.md:176–200`).
- `implement_helper run-forcing-functions-gate` → the constitution forcing-functions gate (verified: `src/commands/implement/main.md:202–212`).
- The two-stage hard gate + `implement_helper wip-commit` (verified: `src/commands/implement/main.md:216–268`).

NO `/implement` behavior change; `/fix` is a SECOND CALLER of these binaries, exactly as `/verify` is a second caller of `verify-touched`. The sole verb change is the additive `wip-commit` task-less mode discovered during build (`## Implementation notes / discovered constraints`, 2026-06-19) — a backward-compatible extension, not a fork.

**2. Reuse `src/devforge/lib/_shared/` where applicable.** `/fix`'s front-half `_scope` step maps the surfaced findings to the touched-file set that feeds `verify-touched --files`. Whether that reuses `_shared/feature_scope.py` (the assembled-feature merge-base diff `/review` + `/verify` use, verified: repo-root `CLAUDE.md` helper-locations — `_shared/feature_scope.py`) or builds a NARROWER finding-targeted scope (the files the findings actually cite, not the whole assembled diff) is OQ-2 — the python-engineer decides at Phase 1. The lean is narrow: `/fix` remediates a finding set, not a whole feature, so the file set fed to `verify-touched` should be the files the fix actually touches, not the entire feature diff.

**3. `/fix` does NOT reuse the `_shared` refutation engine** (`findings_schema` / `_consume` / `_validate` / `_consensus` / `_verify`). `/fix` is not a finder ensemble — it CONSUMES already-refuted findings (`/review` already ran the refutation pass; `/verify` already folded them into a verdict). The refutation engine ran upstream; `/fix` reads its output. State this explicitly so a future session does not wire the refutation engine into `/fix` by analogy with `/review`/`/audit`/`/grill`.

## Helper / orchestrator split + module list

The `_fix/` subpackage is LEAN — `/fix` owns no verdict, no finder ensemble, no AC re-derivation, and no bug-filing, so its own helper surface is small; the heavy lifting is the installed `implement_helper` back-half verbs the orchestrator calls. It uses a verb-registry `_SUBCOMMAND_REGISTRY` in `_cli.py` dispatching `(verb, help, handler)` triples (mirror `_verify/_cli.py` / `_review/_cli.py`), a `main()` argv dispatch, and atomic writes via `tempfile.mkstemp` + `os.replace`. The helper owns the preflight/gate, the findings parsing (read-side), and the finding→file scope mapping; the orchestrator (`main.md`) owns the triage prose, the agent dispatch for the back-half panel, and the phase pacing.

The module list below is a STARTING POINT the python-engineer → python-reviewer loop will right-size — do not treat the optional modules as committed surface.

Modules:

- `__init__.py` — re-export `main` (mirrors `_verify`).
- `_cli.py` — verb registry `_SUBCOMMAND_REGISTRY` + argparse/argv dispatch (mirror `_verify/_cli.py`).
- `_state.py` — run/status state (per-feature run state + status flip, mirroring `_review/_state.py`'s `ReviewState` / `_verify/_state.py`'s `VerifyState`; whether `/fix` needs resumable state given the back-half loop is a Phase-1 call).
- `_preflight.py` — the 4-command setup-chain gate (`/init-forge → /generate-docs → /configure → /constitute`) + feature resolution + `source_root` / `wrapper_mode` resolution from `CLAUDE.md`, mirroring `_verify/_preflight.py` (reads `.devforge/` paths, NOT `.claude/`; do NOT copy `/review`'s stale `.claude/memory/MEMORY.md` check — plan 22 finding F).
- `_findings.py` — parse `specs/[feature]/review.md` findings + `specs/[feature]/verification.md` NEEDS-WORK issues into one working list of remediation items (each: title, severity, files-cited, evidence, source).
- `_scope.py` — map the working list → the touched-file set that feeds `implement_helper verify-touched --files` (OQ-2: narrow finding-targeted vs `_shared/feature_scope.py` assembled diff; lean narrow).
- `_window.py` — detect whether the active feature is in the post-`/implement`, pre-`/summarize` window (implemented-but-not-yet-summarized) so the case-3 conversational offer is gated deterministically (D2 condition 3c). Candidate signals (a STARTING POINT the python-engineer → python-reviewer loop right-sizes — OQ-4): the feature's tasks are all complete AND `specs/[feature]/summary.md` does not yet exist AND the spec is not finalized.

Verbs (kebab-case):

- `preflight` — setup-chain + feature resolution + `source_root`/`wrapper_mode` context.
- `read-findings` — parse `review.md` + `verification.md` NEEDS-WORK issues into the working list.
- `resolve-scope` — map the working list to the touched-file set for `verify-touched`.
- `in-fix-window` — return whether the active feature is implemented-but-not-summarized (the case-3 window gate; OQ-4 decides verb-vs-inline). The always-on `src/CLAUDE.md` rule (Phase 3b) tells the model to run this before offering `/fix` conversationally.
- (`check-status-and-flip` — run state, if Phase 1 decides `/fix` needs it.)

Launchers `fix_helper` (POSIX shell) + `fix_helper.py` (python shim) mirror `verify_helper{,.py}` in structure (verified: `src/devforge/lib/verify_helper.py:16–20` per plan 22 — `_LIB_DIR` `sys.path` insert + `from _verify._cli import main`); `fix_helper.py` imports `from _fix._cli import main`. **Scratch dir literal `${TMPDIR:-/tmp}/forge-fix`** — NOT `forge-verify` / `forge-review` / `forge-audit` / `forge-summarize` (collision avoidance; each command picks a distinct workdir). Note the back-half panel writes its per-reviewer scratch to `${TMPDIR:-/tmp}/forge-implement-review/` exactly as `/implement` PHASE 6 does (verified: `src/commands/implement/main.md:185`) — `/fix` reuses that pattern unchanged.

## The command runtime phases (described inside main.md)

`main.md` wires the runtime flow. (These PHASE numbers are runtime-internal — distinct from the build-phase numbering in `## Execution phases`; build Phase 2 BUILDS this `main.md`.) Each Bash block re-establishes `WORKDIR="${TMPDIR:-/tmp}/forge-fix"` at its top (the `/review`/`/verify` scratch-chain pattern):

- **PHASE 0 — Preflight + feature resolution + findings intake (the D2 boundary).** Gate on the 4-command setup chain; resolve the feature; confirm the feature is in the post-`/implement`/pre-`/summarize` window via `fix_helper in-fix-window` (STOP with "the feature is sealed — file a bug + start a fresh cycle" if it is out of window, D2). Read the surfaced findings via `fix_helper read-findings` (from `review.md` and/or the NEEDS-WORK `verification.md`); a case-3 conversational defect (the USER pointed it out, the model code-confirmed it before proposing `/fix`) is the working-list item when no on-disk pipeline finding matches. STOP with a "no pipeline findings to remediate — run `/review` or `/verify` first, or hand-fix a cold bug" message if the working list is empty AND no case-3 defect was supplied (D2 — `/fix` never invents a defect).
- **PHASE 1 — Triage + scope-estimate (the D7 bounce).** Lightweight triage of the working list; estimate the change. If a "fix" turns out to need an architectural change or a behavior/feature change (not a defect repair), STOP and recommend `/specify` (D7 scope-escalation bounce). Otherwise resolve the touched-file set via `fix_helper resolve-scope`.
- **PHASE 2 — Dispatch the implementing agent at the finding.** Brief the assigned agent (per the file-layer→agent mapping) with the finding(s) + evidence + the touched files. (Architect-guard applies as in `/implement` — the architect never codes; route layer-mixed work per plan 14.)
- **PHASE 3 — Scope-aware verify + self-repair.** `implement_helper verify-touched --files '<json>' --iteration 0`, looping self-repair exactly as `/implement` PHASE 5 (verified: `src/commands/implement/main.md:156–172`).
- **PHASE 4 — Four-reviewer panel.** Fan out the four read-only reviewers and merge via `implement_helper merge-review-panel`, looping to clean exactly as `/implement` PHASE 6 (verified: `src/commands/implement/main.md:176–200`).
- **PHASE 5 — Forcing-functions gate.** `implement_helper run-forcing-functions-gate`, exactly as `/implement` PHASE 6 tail (verified: `src/commands/implement/main.md:202–212`).
- **PHASE 6 — Two-stage hard gate + WIP commit.** The Stage A decisions / Stage B diff read, then `implement_helper wip-commit` on approve, exactly as `/implement` PHASE 7 (verified: `src/commands/implement/main.md:216–268`).
- **PHASE 7 — Present + next step.** Tell the user the fix landed as a `[WIP]` commit and point back to `/verify` to re-verify (re-running `/verify` re-checks the ACs against the remediated diff).

## Execution phases (build order)

Each phase: objective, files touched, helper verbs/modules introduced, an execution agent-loop note, a `## Verify` fenced bash block, and a `DoD:` line. Per repo discipline (`CLAUDE.md`): every `.py` helper change goes through **python-engineer → python-reviewer** with a test written + actually run in the SAME turn (test-immediately-after-write; parsers round-trip REAL producer output, not hand-faked fixtures); every command/spec/reference/CLAUDE.md/plan markdown edit goes through **instruction-author → instruction-reviewer** (route-spec-edits-through-agent-flow); for any Claude-Code-integration concern in the COMMAND SPEC — command frontmatter (`disable-model-invocation`, `argument-hint`), `allowed-tools` entries, the Task-dispatch shape, the emitter/install behavior — verify current conventions via the **claude-code-guide** agent BEFORE writing that spec (confidence is not verification). **This PLAN file is a repo-root design doc and does NOT ship into `.claude/`, so it itself needs no claude-code-guide; Phase 2's `main.md` DOES ship and DOES.** Each phase leaves the system buildable and tests green.

### Phase 0 — Decisions + supersession (doc-only)

**Objective:** record the decisions (D1–D7) and the plan-21-D1 supersession so a future session cannot mistake the reversal for an oversight.

- **Files touched:** this plan (the `## Why supersede plan 21 D1` payload + `## Settled decisions`); a back-pointer in `21-DROP-FIX-REFACTOR-PLAN.md` marking D1 superseded (annotate D1 + the `## Why DROP, not rework` header `→ D1 SUPERSEDED by 26-REINTRODUCE-FIX-PLAN.md (the rest of this plan stands)`; do NOT delete plan 21's rationale — it is still the record for `/refactor` and for the cold-bug boundary `/fix` preserves).
- **Modules/verbs introduced:** none — doc-only.
- **Execution:** instruction-author → instruction-reviewer for both this plan and the plan-21 back-pointer annotation.

#### Verify

```bash
# Plan 21 carries the supersession back-pointer (a future reader finds the reversal, not a phantom):
grep -n "SUPERSEDED\|26-REINTRODUCE-FIX" 21-DROP-FIX-REFACTOR-PLAN.md   # expect: D1 annotated superseded, rest-stands note
# This plan records the reversal reasoning:
grep -n "supersede plan 21 D1\|shared engine underneath" 26-REINTRODUCE-FIX-PLAN.md   # expect: the payload present
```

DoD: this plan records D1–D7 + the supersession reasoning; plan 21's D1 carries a back-pointer to plan 26 noting D1 is superseded and the rest of plan 21 stands; a plan-21 reader cannot mistake the reversal for an oversight; instruction-reviewer loop applied.

### Phase 1 — `_fix/` helper subpackage + launcher

**Objective:** create the `_fix/` subpackage, the launchers, the verb registry, the preflight gate, the findings parser, and the finding→file scope mapper.

- **Files touched:** new `src/devforge/lib/_fix/` subpackage (`__init__.py`, `_cli.py` with `_SUBCOMMAND_REGISTRY` mirroring `_verify/_cli.py`, `_state.py` [if Phase 1 decides `/fix` needs run-state], `_preflight.py`, `_findings.py`, `_scope.py`, `_window.py` [the case-3 window gate — OQ-4]); new launchers `src/devforge/lib/fix_helper` (POSIX shell) + `src/devforge/lib/fix_helper.py` (the `.py` shim mirrors `verify_helper.py:16–20` in structure — `_LIB_DIR` `sys.path` insert + `from _fix._cli import main`).
- **Modules/verbs introduced:** `preflight` (4-command setup-chain gate + feature resolution + `source_root`/`wrapper_mode` from `CLAUDE.md`, mirroring `_verify/_preflight.py`; reads `.devforge/` paths, NOT `.claude/` — do NOT copy plan 22 finding F's stale memory path); `read-findings` (parse `specs/[feature]/review.md` findings + `specs/[feature]/verification.md` NEEDS-WORK issues into one working list); `resolve-scope` (map the working list → the touched-file set for `verify-touched`); `in-fix-window` (return whether the active feature is implemented-but-not-summarized — the case-3 D2 window gate; candidate signals: tasks all complete AND no `specs/[feature]/summary.md` yet AND spec not finalized; OQ-4 decides the exact mechanism + verb-vs-inline — a STARTING POINT the loop right-sizes). Reuse `src/devforge/lib/_shared/` where applicable (OQ-2: narrow finding-targeted scope vs `_shared/feature_scope.py` — the python-engineer decides here; lean narrow).
- **Execution:** python-engineer → python-reviewer per function. **Test-immediately-after-write — parsers round-trip REAL producer output:** `read-findings` round-trips a real `review_helper render-report`-rendered `review.md` AND a real `verify_helper render-report`-rendered `verification.md` NEEDS-WORK report (NOT hand-authored fixtures — per the test-immediately-after-write discipline for parsers reading another tool's output); `preflight` round-trips a real `CLAUDE.md` fixture (gate passes / fails correctly); `resolve-scope` round-trips a real findings working list; `in-fix-window` round-trips real on-disk feature state (tasks-complete + `summary.md`-present/absent + spec-status combinations — in-window returns true, sealed/un-implemented returns false).

#### Verify

```bash
ls src/devforge/lib/_fix/ src/devforge/lib/fix_helper src/devforge/lib/fix_helper.py   # expect: present
grep -n "_SUBCOMMAND_REGISTRY" src/devforge/lib/_fix/_cli.py   # expect: registry present, mirroring _verify
grep -n "from _fix._cli import main" src/devforge/lib/fix_helper.py   # expect: the shim imports _fix
grep -n "read-findings\|resolve-scope\|preflight\|in-fix-window" src/devforge/lib/_fix/_cli.py   # expect: all registered
grep -n "\.devforge" src/devforge/lib/_fix/_preflight.py   # read: only .devforge/ paths
grep -n "MEMORY.md\|.claude/memory" src/devforge/lib/_fix/_preflight.py   # expect: NO match (plan-22 finding F not copied)
# in-fix-window detects the post-/implement, pre-/summarize window (the case-3 D2 gate):
grep -n "summary.md\|in_fix_window\|in-fix-window" src/devforge/lib/_fix/_window.py   # expect: the window signals present
# read-findings round-trips REAL review.md + verification.md producer output:
python -m pytest tests/lib/_fix/   # expect: green (round-trip via the real producers)
```

DoD: `_fix/` subpackage + `fix_helper{,.py}` launchers exist; `preflight` (setup-chain + feature resolution + source-root/wrapper-mode, `.devforge/` paths only), `read-findings` (round-trips real `review.md` + `verification.md`), `resolve-scope`, and `in-fix-window` (the case-3 window gate, round-trips real on-disk feature state) are registered + tested; all `tests/lib/_fix/` tests pass; parser round-trips against real producer output (not hand-faked); python-reviewer loop applied per function.

### Phase 2 — `src/commands/fix/main.md` + references

**Objective:** write the live command spec wiring the front half (findings intake + triage + scope-estimate + D7 bounce) and the back half (delegate to the `implement_helper` verbs).

- **Files touched:** new `src/commands/fix/main.md` (frontmatter `name: fix`, a `description`, `argument-hint`, `disable-model-invocation: true` — mirroring `src/commands/verify/main.md` frontmatter; `allowed-tools` MUST list the three reusable back-half verbs `implement_helper verify-touched`, `implement_helper merge-review-panel`, `implement_helper run-forcing-functions-gate` plus `implement_helper wip-commit` and the `fix_helper` verbs) wiring the `$WORKDIR=forge-fix` scratch-chain, the PHASE-0 preflight + findings intake (D2 empty-list STOP), the PHASE-1 triage + scope-estimate + D7 `/specify` bounce, the PHASE-2 agent dispatch, and PHASES 3–6 delegating to the `implement_helper` back-half verbs (verify-touched → merge-review-panel → run-forcing-functions-gate → hard gate → wip-commit), then the PHASE-7 present + re-`/verify` pointer; new `src/commands/fix/references/*.md` (at minimum a triage / scope-estimate reference + the D7 bounce criteria — right-sized at build time).
- **Modules/verbs introduced:** none — this is the orchestrator spec composing the Phase-1 `fix_helper` verbs + the installed `implement_helper` back-half verbs. The architect-guard (plan 14 — the architect never codes) applies to the PHASE-2 dispatch.
- **Execution:** instruction-author → instruction-reviewer; **claude-code-guide consulted FIRST** for command frontmatter (`disable-model-invocation`, `argument-hint`), the `allowed-tools` entry syntax for the cross-helper `implement_helper` calls, and the four-reviewer Task-dispatch shape BEFORE writing `main.md` (`main.md` ships into `.claude/`; this plan file does not).

#### Verify

```bash
ls src/commands/fix/main.md   # expect: present (+ references/)
grep -n "disable-model-invocation: true\|argument-hint" src/commands/fix/main.md   # expect: frontmatter present
grep -n "forge-fix\|WORKDIR" src/commands/fix/main.md   # expect: the $WORKDIR scratch-chain (forge-fix, NOT forge-verify)
# the three reusable back-half verbs are in allowed-tools and the body:
grep -n "verify-touched\|merge-review-panel\|run-forcing-functions-gate" src/commands/fix/main.md   # expect: all three present
# D2 findings intake + D7 bounce wired:
grep -n "review.md\|verification.md\|read-findings" src/commands/fix/main.md   # expect: consumes pipeline findings (D2)
grep -n "/specify" src/commands/fix/main.md   # expect: the D7 scope-escalation bounce
# no copied back-half machinery (D6) — no re-implemented verify/panel logic, only CALLS:
grep -n "PACKAGE_STACKS\|self-repair cap" src/commands/fix/main.md   # expect: NO match (those live in implement_helper, not copied here)
# install/emit clean (after Phase 4):
grep -rl "{{" src/commands/fix/ 2>/dev/null   # expect: 0 placeholder leaks in source (templates resolve at emit)
```

DoD: `src/commands/fix/main.md` wires the front half (findings intake with the D2 empty-list STOP, triage, scope-estimate, D7 `/specify` bounce) and the back half (delegating to `implement_helper verify-touched` → `merge-review-panel` → `run-forcing-functions-gate` → hard gate → `wip-commit`, D3); `allowed-tools` lists the three reusable back-half verbs; the spec CALLS the verbs and copies no machinery (D6); references right-sized; instruction-reviewer + claude-code-guide loops applied.

### Phase 3 — Wire the proposals (the two command-body offers: cases 1–2)

**Objective:** make `/review` and `/verify` PROPOSE the two-arm fix-or-file OFFER only when their findings/issues list is non-empty (D2 cases 1–2).

- **Files touched:**
  - `src/commands/review/main.md` PHASE 4 — its "Report + summary" close + the next-step pointer (pre-edit: the next-step pointer that today names only `/verify` is at `src/commands/review/main.md:308`; the inline summary render is `:286–293`). Add a `/fix` proposal that fires ONLY when the confirmed/high-stakes findings set is non-empty (D2 case 1) — present the **two-arm OFFER**: (A) run `/fix` to remediate the surfaced findings now (gated), or (B) file a bug to defer — alongside the existing `/verify` next-step. When the report is findings-empty, propose nothing (no phantom `/fix`). Append the proposal AFTER the existing next-step prose at line 308 (i.e., as the final paragraph of PHASE 4 — after `rm -rf "$WORKDIR"` and after `check-status-and-flip --status complete`).
  - `src/commands/verify/main.md` PHASE 8 "Present + next step" (pre-edit: `:290–302`) + PHASE 9 "Issue report + batch bug-filing (NEEDS WORK only)" (pre-edit: `:304–337`). On a NEEDS WORK verdict, present the **two-arm OFFER**: (A) run `/fix` to **remediate now** (gated), or (B) file bugs to **defer** — the two are alternatives, NOT a pipeline (D4). Today PHASE 8's NEEDS WORK branch says "after fixing the blockers via `/implement`, re-run `/verify`" (`:299`) — re-point that to the two-arm offer (re-running `/verify` after `/fix` re-verifies the remediated diff). The PHASE-9 bug-filing stays exactly as-is (it IS the case-2 "file" arm — the defer path); `/fix` does NOT touch `bugs/` (D4).
- **Modules/verbs introduced:** none — spec edits only.
- **Execution:** instruction-author → instruction-reviewer. (No claude-code-guide needed for these edits — they touch prose next-step pointers, not Claude-Code-integration frontmatter/tool syntax; confirm during the instruction-reviewer pass that no `allowed-tools` change is implied.)

#### Verify

```bash
# /review proposes the two-arm offer only on a non-empty finding set:
grep -n "/fix" src/commands/review/main.md   # expect: a non-empty-findings-gated two-arm fix-or-file proposal in PHASE 4
# /verify offers the two-arm fix-or-file choice on NEEDS WORK:
grep -n "/fix" src/commands/verify/main.md   # expect: /fix proposed on NEEDS WORK as the remediate-now arm
# /verify PHASE 9 bug-filing is unchanged (the case-2 file/defer arm; /fix does NOT touch bugs/):
grep -n "file-bugs\|Source: verify" src/commands/verify/main.md   # expect: PHASE 9 bug-filing intact
```

DoD: `/review` PHASE 4 proposes the two-arm fix-or-file offer ONLY when the findings set is non-empty (case 1); `/verify` PHASE 8/9 presents the two-arm offer on NEEDS WORK — (A) `/fix` remediate now vs (B) file bugs to defer (alternatives per D4, not a pipeline; case 2); PHASE 9's bug-filing is unchanged (it is the case-2 file arm); neither proposal fires on an empty finding/issue set; instruction-reviewer loop applied.

### Phase 3b — Wire the conversational offer (case 3) as an always-on `src/CLAUDE.md` rule

**Objective:** wire the case-3 CONVERSATIONAL offer, which CANNOT live in a command body (it happens in free conversation, with no slash command executing). Its only possible home is an always-on behavioral rule in the consumer overlay `src/CLAUDE.md` — the ONLY mechanism that can host a non-command (conversational) behavior.

- **Files touched:** `src/CLAUDE.md` — add a TIGHT always-on behavioral rule:

  > When the user points out a defect and you confirm it by reading the actual code, AND the active feature is implemented-but-not-yet-summarized (run `fix_helper in-fix-window`): offer the user the choice — run `/fix` to remediate now, or file a bug to defer. In any other situation (the defect is unconfirmed or you originated it, or no feature is in that window), offer only to file a bug — never `/fix`.

  This rule carries an always-on token cost — per the plan-08 always-on-trim discipline (`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`), it MUST be kept to a tight block; the mechanics live in `main.md`, the rule only states the conversational trigger + the two-arm offer. The model NEVER auto-invokes `/fix` (every forge command sets `disable-model-invocation: true`) — the rule makes the model PROPOSE; the user types `/fix`. The offer is the same TWO-ARM choice as cases 1–2 (run `/fix` now / file a bug to defer), consistent with D4 (filing is a separate action; `/fix` never writes or closes `bugs/`).
- **Modules/verbs introduced:** none — consumes the Phase-1 `in-fix-window` verb (OQ-4 — verb vs inline state check); no new helper.
- **Execution:** instruction-author → instruction-reviewer; **claude-code-guide consulted** for the `src/CLAUDE.md` always-on-rule authoring (this file ships into the target project as the consumer overlay — a Claude-Code-integration concern).

#### Verify

```bash
# the case-3 conversational always-on rule is present (tight block, plan-08 discipline):
grep -n "in-fix-window\|implemented-but-not-yet-summarized\|remediate now" src/CLAUDE.md   # expect: the tight always-on conversational-offer rule
# the rule states file-only everywhere else (never /fix out of window):
grep -n "only to file a bug\|never \`/fix\`" src/CLAUDE.md   # expect: the out-of-window file-only clause
```

DoD: `src/CLAUDE.md` carries a TIGHT always-on rule wiring the case-3 conversational two-arm offer (user-raised AND code-confirmed AND in-window → offer `/fix` or file-a-bug; every other moment → file only, never `/fix`), gated on `fix_helper in-fix-window`, kept to a tight block per the plan-08 always-on-trim discipline; the rule never auto-invokes `/fix` (proposes only); instruction-reviewer + claude-code-guide loops applied.

### Phase 4 — Emit + docs reconcile

**Objective:** make `/fix` emit + install, and reconcile every doc that references `/fix` (including re-pointing `storage-rules.md` per D4).

- **Add `"fix"` to the emitter `_PROMOTED` tuple** — `scripts/emitters/claude.py:51` (verified this session: the tuple ends `…, "grill", "summarize")` and does NOT contain `fix`). Append `"fix"`. (The `_PROMOTED` edit is a one-line Python tuple change — python-engineer → python-reviewer; confirm `tests/scripts/` still passes.)
- **Add a `src/CLAUDE.md` catalog entry** for `/fix` — a PURPOSE ONE-LINER per the plan-08 trim discipline (mechanics live in `main.md`): proposal-only gated remediation of `/review`/`/verify` findings, reuses `/implement`'s back-half gates, writes a `[WIP]` commit, does not touch `bugs/`. Add a **workflow-chain annotation** showing `/fix` as a conditional remediation loop off `/review` and `/verify` — model it on how `[/grill]` is shown as optional/bracketed in the "Spec-Driven Development Flow" code block (verified: `src/CLAUDE.md` Workflow chain renders `… /plan → [/grill] → /breakdown …` with `(optional, high-stakes)` beneath). The exact representation (a bracketed conditional-loop annotation vs catalog-only) is OQ-3.
- **Re-point `src/devforge/storage-rules.md` (D4)** — it currently claims a `fix` command CLOSES bug files; that framing is stale (`/fix` is findings-only, never touches `bugs/`). Correct three sites (verified pre-edit this session):
  - The File Lifecycle line `fix          → updates bugs/NNN-description.md status to Fixed (when given a bug file)` (`storage-rules.md:159`) — REMOVE it (`/fix` writes no `bugs/` file; the `verify` lifecycle line at `:155` already covers Phase-9 bug CREATION; nothing in the framework now mutates bug status programmatically). After removing the stale `:159` line, INSERT a new `/fix` lifecycle entry into the File Lifecycle block: `fix          → writes a [WIP] commit in the source repo (no spec/bugs/ files written)` — so `/fix` appears in the inventory as a command whose output is a git commit only.
  - The Status Lifecycle `In Progress` wording `currently being fixed via the fix command` (`storage-rules.md:264`) — degeneralize to "currently being fixed" (the `Open → In Progress → Fixed` lifecycle stays MANUAL, D4).
  - The "How Bug Files Are Resolved" section (`storage-rules.md:322–324`) — replace `` `fix bugs/NNN-xxx.md` — reads the bug file, fixes the issue, updates status to Fixed `` with a manual-resolution line: bug files are closed MANUALLY (the user edits `**Status**: Fixed` after resolving), or by re-running `/verify` (which re-proves the ACs against the remediated diff). Also re-confirm + degeneralize the two "fix command" field-notes references at `:309` (`Fix Notes` "[Filled in by the fix command after resolution …]" → "[Filled in after resolution …]") and `:315` ("Helps the fix command know what else is being addressed" → "Helps whoever resolves the batch know what else is being addressed"). Re-read each line on edit; the `Status` enum + `## Fix Notes` HEADING themselves stay (manual lifecycle).
- **Add a `CHANGELOG.md` entry** — under `## [Unreleased]` (Keep-a-Changelog convention; an `### Added` subsection): reintroduce `/fix` as a proposal-only gated pipeline-remediation command reusing `/implement`'s back half, superseding plan 21 D1. Do NOT rewrite plan 21's `### Removed` entry (it remains accurate for `/refactor` + for the cold-bug boundary).
- **Add this plan to the active-plans list in the repo-root `CLAUDE.md`** — a plan-26 entry in the numbered active-work list (matching the existing entries' density + the "supersedes plan 21 D1 only" framing).
- **Cross-ref sweep** of every `/fix` reference after the wire-in (re-confirm each aligns):
  - `scripts/emitters/claude.py:51` — `"fix"` ADDED to `_PROMOTED` (above).
  - `src/CLAUDE.md` — the new catalog entry + the Workflow-chain annotation (above) + the Phase-3b case-3 conversational always-on rule (a separate `/fix` reference site; re-confirm it aligns with the catalog one-liner + does not duplicate the mechanics that live in `main.md`).
  - `src/devforge/storage-rules.md` — re-pointed per D4 (above); `:155` `verify` lifecycle line confirmed accurate, no change.
  - repo-root `CLAUDE.md:24,25` — the plan-14 + plan-15 status summaries name `/fix` as APPEND-ONLY HISTORY (plan 21 `## Out of scope` flagged these as intentional history). LEAVE UNTOUCHED — they record past work, not a live surface. The new plan-26 entry is the live record of the reintroduction.
  - `21-DROP-FIX-REFACTOR-PLAN.md` — the D1 supersession back-pointer (Phase 0); CHANGELOG history exception (D4 there) unchanged.
- **Install-ride verification** (mirror plans 10/11/20/22): run `install.sh <tmp-target>` and confirm `fix command: yes (folder, N references)` (N = the reference-file count from Phase 2, auto-globbed by the emitter), **0 `{{` placeholder leaks** in the emitted command, and an **executable `fix_helper`** installed at `.devforge/lib/fix_helper`.
- **Execution:** the `_PROMOTED` edit + the `tests/scripts/` re-run via python-engineer → python-reviewer; the `src/CLAUDE.md` + `storage-rules.md` + `CHANGELOG.md` + repo-root `CLAUDE.md` markdown reconciliation via instruction-author → instruction-reviewer; claude-code-guide consulted for the emitter/install behavior.

#### Verify

```bash
# fix promoted in the emitter:
grep -n "\"fix\"" scripts/emitters/claude.py   # expect: "fix" in _PROMOTED
# storage-rules re-pointed (D4) — no live "fix command closes bugs" claim:
grep -n "fix command\|via the fix command\|fix bugs/NNN" src/devforge/storage-rules.md   # expect: NO match (all degeneralized to manual / re-run /verify)
grep -n "^fix " src/devforge/storage-rules.md   # expect: NO match (the File Lifecycle fix→bugs line removed)
# src/CLAUDE.md catalog + workflow annotation present, modeled on [/grill]:
grep -n "/fix" src/CLAUDE.md   # expect: the new catalog one-liner + the conditional-loop annotation
# this plan is in the repo-root active-plans list:
grep -n "26-REINTRODUCE-FIX" CLAUDE.md   # expect: the plan-26 active-work entry
# CHANGELOG records the reintroduction under [Unreleased]:
grep -n "fix" CHANGELOG.md | head   # expect: an ### Added [Unreleased] reintroduction entry
# full cross-ref sweep — no dangling /fix references (excluding the intentional history + helper-internal hits):
grep -rn "/fix\|fix command" src/ scripts/ CLAUDE.md CHANGELOG.md | grep -v "fix_helper\|_fix/\|14-ARCHITECT\|15-AGENT\|prefix\|fixture\|fix the\|fixed\|fixing"   # read: only the inventoried, still-accurate references
# install ride:
#   install.sh <tmp> reports: fix command: yes (folder, N references); 0 '{{' leaks; .devforge/lib/fix_helper executable
python -m pytest tests/scripts/   # expect: green (emit still works with fix added)
```

DoD: `fix` is in `_PROMOTED` (so it emits/installs); `src/CLAUDE.md` carries the catalog one-liner + the conditional-loop workflow annotation (modeled on `[/grill]`); `src/devforge/storage-rules.md` is re-pointed (D4 — no claim that a `fix` command closes bug files; the `Open → In Progress → Fixed` lifecycle is MANUAL); `CHANGELOG.md` has the `[Unreleased]` reintroduction entry; the repo-root `CLAUDE.md` active-plans list has the plan-26 entry; the cross-ref sweep is clean (only the intentional plan-14/15 history at `CLAUDE.md:24,25` survives as `/fix` residue); the install ride shows `fix command: yes` with N references, 0 `{{` leaks, and an executable helper; author→reviewer + python→reviewer + claude-code-guide loops applied.

### Phase 5 — testForge20 e2e (USER-DRIVEN — HARD GATE)

**WAIVED 2026-06-19 (maintainer) — NOT executed.** The build shipped without this runtime gate; the steps below remain the validation recipe for whenever an e2e is run, but plan 26 is marked DONE (build) without it. `/fix` is build-verified, not runtime-e2e-validated.

**Objective:** the repo's standard manual e2e gate — confirm `/fix` works end to end as a pipeline-remediation loop off `/review` (and/or `/verify`).

- Re-install the forge into testForge20 (so the new `/fix` source is emitted), run a feature through `/implement` → `/review` (confirm `/review` PROPOSES `/fix` when its findings set is non-empty), then run `/fix` (confirm it remediates the surfaced findings via the reused `implement_helper` back-half engine — verify with self-repair → four-reviewer panel → forcing-functions gate → hard gate → `[WIP]` commit), then re-run `/verify` (confirm re-verification passes against the remediated diff).
- **Success looks like:** `/review` proposes `/fix` only when its report has findings; `/fix` gates on the setup chain, intakes the findings (STOPS with the "no pipeline findings" message on an empty list), triages, dispatches the implementing agent at the finding, runs verify-touched + the four-reviewer panel + the forcing-functions gate exactly as `/implement` does, lands the fix as a `[WIP]` commit, and writes NO `bugs/` file; a `/verify` re-run re-proves the ACs; a "fix" that turns out to need an architectural/behavior change triggers the D7 `/specify` bounce instead of a code change.
- Confirm the install ride (can be checked now): `fix command: yes (folder, N references)`, 0 `{{` leaks, executable helper.
- Mark DONE only after user sign-off.

#### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# Observe during the /implement → /review → /fix → /verify run:
#   - /review proposes /fix ONLY when its findings set is non-empty (no phantom proposal on a clean report).
#   - /fix preflight gates the setup chain + resolves the feature + reports Source Root.
#   - /fix read-findings intakes review.md (and/or verification.md NEEDS-WORK issues); STOPS on an empty list.
#   - /fix triage runs; a defect routes to the agent, an architectural/behavior change triggers the D7 /specify bounce.
#   - verify-touched loops self-repair; the four-reviewer panel merges to clean; the forcing-functions gate passes.
#   - the two-stage hard gate runs; on approve, a single [WIP] commit lands; NO bugs/ file is written.
#   - re-running /verify re-proves the ACs against the remediated diff.
```

DoD: e2e confirms `/review` proposes `/fix` on a non-empty finding set, `/fix` remediates the surfaced findings through the reused `implement_helper` back-half engine (verify → panel → forcing-functions → hard gate → `[WIP]` commit) and writes no `bugs/` file, the D7 `/specify` bounce fires on a non-defect, and a `/verify` re-run re-verifies the remediated diff; user-driven sign-off.

## Settled decisions

### D1 — Reintroduce `/fix`, superseding plan 21 D1 (only D1)

Reintroduce a `/fix` command. This supersedes ONLY plan 21's D1 ("No fast-path command or tier"); every other plan-21 decision stands. The rationale is the `## Why supersede plan 21 D1` payload: the framework converged on "shared engine underneath, distinct command surface per distinct workflow moment" (`/review` vs `/verify` over `_shared/`; `/verify` reusing `verify-touched`), a pattern plan 21 D1 did not anticipate; `/fix`'s moment is as distinct from `/implement`'s as `/review`'s is from `/verify`'s; the staleness fear was a property of the v1.28 COPY draft, not of a thin CALLER (D6); and plan 21 §5's accepted cost (lost verify gate + lost clean commit) is exactly what a gated `/fix` RESTORES.

### D2 — The fix-or-file OFFER fires in exactly THREE in-window situations; everywhere else, file only

> **⚠ AMENDED 2026-08-26 by `88-COLD-FIX-BUGS-LANE-PLAN.md` (Phases 0–4 built). Two narrow changes; the rest of D2 stands verbatim.**
>
> **(1) The free-text ban is EXTENDED, not reversed.** D2's refusal of a free-form *"describe a bug"* input is intact and is still enforced — there is no argument form and no prompt that turns typed prose into a working-list item. What plan 88 added is a FOURTH intake that is not free text: an explicit `bugs/NNN-<slug>.md` FILE argument. A bug file is a WRITTEN finding with a title, severity, evidence and a file table, produced by `/devforge:report-bug`, so *"consumes findings, never invents them"* stays literally true. **A future session must still NOT add a free-text intake** — that half of D2 is untouched.
>
> **(2) The window rule is amended for FEATURE-LESS runs only.** D2's *"everywhere else, file only"* and its in-window rationale below bind runs that HAVE a feature. Plan 88's cold lane has no feature directory at all, so it skips feature resolution, the `in-fix-window` gate and the `read-findings` call — not as an exemption, but because each needs a `--feature` that does not exist. **The sealed-unit reasoning in the rationale paragraph below is NOT weakened**: a cold run is not fixing inside a feature unit, it writes no `[WIP]` commit, and it lands a standalone `fix(scope):` commit belonging to no feature's history. ⚠ **One protection IS genuinely lost and is recorded rather than argued away**: the window gate also refused to run mid-`/devforge:implement` (`not_all_tasks_complete`), and the cold lane has no such interlock.
>
> The three in-window situations D2 enumerates are unchanged; plan 88 added a fourth situation that is out-of-window by construction.

When a bug exists, the model presents a **TWO-ARM OFFER** to the user: **(A) run `/fix` to remediate now**, or **(B) file a bug to defer**. The model NEVER auto-invokes `/fix` — every forge command sets `disable-model-invocation: true` (verified: the convention in repo-root `CLAUDE.md` — the model can only PROPOSE; the user types `/fix`). The offer is never made on the model's own hunch.

The fix-or-file offer fires in exactly THREE situations, ALL inside the **post-`/implement`, pre-`/summarize` window** — the window where the feature's code exists but is not yet sealed (WIP commits still open, not squashed/finalized):

1. **`/review` surfaces findings** → the `/review` command body proposes the offer (Phase 3 `/review` wiring).
2. **`/verify` returns NEEDS WORK** → the `/verify` command body proposes the offer (Phase 3 `/verify` wiring; `/verify` PHASE 9 `file-bugs` already IS the "file" arm).
3. **Conversationally** → ONLY when ALL THREE of: (a) the USER points out the bug (the model never originates it), AND (b) the model CONFIRMS it is a real defect by reading the actual code (ground the confirmation in the code, do NOT rubber-stamp), AND (c) the active feature is in the post-`/implement`, pre-`/summarize` window. All three are mandatory — this is an AND, not an any-of. Case 3 has no command body to host it, so it lives as an always-on behavioral rule in the consumer overlay `src/CLAUDE.md` (Phase 3b).

In EVERY OTHER moment — before `/implement`, after `/summarize`/`/finalize` has sealed the feature, no active in-window feature, or a defect the user did not raise (a cold or model-originated bug) — the model offers ONLY to **file a bug** (the defer arm). It must NOT offer `/fix`. A standalone cold bug the user notices independently still goes file-a-bug / full-chain (plan 21 §4's boundary preserved); `/fix` is never a free-text cold bug-fixer.

**Why the window gates the offer:** in-window the feature's WIP commits are still open, so an in-place `/fix` (reusing the implement back-half engine) lands cleanly as another `[WIP]` commit on the open unit. Once `/summarize`/`/finalize` squashes and seals the feature, fixing in place would corrupt a sealed unit, so a later bug goes to a bug file + a fresh cycle. The two-arm offer maps onto D4: `/fix` = remediate now; the bug file = defer; `/fix` itself still does NOT touch `bugs/` (filing is a SEPARATE action offered as the alternative arm).

**Case-3 assurance asymmetry:** case 3's confirmation is SINGLE-MODEL — it does NOT get the refutation / cross-examination engine (plan 19) that `/review`/`/verify` (cases 1–2) run to filter false positives, so it is lower-assurance than cases 1–2. The mitigation is built into the gating: the USER raised the defect (it is not a model hunch) and the model must GROUND the confirmation by reading the actual code before offering (condition 3b — not droppable).

### D3 — Full `/implement` back-half reuse

`/fix`'s back half is the same operations as `/implement` PHASES 5–7 (verify-touched → merge-review-panel → run-forcing-functions-gate → hard gate → wip-commit), wired as `/fix` PHASES 3–6 (the forcing-functions gate is a separate phase from the review panel, unlike in `/implement` where both live in PHASE 6): `implement_helper verify-touched` (with self-repair) → `merge-review-panel` (the four-reviewer panel `code-reviewer`/`qa-reviewer`/`security-reviewer`/`performance-analyst`) → `run-forcing-functions-gate` → the two-stage hard gate → `wip-commit`. **Decided over a lighter single-reviewer loop:** the strongest gates, zero staleness (single source-of-truth binaries), and no second review path to maintain. NO `/implement` / `implement_helper` change — **EXCEPT** the one additive, backward-compatible `wip-commit` task-less mode discovered during build (`/implement` stays byte-identical); see `## Implementation notes / discovered constraints` (2026-06-19).

### D4 — Findings-only; `/fix` does NOT touch `bugs/`

> **⚠ AMENDED 2026-08-26 by `88-COLD-FIX-BUGS-LANE-PLAN.md` (Phases 0–4 built). NARROW — the creation ban is absolute and permanent; only the CLOSE half moved.**
>
> **`/devforge:fix` still CREATES no `bugs/` file, ever, in either lane** — `/devforge:report-bug` remains the sole creator and the "defer" arm, exactly as D4 says. **The in-window (feature) lane still writes no `bugs/` file at all**, so D4 is unchanged for every situation D4 was written about.
>
> **What changed:** the new COLD lane, entered only on an explicit `bugs/NNN-<slug>.md` argument, flips **that ONE file** — and only that one — to `**Status**: Fixed` with its `**Fixed**:` date and `## Fix Notes` filled, after the two-stage hard gate approves and the remediation commit lands. It is performed by a helper verb (`fix_helper close-bug` over `_shared/bug_file.py`), which refuses the close when the file is not `Open`/`In Progress` or when its `## Fix Notes` body is no longer the placeholder — **hand-written notes are never overwritten**.
>
> **So the `Open → In Progress → Fixed` lifecycle is no longer manual-ONLY**; the manual path remains valid and is still the ordinary one. `src/devforge/storage-rules.md` was reconciled at Phase 4 accordingly. See also the `## Deferrals / follow-ups` `close-bug` bullet, which this COLLECTS.

`/fix` is the "remediate now" path; `bugs/` filing (by `/verify` PHASE 9) is the "defer" path — they are ALTERNATIVES, not a pipeline. `/fix` writes no `bugs/` file and closes none. The `bugs/` `Open → In Progress → Fixed` lifecycle stays MANUAL (the user edits the status after resolving, or re-runs `/verify`). This plan re-points `src/devforge/storage-rules.md` so it no longer claims a `fix` command closes bug files: it REMOVES the `fix → updates bugs/… to Fixed` File Lifecycle line (`:159`), degeneralizes the `In Progress` "via the fix command" wording (`:264`), and rewrites "How Bug Files Are Resolved" (`:322–324`) to manual / re-run-`/verify`. A future `close-bug` consumer is explicitly DEFERRED (see `## Deferrals / follow-ups`).

### D5 — `/refactor` stays dropped

Plan 21's drop of `/refactor` is sound (its front half duplicates `/audit`'s analysis; its back half duplicates `/implement`; no uncovered slice — plan 21 §2) and is UNTOUCHED by this plan. Do NOT reintroduce `/refactor`.

### D6 — Thin surface, no copied machinery (the anti-staleness guarantee)

`/fix` CALLS the existing `implement_helper` verbs (`verify-touched`, `merge-review-panel`, `run-forcing-functions-gate`, `wip-commit`); it never re-implements them. Because those are single-source-of-truth binaries, a caller of them cannot drift from them — this is the structural answer to plan 21 §1's "kept in sync by hand" staleness objection (which was true of the v1.28 COPY draft, not of a thin caller). Do NOT resurrect or port the deleted v1.28 `fix.md` draft. (Build-time refinement: `wip-commit` needed an additive task-less mode for `/fix` to call it honestly — extending the one binary, NOT adding a fix-side commit composer, is exactly how D6's single-source-of-truth principle is preserved; see `## Implementation notes / discovered constraints` (2026-06-19).)

### D7 — Scope-escalation bounce to `/specify`

If during triage a "fix" turns out to need an architectural change or a behavior/feature change (not a defect repair), `/fix` STOPS and recommends `/specify` (the same guard the v1.28 draft had — re-built fresh, not copied, per D6). `/fix` remediates defects, not feature work; feature/architecture changes re-enter the spec pipeline.

## Implementation notes / discovered constraints

### 2026-06-19 — `wip-commit` is task-coupled; `/fix` gets an ADDITIVE task-less mode (the ONE `implement_helper` change)

D3, D6, and the `## Out of scope` "Changing `implement_helper`" bullet originally asserted "NO `/implement` / `implement_helper` change." That boundary was premised on `wip-commit` being reusable AS-IS. While authoring `src/commands/fix/main.md` PHASE 6 that premise proved **false**, so this note records the discovered constraint + the decision so a future session does not read the original "no `implement_helper` change" wording as still-absolute and get confused.

- **Discovered constraint:** `implement_helper wip-commit` is **task-coupled**. Its `--task-file`/`--index`/`--number` were `required=True`, it STAGES the task file + index alongside the touched files in standalone mode, and it embeds task-shaped detail in the message (`_implement/_cmds_commit.py` `cmd_wip_commit`). A `/fix` remediation has NO task file, so `/fix` cannot call `wip-commit` honestly as it stood — a real task-path would stage an unrelated file into the remediation commit, and a fake path would fail `git add`.
- **Decision:** add an **ADDITIVE, backward-compatible task-less mode** to `wip-commit` — `--task-file`/`--index`/`--number` become OPTIONAL. When all three are absent, the verb enters fix mode: it stages ONLY the touched `--files` (no task file, no index) and writes a `[WIP] fix: <title>` message (standalone) / `[TICKET-ID] - <title>` (wrapper, ticket derived from the source branch). `--files` + `--title` remain required.
- **`/implement` is BYTE-IDENTICAL.** `/implement` PHASE 7 keeps passing all of `--task-file`/`--index`/`--number`, so the task-shaped staging + message path is exactly as before; the new mode is reachable only when those flags are omitted, which only `/fix` does.
- **This is the ONLY `implement_helper` change in the plan.** It was chosen over the alternative — a fix-side commit path (a dedicated `fix_helper commit` verb that re-derives the wrapper/attribution message composition) — precisely to preserve **D6's single-source-of-truth principle**: a second commit composer would duplicate the wrapper/`[TICKET-ID]`/attribution logic and risk drifting from `wip-commit`. Extending the one binary keeps the composition single-sourced. No other back-half verb (`verify-touched`, `merge-review-panel`, `run-forcing-functions-gate`) and no `/implement` behavior changes.

## Open questions (OQ-N)

- **OQ-1 — persisted vs live findings.** Does `/fix` read PERSISTED findings (`review.md` / `verification.md` on disk, re-runnable) or only the live in-session findings? **Lean: persisted** — `read-findings` parses the on-disk artifacts, so `/fix` works in a fresh session after `/review`/`/verify` ran earlier (and so the parser can round-trip real producer output per the test discipline). Resolve at the Phase 1 build.
- **OQ-2 — `_fix` `_scope` vs `_shared/feature_scope.py`.** Does `_fix` need its own narrow `_scope` (findings → the files the fix actually touches) or reuse `_shared/feature_scope.py` (the whole assembled-feature merge-base diff)? **Lean: narrow finding-targeted scope** — `/fix` remediates a finding set, not a whole feature, so feeding `verify-touched` the narrow touched set is tighter than the assembled diff. The python-engineer decides at Phase 1.
- **OQ-3 — workflow-chain representation in `src/CLAUDE.md`.** A conditional-loop annotation in the "Spec-Driven Development Flow" code block (modeled on the bracketed `[/grill]` optional step) vs catalog-only (a `#### /fix` Command-Details entry without touching the flow diagram). **Lean: a conditional-loop annotation** so the model-facing always-on catalog (plan 08 — the only model-facing command-awareness source) advertises `/fix` as a real remediation loop, not a phantom. Resolve at the Phase 4 build.
- **OQ-4 — case-3 window-detection mechanism.** The exact way the case-3 conversational always-on rule (Phase 3b) detects the post-`/implement`/pre-`/summarize` window: a dedicated `fix_helper in-fix-window` verb the rule tells the model to run (the `_window.py` module + the candidate signals — tasks all complete AND no `specs/[feature]/summary.md` yet AND spec not finalized), vs an inline state check documented in the always-on rule text itself. **Lean: a helper verb** — so the always-on rule stays short (plan-08 discipline) and the detection is deterministic rather than model-judged. Resolve at the Phase 1 build (the verb) + Phase 3b (how the rule invokes it).

## Deferrals / follow-ups

- **A `bugs/` `Open → Fixed` consumer (a `close-bug` verb)** — explicitly NOT built (D4 chose findings-only; `/fix` never touches `bugs/`, and the lifecycle stays MANUAL). A future plan could add a `close-bug` verb (to `_verify` or a new helper) if the manual close proves painful in practice. Recorded so a future session does not mistake the manual-close design for an oversight. **⚠ COLLECTED 2026-08-26 — this deferral's trigger fired and the verb was built.** `88-COLD-FIX-BUGS-LANE-PLAN.md` ships `fix_helper close-bug` over a new function in `src/devforge/lib/_shared/bug_file.py` (beside the existing writer, so the bug-file format stays single-sourced). The trigger that fired was not "the manual close proves painful" in isolation but the stronger finding that `bugs/` files had **no consumer at all** — two producers, no reader — with `/devforge:report-bug`'s own forward pointer naming `/devforge:research`, which had zero `bugs/` awareness. **This bullet is retained rather than deleted**: it is the record that the verb was chartered here first, so its arrival is a collected deferral, not an unplanned reversal.
- **The "file a bug" ARM of the offer (D2 arm B) depends on a bug-filing capability only PARTLY built today** — a known dependency, NOT a blocker. The case-2 file arm is covered: `/verify` PHASE 9 `file-bugs` already writes `bugs/NNN-*.md` (`Source: verify`). But a STANDALONE conversational "file a bug" command (`report-bug`) is still `_pending`/unbuilt (`src/_pending/commands/report-bug.md`). So for case 3 + all out-of-window moments, the file arm either writes a `bugs/NNN-*.md` directly in the `src/devforge/storage-rules.md` format or waits on `report-bug` being promoted. This is consistent with D4: the file arm writes `bugs/`; `/fix` (arm A) never does. Recorded so a future session knows the file arm's standalone path is a dependency to satisfy, not a `/fix`-side write.

## Out of scope (do NOT plan here)

- **Resurrecting or porting the deleted v1.28 `fix.md` draft** (D6 — it copied `/implement`'s back-half; this plan builds a thin CALLER fresh).
- **Reintroducing `/refactor`** (D5 — plan 21's drop of it stands).
- **A cold / free-form bug-fixer entry to `/fix`** (D2 — the offer fires only in the 3 in-window situations; cold or out-of-window bugs get the file-a-bug arm only, never `/fix`).
- **`/fix` writing or closing `bugs/` files** (D4 — findings-only; the `bugs/` lifecycle is manual; the `close-bug` consumer is deferred).
- **Changing `/implement` behavior, or the `verify-touched` / `merge-review-panel` / `run-forcing-functions-gate` back-half verbs** (D3/D6 — `/fix` is a second CALLER of these unchanged binaries). The **one carved-out exception** is the additive, backward-compatible `wip-commit` task-less mode discovered during build (`--task-file`/`--index`/`--number` made optional so `/fix` can commit without a task; `/implement` keeps passing them and stays byte-identical) — see `## Implementation notes / discovered constraints` (2026-06-19). That ONE additive verb extension is in scope; every other `implement_helper` change and any `/implement` behavior change remains out.
- **Reopening any plan-21 decision other than D1** (D2–D6 there stand; the `/refactor` drop, the `wip.md` mechanism, the `_pending`-tail dereferencing, the CHANGELOG/DEVELOPMENT-STATUS conventions, and `/security`+`/audit` survival are all unchanged).
- **Reshaping the plan-15 agent roster.** `/fix`'s PHASE-2 dispatch uses the existing file-layer→agent mapping + the plan-14 architect-guard; no agent is added or reshaped.

## Context for next session

- `/fix` is a **gated pipeline-remediation** command OFFERED (never auto-invoked — every forge command sets `disable-model-invocation: true`) as the "remediate now" arm of a TWO-ARM fix-or-file offer, in exactly THREE in-window situations (D2): `/review` findings, `/verify` NEEDS WORK, or a conversational defect the USER raised AND the model code-confirmed while the active feature is post-`/implement`/pre-`/summarize`. In every other moment the model offers ONLY to file a bug — never `/fix`. `/fix` is NOT a cold general bug-fixer (D2) and NOT a linear pipeline step. Its defining job: remediate a known, already-scoped defect WITH `/implement`'s full per-task gates, WITHOUT re-running spec → plan → breakdown. It reuses `/implement`'s back half byte-for-byte by CALLING `implement_helper verify-touched` / `merge-review-panel` / `run-forcing-functions-gate` / `wip-commit` (D3/D6 — a thin caller, never a copy). See the `/implement`-vs-`/fix` invariant table in `## Command mission`.
- **This supersedes ONLY plan 21 D1** (`## Why supersede plan 21 D1`): the framework converged on "shared engine underneath, distinct command surface per distinct workflow moment" (`/review` vs `/verify` over `_shared/`; `/verify` reusing `verify-touched`) — a pattern plan 21 D1 did not anticipate; the staleness fear was a property of the v1.28 COPY, not of a thin caller; plan 21 §5's accepted cost (lost verify gate + clean commit) is what a gated `/fix` RESTORES. Plan 21 D2–D6 + the `/refactor` drop stand. Plan 21's D1 carries a Phase-0 back-pointer to this plan so the reversal is not mistaken for an oversight.
- **7 settled decisions:** D1 reintroduce `/fix` (supersede plan 21 D1 only); D2 the two-arm fix-or-file OFFER fires in exactly 3 in-window situations (`/review` findings / `/verify` NEEDS WORK / user-raised + code-confirmed conversational defect, all post-`/implement`/pre-`/summarize`), everywhere else file-only — never auto-invoked, never a cold fixer, case-3 confirmation is single-model (lower-assurance, mitigated by user-raised + code-grounded gating); D3 full `/implement` back-half reuse; D4 findings-only (no `bugs/`); D5 `/refactor` stays dropped; D6 thin caller, no copied machinery; D7 scope-escalation bounce to `/specify`.
- **`_fix/` is LEAN** (no verdict, no finder ensemble, no AC re-derivation, no bug-filing): `_cli.py` registry, `_preflight.py` (setup-chain + feature resolution + source-root/wrapper-mode, `.devforge/` paths), `_findings.py` (`read-findings` — parse `review.md` + `verification.md` NEEDS-WORK issues), `_scope.py` (`resolve-scope` — finding→file set for `verify-touched`), `_window.py` (`in-fix-window` — the case-3 post-`/implement`/pre-`/summarize` window gate; OQ-4), optional `_state.py`. Launchers `fix_helper{,.py}` mirror `verify_helper{,.py}` (`verify_helper.py:16–20`). Scratch literal `${TMPDIR:-/tmp}/forge-fix`; the back-half panel reuses `${TMPDIR:-/tmp}/forge-implement-review/` (`implement/main.md:185`).
- **6 build phases + the e2e gate (Phases 0–4 DONE + committed; Phase 5 WAIVED — NOT executed):** 0 decisions + plan-21-D1 supersession (doc-only) → 1 `_fix/` subpackage + launcher (preflight, read-findings, resolve-scope, in-fix-window; parsers round-trip real `review.md`/`verification.md`) → 2 `main.md` + references (front-half triage + D7 bounce; back-half delegate to `implement_helper`) → 3 wire the `/review` + `/verify` command-body offers (cases 1–2, non-empty-only; the two-arm fix-or-file choice) → 3b wire the case-3 conversational offer as a TIGHT always-on `src/CLAUDE.md` rule (the only host for a non-command behavior; gated on `in-fix-window`) → 4 emit + docs reconcile (add `fix` to `_PROMOTED`; `src/CLAUDE.md` catalog + workflow annotation; re-point `storage-rules.md` per D4; CHANGELOG; repo-root active-plans entry; install ride) → 5 testForge20 e2e (USER-DRIVEN HARD GATE — WAIVED by maintainer 2026-06-19, NOT executed; `/fix` is build-verified but not runtime-e2e-validated).
- **4 OQs:** OQ-1 (persisted vs live findings; lean persisted), OQ-2 (narrow `_fix/_scope` vs `_shared/feature_scope.py`; lean narrow), OQ-3 (workflow-chain representation in `src/CLAUDE.md`; lean a `[/grill]`-style conditional-loop annotation), OQ-4 (case-3 window-detection mechanism — `fix_helper in-fix-window` verb vs inline rule check; lean a helper verb). Deferrals: a `bugs/` `close-bug` consumer (NOT built — D4 findings-only); the standalone conversational `report-bug` file-arm command (still `_pending`/unbuilt — the file arm writes `bugs/` directly meanwhile, consistent with D4).
- **Verified file:line facts (this session):** `_PROMOTED` lacks `fix` and ends `…, "grill", "summarize")` (`scripts/emitters/claude.py:51`); the three reusable back-half verbs are live binaries in `/implement`'s allowed-tools (`src/commands/implement/main.md:10–13`) and wired at PHASE 5 (`:156–172`), PHASE 6 (`:176–212`), PHASE 7 (`:216–268`); the back-half panel scratch literal (`:185`); `/review` PHASE 4 next-step pointer to `/verify` (`src/commands/review/main.md:308`) + inline-summary render (`:286–293`); `/verify` PHASE 8 next-step (`:290–302`, incl. the `:299` "via `/implement`, re-run `/verify`" line to re-point) + PHASE 9 bug-filing (`:304–337`); the `storage-rules.md` stale-`fix` sites — File Lifecycle (`:159`), Status Lifecycle `In Progress` (`:264`), How-Resolved (`:322–324`), Fix-Notes field-note (`:309`), Related-Issues field-note (`:315`) — and the still-accurate `verify` lifecycle line (`:155`); the launcher shim shape (`src/devforge/lib/verify_helper.py:16–20` per plan 22); the intentional plan-14/15 `/fix` history at repo-root `CLAUDE.md:24,25`; plan 21's deletion of `src/_pending/commands/fix.md` (plan 21 blast-radius A) + its D1/§1/§4/§5 rationale; the standalone conversational file-arm command `src/_pending/commands/report-bug.md` exists but is `_pending`/unbuilt (the case-3/out-of-window file arm writes `bugs/` directly meanwhile); every forge command sets `disable-model-invocation: true` (the model can only PROPOSE `/fix`, the user types it).

## When resuming work

1. **Re-read this plan in full** + `21-DROP-FIX-REFACTOR-PLAN.md`'s `## Why DROP, not rework` (§1–§5) + its D1 — so you understand exactly what is being reversed (D1 only) and what is NOT (the `/refactor` drop, the cold-bug boundary, D2–D6). Then re-read the live files it grounds against: `src/commands/implement/main.md` PHASES 5–7 (the back-half engine `/fix` calls) + its allowed-tools (`:10–13`), `src/commands/verify/main.md` + `src/devforge/lib/_verify/` (the structural model for the `_fix/` subpackage + the `verification.md` NEEDS-WORK producer), `src/commands/review/main.md` PHASE 4 (the `review.md` producer + the proposal hook), `src/devforge/storage-rules.md` (the D4 re-point sites), `src/devforge/lib/_shared/feature_scope.py` (the OQ-2 reuse candidate), `src/_pending/commands/report-bug.md` (the still-unbuilt standalone file-arm command), and `scripts/emitters/claude.py:51` + `src/CLAUDE.md` (the wire-in + the Phase-3b case-3 always-on rule host). The `main.md`/helper line numbers above are pre-edit; re-read each file from scratch after a phase edits it.
2. **All OQs resolved during the Phases 0–4 build** — OQ-1/OQ-2/OQ-4 (the verb) at Phase 1, OQ-3 at Phase 4, OQ-4 (how the rule invokes the verb) at Phase 3b. No blocking OQ remains.
3. **Phases 0–4 are DONE + committed** (`efa16e4`, `154c2c4`, `f91e1b4`, `cd7c688`, `26ae580`): Phase 0 the supersession record; Phase 1 the `_fix/` subpackage (incl. the `in-fix-window` window gate); Phase 2 `main.md` + references; Phase 3 the `/review` + `/verify` command-body offers (cases 1–2); Phase 3b the case-3 conversational offer as a TIGHT always-on `src/CLAUDE.md` rule; Phase 4 the emitter wire-in + docs reconcile (incl. the D4 `storage-rules.md` re-point) + the passing install ride. **Phase 5 (testForge20 e2e) is WAIVED — NOT executed** (maintainer 2026-06-19): the build shipped without the runtime gate. `/fix` is build-verified (unit tests + install ride) but not runtime-e2e-validated; the Phase 5 recipe stands as the validation procedure if/when an opportunistic e2e is run. Do NOT treat Phase 5 as forgotten remaining work — it was deliberately skipped.
4. Route every Python helper change through **python-engineer → python-reviewer** with a test written + run in the same turn (round-trip REAL producer output — a real `review_helper render-report`-rendered `review.md` + a real `verify_helper render-report`-rendered `verification.md` NEEDS-WORK report for `read-findings`, a real `CLAUDE.md` for `preflight`, a real findings working list for `resolve-scope`, real on-disk feature state for `in-fix-window` — not hand-faked fixtures); route every command/spec/reference/CLAUDE.md/plan markdown edit through **instruction-author → instruction-reviewer**; verify command frontmatter (`disable-model-invocation`, `argument-hint`), the cross-helper `allowed-tools` syntax, the four-reviewer Task-dispatch shape, and the emitter/install behavior via the **claude-code-guide** agent BEFORE writing `main.md` (Phase 2), AND verify the consumer-overlay `src/CLAUDE.md` always-on-rule authoring via **claude-code-guide** BEFORE writing the case-3 rule (Phase 3b — `src/CLAUDE.md` ships into the target project). This plan file is a repo-root design doc and does NOT ship into `.claude/`, so it needs no claude-code-guide; `main.md` (Phase 2) + the `src/CLAUDE.md` rule (Phase 3b) DO ship and DO.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(fix): proposal-only gated pipeline-remediation command on the implement back-half`, `feat(fix): read-findings + resolve-scope helper verbs`, `chore(commands): promote fix + re-point storage-rules bug lifecycle to manual`).

## Related plans

- `21-DROP-FIX-REFACTOR-PLAN.md` — the plan this SUPERSEDES (D1 ONLY). Its `## Why DROP, not rework` (§1–§5) is the prior reasoning; `## Why supersede plan 21 D1` here reverses D1 specifically (the shared-engine pattern dissolves §1's duplication tax; §5's accepted cost is what a gated `/fix` restores). Plan 21's `/refactor` drop + D2–D6 stand; plan 21 D1 carries a Phase-0 back-pointer to this plan.
- `22-VERIFY-COMMAND-REDESIGN-PLAN.md` — the STRUCTURAL MODEL for the `_fix/` subpackage (the `_cli.py` verb registry, the `_preflight` setup-chain + source-root resolution, the per-command scratch-chain + helper/orchestrator split, the launcher shim shape `verify_helper.py:16–20`) AND the precedent for reusing `implement_helper verify-touched` from a non-`/implement` command (plan 22 D2 — `/verify` calls it report-only; `/fix` calls it with the self-repair loop). `/verify`'s NEEDS WORK verdict + `verification.md` is one of `/fix`'s two finding sources (PHASE 0), and `/verify` PHASE 8/9 is one of the two proposal hooks (Phase 3).
- `20-REVIEW-COMMAND-REDESIGN-PLAN.md` — produces `specs/[feature]/review.md` (the other `/fix` finding source, PHASE 0) and `/review` PHASE 4 is the other proposal hook (Phase 3); also the `_shared/` extraction precedent (the OQ-2 `_scope` reuse candidate, and the "distinct command surface over a shared engine" pattern the supersession rests on).
- `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` / `07-EXECUTE-TASK-REDESIGN-PLAN.md` — the `/implement` command whose PHASES 5–7 back-half engine (`verify-touched` → the four-reviewer `merge-review-panel` → `run-forcing-functions-gate` → the two-stage hard gate → `wip-commit`) `/fix` reuses byte-for-byte by CALLING the verbs (D3/D6).
- `14-ARCHITECT-NOT-IMPLEMENTER-PLAN.md` — the architect-guard (the architect never codes) that `/fix`'s PHASE-2 agent dispatch honors via the existing file-layer→agent mapping; plan 14's `## Deferrals` chartered the "`/fix` drop-vs-fix decision" that plan 21 resolved (dropped) and this plan now reverses (D1).
- `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` — why the `src/CLAUDE.md` `/fix` catalog entry must be a PURPOSE ONE-LINER and why a workflow annotation is load-bearing (the always-on catalog is the only model-facing command-awareness source, since `/fix` sets `disable-model-invocation: true`); and the always-on-trim discipline that bounds the Phase-3b case-3 conversational rule to a tight block (every line in `src/CLAUDE.md` carries a per-session token cost).
