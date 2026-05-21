# Quality Audit: AIDevTeamForge — Cumulative Results (v1 → v2 → v3 → v4 → v5)

## Overview

Five audit passes covering the entire AIDevTeamForge template system: 15 commands, 5 templates, 14 agent templates, install.sh, update.sh, template-manifest.json, settings.template.json, and cross-file consistency.

| Audit | Date | Issues Found | Resolved |
|-------|------|-------------|----------|
| v1 | 2026-03-25 | 31 | 31 (30 fixed, 1 moot) |
| v2 | 2026-03-25 | 16 | 16 (15 fixed, 1 accepted) |
| v3 | 2026-03-25 | 12 | 12 (9 fixed, 3 accepted/deferred) |
| v4 | 2026-03-25 | 5 | 5 (3 fixed, 2 acceptable/no-action) |
| v5 | 2026-03-25 | 1 | 1 (1 fixed) + 12 assessed as not actionable |
| **Total** | | **65** | **65** |

---

## v1 Audit (31 issues) — ALL RESOLVED

| ID | Severity | Issue | Status |
|----|----------|-------|--------|
| C1 | CRITICAL | Phase 8 auto-compact impossible | RESOLVED |
| C2 | CRITICAL | Constitution placeholder gap | RESOLVED |
| C3 | CRITICAL | Greenfield threshold conflict | RESOLVED |
| C4-C7 | CRITICAL | settings.local.json, git add -A, history rewrite, universal rules | RESOLVED |
| H1-H8 | HIGH | Test execution, agent coverage, memory format, branch numbering, /commit ref, review cycles, dates, onboard duplicate | RESOLVED |
| M1-M10 | MEDIUM | Setup detection, context budget, session-state, wrapper isolation, compaction, contracts, update.sh merge, git check, research format | RESOLVED/MOOT |
| L1-L6 | LOW | Model docs, install.sh, unused template, paths, locale, memory field | RESOLVED |

---

## v2 Audit (16 issues) — ALL RESOLVED

| ID | Severity | Issue | Status |
|----|----------|-------|--------|
| N-H1 | HIGH | install.sh copies release.md to target projects | RESOLVED |
| N-H2 | HIGH | Type check/lint hardcoded to TypeScript/ESLint | RESOLVED |
| N-H3 | HIGH | settings.template.json missing Edit/Write/Bash/Agent permissions | RESOLVED |
| N-M1 | MEDIUM | Architect template `Te/sting` typo | RESOLVED |
| N-M2 | MEDIUM | Wrong context7 MCP tool name | RESOLVED |
| N-M3 | MEDIUM | /refactor review cycle no cap | RESOLVED |
| N-M4 | MEDIUM | Workflow diagram `(auto)` label misaligned | RESOLVED |
| N-M5 | MEDIUM | /verify and /clarify lack constitution guard | RESOLVED |
| N-M6 | MEDIUM | /release doesn't check CLAUDE.template.md | RESOLVED |
| N-M7 | MEDIUM | install.sh leaks template memory files | RESOLVED |
| N-M8 | MEDIUM | Agent prompt TypeScript-specific | RESOLVED |
| N-L1 | LOW | research/.gitkeep in manifest | RESOLVED |
| N-L2 | LOW | setup-complete marker unused | ACCEPTED |
| N-L3 | LOW | Dead merge_sections() code | RESOLVED |
| N-L4 | LOW | "(Task tool)" legacy reference | RESOLVED |
| N-L5 | LOW | No Type Check Command field in CLAUDE.md | RESOLVED |

---

## v3 Audit (12 issues) — ALL ADDRESSED

### HIGH (4) — All fixed

#### ~~V3-H1. update.sh baseline updated unconditionally on merge conflict~~ RESOLVED
- **Resolution**: Moved `cp "$new_agent" "$baseline"` inside the merge-success branch only. On conflict, both agent and baseline are left unchanged so the next update retries the full merge.

#### ~~V3-H2. update.sh migrate_project_config() missing TYPE_CHECK_COMMAND/LINT_COMMAND~~ RESOLVED
- **Resolution**: Added extraction of Type Check Command and Lint Command from CLAUDE.md, language-based fallback detection, PROJECT_MODE inference, and all three fields to the jq arguments and JSON output.

#### ~~V3-H3. Hardcoded `tsc --noEmit` in execute-task.md Phase 0.3 Recovery~~ RESOLVED
- **Resolution**: Changed to "Run the Type Check Command from CLAUDE.md, the Lint Command, and the build command".

#### ~~V3-H4. Hardcoded `tsc` in CLAUDE.template.md Automated Guards~~ RESOLVED
- **Resolution**: Changed to "type check + lint + build".

### MEDIUM (5) — All fixed

#### ~~V3-M1. wip.md shared between commands with no type differentiation~~ RESOLVED
- **Resolution**: Added `## Command` field (execute-task | fix | refactor) to wip.md template in all three commands. Each command's Phase 0 recovery now checks the Command field first and stops with a clear message if the wip.md belongs to a different command.

#### ~~V3-M2. WIP squash atomicity — no error handling if commit fails after reset~~ RESOLVED
- **Resolution**: Added error handling note: if commit fails after reset --soft, do NOT delete wip.md. Inform user that changes are staged. wip.md is only deleted after successful commit.

#### ~~V3-M3. /verify doesn't cross-check task statuses before marking spec Complete~~ RESOLVED
- **Resolution**: Added task completion cross-check to Phase 7: all task files must have Status: Complete before spec can be marked Complete.

#### ~~V3-M4. /fix has no awareness of pending spec tasks on same files~~ RESOLVED
- **Resolution**: Added file overlap check in Phase 1.2: scans specs/*/tasks/*.md for Pending/In Progress tasks targeting the same files and warns the user (non-blocking).

#### ~~V3-M5. LINT_COMMAND defined but not in PostToolUse hook~~ RESOLVED
- **Resolution**: Documented the intentional asymmetry in CLAUDE.template.md: Type Check Command runs via hook, Lint Command runs during explicit verification phases.

### LOW (3) — Deferred/accepted

#### V3-L1. TYPE_CHECK_COMMAND/LINT_COMMAND not in README/DEVELOPMENT-STATUS
- **Status**: DEFERRED — will be addressed during next /release.

#### V3-L2. Inconsistent terminology (Type Check Command vs type checking vs type checker)
- **Status**: ACCEPTED — functionally correct, cosmetic only.

#### V3-L3. No validation that TYPE_CHECK_COMMAND works after generation
- **Status**: DEFERRED — nice-to-have for future improvement.

---

---

## v4 Audit (5 issues) — ALL ADDRESSED

### v3 Fix Verification: 17/17 PASS, 0 regressions

### CRITICAL (1) — Fixed

#### ~~V4-C1. `${language,,}` in update.sh incompatible with macOS bash 3.2~~ RESOLVED
- **Resolution**: Replaced `${language,,}` with portable `$(echo "$language" | tr '[:upper:]' '[:lower:]')`. Works on bash 3.2+ and POSIX sh.

### MEDIUM (2) — Fixed

#### ~~V4-M1. Setup-wizard missing Astro/Remix/Deno/Bun auto-detection~~ RESOLVED
- **Resolution**: Added `astro`, `@remix-run/react` to framework detection; added `deno.json`/`deno.jsonc` and `bun.lockb`/`bunfig.toml` under new "Runtimes" section.

#### ~~V4-M2. CLAUDE.template.md Crash Recovery missing `## Command` field docs~~ RESOLVED
- **Resolution**: Added sentence explaining the Command field and cross-command mismatch detection.

### LOW (2) — No action needed

#### V4-L1. execute-task.md is 590 lines (31KB)
- **Status**: ACCEPTABLE — within Claude Code limits, well-structured.

#### V4-L2. Agent description fields are large
- **Status**: ACCEPTABLE — functional, no truncation risk.

---

---

## v5 Audit (1 issue) — FIXED

### v4 Fix Verification: ALL PASS, ZERO REGRESSIONS
- Bash portability: confirmed no bash 4+ features in update.sh or install.sh
- Placeholder consistency: 24/24 keys present in setup-wizard, update.sh migration, and all templates
- Agent template coverage: 14/14 agents fully covered
- Markdown formatting: no corruption
- 12 additional semantic/logic items evaluated and assessed as not actionable (by design, already handled, theoretical, or impossible)

### MEDIUM (1) — Fixed

#### ~~V5-M1. Phase 0.1 doesn't handle old wip.md files missing `## Command` field~~ RESOLVED
- **Resolution**: Added fallback to all 3 commands (execute-task, fix, refactor): "If the `## Command` field is missing (pre-v3 format), assume the current command and continue with recovery."

---

## Cumulative Statistics

| Metric | Value |
|--------|-------|
| Total issues found | 65 |
| Fixed | 58 |
| Accepted (by design) | 4 |
| Deferred (next release) | 2 |
| Moot (dead code removed) | 1 |
| Files modified across all audits | 18 unique files |
| Commands with constitution guard | All 8 that need it |
| Language-agnostic type check refs | All commands updated |
| wip.md cross-command safety | All 3 commands protected |
