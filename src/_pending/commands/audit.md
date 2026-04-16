# /audit — Adversarial Codebase Audit

Standalone, on-demand whole-codebase audit for periodic "second opinion" quality reviews. Invokes review agents in ADVERSARIAL MODE to hunt for mislogic, contradictions, and lying code. Read-only. Writes a dated report to `audits/YYYY-MM-DD-audit.md` and prints inline. **NOT part of any workflow chain — invoke manually after several specs ship.**

> This command writes audit reports for the **user's project** to `audits/` at the workspace root. It is unrelated to the AIDevTeamForge template repo's own `QUALITY-AUDIT.md` file (which audits the template itself).

## Usage
```
/audit                          # full codebase audit (default)
/audit --full                   # explicit full codebase audit
/audit src/auth/                # deep-dive one directory
/audit path/to/file.ts          # audit a single file
/audit path/to/file.ts:42-87    # audit a code selection
/audit --uncommitted            # audit only uncommitted changes
```

## Arguments
- `$ARGUMENTS` — empty (default: `--full`), `--full`, `--uncommitted`, file path (with optional `:start-end`), or directory path. Empty means **full codebase**, deliberately differing from `/security` where empty means uncommitted.

## PHASE 1 — Load Context & Guard

**Step order matters**: cheapest guards first, mode determination before mode-conditional I/O.

1. **Determine mode from `$ARGUMENTS` (no I/O)**:
   - Empty or `--full` → **broad mode**
   - `--uncommitted` → **narrow mode**
   - Looks like a path (file or directory) → **narrow mode**
   - Anything else → stop with usage hint

2. **Agent-existence check (cheapest fail-fast)**: check which audit-capable agents exist in `.claude/agents/`:
   - `code-reviewer.md`
   - `architect.md`
   - `qa-engineer.md`
   - `security-reviewer.md`

   If **zero** exist, stop immediately with:
   ```
   ⛔ No audit-capable agents installed. Run /setup-wizard first to install at least one of: code-reviewer, architect, qa-engineer, security-reviewer.
   ```
   If 1–3 exist, proceed and note the missing ones for the report's "Agents skipped (not installed)" section.

3. Read `constitution.md`. **Guard**: if it contains `_Run /constitute to populate_`, stop with:
   ```
   ⛔ constitution.md has not been populated yet. Run /constitute before /audit.
   ```

4. Read `CLAUDE.md` — note Source Root, project type, framework, language. **Define `audits/` location**: `audits/` lives at the **workspace root** (the directory containing `CLAUDE.md`), NEVER under Source Root, even in wrapper mode.

5. Read `.claude/memory/MEMORY.md` — extract pitfalls, past incidents, lessons relevant to the audit.

6. **Recurring-issues lookup (broad mode only — skip entirely in narrow mode)**:
   - Glob `specs/*/review.md`, filter to files modified in the **last 90 days**. If none qualify, skip this step with a note for the report: "No recent reviews to cross-reference."
   - From the qualifying files, take up to the **5 most recently modified**.
   - Extract **Critical findings only** (skip High/Medium/Info to keep the list bounded).
   - Cap the total at **25 entries** — if more, take the most recent.
   - This becomes the "Recurring Issues to Verify" list. This is the audit's differentiator over `/review`: it can see drift across features.

## PHASE 2 — Determine Scope

There are two pipeline shapes: **broad** (`--full`) and **narrow** (file / directory / `--uncommitted`). Narrow scopes simplify the pipeline.

### Broad mode (`--full` / empty) — full pipeline

Count source files under Source Root (exclude `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `vendor`, test files):

- **`<50` files**: read all source files. Single agent invocations on the full set.
- **`50–200` files**: identify module boundaries (top-level source directories). Module-based subagent fan-out — one agent instance per top-level source dir, per agent type.
- **`200+` files**: sample-based scan. Prioritize these categories:
  - Entry points (main files, index files, app bootstrap)
  - Auth/authorization code (middleware, guards, login handlers)
  - API handlers (routes, controllers, endpoints)
  - Data access (database queries, ORM usage, repositories)
  - Configuration (env handling, secrets loading)
  - Core domain modules

All Phase 4 sub-phases run (recurring-issues mapping, cross-agent consensus, force-rank).

### Narrow mode (`--uncommitted` / file / directory) — simplified pipeline

- **`--uncommitted`**: run `git diff` and `git diff --cached` to collect changed files. If no uncommitted changes, stop with: `No uncommitted changes. Use --full or specify a path.`
- **File path**: read the file (full content even if `:start-end` line range given). If line range specified, mark it as the focus area but include the full file for context. Read up to 3 import-related files for cross-file logic flow.
- **Directory path**: glob source files in the directory, exclude tests/config/assets. If more than 20, prioritize by criticality heuristic (auth, API, data access).

**Pipeline simplifications for narrow mode**:
- **Skip the recurring-issues lookup** (Phase 1 step 6). The narrow target may not be in any spec, and cross-feature drift isn't the question being asked.
- **No module fan-out**. Run all available agents on the same input set, single-batch.
- **Cross-agent consensus still applies** but on narrower input it will be rare — that's fine.
- **Force-rank still runs** but produces a Top 5 (not Top 10).

### Source Root note

If `CLAUDE.md` specifies `SOURCE_ROOT != "."`, source files live under that path — pass this to every agent so they read from the correct location. **`audits/` still lives at the workspace root regardless.**

## PHASE 3 — Launch Adversarial Agents

For each **available** agent (from Phase 1 step 2), build the prompt as follows:

1. Read `.claude/agents/<agent>.md` and include its **full content** as the opening section of the agent prompt.
2. Append the **Adversarial Preamble** (verbatim, see below).
3. Append the **Mislogic Hunt Checklist** (verbatim, see below).
4. Append the agent-specific focus block (see 3.1).
5. Append the target files, constitution rules, MEMORY.md excerpts, the "Recurring Issues to Verify" list from Phase 1 step 6 (broad mode only — narrow mode skips this), and the Source Root note.
6. Append the **Output Contract** (see 3.2 — every agent must follow it identically so the parent can parse it).
7. **Append the closing mode reminder as the very last instruction** (see 3.3) — the most-recent instruction wins over the agent's baked-in polite tone.
8. Instruct the agent to write its findings to `audits/.tmp-{agent-name}.md` instead of returning them inline. The parent will stream-consolidate from these temp files in Phase 4.

### 3.1 — Agent-specific focus blocks

**code-reviewer** (primary mislogic hunter):
> Your primary mission in ADVERSARIAL MODE: find naming-vs-behavior mismatches, lying comments, dead branches, off-by-one errors, inverted conditions, copy-paste bugs, and scope-creep residue. Constitution violations remain Critical and are never downgraded.

**architect** (cross-module contradictions):
> Your primary mission in ADVERSARIAL MODE: find cross-module contradictions, layering drift, SOLID violations that compound across files, contradictory domain rules in different files, and dependency direction violations. You are looking for the "two files that can't both be right" situations.

**qa-engineer** (logic blind spots, NOT test writing):
> Your primary mission in ADVERSARIAL MODE: treat untested branches as **logic blind spots** where mislogic hides. Do **NOT** write tests. Report each significant untested branch as an audit finding with severity based on how much domain logic is uncovered.
>
> **Branch scope (strict)**: only consider untested **public functions and methods in business-logic modules** (services, controllers, use cases, domain logic). Do NOT report: private helpers, pure utility functions, type-only files, configuration files, generated code, or files matching `*.test.*` / `*.spec.*`.
>
> If the project has zero tests, return a single High finding: `"No tests found — entire codebase is a logic blind spot"` and stop.

**security-reviewer** (drift scan):
> Your primary mission in ADVERSARIAL MODE: scan for security regressions and drift in code that has **NOT** been touched in recent features. You are the second line of defense after per-feature `/review`. Assume nothing is safe just because it is old.

### 3.2 — Output Contract (every agent must follow this exactly)

Each agent writes its findings to `audits/.tmp-{agent-name}.md` using this **fixed parseable format**. The parent command will regex-parse these headings, so deviation breaks the pipeline.

````
# Agent: {agent-name}
# Status: complete
# Finding count: N

## Finding 1
Severity: Critical | High | Medium | Info
File: path/to/file.ext
Line: 42
Pattern: <one-line pattern name, e.g. "Naming lie">
Confidence: Certain | Likely | Speculative
Evidence:
```
<verbatim quoted code or comment, copy-pasted from the file, no edits>
```
Why it's wrong: <one paragraph>
Remediation: <one paragraph>

## Finding 2
[same fields]

...

## Top 5 Priorities (this agent only)
1. Finding #N — <one-line description>
2. ...
````

**Hard rules for the agent**:
- **Cap at 30 findings.** Self-triage. If you have more, drop the lowest-confidence ones.
- **Every finding MUST have a verbatim Evidence block.** No quote = no finding. The parent will validate this and discard ungrounded findings (see Phase 4).
- **The Evidence block must be a literal copy from the file.** Do not paraphrase, do not abbreviate, do not insert `...`. If the relevant code is more than 20 lines, cite the most important 5–10 lines.
- **The Line field must point to the first line of the Evidence block in the actual file.**
- If the agent fails partway, it must still write a temp file with `# Status: failed` and a `# Reason: <message>` line, so Phase 4 can detect failure.
- If the agent finds nothing, write a temp file with `# Status: complete` and `# Finding count: 0`. Empty file ≠ failure.

### 3.3 — Closing mode reminder (verbatim, appended as the last instruction in every agent prompt)

```
REMEMBER: ADVERSARIAL AUDIT MODE is in effect. Bias toward false positives ONLY when grounded in verbatim quotes from the actual code. Fabrications are forbidden. Cap your findings at 30 — self-triage to the most important. Every finding needs a verbatim Evidence quote and a Confidence tier. Do not soften. Critical of code, not people.
```

### 3.4 — Batched parallel launch

To avoid the context exhaustion failure mode documented in CHANGELOG 1.27.0 for `/verify`:

- **Batch A (parallel)**: code-reviewer + architect → wait → both write to `audits/.tmp-*.md`.
- **Batch B (parallel)**: qa-engineer + security-reviewer → wait → both write to `audits/.tmp-*.md`.

For 200+ file codebases using module subagents, run **one module** through Batch A → Batch B before moving to the next module. Do **not** fan out every module in parallel.

## PHASE 4 — Stream-Consolidate, Verify, & Rank

**Critical**: do NOT load all findings from all agents into context at once. The parent command must stream them. Also: **verify every finding before accepting it** — adversarial mode invites hallucination, and grounding checks are the antidote.

### 4.1 — Stream agent outputs

For each agent in `[code-reviewer, architect, qa-engineer, security-reviewer]`:

1. Check if `audits/.tmp-{agent}.md` exists.
   - **Missing**: log `"Agent failed: {agent} (no output)"` to a `failed_agents` list. Skip and continue.
   - **`Status: failed`**: log `"Agent failed: {agent} ({reason})"` to `failed_agents`. Delete the temp file. Skip and continue.
   - **`Status: complete, Finding count: 0`**: log `"Agent ran clean: {agent}"`. Delete the temp file. Continue.
   - **`Status: complete, Finding count > 0`**: parse using the regex format from the Output Contract.
2. For each parsed finding, run **finding validation** (4.2) before adding to the working list.
3. Delete the temp file after parsing.

### 4.2 — Finding validation (anti-hallucination guard)

For each finding extracted from an agent's temp file, run these checks **in order** and **discard the finding** if any check fails. Discarded findings are tallied for the report's "Findings discarded by validation" count.

1. **File exists check**: confirm the cited file path exists on disk under Source Root (or at workspace root for config files). Fail → discard.
2. **Line number sanity**: read the file, count lines, confirm the cited Line number is `1 ≤ N ≤ total_lines`. Fail → discard.
3. **Verbatim quote check (the critical guard)**: read the file content around the cited line (Line ± 30 lines for context). Confirm the Evidence block's content appears as a **literal substring** in the file. Whitespace-normalize (collapse runs of spaces, ignore trailing whitespace) before comparing, but require exact token match. Fail → discard.
4. **Evidence non-empty check**: confirm the Evidence block is not empty, not just `...`, not just whitespace. Fail → discard.
5. **Pattern field present**: confirm the Pattern field is non-empty. Fail → discard (these are unstructured findings that won't merge correctly).

Findings that pass all 5 checks enter the working list. Track the discard count per agent for the report.

### 4.3 — Cross-agent consensus (exact-match only, no LLM judgment)

After all four agents are streamed in:

1. Build a hash key for every finding: `sha1(file_path + ":" + line_number + ":" + normalized(pattern))`. Normalize the pattern by lowercasing and stripping punctuation.
2. Group findings by hash key.
3. For each group with **2 or more findings from different agents**:
   - Merge into a single finding (keep the highest-severity Evidence block).
   - Tag `[CROSS-AGENT]`.
   - Bump severity by exactly one level (Info → Medium → High → Critical, capped at Critical).
4. Findings whose hash key is unique stay as-is.

**No semantic matching.** "Similar findings" do NOT merge. The parent command does not get to decide that two differently-worded findings are "really the same" — that path leads to confabulated consensus.

### 4.4 — Recurring-issues mapping (broad mode only — skip in narrow mode)

For each entry in the Phase 1 step 6 "Recurring Issues to Verify" list:

1. Extract the past finding's file path and a 5–10 word "fingerprint" of its description (the most distinctive nouns/verbs).
2. Check the working list for findings whose `(file_path, pattern)` matches the past finding's `(file_path, fingerprint)` exactly. **No fuzzy matching** — exact substring on both fields.
3. Apply mapping:
   - **No match in working list, file unchanged**: tag the past entry "RESOLVED" in the report's Recurring Issues table. Do not add to working list.
   - **Match in working list at same file**: tag the working-list finding `[RECURRING]` and bump severity one level.
   - **Match in working list at additional files** (same fingerprint, different file paths): tag `[RECURRING-SPREAD]` and bump severity by two levels (capped at Critical).
4. **Algorithmic only.** The parent does not LLM-judge whether two findings are "really" the same recurring issue. Exact match or no match.

### 4.5 — Force-rank the Top 10

Score each finding:

```
score = severity_weight × confidence_weight × cross_agent_bonus × recurring_bonus

where:
  severity_weight   = {Critical: 8, High: 4, Medium: 2, Info: 1}
  confidence_weight = {Certain: 3, Likely: 2, Speculative: 1}
  cross_agent_bonus = 1.5 if [CROSS-AGENT] else 1.0
  recurring_bonus   = 2.0 if [RECURRING-SPREAD], 1.5 if [RECURRING], 1.0 otherwise
```

Sort descending. Take the top 10 (or top 5 in narrow mode).

### 4.6 — Truncation safety

If the parent's context fills before consolidation completes (e.g., on very large codebases with 4 large temp files), the partial consolidated list still goes into the report with a note: `⚠️ Consolidation truncated due to context limits — N agent reports merged out of M.` Better partial than nothing. The temp files left undeleted will be cleaned up by the next `/audit` run (Phase 5 step 0).

## PHASE 5 — Write Report

0. **Cleanup stale temp files**: at the start of Phase 5, delete any leftover `audits/.tmp-*.md` files from a prior interrupted run. (Phase 4 deletes them on success; this catches the failure case.)
1. `mkdir -p audits` (top-level `audits/` directory at workspace root, **not** `docs/audits/`, even in wrapper mode).
2. **First-run only**: if `audits/.gitignore` does not exist, create it with the single line `.tmp-*.md`. This prevents temp files from ever being committed even if `audits/` is added to git.
3. Compute output path: `audits/YYYY-MM-DD-audit.md`. If exists, append `-2`, `-3`, ... until unused.
4. Write the report (format below).
5. **Do NOT commit. Do NOT stage.** Let the user decide whether to keep the audit in git history.

### Report format

```markdown
# Audit Report — YYYY-MM-DD

**Scope**: [full / uncommitted / path]
**Files audited**: [count]
**Agents invoked**: [list, with "skipped (not installed)" for missing]
**Recurring-issue reviews consulted**: [list of specs/*/review.md, or "none"]
**Source Root**: [from CLAUDE.md]
**Framework / Language**: [from CLAUDE.md]

## Top 10 Priorities
Force-ranked across all buckets. Fix these first.
1. [severity] [file:line] — [one-line description] [confidence] [tags]
...

## Critical Findings

### Mislogic / Logic Contradictions
- [file:line] — [description]
  Evidence:
  ```
  [verbatim quoted code/comment]
  ```
  Why it's wrong: [the contradiction]
  Remediation: [specific fix]
  Confidence: Certain | Likely | Speculative
  Tags: [CROSS-AGENT] [RECURRING] [CONSTITUTION-VIOLATION]

### Cross-Module Contradictions
[same finding format]

### Security Regressions
[same finding format]

### Constitution Violations
(Always Critical, never downgraded.)
[same finding format]

## High Findings
[same sub-sections]

## Medium Findings
[same sub-sections]

## Info / Observations
[same sub-sections]

## Logic Blind Spots (Untested Branches)
[from qa-engineer]

## Recurring Issues Status
| Past Review | Finding | Status |
|---|---|---|
| specs/003-foo/review.md | Null check bypass in X | STILL PRESENT, SPREAD TO 4 FILES |
| specs/005-bar/review.md | Race condition in Y | RESOLVED |

## Not Audited
- Runtime behavior (no dynamic analysis)
- Dependency CVEs (run `npm audit` / `pip audit` separately)
- Performance (out of scope — use /review)
- UI/design consistency (out of scope)
- Infrastructure / deployment config

## Summary
- Critical: N | High: N | Medium: N | Info: N
- Cross-agent consensus findings: N
- Recurring (unresolved): N
- Agents skipped (not installed): [list]
- Agents failed (ran but errored): [list with reasons]
- **Findings discarded by validation**: N total
  - Failed file-exists check: N
  - Failed line-number sanity: N
  - Failed verbatim-quote check: N (likely hallucination)
  - Failed evidence-non-empty check: N
  - Failed pattern-field check: N

## Methodology
Adversarial mode — deliberate bias toward false positives over false negatives,
but every finding is grounded in a verbatim quote from the actual code.
Findings without grounding are discarded by Phase 4 validation. Confidence
tiers indicate certainty. "Speculative" findings are hypotheses, not verdicts.

If "Failed verbatim-quote check" count is high (>5), the agents are
hallucinating evidence — review the agent prompts for tone drift.
```

## PHASE 6 — Present Inline Summary

Print to console:

```
## Audit Complete

**Scope**: [scope]
**Findings**: N Critical, N High, N Medium, N Info
**Cross-agent consensus**: N
**Recurring (unresolved)**: N
**Agents skipped**: [list or "none"]
**Findings discarded by validation**: N (verbatim-quote failures: N)

### Top 5 Priorities
1. ...
2. ...
3. ...
4. ...
5. ...

Full report: audits/YYYY-MM-DD-audit.md

Not committed — review, then commit if you want audit history in git, or delete.

NOTE: /audit is adversarial. It biases toward false positives over false
negatives. "Speculative" findings are hypotheses, not verdicts. Review with
that in mind.
```

## IMPORTANT RULES

1. **Read-only** — no source modifications, no fixes, no auto-commit of the audit report.
2. **Standalone** — `/audit` is NEVER invoked by another command, never part of any workflow chain, never auto-triggered.
3. **Grounded adversarial bias** — false positives are acceptable ONLY when grounded in verbatim quotes from real code. Fabrications are forbidden. Phase 4 validation discards ungrounded findings.
4. **Constitution violations always Critical** — never downgraded, regardless of confidence.
5. **Critique code, not people** — findings describe what is wrong with the code, never who is wrong. No hostile language in committed output.
6. **Algorithmic merging only** — cross-agent consensus and recurring-issue tags are computed by exact-match hash keys, never by LLM "is this similar" judgment. No semantic dedupe.
7. **Dated reports, not overwritten** — re-runs on the same day append `-2`, `-3` suffix. The user keeps history across audits.
8. **Not committed** — the user decides whether to keep audit history in git. Temp files (`audits/.tmp-*`) are gitignored on first run.
9. **Context-aware batching** — large codebases use the two-batch + module-subagent strategy AND stream-consolidation. Do NOT fan out all agents on all files at once, do NOT load all findings into context at once (CHANGELOG 1.27.0 documents the failure mode).
10. **Skip missing agents gracefully** — note them in the report; only fail if all four are missing. Failed agents (ran but errored) are tracked separately from missing agents.
11. **Wrapper-mode aware** — pass Source Root to every agent for source files; `audits/` always lives at workspace root, never under Source Root.
12. **Mode reminder is the last instruction** — every agent prompt ends with the Adversarial Mode reminder so the most-recent instruction wins over the agent's baked-in polite tone.
13. **Cap findings per agent at 30** — agents must self-triage. The Output Contract enforces this.
14. **Verbatim Evidence required** — every finding must include a literal quote from the actual file. The Output Contract enforces this; Phase 4.2 validates it.

## The Adversarial Preamble (verbatim, injected per agent invocation)

```
=== ADVERSARIAL AUDIT MODE ===

You are reviewing this code as if in a heated senior-level code review debate.
Your job is to be VERY critical and to ARGUE with the code. Question every
assumption. Find logical contradictions, naming-vs-behavior mismatches,
comments that lie about what the code actually does, and rules that
contradict each other across files.

THE LINE BETWEEN FALSE POSITIVE AND FABRICATION:
- False positive = "I think this code is wrong, here is the actual quoted code,
  here is why I think it is wrong." This is acceptable and encouraged.
- Fabrication = "this code is wrong" with invented evidence, made-up line
  numbers, or quotes that do not appear in the file. This is FORBIDDEN.
- Every finding MUST include a verbatim quote copy-pasted from the actual
  source file. If you cannot quote the exact problematic code, you cannot
  report the finding. No exceptions.
- Every finding MUST cite a real file:line that exists. Do not guess line
  numbers. Do not pattern-complete with plausible-sounding examples (e.g.
  "maxRetries=3 vs maxRetries=5") unless those exact values exist in the code.
- The Mislogic Hunt Checklist below contains EXAMPLES of what to look for,
  NOT a list of bugs you should find. If the codebase has none of these
  patterns, report none of these patterns.

Ground rules:
1. Bias toward false positives over false negatives — but only when grounded
   in real, quoted code. Ungrounded suspicion is not a finding.
2. Do NOT soften findings. Do NOT add "this is probably fine" disclaimers.
3. Do NOT assume good intent in unclear code. If code is unclear, call it
   out and demand the justification that should have been in a comment.
4. Treat every comment as a claim that must be verified against the code
   below it. Comments that no longer match the code are findings — but you
   must quote both the comment AND the contradicting code.
5. Treat naming as a contract. `validateEmail` that returns early on null
   without validating is a lying name and a finding — but you must quote
   the function body to prove it.
6. You are looking for the bug the team missed. Assume it exists. Find it.
   But if you cannot ground a suspicion in actual code, do not invent one.

Critique the CODE, not the PEOPLE. Every finding describes what is wrong
with the code, never who is wrong. "This function is misnamed" — good.
"The author was careless" — forbidden.

Every finding must include a Confidence tier:
- Certain: bug is demonstrable from the code alone
- Likely: strong evidence; runtime behavior could change the conclusion
- Speculative: hypothesis worth checking, not a verdict

Constitution rule violations are ALWAYS Critical, never downgraded,
regardless of confidence. Mark them [CONSTITUTION-VIOLATION].
```

## The Mislogic Hunt Checklist (verbatim, appended to each agent prompt)

```
=== MISLOGIC HUNT CHECKLIST ===

In addition to your normal review, systematically hunt for these patterns.
These are EXAMPLES of what to look for, NOT a list of bugs you should find.
If the codebase has none of these patterns, report none.

Naming lies
- Function name promises X but body does Y (validate* that doesn't validate,
  is* that returns non-boolean, get* with side effects, set* that also reads,
  pure* that mutates)
- Variable name contradicts the value (`count` holding a list, `enabled`
  defaulting to true but used as "disabled")

Comment lies
- Comments describing behavior that no longer matches the code
- "TODO: fix X" where X is now broken differently
- Doc comments listing parameters the function no longer accepts
- "Returns null on error" comments where the code throws

Control-flow mislogic
- Off-by-one (< vs <=, exclusive-vs-inclusive range bugs)
- Inverted conditions (if (!isValid) proceed-happy-path)
- Unreachable branches (if (x) ... else if (x && y) ...)
- Dead defaults
- Early-return that skips cleanup
- Truthiness collapse bugs (0, "", [], null, undefined treated alike)
- Boolean operator confusion (&& vs || in guard chains)

Cross-file contradictions
- Two files encoding the same business rule with different thresholds
- Config A says one value, code B hardcodes a different value
- Enum in one file missing cases the consumer assumes exist
- Type X defined in two places with drifted shapes
- Same constant redeclared with different values
- Import graph claims acyclic but contains a cycle

Configuration mislogic
- Config that contradicts itself (prod=true + debug=true)
- Feature flag checked but never set, or set but never checked
- Env var referenced in code but missing from .env.example
- Default in code differs from default in docs

Error-handling mislogic
- try/catch that swallows errors and logs "success"
- Error path returning the same shape as success path with no discriminator
- Catch that re-throws but loses the stack
- Error message that doesn't match the error it describes

Validation mislogic
- Validation after use (validate(x) called after const y = x.foo)
- Client-side check with no server-side enforcement
- Allowlist that is actually a denylist (check the operator)
- Sanitization on output but not input, or vice versa

Dead / zombie code
- Functions never called
- Imports never used
- Branches unreachable given the type system
- Parameters always passed the same value

Scope creep residue
- Code for cut features whose plumbing remains
- Comments referring to removed systems
- Abstractions with one consumer that never grew the second one

For each mislogic finding, state:
- Pattern matched
- Evidence (verbatim quoted code/comment from the file)
- Why it's wrong (the contradiction)
- Remediation
```