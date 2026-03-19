# /plan — Technical Implementation Plan

Takes an approved spec and produces a technical plan: research findings, data model, API contracts, and architecture decisions. This is the bridge between WHAT (spec) and HOW (task breakdown).

## Usage
```
/plan [spec-file-or-feature-dir]
```

## Arguments
- `$ARGUMENTS` — Path to a spec file or feature directory in `specs/`. If empty, use the most recently modified feature.

## Context in the Workflow

```
/clarify (optional) → /specify → /plan → /breakdown → /execute-task → /verify
```

`/plan` runs AFTER the spec is approved, BEFORE task breakdown. It answers technical questions the spec intentionally left open (specs describe WHAT, plans describe HOW).

## Prerequisites

1. A spec must exist with **Status: Approved**
2. If status is still "Draft", stop and inform the user

## PHASE 0: Research (if needed)

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path.

Read the spec and identify technical unknowns:
- Are there technology choices that need investigation?
- Are there external APIs/services that need their contracts checked?
- Are there performance constraints that need benchmarking?
- Are there existing patterns in the codebase that need to be understood?

### For existing codebases:
- Read relevant source files to understand current patterns
- Check how similar features are implemented
- Identify reusable code and patterns

### For greenfield projects:
- Use WebSearch for framework best practices relevant to this feature
- Check the constitution's scaffolding guide for pattern references
- Research libraries or approaches if the spec mentions unfamiliar tech

### Research output:
If research was needed, save to `specs/[feature-name]/research.md`:

```markdown
# Research: [Feature Name]

**Date**: [DD-MM-YYYY HH:MM Ukrainian time]

## Questions Investigated
1. [Question] → [Finding + decision]
2. [Question] → [Finding + decision]

## Decisions
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| [choice] | [why] | [what else was evaluated] |

## References
- [links to docs, examples, or source files]
```

If no research needed, skip this phase.

## PHASE 1: Technical Design

### 1.1: Data Model (if applicable)

If the feature involves data entities, define them. Save to `specs/[feature-name]/data-model.md`:

```markdown
# Data Model: [Feature Name]

## Entities

### [EntityName]
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier |
| ... | ... | ... | ... |

### Relationships
- [Entity A] → [Entity B]: [relationship type and description]

### Validation Rules
- [Field]: [constraint]
```

For existing codebases, reference existing types/interfaces instead of redefining them. Only document NEW or CHANGED entities.

### 1.2: API Contracts (if applicable)

If the feature involves API calls (REST, GraphQL, etc.), define contracts. Save to `specs/[feature-name]/contracts.md`:

```markdown
# API Contracts: [Feature Name]

## [Endpoint/Query/Mutation Name]
- **Type**: [GET/POST/Query/Mutation]
- **Input**: [type definition or reference to existing type]
- **Output**: [type definition or reference to existing type]
- **Errors**: [error cases and response format]
```

For existing codebases, reference existing GraphQL queries/mutations or REST endpoints. Only document NEW or CHANGED contracts.

### 1.3: Architecture Decisions

Document HOW the feature maps to the project's architecture. This is the core of the plan.

## PHASE 2: Write the Plan

Save to `specs/[feature-name]/plan.md`:

```markdown
# Plan: [Feature Name]

**Date**: [DD-MM-YYYY HH:MM Ukrainian time]
**Spec**: [path to spec.md]
**Status**: Draft

## Summary

[2-3 sentences: what this plan implements and the technical approach]

## Technical Context

**Architecture**: [from constitution — which layers are involved]
**Error Handling**: [pattern to use]
**State Management**: [approach for this feature]

## Constitution Check

[Verify the planned approach doesn't violate any NON-NEGOTIABLE rules]
- Rule X: [compliant / requires attention]
- Rule Y: [compliant / requires attention]

## Implementation Approach

### Layer Map

[Which architectural layers this feature touches and what happens in each]

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Domain | [types, interfaces, use cases] | [file paths] |
| Data | [repositories, API calls] | [file paths] |
| Presentation | [components, views, state] | [file paths] |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| [decision] | [approach] | [rationale] | [alternatives] |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| [path] | Create/Modify | [brief description] |
| [path] | Create/Modify | [brief description] |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |

## Dependencies

[Any external dependencies: packages to install, services to configure, environment variables]

## Supporting Documents

- [Research](research.md) — if research was performed
- [Data Model](data-model.md) — if data entities are involved
- [Contracts](contracts.md) — if API changes are involved
```

## PHASE 3: User Approval

**HARD GATE**: The plan MUST be approved before `/breakdown` can generate tasks.

Present a summary:

"I've created the technical plan at `specs/[feature-name]/plan.md`.

**Approach**: [1-2 sentences]
**Files affected**: [count] ([N] new, [M] modified)
**Key decisions**: [list the most important ones]
**Risks**: [high-risk items if any]
**Supporting docs**: [list what was generated]

Please review and approve. Once approved, run `/breakdown` to generate tasks."

## IMPORTANT RULES

1. **Plans describe HOW, not WHAT** — the spec already defines WHAT. Don't repeat requirements, translate them into technical decisions
2. **Constitution compliance is mandatory** — verify before presenting to user. If the plan would violate a rule, redesign or flag it
3. **Reference existing code** — for existing codebases, always reference actual file paths and existing patterns. Don't propose new patterns when existing ones work
4. **Greenfield: follow the scaffolding guide** — the constitution's Section 7 defines where things go. Follow it
5. **Minimal supporting docs** — only create research.md, data-model.md, contracts.md if they're actually needed. Don't create empty files
6. **Memory check** — consult MEMORY.md for lessons about similar technical decisions
7. **Keep it scannable** — tables over paragraphs, decisions over discussions