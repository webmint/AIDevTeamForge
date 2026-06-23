# 32 — /generate-docs GREENFIELD LANE

**DRAFT — decision record, not started, no code.** Awaiting maintainer ratification of the recommended option. Recorded 2026-06-23 on `develop-2.0-init`. This file is a DECISION RECORD, not an active execution plan: it lays out a framework asymmetry + a decision space and recommends one option, but picks no winner unilaterally — the maintainer ratifies. The per-phase steps below carry `## Verify` criteria scoped to "ratify option N" / "verify signal availability", NOT code-landing criteria; the build phases get authored once an option is ratified (see `## When resuming work`).

## Problem — the greenfield asymmetry in the 4-command setup chain

The 4-command setup chain is `/init-forge` → `/generate-docs` → `/configure` → `/constitute` (the canonical order; see `src/CLAUDE.md` Workflow "Spec-Driven Development Flow"). Two of those commands treat a fresh-scaffold (greenfield) project asymmetrically:

- **`/constitute` HAS an explicit greenfield lane.** It emits "Section 7 (Scaffolding Guide)" only when `mode == "greenfield"` (`src/commands/constitute/main.md:9` — the command-summary sentence; `main.md:136` "Section 7 — Scaffolding Guide (greenfield only)"; `main.md:138` "Compose only when `mode == \"greenfield\"`"). `mode` is auto-resolved from `INIT_JSON.project_state` by Phase 4's Q-mode (`main.md:430-431`: `project_state == "empty"` → `greenfield`, `project_state == "brownfield"` → `existing-codebase`), or prompted when the field is missing/unexpected (`main.md:433`). Q-mode runs at runtime as Phase 1.5 (`main.md:138`).
- **`/generate-docs` has NO greenfield lane.** It is a pure code-reader: bottom-up tiers concern → package → project + glossary, every doc seeded from indexed source (`src/commands/generate-docs/main.md` — Phase 2 "Concern tier loop" `:96`, Phase 3 "Package tier loop" `:255`, Phase 4 "Project tier loop" `:321`, Phase B "Glossary" `:477`). Its Phase 0 gate keys on `.devforge/index.json` (`main.md:51`), not on project maturity. It reads `init.yaml` ONLY to resolve `project_root` for wrapper-mode tree-walking (`main.md:349`) — it does NOT read `project_state`. On a fresh scaffold (e.g. a base Electron + React install with essentially no application code) there is nothing to document, so `/generate-docs` is a near-no-op or produces empty/thin docs.

The asymmetry bites because `/generate-docs` output is a HARD precondition downstream:

- `/specify` Phase 0.1 calls `specify_helper preflight`, which requires `docs/architecture.md` present + non-empty (`src/commands/specify/main.md:36` — the artefact list; `main.md:40` — "Exit 0 → all present + non-empty + populate-guard absent").
- `/specify` Phase 1 mandates READING `docs/architecture.md` as one of four base reads gated by `phase1-finalize` (`src/commands/specify/main.md:211`).

The chain is NOT bricked at the gate on a fresh scaffold, but for a subtle reason worth recording precisely:

- `install.sh` copies stub `docs/overview.md` + `docs/architecture.md` into the target, per-file presence-guarded (`install.sh:216-223`). These stubs are present + non-empty.
- The `/specify` gate's populate-guard literal is `_Run /constitute to populate_` (`src/commands/specify/main.md:40`), which is constitution-specific. The shipped `docs/architecture.md` stub (`src/docs/architecture.md`) contains NO such literal — its placeholder prose reads e.g. `_Populated by \`constitute\` ..._` / `_Populated by \`generate-docs\` ..._`, none of which match the gate's literal.
- Therefore the gate PASSES on the bare install stub even when `/generate-docs` never produced anything. The chain proceeds — but with meaningless placeholder docs.

**Concrete trigger.** A user scaffolded a greenfield Electron + React app, could not meaningfully run `/generate-docs` (no application code to read), and was left with the install stub docs. `/constitute` handled greenfield correctly (its lane exists); `/generate-docs` and the `/specify` gate did not, leaving the user confused about whether running `/generate-docs` was required, what it did, and whether the resulting stub docs were acceptable input to `/specify`.

### Related context (out of scope for this plan)

A separate, sibling change — IN PROGRESS at the time this plan was recorded — fixes `/configure`'s `substitute-templates` not filling the `{{PROJECT_NAME}}` / `{{PROJECT_DESCRIPTION}}` placeholders in the install stub docs. That placeholder-substitution fix is OUT OF SCOPE here and is NOT re-specified by this plan; it is mentioned only because a ratified Option 1 (below) leaves the substituted stubs in place, so the two changes touch overlapping output. This plan assumes the stubs are placeholder-substituted by the time `/generate-docs` runs.

## Decision space

**Core question: should `/generate-docs` acquire a greenfield lane, and/or should the `/specify` gate treat greenfield differently?**

The options below are distinct candidate answers. They are not all mutually exclusive — Option 3 is a strict subset of Option 1's user-facing messaging, and a hybrid is possible (Option 4). No winner is picked unilaterally; the maintainer ratifies one (or a hybrid) at the `## Verify` gate of Phase 0.

### Option 1 — Greenfield no-op-with-clean-stubs mode in `/generate-docs` (RECOMMENDED)

Teach `/generate-docs` to detect greenfield and short-circuit. On greenfield:

1. Skip the code-reading tiers (Phase 2 concern / Phase 3 package / Phase 4 project / Phase B glossary).
2. Leave the install stub `docs/overview.md` + `docs/architecture.md` in place (already placeholder-substituted by the sibling `/configure` fix — see Related context).
3. Emit a clear user-facing message: nothing to document yet — `docs/` will grow as features ship via tech-writer / `/finalize`.
4. Exit 0 cleanly so the chain proceeds to `/configure` → `/constitute`.

**The greenfield signal.** Reuse the SAME source `/constitute` uses: `INIT_JSON.project_state` from `.devforge/init.yaml`, produced by `/init-forge` (step 1) and therefore on disk before `/generate-docs` runs (step 2). The field is a required scalar with enum `{empty, brownfield}` (verified in `src/devforge/lib/init_helper.py` — `ENUM_FIELDS["project_state"] = {"empty", "brownfield"}`, `REQUIRED` tuple includes `project_state`). The greenfield case is `project_state == "empty"` (the same value `/constitute` maps to `greenfield` at `src/commands/constitute/main.md:431`). A near-empty CBM `index_repository` result is a possible CORROBORATING signal but is NOT required by this option — see OQ-2.

**Pros.**
- Symmetric with `/constitute` — same signal, same maturity concept, one mental model for the user across the chain.
- Removes the "did I need to run this? why is it empty?" confusion at its source: the command itself states what greenfield means for docs.
- Cheapest CBM path on greenfield — skips the `index_repository` reindex + the whole-tree `source_stamp` scan the brownfield Phase 1 preflight pays.
- The signal already exists on disk at step 2 (pending OQ-1 confirmation that `init.yaml` is readable and `project_state` is populated at that point — it is REQUIRED by `init_helper`, so a successful `/init-forge` guarantees it; the open question is only whether `/generate-docs` is ever run before a complete `/init-forge`).

**Cons.**
- Adds a branch to a command that is currently single-lane (a pure code-reader). The greenfield branch is a NEW first-of-its-kind shape for this command.
- Decision: should the detection live in the helper (mechanical) or in the orchestrator/main.md (LLM judgment)? — OQ-3.
- If the user scaffolded SOME code but `project_state` is still `empty` (e.g. `/init-forge` ran before any code landed), the no-op skips docs that could have been written. Mitigated by the message telling the user to re-run `/generate-docs` once code exists (`/generate-docs` is already "re-run when the codebase structure changes significantly" per `src/CLAUDE.md`).

### Option 2 — Relax / repath the `/specify` gate for greenfield

Make the `docs/architecture.md` precondition explicitly satisfiable by the stub on greenfield (it already is — see Problem), and DOCUMENT that, OR route greenfield specs through a different evidence source than `docs/architecture.md`.

**Pros.**
- Smaller surface — touches only `/specify` Phase 0/Phase 1, not `/generate-docs`.
- Acknowledges the already-true behavior (the stub passes the gate) rather than pretending generate-docs produced something.

**Cons.**
- Weakens the brownfield guarantee — the gate exists to ensure `/specify` reads REAL architecture context; relaxing it risks brownfield projects slipping through on stubs too (the gate cannot easily tell "intentional greenfield stub" from "brownfield run-generate-docs-was-skipped stub").
- Risks cargo-culting empty docs: a greenfield `/specify` that "reads" a stub `docs/architecture.md` gains nothing, and the user may not realize the architecture context is hollow.
- Does NOT address the `/generate-docs` confusion (the user still doesn't know what running it on greenfield does) — it only unblocks the downstream gate.

### Option 3 — Do nothing structural; document the greenfield path

Accept the status quo: `/generate-docs` is a no-op on greenfield, the stub satisfies the `/specify` gate, and the only change is explicit user-facing guidance — e.g. a line in `src/CLAUDE.md`'s `/generate-docs` command-detail and/or the command intro stating "on a greenfield project with no application code, `/generate-docs` has nothing to document; the install stubs are valid input to the rest of the chain — proceed to `/configure`."

**Pros.**
- Cheapest — no command branch, no gate change, no helper change. Pure docs.
- Zero risk of weakening the brownfield gate or adding a code branch.
- Removes the user's CONFUSION (the most acute symptom) without changing behavior.

**Cons.**
- Leaves the asymmetry — `/constitute` has a real lane, `/generate-docs` does not; the user must internalize that the two predecessor commands treat greenfield differently for reasons that are invisible.
- The "no-op" is implicit: `/generate-docs` still runs its CBM-sync preamble + Phase 0/Phase 1 preflight (incl. the `index_repository` reindex) on a greenfield repo before discovering there's nothing to do — wasted preflight cost with no short-circuit.
- Guidance prose tends to rot if a later change makes greenfield generate-docs do something; a documented-but-unenforced path is a sentence-level hallucination risk for future sessions.

### Option 4 — Hybrid (Option 1 short-circuit + Option 3 messaging, NO Option 2 gate change)

Build the Option 1 greenfield short-circuit (skip tiers, exit 0) AND ship the Option 3 user-facing guidance as the short-circuit's message, but do NOT touch the `/specify` gate (Option 2) — the stub already passes it, and leaving the gate strict preserves the brownfield guarantee.

This is effectively "Option 1, where the no-op message IS the documentation." It is called out separately because it is the natural landing point if the maintainer wants the structural short-circuit (Option 1) without re-opening the gate (Option 2). The RECOMMENDED option (Option 1) already folds in the message, so Option 4 ≈ Option 1; it is listed to make explicit that the gate-relaxation (Option 2) is a SEPARATE axis the maintainer can decline independently.

## Recommendation

**Recommended: Option 1 (which subsumes Option 4's framing) — a greenfield short-circuit in `/generate-docs` keyed on `INIT_JSON.project_state == "empty"`, leaving the substituted stubs in place, emitting a clear message, exiting 0; and NOT relaxing the `/specify` gate (decline Option 2).**

**Why.**
- **Symmetry is the right invariant.** `/constitute` already established `INIT_JSON.project_state` as THE greenfield signal for the setup chain (`src/commands/constitute/main.md:430-431`). Giving `/generate-docs` a lane off the same signal makes the two predecessor commands behave coherently — one concept ("is this project empty?"), one source of truth, two consumers. Option 3 alone leaves them asymmetric; Option 2 alone fixes the wrong end (the gate, not the producer).
- **It fixes the cause, not the symptom.** The user's confusion is downstream of `/generate-docs` having no greenfield concept. Option 1 puts the concept where it belongs — in the producer — and the message falls out for free.
- **It declines to weaken the brownfield gate.** Option 2's gate-relaxation trades a real safety property (brownfield `/specify` reads real architecture) for a problem Option 1 already solves structurally. The stub already passes the gate today, so greenfield is unblocked WITHOUT touching the gate.
- **It is the cheap path on greenfield.** Short-circuiting before the tiers (and ideally before the `index_repository` reindex) saves the preflight cost Option 3 still pays.

**What would need to change (build phases, authored after ratification).**
- `src/commands/generate-docs/main.md` — add a greenfield-detection step (read `init.yaml` `project_state`) early, before the CBM-sync preamble's expensive reindex if OQ-3 lands detection in the orchestrator; a greenfield short-circuit that skips Phase 2/3/4/B, emits the message, exits 0.
- Possibly `src/devforge/lib/_generate_docs/_preflight.py` — if OQ-3 lands detection in the helper, the preflight returns a `greenfield: true` (or equivalent) field the orchestrator branches on (helper-owns-shape: the helper owns the detection contract, the orchestrator composes the user message). This is the path consistent with `feedback_helper_owns_shape_principle`.
- `src/commands/specify/main.md` — NO change under the recommendation (Option 2 declined). If the maintainer ratifies a hybrid that DOES relax the gate, this file is in scope; otherwise it is not.
- Likely a `src/CLAUDE.md` `/generate-docs` command-detail sentence noting the greenfield short-circuit (so the always-on catalog reflects the new lane).

## Open questions (enumerated, NOT resolved)

- **OQ-1 — `init.yaml` / `project_state` availability at step 2.** Is `.devforge/init.yaml` guaranteed present with a populated `project_state` when `/generate-docs` runs? `project_state` is a REQUIRED enum field in `init_helper` (verified: `src/devforge/lib/init_helper.py` `REQUIRED` tuple + `ENUM_FIELDS`), so a SUCCESSFUL `/init-forge` guarantees it. The residual question is whether `/generate-docs` can be reached before `/init-forge` completes (its Phase 0 gate keys on `.devforge/index.json` at `src/commands/generate-docs/main.md:51`, not on `init.yaml`). Must be confirmed before Option 1 is buildable.
- **OQ-2 — CBM near-empty signal.** Does CBM `index_repository` on a near-empty scaffold return a usable "this is basically empty" signal (node/file counts) that could CORROBORATE or REPLACE the `project_state` check? Option 1 does not require it (it keys on `project_state`), but a corroborating signal could harden detection against the "`project_state == empty` but some code exists" edge.
- **OQ-3 — detection home: helper vs orchestrator.** Should greenfield detection be mechanical (in `src/devforge/lib/_generate_docs/_preflight.py`, returning a field) or an orchestrator/LLM judgment in `main.md`? The helper-owns-shape principle (`feedback_helper_owns_shape_principle`) favors the helper owning the detection contract while the orchestrator composes the user-facing message — but the final call is the maintainer's at ratification.
- **OQ-4 — overlap with the incremental-mode plan (`28-GENERATE-DOCS-INCREMENTAL-MODE-PLAN.md`, deferred).** Both this plan and plan 28 touch the `/generate-docs` preflight: plan 28 proposes swapping the full `index_repository` for `detect_changes` and skipping the whole-tree `source_stamp` scan (`28-GENERATE-DOCS-INCREMENTAL-MODE-PLAN.md` "Chosen design" step 4); this plan (Option 1) proposes a greenfield short-circuit BEFORE the tiers. If both land, the preflight grows two distinct early branches (greenfield short-circuit + incremental scope). Sequence + interaction must be reconciled when the second of the two is promoted to a build plan.

## Phase 0 — Maintainer ratification (decision gate)

Present this decision record to the maintainer. The maintainer ratifies exactly one of Option 1 / Option 2 / Option 3 / Option 4 (or directs a different hybrid). Until ratification, no code phases are authored.

### Verify

- Maintainer has ratified a single option (record the chosen option number + any amendments inline in this file under a new `## Ratified` heading when it happens).
- If the ratified option is 1 or 4: OQ-1 has been answered (verified `init.yaml` + `project_state` are present and populated at `/generate-docs` invocation time) and OQ-3 has been decided (helper vs orchestrator detection home).

## Phase 1 — (authored after ratification) Build the ratified lane

NOT authored yet. Once Phase 0 ratifies an option, this phase is replaced with a concrete per-step build breakdown (files, setters, `## Verify` per step) following the repo's plan conventions and the discipline rules in the repo-root `CLAUDE.md` ("Code & spec discipline"). The build runs behind the standard agent loops (python-engineer → python-reviewer for any helper change; instruction-author → instruction-reviewer + claude-code-guide for any `main.md` / `src/CLAUDE.md` change).

### Verify

- Placeholder until Phase 0 ratifies an option. No verification criteria until the build steps exist.

## Context for next session

This is a recorded decision awaiting ratification, NOT an active build. The asymmetry: `/constitute` has a greenfield lane keyed on `INIT_JSON.project_state` (`src/commands/constitute/main.md:430-431`); `/generate-docs` has none and is a pure code-reader, so it no-ops on a fresh scaffold yet its `docs/architecture.md` output is a hard `/specify` precondition (`src/commands/specify/main.md:36`, `:211`). The chain survives because the install stub (`install.sh:216-223`) passes the gate (the gate's populate-guard literal `_Run /constitute to populate_` at `src/commands/specify/main.md:40` is constitution-specific and absent from the architecture stub). The recommended fix is Option 1 — a greenfield short-circuit in `/generate-docs` off the SAME `project_state` signal `/constitute` uses, declining to relax the `/specify` gate. The sibling `/configure` placeholder-substitution fix (Related context) is a separate in-progress change, NOT this plan's scope.

## When resuming work

This is a recorded decision, not an active build. Before authoring any edit instruction:

1. Re-confirm the cited line numbers against the live tree — `src/commands/constitute/main.md:9/136/138/430-431/433`, `src/commands/generate-docs/main.md:51/96/255/321/349/477`, `src/commands/specify/main.md:36/40/211`, `install.sh:216-223`, and the `src/docs/architecture.md` stub's absence of the populate-guard literal. Line numbers drift; verify before trusting.
2. Resolve OQ-1 (is `init.yaml` `project_state` available at `/generate-docs` time?) before treating Option 1 as buildable.
3. Get the maintainer to ratify an option (Phase 0). Record the ratification inline.
4. Reconcile OQ-4 against `28-GENERATE-DOCS-INCREMENTAL-MODE-PLAN.md` if that plan has since been promoted — both touch the `/generate-docs` preflight.
5. Then promote Phase 1 to a real per-step build breakdown with `## Verify` per step.
