# 50-GRILL-FALSE-NEGATIVE-BIAS-PLAN

**Status:** Phases 1 (P3) + 2 (P1) SHIPPED in the working tree 2026-07-05 on `develop-2.0-init` (Phase 0 ratified inline below). Phase 3 (P2) remains ratification-GATED (decision record only). Phase 4 (consumer/testForge20 e2e) is the remaining user-driven gate.

Closes a structural false-negative bias in `/grill` surfaced by a design critique of the framework's own gate architecture (this session, 2026-07-04). The critique's thesis was verified against code and **confirmed with one refinement** (see Context). Three fixes, ordered cheapest-first: **P3** a non-blocking stakes-prompter after `/plan`, **P1** a widened high-stakes protected set, **P2** (ratification-gated) N-anchor grounding for emergent defects.

**SHIPPED (Phases 1–2, 2026-07-05):**
- **P3** — `plan_helper stakes-hint` verb (`src/devforge/lib/_plan/_stakes.py`, OR-of-five minority-firing signals; always exit 0, silent no-op on bad input) + `/plan` PHASE-4 wire-in (`plan/main.md`, non-blocking verbatim-echo, path derived from the carried `<plan-path>` sibling) + `grill/main.md:16`+`:389` reconciliation + `src/CLAUDE.md` `/plan`+`/grill` catalog notes. 257 `plan_helper` tests. Reviewer findings fixed: dependency-heuristic negation-object false-positives (nothing/nobody/zero), silent-no-op path robustness, 5th-signal doc completeness.
- **P1** — `[DATA-LOSS]`/`[IRREVERSIBLE]` high-stakes tag (TAG not category, D3). Emission: `design-attack-checklist.md` data-integrity vector (`/grill`-scoped). Routing (universal, D4): `_shared/_consume.py` `_HIGH_STAKES_MARKERS` allowlist (the hardcoded single-marker check would have silently never routed the new tags) + `_shared/_verify.py` `_DATA_LOSS_TAGS`/`_has_data_loss_tag`/dismissed carve-out. Report: `_grill/_report.py` + `report-format.md` Methodology enumerations widened to all four `[CONTESTED]` triggers. `/audit`+`/review` inherit routing but do NOT emit yet (documented follow-on, their report text intentionally unchanged). 234 `_shared` + 393 `_grill` + 269 `_review` + 749 `_audit` tests green, zero regressions. Cross-file tag strings byte-identical across all 7 files (swept).

---

## Context — the thesis, code-grounded

`/grill` reliably catches localized, quotable defects but has a blind spot for systemic / emergent architectural defects (layering violations that only manifest across N files, emergent coupling, invariant erosion, state-machine holes) — the most expensive class. For a tool whose job is "kill a fatally-flawed design while it's cheap," a false-green **PROCEED** manufactures confidence and is worse than no grill. Verified drivers:

| Driver | Verified anchor | Verdict |
|---|---|---|
| Refuter default = not-a-defect unless demonstrable from a verbatim quote | `src/commands/grill/references/refutation-preamble.md:10` ("THE DEFAULT VERDICT IS NOT-A-DEFECT") | **real driver** |
| Only `security` + `[CONSTITUTION-VIOLATION]` are "too costly to default-dismiss" (surfaced `[CONTESTED]` when a refuter can't confirm) | `src/devforge/lib/_shared/_verify.py:88` `_HIGH_STAKES_CATEGORIES = frozenset(["security"])` + `:156` `_has_constitution_tag` | **real driver** |
| Single anchor: every finding quotes exactly ONE artifact; a cross-file partner is named in *unquoted prose* the refuter isn't obliged to credit | `src/commands/grill/references/design-attack-checklist.md:98` ("copy-pasted from exactly ONE artifact") | **real driver — the core** |
| "Single adversary vs up to 3 refuters" (finder outnumbered) | `route_refutation` assigns each finding ONE non-author refuter; the `[code-reviewer, qa-reviewer, security-reviewer]` list is an author-exclusion *pool*, not 3 votes | **OVERSTATED — per-finding ratio is 1:1, NOT a driver** (settled: single finder retained) |

**Precise locus.** The adversary IS instructed to hunt systemic defects (`design-attack-checklist.md:17` layering/SOLID/god-component; `:68` undefined state transitions). The blind spot is downstream: the single-anchor grounding rule + refuter default-dismiss **preferentially kill the emergent findings the adversary does raise**, because no single quoted site is individually damning — the defect is the aggregate. The fix targets grounding + protected-set, NOT finder count.

**Partial mitigation already present (do not over-correct):** the USER owns the verdict at the `/breakdown` approval gate and `/grill` is opt-in/advisory (`grill/main.md:14,16`). A false-green PROCEED *anchors* a human; it does not *auto-advance*. Real harm, but bounded.

---

## Settled decisions (from this session)

- **D1 — Single finder retained.** Head-count is not the bias driver (per-finding ratio is 1:1). No second adversary lens, no second pass. (AskUserQuestion 2026-07-04.)
- **D2 — P2 is ratification-gated.** The emergent-grounding fix is a schema-level project across `_shared/` (shared by `/audit` + `/review` + `/grill`). Full design lands in this plan; build unblocks only on Phase 0 sign-off. (AskUserQuestion 2026-07-04.)
- **D3 — P1 uses a TAG, not a new category.** `CATEGORY_ENUM` (`findings_schema.py:47`) is fixed and shared; extending it threads through every producer/consumer. The precedented cheap path is a marker tag like `[CONSTITUTION-VIOLATION]` — add `[DATA-LOSS]` / `[IRREVERSIBLE]` to the high-stakes predicate. A data-loss finding stays `system_design`/`blind_spot` + the tag, exactly as a constitution violation is `blind_spot` + `[CONSTITUTION-VIOLATION]`.
- **D4 — P1's routing change is universal by design; emission is scoped.** `_verify.py` lives in `_shared/`, so the new tag's headline-surfacing applies to `/audit` + `/review` + `/grill` alike. That is CORRECT (data-loss should never be buried anywhere). Emission (the checklist vector that tells a finder to *write* the tag) is added to `/grill`'s `design-attack-checklist.md` now; `/audit` + `/review` checklists get the vector as a **documented follow-on** (their routing is inert until then — harmless). Named explicitly so a future session does not read the shared-engine change as accidental scope creep.
- **D5 — P3 is a non-blocking HINT, never an auto-gate.** Preserves `/grill`'s "opt-in by construction" stance. Requires reconciling `grill/main.md:16` (see the critical cross-ref below).
- **D6 — P3 is helper-owned.** Threshold logic + hint text live in a testable `plan_helper` verb (helper-owns-shape); the `/plan` wire-in is one Bash call + verbatim echo. Thresholds MUST fire on a *minority* of plans (hint fatigue = the failure mode; a hint that fires on every plan is noise and gets ignored, reproducing "no prompter").

---

## Critical cross-reference (mandatory, must be fixed in Phase 1)

The "no stakes-detector" claim appears at **BOTH** `src/commands/grill/main.md:16` AND `src/commands/grill/main.md:389` (a restatement of the same stance, not a separate concept — `:389` is item 1 of the `## Important rules` section). Both currently read as a flat denial:

> `:16` — "There is NO deterministic stakes-detector, NO forced gate on every `/plan` run, and NO place to 'harden' it into an always-on check."
> `:389` — "Opt-in, never an auto-gate ... There is NO stakes-detector, NO forced gate on every `/plan` run, and NO place to harden it into an always-on check." (note: `:389` omits the word "deterministic")

P3 introduces a deterministic stakes-detector that fires on `/plan` runs. BOTH lines become false unless reworded to distinguish a **non-blocking advisory hint** (which P3 adds) from a **forced auto-gate** (which P3 does NOT add, and which the stance still forbids). Phase 1's instruction-author edit on `grill/main.md` MUST reword BOTH `:16` and `:389` to forbid the forced auto-gate while permitting the non-blocking advisory hint, and the `grep` sweep MUST confirm no other file repeats the "no stakes-detector" claim. `src/CLAUDE.md`'s `/grill` catalog entry (`src/CLAUDE.md:53`, "Optional, opt-in ... run for high-stakes plans") is compatible but should note the hint operationalizes that recommendation.

---

## PHASE 0 — Maintainer ratification gate (SIGN-OFF REQUIRED before any build)

No code until the maintainer ratifies:

1. **P1 tag mechanism + universal routing (D3 + D4).** Confirm the tag names (`[DATA-LOSS]` / `[IRREVERSIBLE]` — or a single `[DATA-LOSS]`), and accept that `_verify.py`'s headline-surfacing change applies to `/audit` + `/review` + `/grill`. **Contingency:** D3, 2.1, 2.2, and "Context for next session" are all written assuming BOTH tags; if the maintainer ratifies the single-`[DATA-LOSS]` alternative here, those four sections MUST be updated to drop every `[IRREVERSIBLE]` reference before Phase 2 starts.
2. **P2 build authorization (D2).** Ratify the N-anchor design in Phase 3 before it is built (or defer P2 to its own future plan). Until ratified, Phase 3 stays a decision record.
3. **P3 threshold philosophy (D6).** Accept "fire on a minority" as the tuning constraint; the exact thresholds are the python-engineer's call with tests.

**Verify:** maintainer records sign-off (or amendments) inline in this section before Phase 1 starts.

**SIGN-OFF (2026-07-04):** RATIFIED. (1) Tag mechanism = **BOTH** `[DATA-LOSS]` + `[IRREVERSIBLE]` (the two-tag path; the single-tag contingency does NOT apply). Universal `_verify.py` routing across `/audit` + `/review` + `/grill` ACCEPTED. (2) P2 stays **GATED** — build this pass ships Phase 1 (P3) + Phase 2 (P1) only; Phase 3 (P2) remains a decision record. (3) "Fire on a minority" threshold philosophy accepted. Build authorized.

---

## PHASE 1 — P3: non-blocking stakes-prompter (SHIP FIRST — cheapest, no engine change)

**Goal:** after `/plan` finalizes, if the plan's own structured signals cross a minority-firing threshold, print a non-blocking "consider `/grill`" hint. Removes the reliance on author self-diagnosis of high-stakes without becoming an auto-gate.

**Signals available (from the just-written `plan-handoff.json` `BreakdownSeeds`, `src/devforge/lib/_plan/handoff_schema.py:242`):** `len(file_impact)` (`FileImpactRow` list), `len(risks)`, `dependencies` (List[str]), plus the sibling `specs/NNN-*/data-model.md` presence (new data model) and a security-keyword scan of `risks` / `key_design_decisions` text. Note: the handoff has no "new vs existing dependency" flag, so "new dependency" is approximated by `dependencies` being non-empty combined with other signals — the helper owns the exact composition.

### 1.1 — `plan_helper stakes-hint` verb (python-engineer → python-reviewer loop)

- New verb in `src/devforge/lib/_plan/` (registered in the `plan_helper` CLI). Input: the `plan-handoff.json` path. Reads `BreakdownSeeds`; infers the `data-model.md` sibling; composes signals; if the threshold is crossed, prints the hint block to stdout and exits 0; if not, prints nothing and exits 0 (silent). Never blocks, never exits non-zero on a well-formed handoff.
- Hint block names WHICH signals fired (e.g. "touches 11 files · new data model · security-relevant risk") and the literal `/grill <plan-path>` next step.
- **Test-immediately (feedback_test_first_python_helpers):** round-trip via the real producer — `plan_helper finalize-handoff` writes a `plan-handoff.json`, then `stakes-hint` reads it. Cover: below-threshold (silent), each single signal, combined signals, malformed/absent handoff (silent no-op, never crash), missing `data-model.md` sibling.

### 1.2a — `/plan` main.md wire-in (instruction-author → instruction-reviewer + claude-code-guide loop, `plan/main.md` ONLY)

- Edits `src/commands/plan/main.md` ONLY (one file per instruction-author dispatch — feedback_intra_file_only_consistency_check). Add a step in PHASE 4 **after** `finalize-handoff` + `commit-artifacts` succeed and **before** the `render-breakdown-handoff` verbatim block (do not inject into that helper-owned block). The step calls `plan_helper stakes-hint <plan-handoff-path>` and, on non-empty stdout, copies it VERBATIM into the user-facing message as a fenced block (feedback_verbatim_echo_directive). Empty stdout → emit nothing.
- Brief the instruction-author with the `grill/main.md:16` + `:389` reconciliation (step 1.2b) as **read-only cross-file context** — it explains WHY the new detector must not read as a forced gate — NOT as an edit target for this dispatch.
- Ships into consumer `.claude/commands/plan/` → routes through claude-code-guide for authoring conventions (feedback_claude_code_authoring_best_practices).

### 1.2b — `grill/main.md` reconciliation (SEPARATE instruction-author → instruction-reviewer + claude-code-guide dispatch, `grill/main.md` ONLY)

- A distinct dispatch editing `src/commands/grill/main.md` ONLY (one file per instruction-author dispatch — feedback_intra_file_only_consistency_check). Reword BOTH `grill/main.md:16` AND `grill/main.md:389` (the critical cross-ref above): reword the "NO stakes-detector" denial → forbid the forced auto-gate while permitting the non-blocking advisory hint P3 adds.
- Ships into consumer `.claude/commands/grill/` → routes through claude-code-guide for authoring conventions (feedback_claude_code_authoring_best_practices).

### 1.3 — Docs reconcile (same phase)

- `src/CLAUDE.md` `/plan` command detail: note the closing stakes-hint. `src/CLAUDE.md` `/grill` entry (`src/CLAUDE.md:53`): note the hint operationalizes the "run for high-stakes plans" prose. `CHANGELOG.md`. Grep sweep for any other "no stakes-detector" / "author decides" claim (feedback_cross_check_after_every_change).

**Verify:**
- `plan_helper stakes-hint` tests pass (below-threshold silent + each signal + malformed no-op).
- A high-signal synthetic `plan-handoff.json` emits the hint; a trivial one emits nothing.
- After the rewording, a wording-agnostic sweep — `grep -rn "stakes-detector" src/commands/grill/main.md` — then MANUALLY confirm every surviving hit (expected: the reworded `:16` and `:389`) reads as "no forced auto-gate" (a non-blocking advisory hint MAY exist) rather than "no stakes-detector exists at all." Do NOT hardcode a specific old sentence string — `:16` and `:389` are worded differently (`:389` has no "deterministic"), so a fixed-string grep would miss one. A wider `grep -rn "stakes-detector" src/` also confirms no OTHER file repeats the flat-denial claim.
- instruction-reviewer + claude-code-guide clean on the `/plan` (1.2a) + `/grill` (1.2b) main.md edits.

---

## PHASE 2 — P1: widen the high-stakes protected set (routing universal, emission scoped to /grill)

**Goal:** a `[DATA-LOSS]` / `[IRREVERSIBLE]` finding a refuter cannot confirm is surfaced `[CONTESTED]` in the headline instead of buried in the appendix — the same guarantee `security` + `[CONSTITUTION-VIOLATION]` already get. Data-loss / irreversible-migration is the same unrecoverable cost class.

### 2.1 — `_shared/_verify.py` routing (python-engineer → python-reviewer loop)

- Add the new tag(s) to the high-stakes determination: extend `_is_high_stakes` (`src/devforge/lib/_shared/_verify.py:143`) so a finding carrying `[DATA-LOSS]` / `[IRREVERSIBLE]` is high-stakes (mirror the `_has_constitution_tag` path, not the `_HIGH_STAKES_CATEGORIES` category path — D3).
- Add the parallel carve-out at the dismissed branch (`_verify.py:620` region) — the same `_verify.py` mechanism that already routes a dismissed `[CONSTITUTION-VIOLATION]` to `contested`: a **dismissed** `[DATA-LOSS]` / `[IRREVERSIBLE]` finding routes to `contested` and gets `[CONTESTED]`-tagged, exactly as the dismissed `[CONSTITUTION-VIOLATION]` case does — so a refuter cannot silently bury a grounded data-loss risk.
- **Test-immediately:** confirmed / dismissed / uncertain × {`[DATA-LOSS]` present, absent}; assert dismissed-with-tag → contested + `[CONTESTED]`; assert NO behavior change for existing `security` / constitution / untagged findings (the `tests/lib/_audit/` + `tests/lib/_review/` + `tests/lib/_grill/` suites are the shared-engine regression net across all three `_shared` consumers — run them, prove green).

### 2.2 — `/grill` emission vector (instruction-author → instruction-reviewer loop)

- Add a "Data integrity / irreversible migration" attack vector to `src/commands/grill/references/design-attack-checklist.md`, mirroring the constitution-violation vector (`:89`): what to QUOTE as Evidence (the plan section declaring the destructive/irreversible schema-or-data change), and the instruction to mark `[DATA-LOSS]` / `[IRREVERSIBLE]` in the `Pattern` line + `Why it's wrong`. Category stays `system_design` / `blind_spot`.
- Update `src/commands/grill/references/refutation-preamble.md` only if the refuter needs to know the new tag exists for its verdict (the routing is downstream in `_verify.py`, so the refuter contract likely needs no change — confirm during the loop and state the result; do not edit speculatively).

### 2.3 — Follow-on note (D4)

- Record in this plan + `src/CLAUDE.md`: `/audit` (`mislogic-checklist.md` / `best-practices-checklist.md`) + `/review` (`emergent-issue-checklist.md`) inherit the `_verify.py` routing immediately but will not EMIT the tag until their finder checklists gain the same vector — a documented, non-blocking follow-on, not a regression.

**Verify:**
- `_verify.py` tests pass; `tests/lib/_audit/` + `tests/lib/_review/` + `tests/lib/_grill/` all green (zero regression on existing high-stakes routing across ALL THREE `_shared`-engine consumers — `_review/_cli.py` imports from `_shared` and `tests/lib/_review/test_report.py` exercises the `_verify.py` routing, so `/review` is affected per D4).
- A synthetic dismissed `[DATA-LOSS]` finding lands in the headline `[CONTESTED]`, not the appendix.
- instruction-reviewer clean on the checklist edit; grep sweep confirms the tag string is consistent across `_verify.py` + the checklist.

---

## PHASE 3 — P2: N-anchor emergent-defect grounding (RATIFICATION-GATED — decision record until Phase 0 signs off)

**Do NOT build until Phase 0 item 2 is ratified.** This is the schema-level fix for the core weakness (emergent findings die at the single-anchor grounding rule). It is designed here so ratification is informed.

### The design

- **Problem restated precisely:** the grounding rule (`design-attack-checklist.md:98`) permits ONE verbatim quote + a prose-named partner. A systemic defect's essence is the *relationship* across N sites; the refuter judges the single anchor and default-dismisses because that one quote can't prove the aggregate. Loosening grounding to "cite the pattern" would reopen the fabrication door the entire `_shared` engine exists to close.
- **Fix — N-anchor, NOT weaker grounding:** allow a finding to carry MULTIPLE anchors, each a *literal verbatim quote* from its own artifact; the defect is the demonstrated relationship among them. Same verbatim discipline (every quote still a literal substring, still re-validated by re-reading the cited file), more quotes. The refuter gets a parallel N-anchor confirm branch: it must find the multi-site relationship demonstrated by the quoted set, not just one line.
- **Blast radius (why it's gated):** the anchor is split across TWO dataclasses. `Finding.file` (`findings_schema.py`) is single-anchor — a lone `file: str`, no `evidence` field. The quote itself rides `ParsedFinding.evidence` (`src/devforge/lib/_shared/_consume.py:63`), the processing-layer record; that field is likewise single-valued. `_consume.py`'s own docstring (`:6-22`) documents the split and the 1:1 conversion at the report boundary. So N-anchor needs a schema extension (a list of `(file, quote)` anchors) on BOTH `ParsedFinding` (the working quote) and `Finding` (the report shape) PLUS the documented `Finding`-conversion boundary in `_consume.py`, rippling through `_consume` (parse), `_validate` (re-read each cited file, confirm each quote is a substring), and the refuter re-key tuple `(File, Line, Pattern, Agent)`. Shared by `/audit` + `/review` + `/grill`.

### Build phases (author only after ratification)

1. **Schema (python-engineer → python-reviewer):** extend the multi-anchor field on BOTH `ParsedFinding` (`_consume.py` — the working record that carries the quote) AND, at the report boundary, `Finding` (`findings_schema.py` — the report shape), not `findings_schema.py` alone; keep the two consistent through the documented 1:1 conversion (`_consume.py:6-22`). Optional field, back-compatible — single-anchor findings unchanged, so existing `/audit` + `/review` behavior is byte-identical when no multi-anchor is present. Tests: single-anchor round-trip unchanged; multi-anchor round-trip; validation rejects a non-substring anchor.
2. **Consume + validate (python-engineer → python-reviewer):** `_consume` parses the multi-anchor block; `_validate` re-reads each cited file and discards the finding if ANY anchor quote is not a literal substring. Tests round-trip via the real finding-emission format.
3. **Refuter contract (instruction-author → instruction-reviewer):** add the N-anchor confirm branch to `refutation-preamble.md` + the emission contract to `design-attack-checklist.md` (the grounding-rule section at `:98`). The verdict re-key tuple stays stable.
4. **Grill wire-in (instruction-author → instruction-reviewer + claude-code-guide):** any `/grill main.md` phase text that describes the single-anchor shape.

**Verify (post-ratification):** existing single-anchor suites byte-identical; a synthetic emergent finding with 3 literal anchors survives validation + refutation and reaches the headline; a fabricated multi-anchor (one non-substring quote) is discarded.

---

## PHASE 4 — Consumer e2e (user-driven, HARD GATE)

Install to testForge20 (or a consumer) and exercise:
- Run `/plan` on a high-stakes synthetic feature → confirm the stakes-hint fires; run it on a trivial feature → confirm silence (P3).
- Run `/grill` on a plan with a data-loss design decision the refuter can't confirm → confirm it surfaces `[CONTESTED]` in the headline (P1).
- (If P2 built) a plan with an emergent cross-file defect → confirm the N-anchor finding survives to the headline.

---

## Ship order

**Phase 1 (P3) first** — no engine change, `/plan` already holds the signals, immediately useful. **Phase 2 (P1) second** — tag routing + one checklist vector, own the cross-command routing blast radius. **Phase 3 (P2) last and only on ratification** — the schema project; do not ship a weaker-grounded shortcut.

---

## Context for next session

- The thesis is confirmed; leg 1 (finder head-count) is a red herring — do NOT add a second finder (D1).
- Every build step routes through the CLAUDE.md loops: python → python-engineer → python-reviewer; command/reference/agent md → instruction-author → instruction-reviewer (+ claude-code-guide for anything shipping into `.claude/`).
- The single most-likely-to-be-missed item is the `grill/main.md:16` reconciliation — P3 is a deterministic detector, and that line currently denies one exists. Fix it in the same phase.
- P1 mechanism is a TAG (`[DATA-LOSS]` / `[IRREVERSIBLE]`), NOT a `CATEGORY_ENUM` addition (D3). The `_verify.py` change is universal across `/audit` + `/review` + `/grill` by design (D4).
- P2 is designed but gated. Its N-anchor approach preserves the verbatim anti-hallucination guard — do NOT reframe it as "cite the pattern loosely."

## When resuming work

1. Confirm Phase 0 sign-off state in this file. If unsigned, do not build — resolve the ratification items first.
2. Start Phase 1.1 (the `plan_helper stakes-hint` verb) via python-engineer with the test cases named in 1.1; loop to python-reviewer until clean.
3. Then Phase 1.2 as TWO separate instruction-author dispatches — NEVER one call handed two files (instruction-author scope is intra-file, feedback_intra_file_only_consistency_check): **1.2a** edits `plan/main.md` ONLY (brief it with the `grill/main.md:16` + `:389` reconciliation as read-only cross-file context, carried in the brief), then **1.2b** is a separate dispatch editing `grill/main.md` ONLY (reword BOTH `:16` and `:389`). Loop each to instruction-reviewer + claude-code-guide.
4. Re-read `_shared/_verify.py:88,143,156,620` before Phase 2 — the line numbers may drift; grep for `_HIGH_STAKES_CATEGORIES` / `_has_constitution_tag` to re-anchor.
