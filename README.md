# AIDevTeamForge

A spec-driven development template for Claude Code that combines structured specification workflow with enforced execution quality.

Install it into any project — existing or greenfield — and get a full AI development lifecycle: from vague ideas through research, specifications, and technical plans to atomic task execution by specialized agents (architect, frontend/backend engineers, QA, code reviewer, and more). Every phase transition requires your explicit approval. Automated guardrails — type checking after every edit, build verification, self-repair loops, cross-task contract validation, and constitution enforcement — catch errors before they compound. A crash recovery system preserves partial work, and a wrapper mode lets you use it on client projects with zero AI traces in their repo.

## Philosophy

Your workflow's **hard gates, specialized agents, and automated hooks** as the foundation. Spec-kit's **structured intake** (research → clarify → specify → plan → tasks) layered on top for scoping quality.

Every phase transition requires explicit user approval. No step can be skipped.

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
   - Ask which model agents should use (default: opus) — applies to 13 agents; tech-writer is always sonnet for speed
   - Generate `CLAUDE.md`, `constitution.md`, agents, hooks, and memory
   - Remove the templates directory when done

### MCP Servers

The template includes two pre-configured MCP servers in `.mcp.json`:

- **Context7** — Fetches up-to-date documentation for libraries and frameworks directly into context. Powered by `@upstash/context7-mcp`. No setup required — runs via `npx`.
- **Chrome DevTools** — Connects to WebStorm's Chrome debugger for taking screenshots and evaluating scripts in the browser. Requires WebStorm JS debugger to be running. The script at `scripts/chrome-devtools-mcp.sh` auto-detects the debugging port.

Both servers are enabled by default in the settings template. Permissions for their tools (`take_screenshot`, `evaluate_script`, `resolve-library-id`, `get-library-docs`) are pre-allowed.

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

`/setup-wizard` writes `.claude/project-config.json` with all template variable values (framework, language, architecture, agent model, etc.). `update.sh` reads this file to apply placeholder substitution when updating agents and CLAUDE.md. For projects that predate this feature, the update script auto-extracts values from the existing `CLAUDE.md` and agent files as a one-time migration.

### Three-way merge

Agents and CLAUDE.md use three-way merge (`git merge-file`) to apply only the template diff while preserving all project customizations — wizard-added framework-specific items, custom sections, and manual edits. Baselines (snapshots of the substituted template) are stored in `.claude/agents/.baseline/` and `.claude/.baseline/`. The setup wizard saves baselines during generation, so the very first `update.sh` run can three-way merge immediately — no bootstrap needed.

### Version tracking

Each project stores its template version in `.claude/template-version`. The update script compares this with the template's current version and shows the relevant changelog entries before applying changes.

Requires `jq` for JSON merging and `perl` for placeholder substitution (both pre-installed on macOS and most Linux distributions).

## Workflow

```
/setup-wizard → /constitute → /onboard → /research → /clarify → /specify → /plan → /breakdown → /execute-task → /verify → /summarize
   (once)         (once)       (once)    (optional)  (optional)  (per feat)                      (per task/batch)  (per feat)  (auto)

/fix "bug description"        ← lightweight shortcut for small bugs (skips spec/plan/breakdown)
/fix bugs/003-null-check.md  ← fix a reported bug from the backlog
/report-bug "description"    ← log a bug for later fixing
/refactor path/to/file.ts    ← focused code restructuring without behavior changes
/refresh-docs                ← update stale documentation (git delta, not full scan)
```

### Phase 0: `/setup-wizard` (one-time)
Interactive wizard that adapts the template to your project. Auto-detects stack for existing codebases, interviews you for greenfield projects. Generates all config files.

### Phase 1: `/constitute` (one-time)
Deep codebase analysis (existing projects) or preference-based interview (greenfield) that produces `constitution.md` — non-negotiable rules, architecture decisions, patterns. Persists across sessions.

### Phase 1.5: `/onboard` (one-time, existing projects only)
Deep codebase scan that generates comprehensive documentation in `docs/`. Delegates to the tech-writer agent, which uses subagents for large codebases to stay within context limits. Produces `overview.md`, `architecture.md`, `features/*.md`, and `api/*.md` — the knowledge base all agents read before executing tasks. Skip for greenfield projects (docs are built incrementally).

### Phase 1.75: `/research "topic or idea"` (optional, per idea)
Quick feasibility check for vague ideas. Investigates the codebase for related patterns, optionally researches external approaches (signal-based — only when the idea involves new libraries, integrations, or unfamiliar tech), and displays the full research report in the console. You're then asked whether to save — if yes, saves to `research/YYYY-MM-DD-[topic-slug].md`. Does NOT create specs, modify code, or create branches. Use before `/specify` when you're unsure whether an idea is viable or how it fits the project's architecture.

### Phase 2: `/clarify "feature description"` (optional, per feature)
Scans requirements against 9 ambiguity categories, asks up to 5 multiple-choice questions with recommendations. Saves to `specs/[feature]/clarifications.md`. Skip if requirements are already clear.

### Phase 3: `/specify "feature description"` (per feature)
Produces a structured specification with acceptance criteria, scope boundaries, and risk assessment. Saves to `specs/[feature]/spec.md`. **Requires approval.** When invoked on the default branch, auto-creates a `spec/NNN-short-desc` branch (incremental numbering, 2-3 word description from the feature name). Skips if already on a `spec/*` branch.

### Phase 4: `/plan` (per feature)
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research findings. Codebase research always runs; deep web research is signal-based — only triggered when the spec references external libraries, third-party integrations, architectural forks, or unfamiliar technology. Saves to `specs/[feature]/plan.md`. **Requires approval.**

### Phase 5: `/breakdown` (per feature)
Takes an approved plan and generates ordered, atomic tasks with dependencies and agent assignments. Each task includes cross-task contracts (Expects/Produces) that are verified during execution to prevent silent error compounding. Review checkpoints are auto-placed at convergence points and layer boundaries. Saves to `specs/[feature]/tasks/`. **Requires approval.**

### Phase 6: `/execute-task` (per task or batch)
Picks up a task (or multiple tasks), reads relevant docs for context, selects the assigned agent, executes with scope constraints, and verifies (tsc, lint, build, done conditions, contract postconditions, affected tests). Contract preconditions are checked before execution — if a prior task's output doesn't match expectations, execution stops with upstream tracing. If verification fails, a self-repair agent automatically fixes errors (up to 3 attempts). At review checkpoints, user reviews preceding work before continuing. Then the tech-writer agent updates `docs/`.

Supports multiple execution modes:
- `/execute-task` — next pending task
- `/execute-task 3` — specific task
- `/execute-task 1,3,5` — specific tasks sequentially
- `/execute-task 1-5` — range of tasks
- `/execute-task all` — all pending tasks in feature

### Phase 7: `/verify` (per feature)
Code review against the spec's acceptance criteria, cross-referenced with constitution rules. Updates persistent memory with lessons learned. Phase 10 (Issue Triage) lets you decide per-issue: fix now (chains into `/fix`), report for later (creates a bug file in `bugs/`), or skip. Automatically triggers `/summarize` when verdict is APPROVED.

### Phase 8: `/summarize` (per feature, auto)
Generates a concise, PR-ready summary of the completed feature. Reads spec, plan, tasks, and git history to produce a structured overview of what was built, files changed, key decisions, and acceptance criteria. Saves to `specs/[feature]/summary.md`. Runs automatically after `/verify` approves — no manual invocation needed.

### `/fix "bug description"` (standalone, for small bugs)
Lightweight bug-fixing workflow that bypasses the full spec→plan→breakdown pipeline. Designed for small, localized bugs (1-5 files). Also accepts bug file paths: `/fix bugs/003-null-check.md` — reads the file, extracts description and file(s), and updates the bug's status to Fixed after completion. Phases: diagnose (with **runtime-debugger** agent for runtime errors), apply minimal fix, verify (tsc + lint + build + self-repair loop), code review (**code-reviewer** agent), test assessment (**qa-engineer** agent). Includes crash recovery, constitution enforcement, and memory updates. If the bug turns out to be larger than expected, recommends escalating to `/specify`.

### `/report-bug "description"` (standalone, for logging bugs)
Creates a structured bug report file in `bugs/` for later fixing. Accepts an optional `--file` flag to link the bug to a specific file and `--severity` flag (Critical/Warning/Info, defaults to Warning). Bug files follow sequential numbering (`001-short-description.md`) with a status lifecycle (Open → In Progress → Fixed). Fix a reported bug with `/fix bugs/NNN-xxx.md` or escalate larger ones with `/specify`.

### `/refactor path/to/file.ts "goal"` (standalone, for code restructuring)
Focused refactoring workflow for behavior-preserving code restructuring (1-5 files). Supports IDE-injected context (active file/selection from WebStorm) or manual file path with optional line range. Phases: analyze code against 9 refactoring categories (long functions, deep nesting, SOLID/DRY violations, type safety, naming, dead code, pattern mismatches, complexity), present detailed proposal with before/after for each opportunity (hard gate — partial approval supported), apply refactoring with auto-selected agent (**architect**, **frontend-engineer**, or **backend-engineer** based on file layer), verify (tsc + lint + build + tests + self-repair loop), code review (**code-reviewer** agent), test assessment (**qa-engineer** agent — tests must pass unchanged since refactoring is behavior-preserving), mandatory documentation update (tech-writer agent evaluates whether docs are needed). If the refactoring grows beyond 5 files, recommends escalating to `/specify`.

### `/refresh-docs` (standalone, for stale documentation)
Lightweight documentation refresh that detects what source files changed since docs were last updated and invokes the tech-writer on just those files. Uses git delta detection — sits between `/onboard` (full codebase scan) and Phase 5 of `/execute-task` (single task). Supports `--since <commit>`, `--module <name>`, and `--all` (delegates to `/onboard`). Captures both committed and uncommitted changes. Includes verification (tsc + lint) and memory update.

## Artifact Storage

```
research/
  YYYY-MM-DD-topic-slug.md         # Research reports (/research) — exploratory, pre-spec

specs/
  001-user-auth/                 # Numbered feature directories
    spec.md                      # /specify output
    clarifications.md            # /clarify output (optional)
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
- **9-category ambiguity scan**: Catches requirement gaps before implementation
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
- `docs/` — Project documentation, updated automatically by tech-writer agent after each task (along with inline JSDoc/docstrings in source files)

## Template Files

The `.claude/templates/` directory contains raw templates with `{{PLACEHOLDER}}` variables. Consumed by `/setup-wizard` and can be deleted after setup.
