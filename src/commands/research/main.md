---
name: research
description: Investigate a bug or enhancement against the codebase; produce a structured research report grounded in CBM + docs.
argument-hint: "<topic>"
---

# /devforge:research — Codebase Research

`/devforge:research` is repeatable per ticket. It clarifies a vague bug or enhancement input into a structured symptom memo, runs an orchestrator-direct investigation that consults the CBM graph + `docs/` corpus, composes a research report with mandatory ≥2 hypothesis enumeration, and — once the user confirms the save — allocates the feature directory and saves the rendered report there as `research-report.md`. State + render shape are owned by `.devforge/lib/research_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) has completed before any investigation fires.

`/devforge:research` reads source code and never writes it. The confirmed save is nonetheless a repository mutation: it creates the feature directory, may create the `spec/NNN-<feature-slug>` branch, and `[WIP]`-commits the artifacts it wrote. A run the user declines to save leaves nothing behind in the repository outside `.devforge/` scratch (a tier-1.5 probe script, if any, persists separately in system scratch — see Step 4.7).

Usage: `/devforge:research "<topic>"` (e.g. `/devforge:research "items not sorted in admin products view"` or `/devforge:research "make export faster on large datasets"`).

## Outputs of this phase

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run writes into: one path the orchestrator holds in working memory for the rest of the run. Step 4.2 takes it from `allocate-feature-dir`'s `relative_path` on a fresh allocation, and Phase 0.6's attach arm takes it from the re-entry seed file's parent directory. The orchestrator never composes it from parts, never re-shapes it, and never substitutes another key for it; every artifact path below is `<feature_dir>` plus a filename. In wrapper mode it resolves under the install root, never the nested source root.

- `.devforge/research-state.json` — SymptomMemo (Phase 1 state). Owned + shaped by the helper; initialized at Phase 0.3 (`reset-memo`, `set-topic`), then mutated via Phase-1 setter subcommands.
- `.devforge/research-report.json` — ResearchReport (Phase 2 + 3 state). Owned + shaped by the helper; mutated only via Phase-2/3 setter subcommands.
- `<feature_dir>` — the feature directory, allocated by Phase 4's `allocate-feature-dir` after the user confirms the save and the feature name (a `/devforge:grill` re-entry run reuses the seed's existing directory instead — see Phase 0.6). Nothing under `specs/` is created before that confirmation.
- `<feature_dir>/research-report.md` — rendered report. Helper's `render` writes to stdout; Phase 4 saves those bytes into the allocated directory.
- `<feature_dir>/research-handoff.json` — the specify-bound handoff, written by Phase 4's `finalize-handoff --feature-dir` on save (sibling to the report).
- `<feature_dir>/probe-script.<ext>` — CONDITIONAL: present only when Phase 2.6 recorded a tier-1.5 probe script; Phase 4 copies it out of scratch on save.
- `<feature_dir>/emission-matrix.md` — CONDITIONAL: present only when the recommended approach removes or suppresses a value the changed code emits; composed by the orchestrator in Phase 3 and written by Phase 4 on save. Its absence means that trigger did not fire — see Phase 3's Emission matrix step.
- Branch `spec/NNN-<feature-slug>` — created by Phase 4 on a freshly allocated directory when the run is on the repository's default branch. On any other branch, and on every `/devforge:grill` re-entry run, no checkout is emitted and the current branch is kept.

On save, Phase 4 `[WIP]`-commits the artifacts it wrote into the install repo via `.devforge/lib/artifact_helper commit-artifacts` (install-repo-only, fail-soft) so the work is git-safe the moment it is written; the commit folds into `/devforge:finalize`'s squash.

## Phase 0 — Pre-flight gate

Two preflight checks run in order. Both must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/research_helper preflight
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/devforge:init-forge`)
- `docs/architecture.md` (produced by `/devforge:generate-docs`)
- `.devforge/configure.yaml` (produced by `/devforge:configure`)
- `constitution.md` (produced by `/devforge:constitute`)

Exit 0 → all present + non-empty; proceed. Exit 2 → at least one missing or empty; helper emits a `BLOCKED:` message on stderr naming each missing artefact + producer command. On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/devforge:research`.

**Memory read (same call).** The same `preflight` call also reads `.devforge/memory.md` — the project's persistent cross-session lessons file — and writes a JSON object to stdout ahead of the exit-code branch above, so the object is there on the pass and on the `BLOCKED` path alike. Capture that stdout and take `memory_state` from it; the object also carries `memory_excerpt` (the populated `## ` sections of that file, `## Task Outcomes` excluded) and `memory_present`. This changes nothing about the exit-2 handling above: on that path the JSON is extra output to ignore, and copying the stderr verbatim and ending the turn is still the whole response. If stdout carries no JSON object at all, treat it as `absent` and take the no-op branch below — the memory read never stops the run.

Branch on `memory_state`:

- `absent` or `stub` → no-op. Say nothing to the user about memory, raise no warning, add no step. A memory file that is missing, or still the stub the installer ships, records no lessons yet; on a new project that is the correct state, not a fault to remedy.
- `populated` → read `memory_excerpt` and pick out the entries that bear on this run's topic. Hold those in working memory now (so they are not lost during the rubric) and carry them into Phase 1's `affected_area` + `scope` questions and Phase 2's investigation. Arriving there is the point: an entry can name a place to look — a related repository that is readable locally, a file to read before scoping — and one that surfaces only after Phase 1 has committed the scope is too late to change what this run searches. When `memory_excerpt` comes back empty even though `memory_state` is `populated` — every populated line sits in the excluded `## Task Outcomes` section — take the `absent` / `stub` no-op branch above instead: carry nothing into Phase 1 or Phase 2, and say nothing to the user about memory.

The excerpt is not the whole file: it renders the file's populated `## ` sections — a section with no entries under its heading is dropped heading and all, `## Task Outcomes` is excluded outright, and any other section is kept — and when the line budget cannot fit a section whole, the lines it drops are always that section's EARLIEST ones, with an inline marker line right after the heading naming how many were omitted. So an entry's absence from a non-empty excerpt means it sits in the excluded section or behind a marker the excerpt itself declares, never "never recorded" — do not conflate these. An empty excerpt means there are no readable lessons: the file is absent or still the shipped stub, or everything in it sits in the excluded section.

**Honesty bound.** A carried memory entry is an UNVERIFIED prior-session assertion, not evidence for this run: it is a candidate evidence source and a constraint to check, never a finding and never grounds for a conclusion on its own. A past session wrote it, and the code it describes may have changed since — or the entry may have been wrong when it was written. Re-ground what it points at through the Phase 2 chain before any of it reaches `record-finding`, which takes its `file:line` from the Phase 2.3 grounding rule and never from prose.

### Phase 0.2 — CBM index refresh

```bash
.devforge/lib/generate_docs_helper preflight
```

This refreshes the CBM index stamp so Phase 2 graph queries see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. Helper non-zero exit: copy stderr VERBATIM and end the turn; user re-runs `/devforge:generate-docs` or `index_repository` and re-invokes `/devforge:research`.

### Phase 0.3 — Topic argument

If `$ARGUMENTS` is non-empty, treat it as the topic. If empty, ask the user via AskUserQuestion: `"What's the topic? (bug or enhancement, one sentence)"` — single-line question text, free-text answer. Then reset helper state and stamp topic + date:

```bash
.devforge/lib/research_helper reset-memo
.devforge/lib/research_helper reset-report
.devforge/lib/research_helper set-topic --value "<topic>"
.devforge/lib/research_helper set-verbatim-prompt --value "<full raw $ARGUMENTS>"
.devforge/lib/research_helper set-date --value $(date -u +%Y-%m-%d)
```

`reset-memo` + `reset-report` write fresh-defaults state. `set-topic` auto-derives `topic_slug` for the eventual filename. `set-date` enforces `YYYY-MM-DD`. `set-verbatim-prompt` persists the full original prompt the user passed to `/devforge:research` — the complete `$ARGUMENTS`, NOT the one-sentence topic `set-topic` records. `$ARGUMENTS` may carry a multi-sentence prompt (e.g. a symptom plus a trailing "Suspected cause:" hypothesis); the topic is a curated paraphrase, so the un-paraphrased boundary input would otherwise be lost after Phase 0.3. Persisting it here is what lets Phase 4's `finalize-handoff` carry it into the handoff as `Intent.verbatim_prompt`, so a downstream stage can tell what the user ACTUALLY asked from what this command INTERPRETED (per plan 18 Step 1). When `$ARGUMENTS` was empty and the topic came from the AskUserQuestion fallback above, pass that same user reply as `--value` — it is the verbatim input in that branch.

Fresh-every-run: `reset-memo` + `reset-report` ALWAYS run at Phase 0.3, unconditionally. Any prior `.devforge/research-state.json` + `.devforge/research-report.json` are overwritten with fresh defaults. `/devforge:research` does not resume mid-flight prior runs — every invocation starts clean. If the user killed a prior run mid-investigation, that work is lost; re-answer the rubric from scratch.

### Phase 0.4 — Suspected-cause classification (pre-rubric, runs before Phase 1)

A `/devforge:research` prompt often carries a mechanism guess alongside the symptom — a trailing "Suspected cause: …" clause (or an equivalent lead-in: "I think it's …", "probably because …", "root cause is …", "this is caused by …"). Scan the verbatim prompt persisted by `set-verbatim-prompt` for any such lead-in BEFORE the six-dimension rubric runs. A user- or research-supplied mechanism guess is a CLAIM TO DISPROVE, not a fact: it MUST NOT silently become the `desired` dimension, any other rubric dimension, or the eventual recommended approach. It belongs in the hypothesis lane.

When a suspected-cause clause is present, hold the verbatim mechanism text in working memory now (so it is not lost during the rubric) and carry it forward as one of the candidates Phase 2.5 enumerates. There is no pre-rubric setter for a standalone hypothesis — the suspected cause is persisted by the existing Phase 2.6 `record-hypothesis` call (which requires `--cause`, `--falsifier`, and `--runtime-probe-needed`), alongside the ≥2 enumerated candidates. The point of capturing it here is to guarantee the guessed mechanism enters Phase 2.5 as a hypothesis to disprove — with its own falsifier (the observation that would refute the guessed mechanism) — rather than bleeding into a rubric dimension. This pre-rubric classifier is the home Step 5's binary-classification gate routes `hypothesis` statements into (per plan 18 Step 5 — the user-facing front door over this same lane); treating the suspected cause as a falsifiable hypothesis is what makes it a typed, gate-detectable claim rather than free prose. The captured mechanism feeds Phase 2.5 hypothesis enumeration; it never enters `symptom` / `desired` or any rubric dimension.

When the prompt carries NO suspected-cause lead-in, this step is a no-op — proceed directly to Phase 0.5.

### Phase 0.5 — Intake-interrogation gate (user-facing front door, runs before Phase 1)

Phase 0.4 silently classified a suspected cause and held it in working memory for the hypothesis lane; Phase 0.5 is the USER-FACING front door over that same machinery. It surfaces the framework's interpretation of the verbatim prompt for ONE confirmation before the Phase 1 rubric commits investigation cost — this is the gate that closes the over-solve failure (plan 18 Step 5: in the original failure the user never saw, and so could never correct, the framework's interpretation). Phase 0.5 does NOT re-run Phase 0.4's detection logic — it reuses the detection decision Phase 0.4 made in working memory (the `hypothesis`-vs-`requirement` split) and adds the minimality challenge + echo-back + confirmation on top. Phase 0.5 Step 1 is where that decision is first persisted, via `record-intake-classification`; Phase 0.4 makes no helper call for the classification.

**PROPORTIONALITY (HARD requirement — not advice).** The gate is PROPORTIONATE, inheriting the same proportionality the Phase 1 rubric already carries (its turn caps + accept-gaps coverage exit). Auto-classify the easy parts; surface to the user ONLY the high-stakes ambiguities — conflations (a requirement mixed with a hypothesis), scope-expanders (an extra distinction or state not in the stated desired outcome), and big-design-driving hypotheses (a mechanism guess that would shape the architecture). It is NOT a 20-question inquisition. A clean prompt — no hypothesis, no scope-expander, one obvious minimal fix — passes with ONE echo-back confirmation and ZERO interrogation. Over-interrogating a trivial bug is itself the over-build failure mode this gate exists to fight.

#### Step 1 — Binary-classify each statement

Partition the verbatim prompt (the field `set-verbatim-prompt` persisted in Phase 0.3) into statements and classify each as one of TWO classes: `requirement` (the desired outcome — what the user asked for) vs `hypothesis` (a suspected cause or mechanism guess). Reuse Phase 0.4's detection: a `"Suspected cause:"` lead-in (or equivalent — "I think it's …", "probably because …", "root cause is …") was already detected there and held in working memory for the hypothesis lane; it will be persisted via `record-hypothesis` at Phase 2.6. Here that same statement is ALSO tagged `hypothesis` for the echo-back. Everything else is a `requirement`. Record each statement:

```bash
.devforge/lib/research_helper record-intake-classification \
    --statement "<the prompt statement, verbatim or lightly paraphrased>" \
    --kind <requirement|hypothesis> \
    --minimal-fix "<see Step 2 — pass on requirement statements>"
```

The setter is idempotent on `--statement`: re-recording the same statement overwrites its prior `--kind` + `--minimal-fix` (this is the mechanism the `correct` branch in Step 3 uses). `--kind` must be exactly `requirement` or `hypothesis` (the helper rejects any other value with exit 2). On a clean single-requirement prompt this is ONE call with `--kind requirement`; do not manufacture extra statements to classify.

#### Step 2 — Minimality challenge

Compose the SIMPLEST change that satisfies the stated desired outcome ALONE, and pass it as `--minimal-fix` on the requirement statement. Any addition beyond that simplest change — a guessed mechanism, an extra distinction, a new state — is an "extra" the user must CONSCIOUSLY opt into; it is never assumed into the minimal fix. Concretely for the trip-wire this gate exists to catch: a prompt whose desired outcome is "render an empty section plus an error toast on load failure, never leak the prior items" yields the minimal fix "branch the render on load-failure; show empty + toast" — with NO inline-items mechanism and NO empty-vs-failure split, because neither is in the stated desired outcome. `--minimal-fix` is optional on the setter (omit it on `hypothesis` statements — their minimal fix is "verify first", not a code change), but for the requirement statement carrying the desired outcome it is REQUIRED: it is the surface the user confirms or corrects.

#### Step 3 — Echo-back + ONE confirmation

Render the echo-back block and surface it for confirmation:

```bash
.devforge/lib/research_helper render-intake-echo
```

The helper owns the block shape — `## Intake interpretation` with a `### Requirements (what you asked for)` section (each requirement + its `Minimal scope:` line), a `### Hypotheses to verify — NOT requirements` section (omitted entirely when no hypothesis was classified — the proportionality rule), and a `### Minimal scope` section. The hypotheses section is where a suspected cause surfaces as "hypothesis to verify, not a requirement." Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) — this is the established verbatim-echo convention; the orchestrator does NOT re-shape the block.

Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]`. End the turn. The user's reply opens the next turn.

- On `confirm`: proceed to Phase 1.
- On `correct`: the user names what was misclassified (a statement that should flip `requirement`↔`hypothesis`, or a minimal fix that scoped too wide). Re-record the affected statement(s) via `record-intake-classification` (the idempotent overwrite on `--statement`), then re-run `render-intake-echo` and echo the corrected block ONCE more. Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]` (same options — this is the ONE bounded correction). End the turn. On the next reply: `confirm` → proceed to Phase 1; `correct` (or any other reply) → proceed to Phase 1 regardless. The gate allows AT MOST one correction pass — it does not loop, so even a second `correct` advances to Phase 1 rather than re-entering this branch.

When the prompt is a clean single-requirement bug with no hypothesis and one obvious minimal fix, Steps 1-2 are a single `record-intake-classification --kind requirement --minimal-fix "…"` call and Step 3 is one echo-back the user confirms in a single turn — zero interrogation, per the proportionality requirement above.

### Phase 0.6 — Re-entry from `/devforge:grill` (conditional — skip if no seed)

Before beginning the investigation, check for a `/devforge:grill` re-entry seed. Glob `specs/*/grill-seed.json`. If any matched file has a `target_stage` equal to `"research"` (this command's stage), you are re-entering from a `/devforge:grill` RE-ENTER-UPSTREAM verdict — the design-time grill proved a plan defect was rooted in THIS research investigation's conclusion, and the re-run must be DIRECTED so it does not re-derive the invalidated conclusion. Read that seed and treat it as a binding directive for this run. Read it DIRECTLY: parse the matched file's flat JSON inline — do NOT call any grill helper or `grill_helper` verb (the orchestrator reads the file itself, so this block stays valid even if `/devforge:grill` is ever removed). The seed carries these fields:

- `feature` — the feature this seed was emitted for; read it from the seed and state it up front in your re-entry message (do NOT infer it from the file path).
- `prior_conclusion` — what the previous research investigation concluded; it was invalidated, so do NOT re-derive it.
- `invalidating_evidence` — how `/devforge:grill` proved it wrong, grounded in the plan / spec / code.
- `must_satisfy` — what this re-run must now additionally satisfy; address it explicitly.
- `carried_findings` — prior findings to carry forward; stay monotonic (never re-surface a finding a prior pass already disproved).

**Attach mode (binds Phase 4).** The matched seed file's PARENT DIRECTORY is this feature's already-allocated feature directory — a `/devforge:grill` seed exists only for a feature that already has one. Record that directory path in working memory now as this run's `<feature_dir>`: on save, Phase 4 reuses it instead of allocating a new one, skips branch creation, and overwrites the artifacts in place. This is the one value you take from the seed's location rather than from its contents — the `feature` field above is still what you NAME in your messages; the parent directory is where you WRITE.

State up front in your first user-facing message that you are running in grill-re-entry mode for the named `feature`, and name how this run addresses `must_satisfy`. Then run Phases 1–4 normally, with the seed's directive constraining the investigation and Phase 4 saving in attach mode.

This block only READS the seed's directive. It does NOT delete the seed or change its `cycle_count` — seed lifecycle (deleting or incrementing `cycle_count` after consumption) is handled by the next `/devforge:grill` run, which reads `carried_findings` to stay monotonic. That is a v1 simplification; do not add seed-deletion logic here.

When no `specs/*/grill-seed.json` file matches `target_stage == "research"` (the normal case — a `/devforge:grill` run writes a seed only when it reaches a RE-ENTER-UPSTREAM recommendation AND the user picks the matching re-entry at its human gate, and most runs never reach one), this block is a no-op: proceed directly to Phase 1, and Phase 4 allocates a fresh feature directory on save.

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

### Design-reference capture (supplementary — non-gating)

Some enhancements target a UI surface with a design reference — an HTML export, a Figma node, or a screenshot — that expresses what the built UI should look like. Capture it here so that intent is recorded once at intake as a structured anchor rather than left in prose. Before the first dimension question, ask one supplementary free-text prompt: ``"Is there a design reference for this feature's UI — an HTML export, a Figma node, or a screenshot? If so, name the kind, the file path or URL, and which element selector(s) carry the intent (e.g. a class like `.fooBar`). If none, answer 'none'."`` — single-line question text, free-text answer. After the user replies:

- If the user names a reference, compose `--value` as `<scheme>:<target>` (`scheme` = `html` / `figma` / `screenshot` matching the named kind; `target` = the file path or URL) and `--selectors` as a JSON array of the named intent selectors:

  ```bash
  .devforge/lib/research_helper set-design-anchor \
      --value "html:design/reference.html" \
      --selectors '[".fooBar", ".badge"]'
  ```

- If the user names none (no reference, or the feature has no UI), record the empty anchor:

  ```bash
  .devforge/lib/research_helper set-design-anchor \
      --value "none" \
      --selectors '[]'
  ```

The helper validates `--value` as a design-source `scheme:target`; a value whose scheme is not one of `html` / `figma` / `screenshot` / `none` is rejected with a non-zero exit and nothing is persisted, so pass a well-formed `scheme:target` or the bare word `none`. This capture is OPTIONAL and is NOT one of the six rubric dimensions above — it does not participate in the coverage check or `symptom-finalize`, so an unanswered design-reference question never blocks finalization. This call does NOT gate progression. Advance to the pre-rubric docs scan regardless of the user's answer.

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

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift, refinement, and mode-flip classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns within the same `/devforge:research` run by reading prior assistant messages in the conversation.

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

Ask via AskUserQuestion `"Investigation will scan roughly <N> CBM calls. Proceed?"` with options `["proceed", "cancel"]`. On `cancel`: copy a one-line note ("Investigation cancelled. Re-run /devforge:research from scratch when ready — prior state will be overwritten.") into the user-facing message and end the turn. On `proceed`: continue.

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

   **Surface-count frame (when the ticket names a specific surface).** When the ticket names a specific UI surface, screen, or tab (e.g. "on the 'Suggested' search", "in the dealer modal"), you MUST evaluate a surface-count frame as one of the candidates here: "the named surface is NOT the only entry point — other surfaces reach the same shared symbol," with falsifier = the inbound `trace_path` of that shared symbol. If a different framing wins the runner-up slot, that is fine — no second recorded frame is required, because the surface-count question is still mechanically probed downstream by Phase 2.4c's caller enumeration + Step 2b's per-caller surface trace.

3. **Identify the CONCRETE FALSIFIER** — the specific evidence that would prove the alternative framing OVER the primary. Phase 2.4 / 2.4b / 2.4c searches will probe FOR this evidence.

4. **Rate `confidence_vs_primary`** as one of `lower` / `comparable` / `higher` relative to the primary framing.

5. **Record via:**

   ```bash
   .devforge/lib/research_helper record-runner-up-framing \
       --frame "<one-sentence alternative root cause>" \
       --falsifier "<concrete evidence that would confirm THIS framing over the primary>" \
       --confidence-vs-primary "lower|comparable|higher"
   ```

   ONE call per `/devforge:research` run. Re-calling overwrites (last call wins).

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

### Phase 2.4c — Helper-API surface enumeration (MANDATORY — mode-independent)

Helper-API surface enumeration runs once per framing recorded in Phase 2.3b. The runner-up frame may surface different fix-path helpers than the primary — the two frames imply different layer-stack entry points. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

Without this step the LLM anchors on view-layer / minimal-change fixes when the helper layer already has the inputs to enforce an invariant. Phase 2.4c forces structural evidence — inbound callers, dead siblings, consumer-chain endpoints — onto the report before Phase 3 enumerates approaches.

**Definition of "fix-path helper".** A helper whose signature carries the symptom value, or any value the symptom value derives from.

**Stopping rule (layer-boundary, NOT same-package).** Trace AT MOST 2 layer boundaries above the symptom site, following the dependency-inversion direction (outer-to-inner; e.g., presentation-layer file → composable/store → domain helper → entity static; presentation → application → domain). Stop at framework/vendor packages (do not trace into framework internals, vendored SDKs, or shared utility libs). Cross application/domain package boundaries within the project workspace — this is the explicit point of the rule. The OLD same-package restriction is removed: cross-package traces within the project are NOT just allowed, they are REQUIRED when the symptom lives in a presentation-layer file (Vue / React component, view, page). Verify check 8b enforces this on every run (mode-independent): when the primary finding's `file:line` resolves to a presentation-layer path AND `fix_path_helpers` is non-empty with every entry's `file_line` in the same package as the symptom, `verify` exits non-zero with a `cross-layer rule` violation. Domain-layer symptoms (a bug whose symptom site is already inside `pkg-<domain>/`) remain same-package OK — no cross-layer trace is required for domain-internal bugs because the helper layer is already the symptom layer.

For each fix-path helper, run the steps below in order.

**Step 1 — Record the helper itself.** Run `search_graph(label="Method", qn_pattern="<helper QN>")` (or `label="Function"` / `label="Class"` per the helper's kind) to confirm the helper exists in the codebase index and to capture its definition `file_path:line`. Both the helper's qualified name AND its definition `file:line` are required:

```bash
.devforge/lib/research_helper record-fix-path-helper \
    --helper-qn "<helper qualified name>" \
    --file-line "<helper definition file_path:line>"
```

`--file-line` MUST be copied verbatim from the `search_graph` result row's `file_path` + `line` fields — this is where the helper itself is DEFINED, NOT where it is CALLED FROM. The setter rejects the `(none)` sentinel for `--file-line` because layer-boundary detection requires a real path. The setter is dedupe-on-append: re-recording the same `--helper-qn` is a no-op (the existing `--file-line` is preserved). The setter also exits 2 when a no-shared-callers justification is already recorded — recording a helper contradicts that justification, and the two are mutually exclusive; see **No-shared-callers escape** at the end of this phase.

**Anchor gate (Patch 5).** `--file-line` MUST also anchor to at least one already-recorded `findings[]` row's `--file-line` — either exact match OR same path with line number within ±5 (lenient to absorb minor CBM/trace offsets). This forces every fix-path helper to start from CBM evidence already in the report, not an invented file location. Recording sequence: run Phase 2.3 + 2.4 + 2.4b FIRST (which calls `record-finding` repeatedly), THEN Phase 2.4c (which calls `record-fix-path-helper`). When the helper has no anchoring finding, the setter exits with code 2 and stderr `record-fix-path-helper: --file-line <X> does not anchor to any recorded finding (no finding's file_line collides — exact match or same path within ±5 lines).` plus the current set of finding file_lines for reference.

**Sticky-reject (anti-adversarial).** Once a `(helper_qn, file_line)` pair is rejected by the anchor gate, the setter records it in `helper_rejection_log` and refuses ALL future retries of the same pair, even if a finding at that file_line is recorded post-hoc. This closes the adversarial path where the LLM would record a fabricated finding to unblock a rejected helper. Stderr: `record-fix-path-helper: this (helper_qn, file_line) combo was previously rejected as unanchored (...); cannot retry even if findings now contain a collision (sticky-reject closes the post-hoc-anchor adversarial path).` Workarounds (in order): (a) pick a DIFFERENT `--file-line` for the same helper that anchors to a finding AT THE TIME OF THE NEW CALL; (b) restart `/devforge:research` from scratch to clear rejection state. Note: changing the `--helper-qn` alone does NOT unblock — the anchor gate fires on the unanchored `--file-line` regardless of QN, so a new QN at the same unanchored file_line gets its own rejection log entry without making progress. Verify check 14 mirrors the anchor rule at verify time — catches direct-state-mutation bypass attempts.

**Recovery on anchor rejection.** When the helper rejects with the "does not anchor" stderr, copy the stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Then either (a) return to Phase 2.3 / 2.4 to record the missing finding via `record-finding` FIRST + then call `record-fix-path-helper` with a DIFFERENT `--file-line` (the original combo is sticky-rejected — pick a closer-anchored helper site instead), or (b) reconsider whether the helper QN is the right fix-path target — if Phase 2.4c surfaced it via `trace_path` inbound walk, the trace_path result row's own `file_path:line` is the helper's call-site (which should already be in findings); re-anchor to that.

**Step 2 — Inbound caller enumeration + declared total.**

```
trace_path(<helper_qn>, mode=calls, direction=inbound)
```

Run the trace at depth 1. Before counting anything, **verify the result belongs to THIS helper.** `trace_path` keys on the BARE function name, so for a name shared by two functions it can silently return the OTHER symbol's callers with no error — a wrong-symbol trace yields a confidently wrong total. The result rows carry the CALLERS' qualified names, not the helper's, so you cannot match rows against the helper QN directly. Sanity-check with what you already know instead: the caller that LED you to this helper (typically the symptom site's function, whose call site is already in your findings) must appear among the returned rows. If it does not, or the returned callers' packages are implausible for the helper's recorded definition `file:line`, assume the trace resolved a different same-named symbol: confirm uniqueness via `search_graph(label="<the helper's kind, as in Step 1>", qn_pattern="<helper QN>")`, discard the ENTIRE result set (never filter per-row), and re-derive the callers via `search_code` on the helper's call sites before declaring any total.

**Declare the caller total** — the number of inbound caller rows the trace returned for this helper, including the symptom site's own function when it appears as a caller:

```bash
.devforge/lib/research_helper declare-caller-total \
    --helper-qn "<helper_qn>" \
    --total <N>
```

`<N>` is that verified row count. This counting rule — inbound rows at depth 1, symptom site included when it appears — is pinned verbatim in the setter's `--help`; declare `--total` against exactly that rule so the check-9 comparison is honest. `--helper-qn` must match a helper already recorded via Step 1 (the setter rejects an unrecorded QN with exit 2).

**Record EVERY caller** (including the symptom site itself) via:

```bash
.devforge/lib/research_helper record-inbound-caller \
    --helper-qn "<helper_qn>" \
    --caller-qn "<caller_qn>" \
    --file-line "<path:line>"
```

The Phase 2.3 `file:line` grounding rule applies — `<path:line>` MUST be copied verbatim from the `trace_path` result row's `file_path` + `line` fields. Never reconstruct. The recorded row count for this helper must EQUAL the declared total; check 9 rejects a mismatch (see the gates block below).

**Step 2b — Trace each caller to its surface and classify scope.**

Enumeration only puts callers on the table; it does not say which ones the change actually touches. For EACH caller recorded in Step 2, trace UP toward its user-facing entry point, then classify it in- or out-of-scope with a justification.

Trace up from the caller:

```
trace_path(<caller_qn>, mode=calls, direction=inbound)
```

Follow the inbound chain until the first user-facing entry point — a component, route, view, or CLI command — surfaces, bounded at 8 hops (whichever comes first). The empirically-validated chain for the seed incident was depth ≤ 6; if no entry point surfaces within 8 hops, use surface `"none"` and state in the justification how far the trace got. A caller genuinely not reachable from any user-facing surface (a pure internal utility, test-only code) also takes surface `"none"` — the bare word `none`, NOT the parenthesized `(none)` sentinel used elsewhere in this file; the setter accepts any non-empty string, so a mistyped `(none)` would persist silently.

Then classify the caller:

```bash
.devforge/lib/research_helper classify-caller-scope \
    --helper-qn "<helper_qn>" \
    --caller-qn "<caller_qn>" \
    --surface "<user-facing entry point, or none for a caller not reachable from any surface>" \
    --scope <in|out> \
    --justification "<why this caller is or is not affected by the change>"
```

The `(helper_qn, caller_qn)` pair MUST already exist from Step 2 — the setter rejects an unrecorded pair with exit 2. `--surface` and `--justification` must be non-empty; `--scope` is exactly `in` or `out`. When an entry point WAS found, the `--justification` MUST cite it by name — that is what converts "X is a caller" into "X is reachable from surface Y, therefore in/out of scope."

**Where the `--surface` value comes from.** Derive it from the caller's CONSTRUCTION SITES — the code that builds, mounts, or registers that caller, and the dependencies it is built with. The upward trace this step already runs supplies the hops, within the same 8-hop bound; the construction evidence is read at those hops through the CBM chain — `get_code_snippet` on the hop's `file:line`, plus `search_code` for a literal from it when the snippet leaves the construction relationship unclear. A label taken from the name of a lane, tab, route, or mode the caller RESEMBLES is not derived, it is a guess, and nothing downstream can tell the two apart: Phase 3's emission matrix reads this value as context for the row's Note, and every later stage that reads these caller rows inherits the label as a traced fact. When the construction sites do not surface within that bound, do not fall back to the nearest plausible name — take surface `"none"` per the rule above and record in the `--justification` what the trace covered and what blocked it, the same shape the not-reachable case uses.

**Honesty bound.** This gate forces the classification + justification to EXIST for every caller; it cannot force the in/out call to be CORRECT. Likewise check 19 forces `--surface` to exist (non-empty); it cannot force the label to have been genuinely derived from construction sites rather than guessed. Correctness stays your judgment on both counts and is audited downstream — at `/devforge:plan`'s architect consult (sub-question 7) and by the human.

Verify check 19 enforces this: every `inbound_callers` row must carry a non-empty surface, a scope ∈ {in, out}, and a non-empty justification. On non-zero exit from `verify` citing check 19, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then classify the missing caller(s) via `classify-caller-scope` before re-running `verify`.

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

**MANDATORY — mode-independent.** This phase runs on EVERY `/devforge:research` run — bug or enhancement alike, however the mode was determined (auto-detected from symptom tokens, or picked by the user when detection was ambiguous). The helper's `verify` step enforces four gates on Phase 2.4c state:

- **Check 8 (mode-independent)** rejects a report whose `fix_path_helpers` list is empty AND that carries no no-shared-callers justification. Two remedies satisfy it: enumerate at least one fix-path helper via Steps 1-2 above, OR record the justification described in **No-shared-callers escape** below. `verify` separately rejects the contradictory state where BOTH the list and the justification are set; its stderr names the recovery — `reset-report`, then re-record via exactly one of the two paths.
- **Check 8b (mode-independent)** — the cross-layer rule documented in the Stopping rule above — rejects a NON-EMPTY list where every `fix_path_helpers[].file_line` is in the same package as the primary symptom's file path when that symptom path is presentation-layer (Vue / React / views). It cannot fire on the justification escape, which leaves the list empty.
- **Check 9 (mode-independent)** rejects a helper that has no declared caller total, and rejects a helper whose recorded `inbound_callers` row count does not equal its declared total — for every helper recorded, in any mode. Remedy: declare the total via `declare-caller-total` (Step 2), then record every missing caller via `record-inbound-caller`; if the declared total was itself wrong, re-run the Step 2 trace and re-declare. It is vacuous when the list is empty.
- **Check 19 (mode-independent)** rejects any recorded `inbound_callers` row that Step 2b did not scope-classify — every caller must carry a non-empty surface, a scope ∈ {in, out}, and a non-empty justification. Remedy: run `classify-caller-scope` for each unclassified caller. It is vacuous when no caller was recorded.

On non-zero exit from `verify` citing any of these checks, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then return to Phase 2.4c and complete the missing steps before re-running `verify`. For check 8b specifically, the fix is to trace one helper UP through a package boundary (presentation → application or presentation → domain) and re-run Step 1 with that helper's qualified name and definition `file:line`.

**No-shared-callers escape (check 8's auditable skip).** Record a justification ONLY when the investigation has confirmed the change touches no existing shared symbol with other callers — the canonical case is a change that is purely additive in a new module, so there is no inbound caller to enumerate. It is not a shortcut for an enumeration you did not run: the prose is the audit trail a reader uses to judge that claim, so give the concrete reason (what the change adds, and why nothing existing calls into it).

```bash
.devforge/lib/research_helper record-no-shared-callers-justification \
    --justification "<concrete reason this change has zero shared callers to enumerate>"
```

`--justification` is required and must be non-empty — an empty or whitespace-only value exits 2 with `research_helper: no_shared_callers_justification: value cannot be empty`. Re-calling overwrites the prior text (last-write-wins). The justification and the helper list are mutually exclusive, and each setter refuses the contradiction from its own side:

- `record-no-shared-callers-justification` exits 2 when `fix_path_helpers` is already non-empty — a recorded helper means shared-caller enumeration is already in flight, so check 8 is satisfied by that helper plus its `inbound_callers` rows and no justification is accepted.
- `record-fix-path-helper` exits 2 when a justification is already recorded. Its stderr names the two forward paths: run `reset-report` and re-record if the justification was premature, or reconsider whether this helper is a false positive.

On either exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then take exactly one of the two paths — do not retry the rejected setter unchanged.

### Phase 2.4d — Click-handler-to-write-boundary trace (MANDATORY when bug mode + presentation-layer symptom)

Phase 2.4c surfaces helper-API surfaces; it does NOT force the LLM to read intermediate transformers/adapters/mappers that sit BETWEEN the user-action handler and the write-boundary call. Adapter functions advertise shape conversion via their names (`adapter`, `mapper`, `transformer`) and the LLM treats them as identity-preserving on the values they pass through — so a function that silently rewrites `id` to `Math.floor(10000 + Math.random() * 90000)` looks like a no-op from outside and gets skipped. Phase 2.4d closes that gap by forcing end-to-end reads of every intermediate on the call chain from handler to write-boundary.

**Gate.** This phase is MANDATORY when `memo.mode == "bug"` AND the primary finding's `file_line` resolves to a presentation-layer path (Vue / React / views — same `_is_presentation_layer` heuristic check 8b uses). Skip when: (bug mode AND primary finding is a domain-layer path) OR (enhancement mode regardless of layer).

**Step 1 — Identify the user-action handler.** The function on the symptom file that fires on the user's repro action (click handler, form submit, input change). Source: `repro_or_current` dimension prose + the `affected_area` file path. Run `search_code` for event-binding tokens in the symptom file:

```
search_code(pattern="@click=|onClick=|addEventListener|v-on:|onPress|onPanResponderMove|hx-on::|dispatchEvent|useClickHandler|useEventListener")
```

Pick the function bound to the user-action event. Record its qualified name.

**Heuristic-fragility fallback.** If no handler token is found via the `search_code` sweep (dynamic event binding with variable event type, composable-wrapped binding, framework-specific syntax not in the token list, programmatic dispatch), ask the user ONE direct prompt: *"I couldn't auto-detect the click/event handler that triggers the bug from the symptom file. Which function or method handles the user action that reproduces the bug? (give a function name or `file:line`)"*. Wait for the user answer, then proceed. Do NOT guess. Do NOT skip Phase 2.4d on heuristic miss — the user-fallback is the recovery path.

**Step 2 — Identify the write-boundary call.** The function the handler eventually calls that PERSISTS the operation. Write-boundary token list (covers REST + Redux + repository + WebSocket + GraphQL + IndexedDB + SSE + message-bus + Apollo cache + state-management actions):

```
addLine|dispatch|commit|mutate|mutation|repo.save|*.put|*.post|*.create|*.update|*.emit|*.send|*.publish|cache.writeQuery|cache.writeFragment|store.put|tx.add|tx.put|.dispatchEvent|eventBus.emit|bus.publish
```

Run `search_code` for those tokens in the symptom file. Pick the call whose receiver name matches one of the tokens AND whose argument list visibly carries the symptom value (the value cited in `memo.dimensions.symptom` or `memo.dimensions.desired`). Record its qualified name. If no token matches (project uses non-conventional write-boundary verbs not on the list — e.g., `tellSaga`, `enqueueWork`, `requestSync`), ask the user ONE direct prompt: *"I couldn't auto-detect the write-boundary call (the function that persists the operation) from the symptom file. Which function in the call chain actually persists the change? (give a function name or `file:line`)"*. Wait for the user answer, then proceed.

**Step 3 — Trace handler → write-boundary.** Run:

```
trace_path(<handler_qn>, mode=calls, direction=outbound)
```

Record the full path of intermediate function QNs (everything between the handler and the write-boundary call, exclusive on both ends). Use `mode=calls` always — CBM's `mode=data_flow` returns identical hop lists to `mode=calls` for first-party project code (pre-flight verified 2026-05-18) and provides no incremental signal.

**Handler-not-a-graph-node fallback.** Vue / SFC template files emit only File and Module nodes in the CBM graph — the handler defined in `<script setup>` may not resolve as a Function node. If `trace_path` returns empty OR `search_graph(name_pattern="<handler_name>")` returns 0 results, ask the user ONE direct prompt: *"I couldn't trace from `<handler>` to a write-boundary call via the code graph (Vue/template files often aren't indexed at function granularity). What intermediate functions does the handler call before reaching the persistence call? (list function names or `file:line` references)"*. Wait for the user answer, then proceed with the user-supplied chain.

**Step 4 — Read each intermediate end-to-end + record findings.** For EACH intermediate function on the path (excluding the handler and the write-boundary themselves), apply two cumulative filters to decide whether to call `get_code_snippet`:

1. **First-party filter.** Skip functions whose source file is in framework / vendor / SDK packages (Vue runtime, Pinia store internals, BLoC infrastructure, `node_modules/*`, `@vue/*`, `@pinia/*`). Read only first-party project workspace files.
2. **Shape-conversion-name filter (priority hint).** Preferentially read functions whose name matches a shape-conversion pattern (case-insensitive substring): `adapter|mapper|transformer|normalizer|converter|serializer|deserializer|encoder|decoder|wrapper|builder|formatter|parser`. These names advertise shape conversion but commonly hide value mutation. Pure-passthrough functions (handlers / dispatchers / forwarders whose names do NOT match the pattern) may be skipped at LLM discretion when the file body is large. The filter is a HINT, not a hard gate — when in doubt, read.

For each function read, look for value-mutation patterns: `Math.random`, `crypto.random`, `Date.now`, `uuid()`, manual id reassignment (`item.id = ...`, `obj[...] = ...`), `structuredClone` / destructuring that loses fields, type-coercion that drops precision.

Then record EACH intermediate function as a Finding row via:

```bash
.devforge/lib/research_helper record-finding \
    --surface "data-flow intermediate: <one-line role>" \
    --file-line "<path:line>" \
    --relevance "<one-line note — include the intermediate's qualified name here (or in --surface)>" \
    --framing "primary" \
    --rests-on-literal "<path:line>|none"
```

Answer `--rests-on-literal` on this call as on every other `record-finding` call — Phase 2.6 defines what it answers, and check 20 rejects the report when any finding leaves it unanswered. An intermediate that merely passes a value through answers `none`; one whose hardcoded literal is the grounds for calling the chain dead or live answers that literal's `file:line`.

Either the `--relevance` or `--surface` text MUST contain the intermediate's qualified name as a substring — the `record-data-flow-chain` setter substring-matches each `intermediate_qns[i]` against existing findings' `relevance` AND `surface` fields and rejects intermediates with no referencing finding. Inline-call expressions also count as intermediates: when the write-boundary call argument list contains a function call expression (not just identifier passthrough), the call expression's callee MUST be added to `intermediate_qns` as well.

**Step 5 — Persist the chain.** After every intermediate has a recorded Finding:

```bash
.devforge/lib/research_helper record-data-flow-chain \
    --handler-qn "<handler qualified name>" \
    --write-boundary-qn "<write-boundary qualified name>" \
    --intermediate-qns '["<intermediate_qn_1>", "<intermediate_qn_2>", ...]'
```

`--intermediate-qns '[]'` is valid (direct handler→write-boundary call with no intermediates). The setter validates each intermediate_qn against existing findings; if any intermediate has no referencing Finding, the setter exits with code 2 — copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), record the missing Finding via `record-finding` first, then re-run `record-data-flow-chain`. Last-write-wins on subsequent calls.

**Verify enforcement.** The helper's `verify` step adds check 15: when bug mode + presentation-layer primary symptom, `data_flow_chain` must be non-null. On non-zero exit from `verify` citing check 15, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then return to Phase 2.4d Step 1 to complete the missing trace.

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
    --evidence "<text — typically a file:line or consumer name>" \
    --stable-across-calls <true|false|unknown>     # REQUIRED when --classification invariant
```

**`--stable-across-calls` (stability axis — REQUIRED for invariant).** A value being invariant by KIND (an `id`, a contract field, a payload-shape token) does NOT imply the value is STABLE across calls. An adapter / transformer / mapper between the user-action handler and the write-boundary may reassign the value per call (`Math.random()`, `Date.now()`, `uuid()`, manual id reassignment). The kind axis and the stability axis are independent — an invariant id that is randomized per call still satisfies "invariant by kind" but breaks any downstream comparator that expects stability.

Pass `--stable-across-calls true` when Phase 2.4d's data-flow chain shows every intermediate is identity-preserving on the value (no `Math.random` / `Date.now` / manual reassignment in any intermediate body). Pass `--stable-across-calls false` when at least one intermediate rewrites the value (and call `record-value-production-site` for the rewriter site FIRST — see below). Pass `--stable-across-calls unknown` ONLY when the symptom is domain-layer (no presentation-layer trace path applies); the helper REJECTS `unknown` for presentation-layer symptoms because Phase 2.4d's data-flow chain (already recorded) provides the structural evidence to investigate.

**Helper gates on `set-value-semantics --classification invariant`.** Four independent rejections (evaluated in this order — first failing gate emits the rejection):

1. `--stable-across-calls` is required — exit 2 if omitted.
2. `--stable-across-calls unknown` AND symptom is presentation-layer — exit 2 with: investigate the production site via Phase 2.4d data-flow chain (already recorded) before classifying.
3. No `consumer_chain` row for `--value` — exit 2 (unchanged from prior phase). Recovery: return to Phase 2.4c Step 4 and call `record-consumer-chain` first.
4. `--stable-across-calls false` requires at least one `value_production_sites` row for `--value` — exit 2. Recovery: call `record-value-production-site` first.

On any exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The helper writes nothing on rejection — the state file is untouched.

**Production-site recording (required before `--stable-across-calls false`).** When Phase 2.4d's intermediate-trace reveals a rewriter (an intermediate function whose body contains `Math.random`, `crypto.random`, `Date.now`, `uuid()`, or a manual id reassignment), record the rewriter site:

```bash
.devforge/lib/research_helper record-value-production-site \
    --value "<symbol>" \
    --file-line "<rewriter file:line — the exact line where the value is assigned/computed>" \
    --is-stable <true|false>
```

The setter is append-only with `(value, file_line)` distinct dedupe. A single value may have MULTIPLE production sites (e.g., three adapters all rewriting the same id field — record each via a separate call with distinct `--file-line`). The setter rejects the `(none)` sentinel — production site must be a real path. `--is-stable false` flags a randomization site (the value differs across calls — e.g., `Math.random`, `Date.now`, `uuid()`); `--is-stable true` flags a deterministic reassignment site (the value is reassigned but produces the same output for the same input — e.g., a normalization helper, a hash function, an enum-coercion).

Why this matters: an invariant value mis-classified as preference produces hypotheses framed "the UI didn't seed correctly" — wrong framing leads to view-layer fix recommendations in Phase 3. A stable-but-unstable invariant value mis-classified as just "invariant by kind" produces hypotheses framed "id field-name mismatch" or "type coercion" — wrong framing leads to comparator fixes in the symptom file while the actual rewriter at the production site continues to randomize the id every call. Classification + stability ground hypothesis enumeration in the right semantics.

Enumerate at least 2 candidate root causes for the symptom. For each, write a one-line falsifier (the observation that would disprove it) and mark whether falsification needs runtime data. Single-hypothesis output is rejected by the helper's `verify` gate.

**Hypothesis-citation gate (check 16).** In bug mode, when any `value_semantics` row has `--stable-across-calls false` (recorded above), at least one `record-hypothesis --cause` text MUST contain a `value_production_sites[].file_line` for one of those unstable values as a substring (word-boundary match on the `:line` suffix — `src/foo.ts:5` does NOT match `src/foo.ts:50`). The helper's `verify` step (check 16) exits with code 2 when no hypothesis cites any production-site file_line — the LLM must enumerate the production-site rewriter as a candidate root cause. Enhancement mode skips check 16 (no production-site-rewriter root cause enumeration is required). On exit 2 in bug mode, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then add a hypothesis whose `--cause` text references the production-site `file:line` literally (e.g., `--cause "id is randomized per-call at src/helpers/widgetFamilyToItemAdapters.ts:5 via Math.random()"`).

For any hypothesis whose falsifier needs runtime data (lifecycle race, framework lifecycle gap, vendor side-effect, network-shaped issue, timing-shaped issue), prepare a specific probe — a `console.log` probe, an `app.config.warnHandler` capture, a network-tab inspection, a breakpoint dump, etc.

### Phase 2.5b — Literal archaeology (MANDATORY when the investigation points at a hardcoded literal — mode-independent)

Phase 2.5 classifies value semantics + stability for symbols. It does NOT examine WHY a primitive literal exists where the investigation found it. A hardcoded `false` / `0` / `null` / `"string"` anywhere the investigation leans on it has historical intent — placeholder, migrated from a legacy system, deliberate policy, forgotten across a later policy change, inherited verbatim by a refactor, or generated. Without that classification the literal's CURRENT value is read as its INTENDED value, and that misreads in two directions.

When the recommendation REPLACES the literal, the LLM treats it as "the bug" and proposes literal-replacement at the call site — the wrong fix layer when intent ∈ {placeholder, forgotten, inherited-refactor} (the default-source belongs upstream: wrapper signature, state-init factory, or use-case default). When the recommendation instead REASONS FROM the literal — "the flag is hardcoded `false`, so this chain is dead"; "its only caller passes `true`, so this prop is live" — a scope call (dead vs live, in vs out of scope, keep vs delete) rests on a value that may have stopped meaning what it says the moment a later commit restructured around it without touching it. That second shape replaces nothing, so no fix layer is at stake; what is at stake is whether the literal is evidence at all.

**Trigger.** Run Phase 2.5b when ANY of the following hold: (1) Phase 2.4d's data-flow chain trace reveals a hardcoded primitive literal at a finding's `file_line` (one of the intermediate functions passes or assigns the literal rather than a variable) — this arm presupposes Phase 2.4d ran, and that phase's own Gate restricts it to bug mode with a presentation-layer symptom, so arm (1) cannot fire in an enhancement run; (2) the Phase 3 recommended approach you are about to draft will replace a primitive literal with a different value; (3) a finding's or a conclusion's grounds cite the VALUE of a primitive literal as the basis for a scope call — dead vs live, in vs out of scope, keep vs delete — where the plan is to delete or to keep the surrounding code, never to replace that value. Arms (2) and (3) carry no mode condition: both fire in bug and enhancement runs alike, and only arm (1)'s upstream trace is mode-restricted. When in doubt, run Phase 2.5b — check 17 fires at verify if the approach replaces a literal and archaeology was skipped, and check 20 fires if a finding names a literal its conclusion rests on and archaeology was skipped. "Primitive literal" = JS/TS `true|false`, Python `True|False`, `null|undefined|None`, decimal / hex / BigInt / scientific number, single-quoted / double-quoted / backtick-template string. Array / object / regex / function literals are OUT OF SCOPE — record them as ordinary findings instead.

**Steps.** Run the git commands below against the repository that holds the code under investigation — in a wrapper-mode install that is the nested Source Root, not the install root, and querying the wrong root returns an empty history indistinguishable from a literal that genuinely has no prior life. Confirm which repository you are querying before trusting a result; no step in this command resolves that root for you. Step 4's forward sweep runs one such query per path and is exposed the same way, more sharply: its clean result — nothing found since the introducing commit — is character-for-character what the wrong root returns for every path handed to it, and it is a result you would otherwise read as reassuring. Settle the root once, before the first git command below, and treat every empty result in this phase as unread until you have.

1. **Find the introducing commit.** Run `git log -S "<literal>" -- <file>` with `<literal>` quoted (escape shell metacharacters). The introducing commit is the OLDEST commit whose diff added the literal (last entry in the log output); anchor on it. That anchor is where the history window STARTS, not where it ends — step 4 sweeps forward from it to `HEAD`. Any newer entry in this same log already falls inside that forward window, so do not re-anchor on one.

2. **Read the commit subject.** Run `git show --stat <introducing-commit-sha>` to see the commit's subject line and which files it touched.

3. **Confirm author + date via blame.** Run `git blame -L <start>,<end> <file>` around the literal's line; the blame entry's author + date confirm the introducing-commit fingerprint.

4. **Sweep forward for commits that changed how the value is supplied.** Steps 1-3 establish how the literal got there. They cannot establish that it still means what it meant then. Sweep BOTH the literal's own file AND the file of EACH inbound caller enumerated at Phase 2.4c Step 2 — the window the anchor opened covers all of them, and a sweep of the literal's file alone, run without first checking whether that enumeration found any callers, reproduces the blind spot steps 1-3 already have. For each file in that set, run:

   ```bash
   git log <introducing-commit-sha>..HEAD -- <path>
   ```

   Read the subjects for commits that changed how this value is SUPPLIED: a prop removed from a parent, a default relocated to another layer, a flag stripped from a caller, a wrapper that stopped forwarding the argument. Open the diff (`git show <sha>`) for any subject that reads that way — the subject line is a filter, not the answer.

   Sweep the caller paths with the same attention as the literal's own file, and expect the caller paths to be where this pays: the commit that turns a literal into a leftover frequently never touches the literal, its line, or its file at all. It removes whatever used to supply a different value, one layer up, and the literal it strands still reads exactly as considered as it did the day it was written.

   When Phase 2.4c recorded no inbound callers — the no-shared-callers justification is the sanctioned route to that state, and not the only way a report reaches it — the sweep covers the literal's own file alone. That is a narrower sweep than a caller-bearing one and the carrier below cannot express the difference — an `[]` from a one-path sweep is indistinguishable from an `[]` that cleared five caller files — so note the narrowing in the recommended-approach `--rationale`, the one free-text field that exists on every run. When step 1 could not identify an introducing commit at all (the fallback at the end of this phase), there is no anchor to sweep forward from and the sweep does not run; that is the "not swept" state described in step 6, not a clean one.

   Record the outcome in step 6 and nothing more. What this sweep produces — evidence for step 5's classification, for the scope call the report will carry, and a record of how far you actually looked — exists only if you run it in full: the diligence is yours alone to supply, since no check forces this sweep to run and none can tell a thorough sweep from a cursory one. What the sweep's RESULT does not do is gate where the investigation goes next: finding a supply-changing commit does not stop the investigation, and finding none does not clear the literal — a value can be stranded by a commit whose subject reads like anything at all, or by one in a file nobody enumerated.

5. **Classify intent.** Pick ONE of the 6 enum values:

   | Intent | When it applies |
   |---|---|
   | `placeholder` | Literal was a TODO / FIXME / temporary value (commit msg or surrounding code says "default for now", "TBD", etc.). |
   | `migrated` | Literal carried over from a legacy system (commit msg cites the migration; surrounding code references the legacy identifier). |
   | `deliberate` | Literal was a considered policy choice with rationale in the commit message (commit msg explains WHY this value). |
   | `forgotten` | Literal added during a feature intro but never updated when a later policy was added (commit msg introduces the feature; a later commit adds the policy without revisiting the literal). |
   | `inherited-refactor` | A later refactor preserved the literal verbatim while restructuring around it (commit msg describes structural change, not value change). |
   | `generated` | Literal lives in a generated file (path matches `**/generated/**` or `**/node_modules/**`, OR file header has an `AUTO-GENERATED` marker). |

6. **Record the archaeology.** Call:

   ```bash
   .devforge/lib/research_helper record-literal-archaeology \
       --literal "<literal as it appears in source>" \
       --file-line "<path:line>" \
       --introduced-by "<commit sha — 7 to 40 hex chars>" \
       --introduced-when "<YYYY-MM-DD>" \
       --commit-subject "<one-line subject from the commit>" \
       --intent <placeholder|migrated|deliberate|forgotten|inherited-refactor|generated> \
       --use <fix-layer|evidence> \
       --supply-changing-commits '[{"sha": "<7-40 hex>", "subject": "<one-line subject>"}]'
   ```

   The last line is the OPTIONAL step-4 carrier — omit that line entirely when the sweep did not run, pass `'[]'` when it ran and found nothing, and read the three-state rule below before choosing between those two.

   **`--use` (why this row is being recorded).** Pick the value from what the recommended approach DOES to the literal, never from how its summary is worded:

   - `fix-layer` — the approach REPLACES this literal with a different value, so after the fix something still supplies that value, at this site or at an upstream default-source. The per-intent recovery rule below is written for this use, and `finalize-handoff` requires the recommended approach's `--rationale` to name the escalation (it must contain `default`, `wrapper`, `caller`, or `escalat`) when the intent is `placeholder`, `forgotten`, or `inherited-refactor`.
   - `evidence` — the literal's VALUE is cited as grounds for a scope conclusion (typically that the code around it is dead, or that it is live), and the approach deletes or keeps that code without supplying any replacement value. This is the row trigger arm (3) calls for, and the per-intent evidence rule below is the one written for it. Nothing is being replaced, so there is no default-source to escalate and that `finalize-handoff` requirement does not apply to this row.

   When neither bullet plainly fits — a literal dropped as collateral of removing unrelated dead code, where that literal's own value is not what the approach's reasoning turns on — default to `fix-layer`. `fix-layer` is the branch a forcing function still checks; `evidence` silently exempts the row, so the safe default is the one that can still fail loudly.

   Both values are reachable on a run today, and each has a gate that compels the call. Check 17 matches the recommended approach's PROSE (`replace` / `change` / `swap` leading to `with` / `to` / `for`), not what the change actually does, so a deletion-shaped approach narrated with replacement idiom (`swap the literal true with removing the dead flag prop entirely`) reaches this setter and takes `--use evidence`. Check 20 compels the call from the other side: a finding that answered `--rests-on-literal` with a `file:line` (Phase 2.6) demands a row at that `file_line`, and such a row takes `--use evidence` whenever the approach deletes or keeps the code instead of replacing the value. Mis-tagging such a row as `fix-layer` re-arms the escalation-cite requirement above, and on a `placeholder` / `forgotten` / `inherited-refactor` intent `finalize-handoff` then fails at Phase 4 Step 4.6 — after the report is already written. No check downstream will catch a wrong `--use` value — check 17 matches on the literal and its `file_line`, check 20 on a row existing at the `file_line` the finding named, and neither reads the field. Get it right when you make the call; nothing after this point will.

   The setter dedupes on `(literal, file_line)` — re-recording the same pair is a no-op (first write wins on the `--intent`, `--use`, and `--supply-changing-commits` values alike). The setter rejects the `(none)` sentinel and unrecognized literal tokens. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

   **`--supply-changing-commits` (what step 4's sweep returned).** Optional, and its three states are NOT interchangeable:

   - **Flag omitted entirely** — the sweep did not run for this literal. A normal outcome; nothing penalizes it, and it is the honest answer whenever step 4 had no anchor to sweep from or you did not get to it.
   - **`'[]'`** — the sweep RAN, over the literal's file and every caller file it covered, and found no commit that changed how the value is supplied.
   - **Populated** — a JSON array of `{"sha": "...", "subject": "..."}` objects, one per commit the sweep found. `sha` is 7-40 hex characters, `subject` is that commit's one-line subject, and no other key is accepted in an element.

   Omitting the flag and passing `'[]'` are different claims and must never be conflated: "nobody looked" is not "somebody looked and it was clean". The rendered report keeps them visibly apart — `not swept` against `no supply-changing commits since the introducing commit` — under its own `### Supply-changing commits since introduction` heading, and that line is what a human reviewer reads to tell an unexamined literal from an examined one. Collapsing the two costs a reader the only signal that distinction carries.

   Pass this flag on the SAME `record-literal-archaeology` call that carries the intent. The dedupe rule above means a second call for the same `(literal, file_line)` returns 0 and writes nothing, with no message on stderr — so a sweep result sent in a follow-up call is discarded, silently, and the row keeps reading `not swept` forever. There is no amend and no repair verb for this field: if step 4 is still outstanding when you reach this step, finish it before making the call rather than recording the row now and intending to correct it.

**Per-intent recovery rule — `--use fix-layer` rows (drives Phase 3's recommended-approach drafting).**

- `intent ∈ {placeholder, forgotten, inherited-refactor}` → the fix layer is NOT the literal site. Escalate the default-source one layer up: literal at a call-site → default at the wrapper signature; literal at state init → default at the state-init factory function; literal in a use-case caller → default in the use-case method signature. Phase 3 must propose the upstream default, not literal replacement at the call site.
- `intent == migrated` → investigate the legacy system's behavior for the SAME literal before recommending. The legacy version likely had a different default OR an upstream policy that the migration dropped. Surface the legacy gap in Phase 3's rationale.
- `intent == deliberate` → literal replacement may be the right fix (LLM's instinct was correct), BUT the archaeology row + commit-msg cite are REQUIRED to justify overriding a documented deliberate choice. Phase 3 rationale must cite the introducing commit by SHA + subject.
- `intent == generated` → fix layer is the generator template, not the consumer. Trace back to the template file; propose the change there. Phase 3 should NOT recommend editing the generated file.

**Per-intent evidence rule — `--use evidence` rows (drives what a scope conclusion may rest on).** This block answers a different question from the fix-layer rules above — not "where does the fix belong?" but "is this literal evidence of anything?" — so read it separately. Neither block substitutes for the other, and an `evidence` row takes only the rules here.

- `intent ∈ {placeholder, forgotten, inherited-refactor}` → the literal's current value is NOT evidence of intent. Any scope call resting on it must be RE-DERIVED from another source — the helper's inbound callers (Phase 2.4c Step 2), the surrounding code's own history, or a runtime probe — or DOWNGRADED in confidence in the report, naming the archaeology row as the reason for the downgrade. A literal a later refactor preserved verbatim describes what the code did BEFORE that refactor, not what it does now.
- `intent == deliberate` → what stands depends on what step 4's sweep returned, because a considered choice at introduction is a claim about the moment it was made and not about what the value means now. **Sweep found nothing (`[]`)** → Phase 3's rationale MUST cite the introducing commit by SHA + subject before the scope call may stand — the same evidentiary bar the `deliberate` fix-layer rule imposes on overriding one. **Sweep found a supply-changing commit** → that later commit, not the introducing one, is what decides whether the literal still describes anything live, and a deliberate introduction is exactly what a stranded value looks like; the classification no longer carries the scope call, so RE-DERIVE it as the first bullet requires or DOWNGRADE it in the report, citing the supply-changing commit by SHA + subject as the reason. **Sweep not run** → the row supports neither reading; run step 4, or record the scope call as resting on an unswept literal and downgrade it accordingly.
- `intent ∈ {migrated, generated}` → no evidence rule applies. The fix-layer rules above are the only ones written for these two intents, and they are inert when nothing is being replaced; record the row and proceed.

**Honesty bound.** Check 20 forces the archaeology row to EXIST for a literal a finding rests on; it cannot force the scope call drawn from that row to be CORRECT. Correctness stays your judgment, and the row is what lets a human audit it — the rendered report carries a Literal Archaeology section for exactly that reason.

**Helper verify check 17 (mode-independent).** When Phase 3 sets a recommended approach whose `--rationale` or whose linked approach's `--description` contains literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) and no `literal_archaeology` row exists for `<X>` at a recorded finding's `file_line`, `verify` exits with code 2 citing check 17 — in any mode. Recovery: run the steps above + `record-literal-archaeology`, then re-run `verify`.

**Helper verify check 20 (mode-independent).** Every `findings[]` row must answer `--rests-on-literal` (Phase 2.6), and a row that answers with a `file:line` rather than `none` requires a `literal_archaeology` row at that same `file_line`. In any mode, `verify` exits with code 2 citing check 20 when a finding leaves the field unanswered, or when it names a `file:line` that no archaeology row covers. On non-zero exit citing check 20, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then take the path the cited arm allows. For a named-but-uncovered `file:line`: run the steps above + `record-literal-archaeology` for that literal with `--use evidence`, then re-run `verify`. For an unanswered field: `record-finding` APPENDS a row and never updates one already recorded, so the answer is back-filled with the sibling setter `classify-finding-literal` (Phase 2.6) — never by re-calling `record-finding`, which would append a duplicate and leave the original violation standing. That back-fill can itself refuse: when more than one finding shares the surface and `file:line` you name, the setter stops and lists the matches rather than answering them all, and Phase 2.6 covers the two ways forward.

**Fallback when archaeology fails.** On a shallow git clone or a file not under git tracking: `git log -S` returns 0 commits OR `git blame` returns `(uncommitted)`. Treat the archaeology as inconclusive — pass `--intent forgotten`, the conservative classification, which points the same way for both uses: on a `--use fix-layer` row it forces fix-layer escalation per the recovery rule, and on a `--use evidence` row it lands in the evidence rule's first bullet, so the literal cannot carry the scope call on its own. What an `evidence` row is exempt from is only the `finalize-handoff` escalation-cite requirement; the evidence rule itself applies in full. Then add a one-line note in the recommended-approach rationale — `--rationale` is a required argument on `set-recommended-approach`, so that text exists on every run: `"archaeology inconclusive (shallow clone or untracked file); intent assumed forgotten per Phase 2.5b fallback rule"`. On a `--use evidence` row, extend that note to state that the literal's value is therefore not treated as evidence for the scope call it was cited for.

### Phase 2.6 — Wire findings into helper

After the CBM chain + parallel-pattern sweep + canonical-pattern search + helper-API surface enumeration (Phase 2.4c) + hypothesis enumeration complete, call helper setters in this order. Phase 2.4c state (`fix_path_helpers`, `inbound_callers`, `dead_siblings`, `consumer_chain`, `value_semantics`) is already recorded in the report by its own setters — do not re-record those surfaces via `record-finding`. Compose values from the in-context findings; do not re-shape.

For each finding — one per code surface that bears on the symptom, including every parallel surface from Phase 2.4 AND every canonical-pattern row from Phase 2.4b. Apply the same `search_code` pre-verification loop to canonical rows. The `--file-line="(none)"` negative-result row from Phase 2.4b is exempt from `search_code` verification — `(none)` is the sentinel value, not a path to verify.

```bash
.devforge/lib/research_helper record-finding \
    --surface "<surface label>" \
    --file-line "<path:line>" \
    --relevance "<one-line how-it-relates>" \
    --framing "<primary|runner-up>" \
    --rests-on-literal "<path:line>|none"
```

`<path:line>` MUST be the exact `file_path:line` from a `search_graph` or `search_code` result row (per Phase 2.3 grounding rule). BEFORE every `record-finding` call, run a one-line verification: `search_code(pattern="<expected literal at that line>")` and confirm the result row's `file_path:line` matches the value you are about to pass. On mismatch, take the result row's line as authoritative and pass THAT to `--file-line`; the LLM's recollection is wrong (off-by-one drift is the failure this catches). Only after the verification matches: call `record-finding`. If the verification `search_code` returns 0 hits: widen the pattern (try an adjacent literal) and retry once. If still 0 hits, pass the original result-row `file:line` you already hold (from the Phase 2.3 chain) and note the unconfirmed status in `--relevance`. Do not skip the finding.

`--framing` is optional and defaults to `primary` when omitted. Pass `--framing runner-up` for findings that support the runner-up framing recorded in Phase 2.3b — including NEGATIVE findings (evidence disproving the runner-up). At least one finding must carry `--framing runner-up` for `verify` check 12b to pass (check 12b fires only once `runner_up_framing` is set; check 12a — the unconditional gate that demands `runner_up_framing` be set at all — is satisfied earlier by the Phase 2.3b `record-runner-up-framing` call). That one finding may be positive (evidence supporting the runner-up) or negative (evidence the runner-up's falsifier did not hold up).

`--rests-on-literal` records whether this finding's conclusion rests on the VALUE of a hardcoded primitive literal: the literal's `file:line` when it does, the bare word `none` when it does not. Answer it on EVERY `record-finding` call in this command — Phase 2.4d Step 4's data-flow intermediates and Phase 2.4 / 2.4b's `--file-line="(none)"` negative-result rows included. "The flag is hardcoded `false`, so this chain is dead" and "its only caller passes `true`, so this prop is live" are both `file:line` answers, because the scope call turns on what the literal says; a finding that only reports where code lives, or what a canonical pattern does, answers `none`. A `file:line` answer commits you to Phase 2.5b for that literal: check 20 (mode-independent) rejects the report when a finding names a `file:line` that no `literal_archaeology` row covers, and rejects it when any finding leaves the field unanswered. On non-zero exit from `verify` citing check 20, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then run Phase 2.5b's steps + `record-literal-archaeology` with `--use evidence` for the named `file:line` before re-running `verify`.

When check 20 instead cites a finding that has not answered the field at all, the repair is the sibling setter `classify-finding-literal`, which answers the field on a finding ALREADY recorded — the check's stderr names it with the offending row's exact `--surface` and `--file-line`:

```bash
# Append --all ONLY in the narrow multi-match case described below; it is not part of the normal call:
.devforge/lib/research_helper classify-finding-literal \
    --surface "<surface label>" \
    --file-line "<path:line>" \
    --rests-on-literal "<path:line>|none"
```

The two setters are not interchangeable: `record-finding --rests-on-literal` is the record-time path for a NEW finding, `classify-finding-literal` the repair path for one already recorded. Do NOT re-call `record-finding` for that surface instead — it appends a second row rather than answering the first, leaving the original violation standing next to a duplicate finding.

`--surface` and `--file-line` are not a unique key — `record-finding` appends without dedupe, so two findings can legitimately carry the same pair. That gives this setter a second failure mode, distinct from the no-such-row one: when more than one row matches it exits 2 before touching anything, listing each matching row's `relevance` and its current answer (or `(unanswered)`). Read those rows. The default response prevents FUTURE collisions only — it does not repair rows already on file, since `record-finding` appends and a newly-labelled row never retires a colliding one. Within that limit it is the route to take: compose each `record-finding --surface` around what that finding actually rests on, so the pair keeps addressing one row. Append `--all` only when you have read the listed rows and the same answer is genuinely correct for EVERY one of them: it writes that answer across all matches, so a wrong call there stamps a fabricated answer onto a finding whose reasoning never rested on that literal — and check 20 accepts a fabricated answer exactly as readily as a considered one. When that is not true — the rows rest on different literals — the repair costs this run's whole report state, not just the colliding rows: `reset-report` plus re-recording is the only correct route. That price is exactly why the labels are worth getting right at `record-finding` time.

`none` is an answer, not a default. The check cannot tell a considered `none` from a reflexive one, so decide the answer before the call — answering at record time is one call, repairing it afterwards is two. A wrong `none` is how a literal whose meaning changed under a later commit ships as a scope conclusion nobody re-derived.

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

**Probe feasibility classification (MANDATORY — all modes).** Before the verify-step block below, classify the probe's feasibility along five boolean axes. These flags feed the downstream `finalize-handoff` probe-tier classifier (tier 1 = LLM unit test, tier 1.5 = LLM standalone script, tier 2 = LLM via chrome MCP, tier 3 = user manual). Call:

```bash
.devforge/lib/research_helper set-probe-feasibility \
    --data-shape-only <true|false> \
    --auth-required <true|false> \
    --network-dependent <true|false> \
    --timing-dependent <true|false> \
    --is-test-code <true|false>
```

Flag semantics:

- `--data-shape-only` — verification depends only on data shapes / function outputs / state values, with no auth, network, or timing dependencies.
- `--auth-required` — verification needs an authenticated session (logged-in user, API token, etc.).
- `--network-dependent` — verification needs real network calls or external services (not stubbable).
- `--timing-dependent` — verification depends on race conditions, lifecycle ordering, or async timing.
- `--is-test-code` — the bug is in test code itself; probing the test would be circular, so the classifier forces tier 3 (user manual).

All five flags are required in one call. Each accepts exact lowercase `true` or `false` only (argparse exact-match; `True` / `TRUE` are rejected; on rejection, stderr will read `invalid choice` — verify lowercase and retry without JSON-escaping). `finalize-handoff` in Phase 4 rejects with exit 2 + `"finalize-handoff: probe_feasibility incomplete; missing flags: [...]"` when any flag is unset. Call `set-probe-feasibility` immediately after the structured root-cause block (before the verify-step) — the classifier must run before finalize-handoff, and early placement avoids accidental omission.

If any hypothesis carries `runtime_probe_needed=yes`, set the verify step (all three sub-fields required in one call):

```bash
.devforge/lib/research_helper set-verify-step \
    --probe "<log/instrumentation to add>" \
    --reproduction "<exact user action that triggers the symptom>" \
    --discriminator "<if X → H_n confirmed; if Y → H_m confirmed>"
```

**Probe-script (CONDITIONAL — fires when tier resolves to 1.5).** Run this sub-step ONLY when ALL of the following hold based on flags you just set + a one-line state read:

- `set-probe-feasibility` flags above: `data_shape_only=true` AND `auth_required=false` AND `network_dependent=false` AND `timing_dependent=false` AND `is_test_code=false`.
- `.devforge/init.yaml`'s `test_infra.status` is `"absent"` OR the `test_infra` block is missing entirely. Read via:

  ```bash
  grep -E "^  status:" .devforge/init.yaml || echo "(no test_infra block)"
  ```

  Interpret: a line `  status: absent` (or empty/missing output) satisfies the condition; `  status: present` does not.

If ALL conditions hold → tier will resolve to 1.5 in Phase 4 `finalize-handoff`; proceed with steps 1-4 below. Otherwise SKIP this entire sub-step.

1. Create the scratch directory, then create a script file directly inside it (no subdirs — the helper rejects a deeper path):

   ```bash
   mkdir -p "${TMPDIR:-/tmp}/forge-research"
   ```

   The script path is `${TMPDIR:-/tmp}/forge-research/probe-script.<ext>`. The helper does NOT create this directory — run the `mkdir -p` above before the first write. The script lives in scratch for the rest of the run; Phase 4 copies it into the feature directory on save. Extension matches the chosen runtime:
   - `node` / `deno` / `bun` → `.mjs`
   - `python` → `.py`
   - `ruby` → `.rb`
2. Inline the buggy logic VERBATIM from the cited `file:line` locations recorded as findings in Phase 2.4d / 2.5. Do NOT reconstruct from memory — copy the source bytes. Prepend each inlined block with a `// SOURCE: <file>:<line>` comment (use the runtime's comment syntax — `#` for python/ruby) so the inlined-from contract is auditable.
3. The script's pass/fail assertion must map to the `--discriminator` set in the verify-step block above (one observable outcome per hypothesis).
4. Record the script:

   ```bash
   .devforge/lib/research_helper record-probe-script \
       --script-path "${TMPDIR:-/tmp}/forge-research/probe-script.<ext>" \
       --runtime <node|python|ruby|deno|bun> \
       --inlines-from '["<path>:<line>", "<path>:<line>", ...]'
   ```

Validators (all rejected with exit 2 + stderr message prefixed `record-probe-script: ...`): `--script-path` file must exist on disk AND be a DIRECT child of the scratch directory `${TMPDIR:-/tmp}/forge-research` (no subdirs); `--runtime` must resolve via `shutil.which`; `--inlines-from` must be a non-empty JSON array of `<path>:<line>` tokens (each `<line>` must be digits-only). Strict-match idempotency: re-recording the same `--script-path` with a different `--runtime` or different `--inlines-from` is rejected exit 2 — to revise an entry, run `reset-report` and re-record from scratch, or choose a different `--script-path`. Exact re-record of the same triple is a no-op (exit 0 + stderr "already recorded" notice).

Skip-clause consequences. If you skip this sub-step but tier later resolves to 1.5 in Phase 4 `finalize-handoff`, the handoff.json will fall back to the deterministic default `${TMPDIR:-/tmp}/forge-research/probe-script.mjs` — but no file exists at that path, leaving a dangling reference. If you record a probe script but tier resolves to ≠ 1.5, the recorded entry is silently ignored — `finalize-handoff` only reads `probe_scripts` when it classifies tier 1.5, so the entry stays in `research-report.json` unused and the written script file lingers in the scratch directory. Skip only when the trigger conditions above clearly don't hold; recording speculatively wastes work and leaves an unreferenced file behind.

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string), retry up to 3 times. On the 4th failure, copy stderr VERBATIM to the user and end the turn; user must re-run `/devforge:research` from scratch — prior partial state will be overwritten.

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

   **MANDATORY (when the recommended approach replaces a hardcoded literal, or rests a scope call on one):** if `--rationale` or the linked approach's `--description` will contain literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) where `<X>` is a primitive literal, Phase 2.5b `record-literal-archaeology` for `<X>` at the literal's `file_line` — which must be a recorded finding's `file_line`, since that is what check 17 matches on — MUST have been called BEFORE `set-recommended-approach`. Check 17 enforces this at verify time, in any mode: on non-zero exit citing check 17, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), run Phase 2.5b's git-archaeology steps + `record-literal-archaeology`, then re-run `verify`.

   The same obligation holds for a literal the recommendation REASONS FROM rather than replaces: when the rationale rests a scope call (dead vs live, in vs out of scope, keep vs delete) on what a literal says, that literal needs its archaeology row too, recorded `--use evidence`. Check 17 does not see that shape — it matches replacement prose only. Check 20 is what compels it, via the `--rests-on-literal` answer on the finding carrying the conclusion (Phase 2.6). Record it in that order and the row is already in place when this setter runs; nothing enforces that order here, so when the step was skipped the row is still missing at this point and check 20 is the backstop — `verify` runs after every Phase 3 setter, and the recovery is the one Phase 2.5b names.

   **Proposed call-shape gate (Patch 9).** When EITHER `--single-layer-justification` is set OR `--rationale` (or the linked approach's `--description`) contains literal-replacement prose, `--proposed-call-shape` is REQUIRED. The shape must be the exact post-fix call as it would appear at the fix site (function name + parenthesized arg list, multi-line accepted — helper collapses whitespace). The helper parses the shape, splits the arg list on top-level commas, and rejects when the same identifier (bare name, dotted member access, or optional-chained `a?.b?.c`) appears more than once — argument duplication signals the default-source belongs at a different layer (wrapper signature / state initialization / use-case default) rather than at the call site. Example call:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "Wrapper default-param for flag" \
       --rationale "<why>" \
       --hypotheses-addressed '["A"]' \
       --hypotheses-not-covered '[]' \
       --single-layer-justification "<prose>" \
       --cites '["<token>"]' \
       --proposed-call-shape "loadData()"
   ```

   On argument duplication, the helper exits with code 2 and stderr `set-recommended-approach: --proposed-call-shape "<shape>" contains argument duplication ("<ident>" appears N times in the arg list). Same value passed multiple times in one call indicates the default-source belongs at a different layer (wrapper signature / state initialization / use-case default). Reconsider the fix layer and re-draft.` Recovery: escalate the default-source one layer up (wrapper signature, state-init factory, or use-case default), re-draft the approach so the call site no longer needs the duplicated arg, then re-call `set-recommended-approach` with a non-duplicating `--proposed-call-shape`. Parser failure (nested calls, unsupported syntax) is fail-soft: helper emits a stderr advisory `research_helper: set-recommended-approach: --proposed-call-shape "<shape>" could not be fully parsed (nested calls / unsupported syntax); argument-duplication check skipped, shape stored verbatim.` and proceeds to exit 0. Check 18 mirrors the duplication check at verify time (catches state-mutation bypass) — same recovery applies.

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

   Call it WITHOUT `--research-path` here. The feature directory does not exist yet — Phase 4 allocates it only after the user confirms the save — so the Next-Step block's `Research reference:` line renders the placeholder `(path assigned when this research is saved to its feature directory)`. That placeholder is the correct text for the Phase-3 preview; Phase 4 re-runs this setter with the real path before anything is written to disk.

8. **Evidence lanes consulted** (all four flags in one call, exact lowercase `true` / `false`):

   ```bash
   .devforge/lib/research_helper set-evidence-lanes \
       --static-graph <true|false> \
       --text-search <true|false> \
       --runtime-probe <true|false> \
       --history <true|false>
   ```

   Skipping this call blocks the handoff: Phase 4's `finalize-handoff` rejects a run that never made it, and without that handoff `/devforge:specify` has nothing to consume. The check asks only whether the call happened — any combination of `true` and `false` satisfies it; no declaration at all does not. Make the call here, in Phase 3, rather than meeting that rejection at Step 4.6, by which point the user has confirmed the save, the branch exists, and `research-report.md` is already on disk. A clean `verify` is not evidence the declaration exists — the check that enforces it runs later, at Phase 4. Each lane starts UNDECLARED, a different state from an explicit `false`: `false` is a claim you make, undeclared is a claim you never made. Re-calling overwrites (last call wins).

   Each flag reports what this investigation actually consulted, scoped by TOOL rather than by phase: `--static-graph` any `search_graph` / `trace_path` / `get_code_snippet` call this run made, in whichever phase — they run well beyond the Phase 2.3 chain; `--text-search` any `search_code` call this run made, including the one Phase 2.3's own step-2 fallback fires inside that chain; `--runtime-probe` runtime evidence actually obtained during this run (a probe merely RECOMMENDED in the verify-step above is `false`); `--history` the `git log` / `git show` / `git blame` archaeology of Phase 2.5b. A `false` costs the report nothing — no lane is required to have run, and the declaration is the deliverable, not the coverage. Inflating a lane to `true` is the answer that does damage: this is the record a reader uses to tell "that lane found nothing" from "that lane never ran", so a false `true` retires a question nobody actually asked.

### Verify

```bash
.devforge/lib/research_helper verify
```

Helper cross-checks: ≥2 hypotheses, recommended-approach name matches an approach, recommended-approach respects `unchanged_behavior`, verdict ∈ mode-allowed-set, structured root-cause fields populated when bug-mode + confidence ∈ {`Confirmed`, `Hypothesis`}, verify-step's 3 sub-fields populated when any hypothesis needs a runtime probe, all required sections populated. Check 8 (caller-enumeration gate) is mode-independent — it rejects a report in ANY mode whose `fix_path_helpers` list is empty and that carries no no-shared-callers justification, and separately rejects a report where both are set; see Phase 2.4c for the two remedies and the escape's contradiction rules. Check 8b (cross-layer rule) rejects a report where the primary symptom's `file:line` resolves to a presentation-layer path AND every `fix_path_helpers[].file_line` is in the same package as the symptom — at least one helper must trace through a package boundary; see Phase 2.4c Stopping rule. Check 12a (unconditional) rejects a report whose `runner_up_framing` is unset — Phase 2.3b must execute before `verify`. Check 12b (conditional on `runner_up_framing` set) rejects a report where no finding row carries `framing == "runner-up"` — at least one finding (positive or negative — disproving the runner-up via its falsifier is a valid outcome) must be tagged `--framing runner-up` for the runner-up to be considered probed. Check 13 (single-layer recommendation gate) rejects a report where all `fix_path_helpers[].file_line` resolve to one package AND `recommended_approach.single_layer_justification` / `cites` are missing or empty — supply both via `set-recommended-approach --single-layer-justification ... --cites '[...]'` (see Phase 3 step 3). Check 13 is suppressed when check 8b applies (presentation-layer symptom + same-package helpers); in that case the single-layer escape path cannot satisfy verify and the only recovery is adding a cross-layer helper. Check 14 (fix-path-helper anchor gate) rejects a report where any `fix_path_helpers[]` entry's `file_line` does not anchor to a recorded finding (exact match OR same path within ±5 lines) — see Phase 2.4c Step 1 anchor gate. Check 17 (literal-archaeology gate) is mode-independent — it rejects a report in ANY mode whose `recommended_approach.rationale` OR the linked approach's `description` contains literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) where `<X>` is a recognizable primitive literal AND no `literal_archaeology` row exists for `<X>` at a `findings[].file_line` — recovery: run Phase 2.5b archaeology + `record-literal-archaeology`, then re-run `verify`. Check 18 (argument-duplication shape check) rejects a report whose `recommended_approach.proposed_call_shape` contains the same identifier (bare / dotted / optional-chained) more than once in its arg list — argument duplication signals the default-source belongs at a different layer; recovery: escalate the default-source upstream (wrapper signature / state initialization / use-case default) and re-call `set-recommended-approach` with a non-duplicating `--proposed-call-shape`. Shapes that could not be parsed (nested calls, unsupported syntax) are treated as non-duplicating — same fail-soft rule as the setter gate. Exit 0 → pass; non-zero → at least one violation enumerated on stderr.

On non-zero exit: copy stderr VERBATIM, identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/devforge:research` from scratch (all prior state will be overwritten).

### Hypothesis-suppression gate

After `verify` exits 0, run the dedicated hypothesis-suppression gate (this is a separate verb from `verify`, not one of its 20 checks):

```bash
.devforge/lib/research_helper verify-hypothesis-suppression
```

The gate defends the Phase 0.4 / Step 5 separation at finalize time: an UNVERIFIED suspected-cause hypothesis must not also reappear as design direction. Mechanically, the helper token-overlaps each unverified hypothesis's `--cause` text against `recommended_approach.rationale` (the text that becomes `plan_seeds.recommended_approach_summary` in the handoff) and exits 2 on any shared identifier/vocabulary token. A hypothesis is exempt from the gate ONLY when it is CONFIRMED, and confirmation requires BOTH conditions together: the session/probe grade is HIGH (tier 1 / 1.5 — not MEDIUM/LOW and not feasibility-discriminator-unresolved) AND the hypothesis is recorded as addressed in `recommended_approach.hypotheses_addressed` (matched by its label). Behaviorally: confirmed (HIGH-grade AND addressed) → exempt; anything else → gated. An unconfirmed hypothesis stays gated even in a HIGH-grade session — a runner-up that the session did not confirm but whose mechanism leaks into the rationale is still flagged, because HIGH grade alone is not confirmation without the addressed-label match. Exit 0 → clean (no recommended approach yet, or no unverified mechanism leaked); exit 1 → state unreadable; exit 2 → a leak was found.

**Scope of this check (do not over-trust it).** This is a MODERATE mechanical backstop: it catches a leaked mechanism when the recommended approach REUSES the cause's identifiers/vocabulary — the common case, since an approach summary usually names the API / symbol it changes. It does NOT catch pure semantic paraphrase: a recommended approach that encodes the same mechanism in entirely different words shares zero tokens and passes. Paraphrase leakage is caught by Step 5's echo-back human gate (plan 18 Step 5), not by this check.

On exit 2: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The recovery is exactly what the stderr names — move the mechanism into an open question via `record-gap` (record it against the `desired` dimension with a `"confirm <mechanism> before designing"` description), then remove the mechanism from the recommended approach by re-calling `set-recommended-approach` with a `--rationale` that no longer encodes the unverified cause. Re-run `verify-hypothesis-suppression` after the fix; cap at 3 iterations, then surface to the user and end the turn.

### Render

```bash
.devforge/lib/research_helper render
```

Helper walks the locked schema and emits the full research report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order (Header → Metadata → Summary → Symptom → Codebase Findings (WHERE) → Root Cause Hypothesis (WHY) → optional Structured Root Cause → optional Runner-up framing → Hypothesis Enumeration → optional Recommended Verify Step → Approaches (HOW) → Constitution Constraints → Complexity Assessment → optional Value Semantics → optional Value Production Sites → optional Literal Archaeology → Evidence Lanes Consulted → optional Open Uncertainties → optional Next Step), heading levels, and table shapes. The Runner-up framing section renders only when `runner_up_framing` is set (see Phase 2.3b). Evidence Lanes Consulted is the one section carrying no "optional" qualifier above: it renders on every report, listing each lane as `consulted` or `not consulted`, so a lane that never ran says so rather than vanishing from the report (see setter 8). The Codebase Findings table includes a `Framing` column showing the per-finding tag (`primary` or `runner-up`).

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the rendered report.

This render is a PREVIEW, not the saved file. Nothing is written to disk in Phase 3, and the Next-Step block still carries the path placeholder described in setter 7. On save, Phase 4 re-runs `set-next-step-text` with the allocated path and re-runs `render`; the bytes written to the feature directory come from THAT second render.

The LLM does NOT edit the rendered report via Write or Edit at any point — Phase 4 writes the helper's rendered bytes verbatim and never reshapes them. The helper's `render` is the only composer of this markdown; any post-render fix is applied by re-calling the relevant setter + `render` + `verify` in a new turn.

### Emission matrix (CONDITIONAL — fires when the recommended approach removes or suppresses an emitted value)

**Trigger.** Run this step when the recommended approach you just recorded REMOVES or SUPPRESSES a value the changed code emits today — a value that code returns, renders, passes as an argument, writes into a payload, or publishes on an event, and that after the change it no longer does. Read the trigger off what the approach DOES to the code (the linked approach's `--description` plus the `--rationale` you passed to `set-recommended-approach`), never off how the summary happens to be worded.

**The trigger is a fact about the change, never a belief about the callers.** Do not condition it on how many call sites you think exist, or on a judgment that the only caller is the one the topic names. A confident caller count is precisely the claim this matrix tests, so it can never be what decides whether to build one: when the approach removes or suppresses an emitted value, compose the matrix even when you are certain a single call site exists.

**Skip clause.** When the approach removes and suppresses nothing the changed code emits — it adds behavior, swaps one value for another, or restructures without dropping an emission — no matrix is composed here and none is written in Phase 4. That is the complete and correct outcome for such a run: an absent `emission-matrix.md` in a feature directory means the trigger did not fire, not that a step was skipped. State which of the two cases this run is in, in one line, in the same message that carries the rendered report, so the user can tell "not applicable" from "not done".

**No helper owns this file.** `render` composes `research-report.md` and nothing else; no verb emits this matrix and no verb checks it. You compose the markdown directly, in the message — Phase 4's invariant holds, so nothing goes to disk here (nothing outside `.devforge/` scratch exists before the user's confirmation in Step 4.1). The rules at the end of this step are therefore the only thing standing between a wrong row and the plan built on it: no gate downstream will catch a cell you asserted instead of traced.

Compose it in this shape:

```
# Emission Matrix

**Change under evaluation**: <the recommended approach's name>
**Values this change removes or suppresses**: <listed once — a per-run constant, never a column>

| Call site | Emits today | Intersection with the removed set | Verdict | Note |
|---|---|---|---|---|
| <file:line> | <what this caller emits> | <traced, not asserted; `none` when empty> | affected / unaffected | <required when the verdict is `affected`, or when a cell reads `varies`> |
```

1. **Take the rows from the enumeration you already ran.** `read-report` at the top of Phase 3 already printed the state they come from: the rows are the `inbound_callers` entries recorded against the `fix_path_helpers` this approach changes (Phase 2.4c Steps 1-2b). One matrix row per recorded caller. The `Call site` cell copies that row's `file_line` verbatim — the Phase 2.3 grounding rule holds here as everywhere: never re-derive a line number, and never take one from `get_code_snippet` output. Do NOT re-run the inbound traces to build this table. Check 9 already pinned the recorded caller count to the declared total and check 19 already forced every recorded caller to carry a surface, a scope, and a justification, so the enumeration behind these rows is complete by construction; a second trace here would only produce a second count that nothing reconciles against the first.

   Read each caller's recorded `surface`, `scope`, and `justification` as context for its Note — but decide the verdict from the intersection, not from that `scope` value. `in` / `out` was your judgment about where the fix goes; `affected` / `unaffected` is a traced fact about what the site emits, and the two can legitimately disagree on the same row. That `surface` is context only so far as it was derived from the caller's construction sites, the way Phase 2.4c Step 2b requires — a label with no construction site behind it names a resemblance, not a surface, and the Note must not restate it as a traced fact. When the row's `justification` shows the trace never reached those sites, the Note says so rather than repeating the label.

   **A fired trigger with no rows is a contradiction.** A change that removes an emitted value has at least one path emitting it today, so an empty row set means the enumeration is incomplete or the trigger was read off the wrong thing — it does not mean the code has no callers. Settle that before composing: return to Phase 2.4c and enumerate the callers of the symbol this approach changes, or re-read what the approach actually removes. A recorded no-shared-callers justification does not settle it either — that escape is for a change with no existing shared symbol to call into, which is not a change that removes something existing callers emit.

2. **Fill the two header lines.** `**Change under evaluation**` is the recommended approach's `--name`, exactly as `set-recommended-approach` recorded it. `**Values this change removes or suppresses**` lists those values once, there. They are a per-run constant — identical for every row — so they never become a column, and every row's cells are read against that one list.

3. **Trace each row's two evidence cells against the code.** For every call site, read what it emits at that `file:line` through the CBM chain — `get_code_snippet` on the recorded row, plus `search_code` for a literal from it when the snippet leaves the emitted set unclear. Raw `Read` / `Grep` / `Glob` / `grep` / `cat` over source files stay forbidden (Phase 2.3). `Emits today` is what THIS site emits, as read. `Intersection with the removed set` is which members of the header's removed set appear in that emitted set, and reads `none` when empty.

4. **Verdict — `affected` or `unaffected`, and nothing else.** `affected` when the intersection is non-empty; `unaffected` when it reads `none`. Those two words are the whole vocabulary of that column. Whether a path becomes unreachable is a consequence of a guard the design does not have yet — `/devforge:plan` is where one gets chosen — so this matrix makes no reachability claim of its own and produces no unreachable-path rows.

5. **`varies` when the emitted set is not statically determinable.** When a call site assembles what it emits at runtime, sits behind a dispatch you cannot resolve from the code, or cannot be read at all, write `varies` in that cell, state in the Note which values you considered and what blocked the trace, and record the verdict as `affected`. The conservative reading is the recorded one: an undeterminable set is never `unaffected`.

6. **Collapse rows only on identical emitted sets.** Call sites that emit an IDENTICAL set may share one row, and that row must still enumerate every collapsed call site's `file:line` in the `Call site` cell. Any difference between them — one extra value, one different value — forces separate rows. Collapsing is a formatting economy, never a way to stop enumerating.

**The rules this matrix must satisfy.** Five of the six are the composer's, and they are obligations on how you fill the table — not text to copy into the file. Their numbering is shared with the stage that consumes the matrix, which is why it is not contiguous here.

- **Rule 1 — every call site appears.** Found mechanically and cited by file and line. No sampling, no representative subset, no row dropped because it looked obviously unaffected: an `unaffected` row is a result, and omitting it is indistinguishable from never having looked.
- **Rule 2 — the evidence cells are traced, never asserted.** `Emits today` and `Intersection with the removed set` are read out of the code at that call site, and a non-`varies` cell records the VALUE SET that read established — the values themselves, never a name that stands for them. A cell filled in from the caller's name, from what the topic implies, or from what you expect that caller to do, is an assertion wearing a trace's clothes; so is one naming an expression, a parameter, or a name standing in for its values, even when that expression was copied out of the code — a claim about which values a site presents is checkable against values and against nothing else.
- **Rule 3 — a non-empty intersection is justified in one sentence.** Every `affected` row's Note says why that call site emits a value this change removes. If you cannot write that sentence, the design is wrong — not the row.
- **Rule 4 — an `affected` verdict is an obligation, not a warning.** It obliges the architect to account for that call site at `/devforge:plan`. Where the change made there renders a path unreachable, the constitution's **No dead code** rule applies — delete it, do not guard it. That call belongs to `/devforge:plan`; this matrix makes no reachability claim of its own.
- **Rule 6 — derived exclusions.** An "explicitly not modified" or out-of-scope entry for a caller of the changed code is valid ONLY when that caller's row shows an EMPTY intersection, and the row is what states it. A non-empty intersection invalidates the entry: escalate it as a product question — does that surface keep emitting the value, or not? — and never resolve it by inferring intent from the topic's silence.

There is no rule 5 in this step. Rule 5 governs how `/devforge:plan` CONSUMES the matrix, not how you produce it, so it is stated there and nothing in this command applies it. Do not close the gap by renumbering rule 6 — the numbers are the shared vocabulary between the two sites.

Surface the composed matrix in the same user-facing message as the rendered report, below it, as a fenced block. Step 4.5b writes those exact bytes once the user confirms the save; on the don't-save arm they stay in the message and nothing else in this command reads them.

## Phase 4 — Save + recommend

Phase 4 runs in one fixed order: confirm the save + the feature name → resolve the feature directory (allocate, or attach) → create the branch → write the report → copy the probe script → write the emission matrix → write the handoff → commit. Nothing outside `.devforge/` scratch is created before the user's confirmation in Step 4.1, and no step below runs on the don't-save arm.

### Step 4.1 — Ask to save (one question, feature name included)

Compose the proposed feature slug from `memo.topic_slug` (already in state — `read-memo` prints it). The slug becomes the permanent feature-directory name and the branch name, so it must be 2-4 lowercase kebab-case words whose first character is a letter. `set-topic` derives `topic_slug` by lowercasing the topic, replacing each non-alphanumeric run with `-`, and keeping the first 4 words — that value can come out as a single word or with a leading digit, neither of which is a valid feature slug. When it does, adjust it before displaying: add a distinguishing word from the topic to reach two words, and reword or drop a leading numeric segment.

After echoing the rendered report, ask ONE question via AskUserQuestion — single-line question text `"Save this research as feature '<proposed-slug>'?"` — with exactly two options: `"Save as <proposed-slug> (Recommended)"` and `"Don't save"`. Do NOT add an "Other" option of your own; the tool appends its own free-text row, and that row is the rename path.

End the turn. The user's reply opens the next turn. Read the reply as follows:

- `Save as <proposed-slug> (Recommended)` → save under the proposed slug; go to Step 4.2.
- `Don't save` → go to Step 4.7.
- Free text (the tool's own row) → treat it as SAVE, using the typed text as the feature name — UNLESS the text clearly declines (e.g. "no", "skip", "cancel", "don't save"), in which case go to Step 4.7. Normalize the typed text by the same rule as the proposed slug: lowercase it, replace each non-alphanumeric run with `-`, keep the first 4 words, and require 2-4 words with a letter as the first character. Use the normalized slug for the rest of Phase 4.
- Free text that yields no valid slug under that rule (fewer than two usable words, or nothing that can start with a letter) → do not guess a name. Ask Step 4.1's question again, naming what was wrong with the typed text; the user can also pick either literal option to move on.

**Attach-mode variant.** When Phase 0.6 recorded an attach directory, this run has no slug to propose — the feature is already named. Skip the slug composition above and ask instead: single-line question text `"Save this research into the existing feature '<feature>'?"` with exactly two options, `"Save to <feature> (Recommended)"` and `"Don't save"` — `<feature>` is the seed's `feature` field, per Phase 0.6's rule that the seed's `feature` is what your messages NAME while its parent directory is where they WRITE. The directory is never renamed, so free text is NOT read as a slug here: treat any free-text reply as SAVE into `<feature_dir>` unless it clearly declines (e.g. "no", "skip", "cancel", "don't save"), in which case go to Step 4.7. On save, go to Step 4.2's attach arm.

### Step 4.2 — Resolve the feature directory

**Attach mode.** If Phase 0.6 recorded a grill-re-entry feature directory, that directory IS this run's `<feature_dir>`: skip allocation, skip Step 4.3 entirely, and let Steps 4.4-4.6 overwrite the artifacts in place (the superseded versions stay recoverable from the per-step git commits). An attached directory is never renamed — Step 4.1's attach-mode variant neither proposes nor reads a slug — so the path Phase 0.6 recorded is the `<feature_dir>` Steps 4.4-4.6 use. Go to Step 4.4.

**Fresh allocation.** Otherwise allocate a new feature directory with the confirmed slug:

```bash
.devforge/lib/research_helper allocate-feature-dir --slug "<confirmed-slug>"
```

Stdout is a JSON object. Take `relative_path` from it — that value is this run's `<feature_dir>`, and it is what every step below writes into. Hold it in working memory exactly as the helper reported it: do not re-shape it, do not rebuild it from any other key on that object, and do not substitute the sibling `path` key, whose absolute form Step 4.4 would write verbatim into the rendered report's `Research reference:` line. No step in this command reads `path`. Take `formatted_number` as well; it is Step 4.3's `--number` input and this command reads it for nothing else, so no step composes a path from it. The helper creates the directory and fails loudly rather than reusing an existing one.

On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then: on a rejected slug, return to Step 4.1 and ask again with a corrected proposal; on any other error, report it and end the turn — nothing has been written yet, so the run stops cleanly and the user can re-run `/devforge:research`.

**A seedless re-run always allocates a NEW directory.** No topic matching is performed: running `/devforge:research` again on a topic that already has a feature directory produces a second, separate one, with no reference to the earlier run. That is intended — the closing message names the directory that was created so the user can delete it if it is an unwanted duplicate.

### Step 4.3 — Create the feature branch (fresh allocation only)

Skip this entire step in attach mode — the feature already has its branch.

Detect the current branch:

```bash
git branch --show-current
```

If that command fails because the directory is not a git repository, skip the rest of this step: tell the user `"Skipped branch creation: not a git repository."` and continue at Step 4.4.

Detect the repository's default branch, in this order; stop at the first that succeeds:

1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` — parse the branch name from the output.
2. `git show-ref --verify --quiet refs/heads/main`.
3. `git show-ref --verify --quiet refs/heads/master`.
4. None of the above resolved → skip the rest of this step: tell the user `"Skipped branch creation: could not resolve the default branch (no origin/HEAD, main, or master). Create a branch manually if you want one."` and continue at Step 4.4.

Branch creation is best-effort and never stops the save. Ask no question here and end no turn on either skip path — this phase's product is the artifacts, and Steps 4.4-4.6 write them on whatever branch the session is already on.

Then ask the helper what to do:

```bash
.devforge/lib/research_helper render-branch-command \
    --slug "<confirmed-slug>" \
    --number "<formatted_number from Step 4.2>" \
    --current-branch "<current branch>" \
    --default-branch "<default branch>"
```

Stdout is a single line. When the run is on the default branch it is a checkout command of the form `git checkout -b spec/NNN-<slug>` — execute that line and tell the user `"Created and switched to branch spec/NNN-<slug>"`. On any other branch it is a `# already on non-default branch ...` informational comment — emit no checkout, keep the current branch, and continue.

### Step 4.4 — Re-render with the real path, then write the report

The Phase-3 render was a preview whose `Research reference:` line carries a placeholder. Now that the directory exists, re-render with the real path:

```bash
.devforge/lib/research_helper set-next-step-text \
    --research-path "<feature_dir>/research-report.md"

.devforge/lib/research_helper render
```

Write THAT `render` stdout, byte-verbatim, to `<feature_dir>/research-report.md`. Do not re-format, re-shape, or hand-edit it — the only difference between the preview the user already saw and the saved file is the helper-rendered reference line. In attach mode this overwrites the previous `research-report.md`, which is the intent.

On a verdict outside the proceeding-set, `set-next-step-text` is a no-op that ignores `--research-path`, and the rendered report carries no Next-Step section (see Phase 3 setter 7). Run both calls anyway — the re-render is what gets written either way.

### Step 4.5 — Copy the probe script (conditional)

Run this step ONLY when Phase 2.6 recorded a tier-1.5 probe script. Copy it out of scratch into the feature directory, keeping the same extension:

```bash
cp "${TMPDIR:-/tmp}/forge-research/probe-script.<ext>" "<feature_dir>/probe-script.<ext>"
```

When no probe script was recorded, skip this step and leave the probe-script path out of Step 4.6's commit.

### Step 4.5b — Write the emission matrix (conditional)

Run this step ONLY when Phase 3's Emission matrix step composed a matrix. Write those bytes — the ones the user already saw below the rendered report — to `<feature_dir>/emission-matrix.md`.

Do not re-compose the table here and do not reshape it: its content was settled in Phase 3, and nothing between there and here changes the recommended approach it was composed against. Unlike `research-report.md`, whose bytes come from the helper's `render`, these bytes are yours — no helper renders this file and none validates it. In attach mode this overwrites the previous `emission-matrix.md`, which is the intent.

When Phase 3 composed no matrix — its skip clause fired because the recommended approach removes and suppresses nothing the changed code emits — skip this step and leave the matrix path out of Step 4.6's commit. No file is written, and that absence is the correct record of such a run.

### Step 4.6 — Write the handoff, then commit

```bash
.devforge/lib/research_helper finalize-handoff \
    --feature-dir "<feature_dir>"
```

The helper writes `<feature_dir>/research-handoff.json` and records the sibling `research-report.md` as the handoff's research path. In attach mode it overwrites the existing handoff.

If the helper exits non-zero, tell the user `"Research report saved at <feature_dir>/research-report.md but research-handoff.json failed: <stderr>. Re-run finalize-handoff manually after fixing the missing state."` and end the turn. If it exits 0, capture the stdout `wrote: <abs path>` for the closing message.

Then `[WIP]`-commit everything this run wrote, so the work is git-safe immediately. `--paths` carries the report and the handoff, plus `<feature_dir>/probe-script.<ext>` when Step 4.5 copied one and `<feature_dir>/emission-matrix.md` when Step 4.5b wrote one; the two extras are independent — either, both, or neither may be present. The label uses the topic slug:

```bash
# Two paths normally; append each extra element ONLY when its own step produced it:
#   "<feature_dir>/probe-script.<ext>"  — ONLY when Step 4.5 copied a probe script
#   "<feature_dir>/emission-matrix.md"  — ONLY when Step 4.5b wrote the emission matrix
# With both: '["<feature_dir>/research-report.md", "<feature_dir>/research-handoff.json", "<feature_dir>/probe-script.<ext>", "<feature_dir>/emission-matrix.md"]'
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["<feature_dir>/research-report.md", "<feature_dir>/research-handoff.json"]' \
    --label "research: <topic-slug>"
```

The helper stages those paths in the install repo and makes a `[WIP] research: <topic-slug>` commit; it is install-repo-only (never the source repo in wrapper mode). This call is UNCONDITIONAL on the save arm — always run it once the report and handoff are written. It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifacts are already saved, so warn the user with the helper's stderr and continue to the closing message; do NOT abort the command or re-run the save); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op.

### Step 4.7 — On "Don't save"

Nothing is written outside `.devforge/` scratch: no feature directory, no branch, no report, no handoff, no commit. Do not run `finalize-handoff` on this arm — it has not run yet at this point in the flow, and running it would leave an orphaned handoff for a feature that does not exist.

The rendered report stays in the assistant message only. `.devforge/research-state.json` and `.devforge/research-report.json` remain on disk until the next `/devforge:research` invocation overwrites them, and a tier-1.5 probe script written during the run stays in `${TMPDIR:-/tmp}/forge-research/`.

### Closing message

If a save happened AND the verdict is in the proceeding-set, the saved report contains a `## Next Step` section with a copy-pasteable `/devforge:specify "..."` block (that block is composed by `research_helper render` — it is the helper's string, not this spec's, so do not rewrite it here). Tell the user: `"/devforge:research is done. Created feature directory <feature_dir> — open <feature_dir>/research-report.md to review. The 'Next Step' section at the bottom is a copy-pasteable block for a new spec session — copy it manually when you're ready. The intake handoff /devforge:specify requires is its sibling, <feature_dir>/research-handoff.json; delete the directory if you meant to add to an existing feature."`

If a save happened AND the verdict is not in the proceeding-set, the report omits the Next-Step section. Tell the user: `"/devforge:research is done. Created feature directory <feature_dir> — open <feature_dir>/research-report.md to review. The verdict was '<verdict>' — recommended next step is to address the cited uncertainties or follow the recommended verify probe before specifying a fix. The handoff at <feature_dir>/research-handoff.json records the research state for downstream tooling; delete the directory if you meant to add to an existing feature."`

In attach mode, make two substitutions in whichever template applies: replace `"Created feature directory <feature_dir>"` with `"Updated feature directory <feature_dir> in place (grill re-entry)"`, and drop the trailing `"; delete the directory if you meant to add to an existing feature."` clause. Attach mode creates no directory and no branch, so there is nothing to delete.

If the user declined to save, tell the user: `"/devforge:research is done. The report is in the prior message; .devforge/research-state.json and .devforge/research-report.json hold the state but will be overwritten on the next /devforge:research invocation. No feature directory, branch, report, or handoff was written — re-run /devforge:research and save to produce them."`
