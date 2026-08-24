# 30 — RETIRE /setup-wizard

**Status**: SHIPPED 2026-06-21 (working tree). Both "blocker" Open Questions DISSOLVED on investigation — neither migration was actually needed:
- **OQ2 (generator-spec relocation) — DISSOLVED**: `generate-agents.py` reads `src/agents/*.md` (line 4, 260 `args.src.glob("*.md")`), NOT `setup-wizard/references/agents.md`. Lines 32/161 were stale COMMENT pointers to a file that *no longer existed*. No relocation — just dropped the dead comments. Agent generation is fully independent of setup-wizard (verified: scratch `install.sh` + `update.sh` both regenerate 18 agents with setup-wizard gone).
- **OQ1 (agent-restore wording) — RESOLVED to `update.sh`**: `update.sh` runs `generate-agents.py` (line 715) → regenerates `.claude/agents/`. The four command specs (`audit`/`fix`/`grill`/`review`) now say "re-run `update.sh`" instead of "run `/setup-wizard`".
- **OQ1 (agent-restore wording) — AMENDED 2026-08-24**: the resolution above rested on a premise that is only half-true, so the wording it produced was wrong for the common case. `update.sh` does run `generate-agents.py`, but a regenerated agent only LANDS through one of three branches, and an agent that WAS installed and was later deleted from `.claude/agents/` falls through all three: the `generated:agents` three-way merge walks the snapshot at `.devforge/template/.claude/agents/` and emits work for an agent ONLY when that file also exists live in the target, so a deleted one is silently skipped (and, unlike the other templateDerived entries, it is never queued as a MISSING/add either); `NEW_AGENTS` is the current `src/agents/` roster MINUS the snapshot, and a previously-installed agent IS in the snapshot; `REMOVED_AGENTS` is the snapshot MINUS the roster, and an agent the framework still ships IS in the roster. Plan 72's repair guard does not reach it either — its sentinel is a missing executable `.devforge/lib/*_helper` launcher, and tripping it only forces past the confirmation prompts; it adds no agent-restore path. The real remedies are `install.sh` (which regenerates every agent, and also overwrites `.claude/settings.json`) or hand-copying the file into `.claude/agents/`, and every agent-restore site in the four command specs named above (`audit`/`fix`/`grill`/`review`) was corrected to say exactly that on 2026-08-24. A fourth `RESTORE` branch in `update.sh` — deliver a roster agent that is present in the snapshot but missing from the live target — was CONSIDERED and DECLINED as disproportionate for this repo's install population (a few local v2 installs, never shipped at scale); the revival trigger is **v2 shipping to installs the maintainer does not control**. The OQ1 bullet above is left byte-unchanged as the record of what was decided then.

Done (verified: emitter test 9 OK; scratch install exit 0 = 18 agents, no setup-wizard command, no wizard_render shipped; update exit 0 = 18 agents regenerate):
- Deleted `src/commands/setup-wizard/` + `src/devforge/lib/wizard_render{,.py}` + `tests/lib/test_wizard_render.py`.
- `generate-agents.py`: dropped the 2 dead `agents.md §6.4` comment pointers (generalized "wizard" → "post-install config step").
- `src/manifest.json`: removed the `setup-wizard.md` entry.
- `scripts/lib/command_source.py`: docstring examples `setup-wizard` → `audit`.
- `src/devforge/lib/detect_report.py`: docstring reworded — ORPHANED (its sole consumer setup-wizard is gone; flagged dead-code, see below).
- `scripts/emitters/claude.py` + `install.sh`: retirement notes / dropped wizard_render from comments.
- Repointed (instruction-author + instruction-reviewer loop): 4 command specs agent-install refs → `update.sh`; `src/CLAUDE.md` removed the `/setup-wizard` catalog entry; `src/constitution.md` + `src/docs/overview.md` shipped-template header/name provenance → `/init-forge`+`/configure`; README + DEVELOPMENT-STATUS de-wizared (setup section → 2.0 chain, mechanism prose reattributed to `/configure` / `install.sh` / generalized).
- `.claude/agents/instruction-author.md`: repointed the AskUserQuestion-contract + phase-numbering anchors off the deleted `setup-wizard/main.md` (review F2).
- Path fix (review F1): `.claude/project-config.json` → `.devforge/project-config.json` in DEVELOPMENT-STATUS. Wrapper-gitignore staleness fix (F3): `install.sh --wrapper` → `/init-forge` STEP 0.

**Follow-ups NOT done here:**
- `detect_report.py` (+ `tests/lib/test_detect_report.py`) is now ORPHANED dead code (zero functional consumers) — its own docstring authorizes removal "when /setup-wizard is decommissioned". A dedicated deletion pass is warranted (left in place this commit to avoid scope-creeping a 42KB+helper+tests deletion the user didn't explicitly greenlight).
- **2.0 docs refresh** (the original "Related debt" below): README + DEVELOPMENT-STATUS still carry non-wizard pre-2.0 staleness — `/execute-task` (now `/implement`), `docs/features/*` (dropped tier), stale command/agent counts. The wizard-scrub touched these files but deliberately did NOT chase the broader staleness.

---

### (original draft preserved below for rationale)

Split out from `29-…-SINGLE-ROOT-PLAN.md` Workstream C when the onboard retirement shipped: `/onboard` retired cleanly, but `/setup-wizard` was *believed* to carry two live responsibilities. (Investigation 2026-06-21 showed both were already vestigial — see Status above.)

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
