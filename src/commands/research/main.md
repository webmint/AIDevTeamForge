---
name: research
description: Investigate a bug or enhancement against the codebase; produce a structured research report grounded in CBM + docs.
disable-model-invocation: true
---

# /research — Codebase Research

`/research` is repeatable per ticket. It clarifies a vague bug or enhancement input into a structured symptom memo, runs an orchestrator-direct investigation that consults the CBM graph + `docs/` corpus, composes a research report with mandatory ≥2 hypothesis enumeration, and saves the rendered report to `research/YYYY-MM-DD-<topic-slug>.md`. State + render shape are owned by `.devforge/lib/research_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) has completed before any investigation fires.

Usage: `/research "<topic>"` (e.g. `/research "items not sorted in admin products view"` or `/research "make export faster on large datasets"`).

## Outputs of this phase

- `.devforge/research-state.json` — SymptomMemo (Phase 1 state). Owned + shaped by the helper; initialized at Phase 0.3 (`reset-memo`, `set-topic`), then mutated via Phase-1 setter subcommands.
- `.devforge/research-report.json` — ResearchReport (Phase 2 + 3 state). Owned + shaped by the helper; mutated only via Phase-2/3 setter subcommands.
- `<install_root>/research/YYYY-MM-DD-<topic-slug>.md` — rendered report. Helper's `render` writes to stdout; orchestrator saves it via the Phase 4 save prompt. Filename slug is auto-derived by the helper from the topic.

## Phase 0 — Pre-flight gate

Two preflight checks run in order. Both must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/research_helper preflight
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/init-forge`)
- `docs/architecture.md` (produced by `/generate-docs`)
- `.devforge/configure.yaml` (produced by `/configure`)
- `constitution.md` (produced by `/constitute`)

Exit 0 → all present + non-empty; proceed. Exit 2 → at least one missing or empty; helper emits a `BLOCKED:` message on stderr naming each missing artefact + producer command. On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/research`.

### Phase 0.2 — CBM index refresh

```bash
.devforge/lib/generate_docs_helper preflight
```

This refreshes the CBM index stamp so Phase 2 graph queries see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. Helper non-zero exit: copy stderr VERBATIM and end the turn; user re-runs `/generate-docs` or `index_repository` and re-invokes `/research`.

### Phase 0.3 — Topic argument

If `$ARGUMENTS` is non-empty, treat it as the topic. If empty, ask the user via AskUserQuestion: `"What's the topic? (bug or enhancement, one sentence)"` — single-line question text, free-text answer. Then reset helper state and stamp topic + date:

```bash
.devforge/lib/research_helper reset-memo
.devforge/lib/research_helper reset-report
.devforge/lib/research_helper set-topic --value "<topic>"
.devforge/lib/research_helper set-date --value $(date -u +%Y-%m-%d)
```

`reset-memo` + `reset-report` write fresh-defaults state. `set-topic` auto-derives `topic_slug` for the eventual filename. `set-date` enforces `YYYY-MM-DD`.

Fresh-every-run: `reset-memo` + `reset-report` ALWAYS run at Phase 0.3, unconditionally. Any prior `.devforge/research-state.json` + `.devforge/research-report.json` are overwritten with fresh defaults. `/research` does not resume mid-flight prior runs — every invocation starts clean. If the user killed a prior run mid-investigation, that work is lost; re-answer the rubric from scratch.

## Phase 1 — Symptom clarification (rubric Q&A)

Convert the vague topic into a structured symptom memo across 6 dimensions. The helper owns the rubric; the orchestrator drives one dimension at a time, picking the highest-uncertainty dimension to ask next.

**MANDATORY: never skip the rubric.** Even when `$ARGUMENTS` contains a pre-filled ticket that appears to address all 6 dimensions, ask each dimension question separately and wait for the user's answer in its own turn. Pre-filled input is a STARTING POINT for the `symptom` dimension only — never a license to auto-fill the remaining 5 in one pass. User commitment is per-dimension; that is the forcing function this phase exists for. The rubric is not optional, not advisory, not skippable based on input completeness.

**MANDATORY: never fabricate a user mode.** Do not write — in any user-facing message, internal narration, or tool-call rationale — phrases like "user requested no-questions mode", "user wants free-form", "user said skip the rubric", "no-prompt mode", or any equivalent. No such mode exists. No such request is in scope. If you find yourself about to justify a shortcut by attributing intent to the user, STOP — you are rationalizing a fabrication. Run the rubric.

### Rubric dimensions

| Dimension | Captures | Bug-mode example | Enhancement-mode example |
|---|---|---|---|
| `symptom` | What's wrong (bug) or what needs to change (enhancement) | "Items not sorted in admin products view" | "Export is slow on large datasets" |
| `affected_area` | Which UI / module / feature surface | "Admin > Products > List page" | "ExportService background job" |
| `repro_or_current` | Repro steps (bug) or current behavior (enhancement) | "Open list with 50+ items, scroll" | "5 min runtime on 100K rows; synchronous" |
| `desired` | Expected behavior (bug) or target behavior (enhancement) | "Alphabetical by name, A→Z" | "Under 30s OR async with progress" |
| `scope` | One place / feature-wide / cross-cutting | "one place" | "feature-wide" |
| `unchanged_behavior` | What must NOT regress | "Filter + pagination on same page must keep working" | "Existing small-dataset exports must stay synchronous + complete in ≤2s" |

Per-dimension state enum: `Clear` / `Partial` / `Missing` (default `Missing`). Turn cap: 2 follow-ups per dimension before the helper auto-marks `Partial`.

### Pre-rubric docs scan (orchestrator-only)

Before asking the first dimension question, read the project docs corpus to seed `affected_area` candidates:

- `docs/architecture.md` — project-tier architecture
- `docs/glossary.md` — term grounding

Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`:

1. `get_architecture` (CBM) — pulls the rendered architecture md from the graph.
2. `search_graph` with `label="File"` + `name_pattern=<regex on file_path>` — locate candidate package roots that match topic tokens. The argument name is `name_pattern`, NOT `file_pattern`; the wrong name returns silent 0 hits.

Surface 2-3 candidate packages or modules in the next `affected_area` prompt as suggestions.

### Per-dimension question protocol

For each of the 6 dimensions, in highest-uncertainty-first order:

1. **Ask one question.**
   - For `scope`: closed-choice. Use AskUserQuestion with options `["one place", "feature-wide", "cross-cutting"]`. Question text is single-line.
   - For the other five (`symptom`, `affected_area`, `repro_or_current`, `desired`, `unchanged_behavior`): plain prose prompt — paragraph context (if needed) printed as prose ABOVE the question; the question itself is a single line ending with `?`. Wait for free-text reply. Do NOT use AskUserQuestion for these (the answer is open-ended free text).

2. **Persist the answer.** Call the dimension's setter:

   ```bash
   .devforge/lib/research_helper set-<dimension> \
       --value "<user's answer>" \
       --state <Clear|Partial|Missing>
   ```

   Subcommand names: `set-symptom`, `set-affected-area`, `set-repro-or-current`, `set-desired`, `set-scope` **(see narrow-framing gate below — requires `--evidence` when value is `"one place"`)**, `set-unchanged-behavior`. Default `--state` is `Clear` — pass `--state Partial` when the answer leaves a gap. For follow-up turns on the same dimension, add `--increment-turn` so the helper tracks the bounded-turn cap.

   **`set-scope` evidence requirement (narrow-framing gate).** When the user picks `"one place"` from the closed-choice options, `set-scope` requires an additional `--evidence` flag carrying a `file:line` citation that proves the symptom is localized to that single site:

   ```bash
   .devforge/lib/research_helper set-scope \
       --value "one place" \
       --evidence "<path:line of the single symptom site>" \
       --state Clear
   ```

   `--evidence` is REQUIRED whenever `--value` normalizes to `"one place"` (case-insensitive, whitespace-stripped). It must be a real `file:line` citation in `path/to/file.ext:NNN` form — the `(none)` sentinel is rejected because narrow framing demands a concrete locality citation. Without `--evidence`, the helper exits with code 2 and stderr `set-scope: --evidence is required when --value == 'one place'.` plus the rationale (narrowing scope gates Phase 2 exploration depth, so the LLM must commit to a verifiable locality before downstream phases run). When `--evidence "(none)"` is passed, the helper also exits with code 2 and stderr `set-scope: --evidence cannot be '(none)' when --value == 'one place'; narrow framing requires a concrete file:line citation.` The citation should typically be the symptom site identified from the Phase 0 pre-rubric docs scan or from `$ARGUMENTS` if the user supplied a specific file in their topic. For `--value "feature-wide"` or `--value "cross-cutting"`, `--evidence` is not required (broader framings are the safer defaults; narrowing is the risky direction).

   **Recovery on rejection.** If the helper rejects the call (exit 2), copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Then choose a recovery path based on which rejection fired:
   - Missing or empty `--evidence` → (a) ask the user one follow-up to supply the locality citation if their original answer didn't include a file path, OR (b) re-prompt with the original `AskUserQuestion` options and let them pick a broader framing.
   - `--evidence "(none)"` rejected → only path (b) applies: the user/LLM deliberately passed the sentinel, so re-prompting for a real `file:line` citation OR a broader framing is the only forward path; do not retry with `(none)`.
   Do not retry the setter call without a citation — the gate will reject again.

3. **Run helper-side conflict check.**

   ```bash
   .devforge/lib/research_helper check-conflicts
   ```

   Stdout is a JSON array of detected direct contradictions (token-overlap rule). If the array is non-empty: block via AskUserQuestion `"Which to keep — the new answer or the prior one?"` with the two competing values as options. Then record the resolution:

   ```bash
   .devforge/lib/research_helper record-conflict-resolution \
       --index <0-based index from check-conflicts output> \
       --resolution "user-chose-<new|prior>" \
       --rewrite-dimension <dimension_name>  # underscore form, e.g. affected_area
   ```

   `--rewrite-dimension` clears the loser's value so the user must re-answer it on the next pass.

4. **Run LLM-side drift check.** Compare the just-set answer against the previously-confirmed dimensions held in memory from prior turns. Classify as one of:
   - `direct` — already handled by the helper in step 3; skip here.
   - `drift` — new answer expands scope beyond an earlier confirmed boundary (e.g., `affected_area` was `"one component"` earlier, but the new answer indicates feature-wide). Do not block. Hold the observation in memory; surface it to the user at the next natural pause (after the coverage echo or before mode detection) as a plain-prose note: `"Heads up — your <new dimension> answer suggests <observed drift>. Adjust <affected dimension> or continue?"` Wait for the user's reply before advancing.
   - `refinement` — new answer is a superset of the earlier one (e.g., `"Admin > Products"` → `"Admin > Products + Admin > Orders"`). Re-call the affected dimension's setter with the superset value to overwrite (e.g., `set-affected-area --value "Admin > Products + Admin > Orders" --state Clear`). No user prompt.
   - `mode-flip` — symptom signaled bug-shape, the new answer signals enhancement-shape (or vice versa). Ask via AskUserQuestion `"Treat this as a bug or an enhancement?"` with options `["bug", "enhancement"]`, then call `detect-mode --override <choice>`.
   - `none` — no drift; advance to the next dimension.

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift, refinement, and mode-flip classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns within the same `/research` run by reading prior assistant messages in the conversation.

5. **Advance.** Pick the next highest-uncertainty dimension and return to step 1.

### Coverage check + exit

After all 6 dimensions have been asked at least once OR the user explicitly accepts gaps:

```bash
.devforge/lib/research_helper symptom-coverage
```

Stdout is JSON: `per_dimension` (map of `dim → {state, value, turns}`), `counts` (`{Clear, Partial, Missing}`), `mode`, `conflicts_open` (count of conflicts still `blocked-pending-user`). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) so the user sees per-dimension state before deciding to continue or accept gaps.

If the user wants to continue clarifying: return to the per-dimension protocol for any dimension whose state != `Clear`.

If the user accepts gaps: for each dimension with state ∈ `{Partial, Missing}`, record a gap marker, then finalize:

```bash
.devforge/lib/research_helper record-gap \
    --dimension <name> \
    --description "<one-line gap description>"

.devforge/lib/research_helper symptom-finalize --accept-gaps
```

If the user is clarifying all the way to `Clear`, finalize without the flag:

```bash
.devforge/lib/research_helper symptom-finalize
```

Exit code:
- `0` → memo accepted; advance to mode detection.
- non-zero → blocked. Stderr enumerates the reason (unresolved direct conflict OR Partial/Missing without `--accept-gaps`). Copy stderr VERBATIM, end the turn, address the cited issue on the next user reply.

### Mode detection

```bash
.devforge/lib/research_helper detect-mode
```

Stdout JSON: `{"mode": "bug" | "enhancement" | null, "source": "auto" | "override" | "ambiguous"}`. `source = "auto"` on a clear detection from symptom tokens; `source = "override"` when called with `--override`; `source = "ambiguous"` when symptom tokens are mixed-signal and no override was supplied (`mode` is `null` in that case). If `mode` is non-null: advance to Phase 2. If `mode` is null (mixed-signal symptom tokens), ask via AskUserQuestion `"Treat this as a bug or an enhancement?"` with options `["bug", "enhancement"]`, then:

```bash
.devforge/lib/research_helper detect-mode --override <user's choice>
```

### Stop discipline (mandatory)

After emitting any AskUserQuestion or free-text prompt in Phase 1, end the assistant turn. Do NOT advance to the next dimension, the next protocol step, or any helper setter call in the same turn. The user's reply opens the next turn; the next turn parses it and continues. Plain-prose prompts have no harness-level "wait for user" affordance — the LLM-level stop is the only mechanism preventing accidental auto-advance.

## Phase 2 — Investigation (orchestrator-inline)

Phase 2 runs in the main thread — NO subagent dispatch. Orchestrator-inline keeps the full session context intact, which is what the parallel-pattern sweep in Phase 2.4 needs to find sibling bug sites in the same file.

### Phase 2.1 — Cost gate

Before any CBM call, surface the estimated CBM call count + token cost based on `affected_area`. Rough rule of thumb: one-package scope ≈ 15-30 CBM calls; feature-wide ≈ 30-60 calls; cross-cutting ≈ 60-120 calls. Token cost is bounded — orchestrator-inline reuses the existing session context, no fresh subagent boot.

Ask via AskUserQuestion `"Investigation will scan roughly <N> CBM calls. Proceed?"` with options `["proceed", "cancel"]`. On `cancel`: copy a one-line note ("Investigation cancelled. Re-run /research from scratch when ready — prior state will be overwritten.") into the user-facing message and end the turn. On `proceed`: continue.

### Phase 2.2 — Read docs layer first

Read these via the CBM graph (md files are indexed; use `search_graph` with `label="File"` + `name_pattern=<regex on file_path>`, NOT `file_pattern`) before any source-code discovery:

- `docs/architecture.md`
- `docs/<affected_package>/architecture.md` (substitute `<affected_package>` from `memo.dimensions.affected_area.value`)
- `docs/<affected_package>/<closest_concern>/index.md` (closest concern derived from the affected-area phrase)
- `docs/glossary.md`

Docs ground the symptom in package + concern boundaries before code-level discovery fires.

### Phase 2.3 — CBM discovery chain (MANDATORY order)

Raw `Read` / `Grep` / `Glob` / `grep` / `find` / `cat` over source-file extensions are forbidden and will be blocked by runtime hooks. Chain:

1. **`search_graph`** — query for named symbols matching symptom tokens. Use `qn_pattern` for qualified-name regex; `name_pattern` for short-name regex; `label="File"` queries use `name_pattern` (regex on file_path), NOT `file_pattern`.
2. If `search_graph` returns 0 hits for an expected behavior → **`search_code`** — text or regex search with a literal token (e.g. `.sort(`, `.filter(`, `.localeCompare(`) over the affected package. This catches inline expressions buried inside framework reactive blocks (Vue `<script setup>`, React hooks, Svelte reactive blocks) that the graph indexer does not promote to named symbols.
3. **`trace_path`** — impact analysis on confirmed surfaces. Pick a `mode` from `calls` / `data_flow` / `cross_service`.
4. **`get_code_snippet`** — read source on the highest-confidence candidates. This is the only sanctioned source-read path; do not use raw `Read`.

Confidence calibration: 0 hits at `search_graph` alone means "no NAMED implementation"; 0 hits at `search_code` means "truly absent". Do not conflate these.

**`file:line` grounding (MANDATORY).** Every `file_path:line` you will later pass to `record-finding` MUST be copied verbatim from a `search_graph` or `search_code` result row's `file_path` + `line` fields. Never derive a line number from `get_code_snippet` output — `get_code_snippet` returns a code slice whose internal lines do NOT correspond to absolute file line numbers, and the LLM will drift by ±1 to ±N. Never reconstruct a line number from prose context. If you only have a snippet and need the line, re-run `search_code` for a literal token from the snippet to recover the authoritative `file:line` row. If that re-run returns 0 hits, widen the token (try a longer substring or a different literal from the same snippet) and retry once. If still 0 hits, fall back to the original result-row `file:line` you held before calling `get_code_snippet`, and note in `--relevance` that the line could not be re-confirmed.

### Phase 2.3b — Framing challenge (MANDATORY)

Phase 2.3 framing locks in. Without adversarial competition, Phase 2.4 / 2.4b / 2.4c inherit the chosen frame unchallenged — the LLM enumerates hypotheses *within* the chosen frame, never *across* competing frames. Phase 2.3b breaks the lock by forcing one alternative-framing commit BEFORE downstream searches run, so subsequent searches probe BOTH frames.

1. **State the PRIMARY framing** in one sentence based on Phase 2.3 evidence ("the bug is caused by X").

2. **State the strongest ALTERNATIVE framing** — a different root-cause hypothesis at the FRAMING level, not at the hypothesis level. Framing-level competition is distinct from the ≥2 hypothesis enumeration the helper enforces in Phase 2.5 — that enumeration produces hypotheses *within* one frame. Two examples to disambiguate:

   - Same frame, two hypotheses (NOT what Phase 2.3b wants): primary frame "comparator field-name typo" → H1 "primary-id vs alternate-id mismatch" / H2 "type coercion drops the match". Both H1 + H2 live inside the same comparator-typo frame.
   - Different framings (what Phase 2.3b wants): primary "id-field mismatch (presentation-layer fix)" vs runner-up "shallow walk + missing structural classifier (cross-layer fix)". Different root causes, different fix layers, different surfaces.

3. **Identify the CONCRETE FALSIFIER** — the specific evidence that would prove the alternative framing OVER the primary. Phase 2.4 / 2.4b / 2.4c searches will probe FOR this evidence.

4. **Rate `confidence_vs_primary`** as one of `lower` / `comparable` / `higher` relative to the primary framing.

5. **Record via:**

   ```bash
   .devforge/lib/research_helper record-runner-up-framing \
       --frame "<one-sentence alternative root cause>" \
       --falsifier "<concrete evidence that would confirm THIS framing over the primary>" \
       --confidence-vs-primary "lower|comparable|higher"
   ```

   ONE call per `/research` run. Re-calling overwrites (last call wins).

**MANDATORY — never skip, even when the bug looks unambiguous.** The phase exists specifically to challenge "looks unambiguous" framings: the regression class this phase guards against is the LLM that commits to the first plausible frame in Phase 2.3 and stops considering alternatives.

**Downstream impact.** Phase 2.4 / 2.4b / 2.4c findings that support the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed). Phase 3's `verify` enforces two gates: check 12a (unconditional) rejects a report whose `runner_up_framing` is unset — Phase 2.3b is mandatory and must execute before `verify` runs; check 12b (conditional on `runner_up_framing` set) rejects a report with zero `--framing runner-up` findings — at least one runner-up-tagged finding (positive or negative) must follow.

### Phase 2.4 — Parallel-pattern sweep (MANDATORY)

Phase 2.4 searches MUST probe both framings recorded in Phase 2.3b. After identifying the primary-frame parallel-pattern surface, run a SECOND search targeting the runner-up frame's falsifier. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

After the primary surface is located, run a parallel-pattern sweep over the SAME file before recording findings:

```
search_code(pattern="<primary-frame bug-pattern literal>")
```

The supported `search_code` argument is `pattern` only. Scope the sweep to the primary file by filtering the returned hits in the orchestrator — keep only rows whose `file_path` equals `<primary_file_path>`. Discard every hit outside that file. If `pattern` returns dozens of hits across the package, narrow it (add a containing identifier, include the file's base name as an OR-token in the regex) so the in-file rows surface near the top.

Then run a SECOND `search_code` targeting the runner-up frame's falsifier token PROJECT-WIDE (not in-file-only — the runner-up may surface in a different file):

```
search_code(pattern="<runner-up-falsifier literal>")
```

The falsifier literal comes from the `--falsifier` text recorded in Phase 2.3b — extract a literal code token from it (a method name, a property, a class identifier, a call shape). Both searches are MANDATORY; skipping the runner-up search leaves the runner-up frame's parallel-pattern evidence ungathered and biases the report toward the primary framing by default. If the runner-up search returns 0 hits, record a negative Finding via the Phase 2.6 setter with `--file-line="(none)"`, `--framing runner-up`, `--relevance="runner-up falsifier not found project-wide"`. If it returns hits, evaluate each and record supporting or disproving findings tagged `--framing runner-up`.

Example: primary surface is a `.sort()` at `ProductListView.vue:114` with status-only comparator (primary frame = "unstable comparator"); runner-up frame = "race between fetch and watch" with falsifier literal `watch(` or the fetch handler name. Sweep the primary file for any other `.sort(` / `.filter(` / `.map(` calls that touch the same data shape — there is often a parallel block (e.g. a sibling block at line 252-279) with the same bug; missing the parallel block lets it ship as a regression. Sweep project-wide for the runner-up falsifier literal — hits identify other places where the same race shape could occur. Record every parallel surface AND every runner-up hit as its own `Finding` row with the correct `--framing` tag.

This step is MANDATORY when `mode == "bug"` and the primary surface is an inline expression (sort / filter / comparator / validator). For enhancement mode, sweep is OPTIONAL.

### Phase 2.4b — Canonical-pattern search (MANDATORY)

Canonical-pattern search runs once per framing recorded in Phase 2.3b. The runner-up frame's canonical pattern may diverge from the primary's because the two frames imply different solution classes — search the codebase for the canonical pattern of EACH framing's desired fix. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

Before composing approaches in Phase 3, search the codebase for **existing implementations of the DESIRED behavior** — not the bug. Phase 2.3/2.4 chain finds where the bug LIVES; this step finds how the codebase ALREADY SOLVES the same problem class. Reuse beats reinvention; "Search before building" is a constitution constraint in every project.

Run a project-wide `search_code` for the literal token that characterizes the **primary** framing's fix pattern:

```
search_code(pattern="<primary-frame solution-pattern literal>")
```

Then run a SECOND project-wide `search_code` for the literal token that characterizes the **runner-up** framing's fix pattern (the canonical implementation that would resolve the runner-up frame's falsifier):

```
search_code(pattern="<runner-up-frame solution-pattern literal>")
```

Both searches are MANDATORY — the runner-up frame's canonical pattern may diverge from the primary's because the two frames imply different solution classes. Skipping the runner-up search leaves the runner-up frame without a canonical-reuse candidate, which biases Phase 3 toward the primary-frame recommendation by default.

Example (matching the Phase 2.4 example): if the primary frame is "sort comparator with no alphabetical tie-breaker", the primary solution-pattern literal is `localeCompare` (or `sortBy`, or whatever the project's canonical secondary-sort idiom is); if the runner-up frame is "fetch / watch race causes unstable input order", the runner-up solution-pattern literal is the project's canonical reactive-derivation idiom (e.g. `computed(` for Vue, `useMemo(` for React). Result rows from EITHER search = candidate canonical implementations elsewhere in the codebase. For each, judge whether it really solves the same problem class (look at the surrounding structure via `get_code_snippet`).

Record every confirmed canonical implementation as its own `Finding` row with:
- `--surface` = a label naming the helper / file role (e.g. "canonical sort helper", "existing localeCompare site")
- `--file-line` = exact `file_path:line` from the `search_code` result row (per Phase 2.3 grounding rule)
- `--relevance` = the literal phrase "canonical pattern — reusable" followed by a one-line note on what it does
- `--framing` = `primary` when the row supports the primary framing's canonical pattern; `runner-up` when it supports the runner-up framing's canonical pattern (per Phase 2.3b's downstream-impact rule)

These findings feed Phase 3:
- The recommended approach MUST cite the canonical pattern by exact file:line if one was found, and MUST recommend reusing it over writing a new helper. Fresh helper extraction is only justified when Phase 2.4b recorded `file_line = "(none)"` (no canonical found); in that case the `--rationale` must say so explicitly.
- When a canonical pattern was found, the Constitution Constraints section MUST include the "Search before building" rule with the canonical helper's file:line in the impact column. When no canonical was found, omit this entry — its absence is information.

If 0 canonical implementations are found for a framing (the codebase has no existing solution for that frame's problem class): record one `Finding` for THAT framing with `--surface="canonical-pattern search"`, `--file-line="(none)"`, `--relevance="no canonical pattern found project-wide for <framing's solution-pattern>; new helper extraction is justified"`, and the matching `--framing primary|runner-up` tag. Record the negative result independently per framing — a 0-result on the primary search does NOT mean the runner-up search is skipped, and vice versa. This makes the negative result explicit per framing so a reviewer can spot a miss. Note: `"(none)"` is the only sanctioned exception to the Phase 2.3 `file:line` grounding rule — it is a sentinel for an explicitly absent result, not a missing verification.

This step is MANDATORY for both bug and enhancement modes. Skipping it silently re-invents what already exists.

### Phase 2.4c — Helper-API surface enumeration (MANDATORY for bug mode; OPTIONAL for enhancement)

Helper-API surface enumeration runs once per framing recorded in Phase 2.3b. The runner-up frame may surface different fix-path helpers than the primary — the two frames imply different layer-stack entry points. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

Without this step the LLM anchors on view-layer / minimal-change fixes when the helper layer already has the inputs to enforce an invariant. Phase 2.4c forces structural evidence — inbound callers, dead siblings, consumer-chain endpoints — onto the report before Phase 3 enumerates approaches.

**Definition of "fix-path helper".** A helper whose signature carries the symptom value, or any value the symptom value derives from.

**Stopping rule (layer-boundary, NOT same-package).** Trace AT MOST 2 layer boundaries above the symptom site, following the dependency-inversion direction (outer-to-inner; e.g., presentation-layer file → composable/store → domain helper → entity static; presentation → application → domain). Stop at framework/vendor packages (do not trace into framework internals, vendored SDKs, or shared utility libs). Cross application/domain package boundaries within the project workspace — this is the explicit point of the rule. The OLD same-package restriction is removed: cross-package traces within the project are NOT just allowed, they are REQUIRED when the symptom lives in a presentation-layer file (Vue / React component, view, page). Verify check 8b enforces this: when the primary finding's `file:line` resolves to a presentation-layer path AND every `fix_path_helpers` entry's `file_line` is in the same package as the symptom, `verify` exits non-zero with a `cross-layer rule` violation. Domain-layer symptoms (a bug whose symptom site is already inside `pkg-<domain>/`) remain same-package OK — no cross-layer trace is required for domain-internal bugs because the helper layer is already the symptom layer.

For each fix-path helper, run the four steps below in order.

**Step 1 — Record the helper itself.** Run `search_graph(label="Method", qn_pattern="<helper QN>")` (or `label="Function"` / `label="Class"` per the helper's kind) to confirm the helper exists in the codebase index and to capture its definition `file_path:line`. Both the helper's qualified name AND its definition `file:line` are required:

```bash
.devforge/lib/research_helper record-fix-path-helper \
    --helper-qn "<helper qualified name>" \
    --file-line "<helper definition file_path:line>"
```

`--file-line` MUST be copied verbatim from the `search_graph` result row's `file_path` + `line` fields — this is where the helper itself is DEFINED, NOT where it is CALLED FROM. The setter rejects the `(none)` sentinel for `--file-line` because layer-boundary detection requires a real path. The setter is dedupe-on-append: re-recording the same `--helper-qn` is a no-op (the existing `--file-line` is preserved).

**Step 2 — Inbound caller enumeration.**

```
trace_path(<helper_qn>, mode=calls, direction=inbound)
```

Record EVERY caller (including the symptom site itself) via:

```bash
.devforge/lib/research_helper record-inbound-caller \
    --helper-qn "<helper_qn>" \
    --caller-qn "<caller_qn>" \
    --file-line "<path:line>"
```

The Phase 2.3 `file:line` grounding rule applies — `<path:line>` MUST be copied verbatim from the `trace_path` result row's `file_path` + `line` fields. Never reconstruct.

**Step 3 — Sibling-method enumeration.**

```
search_graph(label="Method", qn_pattern="<containing_class>\\.")
```

For each sibling returned, run `trace_path mode=calls direction=inbound`. Any sibling that appears to have an empty inbound set MUST be cross-verified via:

```
search_code(pattern="<method-name>(")
```

Only siblings with 0 inbound callers in `trace_path` AND 0 textual call sites in `search_code` are confirmed dead. Record each confirmed dead sibling via:

```bash
.devforge/lib/research_helper record-dead-sibling \
    --class-qn "<class qualified name>" \
    --method-qn "<method qualified name>" \
    --verified-via <trace_path|search_code>
```

`--verified-via` documents which evidence source confirmed the dead state. For any dead sibling discovered through this step, always pass `--verified-via search_code` — the textual cross-check is mandatory and `search_code` is the confirming evidence source. The `--verified-via trace_path` value exists for future cases where a graph-only trace is conclusive on its own; do not use it here. The helper accepts only those two literal values.

**Step 4 — Forward data-flow trace on the symptom value(s).** Extraction rule: from `memo.dimensions.desired.value`, pull every noun-phrase or token that maps to a code symbol (a method, property, class, named data field, or named payload value). If `desired.value` is expressed purely in user-facing terms with no identifiable code-symbols (e.g. 'list shows alphabetically'), skip Step 4 and note in the consumer-chain that desired is expressed in user terms only — Phase 2.5 classification will then default to `preference` (no payload-shape evidence available).

For each symbol cited in `memo.dimensions.desired.value`:

```
trace_path(<symptom-value-source>, mode=data_flow, direction=outbound)
```

Record the consumer-chain endpoint (the consumer that actually reads the value) via:

```bash
.devforge/lib/research_helper record-consumer-chain \
    --value "<symbol>" \
    --consumer-qn "<qualified name>" \
    --file-line "<path:line>" \
    --role "<one-line description of what the consumer does with this value>"
```

The Phase 2.3 `file:line` grounding rule applies to `--file-line` here as well.

**MANDATORY in bug mode.** Skipping is forbidden when `memo.mode == "bug"`. The helper's `verify` step enforces three gates on Phase 2.4c state: check 8 rejects an empty `fix_path_helpers` list in bug mode; check 8b (the cross-layer rule documented in the Stopping rule above) rejects a list where every `fix_path_helpers[].file_line` is in the same package as the primary symptom's file path when that symptom path is presentation-layer (Vue / React / views); check 9 rejects any `fix_path_helpers` entry that has no `inbound_callers` row. On non-zero exit from `verify` citing any of these checks, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then return to Phase 2.4c and complete the missing steps before re-running `verify`. For check 8b specifically, the fix is to trace one helper UP through a package boundary (presentation → application or presentation → domain) and re-run Step 1 with that helper's qualified name and definition `file:line`.

For enhancement mode this phase is OPTIONAL — run it when the enhancement adds a new code path that touches an existing helper signature; skip when the enhancement is purely additive in a new module.

### Phase 2.5 — Hypothesis enumeration (MANDATORY ≥2)

**MANDATORY value-semantics classification (run before hypothesis enumeration).** For every symbol extracted via the Phase 2.4c Step 4 extraction rule, classify it as one of:

- `preference` — per-user-action, per-toggle, per-request-context (e.g., a sort order the user picked, a filter the user set).
- `invariant` — per-identity, per-business-rule, payload-shape contract (e.g., an identifier required by the API contract, a flag the receiver dispatches on).
- `unclassified` — evidence insufficient to commit to either.

Evidence should cite a `consumer_chain` row recorded in Phase 2.4c — `--evidence` typically cites the consumer's `file:line` or its role string. (Helper does NOT validate the `--evidence` content beyond non-empty; the existence of a `consumer_chain` row for the same `--value` is what the helper enforces when `--classification invariant` is passed.) Call:

```bash
.devforge/lib/research_helper set-value-semantics \
    --value "<symbol>" \
    --classification <preference|invariant|unclassified> \
    --evidence "<text — typically a file:line or consumer name>"
```

The helper enforces this dependency: `set-value-semantics --classification invariant` exits with code 2 when no `consumer_chain` row exists for `<symbol>`. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), return to Phase 2.4c Step 4 to record the missing `consumer_chain` entry, then end the turn. The next turn re-runs `set-value-semantics`. The helper writes nothing on rejection — the state file is untouched.

Why this matters: an invariant value mis-classified as preference produces hypotheses framed "the UI didn't seed correctly" — wrong framing leads to view-layer fix recommendations in Phase 3. Classification grounds hypothesis enumeration in the right semantics.

Enumerate at least 2 candidate root causes for the symptom. For each, write a one-line falsifier (the observation that would disprove it) and mark whether falsification needs runtime data. Single-hypothesis output is rejected by the helper's `verify` gate.

For any hypothesis whose falsifier needs runtime data (lifecycle race, framework lifecycle gap, vendor side-effect, network-shaped issue, timing-shaped issue), prepare a specific probe — a `console.log` probe, an `app.config.warnHandler` capture, a network-tab inspection, a breakpoint dump, etc.

### Phase 2.6 — Wire findings into helper

After the CBM chain + parallel-pattern sweep + canonical-pattern search + helper-API surface enumeration (Phase 2.4c) + hypothesis enumeration complete, call helper setters in this order. Phase 2.4c state (`fix_path_helpers`, `inbound_callers`, `dead_siblings`, `consumer_chain`, `value_semantics`) is already recorded in the report by its own setters — do not re-record those surfaces via `record-finding`. Compose values from the in-context findings; do not re-shape.

For each finding — one per code surface that bears on the symptom, including every parallel surface from Phase 2.4 AND every canonical-pattern row from Phase 2.4b. Apply the same `search_code` pre-verification loop to canonical rows. The `--file-line="(none)"` negative-result row from Phase 2.4b is exempt from `search_code` verification — `(none)` is the sentinel value, not a path to verify.

```bash
.devforge/lib/research_helper record-finding \
    --surface "<surface label>" \
    --file-line "<path:line>" \
    --relevance "<one-line how-it-relates>" \
    --framing "<primary|runner-up>"
```

`<path:line>` MUST be the exact `file_path:line` from a `search_graph` or `search_code` result row (per Phase 2.3 grounding rule). BEFORE every `record-finding` call, run a one-line verification: `search_code(pattern="<expected literal at that line>")` and confirm the result row's `file_path:line` matches the value you are about to pass. On mismatch, take the result row's line as authoritative and pass THAT to `--file-line`; the LLM's recollection is wrong (off-by-one drift is the failure this catches). Only after the verification matches: call `record-finding`. If the verification `search_code` returns 0 hits: widen the pattern (try an adjacent literal) and retry once. If still 0 hits, pass the original result-row `file:line` you already hold (from the Phase 2.3 chain) and note the unconfirmed status in `--relevance`. Do not skip the finding.

`--framing` is optional and defaults to `primary` when omitted. Pass `--framing runner-up` for findings that support the runner-up framing recorded in Phase 2.3b — including NEGATIVE findings (evidence disproving the runner-up). At least one finding must carry `--framing runner-up` for `verify` check 12b to pass (check 12b fires only once `runner_up_framing` is set; check 12a — the unconditional gate that demands `runner_up_framing` be set at all — is satisfied earlier by the Phase 2.3b `record-runner-up-framing` call). That one finding may be positive (evidence supporting the runner-up) or negative (evidence the runner-up's falsifier did not hold up).

For each hypothesis (≥2):

```bash
.devforge/lib/research_helper record-hypothesis \
    --cause "<cause text>" \
    --falsifier "<one-line falsifier>" \
    --runtime-probe-needed <yes|no>
```

Then the primary root cause + confidence:

```bash
.devforge/lib/research_helper set-root-cause-hypothesis --value "<text>"
.devforge/lib/research_helper set-confidence --value <Confirmed|Hypothesis|Speculative>
```

Bug-mode structured root cause (only when `memo.mode == "bug"` AND `confidence ∈ {Confirmed, Hypothesis}`):

```bash
.devforge/lib/research_helper set-trigger --value "<immediate event>"
.devforge/lib/research_helper set-root-cause-systemic --value "<underlying systemic flaw>"
.devforge/lib/research_helper record-contributing-factor --value "<factor>"
# repeat record-contributing-factor up to 3 times
```

If any hypothesis carries `runtime_probe_needed=yes`, set the verify step (all three sub-fields required in one call):

```bash
.devforge/lib/research_helper set-verify-step \
    --probe "<log/instrumentation to add>" \
    --reproduction "<exact user action that triggers the symptom>" \
    --discriminator "<if X → H_n confirmed; if Y → H_m confirmed>"
```

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string), retry up to 3 times. On the 4th failure, copy stderr VERBATIM to the user and end the turn; user must re-run `/research` from scratch — prior partial state will be overwritten.

## Phase 3 — Report drafting + render

Phase 3 is orchestrator-direct compose (NO subagent dispatch). Read memo + report state once for context, then call the Phase 3 setters listed below in order.

```bash
.devforge/lib/research_helper read-memo
.devforge/lib/research_helper read-report
```

### Setters (in order)

1. **Summary** (3-5 sentences: what was found, root cause, recommended approach, remaining uncertainty):

   ```bash
   .devforge/lib/research_helper set-summary --value "<3-5 sentences>"
   ```

2. **Approaches** (typically 2; each must cite which hypothesis indices it addresses + which it does NOT cover). Hypothesis index strings come from the order the hypotheses were recorded in Phase 2 — refer to them as `"A"`, `"B"`, ... For each approach:

   ```bash
   .devforge/lib/research_helper set-approach \
       --name "<approach name>" \
       --description "<1-2 sentences>" \
       --addresses-hypotheses '["A","B"]' \
       --does-not-cover '["C"]' \
       --pros '["pro-1", "pro-2"]' \
       --cons '["con-1", "con-2"]' \
       --complexity <Low|Med|High>
   ```

   **MANDATORY (when `value_semantics` contains an invariant row AND `dead_siblings` is non-empty):** at least one approach in the enumerated list MUST touch the helper signature or revive a dead sibling — and MUST cite the dead-sibling `method_qn` (or the literal token `signature`) explicitly in the approach's `--name`, `--description`, `--pros`, or `--cons`. The helper's `verify` step (check 10) enforces this: on non-zero exit citing "no approach mentions helper signature change or dead-sibling QN", copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then re-call `set-approach` (overwriting or adding) so at least one approach satisfies the check.

3. **Recommended approach** — name must match an existing approach. Helper additionally enforces "must not violate `memo.dimensions.unchanged_behavior.value`" via a cross-check; pick the approach + cite hypotheses accordingly:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "<must match an approach.name>" \
       --rationale "<why this approach + acknowledged uncertainty>" \
       --hypotheses-addressed '["A","B"]' \
       --hypotheses-not-covered '["C"]'
   ```

   **MANDATORY canonical-pattern citation.** If Phase 2.4b recorded any `Finding` row with `relevance` starting "canonical pattern — reusable", the `--rationale` MUST cite that pattern's `file:line` and state the recommended approach REUSES it (not reinvents). Only justify a fresh helper extraction when the canonical pattern's `file_line` was recorded as `(none)` in Phase 2.4b (no canonical found), and the `--rationale` must say so explicitly: "no canonical pattern exists project-wide; new helper justified".

   **MANDATORY (when `value_semantics` contains an invariant row):** `--rationale` MUST cite at least one of: a `consumer_chain` row's `consumer_qn`, an invariant row's `evidence` string, OR a `dead_siblings` row's `method_qn`. The helper's `verify` step (check 11) enforces this: on non-zero exit citing "rationale cites neither a consumer_chain entry, an invariant evidence string, nor a dead-sibling QN", copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then re-call `set-recommended-approach` with a `--rationale` that contains one of those tokens.

   **Single-layer recommendation gate (Patch 4).** When all `fix_path_helpers[].file_line` resolve to the same package (single-layer detection via `_extract_package`, same heuristic as check 8b), the recommendation is anchored to one layer-stack region. The helper requires TWO additional args to defend the choice:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "<must match an approach.name>" \
       --rationale "<why this approach + acknowledged uncertainty>" \
       --hypotheses-addressed '["A","B"]' \
       --hypotheses-not-covered '["C"]' \
       --single-layer-justification "<prose: why symptom is layer-local>" \
       --cites '["<recorded row token>","<recorded row token>"]'
   ```

   `--single-layer-justification` is free-text prose explaining why the symptom is genuinely layer-local. `--cites` is a JSON array of tokens, each of which MUST resolve to a recorded `consumer_chain.consumer_qn`, `value_semantics.value`, `value_semantics.evidence`, OR `dead_siblings.method_qn` — the helper rejects any cite token that doesn't match a recorded row. Without `--single-layer-justification`, the helper exits with code 2 and stderr `set-recommended-approach: --single-layer-justification is required when all fix_path_helpers resolve to the same package (<pkg>).` Without `--cites` (or with `--cites '[]'`), the helper exits with code 2 and stderr `set-recommended-approach: --cites is required (non-empty JSON array)…`. Verify check 13 catches the same conditions at verify time (covers out-of-order setter calls where `recommended_approach` was written before `fix_path_helpers` collapsed to single-layer).

   **Suppression (check 8b precedence).** When check 8b would fire — i.e., the primary symptom's `file:line` is in a presentation-layer file (.vue / .tsx / .jsx / views / components / pages) AND all helpers are in the same package as the symptom — the single-layer gate is SUPPRESSED at both setter time AND verify time. Rationale: check 8b vetoes verify unconditionally for presentation-layer same-package state, so supplying `--single-layer-justification` cannot rescue the report. The LLM's only recovery path in that case is to add a cross-layer helper via Phase 2.4c, not to defend the single-layer recommendation. Reading order: if `verify` reports `cross-layer rule` (check 8b), trace one more helper UP through a package boundary in Phase 2.4c — do NOT attempt to satisfy check 13.

   **Recovery on rejection.** If the helper rejects the call (exit 2), copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Identify the rejection cause from the stderr text, fix the missing arg (supply justification, supply non-empty cites, or replace an unresolved cite with one that matches a recorded row), and re-call `set-recommended-approach`.

4. **Constitution constraints** — read `constitution.md` for rules that bear on the affected area + recommended approach. For each rule that constrains or enables the change:

   ```bash
   .devforge/lib/research_helper set-constitution-constraints \
       --rule "<rule reference, e.g. '§3.2 Error Handling'>" \
       --impact "<how it constrains or enables the approach>"
   ```

   **MANDATORY "Search before building" entry.** When Phase 2.4b found a canonical pattern, this section MUST include a `set-constitution-constraints` call with `--rule="Search before building"` (or the project's equivalent rule reference per `constitution.md`) and `--impact` containing the canonical pattern's `file:line` plus a one-line note that reuse beats reinvention. When no canonical was found, omit this entry — its absence is information.

5. **Complexity** (3 sub-fields in a single call):

   ```bash
   .devforge/lib/research_helper set-complexity \
       --codebase-changes <Low|Med|High> --codebase-notes "<estimated diff scope>" \
       --risk <Low|Med|High> --risk-notes "<what could regress>" \
       --verify-cost <Low|Med|High> --verify-notes "<probe + test effort>"
   ```

6. **Verdict** (mode-aware enum — helper rejects values outside the mode's allowed set):

   | Mode | Allowed verdict values |
   |---|---|
   | `bug` | `Root cause confirmed` / `Root cause hypothesis (needs repro)` / `Multiple plausible causes` |
   | `enhancement` | `Feasible` / `Feasible with caveats` / `Not Recommended` |

   ```bash
   .devforge/lib/research_helper set-verdict --value "<verdict>"
   ```

7. **Next-step text** — only emits when verdict ∈ proceeding-set (`Root cause confirmed` / `Root cause hypothesis (needs repro)` for bug; `Feasible` / `Feasible with caveats` for enhancement). On other verdicts the call is a no-op and the rendered report omits the Next-Step section.

   ```bash
   .devforge/lib/research_helper set-next-step-text
   ```

### Verify

```bash
.devforge/lib/research_helper verify
```

Helper cross-checks: ≥2 hypotheses, recommended-approach name matches an approach, recommended-approach respects `unchanged_behavior`, verdict ∈ mode-allowed-set, structured root-cause fields populated when bug-mode + confidence ∈ {`Confirmed`, `Hypothesis`}, verify-step's 3 sub-fields populated when any hypothesis needs a runtime probe, all required sections populated. Check 8b (cross-layer rule) rejects a bug-mode report where the primary symptom's `file:line` resolves to a presentation-layer path AND every `fix_path_helpers[].file_line` is in the same package as the symptom — at least one helper must trace through a package boundary; see Phase 2.4c Stopping rule. Check 12a (unconditional) rejects a report whose `runner_up_framing` is unset — Phase 2.3b must execute before `verify`. Check 12b (conditional on `runner_up_framing` set) rejects a report where no finding row carries `framing == "runner-up"` — at least one finding (positive or negative — disproving the runner-up via its falsifier is a valid outcome) must be tagged `--framing runner-up` for the runner-up to be considered probed. Check 13 (single-layer recommendation gate) rejects a bug-mode report where all `fix_path_helpers[].file_line` resolve to one package AND `recommended_approach.single_layer_justification` / `cites` are missing or empty — supply both via `set-recommended-approach --single-layer-justification ... --cites '[...]'` (see Phase 3 step 3). Check 13 is suppressed when check 8b applies (presentation-layer symptom + same-package helpers); in that case the single-layer escape path cannot satisfy verify and the only recovery is adding a cross-layer helper. Exit 0 → pass; non-zero → at least one violation enumerated on stderr.

On non-zero exit: copy stderr VERBATIM, identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/research` from scratch (all prior state will be overwritten).

### Render

```bash
.devforge/lib/research_helper render
```

Helper walks the locked schema and emits the full research report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order (Header → Metadata → Summary → Symptom → Codebase Findings (WHERE) → Root Cause Hypothesis (WHY) → optional Structured Root Cause → optional Runner-up framing → Hypothesis Enumeration → optional Recommended Verify Step → Approaches (HOW) → Constitution Constraints → Complexity Assessment → optional Open Uncertainties → optional Next Step), heading levels, and table shapes. The Runner-up framing section renders only when `runner_up_framing` is set (see Phase 2.3b). The Codebase Findings table includes a `Framing` column showing the per-finding tag (`primary` or `runner-up`).

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the rendered report.

The LLM does NOT edit the rendered report via Write or Edit at any point. The helper's `render` is the only writer; any post-render fix is applied by re-calling the relevant setter + `render` + `verify` in a new turn.

## Phase 4 — Save + recommend

### Ask to save

After echoing the rendered report, ask via AskUserQuestion `"Save this research to a file?"` with options `["save", "skip"]`.

End the turn. The user's reply opens the next turn.

### On save

Compute the filename from helper state: `research/<report.date>-<memo.topic_slug>.md` under `<install_root>`. Create the `research/` directory if it does not exist. If the target path already exists, append `-2`, `-3`, ... until a free name is found.

Write the rendered text captured in Phase 3 (the same bytes printed there) to the chosen path. Use the helper-rendered bytes verbatim — do not re-format or re-shape.

### On skip

The rendered report stays in the assistant message only. No file is written. `.devforge/research-state.json` and `.devforge/research-report.json` remain on disk until the next `/research` invocation overwrites them.

### Closing message

If a save happened AND the verdict is in the proceeding-set, the rendered report already contains a `## Next Step` section with a copy-pasteable `/specify "..."` block. Tell the user: `"/research is done. Open <path> to review. The 'Next Step' section at the bottom is a copy-pasteable block for a new /specify session — copy it manually when you're ready."`

If a save happened AND the verdict is not in the proceeding-set, the report omits the Next-Step section. Tell the user: `"/research is done. Open <path> to review. The verdict was '<verdict>' — recommended next step is to address the cited uncertainties or follow the recommended verify probe before specifying a fix."`

If the user chose `skip`, tell the user: `"/research is done. The report is in the prior message; .devforge/research-state.json and .devforge/research-report.json hold the state but will be overwritten on the next /research invocation."`
