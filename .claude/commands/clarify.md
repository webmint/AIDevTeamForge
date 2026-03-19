# /clarify — Structured Requirement Clarification

Optional pre-step before `/specify`. Use when requirements are vague or have many possible interpretations. Resolves ambiguities through structured taxonomy scanning and targeted multiple-choice questions.

## Usage
```
/clarify "topic or feature to clarify"
/clarify specs/[feature-name]/spec.md
```

## Arguments
- `$ARGUMENTS` — A feature description to clarify, OR a path to an existing spec file to refine.

## Context in the Workflow

```
/clarify (optional) → /specify → /plan → /breakdown → /execute-task → /verify
```

`/clarify` is NOT mandatory. Skip it when requirements are already clear. Use it when:
- The feature request is vague ("make it better", "add authentication")
- Multiple reasonable interpretations exist
- The user wants to explore options before committing

## PHASE 1: Load Context

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, scope all codebase scanning to that path.

1. Read `constitution.md` for architecture constraints
2. Read `.claude/memory/MEMORY.md` for related past work
3. If an existing spec is referenced, read it
4. If existing code is relevant, scan it

## PHASE 2: Ambiguity Scan

Evaluate the description against 9 taxonomy categories. Assign each a status: **Clear**, **Partial**, or **Missing**.

| # | Category | What to Check |
|---|----------|---------------|
| 1 | Functional Scope | What's in vs out? Boundaries clear? |
| 2 | Domain Models & Data | Entities, relationships, data shapes defined? |
| 3 | User Interaction Flows | Step-by-step user journeys clear? |
| 4 | Non-Functional Requirements | Performance, accessibility, security? |
| 5 | External Dependencies | Third-party services, APIs, integrations? |
| 6 | Edge Cases & Failures | Error states, boundary conditions, recovery? |
| 7 | Technical Constraints | Architecture layer, patterns, tech choices? |
| 8 | Terminology | Terms used consistently? Ambiguous jargon? |
| 9 | Acceptance Criteria | Completion signals testable and measurable? |

Present a coverage table:

```
| Category              | Status  | Notes |
|-----------------------|---------|-------|
| Functional Scope      | Clear   | ...   |
| Domain Models & Data  | Partial | ...   |
| ...                   | ...     | ...   |
```

If ALL Clear → recommend skipping directly to `/specify`. Done.

## PHASE 3: Targeted Questions

Generate up to **5 questions** from Partial/Missing categories.

**Rules:**
- Multiple-choice only (2-4 options per question)
- Recommend one option with brief rationale (based on constitution, codebase, or best practices)
- Present one at a time using AskUserQuestion
- Priority: scope > architecture > data > UX > edge cases
- If constitution constrains a choice, state it instead of asking
- Follow-up clarifications within one question don't consume the 5-question quota

**Stop when:**
- All 5 questions asked, OR
- User signals done, OR
- All categories are Clear

## PHASE 4: Save Results

Save to `specs/[feature-name]/clarifications.md` (create the feature directory if needed):

```markdown
# Clarifications: [Feature Name]

**Date**: [DD-MM-YYYY HH:MM Ukrainian time]
**Questions asked**: [N] of 5

## Decisions

| # | Category | Question | Decision | Rationale |
|---|----------|----------|----------|-----------|
| 1 | ... | ... | ... | ... |

## Coverage (Before → After)

| Category | Before | After |
|----------|--------|-------|
| ... | Partial | Clear |

## Constraints Identified
- ...

## Outstanding Items
[Categories still Partial/Missing, if any]
```

If clarifying an existing spec, also update the spec file's relevant sections directly and append a Clarifications log at the bottom.

## PHASE 5: Recommend Next Step

- All clear → "Run `/specify \"[refined description]\"`"
- Still gaps → "Run `/clarify` again on [specific topic], or proceed to `/specify` and note gaps as Open Questions"

**HARD GATE**: User decides whether to proceed or clarify further. Never auto-advance.

## IMPORTANT RULES

1. Your setup's rules are primary — constitution, memory, hard gates all apply here
2. Options, not open questions — always provide concrete choices
3. Recommend an answer — don't just list options, suggest the best one
4. Max 5 questions — document remaining gaps, don't exceed the limit
5. Check memory — use MEMORY.md to inform recommendations
6. Minimal scope — clarify what's needed for THIS feature, don't expand into adjacent concerns