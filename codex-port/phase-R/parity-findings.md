# Cross-Runtime Parity Findings

Discoveries from running the same forge commands against the same project under both Claude Code and Codex CLI in parallel. Each finding is a real divergence between how the two runtimes interpret the shared spec (or a real behavioral gap to fix).

## Methodology

Two git worktrees sharing one `.git/`:
- `testParity/` on branch `claude-parity` — Claude Code
- `testParity-codex/` on branch `codex-parity` — Codex CLI

Both point at the same source (`db-cse-ui-strata/` — a Vue 3 / TypeScript / Lerna / GraphQL / Okta monorepo, ~2260 source files, 24 packages + 1 app, brownfield).

Identical wizard answers used on both sides (per answer sheet). Commands run in parallel terminals, stage-by-stage checkpoint diffs between phases.

## How to use this file

- Each finding has: severity, phase, observed divergence, spec reference, root cause (if known), impact, proposed fix.
- When a finding is fixed, cross it out or move to a **Resolved** section with commit ref.
- Rerun the full parity test after a batch of fixes to verify closure + surface new findings.

---

## Run 1 — 2026-04-24

**Forge commit at run start**: `6febe5b` (after the Phase 1 enforcement scan / pitfall promotion fixes)

**Setup bugs fixed during this run** (not parity findings — install blockers):
- **Install flow**: `.codex/config.toml` and `.codex/agents/*.toml` shipped with unsubstituted `{{PLACEHOLDER}}` tokens in structural fields. Codex crashed on config; silently disabled all agents. Fixed in `scripts/lib/install_defaults.py` + `scripts/generate-agents.py` + wizard spec rewrite (key-based regex replacement instead of placeholder substitution).

### Actual inputs given during this run

So Run 2 and beyond can reproduce with identical input and isolate runtime-interpretation drift from input-variance drift.

**Codex side** (entered inline as a combined response to Codex's batched Q0-Q3 prompt):
1. Project name: `CSE UI`
2. Description: `Connected Sales Experience Mobile Application (Android + IOS Ionic Enterprise) And Web Application.`
3. Project type: `Frontend / web application`
4. Languages + frameworks: `TypeScript + Vue 3`

**Claude side** (each question asked as a separate turn — confirms Finding 4; UI presented Q1-Q3 with "Recommended" defaults the user accepted):
1. Project name: `CSE UI` (free text, root package.json's name was `root`)
2. Description: confirmed README-derived default (`Connected Sales Experience Mobile Application (Android + IOS Ionic Enterprise) And Web Application.`) via "Recommended" option
3. Project type: `Frontend / web application` (Recommended) — confirmed
4. Languages + frameworks: `TypeScript + Vue 3` (Recommended) — confirmed

**Additional parity data point surfaced**: Claude presented Q1-Q3 with pre-computed defaults labeled "Recommended" and a one-click confirm path. Codex presented the same questions as free-text prompts without pre-computed defaults. Neither is strictly wrong per spec, but the UX gap is meaningful:

- Claude: detected → proposed → user confirms (optimistic; relies on good detection)
- Codex: detected → showed context → user writes → user confirms (conservative; treats answer as authoritative input)

Log as **Divergence 5 (LOW)** at the Findings section below.

Remaining questions (Q4 architecture through Q11 AC verification) answered per the canonical sheet:
- Q4 architecture: `feature-modular monorepo`
- Q5 error handling: `purify-ts Either/Maybe`
- Q6 API layer: `GraphQL`
- Q7 testing: `Vitest`
- Q8 workflow enforcement: `strict`
- Q9 AI attribution: `no`
- Q10a (Claude only): tiers `opus / sonnet / sonnet`
- Q10b (Codex only): reasoning `high / medium / medium`; model overrides = accept defaults (null)
- Q11 AC verification: `Multiple` → `Code-only` + `Runtime-assisted`
  - Runtime URL: `https://okta.local.dev.dice-tools.com:8080`
  - API base / CLI command: skipped

**Manual overrides during run** (where a runtime proposed a wrong default that the user corrected):
- Codex Finding 2: user will override `DEFAULT_BRANCH` from `codex-parity` → `dev` when asked, to keep downstream state correct.

### Findings

Sorted HIGH → MEDIUM → LOW. IDs preserved from discovery order so cross-references stay intact.

| # | Severity | Phase | Title |
|---|---|---|---|
| 4 | HIGH | 2 (interview) | Codex batches questions (4 + 8 observed) — breaks branching logic because conditional follow-ups must be pre-computed before user's answer is known |
| 2 | HIGH | 1 (detect) | Codex used outer worktree's git for `DEFAULT_BRANCH`; should use inner source repo's git |
| 8 | HIGH | 2 (interview) | Claude completely missed `purify-ts` + `Either<DataError, ...>` usage, proposed project adopt a Result pattern it already has. Codex detected it correctly. Asymmetric miss vs Finding 3 — Claude did NOT scan dependency manifests deeply for error-handling libraries. |
| 14 | HIGH | 1+5 (detect/populate) | Per-package command depth: Claude reads each package's `package.json` scripts and records real commands per package (`vite build --mode raw`, `tsc --noEmit`, `eslint --ext .ts ./src`). Codex uses generic fallback (`yarn build`/`yarn check`/`yarn lint`) for every package uniformly. Downstream commands that operate per-package (constitute, execute-task) get different-fidelity info. |
| 15 | HIGH | 1+5 (detect/populate) | Top-level BUILD_COMMAND / LINT_COMMAND disagreement: Claude `yarn build:raw` + `yarn lint:core && yarn lint:web`. Codex `yarn build:origin` + `yarn lint:web`. These are commands that would actually be run later; whichever runtime got it wrong produces a forge that fails builds/lints. User must verify which is correct by reading actual root `package.json`. |
| 3 | MEDIUM | 1 (detect) | Detection granularity asymmetry — Claude deeper on build/test/auth tooling, Codex broader on frontend libs |
| 6 | MEDIUM | 2 (interview) | Architecture-pattern detection asymmetry — Codex proposed wrong default (`layered / BLoC + use-cases + repositories` from internal folder structure); Claude proposed correct default (`feature-modular monorepo` from workspace shape). Asymmetric with Finding 8 (opposite direction). |
| 7 | MEDIUM | 2 (interview) | Runtime-URL detection asymmetry — Claude opened `apps/app-web/vite.config.ts` and extracted `server.host`/`port`/`https` to synthesize the correct URL. Codex used generic Vite default `http://localhost:5173`, missing the project-specific config. |
| 9 | MEDIUM | 2 (interview) | Claude reshaped Q11 AC-verification options — dropped `Off` and `Multiple` branches, invented "Code-only + Tests" pre-combination not in spec. User forced into "Type something" fallback to get a spec-compliant multi-mode answer. |
| 10 | MEDIUM | 4 (agent curation) | Husky pre-commit hooks detected by Claude (cited for devops-engineer); missed by Codex. Has downstream impact — Husky is a canonical `[enforced]` rule source per constitute's Phase 1 enforcement scan, so Codex-side constitute would under-index enforced rules. |
| 16 | MEDIUM | 1+5 (detect/populate) | PACKAGES_DETECTED content drift: Codex includes `scripts/` as a package; Claude excludes it. Element ordering also differs (Claude alphabetic within categories; Codex apps-first then root then packages). |
| 17 | MEDIUM | 5 (populate) | project-config.json free-text fields (`PROJECT_STRUCTURE`, `DEV_COMMANDS`, `ARCHITECTURE_DETAILS`, `WRAPPER_MODE_SECTION`, `AGENT_LIST`) filled differently: Claude = terse breadcrumb references (`"See \`## Project Structure\` in CLAUDE.md"`); Codex = extensive inline duplicated content. Spec expects the former (single source of truth in CLAUDE.md/AGENTS.md). Codex's behavior = content duplication + drift risk. |
| 1 | MEDIUM | 0 (prereq) | Claude auto-detected wrapper mode; Codex asked for confirmation (spec says ask) |
| 5 | LOW | 2 (interview) | Claude pre-computes "Recommended" defaults for one-click confirm; Codex shows context then asks for free-text answer |
| 11 | LOW | 4 (agent curation) | Phase 4 override UX: Claude offered hedged alternate options (`Also keep mobile-engineer`/`Also keep backend-engineer`); Codex plain-text "confirm or override". Cosmetic. |
| 12 | LOW | 5 (summary) | Codex's on-screen Phase 5 summary abbreviated "Populated Files" list (showed 2 items); on-disk `.devforge/setup-complete` marker has the correct full list (9+ items). Cosmetic reporting gap — artifacts are all present on disk. |
| 13 | LOW | 1+5 (detect/summary) | Off-by-one package count — Claude says 25, Codex 26. Claude excludes `scripts/`, Codex includes it. Consistent within each runtime. Spec doesn't explicitly prescribe which. |
| 18 | LOW | 5 (populate) | JSON formatting divergence: Codex pretty-prints (one field per line) while Claude uses compact objects. Both valid JSON. Causes noisy future diffs. |

---

Detailed entries below are sorted HIGH → MEDIUM → LOW to match the summary table. Only findings with deep-dive content have their own sections; findings whose summary-table entry captures everything (6, 7, 9, 10-18) are not duplicated here. IDs preserved from discovery order for cross-reference stability.

---

### Finding 4 — HIGH — Phase 2: Codex batches multiple questions into one combined prompt (4-question + 8-question batches observed)

**Severity**: HIGH (escalated twice — initially LOW, then MEDIUM after Q0-Q3 batch observed, then HIGH after Q5-Q12 batch observed AND branching-logic consequence understood)

**Observed**:
- Claude: asks each question as a separate sequential turn.
- Codex: presented Q0-Q3 as one combined prompt ("Please answer these in order..."), then presented Q5-Q12 as a second combined prompt of 8 questions.

**Spec reference**: `src/commands/setup-wizard/references/questions.md` — each question is its own `## Q0`, `## Q1`, etc. section with its own `{{ask}}` block.

**Root cause hypothesis**: Codex may have batched for efficiency (fewer turn-trips). Claude respected the per-question structure. Spec doesn't explicitly forbid batching but clearly structures questions as separate units.

**Impact**:

1. **UX**: user must hold more state in head; answers have to be typed in a numbered list format rather than one-at-a-time.
2. **Branching logic breaks**: several wizard questions trigger conditional follow-ups. Q11 → Multiple → sub-follow-up for modes; Q11 → Runtime-assisted → sub-follow-up for URL. When Codex batches these, it **pre-computes the follow-up defaults AHEAD of the user's answer**. Observed in Run 1: Codex prefilled `http://localhost:5173` as the Q12 URL default inside the batched Q5-Q12 prompt — asking the URL question before the user had said they wanted runtime-assisted. If the user had picked `off`, that URL question shouldn't have been asked at all.
3. **Downstream flattening**: this pattern will recur in every wizard / constitute / breakdown flow that has conditional branches. Constitute's Phase 2 (TBD resolution) and Phase 6 (revise loop) both depend on user-input stops between branches — batching flattens those.

**Proposed fix**:
- (a) Add explicit, prominent instruction in the wizard's Phase 2 spec (e.g., in `main.md` under IMPORTANT RULES): **"Ask each question in a separate turn. Do NOT batch multiple questions into a single prompt. Each `{{ask}}` block is exactly one user-input stop. For questions with conditional sub-follow-ups (e.g., Q11 Multiple, Q11 Runtime-assisted), wait for the user's answer to the primary question BEFORE computing or presenting the follow-up."**
- (b) Extend to all commands that use `{{ask}}`-style interview blocks (constitute Phase 3, breakdown review, execute-task questions if any) — this is a runtime-wide spec-interpretation gap, not just wizard-specific.
- (c) Consider a spec-language convention: prefix interactive blocks with something stronger than `{{ask}}` for conditional branches — e.g., `{{ask-stop}}` — to make the "must-not-batch" property explicit to the reading model.

---

### Finding 2 — HIGH — Phase 1: default branch read from wrong git repo

**Severity**: HIGH (correctness bug; wrong value lands in project-config.json)

**Observed**:
- Claude: `Default branch (inner): dev` (from `db-cse-ui-strata/.git`) ✅
- Codex: `Default branch: codex-parity` (from outer worktree's `.git`) ❌

The user is testing parity via git worktrees: the outer worktree is on branch `codex-parity` (meaningless to the actual project); the inner source repo is on `dev` (the real project branch).

**Spec reference**: `src/commands/setup-wizard/references/detect.md:132`

> Wrapper mode: run the detection against the `SOURCE_ROOT` repo (inner folder's `.git`), since that is the repo downstream commands operate on for source-code git operations. If wrapper mode AND the outer workspace also has a `.git`, the inner repo's default branch is the one that matters.

**Root cause hypothesis**: Codex defaulted to `git rev-parse` in the current working directory without switching into `SOURCE_ROOT/.git`. The spec requires running git commands against the inner repo; Codex ran them against the outer.

**Impact**: `project-config.json` `DEFAULT_BRANCH` ends up as `codex-parity`. Every downstream command that reads `DEFAULT_BRANCH` (branch-based auto-commits, PR creation, git log reads, baseline diffs) operates against a branch that doesn't exist in the source repo. **Breaks wrapper mode in Codex silently.**

**Proposed fix**: in `detect.md`, explicitly state that all git operations in wrapper mode MUST target `SOURCE_ROOT/.git`. Consider adding a concrete command template: `git -C "$SOURCE_ROOT" rev-parse --abbrev-ref HEAD` so the runtime doesn't have to interpret.

---

### Finding 8 — HIGH — Phase 2: Claude missed `purify-ts` + `Either<DataError, ...>` usage entirely

**Severity**: HIGH (wrong detection → wrong default → could mislead user into adopting a pattern they already use)

**Observed**:

- **Claude**: at Q5 (error handling), presented: "I didn't find a dominant error-handling library (no `neverthrow`, no custom Result type) — it looks like standard try/catch + Apollo error handling." Recommended options were `Try/catch + Apollo` or "Introduce Result/Either pattern" (as if greenfield).
- **Codex**: at the equivalent Q6 (in its numbering), detected correctly: "I see `Either<DataError, ...>` return types, `purify-ts` in dependencies, and `DataError` used in repository code."

The project uses `purify-ts` extensively: imported in `CoreRepository`, threaded through every use case, folded in every BLoC. Visible in:
- `apps/app-web/package.json` `purify-ts` dependency
- Every package's `package.json` transitively depending on it
- Source files `pkg-cse-core/src/**/data/*.ts` with `Either<DataError, T>` signatures

**Spec reference**: detection spec implicitly says to identify error-handling library. Claude's limited search (probably grepping for `neverthrow` / `Result<T,E>` / known patterns) missed `purify-ts` — a less common but explicitly-named library in dependencies.

**Root cause hypothesis**: Claude's detection may have a hardcoded lookup for common error-handling libraries (neverthrow, oxide.ts, ts-results). If `purify-ts` isn't in that list, it reports "no dominant library." Codex seems to have scanned actual code signatures — catching the pattern even though the library isn't in a canonical list.

**Impact** (severe in this specific case):
- User accepts Claude's "Recommended: Try/catch + Apollo" default → `project-config.json` stores wrong `ERROR_HANDLING` value → constitute later synthesizes error-handling rules against the wrong pattern → agents are told to use try/catch when the codebase uses `Either`. **Systemic rule-quality failure for any user who accepts the Recommended answer.**
- User noticing the miss (as happened here) overrides manually. But users who don't know their own codebase deeply would miss this.

**Proposed fix**: extend detection spec explicitly:
- Grep for `purify-ts`, `neverthrow`, `fp-ts`, `oxide.ts`, `ts-results`, `result-type`, `monet` in all `package.json` / `pyproject.toml` / `Cargo.toml` etc. as a DEPENDENCY-level signal.
- Grep source for patterns like `Either<`, `Result<`, `Maybe<`, `Task<` as a USAGE-level signal.
- Combine: if dependency present OR usage pattern present, report the library by name. Never conclude "no library" unless BOTH checks return empty.
- Applies to all detection categories, not just error handling — the same pattern may have missed state-management libs, validation libs, etc.

**Cross-finding pattern**: combined with Finding 3 (Claude deeper-but-narrower vs Codex broader-but-shallower), this suggests Claude is optimizing for a shorter scan by relying on a canonical list of known patterns, while Codex does a broader grep. Explicit checklist (Finding 3 proposed fix) addresses both.

---

### Finding 3 — MEDIUM — Phase 1: detection granularity asymmetry

**Severity**: MEDIUM (incomplete detection → incomplete downstream rules, asymmetric between runtimes)

**Observed** — items each runtime caught that the other missed:

| Signal | Claude | Codex |
|---|---|---|
| Okta auth plugin | ✅ | ❌ |
| Apollo GraphQL client (as distinct lib) | ✅ | only via `graphql-codegen` |
| `vue-tsc --noEmit` typecheck command | ✅ | ❌ |
| `eslint` lint command | ✅ | ❌ |
| npm-root vs Yarn-inner package manager split | ✅ | ❌ |
| tailwindcss, sass (styling) | ❌ | ✅ |
| pinia (state management) | ❌ | ✅ |
| vue-router | ❌ | ✅ |
| File count summary | ❌ | ✅ (~2260) |

Net: Claude went deeper-but-narrower; Codex broader-but-shallower.

**Spec reference**: `src/commands/setup-wizard/references/detect.md` (Phase 1 detection instructions broadly — what to read, what to extract).

**Root cause hypothesis**: the spec describes WHAT to detect but leaves interpretation of depth vs breadth open. Different model families optimize differently when asked to produce a "detection summary." Neither is wrong per spec; neither is fully right for downstream.

**Impact**: downstream commands (especially constitute) cite detected tooling when synthesizing rules. Asymmetric detection → asymmetric rule synthesis later. A user under Codex gets no Okta/Apollo/eslint-derived constitution rules; a user under Claude gets no tailwindcss/pinia/vue-router-derived rules.

**Proposed fix**: extend `detect.md` with an explicit per-category checklist that both runtimes must produce as a structured output (not free-form prose):

```
[ ] Languages (array)
[ ] Frameworks (array, with role: frontend / backend / library / plugin)
[ ] Auth layer (if any)
[ ] API client layer (if any)
[ ] State management (if any)
[ ] Styling (if any)
[ ] Routing (if any)
[ ] Build tool
[ ] Type-check command (exact CLI invocation)
[ ] Lint command (exact CLI invocation)
[ ] Test runner
[ ] Package manager (+ note if outer and inner differ)
[ ] File count under SOURCE_ROOT
[ ] Manifest count
```

Turning the "detection" into a filled-out checklist forces parity between runtimes. This single fix would likely collapse Findings 3, 6, 7, 8, 10, 14, 15, 16.

---

### Finding 1 — MEDIUM — Phase 0: wrapper-mode confirmation asked differently

**Severity**: MEDIUM (UX inconsistency; not a correctness bug since user can confirm in both)

**Observed**:
- Claude: auto-detected wrapper mode from nested `.git` and proceeded without confirming. Showed the detection result only.
- Codex: showed the `{{ask}}` prompt and waited for `yes`/`no` before continuing Phase 1.

**Spec reference**: `src/commands/setup-wizard/references/detect.md:39`

> `{{ask "I found a nested git repository at [folder-name]/. Is this a wrapper workspace where template artifacts live at the outer root and the actual source code lives in that subfolder?"}}`

The `{{ask}}` marker is spec-prescribed. Codex followed it; Claude short-circuited.

**Root cause hypothesis**: Claude may interpret `{{ask}}` semantics as "present and proceed on reasonable default" rather than "required user-input stop." Or Claude's single-nested-git heuristic may be treated as unambiguous enough to skip the confirmation.

**Impact**: if the user's inner repo is NOT meant to be the source root (e.g., it's a vendored submodule or a tool fixture), Claude would silently misconfigure wrapper mode. Codex catches this at the confirmation step.

**Proposed fix**: audit how Claude interprets `{{ask}}` markers. If Claude systematically skips single-branch `{{ask}}` prompts, either:
- (a) Add explicit "DO NOT SKIP THIS QUESTION" wording to the spec at critical confirmation points, OR
- (b) Document in the spec that Claude auto-proceeds when inference is unambiguous, and explicitly flag which questions must never auto-proceed (wrapper mode, workflow enforcement, AC verification mode).

---

### Finding 5 — LOW — Phase 2: Claude offers "Recommended" one-click defaults; Codex asks for free-text

**Severity**: LOW (UX divergence; same final answers)

**Observed**:
- Claude: for Q1-Q3, pre-computed a recommended default from detection output and presented it as a selectable option labeled `(Recommended)`. User confirmed with one click.
- Codex: for the same questions, showed the detection context and asked the user to write the answer inline. No pre-selected option.

**Spec reference**: `src/commands/setup-wizard/references/questions.md` — per-question `{{ask}}` blocks. Spec doesn't specify UI affordance (radio vs free-text vs pre-filled).

**Root cause hypothesis**: the two runtimes interpret `{{ask}}` with different UI conventions. Claude Code has a structured-select UI primitive and reaches for it when options are enumerable; Codex has a plainer ask-and-read-input pattern.

**Impact**:
- Claude's UX is friendlier but biases toward accepting detected values (user may miss a wrong detection if they reflexively click Recommended). This aligns with Finding 1 (Claude auto-proceeding on wrapper mode) — a broader "Claude optimizes for flow; Codex optimizes for deliberate input" pattern.
- Codex's UX is friction-heavier but forces the user to think about each answer — catches detection mistakes earlier.

**Proposed fix**: cosmetic; low priority. If we want parity on this UX pattern:
- (a) Explicit in spec: "If a detected default exists, present it as a pre-selected option the user can confirm or override." Push Codex toward Claude's pattern.
- (b) Or leave divergent; document that Claude's `(Recommended)` UX is the flagship experience and Codex's free-text is the fallback. Document in README / onboarding notes.

Pattern to watch across runs: if Finding 1 + Finding 5 both reflect "Claude auto-proceeds on inferred answers", that's a systemic framing gap worth addressing explicitly in the spec rather than finding-by-finding.

---

## Run 1 conclusion

**Scope of this run**: setup-wizard only. Onboard and constitute phases deferred to a later run (user decision — fix findings first).

**Final tally**: 18 divergences.

**By severity**:
- HIGH (5): 2, 4, 8, 14, 15
- MEDIUM (7): 3, 6, 7, 9, 10, 16, 17
- LOW (6): 1, 5, 11, 12, 13, 18

**By phase**:
- Phase 0 (prereqs): 1
- Phase 1 (detection): 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17
- Phase 2 (interview): 4, 5, 6, 7, 8, 9
- Phase 4 (agent curation): 10, 11
- Phase 5 (populate): 12, 14, 15, 16, 17, 18

**Bidirectional asymmetries**:
- Finding 6 (Codex misdetected architecture; Claude right)
- Finding 7 (Codex URL default too generic; Claude read vite.config.ts correctly)
- Finding 8 (Claude missed purify-ts; Codex detected correctly)

Neither runtime alone produces reliable detection. This is the core insight: the parity test surfaces that the spec is not tight enough to force equivalent output across runtimes.

**Key themes observed**:

1. **Codex batches, Claude sequences**. Codex's multi-question batching (Finding 4) is the single highest-impact finding — breaks conditional branching in any flow with user-dependent follow-ups.

2. **Detection depth is asymmetric and unpredictable**. Neither runtime is consistently deeper or shallower; each has blind spots the other catches. Forced-checklist detection (Finding 3's proposed fix) would likely close most of Findings 3, 7, 8, 10, 14, 15 at once.

3. **Content-vs-reference convention is unspecified**. Finding 17 shows Codex duplicates content inline where Claude uses terse references. Spec needs to be explicit: project-config.json is answer-record, not knowledge-record.

4. **Per-package work is where Codex shortcuts hardest**. Finding 14 (per-package commands) and Finding 16 (packages list) show Codex does one-size-fits-all across packages; Claude reads each. Likely a token-saving heuristic under Codex.

**Recommended next step**: batch-fix the HIGH severity findings (4, 8, 14, 15) + Finding 3's forced-checklist proposal, which collapses several MEDIUM findings. Then rerun parity test as Run 2.

---

## Run 1 Resolutions

Fixes applied between Run 1 and Run 2. Run 2 verification uses this list as its checklist — each resolution names what it should close AND what could regress, so Run 2 can detect both "fix worked" and "fix broke something else."

### R1 Resolution 1 — Finding 3 fix: forced structured Detection Report

**Date**: 2026-04-24
**Commit**: `44ce2a4`
**Files changed**:
- `src/commands/setup-wizard/references/detect.md` — added a required **Detection Report** section (fenced YAML emit) with 8 rules governing the emit.

**What changed (substance)**:
- Phase 1 now ends with a required structured Detection Report. Free-form prose summary is explicitly NOT a substitute. Both runtimes emit the same YAML shape.
- Every field is required. `null` must carry a one-line reason — never omitted.
- **Dep+usage double-check** rule for library-category fields (auth, api-client, state-mgmt, styling, routing, error-handling, validation): `null` only if BOTH dep-manifest scan AND source-usage grep return empty. Canonical library/pattern shortlists listed inline.
- **Architecture bucket enumerated**: `layered | feature-modular | monorepo | feature-modular-monorepo | hexagonal | mvc | bloc | flat | other`. No free-form labels.
- **Per-package commands are per-package-specific**: every `packages[]` entry must read its `build_command` / `lint_command` / `type_check_command` / `test_command` from THAT package's manifest. Generic fallback allowed only when the manifest has no scripts, and must be marked `command_source: fallback`.
- **Workspace-member vs utility-manifest distinction**: only workspace-declared directories go in `packages[]`; ad-hoc script/utility manifests go in `optional.utility_manifests[]`.
- **`runtime_url` must read dev-server config** if present (vite.config.ts, next.config.js, etc.); framework defaults are acceptable ONLY when no dev-server config exists and must be flagged `source: framework-default`.
- Evidence sub-field or inline comment required for every non-null value.
- Wrapper-mode prefix applies to per-package commands too.

**Expected to close in Run 2** (9 findings from Run 1):
- Finding 3 — detection granularity asymmetry (structured emit forces parity)
- Finding 6 — architecture misdetection (enumerated bucket prevents invented labels)
- Finding 7 — runtime-URL generic default (explicit "must read dev-server config" rule)
- Finding 8 — purify-ts miss (dep+usage double-check rule)
- Finding 10 — Husky missed by Codex (`enforcement_tooling[]` is a required field)
- Finding 13 — off-by-one package count (workspace-member vs utility rule)
- Finding 14 — per-package commands uniform fallback (per-package required command fields)
- Finding 15 — wrong top-level build/lint command (evidence requirement + scripts-block rule)
- Finding 16 — `PACKAGES_DETECTED` content drift (workspace-member vs utility rule)

**Not expected to close** (orthogonal; need their own fixes):
- Finding 2 — wrong git repo for default branch (needs STEP 2.1 command-template change)
- Finding 4 — Codex batches questions (needs Phase 2 `{{ask}}` rule change)
- Finding 1 — wrapper confirm skipped by Claude (needs Phase 0 spec wording change)
- Finding 5 — Recommended-default UX divergence (cosmetic; deferred)
- Finding 9 — Q11 AC-verification option reshape (needs Phase 2 question spec tightening)
- Finding 11, 12, 17, 18 — populate/summary formatting divergences (need populate.md spec changes)

**Potential regressions to watch in Run 2**:
- **Stack fit**: unusual stacks (non-Vue/TS, non-monorepo, non-web) squeezing into the canonical field set. `optional:` is the escape hatch — if either runtime leaves fields empty where stack-specific values should appear, flag it. Parity test is single-project today; stack-fit will surface when test matrix grows.
- **Architecture bucket coerced**: runtime may pick the closest-looking bucket when evidence actually says `other`. Check `architecture_evidence` against the bucket in Run 2.
- **Token cost**: structured emit is longer than prose summary. Watch for Codex truncation (Codex `high`-reasoning context budget). If truncation happens, consider trimming optional fields or splitting the emit across phases.
- **Over-reporting**: dep+usage double-check could produce false positives (a lib in `devDependencies` but not actually used). Evidence field should disambiguate; mark regression if a library is named that has no source-code usage.
- **Enforcement-tooling noise**: every detected hook/linter/formatter now required as an entry. Watch that `enforcement_tooling[]` doesn't over-include (e.g., listing Prettier/ESLint without confirming they're actively enforced, not just installed).

**R2 verification checklist** (run after rerunning wizard on both sides):
1. Both runtimes emit a fenced YAML Detection Report at end of Phase 1 — same shape, same field set.
2. No field missing. `null` values carry a `# reason: ...` comment.
3. `error_handling.library == "purify-ts"` on BOTH runtimes (Run 1: Claude missed).
4. `packages[]` entries have per-package-specific commands on BOTH runtimes (Run 1: Codex uniform fallback).
5. `architecture_shape == "feature-modular-monorepo"` (or `monorepo` if the enumerated set is revised) on BOTH runtimes (Run 1: Codex picked wrong free-form label).
6. `runtime_url.source` references `apps/app-web/vite.config.ts` on BOTH runtimes (Run 1: Codex fell to framework default).
7. `enforcement_tooling[]` includes Husky on BOTH runtimes (Run 1: Codex missed).
8. `packages[]` excludes `scripts/` (listed in `optional.utility_manifests[]` instead) on BOTH runtimes — assuming `scripts/` is not declared as a workspace member.
9. `package_manager.tool` and `package_manager.outer_tool` both populated correctly for the wrapper-mode CSE test project (outer: npm, inner: yarn).
10. Language ordering matches Run 1 direction (TypeScript first) on both runtimes.

If the fix closed all 9 findings without regressions, move on to Finding 4 (no-batching rule). If any listed regression appears, log it as a new finding under `## Run 2 — <date>` and decide whether to revise this resolution before continuing.

### R1 Resolution 2 — Finding 4 fix: `{{ask}}` no-batching rule (shared contract)

**Date**: 2026-04-24
**Commit**: `3177259`
**Files changed**:
- `src/commands/setup-wizard/main.md` — tightened the `{{ask}}` marker contract in the "Variation markers" section (added three clauses: one-turn-per-ask, wait-before-compute for conditional follow-ups, applies to every command using `{{ask}}`); added IMPORTANT RULES #9 pointing back to the contract.

**Approach** (considered but rejected):
- Codex-only `{{#codex}}` conditional block, per-runtime emitter preamble, or Codex skill-global preamble — all would work, but the rule is a semantic contract of the `{{ask}}` marker itself, not a runtime patch. Shared placement is the semantically honest location; per-runtime treatment is the escalation path if Run 2 shows Codex still batches despite the shared rule. See conversation log 2026-04-24 for full tradeoff analysis.

**What changed (substance)**:
- `{{ask}}` marker definition now spells out: "One turn = one `{{ask}}`. Never batch, even adjacent questions. Wait-before-compute for conditional sub-follow-ups — do not pre-render follow-ups that depend on the primary answer."
- Contract stated as belonging to the sigil itself, so it flows to every command that uses `{{ask}}` (wizard now; onboard, constitute, breakdown, specify, verify when each is reviewed per PLAN §4).
- IMPORTANT RULES #9 gives the rule a second surface point so it's unmissable at load time.

**Expected to close in Run 2**:
- Finding 4 — Codex batches multiple `{{ask}}` blocks into one prompt (including Q0–Q3 batching AND Q11 follow-up pre-computation).

**Not expected to close**:
- onboard/constitute/breakdown/specify/verify — the contract applies there per its text, but those commands haven't been reviewed yet (PLAN §4: "After parity-batch closes"). When reviewed, their `{{ask}}` definitions should reference or inline the same contract.

**Potential regressions to watch in Run 2**:
- **Claude over-compliance**: Claude might add spurious turns if it interprets the rule too literally (e.g., breaking an existing confirmation into multiple turns). Watch for "Claude asks N+1 times than Run 1" in Q0–Q11.
- **Finding 5 interaction**: Claude's "Recommended" one-click UX (Q1–Q3) is still allowed under the rule — each question is still one turn; "Recommended" is just the default option presented inside that turn. If Claude suppresses "Recommended" defaults in Run 2 thinking the rule forbids them, that's a regression — the rule governs turn count, not UX affordance.
- **Codex may still batch despite the shared rule** — if Run 2 shows any batching, that's evidence prose alone doesn't hold for Codex, and we escalate to Codex-specific treatment: (i) `{{#codex}}` conditional block with stronger wording, (ii) Codex emitter prepends a runtime-level preamble, or (iii) Codex skill-global preamble. The escalation path is justified by Run 2 evidence, not pre-emptively.
- **Over-strictness in non-wizard commands**: if a later-reviewed command (onboard/constitute) has legitimate reasons to group questions (e.g., pure acknowledgement prompts that require no branching), the rule may need a carve-out. Currently no such carve-out — add only if Run 2 or later phases show real need.

**R2 verification checklist** (Codex side — Claude should remain unchanged):
1. Codex presents Q0 as a standalone turn (was: batched with Q1–Q3 in Run 1).
2. Codex presents Q5 through Q12 one per turn (was: batched 8-at-a-time in Run 1).
3. For Q11 branching: Codex does NOT render a Q12 URL prompt (or any follow-up content) until AFTER the user's Q11 answer is received. If the user picks `Off` or `Code-only`, no URL prompt is rendered at all.
4. Total Codex turns in Phase 2 increases from ~2 (Run 1: two batched prompts) to ~12 (one per question — roughly matching Claude's turn count).
5. Claude's Phase 2 turn count is unchanged from Run 1 (no over-compliance regression).
6. Claude still offers "Recommended" one-click defaults for Q1–Q3 where detection succeeded (Finding 5 UX preserved).

If Codex still batches in Run 2, open escalation path: add Codex-only tightening via `{{#codex}}` conditional or emitter preamble, justified by Run 2 evidence.

### R1 Resolution 3 — Finding 2 fix: `git -C "$SOURCE_ROOT"` templates in STEP 2

**Date**: 2026-04-24
**Commit**: `df47349`
**Files changed**:
- `src/commands/setup-wizard/references/detect.md` — STEP 2 rewritten to use concrete `git -C "$SOURCE_ROOT" …` templates; added a top-of-STEP-2 "Git-command targeting rule" principle; removed the now-redundant wrapper-mode prose note that was failing to hold on Codex.

**What changed (substance)**:
- All three detection commands (`symbolic-ref refs/remotes/origin/HEAD`, `symbolic-ref HEAD`, `branch --show-current`) now include `-C "$SOURCE_ROOT"` explicitly. No more reliance on runtime interpretation of "run against the inner repo."
- `$SOURCE_ROOT` = `.` in standalone, inner folder name in wrapper — `-C` form is safe and correct in both cases, so no branching required.
- Explicit clarifier added: "substitute the actual `SOURCE_ROOT` value before invoking — do NOT emit the literal string `$SOURCE_ROOT` to the shell" — guards against a runtime treating the placeholder as literal.

**Expected to close in Run 2**:
- Finding 2 — wrapper-mode git commands anchored on wrong repo (Codex read outer worktree's `.git`).

**Not expected to close**:
- Any other finding — Finding 2 is narrow.

**Potential regressions to watch in Run 2**:
- **`$SOURCE_ROOT` emitted literal**: if either runtime passes `git -C "$SOURCE_ROOT"` as a literal string to shell (without substituting the value), git errors out. Mitigation: explicit clarifier in the principle text. Watch for `fatal: cannot change to '$SOURCE_ROOT': No such file or directory` in Run 2.
- **Cwd drift**: `git -C "."` resolves relative to the runtime's cwd. If the wizard invocation runs from a non-workspace cwd (shouldn't per install convention), detection targets wrong repo. No known case; monitor if Run 2 reports a branch name that matches neither outer nor inner repo.
- **Standalone mode regression**: the `-C "."` form is a mild change from implicit cwd. If any runtime has an edge-case issue with it, `DEFAULT_BRANCH` may come back empty or wrong even in standalone. Unlikely (standard git behavior), but watch.
- **No impact on Claude expected** — Claude already detected correctly in Run 1 by reading the inner repo. The `-C` form just removes ambiguity; Claude's behavior should be unchanged.

**R2 verification checklist**:
1. Codex reports `DEFAULT_BRANCH = dev` for the CSE test project (was `codex-parity` in Run 1).
2. Claude still reports `DEFAULT_BRANCH = dev` (no regression).
3. `.devforge/project-config.json` on both sides contains `"default_branch": "dev"`.
4. No literal-`$SOURCE_ROOT` shell errors surfaced in either runtime's Phase 1 trace.
5. Detection Report (R1 Resolution 1) `default_branch` field populated with `dev` on both sides.

### R1 Resolution 4 — Finding 15: ground truth recorded for CSE test project

**Date**: 2026-04-24
**Commit**: `cfc7a59`
**Files changed**: `codex-port/phase-R/parity-findings.md` only (data recording; no spec change).

**Why this is separate from a spec fix**: Finding 15 is not a spec-interpretation problem — it's a data-correctness problem. Run 1 showed Claude and Codex disagreeing on the top-level build/lint commands for the CSE project. R1 Resolution 1 (Detection Report + evidence rule) is the mechanism that will make both runtimes cite their sources in Run 2, but without independently-verified ground truth, R2 scoring can only measure convergence, not correctness. This resolution records the ground truth.

**Source**: `/Users/mykolakudlyk/Projects/testParity/db-cse-ui-strata/package.json` at pinned commit `9354389c6` (shared across both worktrees per PLAN §4).

**Observed facts about the root manifest**:
- No script named `build` (bare). Variants present: `build:ci`, `build:raw`, `build:core:raw`, `build:web:raw`, `build:dev`, `build:qa`, `build:prod`, `build:origin`, `build:force`.
- No script named `lint` (bare). Variants present: `lint:core` (`lerna run --scope pkg-* lint`), `lint:web` (`lerna run --scope app-web lint`).
- No script named `typecheck` (bare). Related: `check` (`lerna run --scope pkg-* check && lerna run --scope pkg-* build && lerna run --scope app-* check` — NB: also triggers pkg-* build, not a pure typecheck), `check-web` (app-* check only).
- `build:ci` = `npm run bootstrap && npm run build:raw` → CI pipeline's canonical build is `build:raw`.

**Ground truth (what the root-level commands SHOULD be)**:

| Field | Correct value | Reasoning |
|---|---|---|
| `BUILD_COMMAND` | `yarn build:raw` | CI pipeline calls this path (`build:ci` → `build:raw`). Produces pkg-* raw + app-web raw. |
| `LINT_COMMAND` | `yarn lint:core && yarn lint:web` | No bare `lint` script; correct answer is the union of pkg-* + app-web lint. |
| `TYPE_CHECK_COMMAND` | `yarn check` (ambiguous — also builds pkg-*) OR per-package `vue-tsc --noEmit` | No clean top-level typecheck script. `check` runs builds as a side effect. Per-package `vue-tsc --noEmit` is the cleanest pure typecheck. |

**Run 1 scoring against ground truth**:

| Command | Claude (Run 1) | Codex (Run 1) | Ground truth | Claude correct? | Codex correct? |
|---|---|---|---|---|---|
| BUILD | `yarn build:raw` | `yarn build:origin` | `yarn build:raw` | ✅ | ❌ (`:origin` is not the CI path) |
| LINT | `yarn lint:core && yarn lint:web` | `yarn lint:web` | `yarn lint:core && yarn lint:web` | ✅ | ❌ (missing `lint:core` — pkg-* packages unlinted) |
| TYPECHECK | `vue-tsc --noEmit` (per-package) | _not reported_ | `yarn check` or `vue-tsc --noEmit` | ✅ (valid per-package) | n/a |

**Finding**: Codex's root-level commands in Run 1 were **incorrect**, not just different. `yarn build:origin` is a secondary build variant, not the canonical one. `yarn lint:web` is incomplete — it skips linting of all pkg-* packages. These commands would fail in real use: a developer running them expecting "build everything" or "lint everything" would get partial results.

**Root-cause hypothesis**: Codex likely picked the *first or shortest* matching script name without evaluating which script is canonical. Claude's scan went deeper — cross-referenced `build:ci` to determine the CI path, and composed `lint:core && lint:web` as a union when no bare `lint` existed.

**R2 expected outcome** (with R1 Resolution 1's evidence rule applied):
- Both runtimes must emit `build_command` with an `evidence:` citation. Correct emits will quote `package.json scripts.build:raw` (or reference `build:ci → build:raw` chain).
- Both runtimes must emit `lint_command` with evidence. Correct emits will note the absence of a bare `lint` script and compose the pkg-* + app-web union explicitly.
- If either runtime still emits `yarn build:origin` or `yarn lint:web` alone in R2, that's a Finding-3-fix regression — the evidence rule is being followed in form but not substance, and the spec needs tighter composition guidance (e.g., "when no bare `build` / `lint` script exists, report the CI-referenced script for build and the comprehensive-scope union for lint").

**R2 verification checklist** (merges into R1 Resolution 1's checklist):
1. Claude Detection Report: `build_command: yarn build:raw`, evidence cites `scripts.build:raw` or `build:ci` chain.
2. Codex Detection Report: `build_command: yarn build:raw` (not `build:origin`), evidence cites the same.
3. Claude Detection Report: `lint_command: yarn lint:core && yarn lint:web`, evidence notes absence of bare `lint`.
4. Codex Detection Report: `lint_command: yarn lint:core && yarn lint:web` (not `yarn lint:web` alone).
5. Either runtime choosing `yarn check` for typecheck should flag in evidence that it also builds pkg-* (side effect).

---

## Run 2 — 2026-04-24

**Forge commit at run start**: `cfc7a59` (after R1 Resolutions 1–4 — Findings 3/4/2/15 fixes landed).

**Test infrastructure**:
- `testParity/` on branch `claude-parity-run2` — Claude side (reset to pre-install `64bb325`, reinstalled with current spec)
- `testParity-codex/` on branch `codex-parity-run2` — Codex side (same)
- Source (`db-cse-ui-strata/`) pinned to same commit `9354389c6` as Run 1

**Scope**: setup-wizard phase (same as Run 1). R1 Resolution 1–4 verification checklists scored at end of run.

**Findings logged live (continue numbering from Run 1; Run 1 ended at Finding 18)**:

### Finding 19 — NEW IN RUN 2 — MEDIUM — Phase 2 Q0: project-name detection blindly trusts `manifest:name`

**Severity**: MEDIUM (both runtimes land wrong default; user-facing outcome degraded from Run 1)

**Observed (Run 2)**:
- **Codex-R2**: proposed `root` verbatim from `db-cse-ui-strata/package.json:name` for Q0. Spec-adherent (per `questions.md` Q0 lines 42–52).
- **Claude-R2**: refused `root` as "not descriptive", surfaced three alternative candidates (`db-cse-ui-strata` / `Strata` / `DB CSE UI`) with cited evidence — directory name, pipeline-file suffix (`strata_dev_pipeline.yml`), and `package.json:repository` field. Dropped README as a source.
- **Neither runtime** surfaced `CSE UI` — the value both runtimes converged on in Run 1.

**Comparison to Run 1**:
- **Claude-R1**: proposed `CSE UI` (README-derived). **Off-spec** per Q0 (spec says manifest-only), but landed a user-friendly answer.
- **Codex-R1**: Q0 was batched with Q1–Q3; user typed `CSE UI` directly. Codex's actual per-question Q0 default was never visible. → Codex-R2's `root` proposal is **new visibility**, not a regression.
- **User-facing outcome worse in R2**: both runtimes in R1 yielded `CSE UI` (one via off-spec READ, one via batched free-text input). In R2 neither surfaces it.

**Not caused by R1 Resolutions 1–4**: none of those four fixes touched Q0. `detect.md` STEP 2 (Finding 2 fix) is branch detection; Detection Report (Finding 3 fix) does not require `project_name` as a field; `{{ask}}` semantics (Finding 4 fix) does not change question source hierarchy; ground-truth recording (Finding 15) is data only.

**Root cause — `questions.md` Q0 spec is too narrow** (lines 42–52):

> If a manifest file exists at SOURCE_ROOT and contains a name field:
> "I found the project name `[detected name]` in `[manifest file]`. Confirm or override."

Three gaps:

1. **No scaffold-default blocklist.** Monorepo root manifests commonly declare `"name": "root"`, `"name": "workspace"`, `"name": "monorepo"`, `"name": "project"`, etc. — scaffold artifacts, not meaningful names. Spec treats them identically to real project names and presents them verbatim to the user.
2. **No fallback hierarchy.** If `manifest:name` is missing OR a scaffold default, spec has no guidance on where to look next (README `# Heading`, `manifest:repository` / `manifest:homepage` URL path segment, directory basename).
3. **Single-source rigidity.** Spec presents exactly ONE candidate (or free-text ask). Claude-R2's multi-option approach with cited evidence is arguably better UX, but spec neither endorses nor forbids it — which is itself a cross-runtime divergence source. Codex reads the spec literally (single candidate); Claude exercises judgment (multi-option).

**Why this was invisible in Run 1**:
- Claude's off-spec README consultation happened to land the right answer.
- Codex's batching hid its per-question behavior — user's free-text input papered over the spec-default proposal.
- R1 Resolution 2 (`{{ask}}` no-batching) made Codex's per-question behavior visible for the first time, which is how this gap surfaced now.

**Impact**:
- `PROJECT_NAME` lands as `root` (Codex) or `db-cse-ui-strata` (Claude) if user confirms — wrong value flows to CLAUDE.md / AGENTS.md / `project-config.json`.
- User must override on both runtimes to get a meaningful name. Cross-runtime parity at Q0 is NOT achieved.

**Proposed fix**:

1. Add scaffold-default blocklist in Q0: treat `root`, `workspace`, `monorepo`, `project`, `app`, `main`, `source`, `template`, `new-project`, `my-app` as "effectively null" — fall through to hierarchy step 2.
2. Add explicit source hierarchy (first non-null wins; all others presented as alternatives with cited evidence):
   - a. `manifest:name` (if present AND not scaffold-default)
   - b. README title — first `# Heading` in `README.md` / `README.rst` / `README.txt` at SOURCE_ROOT
   - c. `manifest:repository` / `manifest:homepage` URL → extract last path segment, titleize
   - d. Directory basename (SOURCE_ROOT), titleized (kebab/snake → Title Case)
   - e. Free-text ask (no default)
3. When multiple sources yield distinct candidates, present all with cited evidence — codifies Claude-R2's behavior, makes spec-compliant rather than off-spec.

**Expected R3 verification**: both runtimes propose `CSE UI` (or equivalent README-title-derived name) as the top candidate for the CSE test project. Cross-runtime delta on Q0 collapses.

---

### Finding 20 — NEW IN RUN 2 — MEDIUM — Phase 2 Q2: Codex omits Options list because ask-boundary is spec-ambiguous

**Severity**: MEDIUM (user asked an enumerated-choice question without seeing the choices — forced to free-text or guess)

**Observed (Run 2)**:
- **Codex-R2**: presented Q2 evidence-rich lead-in and the closing question "What type of project is this?" — but **omitted the Options list** entirely. No bullet choices shown. (User confirmed via back-channel during the run.)
- **Claude-R2**: lead-in + 3 enumerated options with descriptions (Frontend / Full-stack / Library), "Recommended" marker on option 1, "Type something" + "Chat about this" fallbacks. Spec-adherent.

**Comparison to Run 1**:
- **Codex-R1**: Q0–Q3 batched; unknown whether Options were embedded in the combined prompt. User's answer `Frontend / web application` suggests Options were visible somehow (or user answered from memory).
- **Claude-R1**: presented Options as selectable, user picked Recommended. Consistent with R2.
- **Codex-R2 behavior is new visibility** (exposed by R1 Resolution 2's no-batching rule), not a regression.

**Not caused by R1 Resolutions 1–4**: none of the four fixes touched `questions.md` Q2. This is a pre-existing spec gap made visible now that Codex asks questions individually.

**Root cause** — `questions.md` Q2 (lines 70–92) structure:

```
**If concrete indicators were found:**

> Based on what I found — [quote...] — this looks like a [proposed type]. What type of project is this?
>
> Options:
> - Frontend / web application
> - Backend API / service
> - ...
```

The question is rendered as a markdown blockquote. The Options list is continued-blockquote (still prefixed with `>`) but visually separated by a blank-blockquote line. There is NO explicit `{{ask "..."}}` / `{{/ask}}` wrapping around the full question + options.

Codex appears to parse the ask-boundary at "What type of project is this?" and treat the Options list as trailing context — so it asks the question but omits the choices. Claude renders the whole blockquote (including Options) as one choice block via its structured-select UI primitive. Both interpretations are defensible given the loose markdown; the spec is ambiguous about where the ask ends.

**Cross-question scope (observed in full Run 2)**:

| Question | Options format in spec | Codex-R2 behavior |
|---|---|---|
| Q2 (project type) | Separate `Options:` bullet list | ❌ Omitted — collapsed to meta-options |
| Q3 (languages) | Confirm-detection (no canonical enum) | ✅ N/A — not a canonical-enum question |
| Q4 (architecture) | Separate `Options:` bullet list | ❌ Omitted — collapsed to meta-options |
| Q5 (error handling) | Confirm-detection | ✅ Meta-options (spec-appropriate) |
| Q6 (API layer) | Confirm-detection | ✅ Meta-options (spec-appropriate) |
| Q7 (testing) | Confirm-detection | ✅ Meta-options (spec-appropriate) |
| Q8 (enforcement) | Separate `Options:` bullet list | ❌ Omitted — collapsed to meta-options |
| Q9 (AI attribution) | Binary yes/no | ❌ Meta-options with **inverted default direction** |
| Q10b (Codex tiers) | **Inline** in question text | ✅ Rendered correctly |
| Q11 primary (AC verification) | Separate `Options:` bullet list | ✅ Rendered correctly (inconsistent with Q2/Q4/Q8) |
| Q11 follow-up (which modes) | Separate `Options:` bullet list | ✅ Rendered correctly |

**Updated hypothesis**: behavior is **stochastic** with list-format Options, not strictly structural. Q11 has the same markdown shape as Q2/Q4/Q8 but renders correctly. Q10's inline-in-text format always renders. This strengthens Finding 20's Option A (explicit `{{ask}}` / `{{/ask}}` wrapping) over Option B (formatting): Option B assumes a structural distinction that Codex doesn't consistently honor; Option A removes interpretation entirely.

**Impact**:
- Users on Codex are asked to choose among options they cannot see. Either they type from memory (fragile) or skip to free-text (losing enumerated structure).
- `PROJECT_TYPE` (and downstream fields if the same bug repeats at Q3–Q11) may land as free-text rather than one of the spec's canonical enumerated values → downstream commands that branch on exact-match enum values break.
- Cross-runtime parity on enumerated answers is NOT achieved by current spec.

**Relationship to R1 Resolution 2**: the no-batching rule made this visible but didn't cause it. The deeper gap — implicit ask boundaries in `questions.md` — was always there. This argues for extending R1 Resolution 2's `{{ask}}` contract by requiring every interview question to be a single `{{ask}}`…`{{/ask}}` block with options inside it, rather than loose markdown.

**Proposed fix** (three options):

- **Option A (structural — recommended)**: wrap every question's content in explicit `{{ask "question text"}}` ... `{{/ask}}` markers with Options as a bullet list inside. Both runtimes parse the full ask as one unit. Composes cleanly with R1 Resolution 2 ("one turn = one `{{ask}}`") — combined, the spec contract becomes: every `{{ask}}` block includes the lead-in + options + fallback text; each is one turn; never batched.
- **Option B (formatting only)**: restructure Options to be unambiguously inside the blockquote (e.g., numbered list wrapped in the same blockquote text, no blank-blockquote separator line). Lower effort, weaker guarantee — still relies on markdown-parsing interpretation.
- **Option C (louder prose)**: add an IMPORTANT RULE to `setup-wizard/main.md`: "When a question spec lists Options, ALWAYS present every option to the user as selectable choices, regardless of surrounding markdown structure." Runtime-behavior rule, not a structural fix.

**Recommendation**: Option A. Aligns with R1 Resolution 2's direction (`{{ask}}` as the unit of interaction), removes interpretation, touches all affected questions in one edit pass.

**Expected R3 verification**: Codex presents every enumerated Options list in full at every choice question (Q2–Q11 where applicable). Cross-runtime delta collapses on option-presentation.

---

### Finding 21 — NEW IN RUN 2 — MEDIUM — Architecture enum missing `clean`; also needs to allow compound labels

**Severity**: MEDIUM (both runtimes land wrong or no architecture label; polluted project-config downstream)

**Observed (Run 2)**:
- **Claude-R2**: proposed `"feature-modular monorepo with hexagonal layering"` — reached for `hexagonal` as nearest enum bucket despite the evidence (`data/ + domain/ + domain/cases/ + presentation/` with repository pattern and use-cases) being **Clean Architecture**, not hexagonal.
- **Codex-R2**: refused to propose any specific architecture; asked user to choose Confirm / Override / Defer with no bucket named.
- **User manually overrode** to `"Clean Architecture, feature-modular monorepo"` on both sides.

**Correction to Finding 6 (R1)**: Finding 6's "Claude correct, Codex wrong" narrative was itself wrong. Claude-R1's `feature-modular monorepo` answer was **also incomplete** — missed the Clean Arch layering. Codex-R1's `layered / BLoC + use-cases + repositories` was poorly labeled but actually described Clean Arch in substance. Neither runtime has ever correctly labeled this codebase in either run.

**Root cause**: R1 Resolution 1's `architecture_shape` enum list is incomplete:

```
layered | feature-modular | monorepo | feature-modular-monorepo | hexagonal | mvc | bloc | flat | other
```

Missing: `clean` (Clean Architecture — domain/use-cases/adapters with inward dependency direction). Claude reached for `hexagonal` as the nearest plausible bucket. Codex, encountering a no-fit situation, bailed to meta-options rather than picking a wrong bucket. Both behaviors are defensible given the gap.

**Secondary issue — no compound labels**: the CSE codebase is genuinely `clean + feature-modular-monorepo` simultaneously. R1 Resolution 1's enum is a scalar (`architecture_shape: feature-modular-monorepo`), not an array. Real codebases often combine patterns; the scalar enum forces a lossy choice.

**Proposed fix**:
1. Add `clean` to the enum with evidence cues in detect.md: "Clean Architecture indicators: `use-cases` directory or `domain/cases/`, repository pattern with interface in domain + implementation in data, dependency direction strictly inward (domain imports nothing from adapters)."
2. Change `architecture_shape` from scalar to array in Detection Report schema: `architecture_shape: [clean, feature-modular-monorepo]`. Populate.md's rendering should join with `+`: `"Clean Architecture + feature-modular monorepo"`.
3. Add rule: "When evidence supports multiple patterns, emit all that apply. When NO enum bucket fits, emit `[other]` with explicit `architecture_evidence` citation."
4. Refresh Finding 6's "correct answer" narrative in the Run 1 section of this file (or note superseded by Finding 21).

**Expected R3 verification**: both runtimes emit `architecture_shape: [clean, feature-modular-monorepo]` (or equivalent compound) for CSE; no manual user override needed.

---

### Finding 22 — NEW IN RUN 2 — HIGH — Phase 1 ↔ Phase 2 field linkage missing (Q11 URL is the visible failure)

**Severity**: HIGH (lands wrong/blank value in `AC_RUNTIME_URL` on Codex; cascades to runtime-assisted verification failure)

**Observed (Run 2)**:
- **Claude-R2 Q11 URL**: opened `apps/app-web/vite.config.ts`, extracted `server: { host, port, https }`, proposed `https://okta.local.dev.dice-tools.com:8080` — correct. ✅
- **Codex-R2 Q11 URL**: asked blank — no URL proposed, no evidence, no mention of vite.config.ts. Worse than Run 1 (R1 at least guessed `http://localhost:5173`; R2 proposes nothing).

**Root cause**: two linked gaps:

1. **Detection Report not emitted** (Finding 23). R1 Resolution 1's Detection Report required a `runtime_url` field populated from dev-server config. If Codex had emitted it, `runtime_url` would be available for Phase 2 to reference.
2. **Even if Phase 1 populated `runtime_url`, `questions.md` Q11 doesn't link to it.** Q11's conditional URL follow-up is spec'd as a fresh free-text ask, not as "present the detected `runtime_url` as default and confirm/override." So even with a working Detection Report, Phase 2 would still ignore it.

**Why this cascades**: the pattern repeats for any Phase-2 question whose answer might be detectable in Phase 1. `default_branch` (Q0 area), `project_description` from README (Q1), architecture (Q4), error-handling library (Q5), API layer (Q6), testing framework (Q7) — all are potential Phase 1 detection outputs. Spec currently re-asks each via Phase 2 without referencing Phase 1 outputs.

Claude happens to consult its Phase 1 memory organically during Phase 2 (which is why Q11 URL worked on Claude in both runs). Codex treats Phase 2 as independent from Phase 1 detection. Spec doesn't force the linkage either way.

**Proposed fix**:

1. **Per-question linkage notes** in `questions.md` — for every question whose answer has a Phase 1 detection counterpart, add a "Phase 1 source" line:
   > **Phase 1 source**: `detection_report.runtime_url` (from `vite.config.ts` / `next.config.js` / dev-server config). If populated, present as pre-filled default with confirm/override. If null, ask free-text.
2. **Phase 2 preamble rule** in `main.md`: "Before asking any question, check whether the Detection Report has a field populating the answer. If yes, present the detected value as the default; ask to confirm/override. If no, ask fresh."
3. **Depends on Finding 23 closure** — without a Detection Report, there's nothing to reference. Finding 22 closure requires Finding 23 closed first.

**Expected R3 verification**: Codex Q11 URL presents `https://okta.local.dev.dice-tools.com:8080` as pre-filled default (matching Claude), sourced from Detection Report.

---

### Finding 23 — NEW IN RUN 2 — HIGH (blocker) — Both runtimes skip the required YAML Detection Report emit

**Severity**: HIGH — this is the largest single failure mode in Run 2. R1 Resolution 1's centerpiece fix (structured YAML emit) did not land on either runtime. All closures claimed via this mechanism need separate evidence.

**Observed (Run 2)**:
- **detect.md says**: "Before moving to Phase 2, emit a single structured Detection Report as a fenced YAML code block. This is required output, not optional prose."
- **Claude-R2 emitted**: a "Phase 1 Detection Summary" as a structured-prose bullet list (readable, thoughtful, but NOT fenced YAML). Contents correct; shape wrong.
- **Codex-R2 emitted**: free-form status sentence ("I have the verification mode and runtime URL. I'm finishing the detection data..."). No structured form at all.
- **Neither rendered the YAML template** specified in detect.md as a filled, fenced code block.

**Root cause**: the spec language describes the requirement but doesn't enforce it:
- Says "required output, not optional prose" — but doesn't state the consequence of omission (no HALT, no re-prompt, no Phase 2 precondition)
- Presents the YAML template as a fillable shape, but runtimes read it as reference documentation rather than an action-required emit
- No Phase 2 preflight check for the Detection Report's existence

Both runtimes optimized past the emit because the spec didn't make proceeding-without-it impossible. Each substituted its own summary style (prose bullet list / free-form sentence) as "equivalent."

**Cascade impact** — closures claimed via Detection Report and their actual Run 2 status:

| Finding | Claimed via R1 Res 1 | Actual R2 status | Mechanism of actual status |
|---|---|---|---|
| 3 (detection granularity) | ✅ | Partial | Prose summaries more consistent, but not mechanically comparable |
| 6 (architecture) | ✅ | ❌ Open (Finding 21) | Enum gap, no bucket for Clean Arch |
| 7 (runtime_url) | ✅ | Claude ✅ / Codex ❌ | Claude's "must read config" rule leaked to prose; Codex ignored |
| 8 (purify-ts) | ✅ | ✅ Closed | Dep+usage rule held independently of Detection Report |
| 10 (Husky) | ✅ | Claude ✅ / Codex ❌ | Codex has no `enforcement_tooling[]` to emit without DR |
| 13 (packages set) | ✅ | ❌ Open | BOTH wrong in opposite directions — see reframe below |
| 14 (per-package cmds) | ✅ | ❌ Open (partial) | No per-package structured emit to verify |
| 15 (build/lint top-level) | ✅ | Build ❌ / Lint ✅ | Lint closed via evidence rule; build still wrong on Codex |
| 16 (packages[] ordering) | ✅ | ❌ Open | Both sides have different orderings from each other AND from R1 |

**Net**: only Finding 8 cleanly closed via R1 Resolution 1. Findings 3, 6, 13, 14, 16 remained open because the structured emit never happened. Findings 7, 10, 15 partially closed via surgical sub-rules that leaked into prose behavior.

**Proposed fix — three combined changes**:

1. **HALT language in detect.md**:
   > "You MUST emit this Detection Report as a fenced YAML code block. This is the FINAL action of Phase 1. Do NOT proceed to Phase 2 until the YAML block has been rendered verbatim to the user. A prose summary does NOT satisfy this requirement. If you have not emitted the block, return to Phase 1 and emit it before any Phase 2 activity."

2. **Visual emit markers** bracketing the template:
   ```
   # >>> EMIT THIS BLOCK VERBATIM TO USER BEFORE PHASE 2 <<<
   detection_report:
     ...
   # >>> END OF EMIT <<<
   ```

3. **Phase 2 preflight check** in `questions.md` opening or `main.md`:
   > "Before asking Q0: verify the Phase 1 Detection Report was emitted as a fenced YAML block. If not visible in conversation, return to Phase 1 and emit it."

4. **Consider generator-level structural fix (Path B from strategic eval)**: move Detection Report composition out of LLM-trust. LLM provides field values; a Python helper in `scripts/lib/` composes the YAML. Higher engineering cost, structural guarantee. Tracked separately from this spec fix.

**Expected R3 verification**: both runtimes emit a fenced YAML Detection Report before Phase 2. Structural comparison becomes possible. Findings 13, 14, 16 closure mechanically verifiable via field-level diff.

---

### Finding 24 — NEW IN RUN 2 — LOW — Detection doesn't assess freshness of README/doc evidence

**Severity**: LOW (false-positive agent, user can override; low-volume impact)

**Observed (Run 2)**: both runtimes kept `migration-engineer` agent based on README's "Strata cutover from cse-ui" section. User noted this section is **stale** — the cutover is legacy documentation, not active work. Both runtimes treated README as current/authoritative without freshness check.

**Root cause**: `agents.md` Phase 4 treats README mentions as authoritative evidence without cross-referencing:
- Git history of the relevant directories / files
- Presence of migration-specific artifacts (migration scripts, dual-write code, cutover tooling)
- Date of last meaningful activity in areas the README describes

**Proposed fix**:
- Add to `agents.md`: "When citing README content as evidence for keeping an agent, verify the content is current. Signals: recent git commits to referenced directories; presence of artifacts matching the README claim; absence of 'DONE' / 'COMPLETED' markers. If README content appears historical, present the agent as 'suggested — please verify' rather than auto-keep."
- Accept false positives as low-impact when user can override; don't over-engineer.

---

### Finding 25 — NEW IN RUN 2 — MEDIUM — Codex implements brownfield detection as a generated script, not as per-manifest LLM reasoning

**Severity**: MEDIUM (applies hidden filters/defaults not spec-derived; causes Findings 13/16/26-style divergence downstream)

**Framing refined via direct inquiry** (user asked Codex to self-report its tool usage during the session):
- Codex has no structured Read tool. All file reads route through `exec_command` (shell). Primary read pattern: `sed -n 'start,endp' <file>`. Primary search: `rg --files` / `rg -n`. Primary directory enumeration: `find` / `ls -la`. These are fine.
- Writes go through `apply_patch` (proper diff tool) — also fine.
- The problem pattern is **bulk-parse-via-script**: Codex used `node -e '<complex fs operations>'` a few times to parse many `package.json` files at once and generate structured output (`PACKAGES_DETECTED` / `PACKAGE_STACKS` metadata). One node one-liner errored mid-run (`[eval]:1`) but Codex continued.

So the real issue isn't "Codex uses node" — it's **detection-as-script vs detection-as-reasoning**. Claude carries per-manifest content in conversational memory and reasons about each one individually. Codex generates a script that iterates all manifests and emits derived data. Scripts apply filters and defaults that aren't spec-derived.

**Observed downstream consequences (from Run 2 diffs)**:
- **Finding 13** (missing `packages/pkg-test`): Codex's enumeration script applied some filter that dropped it. A per-manifest LLM read wouldn't have a filter.
- **Finding 16** (unusual ordering): script's iteration order (probably alphabetic within categories) rather than workspace-declaration order.
- **Finding 26** (`npm run` defaults): script's default runner, not lockfile-aware. The spec rule "yarn.lock → yarn" lives in `detect.md` but the script doesn't read `detect.md`.

**Impact**:
- **Portability**: bulk-parse scripts require a language runtime (node in this case) installed at detection time. Pure-Python / pure-Rust / pure-Go target projects have Codex's bulk-parse approach fail outright.
- **Fragility**: complex one-liners prone to syntax errors; a single failure can silently corrupt detection.
- **Hidden drift from spec**: script-applied filters/defaults bypass spec rules because the spec is for the LLM, not for a script the LLM generates.

**Proposed fix** (post-R3; wait to see if Findings 13/16/26 close first via R3's batch):

Add to `detect.md` and `populate.md`:
> "Detection is per-manifest reasoning, not per-project scripting. When populating `packages[]`, `per_package_commands`, or any other structured Report field, read each manifest file individually and populate the Report fields directly from what you observed — do not generate a script that emits the structured data as bulk output. Per-file reasoning keeps the detection accountable to spec rules on each entry (workspace-member check per Rule 5, lockfile-based runner selection, dep+usage double-check per Rule 2, etc.). This does NOT forbid shell use for individual reads (`sed -n`), searches (`rg`), or directory listings (`find` / `ls`) — those are the correct tools for file-by-file interaction. What's forbidden is the script-as-detection pattern: `node -e '...fs.readdirSync...emit JSON...'` or equivalent in any language."

**R4 priority** — pick up only if R3 still shows Findings 13/16/26 divergence despite their direct fixes landing. If R3 closes those via the Finding 23/26/22 fixes, this Finding 25 is moot (symptom disappears when detection-as-reasoning is structurally enforced via Detection Report emit).

---

### Finding 26 — NEW IN RUN 2 — MEDIUM — Command runner divergence: Codex ignores lockfile-based runner selection

**Severity**: MEDIUM (commands in `project-config.json` and downstream CLAUDE.md/AGENTS.md don't match project convention; users running them get "yarn not found" or "engine mismatch")

**Observed (Run 2)** — from `project-config.json` diff:

| Command | Claude-R2 | Codex-R2 | Correct per lockfile |
|---|---|---|---|
| BUILD_COMMANDS | `yarn build:raw` | `npm run build:origin` | `yarn` (yarn.lock at SOURCE_ROOT) |
| TYPE_CHECK_COMMANDS | `yarn check` | `npm run check` | `yarn` |
| LINT_COMMANDS | `yarn lint:core && yarn lint:web` | `npm run lint:core && npm run lint:web` | `yarn` |

CSE has `yarn.lock` at SOURCE_ROOT. `detect.md` STEP 3 "Command-runner selection" rule explicitly says: `yarn.lock → yarn`. Codex ignored this.

**Root cause hypothesis**: Codex's Phase 3 population used its own implementation (likely the node shell enumeration from Finding 25), which defaulted to `npm run` without checking for lockfile. The spec's heuristic lives in detect.md but Codex's Phase 3 logic doesn't read back to detection outputs for runner choice.

**Related to Finding 23**: if Detection Report were emitted, `package_manager.tool: yarn` would be a field. Phase 3 would read from there instead of re-implementing. Tied to Finding 22 (Phase 1↔2 linkage) too.

**Impact**:
- `project-config.json` commands unusable as-written if user tries to run them.
- Downstream verification / execute-task commands will fail with `npm run build:origin` in a yarn-managed project.
- Breaks the "wizard writes real commands that actually run" contract (IMPORTANT RULE #4 in setup-wizard/main.md).

**Proposed fix**:
1. Strengthen `detect.md` Command-runner selection: "Before emitting any `BUILD_COMMAND` / `LINT_COMMAND` / `TYPE_CHECK_COMMAND` / `TEST_COMMAND`, verify the chosen runner matches observable lockfile signals at SOURCE_ROOT. Emit per the lockfile rule, not per runtime preference."
2. Tie to Finding 23 closure: Detection Report emit enforces `package_manager.tool` field with evidence; Phase 3 reads from there.
3. Add `populate.md` rule: "Per-command emit reads `package_manager.tool` from Detection Report. Compose runner prefix from that value, not from defaults."

**Expected R3 verification**: Codex emits `yarn build:raw`, `yarn check`, `yarn lint:core && yarn lint:web` — matching Claude.

---

## Run 2 — R1 Resolution Scoring

| Resolution | Findings targeted | Result |
|---|---|---|
| **R1 Res 1** — Detection Report + rules | 3, 6, 7, 8, 10, 13, 14, 15, 16 | **Partially failed** — YAML emit skipped by both runtimes (Finding 23). Surgical sub-rules landed independently where prose could carry them: dep+usage rule closed Finding 8 ✅; `runtime_url` rule closed Finding 7 on Claude (not Codex). Most expected closures remain open — see Finding 23 cascade table. |
| **R1 Res 2** — `{{ask}}` no-batching | 4 | **Closed** ✅ — held across all 11 questions including Q11 conditional URL branch. Also closed Findings 1 and 9 as side-effects. |
| **R1 Res 3** — `git -C "$SOURCE_ROOT"` templates | 2 | **Closed** ✅ — Codex now targets SOURCE_ROOT correctly for default-branch detection. |
| **R1 Res 4** — ground truth recorded for CSE | 15 (scoring anchor) | **Useful** — lint-side closed (Codex now emits `lint:core && lint:web`); build-side still wrong (Codex: `build:origin`, ground truth: `build:raw`). Ground-truth recording enabled definitive scoring. |

## Run 2 — Closures (findings closed or confirmed in R2)

- ✅ **Finding 2** — git-command targeting (R1 Res 3)
- ✅ **Finding 4** — Codex batching (R1 Res 2)
- ✅ **Finding 8** — Claude purify-ts miss (R1 Res 1 dep+usage rule)
- ✅ **Finding 9** — Claude Q11 option reshape (side-effect of R1 Res 2)
- ✅ **Finding 12** — Codex summary abbreviation (resolved without explicit fix)
- Partially: **Finding 15 lint side** (Codex now emits correct lint command)
- Partially: **Finding 7 Claude side** (Claude consistently reads vite.config.ts)

## Run 2 — Still open from Run 1

- ❌ Finding 1 — wrapper-confirm (works in R2 via side-effect, not structural fix)
- ❌ Finding 3 — API_LAYERS: Codex still `"GraphQL"` not `"Apollo Client"`
- ❌ Finding 5 — Recommended-default UX (cosmetic, unchanged)
- ❌ Finding 6 — architecture misdetection (**superseded by Finding 21** — root cause is enum gap)
- ❌ Finding 7 — Codex `runtime_url` blank (**Finding 22 root cause**)
- ❌ Finding 10 — Codex Husky miss (cascade of Finding 23)
- ❌ Finding 11 — Phase 4 override UX (cosmetic, unchanged)
- ❌ Finding 13 — packages set divergence (BOTH wrong, opposite directions: Claude hallucinated `pkg-test`; Codex over-included `scripts/`. Correct answer: 25 members. See Finding 13 reframe below.)
- ❌ Finding 14 — per-package commands (not yet fully diffed — see R3 scoring)
- ❌ Finding 15 build-side — Codex emits wrong build command (`build:origin` vs `build:raw`)
- ❌ Finding 16 — packages[] ordering (different orderings; both different from R1's pattern)
- ❌ Finding 17 — free-text fields (not yet fully diffed via CLAUDE.md ↔ AGENTS.md)
- ❌ Finding 18 — JSON formatting (cosmetic, unchanged)

## Run 2 — Parity verdict (Path A: semantic output match)

**`project-config.json` semantic fields: ~80–85% match.**

Converged:
- description, type, frameworks, languages
- architecture (after user override to Clean Arch on both sides)
- error-handling library (same library, different phrasing)
- testing framework, lint command, typecheck command (semantically — runner differs)
- workspace mode, source root, default branch
- runtime URL (after user provided on Codex side)

Divergent:
- `PACKAGES_DETECTED` set (Codex wrong on 2 entries) + ordering
- `BUILD_COMMANDS` (Codex wrong: `build:origin`)
- `API_LAYERS` (Codex missing Apollo Client)
- Command runner (yarn vs npm run — Finding 26)
- JSON formatting (Finding 18, cosmetic)

**CLAUDE.md ↔ AGENTS.md diff**: 481 lines — not yet decomposed into semantic-vs-formatting breakdown. Open for R3.

## Run 2 — Finding 13 reframe (post-verification)

**Date**: 2026-04-24 (post-R2, pre-R3)
**Source**: user verification of `packages/pkg-test/package.json` existence in CSE source. File does NOT exist. This inverts Finding 13's original framing.

**Original framing (R1 and early R2)**: "Claude excludes `scripts/` (correct); Codex includes `scripts/` (wrong). Codex off-by-one."

**Corrected framing**: BOTH runtimes err on `PACKAGES_DETECTED` — in opposite directions. The coincidence that both totaled 26 hid that they have different 26-member sets.

- **Claude**: 25 workspace members + 1 **hallucinated entry** (`packages/pkg-test` — directory matches the `packages/*` glob but has NO `package.json`). Treated glob-match alone as sufficient for inclusion.
- **Codex**: 25 workspace members + 1 **over-included utility** (`scripts/` — has `package.json` but NOT declared in `package.json`'s `workspaces: ["packages/*", "apps/*"]`). Treated manifest-presence alone as sufficient.
- **Correct answer**: 25 members total (1 root `.` + 1 `apps/app-web` + 23 `packages/` workspace members with manifests).

Both runtimes failed to apply the conjunction: workspace-member membership requires (a) workspace-declaration match AND (b) manifest file present. Each interpreted Rule 5 as a single-sided test.

**Codex self-confirmed** (via post-R2 interrogation): *"packages/pkg-test matches the packages/* glob, but it has no package.json, so it is not a valid workspace package in the practical Yarn/Lerna sense. Its omission from PACKAGES_DETECTED is consistent with the current Phase 1 definition."* Codex's exclusion was actually correct; its `scripts/` inclusion was the only error on Codex side.

**Claude self-report**: not obtained yet. Claude's hallucination of `pkg-test` has no self-diagnosis on record. Candidate questions for future Claude interrogation: "What signal told you `packages/pkg-test/` was a workspace package despite no manifest?"

**Fix landed**: `ec76f91` (Rule 5 (a) AND (b) conjunction) + `c6ceaa5` (workspace-root exception + related tightenings).

**R3 verification**:
- Both runtimes emit exactly **25 entries** in `packages[]` (not 26 on either side)
- Neither side includes `packages/pkg-test` (glob-match without manifest → skip)
- Neither side includes `scripts/` in `packages[]` — it moves to `optional.utility_manifests[]` (manifest without workspace declaration)
- Root `.` retained in `packages[]` via workspace-root exception

**Why this matters for scoring**: "both 26" in R2 project-config.json diff looked like numeric parity. It wasn't — the two 26-member sets differed by 2 entries. R3's 25-member emits on both sides will be real parity if they also match member-for-member.

---

## Run 2 — Next fix batch (priority ordered)

1. **Finding 23** (HIGH, blocker) — Detection Report HALT language + visual emit markers + Phase 2 preflight. Highest leverage: closes Findings 13, 14, 15 build-side, 16 structurally; unblocks Findings 22, 26 which depend on it.
2. **Finding 26** (MEDIUM) — Command-runner selection tie-in to Detection Report. Closes BUILD / TYPE_CHECK / LINT command parity.
3. **Finding 22** (HIGH) — Phase 1 ↔ Phase 2 field linkage in questions.md. Closes Codex runtime_url blank. Depends on Finding 23.
4. **Finding 21** (MEDIUM) — architecture enum: add `clean`, allow compound labels. Closes Findings 6 and native Clean Arch detection.
5. **Finding 19** (MEDIUM) — Q0 scaffold-default blocklist + fallback hierarchy.
6. **Finding 20** (MEDIUM) — `{{ask}}` wrap for canonical-enum questions (Option A).
7. **Finding 25** (MEDIUM) — prohibit shell+language-runtime execution in detection.

Findings 1, 5, 11, 17, 18, 24 deferred to a later run — cosmetic or low-impact.

**Expected effort**: Finding 23 is ~50 lines of spec edit. Findings 26, 22, 21 each ~20–30 lines. Total next batch: ~150 lines, one commit cycle. Then Run 3.

---

## Run 3 — 2026-04-24

**Forge commit at run start**: `201b851` (spec substantively at `c6ceaa5`). Pre-R3 spec changes landed between R2 and R3:
- `d038c24` Finding 23 — Detection Report as handoff (causal framing + visual markers + Phase 2 preflight)
- `a195bba` Finding 26 — runner prefix sourced from Report
- `d1bcef8` Finding 22 — Q11 URL reads Report first
- `ab9b9e4` Finding 25 refined — detection-as-script framing
- `ec76f91` Rule 5 (a) AND (b) workspace-member conjunction
- `c6ceaa5` Rule 4 root-isolation + Rule 5 root-exception + Rule 9 README scope
- `201b851` Finding 13 reframe (pkg-test hallucination, both-wrong)

**Test infrastructure**:
- `testParity/` on branch `claude-parity-run3` — Claude side, reset to pre-install `64bb325`, reinstalled with current spec
- `testParity-codex/` on branch `codex-parity-run3` — Codex side, same
- Source (`db-cse-ui-strata/`) pinned to `9354389c6` — matches R1/R2
- Model: gpt-5.4 on both sides (held constant to isolate spec-variable from model-upgrade variable)

**Scope**: setup-wizard phase only. Same answer sheet as R1/R2. Post-R3 interviews conducted against both runtimes' wizard-completion session for self-report diagnostics.

### R3 Headline results

1. **Finding 23 closed ASYMMETRICALLY** — Claude emitted the fenced YAML Detection Report as specified. Codex still skipped it. Spec text fixes moved Claude to compliance; did NOT move Codex.
2. **Finding 22 closed on BOTH sides** — Codex now reads `vite.config.ts` and pre-fills the correct URL at Q11, matching Claude.
3. **Finding 13 closed on BOTH sides** — Rule 5 (a) AND (b) conjunction held. Both runtimes emit 25 workspace members with identical sorted list.
4. **6 findings closed total** (10, 13, 19, 20, 22, 23-on-Claude-only).
5. **1 new HIGH finding surfaced** — Finding 27 (multi-stack mis-detection on Codex).
6. **4 additional spec bugs uncovered via Claude's self-report** — Findings 28–31.
7. **Path B validated by Codex's direct endorsement** — "Yes, a Python-composed approach would likely work better."

### R3 Findings

Continue numbering from Run 2 (ended at Finding 26).

---

### Finding 27 — NEW IN R3 — HIGH — Codex treats file extensions as separate languages without framework-convention understanding

**Severity**: HIGH — cascades through Q4–Q7 as spurious multi-stack meta-questions and pollutes `LANGUAGES` / `FRAMEWORKS` arrays in `project-config.json`.

**Observed (R3)**:

Codex's Q3 detected 3 language stacks for the CSE project:
1. TypeScript (~1908 files) with Vue 3 / Vite
2. Vue (~470 files) with Vue 3 / Vite
3. JavaScript (~103 files) with Lerna workspace scripts

Claude's Q3 correctly detected 1 stack: TypeScript + Vue 3. Claude collapsed `.vue` files into the TypeScript stack (SFCs with `<script lang="ts">` contain TypeScript), and treated `.js` files as tooling scripts, not a separate app stack.

**Cascade effect on Codex**:
- Q4 architecture: "Does the same pattern apply across all 3 stacks?" (spurious meta-question not in spec)
- Q5 error handling: same "across all 3 stacks" meta-branch
- Q6 API layer: same
- Q7 testing: same
- Phase 5 summary: `Languages: TypeScript, Vue, JavaScript` / `Frameworks: Vue 3, Vite, Lerna Workspaces` — where `Lerna` is a monorepo coordinator (not a framework) and `Vue` isn't a language separate from TypeScript.

**Root cause — confirmed via both runtime interviews**:

- **Codex's self-report**: *"My effective algorithm: Detect manifests → count source files by extension → map extensions directly to language buckets → order by file count. The failure is at step 3. I treated .vue as its own 'language-ish' bucket instead of a framework-owned container format, and I treated .js tooling files as evidence of a third stack instead of infrastructure."*
- **Claude's self-report** (contrast): *"Framework-convention knowledge, not a spec rule. There's no rule I can cite that says 'collapse .vue into the language of the embedded script'. My reasoning: .vue / .svelte / .astro are Single File Component containers — the language is whatever's inside `<script lang=\"...\">`."*

Both runtimes confirm: the installed `detect.md` STEP 3 "Languages and runtimes" bullet maps `.ts/.tsx → TypeScript` etc. with "etc." doing all the work. No SFC-container collapsing rule. No tooling-script exclusion rule. No coordinator-exclusion rule for FRAMEWORKS[].

**Proposed fix — merged text from both runtime interview answers**:

Add to `detect.md` STEP 3 "Aggregated categories" before `LANGUAGES` / `FRAMEWORKS` emission:

```
**SFC-container and tooling-stack collapsing** — before emitting LANGUAGES[]:

1. SFC-container collapse: `.vue`, `.svelte`, `.astro` files are NOT separate
   languages. Count each file under the embedded script language. Sampling:
   read up to 5 files per package for `<script lang="...">` directives.
   lang="ts" → TypeScript; lang="js" or no lang → JavaScript; sample is
   conclusive if ≥4 of 5 agree. If inconclusive, fall back to package's
   typescript devDep + sibling tsconfig.json (both present → TypeScript).
   Vue/Svelte/Astro appear in FRAMEWORKS, never in LANGUAGES.

2. React-family extension collapse: `.tsx` → TypeScript, `.jsx` → JavaScript.
   React is a framework, not a language.

3. Tooling-script exclusion: `.js` / `.mjs` / `.cjs` files at the workspace
   root or under a `scripts/` directory, in a project whose package manifest
   declares TypeScript, are tooling (build helpers, codegen, env setup) — not
   a separate application stack. Exclude from LANGUAGES aggregation. Note
   them in `optional.tooling_scripts[]` in the Detection Report.

4. Monorepo coordinator exclusion: monorepo coordinators (Lerna, Nx,
   Turborepo, pnpm-workspaces, Cargo-workspace, Go-workspace) can populate
   `monorepo_tool` but MUST NOT populate FRAMEWORKS[].

5. A new language stack is emitted only when that language represents a
   substantive application or library surface in one or more detected
   packages — not incidental tooling.
```

**Expected R4 outcome**: Codex emits `LANGUAGES: [TypeScript]`, `FRAMEWORKS: [Vue 3]`, `monorepo_tool: Lerna`. Matches Claude. No spurious "across all stacks" meta-questions at Q4/Q5/Q6/Q7.

---

### Finding 28 — NEW IN R3 (surfaced via Claude interview) — MEDIUM — `PACKAGE_STACKS` table needs monorepo-scale collapse rule

**Severity**: MEDIUM — user-facing CLAUDE.md / AGENTS.md becomes dominated by ~46 near-identical rows across two tables for a 25-package monorepo with uniform library stack. Readability degraded; drift surface increased.

**Observed (Claude Q4 friction point)**:

> *"populate.md:362-384 renders one row per package, two tables (conventions + tools), no collapse option. For CSE UI: 23 of the 25 packages have identical values in every non-path column. That's ~46 near-identical rows across two tables, dominating CLAUDE.md. The monorepo-scale hint exists for {{PROJECT_STRUCTURE}} ('6+ packages → collapse shared libraries to one line each') at populate.md:172 but doesn't carry over to {{PACKAGE_STACKS_SECTION}}."*

**Proposed fix**: add symmetric collapse rule in `populate.md` §5.1 `{{PACKAGE_STACKS_SECTION}}`:

> "When `len(PACKAGES_DETECTED) ≥ 6` AND `≥ 80%` of packages share identical non-path column values (language, framework, architecture, error-handling, API, testing, build tool, build command, type-check command, lint command), emit a single 'Defaults for all other library packages' row capturing the shared values, followed by one row per deviator package. Apps (framework != null) are always emitted as individual rows regardless of shared-value count."

**Expected R4 outcome**: for CSE, CLAUDE.md shows 3 rows (1 app + 1 defaults + ~1 deviator like `package-starter`) instead of 25+.

---

### Finding 29 — NEW IN R3 (surfaced via Claude interview) — MEDIUM — `framework_hint: null` fallback chain wrong for library packages

**Severity**: MEDIUM — library-package records incorrectly inherit app-primary framework in per-package tables.

**Observed (Claude Q4 friction point)**:

> *"populate.md:337 fallback: framework = p.framework_hint if set; else FRAMEWORKS[i]; else '—'. For CSE UI, FRAMEWORKS[0] = 'Vue 3'. Literally applying the rule would write 'Vue 3' into every pkg-cse-* library row — but those packages are plain TypeScript libraries consumed by the Vue app; they aren't Vue apps themselves. I wrote '—' for all of them, deviating from the spec."*

**Root cause**: the fallback chain assumes package without explicit framework inherits primary. But `framework_hint: null` semantically means "this package has no app-level framework" — not "fall back to project primary."

**Proposed fix**: in `populate.md:337` fallback chain:

> "For per-package `framework`: use `p.framework_hint` if non-null. If `p.framework_hint == null`, emit `'—'` — do NOT fall back to `FRAMEWORKS[i]`. Library packages never inherit the app's framework by default. Only apps with explicit framework detection show a framework label."

**Expected R4 outcome**: library packages (pkg-cse-*) show `—` for framework. Only `apps/app-web` shows `Vue 3`.

---

### Finding 30 — NEW IN R3 (surfaced via Claude interview) — MEDIUM — `type_check_command` needs `via-build` sentinel for library packages

**Severity**: MEDIUM — per-package type-check commands either use wrong scope (whole-monorepo) or fall through to "—" which hides that type-checking actually happens.

**Observed (Claude Q4 friction point)**:

> *"For every pkg-cse-* library, I wrote '—' under Type Check. The spec's fallback is TYPE_CHECK_COMMANDS[i], which for TypeScript points at the root `yarn check` — which runs every package's check (not that one package's). Running the whole-monorepo check as a per-package type-check command is wrong for scope-aware verification. The packages don't have their own check scripts — they rely on the vue-tsc/tsc pass inside their vite build."*

**Proposed fix**: add fourth sentinel value to per-package type_check_command semantics:

> "Per-package `type_check_command` sentinel values:
> - **manifest command** (e.g., `yarn workspace <name> typecheck`) — package has its own type-check script
> - **`'via-build'`** — package's type-checking happens during its build step; the build command is the recovery path. Emit `via-build (run: <build_command>)` in the table.
> - **`'—'`** — package has no type-checking (e.g., pure data/config).
>
> Do NOT fall back to stack-level `TYPE_CHECK_COMMANDS[0]` (whole-monorepo check) as a per-package command — wrong scope."

**Expected R4 outcome**: library packages show `via-build (run: yarn workspace <name> build)` where applicable. Downstream `/execute-task` verification uses the correct per-package command.

---

### Finding 31 — NEW IN R3 (surfaced via Claude interview) — LOW — Template duplication between `CLAUDE.md` prose and `project-config.json` JSON keys

**Severity**: LOW (functional, but drift risk).

**Observed (Claude Q4 friction point)**:

> *"Same five-bullet text in two places — one with real newlines, one with \\n escapes. Same for AGENT_LIST ({{AGENT_LIST}} in CLAUDE.md and AGENT_LIST key in project-config.json). Drift risk: if a later command edits only one, they diverge."*

**Affected placeholders**: `{{COMMIT_ATTRIBUTION}}`, `{{AGENT_LIST}}`.

**Proposed fix**: declare `project-config.json` as canonical source; `CLAUDE.md` / `AGENTS.md` render the prose form at read-time via template-include. Alternatively, if template-include is infrastructure cost, explicitly document duplication with rule: *"When these fields are updated, both copies MUST be updated in the same operation. `project-config.json` is authoritative on conflict."*

Defer unless a follow-up command surfaces drift.

---

### Finding 23 sub-findings — surfaced via Claude interview

Claude emitted the YAML Report but flagged two sub-issues worth spec-clarifying:

**Finding 23A — HTML comment marker semantics ambiguous**

Claude interpreted `<!-- >>> EMIT THIS YAML BLOCK TO USER — VERBATIM — BEFORE PHASE 2 <<< -->` and `<!-- >>> END OF REQUIRED EMIT <<< -->` as template-authoring meta-prose (similar to authoring blockquotes in `populate.md` §5.7 that get stripped from `constitution.md`). So Claude emitted the YAML inside the markers but NOT the markers themselves.

**Ambiguity**: is the intent (a) markers are authoring anchors, strip them from emit; OR (b) markers are parser anchors, keep them in emit so a downstream tool can find the YAML block?

**Proposed fix**: pick one interpretation and state explicitly in `detect.md`:
- **Option A (authoring)**: "The `<!-- >>> EMIT <<< -->` markers are authoring anchors for spec readers. Do NOT emit them to the user — emit only the fenced YAML code block between them."
- **Option B (parser)**: "The `<!-- >>> EMIT <<< -->` markers are parser anchors. Emit them verbatim as HTML comments around the YAML fence so downstream tools can locate the block."

**Recommendation**: Option A. The YAML fence itself (```yaml ... ```) is already a parser anchor.

**Finding 23B — `packages[]` array abbreviation in emit**

Claude abbreviated the `packages[]` array in the YAML: listed first 3 entries fully, then `# ... additional 22 packages follow the same pattern` + name-only list. Judgment call for user-facing readability, but a machine reader parsing the YAML to populate `project-config.json.PACKAGE_STACKS` would get truncated data.

**Proposed fix**: add explicit rule to `detect.md` Detection Report Rule 4 or as a new rule:

> "**No abbreviation**: the `packages[]` array in the emitted Report MUST contain one entry per workspace member verbatim — no `# ...` stand-ins, no 'similar to above' shortcuts — even for large monorepos. The Report is consumed by `populate.md` §5.5 as the source of truth for `project-config.json.PACKAGE_STACKS`; abbreviation breaks that handoff."

---

### Finding 21 refinement (after Claude interview)

Claude's self-report distinguishes two components of the Finding 21 fix:

**Component 1** (enum gap): `detect.md:300` enum list lacks `clean`. This is a spec gap confirmed.

**Component 2** (Q4 cue gap): Even with enum fixed, Claude reports it would still default to `hexagonal` because of "availability bias in TypeScript ecosystem prose" unless Q4's option text explicitly cues the distinguishing signals.

Claude's specific observation:

> *"I was pattern-matching on the shape (three layers + ports-and-adapters flavor) rather than the specifier signal (the cases/ subfolder, which is the Clean-specific artifact). [...] What I wouldn't want is for the spec to just add clean to the enum without language cueing the distinction; I'd still default to hexagonal by the availability bias above."*

**Proposed fix — two parts**:

1. Add `clean` to `detect.md:300` enum: `layered | feature-modular | monorepo | feature-modular-monorepo | clean | clean-feature-modular-monorepo | hexagonal | mvc | bloc | flat | other`.

2. Add specifier-signal cues to Q4's option prose in `questions.md`:

   > "**Clean Architecture** signals: `domain/cases/` or `use-cases/` subfolder within each feature module; repository pattern with interface-in-domain + implementation-in-data; dependency direction strictly inward (domain imports from nothing; data imports from domain; presentation imports from domain + data adapters). The `cases/` subfolder is the clearest Clean-specific artifact — distinguishes Clean from hexagonal even when both have three-layer structure."

**Expected R4 outcome**: Claude offers `Clean Architecture` as the Recommended option when `domain/cases/` is detected. Codex emits `clean` or `clean-feature-modular-monorepo` in Report enum. Both converge without user override.

---

## R3 — Previous-finding resolution scoring

| Finding | R2 status | R3 status | Mechanism |
|---|---|---|---|
| 2 (git -C) | ✅ Closed | ✅ Closed (held) | Rule 3 template |
| 4 ({{ask}} no-batching) | ✅ Closed | ✅ Closed (held) | One turn per ask |
| 8 (purify-ts) | ✅ Closed | ✅ Closed (held) | Dep+usage rule |
| 9 (Q11 option reshape) | ✅ Closed (side-effect) | ✅ Closed (held) | {{ask}} rule side-effect |
| 10 (Husky miss, Codex) | ❌ Open | ✅ **Closed** | Phase 4 citations now include `.husky/pre-commit` |
| 12 (Codex summary abbrev) | ✅ Closed | ✅ Closed (held) | Unchanged |
| 13 (packages set) | ❌ Open | ✅ **Closed both sides** | Rule 5 (a) AND (b) — identical 25-entry sorted list |
| 14 (per-package commands) | ❌ Open | — Can't fully score without diff content | Need PACKAGE_STACKS inspection |
| 15 build (Codex build:origin) | ❌ Open | — Need diff content | Diff is 656 lines; formatting dominates |
| 15 lint | ✅ Partially closed (R2) | ✅ Closed (held) | Evidence rule |
| 16 (ordering) | ❌ Open | ❌ Still open (cosmetic) | Not prioritized |
| 17 (free-text fields) | ❌ Open | — Not decomposed from CLAUDE.md diff | Defer |
| 18 (JSON formatting) | ❌ Open | ❌ Still open | Cosmetic; 656-line diff dominated by whitespace |
| 19 (Q0 scaffold default) | ❌ Open | ✅ **Closed** | Both runtimes surface README `CSE UI` over manifest `root` |
| 20 (Options collapse, Codex) | ❌ Open | ✅ **Closed (with Codex caveat)** | Codex presents canonical enums at Q2/Q6/Q7/Q8/Q9/Q11; Codex self-reports partial stability |
| 21 (architecture enum) | ❌ Open | ❌ Still open | Needs enum + Q4 prose cue (refined per Claude interview) |
| 22 (Q11 URL) | Claude ✅ / Codex ❌ | ✅ **Closed both sides** | Codex now reads vite.config.ts and pre-fills URL |
| 23 (YAML emit) | ❌ Open | **Claude ✅ / Codex ❌** | Asymmetric: Claude emitted correctly; Codex skipped again per self-report |
| 24 (README freshness) | ❌ Open | ❌ Still open (migration-engineer false-positive persists) | Defer |
| 25 (script detection) | Framing refined R2 | — No explicit node one-liner observed in R3 paste | Inconclusive; defer |
| 26 (runner prefix) | ❌ Open | — Need diff content | Depends on Finding 23 closure |

## R3 — Closures

- ✅ **Finding 10** — Codex Husky miss (devops-engineer rationale now cites `.husky/pre-commit`)
- ✅ **Finding 13** — packages set divergence (both 25, identical sorted list; Rule 5 (a) AND (b) held)
- ✅ **Finding 19** — Q0 scaffold default (both surface README `CSE UI` over manifest `root`)
- ✅ **Finding 20** — Codex Options collapse (canonical enums now presented at Q2/Q6/Q7/Q8/Q9/Q11)
- ✅ **Finding 22** — Q11 URL (both runtimes pre-fill from `vite.config.ts`)
- ✅ **Finding 23 (Claude only)** — YAML Detection Report emitted correctly on Claude side

## R3 — Still open from Run 1 and Run 2

- ❌ **Finding 23 (Codex)** — Codex still skips YAML emit despite revised spec. Codex self-report: *"my execution policy still prioritized conversational progress over emitting the structured handoff artifact. [...] current textual reinforcement is not sufficient for me."* **Path A ceiling reached for this concern on Codex.**
- ❌ Finding 21 — architecture enum + Q4 cue (fix drafted, not landed)
- ❌ Finding 18 — JSON formatting (cosmetic)
- ❌ Finding 24 — README freshness (migration-engineer false-positive persists)
- Findings 14, 15-build, 26 — need project-config.json content diff to score definitively

## R3 — New findings

- **Finding 27** — multi-stack mis-detection (Codex); framework-collapsing rule drafted, endorsed by both runtimes
- **Finding 28** — PACKAGE_STACKS monorepo-scale collapse rule missing (surfaced by Claude)
- **Finding 29** — framework_hint null fallback chain wrong for library packages (surfaced by Claude)
- **Finding 30** — type_check_command needs via-build sentinel (surfaced by Claude)
- **Finding 31** — CLAUDE.md / project-config.json template duplication (surfaced by Claude)
- **Finding 23A** — HTML comment marker semantics ambiguous (sub-finding from Claude Q2)
- **Finding 23B** — packages[] abbreviation in emit (sub-finding from Claude Q2)

## R3 — Parity verdict

**`project-config.json` diff**: 656 lines (R2 was 659 — essentially unchanged in volume; semantic content has shifted).

**Converged on R3**:
- Description, project type, workspace mode, source root, default branch
- Architecture (both users overrode to Clean Architecture, feature-modular monorepo — spec still missing `clean` in enum)
- Error-handling library (purify-ts)
- Testing framework, lint command
- **Packages count and sorted set** (25 entries, identical members — R3 cleanup)
- **Q11 URL** (R3 cleanup)

**Divergent**:
- **Languages / Frameworks arrays** — Codex 3-entry bloat per Finding 27 (Codex: TypeScript+Vue+JavaScript + Vue 3+Vite+Lerna Workspaces; Claude: TypeScript + Vue 3). Biggest R3 divergence.
- **Architecture label** on Claude side — offered `hexagonal-style` not `clean` (Finding 21 component 2)
- **JSON formatting** — Finding 18 unchanged
- **BUILD_COMMANDS** runner prefix — likely still diverges (need diff content)

**Semantic parity**: ~80% on the fields we can verify. Would rise to ~90%+ with Finding 27 + Finding 21 fixes landed.

## R3 — Path B justification

Codex's interview answer directly endorses Path B for Detection Report composition:

> *"Yes, a Python-composed approach would likely work better. [...] structured field-by-field prompting is more reliable than 'emit a whole YAML report now.' If the helper constrained me to fill explicit fields one at a time, I would expect lower drift at the value level too."*

Codex's preferred interface, ranked:
1. Typed field-by-field helper with validation (enums, required null-reasons, package-record shapes; rejects invalid and reasks)
2. One structured object with schema validation
3. Field-by-field for high-risk sections only: `languages`, `frameworks`, `packages[]`, per-package commands, `runtime_url`, `architecture_shape` — "probably the best cost/benefit"

**Decision**: Path B for Detection Report structural composition on Codex is evidence-justified. Path A continues for rules, vocabularies, flow-control, UX guidance — where R3 data shows it's working.

## R3 — Next fix batch (priority ordered)

**High — land pre-R4 (this session)**:
1. **Finding 27** — framework-convention collapsing rule in `detect.md` STEP 3 (text from merged interview answers)
2. **Finding 21** — add `clean` to enum + Q4 prose cue for Clean vs hexagonal distinction
3. **Finding 23A** — clarify HTML marker semantics (recommend Option A: authoring-only, strip from emit)
4. **Finding 23B** — explicit "no abbreviation" rule for `packages[]` in emit
5. **Finding 29** — framework_hint null fallback fix in `populate.md`

**Medium — also land pre-R4**:
6. **Finding 28** — PACKAGE_STACKS monorepo-scale collapse rule in `populate.md`
7. **Finding 30** — via-build sentinel for per-package type_check_command

**Strategic — post-R4 if Finding 23 still open on Codex**:
8. **Path B scaffolding** — Python helper in `scripts/lib/detect_report.py` using Codex's preferred field-by-field interface

**Deferred**:
9. Finding 31 — template duplication (structural; low priority)
10. Finding 24 — README freshness (low priority)

---

## How to run this test again

```bash
# 1. Reset worktrees to post-install baseline
cd /Users/mykolakudlyk/Projects/testParity
git reset --hard <post-install-commit>   # or re-run install.sh after rm -rf

cd /Users/mykolakudlyk/Projects/testParity-codex
git reset --hard <post-install-commit>

# 2. Fix whatever findings you're trying to validate (edit src/ files in ai-dev-team-forge)

# 3. Re-run install in both worktrees (picks up spec changes)

# 4. Run /setup-wizard (Claude) and $setup-wizard (Codex) in parallel
#    Use the answer sheet from the chat / PLAN.md

# 5. Diff artifacts at each phase checkpoint, append new findings here
```

Future run additions go below as `## Run 2 — YYYY-MM-DD`, etc.
