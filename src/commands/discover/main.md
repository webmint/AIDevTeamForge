---
name: discover
description: Pre-spec exploration of a greenfield feature; produce a structured discovery report grounded in prior-art survey + codebase fit-check.
argument-hint: "<topic>"
---

# /devforge:discover — Greenfield Feature Discovery

`/devforge:discover` is repeatable per greenfield feature. It clarifies a vague feature idea into a structured scoping memo across 8 dimensions, runs an orchestrator-direct investigation that surveys prior art via web + Context7 AND reconciles user-belief against codebase reality via the CBM graph + `docs/` corpus, composes a discovery report with 2-3 design options + Build-vs-Buy + Derisk plan, and — once the user confirms the save — allocates the feature directory and writes the rendered report plus its specify-bound handoff inside it. `/devforge:discover` reads source code without modifying it, but a saved run is NOT inert on the repository: it creates that directory, creates a `spec/NNN-<feature-name>` git branch when the session is on the default branch, and `[WIP]`-commits what it wrote. State + render shape are owned by `.devforge/lib/discover_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) has completed before any investigation fires.

Usage: `/devforge:discover "<topic>"` (e.g. `/devforge:discover "audit log persistence layer"` or `/devforge:discover "auth in a TypeScript backend framework"`).

## Outputs of this phase

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run writes into: one path the orchestrator holds in working memory for the rest of the run. Phase 4's save flow takes it from `allocate-feature-dir`'s `relative_path` on a fresh allocation (step 1), and Phase 0.6's attach arm takes it from the re-entry seed file's parent directory. The orchestrator never composes it from parts, never re-shapes it, and never substitutes another key for it; every artifact path below is `<feature_dir>` plus a filename. In wrapper mode it resolves under the install root, never the nested source root.

- `.devforge/discover-scope.json` — ScopingMemo (Phase 1 state). Owned + shaped by the helper; initialized at Phase 0.3 (`reset-memo`, `set-topic`), then mutated via Phase-1 setter subcommands.
- `.devforge/discover-report.json` — DiscoveryReport (Phase 2 + 3 state). Owned + shaped by the helper; mutated only via Phase-2/3 setter subcommands.
- `<feature_dir>` — the feature directory, allocated by Phase 4's `allocate-feature-dir` only after the user confirms the save and the feature name (a `/devforge:grill` re-entry run reuses the seed's existing directory instead — see Phase 0.6). A run the user does not save leaves nothing here. A `spec/NNN-<feature-name>` git branch is created alongside it when the session is on the default branch.
- `<feature_dir>/discovery-report.md` — rendered report. Helper's `render` writes to stdout; the orchestrator writes those bytes into the feature directory in Phase 4's save flow.
- `<feature_dir>/discover-handoff.json` — the specify-bound handoff, written by Phase 4's `finalize-handoff` (sibling to the rendered report). The report stem is `discovery-` and the handoff stem is `discover-`; that asymmetry is deliberate — never normalize one to match the other.

On save, Phase 4 `[WIP]`-commits the rendered report + its handoff into the install repo via `.devforge/lib/artifact_helper commit-artifacts` (install-repo-only, fail-soft) so the work is git-safe the moment it is written; the commit folds into `/devforge:finalize`'s squash.

## Phase 0 — Pre-flight gate

Two preflight checks run in order. Both must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/discover_helper preflight
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/devforge:init-forge`)
- `docs/architecture.md` (produced by `/devforge:generate-docs`)
- `.devforge/configure.yaml` (produced by `/devforge:configure`)
- `constitution.md` (produced by `/devforge:constitute`)

Exit 0 → all present + non-empty; proceed. Exit 2 → at least one missing or empty; helper emits a `BLOCKED:` message on stderr naming each missing artefact + producer command. On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/devforge:discover`.

**Memory read (same call).** The same `preflight` call also reads `.devforge/memory.md` — the project's persistent cross-session lessons file — and writes a JSON object to stdout ahead of the exit-code branch above, so the object is there on the pass and on the `BLOCKED` path alike. Capture that stdout and take `memory_state` from it; the object also carries `memory_excerpt` (the populated `## ` sections of that file, `## Task Outcomes` excluded) and `memory_present`. This changes nothing about the exit-2 handling above: on that path the JSON is extra output to ignore, and copying the stderr verbatim and ending the turn is still the whole response. If stdout carries no JSON object at all, treat it as `absent` and take the no-op branch below — the memory read never stops the run.

Branch on `memory_state`:

- `absent` or `stub` → no-op. Say nothing to the user about memory, raise no warning, add no step. A memory file that is missing, or still the stub the installer ships, records no lessons yet; on a new project that is the correct state, not a fault to remedy.
- `populated` → read `memory_excerpt` and pick out the entries that bear on this run's topic. Hold those in working memory now (so they are not lost during the rubric) and carry them into Phase 1's `integration_points` + `functional_scope` questions and Phase 2's investigation. Arriving there is the point: an entry can name a place to look — a related repository that is readable locally, a module to read before scoping — and one that surfaces only after Phase 1 has finalized the scope is too late to change which verbs Step 2.0 searches or which touchpoints Step 2.2 reconciles. When `memory_excerpt` comes back empty even though `memory_state` is `populated` — every populated line sits in the excluded `## Task Outcomes` section — take the `absent` / `stub` no-op branch above instead: carry nothing into Phase 1 or Phase 2, and say nothing to the user about memory.

The excerpt is not the whole file: it renders the file's populated `## ` sections — a section with no entries under its heading is dropped heading and all, `## Task Outcomes` is excluded outright, and any other section is kept — and when the line budget cannot fit a section whole, the lines it drops are always that section's EARLIEST ones, with an inline marker line right after the heading naming how many were omitted. So an entry's absence from a non-empty excerpt means it sits in the excluded section or behind a marker the excerpt itself declares, never "never recorded" — do not conflate these. An empty excerpt means there are no readable lessons: the file is absent or still the shipped stub, or everything in it sits in the excluded section.

**Honesty bound.** A carried memory entry is an UNVERIFIED prior-session assertion, not a fact about the codebase as it stands: it is a candidate evidence source and a constraint to check, never a finding and never grounds for a conclusion on its own. A past session wrote it, and the code it describes may have changed since — or the entry may have been wrong when it was written. It MUST NOT silently become a scope dimension's value, a prior-art or integration-touchpoint row, or the recommended design option: Step 2.2's fit-check is what produces this run's reality, and an entry is one more belief for it to reconcile rather than a shortcut past it.

### Phase 0.2 — CBM index refresh

```bash
.devforge/lib/generate_docs_helper preflight
```

This refreshes the CBM index stamp so Phase 2 graph queries see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. Helper non-zero exit: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn; user re-runs `/devforge:generate-docs` or `index_repository` and re-invokes `/devforge:discover`.

### Phase 0.3 — Topic argument

Two branches based on `$ARGUMENTS`:

- **`$ARGUMENTS` non-empty:** treat it as the topic. Proceed directly with the reset chain below (no AskUserQuestion, no turn break) in the same turn the command was invoked.
- **`$ARGUMENTS` empty:** ask the user via AskUserQuestion: `"What's the topic? (greenfield feature, one sentence)"` — single-line question text, free-text answer. End the turn. The user's reply arrives in the next turn as the topic. On the next turn: proceed with the reset chain below using the user's reply as `<topic>`.

Reset chain (runs in the turn determined by the branch above):

```bash
.devforge/lib/discover_helper reset-memo
.devforge/lib/discover_helper reset-report
.devforge/lib/discover_helper set-topic --value "<topic>"
.devforge/lib/discover_helper set-verbatim-prompt --value "<full raw $ARGUMENTS>"
.devforge/lib/discover_helper set-date --value $(date -u +%Y-%m-%d)
```

`reset-memo` + `reset-report` write fresh-defaults state. `set-topic` auto-derives `topic_slug` for the eventual filename. `set-date` enforces `YYYY-MM-DD`. `set-verbatim-prompt` persists the full original prompt the user passed to `/devforge:discover` — the complete `$ARGUMENTS`, NOT the one-sentence topic `set-topic` records. `$ARGUMENTS` may carry a multi-sentence feature description; the topic is a curated paraphrase, so the un-paraphrased boundary input would otherwise be lost after Phase 0.3. Persisting it here is what lets Phase 4's `finalize-handoff` carry it into the handoff as `Intent.verbatim_prompt`, so a downstream stage can tell what the user ACTUALLY asked from what this command INTERPRETED (per plan 18 Step 1). When `$ARGUMENTS` was empty and the topic came from the AskUserQuestion fallback above, pass that same user reply as `--value` — it is the verbatim input in that branch.

Fresh-every-run: `reset-memo` + `reset-report` ALWAYS run at Phase 0.3, unconditionally. Any prior `.devforge/discover-scope.json` + `.devforge/discover-report.json` are overwritten with fresh defaults. `/devforge:discover` does not resume mid-flight prior runs — every invocation starts clean. If the user killed a prior run mid-investigation, that work is lost; re-answer the rubric from scratch.

### Phase 0.4 — Suspected-fit classification (pre-rubric, runs before Phase 1)

A `/devforge:discover` prompt sometimes carries a placement guess alongside the feature idea — a clause asserting WHERE the feature should live or HOW it should be built ("this belongs in the auth module", "we should reuse the existing queue", "probably a new service", "the bottleneck is …"). Scan the verbatim prompt persisted by `set-verbatim-prompt` for any such lead-in BEFORE the eight-dimension rubric runs. A user-supplied placement or mechanism guess is a CLAIM TO RECONCILE, not a fact: it MUST NOT silently become a scope dimension's value or the recommended design option. It belongs in the user-belief lane that Phase 2's Stream B fit-check reconciles against codebase reality.

When such a clause is present, record it as a gap against the `integration_points` dimension (the dimension whose captured value is explicitly the user's BELIEF about where the feature lives — see the Rubric dimensions table — reconciled vs reality in Phase 2):

```bash
.devforge/lib/discover_helper record-gap \
    --dimension integration_points \
    --description "user-supplied placement guess (confirm via Phase 2 fit-check): <verbatim guess>"
```

Recording it as a gap (not as a settled `integration_points` value) keeps the guess a claim the fit-check must confirm or refute — the same separation `/devforge:research` enforces via its hypothesis lane. This pre-rubric classifier is the home Step 5's binary-classification gate routes `hypothesis` statements into (per plan 18 Step 5 — the user-facing front door over this same lane). **Discover's hypothesis lane diverges from `/devforge:research`'s and a Step-5 builder must respect the divergence:** discover's lane IS the `record-gap --dimension integration_points` call already above in this Phase 0.4 — it has NO `record-hypothesis` verb (that is `/devforge:research`-only). Do NOT mirror `/devforge:research`'s `record-hypothesis` into `/devforge:discover`; route a classified `hypothesis` to this `record-gap` call instead. And discover's backstop against a leaked guess is the Phase 2 fit-check + the Step-5 echo-back human gate, NOT a `verify-hypothesis-suppression` gate (no such verb exists for `/devforge:discover` — see the callout below). The captured guess does NOT enter any scope dimension's value and does NOT pre-commit a design option.

When the prompt carries NO placement or mechanism guess, this step is a no-op — proceed directly to Phase 0.5.

**No mechanical suppression gate in `/devforge:discover`.** Unlike `/devforge:research`, `/devforge:discover` has no hypothesis/probe-tier machinery and no `verify-hypothesis-suppression` verb. The discover backstop against a guess leaking into design direction is the Phase 2 Stream B fit-check plus the Step-5 echo-back human gate, NOT a mechanical suppression check.

### Phase 0.5 — Intake-interrogation gate (user-facing front door, runs before Phase 1)

Phase 0.4 silently recorded any placement / mechanism guess as a gap against `integration_points`; Phase 0.5 is the USER-FACING front door over that same machinery. It surfaces the framework's interpretation of the verbatim prompt for ONE confirmation before the Phase 1 rubric commits scoping cost — this is the gate that closes the over-solve failure (plan 18 Step 5: in the original failure the user never saw, and so could never correct, the framework's interpretation). Phase 0.5 does NOT re-run Phase 0.4's detection logic — it reuses the detection decision Phase 0.4 made (a placement / mechanism guess is a scope-expander; everything else is a requirement) and adds the minimality challenge + echo-back + confirmation on top. Phase 0.4's only helper call is `record-gap --dimension integration_points` for the guess; the binary `requirement`-vs-scope-expander split is first persisted at Phase 0.5 Step 1, via `record-intake-classification`.

**Discover lane divergence (do NOT mirror `/devforge:research`).** Discover has NO `record-hypothesis` verb and NO research-shaped hypothesis lane — a classified scope-expander routes to `record-gap --dimension integration_points` (the Phase 0.4 call already above), NOT to `record-hypothesis`. The echo-back render uses scope-expander wording ("Scope-expanders to verify — NOT requirements"), not the research "suspected cause" wording. This is the same divergence stated in Phase 0.4; a builder must preserve it. `record-intake-classification --kind hypothesis` is the tag the discover echo-back reads — that `hypothesis` kind value names a scope-expander here, not a bug-cause hypothesis.

**PROPORTIONALITY (HARD requirement — not advice).** The gate is PROPORTIONATE, inheriting the same proportionality the Phase 1 rubric already carries (its turn caps + accept-gaps coverage exit). Auto-classify the easy parts; surface to the user ONLY the high-stakes ambiguities — conflations (a requirement mixed with a placement guess), scope-expanders (a "we should also …" speculative addition not in the stated feature intent), and big-design-driving placement guesses (a "this belongs in module X" guess that would shape the design). It is NOT a 20-question inquisition. A clean prompt — no scope-expander, no placement guess, one obvious minimal scope — passes with ONE echo-back confirmation and ZERO interrogation. Over-interrogating a trivial feature idea is itself the over-build failure mode this gate exists to fight.

#### Step 1 — Binary-classify each statement

Partition the verbatim prompt (the field `set-verbatim-prompt` persisted in Phase 0.3) into statements and classify each as one of TWO classes: `requirement` (the feature intent — what the user asked for) vs `hypothesis` (a scope-expander or placement guess). Reuse Phase 0.4's detection: a placement / mechanism clause ("this belongs in the auth module", "we should reuse the existing queue", "probably a new service") was already detected there and recorded as a gap against `integration_points` via `record-gap`; here that same statement is ALSO tagged `hypothesis` for the echo-back. Everything else is a `requirement`. Record each statement:

```bash
.devforge/lib/discover_helper record-intake-classification \
    --statement "<the prompt statement, verbatim or lightly paraphrased>" \
    --kind <requirement|hypothesis> \
    --minimal-fix "<see Step 2 — pass on requirement statements>"
```

The setter is idempotent on `--statement`: re-recording the same statement overwrites its prior `--kind` + `--minimal-fix` (this is the mechanism the `correct` branch in Step 3 uses). `--kind` must be exactly `requirement` or `hypothesis` (the helper rejects any other value with exit 2); the `hypothesis` value names a scope-expander in discover, per the divergence above. A classified scope-expander is ALSO routed to `record-gap --dimension integration_points` (per Phase 0.4) — `record-intake-classification` does NOT route it automatically; the two calls are separate. On a clean single-requirement feature idea this is ONE call with `--kind requirement`; do not manufacture extra statements to classify.

#### Step 2 — Minimality challenge

Compose the SIMPLEST scope that satisfies the stated feature intent ALONE, and pass it as `--minimal-fix` on the requirement statement. Any addition beyond that simplest scope — a "we should also …" speculative feature, an extra integration the user only guessed at — is an "extra" the user must CONSCIOUSLY opt into; it is never assumed into the minimal scope. `--minimal-fix` is optional on the setter (omit it on `hypothesis`/scope-expander statements — their minimal scope is the feature without the speculative addition), but for the requirement statement carrying the feature intent it is REQUIRED: it is the surface the user confirms or corrects.

#### Step 3 — Echo-back + ONE confirmation

Render the echo-back block and surface it for confirmation:

```bash
.devforge/lib/discover_helper render-intake-echo
```

The helper owns the block shape — `## Intake interpretation` with a `### Requirements (what you asked for)` section (each requirement + its `Minimal scope:` line), a `### Scope-expanders to verify — NOT requirements` section (omitted entirely when no scope-expander was classified — the proportionality rule), and a `### Minimal scope` section. The scope-expanders section is where a "we should also …" addition or placement guess surfaces as "scope-expander to verify, not a requirement," and its routing text names `record-gap --dimension integration_points` (NOT a research hypothesis lane). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) — this is the established verbatim-echo convention; the orchestrator does NOT re-shape the block.

Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]`. End the turn. The user's reply opens the next turn.

- On `confirm`: proceed to Phase 1.
- On `correct`: the user names what was misclassified (a statement that should flip `requirement`↔scope-expander, or a minimal scope that scoped too wide). Re-record the affected statement(s) via `record-intake-classification` (the idempotent overwrite on `--statement`), then re-run `render-intake-echo` and echo the corrected block ONCE more. Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]` (same options — this is the ONE bounded correction). End the turn. On the next reply: `confirm` → proceed to Phase 1; `correct` (or any other reply) → proceed to Phase 1 regardless. The gate allows AT MOST one correction pass — it does not loop, so even a second `correct` advances to Phase 1 rather than re-entering this branch.

When the prompt is a clean single-requirement feature idea with no scope-expander and one obvious minimal scope, Steps 1-2 are a single `record-intake-classification --kind requirement --minimal-fix "…"` call and Step 3 is one echo-back the user confirms in a single turn — zero interrogation, per the proportionality requirement above.

### Phase 0.6 — Re-entry from `/devforge:grill` (conditional — skip if no seed)

Before beginning the investigation, check for a `/devforge:grill` re-entry seed. Glob `specs/*/grill-seed.json`. If any matched file has a `target_stage` equal to `"discovery"` (this command's stage), you are re-entering from a `/devforge:grill` RE-ENTER-UPSTREAM verdict — the design-time grill proved a plan defect was rooted in THIS discovery / build-vs-buy stage's conclusion, and the re-run must be DIRECTED so it does not re-derive the invalidated conclusion. Read that seed and treat it as a binding directive for this run. Read it DIRECTLY: parse the matched file's flat JSON inline — do NOT call any grill helper or `grill_helper` verb (the orchestrator reads the file itself, so this block stays valid even if `/devforge:grill` is ever removed). The seed carries these fields:

- `feature` — the feature this seed was emitted for; read it from the seed and state it up front in your re-entry message (do NOT infer it from the file path).
- `prior_conclusion` — what the previous discovery / build-vs-buy conclusion was; it was invalidated, so do NOT re-derive it.
- `invalidating_evidence` — how `/devforge:grill` proved it wrong, grounded in the plan / spec / code.
- `must_satisfy` — what this re-run must now additionally satisfy; address it explicitly.
- `carried_findings` — prior findings to carry forward; stay monotonic (never re-surface a finding a prior pass already disproved).

State up front in your first user-facing message that you are running in grill-re-entry mode for the named `feature`, and name how this run addresses `must_satisfy`. Then run Phases 1–4 with the seed's directive constraining the investigation, and with Phase 4 in attach mode per the next paragraph.

**Attach mode — the feature directory already exists.** Hold the matched seed file's PARENT DIRECTORY in working memory as this run's `<feature_dir>`. Because that directory was allocated by the earlier run of this feature, Phase 4's save flow SKIPS allocation and SKIPS branch creation, and overwrites the discovery report + handoff in place; the superseded versions stay recoverable from the earlier `[WIP]` commit. The parent directory is a path fact about where the seed was found — it is NOT the seed's `feature` field, which is the name you state in user-facing text.

This block only READS the seed's directive. It does NOT delete the seed or change its `cycle_count` — seed lifecycle (deleting or incrementing `cycle_count` after consumption) is handled by the next `/devforge:grill` run, which reads `carried_findings` to stay monotonic. That is a v1 simplification; do not add seed-deletion logic here.

When no `specs/*/grill-seed.json` file matches `target_stage == "discovery"` (the normal case — a `/devforge:grill` run writes a seed only when it reaches a RE-ENTER-UPSTREAM recommendation AND the user picks the matching re-entry at its human gate, and most runs never reach one), this block is a no-op: proceed directly to Phase 1, and Phase 4 allocates a fresh feature directory on save.

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

### Design-reference capture (supplementary — non-gating)

Some features target a UI surface with a design reference — an HTML export, a Figma node, or a screenshot — that expresses what the built UI should look like. Capture it here so that intent is recorded once at intake as a structured anchor rather than left in prose. Ask one supplementary free-text prompt: ``"Is there a design reference for this feature's UI — an HTML export, a Figma node, or a screenshot? If so, name the kind, the file path or URL, and which element selector(s) carry the intent (e.g. a class like `.fooBar`). If none, answer 'none'."`` — single-line question text, free-text answer. After the user replies:

- If the user names a reference, compose `--value` as `<scheme>:<target>` (`scheme` = `html` / `figma` / `screenshot` matching the named kind; `target` = the file path or URL) and `--selectors` as a JSON array of the named intent selectors:

  ```bash
  .devforge/lib/discover_helper set-scope-design-anchor \
      --value "html:design/reference.html" \
      --selectors '[".fooBar", ".badge"]'
  ```

- If the user names none (no reference, or the feature has no UI), record the empty anchor:

  ```bash
  .devforge/lib/discover_helper set-scope-design-anchor \
      --value "none" \
      --selectors '[]'
  ```

The helper validates `--value` as a design-source `scheme:target`; a value whose scheme is not one of `html` / `figma` / `screenshot` / `none` is rejected with a non-zero exit and nothing is persisted, so pass a well-formed `scheme:target` or the bare word `none`. This capture is OPTIONAL and is NOT one of the eight rubric dimensions above — it does not participate in the coverage check or `scope-finalize`, so an unanswered design-reference question never blocks finalization. This call does NOT gate progression. Advance to the docs scan regardless of the user's answer.

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

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift and refinement classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns within the same `/devforge:discover` run by reading prior assistant messages in the conversation.

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

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string or an enum-spelling miss), retry up to 3 times. On the 4th failure, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) and end the turn; user must re-run `/devforge:discover` from scratch — prior partial state will be overwritten.

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

5. **Absence probe** — run this setter when setter 4's `--recommendation` is `Build` AND Step 2.0 recorded no `internal:` prior-art entry (the run whose gate message read `Internal canonical-pattern search found 0 existing implementations.`). Those two together are a bare absence claim — nothing internal covers this, so build it — and git history is the one source that can refute it: the capability may be missing because someone deliberately deleted it.

   Probe the plausible name and location the capability would have occupied, using either query or both:

   ```bash
   git log -S "<symbol the capability would have been named>"
   git log --diff-filter=D -- <path the capability would have lived under>
   ```

   Run both queries against the repository that holds the project's source code — in a wrapper-mode install that is the nested Source Root, not the install root. Querying the wrong root returns an empty history indistinguishable from a genuine absence, and the `--found false` you would record from it satisfies the guard exactly as a real one does — so confirm which repository you are querying before recording, since no step in this command resolves that root for you.

   Then record what the probe found — one call per claim probed:

   ```bash
   .devforge/lib/discover_helper record-absence-probe \
       --claim "<one-line: what is claimed absent>" \
       --symbol "<the -S token, or none>" \
       --path "<the --diff-filter=D path, or none>" \
       --found false
   ```

   When the probe DID surface a prior deletion, `--found true` requires both commit flags; `--found false` forbids them:

   ```bash
   .devforge/lib/discover_helper record-absence-probe \
       --claim "<one-line: what is claimed absent>" \
       --symbol "<the -S token, or none>" \
       --path "<the --diff-filter=D path, or none>" \
       --found true \
       --deleted-commit-sha "<7-40 char hex sha of the deleting commit>" \
       --deleted-commit-subject "<one-line subject of that commit>"
   ```

   Pass the literal `none` for whichever query this probe did not run; the helper rejects a call where BOTH are `none`, since such a row names no target.

   Phase 4's `finalize-handoff` rejects a save whose report is absence-founded and carries no probe — the guard asks only whether a probe was recorded, never what it found. Run the probe here, in Phase 3, rather than meeting that rejection at the save flow's step 5, where the report is already on disk and only the handoff fails. Finding a prior deletion does NOT overturn the Build recommendation: the author may have good reason to rebuild, but a deletion you found and left unexplained is what the reader most needs — say in setter 4's `--reasoning` WHY the recommendation stands despite it. The SHA and subject already render in the report's `## Absence Probes` section, so do not re-type them there: the structured row carries what the history showed, the prose carries what you concluded from it — the same split `/devforge:research` draws between its archaeology row and its recommended-approach rationale. Finding nothing is an equally valid and sufficient outcome: `--found false` records a real, now-verified absence and satisfies the guard exactly as `--found true` does.

6. **Derisk plan** — at least 1 item; each item is a one-line action that reduces uncertainty before commitment (e.g., spike, prototype, contract test, vendor benchmark):

   ```bash
   .devforge/lib/discover_helper set-derisk-plan --items '["item-1","item-2","item-3"]'
   ```

7. **Constitution constraints** — read `constitution.md` for rules that bear on the recommended option + integration touchpoints. For each rule that constrains or enables the design, call the setter (call 0..N times — omit entirely when no rule applies):

   ```bash
   .devforge/lib/discover_helper set-constitution-constraints \
       --rule "<rule reference, e.g. '§3.2 Error Handling'>" \
       --impact "<how it constrains or enables the recommended option>"
   ```

8. **Verdict** — one of `Worth pursuing` / `Promising with caveats` / `Reconsider`. Apply the verdict-flip rule (invariant D): when `overall_fit ∈ {Strained, Misfit}` OR `effort_estimate = "Major refactor required"`, the verdict MUST be `Reconsider`, UNLESS the Phase 1 finalize set `memo.override_recorded = True` (via `scope-finalize --accept-gaps`):

   ```bash
   .devforge/lib/discover_helper set-verdict --value "<verdict>"
   ```

9. **Recommendation** — concrete next action + one-line "what happens next":

   ```bash
   .devforge/lib/discover_helper set-recommendation \
       --action "<concrete next action>" \
       --next "<one-line description of the immediate next step>"
   ```

10. **Next-step text** — composed by the helper from `memo.functional_scope` + `memo.users` + `memo.success_criteria` + `report.verdict` + `report.recommended_option`. Call the subcommand on every verdict — on `Worth pursuing` / `Promising with caveats` the helper composes a copy-pasteable handoff block; on `Reconsider` the helper clears `next_step_text` to `None` so the rendered report omits the Next-Step section (invariant E enforces this in `verify`).

   Pass an LLM-distilled 1-2 sentence topic via `--topic`. Compose the topic yourself from `memo.functional_scope` + `memo.users` + `memo.success_criteria` — keep it ≤2 sentences and ≤200 characters; never copy the entire `functional_scope` value verbatim. The distilled topic becomes the argument inside `/devforge:specify "..."` at the top of the handoff block (that literal invocation string is composed by the helper — it is the helper's string, not this spec's, so do not rewrite it here). The helper strips literal `\n` escape sequences from the topic and from the embedded key-fact values; do not rely on that as a license to pass multi-paragraph junk — the cleanup is defensive, not stylistic.

   ```bash
   .devforge/lib/discover_helper set-next-step-text \
       --topic "<1-2 sentence distilled topic, ≤200 chars>"
   ```

   On `verdict = Reconsider`, omit `--topic`; the call clears `next_step_text` regardless:

   ```bash
   .devforge/lib/discover_helper set-next-step-text
   ```

   Call it here WITHOUT `--feature-dir`. The feature directory does not exist yet — Phase 4's save flow allocates it only after the user confirms the save — so on the proceeding verdicts the helper renders the reference line as `Discovery reference: (path assigned when this discovery is saved to its feature directory)`. That placeholder is intentional: the Phase 3 render is a preview the user sees before the directory is named, so it must not show a location that could turn out to be wrong. Keep the `--topic` value you passed here in working memory — Phase 4's save flow re-runs this exact call with `--feature-dir` added once the directory exists.

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

On non-zero exit: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/devforge:discover` from scratch (all prior state will be overwritten).

### Render

```bash
.devforge/lib/discover_helper render
```

Helper walks the locked schema and emits the full discovery report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order, heading levels, and table shapes.

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the rendered report.

This render is a PREVIEW — no file is written from it. On the proceeding verdicts its `Discovery reference:` line still carries the placeholder described above. Phase 4's save flow re-renders after the feature directory exists, and those later bytes are the ones written to disk.

The LLM does NOT edit the rendered report via Write or Edit at any point. The helper's `render` is the only composer of that markdown; any post-render fix is applied by re-calling the relevant setter + `render` + `verify` in a new turn.

## Phase 4 — Save + recommend

Phase 4 is the only phase that writes outside `.devforge/` scratch. Nothing below the save prompt runs until the user confirms the save, and a run the user declines to save leaves the repository untouched — no directory, no branch, no report, no handoff, no commit.

### Ask to save

After echoing the rendered report, propose the feature name, then ask ONE question. There is no separate feature-name question: the save prompt carries the proposal, and AskUserQuestion's own free-text row is the override path.

**Compose the proposed feature name.** Start from `memo.topic_slug` (auto-derived by `set-topic` at Phase 0.3; visible in the `read-memo` output read at the start of Phase 3) and normalize it to a 2-4 word lowercase kebab-case slug — first character a letter, 2 to 4 alphanumeric segments joined by `-` (e.g. a topic slug of `auth-in-a-typescript-backend-framework` becomes `typescript-auth-backend`). `allocate-feature-dir` rejects any value outside that shape, so a `topic_slug` with 5+ segments MUST be shortened here rather than passed through. This confirmed slug is the `--slug` value step 1 passes to `allocate-feature-dir`; the rest of Phase 4 calls it `<feature-name>`.

Then ask via AskUserQuestion `"Save this discovery as feature '<feature-name>'?"` with options `["Save as <feature-name>", "Don't save"]`. Single-line question text. Do NOT add an explicit "Other" option — AskUserQuestion always offers a free-text row of its own. Name `Save as <feature-name>` as the recommended choice in the prose above the question.

End the turn. The user's reply opens the next turn. Read the reply as:

- `Save as <feature-name>` → save under the proposed slug; run the `### On save` flow.
- `Don't save` → run the `### On don't-save` branch.
- **Free text** → treat it as "save, and this text is the feature name", UNLESS the text clearly declines (`"no"`, `"skip"`, `"not now"`, or equivalent), which is a `Don't save`. Normalize the text to the same 2-4 word lowercase kebab-case shape and use it as `<feature-name>`. If it cannot be normalized (no alphanumeric content to work with), ask this same question once more with a corrected proposal and the same two options, then end the turn.

This prompt is also re-entered from `### On save` step 1 when `allocate-feature-dir` rejects the slug; the reply branches above apply unchanged on that second pass.

**Attach-mode variant.** When Phase 0.6 recorded an existing feature directory, its name is already fixed and cannot be renamed by this run. Ask instead: `"Save this discovery into the existing feature '<feature>'?"` with options `["Save to <feature>", "Don't save"]`, where `<feature>` is the seed's `feature` field — per Phase 0.6's rule that the seed's `feature` is what your messages NAME while its parent directory is where they WRITE. A free-text reply that does not clearly decline still means save; the existing directory is NEVER renamed and the free text is NOT used as a slug.

### On save

Six steps, in this order. Steps 1 and 2 are the only skippable ones, and only in attach mode.

**1 — Resolve the feature directory.**

In attach mode (Phase 0.6 recorded an existing feature directory), that directory IS this run's `<feature_dir>` for the rest of this flow: skip this step's helper call, skip step 2 entirely, and go to step 3.

Otherwise allocate a fresh directory:

```bash
.devforge/lib/discover_helper allocate-feature-dir --slug "<feature-name>"
```

Exit 0 → stdout is a JSON object. Take `relative_path` from it — that value is this run's `<feature_dir>`, and it is what every step below writes into. Hold it in working memory exactly as the helper reported it: do not re-shape it, do not rebuild it from any other key on that object, and do not substitute the sibling `path` key, whose absolute form step 3 would hand to `set-next-step-text --feature-dir`, which renders it verbatim into the `Discovery reference:` line step 4 writes to disk and step 6 commits. No step in this command reads `path`. Take `formatted_number` as well; it is step 2's `--number` input and this command reads it for nothing else, so no step composes a path from it.

Exit 2 → copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then branch on which error the helper cited. Nothing has been written to the repository in either branch:

- **`invalid slug ...`** — the helper rejected `<feature-name>` against the 2-4 word lowercase kebab-case shape. Do NOT end the run. Compose a corrected name that satisfies that shape and return to `### Ask to save`, re-asking that question with the corrected proposal; end the turn there. Sending the user back to re-invoke `/devforge:discover` instead would be destructive: Phase 0.3 resets the memo and report unconditionally on every invocation, so the eight rubric answers and the whole Phase 2 investigation would be thrown away over a name the user can fix in one turn.
- **Any other error** (`feature dir already exists ...`, `cannot create ...`) — a filesystem condition this run cannot compose its way out of. End the turn; the user resolves the cited condition and re-invokes `/devforge:discover`.

A seedless run ALWAYS allocates a new directory, even when an earlier `/devforge:discover` already covered the same topic — this command does no topic matching against existing features. Say so in the closing message so the user can delete the duplicate if that was not the intent.

**2 — Create the feature branch.** (skipped in attach mode)

Read the current branch with `git branch --show-current`. Resolve the repository's default branch in this order, stopping at the first that succeeds:

1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` — parse the branch name off the end of the output (`refs/remotes/origin/main` → `main`).
2. `git show-ref --verify --quiet refs/heads/main` → `main`.
3. `git show-ref --verify --quiet refs/heads/master` → `master`.

If the current-branch command fails (for example the install root is not a git repository) or none of the three resolves a default branch, SKIP this step: tell the user no branch was created and name which of the two reasons applied — adding that they can create one with `git checkout -b spec/NNN-<feature-name>` when the repository does exist — then continue to step 3. Do not ask the user and do not stop the save — the artefacts, not the branch, are what this phase exists to produce.

With both branch names in hand:

```bash
.devforge/lib/discover_helper render-branch-command \
    --slug "<feature-name>" \
    --number "<formatted_number from step 1>" \
    --current-branch "<current branch>" \
    --default-branch "<default branch>"
```

Stdout is exactly one line. When it is a `git checkout -b spec/NNN-<feature-name>` command, execute that line as written and tell the user `"Created and switched to branch spec/NNN-<feature-name>"`. When it is a `# already on non-default branch ...` informational comment, no checkout is emitted — continue to step 3 unchanged.

**3 — Re-render the report against the real feature directory.**

Re-run the EXACT `set-next-step-text` call Phase 3's setter 10 made — same `--topic` value, or no `--topic` at all when the verdict is `Reconsider` — with `--feature-dir` added, then re-render:

```bash
.devforge/lib/discover_helper set-next-step-text \
    --topic "<the same distilled topic passed in Phase 3>" \
    --feature-dir "<feature_dir>"

.devforge/lib/discover_helper render
```

The helper now renders `Discovery reference: <feature_dir>/discovery-report.md` in place of the Phase 3 placeholder. That reference line is the ONLY difference between these bytes and the ones echoed in Phase 3.

**4 — Write the report.**

Write step 3's `render` stdout byte-verbatim to `<feature_dir>/discovery-report.md`. The verbatim invariant binds THIS render, not the Phase 3 preview: use the bytes the helper just printed, and do not re-format, re-shape, or hand-merge them with the earlier echo. In attach mode this overwrites the previous run's report in place, which is intended — the superseded version stays recoverable from the earlier `[WIP]` commit.

**5 — Write the handoff.**

```bash
.devforge/lib/discover_helper finalize-handoff --feature-dir "<feature_dir>"
```

The helper writes `<feature_dir>/discover-handoff.json` and records the sibling report at `<feature_dir>/discovery-report.md`. The report stem (`discovery-`) and the handoff stem (`discover-`) differ on purpose — pass `--feature-dir` and let the helper own both names. On exit 0 stdout is a `wrote: <path>` line; surface that path to the user. On non-zero exit: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), tell the user the report is saved but the handoff is missing so `/devforge:specify` will block until it exists, and end the turn — the fix is to correct the cited violation with the relevant Phase 3 setter and re-run this one command with the same `--feature-dir`, NOT to re-run `/devforge:discover` (which would allocate a second directory).

**6 — Commit both artefacts.**

```bash
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["<feature_dir>/discovery-report.md", "<feature_dir>/discover-handoff.json"]' \
    --label "discover: <topic-slug>"
```

The label keeps using the run's `topic_slug`, not the confirmed feature slug — it is a commit-message label, not a path, and the two differ whenever the user renamed the feature at the save prompt. The helper stages those paths in the install repo and makes a `[WIP] discover: <topic-slug>` commit; it is install-repo-only (never the source repo in wrapper mode). This call is UNCONDITIONAL — always run it once steps 4 and 5 have written both files. It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artefacts are already saved, so warn the user with the helper's stderr and continue; do NOT abort the command or re-run the save); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op.

### On don't-save

Nothing is written outside `.devforge/` scratch: no feature directory is allocated, no branch is created, neither the report nor the handoff is written, and no `[WIP]` commit fires. The rendered report stays in the assistant message only. `.devforge/discover-scope.json` and `.devforge/discover-report.json` remain on disk until the next `/devforge:discover` invocation overwrites them — re-run `/devforge:discover` and save to produce the feature directory with both artefacts in it.

### Closing message

If a save happened AND the verdict is in the proceeding-set (`Worth pursuing` / `Promising with caveats`), the written report already contains a `## Next Step` section with a copy-pasteable handoff block. Tell the user: `"/devforge:discover is done. Open <feature_dir>/discovery-report.md to review. The 'Next Step' section at the bottom is a copy-pasteable block for your next session — copy it manually when you're ready."`

If a save happened AND the verdict is `Reconsider`, the report omits the Next-Step section. Tell the user: `"/devforge:discover is done. Open <feature_dir>/discovery-report.md to review. The verdict was 'Reconsider' — address the cited concerns or refine scope before continuing."`

On either saving branch, also state which directory was used and how — a fresh allocation: `"Allocated a new feature directory <feature_dir> for this discovery; delete it if you meant to add to an existing feature."`; attach mode: `"Overwrote the discovery artefacts in the existing feature directory <feature_dir>."` When step 2 created a branch, name that branch too.

If the user chose `Don't save`, tell the user: `"/devforge:discover is done. The report is in the prior message; no feature directory, report, or handoff was written and no branch was created. .devforge/discover-scope.json and .devforge/discover-report.json hold the state but will be overwritten on the next /devforge:discover invocation."`
