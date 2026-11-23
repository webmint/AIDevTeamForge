# /specify — Feature Specification

Create a structured specification for a feature or change. This command takes a natural language description and produces an unambiguous, reviewable spec.

## Usage
```
/specify "feature description here"
```

## Arguments
- `$ARGUMENTS` — The feature description provided by the user, or a feature directory from `/research` (`specs/<KEY|NNN>-*`, with its `research-report.md`), or the path of a `/research` report. If empty, ask the user to describe what they want.

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

**Autonomous mode** (`_autonomous-mode.md`, point `default-branch`): use `DEFAULT_BRANCH` from `.claude/project-config.json`; never ask.

### 0.3: Branch Decision

**If `$ARGUMENTS` is a feature directory** (or its `research-report.md`): check out `spec/<directory name>`, creating it from the current branch when it is missing, and skip to Pre-Step.

**If already on a `spec/*` branch**: Skip to Pre-Step — already on a spec branch.

**If on the default branch**: the branch is created in Phase 4, once the directory is named, so both share the name; Phases 1-3 only read and are safe here. **Generate a short description** from `$ARGUMENTS` (a research report or feature directory: from the report's Request block), a 2-3 word kebab-case summary of the feature (e.g., "add user authentication" → `user-auth`, "implement dark mode toggle" → `dark-mode`), for Phase 4.

**If on any other branch** (not default, not `spec/*`): Ask the user:
```
You're currently on branch `[branch-name]`, which is not the default branch.

Options:
1. Create spec branch from here (branch off current branch)
2. Switch to [default-branch] first, then create spec branch
3. Continue on current branch without creating a spec branch
```

Wait for user choice and execute accordingly.

**Autonomous mode** (`_autonomous-mode.md`, point `branch`): switch to the default branch, then create the spec branch.

### 0.4: Audit Gate

When `.claude/quality-profile.json` sets `auditGate`, run `python3 scripts/forge/audit-gate.py start-line`. When the request remediates audit themes, the spec is structural (see "Spec type" in Phase 4; ask the user when unsure) and runs `start-line --remediation "#n,#m"` instead, naming the blocking issues it fixes (without an issue tracker, the theme ids: `--remediation T1,T3`):
- **Exit 0**: keep the printed `Audit gate: …` line; Phase 4 writes it verbatim into the spec header.
- **Exit 1**: show the printed reason and ask the user: run `/audit` first (stop here), or start anyway. On "start anyway", the header records `Audit gate: started while blocked — <user's reason>`.
  **Autonomous mode** (`_autonomous-mode.md`, point `audit-gate`): STOP 8 — return `blocked (audit due)`; never start anyway.

- **Exit 2**: show the error line (for example an `integrationRef` that does not resolve yet), note it in the HARD GATE summary and continue. A remediation request needs its printed line (without it `check-pr` rejects the spec while the gate is blocked): fix the cause (for example `git fetch` the integration ref) and run it again; when it still exits 2, ask the user how to proceed.

When `auditGate` is unset, or the script reports the state as unknown, note it in the HARD GATE summary and continue.

**Autonomous mode** (`_autonomous-mode.md`, point `audit-gate`): exit 2 on a remediation request after the retry is STOP 8 too; a spec type that is unsure is chosen as that point says and recorded under Decisions.

## Pre-Step: Reset Session State

Delete `.claude/session-state.md` if it exists (or overwrite with the empty placeholder). A new spec means a new feature scope — previous session tracking is irrelevant.

```markdown
<!-- This file is a fixed-size sliding window. Always fully overwritten, never appended. Max ~40 lines. -->
# Session State

No tasks executed yet. This file is updated automatically after each `/execute-task` run.
```

## PHASE 1: Understand the Request

Read the user's description from `$ARGUMENTS`, or from the report's Request block when `$ARGUMENTS` is a report or its directory. It is recorded verbatim: read `.claude/commands/_intent-check.md` → "The Request Record".

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
5. The `/research` report for this request (`specs/<KEY|NNN>-*/research-report.md`, or a `research/YYYY-MM-DD-<slug>.md` from before 1.39.0), when the user names one or `$ARGUMENTS` is its path. Its `**This part**:` field, after a split, is the part this spec covers. Its `**Depends on**` field, when present, is constraints, not the request. Its recommendation is weighed in Phase 2. Check it is not stale: after `git fetch origin`, run `git diff --name-only <Investigated at sha> <ref> -- <scoped paths>`, with `<ref>` = the binding's `integrationRef`, else `origin/[DEFAULT_BRANCH]`. Any output means a merge touched the investigated area: do not use its findings (its Request block is still the request: record it), tell the user it is stale and have `/research` re-run against the current code. A report without an `**Investigated at**:` line counts as stale.

## PHASE 1.5: Prior Art

Answers "does the product already do this, or something that overlaps or contradicts it?" before the questions of Phase 2 are asked, because prior art changes them.

1. **Search.** Start from the research report's "Reuse or Extend" rows, when there is one. Scan the feature docs related to the request (Phase 1 step 4) and search the search scopes for the request's concepts by name and meaning. The search scopes are `searchScopes` minus `generatedDirs` in `.claude/quality-profile.json` (`python3 scripts/forge/quality_profile.py scopes` prints them; the source directories when unset).
2. **Pick 0-5 candidates by meaning**: code or documented behaviour that the request needs, extends, re-specifies or may contradict.
3. **Open only the candidates.** Read the entry point's declaration and doc comment, and the candidate's section of its feature doc. When the spec may change shared behaviour, search the scopes for its callers.
4. **Record** the section "2a. Prior art" (template below): one row per candidate. A candidate that is unrelated after reading is listed as such. "None: no candidate for <need>; searched <scopes and terms>, read <docs>" is a valid entry.

Prior art is behavioural: it records what the product already does and whether this spec reuses, extends or replaces that behaviour. How to reuse it (which symbol to call) is decided in `/plan`. A spec that re-specifies an existing capability as new behaviour, or states an AC that contradicts a candidate's behaviour without saying so, is the defect this step prevents.

## PHASE 2: Clarify Requirements

Read `.claude/commands/_specify-checks.md` → "Decision Points" and ask the user each point it calls open, before the spec is saved: here, and for the points found later, through Phase 4.
Each question as asked and the user's answer as given go verbatim into the request record.

**Autonomous mode** (`_autonomous-mode.md`, point `clarify`): as `_specify-checks.md` → "Decision Points" says.

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

1. **Read the constitution** — especially Section 7 (Scaffolding Guide, or the document it points to) for directory structure and pattern references
2. **Identify what needs to be CREATED** — list the new files/modules this feature requires
3. **Check the constitution's pattern references** — use those as the starting templates
4. **Reference framework docs** — use WebSearch if needed for framework-specific best practices for this feature type
5. **Check MEMORY.md** — for any lessons from previous features in this project

**In the spec**, "Current State" says what exists so far (even nothing) and where the scaffolding guide puts this feature.

## PHASE 4: Write the Specification

Use the feature directory of `$ARGUMENTS` when there is one. Otherwise name and create it by `.claude/storage-rules.md` → "Feature Directories" (autonomous point `ticket`); a reused directory's `research-report.md` is the research report. Save the spec to `specs/<KEY|NNN>-feature-name/spec.md`.

**If branch creation was deferred from Phase 0.3**: Before writing any files, create and checkout the spec branch named after the directory:
```
git checkout -b spec/<directory name>
```
Inform the user: `Created and switched to branch spec/<directory name>`. This ensures the branch and directory always share the same name.

### Spec type: feature or structural

A spec is **structural** when it preserves behaviour: it extracts a single source for a concept, adds a seam, or adds a machine check, and no acceptance criterion describes new or changed user-facing behaviour. Every other spec is a **feature** spec. A change that also alters behaviour is split (the behaviour change goes through `/fix` or its own feature spec) or stays a feature spec.

A structural spec runs a lean pipeline: the plan-gate runs the architect lens only (plus the security lens when the spec touches access control, privileged code, permissions or authentication), and the breakdown-gate is skipped. Everything else runs as for a feature spec.

The acceptance criteria of a structural spec are invariants, each with the check that proves it. They read the project binding `.claude/quality-profile.json`:
- **One definition**: "one definition of <concept> at <path> (<symbol>); a search of the search scopes finds no other derivation", naming the search (scopes as in Phase 1.5). When the concept has a row in the canonical sources registry (`canonicalSources`), the AC cites the row, and the spec updates the row's single definition and consumers; otherwise the spec adds the row.
- **Ratchet**: "ratchet <name> lowered from <n> to at most <m>", for a count the binding defines (`ratchets`); when the spec adds a machine check (a lint rule, a catalog test or a new ratchet), an AC says it lands before the copies are migrated, so no new copy appears during the change.
- **Regression**: "the existing tests pass unchanged"; no test is weakened to pass.
- A binding key that is unset uses the manual form: the AC names the search or the counting command itself, and the spec says so.

### Spec Format:

A new spec takes this template. Read `.claude/commands/_writing.md` → "Specs" now: each section holds what it says. Before a new or a revised spec is saved, apply `_specify-checks.md` → "Decision Points": points found later, one number, Open Questions only by the user's choice. Save the request record to a new `specs/<KEY|NNN>-feature-name/history.md` (`_intent-check.md` → "The Request Record").

```markdown
# Spec: [Feature Name]

**Date**: [YYYY-MM-DD]
**Status**: Draft | Approved | In Progress | Complete
**Author**: Claude + [User]
**Type**: feature | structural
**Format**: 2
[The `Audit gate: …` line from Phase 0.4, verbatim; omit when `auditGate` is unset]

## 1. Summary

[5-10 plain lines for people, with why it is needed]

## 2. Current State

[The facts the criteria and the plan depend on, with file:line; a link to research-report.md, when there is one, for the rest]

## 2a. Prior art

[From Phase 1.5. One row per candidate; evidence is file:line of what was read. Or "None: no candidate for <need>; searched <scopes and terms>, read <docs>".]

| Candidate | What this spec needs from it | Decision | Evidence read |
|-----------|------------------------------|----------|---------------|
| [symbol, module or feature-doc section] | [the behaviour the spec needs, extends, re-specifies or may contradict] | reuse behaviour / extend / new, because [reason] / unrelated after reading | [file:line, callers found] |

## 3. Behaviour and Acceptance Criteria

### 3.1 [Behaviour]

[A few lines of behaviour]

- [ ] **AC-1**: [Specific, testable criterion]

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| [Component/Module] | [file paths] | [what changes] |

## 5. Out of Scope

- [One line per entry]

## 6. Technical Constraints

[Only what constitution.md and CLAUDE.md do not already say: external systems, features that must not break]

## 7. Decisions

- **DEC-1** [Title]: [decision]. Why: [one sentence].

## 8. Open Questions

- **Q-[N]** [Question]

## 9. Risks

| Id | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| RISK-1 | [risk] | Low/Med/High | Low/Med/High | [how to handle] |
```

**An existing spec keeps its format.** When the directory already has a `spec.md` (a revision, for example when `/verify` or the intent check sends the user back), edit it in place, keeping its `**Format**: 2` line or its absence. An older spec keeps its Request section (when it has one) and its own section names and numbers; a decision goes under its Decisions section, added after Risks when missing.

### Size Check

A `**Format**: 2` spec, once its criteria are written: run `python3 scripts/forge/spec_lint.py scope specs/<KEY|NNN>-*` and apply `.claude/storage-rules.md` → "Feature Size".

## PHASE 4.5: Independent Gate (spec-gate)

Read `.claude/commands/_independent-gate.md` and run the **spec-gate** on `specs/<KEY|NNN>-[feature-name]/spec.md`. Apply its loop before presenting the spec.

## PHASE 5: User Approval

**HARD GATE**: The spec MUST be approved before proceeding to `/breakdown`.

**Autonomous mode** (`_autonomous-mode.md`, point `specify`): self-approve as that file's "Self-Approval at a HARD GATE" says, instead of waiting.

Present the spec to the user (`CLAUDE.md` → "Talking to the User"):

"I've created the specification at `specs/<KEY|NNN>-[feature-name]/spec.md`.
[A `**Format**: 2` spec: its `## 1. Summary` as written. An older spec: these key points]
- **What changes**: [1-2 sentences]
- **Files affected**: [count] files across [areas]
- **Acceptance criteria**: [count] testable criteria
- **Out of scope**: [key exclusions]
[When the run picked a value within an answer or the request: each value, and the answer it came from in words with its `Q-N` in brackets, or "the request"]

[the gate result from `_independent-gate.md` → "At the HARD GATE"]
[After a Size Check split: each other part as `/research "<request>"`]

Please review and either approve or request changes. Once approved, run `/plan` to create the technical implementation plan."

A change request that adds or excludes scope is appended to the request record, verbatim and dated.

## IMPORTANT RULES

1. **Specs are contracts** — once approved, the implementation must satisfy every acceptance criterion
2. **Be exhaustive on "out of scope"** — this prevents the most common problem (scope creep)
3. **Every AC must be testable** — "improved UX" is not testable, "modal closes after successful save" is
4. **Reference specific files** — use `path/to/file.ts:line` for existing code. For greenfield, reference the constitution's directory structure for where files should be created
5. **Check MEMORY.md** — if similar work was done before, reference what went right/wrong
6. **Don't propose solutions** — the spec says WHAT (`_writing.md` → "Rules")
7. **Greenfield: include scaffolding needs** — if the feature requires creating directory structure, types, or foundational modules that don't exist yet, list them in the "Affected Areas" table with Impact = "Create new"
8. **Prior art before questions** — Phase 1.5 runs before Phase 2, and the spec carries its "2a. Prior art" section; a spec without it is incomplete. The decision is about behaviour (reuse, extend, new); the symbol to call is the plan's decision