# /security — Security Review

On-demand security review of specific files, directories, or the entire codebase. Uses the security-reviewer agent with constitution and memory context. Read-only — reports findings, does not modify code.

## Usage
```
/security path/to/file.ts                    # review a specific file
/security path/to/file.ts:42-87             # review a code selection
/security src/api/                            # review a directory
/security                                     # review uncommitted changes
/security --full                              # full codebase scan (existing projects)
```

## Arguments
- `$ARGUMENTS` — File path (with optional `:start-end` line range), directory path, `--full`, or empty.
  - **File path**: Review that specific file. If line range provided, focus on that section but read the full file for context.
  - **Directory**: Review all source files in that directory (exclude `node_modules`, `dist`, `build`, `__pycache__`, etc.).
  - **Empty**: Review all uncommitted changes (`git diff` + `git diff --cached`).
  - **`--full`**: Full codebase security scan. Uses module-based subagent strategy for large codebases.

## PHASE 1: Load Context

1. Read `constitution.md` — extract security-related rules (Section 3.2 Error Handling, Section 4.2 NEVER DO, any project-specific security rules)
2. Read `.claude/memory/MEMORY.md` — check for known security pitfalls
3. Read `CLAUDE.md` — note Source Root (for wrapper mode), project type, framework

## PHASE 2: Determine Scope

### If file path provided:
1. Read the target file completely
2. If line range specified, note it as the focus area but include the full file for context
3. Identify related files: what does this file import? What imports it? (Read up to 3 related files for data flow context)

### If directory provided:
1. Glob all source files in the directory (exclude test files, config files, assets)
2. If more than 20 files, prioritize: files handling user input, auth, API calls, data storage, file operations
3. Read prioritized files (up to 20)

### If empty (uncommitted changes):
1. Run `git diff` and `git diff --cached` to identify changed files
2. Read the changed files completely
3. If no uncommitted changes, inform user: "No uncommitted changes found. Specify a file, directory, or use `--full` for full codebase scan."

### If `--full`:

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, scan that path.

Count source files (exclude `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `vendor`, test files):

**< 50 files**: Read all source files. Launch a single security-reviewer agent.

**50-200 files**: Identify module boundaries (top-level source directories). Launch one security-reviewer subagent per module. Each subagent receives its module's files + constitution security rules.

**200+ files**: Sample-based scan. Prioritize these file categories:
- Entry points (main files, index files, app bootstrap)
- Auth/authorization code (middleware, guards, login handlers)
- API handlers (routes, controllers, endpoints)
- Data access (database queries, ORM usage, repository files)
- Configuration (env handling, secrets loading, CORS setup)
- User input processing (forms, parsers, validators)
- File operations (upload handlers, file system access)
Launch one security-reviewer subagent per module on priority files only.

## PHASE 3: Launch Security Review

### Targeted mode (file, directory, uncommitted)

Launch the **security-reviewer** agent with:
1. The target files content
2. Constitution security rules
3. MEMORY.md security-related entries
4. Related files for data flow context (if file mode)
5. Instruction: "Review the provided code for security vulnerabilities. Check all categories from your Security Review Checklist. Report findings with severity, file:line references, and remediation suggestions."

### Full codebase mode

For each module/batch, launch a security-reviewer subagent with:
1. The module's source files
2. Constitution security rules
3. Instruction: "Scan for security vulnerabilities. Focus on: hardcoded secrets, injection vectors, auth gaps, unsafe code patterns, data exposure, input validation gaps. Return structured findings."

After all subagents complete, consolidate:
- Merge all findings
- Deduplicate overlapping issues (same pattern in multiple files → one finding with multiple locations)
- Sort by severity (Critical → High → Medium → Info)

## PHASE 4: Present Report

```
## Security Review

**Scope**: [file / directory / uncommitted changes / full codebase]
**Files reviewed**: [count]
**Framework**: [from CLAUDE.md]

### Critical (exploit risk)
- [file:line] [CWE-XXX] — [description]
  → Remediation: [specific fix]

### High (security weakness)
- [file:line] [CWE-XXX] — [description]
  → Remediation: [specific fix]

### Medium (defense-in-depth gap)
- [file:line] — [description]
  → Remediation: [suggestion]

### Info (hardening suggestion)
- [observation]

### Not Checked
- Dependency vulnerabilities (run `npm audit` / `pip audit` / `cargo audit` separately)
- Runtime behavior (requires dynamic testing)
- Infrastructure configuration (outside code scope)
- Cryptographic implementation correctness (requires specialist review)

### Summary
- Critical: N | High: N | Medium: N | Info: N
- Top priorities: [top 3 most important findings]
```

## IMPORTANT RULES

1. **Read-only** — do not modify any files, do not fix issues, do not commit anything
2. **Be specific** — cite file and line, include CWE identifier for Critical/High
3. **Include remediation** — every finding must have a specific fix suggestion
4. **No false confidence** — always include the "Not Checked" section. This is code review, not a penetration test
5. **Check constitution** — project-specific security rules override generic advice
6. **Prioritize exploitable issues** — real vulnerabilities over theoretical risks
7. **Data flow matters** — trace user input from entry point to storage/output. Single-file review misses flow-based vulnerabilities, so read related files for context
