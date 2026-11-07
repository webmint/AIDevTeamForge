# RESEARCH — 2026-10-07 — `/devforge:discover` optimization: findings, cost shape, verdict

**Status**: evidence file, third of the 2026-10-07 set (`RESEARCH-2026-10-07-RESEARCH-AUDIT.md`, `RESEARCH-2026-10-07-DISCOVER-VS-V1-RESEARCH.md`). No plan owns it yet. Same protocol as the research audit; findings saved, not presented one at a time; Reaction lines `pending`. Nothing in `src/` was modified. **Every runtime number here is predicted from the spec — no `/discover` run has ever been profiled** (the cost diagnosis of 2026-09-27 carries one static row for discover, `:98`). Part 3 carries the open questions shared with the research audit plus one discover-specific one.

**Inputs read in full**: `src/commands/discover/main.md` at HEAD `44d9e1c` (826 lines, 88,345 bytes, zero `references/`); v1 `research.md` (its predecessor by job — see the comparison file); `src/devforge/lib/_discover/_cli.py` (41 verbs, `COMPLEXITY_ENUM` / `EFFORT_ENUM` at `:31-34`), `_cmds_fit.py` (`:14-33`, `:63`), `_cmds_core.py` (`cmd_verify` at `:565`, invariants A–G), `_cmds_handoff.py` (`:208-210`), `handoff_schema.py` (`:671-678`, `:745`); `src/devforge/lib/_specify/_cmds_handoff.py` (the discover import, `:469-569`); `src/hooks/cbm-code-discovery-gate`. Line numbers are HEAD anchors; locate by heading when they drift.

---

## Part 1 — Findings (12: 2 high, 4 medium, 5 low, 1 nit)

### 1. Phase 1 mandates ten separate human turns that Phase 0.5 calls the failure mode — HIGH (cost)

- **Location**: `main.md:116` (*"A clean prompt … passes with ONE echo-back confirmation and ZERO interrogation. Over-interrogating a trivial feature idea is itself the over-build failure mode this gate exists to fight."*) versus `:207` (*"ask each dimension question separately and wait for the user's answer in its own turn … never a license to auto-fill the remaining 7 in one pass"*), `:209` (anti-rationalization paragraph), `:228` (references prompt), `:246` (design-reference prompt), `:286` (one question per dimension), `:339` (coverage question, *"End the turn"*), `:375` (stop discipline).
- **Issue**: a clean run with `$ARGUMENTS` stops 13 times before anything is written: echo-back 1, references 1, design reference 1, eight dimensions 8, coverage 1, save 1. Twelve of the thirteen are intake. The eight dimensions all leave the command as `DimensionRecord`s (`handoff_schema.py:671-678`); whether `/specify` reads them is Part 3's OQ-3.
- **Why it matters**: v1 asked nothing and produced the report the maintainer credits; the research audit measured 12 stops on `/research` (6 dimensions) and put them at the top of the wall-clock bill; discover has two more dimensions and two more supplementary prompts, so its intake is the most expensive in the pipeline. The maintainer runs `Strict`, so no enforcement knob buys it back. **This reverses a ratified forcing function** (*"User commitment is per-dimension"*, `:207`) — the maintainer's call; this records the price.
- **Fix** (text only, helper unchanged): one batched scoping table — pre-fill the eight dimensions plus `references` and `design reference` as ten rows from the verbatim prompt and the 0.5 classification, propose a `state` per row, ask ONE question (*"Confirm all, or name the row(s) to correct?"*), loop only on named rows with `--increment-turn`, then `check-conflicts` once over the table. Per-dimension commitment survives (every value is shown and confirmed; a corrected row gets its own turn). `scope-coverage` becomes the echo of the confirmed table, not a separate decision. Predicted: 12 intake stops → 2.
- **Cross-ref**: the eight `set-scope-*` setters, `check-conflicts`, `record-conflict-resolution`, `scope-coverage`, `scope-finalize`, `record-references`, `set-scope-design-anchor` unchanged (`_cmds_scope.py`). `:207-209` rewritten, not deleted. The same decision applies to `/research` Phase 1 (research audit finding 3) — take it once.
- **Reaction**: pending.

### 2. A recorded row cannot be retracted, invariant G locks a false-positive internal hit into the rationale, and the only repair is the reset the spec itself calls destructive — HIGH

- **Location**: `main.md:385-390` (verb extraction examples: `audit`, `revision`, `history`, `snapshot`, `log`; `queue`, `job`, `worker`, `retry`), `:397` (*"plausibly implements"*), `:399-414` (`record-prior-art --source internal:<path>` + `record-integration-touchpoint` per hit), `:430` and `:656` (invariant G: *"`recommended_option.rationale` MUST contain at least one of those `internal:` paths as a substring"*), `:510` and `:658` (4th-failure exits: *"re-run `/devforge:discover` from scratch — prior partial state will be overwritten"*), `:731` (*"Sending the user back to re-invoke … would be destructive: Phase 0.3 resets the memo and report unconditionally … thrown away over a name the user can fix in one turn"*). Code: `_cmds_fit.py:14-33` — `record-prior-art` appends, no dedupe; `_cli.py` registers no `remove-` / `retract-` verb (grep: 0); `_cmds_core.py` G check.
- **Issue**: the extraction examples hand the model generic tokens (`log`, `job`, `history`) that match loggers, cron jobs and git helpers project-wide. One `log` hit recorded as `internal:` is permanent: no verb removes it, and G then demands the rationale carry that logger's path. `:430`'s wording offers an escape — *"or explicitly state which capability the existing implementation does NOT cover"* — but the check tests the substring, not the explanation, so the escape still requires the path in the rationale. The model's exits are: write the logger path into the rationale, or the full reset that `:731` argues against.
- **Why it matters**: the same shape as research audit findings 1 and 2 — a correct-looking call with no undo, and a gate whose only recovery is a fabricated-looking citation or a reset. Discover already contains the argument against the reset at `:731` and does not apply it to its own 4th-failure exits.
- **Fix** (code + text): `remove-prior-art --reference` (drops the row and its `internal:` touchpoint when one was recorded) and `remove-integration-touchpoint --name` (drops its fit assessment); `:510` and `:658` name the targeted removal before the restart; `:385-390` add the rule *"drop a token that names a generic facility (`log`, `job`, `user`, `event`) unless it is the feature's own noun"*; `:430` reworded to what G tests.
- **Cross-ref**: G is stated at `:407`, `:430`, `:656` — three sites change together. `verify` invariants in `_cmds_core.py:565+`; `tests/lib/test_discover_*`. Research audit finding 1's verbs are the sibling pattern; one design for both commands.
- **Reaction**: pending.

### 3. The command is overloaded: 88 KB, zero references, builder notes shipped to consumers — MEDIUM

- **Location**: whole file. Measured blocks: Phase 4 `:674-826` 19.8 KB (attach mode, exit-3 recovery, ticket arms threaded through six steps); Phase 1 `:203-375` 14.1 KB; Phase 3 `:512-672` 12.4 KB; 0.4 + 0.5 `:92-167` 12.0 KB; 0.6 re-entry `:169-201` 6.5 KB; memory-excerpt semantics `:45-54` 3.4 KB — duplicated verbatim from `research/main.md:52-61`. Boilerplate: *"copy … VERBATIM"* × 14, *"end the turn"* × 21, *"hands the choice back"* × 7, `MANDATORY` × 6. Builder notes: *"Discover lane divergence (do NOT mirror `/devforge:research`) … a builder must preserve it"* three times (`:104`, `:108`, `:114`); *"per plan 18 Step 1 / Step 5"* (`:88`, `:104`, `:112`); *"That is a v1 simplification"* (`:199`). Longest lines: `:810` 1,367 chars, `:9` 1,265, `:707` 1,230, `:197` 1,219, `:104` 1,167.
- **Why it matters**: ≈ 22 k tokens on every turn as cache-read; the three "do not mirror research" paragraphs are instructions to a plan author, not to the model running the command. Discover is already the leaner sibling (research: 33 / 16 / 12 / 27) — which makes it the cheaper place to establish the Conventions-block + references pattern before applying it to research.
- **Fix**: `## Conventions` block (verbatim-copy, delegated-reply, end-the-turn); extract to `.devforge/command-refs/discover/`: `re-entry.md` (0.6 + attach arms of the save prompt, step 1, step 2, closing), `save-recovery.md` (step 5 exit 3), and a shared `memory-excerpt.md` both intake commands cite; delete the builder notes; collapse `:9` into two sentences. Predicted 88 → ~50 KB.
- **Cross-ref**: `scripts/emitters/claude.py` routes `references/` automatically; a shared reference across two commands is NEW — the emitter writes per-command directories, so either duplicate the file into both or add a shared slot (decide at plan time). `src/CLAUDE.md` catalog line for `/discover`.
- **Reaction**: pending.

### 4. Docs reads are forced through CBM on the strength of a one-shot hook — MEDIUM

- **Location**: `main.md:275` (*"Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`"*), `:460-465` (Layer 1: four `docs/` files *"via the CBM graph"*), `:467` (*"forbidden and will be blocked by runtime hooks on the first matched call per session"*). Hook: `src/hooks/cbm-code-discovery-gate` — blocks the first `Read|Grep|Glob` of a session for any path, then passes everything.
- **Issue**: `:467` is closer to the truth than research's `:412` (it says "first matched call"), but it is still the reason given for forbidding `Read` on markdown, and the hook's own message permits exactly that. Six docs reads per run become 12–18 CBM calls.
- **Fix**: `:275` and `:460` say `Read` for the four docs paths; `:467` scoped to source. Same as research audit finding 5; OQ-2 decides the rest.
- **Cross-ref**: `src/settings.template.json:28`; specify's audit finding 11 is the third sibling.
- **Reaction**: pending.

### 5. The absence-probe guard runs only after the report is on disk — MEDIUM

- **Location**: `main.md:595` (*"Phase 4's `finalize-handoff` rejects a save whose report is absence-founded and carries no probe … Run the probe here, in Phase 3, rather than meeting that rejection at the save flow's step 5, where the report is already on disk and only the handoff fails"*). Code: `_cmds_handoff.py:208-210` (`requires_absence_probe` guard, plan 73 D6); `cmd_verify` (`_cmds_core.py:565+`) has invariants A–G and no absence invariant.
- **Issue**: `verify` passes, the user confirms, the directory and branch exist, the report is written, and only then the handoff fails. The spec's mitigation is a sentence asking the model to remember.
- **Fix** (code + text): invariant **H** in `verify` — *"when `build_vs_buy.recommendation == Build` and no `internal:` prior-art row exists, at least one `absence_probes` row is required"* — the same predicate `requires_absence_probe` already computes; `finalize-handoff` keeps its guard as backstop; `:595` shrinks to the letter.
- **Cross-ref**: research audit finding 7 (same class, three guards); `tests/lib/test_discover_handoff_cli.py`; `/discover` and `/research` share the plan-73 D6/D7 mirror — fix both.
- **Reaction**: pending.

### 6. Per-row setters make Phases 2–3 the turn multiplier — MEDIUM (cost)

- **Location**: Step 2.0 `:399-414` (two calls per internal hit), Step 2.1 `:444-450` (one per prior-art result), Step 2.2 `:478-506` (`record-integration-touchpoint` + `record-fit-assessment` per touchpoint, cross-validated by name — `_cmds_fit.py:63`; then three aggregates), Phase 3 `:521-640` (ten setters), Phase 4 (six calls). 54 helper call sites in the spec.
- **Issue**: a run with three internal hits, four prior-art results and three touchpoints makes ≈ 6 + 4 + 9 + 10 + 6 calls in Phases 2–4 plus ≈ 17 in Phases 0–1 ≈ 52 helper calls, each its own turn. The touchpoint / fit-assessment pair also carries its own failure class (`--touchpoint` must match a recorded `--name`, `:498`).
- **Why it matters**: the diagnosis established that turns, not bytes, are the price; this is discover's share of plan 124 L1.
- **Fix** (code + text): `record-prior-art --rows '[…]'`; `record-touchpoints --rows '[{name, module_path, reason, user_expected, reality, effort, blockers}]'` — touchpoint and assessment in one row, which removes the name-mismatch failure outright; `apply-report --json` for Phase 3's scalar setters. Per-row verbs stay. Predicted ≈ 52 → 15–18 helper calls.
- **Cross-ref**: validators in `_cli.py` enums and `_cmds_fit.py`; batch verbs must evaluate invariant G and the touchpoint-match rule per row with the same stderr shape. Plan 124 directive must be rewritten first.
- **Reaction**: pending.

### 7. Stream A has no skip clause when Step 2.0 covered every capability — LOW

- **Location**: `main.md:434` (*"When Step 2.0 surfaced internal hits, EXCLUDE the capabilities already covered … Stream A surveys only the GAP capabilities"*) — nothing says what happens when the gap set is empty; `:436-450` then lists three web sources and a setter per result. v1 `research.md` PHASE 3 had the explicit rule *"No signals found → Skip this phase entirely."*
- **Issue**: an internal-only feature (every capability already implemented somewhere) still gets a web survey, because the only instruction is to narrow the query, never to drop it.
- **Fix**: one sentence after `:434`: *"When the gap set is empty, skip Step 2.1, record no web prior-art, and say so in the Step 2.0 gate message."* Confirm at fix time that invariant A's required fields for the proceeding verdicts do not include a web prior-art row (`_cmds_core.py:565-90`).
- **Reaction**: pending.

### 8. The v1 overlap check against existing features is gone — LOW

- **Location**: `main.md:735` (*"A seedless run ALWAYS allocates a new directory, even when an earlier `/devforge:discover` already covered the same topic — this command does no topic matching"*); v1 rule 5 scanned `specs/` and asked before proceeding.
- **Fix**: under the save question, list existing `specs/**/discovery-report.md` whose slug shares a token with the proposed one (`artifact_helper find-feature-artifacts` exists; no new stop). Same as research audit finding 9(b).
- **Reaction**: pending.

### 9. `Reconsider` has no alternative slot — LOW

- **Location**: `main.md:611` (verdict), `:617-623` (`set-recommendation --action --next` runs on every verdict; nothing requires the action on `Reconsider` to name an alternative or a scope change). v1: *"Not recommended: [Reason]. Consider [alternative] instead."*
- **Fix**: text at `:617`: on `Reconsider`, `--action` names the alternative or the scope change that would flip the verdict; optionally invariant A's `Reconsider` minimum requires it.
- **Reaction**: pending.

### 10. Two enums for the same scale with different spellings in one command — LOW

- **Location**: `_cli.py:31` `COMPLEXITY_ENUM = ("Low", "Med", "High")` vs `:34` `EFFORT_ENUM = ("Low", "Medium", "High", "Major refactor required")`; spec `:540` documents the trap (*"note: `Med`, not `Medium`"*) instead of removing it; `_handoff_build.py:168-169` writes `likelihood="Med"`.
- **Fix** (code): normalize `Med` / `Medium` on input for both setters; storage unchanged; delete the `:540` warning.
- **Reaction**: pending.

### 11. Stale or builder-only sentences; sibling drift — LOW bundle

- (a) `:104`, `:108`, `:114` — three *"do NOT mirror `/devforge:research`"* paragraphs addressed to a plan builder; delete (finding 3).
- (b) `:199` *"That is a v1 simplification"* — grill-seed mechanism's first version, a maintainer term.
- (c) `:467` hook claim — finding 4.
- (d) Turn cap 3 follow-ups per dimension (`:224`) vs research's 2 (`research/main.md:233`, `_research/_constants.py:37`) — same mechanism, two numbers, neither justified in either spec; pick one.
- (e) `append-outcome` is registered in `_discover/_cli.py` and called by no command spec (same orphan class as research's three).
- (f) `:286` says `AskUserQuestion` only for closed 2–4-option answers, then `:306` and `:321` use it for conflict and drift replies whose options are free values — consistent in practice, inconsistent in rule; one sentence.
- **Reaction**: pending.

### 12. The Step 2.0 gate message is a mandatory verbatim block even at zero hits — NIT

- **Location**: `main.md:418-428`. A fixed user-facing block (*"Internal canonical-pattern search found 0 existing implementations."*) that attaches no decision — not a stop, but a required echo.
- **Fix**: fold into one line of the Phase 3 render preamble, or keep only the N ≥ 1 form.
- **Reaction**: pending.

---

## Part 2 — Can `/discover` be simplified without losing quality?

### 2.1 Where the price is (static — never measured)

| | v1 `research.md` | v2 `discover/main.md` |
|---|---|---|
| Prose at invocation | 9.6 KB ≈ 2.4 k tokens | 88 KB ≈ 22 k tokens, zero references |
| Helper calls, clean run (3 internal hits / 4 prior-art / 3 touchpoints) | 0 | ≈ 52 (Phases 0–1 ≈ 17, Phase 2 ≈ 19, Phase 3 ≈ 10, Phase 4 ≈ 6) |
| Human stops | 1 | 13 (12 intake + save) |
| CBM calls | 0 | ≈ 10–20 (Step 2.0: 2 per verb × 1–5 verbs; Step 2.2: 4 docs via graph + chain) |
| Web calls | 0–3, conditional | 3–8, unconditional (WebSearch → Context7 ×2 per library → WebFetch) |
| Runtime | 14 min / 98 turns / 4 stops (v1 research median) | **unmeasured** |

**What each v2 layer buys** (from the comparison file): intake (echo-back + 10 prompts) buys a typed memo and a confirmed interpretation at 12 stops; investigation (Step 2.0 internal-first + G, Stream A, fit-check belief-vs-reality, absence probe) buys evidence v1 never produced at ≈ 19 helper + 10–20 CBM + 3–8 web calls; verification (A–G) is proportionate; artefacts are the pipeline.

### 2.2 Verdict

Yes — in the same three layers as research, with discover's stops the larger share:

| Layer | Findings | Moves | Prediction | Kind |
|---|---|---|---|---|
| Stops | 1 | 13 → 3 (echo-back, scoping table, save) | the dominant wall-clock item; unmeasured, so stated as a count | policy + text (reverses a ratified forcing function) |
| Turns | 6, 2, 5, 7 | helper calls 52 → 15–18; no resets; no post-save failure; no empty-gap web survey | ≈ −35 turns per run | code + text (124 L1) |
| Bytes | 3, 11, 4 | 88 → ~50 KB | cache-read per turn ≈ −8 % | text (124 L7) |

The web survey is the one cost with latency rather than turns (WebSearch / Context7 round-trips), and the only number for it is "never measured". Finding 7 is the cheapest cut there.

### 2.3 Do not cut

- Step 2.0 internal-first search and invariant G (with finding 2's retraction so G cannot trap) — v1 could recommend building what existed.
- The fit-check's `--user-expected` / `--reality` split; `set-overall-fit` + `set-effort-estimate` feeding invariant D.
- Build-vs-buy with `--reasoning`; design options as data-model / API / state-machine shapes; the derisk plan.
- The absence probe as a conditional (plan 73 D6 incident), moved under invariant H.
- The 0.5 echo-back — the one confirmation the scoping table merges into.
- The handoff and Phase 4's invariant (nothing outside `.devforge/` before the save confirmation).

### 2.4 The floor, stated honestly

After all three layers a clean run still makes ≈ 15 helper calls, ≈ 10–20 CBM calls (OQ-2's territory), 0–8 web calls and 3 stops. That is v1's shape (52 tool calls, 1 stop) plus the investigation forcing functions in 2.3; going below it means cutting one of them, which is OQ-1 / OQ-2 / OQ-3 and not this verdict. Every prediction above is static — a single profiled discover run (plan 124 item 7) is the precondition for any of this to carry a number.

### 2.5 Sequencing

1. Measure first: one discover run through the fixed profiler (124 item 7) — none exists.
2. Text only: findings 3, 4, 11, 12, 7, 9 — one author → reviewer pass.
3. Policy: finding 1 — decided together with research audit finding 3 (one scoping-table design, two commands).
4. Code + text: findings 2, 5, 10 — small verbs, invariant H, enum normalization.
5. Code + text: finding 6 — batch verbs, after plan 124's directive is rewritten.
6. Parity: finding 8.

---

## Part 3 — Open questions (shared with the research audit, plus one of discover's own)

- **OQ-1 (rubric)** and **OQ-2 (CBM)** — `RESEARCH-2026-10-07-RESEARCH-AUDIT.md` Part 3 carries them with their evidence; both apply here unchanged, with 8 dimensions instead of 6 and Step 2.0 as the third graph-shaped mechanism a CBM "no" would re-spec.
- **OQ-3 — Does `/specify` read the eight dimensions the discover handoff carries?** The handoff carries all eight as `DimensionRecord`s plus `references` (`_discover/handoff_schema.py:671-678`, `:745`). A name grep across `src/devforge/lib/_specify/*.py` finds `functional_scope` 0, `inputs_outputs` 0, `integration_points` 0, `non_goals` 0, `success_criteria` 0, `users` 4, `references` 1; `edge_cases` at `_specify/_schema.py:82` is specify's own DP category, not the discover field. The discover import (`_specify/_cmds_handoff.py:469-569`) visibly reads `discover_recommended_summary`, `AffectedArea` (with `is_internal_extension_candidate`), risks, open questions, `design_anchor` and `spec_seeds`. **Not established**: whether `_import_handoff_discover` (`:569`) maps the dimension block generically without naming fields — read it before concluding. If the dimensions are carried but unread, the rubric's justification (*a typed memo the handoff carries*) is weaker for discover than for research, and OQ-1's answer for discover follows from that alone. **Resolved 2026-10-07** — see `RESEARCH-2026-10-07-SPECIFY-VS-V1-SPECIFY.md` Part 5: the discover import is `_import_handoff_discover` at `_specify/_cmds_handoff.py:749` (the `:569` anchor above was wrong); it reads `spec_seeds` and two `plan_seeds` fields only, `discovery_block.memo_dimensions` has zero reads anywhere in `_specify/`, and `discovery-report.md` renders no scoping section — the eight dimensions reach `/specify` neither typed nor as prose.
