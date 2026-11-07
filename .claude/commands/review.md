# /review — Expert Code Review

Launches specialist review agents (security, performance, test assessment) on completed feature code. Produces a structured review report for `/verify` to incorporate into its verdict.

## Usage
```
/review [spec-file]
```

## Arguments
- `$ARGUMENTS` — Optional path to a spec file or its feature directory in `specs/`. If empty, use the most recently modified spec in `specs/`.

## PHASE 1: Load Context

**Source Root**: Read `CLAUDE.md` and note the Source Root (default: `.`). When reading task completion notes, changed files are listed relative to the repository root. In wrapper mode (`SOURCE_ROOT != "."`), source files live under the Source Root path — inform agents of this so they read files from the correct location.

1. Read the spec file (from `$ARGUMENTS` or most recent feature directory in `specs/`)
2. Read the feature's `plan.md` (for architecture decisions — needed by performance-analyst)
3. Read all task files in `specs/NNN-feature/tasks/` — extract:
   - Task titles and completion status
   - Completion Notes (files changed, deviations)
4. Read `constitution.md`
   - **Guard**: If `constitution.md` contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/review`."
5. Read `.claude/memory/MEMORY.md` (for known pitfalls, security patterns, and performance anti-patterns from prior work)
6. Collect the list of all changed files across all tasks (from task completion notes) and deduplicate

**Completeness warning**: Read `specs/[feature]/tasks/README.md`. If any task has Status other than `Complete`:
```
⚠️ Not all tasks are Complete. Review findings may change after remaining tasks are executed.
Proceeding with review of current state.
```

## PHASE 2: Security Review

If `.claude/agents/security-reviewer.md` exists, launch the **security-reviewer** agent on all files changed across the feature's tasks.

Read `.claude/agents/security-reviewer.md` and include its **full content** as the opening section of the agent prompt.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The feature spec (for context on what was built)
3. The constitution's security-related rules (if any)
4. Relevant entries from MEMORY.md (known security pitfalls, past incidents)

Instruct the agent: "If any finding involves a constitution rule violation, mark it Critical regardless of other severity factors."

Collect the agent's findings with severity levels (Critical, High, Medium, Info).

If the agent doesn't exist, skip this phase and note in the report: _Skipped — no security-reviewer agent configured._

## PHASE 3: Performance Review

If `.claude/agents/performance-analyst.md` exists, launch the **performance-analyst** agent on all files changed across the feature's tasks.

Provide the agent with:
1. The list of all changed files
2. The feature spec (especially any performance-related acceptance criteria)
3. The plan's architecture decisions (from `plan.md`, for context on expected data flow)
4. Relevant entries from MEMORY.md (known performance anti-patterns)

Collect the agent's findings with impact levels (High, Medium, Low).

If the agent doesn't exist, skip this phase silently.

## PHASE 4: Test Assessment

If `.claude/agents/qa-engineer.md` exists, launch the **qa-engineer** agent.

Provide the agent with:
1. The list of all changed files (from all task completion notes)
2. The spec's acceptance criteria (for AC-to-test traceability)
3. The feature's test files (if any were created or modified across tasks)
4. The checklist `.claude/checklists/test-lens.md`, when it exists and its `**Gate**:` line does not say `off`: the agent reports every failed item by its id

The agent assesses: test coverage gaps for changed code, untested AC items, missing edge case tests, and test strength (would each test fail if the feature were broken; scoped, exact assertions). It does NOT write tests — report only.

If the agent doesn't exist, skip this phase silently.

## PHASE 4.5: Adoption Check

A shared source helps only when it is consumed. This phase reads the project binding `.claude/quality-profile.json`: the canonical sources registry (`canonicalSources`), the search scopes (`searchScopes` minus `generatedDirs`, printed by `python3 scripts/forge/quality_profile.py scopes`; the source directories when unset) and the export patterns (`newExports`). When the registry is unset, skip the registry part (items 1 and 3 below) and say so in the report.

`<base>` is the branch's merge base with the binding's `integrationRef` (else `origin/[DEFAULT_BRANCH]`, from `.claude/project-config.json`): `git merge-base HEAD <ref>`.

Launch the **code-reviewer** agent (or, when it does not exist, do it yourself) with:
1. The registry rows this spec added or changed (diff of the registry document against `<base>`) and the plan's Reuse Map, when it has one.
2. The spec's new exports: `python3 scripts/forge/new-exports.py --base <base>`.
3. Instruction: "For every registry row the spec added or changed, search the scopes by name, signature and meaning for other derivations of the same concept, outside its single definition. For every `reuse` or `extend` row of the Reuse Map, confirm the code consumes the named source. Where the per-task code reviews already searched a new export (their new-exports check), reuse that result; search the rest. Report each hit with file:line and whether the hit is in this spec's changed files or in older code."

Findings:
- A bypass in this spec's code (a derivation outside the single definition, a Reuse Map `reuse` row the code does not follow, a new export that duplicates an older source): **Critical**, fixed before `/verify`.
- A bypass in older code: one follow-up per concept (seam first, for a later spec), never one per site.
- Record the counts in the report: rows checked, bypasses in this spec, bypasses in older code.

## PHASE 4.6: Structural Check

The gates above measure correctness, and a copied block looks clean in a per-task diff. This phase reads the same ratchets as `/audit`, so the spec cannot add what the next audit would flag. It is mechanical: run it yourself (no agent) while the agents run, with the same `<base>` as PHASE 4.5. It reads the project binding: `ratchets` (counts and the clone ratchets' `groupsCommand`) and `hubFiles`.

1. **Ratchets**: `scripts/forge/gate.sh ratchet -- python3 scripts/forge/ratchet.py check`. A `GREW` line is **Critical** (the spec added duplication, a suppression or a layer breach). A `LOWER` line is recorded for `/finalize`'s baseline update.
2. **Third copies**: `python3 scripts/forge/ratchet.py copies --files <changed files> --min-copies 3 --added-since <base>`. Each listed group is a block of logic with three or more copies to which this spec added or changed lines. It is **Critical** unless the plan's "Copies and Hubs" decided it (`not a copy: <reason>` that the code bears out); a seam task that landed leaves no such group. This also covers logic that is not a new export (a copied body inside an existing function).
3. **Hubs**: `python3 scripts/forge/hub-files.py check --base <base>`. Each `hub` or `new-hub` file the spec edited is checked against the plan's "Copies and Hubs" decision: an edit the plan did not decide is a **Warning**; a `new-hub` that no decision covers is a seam-first follow-up.
4. **Placement and layers**: the layer and file-placement checks of the lint (the binding's `layers`) ran in the task gates; a suppression they added shows in step 1.

When a key is unset, run the step by hand (the clone detector on the changed files, `git log` on the hub candidates) and say so. Record the counts in the report: ratchets grown, third copies, hub edits decided / undecided.

## PHASE 5: Write Review Report

Save the structured review report to `specs/[feature]/review.md`:

```markdown
# Review Report: [NNN-feature-name]

**Date**: [date]
**Spec**: [spec file path]
**Changed files**: [count]

## Security Review

- Critical: [N] | High: [N] | Medium: [N] | Info: [N]

[For each finding:]
- **[Severity]** — [file path]: [description]
  Recommendation: [suggested fix]

## Performance Review

[Include if performance-analyst ran, otherwise:]
_Skipped — no performance-analyst agent configured._

- High: [N] | Medium: [N] | Low: [N]

[For each finding:]
- **[High/Medium/Low]** — [file path]: [description]
  Recommendation: [suggested optimization]

## Test Assessment

[Include if qa-engineer ran, otherwise:]
_Skipped — no qa-engineer agent configured._

- AC items with test coverage: [N] of [M]
- Coverage gaps: [list uncovered areas]
- Verdict: ADEQUATE / GAPS FOUND

[For each gap:]
- [AC-N]: [description of missing coverage]

## Adoption Check

- Registry rows checked: [N] | Reuse Map rows confirmed: [N of M] | New exports: [N]
- Bypasses in this spec: [N] (Critical) | in older code: [N] (follow-ups)

[For each bypass:]
- **[Critical / follow-up]** — [file:line]: [concept] derived outside `[single definition]`

## Structural Check

- Ratchets grown: [N] (Critical) | lowered: [names] | Third copies added: [N] (Critical unless decided) | Hub edits: [N decided / M undecided]

[For each finding:]
- **[Critical / Warning / follow-up]** — [ratchet name, copy group regions, or hub path]: [what grew or was copied] — plan decision: [row or "none"]

## Follow-ups

[Seam-first items for a later spec: bypasses in older code (one per concept) and undecided `new-hub` files. "None" when empty.]
```

Commit the review report:
```
git add specs/[feature]/review.md && git diff --cached --quiet || git commit -m "[WIP] Review report: [feature-name]"
```

## PHASE 6: Present Summary

Display a concise summary of findings:

```
## Review Complete

**Security**: [N] Critical, [N] High, [N] Medium, [N] Info
**Performance**: [summary or "skipped"]
**Test Coverage**: [verdict or "skipped"]
**Adoption**: [bypasses in this spec / in older code, or "skipped (no registry)"]
**Structure**: [ratchets grown / third copies added / hub edits undecided]

Full report: specs/[feature]/review.md

Next: Run `/verify` to validate acceptance criteria and render verdict.
```

## IMPORTANT RULES

1. **Review does not render a verdict** — it produces findings with severity levels. The verdict is `/verify`'s job, which incorporates these findings
2. **Review does not fix code** — it identifies issues, not patches
3. **Idempotent** — running `/review` again overwrites `review.md` with fresh findings
4. **All agents run in parallel when possible** — launch security, performance, test assessment and the adoption check concurrently to minimize execution time; run the structural check yourself meanwhile
5. **Constitution violations are always Critical** — never downgrade a constitution-related security finding
