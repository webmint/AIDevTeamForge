# 44 — Constitution Drift Wiring Plan

**Status:** **✅ DONE (build) 2026-06-25** — Phases 0–4 shipped + committed on `develop-2.0-init`. **Phase 5 (testForge20 + mintEnvoy e2e) DEFERRED to user validation** (maintainer will validate later; not blocking). Phase 0 ratified: D1 warn-only (no auto-stub), Option C (OQ3) deferred, OQ1 greenfield silent-skip, OQ2 summarized warning. Phase 1+3 = `scripts/constitution-drift-check.sh` (`forge_check_constitution_drift`) sourced by `update.sh` (before the equal-version bail) + `install.sh`'s brownfield branch. Phase 2 = `constitute_helper forge-internal:verify-forcing-function-keys` (15 tests; 220 `_constitute` suite green; python-engineer→python-reviewer, 4 findings applied). Phase 4 = CLAUDE.md row + CHANGELOG + this status reconciled. Build-verified (verb exit codes, smoke-tested synthetic mintEnvoy reproduction, `bash -n` clean); NOT yet runtime-validated against a real install.
**Branch:** `develop-2.0-init`.
**Discovered:** 2026-06-25, auditing whether the 2.0.1 update fully landed in a consumer install (mintEnvoy). Code landed clean; the **constitution + forcing-functions config did not** — and nothing surfaced the gap. Found by gut, not by tooling.

---

## Problem

The constitution holds **framework-owned universal law** (§3.5 Universal Code Quality, §3.6 Design Principles, §3.7 Check Before You Build, §3.8 Design Fidelity, §4.1–4.3 Patterns & Anti-Patterns universal rules, §6.1–6.4 refactoring principles) **inside a user-owned, presence-guarded document** (`<root>/constitution.md`, placed once by `install.sh:238` and never touched again).

Both delivery scripts refuse to overwrite it by design (brownfield safety):
- `install.sh:238` — `if [ ! -f "$TARGET_DIR/constitution.md" ]` → place, else the brownfield-skip echo at `install.sh:241` ("existing constitution.md detected — leaving as-is").
- `update.sh` — **(pre-fix state)** had **zero** references to `constitution.md`; never delivered or checked it. **FIXED by Phases 1+3 of this plan:** it now sources `scripts/constitution-drift-check.sh` and WARNS on drift before the equal-version bail — but still delivers/overwrites nothing (warn-only, zero mutation).

Same blind spot for the machine config: `.devforge/constitute.json`'s `forcing_functions` block is `/constitute`-generated, never install/update-placed — so a detector added to the framework schema after a project was constituted (e.g. plan 40's `design_token_provenance`) never appears in that project's config.

**Consequence:** when the framework adds new universal law or a new forcing-function rule, every already-installed project silently stays stale across all future version bumps. The enforcement code ships (lib/helpers/detectors all land via the normal `cp -R`), but the **law that activates it and the config that enables it do not** — the code is installed but inert.

**Concrete instance (mintEnvoy, 2026-06-25):** on `template-version 2.0.1` with all commands/agents/lib byte-current, yet:
- `constitution.md` from a much older template — no §3.7, no §3.8, drifted §3.5/§3.6 universal content; `forge-internal:verify-universal-defaults` reports **~30 MISSING** universal rules across §3.5/§3.6/§3.7/§3.8/§4/§6.
- `constitute.json.forcing_functions` carries only the 3 original detectors (all `enabled:false`); the `design_token_provenance` key is **absent entirely**.
- The irony: mintEnvoy is the *exact* design-drift project that **motivated plan 40**, and none of plan 40's constitutional/config layer reached it.

## The tooling already exists — it is just unwired

The drift detector was **built and validated** in the 18-May patch cycle (CONSTITUTION-DRIFT-DETECTOR — `forge-internal:verify-universal-defaults`, validated on testForge20 with exit 2 + 29 MISSING findings). It:
- takes `--consumer-path <root>` + `--canonical-path <constitution.md>`,
- diffs the consumer's `.devforge/constitute.json` universal sections vs the canonical `constitution.md` named by `--canonical-path`,
- prints `MISSING §X.Y [Rule]` lines + a JSON findings array, exits non-zero on drift.

**The only gap is that nobody runs it on the consumer at update time.** It is namespaced `forge-internal:` and wired into no script. This plan wires it in. It does **not** build new detection from scratch — it closes a wiring gap around validated tooling.

---

## Proposed mechanism (WARN-ONLY, zero mutation)

At update time (and the install-brownfield-skip path), **detect drift and warn**; never edit user content. The human applies the refresh by re-running `/constitute`. Two symmetric checks:

- **A — universal-section drift.** Run the existing `forge-internal:verify-universal-defaults` against the target, with the canonical path pointed at the freshly-shipped template constitution (`$TEMPLATE_DIR/src/constitution.md`). On any MISSING/DRIFTED finding, print a loud, bounded warning naming the drifted sections and telling the user to re-run `/constitute`.
- **D — forcing-function key drift.** A new lightweight helper verb compares the consumer `constitute.json.forcing_functions` keys against the canonical rule set (`_constitute/_schema.py::FORCING_FUNCTION_RULES`). On any schema rule absent from the consumer config, warn (naming the missing rules) and point at `/constitute` Section 3.5.

Both are advisory. Both fail-soft (a check error warns "drift check skipped" and never aborts the update). Neither mutates `constitution.md` or `constitute.json`.

---

## Decisions (proposed — ratify in Phase 0)

- **D1 — Warn-only, never auto-merge.** Programmatic merge into `constitution.md` is unsafe: section numbers already collide across template generations (mintEnvoy §3.5 "Documentation" vs canonical §3.5 "Universal Code Quality"). The detector finds drift; the human applies it via `/constitute` re-synthesis. *(Rejected: auto-merge universal sections; auto-inject disabled forcing-function stubs — both mutate user content silently.)*
- **D2 — Reuse `forge-internal:verify-universal-defaults` as-is, no consumer alias.** `update.sh`/`install.sh` are framework code; invoking a `forge-internal:` verb from them is in-bounds. The user-visible warning text is composed by the shell script, not the verb name, so the namespace never leaks to the user. *(Rejected: a cosmetic `check-constitution-drift` alias — YAGNI.)*
- **D3 — Wire into BOTH `update.sh` and `install.sh`'s brownfield-skip branch.** Update is the primary cadence (drift only appears across versions). But reinstall-over-existing hits the same presence guard and the same blind spot, so the brownfield "leaving as-is" branch must warn too. Factor the warning into one shared shell snippet to keep them identical. *(This is why "just reinstall" does not fix the problem — confirmed 2026-06-25.)*
- **D4 — Oracle is `constitute.json`, document is `constitution.md`; accept the asymmetry, name it.** The detector compares the config snapshot (`constitute.json`), not the rendered root document. A user who hand-edits `constitution.md` without re-running `/constitute` would diverge from their own config. For drift-at-update this is acceptable — `constitute.json` is the framework's tracking state and the input `/constitute` re-renders from. Documented as a known limitation, not solved here.
- **D5 — Fail-soft.** Any check failure (missing `constitute.json` on a not-yet-constituted target, parse error, helper non-zero for a non-drift reason) prints "constitution drift check skipped: <reason>" and continues. The drift check must never block an update.
- **D6 — `forcing_functions` key-drift check is a new helper verb, not inline shell.** Per the repo's helper-owns-shape discipline + test-first rule, the schema-vs-config key diff belongs in `_constitute/` with its own test, not as `jq`/`grep` in `update.sh`. The verb prints missing rule keys + exits non-zero on drift; the shell composes the warning.

## Open questions (resolve in Phase 0)

- **OQ1 — Greenfield/not-yet-constituted targets.** If `.devforge/constitute.json` is absent (installed but `/constitute` never run), A and D both no-op silently (nothing constituted = nothing to drift). Confirm silent-skip is the wanted behavior (vs an info line "constitution not yet synthesized").
- **OQ2 — Warning verbosity cap.** mintEnvoy produced ~30 MISSING lines. Cap the per-section detail in the shell warning (e.g. summarize "§3.7, §3.8 and 4 other sections drifted — N rules missing") with the full list behind the raw verb output? Or print all? Lean: summarize sections + count, point at the verb for detail.
- **OQ3 — Deeper structural fix (Option C) scope.** Split the universal sections out of the user-owned document into a framework-owned file that `update.sh` *does* overwrite (like lib), leaving only project-specific sections presence-guarded. This kills the drift class entirely instead of warning about it. It is a real refactor (two files, agents read both, a migration for existing installs) and is explicitly **out of scope here** — this plan is the cheap safety net. Decide whether C becomes its own follow-on plan now or is deferred pending evidence the warn-only net is insufficient.

---

## Phases

### Phase 0 — Ratify (maintainer sign-off gate)
Confirm D1–D6, resolve OQ1–OQ3. No code until signed off. Argue the warn-only stance (D1) vs any appetite for auto-stubbing the forcing-function keys — the one place auto-mutation is behavior-neutral, since an `enabled:false` stub changes no enforcement. If the maintainer wants discoverability over purity here, D1's rejected "auto-inject disabled forcing-function stubs" alternative is revisited at this gate; the proposed default remains warn-only.

### Phase 1 — Universal-section drift check in `update.sh` (Option A)
Once `TEMPLATE_VERSION`/`TARGET_VERSION` are read but **before** the equal-version bail at `update.sh:189` (per the sharp edge), run `forge-internal:verify-universal-defaults --consumer-path "$TARGET_DIR" --canonical-path "$TEMPLATE_DIR/src/constitution.md"` against the installed `.devforge/lib/constitute_helper`. On non-zero/findings, print a bounded warning (per OQ2) naming drifted sections + "re-run `/constitute` to apply." Fail-soft per D5.
**Verify:** run `update.sh` against a copy of the mintEnvoy install (a `2.0.1` target — the equal-version path) → warning fires, names §3.7/§3.8 + others, the equal-version bail still reports "already on version", update completes exit 0. Run against a current/clean install → no warning.

### Phase 2 — Forcing-function key-drift verb (Option D, helper side)
New `constitute_helper` verb (e.g. `forge-internal:verify-forcing-function-keys --consumer-path <root>`) diffing `constitute.json.forcing_functions` keys vs `_schema.py::FORCING_FUNCTION_RULES` (`_schema.py:45`). Prints missing rule keys, exits non-zero on drift. Built python-engineer → python-reviewer, test written + run same turn (round-trip via a real `constitute.json` fixture, not hand-authored).
**Verify:** against mintEnvoy → reports `design_token_provenance` missing, exit non-zero. Against a config carrying all schema keys → exit 0.

### Phase 3 — Wire Phase-2 verb into `update.sh` + share with `install.sh` brownfield path (Option D shell + D3)
Call the Phase-2 verb alongside Phase 1; compose a combined "constitution out of date" warning. Factor both checks into one shared shell function/snippet sourced by `update.sh` and `install.sh`'s brownfield "leaving as-is" branch (`install.sh:241`).
**Verify:** reinstall over the mintEnvoy copy → same warning fires from the brownfield branch; fresh install into an empty dir → no warning (constitution placed fresh, no drift).

### Phase 4 — Docs reconcile
CLAUDE.md "Where to find what" (forcing-functions / constitution row — note the update-time drift check + the new verb), CHANGELOG entry, and this plan's status. Cross-ref sweep for any text claiming `update.sh` never touches the constitution (now false in spirit — it still places/overwrites nothing, but it warns on drift).
**Verify:** grep sweep clean; CHANGELOG entry present.

### Phase 5 — testForge20 + mintEnvoy e2e (user-driven, HARD GATE)
Run the wired `update.sh` against testForge20 and the mintEnvoy install; confirm the warning fires with accurate section/rule names and the update completes. Then run `/constitute` on mintEnvoy and re-run the checks → drift clears (closes the original gap).

---

## Context for next session
- The detector (`forge-internal:verify-universal-defaults`) is `cmd_verify_universal_defaults` at `src/devforge/lib/_constitute/_cmds_quality.py:128`; registered in `_constitute/_cli.py:515`; canonical section list `_UNIVERSAL_SECTIONS` defined at `_constitute/_schema.py:294`, consumed in `_constitute/_universal.py`. It reads consumer `.devforge/constitute.json`, not root `constitution.md` (D4).
- Forcing-function canonical rule set: `_constitute/_schema.py::FORCING_FUNCTION_RULES` (`_schema.py:45`, a `frozenset`) — the Phase-2 diff's comparison target. The verb map `_constitute/_forcing_functions/_setters.py::RULE_TO_VERB` is asserted key-equal to it at `_setters.py:64`, so its keys are an equivalent oracle if convenient. Consumer config: `.devforge/constitute.json` `forcing_functions` block.
- `update.sh` version logic: `TEMPLATE_VERSION`/`TARGET_VERSION` compared at `update.sh:189` (`if [ "$TEMPLATE_VERSION" = "$TARGET_VERSION" ]`); on equal versions it warns "already on version" and, absent `--force`/`$FORCE`, exits. The drift check must run **before** this bail so it covers both the versions-differ path and the versions-equal path.
- **Sharp edge:** the `update.sh:189` equal-version bail exits before any later step runs. mintEnvoy proves drift is possible *at equal version* — it is on `2.0.1` with all code byte-current yet fully drifted, because its original install predates a universal-section change shipped within the 2.0.x line. So the drift check cannot sit after the bail; it runs **before** it (and before any `--force` short-circuit), or a same-version-but-drifted install is never caught. This placement is proposed, not settled: Phase 0 ratifies it, Phase 1 implements it.

## When resuming work
Read this file in full. Phase 0 is a hard gate — do not write code before D1–D6 + OQ1–OQ3 are signed off. Phases 1+3 are shell (`update.sh`/`install.sh`); Phase 2 is a helper verb (python-engineer → python-reviewer, test-first). Any user-facing warning wording that ships is framework-internal shell, not a `.claude/` artifact — no instruction-author/claude-code-guide loop required, but keep the wording terse + actionable.
