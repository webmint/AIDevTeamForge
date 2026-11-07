# RESEARCH — 2026-10-05 — `/devforge:specify` audit: size, logical inconsistencies, simplification

**Status**: evidence file for `133-SPECIFY-SIMPLIFICATION-PLAN.md`. On 2026-10-05 the maintainer asked for the findings to be saved as the next plan WITHOUT the one-at-a-time audit-reaction flow, so the `Reaction` lines below stay `pending` / `not presented` by design and the plan's D1–D9 carry the decisions instead. No `src/` edit has been made on the strength of this file.

**Scope**: `src/commands/specify/main.md` (1035 lines, 132,129 bytes, ~19.6 k words, no `references/` directory) read in full; claims cross-checked against `src/devforge/lib/_specify/*.py`, `src/devforge/lib/_shared/feature_alloc.py`, `src/hooks/cbm-code-discovery-gate`, `src/settings.template.json`. Cost figures are taken from `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` (sections cited inline) and are not re-measured here.

**Naming**: this file follows the root-level `RESEARCH-<date>-<topic>.md` precedent (`RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`); no `AUDIT-` prefix exists in the tree, so none is invented.

---

## Part 1 — Findings (12: 1 high, 5 medium, 5 low, 1 nit bundle)

Line numbers are those of `src/commands/specify/main.md` on 2026-10-05; they drift with every edit — grep the quoted text.

### 1. `from-here` is a no-op identical to `stay` — HIGH

- **Location**: `main.md:75` (Phase 0.2, third arm), confirmed by `main.md:19` and `main.md:612-626` (Step 4.1 branch block); code `src/devforge/lib/_specify/_cmds_phase4_setters.py:193-247` → `src/devforge/lib/_shared/feature_alloc.py:1051` (`decide_branch_action`, arm 3 `keep-other`).
- **Issue**: the AskUserQuestion offers `from-here` ("Create a spec branch from here") and promises "keep current branch as base; defer branch creation to Step 4.1". Step 4.1 calls `create-branch`; for current ≠ default and not `spec/*`, `decide_branch_action` returns `keep-other`: stdout is the `# already on non-default branch ...` comment, no checkout, `branch_created=False`. `main.md:19` itself says "only its default-branch arm emits a checkout". `from-here` and `stay` therefore produce identical state and identical git.
- **Why it matters**: the model, told to create a branch, either delivers nothing silently (user believes it is on `spec/*`) or runs `git checkout -b` by hand to honour the promise, at which point state (`branch_decision=keep`) and git disagree and the "Created and switched to branch" line is never printed because the helper never emits it.
- **Fix** (text only): drop `from-here`; the question becomes `"You're on <branch>. Switch to <default-branch> first, or stay on <branch>?"` with options `["switch-to-default", "stay"]`; delete the three `from-here` sentences (`:75`, `:612`, `:626`). Same fix adds the missing half-sentence on `switch-to-default`: after the checkout the default-branch arm applies, so creation is deferred to Step 4.1. Alternative rejected: a fourth arm in `decide_branch_action` — the function is shared with `/research` and `/discover`, neither offers `from-here`, so `/specify` would become the one command that branches off a non-default branch.
- **Cross-ref**: `from-here` occurs only in `src/commands/specify/main.md` (3 hits); zero in `src/devforge/lib` and in every other command. Rename safe.
- **Reaction**: pending (presented 2026-10-05).

### 2. The command is overloaded: no references, repeated boilerplate, maintainer commentary, rare paths inline — MEDIUM

- **Location**: whole file. Measured: 132 KB / 1035 lines / ~19.6 k words ≈ 33 k tokens at invocation (bytes/4; the diagnosis measured 30 k on 2026-09-27, the file has grown since). Second-largest command after `research` (207 KB); zero `references/` while `audit` (6), `grill` (4), `review` (4), `implement` (4), `fix`, `verify`, `constitute`, `configure`, `spec-check`, `finalize`, `summarize` all split on-demand text out under plan 63's `.devforge/command-refs/<name>/` layout.
- **Issue**, four concrete waste classes (counts by grep, 2026-10-05):
  1. Repeated protocol boilerplate: "copy … VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)" × 18; "ask the same question once more, and if the second reply again picks none" × 5; "exit code is 0 unless the helper itself fails" × 4 plus "a warning is NOT a verify failure" × 3; "Single-line question text" × 7; "End the turn" × 9.
  2. Maintainer history shipped to consumers: `v1` / `v3` references × 5 ("v3 verbatim", "parity tests of v1"); the "`use` removed" migration note (Step 4.6); two "Known limitation" paragraphs, one citing `constitute_helper forge-internal:verify-universal-defaults` (a maintainer verb); the "future Stage 2 enhancement" roadmap (Step 4.11); the `test_anchor` "currently deferred" note (Step 4.4); "That is a v1 simplification" (Phase 0.5); the HTML authoring comment (Step 4.10).
  3. Rare paths inline: re-entry (13 mentions), intake-rerun (9), bucketed (12), genuine-fallback (12), reset path (3). The five longest lines are the Step 4.3 `no-code-change` paragraph (2709 chars, `:657`), Phase 0.5 (2294, `:144`), Step 5.3 `request-changes` (2192, `:961`), Step 4.9 change-kind (2135, `:856`), and Step 5.4 `write-design-anchor` (1919, `:976`).
  4. Restatement: IMPORTANT RULES 8, 11, 12 repeat Step 4.9's non-blocking-warning semantics a third time each; Phase 2's priority order and its "7th category slots between" note appear twice.
- **Why it matters**: 33 k tokens of prose ride on every one of the run's ~200 turns as cache-read (diagnosis Part 2 §2.1: prose ≈ 25% of the per-turn context on `research`; `specify`'s share is similar); the rare-path prose is read on every run and used on almost none; the maintainer notes carry no instruction. Plan 124 lever 6 (L7, prose diet) names this class for `research` / `breakdown`; `specify` is not yet in its scope.
- **Fix**: (a) one `## Conventions` block near the top holding the three repeated protocols, cited by name from each site; (b) delete class 2 outright; (c) extract class 3 to `.devforge/command-refs/specify/` — `re-entry.md` (Phase 0.5 + arms (b)/(c) of Phase 0.4), `header-paths.md` (Step 4.1 bucketed + genuine-fallback limitations), `request-changes.md` (Step 5.3 reset path), `coherence-checks.md` (Step 4.9 trio + Step 5.2) — each loaded only when its condition fires; (d) collapse IMPORTANT RULES 8/11/12 to one-line pointers. Predicted: 132 KB → 70–80 KB main; quality-neutral by construction because no gate, validator or forcing function moves — only where the words live. See Part 2 for why this lever alone does not move the price.
- **Cross-ref**: `scripts/emitters/claude.py` `_PROMOTED` already routes `references/` to `.devforge/command-refs/<name>/`; `specify` has no entry there to add beyond the directory itself. Not yet grepped: every "see Step X" pointer inside the extracted paragraphs must be re-checked after extraction.
- **Reaction**: not yet presented.

### 3. Step 4.1 labels the legacy `<NNN>-<slug>` warm path "the normal case" — MEDIUM

- **Location**: `main.md:565` ("Warm path — state already carries `spec_number` and `feature_slug` (the normal case)"); contrast `main.md:567` ("the shape intake allocated before the `<YYYY>/<MM>` bucketed layout; nothing migrates those directories") and `main.md:136`; code `src/devforge/lib/_shared/feature_alloc.py:501` (`allocate_feature_dir` keys every NEW allocation on `strftime("%Y")`/`%m`; its module docstring at `:37` forbids reading "NNN" as describing a new allocation).
- **Issue**: intake allocates `specs/<YYYY>/<MM>/<leaf>` for every new feature, and `import-handoff` seeds `spec_number` only from a `<NNN>-<slug>` basename (`main.md:136`), so the warm path is reachable only for pre-plan-91 directories. The bucketed path is the normal case; the file says the opposite. The Step 4.1 intro (`main.md:563`, "On three of the four paths … `spec_number` + `feature_slug` decide which directory") and the Step 5.1 / Step 5.4 path lists (which name `specs/<NNN>-<feature-name>` first) inherit the stale framing.
- **Why it matters**: sentence-level hallucination seed. A fresh session reads "normal case", expects `spec_number` in state, and reaches for `assign-spec-number` on a bucketed directory — the exact misfire `main.md:566` warns against — or reports "no spec number" as an anomaly when it is the default.
- **Fix** (text only): relabel — bucketed = "the normal case for every directory intake allocates today"; warm/cold = "legacy `<NNN>-<slug>` directories (pre-plan-91), kept so they still resolve". Keep the four-path ORDER unchanged: `main.md:583` explains why warm/cold must be tried first (`import-handoff` reads a `<NNN>-<slug>` last segment first). Reword the Step 4.1 intro and put `specs/<YYYY>/<MM>/<leaf>` first in the two path lists.
- **Cross-ref**: "normal case" has 3 hits in `main.md` — `:71` (branch, correct), `:159` (no seed, correct), `:565` (stale). `feature_alloc.py:1012-1024` already describes Step 4.1's four paths by name and needs no change.
- **Reaction**: not yet presented.

### 4. The greenfield mandatory-read slot `specs/*/discovery-report.md` never auto-matches a bucketed path — MEDIUM

- **Location**: `main.md:518` (greenfield slot table) and `main.md:498` ("concrete patterns auto-match by path"); code `src/devforge/lib/_specify/_cmds_phase3.py:22-36` (`_slot_matches_path`), `src/devforge/lib/_specify/_schema.py:373`.
- **Issue**: `Path(read_path).match("specs/*/discovery-report.md")` matches right-anchored component-wise: for `specs/2026/10/<leaf>/discovery-report.md` the third component from the right is `10`, not `specs` → no match. The substring fallback strips only trailing `*` and `/`, so `base` keeps the literal `*` and is never a substring. Greenfield + bucketed layout is the only combination in which this file exists today, so `verify-mandatory-reads` exits 2 on every such run unless the model passes `--slot-pattern "specs/*/discovery-report.md"` for a non-sentinel slot, which `main.md:498` says is only for sentinels, or records `--n-a-reason` for a file it just read.
- **Why it matters**: a deterministic gate fails on the default layout; the recovery the model will find is a false N/A on a file that exists, which is exactly the silent-drop the slot table exists to prevent.
- **Fix** (code + test + text): change the slot pattern to `*/discovery-report.md` — `Path.match` right-anchors two components, so it matches both `specs/042-slug/discovery-report.md` and `specs/2026/10/<leaf>/discovery-report.md`; update the description string; add a test in `tests/lib/test_specify_helper.py` with both shapes; update `main.md:518`. Alternative: a `__discovery_report__` sentinel, rejected as a larger text change for the same effect.
- **Cross-ref**: `specs/*/discovery-report.md` occurs in `src/devforge/lib/_specify/_schema.py`, `src/devforge/lib/_specify/_topic.py`, `src/commands/specify/main.md`, `tests/lib/test_specify_helper.py` — four files, all in the same fix. `_topic.py`'s use must be read before changing (it may be a render-group key, not a slot).
- **Reaction**: not yet presented.

### 5. Phase 1.5's "≥3 findings OR marker" leaves no honest route for a source with 1–2 relevant items — MEDIUM

- **Location**: `main.md:306-313`; code `src/devforge/lib/_specify/_cmds_phase01.py:304-317` (`_source_coverage`), `:320-342` (`cmd_verify_findings`).
- **Issue**: `_source_coverage` returns `partial` for 1–2 findings regardless of the marker (the marker is consulted only at count 0), and no verb deletes a finding. A source with exactly one or two task-relevant items therefore has one exit: invent findings until three exist. The marker's own wording ("contains nothing task-relevant") forbids the honest alternative.
- **Why it matters**: the rule exists to stop silent dropping (variance rule #3 from the v1 parity tests); as implemented it manufactures padding instead, and padded findings must then be landed in §5–§9 by the coverage rule, so the invention propagates into the spec.
- **Fix** (code + test + text): let the marker waive `partial` too (`count < 3 and marker → clear`), and reword the marker's meaning in `main.md` from "nothing task-relevant" to "no further task-relevant items" (the verb name `mark-source-no-items-relevant` can stay; its help text changes). This keeps the forcing function — an explicit per-source assertion — and removes the padding incentive. Not a loosening to "≥1": a source with zero findings still needs the marker.
- **Cross-ref**: `mark-source-no-items-relevant` occurs in `_cmds_phase01.py`, `_cli.py`, `main.md`, `tests/lib/test_specify_helper.py` — four files.
- **Reaction**: not yet presented.

### 6. Phase 2 states two rules that point opposite ways, and the second is an escape hatch — MEDIUM

- **Location**: `main.md:342` ("Do not skip a decision point because the model has a default preference") versus `main.md:438` ("Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings").
- **Issue**: the DP definition (`:335-340`) plus the `set-dp-default-applied --delegated-reply` gate (`:373`) are built so that no value the user neither gave nor delegated enters state. `:438` hands the model a judgment call ("can I answer this from the codebase?") that lets it resolve a decision point itself with no setter trace — the shape the Meta-discipline zero-escape-hatch policy names. The two sentences have no bridge.
- **Why it matters**: on auto mode the model is already nudged to work on without asking; `:438` is the sentence it will cite when it does. The decision-point protocol is one of the parts the diagnosis lists as credited (the Coupling decision point).
- **Fix** (text only): rewrite `:438` so it restricts the DEFINITION, not the asking: "A choice the codebase or the Phase 1.5 findings already settle has ONE valid implementation and is not a decision point; record why under the category's `no_DP_in_category` rationale. A choice with two or more valid implementations is asked, whatever you would pick." Keep the surface sentence that follows it.
- **Cross-ref**: "CANNOT answer by reading" occurs only in `src/commands/specify/main.md`.
- **Reaction**: not yet presented.

### 7. Phase 3 Step 1's handoff-seeded precondition has a gap for discover imports — LOW

- **Location**: `main.md:467` (fires only when `source.handoff_kind == "research"`) and `main.md:474` ("Skip this precondition entirely when … `spec_type_seeded_by_upstream` is false OR `spec_type` is null"); code `src/devforge/lib/_specify/_cmds_handoff.py:837-838` (discover import sets `spec_type=greenfield_feature` and `spec_type_seeded_by_upstream=True`).
- **Issue**: after a discover import, neither sentence covers the state (seeded true, type set, kind discover). The origin-based paragraph (`:490`) later re-asks via the `discovery-report.md` read and re-calls `classify-spec-type`, so the run proceeds — but the stated precondition is incomplete and a reader cannot tell whether the discover case was forgotten or intended.
- **Fix** (text only): one sentence at `:474`: "or when the imported handoff is a discover handoff — the origin-based pre-seed below handles that case."
- **Cross-ref**: `spec_type_seeded_by_upstream` appears in 3 helper modules, 6 test files and 3 fixtures — none change; text-only.
- **Reaction**: not yet presented.

### 8. Step 5.2 re-runs three of the four non-blocking checks and omits `verify-scope-coherence` — LOW

- **Location**: `main.md:946-954`; heading names "Constitution, numerical-consistency and change-kind-coherence".
- **Issue**: the stated reason for the re-run ("state may have changed since Phase 4 first ran them") applies equally to scope coherence — a `request-changes` loop that appends a §6 entry is the exact trigger. Rule 11 (`:1034`) says nothing about a recheck either.
- **Fix** (text only): add the fourth call to Step 5.2 and its heading; one clause in rule 11.
- **Cross-ref**: `verify-scope-coherence` is named in `src/commands/plan/main.md` as well (one line, a reference to what `/specify` ran); unaffected.
- **Reaction**: not yet presented.

### 9. `set-finding-landed --landed-ref` is unvalidated free text — LOW

- **Location**: `main.md:835` (Step 4.9 `verify-coverage` bullet); code `src/devforge/lib/_specify/_cmds_phase4_setters.py:698-745`.
- **Issue**: the verb validates `--finding-id` and `--landed-in` but stores `--landed-ref` (e.g. `AC-3`) without checking that such an entry exists in the named bucket. A finding can be marked landed on nothing, and `verify-coverage` passes. The sibling path (`--finding-ref` on the setters) is advertised at `:835` as "a typo fails loudly, never silently passes coverage"; this path does not meet that bar.
- **Fix** (code + test): when `--landed-ref` is given, require it to name an existing entry of the bucket (`AC-<n>` present in `acceptance_criteria`, and so on); exit 2 otherwise. Text: one clause at `:835`.
- **Cross-ref**: `set-finding-landed` occurs in `_cli.py`, `_cmds_phase4_setters.py`, `main.md`, `tests/lib/_specify/test_landing.py` — four files.
- **Reaction**: not yet presented.

### 10. `request-changes` re-runs Step 4.10 and re-asks the design source on every loop — LOW

- **Location**: `main.md:961` ("re-run Phase 4 Step 4.9 verifiers + Step 4.10 design-source capture + `render` + …").
- **Issue**: `set-design-source` is a persisted scalar; nothing in a `request-changes` pass invalidates it, yet the loop re-asks the user. One extra stop per loop. Overlaps `123-PROJECT-TYPE-GATED-DESIGN-INTAKE-PLAN.md` (stub: "the design intake fires on every project, whose type is never established"), which gates the FIRST ask; this finding is about the repeat.
- **Fix** (text only): drop "Step 4.10 design-source capture" from the re-run list; add "the design source persists across the loop; re-run Step 4.10 only when the user names it as what to change".
- **Cross-ref**: "Step 4.10 design-source capture" occurs only in `main.md`. Plan 123 should be told of the overlap when it is built.
- **Reaction**: not yet presented.

### 11. Phase 3 Step 3 opens by mandating Glob/Grep, then forbids them for the discovery it describes — LOW

- **Location**: `main.md:532` ("Use Glob/Grep tools specifically (not Bash `grep`/`find`) so the tool-call log is auditable") versus `main.md:539` (item 4: "do not use raw `Read` over source-extension files (runtime hooks block raw calls on first match per session)") and `main.md:227` (§1.4: "do NOT use raw `Read`/`Grep`/`Glob` for source-code discovery"); hook `src/hooks/cbm-code-discovery-gate` (PreToolUse matcher `Read|Grep|Glob`, `src/settings.template.json:28`; blocks once per session and tells the model "Fall back to Grep/Glob/Read only for non-source text content").
- **Issue**: the opening sentence sends the model straight into the hook; the retry passes (the gate fires once), so the cost is one blocked call and one turn per run plus a contradiction a reader must resolve by reading the hook.
- **Fix** (text only): make the opening sentence say what the hook says: "For non-source text (docs, config, markdown) use the Glob/Grep tools, not Bash `grep`/`find`, so the tool-call log is auditable; for source files use the CBM chain below."
- **Cross-ref**: "Use Glob/Grep tools specifically" occurs only in `main.md`.
- **Reaction**: not yet presented.

### 12. Stale sentences (sentence-level hallucination check) — NIT bundle

- `main.md:29` "Four preflight steps run in order" — Phase 0 has six (0.1–0.6). Only hit for "Four preflight" is this line.
- `main.md:978` "Write the handoff artefact first" — the `write-design-anchor` step now precedes it (`:974-976`). Only hit for "handoff artefact first" is this line.
- `main.md:21` and `:976` call `design-anchor.json` an "immutable design-intent record" while `:132` and `:976` say the helper "overwrites unconditionally" / "a re-run overwrites it". Only hits for "immutable design-intent" are in `main.md`. Fix: "structured design-intent record, rewritten only by `/devforge:specify`".
- `main.md:23` "both exist by the time Step 5.4 reaches either commit-artifacts call" is unguarded: `write-design-anchor`'s failure arm (`:976`) says "address the cited cause, and re-run", never "end the turn", so a model that proceeds past a failed anchor write reaches `commit-artifacts` with one of the two files missing. Fix: make the failure arm end the turn, like every other exit-2 site.
- **Fix**: four one-line edits in the same plan phase as finding 1.
- **Reaction**: not yet presented.

---

## Part 2 — Can `/specify` be simplified without losing quality? Where its price sits against v1

Measured figures are the diagnosis's (`RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`, F3, F7, Part 2 §2.1); static counts are from `main.md` on 2026-10-05.

### 2.1 Where the price is

| `/specify` | v1 (median of 17 runs) | v2 heavy run (2026-09-27) |
|---|---|---|
| LLM minutes | 11.5 | 19 |
| assistant turns | 50 | 197 |
| helper calls | 0 | 63 |
| stops for the human | 1 | 2 |
| output tokens | 42 k | 101 k |
| cache-read tokens | 5.0 M | 22.8 M |
| cache-read per turn | ≈ 100 k | ≈ 116 k |
| CBM result bytes | 0 | 0 |
| prose loaded at invocation | — | 30 k tokens (33 k today) |

Three facts fall out for this command specifically:

1. **Per-turn context is nearly equal** (≈ 100 k vs ≈ 116 k). The ×4.5 on cache-read is the ×4 on turns, not fatter turns. A prose diet alone (finding 2) cuts the per-turn figure by roughly 10 k and leaves the turn count where it is.
2. **Turns come from helper calls.** Assistant turns ≈ 2 × tool calls in both generations (diagnosis §2.1): 63 helper calls ≈ 126 of the 197 turns. CBM is not `/specify`'s cost (0 calls on the measured runs).
3. **Stops are already at v1 level** (2 vs 1). Cutting questions buys nothing here; the two stops are the decision-point round and the approval gate, both credited.

Static minimum helper calls per phase on a thorough run (counted from `main.md`; the measured heavy run made 63, so real runs under-fill the minimum):

| Phase | Calls | Of which per-item setters |
|---|---|---|
| 0 preflight / reset / find / import | 4 | 0 |
| 1 reads + finalize | 9–16 | `record-input-read` × 8–15 |
| 1.5 findings + render + finalize | 30–50 | `record-finding` × ≥3 per source |
| 2 decision points + coverage + finalize | 12–20 | `record-decision-point` × ≥7, `set-dp-*` × N |
| 3 classify + mandatory reads + finalize | 6–18 | `record-mandatory-read` × 3–15 |
| 4 header + sections + 7 verifiers + design + render + stamp | 35–60 | `add-ac` × ≥7, `record-*` × N |
| 5 summary + 3 rechecks + anchor + handoff + commit + block | 8 | 0 |

### 2.2 Verdict

Yes — in two layers, and only the second moves the price.

**Layer A — prose diet (finding 2 + plan 124 L7 extended to `specify`).** 132 KB → 70–80 KB. Zero quality risk: no gate, validator or forcing function changes, only where the words live. Effect on price: small (≈ −10% cache-read per turn). Worth doing because the same edits carry findings 1, 3, 6, 7, 8, 10, 11, 12.

**Layer B — turn diet (plan 124 L1 applied to `specify`, plus composite verifiers).** The quality of `/specify` lives in its VALIDATORS (EARS regex, `--finding-ref` existence, `--delegated-reply` required, `--path-evidence` shape on `no-code-change`, `nfr` quantifier, constitution-ref existence, the four-bucket coverage rule) and in its ENUMERATIONS (Phase 1.5 findings, seven DP categories, seven AC subsections). Neither depends on one process spawn per field. Concretely:

- `apply-findings --from-json`: Phase 1 reads + Phase 1.5 findings + markers in one payload; runs the ≥3-or-marker rule and the path auto-tag; names the failing source. Replaces 40–65 calls with 1–2.
- `apply-decision-points --from-json`, one call per question ROUND (answers arrive per round, so this cannot be one call per run); carries the `--delegated-reply` gate and the follow-up cap. Replaces 12–20 calls with 2–4.
- `apply-spec-sections --from-json`: §1–§9 in one payload with every per-entry validator; names the failing entry and field. Replaces 35–60 calls with 1–3. `revise-ac` stays for the `request-changes` loop.
- `phase4-finalize` and `phase5-recheck` composites: the 4 blocking + 3 non-blocking checks in one call with grouped stderr (precedent in the same helper: `findings-finalize`, `dp-finalize`, `phase3-finalize` already wrap a verifier). Replaces 7 + 3 calls with 2.

Predicted (static, not measured): heavy path 63 → 15–20 helper calls; turns 197 → 90–110; output tokens roughly halved (the setter payloads that repeat conversation text disappear); wall time ≈ −40–50%. The diagnosis's condition stands: a batch validator that reports only "invalid" costs more turns than it saves, so every message must name the field.

**Quality-neutral deletions found by this audit (no plan 124 lever covers them):** Phase 0.6 model advisory (one read + one line the user "is free to ignore": −1 call, −1 turn); the Step 5.3 re-ask of the design source (finding 10: −1 stop per loop); IMPORTANT RULES 8/11/12 (restatements).

### 2.3 Do not cut

The parts the benchmark and plan 81 credited, all of which survive Layers A and B unchanged: Phase 1.5 findings enumeration (anti-silent-drop); the four-bucket coverage rule (every finding lands); the seven-category DP sweep with the delegated-reply gate; the §5.2 reachability citation (plan 81 F3, Step 4.4) and the §4 `no-code-change` path evidence (plan 107); the design anchor; the typed specify→plan handoff; the two human stops. The diagnosis's §2.4 list and this one agree.

### 2.4 The floor, stated honestly

After both layers `/specify` does not return to v1's 50 turns. v1 had no state machine, no findings enumeration and no DP sweep; the residual ≈ 90–110 turns IS those three things, i.e. the quality. Whether that quality is worth ×2 on turns is unproven on outcome: the diagnosis's F8 rests on one v2 run with a different model, and the plan-81 acceptance re-run has not happened. The only measurement that settles it is the ablation in the diagnosis Part 1 §5 (same v2, batch writes on, grill + spec-check off), run through `profile_helper` after its F9 marker anchor is fixed.

Two chain-level levers that are not `/specify`'s but dominate what the maintainer sees: a fresh session per pipeline command (diagnosis F10: cache-read per message grew 276 k → 580 k across one feature without `/clear`), and the grill policy knob (plan 124 L3, ≈ 1 h and ≈ 26 M tokens per feature outside `Strict`).

### 2.5 Sequencing note

Plan 124 is queued after plans 106–123 by maintainer directive (2026-09-28). The `specify`-specific Layer B above is plan 124 lever 1 narrowed to one helper; building it ahead of the queue needs that directive revisited. Layer A and findings 1, 3–12 need no such revisit: they are a text-and-small-code plan on their own.
