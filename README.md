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
| **codebase-memory-mcp** | Code knowledge graph (used by `/generate-docs`, `/research`, `/implement`) | install separately — see below |
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

To push template improvements to an already-installed project without clobbering your customizations:

```bash
./update.sh /path/to/your-project        # add --dry-run to preview, --force to skip the prompt
```

## Flow

```
Setup (once):     /init-forge → /generate-docs → /configure → /constitute

Per feature:      /research OR /discover → /specify → [/spec-check] → /plan → [/grill] → /breakdown
                    → /implement → /review → /verify → /summarize → /finalize

Standalone:       /audit   /report-bug   /fix   /pr-review
```

Each arrow is a user-approved gate. `[/spec-check]` is optional (opt-in, proves the spec's acceptance criteria don't contradict each other before planning). `[/grill]` is optional (opt-in, for high-stakes plans). `/fix` is not a linear step — it's a proposal-only remediation loop the model offers off `/review`/`/verify`.

## Commands

### Setup (run once per project)

- **`/init-forge`** — Bootstrap: detect workspace mode (standalone vs wrapper), project root, default branch, project state.
- **`/generate-docs`** — Build the `docs/` knowledge base from the indexed codebase (concern → package → project tiers). The shared context for all agents.
- **`/configure`** — Populate the project config, prune the agent roster to the project's stacks, substitute `{{KEY}}` template placeholders.
- **`/constitute`** — Produce `constitution.md`: non-negotiable rules, architecture decisions, patterns. Deep codebase analysis for existing projects; interview for greenfield.

### Per-feature pipeline

- **`/research "topic"`** — Investigate a bug or enhancement against existing code → research handoff. Intake lane for `/specify`. On save it allocates the feature dir `specs/NNN-name/` and the `spec/NNN-name` branch, and writes its report + handoff there.
- **`/discover "idea"`** — Survey a greenfield feature (internal prior art + web) → discovery handoff. The other intake lane for `/specify`. Allocates the feature dir + branch on save, same as `/research`.
- **`/specify "feature"`** — Author a 9-section spec with EARS acceptance criteria → `specs/NNN-name/spec.md`, written into the feature dir intake allocated. Blocks until a pending research/discover handoff exists.
- **`/spec-check`** *(optional)* — SMT consistency prover for the spec's acceptance criteria: formalizes each AC and proves (via Z3) whether they contradict each other → `spec-check.md`. Recommends CONSISTENT / REVISE-SPEC / DISMISS; you check the translation and own the verdict. A consistency prover, not a mind-reader. Needs `z3-solver` (opt-in pip dep, not installed by default).
- **`/plan`** — Technical plan from the approved spec: architecture, data model, API contracts, research → `plan.md`.
- **`/grill`** *(optional)* — Design-time adversarial review of `plan.md` before decomposition. Recommends PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; you own the verdict.
- **`/breakdown`** — Ordered atomic tasks with dependencies, agent assignments, and Expects/Produces contracts → `tasks/`.
- **`/implement`** — Drain tasks one at a time: assigned agent → scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → per-task hard gate before commit.
- **`/review`** — Feature-level emergent cross-task review over the assembled diff (the issues per-task review can't see) → findings-only `review.md`.
- **`/verify`** — Verify ACs + assembled mechanical checks + regression gate, fold in `/review` findings → single verdict (APPROVED / NEEDS WORK / REJECTED).
- **`/summarize`** — PR-ready feature narrative: what was built, change stats, key decisions, AC status → `summary.md`.
- **`/finalize`** — Surgical `docs/` updates + squash WIP commits into one clean feature commit. Last step before opening a PR.

### Standalone (use anytime)

- **`/audit`** — Adversarial whole-codebase quality review (mislogic + system design + best practices + duplication + constitution). Refutation-gated, grounded in verbatim code quotes.
- **`/report-bug "desc"`** — Log a bug to `bugs/NNN-*.md` (Open → In Progress → Fixed lifecycle). Pure capture, no agent.
- **`/fix`** — Proposal-only remediation loop off `/review`/`/verify` findings, run through `/implement`'s gates. The model offers it; you invoke it.
- **`/pr-review <PR#>`** — Personal-overlay review of a foreign GitHub PR (AI-slop + blast-radius + scope-drift).

## Artifact layout

```
specs/NNN-feature/                     bugs/NNN-slug.md
  research-report.md research-handoff.json     (/research lane)
  discovery-report.md discover-handoff.json    (/discover lane)
  spec.md plan.md tasks/ review.md verification.md summary.md
audits/  YYYY-MM-DD-audit.md
```

## More docs

Detailed guides (agent roster, forcing functions, wrapper mode, handoff contracts) are coming. For now, framework internals live in `CLAUDE.md`, `DEVELOPMENT-STATUS.md`, and `CHANGELOG.md`.
