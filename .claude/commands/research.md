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
/research (optional) → /clarify (optional) → /specify → /plan → /breakdown → /execute-task → /verify
```

`/research` is NOT mandatory. Skip it when you already know what you want to build. Use it when:
- You have a half-formed idea and want a quick feasibility check
- You're unsure whether something already exists in the codebase
- You want to compare approaches before writing a spec
- You need to validate that an idea fits the project's architecture

### /research vs /clarify vs /specify

| Command | Input | Purpose | Output |
|---------|-------|---------|--------|
| `/research` | Vague idea or topic | Does this fit? What exists? What are the options? | Feasibility report |
| `/clarify` | Known feature, unclear details | Resolve ambiguities about a specific feature | Clarifications file |
| `/specify` | Clear feature description | Create a formal contract with acceptance criteria | Spec file |

## PHASE 1: Load Context

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, scope all codebase scanning to that path.

1. Read `constitution.md` for architecture constraints and NON-NEGOTIABLE rules
2. Read `.claude/memory/MEMORY.md` for lessons from past work in related areas
3. Read `CLAUDE.md` for project structure, tech stack, and available patterns
4. Read `docs/architecture.md` if it exists — for current architecture patterns
5. Scan `specs/` directory names to check if this topic overlaps with an existing or in-progress feature
6. Parse `$ARGUMENTS` for the research topic. If empty, use AskUserQuestion to ask what the user wants to investigate.

If an existing spec already covers this topic, inform the user and ask whether they want to proceed with research anyway or work with the existing spec.

## PHASE 2: Codebase Investigation

### Step 1: Keyword Extraction

From the user's description, extract 3-7 search terms:
- Technical terms (e.g., "cache", "WebSocket", "auth")
- Domain concepts (e.g., "payment", "notification", "user role")
- Library/tool names (e.g., "Redis", "Socket.io", "JWT")
- Pattern names (e.g., "middleware", "event bus", "repository")

### Step 2: Codebase Search

For each keyword:
- Use Grep to find occurrences in source files
- Use Glob to find files with related names
- Read the most relevant files (up to 10 total across all keywords)

Map what you find:
- **Existing infrastructure**: What code already relates to this idea?
- **Patterns in use**: How does the codebase handle similar concerns?
- **Reusable abstractions**: Are there utilities, base classes, or patterns that could be extended?
- **Related dependencies**: What packages/services are already in use that relate?

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

### Step 2: Web Research

For each signal detected:
- Use WebSearch to find current best practices and proven approaches
- Compare 2-3 alternatives with brief pros/cons
- Check: maintenance status, community adoption, compatibility with project stack
- Keep it concise — this is a feasibility check, not a full evaluation

## PHASE 4: Generate Research Report

Generate the full report and **render it directly in the console** so the user can read it immediately. Do NOT save to a file yet — saving happens in Phase 5 after user confirmation.

### Report Format

```markdown
# Research: [Topic Name]

**Date**: [YYYY-MM-DD]
**Topic**: [user's original description]
**Verdict**: Feasible | Feasible with Caveats | Not Recommended

## Summary

[3-5 sentences: what the idea is, whether it fits the project, and the recommended direction]

## Codebase Findings

### Existing Related Code
| Area | Files | Relevance |
|------|-------|-----------|
| [module/area] | [file paths] | [how it relates] |

### Patterns Available
- [Pattern]: [how it could be leveraged]

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

- **Proceed**: "Run `/specify "[refined description]"` to create a formal specification."
- **Clarify first**: "Run `/clarify "[specific aspect]"` to resolve [uncertainties] before specifying."
- **Not recommended**: "[Reason]. Consider [alternative] instead."
```

## PHASE 5: Ask to Save & Recommend

The full report was already displayed in Phase 4. Now ask the user whether to save it.

### Step 1: Ask to Save

Use `AskUserQuestion` to ask: **"Save this research to a file?"**

- **If yes**: Save to `research/YYYY-MM-DD-[topic-slug].md` at project root.
  - `YYYY-MM-DD` = current date (e.g., `2026-03-25`)
  - `[topic-slug]` = lowercase kebab-case, 2-4 words derived from the topic (e.g., `caching-strategy`, `websocket-real-time`, `authentication-options`)
  - Create the `research/` directory if it doesn't exist
  - If a file at that path already exists, append `-2`, `-3`, etc. (e.g., `24-03-26-caching-strategy-2.md`)
  - Confirm: `Saved to research/[filename].md`
- **If no**: Do nothing. The research stays in the console only.

### Step 2: Next Steps

Present next steps to the user:

```
Next steps:
- To proceed: `/specify "[refined description]"`
- To clarify first: `/clarify "[specific aspect]"`
- To research deeper: `/research "[narrower sub-topic]"`
- To shelve: no action needed
```

Tailor the next steps to the verdict. If not recommended, lead with the alternative. If feasible, lead with `/specify`.

## IMPORTANT RULES

1. **Lightweight, not exhaustive** — this is a quick check, not a full analysis. Aim for useful in minutes, not hours.
2. **Signal-based external research** — do not web search unless signals justify it. Simple ideas that only touch existing codebase patterns need no external research.
3. **No code modifications** — this command only reads and reports. No file edits, no branches, no commits.
4. **Constitution awareness** — all feasibility assessments must account for architecture rules and NON-NEGOTIABLE constraints.
5. **Check for duplicates** — scan `specs/` for existing features that overlap. Don't research what's already specified.
6. **Recommend concretely** — always suggest a specific next command with a refined description the user can copy-paste.
7. **Consult memory** — check `MEMORY.md` for lessons, gotchas, or decisions about similar areas.
8. **Concise over comprehensive** — the report should help the user decide quickly. Trim anything that doesn't aid the decision.