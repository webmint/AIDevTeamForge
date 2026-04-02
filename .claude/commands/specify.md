# /specify — Feature Specification

Create a structured specification for a feature or change. This command takes a natural language description and produces an unambiguous, reviewable spec.

## Usage
```
/specify "feature description here"
```

## Arguments
- `$ARGUMENTS` — The feature description provided by the user. If empty, ask the user to describe what they want.

## PHASE 0: Branch Setup

Before any spec work, ensure you're on a dedicated spec branch.

### 0.0: Prerequisites

Verify this is a git repository:
```bash
git rev-parse --is-inside-work-tree
```
If the command fails, stop and tell the user: **"This directory is not a git repository. Initialize with `git init` and make an initial commit first."**

### 0.1: Detect Current Branch

Run `git branch --show-current` to get the current branch name.

### 0.2: Detect Default Branch

Determine the repository's default branch using these methods in order:
1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` — parse the branch name from the output
2. If that fails, check if `main` exists: `git show-ref --verify --quiet refs/heads/main`
3. If that fails, check if `master` exists: `git show-ref --verify --quiet refs/heads/master`
4. If none found, ask the user what their default branch is

### 0.3: Branch Decision

**If already on a `spec/*` branch**: Skip to Pre-Step — already on a spec branch.

**If on the default branch**: Prepare for spec branch creation (branch is created in Phase 4 after the spec number is determined):

1. **Generate short description**: From `$ARGUMENTS`, generate a 2-3 word kebab-case summary that captures the essence of the feature (e.g., "add user authentication" → `user-auth`, "implement dark mode toggle" → `dark-mode`). Save this for use in Phase 4.

2. **Note**: Branch creation is deferred to Phase 4 so the branch number matches the spec directory number. Phases 1-3 are read-only research and safe to run on the default branch.

**If on any other branch** (not default, not `spec/*`): Ask the user:
```
You're currently on branch `[branch-name]`, which is not the default branch.

Options:
1. Create spec branch from here (branch off current branch)
2. Switch to [default-branch] first, then create spec branch
3. Continue on current branch without creating a spec branch
```

Wait for user choice and execute accordingly.

## Pre-Step: Reset Session State

Delete `.claude/session-state.md` if it exists (or overwrite with the empty placeholder). A new spec means a new feature scope — previous session tracking is irrelevant.

```markdown
<!-- This file is a fixed-size sliding window. Always fully overwritten, never appended. Max ~40 lines. -->
# Session State

No tasks executed yet. This file is updated automatically after each `/execute-task` run.
```

## PHASE 1: Understand the Request

Read the user's description from `$ARGUMENTS`.

Before doing ANY analysis, read these files for context:
1. `constitution.md` — project rules and patterns
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/specify`."
2. `.claude/memory/MEMORY.md` — past lessons and known pitfalls
3. `CLAUDE.md` — project structure and commands
4. Read relevant project documentation from `docs/` (if the directory exists):
   - `docs/architecture.md` — current architecture patterns, layer boundaries, data flow
   - `docs/features/*.md` — scan for features related to the request
   - `docs/api/*.md` — if the request involves API changes
   - If `docs/` doesn't exist or is empty, skip — rely on codebase analysis in Phase 3

## PHASE 2: Clarify Requirements

Based on the description, identify ambiguities and ask clarifying questions. Use AskUserQuestion to ask 2-4 focused questions.

**Common clarification areas:**

1. **Scope boundaries**: "Should this also affect [related area], or just [specific area]?"
2. **Edge cases**: "What should happen when [edge case]?"
3. **Existing behavior**: "Currently [X] works like [this]. Should it change or stay the same?"
4. **UI/UX details**: "Should there be a loading state? Error message? Confirmation dialog?"
5. **Data flow**: "Where should this data come from? [Option A] or [Option B]?"
6. **Breaking changes**: "This might affect [existing feature]. Is that acceptable?"

**Rules for clarification:**
- Only ask questions you CANNOT answer by reading the codebase
- Group related questions into one AskUserQuestion call
- Never ask more than 4 questions total
- If the description is clear enough, skip to Phase 3

## PHASE 3: Codebase Analysis

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, all file searches and code reads target that path. File paths in the spec's Affected Areas table use workspace-relative paths (e.g., `SOURCE_ROOT/src/...`).

### If existing codebase:

**Step 1: Docs-guided understanding** (if docs were loaded in Phase 1)
- Use docs to understand the high-level behavior, architecture, and feature relationships in the affected area
- Identify which source files are most relevant based on docs references
- Note any gaps — areas the docs don't cover that need direct codebase investigation

**Step 2: Targeted codebase reads**
- Read the specific source files identified from docs (for concrete file paths, line numbers, exact interfaces)
- For areas not covered by docs, use Glob and Grep to locate related files
- Verify docs accuracy — if code doesn't match what docs describe, note the discrepancy
- Map dependencies and identify patterns
- Cross-reference with MEMORY.md for known issues in this area

**If no docs were loaded** (docs/ doesn't exist), fall back to full codebase exploration:
1. **Find affected files**: Use Glob and Grep to locate all files related to the feature
2. **Read key files**: Read the most important files (components, stores, types, API calls)
3. **Map dependencies**: Understand what depends on what
4. **Identify patterns**: How are similar features currently implemented?
5. **Check for pitfalls**: Cross-reference with MEMORY.md for known issues in this area

### If greenfield (few or no source files yet):
Since there's little or no existing code:

1. **Read the constitution** — especially Section 7 (Scaffolding Guide) for directory structure and pattern references
2. **Identify what needs to be CREATED** — list the new files/modules this feature requires
3. **Check the constitution's pattern references** — use those as the starting templates
4. **Reference framework docs** — use WebSearch if needed for framework-specific best practices for this feature type
5. **Check MEMORY.md** — for any lessons from previous features in this project

**Key difference**: In the spec, "Section 2: Current Behavior" should describe "Current State" instead — what exists so far (even if nothing) and what the scaffolding guide says about where this feature should live.

## PHASE 4: Write the Specification

Generate a feature name (lowercase kebab-case, 2-4 words). Determine the next sequential number by scanning existing `specs/` directories for the highest `NNN` prefix. Create `specs/NNN-feature-name/` and save the spec to `specs/NNN-feature-name/spec.md`.

**If branch creation was deferred from Phase 0.3**: Before writing any files, create and checkout the spec branch using the same `NNN` from the directory scan above:
```
git checkout -b spec/NNN-short-desc
```
Inform the user: `Created and switched to branch spec/NNN-short-desc`. This ensures the branch and directory always share the same number.

### Spec Format:

```markdown
# Spec: [Feature Name]

**Date**: [YYYY-MM-DD]
**Status**: Draft | Approved | In Progress | Complete
**Author**: Claude + [User]

## 1. Overview

[2-3 sentence description of what this feature does and why it's needed]

## 2. Current State

[Existing codebase: Describe how the system currently works in the affected area. Include file paths and line numbers. Incorporate context from docs/ loaded in Phase 1 — documented behavior, architecture patterns, and feature relationships. This section is the primary way downstream commands (/plan, /breakdown) inherit docs knowledge, so capture it fully here rather than assuming they will read docs themselves.]
[Greenfield: Describe what exists so far (may be nothing). Reference the constitution's scaffolding guide for where this feature should be built.]

## 3. Desired Behavior

[Describe exactly what should change]
[Be specific — "the button should be blue" not "improve the button"]

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| [Component/Module] | [file paths] | [what changes] |
| ... | ... | ... |

## 5. Acceptance Criteria

Each criterion must be testable and unambiguous:

- [ ] **AC-1**: [Specific, testable criterion]
- [ ] **AC-2**: [Specific, testable criterion]
- [ ] **AC-3**: [Specific, testable criterion]
...

## 6. Out of Scope

[Explicitly list things that are NOT part of this spec]
[This prevents scope creep during implementation]

- NOT included: [thing 1]
- NOT included: [thing 2]

## 7. Technical Constraints

[Any constraints from the constitution, architecture, or external systems]

- Must follow: [architecture pattern]
- Must not break: [existing feature]
- Must use: [specific API/pattern]

## 8. Open Questions

[Any remaining uncertainties that might come up during implementation]
[These should be minor — major questions should have been resolved in Phase 2]

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |
```

## PHASE 5: User Approval

**HARD GATE**: The spec MUST be approved before proceeding to `/breakdown`.

Present the spec summary to the user:

"I've created the specification at `specs/NNN-[feature-name]/spec.md`. Key points:
- **What changes**: [1-2 sentences]
- **Files affected**: [count] files across [areas]
- **Acceptance criteria**: [count] testable criteria
- **Out of scope**: [key exclusions]

Please review and either approve or request changes. Once approved, run `/plan` to create the technical implementation plan."

## IMPORTANT RULES

1. **Specs are contracts** — once approved, the implementation must satisfy every acceptance criterion
2. **Be exhaustive on "out of scope"** — this prevents the most common problem (scope creep)
3. **Every AC must be testable** — "improved UX" is not testable, "modal closes after successful save" is
4. **Reference specific files** — use `path/to/file.ts:line` format for existing code. For greenfield, reference the constitution's directory structure for where files should be created
5. **Check MEMORY.md** — if similar work was done before, reference what went right/wrong
6. **Don't propose solutions** — the spec describes WHAT, not HOW. Solutions come in `/breakdown`
7. **Greenfield: include scaffolding needs** — if the feature requires creating directory structure, types, or foundational modules that don't exist yet, list them in the "Affected Areas" table with Impact = "Create new"