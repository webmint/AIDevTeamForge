---
name: research
description: Investigate a bug or enhancement against the codebase; produce a structured research report grounded in CBM + docs.
disable-model-invocation: true
---

# /research — Codebase Research

`/research` is invoked after the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It clarifies a vague bug or enhancement input into a structured symptom memo, then runs an orchestrator-direct investigation that consults the CBM graph + `docs/` corpus, composes a research report with mandatory ≥2 hypothesis enumeration, and saves the rendered report to `research/YYYY-MM-DD-<topic-slug>.md`. State + render shape are owned by `.devforge/lib/research_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread.

Usage: `/research "<topic>"` (e.g. `/research "items not sorted in admin products view"` or `/research "make export faster on large datasets"`).

## Outputs of this phase

- `.devforge/research-state.json` — SymptomMemo (Phase 1 state). Owned + shaped by the helper; mutated only via Phase-1 setter subcommands.
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

Idempotency note: `reset-memo` + `reset-report` run only here at Phase 0 start. On resume (kill-and-restart), do NOT re-reset — see `## Resume` at the end of this spec.

## Phase 1 — Symptom clarification (rubric Q&A)

Convert the vague topic into a structured symptom memo across 6 dimensions. The helper owns the rubric; the orchestrator drives one dimension at a time, picking the highest-uncertainty dimension to ask next.

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

   Subcommand names: `set-symptom`, `set-affected-area`, `set-repro-or-current`, `set-desired`, `set-scope`, `set-unchanged-behavior`. Default `--state` is `Clear` — pass `--state Partial` when the answer leaves a gap. For follow-up turns on the same dimension, add `--increment-turn` so the helper tracks the bounded-turn cap.

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

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift, refinement, and mode-flip classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns by reading the prior assistant message on resume.

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

Ask via AskUserQuestion `"Investigation will scan roughly <N> CBM calls. Proceed?"` with options `["proceed", "cancel"]`. On `cancel`: copy a one-line note ("Investigation cancelled; .devforge/research-state.json preserved — re-run /research to resume.") into the user-facing message and end the turn. On `proceed`: continue.

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

### Phase 2.4 — Parallel-pattern sweep (MANDATORY)

After the primary surface is located, run a parallel-pattern sweep over the SAME file before recording findings:

```
search_code(pattern="<bug-pattern literal>")
```

The supported `search_code` argument is `pattern` only. Scope the sweep to the primary file by filtering the returned hits in the orchestrator — keep only rows whose `file_path` equals `<primary_file_path>`. Discard every hit outside that file. If `pattern` returns dozens of hits across the package, narrow it (add a containing identifier, include the file's base name as an OR-token in the regex) so the in-file rows surface near the top.

Example: primary surface is a `.sort()` at `ProductListView.vue:114` with status-only comparator. Sweep the same file for any other `.sort(` / `.filter(` / `.map(` calls that touch the same data shape — there is often a parallel block (e.g. a sibling block at line 252-279) with the same bug. Missing the parallel block lets it ship as a regression. Record every parallel surface as its own `Finding` row.

This step is MANDATORY when `mode == "bug"` and the primary surface is an inline expression (sort / filter / comparator / validator). For enhancement mode, sweep is OPTIONAL.

### Phase 2.5 — Hypothesis enumeration (MANDATORY ≥2)

Enumerate at least 2 candidate root causes for the symptom. For each, write a one-line falsifier (the observation that would disprove it) and mark whether falsification needs runtime data. Single-hypothesis output is rejected by the helper's `verify` gate.

For any hypothesis whose falsifier needs runtime data (lifecycle race, framework lifecycle gap, vendor side-effect, network-shaped issue, timing-shaped issue), prepare a specific probe — a `console.log` probe, an `app.config.warnHandler` capture, a network-tab inspection, a breakpoint dump, etc.

### Phase 2.6 — Wire findings into helper

After the CBM chain + parallel-pattern sweep + hypothesis enumeration complete, call helper setters in this order. Compose values from the in-context findings; do not re-shape.

For each finding (one per code surface that bears on the symptom — including every parallel surface from Phase 2.4):

```bash
.devforge/lib/research_helper record-finding \
    --surface "<surface label>" \
    --file-line "<path:line>" \
    --relevance "<one-line how-it-relates>"
```

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

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string), retry up to 3 times. On the 4th failure, copy stderr VERBATIM to the user and end the turn; user must re-run `/research` to retry from the saved memo state.

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

3. **Recommended approach** — name must match an existing approach. Helper additionally enforces "must not violate `memo.dimensions.unchanged_behavior.value`" via a cross-check; pick the approach + cite hypotheses accordingly:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "<must match an approach.name>" \
       --rationale "<why this approach + acknowledged uncertainty>" \
       --hypotheses-addressed '["A","B"]' \
       --hypotheses-not-covered '["C"]'
   ```

4. **Constitution constraints** — read `constitution.md` for rules that bear on the affected area + recommended approach. For each rule that constrains or enables the change:

   ```bash
   .devforge/lib/research_helper set-constitution-constraints \
       --rule "<rule reference, e.g. '§3.2 Error Handling'>" \
       --impact "<how it constrains or enables the approach>"
   ```

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

Helper cross-checks: ≥2 hypotheses, recommended-approach name matches an approach, recommended-approach respects `unchanged_behavior`, verdict ∈ mode-allowed-set, structured root-cause fields populated when bug-mode + confidence ∈ {`Confirmed`, `Hypothesis`}, verify-step's 3 sub-fields populated when any hypothesis needs a runtime probe, all required sections populated. Exit 0 → pass; non-zero → at least one violation enumerated on stderr.

On non-zero exit: copy stderr VERBATIM, identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/research` to repair from saved state.

### Render

```bash
.devforge/lib/research_helper render
```

Helper walks the locked schema and emits the full research report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order (Header → Metadata → Summary → Symptom → Codebase Findings (WHERE) → Root Cause Hypothesis (WHY) → optional Structured Root Cause → Hypothesis Enumeration → optional Recommended Verify Step → Approaches (HOW) → Constitution Constraints → Complexity Assessment → optional Open Uncertainties → optional Next Step), heading levels, and table shapes.

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

The rendered report stays in the assistant message only. No file is written. `.devforge/research-state.json` and `.devforge/research-report.json` are preserved on disk — the user can re-run `/research` to resume from saved state.

### Closing message

If a save happened AND the verdict is in the proceeding-set, the rendered report already contains a `## Next Step` section with a copy-pasteable `/specify "..."` block. Tell the user: `"/research is done. Open <path> to review. The 'Next Step' section at the bottom is a copy-pasteable block for a new /specify session — copy it manually when you're ready."`

If a save happened AND the verdict is not in the proceeding-set, the report omits the Next-Step section. Tell the user: `"/research is done. Open <path> to review. The verdict was '<verdict>' — recommended next step is to address the cited uncertainties or follow the recommended verify probe before specifying a fix."`

If the user chose `skip`, tell the user: `"/research is done. The report is in the prior message; .devforge/research-state.json and .devforge/research-report.json hold the state — re-run /research to resume."`

## Resume

`/research` supports kill-and-resume. If the user invokes `/research` again before completing a prior run, the prior state lives in `.devforge/research-state.json` + `.devforge/research-report.json`.

Resume flow on re-invocation:

1. Run Phase 0.1 + 0.2 preflight (always — predecessor artefacts may have changed).
2. Read prior state:

   ```bash
   .devforge/lib/research_helper read-memo
   .devforge/lib/research_helper read-report
   ```

3. Inspect `report.topic` (the canonical topic field; helper auto-derives `memo.topic_slug` from it): if it matches the new `$ARGUMENTS` (or no argument given), resume. If it differs, ask via AskUserQuestion `"Prior research on '<prior topic>' is in progress. Resume it or start fresh?"` with options `["resume", "start-fresh"]`. On `start-fresh`: run Phase 0.3 reset; on `resume`: skip Phase 0.3.

4. Check coverage to find resume point:

   ```bash
   .devforge/lib/research_helper symptom-coverage
   ```

   If any dimension has state != `Clear` AND `memo.override_recorded` is not true → resume Phase 1 at the first such dimension.

   If memo is finalized (all `Clear` or `override_recorded=true`) AND any required Phase 2 setter is missing → resume Phase 2. Inspect `report` JSON for the first unset section: findings empty → start at Phase 2.1 cost gate; findings present but `hypotheses` empty or `root_cause_hypothesis`/`confidence` unset → resume Phase 2.6 at the first missing setter; hypotheses and root-cause set but recommended approach missing → start at Phase 3 compose.

   If memo + report are both populated → run `verify`; on pass, proceed directly to Phase 3's `render` + Phase 4 save. On non-zero `verify`, repair the cited violation per Phase 3's verify-failure handling.

Resume never re-runs `reset-memo` / `reset-report` — those are Phase 0.3 only.
