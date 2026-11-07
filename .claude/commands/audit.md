# /audit — Adversarial Codebase Audit

Standalone, on-demand whole-codebase audit for periodic "second opinion" quality reviews. Invokes review agents in ADVERSARIAL MODE to hunt for mislogic, contradictions, and lying code, and runs a **structural lens** (Phase 3.5) that measures duplication, single sources, variation points and responsibility placement across modules. Read-only for source code: it writes only its report and the learning step's checklist items (Phase 5). Writes a dated report to `audits/YYYY-MM-DD-audit.md` (with its Structure section, the theme status against the previous audit and a drafted theme triage) and prints inline. **NOT part of any workflow chain — invoke manually after several specs ship, or on the audit cadence of the project's audit gate (`--since-last`).**

> This command writes audit reports for the **user's project** to `audits/` at the workspace root. It is unrelated to the AIDevTeamForge template repo's own `QUALITY-AUDIT.md` file (which audits the template itself).

## Usage
```
/audit                          # full codebase audit (default)
/audit --full                   # explicit full codebase audit
/audit --since-last             # cadence audit: files changed since the previous audit, plus the open themes
/audit src/auth/                # deep-dive one directory
/audit path/to/file.ts          # audit a single file
/audit path/to/file.ts:42-87    # audit a code selection
/audit --uncommitted            # audit only uncommitted changes
```

## Arguments
- `$ARGUMENTS` — empty (default: `--full`), `--full`, `--since-last`, `--uncommitted`, file path (with optional `:start-end`), or directory path. Empty means **full codebase**, deliberately differing from `/security` where empty means uncommitted. `--since-last` is the audit of an audit cadence (every few merged specs): it audits what changed since the previous audit and re-measures the themes that audit left open; a full audit runs on request.

## PHASE 1 — Load Context & Guard

**Step order matters**: cheapest guards first, mode determination before mode-conditional I/O.

1. **Determine mode from `$ARGUMENTS` (no I/O)**:
   - Empty or `--full` → **broad mode**
   - `--since-last` → **broad mode** over the cadence file set (Phase 2); falls back to `--full` when there is no previous audit
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

5a. **Project binding** (`.claude/quality-profile.json`, when present; an unset key falls back as noted):
   - `searchScopes` and `generatedDirs`: every glob, grep and file count of this audit, and of every agent it launches, stays inside the search scopes and skips the generated directories (`python3 scripts/forge/quality_profile.py scopes` prints the resolved scopes). Unset: the Source Root, nothing skipped.
   - `enforcementMap`: read the enforcement map (the table under that heading). A rule tagged `review-only` with a violation in this audit and in the previous audit gets a proposed machine check (lint rule, catalog test or ratchet) in the report's Summary. Unset: skip.
   - `ratchets` and `baselineFile`: the measurements of the structural lens (Phase 3.5, S1): each ratchet's count, its baseline and the locations behind it (`locationsCommand`). Unset: S1 records "no ratchets bound" and the lens relies on its own searches.
   - `semanticClones`: the optional semantic-clone step of the structural lens (S1a). Unset or `enabled` false: the step is skipped.
   - `canonicalSources`: the canonical sources registry (the table under that heading): the concepts with a single definition, checked by the structural lens (S2, S3). Unset or an empty table: the lens builds its concept list from its other sources (S2) and proposes the first rows.
   - `planningSources`: the documents that declare future variations (roadmap, brief, open questions): read by the structural lens for variation points (S4). Unset: S4 uses the code signals only.
   - `layers`: the declared layer directions; the structural lens checks imports against them (S5). Unset: S5 uses the layering the constitution states.
   - `auditGate` and `integrationRef`: where audit reports live (`auditGate.auditReports`) and the branch whose history dates the previous audit (`integrationRef`, else `origin/[DEFAULT_BRANCH]` from `.claude/project-config.json`). Unset: the previous audit is the newest `audits/*-audit.md` by name, dated from the working tree.

6. **Recurring-issues lookup (broad mode only — skip entirely in narrow mode)**:
   - Glob `specs/*/review.md`, filter to files modified in the **last 90 days**. If none qualify, skip this step with a note for the report: "No recent reviews to cross-reference."
   - From the qualifying files, take up to the **5 most recently modified**.
   - Extract **Critical findings only** (skip High/Medium/Info to keep the list bounded).
   - Cap the total at **25 entries** — if more, take the most recent.
   - This becomes the "Recurring Issues to Verify" list. This is the audit's differentiator over `/review`: it can see drift across features.

7. **Previous audit (broad mode only)**: the newest audit report other than the one this run writes (on the integration ref when `auditGate` is set; the commit that added it dates it). From it take:
   - its `## Structure` measurements table (the ratchet counts the trend in S1 compares with); a report without one means "first measurement";
   - its `## Theme triage` table: every theme with its findings, disposition and issue. These are the **open themes** this audit re-measures (Phase 4.7). A theme whose issue is closed is still re-measured once, to confirm it stays fixed.
   No previous report: skip, and say so in the report ("first audit under the loop").

## PHASE 2 — Determine Scope

There are two pipeline shapes: **broad** (`--full`) and **narrow** (file / directory / `--uncommitted`). Narrow scopes simplify the pipeline.

### Broad mode (`--full` / empty) — full pipeline

Count source files under the search scopes (Phase 1 step 5a; the Source Root when unset) (exclude `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `vendor`, test files):

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

### Cadence set (`--since-last`)

The file set is the union of:
- the files under the search scopes changed since the commit that added the previous audit report (`git diff --name-only <that commit>..<integration ref> -- <search scopes>`);
- the files cited by the open themes (Phase 1 step 7), so a theme is re-measured even where nothing changed.

Count and fan out this set as in broad mode. The structural lens (Phase 3.5) still runs over the whole search scope: duplication and single sources are cross-module questions, and a copy added to a changed file matters only next to the unchanged original.

### Narrow mode (`--uncommitted` / file / directory) — simplified pipeline

- **`--uncommitted`**: run `git diff` and `git diff --cached` to collect changed files. If no uncommitted changes, stop with: `No uncommitted changes. Use --full or specify a path.`
- **File path**: read the file (full content even if `:start-end` line range given). If line range specified, mark it as the focus area but include the full file for context. Read up to 3 import-related files for cross-file logic flow.
- **Directory path**: glob source files in the directory, exclude tests/config/assets. If more than 20, prioritize by criticality heuristic (auth, API, data access).

**Pipeline simplifications for narrow mode**:
- **Skip the recurring-issues lookup** (Phase 1 step 6). The narrow target may not be in any spec, and cross-feature drift isn't the question being asked.
- **No module fan-out**. Run all available agents on the same input set, single-batch.
- **Cross-agent consensus still applies** but on narrower input it will be rare — that's fine.
- **Force-rank still runs** but produces a Top 5 (not Top 10).
- **No structural lens** (Phase 3.5), no theme status and no triage draft: a narrow target cannot show cross-module structure.

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
> Your primary mission in ADVERSARIAL MODE: find cross-module contradictions, layering drift, contradictory domain rules in different files, and dependency direction violations. You are looking for the "two files that can't both be right" situations. Duplication, single sources, variation points and responsibility placement are measured by the structural lens (Phase 3.5); report them here only when you meet them inside your module, with the Lens field set to `structural`.

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
Lens: mislogic | structural                      (optional; default mislogic)
Concept: <the concept or seam the finding is about> (structural findings only)
Principle: <GRASP pattern; SOLID principle only on a confirmed axis> (structural findings only)
Also at:                                         (structural findings only: every other copy or site, one per line)
- path/to/other.ext:17 — `<verbatim line from that file>`
- path/to/third.ext:88 — `<verbatim line from that file>`

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
- **Every `Also at` entry carries its own verbatim line** from the cited file; Phase 4.2 validates each entry like the Evidence block and drops an entry that fails (the finding stays if its main Evidence holds).
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
- **Batch C (broad mode only)**: the structural lens (3.5) → writes `audits/.tmp-structural.md`.

For 200+ file codebases using module subagents, run **one module** through Batch A → Batch B before moving to the next module. Do **not** fan out every module in parallel. Batch C runs once, over the whole search scope, never per module.

### 3.5 — Structural lens (broad mode)

The mislogic hunt reads file by file; it does not see that one rule is written in five places, that a shared helper is bypassed, or that a closed set is spread as literals. This lens measures that. It produces the report's `## Structure` section, which feeds the theme status and triage (Phase 4.7) and the learning step (Phase 5).

**Who runs it**: one dedicated pass by the `architect` agent (its file content, the Adversarial Preamble, then the **Structural Lens** block below instead of the Mislogic Hunt Checklist, then the Output Contract with `Lens: structural`, then the closing reminder). Without an installed `architect`, skip the lens and note it in the report. On a large scope it may split the steps across at most three nested agents (for example S1–S3, S4, S5), each over the whole search scope; it never splits by module. It writes `audits/.tmp-structural.md` and appends the S1 measurements and the S2 concept table after the findings under a `## Measurements` and a `## Concepts` heading (Phase 4 copies them into the report).

**Structural Lens block** (verbatim, appended to the agent prompt; the parent fills `<…>` from Phase 1):

```
=== STRUCTURAL LENS ===

You measure structure across the whole search scope (<search scopes>). You do not hunt
line-level bugs. Every finding still needs a verbatim Evidence quote, and every other
copy or site you cite goes into "Also at" with its own verbatim line. Use the language
of GRASP for responsibility (Information Expert, Controller, Creator, High Cohesion,
Low Coupling, Polymorphism, Pure Fabrication, Indirection, Protected Variations).
Name a SOLID principle only on a confirmed axis of change (S4): never report a missing
abstraction for a concept without a variation signal. These steps are a procedure, not
a list of problems this code base has; report only what you can quote.

S1 Measurements. Run `python3 scripts/forge/ratchet.py report --previous <previous report>`
   (without --previous on a first audit). When it prints that no ratchets are bound,
   record "no ratchets bound" and rely on your own searches. Record each count, its
   baseline, the previous audit's count and the trend, and the top locations. Read the
   top duplicate locations (exact, renamed-identifier and similar-function clones alike)
   and name the concept each cluster implements: every cluster is a candidate for S2.

S1a Semantic candidates (optional). Runs only when `semanticClones` in
   .claude/quality-profile.json is set and its `enabled` is true; otherwise record
   "semantic step: not enabled" in the Measurements and go on. The step lists candidate
   Type-4 clones (code that does the same thing written differently, found by comparing
   embeddings of functions; experimental). It is never a ratchet and never a finding by
   itself.
   - Run the project's semantic clone detector under `nice` with the binding's `paths`,
     `scope`, `model`, `ignore` and `threshold`. Embeddings run locally; never point the
     step at a remote embeddings API. The user downloads the model once: the audit never
     downloads it, and when it is missing records "skipped: model not downloaded" and
     goes on.
   - Report by cluster, not by pair: group the pairs that share a function into one
     cluster (one concept, N copies). Rank clusters by lines x copies, largest first, and
     review the top ones (at most about 20). Before a cluster is filed, check it against
     the open themes and the registry: a cluster that is already tracked extends that
     item instead of opening a new one. A confirmed duplicate (the same decision or rule
     implemented twice) becomes a concept for S2 and, with S3's evidence rules, a
     finding. Noise (getters, mappers, CRUD boilerplate, exhaustiveness switches,
     generated or declarative code) is dismissed with a one-line reason. Record the
     counts: pairs reported, clusters, confirmed, dismissed, already tracked.

S2 Concept inventory. List the concepts that must have exactly one definition:
   a. every row of the canonical sources registry (<canonical sources>; may be empty);
   b. the concepts behind the S1 duplicate clusters;
   c. derived figures and business rules: values computed from other data (totals,
      remaining or open quantities, balances, states derived from other records) and
      rules the constitution, the architecture doc or the planning sources state;
   d. closed sets: every field or parameter that holds a kind, type, status, mode or
      role, found by its declaration (enum, union type, check constraint, literal list);
   e. cross-cutting technical concerns every feature module needs: reading and
      validating untyped payloads, error normalization, guarding async work against a
      changed session, tenant or input (stale responses), formatting numbers, dates and
      money, read-only or permission decisions, list and filter state, routing or
      registration of modules;
   f. the exports of the shared layer (each is a single definition by construction);
   g. operation families: one operation offered once per kind (a function, endpoint or
      handler per entity or document kind doing the same job). The family is one
      concept: compare every member, including its execution or security mode.
   Keep the concepts with two or more consumers, at most about 40, most consumers first.
   Write them as a table: concept, kind (derived figure | business rule | closed set |
   shared helper | cross-cutting seam), owner if one exists, the files that use it.

S3 Derivations. For each concept, search the scope three ways: by name, by signature,
   and by meaning (the same expression shape: the same join, filter or aggregate, the
   same literal set, the same guard idiom, the same mapping table). Sort every hit into:
   the single definition, a consumer that goes through it, or another derivation.
   - Another derivation of a registered concept: Critical.
   - A business rule or derived figure with two or more derivations: High; Critical when
     the copies differ. Compare every copy with the first and list the differences
     (literals, limits, error codes, member lists, branches, execution or security
     mode): differences mean the copies have already drifted.
   - A technical helper or idiom hand-rolled in three or more modules: High; Critical
     when the copies differ (Pure Fabrication missing).
   - A shared definition that exists while other code does the same thing without it:
     High (an unadopted shared source; Indirection or Information Expert).
   One finding per concept, never per copy: the first copy in Evidence, the rest in
   Also at, the count in the title.

S4 Variation points. A concept is a variation point when one of these signals holds:
   a planning source (<planning sources>) says it will gain variants or a new factor;
   a second implementation of it exists; S1 or S3 found it derived in several places;
   code branches on the members of a closed set outside one registry (switch, if-chain,
   a map keyed by member, a per-member check constraint, a literal member list in a
   query or report, a default branch that silently absorbs a new member); a decision
   is made from a proxy at several sites under several names (for example a state
   standing in for a permission). For each: count the read or branch sites, name the
   seam that would isolate it (one owner: a resolver, a registry or a strategy), and
   report it when no such seam exists: High, Critical when a planning source schedules
   the variation in its upcoming items. A closed set used by two or more modules
   without one typed registry is at least High.

S5 Responsibility placement.
   - Layer directions: check imports against the declared layers (<layers>, or the
     constitution): presentation code that calls the data layer, or orchestrates a use
     case itself (Controller). One finding per direction, all sites in Also at.
   - High Cohesion: list the ten largest units of each layer by line count and name
     their responsibilities; a unit with two or more unrelated responsibilities, or
     the same large unit copied across features (parallel cores), is a finding.
   - Low Coupling: hub files that many features edit (count the commits that touch
     them) and that register modules by string, side effect or list entry without a
     compile-time link, so a forgotten entry fails silently.
   - Information Expert: a figure computed away from the module that owns its data,
     while the owner exists.
   - Indirection: a facade or seam that exists and is bypassed.

S6 Themes. Group the findings of S3–S5 by root cause: one concept or one missing seam
   is one theme. Each theme: a short name, the principle, the number of copies or
   sites, the finding ids. A theme that matches an open theme of the previous audit
   (<open themes>) keeps that theme's name.

Severity: a constitution rule the structure breaks (for example a stated single-source
or layering rule) is Critical and tagged [CONSTITUTION-VIOLATION]. Never report a
"future" abstraction: no signal, no finding.
```

## PHASE 4 — Stream-Consolidate, Verify, & Rank

**Critical**: do NOT load all findings from all agents into context at once. The parent command must stream them. Also: **verify every finding before accepting it** — adversarial mode invites hallucination, and grounding checks are the antidote.

### 4.1 — Stream agent outputs

For each agent in `[code-reviewer, architect, qa-engineer, security-reviewer, structural]` (`structural` is the Phase 3.5 pass; its `## Measurements` and `## Concepts` sections are kept aside for the report before the findings are parsed):

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
6. **Also-at entries** (structural findings): run checks 1–3 on each entry against its own file and line. An entry that fails is dropped and counted under "Failed verbatim-quote check"; the finding stays when its main Evidence passed. The copy count in the finding is the number of entries that survive plus one.

Findings that pass checks 1–5 enter the working list. Track the discard count per agent for the report.

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

### 4.7 — Themes and theme status (broad mode only)

A triage view over the validated findings; it never merges findings or changes their severity (the rules of 4.3 and 4.4 still hold).

1. **Group** every Critical and High finding, and every structural finding, into themes by root cause: one concept, one missing seam, one unenforced rule or one defect class is one theme. Start from the structural pass's S6 themes; add the mislogic and security findings that share a root cause; findings without a shared cause stay single-finding themes.
2. **Theme status** for each open theme of the previous audit (Phase 1 step 7), from evidence only:
   - `fixed`: none of its findings reproduces, and its ratchet locations and copies are gone;
   - `shrinking`: fewer copies, sites or ratchet count than the previous audit recorded;
   - `unchanged`: the same copies or count;
   - `grown`: more copies, more modules or a higher ratchet count.
   Cite the counts (copies before → now, the ratchet trend from the measurements). A theme of the previous audit that this audit cannot re-measure is `unknown`, never `fixed`.
3. **Machine check for every theme**: every theme's row names the machine check its fix leaves behind, a lint rule, catalog test or ratchet that fails on a new copy (an existing ratchet with its locations, or the rule to add); a non-blocking theme with no copyable class may say `none: <reason>`. **Escalation**: a `grown` theme is marked **escalated**: its machine check becomes mandatory before the next feature spec starts, and the triage row says so.
4. **Disposition** of every new or still-open theme, a default that needs no ruling: `fix` (small, user-visible defects), `touch-rule` (fixed by the next change that touches its files), `class-guard` (a machine check first, then the fix), or `seam-before:<upcoming planning item>` (must land before the named item of the planning sources). Blocking: every theme with a Critical finding, and every escalated theme. Inserting new work into the roadmap is not a disposition; it is proposed to the user with the theme list and a cost estimate.

## PHASE 5 — Write Report

0. **Cleanup stale temp files**: at the start of Phase 5, delete any leftover `audits/.tmp-*.md` files from a prior interrupted run. (Phase 4 deletes them on success; this catches the failure case.)
1. `mkdir -p audits` (top-level `audits/` directory at workspace root, **not** `docs/audits/`, even in wrapper mode).
2. **First-run only**: if `audits/.gitignore` does not exist, create it with the single line `.tmp-*.md`. This prevents temp files from ever being committed even if `audits/` is added to git.
3. Compute output path: `audits/YYYY-MM-DD-audit.md`. If exists, append `-2`, `-3`, ... until unused.
4. Write the report (format below).
5. **Audit learning step** (broad mode; skip when `.claude/checklists/` does not exist and list the proposed items in the report only): for every root cause in "Root causes and gate learning", name the earliest gate that should have caught it (spec-gate, plan-gate, breakdown-gate, task-review, test-lens, or a machine check) and append at most ONE generic, reusable item to that gate's checklist `.claude/checklists/<gate>.md` (item format per `.claude/storage-rules.md` → "Checklist Rules", the same checklists `/finalize`'s learning step writes):
   - worded as a check, never as this code base's instance (no file, concept or domain noun of this project);
   - with the next free id and the origin `audit YYYY-MM-DD/<theme>` (the report date);
   - deduplicated: when an existing item covers it, add the origin to that item instead.
   List the items in the report.
6. **Do NOT commit. Do NOT stage.** Let the user decide whether to keep the audit and its checklist items in git history.

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

## Structure
(Broad mode; from the structural lens, Phase 3.5. Omitted in narrow mode.)

### Measurements
| Ratchet | Count | Baseline | Previous audit | Trend |
|---|---:|---:|---:|---|
| <name> | <n> | <n> | <n or -> | first measurement / unchanged / shrinking (-d) / grown (+d) / fixed (-d) |
Top locations per ratchet (from `locationsCommand`), and the concept each top cluster implements. Semantic step: counts, or "not enabled" / "skipped: model not downloaded".

### Concepts and registry conformance
| Concept | Kind | Registered | Single definition | Other derivations (copies) | Drift | Finding |
|---|---|---|---|---|---|---|
Rows the registry lacks are proposed registry rows (the bootstrap of an empty registry).

### Variation points
| Concept | Signal | Read or branch sites | Seam | Planned variation (planning source item) | Finding |
|---|---|---|---|---|---|

### Placement
Layer-direction, cohesion, coupling, information-expert and indirection findings, grouped by theme, each with its principle.

## Theme status
(Against the previous audit's open themes, Phase 4.7. "First audit under the loop" when there is none.)
| Theme | Issue | Previous | Now | Status | Evidence (counts) | Escalated |
|---|---|---|---|---|---|---|

## Root causes and gate learning
| Root cause | Themes | Gate that should have caught it | Checklist item added (id, origin) or "covered by <id>" |
|---|---|---|---|

## Theme triage
(Keep this heading exactly: `python3 scripts/forge/audit-gate.py triage-check` looks for it. Drafted by `/audit`; the user triages it, see "Audit Gate" below. Every column is mandatory: the check fails a row without a machine check and a blocking row that names no open blocking issue.)
| Theme | Findings | Disposition | Blocks | Escalated | Machine check | Issue |
|---|---|---|---|---|---|---|
| T1 <name> | F-n, … | fix / touch-rule / class-guard / seam-before:<item> | yes / no | yes / no | <lint rule / ratchet / catalog test that fails on a new copy; non-blocking only: none: <reason>> | (to file) |

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
**Structure**: <ratchet>=<n> (<trend>), …; concepts N (registered N, with copies N); variation points without a seam N
**Themes**: N (blocking N); previous themes fixed N / shrinking N / unchanged N / grown N (escalated N)

### Top 5 Priorities
1. ...
2. ...
3. ...
4. ...
5. ...

Full report: audits/YYYY-MM-DD-audit.md

Not committed — review, then commit if you want audit history in git, or delete.
Next (broad mode): triage the `## Theme triage` table (see "Audit Gate").

NOTE: /audit is adversarial. It biases toward false positives over false
negatives. "Speculative" findings are hypotheses, not verdicts. Review with
that in mind.
```

## Audit Gate

A broad-mode audit ends with a drafted `## Theme triage` table; the user triages it:
- Confirm or change each row's disposition, `Blocks` and machine check.
- When the project uses an issue tracker, file one issue per blocking theme with the labels the binding's `auditGate.blockingIssues` command filters on, and replace the row's `(to file)` with its number (`#n`). The fixing change closes the issue.
- Without an issue tracker (`auditGate` unset), the triage table itself is the record: write `-` in the Issue column.
- Validate with `python3 scripts/forge/audit-gate.py triage-check --report audits/YYYY-MM-DD-audit.md` (exit 1 names each problem; with `auditGate` unset it prints one line and exits 0). `python3 scripts/forge/audit-gate.py status` shows whether the gate is open.

## IMPORTANT RULES

1. **Read-only** — no source modifications, no fixes, no auto-commit of the audit report. The only writes are the report and the learning step's checklist items (Phase 5 step 5), both left uncommitted.
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
15. **Structure is measured, not sampled** — the structural lens runs once over the whole search scope (never per module), counts copies and sites, and reports one finding per concept with every copy cited. GRASP names the responsibility problem; a SOLID principle is named only on a confirmed axis of change.
16. **Themes carry over** — every open theme of the previous audit gets a status backed by counts; every theme names its machine check, and a grown theme is escalated so the check lands before the next feature spec; triage dispositions are defaults that need no ruling.

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