# RESEARCH — 2026-10-07 — `/devforge:research` audit: size, logical inconsistencies, simplification, v1 comparison

**Status**: evidence file. **Part 0 (read first) holds the sequence agreed on 2026-10-07 for the next session.** No plan owns it yet — candidate homes are a dedicated `<NNN>-RESEARCH-SIMPLIFICATION-PLAN.md` (the shape `133-SPECIFY-SIMPLIFICATION-PLAN.md` has) or the per-mechanism umbrella plan proposed on 2026-10-07 for all 21 commands. On 2026-10-07 the maintainer asked for the same audit `/devforge:specify` received on 2026-10-05 (`RESEARCH-2026-10-05-SPECIFY-AUDIT.md`), run on `/devforge:research` alone, with v1's `research.md` as a second input. Reaction lines stay `pending` — the findings were saved, not presented one at a time, by the maintainer's instruction. Nothing in `src/` was modified. **Part 4** (added the same day, second pass) holds four further findings (13–16: 1 high, 3 medium), two amendments (to findings 4 and 5) and one cross-command nit (17) from a conformance pass against the live CBM tool schemas and Anthropic's published guidance; its reaction lines are `pending` too. **Part 3 holds two open questions the maintainer added the same day — whether all six rubric questions are needed, and whether CBM is needed at all — which must be answered before Part 2.3's "do not cut" list is ratified.**

**Inputs read in full**: `src/commands/research/main.md` at HEAD `44d9e1c` (1,519 lines, 207,212 bytes, zero `references/`); v1 `.claude/commands/research.md` from `main` (`9eeff96`, 232 lines, 9,566 bytes); `src/devforge/lib/_research/_cli.py` verb table (61 verbs); `src/hooks/cbm-code-discovery-gate`; `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` Part 2 tables (`:81-90`, `:103-109`, `:135-143`, `:299-304`); `src/devforge/lib/_research/_cmds_basic.py` (`cmd_reset_report`), `_cmds_dataflow.py`, `_cmds_handoff.py` (`:207`, `:214`), `_cmds_render_verify.py` (`:976`). Line numbers below are HEAD anchors; locate by heading when they drift.

**Method**: the specify protocol — every sentence against (a) definitional, (b) verifiable now, (c) explicit forward reference; counts by `grep`; every fix carries its cross-ref result; plus one question v1 forces: *what did v1 do in 9.6 KB of what v2 does in 207 KB, and what does each v2 addition buy?*

---

## Part 0 — READ FIRST: the sequence to follow in the next session (agreed 2026-10-07)

**Status of this Part**: the working sequence the maintainer accepted on 2026-10-07 after the model argued it (English paraphrase of the maintainer's idea: *"the command is unstructured and bloated; we write the structure first, then pick from the old version everything that is needed, removing duplication"*). It is NOT yet a numbered plan — no `<NNN>-…-PLAN.md` exists for it and no number is reserved; opening one is the maintainer's call, and plans execute in numeric order. Nothing below has been executed. Nothing in `src/` has been modified.

**The approach in one line**: a skeleton-first rewrite of `src/commands/research/main.md`, ported station by station from the old file through a port ledger, against TODAY's helper (no code change), behavior-preserving except where a finding in Parts 1 / 4 carries a `fix` reaction. Not in-place edits: the file is accreted (b/c/d/e suffixes, the same rule at three to five sites, maintainer commentary), and duplication is a whole-file property that in-place edits cannot remove.

### Step 0 — Four decisions BEFORE the port (one conversation, text policy only)

Deciding them after the port lets the old answers ride through silently.

1. **Rubric: six separate turns or one batched table** — Part 1 finding 3 + Part 3 OQ-1. Reverses a ratified forcing function; the maintainer owns it. The same decision applies to `/discover`.
2. **Phase 2.1 cost gate: keep or delete** — Part 1 finding 6 (plan 124 item 3 already proposes deleting it).
3. **CBM**: NOT decided here — Part 3 OQ-2 waits on plan 127's measurement. For this port CBM stays as-is but ISOLATED: one `CBM tool contract` section (Part 4 finding 13) plus the discovery steps, so a later swap to text search touches one place.
4. **Helper contract: unchanged for this port.** Batch verbs (Part 1 finding 8, plan 124 L1) land later and rewrite the same sites; changing text and helper together doubles the blast radius. Consequence: the new prose keeps today's 74 per-row call shapes.

### Step 1 — The skeleton (~150 lines, reviewed on its own)

Run map (stations in order, every conditional section with its trigger), section names, a `Conventions` block (verbatim-echo, delegated-reply, end-the-turn, the two `none` sentinels, the `file:line` grounding rule — Part 1 finding 4(a), finding 10), the `Verify checks` table (name ↔ number ↔ satisfying step ↔ repair verb — Part 4 finding 16), the `CBM tool contract` (Part 4 finding 13). Naming rules: a section is named by what it PRODUCES or DECIDES, one noun phrase, ≤ 4 words; sequence lives in the run map, never in the heading (no `2.4c`); a conditional section carries its trigger in the name's tail; checks get names (the file already names seven of twenty: caller-enumeration gate, cross-layer rule, anchor gate, single-layer gate, hypothesis-citation gate, literal-archaeology gate, argument-duplication check — extend that style) and KEEP their numbers beside the names, because the helper's stderr prints the numbers. Design the skeleton as the shared INTAKE skeleton: `/discover` is the twin (same rubric, intake, save) and inherits the station names when it is ported.

Proposed section map (working names; adjust at Step 1, not silently during the port):

```
# /devforge:research
Overview · Run map · Conventions · CBM tool contract · Verify checks

## Preflight
  Setup-chain check · Memory read · Index refresh

## Intake
  Topic and verbatim prompt
  Ticket-file input                      (conditional)
  Suspected-cause capture
  Interpretation echo-back
  Grill re-entry                         (conditional; sets attach mode)
  Design reference
  Docs scan for candidate areas
  Symptom rubric                         (six dimensions; conflicts, drift, coverage — shape per Step 0 decision 1)
  Mode detection

## Investigation
  Cost estimate                          (only if Step 0 decision 2 keeps it)
  Docs grounding
  Symptom-site discovery
  Framing challenge
  Sibling-bug sweep                      (today: parallel-pattern sweep)
  Existing-solution search               (today: canonical-pattern search)
  Fix-path helpers and callers
     Helper · Callers and declared total · Caller surfaces and scope
     Dead siblings · Value consumers · No-shared-callers escape
  Handler-to-write chain                 (bug + presentation only)
  Feature surfaces
  Value semantics
  Hypotheses
  Literal archaeology                    (literal-triggered)
  Recording the evidence                 (record-finding rules, rests-on-literal, probe feasibility, probe script)

## Report
  Summary and approaches · Recommended approach · Uncovered surfaces
  Constitution constraints · Complexity and verdict · Evidence lanes
  Verify · Hypothesis-suppression gate · Preview render
  Emission matrix                        (removal-triggered)

## Save
  Save confirmation (feature name, ticket) · Feature directory · Feature branch
  Report file · Probe-script file (conditional) · Emission-matrix file (conditional)
  Handoff and commit · Save recovery (exit 3) · Don't save · Closing message
```

Known doubt in the map: `Recording the evidence` restates today's Phase 2.6, which finding 8's batch verbs would dissolve into the steps that produce findings. Keep it while Step 0 decision 4 holds; merge it when batch verbs land.

### Step 2 — The port ledger (the expensive part; the part that makes this a port and not a retelling)

A table over the OLD file, built station by station: `old section + line` · `the rule, in one line` · `origin incident, when known` (plan 18, plans 73 / 75, benchmark 81, Patch 4 / 5 / 9, sticky-reject's adversarial path, …) · `disposition` = `kept at <new section>` / `merged into <new section>` / `dropped: <reason>` · `new section`. No rule leaves the old file without a row. Part 2.3's "do not cut" list is the seed and is incomplete.

The variant rule: most repeats are VARIANTS, not copies — the 8b rule is stated at five sites with slightly different scope, and Part 1 finding 2's trap lives in that difference. Merging means picking ONE canonical statement and checking that every variant agrees with it; where they disagree it is a decision to record in the ledger, never a silent merge. The ledger says which variant won and why.

### Step 3 — Port station by station

Order: Preflight → Intake → Investigation → Report → Save. Each station: `instruction-author` writes from that station's ledger rows (the ledger IS the brief) → `instruction-reviewer` reads it → one commit per station. Rare arms go to `references/` at once (`re-entry.md`, `click-handler-trace.md`, `literal-archaeology.md`, `emission-matrix.md`, `probe-script.md`, `save-recovery.md` — Part 1 finding 4(c)); the trigger sentence stays inline. The skeleton is step zero of this sequence and its own commit.

### Step 4 — Cross-check (part of the same change, not a later audit)

- The helper's ~150 `Phase N.Nx` / `Step N` / `check N` pointers in `src/devforge/lib/_research/` (docstrings + stderr) are NOT rewritten in this pass (Step 0 decision 4); the `Verify checks` table's number ↔ name column is what keeps a stderr pointer resolvable. Rewrite the pointers with plan 124 L1.
- Three references to research's "Phase 1" outside the file: `src/commands/plan/main.md:83`, `:680`, `src/commands/specify/main.md:492` (counts of 2026-10-07).
- `src/CLAUDE.md` catalog entry for `/devforge:research` (lists no references today). The emitter (`scripts/emitters/claude.py`) needs nothing: `references/` already routes to `.devforge/command-refs/research/`.
- Every helper verb the OLD file named (59 distinct, 74 call sites) is either called in the new file or carries a `dropped` ledger row.

### Step 5 — One live run before the swap

Run the ported command once on a scratch / test install (surgical delivery, no `install.sh`) and read the run against the ledger before it replaces `src/`. Measurement (plan 124 item 7, the profiler anchor fix) is recommended before / after but is not a precondition.

### Done means

- every ledger row has a disposition;
- `instruction-reviewer` clean on every station;
- every old helper verb accounted for (called or `dropped`);
- `main.md` ≤ 600 lines plus references (the published limit is 500 lines for the body — Part 4, amendment to finding 4 — so state the number aimed at);
- the live run passed.

### Constraints that hold throughout

- Behavior-preserving except findings with a `fix` reaction in Parts 1 / 4; anything new (Part 1 finding 9's external research and duplicate detection included) is a separate plan.
- File content stays English; spec edits go author → reviewer; delegation briefs carry the ledger rows, not a summary of them.
- Honest cost: multi-session; the ledger alone may take a session.

### What is still open after this Part

The four Step 0 decisions; whether and when a numbered plan is opened for this sequence; every `Reaction: pending` line in Parts 1 and 4.

---

## Part 1 — Findings (12: 3 high, 5 medium, 3 low, 1 nit)

### 1. `reset-report` is the only repair for three ordinary states — HIGH

- **Location**: `main.md:668-669` (justification vs helper list: *"run `reset-report` and re-record if the justification was premature"*), `:982` (`classify-finding-literal` multi-match: *"`reset-report` plus re-recording is the only correct route"*), `:1075` (probe-script revision: *"run `reset-report` and re-record from scratch, or choose a different `--script-path`"*), `:539` (sticky-reject workaround (b): *"restart `/devforge:research` from scratch to clear rejection state"*). Code: `src/devforge/lib/_research/_cmds_basic.py:47-53` — `cmd_reset_report` writes `default_report_state()`: every Phase 2 and Phase 3 row goes (findings, fix-path helpers, callers, dead siblings, consumer chain, hypotheses, archaeology, approaches). `_cli.py` registers 61 verbs; none removes or updates a row (`grep remove-` → 0).
- **Issue**: each of the three states is reached by an ordinary, correct-looking call — recording the component's own method as a fix-path helper on a presentation bug (then needing the escape, finding 2), two findings on one `surface` + `file:line` (allowed: `record-finding` appends without dedupe, `:982`), a probe script revised after a hypothesis changed. The only sanctioned repair wipes the whole run's state.
- **Why it matters**: the repair re-runs Phases 2.3–2.6 — 30–60 turns and ~45 CBM calls — for a one-row mistake. This is a direct mechanism behind "long" and "dumb": a model that knows the price of a reset either fabricates around the rejection or spends the turns.
- **Fix** (code + text): three targeted verbs — `remove-fix-path-helper --helper-qn` (also drops that helper's `inbound_callers`, `caller_totals` and scope rows; leaves `helper_rejection_log` untouched so sticky-reject keeps its meaning), `remove-finding --surface --file-line [--all]` (same match rule as `classify-finding-literal`), `remove-probe-script --script-path`. Reword `:668`, `:982`, `:1075` to name the targeted verb; `:539` keeps the restart as the LAST option.
- **Cross-ref**: `reset-report` 8 hits in `main.md`, all in these recovery sentences plus Phase 0.3's unconditional reset (`:104`, `:113` — unchanged). Checks 9, 14, 19 read the rows a removal touches — the new verbs must keep `caller_totals` and `inbound_callers` consistent or check 9 fires after a removal. Tests: `tests/lib/test_research_*`.
- **Reaction**: pending.

### 2. Phase 2.4c's presentation-layer rule has no honest exit for a presentation-local fix — HIGH

- **Location**: `main.md:523` (Stopping rule: cross-package traces *"are NOT just allowed, they are REQUIRED when the symptom lives in a presentation-layer file"*), `:653` (check 8b), `:657` (*"For check 8b specifically, the fix is to trace one helper UP through a package boundary"*), `:1141` (*"The LLM's only recovery path in that case is to add a cross-layer helper via Phase 2.4c"*) — versus `:659` (the no-shared-callers escape: *"ONLY when the investigation has confirmed the change touches no existing shared symbol with other callers"*) and `:668` (`record-no-shared-callers-justification` exits 2 once `fix_path_helpers` is non-empty; code `_cli.py:852`, `_cmds_dataflow.py:174`).
- **Issue**: a bug whose fix genuinely lives in the component — a comparator inside the component's own method, a template literal, a wrong class — produces a non-empty same-package helper list the moment the model records the method it found (the natural first call). Check 8b then fires; the two "only recovery" sentences say *add a cross-layer helper*; the escape is refused because the list is non-empty; the only way to an empty list is finding 1's `reset-report`. The model's options are: invent a cross-layer helper (a fabricated fix layer), or reset the run.
- **Why it matters**: this is the shape of the frozen-benchmark evidence file (`81-EVIDENCE-V2-BENCHMARK-RUN.md`, subtitle *"the analysis was right, the inference was wrong"*) — a correct investigation steered into a wrong recommendation by a gate. Whether that incident took this exact path is NOT established here; the path exists in the text regardless.
- **Fix**: (a) finding 1's `remove-fix-path-helper`; (b) `:657` and `:1141` name BOTH exits — *"trace one helper up through a package boundary when the fix needs one; when the fix is presentation-local, remove the same-package helper and record the justification with the concrete reason (`the fix is presentation-local: <what changes>`)"*; (c) `:659` widens the escape's definition from *"touches no existing shared symbol"* to *"changes no shared symbol's signature or contract"* — a label fix touches a shared component without changing a contract. Check 8b's code is unchanged; only the prose and the escape's reach move.
- **Cross-ref**: check 8b is stated at `:523`, `:653`, `:657`, `:1141`, `:1234` (five sites — all five change together). `_cmds_render_verify.py` check 8/8b; `tests/lib/test_research_helper*.py` fixtures for the escape. `/discover` has its own 2.4c twin? — not checked; grep `no-shared-callers` across `src/commands` before the edit.
- **Reaction**: pending.

### 3. Phase 1 mandates six separate human turns that Phase 0.5 calls the failure mode — HIGH (cost)

- **Location**: `main.md:127` (*"A clean prompt … passes with ONE echo-back confirmation and ZERO interrogation. Over-interrogating a trivial bug is itself the over-build failure mode this gate exists to fight."*) versus `:218` (*"ask each dimension question separately and wait for the user's answer in its own turn. Pre-filled input is a STARTING POINT for the `symptom` dimension only"*), `:220` (the anti-rationalization paragraph), `:237` (design-reference question, a seventh prompt), `:279` (*"Wait for free-text reply"*), `:347` (coverage echo, then the user decides continue / accept gaps), `:387` (*"After emitting any AskUserQuestion or free-text prompt in Phase 1, end the assistant turn"*).
- **Issue**: on every run — a one-line bug included — the user confirms the interpretation at 0.5 (1 stop), then answers six questions in six turns about the same prompt, then the design-reference question, then the coverage decision: 8–9 stops before investigation starts. The cost diagnosis measured 12 stops median on `/research` v2 against 4 on v1 (`RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md:105`), and 29 min of answering on one run (`:205`). `:220` exists because the model keeps trying to skip the rubric — the spec records its own friction point.
- **Why it matters**: human stops are where v2's wall-clock goes (idle 6–76 h across the pipeline, per the diagnosis); the rubric re-asks what 0.5 just confirmed; and the maintainer always runs `Strict`, so no enforcement knob buys this back. **This reverses a ratified forcing function** (*"User commitment is per-dimension; that is the forcing function this phase exists for"*, `:218`). The decision is the maintainer's; this finding records the price.
- **Fix** (text only, helper unchanged): a batched rubric. Pre-fill all six dimensions from the verbatim prompt plus the 0.5 classification, render them as one table with the proposed `state` per row, ask ONE question — *"Confirm all six, or name the dimension(s) to correct?"* — and loop only on the named dimensions. Per-dimension commitment survives (the user sees and confirms each value; a corrected row is re-asked on its own), the six `set-<dimension>` calls land in one turn, `--increment-turn` and `check-conflicts` keep working. Fold the design-reference question in as a seventh row (`none` default). Keep `symptom-coverage` as the echo of the confirmed table rather than a separate decision point. Predicted: 8–9 stops → 2 (echo-back, rubric table).
- **Cross-ref**: the six setters, `check-conflicts`, `record-conflict-resolution`, `symptom-coverage`, `symptom-finalize` are unchanged (`_cmds_phase1.py`). The `MANDATORY: never skip the rubric` and `never fabricate a user mode` paragraphs (`:218-220`) are rewritten, not deleted — the batched table is the non-skippable rubric. `/discover` Phase 1 has a parallel rubric — the same decision applies there and should be taken once.
- **Reaction**: pending.

### 4. The command is overloaded: 207 KB, zero references, five waste classes — MEDIUM

- **Location**: whole file. Measured: 207,212 bytes / 1,519 lines ≈ 52 k tokens at invocation (bytes/4). Largest command in the tree (next: `specify` 132 KB); zero `references/` while 11 commands carry them.
- **Issue**, five classes (counts by grep, 2026-10-07):
  1. Repeated protocol boilerplate: *"copy … VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)"* × 33; *"hands the choice/answer back to you (…)"* × 12; *"end the turn"* × 16; `MANDATORY` × 27; *"Honesty bound"* × 4.
  2. Rare paths inline, measured by block: grill re-entry 0.6 = 6.2 KB (`:180-212`); click-handler trace 2.4d = 9.1 KB (`:673-741`, bug + presentation only); literal archaeology 2.5b = 20.7 KB (`:850-947`, fires on a literal only); emission matrix = 10.0 KB (`:1285-1334`, fires on a removal only); Phase 4 = 24.1 KB (`:1336-1519`, where attach mode, exit-3 recovery and the ticket-file third option are rare arms threaded through six steps). ≈ 70 KB, a third of the file, is prose for paths most runs never take. Smaller: the ticket-file arm (`:80-99`), probe-script tier 1.5 (`:1041-1077`), memory-excerpt semantics (`:52-61`).
  3. Maintainer commentary shipped to consumers: `Patch 4` / `Patch 5` / `Patch 9` × 3; `plan 18` × 3; *"pre-flight verified 2026-05-18"* (`:703`); *"That is a v1 simplification; do not add seed-deletion logic here"* (`:210`); *"The OLD same-package restriction is removed"* (`:523`); *"the empirically-validated chain for the seed incident was depth ≤ 6"* (`:582`).
  4. Restatement: the Verify paragraph `:1234` (3,414 chars, the longest line in the file) restates checks 8, 8b, 12a, 12b, 13, 14, 17, 18 already stated at their steps; the `--framing` tagging rule stated five times (`:453`, `:457`, `:481`, `:517`, `:966`); `--rests-on-literal` explained four times (`:725`, `:796`, `:856`, `:968`); check 20's recovery three times (`:945`, `:968`, `:970`).
  5. Long single lines: `:1234` 3,414 chars, `:796` 2,901, `:1246` 1,881, `:856` 1,458, `:144` 1,402.
- **Why it matters**: 52 k tokens ride on every one of the run's 172–258 turns as cache-read (diagnosis `:137`: research v2 17.6–37 M cache-read vs v1 4.8 M; Part 2 §2.1 puts prose at ≈ 25 % of per-turn context). Plan 124 lever 6 (L7, prose diet) names `research` first.
- **Fix**: (a) one `## Conventions` block near the top holding the three repeated protocols (verbatim-copy, delegated-reply, end-the-turn), cited by name; (b) delete class 3 outright; (c) extract class 2 to `.devforge/command-refs/research/`: `re-entry.md` (0.6 + the attach arms of 4.1 / 4.2 / 4.3 / 4.4 / 4.6 / closing), `click-handler-trace.md` (2.4d), `literal-archaeology.md` (2.5b, trigger stays inline), `emission-matrix.md`, `probe-script.md`, `save-recovery.md` (exit 3); (d) collapse `:1234` to a one-line pointer (*"`verify` runs checks 1–20; each is stated at the step that satisfies it"*); (e) state the `--framing` and `--rests-on-literal` rules once each in Phase 2.6. Predicted: 207 → ~100 KB.
- **Cross-ref**: `scripts/emitters/claude.py` routes `references/` to `.devforge/command-refs/<name>/` for every promoted command — nothing to add beyond the directory. Every *"see Phase X"* / *"Step 2b's rules"* pointer inside an extracted block must be re-checked after extraction (not grepped here). `src/CLAUDE.md` catalog line for `/research` lists no references today — update it.
- **Reaction**: pending.

### 5. Docs reads are forced through CBM on the strength of an enforcement the hook does not provide — MEDIUM

- **Location**: `main.md:266` (*"Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`"*), `:401-406` (*"Read these via the CBM graph (md files are indexed …)"* for `docs/architecture.md`, `docs/<pkg>/architecture.md`, `docs/<pkg>/<concern>/index.md`, `docs/glossary.md`), `:412` (*"Raw `Read` / `Grep` / `Glob` … over source-file extensions are forbidden and will be blocked by runtime hooks"*). Hook: `src/hooks/cbm-code-discovery-gate:1-13` — matcher `Read|Grep|Glob`, blocks the FIRST call of a session for any path (not extension-aware), then every later call passes (`exit 0`); its message says *"Fall back to Grep/Glob/Read only for non-source text content"*.
- **Issue**: six markdown reads per run are routed through `get_architecture` + `search_graph label=File` + `get_code_snippet` — two to three CBM calls per file in place of one `Read` — on the stated ground that raw reads are blocked. They are not: the hook is a one-shot reminder, and its own text permits `Read` on docs. The diagnosis (`:301`) measured CBM returning 196 KB of research's 274 KB tool-result bytes at 4.3 KB per call; the docs reads are the one CBM use with no discovery rationale behind them.
- **Why it matters**: cost with no gate reason, and a false enforcement claim (`:412`) that a future session will repeat as fact.
- **Fix**: `:266` and `:401-406` say `Read` for the four docs paths (one call each) and keep CBM for symbol lookups; `:412` scoped to what the hook actually does (*"the first raw read of a session is blocked once as a reminder; the Phase 2.3 chain is the sanctioned path for SOURCE, not for `docs/`"*).
- **Cross-ref**: `src/settings.template.json:28` matcher; the same *"do NOT use raw Read"* sentence may exist in `/discover` and `/specify` (specify's audit finding 11 is the sibling) — grep `raw \`Read\`` across `src/commands` before the edit. Plan 127 (CBM vs files measurement) is the place the saving gets a number.
- **Reaction**: pending.

### 6. Phase 2.1's cost gate is a stop that quotes a number below the spec's own mandatory floor — MEDIUM

- **Location**: `main.md:393-397`.
- **Issue**: the gate asks the user to approve *"roughly <N> CBM calls"* with the rule of thumb *"one-package scope ≈ 15-30"*. The mandatory chain for a one-package bug with one fix-path helper, three callers and four siblings is ≈ 39 CBM calls before any judgment call: 2.3 (≥4) + 2.4 (2) + 2.4b (2) + 2.4c (`search_graph` 1 + inbound trace 1 + per-caller trace 3 + sibling `search_graph` 1 + sibling traces 4 + sibling `search_code` ≤4 + data-flow 1) + 2.4d (≥4) + 2.4e (3 probes + ≥3 traces) + 2.6 pre-verification (1 per finding, ≥6). The diagnosis measured 45 CBM calls on the benchmark run (`:301`). `cancel` discards Phases 0–1 (8–9 stops already paid) — no run cancels.
- **Why it matters**: one stop per run with no decision value, quoting a number the spec's own MANDATORY steps exceed.
- **Fix**: delete the question. Print the estimate as one line (derived from the mandatory floor by mode + layer, not the rule of thumb) and continue. Plan 124 L2 (a CBM call BUDGET with a named fallback) is a different mechanism and is unaffected.
- **Cross-ref**: *"Cost gate"* appears in `research/main.md:393` and `generate-docs/main.md:79` (a once-per-project index estimate — a different thing, leave it). `/discover` has no cost gate.
- **Reaction**: pending.

### 7. Three save-time preconditions are enforced only after the report is on disk — MEDIUM

- **Location**: `main.md:1030` (*"`finalize-handoff` in Phase 4 rejects with exit 2 … when any flag is unset"*), `:1224` (*"Skipping this call blocks the handoff … A clean `verify` is not evidence the declaration exists — the check that enforces it runs later, at Phase 4"*), `:909` + `:914` (escalation cite: *"`finalize-handoff` then fails at Phase 4 Step 4.6 — after the report is already written"*). Code: `src/devforge/lib/_research/_cmds_handoff.py:207` (`probe_feasibility incomplete`), `:214` (evidence-lanes declaration guard, plan 73 D7). The escalation-cite guard was NOT located in `_cmds_handoff.py` / `_handoff_build.py` by `grep -iE 'escalat|wrapper'` (one docstring hit) — it either lives under other wording or `:909` is stale; verify before relying on it (see finding 11g).
- **Issue**: `verify` (20 checks) passes, the user confirms the save, the directory and branch are created, `research-report.md` is written, and only then `finalize-handoff` exits 2. The spec's mitigation is prose asking the model to remember (`:1030` *"early placement avoids accidental omission"*, `:1224`).
- **Why it matters**: a failed save leaves a half-feature (directory + branch + report, no handoff) and a manual recovery; it costs a Phase 4 re-run and the user's trust at the exact moment the run should be done.
- **Fix** (code + text): fold the finalize-only guards into `verify` as checks 21–22 (23 if the escalation cite exists in code) so one `verify` before Step 4.1 covers the save; `finalize-handoff` keeps its guards as a backstop. `:1030` and `:1224` shrink to the check numbers.
- **Cross-ref**: `_cmds_render_verify.py` check table and its tests; `:1234` (the Verify paragraph) and the `/specify` consumer, which reads the handoff's `evidence_lanes` — unchanged shape. `/discover finalize-handoff` has the same declaration guard (plan 73 D7 mirror) — same fix applies there.
- **Reaction**: pending.

### 8. Per-row setters make Phases 2.4c / 2.4e / 2.6 the turn multiplier — MEDIUM (cost)

- **Location**: `main.md:530-646` (2.4c: `record-fix-path-helper`, `declare-caller-total`, `record-inbound-caller` × N, `classify-caller-scope` × N, `record-dead-sibling` × M, `record-consumer-chain` × K), `:787-796` (2.4e: `record-finding` per surface), `:956-1009` (2.6: `record-finding` per finding each preceded by a `search_code` pre-verification `:964`, `record-hypothesis` × ≥2, four scalar setters, `record-contributing-factor` × ≤3), `:1092-1222` (Phase 3: eight scalar setters each its own call). 74 helper call sites in the spec; 61 CLI verbs.
- **Issue**: a one-helper / three-caller / six-finding / two-hypothesis bug run makes ≈ 45 helper calls in Phases 2–3 alone, each its own turn, plus six `search_code` pre-verifications. The diagnosis measured 31–40 helper calls and 172–258 turns per run (`:83`).
- **Why it matters**: the diagnosis established that cost is turns × context and that helpers cost turns, not bytes. This is research's half of plan 124 lever 1 (L1, batch writes); `specify`'s half is `133` D7.
- **Fix** (code + text): four batch verbs taking JSON rows and reusing the existing per-row validators — `record-callers --helper-qn --total N --rows '[{caller_qn, file_line, surface, scope, justification}]'` (replaces `declare-caller-total` + N + N; check 9 and check 19 evaluate the batch atomically), `record-findings --rows '[{surface, file_line, relevance, framing, rests_on_literal}]'`, `record-hypotheses --rows '[{cause, falsifier, runtime_probe_needed}]'`, `apply-report --json '{summary, complexity, verdict, evidence_lanes, …}'` for Phase 3's scalar setters. The per-row verbs stay (the batch verbs are additive; the spec shows the batch form). The `search_code` pre-verification stays but is stated as *"in the same turn as the result row you copy from"* — the drift it guards against is between turns, so the batch call lands right after the searches. Predicted: 45 → 12–15 helper calls; turns 172–258 → 100–130 together with finding 3.
- **Cross-ref**: `_validators.py` per-row validators; sticky-reject and the anchor gate (`:537-539`) must evaluate per row inside the batch with the same stderr shape; tests mirror `tests/lib/test_research_helper*.py`. Plan 124 item 1 names this lever; it must not be built before plan 124's directive is rewritten (see sequencing).
- **Reaction**: pending.

### 9. v2 dropped two v1 behaviours without a replacement: external research and duplicate detection — LOW

- **Location**: v1 `research.md` PHASE 3 (signal-based Context7 / WebSearch when the idea names a library, service or pattern the project lacks — a five-row signal table) and rule 5 (*"scan `specs/` for existing features that overlap"*). v2 `main.md`: zero occurrences of `WebSearch` / `Context7` / *external research*; `:1399` (*"No topic matching is performed … produces a second, separate one"*) and the closing message (`:1511`) telling the user to delete a duplicate. `/discover` carries external research (4 hits) for greenfield; `/research` is brownfield-only and has none.
- **Issue**: an enhancement that introduces a new dependency gets an enhancement-mode verdict (`Feasible` / `Feasible with caveats` / `Not Recommended`, `:1200`) that rests on nothing about that dependency; and a second run on a topic that already has a feature directory silently creates a sibling.
- **Why it matters**: both are v1 quality the maintainer credited (*"v1 shows itself great on real projects"*); both are cheap.
- **Fix**: (a) enhancement mode only: a conditional *"External signal"* step after 2.4b, v1's signal table verbatim, result recorded via `set-constitution-constraints --rule "External dependency" --impact "<library — status — compatibility>"` (no new verb) — skipped when no signal; (b) at Step 4.1, list existing `specs/**/research-report.md` whose `topic_slug` shares a token with the proposed slug, as information under the save question (`artifact_helper find-feature-artifacts` already exists; no new stop).
- **Cross-ref**: `/discover` external-research prose is the pattern to copy, not to duplicate — cite it. The `specs/<YYYY>/<MM>/<leaf>` layout (plan 91) means a slug match is a token match, not a path match.
- **Reaction**: pending.

### 10. Two `none` sentinels with opposite spellings, one of which persists silently — LOW

- **Location**: `--file-line "(none)"` is the negative-result sentinel (`:473`, `:511`, `:953`; 13 `(none)` occurrences); `--surface "none"` is bare (`:582`: *"the bare word `none`, NOT the parenthesized `(none)` sentinel … a mistyped `(none)` would persist silently"*); `--rests-on-literal none` is bare (`:961`); `set-scope --evidence "(none)"` is rejected (`:302`); `record-fix-path-helper` and `record-value-production-site` reject `(none)` (`:535`, `:840`).
- **Issue**: the spec documents that one of its own sentinels, mistyped in the way the other sentinel invites, persists silently.
- **Why it matters**: a `(none)` surface row renders in the report and in the handoff as a surface literally named `(none)`; `/specify` reads it.
- **Fix** (code + one sentence): `classify-caller-scope` and `record-finding` reject `--surface "(none)"` with exit 2 and the hint *"use the bare word none"*; one sentence in the Conventions block states the two sentinels.
- **Cross-ref**: `_validators.py`; `/specify` and `/plan` consume `(none)` file-line rows from the handoff — the file-line sentinel does not change.
- **Reaction**: pending.

### 11. Stale or contradictory sentences (sentence-level hallucination check) — LOW bundle

- (a) `:1147` *"`verify` runs after every Phase 3 setter"* vs `:1228-1236` — one `verify` call after the setters, cap 3 iterations. Delete the clause.
- (b) `:703` *"CBM's `mode=data_flow` returns identical hop lists to `mode=calls` for first-party project code (pre-flight verified 2026-05-18)"* vs `:635` and `:764`, which use `mode=data_flow` as a distinct trace. One of the two is wrong for the reader; the dated claim is the one to delete.
- (c) `:412` *"will be blocked by runtime hooks"* — the hook blocks once per session, for any path, then passes everything (finding 5). Reword.
- (d) `:210` *"That is a v1 simplification"* — `v1` here is the grill-seed mechanism's first version, a maintainer term a consumer reads as the framework's v1. Delete.
- (e) `:1248` documents a false positive of the hypothesis-suppression gate (*"a generic word of 8 or more characters (`declared` is one) fires the gate as well"*) and offers no exit for it: `declare-grounded-overlap` needs a recorded row carrying the token (`:1263`), `record-gap` is for mechanisms, rewording is forbidden (`:1267`). Code `_cmds_render_verify.py:976` drops tokens under 4 chars and stopwords, counts tokens ≥ 8 chars. A generic shared word has no honest exit. Fix in code: count a token only when it looks like an identifier (contains `.`, `_`, a digit, or an inner capital) — then `:1248`'s admission can go.
- (f) `:1234` — 3,414 chars restating eight checks (finding 4, class 4).
- (g) `:909` / `:914` claim `finalize-handoff` requires the rationale to contain `default` / `wrapper` / `caller` / `escalat` on three intents. `grep -iE 'escalat|wrapper'` over `_cmds_handoff.py` and `_handoff_build.py` finds one docstring. Either the guard lives under other wording or the sentence is stale — unresolved here; whichever it is, a sentence that names a rejection the code may not perform is the class this check exists for.
- **Reaction**: pending.

### 12. CLI verbs no command calls — NIT

- **Location**: `_cli.py` registers `append-outcome`, `check-outcome`, `summary`; none appears in `src/commands/**/*.md` (`append-outcome` / `check-outcome` also exist in `_discover`; hits are in `_cli.py`, `_cmds_handoff.py`, `handoff_schema.py` and `tests/lib/test_discover_handoff_cli.py`).
- **Issue**: three verbs with no spec caller — maintainer / test-only, or dead.
- **Fix**: confirm callers (tests and `scripts/` only?) and either mark them maintainer verbs in the helper docstring or delete them with their tests. The reverse direction is clean: every verb `main.md` names exists in the CLI, including the five bare `set-<dimension>` names at `:289` (the bare-name false alarm from the specify audit was checked for here).
- **Reaction**: pending.

---

## Part 2 — Can `/research` be simplified without losing quality? What v1 did in 9.6 KB

### 2.1 Where the price is

Static (files at HEAD) and measured (cost diagnosis of 2026-09-27; v1 medians over 92 runs, v2 over 1–3 runs per command):

| | v1 `research.md` | v2 `research/main.md` |
|---|---|---|
| Prose at invocation | 9.6 KB / 232 lines ≈ 2.4 k tokens | 207 KB / 1,519 lines ≈ 52 k tokens |
| Helper verbs | 0 (no helper existed) | 61 in CLI, 58 named in spec, 74 call sites |
| Stops, static | 2 `AskUserQuestion` (topic when empty, save) | 13 `AskUserQuestion` + 6 free-text rubric prompts + 3 fallback prompts (2.4d) |
| Stops, measured median | 4 | 12 |
| Framework min / turns / helper calls | 14 / 98 / — | 30–68 / 172–258 / 31–40 |
| Tool calls per run | 52 (40 direct reads, 0 CBM) | 92 (32 helper, 45 CBM, 12 reads) |
| Tool-result bytes | 121 KB | 274 KB, of which CBM 196 KB |
| Cache-read | 4.8 M | 17.6–37 M |
| Output tokens | 46 k | 91–144 k |
| Artifacts | one `research/<date>-<slug>.md` on request | feature dir + branch + `research-report.md` + `research-handoff.json` + conditional probe script / emission matrix / `intake-rerun.json` + `[WIP]` commit |

**What v1 did**: load five context files → extract 3–7 keywords → Grep / Glob / Read up to 10 files → conditional external research on five signals → render a fixed report (codebase findings, constitution constraints, 2 approaches with a recommendation, complexity, next step) in the console → one save question → next steps. One stop, no state, no gates.

**What v2 adds, grouped by what it buys**:

- **A. Intake discipline** (0.4 suspected-cause, 0.5 echo-back, Phase 1 six-dimension rubric, conflicts, drift, mode detection). Buys a typed `SymptomMemo` that the handoff carries and a confirmed interpretation. Costs 8–9 of the 12 stops (finding 3) and ~20 helper calls.
- **B. Investigation forcing functions** (2.3 grounding rule, 2.3b framing challenge, 2.4 sweep, 2.4b canonical pattern, 2.4c caller enumeration + scope classification, 2.4d handler chain, 2.4e feature-surface sweep, 2.5 value semantics, 2.5b literal archaeology). Buys the structural evidence `/plan` and `/specify` consume — caller enumeration, the emission matrix and the inference rules were credited on 2026-10-05 as the mechanisms worth keeping. Costs ≈ 45 CBM calls and ≈ 30 helper calls (findings 6, 8).
- **C. Verification** (20 `verify` checks, the suppression gate, three finalize-time guards). Buys rejection of fabricated or incomplete reports. Costs the verify loops (≤ 3 + 3), the reset-only repairs (finding 1), the 8b trap (finding 2) and the post-save failures (finding 7).
- **D. Artifact plumbing** (allocation, branch, handoff, WIP commit, probe script, matrix). Buys the pipeline. Costs 6 calls and 24 KB of Phase 4 prose (finding 4).

### 2.2 Verdict

Yes — without touching the evidence B produces — in three layers, ordered by how much each moves the measured numbers:

| Layer | Findings | What it moves | Prediction | Kind of change |
|---|---|---|---|---|
| Stops | 3, 6 | 12 → 3–4 per run (echo-back, rubric table, save) | idle time to v1's level; `answering` 29 min → ~8 | policy (reverses a ratified forcing function) + text |
| Turns | 8, 1, 7 | helper calls 31–40 → 12–15; no full-run resets; no post-save failures | turns 172–258 → 100–130 | code + text (plan 124 L1 for research) |
| Bytes | 4, 11 | 207 → ~100 KB | cache-read per turn ≈ −10–12 % | text only (plan 124 L7) |

Together: framework minutes 30–68 → an estimated 15–25 against v1's 14. The estimate is static; the measurement plan (124 item 7, `_COMMAND_MARKER_RE`) is what turns it into a number.

### 2.3 Do not cut

- The Phase 2.3 `file:line` grounding rule and the one-line pre-verification (moved into the same turn, not removed).
- 2.3b framing challenge — one call, the cheapest anti-anchoring device in the file.
- 2.4c caller enumeration + Step 2b scope classification, and the emission matrix — credited mechanisms; make them batch calls (finding 8), not optional.
- 2.5b literal archaeology — keep the trigger inline and the procedure in a reference (finding 4); it answers two recorded incidents (plans 73, 75).
- ≥ 2 hypotheses with falsifiers; the handoff; Phase 4's invariant (nothing outside `.devforge/` before the save confirmation).
- The 0.5 echo-back — it is the ONE intake confirmation the rubric should merge into, not a stop to remove.

### 2.4 The floor, stated honestly

The CBM half of the run — ≈ 45 calls on a one-package bug — is untouched by all three layers; it is the mandatory chain's floor (finding 6's arithmetic) and plan 127 / lever L2's territory. v1 made 52 tool calls to v2's 92: v2 is v1 plus the forcing functions, and no prose diet or batch verb takes the floor below ≈ 40 calls without cutting a forcing function. That cut is a separate decision with its own evidence need, not part of this verdict.

### 2.5 Sequencing

1. Measure first (plan 124 item 7) so each layer has a before / after.
2. Text only: findings 4, 11, 5, 10's sentence — one author → reviewer pass, no helper change.
3. Policy: findings 3 and 6 in one decision (the same decision applies to `/discover`'s rubric).
4. Code + text: findings 1, 2, 7, 10 — the trap set; small verbs, high value.
5. Code + text: finding 8 — the batch verbs, after plan 124's directive (*"built AFTER 106–123"*) is rewritten on the maintainer's say-so.
6. Parity: findings 9, 12.

None of this executes without a numbered plan; this file is the evidence it cites.

---

## Part 3 — Open questions the maintainer asked to record (2026-10-07, NOT answered)

Both questions are larger than any finding above: they ask whether a forcing function should exist, not how to make it cheaper. Part 2.4 deliberately left that class of decision out of the verdict. They are recorded here so the plan that picks this file up has to answer them before it ratifies the "do not cut" list in 2.3. Each carries the evidence in hand and what is still missing; neither carries a recommendation.

### OQ-1 — Are all six rubric questions needed?

- **The question**: finding 3 batches the six dimensions into one confirmation but keeps all six. The maintainer's question is one level up: does each dimension need to be ASKED, or can some be inferred (with `--state Partial` and the `Model inference — the user delegated:` attribution the spec already defines at `:291`) and only confirmed in the batched table?
- **Evidence in hand**: v1 asked none of them and the maintainer credits v1's results. Spec-side consumers per dimension (grep of `memo.dimensions.<d>` + backticked name in `main.md`): `affected_area` 13 sites (docs scan `:261-271`, 2.2 docs paths `:404-405`, 2.4e probe 3 `:769`, `record-gap --dimension affected_area` `:1168`), `desired` 9 (2.4c Step 4 symbol extraction `:630`, 2.5 value semantics, 2.4e), `symptom` 6, `scope` 6 (narrow-framing gate `:293-307`, 2.4c depth), `unchanged_behavior` 5 (the `set-recommended-approach` cross-check `:1113`, check at verify), `repro_or_current` 3 (2.4d handler identification `:679`, bug mode only). `handoff_schema.py:387-389` carries `symptom_summary`, `desired_summary`, `scope` as typed fields; the other three were not found as typed handoff fields in this pass (grep of `class` / typed attributes only — verify before relying on it). So three dimensions leave the command; three are consumed inside it.
- **What the answer turns on**: for each dimension, does its consumer FAIL on a model-inferred value, or merely degrade? `scope = "one place"` is the only value with a hard gate (`--evidence` required); `unchanged_behavior` feeds a cross-check that is vacuous on an empty value; `repro_or_current` is read only in bug mode by 2.4d, which has its own user fallback prompt (`:687`). A dimension whose consumer tolerates `Partial` is a candidate to infer-and-confirm rather than ask.
- **What is missing**: a count, from real runs, of how often the user's answer to each dimension differed from what the prompt already said — the diagnosis measured stops, not information gained per stop. The profiler fix (plan 124 item 7) plus the research-state.json of past runs on the 2.0.12 install can supply it without a new mechanism.
- **Where it gets decided**: the same plan that takes finding 3; the decision applies to `/discover`'s rubric in the same stroke.

### OQ-2 — Is CBM needed at all?

- **The question**: v2 routes every source read through `codebase-memory-mcp` (the Phase 2.3 chain) and forbids raw `Read` / `Grep` for source. v1 used Grep / Glob / Read only. Is the graph buying evidence that grep cannot produce, at a price worth paying — or is it the single largest cost item with a maintenance tail?
- **Evidence in hand — cost**: on the benchmark research run CBM was 45 of 92 tool calls and 196 KB of 274 KB tool-result bytes at 4.3 KB per call (diagnosis `:301`); v1's run made 40 direct reads for 121 KB (`:302`). CBM mentions by command (`main.md` + references): `research` 54, `generate-docs` 14, `discover` 13, `pr-review` 12, `specify` 11, `plan` 3, `grill` 3, `audit` 3, `implement` 1, `constitute` 1 — ten of 21 commands, research alone half the surface. 15 helper `.py` files reference it. Four hooks are wired in `src/settings.template.json` (`cbm-code-discovery-gate`, `cbm-mcp-marker`, `cbm-session-reminder`, `cbm-sync-session-start`) plus `install.sh` wiring. Four of the twelve open stubs are CBM maintenance (112 manifest-less infra packages, 113 index skip-list drops source dirs, 114 glossary CBM project arg, 115 wrapper inner-repo CBM visibility).
- **Evidence in hand — value**: the graph is what makes three mechanisms cheap to state: inbound caller enumeration (`trace_path … direction=inbound`, 2.4c Step 2), the 8-hop upward surface trace (Step 2b, 2.4e), and the outbound data-flow trace (Step 4). The spec itself already distrusts the graph in each: `trace_path` keys on the bare name and can return another symbol's callers (`:549` — discard the whole set and re-derive via `search_code`); a sibling with an empty inbound set must be cross-checked by `search_code` (`:613-619`); Vue / SFC handlers may not be graph nodes at all (`:705`); `get_code_snippet` line numbers are not file line numbers (`:421`); `mode=data_flow` is asserted identical to `mode=calls` (`:703`). Every one of those cross-checks is a text search — the thing v1 did.
- **Maintainer's observation (2026-10-07, same day, English paraphrase)**: *"search works fine in v1"* — v1's Grep / Glob / Read discovery is adequate on the real projects it has run on. Weight: v1's search is the one side with field evidence — 92 runs across three client installs plus the benchmark (diagnosis `:27`) — while CBM's contribution to OUTCOME is the thing the diagnosis marked unproven (F8). **This flips the burden of proof**: the default is no longer "CBM stays unless shown useless" but "text search is the default unless 127 shows the graph adds evidence v1's search missed on the same bug". What the observation does NOT settle: v1 produced feasibility reports, never a declared caller total, an emission matrix or an upward surface trace — the three things v2's downstream consumes — so "fine" is measured against v1's deliverable, not v2's. That gap is exactly what the 127 run below has to close in one direction or the other.
- **Maintainer's second observation (2026-10-07, English paraphrase)**: *"just forcing everyone to install this thing is a poor decision."* This is the adoption axis, and it is independent of the token arithmetic above. What v2 forces today: `install.sh:440` copies `src/mcp.json` into every consumer's `.mcp.json` (project-scope MCP server); `src/settings.template.json` wires four CBM hooks into every session (`cbm-code-discovery-gate` on `Read|Grep|Glob`, `cbm-mcp-marker`, `cbm-session-reminder`, `cbm-sync-session-start`, which prompts a re-index on every session boot when HEAD moved — `install.sh:485`); `/generate-docs` Phase B *"assumes CBM is indexed"* and its preflight calls `index_repository` (`generate-docs/main.md:43`, `:575`); `/research` Phase 0.2 refreshes the index stamp and Phase 2.3 forbids raw reads. So the server is a hard dependency of the setup chain, not an accelerator: a consumer without it cannot complete `/generate-docs`, and every session pays the hook and the re-index prompt. For an enterprise evaluator this is the first install step and a third-party component that indexes the whole codebase — a vetting item (what it runs, where the index lives, what it sends) before the framework's own value is ever seen. The 2026-10-03 enterprise research lists no gap this dependency closes.
- **The zero-maintenance shape, for the record**: the framework stops knowing CBM exists — no `.mcp.json` shipped, no hooks, no preflight, no `index_repository`, specs written for `Grep -n` / `Read` as v1 was. A consumer who has any code-graph MCP server keeps using it as Claude uses any tool; the specs neither require nor mention it. This is cheaper than "CBM optional": an optional path documented in the specs is a second path to maintain (the dual-path prose cost), while an undocumented tool costs nothing. The price of the zero shape is a re-spec of the three graph-shaped mechanisms (2.4c callers via `grep -n "<name>("`, 2b upward trace via read-the-caller, 2.4e via text probes — the cross-checks the spec already mandates), and a replacement for `/generate-docs`' architecture extraction, which is the one place the graph does structural work no grep does cheaply.
- **What the answer turns on**: whether the caller total that check 9 pins (`declare-caller-total` vs recorded rows) comes out the same from `grep -n "<name>("` over first-party code as from `trace_path`, on the same bug, and at what turn and byte cost. If it does, the graph's distinctive contribution is the multi-hop upward trace — and that is a judgment the spec already labels "yours to cite and nothing checks it" (`:603`, `:798`).
- **What is missing**: exactly plan 127's measurement (CBM vs files token measurement, Phase 0 OPEN, nothing measured) — run on one bug both ways, comparing turns, result bytes, the check-9 caller count, and whether the recommendation differs. Without it this question is a belief in both directions.
- **Blast radius if the answer is "no"**: ten command specs, 15 helper files, four hooks, `install.sh`, `generate-docs`' index preflight, plans 112–115 (closed as moot), 127 (becomes the decision record), and the `_PROMOTED` surface of `.devforge/command-refs/`. A "partial no" — CBM optional, text search the default, graph used only where a trace is explicitly requested — has a smaller radius and is the shape v1 → v2 skipped.
- **Where it gets decided**: plan 127 Phase 0, re-scoped from "measure CBM vs files" to "decide whether CBM stays", with the measurement as its Phase 1.

---

## Part 4 — Conformance pass (2026-10-07, second pass, same day): live tool schemas + Anthropic guidance

**What this pass asked**: three questions the maintainer put the same day, in their words (English paraphrase): *how understandable is the command to the model that executes it, does it raise the clarity and efficiency of that model's work, and does it conform to Anthropic's standards and guides?* Part 1 is not repeated; everything below is additional to it. Reaction lines stay `pending` — saved, not presented one at a time, by the maintainer's instruction. Nothing in `src/` was modified.

**Inputs read for this pass**: `src/commands/research/main.md` — the same bytes Part 1 anchored (1,519 lines, 207,212 bytes; `git status` shows it unmodified); the LIVE tool schemas of `mcp__codebase-memory-mcp__search_code`, `search_graph`, `trace_path`, `get_code_snippet` as loaded in this session on 2026-10-07 from the CBM server on the maintainer's machine (consumer installs may run another version — plan 124 item 2 records two CBM versions in the field); the `AskUserQuestion` tool schema as loaded in this session (`options`: 2–4 items; the tool appends its own `Other` row); `src/hooks/cbm-code-discovery-gate`; `scripts/emitters/claude.py:76-83` + `scripts/lib/command_source.py:66-96`; and six documentation pages fetched by the `claude-code-guide` agent with verbatim quotes, cited inline below by URL + section.

**Executor's read (the first two questions, in brief)**. Sentence by sentence the file is clear: precise wording, a stated reason behind most rules, one consistent voice. Document-wide it is hard to execute: six phases, ~25 steps and seven conditional arms (ticket-file, grill re-entry / attach, 2.4d, 2.5b, emission matrix, exit 3, don't-save) that the executor must assemble into a state machine from prose; `verify` checks cited 69 times by number with no table defining them (finding 16); the same rule stated three to five times at different sites, which is where Part 1's contradictions (finding 11) live. Clarity of the OUTPUT goes up — the forcing functions (2.3b, 2.4c, 2.4e, the emission matrix, ≥ 2 hypotheses) are what the maintainer credited on 2026-10-05. Efficiency of the WORK goes down, by the measured numbers Part 2.1 already carries (52 k tokens of prose on every one of 172–258 turns; 12 stops median against v1's 4); those numbers were not re-measured here.

### 13. The CBM tool contract pinned in the prose is false against the live schemas — HIGH

- **Location**: `main.md:465` (*"The supported `search_code` argument is `pattern` only"*, and in the same line *"include the file's base name as an OR-token in the regex"*), `:682` (the handler-token sweep `search_code(pattern="@click=|onClick=|addEventListener|…")`), `:473` (0 hits on the runner-up falsifier → a negative finding *"runner-up falsifier not found project-wide"*), `:419` (*"0 hits at `search_code` means 'truly absent'"*), `:269` / `:401` / `:414` (*"The argument name is `name_pattern`, NOT `file_pattern`; the wrong name returns silent 0 hits"* and its two restatements), `:549` (*"Run the trace at depth 1"* — the argument is never named). Live schemas, 2026-10-07: `search_code` takes `pattern` + `project` (both required), `file_pattern`, `path_filter`, `regex` (default `false`), `mode` (`compact` / `full` / `files`, default `compact`), `limit` (default 10), `max_output_tokens`; `search_graph` takes `file_pattern` alongside `name_pattern` / `qn_pattern` / `label` / `query`, `project` required, `max_output_tokens` default 3,200; `trace_path` takes `function_name` + `project` (required), `depth` (default 3, max 15), `direction` (default `both`), `mode` (default `calls`), `include_tests` (default `false`), `max_output_tokens` default 3,200; `get_code_snippet` takes `qualified_name` + `project` (required), `start_line`, `source_mode` (`auto` / `full` / `outline`), `max_lines`.
- **Issue**: four claims the executor is told to rely on are wrong against the tool it is calling. (a) `pattern` is not the only argument. (b) The spec assumes regex semantics throughout — the alternation at `:682` and the "OR-token in the regex" at `:465` — while the live default is a literal match: under `regex: false` the `:682` string matches nothing, the *"heuristic-fragility fallback"* fires and the user is asked a question the tool would have answered; at `:473` a 0-hit that is a mode artifact is recorded as a negative finding, and `:419` tells the executor to read it as "truly absent". (c) `file_pattern` exists on `search_graph`, so the stated rationale for the `name_pattern` aside is stale (whether `file_pattern` filters `file_path` for `label="File"` rows was not tested here — the claim that the name does not exist is what is false). (d) `:465` instructs the executor to pull *"dozens of hits across the package"* and filter them in the orchestrator, while `file_pattern` / `path_filter` would scope the search server-side — these are the bytes plan 124 L2 measured (26 `search_code` calls, 129 KB per run on the benchmark install). And `trace_path` defaults to depth 3: an executor that does not pass `depth: 1` by name declares the check-9 caller total over depth-3 rows. None of the four tools is ever told `project`, which every one of them requires.
- **Why it matters**: category (b) of the sentence-level hallucination check fails today, and the failure is silent — a 0-hit reads as evidence. The more general point is the shape of the mistake: a tool contract pinned in prose drifts with every server release, in both directions (a consumer on an older CBM may find the regex claim true and the `file_pattern` claim false). This is the class of sentence the maintainer's discipline rule names as the most dangerous: it looks like ground truth and was true once.
- **Fix**: state the contract once — a `## CBM tool contract` block, or `references/cbm-tool-contract.md` loaded from the Phase 2.3 chain, carrying the four tools' argument shapes with the date and server version they were verified against; every call shape in the spec then names `project`, passes `regex: true` wherever alternation is used (`:465`, `:682`, and any `|` pattern), uses `file_pattern` / `path_filter` for in-file scoping instead of client-side filtering (`:465`), and passes `depth: 1` by name at `:549`; delete the `pattern`-only sentence and the three `NOT file_pattern` asides. Add one line to the contract block telling the executor to trust the live tool schema over the block when they disagree, and to say so in `--relevance`.
- **Cross-ref**: *"argument is `pattern` only"* — one hit in `src/`, `research/main.md:465`. *"NOT `file_pattern`"* — three hits, all in `research/main.md`. `discover/main.md` carries 13 CBM mentions and was NOT grepped for the same claims — grep before editing. Plan 124 item 2 already schedules retiring the `pattern`-only sentence under lever L2 together with `mode=compact` / `limit` / `max_output_tokens`; this finding is the text half of that lever and must not pre-empt the budget decision (OQ-2 and plan 127 decide whether CBM stays at all — if it goes, this finding goes with it). `src/hooks/cbm-code-discovery-gate` is unaffected.
- **Reaction**: pending.

### 14. `AskUserQuestion` is prescribed for a free-text-only question, against the tool's own contract and the file's own rule — MEDIUM

- **Location**: `main.md:101` (*"ask the user via AskUserQuestion: `"What's the topic? (bug or enhancement, one sentence)"` — single-line question text, free-text answer"*) versus `:279` (*"Do NOT use AskUserQuestion for these (the answer is open-ended free text)"*). Tool schema as loaded: `options` requires 2–4 entries per question; the tool appends its own `Other` row. Docs: *"Claude uses `AskUserQuestion` to ask you multiple-choice questions when it needs a decision or a clarification. Answer by picking an option, or type your own text through the `Other` row or the notes field."* — https://code.claude.com/docs/en/tools-reference, section "AskUserQuestion tool behavior" (the 2–4 bound is in the schema, not the docs). Twin: `discover/main.md:76`, the same sentence.
- **Issue**: no valid call satisfies `:101` — a free-text-only question has no option set. The executor either invents two options to carry the `Other` row, or falls back to prose; `:279` says prose is the rule for open-ended answers, so the file contradicts itself about the one question it asks before any state exists.
- **Why it matters**: a contradiction at the first user-facing step of the empty-argument path; and an invented option set at that point ("bug" / "enhancement"?) would pre-empt `detect-mode`, which Phase 1 owns.
- **Fix**: `:101` becomes the plain-prose prompt + end-the-turn shape `:279` already prescribes; same edit at `discover/main.md:76`. No helper change.
- **Cross-ref**: the other 12 `AskUserQuestion` sites in `research/main.md` carry option sets (`:156` confirm / correct, `:278` scope, `:315` two values, `:332` / `:377` bug / enhancement, `:397` proceed / cancel, `:1346` / `:1348` save / ticket) — unchanged. `configure/references/q11-tiers.md:92` states the `Other`-row rule correctly and is the house reference for it.
- **Reaction**: pending.

### 15. Emphasis is saturated, and the two anti-rationalization paragraphs forbid thoughts instead of giving the reason — MEDIUM

- **Location**: whole file; counts 2026-10-07: `MANDATORY` 27, `MUST` 25, `VERBATIM` 33, *"do not summarize or paraphrase"* 26, *never* 90, `Do NOT` / `do NOT` 18, `ONLY` 14, `REQUIRED` 7, *"Honesty bound"* 4. `:218-220` — the two `**MANDATORY: never skip the rubric**` / `**MANDATORY: never fabricate a user mode**` paragraphs, the second of which is a list of forbidden phrases (*"user requested no-questions mode"*, *"the ticket file covers all six dimensions"*, …) ending *"If you find yourself about to justify a shortcut by attributing intent to the user, STOP — you are rationalizing a fabrication."*
- **Anthropic guidance, verbatim**: *"Claude Opus 4.5 and Claude Opus 4.6 are also more responsive to the system prompt than previous models. If your prompts were designed to reduce undertriggering on tools or skills, these models may now overtrigger. The fix is to dial back any aggressive language. Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'."* and *"Tell Claude what to do instead of what not to do."* — https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices, sections "Tool usage" and "Control the format of responses". The counterpoint, from the Claude Code best-practices page: *"If Claude keeps skipping one instruction, add emphasis such as 'IMPORTANT' to that line alone. If you emphasize many lines, none of them stands out."* — https://code.claude.com/docs/en/best-practices, section "Write an effective CLAUDE.md". Both sides say the same thing about this file: emphasis works on ONE line, and this file has it on about a hundred.
- **Issue**: the marker no longer separates a step a `verify` check enforces (where skipping is caught) from a pure-judgment step (where only the prose stands); the executor cannot rank them. `:220` is the clearest symptom: it records that the model keeps trying to skip the rubric and answers with a phrase blacklist rather than the user-facing reason per-dimension commitment is worth six stops — which is also the policy question Part 1 finding 3 and OQ-1 leave open. The four *"Honesty bound"* paragraphs are the counter-example inside the same file: plain voice, the limit of the check stated, the executor's judgment named — they are the register the rest should use.
- **Why it matters**: for a Claude 4-family executor the documented effect of the saturated register is overtriggering — echoing, asking and refusing shortcuts where none was attempted — on top of the salience loss the CLAUDE.md guidance names. The cost side is Part 1 finding 4's class 1 (the repeated protocol boilerplate).
- **Fix** (text only): (a) reserve `MANDATORY` for a step a `verify` check enforces and name the check inline (*"MANDATORY — check 12a"*); everywhere else plain imperative; (b) rewrite `:218-220` as one paragraph giving the reason (what the user loses when a dimension is inferred rather than committed), no phrase list — or, if finding 3's batched rubric is adopted, replace both paragraphs with the batched-table rule; (c) the 26 verbatim-copy sentences go to the Conventions block finding 4(a) proposes (not duplicated here); (d) keep the four *"Honesty bound"* paragraphs as written. Phrase every remaining prohibition as the action to take (*"read the four docs paths with `Read`"* rather than *"do NOT use raw `Read`"* — finding 5 already moves that sentence).
- **Cross-ref**: `discover/main.md:375` is the twin of `:387`; the same register runs through `specify` (Part 1 of the 2026-10-05 audit). This is a style decision to take once across the 21 commands — the per-mechanism umbrella plan proposed 2026-10-07 is the place — not per file. Finding 4(a) owns the Conventions block; this finding adds nothing to it.
- **Reaction**: pending.

### 16. Checks are cited 69 times by number and defined nowhere as one list; the file has no map — MEDIUM

- **Location**: whole file. `grep -oiE '\bcheck(s)? [0-9]+[ab]?'` → 69 references: check 20 × 14, 8b × 11, 17 × 10, 19 × 5, 8 / 12b / 13 × 4, 9 / 12a / 16 × 3, 14 / 15 / 18 × 2, 10 / 11 × 1. The only consolidated statement is the Verify paragraph `:1234` (3,414 chars, Part 1 finding 4 class 4), which names checks 8, 8b, 12a, 12b, 13, 14, 17, 18 and describes seven others without a number; checks 9, 10, 11, 15, 16, 19, 20 do not appear in it. There is no table of contents and no phase / step map; the first structural overview the executor gets is the heading tree itself.
- **Issue**: every numbered reference is a lookup into prose at two or three sites; "which step satisfies check 19 and which verb repairs it" takes reading `:605`, `:655` and `:1234` and reconciling them. The number is used as a shared vocabulary without a dictionary.
- **Why it matters**: this is the mechanism behind the executor's document-level difficulty named at the top of this Part, and behind Part 1 finding 11 — rules restated at several sites are rules that can drift apart at those sites.
- **Fix** (text, plus one maintainer test): a `## Verify checks` table — columns `check` / `rejects` / `satisfied at (step)` / `repair verb` — once, near the top or in a reference file; every inline mention shrinks to *"(check 19)"*; a 15-line phase / step map after `## Outputs of this phase` naming the seven conditional arms and their triggers; `:1234` collapses to the one-line pointer finding 4(d) proposes. This AMENDS finding 4(d): the collapse needs a target for the 69 number references to land on, so the table comes with it. The table is a hand-maintained restatement of `_cmds_render_verify.py` and therefore a hallucination-risk surface of its own: pair it with a test under `tests/lib/` that asserts the table's check numbers equal the set the code registers, so a check added or removed in code fails the gate.
- **Cross-ref**: `src/devforge/lib/_research/_cmds_render_verify.py` is the source of truth for the check list — read it before writing the table (not read in this pass). `/discover` and `/specify` carry their own numbered check sets and the same shape applies. Anthropic's long-context guidance (*"Ground responses in quotes… ask Claude to quote relevant parts of the documents first"*, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips) is the nearest published principle: a numbered, quotable table is what lets an executor cite a check instead of reconstructing it.
- **Reaction**: pending.

### Amendment to finding 4 — the published size standard

- Anthropic, verbatim: *"Keep SKILL.md body under 500 lines for optimal performance. Split content into separate files when approaching this limit."* and *"SKILL.md serves as an overview that points Claude to detailed materials as needed, like a table of contents in an onboarding guide."* — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices, sections "Token budgets" and "Progressive disclosure patterns". The slash-commands page files `.claude/commands/*.md` under "Legacy Commands (Deprecated)" and states *"Both use the same frontmatter except `name` and `paths` fields aren't supported in command files"* (https://code.claude.com/docs/en/slash-commands), so the skill guidance is the governing standard for command files too.
- `research/main.md` is 1,519 lines — 3.0 × the stated limit, with zero `references/`, while the framework already implements the split (11 commands ship references into `.devforge/command-refs/<name>/`). Finding 4's fix (c) is therefore not a local optimisation but conformance to a published limit; its target of ~100 KB is still ~750 lines, above the limit — the plan that takes it should state which number it is aiming at.
- **Loading mechanics (verified 2026-10-09, maintainer's question "does a split still count as one big command?")**. Docs, verbatim: *"When invoked, the rendered skill content enters the conversation as a single message"* (https://code.claude.com/docs/en/skills, "Skill Content Lifecycle"); *"Claude reads SKILL.md only when the Skill becomes relevant, and reads additional files only as needed."* and *"…Claude reads SKILL.md, sees the reference to `reference/finance.md`, and calls bash to read just that file. The sales.md and product.md files remain on the filesystem, consuming zero context tokens until needed."* (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices, "Progressive disclosure patterns"). So a reference file costs nothing until the executor reads it, and from that read on it costs the same as inline text for the rest of the session (cache-read on every turn) — the split is a CONDITIONAL-LOAD mechanism, not compression. Rule for Step 1 of Part 0: content every run uses (Conventions, the checks table, the CBM contract, the main path) stays inline; only arms most runs never take move to references, each cited as *"read X when Y"* at its trigger, never listed as "read all of these first". The framework's emitter already fits this: `scripts/lib/command_source.py` rewrites `references/X.md` to the plain path `.devforge/command-refs/<name>/X.md` (zero `@`-includes across the 21 sources, grep 2026-10-09), and the references live outside the `.claude/commands/` scan (plan 63). Two things the docs do NOT state, per the same pass: the `@file` include syntax (only `` !`command` `` injection is documented) and whether an arbitrary `.md` inside `.claude/commands/<dir>/` is scanned as a command — the second rests on the framework's own plan-63 observation, not on a quote (the agent's "quote" for it contained the word `devforge`, i.e. it echoed the question's example; treated as unverified).
- **Reaction**: pending.

### Amendment to finding 5 — the ticket-file `Read` meets the discovery gate

- `main.md:83` (*"Read the file with the Read tool"*) runs on a fresh session before any other `Read`; `src/hooks/cbm-code-discovery-gate` (matcher `Read|Grep|Glob`) blocks the FIRST matched call of a session with exit 2 — docs: *"Exit 2: Blocking error: prevents the action"* (https://code.claude.com/docs/en/hooks, section "Exit Codes") — and its message ends *"If you still need this tool, retry — this gate fires once per session."* The spec does not mention it, so a ticket-file run's first step is a blocked call with no instruction for the executor. Fold into finding 5's rewrite of `:412`: one sentence at `:83` — *"the first `Read` of a session is blocked once by the discovery gate; retry the same call"* — or read the file through Bash `cat` (a `.md` path is outside `bash-ban-raw-tools`' source-extension list).
- **Reaction**: pending.

### 17. `name:` is a frontmatter field Claude Code does not support in command files — NIT, cross-command

- **Location**: `src/commands/*/main.md:2` — all 21 commands carry `name: <command>`. Docs, verbatim: *"Both use the same frontmatter except `name` and `paths` fields aren't supported in command files."* (https://code.claude.com/docs/en/slash-commands, section "Legacy Commands (Deprecated)"). The emitter passes the frontmatter through unchanged (`scripts/emitters/claude.py:82` writes `body` as processed) and derives the command name from the source directory, never from the field (`scripts/lib/command_source.py:88`, `:96` — `name=cmd_name`).
- **Issue**: a documented-unsupported field ships in every emitted command. Harmless today (ignored by the runtime), but it is the seed of a future-session belief that `name:` is what names the command.
- **Fix**: drop `name:` from all 21 `main.md` frontmatters in one sweep, or keep it as a framework-internal field and say so in one sentence where the emitter's layout is documented (`CLAUDE.md` → "Generators / emitters" row). Not research-specific; belongs to the umbrella plan.
- **Cross-ref**: `scripts/generate-agents.py:244` reads `meta.get("name")` for AGENT files (`name` IS a supported field for sub-agent files) — unaffected and must not be swept with the commands.
- **Reaction**: pending.

### What this pass did not do

- `discover/main.md` was not grepped for the finding-13 claims or the finding-15 register beyond the two twins cited.
- `_cmds_render_verify.py` was not read; finding 16's statement of which checks `:1234` omits is by number as the prose cites them, not against the code.
- Whether `search_graph`'s `file_pattern` filters `label="File"` rows by `file_path` was not tested; only its existence was verified.
- No measurement; every number above is a static count or a quotation of Part 2.1 / the cost diagnosis.
