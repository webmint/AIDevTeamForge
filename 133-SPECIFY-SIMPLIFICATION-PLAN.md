# 133 — Specify Simplification Plan

**Created**: 2026-10-05
**Status**: **Stub — findings recorded, decisions and phases SKETCHED, Phase 0 NOT ratified, nothing built, nothing measured.** The maintainer asked for the audit findings to be saved as the next plan WITHOUT running them through the audit-reaction flow or the instruction-author → instruction-reviewer loop; this file is that record. ⚠ **Numbered 133 because `ls *-PLAN.md` at the repo root on 2026-10-05 ends at 132. Other sessions work in this checkout and may take 133 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-05 and will drift — grep the quoted text, never the digits.** ⚠ **Sequencing**: plans execute in numeric order; plan 124 (pipeline cost reduction) is queued after 106–123 by maintainer directive of 2026-09-28, and this plan's D7 is plan 124 lever 1 narrowed to one helper — see D9.
**Branch:** `develop-2.0-init`

## Origin & evidence

**Maintainer, 2026-10-05 (recorded in English):** asked whether `/devforge:specify` is "too large, overloaded, and whether it contains logical inconsistencies"; then whether it "can be simplified without losing quality — the price is now very high compared to v1"; then: *"just save these findings as the next plan, but do not run it through the flow — I already see on first use that it got longer and harder."* The last sentence is the plan's reason: a first-use observation on a real install, not a benchmark.

**Evidence class, repeated in every summary of this plan:** a full read of `src/commands/specify/main.md` (1035 lines, 132,129 bytes, no `references/`) on 2026-10-05, with every code-level claim verified by reading `src/devforge/lib/_specify/*.py`, `src/devforge/lib/_shared/feature_alloc.py`, `src/hooks/cbm-code-discovery-gate` and `src/settings.template.json`; cost figures taken from `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` (one measured v2 heavy run against a v1 median of 17 runs) and NOT re-measured. The full findings with their `Why it matters` and cross-reference results are in `RESEARCH-2026-10-05-SPECIFY-AUDIT.md` (untracked, repo root); this plan carries the compact form.

**Where `/specify`'s price sits** (diagnosis F3, F7, §2.1): v1 median 50 turns / 0 helper calls / 1 stop / 42 k output / 5.0 M cache-read; v2 heavy run 197 turns / 63 helper calls / 2 stops / 101 k output / 22.8 M cache-read. Cache-read per turn is ≈ 100 k vs ≈ 116 k — nearly equal — so the ×4.5 on cache-read is the ×4 on turns. Assistant turns ≈ 2 × tool calls, so the 63 helper calls are ≈ 126 of the 197 turns. CBM is 0 calls on this command. Stops are at v1 level. Prose at invocation ≈ 33 k tokens (bytes/4).

## Findings (12: 1 high, 5 medium, 5 low, 1 nit bundle)

Line numbers are `src/commands/specify/main.md` on 2026-10-05.

- **F1 — HIGH — `from-here` is a no-op identical to `stay`.** `:75` offers "Create a spec branch from here" and promises creation at Step 4.1; `create-branch` (`_cmds_phase4_setters.py:193`) → `decide_branch_action` (`_shared/feature_alloc.py:1051`) arm 3 returns `keep-other` for a non-default, non-`spec/*` branch: comment on stdout, no checkout, `branch_created=False`. `:19` admits "only its default-branch arm emits a checkout". Cross-ref: `from-here` only in `specify/main.md` (3 hits).
- **F2 — MEDIUM — overloaded.** Second-largest command (132 KB; `research` 207 KB) and the largest with zero `references/` while 11 commands split on-demand text out. Four waste classes: repeated protocol boilerplate (verbatim-echo × 18, picks-none re-ask × 5, non-blocking-warning semantics × 4 + 3, "Single-line question text" × 7, "End the turn" × 9); maintainer history shipped to consumers (`v1`/`v3` × 5, "`use` removed", two "Known limitation" paragraphs, "Stage 2 enhancement", `test_anchor` "currently deferred", "v1 simplification", the HTML authoring comment); rare paths inline (re-entry 13, intake-rerun 9, bucketed 12, genuine-fallback 12 mentions; the five longest lines are 1.9–2.7 k chars at `:657`, `:144`, `:961`, `:856`, `:976`); restatement (IMPORTANT RULES 8/11/12 repeat Step 4.9 a third time; Phase 2's priority order twice).
- **F3 — MEDIUM — Step 4.1 calls the legacy warm path "the normal case".** `:565` vs `:567` ("the shape intake allocated before the bucketed layout; nothing migrates those directories") and `feature_alloc.py:501` (every NEW allocation is `specs/<YYYY>/<MM>/<leaf>`). The bucketed path is the normal case; the Step 4.1 intro (`:563`) and the Step 5.1 / 5.4 path lists inherit the stale framing. Cross-ref: "normal case" 3 hits (`:71`, `:159` correct; `:565` stale). Order of the four paths stays (`:583` explains why).
- **F4 — MEDIUM — greenfield slot `specs/*/discovery-report.md` never auto-matches a bucketed path.** `_cmds_phase3.py:22-36`: `Path.match` right-anchors three components (`specs` ≠ `10`); the substring fallback keeps the literal `*`. Greenfield + bucketed is the only case where the file exists, so `verify-mandatory-reads` exits 2 every time unless the model guesses `--slot-pattern` for a non-sentinel slot (`:498` says sentinels only) or files a false N/A. Cross-ref: pattern in `_schema.py:373`, `_topic.py`, `main.md:518`, `tests/lib/test_specify_helper.py` — read `_topic.py`'s use before changing it.
- **F5 — MEDIUM — "≥3 findings OR marker" has no honest route for 1–2 relevant items.** `_cmds_phase01.py:304-317`: `partial` for 1–2 findings regardless of the marker; no verb deletes a finding; the marker's wording ("nothing task-relevant") forbids the honest reading. Only exit: pad to three, and padded findings must then land in §5–§9. Cross-ref: `mark-source-no-items-relevant` in `_cmds_phase01.py`, `_cli.py`, `main.md`, `tests/lib/test_specify_helper.py`.
- **F6 — MEDIUM — Phase 2's two rules point opposite ways; the second is an escape hatch.** `:342` "Do not skip a decision point because the model has a default preference" vs `:438` "Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings". The DP definition (`:335-340`) and the `--delegated-reply` gate (`:373`) exist so no value the user neither gave nor delegated enters state; `:438` lets the model decide with no setter trace. Cross-ref: phrase only in `specify/main.md`.
- **F7 — LOW — Phase 3 Step 1 precondition gap for discover imports.** `:467` fires only for `handoff_kind == "research"`; `:474` skips only when seeded is false OR type is null; `_cmds_handoff.py:837-838` sets both on a discover import. The origin-based paragraph (`:490`) rescues the run; the stated precondition is incomplete.
- **F8 — LOW — Step 5.2 re-runs three non-blocking checks and omits `verify-scope-coherence`** (`:946-954`) although its own rationale (state changed on `request-changes`) applies; rule 11 (`:1034`) silent too. Cross-ref: `plan/main.md` names the verb once, as a reference — unaffected.
- **F9 — LOW — `set-finding-landed --landed-ref` is unvalidated** (`_cmds_phase4_setters.py:698-745`): a finding can be marked landed on `AC-3` that does not exist and `verify-coverage` passes, against `:835`'s "a typo fails loudly". Cross-ref: `_cli.py`, `_cmds_phase4_setters.py`, `main.md`, `tests/lib/_specify/test_landing.py`.
- **F10 — LOW — `request-changes` re-runs Step 4.10 and re-asks the design source every loop** (`:961`); `set-design-source` is a persisted scalar. Overlaps plan 123 (first ask gated on project type); this is the repeat. Cross-ref: phrase only in `main.md`.
- **F11 — LOW — Phase 3 Step 3 mandates Glob/Grep (`:532`) then forbids them for source discovery (`:539`, `:227`)**; the shipped hook (`src/hooks/cbm-code-discovery-gate`, matcher `Read|Grep|Glob`, fires once per session) says "fall back to Grep/Glob/Read only for non-source text content". Cost: one blocked call + one turn per run and a contradiction. Cross-ref: phrase only in `main.md`.
- **F12 — NIT bundle — stale sentences:** `:29` "Four preflight steps" (six exist); `:978` "Write the handoff artefact first" (the anchor write now precedes it); `:21`/`:976` "immutable design-intent record" vs `:132`/`:976` "overwrites unconditionally"; `:23` "both exist by the time Step 5.4 reaches either commit-artifacts call" is unguarded because `write-design-anchor`'s failure arm (`:976`) never ends the turn. Cross-ref: each phrase only in `main.md`.

## Decisions — recorded, NOT decided

Each carries a recommendation and its strongest counter-argument; each waits for the maintainer.

- **D1 — Drop `from-here` (F1).** Recommend: text-only; options become `["switch-to-default", "stay"]`; add the missing half-sentence that `switch-to-default` then takes the default-branch arm (deferred creation). Counter: teach `decide_branch_action` a fourth arm instead. Rejected in the recommendation because `/research` and `/discover` share the function and neither offers `from-here`, so `/specify` would become the one command that branches off a non-default branch.
- **D2 — Relabel Step 4.1's paths (F3).** Recommend: bucketed = "the normal case for every directory intake allocates today"; warm/cold = "legacy `<NNN>-<slug>` directories (pre-plan-91), kept so they still resolve"; keep the ORDER; put `specs/<YYYY>/<MM>/<leaf>` first in the Step 5.1 / 5.4 path lists. Counter: none of substance — the order's rationale at `:583` is untouched.
- **D3 — Slot pattern `*/discovery-report.md` (F4).** Recommend: change `_schema.py:373` (two right-anchored components match both layouts), update the description, add a two-shape test, update `main.md:518`. Counter: a `__discovery_report__` sentinel — same effect, larger text change.
- **D4 — The marker waives `partial` (F5).** Recommend: `count < 3 and marker → clear`; reword the marker's meaning to "no further task-relevant items"; verb name unchanged. Counter: this loosens variance rule #3. Answer: the forcing function is the explicit per-source assertion, which stays; what goes is the padding incentive. A source with zero findings still needs the marker.
- **D5 — Bridge Phase 2's rules (F6).** Recommend: rewrite `:438` to restrict the DEFINITION — "a choice the codebase or the findings already settle has one valid implementation and is not a decision point; record why under the category's `no_DP_in_category` rationale; a choice with two or more valid implementations is asked, whatever you would pick." Counter: delete `:438` outright. Rejected because the sentence's cost-control intent is legitimate; only its shape is an escape hatch.
- **D6 — Prose diet + references extraction (F2, F7, F8, F10, F11, F12).** Recommend: one `## Conventions` block for the three repeated protocols, cited by name; delete the maintainer-history class; extract to `.devforge/command-refs/specify/` — `re-entry.md` (Phase 0.5 + Phase 0.4 arms (b)/(c)), `header-paths.md` (Step 4.1 bucketed + genuine-fallback limitations), `request-changes.md` (Step 5.3 reset path), `coherence-checks.md` (Step 4.9 trio + Step 5.2); collapse IMPORTANT RULES 8/11/12 to pointers; delete Phase 0.6 (one read + one line the user "is free to ignore"). Predicted 132 KB → 70–80 KB. **Honest bound:** this cuts cache-read per turn by ≈ 10 k of ≈ 116 k and leaves the turn count alone — it is hygiene, not the price. Counter: extraction adds conditional loads the model may skip. Answer: `audit`, `grill`, `review`, `implement` already run that way under plan 63's layout; the condition for each reference is a sixth-field token or a Step 4.1 path the orchestrator already holds.
- **D7 — Turn diet: batch writes + composite verifiers (the price lever).** Recommend four verbs in `specify_helper`, each running the SAME validators the setters run and naming the failing field: `apply-findings --from-json` (Phase 1 reads + 1.5 findings + markers; replaces 40–65 calls with 1–2), `apply-decision-points --from-json` (one per question ROUND, since answers arrive per round; carries the `--delegated-reply` gate and the follow-up cap; replaces 12–20 with 2–4), `apply-spec-sections --from-json` (§1–§9 with every per-entry validator; replaces 35–60 with 1–3; `revise-ac` stays for the loop), `phase4-finalize` + `phase5-recheck` (4 blocking + 3 non-blocking in one call with grouped stderr; precedent: `findings-finalize`, `dp-finalize`, `phase3-finalize` already wrap a verifier). Predicted, static, unmeasured: heavy path 63 → 15–20 helper calls; turns 197 → 90–110; output tokens roughly halved. Counter: per-field calls make the model "think about each field". Answer: the v1 parity-test variance that Phase 1.5 fixed came from ENUMERATION, which survives in the JSON payload; the per-call shape carries no validator of its own. Condition from the diagnosis: a batch that reports only "invalid" costs more turns than it saves.
- **D8 — Validate `--landed-ref` (F9).** Recommend: when given, it must name an existing entry of the bucket; exit 2 otherwise; one clause at `:835`. Counter: make it required. Rejected: the verb's documented use includes landing on an entry written outside the helper.
- **D9 — Queue position.** D1–D6 and D8 are a text-and-small-code plan on their own and do not touch plan 124's levers. D7 IS plan 124 lever 1 narrowed to `specify_helper`, and plan 124 is queued after 106–123 by the 2026-09-28 directive. Recommend: build Phases 1–3 (D1–D6, D8) in numeric order as this plan; hold Phase 4 (D7) until the maintainer either revisits the directive or folds Phase 4 into plan 124's build. Counter: the maintainer's first-use complaint is about the price, and only D7 moves it. The counter is real; the directive is the maintainer's to lift, not this plan's.

## Non-goals — what is NOT cut

The parts the benchmark and plan 81 credited, and that every decision above leaves unchanged: Phase 1.5 findings enumeration; the four-bucket coverage rule; the seven-category decision-point sweep with the `--delegated-reply` gate; the §5.2 reachability citation (plan 81 F3) and the §4 `no-code-change` path evidence (plan 107); the design anchor; the typed specify→plan handoff; the two human stops (DP round, approval). Also out: `/spec-check` and `/grill` (plan 124 L3), fresh-session-per-command (diagnosis F10, L9), the `cold` pick arm.

**The floor, stated once:** after D6 and D7 `/specify` does not return to v1's 50 turns. v1 had no state machine, no findings enumeration and no DP sweep; the residual ≈ 90–110 turns is those three things. Whether that is worth ×2 on turns is unproven on outcome (diagnosis F8: one v2 run, different model; the plan-81 re-run has not happened). The ablation in the diagnosis Part 1 §5 is the only measurement that settles it.

## Phases — sketched, not ratified

### Phase 1 — Text-only fixes (D1, D2, D5, F7, F8, F10, F11, F12)

**Deliverables:** `src/commands/specify/main.md` edits for F1, F3, F6, F7, F8, F10, F11, F12; no helper change. Each edit is a grep-anchored replacement, not a rewrite.

**Verify:** `grep -c 'from-here' src/commands/specify/main.md` → 0; `grep -n 'normal case'` → `:71`-class and `:159`-class hits only, none on the warm path; `grep -c 'CANNOT answer by reading'` → 0; Step 5.2 lists four verbs; `grep -c 'Four preflight'` → 0; `grep -c 'handoff artefact first'` → 0; `grep -c 'immutable design-intent'` → 0; `instruction-reviewer` pass clean (the maintainer waived the loop for WRITING this plan, not for BUILDING it); `scripts/generate.sh` emits without error.

### Phase 2 — Code fixes with tests (D3, D4, D8)

**Deliverables:** `_schema.py` slot pattern + description; `_cmds_phase01.py:_source_coverage` marker-waives-partial; `_cmds_phase4_setters.py:cmd_set_finding_landed` ref validation; tests in `tests/lib/test_specify_helper.py` (both directory shapes for the slot; 1-finding + marker → clear; 0 findings, no marker → none) and `tests/lib/_specify/test_landing.py` (unknown `--landed-ref` → exit 2); `main.md:518`, `:306-313`, `:835` wording; `_topic.py` read and, if it keys on the same literal, updated in the same commit.

**Verify:** `python -m pytest tests/lib/test_specify_helper.py tests/lib/_specify/test_landing.py -q` green; `grep -rn 'specs/\*/discovery-report.md' src/ tests/` → 0 outside `__pycache__`; `python-reviewer` pass clean.

### Phase 3 — Prose diet and references (D6)

**Deliverables:** `## Conventions` block; maintainer-history deletions; `src/commands/specify/references/{re-entry,header-paths,request-changes,coherence-checks}.md` with their load conditions stated at the extraction sites; IMPORTANT RULES 8/11/12 collapsed; Phase 0.6 removed and its one mention in the "Every arm above … reaches it" sentence with it.

**Verify:** `wc -c src/commands/specify/main.md` ≤ 82,000; `grep -c 'VERBATIM into your next user-facing message'` ≤ 3 (the conventions block plus the two gate sites that must stay verbatim by the diagnosis's L7 risk note); `grep -cE '\bv[13]\b'` → 0; `ls .devforge/command-refs/specify/` on a scratch emit shows the four files; every "see Step X" pointer inside the extracted text re-resolved by grep; `instruction-reviewer` pass clean.

### Phase 4 — Turn diet (D7) — HELD per D9

**Deliverables (when released):** the four verbs with their validators and field-naming errors; `main.md` phase sites rewritten to one call each; `tests/lib/_specify/test_apply_*.py` covering every validator the per-field setters run (enumerate them from `_cli.py` first — 58 verbs on 2026-10-05). Measurement: `profile_helper` before/after on one feature, AFTER plan 124 item 7 fixes the F9 marker anchor; otherwise the before/after cannot be segmented.

**Verify:** static count of `specify_helper` invocations in `main.md` ≤ 25; every validator named in `_cli.py` has a batch-path test; measured helper calls on one heavy run ≤ 25.

## Context for next session

### Honest bounds

- Nothing here is measured by this plan. The v2 figures are ONE heavy run from the diagnosis; the v1 figures a median of 17. The maintainer's trigger is a first-use feel on a real install, which this plan does not quantify.
- Every saving under D6 and D7 is a static prediction from counts. The diagnosis's own caveat applies: predictions, not runs.
- The audit read the command's TEXT against its CODE. It did not run `/devforge:specify`; a consumer run may show failures this read missed, and would also show which rare paths (re-entry, intake-rerun, genuine fallback) ever fire in practice.

### Traps

- **Count sweeps under-report.** The same number is phrased differently per file (18 verbatim sites here; the diagnosis counted 28 in research and 37 in breakdown with a different pattern). Re-grep with the exact phrase before relying on any count; never "fix" a count in a finished plan.
- **F4's fix touches `_topic.py`.** It also contains the literal `specs/*/discovery-report.md`; read its use before editing — it may be a render-group key, not a slot, and the two must not be confused.
- **F3's fix must not reorder the four paths.** `main.md:583` gives the ordering rationale; only the labels and the Step 5.1 / 5.4 list order change.
- **Plan 123 overlap (F10).** 123 gates the FIRST design ask on project type; this plan removes the REPEAT on `request-changes`. Tell plan 123's build session.
- **Plan 124 overlap (D7).** Same lever as 124 item 1. Whichever builds first owns the batch validator design; the other rewrites its sites.
- **Concurrent sessions in this checkout.** Commit by explicit path; do not sweep ledgers while another session is mid-build.
- **The user runs `Strict`.** Nothing here keys on `workflow_enforcement`; no lever in this plan is Moderate/Light-only.

### File anchors (2026-10-05, will drift)

`src/commands/specify/main.md` — `:19` outputs branch bullet, `:29` "Four preflight", `:75` Phase 0.2 third arm, `:144` Phase 0.5, `:306-313` ≥3 rule, `:342` / `:438` Phase 2 rules, `:467` / `:474` Phase 3 Step 1, `:498` / `:518` slot table, `:532` Step 3 opening, `:563-583` Step 4.1 paths, `:612-626` branch block, `:657` Step 4.3 paragraph, `:835` verify-coverage bullet, `:856` change-kind, `:946-954` Step 5.2, `:961` request-changes, `:974-978` Step 5.4 anchor/handoff, `:1034-1035` rules 11–12.
Code — `_cmds_phase4_setters.py:193` (`cmd_create_branch`), `:698` (`cmd_set_finding_landed`); `_shared/feature_alloc.py:501` (`allocate_feature_dir`), `:1051` (`decide_branch_action`); `_cmds_phase01.py:304` (`_source_coverage`); `_cmds_phase3.py:22` (`_slot_matches_path`); `_schema.py:373`; `_cmds_handoff.py:837-838`.

## When resuming work

1. Re-check that 133 is still this plan's number (`ls 13[3-9]-*.md`).
2. Read `RESEARCH-2026-10-05-SPECIFY-AUDIT.md` for the full findings; this file is the compact form.
3. Ask the maintainer to ratify D1–D9 (one exchange; the recommendations are stated). D9 decides whether Phase 4 exists in this plan at all.
4. Build Phases 1–3 in order, each through the normal flow (instruction-author → instruction-reviewer for `main.md`; python-engineer → python-reviewer for helper code), committing per phase by explicit path.
5. Do NOT start Phase 4 without the D9 answer.
