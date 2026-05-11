# /discover command plan

Status: planning. Net-new command. No code yet.
Active branch: `develop-2.0-init` (or successor — confirm at session start).

## Why /discover

`/research` (existing, under redesign per REDESIGN-RESEARCH-PLAN.md) targets existing-code delta — bug fix + enhancement. Both produce report shape: locate + trace + root-cause + options-to-bridge. Greenfield features (no related code exists yet) don't fit that shape: report's primary section "Existing Related Code" goes empty, "Gaps" balloons, "Approaches" collapses to "pick a library."

Greenfield needs a different lens:

- Prior-art survey (industry references, comparable products, established patterns).
- Integration surface sketch (where would this live in current architecture?).
- 2–3 design options (data model / state machine / API shape — not library comparison).
- Derisk plan (which unknown to prototype first).
- Build-vs-buy proposal.

`/discover` fills that gap. Workflow slot: `/discover → /specify → /plan → /breakdown → /execute-task → ...` — parallel to `/research` on the existing-code track. User picks at entry point.

## Naming locked

`/discover`. Alternatives considered in chat: `/groom` (Jira/PM backlog-refinement overload), `/explore`, `/scout`, `/prospect`. `/discover` reads clearest for an engineering audience; minor PM-discovery overload acceptable in context.

## Scope locked

1. Greenfield only — no existing-code investigation surface. If `/discover` detects related code mid-flow, recommend follow-up `/research` rather than handle both.
2. Pre-`/specify` slot, parallel to `/research`.
3. Output: structured report (rendered to console + ask-to-save like `/research`).
4. Hybrid agent dispatch (see Agent ownership below).
5. Helper-owns-shape (per `feedback_helper_owns_shape_principle`). Report schema owned by Python helper; LLM composes values via setters.
6. **Phase 0 scoping dialogue** before investigation. Vague-idea input (e.g., "auth in NestJS") gets narrowed via rubric-driven Q&A before any subagent dispatch — otherwise web-research drowns in 50 generic results, integration-surface scan has no focus target.

## Prerequisites (hard gate)

`/discover` refuses to run unless all setup-chain commands have completed. Helper `preflight` subcommand checks three artefacts at startup; exits non-zero with explicit instruction if any missing:

| Required artefact | Produced by | Hard-gate check |
|---|---|---|
| `.devforge/manifest.json` (or equivalent) | `/init-forge` | File exists |
| `docs/architecture.md` | `/generate-docs` | File exists + non-empty |
| `.devforge/project-config.json` | `/configure` | File exists + non-empty |
| `constitution.md` | `/constitute` | File exists + non-empty |

On missing artefact, helper emits:

```
BLOCKED: /discover requires the full 4-command setup chain.
Missing: <artefact>
Run: /init-forge → /generate-docs → /configure → /constitute, then retry /discover.
```

Exit code 2. No graceful skip, no fallback path. Setup is a prerequisite, not a recommendation.

## Phases (target order)

```
PHASE 0: Scoping dialogue          ← rubric-driven Q&A, orchestrator-only
PHASE 1: Investigation             ← parallel dispatch (web-research || integration-surface)
PHASE 2: Report drafting           ← orchestrator composes report from Phase 0 memo + Phase 1 findings
PHASE 3: Save + recommend          ← ask-to-save, next-step recommendation
```

## Existing-code awareness layer (docs + MCP)

`/discover` consults **two layers** when reasoning about existing code — both Phase 0 (pre-rubric hints for `integration_points`) and Phase 1 (fit-check):

### Layer 1: docs/ narrative context

Read by orchestrator (Phase 0 pre-rubric step) and integration-surface subagent (Phase 1):

- `docs/architecture.md` — project-tier architecture (per Track 4, shipped 2026-05-09)
- `docs/<package>/architecture.md` — package-tier architecture
- `docs/<package>/<concern>/index.md` — concern md (per /generate-docs Phase 2)
- `docs/glossary.md` — term grounding (per JUDGMENT-LAYER-PLAN Track B)

Use docs/ for **narrative orientation** (what the project is, package responsibilities, domain vocabulary). Mirrors /research preflight pattern (`src/_pending/commands/research.md` PHASE 1).

### Layer 2: CBM/MCP structural queries

CBM (codebase-memory-mcp) tools called by Phase 1 integration-surface subagent + orchestrator:

- `search_graph(name_pattern=..., label=..., qn_pattern=...)` — find named functions/classes/routes (File-label queries use `name_pattern`, not `file_pattern` — per memory `feedback_cbm_search_graph_pattern_keys`)
- `search_code(pattern=...)` — text-fallback for inline framework expressions invisible to graph (per memory `feedback_cbm_discovery_chain_search_graph_then_code` — mandatory chain: `search_graph` → `search_code` → declare absent only if BOTH return nothing)
- `trace_path(function_name, mode=calls|data_flow|cross_service)` — call chains for fit-check impact analysis
- `get_code_snippet(qualified_name)` — read source (NOT raw Read/cat)
- `get_architecture(aspects=...)` — structural summary
- `agentic_context "<topic>"` / `agentic_impact "<topic>"` / `agentic_architecture "<topic>"` — synthesized bundles when LLM mode enabled

### Runtime enforcement (hooks already shipped)

Four hooks at `src/hooks/` (propagated to target dir via install.sh; shipped 2026-05-09 per `project_track1_f11_hooks_shipped`):

- `cbm-session-reminder` (SessionStart) — injects CBM-first protocol into context on session start/resume/clear/compact
- `cbm-code-discovery-gate` (PreToolUse Read|Grep|Glob) — once-per-session block to remind CBM-first
- `bash-ban-raw-tools` (PreToolUse Bash) — once-per-session block on raw `grep`/`find`/`cat` over source-file extensions
- `cbm-mcp-marker` (PostToolUse Bash|mcp__codebase-memory-mcp__.*) — telemetry to `.devforge/cbm-usage.log`

Hooks fire once per session as reminder. `/discover` spec MUST explicitly instruct orchestrator + subagents to use CBM tools by name in briefs — hooks are reminder layer, not strict enforcement after first block.

### Preflight gate

Before Phase 1 dispatches, orchestrator runs preflight (mirror /research):

```
./.devforge/lib/generate_docs_helper preflight
```

Skip if `.devforge/.preflight-stamp` is fresher than 60s. Ensures CBM index is current. If preflight fails (no index), Phase 1 cannot proceed — hard-gate prerequisites already guarantee docs/ + constitution.md exist, so a preflight failure means CBM index is stale or missing. Emit error + instruct user to run `index_repository` (or rerun `/generate-docs` if substrate is broken).

## Phase 0: Scoping dialogue

**Goal**: convert vague-idea input into a structured scoping memo before any investigation fires. Without Phase 0, Phase 1 subagents have no narrowed query and produce noisy output.

**Shape**: rubric-driven Q&A. Helper owns the rubric (closed list of dimensions); LLM detects unfilled dimensions, asks one question at a time targeting the highest-uncertainty dimension; helper records user-confirmed values via setters.

**Rubric (generic, topic-agnostic):**

| Dimension | What it captures | Example ("auth in NestJS") |
|---|---|---|
| `functional_scope` | What does the feature DO | "JWT login + refresh + RBAC + 2 OAuth providers" |
| `users` | Who interacts | "End users + admins; no machine-to-machine" |
| `inputs_outputs` | Data shape (request/response, events, persisted entities) | "Email+password OR OAuth callback → JWT pair" |
| `integration_points` | Where it touches existing system | "All API routes need guard; extend existing user table" |
| `constraints` | Perf / compliance / deploy / scale | "GDPR; 7-day session; SOC2 audit log" |
| `non_goals` | Explicit OUT (prevents scope creep) | "No SAML SSO; no biometric; no passwordless yet" |
| `success_criteria` | High-level "done" signal | "Signup → login → hit protected route → token refreshes" |
| `edge_cases` | Failure modes + unwanted-behavior surfaces (separate from `constraints` — limits vs failure semantics are different questions) | "OAuth provider returns 500; token replay; concurrent login race; user-row delete cascade" |

**Pre-rubric supplementary prompts**:

Before rubric Q&A begins, helper asks one-shot supplementary prompts (free-text, no state machine, doesn't gate exit):

- `references` — "Any similar existing code, libraries, or product references to pattern after?" Stored as `ScopingMemo.references: list[str]`. When non-empty, Phase 1 subagents receive reference names as additional search anchors — dramatically narrows web-research and codebase-fit scans. Skip cleanly if user has no reference; proceed to rubric without penalty.

Adopted from Agent OS `/shape-spec` pattern (compresses many future questions into one when user already has an anchor). Source: <https://buildermethods.com/agent-os/shape-spec>.

**Pre-rubric docs scan** (orchestrator-side):

Before asking the rubric questions, orchestrator reads `docs/architecture.md` + `docs/glossary.md` to surface candidate `integration_points` hints. When user reaches the `integration_points` question, orchestrator offers detected hints as starting suggestions (e.g., "I see your project has packages X, Y, Z — likely touchpoints?") rather than asking blind. Hooks-friendly: orchestrator reads `.md` (not source code), so CBM gate does not block.

Docs presence is guaranteed by the hard-gate prerequisites — no skip path needed.

**Question strategy per dimension**:

- **Closed-choice dimensions** (e.g., "JWT vs session", "build vs adopt OSS") → `AskUserQuestion` with 2–4 options (per `feedback_askuserquestion_single_line_only` — single-line, no multi-line markdown).
- **Open dimensions** (e.g., "describe your OAuth providers + scopes") → free-text prompt rendered as plain prose, user replies in next turn.
- LLM picks per dimension type at runtime.

**Bounded turns**:

- Hard cap: 3 follow-ups per dimension. After cap, helper logs the dimension as `Partial` and moves on.
- State enum (per dimension): `Clear` (user-confirmed) / `Partial` (asked but unresolved within turn cap) / `Missing` (not yet asked). Aligned with GitHub Spec Kit clarify taxonomy. Source: <https://github.com/github/spec-kit/blob/main/templates/commands/checklist.md>.
- Helper tracks coverage after every setter call. After every turn, helper emits coverage state (e.g., `5/8 Clear, 2 Partial, 1 Missing`).
- Exit when all 8 dimensions are `Clear` OR user explicitly accepts gaps. On accepted-gap exit, helper emits two artefacts:
  - **Coverage summary table** rendered at top of scoping memo (per-dimension `Clear`/`Partial`/`Missing` state).
  - **`[NEEDS CLARIFICATION: <dimension> — <gap description>]` markers** serialized into `ScopingMemo.gaps`, so `/specify` (downstream) sees explicit uncertainty rather than silent absence. Adopted from Spec Kit. Source: <https://github.com/github/spec-kit/blob/main/spec-driven.md>.
- `scope-finalize` exit code: `0` when all `Clear`; `0` with `override_recorded=true` when user accepted gaps + helper recorded the override; non-zero when `Partial`/`Missing` present without override (forces explicit user choice).

**Persistence**:

- Scoping memo saved to `.devforge/discover-scope.json` after every setter call (mirrors `/constitute` + `/configure` per-answer persistence pattern).
- If user kills `/discover` mid-flow, restart resumes from saved state — no dialogue replay.
- Helper subcommand `read-scope` returns current memo for resume; `set-scope-<dimension>` sets one dimension; `scope-coverage` returns coverage state; `scope-finalize` locks the memo for Phase 1.

**Misalignment detection (hybrid by severity)**:

When user's later answer contradicts or drifts from earlier confirmed dimensions, helper + orchestrator detect and respond by severity. Three categories:

| Category | Example | Detection layer | Response |
|---|---|---|---|
| **Direct contradiction** | `non_goals` contains "OAuth" + `integration_points` mentions "OAuth callback routes" | **Helper-side** (token-overlap rule, deterministic, no LLM) | **Hard-block.** Halt rubric Q&A, present conflict via AskUserQuestion ("which to keep?"), rewrite loser dimension, then resume. |
| **Drift / scope creep** | Started "auth for end users", later answer adds "admin SSO" — expands scope | **LLM-side** (orchestrator runs short check after each setter call: "does this new answer expand or conflict with previously confirmed dimensions?") | **Soft-flag.** Log to `conflicts` list, continue rubric Q&A, surface at next natural pause: "this expands scope from X to X+Y — keep, narrow, or split into two features?" |
| **Refinement** | `users` = "end users" → later "actually end users + admins" | **LLM-side** (same check, classified as refinement when older answer is subset of new) | **Quiet update.** Rewrite affected dimension, log change in memo, no interruption. |

**Per-setter call protocol**:

```
After every set-scope-<dimension>:
  1. Helper runs check-conflicts (token-overlap rules; cheap, deterministic).
     If direct contradiction → block via AskUserQuestion, record resolution, rewrite loser dimension.
  2. Else orchestrator runs LLM-side drift check (short prompt).
     If drift detected → log to ScopingMemo.conflicts with type=drift, surface at next pause.
     If refinement detected → log + quietly rewrite affected dimension.
  3. Resume rubric Q&A.
```

**Anti-patterns explicitly forbidden**:

- Silent overwrite — later answer must never replace earlier without surfacing in conflicts log.
- LLM-only detection for direct contradictions — token-overlap rules run first; LLM only handles semantic drift.
- Force user to re-walk all 8 dimensions on conflict — only re-ask the affected dimension(s).

**What Phase 0 feeds**:

- Phase 1 web-research subagent: narrowed query built from `functional_scope + constraints + non_goals + edge_cases` (e.g., "NestJS Passport JWT multi-tenant RBAC patterns + token-replay mitigation" instead of "NestJS auth"). When `references` is non-empty, include reference names as additional search anchors.
- Phase 1 integration-surface + fit-check subagent: scoped scan target from `integration_points` (e.g., "scan API route definitions + user/auth-adjacent modules" instead of "scan entire codebase"). The user's `integration_points` answer is **the user's belief** about what the new feature touches — Phase 1 produces the **reality check** (what actually exists, what would be touched, what would need refactor first). Mismatch between belief and reality is a Phase 2 report finding, not an error.
- Phase 2 report: every section is informed by memo (Prior Art relevance scored against `functional_scope` + `references`; Design Options framed against `constraints` + `non_goals` + `edge_cases`; Derisk Plan derived from highest-uncertainty `success_criteria` + flagged `edge_cases`; **Fit Assessment** reconciles user's `integration_points` belief against Phase 1 reality check; gap markers from `ScopingMemo.gaps` rendered in a dedicated "Open uncertainties" section).

## Phase 2 report shape (target)

```markdown
# Discovery: [Topic Name]

**Date**: [YYYY-MM-DD]
**Topic**: [user's original description]
**Verdict**: Worth pursuing / Promising with caveats / Reconsider

## Summary

[3–5 sentences: what the idea is, why it's worth (or not) pursuing, recommended starting shape]

## Prior Art

| Reference | What it is | Relevance |
|-----------|------------|-----------|
| [product/library/pattern] | [1-line] | [how it informs our shape] |

## Integration Surface

[Where this would live in the current architecture — bullet list of touchpoints + reasons.]

| Touchpoint | Module/file | Why touched |
|------------|-------------|-------------|
| [name] | [path] | [reason] |

## Fit Assessment

[Reconciliation of user's Phase 0 `integration_points` belief against Phase 1 scan reality. Mismatch IS the headline finding.]

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|------------|---------------|----------------|--------|----------|
| [name] | yes/no | [what actually exists + compatibility note] | Low / Med / High | [list or "none"] |

**Overall fit**: Good / Acceptable / Strained / Misfit
**Effort estimate**: Low / Medium / High / Major refactor required
**Rationale**: [1–3 sentences explaining the fit verdict — what works, what doesn't, what would need to change first]

## Design Options

### Option A: [Name]
- **Shape**: [data model / state machine / API surface sketch — pseudocode OK]
- **Pros**: [list]
- **Cons**: [list]
- **Complexity**: Low / Medium / High

### Option B: [Name]
- (same shape)

**Recommended option**: [X] — [one-line rationale]

## Build vs Buy

| Build | Buy/Adopt |
|-------|-----------|
| [what we'd own] | [SaaS / OSS candidates] |

**Recommendation**: [Build / Buy / Hybrid] — [reasoning]

## Derisk Plan

[Ordered list of unknowns to probe first; smallest viable slice that validates the riskiest assumption.]

## Constitution Constraints

[If constitution.md populated, cite relevant rules + their impact on design.]

## Recommendation

- **Proceed**: "Run `/specify "[refined description]"` to formalize AC."
- **Reconsider**: "[Reason]. Consider [alternative] instead."

## Next step

[Rendered only when Verdict = Worth pursuing or Promising with caveats. Skipped on Reconsider.]

Copy the block below into a new `/specify` session manually. No automated handoff — user controls when (or if) `/specify` runs.

~~~
/specify "[1-2 sentence refined description distilled from functional_scope + users + success_criteria]"

Discovery reference: discover/YYYY-MM-DD-<topic-slug>.md
Key facts:
- Functional scope: [from ScopingMemo.functional_scope]
- Users: [from ScopingMemo.users]
- Success criteria: [from ScopingMemo.success_criteria]
- Recommended option: [Option name from Design Options]
- Open uncertainties: [count] (see discovery doc §Open uncertainties)
~~~
```

**Why this section exists**: `/discover` produces its own document shape (this report), not a `/specify` spec. This section is just a copy-pasteable starter prompt for the user — it lives at the bottom of the saved md file. Back-link to the discovery doc preserves full context for whoever reads `/specify` later.

### Verdict flip rule (effort-aware)

Helper enforces the following escalation:

- If Fit Assessment `Overall fit` = `Strained` OR `Misfit` → Verdict MUST be `Reconsider` UNLESS user's Phase 0 `non_goals` or explicit confirmation accepts the refactor cost upfront (helper records the override).
- If `Effort estimate` = `Major refactor required` → same rule: Verdict flips to `Reconsider` with rationale tying back to the specific Fit Assessment row that triggered it.
- Helper exit code from `verify` is non-zero if Verdict + Fit Assessment combination violates the rule without recorded override.

## Agent ownership — hybrid dispatch

**Phase 0 (Scoping dialogue)**: orchestrator-only. Dialogue cannot be dispatched — AskUserQuestion + free-text turns + setter calls must stay on the main thread for interaction fidelity. Per `feedback_avoid_subagents_for_sequential_identical_workflows`, dialogue has no parallelism, no tool isolation gain, and dispatch would stale-brief the agent between turns.

**Phase 1 (Investigation)**: parallel subagent dispatch — real parallelism + real context-budget benefit. Both subagents are **framework-owned** at `src/agents/` (NOT external plugins). Each is emitted via `scripts/emitters/claude.py` to `.claude/agents/` in target project. Pattern may be adapted from `cavecrew-investigator` as a reference but lives in framework — no runtime external dependency.

1. **`discover-web-researcher` subagent** (at `src/agents/discover-web-researcher.md`) — prior-art survey via Context7 + WebSearch using narrowed query from Phase 0 memo. Returns compressed reference list. Tools allowed: WebFetch, WebSearch, Context7 MCP. Web survey content is long + noisy; subagent dispatch keeps main context clean.
2. **`discover-fit-checker` subagent** (at `src/agents/discover-fit-checker.md`) — uses the **two-layer awareness** (docs + CBM/MCP, see "Existing-code awareness layer" above) to scan for module structure scoped to Phase 0 `integration_points`. Tools allowed: Read (for docs/ only), Grep, Glob, Bash + all `mcp__codebase-memory-mcp__*` tools. NO write/edit tools. Discovery chain:
   - **Layer 1 (docs/)**: read `docs/architecture.md`, `docs/<package>/architecture.md` for the suspected packages, `docs/<package>/<concern>/index.md` for relevant concerns, `docs/glossary.md` for term grounding.
   - **Layer 2 (CBM)**: `agentic_context "<integration_points value>"` for synthesized bundle → `search_graph(name_pattern=...)` for named symbols → `search_code(pattern=...)` fallback for inline expressions (mandatory chain per `feedback_cbm_discovery_chain_search_graph_then_code`) → `trace_path` for impact chains on fit-check candidates → `get_code_snippet` to read source.
   - **Raw Read/Grep/Glob over source files is forbidden** — hooks (`bash-ban-raw-tools` + `cbm-code-discovery-gate`) will block first attempt per session; spec instructs subagent to never even try.

Two outputs: (a) compressed touchpoint list (what exists + where), (b) **fit-check** per touchpoint — does the user's belief match reality? What's the integration effort? Are there blockers (incompatible schemas, conflicting patterns, missing infrastructure)? Returns reconciled view: user-expected vs reality, effort estimate per touchpoint, blockers list.

Both dispatch in parallel. Orchestrator consumes both compressed reports.

**Phase 2 (Report drafting)**: orchestrator-only. Composes report from Phase 0 memo + Phase 1 findings.

**Phase 3 (Save + recommend)**: orchestrator-only. AskUserQuestion for save decision.

Same hybrid pattern adopted for `/research` (orchestrator owns dialogue + report; dispatch expensive investigation only). Not full agent-owned.

## Constraints

- Zero-escape-hatch policy in spec body (no OR / if / except / unless / use-judgment).
- Helper-owns-shape: Python helper at `src/devforge/lib/discover_helper.py` mirroring `/constitute` + `/generate-docs` subcommand pattern.
- LLM-first density: spec body is LLM instructions, not human-onboarding wiki.
- Triple-agent verification on every spec edit: **instruction-author** writes/edits → **instruction-reviewer** checks intra-file logical flow + cross-reference consistency + sentence-level hallucination risk → **claude-code-guide** verifies Claude Code authoring conventions (external). All three must return clean before commit. Per `feedback_dual_agent_verify_command_statements` (rename pending).
- No real project names in examples (per `feedback_no_real_project_names`).
- Test-first for helper functions (per `feedback_test_first_python_helpers`).
- **No `model:` override** in `src/commands/discover/main.md` frontmatter (per `feedback_avoid_command_model_override`). Inherit session model.
- **Spec body is self-contained LLM instructions** scoped to `/discover` execution only — no forward refs to `/specify` or downstream phases in the spec prose (per `feedback_llm_instructions_self_contained`). The copy-pasteable next-step text lives in the OUTPUT document only (Phase 2 "Next step" section), never in the spec body. No automated handoff at runtime.
- **Verbatim echo directive** when spec instructs LLM to display helper output (coverage summary, scoping memo render, etc.): use the wording "copy VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase)" (per `feedback_verbatim_echo_directive`). "Relay" / "show" are ambiguous and get skipped.
- **Discovery document has its own shape** — not a `/specify` template, not a `/research` report. Owns: Verdict, Summary, Prior Art, Integration Surface, Fit Assessment, Design Options, Build-vs-Buy, Derisk Plan, Constitution Constraints, Open uncertainties, Next-step copy-pasteable text. Distinct identity preserved through render.

## Work order

- **Step 1**: confirm naming + scope + Phase 0 dialogue shape (done in chat 2026-05-11).
- **Step 2**: draft schemas (Python dataclasses / pydantic) for `discover_helper.py`:
  - Phase 0 `ScopingMemo` schema — 8 rubric dimensions (`functional_scope`, `users`, `inputs_outputs`, `integration_points`, `constraints`, `non_goals`, `success_criteria`, `edge_cases`) + per-dimension state enum (`Clear | Partial | Missing`, aligned with GitHub Spec Kit taxonomy) + per-dimension turn counts. Plus supplementary fields: `references: list[str]` (pre-rubric pointers; empty list when user has none), `gaps: list[{dimension: str, description: str}]` (NEEDS CLARIFICATION markers when user accepts partial exit), `override_recorded: bool`, `conflicts: list[Conflict]` (misalignment detection log). `Conflict` shape: `{type: "direct" | "drift" | "refinement", dimensions: list[str], description: str, resolution: "blocked-pending-user" | "user-chose-<X>" | "logged-no-action" | None}`. State persisted to `.devforge/discover-scope.json` (mirrors /constitute's `.devforge/constitute.json` pattern).
  - Phase 2 `DiscoveryReport` schema — sections per "Phase 2 report shape" above + next-step text section at bottom. Closed enums for Verdict, Recommendation, Complexity. State persisted to `.devforge/discover-report.json` while in-flight (mirrors /constitute's per-section state); rendered to `discover/YYYY-MM-DD-<topic-slug>.md` on Phase 3 save.
- **Step 3**: implement helper subcommands. Test-first per `feedback_test_first_python_helpers`. Subcommands:
  - Phase 0: `read-scope`, `set-scope-<dimension>` (×8 — includes `set-scope-edge-cases`), `record-references` (pre-rubric, optional one-shot), `record-gap` (when user accepts a dimension as `Partial`/`Missing` — appends NEEDS CLARIFICATION marker to `gaps`), `check-conflicts` (runs token-overlap rules after each setter; returns list of detected direct contradictions; orchestrator wraps with LLM-side drift check), `record-conflict-resolution` (logs user's resolution choice, rewrites loser dimension on direct contradiction), `scope-coverage` (returns `Clear`/`Partial`/`Missing` per dimension + coverage table + conflicts log summary), `scope-finalize` (emits coverage summary block + serialized gap markers + conflicts log; exit non-zero if `Partial`/`Missing` without `override_recorded` OR if any `conflicts.resolution == "blocked-pending-user"`).
  - Phase 1: `record-prior-art`, `record-integration-touchpoint`, `record-fit-assessment` (per-touchpoint: user-expected vs reality + effort + blockers), `set-overall-fit`, `set-effort-estimate` (consumed by subagents).
  - Phase 2: `set-design-option`, `set-build-vs-buy`, `set-derisk-plan`, `set-verdict`, `set-recommendation`, `set-next-step-text` (composes the copy-pasteable `/specify` prompt section from ScopingMemo + DiscoveryReport state; only emits when Verdict ≠ Reconsider; pure text generation, no automation), `render` (concatenates all sections including next-step text at the bottom). `verify` enforces Verdict flip rule (Strained/Misfit/Major-refactor → Reconsider unless override recorded).
  - Prerequisites: `preflight` (hard-gate check for `.devforge/manifest.json` + `docs/architecture.md` + `constitution.md`; non-zero exit + message on missing).
  - Cross-phase: `summary`, `verify` (mirrors `/constitute` pattern).
  - **Test fixture**: author `tests/lib/fixtures/discover-sample-report.md` covering one happy-path greenfield-feasible scenario (generic placeholders per `feedback_no_real_project_names` — e.g., "auth in a TypeScript backend framework"). Round-trip discipline (per `feedback_test_first_python_helpers`): build via real helper setter calls → `render` → diff against fixture. Fixture maintained as the canonical expected-shape artifact for `render()` regression tests. Skeleton lives in helper code (inline render, mirrors /constitute); fixture is a complete example, not a skeleton.
- **Step 4a**: author spec at `src/commands/discover/main.md` + reference docs (if any). Spec body covers all 4 phases with explicit transition gates (Phase 0 → Phase 1 requires `scope-finalize` exit code 0).
- **Step 4b**: author framework-owned subagents at `src/agents/`:
  - `src/agents/discover-web-researcher.md` — Context7 + WebSearch + WebFetch tools only. Prior-art survey discipline.
  - `src/agents/discover-fit-checker.md` — Read (docs/ only) + Grep + Glob + Bash + CBM/MCP tools. CBM chain discipline (per memory `feedback_cbm_discovery_chain_search_graph_then_code`). NO write/edit tools.
  Pattern may be adapted from `cavecrew-investigator` plugin agent as a reference, but files ship inside framework — no external plugin dependency.
- **Step 5**: triple-agent verify in iterative apply-verify loop (per `feedback_iterative_review_loop_preferred`):
  1. `instruction-author` drafts/edits spec.
  2. `instruction-reviewer` + `claude-code-guide` review in parallel (single message, two Agent tool calls).
  3. If either reviewer returns findings → loop back to step 1 with fixes briefed to author. Repeat until both reviewers clean.
  4. Present clean draft to user for approval.
  5. User approves → proceed to Step 6. User redirects → loop back to step 1 with new direction.
- **Step 6**: update emitter `scripts/emitters/claude.py` `_PROMOTED` list for `discover` command AND ensure both subagents (`discover-web-researcher`, `discover-fit-checker`) are in the emitter's agents list (per `feedback_emitter_promoted_cross_check`).
- **Step 7**: cross-update README, DEVELOPMENT-STATUS, CLAUDE.template, storage-rules (per `feedback_release_docs`).
- **Step 8**: empirical test on testForge20 with a genuinely greenfield topic. Validate Phase 0 dialogue converges within bounded turns; validate Phase 1 subagents receive narrowed query (not raw user input); validate docs/ + CBM consultation paths fire correctly + hooks log to `.devforge/cbm-usage.log`.
- **Step 9**: ship to develop-2.0-init / main with CHANGELOG entry. Cross-update README + DEVELOPMENT-STATUS + CLAUDE.template (per `feedback_release_docs`) confirmed at this step.

## Verify criteria

- **Step 3**: 100% helper subcommand tests pass; helper round-trips state via JSON. Coverage check on real input shapes (per `feedback_test_first_python_helpers`). Phase 0 specific:
  - `scope-coverage` returns accurate state after each setter call.
  - Bounded-turn cap (3 follow-ups/dimension) enforced; over-cap returns "partial" state, no crash.
  - `scope-finalize` exit code 0 only when all dimensions are `confirmed` OR user explicitly accepted gaps (helper records the override).
- **Step 4a**: spec passes intra-file consistency check (instruction-author). Phase transitions documented with helper gate references.
- **Step 4b**: both subagent files ship in framework (not external plugins); each passes triple-agent verify; emit to target `.claude/agents/` via install.sh; tool lists are read-only (no Write/Edit/NotebookEdit).
- **Step 5**: both verifier agents return clean.
- **Step 6**: `./install.sh` on fresh testForge20 promotes `/discover` into `.claude/commands/`.
- **Step 8**: empirical run produces report with all sections populated; user confirms output is actionable + matches the design-exploration lens (not feasibility-check repurposed). Validate:
  - Phase 0 dialogue converges within bounded turns on a vague-idea input (e.g., "auth in NestJS").
  - Phase 1 subagents receive narrowed query derived from scoping memo (inspect dispatch brief; raw user input must NOT appear as the subagent query).
  - Kill-and-resume: kill `/discover` mid-Phase-0, restart, confirm dialogue resumes from saved state without re-asking confirmed dimensions.
  - **Fit Assessment populated with at least one user-belief-vs-reality mismatch row OR explicit "all match" rationale; never empty.**
  - **Verdict flip rule fires correctly**: induce a Strained/Misfit Fit Assessment, confirm Verdict auto-flips to Reconsider; record an override, confirm verify exits 0.
  - **`edge_cases` dimension populated** on greenfield input; not silently skipped or merged into `constraints`.
  - **Coverage summary table emitted** at Phase 0 exit (8 dimensions with `Clear`/`Partial`/`Missing` state); renders at top of scoping memo.
  - **`[NEEDS CLARIFICATION]` gap markers serialized** in `ScopingMemo.gaps` when user accepts partial exit; downstream `/specify` can read them. Markers also surface in Phase 2 report "Open uncertainties" section.
  - **`references` field captured** when user provides anchors; empty list (no fabrication) when user has none. Phase 1 subagent briefs include references as search anchors when present.
  - **Hard-gate prerequisites enforced**: induce missing `docs/architecture.md`, confirm `preflight` exits non-zero with the required setup-chain message; restore and confirm exits clean.
  - **Next-step text section rendered** at bottom of saved md when Verdict ≠ Reconsider; section contains copy-pasteable `/specify "..."` prompt + key facts (functional_scope, users, success_criteria, recommended option, open-uncertainty count) + link back to saved discovery doc. Section omitted on Reconsider verdict. No orchestrator-driven automation — text is for user manual copy.
  - **Misalignment detection fires**:
    - **Direct contradiction**: induce conflict (e.g., set `non_goals` containing "OAuth", then `integration_points` mentioning "OAuth"); confirm helper `check-conflicts` flags it; confirm orchestrator blocks via AskUserQuestion; confirm `scope-finalize` exits non-zero until user resolves.
    - **Drift**: induce scope expansion (e.g., set `users` to "end users", later set to "end users + admins"); confirm LLM-side check classifies as `drift`; confirm logged to `conflicts` without blocking; confirm user prompted at next natural pause.
    - **Refinement**: induce subset-to-superset update on same dimension; confirm quiet rewrite without surfacing; confirm logged with `type=refinement` and `resolution=logged-no-action`.
  - **No silent overwrites**: any later answer that affects a confirmed dimension is logged in `conflicts` regardless of classification.
  - **Phase 1 integration-surface subagent uses CBM tools by name** (`search_graph`, `search_code`, `trace_path`, `get_code_snippet`) — never Read/Grep/Glob over source. Confirm by inspecting subagent dispatch transcript.
  - **Preflight gate fires** before Phase 1 dispatch; skipped only when `.devforge/.preflight-stamp` is fresher than 60s.
  - **`.devforge/cbm-usage.log` records** Phase 1 CBM invocations (telemetry from `cbm-mcp-marker` hook). Confirm log file grows during test run.

## Open questions

1. Should `/discover` output be savable to `discover/YYYY-MM-DD-topic.md` (mirroring `/research`'s `research/`)? Default yes for symmetry.
2. Cost gate: web-research subagent uses Context7 + WebSearch. Surface estimated token cost before kicking off, parallel to `/generate-docs` Phase 1 cost gate?
3. ~~Hybrid input (mostly greenfield but touches some existing code)~~ **Closed 2026-05-11** — see "Decisions added 2026-05-11" below. `/discover` always runs codebase fit-check in Phase 1; output may flip Verdict to Reconsider on high-effort fit.
4. Helper signature: does helper need `read-*` subcommands (per `/constitute` pattern) or just setters + render + verify? Decide once schema is drafted.
5. Should `/discover` consult `constitution.md` proactively? Same conditional + non-blocking pattern as `/research` (per REDESIGN-RESEARCH-PLAN.md open question §2).
6. Phase 0 rubric extensibility per topic domain (auth vs data-pipeline vs UI feature). **Updated 2026-05-11**: universal 8th dimension `edge_cases` added based on SDD framework survey (Spec Kit + Kiro EARS + Tessl all treat failure-handling as first-class). Default still: strictly generic in v1, no topic-specific sub-dimensions. Revisit only if empirical use shows specific topics still under-specified after the 8-dimension rubric + supplementary `references` prompt.
7. BMAD PRFAQ kickoff sub-mode for ultra-vague input (≤1 sentence, no anchor verbs/nouns) — deferred per YAGNI. Add only if empirical signal shows the vague-input case is common. Source: <https://docs.bmad-method.org/explanation/analysis-phase/>.

## When resuming work

1. Read this file in full.
2. Read REDESIGN-RESEARCH-PLAN.md for the existing-code counterpart (boundary check — confirm split still holds).
3. Read `/constitute` as the reference shape: `src/devforge/lib/constitute_helper.py` + `src/commands/constitute/main.md`.
4. Read framework-owned `src/agents/discover-web-researcher.md` + `src/agents/discover-fit-checker.md` once authored. If not yet authored, reference `cavecrew-investigator` plugin agent as a pattern source for one-time read; the framework versions are the authoritative copies thereafter. No external plugin dependency at runtime.
5. Pick up at the next unaddressed Work order step.
