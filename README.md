# AIDevTeamForge

Spec-driven development framework for Claude Code. Install it into any project — greenfield or existing — and get a full AI development lifecycle: vague idea → research → spec → plan → atomic tasks → execution by specialized agents → review → verify → PR-ready feature.

Every phase transition needs your explicit approval. Automated guardrails — type-check/lint/build after each task, self-repair loops, per-task review panels, cross-task contracts, a design-fidelity check, and constitution enforcement — catch errors before they compound. Wrapper mode lets you run it on client projects with zero AI traces in their repo.

## Requirements

| Dependency | Why | Notes |
|---|---|---|
| **bash** + **git** | Install/update scripts, all git workflow | git repo required in the target project |
| **Python 3.8+** | Runtime helpers (`.devforge/lib/*`) | pre-installed on macOS + most Linux |
| **jq** | JSON merge during install/update | pre-installed on macOS + most Linux |
| **Node.js** (`npx`) | Context7 + Chrome DevTools MCP servers | needed for docs-fetch + AC verification |
| **codebase-memory-mcp** | Code knowledge graph (used by `/devforge:generate-docs`, `/devforge:research`, `/devforge:implement`) | install separately — see below |
| Chrome/Chromium w/ remote debugging | Runtime AC + design-fidelity verification | optional; backend-only projects skip it |

**codebase-memory-mcp** — local tree-sitter knowledge graph over 155 languages, queried via MCP (`search_graph`, `trace_path`, `get_code_snippet`, …). Install the binary from [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp):

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

It self-registers on PATH; restart Claude Code afterward. **Context7** and **Chrome DevTools** MCPs are pre-configured in `.mcp.json` and run via `npx` — no manual setup.

## Install

```bash
/path/to/AIDevTeamForge/install.sh /path/to/your-project
```

Copies `.claude/`, `.devforge/`, `docs/`, `CLAUDE.md`, `constitution.md`, and `.mcp.json` into the project. Artifact directories (`specs/`, `bugs/`, `audits/`) are created by the commands that write them. Then open the project in Claude Code and run the one-time setup chain.

Non-English operators can have Claude reply in another language: set the `language` key in `~/.claude/settings.json` (every project on your machine) or in `.claude/settings.local.json` (this project only — Claude Code "keeps it out of git when it creates the file; if you create it by hand, add it to `.gitignore` yourself"). Do not use `.claude/settings.json`, which `install.sh` overwrites. The installed `CLAUDE.md` keeps every file artifact and commit message in English regardless; the setting applies to conversation only.

To push template improvements to an already-installed project without clobbering your customizations:

```bash
./update.sh /path/to/your-project        # add --dry-run to preview, --force to skip the prompt
```

## Flow

```
Setup (once):     /devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute

Per feature:      /devforge:research OR /devforge:discover → /devforge:specify → /devforge:spec-check
                    → /devforge:plan → /devforge:grill → /devforge:breakdown → /devforge:implement
                    → /devforge:review → /devforge:verify → /devforge:summarize → /devforge:finalize

Standalone:       /devforge:audit   /devforge:report-bug   /devforge:fix   /devforge:pr-review
```

Every command is namespaced under `devforge:` so it never collides with a bundled or plugin skill of the same name; the `/` menu is fuzzy-searched, so typing `verify` still surfaces `/devforge:verify`. Thirteen of the twenty are model-invocable — propose one and Claude runs it once you agree. Seven are human-typed only: the four setup commands, `/devforge:grill`, `/devforge:spec-check`, and `/devforge:fix`.

Each arrow is a user-approved gate. `/devforge:spec-check` is required before `/devforge:plan` — you type it (nothing auto-runs it), and `/devforge:plan` blocks until a fresh report for that spec exists; that check is on the report's presence and freshness only, never on its verdict, so you still own every call it raises. `/devforge:grill` is required before `/devforge:breakdown` — you type it too (nothing auto-runs it), and `/devforge:breakdown` blocks until a grill report exists for that plan; that check is on the report's presence and its recorded adversary run only, never on its freshness and never on its disposition, so a KILL report unblocks `/devforge:breakdown` exactly as a PROCEED one does and you still own every call it raises. `/devforge:fix` is not a linear step — it's a proposal-only remediation loop the model offers off `/devforge:review`/`/devforge:verify`.

## Commands

### Setup (run once per project)

- **`/devforge:init-forge`** — Bootstrap: detect workspace mode (standalone vs wrapper), project root, default branch, project state.
- **`/devforge:generate-docs`** — Build the `docs/` knowledge base from the indexed codebase (concern → package → project tiers). The shared context for all agents.
- **`/devforge:configure`** — Populate the project config, prune the agent roster to the project's stacks, substitute `{{KEY}}` template placeholders.
- **`/devforge:constitute`** — Produce `constitution.md`: non-negotiable rules, architecture decisions, patterns. Deep codebase analysis for existing projects; interview for greenfield.

### Per-feature pipeline

- **`/devforge:research "topic"`** — Investigate a bug or enhancement against existing code → research handoff. Intake lane for `/devforge:specify`. On save it allocates the feature dir `specs/NNN-name/` and the `spec/NNN-name` branch, and writes its report + handoff there.
- **`/devforge:discover "idea"`** — Survey a greenfield feature (internal prior art + web) → discovery handoff. The other intake lane for `/devforge:specify`. Allocates the feature dir + branch on save, same as `/devforge:research`.
- **`/devforge:specify "feature"`** — Author a 9-section spec with EARS acceptance criteria → `specs/NNN-name/spec.md`, written into the feature dir intake allocated. Blocks until a pending research/discover handoff exists.
- **`/devforge:spec-check`** *(required before `/devforge:plan`; you type it)* — SMT consistency prover for the spec's acceptance criteria: resolves each criterion's subject against the code, formalizes what resolves, and proves (via Z3) whether the criteria contradict each other → `spec-check.md`. Recommends CONSISTENT / REVISE-SPEC / DISMISS; you check the translation and own every verdict it raises, while a clean result is accepted without asking. `/devforge:plan` blocks until this report exists and still matches the spec — presence and freshness only, never the verdict. A consistency prover, not a mind-reader. Needs `z3-solver` (a one-time `pip install z3-solver`, not installed by the template).
- **`/devforge:plan`** — Technical plan from the approved spec: architecture, data model, API contracts, research → `plan.md`.
- **`/devforge:grill`** *(required before `/devforge:breakdown`; you type it)* — Design-time adversarial review of `plan.md` before decomposition. Recommends PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; you own every verdict it raises, while a run where nothing survived cross-examination is accepted without asking. `/devforge:breakdown` blocks until this report exists for the plan — presence and the recorded adversary run only, never freshness and never the disposition, so a KILL report unblocks it exactly as a PROCEED one does. What is mandatory is that the grill RAN, never that its disposition binds.
- **`/devforge:breakdown`** — Ordered atomic tasks with dependencies, agent assignments, and Expects/Produces contracts → `tasks/`.
- **`/devforge:implement`** — Drain tasks one at a time: assigned agent → scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → per-task hard gate before commit.
- **`/devforge:review`** — Feature-level emergent cross-task review over the assembled diff (the issues per-task review can't see) → findings-only `review.md`.
- **`/devforge:verify`** — Verify ACs + assembled mechanical checks + regression gate, fold in `/devforge:review` findings → single verdict (APPROVED / NEEDS WORK / REJECTED).
- **`/devforge:summarize`** — PR-ready feature narrative: what was built, change stats, key decisions, AC status → `summary.md`.
- **`/devforge:finalize`** — Surgical `docs/` updates + squash WIP commits into one clean feature commit. Last step before opening a PR.

### Standalone (use anytime)

- **`/devforge:audit`** — Adversarial whole-codebase quality review (mislogic + system design + best practices + duplication + constitution). Refutation-gated, grounded in verbatim code quotes.
- **`/devforge:report-bug "desc"`** — Log a bug to `bugs/NNN-*.md` (Open → In Progress → Fixed lifecycle). Pure capture, no agent.
- **`/devforge:fix`** — Proposal-only remediation loop off `/devforge:review`/`/devforge:verify` findings, run through `/devforge:implement`'s gates. The model offers it; you invoke it.
- **`/devforge:pr-review <PR#>`** — Personal-overlay review of a foreign GitHub PR (AI-slop + blast-radius + scope-drift).

## Artifact layout

```
specs/NNN-feature/                     bugs/NNN-slug.md
  research-report.md research-handoff.json     (/devforge:research lane)
  discovery-report.md discover-handoff.json    (/devforge:discover lane)
  spec.md plan.md tasks/ review.md verification.md summary.md
audits/  YYYY-MM-DD-audit.md
```

## More docs

Detailed guides (agent roster, forcing functions, wrapper mode, handoff contracts) are coming. For now, framework internals live in `CLAUDE.md`, `DEVELOPMENT-STATUS.md`, and `CHANGELOG.md`.
