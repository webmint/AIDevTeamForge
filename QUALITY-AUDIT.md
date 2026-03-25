# Quality Audit: AIDevTeamForge — Issues, Gaps & Mislogic

## Context

Comprehensive quality audit of the AIDevTeamForge template system — a set of Claude Code slash commands, agent templates, and configuration files that guide Claude Code through spec-driven development workflows in real projects. All findings evaluated against Claude Code's specific capabilities: built-in `/compact`, automatic context compression, PostToolUse hooks, Agent/Task tools, settings.json/settings.local.json, and slash command execution.

---

## CRITICAL — Will cause workflow failures or incorrect behavior

### C1. `/execute-task` Phase 8 tells Claude to "auto-compact" but Claude can't invoke `/compact` itself
- **Location**: `execute-task.md` Phase 8 (line 526)
- **Problem**: Phase 7.5.2 correctly recommends the USER run `/compact` with preserve instructions — that's the right approach and should stay. But Phase 8 (multi-task, heavy load) says: "auto-compact before continuing. Run `/compact`... Do NOT ask — compact and continue." Claude cannot programmatically invoke `/compact` — it's a user-initiated slash command.
- **Impact**: During `execute-task all` with 6+ tasks, Claude hits an instruction it literally cannot execute. It will either skip it (risking context exhaustion), halt confusingly, or hallucinate that it compacted.
- **Fix**: Keep the `/compact` with preserve instructions inline as-is (the 6-point template is correct and only needs dynamic feature/task fill-in). Only change Phase 8 heavy-load handling: instead of "Do NOT ask — compact and continue", change to pause execution, present the pre-built `/compact` command with preserve instructions to the user, ask them to run it, then tell them to resume with `/execute-task [remaining-tasks]`. Phase 7.5.2 (single-task recommend) is already correct — no change needed there.

### C2. Constitution stub created by `/setup-wizard` has placeholder text — commands between setup-wizard and `/constitute` read garbage
- **Location**: `constitution.template.md` lines 25, 29, 32, 38, 42, 44, 48, 127, 153, 165, 171, 205, 209
- **Problem**: `/setup-wizard` Step 3.5 creates `constitution.md` from the template with "_Run /constitute to populate_" stubs in all project-specific sections. `/constitute` completely overwrites it later. But if any command runs between these two (the user runs `/specify` before `/constitute`), Claude reads a constitution full of placeholder text.
- **Impact**: Pre-flight checks reference "Constitution compliance" but the constitution has no actual project rules. Claude will either skip constitution checking (violating workflow) or flag everything as a violation (blocking all work).
- **Fix**: Either (a) don't create a constitution stub in setup-wizard — just note that `/constitute` must run first, or (b) add an explicit check in `/specify`, `/plan`, `/fix`, `/refactor`: "If constitution.md contains '_Run /constitute to populate_', stop and inform the user to run `/constitute` first."

### C3. Greenfield detection threshold conflicts between three commands
- **Location**: `setup-wizard.md` line 44-46: greenfield = 0-5 files. `constitute.md` line 19: greenfield < 10 files. `onboard.md` line 12: existing = 6+ files.
- **Problem**: A project with 7 source files is:
  - **Existing** per `/setup-wizard` (6+ = existing)
  - **Greenfield** per `/constitute` (< 10 = greenfield)
  - **Existing** per `/onboard` (6+ = existing)
- **Impact**: `/setup-wizard` auto-detects patterns and generates CLAUDE.md for an existing project. Then `/constitute` enters greenfield mode and interviews the user about architecture choices — ignoring what setup-wizard already detected. Contradictory behavior in the same workflow.
- **Fix**: Align all thresholds. Recommend using a flag in `project-config.json` (set by setup-wizard) instead of re-counting files each time: `"PROJECT_MODE": "greenfield"` or `"existing"`.

### C4. `settings.local.json` in template repo has literal `{{TYPE_CHECK_COMMAND}}` — PostToolUse hook will break
- **Location**: `.claude/settings.local.json` (copied by `install.sh` to target project)
- **Problem**: The template repo's `.claude/settings.local.json` contains a PostToolUse hook with `"command": "{{TYPE_CHECK_COMMAND}}"`. `install.sh` copies the entire `.claude/` directory including this file. Claude Code's harness will try to execute this literal string as a shell command after every Edit/Write operation.
- **Impact**: Every file edit triggers a hook that runs `{{TYPE_CHECK_COMMAND}}` in the shell — which fails immediately. The hook is async with 30s timeout, so it won't block Claude, but it generates noise/errors in every session until `/setup-wizard` generates the proper `.claude/settings.json`.
- **Fix**: Remove the PostToolUse hook from `settings.local.json` — it belongs only in `settings.template.json` (which `/setup-wizard` reads and generates `settings.json` from). Or have `install.sh` exclude `settings.local.json`.

### C5. `execute-task` uses `git add -A` throughout — risks committing secrets and unwanted files
- **Location**: `execute-task.md` lines 176, 260, 291, 319, 377-379, 411. Also `fix.md` lines 180, 219, 245, 273, 299, 325. Also `refactor.md` lines 220, 283, 309, 337, 365, 390.
- **Problem**: `git add -A && git commit` is used for every checkpoint, WIP commit, doc commit, and repair commit. This adds ALL untracked and modified files including `.env`, credentials, large binaries, and IDE config.
- **Impact**: Secrets or unwanted files get committed in WIP/checkpoint commits. Even though these get squashed, they remain in git reflog and can be recovered. Claude Code's own system prompt explicitly warns against `git add -A`.
- **Fix**: Replace with specific file additions: `git add [list of files from task's Files section] .claude/wip.md`. For doc commits: `git add docs/ [source files]`. For checkpoint commits: `git add -A -- ':!.env*' ':!*.pem' ':!*.key'` (exclude common secret patterns).

### C6. `execute-task` Phase 6 squash uses `git reset --soft` — rewrites history
- **Location**: `execute-task.md` lines 411-416. Also `fix.md` lines 325-328. `refactor.md` lines 390-394.
- **Problem**: Squashing WIP commits via `git reset --soft [hash] && git commit` rewrites git history. If the user pushed the branch (common when working on spec branches), this forces a `git push --force`.
- **Impact**: Claude will execute the reset without checking if commits were pushed. In team environments this can destroy others' work.
- **Fix**: Add a pre-squash check: "Before squashing, verify no WIP commits have been pushed: `git log --oneline origin/[branch]..HEAD`. If WIP commits exist on remote, skip squashing — the WIP commits become the final commits."

### C7. `/constitute` overwrites constitution.md entirely — losing ALL universal rules from the template
- **Location**: `constitute.md` Phase 3 vs `constitution.template.md` sections 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 6.1-6.4
- **Problem**: The constitution template has extensive, carefully crafted universal rules: no dead code, SOLID/DRY/KISS principles, early returns, check-before-build, patterns with code examples, etc. But `/constitute` Phase 3 says "Write `constitution.md`" using a section structure — it does NOT instruct Claude to preserve the universal sections from the template.
- **Impact**: Claude generates a fresh constitution that may lack the quality standards from the template. The universal rules (sections 3.5-3.7, 4.1-4.3, 6.1-6.4) — representing substantial engineering wisdom — get replaced with whatever Claude generates, which may be weaker, less specific, or missing entirely.
- **Fix**: Add to `/constitute` Phase 3: "Read `.claude/templates/constitution.template.md`. Copy all sections tagged `[universal]` (3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 6.1-6.4) verbatim into the generated constitution. Only populate `[project-specific]` sections from analysis/interview."

---

## HIGH — Will cause confusion or significantly degraded behavior

### H1. No test execution in `/execute-task` verification pipeline
- **Location**: `execute-task.md` Phase 3.3 (lines 265-298)
- **Problem**: Post-execution verification checks: tsc, lint, build, done-conditions, contracts. It does NOT run tests. The `/refactor` command (Phase 5, line 295) runs tests, but `/execute-task` — the primary execution pipeline — does not.
- **Impact**: Code passes all gates while breaking existing tests. Tests are only checked during `/verify` (end of feature), which may be 10+ tasks later. This is the #1 source of regressions in real projects.
- **Fix**: Add to Phase 3.3: "6. **Run affected tests**: If test files exist for the changed areas (search for `*.test.*`, `*.spec.*` in the same directories), run them. Test failures enter the self-repair loop."

### H2. `/breakdown` agent assignment table only covers 6 of 14 agent types
- **Location**: `breakdown.md` lines 84-93
- **Problem**: Assignment table maps to: architect, frontend-engineer, backend-engineer, runtime-debugger, performance-analyst, security-reviewer. Missing: db-engineer, api-designer, design-auditor, migration-engineer, devops-engineer, tech-writer, qa-engineer, code-reviewer.
- **Impact**: For a database migration task (common!), Claude has no guidance and defaults to architect. For CI/CD setup, no guidance either.
- **Fix**: Expand the table:
  - Database schemas, migrations, queries → `db-engineer`
  - API contract design, OpenAPI specs → `api-designer`
  - CI/CD, Docker, deployment config → `devops-engineer`
  - Data migration, backward compatibility → `migration-engineer`
  - Accessibility, design system compliance → `design-auditor`

### H3. Memory updates have no defined format — becomes unstructured noise
- **Location**: `execute-task.md` Phase 7, `fix.md` Phase 9, `refactor.md` Phase 9, `verify.md` Phase 8
- **Problem**: All say "update MEMORY.md" but none specifies the format. The template `memory.template.md` defines sections (Known Pitfalls, What Worked, etc.) but commands just say "add a concise note."
- **Impact**: After 10+ tasks, MEMORY.md is an unstructured dump. Different sessions format entries differently. Claude reads it but extracts little value.
- **Fix**: Define format in each command: "Add to the appropriate section in MEMORY.md using the format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_`"

### H4. Spec branch numbering and spec directory numbering use independent counters
- **Location**: `specify.md` lines 35-39 (branches scan `git branch`) vs line 130 (directories scan `specs/`)
- **Problem**: Branch numbering scans `git branch -a --list '*spec/*'`. Directory numbering scans `specs/`. If someone deletes a spec directory but not the branch (or vice versa), numbers diverge. Branch `spec/003-auth` might correspond to `specs/002-auth/`.
- **Fix**: Derive branch name from the spec directory number: first create the spec directory (Phase 4), then create branch `spec/NNN-name` using the same NNN.

### H5. `/verify` Phase 9 references `/commit` which doesn't exist
- **Location**: `verify.md` Phase 9 (line 176)
- **Problem**: Says "Ready for `/commit` or PR creation." There is no `/commit` slash command (neither built-in Claude Code nor custom). Claude Code has a built-in `/commit` skill via its system prompt but it's not a slash command in the same sense.
- **Impact**: Claude may try to invoke it as a custom command and fail, or correctly interpret it as a suggestion to commit.
- **Fix**: Change to: "Ready for commit (use `git add` + `git commit`) or PR creation."

### H6. `/fix` Phase 6 code review can trigger unlimited fix cycles
- **Location**: `fix.md` lines 268-276
- **Problem**: If code-reviewer returns BLOCK, the instruction says "Apply the required fixes, Re-run verification." No iteration limit. Phase 5 has a 3-attempt repair loop, but Phase 6's review-triggered fixes have no limit. Claude could loop: fix → review → BLOCK → fix → review → BLOCK...
- **Impact**: Context exhaustion from an infinite loop of review-triggered changes.
- **Fix**: Add: "If the code-reviewer returns BLOCK, apply fixes and re-verify (max 1 additional review cycle). If still BLOCKED, report to the user."

### H7. Date format inconsistency across commands
- **Location**: Multiple files
- **Problem**: Four different date formats:
  - Research filenames: `DD-MM-YY` (2-digit year, doesn't sort chronologically)
  - Plan/Clarify timestamps: `DD-MM-YYYY HH:MM Ukrainian time`
  - Spec dates: `YYYY-MM-DD` (ISO)
  - Bug report dates: `YYYY-MM-DD`
- **Impact**: Inconsistent naming, sorting issues, and "Ukrainian time" is locale-specific.
- **Fix**: Standardize on ISO 8601 (`YYYY-MM-DD`) everywhere. Remove "Ukrainian time" — use local timezone.

### H8. `/onboard` Phase 3.3 tries to update CLAUDE.md with content that's already there
- **Location**: `onboard.md` lines 466-478
- **Problem**: Phase 3.3 says "Update CLAUDE.md to add `/onboard` to the workflow commands section." But `CLAUDE.template.md` already has `/onboard` in the workflow diagram (line 39) and description (lines 72-73). Claude will either add a duplicate or waste context checking.
- **Fix**: Remove Phase 3.3 from onboard.md.

---

## MEDIUM — Could cause subtle problems or degraded quality

### M1. No mechanism to detect partially completed setup-wizard
- **Problem**: If setup-wizard is interrupted mid-generation, some files exist but not others. No single "setup complete" marker.
- **Fix**: Write `.claude/setup-complete` marker at the very end of setup-wizard. Check for it in other commands' prerequisites.

### M2. Context load in `/execute-task` Phase 1.2 has no budget
- **Location**: `execute-task.md` line 144
- **Problem**: "Read ALL files listed in the task's Files section" with no limit. A task listing 10+ large files consumes significant context before the agent starts. Combined with spec.md, plan.md, constitution.md, MEMORY.md, and relevant docs, the pre-execution context load can be massive.
- **Note**: Claude Code's automatic context compression mitigates this somewhat, but the agent still operates within a finite context window. Pre-loading many large files reduces the space available for actual work.
- **Fix**: Add: "If total estimated lines of task files exceed 500, read only the sections relevant to the change (use Change Details to identify which functions/blocks to focus on)."

### M3. Session-state.md size limit (~40 lines) not enforced
- **Location**: `execute-task.md` Phase 7.5.1
- **Problem**: The instruction says "max ~40 lines" but there's no verification step.
- **Fix**: Add: "After writing session-state.md, verify line count. If over 40 lines, trim oldest entries from 'Key Decisions' and 'Files Modified.'"

### M4. `/fix` and `/refactor` don't update session-state.md
- **Location**: `fix.md` and `refactor.md` — no session state management at all
- **Problem**: `/execute-task` carefully manages session-state.md (Phase 7.5). But `/fix` and `/refactor` don't touch it. After a fix or refactor, session state is stale.
- **Fix**: Add a session-state update phase after the final commit in both commands.

### M5. Wrapper mode isolation check is incomplete
- **Location**: `execute-task.md` Phase 3.3.7 (line 275)
- **Problem**: Checks for `.claude/`, `specs/`, `docs/overview.md`, `constitution.md`, `CLAUDE.md` inside SOURCE_ROOT. Misses: `bugs/`, `research/`, `.mcp.json`, `wip.md`, `session-state.md`.
- **Fix**: Use a comprehensive glob: `SOURCE_ROOT/{.claude,specs,docs,bugs,research,constitution.md,CLAUDE.md,.mcp.json}`.

### M6. `/execute-task` Phase 7.5.2 and Phase 8 contradict on compaction behavior
- **Location**: Phase 7.5.2 (line 496) vs Phase 8 (line 526)
- **Problem**: Phase 7.5.2: "Do NOT auto-compact — always let the user decide." Phase 8: "auto-compact before continuing. Do NOT ask." Direct contradiction for heavy context load. Both use `/compact` with preserve instructions (which is the right approach), but they disagree on whether to ask the user.
- **Fix**: Reconcile both to use the same pattern: present the `/compact` command with preserve instructions and ask the user to run it. Phase 7.5.2 (single-task) = recommend. Phase 8 (multi-task, heavy) = strongly recommend and pause execution until user compacts. Neither should claim Claude can auto-invoke it.

### M7. Contracts reference "grep-verifiable" items but some constructs aren't grep-friendly
- **Location**: `breakdown.md` lines 128-143
- **Problem**: Contract items like "has a public getter named X" may not be grep-findable for computed properties, decorators, or framework-specific constructs (e.g., Vue's `computed()`, Angular's `@Input()`).
- **Fix**: Add guidance: "Contracts must reference literal strings that appear in source code — export names, function names, interface names, field names. Avoid referencing abstract concepts (e.g., 'has a getter') — reference the literal declaration pattern instead."

### M8. `update.sh` section merge only handles `##` headers
- **Location**: `update.sh` lines 278-368
- **Problem**: The perl script splits on `^## `. Custom `###` or `#` sections added by the user get merged into the body of the preceding `##` section.
- **Fix**: Document the limitation or handle all header levels.

### M9. `/specify` Phase 0.3 branch creation doesn't check if git is initialized
- **Problem**: Branch operations assume git repo exists. If project has no git (just installed, no `git init`), all operations fail silently or with confusing errors.
- **Fix**: Add prerequisite: "Verify this is a git repository. If not: 'Initialize with `git init` and make an initial commit first.'"

### M10. Research filenames use DD-MM-YY which doesn't sort chronologically
- **Location**: `research.md` line 197
- **Problem**: `25-03-26-topic.md` sorts lexicographically, not by date.
- **Fix**: Use `YYYY-MM-DD` format.

---

## LOW — Minor improvements

### L1. Agent model assignments undocumented
- runtime-debugger=opus, tech-writer=haiku, others=sonnet. No rationale documented.
- **Fix**: Add rationale in README or a comment in setup-wizard.

### L2. `install.sh` copies `settings.local.json` with unresolved placeholder
- Related to C4. The install script should exclude it or rename it.

### L3. Spec template `templates/spec.template.md` is never used by `/specify`
- `/specify` Phase 4 generates a spec with inline format, doesn't read the template.
- **Fix**: Either have `/specify` read and fill the template, or remove `spec.template.md`.

### L4. `CLAUDE.template.md` shows `specs/research/` but `/research` saves to `research/` at root
- **Location**: CLAUDE.template.md line 172 vs research.md line 197
- **Fix**: Update CLAUDE.template.md to match actual behavior.

### L5. Several commands hardcode "Ukrainian time"
- Locale-specific assumption. Only relevant to the original author.
- **Fix**: Remove "Ukrainian time" — say "local time" or omit timezone.

### L6. `memory: project` field only on runtime-debugger agent — unclear what it does
- **Location**: `runtime-debugger.template.md` line 5
- **Problem**: No other agent has this field. No documentation explains its purpose.
- **Fix**: Document what `memory: project` means in agent frontmatter, or remove if unused.

---

## Summary

| Severity | Count | Top Issues |
|----------|-------|------------|
| **CRITICAL** | 7 | Phase 8 auto-compact impossible, constitution placeholder gap, greenfield threshold conflict, settings.local.json broken hook, git add -A risk, history rewrite, universal rules lost |
| **HIGH** | 8 | No test execution in pipeline, agent assignment gaps, memory format undefined, unlimited review cycles, date inconsistency |
| **MEDIUM** | 10 | Context budget, session-state gaps, wrapper isolation, compaction contradiction |
| **LOW** | 6 | Undocumented models, unused template, locale assumption |
| **TOTAL** | **31** | |

---

## Implementation

Save this audit as `QUALITY-AUDIT.md` at the project root (`/Users/mykolakudlyk/Projects/ai-dev-team-forge/QUALITY-AUDIT.md`).

## Verification

After implementing fixes:
1. Trace the full workflow `/setup-wizard` → `/constitute` → `/specify` → `/plan` → `/breakdown` → `/execute-task` → `/verify` and confirm no state contradictions
2. Run `install.sh` on a test project and verify no unresolved `{{PLACEHOLDER}}` in any file loaded by Claude Code's harness
3. Simulate a 7-file project to verify greenfield detection consistency
4. Grep all commands for `git add -A` and replace with specific additions
5. Verify `/constitute` preserves universal rules from template
6. Verify all date formats are consistent
7. Test multi-task `execute-task all` with 6+ tasks to confirm compaction handling works
