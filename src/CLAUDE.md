# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

{{PROJECT_DESCRIPTION}}

- **Name**: {{PROJECT_NAME}}
- **Type**: {{PROJECT_TYPE}}
- **Frameworks**: {{FRAMEWORK}}
- **Languages**: {{LANGUAGE}}
- **Build Tool**: {{BUILD_TOOL}}
- **Build Command**: `{{BUILD_COMMAND}}`
- **Type Check Command**: `{{TYPE_CHECK_COMMAND}}`
- **Lint Command**: `{{LINT_COMMAND}}`
- **Project Root**: {{PROJECT_ROOT}}

{{WRAPPER_MODE_SECTION}}

## Project Structure

{{PROJECT_STRUCTURE}}

## Development Commands

{{DEV_COMMANDS}}

## Architecture

{{ARCHITECTURE_DETAILS}}

{{PACKAGE_STACKS_SECTION}}

## Workflow

### Spec-Driven Development Flow

```
Setup (once per project):
/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute

Per feature:
/devforge:research OR /devforge:discover → /devforge:specify → /devforge:spec-check → /devforge:plan → /devforge:grill → /devforge:breakdown → /devforge:implement (per task) → /devforge:review → /devforge:verify → /devforge:summarize → /devforge:finalize
```

Forge commands are namespaced — invoke them as `/devforge:<name>` (e.g. `/devforge:verify`). Seven are **human-typed only**: the one-time setup commands `/devforge:init-forge`, `/devforge:generate-docs`, `/devforge:configure` and `/devforge:constitute`, the adversarial checks `/devforge:grill` (whose run `/devforge:breakdown` requires) and `/devforge:spec-check` (whose fresh report `/devforge:plan` requires), and `/devforge:fix`. Never invoke those seven — name the command and let the user type it. Every other forge command is model-invocable: propose it, and once the user agrees, run it directly rather than asking the user to type it.

`/devforge:research` (bug/enhancement against existing code) OR `/devforge:discover` (greenfield) is a **required precondition** for `/devforge:specify` — `/devforge:specify` blocks until a pending research or discover handoff exists in a feature directory. Use `/devforge:research` when investigating existing code, `/devforge:discover` when surveying a greenfield idea; the two cover complementary intake lanes, and either one satisfies the `/devforge:specify` gate.

`/devforge:spec-check` is a **required step** — a spec-tier consistency check run between `/devforge:specify` and `/devforge:plan` that formalizes the acceptance criteria and proves whether they contradict each other. It never auto-runs: the USER types it, and `/devforge:plan` blocks until a fresh report for that spec exists. What is mandatory is that the check RAN and that its report still matches the current `spec.md` — `/devforge:plan`'s gate reads presence and freshness ONLY, never the verdict, so a REVISE-SPEC report satisfies it exactly as a CONSISTENT one does and the human keeps every disposition. A clean result is accepted without a question; anything else asks. It is a consistency prover, not a mind-reader — it checks whether the ACs contradict EACH OTHER, not whether they are what you meant.

`/devforge:fix` is **not a linear step** — it is a proposal-only remediation command with two lanes: a FEATURE lane OFF `/devforge:review` and `/devforge:verify` (and off an in-window conversational defect), run inside the post-`/devforge:implement`/pre-`/devforge:summarize` window; and a COLD lane run on an explicit `bugs/NNN-<slug>.md` argument, which has no feature and no window. The model OFFERS either lane, the user invokes it. It never appears in the arrow chain above.

- `/devforge:research "topic"` — Investigate a bug or enhancement against the existing codebase (required intake lane for `/devforge:specify`); on a confirmed save allocates `specs/NNN-name/` + the `spec/<feature-name>` branch and writes `research-report.md` + `research-handoff.json` there, WIP-committing them as it writes (folds into `/devforge:finalize`'s squash)
- `/devforge:discover "feature idea"` — Greenfield-feature discovery (required intake lane for `/devforge:specify`); on a confirmed save allocates `specs/NNN-name/` + the `spec/<feature-name>` branch and writes `discovery-report.md` + `discover-handoff.json` there, WIP-committing them as it writes (folds into `/devforge:finalize`'s squash)
- `/devforge:specify "feature"` — Create spec with acceptance criteria → `specs/NNN-name/spec.md`, written into the feature directory intake already allocated (blocks until a pending research or discover handoff exists); captures a per-feature `**Design source**:` declaration (`html` / `figma` / `screenshot` / `none`) in the spec frontmatter and persists a structured design anchor (`specs/NNN-name/design-anchor.json` — the design source plus which selectors carry the design intent) captured at intake; WIP-commits the spec + handoff as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:spec-check` — **Required before `/devforge:plan`, typed by the user** spec-tier SMT consistency check of the acceptance criteria → `specs/NNN-name/spec-check.md` (run between `/devforge:specify` and `/devforge:plan`; `/devforge:plan` blocks until a fresh report exists, checking that report's presence + freshness only and never its verdict; a consistency prover, not a mind-reader — checks whether the ACs contradict each other, not whether they are what you meant); WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:plan` — Technical plan from approved spec → `specs/NNN-name/plan.md`; WIP-commits the plan + handoff (and the spec's Draft→Approved status flip) as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:grill` — **Required before `/devforge:breakdown`, typed by the user** design-time adversarial review of the completed `plan.md` → `specs/NNN-name/grill.md` (run between `/devforge:plan` and `/devforge:breakdown`; `/devforge:breakdown` blocks until a grill report exists whose recorded adversary run completed, checking that report's presence only — never its freshness and never its disposition, so a KILL report satisfies it exactly as a PROCEED one does and the human keeps every call); WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:breakdown` — Atomic tasks with dependencies → `specs/NNN-name/tasks/`; WIP-commits the task files + handoff (and the plan's Draft→Approved status flip) as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:implement` — Drain the feature's tasks one at a time (no args); per-task hard gate before commit
- `/devforge:review` — Feature-level emergent cross-task review → findings report; WIP-commits the report as it writes it (folds into `/devforge:finalize`'s squash)
- `/devforge:verify` — Verify ACs + assembled mechanical checks, fold `/devforge:review` findings → APPROVED / NEEDS WORK / REJECTED verdict + spec flip on APPROVED; WIP-commits the verification report (and the flipped spec) as it writes them (folds into `/devforge:finalize`'s squash)
- `/devforge:fix` — **Proposal-only remediation command** (NOT a linear step), two lanes. FEATURE lane: OFFERED off `/devforge:review` findings / `/devforge:verify` NEEDS WORK / an in-window conversational defect → gated fix via `/devforge:implement`'s back half → `[WIP] fix:` commit, or instead a scope-change bounce that writes a verdict-gated backward re-entry seed (`specs/NNN-name/fix-seed.json`) for `/devforge:specify`, WIP-committing it as it writes it (folds into `/devforge:finalize`'s squash). COLD lane: typed with a `bugs/NNN-<slug>.md` argument → the same gated back half over one already-filed bug, ending in a clean `fix(scope):` commit (never `[WIP]` — nothing squashes it) plus that one bug file flipped to Fixed; its scope-change bounce recommends `/devforge:research` and writes no seed. `/devforge:report-bug` is both the file-and-defer alternative and the way a cold bug becomes remediable
- `/devforge:summarize` — PR-ready feature synthesis → `specs/NNN-name/summary.md`; WIP-commits the summary as it writes it (folds into `/devforge:finalize`'s squash)
- `/devforge:finalize` — Surgical `docs/` updates via tech-writer + an unconditional `specs/<feature>/` safety-net commit + squash WIP commits into a clean feature commit

`/devforge:research` and `/devforge:discover` are read-only on source code and produce no spec themselves — but a confirmed save is a repository mutation: it creates the feature directory, creates the `spec/<feature-name>` branch when the session is on the default branch, and WIP-commits the artifacts. Their handoffs are a required precondition for `/devforge:specify`, so they belong to the spec pipeline above, not to the standalone group below.

Standalone (no pipeline connection — runs outside the spec pipeline):
- `/devforge:audit` — Adversarial whole-codebase quality + system-design + best-practices review
- `/devforge:report-bug` — Pure-capture bug report: writes one `bugs/NNN-<slug>.md` (Status Open, Source manual) and stops; dispatches no agent

### Command Details

Argument syntax per command; the workflow list above carries the one-line purposes, and a command's full behavior loads when it runs. Seven commands — `/devforge:init-forge`, `/devforge:generate-docs`, `/devforge:configure`, `/devforge:constitute`, `/devforge:spec-check`, `/devforge:grill`, `/devforge:fix` — are human-typed only, so their entries below carry a full description: this section is the only place the model sees what they do.

#### `/devforge:research "<topic>"`
Bug/enhancement intake lane. Hard-gated on the 4-command setup chain.

#### `/devforge:discover "<topic>"`
Greenfield intake lane. Hard-gated on the 4-command setup chain.

#### `/devforge:specify "<feature description>"`
Writes `spec.md` into the feature directory intake allocated; blocks until a pending research or discover handoff exists. **Requires approval before `/devforge:plan`.**

#### `/devforge:spec-check [feature-or-spec]`
**Required before `/devforge:plan`, and typed by the user — it is never auto-invoked** spec-tier consistency check of the acceptance criteria — the spec-level mirror of `/devforge:grill`, positioned between `/devforge:specify` and `/devforge:plan` so a self-contradictory spec is caught before `/devforge:plan` builds on it. `/devforge:plan`'s Phase 0a.8 gate blocks until `specs/[feature]/spec-check.md` exists beside the resolved spec and the spec hash it recorded still matches that spec; that gate reads PRESENCE and FRESHNESS only, never the verdict, so a REVISE-SPEC report satisfies it exactly as a CONSISTENT one does. When it blocks, name `/devforge:spec-check` for the user to run — never run it yourself. Formalizes each acceptance criterion into a constraint IR via the read-only `spec-formalizer` agent (a fixed 2-pass quorum keeps the formalization — and so the verdict — reproducible), runs the Z3 SMT solver over the constraints, and recommends a 3-way disposition — CONSISTENT / REVISE-SPEC / DISMISS. The human checks the TRANSLATION (does the IR faithfully capture each AC?) and owns every verdict the run raises — the tool recommends, it never decides; a clean result (no contradiction reproduced, every AC's subject resolved, no citation miss) is accepted without a question, and anything else surfaces the report and asks. Writes `specs/[feature]/spec-check.md`; when the user's pick matches a REVISE-SPEC recommendation, the orchestrator emits a backward re-entry seed (`specs/[feature]/spec-check-seed.json`, `target_stage="spec"`) that `/devforge:specify` consumes on re-run. WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash). Scope boundary: it is a consistency prover, not a mind-reader — it checks whether the ACs contradict EACH OTHER, not whether they are what you MEANT (a single coherent-but-wrong AC passes). It is STRONG on numeric / state / enum invariants but catches a permission clash ONLY when a permitting case is asserted reachable (not "permission logic" in general). The Z3 proof is deterministic over a human-checked, quorum-stable formalization — not a bare "deterministic proof of your spec".

#### `/devforge:plan [spec-file]`
**Requires a fresh `/devforge:spec-check` report for the resolved spec before it will run** (Phase 0a.8 blocks otherwise — name `/devforge:spec-check` for the user to type). **Requires approval before `/devforge:breakdown`.**

#### `/devforge:breakdown [plan-file]`
**Requires approval before `/devforge:implement`.**

#### `/devforge:grill [plan-file-or-feature]`
**Required before `/devforge:breakdown`, and typed by the user — it is never auto-invoked** design-time adversarial review of the completed `plan.md` — the design-level mirror of `/devforge:review`, positioned between `/devforge:plan` and `/devforge:breakdown` so a fatally-flawed design is killed before `/devforge:breakdown` decomposes it. `/devforge:breakdown`'s entry gate blocks until `specs/[feature]/grill.md` exists beside the resolved plan AND its sibling `grill-state.json` records that the adversary dispatch completed; that gate reads PRESENCE and that recorded status only — never freshness (a report written against a since-edited `plan.md` still passes, so acting on a finding never costs another full adversarial run) and never the verdict, so a KILL report satisfies it exactly as a PROCEED one does. When it blocks, name `/devforge:grill` for the user to run — never run it yourself. `/devforge:plan`'s finalize-time stakes-hint is unchanged and still non-blocking: it flags a high-stakes plan (new architecture / dependency / data model / security) so the grill gets extra attention, and it neither runs `/devforge:grill` nor gates anything. Dispatches the `devils-advocate` adversary plus a refutation pass (architect-excluded `[code-reviewer, qa-reviewer, security-reviewer]`), reusing the shared refutation engine. The adversary reads `plan.md` + `spec.md` + the recon dossier + `constitution.md` + a scoped three-ring codebase slice, with self-gated web-verification of the plan's external claims. Writes `specs/[feature]/grill.md` with a recommended 4-way disposition — PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; when the user's PHASE-7 pick matches a REVISE-PLAN or RE-ENTER-UPSTREAM recommendation, the orchestrator emits a backward re-entry seed (`specs/[feature]/grill-seed.json`) whose `target_stage` routes the consumer — on RE-ENTER-UPSTREAM the seed targets an upstream stage for the `/devforge:research`/`/devforge:discover`/`/devforge:specify` commands to consume, on REVISE-PLAN it targets `plan` for `/devforge:plan` to consume on re-run (so the revision addresses the grill's confirmed findings instead of re-deriving the plan). A run where nothing survived cross-examination presents the result and ends without asking a question; anything else opens the human gate. WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash). The USER owns the final verdict at the `/devforge:breakdown` approval gate — all four dispositions survive, KILL included, and what became mandatory is that the grill RAN, never that its disposition binds.

#### `/devforge:implement`
No arguments — auto-resolves the first incomplete feature in resolution order (legacy `NNN-` directories by number, then `YYYY/MM`-bucketed directories by year, month, then name) and drains its tasks in dependency order, with a per-task hard gate before each commit.

#### `/devforge:review [spec-file/feature-dir]`
Findings only, NO verdict — the verdict is `/devforge:verify`'s.

#### `/devforge:verify [spec-file]`
Owns the single APPROVED / NEEDS WORK / REJECTED verdict; on APPROVED it flips the spec `**Status**:` → Complete.

#### `/devforge:fix [spec-file/feature-dir | bugs/NNN-slug.md]`
**Proposal-only gated remediation command** — NOT a linear pipeline step. OFFERED (never auto-invoked — the model proposes, the user types `/devforge:fix`) in FOUR situations, and the ARGUMENT decides which lane runs. Three are FEATURE-lane and all sit inside the post-`/devforge:implement`/pre-`/devforge:summarize` window: `/devforge:review`'s findings, `/devforge:verify`'s NEEDS WORK verdict, or an in-window conversational defect the user raised and the model code-confirmed. The fourth is the COLD lane — an explicit `bugs/NNN-<slug>.md` argument — which has no feature and no window at all, and is the route for a real defect that sits outside any feature. Consumes findings that were WRITTEN before the run started, from THREE sources (`specs/[feature]/review.md`, `specs/[feature]/verification.md`, or one `bugs/NNN-<slug>.md` handed to it by path) — it never invents a defect and never accepts a typed bug description — triages and scopes them, then reuses `/devforge:implement`'s back half by CALLING the `implement_helper` verbs (scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → two-stage hard gate → commit); it copies no machinery, and BOTH lanes run that back half unchanged. A bug FILE is a written finding but NOT a confirmed one, so the cold lane confirms it against live code before remediating and STOPS when it cannot. Commit shape differs: the feature lane writes a `[WIP] fix:` commit that `/devforge:finalize` squashes; the cold lane writes a clean `fix(scope):` commit that nothing squashes, because there is no feature to finalize. CREATES no `bugs/` file ever — `/devforge:report-bug` remains the only creator and the "defer" arm — and its single `bugs/` write is the cold lane flipping the ONE file it was handed to `Fixed` after the hard gate approves. A "fix" that turns out to need an architectural/behavior change bounces instead of remediating, and the bounce differs by lane. FEATURE lane: it names WHICH item and WHY, then asks ONE question about who owns the scope change; when the user's pick matches that recommendation the orchestrator emits a backward re-entry seed (`specs/[feature]/fix-seed.json`, `source="fix"`, `target_stage="spec"`, WIP-committed under the distinct `[WIP] fix-seed:` label — folds into `/devforge:finalize`'s squash) that `/devforge:specify` detects and consumes on its next run, so the recommended fresh cycle (`/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown`) is DIRECTED at the named scope change instead of re-deriving it; every other pick writes nothing. COLD lane: it recommends the full chain from `/devforge:research` (never `/devforge:specify`, which blocks without a handoff), asks nothing, writes NO seed, and leaves the bug `Open`. A run either bounces or remediates, never both.

#### `/devforge:summarize [spec-file]`
Gates on the spec `**Status**: Complete` flip `/devforge:verify` owns; writes only `specs/[feature]/summary.md` and renders no verdict.

#### `/devforge:finalize [spec-file]`
Gate-checked: the spec must be Complete (set by `/devforge:verify`). The last step before creating a PR.

#### `/devforge:init-forge`
First command in the 4-command setup chain — bootstraps the project: captures the structural fields, then hands off to `/devforge:generate-docs`.

#### `/devforge:generate-docs`
One-time brownfield doc generation (second command in the 4-command setup chain) — reads the indexed codebase and builds the `docs/` knowledge base in bottom-up tiers (concern → package → project + glossary) via the `generate_docs_helper` setter API (tech-writer in Skeleton-Fill Mode). Handles both monorepo and standalone single-root layouts. Re-run when the codebase structure changes significantly.

#### `/devforge:configure`
Third command in the 4-command setup chain — populates `.devforge/project-config.json` and substitutes the file templates, from `/devforge:init-forge` state + `/devforge:generate-docs` output.

#### `/devforge:constitute`
One-time deep codebase analysis (or interview for greenfield projects) that generates `constitution.md` — non-negotiable rules, architecture decisions, patterns. Its Section 3.5 forcing-functions config-capture offers the `design_token_provenance` rule (the build-time half of the Design Fidelity principle) for UI projects with a design source.

#### `/devforge:audit [--full | --uncommitted | --top N | path] [--passes N]`
**NOT part of any workflow chain** — invoke manually after several specs ship. `--top N` defaults to 25; `--passes N` (clamped 1–3) defaults to 2 for the broad and hotspot scopes and 1 for narrow.

#### `/devforge:report-bug "<bug description>" [--file <path>] [--severity Critical|Warning|Info]`
**NOT part of any workflow chain.** Severity defaults to `Warning`; the `NNN` prefix is assigned by the helper.

### Conversational fix-or-file offer

When the user points out a defect AND you confirm it is real by reading the actual code, offer the route that fits. Choose between the routes by asking whether the fix REPAIRS existing behavior or CHANGES what the system does — never by counting files.

- **In-window defect repair** — the active feature is implemented-but-not-yet-summarized (verify with `.devforge/lib/fix_helper in-fix-window --feature <feature>` — exit 0 = in-window; any other result, whether out-of-window or the helper is unavailable/errors, → treat as not in-window). All three conditions are required (user-raised AND code-confirmed AND in-window): offer a two-arm choice — run `/devforge:fix` to remediate now (a gated remediation loop), or run `/devforge:report-bug` to file a bug and defer.
- **Cold defect repair** — a confirmed repair with no feature in that window (none active, or it is already sealed): offer `/devforge:report-bug` to file it, then `/devforge:fix bugs/NNN-<slug>.md` to remediate it under the same gates.
- **A change, not a repair** — the fix would add behavior, change a data model or contract, or restructure a layer: recommend the full chain from `/devforge:research`, in or out of window.

If the defect is unconfirmed or you originated it, offer only `/devforge:report-bug` — never `/devforge:fix`. Never auto-run `/devforge:fix`: it is human-typed only, so propose it and let the user invoke it.

## Available Agents

{{AGENT_LIST}}

Agent selection is automatic in `/devforge:implement` based on the task's assigned agent.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `/devforge:plan` can run
- Fresh `/devforge:spec-check` report for the resolved spec → before `/devforge:plan` can run (a mechanical precondition, not an approval: presence + freshness of `spec-check.md` only — its verdict never gates)
- Plan approval → before `/devforge:breakdown` can run
- `/devforge:grill` run for the resolved plan → before `/devforge:breakdown` can run (a mechanical precondition, not an approval: presence of `grill.md` plus the adversary status recorded in `grill-state.json` only — never its freshness and never its disposition)
- Task breakdown approval → before `/devforge:implement` can start
- Acceptance criteria → verified in `/devforge:verify`

### Verification (explicit, scope-aware — no per-edit hooks)

Verification runs at task boundaries (end of `/devforge:implement`, etc.), not after every file edit. No per-edit hooks, no auto-execution after Edit/Write. (Runtime hooks for CBM-first discovery enforcement are described in **CBM-first Protocol Enforcement** below — those operate on Read/Grep/Glob/Bash/SessionStart, not on Edit/Write.) Verification is **scope-aware**: the phase reads `PACKAGE_STACKS` (see `## Packages` above) to determine which type-check / lint / build / test commands apply to each file touched during the task.

**Scope-aware verification flow**:

1. Identify files touched during the task (git diff against the task-start checkpoint).
2. For each touched file, find its package via `PACKAGE_STACKS` path lookup (longest path prefix wins; e.g., `services/api/users.py` matches the `services/api` package).
3. Run that package's `type_check_command`, `lint_command`, and `test_command` (stored in `.devforge/project-config.json`). Skip `"N/A"` and absent commands silently (no-op; not a failure).
4. Build (`build_command`) runs once per task between the static checks and the tests, aggregated across touched packages when multiple are edited. The fixed order is static checks (type-check + lint) → build → tests, so a failing build surfaces before any test runs.
5. For files not inside any detected package (top-level scripts, misc files): fall back to the primary-stack commands (`TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `BUILD_COMMANDS[0]` / `TEST_COMMANDS[0]`).
6. **Self-repair loop**: if type check, lint, or a test fails, attempt up to 3 auto-repair iterations before stopping and reporting. Code-review findings are reported to the user, not auto-repaired.

**Pre-flight check** (before each task): read `constitution.md` and `.devforge/memory.md` so the task starts with the right context.

Full specification in `/devforge:implement`.

**End-to-end suite** — feature-level, never per task: when `E2E_COMMAND` is configured, `/devforge:verify` runs it ONCE against the assembled feature and reports the result, and the run is ADVISORY — no status changes the verdict. An unconfigured `E2E_COMMAND` runs nothing and reports nothing. Full specification in `/devforge:verify`.

## CBM-first Protocol Enforcement

Four hook scripts ship at `.claude/hooks/` and are wired in `.claude/settings.json` to enforce the codebase-memory-mcp (CBM) discovery protocol at runtime. They steer code exploration toward `search_graph`, `trace_path`, `get_code_snippet`, `search_code`, and `query_graph` instead of raw `Read`/`Grep`/`Glob` or shell `grep`/`find`/`cat` over source files.

| Hook | Event | Matcher | Behavior |
|---|---|---|---|
| `cbm-code-discovery-gate` | `PreToolUse` | `Read\|Grep\|Glob` | Blocks (exit 2) on the first matched call of the session and sets the gate file, with a stderr reminder to use CBM tools; subsequent matches in the same session pass through (exit 0). Gate file: `/tmp/cbm-code-discovery-gate-$PPID`. |
| `bash-ban-raw-tools` | `PreToolUse` | `Bash` | First call per session whose `command` contains `grep`/`find`/`cat` over a source-extension file (`.py`, `.ts`, `.tsx`, `.vue`, `.go`, …) blocks (exit 2); other Bash calls and subsequent same-session matches pass through. Gate file: `/tmp/bash-ban-raw-tools-$PPID`. |
| `cbm-mcp-marker` | `PostToolUse` | `Bash\|mcp__codebase-memory-mcp__.*` | Appends `<UTC timestamp> <tool_name>` to `.devforge/cbm-usage.log` for every matched call (Bash + every CBM MCP tool); filter the log on the `mcp__` prefix to isolate the CBM-adoption signal. Always exit 0; never blocks. |
| `cbm-session-reminder` | `SessionStart` | `startup\|resume\|clear\|compact` | Stdout is injected as session context; re-states the CBM-first protocol after compaction / resume / clear. |
| `cbm-sync-session-start` | `SessionStart` | `startup\|resume\|clear\|compact` | Calls `.devforge/lib/cbm_sync_helper check`; emits stdout context block instructing Claude to run `mcp__codebase-memory-mcp__detect_changes` (drift) or `mcp__codebase-memory-mcp__index_repository` (missing) plus `cbm_sync_helper write` to refresh the stamp. Silent on `current` / `not-a-git-repo`. Stamp file: `.devforge/cbm-last-indexed-sha`. |

### Disabling individual hooks

To disable any hook, remove its entry from the corresponding event array in `.claude/settings.json`. The hook scripts under `.claude/hooks/` remain on disk but are no longer invoked. Re-running `install.sh` overwrites `.claude/settings.json` and restores the hooks.

### Why CBM-only

The hook messages reference codebase-memory-mcp tools exclusively (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`, `get_architecture`, `index_repository`). They do NOT reference codegraph's `agentic_*` tools — those require LLM-enabled mode that is not configured in default forge installs.

## Placeholder Convention

Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`, `{{LANGUAGE}}`) in a template file is a substitution placeholder. Each marker is replaced with the user's answer or a detected value before the file is presented to the user.

Authors of template files — constitution, agent files, docs, this CLAUDE.md — may use these placeholders freely. Readers must never see literal `{{...}}` text in substituted output; if a placeholder reaches the user verbatim, the substitution step is broken or the marker name is wrong.

## Key Rules

### Always
1. **Read before write** — always read files before modifying them
2. **Constitution is law** — `constitution.md` rules override everything except user instructions
3. **Minimal changes** — every change should impact as little code as possible
4. **Memory is persistent** — check `.devforge/memory.md` for lessons from past sessions
5. **Specs are contracts** — once approved, implementation must satisfy every acceptance criterion
6. **One task at a time** — execute tasks sequentially following the dependency graph
7. **Document new code** — all new functions/variables must have clear documentation
8. **Lint everything** — linting must pass on all changed files before task completion
9. **Handle both paths** — every fallible operation must handle success AND error cases
10. **Validate at boundaries** — validate external input (user input, API responses, env vars); trust internal code
11. **SOLID, DRY, KISS** — single responsibility, don't repeat logic 3+ times, keep it simple
12. **Search before building** — before writing anything generic/reusable, search the codebase for existing utilities, helpers, or components that already do it
13. **Session state** — after each `/devforge:implement`, overwrite `.devforge/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `/devforge:implement` writes a WIP marker (`.devforge/wip.md`) before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.
15. **English in files** — all file content and commit messages stay in English (specs, plans, code, comments, docs), regardless of any operator response-language setting; a non-English response language applies to conversation only. Verbatim quotes of user-reported words may keep their original language.
16. **Test behavior changes** — every change to observable behavior ships with a test that asserts it; the configured test command must pass on changed files before task completion

### Never
1. **Never swallow errors** — empty catch blocks are forbidden; handle, re-throw, or log with reason
2. **Never commit secrets** — no API keys, tokens, or credentials in code
3. **Never commit debug artifacts** — no console.log, debugger, print() left behind
4. **Never leave bare TODOs** — every TODO must have context and a reference
5. **Never modify outside scope** — do not "fix" unrelated code you happen to see
6. **Never guess** — if unsure how code works, read it; if unsure what user wants, ask

## Commit Convention

### Format
- **Final commits**: Conventional Commits — `type(scope): description`
  - `feat(scope):` — new feature
  - `fix(scope):` — bug fix
  - `refactor(scope):` — behavior-preserving restructuring
  - `docs:` — documentation only
- **WIP commits**: `[WIP] Type: description — phase detail` (squashed into final commit)
- **Checkpoint commits**: `[checkpoint] Pre-type: description` (squashed into final commit)

### Attribution
{{COMMIT_ATTRIBUTION}}

### Rules
- Keep commit title under 72 characters
- No period at end of title
- Body is optional; use for non-obvious "why"
- One logical change per final commit (WIP commits get squashed)

## Artifact Storage

```
specs/
  001-feature-name/            # Numbered feature dirs (allocated by /devforge:research or /devforge:discover)
    research-report.md         # /devforge:research report — bug/enhancement lane
    research-handoff.json      # /devforge:research → /devforge:specify handoff
    probe-script.<ext>         # /devforge:research tier-1.5 probe (optional)
    emission-matrix.md         # /devforge:research caller emission matrix (optional)
    discovery-report.md        # /devforge:discover report — greenfield lane
    discover-handoff.json      # /devforge:discover → /devforge:specify handoff
    spec.md                    # /devforge:specify output
    plan.md                    # /devforge:plan output
    research.md                # /devforge:plan research notes (optional) — NOT research-report.md
    data-model.md              # /devforge:plan data model (optional)
    contracts.md               # /devforge:plan API contracts (optional)
    tasks/                     # /devforge:breakdown output
      README.md                # Task index with dependency graph
      001-define-types.md      # Individual task files
      002-create-repo.md
      003-build-component.md

docs/
  overview.md                  # Project overview + package map (project tier)
  architecture.md              # Cross-package architecture + layering rationale
  glossary.md                  # CBM-augmented project glossary (project tier; Phase B)
  <package>/                   # One subdir per package (from .devforge/index.json)
    overview.md                # Package role + concerns list
    architecture.md            # Package layers + patterns
    <concern>/                 # One subdir per src/ subfolder
      index.md                 # Concern: Purpose + Structure (annotated tree, fenced) — LLM-first density
```

- Feature dirs: `NNN-kebab-name`, sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md`, sequential within feature
- Everything for a feature lives in one directory — including the intake report + handoff, since `/devforge:research` and `/devforge:discover` create the directory (and the `spec/<feature-name>` branch) at their confirmed save and `/devforge:specify` resolves it rather than allocating one
- docs/ is generated by `/devforge:generate-docs` (Plan F): bottom-up tiers (concerns → packages → project), incremental skip via `source_stamp` frontmatter
- docs/ files are LLM context source first, dev-greppable second (LLM-first density format; see `.devforge/storage-rules.md`)
- Structural queries (exports, types, callers, deps, dead code) are NOT in docs/ — query the codebase-memory-mcp graph live via MCP tools (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`)
- Md files are auto-indexed by codebase-memory-mcp; `search_graph(query="<fuzzy topic>")` plus `search_code(pattern)` together surface md narrative + code structure
- `docs/glossary.md` is the project-tier consolidated glossary produced by Phase B — 30-150 CBM-classified terms (code-anchored / fuzzy-anchored / prose-only) with 1-2 sentence definitions and cite-back paths; concern-tier Purpose paragraphs still carry inline disambiguation
- See `.devforge/storage-rules.md` for full conventions including density rules + cite-back validation
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{PROJECT_ROOT}}`

## Session Continuity

At the start of each session, read `.devforge/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — per-task history lives in task completion notes (`specs/`); this file keeps only the sliding window above. `.devforge/memory.md` is not a history home either: it carries feature-level LESSONS, written by `/devforge:verify` into its named `## ` sections
- **Updated automatically** by `/devforge:implement` (Phase 7)

If context is compacted or a new session starts, session-state.md ensures the next `/devforge:implement` can bootstrap without re-discovering state.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `/devforge:implement` will detect the interrupted state via `.devforge/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. The WIP marker includes a `Command` field identifying which command was interrupted; if you run a different command while a marker exists, it detects the mismatch and asks you to resolve the previous session first. Git checkpoint commits (`[WIP]` prefix) preserve partial work and are squashed into a clean feature commit by `/devforge:finalize` when the feature is approved.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](.devforge/memory.md) — Persistent learnings
- [Project Config](.devforge/project-config.json) — `/devforge:configure` answers plus per-stack arrays (`LANGUAGES`, `FRAMEWORKS`, `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS`) and per-package `PACKAGE_STACKS` records
