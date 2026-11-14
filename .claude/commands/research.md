# /research — Quick Feasibility & Fit Research

Lightweight pre-step before `/specify`. Use when you have a vague idea or topic and want to quickly check whether it fits the project, what already exists, and what approaches are viable — without committing to a full specification.

## Usage
```
/research "topic or idea"
/research "what about WebSockets for real-time updates?"
/research "caching strategy for API responses"
/research "should we add dark mode?"
```

## Arguments
- `$ARGUMENTS` — The topic, idea, or question to research. Can be vague. If empty, ask the user what they want to investigate.

## Context in the Workflow

```
/research (optional) → /specify → /plan → /breakdown → /execute-task → /review → /verify → /finalize
```

`/research` is optional by default: skip it when you already know what you want to build. A project may make it mandatory before every `/specify` (its `CLAUDE.md` says so); then it runs even for a well-understood request, because its codebase investigation is what finds the code a new spec would otherwise duplicate. Use it when:
- You have a half-formed idea and want a quick feasibility check
- You're unsure whether something already exists in the codebase
- You want to compare approaches before writing a spec
- You need to validate that an idea fits the project's architecture

### /research vs /specify

| Command | Input | Purpose | Output |
|---------|-------|---------|--------|
| `/research` | Vague idea or topic | Does this fit? What exists? What are the options? | Feasibility report |
| `/specify` | Feature description (any clarity level) | Create a formal contract with acceptance criteria | Spec file |

## PHASE 1: Load Context

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, scope all codebase scanning to that path.

1. Read `constitution.md` for architecture constraints and NON-NEGOTIABLE rules
2. Read `.claude/memory/MEMORY.md` for lessons from past work in related areas
3. Read `CLAUDE.md` for project structure, tech stack, and available patterns
4. Read `docs/architecture.md` if it exists — for current architecture patterns
5. Scan `specs/` directory names to check if this topic overlaps with an existing or in-progress feature (a directory named after the request's ticket key is that feature)
6. Parse `$ARGUMENTS` for the research topic. If empty, use AskUserQuestion to ask what the user wants to investigate. Keep `$ARGUMENTS` exactly (or the user's reply when you asked) for the report's `**Request (verbatim)**` block; in autonomous mode, the roadmap row or the description from the conductor's Inputs. Never paraphrase it.
7. **Issue** (when `ISSUE_TRACKER` in `.claude/project-config.json` is `jira` or `github`): if the topic (or, in autonomous mode, the conductor's Inputs) contains matches of `ISSUE_KEY_PATTERN`, read the issue the way `/review-pr` PHASE 1 step 6 does (same keys: `JIRA_MCP_SERVER`, `JIRA_SITE`; in wrapper mode `gh issue view` runs inside the Source Root; the first match the tracker returns is the issue) and fold its summary and description into the topic; copy its description verbatim into the report's `**Request (verbatim)**` block, under the label line `> Issue <KEY> — <title (summary)>:`, preceded by a lone `>` line: the issue says what is wanted, Phase 2 finds what already exists and how to build it. No key in the topic or the Inputs: proceed without an issue; never search for one. The issue cannot be read (tools not available, several Jira sites and no `JIRA_SITE`): proceed without it; the report's `**Issue**` line says why.

If an existing spec already covers this topic, inform the user and ask whether they want to proceed with research anyway or work with the existing spec.

**Autonomous mode** (`_autonomous-mode.md`, point `existing-spec`): return `blocked (existing spec specs/<KEY|NNN>-*)`; the conductor resumes that spec instead.

## PHASE 2: Codebase Investigation

### Step 1: Keyword Extraction

From the user's description, extract 3-7 search terms:
- Technical terms (e.g., "cache", "WebSocket", "auth")
- Domain concepts (e.g., "payment", "notification", "user role")
- Library/tool names (e.g., "Redis", "Socket.io", "JWT")
- Pattern names (e.g., "middleware", "event bus", "repository")

### Step 2: Codebase Search

When `.claude/quality-profile.json` sets `searchScopes`, search only inside them, never the repository root (`python3 scripts/forge/quality_profile.py scopes` prints them minus `generatedDirs`).

For each keyword:
- Use Grep to find occurrences in source files and documentation (`docs/`) — docs may already describe existing functionality related to the topic
- Use Glob to find files with related names (in both source and docs)
- Read the most relevant files (up to 10 total across all keywords)

Map what you find:
- **Existing infrastructure**: What code already relates to this idea?
- **Patterns in use**: How does the codebase handle similar concerns?
- **Reusable abstractions**: Are there utilities, base classes, or patterns that could be extended?
- **Related dependencies**: What packages/services are already in use that relate?
- **Near duplicates**: code that already implements the same rule, calculation, check or query under another name or in another layer. Name each one: a new spec that re-implements it is the defect this phase exists to prevent.

### Step 3: Constitution Check

Cross-reference the idea against constitution rules:
- Does the architecture support this kind of feature? (layer boundaries, dependency rules)
- Are there NON-NEGOTIABLE rules that constrain the approach?
- Does the project's tech stack align, or would this require introducing new technology?
- Are there patterns in the constitution that this idea should follow?

## PHASE 3: External Research (Signal-Based)

**This phase is conditional.** Only run web research when signals justify it.

### Step 1: Signal Scan

Check if the idea involves any of these signals:

| Signal | Example |
|--------|---------|
| External library/package not yet in the project | "add caching with Redis", "use WebSockets" |
| New integration with third-party service or API | "connect to Stripe", "OAuth with Google" |
| Architectural pattern not present in codebase | "add event sourcing", "implement CQRS" |
| Technology the project has never used | "add GraphQL", "use gRPC" |
| Performance technique requiring benchmarks | "server-side rendering", "lazy loading" |

**No signals found** → Skip this phase entirely. The codebase analysis is sufficient.

**1+ signals found** → Continue to Step 2.

### Step 2: Research

For each signal detected, choose the appropriate tool:

**For specific libraries named by the user:**
- Try Context7 first (`resolve-library-id` → `query-docs`) to get current documentation
- If Context7 has no docs for the library, fall back to WebSearch

**For comparing alternatives or architectural patterns:**
- Use WebSearch to find current best practices and proven approaches
- Compare 2-3 alternatives with brief pros/cons
- Check: maintenance status, community adoption, compatibility with project stack

Keep it concise — this is a feasibility check, not a full evaluation

## PHASE 4: Generate Research Report

Generate the full report and **render it directly in the console** so the user can read it immediately. Do NOT save to a file yet — saving happens in Phase 5 after user confirmation.

### Report Format

```markdown
# Research: [Topic Name]

**Date**: [YYYY-MM-DD]
**Investigated at**: [`git rev-parse <ref>` at investigation time, `<ref>` = the binding's `integrationRef`, else `origin/[DEFAULT_BRANCH]`; the report is valid only for the code at this commit]
**Scoped paths**: [the paths Phase 2 searched, so staleness can be checked against them]
**Topic**: [user's original description]
**Issue**: [KEY — summary; `KEY — not read (<reason>)`; omit this line when the topic names no issue]
**Verdict**: Feasible | Feasible with Caveats | Not Recommended
**Request (verbatim)**:
> [the request kept in Phase 1 step 6, word for word; every line prefixed `> `, a blank line as `>`]
>
> Issue [KEY] — [title]:
> [the issue's description from step 7, quoted the same way; omit these lines when no issue was read]

## Summary

[3-5 sentences: what the idea is, whether it fits the project, and the recommended direction]

## Codebase Findings

### Existing Related Code
| Area | Files | Relevance |
|------|-------|-----------|
| [module/area] | [file paths] | [how it relates] |

### Patterns Available
- [Pattern]: [how it could be leveraged]

### Reuse or Extend
| Existing code (symbol, path) | What it already does | Reuse / extend / replace |
|------------------------------|----------------------|--------------------------|
| [symbol] | [behaviour] | [the spec should call it, widen it, or replace it and why] |

"None found" is valid only with the searches that found nothing (scopes and terms).

### Gaps
- [What infrastructure or patterns are missing]

## Constitution Constraints

| Rule | Impact on This Idea |
|------|-------------------|
| [rule reference] | [how it constrains or enables the approach] |

## Approaches

### Option A: [Name]
- **Description**: [1-2 sentences]
- **Pros**: [list]
- **Cons**: [list]
- **Complexity**: Low / Medium / High

### Option B: [Name]
- **Description**: [1-2 sentences]
- **Pros**: [list]
- **Cons**: [list]
- **Complexity**: Low / Medium / High

**Recommended approach**: [Option X] — [one-line rationale]

## External Research

[Only if Phase 3 ran. Otherwise omit this section entirely.]

### Libraries/Tools Evaluated
| Library | Status | Compatibility | Notes |
|---------|--------|---------------|-------|
| [name] | Active/Maintained | Yes/No | [brief] |

### References
- [links to docs or articles consulted]

## Complexity Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Codebase changes | Low/Med/High | [estimated scope] |
| New dependencies | Low/Med/High | [packages/services needed] |
| Risk | Low/Med/High | [what could go wrong] |

## Recommendation

[One of three outcomes with a concrete next step:]

- **Proceed**: "Run `/specify specs/[feature directory]` to create a formal specification." (Not saved: `/specify "[the request, verbatim]"`.)
- **Uncertain areas**: "Run `/specify` the same way — it will ask clarifying questions about [uncertainties] before writing the spec."
- **Not recommended**: "[Reason]. Consider [alternative] instead."
```

## PHASE 5: Ask to Save & Recommend

The full report was already displayed in Phase 4. Now ask the user whether to save it.

### Step 1: Ask to Save

Use `AskUserQuestion` to ask: **"Save this research as feature `specs/<directory>/`?"**, naming the directory it will create. When an issue was read, recommend Yes: an unsaved report's `/specify` line carries only the request, not the issue text.

**Autonomous mode** (`_autonomous-mode.md`, point `research-save`): save it without asking; when the request holds several ticket keys, return `blocked (user gate ticket)` with the keys before creating anything (point `ticket`).

- **If yes**: the report starts the feature's directory and spec branch.
  1. **Directory**: name it by `.claude/storage-rules.md` → "Feature Directories" (the ticket key when the request has one, otherwise the next number; one ticket per feature). When a directory of the same ticket exists and has no `spec.md`, reuse it and overwrite its report (interactive: ask first); one with a `spec.md` is the existing-spec case of Phase 1 step 5.
  2. **Branch**: on the default branch, `git checkout -b spec/<directory>` (`git checkout spec/<directory>` when that branch exists); already on `spec/<directory>`, stay; on any other branch, the three options of `/specify` 0.3 (autonomous point `branch`).
  3. **Write** `specs/<directory>/research-report.md`, then commit it alone (follow the **Commit Convention** section in CLAUDE.md): `git add specs/<directory>/research-report.md && git commit -m "[WIP] Research: <directory>"`.
  4. Confirm: `Saved to specs/<directory>/research-report.md on branch spec/<directory>`
- **If no**: Do nothing. The research stays in the console only.

### Step 2: Next Steps

Present next steps to the user:

```
Next steps:
- To proceed: `/specify specs/[directory]`
- To research deeper: `/research "[narrower sub-topic]"`
- To shelve: no action needed
```

When the report was not saved, the proceed line is `/specify "[the request, verbatim]"`: the request kept in Phase 1 step 6, unchanged, never a refined description. Tailor the next steps to the verdict. If not recommended, lead with the alternative. If feasible, lead with `/specify`.

## IMPORTANT RULES

1. **Lightweight, not exhaustive** — this is a quick check, not a full analysis. Aim for useful in minutes, not hours.
2. **Signal-based external research** — do not web search unless signals justify it. Simple ideas that only touch existing codebase patterns need no external research.
3. **No code modifications** — this command only reads and reports. Its only writes are a saved report, its feature directory, its spec branch and that one commit.
4. **Constitution awareness** — all feasibility assessments must account for architecture rules and NON-NEGOTIABLE constraints.
5. **Check for duplicates** — scan `specs/` for existing features that overlap. Don't research what's already specified.
6. **Recommend concretely** — always suggest a specific next command the user can copy-paste: `/specify` with the saved report's path, or with the request verbatim; never a refined description.
7. **Consult memory** — check `MEMORY.md` for lessons, gotchas, or decisions about similar areas.
8. **Concise over comprehensive** — the report should help the user decide quickly. Trim anything that doesn't aid the decision.