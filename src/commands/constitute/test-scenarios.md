# constitute — manual test scenarios

This file is a dev artifact — NOT emitted to target projects (the emitter only picks up `main.md` and `references/*.md`; files at `src/commands/constitute/` root are ignored).

Purpose: document the branches `constitute/main.md` must cover, with concrete input fixtures and expected structural properties. Use this as a checklist when auditing constitute for regression after any spec change. Each scenario describes the minimum setup, the expected branch the command takes, and the structural properties the output must satisfy.

**Update discipline**: add a scenario when a new branch lands in main.md; remove / revise a scenario when a branch is removed or reshaped.

## Scenario 1: Happy-path brownfield, onboard ran

**Setup**:
- `.devforge/project-config.json` with `PROJECT_STATE: "brownfield"`, `LANGUAGES: ["TypeScript"]`, `FRAMEWORKS: ["Next.js"]`, `ARCHITECTURES: ["feature-sliced"]`, `ERROR_HANDLINGS: ["neverthrow Result<T,E>"]`, `API_LAYERS: ["REST"]`, `TESTINGS: ["vitest"]`, `WORKFLOW_ENFORCEMENT: "moderate"`
- `constitution.md` with all `[project-specific]` sections carrying `_Run constitute to populate_` sentinels (freshly installed state)
- `docs/overview.md` and `docs/architecture.md` populated with onboard output
- `docs/features/auth.md`, `docs/features/cart.md` populated
- `.devforge/memory.md` has `### Module boundaries (from onboard)` subsection
- `tsconfig.json` at root with `"strict": true`

**Expected branch**: Fresh-fill mode. No TBD resolution needed. Q-naming may skip (if onboard observed patterns). Q-domain skips (brownfield with onboard → domain in docs/features/).

**Expected structural properties after Phase 5**:
- Every `[project-specific]` sentinel replaced
- Every rule carries exactly one source tag from {[extracted], [convention], [enforced], [recommended]}
- At least one `[extracted]` rule cites a real file path (e.g., `docs/features/auth.md`)
- At least one `[enforced]` rule cites `tsconfig.json strict: true`
- `<!-- SCHEMA_VERSION: constitute-1.0 -->` stamp present near the top
- `Last updated:` line shows today's date
- `[universal]` sections unchanged byte-for-byte
- Section 1 Project Identity unchanged byte-for-byte
- §7 Scaffolding Guide either omitted or carries the canonical empty marker with reason `not applicable`

## Scenario 2: Happy-path greenfield, no onboard

**Setup**:
- `PROJECT_STATE: "greenfield"`, single-stack TS+Next.js as above
- `constitution.md` with all sentinels
- `docs/overview.md` and `docs/architecture.md` are stubs (wizard-populated placeholders only)
- No `docs/features/` or `docs/api/` files
- `.devforge/memory.md` has only wizard's `### Initial detection (from setup-wizard)` subsection

**Expected branch**: Fresh-fill mode. Q-naming asks per category (onboard didn't observe anything). Q-domain asks (greenfield).

**Expected structural properties**:
- Most rules tagged `[convention]` (from framework idioms + user answers); few or no `[extracted]`
- `[enforced]` rules only where actual config files are present at root
- §5 Domain Rules populated from user's Q-domain answer (or empty marker with reason `user deferred` if user answered "skip")
- §7 Scaffolding Guide populated with directory proposal + first-files list matching `ARCHITECTURES[0]`
- SCHEMA_VERSION stamp + Last updated as above

## Scenario 3: Brownfield without onboard

**Setup**:
- `PROJECT_STATE: "brownfield"`, single-stack as above
- `constitution.md` with sentinels
- `docs/overview.md` and `docs/architecture.md` are STUBS (onboard was skipped)
- No onboard findings in `.devforge/memory.md`

**Expected branch**: Fresh-fill mode. Q-naming asks per category (no onboard observations to skip from). Q-domain ASKS (not skipped — no onboard findings available per updated Q-domain gate).

**Expected structural properties**:
- No `[extracted]` rules (no onboard output to cite)
- Most rules `[convention]` or `[enforced]` (from root configs)
- Similar to Scenario 2 structurally, minus §7 (brownfield omits scaffolding)

## Scenario 4: Full-rewrite mode (re-constitute)

**Setup**:
- Same as Scenario 1, but constitution.md already has all `[project-specific]` sections populated (from a previous constitute run)
- No `_Run constitute to populate` sentinels anywhere in the file

**Expected branch**: Prereq #4 detects no sentinels → asks user to re-constitute or abort. User picks re-constitute. Operation mode = Full-rewrite. Phase 5 overwrites every `[project-specific]` section regardless of previous content.

**Expected structural properties**:
- Post-run content is fresh synthesis, not merged with previous
- `[universal]` sections still unchanged byte-for-byte
- Section 1 unchanged
- SCHEMA_VERSION stamp updated (or added if missing)

## Scenario 5: Abort during review (Phase 6)

**Setup**: Scenario 1 setup; user picks "Abort" at Phase 6.

**Expected structural properties**:
- `constitution.md` restored to pre-Phase-5 state (bytes match `.devforge/wip/constitute-prewrite.md`)
- `.devforge/wip/constitute-prewrite.md` deleted after abort
- No partial-write state
- No changes to `project-config.json` even if Phase 2 resolved TBDs

## Scenario 6: TBD resolution in Phase 2

**Setup**:
- `ARCHITECTURES: ["TBD"]` (user deferred Q4 during wizard)
- Everything else as Scenario 2

**Expected branch**: Phase 2 asks the user to resolve the architecture TBD. Two sub-scenarios:

**6a. User provides an answer** ("hexagonal"):
- `project-config.json` updated: `ARCHITECTURES: ["hexagonal"]`
- Phase 4 synthesizes §2.1 Layer Boundaries based on hexagonal shape
- `§2.1` has real rules, not empty marker

**6b. User answers "still defer"**:
- `project-config.json` keeps `ARCHITECTURES: ["TBD"]`
- §2.1 (and §2.2, §2.3 since they all derive from architecture) use canonical empty marker with reason `user deferred`
- No fabricated architecture rules

## Scenario 7: Tag validation downgrade

**Setup**:
- Scenario 1 setup
- During Phase 4, LLM generates a rule: `[extracted] Imports go through barrel files. Observed in src/features/profile/index.ts.`
- But `src/features/profile/index.ts` does NOT exist in the test project

**Expected**:
- Phase 4.5 checks the cited path; file missing.
- Rule's tag downgraded to `[convention]` (rule content preserved).
- `EXTRACTED_DOWNGRADES = 1` tracked.
- Phase 6 summary shows `Tag adjustments` block with `1 [extracted] → [convention] (cited file didn't exist)`.

## Scenario 8: Empty section (§6.5 no deprecation pattern)

**Setup**:
- Single-stack Python project, greenfield
- Phase 4 synthesizing §6.5 Deprecation Handling — language convention `warnings.warn(DeprecationWarning)` is known
- But if the LLM chooses NOT to emit a convention rule (e.g., user-declared minimal strictness + no observed pattern), Phase 4 produces no rules for §6.5

**Expected structural properties**:
- §6.5's body is the canonical empty marker: `_No rules synthesized — no applicable default. Rerun {{cli.sigil}}constitute with Full-rewrite mode after adding context..._`
- Marker does NOT start with `_Run constitute to populate` (so a re-run in Fresh-fill mode won't re-target it)
- Phase 6 summary's "Empty sections" block includes §6.5 with reason `no applicable default`

## Scenario 9: Crash recovery (wip file present at start)

**Setup**:
- `.devforge/wip/constitute-prewrite.md` exists from a previous interrupted run
- `constitution.md` may be in partial state

**Expected branch**: Prereq #5 fires. User is asked Recover / Continue / Abort.

**Expected structural properties per choice**:
- **Recover**: `constitution.md` bytes match the wip file; wip file deleted; this run proceeds from Prereq #1 onward with clean state
- **Continue**: wip file deleted, current `constitution.md` kept as-is, this run proceeds
- **Abort**: no changes

## Scenario 10: Multi-stack monorepo

**Setup**:
- `LANGUAGES: ["TypeScript", "Python"]`, `FRAMEWORKS: ["Next.js", "FastAPI"]`
- `ARCHITECTURES: ["feature-sliced", "hexagonal"]`, etc.
- `PACKAGES_DETECTED` / `PACKAGE_STACKS` populated

**Expected structural properties**:
- §3.1 Type Safety has two sub-blocks: one for TypeScript, one for Python (different escape-hatch types, different tool chains)
- §3.3 Naming Conventions has per-language sub-blocks
- §2.1 Layer Boundaries: if both stacks use the same architecture, one block; if different, per-stack blocks
- Cross-cutting sections (§6.6 workflow, §6.5 deprecation at project level) single block without stack labels

---

## Running the scenarios

No automation yet — these are manual-verification fixtures. Typical flow:

1. Set up a sandbox project matching the scenario's setup.
2. Run `{{cli.sigil}}constitute` against it.
3. Walk through the "Expected structural properties" checklist.
4. If anything fails, file a finding and add to the next audit pass.

For a more automated approach (dry-run mode, structural assertion parser), see PLAN.md follow-up items.
