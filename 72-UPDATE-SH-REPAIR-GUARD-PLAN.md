# 72 — update.sh Repair Guard Plan

**Status**: **DONE (build) 2026-08-12.** Phase 0 ratified by the maintainer 2026-08-12 ("implement") — OQ-1 → **(b)** and OQ-2 → **fold into Phase 1** were resolved by the orchestrator and flagged to the maintainer. Phases 1 + 2 built behind `python-engineer` → `python-reviewer` (4 findings: 2 code-side applied — the OQ-1(b) refusal rerouted `warn` → `err` so it lands on stderr, and a comment recording that the new `bin/` chmod block is `.sh`-only; 2 doc-side, resolved by the Phase-3 pass), committed `5790d73` (`update.sh` + `src/manifest.json`) and `b96735e` (`install.sh`). Phase 3 = the docs reconcile (`CHANGELOG.md`, repo-root `CLAUDE.md`, the plan-56 back-pointer, this file). **Phase 4 reproduction PASSED** — see *Reproduction (post-fix)*. Version NOT bumped (deferred to the maintainer, matching plans 49 / 56 / 65). Drafting history: **Reviewed 2026-08-12** (instruction-reviewer, 6 findings applied); the HIGH-1 empirical question was settled by running the reproduction — the non-interactive failure mode is a crash at the prompt, not a silent `exit 0`, and both baseline transcripts are embedded below under *Reproduction transcripts (2026-08-12)*.
**Branch**: `develop-2.0-init`
**Discovered**: 2026-08-11, in a consumer eval install at `~/Projects/doosan/testframeworks/forge` — a forge-installed project with every VERSIONED artifact present and zero helper code.

## Problem

*This whole section describes the PRE-fix state (2026-08-11/12). The fix shipped 2026-08-12 — every present-tense "`update.sh` cannot / `install.sh` never" claim below is history. See **Status** and `## Reproduction (post-fix)`.*

A consumer eval install was materialized as a **fresh git checkout of a committed "forge setup" state**. Plans 56 + 63 gitignore the install-reproducible CODE dirs (`.devforge/lib/`, `.devforge/bin/`, `.devforge/templates/`, `.devforge/command-refs/` — `src/files/devforge.gitignore:15-19`) and untrack them (`scripts/devforge-state-migrate.sh:55`), so the checkout carried `CLAUDE.md`, `constitution.md`, `.claude/`, `specs/` — and **no helpers at all**. `/devforge:research` failed with `no such file or directory: .devforge/lib/research_helper`.

The setup harness had run `update.sh` non-interactively to (re)provision the install. It reached the equal-version confirmation prompt and **died there** — restoring nothing — and the pipeline was run against the un-repaired tree anyway.

This is plan 56's documented OQ-1 gap — *"a fresh clone that skips a forge install/update lacks the helpers until one runs (OQ-1 → assumed install step, like `npm install`; no missing-helpers guard built)"* (`CLAUDE.md:73`, `56-DEVFORGE-CODE-GITIGNORE-PLAN.md:89`) — hit in practice. The revival condition is met: the assumed install step **did** run, and restored nothing.

### The two confirmation gates (behavior reproduced 2026-08-12)

`update.sh` has **two** `read -r confirm` gates on the full-update path, both skipped by `--force`. Interactively each defaults to abort (`info "Aborted."; exit 0`). Non-interactively **neither default is ever reached**: `read` fails on EOF, and because it is an unguarded simple command under `set -euo pipefail` (`update.sh:9`), the script dies on that line. The `case` / `"Aborted."` / `exit 0` statement that follows never executes.

| Gate | Site | Trigger | Interactive default (empty answer) | Non-interactive behavior (`read` gets EOF) |
|---|---|---|---|---|
| Equal-version bail | `update.sh:245-253` | `TEMPLATE_VERSION == TARGET_VERSION` | default N → `info "Aborted."; exit 0` | script dies at `read` → **exit 1**, no `Aborted.` line, no repair |
| Apply confirmation | `update.sh:651-656` | every non-`--force` full run | default N → `info "Aborted."; exit 0` | script dies at `read` → **exit 1**, no `Aborted.` line, no repair |

The version read is `update.sh:225` (`jq -r '.version' src/manifest.json`) vs `update.sh:226-232` (`$TARGET_DIR/.claude/template-version`, `"(unknown)"` when absent).

### Reproduction transcripts (2026-08-12)

Both runs used a scratch target: a `git init` directory whose only forge artifact is `.claude/template-version`.

Transcript A — equal-version gate (marker = `2.0.8`, matching the template):

```
$ ./update.sh <target> </dev/null; echo EXIT=$?
...
ℹ  Template version: 2.0.8
ℹ  Target version:   2.0.8
⚠  Target is already on version 2.0.8.

Continue anyway? [y/N]
EXIT=1
```

(no `Aborted.` line — the script died at `read` on EOF)

Transcript B — apply-confirmation gate (same target, marker set to `2.0.7` so the equal-version gate does not fire):

```
$ ./update.sh <target> </dev/null; echo EXIT=$?
...
+  WRITE  .claude/template-version → 2.0.8

Apply these changes? [y/N]
EXIT=1
```

### What the defect actually is

1. **`update.sh` cannot restore a broken install non-interactively at all.** It dies at whichever prompt it reaches first, regardless of what any answer-default would have been. The only failure surface is a dangling `[y/N]` line — no actionable message, nothing naming the missing helpers.
2. **Even a healthy install crashes on an idempotent scripted run.** Equal version + closed stdin exits 1 (Transcript A). The bail at `update.sh:245` compares versions only — nothing in the current script looks at install completeness — so a complete, up-to-date install behaves identically, where the correct behavior is a clean no-op.
3. **Interactively, the equal-version default gives no repair either.** Pressing Enter answers N and aborts with `exit 0` — the `"Aborted."` / exit-0 path is real **only** on the interactive path — so a human accepting the default on a helper-less tree walks away with the install still broken.

A scripted caller checking `$?` therefore *can* see the non-interactive failure; the incident harness evidently did not act on it. Do not restate this defect as "a scripted caller cannot distinguish the abort from success" — that framing was the pre-reproduction diagnosis and is false.

**The fix mechanism is unchanged by this correction.** D1 sets `FORCE=true` before either gate is reached, and D2 returns before the equal-version prompt on a non-tty; both short-circuit ahead of any `read`, so neither depends on what `read` does at EOF. The diagnosis was wrong about the failure *shape*, not about the failure *site* — the two gate anchors and the design that clears them both stand.

### Why the restore itself already works

No new copy logic is needed anywhere. Once a full run gets past both prompts:

- `update.sh:661-666` walks the manifest `templateOwned` pairs with `mkdir -p` + `cp` — it **creates missing files**, it does not merely overwrite existing ones. That covers `src/devforge/lib/** → .devforge/lib/**` (`src/manifest.json:9`) and `src/git-hooks/** → .devforge/templates/git-hooks/**` (`src/manifest.json:11`).
- `update.sh:702-704` (FIX D) `chmod +x`-es every `.devforge/lib/*_helper` afterwards, so restored launchers are executable.
- `update.sh:971` re-emits the promoted commands, which rewrites `.devforge/command-refs/<name>/`.

So the fix is entirely about **reaching** that code, not about adding restore behavior.

### Secondary defect: install.sh never stamps a version (FIXED 2026-08-12 by D3 — `install.sh:389-406`)

`install.sh` contains **zero** references to `template-version` (grep verified: 0 matches) and never reads a version at all. A freshly installed project is unstamped, so its first `update.sh` reports `Target version: (unknown)`. That is benign for the bail (`"(unknown)"` never equals the template version, so it does not fire) but it is wrong reporting, and it silently suppresses the changelog excerpt block, which is gated on `TARGET_VERSION != "(unknown)"` (`update.sh:257`). `update.sh` writes the marker at the end of a successful full run (`update.sh:1014`); `install.sh` has no counterpart.

## Why it matters

The framework's whole consumer-side story is "the helpers are install-reproducible; re-run the installer." Plan 56 made that the *only* recovery path for four gitignored dirs. But the installer cannot take that path non-interactively at all: it dies at a confirmation prompt, restores nothing, and reports the failure as a bare `[y/N]` line. A caller that checks `$?` gets a failure it cannot diagnose; a caller that does not — the incident — runs a whole eval against an un-provisioned tree where every command fails, and the failure looks like a framework bug rather than a provisioning bug. The interactive path is no better for this shape: the equal-version prompt defaults to abort, so an operator pressing Enter on a helper-less tree also gets no repair.

Cost is low: two shell edits plus a version stamp, no Python, no new copy logic, no change to any command spec.

## Scope

**In scope** — `update.sh`'s two confirmation gates (which block every non-interactive repair, dying at the prompt), an auto-detected repair mode, and `install.sh`'s missing version stamp.

**Out of scope** (documented, deliberate — do not re-derive these as bugs):

- **The eval harness's "setup v4" force-add of the CODE dirs into the setup commit.** That is user-side eval methodology, not framework code. The framework's contract stays "CODE dirs are gitignored; the installer restores them."
- **Any command-runtime missing-helpers guard.** Commands already fail loud with the exact missing path (`no such file or directory: .devforge/lib/research_helper`). A second guard layer at 20 command entry points buys nothing over the shell fix at the one place that can actually repair the install.
- **`install.sh`'s copy logic.** It restores correctly today (`install.sh:271` `cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"`). Its side-effect of overwriting `/devforge:configure`-substituted files with raw templates — observed during the incident — is **pre-existing DESIGNED behavior**: `/devforge:configure` re-substitutes them. Not a defect, not fixed here.
- **The constitution drift check (plan 44) and its ordering.** It runs at `update.sh:240-243`, deliberately BEFORE the equal-version bail. The repair guard goes after it; the ordering is preserved.
- **Constitution re-synthesis in any consumer.** Untouched.

## Decisions (recommendations — ratify in Phase 0)

### Drafting corrections (verified against the working tree 2026-08-11)

Two facts found while grounding this plan changed the shape of D1 from its first framing. Both are load-bearing; ratify them explicitly.

1. **Skipping the equal-version bail alone is inert.** The apply confirmation at `update.sh:651-656` is a second `read -r confirm` on the same path, so a non-interactive repair run would die there instead — restoring nothing, exit 1. Repair mode must clear **both** gates.
2. **The repair trigger must not be conditioned on version equality.** The incident shape reproduces with a version *difference*: an incomplete install whose `TARGET_VERSION` is older skips the bail entirely and then hits the apply confirmation — which is exactly Transcript B above. Gating repair mode on `TEMPLATE_VERSION == TARGET_VERSION` would leave that variant broken. Completeness and version are independent axes; treat them independently.

### D1 — Repair guard, auto-detected, version-independent (RECOMMENDED)

In `update.sh`, immediately after `TARGET_VERSION` is read and the drift check runs (i.e. after `update.sh:243`, before the bail at `:245`), compute install-completeness:

> **INCOMPLETE** iff `$TARGET_DIR/.devforge/lib` is missing, OR it contains no executable file matching `*_helper` at its top level.

If INCOMPLETE — **regardless of how the versions compare** — print a loud, explicit warning (`install incomplete — helper code missing (.devforge/lib has no executable *_helper launcher); proceeding in REPAIR MODE despite the version check`) and **set `FORCE=true`**. No prompt, no flag, no judgment call.

`FORCE=true` is the mechanism because `FORCE` is already the single switch that clears both gates (`update.sh:247` and `update.sh:652`) and nothing else — its only other use is the surgical-mode prompt at `update.sh:120`, which is unreachable from here (the `--only` branch exits at `update.sh:194`, before the version read at `:225`). One assignment, two gates cleared, zero new conditionals, and the existing `--force` semantics are exactly "skip the prompt and continue."

`--dry-run` stays honest: the dry-run exit at `update.sh:646-649` precedes the apply confirmation and is not affected by `FORCE`, so a dry run on an incomplete install prints the repair warning plus the plan and changes nothing.

**Sentinel rationale.** The load-bearing artifact is an executable `*_helper` launcher in `.devforge/lib/` — 24 exist in a healthy install, and the pipeline commands' helper calls all route through these launchers. The sentinel does **not** catch a partially-corrupted `.devforge/lib` (some but not all `*_helper` launchers missing) — accepted because the CODE class (plan 56) is gitignored and untracked as one unit, so it is lost or present as a whole; partial loss is not the reproduced incident shape. Two deliberate exclusions:
- **NOT `.devforge/bin/`.** The exclusion stands, but its reason is **narrowness, not impossibility**: the sentinel is scoped to the reproduced incident shape — a missing `lib/` launcher, which is what every pipeline command actually invokes. As of OQ-2's fold-in, `bin/` **is** restorable by `update.sh` (manifest pair `src/devforge/bin/** → .devforge/bin/**` at `src/manifest.json:10`, exec bit restored at `update.sh:731-735`) and is restored by the same repair run, so adding it to the trigger would buy no recovery — only a second way to trip. **Correction:** the drafted reason for this exclusion — that `bin/` is absent from the manifest, named nowhere in `update.sh`, and therefore makes the guard "permanently unsatisfiable" — was true when drafted and became FALSE the moment OQ-2 landed. See OQ-2's resolution.
- **NOT a `.devforge/command-refs/` count.** Only 11 of the 20 promoted commands ship reference files (28 files total), so any count check would encode a number that drifts with every command that gains or loses a reference.

**Rejected — a `--repair` flag.** The broken state is mechanically detectable from the filesystem, and requiring an opt-in flag re-opens the exact no-repair trap for the caller that just fell into it: a harness that did not know to pass `--force` will not know to pass `--repair`. Per the zero-escape-hatch policy, one mandatory behavior with no operator judgment call.

**Rejected — reusing `--force` by telling operators to always pass it.** That is documentation, not a guard, and it disables the interactive confirmation for healthy installs too.

### D2 — Non-interactive bail semantics for the healthy equal-version case

When the versions are equal **and** the install is complete **and** `--force` was not passed: if stdin is not a tty (`[ ! -t 0 ]`), skip the prompt and `exit 0` with an explicit message — `Target is already on version X and the install is complete — nothing to do.` Interactive decline keeps its current behavior (`exit 0`, "Aborted.") — that is a user choice and an honest no-op.

**`--force` must never be swallowed by this branch.** `--force` promises "skip confirmation prompt" (`update.sh:56`), i.e. a full re-apply — so the new check carries `[ "$FORCE" != true ]` as an explicit condition, most simply by nesting it inside the existing `if [ "$FORCE" != true ]` block at `update.sh:247`. Without that condition, `update.sh --force <target>` on an equal-version complete install would print "nothing to do" and exit 0, silently skipping the re-apply the flag was passed for. Scenario (g) in D4 is the regression net.

The argument for exit 0 rather than a deliberate non-zero exit: after D1, "up to date" **structurally implies** helpers are present, so a zero exit is a true statement (apt / npm "already up to date" semantics). Note what this changes — today that same invocation crashes with exit 1 at the prompt (Transcript A), so D2 converts a crash into a clean no-op; it is a fix for idempotent "ensure updated" callers, not a relaxation of a working check. Making the branch exit non-zero on purpose was considered and rejected: it would keep those callers broken over a state that is not an error. The dangerous case — a broken install reporting up-to-date — is impossible once D1 lands, because D1 evaluates before this branch and forces the update through.

### D3 — install.sh stamps `.claude/template-version`

At the end of a successful **full** install — after the git-hook template copy (`install.sh:385-387`), before the closing `Done.` block (`install.sh:389-396`) — read `.version` from `src/manifest.json` and write it to `$TARGET_DIR/.claude/template-version`, mirroring `update.sh:1014` (same single-line-plus-newline shape; `update.sh:229` strips whitespace on read, so the formats agree).

**Read via `python3`, not `jq`.** `install.sh` already resolves and preflight-gates a Python 3 interpreter into `PY_CMD` (`install.sh:74-93`) and has **no** `jq` dependency; `update.sh` has one (`update.sh:198-202`). Adding a hard `jq` dependency to `install.sh` to write one line would be a real portability regression for fresh installs.

**The `--only` surgical path does not stamp, by construction.** `install.sh`'s `--only` branch exits at `install.sh:232`, well before the stamp site — no conditional is needed. This matches `update.sh:193`, which already tells the user the surgical path skipped the version marker. A surgical delivery from a newer template does not make the whole install that version.

**Fail-soft.** Guard the read; on failure warn and skip the stamp. `install.sh` has no `set -e` (only the shebang at `install.sh:1`), so an unguarded failure would silently continue anyway — the guard exists to make the skip *visible*, and to guarantee a successful install is never turned into a failed one over a marker file.

### D4 — Test strategy: scratch git fixtures, run during build, not committed

No committed shell-test infrastructure exists for the installers. Follow the plan-49 / plan-56 precedent: throwaway fixture repos under the session scratchpad, one scenario per Verify block, run during the build and recorded in this plan.

| # | Scenario | Assert |
|---|---|---|
| (a) | Equal version + `.devforge/lib` removed + non-tty stdin | Update proceeds in repair mode; `.devforge/lib` restored with executable `*_helper` launchers; exit 0 |
| (b) | Equal version + intact install + non-tty stdin, no `--force` | "nothing to do" message; exit 0; target tree byte-untouched (`git status --porcelain` identical before/after, plus a `find -newer` check against a pre-run timestamp file) |
| (c) | Older `TARGET_VERSION` + intact install + tty-less `--force` | Normal update runs exactly as before — regression net for the version-differs path |
| (d) | Fresh full `install.sh` into an empty dir | `.claude/template-version` exists and equals `src/manifest.json`'s `.version` |
| (e) | `install.sh --only <cmd>` against an existing install | Marker not created; if one existed, byte-unchanged |
| (f) | Older `TARGET_VERSION` + `.devforge/lib` removed + non-tty stdin | Repair mode fires (version-independence — the D1 correction); helpers restored |
| (g) | Equal version + intact install + `--force`, stdin `</dev/null` | Full re-apply runs (files re-copied), exit 0 — **not** the D2 "nothing to do" no-op |
| (h) | Complete install + *differing* version + non-tty stdin, no `--force` | The OQ-1(b) refusal message is printed **on stderr** (`err`, not `warn`) and names `--force`; exit 1; nothing applied |
| (i) | Equal version + `.devforge/lib` **and** `.devforge/bin` both removed + non-tty stdin | Repair mode restores both; `.devforge/bin/chrome-devtools-mcp.sh` is present and executable |

Rows (h) and (i) were added during Phase 1, when OQ-1(b) and OQ-2 were folded in. **(h) asserts the stream, not just the text** — the `python-reviewer` pass caught the refusal going out on stdout via `warn` and rerouted it to `err`, so the assertion is stderr-specific. **(i) was run in a strengthened form**: `.devforge/bin/` is deleted before the run, so a restored executable `chrome-devtools-mcp.sh` is attributable to the new manifest pair and cannot be a file the fixture already had.

**Not mechanically covered:** the interactive-decline path (equal version, complete install, human answers `N`). A tty cannot be simulated in this harness; it is verified by code inspection only. Say so in the Phase-1 report rather than implying coverage.

### D5 — Docs reconcile scope

- `CHANGELOG.md` — one entry. **No version bump** — the bump is the maintainer's call, matching plans 49 / 56 / 65.
- Repo-root `CLAUDE.md` — add the plan-72 entry to the active-plans list, AND amend the plan-56 entry's OQ-1 clause at `CLAUDE.md:73` (*"no missing-helpers guard built"*) with a pointer that plan 72 closed it on the `update.sh` path. Leaving that sentence unqualified would make a future session believe no guard exists.
- `56-DEVFORGE-CODE-GITIGNORE-PLAN.md:89` — its OQ-1 resolution says *"No missing-helpers guard is built."* That is a historical decision record, so **add a back-pointer, do not rewrite the decision** — the same pattern plan 26 used when it superseded plan 21's D1.
- **Do NOT edit `done-plans/` archives.**
- If either script's usage text is touched, `install.sh`'s header Usage comment (`install.sh:18-19`) and `update.sh`'s usage block + `--force` help text (`update.sh:52-56`) must stay accurate. Repair mode is auto-detected, so neither *needs* a new flag line; a one-line mention of the auto-repair behavior in `update.sh`'s usage output is optional.

## Open questions

- **OQ-1 — RESOLVED (2026-08-12) → (b), implemented in Phase 1.** The refusal is printed by `err()` — i.e. on **stderr** — immediately before the `read`, and the run exits 1 (`update.sh:692-695`, inside the existing `if [ "$FORCE" != true ]` block); the exit code is unchanged from the pre-fix behavior, only the diagnosis is new. Scenario (h) is its net. Original analysis retained below. **The generic non-tty apply-confirmation remains.** After D1 + D2, one non-interactive failure path survives: a **complete** install with a **differing** version, run without `--force`, still dies at `update.sh:651-656` with exit 1 and a dangling `Apply these changes? [y/N]` line — Transcript B's exact shape, minus the repair-mode short-circuit that D1 gives the incomplete case. It is strictly less dangerous than the incident (the install works and the caller does get a non-zero exit; the tree is merely stale), but the failure is undiagnosable from the output. Three candidates: **(a)** auto-apply on non-tty — changes behavior for every existing scripted caller, and silently updates trees whose operator never confirmed; **(b)** message-only — detect `[ ! -t 0 ]` before the prompt, print an explicit "non-interactive and not `--force` — refusing to apply; re-run with `--force`", exit non-zero; this keeps today's exit semantics and only makes them legible, and needs the same pre-`read` guard shape D2 uses (under `set -euo pipefail` you cannot print *after* a failing `read`); **(c)** leave as-is. **Recommend: do not adopt (a).** The choice between (b) and (c) is the maintainer's — (b) costs roughly three lines and changes no exit code, (c) costs nothing and leaves the bare prompt. Document whichever is chosen in the Phase-3 CHANGELOG entry as known behavior. Resolve in Phase 0.
- **OQ-2 — RESOLVED (2026-08-12) → folded into Phase 1.** `.devforge/bin/` **is** now restorable: the manifest gained the pair `src/devforge/bin/** → .devforge/bin/**` (`src/manifest.json:10`) and `update.sh` gained the matching `chmod +x` block for `bin/*.sh` (`update.sh:725-735`), so a repair run restores `chrome-devtools-mcp.sh` executable instead of leaving `src/mcp.json`'s server entry dead. The block globs `*.sh` only — `bin/` is `.sh`-only by convention today, and the code carries a comment saying to widen the glob if that ever changes. The D1 sentinel was NOT widened to require `bin/` (see its rationale). Scenario (i) is its net. Original analysis retained below. **`.devforge/bin/` is not restorable by `update.sh`.** It is in plan 56's CODE class (gitignored + untracked, `src/files/devforge.gitignore:17`) but is absent from the manifest `templateOwned` set, so repair mode restores `lib` / `templates` / `command-refs` and **not** `bin`. Its one file, `chrome-devtools-mcp.sh`, is referenced by `src/mcp.json:15`, so a fresh-checkout install has a dead chrome-devtools MCP server entry until a full `install.sh` runs. Closing it is a manifest entry (`src/devforge/bin/** → .devforge/bin/**`) **plus** a `chmod +x` restore block mirroring `update.sh:677-681` — small, but a second work item with its own blast radius (every consumer update begins overwriting `bin/`). **Recommend: fold into Phase 1 as a clearly separated second edit if the maintainer wants repair mode to be complete; otherwise defer and state the non-coverage in the repair-mode warning text.** Resolve in Phase 0.

## Phases

### Phase 0 — Maintainer ratification (GATE)

Sign off on D1 (auto-detected, version-independent, `FORCE=true` mechanism, lib-only sentinel), D2 (non-tty "nothing to do", exit 0, `--force` never swallowed), D3 (install.sh stamp via python3, full-install only, fail-soft), D4 (scratch-fixture tests, seven scenarios, interactive path uncovered), D5 (docs scope) — plus the two drafting corrections and a stance on OQ-1 and OQ-2. **No edits before this gate clears.**

**Verify**: maintainer explicitly ratifies D1–D5 and resolves OQ-1 + OQ-2.

### Phase 1 — `update.sh`: repair guard + non-tty equal-version semantics (D1 + D2)

Single insertion between `update.sh:243` (drift check) and `update.sh:245` (bail):

1. Compute `INSTALL_INCOMPLETE` from the D1 sentinel. **`update.sh` runs under `set -euo pipefail` (`update.sh:9`)** — write the check so a no-match glob and a false test cannot abort the script. An `if`-guarded `[ -f "$f" ] && [ -x "$f" ]` loop over `"$TARGET_DIR/.devforge/lib/"*_helper` is errexit-safe (an `if` whose branch does not run returns 0); a bare `[ … ] && …` as the last command of a loop body is not. Both tests are required: D1's sentinel is an executable **file**, and `-x` alone is true for a directory. Mirror the existing glob idiom at `update.sh:702-704`, not its `&&` form.
2. If INCOMPLETE: two `warn` lines (splitting D1's example message into two `warn()` calls — wording may differ, content must not: one states the missing artifact, one states that the prompts are being skipped) and `FORCE=true`.
3. Rewrite the equal-version branch (`update.sh:245-253`) so that when versions are equal and the install is complete and `--force` was not passed and `[ ! -t 0 ]`, it prints the explicit "already on version X and the install is complete — nothing to do" line and exits 0 before the prompt. Nesting the new check inside the existing `if [ "$FORCE" != true ]` at `update.sh:247` satisfies the `--force` condition structurally. The interactive branch is unchanged.

Nothing downstream of `:253` changes. Route through `python-engineer` → `python-reviewer` (the repo's precedent for installer shell work, plans 49 / 56).

**Verify**: scratch scenarios (a), (b), (c), (f), (g) pass with recorded output — (g) is the `--force`-not-swallowed net for item 3. `grep -n 'FORCE' update.sh` shows the new assignment and no other new call site. A `--dry-run` on an incomplete install prints the repair warning and modifies nothing. Interactive-decline verified by inspection and reported as inspection-only.

### Phase 2 — `install.sh`: version stamp (D3)

Insert the stamp block between `install.sh:387` (git-hook template copy) and `install.sh:389` (the `Done.` echo): read `.version` from `$TEMPLATE_DIR/src/manifest.json` via `$PY_CMD`, write it to `$TARGET_DIR/.claude/template-version`, echo a one-line confirmation in the existing two-space install-log style. On a failed or empty read, echo a warning and skip. Same `python-engineer` → `python-reviewer` loop.

**Verify**: scratch scenarios (d) and (e) pass. `grep -n template-version install.sh` returns exactly the new block. A fresh install followed immediately by `update.sh` reports `Target version: <manifest version>` rather than `(unknown)`, and the changelog-excerpt gate at `update.sh:257` now behaves as designed.

### Phase 3 — Docs reconcile + cross-ref sweep (D5)

- `CHANGELOG.md` entry (no version bump).
- Root `CLAUDE.md`: add the plan-72 entry; amend the plan-56 entry's OQ-1 clause at `CLAUDE.md:73`.
- `56-DEVFORGE-CODE-GITIGNORE-PLAN.md:89`: back-pointer only.
- Cross-ref grep: `template-version`, `missing-helpers`, `OQ-1 → assumed install step`, `repair mode`, `--force`. Confirm no doc still asserts that a missing-helpers guard does not exist, and that no doc claims `install.sh` leaves the target unstamped.

**Verify**: the sweep returns no stale claim; both `CLAUDE.md` and `CHANGELOG.md` describe repair mode and the install stamp consistently; `done-plans/` untouched.

### Phase 4 — Post-fix end-to-end reproduction (mechanically runnable — NOT a consumer e2e)

**Baseline is already captured.** The broken-behavior transcripts were recorded on 2026-08-12 and live in the Problem section under *Reproduction transcripts (2026-08-12)*; Phase 4 does **not** re-run them. Its only job is the POST-fix half — proving the fixed `update.sh` restores helpers non-interactively where the pre-fix script died at the prompt.

**Deliberate departure from this repo's usual user-driven testForge20 gate**: the incident is fully reproducible in a local fixture, so there is no reason to defer verification to a consumer install. Script it:

1. Create a scratch dir, `git init`, run a full `install.sh` into it (post-Phase-2, so it is stamped).
2. `git add -A && git commit` — the CODE dirs are gitignored + untracked by `forge_migrate_devforge_state`, so the commit carries the VERSIONED artifacts and `.claude/template-version` and **no** helper code. This is the "setup commit" shape.
3. Fresh-clone that repo to a second scratch dir. Confirm `.devforge/lib` is absent — the incident state.
4. Run `update.sh <clone>` with stdin closed (`< /dev/null`), no `--force`.
5. Assert: repair-mode warning printed; `.devforge/lib` present with ≥1 executable `*_helper`; `.devforge/command-refs/` re-emitted; exit 0.
6. Sanity: `.devforge/lib/research_helper --help` (or the launcher's no-arg usage) runs — i.e. the exact failure the incident reported is gone.

Record the post-fix transcript in this plan under a `## Reproduction (post-fix)` heading, beside — not replacing — the baseline transcripts in the Problem section.

**Verify**: step 4's run restores helpers and exits 0, where the pre-fix script died at the equal-version prompt with exit 1 (Transcript A); re-running the same command a second time hits the D2 "nothing to do" path (complete install, equal version, non-tty, no `--force`) and exits 0 without touching the tree.

## Reproduction (post-fix)

Run 2026-08-12, after Phases 1 + 2 landed. This is the POST-fix half only — the pre-fix baseline lives in the Problem section under *Reproduction transcripts (2026-08-12)* and was not re-run.

**Fixture chain** (scripted, following Phase 4's steps):

1. Full `install.sh` into a `git init` scratch dir — stamped `2.0.8` by the Phase-2 stamp.
2. `git add -A` + commit → the commit carried **75 files and zero `.devforge/lib` entries**; the plan-56 gitignore held. This is the "setup commit" shape.
3. Fresh clone of that repo → `.devforge/lib` **absent**. This is the incident state.
4. `./update.sh <clone> </dev/null` — no `--force`.

**Result: exit 0**, both repair warnings printed:

```
⚠  Install incomplete — .devforge/lib has no executable *_helper launcher.
⚠  Skipping confirmation prompts and repairing the install now (REPAIR MODE).
```

**Post-run assertions, all passing:**

- 24 executable `*_helper` launchers restored under `.devforge/lib/`.
- 11 `.devforge/command-refs/` directories re-emitted.
- `.devforge/bin/chrome-devtools-mcp.sh` restored and executable — the OQ-2 fold-in.
- `.devforge/lib/research_helper` runs and prints its usage. The exact incident failure (`no such file or directory: .devforge/lib/research_helper`) is gone.

**Second identical run: exit 0**, printing `Target is already on version 2.0.8 and the install is complete — nothing to do.` — the D2 no-op, reachable precisely because the first run made the install complete.

**Contrast with the baseline**: on this same shape the pre-fix script died at the equal-version prompt with exit 1 and a dangling `Continue anyway? [y/N]` line, restoring nothing (Transcript A).

**Benign residue, not a defect**: the repair leaves `.claude/template-manifest.json` untracked in the clone. It is a normal `update.sh` `templateOwned` deliverable (`src/manifest.json:8`) that the setup commit never contained — a new untracked file after an update, not a failure of one.

## Context for next session

- The fix is **two shell edits + a docs pass**. No Python helper change, no command-spec change, no `.claude/`-shipped file — so **no** `instruction-author` / `instruction-reviewer` / `claude-code-guide` loop is required for Phases 1–2 (`python-engineer` → `python-reviewer` is the loop, per plans 49 / 56).
- **The two-gate fact is the crux**: `update.sh:245-253` (equal-version bail) AND `update.sh:651-656` (apply confirmation) both `read -r confirm`. Non-interactively the script **dies at whichever it reaches first** — exit 1 under `set -euo pipefail`, no `Aborted.` line (reproduced 2026-08-12, transcripts in the Problem section); interactively both default to N → `Aborted.`, exit 0. Either way nothing is restored, and a fix that clears only the first restores nothing.
- **Repair mode is version-independent** — an incomplete install with an *older* version reproduces the incident too, at the apply confirmation instead of the bail (Transcript B). Do not re-couple the trigger to version equality.
- **The mechanism is `FORCE=true`**, not new conditionals: `FORCE` already gates both prompts (`update.sh:247`, `update.sh:652`) and nothing else reachable from the guard site (`update.sh:120` lives in the `--only` branch, which exits at `update.sh:194`). The corollary for D2: its non-tty "nothing to do" branch must itself be `--force`-conditioned, or `--force` gets swallowed instead of re-applying.
- **The sentinel is lib-only**: `.devforge/lib` present AND ≥1 top-level executable `*_helper` **file** (`-f` and `-x`, since `-x` alone passes for a directory). Not `bin/` — narrowness, not impossibility: OQ-2 made `bin/` restorable and the repair run restores it, so requiring it in the *trigger* would add no recovery. Not a `command-refs/` count (11 of 20 commands have references). Partial `lib` corruption is deliberately uncovered — see the sentinel rationale.
- **Every `update.sh` / `install.sh` line number in this plan is a PRE-fix anchor** and has shifted: Phase 1 inserted the repair guard ahead of the equal-version bail and Phase 2 inserted the stamp block. Post-fix anchors for the load-bearing sites — repair guard `update.sh:248-269`, equal-version branch + D2 no-op `update.sh:271-287`, apply confirmation + OQ-1(b) refusal `update.sh:686-699`, `bin/` exec-bit restore `update.sh:725-735`, install stamp `install.sh:389-406`. Re-grep rather than trusting any other number here.
- **No new copy logic anywhere** — `update.sh:661-666` already `mkdir -p` + `cp`s missing files, `update.sh:702-704` restores the exec bits, `update.sh:971` re-emits `command-refs/`.
- `update.sh` runs under `set -euo pipefail` (`update.sh:9`); `install.sh` does not (`install.sh:1`). Write each edit to its own script's error discipline.
- Out of scope by decision: the eval harness's setup commit, a command-runtime guard, `install.sh` copy logic (the configure-overwrite is designed behavior), the plan-44 drift check and its ordering.

## When resuming work

**Phases 0–4 are complete** (see **Status**) — there is no pending work in this plan and no deferred e2e. What stays live is the accuracy of the claims it made elsewhere:

1. `CHANGELOG.md` (the plan-72 entry) and the repo-root `CLAUDE.md` plan-72 entry both describe repair mode, the D2 no-op, the OQ-1(b) stderr refusal, the `bin/` restore, and the install stamp. If either script changes, they change with it.
2. `56-DEVFORGE-CODE-GITIGNORE-PLAN.md:89` and the repo-root `CLAUDE.md` plan-56 entry carry back-pointers saying plan 72 closed plan 56's OQ-1. The closure is **`update.sh`-only**: a fresh clone that runs neither installer still has no helpers, and `install.sh` needs no completeness guard because it copies unconditionally. Do not widen either back-pointer into "the missing-helpers gap is closed everywhere."
3. Before widening the D1 sentinel past its lib-only shape, re-read the sentinel rationale — both exclusions are reasoned, and the `bin/` one changed reason once already (OQ-2).
4. The version was NOT bumped. The `CHANGELOG.md` entry sits under `## [Unreleased]`; the maintainer's release pass folds it into the next version heading.
