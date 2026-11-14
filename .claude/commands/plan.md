# /plan — Technical Implementation Plan

Takes an approved spec and produces a technical plan: research findings, data model, API contracts, and architecture decisions. This is the bridge between WHAT (spec) and HOW (task breakdown).

## Usage
```
/plan [spec-file-or-feature-dir]
```

## Arguments
- `$ARGUMENTS` — Path to a spec file or feature directory in `specs/`. If empty, use the most recently modified feature.

## Context in the Workflow

```
/research (optional) → /specify → /plan → /breakdown → /execute-task → /review → /verify → /finalize
```

`/plan` answers the technical questions the spec intentionally left open.

## Prerequisites

1. A spec must exist with **Status: Approved**; if it is still "Draft", stop and inform the user
2. Run `python3 scripts/forge/spec_lint.py hash specs/[feature-name] --check`. Its line (whether the spec changed after its last spec-gate review, and any unreviewed changes) goes into the HARD GATE summary; exit 2 (no gate report or no hash, e.g. gate off or a spec gated before 1.37.1) is noted there, not a stop

## PHASE 0: Research Evaluation

**Guard**: Read `constitution.md`. If it contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/plan`."

**This phase always runs.** Scan the spec to determine the research depth needed.

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path.

### Step 1: Codebase Research (always)

- Read relevant source files to understand current patterns
- Check how similar features are implemented
- Identify reusable code and patterns
- For greenfield projects: check the constitution's scaffolding guide for pattern references
- Do not re-read `docs/`; the spec's "Current State" and "Affected Areas" carry their context (rule 8)

### Step 2: Signal Scan

Read the spec and check for these signals. **Only flag signals for things NOT already in the project's current stack.** If the spec references a library/technology that's already in the project's dependencies (check `CLAUDE.md`, `package.json`, `pubspec.yaml`, `requirements.txt`, etc.), that is NOT a signal.

| Signal | Example | NOT a signal when... |
|--------|---------|---------------------|
| External library/package **not in project dependencies** | "use Stripe SDK" (and Stripe is not in package.json) | Library is already installed |
| New integration with **unconfigured** third-party service | "connect to payment gateway" (no payment config exists) | Service is already integrated |
| Architectural decision where multiple valid approaches exist | "real-time updates" (polling vs SSE vs WebSocket) | Always a signal — requires decision |
| Greenfield pattern not yet present in the codebase | first use of caching, first background job | Pattern already exists in codebase |
| Performance constraints that need benchmarking | "handle 10k concurrent users", "< 200ms response" | Always a signal — requires research |
| Technology **not part of the project's current stack** | new protocol or tool the codebase hasn't used | Technology is already in the stack |

**No signals found** → proceed to Phase 1 with codebase research only.

**1+ signals found** → continue to Step 3.

### Step 3: Deep Research (when signals detected)

For each signal, choose the appropriate research tool:

**For specific libraries named in the spec:**
- Try Context7 first (`resolve-library-id` → `query-docs`)
- If Context7 has no docs for the library, fall back to WebSearch

**For comparing alternatives or architectural decisions:**
- Use WebSearch to find current best practices and proven approaches
- Compare at least 2-3 alternatives with pros/cons
- Check library options: maintenance status, bundle size, community adoption

**For all signals:**
- Look at real-world examples of similar implementations
- Verify external API contracts and limitations

### Research output:

Save to `specs/[feature-name]/research.md`:

```markdown
# Research: [Feature Name]

**Date**: [YYYY-MM-DD]
**Signals detected**: [list which signals triggered deep research]

## Questions Investigated
1. [Question] → [Finding + decision]
2. [Question] → [Finding + decision]

## Alternatives Compared

### [Decision Area] (e.g., "Payment processor", "WebSocket library")
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| [option A] | [pros] | [cons] | Chosen / Rejected |
| [option B] | [pros] | [cons] | Chosen / Rejected |
| [option C] | [pros] | [cons] | Chosen / Rejected |

**Decision**: [chosen option] — [one-line rationale]

## References
- [links to docs, examples, or source files consulted]
```

With no signals, skip research.md.

## PHASE 1: Technical Design

### 1.1: Data Model (if applicable)

If the feature involves data entities, define them. Save to `specs/[feature-name]/data-model.md`:

```markdown
# Data Model: [Feature Name]

## Entities

### [EntityName]
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier |
| ... | ... | ... | ... |

### Relationships
- [Entity A] → [Entity B]: [relationship type and description]

### Validation Rules
- [Field]: [constraint]
```

For existing codebases, reference existing types/interfaces instead of redefining them. Only document NEW or CHANGED entities.

### 1.2: API Contracts (if applicable)

If the feature involves API calls (REST, GraphQL, etc.), define contracts. Save to `specs/[feature-name]/contracts.md`:

```markdown
# API Contracts: [Feature Name]

## [Endpoint/Query/Mutation Name]
- **Type**: [GET/POST/Query/Mutation]
- **Input**: [type definition or reference to existing type]
- **Output**: [type definition or reference to existing type]
- **Errors**: [error cases and response format]
```

For existing codebases, reference existing GraphQL queries/mutations or REST endpoints. Only document NEW or CHANGED contracts.

### 1.3: Architecture Decisions

Document HOW the feature maps to the project's architecture. This is the core of the plan.

### 1.4: Structural specs

When the spec's **Type** is `structural`, the plan adds a section "Migration" after "Implementation Approach". It reads the project binding `.claude/quality-profile.json`:
- **Copies**: every derivation of the concept, found by searching the search scopes (`searchScopes` minus `generatedDirs`, printed by `python3 scripts/forge/quality_profile.py scopes`; the source directories when unset) by name, by signature and by meaning, each with file:line. Cite the concept's row in the canonical sources registry (`canonicalSources`), or write the row this plan adds: concept, kind, owner, single definition, how to consume, consumers.
- **Owner**: the module that holds the data the concept needs (Information Expert), and why; the layer that consumers reach it from.
- **Order**: the machine check first (a lint rule, a catalog test, or a ratchet with its baseline), then the single definition, then the consumer migrations (a few per task), then lowering the baselines. The existing tests stay green after every step.
- **Seam**: when the spec adds a seam for a concept that varies, list the planned variations from the planning sources (`planningSources`) with their item ids, and the seam's contract (preconditions, postconditions, invariants). Add a seam only on a confirmed axis; nothing is abstracted for the future.
- **Behaviour**: state that the change preserves behaviour and name the existing tests that pin it. A step that would change behaviour is a blocker: the spec goes back to `/specify` (split it, or make it a feature spec).

For a structural spec the "Migration" section is the reuse map of the concept it extracts; 1.5 still covers every other new symbol the plan introduces.

### 1.5: Reuse Map, Responsibilities and Seams (every spec)

Every plan, feature or structural, has a Reuse Map: no later gate asks "does this already exist?" unless the plan does. It reads the project binding `.claude/quality-profile.json`: the search scopes (`searchScopes`; the source directories when unset), the canonical sources registry (`canonicalSources`; when unset, the plan says so and the map rests on the searches alone), the planning sources (`planningSources`) and the layer directions (`layers`).

0. **Start from the spec's "Prior art"** (written by `/specify` from the feature docs and a search). Each candidate decided `reuse` or `extend` becomes a row of the map, with the search that confirms its entry symbol and callers; a candidate decided `unrelated` needs no row. A spec without a "Prior art" section gets that read here (the `docs/features/` docs of the touched area plus a search in the search scopes), and the plan says so.
1. **Entries**: one row for each new operation, derived value, helper, closed-set member or seam the plan introduces:
   - the search done: the query (name, signature and meaning: what it computes, not only what it is called) and the scope, with the hits as file:line, or "none";
   - the registry row it matches, if any;
   - the decision: `reuse <X>` · `extend <X>` · `new, because <reason>`. A `new` shared source adds its registry row in this plan (concept, kind, owner, single definition, how to consume, axis of change, contract, consumers) and names its expected consumers.
   - **Extraction threshold** (against over-engineering): the project's DRY rule, if any. A copy found by the search is moved to the shared layer by this spec only when this spec adds a consumer of it.
2. **Responsibilities** (GRASP, named at the decision): for each use case the controller (the layer that orchestrates it; presentation code never orchestrates or calls the data layer, per the layer directions); for each derived figure or operation its owner (the module that holds the data it needs, *Information Expert*), or the reason for another owner.
3. **Variation points**: read the upcoming items of the planning sources (`planningSources`) and list every variation point the spec consumes: a concept with evidence that it will vary (a planning source declares variants, a second implementation exists, a clone ratchet flags the same derivation in several places, a branch on a kind, type or status grows, an audit or escape traced a defect to scattered reads). Each gets its seam: `reuse <seam>` or `new seam <X>` with the planning item ids. Consumers never read the varying data directly. The first spec that consumes a known variation point creates its seam, even before the variation ships.
4. **Seams and contracts** (SOLID, only on a confirmed axis):
   - every new seam has a written contract (preconditions, postconditions, invariants, in the domain's terms) and one shared contract test suite that every implementation runs unchanged; a new implementation of an existing seam runs that seam's suite (the registry row's "contract" column names it);
   - no abstraction without a confirmed axis (config for constants, plugin points, strategy hierarchies for fixed rules): that is soft-coding; a deliberate exception is named and justified in "Key Design Decisions";
   - a client (a screen, a role, a caller) gets only the operations it may use, not the whole entity API; one security mode per operation family;
   - business and application code depend on contracts named in the domain's language; infrastructure SDKs, ORMs and transport clients stay in the layers the layer directions allow.
5. **Copies and Hubs on the touched files** (the same ratchets `/audit` reads, so a plan cannot add what the next audit would flag). It reads the project binding `.claude/quality-profile.json`: the clone ratchets' `groupsCommand` (`ratchets`) and the hub list (`hubFiles`). Run, on the existing files of File Impact:
   - `python3 scripts/forge/ratchet.py copies --files <files> --min-copies 2`: every copy group (exact, renamed or similar clones) with a copy in a touched file;
   - `python3 scripts/forge/hub-files.py check --files <files>`: every touched file that most feature changes edit (`hub`) or that this plan makes one (`new-hub`).

   For each listed group whose logic the plan extends, changes or copies again: a group that would reach its third copy (or has more already) gets a **seam task** ordered before the task that would add the copy (extract the shared definition or reuse it: the consolidation exception of `/execute-task` rule 1), or the row says `not a copy: <reason>` (the same tokens, different concepts). A two-copy group that the plan does not copy needs no task. For each `hub` or `new-hub` the plan edits to register a feature (a route, a menu entry, a composition-root line, a seed block): the entry goes through a registration seam (a self-registering manifest of the module, a compile-time link), or the row records why the hub edit stays. When `ratchets` has no `groupsCommand` or `hubFiles` is unset, run the clone detector and `git log` by hand on the touched files and say so in the plan.

### 1.6: Open Themes Touched (touch rule)

Audit themes are fixed by the next spec that touches their code. List the open theme issues: the rows of the last audit's theme triage (`.claude/quality-profile.json` → `auditGate`: the newest report matching `auditReports`, its `triageHeading` table; read only that section, e.g. `sed -n '/^<triageHeading>/,/^## /p' <report>`, never the whole report) whose issue is still open (without an issue tracker: the rows with Blocks `yes` or disposition `touch-rule` that no later change has fixed), and the registry rows whose status names an open issue. When `auditGate` is unset, use the open theme issues the last `/audit` report lists, if any. For each theme whose files intersect this plan's File Impact:
- **fix in place**: add the theme's fix for the touched files to File Impact (the breakdown gives it a task, and the pull request says `Fixes #n` when the theme is then fully fixed, `Refs #n` otherwise; without an issue tracker, name the triage theme id, e.g. `Fixes T1`); or
- **defer**: when the fix exceeds about a quarter of this spec's tasks or needs a decision this spec cannot take, record the deferral with the issue number and the reason; the theme then gets its own chore.

A plan that touches a theme's files and records neither is incomplete. A copy group of 1.5 step 5 is an open theme too.

**A deferral holds once**: a theme or copy group that an earlier spec already deferred is fixed in place by the next spec that touches its files, whatever its size. When that is impossible, the plan says so and you tell the user, who decides: raise the theme to blocking (its issue gets the blocking labels, or, without a tracker, its triage row says Blocks `yes`; the audit gate then holds new feature specs until the seam lands), or defer again with the reason recorded in "Open Themes Touched".

## PHASE 2: Write the Plan

Save to `specs/[feature-name]/plan.md`:

```markdown
# Plan: [Feature Name]

**Date**: [YYYY-MM-DD]
**Spec**: [path to spec.md]
**Status**: Draft

## Summary

[2-3 sentences: what this plan implements and the technical approach]

## Technical Context

**Architecture**: [from constitution — which layers are involved]
**Error Handling**: [pattern to use]
**State Management**: [approach for this feature]

## Constitution Compliance

[Verify the planned approach doesn't violate any NON-NEGOTIABLE rules]
- Rule X: [compliant / requires attention]
- Rule Y: [compliant / requires attention]

## Implementation Approach

### Layer Map

[Which architectural layers this feature touches and what happens in each]

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Domain | [types, interfaces, use cases] | [file paths] |
| Data | [repositories, API calls] | [file paths] |
| Presentation | [components, views, state] | [file paths] |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| [decision] | [approach] | [rationale] | [alternatives] |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| [path] | Create/Modify | [brief description] |
| [path] | Create/Modify | [brief description] |

## Reuse Map

| New symbol or concept | Search (query · scope) | Hits (file:line) | Registry row | Decision |
|-----------------------|------------------------|------------------|--------------|----------|
| [operation / figure / helper / closed-set member / seam] | [name, signature, meaning · scopes] | [file:line or none] | [row or —] | reuse X / extend X / new, because … |

**Registry rows added**: [concept · kind · owner · single definition · consumers, or "none"]

### Copies and Hubs

| Group or hub (from `ratchet.py copies` / `hub-files.py check`) | Copies or edits | Touched by | Decision |
|----------------------------------------------------------------|-----------------|------------|----------|
| [ratchet copies=N regions, or hub n/window path] | [N] | [task or file] | seam task before [task] / reuse [seam] / registration seam [X] / not a copy: [reason] / hub edit stays: [reason] |

[Or: "No copy group with a copy in a touched file; no hub touched." with the two command summary lines.]

### Responsibilities and Variation Points

| Use case or figure | Controller / owner | Variation point consumed | Seam (reuse / new) | Planning item |
|--------------------|--------------------|--------------------------|--------------------|---------------|
| [use case] | [layer or module, and why] | [concept or "none"] | [seam] | [item id] |

### Seams and Contracts

[For each new seam or new implementation of a seam: the contract (pre, post, invariants) and the shared contract suite it runs. "No new seam" otherwise.]

## Open Themes Touched

| Theme issue | Touched files | Decision |
|-------------|---------------|----------|
| #[n] [title] | [paths] | fix in place (task) / defer: [reason] |

[Or: "No open theme touches this plan's files."]

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| docs/features/[name].md | Update/Create | [what needs documenting] |
| docs/api/[name].md | Update | [new endpoints or changed contracts] |
| docs/architecture.md | Update | [if architecture patterns change] |

[If no documentation impact: "No documentation changes expected — internal implementation only."]

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |

## Dependencies

[Any external dependencies: packages to install, services to configure, environment variables]

## Supporting Documents

- [Research](research.md) — if research was performed
- [Data Model](data-model.md) — if data entities are involved
- [Contracts](contracts.md) — if API changes are involved
```

## PHASE 2.5: Plan-Spec Cross-Reference Check

Before presenting the plan to the user, verify completeness:

1. Read every AC from the spec's Acceptance Criteria section
2. For each AC, verify the plan addresses it:
   - Check the plan's "Layer Map" and "File Impact" for files/components related to this AC
   - Check "Key Design Decisions" for approach decisions relevant to this AC
3. If any AC has no clear implementation path in the plan:
   - Revise the plan to add the missing coverage
   - If you cannot determine the implementation path, add it to the plan's Risk Assessment as: "AC-[N] has no clear implementation path — requires clarification during breakdown"
4. Check the reverse: does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning (add to the plan's File Impact table with a note).
5. Every new symbol or concept in File Impact, the data model and the contracts has a Reuse Map row with its search; every "Prior art" candidate of the spec decided `reuse` or `extend` has its row (1.5 step 0); every theme of 1.6 whose files the plan touches has a decision in "Open Themes Touched".
6. Every copy group and hub that 1.5 step 5 listed for a touched file has a row in "Copies and Hubs", and every group the plan would bring to a third copy has a seam task ordered before the copy.

## PHASE 2.6: Independent Gate (plan-gate)

Read `.claude/commands/_independent-gate.md` and run the **plan-gate** (architect, security and qa lenses in parallel) on the plan and its supporting documents. Apply its loop before presenting the plan.

## PHASE 3: User Approval

**HARD GATE**: The plan MUST be approved before `/breakdown` can generate tasks.

**Autonomous mode** (`_autonomous-mode.md`, point `plan`): self-approve as that file's "Self-Approval at a HARD GATE" says, instead of waiting. A question for the user is answered as point `clarify` says.

Present a summary:

"I've created the technical plan at `specs/[feature-name]/plan.md`.

**Approach**: [1-2 sentences]
**Files affected**: [count] ([N] new, [M] modified)
**Key decisions**: [list the most important ones]
**Risks**: [high-risk items if any]
**Supporting docs**: [list what was generated]
**Spec hash**: [Prerequisites step 2]
[the `**Gate**:` line from `_independent-gate.md` → "At the HARD GATE"]

Please review and approve. Once approved, run `/breakdown` to generate tasks."

## IMPORTANT RULES

1. **Plans describe HOW, not WHAT** — the spec already defines WHAT. Don't repeat requirements, translate them into technical decisions
2. **Constitution compliance is mandatory** — verify before presenting to user. If the plan would violate a rule, redesign or flag it
3. **Reference existing code** — for existing codebases, always reference actual file paths and existing patterns. Don't propose new patterns when existing ones work
4. **Greenfield: follow the scaffolding guide** — the constitution's Section 7 (or the document it points to) defines where things go. Follow it
5. **Minimal supporting docs** — only create research.md, data-model.md, contracts.md if they're actually needed. Don't create empty files
6. **Memory check** — consult MEMORY.md for lessons about similar technical decisions
7. **Keep it scannable** — tables over paragraphs, decisions over discussions
8. **Docs context comes from the spec** — do not re-read docs; use the spec's "Current State" and "Affected Areas" sections. If the spec notes stale or missing docs, carry that forward as a plan risk
9. **Reuse map is mandatory** — no new operation, figure, helper, closed-set member or seam without its search and decision (1.5); no touched open theme without a fix or a recorded deferral (1.6)