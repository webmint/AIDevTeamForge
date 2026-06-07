# Agent Authoring Conventions

Standing convention for authoring or editing an agent **source** file in `src/agents/*.md`. Follow it so the fleet stays standardized. This is a reference, not a tutorial — locked decisions live in `15-AGENT-STANDARDIZATION-PLAN.md`; this doc records the shape they settled on.

## Why this file lives here (not in `src/agents/`)

This doc sits at `src/agents-AUTHORING.md`, a **sibling** of `src/agents/`, deliberately NOT inside it. `scripts/generate-agents.py:260` globs `args.src.glob("*.md")` (default `--src src/agents`) and parses **every** match as an agent meta-block source. A `.md` placed inside `src/agents/` would be emitted as a junk agent (or error the build). One level up keeps the doc co-discoverable while staying outside that glob — provably build-inert, no generator change.

Corollary: do not add new `.md` files under `src/agents/` unless they are real agent sources. A new agent source IS a new `.md` in that directory (e.g. `qa-reviewer.md`); anything else goes elsewhere.

## The meta-block contract

Every source opens with a fenced ` ```yaml ` block, then a free-form markdown body. The generator reads the block as semantic data and emits a Claude-native `.claude/agents/<name>.md` (`emit_claude`, `generate-agents.py:168`); the body passes through unchanged as the agent's system prompt. The contract is **fixed** — author to it, never change it.

| Field | Required | Form | Notes |
|---|---|---|---|
| `name` | yes | lowercase-hyphen identifier | Becomes the emitted filename and the `{{AGENT_LIST}}` entry (filename-derived). |
| `description` | yes | non-empty string (see [description form](#description-form-f1)) | Generator errors on empty (`generate-agents.py:215`). |
| `model_tier` | yes | one of `think \| do \| verify \| scan` | Emitted as `model:` — `think→opus`, `do→sonnet`, `verify→sonnet`, `scan→haiku` (`install_defaults.py:30`). Not a placeholder. |
| `tools` | optional | comma-separated list (e.g. `Read, Grep, Glob, Bash`) | Emitted verbatim when non-empty after `.strip()`; **omit to inherit all tools**. See [tools allowlist](#tools-read-only-allowlist-d5). |
| `applies_to` | optional | project-natures list (e.g. `["all"]`) | Consumed by `configure_helper prune-agents`. Claude Code ignores the unknown key. |

Skeleton meta block:

```yaml
name: example-reviewer
description: "Use to <purpose>. Use proactively when <trigger>."
tools: Read, Grep, Glob, Bash
model_tier: verify
applies_to: ["all"]
```

(`tools:` line present only for the 6 pure reviewers; omit it for everyone else.)

## The canonical body skeleton (D-Skeleton)

Fixed section **order** and **names**. Depth varies by role-family, but the names do not. The body opens with a bare identity line (no `##` heading), then the named sections in this order:

1. **Identity** (no heading) — `You are a {role}. {one-line mandate}.` One line. No "elite" / "senior" / "relentless" / "director-of" inflation. A substantive role descriptor is allowed (architect's "a director, not an implementer" is its mandate, not inflation — the ban is on empty seniority adjectives).
2. **`## Core Expertise`** — focus/expertise bullets; `**Field**: {{PLACEHOLDER}}` pairs where stack-specific.
3. **`## Project Paths`** — exactly `{{PROJECT_PATHS}}`. In **every** agent, no exceptions (D2).
4. **`## Approach`** — the working procedure as a numbered list. This one name replaces the old divergent names (`Principles` / `Workflow` / `Phases` / `Testing Philosophy` / `Mandatory Debugging Loop`).
5. **`## Output`** — deliverable contract. Mandatory for pure reviewers (carries unified severity + one verdict vocab); optional for code-only builders.
6. **`## Boundaries & Handoffs`** — own X · defer Y to {named agent} · consult specialists via the orchestrator. In every agent. See [boundaries](#boundaries--handoffs-d-boundaries).
7. **`## Rules`** — numbered. Closes with the constitution + memory, minimal-scope, and grounding conventions (see [Rules closers](#rules-section-closers)).

Skeleton example (minimal reviewer):

```markdown
You are a {role}. {one-line mandate}.

## Core Expertise
- **{Field}**: {{PLACEHOLDER}}
- ...

## Project Paths

{{PROJECT_PATHS}}

## Approach
1. ...
2. ...

## Output
Severity: Critical / High / Medium / Info. Verdict: {one vocab}.
Read-only — report findings, do not modify code.

## Boundaries & Handoffs
- Own: {what this agent does}.
- Defer {X} to `{named-agent}`.
- Consult specialists via the orchestrator (subagents cannot spawn other subagents).

## Rules
1. ...
N. Read `constitution.md` before deciding; check `.devforge/memory.md` for prior lessons.
N+1. Minimal scope — change only what the task requires.
N+2. {grounding rule — verbatim, see below}.
```

`architect` and `tech-writer` keep additional substantive sections **beyond** this skeleton (architect's decision-output format, tech-writer's 3 operating modes). They conform section NAMES and Rules style — they are not flattened to the minimal skeleton.

## The four role-families

The **target** roster is **17** agents in four families (16 exist today; `qa-reviewer` is authored in Phase 1 of `15-AGENT-STANDARDIZATION-PLAN.md`). Membership and how each family's body differs:

### Pure read-only reviewers (6) — tools-locked

`code-reviewer`, `security-reviewer`, `ac-verifier`, `design-auditor`, `performance-analyst`, `qa-reviewer`.

- `tools:` read-only allowlist (`Read, Grep, Glob, Bash` + any read-only MCP the agent genuinely needs). NO `Edit`/`Write`. NO `Agent`.
- `## Output` **mandatory** — carries the [unified severity](#unified-severity-d1) + exactly one verdict vocab.
- Read-only stance stated explicitly in the body (it reports findings; it does not modify code).

### Builders (8) — inherit all tools

`api-designer`, `backend-engineer`, `db-engineer`, `devops-engineer`, `frontend-engineer`, `migration-engineer`, `mobile-engineer`, `qa-engineer`.

- Omit `tools:` (inherit read + write).
- `## Output` optional (a code-only builder may omit it).
- `## Boundaries & Handoffs` names the reviewer/sibling to hand the work off to.
- `qa-engineer` is a pure test-WRITER here; test assessment is `qa-reviewer`'s job.

### Actor (1) — inherits all tools

`runtime-debugger`.

- Omit `tools:` (it runs a fix loop and edits code).
- Builder-style `## Boundaries & Handoffs` (it acts; no reviewer verdict block).
- It never reviews.

### Specials (2) — richer substance allowed

`architect`, `tech-writer`.

- Multi-section substance is preserved. Conform section NAMES and Rules style only; do not flatten.
- `architect` is the **reference implementation** for the Boundaries / specialist-consulting discipline — match its shape when authoring any agent's `## Boundaries & Handoffs`.
- `tech-writer` keeps its 3 operating modes.

## Unified severity (D1)

Any agent that emits findings uses exactly this scale, verbatim:

```
Critical / High / Medium / Info
```

Anchored to `src/devforge/lib/_audit/findings_schema.py:49` (`SEVERITY_ENUM = ("Critical", "High", "Medium", "Info")`). This replaces the old divergent vocabularies (Critical/Warning/Info; high/med/low impact; PASS/FAIL; ADEQUATE/GAPS). Each pure reviewer pairs the severity with **one** verdict vocab in its `## Output`. A pure-builder produces code/tests, not findings, so it carries no severity vocab.

## `tools:` read-only allowlist (D5)

Apply `tools: Read, Grep, Glob, Bash` (plus any read-only MCP genuinely needed) to the **6 pure reviewers** only. Claude Code supports the allowlist (comma-separated; the emitter renders it verbatim).

Omitting `Agent` from the list also blocks subagent-spawning. That matters because **subagents cannot spawn other subagents** — a reviewer with no `Agent` grant cannot try (and silently fail) to call another agent. Builders and the actor omit the whole `tools:` line and inherit everything.

## `description` form (F1)

A concise one-to-two-sentence purpose plus a delegation signal — `Use when…` / `Use proactively` / `Use immediately after…`. Keep it non-empty (the generator errors on empty).

Do NOT embed `user:` / `assistant:` dialogue `Examples:` blocks. They are not a Claude Code convention, and dispatch in this framework is orchestrator-mediated (not model-auto-invocation), so dialogue examples carry no functional weight.

## Constitution + memory convention (F2)

A fixed `## Rules` line, prose — not a new frontmatter field (the meta-block contract is fixed):

> Read `constitution.md` before deciding; check `.devforge/memory.md` for prior lessons.

## Reference the constitution by concept-name, never `§`-number (F3)

Section numbers drift across constitution versions (e.g. template §3.6 "Design Principles" vs a populated §3.6 "Function Length & Simplicity"). Cite the constitution by its section NAME/CONCEPT (e.g. "Patterns & Anti-Patterns material"), never by a `§`-number. A `§`-number reference is a dangling reference waiting to happen.

## The grounding rule (D-Grounding)

Add this as a standard `## Rules` line in every agent, verbatim:

> When the constitution is silent on a convention, ground in real code (CBM / existing files) before acting; apply the dominant observed pattern and flag any inconsistency in your output; never invent a convention from 'framework idiom' alone.

This closes the drift vector that the old weak "follow framework-idiomatic conventions" fallback opened. There must be no "framework idiom"-only fallback left anywhere in the fleet.

## Boundaries & Handoffs (D-Boundaries)

Every agent carries a `## Boundaries & Handoffs` body section. It does three things: it **names what the agent owns**, it **names which other agent(s) it defers specific concerns to** (e.g. defer test assessment to `qa-reviewer`, defer security depth to `security-reviewer`), and it **routes specialist consultation through the orchestrator** — never by calling another agent directly, because subagents cannot spawn other subagents (see [Subagents cannot spawn other subagents](#subagents-cannot-spawn-other-subagents) below).

`architect.md`'s `## Boundaries & Handoffs` + `## Consulting Specialists` is the reference implementation — match its shape in lighter form for every other agent: state the owned scope, list the named deferrals, and emit a consultation request to the orchestrator rather than attempting a direct subagent call.

## Subagents cannot spawn other subagents

An agent that needs specialist depth does NOT call another agent. It **emits a consultation request** — name the specialist, state the specific sub-question, include the context the orchestrator must pass — and the orchestrator relays it. `architect.md` (`## Consulting Specialists`) is the model: identify the sub-question, emit a structured request in the output, treat any relayed response as input (synthesize, never rubber-stamp), and proceed from own reasoning if no response is relayed. Back-port this into `## Boundaries & Handoffs` in lighter form for non-architect agents.

## Rules-section closers

Every agent's `## Rules` list closes with these conventions (combine the order to fit the agent; the wording is fixed):

1. Constitution + memory (F2): *"Read `constitution.md` before deciding; check `.devforge/memory.md` for prior lessons."*
2. Minimal scope: change only what the task requires; no speculative work.
3. Grounding (D-Grounding): the verbatim grounding rule above.

## Authoring checklist

Before declaring an agent source done:

- [ ] Meta block has `name`, `description` (non-empty), `model_tier` ∈ {think, do, verify, scan}.
- [ ] `tools:` present **iff** the agent is one of the 6 pure reviewers (and lists no `Edit`/`Write`/`Agent`); omitted otherwise.
- [ ] Body sections appear in skeleton order with the fixed names; `## Project Paths` carries `{{PROJECT_PATHS}}`.
- [ ] Pure reviewer: `## Output` present with unified severity + one verdict vocab + read-only stance.
- [ ] `## Boundaries & Handoffs` names who it defers to and routes specialist consultation through the orchestrator.
- [ ] `description` has no dialogue `Examples:` block.
- [ ] No `§`-number constitution references; no "framework idiom"-only fallback.
- [ ] `## Rules` closes with the constitution+memory, minimal-scope, and grounding lines.
- [ ] Source parses through `scripts/generate-agents.py` (run it into a scratch `--target`).
- [ ] Edited via `instruction-author` → `instruction-reviewer` (this repo's spec-edit discipline).
