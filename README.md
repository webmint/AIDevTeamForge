# AIDevTeamForge

A spec-driven development template for Claude Code that combines structured specification workflow with enforced execution quality.

Install it into any project — existing or greenfield — and get a full AI development lifecycle: from vague ideas through research, specifications, and technical plans to atomic task execution by specialized agents (architect, frontend/backend engineers, QA, code reviewer, and more). Every phase transition requires your explicit approval. Automated guardrails — type checking after every edit, build verification, self-repair loops, cross-task contract validation, and constitution enforcement — catch errors before they compound. A crash recovery system preserves partial work, and a wrapper mode lets you use it on client projects with zero AI traces in their repo.

## Philosophy

Your workflow's **hard gates, specialized agents, and automated hooks** as the foundation. Spec-kit's **structured intake** (research → specify → plan → tasks) layered on top for scoping quality.

Every phase transition requires explicit user approval. Optional steps (research, onboard) can be skipped when not needed.

## Installation

```bash
# Standard installation
/path/to/AIDevTeamForge/install.sh /path/to/your-project

# Wrapper mode (for client-invisible AI usage)
/path/to/AIDevTeamForge/install.sh --wrapper /path/to/workspace inner-project-folder
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

- **`/specify "feature description"`** — Structured specification with acceptance criteria. Asks clarifying questions as needed (rounds of up to 5, prioritized by impact — no artificial limit). **Requires approval.** Auto-creates `spec/NNN-short-desc` branch.
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
/report-bug "description"     ← log a bug for later
/refresh-docs                  ← update stale documentation
/research "topic or idea"      ← quick feasibility check
```

- **`/fix`** — Diagnose → delegate to agent → verify → code review → test assessment → doc update. Accepts enriched bug files with AC/expected/actual behavior context. Self-contained (own squash, own docs). Escalates to `/specify` if scope > 5 files.
- **`/refactor`** — Analyze 9 categories → propose (partial approval supported) → delegate to agent → verify → code review → test assessment → doc update. Auto-selects agent by file layer. Self-contained. Escalates to `/specify` if scope > 5 files.
- **`/security`** — On-demand security review. Target a file, directory, uncommitted changes, or full codebase (`--full`). Launches security-reviewer agent with constitution context. Reports Critical/High/Medium/Info with CWE identifiers and remediation. Read-only.
- **`/report-bug`** — Creates structured bug file in `bugs/` with status lifecycle (Open → In Progress → Fixed).
- **`/refresh-docs`** — Lightweight doc update using git delta. Tech-writer in Refresh Mode.
- **`/research`** — Investigates codebase + docs/ for related patterns. Signal-based external research (Context7 first). Displays report in console, optionally saves to `research/`.

## Artifact Storage

```
research/
  YYYY-MM-DD-topic-slug.md         # Research reports (/research) — exploratory, pre-spec

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
├── CLAUDE.md                    # Project config (Source Root = client-project)
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

### Setup options
1. **Auto-detect**: Run `install.sh` normally, then `/setup-wizard` — it detects nested git repos and asks
2. **Pre-configure**: `install.sh --wrapper /path/to/workspace inner-folder` — sets up `.gitignore` entry upfront

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
