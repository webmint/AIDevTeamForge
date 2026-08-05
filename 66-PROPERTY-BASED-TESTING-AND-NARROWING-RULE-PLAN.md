# 66 — Property-Based Testing for Pure Builders + Shared-Code-Narrowing Rule

**Status:** PHASES 0–4 SHIPPED 2026-08-03 (working tree). D1–D7 ratified at build (maintainer's "implement 66" go = Phase-0 sign-off on the recorded leanings). Only Phase 6 (testForge20 e2e, user-driven HARD GATE) remains; Phase 5 stays DELIBERATELY ABSENT. **Build deviations from this draft, all reviewer-driven:** (1) the verb's missing-handoff behavior was reconciled with `/breakdown` PHASE 0a.5's tolerated no-handoff path via a `plan.md` heading-presence fallback — never-declared → `skip` exit 0; declared-but-handoff-less → fail-closed with a `plan_helper finalize-handoff` remedy (a HIGH instruction-review finding; the pure fail-closed contract drafted below is superseded); (2) constitution §-number citations were replaced with concept-name citations per authoring rule F3; (3) prose-level Narrowing enforcement was added beyond the draft (a `/plan` PHASE 2.5 step-7 trace + an `architect.md` Rule-9 Narrowing forcing step) — still NOT the deferred mechanical detector; (4) `verify-universal-defaults` needed NO code change (it parses the live canonical `src/constitution.md`; only tests moved, §3.6 → 8 rules with a `>= 8` floor). See the repo-root `CLAUDE.md` plan-66 entry for the full shipped inventory.
**Type:** BUILD plan (WI-1, test-lane mechanization) + CONSTITUTION plan (WI-2, one prose rule, forcing-function deferred).
**Branch:** `develop-2.0-init`.
**Created:** 2026-08-01, seeded from the five-solution MIG-2957 comparison on `db-cse-ui-strata` (evidence: `cse-strata-ws-forge/research/2026-07-31-mig-2957-solution-comparison.md` in the mintEnvoy wrapper workspace — five independently-built solutions to one ticket, incl. a Kiro spec set, judged by empirical probe tests).
**Rewritten:** 2026-08-03 (v2) — the v1 believed-state checklist was verified against `src/`; two findings invalidate v1's leverage story and re-anchor the WI-1 trigger (see "Verified state"). Phases now name their mandatory agent loops per repo convention.

---

## Problem

Two gaps the MIG-2957 comparison exposed; everything else it surfaced the framework already has (EARS enforcement in `_specify/_schema.py`, AC↔task traceability walkers in `/breakdown`, AC→IR formalization + solver in `/spec-check` per plan 62, scope-fidelity intake per plan 18).

**WI-1 — no property-based testing lane.** Zero hits for `fast-check` / `hypothesis` / property-based anywhere in `src/` (re-verified 2026-08-03; the only "hypothesis" grep hits are `_discover`'s intake-classification vocabulary). Every test the pipeline produces or demands is example-based. Pure filter/builder/mapper functions — deterministic, no I/O — are exactly where example tests structurally under-cover:

- The comparison's winning solution shipped 25 example tests and still had zero input-space coverage ("for ANY query string, the OR clause has exactly N members" was asserted for `'acme'` only).
- A real 2024 defect in the same target repo is the canonical catch: `String.prototype.search(userInput)` treats the query as a REGEX — `(`, `[`, `+` in a search box break matching. Example tests with plain-word fixtures can never find this; a 100-iteration property run with special-char arbitraries finds it in seconds.
- The Kiro spec in the comparison PROPOSED exactly this (fast-check, "Property 1: for any non-empty string…") and then lost it to its own `*`-optional task escape hatch — the shipped code contains no property tests. Lesson: **a property lane that is optional evaporates; it must be gated** (plan 41's orphan discipline: a declared property target with no covering test task is an ORPHANED PROPERTY).

**WI-2 — the constitution cannot see semantic blast radius.** The comparison's mechanism-level lesson: the winning solution narrowed shared-code behavior via a *layer-wide policy* inside a shared service ("SHIP_TO tabs never search address fields") when a *caller-scoped opt-in* had identical coverage and zero latent risk to unnamed callers. Current `src/constitution.md` §3.6 KISS (`src/constitution.md:114-117` — "simplest solution", no speculative layers) actively REWARDS the layer-wide form (fewer touch points, no new API surface) and nothing pushes back. Grep confirms (2026-08-03): no caller-scoped / blast-radius / narrowing language anywhere in `src/constitution.md`.

## Why it matters

- WI-1: pure builders are the highest-density defect site in filter/query-construction code (the MIG-2957 ticket *was* one), and the cheapest place to run properties (no mocks, no I/O, deterministic). The gate makes the lane non-optional; generation is an optimization on top.
- WI-2: "smallest API diff" vs "narrowest semantic blast radius" is a real fork the pipeline currently resolves silently, always toward the former. One prose rule makes it a named, reviewable decision. Cheap, high leverage.

## Verified state (2026-08-03 — replaces v1's believed-state checklist)

Verified against `src/` this session; re-run the greps at Phase 0 start only if `src/` changed since.

- **[VERIFIED] Zero PBT presence in `src/`.** Grep for `fast-check|hypothesis|property-based` — no test-lane hits.
- **[VERIFIED — INVALIDATES v1 premise] The plan-62 IR does NOT persist.** The formalizer IR lives only in run-scoped scratch `${TMPDIR:-/tmp}/forge-spec-check` (`src/commands/spec-check/main.md:43` — "scratch state for one run"); the only durable artifacts are the human-facing `spec-check.md` (`_spec_check/_report.py::write_spec_check_report`) and, on a matching REVISE-SPEC pick, `spec-check-seed.json`. v1's "the IR is, almost verbatim, the generator seed" claim was half-false: the front half exists for one run, then evaporates. Any IR-consuming stub generation (v1 Option B) requires NEW persistence work first.
- **[VERIFIED — INVALIDATES v1 trigger] `/spec-check` is opt-in advisory** (plan 62 D14; bracketed in the `src/CLAUDE.md` workflow chain). A property lane conditioned on "plan-62 IR non-empty" fires only when the user opted into `/spec-check` — most features skip it, so the v1 Option-A trigger reproduces Kiro's evaporation one level up. The trigger must not depend on `/spec-check` having run.
- **[VERIFIED] `qa-engineer` dedicated test-authoring row exists** in the `/breakdown` Agent Assignment table (`src/commands/breakdown/main.md:254`, emission conditions `:263` — plan 41 WI-1, D2 model (a): dedicated task on coverage-gap / test-heavy-AC flag). The executor for a property-test task already has a routing row; WI-1 extends its emission conditions, it does not create the row.
- **[VERIFIED] The `/breakdown` PHASE 3.5 gate family is the home for the orphan check** — `verify-contract-chain` / `verify-ac-coverage` / `verify-agent-roster` / `verify-manifest-present` (`src/commands/breakdown/main.md:400-433`), each a `breakdown_helper` verb that HARD-halts and is folded into `finalize-handoff` as a chokepoint (plans 09/38/42). v1's "plan-41-style reachability walker" framing was the wrong home: plan 41's walker is MAINTAINER-side (`scripts/lib/`); this check is CONSUMER-runtime → `breakdown_helper` verb, plan-38/42 shape.
- **[VERIFIED] Stack detection exists.** Per-stack test frameworks are captured at `/configure` — `.devforge/project-config.json` carries `TESTINGS` + per-package `PACKAGE_STACKS` records (incl. `test_command`), and constitution §3.4 renders `{{TESTING}}` per stack (`src/constitution.md:55-58`). The fast-check-vs-hypothesis choice reads existing config; no new capture step.
- **[VERIFIED] WI-2 insertion point.** §3.6 Design Principles [universal] at `src/constitution.md:100-119`; the `*Backed by*` forcing-function citation pattern (`:96-98`, `:119`) is the established shape if a detector is ever added. Universal-section text is drift-tracked by `constitute_helper forge-internal:verify-universal-defaults` — any §3.6 amendment MUST update the canonical defaults it diffs against, in the same change.
- **[SPOT-CHECK at build, low risk] `src/agents/qa-engineer.md`** charter is pure test-writer (plan 15 Phase 2); confirm its body needs no property-test vocabulary before Phase 3 briefs cite it.

## Design (the fork, resolved by the verified state)

**Trigger = architect-named pure-builder targets, declared at `/plan`.** Not `/spec-check` IR presence (opt-in + scratch-only — see Verified state). The architect consultation `/plan` already runs (plan 02 Step 8) names the feature's pure builder/filter/mapper targets in a dedicated `plan.md` section; `plan_helper finalize-handoff` parses that section into `BreakdownSeeds` (`_plan/handoff_schema.py:242`) as a new `pure_builder_targets` field, so `/breakdown` receives them mechanically (producer-owns-shape). No targets named → lane silent for that feature; no inference, no heuristic purity detection (v1 OQ-1 resolved: architect declares, walker only checks that *declared* targets got covered).

**Gate = `breakdown_helper verify-property-coverage`.** The 5th member of the PHASE 3.5 family: every `pure_builder_targets` entry must be covered by a property-test task (the qa-engineer dedicated row); an uncovered target = ORPHANED PROPERTY → exit 2, HARD-halt, no bypass, folded into `finalize-handoff` as a chokepoint (plan 38/42 shape exactly).

**Options disposition (v1 A/B/C/D restaged):**
- **Option A (gate + human-authored tests) — BUILD NOW**, on the architect-named trigger above.
- **Option B (IR→stub generation) — DEFERRED behind an explicit prerequisite:** persist the formalizer IR (a durable `specs/[feature]/spec-check-ir.json` or equivalent) — new plan-62-side work this plan does not contain. Do not build B first; the gate is the part with teeth (see Context for next session).
- **Option C (instruction-only) — REJECTED baseline.** Kiro's `*`-optional shape; empirically evaporates.
- v1 Option D ("A then B") survives as: A is this plan; B is a follow-on gated on IR persistence + observed task volume.

## Open questions (Phase 0 ratification input)

- OQ-2 (unsupported stacks): v1 stack matrix = fast-check (TS/JS via the package's test framework) + hypothesis (Python/pytest). A `PACKAGE_STACKS` entry with no mature PBT lib → graceful skip with a recorded reason in the task file (honest-skip, plan-62 formalizer precedent), never silence.
- OQ-3 (seed policy): pinned seed in the test command (reproducible, weaker exploration) vs random seed + failure-seed logging (stronger exploration, replay needs plumbing). Leaning: pinned default seed + the runner's failure-seed reporting where the lib supports it. Interacts with plan 59's reproducibility stance.
- OQ-4 (property-tag format): adopt a `Property N:` tag in task/test text so `/verify` could walk property↔AC coverage mechanically later? Leaning: defer the `/verify` walk (WI-1 does not change `/verify` — a failing property test is an ordinary red test in the existing blocker path; the orphan case is breakdown-side); adopt the tag format now so the walk is possible without retrofit.
- OQ-5 (WI-2 placement): §3.6 amendment vs new §6.x entry. Draft rule text: *"When RESTRICTING existing behavior of shared code, prefer a caller-scoped opt-in over a layer-wide policy change; a broadened rule inside a shared service MUST name every current caller it affects, in the plan."* Leaning §3.6 (it is the section whose KISS text creates the bias). Forcing-function DEFERRED (prose-first v1, plan-18 Step-4 precedent) — mechanizing "is this narrowing shared behavior?" is an unsolved detector; do not block the rule on it.

## Phases

Every `main.md` / agent / constitution edit routes through **instruction-author → instruction-reviewer**, plus **claude-code-guide** for files that ship into a consumer's `.claude/` (command specs, agent files). Every helper change routes through **python-engineer → python-reviewer**, test-first. No phase is exempt.

- **Phase 0 — Ratify.** Maintainer sign-off on D1–D7 (below), which fold in the OQ-2/3/4/5 leanings. The verified-state table above replaces the v1 checklist; nothing further to verify unless `src/` moved.
- **Phase 1 (WI-2 — independent, small, ships regardless of WI-1).** Constitution rule lands in `src/constitution.md` per OQ-5; `/plan`'s spec (`src/commands/plan/main.md`) names the mechanism-choice decision point (when a plan restricts shared-code behavior, record the caller-scoped-vs-layer-wide choice + affected callers); the `verify-universal-defaults` canonical defaults updated in the same change; CHANGELOG + docs reconciled. Loops: instruction-author → instruction-reviewer + claude-code-guide (plan/main.md ships to `.claude/`); python-engineer → python-reviewer pass on the canonical-defaults constant edit.
- **Phase 2 (WI-1 producer — target declaration).** `/plan`: architect consult names pure-builder targets → dedicated `plan.md` section; `_plan/handoff_schema.py` `BreakdownSeeds` grows `pure_builder_targets` (backward-compatible: absent → empty, old handoffs unaffected); `plan_helper finalize-handoff` parses the section. Loops: python-engineer → python-reviewer (schema + parser + tests, round-tripped via the real producer); instruction-author → instruction-reviewer + claude-code-guide (`plan/main.md` + the architect consult prompt; `src/agents/architect.md` only if its consult contract needs the vocabulary).
- **Phase 3 (WI-1 consumer — gate).** `/breakdown`: property-test task emission wired to the existing qa-engineer dedicated row (`main.md:254` emission conditions extended: named pure-builder targets present → property-test task MUST exist); new `breakdown_helper verify-property-coverage <tasks-dir> <plan-handoff-path>` verb (ORPHANED PROPERTY → exit 2) wired at PHASE 3.5 as the 5th gate + folded into `finalize-handoff` (plan 38/42 shape: HARD-halt, no bypass, offender list on stdout). Loops: python-engineer → python-reviewer; instruction-author → instruction-reviewer + claude-code-guide.
- **Phase 4 (WI-1 — stack matrix + seed policy).** qa-engineer property-task brief template: lib selection read from `PACKAGE_STACKS` / `TESTINGS` (fast-check / hypothesis per OQ-2), ≥100 iterations, special-char + unicode arbitraries, seed policy per OQ-3, dev-dependency install step, graceful-skip path with recorded reason for unsupported stacks. Loops: instruction-author → instruction-reviewer + claude-code-guide (task-template / brief text; agent-file edit if qa-engineer body needs the property vocabulary — see spot-check).
- **Phase 5 — DELIBERATELY ABSENT.** IR-stub generation (old Option B) is NOT in this plan; it requires plan-62-side IR persistence first and is a follow-on plan gated on Phase 3's observed task volume.
- **Phase 6 — testForge20 e2e (user-driven HARD GATE).** A feature whose plan names ≥2 pure-builder targets: confirm the property-test task is born, tests run ≥100 iterations incl. special-char/unicode arbitraries, `verify-property-coverage` fails a breakdown that drops the task, and an unsupported stack records an honest skip.

## Decisions to ratify (Phase 0)

- D1: Option A now on the architect-named trigger; Option B deferred to a follow-on plan behind IR persistence. (v1's D-leaning, re-anchored.)
- D2: Purity-target declaration = architect names targets at `/plan`; carried mechanically via `BreakdownSeeds.pure_builder_targets`; walker checks declared targets only, no inference.
- D3: Seed policy (OQ-3).
- D4: WI-2 rule text + placement (OQ-5) — forcing-function explicitly deferred; canonical-defaults sync is part of the same change.
- D5: Property-tag format now, `/verify` walk deferred (OQ-4).
- D6: Gate home = `breakdown_helper` verb + `finalize-handoff` chokepoint (consumer-runtime, plan-38/42 family) — NOT a maintainer-side `scripts/lib/` walker.
- D7: Unsupported-stack handling = graceful skip with recorded reason, never silence (OQ-2).

## Dependencies + related

- Plan 62 (SMT requirements consistency) — sibling, NOT a dependency anymore: its IR is scratch-only and `/spec-check` is opt-in (see Verified state). Becomes a dependency only for the deferred stub-generation follow-on.
- Plan 67 (caller-enumeration gate mode-decouple) — SIBLING from the same MIG-2957 comparison; owns the /research-side mechanical enumeration gate + the research-handoff caller carry that gives WI-2's "name every current caller" rule its typed upstream source; see 67's "Division of labor vs plan 66".
- Plan 41 (agent-executor reachability) — orphan-discipline precedent; also shipped the qa-engineer dedicated row WI-1 reuses.
- Plans 38/42 (roster + manifest PHASE 3.5 gates) — the exact verb + chokepoint shape `verify-property-coverage` copies.
- Plan 02 (`/plan` redesign) — the architect-consult + `finalize-handoff` machinery Phase 2 extends.
- Plan 15 (agent standardization) — `qa-engineer` as pure test-writer, the executor.
- Plan 18 (scope fidelity) — prose-first-v1 precedent for WI-2's deferred detector.
- Plan 34 (verify hygiene) — polyglot stance constrains the stack matrix.
- Plan 59 (LLM-verdict reproducibility) — sibling determinism concern for OQ-3.
- External evidence: `cse-strata-ws-forge/research/2026-07-31-mig-2957-solution-comparison.md`.

## Context for next session

The trap in WI-1 is building the stub generator first because the IR makes it look easy — it is now VERIFIED to be worse than v1 feared: the IR does not even persist past the `/spec-check` run, and `/spec-check` itself is opt-in, so a generator would have no durable input for most features. The gate (`verify-property-coverage` on architect-named targets) is the part with teeth; generation is a follow-on plan. Kiro had the generation idea and no gate, and shipped zero property tests — that ordering is the whole lesson. WI-2 is deliberately tiny: one paragraph of constitution text plus a `/plan` touchpoint plus the canonical-defaults sync; do not let it grow a detector it doesn't need yet.

## When resuming work

1. Read this file in full + `src/commands/breakdown/main.md` PHASE 3.5 + gate verbs (`:254`, `:400-433`) + `_plan/handoff_schema.py` (`BreakdownSeeds`) + `src/agents/qa-engineer.md`.
2. If `src/` changed since 2026-08-03, re-run the Verified-state greps before trusting the table.
3. Ratify D1–D7 before drafting any schema, verb, or template code.

## Verify

- Phase 0 done = D1–D7 ratified + OQ leanings confirmed/overridden + WI-2 text agreed, recorded here.
- Phase 1 (WI-2) done = rule in `src/constitution.md`, canonical `verify-universal-defaults` baseline updated in the same change (drift detector green), `/plan` names the mechanism-choice decision point, docs reconciled.
- Phase 2 done = `BreakdownSeeds.pure_builder_targets` field + `finalize-handoff` parser shipped with tests (round-tripped via the real producer), old handoffs without the field parse unchanged, `/plan` spec renders the architect-named targets section.
- Phase 3 done = qa-engineer row emission conditions extended, `verify-property-coverage` exits 2 on an uncovered declared target at PHASE 3.5 AND via the `finalize-handoff` chokepoint, offender list on stdout, tests green.
- Phase 4 done = property-task brief template reads lib selection from `PACKAGE_STACKS`/`TESTINGS`, encodes seed policy (D3) + ≥100 iterations + special-char/unicode arbitraries + the D7 graceful-skip path.
- Phase 6 (e2e, user-driven) done = on a plan naming ≥2 pure-builder targets, the property-test task is born, tests run ≥100 iterations incl. special-char/unicode arbitraries, a breakdown that drops the task fails the gate, and an unsupported stack records an honest skip.
