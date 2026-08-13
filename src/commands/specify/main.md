---
name: specify
description: Author a 9-section feature spec under specs/NNN-name/spec.md with EARS-validated AC, coverage-rule enforcement, and a manual-next-step /devforge:plan block.
argument-hint: "<feature description>"
---

# /devforge:specify — Feature Specification

`/devforge:specify` is repeatable per feature. It reads the seven mandatory Phase 1 input sources, enumerates structured findings into the conversation, surfaces every decision point across seven categories, classifies the spec into one of five types, then renders a deterministic 9-section spec to `specs/NNN-<feature-name>/spec.md` via `.devforge/lib/specify_helper` setters. State + render shape are owned by the helper; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) has completed before any spec work fires. Phase 0.4's gate then RESOLVES the feature directory `/devforge:research` or `/devforge:discover` already allocated at intake — `/devforge:specify` writes `spec.md` into that existing directory instead of allocating a new one.

Usage: `/devforge:specify "<feature description>"` (e.g. `/devforge:specify "migrate the monorepo from lerna to pnpm workspaces"` or `/devforge:specify "add scheduled export jobs for tenant data"`). If `$ARGUMENTS` is empty, ask the user to describe the feature before calling any helper subcommand.

## Outputs of this phase

- `.devforge/specify-state.json` — canonical SpecDoc state (Phase 0–5 buckets). Owned + shaped by the helper; mutated only via setter subcommands.
- `specs/NNN-<feature-name>/spec.md` — rendered 9-section spec markdown, written into the feature directory resolved in Phase 0.4 (the one `/devforge:research` or `/devforge:discover` allocated at intake). Helper's `render` writes to stdout; orchestrator saves the bytes verbatim under `<install_root>/specs/`.
- Branch `spec/NNN-<feature-name>` — FALLBACK only. `/devforge:research` and `/devforge:discover` create this branch at intake, so `/devforge:specify` normally creates nothing; Step 4.1 calls `create-branch` only when Phase 0.2 deferred creation, and only its default-branch arm emits a checkout.
- `specs/NNN-<feature-name>/handoff.json` — specify→plan structured handoff, written by `finalize-handoff` on the approve branch of Phase 5 (sibling to `spec.md`). Carries `spec_seeds` (structured spec sections) + upstream research/discover provenance; spec status stays `Draft` (`/devforge:plan` owns the flip). `/devforge:plan` auto-discovers this sibling handoff on its first run and reads the upstream plan-seeds; the user still invokes `/devforge:plan` manually (no auto-dispatch from `/devforge:specify`).
- `specs/NNN-<feature-name>/design-anchor.json` — structured, immutable design-intent record (`kind` / `file` / `selectors` plus a `source_hash` baseline), written by `write-design-anchor` on the approve branch of Phase 5 (Step 5.4). Composed from the design anchor carried across the `/devforge:research` / `/devforge:discover` intake handoff, or — when intake captured none — from the `**Design source**:` declaration as a backstop. `/devforge:specify` is the gate that guarantees this record exists before `/devforge:plan`.

On approve, Step 5.4 `[WIP]`-commits the spec into the install repo via `.devforge/lib/artifact_helper commit-artifacts` (install-repo-only, fail-soft) so the work is git-safe the moment it is written; the commit folds into `/devforge:finalize`'s squash. `spec.md` and `design-anchor.json` are always committed on approve (both exist by the time Step 5.4 reaches either commit-artifacts call); `handoff.json` is committed additionally when `finalize-handoff` succeeds. `.devforge/specify-state.json` is NOT committed (it is `.devforge/`-scoped runtime state).

The LLM does NOT edit `.devforge/specify-state.json` or the rendered `spec.md` via Write or Edit at any point. The helper's setters + `render` are the only writers; this preserves the helper-owns-shape invariant.

## Phase 0 — Preflight + branch detection + session-state reset + feature-dir resolution

Four preflight steps run in order. All must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/specify_helper preflight --install-root .
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/devforge:init-forge`)
- `docs/architecture.md` (produced by `/devforge:generate-docs`)
- `.devforge/configure.yaml` (produced by `/devforge:configure`)
- `constitution.md` (produced by `/devforge:constitute`)

Exit 0 → all present + non-empty + populate-guard absent; proceed. Exit 2 → at least one missing/empty OR `constitution.md` still contains the populate-guard literal `_Run /devforge:constitute to populate_` (the helper also matches the legacy un-namespaced `_Run /constitute to populate_` that an older install may still carry). On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/devforge:specify`.

When the populate-guard literal is the only failure, the helper's stderr already cites `/devforge:constitute` as the producer; the v3-verbatim user-facing wording for that condition is: **⛔ constitution.md has not been populated yet. Run `/devforge:constitute` before using `/devforge:specify`.** Echo that line as part of the verbatim stderr block so the user sees the explicit instruction.

### Phase 0.2 — Git state + branch detection

Verify this is a git repository:

```bash
git rev-parse --is-inside-work-tree
```

If the command fails: end the turn and tell the user **"This directory is not a git repository. Initialize with `git init` and make an initial commit first."** No further phases run.

Detect current branch:

```bash
git branch --show-current
```

Detect the repository's default branch, in this order; stop at the first that succeeds:

1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` — parse the branch name from the output.
2. `git show-ref --verify --quiet refs/heads/main`.
3. `git show-ref --verify --quiet refs/heads/master`.
4. None of the above resolved → ask the user via AskUserQuestion: `"What's the default branch for this repo?"` with options `["main", "master"]`. Single-line question text. End the turn. The user's reply opens the next turn; treat it as the default-branch value.

Branch decision. `/devforge:research` and `/devforge:discover` create the `spec/NNN-<slug>` branch themselves at intake when the run is on the default branch, so the first arm below is the normal case and `/devforge:specify` creates no branch. The other two arms are the fallback states: intake skipped the checkout (not a git repository, unresolvable default branch, or intake itself ran on a non-default branch), or the user switched branches since.

- **Already on a `spec/*` branch:** keep the branch. Proceed to Phase 0.3. Branch creation in Step 4.1 is skipped.
- **On the default branch:** prepare for the fallback spec-branch creation. Do NOT derive a slug from `$ARGUMENTS` here — `create-branch` composes the branch name from the `spec_number` + `feature_slug` in state, which Step 4.1 sets, so the branch name matches the directory `spec.md` is written into. Branch creation is deferred to Step 4.1 for that reason. Phases 1–3 are read-only research and safe to run on the default branch.
- **On any other branch** (not default, not `spec/*`): ask the user via AskUserQuestion: `"You're on <branch>. Create a spec branch from here, switch to <default-branch> first, or stay on <branch>?"` with options `["from-here", "switch-to-default", "stay"]`. Single-line question text. End the turn. The user's reply opens the next turn. On `from-here`: keep current branch as base; defer branch creation to Step 4.1. On `switch-to-default`: run `git checkout <default-branch>` in the next turn before continuing. On `stay`: skip branch creation entirely (Step 4.1 will not call `create-branch`).

### Phase 0.3 — Session-state reset

Reset `.devforge/session-state.md` to the empty placeholder so the next `/devforge:implement` bootstraps from a clean snapshot. A new spec means a new feature scope — previous session tracking is irrelevant.

```bash
mkdir -p .devforge && cat > .devforge/session-state.md <<'EOF'
<!-- This file is a fixed-size sliding window. Always fully overwritten, never appended. Max ~40 lines. -->
# Session State

No tasks executed yet. This file is updated automatically after each `/devforge:implement` run.
EOF
```

Then reset helper state for this run:

```bash
.devforge/lib/specify_helper reset-state
```

`reset-state` writes a fresh defaults JSON at `.devforge/specify-state.json`. Fresh-every-run: any prior state is overwritten. `/devforge:specify` does not resume mid-flight prior runs — every invocation starts clean.

### Phase 0.4 — Pending-feature-dir resolution

```bash
.devforge/lib/specify_helper find-handoffs --require
```

`/devforge:research` and `/devforge:discover` allocate the feature directory `specs/NNN-<slug>/` themselves at intake finalize and write their report + handoff inside it, so by the time `/devforge:specify` runs, the directory — its `NNN` and its slug — already exists. This step RESOLVES that directory; it never allocates one.

Helper makes one glob pass over `specs/*/research-handoff.json` AND `specs/*/discover-handoff.json` and lists only feature dirs that are **pending**. A feature dir is pending when its intake handoff is present AND either arm holds:

- **(a) `spec.md` is absent** — the feature has not been specified yet. This is the normal arm.
- **(b) `spec.md` exists AND a sibling `*-seed.json` in the same dir has `target_stage == "spec"`** — the re-entry arm: a `/devforge:grill` RE-ENTER-UPSTREAM or `/devforge:spec-check` REVISE-SPEC verdict is asking for this spec to be REVISED. Without this arm the gate would block every re-entry before Phase 0.5 could consume the seed. A corrupt seed file, or one targeting another stage, does not admit the dir.

Emits one summary line per hit to stdout (most recent first). Output format per line: `<mtime ISO> | <handoff_path> | kind=<research|discover> | <mode_or_verdict> | <truncated summary>`, with a sixth field ` | re-entry` appended when — and only when — arm (b) admitted the dir. For research handoffs `mode_or_verdict` is `mode=<mode>` (summary from `plan_seeds.recommended_approach_summary`); for discover handoffs it is `verdict=<verdict>` (summary from `plan_seeds.recommended_option_rationale`, falling back to `intent.feature_concept` when that rationale is empty). Summary truncated to 80 chars. Exit 0 when ≥1 pending feature dir is found; exit 2 with a BLOCKED message on zero hits — the gate is enforced via `--require`, and its stderr names both arms.

A `re-entry`-marked hit resolves to its feature dir exactly like an unmarked one — same pick flow, same import, same `spec.md` path. The only difference is that `spec.md` already exists there and this run REVISES it; Phase 0.5 governs how, from the seed sitting in that same dir.

mtime orders the hits and does nothing else: there is no age filter, so a feature dir whose intake ran weeks ago stays discoverable for as long as it is pending. Do NOT pass `--since` — the flag is deprecated and accepted-but-ignored (a malformed value still fails loudly, but a well-formed one filters nothing).

**This gate is mandatory, with no override.** A pending feature dir — arm (a) or arm (b) above — must exist before `/devforge:specify` proceeds. Arm (b) is not a loosening: it still requires an intake handoff, and it additionally requires a downstream check to have asked for the revision. The intake interrogation that validates the user's prompt lives in `/devforge:research` and `/devforge:discover`; allowing `/devforge:specify` to run cold would let a user skip straight past that gate, so the precondition is unbypassable — there is NO cold-spec escape hatch, even for a feature the user researched externally. The mitigation for the externally-researched case is PROPORTIONATE research, not a bypass: the user runs `/devforge:research "<topic>"` (or `/devforge:discover "<idea>"`), but the rubric scales DOWN to a fast pass that still runs the intake gate (the prompt echo-back included), so the prompt is validated at the boundary regardless. "Mandatory" therefore does not mean "heavyweight" — a two-sentence bug still goes through research, but research for it is a 30-second pass, not a full investigation. The gate accepts research OR discover so neither track is excluded (discover covers greenfield, where research's bug/enhancement framing does not fit).

**Scope of this gate (it applies ONLY to the spec pipeline).** The standalone `/devforge:audit` flow is separate from the spec pipeline and is NOT gated by this precondition; it exists precisely to bypass the heavy pipeline for small, one-off work.

On zero hits (exit 2): copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The stderr names the two locations it globbed, both pending arms, and the two recovery commands — `/devforge:research "<topic>"` for a bug or enhancement against existing code, `/devforge:discover "<idea>"` for a greenfield feature. The user runs one, then re-invokes `/devforge:specify`. Do NOT proceed to Phase 1 and do NOT offer a cold-start alternative — there is no override.

On one or more hits: count R research and D discover handoffs from the output lines (one feature dir contributes two lines when both lanes ran for it). AskUserQuestion: `"Found handoff(s) — R research, D discover. Pre-seed spec from one?"` (substitute actual counts for R and D) with options `["yes-most-recent", "pick-other", "cold"]`. Single-line question text. End the turn. The user's reply opens the next turn.

Every arm resolves a feature directory: it is the PARENT directory of the handoff path on the chosen stdout line. Hold it in working memory as the **resolved feature dir** — Phase 1's §1.5/§1.6 corpus reads, Step 4.1's header assignment, and Step 4.11's spec write all use it, and `spec.md` is written into it in every arm (created on a first pass, overwritten on a `re-entry` revision) — except Step 4.1's genuine-fallback path, which allocates a fresh directory instead; see Step 4.1. Also carry whether the chosen line ended in ` | re-entry`, so Phase 0.5 knows to expect a seed in that dir. Intake always names the directory `<NNN>-<slug>`; the helper also lists any other `specs/` subdirectory that happens to carry an intake handoff, and Step 4.1's genuine-fallback path covers that shape.

- **`yes-most-recent`** → invoke `.devforge/lib/specify_helper import-handoff --handoff-path <newest path>` using the second field (the handoff path) from the first line of the `find-handoffs` stdout (most-recent-first ordering). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Continue to Phase 1. The resolved feature dir is that path's parent.
- **`pick-other`** → in the next user-facing message, print the full `find-handoffs` stdout as a fenced code block with a 1-based index prefix per line. Each line is prefixed with `[research]` or `[discover]` as the kind tag (derived from the `kind=<kind>` field in the output line); print each line's trailing ` | re-entry` marker unchanged where present, and state in one line of prose above the block that a `re-entry` line revises an already-specified feature. Ask the user `"Reply with the index of the handoff to import."` as plain prose. End the turn. The user's numeric reply opens the next turn; invoke `import-handoff --handoff-path <path at that index>`. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Continue to Phase 1. The resolved feature dir is the picked path's parent.
- **`cold`** → skip the import. `cold` means "do not pre-seed the spec from the handoff's CONTENT" — it does NOT mean "no feature dir" and it is NOT a bypass of the gate above, which has already passed. The resolved feature dir is the FIRST (most-recent) line's parent directory, the same one `yes-most-recent` would have imported from; there is no cold-pick-other arm. `spec.md` still lands in that directory, and Step 4.1 derives `spec_number` + `feature_slug` from its basename. Continue to Phase 1 with no pre-seed. One cost to weigh before picking `cold` on a `re-entry`-marked hit: skipping the import leaves the design anchor empty in state, so Step 5.4's `write-design-anchor` — which composes purely from state and overwrites unconditionally — replaces the feature's existing `design-anchor.json` with a selector-less anchor built from this run's `**Design source**:` answer; pick `yes-most-recent` or `pick-other` instead when the feature has a design anchor worth keeping.

On the two importing arms, `import-handoff` also seeds `spec_number` + `feature_slug` in state from the resolved feature dir's basename whenever that basename has the `<NNN>-<slug>` shape (always true for an intake-allocated directory), so Step 4.1 allocates no number; a basename without that shape leaves both fields unseeded for Step 4.1's genuine fallback. It dispatches on `handoff_kind` automatically; no separate subcommand is needed for research vs discover handoffs.

On `import-handoff` exit 2 (missing file / invalid JSON / schema validation failure / unknown kind): copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Do NOT proceed to Phase 1 — end the turn. The user fixes the upstream handoff and re-runs `/devforge:specify`.

On `import-handoff` exit 0 with a `warning:` line on stderr (prefixed `import-handoff: warning:`) (re-import would overwrite user-composed `state.overview` / `state.desired_behavior` / AC content): surface the stderr warning text to the user as plain prose alongside the verbatim stdout block, then continue to Phase 1. The helper has already overwritten pre-seeds; the warning is informational so the user knows downstream sections may need re-review at Phase 5 approval.

### Phase 0.5 — Re-entry from `/devforge:grill` or `/devforge:spec-check` (conditional — skip if no seed)

Before beginning the spec work, check for a re-entry seed. When Phase 0.4's chosen hit carried the ` | re-entry` marker, the seed that admitted it is in the resolved feature dir and this block WILL fire; when the hit was unmarked, it normally does not. Either way the check is the same and is run unconditionally: glob `specs/<resolved-feature-dir>/*-seed.json` — the feature dir resolved in Phase 0.4, and ONLY that dir. Do NOT glob `specs/*/` project-wide: another feature's stale spec-targeted seed would then bind this run to a directive that was never about this feature, and the same-dir scoping is exactly what Phase 0.4's arm (b) already keyed on. If any matched file has a `target_stage` equal to `"spec"` (this command's stage), you are re-entering this (upstream) spec stage because a DOWNSTREAM adversarial check found the flaw is rooted here; read the seed's `source` field to know which check fired: `/devforge:grill` (a RE-ENTER-UPSTREAM verdict on the plan's design) or `/devforge:spec-check` (a REVISE-SPEC verdict on the spec's AC logic). In either case a downstream adversarial check invalidated a conclusion of THIS spec stage, so the re-run must be DIRECTED and must not re-derive the invalidated conclusion. Read that seed and treat it as a binding directive for this run. Read it DIRECTLY: parse the matched file's flat JSON inline — do NOT call any `grill_helper` verb or (once it exists) `spec_check_helper` verb (the orchestrator reads the file itself, so this block stays valid even if `/devforge:grill` or `/devforge:spec-check` is ever removed). The seed carries these fields:

- `source` — which command emitted this seed (`grill` or `spec-check`); read it first and state up front which command's verdict you are re-entering from (`/devforge:grill` RE-ENTER-UPSTREAM, or `/devforge:spec-check` REVISE-SPEC).
- `feature` — the feature this seed was emitted for; read it from the seed and state it up front in your re-entry message (do NOT infer it from the file path).
- `prior_conclusion` — what the previous spec concluded; it was invalidated, so do NOT re-derive it.
- `invalidating_evidence` — how the downstream check proved it wrong, grounded in the plan / spec / code.
- `must_satisfy` — what this re-run must now additionally satisfy; address it explicitly.
- `carried_findings` — prior findings to carry forward; stay monotonic (never re-surface a finding a prior pass already disproved).

State up front in your first user-facing message that you are running in re-entry mode — naming the seed's `source` command (`/devforge:grill` or `/devforge:spec-check`) — for the named `feature`, and name how this run addresses `must_satisfy`. Then run Phases 1–5 normally, with the seed's directive constraining the spec.

A re-entry run REVISES an existing spec: the resolved feature dir already contains `spec.md`, and Step 4.11 overwrites it with the fresh render. That is the intended outcome — the superseded version stays recoverable from the per-step `[WIP]` commits, so nothing is lost. No phase treats an existing `spec.md` as an error, and no phase feeds it into the new render: the render is composed from `.devforge/specify-state.json`, which Phase 0.3 reset to defaults, so the revision is authored from the seed plus this run's Phase 1–3 inputs rather than edited in place. To carry forward material from the superseded spec, read it as a Phase 1 input (§1.7) so it lands in the Phase 1.5 findings like any other source.

When MORE THAN ONE file in that one directory matches `target_stage == "spec"` (e.g. a stale `spec-check-seed.json` left by an earlier REVISE-SPEC alongside a later `grill-seed.json` for the same feature, since this block does not delete a consumed seed), process ALL of them: narrate each seed's `source` up front and address every seed's `must_satisfy`, unioning their `carried_findings`. If only one can be fully addressed this run, name the others explicitly as still-pending in the re-entry message. Do not silently pick one.

This block only READS the seed's directive. It does not delete the seed or mutate its `cycle_count` — that lifecycle management, whatever form it takes, is the emitting command's responsibility, not this consumer's. That is a v1 simplification; do not add seed-deletion logic here.

When no `specs/<resolved-feature-dir>/*-seed.json` file matches `target_stage == "spec"` (the normal case — both `/devforge:grill` and `/devforge:spec-check` are opt-in, and no seed is ever produced unless a `/devforge:grill` run reaches a RE-ENTER-UPSTREAM verdict or a `/devforge:spec-check` run reaches a REVISE-SPEC verdict), this block is a no-op: proceed directly to Phase 1.

## Phase 1 — Input reads (7 sources)

Read the feature description from `$ARGUMENTS` and hold it in working memory as the **topic** used for filename-overlap matching against prior spec directories under `specs/` (§1.7). This feature's own intake reports (§1.5 / §1.6) are NOT topic-matched — they sit at fixed paths inside the feature dir resolved in Phase 0.4.

Before any analysis, read these inputs for context. **All bullets are required if the file/directory exists. Do not skip discretionarily — every applicable input must be read.**

For every file actually read, call:

```bash
.devforge/lib/specify_helper record-input-read --path "<relative path>"
```

The helper auto-tags `source_origin` from the path (`discover` / `research` / `prior_spec` / `context`); no content parsing. Under `specs/` the tag is decided by FILENAME, not by the prefix: `research-report.md` tags `research`, `discovery-report.md` tags `discover`, and every other `specs/` path tags `prior_spec`. Idempotent — re-recording the same path overwrites the prior entry.

### 1.1 `constitution.md` — project rules and patterns

Read the full file. Phase 0.1 already enforced the populate-guard check; the file is guaranteed populated at this point. Record:

```bash
.devforge/lib/specify_helper record-input-read --path "constitution.md"
```

### 1.2 `.devforge/memory.md` — past lessons and known pitfalls

If the file exists, read it. Record the slot either way — this call is unconditional, since Phase 1 finalize counts `.devforge/memory.md` among its four mandatory base reads whether or not the file is there:

```bash
.devforge/lib/specify_helper record-input-read --path ".devforge/memory.md"
```

For this one path the helper does more than store the string it was handed: it probes the file itself and records the state it observed — one of `absent` / `stub` / `populated`, stored under the key `memory_state`. No CLI flag carries that value; the caller cannot supply it. All three states pass Phase 1 finalize. `stub` is the ordinary reading on a fresh install, which ships that stub with nothing recorded in it yet, and `absent` is equally fine — neither is a fault to fix or report. A recorded state establishes only that the helper consulted the file: it is not evidence that the file held content, and not evidence that you read or absorbed anything in it. Reading the content for context when it is present stays your job, unchanged.

Branch on the recorded `memory_state` for what that content feeds:

- `absent` or `stub` → nothing has been recorded yet, so this source carries nothing forward. Say nothing to the user about memory, raise no warning, add no step; take §1.5's `mark-source-no-items-relevant` path for this source. A memory file that is missing, or still the stub the installer ships, is the correct state on a new project, not a fault to remedy.
- `populated` → pick out the entries naming a known pitfall in the area this feature touches — the topic this phase opened with, plus the packages and concerns §1.4 surfaced — and carry each one into §1.5 as its own `record-finding` bullet. Enumerating them there is the point: a pitfall that stays in working memory is one Phase 2 can silently design past, and Phase 4's acceptance criteria are written from the §1.5 findings, not from recall.

**Honesty bound.** A carried memory entry is an UNVERIFIED prior-session assertion, not a fact about the code as it stands: it is a pitfall to check for and a constraint to respect, never an acceptance criterion on its own and never grounds for a claim about current behavior. A past session wrote it, and the code it describes may have changed since — or the entry may have been wrong when it was written. Re-ground what it points at against the actual code (§1.4's docs reads and the codebase-memory-mcp graph) before any of it shapes an acceptance criterion.

### 1.3 `CLAUDE.md` — project structure and commands

Read the full file. Record:

```bash
.devforge/lib/specify_helper record-input-read --path "CLAUDE.md"
```

### 1.4 `docs/` tree — architecture + topic-relevant docs

Read in this order:

- `docs/architecture.md` — project-tier architecture patterns, layer boundaries, data flow.
- `docs/glossary.md` — term grounding.
- `docs/<source-root>/packages/**/*.md` and `docs/<source-root>/apps/**/*.md` — scan for files whose name or content matches the topic.
- Any other `.md` files under `docs/` whose name or content matches the topic.

Use the codebase-memory-mcp graph for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob` for source-code discovery (runtime hooks will block raw calls on first match). `get_architecture` pulls the rendered architecture md; `search_graph` with `label="File"` + `name_pattern=<regex on file_path>` locates candidate package roots (argument name is `name_pattern`, NOT `file_pattern`).

Record one `record-input-read` call per md file actually consumed, with the relative path.

### 1.5 `specs/<NNN>-<slug>/research-report.md` (if the file exists) — this feature's `/devforge:research` investigation report

The `/devforge:research` run that produced this feature's intake handoff wrote its report beside that handoff, inside the feature dir resolved in Phase 0.4 — so there is exactly one candidate, at a fixed path, and no topic-token scan applies. Read the file in full when it exists, then record it:

```bash
.devforge/lib/specify_helper record-input-read --path "specs/<NNN>-<slug>/research-report.md"
```

Auto-tagged `source_origin = "research"` (the helper dispatches on the `research-report.md` filename, not on the `specs/` prefix). No content parsing of `/devforge:research` output — the file is consumed as plain markdown into Phase 1.5 findings.

### 1.6 `specs/<NNN>-<slug>/discovery-report.md` (if the file exists) — this feature's `/devforge:discover` discovery report

Same shape as §1.5, at the sibling path in the same resolved feature dir. Read the file in full when it exists, then record it:

```bash
.devforge/lib/specify_helper record-input-read --path "specs/<NNN>-<slug>/discovery-report.md"
```

Auto-tagged `source_origin = "discover"`. A feature dir normally carries one lane's report; both files exist when both lanes ran for it. Read whichever of the two are present.

The literal `/devforge:specify "<distilled topic>"` line that may appear at the top of a `/devforge:discover` Next-Step block is the user's manual handoff text in the source doc — NOT an instruction to recurse. Treat it as plain prose; do not re-invoke `/devforge:specify` on it.

### 1.7 `specs/` (if directory exists) — prior spec directories on related topics

Enumerate via `ls specs/` and read the `spec.md` of any prior spec directory whose name has ≥1 topic-token overlap with the feature description. Record one `record-input-read --path "specs/<dir-name>/spec.md"` per file consumed. Auto-tagged `source_origin = "prior_spec"`.

On a re-entry run (Phase 0.5 fired), the resolved feature dir's own `spec.md` — the version this run supersedes — is read here too, under the same call and the same `prior_spec` tag. Read it so the material worth keeping survives into the Phase 1.5 findings; the seed's directive still governs what must change.

### Phase 1 finalize

After every read has been recorded:

```bash
.devforge/lib/specify_helper phase1-finalize
```

The helper gates Phase 1 → Phase 1.5: all four mandatory base reads (`constitution.md`, `.devforge/memory.md`, `CLAUDE.md`, `docs/architecture.md`) must be recorded, and the `.devforge/memory.md` record must additionally carry the state §1.2's probe observed. Exit 0 → advance. Exit 2 → stderr enumerates the shortfall: reads that were never recorded, or — with all four paths already present — a memory record carrying no probed state at all, which means a read was claimed that the probe never performed (a hand-edited state file, or one written before this check existed). The state's VALUE never gates: `absent` and `stub` pass exactly like `populated`, and only the absence of an observed state is rejected. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), perform the missing read(s) + `record-input-read` calls, then re-run `phase1-finalize`.

## Phase 1.5 — Findings enumeration (REQUIRED INTERMEDIATE OUTPUT)

**Before proceeding to Phase 2, produce a structured intermediate output enumerating what was found in each input.** This is a hard requirement. Output it to the conversation (not to a file) before any further analysis.

This intermediate output converts implicit recall into explicit enumeration. It prevents silent dropping of input content (the dominant variance source observed in parity tests of v1).

For every input source recorded in Phase 1, call `record-finding` once per task-relevant item:

```bash
.devforge/lib/specify_helper record-finding \
    --source-path "<path from Phase 1>" \
    --source-section "<heading or subheading>" \
    --content "<finding text>"
```

`--source-section` may be empty for short files. The helper auto-assigns a `finding_id` of the form `F-<source-slug>-<N>`. The `--landed-in` default is `unlanded`; Phase 4 setters mutate it via cross-references (do not pre-fill here).

**≥3 bullets per read source when content is task-relevant.** If a source was read but contains nothing task-relevant, call:

```bash
.devforge/lib/specify_helper mark-source-no-items-relevant --source-path "<path>"
```

This waives the ≥3-bullet rule for that source. A source not read at all is skipped entirely (no marker required).

After every read source is either populated with ≥3 findings or marked irrelevant, emit the findings section to the conversation:

```bash
.devforge/lib/specify_helper render-findings
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the enumerated findings; verbatim echo is mandatory so the user sees exactly what Phase 2 will reason against.

Then gate:

```bash
.devforge/lib/specify_helper findings-finalize
```

Helper runs `verify-findings` then stamps `findings_finalized=true`. Exit 0 → advance to Phase 2. Exit 2 → stderr enumerates the per-source shortfall (a read source has fewer than 3 findings AND no "no-items-relevant" marker). On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), record the missing findings (or the no-items-relevant marker) for the cited source, then re-run `findings-finalize`.

## Phase 2 — Decision-point coverage (7 categories)

Based on `$ARGUMENTS` + the Phase 1.5 findings, identify decision points and either ask clarifying questions (interactive mode) or apply named defaults (auto mode).

**Definition — "Decision Point"**: any choice whose outcome would change at least one entry in the eventual spec's:

- Acceptance Criteria list, OR
- Affected Areas table, OR
- Out-of-Scope list, OR
- Technical Constraints list, OR
- Risks table.

**Rule**: For every decision point with ≥2 valid implementations, generate a clarifying question. Do not skip a decision point because the model has a default preference — surface the choice to the user. The model's default is one valid answer; the user's input is required to commit to it.

### Categories to scan for decision points (cover each — none are optional)

1. **scope_boundaries** — does this affect related area X, related area Y, or only specific area Z?
2. **existing_behavior** — for each existing behavior in the affected area, must it be preserved, modified, or replaced?
3. **data_flow_state** — for each new piece of state or data, where does it come from?
4. **edge_cases** — what should happen for empty input, error condition, concurrent operations, etc.?
5. **ui_ux_details** — loading state, error message, confirmation, accessibility, mobile?
6. **breaking_changes** — every behavior change might affect downstream consumers. For each, is the break acceptable, or must compatibility be preserved?
7. **tooling_configuration** — for migration / config-change / infrastructure specs, every config change has options (proactive vs reactive, opt-in vs opt-out, default vs explicit). Surface each.

For each category, identify whether the request creates a decision point. If yes, record at least one `DecisionPoint`. If no, record **exactly one** terminal `no_DP_in_category` entry with a rationale (e.g., "Category X: no decision point — already determined by [constraint Y]") — that entry lands in §8 Open Questions of the rendered spec.

### Mode detection

```bash
.devforge/lib/specify_helper detect-mode --reminder-text "<latest <system-reminder> block text>"
```

Add `--auto` when the user passed `--auto` on the `/devforge:specify` invocation OR when the environment variable `DEVFORGE_AUTO_MODE=1` is set. The helper auto-detects via three C-strict signals — env var (`DEVFORGE_AUTO_MODE=1`), `--auto` flag, OR case-insensitive substring match for `"auto mode is active"` / `"auto mode still active"` in the supplied `--reminder-text`. No other signal counts. User natural-language prose is not a signal.

The helper persists `mode` to state + prints `auto` or `interactive` to stdout.

**When uncertain about mode → prefer interactive (the helper's default).** Asking and waiting is reversible; proceeding without input is not.

### Per-decision-point protocol

For each decision point (across all 7 categories), in priority order (**scope > breaking changes > data flow > tooling > UX > edge cases**). The 6-item priority order is v3 verbatim; the 7th category `existing_behavior` slots between `data flow` and `tooling` (treat it on par with `data_flow_state` when ordering rounds — both surface state-related decisions). Per-DP loop body:

1. **Record the decision point.** Supply ≥2 valid implementations:

   ```bash
   .devforge/lib/specify_helper record-decision-point \
       --category <category> \
       --description "<one-line description of the choice>" \
       --valid-implementations '["impl-A","impl-B"]'
   ```

   The helper auto-assigns a `dp_id` of the form `DP-<category>-<N>` and creates the entry with `status="pending"`.

2. **Resolve the decision point** — auto path vs interactive path. Both wrong-mode calls are hard helper gates (exit 2): `set-dp-default-applied` in interactive mode emits `"set-dp-default-applied: mode=interactive rejects default-applied setter (use set-dp-answer)"`, and `set-dp-answer` in auto mode emits `"set-dp-answer: mode=auto rejects user-answer setter (use set-dp-default-applied)"`. The orchestrator picks the setter that matches the mode `detect-mode` persisted in state; the helper enforces.

   **Auto path** (mode=`auto`): draft the default from Phase 1.5 findings + model recommendation, then:

   ```bash
   .devforge/lib/specify_helper set-dp-default-applied \
       --dp-id "<DP-id>" \
       --default-applied "<named default>"
   ```

   The rendered spec marks the entry `[default applied]` in §8. The user reviews defaults at the Phase 5 approval gate.

   **Interactive path** (mode=`interactive`): present the question to the user.

   - **Preferred**: `AskUserQuestion` when the answer fits 2–4 mutually-exclusive options. Single-line question text, no multi-line markdown or blockquote. If paragraph-length context is needed, print the context as plain prose ABOVE the AskUserQuestion call and keep the question line short.
   - **Fallback**: when `AskUserQuestion` is not available (older runtime, headless mode, or tool not loaded), use a numbered markdown list with one question per item. Each question lists explicit alternatives `(a)`, `(b)`, `(c)` and names the model's recommended default at the end.
   - **Bundling**: when ≥4 related questions exist AND they are NOT conditionally dependent on each other, bundle them into a single `AskUserQuestion` call (the tool supports multiple questions per call) so the user submits once. Do NOT bundle decisions that are conditionally dependent (e.g., "What tool?" determines whether the cache-strategy question even applies).

   End the turn after presenting the question(s). The user's reply opens the next turn. Then persist:

   ```bash
   .devforge/lib/specify_helper set-dp-answer \
       --dp-id "<DP-id>" \
       --user-answer "<verbatim user answer>"
   ```

3. **Deferral path** (either mode). When the user (or auto-mode rationale) explicitly punts the decision to §6 Out of Scope or §8 Open Questions:

   ```bash
   .devforge/lib/specify_helper set-dp-deferral \
       --dp-id "<DP-id>" \
       --deferral-kind <OOS|open_question> \
       --reason "<one-line rationale>"
   ```

   Add `--increment-turn` when the deferral is the result of a follow-up exchange. The helper enforces a per-DP cap of 3 follow-ups: at the cap, the next `set-dp-deferral --increment-turn` auto-transitions the DP to `deferred_open_question` with `[exceeded cap]` visible in the §8 render.

4. **No-decision-point-in-category**. When a category has no decision point at all, record **exactly one** terminal entry per category:

   ```bash
   .devforge/lib/specify_helper record-decision-point \
       --category <category> \
       --description "no relevant decision point for <category>" \
       --no-dp-in-category
   ```

   The helper sets `status="no_DP_in_category"` and treats the category as Clear for coverage purposes. Helper accepts duplicate `--no-dp-in-category` calls for the same category but they pollute the §8 render with redundant `[no DP in category X]` lines — call once and move on.

### Question rounds

- Up to 5 questions per round.
- Prioritization order across rounds: **scope > breaking changes > data flow > tooling > UX > edge cases** (v3 verbatim 6-item order; slot `existing_behavior` alongside `data flow` per the Per-DP protocol note above).
- After each round, decide if more clarification is needed based on **whether all decision points have been covered, not on subjective sufficiency**.
- Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings.

### Coverage check + exit

After every category has at least one `DecisionPoint` (active or `no_DP_in_category`):

```bash
.devforge/lib/specify_helper rubric-coverage
```

Stdout is JSON `{category: state}` mapping each of the 7 categories to one of `Clear` / `Partial` / `Missing` / `NoDPInCategory`. Copy stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) so the user sees per-category state before Phase 3 starts.

Then gate:

```bash
.devforge/lib/specify_helper dp-finalize
```

Helper runs `verify-decision-coverage` then stamps `dp_finalized=true`. Exit 0 → every category is `Clear` or `NoDPInCategory`; advance to Phase 3. Exit 2 → at least one category is `Partial` or `Missing`; stderr enumerates the gaps. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), return to the per-decision-point protocol for the cited categories, then re-run `dp-finalize`.

**Stop only when every decision point identified above has either (a) a user answer, or (b) an explicit "out of scope" / "open question" entry. Do not stop early based on subjective sufficiency.** In auto mode, a recorded default (`set-dp-default-applied`) also satisfies (a) for stop-rule purposes — the user reviews defaults at the Phase 5 approval gate.

## Phase 3 — Codebase analysis (spec-type classification + per-type reads)

Goal: classify the spec type, read the mandatory per-type files, supplement with CBM / Glob / Grep exploration.

### Step 1 — Classify the spec type

**Handoff-seeded spec_type check (precondition).** If Phase 0.4 ran `import-handoff` on a research handoff (state has `spec_type_seeded_by_upstream == true` AND `spec_type` is set AND `source.handoff_kind == "research"`, with `source.handoff_path` the install-root-relative `specs/<NNN>-<slug>/research-handoff.json`), surface the pre-seeded value to the user before classifying:

- AskUserQuestion `"Research handoff pre-seeded spec_type=<value>; accept or override?"` with options `["accept", "override"]`.
- On `accept`: call `.devforge/lib/specify_helper classify-spec-type --spec-type <pre-seeded-value> --rationale "pre-seeded from research handoff at <handoff_path>" --seeded-by-upstream`. Lock in the value.
- On `override`: proceed with normal LLM-driven `classify-spec-type` flow described below.

Skip this precondition entirely when Phase 0.4 did not import (spec_type_seeded_by_upstream is false OR spec_type is null).

Choose one of five spec types based on `$ARGUMENTS` + Phase 1.5 findings:

- `migration_tooling` — package manager, build tool, monorepo orchestrator, CI infra, framework version bump.
- `feature_addition` — new component, new endpoint, new flow, new domain entity.
- `bug_fix` — existing behavior is wrong.
- `refactor` — behavior preserved, structure changed.
- `greenfield_feature` — feature has no related code yet; scaffolding from constitution Section 7.

```bash
.devforge/lib/specify_helper classify-spec-type \
    --spec-type <migration_tooling|feature_addition|bug_fix|refactor|greenfield_feature> \
    --rationale "<one-line rationale>"
```

**Upstream pre-seeding (origin-based, from Phase 1 source-origin tags).** When any Phase 1 input has `source_origin == "discover"` (this feature's `discovery-report.md`, §1.6), pre-seed `spec_type=greenfield_feature` because `/devforge:discover` is scope-locked to greenfield. Add `--seeded-by-upstream` to the call and use a rationale that cites the discovery report. Surface the pre-seed to the user before locking it in, via AskUserQuestion: `"Upstream is /devforge:discover — pre-seeded spec_type=greenfield_feature; override?"` with options `["accept", "override"]`. Single-line question text. End the turn. On `accept`, proceed. On `override`, ask which of the other four types in the next turn and re-call `classify-spec-type` without `--seeded-by-upstream`.

A `research` origin (this feature's `research-report.md`) and `prior_spec` origins do NOT pre-seed (research is neutral on bug/enhancement/refactor; the LLM classifies from content). A resolved feature dir carrying neither report — no `research`- or `discover`-tagged Phase 1 input — does NOT pre-seed either. This pre-seed is driven by the Phase 1 reads, not by the import: a `cold` pick in Phase 0.4 skips the handoff-content import but still reads the reports in §1.5/§1.6, so a `discovery-report.md` pre-seeds `greenfield_feature` on the cold path too. The handoff-seeded precondition above is the one that does NOT fire on `cold`, because no import ran.

State the classification at the start of Phase 3 user-facing output so the user can challenge it before mandatory reads consume tokens.

### Step 2 — Mandatory read list per spec type

Each spec type has a closed slot table. Walk every slot. For each slot, either record the actual file path read OR record `--n-a-reason` explaining why the slot does not apply to this spec. Sentinel slots (surrounded by `__`) require an explicit `--slot-pattern`; concrete patterns auto-match by path.

```bash
.devforge/lib/specify_helper record-mandatory-read \
    --read-path "<actual path>" \
    [--slot-pattern "<sentinel slot, e.g. __entry__>"]

# OR

.devforge/lib/specify_helper record-mandatory-read \
    --slot-pattern "<slot pattern>" \
    --n-a-reason "<why this slot is N/A for this spec>"
```

The per-type slot tables (helper-owned, walked in order):

- **`migration_tooling`**: `package.json` · `.github/workflows/*` · `**/package.json` · `.husky/*` · `.pre-commit-config.yaml` · `.lefthook.yml` · `lerna.json` · `turbo.json` · `nx.json` · `pnpm-workspace.yaml` · `rush.json` · `*lock*` (note presence/size only) · `.npmrc` · `.yarnrc` · `.pnpmrc`.
- **`feature_addition`**: `__entry__` (root component / entry files — router, store, app init) · `__similar_feature__` (most-similar existing feature via grep) · `__type_defs__` (type defs for affected entities) · `__api_ops__` (API / GraphQL ops for affected resources) · `__test_files__` (test files for affected area).
- **`bug_fix`**: `__buggy_files__` (the buggy file(s) named in the request) · `__direct_deps__` (direct deps of buggy file) · `__direct_callers__` (direct callers via grep) · `__recent_git_log__` (recent git log on buggy file — `git log -5 -- path/to/file`).
- **`refactor`**: `__refactored_files__` (the file(s) being refactored) · `__all_callers__` (all callers via grep) · `__all_tests__` (all tests for refactored code).
- **`greenfield_feature`**: `constitution.md#scaffolding-guide` (Constitution Section 7) · `__framework_docs__` (framework docs via WebSearch for the feature pattern) · `.devforge/memory.md` (prior-feature lessons) · `specs/*/discovery-report.md` (the `/devforge:discover` reference md, if Phase 1 loaded one).

Gate:

```bash
.devforge/lib/specify_helper verify-mandatory-reads
```

Exit 0 → every slot for the active `spec_type` is covered. Exit 2 → at least one slot has neither `read_path` nor `n_a_reason`. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), perform the cited slot(s) and re-run.

### Step 3 — Discretionary exploration

After the mandatory reads, perform additional exploration for anything not covered above.

**Use Glob/Grep tools specifically (not Bash `grep`/`find`) so the tool-call log is auditable.** The Glob/Grep tools produce structured records that show exactly which paths were enumerated and which patterns matched.

For structural code discovery (named symbols, callers, impact paths), use the codebase-memory-mcp chain in MANDATORY order:

1. `search_graph` — query for named symbols and files (use `qn_pattern` for qualified-name regex; `name_pattern` for short-name regex; `label="File"` queries use `name_pattern`, NOT `file_pattern`).
2. If `search_graph` returns 0 hits for an expected behavior → `search_code` — text or regex search with a literal token over the affected package. Catches inline expressions buried inside framework reactive blocks (Vue `<script setup>`, React hooks, Svelte) that the graph indexer does not promote to named symbols.
3. `trace_path` — impact analysis on confirmed surfaces (`mode` ∈ `calls` / `data_flow` / `cross_service`).
4. `get_code_snippet` — read source on the highest-confidence candidates. This is the only sanctioned source-read path; do not use raw `Read` over source-extension files (runtime hooks block raw calls on first match per session).

Confidence calibration: 0 hits at `search_graph` alone means "no NAMED implementation"; 0 hits at `search_code` means "truly absent". Do not conflate these.

### Step 4 — Cross-reference

- Cross-reference findings with `.devforge/memory.md` for known issues in this area.
- Verify docs accuracy if Phase 1 read docs files — flag discrepancies between docs and actual code as Phase 1.5 findings (re-enter Phase 1.5 to record them) before Phase 4 begins.
- Note any patterns from the most-similar existing feature that this spec should follow.

### Phase 3 finalize

```bash
.devforge/lib/specify_helper phase3-finalize
```

Helper re-runs `verify-mandatory-reads` then stamps `phase3_finalized=true`. Exit 0 → advance to Phase 4. Exit 2 → copy stderr VERBATIM, fix the cited slot(s), re-run.

## Phase 4 — Write the specification

Goal: deterministic 9-section render via setters + verifiers; the helper owns section order, heading text, and AC subsection labels.

### Step 4.1 — Header (spec number, feature name, date, branch)

`spec_number` + `feature_slug` decide which directory `spec.md` is written into, so wherever Phase 0.4 resolved a feature dir they must name THAT dir rather than a fresh one. Take exactly ONE of the three number paths below — they are ordered; use the first whose condition holds — then run the feature-name, date, and branch steps that follow, which apply to all three. A re-entry revision (Phase 0.5 fired) takes the same paths on the same conditions: an existing `spec.md` in the resolved dir changes nothing here, because these paths key on state and on the directory's name.

**Warm path — state already carries `spec_number` and `feature_slug` (the normal case).** `import-handoff` seeded both in Phase 0.4 from the resolved feature dir's `<NNN>-<slug>` basename. Do NOT call `assign-spec-number`: its fresh `max+1` scan would produce a different number and send `spec.md` to a different directory than the intake artifacts. Take `<NNN>` and `<slug>` from that basename and go straight to the feature-name step.

**Cold path — state carries neither field, and the resolved feature dir's basename has the form `<NNN>-<slug>`** (exactly three digits, a hyphen, then the slug — the shape intake allocates). This is the `cold` pick in Phase 0.4: no import ran, so nothing was seeded. Split the basename at the first hyphen and seed the number from it:

```bash
.devforge/lib/specify_helper set-spec-number --value "<NNN>"
```

Persists the value verbatim after validating it is 3+ digits (zero-padding preserved). Performs no scan — the caller already knows the number.

**Genuine fallback — state carries no `spec_number` and the resolved dir's basename is not `<NNN>-<slug>`.** Reachable two ways: a handoff sitting in a non-`NNN` directory under `specs/` (`find-handoffs` lists any `specs/` subdirectory carrying an intake handoff, not only `NNN-`-prefixed ones), or a pre-migration handoff imported by explicit path from outside `specs/`. In both cases `import-handoff` leaves the fields unseeded and there is no number to split out, so allocate fresh — and note the consequence to the user: `spec.md` will land in a NEW directory, not beside the intake handoff.

One documented limitation of this path: on the importing arms `import-handoff` has already written `downstream_links.spec_path` into the intake handoff, pointing at the handoff's OWN directory — which the fresh allocation then does not use, so that field is left stale. Nothing corrects it and no defensive check is added; say so when you note the new directory, so the user knows the two do not agree. The other two paths are unaffected, because there the allocated directory IS the handoff's directory.

```bash
.devforge/lib/specify_helper assign-spec-number
```

Scans `specs/` for the highest `NNN-*` prefix and emits the next zero-padded number to stdout (`001`, `002`, …). Persists `spec_number`. Do not pass `--specs-root`: the flag is accepted-but-ignored, and the scan always targets `specs/` under the install root.

**Feature name (all three paths).**

```bash
.devforge/lib/specify_helper assign-feature-name --feature-name "<2-4 word kebab-case>"
```

On the warm and cold paths, `<slug>` is the resolved feature dir's basename after the `<NNN>-` prefix — pass it verbatim so the rendered header matches the directory. On the genuine-fallback path, generate a 2-4 word kebab-case slug from `$ARGUMENTS` (e.g., `user-auth`, `dark-mode-toggle`) and, if the proposal fails validation, fix it and re-call. The helper validates the pattern `^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$` and persists both `feature_name` and `feature_slug`.

This call runs on the warm path too, even though `import-handoff` already seeded `feature_slug`: the import seeds `feature_slug` alone, and `feature_name` is what the rendered spec title and the Step 5.1 approval summary use. An intake-allocated directory always carries a slug that passes validation, because intake validates the slug against this same pattern before creating the directory. If the helper nonetheless rejects a dir-derived slug (a hand-created or pre-migration directory), copy its stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) and end the turn — the user renames the directory or re-runs intake.

```bash
.devforge/lib/specify_helper set-date --date "$(date -u +%Y-%m-%d)"
```

Helper accepts only `YYYY-MM-DD` format.

**Branch — fallback only.** `/devforge:research` and `/devforge:discover` create `spec/NNN-<slug>` at intake, so the session is normally already on it and nothing runs here. Call `create-branch` only when Phase 0.2 deferred branch creation — the default-branch arm, or the `from-here` choice on the other-branch arm:

```bash
.devforge/lib/specify_helper create-branch \
    --current-branch "<current branch from Phase 0>" \
    --default-branch "<default branch from Phase 0>"
```

When on the default branch, the helper's stdout emits a single line of the form `git checkout -b spec/NNN-<slug>`. Execute that line:

```bash
git checkout -b spec/NNN-<slug>
```

Tell the user: `"Created and switched to branch spec/NNN-<slug>"`. The `NNN-<slug>` in that line is the one now in state, so on the warm and cold paths the branch name matches the resolved feature dir. When on a non-default branch (Phase 0.2 user choice = `from-here`), the helper emits a `# already on non-default branch ...` informational comment and skips the checkout.

### Step 4.2 — Narrative sections (§1 Overview, §2 Current State, §3 Desired Behavior)

```bash
.devforge/lib/specify_helper set-overview --content "<2-3 sentences>"
.devforge/lib/specify_helper set-current-state --content "<existing-codebase narrative OR greenfield scaffolding ref>"
.devforge/lib/specify_helper set-desired-behavior --content "<specific description of what should change>"
```

§2 Current State: for an existing codebase, describe how the system currently works in the affected area; include file paths + line numbers (`path/to/file.ts:42` format). Incorporate context from `docs/` loaded in Phase 1 (documented behavior, architecture patterns, feature relationships) — this section is the primary way downstream commands inherit docs knowledge, so capture it fully rather than assuming downstream will re-read docs. For greenfield, describe what exists so far (may be nothing) and reference constitution Section 7 for where the feature should be scaffolded.

§3 Desired Behavior: be specific. "The button shall be blue" not "improve the button". The spec describes WHAT, not HOW; solutions come in `/devforge:plan`.

### Step 4.3 — §4 Affected Areas (table rows)

Call once per row:

```bash
.devforge/lib/specify_helper record-affected-area \
    --area "<component or module name>" \
    --files '["<path-1>","<path-2>"]' \
    --impact "<one-line description of what changes>"
```

For greenfield, list scaffolding needs explicitly (Impact = "Create new") so `/devforge:plan` and `/devforge:breakdown` see the surface area to bootstrap.

### Step 4.4 — §5 Acceptance Criteria (7 categorized subsections, EARS notation)

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

Every AC `statement` uses EARS notation (Easy Approach to Requirements Syntax, IEEE 29148-2018 / Kiro convention). Choose one of 5 variants; helper validates the statement matches the declared variant via regex. Malformed statements are rejected.

| Variant | Pattern | Use when |
|---|---|---|
| `ubiquitous` | `The <system> shall <response>.` | always-true requirement |
| `event_driven` | `WHEN <trigger>, the <system> shall <response>.` | event response |
| `state_driven` | `WHILE <state>, the <system> shall <response>.` | state-dependent behavior |
| `optional` | `WHERE <feature>, the <system> shall <response>.` | feature-flag / conditional |
| `unwanted` | `IF <trigger>, THEN the <system> shall <response>.` | unwanted-behavior prevention |

**Subsection-EARS constraints.** §5.1 (`tooling_artifact_presence`) and §5.7 (`hygiene`) accept only the `ubiquitous` variant AND require a `--verification-command`. The other five subsections accept any of the five EARS variants; `--verification-command` is optional. The helper rejects an AC that violates these constraints.

Call once per AC:

```bash
.devforge/lib/specify_helper add-ac \
    --subsection <tooling_artifact_presence|behavior_preservation|behavior_change|ci_pipeline|hooks_gates|documentation|hygiene> \
    --ears-variant <ubiquitous|event_driven|state_driven|optional|unwanted> \
    --statement "<EARS-formatted statement>" \
    [--verification-command "<executable check>"] \
    [--test-anchor "<path::test_name>"] \
    [--finding-ref "<F-source-N from Phase 1.5>"]
```

The seven subsection keys map to fixed headings:

- `tooling_artifact_presence` → **5.1 Tooling / artifact presence and absence** (Ubiquitous only; `--verification-command` required)
- `behavior_preservation` → **5.2 Behavior preservation**
- `behavior_change` → **5.3 Behavior change**
- `ci_pipeline` → **5.4 CI / pipeline**
- `hooks_gates` → **5.5 Hooks / gates**
- `documentation` → **5.6 Documentation**
- `hygiene` → **5.7 Hygiene** (Ubiquitous only; `--verification-command` required)

For a subsection that does not apply to this spec, record an explicit N/A marker instead of an AC:

```bash
.devforge/lib/specify_helper add-ac \
    --subsection <subsection-key> \
    --mark-na \
    --n-a-reason "<why this subsection is N/A>"
```

Each subsection: at least one AC if applicable, or "N/A — [reason]". Do not collapse subsections that don't apply — explicitly mark them N/A so reviewers know they were considered.

**Optional `test_anchor` field.** When a brownfield AC corresponds to an existing test, populate `--test-anchor` with `path::test_name`. Downstream `/devforge:verify` will consume the anchor once fine-grained tests-mode test→AC mapping lands (currently deferred — today `/devforge:verify`'s `tests` mode runs the assembled suite as one mechanical gate and code-reads the ACs independently of the anchor). Leave empty when no test exists yet — `/devforge:breakdown` plans the test.

See `tests/lib/fixtures/specify-sample-migration.md` for the migration_tooling AC shape (all 7 subsections populated with mixed EARS variants + paired verification commands on §5.1 + §5.7), and `tests/lib/fixtures/specify-sample-greenfield.md` for the greenfield_feature shape (`N/A` markers on §5.2 + §5.4 + `[default applied]` rendering in §8).

### Step 4.5 — §6 Out of Scope

The coverage rule: **For each Phase 1.5 finding (every item enumerated under "Findings from Inputs"), this finding either (a) becomes an Acceptance Criterion in §5, (b) becomes a Technical Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in the Risks table in §9 with a documented mitigation strategy. A Phase 1.5 finding that does not appear in any of the above is a hard error — re-verify Phase 1.5 enumeration is complete before saving.**

Record each OOS item with the Phase 1.5 cross-reference where applicable:

```bash
.devforge/lib/specify_helper record-out-of-scope \
    --content "<NOT-included item>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]
```

Be exhaustive on Out of Scope — this prevents scope creep during implementation. A §6 entry that contradicts a §5 AC / §4 affected-area (the spec both excludes and requires the same concern) is surfaced by `verify-scope-coherence` at Phase 4 Step 4.9 as a non-blocking warning for the author to reconcile.

### Step 4.6 — §7 Technical Constraints

§7 captures **constraints that drive architecture**, not the architecture itself. Architecture choices belong in `/devforge:plan` (sourced from CBM-indexed prior decisions + constitution rules), not here. Five kinds; helper rejects mismatched or vague invocations.

```bash
# NFR — quantified non-functional requirement (drives architecture in /devforge:plan)
.devforge/lib/specify_helper record-constraint \
    --kind nfr \
    --quantifier "<numeric-threshold + unit OR named-compliance-class>" \
    --content "<constraint text>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]

# Constitution anchor — transcribes a code-pattern rule from constitution.md
.devforge/lib/specify_helper record-constraint \
    --kind constitution_anchor \
    --constitution-ref "<§-ref, e.g. §3.6>" \
    --content "<verbatim quoted rule text>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]

# External system — integration contract with an off-codebase dependency
.devforge/lib/specify_helper record-constraint \
    --kind external_system \
    --protocol "<protocol name, e.g. REST | gRPC | SAML 2.0>" \
    --content "<integration constraint text>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]
# OR — if the contract lives in a doc (OpenAPI / proto / etc.):
.devforge/lib/specify_helper record-constraint \
    --kind external_system \
    --contract-doc-ref "<path/to/contract>" \
    --content "<integration constraint text>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]

# Process rule — non-architectural workflow constraint (e.g. commit conventions)
.devforge/lib/specify_helper record-constraint \
    --kind follow \
    --content "<rule text>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]

# Behavior preservation — existing functionality that must not regress
.devforge/lib/specify_helper record-constraint \
    --kind not_break \
    --content "<behavior to preserve>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]
```

Render labels: `nfr` → "Must satisfy NFR (<quantifier>)"; `constitution_anchor` → "Must follow constitution §<ref>"; `external_system` → "Must integrate with external system (<protocol or contract>)"; `follow` → "Must follow"; `not_break` → "Must not break".

**Helper-enforced validators (will reject invalid invocations at write time):**

- `nfr`: `--quantifier` required, must contain numeric threshold + unit (`ms / s / sec / min / hr / users / req/s / rps / qps / tps / GB / MB / KB / TB / % / $ / connections / rows / records`) OR named-class citation (`PCI-DSS / SOC 2 / ISO XXXXX / GDPR / HIPAA / FedRAMP / FIPS / NIST`). Bare adjectives (`high`, `low`, `fast`, `scalable`, `robust`, `performant`, `secure`, etc.) rejected as vague.
- `constitution_anchor`: `--constitution-ref` required; helper greps `<install_root>/constitution.md` for `^### §<ref>` (or bare `^### <ref>`); rejects on miss.
- `external_system`: at least one of `--protocol` OR `--contract-doc-ref` required.

**DO NOT** encode architecture choice in §7. `--kind nfr --content "must use microservice architecture"` is wrong — that's a `/devforge:plan` decision sourced from CBM-indexed prior plans + constitution. If you're tempted to record architecture here, identify the underlying NFR that drives it and record that instead.

**`use` removed.** Invocations with `--kind use` now exit 2 with a migration message naming the three replacement kinds. Legacy entries in pre-existing state JSON surface a stderr warning at load time (non-blocking) and are silently dropped at render — re-record under the correct new kind.

**Known limitation — `constitution_anchor` validates location, not body match.** The helper confirms the cited section EXISTS in `<install_root>/constitution.md`; it does NOT confirm the citation's body matches the framework canonical text. If the consumer's `constitution.md` has drifted from framework `src/constitution.md` (e.g. consumer was `/devforge:constitute`'d before a strengthening patch landed), the anchor citation passes the structural gate while referencing stale body text. Maintainers run `constitute_helper forge-internal:verify-universal-defaults --consumer-path <dir>` periodically to detect this; consumer-side resync stays manual.

### Step 4.7 — §8 Open Questions

Two sources land here:

1. Genuine remaining uncertainties.
2. Per-Phase-2-category "no decision point" rationales (the `no_DP_in_category` entries from Phase 2 — the helper auto-renders those in §8).

For genuine open questions, call:

```bash
.devforge/lib/specify_helper record-open-question \
    --question-id "<Q-N or stable id>" \
    --content "<question text>" \
    [--category-no-dp-reason "<optional rationale text>"]
```

### Step 4.8 — §9 Risks (table rows)

Call once per row:

```bash
.devforge/lib/specify_helper record-risk \
    --risk "<risk description>" \
    --likelihood <Low|Med|High> \
    --impact <Low|Med|High> \
    --mitigation "<how to handle>" \
    [--finding-ref "<F-source-N from Phase 1.5>"]
```

### Step 4.9 — Verifiers (run in order)

```bash
.devforge/lib/specify_helper verify-coverage
.devforge/lib/specify_helper verify-ac-subsection-coverage
.devforge/lib/specify_helper verify-ac-shape
.devforge/lib/specify_helper verify-numerical-consistency
```

- `verify-coverage` — every Phase 1.5 `Finding` has `landed_in != unlanded`. Findings are recorded `unlanded` in Phase 1.5; they land here in §5–§9 as you write the entries that cover them. Walk each `unlanded` finding cited on stderr and pass its `finding_id` to the setter you write for it: (a) `add-ac ... --finding-ref <finding_id>`, (b) `record-constraint ... --finding-ref <finding_id>`, (c) `record-out-of-scope ... --finding-ref <finding_id>`, or (d) `record-risk ... --finding-ref <finding_id>`. The `--finding-ref` flag is what flips the finding from `unlanded` to that bucket so `verify-coverage` passes — writing the AC/Constraint/OOS/Risk without the flag leaves the finding `unlanded` and fails the gate. `--finding-ref` is repeatable on `add-ac`, `record-constraint`, and `record-risk` (pass it once per finding): one entry can land several findings, and one finding can be landed by the single entry that covers it. A `--finding-ref` naming an unknown `finding_id` exits non-zero (a typo fails loudly, never silently passes coverage). When a finding is already covered by an existing §5–§9 entry and there is no new AC/Constraint/OOS/Risk to add, land it directly with `set-finding-landed --finding-id <finding_id> --landed-in <AC|Constraint|OOS|Risk> [--landed-ref <existing entry ref, e.g. AC-3>]`. Re-run until exit 0.
- `verify-ac-subsection-coverage` — each of the 7 §5 subsections has ≥1 AC OR an explicit `--mark-na --n-a-reason` marker. On exit 2, add the missing AC or N/A marker for the cited subsection and re-run.
- `verify-ac-shape` — every AC `statement` matches the regex for its declared `ears_variant`. On exit 2, re-call `add-ac` with a corrected statement (the helper appends — there is no delete; re-add with the same `ac_id` is rejected, so revise the proposed text BEFORE re-running `add-ac`; if the AC has already been recorded under that `ac_id`, reset state and re-walk Step 4.4 to avoid stale entries).
- `verify-numerical-consistency` — every multi-occurrence digit-prefixed noun in the rendered spec carries the same numeric value across all occurrences. On exit 2, the stderr cites locations; resolve by editing the source values via setters and re-rendering. Verify counts via direct Bash enumeration before composing setter content — for every count, size, version number, or line number you write into the spec, the same verified value must appear everywhere it is referenced.

```bash
.devforge/lib/specify_helper check-constitution-compliance --constitution-path constitution.md
```

Non-blocking. Helper greps `constitution.md` for `MUST` / `MUST NOT` / `SHALL` / `SHALL NOT` lines and surfaces token-overlap warnings against rendered AC / Constraints / OOS. Warnings appear on stderr but exit code is 0 unless the helper itself fails. Surface any warning text to the user as plain prose so they decide whether to amend the spec or proceed with the conflict noted (a noted conflict typically lands in §8 Open Questions). Re-run this command at Phase 5 entry so changes between Phase 4 and approval re-surface relevant warnings.

```bash
.devforge/lib/specify_helper verify-scope-coherence
```

Non-blocking. Helper token-overlaps each §6 Out-of-Scope entry against every §5 AC `statement` and §4 affected-area `impact`, and surfaces a WARNING naming the §6 entry plus the conflicting §5/§4 entry whenever an OOS exclusion overlaps a mandate (the spec both excludes and requires the same concern). Warnings appear on stderr but exit code is 0 unless the helper itself fails — a warning is NOT a verify failure, so do not treat it as one. Surface any warning text to the user as plain prose. Recovery is advisory reconciliation, not a block: the author reconciles the real contradiction by EITHER dropping the §6 OOS entry (the concern is actually in scope) OR weakening/removing the §5/§4 mandate (the concern is actually out of scope). This is a token-overlap heuristic and WILL surface false positives (a §6 entry and a §5 AC sharing a noun without truly conflicting); on a false positive, note it and proceed — the hard human gate is the Phase 5 approval echo-back, and this check is a warning backstop behind it.

### Step 4.10 — Capture the design source

Declare where this feature's UI design comes from. The declaration shape is `scheme:target` where scheme is one of `html`, `figma`, `screenshot`, or the bare literal `none`. This fires on every spec — a feature with no UI simply declares `none`.

Ask via AskUserQuestion: `"What is this feature's design source?"` with options `["None — no UI, or no design reference", "Local design/reference.html", "Figma", "Screenshot / image file"]`. Default = the first option (None). Single-line question text. End the turn. The user's reply opens the next turn.

<!-- Authoring note: the four options are a structured scheme (the composed `scheme:target` value feeds the `set-design-source` setter below); the Figma URL / screenshot path is captured in a next-turn prose follow-up. This split is intentional and must NOT be collapsed into an "Other" free-text option — that would make 5 options (over AskUserQuestion's 2–4 limit) and would not capture a structured scheme. -->


Compose the declaration value from the choice:

- `None — no UI, or no design reference` → `none` (fully determined; no follow-up needed).
- `Local design/reference.html` → `html:design/reference.html` (fully determined; no follow-up needed).
- `Figma` → in the next turn, ask in plain prose: `"Paste the Figma frame URL."` Compose `figma:<url>` from the URL the user supplies.
- `Screenshot / image file` → in the next turn, ask in plain prose: `"Give the screenshot path, relative to the repo root."` Compose `screenshot:<path>` from the path the user supplies.

Write the composed value:

```bash
.devforge/lib/specify_helper set-design-source --value "<composed value>"
```

The setter validates the shape: it exits non-zero (with a stderr message naming the valid shapes `html:<path> | figma:<url> | screenshot:<path> | none`) on an unknown scheme, an empty target, a bare recognized scheme with no colon, or any `none:<...>` (`none` must be bare). On non-zero exit, surface the stderr to the user, fix the value, and re-call.

### Step 4.11 — Render + save

```bash
.devforge/lib/specify_helper render
```

Stdout is the full 9-section spec markdown matching the helper's locked template. Capture the stdout bytes verbatim; do not paraphrase or re-format.

Write the rendered bytes into the feature directory. On the warm and cold paths that directory is the one resolved in Phase 0.4 and already exists — the `mkdir -p` is a no-op there and creates the directory only on the genuine-fallback path:

```bash
mkdir -p "specs/<NNN>-<feature-name>"
# write the captured render bytes to:
#   specs/<NNN>-<feature-name>/spec.md
```

Use Write with the captured bytes as the file content. Do NOT edit the rendered markdown — any change goes back through the relevant setter + a fresh `render`. On a re-entry revision (Phase 0.5 fired) `spec.md` already exists at that path and this Write REPLACES it wholesale — that is correct, not a collision to route around; the superseded version stays in git history via the per-step `[WIP]` commits.

After Write, verify the on-disk bytes match the helper render in canonical form:

```bash
.devforge/lib/specify_helper verify-rendered --path "specs/<NNN>-<feature-name>/spec.md"
```

Exit 0 = on-disk file matches helper render in canonical form (LF line endings, no trailing whitespace, single trailing newline). Exit 2 = real content drift between rendered + written bytes; re-render + re-write before proceeding to Phase 5. Cosmetic editor mutations (CRLF, trailing whitespace, extra trailing newlines) are tolerated; content changes are not.

Stamp the spec at the current repo HEAD so downstream commands can detect drift:

```bash
.devforge/lib/cbm_sync_helper stamp-spec "specs/<NNN>-<feature-name>/spec.md"
```

Appends `(spec_path, git_sha, stamped_at)` to `.devforge/spec-stamps.jsonl` (append-only). Downstream `/devforge:plan` and `/devforge:implement` invoke `check-spec` to surface drift: `current` = no §4-cited file changed since the stamp; `drift <a>..<b> <files>` = at least one cited file changed; `missing` = no stamp.

**Known limitation — drift detection precision is bounded by §4 Affected Areas completeness.** If a cited file is missing from §4, drift on that file is silent. `/devforge:breakdown` already pressures §4 completeness for task partitioning, so the same pressure benefits drift detection — but it is a known ceiling. A future Stage 2 enhancement may expand the cited set via CBM `trace_path` outbound from §4-cited files; deferred until empirical miss-rate justifies the cost.

## Phase 5 — Approval + manual next step

### Step 5.1 — Summary echo

```bash
.devforge/lib/specify_helper render-summary
```

Stdout is the deterministic 4-bullet approval summary. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The summary form is:

```
I've created the specification at `specs/NNN-[feature-name]/spec.md`. Key points:
- **What changes**: [1-2 sentences]
- **Files affected**: [count] files across [areas]
- **Acceptance criteria**: [count] testable criteria across [count of applicable subsections] AC categories
- **Out of scope**: [key exclusions]

Please review and either approve or request changes. Once approved, run `/devforge:plan` to create the technical implementation plan.
```

### Step 5.2 — Constitution recheck (re-run)

```bash
.devforge/lib/specify_helper check-constitution-compliance --constitution-path constitution.md
```

Re-run as an entry gate: state may have changed between Phase 4's first invocation and now (e.g., a Phase 4 verifier loop revised an AC). Surface any warning text to the user as plain prose alongside the approval prompt.

### Step 5.3 — Approval prompt

AskUserQuestion: `"Approve this spec?"` with options `["approve", "request-changes", "cancel"]`. Single-line question text. End the turn. The user's reply opens the next turn.

- **`approve`** → emit the manual-next-step block (Step 5.4). Spec status stays `Draft`. The user (or `/devforge:plan` on its first run) flips status to `Approved` separately — `/devforge:specify` does not auto-flip.
- **`request-changes`** → in the next turn, ask the user which phase/section to revise. Re-enter the relevant phase (re-run the setters that touch the cited area), then re-run Phase 4 Step 4.9 verifiers + Step 4.10 design-source capture + `render` + write the file + Phase 5 Step 5.1 summary + Step 5.3 approval. The state file persists across the loop; setters mutate in place.
- **`cancel`** → leave `.devforge/specify-state.json` in its current state and the rendered `spec.md` on disk as a draft; tell the user `"Run /devforge:specify again when ready; current state preserved at .devforge/specify-state.json (will be overwritten on the next /devforge:specify invocation)."` End the turn.

### Step 5.4 — Manual-next-step block

This step runs ONLY on the `approve` branch of Step 5.3 — never on `request-changes` or `cancel`.

**Persist the design anchor.** Before writing the handoff artefact, persist this feature's design intent to the feature directory:

```bash
.devforge/lib/specify_helper write-design-anchor
```

The helper writes `specs/<NNN>-<feature-name>/design-anchor.json` atomically from the design anchor already in `/devforge:specify` state — the one carried from a `/devforge:research` / `/devforge:discover` handoff by `import-handoff` (Phase 0.4) when intake captured one, or, when intake captured none, one the helper composes from the `**Design source**:` declaration recorded by `set-design-source` (Step 4.10) as a backstop. The backstop is internal to the helper; no separate orchestration is required. Its only preconditions are `spec_number` and `feature_slug`, both set in Step 4.1 (by whichever of its three number paths applied, plus `assign-feature-name`) and therefore already present on this branch; the helper creates the feature directory itself if needed. The `**Design source**:` frontmatter line stays as the human-readable summary of the same intent; `design-anchor.json` is persisted as the structured, immutable design-intent record, so later pipeline stages can read it directly in place instead of having it re-carried through handoffs. `/devforge:specify` is the gate that guarantees this record is persisted before `/devforge:plan`; the write is idempotent — a re-run of `/devforge:specify` overwrites it. On a non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), address the cited cause, and re-run.

**Write the handoff artefact first.** Before emitting the manual block, write the structured specify→plan handoff:

```bash
.devforge/lib/specify_helper finalize-handoff
```

Helper reads `.devforge/specify-state.json` (read-only, no mutation), builds the handoff from the rendered spec sections + any upstream research/discover provenance, validates, and atomic-writes `specs/<NNN>-<feature-name>/handoff.json` (sibling to the `spec.md` already written in Phase 4). The handoff carries spec status `Draft` — `finalize-handoff` does NOT flip status. On exit 0: surface the written `specs/<NNN>-<feature-name>/handoff.json` path to the user in your next user-facing message as a fenced code block, then proceed to the WIP-commit block below. On non-zero exit (render-completeness failure — missing spec_number/feature_slug, or empty/partial spec content): `handoff.json` was NOT written, but `spec.md` (from Phase 4) and `design-anchor.json` (from the persist step above) exist — so before ending the turn, git-safe them by running `commit-artifacts` with those two paths (`handoff.json` is absent → not included):

```bash
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["specs/<NNN>-<feature-name>/spec.md", "specs/<NNN>-<feature-name>/design-anchor.json"]' \
    --label "spec: <NNN>-<feature-name>"
```

Then copy the `finalize-handoff` stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) and end the turn; the user must address the cited violation and re-invoke `/devforge:specify`. The `commit-artifacts` call is itself FAIL-SOFT (see the WIP-commit block below for its exit semantics) — if it too fails, warn with its stderr alongside the `finalize-handoff` stderr and still end the turn.

This handoff.json is auto-discovered by `/devforge:plan` on its first run; the manual next-step block below remains how the user LAUNCHES `/devforge:plan` (restart Claude Code + run the explicit command) — there is no auto-dispatch from `/devforge:specify`.

**WIP-commit the spec artifacts.** With `spec.md` written in Phase 4, `handoff.json` now written by `finalize-handoff`, and `design-anchor.json` written by the persist step above, `[WIP]`-commit all three so the work is git-safe immediately:

```bash
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["specs/<NNN>-<feature-name>/spec.md", "specs/<NNN>-<feature-name>/handoff.json", "specs/<NNN>-<feature-name>/design-anchor.json"]' \
    --label "spec: <NNN>-<feature-name>"
```

The helper stages those three paths in the install repo and makes a `[WIP] spec: <NNN>-<feature-name>` commit; it is install-repo-only (never the source repo in wrapper mode). Do NOT include `.devforge/specify-state.json` — it is `.devforge/`-scoped runtime state, excluded by design. This call is UNCONDITIONAL — always run it; `spec.md` exists from Phase 4, and the helper benign-skips `handoff.json` if `finalize-handoff` did not write it (the `finalize-handoff` non-zero branch above already commits `spec.md` + `design-anchor.json` without `handoff.json`, so this block runs with all three paths only on the success branch). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifacts are already written, so warn the user with the helper's stderr and continue to the `render-plan-handoff` block below; do NOT abort the approve flow); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op.

`/devforge:specify` does NOT mutate spec status — it stays `Draft` from Phase 4 render-time. The status flips to `Approved` only when (a) the user manually edits the `**Status**:` line in `specs/NNN-<feature-name>/spec.md`, OR (b) `/devforge:plan` flips it as part of its entry gate. Both paths are out-of-scope for `/devforge:specify`.

```bash
.devforge/lib/specify_helper render-plan-handoff
```

Stdout from `render-plan-handoff` is the deterministic manual-next-step block — copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The block heading reads `## Manual next step — run /devforge:plan`; it notes that a structured `handoff.json` was written for `/devforge:plan` and is auto-discovered by `/devforge:plan` on its first run (the manual step remains only because launching `/devforge:plan` is manual — no auto-dispatch from `/devforge:specify`), instructs the user to **restart Claude Code** (exit and relaunch the CLI/app so the newly installed command is picked up), and embeds the literal `/devforge:plan specs/NNN-feature-name/spec.md` invocation. It also carries the spec status (currently `Draft` — `/devforge:plan` will flip on its first run), spec type, AC counts per subsection, decision-point status counts, affected-area counts, and the 100%-coverage assertion for Phase 1.5 findings.

The downstream subcommand `resolve-open-question` ships in `.devforge/lib/specify_helper` for `/devforge:plan` and `/devforge:breakdown` to call when they resolve a §8 entry — `/devforge:specify` itself does NOT call it. The resolution audit trail lives in state; re-renders of `spec.md` (after a downstream `resolve-open-question` call) strike through resolved entries with the resolution note + phase + timestamp.

### Closing message

After the verbatim manual-next-step block from `render-plan-handoff` lands in the user-facing message, end the turn with a single short confirmation: `"/devforge:specify is done. Spec status: Draft — /devforge:plan will flip it to Approved on first run (or edit the **Status:** line in spec.md manually). Restart Claude Code, then copy the invocation line from the block above to continue."` Do NOT restate that invocation in your closing sentence — the block already contains the literal `/devforge:plan specs/NNN-feature-name/spec.md` line, which `render-plan-handoff` composes (it is the helper's string, not this spec's — do not rewrite it here).

## IMPORTANT RULES

1. **Specs are contracts** — once approved, the implementation must satisfy every acceptance criterion.
2. **Be exhaustive on "out of scope"** — this prevents the most common problem (scope creep).
3. **Every AC must be testable** — "improved UX" is not testable; "modal closes after successful save" is.
4. **Reference specific files** — use `path/to/file.ts:line` format for existing code. For greenfield, reference constitution Section 7 for where files should be created.
5. **Check `.devforge/memory.md`** — if similar work was done before, reference what went right/wrong.
6. **Don't propose solutions** — the spec describes WHAT, not HOW. Solutions come in `/devforge:plan`.
7. **Greenfield: include scaffolding needs** — if the feature requires creating directory structure, types, or foundational modules that don't exist yet, list them in `Affected Areas` with Impact = "Create new".
8. **Verify numerical claims** — for every count, size, version number, or line number you write into the spec, verify by direct Bash enumeration before writing. If a number appears in multiple places, use the same verified value throughout. Inconsistent numbers in the same spec are a hard error — `verify-numerical-consistency` blocks the render until reconciled.
9. **Phase 1.5 is mandatory** — every input file read in Phase 1 must produce an enumerated findings list before Phase 2 begins. Skipping or compressing this step is a hard error. The findings output is the bridge between reading and writing; without it, content silently drops.
10. **Decision points must be exhaustively surfaced** — Phase 2 must surface every decision point per the rule in that phase, across all 7 categories. The model's preferred default does not justify skipping a question — surface the choice to the user even when the model has a strong recommendation. Document categories with no decision point in §8 Open Questions.
11. **§5↔§6 coherence is a non-blocking warning** — `verify-scope-coherence` (Phase 4 Step 4.9) flags a §6 Out-of-Scope entry that overlaps a §5 AC / §4 affected-area mandate, but it is a token-overlap heuristic and false-positive-prone, so it surfaces a WARNING and exits 0 — a warning does NOT fail the verify and does NOT gate the spec. On a real contradiction the author reconciles (drop the §6 entry OR weaken the §5/§4 mandate); on a false positive, note it and proceed.
