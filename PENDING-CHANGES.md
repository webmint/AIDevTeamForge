# Pending Changes

Changes identified but not yet implemented. Address before or after end-to-end testing.

---

## 1. Defer git commits in /fix and /refactor until user reviews changes

**Affects**: `fix.md`, `refactor.md`

**Current behavior**: After the agent applies changes, a `[WIP]` commit is created immediately — before the user sees the diff. Verification, code review, and test assessment all happen on already-committed code.

**Proposed behavior**: After the agent applies changes, show the user the diff and ask for confirmation before committing. The user reviews the actual implementation (not just the proposal) before anything enters git history.

**Flow change**:
```
Before:  agent applies → WIP commit → verify → review → squash
After:   agent applies → show diff → user confirms → commit → verify → review → squash
```

**Why**: The user approved a PROPOSAL (diagnosis in /fix, refactoring plan in /refactor), not the actual code. The agent might implement differently than proposed. The user should verify the implementation matches before committing. In real life: developer changes code → checks diff → commits. Not auto-commit then check later.

**Crash safety tradeoff**: Without WIP commit, a crash after the agent but before user confirmation loses the work (only in working directory). Acceptable risk for standalone commands — crashes during interactive review are rare.

**Does NOT apply to /execute-task**: execute-task is a pipeline command where tasks build on each other via contracts. WIP commits are needed for multi-task continuity and crash recovery across batch execution.

---

## 2. Replace WebStorm-specific references with IDE-agnostic wording

**Affects**: `refactor.md`, `fix.md`, `verify.md`, `CLAUDE.template.md`

**Current**: 5 references to "WebStorm" and "JetBrains plugin" in command files. The functionality is IDE-agnostic (Claude Code works in VS Code, JetBrains, web, CLI) but the wording isn't.

**Locations**:
- `refactor.md` line 15: "JetBrains plugin passes active file/selection"
- `refactor.md` line 77: "start the WebStorm JS debugger"
- `fix.md` line 95: "start the WebStorm JS debugger"
- `verify.md` line 59: "Start the WebStorm JS debugger"
- `CLAUDE.template.md` line 91: "active file/selection from WebStorm"

**Proposed**: Replace with IDE-agnostic wording:
- "JetBrains plugin" → "IDE extension"
- "start the WebStorm JS debugger" → "start your IDE's JS debugger (the detection script handles port discovery automatically)"

**Note on WebStorm**: The debug port is dynamic (not a fixed number) and the port file location changes between WebStorm versions. That's why `chrome-devtools-mcp.sh` exists — it searches for `DevToolsActivePort` across all JetBrains version directories. The script already handles this. The user-facing message should NOT tell users to set a specific port — just "start the debugger, the script handles the rest." Only mention `CHROME_DEBUG_PORT` env var or `--remote-debugging-port` as a fallback for non-JetBrains setups.
