# Claude Hybrid Template

A spec-driven development template for Claude Code that combines structured specification workflow with enforced execution quality.

## Philosophy

Your workflow's **hard gates, specialized agents, and automated hooks** as the foundation. Spec-kit's **structured intake** (clarify → specify → plan → tasks) layered on top for scoping quality.

Every phase transition requires explicit user approval. No step can be skipped.

## Installation

```bash
# Standard installation
/path/to/claude-hybrid-template/install.sh /path/to/your-project

# Wrapper mode (for client-invisible AI usage)
/path/to/claude-hybrid-template/install.sh --wrapper /path/to/workspace inner-project-folder
```

This copies `.claude/`, `specs/`, `scripts/`, `.mcp.json`, and `update.sh` into your project. It also writes `.claude/template-version` to track which version you're on. Then open it in Claude Code and run `/setup-wizard`.

The wizard will:
   - Detect workspace mode (standalone vs wrapper around a client project)
   - Detect your project structure (or interview you for greenfield projects)
   - Ask clarifying questions about your stack
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
| **Template-owned** | Overwritten with latest version | Commands (`.claude/commands/`), templates, scripts, `update.sh` |
| **Project-owned** | Never touched | `CLAUDE.md`, `constitution.md`, agents, memory, specs, docs |
| **Merge files** | Smart-merged (union of keys/lines) | `.mcp.json` (new servers added), `.gitignore` (new entries added) |
| **Copy if missing** | Copied only if absent | New files added to the template that projects don't have yet |

### Version tracking

Each project stores its template version in `.claude/template-version`. The update script compares this with the template's current version and shows the relevant changelog entries before applying changes.

Requires `jq` for JSON merging (`brew install jq` on macOS, `apt install jq` on Linux).

## Workflow

```
/setup-wizard → /constitute → /onboard → /clarify → /specify → /plan → /breakdown → /execute-task → /verify
   (once)         (once)       (once)    (optional)  (per feat)                      (per task/batch)  (per feat)
```

### Phase 0: `/setup-wizard` (one-time)
Interactive wizard that adapts the template to your project. Auto-detects stack for existing codebases, interviews you for greenfield projects. Generates all config files.

### Phase 1: `/constitute` (one-time)
Deep codebase analysis (existing projects) or preference-based interview (greenfield) that produces `constitution.md` — non-negotiable rules, architecture decisions, patterns. Persists across sessions.

### Phase 1.5: `/onboard` (one-time, existing projects only)
Deep codebase scan that generates comprehensive documentation in `docs/`. Delegates to the tech-writer agent, which uses subagents for large codebases to stay within context limits. Produces `overview.md`, `architecture.md`, `features/*.md`, and `api/*.md` — the knowledge base all agents read before executing tasks. Skip for greenfield projects (docs are built incrementally).

### Phase 2: `/clarify "feature description"` (optional, per feature)
Scans requirements against 9 ambiguity categories, asks up to 5 multiple-choice questions with recommendations. Saves to `specs/[feature]/clarifications.md`. Skip if requirements are already clear.

### Phase 3: `/specify "feature description"` (per feature)
Produces a structured specification with acceptance criteria, scope boundaries, and risk assessment. Saves to `specs/[feature]/spec.md`. **Requires approval.**

### Phase 4: `/plan` (per feature)
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research findings. Saves to `specs/[feature]/plan.md`. **Requires approval.**

### Phase 5: `/breakdown` (per feature)
Takes an approved plan and generates ordered, atomic tasks with dependencies and agent assignments. Saves to `specs/[feature]/tasks/`. **Requires approval.**

### Phase 6: `/execute-task` (per task or batch)
Picks up a task (or multiple tasks), reads relevant docs for context, selects the assigned agent, executes with scope constraints, and verifies. If verification fails, a self-repair agent automatically fixes errors (up to 3 attempts). Then the tech-writer agent updates `docs/`.

Supports multiple execution modes:
- `/execute-task` — next pending task
- `/execute-task 3` — specific task
- `/execute-task 1,3,5` — specific tasks sequentially
- `/execute-task 1-5` — range of tasks
- `/execute-task all` — all pending tasks in feature

### Phase 7: `/verify` (per feature)
Code review against the spec's acceptance criteria, cross-referenced with constitution rules. Updates persistent memory with lessons learned.

## Artifact Storage

```
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
```

- Feature dirs: `NNN-kebab-name` — sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md` — sequential within feature
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
- **Self-repair loop**: When verification catches errors, a repair agent automatically fixes them (up to 3 attempts) before escalating
- **Persistent memory**: Lessons learned carry across sessions
- **Agent specialization**: Domain-specific agents, not generic ones
- **Minimal changes rule**: Every task touches as little code as possible
- **Mandatory linting**: Must pass before task completion
- **Constitution compliance**: Checked in pre-flight before every task
- **9-category ambiguity scan**: Catches requirement gaps before implementation
- **Auto-compact**: In batch execution, automatically compacts context at heavy load to prevent degradation

## Pre-Populated Universal Rules

The constitution template comes with universal rules that apply to ALL projects regardless of language or framework. These are ready out of the box — no `/constitute` needed:

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
- Git auto-commits apply to the wrapper repo only — you commit source changes to the client's repo manually
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
