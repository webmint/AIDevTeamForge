# 45 — SEAM TRUST PROPAGATION

**Status:** **NOT STARTED — awaiting Phase 0 maintainer ratification.** No code, no docs. This plan was drafted out of a multi-turn design-critique of Forge's own gate architecture. It delivers FOUR work items AS SEPARATE PATCHES, each followed by an explicit human hardgate (STOP) — never batched. The critical-path order is Step 1 (a TRACE that produces evidence, changes NO code) → Step 2 (caveat-propagation patch) → Step 3 (a structural re-anchor patch that is CONDITIONAL on Step 1's evidence and is NOT pre-specified). The Golden Regression Catalog is off the critical path (cheap, zero-risk markdown) and is the fourth work item. The paraphrase-judge is EXCLUDED, not deferred (see `## Excluded`).

## The governing discipline — every claim ships with its proving command

This plan emerged from an engagement that already produced ONE fabricated assertion (a "byte-identical" claim stated, never run). The lesson is hard-coded into this plan as a rule that binds every step:

> **Every directional / load-bearing claim ships paired, inline, with the exact raw `git` / `grep` / run command whose output proves it.** An unshown check is unfalsifiable. A claim without its raw-command commitment is a defect, to be treated like a failing test — not waved through.

The commands embedded below are the commitments. When a step executes, its raw stdout/exit code IS the deliverable (Step 1 most of all). No step may let an eval, a score, or a "looks right" substitute for the human reading the raw output at the hardgate.

## Problem — trust crosses seams unvalidated

The framework has many places where one stage authors a value, validates it only for SHAPE (enum membership / non-empty / token-overlap), and a downstream stage then SCOPES ITS OWN WORK by TRUSTING that value as ground truth. Two such seams motivate this plan:

- **Seam A (design-fidelity circularity, suspected):** at `/breakdown` PHASE 2.5 an LLM authors a per-element design disposition (`MATCH` / `DEFER-EMPTY` / `STATIC-PLACEHOLDER` / `DEVIATE`) into `specs/[feature]/design-manifest.json`. TWO downstream fidelity gates scope their work by trusting that disposition. An element that SHOULD be `MATCH` but the LLM mistags `DEVIATE` is skipped by both gates — so the check that would catch the misclassification is itself gated by the misclassification. Circular. **Suspected PARTIAL BY AXIS** — see Step 1.
- **Seam E (paraphrase leak):** `/research` validates that its `recommended_approach` rationale does not reuse an unverified hypothesis's VOCABULARY, but the gate's own docstring admits it catches identifier reuse only, NOT semantic paraphrase. A paraphrased leak passes shape validation and is then framed downstream as an "authoritative starting point."

Both seams share the same defect class: **shape-validity treated as correctness-validity at the consuming seam.** Step 2 addresses the class cheaply (a deterministic provenance caveat). Step 3 addresses Seam A structurally — but only IF Step 1's trace proves the circularity is real.

## Settled decisions

- **D1 — Step 1 is a TRACE, sequenced before any fix.** No fix may precede it or batch with it. Its sole deliverable is raw command output that proves (or refutes) the Seam-A circularity live. A suspicion is not a license to patch.
- **D2 — Four separate patches, four human hardgates.** Step 1, Step 2, Step 3, and the Golden Regression Catalog each STOP for a human read before the next begins. No batching.
- **D3 — Step 3's mechanism is left DEPENDENT on Step 1.** Its exact shape is determined by what the trace shows (a spacing-only gap is a narrower fix than a broad one). Step 3 below states constraints only; it does NOT pre-write a mechanism as though the circularity is already proven.
- **D4 — Step 2's caveat flag is anchor-free and deterministic.** It carries NO LLM call in its decision path. It does NOT validate correctness; it records that a value was shape-checked only, so downstream stops treating shape-validity as ground truth. This single flag is also the entire treatment for Seam E.
- **D5 — No LLM-judge is introduced anywhere without a named external anchor** (golden set / CBM graph / `reference.html` / deterministic oracle). The Seam-E paraphrase-judge has no such anchor and is EXCLUDED (see `## Excluded`), not reserved or deferred.
- **D6 — Evals inform, never replace, the human hardgate.** No automated score may auto-pass a STOP.
- **D7 — Step 2 is additive / back-compatible.** New dataclass fields carry defaults so existing handoff JSON round-trips byte-identically; proven by a real-producer round-trip test (not asserted). *(Refined at Step-2 close: the honest assertion pair is old-JSON-lacking-the-field PARSES to the default + current-producer output is STABLE — NOT that an old JSON re-serializes byte-identically once the serializer emits the new field. Proven by `test_old_handoff_json_deserializes_correctness_vetted_defaults_false` + `test_current_producer_output_round_trips_stably`, run through the real producer/parser.)*
- **D8 — manifest disposition is EXCLUDED from the Step-2 caveat flag ON THE ASSUMPTION Step 3 ships and re-anchors the disposition scoping (a dependency CREATED by Step 2, recorded 2026-06-27).** Step 2 deliberately did NOT flag the design-manifest `disposition` (OQ-2) because Step 3 is slated to supersede that path structurally. **This exclusion is only valid if Step 3 actually ships and actually re-anchors the spacing scoping.** If at Step 3's hardgate the spacing re-anchor is judged too invasive and dropped, the disposition path ends up **neither flagged NOR fixed** — seam-A's spacing hole (confirmed live in the Step-1 trace) left fully uncovered. **Consequence: Step 3 is no longer optional cleanup for the disposition path — it is load-bearing, BECAUSE Step 2 skipped flagging it.** A future session MUST NOT read "disposition unflagged" as "disposition safe." If Step 3 is abandoned, the fallback obligation is to flag the manifest disposition with the Step-2 caveat (or otherwise cover the spacing hole) — the hole does not get to silently persist.

## Open questions (enumerated, NOT resolved)

- **OQ-1 — Is the Seam-A circularity total or partial-by-axis?** The hypothesis (Step 1) is PARTIAL: color literals on a mistagged element are re-caught by the manifest-independent Check 1, so only hardcoded SPACING is genuinely silently-skipped. Step 1 RESOLVES this with raw output. Step 3's scope depends on the answer.
- **OQ-2 — Which handoff fields get the Step-2 caveat flag? — RESOLVED 2026-06-27.** The enumeration grep (over `_research/handoff_schema.py`, `_specify/handoff_schema.py`, `_design/_schema.py`) was run; the final set is **`PlanSeeds` ONLY** — the field `correctness_vetted: bool = False` added to the research→plan recommendation carrier. **Excluded with rationale:** (a) `SpecSeeds` — also shape-validated, but has NO documented downstream trust-amplification; the load-bearing reason to flag is `/plan`'s "authoritative starting point" amplifier (`plan/main.md:78,180`), which is specific to the recommendation, so flagging `SpecSeeds` would add annotation noise without closing a confirmed seam. (b) the design-manifest `disposition` — excluded because Step 3 is slated to supersede that path structurally (see **D8** — this exclusion is CONDITIONAL on Step 3 shipping).
- **OQ-3 — Which consumers READ the flag, and how do they surface it? — RESOLVED 2026-06-27.** The `plan_helper` research-plan-seeds render path (`_render_research_plan_seeds`) reads `ps.get("correctness_vetted", False)` and renders an adjacent caveat (`⚠ provenance: shape-checked (token-overlap), NOT correctness-vetted — verify before treating as authoritative`) right after the recommendation line. NO `main.md` edit — the caveat counters `/plan`'s framing by adjacency, not deletion (softening the "authoritative" wording is deferred as a separate `.claude/`-shipping edit, to be done only if the caveat proves insufficient in practice). The design-tokens `match_refs` loader is NOT a Step-2 consumer (Step 3 supersedes that path, per D8).
- **OQ-4 — Where does the Golden Regression Catalog live?** A new repo-root `REGRESSION-ANCHORS.md` vs a section in an existing doc. Resolve at the catalog's hardgate.

## Phase 0 — Maintainer ratification (decision gate, no code)

Present this plan. The maintainer confirms: (a) the four-patch / four-hardgate sequencing (D1, D2); (b) that Step 1 runs and its raw output is read BEFORE Step 3 is authored (D3); (c) the Seam-E paraphrase-judge exclusion (D5, `## Excluded`); (d) the Step-2 candidate field set is subject to the OQ-2 enumeration grep before it finalizes. Until ratification, no build steps are authored.

### Verify

- Maintainer has signed off on the sequencing and the exclusion. Record the sign-off inline here when it happens.
- No work item below has started before this gate clears.

---

## Step 1 — TRACE the Seam-A circularity (evidence only, NO code change)

**Goal:** prove or refute, live and end-to-end, that a hardcoded SPACING value on an element MISTAGGED `DEVIATE` ships UNCHECKED, and is caught when the same element is correctly tagged `MATCH`. The deliverable is raw stdout + exit codes, nothing else. No fix is written in this step.

### The claim chain, each link with its proving command

**Link 1 — Check 5 only inspects `MATCH` elements.** `match_refs` (the set Check 5 scopes to) is built ONLY from elements whose `disposition == "MATCH"`.

```bash
# proves match_refs is MATCH-only — the if-disposition gate
grep -n 'disposition == "MATCH"' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_cmd.py
#   _load_manifest_match_refs_from_json (def at _cmd.py:69); MATCH conditional at _cmd.py:85
grep -n '_MANIFEST_GLOB' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_cmd.py
#   _MANIFEST_GLOB = "specs/*/design-manifest.json" at _cmd.py:66 — the project-wide glob
```

**Link 2 — Check 5's spacing sub-check is its UNIQUE coverage; color is NOT.** Check 1 bans hardcoded COLOR literals on EVERY line regardless of disposition (manifest-independent). Check 5 ALSO re-flags color on MATCH elements — so color is double-covered and does NOT prove circularity. The spacing literal sub-check (px/rem/em on margin/padding/gap/inset/top/right/bottom/left) runs ONLY on MATCH elements AND only when `spacing_scale_available` is True; NO other check covers spacing.

```bash
# Check 1 is manifest-independent (scans every line, no match_refs arg)
grep -n 'def _check1_color_literals' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_scanner.py
#   _scanner.py:324 — takes (source, rel_path, rule); no match_refs parameter
# Check 5 is manifest-keyed and the only home of the spacing sub-check
grep -n 'def _check5_match_token_binding' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_scanner.py
#   _scanner.py:670 — takes match_refs + spacing_scale_available; returns [] when not match_refs
grep -n 'spacing_scale_available' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_scanner.py
#   the spacing sub-check is gated on `if spacing_scale_available:` (~_scanner.py:780), inside the
#   per-MATCH-block loop (margin|padding|gap|inset|top|right|bottom|left at ~_scanner.py:783-792)
# confirm no other check scans spacing literals
grep -rn 'margin|padding|gap' src/devforge/lib/_constitute/_forcing_functions/_design_tokens/_scanner.py
#   expect the ONLY hit to be inside _check5_match_token_binding
```

**Link 3 — the runtime half (`design-auditor`) also scopes by the disposition.** The agent SKIPs `DEVIATE` and compares only the box model for `DEFER-EMPTY`. This is an INSTRUCTION QUOTE, not an execution — the agent cannot be mechanically run, and this step states that honestly.

```bash
# proves the runtime scoping rule exists as agent instruction (quote, not execution)
grep -n 'DEVIATE\|DEFER-EMPTY\|Scope the comparison by the manifest' src/agents/design-auditor.md
#   src/agents/design-auditor.md:31 "Scope the comparison by the manifest";
#   :33 DEFER-EMPTY → box model only; :35 DEVIATE → SKIP
```

### The live trace recipe (the deliverable)

Construct a throwaway temp project (under the session scratchpad, never in the repo) with the minimum to drive the REAL gate:

1. `design/reference.html` — a button carrying `data-ref="cta"` whose correct disposition is `MATCH`, plus a second element `data-ref="ctrl"` (the control, see scenario B).
2. `design/styles.css` — a CSS token source defining spacing tokens (e.g. `--spacing-2: 8px;`) so `spacing_scale_available` resolves True. (Without `token_source_css`, the spacing sub-check is relaxed and the trace cannot isolate the axis — confirm via `_cmd.py` `_load_token_source`.)
3. A component style file (e.g. `src/cta.css`) with a `[data-ref="cta"]` rule containing BOTH a hardcoded SPACING literal (`padding: 13px`) AND a hardcoded hex color (`color: #abc`); and a `[data-ref="ctrl"]` rule containing ONLY a hardcoded spacing literal (`margin: 11px`, no color).
4. `specs/001-x/design-manifest.json` — a manifest. Two scenario variants:
   - **Variant DEVIATE:** `cta` and `ctrl` both tagged `DEVIATE` (the misclassification).
   - **Variant MATCH:** `cta` and `ctrl` both tagged `MATCH` (the correct tag).
5. `.devforge/constitute.json` — enabling `forcing_functions.design_token_provenance` with `enabled: true` and `token_source_css` pointing at `design/styles.css`.

Run the REAL gate twice (once per manifest variant), capturing raw stdout + exit code each time. The gate is invoked through the `constitute_helper` launcher, which dispatches to the `verify-design-tokens` subparser (`"verify-design-tokens"` string at `_constitute/_cli.py:357`; handler bound by `set_defaults(func=cmd_verify_design_tokens)` at `_cli.py:378`):

```bash
# confirm the dispatch path before running
grep -n 'verify-design-tokens\|cmd_verify_design_tokens' src/devforge/lib/_constitute/_cli.py
#   "verify-design-tokens" string at _cli.py:357; set_defaults(func=cmd_verify_design_tokens) at _cli.py:378

# run with the DEVIATE manifest in place, capture raw output + exit code
python3 src/devforge/lib/constitute_helper.py verify-design-tokens \
    --root "$TMP/proj" --config "$TMP/proj/.devforge/constitute.json"; echo "exit=$?"

# swap in the MATCH manifest, run again, capture raw output + exit code
python3 src/devforge/lib/constitute_helper.py verify-design-tokens \
    --root "$TMP/proj" --config "$TMP/proj/.devforge/constitute.json"; echo "exit=$?"
```

**What the deltas prove (the trace must REPORT, not assume):**

- **`cta` (color + spacing):** both runs are expected to exit 2 (the hex color is caught by Check 1 under EITHER disposition). The Seam-A evidence is in the FINDINGS LIST, not the exit code — diff the two stdout findings lists: the spacing finding for `[data-ref=cta]` must appear ONLY in the MATCH run. If it appears in both, the circularity is NOT real and Step 3 is cancelled.
- **`ctrl` (spacing-only) — the clean isolation:** the DEVIATE run is expected to exit 0 clean on `ctrl` (no color to catch, spacing skipped because not MATCH), and the MATCH run to surface the `[data-ref=ctrl]` spacing finding. An exit-code/finding flip on `ctrl` driven solely by flipping the disposition — same source bytes — is the crisp proof the spacing axis is circular.

The trace MUST explicitly state, in its written conclusion, whether the circularity is **total** or **partial-by-axis (color re-covered by Check 1, spacing not)** — this resolves OQ-1 and SIZES Step 3.

### Verify

- The raw stdout + exit code of BOTH runs (DEVIATE and MATCH variants) is captured verbatim and read by a human.
- The conclusion explicitly classifies the circularity as total / partial-by-axis / refuted, citing the spacing-finding delta on `cta` and the exit-code flip on `ctrl`.
- The `design-auditor` runtime half is recorded as an INSTRUCTION QUOTE (`grep` output from `design-auditor.md`), explicitly not an execution.
- No code in the repo changed during this step.

### >>> HUMAN HARDGATE — STOP <<<

Read the raw trace output. Decide: is the circularity real, and is it total or partial-by-axis? Step 3 is authored ONLY after this decision, and ONLY if confirmed. Do not proceed to Step 2 or Step 3 until a human has read the raw output and recorded the verdict here.

**VERDICT — recorded 2026-06-27 (maintainer read both runs' raw stdout).** Circularity **CONFIRMED, partial-by-axis, spacing-only.** Live trace (fixture under session scratchpad, no repo code changed): same `src/cta.css` bytes, gate run twice via `constitute_helper.py verify-design-tokens`, only the manifest disposition flipped. RUN A (`cta`+`ctrl` mistagged `DEVIATE`): 1 finding — color only (`cta.css:3`); both spacing literals absent; exit 2 solely from the color. RUN B (same bytes, correct `MATCH`): 4 findings — adds `cta.css:2` + `cta.css:6` spacing. `ctrl` (spacing-only, no color) is the clean proof: zero findings under `DEVIATE`, surfaces under `MATCH` — the flip is driven solely by the disposition. **Color** is re-caught by the manifest-independent Check 1 (`_scanner.py:324`) in both runs → not circular. **Spacing** is Check 5's sole coverage (`_scanner.py:784`, scoped by `match_refs` built MATCH-only at `_cmd.py:85`) → silently skipped on a mistag → circular. Runtime half accepted as instruction-quote (`design-auditor.md:35` `DEVIATE` → SKIP), not executed. **Consequence for Step 3:** licensed, scoped to the spacing axis only — NOT a wholesale manifest-pipeline rewrite; Checks 1–4 stay untouched. **Order:** Step 2 (caveat propagation) proceeds FIRST (closes the defect class cheaply, back-compat, independent of Step 3); Step 3 gets its own author→review cycle on the mechanism after Step 2's hardgate.

---

## Step 2 — Caveat propagation (first real patch)

**STATUS: DONE 2026-06-27 (python-engineer → python-reviewer CLEAN; maintainer signed off at the hardgate).** Shipped `PlanSeeds.correctness_vetted: bool = False` (`_research/handoff_schema.py`, serialized via `_handoff_build.py` `asdict`, defaulted on absence by `_dict_to_dataclass`) + a deterministic adjacent caveat in `plan_helper._render_research_plan_seeds`. 16 new tests; 173/173 in the two affected modules, run through the real producer/parser via `uv run --with pytest`. Back-compat proven as the honest pair (old-JSON→default + current-producer-stable), no impossible byte-identity claimed (D7). Field set + consumer locked per OQ-2 / OQ-3. **Created dependency D8 — manifest disposition is now load-bearing on Step 3.** The reviewer's one nit (`if not x:` → `if x is not True:` truthiness guard) was applied.

**Goal:** add a deterministic provenance marker to the handoff-schema fields that carry LLM-authored judgments validated only for enum/shape at origin, so a downstream consumer stops silently treating shape-validity as correctness. This is the entire treatment for Seam E.

### Establish the framing this patch neutralizes (proving commands)

`/plan` currently frames the upstream recommendation as an "authoritative starting point" and forbids silent contradiction — strong language applied to a value that was only shape-checked upstream:

```bash
grep -n 'authoritative starting point' src/commands/plan/main.md
#   src/commands/plan/main.md:78
grep -n 'Do not contradict the upstream recommendation silently' src/commands/plan/main.md
#   src/commands/plan/main.md:180
```

The Seam-E gate itself admits it is shape-only:

```bash
grep -n -A 4 'IDENTIFIER/VOCABULARY reuse only' \
    src/devforge/lib/_research/_cmds_render_verify.py
#   match at _cmds_render_verify.py:648; the limitation text continues through :652 (shown by -A 4)
#   — "catches IDENTIFIER/VOCABULARY reuse only, not semantic paraphrase ...
#   Pure-paraphrase leakage is caught by the Step-5 ... human gate"
```

### Enumerate the candidate fields BEFORE finalizing (the OQ-2 grep)

Do not guess the field set. Enumerate the shape-only LLM-authored carrier fields with a grep, then choose:

```bash
# the candidate carriers (starting list — the grep finalizes the set)
grep -n 'recommended_approach_summary\|class PlanSeeds' src/devforge/lib/_research/handoff_schema.py
#   PlanSeeds class at handoff_schema.py:659; recommended_approach_summary field at :666
grep -n 'def validate_element\|disposition' src/devforge/lib/_design/_schema.py
#   validate_element at _design/_schema.py:117 — validates disposition as ENUM only (no correctness)
grep -n 'class SpecSeeds' src/devforge/lib/_specify/handoff_schema.py
#   SpecSeeds at _specify/handoff_schema.py:278 — overview/constraints/etc. shape-validated only
```

Candidate carriers to mark (final set fixed by the grep above, per OQ-2):

- `src/devforge/lib/_research/handoff_schema.py` — `PlanSeeds.recommended_approach_summary` (the field the Seam-E gate checks for vocabulary overlap; validated for token-overlap shape only).
- `src/devforge/lib/_design/_schema.py` — the manifest element `disposition` (validated only as an enum by `validate_element`).
- `src/devforge/lib/_specify/handoff_schema.py` — any `SpecSeeds` field that is LLM-authored prose validated only as non-empty/shape.

### The marker

A deterministic, anchor-free provenance field — e.g. `correctness_vetted: false` (or `provenance: "shape-checked"`) — added as a new dataclass field WITH A DEFAULT, so existing handoff JSON round-trips byte-identically. The flag carries NO LLM call in its decision path; it records origin-validation strength, it does not assert correctness.

### The consumer that READS it (per OQ-3)

Name the consumer in the patch — the lead candidate is `plan_helper render-plan-seeds`, which renders a "shape-checked, not correctness-vetted" annotation alongside the seed so `/plan`'s "authoritative starting point" framing (lines 78, 180 above) is read with the right epistemic weight. The design-tokens `match_refs` loader is a candidate consumer ONLY if Step 3 does not supersede that path.

### Verify

- A real-producer round-trip test proves back-compat: render a handoff through the REAL producer, parse it, and assert pre-existing JSON (without the new field) round-trips byte-identically (D7). Do not assert byte-identity — run the round-trip and show it.

```bash
# the back-compat proof is a test that RUNS, not a claim
python3 -m pytest tests/lib/test_research_handoff_schema.py -q   # the round-trip case (added in Step 2) must parse pre-existing JSON lacking the new field and assert it deserializes byte-identically
```

- The OQ-2 enumeration grep output is recorded; the final marked-field set is justified against it.
- The named consumer renders the caveat — verified by reading the rendered output, not by inspecting the code alone.
- All edits route through python-engineer → python-reviewer (schema/helper) and instruction-author → instruction-reviewer + claude-code-guide (any `main.md` annotation that ships into `.claude/`).

### >>> HUMAN HARDGATE — STOP <<<

Read the round-trip test output and the rendered caveat. Confirm back-compat is proven (not asserted) and the consumer surfaces the flag. Do not proceed until a human signs off.

---

## Step 3 — Structural re-anchor (second patch, CONDITIONAL on Step 1)

**STATUS: DONE 2026-06-27 (python-engineer → python-reviewer → 3-finding fix → re-verified CLEAN; maintainer signed off at the hardgate).** Mechanism: Check 5's SPACING sub-check now scopes on `spacing_scope_refs = (data-refs present in `design/reference.html`, parsed via stdlib `html.parser`) − (DEVIATE elements with a non-empty `deviate_reason`)`, instead of the LLM-authored `match_refs`. Reference absent / unreadable / anchorless → `spacing_scope_refs = None` → byte-identical `match_refs` fallback. DEVIATE rule: exempt iff DEVIATE AND non-empty recorded reason (auditable, non-silent); a bare mistag is caught. Files: `_design_tokens/_cmd.py` (+`html.parser`, `_DataRefFinder`, 4 scope-builder fns, step 10.5), `_design_tokens/_scanner.py` (`spacing_scope_refs` param; spacing/color scoping split). Checks 1–4 byte-unchanged; Check 5 color sub-check unchanged. Verified: 168 `test_design_tokens.py` tests + a 4-case live trace (mistag CAUGHT / reasoned-DEVIATE EXEMPT / no-reference NO-OP / empty-reference FALLBACK no-regression), raw output read at the hardgate. python-reviewer's 3 findings fixed: a silent fail-open regression on empty reference (return `None` not `set()`), the inaccurate "MATCH element" label → "design-referenced element", and a missing regression test. **D8 CLOSED** — Step 3 shipped and re-anchored the disposition scoping, so the Step-2 manifest-disposition exclusion is retroactively valid; the fallback obligation was not triggered.

**Step 1 CONFIRMED the circularity (spacing-only, recorded at the Step-1 hardgate above) — so Step 3 is LICENSED and now ACTIVE.** Scope is locked by the trace verdict: the **spacing axis only** (Check 5's sole unique coverage); Checks 1–4 stay untouched (Check 1 already re-covers color). Mechanism shape is TBD per D3 — the author→review cycle designs it; it is NOT pre-written here.

**LOAD-BEARING (per D8):** Step 3 is no longer optional cleanup. Step 2 deliberately did NOT flag the manifest `disposition`, on the assumption Step 3 re-anchors that scoping. If Step 3 is dropped at its hardgate, the disposition path is left **neither flagged nor fixed** and seam-A's confirmed spacing hole persists uncovered. If Step 3 is abandoned, the fallback obligation (D8) is to cover the spacing hole another way (e.g. flag the manifest disposition with the Step-2 caveat) — the hole does not get to silently persist.

**Authored ONLY because Step 1's trace CONFIRMED the circularity. Mechanism shape is TBD pending the author→review cycle — deliberately NOT pre-specified here.**

If the trace confirms (and per its total / partial-by-axis verdict), break the circularity STRUCTURALLY: make the fidelity check derive dispositions FROM `design/reference.html` — a source already in the repo — instead of trusting the LLM-authored `design-manifest.json` for the scoping decision. The narrower the trace's finding (e.g. spacing-only), the narrower this fix.

**Constraints (the only thing fixed now):**

- It MUST be a structural re-anchoring on `reference.html` (a source the LLM did not get to mistag for this purpose), NOT a new LLM-judge "checking" the manifest. A second LLM scoring the first LLM's manifest shares the author's blind spot — forbidden by D5.
- It MUST NOT introduce any LLM call into the scoping decision path.
- Its scope MUST match the trace's verdict — a partial-by-axis (spacing-only) confirmation licenses a spacing-only re-anchor, not a wholesale rewrite of the manifest pipeline.
- It MUST preserve the manifest-independent Checks 1-4 unchanged (they already work; the trace proves Check 1 re-covers color).

This section is intentionally left as "shape TBD pending Step 1 output." Do not expand it into a mechanism until the trace is read at Step 1's hardgate.

### Verify

- (To be authored after Step 1.) The verify will re-run the Step-1 trace recipe and show that the previously-silent spacing literal on a `DEVIATE`-mistagged element is NOW caught — i.e. the disposition no longer gates the check that would catch its own misclassification. Same raw-command discipline: the proof is the re-run stdout/exit-code delta, not a claim.

### >>> HUMAN HARDGATE — STOP <<<

Read the re-run trace. Confirm the circularity is broken on the axis Step 1 identified, and that Checks 1-4 are unchanged. Do not proceed until a human signs off.

---

## Golden Regression Catalog (off critical path — cheap, zero-risk, ~20 lines markdown)

**Goal:** NAME the three already-verified meta-bug cases as regression anchors so a future refactor does not delete their guards. This is a doc, NOT a fix, NOT code. Do it any time; it has its own hardgate.

The three cases, each cited with the path that VERIFIES it (the path is the commitment — a future session checks the guard still exists by running its test).

All six cited SHAs were resolved live and ALL exist as of authoring (the per-case `git log --oneline -1 <sha>` commands below remain the re-verification commitment for a future session):

```
09bcbf2 Agent pipeline: universal source → per-runtime files (Claude + Codex)
6cc933c feat(design-fidelity): gate visual drift for frontend tasks (plan 40)
ccbd2db feat(specify): import-handoff + find-handoffs + Phase 0.4 wire-in (RESEARCH-HANDOFF Step 6)
8e4c8e9 feat(specify+research): kind-dispatch on handoff helpers (DISCOVER-HANDOFF Steps 4+6)
de3f334 fix(specify): reconcile duplicate/malformed entries at handoff ingestion
f0a9e95 feat(breakdown,design-fidelity): mechanically guarantee the design-manifest trigger (plan 42)
```

- **design-auditor born-orphaned** — an agent named responsible with no command dispatching it (introduced `09bcbf2`, first real dispatch `6cc933c`). Guard: `tests/lib/test_agent_reachability.py`.

```bash
git log --oneline -1 09bcbf2 && git log --oneline -1 6cc933c
ls tests/lib/test_agent_reachability.py
```

- **manifest reference-present-but-absent** — a `design/reference.html`-present feature shipping with no `design-manifest.json` (gate shipped `f0a9e95`). Guard: `tests/lib/test_breakdown_helper.py::test_reference_present_manifest_absent_exits_2`.

```bash
git log --oneline -1 f0a9e95
grep -n 'def test_reference_present_manifest_absent_exits_2' tests/lib/test_breakdown_helper.py
```

- **import-handoff dedup** — duplicate handoff import (introduced `ccbd2db` / `8e4c8e9`, fixed `de3f334`). Guard: `tests/lib/test_specify_helper.py::TestImportHandoffDedupe`.

```bash
git log --oneline -1 ccbd2db && git log --oneline -1 8e4c8e9 && git log --oneline -1 de3f334
grep -n 'class TestImportHandoffDedupe' tests/lib/test_specify_helper.py
```

Pick the location at the hardgate (OQ-4: a new repo-root `REGRESSION-ANCHORS.md` vs a section in an existing doc).

### Verify

- Each of the three guard paths resolves (the `ls` / `grep` commands above return a hit) — proven, not asserted.
- Each cited commit SHA resolves (`git log --oneline -1 <sha>` succeeds). All six were confirmed-resolving as of this draft (output shown under the catalog intro above); re-run them at the hardgate to re-confirm.
- The catalog location is decided (OQ-4).

### >>> HUMAN HARDGATE — STOP <<<

Read the catalog. Confirm all three guards resolve and all SHAs are live. Sign off on the location.

---

## Excluded — the Seam-E paraphrase-judge (NOT deferred, NOT reserved)

An LLM that judges LLM output for SEMANTIC PARAPHRASE leak (the gap the Seam-E gate's own docstring admits at `_cmds_render_verify.py:648-652`) is EXCLUDED from this plan and from any reserved space within it.

- It shares the author's blind spot — an LLM scoring an LLM for paraphrase is a correlated rubber-stamp, not an independent check. This violates D5 (no LLM-judge without a named external anchor).
- It is only legitimate against a MEASURED held-out labeled leak/clean set. That set does not exist and will not be built here.
- Seam E is handled by the Step-2 caveat flag ALONE — downstream at least knows the recommendation is shape-only.

No step in this plan may propose, scaffold, or "leave room for" such a judge. If a future plan wants it, it starts by building the labeled held-out set FIRST — that is a different plan with a different gate.

```bash
# the anchor-absence is itself checkable: there is no held-out paraphrase eval set in the repo
grep -rn 'paraphrase' tests/ 2>/dev/null || echo "no paraphrase eval corpus — exclusion stands"
```

## Context for next session

This plan is NOT an active build — it is a ratification-pending design with a strict sequencing discipline. It addresses a defect CLASS: a value author validates SHAPE only, and a downstream stage SCOPES ITS OWN WORK by trusting that value as ground truth. Two instances motivate it. **Seam A** (design-fidelity): at `/breakdown` PHASE 2.5 an LLM writes a per-element `MATCH`/`DEFER-EMPTY`/`STATIC-PLACEHOLDER`/`DEVIATE` disposition into `specs/[feature]/design-manifest.json`; the STATIC gate `verify-design-tokens` Check 5 (`_design_tokens/_scanner.py:670`, scoped by `match_refs` built MATCH-only at `_design_tokens/_cmd.py:85`) and the RUNTIME gate `design-auditor` (`src/agents/design-auditor.md:31-35`) both scope by that disposition — so an element mistagged `DEVIATE` is skipped by the very check that would catch the mistag. The circularity is SUSPECTED PARTIAL-BY-AXIS: color literals are re-caught by the manifest-independent Check 1 (`_scanner.py:324`), so only hardcoded SPACING (Check 5's unique sub-check, `_scanner.py:~780`, requires `token_source_css`) is genuinely silently-skipped. **Seam E** (paraphrase): `/research`'s overlap gate catches vocabulary reuse but not semantic paraphrase (admitted at `_cmds_render_verify.py:648-652`), yet `/plan` frames the recommendation as an "authoritative starting point" (`plan/main.md:78`, `:180`). The plan's spine: **Step 1** TRACES Seam A live (raw output only, no code) and reports total vs partial-by-axis; **Step 2** adds a deterministic shape-checked-not-correctness-vetted caveat to the carrier fields (handling Seam E entirely); **Step 3** structurally re-anchors the fidelity check on `reference.html` IF and ONLY IF Step 1 confirms — mechanism deliberately unspecified until the trace is read. Four separate patches, four human hardgates, never batched. The paraphrase-judge is EXCLUDED (no labeled held-out set; correlated rubber-stamp). Every load-bearing claim ships with its raw proving command — an unshown check is unfalsifiable.

## When resuming work

1. **Do not skip Step 1.** It is a trace, not a fix. Its raw stdout/exit-code IS the deliverable. Re-confirm the cited anchors against the live tree first (line numbers drift) — run the proving `grep`s in Step 1 before constructing the temp project; do not trust the line numbers in this file without re-running them.
2. **Read Step 1's raw output at its hardgate before authoring Step 3.** Step 3's scope is set by the trace's total / partial-by-axis verdict. Authoring Step 3 before reading the trace re-introduces the exact "stated, not checked" failure this plan exists to prevent.
3. **Run the OQ-2 enumeration grep before fixing the Step-2 field set.** Do not guess which fields are shape-only carriers.
4. **Prove Step 2 back-compat by running the round-trip test** — show the output; do not assert byte-identity.
5. **Keep the paraphrase-judge out.** If it tempts you, the entry cost is a measured labeled held-out leak/clean set, in a different plan.
6. Route every code edit through python-engineer → python-reviewer and every `.claude/`-shipping `main.md` edit through instruction-author → instruction-reviewer + claude-code-guide.
