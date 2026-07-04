# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- feat(gitignore,finalize): make a consumer install's git tree CLEAN after a full pipeline cycle (`49-DEVFORGE-RUNTIME-STATE-DISPOSITION-PLAN.md`, Phases 1–5, 2026-07-04). Previously every cycle left `.devforge/` runtime state dirty (the maintainer hand-committed it), because `.devforge/` mixed three storage classes under one dir with no per-file git disposition AND the one session-state ignore rule pointed at a DEAD path (`.claude/session-state.md`, pre-plan-22) that the `union_lines` merge propagated from the forge repo's own root `.gitignore` into every consumer. Adds a 3-class disposition (VERSIONED / EPHEMERAL / FEATURE-SCOPED): EPHEMERAL files (`session-state.md`, `*-state.json`, `*-report.json`, `discover-scope.json`, pointers, logs, `*.lock`) are gitignored via a NEW dedicated `src/files/devforge.gitignore` template (merged by a `manifest.json` `mergeFiles[".gitignore"].templateSource` + a new `update.sh` `merge_src()` source resolver + an `install.sh` inline union for fresh installs), plus a fail-soft / tracked-only / install-repo-only `git rm --cached` migration in `update.sh` that also deletes the dead line; VERSIONED `memory.md` + `spec-stamps.jsonl` deltas fold into the `/finalize` PHASE-2 safety-net commit so they ride the squash (a deliberate narrow file-level revisit of plan 33/37's blanket runtime-state exclusion, back-pointer inline). `src/devforge/storage-rules.md` documents the 3-class model + the scratch-vs-record trap (`.devforge/research-report.json` ≠ `research/<slug>/handoff.json`). Reuse-only (no new helper); install-repo-only / wrapper-safe by construction. The migration lives in a shared `scripts/devforge-state-migrate.sh` sourced by BOTH `install.sh` and `update.sh` (so a re-install onto an already-forge'd target also cleans up). 50 scratch tests green; `finalize/main.md` edit `instruction-reviewer`-clean. Phase 6 (consumer/testForge20 pipeline e2e) is the remaining user-driven gate.

## [2.0.4] - 2026-06-30

### Added
- feat(breakdown): add a per-task **implementability** sub-question to the `/breakdown` Phase-2 mandatory architect consult (`47-BREAKDOWN-IMPLEMENTABILITY-SUBQUESTION-PLAN.md`, 2026-06-30). The consult validated task STRUCTURE (atomicity / dependency-ordering / contract-chain) but never asked whether the assigned engineer could implement a task without guessing a decision the plan never made — so an underspecified intent (a missing input the steps assume, an unstated choice between two valid implementations, a done-condition more than one diff could satisfy) was caught only downstream at the per-task review panel, `/verify`, or the human approval gate, after the breakdown was written. Adds a 4th always-asked sub-question on the consult that already runs every breakdown, by the right specialist (the architect), before any task file is written. Scope is intent-completeness, with an explicit anti-false-positive carve-out: a task fully determined by its contracts + the spec/plan/constitution/docs context the implementer also reads is NOT a finding (it is not a prose-style/verbosity judgment). Findings ride the existing revise-before-write loop; a plan-level gap (a decision `/plan` should have made) escalates to the human. NO new agent, helper, forcing-function, or provenance-schema change — pure prose to the already-emitted command (the three in-file 3-item enumerations of the sub-questions updated to 4-item). Why a 4th sub-question and not a separate prose-reviewer or a mechanical gate: clarity is a judgment call (a forcing-function would false-positive on terse-but-determined tasks), and a dedicated per-task pass is heavyweight for a problem the downstream panel + `/verify` already backstop. Built behind instruction-author → instruction-reviewer (2 findings applied) + claude-code-guide (convention-clean). testForge20 e2e is the remaining user-driven gate.

### Changed
- Template version: 2.0.3 → 2.0.4

## [2.0.3] - 2026-06-29

### Added
- feat(handoff,plan): caveat-propagate shape-only recommendation provenance (`45-SEAM-TRUST-PROPAGATION-PLAN.md` Step 2 / Seam E, 2026-06-27). A design critique of the framework's own gate architecture found handoff seams where one stage validates a value for SHAPE only and a downstream stage scopes its own work by trusting that value as correctness. Seam E: `/plan` silently treated the research handoff's `recommended_approach` as authoritative even though research only token-overlap-validated it. Adds `PlanSeeds.correctness_vetted` (default `False`) to the research→plan handoff carrier (`_research/handoff_schema.py`) and renders an adjacent "shape-checked (token-overlap), NOT correctness-vetted" caveat in `plan_helper`'s research-seeds output — deterministic, no model call in the decision path. Back-compat proven as the honest pair: old JSON lacking the field parses to the default; current-producer output round-trips stably (no impossible byte-identity claim). 173 tests through the real producer/parser.
- docs: Golden Regression Catalog at repo root (`REGRESSION-ANCHORS.md`, plan 45 off-critical-path deliverable). Pins three fixed meta-bugs (orphaned design-auditor, skippable design-manifest trigger, import-handoff dedup) to their guarding tests, and records the tier-1.5 "probe misroute" as a rejected phantom (no failing-state-then-fix in git). A registry so a future session can tell a real regression anchor from a phantom.

### Fixed
- fix(shared): tolerate decorated finding labels in the `_consume` parser (`46-SHARED-CONSUME-LABEL-TOLERANCE-PLAN.md`, 2026-06-29). Finder/refuter agents wrote `## Finding N` fields with dash-bullet labels (`- Severity:`), bold labels (`**Severity**:`), or backtick-wrapped File/Line values that the bare-label regexes missed, so whole findings were SILENTLY dropped — `/review` rendered a false findings-empty report and `/verify` folded it into a wrongly-APPROVED verdict. The shared refutation/finding engine, so `/audit` and `/grill` hit the same gap. Fixed at the single chokepoint `_shared/_consume.py`: a fence-aware `_normalize_label_lines` pass rewrites decorated known-label lines to bare form and backtick-strips the six single-line field values before the existing regexes run (the boolean `in_fence` toggle is the markdown-correct fence model); a `_strip_inline_code` balanced-backtick stripper; and `_parse_finding_block` now extracts `why`/`remediation` from the post-evidence tail so a field-looking line inside the evidence block is no longer mis-picked. `_validate.py` untouched (consume is the sole producer; the `file_missing` symptom disappears). 37 new tests; full `_shared`+`_audit`+`_review`+`_grill` suite 1914 pass, zero regressions. A residual malformed-markdown edge (a bare ` ``` ` inside an evidence body followed by a decorated label) is documented as cosmetic-only (why/remediation prose, never a drop or wrong verdict). Discovered in a consumer install (mintEnvoy) across three `/review` rounds. Built behind instruction-reviewer + python-engineer→python-reviewer loops.
- fix(design-tokens): re-anchor `verify-design-tokens` Check 5 spacing scope on `reference.html` (`45-SEAM-TRUST-PROPAGATION-PLAN.md` Step 3 / Seam A, 2026-06-27). Check 5's hardcoded-spacing sub-check was gated by `match_refs` (the LLM-authored MATCH disposition), so a mistagged-DEVIATE element silently escaped the only hardcoded-spacing check (a self-referential trust seam — the gate trusted the same LLM output it was meant to police; confirmed by a live trace, partial-by-axis: spacing-only, color is re-covered by the manifest-independent Check 1). Now scopes the spacing sub-check on the `data-ref`s present in `design/reference.html` (stdlib `html.parser`, which the LLM cannot mistag for this purpose) minus DEVIATE-with-recorded-reason exemptions; falls back byte-identically to `match_refs` when `reference.html` is absent/unreadable/anchorless. Checks 1–4 and Check 5's color sub-check unchanged. 168 design-token tests + a 4-case live trace.
- fix(update): keep the constitution-drift check from aborting `update.sh` under `set -e`. `forge_check_constitution_drift` captured the helper exit with a bare `var="$(helper ...)"; exit=$?` pair; under `update.sh`'s `set -euo pipefail` an assignment whose command substitution exits non-zero aborts the script — and exit 2 is the drift-detected case the check exists to handle, so `update.sh` died silently at the check on any already-drifted project (clean projects exit 0 and passed, hiding it). Captures the exit via the `|| var=$?` idiom (pre-initialized to 0) at both verb call sites so the failure stays inside an OR-list. `install.sh` has no `set -e` and was unaffected; the shared `scripts/constitution-drift-check.sh` fix covers both callers.

### Changed
- Template version: 2.0.2 → 2.0.3

## [2.0.2] - 2026-06-26

### Added
- feat(specify,design-fidelity): declare-and-warn for non-file design sources (`43-NON-FILE-DESIGN-SOURCE-FIDELITY-PLAN.md`, 2026-06-25). Plan 40's design-fidelity apparatus is keyed end-to-end on a local `design/reference.html` (parsed at `/breakdown` PHASE 2.5, token-checked at `/implement`, rendered-diffed at `/review`), so a team whose design source is a Figma selection / hosted URL / screenshot got ZERO fidelity enforcement, SILENTLY — no manifest, every gate skips clean, no operator signal. **Ratified Option 4 + Option 1 hybrid:** a typed per-feature `design_source` declaration (the declare-and-warn precursor) with convert-to-reference as the standing answer (export the non-file source to `design/reference.html` so the existing apparatus applies unchanged); NO new enforcement backend (Figma-API / URL-render declined). **Declaration home (OQ-1) = spec.md frontmatter (per-feature):** `/specify` Phase 4 captures the source via a single-line AskUserQuestion (4 schemes — `html` / `figma` / `screenshot` / `none`, default `none`; Figma/Screenshot targets via a next-turn prose follow-up) and writes it with a new `specify_helper set-design-source --value <v>` setter; `render_spec` emits a `**Design source**:` frontmatter line on every spec. **Classify/WARN helper:** new `design_helper check-design-source --spec <path> --workspace-root <path>` (`_design/_source.py` — `parse_design_source` + the verb) emits a loud NON-BLOCKING WARN (stderr, exit 0) when a non-file source is declared but no enforceable `design/reference.html` exists, naming the convert-to-reference remedy. Producer and consumer agree on the `scheme:target` grammar (first-colon split preserves Figma URLs; `none` is a bare sentinel — `none:` rejected both sides). **Consumer wire-in (Step 1C):** `/breakdown` PHASE 2.5's reference-absent branch now runs `check-design-source` on the spec and surfaces the WARN verbatim before the (still non-blocking) skip — landed after plan 42 reshaped that detect step; a genuine non-UI feature still skips silently. Built behind python-engineer→python-reviewer (design + specify suites green; 1003-test cross-suite sweep clean) + instruction-author→instruction-reviewer + claude-code-guide loops. Consumer e2e deferred by maintainer (not blocking — build-verified + end-to-end smoke clean).
- feat(update,install,constitution): warn on constitution + forcing-function drift at update/install time (`44-CONSTITUTION-DRIFT-WIRING-PLAN.md`, 2026-06-25). Closes a silent staleness class: the constitution holds framework-owned universal law (§3.5–§3.8, §4, §6) and the forcing-functions config inside user-owned, presence-guarded files (`constitution.md`, `.devforge/constitute.json`) that `install.sh` places once and `update.sh` never touched — so when the framework adds new law or a new detector (e.g. plan 40's `design_token_provenance`), every already-installed project's enforcement code ships but stays inert, even at equal version. The drift detector (`forge-internal:verify-universal-defaults`, built + validated in the 18-May cycle) already existed but ran on no consumer. **Wiring (WARN-ONLY, zero mutation):** a shared `scripts/constitution-drift-check.sh` snippet (`forge_check_constitution_drift`) sourced by `update.sh` (before the equal-version bail, so a same-version-but-drifted install is still caught) and `install.sh`'s brownfield "leaving as-is" branch runs that verb plus a **new sibling verb** `constitute_helper forge-internal:verify-forcing-function-keys` (diffs consumer `constitute.json.forcing_functions` keys vs the canonical `_schema.py::FORCING_FUNCTION_RULES` frozenset; exit 0 clean / 2 drift / 3 not-yet-constituted / 1 corrupt) against an already-constituted target, then prints a bounded warning naming the drifted universal sections + missing forcing-function rules and tells the user to re-run `/constitute`. Both checks fail-soft (any error prints "skipped", never blocks install/update) and greenfield-silent-skip (no `.devforge/constitute.json` ⇒ nothing to drift). It NEVER edits `constitution.md` or `constitute.json` — the human applies the refresh via `/constitute` re-synthesis (auto-merge rejected: section numbers collide across template generations). Uses the freshly-shipped TEMPLATE helper, not the consumer's still-stale installed one. Discovered auditing whether the 2.0.1 update fully landed in a consumer install (mintEnvoy) — code landed clean, the constitution + forcing-functions config did not, and nothing surfaced the gap. The deeper structural fix (Option C: split universal law into a framework-owned file `update.sh` overwrites) is deferred — this is the cheap safety net. Built behind python-engineer→python-reviewer (15 verb tests + 220 `_constitute` suite green). testForge20 + mintEnvoy e2e is the remaining user-driven hard gate.
- feat(breakdown,design-fidelity): mechanically guarantee the design-manifest trigger plan 40's apparatus depends on (`42-DESIGN-MANIFEST-TRIGGER-FORCING-FUNCTION-PLAN.md`, 2026-06-25). Preventive hardening: plan 40 made visual drift gate-blocking through a `specs/[feature]/design-manifest.json` (produced at `/breakdown` PHASE 2.5) that two downstream gates depend on — `/implement`'s static `verify-design-tokens` Check 5 and `/review`'s `design-auditor` dispatch — but the manifest's load-bearing TRIGGER was skippable PROSE with a silent-failure cascade: a skipped PHASE 2.5 wrote tasks + a green `breakdown-handoff.json` with no manifest, after which Check 5 (which globs `specs/*/design-manifest.json` project-wide) either no-ops or checks ANOTHER feature's MATCH refs, and the `design-auditor` dispatch never fires — same shape as the gap plan 38 closed for the agent roster. **WI-1 (mechanical backstop):** new `breakdown_helper verify-manifest-present <tasks-dir>` forcing-function (sibling to `verify-contract-chain` / `verify-ac-coverage` / `verify-agent-roster`; a shared `_validate_manifest_present` predicate composing `_design`'s `validate_manifest` via a single import) asserts `design/reference.html` present ⇒ `design-manifest.json` present-and-valid — wired as the 4th `/breakdown` PHASE 3.5 integrity gate (HARD-halt, NO `## Risk Assessment` bypass) AND folded into `finalize-handoff` as a chokepoint so a poisoned handoff cannot be written. PHASE 2.5's detect step is now a mechanical `test -f design/reference.html` (the producer and the PHASE 3.5 backstop share the same file-existence predicate; D4 Option B — `--scope-only` can't run at intake because no tasks-dir exists yet, and the reference-path literal is already duplicated in PHASE 2.5's `resolve-reference` call). **WI-2 (defense-in-depth):** loud-WARN non-blocking tripwires at `/implement`'s forcing-functions gate site + `/review` PHASE 2.5 surface the legacy/tampered `reference.html`-present-but-manifest-absent case (the PHASE 3.5 gate guards fresh decompositions; the tripwires catch already-decomposed features whose manifest never existed or vanished). No change to plan 40's apparatus — this adds a trigger guarantee, not fidelity logic. Non-FILE design sources (Figma / hosted URL / screenshot) are a tracked non-goal (plan 43). Built behind python-engineer→python-reviewer (296 breakdown tests) + instruction-author→instruction-reviewer + claude-code-guide loops. testForge20 / consumer e2e deferred by maintainer (not blocking — build-verified).

### Fixed
- fix(update,configure): delegate `update.sh` placeholder substitution to the `/configure` renderer. `update.sh` carried its own `{{KEY}}`→`config[KEY]` substituter and read `project-config.json` from the legacy `.claude/` path — both had drifted from the multi-stack `_render.py` renderer (it knew none of the singular↔plural aliases like `LANGUAGE`←`LANGUAGES` or the composed `PACKAGE_STACKS` table, and the config moved to `.devforge/`), so on any install with the current config schema `CLAUDE.md` was skipped for "unresolved placeholders" and agents were mis-substituted. New `configure_helper substitute-file --file <path>` verb makes the renderer the single source of truth; `update.sh` now delegates to it (config path → `.devforge/project-config.json`, `perl` hard-requirement → `python3`, merge gate keys on the verb's exit code instead of a `{{...}}` grep that false-skipped legitimate `{{UPPERCASE}}` passthrough), retires the `CLAUDE.md`-scraping `migrate_project_config` in favour of a `render-config` rebuild from `configure.yaml`, and removes the dead `AGENT_MODEL`→`MODEL_*` migration. The minimal YAML parser's single-quote rejection message is now actionable across all three mirrored copies. (181 `_configure` + 127 `detect_report` pass; `substitute-file` gets a 21-case suite.)
- fix(specify): dedupe duplicate/malformed entries at handoff ingestion. `import-handoff` overwrote the four spec-state buckets (constraints / affected_areas / risks / open_questions) with a handoff's `spec_seeds` lists verbatim; the schema validates each item individually but never across the list, so exact-duplicate and whitespace-variant entries passed validation and landed in committed state with no removal path except a full `reset-state`. Adds a source-level insertion-ordered dedupe (`_dedupe_seeds` + per-section key functions) applied in both research and discover import paths before the converters run (whitespace-normalized identity key, no case-folding so `GET` vs `get` stay distinct; first-occurrence-wins, survivor stored verbatim; `open_questions` deduped upstream of the positional id assignment so ids stay gap-free; per-entry stderr drop log). Re-importing the same handoff is now byte-identical and a dup-carrying handoff lands clean on first import.

## [2.0.1] - 2026-06-24

### Added
- feat(agents,verify): close the "orphaned declaration" class + add a permanent reachability gate (`41-AGENT-EXECUTOR-REACHABILITY-PLAN.md`, 2026-06-24). A declarations→executors survey found three orphan types — type-1 ORPHANED AGENT (named responsible, no command dispatches it), type-2 ORPHANED STEP ("verified at stage Y" but Y doesn't), type-3 ORPHANED FINDING (runs in an ensemble but gates nothing). Three work items (design-auditor was the canonical orphan but is owned by plan 40; the consumer-runtime roster check is plan 38's `verify-agent-roster` — complementary). **WI-1 (type-1):** wired the orphaned `qa-engineer` (a chartered test-writer named only in the `/breakdown` consult-relay list, with no Agent-Assignment row, so no task routed to it) a real executor — a "Dedicated test-authoring / coverage-gap task → qa-engineer" row + rule in `breakdown/main.md` (inline tests stay each engineer's default; a dedicated qa-engineer task is created only on a coverage-gap / test-heavy-AC flag). **WI-2 (type-3):** confirmed Medium-severity non-constitution `/review` findings now gate the `/verify` verdict to NEEDS WORK (they were rendered to the human but never appended to `blockers[]`) — `_verify/_verdict.py` `medium_finding` blocker (never REJECTED; contested Medium does NOT gate; Info advisory); **hygiene stays advisory (plan 34 untouched)** with the plan-34 false-positive regression test as a guard; `report-format.md` + `verify/main.md` PHASE 9 reconciled; 511 `_verify` tests pass. **WI-3 (permanent gate):** a maintainer-side agent-executor-reachability checker — `scripts/lib/agent_reachability.py` + `scripts/verify-agent-reachability.py` CLI + `tests/lib/test_agent_reachability.py` (36 tests) — parses the `src/agents/*.md` roster and every dispatch path (literal `subagent_type:`, the `/breakdown` Agent-Assignment table, and helper ensemble/refuter lists via AST incl. dict keys) and FAILS on an agent with no executor, an unknown assignment, or a hard-fail relay-only agent (`RELAY_ONLY_ALLOWLIST` escape, empty). Live-src green (all 18 roster agents reachable); the pytest test against live `src/` is the permanent gate (no CI in repo). The gate mechanizes type-1 + unknown-agent ONLY — type-2 forward-prose and type-3 finding-inertness stay human review conventions (not silently claimed as covered). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. testForge20 e2e is the remaining user-driven gate.
- feat(design-fidelity): make visual drift from a `design/reference.html` structurally gate-blocking for any frontend task (`40-DESIGN-FIDELITY-FORCING-FUNCTION-PLAN.md`, 2026-06-24). Root-caused from a consumer install whose UI shell drifted from its design reference — the drift was contract-licensed (the spec accepted "semantic equivalence, not pixel-exact"; fidelity was deferred to a `/review` → design-auditor pass that **no command actually dispatched** — `design-auditor` was an orphan agent; hardcoded hex + `var(--token,<literal>)` fallbacks passed `/implement` unchecked). Fix = **two orthogonal gates + a required pre-code disposition manifest** (a runtime compare reads resolved values without provenance so it can't catch token-bypass; a static grep can't catch right-token-wrong-spacing — neither is redundant). **Contract:** persisted universal constitution section **§3.8 Design Fidelity** (`*Backed by* constitute_helper verify-design-tokens`; narrow reference-present⇒1:1 carve-out, markup rebuilt freely) + the `design-auditor.md` Rule 5 carve-out. **Manifest:** `src/devforge/lib/_design/` (`design_helper`) produces `specs/[feature]/design-manifest.json` at `/breakdown` PHASE 2.5 (conditional on a `design/reference.html`; `data-ref`-keyed; 4-way taxonomy MATCH / DEFER-EMPTY / STATIC-PLACEHOLDER / DEVIATE) — an unclassified element or unresolvable value HALTS intake and escalates before any task is written. **Static provenance gate:** new `_constitute/_forcing_functions/_design_tokens/` + `constitute_helper verify-design-tokens` (no hardcoded color/border/spacing literals, no `var(--x,<literal>)` fallbacks, undefined-token-fails-loud, token-binding on MATCH elements, `:hover`+`:focus-visible`) at `/implement`'s per-task forcing-functions gate + the opt-in pre-commit hook; global config is `{enabled, token_source_css}` only, Check 5 globs the per-feature manifests at runtime; offered by `/constitute` Section 3.5 (`design_token_provenance` rule, UI projects). **Runtime conformance gate:** `design-auditor` re-equipped (hybrid computed-style + scoped-screenshot mechanism, structured `CHROME_MCP_AVAILABLE` probe replacing its prose fallback, declare-not-covered when MCP absent) and WIRED into `/review` as a new conditional PHASE-2.5 dispatch — the first time the runtime check actually runs (resolving 3 `design-auditor` orphan sites). **Producer alignment:** `frontend/mobile-engineer` briefs gained a `### Design Fidelity` subsection (bind tokens incl. typography, declare hover/focus-visible, carry `data-ref` anchors, escalate-don't-guess). Also de-assigned the read-only `design-auditor` from `/breakdown`'s per-task implementer table and fixed a pre-existing `ac-verifier.md` `list_pages`-not-allowlisted bug. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; `_design`/`_design_tokens`/`_constitute`/`_review` suites green. testForge20 e2e is the remaining user-driven hard gate.
- feat(artifact): per-step planning-artifact WIP commits across the pipeline (`37-PER-STEP-ARTIFACT-COMMIT-PLAN.md`, 2026-06-23). Each pipeline command — `/research`, `/discover`, `/specify`, `/plan`, `/grill`, `/breakdown`, `/review`, `/verify` — now WIP-commits its OWN planning artifacts (spec/plan/handoffs/grill/review/verification reports + research/discover reports + per-feature `*-state.json`) the moment it writes them, via the new shared `.devforge/lib/artifact_helper commit-artifacts` verb (install-repo-only + fail-soft — the git op never blocks the command). This closes the gap where planning artifacts sat untracked until `/finalize`, so a `git clean` could silently delete them: work is now git-safe at every step (recoverable after an interrupt or `git clean`). The per-step commits fold into `/finalize`'s `git reset --soft` squash, so the final feature commit — and the PR — is byte-identical to before. `/finalize` also retains an unconditional `specs/<feature>/` safety-net commit. Supersedes `33-FINALIZE-STAGES-SPEC-ARTIFACTS-PLAN.md` (which chose a finalize-only `git add specs/<feature>/`); this plan carries 33's whole-dir/install-repo-only safety-net forward as D4. `/implement` + `/summarize` are unchanged — both already committed their own artifacts. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. testForge20 e2e (standalone + wrapper) is the remaining user-driven hard gate.
- feat(grill,plan): `/grill` REVISE-PLAN now emits a re-entry seed consumed by `/plan` (`36-GRILL-UNIVERSAL-REENTRY-PLAN.md`, 2026-06-23). The REVISE-PLAN disposition emits a backward `specs/[feature]/grill-seed.json` with `target_stage="plan"`, consumed by a new `/plan` **PHASE 0a.7** re-entry block (mirrors `/specify`'s Phase 0.5 consumer) so a re-`/plan` addresses the grill's confirmed findings instead of re-deriving the plan — `/plan` becomes the **4th consumer** of the `ReEntrySeed`. `_grill/seed_schema.py` `SEED_TARGET_STAGES` grows `3 → 4` (`spec`/`discovery`/`research` + `plan`); a `render_report` `_UPSTREAM_STAGES` (the 3 upstream stages) guard keeps RE-ENTER-UPSTREAM rendering distinct from REVISE-PLAN (RE-ENTER-UPSTREAM still targets the 3 upstream stages for `/research` / `/discover` / `/specify`; only REVISE-PLAN targets `plan`). OQ-1 resolved: `carried_findings` stays `List[str]`. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. testForge20 e2e is the remaining user-driven hard gate.

### Fixed
- fix(breakdown): validate assigned agents against the installed roster (`38-BREAKDOWN-AGENT-ROSTER-VALIDATION-PLAN.md`, 2026-06-24). `/breakdown` assigned each task an agent from a static table with no check that the agent was actually generated for the project, and the split-or-escalate rule was prose-only — so a consumer install (a desktop Electron app with no backend stack) got `backend-engineer` assigned to an Electron main-process file, and `/implement` halted far downstream on the missing agent. Two halves fixed. **A (mechanical gate):** a new `breakdown_helper verify-agent-roster <tasks-dir>` forcing-function (sibling to `verify-contract-chain` / `verify-ac-coverage`) globs the installed `.claude/agents/*.md` roster and HARD-halts at `/breakdown` Phase 3.5 on any task whose `**Agent**:` isn't installed (listing offenders + the available roster, mirroring `/implement`'s message); the same check is folded into `finalize-handoff` as a chokepoint so a poisoned `breakdown-handoff.json` cannot be written. Fail-closed on an absent/empty roster; the default `--agents-dir .claude/agents` is correct in both standalone and wrapper mode (the roster lives in the install root, not the Source Root). **B (table fix):** the Agent Assignment table gained a row for non-server host/runtime-entrypoint code (Electron main, desktop-app `main`, CLI entrypoint, Tauri core) → the owning package's stack implementer per `PACKAGE_STACKS`, explicitly NOT `backend-engineer` by default. The `/implement` missing-agent guard is unchanged — this moves the failure left, from `/implement` to `/breakdown`. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops (974 breakdown/implement tests pass). testForge20 / consumer e2e is the remaining user-driven gate.
- fix(grill): write the re-entry seed from the user's verdict, not the recommendation (`39-GRILL-SEED-VERDICT-GATED-PLAN.md`, 2026-06-24). `/grill` wrote `grill-seed.json` in PHASE 6 from the *recommendation*, before the PHASE-7 human gate — so an overridden seed (grill recommends Revise/Re-enter, user picks Proceed) became an orphan a later `/plan` or `/specify` silently obeyed. Fix (Option A): `write-seed` + its commit move into PHASE 7's matching re-entry arm, gated on the user's verdict — the seed exists only when the user authorizes a re-entry that matches the recommendation; a cross-pick or Proceed/Kill writes none. Helper verbs + `render-report --re-entry-target` unchanged; 392 `_grill` tests green. Closes the override case left open by plan 36 D3.
- fix(grill): correct `/grill` PHASE 4 refuter routing (`35-GRILL-REFUTER-ROUTING-FIX-PLAN.md`, 2026-06-23). The spec told the orchestrator to pass only a finding's author to `route-refutation --finders`, but the helper requires every eligible refuter to be present in `--finders` — so with `devils-advocate` the sole present finder, all findings self-refuted to their own author and no cross-examination ran. Spec-side fix only (`src/commands/grill/main.md` PHASE 4): a present-refuter determination step composes `--finders "devils-advocate,<present-refuters>"` so the architect-excluded refuter priority `[code-reviewer, qa-reviewer, security-reviewer]` actually routes; the `_shared` refutation helper is unchanged. Empirically validated. testForge20 e2e is the remaining user-driven gate.
- fix(update): prune removed files and wire all 2.0 delivery paths in `update.sh` (2026-06-23). `update.sh` delivered new/changed commands and overwrote helpers but never pruned removed files and skipped several delivery paths, so 2.0 targets carried dead commands/agents/helpers and missed new framework agents. Now: prunes removed commands (via the emitter `--list`), prunes+installs agents via the `.devforge/` template-snapshot oracle (new agents land even pre-`/configure`; `/configure`-pruned agents respected), mirrors `.devforge/lib` to drop removed helpers, and `chmod`s delivered hooks + git-hook templates. `manifest.json` drops 8 dead flat-command entries and adds `storage-rules.md` + `src/hooks/**` delivery; `claude.py` gains `--list` (the canonical promoted-command source). Verified end-to-end against a real install (prune + new-agent install + helper mirror + dry-run no-op + idempotency).

## [2.0.0] - 2026-06-23

### Added
- feat(configure): `/configure` now excludes the framework's installed folders from the consumer project's linters/formatters (`31-LINT-IGNORE-FRAMEWORK-FOLDERS-PLAN.md`, 2026-06-22). The framework installs into ANY ecosystem (Python, Go, Rust, Ruby, JS/TS, …) and its folders carry `.py` (`.devforge/lib/*`), `.md`, `.sh` — so a target's own toolchain (ruff/black/mypy, prettier/eslint, golangci-lint, rubocop, …) would reformat/flag the framework's templates + helper code. New cross-ecosystem **detect-and-append registry** (`_configure/_lint_ignore.py` + `lint-ignore` verb, `/configure` Phase 6) excludes `.claude/`, `.devforge/`, `specs/`, `bugs/`, `research/`, `discover/`, `audits/` (NOT `docs/`) from each linter detected by config-file presence. 15 handlers: prettier/eslint/markdownlint/flake8/biome/ruff/black/isort/mypy/pylint/rustfmt/rubocop/golangci-lint/VS Code/JetBrains. STDLIB-ONLY (no PyYAML/tomlkit) → safe AUTO writes for gitignore/INI/JSON families + clean-case TOML; everything risky (external YAML, eslint flat-config, existing-TOML-tables) falls to a printed MANUAL instruction — never a corrupting edit. Dry-run → bulk-confirm → `--apply`; NON-FATAL + default-SKIP on ambiguous reply (it writes the user's own configs). 80 helper tests; per-linter ignore syntaxes verified against official docs. testForge20-style e2e on a real JS + Python target is the remaining user-driven gate.
- feat(generate-docs): `/generate-docs` now supports standalone single-root (non-monorepo) projects (`29-GENERATE-DOCS-SINGLE-ROOT-PLAN.md` Workstream A, 2026-06-21). The concern enumerator previously skipped the `.` package unconditionally — correct for a monorepo orchestration root, but it produced zero docs when `.` is the only real package. Now `.` is enumerated when it is the sole package (Option A); the project tier seeds directly from the concern docs when no package overviews exist (`_enumerate_concern_docs`/`_read_concern_seed`); the orchestrator skips Phase 3 (package tier) for single-root to avoid the `docs/overview.md` collision. Also fixed two latent HIGH bugs the single-root path exposed: the `pkg="."` subfolder prefix (`f"{pkg}/src/..."` → `"./src/..."`) silently blanked the structure tree + broke the split partition for every single-root concern (now built via `PurePosixPath`). Monorepo output is byte-identical. 148 unit tests + a real-data smoke (`preflight` on a real single-root index → 3 concerns).

### Removed
- chore(onboard): retired `/onboard` (`29-GENERATE-DOCS-SINGLE-ROOT-PLAN.md` Workstream C, 2026-06-21). Superseded by `/generate-docs` (Skeleton-Fill Mode) for brownfield doc generation — `/onboard` was already documented as deprecated in `tech-writer.md`. Deleted `src/commands/onboard/` + `onboard_helper{,.py}`; removed from emitter `_PROMOTED` + `src/manifest.json`; removed the tech-writer "Onboarding Mode" (now two modes: Normal + Skeleton-Fill); scrubbed the flow + catalog in `src/CLAUDE.md`, the `src/docs/` stub templates, and `agents-AUTHORING.md`. `/setup-wizard` retirement is tracked separately (`30-RETIRE-SETUP-WIZARD-PLAN.md`) because it still hosts the agent-generator spec read by `scripts/generate-agents.py` and is the documented agent-install entry point.

### Added
- feat(report-bug): rebuilt `/report-bug` — the proposal-only file-and-defer arm (`27-REPORT-BUG-COMMAND-PLAN.md`, 2026-06-19). Builds the "file a bug to defer" arm that `/fix` (plan 26 D4) and the `src/CLAUDE.md` fix-or-file offer already assumed but had no command behind. A live, emitted command at `src/commands/report-bug/main.md` + a new `src/devforge/lib/_report_bug/` helper subpackage (verbs `preflight` + `write-bug`) + a `report_bug_helper{,.py}` launcher. **Pure capture, agent-free** (D2) — parses a description (+ optional `--file`/`--severity`), resolves the `bugs/` dir under the install root (wrapper-mode-aware, reusing `_implement/_workspace.resolve_workspace`), writes ONE `bugs/NNN-<slug>.md` (`**Status**: Open`, `**Source**: manual`) and stops; it dispatches no agent and runs no diagnosis (that is `/research`'s job), never touching the bug lifecycle beyond the initial `Open` record. **Proposed by routing state, not a size metric** (D3) — the system offers `/report-bug` whenever a real, code-confirmed defect won't be remediated now (out-of-fix-window defects, in-window defects the user declines to `/fix`, `/fix` scope-bounces the user declines to `/specify`); it reuses the existing `fix_helper in-fix-window` check and is the always-available file-only fallback. **Reuses (does NOT fork) the bug-writer** (D4) — Phase 0 extracted `file_bugs` from `_verify/_bugs.py` into `src/devforge/lib/_shared/bug_file.py` and added a `source="verify"` default param (replacing the hardcoded `**Source**: verify`); `/verify` passes no source so its output is byte-identical (its `tests/lib/_verify/` suite is the regression net) and `/report-bug` passes `source="manual"`. Emitter `_PROMOTED += report-bug`; the stale flat-file `src/commands/report-bug.md` entry was removed from `src/manifest.json` (folder layout is `_PROMOTED`-handled) and the superseded `src/_pending/commands/report-bug.md` draft was deleted. (Supersedes the original v1.7.0 `/report-bug` — the manual-scan, `/fix bugs/NNN` design — recorded below.) Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; `tests/lib/_shared` + `tests/lib/_report_bug` green. testForge20 e2e is the remaining user-driven hard gate.
- feat(fix): reintroduced `/fix` — proposal-only gated pipeline-remediation command (`26-REINTRODUCE-FIX-PLAN.md`, 2026-06-19). A NEW live command at `src/commands/fix/main.md` + `references/` + a new `src/devforge/lib/_fix/` helper subpackage + a `fix_helper{,.py}` launcher. **Job:** remediate a known, already-diagnosed, already-scoped defect the pipeline itself surfaced — WITH `/implement`'s full per-task gates — WITHOUT re-running spec → plan → breakdown. **Supersedes ONLY plan 21's D1** ("no fast-path command or tier"); every other plan-21 decision stands (the `/refactor` drop + D2–D6 are untouched). The reversal is deliberate: the framework converged after plan 21 on "shared engine underneath, distinct command surface per distinct workflow moment" (`/review` vs `/verify` over `_shared/`; `/verify` reusing `verify-touched`), a pattern plan 21 D1 did not anticipate — and the staleness fear D1 cited was a property of the deleted v1.28 COPY draft, not of a thin CALLER. **OFFERED, never auto-invoked** (every forge command sets `disable-model-invocation: true` — the model proposes, the user types `/fix`) as the "remediate now" arm of a **two-arm fix-or-file offer** in exactly THREE in-window situations, all post-`/implement`/pre-`/summarize` (D2): `/review` surfaces findings, `/verify` returns NEEDS WORK, or the USER raises a defect the model code-confirms in-window; every other moment offers ONLY the file-a-bug arm. It is NOT a cold/free-text bug-fixer — a standalone cold bug still goes hand-fix / full-chain (plan 21 §4's boundary preserved). **Thin caller, no copied machinery** (D3/D6) — `/fix`'s back half is byte-for-byte `/implement` PHASES 5–7, reused by CALLING the installed `implement_helper` verbs `verify-touched` (with self-repair) → `merge-review-panel` (the four-reviewer panel) → `run-forcing-functions-gate` → the two-stage hard gate → `wip-commit`; it copies none of them, so it cannot drift. The ONE `implement_helper` change is the additive, backward-compatible task-less `wip-commit` mode (`--task-file`/`--index`/`--number` made optional so `/fix` can commit a `[WIP] fix:` without a task; `/implement` keeps passing them and stays byte-identical). **Findings-only** (D4) — `/fix` writes no `bugs/` file and closes none; the `bugs/` `Open → In Progress → Fixed` lifecycle stays MANUAL (the user edits the status, or re-runs `/verify`). This reconciled `src/devforge/storage-rules.md` (the stale `fix → updates bugs/… to Fixed` File Lifecycle line removed and the "How Bug Files Are Resolved" / `In Progress` / Fix-Notes / Related-Issues sites degeneralized to manual). **Scope-escalation bounce** (D7) — a "fix" that turns out to need an architectural/behavior change STOPS and recommends `/specify`. The case-3 conversational offer lives as a TIGHT always-on rule in `src/CLAUDE.md` (the only host for a non-command behavior), gated on `fix_helper in-fix-window`. Emitter `_PROMOTED += fix`. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. testForge20 e2e is the remaining user-driven hard gate.
- feat(finalize): redesigned `/finalize` — terminal PR-prep (surgical docs + history squash) (`25-FINALIZE-COMMAND-REDESIGN-PLAN.md`, 2026-06-18). Replaces the stale pre-pivot `src/_pending/commands/finalize.md` draft (deleted) with a live, emitted, pipeline-wired command at `src/commands/finalize/main.md` + `references/results-and-docs.md` + a new `src/devforge/lib/_finalize/` helper subpackage + `finalize_helper{,.py}` launcher. **Job:** the terminal PR-prep step — surgical feature-completion docs plus git-history cleanup. Runs after `/summarize`; its next step is "create a PR" (TERMINAL — no next-pipeline-command pointer). **DISPATCHES an agent AND MUTATES — the inverse of `/summarize` on both axes** (D1/D4): it dispatches the `tech-writer` agent (Normal/surgical mode) AND rewrites local git history (the squash) AND writes `docs/`. It runs NO finder ensemble, NO refutation pass, and renders NO verdict. **tech-writer KEPT but RETARGETED to live `docs/`** (D1) — the agent's surgical updates point at the LIVE Plan-F locations (`docs/<package>/<concern>/index.md` Hazards, `docs/<package>/architecture.md`, `docs/architecture.md`), NOT the dropped per-feature `docs/features/` tier; this redesign reconciles `tech-writer.md`'s internal contradiction (the dead `docs/features/` claims that survived alongside the Plan-F "dropped" notes) plus the dead-tier claims in `src/docs/overview.md` + `src/devforge/storage-rules.md`. **History squash** (D3/D6) — `_finalize/_squash.py`'s net-new `squash` verb (+ `resolve-squash-base` / `check-pushed`) collapses the feature's `[WIP]`/`[checkpoint]` commits into one clean `feat(<feature-name>): <title>` commit (attribution per config); the squash is gated behind an explicit user confirmation (D4) and refuses to rewrite already-pushed history (the `origin/<branch>..HEAD` guard skips + warns). **Wrapper-mode dual squash, source repo traceless** (D5) — in wrapper mode BOTH repos are squashed; the source (product) repo squash uses the `[TICKET-ID] - Description` format with NO `Co-Authored-By` / NO AI traces / NO conventional-commit prefix, REGARDLESS of `COMMIT_ATTRIBUTION`. **Docs `[WIP]`-committed BEFORE the squash** (D8) so they fold into the single clean commit. **Reuses (does NOT fork) the assembled-feature scope resolver** — `src/devforge/lib/_shared/feature_scope.py` (the same resolver `/review` / `/verify` / `/summarize` use, `heading_label="Finalize Scope"`) supplies both the changed-file list for the tech-writer brief and the squash merge-base (D2); `/finalize` does NOT reuse the `_shared` refutation engine. **Stateless** (D7) — no run-state file; the squash is a single idempotent op (re-running on a finalized feature no-ops "Nothing to finalize"). Emitter `_PROMOTED += finalize`; the stale flat-file `src/commands/finalize.md` entry was removed from `src/manifest.json` (the folder layout is `_PROMOTED`-handled). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops. **Deferred:** Phase 6 (separable `/implement` source-WIP attribution reconciliation — D9; after a successful squash the per-task WIP commits are erased, so it only covers the narrow already-pushed-skip edge). testForge20 e2e is the remaining user-driven hard gate.
- feat(summarize): redesigned `/summarize` — PR-ready feature synthesis (`24-SUMMARIZE-COMMAND-REDESIGN-PLAN.md`, 2026-06-18). Replaces the stale pre-pivot `src/_pending/commands/summarize.md` draft (deleted) with a live, emitted, pipeline-wired command at `src/commands/summarize/main.md` + `references/summary-format.md` + a new `src/devforge/lib/_summarize/` helper subpackage (`_cli`, `_preflight`, `_changes`, `_inputs`) + `summarize_helper{,.py}` launcher. **Job:** the pure synthesis step — render the completed feature as a PR-ready narrative. Runs after `/verify` approves, before `/finalize`. **Pure synthesis** — orchestrator-inline, **agent-free** (D1), renders NO verdict, and is **read-only on every input** (D4) — it writes ONLY `specs/[feature]/summary.md` and mutates none of the spec/plan/tasks. **AC status from `verification.md`** — the summary reads the authoritative AC table from `/verify`'s `specs/[feature]/verification.md` rather than re-deriving it from the spec (`_inputs` `read-verification`, D3); it also pulls each task's `## Completion Notes` (`parse-completion-notes`) and the plan's key decisions from `plan.md` (`read-plan-decisions`, D9). **Reuses the assembled-feature scope resolver** — `_changes` `gather-change-data` reuses `src/devforge/lib/_shared/feature_scope.py` (the same resolver `/review` and `/verify` use) for the git change stats; no fork. **Stateless** (D8) — `_preflight` gates on the setup chain + the spec `**Status**: Complete` flip (NO constitution-populated guard); the run is idempotent (a re-run overwrites `summary.md`) and makes a `[WIP]` commit that `/finalize` squashes. Emitter `_PROMOTED += summarize`; the stale flat-file `summarize.md` entry — and the lingering `review.md` flat-file entry flagged by plan 22 — were removed from `src/manifest.json` (folder layouts are `_PROMOTED`-handled). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; ~150 `tests/lib/_summarize/` tests pass. `/finalize` (the pipeline's final step) is the sibling follow-on, redesigned separately. testForge20 e2e is the remaining user-driven hard gate.
- feat(grill): new `/grill` — design-level adversarial review of the completed plan (`23-ADVERSARIAL-GRILLING-PLAN.md`, 2026-06-17). A standalone, **opt-in** command — the design-level mirror of `/review` — at `src/commands/grill/main.md` + `references/` + a new `src/devforge/lib/_grill/` helper subpackage + a `grill_helper{,.py}` launcher. **Job:** attack the completed `plan.md` BEFORE it is decomposed, so a fatally-flawed design dies cheaply. Positioned between `/plan` and `/breakdown` (run it for high-stakes plans — new architecture / dependency / data model / security; it is NOT a mandatory gate). **Single adversary** — dispatches the new `devils-advocate` agent (roster grows 17 → **18**; a read-only `tools:` allowlist with the CBM graph + context7 + WebFetch/WebSearch, NO `Edit`/`Write`/`Agent`), the architect's adversarial counterpart: the architect proposes/optimizes a design, the adversary attacks the chosen one and hunts the flaw nobody refuted. **The adversary does its own blast-radius traversal** — the scope step hands it a STATIC manifest (paths to `plan.md` + `spec.md` + the recon dossier + `constitution.md`), not a pre-resolved radius, because a Python helper cannot call the CBM graph; the agent performs the three-ring walk itself (Ring 0 read-in-full of the plan's MODIFY targets + their tests; Ring 1 capped one-hop callers/callees via `trace_path`; Ring 2 query-only via `search_graph`/`search_code`/`get_architecture`, pulling only the snippet a hit points to). **Self-gated web-verification** — when (and only when) the plan names an external dependency, the adversary VERIFIES the plan's claim against current docs via context7 (WebFetch/WebSearch for CVEs only) — VERIFY, not re-DISCOVER: a "better option exists" hit is flagged as an upstream signal, never adopted into a plan rewrite. **Architect-EXCLUDED refutation pass** — each grounded attack is cross-examined by a non-author refuter from `[code-reviewer, qa-reviewer, security-reviewer]` (the architect is never a refuter — it is not a finder here and must not cross-examine its own conceptual domain), default-dismiss unless the defect is re-demonstrated from quoted code. **Reuses the refutation engine** — the helper imports the roster-agnostic verbs from `src/devforge/lib/_shared/` (the same `route_refutation` / `apply_verdicts` / validation pipeline `/audit` and `/review` use), passing its architect-excluded priority through `route_refutation`'s `priority=` parameter — ZERO engine fork. Helper subpackage modules: `seed_schema`, `_state`, `_preflight`, `_scope`, `_brief`, `_report`, `_cli` (12 verbs: `check-status-and-flip`, `preflight`, `resolve-scope`, `render-brief`, `consume-tmp`, `validate-findings`, `route-refutation`, `render-verify-brief`, `consume-verdicts`, `apply-verdicts`, `render-report`, `write-seed`). **Output** = `specs/[feature]/grill.md` (confidence-gated findings — CONFIRMED headline + surfaced high-stakes `[CONTESTED]` + a Dismissed/Worth-a-glance appendix) plus a **recommended 4-way disposition** — PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL — chosen via the D9 two-question "does fixing it destroy the plan?" routing tree (a grounded defect can be CORRECT while its root cause lives UPSTREAM; a finding earns an upstream route only when it is INVARIANT under every valid plan). **Backward re-entry seed** — on a RE-ENTER-UPSTREAM disposition `/grill` also emits `specs/[feature]/grill-seed.json` (`ReEntrySeed` schema, `source = "grill"`, `target_stage ∈ {spec, discovery, research}`, carrying `prior_conclusion` / `invalidating_evidence` / `must_satisfy` + a bounded-compounding `cycle_count`); the upstream `/research` / `/discover` / `/specify` commands consume it ADDITIVELY / CONDITIONALLY / INERTLY (D10 removability — a helper-free direct JSON read in a conditional re-entry block that no-ops when no matching seed exists, so deleting `/grill` leaves the three upstream commands byte-unchanged). **The USER owns the final verdict** at the `/breakdown` approval gate — `/grill` recommends, it never decides. Emitter `_PROMOTED += grill`. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; ~hundreds of `tests/lib/_grill/` tests pass (full repo suite 8054 passed). The `/research` + `/discover` consumer blocks are authored + reviewed in the working tree but commit alongside the uncommitted `18-SCOPE-FIDELITY-AND-PROMPT-INTAKE-PLAN.md` intake-gate work that shares those two files (the `/specify` consumer block + all other phases are committed). testForge20 e2e is the remaining user-driven hard gate.
- feat(verify): redesigned `/verify` — acceptance-criteria verification + verdict (`22-VERIFY-COMMAND-REDESIGN-PLAN.md`, 2026-06-17). Replaces the stale pre-pivot `src/_pending/commands/verify.md` draft (deleted) with a live, emitted, pipeline-wired command at `src/commands/verify/main.md` + `references/report-format.md` + a new `src/devforge/lib/_verify/` helper subpackage (13 verbs: `check-status-and-flip`, `preflight`, `resolve-feature-scope`, `read-ac-config`, `parse-acs`, `read-review-findings`, `merge-ac-results`, `check-hygiene`, `compute-verdict`, `render-report`, `render-inline-summary`, `flip-spec-status`, `file-bugs`) + `verify_helper{,.py}` launcher. **Job:** the ONE thing nothing else in the pipeline owns — **the verdict**. Runs after `/review` drains a feature's tasks, before `/summarize`/`/finalize`. **Acceptance-criteria verification** — proves each AC PASS/FAIL/PARTIAL via the `ac-verifier` agent, whose method is selected by `ac_verification_mode` in `.devforge/project-config.json` (`runtime-assisted` probes the running app via Chrome DevTools MCP + API + CLI using the `ac_runtime_url`/`ac_runtime_api_base`/`ac_runtime_cli_command` config, MCP-availability probed first; `tests` / `code-only` / `off` read code, with `off` a code-reading floor noted as advisory in the verdict). **Assembled-feature mechanical checks** — type-check / lint / build / test across ALL the feature's tasks together (the cross-task version of `/implement`'s per-task gate), **reusing the installed `implement_helper verify-touched` binary** report-only at `--iteration 0` — it reports failures, never self-repairs (fixing is `/implement`'s job). **Folds in `/review`'s findings** — reads `specs/[feature]/review.md` confirmed + high-stakes `[CONTESTED]` findings into the verdict (warns + proceeds weakened if missing). **Owns the verdict** — the deterministic `compute-verdict` renders APPROVED / NEEDS WORK / REJECTED to `specs/[feature]/verification.md`; constitution violations always block APPROVED (confirmed → REJECTED, contested → at least NEEDS WORK). **Writes back to the spec** (the deliberate departure — the only review/verify command that mutates its input): on APPROVED, after a cross-check that all task files are `Complete`/`Skipped`, `flip-spec-status` flips `spec.md`'s `**Status**:` → Complete and ticks the passed AC boxes `- [ ]` → `- [x]` — the lifecycle transition `/summarize` + `/finalize` gate on; on NEEDS WORK, `file-bugs` writes `bugs/NNN-*.md` in the `.devforge/storage-rules.md` format (`Source: verify`). **Reuses (does NOT fork) the assembled-feature scope resolver** — Phase 0 extracted `resolve_feature_scope` + its git helpers out of `_review/_scope.py` into `src/devforge/lib/_shared/feature_scope.py` (flat layout) and parameterized the scope-block heading label (`/review` renders "Review Scope", `/verify` renders "Verification Scope"), re-pointing `/review` to import from `_shared` so it stays byte-behaviorally identical (its `tests/lib/_review/test_scope.py` is the regression net). `/verify` does NOT reuse the `_shared` refutation engine (no finder ensemble, no refutation pass — that is `/review`'s job). **Agent fix** — `src/agents/ac-verifier.md`'s `## Input` contract was aligned to the live config keys (the dead `AC_VERIFICATION` / `AC_VERIFICATION_URL` / `AC_VERIFICATION_API_BASE` keys + `auto`/`browser-only`/`api-only` modes are gone) and the four `ac_verification_mode` modes got an explicit behavior mapping; the plan-15 agent skeleton was not reshaped. Emitter `_PROMOTED += verify`; the stale flat-file `src/commands/verify.md` entry was removed from `src/manifest.json` (the folder layout is `_PROMOTED`-handled). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; ~hundreds of `tests/lib/_verify/` tests pass. **Deferred:** OQ-1 (fine-grained tests-mode test→AC mapping — the `ac-verifier` code-reads in `tests` mode; the assembled test leg is an independent PHASE-4 blocker) and OQ-2 (structured `verify-handoff.json` for `/summarize`+`/finalize` — they gate on the spec `**Status**: Complete` flip for now). testForge20 e2e is the remaining user-driven hard gate.
- feat(review): redesigned `/review` — feature-level emergent cross-task review (`20-REVIEW-COMMAND-REDESIGN-PLAN.md`, 2026-06-15). Replaces the stale pre-pivot `src/_pending/commands/review.md` draft (deleted) with a live, emitted, pipeline-wired command at `src/commands/review/main.md` + 4 `references/` + a new `src/devforge/lib/_review/` helper subpackage + `review_helper{,.py}` launcher. **Job:** the ONE review nothing else in the pipeline owns — emergent cross-task issues the `/implement` per-task panel structurally cannot see (it reviews each task's diff in isolation): cross-task security holes, assembled-data-flow performance, cross-task duplication/divergence, cross-task architectural drift. Runs after `/implement` drains a feature's tasks, before `/verify`. **Scope** = the assembled-feature git diff (`git diff --name-only $(git merge-base <base> HEAD)..HEAD` — the union of the feature's accumulated WIP commits, mechanical ground truth, not completion-note prose). **5-finder ensemble** (`code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst`) dispatched in emergent-cross-task mode over the assembled diff (anti-relitigation preamble injected verbatim so finders report ONLY emergent cross-task issues, not what the per-task panel already forced fixed), each finding validated against real source then **cross-examined by a 4-refuter pass** (`/audit`'s priority `[code-reviewer, architect, qa-reviewer, security-reviewer]`; `performance-analyst` finds but NEVER refutes — a specialist surfaces perf findings, a generalist refutes them) that default-dismisses unless the defect is demonstrable as emergent at feature scope. **Reuses the refutation engine** — Phase 0 extracted the roster-agnostic pieces (`findings_schema`, `_consume`, `_validate`, `_consensus`, `_verify`) out of `_audit/` into `src/devforge/lib/_shared/` (flat layout) and parameterized `route_refutation`'s priority so `/audit` stays behaviorally identical (its `tests/lib/_audit/` suite is the regression net); `/review` is code-independent of `/audit` (both depend only on `_shared/`). **Output** = `specs/[feature]/review.md`, findings-only (CONFIRMED headline + surfaced high-stakes `[CONTESTED]` + a Dismissed/Worth-a-glance appendix) — **NO verdict** (the verdict is `/verify`'s); `/verify` folds the findings into its verdict (warns if missing) and `/audit`'s recurring-issue scan globs recent `specs/*/review.md`. Read-only — no source edits, no auto-commit. Emitter `_PROMOTED += review`. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer + claude-code-guide loops; 267 `tests/lib/_review/` tests pass. testForge20 e2e is the remaining user-driven hard gate.
- feat(audit): refutation pass + confidence-gated report for `/audit` (`19-AUDIT-FALSE-POSITIVE-PRECISION-PLAN.md`, 2026-06-15). Recovers PRECISION on the over-reporting `/audit` pipeline without shrinking the recall plans 11/12 bought. **New refutation / cross-examination stage** (PHASE 4.2.5, after consensus/merge, before recurring/rank): new `references/refutation-preamble.md` + new `_audit/_verify.py` module + four verbs (`route-refutation`, `render-verify-brief`, `consume-verdicts`, `apply-verdicts`) in `_cli.py`. `route-refutation` groups the deduped working list by author and assigns each group a NON-AUTHOR finder (deterministic priority order `[code-reviewer, architect, qa-reviewer, security-reviewer]`, author-excluded, only present finders eligible; the sole present finder self-refutes); each refuter cross-examines its routed subset under the refutation preamble and writes a fixed-format markdown verdict per finding (`confirmed`/`dismissed`/`uncertain`), default-dismiss unless the defect is re-demonstrated from quoted code; `consume-verdicts` parses + merges the per-refuter files and `apply-verdicts` partitions the working list. NO new agent file — cross-examination reuses the four existing finders (a single non-finder skeptic was invalidated by the charter check — no generalist non-finder correctness reviewer exists in the roster). **Confidence-gated report**: the headline (`## Top N Priorities` + `## Findings by File`) draws from CONFIRMED findings unioned with high-stakes `[CONTESTED]` findings; DISMISSED + low-stakes uncertain findings render in a clearly-separated `## Dismissed / Worth a Glance` appendix (never deleted — a dismissal is itself a judgment that can be wrong). **High-stakes recall guard (D7)**: `security` + `[CONSTITUTION-VIOLATION]` findings the refuter returns `uncertain` on are SURFACED in the headline flagged `[CONTESTED]` (never buried), and a "dismiss" verdict on a grounded `[CONSTITUTION-VIOLATION]` finding also surfaces as `[CONTESTED]` rather than dropping to the appendix (a grounded rule-break is never silently dismissed). **Multi-pass de-amplification**: `_merge` no longer floors confidence to `"Likely"` on multi-pass recurrence and `_rank`'s `pass_bonus` is neutralized — `pass_count` / `[MULTI-PASS:k]` are now descriptive only (correlated re-generation across passes is recall evidence, not correctness evidence; single-pass output is unaffected). **False-positive-bias reword**: the explicit "bias toward false positives / assume a bug exists" framing is replaced with "demonstrate the defect or do not report it" across `references/adversarial-preamble.md`, the coupled `_scope.py` `_CLOSING_REMINDER` constant (the last brief instruction), and the report `## Methodology` blurb — the adversarial stance and the Confidence tiers stay (recall preserved), precision is recovered downstream in refutation. **Stale-draft deletion**: removed the pre-port `src/_pending/commands/audit.md` draft (superseded by the live command per `10-AUDIT-COMMAND-PORT-PLAN.md` Decision 1; a stale on-disk copy was a future-hallucination seed). Anchored to plan 17's confirm-before-it-gates principle (different mechanism — the helper/orchestrator scratch-chain split, not `merge-review-panel`). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer loops; ~1026 `tests/lib/_audit/` tests pass. testForge20 e2e is the remaining user-driven hard gate.
- feat(implement): per-task reviewer panel + test gate for `/implement` (`17-IMPLEMENT-PER-TASK-PANEL-PLAN.md`, 2026-06-07). Three changes to the per-task loop. **PHASE 5 verify now runs tests** — the scope-aware flow gained a test command per touched package (per-package `test_command` in `PACKAGE_STACKS`, primary-stack `TEST_COMMANDS[0]` fallback), run last in the fixed order static checks (type-check + lint) → build → tests; backward-compatible — a project with no test command configured runs no tests and the verify behavior is otherwise unchanged. **PHASE 6 is now a parallel panel of four read-only reviewers** — `code-reviewer` + `qa-reviewer` + `security-reviewer` + `performance-analyst` fan out over the touched files at once and are merged by the new `merge-review-panel` helper verb into a single verdict (panel-clean = all four clean), replacing the prior single code-reviewer⇄engineer review loop for this phase; on any dirty reviewer the implementing agent is relaunched once with the synthesized findings and the FULL panel re-fans-out at the next iteration (no delta-scoping, so a repair can't open a cross-file-regression hole), capped at `REVIEW_LOOP_CAP` (3). **PHASE 7 is all-findings-fixed** — the human hard gate's `approve` (Stage B) is reachable ONLY from a fully-clean panel; the `accept anyway` option is removed, an open finding never reaches `approve`, and reviewer conflicts surface first as a Stage A `AskUserQuestion` decision item (resolve → re-review to clean → only then Stage B). One D8 carve-out `src/agents/*.md` edit: `security-reviewer` + `performance-analyst` verdict lines normalized to `### Verdict:` so the shared `_VERDICT_RE` matches. Built on plan 15's standardized 17-agent reviewer roster (hard precondition, satisfied). The single-reviewer `review-loop-step` verb is **superseded** by `merge-review-panel` for PHASE 6, but its module (`_cmds_review_loop.py`) is retained as the source of the shared `_VERDICT_RE` + `REVIEW_LOOP_CAP`. Phase 7 (testForge20 e2e) is the remaining user-driven hard gate.
- feat(generate-docs): conventions schema extended 4 → 6 buckets (`16-CONVENTION-CAPTURE-PLAN.md`, 2026-06-07). `/generate-docs` Phase 4.3 now captures two new `## Conventions` buckets in `docs/architecture.md` — **`styling`** and **`state_management`** — alongside the existing `naming` / `file_organization` / `import_style` / `error_handling`, composed from the codebase (CBM + detected stack) under the same judgment discipline as the existing four (orchestrator-composed; no dedicated mechanical detector). The two new buckets are **appended last** in the `section_order` tuple across all four producer sites (`_renderers.py` `section_order`, `_cmds_project.py` `cmd_set_architecture_conventions` key tuple + `--conventions` help text, `generate-docs/main.md` Phase 4.3 table row + example call); because empty buckets are omitted from render output, a 4-bucket caller renders **byte-identical** to before (regression-free extension). Closes the PRODUCER gap behind `15-AGENT-STANDARDIZATION-PLAN.md`'s consumer-side convention-grounding: the plan-15 agents reference captured styling/state-management conventions that `/generate-docs` (the only code-reading command) previously never captured. Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer loops. NO `src/agents/*.md` change. testForge20 e2e is the remaining user-driven gate.
- feat(agents): new `qa-reviewer` agent — read-only test-suite assessor split out of `qa-engineer` (`15-AGENT-STANDARDIZATION-PLAN.md`, 2026-06-07). Roster grows 16 → **17**. `qa-engineer` becomes a pure test-writer **builder** (retiered to `do`, inherits all tools); the assessment half (AC-to-test traceability, coverage-gap verdicts) moves to the new `qa-reviewer`, one of the 6 tools-locked pure read-only reviewers. The new source auto-appears in `{{AGENT_LIST}}` (derived from filenames, not descriptions) with no consumer wiring; the meta-block contract (`generate-agents.py` / `emit_claude`) is unchanged.
- feat(audit): mode-conditional `--passes` default (2026-06-02). When `--passes` is omitted, `resolve-mode` now defaults the pass count by scope mode — **broad** (`--full`/empty) → 2, **hotspot** (`--top N`) → 2, **narrow** (file/directory/`--uncommitted`) → 1 — so deep/periodic audits get multi-pass union recall by default while quick targeted (narrow) checks stay single-pass. An explicit `--passes N` (still clamped to `[1,3]`) always overrides the mode default. The execution-model fork still keys on the resolved `passes` value (`== 1` → linear single-pass, no merge; `>= 2` → the Phase 3.0 K-loop), so broad/hotspot runs now take the multi-pass merge path by default. Spec (`src/commands/audit/main.md` Phase 1.1 + frontmatter/usage) + consumer-overlay `#### /audit` entry reconciled; helper change shipped separately.
- feat(audit): opt-in multi-pass union `/audit --passes N` (`12-AUDIT-MULTI-PASS-UNION-PLAN.md`, 2026-06-01). New `--passes N` flag (int, **default 1**, clamped to `[1,3]` with a stderr note when clamped) composes with every scope mode (`--full --passes 3`, `--top 25 --passes 2`, narrow `--passes 2`). At `--passes 1` behavior is **byte-identical to before** — the merger is never invoked and the existing single-pass pipeline (incl. `compute-consensus`) runs verbatim. At `--passes >= 2` the dispatch + consume + validate phase runs K times and a single tolerant location-based merge (`merge-passes`, key `(file, line ± 3)`) unions all 4×K agent outputs, **replacing** `compute-consensus`; merged findings carry a `pass_count` and the tags `[MULTI-PASS:k]` (seen in ≥2 passes) and `[CROSS-AGENT]` (≥2 agents, severity bumped), and a finding in ≥2 passes gets a confidence floor of `Likely`. The report Summary gains a `- Passes run: N | Multi-pass-confirmed findings: <count>` line only when `passes >= 2` (count = findings with `pass_count >= 2`); single-pass reports are unchanged. Tradeoff: in multi-pass the per-finding `consensus` (agent-name) map is `{}` (no `compute-consensus` runs) — cross-agent corroboration surfaces via the `[CROSS-AGENT]` tag + severity bump instead. Purpose: push single-run observed-union coverage (~60%) toward ~79% (2 passes) / ~92% (3 passes) for periodic deep "second-opinion" audits, at K× the cost (hence opt-in). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer loops; ~840 `_audit` tests passing. New `_audit/_merge.py` (tolerant union merger) + `merge-passes` / `render-report --passes-run` verb wiring + `pass_count`/`[MULTI-PASS]` schema/report/rank threading + main.md K-loop. Step 8 (testForge20 e2e A/B) is the remaining user-driven hard gate.
- feat(audit): full-spectrum `/audit` (`11-AUDIT-FULL-SPECTRUM-PLAN.md`, 2026-06-01). One default run now hunts five dimensions — mislogic (existing) + **system design** (layering/SOLID/god-component) + **language/framework best practices** (type-safety suppression, untyped boundaries, reactivity/lifecycle misuse, perf-idiom smells) + **duplication/divergence** + **constitution-principle adherence** — no lens flag. Backbone applies the "commands don't own shape" principle: findings carry a producer-declared `Category` (owned `findings_schema.CATEGORY_ENUM` = `mislogic, system_design, best_practice, duplication, security, blind_spot`), validated in `_consume.py`, and `_report._bucket_finding` buckets by the declared category — the old agent-name heuristic (`agent==architect→Cross-Module`, `agent==security-reviewer→Security`) is **deleted**. Report sub-sections: Mislogic / **System Design** (renamed from Cross-Module Contradictions) / **Best Practices** / **Duplication** / Security Regressions / Constitution Violations. New `references/best-practices-checklist.md` (polyglot-safe, stack-tagged examples; judgment findings marked `Likely`/`Speculative`, never `Certain`) injected into every agent brief alongside `mislogic-checklist.md`. Phase 3.1 now standard-passes constitution excerpts via `--extra-context-file` so the adherence hunt has rules to check. Static performance-idiom smells moved in-scope (runtime profiling still out; visual/UI design still out). Emitter auto-globs the new reference (`audit command: yes (folder, 5 references)`). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer loops; ~10 reviewer findings fixed (incl. a grounded-false Phase 3.1 claim that `preflight-context` exposes constitution text — it only emits booleans).
- feat(breakdown): redesigned `/breakdown` aligned with the redesigned chain (`09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md`, 2026-05-25). New `src/commands/breakdown/main.md` (11 phases mirroring `/plan`) + `breakdown_helper` (13 verbs: `pick-plan`, `render-pick-summary`, `list-plans`, `check-status-and-flip`, `read-plan-handoff` consumer, `render-findings-from-plan`, `render-task-file`, `render-tasks-index`, `render-consultation-block`, `verify-contract-chain` + `verify-ac-coverage` forcing-functions, `finalize-handoff` producer, `render-execute-task-handoff`) + `_breakdown/handoff_schema.py` (`handoff_kind="breakdown"`, 232 tests). Consumes the approved plan's sibling `plan-handoff.json` ("consumer obeys producer"). Emits human `tasks/NNN-*.md` (storage-rules format) + structured `specs/NNN/breakdown-handoff.json` — the producer side of the breakdown→`/execute-task` handoff (machine contract lives in JSON, NOT YAML frontmatter; `/execute-task` consumer conforms when built — see `07-EXECUTE-TASK-REDESIGN-PLAN.md`). Mandatory+scoped `architect` consultation at the decomposition phase (atomicity / ordering / contract-chain integrity); agent-assignment table inlined (sole owner — `/fix`+`/refactor` slated for removal). Emitter `_PROMOTED` += `breakdown`.
- feat(constitute): add `forge-internal:verify-universal-defaults` drift detector for consumer constitute.json vs canonical src/constitution.md (read-only; maintainer-side)
- feat(constitute): forcing-functions family — consumer-side mechanical detectors backing constitution rules LLMs systematically violate. Substrate at `src/devforge/lib/_constitute/_forcing_functions/` shipped via `.devforge/lib/constitute_helper`. Three rules wired across phases:
  - `verify-magic-enum` — flags inline string/int literals where a same-module enum-like declaration (TS `enum` / `as const` map / Python `Enum`) covers the same value (`ccc25b8`; empirical gate-relaxation `aae5a02` + `EMPIRICAL-VERIFY-MAGIC-ENUM-2026-05-21.md`)
  - `verify-cross-layer-imports` — flags import edges that cross declared layer boundaries from a user-supplied DAG + per-layer dir mapping (`a370229`)
  - `verify-any-leak` — flags `any` annotations (TS) / `Any` (Python) in files importing from declared generated-types dirs (`4b058da`)
- feat(constitute): wizard wire-in for forcing-functions config-capture (`f999a88`) — `/constitute` Section 3.5 echoes a three-rule `forcing_functions` config block (not a numbered constitution.md sub-section) and applies via three `constitute_helper set-forcing-functions` calls (one per rule); `cmd_verify` now validates each enabled `forcing_functions.<rule>` block against the per-rule required-fields schema in `_constitute/_schema.py`; helper exposes machine-readable `list-forcing-functions [--enabled] [--format key|verb]` for hook consumers.
- feat(install): pre-commit hook template `src/git-hooks/pre-commit-forcing-functions.sh` shipped to `.devforge/templates/git-hooks/` by `install.sh` (`f999a88`); hook resolves `.devforge/lib/constitute_helper` + `.devforge/constitute.json`, runs each enabled detector, aborts the commit on any violations (exit 1) and emits the helper's stderr findings verbatim. Opt-in via `/constitute` Phase 6.4 (`cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`); silently no-ops when config or helper is absent.

### Changed
- **`/constitute` Phase 2 conventions routing redirect (`16-CONVENTION-CAPTURE-PLAN.md`, 2026-06-07)** — `/constitute` Phase 2 gains an explicit routing table that REDIRECTS each `docs/architecture.md` `## Conventions` bucket to its constitution home (or to none), needed because Section 3 (Code Quality Standards) previously composed from the WHOLE `DOCS_JSON.architecture.conventions` raw-text blob, so the two new `/generate-docs` buckets would otherwise leak into §3. The redirect: the four legacy buckets (`naming` / `file_organization` / `import_style` / `error_handling`) stay → **§3 Code Quality Standards** (Section 3 intake NARROWED to those four, separated by their rendered `**Heading**` sub-section labels); **`state_management` → §4 Patterns & Anti-Patterns** project-specific buckets (§4.1.1 / §4.2.1 / §4.3.1, emitted via `add-pattern-rule --scope project-specific`), NOT §3; **`styling` → documented-only** in `docs/architecture.md`, lifted into NEITHER §3 NOR §4 (styling authority is existing components plus the design reference, never the constitution, per `15-AGENT-STANDARDIZATION-PLAN.md`). Instruction-only — NO `/constitute` helper / `_md_parsers` change (the raw-text lift already carries the new buckets through). Built behind the instruction-author→instruction-reviewer loop.
- **Agent-fleet standardization to a canonical skeleton (`15-AGENT-STANDARDIZATION-PLAN.md`, 2026-06-07)** — rewrote all 17 `src/agents/*.md` bodies to one ordered skeleton (Identity → `## Core Expertise` → `## Project Paths` → `## Approach` → `## Output` → `## Boundaries & Handoffs` → `## Rules`), anchored to `architect` as the reference implementation; previously the 16 ad-hoc-authored sources diverged in identity phrasing, section names, severity vocabularies, and constitution/memory handling, with `{{PROJECT_PATHS}}` missing from two and several discrete bugs. The 6 **pure read-only reviewers** (`code-reviewer`, `security-reviewer`, `ac-verifier`, `design-auditor`, `performance-analyst`, `qa-reviewer`) gain a read-only `tools:` allowlist (`Read, Grep, Glob, Bash` + enumerated read-only chrome-devtools MCP tools for ac-verifier/design-auditor; **no** `Edit`/`Write`/`Agent`) and the unified `Critical/High/Medium/Info` severity (anchored to `findings_schema.SEVERITY_ENUM`); the 8 builders + `runtime-debugger` actor inherit all tools and carry builder-style `## Boundaries & Handoffs`. `performance-analyst` is **demoted** from an optimization-implementer to a pure read-only analyst, and `qa-engineer` is **split** (test-writer builder retained; assessor half → new `qa-reviewer`). Specials `architect`/`tech-writer` were light-conformed (section NAMES + Rules style) without flattening their richer substance — `tech-writer` keeps its 3 modes. **Consumer rewire** (the load-bearing consequence): `qa-engineer`-reviewer references repointed to `qa-reviewer` across `/review`/`/fix`/`/refactor`/`/audit` (command markdown + `src/CLAUDE.md` + the `_audit` helper `_AUDIT_AGENTS`/`_FOCUS_BLOCKS` + tests, changed atomically), and `performance-analyst`/`security-reviewer` implementer rows rerouted to the owning engineer in `breakdown/main.md` + `_agent-assignment.md`. Commits: `9a63f19` (plan) + `348561b` (Phase 0 authoring doc `src/agents-AUTHORING.md`) + `fcc4947` (Phase 1 reviewers) + `ea2995d` (Phase 2 builders/actor) + `76df502` (Phase 3 specials) + `3fe4644` (Phase 4 consumer rewire). The build contract (`generate-agents.py` / `emit_claude` / meta-block) is untouched; 901 `_audit` tests pass and Phase 5 structural verification passed (17 agents emit, exactly 6 tools-locked, all cross-ref sweeps 0, `test_generate_agents` + full suite green). Full install-ride / testForge20 e2e is the remaining user-driven gate.
- **Consumer-overlay `CLAUDE.md` command-catalog trim (`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`, 2026-05-24)** — collapsed the deep phase-by-phase `#### Command Details` paragraphs for `/research`, `/discover`, `/specify` (170w / 268w / 299w) into purpose one-liners. `src/CLAUDE.md` dropped 3383 → 2806 words (−17.1% always-on per consumer turn). Full phase mechanics remain authoritative in each command body (`src/commands/<cmd>/main.md`), which loads only on invocation. Rationale: every forge command sets `disable-model-invocation: true`, so Claude Code does NOT inject the command's `description` frontmatter into model context (custom commands are merged into skills; the docs' context-loading table marks that flag "Description not in context") — so the always-on `CLAUDE.md` catalog (flow diagram + bullet list + one-line `####` purpose) is the only model-facing command-awareness source and stays, while the redundant phase walkthroughs are removed. Supersedes the ABORTED `06-CONDITIONAL-CONTEXT-PLAN.md`.
- **`/research` redesigned** — replaces the prior "quick feasibility check" with a structured bug + enhancement investigation flow grounded in the 4-command setup chain. Hard-gated on `.devforge/init.yaml` + `docs/architecture.md` + `.devforge/configure.yaml` + `constitution.md` (refuses to run when any artefact is missing). 4-phase orchestrator:
  - **Phase 0 — Preflight + topic.** Helper-side artefact check + CBM index-stamp refresh.
  - **Phase 1 — Symptom clarification.** 6-dimension rubric (`symptom`, `affected_area`, `repro_or_current`, `desired`, `scope`, `unchanged_behavior`) with bounded turns (2 follow-ups per dimension), bug-vs-enhancement mode auto-detection from symptom tokens, helper-side direct-contradiction detection + LLM-side drift/refinement/mode-flip classification, accepted-gap exit via `[NEEDS CLARIFICATION]` markers.
  - **Phase 2 — Investigation (orchestrator-inline).** Cost gate, then orchestrator-direct CBM walk in the main thread — no subagent dispatch. Mandatory CBM discovery chain: `search_graph` → if 0 hits `search_code` (catches inline Vue `<script setup>` / React hooks / Svelte reactive expressions invisible to graph) → `trace_path` → `get_code_snippet`. Mandatory parallel-pattern sweep over the primary file before recording findings (catches sibling buggy blocks — e.g. `causeToChoices` parallel to the primary `.sort()` site). Mandatory hypothesis enumeration ≥2 (each with one-line falsifier + runtime-probe flag). Optional bug-mode structured root cause (`trigger` + `root_cause_systemic` + ≤3 `contributing_factors`, Google SRE postmortem shape) when confidence ≥ Hypothesis. Optional verify-step block (`probe` + `reproduction` + `discriminator`, Cursor Debug Mode shape) when any hypothesis needs a runtime probe.
  - **Phase 3 — Report compose + render.** Orchestrator-direct setters: summary + approaches (each cites which hypotheses it addresses + does-not-cover) + recommended approach (helper enforces `unchanged_behavior` respect) + constitution constraints + complexity + mode-aware verdict + next-step text. Helper `verify` cross-checks all invariants before `render`.
  - **Phase 4 — Save + recommend.** Saves to `research/YYYY-MM-DD-<topic-slug>.md` on user confirm. When verdict allows proceeding (`Root cause confirmed` / `Root cause hypothesis (needs repro)` for bug; `Feasible` / `Feasible with caveats` for enhancement), the rendered doc includes a copy-pasteable `/specify "..."` handoff block — manual copy, no automation.
- New framework helper: `.devforge/lib/research_helper` (POSIX shell wrapper around `research_helper.py`) — owns shape via 36 subcommands; state persisted to `.devforge/research-state.json` (SymptomMemo) + `.devforge/research-report.json` (ResearchReport).
- Emitter `scripts/emitters/claude.py` `_PROMOTED` tuple now includes `research`; `update.sh` re-emit message lists the full promoted set.
- Design pivot 2026-05-11: dropped the `research-investigator` subagent (briefly authored then removed). Empirical comparison showed dispatch cost 5-7× tokens AND tunneled the investigator onto the first matched surface, missing parallel buggy blocks in the same file. Orchestrator-inline Phase 2 with explicit parallel-pattern sweep restores coverage at lower cost.
- **`/discover` shipped + 5 empirical fixes (2026-05-14)** — net-new greenfield-feature discovery command (parallel to `/research`). Hard-gated on the same 4-command setup chain. 4-phase orchestrator: Phase 0 preflight + topic; Phase 1 8-dimension scoping rubric (`functional_scope` / `users` / `inputs_outputs` / `integration_points` / `constraints` / `non_goals` / `success_criteria` / `edge_cases`) with bounded turns + helper-side conflict detection; Phase 2 three sequential orchestrator-inline steps — **Step 2.0** project-wide internal canonical-pattern search (mandatory; extracts capability verbs from `functional_scope` and records `internal:<path>` prior-art entries BEFORE web survey), **Step 2.1** web survey gap-narrowed to capabilities NOT covered by Step 2.0, **Step 2.2** fit-check via docs layer + CBM structural chain (`search_graph` → `search_code` → `trace_path` → `get_code_snippet`) reconciling user-belief vs codebase-reality; Phase 3 compose+render+verify; Phase 4 save to `discover/YYYY-MM-DD-<topic-slug>.md` with copy-pasteable `/specify` handoff block. Verify enforces invariants A-G including **invariant G** (when any prior-art `source.startswith("internal:")`, `recommended_option.rationale` MUST cite at least one of those internal paths — forces "extend existing" framing over "build new") and the **verdict-flip rule** (Strained/Misfit fit OR Major-refactor effort → `Reconsider` unless `memo.override_recorded` via `scope-finalize --accept-gaps`). Fix batch from 4 empirical runs on testForge20: (A) mandatory `--module-path` grounding from CBM result rows; (B) Phase 2.0 internal canonical-pattern search + invariant G; (C) slug truncation at last `-` word boundary (no mid-word cuts); (E) setter-side rejection of letter-prefixed `--name` (`A:`, `Option B:`) to prevent `### Option A: A: ...` double-prefix renders; (F1) `set-next-step-text --topic` for LLM-distilled 1-2 sentence handoff (prevents verbatim `functional_scope` dump into `/specify "..."`); (F2) `_clean_inline_escapes` strips literal `\n` / `\r` / `\t` from setter values + topic.
- New framework helper: `.devforge/lib/discover_helper` (POSIX shell wrapper around `discover_helper.py`) — owns shape via 40+ subcommands; state persisted to `.devforge/discover-scope.json` (ScopingMemo) + `.devforge/discover-report.json` (DiscoveryReport).
- Emitter `scripts/emitters/claude.py` `_PROMOTED` tuple now includes `discover`.

### Removed
- chore(commands): dropped `/fix` and `/refactor` (`21-DROP-FIX-REFACTOR-PLAN.md`, 2026-06-15). Deleted the two stale pre-pivot drafts `src/_pending/commands/fix.md` + `src/_pending/commands/refactor.md` and removed their already-broken `src/manifest.json` install entries (both `source` paths pointed at non-existent `src/commands/*.md` files). Neither command was ever emitted (absent from `scripts/emitters/claude.py` `_PROMOTED`), so no installed target project changes — this is a source-tree cleanup. Every consumer reference was dereferenced across the consumer overlay, agents, command specs, helper docstrings, the adjacent `_pending` tail, and the maintainer docs. Rationale: fast-path commands duplicate the full chain's pieces (diagnosis / execution / the task contract) — see `21-DROP-FIX-REFACTOR-PLAN.md`. Small bugs are hand-fixed and routed through the existing tools (`/research` for diagnosis, a one-off test task, the project's verify commands, `/audit` as the periodic safety net); `/security` + `/audit` are explicitly retained.
- chore(commands): dropped `/security` (2026-06-19). Deleted the never-emitted pre-pivot draft `src/_pending/commands/security.md` and removed its already-broken `src/manifest.json` install entry (the `source` path pointed at a non-existent `src/commands/security.md`). The command was never emitted (absent from `scripts/emitters/claude.py` `_PROMOTED`), so no installed target project changes — a source-tree cleanup. **Supersedes plan 21's D5** (`21-DROP-FIX-REFACTOR-PLAN.md`, which retained `/security` as "read-only and non-duplicating"). The retention premise no longer holds: `/audit` now runs the SAME `security-reviewer` agent in every scope mode `/security` offered (file / directory / `--uncommitted` / `--full`) with a more sophisticated engine (refutation precision, multi-pass recall, confidence-gated reporting, and a high-stakes-security `[CONTESTED]` surfacing guard), making `/security`'s coverage a strict subset of `/audit`'s — building it to parity would mean a second, inferior codebase-review engine to maintain. The `security-reviewer` AGENT is RETAINED (still used by `/audit`, `/review`, `/implement`, `/grill`); only the standalone `/security` COMMAND is removed. Consumer references dereferenced across the consumer overlay (`src/CLAUDE.md` Standalone bullet + Command Details block), the `/specify` standalone-gate paragraph (`src/commands/specify/main.md`), `README.md`, and `DEVELOPMENT-STATUS.md`. If a security-only focus is later wanted, the right mechanism is an `/audit --security` focus flag reusing the `/audit` engine, not a standalone command.

## [1.28.0] - 2026-04-10

### Added
- **`/audit` command** — standalone, on-demand adversarial whole-codebase audit for periodic "second opinion" quality reviews. Launches code-reviewer, architect, qa-engineer, and security-reviewer in ADVERSARIAL MODE to hunt for mislogic (naming-vs-behavior mismatches, lying comments, off-by-one errors, dead branches, cross-file contradictions, contradictory configs), with a structured Mislogic Hunt Checklist of 9 pattern categories. Supports `--full` (default), `--uncommitted`, file path, or directory scope. Reads up to 5 recent `specs/*/review.md` files (last 90 days) to track recurring/unresolved issues across features. Writes dated reports to `audits/YYYY-MM-DD-audit.md` and prints inline summary. Read-only, not auto-committed, **not part of any workflow chain** — invoke manually after several specs ship
  - **Anti-hallucination grounding**: every finding must include a verbatim Evidence quote from the actual code; Phase 4.2 validation re-reads each cited file and discards findings whose quote does not appear there (fabrication guard). Discard counts surfaced in the report's Methodology section so users can detect when agents drift toward fabrication
  - **Stream-consolidation**: agents write to `audits/.tmp-{agent}.md`; the parent reads and deletes one at a time to avoid context exhaustion (the failure mode that motivated `/verify`'s split into `/review` + `/verify` + `/finalize` in 1.27.0)
  - **Algorithmic merging only**: cross-agent consensus and recurring-issue tags use exact-match hash keys, never LLM "is this similar" judgment, to prevent confabulated consensus
  - **Adversarial Preamble** wraps each agent invocation with explicit "false positive vs fabrication" rules + closing mode reminder injected as the last instruction so the most-recent prompt wins over the agent's baked-in polite tone. Adversarial mode lives in `audit.md` only — `/review`, `/verify`, `/execute-task`, `/fix`, `/refactor` continue using the normal professional tone
  - Two-batch parallel agent launch (code-reviewer + architect, then qa-engineer + security-reviewer) with module-subagent fan-out for 200+ file codebases
  - Hard-stops with clear messages when no audit-capable agents are installed or when `constitution.md` is unpopulated
  - 14 IMPORTANT RULES enforce read-only behavior, grounded adversarial bias, algorithmic merging, dated non-overwriting reports, agent failure resilience, and wrapper-mode awareness

### Changed
- Template version: 1.27.0 → 1.28.0

## [1.27.0] - 2026-04-08

### Added
- **`/review` command** — expert code review launching specialist agents (security-reviewer, performance-analyst, qa-engineer) on all changed files across a feature. Produces structured review report at `specs/[feature]/review.md` with severity-classified findings. Separate from `/verify` verdict — findings only, no judgment
- **`/finalize` command** — feature ship preparation: launches tech-writer for feature-level documentation in `docs/`, then squashes all WIP/checkpoint commits into a single clean feature commit. Gate-checked (spec must be Complete). The last step before PR creation

### Changed
- **`/verify` simplified** — removed security review, performance review, test assessment (moved to `/review`), tech-writer docs (moved to `/finalize`), feature squash (moved to `/finalize`), and auto-`/summarize` invocation. Now focuses on: AC verification (ac-verifier agent), cross-task integration check, and verdict. Reads `/review` findings if available (warns if missing). Agent count per command reduced from 5 to 1
- **Workflow chain expanded**: `→ /execute-task → /verify → /summarize` becomes `→ /execute-task → /review → /verify → /summarize → /finalize`. All steps user-activated with warn-not-block guards
- **All auto-triggers removed**: `/execute-task` no longer auto-invokes `/verify` when all tasks complete; `/verify` no longer auto-invokes `/summarize` on APPROVED verdict. Each command reports a clear next-step prompt instead
- **`/summarize` commit** uses `[WIP]` prefix so it's included in `/finalize`'s squash. Adds finalization detection (warns if run after squash). Adds "Next: Run `/finalize`" guidance
- **`/execute-task` completion** now shows "all tasks complete, run `/review` → `/verify` → `/summarize` → `/finalize`" when the last task finishes (single-task and multi-task modes)
- Template version: 1.26.0 → 1.27.0

### Fixed
- **Auto-verify reliability** — the auto-verify trigger was buried in a dynamically-loaded sub-file (`_context-maintenance.md` Phase 7.3) where the LLM lost the thread after outputting compaction recommendations. Real-world evidence: verify ran but partially completed — squash executed (destructive) while docs and summary were dropped. Fixed by eliminating auto-triggers entirely — each workflow step is now a focused, user-activated command that completes reliably within context limits
- **Context exhaustion in `/verify`** — monolithic verify launched up to 5 agents + squash + auto-summarize in a single command. Context filled before later phases could execute, causing partial failures. Fixed by splitting into `/review` (1-3 agents), `/verify` (1 agent), `/finalize` (1 agent) — each command fits comfortably in context
- **Partial failure safety** — previously, squash (destructive, irreversible) could execute while docs/summary were skipped due to context exhaustion, leaving the repo in an inconsistent state. Fixed by isolating the squash in `/finalize` as the very last step, user-initiated

## [1.26.0] - 2026-04-06

### Added
- **`/security` command** — standalone on-demand security review. Targets a file (with optional line range), directory, uncommitted changes, or full codebase (`--full`). Uses security-reviewer agent with constitution and memory context. Full codebase mode uses module-based subagents for large projects. Read-only — reports findings with CWE identifiers and remediation suggestions
- **`/verify` Phase 5.5: Test Assessment** — qa-engineer agent assesses test coverage gaps for all changed files. Checks AC-to-test traceability, untested AC items, missing edge case tests. Report-only — does not write tests. AC items with zero test coverage become Warning issues in the verification report
- **Security-reviewer template**: Added Section 7 (Client-Side Security — localStorage, cookies, client state exposure) and Section 8 (Unsafe Code Patterns — eval, dynamic imports, prototype pollution, path traversal, unsafe deserialization)

### Changed
- **Security-reviewer agent now mandatory** for all projects — moved from conditional (auth-only) to always-included in setup wizard. Every project gets security review at `/verify` Phase 4, regardless of whether it has auth libraries
- **`/verify` Phase 4** simplified — removed conditional "if agent exists" check. Security review always runs
- **Security-reviewer template**: Added Rule 7 — skip checklist items that don't apply to the project type (CLI tools skip CORS checks, backend APIs skip client-state review)
- Template version: 1.25.0 → 1.26.0

## [1.25.0] - 2026-04-04

### Added
- **Per-task code review**: `/execute-task` Phase 3.3 launches code-reviewer agent after each task. Findings reported to user with options (address now / continue / stop). Critical issues block completion. Issues caught at Task 2, not Task 10
- **Shared agent assignment** (`_agent-assignment.md`): Single source of truth for file-layer→agent mapping, referenced by `/breakdown`, `/fix`, and `/refactor`
- **Plan-spec cross-reference check**: `/plan` Phase 2.5 verifies every spec AC has an implementation path before presenting to user. Gaps auto-fixed or flagged as risks
- **`{{TYPE_SAFETY_RULES}}` placeholder**: Agent templates now language-agnostic. Setup wizard generates type safety rules based on detected language instead of hardcoded TypeScript items
- **`DEFAULT_BRANCH` config key**: Detected once at setup (cascade: origin/HEAD → main → master → develop). Used by `/summarize` and `/verify` squash — no hardcoded `main`
- **Enriched bug file format**: Feature, AC, Expected/Actual Behavior, Related Issues fields. Bug files are self-contained work orders for fresh `/fix` sessions
- **Failure-count guidance** in `/verify` Phase 10: 1-3 issues → fix in session, 4-6 → compact between fixes, 7+ → consider re-executing tasks
- **Cross-platform Chrome DevTools script**: Supports macOS + Linux + WSL, JetBrains + Chrome/Chromium paths, `CHROME_DEBUG_PORT` env var override, port 9222 fallback
- **Conditional Chrome MCP**: Only installed for projects with `AC_VERIFICATION` set to "auto" or "browser-only". Non-frontend projects get clean `.mcp.json`
- **Prior task completion notes**: `/execute-task` Phase 1.2 reads completion notes from earlier tasks for context continuity across sessions
- **`templateRepoOnly` section** in manifest: Formally documents files excluded from installation (release.md, install.sh, update.sh, audit files)
- **Context7-first library research**: `/plan` and `/research` try Context7 for specific library docs before falling back to WebSearch

### Changed
- **`/execute-task` restructured**: 12 sub-phases → 6 phases. Removed per-task tech-writer (inline docs are the agent's job, feature docs at /verify). Removed per-task WIP squash (deferred to /verify). Removed AC readiness check and TaskCreate ceremony
- **`/verify` Phase 3**: Full code review → cross-task integration check. Individual code quality handled per-task
- **`/verify` Phase 10**: Complex per-issue triage with auto-fix invocations → simplified issue report with suggested actions and batch bug filing. `/verify` no longer invokes `/fix` — verification is read-only
- **`/verify` Phase 9.5**: Wrapper-only squash → all-mode feature squash using `git merge-base` instead of checkpoint commit search
- **`/verify` Phase 3.3**: Tech-writer for feature-level docs (moved from per-task in execute-task)
- **`/fix` Phase 4**: Direct code writing → agent delegation via shared assignment table. Added docs/ lookup for intended-behavior context. Added agent selection via `_agent-assignment.md`
- **`/specify` Phase 2**: Removed 2-4 question limit. AI asks in rounds of up to 5, prioritized by impact, stops when enough for the spec
- **`/plan` Phase 0**: Constitution guard moved before research (was inside output template — wasted research if constitution empty)
- **`/plan` Signal Scan**: Tightened all 6 signals with "NOT a signal when already in project" qualifier
- **`/research` Phase 2**: Expanded search scope to include `docs/` alongside source files
- **`/summarize` Phase 2**: Reads `DEFAULT_BRANCH` from config, added wrapper mode source repo change gathering
- **Recovery rollback**: Grep-based commit discovery → stored hash from wip.md with `git cat-file` validation
- **Code review in `/fix` and `/refactor`**: Silent auto-fix on BLOCK → report to user with options (consistent with execute-task)
- **WIP phase tracking**: Accurate transitions across all phases in execute-task, fix, and refactor
- **Contract verification**: Grep for existence checks, Read for structural checks — clarified in breakdown and execute-task
- **Constitution stub**: Setup wizard copies template with resolved headers instead of generating free-form text. Guarantees sentinel strings for guards
- **Agent templates**: `JSDoc` → `Inline docs` in architect, frontend-engineer templates. TypeScript-specific checklist items replaced with `{{TYPE_SAFETY_RULES}}`
- Template version: 1.24.1 → 1.25.0

### Fixed
- Recovery Phase 6 squash failure left unrecoverable WIP state
- Session state lost critical context for late-stage tasks (completion notes now preserved in compaction)
- Argument parsing edge cases (`1-feature-auth` misread as range, no error on invalid task numbers)
- Auto-verify sometimes skipped (instruction buried in external file — added inline reminder)
- Multi-task continuation Phase 8 step 2 wording caused confusion (explicit sub-steps)
- `/verify` REJECTED verdict had no next-step guidance (now directs user to revise spec)

### Removed
- **`/clarify` command**: Redundant pre-specify step. Clarification absorbed into `/specify` Phase 2 with no question limit
- **Per-task tech-writer** from execute-task: Agents write inline docs. Feature docs at `/verify` time
- **Per-task WIP squash** from execute-task: WIP commits accumulate, squashed by `/verify`
- **Chrome DevTools** from default `.mcp.json`: Conditional via setup wizard
- Dead recovery branches for non-existent phases
- Hardcoded TypeScript review items from 5 agent templates

## [1.24.1] - 2026-04-02

### Fixed
- **Missing Workflow sections** in implementation agent templates: `db-engineer`, `devops-engineer`, and `migration-engineer` now have `Your Workflow` sections consistent with their peers (backend-engineer, frontend-engineer, mobile-engineer)
- **Missing Output Format** in `qa-engineer` — only analysis/review agent without a structured output template. Now includes a Test Report format matching other review agents
- **Missing Output Format** in `architect` — design deliverables had no predictable structure. Now includes an Architecture Decision format (context, decision, components, dependencies, trade-offs)
- Template version: 1.24.0 → 1.24.1

## [1.24.0] - 2026-04-02

### Changed
- **Docs reading consolidated to `/specify`**: Docs are now read once at `/specify` Phase 1 and embedded into the spec's "Current State" section. `/plan` no longer reads `docs/` — it inherits docs context from the spec. `/execute-task` no longer searches `docs/` broadly — it reads only files referenced in the task's `Context docs` field
  - `/specify` Phase 3 restructured: docs-guided codebase analysis (targeted reads) when docs exist, full exploration fallback when they don't
  - Spec Section 2 explicitly instructs to capture docs context for downstream inheritance
- **New `Context docs` field in task format**: `/breakdown` now embeds specific doc file references per task (max 2), with Doc Reference Rules for when to include them (integration tasks, pattern extensions, API tasks) vs. skip (self-contained tasks)
- **`/execute-task` agent prompt** includes new `Documentation Context` section with content from task-referenced docs
- Template version: 1.23.0 → 1.24.0

## [1.23.0] - 2026-04-01

### Added
- **Tiered agent model system**: Replaced single `AGENT_MODEL` with 3 tiers — Think (opus: architect, api-designer, security-reviewer), Do (sonnet: implementation agents), Verify (sonnet: code-reviewer, ac-verifier, qa-engineer). Configurable per tier in setup wizard Question 8
  - Templates use `{{MODEL_THINK}}`, `{{MODEL_DO}}`, `{{MODEL_VERIFY}}` placeholders
  - `update.sh` auto-migrates old `AGENT_MODEL` config to tier keys on first run
- **2-dimensional agent assignment in `/breakdown`**: Tasks are now classified by nature (design-decision vs. mechanical) before assigning by file layer. Mechanical tasks go to the nearest dependency's agent instead of defaulting to architect
  - Bundling rule: mechanical tasks <30 lines with a single same-agent dependency can be merged into the parent task
- **`backend-engineer` in breakdown assignment table**: Previously had a template but no assignment rule — now assigned to API endpoints, controllers, middleware, services, and server-side logic tasks
- **Always-delegate rule in `/execute-task`**: Rule 1 now mandates every task must be executed via the Agent tool — orchestrator never writes implementation code directly, regardless of task size
- **Mobile support**: New `mobile-engineer` agent template with Flutter/React Native/Swift/Kotlin expertise. Mobile-specific sections added to design-auditor, devops-engineer, performance-analyst, and qa-engineer templates. Setup wizard detects mobile frameworks. Breakdown table includes mobile-engineer row

### Changed
- **Architect scope narrowed**: Assignment table row changed from "Core/domain/data layers, business logic, API, types" to "Domain models, interfaces, contracts, type definitions, architectural decisions" — implementation work now routes to backend-engineer
- **State management with orchestration logic** explicitly assigned to architect (BLoC with business rules, Redux reducers with logic, Pinia stores with computed logic)
- Template version: 1.22.0 → 1.23.0

### Fixed
- `backend-engineer` agent template existed but was unreachable — no breakdown assignment rule mapped to it
- Repository implementation tasks (boilerplate wrapping) over-assigned to architect instead of db-engineer
- DI registration / routing tasks over-assigned to architect instead of frontend-engineer
- Orchestrator skipping agent delegation for "trivial" tasks despite clear instructions

## [1.22.0] - 2026-03-26

### Added
- **Shared command partials**: Extracted conditional and duplicated sections into 4 reusable `_`-prefixed files in `.claude/commands/`:
  - `_recovery.md` — Phase 0 crash recovery logic, shared by `/execute-task`, `/fix`, and `/refactor` (previously duplicated ~50 lines × 3 files)
  - `_context-maintenance.md` — Phase 7.5 session state and context health management, loaded on-demand by `/execute-task`
  - `_multi-task-continuation.md` — Phase 8 queue management and batch execution, loaded only for multi-task runs
  - `_tech-writer-onboarding.md` — Full onboarding scan instructions (Section A), loaded on-demand by `/onboard`

### Changed
- **Command prompt sizes reduced**: `/execute-task` 685→450 lines (-34%), `/onboard` 504→171 lines (-66%), `/fix` 520→471 lines (-9%), `/refactor` 581→531 lines (-9%) — reduces per-invocation cognitive load on Claude
- **Emphasis marker inflation reduced**: Strong markers (CRITICAL/NEVER/MUST/IMPORTANT) across the 4 main execution commands cut from 183→71 total — remaining markers reserved for genuine safety/correctness risks (data loss, workflow corruption, scope violations)
- **IMPORTANT RULES trimmed in `/execute-task`**: 11 rules→6, removing rules that duplicate inline instructions (fail-fast, agent isolation, verify-everything already enforced by their respective phases)
- **Tech-writer Part 2 prompts trimmed**: Document-when/skip-when criteria removed from `/execute-task`, `/fix`, and `/refactor` agent prompts — these already exist in the tech-writer agent file (Part 1) loaded at runtime
- **`/refresh-docs` now loads agent file**: Phase 3 follows the same Part 1 (agent file) + Part 2 (context) pattern used by all other commands, instead of embedding an inline prompt with duplicated rules
- Template version: 1.21.1 → 1.22.0

### Fixed
- Duplicated "Source repo note" paragraph in `/execute-task` Phase 6

## [1.21.1] - 2026-03-26

### Changed
- **Source auto-commit simplified**: Reduced per-command WIP commits from 5-7 (one per phase) to 1 (after verification passes only) — less context pressure, fewer points for Claude to forget
- **Squash logic deduplicated**: Extracted into a shared `Source Repo Auto-Commit` reference section at the top of each command file, replacing ~70 lines of duplicated inline logic with compact references
- **User-confirmed squash**: Source repo squash now proposes `[TICKET-ID] - Description` and asks user to confirm or edit before committing, instead of auto-committing silently
- Template version: 1.21.0 → 1.21.1

## [1.21.0] - 2026-03-26

### Added
- **`ac-verifier` agent template**: New agent that verifies acceptance criteria against a running application. Classifies each AC item as frontend (Chrome MCP), backend (API/curl), or manual, then systematically tests each one and returns a structured pass/fail report with evidence
- **Setup wizard Question 9**: AC verification mode selection — Auto (browser + API with fallback), Browser only, API only, or Off. Includes auto-detection of dev server URL and API base URL from package.json/framework defaults
- **3 new config keys**: `AC_VERIFICATION` (mode), `AC_VERIFICATION_URL` (dev server), `AC_VERIFICATION_API_BASE` (API endpoint base) — stored in project-config.json
- **MCP readiness checks**: `/execute-task` (Phase 1.3), `/fix` (Phase 1.1.5), and `/refactor` (Phase 1.1.5) now probe Chrome DevTools MCP at startup and display an informational warning if not available — non-blocking
- **13 new Chrome DevTools MCP permissions** in settings template: `navigate_page`, `take_snapshot`, `list_pages`, `select_page`, `click`, `fill`, `fill_form`, `wait_for`, `press_key`, `hover`, `list_console_messages`, `list_network_requests`, `get_network_request`

### Changed
- **`/verify` Phase 2 rewritten**: Now supports three paths — ac-verifier agent (when enabled + MCP available), code-reading fallback (when MCP unavailable or mode is "off"), and graceful degradation between them. Adds MCP availability probe and structured result merging with Category column
- **CLAUDE.template.md**: Updated `/verify` description to mention AC verification capability
- Template version: 1.20.0 → 1.21.0

## [1.20.0] - 2026-03-26

### Added
- **Source repo auto-commit in wrapper mode**: All execution commands (`execute-task`, `fix`, `refactor`) now auto-commit source changes to the inner repo with per-phase WIP commits for crash safety
- **Source repo squash**: `/verify` Phase 9.5 squashes all source WIP commits into a single clean commit when verdict is APPROVED. `/fix` and `/refactor` squash at their own Phase 8.1.1. Commit format: `[TICKET-ID] - Description` — ticket ID extracted from source branch name (`[A-Z]{2,}-[0-9]+` pattern), description from spec overview or bug/refactoring context. Falls back to user prompt if no ticket ID found
- **Source repo crash recovery**: Phase 0 in all 3 execution commands now checks and recovers source repo state. WIP marker includes `## Source Repo Checkpoint` section with commit hash and branch name
- **Pre-existing source changes warning**: Phase 2.5/3.1 warns if source repo has uncommitted changes before creating the checkpoint

### Changed
- Wrapper Rule 3 updated across setup-wizard, DEVELOPMENT-STATUS, and README — from "source commits are manual" to "auto-commit both repos with WIP + squash"
- Template version: 1.19.0 → 1.20.0

## [1.19.0] - 2026-03-26

### Changed
- **Tech-writer invocation standardized**: All commands (`execute-task`, `fix`, `refactor`, `verify`) now use the same 2-part prompt pattern — Part 1 loads `.claude/agents/tech-writer.md` (full agent workflow), Part 2 provides task-specific context
- **Documentation phase now mandatory**: `/fix` and `/refactor` Phase 7.5 changed from conditional ("if public API changed, invoke tech-writer") to mandatory — tech-writer always invoked and decides itself whether docs are needed, with explicit skip/document criteria and justification requirements
- **Post-doc verification strengthened** (`execute-task`): Now checks changed signatures on existing exports (not just new exports), detects stale doc references, and validates tech-writer skip justifications against actual diff
- Template version: 1.18.0 → 1.19.0

### Fixed
- **Task "Done When" checkboxes never checked**: `execute-task` Phase 4 had vague "Mark done conditions with `[x]`" — replaced with explicit instruction to change `- [ ]` to `- [x]` in the Done When section
- **Spec AC checkboxes never checked**: `/verify` Phase 7 updated spec status to "Complete" but never marked acceptance criteria checkboxes — added explicit instruction to change `- [ ]` to `- [x]` for passing ACs

## [1.18.0] - 2026-03-25

### Added
- **`/summarize` command**: New command that generates concise, PR-ready feature summaries from spec, plan, tasks, and git history — saves to `specs/[feature]/summary.md`
- **Auto-verify on feature completion**: `/execute-task` Phase 7.5.3 automatically triggers `/verify` when all tasks in the feature are marked Complete — no manual invocation needed
- **Auto-summarize on approval**: `/verify` Phase 9 automatically triggers `/summarize` when verdict is APPROVED
- **Full automated chain**: Last task completion → `/verify` → `/summarize` runs end-to-end without human intervention

### Changed
- Workflow diagrams across all commands now include `→ /summarize` as the final step
- `/verify` Phase 9 APPROVED path chains into `/summarize` instead of suggesting manual commit/PR
- `/execute-task` Phase 8 step 2 defers to Phase 7.5.3 for feature-complete detection
- Template version: 1.17.0 → 1.18.0

## [1.17.0] - 2026-03-25

### Added
- **Language-agnostic verification**: New `Type Check Command` and `Lint Command` fields in CLAUDE.template.md — commands now reference these fields instead of hardcoded `tsc --noEmit` / ESLint, supporting Python/Go/Rust/any language
- **WIP cross-command safety**: `## Command` field in `.claude/wip.md` identifies which command (execute-task, fix, refactor) created it — prevents cross-command recovery confusion with backward compatibility for pre-v3 wip.md files
- **Permissions**: Edit, Write, Bash, Agent added to `settings.template.json` default permissions — workflow no longer requires dozens of manual approval prompts per task
- **Constitution guard**: Added to `/verify` and `/clarify` — all 8 commands that read constitution now check for unpopulated placeholder
- **Framework detection**: Astro, Remix, Deno, Bun auto-detection in `/setup-wizard` Step 1
- **Review cycle cap**: `/refactor` Phase 6 code review now capped at 1 additional cycle (matching `/fix`)
- **Verify task cross-check**: `/verify` Phase 7 now confirms all tasks are Complete before marking spec Complete
- **Fix file overlap warning**: `/fix` Phase 1.2 warns when pending spec tasks target the same files
- **Release template check**: `/release` Phase 5.5 checks CLAUDE.template.md and storage-rules.md for needed updates
- **Squash error handling**: execute-task/fix/refactor now preserve wip.md if the final commit fails after `git reset --soft`

### Changed
- All verification steps in execute-task, fix, refactor, verify, breakdown, storage-rules now reference "Type Check Command from CLAUDE.md" and "Lint Command from CLAUDE.md" instead of TypeScript/ESLint
- CLAUDE.template.md Automated Guards section now language-agnostic ("type check + lint + build")
- CLAUDE.template.md workflow diagram labels corrected (each command has its own label)
- CLAUDE.template.md Crash Recovery section documents `## Command` field and cross-command detection
- CLAUDE.template.md PostToolUse hook description documents lint command asymmetry (hook runs type checker only; linter runs during explicit verification)
- `update.sh` three-way merge: baseline only updated on successful merge — previously updated unconditionally, silently losing template changes after conflicts
- `update.sh` `migrate_project_config()`: now extracts TYPE_CHECK_COMMAND, LINT_COMMAND, PROJECT_MODE with language-based fallback detection
- `update.sh`: replaced bash 4+ `${language,,}` with portable `tr '[:upper:]' '[:lower:]'` for macOS bash 3.2 compatibility
- `install.sh`: now removes `release.md` (template-repo-only command) and cleans `.claude/memory/` (template-repo-specific files) after copy
- `settings.template.json`: corrected context7 MCP tool name from `get-library-docs` to `query-docs`
- `template-manifest.json`: added `research/.gitkeep` to `copyIfMissing`
- `setup-wizard.md`: TYPE_CHECK_COMMAND and LINT_COMMAND added to required keys and example project-config.json
- Template version: 1.16.5 → 1.17.0

### Fixed
- `architect.template.md` line 15: `Te/sting` typo → `Testing`
- `onboard.md`: removed legacy "(Task tool)" parenthetical references

### Removed
- Dead `merge_sections()` Perl function (~100 lines) from `update.sh` — replaced by git merge-file three-way merge

## [1.16.5] - 2026-03-25

### Fixed
- **L1**: Documented agent model strategy in setup-wizard and README — explains why 13 agents use configurable `{{AGENT_MODEL}}` while tech-writer is hardcoded to `sonnet`
- **L6**: Removed undocumented `memory: project` field from runtime-debugger agent template — not a standard Claude Code frontmatter field, no other agent used it

### Removed
- **L3**: Deleted unused `spec.template.md` — `/specify` generates specs from an inline format, never reads this template

### Changed
- Template version: 1.16.4 → 1.16.5

## [1.16.4] - 2026-03-25

### Fixed
- **M1**: `/setup-wizard` now writes `.claude/setup-complete` marker at end of generation — allows detecting interrupted setups
- **M2**: `/execute-task` Phase 1.2 file reading budgeted — if task files exceed 500 lines total, reads only relevant sections instead of all files fully
- **M3**: `/execute-task` Phase 7.5.1 now verifies session-state.md line count after writing — trims oldest entries if over 40 lines
- **M4**: `/fix` and `/refactor` now update `.claude/session-state.md` after completion (new Phase 10) — prevents stale session state after non-execute-task workflows
- **M5**: Wrapper mode isolation check expanded to include `bugs/`, `research/`, `.mcp.json` — previously only checked 6 artifact types, now covers 9
- **M6**: Reconciled compaction contradiction between Phase 7.5.2 (advisory) and Phase 8 (pause) — added explicit note that the difference is intentional: single-task = recommend, multi-task = pause
- **M7**: `/breakdown` contract rules now require literal source code strings — "has a getter" style contracts replaced with guidance to reference declaration patterns (e.g., "`get cartTotals()`")
- **M8**: Documented `update.sh` `merge_sections()` limitation — only splits on `##` headers; custom `###` or `#` sections merge into preceding `##` body
- **M9**: `/specify` Phase 0.0 prerequisite added — verifies git repository exists before branch operations, prevents cryptic errors in non-git directories
- **M10**: Fixed research filename example from `24-03-26-` to `2026-03-26-` to match the YYYY-MM-DD format specification

### Changed
- Template version: 1.16.3 → 1.16.4

## [1.16.3] - 2026-03-25

### Fixed
- **H1**: `/execute-task` Phase 3.3 now runs affected tests (`*.test.*`, `*.spec.*`) as verification step 7 — test failures enter the self-repair loop
- **H2**: `/breakdown` agent assignment table expanded from 6 → 11 agent types — added db-engineer, api-designer, devops-engineer, migration-engineer, design-auditor
- **H3**: Standardized MEMORY.md entry format (`- **[AREA]**: [observation] _(Task N / Feature NNN)_`) across execute-task, fix, refactor, and verify commands
- **H4**: Unified spec branch/directory numbering in `/specify` — branch creation deferred to Phase 4 so both use the same NNN from `specs/` scan
- **H5**: `/verify` Phase 9 approval message no longer references non-existent `/commit` command
- **H6**: `/fix` Phase 6 code review loop limited to max 1 additional cycle when BLOCKED — prevents infinite fix→review loops
- **H7**: Standardized all date formats to ISO 8601 (`YYYY-MM-DD`) — removed `DD-MM-YY`, `DD-MM-YYYY HH:MM Ukrainian time` variants from plan, research, and clarify commands
- **H8**: Removed redundant Phase 3.3 from `/onboard` that tried to add already-existing `/onboard` entry to CLAUDE.md

### Changed
- Template version: 1.16.2 → 1.16.3
- Updated README.md, DEVELOPMENT-STATUS.md, CLAUDE.template.md, and storage-rules.md to reflect H1 (test execution) and H7 (date format) fixes

## [1.16.2] - 2026-03-25

### Fixed
- **C1**: Context handling pauses execution and prompts user-initiated compaction for heavy task loads instead of silently continuing
- **C2**: Commands now guard against empty `constitution.md` — prompts user to run `/constitute` first
- **C3**: Project mode detection uses `project-config.json` flag instead of re-counting files each time, preventing contradictory greenfield/existing behavior
- **C4**: `install.sh` no longer copies `settings.local.json` to target projects — file is project-owned, not part of template install
- **C5**: Replaced all 18 `git add -A` instances with scoped staging across `execute-task`, `fix`, `refactor`, and `verify` commands — prevents accidentally committing secrets/unwanted files
- **C6**: Pre-squash safety check added to all three workflow commands — verifies WIP commits haven't been pushed before `git reset --soft` to avoid rewriting shared history
- **C7**: `/constitute` now reads `constitution.template.md` and copies all `[universal]` sections (3.5–3.7, 4.1–4.3, 6.1–6.4) verbatim instead of regenerating them

### Changed
- Template version: 1.16.1 → 1.16.2

## [1.16.1] - 2026-03-25

### Changed
- Tech-writer agent model hardcoded to `sonnet` instead of `{{AGENT_MODEL}}` — docs generation doesn't need opus, sonnet is faster and cheaper
- `/release` command added for automating version bumps, changelog, and documentation updates in the template repo

### Fixed
- Artifact Storage tree in CLAUDE.md template showed `research/` nested under `specs/` — corrected to project root, matching `/research` command behavior since v1.13.0

## [1.16.0] - 2026-03-25

### Added
- `/setup-wizard` now saves **baselines** during generation (Steps 3.1.1 and 3.2.1)
  - CLAUDE.md baseline saved to `.claude/.baseline/CLAUDE.md`
  - Agent baselines saved to `.claude/agents/.baseline/[name].md`
  - Enables `update.sh` three-way merge immediately after setup — no bootstrap run needed

### Changed
- Template version: 1.15.0 → 1.16.0

## [1.15.0] - 2026-03-24

### Added
- **Configurable agent model** — `/setup-wizard` Question 8 asks preferred model for agents (default: `opus`)
  - All 14 agent templates now use `{{AGENT_MODEL}}` placeholder instead of hardcoded model
  - Stored in `.claude/project-config.json` (`AGENT_MODEL` key)
  - To switch models (e.g., when rate-limited): change `AGENT_MODEL` in `project-config.json` and re-run `/setup-wizard` or edit agent files directly
- **Three-way merge for agents and CLAUDE.md** — `update.sh` now uses `git merge-file` instead of section-merge or full replacement
  - Applies only the actual template diff (baseline → new) to current files
  - Preserves ALL project customizations: wizard-added framework-specific items, custom sections, manual edits
  - Baselines stored in `.claude/agents/.baseline/` and `.claude/.baseline/`
  - First update saves baselines (files unchanged); subsequent updates three-way merge
- **Placeholder validation** — `update.sh` validates no `{{PLACEHOLDER}}` remains after substitution; skips file if unresolved (prevents destroying working agents with raw placeholders)
- **Config validation** — `update.sh` warns when `project-config.json` values themselves contain raw `{{PLACEHOLDER}}` patterns
- `AGENT_MODEL` extraction in `update.sh` migration (reads `model:` from agent frontmatter, defaults to `opus`)

### Changed
- Templates (`.claude/templates/**`) no longer copied to target projects during update — removed from `templateOwned` patterns
- CLAUDE.md moved from section-merge to three-way merge (same approach as agents)
- Removed `sectionMerge` category from manifest (replaced by three-way merge)
- Template version: 1.14.0 → 1.15.0

### Fixed
- **Agents overwritten with raw `{{PLACEHOLDER}}`** — when `project-config.json` had broken values (e.g., `"PROJECT_PATHS": "{{PROJECT_PATHS}}"`), agents were destroyed. Now validates before writing.
- **Templates pushed to target projects** — `.claude/templates/**` was in `templateOwned`, causing raw template files to appear in target projects
- **CLAUDE.md custom sections deleted** — section-merge dropped user-added sections (e.g., `## Figma Plugin Architecture Notes`). Three-way merge preserves them.

## [1.14.0] - 2026-03-24

### Added
- **Commit Convention** section in CLAUDE.md template — consolidates all commit rules (format, attribution, general rules) in one place
- **AI attribution control** — `/setup-wizard` Question 7 asks whether commits should include Claude co-author attribution (`Co-Authored-By` trailer)
  - Default is **No** — no AI/Claude mention in commit titles, body, trailers, or git identity
  - Opt-in: appends `Co-Authored-By: Claude <noreply@anthropic.com>` to every commit
  - Stored in `CLAUDE.md` (Commit Convention > Attribution section) and `.claude/project-config.json` (`COMMIT_ATTRIBUTION` key)
- `COMMIT_ATTRIBUTION` placeholder in CLAUDE.md template, substituted by `/setup-wizard` based on user preference
- All commit-creating commands (`/execute-task`, `/fix`, `/refactor`, `/verify`, `/refresh-docs`) now reference the Commit Convention in CLAUDE.md for format and attribution rules
- `update.sh` migration extracts `COMMIT_ATTRIBUTION` from existing CLAUDE.md; defaults to no-attribution if section not found

### Changed
- Template version: 1.13.0 → 1.14.0

## [1.13.0] - 2026-03-24

### Changed
- `/research` command now displays the full research report in the console before saving
- `/research` now asks the user whether to save the report (previously auto-saved)
- Research reports moved from `specs/research/` to `research/` at project root
- Research file naming changed from `[topic-slug].md` to `DD-MM-YY-[topic-slug].md`
- Storage rules updated to reflect new research location and naming convention

## [1.12.0] - 2026-03-24

### Fixed
- **Critical: Agents broken after update** — `update.sh` copied raw `.template.md` files with unresolved `{{PLACEHOLDER}}` variables (e.g., `{{FRAMEWORK}}`, `{{LANGUAGE}}`) into `.claude/agents/`, destroying project-specific values. Now applies placeholder substitution using `.claude/project-config.json`
- **CLAUDE.md never updated** — was classified as project-owned so `update.sh` skipped it entirely. Template-owned sections (workflow commands, key rules, quality gates, artifact storage, session continuity) now update via section-based merge while project-specific sections (project overview, structure, commands, architecture, agent list) and user-added custom sections are preserved
- **Templates and manifest not synced** — `.claude/templates/**` and `.claude/template-manifest.json` were missing from `templateOwned` patterns, causing stale copies in target projects after update

### Added
- `.claude/project-config.json` — machine-readable file storing all template variable values, written by `/setup-wizard` (Step 3.8), read by `update.sh` for placeholder substitution during updates
- **Section-based merge** strategy in `update.sh` for files with mixed template/project ownership (CLAUDE.md)
  - Template-owned sections updated from latest template
  - Project-owned sections preserved from target
  - User-added custom sections appended
- **One-time migration** in `update.sh` — for existing projects without `project-config.json`, extracts values from `CLAUDE.md` and agent files automatically
- `perl` dependency check in `update.sh` (required for multi-line placeholder substitution)
- `/setup-wizard` Step 3.8 — writes `.claude/project-config.json` after generating all config files

### Changed
- `update.sh` now requires `perl` in addition to `jq`
- Template manifest: `.claude/templates/**` and `.claude/template-manifest.json` moved to `templateOwned`; `CLAUDE.md` moved from `projectOwned` to new `sectionMerge` category
- Command count: 14 (unchanged); template version: 1.11.0 → 1.12.0 → 1.13.0

## [1.11.0] - 2026-03-23

### Added
- `/research` command — lightweight feasibility check for vague ideas before `/specify`
  - Investigates the codebase for related patterns, code, and infrastructure
  - Signal-based external research — only web searches when the idea involves new libraries, integrations, or unfamiliar tech
  - Outputs a concise report to `specs/research/[topic-slug].md` with verdict, approaches, complexity assessment, and concrete next-step recommendation
  - No code modifications, no branches, no commits — purely investigative
  - Sits before `/clarify` in the workflow: `/research` (optional) → `/clarify` (optional) → `/specify`
- `specs/research/` directory in storage rules for research report artifacts

## [1.10.0] - 2026-03-23

### Added
- `/refresh-docs` command — lightweight documentation refresh that targets only changed files
  - Uses git delta to detect source files changed since docs were last updated
  - Invokes tech-writer in new **Refresh Mode** — scoped to changed files, not full codebase scan
  - Supports `--since <commit>`, `--module <name>`, and `--all` (delegates to `/onboard`) flags
  - Captures both committed and uncommitted changes
  - Scoped `git add` (only doc-related files) instead of `git add -A`
  - Includes verification (tsc + lint on changed source files) and memory update phases
- **Refresh Mode** in tech-writer agent template — third operating mode alongside Normal and Onboarding
  - Reads only changed files grouped by module
  - Updates both inline docs (JSDoc/docstrings) and `docs/` folder
  - Cleans up stale doc references for removed public APIs
- `/verify` **"Fix docs now"** triage option — invokes tech-writer directly for documentation-only issues, bypassing `/fix`
  - Documentation gaps flagged during verification now record specific file paths and API names
  - Phase 10.4 summary includes "Fix docs now" count
- `/plan` now reads `docs/` during Phase 0 research — `docs/architecture.md`, `docs/features/*.md`, and `docs/api/*.md` for architectural context
- `/plan` output now includes **Documentation Impact** section — declares which docs will need updating, giving `/execute-task` Phase 5 better targets

### Changed
- `/execute-task` Phase 5 (Documentation Update) **rewritten** with stronger enforcement
  - Structured prompt template for tech-writer invocation (mirrors Phase 3.2's execution agent pattern)
  - New Phase 5.1: Post-Doc Verification — checks `git diff` for new public exports and verifies inline docs exist
  - New Phase 5.2: Commit — doc changes get their own `[WIP]` commit
  - Re-invokes tech-writer if public APIs lack documentation
- `/execute-task` compact preservation lists updated — all 3 instances (moderate, heavy, auto-compact) now include item (6): Phase 5 documentation obligation
- `/execute-task` IMPORTANT RULES: new rule 10 — "Documentation is non-negotiable" (equivalent to skipping verification)
- `/fix` now includes Phase 7.5: Documentation Update (Conditional) — launches tech-writer when public API signatures or user-facing behavior changed
  - Report template includes `**Documentation**:` line
  - Tech-writer receives `docs/` folder structure for context
- `/refactor` now includes Phase 7.5: Documentation Update (Conditional) — launches tech-writer when public API signatures, import paths, or architecture changed
  - Report template includes `**Documentation**:` line
  - Tech-writer receives `docs/` folder structure for context
- `/plan` IMPORTANT RULES: new rule 8 — "Read docs before planning"
- Command count: 13 → 14

## [1.9.0] - 2026-03-23

### Added
- **Cross-task contracts** in `/breakdown` and `/execute-task` — prevents silent error compounding between sequential tasks
  - Each task file now has a `## Contracts` section with `### Expects` (preconditions) and `### Produces` (postconditions)
  - `/breakdown` generates contracts during task creation with concrete, grep-verifiable conditions (exports, interfaces, function names — never line numbers)
  - `/execute-task` Phase 2 verifies preconditions before execution — stops with upstream tracing if a contract is violated
  - `/execute-task` Phase 3.3 verifies postconditions after execution — feeds into the existing self-repair loop on failure
  - Agent prompt includes postconditions as "What This Task Must Produce" so the agent is aware of verification expectations
  - Completion notes and reports now include contract verification results
- **Contract consistency check** in `/breakdown` — after generating all tasks, verifies every "Produces" is consumed by a downstream "Expects" and every "Expects" traces to an upstream "Produces" or existing codebase state
- **Review checkpoint gates** in `/execute-task` multi-task mode — auto-placed pause points at convergence (2+ dependencies), layer boundary crossings (domain → presentation), and high-risk tasks
  - New `**Review checkpoint**: Yes/No` field in task file headers
  - At checkpoints: user sees preceding tasks' contract results and chooses Continue / Review (git diff) / Pause
  - `/breakdown` README.md now includes a Review Checkpoints table
- Storage rules updated with Contracts section and Review checkpoint field in task file format

## [1.8.0] - 2026-03-22

### Added
- **Build verification step** in all workflow commands that run post-execution checks
  - Runs the project's actual build command (e.g., `npm run build`, `next build`, `vite build`) after tsc and lint
  - Catches bundler-specific failures that `tsc --noEmit` alone misses: import resolution, asset processing, SSR/SSG errors, ESM/CJS incompatibilities, unexpected token issues
  - Gated on `Build Command` field in CLAUDE.md — skipped if not configured or set to `N/A`
  - Included in self-repair loop — build errors get auto-fixed (up to 3 attempts) like tsc/lint errors
  - Added to: `/execute-task` (Phase 3.3), `/verify` (Phase 3), `/fix` (Phase 5), `/refactor` (Phase 5)
- `**Build Command**` field in CLAUDE.md template — stores the actual build command (distinct from `Build Tool` which is just the tool name)
- `/setup-wizard` now detects and populates `{{BUILD_COMMAND}}` — auto-detects from package.json `scripts.build`, Makefile, Go/Rust project conventions

### Changed
- Verification reports in all commands now include `Build: PASS/FAIL/SKIP` line
- CLAUDE.md template references updated: `(tsc, lint, ...)` → `(tsc, lint, build, ...)`
- Automated Guards section updated: `tsc + lint` → `tsc + lint + build`

## [1.7.0] - 2026-03-20

### Added
- `/report-bug` command — standalone bug reporting that creates structured bug files in `bugs/`
  - Accepts description, optional `--file` path, optional `--severity` (defaults to Warning)
  - Creates `bugs/NNN-short-description.md` with status lifecycle (Open → In Progress → Fixed)
  - Suggests `/fix bugs/NNN-xxx.md` or `/specify` for resolution
- `bugs/` directory — lightweight bug backlog at project root (parallel to `specs/` and `docs/`)
  - Sequential numbering (001, 002, ...) with kebab-case descriptions
  - Structured format: status, severity, source, description, file(s), evidence, fix notes
  - Created by `/report-bug` (manual) or `/verify` Phase 10 triage (automated)
  - Resolved by `/fix bugs/NNN-xxx.md` which updates status to Fixed
- `/verify` Phase 10: Issue Triage — after presenting the verification report, lets user decide per-issue what to do
  - Per-issue options: "fix now" (chains into `/fix`), "report for later" (creates bug file), "skip"
  - Batch shortcut when >5 issues: "report all remaining for later" to avoid tedious per-issue prompts
  - Bug files created for all triaged items (including "fix now") for tracking regardless of outcome
  - Only activates on NEEDS WORK verdict with Critical/Warning issues
- `/fix` now accepts bug file paths as input: `/fix bugs/003-null-check.md`
  - Phase 1.0 (Input Detection): reads bug file, extracts description and file(s), updates status to In Progress
  - Phase 8.1.5 (Update Bug File): after successful fix, marks bug as Fixed with date and fix notes
  - Existing usage (`/fix "description"`) unchanged — fully backward-compatible

### Changed
- Storage rules updated with Bug Report Rules section (naming, format, lifecycle, creation/resolution)
- Template manifest updated with `report-bug.md` (template-owned), `bugs/**` (project-owned), `bugs/.gitkeep` (copy-if-missing)
- `install.sh` now copies `bugs/` directory to target during installation
- Command count: 11 → 12

## [1.6.0] - 2026-03-19

### Changed
- `/plan` Phase 0 (Research) revamped with signal-based evaluation
  - Codebase research always runs; deep research (web search) only triggers when complexity signals are detected
  - Six signal categories: external libraries, third-party integrations, architectural forks, greenfield patterns, performance constraints, unfamiliar technology
  - Deep research compares 2-3 alternatives with pros/cons for each signal
  - Research output saved to `specs/[feature]/research.md` only when signals found; skipped for simple features
  - Reduces unnecessary web searches on simple features where codebase context is sufficient

## [1.5.0] - 2026-03-19

### Added
- `/fix` command — lightweight bug-fixing workflow for small, localized bugs (1-5 files)
  - Diagnosis phase with **runtime-debugger** agent for runtime errors or manual tracing for logic bugs
  - Hard gate on diagnosis — user must confirm root cause before any code changes
  - Scope guard — automatically recommends `/specify` if bug affects more than 5 files
  - **code-reviewer** agent runs on all changed files after fix
  - **qa-engineer** agent assesses test impact and writes regression tests when warranted
  - Self-repair loop (up to 3 attempts) on verification failure — same pattern as `/execute-task`
  - Full crash recovery with WIP markers and git checkpoints
  - Wrapper mode awareness (Source Root scoping, isolation checks)
  - Memory update for bug patterns and pitfalls
- `/refactor` command — focused code refactoring workflow for behavior-preserving restructuring (1-5 files)
  - Supports both IDE-injected context (active file/selection from WebStorm) and manual file path with optional line range
  - Structured analysis phase scans 9 refactoring categories: long functions, deep nesting, SOLID/DRY violations, type safety, naming, dead code, pattern mismatches, complexity
  - Auto-selects execution agent based on file layer (**architect**, **frontend-engineer**, or **backend-engineer**)
  - Hard gate on proposal — user sees detailed before/after for each opportunity and can approve all, specific items, or cancel
  - Partial approval supported — approve individual refactoring actions by number
  - **code-reviewer** agent validates refactored code
  - **qa-engineer** agent verifies tests still pass (behavior-preserving guarantee)
  - Self-repair loop, crash recovery, constitution enforcement, and memory updates — same patterns as `/fix`

### Changed
- `/specify` now auto-creates a `spec/NNN-short-desc` branch when invoked on the default branch
  - Incremental numbering based on existing `spec/*` branches (local + remote)
  - Short description (2-3 words kebab-case) generated from the feature description
  - Skips if already on a `spec/*` branch; asks user if on any other non-default branch
- Command count: 9 → 11
- CLAUDE.md template updated with `/fix`, `/refactor`, and `/specify` branch creation in workflow commands section
- Template manifest updated to include `fix.md` and `refactor.md` as template-owned

## [1.3.0] - 2026-03-19

### Added
- **Wrapper mode** — setup wizard now detects nested git repos and offers wrapper mode for projects where AI usage must be invisible to the client
  - Wrapper repo holds all Claude artifacts (`.claude/`, `CLAUDE.md`, `constitution.md`, `specs/`, `docs/`)
  - Inner folder is the client's separate git repo with zero Claude traces
  - Auto-detection: scans for nested `.git/` directories at depth 1
  - New `{{SOURCE_ROOT}}` and `{{WRAPPER_MODE_SECTION}}` placeholders in CLAUDE.md template
  - New `{{WORKSPACE_MODE}}` placeholder in memory template
  - Inner project folder automatically added to wrapper's `.gitignore`
  - Git auto-commits apply to wrapper repo only; source code commits are manual
- All 9 commands now read Source Root from CLAUDE.md and scope source scanning accordingly
- `/execute-task` Phase 3.3 includes wrapper isolation check (no Claude artifacts inside Source Root)
- `install.sh` now supports `--wrapper` flag for pre-configuring wrapper mode during installation

### Changed
- `/setup-wizard` Step 0 is now Workspace Mode Detection; original greenfield detection moved to Step 0.5
- `/constitute` scans Source Root instead of workspace root when in wrapper mode
- `/onboard` uses Source Root as starting point for tree scan
- Settings template type-check command prefixed with `cd SOURCE_ROOT &&` in wrapper mode

## [1.2.0] - 2026-03-19

### Added
- `/execute-task` self-repair loop — when post-execution verification fails (tsc, lint, done-conditions), automatically launches a repair agent to fix errors (up to 3 attempts) before stopping
- `/execute-task` multi-task arguments:
  - `1,3,5` — execute specific tasks sequentially
  - `1-5` — execute a range of tasks
  - `all` — execute all pending tasks in active feature
- Phase 8 (Multi-Task Continuation) — chains task cycles, checks dependencies between tasks, produces batch summary
- Auto-compact in multi-task mode — at heavy context load (6+ tasks), automatically compacts without asking

### Changed
- `/execute-task` Phase 3.3 now includes self-repair before escalating to user
- Important Rules updated: "one task at a time" → "one task per cycle", added self-repair and hard-stop rules
- Context hygiene rule updated: auto-compact at heavy load in multi-task mode

## [1.1.0] - 2026-03-19

### Added
- `/onboard` command — deep codebase scan and documentation generation for existing projects
  - Delegates all scanning and writing to the tech-writer agent in onboarding mode
  - Context-safe: uses subagent parallelism, smart extraction, and fixed-size output contracts
  - Size-based scan strategies: direct (< 50 files), subagent-per-module (50-200), two-pass (200-1000), sample-based (1000+)
  - Generates real `docs/` content: `overview.md`, `architecture.md`, `features/*.md`, `api/*.md`
  - Enriches `.claude/memory/MEMORY.md` with module boundaries, dependency warnings, and complexity areas
  - Run once after `/constitute` for existing projects

### Changed
- Tech-writer agent template now supports two operating modes: Normal (task docs) and Onboarding (deep scan)
- Workflow updated: `/setup-wizard` → `/constitute` → `/onboard` → `/clarify` → `/specify` → ...
- `/constitute` now recommends `/onboard` as next step for existing projects
- `/setup-wizard` next steps mention `/onboard` for existing projects
- `/execute-task` Phase 1.2 clarifies that `docs/` is populated by `/onboard` for existing projects
- CLAUDE.md template updated with `/onboard` in workflow diagram and command list
- Template manifest updated to include `onboard.md` as template-owned

## [1.0.0] - 2026-03-17

### Added
- 8 workflow commands: setup-wizard, constitute, clarify, specify, plan, breakdown, execute-task, verify
- 14 specialized agent templates (code-reviewer, qa-engineer, runtime-debugger, tech-writer, frontend-engineer, backend-engineer, architect, db-engineer, devops-engineer, design-auditor, api-designer, performance-analyst, security-reviewer, migration-engineer)
- 6 configuration templates (CLAUDE.md, constitution, spec, memory, settings, storage-rules)
- MCP server integrations (Context7, Chrome DevTools)
- Hard gates at every workflow phase transition
- PostToolUse hooks for automated type checking
- Persistent memory system
- Session continuity via fixed-size sliding window
- Crash recovery with WIP checkpoints
- Greenfield project support
- Template update system (update.sh) with manifest-based file categorization
- install.sh for fresh project installation