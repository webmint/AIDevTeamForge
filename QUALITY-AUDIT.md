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

### ~~C4. `settings.local.json` in template repo has literal `{{TYPE_CHECK_COMMAND}}` — PostToolUse hook will break~~ RESOLVED
- **Resolution**: `install.sh` now removes `settings.local.json` after the bulk `.claude/` copy (`rm -f`). The hook with `{{TYPE_CHECK_COMMAND}}` exists only in `settings.template.json` (correct), and `settings.local.json` is project-owned and no longer copied to target projects.

### ~~C5. `execute-task` uses `git add -A` throughout — risks committing secrets and unwanted files~~ RESOLVED
- **Resolution**: All 18 `git add -A` instances replaced with scoped staging across `execute-task.md`, `fix.md`, `refactor.md`, and `verify.md`. Checkpoint commits no longer stage files (use `--allow-empty`). Work/repair/review commits stage only modified files. Doc/test commits scope to `docs/` or test files respectively.

### ~~C6. `execute-task` Phase 6 squash uses `git reset --soft` — rewrites history~~ RESOLVED
- **Resolution**: All 3 squash sections (`execute-task.md`, `fix.md`, `refactor.md`) now check `git log --oneline origin/$(git branch --show-current)..HEAD` before squashing. If WIP commits were already pushed, squashing is skipped to avoid rewriting shared history.

### ~~C7. `/constitute` overwrites constitution.md entirely — losing ALL universal rules from the template~~ RESOLVED
- **Resolution**: Phase 3 now instructs Claude to read `constitution.template.md` and copy all `[universal]` sections (3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 6.1-6.4) verbatim. The section structure was updated to include all 10 universal sections alongside project-specific sections.

---

## HIGH — Will cause confusion or significantly degraded behavior

### ~~H1. No test execution in `/execute-task` verification pipeline~~ RESOLVED
- **Resolution**: Phase 3.3 now includes step 7 ("Run affected tests") which searches for `*.test.*` / `*.spec.*` files in changed directories and runs them if a test runner is available. Test failures enter the self-repair loop alongside tsc, lint, and build errors.

### ~~H2. `/breakdown` agent assignment table only covers 6 of 14 agent types~~ RESOLVED
- **Resolution**: Added 5 execution-capable agent types to the assignment table: db-engineer, api-designer, devops-engineer, migration-engineer, design-auditor. The remaining 3 (tech-writer, qa-engineer, code-reviewer) are verification agents that run automatically and don't need task assignment rows.

### ~~H3. Memory updates have no defined format — becomes unstructured noise~~ RESOLVED
- **Resolution**: All 4 commands (execute-task Phase 7, fix Phase 9, refactor Phase 9, verify Phase 8) now include the standardized format: `- **[AREA]**: [observation] _(Task N / Feature NNN)_` with instruction to add entries under the matching MEMORY.md section.

### ~~H4. Spec branch numbering and spec directory numbering use independent counters~~ RESOLVED
- **Resolution**: Branch creation deferred from Phase 0.3 to Phase 4. The spec directory number (from scanning `specs/`) is now the single source of truth — the branch `spec/NNN-name` is created using the same NNN immediately before writing the spec file.

### ~~H5. `/verify` Phase 9 references `/commit` which doesn't exist~~ RESOLVED
- **Resolution**: Changed to `Ready for commit (git add + git commit) or PR creation.` — no longer references a non-existent slash command.

### ~~H6. `/fix` Phase 6 code review can trigger unlimited fix cycles~~ RESOLVED
- **Resolution**: Phase 6 now specifies max 1 additional review cycle when code-reviewer returns BLOCK. If still blocked after that cycle, execution stops and reports to the user.

### ~~H7. Date format inconsistency across commands~~ RESOLVED
- **Resolution**: Standardized all date formats to ISO 8601 (`YYYY-MM-DD`). Removed "Ukrainian time" references from plan.md, research.md, and clarify.md. Updated research filename format from `DD-MM-YY` to `YYYY-MM-DD`.

### ~~H8. `/onboard` Phase 3.3 tries to update CLAUDE.md with content that's already there~~ RESOLVED
- **Resolution**: Removed Phase 3.3 ("Update Workflow References") from onboard.md. The `/onboard` entry already exists in `CLAUDE.template.md`.

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
