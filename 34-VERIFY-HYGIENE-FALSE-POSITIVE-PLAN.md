# 34 — /verify Hygiene False-Positive Fix

**Status**: BUILD DONE (2026-06-23) on `develop-2.0-init` — all 4 steps shipped behind agent loops; testForge20 e2e (reinstall) is the remaining user-driven gate.

## Problem

`/verify` returns a false-positive **NEEDS WORK** on clean features. Surfaced on testForge20
(`001`-style feature, 14/15 genuine AC PASS + mechanical PASS) — the verdict was driven entirely
by hygiene noise, not real defects. Recurring (matches the feature-001 memory note).

Four independent root causes (diagnosed 2026-06-23, code-verified):

- **RC1 — hygiene scans non-source files.** `check_hygiene` (`src/devforge/lib/_verify/_hygiene.py`)
  runs its leftover-artifact regexes (`debug_print`, `commented_code_block`, `bare_todo`) over
  **every file in the assembled diff**, no file-type gate. `changed_files` comes from
  `resolve_feature_scope` (`src/devforge/lib/_shared/feature_scope.py`) = raw
  `git diff --name-only merge-base..HEAD`, zero filtering. So it reads `specs/*.md`,
  `design/reference.html`, JSDoc prose. `// print()` in HTML commented markup matches
  `_DEBUG_PRINT_RE`; `### Expects:` spec headers match `commented_code_block` rules. = the 32
  "leftover artifacts." All prose.
- **RC2 — scope-creep baseline structurally incomplete.** `scope_creep` = whole diff MINUS
  `scope_baseline` (src-only `touched_files` union from `breakdown-handoff.json`, `_cli.py`).
  The pipeline ITSELF writes files the src-only baseline can never contain — `specs/<feature>/*.md`
  task records, `design/reference.html`, review-driven test files added after breakdown. All legit,
  all flag as scope-creep forever. = the 6 "scope-creep" files.
- **RC3 — both feed the verdict as a HARD BLOCKER.** `_verdict.py:309-324`:
  `hygiene_flags = scope_creep non-empty OR leftover_artifacts non-empty` → blocker → NEEDS WORK.
  The amplifier: RC1+RC2 noise doesn't just print, it BLOCKS the verdict.
- **RC4 — AC-14 grep self-match (spec + agent gap, not a helper bug).** The
  `! grep -rEn 'style=[{][{]' Tabs.tsx` check is authored in the spec. Naive negative-grep, no
  comment exclusion → matches the JSDoc that *documents* the rule it forbids. Compounding:
  `src/agents/ac-verifier.md` has zero guidance to inspect WHAT a grep matched — so the agent
  trusted the exit code and marked PARTIAL instead of reading the 2 doc-comment matches.

## Decisions

- **D1 — file-gate is a DENYLIST, not an allowlist.** Skip known prose extensions + forge-artifact
  dirs. Rationale: repo dropped hardcoded typed-language assumptions for polyglot targets
  (commit `dd1c29c`); an allowlist of code extensions re-introduces that fragility. The leftover
  patterns are inherently code; excluding known prose is robust + matches the existing
  "prefer false negatives" posture.
  - Skip path prefixes: `specs/`, `docs/`, `design/`, `audits/`, `research/`, `discover/`,
    `bugs/`, `.devforge/`
  - Skip extensions: `.md`, `.html`, `.htm`, `.txt`, `.json`, `.yaml`, `.yml`, `.csv`, `.svg`,
    `.lock`
- **D2 — hygiene is ADVISORY, not a blocker** (user-confirmed 2026-06-23). Remove `hygiene_flags`
  from the blocker set in `_verdict.py`; it stays as an informational line in the report. Real
  blockers (AC fail, mechanical fail, critical/high findings, constitution) unchanged. Rationale:
  hygiene is a heuristic; the module docstring itself says trust erodes faster from spurious flags;
  a heuristic must not own a blocking verdict.
- **D3 — no test-file name special-casing.** With D1 (artifact-dir exclusion) + D2 (advisory), a
  lone review-driven `*.test.*` surfaces as advisory noise, not a blocker. Adding name-matching to
  scope_creep = extra surface for no gain.

## Steps

### Step 1 + 2 — hygiene file-gate (RC1 + RC2) · `src/devforge/lib/_verify/_hygiene.py`
Add a `_is_code_file(path)` predicate (D1 denylist). Apply it before BOTH the leftover-artifact
scan AND the scope_creep comparison in `check_hygiene`. Step 2 (scope_creep proof) folds in — the
same gate excludes `specs/`/`design/` from scope_creep; add explicit scope_creep tests.
- Loop: **python-engineer** → **python-reviewer**.
- Verify: mixed tmp tree (`.py` with real `print(`, `.md` with `### Expects:`, `.html` with
  `// print()`) → only `.py` flags; `specs/x.md` never scope-creeps. Full `tests/lib/_verify/`
  green.

### Step 3 — hygiene → advisory (RC3, D2) · `src/devforge/lib/_verify/_verdict.py` + `_report.py`
Remove the `hygiene_flags` blocker block (`_verdict.py:309-324`); keep a reason/advisory line.
Reword `_report.py` hygiene lines (Code Quality section) to mark them explicitly non-blocking.
- Loop: **python-engineer** → **python-reviewer**.
- Verify: clean-but-hygiene-flagged case → APPROVED with advisory note; real blockers still
  NEEDS WORK. Cross-check `hygiene` across `_verify/`.

### Step 4 — ac-verifier grep-match guidance (RC4) · `src/agents/ac-verifier.md`
Add a rule: a negative-grep AC that matches must read the matched lines; matches confined to
comments / docstrings / JSDoc = behavioral PASS, not PARTIAL.
- Loop: **instruction-author** → **instruction-reviewer** → **claude-code-guide** (agent ships into
  `.claude/agents/`).
- Verify: re-read for the new rule; sentence-level hallucination check (no forward refs).

## Cross-cutting
- Full `tests/lib/_verify/` suite green after each step.
- Fixes are `src/`-side — need reinstall to reach testForge20. Re-running `/verify` as-is on the
  current instance reproduces the false positive until fix + reinstall.

## Verify (DoD)
- [x] Step 1+2: `_is_code_file` gates both scans; tests prove `.md`/`.html`/`specs/` excluded.
      `check_hygiene` returns `files_skipped`; both `_cli.py` fallback dicts + the 3 prose shape
      enumerations (`_cli.py` docstring, `main.md`, `report-format.md`) carry the key.
      python-engineer → python-reviewer (clean).
- [x] Step 3: `hygiene_flags` removed from the blocker set in `_verdict.py`; clean+flagged →
      APPROVED; advisory `reasons` line retained; `_report.py` + `report-format.md` mark hygiene
      advisory (stale "hygiene flag" blocker claim at `report-format.md:90` fixed).
      python-engineer → python-reviewer + instruction-author → instruction-reviewer (clean).
- [x] Step 4: ac-verifier rule 13 added (read negative-grep matches; doc-only matches → PASS,
      real-code matches → FAIL); both branches, tool-agnostic, modes enumerated.
      instruction-author → instruction-reviewer → claude-code-guide (clean).
- [x] Full `tests/lib/_verify/` green (496 passed, 17 subtests).
- [ ] testForge20 e2e (user-driven) — re-run `/verify` after reinstall, confirm APPROVED on the
      previously-false-NEEDS-WORK feature.
