# 18-SCOPE-FIDELITY-AND-PROMPT-INTAKE-PLAN

**Status**: DRAFTED 2026-06-07; **ALL 6 STEPS SHIPPED 2026-06-07** on `develop-2.0-init` (working tree). The mechanized `/plan` OOS-respect check (Step 4) is the one DEFERRED piece (prose-first v1; future, gated on empirical miss-rate). Each step landed behind the framework's python-engineer→python-reviewer (helpers/schemas) and instruction-author→instruction-reviewer (spec docs) loops. The step bodies below remain the authoritative spec of what was built; only the status-tracking framing has been updated. No code in this file (the code landed in the helper subpackages + the four command specs + the two handoff schemas, not here). This was a DESIGN doc; it is now IMPLEMENTED.
**Branch**: `develop-2.0-init`
**Driver**: A real testForge20 e2e (`specs/001-on-the-configuration-page`) over-built a one-line-class bug fix. The framework treats every INTERNAL artefact (memo, handoff, spec, plan, tasks) as structured + gated, but treats the ONE EXTERNAL input — the user's prompt — as trusted. The constitution's own boundary rule (`src/constitution.md:139` — "Validate at boundaries. Validate all external input: user input, API responses, file content, environment variables. Trust internal code.") names user input as the thing to validate; the pipeline applies that rule to API responses and env vars but never to the prompt that seeds the whole pipeline. This plan makes the prompt the validated boundary: it separates a user/research *hypothesis* from a *requirement*, confidence-gates hypothesis propagation, adds scope-coherence + out-of-scope backstops, and makes research/discover (which now carries an intake-interrogation gate) mandatory before `/specify`.

---

## Context for next session

### The over-solve (what happened, verified against testForge20 `specs/001-on-the-configuration-page`)

The user asked for a narrow bug fix: on a failed configuration-leaf load, render an empty section + an error toast, and never leak the previous (or base-machine) items into the new section. The pipeline instead produced a discriminated `ConfigurationItemsOutcome` carrying items inline + a per-section `loadState` + an empty-vs-failure split — machinery whose only justification is defending an *overlapping-load race*, which the spec itself (§6 Out of Scope) excluded.

### The root chain (state this in the plan; each link is a propagation defect, not a one-off mistake)

1. **User prompt** — carried a clean *desired outcome* AND an unrequested mechanism guess: *"Suspected cause: getConfigurationItems returns Promise<void> (no success/failure signal) … updateSections unconditionally reads configurationMenuState.items after the await."* That HYPOTHESIS — not a requirement — seeded the inline-items / shared-slot design.
2. **`/research`** — graded the race "Hypothesis, tier-3, needs repro" (the rubric + probe tiering did their job at classification), yet the *suspected cause* still propagated downstream as the *recommended fix*. The verbatim prompt was dropped entirely — only a structured paraphrase (`Intent.symptom_summary` / `Intent.desired_summary`) flows in the handoff, so no downstream stage can audit requirement-vs-interpretation.
3. **`/specify`** — kept "branch on outcome / avoid the shared slot" in §4/§5 while marking the slot's concurrency-hardening Out of Scope in §6 → an internal contradiction (a §5 AC mandating behavior whose §6 entry excludes it). Also introduced the empty-vs-failure split, an extra distinction not present in the desired outcome.
4. **`/plan`** — the architect's specialist relay asked the frontend-engineer "is branching enough to avoid the race"; the consult *solved* the race (inline items in the outcome) instead of flagging the race OOS per §6.
5. **`/breakdown` + `/implement`** — built it faithfully. The downstream stages are innocent: they obeyed an upstream design that had already over-committed.

### Why the existing forcing functions did not catch it

The architect charter ALREADY has a state-cardinality forcing step (`src/agents/architect.md` Rule 9, lines 134–139 + 153): "before declaring any multi-state type … map every state to the acceptance criterion that exercises it. Collapse any state no AC … exercises." That step did not fire usefully because the SPEC ITSELF carried an AC for the empty-vs-failure split — so the failed/empty states each *did* map to an AC. The defect had already been laundered into a requirement upstream (links 1–3). A forcing function that checks "does every state map to an AC" cannot catch an over-solve whose extra states were written into the ACs. The fix must act at the boundary (links 1–3), not only at the architect (link 4).

### The unifying defect (the one sentence)

The prompt is the framework's one un-validated trust boundary, and the pipeline cannot distinguish a user/research *hypothesis* from a *requirement*, nor catch a design that solves an Out-of-Scope concern.

### Current-state facts this plan builds on (verified 2026-06-07; cite when implementing)

- **Research handoff `Intent`** (`src/devforge/lib/_research/handoff_schema.py:254-265`, dataclass header; **Step-1-updated** — the cited range still brackets the class + docstring but the field block now extends a few lines past it) now has FOUR fields: `symptom_summary`, `desired_summary`, `scope`, and `verbatim_prompt` (added by Step 1 as `Optional[str] = None`, tolerate-missing-on-read per OQ-1). The prior "NO verbatim-prompt field" claim is now FALSE — the raw prompt has a typed home. There is still NO `suspected_cause`/hypothesis field (Step 2 adds the hypothesis lane). So `desired` is already separated from `symptom`, AND the raw boundary input is now preserved separately — but a *mechanism guess* still has nowhere typed to live (Step 2's lane) and can still leak into the recommended-approach summary in `plan_seeds` until Step 2 ships. *(Step 2 shipped — now a mechanism guess has a typed home: the pre-rubric suspected-cause classifier records it as a `record-hypothesis` entry, and `verify-hypothesis-suppression` gates its leak into `plan_seeds`; this "until Step 2 ships" caveat is resolved.)*
- **Discover handoff `Intent`** (`src/devforge/lib/_discover/handoff_schema.py:209-223`, dataclass header; **Step-1-updated** — same caveat: the range brackets the class + docstring, the field block now extends past it) now has `feature_concept`, `topic`, `topic_slug`, optional `scope_summary`, and `verbatim_prompt` (added by Step 1 as `Optional[str] = None`, tolerate-missing-on-read per OQ-1). The prior "Also NO verbatim-prompt field" claim is now FALSE.
- **The verbatim prompt today** lives only in the rendered research report's `**Topic**:` line (set by `research_helper set-topic`, `src/commands/research/main.md:55-64`) — never in the machine handoff. Confirmed: the handoff `Intent` is a paraphrase, not the raw prompt.
- **`/research` Phase 1 rubric** (`src/commands/research/main.md:76-86`) captures six dimensions: `symptom`, `affected_area`, `repro_or_current`, `desired`, `scope`, `unchanged_behavior`. None of the six captures a *suspected cause / mechanism hypothesis* as a distinct, confidence-gated signal — a "Suspected cause:" sentence in the prompt currently has no rubric home and bleeds into `symptom` or `desired`. *(Step 2 shipped — now a "Suspected cause:" lead-in is auto-detected by the pre-rubric classifier BEFORE the six-dimension rubric and routed to the hypothesis lane, so it no longer bleeds into `symptom`/`desired`.)*
- **`/research` already has confidence/tier machinery**: the `Probe` block (`_research/handoff_schema.py:781-847`) carries a `tier` (`1`/`1.5`/`2`/`3`) + a `Discriminator` (`primary_confirms_if` / `runner_up_confirms_if` / `both_disproved_if`); `compute_confidence_grade` (lines 205-246) derives HIGH/MEDIUM/LOW. Hypotheses are enumerated with falsifiers (`record-hypothesis`, `src/commands/research/main.md:613-620`). The machinery to GATE propagation exists; it is just not wired to suppress an unverified mechanism from becoming design direction.
- **`/specify` gate is currently OPTIONAL on upstream handoffs.** Phase 0.4 (`src/commands/specify/main.md:94-114`) globs handoffs and on zero hits emits "No recent handoff found; proceeding cold" (line 102) and continues. `/specify` is hard-gated only on the 4-command setup chain (Phase 0.1, lines 27-42), NOT on research/discover. So today research IS optional — piece 6 changes this. *(Step 6 shipped — now `/specify` Phase 0.4 BLOCKs on zero research/discover handoffs (`find-handoffs --require`, exit 2, no override); research/discover is mandatory for the spec pipeline.)*
- **`/specify` §6 Out of Scope** is recorded via `record-out-of-scope` (`src/commands/specify/main.md:575-587`); §5 ACs via `add-ac` (lines 522-573). There is currently NO check that a §5 AC or §4 affected-area does not mandate behavior a §6 entry excludes. The coverage rule (line 577) ensures every Phase 1.5 finding LANDS somewhere; it does not check §5↔§6 contradiction. *(Step 3 shipped — now `verify-scope-coherence` (non-blocking warning, Phase 4 Step 4.9) token-overlaps §5/§4 mandate text against §6 OOS terms and surfaces a §5↔§6 contradiction candidate.)*
- **`/plan` Key Design Decisions** are authored by the architect (`src/commands/plan/main.md:294-330`) and transcribed into the plan's table (lines 386-390: `decision | chosen | why | rejected`). The architect's specialist-consult sub-questions (lines 321-326) ask "which layers / decisions with multiple approaches / dependency risks / constitution risks" — none asks "is this concern in scope per §6?" or "what is the MINIMAL change for the in-scope ACs?". There is no backstop tracing each decision's rationale to an in-scope AC. *(Step 4 shipped — now `/plan` Phase 1.3 asks the minimality + §6-scope sub-questions and Phase 2.5 runs a prose-first OOS-respect trace of each decision's rationale; the mechanized `plan_helper` check is DEFERRED.)*

---

## How the 6 pieces fit together (dependency map)

- **Steps 1 + 2** are research-schema + research-spec FOUNDATIONS. Step 1 adds the verbatim prompt to both handoff schemas. Step 2 adds the `requirement` vs `suspected_cause` separation + confidence-gating in `/research`. They are independent of each other but both feed Step 5.
- **Step 5** (the intake interrogation gate, the capstone) CONSUMES Steps 1 + 2: it binary-classifies the verbatim prompt (needs Step 1) and routes a suspected-cause statement to the hypothesis lane (needs Step 2). The hypothesis lane is the ONLY new classification Step 5 introduces — `requirement` is everything else and flows to the existing rubric unchanged. Build 1 + 2 before 5.
- **Step 6** ENFORCES Step 5: making research/discover mandatory before `/specify` is what makes the Step 5 gate unbypassable. Build 5 before 6 (a mandatory gate with nothing behind it is pure friction).
- **Steps 3 + 4** are downstream BACKSTOPS, independent of 1/2/5/6 and of each other. Step 3 adds a `/specify` §5↔§6 scope-coherence check. Step 4 adds a `/plan` out-of-scope-respect backstop + minimality re-framing of the architect's consult prompts. They catch an over-solve that slips the upstream gate; they do not depend on the gate existing.

Recommended build order: **1, 2, 5, 6, then 3, 4** (foundations → capstone → enforcement → backstops). Steps 3 and 4 may land in either order or in parallel.

---

## Step 1 — Carry the verbatim prompt into the research + discover handoffs

**✅ SHIPPED** — `verbatim_prompt` field added to both research + discover `Intent` schemas (v1.1, back-compat tolerate-missing-on-read) + `set-verbatim-prompt` setter + Phase 0.3 wiring in both commands; finalize populates from the persisted field.

**Owner**: python-engineer → python-reviewer (schema + helper), then instruction-author → instruction-reviewer (spec wording for the new field's provenance).

**Files touched**:
- `src/devforge/lib/_research/handoff_schema.py` — extend the `Intent` dataclass (lines 254-265).
- `src/devforge/lib/_discover/handoff_schema.py` — extend the `Intent` dataclass (lines 209-223).
- `src/devforge/lib/_research/` + `src/devforge/lib/_discover/` — add a new `set-verbatim-prompt` setter verb to each helper that persists the full raw `$ARGUMENTS` to the command's state file (helper-owns-shape; confirm the exact state-setter module against the installed verb set when implementing).
- `src/commands/research/main.md` — add a `set-verbatim-prompt` call at Phase 0.3 (right after `set-topic`, before the rubric) persisting the full raw `$ARGUMENTS`; populate the handoff field at finalize (Phase 4 `finalize-handoff`, lines 855-871) from THAT persisted field, not the one-sentence topic.
- `src/commands/discover/main.md` — add the parallel `set-verbatim-prompt` call at Phase 0.3 persisting the full raw `$ARGUMENTS`; populate at its finalize (Phase 4.0, `discover_helper finalize-handoff`, `src/commands/discover/main.md:470`) from the persisted field.
- Tests: `tests/lib/_research/` + `tests/lib/_discover/` (round-trip via the real `finalize-handoff` producer, not hand-authored fixtures, per the test-immediately-after-write rule).

**Rationale / argument**: The verbatim prompt is the only artefact that lets a downstream stage tell what the user ACTUALLY asked for from what an upstream stage INTERPRETED. Today the handoff carries paraphrases (`symptom_summary` / `desired_summary`) — a downstream auditor cannot recover the original to check fidelity. Adding the raw prompt makes requirement-vs-interpretation auditable at every stage (Steps 3, 4, and 5 all read it). The verbatim prompt is the boundary input the constitution's §139 rule names; storing it unmodified is the precondition for validating it.

Why a NEW field rather than reusing `symptom_summary`: `symptom_summary` is a curated paraphrase the rubric produces; the raw prompt is the un-curated boundary input. Conflating them destroys exactly the distinction this plan needs. The new field is append-only context, never edited by downstream stages.

**Concrete change**:
- Add `verbatim_prompt: str` (required, non-empty after strip) to BOTH `Intent` dataclasses. Validate in `__post_init__` with the existing `_require_nonempty` helper (matches the file's established validation idiom — every required string field in these schemas is checked that way).
- Bump `SCHEMA_VERSION` from `"1.0"` to `"1.1"` in BOTH schemas (OQ-1 RESOLVED: back-compat). On read, `verbatim_prompt` is tolerated-missing so any pre-existing `"1.0"` `handoff.json` still loads — the field is required when WRITING a new handoff (validated in `__post_init__` as below) but its absence on an older record is not a load error. Implement the tolerate-missing-on-read branch in the schema's deserialization path (confirm the exact load idiom against the file's existing optional-field handling when implementing).
- Add a `set-verbatim-prompt` setter to BOTH helpers, called at Phase 0.3 immediately after `set-topic` (before the rubric), persisting the full raw `$ARGUMENTS` to the state file. This is a DISTINCT field from the one-sentence topic `set-topic` records: the "Suspected cause:" sentence lives in the full `$ARGUMENTS` and is otherwise lost after Phase 0.3 (only the paraphrased topic survives). Setter/getter language: the helper owns the field; the orchestrator does not hand-write JSON.
- In `research_helper finalize-handoff`, populate `Intent.verbatim_prompt` from the persisted `verbatim_prompt` state field (the value `set-verbatim-prompt` recorded), NOT from the topic.
- In `discover_helper finalize-handoff`, populate `Intent.verbatim_prompt` from the persisted `verbatim_prompt` state field, NOT from the discover topic.

### Verify

```bash
# Both Intent dataclasses declare the new field.
grep -n "verbatim_prompt" src/devforge/lib/_research/handoff_schema.py src/devforge/lib/_discover/handoff_schema.py
# Expect: a field declaration + a _require_nonempty check in each file.

# A set-verbatim-prompt setter persists the full $ARGUMENTS (distinct from set-topic).
grep -rn "set-verbatim-prompt\|verbatim_prompt" src/devforge/lib/_research/ src/devforge/lib/_discover/
# Expect: a setter verb writing the raw prompt to state + finalize-handoff reading
# it from THAT field (not from the one-sentence topic).

# The spec wires the setter at Phase 0.3, right after set-topic.
grep -n "set-verbatim-prompt" src/commands/research/main.md src/commands/discover/main.md
# Expect: a Phase 0.3 call immediately after set-topic, before the rubric.

# Round-trip test exists and passes (real producer, not a hand fixture).
# Run the research + discover handoff test suites; expect green with a new
# assertion that finalize-handoff emits a non-empty verbatim_prompt equal to
# the full $ARGUMENTS the helper was seeded with (NOT the paraphrased topic) —
# the assertion must use a fixture whose full prompt differs from its topic
# (e.g. a "Suspected cause:" tail) so a topic-vs-prompt regression is caught.
```

**Forward references created by this step**: Step 5's classification reads `Intent.verbatim_prompt`; Steps 3 and 4 may cite it when checking fidelity. The `SCHEMA_VERSION` bump is settled (OQ-1 RESOLVED: `"1.0"` → `"1.1"`, `verbatim_prompt` tolerated-missing on read).

---

## Step 2 — Separate `desired` (requirement) from `suspected_cause` (hypothesis); confidence-gate propagation

**✅ SHIPPED** — pre-rubric suspected-cause classifier at Phase 0.4 (research `record-hypothesis`; discover `record-gap --dimension integration_points`, divergence documented) + `verify-hypothesis-suppression` check (label-based exemption; honest scope: identifier-reuse, not paraphrase → Step 5) + `_shared/text_overlap.py` shared tokenizer.

**Owner**: python-engineer → python-reviewer (schema + helper rubric machinery), then instruction-author → instruction-reviewer (Phase 1 rubric + propagation wording in `/research`).

**Files touched**:
- `src/commands/research/main.md` — Phase 1 rubric (lines 76-86) gains an explicit hypothesis lane; the Phase 2.5 hypothesis-enumeration wiring (lines 495-543) and the Phase 3 recommended-approach setters (lines 711-792) gain a propagation gate.
- `src/commands/discover/main.md` + `src/devforge/lib/_discover/` — the parallel pre-rubric suspected-cause classifier (Step 5's discover mirror routes `hypothesis` classifications here, so the lane must exist in discover too). Discover gets the same pre-rubric suspected-cause-as-hypothesis capture (OQ-2 RESOLVED: pre-rubric classification, not a rubric dimension); whether discover ALSO carries the full tier/discriminator gate or only the routing lane depends on whether discover's scoping uses the `Probe` machinery (confirm against `_discover/` when implementing).
- `src/devforge/lib/_research/handoff_schema.py` — represent a suspected-cause as a confidence-graded hypothesis that, when unverified, does NOT populate `plan_seeds` design direction (it lands as an open question instead).
- Tests: `tests/lib/_research/` + `tests/lib/_discover/`.

**Rationale / argument**: A mechanism a user (or research) *guesses* is an input to investigation, not an output of it. The pipeline conflated the two: the suspected cause arrived as prose and exited as the recommended fix without ever being confirmed. The rubric must give a suspected cause its own lane (so it is not silently absorbed into `symptom`/`desired`), and the EXISTING tier/discriminator machinery must GATE whether that lane reaches design. A low-tier (`2`/`3`) or discriminator-unresolved hypothesis propagates as "confirm before designing," never as a requirement.

Why reuse the existing `Probe`/`tier`/`Discriminator` machinery rather than invent a new confidence field: the machinery already exists and already classifies (`_research/handoff_schema.py:781-847`, `compute_confidence_grade` lines 205-246). The defect was never missing classification — research correctly graded the race tier-3. The defect was that classification did not GATE propagation. Wiring the existing tiers to suppress propagation is the minimal change; a parallel confidence system would be redundant machinery (a KISS violation, and ironically the same over-build pattern this plan exists to prevent).

**Concrete change**:
- **Suspected-cause lane (pre-rubric classification, OQ-2 RESOLVED)**: capture a `suspected_cause` as a PRE-RUBRIC prompt-classification, NOT a 7th rubric dimension — a user- or research-supplied mechanism is auto-detected from the "Suspected cause:" lead-in (and equivalents) in `$ARGUMENTS` BEFORE the six-dimension rubric runs, and recorded as a HYPOTHESIS, never as `desired`. The classified suspected-cause feeds Phase 2.5 hypothesis enumeration; it never enters `symptom`/`desired` or any rubric dimension. The captured suspected-cause MUST become a `record-hypothesis` entry with a falsifier (the existing Phase 2.5 mechanism), so it is treated as a claim to disprove, not a fact. (This pre-rubric classifier is the home Step 5's binary-classification gate routes `hypothesis` statements into — Step 5 is the user-facing front door over this same lane.)
- **Propagation gate (named mechanism: `verify-hypothesis-suppression`)**: routing a hypothesis to an open question describes WHERE it goes; the gate is what ENFORCES that an unverified mechanism does not also reappear as design direction. Add a new verify check (named in the file's established `verify-*` / numbered-check idiom, in the style of the existing checks 8–18) that mechanically: (a) reads each recorded hypothesis whose probe tier resolved to MEDIUM/LOW (per `compute_confidence_grade`) OR whose discriminator is unresolved; (b) token-overlaps that hypothesis's cause-text against `plan_seeds.recommended_approach_summary`; (c) exits non-zero on a match (the unverified mechanism leaked into design direction). The recovery: the author moves the mechanism into an open question ("confirm <mechanism> before designing") and removes it from the recommended-approach summary. Policy restated: a suspected-cause hypothesis may become the recommended approach ONLY when its tier resolves to a confirming grade (tier `1`/`1.5` confirmed → HIGH) OR the discriminator resolved it; otherwise it is an open question and `plan_seeds.recommended_approach_summary` MUST NOT encode it. **Honest scope of this check (do not over-trust it):** the token-overlap is a MODERATE mechanical backstop — it catches a leaked mechanism only when the approach REUSES the cause's identifiers/vocabulary (the common case, since an approach summary usually names the API/symbol it changes). It does NOT catch pure semantic paraphrase: a recommended approach that re-encodes the same mechanism in entirely different words shares zero tokens and passes (the plan's own abstract trip-wire — "Promise<void>" vs "widen the outcome" — shares no tokens). Paraphrase leakage is caught by Step 5's echo-back human gate, NOT by this check. The built helper + tests already document this limitation; this qualifier exists so a future implementer does not trust the check to catch paraphrase.
- **Schema support**: ensure an unverified suspected-cause has a structured home in the handoff that is clearly NOT design direction — i.e. it surfaces under `spec_seeds.open_questions` (the existing `OpenQuestion` record, `_research/handoff_schema.py:360-372`) rather than under `plan_seeds`. Confirm the OpenQuestion shape suffices; if a "hypothesis-to-confirm" needs a distinct marker, that is an additive schema decision (surface to orchestrator).

**Concrete trip-wire (must hold against the real case)**: the testForge20 prompt's "Suspected cause: getConfigurationItems returns Promise<void> …" graded tier-3 → under this gate it propagates as an open question "confirm the Promise<void> mechanism before designing," and the recommended-approach summary may NOT carry "widen the outcome to carry success/failure inline." Use this as the regression assertion.

### Verify

```bash
# A pre-rubric classifier gives suspected-cause its own lane (not symptom/desired,
# not a rubric dimension — OQ-2 RESOLVED: pre-rubric classification).
grep -ni "suspected" src/commands/research/main.md
# Expect: a pre-rubric lane that records a mechanism guess as a hypothesis with a
# falsifier and feeds Phase 2.5, captured before the six-dimension rubric runs.

# The verify-hypothesis-suppression check gates propagation by tier/discriminator.
grep -ni "verify-hypothesis-suppression\|propagat" src/commands/research/main.md
# Expect: a check token-overlapping each MEDIUM/LOW-grade-or-unresolved hypothesis's
# cause-text against plan_seeds.recommended_approach_summary, exiting non-zero on a match.

# Regression: tier-3 suspected cause lands as an open question, NOT plan_seeds direction.
# Run the research handoff suite; expect a test asserting that a tier-3
# suspected-cause produces an OpenQuestion and an empty/neutral
# recommended_approach_summary w.r.t. the unverified mechanism.
```

**Forward references created by this step**: Step 5's minimality challenge + classification depend on the suspected-cause lane existing. Step 4's `/plan` backstop flags any decision whose rationale references an unverified hypothesis — this step is what makes "unverified hypothesis" a typed, detectable thing rather than free prose.

---

## Step 3 — `/specify` scope-coherence check (§5/§4 must not mandate what §6 excludes)

**✅ SHIPPED** — `verify-scope-coherence` non-blocking warning (§5/§4 vs §6 token-overlap; reuses `_shared/text_overlap`), wired at Phase 4 Step 4.9 + IMPORTANT RULE 11.

**Owner**: python-engineer → python-reviewer (a new `specify_helper` verify check), then instruction-author → instruction-reviewer (Phase 4 wiring + IMPORTANT RULES note).

**Files touched**:
- `src/commands/specify/main.md` — Phase 4 Step 4.9 verifiers (lines 677-695) gain a scope-coherence check; the §6 Step 4.5 (lines 575-587) and the IMPORTANT RULES (lines 797-809) reference it.
- `src/devforge/lib/_specify/` — the helper subpackage that owns the verify checks (confirm the exact module against the installed `specify_helper` verb set when implementing).
- Tests: `tests/lib/_specify/`.

**Rationale / argument**: The clearest single artefact of the over-solve was the §5↔§6 contradiction: §5 mandated "branch on outcome to avoid the shared slot" while §6 marked the slot's concurrency-hardening Out of Scope. A spec that simultaneously requires and excludes the same concern is internally incoherent, and that incoherence is exactly what licenses the downstream over-build (the implementer obeys §5; §6 is ignored because §5 is "a contract"). A mechanical check that no §5 AC / §4 affected-area mandates behavior a §6 entry excludes catches this at spec-authoring time, before the contradiction propagates.

Why mechanizable rather than left to LLM judgment: the contradiction is a token-overlap signal between §6 OOS terms and §5/§4 mandate text. This reuses the same token-overlap TECHNIQUE the helper already runs in `check-constitution-compliance` (token-overlap of MUST/SHALL lines against ACs, `src/commands/specify/main.md:692-695`) — and takes the SAME non-blocking posture (OQ-3 RESOLVED: non-blocking warning): like `check-constitution-compliance`, this check surfaces warnings and does NOT fail the verify. The token-overlap is a heuristic that will surface false positives, so a hard gate would cry wolf; the hard human gate is the Step-5 echo-back, and this §5↔§6 check is a warning backstop behind it. Reusing the proven token-overlap approach keeps the check honest (mechanical, not "the LLM thinks it looks fine").

**Concrete change**:
- Add a `verify-scope-coherence` check (named in the file's established `verify-*` idiom) to the Phase 4 Step 4.9 verifier sequence. For each §6 Out-of-Scope entry, extract its salient terms; flag any §5 AC `statement` or §4 affected-area `impact` whose text mandates behavior over the same terms. A flag is a contradiction candidate.
- On a flag: the check surfaces a WARNING (OQ-3 RESOLVED: non-blocking; mirror the `check-constitution-compliance` warning posture, NOT the hard-gate exit-non-zero posture of the other Step 4.9 verifiers) with stderr naming the §6 entry + the conflicting §5/§4 entry. The warning does not fail the verify. Recovery (advisory, surfaced to the author): reconcile — EITHER drop the §6 OOS entry (the concern is actually in scope) OR weaken/remove the §5/§4 mandate (the concern is actually out of scope). The check must not auto-resolve; the warning prompts a conscious reconciliation (the over-solve happened because nobody was prompted to reconcile).
- This is a token-overlap heuristic, so it WILL surface false positives (a §6 entry and a §5 AC sharing a noun without truly conflicting). That is precisely why the posture is a non-blocking warning rather than a hard gate (OQ-3 RESOLVED): a hard gate on a heuristic would block on false positives and erode trust in the gate that matters; the hard human gate is the Step-5 echo-back, and this check is a warning backstop behind it.

**Concrete trip-wire**: against the testForge20 spec, "§6: overlapping-load race hardening — out of scope" + "§5: WHEN a section's load fails, the system shall branch on the load outcome [to avoid the shared slot]" must flag (both reference the load-outcome/slot concern).

### Verify

```bash
# A scope-coherence verify check exists and is wired into Step 4.9.
grep -n "scope-coherence\|verify-scope-coherence" src/commands/specify/main.md
# Expect: the check named in Phase 4 Step 4.9 + referenced near §6 Step 4.5.

# Regression: a §5 AC that mandates a §6-excluded concern flags.
# Run the specify suite; expect a test with a synthetic spec whose §5 mandates
# what §6 excludes → verify-scope-coherence surfaces a non-blocking WARNING
# (OQ-3 RESOLVED) without failing the verify, and a clean spec produces no warning.
```

**Forward references created by this step**: none downstream — this is a self-contained backstop. It cites the existing `check-constitution-compliance` token-overlap mechanism as prior art for the TECHNIQUE; the posture is settled as the SAME non-blocking warning (OQ-3 RESOLVED: non-blocking warning).

---

## Step 4 — `/plan` out-of-scope-respect backstop + minimality re-framing of architect consults

**✅ SHIPPED** (prose-first v1) — `/plan` minimality + §6-scope architect sub-questions + Phase 2.5 OOS-respect trace (PROSE-FIRST, OQ-4) + architect.md Rule 9 extended to OOS-respect + consult minimality framing. The mechanized `plan_helper` token-overlap check remains DEFERRED (future, gated on empirical miss-rate).

**Owner**: instruction-author → instruction-reviewer (the `/plan` + architect spec wording). OQ-4 RESOLVED: prose-first — the v1 backstop is LLM-prose-only, so this step ships through the instruction-author loop ALONE. The python-engineer → python-reviewer loop is engaged ONLY in a LATER deferred mechanization pass (a `plan_helper` token-overlap check), gated on empirical miss-rate — not in v1.

**Files touched**:
- `src/commands/plan/main.md` — Phase 1.3 architect sub-questions (lines 321-326) + Phase 2.5 cross-reference (lines 443-455) + the Key Design Decisions template (lines 386-390).
- `src/agents/architect.md` — the consult sub-question framing (the architect emits the consult requests; its prompts must aim at minimality, not robustness-against-edges). Touch the "How to consult" section (lines 81-87) + Rule 9 minimal-scope (lines 134-139, 153) which already names minimal scope — extend it to OOS-respect.
- `src/devforge/lib/_plan/` — NOT touched in v1 (OQ-4 RESOLVED: prose-first). DEFERRED: the mechanized OOS-respect check (a `plan_helper` token-overlap scan of decision rationales against the spec §6 OOS terms) lands in a later pass only after empirical miss-rate justifies it.
- Tests: `tests/lib/_plan/` — DEFERRED with the mechanized check (none in v1).

**Rationale / argument**: Two distinct fixes here, both at link 4 of the chain.

(a) **OOS-respect backstop**: every Key Design Decision must trace to an in-scope AC or constraint. A decision whose `Why` rationale references a §6 Out-of-Scope concern (or an unverified hypothesis from Step 2) is solving something the spec excluded — flag it. In v1 this is an LLM-prose check (OQ-4 RESOLVED: prose-first): the Phase 2.5 cross-reference reads each decision's rationale and flags one that reaches into §6 OOS. It is *mechanizable* as a token-overlap scan of decision rationales against §6 OOS terms — DEFERRED to a later pass, gated on empirical miss-rate; Decision (a) in the testForge20 plan ("removes the overlapping-load slot race") would trip either form, because "overlapping-load … race" overlaps the §6 OOS entry. This complements the architect's existing state-cardinality forcing step (Rule 9) — that step checks states map to ACs; this checks rationales don't reach into OOS.

(b) **Minimality re-framing**: the architect's specialist-consult prompts currently invite over-solving by their framing. A consult that asks "is branching robust against the race?" pulls the specialist toward hardening the race — which §6 excluded. Re-frame the consult sub-questions toward minimality: "what is the MINIMAL change that satisfies the in-scope ACs?" and "is this concern in scope per §6?" The framing change is cheap and addresses the link-4 mechanism directly (the consult that solved the OOS race).

Why both, not just one: the backstop (a) CATCHES an OOS-reaching decision after it is drafted; the re-framing (b) PREVENTS the consult from generating one. Defense in depth at the link where the over-solve actually crystallized.

**Concrete change**:
- Add to `/plan` Phase 1.3 architect sub-questions a minimality + scope pair: (1) "What is the MINIMAL change that satisfies the in-scope ACs?" (2) "For each design decision, is the concern it addresses in scope per the spec's §6 Out of Scope?" The architect returns these alongside its existing rows.
- Add to Phase 2.5 (Plan-Spec Cross-Reference Check) a step: for each Key Design Decision, confirm its `Why` rationale traces to an in-scope AC/constraint and does NOT reference a §6 OOS term or an unverified hypothesis. Flag any that does. In v1 this is an LLM-prose step the orchestrator performs by reading the decision rationales (OQ-4 RESOLVED: prose-first). The mechanized form — a `plan_helper` token-overlap check scanning decision rationales against §6 OOS terms (same idiom as Step 3) — is DEFERRED to a later pass, built only after empirical miss-rate justifies it ("mechanizable" is a capability claim, not a v1 mandate).
- In `src/agents/architect.md`, extend Rule 9 (minimal scope) to explicitly include OOS-respect: a decision may not address a concern the spec marked Out of Scope; if the architect believes an OOS concern MUST be addressed, it escalates to the user (spec-level ambiguity, per the architect's existing termination rule) rather than silently solving it. Re-frame the "How to consult" guidance so emitted consult sub-questions ask for the minimal in-scope solution, not robustness against excluded edges.

**Concrete trip-wire**: against the testForge20 plan, Key Design Decision "widen `getConfigurationItems` to a discriminated outcome — removes the overlapping-load slot race" must flag: its rationale ("removes the overlapping-load slot race") references the §6 OOS concern.

### Verify

```bash
# /plan asks the minimality + in-scope-per-§6 sub-questions.
grep -ni "minimal\|out of scope\|§6\|in scope per" src/commands/plan/main.md
# Expect: the two new architect sub-questions + the Phase 2.5 OOS-trace step.

# The architect charter forbids solving an OOS concern (escalate instead).
grep -ni "out of scope\|out-of-scope\|minimal" src/agents/architect.md
# Expect: Rule 9 extended to OOS-respect + escalation, consult framing toward minimality.

# v1 ships NO plan_helper OOS-respect check (OQ-4 RESOLVED: prose-first).
grep -rn "oos\|out-of-scope\|scope-respect" src/devforge/lib/_plan/ 2>/dev/null || true
# Expect in v1: no match (the mechanized token-overlap check + tests are DEFERRED
# to a later pass, gated on empirical miss-rate).
```

**Forward references created by this step**: v1 is prose-only (OQ-4 RESOLVED: prose-first). In the prose-only v1, Step 2's typed "unverified hypothesis" is advisory at the plan phase — the LLM-prose backstop reads the decision rationales by hand to flag a decision that references an unverified hypothesis, and the OOS-term flagging works without any typed input. The DEFERRED mechanized pass would consume Step 2's typed "unverified hypothesis" to flag such decisions mechanically (the OOS-term scan works without Step 2; the unverified-hypothesis scan would need it) — that is future work, gated on empirical miss-rate. Either form names the architect's existing Rule 9 as the extension point, not a new rule.

---

## Step 5 — Intake interrogation gate in `/research` (and `/discover`) — THE CAPSTONE

**✅ SHIPPED** — intake-interrogation gate at Phase 0.5 (binary classify + minimality challenge + echo-back + bounded one-correction confirm) in both commands + `record-intake-classification` + `render-intake-echo` helpers; proportionality stated as a hard requirement.

**Owner**: instruction-author → instruction-reviewer (the gate is a spec-phase addition); python-engineer → python-reviewer for any helper support (classification persistence, echo-back render).

**Files touched**:
- `src/commands/research/main.md` — a new intake-interrogation phase BEFORE the Phase 1 rubric proper (or folded into Phase 0.3/Phase 1 entry — surface the placement to the orchestrator; the gate must run before investigation commits).
- `src/commands/discover/main.md` — the mirror gate before discovery scoping.
- `src/devforge/lib/_research/` + `src/devforge/lib/_discover/` — helper support for classification capture + echo-back render (helper-owns-shape: the orchestrator composes the classification values; the helper owns the structure + the echo-back render).
- Tests: `tests/lib/_research/` + `tests/lib/_discover/`.

**Rationale / argument**: Steps 1–4 each fix one link; Step 5 is the validation-at-the-boundary itself — it interrogates the prompt before any link runs. It is the capstone because it consumes Steps 1 (verbatim prompt) + 2 (hypothesis lane) and is the thing Step 6 makes unbypassable. The gate has three parts:

(a) **Binary classification** — classify each prompt statement as one of TWO classes: `hypothesis/suspected-cause` vs `requirement` (everything else). Auto-detect the "Suspected cause:"-style lead-in (and equivalents) → route to Step 2's pre-rubric suspected-cause classifier (its home; OQ-2 RESOLVED: pre-rubric classification, not a rubric dimension — Step 2 owns the lane mechanics); everything else is a requirement and flows to the rubric as it does today. This is where the testForge20 prompt's suspected-cause gets pinned as a hypothesis at the front door, not 3 links downstream. (Deliberately NOT a five-type taxonomy: the traced root cause is a two-class problem — hypothesis-vs-requirement conflation. A `context`/`constraint` split would duplicate the rubric's existing `unchanged_behavior`/`scope` dimensions, and an `out-of-scope` class would need an unwired §6 pre-seed; the binary is the minimal classification that fixes the failure — and avoids the over-build pattern this plan exists to fight.)

(b) **Minimality challenge** — state the SIMPLEST change that satisfies the stated *desired outcome* alone. Any addition beyond it (a guessed mechanism, an empty-vs-failure distinction, a new state) must be CONSCIOUSLY opted into, with the user's confirmation. This directly targets the two over-build artefacts (inline-items mechanism + empty-vs-failure split) — both are "extras" the minimality challenge would force into the open.

(c) **Echo-back confirmation** — show the user the classified interpretation (requirements / hypotheses-to-verify / minimal-fix) and get ONE confirmation before proceeding. The user is the authority on which extras are real; the echo-back is how the gate surfaces the framework's interpretation for correction. This is what actually closes the original failure: in the over-solve the user never saw — and so could never correct — the framework's interpretation.

**Calibration requirement (state explicitly in the spec — this is a hard requirement, not advice)**: the gate is PROPORTIONATE. Auto-classify the easy parts; surface to the user ONLY the high-stakes ambiguities — conflations (requirement mixed with hypothesis), scope-expanders (an extra distinction/state not in the desired outcome), and big-design-driving hypotheses (a mechanism guess that would shape the architecture). It is NOT a 20-question inquisition. A clean prompt with no hypothesis, no scope-expander, and a single obvious minimal fix passes with one echo-back confirmation and zero interrogation. The research rubric already scales (turn caps, accept-gaps); the intake gate inherits that proportionality. Over-interrogating a trivial bug is its own failure mode — and, again, ironically the same over-build pattern this plan fights.

Why reuse Steps 1 + 2 rather than re-implement classification: the verbatim prompt (Step 1) is the gate's input; the hypothesis lane (Step 2) is where a `hypothesis` classification routes. Building classification from scratch here would duplicate Step 2's lane (DRY violation). The gate is the USER-FACING front door over the machinery Steps 1–2 install.

**Concrete change**:
- Add an intake-interrogation phase that runs after the topic is captured (Phase 0.3) and before the rubric investigation commits cost. It: (1) reads the verbatim prompt (Step 1's field, held in state), (2) classifies each statement into the binary (hypothesis vs requirement — auto-detect the "Suspected cause:" lead-in per Step 2's markers), (3) renders a minimality challenge (the simplest change for the desired outcome) + the classification as an echo-back block (helper-rendered, copied verbatim to the user per the established verbatim-echo convention), (4) asks ONE confirmation (AskUserQuestion: `["confirm", "correct"]` — on `correct`, the user adjusts the classification, then re-echo once). The `hypothesis` statements route to Step 2's lane; everything classified `requirement` flows to the rubric exactly as the prompt does today (the gate does NOT re-route requirements into new rubric dimensions — the rubric already owns `desired`/`unchanged_behavior`/`scope`).
- Mirror the gate in `/discover` against its 8-dimension scoping (`functional_scope`, `non_goals`, etc. per `_discover/handoff_schema.py:595-625`) — a greenfield prompt's scope-expanders + any "we should also …" speculative additions get the same minimality challenge + echo-back.
  - **NOTE (discover lane divergence — do NOT mirror `/research` here):** discover's `hypothesis`-routing lane is `record-gap --dimension integration_points` (the pre-rubric classifier already in discover Phase 0.4), NOT a `record-hypothesis` call. `/discover` has no `record-hypothesis` verb — that is `/research`-only. A Step-5 builder routes a classified `hypothesis` to discover's `record-gap --dimension integration_points` call and must NOT add `record-hypothesis` to `/discover`. Discover's leak backstop is the Phase 2 fit-check + this Step-5 echo-back, NOT a `verify-hypothesis-suppression` gate (which does not exist for `/discover`). This divergence is also stated in `src/commands/discover/main.md` Phase 0.4.
- Helper support: a classification record + an echo-back render verb (helper-owns-shape). The orchestrator composes the per-statement classification values; the helper owns the echo-back block structure.

**Concrete trip-wire**: against the testForge20 prompt — the "Suspected cause: …" sentence classifies as `hypothesis`; the desired outcome ("render empty section + error toast, never leak prior items") classifies as `requirement`; the minimality challenge states "branch the render on load-failure; show empty + toast" with NO inline-items mechanism and NO empty-vs-failure split; the echo-back surfaces the suspected-cause as "hypothesis to verify, not a requirement." The user confirms the minimal interpretation and the over-build never seeds.

### Verify

```bash
# An intake-interrogation gate exists in both commands, before investigation commits.
grep -ni "intake\|classif\|minimality\|echo-back\|hypothesis" src/commands/research/main.md src/commands/discover/main.md
# Expect: a phase that classifies each prompt statement into the binary
# (hypothesis vs requirement), runs a minimality challenge, and echoes back for
# one confirmation.

# Proportionality is stated as a hard requirement, not advice.
grep -ni "proportion\|not a 20-question\|high-stakes\|inquisition" src/commands/research/main.md
# Expect: explicit calibration language (auto-classify easy parts; surface only
# conflations / scope-expanders / big-design hypotheses).

# Helper owns the echo-back render shape (orchestrator does not hand-author it).
grep -rn "intake\|classif\|echo" src/devforge/lib/_research/ src/devforge/lib/_discover/
# Expect: a classification setter + an echo-back render verb.
```

**Forward references created by this step**: consumes Step 1 (`Intent.verbatim_prompt`) and Step 2 (the hypothesis lane — the ONLY new classification this gate introduces). Step 6 makes this gate unbypassable. The binary classification adds no `out-of-scope` pre-seed for `/specify` §6 (dropped deliberately — that wiring does not exist and §6 is owned by `/specify`); out-of-scope handling stays where it already lives (Step 3's §5↔§6 coherence check + Step 4's OOS-respect backstop).

---

## Step 6 — Make research/discover mandatory before `/specify`

**✅ SHIPPED** — `/specify` Phase 0.4 BLOCKs without a research/discover handoff (`find-handoffs --require`, exit 2, NO override per OQ-5); trade-off + standalone-exemption noted; `src/CLAUDE.md` reconciled (research/discover moved into the spec flow; `/discover` un-mis-classified).

**Owner**: python-engineer → python-reviewer (the `/specify` preflight gate change), then instruction-author → instruction-reviewer (Phase 0.4 wording + the trade-off note).

**Files touched**:
- `src/commands/specify/main.md` — Phase 0.4 Handoff discovery (lines 94-114) becomes a hard gate: a research OR discover handoff must exist before Phase 1 runs.
- `src/devforge/lib/_specify/` — the `find-handoffs` / preflight verb that backs the gate (confirm the exact module against the installed verb set).
- `src/CLAUDE.md` — the `/specify` catalog entry (lines describing `/specify` in the consumer overlay) + the workflow-flow diagram (the `(per feat)` annotations) must reflect that research/discover is no longer `(optional)` for the spec pipeline.
- Tests: `tests/lib/_specify/`.

**Rationale / argument**: The Step 5 intake gate lives in `/research` and `/discover`. If `/specify` can run cold (which it can today — Phase 0.4 line 102 "proceeding cold"), a user bypasses the entire intake gate by skipping straight to `/specify`. Making a research OR discover handoff a precondition for `/specify` is what makes Step 5 unbypassable — the gate is only as strong as the weakest entry path.

**The trade-off (state it explicitly, with mitigation)**: a mandatory gate adds a required step before every spec. The mitigation is PROPORTIONALITY (the same principle as Step 5): the research rubric scales DOWN to a quick pass for a trivial bug (turn caps + accept-gaps already exist, `src/commands/research/main.md:165-191`), so "mandatory" does not mean "heavyweight." A two-sentence bug still goes through research, but research for it is a 30-second pass, not a full investigation. The gate accepts research OR discover (discover covers greenfield where research's bug/enhancement framing does not fit) — so neither track is excluded.

**Scope of the gate (explicit non-gating — prevent over-application)**: this gate applies ONLY to the spec pipeline (`/specify`). The standalone lightweight flows — `/fix`, `/refactor`, `/audit`, `/security` — are SEPARATE flows outside the spec pipeline and are NOT gated by this. `/fix` already escalates to `/specify` when a bug grows beyond 5 files (`src/CLAUDE.md` `/fix` entry); that escalation path enters the gated pipeline at the `/specify` boundary, which is correct. Do not add the research-handoff gate to the standalone flows — they exist precisely to bypass the heavy pipeline for small, localized work. NOTE (verified 2026-06-07): of the four standalone flows only `/audit` exists as a source spec (`src/commands/audit/`); `/fix`, `/refactor`, `/security` are among the workflow commands not yet ported into `src/commands/` (per the repo-root `CLAUDE.md` active-plans note). So the "do not gate the standalone flows" rule is forward-looking for three of them — apply it when those commands are built, and confirm the exemption holds for `/audit` now. **AMENDMENT (2026-06-19):** the standalone enumeration above is stale. Current reality: the standalone group is `/audit` ALONE — `/refactor` was dropped (plan 21) and `/security` dropped 2026-06-19 (both never-emitted pre-pivot drafts), while `/fix` was reintroduced and ported (plan 26) but is a non-linear proposal-only remediation loop OFF `/review`/`/verify`, not a standalone-group member. The "do not gate the standalone flows" rule stands; re-confirm the live set against `src/CLAUDE.md` on edit.

**Concrete change**:
- Change Phase 0.4: on zero handoff hits, instead of "proceeding cold," the gate BLOCKS — emit a message instructing the user to run `/research "<topic>"` (for a bug/enhancement against existing code) or `/discover "<idea>"` (for a greenfield feature) first, then re-invoke `/specify`. End the turn. (Mirror the Phase 0.1 setup-chain BLOCKED posture, lines 36/40 — verbatim stderr block + end turn.)
- Keep the existing one-hit / multi-hit selection flow (lines 104-110) for the NON-zero case unchanged — that path already works; only the zero-hit branch changes from continue to block.
- NO cold-spec override (OQ-5 RESOLVED: no override). The gate offers no escape hatch even for the "already-researched-externally" case — any override re-opens the bypass Step 5 closes, and the intake gate must run on every entry path to be unbypassable. The mitigation for the externally-researched case is PROPORTIONATE research, not a bypass: the user runs `/research` (or `/discover`), but the rubric scales DOWN to a fast pass that still runs the Step-5 intake gate (echo-back included), so the prompt is still validated at the boundary. This is the same proportionality the trade-off note above relies on — applied here as the answer to "I already researched this myself."
- Reconcile `src/CLAUDE.md`: the workflow diagram annotates `/research` and `/discover` as `(optional)` (the consumer overlay's Spec-Driven Development Flow). After this step they are no longer optional for the spec pipeline — update the annotation + the `(optional)` notes in the `/research` and `/discover` catalog entries. Cross-check: the closing messages of `/research` (`src/commands/research/main.md:878-882`) and `/specify` Phase 0.4 wording must not contradict the new mandatory posture.

### Verify

```bash
# /specify Phase 0.4 blocks on zero handoffs (no "proceeding cold").
grep -n "proceeding cold\|No recent handoff" src/commands/specify/main.md
# Expect: the zero-hit branch now BLOCKS (run /research or /discover first), not continues.

# The trade-off + proportionality + standalone-not-gated note is present.
grep -ni "proportion\|mandatory\|standalone\|fix.*refactor.*audit\|not gated" src/commands/specify/main.md
# Expect: explicit trade-off + the /fix /refactor /audit /security exemption.

# CLAUDE.md no longer calls /research and /discover optional FOR the spec pipeline.
grep -n "(optional)" src/CLAUDE.md
# Expect: the /research + /discover spec-pipeline annotations reconciled (standalone
# uses still legitimate; the spec-pipeline-precondition framing is updated).

# Standalone flows are NOT gated (regression guard).
# Only src/commands/audit/ exists today; fix/refactor/security are not yet ported
# (the loop tolerates missing dirs via 2>/dev/null). Apply the guard to each as it lands.
grep -rn "research.*handoff\|find-handoffs" src/commands/audit/ src/commands/fix/ src/commands/refactor/ src/commands/security/ 2>/dev/null || true
# Expect: no research-handoff precondition added to any standalone flow that exists.
```

**Forward references created by this step**: enforces Step 5 (the gate behind which Step 5 lives). Depends on Step 5 existing (a mandatory gate with no intake interrogation behind it is friction without payoff — build 5 first).

---

## Open Questions (all RESOLVED 2026-06-07, user-approved — each OQ's original question is kept for context; the decision is appended below it. The dependent Steps have been reconciled to match.)

- **OQ-1 (Step 1)** — `SCHEMA_VERSION` bump: adding a REQUIRED `verbatim_prompt` field breaks any already-emitted `handoff.json`. Bump `"1.0"` → `"1.1"` and tolerate the missing field on read (back-compat), or hard-break and require re-running upstream? Architectural; settle before Step 1 ships.
  - **→ RESOLVED: back-compat.** Bump `SCHEMA_VERSION` `"1.0"` → `"1.1"`; `verbatim_prompt` is tolerated-missing on read so old `handoff.json` files still load. No hard-break. Rationale: a hard-break would orphan every in-flight handoff for zero benefit — tolerate-missing-on-read costs one optional-field branch and preserves the pipeline.
- **OQ-2 (Step 2)** — suspected-cause shape: a 7th rubric dimension, OR a pre-rubric prompt-classification that feeds Phase 2.5 hypothesis enumeration? Affects where the lane lives and how Step 5 routes to it.
  - **→ RESOLVED: pre-rubric auto-classification.** The suspected-cause lane is a pre-rubric prompt-classification (auto-detect "Suspected cause:"-style lead-ins) that feeds Phase 2.5 hypothesis enumeration — NOT a 7th rubric dimension. Rationale: a 7th dimension would force a mechanism guess through the six-dimension requirement rubric; pre-rubric classification keeps the hypothesis lane and the requirement rubric cleanly separated, which is exactly the separation this plan exists to enforce.
- **OQ-3 (Step 3)** — scope-coherence posture: hard gate (forces reconciliation, risks false-positive blocks) or non-blocking warning (preserves flow, can be ignored)? The over-solve argues hard gate; calibration argues don't-cry-wolf.
  - **→ RESOLVED: non-blocking warning.** The `/specify` scope-coherence check is a non-blocking warning, not a hard gate. Rationale: it is a token-overlap heuristic that will surface false positives; the hard human gate is the Step-5 echo-back, and §3/§4 are warning backstops behind it. Crying wolf on a heuristic at spec-authoring time would erode trust in the gate that actually matters.
- **OQ-4 (Step 4)** — mechanize the OOS-respect backstop now (a `plan_helper` token-overlap check) or ship LLM-prose-only first and mechanize after empirical miss-rate justifies it? The brief calls it "mechanizable" — capability, not mandate.
  - **→ RESOLVED: prose-first.** Ship the `/plan` OOS-respect backstop as LLM-prose-only first; mechanize (a `plan_helper` token-overlap check) only after empirical miss-rate justifies it. Rationale: "mechanizable" is a capability claim, not a mandate — building the helper in v1 risks the over-build pattern this plan fights; prose-first lets the miss-rate data decide whether the helper earns its keep.
- **OQ-5 (Step 6)** — cold-spec override: allow an explicit override for a legitimate externally-researched cold spec, or no override (stricter, closes the bypass entirely)?
  - **→ RESOLVED: no override.** A research OR discover handoff is mandatory before `/specify`, full stop — no cold-spec override. Rationale: any override re-opens the bypass Step 5 closes. The "already-researched-externally" case is mitigated by *proportionate* research (a fast rubric pass that still runs the Step-5 intake gate), not a bypass — the intake gate must run on every entry path or it is not unbypassable.

---

## When resuming work

1. **Re-read this plan in full** before touching any file — it encodes the root-cause chain that justifies each step; a step edited without the chain in mind tends to re-introduce a different link's defect.
2. **Confirm the current-state facts still hold** (the "Current-state facts" subsection cites exact line numbers as of 2026-06-07). The four source specs (`research`, `discover`, `specify`, `plan` main.md) and the two handoff schemas are under active development on `develop-2.0-init` — re-grep the cited identifiers/line ranges before relying on them. If a cited line moved, update the citation as part of the resuming change (cross-check discipline).
3. **All five Open Questions are RESOLVED** (2026-06-07, user-approved — see the `## Open Questions` section; each OQ names its gating step and carries its decision). Build each step to the resolved decision: OQ-1 back-compat `SCHEMA_VERSION` `"1.0"` → `"1.1"` (Step 1), OQ-2 pre-rubric suspected-cause classification (Step 2), OQ-3 non-blocking warning (Step 3), OQ-4 prose-first OOS-respect backstop (Step 4), OQ-5 no cold-spec override (Step 6). Do not re-litigate a settled OQ; if implementation surfaces a reason a decision no longer fits, escalate to the user rather than silently diverging.
4. **Build order (HISTORICAL — all steps now shipped)**: the steps landed in dependency order 1, 2 (foundations) → 5 (capstone, consumes 1+2) → 6 (enforces 5) → 3, 4 (independent backstops). Each was gated by its own `### Verify` block + the framework's reviewer loops (python-engineer→python-reviewer for helpers/schemas; instruction-author→instruction-reviewer for spec docs).
5. **Implementation is COMPLETE — all 6 steps SHIPPED** (2026-06-07, working tree on `develop-2.0-init`). The only remaining future work is Step 4's DEFERRED mechanized `/plan` OOS-respect check (prose-first v1 shipped; mechanization gated on empirical miss-rate) + the testForge20 e2e of the new mandatory-handoff gate (Step 6). The `### Verify` blocks (per step) and the build-order map (item 4 above) are now HISTORICAL — they describe how each step was confirmed DONE, not work still pending. The original "Every step is DESIGN here" framing no longer holds.
6. **Carry the trip-wires as regression assertions.** Steps 2, 3, 4, 5 each name a concrete testForge20-derived trip-wire (the suspected-cause sentence, the §5↔§6 contradiction, the OOS-reaching decision rationale, the minimality interpretation) — each was wired as a test when its step shipped, so the original over-solve cannot recur silently. (Historical build note; the assertions now live in the suites.)
