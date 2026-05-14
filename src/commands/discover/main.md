---
name: discover
description: Pre-spec exploration of a greenfield feature; produce a structured discovery report grounded in prior-art survey + codebase fit-check.
argument-hint: "<topic>"
disable-model-invocation: true
---

# /discover — Greenfield Feature Discovery

`/discover` is repeatable per greenfield feature. It clarifies a vague feature idea into a structured scoping memo across 8 dimensions, runs an orchestrator-direct investigation that surveys prior art via web + Context7 AND reconciles user-belief against codebase reality via the CBM graph + `docs/` corpus, composes a discovery report with 2-3 design options + Build-vs-Buy + Derisk plan, and saves the rendered report to `discover/YYYY-MM-DD-<topic-slug>.md`. State + render shape are owned by `.devforge/lib/discover_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) has completed before any investigation fires.

Usage: `/discover "<topic>"` (e.g. `/discover "audit log persistence layer"` or `/discover "auth in a TypeScript backend framework"`).

## Outputs of this phase

- `.devforge/discover-scope.json` — ScopingMemo (Phase 1 state). Owned + shaped by the helper; initialized at Phase 0.3 (`reset-memo`, `set-topic`), then mutated via Phase-1 setter subcommands.
- `.devforge/discover-report.json` — DiscoveryReport (Phase 2 + 3 state). Owned + shaped by the helper; mutated only via Phase-2/3 setter subcommands.
- `<install_root>/discover/YYYY-MM-DD-<topic-slug>.md` — rendered report. Helper's `render` writes to stdout; orchestrator saves it via the Phase 4 save prompt. Filename slug is auto-derived by the helper from the topic.

## Phase 0 — Pre-flight gate

Two preflight checks run in order. Both must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/discover_helper preflight
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/init-forge`)
- `docs/architecture.md` (produced by `/generate-docs`)
- `.devforge/configure.yaml` (produced by `/configure`)
- `constitution.md` (produced by `/constitute`)

Exit 0 → all present + non-empty; proceed. Exit 2 → at least one missing or empty; helper emits a `BLOCKED:` message on stderr naming each missing artefact + producer command. On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/discover`.

### Phase 0.2 — CBM index refresh

```bash
.devforge/lib/generate_docs_helper preflight
```

This refreshes the CBM index stamp so Phase 2 graph queries see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. Helper non-zero exit: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn; user re-runs `/generate-docs` or `index_repository` and re-invokes `/discover`.

### Phase 0.3 — Topic argument

Two branches based on `$ARGUMENTS`:

- **`$ARGUMENTS` non-empty:** treat it as the topic. Proceed directly with the reset chain below (no AskUserQuestion, no turn break) in the same turn the command was invoked.
- **`$ARGUMENTS` empty:** ask the user via AskUserQuestion: `"What's the topic? (greenfield feature, one sentence)"` — single-line question text, free-text answer. End the turn. The user's reply arrives in the next turn as the topic. On the next turn: proceed with the reset chain below using the user's reply as `<topic>`.

Reset chain (runs in the turn determined by the branch above):

```bash
.devforge/lib/discover_helper reset-memo
.devforge/lib/discover_helper reset-report
.devforge/lib/discover_helper set-topic --value "<topic>"
.devforge/lib/discover_helper set-date --value $(date -u +%Y-%m-%d)
```

`reset-memo` + `reset-report` write fresh-defaults state. `set-topic` auto-derives `topic_slug` for the eventual filename. `set-date` enforces `YYYY-MM-DD`.

Fresh-every-run: `reset-memo` + `reset-report` ALWAYS run at Phase 0.3, unconditionally. Any prior `.devforge/discover-scope.json` + `.devforge/discover-report.json` are overwritten with fresh defaults. `/discover` does not resume mid-flight prior runs — every invocation starts clean. If the user killed a prior run mid-investigation, that work is lost; re-answer the rubric from scratch.

## Phase 1 — Scoping dialogue (rubric Q&A)

Convert the vague topic into a structured scoping memo across 8 dimensions. The helper owns the rubric; the orchestrator drives one dimension at a time, picking the highest-uncertainty dimension to ask next.

**MANDATORY: never skip the rubric.** Even when `$ARGUMENTS` contains a pre-filled feature description that appears to address all 8 dimensions, ask each dimension question separately and wait for the user's answer in its own turn. Pre-filled input is a STARTING POINT for the `functional_scope` dimension only — never a license to auto-fill the remaining 7 in one pass. User commitment is per-dimension; that is the forcing function this phase exists for. The rubric is not optional, not advisory, not skippable based on input completeness.

**MANDATORY: never fabricate a user mode.** Do not write — in any user-facing message, internal narration, or tool-call rationale — phrases like "user requested no-questions mode", "user wants free-form", "user said skip the rubric", "no-prompt mode", or any equivalent. No such mode exists. No such request is in scope. If you find yourself about to justify a shortcut by attributing intent to the user, STOP — you are rationalizing a fabrication. Run the rubric.

### Rubric dimensions

| Dimension (underscore form) | Setter (kebab form) | Captures |
|---|---|---|
| `functional_scope` | `set-scope-functional-scope` | Core behavior the feature delivers |
| `users` | `set-scope-users` | Who consumes the feature (role, surface) |
| `inputs_outputs` | `set-scope-inputs-outputs` | Data in / data out of the feature boundary |
| `integration_points` | `set-scope-integration-points` | Where in the existing architecture this lives (user's BELIEF — fit-check reconciles vs reality in Phase 2) |
| `constraints` | `set-scope-constraints` | Non-negotiable limits (latency, schema, security, compliance) |
| `non_goals` | `set-scope-non-goals` | Behaviors explicitly out of scope |
| `success_criteria` | `set-scope-success-criteria` | How "done" is recognized |
| `edge_cases` | `set-scope-edge-cases` | Failure modes, boundary conditions, adversarial inputs |

Per-dimension state enum: `Clear` / `Partial` / `Missing` (default `Clear` when a setter is called without `--state`). Turn cap: 3 follow-ups per dimension before the helper auto-marks `Partial` on the next set with `--increment-turn`.

### Pre-rubric supplementary

Before the first dimension question, ask one supplementary free-text prompt: `"Any similar existing code, libraries, or product references to pattern after?"` — single-line question text, free-text answer. After the user replies:

- If the user names ≥1 reference, record them:

  ```bash
  .devforge/lib/discover_helper record-references --values '["<ref-1>","<ref-2>"]'
  ```

- If the user names none, record an empty array:

  ```bash
  .devforge/lib/discover_helper record-references --values "[]"
  ```

This call does NOT gate progression. Advance to the docs scan regardless of the user's answer.

### Pre-rubric docs scan (orchestrator-only)

Before asking the first dimension question, read the project docs corpus to seed `integration_points` candidates:

- `docs/architecture.md` — project-tier architecture
- `docs/glossary.md` — term grounding

Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`:

1. `get_architecture` (CBM) — pulls the rendered architecture md from the graph.
2. `search_graph` with `label="File"` + `name_pattern=<regex on file_path>` — locate candidate package roots that match topic tokens. The argument name is `name_pattern`, NOT `file_pattern`; the wrong name returns silent 0 hits.

Surface 2-3 candidate packages or modules in the `integration_points` prompt as suggestions when that dimension is reached.

### Per-dimension question protocol

For each of the 8 dimensions, in highest-uncertainty-first order:

1. **Ask one question.** Use AskUserQuestion ONLY when the dimension answer fits 2-4 mutually-exclusive options; otherwise use a plain-prose prompt (paragraph context as needed printed as prose ABOVE the question; the question itself is a single line ending with `?`). AskUserQuestion question text is single-line only — never multi-line markdown or blockquotes. Most dimensions here are open-ended free text (`functional_scope`, `users`, `inputs_outputs`, `integration_points`, `constraints`, `non_goals`, `success_criteria`, `edge_cases`); a closed-choice prompt is appropriate only when the user's prior context narrowed an answer to a small mutually-exclusive set. Pick at runtime based on the dimension's shape.

2. **Persist the answer.** Call the dimension's setter:

   ```bash
   .devforge/lib/discover_helper set-scope-<dimension-kebab> \
       --value "<user's answer>" \
       --state <Clear|Partial|Missing>
   ```

   Subcommand names: `set-scope-functional-scope`, `set-scope-users`, `set-scope-inputs-outputs`, `set-scope-integration-points`, `set-scope-constraints`, `set-scope-non-goals`, `set-scope-success-criteria`, `set-scope-edge-cases`. Default `--state` is `Clear` — pass `--state Partial` when the answer leaves a gap. For follow-up turns on the same dimension, add `--increment-turn` so the helper tracks the bounded-turn cap.

3. **Run helper-side conflict check.**

   ```bash
   .devforge/lib/discover_helper check-conflicts
   ```

   Stdout is a JSON array of detected direct contradictions (token-overlap rule). If the array is non-empty: block via AskUserQuestion `"Which to keep — the new answer or the prior one?"` with the two competing values as options. Then record the resolution:

   ```bash
   .devforge/lib/discover_helper record-conflict-resolution \
       --index <0-based index from check-conflicts output> \
       --resolution "user-chose-<new|prior>" \
       --rewrite-dimension <dimension_name>  # underscore form, e.g. integration_points
   ```

   `--rewrite-dimension` clears the loser's value so the user must re-answer it on the next pass.

4. **Run LLM-side drift check.** Compare the just-set answer against the previously-confirmed dimensions held in memory from prior turns. Classify as one of:
   - `direct` — already handled by the helper in step 3; skip here.
   - `drift` — new answer expands scope beyond an earlier confirmed boundary (e.g., `users` was `"internal admins only"` earlier, but the new answer indicates external API consumers as well). Do not block. Hold the observation in memory. Surface immediately as a plain-prose message in the next assistant turn, BEFORE asking the next dimension question: `"Heads up — your <new dimension> answer suggests <observed drift>. Adjust <affected dimension> or continue?"` End the turn. The user's reply opens the next turn; parse it and determine whether to adjust the affected dimension or continue to the next dimension.
   - `refinement` — new answer is a superset of the earlier one (e.g., `"login + signup"` → `"login + signup + password-reset"`). Re-call the affected dimension's setter with the superset value to overwrite (e.g., `set-scope-functional-scope --value "login + signup + password-reset" --state Clear`). No user prompt.
   - `none` — no drift; advance to the next dimension.

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift and refinement classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns within the same `/discover` run by reading prior assistant messages in the conversation.

5. **Advance.** Pick the next highest-uncertainty dimension and return to step 1.

### Coverage check + exit

After all 8 dimensions have been asked at least once OR the user explicitly accepts gaps:

```bash
.devforge/lib/discover_helper scope-coverage
```

Stdout is JSON: `per_dimension` (map of `dim → {state, value, turns}`), `counts` (`{Clear, Partial, Missing}`), `conflicts_open` (count of conflicts still `blocked-pending-user`). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) so the user sees per-dimension state before deciding to continue or accept gaps.

Then ask the user via a plain-prose prompt: `"Scope coverage above. Continue clarifying any dimension, or accept current state and proceed to investigation?"` End the turn. The user's reply opens the next turn and determines the branch (continue clarifying → return to per-dimension protocol; accept gaps → record-gap + scope-finalize chain).

If the user wants to continue clarifying: return to the per-dimension protocol for any dimension whose state != `Clear`.

If the user accepts gaps: for each dimension with state ∈ `{Partial, Missing}`, record a gap marker, then finalize:

```bash
.devforge/lib/discover_helper record-gap \
    --dimension <name> \
    --description "<one-line gap description>"

.devforge/lib/discover_helper scope-finalize --accept-gaps
```

`--accept-gaps` flips `memo.override_recorded = True` — this is the closed override-set referenced by invariant D's verdict-flip rule (see Phase 3 verify).

If the user is clarifying all the way to `Clear`, finalize without the flag:

```bash
.devforge/lib/discover_helper scope-finalize
```

Exit code:
- `0` → memo accepted; advance to Phase 2.
- non-zero → blocked. Stderr enumerates the reason (unresolved direct conflict OR Partial/Missing without `--accept-gaps`). Copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), end the turn, address the cited issue on the next user reply.

### Stop discipline (mandatory)

After emitting any AskUserQuestion or free-text prompt in Phase 1, end the assistant turn. Do NOT advance to the next dimension, the next protocol step, or any helper setter call in the same turn. The user's reply opens the next turn; the next turn parses it and continues. Plain-prose prompts have no harness-level "wait for user" affordance — the LLM-level stop is the only mechanism preventing accidental auto-advance.

## Phase 2 — Investigation (orchestrator-inline)

Phase 2 runs in the main thread — NO subagent dispatch. Orchestrator-inline keeps the full session context intact across the three sequential steps below. Step 2.0 (internal canonical-pattern search) completes before Step 2.1 (Stream A web survey) begins; Step 2.1 completes all `record-prior-art` calls before Step 2.2 (Stream B fit-check) begins. This ordering ensures Step 2.1 narrows the web survey to the GAP capabilities (those NOT already implemented internally), and Step 2.2 can incorporate prior-art canonical-pattern names as additional search anchors.

### Step 2.0 — Internal canonical-pattern search (MANDATORY)

Greenfield framing assumes the project does not already implement the requested capability. That assumption is failure-prone: a project that ALREADY implements ≥1 capability from `functional_scope` elsewhere in the codebase invites a fresh-build recommendation when "extend the existing implementation" is the better path. Step 2.0 scans project-wide for canonical-pattern hits BEFORE any web survey, independent of the user's `integration_points` belief — so coverage does not depend on the user pointing at the right packages.

**Verb extraction (orchestrator-side).** Parse `memo.dimensions.functional_scope.value` into 1-5 capability verbs / nouns that name the feature's primary actions. Examples:

- `functional_scope = "audit log for quote and order changes"` → verbs/nouns = `audit`, `revision`, `history`, `snapshot`, `log`
- `functional_scope = "background job queue with retry and dead-letter handling"` → verbs/nouns = `queue`, `job`, `worker`, `retry`, `dead-letter`

Use canonical pattern names from the domain, not the raw user phrasing.

**Search (project-wide, both CBM tools).** For each extracted verb / noun:

1. `search_graph(name_pattern="<verb regex>", label="Class")` and `search_graph(name_pattern="<verb regex>", label="Function")` — locate named symbols.
2. `search_code(pattern="<verb literal>")` — text fallback for inline expressions per the mandatory `search_graph` → `search_code` chain. Catches reactive blocks (Vue `<script setup>`, React hooks, Svelte) that the graph indexer does not promote to named symbols.

**Record each plausible internal implementation.** For each result row that plausibly implements the capability (the verb appears in a class / function / file name that operates on the same domain entities as the requested feature):

```bash
.devforge/lib/discover_helper record-prior-art \
    --reference "<concern or class name>" \
    --kind pattern \
    --relevance "internal — existing implementation of <capability>" \
    --source "internal:<file_path>"
```

The `--source` prefix `internal:` distinguishes project-internal hits from Step 2.1 web survey hits. The helper accepts the `internal:<path>` form as free-text; the prefix is a convention this command depends on (helper invariant G in `verify` checks for it). Also record an integration touchpoint for each internal hit so it surfaces in the Phase 3 Integration Surface section:

```bash
.devforge/lib/discover_helper record-integration-touchpoint \
    --name "<concern>" \
    --module-path "<file_path>" \
    --reason "existing capability — candidate for reuse over fresh build"
```

**`--module-path` grounding** (same MANDATORY rule as in Step 2.2 below): the value must be copied verbatim from a `search_graph` or `search_code` result row's `file_path` field, or be a directory prefix common to ≥2 such result rows.

**Report internal hits to the user (gate before Step 2.1).** After all verbs / nouns have been searched and the internal hits recorded, copy the following message VERBATIM into your next user-facing message as a fenced code block (substitute the bracketed values; do not summarize or paraphrase):

```
Internal canonical-pattern search found <N> existing implementation(s) of <capability list>:
- <reference-1> — <file_path-1>
- <reference-2> — <file_path-2>
...
Step 2.1 (web survey) will now narrow to the GAP capabilities — those NOT covered by these internal hits.
```

When `N = 0` (no internal hits surfaced), still emit the message with the literal text `Internal canonical-pattern search found 0 existing implementations.` so the user sees the search ran. Step 2.1 then proceeds with the full `functional_scope` capability set, not a narrowed subset.

**Helper-side cite-back enforcement (invariant G).** When Step 2.0 records ≥1 `internal:<path>` prior-art entry, the helper's `verify` (Phase 3) enforces that `recommended_option.rationale` contains at least one of those `internal:` paths as a substring. The rationale must frame the recommended option as "extend existing `<path>`" or explicitly state which capability the existing implementation does NOT cover — fresh-build recommendations without that explicit gap citation are rejected with exit 2.

### Step 2.1 — Prior-art survey (Stream A, gap-narrowed)

Build a narrowed query from the Phase 1 memo before any web call: combine `functional_scope` + `constraints` + `non_goals` + `edge_cases` plus `memo.references` if non-empty. When Step 2.0 surfaced internal hits, EXCLUDE the capabilities already covered by those hits from the query — Stream A surveys only the GAP capabilities. Never query with the raw user input from `$ARGUMENTS` — that is unscoped and surfaces irrelevant hits.

Sources, in order of preference:

1. **`WebSearch`** — industry references, comparable products, established patterns (e.g., named OSS projects, RFCs, vendor architectures).
2. **Context7 MCP** — `mcp__context7__resolve-library-id` to canonicalize each candidate library name, then `mcp__context7__query-docs` for current docs on the resolved id. Training data ages out; Context7 returns current-version material.
3. **`WebFetch`** — specific cited URLs (RFCs, vendor docs, blog posts) when WebSearch surfaces a URL worth reading in full.

Record each result via the helper:

```bash
.devforge/lib/discover_helper record-prior-art \
    --reference "<library/product/pattern name>" \
    --kind <library|product|pattern> \
    --relevance "<one-line note tying it to the topic>" \
    --source "<url or context7-id>"
```

`--kind` is one of `library` / `product` / `pattern`. `--source` is optional (omit for a no-source pattern entry; the helper defaults to empty string).

### Step 2.2 — Fit-check (Stream B, two-layer existing-code awareness)

Reconcile the user's Phase 1 `integration_points` belief against the codebase reality. The user's Phase 1 `integration_points` answer is the user's BELIEF; the fit-check produces the REALITY. Mismatch between belief and reality IS a primary Phase 3 finding, not an error condition.

Scope every query to the modules cited in `memo.dimensions.integration_points.value`.

**Layer 1 — docs narrative.** Read these via the CBM graph (md files are indexed; use `search_graph` with `label="File"` + `name_pattern=<regex on file_path>`, NOT `file_pattern`) before any source-code discovery:

- `docs/architecture.md`
- `docs/<affected_package>/architecture.md` (substitute `<affected_package>` from the Phase 1 `integration_points` value)
- `docs/<affected_package>/<closest_concern>/index.md` (closest concern derived from the integration-points phrase)
- `docs/glossary.md`

**Layer 2 — CBM structural discovery chain (MANDATORY order).** Raw `Read` / `Grep` / `Glob` / `grep` / `find` / `cat` over source-file extensions are forbidden and will be blocked by runtime hooks on the first matched call per session. Chain:

1. **`search_graph`** — query for named symbols and files matching the integration-points tokens. Use `qn_pattern` for qualified-name regex; `name_pattern` for short-name regex; `label="File"` queries use `name_pattern` (regex on file_path), NOT `file_pattern`.
2. If `search_graph` returns 0 hits for an expected behavior → **`search_code`** — text or regex search with a literal token over the affected package. This catches inline expressions buried inside framework reactive blocks (Vue `<script setup>`, React hooks, Svelte reactive blocks) that the graph indexer does not promote to named symbols. Falling through to `search_code` is the mandatory fallback before declaring an integration absent.
3. **`trace_path`** — impact analysis on confirmed surfaces. Pick a `mode` from `calls` / `data_flow` / `cross_service`.
4. **`get_code_snippet`** — read source on the highest-confidence candidates. This is the only sanctioned source-read path; do not use raw `Read`.

Confidence calibration: 0 hits at `search_graph` alone means "no NAMED implementation"; 0 hits at `search_code` means "truly absent". Do not conflate these.

Record each integration touchpoint:

```bash
.devforge/lib/discover_helper record-integration-touchpoint \
    --name "<touchpoint name>" \
    --module-path "<path>" \
    --reason "<why this touchpoint matters>"
```

**`--module-path` grounding (MANDATORY).** Every `--module-path` value MUST be copied verbatim from a `search_graph` or `search_code` result row's `file_path` field, or be a directory prefix common to ≥2 such result rows (e.g., `packages/<pkg-name>/src/<concern>`). Never derive a module path from `get_code_snippet` output, raw recollection, or prose context — the LLM will hallucinate plausible-but-nonexistent package paths. If you only have a snippet and need the path, re-run `search_code` for a literal token from the snippet to recover the authoritative row. If that re-run returns 0 hits, widen the token (try a longer substring or a different literal from the same snippet) and retry once. If still 0 hits, the module is not reliably locatable — pass `--module-path "(unverified)"` and prefix the `--reason` value with `unverified path —` so the unconfirmed status carries into the rendered report.

For each recorded touchpoint, reconcile user-belief vs scan-reality:

```bash
.devforge/lib/discover_helper record-fit-assessment \
    --touchpoint "<must match an existing integration_touchpoint.name>" \
    --user-expected "<user's Phase 1 belief about this touchpoint>" \
    --reality "<what the CBM scan + docs actually showed>" \
    --effort <Low|Medium|High|"Major refactor required"> \
    --blockers '["blocker-1","blocker-2"]'
```

`--touchpoint` MUST match the `--name` of an existing `record-integration-touchpoint` entry (helper rejects an unknown touchpoint). `--effort` is one of `Low` / `Medium` / `High` / `Major refactor required` (the last entry contains a space — quote it). `--blockers` is a JSON array of strings; omit or pass `'[]'` for none.

After all fit-assessments are recorded, aggregate:

```bash
.devforge/lib/discover_helper set-overall-fit --value <Good|Acceptable|Strained|Misfit>
.devforge/lib/discover_helper set-effort-estimate --value <Low|Medium|High|"Major refactor required">
.devforge/lib/discover_helper set-fit-rationale --value "<one-paragraph rationale>"
```

`set-overall-fit` enum is `Good` / `Acceptable` / `Strained` / `Misfit`. `set-effort-estimate` shares the `EFFORT_ENUM` used by `record-fit-assessment`.

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string or an enum-spelling miss), retry up to 3 times. On the 4th failure, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) and end the turn; user must re-run `/discover` from scratch — prior partial state will be overwritten.

## Phase 3 — Report drafting + render

Phase 3 is orchestrator-direct compose (NO subagent dispatch). Read memo + report state once for context, then call the Phase 3 setters listed below in order.

```bash
.devforge/lib/discover_helper read-memo
.devforge/lib/discover_helper read-report
```

### Setters (in order)

1. **Summary** (3-5 sentences: feature in scope, prior-art highlights, fit verdict, recommended direction, primary risk):

   ```bash
   .devforge/lib/discover_helper set-summary --value "<3-5 sentences>"
   ```

2. **Design options** (call ≥1 time; aim for 2-3). Each design option is a distinct data model / state machine / API shape — NOT a library comparison (library candidates were captured by Step 2.1's prior-art). For each option:

   ```bash
   .devforge/lib/discover_helper set-design-option \
       --name "<unique option name, no letter prefix>" \
       --shape "<1-3 sentences describing the data model / API / state machine>" \
       --pros '["pro-1","pro-2"]' \
       --cons '["con-1","con-2"]' \
       --complexity <Low|Med|High>
   ```

   `--complexity` enum is `Low` / `Med` / `High` (note: `Med`, not `Medium`). `--pros` and `--cons` each require ≥1 non-empty string. `--name` MUST NOT carry a letter prefix (`A:`, `Option B:`, etc.) — the helper auto-assigns the letter A/B/C based on insertion order during render. A baked-in `<letter>:` prefix produces `### Option A: A: ...` double-prefix render artifacts; the setter rejects this with exit 2.

3. **Recommended option** — `--name` must match the `--name` of a `set-design-option` entry already recorded; the helper rejects an unknown name:

   ```bash
   .devforge/lib/discover_helper set-recommended-option \
       --name "<must match an existing design-option name>" \
       --rationale "<why this option + acknowledged tradeoffs>"
   ```

4. **Build-vs-Buy** — pick `Build` / `Buy` / `Hybrid`. `--build` describes the build-path; `--buy` describes the adopt-an-existing-thing path (typically grounded in one of Step 2.1's prior-art entries):

   ```bash
   .devforge/lib/discover_helper set-build-vs-buy \
       --build "<build-path description>" \
       --buy "<buy-or-adopt-path description>" \
       --recommendation <Build|Buy|Hybrid> \
       --reasoning "<reasoning text>"
   ```

5. **Derisk plan** — at least 1 item; each item is a one-line action that reduces uncertainty before commitment (e.g., spike, prototype, contract test, vendor benchmark):

   ```bash
   .devforge/lib/discover_helper set-derisk-plan --items '["item-1","item-2","item-3"]'
   ```

6. **Constitution constraints** — read `constitution.md` for rules that bear on the recommended option + integration touchpoints. For each rule that constrains or enables the design, call the setter (call 0..N times — omit entirely when no rule applies):

   ```bash
   .devforge/lib/discover_helper set-constitution-constraints \
       --rule "<rule reference, e.g. '§3.2 Error Handling'>" \
       --impact "<how it constrains or enables the recommended option>"
   ```

7. **Verdict** — one of `Worth pursuing` / `Promising with caveats` / `Reconsider`. Apply the verdict-flip rule (invariant D): when `overall_fit ∈ {Strained, Misfit}` OR `effort_estimate = "Major refactor required"`, the verdict MUST be `Reconsider`, UNLESS the Phase 1 finalize set `memo.override_recorded = True` (via `scope-finalize --accept-gaps`):

   ```bash
   .devforge/lib/discover_helper set-verdict --value "<verdict>"
   ```

8. **Recommendation** — concrete next action + one-line "what happens next":

   ```bash
   .devforge/lib/discover_helper set-recommendation \
       --action "<concrete next action>" \
       --next "<one-line description of the immediate next step>"
   ```

9. **Next-step text** — composed by the helper from `memo.functional_scope` + `memo.users` + `memo.success_criteria` + `report.verdict` + `report.recommended_option`. Call the subcommand on every verdict — on `Worth pursuing` / `Promising with caveats` the helper composes a copy-pasteable handoff block; on `Reconsider` the helper clears `next_step_text` to `None` so the rendered report omits the Next-Step section (invariant E enforces this in `verify`).

   Pass an LLM-distilled 1-2 sentence topic via `--topic`. Compose the topic yourself from `memo.functional_scope` + `memo.users` + `memo.success_criteria` — keep it ≤2 sentences and ≤200 characters; never copy the entire `functional_scope` value verbatim. The distilled topic becomes the argument inside `/specify "..."` at the top of the handoff block. The helper strips literal `\n` escape sequences from the topic and from the embedded key-fact values; do not rely on that as a license to pass multi-paragraph junk — the cleanup is defensive, not stylistic.

   ```bash
   .devforge/lib/discover_helper set-next-step-text \
       --topic "<1-2 sentence distilled topic, ≤200 chars>"
   ```

   On `verdict = Reconsider`, omit `--topic`; the call clears `next_step_text` regardless:

   ```bash
   .devforge/lib/discover_helper set-next-step-text
   ```

### Verify

```bash
.devforge/lib/discover_helper verify
```

Helper cross-checks the following invariants. Exit 0 → pass; non-zero → at least one violation enumerated on stderr.

- **A** — required fields populated per verdict (different minima per verdict; `Reconsider` accepts a thinner report than the proceeding-verdicts).
- **B** — `design_options` ≥ 1 entry when verdict ∈ `{Worth pursuing, Promising with caveats}`.
- **C** — `recommended_option.name` matches an existing `design_options[*].name`.
- **D — Verdict flip rule** — `overall_fit ∈ {Strained, Misfit}` OR `effort_estimate = "Major refactor required"` → verdict MUST be `Reconsider` UNLESS `memo.override_recorded == True` (set only by `scope-finalize --accept-gaps`). This `unless` clause is the closed override-set — the only sanctioned override path is the Phase 1 explicit `--accept-gaps` finalization; no other gate flips the rule.
- **E** — `next_step_text` non-empty when verdict ∈ `{Worth pursuing, Promising with caveats}`; `None` when verdict is `Reconsider`.
- **F** — `derisk_plan` ≥ 1 entry when verdict ∈ `{Worth pursuing, Promising with caveats}`.
- **G — Internal canonical-pattern cite rule** — when any `prior_art[*].source` starts with `internal:`, `recommended_option.rationale` MUST contain at least one of those `internal:` file/dir paths as a substring. Forces the recommended option to be framed as "extend existing `<path>`" or to state explicitly which capability the existing implementation does NOT cover. Triggered only when Step 2.0 surfaced ≥1 internal hit; no-op otherwise.

On non-zero exit: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/discover` from scratch (all prior state will be overwritten).

### Render

```bash
.devforge/lib/discover_helper render
```

Helper walks the locked schema and emits the full discovery report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order, heading levels, and table shapes.

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the rendered report.

The LLM does NOT edit the rendered report via Write or Edit at any point. The helper's `render` is the only writer; any post-render fix is applied by re-calling the relevant setter + `render` + `verify` in a new turn.

## Phase 4 — Save + recommend

### Ask to save

After echoing the rendered report, ask via AskUserQuestion `"Save this discovery report to a file?"` with options `["save", "skip"]`.

End the turn. The user's reply opens the next turn.

### On save

Compute the filename from helper state: `discover/<report.date>-<memo.topic_slug>.md` under `<install_root>`. Create the `discover/` directory if it does not exist. If the target path already exists, append `-2`, `-3`, ... until a free name is found.

Write the rendered text captured in Phase 3 (the same bytes printed there) to the chosen path. Use the helper-rendered bytes verbatim — do not re-format or re-shape.

### On skip

The rendered report stays in the assistant message only. No file is written. `.devforge/discover-scope.json` and `.devforge/discover-report.json` remain on disk until the next `/discover` invocation overwrites them.

### Closing message

If a save happened AND the verdict is in the proceeding-set (`Worth pursuing` / `Promising with caveats`), the rendered report already contains a `## Next Step` section with a copy-pasteable handoff block. Tell the user: `"/discover is done. Open <path> to review. The 'Next Step' section at the bottom is a copy-pasteable block for your next session — copy it manually when you're ready."`

If a save happened AND the verdict is `Reconsider`, the report omits the Next-Step section. Tell the user: `"/discover is done. Open <path> to review. The verdict was 'Reconsider' — address the cited concerns or refine scope before continuing."`

If the user chose `skip`, tell the user: `"/discover is done. The report is in the prior message; .devforge/discover-scope.json and .devforge/discover-report.json hold the state but will be overwritten on the next /discover invocation."`
