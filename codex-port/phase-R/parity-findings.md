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
**Commit**: _pending_
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
