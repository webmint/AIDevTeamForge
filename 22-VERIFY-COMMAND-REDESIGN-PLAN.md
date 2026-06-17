# 22 — VERIFY COMMAND REDESIGN PLAN

**Status:** **Phases 0–7 SHIPPED in the working tree (uncommitted) 2026-06-17** on `develop-2.0-init`; only **Phase 8 (testForge20 e2e) remains — the user-driven HARD GATE**. As-built: Phase 0 extracted the assembled-feature scope resolver to `_shared/feature_scope.py` (parameterized heading; `/review` re-pointed + byte-identical, its `tests/lib/_review/test_scope.py` the green regression net); Phases 1–5 built the `_verify/` subpackage (13 verbs: `check-status-and-flip`, `preflight`, `resolve-feature-scope`, `read-ac-config`, `parse-acs`, `merge-ac-results`, `check-hygiene`, `read-review-findings`, `compute-verdict`, `render-report`, `render-inline-summary`, `flip-spec-status`, `file-bugs`) + `verify_helper{,.py}` launchers; Phase 3 aligned `ac-verifier.md` to the live `ac_verification_mode`/`ac_runtime_*` keys + the 4-mode mapping; Phase 6 wrote `src/commands/verify/main.md` + `references/report-format.md`; Phase 7 promoted `verify` in the emitter `_PROMOTED`, removed the stale `src/manifest.json` flat-file entry, deleted the stale `src/_pending/commands/verify.md` draft, and reconciled `src/CLAUDE.md` + `CHANGELOG.md` + repo-root `CLAUDE.md` + `DEVELOPMENT-STATUS.md` + `README.md`. **1032 tests green** (`_verify` + `_review` + `_shared` + `tests/scripts`); install-ride clean (`verify command: yes (folder, 1 references)`, 0 `{{` leaks, executable `verify_helper`). Built behind per-phase python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. **Decisions settled during build:** OQ-1 resolved (off-mode AC = advisory/non-blocking; fine-grained tests-mode test→AC mapping DEFERRED — `tests` mode code-reads ACs + runs the suite as one mechanical gate); REJECTED tightened to require ≥2 failing ACs AND ≥50% rate (small specs don't over-escalate); the D7 constitution-violation guard hardened (the `[CONSTITUTION-VIOLATION]` tag is now parsed from the rendered review.md first line so a missing `Category:` line can't slip a violation past the verdict). The per-phase sections below are the original design; the `## Verify` blocks were all met. 9 BUILD phases (0–8); the built `main.md` wires 10 runtime PHASES (PHASE 0–9) — a separate numbering space, see `## The command runtime phases`. Redesigns the stale pre-pivot `/verify` draft (`src/_pending/commands/verify.md`) into a live, emitted, pipeline-wired command at `src/commands/verify/main.md` + `references/` + a `src/devforge/lib/_verify/` helper subpackage + a `verify_helper{,.py}` launcher, structurally modeled on the just-shipped `/review` command (plan 20). It REUSES two already-shipped pieces — the assembled-feature scope resolver (extracted to `_shared/` in Phase 0) and the installed `implement_helper verify-touched` mechanical-check binary — rather than re-implementing them.

## Scope & assumptions

These are decided, not open (except the OQs in `## Open questions`):

1. **`/verify` is the pipeline step AFTER `/review` and BEFORE `/summarize`/`/finalize`** — a fragment of the full Workflow chain in `src/CLAUDE.md` reads `…/implement → /review → /verify → /summarize → /finalize` (verified against the "Spec-Driven Development Flow" code block in `src/CLAUDE.md`, the SSOT for pipeline position — NOT the Command-Details `/verify` entry, which Phase 7 flags as stale). `/verify` is pipeline-wired in that slot; its source today is only an unbuilt draft.
2. **The target is a NEW live command tree** at `src/commands/verify/` (`main.md` + `references/*.md`), a NEW helper subpackage `src/devforge/lib/_verify/`, and a NEW launcher `src/devforge/lib/verify_helper{,.py}`. The stale `src/_pending/commands/verify.md` draft is DELETED (Phase 7), not rewritten — leaving it on disk is a future-hallucination seed (a fresh session could mistake the draft for the SSOT; plans 19/20 made the same call for the `/audit` and `/review` drafts).
3. **Every file path, config key, and identifier in this plan is verified against the live tree this session.** The `main.md` / helper line numbers cited are pre-edit; after a phase edits a file, re-read it from scratch rather than navigating by these numbers.
4. **Build NOW; do NOT gate on `/audit`'s or `/review`'s testForge20 e2e** (the user-driven gates from plans 10/11/12/19/20). Phase 0's regression net is `/review`'s existing `tests/lib/_review/` unit suite — it must stay green after the scope-resolver extraction, which is the safety property that lets this plan proceed without waiting on any upstream manual e2e.
5. **`/review` ships in the working tree (uncommitted) per plan 20** — `src/commands/review/main.md`, `src/devforge/lib/_review/`, and `review_helper{,.py}` all exist this session. `/verify`'s producer (`/review`'s `specs/[feature]/review.md`) is therefore real, not hypothetical — `/verify` consumes a concrete artifact.

## Command mission (what /verify is for)

`/verify` exists to own the ONE job nothing else in the pipeline owns: **the verdict**. `/review` is findings-only (verified: `src/commands/review/main.md:12` — "`/review` produces FINDINGS ONLY — it does NOT render a verdict. The verdict is `/verify`'s job"). `/verify` is where acceptance criteria are proven, the assembled feature is mechanically checked together, `/review`'s findings are folded in, and a single APPROVED / NEEDS WORK / REJECTED verdict is rendered and acted on (spec flipped to Complete on approval; bugs filed on NEEDS WORK).

The seven distinct, unowned jobs `/verify` performs:

1. **Acceptance-criteria verification** — prove each AC item PASS / FAIL / PARTIAL against the spec, via the `ac-verifier` agent (runtime modes) or code-reading (verified: the AC list shape `- [ ] **AC-N**: <EARS sentence>`, `tests/lib/fixtures/specify-sample-migration.md:31`, produced per `src/commands/specify/main.md:526–577`).
2. **Assembled-feature mechanical checks** — type-check / lint / build / test across ALL the feature's tasks together — the cross-task version of `/implement`'s PER-TASK gate (verified: `/implement` PHASE 5 runs `implement_helper verify-touched` per task, `src/commands/implement/main.md:156–164`). Per-task green does NOT guarantee assembled green (a type that two tasks each edited can disagree only when both diffs are present).
3. **Fold in `/review` findings** — read `specs/[feature]/review.md`, incorporate its confirmed + high-stakes `[CONTESTED]` security/perf/test findings into the verdict (the stale draft already does this at `src/_pending/commands/verify.md:24–36`; the producer is now real per plan 20).
4. **Render the VERDICT** — APPROVED / NEEDS WORK / REJECTED. This is `/verify`'s defining job.
5. **Flip spec → Complete + tick AC boxes** — the lifecycle transition `/summarize` and `/finalize` gate on (verified: `/finalize` is "Gate-checked: spec must be Complete (set by `/verify`)", `src/CLAUDE.md` Command-Details `/finalize` entry).
6. **Memory update** — feature-level lessons to `.devforge/memory.md`.
7. **Issue report + batch bug-filing** — when NEEDS WORK, file bugs in the `.devforge/storage-rules.md` format (`Source: verify`).

### The /verify-vs-/review-vs-/audit invariant

`/verify`, `/review`, and `/audit` are three different commands with non-overlapping jobs. This table is the invariant the plan must preserve:

| Axis | `/review` | `/verify` | `/audit` |
|---|---|---|---|
| **Trigger** | in-pipeline, after `/implement` drains a feature | in-pipeline, after `/review` | standalone, manual / periodic |
| **Scope** | one feature's assembled diff (all tasks together) | one feature's assembled diff **+ the spec's AC** | whole project, or any part (file / dir / hotspot) |
| **Output** | `specs/[feature]/review.md` (feeds `/verify`) | `specs/[feature]/verification.md` **+ flips spec `**Status**:`** | `audits/YYYY-MM-DD-audit.md` (terminal report) |
| **Job** | emergent cross-task code-quality findings | AC conformance + mechanical integration + verdict | adversarial whole-codebase quality + system-design |
| **Verdict?** | **NO** — findings only | **YES — owns the verdict** | terminal report, no pipeline verdict |

**The boundary, stated explicitly:** `/verify` does NOT run a finder ensemble or the refutation engine — that is `/review`'s job. `/verify` relies on `/review` for cross-task code-quality / consistency reasoning and adds ONLY three things on top: AC conformance, mechanical assembled checks, and the verdict. A `/verify` that re-runs five finders would duplicate `/review` and contradict plan 20's split. (This is D1.)

## What's stale in the draft (the audit)

The draft `src/_pending/commands/verify.md` predates the 4-command setup-chain pivot, the `/execute-task → /implement` rename, the scope-aware verify binary, and the `/review` build. Each finding below gives the draft's wrong value → the correct current value + the file:line that proves it. (All line numbers are pre-edit.)

**A. Stale paths / keys.**

1. Config keys `AC_VERIFICATION` / `AC_VERIFICATION_URL` / `AC_VERIFICATION_API_BASE` with modes `auto` / `browser-only` / `api-only` (`verify.md:42,56,67`) → the live config keys are `ac_verification_mode` ∈ `{code-only, tests, runtime-assisted, off}`, `ac_runtime_url`, `ac_runtime_api_base`, `ac_runtime_cli_command` (verified: `src/devforge/lib/_configure/_schema.py:62–66` field tuple + `:80` `ENUM_FIELDS["ac_verification_mode"] = {"code-only", "tests", "runtime-assisted", "off"}`; the four modes' `/verify` semantics are authored in `src/commands/configure/references/q12-ac.md:17–20`).
2. Config path `.claude/project-config.json` (`verify.md:42,67`) → `.devforge/project-config.json` (verified: the install-root config path throughout `src/CLAUDE.md`, e.g. the References block).
3. Memory path `.claude/memory/MEMORY.md` (`verify.md:22,200`) → `.devforge/memory.md` (verified: `src/CLAUDE.md` References block + Key Rules #4).
4. Storage template `.claude/templates/storage-rules.md` (`verify.md:281`) → `.devforge/storage-rules.md` (verified: the bug-file format lives at `src/devforge/storage-rules.md:250–310`, "Bug Report Rules", with `**Source**: verify | manual` at `:274`).

**B. Stale command name.** `/execute-task` (`verify.md:106,259`) → `/implement` (verified: the command was renamed per `07-EXECUTE-TASK-REDESIGN-PLAN.md`; `src/commands/implement/main.md` is the live spec). The draft's references to `/refresh-docs`, `/summarize`, `/finalize` (`verify.md:215,217,236`) name real-but-pending commands — fine to keep as forward next-step pointers.

**C. Stale mechanics.**

1. PHASE 4.2 "Run the Type Check / Lint / Build Command from CLAUDE.md" (`verify.md:124–126`) → scope-aware per-package `.devforge/project-config.json` `PACKAGE_STACKS` + `*_COMMANDS[]`, already implemented by `implement_helper verify-touched` (verified: `src/commands/implement/main.md:164` describes the longest-path-prefix package match + `cwd = <source_root>` + fixed static→build→tests order).
2. PHASE 1 / 4.1 "parse CLAUDE.md for Source Root" + the manual cross-task-consistency reasoning section (`verify.md:15,111–119`) → Source Root resolves via the preflight helper reading `PROJECT_ROOT`/Source-Root from `CLAUDE.md` (the same logic `_review/_preflight.py:110–161` uses), and the cross-task-consistency reasoning now OVERLAPS `/review`, which post-dates the draft — `/verify` drops that section and folds in `/review`'s findings instead (D1).

**D. Structural gap.** There is no `_verify/` subpackage, no `verify_helper{,.py}` launcher, and no `tests/lib/_verify/`; `verify` is ABSENT from the emitter `_PROMOTED` tuple (verified: `scripts/emitters/claude.py:51` — the tuple currently ends `…, "audit", "review")` and does NOT contain `verify`, so `/verify` is NOT emitted today).

**E. Broken agent.** `src/agents/ac-verifier.md` itself still references the dead keys — its `## Input` section names `AC_VERIFICATION_URL`, `AC_VERIFICATION_API_BASE`, and "AC_VERIFICATION mode — `auto`, `browser-only`, or `api-only`" (verified: `ac-verifier.md:27–29`), and the body reads them throughout (e.g. `:44,56,119`). The agent reads config keys that no longer exist; Phase 3 fixes it.

**F. Caveat (do NOT copy this bug).** `_review/_preflight.py` carries a STALE `.claude/memory/MEMORY.md` existence check feeding a `memory_present` / `memory_excerpt` field (verified: `_review/_preflight.py:68–69,163–169`). `/verify`'s mirrored preflight MUST read `.devforge/memory.md` and not copy that bug. (The `/review` preflight bug is out of scope to fix here — it is noted so `/verify`'s author does not inherit it; flag it back to the orchestrator.)

## Reuse architecture (confirmed decisions)

**HYBRID reuse (confirmed with the user).** Two already-shipped pieces are reused; one engine is explicitly NOT reused.

**1. Phase 0 extracts the assembled-feature scope resolver into `_shared/`.** The resolver `resolve_feature_scope` + its internal git helpers (`_git`, `_is_git_repo`, `_resolve_head_sha`, `_ref_exists`, `_resolve_origin_head`, `_autodetect_base`, `_compute_merge_base`, `_diff_name_only`, `_prefix_paths`) + the generic scope-block renderer currently live in `src/devforge/lib/_review/_scope.py` (verified: git helpers `_scope.py:51–175`, `_prefix_paths` `:183–224`, `resolve_feature_scope` `:232–372`, `_render_scope_block` `:380–433`). They move to a new flat module `src/devforge/lib/_shared/feature_scope.py` (flat matches the established `_shared/` precedent — `literal_call_shape.py`, `node_bin.py`, `text_overlap.py`, verified via glob). **Parameterize the scope-block heading label** — `_render_scope_block` currently hard-codes the literal `=== Review Scope ===` (verified: `_scope.py:407`) — so `/review` renders "Review Scope" and `/verify` renders "Verification Scope". Re-point `_review/_scope.py`'s `cmd_resolve_feature_scope` to import from `_shared.feature_scope`; `/review`'s `tests/lib/_review/test_scope.py` is the regression net (must stay green; `/review` behaviorally identical). This mirrors plan 20's Phase 0 extraction exactly (plan 20 extracted the refutation engine the same way and kept `/audit` green via `tests/lib/_audit/`).

**2. Reuse the installed `implement_helper verify-touched` binary** for the assembled-feature mechanical checks. Its interface (verified: `src/devforge/lib/_implement/_cmds_verify.py:646–677` `add_args_verify_touched`): `--files <json-array-of-source-relative-paths>`, `--root <install-root>`, `--iteration <N>`. Output JSON `status` ∈ `{pass, self_repair, failed, isolation_failure, tooling_unavailable}` (verified: `_cmds_verify.py:59–66,608,621,632` + `:536,593`). Commands run with `cwd = <source_root>`, reading `PACKAGE_STACKS` from `.devforge/project-config.json` (verified: `_cmds_verify.py:660–666` `--root` doc + `src/commands/implement/main.md:164`). **CRITICAL:** `/verify` calls it with `--iteration 0` and treats the result as a REPORT — it does NOT loop on `self_repair`. The self-repair loop is `/implement`'s job; `/verify` reports failures, never fixes (verified: the draft's own rule 3, `verify.md:310` — "Verification does not fix code"). NO change to `/implement` or to `verify-touched`.

**3. `/verify` does NOT reuse the `_shared` refutation engine** (`findings_schema` / `_consume` / `_validate` / `_consensus` / `_verify`, the engine plan 20 extracted). `/verify` is not a finder ensemble — it has no findings of its own to validate or cross-examine; it folds in `/review`'s already-refuted findings. State this explicitly so a future session does not wire the refutation engine into `/verify` by analogy with `/review`.

## Helper / orchestrator split + module list

The `_verify/` subpackage mirrors `_review/`'s structure: a verb-registry `_SUBCOMMAND_REGISTRY` in `_cli.py` dispatching `(verb, help, handler)` triples (verified: the `_review/_cli.py:798–862` registry pattern), a `main()` argv dispatch (verified: `_review/_cli.py:1304–1317`), atomic writes via `tempfile.mkstemp` + `os.replace` (verified: `_review/_state.py:84–93`, `_review/_report.py:540–548`), and handlers returning int exit codes. The helper owns file structure, validation, and atomic writes; the orchestrator owns agent dispatch, verbatim prompt text, user-facing prose, and phase pacing (the same split `src/commands/review/main.md:58` states — but adapt the vocabulary: `review/main.md:58` says "finder/refuter dispatch" because `/review` runs a finder ensemble + refutation pass; `/verify` has neither, so its `main.md` substitutes the `ac-verifier` Task dispatch for that phrase — do NOT import the finder-ensemble vocabulary into `/verify`'s `main.md`).

Modules:

- `__init__.py` — re-export `main` (mirrors `_review`).
- `_cli.py` — verb registry + argparse dispatch.
- `_preflight.py` — setup-chain gate + populated-constitution sentinel + `source_root` / `wrapper_mode` / `framework` / `language` extraction. **Reads `.devforge/memory.md`** (NOT `.claude/memory/MEMORY.md` — do not copy the `_review/_preflight.py` bug, finding F).
- `_state.py` — `VerifyState` at `specs/[feature]/verify-state.json`, mirroring `_review/_state.py`'s `ReviewState` (per-feature scoped state, atomic write, `flip_phase`).
- `_ac.py` — parse the spec's `## Acceptance Criteria` section → AC list; merge `ac-verifier` results back into the AC checklist.
- `_hygiene.py` — the `check-hygiene` verb: flag changed files outside the spec's scope boundaries + leftover debug/TODO/commented-out artifacts across the assembled diff (single-responsibility module, not folded into `_ac.py`).
- `_review_findings.py` — parse `specs/[feature]/review.md` → folded-findings summary for the verdict.
- `_verdict.py` — deterministic verdict computation (APPROVED / NEEDS WORK / REJECTED) from the AC results + mechanical-check result + folded findings.
- `_report.py` — render `specs/[feature]/verification.md` + the inline summary; atomic write (mirrors `_review/_report.py`).
- `_bugs.py` — file bugs in the `.devforge/storage-rules.md` format (`Source: verify`).
- `_specstatus.py` — task-completion cross-check + flip spec `**Status**:` → Complete + tick AC `- [ ]` → `- [x]`.

Verbs (kebab-case):

- `check-status-and-flip` — per-feature run state (mirrors `_review`).
- `preflight` — setup-chain + constitution gate + context.
- `resolve-feature-scope` — wraps `_shared.feature_scope` (the extracted resolver).
- `read-ac-config` — read `ac_verification_mode` / `ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command` from `.devforge/project-config.json`.
- `parse-acs` — parse the spec's AC checkboxes into a structured AC list.
- `merge-ac-results` — merge `ac-verifier` agent output into the AC checklist.
- `check-hygiene` — flag changed files outside the spec's scope boundaries + leftover debug/TODO/commented-out artifacts across the assembled diff (re-points the draft's PHASE 4.2 hygiene checks, `verify.md:127–128`, to the assembled-diff file list).
- `read-review-findings` — parse `specs/[feature]/review.md` into folded findings.
- `compute-verdict` — deterministic verdict.
- `render-report` — write `specs/[feature]/verification.md`.
- `render-inline-summary` — count-first console block.
- `flip-spec-status` — task cross-check + flip spec Status + tick AC boxes.
- `file-bugs` — write `bugs/NNN-*.md` files.

Launchers `verify_helper` (POSIX shell) + `verify_helper.py` (python shim) mirror `review_helper{,.py}` verbatim in shape (verified: `src/devforge/lib/review_helper.py:14–18` — `_LIB_DIR` `sys.path` insert + `from _review._cli import main`); `verify_helper.py` imports `from _verify._cli import main`. **Scratch dir literal `${TMPDIR:-/tmp}/forge-verify`** — NOT `forge-review` or `forge-audit` (collision avoidance; `/audit`, `/review`, and `/verify` may not run concurrently in the same workdir, the exact reason `/review` chose `forge-review`, verified: `src/commands/review/main.md:96`).

## The command runtime phases (described inside main.md)

`main.md` wires a 10-phase runtime flow. (These PHASE 0–9 numbers are runtime-internal — distinct from the build-phase numbering in `## Phases`; the `## Phases` section's Phase 6 BUILDS this `main.md` with all ten runtime PHASES inside it.) PHASE numbering follows the draft's spine (re-pointed to the live mechanics) and `/review`'s scratch-chain pattern (`WORKDIR="${TMPDIR:-/tmp}/forge-verify"` re-established at the top of every Bash block, verified pattern: `src/commands/review/main.md:92,98`):

- **PHASE 0** — preflight + feature resolution + state + scratch (`$WORKDIR=forge-verify`).
- **PHASE 1** — resolve the assembled-feature scope (`merge-base..HEAD` union via the `_shared` resolver; empty-diff stop, mirroring `src/commands/review/main.md:122`).
- **PHASE 2** — read `specs/[feature]/review.md` findings (warn if missing, proceed weakened — mirrors the draft's PHASE 2 graceful path at `verify.md:32–36`).
- **PHASE 3** — AC verification (mode-dispatch per the mapping in D5; parse the spec's ACs; merge results; report failures, never fix).
- **PHASE 4** — assembled mechanical checks (reuse `implement_helper verify-touched --iteration 0` as a REPORT; scope-creep + leftover-artifact hygiene notes).
- **PHASE 5** — compute the verdict + write `specs/[feature]/verification.md` + inline summary.
- **PHASE 6** — spec-status flip (if APPROVED: task cross-check all tasks `**Status**: Complete` / `Skipped` → flip spec `**Status**:` → Complete + tick passed AC boxes; else keep status unchanged).
- **PHASE 7** — memory update (`.devforge/memory.md`).
- **PHASE 8** — present + next-step (APPROVED → `/summarize` then `/finalize`; NEEDS WORK → PHASE 9; REJECTED → revise the spec via `/specify` → `/plan` → `/breakdown`).
- **PHASE 9** — issue report + batch bug-filing (NEEDS WORK only; `file-bugs` writes `bugs/NNN-*.md`).

### AC-mode mapping (this is D5 — the agent fix defines it)

The four `ac_verification_mode` values (verified: `_configure/_schema.py:80`; semantics authored at `configure/references/q12-ac.md:17–20`) map to `/verify` PHASE-3 behavior:

- **`runtime-assisted`** → dispatch the `ac-verifier` agent with Chrome MCP (`ac_runtime_url`) + API (`ac_runtime_api_base`) + CLI (`ac_runtime_cli_command`); probe MCP availability first (a lightweight `mcp__chrome-devtools__list_pages` call, as the draft does at `verify.md:51`); code-fallback for items that are unobservable at runtime.
- **`tests`** → run the assembled-feature test command (via the PHASE-4 `verify-touched` result, whose test leg is scope-aware) and map results to AC items that reference tests; code-read the rest.
- **`code-only`** → code-reading mode — judge each AC by reading the changed files; record `PASS (code)` / `FAIL (code)` / `PARTIAL (code)` (the `(code)` suffix is already the agent's contract, verified: `ac-verifier.md:61,71`).
- **`off`** → skip behavioral AC verification; apply a code-reading floor; the verdict explicitly notes AC were verified by code only. (The exact `off` / `tests` verdict-interaction is OQ-1.)

## Spec / task status facts (for the flip)

- **Spec status** is a markdown bold line `**Status**: <value>`, value ∈ `{Draft, Approved, In Progress, Complete}` (verified: `src/devforge/lib/_specify/_schema.py:32–34` `SPEC_STATUS_ENUM`; rendered shape `**Status**: Draft` at `tests/lib/fixtures/specify-sample-migration.md:4`).
- **Task status** is the same `**Status**:` line, the satisfied set ∈ `{Complete, Skipped}` (verified: `src/devforge/lib/_implement/_cmds_resolve.py:41` `COMPLETE_STATUSES = frozenset(["Complete", "Skipped"])` + the `_STATUS_PATTERN` regex at `:44`); incomplete = any other value (`Pending`, `In Progress`, or absent).
- **Spec ACs** are checkboxes `- [ ] **AC-N**: <EARS sentence>` (verified: `tests/lib/fixtures/specify-sample-migration.md:31`, authored per `src/commands/specify/main.md:526–577`).
- `flip-spec-status` cross-checks all task files are `Complete` / `Skipped` (excluding `README.md`) BEFORE flipping the spec to Complete and ticking `- [ ]` → `- [x]` for the ACs that passed verification. (The draft's PHASE 6 already gates the flip on the task cross-check at `verify.md:188`; this re-points it to the live status vocabulary.)

## Phases (build order)

Each phase: objective, files touched, helper verbs/modules introduced, an execution agent-loop note, a `#### Verify` fenced bash block, and a `DoD:` line. Per repo discipline (CLAUDE.md): every `.py` helper change goes through **python-engineer → python-reviewer** with a test written + actually run in the SAME turn (test-immediately-after-write; parsers round-trip REAL producer output, not hand-faked fixtures); every command/spec/reference/CLAUDE.md/plan markdown edit goes through **instruction-author → instruction-reviewer** (route-spec-edits-through-agent-flow); for any Claude-Code-integration concern — the `ac-verifier` Task dispatch shape, `subagent_type` usage, command frontmatter (`disable-model-invocation`, `argument-hint`), the emitter/install behavior — verify current conventions via the **claude-code-guide** agent BEFORE writing the spec (confidence is not verification). Each phase leaves the system buildable and tests green.

### Phase 0 — Shared scope extraction

**Objective:** lift the assembled-feature scope resolver into `_shared/feature_scope.py` so `/review` and `/verify` share one copy; parameterize the scope-block heading label; re-point `/review`; keep `/review` byte-behaviorally identical.

- **Files touched:** new `src/devforge/lib/_shared/feature_scope.py` holding the moved `resolve_feature_scope` + git helpers + `_prefix_paths` + a heading-label-parameterized `_render_scope_block`. Edit `src/devforge/lib/_review/_scope.py` to import the resolver from `_shared.feature_scope` (keep `cmd_resolve_feature_scope` as the thin `/review` CLI handler, passing the "Review Scope" label). Move the resolver's own tests into `tests/lib/_shared/test_feature_scope.py`; `tests/lib/_review/test_scope.py` stays as the `/review`-side regression net.
- **Modules/verbs introduced:** none new — this is a relocation + one signature widening (a `heading_label` parameter on `_render_scope_block` defaulting to the existing `"Review Scope"` so `/review` is unchanged when the default is used).
- **Execution:** python-engineer → python-reviewer; the moved tests + the re-pointed `tests/lib/_review/` suite run green in the same turn.

#### Verify

```bash
# The resolver now lives under _shared:
ls src/devforge/lib/_shared/feature_scope.py   # expect: present
grep -n "def resolve_feature_scope" src/devforge/lib/_shared/feature_scope.py   # expect: defined here
# heading label parameterized:
grep -n "heading_label\|Review Scope\|Verification Scope" src/devforge/lib/_shared/feature_scope.py   # expect: a heading_label param, default "Review Scope"
# _review re-points to _shared (no orphaned local resolver):
grep -n "from _shared.feature_scope\|from .._shared" src/devforge/lib/_review/_scope.py   # expect: import resolves to _shared
# Regression net green — /review behaviorally unchanged:
python -m pytest tests/lib/_review/test_scope.py   # expect: green
python -m pytest tests/lib/_shared/test_feature_scope.py   # expect: green (moved tests)
```

DoD: `resolve_feature_scope` + its git helpers live in `_shared/feature_scope.py`; `_render_scope_block` takes a `heading_label` defaulting to `"Review Scope"`; `_review/_scope.py` imports from `_shared` and passes `"Review Scope"`; the moved tests + `tests/lib/_review/test_scope.py` are green with `/review` byte-behaviorally unchanged; python-reviewer loop applied.

### Phase 1 — `_verify/` scaffold + preflight + state

**Objective:** create the `_verify/` subpackage, the launchers, the verb registry, run-state, and the preflight gate.

- **Files touched:** new `src/devforge/lib/_verify/` subpackage (`__init__.py`, `_cli.py` with `_SUBCOMMAND_REGISTRY` mirroring `_review/_cli.py:798`); new launchers `src/devforge/lib/verify_helper` (POSIX shell) + `src/devforge/lib/verify_helper.py` (the `.py` shim mirrors `review_helper.py:14–18` verbatim in shape — `_LIB_DIR` `sys.path` insert + `from _verify._cli import main`); new `src/devforge/lib/_verify/_state.py` (`VerifyState` at `specs/[feature]/verify-state.json`, mirroring `_review/_state.py`'s per-feature scope + atomic write + `flip_phase`); new `src/devforge/lib/_verify/_preflight.py`.
- **Modules/verbs introduced:** `check-status-and-flip` (run-state) + a `preflight` verb that gates on (a) the 4-command setup chain `/init-forge → /generate-docs → /configure → /constitute` (mirroring `_review/_preflight.py:39–45` `_SETUP_CHAIN_ARTEFACTS`), (b) the constitution-populated guard — STOP if `constitution.md` is absent or still carries an unpopulated sentinel (the same `_UNPOPULATED_SENTINELS` set `/review` uses, `_review/_preflight.py:31–35`), and (c) Source-Root / wrapper-mode / framework / language resolution from `CLAUDE.md` (the same extraction `_review/_preflight.py:110–161` does). **The preflight reads `.devforge/memory.md`, NOT `.claude/memory/MEMORY.md`** (finding F — do not copy `/review`'s stale memory path).
- **Execution:** python-engineer → python-reviewer; tests round-trip a real `CLAUDE.md` + `constitution.md` fixture (populated and unpopulated) in the same turn.

#### Verify

```bash
ls src/devforge/lib/_verify/ src/devforge/lib/verify_helper src/devforge/lib/verify_helper.py   # expect: present
grep -n "_SUBCOMMAND_REGISTRY" src/devforge/lib/_verify/_cli.py   # expect: registry present, mirroring _review
grep -n "from _verify._cli import main" src/devforge/lib/verify_helper.py   # expect: the shim imports _verify
grep -n "\.devforge/memory.md" src/devforge/lib/_verify/_preflight.py   # expect: reads .devforge/memory.md
grep -n "MEMORY.md\|.claude/memory" src/devforge/lib/_verify/_preflight.py   # expect: NO match (finding F not copied)
python -m pytest tests/lib/_verify/test_preflight.py tests/lib/_verify/test_state.py   # expect: green
```

DoD: `_verify/` subpackage + `verify_helper{,.py}` launchers + `_state.py` (`VerifyState`) + `_preflight.py` exist; the `preflight` verb gates the setup chain + the populated-constitution sentinel + resolves Source-Root/wrapper-mode and reads `.devforge/memory.md`; helper tests written + run + green; python-reviewer loop applied.

### Phase 2 — Input verbs

**Objective:** the read-side verbs that ingest the spec ACs, the AC config, the assembled scope, and `/review`'s findings — parsers round-tripping REAL producer output.

- **Files touched:** new `src/devforge/lib/_verify/_ac.py` (the spec-AC parser), `src/devforge/lib/_verify/_review_findings.py` (the `review.md` parser), and the `resolve-feature-scope` + `read-ac-config` wiring in `_cli.py`.
- **Modules/verbs introduced:** `resolve-feature-scope` (wraps `_shared.feature_scope` — same JSON contract `/review` emits: `files`, `files_for_finders`, `file_count`, `scope_block`, verified `_review/_scope.py:275–289`); `read-ac-config` (reads the four `ac_*` keys from `.devforge/project-config.json`); `parse-acs` (parses `- [ ] **AC-N**: …` checkboxes from the spec's AC section into a structured list); `read-review-findings` (parses `specs/[feature]/review.md` into folded findings).
- **Execution:** python-engineer → python-reviewer; parsers round-trip REAL producer output — `parse-acs` against a real `spec.md` AC section (use `tests/lib/fixtures/specify-sample-migration.md` or a `specify_helper`-rendered spec), and `read-review-findings` against a real `review.md` rendered by `review_helper render-report` (NOT a hand-authored fixture — per the test-immediately-after-write discipline for parsers reading another tool's output).

#### Verify

```bash
grep -n "resolve-feature-scope\|read-ac-config\|parse-acs\|read-review-findings" src/devforge/lib/_verify/_cli.py   # expect: all registered
# parse-acs round-trips a real spec AC section:
.devforge/lib/verify_helper parse-acs --spec tests/lib/fixtures/specify-sample-migration.md   # expect: AC-1..AC-7 structured list
# read-review-findings round-trips a review.md produced by review_helper:
python -m pytest tests/lib/_verify/test_ac.py tests/lib/_verify/test_review_findings.py   # expect: green (round-trip via the real producers)
```

DoD: `resolve-feature-scope` (wrapping `_shared`), `read-ac-config`, `parse-acs`, and `read-review-findings` are registered and tested; the spec-AC parser round-trips a real `spec.md` AC section and the review-findings parser round-trips a real `review_helper`-rendered `review.md`; python-reviewer loop applied.

### Phase 3 — ac-verifier agent fix + mode mapping

**Objective:** align the `ac-verifier` agent's Input contract to the live config keys and define the four-mode behavior mapping — so the agent reads keys that exist.

- **Files touched:** `src/agents/ac-verifier.md` — rewrite the `## Input` section (`:24–30`) to the live keys (`ac_runtime_url`, `ac_runtime_api_base`, `ac_runtime_cli_command`, `ac_verification_mode` ∈ `{code-only, tests, runtime-assisted, off}`) and define the 4-mode behavior mapping (D5). Update the body references that name the dead keys (`:44,56,119` — `AC_VERIFICATION_URL`/`AC_VERIFICATION_API_BASE`/`browser-only`/`api-only`) to the live vocabulary.
- **Modules/verbs introduced:** none — this is an agent-markdown edit only.
- **Execution:** instruction-author → instruction-reviewer; claude-code-guide consulted FIRST for current agent-frontmatter conventions (the `tools:` allowlist + `model_tier` fields are load-bearing and Claude-Code-integration surface). **Scope: ONLY the Input contract + the mode mapping + the dead-key body references** — do NOT reshape the plan-15 canonical agent skeleton (Identity → Core Expertise → Project Paths → Approach → Output → Boundaries & Handoffs → Rules); plan 15 owns the roster skeleton.

#### Verify

```bash
# Dead keys gone, live keys present:
grep -n "AC_VERIFICATION_URL\|AC_VERIFICATION_API_BASE\|browser-only\|api-only" src/agents/ac-verifier.md   # expect: NO match
grep -n "ac_runtime_url\|ac_runtime_api_base\|ac_runtime_cli_command\|ac_verification_mode" src/agents/ac-verifier.md   # expect: present in ## Input
grep -n "code-only\|tests\|runtime-assisted\|off" src/agents/ac-verifier.md   # expect: the four modes named with behavior
# Skeleton untouched (plan-15 headings still present, unchanged count):
grep -n "^## Core Expertise\|^## Approach\|^## Output\|^## Boundaries & Handoffs\|^## Rules" src/agents/ac-verifier.md   # expect: all present
python -m pytest tests/scripts/test_generate_agents.py   # expect: green (agent still emits)
```

DoD: `ac-verifier.md`'s `## Input` section names only live config keys; the four `ac_verification_mode` values have an explicit behavior mapping; the body's dead-key references are updated; the plan-15 skeleton headings are intact; `test_generate_agents` green; instruction-reviewer + claude-code-guide loops applied.

### Phase 4 — Checks + merge

**Objective:** wire the assembled mechanical-check reuse, the AC-result merge (`merge-ac-results`), and the scope-creep/hygiene check (`check-hygiene`).

- **Files touched:** `src/devforge/lib/_verify/_ac.py` (the `merge-ac-results` half) + new `src/devforge/lib/_verify/_hygiene.py` (the `check-hygiene` helper); the `merge-ac-results` + `check-hygiene` registrations in `_cli.py`. (The mechanical check itself is the orchestrator invoking `implement_helper verify-touched` — no `_verify` code wraps it; `main.md` PHASE 4 captures its JSON and treats `status` as a report. The `--files` value is the `files_for_finders` array from PHASE 1's `resolve-feature-scope`.)
- **Modules/verbs introduced:** `merge-ac-results` (merge the `ac-verifier` agent's per-AC PASS/FAIL/PARTIAL output back into the structured AC list from `parse-acs`); `check-hygiene` (flag changed files outside the spec's scope boundaries + leftover debug/TODO/commented-out artifacts across the assembled diff — the draft's PHASE 4.2 hygiene checks, `verify.md:127–128`, re-pointed to the assembled-diff file list).
- **Execution:** python-engineer → python-reviewer; `merge-ac-results` round-trips a real `ac-verifier`-shaped report (the agent's `### Results` table contract, `ac-verifier.md:88–94`) merged against a real `parse-acs` output.

#### Verify

```bash
grep -n "merge-ac-results\|check-hygiene" src/devforge/lib/_verify/_cli.py   # expect: both registered
# main.md treats verify-touched as a report (no self_repair loop):
grep -n "verify-touched\|--iteration 0\|self_repair" src/commands/verify/main.md   # (after Phase 6) expect: --iteration 0, reported never looped
python -m pytest tests/lib/_verify/test_ac.py   # expect: green incl. merge-ac-results round-trip
```

DoD: `merge-ac-results` merges real `ac-verifier` output into the structured AC list; `check-hygiene` (in `_hygiene.py`) flags out-of-scope files + leftover artifacts across the assembled diff; `main.md` (built in Phase 6) invokes `verify-touched --iteration 0` as a report and never loops on `self_repair`; python-reviewer loop applied.

### Phase 5 — Verdict + report + bugs + status-flip

**Objective:** the verdict computation, the `verification.md` render, the inline summary, the spec-status flip, and bug-filing.

- **Files touched:** new `src/devforge/lib/_verify/_verdict.py`, `src/devforge/lib/_verify/_report.py`, `src/devforge/lib/_verify/_specstatus.py`, `src/devforge/lib/_verify/_bugs.py`; the verb registrations in `_cli.py`.
- **Modules/verbs introduced:** `compute-verdict` (deterministic APPROVED / NEEDS WORK / REJECTED from the AC results + the `verify-touched` status + the folded `/review` findings — **constitution violations are always Critical and block APPROVED**, D7); `render-report` (write `specs/[feature]/verification.md`, atomic write mirroring `_review/_report.py:527–556`); `render-inline-summary` (count-first console block, per the audit-format discipline); `flip-spec-status` (task cross-check all tasks `Complete`/`Skipped` → flip spec `**Status**:` → Complete + tick passed AC `- [ ]` → `- [x]`); `file-bugs` (write `bugs/NNN-*.md` in the `.devforge/storage-rules.md` format with `Source: verify`).
- **Execution:** python-engineer → python-reviewer; `_report` round-trips a real verdict + AC-results + folded-findings dict; `flip-spec-status` round-trips a REAL `spec.md` + a real `tasks/` fixture (assert it refuses to flip when a task is not `Complete`/`Skipped`, and ticks only passed ACs); `compute-verdict` asserts a constitution violation always yields a non-APPROVED verdict.

#### Verify

```bash
grep -n "compute-verdict\|render-report\|render-inline-summary\|flip-spec-status\|file-bugs" src/devforge/lib/_verify/_cli.py   # expect: all registered
# render-report writes verification.md:
.devforge/lib/verify_helper render-report --verdict <fixture> --feature specs/001-... --date 2026-06-16   # expect: specs/001-.../verification.md written
# flip-spec-status refuses on incomplete task, ticks passed ACs:
python -m pytest tests/lib/_verify/test_specstatus.py tests/lib/_verify/test_verdict.py tests/lib/_verify/test_report.py tests/lib/_verify/test_bugs.py   # expect: green (constitution-violation → never APPROVED; flip gated on task cross-check; bug format = storage-rules)
```

DoD: `compute-verdict` (constitution violation → never APPROVED), `render-report` (atomic `verification.md`), `render-inline-summary`, `flip-spec-status` (gated on the task cross-check; ticks only passed ACs), and `file-bugs` (`Source: verify`, sequential `NNN`) are all built + tested with real-producer round-trips; python-reviewer loop applied.

### Phase 6 — main.md + references

**Objective:** write the live command spec wiring the 10 runtime phases + the references.

- **Files touched:** new `src/commands/verify/main.md` (frontmatter `name: verify`, `description`, `argument-hint: "[spec-file]"`, `disable-model-invocation: true` — mirroring `src/commands/review/main.md:1–6`); new `src/commands/verify/references/report-format.md` (the `verification.md` skeleton + the verdict-line contract, modeled on `src/commands/review/references/report-format.md`). The `main.md` wires the `$WORKDIR=forge-verify` scratch-chain, the `ac-verifier` Task dispatch (mode-dispatch per D5), the `verify-touched --iteration 0` report call, and the verdict/flip/bug-filing phases.
- **Modules/verbs introduced:** none — this is the orchestrator spec composing the Phase-1..5 verbs.
- **Execution:** instruction-author → instruction-reviewer; claude-code-guide consulted FIRST for command frontmatter (`disable-model-invocation`, `argument-hint`) AND the `ac-verifier` Task-dispatch shape (`subagent_type` usage, how to thread the MCP-availability probe + the `ac_runtime_*` values into the agent prompt).

#### Verify

```bash
ls src/commands/verify/main.md src/commands/verify/references/report-format.md   # expect: present
grep -n "disable-model-invocation: true\|argument-hint" src/commands/verify/main.md   # expect: frontmatter present
grep -n "forge-verify\|WORKDIR" src/commands/verify/main.md   # expect: the $WORKDIR scratch-chain (forge-verify, NOT forge-review)
grep -n "ac-verifier\|verify-touched\|--iteration 0" src/commands/verify/main.md   # expect: AC dispatch + report-only mechanical check
grep -n "APPROVED\|NEEDS WORK\|REJECTED" src/commands/verify/main.md   # expect: the verdict vocabulary
```

DoD: `src/commands/verify/main.md` wires the 10 runtime phases (preflight → scope → review-findings → AC → mechanical → verdict+report → spec-flip → memory → present → bug-filing) with `forge-verify` scratch, the D5 AC mode-dispatch, the report-only `verify-touched` call, and the verdict/flip/bugs flow; `references/report-format.md` documents the `verification.md` skeleton + verdict line; instruction-reviewer + claude-code-guide loops applied.

### Phase 7 — Wire-in

**Objective:** make `/verify` emit + install, delete the stale draft, and reconcile every `/verify` reference.

- **Add `"verify"` to the emitter `_PROMOTED` tuple** — `scripts/emitters/claude.py:51` (verified: the tuple currently ends `…, "audit", "review")` and does NOT contain `verify`). Append `"verify"`.
- **DELETE the stale `src/_pending/commands/verify.md`** (the pre-pivot draft superseded by the live command). Sweep for any live consumer of that path first.
- **Reconcile `src/CLAUDE.md`:** the `/verify` Command-Details entry already exists (verified: `src/CLAUDE.md` `#### /verify [spec-file]`) and names the stale `AC_VERIFICATION` key + `project-config.json` path — update the body to describe the redesigned command (AC verification via the four `ac_verification_mode` modes, assembled mechanical checks, folds `/review` findings, owns the verdict, flips spec to Complete) while keeping it a PURPOSE ONE-LINER per the plan-08 trim discipline (mechanics live in `main.md`); pipeline position unchanged.
- **Cross-ref sweep of every `/verify` reference** (verified inventory this session, to confirm each still aligns after the redesign):
  - `src/CLAUDE.md` — Workflow chain line + the `/verify` Command-Details entry (reconcile, above).
  - `src/commands/configure/references/q12-ac.md:7,17–20` — the AskUserQuestion that sets `ac_verification_mode` and describes each mode's `/verify` behavior (confirm the redesigned `/verify` honors exactly these four mode semantics — it does, per D5; no change expected, but the alignment must be verified).
  - `src/commands/specify/main.md:575` — "Downstream `/verify` reads + runs the `test_anchor`" (confirm the redesigned `/verify` honors `test_anchor` in `tests` mode; if Phase 3 does not yet wire `test_anchor`, record it as a known gap, do NOT silently leave the claim dangling).
  - `src/commands/implement/main.md:44,91` + `src/commands/plan/main.md:24,109` + `src/commands/breakdown/main.md:23` — the workflow-chain comment lines + `plan/main.md:109`'s "post-`/verify` Complete state" reference (confirm still accurate — `/verify` is what sets Complete; no change expected).
  - `src/commands/audit/main.md:289` — the CHANGELOG cross-reference to `/verify`'s batched-dispatch context-exhaustion note (confirm still accurate; no change).
  - `src/manifest.json` — **Remove the stale `{ "source": "src/commands/verify.md", "target": ".claude/commands/verify.md" }` entry from `src/manifest.json:15`** — the flat-file layout is superseded by the folder layout, which `_PROMOTED` + the emitter handle (the manifest's `templateOwned.files` covers flat-file-only commands per `update.sh:884`). Leaving it would break `update.sh` on existing installs (it syncs each manifest `source` path, and `src/commands/verify.md` no longer exists). **Note (separate, out-of-scope for plan 22):** `src/manifest.json:21` carries the equivalent stale `{ "source": "src/commands/review.md", "target": ".claude/commands/review.md" }` flat-file entry — a PRE-EXISTING bug inherited from plan 20's wire-in (`/review` is folder-layout now too). Flag it back to the orchestrator as a separate `/review`-side fix; do NOT fix it here, but record it so it is not lost.
  - `src/_pending/commands/summarize.md` + `src/_pending/commands/finalize.md` — these pending drafts reference `/verify`'s Complete-flip as their gate (confirm they read `**Status**: Complete` — the contract `flip-spec-status` writes; no change here now, the structured handoff is OQ-2).
- **Install-ride verification** (mirror how plans 10/11/20 describe their install-ride checks): run `install.sh <tmp-target>` and confirm `verify command: yes (folder, N references)` (N = the reference-file count from Phase 6, auto-globbed by the emitter), **0 `{{` placeholder leaks** in the emitted command, and an **executable `verify_helper`** installed at `.devforge/lib/verify_helper`.
- **Execution:** the `_PROMOTED` edit is a one-line Python tuple change (python-engineer → python-reviewer — confirm the emit still passes `tests/scripts/`); the deletion + all markdown reconciliation via instruction-author → instruction-reviewer; claude-code-guide consulted for the emitter/install behavior. Add a `CHANGELOG.md` entry + the repo-root `CLAUDE.md` active-plans entry for plan 22.

#### Verify

```bash
# verify promoted in the emitter:
grep -n "verify" scripts/emitters/claude.py   # expect: "verify" in _PROMOTED
# stale flat-file manifest entry removed (folder layout is _PROMOTED-handled):
grep -n "src/commands/verify.md" src/manifest.json   # expect: NO match (entry removed; would break update.sh otherwise)
# stale draft deleted, no live consumer:
ls src/_pending/commands/verify.md 2>/dev/null   # expect: absent
grep -rn "_pending/commands/verify" src/ scripts/ install.sh   # expect: no live consumer
# every /verify reference still aligns (no dangling), excluding helper/internal hits:
grep -rn "/verify\|verification\.md" src/ | grep -v "ac-verifier\|verify-touched\|verify_helper\|_verify/"   # read: only the inventoried, still-accurate references
# install ride:
#   install.sh <tmp> reports: verify command: yes (folder, N references); 0 '{{' leaks; .devforge/lib/verify_helper executable
python -m pytest tests/scripts/   # expect: green (emit still works with verify added)
```

DoD: `verify` is in `_PROMOTED` (so it emits/installs); the stale `src/commands/verify.md` flat-file entry is removed from `src/manifest.json:15` (so `update.sh` does not sync a non-existent source); the stale `src/_pending/commands/verify.md` is deleted with no live consumer; the `src/CLAUDE.md` entry + Workflow chain reconcile to the redesigned command (pipeline position unchanged); the cross-ref sweep is clean (every inventoried `/verify` reference still accurate, `q12-ac.md` modes honored, `test_anchor` handled or flagged); the install ride shows `verify command: yes` with N references, 0 `{{` leaks, and an executable helper; `CHANGELOG.md` + repo-root `CLAUDE.md` updated; author→reviewer + python→reviewer + claude-code-guide loops applied.

### Phase 8 — testForge20 e2e (USER-DRIVEN — HARD GATE)

**Objective:** the repo's standard manual e2e gate — confirm `/verify` works end to end on a real feature that finished `/implement` + `/review`.

- Re-install the forge into testForge20 (so the new `/verify` source is emitted) and run `/verify` over a feature whose tasks were drained by `/implement` and reviewed by `/review`.
- **Success looks like:** the AC verdict is rendered per the project's `ac_verification_mode`; `specs/[feature]/verification.md` is written; on APPROVED the spec `**Status**:` flips to Complete and the passed AC boxes tick `- [x]`; `/review`'s `specs/[feature]/review.md` findings are folded into the verdict (and the run warns if `review.md` is missing); on NEEDS WORK the batch bug-filing writes `bugs/NNN-*.md` in the storage-rules format; the assembled mechanical check (`verify-touched --iteration 0`) is reported and NOT self-repaired.
- Confirm the install ride (can be checked now): `verify command: yes (folder, N references)`, 0 `{{` leaks, executable helper.
- Mark DONE only after user sign-off.

#### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# Observe during the /verify run:
#   - preflight gates the setup chain + populated constitution; reports Source Root.
#   - resolve-feature-scope computes the assembled merge-base..HEAD diff.
#   - AC verification runs per ac_verification_mode (ac-verifier dispatch in runtime-assisted; code-read in code-only/off).
#   - verify-touched --iteration 0 runs the assembled type/lint/build/test ONCE, reported (no self_repair loop).
#   - review.md findings are folded into the verdict (warns if missing).
#   - verification.md is written; the verdict is APPROVED / NEEDS WORK / REJECTED.
#   - On APPROVED: spec **Status**: → Complete + passed AC boxes ticked (after the task cross-check).
#   - On NEEDS WORK: bugs/NNN-*.md filed (Source: verify).
```

DoD: e2e confirms `/verify` over a real `/implement`+`/review`-drained feature renders the AC verdict, writes `verification.md`, flips the spec to Complete on APPROVED (with passed AC boxes ticked after the task cross-check), folds `/review` findings, and files bugs on NEEDS WORK; user-driven sign-off.

## Decisions (settled — flip any during review)

### D1 — `/verify` stays NARROW: AC + assembled mechanical + fold /review + verdict + flip

`/verify` does AC conformance, assembled mechanical checks, folding `/review`'s findings, the verdict, and the spec-status flip. It DROPS the draft's LLM cross-task-consistency reasoning section (`verify.md:111–119`) — `/review` owns cross-task code-quality / consistency reasoning now (it post-dates the draft). NO finder ensemble, NO refutation reuse in `/verify`. (User-confirmed.)

### D2 — HYBRID reuse: extract the scope resolver + reuse verify-touched

Phase 0 extracts `resolve_feature_scope` to `_shared/feature_scope.py` (re-point `/review`; `tests/lib/_review/test_scope.py` is the net), and `/verify` reuses the installed `implement_helper verify-touched` binary for the assembled mechanical checks — report-only, `--iteration 0`, NO self-repair loop. No `/implement` change, no `verify-touched` change. (User-confirmed.)

### D3 — Fix `ac-verifier.md` in this plan

The agent's `## Input` contract is aligned to the live config keys (`ac_runtime_*` / `ac_verification_mode`) and the four-mode mapping is defined (D5). Scope of the agent edit is the Input contract + mode mapping + dead-key body references ONLY — the plan-15 skeleton is not reshaped. (User-confirmed.)

### D4 — Output artifact: write `verification.md` AND flip the spec

`/verify` writes `specs/[feature]/verification.md` (consistency with `review.md` / `audit.md` artifact naming) AND flips the spec `**Status**:` → Complete + ticks AC boxes. **DELIBERATE DEPARTURE** (flag per design-consistency-over-invention): `/verify` is the ONLY review/verify command that WRITES BACK to its input (the spec). Justified because `/verify` owns the spec Complete lifecycle transition that `/summarize` + `/finalize` gate on (verified: `/finalize` is "Gate-checked: spec must be Complete (set by `/verify`)", `src/CLAUDE.md`). `/review` and `/audit` never mutate their inputs; `/verify` does, by design.

### D5 — AC-mode mapping (4 modes → behavior)

`runtime-assisted` → `ac-verifier` with Chrome MCP + API + CLI, MCP-probe first, code-fallback for unobservable items; `tests` → run the assembled test command + map to test-referencing ACs, code-read the rest; `code-only` → code-reading (`PASS (code)` / `FAIL (code)` / `PARTIAL (code)`); `off` → skip behavioral AC verification, code-reading floor, verdict notes AC verified by code only. Grounded in the four `ac_verification_mode` values (`_configure/_schema.py:80`) and their `/verify` semantics (`configure/references/q12-ac.md:17–20`).

### D6 — Bug-filing is a `_verify` `file-bugs` verb, not deferred

`file-bugs` writes `bugs/NNN-*.md` in the `.devforge/storage-rules.md` format (`Source: verify`, `:274`), sequential `NNN` numbering scanned from `bugs/`. NOT deferred to the unbuilt `/report-bug` — the format is known + numbering is mechanical, so building it now is cheaper than a forward dependency. (The draft already files bugs at `verify.md:277–304`; this re-points the format path + helper-owns-shape.)

### D7 — /verify owns the verdict; constitution violations always block APPROVED

`/verify` renders APPROVED / NEEDS WORK / REJECTED; `compute-verdict` is deterministic. Constitution violations are always Critical and BLOCK APPROVED (the draft's rule 5, `verify.md:312` — "Constitution violations are always critical"; `/review` carries the same invariant, `src/commands/review/main.md:316`).

## Open questions (OQ-N)

- **OQ-1 — exact `off` / `tests` mode semantics + verdict interaction.** Can a feature be APPROVED when its ACs are code-only-verified under `off` mode? **Lean:** `off` → code-reading floor + the verdict explicitly flags AC as code-verified-only (an honest verdict, not a blocked one). The `tests` mode's interaction with the PHASE-4 `verify-touched` test leg (does `tests` mode dispatch `ac-verifier` at all, or rely solely on the assembled test result?) is also unsettled. Resolve at the Phase 3 / Phase 5 build (the verdict logic forces the decision).
- **OQ-2 — structured `verify-handoff.json` for `/summarize` + `/finalize`.** Deferred: `/summarize` and `/finalize` gate on the spec `**Status**: Complete` flip only today (verified: `src/_pending/commands/finalize.md` + `summarize.md` are pending drafts reading the spec status, not a typed handoff). Build the producer-side typed handoff when those commands are refactored to consume it ("consumer obeys producer"), mirroring plan 20's OQ-3 deferral. For now `verification.md` markdown + the spec flip are the contract.
- **OQ-3 — `_shared/feature_scope.py` flat vs a `_shared/scope/` subpackage.** **Lean flat** — follows the existing `_shared/` flat precedent (`literal_call_shape.py`, `node_bin.py`, `text_overlap.py`, verified via glob). Authoring-mechanics, not architecture; name the choice in the Phase-0 commit + the helper-locations table.
- **OQ-4 — does the PHASE-7 feature-level memory update duplicate `/implement`'s per-task `.devforge/memory.md` writes?** `/implement` writes per-task lessons to `.devforge/memory.md` (verified: `src/CLAUDE.md` Key Rules #4 + the `/implement` memory phase). **Lean:** keep the `/verify` memory update, but LIGHT — feature-level lessons only (what the assembled feature taught, what verification caught that per-task missed), not per-task duplication. Resolve at the Phase 7 build.

## Out of scope (do NOT plan here)

- **Changing `/review` or `/audit` behavior.** Phase 0's scope-resolver extraction keeps `/review` byte-behaviorally identical (`tests/lib/_review/` is the net); `/audit` is untouched.
- **Building `/summarize`, `/finalize`, `/report-bug`, `/refresh-docs`** (pending drafts). `/verify` POINTS to them as next-steps but does not build them; the structured handoff is OQ-2.
- **Changing `/implement`** (`verify-touched` is reused unchanged; no self-repair loop is added to `/verify`).
- **Reshaping the plan-15 agent roster skeleton.** Only `ac-verifier`'s `## Input` contract + mode mapping + dead-key body references are touched (D3).
- **A finder ensemble or refutation pass in `/verify`** (D1 — that is `/review`'s job; the `_shared` refutation engine is NOT reused here).
- **Fixing `/review`'s stale `.claude/memory/MEMORY.md` preflight bug** (finding F). It is flagged so `/verify` does not inherit it; the `/review`-side fix is a separate concern for the orchestrator to route.
- **Fixing the stale `src/commands/review.md` flat-file manifest entry** (`src/manifest.json:21`) — a PRE-EXISTING bug from plan 20's wire-in (`/review` is folder-layout now, so the flat-file source no longer exists and would break `update.sh` on existing installs the same way the `verify.md:15` entry does). Plan 22 removes ONLY its own `verify.md:15` entry (Phase 7); the `review.md:21` entry is a separate `/review`-side fix to route to the orchestrator. Recorded here so it is not lost.

## Context for next session

- `/verify` is the pipeline step AFTER `/review` and BEFORE `/summarize`/`/finalize` (`/implement → /review → /verify → /summarize → /finalize`, verified `src/CLAUDE.md` Workflow). Its defining job: **the verdict** — `/review` is findings-only (`src/commands/review/main.md:12`), `/verify` owns APPROVED / NEEDS WORK / REJECTED. It adds AC conformance + assembled mechanical checks + folds `/review`'s findings + flips the spec to Complete on top of `/review`'s findings. See the three-command invariant table in `## Command mission`.
- **HYBRID reuse (D2):** Phase 0 extracts `resolve_feature_scope` from `_review/_scope.py` into `_shared/feature_scope.py` (parameterize the `=== Review Scope ===` heading label, `_scope.py:407`; re-point `/review`; `tests/lib/_review/test_scope.py` is the net), and `/verify` reuses the installed `implement_helper verify-touched` binary (`--files`/`--root`/`--iteration`, `_cmds_verify.py:646–677`; statuses `{pass, self_repair, failed, isolation_failure, tooling_unavailable}`) report-only at `--iteration 0` — NO self-repair loop, NO `/implement` change. `/verify` does NOT reuse the `_shared` refutation engine (it is not a finder ensemble).
- **`_verify/` mirrors `_review/`:** `_cli.py` registry (`_review/_cli.py:798`), `_state.py` (`VerifyState` per-feature at `specs/[feature]/verify-state.json`), `_preflight.py` (setup-chain + constitution gate; reads `.devforge/memory.md` NOT `.claude/memory/MEMORY.md` — finding F), `_ac.py`, `_hygiene.py` (the `check-hygiene` verb), `_review_findings.py`, `_verdict.py`, `_report.py` (writes `verification.md`), `_bugs.py`, `_specstatus.py`. Launchers `verify_helper{,.py}` mirror `review_helper{,.py}` (`review_helper.py:14–18`). Scratch literal `${TMPDIR:-/tmp}/forge-verify` (NOT forge-review/forge-audit).
- **The stale draft's audit (`## What's stale in the draft`):** dead config keys `AC_VERIFICATION*` + `auto/browser-only/api-only` → live `ac_verification_mode` ∈ `{code-only, tests, runtime-assisted, off}` + `ac_runtime_*` (`_configure/_schema.py:62–66,80`); `.claude/` paths → `.devforge/`; `/execute-task` → `/implement`; CLAUDE.md-command checks → scope-aware `verify-touched`; the `ac-verifier` agent itself reads the dead keys (`ac-verifier.md:27–29`) — fixed in Phase 3.
- **9 phases:** 0 shared scope extraction → 1 `_verify/` scaffold + preflight + state → 2 input verbs (parse-acs, read-ac-config, read-review-findings, resolve-feature-scope) → 3 ac-verifier agent fix + 4-mode mapping → 4 checks + merge (verify-touched report-only reuse, merge-ac-results, check-hygiene) → 5 verdict + report + bugs + status-flip → 6 main.md + references → 7 wire-in (add `verify` to `_PROMOTED` at `claude.py:51`; delete stale draft; reconcile `src/CLAUDE.md` + `q12-ac.md`; cross-ref sweep; install ride) → 8 testForge20 e2e (USER-DRIVEN HARD GATE).
- **4 OQs:** OQ-1 (`off`/`tests` mode + verdict interaction; lean code-floor + honest verdict), OQ-2 (structured `verify-handoff.json`; deferred until `/summarize`/`/finalize` consume it), OQ-3 (`_shared/feature_scope.py` flat; lean flat), OQ-4 (feature-level memory update; lean keep-but-light).
- **Deliberate departure recorded (D4):** `/verify` is the only review/verify command that writes back to its input (flips the spec Status) — justified by ownership of the Complete lifecycle transition `/summarize`+`/finalize` gate on.
- **Verified file:line facts (this session):** `_PROMOTED` lacks `verify` (`scripts/emitters/claude.py:51`, ends `…, "audit", "review")`); config enum `ac_verification_mode ∈ {code-only, tests, runtime-assisted, off}` (`_configure/_schema.py:80`) + the four `ac_*` field tuple (`:62–66`); the four modes' `/verify` semantics (`configure/references/q12-ac.md:17–20`); `verify-touched` interface + statuses (`_implement/_cmds_verify.py:646–677, 59–66, 608/621/632`); the scope resolver + `=== Review Scope ===` literal + git helpers (`_review/_scope.py:51–175, 232–372, 380–433, 407`); `_review/_preflight.py` stale `.claude/memory/MEMORY.md` (`:68–69,163–169`) + the sentinel/setup-chain sets (`:31–35,39–45`); `review_helper.py` shim shape (`:14–18`); spec status enum (`_specify/_schema.py:32–34`); task satisfied set (`_implement/_cmds_resolve.py:41`); AC checkbox + spec status rendered shapes (`tests/lib/fixtures/specify-sample-migration.md:4,31`); bug-file format + `Source: verify` (`src/devforge/storage-rules.md:250–310,274`); the `ac-verifier` dead keys (`ac-verifier.md:27–29,44,56,119`); the `/verify` reference inventory (`src/CLAUDE.md` Workflow + Command-Details; `q12-ac.md:7,17–20`; `specify/main.md:575`; `implement/main.md:44,91`; `plan/main.md:24,109`; `breakdown/main.md:23`; `audit/main.md:289`; `manifest.json`; the pending `summarize.md`/`finalize.md`; the stale draft `src/_pending/commands/verify.md`).

## When resuming work

1. **Re-read this plan in full** + the live files it grounds against: `src/_pending/commands/verify.md` (the stale draft being replaced), `src/commands/review/main.md` + `src/devforge/lib/_review/{_cli,_preflight,_state,_scope,_report}.py` (the structural model + the resolver being extracted), `src/devforge/lib/_shared/` (the extraction target), `src/agents/ac-verifier.md` (the agent Phase 3 fixes), `src/devforge/lib/_implement/_cmds_verify.py` + `src/commands/implement/main.md` PHASE 5 (the `verify-touched` binary reused), `src/devforge/lib/_configure/_schema.py` + `src/commands/configure/references/q12-ac.md` (the live AC config contract), `src/devforge/storage-rules.md` (the bug format), and `src/CLAUDE.md` (the `/verify` entry + workflow chain the wire-in reconciles). The `main.md`/helper line numbers above are pre-edit; re-read each file from scratch after a phase edits it.
2. **No blocking OQ before Phase 0** — Phase 0 (the scope extraction) is independent of the four OQs; OQ-1 (mode semantics) resolves at Phase 3/5, OQ-2/3/4 ride their leans. Execute Phase 0 first.
3. **Execute Phases 0→8 in order** (each green before the next). Phase 0 is the foundation (the shared resolver); Phases 1–5 build `_verify/` on top; Phase 6 writes `main.md` + references; Phase 7 wires it into the emitter + reconciles docs; Phase 8 is the user-driven HARD GATE.
4. Route every Python helper change through **python-engineer → python-reviewer** with a test written + run in the same turn (round-trip REAL producer output — a real `spec.md` AC section, a real `review_helper`-rendered `review.md`, a real `ac-verifier`-shaped report, a real `spec.md` + `tasks/` fixture for the flip — not hand-faked fixtures); route every command/spec/reference/CLAUDE.md/agent/plan markdown edit through **instruction-author → instruction-reviewer**; verify the `ac-verifier` Task dispatch shape, `subagent_type` usage, command frontmatter, and the emitter/install behavior via the **claude-code-guide** agent BEFORE writing the relevant spec.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(verify): live AC + verdict command on the shared scope resolver`, `refactor(shared): extract assembled-feature scope resolver from _review`, `fix(ac-verifier): align Input contract to live ac_runtime_* config keys`).

## Related plans

- `20-REVIEW-COMMAND-REDESIGN-PLAN.md` — the STRUCTURAL MODEL for this plan (the `_review/` subpackage shape, the `_shared/` extraction precedent, the per-feature state + scratch-chain + helper/orchestrator split) AND the producer of `specs/[feature]/review.md` that `/verify` consumes (PHASE 2 folds its findings into the verdict). Phase 0 here extracts the scope resolver `/review` ships, the same way plan 20's Phase 0 extracted the refutation engine from `/audit`.
- `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` — the `/implement` PER-TASK 4-reviewer panel + per-task `verify-touched` gate (SHIPPED). `/verify` is the ASSEMBLED cross-task gate ABOVE that per-task gate — it runs `verify-touched` over the whole feature diff together (catching what per-task green cannot guarantee) and reuses the same binary report-only.
- `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` — produces the task list + `breakdown-handoff.json` that `/verify`'s `flip-spec-status` cross-checks (all tasks `Complete`/`Skipped` before flipping the spec to Complete).
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — the `/plan` → handoff chain; `plan/main.md:109` already references the "post-`/verify` Complete state" `/verify` sets.
- Downstream consumers gating on the spec Complete flip `/verify` performs: `/summarize` and `/finalize` (pending drafts, `src/_pending/commands/{summarize,finalize}.md`) — `/finalize` is "Gate-checked: spec must be Complete (set by `/verify`)" (`src/CLAUDE.md`). The structured `verify-handoff.json` for them is deferred (OQ-2).
