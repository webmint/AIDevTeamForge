# AIDevTeamForge

A spec-driven development template for Claude Code that combines structured specification workflow with enforced execution quality.

Install it into any project — existing or greenfield — and get a full AI development lifecycle: from vague ideas through research, specifications, and technical plans to atomic task execution by specialized agents (architect, frontend/backend engineers, QA, code reviewer, and more). Every phase transition requires your explicit approval. Automated guardrails — type checking after every edit, build verification, self-repair loops, cross-task contract validation, and constitution enforcement — catch errors before they compound. A crash recovery system preserves partial work, and a wrapper mode lets you use it on client projects with zero AI traces in their repo.

## Philosophy

Your workflow's **hard gates, specialized agents, and automated hooks** as the foundation. Spec-kit's **structured intake** (research → specify → plan → tasks) layered on top for scoping quality.

Every phase transition requires explicit user approval. Optional steps (research, onboard) can be skipped when not needed.

## Installation

```bash
/path/to/AIDevTeamForge/install.sh /path/to/your-project
```

This copies `.claude/`, `specs/`, `bugs/`, `research/`, `scripts/`, and `.mcp.json` into your project (excluding `settings.local.json`, which is project-owned). It also writes `.claude/template-version` to track which version you're on. Then open it in Claude Code and run `/setup-wizard`.

The wizard will:
   - Detect workspace mode (standalone vs wrapper around a client project)
   - Detect your project structure (or interview you for greenfield projects)
   - Ask clarifying questions about your stack
   - Ask whether commits should include AI co-author attribution (default: no)
   - Ask which model each agent tier should use — Think tier (opus), Do tier (sonnet), Verify tier (sonnet); tech-writer is always sonnet
   - Ask how acceptance criteria should be verified — Auto (browser + API with fallback), Browser only, API only, or Off. Auto-detects dev server URL
   - Generate `CLAUDE.md`, `constitution.md`, agents, hooks, and memory
   - Remove the templates directory when done

### MCP Servers

**Context7** — Fetches up-to-date documentation for libraries and frameworks directly into context. Powered by `@upstash/context7-mcp`. Pre-configured in `.mcp.json` for all projects. No setup required — runs via `npx`.

**codebase-memory-mcp** — Local code-intelligence engine: tree-sitter knowledge graph (functions, classes, calls, routes) over 155 languages, queryable via 14 MCP tools (`search_graph`, `query_graph`, `trace_path`, `get_code_snippet`, etc.). Used by `/generate-docs` Phase 3 to gather mechanical fields per concern in a single batched dispatch (Plan E). Pre-configured in `.mcp.json`; binary must be installed first via [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (`curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash`). After install, the binary self-registers on PATH; restart Claude Code so the MCP connection comes up.

**Chrome DevTools** (conditional) — Connects to Chrome/Chromium debugger for screenshots, DOM interaction, and AC verification against the running app. Only added to `.mcp.json` when `/setup-wizard` sets AC verification to "auto" or "browser-only" (frontend/fullstack projects). The script at `scripts/chrome-devtools-mcp.sh` auto-detects the debugging port across JetBrains IDEs, Chrome, and manual launches (macOS, Linux, WSL). Set `CHROME_DEBUG_PORT` env var to override detection.

## Updating Projects

When the template is improved, you can push updates to projects that already use it — without destroying project-specific customizations (CLAUDE.md, constitution.md, agents, memory, specs).

```bash
# From the template repo, pointing at a target project
./update.sh /path/to/target-project

# Preview changes without modifying anything
./update.sh --dry-run /path/to/target-project

# Skip the confirmation prompt
./update.sh --force /path/to/target-project
```

### What gets updated vs. preserved

| Category | What happens | Examples |
|----------|-------------|----------|
| **Template-owned** | Overwritten with latest version | Commands (`.claude/commands/`), manifest, scripts |
| **Three-way merge** | Template diff applied, all project customizations preserved | `CLAUDE.md`, Agents (`.claude/agents/`) — uses `git merge-file` with baselines to apply only what changed in the template |
| **Project-owned** | Never touched | `constitution.md`, `.claude/project-config.json`, memory, specs, docs |
| **Merge files** | Smart-merged (union of keys/lines) | `.mcp.json` (new servers added), `.gitignore` (new entries added) |
| **Copy if missing** | Copied only if absent | New files added to the template that projects don't have yet |

### Project config

`/setup-wizard` writes `.claude/project-config.json` with all template variable values (framework, language, architecture, model tiers, etc.). `update.sh` reads this file to apply placeholder substitution when updating agents and CLAUDE.md. For projects that predate this feature, the update script auto-extracts values from the existing `CLAUDE.md` and agent files as a one-time migration.

### Three-way merge

Agents and CLAUDE.md use three-way merge (`git merge-file`) to apply only the template diff while preserving all project customizations — wizard-added framework-specific items, custom sections, and manual edits. Baselines (snapshots of the substituted template) are stored in `.claude/agents/.baseline/` and `.claude/.baseline/`. The setup wizard saves baselines during generation, so the very first `update.sh` run can three-way merge immediately — no bootstrap needed.

### Version tracking

Each project stores its template version in `.claude/template-version`. The update script compares this with the template's current version and shows the relevant changelog entries before applying changes.

Requires `jq` for JSON merging and `perl` for placeholder substitution (both pre-installed on macOS and most Linux distributions).

## Workflow

### One-Time Setup

Run these once when you first install the template:

```
/setup-wizard → /constitute → /onboard
```

- **`/setup-wizard`** — Interactive wizard. Auto-detects stack for existing codebases, interviews for greenfield. Generates CLAUDE.md, agents, settings, memory, constitution stub. Detects DEFAULT_BRANCH. Conditionally adds Chrome MCP for frontend projects.
- **`/constitute`** — Deep codebase analysis (existing) or preference-based interview (greenfield). Produces `constitution.md` — non-negotiable rules, architecture decisions, patterns.
- **`/onboard`** — (Existing projects only) Deep scan that generates comprehensive `docs/` via tech-writer agent. The knowledge base for all agents. Skip for greenfield (docs built incrementally).

### Feature Development (repeat per feature)

```
/specify → /plan → /breakdown → /execute-task (×N) → /review → /verify → /summarize → /finalize
  ↑ approve    ↑ approve    ↑ approve      per task       per feat   per feat   per feat    per feat
```

- **`/specify "feature description"`** — Structured 9-section feature spec authoring. Hard-gated on the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). Phase 0 preflight + branch detection + session-state reset. Phase 1 reads 7 mandatory input sources (constitution + MEMORY + CLAUDE + docs/ + research/ + discover/ + specs/) with path-based source tagging (no content parsing). Phase 1.5 enumerates structured findings per source (≥3 bullets or N/A marker — REQUIRED INTERMEDIATE OUTPUT). Phase 2 surfaces decision points across 7 categories (`scope_boundaries`, `existing_behavior`, `data_flow_state`, `edge_cases`, `ui_ux_details`, `breaking_changes`, `tooling_configuration`) with C-strict auto-vs-interactive mode detection (env var / `--auto` flag / `<system-reminder>` substring); interactive uses AskUserQuestion (single-line) with markdown fallback; auto records `[default applied]` for user review at Phase 5; per-DP 3-follow-up turn cap. Phase 3 classifies the spec into 5 types (`migration_tooling` / `feature_addition` / `bug_fix` / `refactor` / `greenfield_feature`) with `/discover` path pre-seeding `greenfield_feature`; per-type mandatory-read slot tables + CBM / Glob / Grep discretionary exploration + MEMORY.md cross-reference. Phase 4 renders the 9-section spec via setters with 7-subsection AC categorization, EARS-validated statements (5 variants; §5.1 + §5.7 Ubiquitous-only + verification-command required), Phase 1.5 coverage rule (every finding lands in AC / Constraint / OOS / Risk), numerical-consistency check, non-blocking constitution-recheck. Phase 5 hard-gate approval via deterministic 4-bullet summary + manual-next-step `/plan` block (no automated handoff — user restarts Claude Code, copies the embedded `/plan specs/NNN-feature-name/spec.md` line). State at `.devforge/specify-state.json`. Saves to `specs/NNN-<feature-name>/spec.md` + auto-creates `spec/NNN-<short-desc>` branch when on default. **Requires approval.**
- **`/plan`** — Technical plan: architecture, data model, API contracts, research. Signal-based research (Context7 first for libraries, WebSearch for comparisons) — only triggers for things NOT already in the project. Cross-references plan against spec ACs before presenting. **Requires approval.**
- **`/breakdown`** — Ordered atomic tasks with dependencies, agent assignments (via shared `_agent-assignment.md`), and cross-task contracts (Expects/Produces). Review checkpoints at convergence points. **Requires approval.**
- **`/execute-task`** — 6-phase per-task workflow: load context → pre-flight (contracts) → execute (agent + verify + code review) → complete → bookkeeping. Code review findings reported to user per task. WIP commits accumulate — squashed by `/finalize`.
  - `/execute-task` — next pending | `/execute-task 3` — specific | `/execute-task 1-5` — range | `/execute-task all` — all pending
- **`/review`** — Expert code review: security (security-reviewer) + performance (performance-analyst) + test assessment (qa-engineer). Produces structured findings saved to `specs/[feature]/review.md`. No verdict — findings only.
- **`/verify`** — AC verification + cross-task integration check. Incorporates `/review` findings if available. Renders verdict (APPROVED/NEEDS WORK/REJECTED). Issues reported with batch bug filing.
- **`/summarize`** — PR-ready feature summary. Run after `/verify` approves, before `/finalize`.
- **`/finalize`** — Feature documentation (tech-writer) + feature squash via `git merge-base`. The last step before creating a PR.

### Standalone Commands (use anytime)

```
/fix "bug description"         ← small bugs (1-5 files)
/fix bugs/003-null-check.md   ← fix from bug backlog
/refactor path/to/file.ts     ← behavior-preserving restructuring
/security src/api/             ← security review (file, dir, or --full for codebase)
/audit                         ← adversarial whole-codebase audit (periodic, after several specs)
/report-bug "description"     ← log a bug for later
/refresh-docs                  ← update stale documentation
/research "topic or idea"      ← codebase investigation (bug or enhancement)
/discover "feature idea"        ← greenfield-feature discovery (pre-/specify)
```

- **`/fix`** — Diagnose → delegate to agent → verify → code review → test assessment → doc update. Accepts enriched bug files with AC/expected/actual behavior context. Self-contained (own squash, own docs). Escalates to `/specify` if scope > 5 files.
- **`/refactor`** — Analyze 9 categories → propose (partial approval supported) → delegate to agent → verify → code review → test assessment → doc update. Auto-selects agent by file layer. Self-contained. Escalates to `/specify` if scope > 5 files.
- **`/security`** — On-demand security review. Target a file, directory, uncommitted changes, or full codebase (`--full`). Launches security-reviewer agent with constitution context. Reports Critical/High/Medium/Info with CWE identifiers and remediation. Read-only.
- **`/audit`** — Standalone adversarial whole-codebase audit for periodic "second opinion" quality reviews. Launches code-reviewer, architect, qa-engineer, and security-reviewer in **adversarial mode** with a structured Mislogic Hunt Checklist (naming lies, lying comments, off-by-one, cross-file contradictions, dead branches, contradictory configs, etc.). Reads recent `specs/*/review.md` to track recurring/unresolved issues across features. Anti-hallucination grounding: every finding must include a verbatim quote from the actual code; ungrounded findings are discarded by Phase 4 validation. Writes dated reports to `audits/YYYY-MM-DD-audit.md`. Read-only, not auto-committed, **not part of any workflow chain** — invoke manually after several specs ship.
- **`/report-bug`** — Creates structured bug file in `bugs/` with status lifecycle (Open → In Progress → Fixed).
- **`/refresh-docs`** — Lightweight doc update using git delta. Tech-writer in Refresh Mode.
- **`/research`** — Investigate a bug or enhancement against the codebase. Hard-gated on the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). Phase 0 clarifies the symptom across 6 rubric dimensions (auto-detects bug vs enhancement). Phase 1 walks the codebase-memory-mcp graph + `docs/` corpus in the main thread (no subagent dispatch) with a mandatory `search_graph` → `search_code` fallback chain, a parallel-pattern sweep over the primary file (catches sibling buggy blocks), and ≥2 falsifiable hypotheses. Phase 2 composes a structured report (mode-aware verdict, root-cause hypothesis, runtime-probe recommendation, approaches, complexity). Phase 3 saves to `research/YYYY-MM-DD-<topic-slug>.md` with a copy-pasteable `/specify` handoff block.
- **`/discover`** — Greenfield-feature discovery (parallel to `/research`, but for features with no existing related code yet). Same 4-command hard gate. Phase 0 pre-flight + CBM index refresh. Phase 1 scopes the idea across 8 rubric dimensions (`functional_scope`, `users`, `inputs_outputs`, `integration_points`, `constraints`, `non_goals`, `success_criteria`, `edge_cases`) with bounded turns (3 follow-ups/dim), pre-rubric `references` capture, helper-side direct-conflict detection + LLM-side drift classification, and `[NEEDS CLARIFICATION]` gap markers on accepted partial exit. Phase 2 runs three sequential orchestrator-inline steps: **Step 2.0** project-wide internal canonical-pattern search (mandatory — scans `search_graph` + `search_code` for `functional_scope` capability verbs and records `internal:<path>` prior-art entries BEFORE any web call); **Step 2.1** web survey (WebSearch + Context7 + WebFetch) narrowed to GAP capabilities only; **Step 2.2** fit-check via docs layer + CBM structural chain reconciling user-belief vs codebase-reality, with mandatory `--module-path` grounding from CBM result rows. Phase 3 composes the report (prior art, integration surface, fit assessment, 2-3 design options, build-vs-buy, derisk plan, constitution constraints) with verdict-flip rule (Strained/Misfit fit OR Major-refactor effort → `Reconsider` unless override recorded) AND invariant G cite-rule (when `internal:` prior-art exists, `recommended_option.rationale` must cite at least one internal path — forces "extend existing" framing). Saves to `discover/YYYY-MM-DD-<topic-slug>.md` with a copy-pasteable `/specify` handoff block when verdict allows proceeding.

## Artifact Storage

```
research/
  YYYY-MM-DD-topic-slug.md         # Research reports (/research) — bug/enhancement against existing code

discover/
  YYYY-MM-DD-topic-slug.md         # Discovery reports (/discover) — greenfield feature, pre-/specify

specs/
  001-user-auth/                 # Numbered feature directories
    spec.md                      # /specify output
    plan.md                      # /plan output
    research.md                  # /plan research (optional)
    data-model.md                # /plan entities (optional)
    contracts.md                 # /plan API contracts (optional)
    tasks/                       # /breakdown output
      README.md                  # Task index + dependency graph
      001-define-types.md        # Individual task files
      002-create-repository.md
      003-build-login-form.md

bugs/
  001-null-cart-total.md         # Bug reports (/report-bug or /verify triage)
  002-missing-auth-check.md      # Status: Open → In Progress → Fixed
```

- Feature dirs: `NNN-kebab-name` — sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md` — sequential within feature
- Bug files: `NNN-short-description.md` — sequential, standalone
- Everything for a feature lives in one directory
- Full storage rules in `.claude/templates/storage-rules.md`

## Hard Gates

| Transition | Gate |
|-----------|------|
| setup-wizard → constitute | User confirms generated config |
| constitute → onboard | User approves constitution |
| onboard → specify | Docs generated (existing) or skipped (greenfield) |
| specify → plan | User approves spec |
| plan → breakdown | User approves technical plan |
| breakdown → execute | User approves task list |
| execute → verify | Automated hooks must pass |
| verify → done | User confirms acceptance criteria met |

## Automated Guardrails

- **PostToolUse hooks**: Type checking runs after every file edit
- **Build verification**: Runs the project's Type Check Command, Lint Command, and Build Command after each task to catch type errors, style violations, and bundler-specific failures
- **Self-repair loop**: When verification catches errors (tsc, lint, or build), a repair agent automatically fixes them (up to 3 attempts) before escalating
- **Persistent memory**: Lessons learned carry across sessions
- **Agent specialization**: Domain-specific agents, not generic ones
- **Minimal changes rule**: Every task touches as little code as possible
- **Mandatory linting**: Must pass before task completion
- **Constitution compliance**: Checked in pre-flight before every task — commands guard against empty `constitution.md` and prompt the user to run `/constitute` first
- **Cross-task contracts**: Each task declares what it expects (preconditions) and produces (postconditions). Preconditions are verified before execution; postconditions after. Contract violations stop execution with upstream tracing
- **Review checkpoint gates**: Auto-placed at dependency convergence points and layer boundaries. User reviews preceding work before continuing in batch mode
- **Commit convention**: All commits follow Conventional Commits format. AI co-author attribution is off by default — no `Co-Authored-By` trailers, no AI mentions in commit messages. Opt-in during `/setup-wizard`. All workflow commits use scoped `git add` (specific files only, never `git add -A`)
- **Pre-squash safety check**: Before squashing WIP commits, workflows verify no commits were pushed to the remote — skips squash if history was already shared
- **Auto-compact**: In batch execution, pauses and prompts user-initiated compaction at heavy context load to prevent degradation

## Pre-Populated Universal Rules

The constitution template comes with universal rules that apply to ALL projects regardless of language or framework. `/constitute` preserves these verbatim and only populates project-specific sections:

**Code Quality**: No dead code, no debug artifacts, no magic values, one function one job, early returns, keep functions short, consistent style within files.

**ALWAYS**: Read before write, handle both success and error paths, validate at boundaries, name things for what they are, test assumptions.

**NEVER**: Swallow errors silently, commit secrets, leave bare TODOs, modify outside task scope, guess at behavior.

**PREFER**: Explicit over implicit, composition over inheritance, flat over nested, boring over clever, existing patterns over new ones, small PRs over large.

**Workflow**: Minimal changes, semantic understanding before renaming, read-first principle, document new code, check constitution and memory before every task.

Project-specific rules (architecture, naming conventions, type safety, testing, domain rules) are populated by `/constitute`.

## Wrapper Mode

Use wrapper mode when the Claude orchestration layer must wrap around an existing client project folder (a separate git repo) — keeping AI usage invisible to the client.

```
my-workspace/                    # Wrapper (your git repo)
├── .claude/                     # Commands, agents, memory
├── CLAUDE.md                    # Project config (Project Root = client-project)
├── constitution.md              # Project constitution
├── specs/                       # Feature specifications
├── docs/                        # Documentation
├── .gitignore                   # Ignores client-project/
└── client-project/              # Client's project (client's git repo, zero AI traces)
    ├── src/
    ├── package.json
    └── ...
```

### How it works
- All Claude artifacts stay in the wrapper root — nothing leaks into the inner project
- All source scanning (`/constitute`, `/onboard`, agents) targets the inner folder
- Git auto-commits apply to both repos — wrapper gets workflow commits, source repo gets per-task WIP commits that are squashed into one clean commit (`[TICKET-ID] - Description`, extracted from source branch name) when `/verify` approves the feature (or at `/fix`/`/refactor` final commit)
- `/execute-task` verifies no Claude artifacts were created inside the inner project

### Setup
Run `install.sh`, then `/setup-wizard`. The wizard auto-detects nested git repos, confirms wrapper mode with you, and asks about adding the inner folder to `.gitignore`.

## Greenfield Support

Works with empty/new projects:
- `/setup-wizard` interviews you about intended stack instead of scanning code
- `/constitute` builds constitution from user preferences + framework best practices
- `/specify` creates specs even when there's no existing code to reference
- `/plan` follows the constitution's scaffolding guide for file placement
- `/breakdown` includes infrastructure tasks (create directories, install packages)

## Customization

After running `/setup-wizard`:
- `.claude/agents/*.md` — Add domain-specific knowledge
- `.claude/memory/MEMORY.md` — Pre-seed with known patterns
- `CLAUDE.md` — Adjust workflow steps
- `constitution.md` — Add project-specific rules
- `.claude/settings.json` — Modify hooks and plugins
- `docs/` — Project documentation. Implementing agents write inline docs (JSDoc/docstrings) per task; tech-writer generates feature-level docs at `/verify` time

## Template Files

The `.claude/templates/` directory contains raw templates with `{{PLACEHOLDER}}` variables. Consumed by `/setup-wizard` and can be deleted after setup.
