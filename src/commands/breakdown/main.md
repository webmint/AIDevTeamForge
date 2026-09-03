---
name: breakdown
description: Translate an approved technical plan into ordered, atomic, agent-assigned tasks with verifiable contracts and a structured breakdown→implement handoff.
argument-hint: "[plan-file]"
---

# /devforge:breakdown — Task Breakdown from Plan

`/devforge:breakdown` is repeatable per feature. It takes an approved plan authored by `/devforge:plan` and produces ordered, atomic, agent-assigned tasks with verifiable cross-task contracts: a `tasks/*.md` file per task, a `tasks/README.md` index, and a structured `breakdown-handoff.json`. The orchestrator (the LLM following this spec) writes all task artefacts in the main thread via Write or Edit. Subagent dispatch is reserved for **decision work at one mandatory hook**: the `architect` agent is invoked at Phase 2 (Decomposition) for every run to validate task atomicity, dependency ordering, contract-chain integrity, and per-task implementability. Outside that hook, the orchestrator authors directly and assigns agents via the inlined Agent Assignment table — no per-phase auto-dispatch. Phase 0b's hard gate ensures `/devforge:constitute` has populated the constitution before any breakdown work fires. Produces `<feature_dir>/tasks/` plus `<feature_dir>/breakdown-handoff.json`, and ends with a manual handoff to `/devforge:implement` — no automated dispatch.

Usage: `/devforge:breakdown [plan-file]` (e.g. `/devforge:breakdown <feature_dir>/plan.md`, or `/devforge:breakdown` with no argument to use the most-recently-modified plan under `specs/`).

## Outputs of this phase

`<feature_dir>` — here and everywhere else in this document — is the feature directory this run reads from and writes into: one path the orchestrator holds in working memory for the rest of the run. PHASE 0a resolves it: `pick-plan` prints the absolute path of one `plan.md`, and that file's parent directory is `<feature_dir>`. Hold it exactly as PHASE 0a resolved it — do not re-shape it, do not rebuild it from parts, and do not spell what is inside it. Every artifact path below is `<feature_dir>` plus a filename, and so is every sibling this command reads beside the plan — with one exception, this command's own `tasks/` subdirectory, which holds the task files and their index.

- `<feature_dir>/tasks/NNN-<title>.md` — one rendered task file per task (required).
- `<feature_dir>/tasks/README.md` — task index with dependency graph, risk assessment, and review checkpoints (required).
- `<feature_dir>/breakdown-handoff.json` — structured producer-side handoff (best-effort; see Phase 5).
- `<feature_dir>/design-manifest.json` — the design-fidelity binding: the built-side wiring (`route` + anchor-selector/built-testid pairs) mapping the captured design intent to the elements the feature builds (conditional; written only when the feature has a `design/reference.html` — see Phase 2.5).

After approval (Phase 5), `/devforge:breakdown` WIP-commits these artifacts — the whole `tasks/` directory, `breakdown-handoff.json`, `plan.md` (whose `**Status**:` PHASE 0b flipped), and (when Phase 2.5 produced it) `design-manifest.json` — via `.devforge/lib/artifact_helper commit-artifacts`. The commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/devforge:breakdown` continues — the artifacts are already written). The `[WIP]` commit folds into `/devforge:finalize`'s squash, so the final PR is unchanged. **In WRAPPER mode this is the FIRST per-step commit that tracks the task files + `tasks/README.md` in the install repo** — `/devforge:implement`'s wrapper path stages ONLY source code in the source repo and leaves the task files uncommitted, so this commit is NOT redundant there. (In standalone mode `/devforge:implement` already tracks the task files, so re-staging unchanged ones is a harmless no-op; `breakdown-handoff.json` is newly tracked either way.)

## Context in the Workflow

```
/devforge:research (optional) → /devforge:specify → /devforge:plan → /devforge:grill → /devforge:breakdown → /devforge:implement → /devforge:review → /devforge:verify → /devforge:summarize → /devforge:finalize
```

`/devforge:breakdown` runs AFTER the plan is approved, BEFORE task execution. The plan describes HOW the feature maps to the architecture; `/devforge:breakdown` decomposes that into atomic, independently-verifiable units of work with explicit dependencies and contracts.

## PHASE 0a: Plan resolution

`/devforge:breakdown` consumes one approved plan per invocation. Resolve which plan via the helper:

```bash
.devforge/lib/breakdown_helper pick-plan $ARGUMENTS
```

If `$ARGUMENTS` is non-empty, the helper validates the explicit file path (must be an existing `plan.md` file, not a directory) and prints its absolute path on stdout. If empty, the helper picks the most-recently-modified `plan.md` under `specs/`. Exit 2 means no valid plan was found — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

Capture the resolved absolute path. Its parent directory is this run's `<feature_dir>` — hold that too, exactly as resolved, because every artifact this command writes and every sibling it reads is `<feature_dir>` plus a filename (or, for the task files and their index, `<feature_dir>/tasks/` plus a filename). Then render the preview block:

```bash
.devforge/lib/breakdown_helper render-pick-summary <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Exit 2 means the plan file is missing — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block, then end the turn. Otherwise ask the user via `AskUserQuestion`:

- Question: `"Process this plan?"` — single-line text.
- Options: `["yes", "pick-other", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`yes`** → proceed to Phase 0a.5 with the resolved path.
- **`pick-other`** → in the next turn, run `.devforge/lib/breakdown_helper list-plans` and emit stdout as a numbered list inside a fenced block (exit 2 means no `specs/` directory exists — copy the helper's stderr VERBATIM into a fenced block and end the turn). The helper output is unbounded (one line per plan, mtime desc). For `AskUserQuestion`, take the first four lines as the four option labels — AskUserQuestion caps at four options, so the LLM truncates client-side, not the helper. Question: `"Which plan to break down?"` — single-line text. If more than four plans exist, include `other` as the fourth option; on `other`, ask the user via free-text follow-up for the explicit path, then re-run `pick-plan <path>` to validate. On the chosen path, treat it as the resolved path and proceed to Phase 0a.5.
- **`cancel`** → tell the user `"/devforge:breakdown cancelled. Re-run /devforge:breakdown when ready."` and end the turn.

## PHASE 0a.5: Upstream handoff (consumer)

`/devforge:plan` may have written a sibling `plan-handoff.json` next to the plan, carrying the structured decomposition seeds (layer map, file impact, key design decisions, dependencies, risks). This phase surfaces those seeds as the authoritative decomposition input. There is no user gate here; do not invoke `AskUserQuestion`.

Read the sibling handoff via the helper:

```bash
.devforge/lib/breakdown_helper read-plan-handoff <resolved-path>
```

- Stdout `no-handoff` → no sibling `plan-handoff.json` exists. Tell the user `"No structured plan handoff; decomposing from plan.md directly."` and proceed to Phase 0a.6 with the resolved path. The decomposition input comes from reading `plan.md` directly in Phase 0 and Phase 1. One caveat: if `plan.md` contains a `### Pure-Builder Targets` section, run `.devforge/lib/plan_helper finalize-handoff <resolved-path>` NOW to produce the missing handoff (the producer is idempotent) — the Phase 3.5 property-coverage gate fail-closes on declared-but-handoff-less targets, so producing it here avoids a late halt; when `plan.md` has no such section, no action is needed (that gate skips cleanly).
- A `## Upstream plan seeds` block (Layer Map / File Impact / Key Design Decisions / Dependencies / Risks, plus a trailing `### Pure-Builder Targets (property-test lane)` sub-block when `/devforge:plan` declared any pure-builder targets) → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). State that this block is the authoritative decomposition input — Phase 1 (Deep file analysis) and Phase 2 (Decomposition) are driven by these seeds, not by re-scanning the spec. When the `### Pure-Builder Targets (property-test lane)` sub-block is present and non-empty, its targets drive Phase 3's property-test task emission rule and the Phase 3.5 property-coverage gate. Then proceed to Phase 0a.6 with the resolved path.

Exit 2 means the sibling `plan-handoff.json` is malformed, the wrong handoff kind, or the wrong schema version — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

**Change-induced dead code (MUST-delete kill-list).** The `read-plan-handoff` seeds block above surfaces the decomposition seed sub-sections only — it does NOT carry the change-induced dead-code rows. Read those from `plan.md`'s `### Change-Induced Dead Code` table directly, the same `plan.md` this phase's no-handoff path and Phase 0 / Phase 1 read as the full source. When that table holds ≥1 MUST-delete row (columns File | Anchor token | Kind | Why dead), surface a `### Change-Induced Dead Code (MUST-delete)` sub-block listing each row (file — anchor token — kind — why dead) in your next user-facing message, and state that these are MUST-delete obligations — dead by the constitution's §3.5 (No dead code) — whose removal Phase 2's decomposition and Phase 3's task-writing fold into the owning task. When `plan.md` has no such table, there is no kill-list; surface nothing (no empty sub-block, no "none" line).

**Declared e2e scenarios (full-stack flows).** The `read-plan-handoff` seeds block above surfaces the decomposition seed sub-sections only — it does NOT carry the e2e scenario rows. Read those from `plan.md`'s `### E2E Scenarios` table directly, the same `plan.md` this phase's no-handoff path and Phase 0 / Phase 1 read as the full source. When that table holds ≥1 scenario row (columns Scenario | Acceptance criteria | Flow steps | Preconditions), surface a `### E2E Scenarios (full-stack flows)` sub-block listing each row (scenario — acceptance criteria — flow steps — preconditions) in your next user-facing message, and state that each row is a decomposition obligation Phase 3's task-writing covers with a dedicated test-authoring task — and that nothing at Phase 3.5 checks that coverage. When `plan.md` carries no such table, this feature declared no full-stack flows; write nothing about them — not a sub-block, and not a line recording their absence.

## PHASE 0a.6: Grill gate (MANDATORY)

`/devforge:breakdown` requires that `/devforge:grill` has already run for the resolved plan. This phase is a gate only — it blocks the run when no completed grill run is recorded for that plan, and does nothing else. There is no user gate here; do not invoke `AskUserQuestion`.

Check the grill run via the helper:

```bash
.devforge/lib/breakdown_helper verify-grill-ran --plan <resolved-path>
```

The verb is read-only — it never flips a `**Status**:` line and never writes a file. It resolves `grill.md` and its sibling `grill-state.json` from the resolved plan's own directory (`<feature-dir>/grill.md`, `<feature-dir>/grill-state.json`), and it passes only when BOTH conditions hold: the report exists, AND the adversary status recorded in the state file is `complete` or `clean`. `clean` passes because an adversary that ran and grounded no attack is a successful adversarial pass, not a failed one; `failed` and `missing` do NOT pass even when a `grill.md` sits on disk, because that dispatch produced no usable output. What this gate establishes is therefore that the grill RAN — not merely that a report file exists. Handle the exit code:

- Exit 0 → a `grill.md` sits next to the plan and its sibling state records an adversary run that produced output. Stdout is a JSON ack carrying `ran`, `report_path`, and `adversary_status`; surface the `report_path` value to the user in one line, e.g. `"Grill ran for this plan: <report_path>."` Then proceed to Phase 0b with the resolved path.
- Exit 2 → BLOCKED. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The stderr is already the complete user-facing message: on the four grill-state causes — no `grill.md` next to the plan, a `grill.md` whose sibling `grill-state.json` is missing / unreadable / not a valid state object, a state file carrying no recorded adversary run at all, an adversary dispatch that did not complete — it names the cause, states that this gate is mandatory with no override, and carries the `/devforge:grill <plan-path>` line to run next. The fifth cause is the resolved `plan.md` itself being unreadable, which prints the plain `breakdown_helper: cannot read plan: <path>` line and names no next command (running `/devforge:grill` would not repair a bad plan path). Add nothing to either shape and drop nothing from it.

On the BLOCKED path this run is over. Offer to run `/devforge:grill <plan-path>` now and end the turn; run it only once the user agrees, and never re-invoke `/devforge:breakdown` on that same agreement — when the grill finishes, propose `/devforge:breakdown` as its own next step, which restarts at Phase 0a. One agreement covers one command.

This gate reads PRESENCE and the RECORDED ADVERSARY STATUS only — never the report's disposition, and never its freshness. A grill report recommending KILL satisfies it exactly as a PROCEED one does, because the human owns the disposition at the Phase 4 approval gate. A STALE report — a `grill.md` written against an earlier `plan.md` — satisfies it too, and deliberately so: a freshness condition would mean that acting on the report's own findings by revising the plan invalidates the report and buys another full adversarial run, while ignoring those findings costs nothing, and a gate that charges you for taking its findings seriously is worse than no gate. Do not add a verdict condition, a freshness condition, an override flag, or a skip arm to this phase: the helper offers none of them, and a future session must not "strengthen" the gate into one that reads the disposition or re-hashes the plan.

This phase runs BEFORE Phase 0b's Draft → Approved flip by design — a plan that cannot be decomposed must not be flipped to Approved.

Sub-phase numbers are per-command: the `0a.6` label is local to `/devforge:breakdown` and carries no correspondence to the number any other command gives its own entry gate, so a future session must not renumber this phase to match one.

## PHASE 0b: Status flip + gates

**Guard**: Read `constitution.md`. If it contains `_Run /devforge:constitute to populate_` (or the legacy un-namespaced `_Run /constitute to populate_`, which an older install may still carry), stop: "⛔ constitution.md has not been populated yet. Run `/devforge:constitute` before using `/devforge:breakdown`."

The act of running `/devforge:breakdown` constitutes approval of the plan for decomposition. Flip Draft → Approved structurally via the helper:

```bash
.devforge/lib/breakdown_helper check-status-and-flip <resolved-path>
```

Stdout is one of five state tokens:

- `flipped` — plan was Draft, now Approved. Tell the user: `"Plan status: Draft → Approved (implicit approval via /devforge:breakdown)."`
- `already-approved` — continue silently; no message needed.
- `complete` — the plan has a Status of `Complete` (e.g. manually set). Warn the user, then `AskUserQuestion` `"Plan status is Complete — proceed against a completed plan?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.
- `inserted` — plan lacked a Status line; helper inserted `**Status**: Approved`. Tell the user: `"Plan was missing a Status line; helper inserted **Status**: Approved."`
- `unknown-status:<value>` — plan has a non-standard status. Tell the user the value, then `AskUserQuestion` `"Status is non-standard — proceed?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.

Exit 2 means the plan is malformed (neither Date nor Status frontmatter line). Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

## PHASE 0b.5: Model advisory (printed, never gating)

This step prints one line and does nothing else: it asks no question, it gates nothing, and the user is free to ignore what it says. Every arm above that carries the run forward reaches it.

`/devforge:breakdown` does its judgment work in the `think` tier. Read `CLAUDE_TIER_THINK` from `.devforge/project-config.json` for that tier's configured model. When the file is absent, or that key is absent or `null`, use the built-in `think` default `opus` — the same value `.devforge/lib/configure_helper apply-agent-models` writes onto a `think`-tier agent whose configured value is null; that verb is named here for provenance and is NOT invoked by this step. For the second half of the line, name the model this session runs on as your own environment states it; when your environment states none, write the literal `unknown` rather than guessing one.

Tell the user: `"This command's judgment work belongs to the think tier; configured think model: <value>; this session runs on: <session model, or unknown>."`

What the line recommends is a tier, resolved through this install's own `/devforge:configure` answers, so it tracks the user's choice and names no model version. Then proceed to PHASE 0 (Context load) with the resolved path.

## PHASE 0: Context load

**This phase always runs.** Load the context the decomposition depends on.

Read these in order:

1. The plan's sibling `spec.md` (same `<feature_dir>`) — the acceptance criteria the tasks must collectively cover. Capture its absolute path — `<feature_dir>/spec.md`, the sibling of the resolved plan path — as `<spec-path>`; the Phase 0 drift check, Phase 1.5 findings, Phase 3 task writing, and Phase 3.5 AC-coverage gate all pass this `<spec-path>` to their helpers.
2. `plan.md` (the resolved path) — the layer map, file impact, key design decisions, and risk assessment. If Phase 0a.5 surfaced a `## Upstream plan seeds` block, that block is the authoritative seed; `plan.md` is the full source.
3. The feature's supporting docs if present: `research.md`, `data-model.md`, `contracts.md` (same directory).
4. `constitution.md` — architecture rules and constraints.
5. `.devforge/memory.md` — past lessons about similar decompositions. Read it through the **Memory check** step below rather than by opening the file directly.
6. `CLAUDE.md` — project structure, the `## Architecture` section, and the `## Packages` table for multi-stack projects.

**Memory check.** Read item 5's lessons file through the helper:

```bash
.devforge/lib/breakdown_helper read-memory
```

The verb takes no arguments and always exits 0. It writes a JSON object to stdout carrying `memory_state`, `memory_excerpt` (the populated `## ` sections of `.devforge/memory.md`, `## Task Outcomes` excluded), and `memory_present`. Capture that stdout and branch on `memory_state`:

- `absent` or `stub` → no-op. Say nothing to the user about memory, raise no warning, add no step. A memory file that is missing, or still the stub the installer ships, records no lessons yet; on a new project that is the correct state, not a fault to remedy.
- `populated` → read `memory_excerpt` and pick out the entries bearing on how a feature like this one was split before — a task boundary that proved wrong, an ordering that had to be redone, a contract that was missed. Carry them into Phase 1's file analysis and into Phase 2, where the draft task set is built and the architect validates it; include the bearing entries inline in that architect brief, since they are helper stdout rather than one of the files the brief's path list carries. An entry that surfaces after Phase 2 has fixed the task boundaries is too late to change them. When `memory_excerpt` comes back empty even though `memory_state` is `populated` — every populated line sits in the excluded `## Task Outcomes` section — take the `absent` / `stub` no-op branch above instead: carry nothing into Phase 1 or the Phase 2 architect brief, and say nothing to the user about memory.

`memory_excerpt` is not the whole file: it renders the file's populated `## ` sections — a section with no entries under its heading is dropped heading and all, `## Task Outcomes` is excluded outright, and any other section is kept — and when the line budget cannot fit a section whole, the lines it drops are always that section's EARLIEST ones, with an inline marker line right after the heading naming how many were omitted. An entry's absence from a non-empty excerpt therefore means it sits in the excluded section or behind a marker the excerpt itself declares, never "never recorded"; an empty excerpt means there are no readable lessons — the file is absent or still the shipped stub, or everything in it sits in the excluded section.

**Honesty bound.** A carried memory entry is an UNVERIFIED prior-session assertion, not evidence for this decomposition: it is a constraint to respect and a candidate to check against the plan and the code, never grounds on its own for splitting, bundling, or ordering a task. A past session wrote it, and the code it describes may have changed since — or the entry may have been wrong when it was written.

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path. Claude artifact paths (`specs/`, `docs/`) remain at the workspace root.

**Optional spec drift check**: the spec may have been written against source files that changed since. Check via the helper (advisory, gate only):

```bash
.devforge/lib/cbm_sync_helper check-spec <spec-path>
```

Stdout is one of four forms:

- `current` — the spec's cited files are unchanged since it was stamped. Proceed silently to Phase 1; no message needed.
- `missing` — no drift stamp exists for this spec. Tell the user `"No drift stamp for this spec; proceeding."` and proceed to Phase 1.
- `drift <a>..<b> <file-1> <file-2> ...` — one or more spec-cited files changed since the spec was stamped. Tell the user the spec's cited files changed since it was stamped, listing the changed files from the `<file-...>` tokens. If the `drift` token carries no `<file-...>` tokens (only the two SHAs), do not claim specific files changed — tell the user the spec has drifted from its stamp but the cited-file list could not be computed (the spec file may have moved). Then ask via `AskUserQuestion` `"Spec-cited files changed since the spec was written — proceed with breakdown?"` — single-line text — with options `["proceed", "cancel"]`. On `cancel`, tell the user `"Re-check the spec against the changed files before re-running /devforge:breakdown."` and end the turn. On `proceed`, continue to Phase 1.
- `not-a-git-repo` on stdout (exit 2) — the drift check cannot run (no git repository / no HEAD / git binary missing). Tell the user `"Spec drift check unavailable (not a git repository); proceeding without it."` and proceed to Phase 1. The drift check is advisory — a non-git target must NOT block breakdown.

## PHASE 1: Deep file analysis

Analyze the files the tasks will touch, driven by the plan-handoff `File Impact` + `Layer Map` seeds (from Phase 0a.5) and by reading `plan.md`. Do NOT re-scan the spec for file impact — the plan already settled it. Branch on whether the feature touches an existing codebase or is greenfield.

### If existing codebase

For every file listed in the plan's File Impact table:

1. **Read the file** completely.
2. **Map its dependencies**: what does it import? What imports it?
3. **Identify the change points**: exactly which functions/blocks need to change.
4. **Estimate scope**: how many lines will change? Is it a rename or a logic change?
5. **Check for cascading effects**: will changing this file require changes in files not in the plan's File Impact table?
6. **Identify verifiable semantics**: what exports, interfaces, functions, or call patterns must exist after the change? What must be imported from where? These become the basis for cross-task contracts (Phase 3).

If you discover files that should have been in the plan but weren't, note them as additions — they go in the `## Additions to Spec` section of the tasks index (Phase 3).

**Restructuring over untested code (net-first ordering).** While reading each file, note which of its touched functions this change only RESTRUCTURES — moved, extracted, renamed, or re-shaped with the observable result unchanged — and whether a test covers them today. That second answer comes out of the reading itself: no phase of `/devforge:breakdown` runs a coverage tool, so it is what this analysis believes about coverage, never a measurement. Where a behavior-preserving surface has no covering test, the ordering default is NET FIRST — a task that writes the covering test is ordered AHEAD of the restructuring task, so the net exists and passes before the restructuring starts; the resulting edge is an ordinary depends-on edge, validated by Phase 2's dependency-ordering sub-question like any other. Phase 3's *Regression-net declaration* rule carries this analysis's answer into the task file.

### If greenfield (creating new files)

For every file listed in the plan's File Impact table:

1. **Confirm the file does not exist** — if not, this is a "Create" task.
2. **Read the constitution's scaffolding guide** — verify the file will land in the correct directory per the architecture rules.
3. **Identify the pattern reference** — find the closest pattern example from the constitution.
4. **Map required dependencies** — what types, interfaces, or modules must be created first?
5. **Check for infrastructure needs** — does this feature need new directories, config changes, or package installs?
6. **Identify verifiable semantics** — what exports, interfaces, or functions must exist after each creation step? These become cross-task contracts.

**Greenfield task ordering** follows this sequence:

1. **Infrastructure** — create directories, install packages, add config.
2. **Types / interfaces** — define the data shapes.
3. **Core logic** — domain / business logic, use cases, repositories.
4. **Presentation** — UI components, views, routes.
5. **Integration** — wire everything together (DI, routing, store registration).

## PHASE 1.5: Findings from Plan (REQUIRED INTERMEDIATE OUTPUT)

Before writing any task file, produce a structured intermediate output enumerating what the plan contains and which task will cover each item. This is a hard requirement.

Render the skeleton via the helper (pass the spec path so AC markers are emitted):

```bash
.devforge/lib/breakdown_helper render-findings-from-plan <resolved-path> <spec-path>
```

The helper emits `## Findings from Plan` with a `[TASK COVERAGE: ?]` marker on each plan File Impact + Layer Map row, and an `[ADDRESSED BY: ?]` marker on each spec acceptance criterion. Exit 2 means the plan file is missing — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. Otherwise copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). In the SAME message, replace each marker inline with the task(s) that will cover it:

- `[TASK COVERAGE: ?]` on a File Impact / Layer Map row → `[TASK COVERAGE: task NNN]` (or `tasks NNN, MMM` if split across tasks).
- `[ADDRESSED BY: ?]` on a spec AC → `[ADDRESSED BY: task NNN]` (or `tasks NNN, MMM`).

This intermediate output forces every plan row and every spec AC to be accounted for before tasks are written. Same purpose as `/devforge:plan` Phase 1.5: convert implicit recall into explicit enumeration. Skipping or compressing this step is a hard error.

After this intermediate output is complete, proceed to Phase 2. The "1.5" numbering runs after Phase 0/1 and before Phase 2 despite the numeric ordering, because it gates the task decomposition itself.

## PHASE 2: Decomposition (MANDATORY scoped architect)

This is the decision hook. Translate the plan + file analysis into a draft task set — atomic units, dependency edges, and Expects/Produces contracts — then have the `architect` validate the decomposition before any task file is written.

**Architect consultation: mandatory.**

Before writing any task file, invoke the `architect` agent via the Task tool to validate the decomposition. The architect's `think`-tier reasoning is the specialization point for task-boundary, dependency-direction, contract-chain-integrity, and per-task implementability calls — net-new judgment the plan did not produce. Writing task files without this consultation is a hard error at this phase.

**Orchestrator-mediated consultation relay (the architect emits requests; it does NOT invoke anyone):** subagents cannot spawn subagents, so the architect cannot consult a specialist itself. Instead the architect returns zero-or-more **consultation requests** alongside its validation, and the orchestrator (the LLM running this spec) performs the invocations. Run the loop:

1. Invoke the `architect` agent (mandatory, per above) with your draft task set and the four fixed sub-questions below. It returns its validation (confirmations + revisions to atomicity / ordering / contracts / implementability) AND zero-or-more consultation requests, each carrying a named specialist + a sub-question + context. An implementability finding whose gap is a plan-level decision `/devforge:plan` should have made (not a wording gap) surfaces as a human-escalation rather than a draft-task revision — route it per sub-question 4.
2. For each consultation request: invoke the named specialist via the Task tool with the architect's sub-question + context, capture the specialist's response, then **re-invoke the `architect`** with the relayed response so the architect can synthesize it into its validation. The architect never invokes the specialist — the orchestrator relays both directions.
3. The orchestrator MAY also consult a specialist directly when this spec calls for it, not only on the architect's request.

Any decomposition-relevant specialist may be named: `architect`, `frontend-engineer`, `backend-engineer`, `mobile-engineer`, `security-reviewer`, `db-engineer`, `migration-engineer`, `api-designer`, `performance-analyst`, `design-auditor`, `devops-engineer`, `qa-engineer`, `runtime-debugger`.

**Brief shape (pass file paths, NOT inlined content):**

- `<feature_dir>/spec.md`
- `<feature_dir>/plan.md`
- `<feature_dir>/research.md` / `data-model.md` / `contracts.md` (whichever exist)
- `CLAUDE.md` (architect reads `## Architecture` + `## Packages` directly)
- `constitution.md`

The architect inherits the parent session's Read tool surface and will fetch these itself. Do not summarize their content in the brief — that double-pays context and risks drift. Pass your DRAFT task set (numbers, titles, depends-on edges, Expects/Produces per task) inline in the brief, since it does not yet exist on disk.

**Sub-questions (always asked):**

1. **Task atomicity boundaries / bundling**: is each task one logical change (1-3 files, 5-30 min, one clear done condition)? Should any mechanical task be bundled into its dependency? Should any task be split?
2. **Dependency ordering & direction**: is the depends-on graph acyclic and correctly directed (types before use, data before domain, core before presentation, independent before dependent, riskiest first)?
3. **Contract-chain integrity**: does every `Produces` feed a downstream `Expects` or a spec AC, and does every `Expects` trace to an upstream `Produces` or existing codebase state? Are contracts stated as semantic identifiers (export / function / interface / field names), never line numbers?
4. **Implementability (intent completeness)**: can the assigned engineer execute each task from its done-condition + `Expects`/`Produces` without guessing a decision the plan did not already make? Flag any task whose intent is underspecified — a missing input the steps assume, an unstated choice between two valid implementations, or a done-condition more than one diff could satisfy. This is an intent-completeness check, NOT a prose-style, grammar, or verbosity judgment: any task that is fully determined by its contracts plus the spec / plan / constitution / docs context the implementer also reads is NOT a finding. Route a flag the same way as an atomicity/ordering/contract revision (revise the draft task before writing it); if the missing piece is a decision `/devforge:plan` should have made rather than a wording gap, escalate to the human.

**Agent assignment is orchestrator-direct** via the inlined Agent Assignment table below — a lookup, not judgment. The architect only VALIDATES the agent assigned to design-decision tasks (tasks that choose interfaces, data shapes, algorithms, or contracts downstream tasks depend on); it does not re-derive the whole assignment.

**Change-induced dead-code allocation.** When `/devforge:plan` declared change-induced dead code (the `### Change-Induced Dead Code (MUST-delete)` sub-block surfaced in Phase 0a.5), each MUST-delete row's removal folds into the OWNING task — the task whose change kills that path — as PART of that task's change (Phase 3's *Change-induced dead-code removal* rule). Normally a decision's dead paths and its killing change land in one task, so all its rows fold there. When the kill-list spans files such that no single owning task can carry it, this architect consult decides the split: assign each dead-code row to the task that owns its killing change. Rows MAY spread across several tasks, but every row must land in exactly one task's `**Dead code removal**:` field — never a dedicated deletion task, and never dropped.

### Task Granularity Rules

- **One task = one logical change** that can be verified independently.
- A task should touch **1-3 files** maximum (exception: a rename/replace across many files is ONE task, not many).
- Each task must have a clear **done condition**.
- Tasks should take **5-30 minutes** to implement (not hours). If a task would take longer, break it into sub-tasks.

### Task Nature Classification (mechanical vs design-decision)

For each task, determine whether it is **design-decision** or **mechanical**:

- **Design-decision**: the task requires choosing interfaces, data shapes, algorithms, orchestration logic, or contracts that downstream tasks depend on. No existing pattern to copy — the implementer makes judgment calls. The architect validates the agent assigned to these (see above).
- **Mechanical**: the task follows an established pattern already present in the codebase (e.g., wrapping a data source with try/catch error mapping, registering dependencies in a DI container, adding a route entry). The implementer copies an existing example and substitutes names — zero design decisions.

**Signals a task is mechanical**: the codebase already has 1+ examples of the exact same pattern; the task's output is fully determined by its inputs; the task body is <30 lines of boilerplate with no conditional logic; the task description reduces to "do what feature X did, but for feature Y".

### Bundle Mechanical Tasks

After classification, check whether any mechanical task should be **bundled into its dependency** rather than standing alone:

- **Bundle when**: the mechanical task is <30 lines, has exactly one dependency, and would be assigned to the same agent as that dependency. Keeping it separate adds an execution wave and an agent launch for trivial work.
- **Keep separate when**: the mechanical task touches files in a different layer than its dependency, has multiple dependents that need its output as a checkpoint, or the combined task would exceed the 1-3 file limit.

When bundling, merge the mechanical task's files, contracts, and done-when conditions into the parent task, and update the dependency graph accordingly.

### Agent Assignment table

Assign exactly ONE agent per task by the file's owning package/stack (see `## Packages` / `PACKAGE_STACKS` in `CLAUDE.md`). A type, interface, domain model, contract, or state store is **not its own layer with its own agent** — it belongs to the stack that owns the file, and that stack's implementer writes it. The architect never appears in this table: it shapes at `/devforge:plan` and only *VALIDATES* the decomposition (above) — it does not write code.

| Files in... | Agent |
|-------------|-------|
| API endpoints, controllers, middleware, services, server-side logic — and the backend stack's domain models, types, interfaces, contracts, and business/state logic | backend-engineer |
| UI components, styles, routes, composables, stores — and the frontend stack's domain models, types, interfaces, and state management (BLoC / Redux / Pinia) | frontend-engineer |
| Mobile screens, navigation, native modules, platform-specific code, app lifecycle — and the mobile stack's domain models, types, and state | mobile-engineer |
| Non-server host / runtime-entrypoint code — Electron main process, desktop-app `main`, CLI entrypoint, Tauri core — i.e. the app's host process, NOT a backend server | the owning package's stack implementer per `## Packages` / `PACKAGE_STACKS` (the app's primary implementer — e.g. the frontend/app engineer that owns the rest of the codebase) — NOT `backend-engineer` by default |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | owning stack engineer (backend/frontend/mobile-engineer, per the file's layer) — `performance-analyst` diagnoses and recommends during `/devforge:review`, it never implements |
| Auth, secrets, input validation, security hardening | owning stack engineer (backend-engineer for server-side auth/secrets/validation; frontend-engineer for client-side) — `security-reviewer` reviews during `/devforge:review`, it never implements |
| Database schemas, migrations, queries, seed data | db-engineer |
| API contract design, OpenAPI specs, endpoint structure | api-designer |
| CI/CD, Docker, deployment config, infrastructure | devops-engineer |
| Data migration scripts, backward compatibility layers | migration-engineer |
| Accessibility, design-system compliance, visual-fidelity work on UI files | owning stack engineer (frontend-engineer / mobile-engineer, per the file's layer) |
| Dedicated test-authoring / coverage-gap task — a standalone task that writes tests for existing or just-built behavior, NOT the inline tests an engineer writes for their own implementation task | qa-engineer |
| Unclear or mixed | split per the rule below — never `architect` |

A mixed or unclear task is a decomposition smell, not a routing problem: split it until each piece maps to exactly one stack's implementer; if a piece genuinely spans stacks (e.g. a backend API plus its frontend consumer), break it into per-stack tasks joined by a dependency edge. If splitting is genuinely impossible, escalate to the human. Never assign `architect` to write code — the architect cannot implement.

Host / runtime-entrypoint code that is non-renderer but also not a backend server (an Electron main process, a desktop-app `main`, a CLI entrypoint, a Tauri core) is NOT a `backend-engineer` task by default — route it via the host / runtime-entrypoint row above to the owning package's stack implementer per `## Packages` / `PACKAGE_STACKS`. For a desktop / Electron / CLI app whose code is one app stack, that is the app's primary implementer (the engineer that owns the rest of the codebase), never backend-by-default.

If the owning stack's implementer is not generated for this project (not all projects generate all agents), split or escalate to the human — never fall back to `architect` (the architect cannot write code). `performance-analyst`, `security-reviewer`, and `design-auditor` are READ-ONLY reviewers — they run during `/devforge:review` (and `/devforge:audit`) on the changed files and are never assigned an implementation task (`design-auditor` runs the `/devforge:review` runtime design-fidelity check when the feature has a design reference + manifest). For a genuinely perf- or security-focused investigation, the diagnosis still routes to the owning stack engineer to implement the fix; the reviewer recommends, the engineer changes the code.

Inline tests stay the per-engineer default — each stack engineer writes the tests for their own implementation task. Create a SEPARATE task assigned to `qa-engineer` (the dedicated test-authoring row above) ONLY when decomposition or the Phase-2 architect consult flags a coverage gap or a test-heavy acceptance criterion; this gives `qa-engineer` a real executor without double-covering every task. A SECOND, mechanical trigger also creates a dedicated `qa-engineer` task: when `/devforge:plan` declared pure-builder targets (the `### Pure-Builder Targets (property-test lane)` sub-block surfaced in Phase 0a.5), Phase 3 MUST create a `qa-engineer` property-test task covering every declared target (see Phase 3's *Property-test tasks* rule), enforced by the Phase 3.5 property-coverage gate. `qa-engineer` is `model_tier: do` — a valid implementer, so the "Never assign `architect` to write code" rule above does not apply: `qa-engineer` is a builder, not the architect. If `qa-engineer` is not generated for this project, the split-or-escalate rule applies as for any other missing implementer, and the Phase 3.5 agent-roster gate catches any task assigned to an uninstalled agent. Distinct responsibilities: `qa-engineer` WRITES tests, while `/devforge:implement`'s per-task scope-aware verify step RUNS them.

**Halt rule:** if you reach Phase 3 without having completed the architect consultation, halt, invoke the architect now, then record its validation provenance in the tasks index Specialist Consultation table (Phase 3) before writing any task file. Task files written without a corresponding Specialist Consultation entry are a hard error.

## PHASE 2.5: Design-fidelity intake gate (CONDITIONAL — fires only when the feature has a design reference)

**This phase runs ONLY when the feature implements against a design reference.** A design reference is a `design/reference.html` file at the workspace root (the single HTML artifact the feature's UI implements against). If no such file exists, this feature is not UI-against-a-reference work — SKIP this entire phase and proceed directly to Phase 3. Non-UI features and UI features with no `design/reference.html` are NOT blocked by this gate.

When a `design/reference.html` DOES exist, this gate authors the feature's design-fidelity **binding** — the built-side wiring that maps the captured design intent to what the feature will build — and HALTS intake if that binding is empty or invalid. The binding names WHERE the feature renders (its `route`) and, per correspondence pair, WHICH reference selector maps to WHICH built element's stable testid. The gate runs at INTAKE (before Phase 3 writes task files), not at verify: an unresolved design contract is escalated to the user BEFORE code is written, never after. The `design_helper` owns the binding's validation; the orchestrator reads the captured intent and composes the `route` and pair values.

**Detect the design reference.** Run a mechanical existence test from the workspace root (cwd) — `test -f design/reference.html` — and branch on its boolean result, not on eyeballing the filesystem. If it is present (`test` is zero), continue to Step 1.

If the file is absent (`test` is non-zero), there is no enforceable reference to gate against, so this feature skips the intake gate either way — but first surface any declared non-file design source. Run the source check (the spec is `<feature_dir>/spec.md`, sibling to where `design-manifest.json` would go):

```bash
.devforge/lib/design_helper check-design-source \
  --spec <feature_dir>/spec.md --workspace-root .
```

The verb's exit code is ALWAYS 0 (this is a non-blocking warning, never a halt) — branch on whether the verb produced output (a WARN), not on its exit code. The verb is SILENT in the common cases and prints a WARN (to stderr, exit 0) only when a non-file design source is declared without an enforceable reference. If the verb produced a WARN, the spec declared a non-file design source (`figma`/`screenshot`, or an `html` target that is not an existing file) with no enforceable `design/reference.html`: copy that output VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then proceed to Phase 3 — the WARN's own text explains the skip and the convert-to-`design/reference.html` remedy, so it replaces the plain "skipping" line in this case. If the verb produced no output, tell the user `"No design/reference.html for this feature; skipping the design-fidelity intake gate."` and proceed to Phase 3 (the common cases: the spec declared `none` or declared nothing; note an `html:` source pointing to an existing non-`design/reference.html` path also produces no output but is a misdeclaration this gate does not catch — the design-fidelity gates enforce only `design/reference.html`).

The PHASE 3.5 `verify-manifest-present` gate is the authoritative backstop for the reference-PRESENT case — it re-derives the `design/reference.html` existence check mechanically — so a wrongly-skipped PHASE 2.5 is caught downstream, never silently lost.

**Step 1 — Read the captured design intent (the anchor).** `/devforge:specify` persisted the feature's design intent to `<feature_dir>/design-anchor.json` — an immutable record of shape `{kind, file, selectors, source_hash}` where `kind` + `file` name the design source and `selectors` names which reference selectors carry the intent. Read this file. Its `selectors` are the candidate anchor-side selectors for the binding's pairs (Step 2). If `design-anchor.json` is absent, or its `selectors` list is empty, that does NOT block this gate — Read `design/reference.html` to identify its primary top-level container selector, then author the container-floor pair directly from that container in Step 2. Only an empty or invalid binding halts intake (Step 3).

**Step 2 — Author the binding.** Compose the built-side binding and write it to `<feature_dir>/design-manifest.json` via Write. The binding maps the captured intent to what the feature will build; it has this shape:

```json
{
  "route": "<where the feature's UI renders in the built app>",
  "pairs": [
    { "anchor_selector": "<a selector from the anchor / reference>", "built_testid": "<the stable testid the engineer will add to the built element>" }
  ]
}
```

- **`route`** (required, non-empty): where the feature's UI renders in the built app — a URL path, screen name, or route identifier. The review-time runtime design-fidelity check navigates here to find the surface to compare; without it there is no place to check.
- **`pairs`** (required, at least one): each pair maps one reference selector to one built element.
  - The **FIRST pair is the mandatory container floor**: the anchor's primary region (its top-level container selector) ↔ the built container's stable testid. This single pair covers the styling every child inherits from the container (the most-omitted, most-dangerous class) plus the container's own box geometry.
  - **Additional pairs are opt-in precision** — add one per anchor `selector` (from Step 1) whose per-element fidelity matters. In practice this is a handful of elements.
  - **`anchor_selector`** MAY be brittle (e.g. a bare class) — it points at the static reference file, which never changes, so its fragility is harmless.
  - **`built_testid`** MUST be a stable testid the engineer adds to the living, refactored code — never a brittle selector, because it points at code that gets refactored.

The Phase-2 architect validation of task boundaries and the design decisions it surfaced inform which elements warrant an opt-in pair — author the pairs in light of that consultation, not independently of it.

**Step 3 — Validate the binding (the HALT point).** Run the validator against the authored binding:

```bash
.devforge/lib/design_helper validate-binding \
  --binding-path <feature_dir>/design-manifest.json
```

The verb emits a `{valid, errors}` JSON object to stdout and, on failure, one error line per problem to stderr. It validates BOTH the structural shape (a well-formed `route` plus a `pairs` array whose entries carry `anchor_selector` / `built_testid`) AND completeness — `route` non-empty and at least one fully-specified pair (both `anchor_selector` and `built_testid` non-empty) present; an empty binding is never valid by omission. Because Step 2 authors the JSON directly with no helper skeleton, a structurally-malformed file is caught at THIS gate, not shipped downstream.

- **Exit 0** — the binding is valid (non-empty `route` + at least one fully-specified pair). The intake gate passes; proceed to Phase 3.
- **Exit 1** — validation errors. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Do NOT write any task file. The binding is empty or incomplete — a missing `route`, zero pairs, or a pair missing its `anchor_selector` / `built_testid`. Re-enter Step 2, supply the missing value(s), and re-run Step 3. If a required value genuinely cannot be determined from the spec, plan, anchor, and reference — for example the feature's render `route` is unknown — HALT and escalate to the user: end the turn with the copied errors and a request for the missing value; the user's reply opens the next turn, after which re-author (Step 2) and re-validate (Step 3). Intake does not proceed to Phase 3 until the binding validates.
- **Exit 2** — the binding file could not be read or parsed (a Step 2 write problem, or the path is missing / not a file). Copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

The validated `<feature_dir>/design-manifest.json` PERSISTS as the design-fidelity CONTRACT for the feature — the built-side binding the two downstream design-fidelity gates read. It declares the feature's render `route` and, per pair, which reference selector the built element (identified by its stable testid) must match. The binding is consumed by two enforcement concerns: `/devforge:implement`'s per-task forcing-functions gate runs the static design-token provenance check `verify-design-tokens` on the feature's styling (no hardcoded color literals, no `var(--x, <literal>)` fallbacks, undefined-token-fails-loud), and `/devforge:review`'s PHASE 2.5 dispatches `design-auditor` for the review-time runtime-conformance check (the built UI's rendered values and geometry against the design intent). This phase only PRODUCES that binding; it does not itself run either enforcement.

## PHASE 3: Write tasks

For each task in the validated decomposition, render its skeleton via the helper, then fill the values and write the file. The helper owns the task-file structure (per `.devforge/storage-rules.md` §Task File Format); you compose the values.

```bash
.devforge/lib/breakdown_helper render-task-file --number NNN --title "<imperative title>" --feature <feature-dir-name>
```

`<feature-dir-name>` is the last segment of `<feature_dir>` — the directory's own name, not its path. `render-task-file` stamps that value into the task file's `**Feature**:` field and joins no path onto it, so passing `<feature_dir>` there would put the whole path into that field.

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then fill its placeholders and write the result to `<feature_dir>/tasks/NNN-<title>.md` via Write. Fill these per task:

- **Header fields**: Agent (from the Agent Assignment table), Depends on, Blocks, Spec criteria (`AC-N`), Review checkpoint (Yes/No — see below), Context docs (see below), plus Property targets on dedicated property-test tasks only (see the Property-test tasks subsection below), and Dead code removal on the owning task of any `/devforge:plan`-declared change-induced dead code (see the Change-induced dead-code removal subsection below).
- **Files table**, **Description**, **Change Details** — from the Phase 1 file analysis, plus the behavior-changing / behavior-preserving surface partition on a mixed task (see the Two-hats partition subsection below), and the `Regression net:` line on any task carrying a behavior-preserving surface with no covering test (see the Regression-net declaration subsection below).
- **Contracts** (`Expects` / `Produces`) — per the Contract Generation Rules below; on a mixed task each behavior-preserving surface also carries its preservation postcondition in `Produces` (see the Two-hats partition subsection below).
- **Done When** — task-specific testable conditions; the helper-emitted skeleton already carries the standing tsc/lint/tests/no-secrets/no-debug conditions.
- **Completion Notes** — leave the helper-emitted Completion Notes skeleton empty — it is the read contract that the `/devforge:implement` consumer will fill on completion.

### Property-test tasks (pure-builder targets)

When Phase 0a.5's `read-plan-handoff` output carried a non-empty `### Pure-Builder Targets (property-test lane)` sub-block, `/devforge:plan` identified one or more pure-builder targets — deterministic, no-I/O construction (filters, queries, mappers, formatters) — that warrant property-based testing. For these, Phase 3 MUST create at least one DEDICATED property-test task assigned `qa-engineer` (the dedicated test-authoring row in the Agent Assignment table) that covers EVERY listed target. This is IN ADDITION to any `qa-engineer` task created for a Phase-2 coverage gap or a test-heavy acceptance criterion. One task MAY cover all targets, or you MAY split by package — but every listed target must appear in some property-test task's `**Property targets**:` line. The Phase 3.5 property-coverage gate enforces this mechanically. When authoring each property-test task, copy the target's `Why pure` cell text from the plan's `### Pure-Builder Targets` table verbatim into the task's Description or Change Details — the task file is the self-contained artifact `qa-engineer` reads at `/devforge:implement`, and the invariant-derivation instruction below anchors on that rationale being present in the task itself.

Render each property-test task with the `--property-targets` flag so the skeleton carries the coverage line:

```bash
.devforge/lib/breakdown_helper render-task-file --number NNN --title "<imperative title>" --feature <feature-dir-name> --property-targets "<comma-separated target names>"
```

The flag emits a `**Property targets**: <list>` line after `**Context docs**:`; its comma-separated names must exactly match the target names from the sub-block, since the property-coverage gate matches on exact name. Ordinary (non-property) tasks omit the flag and carry no such line — output is otherwise identical to the base invocation above.

The property-test task's Description and Change Details must instruct the implementing `qa-engineer` to:

- **Pick the property-testing library by the target file's package stack** — longest-path-prefix match against the `## Packages` table / `PACKAGE_STACKS`: **fast-check** for TypeScript / JavaScript (runs under Vitest or Jest), **hypothesis** for Python / pytest.
- **Derive the invariant(s)** for each target from the spec's acceptance criteria and the plan's "Why pure" rationale for that target; run **≥100 iterations**; the arbitraries MUST include special characters (regex metacharacters such as `(`, `[`, `+`), unicode, and empty / boundary values — the defect class example-based tests structurally miss.
- **Seed policy** — pin a fixed seed in the test setup for reproducibility, AND on failure record the failing seed / counterexample in the test output so the case can be replayed.
- **Unsupported stack** (the target file's language has no fast-check / hypothesis equivalent): the task STILL exists and STILL carries its `**Property targets**:` line, but its body instructs writing adversarial-input EXAMPLE tests for the same invariants (special characters, unicode, boundary values) and recording an explicit honest-skip note in the task's Completion Notes — `Property lib: none available for <stack> — example-based adversarial tests substituted`. Never a silent skip.

### Change-induced dead-code removal (fold into the owning task)

When Phase 0a.5 surfaced a `### Change-Induced Dead Code (MUST-delete)` sub-block, `/devforge:plan`'s sub-question 9 named one or more code paths a Key Design Decision renders unreachable — MUST-delete obligations, dead by the constitution's §3.5 (No dead code). Each row's removal folds INTO THE OWNING TASK: the task whose change introduces the dominating condition (or the removal) that kills the path. That owning task deletes the dead path as PART of its change. NEVER create a separate, dedicated deletion task for it: a dedicated deletion task can be dropped, deferred, or reordered after the task that kills the path lands, which re-opens exactly the orphaned-dead-code window this lane exists to close — folding the deletion into the killing task makes the two atomic.

When a decision's dead paths and its killing change land in different tasks such that no single owning task can carry the whole kill-list, the Phase 2 architect consult allocates each row to the task that owns its killing change (see Phase 2's *Change-induced dead-code allocation* note); the rows may spread across several tasks, but every row lands in exactly one task's `**Dead code removal**:` field.

Render each owning task with the `--dead-code-removal` flag so its file carries the obligation:

```bash
.devforge/lib/breakdown_helper render-task-file --number NNN --title "<imperative title>" --feature <feature-dir-name> --dead-code-removal "<anchor-token-1>; <anchor-token-2>"
```

The flag emits a `**Dead code removal**: <text>` line immediately after the `**Property targets**:` line when that line is present, else immediately after `**Context docs**:`. Its value is a SEMICOLON-separated list of the folded rows' literal anchor tokens — each token copied verbatim (character-for-character) from that row's Anchor token cell, `; `-separated. It is NOT free prose and NOT comma-separated: anchor tokens are literal code fragments that commonly contain commas (e.g. multi-arg call-site literals), so the separator is a semicolon, and a token must not itself contain one. `verify-dead-code-coverage` (the Phase 3.5 gate) matches each declared row's anchor token against this field by splitting on `;`, stripping, and exact-match — so a token that does not appear verbatim reads as uncovered. Name the killed file(s) in the task's Files table and Change Details, not in this field. Tasks that kill no declared path omit the flag and carry no such line — output is otherwise identical to the base invocation above.

Contrast with the property-test lane above: that lane creates a DEDICATED `qa-engineer` task because its rationale is coverage (a test author is a distinct unit of work). Dead-code removal is the opposite — its rationale is atomicity, so it is never its own task; it rides the task that makes the code dead.

/devforge:verify confirms each carried row's anchor token is absent from the post-change code (plan 71 Phase 4).

### Two-hats partition (mixed behavior-change + restructuring tasks)

A task is MIXED when both conditions hold, and both are checkable against the task file you just wrote: its Files table has at least one row whose `Action` is `Modify` and whose change touches an existing function the task does not delete, AND its `**Spec criteria**:` line names at least one acceptance criterion whose observable behavior this task changes. A mixed task MUST partition the functions and files it touches into **behavior-changing** surfaces (the observable result is deliberately different afterwards) and **behavior-preserving** surfaces (code moved, extracted, renamed, or re-shaped, observable result identical) — the constitution's Two-hats rule. A task that only restructures existing code, and a task that only adds or changes behavior, wears a single hat: it gets no partition, and you never fill one in trivially to satisfy the shape.

The partition lands in the task's `## Change Details` section, on the entries already written there: label each `- In <path>:` entry — and, where one file holds both kinds of change, each named function under it — behavior-changing or behavior-preserving. Each behavior-preserving surface additionally carries a preservation contract in `### Produces` (see the Contract Generation Rules below): a postcondition asserting that surface's observable result is unchanged, written against a semantic identifier like every other contract item — e.g. "`get cartTotals()` in `CartBLoC.ts` returns the same value as before this task". A behavior-preserving label with no matching `Produces` item declares nothing anyone can check.

Both halves ride sections the orchestrator already fills, and that placement is deliberate: the partition is per-surface prose no fixed header field could hold, and the preservation postcondition belongs in `Produces` because `Produces` is already the channel the `/devforge:implement` consumer verifies by reading the source. The labels themselves are what `code-reviewer`'s Two-hats partition check reads a mixed task's diff against. Render mixed tasks with the base `render-task-file` invocation — this lane adds NO flag and NO header line, unlike the property-test and dead-code lanes above.

Produce the partition HERE, at decomposition, rather than leaving it to be reconstructed at review: Phase 1's file analysis is where it is already known which touched files this change only restructures, and once the task has become one diff that knowledge is gone — a reviewer would have to re-derive which hunks were meant to preserve behavior from the change itself, which is the one thing a diff cannot show.

### Regression-net declaration (restructuring tasks over untested code)

A behavior-preserving surface is a function or file the task moves, extracts, renames, or re-shapes while the observable result stays identical. A task that only restructures carries such surfaces throughout; a mixed task carries them as the preserving half of the Two-hats partition above. Restructuring one of them is safe only when something would fail if the restructuring went wrong. The constitution's Two-hats rule already requires every behavior-preserving surface to carry a preservation postcondition — the partition subsection above lands that postcondition in `Produces` — and over existing code that no test covers, nothing ever runs that could make it come out false. The surface is then restructured with its preservation postcondition unwatched, and the task can be decomposed, implemented, and reviewed without anyone naming that. The regression net at stake here is whatever tests would go red if this restructuring broke that surface — distinct from `/devforge:verify`'s full-suite regression gate, which can only go red on a test that already exists and therefore cannot break at all over a surface no test covers.

Every task carrying a behavior-preserving surface with no covering test MUST declare its regression net in that task's `## Change Details` section, on a line whose fixed literal prefix is `Regression net:`. The obligation is to DECLARE. Only the content of that line varies, and it varies as a report of what this decomposition did — never as a pick between a harder duty and a cheaper one:

- `Regression net: precedes — task NNN` — a task that writes the covering test sits upstream of this one, so the net exists and passes before the restructuring starts. `NNN` is that task's number, and the edge must be real: this task's `**Depends on**:` names it. A net-writing task created here is the Agent Assignment table's dedicated test-authoring row — a `qa-engineer` task, created under the coverage-gap trigger that row's rule already names, not a new one.
- `Regression net: window accepted — <reason>` — no task writes that net first, and `<reason>` names the exposure this decomposition accepts and why it accepts it (for example: the surface is a pure rename the type checker covers end to end; the stack has no test harness the net could be written against yet).

NET FIRST is the default, and the second form is how an author records a departure from it (Phase 1's *Restructuring over untested code* note). A task that meets this rule's trigger and carries no `Regression net:` line at all has not taken the cheaper form — it has skipped the rule.

Two bounds on this rule, both load-bearing. NOTHING CHECKS the declaration: there is no Phase 3.5 gate for it, no `verify-*` verb, and no helper flag. It is an authoring duty whose whole value is that its ABSENCE IS VISIBLE — a task file that restructures untested code and says nothing about a regression net reads wrong on its face to the human who opens it. And the TRIGGER RESTS ON A BELIEF, not on a measurement: "no covering test" is answered from the Phase 1 file analysis, which reads the files and runs no coverage tool, so a wrong belief about what is covered produces a wrong trigger silently. Where the reading leaves it uncertain, declare — an accepted window over a surface that turns out to have had a net costs one sentence, and an undeclared exposure costs exactly the visibility this rule exists to create.

The line rides `## Change Details` because that section is free-form prose the orchestrator already fills, and the fixed `Regression net:` prefix is what makes one prose line findable by a human grepping a feature's tasks for accepted windows. Render these tasks with the base `render-task-file` invocation — this lane adds NO flag and NO header field, unlike the property-test and dead-code lanes above. `Regression net:` is prose with a fixed opening, NOT a `**Bold field**:` line: the helper owns the task-file structure, nothing emits this line for you, and promoting it to a header field would be a change to that structure rather than to this rule.

Declare it HERE, at decomposition, rather than leaving it to implementation: decomposition is where the ordering is still free — a net-writing task can still be inserted upstream and the dependency edges redrawn. Once the restructuring task is being implemented, that ordering is settled, and a declaration written then records an exposure at the point where nobody can still order a net in front of it.

### E2E scenario tasks (declared full-stack flows)

When Phase 0a.5 surfaced a `### E2E Scenarios (full-stack flows)` sub-block, `/devforge:plan`'s sub-question 12 named one or more acceptance criteria that only a full-stack run can verify, each with the minimal user-visible scenario that exercises it. For these, Phase 3 MUST create at least one DEDICATED task assigned `qa-engineer` (the dedicated test-authoring row in the Agent Assignment table) that covers EVERY declared scenario. This needs no new routing rule and no new table row: that row's separate-task trigger already names a test-heavy acceptance criterion, and an acceptance criterion only a full-stack run can verify is one. It is IN ADDITION to any `qa-engineer` task the property-test lane requires, and to any created for a Phase-2 coverage gap. One task MAY cover all scenarios, or you MAY split them across several — but every row of the plan's table must be carried by some e2e task. When the plan carries no such table, this lane does nothing: no e2e task, and no line anywhere recording that there were no scenarios.

Carry each scenario into its task's `## Change Details`: the scenario name, the acceptance criteria it verifies, its ordered flow steps, and the state its run needs before the first step — copied from the plan's `### E2E Scenarios` table, because the task file is the self-contained artifact `qa-engineer` reads at `/devforge:implement`. Render these tasks with the base `render-task-file` invocation — this lane adds NO flag and NO header field, unlike the property-test and dead-code lanes above.

The task body carries these two rules, because the agent that writes the tests reads the task file and not this spec:

- **Framework**: Write the e2e tests in the framework the project's e2e configuration names. When that configuration is empty, the task is BLOCKED and says so — name the missing configuration and stop. Never choose a framework the project has not adopted.
- **File placement**: Put the e2e spec files in a dedicated e2e directory that the package's ordinary test command does not match.

The placement rule is not cosmetic. `/devforge:implement`'s scope-aware verification matches every file a task touched to its owning package and runs that package's own test command, so an e2e spec the package's unit-test glob can reach is run by the wrong runner at the next task and spends that task's self-repair budget on a failure that is not a defect.

Two bounds on this lane, both load-bearing. NOTHING CHECKS the scenario coverage: there is no Phase 3.5 gate for this table, no `verify-*` verb, and no task header field, so a plan declaring three scenarios beside a task set covering none produces no error — the claim is that the absence is VISIBLE in the task set, never that it is blocked. And NOTHING CHECKS the placement either: it is authoring guidance with no gate behind it, so an e2e spec written beside the unit specs produces a confusing red run at the next task rather than an error.

### Contract Generation Rules

Each task's `## Contracts` section has `### Expects` (preconditions) and `### Produces` (postconditions):

- **Expects**: what must be true in the codebase before this task runs correctly. For the first task in a chain, these describe existing state. For downstream tasks, these match an upstream task's `Produces`.
- **Produces**: what must be true after this task completes. The `/devforge:implement` consumer verifies these by reading the source.

Rules:

- 2-5 items per section. Keep them concrete and code-verifiable by reading the source file.
- Reference **semantic identifiers** (function names, export names, interface names, field names) — never line numbers. Line numbers shift as earlier tasks modify files.
- Contracts must reference **literal strings that appear in source code** — export names, function names, interface names, field names, class names. Reference the literal declaration pattern (e.g., "`get cartTotals()` appears in `CartBLoC.ts`"), not abstract concepts ("has a getter").
- Bad contracts: "Cart totals work correctly" (not verifiable); "Line 45 returns the right value" (line numbers shift); "Performance is acceptable" (not code-verifiable).

### Doc Reference Rules

Determine if the agent needs documentation context beyond the task description:

- **Integration tasks** (wiring into an existing feature): reference the neighboring feature's doc.
- **Tasks extending an existing pattern**: reference `docs/architecture.md` if the pattern is documented there.
- **API tasks touching existing endpoints**: reference the relevant `docs/` API file.
- **Self-contained tasks** (new types, isolated logic): no doc reference — the task description is sufficient.
- **Maximum 2 doc references per task** — if more context is needed, include it directly in the task description.

### Review Checkpoint Placement

Set `**Review checkpoint**: Yes` or `No` per task. Auto-place `Yes` at:

1. **Convergence points** — the task depends on 2+ other tasks.
2. **Layer boundary crossings** — the first presentation-layer task after domain/data-layer tasks.
3. **High-risk tasks** — any task rated High in the risk assessment.

All other tasks get `No`. The user can add or remove checkpoints during the Phase 4 approval gate.

### Tasks index

After all task files are written, render the index skeleton via the helper:

```bash
.devforge/lib/breakdown_helper render-tasks-index --feature <feature-dir-name> --spec <spec-path> --plan <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then fill its sections and write the result to `<feature_dir>/tasks/README.md` via Write. Fill: the dependency-graph fence, the index table (one row per task), the `## Additions to Spec` section (files discovered in Phase 1 not in the plan, or "None"), the risk assessment, and the review checkpoints table.

### Specialist Consultation provenance

Render the consultation provenance skeleton via the helper and fill its rows — one row per specialist consulted (Verdict from the enum `accepted` / `modified` / `rejected` / `no-response`; Cites required; the `(none)` row stays when no specialist beyond the mandatory architect was consulted):

```bash
.devforge/lib/breakdown_helper render-consultation-block
```

The helper takes no arguments and owns the column names and verdict enum. Copy its stdout into the tasks index (`README.md`) and fill the rows; this table is the single source of truth for the Phase 2 consultation provenance.

## PHASE 3.5: Integrity gates

Six forcing-functions walk the task set mechanically. Contract-chain and AC-coverage findings MAY be carried to Phase 4 as a documented deferral — explicitly recorded in the index `## Risk Assessment` with a one-line justification. The agent-roster gate has NO such bypass: it is a HARD gate, and a roster violation must be re-routed before Phase 4 (a task literally cannot be implemented by an agent that is not installed). The design-manifest gate likewise has NO bypass: it is a HARD gate, and a reference-present feature whose `design-manifest.json` is absent or invalid must return to PHASE 2.5 to PRODUCE/complete the manifest before Phase 4 (without it the two downstream design-fidelity gates are silently void). The property-coverage gate likewise has NO bypass: it is a HARD gate, and a pure-builder target `/devforge:plan` declared with no covering property-test task is an ORPHANED PROPERTY — the property-test lane must not silently evaporate — so the missing task must be created before Phase 4. The dead-code-coverage gate likewise has NO bypass: it is a HARD gate, and a change-induced dead-code row `/devforge:plan` declared that is folded into no task — or into more than one — is UN-OWNED change-induced dead code (the guard-and-leave failure this lane exists to close), so every declared row must be folded into exactly one owning task before Phase 4.

**Contract chain** — orphan `Produces` / unsatisfied `Expects`:

```bash
.devforge/lib/breakdown_helper verify-contract-chain <tasks-dir>
```

- Exit 0 (`contract-chain: ok (N tasks, P produces, E expects)`) → the chain is intact. No action.
- Exit 2 with a `## Contract chain findings` block on stdout → advisory findings (orphan Produces or unsatisfied Expects). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). For each finding, either revise the tasks (add the missing consumer/producer task, or fix the dependency edge) and re-run, or record the finding in the index `## Risk Assessment` with a one-line justification.
- Exit 2 with `no task files...` on stderr → the tasks directory is missing or empty. Copy the helper's stderr VERBATIM into a fenced code block; this indicates Phase 3 did not write the task files — return to Phase 3.

**AC coverage** — every spec acceptance criterion addressed by ≥1 task:

```bash
.devforge/lib/breakdown_helper verify-ac-coverage <tasks-dir> <spec-path>
```

- Exit 0 (`ac-coverage: ok (...)` or `ac-coverage: no-acs (...)`) → every AC is covered, or the spec has no ACs. No action.
- Exit 2 with a `## Uncovered acceptance criteria` block on stdout → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Every uncovered AC must get a covering task (return to Phase 3 to add it) or be explicitly flagged in the index `## Risk Assessment` as having no implementation path.
- Exit 2 on stderr → the tasks directory is missing or the spec is unreadable. Copy the helper's stderr VERBATIM into a fenced code block and resolve the named problem before re-running.

**Agent roster** — every assigned agent is actually installed in this project's `.claude/agents/` roster:

```bash
.devforge/lib/breakdown_helper verify-agent-roster <tasks-dir>
```

Pass only the tasks directory — do NOT pass `--agents-dir`. The verb defaults to `.claude/agents` relative to the working directory, which is correct in both standalone and wrapper mode: the helper is invoked via the relative path `.devforge/lib/breakdown_helper`, so the working directory is always the install root, where `.claude/` lives.

- Exit 0 (`agent-roster: ok (N tasks, M agents installed)`) → every assigned agent is installed. No action.
- Exit 2 with a `## Agent roster findings` block on stdout → one or more tasks assign an agent that is NOT installed for this project (the block lists each offending task filename and its uninstalled agent name, plus an `Available agents:` line). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). For each offender, RE-ROUTE the task to an installed agent that owns the file's stack — re-enter Phase 3, consult the Agent Assignment table, and apply its split-or-escalate rule — then re-run this gate; NEVER fall back to `architect` (it cannot write code). This is a HARD gate: do not proceed to Phase 4 with an unresolved roster offender.
- Exit 2 with `no agent roster found...` on stderr → `.claude/agents/` is missing or has no agent files (a broken install). Copy the helper's stderr VERBATIM into a fenced code block; this is an install problem to resolve before breakdown can assign agents.
- Exit 2 with `no task files...` on stderr → the tasks directory is missing or empty (Phase 3 did not write the task files). Copy the helper's stderr VERBATIM into a fenced code block; return to Phase 3.

**Design manifest** — a reference-present feature has a present-and-valid `design-manifest.json` (the PHASE 2.5 binding the two downstream design-fidelity gates depend on):

```bash
.devforge/lib/breakdown_helper verify-manifest-present <tasks-dir>
```

Pass only the tasks directory — do NOT pass `--scope-only`, `--reference-path`, or `--manifest-path` (those flags exist for testing and an alternate scope-check mode; `--scope-only` in particular changes the exit-code semantics). The verb defaults the workspace root to the working directory (cwd), the reference to `design/reference.html`, and the manifest to `<feature_dir>/design-manifest.json` (deriving the feature dir as the parent of the tasks dir), which are correct for Phase 3.5 in both standalone and wrapper mode: the helper is invoked via the relative path `.devforge/lib/breakdown_helper`, so the working directory is always the install root, where `.claude/` and `design/` live.

- Exit 0 (`design-manifest: skip (...)` or `design-manifest: ok (...)`) → pass; no action. `skip` = this is not a design-reference feature (no `design/reference.html`); `ok` = the manifest is present and valid.
- Exit 2 with a `## Design manifest findings` block on stdout → a HARD failure: the feature has a `design/reference.html` but its `design-manifest.json` is absent or invalid (an empty or incomplete binding — a missing `route`, or a pair missing its `anchor_selector` / `built_testid`). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Re-enter PHASE 2.5 to author/complete and re-validate the binding, then re-run THIS gate. This is a HARD gate with NO `## Risk Assessment` deferral/bypass: do not proceed to Phase 4 with an unresolved manifest violation.
- Exit 2 with `breakdown_helper: tasks directory not found: ...` on stderr → copy the helper's stderr VERBATIM into a fenced code block; the tasks directory is missing (Phase 3 did not write the task files) — return to Phase 3.

**Property coverage** — every pure-builder target `/devforge:plan` declared is covered by a dedicated property-test task:

```bash
.devforge/lib/breakdown_helper verify-property-coverage <tasks-dir>
```

Pass only the tasks directory — do NOT pass `--plan-handoff` (that flag exists for testing). The verb defaults the plan-handoff to `<tasks-dir>/../plan-handoff.json` (the sibling of the `tasks/` directory, next to `plan.md`), which is correct for Phase 3.5. A task covers a declared target when its `**Property targets**:` line names that target (comma-separated, exact-name match).

- Exit 0 (`property-coverage: skip (no declared pure-builder targets)`) → `/devforge:plan` declared no pure-builder targets (the handoff exists but the key is absent or the list is empty); this is not a property-lane feature. No action.
- Exit 0 (`property-coverage: skip (no plan-handoff.json and no pure-builder targets declared in plan.md)`) → there is no sibling `plan-handoff.json` AND `plan.md` declares no pure-builder targets (no `### Pure-Builder Targets` section, or the section holds only placeholder rows — the same declaration criterion the producer uses) — the feature never declared targets (the PHASE 0a.5 no-handoff path), so there is nothing to verify. No action.
- Exit 0 (`property-coverage: ok (N targets, M covering tasks)`) → every declared target is covered by a property-test task. No action.
- Exit 2 with a `## Property coverage findings` block on stdout → a HARD failure: one or more declared pure-builder targets have no covering property-test task. The block lists one line per uncovered target — `- target '<t>' (<file>): no property-test task covers it` — plus an `Available remedy` hint line. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Return to Phase 3 and create or extend a dedicated `qa-engineer` property-test task whose `**Property targets**:` line names every uncovered target, then re-run THIS gate. This is a HARD gate with NO `## Risk Assessment` deferral/bypass: a `/devforge:plan`-declared pure-builder target with no covering property-test task is an ORPHANED PROPERTY — do not proceed to Phase 4 until every target is covered.
- Exit 2 with `plan-handoff.json not found/unreadable ... plan.md declares pure-builder targets; run plan_helper finalize-handoff ...` on stderr → fail-closed: `plan.md`'s `### Pure-Builder Targets` section declares ≥1 real (non-placeholder) target but the sibling `plan-handoff.json` is missing or malformed, so the declared targets cannot be verified (declared-but-unverifiable must not silently skip — that is the evaporation this gate exists to prevent). Copy the helper's stderr VERBATIM into a fenced code block, then run `.devforge/lib/plan_helper finalize-handoff <plan-path>` to produce the handoff and re-run THIS gate.
- Exit 2 with `no task files found ...` on stderr → the tasks directory is missing or empty (Phase 3 did not write the task files). Copy the helper's stderr VERBATIM into a fenced code block; return to Phase 3.

**Dead-code coverage** — every change-induced dead-code row `/devforge:plan` declared is folded into exactly one owning task:

```bash
.devforge/lib/breakdown_helper verify-dead-code-coverage <tasks-dir>
```

Pass only the tasks directory — do NOT pass `--plan-handoff` (that flag exists for testing). The verb defaults the plan-handoff to `<tasks-dir>/../plan-handoff.json` (the sibling of the `tasks/` directory, next to `plan.md`), which is correct for Phase 3.5. A task covers a declared row when its `**Dead code removal**:` field names that row's anchor token (semicolon-separated list of literal anchor tokens, exact-match); D7 requires EXACTLY ONE owning task — a row named in 2+ tasks' fields is as much a violation as a row named in none.

- Exit 0 (`dead-code-coverage: skip (no declared dead-code rows)`) → `/devforge:plan` declared no change-induced dead code (the handoff exists but `breakdown_seeds.dead_code_rows` is absent or empty); this is not a dead-code-lane feature. No action.
- Exit 0 (`dead-code-coverage: skip (no plan-handoff.json and no change-induced dead code declared in plan.md)`) → there is no sibling `plan-handoff.json` AND `plan.md` declares no dead-code rows (no `### Change-Induced Dead Code` section, or the section holds only placeholder rows — the same declaration criterion the producer uses) — the feature never declared dead code (the PHASE 0a.5 no-handoff path), so there is nothing to verify. No action.
- Exit 0 (`dead-code-coverage: ok (N rows, M covering tasks)`) → every declared row is folded into exactly one owning task. No action.
- Exit 2 with a `## Dead-code coverage findings` block on stdout → a HARD failure: one or more declared dead-code rows are UNCOVERED (`- anchor '<t>' (<file>): no task's '**Dead code removal**:' field covers it`) or DUPLICATED (`- anchor '<t>' (<file>): claimed by N tasks (...) -- must be folded into exactly ONE owning task`). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Return to Phase 3 and fold each uncovered anchor into the `**Dead code removal**:` field of the single task that owns its killing change — and for a duplicated anchor, remove it from every field but that one owning task's — then re-run THIS gate. This is a HARD gate with NO `## Risk Assessment` deferral/bypass: a `/devforge:plan`-declared dead-code row with no owning task (or more than one) leaves change-induced dead code un-owned — do not proceed to Phase 4 until every declared row is folded into exactly one task.
- Exit 2 with `plan-handoff.json not found/unreadable ... plan.md declares change-induced dead code; run plan_helper finalize-handoff ...` on stderr → fail-closed: `plan.md`'s `### Change-Induced Dead Code` section declares ≥1 real (non-placeholder) row but the sibling `plan-handoff.json` is missing or malformed, so the declared rows cannot be verified (declared-but-unverifiable must not silently skip — the same guard-and-leave evaporation this gate exists to prevent). Copy the helper's stderr VERBATIM into a fenced code block, then run `.devforge/lib/plan_helper finalize-handoff <plan-path>` to produce the handoff and re-run THIS gate.
- Exit 2 with `no task files found ...` on stderr → the tasks directory is missing or empty (Phase 3 did not write the task files). Copy the helper's stderr VERBATIM into a fenced code block; return to Phase 3.

## PHASE 4: User approval (HARD GATE)

**Mode-dependent execution path** (mirrors `/devforge:plan` Phase 3):

- **If auto mode is active** (detect via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously): do not pause for clarifying questions during decomposition. Apply the model's recommended defaults to any boundary the plan left open. The user reviews the breakdown at the approval gate below.
- **If auto mode is NOT active** (interactive mode, default): if the decomposition surfaces decision points (e.g., whether to split or bundle a borderline task), the architect consultation in Phase 2 is the place to resolve them; present the resolved breakdown here.
- **When uncertain about mode**: prefer pausing (interactive default). Asking and waiting is reversible; proceeding without input is not.

**HARD GATE**: the breakdown MUST be approved before `/devforge:implement` can run.

Present a summary. This block is LLM-authored (breakdown state lives on disk in the task files and index, not in a state JSON):

"I've broken down the plan into **[N] tasks** at `<feature_dir>/tasks/`.

**Dependency chain**: [simplified graph]
**Riskiest tasks**: [list High-risk tasks and why]
**Review checkpoints**: [count] (before tasks [list])
**Contract chain**: [ok | N findings recorded in Risk Assessment]
**AC coverage**: [all covered | N flagged in Risk Assessment]
**Agent roster**: all agents installed
**Design fidelity**: binding present-and-valid
**Property coverage**: all pure-builder targets covered
**Dead code removal**: [N] declared path(s) folded into owning task(s)"

The `**Dead code removal**:` line is CONDITIONAL — include it ONLY when the plan declared ≥1 `### Change-Induced Dead Code` row (i.e. the PHASE 3.5 dead-code-coverage gate returned `ok`, not `skip`). When none were declared, OMIT the line entirely.

The `**Design fidelity**:` line is CONDITIONAL — include it ONLY when this feature has a `design/reference.html` (i.e. the PHASE 3.5 design-manifest gate ran against a present reference and passed). For a non-UI feature with no `design/reference.html`, OMIT the line entirely — do not emit a "not a design feature" line. Unlike the always-present `**Agent roster**` line, this line is reference-present-gated.

The `**Property coverage**:` line is likewise CONDITIONAL — include it ONLY when `/devforge:plan` declared pure-builder targets (i.e. the PHASE 3.5 property-coverage gate returned `ok`, not `skip`). When there are no pure-builder targets, OMIT the line entirely.

Then ask via `AskUserQuestion`:

- Question: `"Approve this breakdown?"` — single-line text.
- Options: `["approve", "request-changes", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`approve`** → proceed to Phase 5 (finalize).
- **`request-changes`** → in the next turn, ask the user which task or aspect to revise. Re-enter the relevant phase (Phase 1 file analysis / Phase 2 decomposition / Phase 2.5 design-fidelity intake / Phase 3 task writing / Phase 3.5 gates) as needed; re-render the affected task files and index via Write or Edit; re-run the Phase 3.5 gates; re-present the summary above and re-issue this approval prompt. The state lives in the rendered files on disk; this loop mutates them in place.
- **`cancel`** → tell the user `"/devforge:breakdown cancelled. Task drafts preserved at <feature_dir>/tasks/."` and end the turn.

## PHASE 5: Finalize

On `approve`, first write the structured breakdown→implement handoff via the helper. The `<plan-path>` for the call below is the resolved path to the approved `plan.md`.

```bash
.devforge/lib/breakdown_helper finalize-handoff <plan-path>
```

The helper parses `<feature_dir>/tasks/*.md` + the tasks `README.md` and atomic-writes `<feature_dir>/breakdown-handoff.json` (a structured handoff carrying the per-task machine contract — agent, depends_on, touched_files, expects, produces, ac_addressed, review_checkpoint — plus provenance to the sibling `plan-handoff.json`). Handle the exit code:

- Exit 0 → the helper wrote `<feature_dir>/breakdown-handoff.json` and printed its path on stdout. Surface the written path to the user in one line, e.g. `"Structured breakdown handoff written: <path>."` If STDERR also carries a `finalize-handoff: WARN:` line, the dead-code passthrough hit a problem in the sibling `plan-handoff.json` (unreadable sibling or malformed rows) — a NON-FATAL condition. Relay that WARN line to the user VERBATIM so exactly what was affected is visible, then continue.
- Non-zero exit → the helper could not write or validate the handoff. `finalize-handoff` runs the roster check AND the design-manifest assertion AND the property-coverage check (when a sibling `plan-handoff.json` declares pure-builder targets) AND two change-induced-dead-code chokepoints — a declared-but-unsubstantiated check (when `plan.md` declares dead-code rows the sibling handoff fails to carry) and a dead-code-coverage check (when the sibling declares dead-code rows but a declared row is folded into no task or into 2+ tasks) — internally as backstops, so capture BOTH stdout and stderr and branch on their content (the design-manifest, property-coverage, and dead-code-coverage backstops surface as `## Design manifest findings` / `## Property coverage findings` / `## Dead-code coverage findings` blocks on stdout; the declared-but-unsubstantiated dead-code chokepoint is the exception — it surfaces on STDERR, like the `no agent roster found` case):
  - If STDOUT contains a `## Agent roster findings` block → this is a HARD failure, NOT best-effort: one or more tasks assign an uninstalled agent. Copy that stdout block VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and return to Phase 3.5 to re-route the offending task per its gate; do NOT continue to the `render-implement-handoff` block. (In normal flow the Phase 3.5 roster gate already caught this, so this stdout-block path should rarely fire.)
  - Else if STDOUT contains a `## Design manifest findings` block → this is a HARD failure, NOT best-effort: the feature has a `design/reference.html` but its `design-manifest.json` is absent or invalid. Copy that stdout block VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and return to PHASE 2.5 to produce/complete the manifest before re-running; do NOT continue to the `render-implement-handoff` block. (In normal flow the Phase 3.5 design-manifest gate already caught this, so this stdout-block path should rarely fire.)
  - Else if STDOUT contains a `## Property coverage findings` block → this is a HARD failure, NOT best-effort: `/devforge:plan` declared pure-builder targets and at least one has no covering property-test task. Copy that stdout block VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and return to Phase 3 to create/extend the dedicated `qa-engineer` property-test task per the Phase 3.5 property-coverage gate; do NOT continue to the `render-implement-handoff` block. (In normal flow the Phase 3.5 property-coverage gate already caught this, so this stdout-block path should rarely fire. When no sibling `plan-handoff.json` exists, `finalize-handoff` skips this backstop silently — the Phase 3.5 gate is the strict arm.)
  - Else if STDOUT contains a `## Dead-code coverage findings` block → this is a HARD failure, NOT best-effort: `/devforge:plan` declared change-induced dead code and at least one row is folded into no task (no `**Dead code removal**:` field names its anchor token) OR into 2+ tasks (D7 requires exactly ONE owning task). Copy that stdout block VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and return to Phase 3 to fold each uncovered/duplicated anchor into exactly one owning task's `**Dead code removal**:` field per the Phase 3.5 dead-code-coverage gate; do NOT continue to the `render-implement-handoff` block. (In normal flow the Phase 3.5 dead-code-coverage gate already caught this, so this stdout-block path should rarely fire. When no sibling `plan-handoff.json` exists, `finalize-handoff` skips this coverage backstop silently — the separate declared-but-unsubstantiated stderr chokepoint below covers the missing-sibling case, and the Phase 3.5 gate is the strict arm.)
  - Else if STDERR contains `no agent roster found` → this is a HARD failure (broken install — `.claude/agents/` is missing or empty). Copy the helper's stderr VERBATIM into a fenced code block, then HALT and resolve the install before re-running; do NOT continue to the `render-implement-handoff` block.
  - Else if STDERR contains `declares change-induced dead code` → this is a HARD failure, NOT best-effort: `plan.md`'s `### Change-Induced Dead Code` section declares at least one MUST-delete row, but the sibling `plan-handoff.json` carries none — it is missing, stale, or malformed relative to `plan.md`, so the `dead_code_rows` passthrough came up empty. A declared MUST-delete kill-list must never ship as an empty carrier — a later `/devforge:verify` would then pass vacuously. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then run `.devforge/lib/plan_helper finalize-handoff <plan-path>` to regenerate the sibling `plan-handoff.json` and re-run `finalize-handoff`; do NOT continue to the `render-implement-handoff` block.
  - Else (any other non-zero cause — Exit 2 → plan or task files missing, a task carries a placeholder agent, or rendered content failed schema validation; Exit 1 → I/O error writing `breakdown-handoff.json`, e.g. permissions or disk-full) → copy the helper's stderr VERBATIM into a fenced code block, then do NOT abort. Continue to the `render-implement-handoff` block below. The structured handoff is best-effort for these causes; the manual block is the guaranteed human bridge.

The `breakdown-handoff.json` is the **producer side** of the breakdown→implement handoff. The `/devforge:implement` consumer reads this producer's contract. There is no auto-dispatch and no auto-consume: the manual block below remains how the user launches `/devforge:implement`.

Now WIP-commit `/devforge:breakdown`'s own artifacts so the work is git-safe at this step. Run this UNCONDITIONALLY (the task files + index were written in Phase 3 and approved in Phase 4; `breakdown-handoff.json` was just written above, best-effort):

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature_dir>/tasks", "<feature_dir>/breakdown-handoff.json", "<feature_dir>/design-manifest.json", "<feature_dir>/plan.md"]' --label 'breakdown: <feature-dir-name>'
```

Passing the `tasks` DIRECTORY path stages every task file plus `tasks/README.md` under it (the verb passes a directory path to `git add` unchanged, identical to `git add <feature_dir>/tasks`). `commit-artifacts` stages ONLY the named paths and makes a `[WIP] breakdown: <feature-dir-name>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifacts are already written, so note the warning and CONTINUE; do NOT abort); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. **In WRAPPER mode this is the FIRST per-step commit that tracks the task files + `tasks/README.md` in the install repo** — `/devforge:implement`'s wrapper path stages ONLY source code in the source repo and leaves these uncommitted — so the commit is NOT redundant there. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged. If `finalize-handoff` above failed to write `breakdown-handoff.json`, that path is simply not present and the verb stages only the present paths — a benign skip, not a failure. The `design-manifest.json` path is likewise present only when Phase 2.5 produced it (a feature with a `design/reference.html`); for a non-UI feature it is simply absent and skipped. `plan.md` is committed here because PHASE 0b may have mutated its `**Status**:` line on disk (flipped Draft → Approved, or inserted a missing Status line as Approved) and that mutation must be git-safe alongside the breakdown artifacts; when PHASE 0b changed nothing (already Approved, Complete, or a non-standard status) the file is unchanged and staging it is a benign no-op.

Then emit the deterministic manual next-step block via the helper:

```bash
.devforge/lib/breakdown_helper render-implement-handoff <plan-path>
```

Handle the exit code:

- Exit 2 → the plan or task files could not be read. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), tell the user to verify `<feature_dir>/tasks/` exists and re-run `/devforge:breakdown`, and end the turn. Unlike `finalize-handoff`'s non-blocking non-zero exit above (which continues to this block), a failure here DOES end the turn — this block is the guaranteed human bridge, and if it cannot render there is no fallback next-step to fall through to.
- Exit 0 → stdout is the deterministic manual-next-step block — copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The block heading reads `## Manual next step — run /devforge:implement`; it carries the task count, informationally names the numerically-lowest first task, and the literal `/devforge:implement` invocation line (no argument — the command auto-resolves the lowest incomplete feature and its next task). Both of those strings are composed by `render-implement-handoff` — they are the helper's, not this spec's, so do not rewrite them here. The block also instructs the user to **restart Claude Code** before running `/devforge:implement` so any newly-installed command is picked up.

After the block lands in the user-facing message, end the turn with one short confirmation: `"/devforge:breakdown is done. Restart Claude Code, then copy the invocation line from the block above to continue."` Do NOT restate that invocation in your closing sentence — the block already contains the literal `/devforge:implement` line, which `render-implement-handoff` composes (it is the helper's string, not this spec's — do not rewrite it here).

## IMPORTANT RULES

1. **Atomic tasks** — each task must be independently verifiable. Never bundle unrelated changes.
2. **Explicit dependencies** — if task B uses something task A produces, mark it. Missing dependencies cause bugs.
3. **One agent per task** — assign exactly ONE agent. If a task genuinely spans two stacks, split it into per-stack tasks joined by a dependency edge (per the Agent Assignment table's split-or-escalate rule) — never assign `architect` to write code.
4. **Include verification in every task** — every task's Done When carries the standing tsc/lint/tests conditions (the helper-emitted skeleton already does).
5. **Reference spec criteria** — every task maps to at least one acceptance criterion (`AC-N`).
6. **All ACs covered** — every spec acceptance criterion must be addressed by at least one task (enforced by `verify-ac-coverage`).
7. **Don't over-split** — a single find-and-replace across many files is ONE task, not many.
8. **Contract chain integrity** — every `Produces` feeds a downstream `Expects` or a spec AC; every `Expects` traces to an upstream `Produces` or existing state (enforced by `verify-contract-chain`).
9. **Contracts use semantic identifiers** — reference function / export / interface / field names. Never line numbers (they shift as earlier tasks modify files).
10. **Tasks decompose the plan, not the spec** — the plan already settled WHAT and HOW; `/devforge:breakdown` decomposes the plan's File Impact and Layer Map into ordered units. Drive Phase 1 and Phase 2 from the plan, not by re-scanning the spec.
