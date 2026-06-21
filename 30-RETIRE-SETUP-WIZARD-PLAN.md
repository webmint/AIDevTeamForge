# 30 — RETIRE /setup-wizard

**Status**: DRAFTED 2026-06-21, not started. Split out from `29-…-SINGLE-ROOT-PLAN.md` Workstream C when the onboard retirement shipped: `/onboard` retired cleanly, but `/setup-wizard` cannot be deleted by removal alone — it still carries two live responsibilities that must be MIGRATED first. The user chose "retire fully" (2026-06-21); this plan is the migration that makes a clean deletion possible.

## Why setup-wizard can't just be deleted (investigated 2026-06-21)

`/setup-wizard` is already de-promoted (not in emitter `_PROMOTED`; the emitter docstring says it "no longer ships into target projects"). But the source tree + helper are KEPT because two things still depend on them:

1. **`scripts/generate-agents.py` reads `src/commands/setup-wizard/references/agents.md` (§6.4) as its generator spec source** (`generate-agents.py:32,161`). `install.sh` runs `generate-agents.py` to lay down `.claude/agents/`. Delete `setup-wizard/` and agent generation breaks. The agents.md spec must be RELOCATED to a stable home and `generate-agents.py` repointed first.
2. **`/setup-wizard` is the documented "install / restore a missing agent" user entry point**, referenced by four command specs: `audit/main.md` ("run `/setup-wizard` to install at least one"), `fix/main.md`, `grill/main.md`, `review/main.md` (all "run `/setup-wizard` to install the missing agent"). In 2.0 there is NO command that installs/restores agents — `install.sh` + `generate-agents.py` GENERATE them and `/configure prune-agents` only PRUNES. So the replacement instruction is an open decision (deferred from plan 29; see Open Question 1).

Helper + tests to delete once the above are migrated: `src/devforge/lib/wizard_render.py` + `wizard_render` launcher + `tests/lib/test_wizard_render.py` (confirm no consumer beyond the setup-wizard command + install.sh comments — verified 2026-06-21: only those reference it).

## Open questions (resolve before execution)

1. **Agent-restore instruction (deferred from plan 29).** When `audit/fix/grill/review` need a missing agent restored, what should they tell the user to run? Candidates: re-run `install.sh` / `update.sh` (these actually regenerate `.claude/agents/` via `generate-agents.py` — most accurate); `/configure` (WRONG alone — it only prunes, never restores). Likely answer: point to `update.sh` (re-emits + regenerates without clobbering project state). Confirm.
2. **New home for `agents.md` (the generate-agents.py spec).** Options: move to `src/agents/` (alongside the agent sources it governs), or a new `src/generators/` location, or inline into `generate-agents.py`'s own reference dir. Pick one, relocate, repoint `generate-agents.py:32,161`, and re-verify a clean `install.sh` produces identical `.claude/agents/`.

## Scope (the full retirement, once OQs resolved)

1. Relocate `src/commands/setup-wizard/references/agents.md` → chosen home; repoint `generate-agents.py`; verify agent generation byte-identical (diff `.claude/agents/` before/after on a scratch install).
2. Repoint the four `/setup-wizard`-as-agent-installer references (`audit`, `fix`, `grill`, `review` `main.md`) to the OQ-1 answer (instruction-author + instruction-reviewer).
3. Delete `src/commands/setup-wizard/`, `src/devforge/lib/wizard_render{,.py}`, `tests/lib/test_wizard_render.py`.
4. `scripts/lib/command_source.py` — replace the `setup-wizard` docstring EXAMPLES (lines ~6,59,114) with a surviving dir-shaped command (e.g. `init-forge`); cosmetic but removes dangling references.
5. `src/devforge/lib/detect_report.py` — docstring (lines ~1,4,7,1205) frames it as "for /setup-wizard"; reword to its 2.0 role (per-command detection helper) — detect_report itself is KEPT.
6. `src/manifest.json` — remove the `setup-wizard.md` entry (legacy flat-file mapping).
7. `src/CLAUDE.md` — remove the `/setup-wizard` "Additional Commands" entry.
8. `src/docs/overview.md` — the "The setup wizard fills in the name and description from Phase 2 answers" line is stale (2.0: `/init-forge` captures + `/configure` substitutes `{{PROJECT_NAME}}`/`{{PROJECT_DESCRIPTION}}`); reword.
9. README.md + DEVELOPMENT-STATUS.md — remove the remaining `setup-wizard` prose (README setup-section already moved to the 2.0 chain in plan 29; sweep for residual mentions). DEVELOPMENT-STATUS `setup-wizard.md` bullet (line ~10) + scattered "setup wizard" references.
10. Emitter docstring — drop the "kept pending its own retirement" note once done.
11. Verify: scratch `install.sh` + `update.sh` succeed; `.claude/agents/` identical; repo-wide `setup-wizard` / `wizard_render` sweep returns only `.vault/`, CHANGELOG history, and plan files.

## Related debt surfaced (NOT this plan, but note it)

README.md + DEVELOPMENT-STATUS.md carry broader pre-2.0 staleness beyond setup-wizard/onboard — e.g. `/execute-task` (renamed `/implement`), `docs/features/*` (dropped tier), setup-wizard-centric workflow prose. A dedicated **2.0 docs refresh** of those two files is warranted; fold into this plan or track separately.

## When resuming work

Resolve both Open Questions FIRST (they gate everything). Then do scope step 1 (relocate the generator spec) and re-verify agent generation before any deletion — that dependency is the one that breaks the build if mishandled. Re-confirm all cited line numbers against the live tree before editing.
