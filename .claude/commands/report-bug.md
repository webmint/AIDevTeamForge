# /report-bug — Report a Bug for Later

Creates a structured bug report file in `bugs/` for tracking and later fixing via `/fix` or `/specify`.

## Usage
```
/report-bug "description of the bug"
/report-bug "description" --file path/to/suspected/file.ts
/report-bug "description" --file path/to/file.ts --severity Critical
```

## Arguments
- `$ARGUMENTS` — Description of the bug, optionally a `--file` flag pointing to the suspected file, and optionally a `--severity` flag (Critical, Warning, or Info). Severity defaults to Warning. If empty, ask the user to describe the bug.

## PHASE 1: Parse Input

Extract from `$ARGUMENTS`:
1. **Description**: The quoted or unquoted text describing the bug
2. **File** (optional): Value after `--file` flag
3. **Severity** (optional): Value after `--severity` flag — must be one of: Critical, Warning, Info. Defaults to Warning

If `$ARGUMENTS` is empty, ask the user to describe the bug before proceeding.

If `--file` is provided, verify the file exists. If it doesn't, warn the user but continue (the bug report is still useful without a valid file path).

## PHASE 2: Determine Next Bug Number

1. Scan the `bugs/` directory for existing `.md` files
2. Extract the highest NNN prefix (e.g., if `003-something.md` exists, highest is 3)
3. Next bug number = highest + 1 (or 1 if no bugs exist)
4. Zero-pad to 3 digits: 001, 002, 003...
5. Generate a short kebab-case slug from the description (2-4 words, lowercase)

## PHASE 3: Write Bug File

Create `bugs/NNN-short-description.md`:

```markdown
# Bug NNN: [Short Title]

**Status**: Open
**Severity**: [Critical | Warning | Info]
**Source**: manual
**Reported**: [YYYY-MM-DD]
**Fixed**:

## Description

[User's bug description]

## File(s)

| File | Detail |
|------|--------|
| [path/to/file.ts] | [line number or area, if known] |

## Evidence

[If the user mentioned error messages, stack traces, or observed behavior, include it here. Otherwise: "Reported by user."]

## Fix Notes

[To be filled in by /fix]
```

If no `--file` was provided, write the File(s) table as:

```markdown
| File | Detail |
|------|--------|
| (not specified) | — |
```

## PHASE 4: Confirm

Present:

```
Bug reported: bugs/NNN-short-description.md

  Severity: [severity]
  File(s): [file path or "not specified"]

To fix this bug, run: /fix bugs/NNN-short-description.md
To escalate to a full spec: /specify "Bug NNN: [title]"
```

## IMPORTANT RULES

1. **One bug per file** — if the user describes multiple bugs, create separate files for each
2. **Severity defaults to Warning** — only use Critical if the user explicitly says so or the bug clearly prevents core functionality
3. **Don't diagnose** — this command only records the bug. Diagnosis happens in `/fix`
4. **Kebab-case slugs** — 2-4 words, descriptive: `null-cart-total`, `missing-auth-check`, `broken-date-format`
5. **Sequential numbering** — always scan `bugs/` to find the next number, never hardcode or guess