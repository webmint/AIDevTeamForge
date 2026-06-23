# 36 — GRILL UNIVERSAL RE-ENTRY (REVISE-PLAN → `/plan` consumer)

**Status:** IN PROGRESS — Phases 1, 2, 3a BUILT + green (402 tests pass). On `develop-2.0-init`. Remaining: Phase 3b (`grill/main.md` + `report-format.md` spec wiring), Phase 4 (`/plan` consumer block), Phase 5 (docs reconcile); Phase 6 e2e is user-driven. Discovered 2026-06-23 alongside plan 35: across two mintEnvoy `/grill` runs BOTH produced confirmed findings, so REVISE-PLAN is the common outcome — and it has no machine-readable path back into `/plan`. OQ-1 (string vs structured `carried_findings`) is RESOLVED (a): `carried_findings` stays `List[str]`.

## Problem

`/grill` runs after `/plan`. Its disposition routes remediation four ways. Three dispositions already have a structured path; REVISE-PLAN does not:

| Disposition | Structured output today | Consumer today |
|---|---|---|
| PROCEED | none needed | → `/breakdown` |
| **REVISE-PLAN** | **none** | **— (manual hand-transcription from `grill.md` prose)** |
| RE-ENTER-UPSTREAM | `grill-seed.json` (`ReEntrySeed`) | `/research` / `/discover` / `/specify` |
| KILL | none needed | abandon |

`/grill` computes a confirmed/dismissed/contested partition mid-run, then sweeps its scratch WORKDIR at the end of the run (`src/commands/grill/main.md:349`, an `rm -rf` of `${TMPDIR:-/tmp}/forge-grill`) — only the human-readable `grill.md` prose survives. So on REVISE-PLAN the structured confirmed findings exist mid-run and are then destroyed, forcing the human to re-read prose and hand-patch `plan.md` (or re-prompt `/plan` blind). With confirmed findings on every grill run observed so far, this path is hit every run, not rarely.

## North star (user directive 2026-06-23)

**All upstream commands must be able to consume the grill object.** The pipeline commands upstream of `/grill` are `/research`, `/discover`, `/specify`, and `/plan`. Three already consume `ReEntrySeed`; this plan adds the fourth (`/plan`), completing universal consumption. ONE object (`ReEntrySeed`); its `target_stage` field routes it to the single command that owns the flaw's root.

## Decisions (proposed — sign off at Phase 0)

- **D1 — Extend the existing `ReEntrySeed`; do NOT fork a second schema.** "All consume the grill object" means one object. Add `"plan"` to `SEED_TARGET_STAGES` (`src/devforge/lib/_grill/seed_schema.py`, pre-plan baseline `("spec", "discovery", "research")`; now `("spec", "discovery", "research", "plan")` as of Phase 1 — see D7 for why this is distinct from `_report.py`'s `_UPSTREAM_STAGES`). REVISE-PLAN emits a `ReEntrySeed` with `target_stage="plan"`, symmetric to RE-ENTER-UPSTREAM emitting a seed for the upstream stages.
- **D2 — Reuse the existing payload field shape for plan-revision findings.** The existing fields map onto a plan revision: `prior_conclusion` = the flawed plan decision, `invalidating_evidence` = the grounded grill finding, `must_satisfy` = the fix, `carried_findings` = the remaining findings in a multi-finding set. Reuse is the point — no new fields for the `"plan"` target. (Whether `carried_findings` stays `List[str]` or becomes a typed record list is OQ-1 below, not part of D2.)
- **D3 — `/plan` consumption is conditional / additive / inert (the existing pattern).** `/plan` gets a re-entry block mirroring `/specify`'s Phase 0.5 (`src/commands/specify/main.md:120`): glob `specs/*/grill-seed.json`, act only on a matched seed whose `target_stage == "plan"`, and no-op (do not delete or mutate the seed) when absent. The block reads the seed's directive directly (inline flat-JSON parse, no `grill_helper` call) so it stays valid even if `/grill` is removed — identical to the three existing consumers. Seed lifecycle (deletion / `cycle_count` increment) is NOT owned here, matching the v1 simplification in `/specify`'s block.
- **D4 — One seed drives BOTH remediation paths.** Whether the orchestrator hand-patches `plan.md` (small bounded finding sets — still the cheaper, no-re-derive default) or re-runs `/plan` (structural findings), it reads the SAME typed seed. The seed makes both paths lossless; it does not force a re-plan.
- **D5 — The bounded-compounding-loop cap is reused unchanged.** `cycle_count` + `carried_findings` already cap grill→revise→re-grill loops for the upstream stages; the `/plan` re-entry reuses them as-is with no schema or logic change. The REVISE-PLAN seed carries `cycle_count` for symmetry with RE-ENTER-UPSTREAM. The counter is incremented at the NEXT `/grill` run's seed composition (`grill/main.md:281` — "incremented when this run itself re-entered from a prior seed"), and the user-escalation cap fires there too (`grill/main.md:346` — after 2 cycles on the same feature, `/grill` escalates to the user rather than looping). The `/plan` consumer does NOT check `cycle_count` — identical to `/specify`'s Phase 0.5, which reads the seed but never inspects the counter — because the cap fires at the next `/grill` invocation, not at the consumer. A Phase-4 implementer therefore neither skips nor re-invents a consumer-side cap.
- **D6 — The "non-deterministic refuter across runs" observation is OUT OF SCOPE here.** The differing dispatch agent across the two mintEnvoy runs was the refuter self-refute bug owned and build-fixed by plan 35 (`35-GRILL-REFUTER-ROUTING-FIX-PLAN.md`, build done 2026-06-23). This plan notes it as upstream context; it does not re-plan it.
- **D7 — `SEED_TARGET_STAGES` (4) and `_UPSTREAM_STAGES` (3) are two distinct concepts; keep them separate (emerged during the build).** They answer different questions and must not be conflated:
  - `SEED_TARGET_STAGES = ("spec", "discovery", "research", "plan")` (`src/devforge/lib/_grill/seed_schema.py`) is the set of valid `target_stage` values for a `ReEntrySeed` / `write-seed`. A REVISE-PLAN seed legitimately has `target_stage="plan"`. This is the SEED-VALIDITY set.
  - `_UPSTREAM_STAGES = ("spec", "discovery", "research")` (`src/devforge/lib/_grill/_report.py`) is the set of valid `re_entry_target` values for `render_report`'s RE-ENTER-UPSTREAM disposition — and the only stages shown in the report's RE-ENTER-UPSTREAM verdict line. This is the REPORT-RENDERING set. `"plan"` is NEVER a RE-ENTER-UPSTREAM `re_entry_target`, because the plan is not upstream of itself.
  - Consequence: REVISE-PLAN and RE-ENTER-UPSTREAM are SEPARATE dispositions with separate rendering branches. REVISE-PLAN writes a seed (`target_stage="plan"`) via `write-seed`, but its REPORT disposition is REVISE-PLAN, which has NO `re_entry_target` field. RE-ENTER-UPSTREAM renders a `re_entry_target` drawn from `_UPSTREAM_STAGES`. `render_report`'s validation checks `re_entry_target` against `_UPSTREAM_STAGES` (NOT `SEED_TARGET_STAGES`), so `render_report(disposition="RE-ENTER-UPSTREAM", re_entry_target="plan")` correctly raises `ValueError` — RE-ENTER-UPSTREAM + plan is impossible by construction. Built as Phase 3a (the `_report.py` `_UPSTREAM_STAGES` constant + guard), green at 402 tests.

## Open questions

- **OQ-1 (RESOLVED — (a) keep `List[str]`).** Resolution: a plain string carries enough for the orchestrator to act, so `carried_findings` stays `List[str]` — no typed-record reshape, no schema shape change across the four consumers. The rest of the plan (Phases 1–6) is written against the `List[str]` shape, which is now the settled shape. (The rejected alternative was a typed `{file, line, issue, fix}` record list, which would have rippled into all four consumers; not adopted.)

## Phases

### Phase 0 — Sign-off — DONE

Signed off on D1–D7 (D7 emerged during the build and is additive — see Decisions); OQ-1 resolved (a) "keep `List[str]`".

**Verify:** D1–D7 confirmed; OQ-1 resolved to "keep `List[str]`".

### Phase 1 — Schema enum + tests — DONE

In `src/devforge/lib/_grill/seed_schema.py`, `SEED_TARGET_STAGES` grew to `("spec", "discovery", "research", "plan")`. The existing `__post_init__` enum validation (`_require_in_enum(self.target_stage, SEED_TARGET_STAGES, ...)`) accepts `target_stage="plan"` with no other change. OQ-1 resolved (a) `List[str]`, so `carried_findings` was NOT reshaped. Tests assert `ReEntrySeed(target_stage="plan", ...)` validates and that the three existing target stages still validate. Routed through python-engineer → python-reviewer.

**Verify:** `SEED_TARGET_STAGES` includes `"plan"`; `ReEntrySeed(target_stage="plan", ...)` constructs without raising; the existing `"spec"`/`"discovery"`/`"research"` cases still validate; a `target_stage` outside the enum still raises.

### Phase 2 — Helper emits the seed on REVISE-PLAN before the sweep — DONE

On REVISE-PLAN the helper must emit a `ReEntrySeed` to `specs/[feature]/grill-seed.json` with `target_stage="plan"` BEFORE the WORKDIR sweep, sourced from the confirmed-findings partition computed mid-run (so the write must precede the `rm -rf` of the scratch dir). The existing `write-seed` verb in `src/devforge/lib/_grill/_cli.py` (`cmd_write_seed`) passes `--target-stage` straight through to `build_seed` → `ReEntrySeed` with NO stage-specific branching, so once Phase 1 grows the enum the verb's LOGIC accepts `"plan"` with no branch change — REVISE-PLAN reuses the same `write-seed` codepath RE-ENTER-UPSTREAM uses, NOT a duplicate or fork. The logic does not branch, but two human-facing strings in the same file DO enumerate only the three old stages and become stale once `"plan"` is accepted, so both must be updated: the `--target-stage` argparse `help` string (`_cli.py:1449`, verbatim `"Upstream stage to re-enter: spec | discovery | research."`) and the `cmd_write_seed` docstring (`_cli.py:836-837`, `--target-stage <stage>  (spec|discovery|research)`). Anyone running `grill_helper write-seed --help` reads the first; both must list all four accepted values including `plan`. This phase makes those two string updates, confirms the no-fork reuse, and adds a unit test for the `"plan"` target; PROCEED and KILL continue to write no seed. Routed through python-engineer → python-reviewer. **Flagged gap (resolved as built):** payload assembly beyond the enum + the two strings + the spec wiring (Phase 3b) is orchestrator-composed at synthesis — the REVISE-PLAN branch composes the same `write-seed` args (`target_stage="plan"`, `prior_conclusion`, `invalidating_evidence`, `must_satisfy`, `carried_findings`) from the confirmed-findings partition that RE-ENTER-UPSTREAM uses; the helper side was the two strings + tests.

**Verify:** `write-seed --target-stage plan` writes a valid `ReEntrySeed` JSON to `specs/[feature]/grill-seed.json`; one `write-seed` codepath handles all four target stages (no new branch, no fork); the `--target-stage` argparse help and the `cmd_write_seed` docstring list all four accepted values including `plan`; a unit test covers the `"plan"` target end-to-end.

### Phase 3a — `_report.py` rendering guard (emerged during the build) — DONE

`src/devforge/lib/_grill/_report.py` gained a module constant `_UPSTREAM_STAGES = ("spec", "discovery", "research")`, and `render_report`'s `re_entry_target` validation now checks against `_UPSTREAM_STAGES` (NOT `SEED_TARGET_STAGES`). This enforces D7 in code: a RE-ENTER-UPSTREAM report can only render an upstream `re_entry_target`, so `render_report(disposition="RE-ENTER-UPSTREAM", re_entry_target="plan")` raises `ValueError`. REVISE-PLAN renders via its own disposition branch with no `re_entry_target`. Routed through python-engineer → python-reviewer.

**Verify:** `_report.py` defines `_UPSTREAM_STAGES = ("spec", "discovery", "research")`; `render_report` validates `re_entry_target` against `_UPSTREAM_STAGES`; `render_report(disposition="RE-ENTER-UPSTREAM", re_entry_target="plan")` raises `ValueError`; the three upstream `re_entry_target` values still render; the full `_grill` suite is green (402 tests).

### Phase 3b — `grill/main.md` + `report-format.md` wiring (the real bulk of the work)

Wire the REVISE-PLAN disposition in `src/commands/grill/main.md` to call `write-seed --target-stage plan` BEFORE the PHASE-7 WORKDIR sweep (`main.md:349`), symmetric to how RE-ENTER-UPSTREAM already writes its seed before the same sweep. The one-enum-value change in Phase 1 is small; the prose enumeration is the real bulk.

**Design X (D7) governs which sites get `plan` and which stay 3.** The `target_stage` of a seed (`SEED_TARGET_STAGES`, 4 values incl. `plan`) and the `re_entry_target` shown in a RE-ENTER-UPSTREAM verdict (`_UPSTREAM_STAGES`, 3 values, NO `plan`) are different concepts. Sites that enumerate `write-seed --target-stage` values get all four; sites that enumerate the RE-ENTER-UPSTREAM verdict target stay at three. REVISE-PLAN is a separate disposition with its own rendering — it writes a `target_stage="plan"` seed but is NEVER expressed as a RE-ENTER-UPSTREAM target. (Line numbers are current as of this draft — re-verify before editing, since earlier sites in the file shift the later ones.)

**`grill/main.md` sites (8) — all retained, framing made Design-X-consistent:**

- **`main.md:29`** (Outputs section) — today "written ONLY when the disposition is RE-ENTER-UPSTREAM … the named upstream command (`/specify`, `/discover`, or `/research`)". Add REVISE-PLAN → `/plan` as a seed-writing disposition.
- **`main.md:281`** (PHASE 5 synthesis) — a RUNTIME-failure site: it tells the executing LLM the seed token is `spec | discovery | research` and that "the schema rejects any other value with exit 2", so the LLM will not compose a `plan` seed even after the schema accepts it. Add `plan` to the enumerated `write-seed --target-stage` tokens. **Also compose the REVISE-PLAN seed inputs** in this synthesis step: `target_stage="plan"`, `prior_conclusion` = the flawed plan decision, `invalidating_evidence` = the confirmed grill finding, `must_satisfy` = the fix, `carried_findings` = the remaining confirmed findings.
- **(seed-emission section heading, around `main.md:314`)** — today "RE-ENTER-UPSTREAM only — emit the backward seed"; change to "RE-ENTER-UPSTREAM OR REVISE-PLAN — emit the backward seed" so REVISE-PLAN is covered by the same emission section.
- **`main.md:318`** (the `write-seed` bash code block) — currently RE-ENTER-UPSTREAM-only; add the REVISE-PLAN `--target-stage plan` invocation. **Gets all four `--target-stage` values** (it is the `SEED_TARGET_STAGES` path).
- **`main.md:321`** (inline prose, `--target-stage (spec | discovery | research)`) — add `plan`. **Gets all four** (it enumerates `write-seed --target-stage`).
- **`main.md:331`** (PHASE 7 opening — "tell the user … (and, on RE-ENTER-UPSTREAM, `specs/[feature]/grill-seed.json`)") — extend to "on RE-ENTER-UPSTREAM OR REVISE-PLAN" so the user is told a seed was written under REVISE-PLAN too.
- **`main.md:338`** (PHASE 7 `Revise plan` option) — today "re-run `/plan` (or hand-patch `plan.md`), then optionally re-run `/grill`"; add that a `grill-seed.json` with `target_stage="plan"` was written for `/plan` to consume on re-run.
- **`main.md:342`** (PHASE 7 option-visibility guard — "omit `Re-enter upstream` when no seed was written") — a CORRECTNESS edit, not cosmetic: this is a SEED-EXISTENCE test, but once Phase 2+3b make REVISE-PLAN write a seed, "no seed was written" is FALSE on a REVISE-PLAN run, so the guard would erroneously surface the `Re-enter upstream` option — a dead option, since the upstream commands ignore a `target_stage="plan"` seed. Change the test from seed-existence to DISPOSITION-IDENTITY, e.g. "omit `Re-enter upstream` when the disposition is not RE-ENTER-UPSTREAM."
- **`main.md:345`** (PHASE 7 `Revise plan` action arm — "tell the user to re-run `/plan`") — state the seed was written so the re-run is directed, not a blind re-prompt.

**NOT an edit site (Design X — the `_UPSTREAM_STAGES` path, correctly distinct):**

- **`main.md:310`** (the `render-report --re-entry-target` help, "spec | discovery | research") — **STAYS 3.** This is the `_UPSTREAM_STAGES` / RE-ENTER-UPSTREAM `re_entry_target` path, NOT the `write-seed --target-stage` path. `plan` is never a RE-ENTER-UPSTREAM target. Do NOT add `plan` here.

**`report-format.md` sites — re-classified under Design X:**

- **`references/report-format.md:74`** (the report skeleton `**Verdict**:` line — `RE-ENTER-UPSTREAM (target: spec | discovery | research)`, with REVISE-PLAN appearing in the same verdict line with NO target) — **STAYS 3, do NOT add `plan`.** This enumerates the RE-ENTER-UPSTREAM verdict `re_entry_target` (`_UPSTREAM_STAGES`); `plan` is never one. REMOVED from the "add plan" set.
- **`references/report-format.md:82`** (the REVISE-PLAN verdict-guidance bullet) — **NEW site (was missing from the draft).** ADD that on REVISE-PLAN the orchestrator emits a `grill-seed.json` (`target_stage="plan"`) for `/plan` to consume on re-entry.
- **`references/report-format.md:83`** (the RE-ENTER-UPSTREAM verdict-guidance bullet) — **STAYS 3, do NOT change.** It describes the RE-ENTER-UPSTREAM path, whose targets are the three upstream stages. REMOVED from the "add plan" set.
- **`references/report-format.md:165-179`** (the `## The re-entry seed (RE-ENTER-UPSTREAM only)` section) — **CORRECT (gets `plan`).** This section enumerates the seed's `target_stage` + its consumers, which IS the `SEED_TARGET_STAGES` path. Generalize it to both seed-writing dispositions: heading → "RE-ENTER-UPSTREAM or REVISE-PLAN"; the "when and only when RE-ENTER-UPSTREAM" sentence generalizes to "RE-ENTER-UPSTREAM or REVISE-PLAN"; `target_stage (spec|discovery|research)` → `(spec|discovery|research|plan)`; the consumer list `/specify, /discover, or /research` → add `/plan`; the `prior_conclusion`/`must_satisfy` framing generalizes so it also covers the plan-revision case.

These files ship into a target project's `.claude/commands/grill/`, so the edits route through instruction-author → instruction-reviewer → claude-code-guide — instruction-reviewer owns the multi-site cross-consistency check; claude-code-guide confirms authoring conformance (frontmatter, tools, and no authoring regression).

**Verify:** the REVISE-PLAN branch writes the seed before the sweep; the eight `grill/main.md` sites (29, 281, 314-heading, 318, 321, 331, 338, 342, 345) reflect the four-consumer model where they enumerate `write-seed --target-stage` and the REVISE-PLAN seed-emission path; `main.md:310` and `report-format.md:74`/`:83` STAY at three upstream stages (the `_UPSTREAM_STAGES` path); `report-format.md:82` states a `target_stage="plan"` seed is written on REVISE-PLAN; `report-format.md:165-179` generalizes to RE-ENTER-UPSTREAM or REVISE-PLAN with `plan` in the target list and `/plan` in the consumer list; no `grill/main.md` line claims REVISE-PLAN produces no structured output or that the schema rejects a `plan` stage; the line-342 guard omits `Re-enter upstream` by DISPOSITION IDENTITY (disposition ≠ RE-ENTER-UPSTREAM), NOT by seed existence; the disposition prose and the disposition table at the top of this plan agree.

### Phase 4 — `/plan` re-entry block

Add a re-entry block to `src/commands/plan/main.md` mirroring `/specify`'s Phase 0.5 (`src/commands/specify/main.md:120`): glob `specs/*/grill-seed.json`, act only on a matched seed with `target_stage == "plan"`, read it directly (inline flat-JSON parse, no `grill_helper` call), treat it as a binding directive that constrains the re-plan, and no-op when absent. It reads the same five payload fields the `/specify` block reads (`feature`, `prior_conclusion`, `invalidating_evidence`, `must_satisfy`, `carried_findings`) and, like `/specify`, does NOT delete the seed or change `cycle_count`. This file ships into a target project's `.claude/commands/plan/main.md`, so the edit routes through instruction-author → instruction-reviewer → claude-code-guide — instruction-reviewer owns the cross-consistency check (this block's payload-field reads match the seed schema and mirror `/specify` Phase 0.5); claude-code-guide confirms authoring conformance (frontmatter, tools, and no authoring regression).

**Verify:** the `/plan` re-entry block consumes a `target_stage == "plan"` seed and no-ops on absence; it does not own seed lifecycle (no delete, no `cycle_count` write); its payload-field reads match the seed schema; the prose mirrors `/specify` Phase 0.5 in structure.

### Phase 5 — Docs reconcile + cross-ref sweep

Reconcile the docs that describe the consumer set: the `/plan` and `/grill` entries in `src/CLAUDE.md`, `CHANGELOG.md`, the pipeline-handoff table in the repo-root `CLAUDE.md`, and this plan's status line. Run the cross-ref sweep for `grill-seed.json`, `ReEntrySeed`, `SEED_TARGET_STAGES`, and `target_stage` to confirm every site now describes a four-consumer model.

**Verify:** `src/CLAUDE.md` `/grill` entry lists `/plan` among the re-entry-seed consumers; the repo-root `CLAUDE.md` handoff table describes a 4-consumer model; the cross-ref sweep finds no site still asserting a 3-consumer (`/research`/`/discover`/`/specify`-only) model.

### Phase 6 — testForge20 / mintEnvoy e2e (user-driven, HARD GATE)

On a real install, run `/grill` on a `plan.md` to a REVISE-PLAN disposition; confirm `specs/[feature]/grill-seed.json` is written with `target_stage: "plan"` before the WORKDIR sweep. Then re-run `/plan`; confirm the new re-entry block detects the seed, states it is running in grill-re-entry mode for the named feature, and folds the confirmed findings into the re-plan. Confirm the three existing consumers (`/research`/`/discover`/`/specify`) still no-op on a `"plan"`-targeted seed.

**Verify:** REVISE-PLAN writes `specs/[feature]/grill-seed.json` with `target_stage: "plan"`; the re-run `/plan` consumes it and names `must_satisfy`; PROCEED/KILL write no seed; the three existing consumers ignore the `"plan"`-targeted seed.

## When resuming work

- Phases 1, 2, 3a are BUILT + green (402 tests). Remaining work is Phase 3b (spec wiring), Phase 4 (`/plan` consumer), Phase 5 (docs); Phase 6 is the user-driven e2e gate.
- Plan 35 (`35-GRILL-REFUTER-ROUTING-FIX-PLAN.md`, build done 2026-06-23) is prerequisite context — read it. The seed this plan emits carries the findings the refutation pass confirmed, so refuter routing must be correct first; D6 records that the determinism observation belongs to plan 35, not here.
- OQ-1 is RESOLVED (a) — `carried_findings` stays `List[str]`. The schema is the settled shape; do not re-open the typed-record alternative.
- D7 (Design X) is the load-bearing distinction for Phase 3b: `SEED_TARGET_STAGES` (4, incl. `plan`) governs `write-seed --target-stage`; `_UPSTREAM_STAGES` (3, no `plan`) governs the RE-ENTER-UPSTREAM `re_entry_target` rendered in the report. Classify each Phase-3b edit site by which path it enumerates — `report-format.md:74`/`:83` and `main.md:310` STAY at three; the `write-seed --target-stage` sites and the seed section get four.
- Do NOT fork a second seed schema (D1) — extend `SEED_TARGET_STAGES` on the existing `ReEntrySeed`.
- Mirror `/specify`'s Phase 0.5 block (`src/commands/specify/main.md:120`) for the `/plan` consumer (D3/Phase 4) — same glob / conditional / inert-on-absence / direct-read-no-helper pattern.
