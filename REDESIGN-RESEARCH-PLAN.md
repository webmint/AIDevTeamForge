# /research redesign plan

Active branch: `develop-2.0-init` (or successor — confirm at session start).
Status: planning. No code edits yet.

## Why redesign

`/research` exists at `src/_pending/commands/research.md` (pre-promotion). Its current spec was authored under the old setup-wizard architecture + before Plan F docs/ + CBM landed. Per session 2026-05-08 empirical test, the current discovery flow has a precision gap: graph-only searches miss inline framework expressions (Vue `<script setup>`, React hooks, Svelte reactive blocks). Redesign target: a discovery flow that lands precise root cause for typical UI/logic bugs without forcing source reads as the next step after graph queries.

The redesign should integrate with the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) — once /constitute populates `constitution.md`, /research can consult it.

## Prerequisites (hard gate)

`/research` refuses to run unless all setup-chain commands have completed. Helper `preflight` subcommand checks four artefacts at startup; exits non-zero with explicit instruction if any missing:

| Required artefact | Produced by | Hard-gate check |
|---|---|---|
| `.devforge/manifest.json` (or equivalent) | `/init-forge` | File exists |
| `docs/architecture.md` | `/generate-docs` | File exists + non-empty |
| `.devforge/project-config.json` | `/configure` | File exists + non-empty |
| `constitution.md` | `/constitute` | File exists + non-empty |

On missing artefact, helper emits:

```
BLOCKED: /research requires the full 4-command setup chain.
Missing: <artefact>
Run: /init-forge → /generate-docs → /configure → /constitute, then retry /research.
```

Exit code 2. No graceful skip, no fallback path. Mirrors `/discover` hard gate (DISCOVER-PLAN.md).

## Phases (target order)

```
PHASE 0: Symptom clarification     ← rubric-driven Q&A (6 dimensions), orchestrator-only
PHASE 1: Investigation             ← CBM chain + docs read + hypothesis enumeration; dispatch framework-owned `research-investigator` subagent (at `src/agents/research-investigator.md`) for the heavy CBM phase. No external plugin dependency.
PHASE 2: Report drafting           ← orchestrator composes report from Phase 0 memo + Phase 1 findings + hypothesis set
PHASE 3: Save + recommend          ← ask-to-save; saved md ends with copy-pasteable /specify prompt section (manual copy, no automation)
```

## Existing-code awareness layer (docs + MCP)

`/research` consults **two layers** when investigating existing code — both Phase 0 (clarify symptom against known surfaces) and Phase 1 (locate + trace + hypothesize):

### Layer 1: docs/ narrative context

Read by orchestrator (Phase 0 pre-rubric step) and investigation subagent (Phase 1):

- `docs/architecture.md` — project-tier architecture
- `docs/<package>/architecture.md` — package-tier architecture
- `docs/<package>/<concern>/index.md` — concern md (orientation for affected area)
- `docs/glossary.md` — term grounding

Use docs/ for **narrative orientation**. Mirrors `/discover` two-layer pattern.

### Layer 2: CBM/MCP structural queries

CBM (codebase-memory-mcp) tools called by Phase 1 investigation subagent + orchestrator. **Discovery chain is MANDATORY** per Findings §1:

1. `agentic_context "<symptom>"` — synthesized bundle (when LLM mode enabled)
2. `search_graph(name_pattern=..., label=..., qn_pattern=...)` — named symbols (high-signal first; File-label queries use `name_pattern` per memory `feedback_cbm_search_graph_pattern_keys`)
3. **If step 2 returns 0 hits for an expected behavior** → `search_code(pattern=...)` with literal token (`.sort(`, `.filter(`, `.localeCompare(`, etc.) over suspected package files. Catches inline framework expressions invisible to graph (Findings §1).
4. `trace_path(function_name, mode=calls|data_flow|cross_service)` — impact analysis on confirmed surfaces
5. `get_code_snippet(qualified_name)` — read source (NOT raw Read/cat)
6. Only after `search_code` also returns nothing → declare "truly absent" + escalate to source `Read`

**Confidence calibration**: 0 hits at `search_graph` alone = "no NAMED implementation"; 0 hits at `search_code` = "truly absent". Spec must NOT conflate these.

### Runtime enforcement (hooks already shipped)

Same 4 hooks at `src/hooks/` (shipped 2026-05-09 per `project_track1_f11_hooks_shipped`):

- `cbm-session-reminder` (SessionStart) — injects CBM-first protocol into context
- `cbm-code-discovery-gate` (PreToolUse Read|Grep|Glob) — once-per-session block
- `bash-ban-raw-tools` (PreToolUse Bash) — once-per-session block on raw `grep`/`find`/`cat` over source-file extensions
- `cbm-mcp-marker` (PostToolUse Bash|mcp__codebase-memory-mcp__.*) — telemetry to `.devforge/cbm-usage.log`

Hooks fire once per session as reminder. `/research` spec MUST instruct orchestrator + subagent to use CBM tools by name in briefs.

### Preflight gate

Before Phase 1 dispatches, orchestrator runs preflight:

```
./.devforge/lib/generate_docs_helper preflight
```

Skip if `.devforge/.preflight-stamp` is fresher than 60s. Ensures CBM index is current. If preflight fails, emit error + instruct user to run `index_repository` (or rerun `/generate-docs`).

## Phase 0: Symptom clarification

**Goal**: convert vague symptom input ("items not sorted") into a structured symptom memo before any investigation fires. Lighter than `/discover` rubric (6 dimensions vs 8) — investigation is the heavy phase here, not elicitation.

**Shape**: rubric-driven Q&A. Helper owns the rubric; LLM asks one question at a time targeting the highest-uncertainty dimension; helper records via setters.

**Rubric (6 dimensions, bug + enhancement neutral)**:

| Dimension | What it captures | Bug example | Enhancement example |
|---|---|---|---|
| `symptom` | What's wrong (bug) or what needs to change (enhancement) | "Items not sorted in admin products view" | "Export is slow on large datasets" |
| `affected_area` | Which UI / module / feature surface | "Admin > Products > List page" | "ExportService background job" |
| `repro_or_current` | Repro steps (bug) or current behavior (enhancement) | "Open list with 50+ items, scroll" | "5 min runtime on 100K rows; synchronous" |
| `desired` | Expected behavior (bug) or desired behavior (enhancement) | "Alphabetical by name, A→Z" | "Under 30s OR async with progress" |
| `scope` | One place / feature-wide / cross-cutting | "One component" | "Feature-wide; touches DB + service + UI" |
| `unchanged_behavior` | What must NOT regress (regression scope, distinct from `scope` — `scope` = where we look, this = what must keep working). Adopted from Kiro Bugfix triplet (source: <https://kiro.dev/docs/specs/>) | "Filter + pagination on same page must keep working" | "Existing small-dataset exports must stay synchronous + complete in ≤2s" |

**State enum**: `Clear` / `Partial` / `Missing` (same as `/discover`, aligned with GitHub Spec Kit taxonomy).

**Bounded turns**: hard cap 2 follow-ups per dimension (lighter than `/discover`'s 3 — investigation matters more here). After cap, dimension logged as `Partial` and helper moves on.

**Mode signal**: Helper detects bug-vs-enhancement framing from `symptom` content (token signals: "fails", "broken", "wrong", "missing" → bug; "slow", "should", "add", "support" → enhancement). Mode stored in `SymptomMemo.mode` field, drives Phase 2 Verdict copy adaptation.

**Pre-rubric docs scan** (orchestrator-side):

Before asking the rubric questions, orchestrator reads `docs/architecture.md` + `docs/glossary.md` to surface candidate `affected_area` hints. When user reaches the `affected_area` question, orchestrator offers detected hints as starting suggestions (e.g., "I see packages X, Y, Z — likely affected?") rather than asking blind. Docs presence guaranteed by hard-gate prerequisites.

**Persistence**: SymptomMemo saved to `.devforge/research-state.json` after every setter call (mirrors `/constitute` + `/discover` per-answer persistence). Kill-and-resume supported.

**Question strategy per dimension**: closed-choice (`scope`) → AskUserQuestion; open dimensions (`symptom`, `repro_or_current`, etc.) → free-text prompts (single-line per memory `feedback_askuserquestion_single_line_only`).

**Exit**: when all 6 dimensions are `Clear` OR user explicitly accepts gaps. On accepted-gap exit, helper emits:
- Coverage summary table (`Clear`/`Partial`/`Missing` per dimension)
- `[NEEDS CLARIFICATION: <dimension> — <gap description>]` markers serialized into `SymptomMemo.gaps`

`symptom-finalize` exit code: `0` when all `Clear`; `0` with `override_recorded=true` when user accepted gaps; non-zero otherwise.

**Misalignment detection (hybrid by severity)**:

When user's later answer contradicts or drifts from earlier confirmed dimensions, helper + orchestrator detect and respond by severity. Mirrors `/discover` Option C hybrid. Three categories:

| Category | Example | Detection layer | Response |
|---|---|---|---|
| **Direct contradiction** | `desired` = "alphabetical A→Z" + `unchanged_behavior` = "current numeric order must remain" | **Helper-side** (token-overlap rule, deterministic, no LLM) | **Hard-block.** Halt rubric Q&A, present conflict via AskUserQuestion ("which to keep?"), rewrite loser dimension, then resume. |
| **Drift / scope creep / mode flip** | Symptom signaled bug, later answers describe enhancement shape (desired behavior is a new capability, not a fix); OR `affected_area` = "one component" while later evidence shows feature-wide touchpoints | **LLM-side** (orchestrator runs short check after each setter call: "does this new answer expand or conflict with previously confirmed dimensions?") | **Soft-flag.** Log to `conflicts` list, continue rubric Q&A, surface at next natural pause. For mode-flip drift, prompt user to confirm mode (rerun `detect-mode` with override). |
| **Refinement** | `affected_area` = "Admin > Products" → later "Admin > Products + Admin > Orders" — narrower answer becomes superset | **LLM-side** (same check, classified as refinement when older answer is subset of new) | **Quiet update.** Rewrite affected dimension, log change in memo, no interruption. |

**Per-setter call protocol**:

```
After every set-<dimension>:
  1. Helper runs check-conflicts (token-overlap rules; cheap, deterministic).
     If direct contradiction → block via AskUserQuestion, record resolution, rewrite loser dimension.
  2. Else orchestrator runs LLM-side drift check (short prompt).
     If drift detected → log to SymptomMemo.conflicts with type=drift, surface at next pause.
     If refinement detected → log + quietly rewrite affected dimension.
     If mode-flip detected → log + rerun detect-mode with user confirmation.
  3. Resume rubric Q&A.
```

**Anti-patterns explicitly forbidden**:

- Silent overwrite — later answer must never replace earlier without surfacing in conflicts log.
- LLM-only detection for direct contradictions — token-overlap rules run first; LLM only handles semantic drift.
- Force user to re-walk all 6 dimensions on conflict — only re-ask the affected dimension(s).

**What Phase 0 feeds**:

- Phase 1 investigation subagent: narrowed brief built from `symptom + affected_area + scope` (e.g., "Investigate items-not-sorted symptom in Admin > Products > List; scope: one component" instead of raw user input).
- Phase 1 CBM query construction: `search_graph` patterns derived from `affected_area` package + `symptom` tokens.
- Phase 2 report: every section informed by memo (Codebase Findings scoped to `affected_area`; Approaches framed against `desired` behavior + `scope`; Verdict copy adapts to `mode`).

## Phase 1: Investigation

**Goal**: produce concrete file:line findings + root cause hypothesis + ≥2 hypothesis enumeration (per Findings §2) + recommended runtime verify step.

**Dispatched subagent**: framework-owned `research-investigator` at `src/agents/research-investigator.md` (read-only code locator, returns compressed file:line table + hypothesis enumeration). Agent definition is framework-internal — emitted via `scripts/emitters/claude.py` to `.claude/agents/research-investigator.md` in target project. No external plugin dependency. Pattern may be adapted from `cavecrew-investigator` as reference (if it fits), but the file lives in the framework. Brief includes Phase 0 SymptomMemo + docs/ pre-read findings + CBM tool list with mandatory chain order.

**Investigation protocol** (encoded in subagent brief):

1. **Read docs layer first**: `docs/architecture.md` + `docs/<affected_package>/architecture.md` + `docs/<affected_package>/<closest_concern>/index.md` + `docs/glossary.md`.
2. **CBM discovery chain (MANDATORY)** per Findings §1:
   - `agentic_context "<symptom + affected_area>"` for synthesized bundle.
   - `search_graph(name_pattern=...)` for named symbols matching symptom tokens.
   - If 0 hits → `search_code(pattern=<literal token>)` over affected package.
   - `trace_path` on candidate surfaces for impact chains.
   - `get_code_snippet` to read source on highest-confidence candidates.
3. **Hypothesis enumeration (MANDATORY ≥2)** per Findings §2: enumerate plausible root causes; for each, write a one-line falsifier (what would disprove it).
4. **Verify step recommendation**: for hypotheses needing runtime data (lifecycle race, framework lifecycle gap, vendor side-effect), recommend a specific probe (`app.config.warnHandler` capture, console-log probe, breakpoint dump, network-tab inspection).
5. **Raw Read/Grep/Glob over source forbidden** — hooks (`bash-ban-raw-tools` + `cbm-code-discovery-gate`) will block first attempt; spec instructs subagent to never even try.

**Subagent output**: structured findings table + hypothesis list + verify-step recommendation. Returned to orchestrator as compressed text.

**Cost gate (closes Open question §4)**: before dispatching Phase 1, orchestrator surfaces estimated CBM call count + token cost based on `affected_area` scope. User confirms before fire. Mirrors `/generate-docs` Phase 1 cost gate.

## Phase 2 report shape (target)

```markdown
# Research: [Topic Name]

**Date**: [YYYY-MM-DD]
**Topic**: [user's original input]
**Mode**: Bug | Enhancement
**Verdict**: [adapts to Mode — see below]

## Summary

[3-5 sentences: what was found, root cause, recommended approach, remaining uncertainty]

## Symptom

| Dimension | Value |
|---|---|
| Symptom | [from SymptomMemo.symptom] |
| Affected area | [from SymptomMemo.affected_area] |
| Repro / Current | [from SymptomMemo.repro_or_current] |
| Desired | [from SymptomMemo.desired] |
| Scope | [from SymptomMemo.scope] |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance |
|---|---|---|
| [module/area] | [path:line] | [how it relates to symptom] |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: [most-likely cause + 1-2 sentence reasoning chain tying to file:line evidence above]

**Confidence**: Confirmed (verified via probe) / Hypothesis (needs probe) / Speculative (multiple plausible)

### Structured root cause (bug mode, when confidence ≥ Hypothesis)

Adopted from Google SRE postmortem template (source: <https://sre.google/workbook/postmortem-analysis/>). Helper renders only when `mode == "bug"` AND `confidence ∈ {Confirmed, Hypothesis}`. Omitted on `Speculative` or enhancement mode.

| Field | Captures | Example |
|---|---|---|
| `trigger` | What fired the failure NOW (the immediate event) | "User scrolled past 50 items + new item created concurrently" |
| `root_cause` | Underlying systemic flaw (the WHY behind the trigger) | "Sort happens client-side in a watch body without stable comparator; pagination request re-orders without preserving cursor" |
| `contributing_factors` | ≤3 systemic gaps that enabled the failure (process / tooling / docs / test-coverage) | "1. No e2e test covers paginate-while-mutating. 2. Concern doc lacks sort-stability requirement. 3. Component uses inline .sort() vs shared helper." |

## Hypothesis Enumeration

[MANDATORY ≥2 entries per Findings §2. Single-hypothesis output is a verify-error.]

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| [cause A] | [one-line falsifier] | yes / no |
| [cause B] | [one-line falsifier] | yes / no |

## Recommended Verify Step

[Runtime probe to run BEFORE committing to fix. Skip if Root Cause Hypothesis confidence = Confirmed. Adopted from Cursor Debug Mode discipline (source: <https://cursor.com/blog/debug-mode>) — discriminator-naming turns the probe from suggestion into falsifiable gate.]

**MANDATORY three sub-fields when this section emits**:

| Sub-field | Captures | Example |
|---|---|---|
| `probe` | Specific log/instrumentation to add | "Add `console.log('sort-input', items.map(i=>i.id))` at `AlertResolverChoices.vue:201`; add `console.log('sort-output', sorted.map(i=>i.id))` at `:204`" |
| `reproduction` | Exact user action that triggers the symptom | "Open Admin > Alerts; sort by name; create new alert in another tab; switch back" |
| `discriminator` | Falsifiable mapping: "if logs show X → H_n confirmed; if Y → H_m confirmed" — names which hypothesis each observation supports | "If `sort-input` IDs are randomized → H1 (race) confirmed; if `sort-input` is ordered but `sort-output` is not → H2 (unstable comparator); if both ordered identically → H3 (rendering issue, not sort)" |

Helper `set-verify-step` enforces all 3 sub-fields populated when section emits; non-zero exit on partial.

## Approaches (HOW to change)

### Option A: [Name]
- **Description**: [1-2 sentences]
- **Addresses hypothesis**: [A | A+B | all]
- **Does NOT cover**: [hypothesis names this fix would miss]
- **Pros / Cons / Complexity**: [list / list / Low|Med|High]

### Option B: [Name]
- (same shape)

**Recommended approach**: [Option X] — [rationale, including acknowledged uncertainty for non-covered hypotheses]

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| [rule reference] | [how it constrains or enables the approach] |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low / Med / High | [estimated diff scope] |
| Risk | Low / Med / High | [what could regress] |
| Verify cost | Low / Med / High | [probe + test effort] |

## Open Uncertainties

[NEEDS CLARIFICATION markers serialized from SymptomMemo.gaps. Section omitted if no gaps.]

## Next Step

[Verdict-aware recommendation. Adapts copy to Mode.]
```

### Verdict copy (mode-adaptive)

Helper enforces verdict values based on `Mode`:

| Mode | Allowed verdict values |
|---|---|
| Bug | `Root cause confirmed` / `Root cause hypothesis (needs repro)` / `Multiple plausible causes` |
| Enhancement | `Feasible` / `Feasible with caveats` / `Not Recommended` |

`verify` enforces verdict ∈ allowed-set-for-mode; non-zero exit on mismatch.

### Next-step text section (closes Open question §1 + §5)

Research document keeps own shape (not /specify template, not /discover template). When verdict allows proceeding, helper renders a "Next step" section at the bottom of the saved md — pure text for user to copy manually into a new `/specify` session. No automated handoff.

```
## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "[1-2 sentence refined description from symptom + desired]"

Research reference: research/YYYY-MM-DD-<topic-slug>.md
Key facts:
- Mode: [Bug | Enhancement]
- Symptom: [from SymptomMemo.symptom]
- Desired: [from SymptomMemo.desired]
- Recommended approach: [Option name]
- Hypothesis addressed: [list]
- Hypotheses NOT covered: [list]
- Open uncertainties: [count] (see research doc §Open Uncertainties)
~~~
```

Section omitted when verdict = `Not Recommended` or `Multiple plausible causes` (verify probe required first).

## Phase 3: Save + recommend

After Phase 2 report rendered to console:

1. **Ask to save**: AskUserQuestion "Save this research to a file?"
   - If yes → save rendered report to `research/YYYY-MM-DD-<topic-slug>.md`; create `research/` dir if missing; append `-2`/`-3`/... on filename collision.
   - If no → research stays in console only.
2. **Render next-step recommendation** verbatim (per `feedback_verbatim_echo_directive`).

## Findings to encode (locked discoveries to bake into the redesign)

### 1. CBM discovery chain — `search_graph` THEN `search_code` fallback

**Rule**: When CBM `search_graph` returns 0 hits for an expected behavior (sort logic, filter, validation, etc.), do NOT declare "absent" yet. Chain: `search_graph` (named fns/classes) → if 0 hits → `search_code` (text/regex over indexed files) → only declare absent if BOTH return nothing.

**Why**: Empirical 2026-05-08 testForge20 alert-sort research. CBM `search_graph` for `.*sort.*` patterns returned 0 hits across the alert resolver pipeline. The orchestrator declared "alphabetical sort missing entirely." Wrong — sort EXISTED inline at `AlertResolverChoices.vue:203` as a `.sort()` call inside a Vue `watch` body. CBM's tree-sitter graph indexes only callable named symbols (top-level functions, methods, classes); inline expressions, computed refs, watch bodies, and ad-hoc `.sort()`/`.filter()`/`.map()` calls are invisible to graph queries. `search_code` (text/regex) would have found `.sort(` immediately and surfaced the right line.

The same gap applies to React hooks, Vue computed/watch, Svelte reactive blocks, any framework where logic lives in reactive bodies rather than named functions. Tree-sitter graph indexers don't promote inline calls to graph nodes.

**How to encode in /research spec**:
- Discovery protocol step 1: CBM `agentic_context "<topic>"` (synthesized bundle, when LLM mode enabled).
- Step 2: CBM `search_graph` for named symbols (high-signal first).
- Step 3: **MANDATORY** if step 2 returns 0 hits for an expected behavior — chain to `search_code` with the literal token (`.sort(`, `.filter(`, `.localeCompare(`, etc.) over the suspected package's files.
- Step 4: only after both return nothing, declare "truly absent" + escalate to source `Read`.
- Confidence calibration: 0 hits at search_graph alone = "no NAMED implementation"; 0 hits at search_code = "truly absent". Spec must NOT conflate these.
- Inline-call-site bugs (sort/filter/comparison expressions buried in framework reactive blocks) are common in Vue/React UI code. Default to search_code as the second step, not source `Read`.

Memory cross-ref: `feedback_cbm_discovery_chain_search_graph_then_code.md`.

### 2. Hypothesis-enumeration + diagnose-first discipline

**Rule**: When a symptom has multiple plausible causes (provide/inject mismatches, async-timing races, vendor microfrontend bundles, framework lifecycle gaps, etc.), enumerate the FULL hypothesis set BEFORE proposing fixes. For each plausible cause that can't be falsified from static analysis alone, mandate a runtime-verification step (e.g., `app.config.warnHandler` capture, console-log probe, breakpoint dump) before committing to a fix path.

**Why**: Empirical 2026-05-10 comparison on testForge20 `[Vue warn]: injection "notificationsBLoC" not found` ticket. The docs+CBM-driven investigation reached the same root-cause GENRE as the main-branch `/research` flow (provide/inject mismatch on vendor inject sites) but stopped at the FIRST plausible theory ("Pinia store factory context breaks inject"). The main-branch flow enumerated 4 candidate causes (vendor suffixed-key mismatch, teleport-to-non-Vue-tree, plugin install-time setup, vendor module-load side-effect) and recommended a `app.config.warnHandler` capture to identify the actual emitter component before patching. The four-hypothesis breadth mattered because the suffixed-key vendor pattern (`notificationsBLoC-${id}` in `chunk-BZDCDJU3.js:47094`) would have made a host-side `app.provide('notificationsBLoC', ...)` fix a partial fix only — not visible from a single-hypothesis path.

The single-hypothesis failure mode is hard to detect during the investigation itself — the first plausible theory feels sufficient. Discipline must enforce enumeration as a step, not leave it to judgment.

**How to encode in /research spec**:
- Discovery protocol after the search-chain (§1): MANDATORY hypothesis-enumeration step. Output shape: bullet list of N≥2 candidate causes for the symptom, each with a one-line "what would falsify this" probe.
- For each hypothesis whose falsification probe needs runtime data (cannot be answered from static analysis): MANDATORY runtime-verification recommendation in the report. Examples: `app.config.warnHandler` capture for Vue warnings, network-tab probe for HTTP-shaped issues, breakpoint dump for timing/lifecycle issues.
- Output schema gains a `hypotheses` field (array of `{cause, falsifier}`) and a `verify_step` field (the recommended runtime probe). Helper enforces non-empty hypotheses array (≥2 entries) for symptom-driven research; freezes if LLM provides only 1.
- The fix recommendation MUST cite which hypothesis it addresses + which others it would NOT cover. Forces explicit acknowledgement of remaining uncertainty.

**Anti-pattern this prevents**: confident "root cause = X, fix = Y" output when only X was enumerated and Y is partial because non-enumerated causes also contribute. Hypothesis-enumeration surfaces the gaps before they become regressions.

**Cross-CBM-discovery interaction**: this rule layers on top of §1. CBM search-chain finds candidate code surfaces; hypothesis-enumeration explains WHY each surface might be the root cause. Two-rule combo: §1 finds WHERE, §2 explains WHY (and which other WHYs are still in play).

## Constraints (apply when authoring redesign)

- Zero-escape-hatch policy: no "OR / if / except / unless / use-judgment" clauses in the discovery protocol. Each step has a single mandated action.
- Helper-owns-shape: research output schema owned by `research_helper.py`, not by LLM prose (per `feedback_helper_owns_shape_principle`). Helper owns structure; LLM composes values via setters.
- LLM-first density: spec body is LLM instructions, not human-onboarding wiki. No forward refs to future phases or files that don't exist yet (per `feedback_llm_instructions_self_contained`).
- Spec body is self-contained — scoped to `/research` execution only; no forward refs to `/specify` or downstream phases in spec prose. Forward-handoff lives in OUTPUT document's "Next Step" section, not in spec body.
- Triple-agent verification: any /research spec edit goes through **instruction-author** (writer) → **instruction-reviewer** (intra-file logical flow + cross-reference consistency + sentence-level hallucination risk) → **claude-code-guide** (Claude Code authoring conventions) before commit. Iterative apply-verify loop until both reviewers clean (per `feedback_iterative_review_loop_preferred`). Per `feedback_dual_agent_verify_command_statements`.
- No CSE / dev-version refs in shipped spec; production-ready prose only.
- No real project names in examples (per `feedback_no_real_project_names`).
- Test-first for helper functions: every function in `research_helper.py` gets a test written + run in the same turn (per `feedback_test_first_python_helpers`); round-trip via real producer for parsers.
- No `model:` override in `src/commands/research/main.md` frontmatter (per `feedback_avoid_command_model_override`). Inherit session model.
- Verbatim echo directive when spec instructs LLM to display helper output (coverage summary, hypothesis list, render output): use the wording "copy VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)" (per `feedback_verbatim_echo_directive`).
- Research document has its own shape — not a `/specify` template, not a `/discover` report. Owns: Symptom, Codebase Findings (WHERE), Root Cause Hypothesis (WHY), Hypothesis Enumeration, Verify Step, Approaches (HOW), Constitution Constraints, Complexity, Open Uncertainties, Next Step. Distinct identity preserved through render.

## Open questions

1. ~~Does /research save artefacts (e.g., `research/YYYY-MM-DD-topic.md`)?~~ **Closed 2026-05-11** — yes, ask-to-save at Phase 3; save to `research/YYYY-MM-DD-<topic-slug>.md` on confirm.
2. ~~Should /research consult `constitution.md` proactively?~~ **Closed 2026-05-11** — yes. Hard-gate prerequisites guarantee `constitution.md` exists; no conditional path needed.
3. ~~Should /research delegate to a research subagent or stay orchestrator-direct?~~ **Closed 2026-05-11** — hybrid dispatch. See "Decisions added 2026-05-11" §3.
4. ~~Cost-gate prose~~ **Closed 2026-05-11** — yes; surface estimated CBM call count + token cost before Phase 1 dispatch. Mirrors `/generate-docs` Phase 1 cost gate. Encoded in Phase 1 section above.
5. ~~Output shape: free-form vs structured?~~ **Closed 2026-05-11** — structured. Helper-owns-shape per `feedback_helper_owns_shape_principle`. Full template in "Phase 2 report shape (target)" section above.

## Decisions added 2026-05-11 (chat with user)

### 1. Scope boundary — /research = existing code only

/research handles bug fixes + enhancements (both = delta on existing code). Greenfield features split to new `/discover` command (see `DISCOVER-PLAN.md`).

Rationale: bug fix and enhancement share investigation primitives (locate, trace, root cause, options to bridge) — same report shape with neutral "Root Cause Hypothesis" framing serves both. Greenfield has no existing-code surface to investigate; needs design-exploration lens (prior art, integration surface, design sketches, build-vs-buy). Forcing both under one command repeats the existing-code bias this redesign is trying to fix.

### 2. Report shape — bug-neutral, no mode flag

Single report shape covers bug + enhancement. Mode detection via signal-based copy, not separate sections:

- "Root Cause Hypothesis" section serves both (bugs → cause of broken behavior; enhancements → cause of current limitation).
- Verdict copy adapts on signal. Bug-language symptoms → "Root cause confirmed / Root cause hypothesis (needs repro) / Multiple plausible causes". Idea-language → current "Feasible / Feasible with caveats / Not Recommended".
- Spec usage block must include bug-flavored examples (currently zero — reads as enhancement-only). Add e.g. `/research "items not sorted in admin products view"` and `/research "auth fails on Safari 17 after token refresh"`.
- Hypothesis-enumeration discipline (Findings §2) still mandatory regardless of bug-vs-enhancement framing.

### 3. Agent ownership — hybrid dispatch, not full agent-owned

/research stays orchestrator-driven for user dialogue + report rendering + AskUserQuestion. Dispatch framework-owned `research-investigator` subagent (`src/agents/research-investigator.md`) for the heavy CBM/code-exploration phase only. Framework-internal — no external plugin dependency.

Rationale (per `feedback_avoid_subagents_for_sequential_identical_workflows`): apply 3-benefit test (parallelism / tool isolation / context-budget). /research as whole has no parallelism + weak tool isolation. Only context-budget partially earns dispatch (long CBM traces pollute main context). Hybrid captures context savings without losing user-interaction quality. AskUserQuestion via subagents is fragile across agent types; keeping it on orchestrator avoids brief-staleness.

## Work order

- **Step 1**: read current `src/_pending/commands/research.md` end-to-end + map sections to new Phase 0-3 structure.
- **Step 2**: draft schemas (Python dataclasses / pydantic) for `research_helper.py`:
  - Phase 0 `SymptomMemo` schema — 6 rubric dimensions (`symptom`, `affected_area`, `repro_or_current`, `desired`, `scope`, `unchanged_behavior`) + per-dimension state enum (`Clear | Partial | Missing`) + per-dimension turn counts. Plus: `mode: "bug" | "enhancement"` (derived from symptom signals), `gaps: list[{dimension: str, description: str}]`, `override_recorded: bool`, `conflicts: list[Conflict]` (misalignment detection log). `Conflict` shape: `{type: "direct" | "drift" | "refinement" | "mode-flip", dimensions: list[str], description: str, resolution: "blocked-pending-user" | "user-chose-<X>" | "logged-no-action" | None}`. State persisted to `.devforge/research-state.json` (mirrors /constitute pattern). `unchanged_behavior` adopted from Kiro Bugfix triplet (source: <https://kiro.dev/docs/specs/>) — separates regression scope from investigation scope.
  - Phase 1 `Finding` schema — `{surface: str, file_line: str, relevance: str}` + `Hypothesis` schema — `{cause: str, falsifier: str, runtime_probe_needed: bool}`. Hypothesis array enforces minimum 2 entries.
  - Phase 2 `ResearchReport` schema — sections per "Phase 2 report shape" above. Closed enums for `verdict` (mode-aware allowed values), `confidence`, `complexity_rating`. Plus structured root-cause fields (bug mode + confidence ≥ Hypothesis): `trigger: str`, `root_cause_systemic: str`, `contributing_factors: list[str]` (max 3) — adopted from Google SRE postmortem template (source: <https://sre.google/workbook/postmortem-analysis/>). Plus structured verify-step fields: `verify_probe: str`, `verify_reproduction: str`, `verify_discriminator: str` — adopted from Cursor Debug Mode (source: <https://cursor.com/blog/debug-mode>). State persisted to `.devforge/research-report.json` while in-flight; rendered to `research/YYYY-MM-DD-<topic-slug>.md` on Phase 3 save.
- **Step 3**: implement helper subcommands. Test-first per `feedback_test_first_python_helpers`. Subcommands:
  - Prerequisites: `preflight` (hard-gate check for `.devforge/manifest.json` + `docs/architecture.md` + `.devforge/project-config.json` + `constitution.md`; non-zero exit + message on missing).
  - Phase 0: `read-state`, `set-symptom`, `set-affected-area`, `set-repro-or-current`, `set-desired`, `set-scope`, `set-unchanged-behavior`, `detect-mode` (derives bug-vs-enhancement from symptom tokens), `record-gap`, `check-conflicts` (runs token-overlap rules after each setter; returns list of detected direct contradictions; orchestrator wraps with LLM-side drift check), `record-conflict-resolution` (logs user's resolution choice, rewrites loser dimension on direct contradiction; handles mode-flip by rerunning `detect-mode` with override), `symptom-coverage` (returns `Clear`/`Partial`/`Missing` per dimension + coverage table + conflicts log summary), `symptom-finalize` (exit non-zero if `Partial`/`Missing` without `override_recorded` OR if any `conflicts.resolution == "blocked-pending-user"`).
  - Phase 1: `record-finding` (codebase finding), `record-hypothesis` (enforces ≥2 before exit), `set-root-cause-hypothesis`, `set-confidence`, `set-trigger` (bug-mode only; the immediate event), `set-root-cause-systemic` (bug-mode only; underlying systemic flaw), `record-contributing-factor` (bug-mode only; max 3), `set-verify-step` (enforces 3 sub-fields `probe`, `reproduction`, `discriminator` populated; non-zero exit on partial). All consumed by investigation subagent.
  - Phase 2: `set-approach`, `set-recommended-approach` (enforces citation of which hypotheses it addresses + which it does NOT cover; ADDITIONALLY enforces "must not violate `unchanged_behavior`" cross-check), `set-constitution-constraints`, `set-complexity`, `set-verdict` (verifies mode-aware enum), `set-next-step-text` (composes the copy-pasteable `/specify` prompt section from SymptomMemo + ResearchReport state; only emits when verdict allows proceeding; pure text generation, no automation), `render` (concatenates all sections including next-step text at the bottom). `verify` enforces: ≥2 hypotheses, recommended approach cites hypotheses, recommended approach respects `unchanged_behavior`, verdict ∈ mode-allowed-set, structured root-cause fields populated when bug-mode + confidence ≥ Hypothesis, verify-step 3 sub-fields populated when section emits, all required sections populated.
  - Cross-phase: `summary`.
  - **Test fixtures**: author TWO fixtures covering both modes:
    - `tests/lib/fixtures/research-sample-bug-report.md` — bug-mode happy-path scenario (with `unchanged_behavior` + structured root cause + verify-step 3 sub-fields). Generic placeholders per `feedback_no_real_project_names`.
    - `tests/lib/fixtures/research-sample-enhancement-report.md` — enhancement-mode happy-path scenario (no structured root cause sub-fields; mode-aware verdict copy). Generic placeholders.
    Round-trip discipline (per `feedback_test_first_python_helpers`): build via real helper setter calls → `render` → diff against fixture. Fixtures are canonical expected-shape artifacts for `render()` regression tests. Skeleton lives in helper code (inline render, mirrors /constitute); fixtures are complete examples, not skeletons.
- **Step 4a**: author spec at `src/commands/research/main.md` + reference docs (if any). Promote out of `src/_pending/commands/research.md`. Spec body covers all 4 phases with explicit transition gates (Phase 0 → Phase 1 requires `symptom-finalize` exit code 0).
- **Step 4b**: author framework-owned `src/agents/research-investigator.md`. Read-only code locator with CBM chain discipline (per Findings §1) + hypothesis enumeration discipline (per Findings §2). Pattern may be adapted from `cavecrew-investigator` plugin agent as a reference, but the file ships inside the framework — no external dependency. Agent definition is emitted via `scripts/emitters/claude.py` to `.claude/agents/research-investigator.md` in target project. Tools allowed: Read, Grep, Glob, Bash + all `mcp__codebase-memory-mcp__*` tools. NO write/edit tools.
- **Step 5**: triple-agent verify in iterative apply-verify loop (per `feedback_iterative_review_loop_preferred`):
  1. `instruction-author` drafts/edits spec.
  2. `instruction-reviewer` + `claude-code-guide` review in parallel (single message, two Agent tool calls).
  3. If either reviewer returns findings → loop back to step 1 with fixes briefed to author. Repeat until both reviewers clean.
  4. Present clean draft to user for approval.
  5. User approves → proceed to Step 6.
- **Step 6**: update emitter `scripts/emitters/claude.py` `_PROMOTED` list for `research` command AND ensure `research-investigator` agent is in the emitter's agents list (per `feedback_emitter_promoted_cross_check`).
- **Step 7**: cross-update README, DEVELOPMENT-STATUS, CLAUDE.template, storage-rules (per `feedback_release_docs`).
- **Step 8**: empirical test on testForge20 with TWO ticket types:
  - Bug example: alert-sort ticket from 2026-05-08 session (see Findings §1) — validates CBM chain catches inline `.sort()`.
  - Enhancement example: "make export faster on large datasets" — validates same shape serves enhancement mode.
  Validate hard-gate, Phase 0 dialogue converges, Phase 1 subagent uses CBM by name + chains to `search_code` when graph returns 0, hypothesis enumeration enforces ≥2, mode-aware verdict copy adapts, handoff section renders correctly per verdict.
- **Step 9**: ship to develop-2.0-init / main with CHANGELOG entry.

## Verify criteria

- **Step 3**: 100% helper subcommand tests pass; helper round-trips state via JSON. Coverage check on real input shapes (per `feedback_test_first_python_helpers`). Specifics:
  - `symptom-coverage` returns accurate state after each setter call.
  - Bounded-turn cap (2 follow-ups/dimension) enforced; over-cap returns `Partial`, no crash.
  - `symptom-finalize` exit code 0 only when all `Clear` OR user explicitly accepted gaps (helper records override).
  - `detect-mode` correctly classifies seeded symptoms (bug-language → "bug", idea-language → "enhancement"; mixed-signal → ask user via AskUserQuestion).
  - `record-hypothesis` enforces minimum 2 entries before any `set-recommended-approach` accepts; verify exits non-zero if approach landed with single-hypothesis state.
  - `set-verdict` rejects values outside mode-allowed-set.
- **Step 4a**: spec passes intra-file consistency check (instruction-author). Phase transitions documented with helper gate references. No forward refs to `/specify` or downstream in spec body.
- **Step 4b**: `src/agents/research-investigator.md` ships in framework (not external plugin); triple-agent verify passes; agent file emits to target `.claude/agents/research-investigator.md` via install.sh; agent definition has read-only tool list (no Write/Edit/NotebookEdit).
- **Step 5**: both reviewer agents return clean across iterative loop; user approves final draft.
- **Step 6**: `./install.sh` on fresh testForge20 promotes `/research` into `.claude/commands/`.
- **Step 8**: empirical run produces report with all sections populated; output is actionable + matches investigation lens (not feasibility-check repurposed). Validate:
  - **Hard-gate prerequisites enforced**: induce missing `docs/architecture.md`, confirm `preflight` exits non-zero with the required setup-chain message; restore and confirm exits clean.
  - Phase 0 dialogue converges within bounded turns on a bug input AND an enhancement input.
  - Mode signal detected correctly on both; verdict copy adapts.
  - Phase 1 subagent receives narrowed brief derived from SymptomMemo (inspect dispatch brief; raw user input must NOT appear as subagent query).
  - Kill-and-resume: kill `/research` mid-Phase-0, restart, confirm dialogue resumes from saved state.
  - **CBM discovery chain fires correctly** (Findings §1): induce a scenario where `search_graph` returns 0 hits but `search_code` finds the inline `.sort()`; confirm subagent transcript chains correctly + reports "no NAMED implementation; found inline at file:line".
  - **Hypothesis enumeration enforces ≥2** (Findings §2): induce a single-hypothesis Phase 1 output; confirm `verify` exits non-zero.
  - **Recommended approach cites hypotheses**: induce a fix recommendation that doesn't cite which hypotheses it addresses; confirm `verify` exits non-zero.
  - **Recommended approach respects `unchanged_behavior`**: induce a fix that would regress a feature listed in `unchanged_behavior`; confirm `verify` exits non-zero with citation of the violated regression scope.
  - **Structured root-cause fields populated** when `mode == "bug"` AND `confidence ∈ {Confirmed, Hypothesis}`: trigger + root_cause_systemic + ≤3 contributing_factors. Confirm omitted on `Speculative` confidence or enhancement mode.
  - **Verify-step section populated with 3 sub-fields** when any hypothesis has `runtime_probe_needed=true`: probe + reproduction + discriminator. Confirm `verify` exits non-zero when any sub-field missing.
  - **Misalignment detection fires**:
    - **Direct contradiction**: set `desired` = "alphabetical A→Z" then `unchanged_behavior` = "current numeric order must remain"; confirm helper `check-conflicts` flags it; confirm orchestrator blocks via AskUserQuestion; confirm `symptom-finalize` exits non-zero until user resolves.
    - **Drift**: set `affected_area` = "one component" then evidence in Phase 1 shows feature-wide touchpoints; confirm LLM-side check classifies as `drift`; confirm logged to `conflicts` without blocking.
    - **Mode flip**: set `symptom` as bug-shape, later set `desired` as enhancement-shape; confirm helper detects mode-flip; confirm `detect-mode` reruns with user confirmation.
    - **Refinement**: set `affected_area` = "Admin > Products" then later "Admin > Products + Admin > Orders" as superset; confirm quiet rewrite + log with `type=refinement` and `resolution=logged-no-action`.
  - **No silent overwrites**: any later answer that affects a confirmed dimension is logged in `conflicts` regardless of classification.
  - **Next-step text section rendered** at bottom of saved md when verdict ∈ proceeding-set; section contains copy-pasteable `/specify "..."` prompt + key facts + link back to saved research doc. Omitted when verdict = `Not Recommended` or `Multiple plausible causes`. No orchestrator-driven automation — text is for user manual copy.
  - **Preflight gate fires** before Phase 1 dispatch; skipped only when `.devforge/.preflight-stamp` is fresher than 60s.
  - **`.devforge/cbm-usage.log` records** Phase 1 CBM invocations (telemetry from `cbm-mcp-marker` hook).
  - **Cost gate fires**: orchestrator surfaces estimated CBM call count + token cost before Phase 1 dispatch; user confirms.

## When resuming work

1. Read this file in full.
2. Read `feedback_cbm_discovery_chain_search_graph_then_code.md` (memory) for Findings §1 context.
3. Read `DISCOVER-PLAN.md` as the parallel-command reference (same Phase 0/1/2/3 pattern, helper-owns-shape, hard gate, triple-agent verify). `/research` mirrors many `/discover` mechanics with /research-specific schema (5 dims vs 8, ResearchReport vs DiscoveryReport).
4. Read `/constitute` helper as the reference helper-owns-shape shape: `src/devforge/lib/constitute_helper.py` + `src/commands/constitute/main.md`.
5. Read framework-owned `src/agents/research-investigator.md` once authored. If not yet authored, reference `cavecrew-investigator` agent definition as a pattern source (one-time read; the framework version is the authoritative copy thereafter).
6. Check current state of `src/_pending/commands/research.md` + emitter `_PROMOTED` list.
7. Run preflight on testForge20 to confirm CBM index still live: `cd /Users/mykolakudlyk/Projects/testForge20 && ./.devforge/lib/generate_docs_helper preflight --skip-vue-extract --skip-index | jq '.concern_counts'`.
8. Pick up at the next unaddressed Work order step.
