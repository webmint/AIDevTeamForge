# 24 — SUMMARIZE COMMAND REDESIGN PLAN

**Status:** **✅ DONE 2026-06-18** — all phases (1–5) shipped on `develop-2.0-init` (committed `8f978e1`); Phase 5 testForge20 e2e VALIDATED. Redesigns the stale pre-pivot `/summarize` draft (`src/_pending/commands/summarize.md`, 5 phases) into a live, emitted, pipeline-wired command at `src/commands/summarize/main.md` + `references/` + a `src/devforge/lib/_summarize/` helper subpackage + a `summarize_helper{,.py}` launcher, structurally modeled on the just-shipped `/verify` command (plan 22). It REUSES one already-shipped piece — the assembled-feature scope resolver `_shared/feature_scope.py` (created by plan 22 Phase 0) — rather than re-implementing or re-extracting it. `/summarize` is **pure synthesis**: it runs NO finder ensemble, NO refutation engine, and NO verdict. It writes one artifact, `specs/[feature]/summary.md`, idempotently, and mutates none of its inputs. Scope is `/summarize` ONLY — `/finalize` is the sibling follow-on plan 25.

## Scope & assumptions

These are decided, not open (except the OQs in `## Open questions`):

1. **`/summarize` is the pipeline step AFTER `/verify` approves and BEFORE `/finalize`** — the full Workflow chain in `src/CLAUDE.md` reads `… /implement → /review → /verify → /summarize → /finalize` (verified against the "Spec-Driven Development Flow" code block in `src/CLAUDE.md`, the SSOT for pipeline position). `/summarize` is pipeline-wired in that slot; its source today is only an unbuilt flat draft at `src/_pending/commands/summarize.md`.
2. **The target is a NEW live command tree** at `src/commands/summarize/` (`main.md` + `references/*.md`), a NEW helper subpackage `src/devforge/lib/_summarize/`, and a NEW launcher `src/devforge/lib/summarize_helper{,.py}`. The stale `src/_pending/commands/summarize.md` draft is DELETED (Phase 4), not rewritten — leaving it on disk is a future-hallucination seed (a fresh session could mistake the draft for the SSOT; plans 19/20/22 made the same call for the `/audit`, `/review`, and `/verify` drafts).
3. **Every file path, config key, and identifier in this plan is verified against the live tree this session.** The `main.md` / helper line numbers cited are pre-edit; after a phase edits a file, re-read it from scratch rather than navigating by these numbers.
4. **Build NOW; do NOT gate on `/verify`'s testForge20 e2e** (plan 22 Phase 8, the user-driven HARD GATE). `/verify` ships in the working tree (uncommitted) per plan 22 — `src/commands/verify/main.md`, `src/devforge/lib/_verify/`, `verify_helper{,.py}`, and `verify_helper render-report` (which writes `specs/[feature]/verification.md`) all exist this session. `/summarize`'s producer (`verification.md`) is therefore real, not hypothetical — `/summarize` consumes a concrete artifact.
5. **`_shared/feature_scope.py` already exists** (created by plan 22 Phase 0; verified via glob this session — `src/devforge/lib/_shared/feature_scope.py` with `resolve_feature_scope` at `:298` and `_render_scope_block` taking a `heading_label` param defaulting to `"Review Scope"` at `:237`). `/summarize` IMPORTS it; there is NO Phase 0 extraction in this plan.

## Command mission (what /summarize is for)

`/summarize` exists to own the ONE job nothing else in the pipeline owns: **the PR-ready human-facing feature narrative**. `/verify` owns the verdict (verified: `src/commands/verify/references/report-format.md:7` — "This report ENDS in a verdict. `/verify` owns the verdict; `/review` does not"). `/review` owns findings. `/summarize` owns the synthesized story of what was built — in user terms — once the feature record is complete: what was built, the change stats, key decisions, deviations from plan, and the AC status. Its output is copy-ready for a PR description.

The synthesis is **orchestrator-inline** (D1): `main.md` composes the summary prose directly from structured helper inputs — there is NO agent dispatch (no tech-writer). It is a 1-page section-templated synthesis; the stale draft already does it inline (`src/_pending/commands/summarize.md:36-74`), and consistency-over-invention keeps it that way.

**The boundary, stated explicitly:** `/summarize` runs NO finder ensemble, NO refutation engine, and NO verdict. It does not verify (that is `/verify`), does not find issues (that is `/review`), and does not squash commits or generate docs (that is `/finalize`). A future session must NOT wire any finder/refuter/verdict machinery into `/summarize` by analogy with `/review` or `/verify`. (This is D1.)

### The /verify-vs-/summarize-vs-/finalize invariant

`/verify`, `/summarize`, and `/finalize` are three consecutive pipeline commands with non-overlapping jobs. This table is the invariant the plan must preserve:

| Axis | `/verify` | `/summarize` | `/finalize` |
|---|---|---|---|
| **Trigger** | in-pipeline, after `/review` | in-pipeline, after `/verify` approves | in-pipeline, after `/summarize` |
| **Reads** | spec ACs + assembled diff + `review.md` | spec + plan + tasks(+`## Completion Notes`) + git + `verification.md` | spec + plan + tasks + `summary.md` |
| **Writes** | `specs/[feature]/verification.md` + FLIPS spec `**Status**:` | `specs/[feature]/summary.md` | `docs/` + squashes WIP → clean commit |
| **Job** | AC conformance + assembled mechanical + verdict | PR-ready feature narrative | docs + history cleanup |
| **Mutates input?** | **YES** — flips the spec to Complete | **NO** — read-only on inputs | **YES** — squashes commits |

The `/summarize` "Mutates input? NO" cell is the deliberate contrast with `/verify`'s "YES" (D4): `/verify` writes back to its input (the spec) because it owns the Complete lifecycle transition; `/summarize` writes only `summary.md` and touches none of its inputs.

## What's stale in the draft (the audit)

The draft `src/_pending/commands/summarize.md` predates the 4-command setup-chain pivot, the `/execute-task → /implement` rename, the `/review` + `/verify` builds, and `_shared/feature_scope.py`. Each finding below gives the draft's wrong value → the correct current value + the file:line that proves it. (All line numbers are pre-edit.)

**A. Stale config path.** `.claude/project-config.json` (`summarize.md:26`) → `.devforge/project-config.json` (verified: the install-root config path throughout `src/CLAUDE.md`, e.g. the References block — "[Project Config](.devforge/project-config.json)").

**B. Stale branch/source-root resolution.** The draft reads `DEFAULT_BRANCH` and `SOURCE_ROOT` from project-config (`summarize.md:26`) → `source_root` resolves from `CLAUDE.md` Project Root / Source Root via a preflight helper (mirror `_verify/_preflight.py:70,84` — the `source_root` key — and `:129-149` — the wrapper-mode + Project-Root/Source-Root extraction; default `.`), and the merge-base / branch diff is computed by `_shared/feature_scope.py`'s resolver, NOT a hand-read `DEFAULT_BRANCH` line.

**C. Stale change-data gathering.** The draft's manual `git diff --stat [DEFAULT_BRANCH]...HEAD` + `git log` gathering (`summarize.md:28-29`) → reuse the `_shared/feature_scope.py` assembled-scope resolver for the file list + scope block, and add a small `git diff --stat <base>..HEAD` only for the +/- line totals (the resolver is `--name-only`-based — it gives the file list, NOT insertion/deletion counts). The indirectly-referenced `/execute-task` is the renamed `/implement` (live spec `src/commands/implement/main.md`).

**D. Re-derived ACs.** The draft re-derives ACs from the spec (`summarize.md:69-73`) → consume `verification.md`'s AUTHORITATIVE `## Acceptance Criteria` table instead (D3). `/verify` already proved each AC PASS/FAIL/PARTIAL (verified: `src/commands/verify/references/report-format.md:33-35` — the `| AC-N | <status> | <evidence> |` table); `/summarize` must NOT re-derive AC status from the spec.

**E. Structural gap.** There is no `_summarize/` subpackage, no `summarize_helper{,.py}` launcher, and no `tests/lib/_summarize/`; `summarize` is ABSENT from the emitter `_PROMOTED` tuple (verified: `scripts/emitters/claude.py:51` — the tuple ends `…, "audit", "review", "verify")` and does NOT contain `summarize`, so `/summarize` is NOT emitted today). There is also a stale flat-file manifest entry (verified: `src/manifest.json:18` — `{ "source": "src/commands/summarize.md", "target": ".claude/commands/summarize.md" }`).

**Still valid (keep).** The draft's `## Completion Notes` reading of task files (`summarize.md:19-21`) is STILL VALID — `/implement` fills each task's `## Completion Notes` via `implement_helper mark-complete` (verified: `src/devforge/lib/_implement/_cmds_complete.py:293` `_fill_completion_notes`, heading regex `:124` `_COMPLETION_NOTES_HEADING`). Keep the read; re-point the helper-owns-shape parsing into a `_summarize/` verb. The draft's "Concise over comprehensive", "User-facing language", "Deduplicate", "No speculation", and "Idempotent" rules (`summarize.md:97-101`) are also still correct and carry forward.

## Reuse architecture (confirmed decisions)

**Single reuse; one engine explicitly NOT reused.**

**1. NO Phase 0 extraction — `_shared/feature_scope.py` already exists.** Unlike plan 22 (which extracted the resolver from `_review/_scope.py` in its Phase 0), this plan does NOTHING to `_shared/`. `_shared/feature_scope.py` was created by plan 22 Phase 0 and ships in the working tree (verified via glob this session). `/summarize` imports `resolve_feature_scope` from it and calls it with `heading_label="Summary Scope"` (the heading-label parameter exists — `_shared/feature_scope.py:237,303` — and plan 22 already used "Review Scope"/"Verification Scope" through it). **A future session must NOT re-extract anything into `_shared/`** — the module is already shared, and adding a heading-label value is a call-site argument, not a code change to `_shared/`.

**2. `/summarize` reuses git stats via a small `git diff --stat` call** for the +/- insertion/deletion totals. The `_shared` resolver is `--name-only`-based — it returns the changed-file list (`files`, `files_for_finders`, `file_count`, `scope_block`), NOT line-change stats. So `_summarize`'s change-data verb supplements the resolver's file list with one `git diff --stat <base>..HEAD` for the totals line.

**3. `/summarize` does NOT reuse the `_shared` refutation engine** (`findings_schema` / `_consume` / `_validate` / `_consensus` / `_verify`, the engine plan 20 extracted and `/audit` + `/review` use). `/summarize` is not a finder ensemble — it has no findings of its own to validate or cross-examine; it synthesizes a narrative from already-complete artifacts. State this explicitly so a future session does not wire the refutation engine into `/summarize` by analogy with `/review`/`/verify`. (This is D1 + D2.)

## Helper / orchestrator split + module list

The `_summarize/` subpackage mirrors `_verify/`'s / `_review/`'s structure but LEANER — there is no verdict, no finder ensemble, and no bug-filing, so it has fewer modules. It uses a verb-registry `_SUBCOMMAND_REGISTRY` in `_cli.py` dispatching `(verb, help, handler)` triples (mirror `_verify/_cli.py`), a `main()` argv dispatch, and atomic writes via `tempfile.mkstemp` + `os.replace`. The helper owns the preflight/gate, structured-input gathering + parsing (read-side), and atomic file placement; the orchestrator (`main.md`) owns the prose synthesis (D1, inline, agent-free) and phase pacing.

The module list below is a STARTING POINT the python-engineer → python-reviewer loop will right-size — do not treat the optional modules as committed surface.

Modules:

- `__init__.py` — re-export `main` (mirrors `_verify`).
- `_cli.py` — verb registry `_SUBCOMMAND_REGISTRY` + argparse/argv dispatch (mirror `_verify/_cli.py`).
- `_preflight.py` — setup-chain gate + the **spec `**Status**: Complete` gate** (STOP if the resolved spec is not `Complete` → "run /verify first") + `source_root` / `wrapper_mode` resolution from `CLAUDE.md` (mirror `_verify/_preflight.py:70,84,129-149`; reads `.devforge/` paths, NOT `.claude/`).
- `_changes.py` — the `gather-change-data` verb: the changed-file list + `scope_block` via `_shared.feature_scope.resolve_feature_scope(heading_label="Summary Scope")`, a `git diff --stat <base>..HEAD` for the +/- totals, group-by-directory, and wrapper-mode source-repo changes (`git -C $SOURCE_ROOT …` when `SOURCE_ROOT != "."`).
- `_inputs.py` — `read-verification` (the AC status table + verdict parsed from `verification.md`), `parse-completion-notes` (per-task Files-changed + deviations + notes from task files' `## Completion Notes`), and `read-plan-decisions` (the key decisions — `plan.md`'s key-decisions section, D9).
- `_report.py` (optional) — a thin `write-summary` / atomic-placement verb, OR the orchestrator Writes `summary.md` directly. Flag the split as a build-time call.

Verbs (kebab-case):

- `preflight` — setup-chain + the spec-`Complete` gate + `source_root`/`wrapper_mode` context.
- `gather-change-data` — assembled scope (via `_shared`) + `git diff --stat` totals + group-by-directory + wrapper-mode source changes.
- `read-verification` — parse `verification.md`'s `## Acceptance Criteria` table + `## Verdict` into the authoritative AC status + verdict.
- `parse-completion-notes` — parse each task file's `## Completion Notes` into Files-changed + deviations + notes.
- `read-plan-decisions` — read the key decisions (`plan.md`'s key-decisions section, D9).
- `write-summary` (optional) — atomic `summary.md` placement.

Launchers `summarize_helper` (POSIX shell) + `summarize_helper.py` (python shim) mirror `verify_helper{,.py}` verbatim in shape (verified: `src/devforge/lib/verify_helper.py:16-20` — `_LIB_DIR` `sys.path` insert + `from _verify._cli import main`); `summarize_helper.py` imports `from _summarize._cli import main`. **Scratch dir literal `${TMPDIR:-/tmp}/forge-summarize`** — NOT `forge-verify` / `forge-review` / `forge-audit` (collision avoidance; the reason each command picks a distinct workdir, e.g. `/verify` chose `forge-verify`).

## The command runtime phases (described inside main.md)

`main.md` wires a 6-phase runtime flow. (These PHASE 0–5 numbers are runtime-internal — distinct from the build-phase numbering in `## Phases`; the `## Phases` section's Phase 3 BUILDS this `main.md` with all six runtime PHASES inside it.) Each Bash block re-establishes `WORKDIR="${TMPDIR:-/tmp}/forge-summarize"` at its top (the `/review`/`/verify` scratch-chain pattern):

- **PHASE 0** — preflight + feature resolution + the spec-`Complete` gate + scratch (`$WORKDIR=forge-summarize`). STOP if the resolved spec is not `**Status**: Complete` ("run /verify first").
- **PHASE 1** — gather change data (the assembled scope via `_shared.feature_scope` with heading "Summary Scope" + `git diff --stat` +/- totals + group-by-directory + wrapper-mode source-repo changes when `SOURCE_ROOT != "."`).
- **PHASE 2** — read inputs (`verification.md`'s AC status + verdict; each task's `## Completion Notes`; the plan's key decisions).
- **PHASE 3** — compose the summary prose INLINE (orchestrator, agent-free; sections: What was built / Changes / Files changed / Key decisions / Deviations [omit if none] / Acceptance criteria — AC status taken from `verification.md`, NOT re-derived; user-facing language; 1–5 lines per section).
- **PHASE 4** — write `specs/[feature]/summary.md` (idempotent overwrite) + a `[WIP]` commit (`[WIP] Feature summary: NNN-…`, per the Commit Convention in `src/CLAUDE.md`).
- **PHASE 5** — present the summary + the next-step pointer (→ `/finalize`).

## Spec / task status facts (for the gate + the AC table)

- **Spec status** is a markdown bold line `**Status**: <value>`, value ∈ `{Draft, Approved, In Progress, Complete}` (verified: `src/devforge/lib/_specify/_schema.py:32-34` `SPEC_STATUS_ENUM`; rendered shape `**Status**: Draft` at `tests/lib/fixtures/specify-sample-migration.md:4`). The `Complete` flip is set by `/verify`'s `flip-spec-status` (plan 22); `/summarize`'s PHASE-0 gate STOPS if the spec is not `Complete`.
- **AC status is AUTHORITATIVE in `verification.md`, NOT re-derived from the spec.** `verification.md`'s `## Acceptance Criteria` table rows are `| AC-N | <status> | <evidence> |` with status ∈ `{PASS, FAIL, PARTIAL, MANUAL, PASS (code), FAIL (code), PARTIAL (code), UNVERIFIED}` (verified: `src/commands/verify/references/report-format.md:14,33-35`); the verdict is `## Verdict` → `**APPROVED**` / `**NEEDS WORK**` / `**REJECTED**` (verified: `report-format.md:71-73`). `/summarize`'s `read-verification` parser round-trips a REAL `verify_helper render-report` output (`src/devforge/lib/_verify/_report.py:101` `render_report`), not a hand-authored fixture.
- **Spec ACs** in the spec itself are checkboxes `- [ ] **AC-N**: <EARS sentence>` (verified: `tests/lib/fixtures/specify-sample-migration.md:31`). `/summarize` does NOT read these for status — it reads `verification.md`'s table (D3). The spec ACs may be consulted only for the short human-readable AC label text alongside the authoritative status, if that proves needed at the Phase-2 build.
- **Task `## Completion Notes`** are filled per task by `/implement` (verified: `src/devforge/lib/_implement/_cmds_complete.py:293` `_fill_completion_notes`; heading regex `:124`). `parse-completion-notes` reads them for Files-changed + deviations + notes.

## Phases (build order)

Each phase: objective, files touched, helper verbs/modules introduced, an execution agent-loop note, a `#### Verify` fenced bash block, and a `DoD:` line. Per repo discipline (CLAUDE.md): every `.py` helper change goes through **python-engineer → python-reviewer** with a test written + actually run in the SAME turn (test-immediately-after-write; parsers round-trip REAL producer output, not hand-faked fixtures); every command/spec/reference/CLAUDE.md/plan markdown edit goes through **instruction-author → instruction-reviewer** (route-spec-edits-through-agent-flow); for any Claude-Code-integration concern — command frontmatter (`disable-model-invocation`, `argument-hint`), the emitter/install behavior — verify current conventions via the **claude-code-guide** agent BEFORE writing the spec (confidence is not verification). Each phase leaves the system buildable and tests green. There is NO Phase 0 (no shared extraction — `_shared/feature_scope.py` already exists); the build starts at Phase 1.

### Phase 1 — `_summarize/` scaffold + preflight + spec-Complete gate

**Objective:** create the `_summarize/` subpackage, the launchers, the verb registry, and the preflight gate that STOPS unless the spec is `Complete`.

- **Files touched:** new `src/devforge/lib/_summarize/` subpackage (`__init__.py`, `_cli.py` with `_SUBCOMMAND_REGISTRY` mirroring `_verify/_cli.py`); new launchers `src/devforge/lib/summarize_helper` (POSIX shell) + `src/devforge/lib/summarize_helper.py` (the `.py` shim mirrors `verify_helper.py:16-20` verbatim in shape — `_LIB_DIR` `sys.path` insert + `from _summarize._cli import main`); new `src/devforge/lib/_summarize/_preflight.py`.
- **Modules/verbs introduced:** a `preflight` verb that gates on (a) the 4-command setup chain `/init-forge → /generate-docs → /configure → /constitute` (mirroring `_verify/_preflight.py`'s setup-chain artefact set), (b) the **spec `**Status**: Complete` gate** — STOP with "run /verify first" if the resolved spec is not `Complete` (the enum is `src/devforge/lib/_specify/_schema.py:32-34`), and (c) `source_root` / `wrapper_mode` resolution from `CLAUDE.md` (mirror `_verify/_preflight.py:70,84,129-149`). **Deliberately OMITS the constitution-populated sentinel guard that `/verify`/`/review` carry** (`_verify/_preflight.py` `_UNPOPULATED_SENTINELS`) — `/summarize` never reads `constitution.md` content (it is pure synthesis), and the spec-`Complete` gate is a strictly stronger precondition than a populated constitution at this pipeline stage; flag per consistency-over-invention so a future session does not add it back. **The preflight reads `.devforge/` paths, NOT `.claude/`.** (Stateless per D8 — no `_state.py`, no `check-status-and-flip` verb.)
- **Execution:** python-engineer → python-reviewer; tests round-trip a real `CLAUDE.md` + a real `spec.md` fixture in BOTH states (a `Complete` spec passes the gate; a not-`Complete` spec is rejected with the "run /verify first" stop) in the same turn.

#### Verify

```bash
ls src/devforge/lib/_summarize/ src/devforge/lib/summarize_helper src/devforge/lib/summarize_helper.py   # expect: present
grep -n "_SUBCOMMAND_REGISTRY" src/devforge/lib/_summarize/_cli.py   # expect: registry present, mirroring _verify
grep -n "from _summarize._cli import main" src/devforge/lib/summarize_helper.py   # expect: the shim imports _summarize
grep -n "Complete\|run /verify\|run `/verify`" src/devforge/lib/_summarize/_preflight.py   # expect: the spec-Complete gate + the stop message
grep -n "\.devforge\|MEMORY.md\|.claude/memory" src/devforge/lib/_summarize/_preflight.py   # read: only .devforge/ paths, NO .claude/ paths
python -m pytest tests/lib/_summarize/test_preflight.py   # expect: green (Complete spec passes; not-Complete spec rejected)
```

DoD: `_summarize/` subpackage + `summarize_helper{,.py}` launchers + `_preflight.py` exist; the `preflight` verb gates the setup chain + the spec-`Complete` gate (STOP → "run /verify first") + resolves `source_root`/`wrapper_mode` from `CLAUDE.md` reading `.devforge/` paths; helper tests written + run + green (both spec states); python-reviewer loop applied.

### Phase 2 — input / gather verbs

**Objective:** the read-side verbs that gather the assembled change data, the authoritative AC status + verdict, the per-task completion notes, and the plan's key decisions — parsers round-tripping REAL producer output.

- **Files touched:** new `src/devforge/lib/_summarize/_changes.py` (the change-data gatherer), `src/devforge/lib/_summarize/_inputs.py` (the `verification.md` / completion-notes / plan-decisions parsers), and the `gather-change-data` / `read-verification` / `parse-completion-notes` / `read-plan-decisions` wiring in `_cli.py`.
- **Modules/verbs introduced:** `gather-change-data` (the assembled-file list + `scope_block` via `_shared.feature_scope.resolve_feature_scope(heading_label="Summary Scope")` — same JSON contract `/verify` consumes: `files`, `files_for_finders`, `file_count`, `scope_block` — PLUS a `git diff --stat <base>..HEAD` for the +/- totals, group-by-directory, and the wrapper-mode `git -C $SOURCE_ROOT` source-repo changes when `SOURCE_ROOT != "."`); `read-verification` (parses `verification.md`'s `## Acceptance Criteria` table into the authoritative per-AC status + the `## Verdict` line); `parse-completion-notes` (parses each task file's `## Completion Notes` into Files-changed + deviations + notes); `read-plan-decisions` (reads the key decisions — `plan.md`'s key-decisions section, D9).
- **Execution:** python-engineer → python-reviewer; parsers round-trip REAL producer output — `read-verification` against a real `verify_helper render-report`-rendered `verification.md` (NOT a hand-authored fixture); `parse-completion-notes` against a real `implement_helper mark-complete`-filled task file; `gather-change-data` against a real git scope (a fixture repo with a feature branch + a merge-base).

#### Verify

```bash
grep -n "gather-change-data\|read-verification\|parse-completion-notes\|read-plan-decisions" src/devforge/lib/_summarize/_cli.py   # expect: all registered
# gather-change-data reuses _shared with the Summary Scope heading:
grep -n "feature_scope\|Summary Scope\|diff --stat" src/devforge/lib/_summarize/_changes.py   # expect: imports _shared resolver, passes "Summary Scope", adds diff --stat for totals
# read-verification round-trips a real verify_helper-rendered verification.md:
python -m pytest tests/lib/_summarize/test_inputs.py tests/lib/_summarize/test_changes.py   # expect: green (round-trip via the real producers)
```

DoD: `gather-change-data` (reusing `_shared` with `heading_label="Summary Scope"` + `git diff --stat` totals + group-by-directory + wrapper-mode source changes), `read-verification` (authoritative AC table + verdict), `parse-completion-notes` (per-task notes from a real `mark-complete`-filled file), and `read-plan-decisions` are registered and tested; the `verification.md` parser round-trips a real `verify_helper render-report` output and the completion-notes parser round-trips a real `implement_helper mark-complete` task file; python-reviewer loop applied.

### Phase 3 — main.md + references

**Objective:** write the live command spec wiring the 6 runtime phases + the orchestrator-inline synthesis + the reference.

- **Files touched:** new `src/commands/summarize/main.md` (frontmatter `name: summarize`, a `description`, `argument-hint: "[spec-file]"`, `disable-model-invocation: true` — mirroring `src/commands/verify/main.md:1-6`) wiring the `$WORKDIR=forge-summarize` scratch-chain, the PHASE-0 preflight + spec-`Complete` gate, the PHASE-1 change-data gather, the PHASE-2 input reads, the PHASE-3 orchestrator-inline synthesis (the six sections, AC status from `verification.md`), the PHASE-4 idempotent `summary.md` write + `[WIP]` commit, and the PHASE-5 present + `/finalize` next-step; new `src/commands/summarize/references/summary-format.md` (the `summary.md` skeleton — orientation only, NOT a verbatim template the orchestrator fills mechanically, since the synthesis is inline prose).
- **Modules/verbs introduced:** none — this is the orchestrator spec composing the Phase-1/2 verbs. NO agent is dispatched (D1).
- **Execution:** instruction-author → instruction-reviewer; **claude-code-guide consulted FIRST** for command frontmatter conventions (`disable-model-invocation`, `argument-hint`) BEFORE writing `main.md` (this plan file is itself a repo-root plan and does NOT ship into `.claude/`, so it needs no claude-code-guide; `main.md` DOES ship and DOES). Resolve OQ-2 here (keep the stale draft's "already-finalized" warning, re-pointed to the live commit conventions).

#### Verify

```bash
ls src/commands/summarize/main.md src/commands/summarize/references/summary-format.md   # expect: present
grep -n "disable-model-invocation: true\|argument-hint" src/commands/summarize/main.md   # expect: frontmatter present
grep -n "forge-summarize\|WORKDIR" src/commands/summarize/main.md   # expect: the $WORKDIR scratch-chain (forge-summarize, NOT forge-verify)
grep -n "verification.md\|gather-change-data\|read-verification" src/commands/summarize/main.md   # expect: consumes verification.md + the gather/read verbs
grep -n "ac-verifier\|tech-writer\|subagent_type" src/commands/summarize/main.md   # expect: NO match (no agent dispatch — D1)
grep -n "compute-verdict\|flip-spec-status" src/commands/summarize/main.md   # expect: NO match (summarize renders no verdict + mutates no spec — D1/D4)
grep -n "Status.*Complete\|run `/verify`\|/finalize" src/commands/summarize/main.md   # expect: the Complete gate + the /finalize next-step
```

DoD: `src/commands/summarize/main.md` wires the 6 runtime phases (preflight+gate → change-data → inputs → inline synthesis → write+WIP-commit → present) with `forge-summarize` scratch, consumes `verification.md` for authoritative AC status, dispatches NO agent and renders NO verdict (D1 — the no-match grep checks for no agent-dispatch names (`ac-verifier`/`tech-writer`/`subagent_type`) and no verdict-render verbs (`compute-verdict`/`flip-spec-status`); the words `finder`/`refutation` may legitimately appear in boundary negations ("NO finder ensemble, NO refutation pass") and the `files_for_finders` key, so they are NOT in the no-match set; `/summarize` may still REFERENCE the verdict it reads from `verification.md`, it just never renders one), and writes `summary.md` idempotently; `references/summary-format.md` documents the `summary.md` skeleton as orientation; OQ-2 resolved (re-pointed "already-finalized" warning); instruction-reviewer + claude-code-guide loops applied.

### Phase 4 — wire-in

**Objective:** make `/summarize` emit + install, delete the stale draft, remove the stale manifest entry, and reconcile every `/summarize` reference.

- **Add `"summarize"` to the emitter `_PROMOTED` tuple** — `scripts/emitters/claude.py:51` (verified: the tuple currently ends `…, "audit", "review", "verify")` and does NOT contain `summarize`). Append `"summarize"`.
- **DELETE the stale `src/_pending/commands/summarize.md`** (the pre-pivot draft superseded by the live command). Sweep for any live consumer of that path first.
- **REMOVE the stale flat-file manifest entry** — `src/manifest.json:18` carries `{ "source": "src/commands/summarize.md", "target": ".claude/commands/summarize.md" }`. The folder layout (`src/commands/summarize/`) is `_PROMOTED`-handled by the emitter; the flat-file source `src/commands/summarize.md` does NOT exist, so leaving the entry would break `update.sh` on existing installs (it syncs each manifest `source` path). This is the IDENTICAL bug plan 22 Phase 7 removed for the `verify.md` entry. **Also remove the pre-existing stale `src/commands/review.md` flat-file entry** (`src/manifest.json:20` — re-verify the line) in this same manifest edit: `/review` is folder-layout (it is in `_PROMOTED`), so its flat-file source no longer exists and the entry would break `update.sh` on existing installs — the identical bug class. Plan 22 Phase 7 flagged it ('a separate `/review`-side fix to route to the orchestrator') but did not remove it; Phase 4 is the next manifest edit and the natural place to close it.
- **Reconcile `src/CLAUDE.md`:** the `/summarize` Command-Details entry already exists (verified: `src/CLAUDE.md` `#### /summarize [spec-file]`) and the Workflow chain already names `… /verify → /summarize → /finalize` correctly. Update the Command-Details BODY to describe the redesigned command (PR-ready synthesis consuming `verification.md` + the spec + plan + task completion notes + git, agent-free, writes `summary.md`) while keeping it a PURPOSE ONE-LINER per the plan-08 trim discipline (mechanics live in `main.md`); pipeline position unchanged.
- **Cross-ref sweep of every `/summarize` reference** (verified inventory this session, to confirm each still aligns after the redesign):
  - `src/CLAUDE.md` — the Workflow chain line (`… /verify → /summarize → /finalize`, correct) + the `/summarize` Command-Details entry (reconcile body, above; keep one-liner).
  - `src/manifest.json:18` — REMOVE the stale flat-file entry (above).
  - `scripts/emitters/claude.py:51` — ADD `"summarize"` to `_PROMOTED` (above).
  - `src/devforge/storage-rules.md:156` — `summarize → creates specs/NNN-name/summary.md (PR-ready feature summary)` (confirm still accurate; no change expected — the artifact path is unchanged).
  - `src/devforge/lib/_verify/_report.py:296,452` — `/verify`'s next-step pointers to `/summarize` (`:296` "run `/summarize` then `/finalize`"; `:452` "`/summarize` → `/finalize`") — confirm accurate; NO change (this is the live producer reference into `/summarize`).
  - `src/_pending/commands/finalize.md:47-50` — `/finalize`'s warning if `specs/[feature]/summary.md` is missing — confirm; NO change here (`/finalize` is plan 25; it is the downstream consumer of `/summarize`'s output).
  - `src/_pending/commands/execute-task.md:404` + `src/_pending/commands/_multi-task-continuation.md:60` — next-step chain pointers in STALE pre-pivot drafts; leave UNTOUCHED (they are superseded drafts, not live).
- **Install-ride verification** (mirror how plans 10/11/20/22 describe their install-ride checks): run `install.sh <tmp-target>` and confirm `summarize command: yes (folder, N references)` (N = the reference-file count from Phase 3, auto-globbed by the emitter), **0 `{{` placeholder leaks** in the emitted command, and an **executable `summarize_helper`** installed at `.devforge/lib/summarize_helper`.
- **Execution:** the `_PROMOTED` edit is a one-line Python tuple change (python-engineer → python-reviewer — confirm the emit still passes `tests/scripts/`); the deletion + the manifest removal + all markdown reconciliation via instruction-author → instruction-reviewer; claude-code-guide consulted for the emitter/install behavior. Add a `CHANGELOG.md` entry + the repo-root `CLAUDE.md` active-plans entry for plan 24.

#### Verify

```bash
# summarize promoted in the emitter:
grep -n "summarize" scripts/emitters/claude.py   # expect: "summarize" in _PROMOTED
# stale flat-file manifest entry removed (folder layout is _PROMOTED-handled):
grep -n "src/commands/summarize.md" src/manifest.json   # expect: NO match (entry removed; would break update.sh otherwise)
grep -n "src/commands/review.md" src/manifest.json   # expect: NO match (stale /review flat-file entry also removed — plan-22-flagged)
# stale draft deleted, no live consumer:
ls src/_pending/commands/summarize.md 2>/dev/null   # expect: absent
grep -rn "_pending/commands/summarize" src/ scripts/ install.sh   # expect: no live consumer
# every /summarize reference still aligns (no dangling), excluding helper/internal hits:
grep -rn "/summarize\|summary\.md" src/ | grep -v "summarize_helper\|_summarize/"   # read: only the inventoried, still-accurate references
# install ride:
#   install.sh <tmp> reports: summarize command: yes (folder, N references); 0 '{{' leaks; .devforge/lib/summarize_helper executable
python -m pytest tests/scripts/   # expect: green (emit still works with summarize added)
```

DoD: `summarize` is in `_PROMOTED` (so it emits/installs); the stale `src/commands/summarize.md` flat-file entry is removed from `src/manifest.json:18` (so `update.sh` does not sync a non-existent source); the stale `src/_pending/commands/summarize.md` is deleted with no live consumer; the `src/CLAUDE.md` Command-Details body reconciles to the redesigned command (pipeline position + Workflow chain unchanged); the cross-ref sweep is clean (every inventoried `/summarize` reference still accurate; the `_verify/_report.py:296,452` producer pointers + the `finalize.md:47-50` consumer gate honored); the install ride shows `summarize command: yes` with N references, 0 `{{` leaks, and an executable helper; `CHANGELOG.md` + repo-root `CLAUDE.md` updated; author→reviewer + python→reviewer + claude-code-guide loops applied.

### Phase 5 — testForge20 e2e — ✅ VALIDATED 2026-06-18

**Validated outcome (2026-06-18):** the e2e passed. `/summarize` was surgically delivered into testForge20 (a wrapper-mode project, `source_root = db-cse-ui-strata`) without a reinstall — `cp` the `_summarize/` helper + `summarize_helper{,.py}` launchers into `.devforge/lib/`, and the command emitted via the real emitter (`--only summarize`) to scratch then copied into `.claude/commands/`. Running `/summarize` on feature `001-catalog-tab-order` (spec at `**Status**: Complete`) wrote `specs/001-catalog-tab-order/summary.md` with all six sections populated from the real artifacts. Observed:

- **AC status taken verbatim from `verification.md` (D3)** — all 12 ACs (AC-1…AC-12) reproduced with their exact statuses, preserving the subtle `PASS (code)` vs plain `PASS` distinction (not re-derived from the spec, not homogenized).
- **Wrapper-mode source changes included (validates the Phase 3 `--install-root` fix)** — the Files-changed section showed `2 files changed, 296 insertions(+), 1 deletion(-)` for the source repo `db-cse-ui-strata`, grouped under `packages/pkg-cse-catalog/`.
- **No verdict rendered (D1)** — the summary references `APPROVED (per /verify)` but renders none of its own.
- The Deviations section correctly surfaced a real deviation (the scoped per-task verification / monorepo `TS18003` PACKAGE_STACKS gap), from the task completion notes.
- A `[WIP] Feature summary: 001-catalog-tab-order` commit landed (D6); the run is read-only on the spec (D4).

**Objective:** the repo's standard manual e2e gate — confirm `/summarize` works end to end on a real feature that finished `/implement` + `/review` + `/verify` (APPROVED).

- Re-install the forge into testForge20 (so the new `/summarize` source is emitted) and run `/summarize` over a feature whose spec `/verify` flipped to `Complete`.
- **Success looks like:** `specs/[feature]/summary.md` is written; the sections (What was built / Changes / Files changed / Key decisions / Deviations / Acceptance criteria) are populated from the real artifacts (spec, plan, task `## Completion Notes`, git, `verification.md`); the AC status matches `verification.md` (NOT re-derived from the spec); wrapper-mode source changes are included when `SOURCE_ROOT != "."`; a re-run idempotently overwrites `summary.md`; NO agent is dispatched and NO verdict is rendered.
- Confirm the install ride (can be checked now): `summarize command: yes (folder, N references)`, 0 `{{` leaks, executable helper.
- Mark DONE only after user sign-off.

#### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# Observe during the /summarize run:
#   - preflight gates the setup chain + the spec **Status**: Complete gate (stops with "run /verify first" if not Complete).
#   - gather-change-data computes the assembled merge-base..HEAD file list (via _shared) + git diff --stat totals.
#   - read-verification pulls the AC status table + verdict from verification.md (AC status NOT re-derived from spec).
#   - parse-completion-notes reads each task's ## Completion Notes for files/deviations.
#   - the summary prose is composed INLINE (no agent dispatch, no verdict).
#   - summary.md is written; the Deviations section is omitted when no task deviated.
#   - wrapper-mode source changes appear when SOURCE_ROOT != ".".
#   - a second /summarize run overwrites summary.md (idempotent).
```

DoD: e2e confirms `/summarize` over a real `/implement`+`/review`+`/verify`(APPROVED)-finished feature writes a populated `summary.md` synthesized from the real artifacts, takes AC status from `verification.md` (not the spec), includes wrapper-mode source changes when `SOURCE_ROOT != "."`, dispatches no agent / renders no verdict, and overwrites idempotently on re-run; user-driven sign-off.

## Decisions (settled — flip any during review)

### D1 — `/summarize` is SYNTHESIS, orchestrator-inline, agent-free; NO finder/refutation/verdict

`/summarize` composes the PR-ready narrative inline in `main.md` from structured helper inputs — there is NO agent dispatch (no tech-writer), NO finder ensemble, NO refutation engine, and NO verdict. It is a 1-page section-templated synthesis; the stale draft already does it inline (`src/_pending/commands/summarize.md:36-74`), and consistency-over-invention keeps it that way. (User-confirmed.)

### D2 — Reuse `_shared/feature_scope.py` (no Phase 0 extraction); +/- stats via `git diff --stat`; NOT the refutation engine

`/summarize` imports `resolve_feature_scope` from `_shared/feature_scope.py` (which already exists — plan 22 Phase 0 created it; verified via glob) with `heading_label="Summary Scope"`. There is NO Phase 0 extraction in this plan — the module is already shared. The resolver is `--name-only`-based, so the +/- insertion/deletion totals come from a small `git diff --stat <base>..HEAD` call. `/summarize` does NOT reuse the `_shared` refutation engine (`findings_schema`/`_consume`/`_validate`/`_consensus`/`_verify`) — it is not a finder ensemble. (D1 corollary.)

### D3 — Consume `verification.md` for authoritative AC status + the spec Complete gate; do NOT re-derive ACs

`/summarize` parses `/verify`'s `specs/[feature]/verification.md` for the AUTHORITATIVE AC status (the `| AC-N | <status> | <evidence> |` table, `src/commands/verify/references/report-format.md:33-35`) — it does NOT re-derive AC status from the spec, because `/verify` already proved each AC. It reads the spec `**Status**: Complete` as its PHASE-0 gate (STOP → "run /verify first" if not `Complete`). The typed `verify-handoff.json`/`summarize-handoff.json` is DEFERRED (OQ-1, mirroring plan 22's OQ-2 lean). NO change to `/verify`. (User-confirmed.)

### D4 — `/summarize` does NOT mutate its inputs

`/summarize` writes ONLY `specs/[feature]/summary.md`; it touches none of its inputs (spec, plan, task files, `verification.md`, git history). This is the explicit CONTRAST with plan 22's D4 (where `/verify` writes back to its input — it flips the spec `**Status**:`). `/summarize` is read-only-on-inputs by design, like `/review` and `/audit`; unlike `/verify`.

### D5 — Wrapper-mode aware

`gather-change-data` gathers source-repo changes (`git -C $SOURCE_ROOT …`) when `SOURCE_ROOT != "."`, so wrapper-mode installs (specs/docs in the wrapper root, code in the source repo) get both change sets in the summary. The `source_root` is resolved by `_preflight` from `CLAUDE.md` (mirror `_verify/_preflight.py:70,84,129-149`).

### D6 — Idempotent overwrite + a `[WIP]` commit

`/summarize` overwrites `summary.md` on every run (idempotent — the draft's rule 5, `summarize.md:101`) and makes a `[WIP] Feature summary: NNN-…` commit per the Commit Convention in `src/CLAUDE.md` (WIP commits are squashed later by `/finalize`).

### D7 — Scope = `/summarize` only; `/finalize` = sibling plan 25

This plan builds `/summarize` ONLY. `/finalize` (squash WIP commits + tech-writer feature docs + wrapper-mode source squash) is a separate sibling plan, "plan 25". `/summarize` POINTS to `/finalize` as its next-step but does not build it. (User-confirmed.)

### D8 — `/summarize` is STATELESS (no run-state file)

`/summarize` writes NO run-state: no `specs/[feature]/summarize-state.json`, no `_state.py` module, no `check-status-and-flip` verb. It is a single orchestrator pass with NO agent dispatch (a D1 corollary), so there is no expensive multi-phase work to resume; the `summary.md` overwrite is itself idempotent (D6). `/review`/`/verify` carry run-state only for the finder/refuter-dispatch resumability that `/summarize` structurally lacks — copying it here would cargo-cult the form without the function. (Was OQ-1; user-confirmed.)

### D9 — Key decisions come from `plan.md`, NOT `plan-handoff.json`

`read-plan-decisions` parses `plan.md`'s key-decisions section (verify the exact heading text at the Phase 2 build against `/plan`'s real output — the stale draft calls it a "key decisions table", `summarize.md:60`). It does NOT read `specs/[feature]/plan-handoff.json`'s `breakdown_seeds.decisions`: that handoff is a PRODUCER-ONLY contract whose documented consumer is `/breakdown` (repo-root CLAUDE.md helper-locations table — "PRODUCER-ONLY — `/breakdown` consumer"), so a second consumer would couple `/summarize` to a `/breakdown`-owned schema. `plan.md` is the stable human-authored decisions document, which fits a human-prose synthesizer. **Acknowledged tension** (flag per consistency-over-invention): this cuts against the repo's general direction toward typed handoffs over markdown-scraping (plan 1.5) — accepted here because the cross-command coupling cost outweighs the parse-robustness gain for this command. (Was OQ-2; user-confirmed.)

## Open questions (OQ-N)

(OQ-1/OQ-2 in the original draft — run-state and key-decisions-source — were RESOLVED into D8 and D9; the two below are renumbered.)

- **OQ-1 — typed `summarize-handoff.json` for `/finalize`.** DEFERRED (mirroring plan 22's OQ-2 lean). Build the producer-side typed handoff when `/finalize` is refactored to consume it ("consumer obeys producer", plan 25). For now the spec `**Status**: Complete` flip + the existence of `summary.md` are the contract (`finalize.md:47-50` already gates on `summary.md` existence).
- **OQ-2 — keep the draft's "already-finalized" warning?** The draft warns when no `[WIP]`/`[checkpoint]` commits exist and a clean `feat(*)` commit is present, that the summary will reflect current state not task-by-task history (`summarize.md:17`). **Lean KEEP**, re-pointed to the live `[WIP]`/`[checkpoint]` commit conventions (Commit Convention in `src/CLAUDE.md`). Resolve at the Phase 3 build (it is a `main.md` wording decision).

## Out of scope (do NOT plan here)

- **Building `/finalize`** (sibling plan 25 — squash WIP commits + tech-writer feature docs + wrapper-mode source squash). `/summarize` POINTS to it as a next-step but does not build it (D7).
- **Changing `/verify`, `/review`, `/implement`, or `_shared/` behavior.** `/summarize` consumes `verification.md` + reuses `_shared/feature_scope.py` unchanged; it adds no Phase 0 extraction and no `_verify`/`_review`/`_implement` edit.
- **A finder ensemble / refutation pass / verdict in `/summarize`** (D1 — it is pure synthesis; the `_shared` refutation engine is NOT reused here).
- **Reshaping the plan-15 agent roster.** No agent is dispatched by `/summarize`; the roster is untouched.
- **The typed `summarize-handoff.json` producer** (OQ-1, deferred — built when `/finalize` consumes it, plan 25).

## Context for next session

- `/summarize` is the pipeline step AFTER `/verify` approves and BEFORE `/finalize` (`… /implement → /review → /verify → /summarize → /finalize`, verified `src/CLAUDE.md` Workflow). Its defining job: **the PR-ready human-facing feature narrative** — what was built (user terms), change stats, key decisions, deviations, and AC status — synthesized ORCHESTRATOR-INLINE (D1, agent-free) from the now-complete feature record. It writes `specs/[feature]/summary.md` idempotently and mutates none of its inputs (D4). See the three-command invariant table in `## Command mission`.
- **Single reuse (D2):** `/summarize` imports `resolve_feature_scope` from `_shared/feature_scope.py` (created by plan 22 Phase 0 — ALREADY EXISTS; NO Phase 0 extraction in this plan) with `heading_label="Summary Scope"`, and adds a small `git diff --stat <base>..HEAD` for the +/- totals (the resolver is `--name-only`-based). `/summarize` does NOT reuse the `_shared` refutation engine (it is not a finder ensemble).
- **Consume `verification.md` (D3):** `/summarize` parses `/verify`'s `specs/[feature]/verification.md` for the AUTHORITATIVE AC status (`| AC-N | <status> | <evidence> |`, `report-format.md:33-35`; status ∈ `{PASS, FAIL, PARTIAL, MANUAL, PASS (code), FAIL (code), PARTIAL (code), UNVERIFIED}`) — it does NOT re-derive ACs from the spec. It gates on the spec `**Status**: Complete` (STOP → "run /verify first"). NO `/verify` change. The typed handoff is deferred (OQ-1).
- **`_summarize/` mirrors `_verify/` but LEANER** (no verdict, no finder ensemble, no bug-filing): `_cli.py` registry, `_preflight.py` (setup-chain + spec-Complete gate + source_root/wrapper-mode from `CLAUDE.md`, `.devforge/` paths), `_changes.py` (`gather-change-data`), `_inputs.py` (`read-verification`, `parse-completion-notes`, `read-plan-decisions`), optional `_report.py`. Launchers `summarize_helper{,.py}` mirror `verify_helper{,.py}` (`verify_helper.py:16-20`). Scratch literal `${TMPDIR:-/tmp}/forge-summarize` (NOT forge-verify/forge-review/forge-audit).
- **The stale draft's audit (`## What's stale in the draft`):** `.claude/project-config.json` → `.devforge/project-config.json`; hand-read `DEFAULT_BRANCH`/`SOURCE_ROOT` → preflight `source_root` from `CLAUDE.md` + `_shared` resolver; manual `git diff --stat`/`git log` gathering → `_shared` resolver + a small `git diff --stat` for totals; re-derived ACs → consume `verification.md`'s table (D3); structural gap (no `_summarize/`, no launcher, absent from `_PROMOTED` `scripts/emitters/claude.py:51`, stale manifest entry `src/manifest.json:18`). STILL VALID + kept: the `## Completion Notes` task-file read (`/implement` fills it via `_cmds_complete.py:293`).
- **4 build phases + the e2e gate (NO Phase 0):** 1 `_summarize/` scaffold + preflight + spec-Complete gate → 2 input/gather verbs (`gather-change-data` reusing `_shared`, `read-verification`, `parse-completion-notes`, `read-plan-decisions`) → 3 main.md + references (6 runtime PHASES, orchestrator-inline synthesis, `forge-summarize` scratch) → 4 wire-in (add `summarize` to `_PROMOTED` at `claude.py:51`; delete the stale draft; remove the stale `manifest.json:18` flat-file entry; reconcile `src/CLAUDE.md`; cross-ref sweep; install ride) → 5 testForge20 e2e (USER-DRIVEN HARD GATE).
- **2 OQs:** OQ-1 (typed `summarize-handoff.json`; deferred to plan 25), OQ-2 (keep the "already-finalized" warning; lean keep). The original run-state and key-decisions OQs are now D8 (stateless) + D9 (`plan.md`).
- **Deliberate departure recorded (D4):** `/summarize` is read-only-on-inputs — the explicit contrast with `/verify`'s D4 (which writes back to the spec). `/summarize` writes only `summary.md`.
- **Verified file:line facts (this session):** `_PROMOTED` lacks `summarize` (`scripts/emitters/claude.py:51`, ends `…, "audit", "review", "verify")`); stale flat-file manifest entry (`src/manifest.json:18`); `_shared/feature_scope.py` exists with `resolve_feature_scope` (`:298`) + `_render_scope_block(heading_label="Review Scope")` (`:237,303`); `verification.md` AC table + status enum + verdict (`src/commands/verify/references/report-format.md:14,33-35,71-73`) produced by `verify_helper render-report` (`src/devforge/lib/_verify/_report.py:101`); `/verify`'s next-step pointers to `/summarize` (`_verify/_report.py:296,452`); the `## Completion Notes` fill (`src/devforge/lib/_implement/_cmds_complete.py:293`, heading regex `:124`); source_root resolution (`src/devforge/lib/_verify/_preflight.py:70,84,129-149`); spec status enum (`src/devforge/lib/_specify/_schema.py:32-34`); AC checkbox shape (`tests/lib/fixtures/specify-sample-migration.md:31`); the `summarize → summary.md` storage line (`src/devforge/storage-rules.md:156`); `/finalize`'s `summary.md` gate (`src/_pending/commands/finalize.md:47-50`); the launcher shim shape (`src/devforge/lib/verify_helper.py:16-20`); the `verify/main.md` frontmatter the new `main.md` mirrors (`src/commands/verify/main.md:1-6`); the `/summarize` Command-Details one-liner + Workflow chain (`src/CLAUDE.md`).

## When resuming work

1. **Re-read this plan in full** + the live files it grounds against: `src/_pending/commands/summarize.md` (the stale draft being replaced), `src/commands/verify/main.md` + `src/commands/verify/references/report-format.md` + `src/devforge/lib/_verify/{_cli,_preflight,_report}.py` (the structural model + the `verification.md` producer being consumed), `src/devforge/lib/_shared/feature_scope.py` (the resolver being reused, NOT extracted), `src/devforge/lib/_implement/_cmds_complete.py` (the `## Completion Notes` fill the change-data parser reads), `src/devforge/lib/_specify/_schema.py` (the spec status enum the gate checks), `src/devforge/storage-rules.md` (the `summary.md` storage line), `src/_pending/commands/finalize.md` (the downstream consumer of `summary.md` — plan 25), and `src/CLAUDE.md` (the `/summarize` entry + Workflow chain the wire-in reconciles). The `main.md`/helper line numbers above are pre-edit; re-read each file from scratch after a phase edits it.
2. **No blocking OQ before Phase 1** — OQ-1 (typed handoff) is deferred to plan 25; OQ-2 (already-finalized warning) resolves at Phase 3. The original run-state and key-decisions-source OQs are now settled — D8 (stateless) and D9 (`plan.md`). Execute Phase 1 first.
3. **Execute Phases 1→5 in order** (each green before the next). Phase 1 is the scaffold + gate; Phase 2 builds the input verbs; Phase 3 writes `main.md` + the reference; Phase 4 wires it into the emitter + reconciles docs; Phase 5 is the user-driven HARD GATE. There is NO Phase 0 — `_shared/feature_scope.py` already exists, so do not extract anything.
4. Route every Python helper change through **python-engineer → python-reviewer** with a test written + run in the same turn (round-trip REAL producer output — a real `CLAUDE.md` + a real `spec.md` in both Complete/not-Complete states for the gate, a real `verify_helper render-report`-rendered `verification.md` for `read-verification`, a real `implement_helper mark-complete`-filled task file for `parse-completion-notes`, a real git scope for `gather-change-data` — not hand-faked fixtures); route every command/spec/reference/CLAUDE.md/plan markdown edit through **instruction-author → instruction-reviewer**; verify command frontmatter (`disable-model-invocation`, `argument-hint`) + the emitter/install behavior via the **claude-code-guide** agent BEFORE writing `main.md` (Phase 3). This plan file itself is a repo-root plan and does NOT ship into `.claude/`, so it needs no claude-code-guide; `main.md` (Phase 3) DOES ship and DOES.
5. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(summarize): live PR-ready feature-summary command on the shared scope resolver`, `feat(summarize): change-data + verification.md consume verbs`, `chore(commands): promote summarize + drop stale flat-file manifest entry`).

## Related plans

- `22-VERIFY-COMMAND-REDESIGN-PLAN.md` — the STRUCTURAL MODEL for this plan (the `_verify/` subpackage shape, the `_preflight` setup-chain + source-root resolution, the per-command scratch-chain + helper/orchestrator split) AND the upstream producer of `specs/[feature]/verification.md` (PHASE 2 reads its AC status + verdict) + the spec `**Status**: Complete` flip `/summarize` gates on (PHASE 0). Plan 22 Phase 0 created `_shared/feature_scope.py`, which this plan reuses without re-extracting.
- `20-REVIEW-COMMAND-REDESIGN-PLAN.md` — the `_review/` subpackage shape + the `_shared/` extraction precedent + the producer of `specs/[feature]/review.md` (which `/verify` folds into the verdict `/summarize` then reads from `verification.md`).
- `17-IMPLEMENT-PER-TASK-PANEL-PLAN.md` / `07-EXECUTE-TASK-REDESIGN-PLAN.md` — the `/implement` command that fills each task's `## Completion Notes` (via `implement_helper mark-complete`, `_cmds_complete.py:293`) that `/summarize`'s `parse-completion-notes` reads.
- `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` — produces the task list (`specs/[feature]/tasks/`) + `plan-handoff.json` (whose `breakdown_seeds.decisions` was the REJECTED alternate key-decisions source — D9 chose `plan.md` to avoid a second consumer of a `/breakdown`-owned contract).
- The pending sibling `/finalize` (`src/_pending/commands/finalize.md`) is the DOWNSTREAM consumer of `summary.md` (it warns when `summary.md` is missing, `finalize.md:47-50`) — its redesign is the sibling follow-on **plan 25** (D7).
