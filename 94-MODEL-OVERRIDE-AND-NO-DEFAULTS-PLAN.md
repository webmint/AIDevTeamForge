# 94 — Commands run on the tier's model, and the framework ships no model of its own — the override plan 92 deferred, and the defaults it should not have had

**Status:** **✅ DONE (build) 2026-09-04 — Phases 0–3; Phase 4 consumer e2e DEFERRED (user-driven HARD GATE, NOT run; build-verified, NOT consumer-validated).** Phase 0 closed by a single blanket maintainer directive, every item ratified AS RECOMMENDED; commits `c950d7b` (draft) / `36e05b7` (Phase 0 close) / `5d3e134` (Phase 1 code) / `db6088f` (Phase 2 instructions), with the Phase-3 docs commit carrying the three build records. Every decision keeps its recommendation, its alternatives with the reason each is rejected, and its honest bound — **and ratification changed none of them.** ⚠ **The closure came as ONE directive and no per-item deliberation was supplied** — see `## Phase 0 close record`, which says so plainly rather than implying thirteen separate arguments were had. **Ratifying a recommendation does not strengthen it**, and a build that reads a ratified bound as discharged has left this plan.

- **This plan is the direct sibling of `92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md`, and it AMENDS that plan in place.** Plan 92 stays **DONE (build)** — no phase of it is re-opened, no build record of it is edited. What changes there are dated amendment notes at the four sites this plan falsifies (D6), on the house precedent that plan 85 used to amend plan 23 and plan 82 used to amend plan 62.
- **The evidence is TWO maintainer directives and ONE inherited, locally-reproduced mechanical finding. There is no consumer incident and none is claimed.** The directive half is a predicted-gap feature in plan 87's class. **Say both halves wherever this plan is summarized** — see `## Evidence constraint`.
- **Phase 4 is a user-driven consumer e2e HARD GATE and it is the ONLY place the override is ever observed working.** Nothing in the build can see a turn-scoped model override take effect; a green suite proves the files were written, never that the turn ran on the model they name.

**Branch:** `develop-2.0-init`
**Created:** 2026-09-04.

This plan document contains no private-client identifiers and is intended to be **committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

**Two maintainer directives, dated 2026-09-04, given in one line after reading plan 92's closing report** (`## Origin` carries them verbatim). **No consumer run failed, nobody reported a wrong model on a wrong tier, and nothing here has been measured.**

Beside them sits **one inherited mechanical finding that IS verified**: plan 92's Phase-3 build record item (c) reproduced, locally, that a three-way merge of base `opus` / current `fable` / other `sonnet` **conflicts**, that `update.sh` then leaves the whole agent file unchanged **body included**, that its snapshot goes stale, and that the condition **recurs on every later update** while the post-merge apply makes the `model:` line read correct. **That is a local reproduction, not a consumer observation** — and it is the reason directive (2) is a repair rather than a preference. **D2's transition sub-part is the one part of this plan standing on reproduced mechanics; everything else stands on a directive.**

**Model-behavior facts** — the vendor's documented refusal risk for security-focused analysis, relative pricing, and turn length — live in plan 92's `## Model facts`, cached 2026-06-24. **They are decision inputs for D3 and they never reach `src/` in any priced, dated or version-bound form.** This plan does not restate them with numbers, and its `src/` edits must not either.

---

## Origin — two directives in one line, 2026-09-04

**The day after plan 92's build landed** (its five build commits are dated 2026-09-03), after reading its closing report, the maintainer wrote, verbatim, in Ukrainian:

> *"оу оце треба правити! так і задумавалося з початку! це про оверайт моделі. Про ресідуал - дефолтів не має бути це має обирати користувач"*

Translated: **(1)** the command-scoped model override *"is what was intended from the start"* — build it; **(2)** *"about the residual — there must be no defaults, the user chooses."*

**What directive (1) does to plan 92.** It **RESOLVES plan 92's OQ-5 in the affirmative.** That OQ recorded a real fork — a command's own frontmatter may carry `model:` and `effort:`, which would make `/devforge:plan` and its peers actually RUN on the configured tier's model rather than print a recommendation about it — and the maintainer's 2026-09-03 pick was *keep the advisory, treat the override as a separate decision.* **This plan is that separate decision, and it takes the arm plan 92 declined.** Its four recorded costs map one-for-one onto what follows: **(a)** the apply twin over commands is D1's rule; **(b)** overriding the user's own model choice is D1's bounds (i) and (iii), with OQ-3 asking whether an unanswered tier should block; **(c)** the interaction with plan 93's model-invocable commands is D1's bound (iii); **(d)** `effort` overriding the session's level is D5.

**What directive (2) does to plan 92.** It **REVERSES plan 92 D2 half 1** — the static per-tier default map, duplicated in `scripts/lib/install_defaults.py` and `src/devforge/lib/_configure/_agent_models.py` and pinned equal by a maintainer test. It **dissolves plan 92's Trap 3 by construction**: with no static default there is no framework-owned value on the `model:` line to change, so the merge-conflict class that trap names cannot recur. And it **turns plan 92 D6's `security-reviewer` pin from a framework choice into a user question** — a pin is a default with one member, and directive (2) does not exempt it.

⚠ **Directive (2) is a stance, not a bug report.** Nothing observed a framework default doing harm. What was observed — and only locally — is the merge behavior above, which the defaults make possible. **A summary that reports "the defaults broke installs" has invented a finding.**

### The rejected alternative, with its reasoning (recorded so it is not re-proposed)

**Re-open plan 92 and add a Phase 7 + a D2 reversal inside it.** Rejected on three grounds, any one deciding:

- **Plan 92's Phase 0 is CLOSED with every item ratified as recommended, and five build records describe what shipped.** Reversing a ratified half inside that file makes its close record false about itself. A dated amendment note at the reversed site plus a new plan that owns the reversal keeps both readable — which is exactly what plan 85 did to plan 23 and plan 82 did to plan 62.
- **The two directives are one change with one blast radius.** The override needs the tier map; the no-defaults rule changes what the apply verb writes when a tier is unset; both land in the same verb, the same emitter and the same `update.sh` block. Splitting them across a closed plan and a new one would leave the emitter half-edited between phases.
- **The override is a Claude-Code-integration surface plan 92 never touched.** Plan 92 wrote agent frontmatter; this writes command frontmatter, under a different documented resolution story and a different update path (commands are re-emitted wholesale and are not three-way merged). **That deserves its own Phase 0, which is what plan 92's OQ-5 said in as many words.**

A fourth, weaker objection is recorded because it will be raised: two plan numbers for one maintainer sentence is bookkeeping overhead. **It is, and the overhead buys a readable record of which decision was reversed and by whom.**

---

## What is actually being added

Six things. **Phase 0 ratifies each independently**, except D1's transition sub-part and D2, whose dependency is named at both.

1. **The override itself** (Phase 1) — the existing apply verb extended over `.claude/commands/devforge/*.md` and renamed, writing `model:` / `effort:` into the frontmatter of a fixed set of commands from `.devforge/project-config.json` (D1, D5, OQ-1). **Python.**
2. **A helper-owned `COMMAND_TIERS` map with a maintainer consistency test** (Phase 1) — the map pinned against the eight advisory lines' own tier words, so the map and the printed advice cannot drift (D1). **Python.**
3. **The framework's own model choices deleted** (Phase 1) — every emitted agent gets `model: inherit`, no emitted command gets a `model:` line, `CLAUDE_AGENT_DEFAULTS_BY_TIER` and its equality test are deleted, and the `scan` tier is retired (D2). **Python.**
4. **`security` becomes the fourth tier and a QUESTION** (Phases 1–2) — `model_pin` leaves the authoring contract, `security-reviewer` moves onto `model_tier: security`, and Q11 grows a fourth call with its own model and effort question (D3). **Python + instruction.**
5. **The `update.sh` apply block MOVES** (Phase 1) — to after the promoted-command re-emit, because that step overwrites every command file (D1). **Shell.**
6. **The eight advisory lines re-derived** (Phase 2) — their unconfigured-tier prose stops naming a built-in default, and the line's second half becomes the override's readback (D4). **Instruction-only.**

**⚠ Five honest bounds that must survive into every emitted sentence:**

- **The override is TURN-SCOPED and is not saved.** The vendor's own words: *"The override applies for the rest of the current turn and is not saved to settings; the session model resumes on your next prompt."* **So this plan changes what a command's turn runs on, never what the user's session is.**
- **An organization's `availableModels` allowlist silently wins.** *"A value excluded by your organization's `availableModels` allowlist is not used and the session keeps its current model."* **A consumer whose org excludes the configured alias gets the session model and no message** — the configure-time availability probe (plan 92 D5) is the only thing that would have caught it, and it observes a session, not an entitlement.
- **Whether a subagent carrying `model: inherit` follows a command's turn-scoped override is NOT DOCUMENTED.** It is the pivot of the combined design and **only Phase 4's anchor 6 will ever observe it** — never assumed, never written into `src/` as fact.
- **A fresh, never-configured install now runs every agent and every command on the session model.** That is directive (2) working, not a regression — and it is a real behavior change from today, where the framework picks per tier.
- **Nothing validates model × effort.** Plan 92 D4's bound is inherited unchanged: the documented fallback is silent, so an unsupported combination looks exactly like success, and **the fallback is documented for the session-level setting, not explicitly for the frontmatter field** (D5).

---

## Verified mechanics (2026-09-04)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token is the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **Plan 92's apply verb exists and is consumer-side.** `configure_helper apply-agent-models` = `_configure/_cmds_agent_models.py` (`cmd_apply_agent_models`, filesystem + config I/O) over `_configure/_agent_models.py` (pure text-in/text-out), registered in `_configure/_cli.py` under the comment `# Step 5b: apply-agent-models.` It walks `.claude/agents/*.md`, keys on the emitted `model_tier:` line, is **two-pass** (nothing written until every file validates), **idempotent**, and emits `{"applied": [{agent, tier, model, effort, changed}], "skipped": [{agent, reason}]}` on stdout | `_cmds_agent_models.py`; `_cli.py:467`, `:471` |
| 2 | **The static default map, in two places, pinned equal.** `CLAUDE_AGENT_DEFAULTS_BY_TIER = {"think": "opus", "do": "sonnet", "verify": "sonnet", "scan": "haiku"}` in `scripts/lib/install_defaults.py` **and** a commented TWIN in `_agent_models.py`; `tests/lib/_configure/test_agent_models.py` loads the maintainer-tree file by path and asserts the two equal, and proves the pin by MUTATING a copy | `install_defaults.py:39`; `_agent_models.py:29`; `test_agent_models.py:36`, `:47`–`:71` |
| 3 | ⚠ **`install_defaults.py` contains NOTHING ELSE.** The whole module is a docstring plus that one dict. **So D2's deletion empties it** — the file becomes a docstring with no symbol. Its only `import` is `scripts/generate-agents.py`'s `from lib.install_defaults import CLAUDE_AGENT_DEFAULTS_BY_TIER`; **two further sites load it BY PATH** — `tests/scripts/test_generate_agents.py`, which pre-loads it by absolute path to dodge a `lib/` shadowing problem, and `tests/lib/_configure/test_agent_models.py`'s equality test (fact 2), which D2 deletes anyway. **Deleting the module is therefore a FOUR-file change, not one, and two of the four are invisible to an import grep** | `install_defaults.py` (45 lines); `generate-agents.py:65`; `test_generate_agents.py:41`–`:74`; `test_agent_models.py:36` |
| 4 | **The emitter writes the model from that map, and `model_pin` bypasses it.** `_claude_tier_model(tier)` is a bare dict lookup; `emit_claude` writes `model: <pin>` with **no** `model_tier:` line when a source declares `model_pin`, else `model: <tier default>` **and** `model_tier: <tier>`. Emitted order: `name`, `description`, optional `tools`, `model`, optional `model_tier`, optional `applies_to`. `VALID_TIERS = {"think", "do", "verify", "scan"}`; `_MODEL_PIN_RE = ^[a-z][a-z-]*$` (no digit — tightened at plan 92's build after a reviewer showed a hyphenated version slipping both tripwire patterns) | `generate-agents.py:72`, `:84`, `:191`, `:234`–`:247`, `:279` |
| 5 | **Exactly ONE agent declares a pin.** `src/agents/security-reviewer.md`'s meta block is `name` / `description` / `tools: Read, Grep, Glob, Bash` / `model_tier: think` / `model_pin: opus` / `applies_to: ["all"]`. The emitter test pins the LIVE pin set | `src/agents/security-reviewer.md:1`–`:8` |
| 6 | **The authoring contract already records its own extension.** `agents-AUTHORING.md`'s table is `name` / `description` / `model_tier` / `tools` / `applies_to` / `model_pin`, introduced by *"The contract is **fixed** — author to it, never change it."* and followed by a dated **Contract extension — 2026-09-03** paragraph naming plan 92 D6. The `model_tier` row says the tier is *"Emitted TWICE"*; the skeleton block carries a parenthetical stating `model_pin:` is deliberately absent from it | `src/agents-AUTHORING.md:13`, `:19`, `:22`, `:24`, `:36` |
| 7 | **The live configure counts, and the four assertions that pin them.** `FIELD_SCHEMA` = **35** (`test_field_schema_has_35_fields`, `test_default_state_has_35_keys`); `_PROJECT_CONFIG_KEY_ORDER` = **43** (`test_all_43_keys_present`, `test_renders_43_keys_with_defaults`). `ENUM_FIELDS` = **8**, `FIELD_DEFAULTS` = **6** as of plan 92's build. ⚠ **Every one of these moves under D3, and every one is READ LIVE, never incremented** | `tests/lib/test_configure_helper.py:195`, `:199`, `:3414`, `:3571`; plan 92 Phase-1 build record |
| 8 | **`configure/main.md`'s count sites.** *"canonical state (35 fields)"*; *"43 keys: 35 from configure.yaml + 5 from init.yaml + 3 derived"*; *"These ten fields cannot be derived from filesystem scan"*; *"Once `configure.yaml` is fully populated (34 fields set)"*; and plan 89's D6 `regression_gate` note — *"The schema carries 35 fields; the 34 this command populates are set in Phase 3 (24 detection-derived values) and Phase 4 (10 user-only prompts)"* — **which carries its own arithmetic and its own no-prompt instruction** | `src/commands/configure/main.md:13`, `:14`, `:282`, `:326`, `:339` |
| 9 | **Q11 is three calls, each carrying two questions, and its reference file is self-contained.** `references/q11-tiers.md` holds the four-alias availability probe and its one-line report, `## Q11.1/2/3`, the fewer-than-two-aliases arms, `## Pinning a model the list did not offer`, `## Saving the answers`, and `## Defaults rationale` — whose recommended defaults are *"`think = opus`, `do = sonnet`, `verify = sonnet`, and effort `default`"*, described as *"the same values the framework emits into the agent files before this command runs"* | `q11-tiers.md:1`–`:105`; `configure/main.md:301`–`:303` |
| 10 | **The eight advisory lines exist, verbatim and byte-identical modulo the tier word.** `"This command's judgment work belongs to the <tier> tier; configured <tier> model: <value>; this session runs on: <session model, or unknown>."` — `specify` / `plan` / `grill` / `breakdown` = `think`, `implement` / `fix` = `do`, `review` / `verify` = `verify`. **Eight occurrences under `src/`, nothing outside the set.** Each step names `apply-agent-models` for provenance with an explicit *"NOT invoked by this step"* clause, and each resolves a null tier to the built-in default (`plan`: *"use the built-in `think` default `opus`"*) | `grep "judgment work belongs to the" src/commands/`; `plan/main.md:168`–`:176` |
| 11 | **Commands are emitted wholesale from their source and are NOT placeholder-substituted.** `scripts/emitters/claude.py` `emit()` copies each `src/commands/<name>/main.md` body (references rewritten) to `.claude/commands/devforge/<name>.md`; `_PROMOTED` is a **20-name** tuple. `configure_helper substitute-templates` walks **`CLAUDE.md` + `.claude/agents/*.md`** (+ optional `docs/` stubs) and **never a command file** | `emitters/claude.py:57`, `:60`–`:85`; `_cmds_render.py:94`–`:95`, `:153`–`:174` |
| 12 | ⚠ **`update.sh` RE-EMITS every promoted command, deliberately overwriting it — AFTER the plan-92 apply block.** The apply block sits at `# ── Execute: apply-agent-models (plan 92 D1)`, **before** `# ── Execute: mergeFiles`; the re-emit sits far below at `# ── Execute: re-emit promoted dir-shaped commands`, under the comment *"Overwrite semantics here are deliberate: commands are framework-owned … User-modified target commands are NOT preserved across updates"*, followed by the stale-top-level-command prune and then `# ── Write version marker`. **So a `model:` line written into a command before the re-emit is destroyed by it** — this is D1's whole reason for moving the block | `update.sh:936`, `:978`, `:1057`, `:1084`, `:1115` |
| 13 | **Commands are not snapshotted, so they never three-way merge.** `install.sh` snapshots **agents + `CLAUDE.md` only** into `.devforge/template/`; there is no command baseline anywhere. ⚠ **Consequence, and it is an asymmetry worth keeping: the merge-conflict class plan 92's Trap 3 describes cannot exist for commands.** A command file is simply overwritten | `install.sh:397`, `:428`–`:434` |
| 14 | **`install.sh` builds commands through the generator and needs no apply call.** It runs `scripts/generate.sh` (which invokes the emitter), prunes the pre-plan-63 flat layout, then snapshots. **It runs before `/devforge:configure` has ever run**, so there is no configuration to apply — plan 92 recorded the same no-op for agents and `grep -n apply-agent-models install.sh` is empty BY DESIGN | `install.sh:394`–`:426`; plan 92 Phase-3 build record |
| 15 | **`update.sh`'s apply block is guarded, non-fatal and jq-hardened.** Under the same `HAS_CONFIG` guard `substitute_placeholders()` uses; captures stdout and rc without tripping `set -e`; prints `Applied agent models: N with model_tier (M changed), K skipped` plus one `info` per changed agent; every downstream `jq` is `2>/dev/null || VAR="?"` so a malformed stdout **degrades to `?` instead of killing the update**; a failure `warn`s and continues | `update.sh:948`–`:976` |
| 16 | ⚠ **`HAS_CONFIG` is TRUE from the very first update.** `install.sh` ships an ALL-NULL `project-config.json` stub, so the apply block always runs — today as a byte-level no-op, because every null tier resolves to the static default the emitter already wrote. **D2 changes what that no-op writes** (`inherit`), which is why it is a behavior change and not only a deletion | plan 92 Phase-3 build record (b) |
| 17 | **Plan 93's counts are 16 model-invocable / 4 human-typed-only.** `disable-model-invocation: true` survives on `init-forge`, `generate-docs`, `configure`, `constitute` only. Emitted command frontmatter today is `name`, `description`, optional `argument-hint`, and that flag — **no `model:`, no `effort:`, and no other key anywhere in `src/commands/*/main.md`** | `grep -n "^disable-model-invocation" src/commands/`; frontmatter blocks of all 20 sources |
| 18 | **The version-string tripwire is a live gate over `src/`, and both baselines are clean.** `scripts/lib/model_version_tripwire.py` asserts **two** patterns absent: `claude-[a-z]+-[0-9]` and `\b(opus|sonnet|haiku|fable)[\s-]+[0-9]` (case-insensitive; the second widened from `\s+` at plan 92's build). ⚠ **`docs/` is outside its scope** | `scripts/lib/model_version_tripwire.py`; plan 92 D3 + Phase-5 build record |

### Claude Code authoring surface, verified against current docs

Fetched **2026-09-04** from `https://code.claude.com/docs/en/slash-commands` and `https://code.claude.com/docs/en/sub-agents.md`. **Cited so a future author re-verifies rather than trusting this file.**

- **Command files ARE skill files.** *"Custom commands have been merged into skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way."* And: *"Files in `.claude/commands/` support the same frontmatter, except `name` and `paths`, which Claude Code ignores in a command file."*
- **`model`, verbatim from the frontmatter reference:** *"Model to use when this skill is active. The override applies for the rest of the current turn and is not saved to settings; the session model resumes on your next prompt. Accepts the same values as `/model`, or `inherit` to keep the active model. A value excluded by your organization's `availableModels` allowlist is not used and the session keeps its current model. With `context: fork`, the value sets the forked subagent's model instead …"*
- **`effort`, verbatim:** *"Effort level when this skill is active. Overrides the session effort level. Default: inherits from session. Options: `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model."*
- **⚠ The page never states what happens when a command carries NO `model` line.** It documents the override only. **So "no line ⇒ the session model" is the documented override being absent, not a documented guarantee** — D1 and D2 must say it that way.
- **⚠ Unknown keys in a LOCAL command file are not documented either way** — the same gap plan 92 recorded for subagent files. What the page DOES document is the failure on the upload path: *"If you include any field the spec doesn't allow, packaging or upload fails with a hard error instead of ignoring the field"*, with the literal error *"Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name"*. **That is the strongest available evidence against inventing a marker key in command frontmatter, and it is D1's reason for keeping the tier map in the helper.**
- **`metadata` is the DOCUMENTED escape hatch for custom keys:** *"Free-form YAML map for your own key-value data, such as entitlement or catalog fields, read by your own tooling from `SKILL.md`. Claude Code doesn't act on its contents …"* ⚠ **So the marker route is available and documented** — D1 rejects it on other grounds and must not claim it is impossible.
- **`${CLAUDE_EFFORT}` is a documented substitution variable** carrying *"The current effort level: `low`, `medium`, `high`, `xhigh`, or `max`."* ⚠ **There is no model counterpart** — the model half of the advisory line still has no documented source, exactly as plan 92's Phase-4 pass found.
- **Subagent model resolution, verbatim order:** *"1. The per-invocation `model` parameter · 2. The subagent definition's `model` frontmatter, where `inherit` selects the main conversation's model · 3. The `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, when you set it to a model alias or model ID · 4. The main conversation's model."* And: *"When you set `model: inherit` in a subagent's frontmatter, the subagent uses the same model as the main conversation."*
- **`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` still defeats everything, and the page now names a version floor:** *"While `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is on, Claude Code ignores the `model` field of every subagent definition … and Claude can't pass a model when starting a subagent"*, and the surrounding note says the FORCE variable *"Requires Claude Code v2.1.257 or later."* ⚠ **That numeral differs from the pre-v2.1.251 resolution-order note plan 92's Step 0 recorded; the two claims are about different things (when FORCE became available vs when the ordering changed) and this plan reconciles neither.** Neither is a model version, and neither reaches `src/`.
- **⚠ The subagent page says NOTHING about whether a subagent carrying `inherit` follows a command's turn-scoped override.** Confirmed by direct fetch, 2026-09-04. **This is the one load-bearing unknown in the plan.**

### The parallel `claude-code-guide` pass (2026-09-04)

Run alongside the drafting fetches above; its five answers are folded into the decisions that cite them, and **no decision in this file still says "verify at Phase 0" about any of them.**

1. **DOCUMENTED — explicit `inherit` beats the environment variable.** `inherit` is step 2 of the resolution order; `CLAUDE_CODE_SUBAGENT_MODEL` is step 3. **A file with NO `model` line falls through to step 3 before reaching the main conversation's model.** ⇒ **OQ-5 is decided on documented ground: write `model: inherit` explicitly; do not omit the line.**
2. **NOT DOCUMENTED — subagent inheritance under a command override.** ⇒ **D1 states it as a property to be OBSERVED at Phase 4**, and Phase 4 gains a subagent readback anchor (dispatch one `inherit` agent inside an overridden command turn and record what it reports).
3. **`effort` in command frontmatter: DOCUMENTED as overriding the session effort, turn-scoped.** ⚠ **The silent fallback to the highest supported level is documented for the SESSION-level setting** (`model-config.md`, *Effort Level Fallback*), **not explicitly for the frontmatter field.** ⇒ **D5's bound says exactly that, and claims no more.**
4. **NOT DOCUMENTED — unknown frontmatter keys in local command files** — with the upload-path hard error quoted above as the nearest evidence. ⇒ **D1 keeps the tier map in the helper and puts NO marker line into command frontmatter.**
5. **NOT explicitly stated — what a command with no `model` line runs on.** ⇒ **D1 and D2 phrase the no-line case as "the documented override absent, hence the session model by implication", never as a documented guarantee.**

---

## Decisions (D1–D8) — ALL RATIFIED 2026-09-04

Each carries the recommendation, the alternatives with the reason each is rejected, and the **honest bound — what the decision does NOT achieve.** **The bounds are load-bearing: a decision ratified with its bound deleted cannot be re-opened honestly later.**

### D1 — The override mechanism: extend the apply verb over commands, keyed on a helper-owned map *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** Plan 92's verb is **EXTENDED** to `.claude/commands/devforge/*.md` and **RENAMED `apply-models`**, with `apply-agent-models` kept as an argparse alias for one release (OQ-1). For each command in a helper-owned `COMMAND_TIERS` map it writes, into that file's existing frontmatter block:

- **`model:`** ← the tier's `CLAUDE_TIER_<TIER>` value (normalized alias or verbatim pin, exactly as for agents).
- **`effort:`** ← the tier's `CLAUDE_EFFORT_<TIER>` level, the line **REMOVED** when that value is the `default` sentinel (D5).
- **An unconfigured (null) tier ⇒ NO `model:` line at all** — not `inherit`. The turn then runs on the session model **by implication of the documented override being absent**, which is the honest phrasing (guide answer 5) and matches D2's "the framework ships no model of its own".
- **A command outside the map is left byte-identical** and reported under `skipped[]`, as is any file whose frontmatter block is missing or unterminated. **No body byte is touched.** Idempotent, two-pass, same exit-code contract as today (fact 1).

**`COMMAND_TIERS` is the eight commands of plan 92 OQ-2** — `specify` / `plan` / `grill` / `breakdown` → `think`; `implement` / `fix` → `do`; `review` / `verify` → `verify` (fact 10). **A maintainer test pins the map against those eight files' own advisory lines**, matching `judgment work belongs to the <tier> tier` per command source, on plan 89's byte-consistency precedent (`storage-rules.md` ↔ `_DONE_WHEN_FIXED_LINES`). **So the map and the printed advice cannot disagree**, and adding a ninth command to one without the other fails a test.

**Where it runs — two seats.** `/devforge:configure` **Phase 5.4** (the same call, now doing both file classes) and **`update.sh`, where the block MOVES.** ⚠ **The move is the load-bearing half of this decision, not housekeeping:** `update.sh` re-emits every promoted command wholesale, overwriting it (fact 12), and today's block sits far above that step. **New anchor: after `# ── Execute: prune stale top-level commands (FIX B)` and before `# ── Write version marker`.** A build that leaves the block where it is ships a verb whose command half is erased later in the same run.

**⚠ The transition sub-part, and it is where D1 depends on D2.** D2 changes the emitted agent `model:` line from a tier default to the constant `inherit`. For a consumer whose configured value differs from BOTH the old static default and `inherit`, that is exactly plan 92's Trap 3 case — base `opus` / current `<configured>` / other `inherit` — which **conflicts**, leaving that agent's **whole update unapplied, body included**, its snapshot stale, and the condition **recurring on every later update** while the post-merge apply camouflages it (`## Evidence constraint`). **RECOMMENDED MITIGATION: one extra invocation of the same verb against the snapshot, immediately before the agent three-way-merge loop runs** — `--install-root "$TARGET_DIR/.devforge/template"` — so the baseline's `model:` / `effort:` lines carry the consumer's own configured values, base and current agree on that line, the merge takes the regen's `inherit`, and the post-merge apply rewrites it from configuration. **Zero new code: the verb already takes `--install-root`, and `update.sh` refreshes the snapshot from the raw regen afterwards anyway, so the mutation is transient.**

**⚠ Its anchor, stated as precisely as the block move's, because a mitigation placed anywhere else is a no-op or a hazard.** It runs **inside the `# ── Execute: templateDerived (update generated files from templates)` section**, **after** the agent pre-generation block that fills `REGEN_AGENTS_DIR`, and **immediately before the merge loop's entry line** `echo "$DERIVED_UPDATE" | while IFS= read -r line; do` (`update.sh:767`–`:796` today — **read the section live; grep the comment header and the loop entry, never the digits**). **`HAS_CONFIG` is resolved far above** (`update.sh:306`–`:334`), so the same guard the post-merge block uses is available here. ⚠ **Placed after the loop it changes nothing** — the merge has already run; **placed before `HAS_CONFIG` is set it silently never runs.**

**Alternatives considered:**

- *(a) A marker line in each command's own frontmatter (`model_tier: think`), mirroring the agent mechanism.* **REJECTED on two grounds.** Unknown keys in local command files are **not documented either way**, and the same docs page shows the upload path failing hard on an unexpected key with an enumerated allowlist (`### Claude Code authoring surface`) — evidence, not proof, but it points one way. Second, **commands are re-emitted wholesale from `src/commands/<name>/main.md`**, so a marker must live in the source, which puts a second tier declaration in the same file as the advisory line's tier word **with nothing pinning them equal** — the exact drift the recommended consistency test removes.
- *(a′) The documented `metadata:` free-form map, carrying the tier.* ⚠ **POSSIBLE and DOCUMENTED — rejected on preference, and the reason must not be overstated.** It is a real, supported place for custom keys. It is declined because it inherits (a)'s second ground in full — the declaration would sit in eight command sources rather than one map — and because a map plus a grep-based test is mechanically checkable in a way two prose declarations are not. **Recorded as the named widening path** if `COMMAND_TIERS` ever needs per-command data richer than a tier word.
- *(b) A separate `apply-command-models` verb.* **REJECTED**: two verbs mean two call sites in `/devforge:configure`, two in `update.sh`, two report shapes and two summaries to keep true, to express one operation over two directories. This repo's standing rule is *"extend the one binary, never a second composer"* (plan 26's 2026-06-19 note, re-affirmed by plan 88 D3).
- *(c) Keep the name `apply-agent-models`.* **REJECTED**: the name would describe half of what the verb does, and the next reader would trust the name over the docstring. OQ-1 records the alias-for-one-release shape.
- *(d) Placeholder substitution (`model: {{CLAUDE_TIER_THINK}}`).* **REJECTED, and it is not merely undesirable — it is unavailable**: `substitute-templates` walks `CLAUDE.md` and `.claude/agents/*.md` only (fact 11), and a placeholder cannot remove a line, which D5's `default` sentinel requires. **This is plan 92 D1's rejected alternative (a) with one further ground the command surface adds** — there, substitution existed and was declined; here it does not reach the files at all.

**⚠ Honest bound, FIVE parts.** **(i)** The override is **turn-scoped and unsaved** — it changes what a command's turn runs on, never the session. **(ii)** An org-excluded value is **silently not used** and the session keeps its model, with no signal anywhere. **(iii) A model-invoked command switches the session's model mid-conversation for that turn** — plan 92 OQ-5's cost (c), now live because plan 93 made 16 commands model-invocable; **it is accepted, and it is a behavior a user did not type.** **(iv)** Whether a subagent carrying `inherit` follows the override is **NOT DOCUMENTED** and is observed only at Phase 4's anchor 6 — **no sentence in `src/` may assert either answer.** **(v)** A re-run of `install.sh` re-emits commands and drops every `model:` line until `/devforge:configure` (or the verb) runs again; **nothing detects that state**, and unlike the agent path there is no merge to preserve it (fact 13).

### D2 — No framework defaults: `inherit` on agents, nothing on commands, and the map deleted *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE, four parts.**

**Part 1 — the emitter writes `model: inherit` for EVERY agent**, plus the `model_tier:` line it already writes. Explicit rather than omitted, **because the resolution order makes the two different**: `inherit` is step 2 and beats `CLAUDE_CODE_SUBAGENT_MODEL`, while an absent line falls through to step 3 (guide answer 1; OQ-5). **This is documented ground, not a preference.**

**Part 2 — no `model:` line is emitted into any command.** The override arrives only from configuration, through D1's verb.

**Part 3 — `CLAUDE_AGENT_DEFAULTS_BY_TIER` is DELETED** from both `scripts/lib/install_defaults.py` and `_agent_models.py`, **with `DefaultMapEqualityTests` deleted alongside it** — a pin over a literal that no longer exists is dead weight that reads as a live constraint. ⚠ **Deleting the map empties `install_defaults.py`** (fact 3), so Phase 1 also removes the module, its import in `generate-agents.py` and the by-path loader in `tests/scripts/test_generate_agents.py` — **verify that the module is genuinely empty before deleting it rather than trusting this sentence.** The apply verb's null-tier branch then writes `inherit` for an agent and **no line** for a command, and reports `"model": null` for that file so the report never implies a choice nobody made.

**Part 4 — the `scan` tier is RETIRED.** It has zero members and has had none for the life of the roster; plan 92 OQ-3 left it precisely because the default map gave it meaning. **The map is gone, so the tier is dead code rather than dead documentation** — which is the argument plan 92 recorded as *"the strongest argument for deleting, and it is not strong enough to widen this plan."* **It is strong enough here**, and `VALID_TIERS` loses it in the same edit that gains `security` (D3).

**Consequence, stated at the seat where it happens.** A never-configured install now runs every agent and every command on the session model. **That is directive (2) working as asked** — the framework expresses no opinion until the user does. An install that already answered Q11 keeps its answers and re-applies them on the next `update.sh`, so nothing regresses for a configured project.

**Alternatives considered:**

- *Keep a map but make it user-overridable.* **REJECTED**: that is what plan 92 shipped on 2026-09-03, the day before this plan was drafted. **A default is a default whoever can change it**, and directive (2)'s words are *"there must be no defaults, the user chooses"*.
- *Omit the `model:` line on agents instead of writing `inherit`.* **REJECTED on the documented order** — omission hands the choice to `CLAUDE_CODE_SUBAGENT_MODEL`, an environment variable the framework does not set and cannot see, which is a default with a different owner rather than no default (OQ-5).
- *Keep the map only as the Q11 `(Recommended)` labels' source.* **REJECTED as a rename**: a value the framework writes into an agent file is a default; a value it prints beside an option is a recommendation. **The labels stay** — they are plan 92's D2 and D3, whose `## Defaults rationale` argues each one — and they become plain text in `q11-tiers.md`, derived from nothing. ⚠ **Attribution matters here**: plan 92's directive (c) is the origin of the per-command ADVISORY LINE (its D7), not of these labels, and a note that conflates the two would send a future reader to the wrong decision.
- *Retire `scan` in a separate plan.* **REJECTED**: it is one member of the tuple this decision deletes, and leaving it would strand an enum value whose only remaining consumer is a validation error message.

**⚠ Honest bound, THREE parts.** **(i) The transition is not free, and it is the sharpest cost in this plan**: the very release that removes the static default IS a change to the static default, so every configured install whose value differs from both meets plan 92's Trap 3 once. **D1's snapshot-normalization mitigation is a recommendation, not a proof** — Phase 1's local reproduction is the only build-time evidence, and **Phase 4's anchor 4 is the only place it is observed on a real install.** ⚠ **WIDENED BY PHASE 1's BUILD (2026-09-04), and the earlier narrower wording is withdrawn: the residual conflict class is NOT limited to a hand-edited file.** Normalization writes the **NEW** configuration into the baseline, so **any live agent whose `model:` / `effort:` is STALE relative to `project-config.json` at merge time still conflicts** — a setter run without a following apply, or an update landing between a configuration edit and the next apply, produces exactly that state without anyone editing an agent by hand. **The mitigation narrows the class; it does not close it.** **(ii)** `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` still overrides every agent's frontmatter, `inherit` included, and **the framework cannot detect it** (plan 92's Trap 5, inherited unchanged). **(iii) Nothing here measures that the session model is a better choice than a tier default** — it is the choice the maintainer directed, and a consumer who wanted the old behavior now has to answer four questions to get it.

### D3 — `security-reviewer` becomes a QUESTION: a fourth tier, not a pin *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** A fourth tier **`security`** with exactly one member. `src/agents/security-reviewer.md` becomes `model_tier: security`, and **`model_pin` is REMOVED from the authoring contract** — it existed to express a framework-chosen model, which directive (2) forbids. Q11 gains **Q11.4 — "Which model reviews security?"** carrying that tier's model and effort questions in one call, like its three siblings. New fields `claude_tier_security` + `claude_effort_security`, new setters, new render keys `CLAUDE_TIER_SECURITY` / `CLAUDE_EFFORT_SECURITY`, and the apply verb resolves the fourth tier exactly like the other three.

**The question's description carries the reason the pin existed**, in prose and with no price and no version: the vendor documents that one model family's bug-finding gains **exclude security-focused analysis** where cyber classifiers apply, and that such a request can end in a refusal — **and a refused reviewer inside `/devforge:implement`'s panel or `/devforge:grill`'s refutation pass surfaces as a MISSING VERDICT, not as an error.** The recommendation is the deep-reasoning alias without that risk. **Nothing validates the answer.**

**Counts move and are READ LIVE.** Drafting-time: `FIELD_SCHEMA` 35, `_PROJECT_CONFIG_KEY_ORDER` 43, `ENUM_FIELDS` 8, `FIELD_DEFAULTS` 6 (fact 7); Q11 contributes 6 of the 10 Phase-4 prompts and the command populates 34 of 35 fields (fact 8). **Every one of those figures moves under this decision, and Phase 1 COUNTS the live tuples rather than adding two** (plans 89/90's standing rule; plan 92's Trap 6).

**Alternatives considered:**

- *Keep `model_pin`.* **REJECTED**: it is a framework-chosen model for one agent — a one-member default — and directive (2) exempts nothing. Keeping it would also leave the authoring contract carrying a field whose only declared use contradicts the emitter's new behavior.
- *Fold security into `think` and warn in the question text.* **REJECTED**: a user who picks the refusal-prone alias for `think` then gets a security reviewer that can return nothing, **with no separate knob to fix it** — the exact failure the pin was introduced to prevent, now unpreventable.
- *A per-agent question.* **REJECTED**: nineteen questions to express one fact about one agent; the tier is the unit the rest of the system already speaks in.
- *Drop the concern entirely and let the think tier apply.* **REJECTED** on the documented refusal behavior, which is a vendor behavior and not a speculation.

**⚠ Honest bound.** **A user who picks the refusal-prone alias here anyway gets exactly what plan 92 D6 warned about**, and this plan builds no validation, no warning at dispatch and no detection of a missing panel verdict. **The question replaces a guarantee with an informed choice** — that is the whole trade, and it is a real loss of protection, accepted rather than answered. ⚠ **It also touches the authoring contract a second time on consecutive days**: plan 92 added `model_pin` on 2026-09-03 and this plan removes it on 2026-09-04, so `agents-AUTHORING.md`'s fixity clause needs a second dated note **stating the field's whole life**, not a silent deletion.

### D4 — The eight advisory lines stay, and become the override's readback *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** The eight lines are **not deleted** and their printed sentence is **unchanged**. Two things change around them:

- **The unconfigured-tier prose stops naming a built-in default.** Today each step says to use the built-in tier default when the key is absent or null (fact 10); it will say **"not configured — inherits the session model"**, which is what D2 makes true.
- **The line's second half becomes the override's readback.** With D1 shipped, the configured model and the session model should agree inside these eight commands' turns — **so a mismatch is visible in the line the command already prints.** That is D8's anchor and it costs nothing new.

**Alternatives considered:**

- *Delete the lines now that the command actually runs on the tier's model.* **REJECTED**: they are the only place the effect is observable at all (D8), and the second half degrades to `unknown` rather than lying when the session model is unavailable.
- *Add an "override applied" claim to the line.* **REJECTED as unverifiable from inside the turn** — the command cannot read its own frontmatter's effect, and a printed claim that the override worked would be exactly the sentence Phase 4 exists to test.

**⚠ Honest bound.** **The readback is an observation, not a check.** Nothing compares the two halves, nothing fails when they differ, and **the session-model half still rests on an OBSERVED, undocumented harness statement** with `unknown` as the documented-correct fallback (plan 92 D7's bound (i), unchanged — there is still no documented way for a command to learn the session model, and `${CLAUDE_EFFORT}` has no model counterpart).

### D5 — Effort on commands: the tier's level, `default` removes the line *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** Each mapped command's `effort:` comes from its tier's `CLAUDE_EFFORT_<TIER>`; the `default` sentinel means **no `effort:` line**, which the docs define as inheriting the session's effort level. Same sentinel, same six-member enum and same setters as plan 92 D4 — **no new field, no new question beyond D3's pair.**

**Alternatives considered:**

- *Ship the model override without effort.* **REJECTED**: the two fields are one frontmatter write and one configuration read; splitting them means a second pass over the same files later, and the tier's effort answer would stay agent-only for no stated reason.
- *A separate per-command effort question.* **REJECTED**: it multiplies a closed vendor enum across twenty commands to express a per-tier preference the user already gave.

**⚠ Honest bound.** **Nothing validates model × effort** (plan 92 D4, inherited). ⚠ **And the documented silent fallback is documented for the SESSION-level effort setting, not explicitly for the frontmatter field** (guide answer 3) — so the most this plan may say is that an unsupported level is expected to degrade rather than fail, **and that no phase of it observes which.**

### D6 — Plan 92 is amended in place, dated, at four sites *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** Phase 3 writes dated amendment notes into `92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md` **without editing any build record and without re-opening any phase**:

- **D2 half 1 — REVERSED**, with the reason (directive (2)) and a pointer here. **Half 2 (`verify = sonnet`) survives as a RECOMMENDATION LABEL**, not as an applied default — say which half moved.
- **D6 — REPLACED by this plan's D3.** The pin becomes a question; the refusal reasoning is kept, because it is why the question exists.
- **OQ-5 — its DEFERRAL DISCHARGED.** Plan 92's recorded answer (*keep the advisory, treat the override as a separate decision*) is **not overwritten**: the note says the follow-on it asked for is this plan, and that the override is now taken. **Its four costs are answered, not dissolved** — the mapping is in `## Origin`, and none of the four became cheaper.
- **Trap 3 — CLOSED BY CONSTRUCTION, with its transition caveat.** ⚠ **The trap does not merely disappear: it fires once, on the release that removes the default** (D2's bound (i)). A note reading "Trap 3 no longer applies" without that clause would be false in the one release where it matters.
- **D1's "a null tier applies that tier's DEFAULT" → "writes `inherit`"**, and **Phase 6 anchors 1b and 3 restated** — anchor 1b becomes *"`security-reviewer` carries whatever Q11.4 chose"*, since `opus` is no longer guaranteed.
- Plus the repo-root `CLAUDE.md` index line and the `PLAN-STATUS-ARCHIVE.md` entry for plan 92, each gaining a dated pointer here.

**Alternatives considered:**

- *Leave plan 92 alone; let this plan's existence imply the changes.* **REJECTED**: plan 92's D2, D6 and Trap 3 read as current design to a fresh session, and a reader who finds them first will implement against a reversed decision. **This repo's whole ledger discipline exists to prevent that.**
- *Rewrite plan 92's decisions in place without notes.* **REJECTED**: it would falsify its Phase 0 close record, which states every item was ratified as recommended.

**⚠ Honest bound.** **Amendment notes are read by whoever opens the file, and nothing enforces that.** Plan 92 is cited from `CLAUDE.md`, `PLAN-STATUS-ARCHIVE.md`, `DEVELOPMENT-STATUS.md`, `CHANGELOG.md` and `docs/v2/ARCHITECTURE.md`; **Phase 3 sweeps the ones this plan falsifies and claims nothing about the rest.**

### D7 — Scope tripwire: zero gates, and Python confined to a named list *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** **Zero gates, zero new `verify-*` gate numbers, zero hard-fail validators** — plan 75's tripwire in both halves. **No plan-63/93 count delta**: the 16/4 split is untouched, no command is added or removed, no `disable-model-invocation` flag moves, and **no `description` is widened** (a `model:` line is not a description and does not enter the always-on skill-listing budget). ⚠ **Read the counts LIVE at Phase 3 anyway** — plan 63's standing coordination rule, which earned itself on plan 92's Phase-5 sweep (2026-09-03), when the counts had moved 13/7 → 16/4 inside a day.

**Python (and shell) is confined to this list, and a phase that needs more has crossed its boundary:**

1. The verb extended over commands + the rename with its one-release alias + `COMMAND_TIERS` + the map↔advisory-line consistency test (D1, OQ-1).
2. The emitter: `model: inherit` for every agent, `model_pin` support removed, `scan` removed from `VALID_TIERS`, `security` added — plus emitter tests (D2, D3).
3. Two configuration fields, two setters, two render keys, the display group, and every count pin re-COUNTED (D3).
4. Deletion of `CLAUDE_AGENT_DEFAULTS_BY_TIER`, its equality test, and the emptied `install_defaults.py` with its importer and by-path test loaders (D2, fact 3) — **plus the two uses of that map inside `_agent_models.py::_resolve_tier` it leaves behind** (the tier-validity check and the null-value fallback) and the fourth `_TIER_CONFIG_KEYS` entry `security` (D3).
5. **Shell: TWO `update.sh` edits, each with a named anchor** (D1's transition sub-part). **(a)** the apply block **MOVES** to after `# ── Execute: prune stale top-level commands (FIX B)` and before `# ── Write version marker`; **(b)** a pre-merge snapshot-normalization call is **ADDED** inside `# ── Execute: templateDerived …`, after the `REGEN_AGENTS_DIR` block and immediately before the loop entry `echo "$DERIVED_UPDATE" | while IFS= read -r line; do`, under the same `HAS_CONFIG` guard, with `--install-root "$TARGET_DIR/.devforge/template"`. ⚠ **(b) is a deliberate widening of the shell item beyond a pure move**, named here so a reviewer sees it was decided rather than drifted into; it adds **no new code**, only a second call to an existing verb with a different `--install-root`.

**Everything else is instruction-only.** **No back-porting into shipped installs**: they arrive through `update.sh` and a re-run of `/devforge:configure` for Q11.4.

**Alternatives considered:**

- *A `verify-command-models` gate that fails when an emitted command's `model:` disagrees with configuration.* **REJECTED**: first mechanical blocker for a lane with zero observed failures, and the verb is idempotent — the repair for a disagreement is to run apply. **Recorded as the shape, not built**, with the trigger being an OBSERVED install whose commands drifted from its configuration.
- *A WARN at update time when the block's move leaves commands unwritten.* **REJECTED for v1**: the move makes the condition impossible in the same run; a warning about an impossible state teaches a reader the wrong model of the script.

**⚠ Honest bound.** **Nothing verifies the applied model after apply runs**, other than idempotence and its tests — and for commands there is not even a merge to preserve a hand-edit: **the next re-emit silently discards it** (D1 bound (v)).

### D8 — The consumer e2e is the ONLY place the override is observed working *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** State it plainly wherever this plan is summarized: **no build-time check can see a turn-scoped model override take effect.** Tests prove the bytes were written; the docs describe what the bytes mean; **only a real run shows the turn running on the model the line names.**

**The anchor.** Configure `think = <a model the session is NOT set to>`, set `/model` to something else, then run `/devforge:plan`. **PASS = the advisory line's second half reports the tier's model, not the session's.** Everything else in Phase 4 tests the configuration path.

**Alternatives considered:**

- *Add a Python check that reads the frontmatter back.* **REJECTED as a category error**: it would prove the file says `model: X`, which the apply test already proves, and say nothing about the turn.
- *Ask the model to self-report inside the command body and assert on it.* **REJECTED**: there is no documented way for a command to learn the session model (`### Claude Code authoring surface`), so the assertion would rest on the same observed harness statement the advisory already degrades to `unknown` for.

**⚠ Honest bound.** **A green anchor observes ONE session on ONE Claude Code build.** It is not a claim about org allowlists, about older builds, or about subagent inheritance — that last one has its own anchor precisely because it is undocumented and cannot be inferred from this one.

---

## Open questions (OQ-1–OQ-5) — ALL RESOLVED 2026-09-04

### OQ-1 — The verb's name *(RESOLVED 2026-09-04 — rename to `apply-models`, with `apply-agent-models` kept as an alias for one release)*

**RECOMMENDATION: rename to `apply-models`, keeping `apply-agent-models` as an argparse alias for one release.** ⚠ **Count the blast radius before choosing: a `grep -rl apply-agent-models` over the repo returns 28 files on 2026-09-04** — the ten command-surface files (`configure/main.md`, `q11-tiers.md` and the eight advisory steps' provenance clauses), `update.sh`, `agents-AUTHORING.md`, **five `src/` + `scripts/` Python modules** (`_cli.py`, `_cmds_agent_models.py`, `_render.py`, `install_defaults.py`, `generate-agents.py`), **three test modules**, and the ledger/doc set. **An alias makes the rename a documentation sweep rather than a flag day**; the alternative — keep the old name — leaves a name that describes half the verb, and the next reader trusts the name over the docstring.

⚠ **The alias is a deprecation with no removal date, which is its own small debt.** Phase 3 records the removal as owed at the next release that touches this verb.

### OQ-2 — Widen the override set beyond the eight? *(RESOLVED 2026-09-04 — NO widening in v1; the eight stand)*

**RECOMMENDATION: NO for v1.** Candidates recorded rather than built: `research` and `discover` (intake judgment, arguably `think`), `audit` and `spec-check` (adversarial, arguably `think`), `summarize` and `finalize` (drafting, arguably `do`). **Three reasons to wait:** the eight are the set plan 92 already argued and ratified; each addition costs a real per-turn model switch on a command that may be model-invoked (D1 bound (iii)); and **the consistency test binds the map to the advisory lines**, so widening the map means widening the printed advice too — a bigger edit than it looks.

### OQ-3 — Should `/devforge:configure` refuse to complete with an unanswered tier? *(RESOLVED 2026-09-04 — NO refusal; an unanswered tier inherits the session model)*

**RECOMMENDATION: NO.** Phase 4 always asks all four tiers, so the unanswered state arises only for a legacy install that never re-ran the command — and **that install now runs on `inherit`, which is precisely what directive (2) says should happen when the user has not chosen.** A refusal would turn the no-defaults stance into a blocker on a state the stance itself endorses, and it would be the first hard-fail in this lane (D7).

**The counter-argument, recorded:** a user who skips Q11.4 gets a security reviewer on the session model, which may be the refusal-prone one (D3's bound). **That is a real hole and it stays open** — the question's own description is the only mitigation.

### OQ-4 — The `update.sh` summary line *(RESOLVED 2026-09-04 — the line names BOTH classes, and `configure/main.md`'s quote of it is reconciled in the same phase)*

**RECOMMENDATION: extend it to name both classes** — `agents N (M changed), commands K (L changed), skipped S`. Today's line says *"Applied agent models: N with model_tier (M changed), K skipped"* (fact 15), which would silently under-report after D1. ⚠ **The line is composed by `jq` over the verb's stdout, so the report shape is a contract**: if `applied[]` gains a discriminator (e.g. a `kind` field), the shell must read it, and **plan 92's jq-hardening (`2>/dev/null || VAR="?"`) must be preserved on every new expression.**

⚠ **Found while drafting, and it makes this OQ slightly larger than it looks: the two sites already disagree.** `configure/main.md`'s Phase 5.4 tells the reader `update.sh` prints *"Applied agent models: N agents (M changed, K skipped)"*, while the shell actually prints *"Applied agent models: N with model_tier (M changed), K skipped"*. **Pre-existing, harmless today, and this decision must not carry it forward** — whichever wording is chosen goes into BOTH sites in the same phase.

### OQ-5 — Explicit `model: inherit` on agents, or omit the line? *(RESOLVED 2026-09-04 — explicit `inherit`, on documented ground)*

**RECOMMENDATION: explicit `inherit`.** ⚠ **This is no longer a judgment call: the documented resolution order settles it.** `inherit` is step 2 and beats `CLAUDE_CODE_SUBAGENT_MODEL`; an absent line falls through to step 3, handing the choice to an environment variable the framework does not set and cannot see (guide answer 1; `### Claude Code authoring surface`). **Omitting the line would replace a framework default with an environment default, which is not what directive (2) asked for.**

The remaining judgment is cosmetic and is recorded: an explicit `inherit` is one more line in every emitted agent, and a reader who does not know the resolution order may read it as redundant. **Phase 2's authoring-contract note is where that reader is answered.**

---

## Phases

### Phase 0 — Ratification *(doc-only)* — **CLOSED 2026-09-04**

**Objective:** ratify or amend D1–D8 and answer OQ-1–OQ-5, recording each answer in this file with its reasoning. **Nothing else may start.**

**✅ CLOSED 2026-09-04 — see `## Phase 0 close record` below. Phases 1, 2 and 3 are cleared to build; Phase 4 stays a deferred user-driven HARD GATE.** The pick-list below is retained as the record of what needed an explicit answer, **and every item on it was answered by the blanket directive rather than by a separate deliberation** — which the close record states plainly.

**Four items need an explicit pick rather than a nod**, because each has a named fork whose arms lead to different builds:

- **D1's transition sub-part with D2.** The snapshot-normalization call is either taken or the merge conflict is accepted with its recurrence. **These must be answered together** — D2 without the mitigation ships a one-time conflict for every configured install whose value differs from both, and the plan must say which was chosen.
- **D3's contract change.** `model_pin` was added to a table whose own text calls the contract *"fixed"* on 2026-09-03 and would be removed from it the very next day. **That is a second conscious extension, not a formality**, and the note must record the field's whole life.
- **D2 part 4 — retiring `scan`.** Plan 92 OQ-3 decided to keep it. **Reversing another plan's answered OQ is a decision**, and its reason (the map that gave it meaning is gone) must be stated where plan 92's answer is amended.
- **OQ-2's set width.** Eight commands is inherited, not re-derived. **A ratifier who wants more should say so now**, because the consistency test makes a later widening a two-file edit per command.

**⚠ One question Phase 0 CANNOT answer**, and it must not pretend otherwise: **whether a subagent carrying `inherit` follows a command's turn-scoped override.** It is undocumented (guide answer 2), it is external to this repo, and **no directive can settle it** — Phase 4's anchor 6 is the only route.

**Verify:**

- `grep -n "^### D[1-8] " 94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md` returns eight lines and **every one carries a ratification marker with a date.**
- `grep -n "^### OQ-[1-5] " 94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md` returns five lines, each with a recorded answer.
- **A grep for the drafting-time marker — the bracketed, italicised word this file carries on every decision header, every open-question header and both of their section headings until this close — returns ZERO hits.** ⚠ **This bullet deliberately does NOT write that token out**: a Verify criterion quoting the string it forbids can never pass its own grep. **The marker's exact shape is recoverable from any pre-close revision in git history** (plan 92's Phase-0 Verify carries the same construction and the same reason).
- **Every decision still carries its alternatives AND its honest bound.** A ratified decision whose bound was deleted cannot be re-opened honestly.
- The status line at the top names the ratification date and which phases are cleared.
- **D1's transition sub-part and D2 are answered in the same breath**, and if they diverge the ratifier states which mitigation replaces the other.
- **The evidence split survives ratification.** Two directives plus one locally-reproduced merge finding. **A Phase 0 that upgrades a directive into a finding has changed the evidence base and must say where the finding came from.**
- **The five recorded guide answers are still the live doc behavior** — re-check the two fetched pages if more than a few days have passed; **answers 1 and 2 are load-bearing for OQ-5 and D1 respectively.**

---

## Phase 0 close record

**Ratified 2026-09-04 by the maintainer, in-session, with a SINGLE BLANKET DIRECTIVE** — verbatim, in Ukrainian, **with its typo kept as written**: *"ратифікую все як пекомендовано"* (*"I ratify everything as recommended"*). **Every item — D1–D8 and OQ-1–OQ-5 — is ratified AS RECOMMENDED.** No item was amended, deferred or declined except where a decision's own recommendation was to decline (D1's alternatives (a), (a′), (b), (c) and (d); D2's four rejected arms; D3's four; D4's two; D5's two; D6's two; D7's gate and drift-check arms; OQ-2's widening; OQ-3's refusal) — **those declines ARE the recommendation, not a departure from it.**

⚠ **What this closure is, stated plainly rather than dressed up: ONE directive, not thirteen deliberations.** The maintainer supplied no per-item reasoning, and **this record does not manufacture any.** The arguments standing behind each answer are the ones already written in the decision bodies above — they were ratified, not re-derived, and **nothing in this closure adds evidence to any of them.** *(Precedent: plan 91's Phase 0, closed 2026-08-28, and plan 92's, closed 2026-09-03, both by a single blanket directive and both recording the blanket form rather than implying per-item argument.)*

**The four explicit picks, as answered by that directive:**

| Pick | Answer |
|---|---|
| **D1's transition sub-part with D2** | **BOTH, in the same breath.** The pre-merge snapshot-normalization call is TAKEN, at the anchor D1 names, **and** D2 ships with its bound (i) intact — the mitigation is a recommendation whose only real-install observation is Phase 4's anchor 4 |
| **D3's contract change** | **ACCEPTED.** `agents-AUTHORING.md`'s *"fixed — author to it, never change it"* clause is touched a SECOND time on consecutive days — plan 92 added `model_pin` on 2026-09-03, this plan removes it on 2026-09-04 — and **Phase 2 records the field's WHOLE LIFE in one dated note**, because a field that appears and vanishes without a record is indistinguishable from drift |
| **D2 part 4 — retiring `scan`** | **RETIRED**, reversing plan 92's OQ-3 answer on the stated ground that the map which gave the tier meaning is gone. **Phase 3 states that reason where plan 92's OQ-3 is amended**, never as a silent divergence |
| **OQ-2's set width** | **The eight, unchanged.** No widening in v1; the candidates stay recorded, and a later widening is a two-file edit per command because the consistency test binds the map to the printed advice |

**What ratification did NOT change — recorded so a future session does not read closure as scope growth:**

- **Every alternative and every honest bound survives verbatim.** D1's five bounds (turn-scoped, silent org exclusion, mid-conversation model switch on a model-invoked command, undocumented subagent inheritance, no survival across a re-emit), D2's three (the one-time transition conflict, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, nothing measured), D3's loss of a guarantee in exchange for an informed choice, D5's unvalidated model × effort, D6's unenforced amendment notes, D7's un-verified post-apply state and D8's one-session bound are **accepted costs, not answered ones.** **Phase 0's own Verify requires this**, and none was deleted.
- ⚠ **Two costs were ratified WITH their bounds and must not be re-read as discharged.** **(a) The transition cost (D2 bound (i))**: the release that removes the static default IS a change to the static default, so a configured install whose value differs from both meets plan 92's Trap 3 once; the mitigation is recommended, **not proven**, and Phase 1's local reproduction is a build observation while Phase 4's anchor 4 is the only real-install evidence. **(b) The four-questions cost (D2 bound (iii))**: a consumer who wants the old per-tier behavior must now answer four questions to get it, and **nothing here measures that the session model is a better starting point** — it is the choice the maintainer directed.
- **The evidence split is unchanged.** Two maintainer directives dated 2026-09-04 plus one inherited, locally-reproduced merge finding. ⚠ **Ratifying a directive does not upgrade it into a finding**, and no summary of this plan may imply a consumer failure.
- **The five `claude-code-guide` answers were folded into the decisions BEFORE ratification**, not after — `### The parallel claude-code-guide pass` is drafting-time evidence, so the maintainer ratified decisions that already carried it. **No "verify at Phase 0" placeholder survived into the ratified text**, and Phase 1's Step 0 re-asks only the two questions whose answers can move.
- ⚠ **The one question this closure could NOT answer stays open by construction: whether a subagent carrying `model: inherit` follows a command's turn-scoped override.** It is undocumented, external to this repo, and **no directive can settle it** — it remains an OBSERVATION at **Phase 4's anchor 6**, which carries no MUST, and **no sentence in `src/` may assert either answer.**
- **Python and shell stay confined to D7's five-item list.** A phase that needs more has crossed its own boundary.
- **Phase 4 is NOT cleared.** It is a deferred user-driven HARD GATE with seven known-answer anchors, **anchors 1 and 2 scored as a PAIR**. **Everything Phases 1–3 produce will be build-verified and NOT consumer-validated.**

---

### Phase 1 — The Python surface and the `update.sh` move *(Python + shell)* — **BUILT 2026-09-04** (python-reviewer clean on all four runs; commit pending)

**Route: `claude-code-guide` FIRST, then python-engineer → python-reviewer, test-first, tests written AND RUN in the same turn.** ⚠ **The guide pass is owed BEFORE any code**, because this phase changes the frontmatter shipped into every consumer's `.claude/agents/*.md` **and** `.claude/commands/devforge/*.md` — two Claude-Code-integration surfaces. **A phase that reasons "this is Python, so no pass is owed" has read the file extension instead of the artifact.**

**Step 0 — the guide pass.** **Re-put the two questions this plan's design hangs on and RECORD both answers in this phase's build record before any code lands:** (i) has anything changed about the resolution order or `inherit`'s meaning since this plan's drafting fetch of 2026-09-04 (OQ-5's whole basis); (ii) is subagent inheritance under a command's turn-scoped override documented yet (D1's bound (iv) — **a "yes, and it does NOT inherit" answer changes what Phase 4's anchor 6 is for, not whether the phase builds**). ⚠ **Do not re-ask the three questions plan 92's Step 0 settled** (unknown-key tolerance, key order, effort on a model without effort support) — **cite that build record.**

**Step 0b — run BOTH tripwire greps over `src/` and RECORD the results** (fact 18). Both returned zero at plan 92's build; a non-zero result now means something landed in between, and the premise must be re-derived before any edit.

**Deliverables:**

1. **`COMMAND_TIERS` + the consistency test** (D1). The map beside the apply logic; a maintainer test that reads the eight live command sources and asserts each one's advisory tier word equals the map's value, **and that the map has no member without a line and no line without a member.**
2. **The verb extended and renamed** (D1, OQ-1). Walks `.claude/commands/devforge/*.md` in addition to `.claude/agents/*.md`; the stdout report distinguishes the two classes (OQ-4); `apply-agent-models` registered as an alias; **exit-code contract unchanged.**
3. **The emitter** (D2, D3). `model: inherit` for every agent; `model_pin` support removed; `VALID_TIERS` loses `scan` and gains `security`; emitter tests updated, including the real-roster test that currently pins the live pin set.
4. **The deletions** (D2, fact 3). `CLAUDE_AGENT_DEFAULTS_BY_TIER`, `DefaultMapEqualityTests`, and — **if it is then empty** — `install_defaults.py` with its importer and the by-path loader in `tests/scripts/test_generate_agents.py`.
5. **The resolver, re-based** (D2, D3). ⚠ **`CLAUDE_AGENT_DEFAULTS_BY_TIER` is not only a default map — `_agent_models.py::_resolve_tier` uses it TWICE, and deliverable 4 removes it from under both.** Name and replace each:
   - **The tier-validity check** `if tier not in CLAUDE_AGENT_DEFAULTS_BY_TIER: raise AgentValidationError(…)` — its membership test and the `sorted(...)` in its message move onto **a plain tuple of the four valid tiers** (`think`, `do`, `verify`, `security`). **A build that deletes the map without this leaves an unknown `model_tier:` accepted silently**, which is a validation hole, not a cosmetic one.
   - **The fallback** `model = CLAUDE_AGENT_DEFAULTS_BY_TIER[tier]`, taken when the configured value is missing, `None` or not a string — it becomes the literal **`inherit` for an agent file** and **no `model:` line at all for a command file** (D1, D2). ⚠ **That makes the resolution CLASS-DEPENDENT for the first time**: `_resolve_tier` must be told which class it is resolving for, or split. **Decide which at build and say so in the docstring** — the drafted recommendation is a parameter, because two entry points would duplicate the effort branch.
   - **`_TIER_CONFIG_KEYS` gains `"security": ("CLAUDE_TIER_SECURITY", "CLAUDE_EFFORT_SECURITY")`** (D3), and **its comment explaining why `scan` is absent is deleted with the tier** (D2 part 4) rather than left describing a tier that no longer exists.
   - **A test per bullet**: an unknown tier still exits 2 with all four valid names in the message; a null tier yields `inherit` for an agent and no line for a command; a `security`-tier agent picks up `CLAUDE_TIER_SECURITY` / `CLAUDE_EFFORT_SECURITY`.
6. **The `security` tier's configuration surface** (D3). Two fields, two setters, two `_cli.py` registrations, two render keys, the `_summary.py` display group (the `claude_effort_*` entries sit directly after their `claude_tier_*` siblings — follow that shape), whatever `_cmds_verify.py`'s required-field loop needs, **and every count pin re-COUNTED.**
7. **The `update.sh` move + the transition call** (D1, D2), **two edits at two named anchors — read both live before touching either.** **(a) The MOVE:** the existing `# ── Execute: apply-agent-models (plan 92 D1)` block relocates to **after `# ── Execute: prune stale top-level commands (FIX B)`, before `# ── Write version marker`**; its ordering comment must be re-derived, since the reason it currently gives (merge/snapshot ordering) is no longer the whole reason once commands are in scope. **(b) The ADD:** the pre-merge snapshot normalization goes **inside `# ── Execute: templateDerived …`, after the `REGEN_AGENTS_DIR` pre-generation block and immediately before `echo "$DERIVED_UPDATE" | while IFS= read -r line; do`**, under the same `HAS_CONFIG` guard, invoking the same verb with `--install-root "$TARGET_DIR/.devforge/template"`. **Preserve the `HAS_CONFIG` guard, the non-fatal failure handling and every jq guard on both.** ⚠ **A failure of (b) is non-fatal like (a)** — it degrades to the conflict this mitigation exists to avoid, which must be warned about and never abort the update.

**⚠ Three build constraints, each a fact rather than a fork:**

1. **The counts are READ LIVE** (fact 7, plan 92's Trap 6). Four assertions pin the two tuples; `ENUM_FIELDS` and `FIELD_DEFAULTS` move too. **Count the live tuples and write what you counted.**
2. **Every existing configure and emitter test must pass unchanged** except the count pins and the tests this phase deliberately deletes. A failure anywhere else means a shared path moved.
3. **No body byte of any agent or command file is touched.** A test compares the post-apply body byte-for-byte, for both file classes.

**Verify:**

- **claude-code-guide invoked at Step 0 and BOTH answers RECORDED before any code landed.** ⚠ **An answer recorded after the code is a rationalization, and an unrecorded pass is indistinguishable from one that never ran.**
- python-reviewer clean; `tests/lib/` configure suites and `tests/scripts/` emitter suites green; `shellcheck` and `bash -n` clean over the touched `update.sh` ranges.
- **A test proves the extended verb is idempotent over BOTH directories** — run twice, second run changes zero bytes.
- **A test proves a command outside `COMMAND_TIERS` is left byte-identical**, and one proves a command with an unconfigured tier gets **no `model:` line** (not `inherit` — the two classes differ, D1/D2).
- **A test proves every emitted agent carries `model: inherit`** and that no emitted agent carries a pin.
- **A test proves the map↔advisory-line consistency test FAILS when either side is edited alone** — assert it by mutating a copy, not by reasoning about it.
- **Both tripwire patterns still return zero over `src/`**, and `python3 scripts/lib/model_version_tripwire.py src` passes.
- **`configure_helper verify` exits 0 on an install whose two new fields were never set**, and on a legacy `configure.yaml`.
- **All configure count assertions match a fresh count of the live tuples**, and the counted numbers are stated in the commit message.
- **`grep -n "apply-agent-models\|apply-models" update.sh install.sh`** shows the block in `update.sh` only, **below the command re-emit**, with the `install.sh` no-op recorded as deliberate (fact 14).
- **A test proves an unknown `model_tier:` still exits 2 after the default map is gone**, with all four valid tier names in the message — the validity check must not die with the map it read (deliverable 5).
- **A local reproduction of the transition merge is run and RECORDED as a build observation, never as consumer validation.** ⚠ **The recipe, because a vaguer bullet would be scored by whatever was convenient:** install a scratch target from the **OLD** emitter so its snapshot agents carry a static tier default; run `/devforge:configure` (or the setters + `render-config`) so the live `architect.md` carries a **different** configured model; edit that agent's BODY in the scratch template's `src/agents/architect.md`; then run the **NEW** `update.sh`. **MUST produce, all three: no merge conflict reported for `architect.md`, the body edit present in the live file, and the configured model still on its `model:` line.** ⚠ **Record the `Merge conflicts in` line's absence explicitly** — the failure mode this mitigation targets is silent everywhere else.
- `git status` shows zero files modified under `src/commands/` — this phase touches Python, the emitter and `update.sh` only.

**This phase appends a `#### Phase 1 build record` block** carrying the Step-0 answers, the counted numbers, what landed, every divergence from the text above with its reason, and the reviewer findings by severity.

#### Phase 1 build record — Step 0 (2026-09-04)

**The `claude-code-guide` agent was dispatched 2026-09-04 and answered from the live docs, BEFORE any Phase-1 code was written.** This block is the record Phase 1's first Verify bullet requires; **Phase 2 CITES it and does not re-ask.** ⚠ **Nothing below is a build result — no code has landed. This block records the two prerequisite steps only.**

**Answer 1 — the resolution order and the command `model` field are UNCHANGED from the drafting-time fetch, so OQ-5's basis STANDS.** `code.claude.com/docs/en/sub-agents.md` (*Model Resolution Order*) reads exactly as fact-checked at drafting: **per-invocation `model` parameter → the subagent's own `model` frontmatter, where `inherit` selects the main conversation's model → `CLAUDE_CODE_SUBAGENT_MODEL` → the main conversation's model**, with the page's own note that **from v2.1.251 the environment variable no longer overrides the parameter or the frontmatter.** And `code.claude.com/docs/en/slash-commands.md`'s frontmatter reference still carries the `model` field in full: *"The override applies for the rest of the current turn and is not saved to settings; the session model resumes on your next prompt. Accepts the same values as `/model`, or `inherit` to keep the active model. A value excluded by your organization's `availableModels` allowlist is not used and the session keeps its current model."*

⚠ **So D2 part 1, OQ-5 and D1's bounds (i) and (ii) rest on live documented text, re-read on the day of the build** — not on a cached reading. ⚠ **The two Claude Code version numerals in this plan are still two DIFFERENT claims and are still not reconciled**: this answer's **v2.1.251** is when the environment variable stopped overriding the parameter and the frontmatter; `### Claude Code authoring surface`'s **v2.1.257** is the availability floor the page states for `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`. **Neither is a model version, neither reaches `src/`, and the Non-goals entry that declines to reconcile them is unchanged.**

**Answer 2 — subagent inheritance under a command override is STILL NOT DOCUMENTED.** None of the three pages says what model a subagent carrying `model: inherit` — **or no `model` line at all** — runs on when it is started during a turn already under a command/skill `model:` override. ⚠ **The gap is exactly where the plan predicted it, so D1's bound (iv) is unchanged and Phase 4's anchor 6 keeps its purpose**: an OBSERVATION with no MUST, recorded whichever way it comes back. **No sentence in `src/` may assert either answer.**

**Plan 92's three settled questions were CITED, not re-asked** — unknown-key tolerance for `model_tier:`, frontmatter key ORDER, and `effort:` on a model without effort support are answered at that plan's `#### Phase 1 build record — Step 0`, and asking again would produce a second answer that can disagree with code already shipped.

**Step 0b — both tripwire greps and the live gate, run 2026-09-04 before any edit.** `claude-[a-z]+-[0-9]` over `src/` → **0 hits**; `\b(opus|sonnet|haiku|fable)[\s-]+[0-9]` (case-insensitive) over `src/` → **0 hits**; `python3 scripts/lib/model_version_tripwire.py src` → **PASS**. **So this phase starts from a clean baseline** — a failure on either pattern after this build means THIS build introduced it, not that it was always there.

**Phase 1 execution split — an orchestrator decision, recorded because the deliverable list does not imply it.** Deliverable 5's resolver re-basing needs both the emitter's new tier set (deliverable 3) and the configuration keys the fourth tier reads (deliverable 6), and deliverable 7's `update.sh` calls the verb deliverable 2 renames — **so the order is a dependency, not a preference. Four runs, each completing python-engineer → python-reviewer before the next starts:**

| Run | Contents | Why here |
|---|---|---|
| **A** | Deliverable 6 (the `security` tier's configuration surface) | Independent of the verb and the emitter; **runs in PARALLEL with C** |
| **C** | Deliverables 3 + 4 (emitter `inherit` / tiers / pin removal, and the deletions) | Independent of A; **must land before B**, whose resolver replaces what these two remove |
| **B** | Deliverables 1, 2, 5 (`COMMAND_TIERS` + the consistency test, the verb extension and rename, the resolver) | Needs **both** A's config keys and C's tier set |
| **D** | Deliverable 7 (`update.sh` move + transition call) | Calls the verb B renames; last by construction |

⚠ **A and C run in parallel and both touch the counts' neighbourhood**, so the count pins are re-COUNTED in whichever run lands second — **never incremented from the other run's numbers** (plan 92's Trap 6, inherited).

#### Phase 1 build record — Deliverables 1–7 (2026-09-04)

**BUILT and python-reviewer clean on all four runs; the commit is pending.** The split above ran as planned — **A ∥ C, then B, then D**, each completing python-engineer → python-reviewer before the next started. **Findings: A → 0. C → 1 low. B → 6 (3 medium, 2 low, 1 nit). D → 3 (1 medium, 1 low, 1 nit).** ⚠ **Everything below is build-verified and NOT consumer-validated.**

**The counts, COUNTED from the live tuples.** `FIELD_SCHEMA` **37** · `ENUM_FIELDS` **9** · `FIELD_DEFAULTS` **7** · `_PROJECT_CONFIG_KEY_ORDER` **45**. The four pins were RENAMED to carry the live numbers (`…_has_37_fields`, `…_has_37_keys`, `…_45_keys_present`, `…_45_keys_with_defaults`), and `test_enum_fields_has_9_entries` joins them. ⚠ **Quote none of these from here — count the tuples** (plan 92's Trap 6).

⚠ **A build finding about D3 that no decision anticipated, recorded because it looks like a defect and is not one.** `configure_helper verify` **already FAILS (exit 2) on a null `claude_tier_*`** — pre-existing behavior for the three tiers, mirrored for `security`. It is harmless because **`verify` is invoked only from `/devforge:configure`'s own Phase 7**, so an updated-but-not-reconfigured install is never auto-failed. ⚠ **But the INTERMEDIATE tree between run A and Phase 2 would have failed a full `/devforge:configure` at Phase 7, because Q11.4 did not exist yet to answer the field run A had just made required** — a **staged-build artefact**, resolved the same day by Phase 2, and **a reason never to ship run A alone.**

**What landed.**

- **Emitter (`scripts/generate-agents.py`)** — `model: inherit` for every agent plus its `model_tier:`; `VALID_TIERS = {think, do, verify, security}`; **`model_pin` is now IGNORED with ONE stderr warning naming the file and the key** (no shipped source declares it since Phase 2, and the real-roster test asserts **zero** warnings); `_MODEL_PIN_RE` and the `re` import are gone.
- **Deletions** — `scripts/lib/install_defaults.py` (`git rm`), its import and the `sys.path.insert` that served it, the by-path loaders in `tests/scripts/test_generate_agents.py` **and** `tests/lib/_configure/test_agent_models.py`, `DefaultMapEqualityTests`, and `CLAUDE_AGENT_DEFAULTS_BY_TIER` in `_agent_models.py`. ⚠ **Fact 3's four-site blast radius was real and all four were touched.**
- **Resolver (`_agent_models.py`)** — a `VALID_TIERS` tuple; `_TIER_CONFIG_KEYS` at four entries, **indexed directly**; `_resolve_tier` and `plan_rewrite` now take `kind` (`agent` | `command`): a null tier yields **`inherit` on an agent** and **NO `model:` line on a command** (a stale line is REMOVED), effort `default`/null removes the line; `_rewrite_command_field` inserts `model:` immediately after `description:` (or replaces it in place) and `effort:` after `model:` — **after `description:` when only effort is configured**; a missing `description:` or any duplicated key is a validation error.
- **`COMMAND_TIERS`** — the eight, beside the logic, pinned to the eight advisory lines by `tests/lib/_configure/test_command_tiers.py` **in both directions, with mutation proofs both ways**, plus `COMMAND_TIERS ⊆ VALID_TIERS`.
- **Verb (`_cmds_agent_models.py`, `_cli.py`)** — `apply-models` with `aliases=["apply-agent-models"]` (OQ-1); walks agents **and** `.claude/commands/devforge/*.md`; an unmapped command is `skipped` with reason **`not-in-command-tiers`** and left byte-identical; the report is `{"applied":[{kind, name, tier, model|null, effort|null, changed}], "skipped":[{kind, name, reason}]}` sorted by `(kind, name)` — **plan 92's `agent` key is GONE**, and `update.sh`'s jq moved to `.kind` / `.name`; exit codes unchanged; two-pass across both classes; atomic; **CRLF preserved for both classes**.
- **Config surface (run A)** — `claude_tier_security` mirrors `claude_tier_verify` (scalar, non-enum, alias-normalized, no default) and `claude_effort_security` mirrors `claude_effort_verify`, both appended last; setters `set-claude-tier-security` / `set-claude-effort-security`; keys `CLAUDE_TIER_SECURITY` / `CLAUDE_EFFORT_SECURITY` last; the summary group; **and five fixture fixes where "fully populated" tests lacked the new required tier field.**
- **`update.sh` (+110 / −44)** — the apply block **MOVED** after `# ── Execute: prune stale top-level commands (FIX B)` and before `# ── Write version marker`, now calling `apply-models`, its **ordering comment re-derived with TWO independent reasons** (the wholesale command re-emit; the raw snapshot refresh), every `jq` guarded, one `info` line per changed file of either class (`<kind> <name>: model=<model|none> effort=<effort|default>`); the **pre-merge snapshot normalization ADDED** inside `templateDerived`, after the `REGEN_AGENTS_DIR` block and immediately before `echo "$DERIVED_UPDATE" | while …`, under `HAS_CONFIG`, with `--install-root "$TARGET_DIR/.devforge/template"`, non-fatal; the dry-run preview names both classes.

**Run B's six findings, and three of them are worth carrying.** ⚠ **The two hand-kept literals `VALID_TIERS` and `_TIER_CONFIG_KEYS` were UNPINNED, and a dead `.get` fallback would have turned a desync between them into a silent "not configured"** — fixed by indexing directly plus a **set-equality test**, so a tier added to one and not the other now fails loudly instead of resolving to nothing. **No CRLF test covered the command path** (added). **The test file had reached 1118 lines carrying a SELF-GRANTED size exception** — **SPLIT by concern into three files (429 / 457 / 555 lines) and the exception paragraph DELETED**, with **27 = 27 tests conserved across the split**. Also added: the command-side last-line insertion test and the `COMMAND_TIERS ⊆ VALID_TIERS` assertion. **Re-check clean.** ⚠ **Process note, recorded because it shaped the work: a SECOND engineer performed the split after the first stalled twice on long pytest runs competing with the background full suite.**

**Run D's three findings, and the MEDIUM is a wording fix, not a logic fix.** ⚠ **The command "changed" count is structurally NON-ZERO on every run**: the re-emit strips every mapped command's `model:` / `effort:` lines and the apply then restores them, and the snapshot block re-pins the raw-refreshed `inherit` every run. **Nothing is wrong; the old wording implied drift where there is none.** The lines now read **`Applied models: agents N (M changed), commands K (L re-applied after re-emit), skipped S`** and **`Normalized snapshot models: agents N (M re-pinned to configuration)`**, with a comment at each site. **The LOW widened D2's bound (i)** — the residual conflict class is **not** limited to a hand-edited file (the amended bound says so at its own site). **The NIT — the `AGENT_MODELS_*` shell variable prefix now covering both classes — is recorded and NOT fixed.**

**Verify — results as they came back. ⚠ Build observations, NOT consumer validation; none of this is Phase 4.**

- **The transition reproduction, run to the recipe.** A scratch template at plan 92's last commit `8cfd7d9` (whose emitter still writes static defaults) installed into a scratch target and configured `think = fable` / `xhigh`, so the live `architect.md` read `model: fable` while the snapshot read `model: opus`; a body marker added to the CURRENT tree's `src/agents/architect.md`; then the NEW `update.sh --force`. **Result: `grep -c "Merge conflicts in"` = 0 across the whole transcript, the body marker present, `model: fable` still on its line**, the transcript showing `Normalized snapshot models: agents 18 (18 …)` and `Applied models: agents 19 (18 changed), commands 8 (4 …), skipped 12`, with `agent architect: model=fable effort=xhigh` and `command plan: model=fable effort=xhigh`; `plan.md` carries `model: fable` / `effort: xhigh` and `research.md` carries no `model:` line.
- **Idempotence at the file level, with a report that legitimately differs.** A second update changed **zero files** (`git status --porcelain` empty) while the report still showed commands re-applied and snapshot agents re-pinned — **which is run D's MEDIUM, stated as designed behavior rather than discovered drift.**
- **Failure paths.** A malformed config produced **both warnings and rc=0**; `--dry-run --force` printed the preview and wrote nothing; `bash -n` and `shellcheck` are clean over every touched range.
- **The merge mechanism itself, proved both ways.** A three-file `git merge-file` experiment reproduced **the pre-mitigation conflict** (`opus` / `fable` / `inherit` → exit 1) **and the post-normalization clean merge** (`fable` / `fable` / `inherit` plus a body change → exit 0, yielding `inherit` and the body).
- **Suites.** `tests/lib` + `tests/scripts` **11585 passed / 16 skipped** (run while B's fixes were mid-flight); after the split `tests/lib/_configure` **279 passed** (HEAD collected 251); emitter + tripwire + memory-lane + reachability **108 passed**; `verify-agent-reachability.py` **0**; `verify-memory-lane.py` **0**; the version tripwire **PASS**; and `grep -rn "install_defaults\|CLAUDE_AGENT_DEFAULTS_BY_TIER" src scripts tests` returns **only** `agents-AUTHORING.md`'s history note and one test docstring describing the deletion.

**Four deliberate divergences from this phase's own text.**

1. **The test surface is THREE files, not one per source module** — recorded with the reviewer's own reading that concern-based splits have precedent here.
2. **An unmapped command goes under `skipped`**, not into a third top-level array.
3. **`cmd_apply_agent_models`'s Python function name is UNCHANGED** — the verb was renamed, the function was not; OQ-1's alias covers the CLI surface and the internal name is not a consumer contract.
4. **The D8 readback and the anchor-6 subagent observation remain Phase 4's** — nothing in this phase attempted either, and no build result may be read as evidence for them.

**Two residuals recorded, neither this plan's to fix.** `_cli.py`'s module docstring claims *"all 29 `cmd_set_*`"* — **stale before this plan existed**, and the live count differs. And **`_agent_models.py` is now 476 lines, past the 400-line "plan a split" signal** — **the recorded option is moving the command-rewrite helper into a sibling module; it is NOT built.**

### Phase 2 — The question surface and the contract *(instruction-only)* — **BUILT 2026-09-04** (instruction-reviewer clean; commit pending)

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide` for this phase's own surface.** `q11-tiers.md` ships to `.devforge/command-refs/configure/` and `configure/main.md` ships into `.claude/commands/devforge/` — **plan 90's Phase-0 orchestrator ruling binds: every command-spec edit owes the pass, with no frontmatter carve-out.**

⚠ **This phase CITES Phase 1's recorded answers and does not re-ask them.**

Scope:

- **`src/commands/configure/references/q11-tiers.md`** — a fourth call `## Q11.4 — Security tier` in the shape of its three siblings (model + effort in one call, no authored `Other`, the probe's availability filtering, the `(Recommended)` rule that the marker is never moved to another alias); the intro's *"six fields"* becomes eight; **`## Defaults rationale` re-derived**: the recommendations are recommendations only — **the framework now emits no model of its own**, so the sentence *"these are the same values the framework emits into the agent files before this command runs"* becomes false and must be replaced with what is true (an unanswered tier inherits the session model). **The three honest bounds at the end stay, and the security question's own bound joins them.**
- **`src/commands/configure/main.md`** — the Q11 pointer paragraph (four calls, eight answers, eight setters); Phase 5.4 re-written for both file classes with the new verb name and the report shape; **every count site reconciled LIVE** (fact 8); ⚠ **plan 89's D6 `regression_gate` note carries its own arithmetic and is UPDATED IN PLACE, never removed** — its no-prompt instruction is untouched.
- **`src/agents-AUTHORING.md`** — the `model_tier` row re-derived (`think | do | verify | security`; emitted as `model: inherit` **plus** `model_tier:`, with the configured value arriving from the apply verb); the `model_pin` row **removed**; **a second dated contract note recording that the field was added on 2026-09-03 by plan 92 and removed by this plan, with the reason** — a field that appears and vanishes without a record is indistinguishable from drift.
- **`src/agents/security-reviewer.md`** — meta block: `model_tier: security`, `model_pin` gone. ⚠ **Zero body bytes.**
- **The eight advisory steps** — the unconfigured-tier prose only (D4). **The printed sentence itself does not change**, and the provenance clause's verb name follows OQ-1.
- **`src/devforge/storage-rules.md`** — **grep and touch only if it names the verb or the tier map**; record the no-op as a finding if not.

**Verify:**

- Instruction-reviewer clean; **claude-code-guide invoked for this phase's surface and its answers RECORDED**, plus a citation of Phase 1's Step-0 record. ⚠ **Re-asking Phase 1's questions is a FAILURE of this bullet, not extra rigour.**
- **Each per-tier AskUserQuestion call carries exactly two questions, each with 2–4 options and no authored `Other`** — four calls, eight answers.
- **No emitted sentence says the framework emits a model default**, in any file: `grep -rn "built-in .*default\|the framework emits" src/commands/ src/agents-AUTHORING.md` is reviewed line by line.
- **BOTH tripwire patterns return nothing** for every file this phase touches, and `python3 scripts/lib/model_version_tripwire.py src` passes. ⚠ **The security question's description is the likeliest site to break it** — the refusal reasoning invites a version and a price; it takes neither.
- **The `configure/main.md` counts match a fresh count of the live tuples**, the counted numbers are in the commit message, and **plan 89's D6 note is updated in place.**
- **`agents-AUTHORING.md` has one row fewer and one more dated note**, and its fixity clause still binds every remaining field.
- **`git diff src/agents/security-reviewer.md` touches the fenced `yaml` meta block ONLY.**
- **No plan vocabulary in emitted text** — "D3", "OQ-1", "Phase 2" and this plan's number are maintainer vocabulary. Emitted text names only commands, files and behaviors.

**This phase appends a `#### Phase 2 build record` block**, including every deliberate divergence from the scope above.

#### Phase 2 build record (2026-09-04)

**BUILT and instruction-reviewer clean; the commit is pending.** Route as run: **`claude-code-guide` for this phase's own surface FIRST**, then instruction-author → instruction-reviewer, which returned **5 findings — 1 high, 2 medium, 1 low, 1 nit.** Three were in-file fixes, applied and **CONFIRMED on re-check**; the nit was applied; **the low was DECLINED by decision** (below). The re-check returned **one cosmetic nit, recorded and NOT fixed.**

**The guide's answers (2026-09-04), and one of them changed emitted wording.**

- ⚠ **`effort` has NO `inherit` value.** The frontmatter reference reads *"Default: inherits from session. Options: `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model"* (`code.claude.com/docs/en/skills.md`). **So the `default` pick REMOVES the line and never sets a value** — the emitted text says exactly that, and a symmetry with `model: inherit` would have shipped a value Claude Code does not accept.
- **`model: inherit` IS documented for commands** — same page, *"or `inherit` to keep the active model"*. D2 part 1 and OQ-5 stand on it.
- **AskUserQuestion's `Other` free-text row IS documented** (`code.claude.com/docs/en/tools.md`); **its option-count bounds are NOT** — so fact 22's OBSERVED status (inherited from plan 92) is unchanged and still binds the four-option lists.
- ⚠ **Whether a command's `model:` override is visible ANYWHERE during the turn is NOT documented.** **D8's readback stays the only observation**, which is why Phase 4 anchor 5 admits no `unknown`.

**⚠ THE HIGH FINDING WAS A PARALLEL-EXECUTION ARTEFACT, AND THE LESSON REPEATS PLAN 92's.** `configure/main.md`'s Phase 5.4 described the report's name key as `agent` or `command` **per kind**, because that is what this plan's own text implied — while **run B, landing in parallel, ships a single `name` key beside `kind`.** Corrected to the SHIPPED shape: `applied[]` entries are `{kind, name, tier, model, effort, changed}` with **`model` null only for an unconfigured command**, `skipped[]` entries are `{kind, name, reason}`, both **sorted by kind then name**. **Write from the TREE, not from the brief** — plan 92 recorded this same failure twice, and this is its third instance across the two plans.

**The two MEDIUMs, both applied.** **(a) A fifth exit-2 cause was missing** — **commands only**: a file with no `description:` line to anchor an inserted line. **(b) The `update.sh` sentence** (*"followed by one line per changed file, agents and commands alike"*) **is a claim about run D**, not about landed text; **the orchestrator verifies it against `update.sh` before commit** rather than the spec asserting it on faith.

**The LOW, DECLINED by decision.** `verify/main.md`'s *"via the Read tool and not a Bash call"* clause STAYS. **That file alone carries a helper-interaction completeness claim** a silent new read could appear to violate (plan 92's Phase-4 record ruled the same way for the same reason, and ruled that `grill`, `review` and `fix` need no such clause). **Four files, one clause, by their own text — not a uniformity edit.**

**The NIT, applied, and its cosmetic residual recorded.** The value printed for an absent or null tier is **`not configured`**, never `inherit` — **`inherit` is an AGENT-file literal and printing it in a command's advisory line would name a mechanism that does not apply there.** ⚠ **The re-check notes the sentence then composes to *"configured think model: not configured"*, which reads awkwardly; accepted as cosmetic and NOT fixed**, because every alternative wording either drops the tier word or stops being byte-identical across the eight.

**What landed.** **`q11-tiers.md`** — intro re-derived (eight fields, four tiers, **both file classes**, `apply-models`, and the turn-scoped-override sentence); **`## Q11.4 — Security tier`** in the Q11.2/3 shape (one call, two questions, `opus (Recommended)`, the refusal-risk description **number- and version-free**); the zero-alias arm now says the tier **stays unconfigured with no default**; **`## Defaults rationale` → `## Recommendations`** with five one-sentence reasons and **six** honest bounds; `## Saving the answers` gains `security`. **`configure/main.md`** — Phase 4 intro: **twelve** user-only prompts (Q9, Q10, Q11 × 8, Q12 mode, Q13) across **four** Q11 calls; Phase 5 sub-step **5.4 renamed `Apply models`**, both classes, the per-class null split (**agent `inherit` / command no line**), the JSON with `kind`/`name`, exit codes 0/1/2 with **five** validation causes, and the `update.sh` paragraph (after the command re-emit; the pre-merge snapshot normalization; `agents N (M changed), commands K (L changed), skipped S`; one line per changed file of either class); **counts COUNTED live: schema 37, populated 36 = 24 + 12, keys 45 = 37 + 5 + 3**; plan 89's `regression_gate` note **updated in place with its guidance verbatim**; a new `.claude/commands/devforge/*.md` Outputs bullet; the Closing. **`agents-AUTHORING.md`** — the `model_tier` row (four tiers; `model: inherit` + `model_tier:`; `apply-models`; **no default anywhere**); the **`model_pin` row DELETED**; **plan 92's contract note KEPT VERBATIM with a `SUPERSEDED` prefix**; a new dated (2026-09-04) contract-change note recording the field's whole life — *removed the day after it was added*; the reviewer-family clause now naming `security-reviewer`'s tier (**family ≠ tier**, with `api-designer` as the counter-example); the checklist; and every cite re-derived live (`generate-agents.py` `:328`→`:307`, `:195`→`:187`, `:278`→`:251`, plus `:219`–`:220` and `:264`; **the `install_defaults.py:39` cite removed with the module**). **`security-reviewer.md`** — `model_tier: security`, the `model_pin` line deleted, **zero body bytes**. **The eight advisory steps** — ONE sentence each, **byte-identical across the eight modulo the tier word** (`verify` keeps its one decided extra clause): print `not configured` for an absent or null tier, state that the tier has no configured model so the command carries no override and runs on the session's model, and name `apply-models` as what writes `inherit` onto that tier's agents (**provenance only, NOT invoked**). **`storage-rules.md` checked: it names none of the affected terms — a verified no-op.**

**Three deliberate divergences from this plan's Phase-2 text.**

1. **The eight advisory sentences also took the verb RENAME**, which the scope bullet assigned to the provenance clause only — **the no-primary-name grep demanded it**: leaving `apply-agent-models` in eight command specs would have left the alias, not the verb, as the name a consumer reads.
2. **Two Q11.1 effort-option descriptions were widened**, because effort now reaches **commands** as well as agents and the original wording described agents alone.
3. **Plan 92's contract note gained a `SUPERSEDED` prefix** rather than being left untouched, **so a reader of that paragraph ALONE cannot believe the pin is live.** ⚠ **The note's own text is byte-unchanged** — this is a prefix, not an edit to plan 92's reasoning.

**Verify — results as they came back.** `judgment work belongs to the` → **8 files**; `print \`not configured\`` → **8**; **both tripwires 0 over `src/`**; `apply-agent-models` survives in `src/` markdown **exactly once**, as the alias mention in `configure/main.md`; `model_pin` under `src/` appears **only** in `agents-AUTHORING.md`'s history and its removal note; **`src/CLAUDE.md` needs nothing** — checked, recorded as a finding rather than a silence.

⚠ **Carry-forwards handed to Phase 3, and its scope is widened by this record.** `CHANGELOG.md`, repo-root `CLAUDE.md`, `PLAN-STATUS-ARCHIVE.md`, `DEVELOPMENT-STATUS.md` and `docs/v2/ARCHITECTURE.md` still name `apply-agent-models`, the deleted default map and/or the `security-reviewer` pin. **And one finding that is NOT this plan's to fix:** the documented `${CLAUDE_EFFORT}` substitution variable **falsifies the premise of plan 92's OQ-2** (*the advisory line stays silent about effort because the session's level is invisible*). **RECORDED, NOT REOPENED** — plan 92's decision stands until a plan takes it up deliberately.

### Phase 3 — Docs, ledgers, and the plan-92 amendments *(instruction-only)* — **BUILT 2026-09-04** (commit pending)

**Route: instruction-author → instruction-reviewer**, plus `claude-code-guide` for `src/CLAUDE.md` if it is touched (it ships as the consumer's root `CLAUDE.md`; plan 08's always-on-trim discipline binds, and **"checked, nothing to amend" is a finding to record**, not a phase that failed).

Open with `grep -rn "apply-agent-models\|model_pin\|CLAUDE_AGENT_DEFAULTS_BY_TIER\|scan\b" src/ scripts/ *.md docs/` and reconcile every hit. **This sweep list is NOT certified exhaustive** — treat a hit not named below as an omission in this plan, not as a new defect.

Scope: **`CHANGELOG.md`** (one `## [Unreleased]` entry stating the honest bounds — the override is turn-scoped, the framework now ships no model, an org allowlist silently wins, and the security pin became a question); **repo-root `CLAUDE.md`** (this plan's index line, **and the plan-92 line amended** with a dated pointer); **`PLAN-STATUS-ARCHIVE.md`** (the mirrored full entry, plus the same amendment on plan 92's); **`DEVELOPMENT-STATUS.md`** (both tier sites plan 92 corrected — they now describe a default map that no longer exists); **`docs/v2/ARCHITECTURE.md`** (⚠ **narrowly — only the sites THIS plan falsifies**, per the maintainer's 2026-09-03 pick on plan 92; its unrelated stale counts stay a separate item); and **`92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md`** itself, per D6.

⚠ **WIDENED BY PHASE 2's BUILD (2026-09-04) — the five files above are now carry-forwards with a named reason, not a precaution.** Each still names **`apply-agent-models`** (renamed at Phase 1), **`CLAUDE_AGENT_DEFAULTS_BY_TIER`** (deleted) and/or **the `security-reviewer` pin** (now a question), so **each carries at least one sentence this build has already falsified.** ⚠ **`src/` is DONE and `docs/` + the ledgers are NOT** — a sweep that greps only `src/` will report clean over the half Phase 2 already fixed. **One further item is recorded and explicitly NOT actioned here:** the documented `${CLAUDE_EFFORT}` substitution variable falsifies the premise of plan 92's OQ-2 (*the advisory line stays silent about effort because the session's level is invisible*). **Phase 3 records it where it lands and reopens nothing** — plan 92's decision stands until a plan takes it up deliberately, and this plan's D4 leaves the printed sentence unchanged.

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **`grep -rn "CLAUDE_AGENT_DEFAULTS_BY_TIER" .`** returns hits only in maintainer records that describe it as removed — **never in `src/`, `scripts/` or `tests/`.**
- **Every plan-92 amendment named in D6 exists, is dated, and edits no build record.** ⚠ **The Trap 3 note carries its transition caveat** — a note reading "no longer applies" without the once-per-install clause is false in the release that matters.
- **Plan 63's counts were read LIVE and this plan's delta is ZERO** — the check is recorded whether or not the numbers moved. ⚠ **What the rule demands is the live read, not a particular result** (plan 92's Phase-5 record made exactly this correction).
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass — a failure means something unintended moved in the agent roster.
- **The `CHANGELOG.md` entry states the bounds.** An entry claiming commands "run on the configured model" without "for that turn" and "unless your organization excludes it" has over-claimed by two layers.
- **Commit style read from the live `git log`** — subject lowercase and terse with a scope prefix; **read the trailer convention from the log, never from a remembered sentence** (plan 92's Phase-5 record retired its own clause on exactly this).

**This phase appends a `#### Phase 3 build record` block.**

#### Phase 3 build record (2026-09-04)

**BUILT; the commit is pending.** Executed against the LIVE tree with Phases 1 and 2 already committed (`5d3e134`, `db6088f`), and with the maintainer's confirmation that no other session held uncommitted edits. **EIGHT target files edited plus this plan's own file — NINE in total — and `src/` deliberately untouched**, Phase 2 owning that half and this phase not re-opening it. **The eight:** `92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md`, `15-AGENT-STANDARDIZATION-PLAN.md`, `70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`, `DEVELOPMENT-STATUS.md`, `CHANGELOG.md`, repo-root `CLAUDE.md`, `PLAN-STATUS-ARCHIVE.md`, `docs/v2/ARCHITECTURE.md`. ⚠ **Plan 70 was the LAST of the eight and was added mid-phase**, from this phase's own sweep rather than from its scope list — see its entry below.

**The plan-92 amendments (D6) — SIX dated blocks in the body plus ONE clause on the Status line, seven sites in all — with no build record edited and no phase re-opened.** The Status-line clause names this plan and its four reversals; **D1**'s null-tier bullet gained the `inherit` / no-line rule plus the rename and the moved `update.sh` seat; **D2 half 1** is REVERSED at its own site, with **half 2 explicitly surviving as a LABEL** (`verify = sonnet` is a `(Recommended)` marker, no longer a written value); **D6** is REPLACED, and the note says plainly that the *"fifth `security` tier"* alternative D6 rejected is what shipped — **not because its surface got cheaper but because the framework may no longer make the choice at all**; **OQ-5** is RESOLVED AFFIRMATIVELY with its four costs mapped rather than dissolved, and records that D7's advisory line **survives and gains a job**; **Trap 3** is CLOSED BY CONSTRUCTION in three clauses that must travel together (cannot recur · fires once, mitigated · the residual is wider than a hand-edited file). ⚠ **Phase 6's anchors were RESTATED as a dated block BELOW the anchor list rather than rewritten in place**, so the original 1b and 3 stay readable and the change is visible — 1b now expects whatever Q11.4 chose, and 3 additionally checks a mapped command after the re-emit.

**The other seven target files.** `15-AGENT-STANDARDIZATION-PLAN.md` — one dated note under plan 92's, recording that `model_pin` was **removed the day after it was added**, that `model_tier` is now `think | do | verify | security`, and that every agent emits `model: inherit`; **plan 15's reasoning is untouched**. `DEVELOPMENT-STATUS.md` — both sites plan 92 had corrected (`:58`'s key list, now naming `CLAUDE_TIER_SECURITY` and both file classes; item 14, rewritten around four tiers, no framework default, the eight mapped commands, the two `update.sh` seats and the turn-scoped override) with a **second dated sub-bullet** beside plan 92's, ending *"build-verified, NOT consumer-validated"*. `CHANGELOG.md` — one `### Added` entry at the top of `## [Unreleased]` in the house's dense single-bullet style, carrying the evidence split, what shipped, and every honest bound; ⚠ **it never says "runs on Fable" and carries no version string**, and plan 92's own entry gained a bracketed amendment clause **in the shape plan 93 used on plan 85's entry**, because both entries describe the same unreleased cycle and would otherwise contradict each other. Repo-root `CLAUDE.md` — the plan-92 line amended and a plan-94 line added; ⚠ **the new line was first placed between 92 and 93 and then MOVED**, because that index is ascending and 93 is its last entry. `PLAN-STATUS-ARCHIVE.md` — the same amendment on plan 92's entry plus the mirrored full plan-94 entry in position. `docs/v2/ARCHITECTURE.md` — **narrow, per the maintainer's standing pick on plan 92** (*"fix only the falsified sites"*): the overview counts, the setter table's user-prefs row (8 → 10 with the two `-security` setters), the Apply row (verb name, both classes, both `update.sh` seats, the no-default rule), the schema line (35 → 37 fields, `ENUM_FIELDS` 8 → 9 with `claude_effort_security` named), §4.3's heading formula and its user-only list (10 → 12, four Q11 calls), the phase diagram's Q11 line and its Phase-7 counts, the two tree comments, the `(A)` row, and **the design-decision bullet on the non-enum `claude_tier_*` fields — rewritten from "Recommended defaults" to "Recommendations, not defaults — the framework writes no model of its own", with `security=opus` added to the list** (that bullet is the one site in the file where the old defaults read as a framework choice rather than as a count). **The `~32 subcommands` staleness recorded by plan 92 stays untouched**, as its pick directs. **`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`** — a dated note appended under the paragraph whose two citations this build killed (`scripts/lib/install_defaults.py:30` and the tier→model map): the module and the map are deleted, agents emit `model: inherit`, the models come from the install's own Q11 answers via `apply-models`, and the tier names moved (`scan` out, `security` in). ⚠ **The note also states the consequence for that plan's OWN work — the tier→model assignment is now a property of the INSTALL being profiled, not of the framework, so a Phase-2 measurement must record the profiled install's configured models rather than assume the old mapping.** **Plan 70's reasoning is untouched**, and its observation that the cost is turn volume rather than tier misassignment is explicitly left standing.

**Verify — results as they came back, and two of them are findings rather than passes.**

- **`grep -rn "apply-agent-models"` over the repo (excluding `done-plans/`) — every survivor classified, none a live primary name.** In `src/` markdown it appears **exactly once**, as the alias sentence in `configure/main.md`; in `docs/` once, as the alias parenthetical in the Apply row; in code as the argparse `aliases=[…]` registration and its docstrings (`_cli.py`, `generate-agents.py`) plus two test sites that exercise the alias; everywhere else it is a plan record, a ledger entry or a dated history quote.
- ⚠ **TWO STALE CODE COMMENTS FOUND AND NOT FIXED — outside this phase's file list, handed to the orchestrator.** `src/devforge/lib/_configure/_render.py:371` still says *"on every `configure_helper apply-agent-models` run"* and `_cli.py:543` still names the old verb in a comment. **Both are shipped-tree comments the Phase-1 rename did not reach**; neither changes behavior, and **a Phase-3 that edited them would have crossed into a Python phase**.
- **`grep -rn "CLAUDE_AGENT_DEFAULTS_BY_TIER\|install_defaults"` — zero live references.** The only `src/` hit is `agents-AUTHORING.md`'s history note; the only `tests/` hits are a docstring describing the deletion. ⚠ **ONE DANGLING REFERENCE FOUND — and FIXED after the orchestrator widened this phase's file list:** `70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md:35` cited `scripts/lib/install_defaults.py:30` and the four-tier default map **as live**, and that module no longer exists; it now carries a dated note (above). ⚠ **It was found by the sweep, not by the scope list** — which is what the scope list's own *"treat a hit not named below as an omission in this plan"* clause exists for.
- **`grep -rn "model_pin"` — history and removal machinery only.** `src/agents-AUTHORING.md` (the `SUPERSEDED`-prefixed note and the new one), the emitter's removal guard and its warning string, the transition tests that assert the warning and assert **zero** warnings over the real roster, and plan/ledger records.
- **Both tripwire patterns over the eight edited files: ZERO hits in anything this phase wrote.** ⚠ **Pre-existing hits exist and are correctly left alone** — plan 92's `## Model facts` and its own discussion of the two patterns, `CHANGELOG.md`'s plan-92 entry quoting them as examples, `CLAUDE.md:74` and two `PLAN-STATUS-ARCHIVE.md` entries. **All are outside `src/`, so the live gate's scope is unaffected**; `docs/v2/ARCHITECTURE.md` returns zero.
- **Plan 63's counts read LIVE: `^disable-model-invocation:` over `src/commands/` returns exactly FOUR** (`constitute`, `generate-docs`, `init-forge`, `configure`) — **16/4, and this plan's delta is ZERO.** ⚠ **The rule demands the live read, not a particular result**, and the read is recorded here whether or not it moved.
- ⚠ **NOT RUN BY THIS PHASE, and named rather than implied: the `tests/` suite, `scripts/verify-agent-reachability.py`, `scripts/verify-memory-lane.py` and `model_version_tripwire.py`.** Phase 1's record carries their results from the code phase (full suite green, both verifiers 0, tripwire PASS); **this phase edited no `src/`, `scripts/` or `tests/` file, so it re-ran none of them** — the orchestrator re-runs them at commit time.

**One deliberate divergence from this phase's own scope text.** The scope named `docs/v2/ARCHITECTURE.md` for *"only the sites THIS plan falsifies"*; the sweep also found the phase diagram **missing a `Phase 5.4` line entirely** — a plan-92 omission, not a falsified statement — and **left it**, recording it here instead. **A narrow fix stays narrow only if it also refuses the adjacent gap.**

### Phase 4 — Consumer e2e *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim any of this has been observed on a real install.

**Batched per plan 92's OQ-4** — after plan 85's baseline wall-clock run, and after plan 92's own anchors, never before.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **The framework ships no model.** Fresh install, before `/devforge:configure`. **MUST** produce: every `.claude/agents/*.md` carrying `model: inherit`, and **no `.claude/commands/devforge/*.md` carrying a `model:` line at all.**
2. **The choice reaches both classes.** Configure with `think = <alias A>` and `security = <alias B>`, A ≠ B and neither equal to the session model. **MUST** produce: `.claude/commands/devforge/plan.md` carrying `model: <A>`, `.claude/agents/architect.md` carrying `model: <A>`, `.claude/agents/security-reviewer.md` carrying `model: <B>`. **Scored as a PAIR with anchor 1** — an apply that writes everything passes 2 and fails 1; one that writes nothing passes 1 and fails 2. **Neither is meaningful alone.**
3. **An update preserves all three, and the ordering is the thing under test.** Change an agent BODY in `src/`, run `update.sh`. **MUST** produce: the body change merged; `model: <A>` still on the command file **after** the re-emit; the apply summary naming both classes. ⚠ **Record whether any agent reported a merge conflict.**
4. **The transition merge.** From an install configured BEFORE this build (its agents carrying a static tier default in the snapshot and a different configured value live), run `update.sh` across the release. **MUST** produce: no conflict on the `model:` line, the body update applied, and the snapshot refreshed. **This is the only observation D2's bound (i) ever gets on a REAL install** — Phase 1's local reproduction runs the same recipe against a scratch target and is a build observation, never this anchor.
5. **The readback (D8).** With `/model` set to something other than `<A>`, run `/devforge:plan`. **MUST** print the advisory line whose second half names `<A>`. ⚠ **`unknown` is NOT a pass here** — unlike plan 92's anchor 5, this anchor is the override's only evidence, and an `unknown` result means the anchor could not be scored, which is a finding about the harness rather than about D1.
6. **Subagent inheritance — an OBSERVATION, never a gate.** Inside the same overridden turn, dispatch one agent carrying `model: inherit` and record which model it reports. **There is no MUST here**: the behavior is undocumented (guide answer 2), and **whatever it returns is recorded in this plan, not treated as a pass or a failure.**
7. **A never-configured install stays silent.** No question, no line claiming a default, and every command and agent on the session model.

**Verify:**

- All seven anchors are scored **explicitly** — stated, not summarized. **Anchors 1 and 2 are scored as a PAIR.**
- **Anchor 3 greps the command file AFTER the update**, not before — the whole point of the block move.
- **Anchor 6's result is written into this plan verbatim**, whichever way it goes, and **any `src/` sentence that would have to change because of it is named.**
- **If it fails**, record the negative with artifacts and identify which mechanism produced it before proposing anything: commands not rewritten is a D1 finding; a command rewritten but reverted after update is a D1 **seat** finding; an agent carrying a default instead of `inherit` is a D2 finding; `security-reviewer` on the wrong model is a D3 finding; a stray `effort:` line is a D5 finding; a conflicted transition merge is D2's bound (i) landing. **They have different fixes.**
- **A clean run is NOT evidence that any model is better than any other.** It is evidence the configuration path works, and **nothing in this plan measures model quality at all.**

---

## Non-goals

- **Validating model × effort compatibility.** D5's bound — inherited from plan 92 D4 unchanged.
- **The availability probe.** Plan 92 D5 ships as-is; this plan adds a fourth tier to the questions the probe precedes and changes nothing about the probe itself.
- **Any gate, `verify-*` number, or hard-fail validator.** D7 — plan 75's tripwire, both halves.
- **Reviving the `scan` tier.** D2 part 4 retires it; a future tier needs its own members and its own question.
- **A per-command (not per-tier) model question.** D1's map is per-tier by construction; OQ-2 records the widening path for the SET, never for the granularity.
- **Changing plan 63/93's invocability split.** D7 — 16/4 untouched, no `description` widened, no flag moved.
- **Back-porting into shipped installs.** They arrive via `update.sh` and a re-run of `/devforge:configure`.
- **Pinning any model version inside `src/`, in either shape.** The tripwire test enforces it; a consumer may pin through the free-text row, the framework may not.
- **A cost dashboard, a spend estimate, or any priced claim in emitted text.** Plan 92's `## Model facts` stays in plan 92.
- **Changing which agents exist, or which tier any agent belongs to** beyond `security-reviewer`'s move (D3).
- **Prompt de-prescription for any model.** Plan 92 D8, unchanged and not revived here.
- **Reconciling the two Claude Code version numerals** the docs and plan 92's Step-0 record carry (`### Claude Code authoring surface`). Recorded, not resolved.

---

## Dependencies + related

- **`92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md`** — the direct parent. **D2 half 1 reversed, D6 replaced, OQ-5 resolved affirmatively, Trap 3 closed-with-a-caveat, D1's null-tier sentence corrected, Phase-6 anchors 1b and 3 restated** (D6). ⚠ **Its build records are NOT edited and its Phase 0 close is NOT re-opened.** Its Phase-3 record item (c) is this plan's only reproduced mechanical evidence.
- **`93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md`** — makes 16 commands model-invocable, which is what turns D1's bound (iii) from theoretical into live: **a model-invoked command switches the session's model for that turn.** No count moves here.
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** — the emitted layout (`.claude/commands/devforge/<name>.md`) D1 writes into, and the standing coordination rule to read the counts LIVE. ⚠ **That rule earned itself on plan 92's Phase-5 sweep (2026-09-03), when the counts had moved 13/7 → 16/4 inside a day** — never quote a remembered figure.
- **`15-AGENT-STANDARDIZATION-PLAN.md`** and `src/agents-AUTHORING.md` — the meta-block contract D3 edits for the second time in days. **Plan 15's reasoning is not edited.**
- **`89-TEST-FOUNDATION-HARDENING-PLAN.md`** — the byte-consistency test precedent D1's map↔advisory pin copies, and the D6 `regression_gate` note living inside a file Phase 2 edits (**updated in place, never removed**).
- **`90-E2E-TEST-LANE-PLAN.md`** — the `FIELD_DEFAULTS`-baseline route that avoided a `_cmds_verify.py` exemption; D3's new effort field takes the same shape (`"default"` is a real enum member).
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number / no-new-validator tripwire. **Both halves hold** (D7).
- **`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`** — its Phase-5 batching decision is what Phase 4 queues behind. ⚠ **`D7` is an overloaded token across this repo** — plan 85's D7 is the grill cost line, plan 89's D7 is test-meaningfulness, plan 92's D7 is the per-command advisory, and **THIS plan's D7 is the scope tripwire.** Every cross-reference names the plan.
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — the English-only rule binding every byte of this plan and everything it emits, and the predicted-gap-with-no-incident framing `## Evidence constraint` copies for its directive half.
- **`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`** — the always-on-trim discipline binding any `src/CLAUDE.md` edit at Phase 3.
- **`26-REINTRODUCE-FIX-PLAN.md` / `88-COLD-FIX-BUGS-LANE-PLAN.md`** — the *"extend the one binary, never a second composer"* rule D1's alternative (b) is rejected under. **Cited for the stance; neither is edited.**

---

## Context for next session

**The one sentence that governs everything here:** the framework chooses no model anywhere — every agent ships `inherit` and every command ships nothing — and the user's per-tier answers are written by one idempotent helper verb into **both** agent and command frontmatter, at configure time and again after every update, **below the step that re-emits commands.**

**Trap 1 — believing the command override already exists.** It does not. Emitted command frontmatter today is `name`, `description`, optional `argument-hint` and the four setup commands' `disable-model-invocation` (fact 17). **Any sentence in this build saying "the command runs on the configured tier's model" is FALSE until Phase 1's verb extension and the `update.sh` move both land.**

**Trap 2 — writing a model version into `src/`, in EITHER shape.** The tripwire asserts two patterns, `claude-[a-z]+-[0-9]` and `\b(opus|sonnet|haiku|fable)[\s-]+[0-9]`, case-insensitive (fact 18). ⚠ **The second is the one that catches real prose** — a security-question description explaining a refusal risk is the likeliest place in this plan's edits to write one.

**Trap 3 — inventing a marker key in command frontmatter.** Unknown-key handling for local command files is **not documented**, and the same docs page shows the upload path failing hard on an unexpected key with an enumerated allowlist. **`metadata:` is the documented escape hatch** and D1 declines it on other grounds. **A build that adds a bare `model_tier:` line to a command has crossed both the decision and the evidence.**

**Trap 4 — assuming a subagent with `inherit` follows a command's override.** ⚠ **Undocumented, and the design leans on it looking either way**: if it inherits, an overridden `/devforge:plan` turn runs its architect on the tier's model for free; if it does not, the agent runs on the session model while the orchestrator runs on the tier's. **Phase 4's anchor 6 records which; nothing before it may assert either.**

**Trap 5 — assuming a command's `model:` line survives.** `update.sh` re-emits every promoted command wholesale (fact 12) and `install.sh` does the same on a re-install (fact 14); **there is no snapshot and no merge for commands** (fact 13). The line survives **only** because the apply call runs after the re-emit. **Move that block and the feature evaporates silently** — the files look right until the next update.

**Trap 6 — incrementing the configure counts instead of counting them.** Drafting-time: `FIELD_SCHEMA` 35, `_PROJECT_CONFIG_KEY_ORDER` 43, `ENUM_FIELDS` 8, `FIELD_DEFAULTS` 6, four pin assertions, five prose sites in `configure/main.md` (facts 7, 8). **D3 moves all of them.** ⚠ **Those figures are a dated observation and this trap binds them too** — count the live tuples.

**Trap 7 — reading `inherit` as "no model".** They are different: `inherit` is step 2 of the documented resolution order and beats `CLAUDE_CODE_SUBAGENT_MODEL`; **an absent line falls through to that variable first.** This is exactly why OQ-5 recommends the explicit line, and it is the one place where deleting a line would quietly hand the choice to someone else.

**Trap 8 — treating a clean Phase 4 as evidence about models.** Every anchor observes the configuration and override path. **Nothing in this plan measures whether any model is better for any tier**, and plan 92's own A/B is the only thing that ever will.

**The working tree carries uncommitted work throughout**, and several plans this file cites are working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`${CLAUDE_EFFORT}` is a DOCUMENTED substitution variable** carrying the session's current effort level (`### Claude Code authoring surface`). **Plan 92's OQ-2 decided the advisory line stays silent about effort** because the session's level was invisible — **that premise is now false for effort, though it remains true for the model.** ⚠ **This plan does NOT reopen that decision**; it records the variable so a future plan does not re-derive it, and D4 leaves the printed sentence unchanged.
2. **`install_defaults.py` has exactly one symbol** (fact 3), so D2's deletion is a module deletion with a three-file blast radius including a test-side by-path loader that exists to dodge a `lib/` shadowing problem. **A build that deletes only the dict leaves an importable empty module and a loader with nothing to load.**
3. **The docs name two different Claude Code versions** for two different claims about subagent model resolution (`### Claude Code authoring surface`). **Neither is reconciled here**, and no `src/` sentence depends on either.
4. **`agents-AUTHORING.md`'s fixity clause has now been extended twice on consecutive days** — once to add `model_pin` (2026-09-03), once (D3) to remove it (2026-09-04). **Nothing in that file counts its extensions**, and a third would be indistinguishable from the second unless each note names its plan and date.
5. **`configure/main.md`'s Phase 5.4 mis-quotes `update.sh`'s summary line** (OQ-4's own note). The spec says *"Applied agent models: N agents (M changed, K skipped)"*; the script prints *"Applied agent models: N with model_tier (M changed), K skipped"*. **Pre-existing, introduced when plan 92's Phases 2 and 3 were written in parallel** — the same parallel-execution hazard that plan's build records name twice. **Recorded here; OQ-4 is where it gets fixed, in both sites at once.**

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — eighteen rows, each checkable in under a minute. **If rows 2, 3, 10, 11, 12, 13 or 17 no longer hold, stop and re-derive**: they are the default map's owners, the advisory-line set, the command emission path, the update ordering and the invocability split.
2. **Read `update.sh` from the apply block to the version marker in one pass** — the block, `mergeFiles`, the promoted-command re-emit, the stale-command prune, the marker. **The move's correctness is a property of that whole stretch**, not of the two comment lines it sits between.
3. **Read `_configure/_agent_models.py` and `_cmds_agent_models.py` in full before extending them.** The two-pass structure, the CRLF handling (`read_bytes().decode()` — `Path.read_text()` would flatten a consumer's line endings), the atomic per-file write and the non-transactional batch bound are all load-bearing and none is obvious from the verb's name.
4. **Read `scripts/generate-agents.py:191`–`:300` before touching the emitter.** `emit_claude`'s field order is part of every consumer's merge baseline, and `_MODEL_PIN_RE` exists because a reviewer demonstrated a version string entering `src/` through that field.
5. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** — `CLAUDE_AGENT_DEFAULTS_BY_TIER`, `_claude_tier_model`, `VALID_TIERS`, `judgment work belongs to the`, `Execute: apply-agent-models`, `Execute: re-emit promoted dir-shaped commands`, `The contract is **fixed**`, `## Defaults rationale`, `_PROJECT_CONFIG_KEY_ORDER`, `## [Unreleased]`.
6. **Invoke the `claude-code-guide` agent before writing or amending any frontmatter — and note WHERE that lands: at Phase 1's Step 0, BEFORE any code.** This plan writes into **two** Claude-Code-integration surfaces, agent files and command files, and the command surface is new. ⚠ **Cite plan 92's Step-0 record for the three questions it already answered; ask only the two this plan's design added.**
7. **Route every edit through the house loops:** python-engineer → python-reviewer, test-first, for Phase 1 (**with `claude-code-guide` FIRST**); instruction-author → instruction-reviewer for Phases 2 and 3, with `claude-code-guide` added for every command-spec, agent-frontmatter and `src/CLAUDE.md` edit. **Phases 2 and 3 dispatch no python-engineer** — a phase that finds itself needing one has crossed its own boundary and must stop.
8. **Every file byte stays English** (plan 87), including this plan, every emitted question, every option label and every advisory line — regardless of any operator response-language setting. **The Ukrainian directive in `## Origin` is a verbatim quote of a user-reported sentence, which that rule permits.**
9. **Read `## Phase 0 close record` before re-deciding anything.** The four forks it names — the transition mitigation with D2, the contract change, the `scan` retirement, OQ-2's width — are **answered**, and **three of them reverse or narrow a decision another plan ratified**, which is why each is amended at plan 92's own site rather than only here. ⚠ **The closure was ONE blanket directive, so a ratified item carries exactly the argument written in its decision body and no more** — re-opening one means arguing against that text, not against the ratification.
