---
name: plan
description: Translate an approved spec into a technical implementation plan with architecture decisions, layer map, file impact, and risk assessment.
argument-hint: "[spec-file]"
---

# /devforge:plan — Technical Implementation Plan

`/devforge:plan` is repeatable per feature. It takes an approved spec authored by `/devforge:specify` and produces a technical plan: research findings, optional data model, optional API contracts, architecture decisions, layer map, file impact, and risk assessment. The orchestrator (the LLM following this spec) writes all plan artefacts in the main thread via Write or Edit. Subagent dispatch is reserved for **decision work at two mandatory hooks**: the `architect` agent is invoked at Phase 1.3 (Architecture Decisions) for every run, and at Phase 0 Step 3 when 2+ architectural alternatives are being compared. Outside those hooks, the orchestrator authors directly — no per-phase auto-dispatch. Phase 0's hard gate ensures the one-time setup chain (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) has completed before any plan work fires, and Phase 0a.8 additionally hard-gates on a fresh `/devforge:spec-check` report for the resolved spec. Produces `<feature_dir>/plan.md` plus optional supporting docs, and ends with a manual handoff to `/devforge:breakdown` — no automated dispatch.

Usage: `/devforge:plan [spec-file]` (e.g. `/devforge:plan <feature_dir>/spec.md`, or `/devforge:plan` with no argument to use the most-recently-modified spec under `specs/`).

## Outputs of this phase

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run reads from and writes into: one path the orchestrator holds in working memory for the rest of the run. PHASE 0a resolves it: `pick-spec` prints the absolute path of one `spec.md`, and that file's parent directory is `<feature_dir>`. Hold it exactly as PHASE 0a resolved it — do not re-shape it, do not rebuild it from parts, and do not spell what is inside it. Every artifact path below is `<feature_dir>` plus a filename, and so is every sibling this command reads beside the spec.

- `<feature_dir>/plan.md` — rendered plan markdown (required).
- `<feature_dir>/research.md` — when 1+ signals detected per Phase 0 (conditional).
- `<feature_dir>/data-model.md` — when the feature involves new or changed entities (conditional).
- `<feature_dir>/contracts.md` — when the feature involves new or changed API contracts (conditional).

On approve, Phase 4 `[WIP]`-commits `spec.md` (whose `**Status**:` Phase 0b flipped) + `plan.md` + `plan-handoff.json` (plus whichever of `research.md` / `data-model.md` / `contracts.md` this run actually wrote) into the install repo via `.devforge/lib/artifact_helper commit-artifacts` (install-repo-only, fail-soft) so the plan artifacts — and the spec's Phase-0b status flip — are git-safe the moment they exist on disk; the commit folds into `/devforge:finalize`'s squash.

## Context in the Workflow

```
/devforge:research (optional) → /devforge:specify → /devforge:spec-check → /devforge:plan → /devforge:grill → /devforge:breakdown → /devforge:implement → /devforge:review → /devforge:verify → /devforge:summarize → /devforge:finalize
```

`/devforge:plan` runs AFTER the spec is approved, BEFORE task breakdown. It answers technical questions the spec intentionally left open (specs describe WHAT, plans describe HOW).

A fresh `/devforge:spec-check` report for the resolved spec is a precondition of this command: Phase 0a.8 blocks the run when no `spec-check.md` sits next to the spec, when the report carries no verifiable spec-content hash, or when its recorded hash no longer matches the current spec. That gate reads the report's presence and freshness only — never its verdict.

## PHASE 0a: Spec resolution

`/devforge:plan` consumes one approved spec per invocation. Resolve which spec via the helper:

```bash
.devforge/lib/plan_helper pick-spec $ARGUMENTS
```

If `$ARGUMENTS` is non-empty, the helper validates the explicit file path (must be an existing `spec.md` file, not a directory) and prints its absolute path on stdout. If empty, the helper picks the most-recently-modified `spec.md` under `specs/` whose shape passes 9-section validation. Exit 2 means no valid spec was found — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

Capture the resolved absolute path. Its parent directory is this run's `<feature_dir>` — hold that too, exactly as resolved, because every artifact this command writes and every sibling it reads is `<feature_dir>` plus a filename. Then render the preview block:

```bash
.devforge/lib/plan_helper render-pick-summary <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block. Then ask the user via `AskUserQuestion`:

- Question: `"Process this spec?"` — single-line text.
- Options: `["yes", "pick-other", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`yes`** → proceed to Phase 0a.5 with the resolved path.
- **`pick-other`** → in the next turn, run `.devforge/lib/plan_helper list-specs` and emit stdout as a numbered list inside a fenced block. The helper output is unbounded (one line per spec, mtime desc). For `AskUserQuestion`, take the first four lines as the four option labels — AskUserQuestion caps at four options, so the LLM truncates client-side, not the helper. Question: `"Which spec to plan against?"` — single-line text. If more than four specs exist, include `other` as the fourth option; on `other`, ask the user via free-text follow-up for the explicit path, then re-run `pick-spec <path>` to validate. On the chosen path, treat it as the resolved path and proceed to Phase 0a.5.
- **`cancel`** → tell the user `"/devforge:plan cancelled. Re-run /devforge:plan when ready."` and end the turn.

## PHASE 0a.5: Upstream handoff discovery

`/devforge:specify` may have written a sibling `handoff.json` next to the spec, which can point upstream to a `/devforge:research` or `/devforge:discover` handoff carrying the HOW seed. This phase is informational — it surfaces that seed for the planning phases. There is no user gate here; do not invoke `AskUserQuestion`.

Check for a sibling handoff via the helper:

```bash
.devforge/lib/plan_helper read-specify-handoff <resolved-path>
```

- Stdout `no-handoff` → tell the user `"No upstream handoff; planning cold from the spec."` and proceed to Phase 0a.6 with the resolved path.
- A 4-line block (lines `spec-handoff:`, `spec_seeds:`, `upstream_handoff_path:`, `upstream_handoff_kind:`) → read its `upstream_handoff_path` line:
  - value `none` → tell the user `"Spec has no upstream research/discover handoff; planning cold."` and proceed to Phase 0a.6 with the resolved path.
  - a path → render the plan seeds via the helper, passing the `spec-handoff:` value from the 4-line block as the argument:

    ```bash
    .devforge/lib/plan_helper render-plan-seeds <spec-handoff-path>
    ```

    - Stdout `cold-no-plan-seeds` → tell the user `"Upstream handoff carries no plan seeds; planning cold."` and proceed to Phase 0a.6 with the resolved path.
    - A `## Upstream plan-seeds` block → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). State that this block is the HOW seed and is the authoritative starting point for Phase 0 (Research Evaluation — if it already cites canonical patterns or a recommended approach, you have prior art; calibrate research depth instead of rediscovering), Phase 1 (Technical Design), and Phase 1.3 (Architecture Decisions — where the architect consultation fires and the key design decisions are drafted). If your plan diverges from the upstream recommendation, state the divergence and why in the plan's "Specialist Consultation" section — do not silently discard it. Then proceed to Phase 0a.6 with the resolved path.

Exit 2 from either helper means the sibling handoff is malformed or the upstream pointer is dangling/unknown — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

## PHASE 0a.6: Spec drift check

The spec may have been written against source files that changed since. This phase is informational/gate only — it surfaces drift in the spec's §4-cited files before planning starts.

Check for drift via the helper:

```bash
.devforge/lib/cbm_sync_helper check-spec <resolved-path>
```

Stdout is one of four forms:

- `current` — the spec's cited files are unchanged since it was stamped. Proceed silently to Phase 0a.7 with the resolved path; no message needed.
- `missing` — no drift stamp exists for this spec. Tell the user `"No drift stamp for this spec; proceeding."` and proceed to Phase 0a.7 with the resolved path.
- `drift <a>..<b> <file-1> <file-2> ...` — one or more spec-cited files changed since the spec was stamped. Tell the user the spec's cited files changed since it was stamped, listing the changed files from the `<file-...>` tokens. If the `drift` token carries no `<file-...>` tokens (only the two SHAs), do not claim specific files changed — tell the user the spec has drifted from its stamp but the cited-file list could not be computed (the spec file may have moved). Then ask via `AskUserQuestion` `"Spec-cited files changed since the spec was written — proceed with planning?"` — single-line text — with options `["proceed", "cancel"]`. On `cancel`, tell the user `"Re-check the spec against the changed files before re-running /devforge:plan."` and end the turn. On `proceed`, continue to Phase 0a.7 with the resolved path.
- `not-a-git-repo` (exit 2) — the drift check cannot run (no git repository / no HEAD / git binary missing). Tell the user `"Spec drift check unavailable (not a git repository); proceeding without it."` and proceed to Phase 0a.7 with the resolved path. The drift check is advisory — a non-git target must NOT block planning.

## PHASE 0a.7: Re-entry from a downstream re-entry seed (conditional — skip if no seed)

Before beginning the plan work, check for a downstream re-entry seed:

```bash
.devforge/lib/artifact_helper find-feature-artifacts --filenames '["*-seed.json"]'
```

`--filenames` carries a pattern here rather than a fixed name — an entry containing `*`, `?`, or `[` is matched against each feature directory's own file listing — so a seed from any producer is found without this block naming the producers one by one. That search is project-wide: the call walks every feature directory the install has. Keep it that way — the `/devforge:specify` consumer deliberately scopes its own lookup to the resolved feature dir so another feature's stale seed cannot bind the run, and this block's project-wide shape — inherited from the single-producer form it was first written in — is a recorded divergence from that scoping (plan 83), not an oversight to repair here.

Stdout is a JSON object; take `matches` from it — one entry per seed file found, each carrying `file` (the seed's own path, ready to read) and `feature_dir` (the feature directory that holds it). Finding nothing is the normal outcome, not a failure: the call exits 0 with an empty `matches` array, so there is no exit code to test for it — branch on `matches` being empty and take the no-seed arm at the end of this block. A non-zero exit means the call itself failed (a malformed `--filenames` value, or a workspace that could not be resolved), never that no seed exists: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

Read the JSON at each entry's `file`. If one of them has a `target_stage` equal to `"plan"` (this command's stage), you are re-entering from the verdict the seed's `source` names: a downstream command proved correctable defects in this feature's `plan.md`, and this re-run must address the confirmed findings rather than re-derive the flawed plan. Read the seed DIRECTLY: parse the matched file's flat JSON inline — do NOT call any producing command's helper verb, and do not add a `plan_helper` verb to read it either. What is banned is the producer, not helpers in general: `artifact_helper` is shared infrastructure this command already calls to commit its own artifacts, and the verb above matches filenames across feature directories without ever opening a seed or knowing what one means. Locating the file through it and interpreting the file here leaves nothing from any producing command in this block's path, so it remains valid even if one is later removed. The seed carries these fields:

- `source` — which command emitted this seed; read it first and name it in the re-entry message below.
- `feature` — the feature this directive applies to; state it up front (do NOT infer it from the file path).
- `prior_conclusion` — the flawed plan decision the `source` command invalidated; do NOT repeat it in the revised plan.
- `invalidating_evidence` — how that command proved the plan decision wrong (grounded in `plan.md` / `spec.md` / code).
- `must_satisfy` — what the revised plan must now satisfy; address it explicitly in the revised `plan.md`.
- `carried_findings` — the remaining confirmed findings to address; stay monotonic (never re-introduce a defect a prior pass fixed).

State up front in your first user-facing message that you are running in re-entry mode — naming the seed's `source` command, read from the field — for the named `feature`, and how this run addresses each `must_satisfy` item. The planning phases below run normally with this directive constraining what they produce — Phase 2 writes `plan.md` to the same path (overwriting the prior draft), so the result REPLACES rather than hand-patches the existing plan; the seed's directive ensures the replacement addresses the confirmed findings rather than re-deriving the flawed decisions. Proceed to Phase 0a.8 with the resolved path.

This block only READS the seed's directive. It does NOT delete the seed or change its `cycle_count` (that lifecycle is the emitting command's responsibility, not this consumer's — v1 simplification; do not add seed-deletion logic here).

When `matches` comes back empty, and equally when it carries entries but none of them has `target_stage == "plan"`, this block is a no-op — proceed normally to Phase 0a.8 with the resolved path (the normal case — a producing command writes a seed only when the user picks, at that command's own human gate, the arm matching its recommended re-entry disposition, and most runs never reach one). The `*-seed.json` pattern accepts a seed from any `source`; only a seed targeting `plan` matches here, and `/devforge:grill`'s REVISE-PLAN arm is the only one that emits that target today, so a seed from any other source falls through this block untouched.

## PHASE 0a.8: Spec-check gate (mandatory)

`/devforge:plan` requires a fresh `/devforge:spec-check` report for the resolved spec. This phase is a gate only — it blocks the run when that report is absent or stale, and does nothing else. There is no user gate here; do not invoke `AskUserQuestion`.

Check the report via the helper:

```bash
.devforge/lib/plan_helper verify-spec-check --spec <resolved-path>
```

The verb is read-only — it never flips a `**Status**:` line and never writes a file. It re-hashes the current `spec.md` (sha256 over the file's raw bytes) and compares that hash against the `**Spec hash**:` line recorded in the sibling `spec-check.md`. Handle the exit code:

- Exit 0 → a `spec-check.md` sits next to the spec and its recorded hash matches the current `spec.md`. Stdout is a JSON ack carrying `fresh`, `report_path`, and `spec_sha256`; surface the `report_path` value to the user in one line, e.g. `"Spec-check report is fresh: <report_path>."` Then proceed to Phase 0b with the resolved path.
- Exit 2 → BLOCKED. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The stderr is already the complete user-facing message: on the three report-state causes — no `spec-check.md` next to the spec, a report carrying no valid `**Spec hash**:` line, a report whose recorded hash no longer matches the spec — it names the cause, states that this gate is mandatory with no override, carries the `/devforge:spec-check <spec-path>` line to run next, and appends the one-time `pip install z3-solver` message when that package is not importable. The fourth cause is the resolved `spec.md` itself being unreadable, which prints the plain `plan_helper: cannot read spec: <path>` line and names no next command (running `/devforge:spec-check` would not repair a bad spec path). Add nothing to either shape and drop nothing from it.

`/devforge:spec-check` is user-invoked: name it, never run it yourself. On the BLOCKED path this run is over — the user runs `/devforge:spec-check`, then re-invokes `/devforge:plan`, which restarts at Phase 0a.

This gate reads PRESENCE and FRESHNESS only — never the report's verdict. A report recommending REVISE-SPEC satisfies it exactly as a CONSISTENT one does, because the human owns the disposition. Do not add a verdict condition, an override flag, or a skip arm to this phase: the helper offers none of them, and a future session must not "strengthen" the gate into one that reads the verdict.

This phase runs BEFORE Phase 0b's Draft → Approved flip by design — a spec that cannot be planned must not be flipped to Approved.

## PHASE 0b: Status flip

The act of running `/devforge:plan` constitutes approval of the spec for planning. Flip Draft → Approved structurally via the helper:

```bash
.devforge/lib/plan_helper check-status-and-flip <resolved-path>
```

Stdout is one of five state tokens:

- `flipped` — spec was Draft, now Approved. Tell the user: `"Spec status: Draft → Approved (implicit approval via /devforge:plan invocation)."`
- `already-approved` — continue silently; no message needed.
- `complete` — spec is in the post-`/devforge:verify` Complete state. Warn the user, then `AskUserQuestion` `"Spec status is Complete — proceed against a shipped spec?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.
- `inserted` — spec lacked a Status line; helper inserted `**Status**: Approved`. Tell the user: `"Spec was missing a Status line; helper inserted **Status**: Approved."`
- `unknown-status:<value>` — spec has a non-standard status. Tell the user the value, then `AskUserQuestion` `"Status is non-standard — proceed?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.

Exit 2 means the spec is malformed (neither Date nor Status frontmatter line). Echo the helper's stderr verbatim as a fenced block and end the turn.

## PHASE 0: Research Evaluation

**Guard**: Read `constitution.md`. If it contains `_Run /devforge:constitute to populate_` (or the legacy un-namespaced `_Run /constitute to populate_`, which an older install may still carry), stop: "⛔ constitution.md has not been populated yet. Run `/devforge:constitute` before using `/devforge:plan`."

**This phase always runs.** Scan the spec to determine the research depth needed.

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path.

**Memory check.** Read the project's persistent cross-session lessons file before the codebase research below and before any design decision is drafted:

```bash
.devforge/lib/plan_helper read-memory
```

The verb takes no arguments and always exits 0. It writes a JSON object to stdout carrying `memory_state`, `memory_excerpt` (the populated `## ` sections of `.devforge/memory.md`, `## Task Outcomes` excluded), and `memory_present`. Capture that stdout and branch on `memory_state`:

- `absent` or `stub` → no-op. Say nothing to the user about memory, raise no warning, add no step. A memory file that is missing, or still the stub the installer ships, records no lessons yet; on a new project that is the correct state, not a fault to remedy.
- `populated` → read `memory_excerpt` and pick out the entries bearing on this feature's technical area. Carry them into Step 1's codebase research (an entry can name a file or a pattern worth reading), Step 2's signal scan, and — the reason for reading them at this phase rather than later — the Phase 1.3 architect brief, where the Key Design Decisions are actually made. Include the bearing entries in that brief inline: they are helper stdout, not one of the files the brief's path list carries, so nothing else in the brief conveys them. An entry that surfaces after Phase 1.3 has settled a decision is too late to change it. When `memory_excerpt` comes back empty even though `memory_state` is `populated` — every populated line sits in the excluded `## Task Outcomes` section — take the `absent` / `stub` no-op branch above instead: carry nothing into Step 1, Step 2, or the Phase 1.3 architect brief, and say nothing to the user about memory.

`memory_excerpt` is not the whole file: it renders the file's populated `## ` sections — a section with no entries under its heading is dropped heading and all, `## Task Outcomes` is excluded outright, and any other section is kept — and when the line budget cannot fit a section whole, the lines it drops are always that section's EARLIEST ones, with an inline marker line right after the heading naming how many were omitted. An entry's absence from a non-empty excerpt therefore means it sits in the excluded section or behind a marker the excerpt itself declares, never "never recorded"; an empty excerpt means there are no readable lessons — the file is absent or still the shipped stub, or everything in it sits in the excluded section.

**Honesty bound.** A carried memory entry is an UNVERIFIED prior-session assertion, not evidence for this plan: it is a constraint to respect and a candidate to check against the code, never a finding and never grounds for a design decision on its own. A past session wrote it, and the code it describes may have changed since — or the entry may have been wrong when it was written. It licenses nothing here: a Key Design Decision's `Why` column rests on the spec, the constitution, or the code read in Step 1, never on the memory entry alone.

### Step 1: Codebase Research (always)

- Read relevant source files to understand current patterns.
- Check how similar features are implemented.
- Identify reusable code and patterns.
- For greenfield projects: check the constitution's scaffolding guide for pattern references.
- The spec already incorporates relevant documentation context from `docs/`. Do not re-read docs — use the spec's "Current State" and "Affected Areas" sections as your primary source.

After the codebase read, do one design-intent read (separate from the code-pattern research above): if a `design-anchor.json` sibling of the resolved `spec.md` exists (i.e. `<feature_dir>/design-anchor.json`, the design INTENT `/devforge:specify` persisted for a UI feature), read it — a passive, read-only sibling read. Parse the flat JSON directly; do NOT call any helper verb (the anchor is read in place). It carries `{kind, file, selectors}`: the design-source `kind` (e.g. `html`), the source `file`, and the `selectors` that carry the intent. Note the `kind` and the intent-bearing `selectors` so the UI technical approach (Phase 1) is shaped to match the captured intent instead of re-guessing it. `/devforge:plan` does NOT author the built-side binding (the render `route` + selector pairs) — that is `/devforge:breakdown`'s job — and does NOT re-serialize the anchor into `plan-handoff.json`. Absent → silent no-op (a non-UI feature, or one whose intake captured no anchor).

### Step 2: Signal Scan

Read the spec and check for these signals. **Only flag signals for things NOT already in the project's current stack.** If the spec references a library/technology that's already in the project's dependencies (check `CLAUDE.md`, `package.json`, `pubspec.yaml`, `requirements.txt`, etc.), that is NOT a signal — the team has already made that choice.

| Signal | Example | NOT a signal when... |
|--------|---------|---------------------|
| External library/package **not in project dependencies** | "use Stripe SDK" (and Stripe is not in package.json) | Library is already installed |
| New integration with **unconfigured** third-party service | "connect to payment gateway" (no payment config exists) | Service is already integrated |
| Architectural decision where multiple valid approaches exist | "real-time updates" (polling vs SSE vs WebSocket) | Always a signal — requires decision |
| Greenfield pattern not yet present in the codebase | first use of caching, first background job | Pattern already exists in codebase |
| Performance constraints that need benchmarking | "handle 10k concurrent users", "< 200ms response" | Always a signal — requires research |
| Technology **not part of the project's current stack** | new protocol or tool the codebase hasn't used | Technology is already in the stack |

**No signals found** → proceed to Phase 1 with codebase research only.

**1+ signals found** → continue to Step 3.

### Step 3: Deep Research (when signals detected)

For each signal, choose the appropriate research tool:

**For specific libraries named in the spec** (binding):
- **Required**: Use Context7 first (`resolve-library-id` → `query-docs`) to get current documentation. **Do not skip directly to WebSearch.**
- **Fallback condition**: Only fall back to WebSearch if (a) Context7 returns no results for the library, OR (b) the Context7 tool is unavailable in this session. Document the fallback in research.md with the specific reason ("Context7 returned no docs for X" or "Context7 unavailable").
- **Auditability**: The choice is logged in tool-call traces; reviewers can verify which path was taken.

**For comparing alternatives or architectural decisions:**
- Use WebSearch to find current best practices and proven approaches.
- Compare at least 2-3 alternatives with pros/cons.
- Check library options: maintenance status, bundle size, community adoption.

**Seed from upstream plan-seeds (do not relitigate settled alternatives):** If Phase 0a.5 surfaced an `## Upstream plan-seeds` block that already lists alternatives (a research handoff under "Alternatives considered"; a discover handoff under "Design options"), seed the alternatives comparison from those rather than rediscovering them. The 2+-alternatives architect invocation described in this Step 3 fires only for alternatives NOT already settled in the upstream plan-seeds. The Phase 1.3 mandatory architect consultation is unaffected — it fires unconditionally regardless of plan-seeds. When you seed from plan-seeds and therefore skip fresh alternative discovery, record that in the plan's "Specialist Consultation" section, citing the upstream handoff. Do not contradict the upstream recommendation silently — a divergence must be stated with reasoning (this complements the divergence rule in Phase 0a.5).

**Architect consultation: mandatory when 2+ architectural alternatives are being compared.**

After raw findings for each alternative are gathered (pros/cons/maintenance/bundle), invoke the `architect` agent via the Task tool to author the verdict. Brief shape: pass file paths to `<feature_dir>/spec.md`, in-progress research notes, and `CLAUDE.md`; ask which alternative wins for the named decision area and why; expect the architect to return rows verbatim-ready for the research.md "Alternatives Compared" table (verdict column populated per row) plus a one-line decision rationale.

Skip ONLY when alternatives are mechanical (one library is project-default per `CLAUDE.md`, others are non-starters). The skip reason must be recorded as a one-line note in the plan.md "Specialist Consultation" section (see Phase 2 template) — that section is always present in plan.md and is the single source of truth for invocation/skip provenance, regardless of whether research.md was generated. Silent skips are a hard error.

**For all signals:**
- Look at real-world examples of similar implementations.
- Verify external API contracts and limitations.

### Research Output Rule

When 1+ signals are detected, document research findings somewhere visible to the plan reviewer. Two valid paths:

- **Default**: Generate `<feature_dir>/research.md` with the structured template below.
- **Skip-with-reference**: If this feature's own intake report — `<feature_dir>/research-report.md` (written by `/devforge:research`) or `<feature_dir>/discovery-report.md` (written by `/devforge:discover`) — directly addresses ALL detected signals (verified by reading that report), you may reference it instead of generating a new file. Intake writes its report into the feature's own directory, so that directory is the only place to look for it. In this case:
  1. Cite the report's path in the plan's Supporting Documents section
  2. Add a brief "Why no new research" note in the plan's Summary section
  3. Quote 2-3 specific findings from that report in the plan body to prove the reference was actually consulted
  4. Do NOT skip without reference — that is a hard error

If signals are detected and neither path is taken, the plan is incomplete.

### Research output:

Save to `<feature_dir>/research.md`:

```markdown
# Research: [Feature Name]

**Date**: [YYYY-MM-DD]
**Signals detected**: [list which signals triggered deep research]

## Questions Investigated
1. [Question] → [Finding + decision]
2. [Question] → [Finding + decision]

## Alternatives Compared

### [Decision Area] (e.g., "Payment processor", "WebSocket library")
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| [option A] | [pros] | [cons] | Chosen / Rejected |
| [option B] | [pros] | [cons] | Chosen / Rejected |
| [option C] | [pros] | [cons] | Chosen / Rejected |

**Decision**: [chosen option] — [one-line rationale]

## References
- [links to docs, examples, or source files consulted]
```

If no deep research was needed (no signals), skip the research.md file.

## PHASE 1.5: Findings from Spec (REQUIRED INTERMEDIATE OUTPUT)

Before writing any of the plan's tables (Layer Map, File Impact, Key Design Decisions, Risk Assessment), produce a structured intermediate output enumerating what the spec contains. This is a hard requirement.

Render the skeleton via the helper:

```bash
.devforge/lib/plan_helper render-findings-from-spec <resolved-path>
```

The helper enumerates every §3 / §4 / §5 / §6 / §7 / §8 / §9 item with an identifying snippet plus a per-section fill marker. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). In the SAME message, replace each marker inline with your coverage decision:

- `[PLAN COVERAGE: ?]` on §3 / §4 / §5 lines → `[PLAN COVERAGE: <layer/file/decision>]` or `[PLAN COVERAGE: covered by Layer Map: <area>]`. A §5 line that is a BEHAVIORAL AC — one asserting what a path emits, returns, or does at runtime — takes the `<decision>` form, naming the Key Design Decision whose behavior change satisfies it; a Layer Map marker does not cover it (PHASE 2.5 step 2 states the standard).
- `[must not contradict]` on §6 lines → leave as-is, OR append ` → confirmed: <why>` if the plan touches a related area.
- `[LANDS IN: ?]` on §7 lines → `[LANDS IN: Constitution Compliance]` or `[LANDS IN: Risk Assessment]`.
- `[RESOLUTION: ?]` on §8 lines → `[RESOLUTION: <decision>]` if resolved by the plan, or `[RESOLUTION: carry-forward to /devforge:breakdown]`.
- `[MITIGATION CARRIED: ?]` on §9 lines → `[MITIGATION CARRIED: yes — Risk Assessment row <N>]` or `[MITIGATION CARRIED: no — out-of-scope per §6]`.

When a planning decision actually resolves a §8 open question — here at Phase 1.5, or later when a Phase 1 / Phase 2 decision settles one — record the resolution in specify-state via the helper, passing the spec's question id and `--resolution-phase plan`:

```bash
.devforge/lib/specify_helper resolve-open-question --question-id <question-id> --resolution-text "<how the plan resolves it>" --resolution-phase plan
```

This appends a resolution audit entry to specify-state; the spec re-render strikes through the resolved entry. It is conditional — run it only when the plan actually resolves an open question. Unresolved questions stay open for `/devforge:breakdown` (`[RESOLUTION: carry-forward to /devforge:breakdown]`) or carry into the plan's Risk Assessment.

**Each section requires concise bullet enumeration** — reference, don't restate. Goal is a ~15–30-line output that proves every spec section was read and accounted for.

This intermediate output forces every spec section to be acknowledged before plan tables are written. Same purpose as /devforge:specify Phase 1.5: convert implicit recall into explicit enumeration. Skipping or compressing this step is a hard error.

After this intermediate output is complete, proceed to Phase 1 (Technical Design). The "1.5" numbering is deliberate — the section runs after Phase 0 and before Phase 1 despite the numeric ordering, because it gates both the Phase 1 technical artefacts (data model, contracts, architecture decisions — per the Prerequisite at the top of Phase 1) and the Phase 2 plan tables (Layer Map, File Impact, Key Design Decisions, Risk Assessment — per the preamble above).

## PHASE 1: Technical Design

**Prerequisite**: Phase 1.5 must be complete before any technical-design artefacts (data model, contracts, architecture decisions) are drafted.

### 1.1: Data Model (if applicable)

If the feature involves data entities, define them. Save to `<feature_dir>/data-model.md`:

```markdown
# Data Model: [Feature Name]

## Entities

### [EntityName]
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier |
| ... | ... | ... | ... |

### Relationships
- [Entity A] → [Entity B]: [relationship type and description]

### Validation Rules
- [Field]: [constraint]
```

For existing codebases, reference existing types/interfaces instead of redefining them. Only document NEW or CHANGED entities.

### 1.2: API Contracts (if applicable)

If the feature involves API calls (REST, GraphQL, etc.), define contracts. Save to `<feature_dir>/contracts.md`:

```markdown
# API Contracts: [Feature Name]

## [Endpoint/Query/Mutation Name]
- **Type**: [GET/POST/Query/Mutation]
- **Input**: [type definition or reference to existing type]
- **Output**: [type definition or reference to existing type]
- **Errors**: [error cases and response format]
```

For existing codebases, reference existing GraphQL queries/mutations or REST endpoints. Only document NEW or CHANGED contracts.

### 1.3: Architecture Decisions

Document HOW the feature maps to the project's architecture. This is the core of the plan.

**Architect consultation: mandatory.**

Before drafting the Phase 2 plan.md tables (Layer Map, Key Design Decisions, File Impact, Risk Assessment), invoke the `architect` agent via the Task tool. The architect's `think`-tier reasoning is the specialization point for layer-mapping, dependency-direction, package-boundary, and constitution-compliance calls. Orchestrator-direct authoring of these tables without consultation is a hard error at this phase.

**Orchestrator-mediated consultation relay (the architect emits requests; it does NOT invoke anyone):** subagents cannot spawn subagents, so the architect cannot consult a specialist itself. Instead the architect returns zero-or-more **consultation requests** alongside its table rows, and the orchestrator (the LLM running this spec) performs the invocations. Run the loop:

1. Invoke the `architect` agent (mandatory, per above). It returns the table rows (Layer Map / Key Design Decisions / File Impact / Risk seeds / Constitution flags) AND zero-or-more consultation requests, each carrying a named specialist + a sub-question + context.
2. For each consultation request: invoke the named specialist via the Task tool with the architect's sub-question + context, capture the specialist's response, then **re-invoke the `architect`** with the relayed response so the architect can synthesize it into its decision. The architect never invokes the specialist — the orchestrator relays both directions.
3. The orchestrator MAY also consult a specialist directly when this spec calls for it, not only on the architect's request.

Any planning-relevant specialist may be named: `architect`, `frontend-engineer`, `backend-engineer`, `security-reviewer`, `db-engineer`, `migration-engineer`, `api-designer`, `performance-analyst`, `design-auditor`, `mobile-engineer`, `devops-engineer`, `qa-engineer`.

**Brief shape (pass file paths, NOT inlined content):**

- `<feature_dir>/spec.md`
- `<feature_dir>/research.md` (if exists)
- `<feature_dir>/data-model.md` (if drafted at 1.1)
- `<feature_dir>/contracts.md` (if drafted at 1.2)
- `<feature_dir>/emission-matrix.md` (if exists — written by `/devforge:research`)
- `CLAUDE.md` (architect reads `## Architecture` + `## Packages` directly)
- `constitution.md`

`<feature_dir>/research.md` is THIS command's own deep-research file, written by the Research Output Rule in Phase 0 above — it is NOT an artifact `/devforge:research` wrote, and that command writes `research-report.md` and `emission-matrix.md` into the same directory, so pass the path you actually mean and do not conflate the three.

The architect inherits the parent session's Read tool surface and will fetch these itself. Do not summarize their content in the brief — that double-pays context and risks drift.

**Sub-questions (always asked):**

1. Which architectural layers does this feature touch? Return as Layer Map table rows (`layer | what | files`).
2. Are there architectural decisions with multiple valid approaches not resolved by Phase 0 research? Return as Key Design Decisions table rows (`decision | chosen | why | rejected`).
3. Any dependency-direction or package-boundary risks? Return as Risk seeds (likelihood / impact / mitigation hint).
4. Any constitution rules at risk under this approach? Return as one-line flags for the Constitution Compliance section.
5. What is the MINIMAL change that satisfies the in-scope ACs? Return as a one-line statement of the smallest design that meets the §5 acceptance criteria — the baseline the Key Design Decisions must not exceed without justification. When that minimal change is awkward because the existing structure resists it — the AC-satisfying edit would have to be duplicated across call sites, threaded through a signature that cannot carry it, or wedged into a function that already does two jobs — you MAY record a **preparatory restructuring** ahead of it: a Key Design Decisions row like any other, sequenced BEFORE the AC-satisfying decisions, whose chosen approach re-shapes the existing structure WITHOUT changing observable behavior so that the AC-satisfying change becomes the easy one, carried by its own rows in the plan's `### File Impact` table. That recorded decision is itself the justification for exceeding the minimal baseline — stated in the plan rather than left implicit. This lane is permissive and never obligatory: a plan whose ACs are satisfiable against the structure as it stands records none, and nothing here asks why you did not restructure. When you do record one, it carries its own preservation contract in that decision's `Why` column — the postcondition that each restructured surface's observable result is unchanged, in the terms the constitution's Two-hats rule (Design Principles section) sets — and it stays behavior-preserving end to end: an AC-satisfying behavior change folded into it is what turns a preparation into a defect. What this phase records is a DECISION and its file impact, never a task — `/devforge:breakdown` is what decomposes that decision into a task, sequenced ahead of the tasks that depend on it. A purely preparatory decision changes no observable behavior, so it fails the second of the two conditions that make work mixed: the Two-hats partition, and the `code-reviewer` check that reads it, do NOT apply to it at all — the only thing in this plan asserting that it preserves behavior is the preservation contract it states, and nothing else here is watching. Downstream is where that changes. `/devforge:breakdown` decomposes this decision into a restructure-only task, and that command's Regression-net declaration rule attaches to such a task: a behavior-preserving surface no test covers must declare its regression net in that task.
6. For each Key Design Decision, is the concern it addresses in scope per the spec's §6 Out of Scope? Return one line per decision, in one of two conditional forms — in-scope: `decision → in-scope: <AC/constraint cited>` (the OOS half is omitted); OOS-reaching: `decision → OOS: <§6 entry> → escalate` (the in-scope half is omitted). A decision whose concern §6 excludes must NOT be silently solved — the architect escalates it to the user per its Rule 6 (termination), triggered by its Rule 9 OOS-respect check, and the orchestrator surfaces the escalation to the user rather than transcribing the decision.
7. Does any Key Design Decision RESTRICT existing behavior of shared code (a shared service, utility, or layer with multiple callers)? Per the constitution's Narrowing rule (Design Principles section), return one line per such decision: is the restriction caller-scoped (an opt-in the affected caller passes) or layer-wide? For a caller-scoped one, name every caller classified in-scope in the carried caller enumeration (or re-derived per the trigger below; or, when no `**Caller enumeration**` section was carried at all, established by the architect tracing the callers directly) as the callers that receive the opt-in wiring, and confirm no in-scope caller is left unwired — a caller-scoped restriction whose needing-caller set is unnamed is not recordable. Return the FULL trace result on that line, not only the wiring set: every caller the carried enumeration or the trace produced, each carrying its in-scope / out-of-scope classification. A caller leaves that answer by being classified out-of-scope, never by being omitted — the out-of-scope half is where a missed coupling hides, and dropping it spends the trace and then discards most of what it returned. Both halves land in that decision's `Why` column: the in-scope callers as the set that receives the opt-in wiring, the out-of-scope ones named beside them as considered-and-not-wired. For a layer-wide one, return the list of every current caller it affects (for the decision's row) and the reason a caller-scoped opt-in genuinely can't cover it. When the needing-caller set can't be established by any of those paths, a layer-wide key on data every caller already passes is the failure-tolerant fallback (per the constitution's Narrowing rule) — record that instead. A decision that restricts no shared code returns nothing here.
8. Which of the feature's planned functions/modules (from the Layer Map / File Impact under design) are PURE BUILDERS — deterministic, no I/O, no external service or repository access: filter/query/mapper/formatter construction logic? Return one table row per target, verbatim-ready for the plan's `### Pure-Builder Targets` subsection: `target (function/module name) | file | why pure` (the "why pure" cell states the properties that make it property-testable — deterministic, no I/O). Only NAMED targets enter the property-test lane downstream — there is no inference; a feature with no pure builders returns nothing here and the subsection is omitted.
9. Does any Key Design Decision render existing code UNREACHABLE — an arm, function, param, import, or branch no live path can reach after the change lands (a decision that adds a dominating condition, removes a call, or narrows an input domain is the usual cause)? For each Key Design Decision, trace the code the decision touches (`trace_path` / `search_code` on the ACTUAL code, NOT from memory) and return one table row per killed path, verbatim-ready for the plan's `### Change-Induced Dead Code` subsection: `file | anchor token | kind | why dead`, where the **anchor token** is a literal string lifted from the code whose ABSENCE in the post-change file proves the path was removed (e.g. `: 'legacyRegionCode'`) and which must NOT contain a semicolon — `;` is the downstream task-field delimiter and the schema rejects it; pick a shorter or different distinguishing literal from the same path instead — and **kind** is one of `arm | function | param | import | branch`. An anchor token is lifted from the code and from nowhere else — never from a cell of this feature's `emission-matrix.md` or any other carried table — because `/devforge:verify` matches each declared token literally against the post-change file, and a token that never came from the code cannot survive that match. Also classify each decision `simplifies` / `extends` / `neutral`; when it `simplifies`, list the follow-on cleanups it ENABLES as one-line items tagged for the `### Follow-On Cleanups (advisory)` section (a now-trivial ternary to collapse, a now-single-use option to drop). Empty answers are EXPLICIT — a decision that kills nothing returns the literal `renders nothing unreachable`, and silence is not an answer. Removing a declared-dead path is PART of the change, not scope creep: the constitution's §3.5 (No dead code) makes deletion in-scope by rule, so each row here obligates the owning task to delete that path — /devforge:verify confirms each declared row's removal (plan 71 Phase 4).
10. Does any Key Design Decision rest on the VALUE of a hardcoded literal — a decision whose rationale cites what a constant, flag, or default currently IS as grounds for keeping, deleting, or scoping code? Return one line per such decision, naming the literal and — when the carried `**Literal provenance**` section records a row for it — that row's intent classification; a literal the section does not name has no carried intent, so say that on the line and do not infer one. When that intent is `deliberate`, the line MUST also carry the introducing commit SHA — the carried row already supplies it, so this is a copy rather than fresh research, and it makes the decision name the commit that made the value deliberate instead of gesturing at intent. When the recorded intent is `placeholder`, `forgotten`, or `inherited-refactor`, the literal's current value is NOT evidence of design intent: say so on the line and rest the decision's `Why` on something else — the carried caller enumeration, an acceptance criterion, or the code path itself. `migrated` and `generated` carry no evidence verdict either way; the row is context for the decision, not license for it. Weigh the row's `supply-changing commits:` sub-bullet alongside its intent, because the two can disagree: where the sub-bullet lists commits, name the most recent one on the line — a commit that changed how the value is supplied after it was introduced can strand the value, and where such a commit exists it is that later commit, not the introduction, that says what the value means now. This is the case the intent classification alone misreads: a considered introduction is exactly what a stranded value looks like, so `deliberate` plus a listed supply-changing commit is not evidence the value is still intended, and the line rests on the later commit rather than on the intent. Where the sub-bullet reads `no supply-changing commits since the introducing commit`, the intent classification stands on its own. Where it reads `not swept`, the value's supply history was not examined at all — say that on the line, and do not read it as the absence of such a commit. Each line lands in that decision's `Why` column in the Key Design Decisions table; there is no separate plan subsection for literal provenance. A decision that rests on no literal's value returns nothing here.
11. Does this feature have an emission matrix — `<feature_dir>/emission-matrix.md`, written by `/devforge:research` when its recommended approach removed or suppressed a value the changed code emits? When the file is absent, return nothing here. When it exists, read it and return two things. **Currency**: its rows were traced at the `/devforge:research` run, so a call site added since is simply absent from it — confirm the rows against sub-question 7's already-mandated fresh inbound `trace_path`, and do NOT run a second trace for this question. Name every call site that fresh trace shows and the matrix does not, and account for each exactly as for an `affected` row, because a caller added between the `/devforge:research` run and this one would otherwise go unnamed. When no Key Design Decision restricts shared code, sub-question 7 ran no fresh trace and there is nothing to confirm against: say so on the line — the matrix's currency was not checked — and do not invent a trace here to fill the hole. **Accounting**: return one line per row whose `Verdict` is `affected`, either naming the Key Design Decision that covers that row's `Call site` or stating in one sentence why that call site needs no covering. An `affected` row that is neither covered nor answered is not recordable — the decision it bears on cannot be written until the row is accounted for. A row whose `Intersection with the removed set` cell reads `varies` is an `affected` row (the matrix defaults that cell's verdict to `affected`) and is accounted for like any other. Each line lands in the relevant decision's `Why` column in the Key Design Decisions table; the matrix is read where it sits and is NEVER copied into `plan.md`, so no plan subsection carries it and it cannot drift from its source. The matrix's verdicts are `affected` and `unaffected` and nothing else — it makes no claim about whether any path is reachable after the change, so it neither answers nor pre-empts sub-question 9: a path declared unreachable there still comes from sub-question 9's own fresh trace of the code.
12. Which acceptance criteria describe a USER-VISIBLE FLOW that only a full-stack run can verify — a criterion satisfied by a sequence of user-facing steps across the running system, rather than by a value a unit or integration test can assert on its own? For each one, name the MINIMAL scenario that exercises it: the shortest ordered sequence of user-visible steps whose completion is what the criterion asserts, plus whatever state must already exist before the first step. Answer from the acceptance criteria themselves — whether the project has any e2e tooling today does not change which criteria need a full-stack run, so do not read the absence of tooling as the absence of such a criterion. Return one table row per scenario, verbatim-ready for the plan's `### E2E Scenarios` subsection: `scenario | acceptance criteria | flow steps | preconditions` (the "flow steps" cell carries the ordered steps on one line; the "preconditions" cell names the state the run needs before its first step, or `none`). Only NAMED scenarios reach decomposition downstream — there is no inference, and a criterion no row names is one nothing schedules a full-stack test for. Empty answers are EXPLICIT — a feature whose every acceptance criterion is verifiable without a full-stack run returns the literal `no full-stack-only flows`, and silence is not an answer; that literal is not a row, so the subsection is omitted.

**Use the carried caller enumeration (do not re-derive it):** If Phase 0a.5's `## Upstream plan-seeds` block carried a `**Caller enumeration**` section — one line per touched helper (`<helper-qn> (<file:line>)`) with each inbound caller nested beneath it, a classified caller reading `caller: <caller-qn> (<file:line>) — surface: <s>, scope: <in|out> — <justification>` (the `surface` and `scope: in|out` are the caller's in/out-of-scope classification recorded at `/devforge:research`; an unclassified caller carries no suffix, reading just `caller: <caller-qn> (<file:line>)`), recorded at `/devforge:research` — include that section in the architect brief (it is helper stdout, not a file the architect can fetch itself) and tell the architect to use it as sub-question 7's caller-naming source instead of re-deriving callers through fresh `trace_path` calls, reading each caller's `scope` suffix directly: the `scope: in` callers are the set a caller-scoped opt-in must wire, and each such caller's `surface` names its entry point. The carried list reflects the codebase as of the `/devforge:research` run, so re-derive callers ONLY for helpers the plan touches that the section does not name, or whose nested entry reads `(no inbound callers recorded)`. Add one more re-derivation trigger for the Narrowing rule's own subject: for any carried helper that a Key Design Decision actually RESTRICTS, run ONE fresh `trace_path(<helper_qn>, mode=calls, direction=inbound)` on that helper to confirm the carried callers are still current before the decision's Why column cites them — the carried list is the seed and the cross-check baseline here, not the terminal answer, because a caller added between the `/devforge:research` run and this one would otherwise go unnamed. Helpers the plan touches but does not restrict may rely on the carried list as-is. If the section instead carried the single-line form `recorded at /devforge:research — zero shared callers asserted: <justification>`, treat that as an UNVERIFIED research-time assertion — it licenses nothing at `/devforge:plan`, and sub-question 7 is answered by what the architect confirms, not by the justification text.

**Use the carried literal provenance (do not re-derive it):** If Phase 0a.5's `## Upstream plan-seeds` block carried a `**Literal provenance**` section — one line per literal carrying its identity (the literal itself, backtick-quoted, plus its `<file:line>`) and its `intent:`, `use:`, `SHA:`, `when:`, and `subject:` fields, each line followed by a nested `supply-changing commits:` sub-bullet, recorded at `/devforge:research` — include that section in the architect brief (it is helper stdout, not a file the architect can fetch itself) and tell the architect to use it as sub-question 10's source for every literal it names. That sub-bullet carries one of three states and they are not interchangeable: `supply-changing commits: not swept` means the commits that changed how the value is supplied after it was introduced were never looked for on that literal; `supply-changing commits: no supply-changing commits since the introducing commit` means they were looked for and none exist; and a bare `supply-changing commits:` line followed by nested `<sha> — <subject>` entries means they were looked for and these are them. Do not re-run `git log` or `git blame` against those literals here: their history was established upstream, at the point the run actually examined the value, and re-deriving it at plan time both spends the work twice and produces a second answer nothing reconciles against the first. When no `**Literal provenance**` section was carried, treat that absence as an UNVERIFIED research-time negative — it licenses nothing at `/devforge:plan`. What it establishes is bounded: no finding recorded upstream reported resting on a literal. Those are self-reports, and the upstream gate can force the question to be answered, never the answer to be right. It establishes nothing at all about a conclusion carried outside a finding — one carried in a hypothesis, a runner-up framing, or a caller-scope justification is tied to no provenance row, so a literal reasoned from in one of those never reaches this block. A row whose sub-bullet reads `not swept` is that same UNVERIFIED negative narrowed to a single literal: it records that nobody looked, not that the value's supply is unchanged since it was introduced — so it licenses nothing here either. Read it as no evidence in either direction, never as an equivalent of `no supply-changing commits since the introducing commit`. If a decision drafted here rests on a literal the section does not name, record that reliance plainly in the decision's `Why` column so the rationale shows what it stands on — an uncited reliance is still recordable, and dating the literal is not this phase's work.

**Return shape:** architect MUST author table rows verbatim-ready for Phase 2 transcription (no orchestrator paraphrasing) and the architect's standard output already carries a `### Specialists Consulted` block (per its Output Format); the orchestrator transcribes those entries — plus any specialists it consulted directly — into the plan's **Specialist Consultation** table (one row each, with Verdict + Cites).

**Halt rule:** if you reach Phase 2 without having completed this consultation, halt, invoke the architect now, then write the Specialist Consultation section at the top of plan.md (per the Phase 2 template) before drafting any of the Phase 2 tables. Provenance recording is part of the contract — Phase 2 tables drafted without a corresponding Specialist Consultation entry are a hard error.

## PHASE 2: Write the Plan

Save to `<feature_dir>/plan.md`. The Layer Map below shows a Domain/Data/Presentation example consistent with Clean Architecture; the actual layer rows MUST match the project's architecture as declared in `CLAUDE.md` (the `## Architecture` section + the per-package `## Packages` table for multi-stack projects). For monorepos, the layer column may instead be per-package (e.g., `apps/web`, `services/api`) — follow whatever shape the project's `CLAUDE.md` establishes.

```markdown
# Plan: [Feature Name]

**Date**: [YYYY-MM-DD]
**Spec**: [path to spec.md]
**Status**: Draft
**Run by**: [include this line — and the italic bound note on the line directly under it — ONLY when the provenance rule below this template resolves a name; omit BOTH lines entirely when it does not]

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: [yes — see research.md §Alternatives Compared | no — N/A (no 2+ alternatives compared, OR alternatives were mechanical per CLAUDE.md project-defaults — one-line reason: ___)]
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): [see Specialist Consultation table]

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: [rows N-M]
- Key Design Decisions: [rows N-M]
- Risk Assessment seeds: [rows N-M]
- Constitution Compliance flags: [list | none]
- Pure-Builder Targets: [rows N-M | none]
- E2E Scenarios: [rows N-M | none]

[Specialist Consultation table — emit via `plan_helper render-consultation-block` per the instruction below this template, then fill rows]

## Summary

[2-3 sentences: what this plan implements and the technical approach]

## Technical Context

**Architecture**: [from constitution — which layers are involved]
**Error Handling**: [pattern to use]
**State Management**: [approach for this feature]

## Constitution Compliance

[Verify the planned approach doesn't violate any NON-NEGOTIABLE rules]
- Rule X: [compliant / requires attention]
- Rule Y: [compliant / requires attention]

## Implementation Approach

### Layer Map

[Which architectural layers this feature touches and what happens in each]

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Domain | [types, interfaces, use cases] | [file paths] |
| Data | [repositories, API calls] | [file paths] |
| Presentation | [components, views, state] | [file paths] |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| [decision] | [approach] | [rationale] | [alternatives] |

[A decision that restricts shared-code behavior must record the caller-scoped vs layer-wide choice per the constitution's Narrowing rule (Design Principles section); a caller-scoped restriction must name every in-scope caller that receives the opt-in wiring, and a layer-wide restriction must name every current caller it affects — either way in its Why column.]

[Rule 5: An alternative rejected as IMPOSSIBLE — the code can't do it, the value isn't available at that point, the signature won't carry it — must name the arguments the function in question actually receives, each with its reachable VALUE SET — the values callers can actually present, never an expression or a bare parameter name standing in for them — and show the impossibility claim against those values, since it is values, not expressions, that let a reader check whether two callers' tuples are the same rather than only find it plausible. A rejection the reader cannot check against the function's real inputs is not recordable: re-state it on checkable grounds, or drop the alternative from the column and reconsider it on its merits. When such a checkable rejection shows that two call sites can present the SAME REACHABLE tuple of argument values to the function in question — the values those callers can actually reach it with, not merely a shared signature — the default reading is that the two sites are one caller population, not two. An identical reachable tuple paired with opposite required outputs — one acceptance criterion demanding the behavior change at one site while another demands it stay at the other — is an acceptance-criteria conflict, not an implementation gap to bridge: surface it to the user as a product question naming both criteria and the shared tuple — the architect escalates it per its Rule 6 (termination), triggered by its Rule 9 rejected-alternative checkability step — rather than recording a discriminator parameter that forces the tuples apart. A discriminator is recordable only after the decision's Why column shows the two sites genuinely distinct — a difference in how each site is constructed, or in the argument values each can actually present — and an acceptance criterion asserting that one site must not change is not that showing: it is one side of the conflict. This constrains what the existing Alternatives Rejected and Why columns may contain, and sends the conflict it surfaces to the user instead of into either column; it adds no column and no table.]

### Established-Convention Departures

[Include this subsection ONLY if ≥1 Key Design Decision is flagged "DEPARTURE" in its Why column (per architect Rule 3). Omit the entire subsection — heading and table — when there are no departures (e.g. greenfield or first-touch concerns).]

| Departure | Established Pattern Left | Why Necessary |
|-----------|--------------------------|---------------|
| [new pattern chosen] | [what the codebase already does for this concern] | [why the established pattern genuinely doesn't work here] |

### Pure-Builder Targets

[Include this subsection ONLY if Phase 1.3's sub-question 8 returned ≥1 pure-builder target. Omit the entire subsection — heading and table — when none were returned (a feature with no deterministic, I/O-free construction logic).]

| Target | File | Why pure |
|--------|------|----------|
| [function/module name] | [file path] | [deterministic, no I/O — e.g. builds a filter/query from inputs] |

[Each row here becomes a mechanical property-test obligation at `/devforge:breakdown` — a dedicated property-test task must cover every listed target, and a decomposition gate at `/devforge:breakdown` fails otherwise. List only functions that are genuinely deterministic and I/O-free.]

### Change-Induced Dead Code

[Include this subsection ONLY if Phase 1.3's sub-question 9 returned ≥1 killed path. Omit the entire subsection — heading and table — when every decision renders nothing unreachable.]

| File | Anchor token | Kind | Why dead |
|------|--------------|------|----------|
| [file path] | [literal token whose absence proves removal — no semicolons] | [arm/function/param/import/branch] | [why this change kills the path] |

[Each row here is a MUST-delete obligation, not a suggestion: the path is dead by the constitution's §3.5 (No dead code), so its removal folds into the owning task that lands the killing change (never a separate deletion task) — /devforge:breakdown wires this folding rule (plan 71 Phase 3). /devforge:verify confirms each declared row's removal (plan 71 Phase 4).]

### Follow-On Cleanups (advisory)

[Include this subsection ONLY if Phase 1.3's sub-question 9 tagged ≥1 follow-on cleanup on a `simplifies` decision. Omit the entire subsection — heading and list — when none were tagged.]

- [one-line cleanup the change ENABLES — e.g. collapse a now-trivial ternary, delete a now-single-use option]

[These are RECOMMENDATIONS the user reads at the /devforge:plan approval gate, NOT obligations: unlike the MUST-delete rows above, a follow-on cleanup NEVER silently becomes a task. An accepted cleanup becomes its own spec/ticket. This lane is advisory by design — a future session must not "strengthen" it into a gate.]

### E2E Scenarios

[Include this subsection ONLY if Phase 1.3's sub-question 12 returned ≥1 scenario. Omit the entire subsection — heading and table — when none were returned (a feature whose every acceptance criterion is verifiable without a full-stack run).]

| Scenario | Acceptance criteria | Flow steps | Preconditions |
|----------|---------------------|------------|---------------|
| [short scenario name] | [which AC(s) this scenario verifies] | [the ordered user-visible steps, on one line — e.g. sign in → add item → submit → see confirmation] | [state that must exist before the first step, or `none`] |

[Each row here becomes a decomposition obligation at `/devforge:breakdown` — a dedicated test-authoring task covers the listed scenarios. NOTHING CHECKS that obligation: there is no decomposition gate for this table, no `verify-*` verb, and no task header field, so a plan declaring three scenarios beside a task set covering none produces no error. The claim is visibility, not enforcement — an uncovered scenario is visible in the task set, never blocked. Declare only flows that genuinely need the running system end to end; a criterion a unit or integration test can assert belongs in neither this table nor a full-stack run.]

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| [path] | Create/Modify | [brief description] |
| [path] | Create/Modify | [brief description] |

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| docs/<package>/overview.md | Update/Create | [what needs documenting at the package level] |
| docs/<package>/architecture.md | Update | [if package-level layer patterns change] |
| docs/<package>/<concern>/index.md | Update/Create | [if a concern's Purpose or Structure changes] |
| docs/architecture.md | Update | [if cross-package architecture patterns change] |

[If no documentation impact: "No documentation changes expected — internal implementation only."]

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |

## Dependencies

[Any external dependencies: packages to install, services to configure, environment variables]

## Supporting Documents

- [Research](research.md) — if research was performed
- [Data Model](data-model.md) — if data entities are involved
- [Contracts](contracts.md) — if API changes are involved
```

For the `## Specialist Consultation` section's consultation table, emit the controlled-shape skeleton via the helper and fill its rows — one row per specialist consulted (Verdict from the enum `accepted` / `modified` / `rejected` / `no-response`; Cites required; the `(none)` row stays when no specialist was consulted):

```bash
.devforge/lib/plan_helper render-consultation-block
```

The helper takes no arguments and owns the column names and verdict enum. Copy its stdout into the `## Specialist Consultation` section of `plan.md` and fill the rows; this table is the single source of truth for consultation provenance.

### The `**Run by**:` provenance line

The header's `**Run by**:` line records who ran the command that CREATED this plan. No helper composes it — `plan.md` is orchestrator-authored prose end to end, so this line is yours to resolve, and there is no `plan_helper` verb for it (do not add one). Resolve it in this order, and stop at the first step that yields an answer:

1. **Read back before rewriting.** If `<feature_dir>/plan.md` already exists at this point — a Phase 0a.7 re-entry rewriting a prior plan, or a Phase 3 `request-changes` loop coming back through this phase — read that file and carry its existing `**Run by**:` value into the new header VERBATIM. Whatever the file on disk records is what the rewrite records: a value carries over unchanged, and a file with no `**Run by**:` line stays without one — do not backfill a name onto a plan that never carried one. Then stop; steps 2 and 3 do not run on a rewrite. This step is what keeps the bound below true, since without it the field would silently become whoever re-ran the command last.
2. **The gate.** On a first write only (no `plan.md` at that path yet), read `AI_ATTRIBUTION` from `.devforge/project-config.json`. The gate is open only when that key's value is exactly the string `"Yes"`; every other state closes it — `"No"`, the key absent, the file absent or unreadable. This is the answer `/devforge:configure` already captured for attribution in files. There is no separate provenance key, and none is to be added: an install that answered "no attribution in files" must not receive a human name by this route either.
3. **The value.** With the gate open, run `git config user.name` and use exactly what it prints. Read no other git-config key — never `user.email` — and put nothing else in the line: no path, no address, no handle, no name taken from elsewhere in the session.

**Absent, never a placeholder.** When the gate is closed, or `git config user.name` prints nothing (unset, or git unavailable), `plan.md` carries NO `**Run by**:` line and no bound note — omit both lines. Never write `unknown`, never leave the value blank, and never substitute a stand-in.

**The bound ships beside the line.** Whenever the `**Run by**:` line renders, the line directly under it is this sentence, verbatim:

```markdown
_Records who ran the command that created this document; not updated on later edits._
```

That sentence is the whole provenance claim: the field names the creator, and later edits — a `request-changes` rewrite, a `/devforge:grill` re-entry through Phase 0a.7, a downstream `**Status**:` flip — do not update it. A per-edit trail is deliberately not built here; `git log` already carries one.

`spec.md` and `research-report.md` carry the same line, the same bound sentence and the same rules; there they are rendered by `/devforge:specify`'s and `/devforge:research`'s own helpers rather than composed by hand.

## PHASE 2.5: Plan-Spec Cross-Reference Check

Before presenting the plan to the user, verify completeness:

1. Read every AC from the spec's Acceptance Criteria section.
2. For each AC, verify the plan addresses it:
   - Check the plan's "Layer Map" and "File Impact" for files/components related to this AC.
   - Check "Key Design Decisions" for approach decisions relevant to this AC.
   - For a BEHAVIORAL AC — one asserting what a path emits, returns, or does at runtime — coverage means naming the "Key Design Decisions" row whose behavior change satisfies it. A "Layer Map" / "File Impact" file match does NOT cover such an AC, and an AC that no decision's behavior change reaches is uncovered even when every file it names already appears in "File Impact". This is what catches a change to shared code: there, "the files this AC names are unchanged" or "they are already in the impact list" reads as coverage while the behavior at that AC's path changes anyway — a file list is evidence about files, never about behavior. The two bullets above stay the whole check for an AC about files themselves (what exists, where code lives). A behavioral AC left uncovered goes to step 3 like any other uncovered AC — revise, or add the Risk Assessment line.
3. If any AC has no clear implementation path in the plan:
   - Revise the plan to add the missing coverage.
   - If you cannot determine the implementation path, add it to the plan's Risk Assessment as: "AC-[N] has no clear implementation path — requires clarification during breakdown".
4. Check the reverse: does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning (add to the plan's File Impact table with a note).
5. **Surface departures.** If any Key Design Decision is flagged `DEPARTURE` in its Why column (per architect Rule 3), fill the `### Established-Convention Departures` subsection — one row per departure — and include the departures line in the Phase 3 approval summary. If there are no departures, omit both the subsection and the summary line entirely; do not emit an empty section or a "none" line (greenfield stays silent).
6. **Out-of-scope-respect trace.** For each Key Design Decision, read its `Why` rationale and confirm it traces to an in-scope AC or constraint — and that it does NOT reference a term the spec marked Out of Scope in §6, nor an unverified hypothesis carried in from the user's prompt or upstream handoff. Flag any decision whose rationale reaches into §6 OOS: a decision solving an excluded concern is an over-solve. On a flag, do not silently keep the decision — re-enter Phase 1.3, have the architect either re-scope the decision to the in-scope baseline (its Phase 1.3 sub-question 5 minimal change) or escalate the §6 concern to the user per its Rule 6 (termination), triggered by its Rule 9 OOS-respect check. This is the read-side backstop for the §6-respect the architect's sub-question 6 asks at Phase 1.3 (defense in depth — sub-question 6 prevents an OOS-reaching decision; this step catches one that slipped through). **v1 is an LLM-prose step** the orchestrator performs by reading each decision's rationale against the spec's §6 entries (the same §6 lines `render-findings-from-spec` enumerated at Phase 1.5). The mechanized form — a `plan_helper` token-overlap scan of decision rationales against the §6 OOS terms (the same token-overlap technique `/devforge:specify`'s `verify-scope-coherence` already uses to warn when a §5 AC / §4 affected-area mandates a concern the §6 Out-of-Scope excludes — structurally identical: §6 OOS as the source term-set, a second text body as the scan target) — is **DEFERRED** to a later pass, built only after empirical miss-rate justifies it; it is NOT part of v1.
7. **Narrowing-restriction trace.** For each Key Design Decision that restricts existing shared-code behavior, confirm its Why column records the caller-scoped vs layer-wide classification (per the constitution's Narrowing rule, Design Principles section) and the affected caller set: for a caller-scoped restriction, every in-scope caller wired with the opt-in; for a layer-wide restriction, the full list of current callers affected plus why a caller-scoped opt-in can't cover it. If the classification or caller set is missing, re-enter Phase 1.3 and re-invoke the architect (its sub-question 7) rather than filling it in yourself. This is the read-side backstop for sub-question 7, mirroring step 6's shape; the mechanical detector for narrowing is deliberately deferred (there is no helper verb for it — do not invent one).
8. **Emission-matrix accounting.** If the feature has an emission matrix (`<feature_dir>/emission-matrix.md`, read where it sits — it is never copied into `plan.md`), confirm every row whose `Verdict` is `affected` is accounted for in some Key Design Decision's `Why` column: either named there as a call site that decision covers, or answered there in one sentence as a call site needing no covering. If any `affected` row is neither covered nor answered, re-enter Phase 1.3 and re-invoke the architect (its sub-question 11) rather than filling it in yourself. This is the read-side backstop for sub-question 11, mirroring step 7's shape; there is no mechanical detector for matrix accounting — do not invent one. When the feature has no emission matrix, this step has no work: perform none of it and record nothing.

## PHASE 3: User Approval

**Mode-dependent execution path** — auto vs interactive paths:

- **If auto mode is active** (detect via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously): do not pause for clarifying questions during plan creation. Apply model's recommended defaults to any decision the spec left as `[default applied]` or that the plan surfaces fresh. Document each in a "Decision Points Resolved" subsection of the plan summary, marked `[default applied]`. The user reviews defaults at the approval gate below.
- **If auto mode is NOT active** (interactive mode, default): if the plan surfaces decision points the spec didn't resolve (e.g., between filter patterns, single-target invocation methods, or override mechanisms), pause and ask the user via `AskUserQuestion` (or fallback to numbered markdown list) before writing. Do not silently apply defaults in interactive mode.
- **When uncertain about mode**: prefer pausing (interactive default). Asking and waiting is reversible; proceeding without input is not.

**HARD GATE**: The plan MUST be approved before `/devforge:breakdown` can generate tasks.

Present a summary. The block below is LLM-authored (not helper-driven — plan state lives on disk in `plan.md`, not in a state JSON; there is no `render-plan-summary` subcommand to invoke):

"I've created the technical plan at `<feature_dir>/plan.md`.

**Approach**: [1-2 sentences]
**Files affected**: [count] ([N] new, [M] modified)
**Key decisions**: [list the most important ones]
**Departures from convention**: [include this line ONLY if ≥1 departure flagged: "[N] flagged — review §Established-Convention Departures before approving"; omit the entire line when none]
**Pure-builder targets**: [include this line ONLY if ≥1 target named: "[N] named — each requires a dedicated property-test task at /devforge:breakdown (hard gate)"; omit the entire line when none]
**Dead code declared**: [include this line ONLY if ≥1 row named: "[N] path(s) — MUST-delete, folded into the owning task at /devforge:breakdown"; omit the entire line when none]
**Follow-on cleanups**: [include this line ONLY if ≥1 item tagged: "[N] recommended — review §Follow-On Cleanups before approving (advisory, not a task)"; omit the entire line when none]
**Emission matrix**: [include this line ONLY if the feature has an `emission-matrix.md`: "[N] affected row(s) — each accounted for in a Key Design Decision's Why column"; omit the entire line when the feature has no matrix]
**E2E scenarios**: [include this line ONLY if ≥1 scenario named: "[N] named — each needs a dedicated test-authoring task at /devforge:breakdown; review §E2E Scenarios before approving, because nothing checks that the task set covers them"; omit the entire line when none]
**Risks**: [high-risk items if any]
**Supporting docs**: [list what was generated]"

Then ask via `AskUserQuestion`:

- Question: `"Approve this plan?"` — single-line text.
- Options: `["approve", "request-changes", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`approve`** → proceed to Phase 4 (manual handoff block).
- **`request-changes`** → in the next turn, ask the user which section or decision to revise. Re-enter the relevant phase (Phase 0 Research Evaluation if research signals changed / Phase 1 / Phase 1.5 / Phase 2 / Phase 2.5 as needed); re-render the affected portion of `<feature_dir>/plan.md` via Write or Edit; re-present the summary above and re-issue this approval prompt. The state lives in the rendered file on disk; this loop mutates it in place.
- **`cancel`** → tell the user `"/devforge:plan cancelled. Plan draft preserved at <feature_dir>/plan.md."` and end the turn.

## PHASE 4: Manual handoff to /devforge:breakdown

On `approve`, first write the structured plan→breakdown handoff via the helper. The `<plan-path>` for the calls below is the absolute path to the plan written in Phase 2 — `<feature_dir>/plan.md` (the same path shown in the Phase 3 approval summary).

```bash
.devforge/lib/plan_helper finalize-handoff <plan-path>
```

The helper parses the rendered `plan.md` and atomic-writes `<feature_dir>/plan-handoff.json` (a structured handoff carrying the breakdown seeds — layer map, file impact, documentation impact, decisions, risks, specialist consultation, dependencies, pure-builder targets, change-induced dead code — plus provenance to the sibling `/devforge:specify` handoff). Just as it parses the `### Pure-Builder Targets` table into the handoff's pure-builder targets, `finalize-handoff` parses the `### Change-Induced Dead Code` table into `dead_code_rows` — the typed MUST-delete rows sub-question 9 declared; a plan with no such subsection carries an empty `dead_code_rows` list. Handle the exit code:

- Exit 0 → the helper wrote `<feature_dir>/plan-handoff.json` and printed its path on stdout. Surface the written path to the user in one line, e.g. `"Structured plan handoff written: <path> (consumed by /devforge:breakdown Phase 0 via breakdown_helper read-plan-handoff)."`
- Non-zero exit (Exit 2 → `plan.md` not found or rendered content failed schema validation; Exit 1 → I/O error writing `plan-handoff.json`, e.g. permissions or disk-full) → the helper could not write or validate the handoff. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Do NOT abort — continue to the `render-breakdown-handoff` text block below. The structured handoff is best-effort; the manual text block is the guaranteed human bridge.

The `plan-handoff.json` is the **producer side** of the plan→breakdown handoff, consumed by `breakdown_helper read-plan-handoff` in `/devforge:breakdown` Phase 0. There is no auto-dispatch and no auto-consume: the manual text block below remains how the user launches `/devforge:breakdown`.

**WIP-commit the plan artifacts.** With `plan.md` written in Phase 2 and `plan-handoff.json` written above, `[WIP]`-commit the plan artifacts so the work is git-safe immediately. Compose `--paths` from `spec.md` + `plan.md` + `plan-handoff.json` plus whichever optional supporting docs THIS run wrote — include `research.md` (if Phase 0 generated it), `data-model.md` (if Phase 1.1 drafted it), and `contracts.md` (if Phase 1.2 drafted it); omit the ones this run did not write. Use the feature directory's own name — the last segment of `<feature_dir>`, called `<feature-dir-name>` below — for the label. `spec.md` is a mandatory entry — not because `/devforge:plan` produced it, but because Phase 0b may have mutated its `**Status**:` line on disk (flipped Draft→Approved, or inserted a missing Status line as Approved), so that mutation must ride the same git-safe commit as the plan artifacts; when Phase 0b changed nothing (already Approved, Complete, or a non-standard status) staging the unmodified file is a benign "nothing to commit" no-op.

The block below shows the mandatory three-entry minimum — append `"<feature_dir>/research.md"`, `"<feature_dir>/data-model.md"`, and/or `"<feature_dir>/contracts.md"` to the `--paths` array for whichever of those THIS run wrote (omit the ones it did not). The array is composed at runtime, not copied verbatim. `commit-artifacts` takes an absolute entry and a repo-relative one alike, so pass `<feature_dir>` in the form PHASE 0a resolved it and re-shape nothing.

```bash
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["<feature_dir>/spec.md", "<feature_dir>/plan.md", "<feature_dir>/plan-handoff.json"]' \
    --label "plan: <feature-dir-name>"
```

The helper stages those paths in the install repo and makes a `[WIP] plan: <feature-dir-name>` commit; it is install-repo-only (never the source repo in wrapper mode). This call is UNCONDITIONAL — always run it, even if `finalize-handoff` above exited non-zero (`plan.md` still exists, and the helper benign-skips any `--paths` entry that was not written). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifact is already written, so warn the user with the helper's stderr and continue to the `render-breakdown-handoff` block below; do NOT abort the approve flow); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op.

**Surface the design-stakes hint (advisory, non-blocking).** `finalize-handoff` in the first step of this phase wrote `plan-handoff.json` alongside `<plan-path>` (its sibling in the same feature directory) and printed that file's absolute path on stdout — call it `<plan-handoff-path>`. Run the stakes-hint helper against that same path:

```bash
.devforge/lib/plan_helper stakes-hint <plan-handoff-path>
```

The helper reads that `plan-handoff.json` and prints a short "consider running `/devforge:grill`" hint to stdout WHEN the plan's structured signals indicate high stakes (wide file impact, a new data model, a real new dependency, security-relevant risks or decisions, or an unusually risk-laden plan of 4+ recorded risks); otherwise it prints nothing. It always exits 0. Handle its stdout:

- **Non-empty stdout** → copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).
- **Empty stdout** → emit nothing and proceed silently to the `render-breakdown-handoff` step below. Empty output is the normal case for an ordinary plan and is NOT an error.

This hint is ADVISORY and NON-BLOCKING: it never blocks the approve flow, it gates nothing on its own, and the user is free to ignore it. It is NOT what makes `/devforge:grill` happen — `/devforge:breakdown` carries its own entry gate that refuses to decompose a plan until a grill has run for it, and this hint neither implements nor substitutes for that gate. All the hint adds is that THIS plan is high-stakes, so the grill it will get anyway deserves extra attention. Like the other PHASE 4 helper calls, this step is best-effort; because `stakes-hint` always exits 0, there is no non-zero exit to handle here.

Then emit the deterministic handoff block via the helper:

```bash
.devforge/lib/plan_helper render-breakdown-handoff <resolved-path> <plan-path>
```

Handle the exit code:

- Exit 2 → the spec or plan file could not be read. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), tell the user to verify `<feature_dir>/plan.md` exists and re-run `/devforge:plan`, and end the turn. Unlike `finalize-handoff`'s non-blocking exit 2 above (which continues to this block), a failure here DOES end the turn — this block is the guaranteed human bridge, and if it cannot render there is no fallback next-step to fall through to.
- Exit 0 → stdout is the deterministic manual-next-step block — copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The block heading reads `## Manual next step — run /devforge:breakdown`; it carries the spec AC count, plan file-impact count, plan risk count, and the literal `/devforge:breakdown <plan-path>` invocation. The block also instructs the user to **restart Claude Code** before running `/devforge:breakdown` so any newly-installed command is picked up.

After the block lands in the user-facing message, end the turn with one short confirmation: `"/devforge:plan is done. Plan status: Draft — plan stays Draft until /devforge:breakdown runs. Restart Claude Code, then copy the invocation line from the block above to continue."` Do NOT restate that invocation in your closing sentence — the block already contains the literal `/devforge:breakdown <plan-path>` line, which `render-breakdown-handoff` composes (it is the helper's string, not this spec's — do not rewrite it here).

## IMPORTANT RULES

1. **Plans describe HOW, not WHAT** — the spec already defines WHAT. Don't repeat requirements, translate them into technical decisions.
2. **Constitution compliance is mandatory** — verify before presenting to user. If the plan would violate a rule, redesign or flag it.
3. **Reference existing code** — for existing codebases, always reference actual file paths and existing patterns. Don't propose new patterns when existing ones work.
4. **Greenfield: follow the scaffolding guide** — the constitution's Section 7 defines where things go. Follow it.
5. **Minimal supporting docs** — only create research.md, data-model.md, contracts.md if they're actually needed. Don't create empty files.
6. **Memory check** — Phase 0's `read-memory` step is this command's only memory read; when `memory_state` is `populated`, its lessons ride into the Phase 1.3 architect brief. Do not add a second orchestrator-side read of `.devforge/memory.md` elsewhere in this command.
7. **Keep it scannable** — tables over paragraphs, decisions over discussions.
8. **Docs context comes from the spec** — the spec already incorporates `docs/` knowledge. Do not re-read docs; use the spec's "Current State" and "Affected Areas" sections. If the spec notes stale or missing docs, carry that forward as a plan risk.
