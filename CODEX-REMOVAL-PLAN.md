# Codex Removal Plan (in-progress, iterative)

> **Status**: planning complete, execution starting at step 01.
> **Branch**: `feature/codex-remove`
> **Base**: `feature/onboard-hybrid` (the R7 7-gate hybrid that R8 Claude validated against)
> **Strategy**: Option A — single linear branch with tagged checkpoints between steps. Each step leaves the system buildable. Verify before tagging. Don't proceed until verified.

## Context for next session

This plan was drafted after a multi-day investigation (R5 → R7 → R8 → R9 → R10 → R11) into cross-runtime parity for `/onboard`. The investigation established:

1. **Claude produces R8-quality `/onboard` output natively** on the hybrid spec + 7-gate helper. ~8/10 synthesis quality.
2. **Codex hits a synthesis ceiling at ~5–6/10** for `/onboard`-shaped multi-unit synthesis tasks, even with progressive forcing-function hardening (R9 + R10 added 853 LoC of helper gates and verbs).
3. **The cost of multi-runtime parity is severe** — 797 lines of custom Codex-specific tooling per project, multi-day investigation per failure mode, recurring maintenance.
4. **The Codex constraint was suppressing Claude-native optimization** — variation markers, sigil-neutral prose discipline, dual-emitter scaffolding, and forcing functions designed against Codex's failure modes are pure overhead for a Claude-only forge.

The decision to drop Codex was made 2026-04-27. Full rationale + context lives in:
- `20 Projects/AIDevTeamForge/AIDevTeamForge - Conclusion - Codex executor as feature not bug.md` (Obsidian)
- `20 Projects/AIDevTeamForge/AIDevTeamForge - Staging hypothesis - extensions and possible future.md` (Obsidian)
- `20 Projects/AIDevTeamForge/AIDevTeamForge - Post-Codex-drop optimization plan.md` (Obsidian — the "what becomes available" forward-look)

The branches `feature/onboard-hybrid` (R7+R8 reference) and `feature/onboard-memo-first` (R9+R10 Codex hardening) are kept as historical artifacts. The latter should be tagged `archive/r11-investigation` before this work begins, to preserve the investigation as a named git ref.

## What's NOT in scope here

- The R9 + R10 hardening (memo-first verb, judgment-brief verb, claim-symbol gates, Overview-containment gate, cross-package Jaccard) on `feature/onboard-memo-first` — never validated for Claude, drop entirely with the branch. **No cherry-picking from `feature/onboard-memo-first` into this work.**
- Architectural simplifications for `develop-2.0` (helper-dispatches-subagents, validate-after-write architecture, Plan tool integration). These come AFTER `codex-removal` is merged.

## Execution plan: 8 steps

Each step is one commit + one tag. Verify before tagging. Don't proceed without verification.

### Step 00 — baseline

```bash
git tag archive/r11-investigation feature/onboard-memo-first
git checkout -b feature/codex-remove feature/onboard-hybrid
git tag codex-remove/00-baseline
```

**Verify**: `git status` clean, `git tag -l 'codex-remove/*'` shows `00-baseline`, helper file is 1102 lines (R7 7-gate version, no R9/R10 hardening).

### Step 01 — single-runtime scaffolding

Strip the dual-runtime mechanics from the orchestration scripts. Codex emitter still EXISTS but isn't invoked.

**Files to modify:**
- `install.sh` — remove `--runtimes` flag parsing, remove `VALID_RUNTIMES="claude codex"`, simplify to single-runtime install
- `scripts/generate.sh` — change `RUNTIMES="${RUNTIMES:-claude codex}"` to single runtime, drop the `for runtime in $RUNTIMES` loop, single emit

**Verify**:
- `bash install.sh --dry-run /tmp/test-target-step01` runs without error
- Output mentions only Claude paths, no Codex
- `grep -c "codex" install.sh` is zero (or only in comments to be removed in step 02)

**Commit**: `step 01: single-runtime install + generate scaffolding`
**Tag**: `codex-remove/01-scaffolding`

### Step 02 — delete Codex emitter + AGENTS.md template + .codex defaults

**Files to delete:**
- `scripts/emitters/codex.py`
- `src/files/coreLLM/desiredOutput/AGENTS.md` (the Codex coreLLM template)
- `codex-r3-interview.md` (root-level investigation artifact)
- `codex-port/` directory if present (development scratchpad)

**Files to modify:**
- `scripts/lib/install_defaults.py` — remove `.codex/config.toml` default, remove `.codex/agents/*.toml` defaults

**Verify**:
- `bash install.sh --dry-run /tmp/test-target-step02` runs without error
- No `AGENTS.md` in dry-run output
- No `.codex/agents/` paths in dry-run output
- `find . -name 'codex.py' -not -path './.git/*'` returns nothing

**Commit**: `step 02: delete Codex emitter, AGENTS.md template, .codex defaults`
**Tag**: `codex-remove/02-emitter-gone`

### Step 03 — drop AGENTS.md generation from generate-corellm.py

**File**: `scripts/generate-corellm.py`

Remove the AGENTS.md branch entirely. Function should produce only `CLAUDE.md`. Verify the SOURCE.md template still works for Claude-only generation, or simplify SOURCE.md if it had dual-runtime variation.

**Verify**:
- `bash install.sh --dry-run /tmp/test-target-step03` produces only `CLAUDE.md`
- Run actual install (not dry-run) into a fresh dir, verify CLAUDE.md is correctly generated

**Commit**: `step 03: drop AGENTS.md generation, CLAUDE.md only`
**Tag**: `codex-remove/03-corellm-claude-only`

### Step 04 — drop .codex/agents/ generation from generate-agents.py

**Files**:
- `scripts/generate-agents.py` — remove the `.codex/agents/` TOML emit branch + the `CODEX_AGENT_DEFAULTS_BY_TIER` import + its uses (model / reasoning helpers). Output only to `.claude/agents/`.
- `scripts/lib/install_defaults.py` — delete `CODEX_AGENT_DEFAULTS_BY_TIER` symbol (deferred from step 02 because deleting the symbol before its consumer would break Python import).

**Verify**:
- Install into fresh dir produces only `.claude/agents/` with .md files
- No `.codex/` dir created
- `python3 -c "from scripts.lib import install_defaults"` imports clean

**Commit**: `step 04: drop .codex/agents generation, .claude/agents only`
**Tag**: `codex-remove/04-agents-claude-only`

### Step 05 — strip variation markers + delete variation_markers.py + flatten generate-corellm.py

Two marker systems get killed in this step. Both exist purely to enable runtime variation that no longer exists in a Claude-only forge.

**5a. `{{cli.X}}` markers (variation_markers.py system).**

Replace throughout `src/commands/`, `src/agents/`, `src/files/`:
- `{{cli.sigil}}onboard` → `/onboard`
- `{{cli.sigil}}setup-wizard` → `/setup-wizard`
- `{{cli.sigil}}constitute` → `/constitute`
- `{{cli.sigil}}specify` → `/specify`
- (etc., for any other commands)
- `{{cli.primer}}` → `CLAUDE.md`
- Any other `{{cli.<key>}}` → static Claude value

Delete `scripts/lib/variation_markers.py` entirely. Modify any Python that imported it (`scripts/emitters/claude.py`) — remove the substitute call, content is now direct.

**5b. `{{output.X}}` markers (generate-corellm.py system).**

In `src/files/coreLLM/SOURCE.md`:
- `{{output.filename}}` → `CLAUDE.md` (line 1 title)
- `{{output.intro}}` → literal intro string
- `{{output.sigil}}` → `/` (~30 occurrences)

After 5a + 5b, **`generate-corellm.py` has nothing left to substitute** (uppercase wizard placeholders aren't its job). Two finish options:
- (a) Delete `generate-corellm.py`, rename `src/files/coreLLM/SOURCE.md` → `src/files/coreLLM/CLAUDE.md`, have `generate.sh` `cp` it into target.
- (b) Keep `generate-corellm.py` as a trivial copy script. Inferior — dead architecture.

Pick (a).

**Verify**:
- `grep -rn "{{cli\." src/` returns nothing
- `grep -rn "{{output\." src/` returns nothing
- Install into fresh dir produces CLAUDE.md with `/onboard` etc. directly readable
- `find scripts/ -name 'variation_markers.py' -o -name 'generate-corellm.py'` returns nothing

**Commit**: `step 05: strip {{cli.*}} + {{output.*}} markers, delete variation_markers.py + generate-corellm.py`
**Tag**: `codex-remove/05-no-variation`

### Step 06 — strip cross-runtime prose from specs

**File**: `src/commands/onboard/main.md`
- Remove the §"Sigil-neutral prose in `docs/`" section (A.3 area + IMPORTANT RULE #13)
- Remove "cross-runtime artifacts (`.claude/`, `.codex/`, …)" → just `.claude/` `.devforge/`
- Remove the `docs/` is read by both runtimes prose
- Remove "or `$<cmd>` (Codex's sigil)" mentions

**File**: `src/commands/setup-wizard/main.md`
- Remove the entire "### One-time Codex setup" section (`codex --add-trusted-dir` block)
- Remove "AGENTS.md — Project instructions for Codex CLI" line
- Remove other Codex/AGENTS.md mentions

**File**: `src/commands/setup-wizard/references/*.md`
- Search for Codex / AGENTS.md mentions, remove

**File**: `src/agents/architect.md`, `src/files/constitution.md`, `src/files/docs/*.md`
- Remove AGENTS.md mentions, Codex mentions

**File**: `src/_pending/commands/execute-task.md`
- Remove cross-runtime mentions even though command is pending

**Verify**:
- `grep -rln "Codex\|codex\|AGENTS\.md\|cross-runtime\|sigil-neutral" src/` returns hits only in expected places (or zero)
- Manual review: spec reads as Claude-only naturally

**Commit**: `step 06: strip cross-runtime prose, sigil-neutral discipline, Codex setup sections`
**Tag**: `codex-remove/06-claude-prose`

### Step 07 — update top-level docs

**Files**:
- `README.md` — remove Codex / AGENTS.md / `$onboard` mentions; reposition as Claude-native
- `CHANGELOG.md` — append entry for codex-removal with rationale (link to Obsidian Conclusion note)
- `DEVELOPMENT-STATUS.md` — update positioning, remove Codex sections
- `CLAUDE.template.md` — remove Codex variation if present
- `storage-rules.md` — remove cross-runtime artifact mentions
- `src/manifest.json` — remove AGENTS.md from generated files list
- `update.sh` — remove Codex paths if any

**Verify**:
- `grep -rln "codex\|AGENTS\.md\|Codex CLI" --include="*.md" --include="*.json" --include="*.sh" --include="*.template" .` returns nothing in user-facing docs (only in CHANGELOG.md as historical entry)

**Commit**: `step 07: update README, CHANGELOG, DEV-STATUS for Claude-native positioning`
**Tag**: `codex-remove/07-docs-updated`

### Step 08 — final smoke test + ready-to-merge

Run a real /onboard against a small test project (or testParity if it's still set up).

**Steps**:
1. Fresh install: `bash install.sh /tmp/codex-remove-final-test`
2. Manually run `/setup-wizard` → `/onboard` (or use existing testParity setup)
3. Verify Claude produces docs at expected quality
4. Compare to R8 Claude reference (claude-parity-run5 commit 6fe0780 in testParity)

**Verify**:
- `/onboard` runs cleanly
- Output quality matches R8 reference
- No regressions in helper validation
- `git diff codex-remove/00-baseline codex-remove/07-docs-updated --stat` shows the expected scope of changes (+/- LOC totals)

**Commit**: `step 08: final smoke test, ready for develop-2.0 base`
**Tag**: `codex-remove/08-final` (this is the future `develop-2.0` base)

## After codex-removal completes

```bash
# Tag the final state as the develop-2.0 starting point
git tag develop-2.0/baseline codex-remove/08-final

# Branch develop-2.0 from this checkpoint
git checkout -b develop-2.0 codex-remove/08-final
```

`develop-2.0` then becomes active development for:
- Helper-dispatches-subagents architecture (helper-v3 for Claude)
- Promote `/specify`, `/plan`, `/breakdown`, `/execute-task`, `/verify` from `src/_pending/`
- Each command gets its own validation R-runs against testParity-style fixtures
- Eventually `develop-2.0` becomes the new `main`; current `main` archived

## Branch / tag inventory after this work

```
main                                   ← will be archived
feature/onboard-hybrid                 ← R7+R8 reference, frozen
feature/codex-remove                   ← work branch
feature/codex-remove (HEAD)            ← step 08
  tags:
    codex-remove/00-baseline
    codex-remove/01-scaffolding
    codex-remove/02-emitter-gone
    codex-remove/03-corellm-claude-only
    codex-remove/04-agents-claude-only
    codex-remove/05-no-variation
    codex-remove/06-claude-prose
    codex-remove/07-docs-updated
    codex-remove/08-final
archive/r11-investigation              ← tag on feature/onboard-memo-first
develop-2.0                            ← new home, branched from codex-remove/08-final
```

R-run evidence branches preserved as-is:
- `claude-parity-run4` (R5 reference)
- `claude-parity-run5` (R8 reference)
- `codex-parity-run4` (R7 reference)
- `codex-parity-run5` (R9/R10/R11 reference)

## When resuming work

1. Read this file
2. Check `git tag -l 'codex-remove/*'` to see which step you're at
3. Last tag = last verified step
4. Continue with next step's instructions above
5. Verify before tagging
6. Update this file's "Status" line at top if scope changes
