# 92 — Agent model & effort configuration: a live tier knob, version-free model choice, and a per-command session-model advisory

**Status:** **✅ DONE (build) 2026-09-03 — Phase 0 CLOSED (every item ratified AS RECOMMENDED by a single blanket maintainer directive) and Phases 1–5 BUILT. Phase 6 consumer e2e DEFERRED — user-driven HARD GATE, NOT run, and BATCHED behind plan 85's wall-clock baseline per OQ-4.** Commits: `2f6e409` Phase 1 · `7dea6a3` Phase 2 · `c05e5e7` Phase 3 · Phases 4 and 5 built in the same pass, **Phase 4 reviewed CLEAN and Phase 5's docs sweep corrected after review**. **Everything is build-verified and NOT consumer-validated.** ⚠ **AMENDED IN PLACE 2026-09-04 by `94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md`, which reverses D2 half 1, replaces D6, resolves OQ-5 affirmatively and closes Trap 3 by construction — every amendment is a DATED BLOCK at its own decision; no phase is re-opened, no build record is edited, and this plan stays DONE (build).**

- **Every decision below keeps its alternatives and its honest bound, and ratification changed
  neither.** ⚠ **The closure came as ONE blanket directive and no per-item deliberation was
  supplied** — see `## Phase 0 close record`, which says so plainly rather than implying nine
  separate arguments were had. **Ratifying a recommendation does not strengthen it**, and a build
  that reads a ratified bound as discharged has left this plan.
- **The plan has TWO halves and they carry different evidentiary weight.** One **observed,
  grep-verified defect** (`/devforge:configure` Q11 persists three answers that nothing reads)
  and **four maintainer directives** dated 2026-09-03 that ask for capability the framework has
  never had. **The defect half is a repair; the directive half is a predicted-gap feature in
  plan 87's class**, and no summary may blur them. ⚠ **Ratification did NOT move that line** —
  a directive that was ratified is still a directive, never a finding.
- **Phase 6 is a user-driven consumer e2e HARD GATE** and is NOT part of the build. Everything
  Phases 1–5 produce will be build-verified and **NOT consumer-validated**. **OQ-1 is the one
  ratified item Phase 6 may overturn with data**; every other answer stands until re-opened.

**Branch:** `develop-2.0-init`
**Created:** 2026-09-03.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

**There is ONE observed defect behind this plan and NO consumer incident.** The evidentiary base
is (a) a maintainer question dated 2026-09-03 — the framework runs mostly on Opus and Sonnet;
should Fable enter, and where — (b) the `src/` sweep that question triggered, whose results are
the rows of `## Verified mechanics`, and (c) four maintainer directives given the same day,
recorded in `## Origin`.

The defect (fact 8) is **grep-verified and real**: three configuration answers are collected,
validated, persisted and rendered, and read by nothing. **Everything else is directive-driven
capability, not incident-driven repair** — nobody has reported a wrong model on a wrong tier,
nobody has measured that Fable helps this pipeline, and nothing here has been observed to fail
in a consumer run. **Say both halves wherever this plan is summarized**, and never let a later
session read the directive half as an observed loss.

Model-behavior facts quoted in `## Model facts` come from the bundled `claude-api` skill cached
2026-06-24. **They are decision inputs and they never reach `src/`** — a priced, dated,
version-bound claim written into emitted text is exactly the rot this plan exists to avoid.

---

## Origin — a question, a sweep, one defect, and four directives, 2026-09-03

**The question.** The maintainer asked whether Fable should enter a framework that runs mostly on
Opus and Sonnet, and if so where. Nothing in the question named a failure.

**What the sweep found — one defect and three gaps.**

**1. The defect: Q11's answers are write-only.** `/devforge:configure` Phase 4 asks three
sequential AskUserQuestion calls — one per tier — validates each answer through its own setter,
stores it in `.devforge/configure.yaml`, and renders it into `.devforge/project-config.json` as
`CLAUDE_TIER_THINK` / `CLAUDE_TIER_DO` / `CLAUDE_TIER_VERIFY` (facts 4, 5, 6, 7). **A grep for
those key names across `install.sh`, `update.sh`, `src/` and `scripts/` returns hits only inside
`_render.py`, which writes them** (fact 8). No agent file carries a `{{CLAUDE_TIER_*}}`
placeholder, so `substitute-file` never touches an agent's `model:` line. **The emitted `model:`
is fixed at generation time from a static map** (facts 1, 2), and it stays fixed no matter what
the user answered. The question is asked, the answer is stored, and the answer changes nothing.

**2. Two unbuilt intents are documented as if they existed.** `install_defaults.py`'s own
comment says *"Wizard's Q10a may override per tier"* and `generate-agents.py`'s says *"The
post-install config step may OVERWRITE these via key-based regex replacement when
project-specific answers are available"* (facts 1, 2). **Neither override exists anywhere in the
tree.** They are the design that was intended and never built, and they read as ground truth to
a fresh session.

**3. Two shipped documents disagree about the verify tier, and a third describes a feature
that does not exist.** `q11-tiers.md` recommends `verify = Haiku`; `install_defaults.py` ships
`verify: sonnet` (fact 9) — and because of the defect, **every install to date got sonnet**
regardless of what the user picked. Separately, `DEVELOPMENT-STATUS.md:104` claims the tiers are
*"Configurable via `/devforge:configure` (`MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY` in
project-config.json)"* — **stale key names on top of a false claim**, and its parenthetical
enumeration of think-tier agents is incomplete besides (fact 10).

**4. There is no effort surface at all, and no version-free way to name a model.** No
configuration field, no frontmatter line and no question anywhere touches `effort`. Q11's option
lists are three capitalized alias labels plus a free-text `Other` (fact 4), and the labels are
stored verbatim — `Opus` with a capital O, where Claude Code's alias is lowercase `opus`
(fact 5).

**The four directives (maintainer, 2026-09-03, paraphrased and recorded as directives, not as
findings):**

- **(a)** Offer the model choice per tier, and have the LLM show the current versions at run
  time, so **the framework never has to be updated for new model versions.**
- **(b)** Also ask the effort level.
- **(c)** For certain commands, give a recommendation of what to use. **The maintainer is
  undecided for `/devforge:plan` — Opus or Fable** (OQ-1).
- **(d)** Not everyone has Fable access; **it must degrade cleanly.**

**The direction this plan proposes:** make the existing knob LIVE (a helper verb rewrites agent
frontmatter from configuration), keep the choice VERSION-FREE (aliases, never a pinned ID,
enforced by a tripwire test), add EFFORT as a sibling of the model question, PROBE availability
before offering an alias, and print a one-line ADVISORY at the commands where the choice
matters. ⚠ **The advisory was drafted because a command was believed unable to set its own session
model; fact 19 was CORRECTED on 2026-09-03 and it can.** The advisory ships anyway, by maintainer
decision — the override is deferred to its own decision at OQ-5.

### The rejected alternative, with its reasoning (recorded so it is not re-proposed)

The cheapest move is to **change the static map and stop there** — edit
`CLAUDE_AGENT_DEFAULTS_BY_TIER` to whatever the maintainer wants today, delete Q11, and let the
emitter be the only writer. It is rejected on three independent grounds, any one of which
decides it:

- **It answers none of the four directives.** No per-project choice (a), no effort (b), no
  version-freedom (a again — a map edit is exactly the framework update directive (a) forbids),
  and no degradation path for an install without Fable access (d).
- **It deletes a question users have already answered.** Existing installs carry stored Q11
  answers in `.devforge/configure.yaml`. Deleting the question strands them silently; making the
  knob live honours them (D1's designed consequence).
- **It moves the framework further from its own documentation, not closer.** Three files already
  describe a per-tier override (facts 1, 2, 10). Deleting the knob makes all three false in a new
  way instead of making them true.

A fourth, weaker objection is recorded because it will be raised: a static map cannot express
"Fable where available, Opus otherwise", so it forces the framework to choose for every install.
That is a capability argument; the three above are correctness arguments.

---

## What is actually being added

Six things. **Phase 0 ratifies each independently; a future session must not read any one as
depending on the others** — except D2/D4, whose dependency is named at D4's own bound.

1. **An apply mechanism** (Phase 1) — a `configure_helper apply-agent-models` verb that rewrites
   `.claude/agents/*.md` frontmatter from `.devforge/project-config.json` (D1). **Python.**
2. **Effort as a first-class configuration field** (Phase 1) — three enum-restricted fields, three
   setters, three render keys (D4). **Python.**
3. **A version-free question surface** (Phase 2) — Q11 rewritten: probe first, then one call per
   tier carrying BOTH the model and the effort question, with full model IDs offered only as
   session-known suggestions inside the tool-injected `Other` arm (D3, D4, D5). **Instruction.**
4. **One per-agent pin** (Phases 1–2) — an optional `model_pin` meta field, applied to exactly one
   agent, `security-reviewer` (D6). **Python + instruction.**
5. **A post-merge apply call in `update.sh`** (Phase 3) — so a configured install keeps its choice
   through an update instead of silently reverting (D1). **Shell.**
6. **A per-command session-model advisory** (Phase 4) — one always-printed, never-gating line at
   PHASE 0 of a small command set (D7, OQ-2). **Instruction-only.**

**⚠ Four honest bounds that must survive into every emitted sentence:**

- **This build does not choose the orchestrator's model.** D7 prints a recommendation and enforces
  nothing, so a summary claiming the framework "sets the model per command" has over-claimed by a
  full layer. ⚠ **CORRECTED 2026-09-03 — the reason is a DECISION, not a limitation.** The drafted
  clause read *"the framework cannot … `model` and `effort` are agent-only frontmatter fields"*;
  fact 19 now says commands share the skill frontmatter and **can** carry both. **The bound stands
  for what this build does; the impossibility claim does not** (OQ-5).
- **Nothing validates model × effort compatibility.** The docs say *"available levels depend on
  the model"* (fact 18) and this plan builds no compatibility table — building one would be
  exactly the version maintenance directive (a) exists to avoid. **An unsupported combination
  fails at dispatch, not at configure** (D4).
- **The availability probe observes THIS session.** It answers "can this Claude Code build, in
  this session, dispatch a subagent on this alias" — never "does this organization hold Fable
  entitlement" and never "does this account permit 30-day retention" (D5).
- **Nothing here is evidence that Fable helps this pipeline.** OQ-1's A/B at Phase 6 is the only
  measurement this plan will ever produce, and until it runs the think default stays `opus`.

---

## Verified mechanics (2026-09-03)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token is
the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the
string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **The tier default map, and its false comment.** `CLAUDE_AGENT_DEFAULTS_BY_TIER: dict[str, str] = {"think": "opus", "do": "sonnet", "verify": "sonnet", "scan": "haiku"}`, under a comment reading *"Claude's `model:` field takes a short tier name (`opus`, `sonnet`, `haiku`), not a full model ID. Wizard's Q10a may override per tier."* ⚠ **That override does not exist in the tree** (fact 8). The file's own docstring calls itself *"the single source of truth for those defaults"* | `scripts/lib/install_defaults.py:27`–`:35`, `:21` |
| 2 | **The emitter writes `model:` from that map, under a second unbuilt-intent comment.** `_claude_tier_model(tier)` is a bare dict lookup; `emit_claude(...)` renders frontmatter in the fixed order `name`, `description`, optional `tools`, `model: <alias>`, optional `applies_to`. The section comment reads *"The post-install config step may OVERWRITE these via key-based regex replacement when project-specific answers are available."* ⚠ **No such step exists** — recorded as unbuilt intent, not as a missing file | `scripts/generate-agents.py:156`–`:161`, `:164`–`:165`, `:168`–`:197` |
| 3 | **Tier census — 19 agents, and `scan` has no members.** `think` ×5: `api-designer`, `architect`, `devils-advocate`, `security-reviewer`, `spec-formalizer`. `do` ×9: `backend-engineer`, `db-engineer`, `devops-engineer`, `frontend-engineer`, `migration-engineer`, `mobile-engineer`, `qa-engineer`, `runtime-debugger`, `tech-writer`. `verify` ×5: `ac-verifier`, `code-reviewer`, `design-auditor`, `performance-analyst`, `qa-reviewer`. `scan` ×0 | `grep -n "^model_tier:" src/agents/*.md`, 2026-09-03 |
| 4 | **Q11's shape.** `/devforge:configure` Phase 4 carries *"Three sequential AskUserQuestion calls — Q11.1 (think), Q11.2 (do), Q11.3 (verify)"* and delegates the text to a reference file. Each call offers `Opus \| Sonnet \| Haiku \| Other`; `Other` is *"let me name a different model"* followed by a plain free-text prompt. Its `## Defaults rationale` states *"Recommended defaults: `think = Opus`, `do = Sonnet`, `verify = Haiku`"* | `src/commands/configure/main.md:301`–`:303`; `src/commands/configure/references/q11-tiers.md:1`–`:43` |
| 5 | **The setters store free text with NO normalization.** `_cmd_set_claude_tier` runs `_validate_scalar` (non-empty) and writes the value verbatim; its docstring says *"These fields are NOT enum-restricted (see ENUM_FIELDS comment) — they accept any non-empty scalar so users can name custom Claude routes via Q11's `Other` branch."* ⚠ **So the stored value is the capitalized OPTION LABEL — `Opus` — while Claude Code's alias is lowercase `opus`** | `src/devforge/lib/_configure/_cmds_set.py:487`–`:518` |
| 6 | **The schema's non-enum choice is deliberate and documented.** The three `claude_tier_*` entries are plain `"scalar"`s, under a comment stating they are *"intentionally NOT enum-restricted: users may pick the recommended Claude tiers (Opus/Sonnet/Haiku) OR a custom model alias (Bedrock route, self-hosted, or future model name) via the Q11 `Other` branch"* | `src/devforge/lib/_configure/_schema.py:56`–`:60`, `:88`–`:95` |
| 7 | **The render keys exist and ship null.** `_PROJECT_CONFIG_KEY_ORDER` carries `CLAUDE_TIER_THINK` / `CLAUDE_TIER_DO` / `CLAUDE_TIER_VERIFY` under a `# From configure.yaml (user preferences)` comment, and the shipped template renders all three as `null` | `src/devforge/lib/_configure/_render.py:56`–`:61`; `src/devforge/project-config.json:37`–`:39` |
| 8 | ⚠ **THE DEFECT. `CLAUDE_TIER_*` has no consumer.** A grep for those key names over `install.sh`, `update.sh`, `src/` and `scripts/` returns hits **only in `_render.py`**, which writes them. No file under `src/agents/` carries a `{{CLAUDE_TIER_*}}` placeholder, so `configure_helper substitute-file` never reaches an agent's `model:` line. **Three questions are asked, validated, persisted and rendered, and read by nothing** | repo grep, 2026-09-03 |
| 9 | ⚠ **Two shipped documents disagree about the verify tier.** `q11-tiers.md` marks `Haiku` *"(Recommended)"* for Q11.3 and repeats it in `## Defaults rationale`; `install_defaults.py` ships `"verify": "sonnet"`. **Because of fact 8, every install to date got sonnet** | `q11-tiers.md:32`, `:43`; `install_defaults.py:33` |
| 10 | ⚠ **`DEVELOPMENT-STATUS.md` describes a feature that does not exist, with names that do not exist.** *"Configurable via `/devforge:configure` (`MODEL_THINK`, `MODEL_DO`, `MODEL_VERIFY` in project-config.json)"* — **the claim is false (fact 8) AND the three key names are wrong** (fact 7 gives the live names). The same line's *"Think (opus — architect, api-designer, security-reviewer)"* names three of the FIVE think-tier agents (fact 3) | `DEVELOPMENT-STATUS.md:104` |
| 11 | **How an agent file reaches a consumer on update — five steps, and the merge is the load-bearing one.** Agents are regenerated from `src/agents/` into `REGEN_AGENTS_DIR`; the regen is copied to a temp file; `substitute_placeholders()` runs on it (skipping the file entirely on exit 2, and skipping ALL agents when `HAS_CONFIG` is false: *"Skipped $tgt — no .devforge/project-config.json; run /configure"*); `git merge-file <current> <substituted-baseline> <substituted-regen>` merges it against `.devforge/template/<tgt>`; on success the file is written and **the baseline snapshot is refreshed with the RAW regen**. An agent absent from the snapshot is copied in under **first-write semantics** — *"we do NOT skip on unresolved placeholders"* | `update.sh:806`–`:874`, `:825`–`:833`, `:851`–`:856`, `:876`–`:902` |
| 12 | **`update.sh` already calls a `configure_helper` verb — precedent for calling another.** `substitute_placeholders()` shells out to `configure_helper substitute-file` under a `HAS_CONFIG` guard, and the config-rebuild branch calls `configure_helper render-config` directly | `update.sh:316`–`:321`, `:331`–`:333` |
| 13 | **`install.sh` snapshots the EMITTED agents and ships no meta-block sources.** `mkdir -p "$TARGET_DIR/.devforge/template/.claude/agents"` then `cp -R "$TARGET_DIR/.claude/agents/." …`. ⚠ **A grep of `install.sh` for `src/agents` returns ZERO hits** — the nearest thing is a generator comment that never contains the literal, `# Install-time generators (scripts/generate.sh → generate-agents.py /` — so a target install carries only emitted agent files, never the `model_tier:`-bearing sources. **This is D1's whole reason for emitting the tier** | `install.sh:428`–`:433`, `:75`; repo grep 2026-09-03 |
| 14 | **The live counts, and the FOUR assertions that pin them.** `FIELD_SCHEMA` = **32** entries (`test_field_schema_has_32_fields` and `test_default_state_has_32_keys`, adjacent); `_PROJECT_CONFIG_KEY_ORDER` = **40** keys (`test_all_40_keys_present` over `_build_project_config`, and `test_renders_40_keys_with_defaults` over a `render-config` round trip). ⚠ **The brief that commissioned this plan named TWO pins; there are FOUR assertions in three sites** | `tests/lib/test_configure_helper.py:170`, `:174`, `:3371`, `:3528`; `_schema.py`, `_render.py:15`–`:18` |
| 15 | **`configure/main.md`'s four count sites.** *"fills 31 configuration fields"*; *"Once `configure.yaml` is fully populated (31 fields set)"*; *"The schema carries 32 fields; the 31 this command populates are set in Phase 3 (24 detection-derived values) and Phase 4 (7 user-only prompts)"* — plan 89's D6 `regression_gate` note, which also carries its own no-prompt instruction; and the completion message's *"The 31 configuration fields … all 40 keys"*. **Plans 89 and 90 established the rule: COUNT the live tuples and write what you counted, never increment a printed number** | `src/commands/configure/main.md:9`, `:326`, `:339`, `:506` |
| 16 | **The meta-block contract, and its own fixity clause.** `agents-AUTHORING.md`'s table is `name` / `description` / `model_tier` / `tools` / `applies_to`, introduced by *"The contract is **fixed** — author to it, never change it."* Its `model_tier` row reads *"Emitted as `model:` — `think→opus`, `do→sonnet`, `verify→sonnet`, `scan→haiku` (`install_defaults.py:30`). **Not a placeholder.**"* and its `applies_to` row asserts *"Claude Code ignores the unknown key"* | `src/agents-AUTHORING.md:13`, `:15`–`:21` |
| 17 | **The advisory-line precedent, in full.** `plan_helper stakes-hint` *"always exits 0"*, prints nothing in the ordinary case, and its spec says *"This hint is ADVISORY and NON-BLOCKING: it never blocks the approve flow, it gates nothing on its own, and the user is free to ignore it."* | `src/commands/plan/main.md:675`–`:686` |
| 18 | **No model version string of EITHER shape exists under `src/` today — the tripwire's baseline is CLEAN on both patterns.** The API-ID pattern `claude-[a-z]+-[0-9]` returns **zero** hits, and the display-name-with-version pattern `\b(opus\|sonnet\|haiku\|fable)\s+[0-9]` (case-insensitive) **also returns zero** — ⚠ **two patterns are required because the first catches `claude-opus-5` and misses `Opus 5` / `Haiku 4.5` / `Fable 5.1` entirely.** A bare `\b(opus\|sonnet\|haiku\|fable)\b` grep, case-insensitive, hits **8 files**, every one in a known class: the three `_configure` modules (tier comments + the non-enum rationale), `q11-tiers.md` (the question text), `agents-AUTHORING.md:19` (the tier→alias row), and three cost-estimate prose sites (`generate-docs/main.md`, `pr-review/main.md`, `_pr_review/_ensure_cbm.py`) | repo greps, 2026-09-03 |
| 19 | ⚠ **CORRECTED 2026-09-03 — the drafting-time reading was WRONG, and this row now states the opposite.** **Commands SHARE the skill frontmatter, `model` and `effort` INCLUDED**: `slash-commands` states *"Files in `.claude/commands/` support the same frontmatter, except `name` and `paths`, which Claude Code ignores in a command file"*, and that frontmatter table carries both fields. **So a command CAN set the model for its own turn** — see `### Claude Code authoring surface` for the verbatim quotes. The earlier *"agent-only"* sentence, attributed to `plugins-reference.md`, is **not on that page today** (re-fetched 2026-09-03). ⚠ **D7's advisory line is therefore a CHOICE, not the only available mechanism** — the override is possible, documented, and **deliberately not taken** (D7's alternatives; OQ-5) | `code.claude.com/docs/en/slash-commands`, re-fetched 2026-09-03 |
| 20 | **The Agent tool exposes a `model` parameter whose enum is `sonnet \| opus \| haiku \| fable`.** A Claude Code build whose enum lacks a value fails the call with a validation error — which is what makes D5's probe fail-safe rather than fail-open. ⚠ **UPGRADED 2026-09-03 at Phase 2's guide pass: this is DOCUMENTED**, not merely observed — `sub-agents.md` specifies the per-invocation `model` parameter as accepting those four aliases, full IDs, or `inherit`. **So D5's probe stands on documented ground**; the drafting-time "harness-injected and UNDOCUMENTED" reading is withdrawn | session tool schema 2026-09-03; `code.claude.com/docs/en/sub-agents.md`, verified 2026-09-03 |
| 21 | **The harness states the session model in its system prompt** (*"You are powered by the model named …. The exact model ID is …"*) and lists recent model IDs. ⚠ **OBSERVED in this session, NOT documented.** Any design resting on it must degrade to `unknown` | session system prompt, 2026-09-03 |
| 22 | **AskUserQuestion's shape constraints.** 1–4 questions per call; each question 2–4 options; **the tool injects its own `Other` free-text option**, so an authored `Other` is never written. ⚠ **OBSERVED in this session's tool schema and UNDOCUMENTED, exactly like facts 20 and 21.** ⚠ **Consequence for D4: ONE call can carry both the model question and the effort question for a tier.** ⚠ **Consequence for D5: an option list can hold at most four named aliases, and at least two.** ⚠ **Degradation: if either bound changes, D4's two-questions-per-call design and D5's option filtering must be RE-VERIFIED against the live schema before Phase 2 writes `q11-tiers.md`** | session tool schema, 2026-09-03; `src/commands/configure/main.md` bulk-confirm + `src/commands/grill/main.md` PHASE 7 as live examples |

### Claude Code authoring surface, verified against current docs

Fetched **2026-09-03** from `https://code.claude.com/docs/en/sub-agents.md` and
`https://code.claude.com/docs/en/plugins-reference.md`. **Cited so a future author re-verifies
rather than trusting this file.**

- **`model` accepts an alias, a full ID, or `inherit`.** Aliases: `sonnet`, `opus`, `haiku`,
  `fable`. Full IDs: e.g. `claude-opus-5`. `inherit` uses the main conversation's model.
- **⚠ Omitting `model:` is NOT the same as `inherit`.** The documented resolution order is:
  per-invocation `model` parameter → the subagent's own `model` frontmatter (where `inherit`
  selects the main conversation's model) → the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
  → the main conversation's model. **An environment variable sits between the frontmatter and
  the session model**, so "delete the line and it inherits" is false. D1 keeps a `model:` line on
  every emitted agent, which makes this moot today and a trap tomorrow (Trap 5).
- **⚠ `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` overrides the frontmatter ENTIRELY.** Set to `1`, every
  subagent runs on `CLAUDE_CODE_SUBAGENT_MODEL` **regardless of its own `model:` line** — so it
  sits ABOVE the frontmatter in the order above, not below it. **This is the one documented way to
  defeat everything D1 builds**, it is a consumer's environment rather than a repo file, and
  **the framework cannot detect it** (D1's honest bound; Trap 5).
- **`effort` accepts `low | medium | high | xhigh | max`**, with *"available levels depend on the
  model"*, and its documented default is **"inherits from session"** (*"Overrides the session
  effort level. Default: inherits from session."*). ⚠ **This CORRECTS the drafting brief's
  "no documented default"** — and it strengthens D4: removing the `effort:` line is a documented
  inherit-from-session behavior, not an appeal to an unknown harness default.
- **⚠ Unknown-key handling is NOT documented.** The sub-agents page enumerates its fields
  (`name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`,
  `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`,
  `initialPrompt`, `experimental`) and says nothing about keys outside the list; it documents only
  that a file is skipped when its *"YAML doesn't parse"*. **So D1's `model_tier:` line rests on
  REPO PRECEDENT — `applies_to` has shipped as an unknown key since plan 15 (fact 16) — and not
  on documentation.** ⚠ **ASKED AND ANSWERED 2026-09-03 at Phase 1's Step 0, and the answer is
  still NOT a documented guarantee**: the page enumerates the conditions under which a subagent
  file is SKIPPED and an unknown key is not among them, but nothing states that unknown keys are
  ignored. **The STOP arm did not trigger and the bound did not close** — see the
  `#### Phase 1 build record — Step 0` block for the two-part footing this rests on.
- ⚠ **REFUTED 2026-09-03, and the correction is the important one on this page.** The drafting-time
  bullet read *"`model` and `effort` are agent-only … a command cannot set its own session model,
  which is D7's entire premise"*, citing a plugins-reference sentence. **That sentence is not on
  that page today** (re-fetched), and `slash-commands` says the opposite: *"Files in
  `.claude/commands/` support the same frontmatter, except `name` and `paths`, which Claude Code
  ignores in a command file."* **A command may therefore carry `model:` and `effort:`.**
- **`model` in a command/skill, verbatim:** *"Model to use when this skill is active. The override
  applies for the rest of the current turn and is not saved to settings; the session model resumes
  on your next prompt. Accepts the same values as `/model`, or `inherit` to keep the active model. A
  value excluded by your organization's `availableModels` allowlist is not used and the session
  keeps its current model. With `context: fork`, the value sets the forked subagent's model
  instead."* ⚠ **Two properties matter for OQ-5**: the override is **turn-scoped**, and an
  org-excluded value **degrades silently to the current model** rather than failing.
- **`effort` in a command/skill, verbatim:** *"Effort level when this skill is active. Overrides the
  session effort level."*
- ⚠ **What this does NOT change: the ratified mechanism.** D7 ships the advisory line as ratified.
  **What changes is its standing** — it is a chosen option beside a documented stronger one, not the
  only thing available. **OQ-5 records the fork and the maintainer's pick.**

⚠ **This section is the DRAFTING-TIME record (2026-09-03, two pages). It was EXTENDED the same day
by Phase 1's Step 0**, which added a third page — `https://code.claude.com/docs/en/model-config.md`
— and four recorded answers, including the effort silent-fallback rule and the pre-v2.1.251
resolution-order caveat. **Read `#### Phase 1 build record — Step 0` alongside this section; neither
supersedes the other, and the Step-0 block is the newer of the two.**

### Model facts — cached 2026-06-24, decision inputs ONLY

From the bundled `claude-api` skill. ⚠ **These are dated, priced, version-bound claims. They
inform D2, D5, D6 and OQ-1 and they NEVER reach `src/`** — writing any of them into emitted text
would rot on the next model release, which is the exact failure directive (a) forbids.

- **Price per MTok (in / out):** Fable 5.1 $10 / $50 · Opus 5 $5 / $25 · Sonnet 5 $2 / $10 ·
  Haiku 4.5 $1 / $5. **Fable is the most expensive of the four**, and *"at `low`, Fable 5.1 is
  often competitive with Opus and Sonnet on cost per task"*.
- **Fable's documented bug-finding gains EXCLUDE security-focused analysis** where cyber
  classifiers apply, and such a request can end with `stop_reason: "refusal"`. **This is D6's
  whole reason.**
- **Fable requires 30-day data retention** — a zero-data-retention organization receives a 400.
- **The `effort` parameter errors on Haiku 4.5.** ⚠ **So an `effort:` line on a haiku-aliased
  agent may fail, which is a live collision with D4 and is why D2 declines Haiku for the verify
  tier.** A `claude-code-guide` check of what Claude Code does with `effort:` on a `haiku` agent
  was **owed at Phase 1's Step 0 and is ANSWERED (2026-09-03)** — the API's behavior and Claude
  Code's **do** differ: **Claude Code falls back SILENTLY** to the highest supported level at or
  below the one set, and Haiku is not among the effort-supporting models. ⚠ **So this row's
  API-level claim must never be restated as Claude Code behavior** — it weakened D2 half 2's fourth
  reason; see the `#### Phase 1 build record — Step 0` block.
- **Prompts written for prior models are often too prescriptive for Fable** and reduce its output
  quality. **This is D8's whole reason**, and it cuts against a heavily prescriptive command
  corpus (OQ-1).
- **Fable turns run longer.** Relevant to OQ-4's ordering and to Phase 6's wall-clock number.

---

## Decisions (D1–D9) — ALL RATIFIED 2026-09-03

Each carries the recommendation, the alternatives with the reason each is rejected, and the
**honest bound — what the decision does NOT achieve.** **The bounds are load-bearing: a decision
ratified with its bound deleted cannot be re-opened honestly later.**

### D1 — The apply mechanism: a `configure_helper apply-agent-models` verb *(RATIFIED 2026-09-03 — arm (b), the helper verb)*

**RECOMMENDED RULE — arm (b), a new helper verb.** A new `configure_helper apply-agent-models`
verb, over a new module under `src/devforge/lib/_configure/` (**exact filename chosen at Phase 1**,
per house layout), rewrites the YAML frontmatter of every `.claude/agents/*.md` from
`.devforge/project-config.json`:

- **`model:`** ← the agent's tier value from `CLAUDE_TIER_<TIER>`, normalized (D3) or a pinned
  full ID.
- **`effort:`** ← the tier's `CLAUDE_EFFORT_<TIER>` level, **or the `effort:` line is REMOVED**
  when that tier's effort is the `default` sentinel (D4).
- **Keyed on a NEW emitted frontmatter line `model_tier: <tier>`.** A file without `model_tier:`
  is left untouched — which is what makes D6's pin work and what keeps a consumer's hand-written
  agent safe.
- **Idempotent.** Running it twice changes nothing the second time.
- **A `null` tier value applies that tier's DEFAULT** (D2), so an install that never answered Q11
  lands exactly where it lands today.
  ⚠ **AMENDED 2026-09-04 (plan 94 D1/D2): a null tier now writes `model: inherit` on an AGENT and
  NO `model:` line on a COMMAND** — there is no tier default left to apply. **The verb is also
  RENAMED `apply-models`** (it writes both file classes now), with `apply-agent-models` kept as an
  argparse alias for one release, and **its second seat moved**: in `update.sh` it runs after the
  promoted-command re-emit rather than before `mergeFiles`, because that re-emit overwrites every
  command file. **Everything else in this decision stands as built.**

**Where it runs — two seats, both existing:** `/devforge:configure` Phase 5 as a **fourth
sub-step** (`render-config` → `prune-agents` → `substitute-templates` → `apply-agent-models`),
and `update.sh` **after its merge loop**, under the same `HAS_CONFIG` guard `substitute_placeholders()`
already uses (facts 11, 12).

**The emitter KEEPS writing a static `model: <tier default>`, and does NOT write `effort:`.** A
freshly installed, not-yet-configured project therefore has a valid model line — today's bytes —
until apply runs.

**Why the tier must be EMITTED rather than looked up.** A target install carries only the emitted
`.claude/agents/*.md` and their raw snapshot; **the `model_tier:`-bearing sources under
`src/agents/` are never shipped** (fact 13). Without an emitted `model_tier:` line the verb has
no way to know which tier an agent belongs to that does not duplicate the 19-agent roster inside
Python — which is the fact-belongs-beside-the-agent principle D6 also rests on.

**The three-way-merge interaction, stated so no phase re-derives it** (fact 11). A configured
consumer file carries e.g. `model: fable`; the substituted baseline and the substituted regen
both carry the static default; `git merge-file` sees base and other identical and **keeps the
consumer's line**. The post-merge apply then rewrites it from configuration anyway, which is what
makes the result deterministic **either way** rather than dependent on a merge outcome.

**Alternatives considered:**

- *(a) A placeholder — `model: {{CLAUDE_TIER_THINK}}` — substituted by the existing renderer.*
  **REJECTED on two grounds.** First, **string substitution cannot REMOVE a line**, so D4's
  `default` sentinel has no expression: every agent would carry an `effort:` line whose value is
  a word Claude Code does not accept. Second, **before `/devforge:configure` runs the frontmatter
  would carry a raw `{{…}}` as its model value** — `install.sh` ships agents with placeholders
  intact for the later `/configure` to fill (fact 11's first-write comment says so in as many
  words). **Today no roster agent is dispatched before `/devforge:configure`** — verified
  2026-09-03: `/devforge:init-forge` names no subagent at all, and `/devforge:generate-docs` is
  explicitly orchestrator-direct (*"No subagent dispatch"*, and *"NO Task-tool dispatch to any
  compose subagent"*, `src/commands/generate-docs/main.md:13`, `:28`) — **but that is an invariant
  nothing enforces**, and the failure would be a dispatch against an unparseable model value.
  ⚠ **One sub-question is left to Phase 1 rather than asserted here:** what `substitute-file`
  does with a `null` config value for a known key. **Verify at build** — the argument above does
  not depend on the answer.
- *(c) `sed` in `install.sh` / `update.sh`.* **REJECTED**: shell duplicating a Python owner, against
  this repo's standing *"extend the one binary, never a second composer"* rule (plan 26's own
  2026-06-19 note, re-affirmed by plan 88's D3). A frontmatter rewrite is structured editing, and
  the helper-owns-shape principle puts it in the helper.
- *(d) Do nothing — delete Q11 instead.* Recorded in `## Origin`'s rejected alternative with its
  three grounds. A ratifier who wants it should decline this plan, not this decision.

**⚠ Designed consequence, and it must be stated at the seat where it happens.** An existing install
whose stored Q11 answer differs from the shipped default — most obviously an `Other` route, but
equally a user who picked `Haiku` for verify — will have its agents **SWITCH on the next
`update.sh`.** **That is the dead knob coming alive, not a regression**, and `update.sh` prints what
it applied so the change is visible in the run rather than discovered later.

**⚠ Honest bound — what this does NOT achieve.** It does not validate that the configured model
exists, is entitled, or supports the configured effort (D4's bound); it does not reach a consumer's
hand-written agents (no `model_tier:` line, by design); and **it does not make the emitted static
default irrelevant** — an install that never runs `/devforge:configure` still gets the map, and a
future change to that map can produce a merge CONFLICT on the `model:` line for every configured
install (Trap 3). **Verify the conflict behavior at Phase 3** rather than trusting this sentence.
✅ **VERIFIED 2026-09-03 — it DOES conflict, and the bound is LARGER than this paragraph says.** The
conflicted file's **whole update is skipped, body included**, its snapshot goes **stale**, the
condition **recurs on every later update**, and the post-merge apply then makes the `model:` field
read correct **while the stale body stays invisible** — the only signal is a decoupled
`Merge conflicts in <file>` warn. **This is an OPEN residual, not a closed question**; see
`#### Phase 3 build record` item (c) for the two candidate repairs, neither built.

**⚠ The second honest bound, and it is the larger one: a consumer environment can defeat this
mechanism completely.** With `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` set, **every subagent runs on
`CLAUDE_CODE_SUBAGENT_MODEL` regardless of its frontmatter `model:` line**
(`### Claude Code authoring surface`). Every agent this verb writes is then ignored — the pin at
D6 included — **and the framework cannot detect it**: the variable lives in the consumer's
environment, not in any file this repo reads. **No mechanism here can close that**, and a
Phase-6 anchor that fails while that variable is set is an environment finding, not a D1 finding.

### D2 — One owner for the tier default map, and `verify = sonnet` *(RATIFIED 2026-09-03 — BOTH halves, `verify = sonnet`, ratified TOGETHER with D4)*

**RECOMMENDED RULE, two halves.**

**Half 1 — where the apply-time default lives.** The apply-time default literal lives in the
consumer helper (`src/devforge/lib/_configure/`); `scripts/lib/install_defaults.py` keeps its own
literal for the emitter; **a maintainer test pins the two EQUAL**, on plan 89's byte-consistency
precedent (`storage-rules.md` ↔ `_DONE_WHEN_FIXED_LINES`). The alternative — importing
`scripts/lib/install_defaults.py` from `src/devforge/lib/` — is a **cross-boundary import from the
maintainer tree into the shipped tree**, and `src/devforge/lib/` is what gets copied onto a
consumer where `scripts/` does not exist. ⚠ **Phase 1 must check whether any precedent for such an
import exists before choosing** — the recommendation is the duplicate-plus-test, and a found
precedent is a reason to revisit it, not to ignore this sentence.

⚠ **REVERSED 2026-09-04 by plan 94 D2, on a maintainer directive: *"there must be no defaults, the
user chooses."*** **The tier default map is GONE from both trees** — `CLAUDE_AGENT_DEFAULTS_BY_TIER`
was deleted from `scripts/lib/install_defaults.py` (the module itself was `git rm`'d, that literal
having been its only symbol) and from `src/devforge/lib/_configure/_agent_models.py`, and the
`DefaultMapEqualityTests` pin that half 1 designed went with them. **Every emitted agent now carries
the constant `model: inherit`**, which the vendor documents as selecting the main conversation's
model and which — unlike an omitted line — sits ABOVE `CLAUDE_CODE_SUBAGENT_MODEL` in the resolution
order. **The question surface is unchanged and half 2 survives in the only form it can**: the Q11
`(Recommended)` labels stay, `verify = sonnet` among them, **as recommendations printed beside an
option — no longer as a value the framework writes into any file.** ⚠ **What that costs is stated
at plan 94's D2: a never-configured install now runs every agent on the session model, which is the
directive working as asked and a real behavior change from what this plan shipped.**

**Half 2 — the verify tier is `sonnet`, and `q11-tiers.md`'s Haiku recommendation is corrected.**
Four reasons were offered, the last one mechanical — ⚠ **and that fourth reason was WEAKENED on
2026-09-03 by Phase 1's Step-0 findings; THREE stand.** The bullet is kept with its correction
attached rather than deleted, so the ratified reasoning can be re-read as it was argued:

- The five verify-tier agents do **judgment** work, not mechanical work — `ac-verifier` maps ACs
  to evidence, `code-reviewer` runs a ten-item checklist, `design-auditor` reads a two-tier
  compare (fact 3).
- Plan 15 tools-locked those agents as read-only reviewers precisely because their output is a
  judgment, not an edit.
- **Every install to date shipped sonnet** (facts 1, 9), so this half changes no observed
  behavior — it makes the recommendation match what has always been delivered.
- **Haiku 4.5 errors on `effort`** (`## Model facts`), so recommending Haiku while D4 adds an
  effort question ships a recommended combination that can fail.
  ⚠ **WEAKENED (answered 2026-09-03 — silent fallback in Claude Code, see the Phase 1 Step 0
  record).** That sentence describes the **API**, not Claude Code. Claude Code documents a silent
  fallback to the highest supported level at or below the one set, and Haiku is not among the
  effort-supporting models — **so the combination degrades quietly instead of failing loudly.**
  **This reason no longer carries weight on its own**; the three above are what hold half 2 up,
  and they are sufficient without it. ⚠ **The pairing with D4 is NOT withdrawn** — see D4's
  dependency paragraph, whose ground shifts from "known to fail" to "silently does less than the
  user asked for", which is a weaker harm but not no harm.

**The Q11 `(Recommended)` labels are derived from the same default literal** rather than written
independently, so the two cannot drift again.

**Alternatives considered:**

- *Keep Haiku recommended for verify and change `install_defaults.py` instead.* **REJECTED** for
  the four reasons above — and note it would be a behavior change for every existing install on
  its next update, dressed as a documentation fix.
- *Leave both documents as they are and let D1 make the disagreement user-visible.* **REJECTED**:
  D1 turns the disagreement from inert into live, so shipping D1 without D2 half 2 is the one
  combination that actively degrades installs (an install that answered `Haiku` because the
  document recommended it would move to Haiku the moment the knob works).

**⚠ Honest bound.** A pinned-equal test proves the two literals agree; it proves nothing about
whether the values are the RIGHT ones. **No measurement supports `think = opus` over `think =
fable`** (OQ-1), and none exists until Phase 6.

✅ **RATIFIED TOGETHER WITH D4, 2026-09-03 — and the pairing is why half 2 is not cosmetic.** The
blanket directive took **both halves of D2 and all of D4**, so `verify = sonnet` lands in the same
build as the effort question and the vendor's documented Haiku-plus-`effort` failure never becomes
a shipped recommendation. ⚠ **The dependency outlives the ratification**: moving the verify
recommendation back to Haiku later **re-opens D4's bound in that same edit.** The matching note is
at D4's own dependency paragraph. **The honest bound above is unchanged by any of this** — the
literals agree; nothing says they are right.

### D3 — Version-free model choice: aliases, with pinning available and a tripwire *(RATIFIED 2026-09-03 — as recommended)*

**RECOMMENDED RULE.** Q11's per-tier options are the four **aliases** — `opus`, `sonnet`,
`haiku`, `fable` — filtered to those D5's probe found available. Aliases float with Claude Code's
own mapping, so **the framework stores no version and never needs an update for a new one**
(directive (a)). The **tool-injected `Other` arm is the pin route**: any other non-empty scalar is
accepted verbatim as a full model ID.

**In the `Other` arm the orchestrator lists the full IDs it currently knows** from the harness's
environment statement (fact 21) as SUGGESTIONS, **labelled "as known to this session — unverified"**,
and **these are never written into any framework file.** That is directive (a)'s "show the current
versions at run time" satisfied without the framework knowing a single version.

**The setters NORMALIZE the four aliases to lowercase** and accept any other non-empty scalar as a
pin — preserving today's `Other` behavior exactly (facts 5, 6) while fixing the capitalization
mismatch that would otherwise reach `model: Opus`.

**The tripwire, so version-freedom is falsifiable rather than aspirational.** A maintainer test
asserts that **NEITHER version shape appears anywhere under `src/`** — the API-ID pattern
`claude-[a-z]+-[0-9]` **AND** the display-name-with-version pattern
`\b(opus|sonnet|haiku|fable)\s+[0-9]`, case-insensitive. ⚠ **Both patterns are required and the
first alone is not enough**: it catches `claude-opus-5` and misses `Opus 5`, `Haiku 4.5` and
`Fable 5.1` — which is exactly the prose shape a well-meaning author writes into a question, a
rationale or a `CHANGELOG` line. ⚠ **The baseline is already clean on BOTH** — each grep returned
zero hits at drafting time (fact 18) — so Phase 1 adds the STANDING test rather than discovering
the state.

⚠ **WIDENED AT BUILD, 2026-09-03 — the SHIPPED display-name pattern is
`\b(opus|sonnet|haiku|fable)[\s-]+[0-9]`, not the `\s+` form above.** Run C1's reviewer showed that
a HYPHENATED version (`sonnet-4-5`) slips **both** drafted patterns — the API-ID pattern wants a
`claude-` prefix and the `\s+` form wants whitespace. **The decision is unchanged; its regex was
too narrow to enforce it**, and the shipped form is the operative one. **Cite `[\s-]+` from here
on** — see `#### Phase 1 build record — Deliverables 1–5`.

**Recommended labels:** `think = opus` (until OQ-1's A/B), `do = sonnet`, `verify = sonnet` (D2).

**Alternatives considered:**

- *Query the Models API for the live list.* **REJECTED**: it needs an API key most Claude Code
  users do not hold (Claude Code authenticates the session, not the user's API account), and it
  puts a network call inside `/devforge:configure`, which today makes none.
- *Enumerate known full IDs in `q11-tiers.md` and refresh them per release.* **REJECTED** — it is
  precisely the maintenance directive (a) forbids, and the tripwire test exists to make its
  reintroduction fail loudly.
- *Store the alias but resolve it to an ID at apply time.* **REJECTED**: resolution needs a
  mapping the framework would have to maintain, reintroducing the same rot one layer down.

**⚠ Honest bound.** **An alias's meaning is whatever Claude Code maps it to that day, and the
framework deliberately does not know.** A consumer who needs a specific version pins it through
`Other` and **owns that pin forever** — nothing in this plan will ever tell them it went stale.

### D4 — Effort per tier: three enum fields, and `default` means "remove the line" *(RATIFIED 2026-09-03 — as recommended, TOGETHER with D2 half 2)*

**RECOMMENDED RULE.** Each Q11.N AskUserQuestion call carries a **SECOND question** — *"Effort for
this tier?"* — alongside the model question, which fact 22 permits (1–4 questions per call).
Options: `default (Recommended)` | `medium` | `high` | `xhigh`, with `low` and `max` reachable
through the tool-injected `Other` (the 4-option cap, fact 22).

**Three new enum-restricted fields** `claude_effort_think` / `claude_effort_do` /
`claude_effort_verify` ∈ `{default, low, medium, high, xhigh, max}` — **enum-restricted unlike
their `claude_tier_*` siblings**, because effort is a closed vendor enum while a model name is
not (fact 6's rationale applies to models and not to this). Schema **32 → 35** and project-config
keys **40 → 43** — ⚠ **both figures READ LIVE at build** (fact 14, fact 15's rule), never
incremented from this file. Three setters `set-claude-effort-{think,do,verify}`, three render keys
`CLAUDE_EFFORT_THINK` / `CLAUDE_EFFORT_DO` / `CLAUDE_EFFORT_VERIFY`.

**`default` ⇒ apply REMOVES the `effort:` line**, which the docs define as inheriting the session
effort level (`### Claude Code authoring surface`). It is a real, documented behavior with a name —
not an appeal to an unknown harness default.

**Alternatives considered:**

- *One effort question for all three tiers.* **REJECTED**: think and do want different levels by
  the vendor's own guidance, and a single answer would force the most expensive tier's level onto
  the highest-volume one.
- *A free-text effort field, matching `claude_tier_*`'s non-enum shape.* **REJECTED**: the values
  are a closed documented set, and a typo would ship an agent Claude Code cannot dispatch. The
  asymmetry with the model fields is deliberate and is stated in the schema comment.
- *No effort surface; document the vendor default instead.* **REJECTED** — directive (b) asks for
  the question, and the `default` option preserves the do-nothing outcome for anyone who wants it.

**⚠ Honest bound, and it is the sharpest one in this plan.** The docs say *"available levels
depend on the model"*, and **this plan builds NO compatibility validation** — building it would
be the version-tracking maintenance directive (a) forbids. **An unsupported model × effort
combination therefore degrades silently at dispatch (documented fallback), never at configure** —
in a run far from the choice that caused it, and with **no signal that anything was dropped.** The
known instance is Haiku (`## Model facts`), which D2 half 2 steers away from for the one tier that
recommended it — **that is a mitigation for one case, not a fix for the class.**

⚠ **The class is UNCHANGED by Step 0's answer, and the failure SHAPE is now documented rather than
guessed** (2026-09-03). Claude Code falls back to *"the highest supported level at or below the one
you set"*, so a user who picks `xhigh` on a model that tops out lower gets the lower level and is
told nothing. **Silent is arguably worse than loud here**: a dispatch error would at least surface
the mismatch at the moment it mattered, whereas a silent downgrade looks exactly like success.
**Nothing in this plan detects it.**

**⚠ Owed at build — ANSWERED 2026-09-03 (silent fallback in Claude Code, see the Phase 1 Step 0
record).** The `claude-code-guide` check of what Claude Code does with an `effort:` line on a
`haiku`-aliased agent was question 3 of Phase 1's Step 0, asked before any code landed. **The API
errors; Claude Code does not** — it falls back silently, and Haiku is not among the
effort-supporting models. **Phase 2 CITES that recorded answer rather than re-asking it.**

**⚠ D4 DEPENDS ON D2 half 2.** Taking D4 while recommending Haiku for the verify tier ships the
one recommended combination that is known to fail. **Ratify them together or state explicitly
which mitigation replaces the other.**

✅ **RATIFIED TOGETHER 2026-09-03 — the pairing held.** The blanket directive took **both** D4 and
D2 half 2 (`verify = sonnet`), so the combination never arises and **no substitute mitigation was
needed or offered.** ⚠ **The dependency does not expire with ratification**: a future change that
moves the verify recommendation back to Haiku **re-opens D4's bound in the same edit**, and this
paragraph is the record that says so. The matching note is at D2 half 2.

⚠ **The GROUND of this dependency shifted the same day, and the dependency survives on the weaker
ground** (Step 0, question 3). The paragraph above says *"known to fail"* — **in Claude Code it does
not fail; it falls back silently.** So recommending Haiku alongside an effort question would ship a
combination that **quietly ignores the user's effort answer** rather than one that errors.
**Weaker harm, still harm, and still invisible** — which is exactly the class D4's honest bound
says nothing here detects. **The pairing is NOT withdrawn**, and a future ratifier re-opening it
should argue against the silent-downgrade framing, not the error framing.

### D5 — Availability probe: four one-word dispatches before the first question *(RATIFIED 2026-09-03 — as recommended)*

**RECOMMENDED RULE.** Before Q11.1, the orchestrator dispatches — for **each** of the four aliases
— a minimal subagent via the Agent tool with `model: <alias>` and the fixed prompt *"Reply with
the single word OK"*. **Any error, or any non-OK reply, marks that alias unavailable in THIS
session.** One information line reports the four results. **Unavailable aliases are NOT offered**
as options; they remain pinnable through the injected `Other`, which is the escape a determined
user keeps.

**Instruction-only** — an Agent-tool call the orchestrator makes. **No Python, no new verb, no
config field.**

**Why it is fail-safe rather than fail-open** (fact 20): on a Claude Code build whose Agent-tool
enum lacks `fable`, the call fails **validation** and the probe records "unavailable" — which is
the correct answer for that build. A probe that inferred availability from anything else would
have to know which builds carry which enum.

**Alternatives considered:**

- *Probe `fable` only.* **REJECTED**: it special-cases one alias **on the assumption that the other
  three are universally available — an assumption this plan has no evidence for**, and directive
  (d) asks for clean degradation without naming which alias degrades. Four probes cost four
  one-word dispatches and remove the assumption entirely.
- *Ask the user "do you have Fable access?".* **REJECTED as unfalsifiable** — a self-attestation
  question invites a wrong answer that surfaces as a failed dispatch much later, and this repo's
  standing preference is a mechanical check over a claimed one.
- *Offer everything and let dispatch fail later.* **REJECTED**: the failure surfaces at the first
  `/devforge:plan` architect dispatch, in a different command, days from the configuration choice
  that caused it. That is directive (d) unsatisfied.
- *Probe once and cache the result in configuration.* **REJECTED for v1**: entitlement and build
  both change, and a cached "unavailable" would silently outlive the condition that produced it.
  **Recorded as the named widening path** if the four dispatches prove costly.

**⚠ Honest bound.** The probe answers **"can this session dispatch on this alias"** and nothing
else. It does not observe the organization's API plan, its data-retention setting (a
zero-data-retention org gets a 400 from Fable per `## Model facts` — possibly at dispatch, not at
probe), or whether the alias will still work tomorrow. **A green probe is not an entitlement
guarantee.**

### D6 — One per-agent pin: `security-reviewer` stays on `opus` *(RATIFIED 2026-09-03 — the contract extension ACCEPTED)*

**RECOMMENDED RULE.** A new **OPTIONAL** meta field `model_pin: <alias>` joins the
`agents-AUTHORING.md` contract table. The emitter writes `model: <pin>` and **NO `model_tier:`
line**, so D1's apply verb skips the file by its own untouched-without-`model_tier:` rule — one
mechanism, no exclusion list.

**Applied to exactly ONE agent: `security-reviewer` = `opus`.** The reason is in `## Model facts`:
**Fable's documented bug-finding gains EXCLUDE security-focused analysis where cyber classifiers
apply, and such a request can end with `stop_reason: "refusal"`.** A refused reviewer inside
`/devforge:implement`'s four-reviewer panel or `/devforge:grill`'s refutation pass surfaces as a
**missing verdict** — a panel that returns three opinions where four were required, in a gate that
reads panel-clean.

⚠ **This is an ADDITIVE CONTRACT EXTENSION to a table whose own text says the contract is
*"fixed — author to it, never change it"*** (fact 16). **It is recorded as such, with a dated
note at the table**, rather than slipped in — a future author must be able to see that the
fixity clause was consciously extended and by which plan.

**Alternatives considered:**

- *A fifth `security` tier.* **REJECTED**: a one-member tier is a pin with more surface — it adds
  a tier to `install_defaults.py`, to the AUTHORING enum, to the apply verb's map and to Q11's
  question list, to express one fact about one agent.
- *An exclusion set inside the apply verb (`_PINNED_AGENTS = {"security-reviewer"}`).*
  **REJECTED**: the fact belongs beside the agent, not in Python. A reader of
  `security-reviewer.md` must be able to see why it does not follow the tier, and a name in a
  helper is invisible from there.
- *No pin — let the configured think model apply everywhere.* **REJECTED** on the refusal risk
  above, which is a documented vendor behavior rather than a speculation.

**⚠ Honest bound, and it cuts both ways.** The pin is **a floor against one failure mode and a
ceiling against an informed consumer** who has reason to want Fable on security review. **The
cost is accepted, not answered.** It also protects against exactly one documented behavior — it
is not a claim that Opus reviews security better.

⚠ **REPLACED 2026-09-04 by plan 94 D3, under the same no-defaults directive that reversed D2 half 1:
a pin is a default with one member.** **`model_pin` is REMOVED from the `agents-AUTHORING.md`
contract** (its row deleted, this plan's contract-extension note KEPT VERBATIM under a `SUPERSEDED`
prefix and a second dated note recording the field's whole life — added 2026-09-03, removed
2026-09-04), the emitter now **ignores a `model_pin` declaration with one stderr warning** instead of
honouring it, and **`security-reviewer` moved onto a fourth tier `model_tier: security`** with its
own configuration fields (`CLAUDE_TIER_SECURITY` / `CLAUDE_EFFORT_SECURITY`) and its own question
**Q11.4**. ⚠ **The alternative this decision REJECTED — *"a fifth `security` tier … a one-member tier
is a pin with more surface"* — is exactly what shipped**, and the reason it now wins is not that the
surface got cheaper but that the framework may no longer make the choice at all. **The refusal
reasoning is not withdrawn: it is what Q11.4's description tells the user**, number- and
version-free. ⚠ **What is lost is stated at plan 94's D3: a guarantee became an informed choice, and
nothing validates the answer.**

### D7 — The per-command session-model advisory: one line, printed always, gating nothing *(RATIFIED 2026-09-03 — as recommended)*

⚠ **THE PREMISE BELOW WAS WRONG, corrected 2026-09-03 — and the ratified mechanism survives it.**
This decision was drafted, argued and ratified on the reading that a command *cannot* set its own
model. **It can** (fact 19, corrected): commands share the skill frontmatter and `model` / `effort`
are in it. **The advisory line ships as ratified and is unchanged** — what changes is its standing:
it is a CHOSEN option beside a documented stronger one, **not the only thing available.** The
maintainer's 2026-09-03 pick is to keep the advisory and treat the override as a separate decision;
**OQ-5 records the fork, the analysis and the pick.** Everything below is preserved as it was
argued, with the false clause struck at its own site.

**RECOMMENDED RULE.** ~~The framework **cannot** set the orchestrator's model — `model` and `effort`
are agent-only frontmatter fields~~ **(STRUCK 2026-09-03 — fact 19 now says the opposite; the
framework CAN, and this plan declines to)**, so directive (c) is satisfied by **ONE advisory line
at PHASE 0** of a small command set (OQ-2):

> This command's judgment work belongs to the `<tier>` tier; configured `<tier>` model:
> `<value>`; this session runs on: `<model the harness stated, or unknown>`.

**Printed always. Never a gate. Never a question.** Plan 75's tripwire holds in both halves and
`stakes-hint` is the precedent (fact 17): always exit 0, gates nothing, the user is free to
ignore it.

**The recommendation is expressed as a TIER, resolved through the consumer's own Q11 answer.** So
it carries no version, it tracks the consumer's choice rather than the framework's opinion, and
**the maintainer's open "`/devforge:plan`: Opus or Fable?" question has the answer "whatever you
configured for think"** — plus OQ-1's A/B, which is the only thing that can move the default.

**Each listed command names its own tier inline in its own PHASE 0** — **no central table.** A
table would be a second source of truth about which command belongs to which tier, and the first
edit that touched one and not the other would make them disagree.

**Alternatives considered:**

- *A `model:` line in the command's own frontmatter.* ⚠ **CORRECTED 2026-09-03: POSSIBLE and
  DOCUMENTED — NOT CHOSEN for this plan (maintainer decision, same day).** The drafting-time text
  read *"IMPOSSIBLE, not rejected — verified against `plugins-reference.md`"*; **that verification
  was wrong**, the sentence it rested on is not on that page today, and `slash-commands` documents
  commands as sharing the skill frontmatter including `model` and `effort`. **It would satisfy
  directive (c) more literally than the advisory line does** — the command would actually RUN on
  the tier's model for that turn. **It is declined here and deferred to its own decision: OQ-5**,
  which records the three options offered, the pick, and the four costs that make it a separate
  plan rather than a line in this one.
- *A helper verb that composes the line (a `stakes-hint` twin).* **REJECTED for v1**: it is a
  config read and a string, and the tier is a per-command constant. Python here buys a shared
  format and costs a verb, its tests, and a second place the tier lives. **Recorded as the
  widening path** if the line's wording starts drifting between commands.
- *Print it in every command.* **REJECTED**: a line printed 20 times a feature is a line nobody
  reads, and most commands do no tier-sensitive judgment work. OQ-2 scopes the set.

**⚠ Honest bound, THREE parts.** **(i)** The session-model half rests on an **OBSERVED, undocumented**
harness statement (fact 21) and **prints `unknown` without it** — a harness change silently
degrades half the line, and no test can pin it. ⚠ **Phase 4's guide pass HARDENED this bound: there
is no documented way for a command to learn the session model at all** (`ANTHROPIC_MODEL` is a
startup setting, and the skill substitution variables carry no model), **so `unknown` is the
documented-correct fallback rather than a gap to close.** **(ii) Nothing measures whether the line
changes any behavior at all.** It is information placed where a decision is being made; that is the
whole claim. **(iii) ADDED 2026-09-03 — the line now sits beside a documented STRONGER mechanism
this plan declined** (the command-scoped `model:` override, fact 19 corrected). **A reader must not
take "advisory" to mean "the only option available"**: it means the option chosen, with the
alternative recorded at OQ-5 and deferred rather than refuted.

### D8 — Fable prompt tuning is OUT of scope *(RATIFIED 2026-09-03 — as recommended)*

**RECOMMENDED RULE.** The de-prescription warning in `## Model facts` — prompts written for prior
models are often too prescriptive for Fable and reduce its output quality — **applies to the
entire `src/commands/` corpus**, which is deliberately prescriptive from end to end. **This plan
rewrites no prompt for any model.**

**The follow-on is NAMED with an OBSERVED trigger**, so this is a decision rather than a deferral:
an OQ-1 A/B in which `think = fable` **underperforms** `think = opus` on a known-answer anchor.
That is the shape plan 48 (shelve until an OBSERVED skip) and plan 87 (WARN until the first
confirmed leak) both use.

**Alternatives considered:**

- *De-prescribe the think-tier command specs now.* **REJECTED**: it would rewrite the most
  load-bearing instruction text in the repo on the strength of a cached vendor note, with no
  measurement, in the same build that first makes Fable selectable. **If the rewrite were wrong,
  nothing here would tell us.**
- *Ship a per-model prompt variant.* **REJECTED**: two versions of the same command spec is the
  drift surface this repo spends the most effort avoiding, and there is no evidence yet that one
  version is insufficient.

**⚠ Honest bound.** **If the corpus really is too prescriptive for Fable, then D3 offering Fable
is offering a configuration this framework has not tuned for** — and OQ-1's recommended `opus`
default is the only thing standing between that and a consumer default. **Say so; do not imply
Fable is a drop-in.**

### D9 — Scope tripwire: zero gates, and Python confined to a named list *(RATIFIED 2026-09-03 — as recommended)*

**RECOMMENDED RULE.** **Zero gates, zero new `verify-*` gate numbers, zero hard-fail validators**
— plan 75's tripwire in both halves. **No plan-63 13/7 delta** *(⚠ the LIVE counts are **16/4** as of 2026-09-03 — plan 93 removed the flag from `/devforge:grill`, `/devforge:spec-check` and `/devforge:fix`; this plan still contributes NO delta, and the numeral here is the pre-93 figure the decision was written against)*: `/devforge:configure` stays
human-typed (`disable-model-invocation: true`), no command is added, no `description` is widened.

**Python is confined to this list, and a phase that needs more has crossed its boundary:**

1. The `apply-agent-models` verb + its module + its tests (D1).
2. Alias normalization inside `_cmd_set_claude_tier` (D3).
3. Three effort fields + three setters + three render keys + their tests (D4).
4. The emitter's `model_tier:` line and `model_pin` support + emitter tests (D1, D6).
5. Two maintainer tests: the default-map equality pin (D2) and the no-version-string tripwire (D3).

**Everything else is instruction-only.** **No back-porting into shipped installs**: they receive
this through `update.sh` (D1's designed consequence) and through a re-run of
`/devforge:configure` for the new effort questions.

**Alternatives considered:**

- *A `verify-agent-models` gate that fails when an emitted agent's `model:` disagrees with
  configuration.* **REJECTED**: it would be the first mechanical blocker for a lane with zero
  observed failures, and D1's verb is idempotent — the repair for a disagreement is to run apply,
  which the gate would only announce. **Recorded as the shape, not built**, with the trigger
  being an OBSERVED install whose agents drifted from its configuration.
- *A WARN-only drift check at update time (plan 44's shape).* **REJECTED for v1 for the same
  reason** — D1 runs apply at update time, so there is nothing left to warn about. It becomes the
  right answer only if D1's `update.sh` seat is declined.

**⚠ Honest bound.** Nothing verifies that the applied model is the configured one **after** apply
runs, other than apply's own idempotence and its tests. **A consumer who hand-edits an agent's
`model:` line keeps that edit until the next apply silently overwrites it** — recorded, and D1's
`update.sh` summary print is the only thing that makes it visible.

---

## Open questions (OQ-1–OQ-5) — ALL RESOLVED 2026-09-03

⚠ **OQ-5 was ADDED after Phase 0 closed**, by Phase 4's `claude-code-guide` pass, and resolved the
same day. **Phase 0's own Verify criterion says "four lines" and is superseded by this**; the count
is five.

### OQ-1 — The think-tier defaults: model and effort *(RESOLVED 2026-09-03 — `opus` and `default`, until Phase 6's A/B)*

**The model.** With `fable` available, is the recommended `think` default `opus` or `fable`?

**RECOMMENDATION: `opus`, until Phase 6's A/B measures it.** Three reasons: **nothing shipped here
is evidence Fable helps this pipeline**; the de-prescription warning cuts directly against a
heavily prescriptive command corpus (D8); and Fable is the most expensive of the four per MTok
(`## Model facts`), so defaulting to it spends a consumer's money on an unmeasured hypothesis.
**The counter-argument is real and is recorded**: the vendor's documented bug-finding gains are
exactly what a `devils-advocate` or an `architect` would benefit from, and a default of `opus`
means most installs never find out. **Phase 6's anchor 6 is the only thing that may flip this.**

**The effort.** Is the recommended `think` effort `default` or `xhigh`?

**RECOMMENDATION: `default`.** It inherits the session effort (docs, verified above), which means
the framework does not silently override a user who already set their session effort deliberately
— and it tracks the model, whose supported levels differ. **`xhigh` is the recorded alternative**
and is the one to take if Phase 6 shows think-tier output quality is the binding constraint.

### OQ-2 — Which commands get the D7 advisory, and with which tier *(RESOLVED 2026-09-03 — the eight-command set as recommended, no effort mention)*

**RECOMMENDED SET — these eight commands, with these tiers.** The tier assignments follow each
command's dominant judgment work, and **a ratifier may reasonably disagree per command**; the
recommendation is the whole set, not a menu:

| Command | Tier |
|---|---|
| `/devforge:specify` · `/devforge:plan` · `/devforge:grill` · `/devforge:breakdown` | `think` |
| `/devforge:implement` · `/devforge:fix` | `do` |
| `/devforge:review` · `/devforge:verify` | `verify` |
| every other command | none — no line |

**Does the line mention EFFORT? RECOMMENDATION: no.** The session's effort is user-set and
**invisible to the model** — printing a configured AGENT effort beside a session that runs at an
unknown one would invite the reader to conflate two different settings. The line names the model
because the harness states it (fact 21); it stays silent about effort because nothing does.

**⚠ Note for the ratifier:** the set is eight commands out of twenty. A wider set costs a printed
line per run; a narrower one costs the recommendation's reach. **The failure mode of "too many" is
a line nobody reads** — which is the same anti-pattern plan 90's D8 named for nagging warnings.

### OQ-3 — The unused `scan` tier *(RESOLVED 2026-09-03 — leave `scan` as is)*

`scan` has **zero members** (fact 3) and has had none for the life of the roster.

**RECOMMENDATION: leave it as is** — it is a `## Non-goals` entry, not a task. It costs one map
entry and one enum value; deleting it touches `install_defaults.py`, the AUTHORING enum, the apply
verb's map and any test that enumerates tiers, to remove a dead value that harms nothing.

**The alternative — delete it from the map and the enum — is recorded**, and the ratifier who
prefers it should note that D1's apply verb makes the map load-bearing at runtime for the first
time, so a dead tier is now dead code rather than dead documentation. **That is the strongest
argument for deleting, and it is not strong enough to widen this plan.**

### OQ-4 — Ordering against the deferred consumer-e2e batch *(RESOLVED 2026-09-03 — baseline first, A/B second, delta recorded as a NUMBER)*

Several plans carry deferred, user-driven consumer e2e runs that the maintainer has batched
(plan 85's Phase 5 decision, 2026-08-26). **This plan's Phase 6 anchor 6 is an A/B over the
model**, so it interacts with every other deferred run in the batch.

**RECOMMENDATION: baseline first, A/B second, and record the delta as a NUMBER.**

- **Plan 85's D7 wall-clock number must be measured on the Opus/Sonnet baseline FIRST.** If the
  batch runs with `think = fable` already configured, the first wall-clock figure this plan family
  has ever had is confounded by a model change at the moment of its birth — and **Fable turns run
  longer** (`## Model facts`), so the confound is in the direction that matters most.
- **Then this plan's A/B**, one feature, `think = opus` vs `think = fable`, wall-clock via
  `profile_helper` (plan 70).
- ⚠ **A confound already exists and must be named where it lands, not here.** Plan 81's Phase 7
  pins the model `claude-fable-5`, while the maintainer's session default became Fable 5.1 on
  2026-09-03. **That is plan 81's confound to record when its Phase 7 runs**; this plan does not
  edit plan 81 and does not resolve it.

### OQ-5 — Command-scoped model override via frontmatter *(RESOLVED 2026-09-03 — deferred to a follow-on decision, by the maintainer)*

⚠ **This question did not exist when Phase 0 closed.** It was opened by Phase 4's
`claude-code-guide` pass, which found that **fact 19 — and therefore D7's entire premise — was
wrong**: commands share the skill frontmatter, `model` and `effort` included. **It is numbered as
an OQ and resolved the same day rather than being folded into D7 silently**, because the decision
it records is a real fork, not a correction.

**What the override would do, stated at full strength before the costs.** A `model:` line in a
command's own frontmatter would make `/devforge:plan` and its peers **actually RUN on the
configured tier's model for that turn** — not print a recommendation about it. The documented
semantics are unusually well-suited: the override is **turn-scoped** (*"applies for the rest of the
current turn … the session model resumes on your next prompt"*), and a value the organization's
`availableModels` allowlist excludes is **silently not used, the session keeping its current
model** — a graceful degradation this plan would otherwise have had to build. **This is what
directive (c) literally asked for, and more than the advisory line delivers.**

**RESOLVED — the maintainer picked, from three options offered on 2026-09-03: KEEP THE ADVISORY,
and treat the override as a SEPARATE DECISION.** The two options not taken are recorded: replace
Phase 4 with the override now, or ship the advisory now and add the override as a Phase 7 of this
plan.

**The four costs that make it a separate plan rather than a line in this one:**

- **(a) It needs a twin of `apply-agent-models`, over commands.** The value must come from the
  consumer's own Q11 answer, so something must write it into
  `.claude/commands/devforge/*.md` — a new Python verb keyed on a marker line. ⚠ **Substitution is
  not available: commands are NOT in `substitute-templates`' walk**, and a placeholder would
  reproduce D1's rejected alternative (a) exactly.
- **(b) It overrides the user's own `/model` on every command turn.** ⚠ **A sovereignty question
  D7 never had to answer** — the advisory line informs, an override decides for them.
- **(c) It interacts with plan 93's model-invocable commands.** A model-invoked `/devforge:review`
  would **switch the session's model mid-conversation**, which is a different act from a user
  typing a command and expecting it to run on its tier.
- **(d) `effort` in command frontmatter overrides the session effort the same way** — so the same
  sovereignty question arrives twice, and D4's no-validation bound would apply to a surface the
  user did not configure per command.

**Recommendation recorded for the follow-on: a separate small plan with its own Phase 0**, which
can weigh (b) and (c) properly instead of inheriting them. **The advisory line stays until then**,
and D7's third honest bound is what stops a reader mistaking it for the only option.

⚠ **RESOLVED AFFIRMATIVELY 2026-09-04 — the follow-on this OQ asked for is
`94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md`, and it TAKES the override.** This plan's own pick
(*keep the advisory, treat the override as a separate decision*) is **not overwritten** — it was
answered by the separate decision it asked for, on a maintainer directive dated the next day: the
override *"is what was intended from the start."* **What shipped:** the eight commands of OQ-2 now
carry `model:` / `effort:` frontmatter written from `.devforge/project-config.json` by
`apply-models` (plan 94 D1, D5), keyed on a helper-owned `COMMAND_TIERS` map pinned to those same
eight advisory lines by a maintainer test. **The four costs were answered, not dissolved:** (a) is
the verb extension itself; (b) and (c) are plan 94's D1 bounds (i)–(iii), where a **model-invoked**
command now switches the session's model for its own turn; (d) is plan 94 D5, inheriting this
plan's no-validation bound unchanged. ⚠ **D7's advisory line SURVIVES and gains a job** — its second
half is the override's only readback, and it prints `not configured` for a tier nobody answered.

---

## Phases

### Phase 0 — Ratification *(doc-only)* — **CLOSED 2026-09-03**

**Objective:** ratify or amend D1–D9 and answer OQ-1–OQ-4, recording each answer in this file with
its reasoning. **Nothing else may start.**

**✅ CLOSED 2026-09-03 — see `## Phase 0 close record` below. Phases 1, 2, 3, 4 and 5 are cleared to
build; Phase 6 stays a deferred user-driven HARD GATE.** The pick-list below is retained as the
record of what needed an explicit answer, **and every item on it was answered by the blanket
directive rather than by a separate deliberation** — which the close record states plainly.

**Four items need an explicit pick rather than a nod**, because each has a named fork whose arms
lead to different builds:

- **D1's arm** — the helper verb vs the placeholder route. Picking the placeholder collapses D4's
  `default` sentinel (a placeholder cannot remove a line) and should be taken deliberately, with
  D4 amended in the same breath.
- **D2 half 2 with D4** — **these must be ratified together.** Recommending Haiku for verify while
  adding an effort question ships a recommended combination the vendor documents as failing.
- **D6's contract extension** — `agents-AUTHORING.md`'s table says the contract is *"fixed"*.
  Extending it is a real decision about a real constraint, not a formality.
- **OQ-1's think default** — `opus` vs `fable`. This is what directive (c) actually asked about,
  and **it is the one item Phase 6 can overturn with data.**

**Verify:**

- `grep -n "^### D[1-9] " 92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md` returns nine lines and **every
  one carries a ratification marker with a date.**
- `grep -n "^### OQ-[1-4] " 92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md` returns four lines, each with
  a recorded answer.
  ⚠ **AMENDED 2026-09-03 — the count is now FIVE.** Phase 4's `claude-code-guide` pass refuted
  fact 19 and opened **OQ-5**, resolved the same day. **Use `^### OQ-[1-5] `** — a criterion that
  still expects four would read a legitimately answered question as an intruder.
- **A grep for the drafting-time unratified marker — the bracketed, italicised word this file used
  on every D- and OQ-header before this close — returns ZERO hits.** ⚠ **This bullet deliberately
  does NOT write that token out, and the reason is mechanical**: a Verify criterion that quotes the
  string it forbids can never pass its own grep, and would read to every future session as a
  permanently failed close. *(Plan 90's equivalent bullet does embed the literal and therefore
  self-hits — cosmetic in that file, not a defect in its closure, and deliberately not copied
  here.)* **The marker's exact shape is recoverable from any pre-close revision in git history.**
- **Every decision still carries its alternatives AND its honest bound.** A ratified decision whose
  bound was deleted cannot be re-opened honestly.
- The status line at the top names the ratification date and which phases are cleared.
- **D2 half 2 and D4 are answered in the same breath**, and if they diverge the ratifier states
  which mitigation replaces the other.
- **The evidence split survives ratification.** One observed defect (fact 8) plus four directives —
  a Phase 0 that upgrades a directive into a finding has changed the evidence base and must say
  where the finding came from.

---

## Phase 0 close record

**Ratified 2026-09-03 by the maintainer, in-session, with a SINGLE BLANKET DIRECTIVE** — verbatim,
in Ukrainian: *"ратифікую все як рекомендовано, починай Phase 1"* (*"I ratify everything as
recommended, start Phase 1"*). **Every item — D1–D9 and OQ-1–OQ-4 — is ratified AS RECOMMENDED.**
No item was amended, deferred or declined except where a decision's own recommendation was to
decline (D1's alternatives (a), (c) and (d); D2's keep-Haiku arm; D3's Models-API and
enumerate-IDs arms; D4's single-question and free-text arms; D5's three rejected probe shapes;
D6's fifth-tier and exclusion-set arms; D7's frontmatter and helper-verb arms; D8's two rewrite
arms; D9's gate and drift-check arms; OQ-3's delete arm) — **those declines ARE the
recommendation, not a departure from it.**

⚠ **What this closure is, stated plainly rather than dressed up: ONE directive, not thirteen
deliberations.** The maintainer supplied no per-item reasoning, and **this record does not
manufacture any.** The arguments standing behind each answer are the ones already written in the
decision bodies above — they were ratified, not re-derived, and **nothing in this closure adds
evidence to any of them.** *(Precedent: plan 91's Phase 0, closed 2026-08-28 by a single blanket
maintainer directive, which likewise recorded the blanket form rather than implying per-item
argument.)*

**The four explicit picks, as answered by that directive:**

| Pick | Answer |
|---|---|
| **D1's arm** | **(b) — the `configure_helper apply-agent-models` helper verb.** The placeholder route (a), the shell route (c) and delete-Q11 (d) stay rejected as recorded; **the `model_tier:` emitted line ratifies with it**, and so does its bound — the keying rests on repo precedent, not on documentation |
| **D2 half 2 with D4** | **BOTH, in the same breath — `verify = sonnet` AND the three effort fields.** ⚠ **The pairing is the point and it is recorded at BOTH decisions**: ratifying D4 while recommending Haiku for verify would have shipped the one recommended combination the vendor documents as failing (`effort` errors on Haiku 4.5). **Neither ships without the other** |
| **D6's contract extension** | **ACCEPTED.** `agents-AUTHORING.md`'s *"fixed — author to it, never change it"* clause is **consciously EXTENDED**, not overridden: one new OPTIONAL `model_pin` row, applied to exactly one agent. **Phase 2 records the extension with a dated note at the table itself** — an extension a future author cannot see is indistinguishable from drift |
| **OQ-1's think default** | **`opus` for the model, `default` for the effort.** ⚠ **This is the answer directive (c) asked for, and it is the ONE ratified item Phase 6 may overturn with data** — anchor 6's A/B is the only evidence that may flip it, and **ratifying `opus` is not evidence that `opus` is better; it is the absence of evidence that `fable` is** |

**What ratification did NOT change — recorded so a future session does not read closure as scope
growth:**

- **Every alternative and every honest bound survives verbatim.** D1's two bounds (the static
  default's merge behavior; `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` defeating the whole mechanism
  undetectably), D3's floating-alias bound, D4's no-compatibility-validation bound, D5's
  entitlement bound, D6's two-way ceiling, D7's undocumented-harness bound, D8's untuned-corpus
  bound and D9's hand-edit bound are **accepted costs, not answered ones.** **Phase 0's own Verify
  requires this**, and none was deleted.
- **The evidence split is unchanged.** One observed, grep-verified defect (fact 8) plus four
  maintainer directives dated 2026-09-03. ⚠ **Ratifying a directive does not upgrade it into a
  finding**, and no summary of this plan may imply a consumer failure. The directive half remains a
  **predicted-gap** feature in plan 87's class.
- **Plan 75's tripwire still holds, both halves** (D9): zero gates, zero new `verify-*` numbers,
  zero hard-fail validators, and **no plan-63 13/7 delta** *(⚠ LIVE: **16/4** as of 2026-09-03 via plan 93; this plan's delta is still zero)*.
- **Python stays confined to D9's five-item list.** A phase that needs more has crossed its own
  boundary.
- **Phase 1 still owes its Step-0 `claude-code-guide` pass BEFORE any code**, and its answer 1 is
  still a STOP condition: if unknown frontmatter keys turn out NOT to be ignored, D1's keying
  mechanism has no fallback and **returns to Phase 0.** **Ratification did not settle that
  question — it is external to this repo and no directive can answer it.**
  ✅ **DISCHARGED 2026-09-03 — the pass RAN before any code and its answers are recorded at
  `#### Phase 1 build record — Step 0`.** ⚠ **The STOP arm did not trigger, and it did not close
  either**: unknown-key handling is **not documented either way**, so D1's keying rests on the
  enumerated skip list excluding it plus the `applies_to` precedent. **The clause above stays
  true as written** — no directive answered it, and the docs did not either; what changed is that
  the question was asked and its footing is now written down.
- **Phase 6 is NOT cleared.** It is a deferred user-driven HARD GATE with six known-answer anchors,
  **anchor 1's two halves scored as a PAIR**. **Everything Phases 1–5 produce will be
  build-verified and NOT consumer-validated.**

---

### Phase 1 — The Python surface *(Python)* — **BUILT 2026-09-03** (python-reviewer clean; commit pending)

**Route: claude-code-guide FIRST, then python-engineer → python-reviewer, test-first, tests written
AND RUN in the same turn.** ⚠ **This phase DOES owe a claude-code-guide pass, and it owes it
BEFORE any code is written.** Deliverable 4 changes `emit_claude()`, which **fixes the frontmatter
shape shipped into every consumer's `.claude/agents/*.md`** — that is a Claude-Code-integration
surface, and `## When resuming work` step 6 makes the pass unconditional for any frontmatter edit.
A phase that reasons *"this is Python, so no pass is owed"* has read the file extension instead of
the artifact.

**Step 0 — the claude-code-guide pass, a PREREQUISITE that Deliverable 4 depends on.** Invoke the
agent and **record all three answers in this phase's build record BEFORE the emitter code lands**:

1. **Are unknown frontmatter keys ignored?** The docs did not say so on 2026-09-03 and `applies_to`
   is the only evidence (`### Claude Code authoring surface`). **D1's `model_tier:` line rests on
   this answer** — a "no" invalidates the keying mechanism, not merely a sentence.
2. **Is the frontmatter key ORDER significant, and is any position required?** Deliverable 4 pins a
   position in a test, and every consumer's merge baseline diffs against it (fact 11).
3. **What does Claude Code do with an `effort:` line on a `haiku`-aliased agent?** The API errors
   (`## Model facts`); Claude Code's behavior is a separate question and is not assumed here.

**⚠ Phase 2 CITES these recorded answers rather than asking again.** Its own pass covers the
`q11-tiers.md` / AskUserQuestion surface, which this phase does not touch.

**Step 0b — run BOTH tripwire greps and RECORD the results** — `claude-[a-z]+-[0-9]` and
`\b(opus|sonnet|haiku|fable)\s+[0-9]` (case-insensitive), each over `src/`. **Both returned zero at
drafting time** (fact 18); a non-zero result on either at build time means something landed in
between, and that test's premise must be re-derived before it is written.

**Deliverable 1 — the three effort fields (D4).** `claude_effort_think` / `claude_effort_do` /
`claude_effort_verify` join `FIELD_SCHEMA` (as scalars) and **`ENUM_FIELDS`** with
`{default, low, medium, high, xhigh, max}`; three setters in `_cmds_set.py`; three verb
registrations in `_configure/_cli.py`; three keys in `_PROJECT_CONFIG_KEY_ORDER`; a display group
in `_summary.py`; and whatever `_cmds_verify.py`'s required-field loop needs. ⚠ **Read plan 90's
Phase-1 build record before choosing the default style**: `e2e_command` took a `FIELD_DEFAULTS`
baseline of `""` precisely so `_cmds_verify.py` needed no exemption. **A `FIELD_DEFAULTS` entry of
`"default"` is the structurally simpler answer here** — it is a real enum member, so no exemption
and no discriminator is invented. **Do not invent a third style.**

**Deliverable 2 — alias normalization (D3).** `_cmd_set_claude_tier` lowercases a value that
case-insensitively matches one of the four aliases and passes anything else through unchanged as a
pin. **The docstring must say which behavior is which**, because fact 6's "intentionally NOT
enum-restricted" comment is what a future reader will find first.

**Deliverable 3 — `apply-agent-models` (D1).** A new module under `src/devforge/lib/_configure/`
(filename chosen here) plus its verb registration. Contract:

- Reads `.devforge/project-config.json`; a missing or unparseable config is a clean non-zero exit
  with a message, never a partial rewrite.
- Walks `.claude/agents/*.md`. **A file without a `model_tier:` frontmatter line is left
  untouched** (D1, D6).
- Sets `model:` from the tier's `CLAUDE_TIER_*` value, or the tier default (D2) when it is `null`.
- Sets `effort:` from `CLAUDE_EFFORT_*`, **removing the line entirely when the value is `default`**.
- **Idempotent**, and a test proves a second run is a byte-level no-op.
- **stdout JSON listing per-file `{agent, model, effort}` applied** — this is what `update.sh` and
  `/devforge:configure` print, so the shape is a contract, not a convenience.

**Deliverable 4 — the emitter (D1, D6).** `emit_claude` gains a `model_tier: <tier>` line and
`model_pin` support: when a source declares `model_pin`, the emitter writes `model: <pin>` and
**omits `model_tier:`**. Emitter tests updated. ⚠ **The frontmatter key ORDER is part of the
emitted bytes** — pick a position **informed by Step 0's answer 2** and pin it in a test, because
every consumer's baseline snapshot diffs against it (fact 11). ⚠ **This deliverable is the one
that DEPENDS on Step 0** and may not be written before those answers are recorded.

**Deliverable 5 — the two maintainer tests (D2, D3).** The default-map equality pin, and the
no-version-string tripwire over `src/` — **asserting BOTH patterns absent**, the API-ID shape and
the display-name-with-version shape (D3).

**⚠ Three build constraints, each a fact rather than a fork:**

1. **The counts are READ LIVE.** `FIELD_SCHEMA` is 32 and `_PROJECT_CONFIG_KEY_ORDER` is 40
   **as of 2026-09-03** (fact 14). **FOUR assertions pin them, not two** —
   `test_field_schema_has_32_fields`, `test_default_state_has_32_keys`, `test_all_40_keys_present`
   and `test_renders_40_keys_with_defaults`. **Count the live tuples and write what you counted**;
   adding three to a remembered number produces a differently wrong number (plans 89/90's standing
   rule).
2. **Every existing configure test must pass unchanged** except the count pins, which move by
   counting. A failure anywhere else means a shared code path moved.
3. **Nothing here writes any `.claude/` file's CONTENT semantics beyond frontmatter.** The apply
   verb rewrites frontmatter lines and touches no body byte — a test compares the post-apply body
   byte-for-byte.

**Tests — written and RUN in the same turn as the code**, per repo discipline (every function gets
its own test that runs), and **round-tripped through the real producers, never hand-authored
fixtures**: `configure_helper reset` + the new setters → `configure.yaml` → `render-config` →
`project-config.json` → `apply-agent-models` over a temp `.claude/agents/` tree.

**Verify:**

- **claude-code-guide invoked at Step 0 and ALL THREE answers RECORDED in this phase's build
  record, before the emitter code landed.** ⚠ **An answer recorded after the code is not a
  prerequisite, it is a rationalization** — and an unrecorded pass is indistinguishable from one
  that never ran. **If answer 1 came back "unknown keys are NOT ignored", the phase STOPS and D1
  returns to Phase 0**, because the `model_tier:` keying mechanism has no fallback in this plan.
  ✅ **SATISFIED 2026-09-03** — the pass ran before any code and all four answers are recorded at
  `#### Phase 1 build record — Step 0`. ⚠ **Answer 1 came back "not documented either way", which
  is neither the pass nor the STOP this bullet anticipated** — the phase proceeds on the recorded
  two-part footing, and **the STOP arm survives re-pointed at an OBSERVED failure** (agents that
  stop being listed or dispatched once `model_tier:` ships).
- python-reviewer clean; the `tests/lib/` configure suites and `tests/scripts/` emitter suites green.
- **A test proves `apply-agent-models` is idempotent** — run twice, second run changes zero bytes.
- **A test proves an agent file with no `model_tier:` line is untouched** (D6's mechanism).
- **A test proves the `default` effort REMOVES the line**, and that a set effort writes it.
- **A test proves a `null` tier value applies the D2 default**, so an unconfigured install lands
  exactly where it lands today.
- **A test proves the post-apply BODY is byte-identical** to the pre-apply body.
- **The default-map equality test fails when either literal is edited alone** — assert this by
  temporarily editing one in the test, not by reasoning about it.
- **The version-string tripwire test fails on BOTH shapes** — prove it twice: once by adding a
  `claude-opus-5`-style ID under `src/`, once by adding an `Opus 5`-style display name. ⚠ **A test
  that only catches the first shape passes this bullet by half and leaves the prose shape open**,
  which is the likelier of the two to be written by a well-meaning author.
- **`configure_helper verify` exits 0 on an install whose three effort fields were never set**
  (constraint 1's default style). An install that upgrades and then fails its own config check has
  shipped a regression to every consumer at once.
- **All FOUR configure count assertions match a fresh count of the live tuples**, and the counted
  numbers are stated in the commit message.
- `git status` shows zero files modified under `src/commands/` — this phase is Python-only, except
  the emitter, which is `scripts/`.

#### Phase 1 build record — Step 0 (2026-09-03)

**The `claude-code-guide` agent was dispatched 2026-09-03 and answered from the live docs, BEFORE
any Phase-1 code was written.** This block is the record Phase 1's first Verify bullet requires;
**Phase 2 CITES it and does not re-ask.**

**Answer 1 — unknown frontmatter keys: NOT DOCUMENTED either way. The STOP arm did NOT trigger.**
`https://code.claude.com/docs/en/sub-agents.md` enumerates the conditions under which Claude Code
**skips** a subagent file — no `name`; the opening `---` not on the first line; a `name` starting
with `-` or containing `:`; a `name` present with no `description`; YAML that does not parse — and
**an unrecognized key is not among them.** The page says nothing about ignoring, rejecting or
warning on one. ⚠ **So the answer is neither the "yes" the plan hoped for nor the "no" that would
have stopped the phase**, and D1's keying rests on two things, both stated plainly:

- **(a) The enumerated skip list excludes it** — a closed list of skip conditions that does not
  include unknown keys is evidence, though not a guarantee.
- **(b) The `applies_to` precedent** — an unrecognized key emitted into every consumer install
  since plan 15 and dispatched on without complaint (fact 16).

⚠ **The STOP arm's wording is KEPT, re-pointed at an OBSERVED failure**: an install whose agents
stop being listed or dispatched after `model_tier:` lands. **That trigger is an observation, not a
suspicion** — and the docs cannot close it, because they do not speak to it.

**Answer 2 — key ORDER: NOT DOCUMENTED as significant.** Same page; no positional rule beyond the
opening `---` being on line 1. **Decision taken for Deliverable 4, and both positions are pinned by
tests:**

- **`model_tier:` is emitted IMMEDIATELY AFTER `model:`** — emitted order `name`, `description`,
  optional `tools`, `model`, `model_tier`, optional `applies_to`.
- **`apply-agent-models` inserts `effort:` IMMEDIATELY AFTER `model:`** when it writes one — so a
  configured file reads `model`, `effort`, `model_tier`.

**Answer 3 — `effort:` on a model without effort support: DOCUMENTED as a SILENT FALLBACK.**
`https://code.claude.com/docs/en/model-config.md`: *"If you set a level the active model does not
support, Claude Code falls back to the highest supported level at or below the one you set."* and
*"Models not listed here do not support effort."* **Haiku is not listed**, so a `haiku` agent
carrying an `effort:` line runs **without effort and without a dispatch error.**

⚠ **Two sentences elsewhere in this plan were WEAKENED by this answer, and both were corrected in
place rather than deleted** (2026-09-03): **D2 half 2's fourth reason** — *"Haiku 4.5 errors on
`effort`"* describes the **API**, not Claude Code, so **three reasons hold half 2 up, not four**;
and **D4's honest bound**, whose *"fails at DISPATCH"* became *"degrades silently at dispatch
(documented fallback)"*. ⚠ **The CLASS is unchanged and arguably worse than assumed**: the
framework still validates nothing, and the documented failure shape is now known to be **silent**,
which looks exactly like success. **D4's pairing with D2 half 2 stands on the weaker ground** —
a quietly ignored effort answer rather than an error — and that shift is recorded at D4's own
dependency paragraph.

**Answer 4 — model resolution order CONFIRMED, with a version caveat the plan did not have.**
Current order: per-invocation `model` parameter → the subagent's `model` frontmatter (`inherit` =
the main conversation's model) → `CLAUDE_CODE_SUBAGENT_MODEL` when set → the main conversation's
model. ⚠ **Before v2.1.251 the environment variable came FIRST and overrode the frontmatter.**
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` confirmed: when on, Claude Code **ignores every subagent
definition's `model` field** (the built-in Explore/Plan agents included) and Claude cannot pass a
model at spawn; with both variables set, subagents run on `CLAUDE_CODE_SUBAGENT_MODEL`; with only
FORCE set, on the main conversation's model. **Trap 5 carries the pre-v2.1.251 note**, because a
consumer on an older Claude Code with that variable set **never sees the emitted `model:` line at
all** — and this plan builds no version floor.

**Step 0b — both tripwire greps, run over `src/` on 2026-09-03 before any Phase-1 code:**
`claude-[a-z]+-[0-9]` → **0 hits**; `\b(opus|sonnet|haiku|fable)\s+[0-9]` (case-insensitive) →
**0 hits**. **So Deliverable 5's test pins an already-clean baseline** — it does not repair a
violation, and a future failure means that build introduced one.

**Phase 1 execution split — an orchestrator decision for a dependency this plan did not spell
out.** Deliverable 3's tests round-trip **real emitter output**, which must already carry
`model_tier:`, so the emitter cannot come after the apply verb. **Three runs, each completing
python-engineer → python-reviewer before the next starts:**

| Run | Contents | Why here |
|---|---|---|
| **A** | Deliverables 1 + 2 | Independent of the emitter; in flight |
| **C1** | Deliverable 4 (emitter) + the **version-tripwire half** of Deliverable 5 | ⚠ **Must land BEFORE Deliverable 3** — the apply verb's round-trip tests need emitted files that already carry `model_tier:` |
| **B** | Deliverable 3 + the **default-map-equality half** of Deliverable 5 | That literal is born in the apply module, so its pin cannot precede it |

⚠ **Deliverable 5 is therefore SPLIT ACROSS TWO RUNS**, which the phase text does not say. Recorded
here so a builder reading Deliverable 5 as one unit does not block run C1 waiting for a literal
that does not exist yet.

#### Phase 1 build record — Deliverables 1–5 (2026-09-03)

**BUILT and python-reviewer clean; the commit is pending.** The split above ran as planned, each run
completing python-engineer → python-reviewer before the next started: **run A** (Deliverables 1+2)
returned **ZERO findings**; **run C1** (Deliverable 4 + the tripwire half of 5) returned **4
findings, all applied**; **run B** (Deliverable 3 + the equality half of 5) returned **12 findings,
all applied and CONFIRMED on re-check, plus 1 new Low closed.** ⚠ **Run B's four MEDIUMs are the
load-bearing part of this record** — permissions, duplicate keys, CRLF and layering — and each is
named below rather than folded into a count.

**The counts, COUNTED from the live tuples.** `FIELD_SCHEMA` **35** (was 32) · `ENUM_FIELDS` **8**
(was 5) · `FIELD_DEFAULTS` **6** (was 3) · `_PROJECT_CONFIG_KEY_ORDER` **43** (was 40). The four
pins were RENAMED to carry the live numbers: `test_field_schema_has_35_fields`,
`test_default_state_has_35_keys`, `test_all_43_keys_present`, `test_renders_43_keys_with_defaults`.
⚠ **Three PRE-EXISTING stale counts were corrected while touching those exact lines** —
`_render.py`'s *"31 FIELD_SCHEMA entries"* docstring, `_cmds_verify.py`'s *"32/31"*, and
`_cmds_set.py`'s *"Enum scalar setters (6)"* header, **which was already wrong at 5.** They are
recorded as pre-existing, not claimed as this plan's defects. **`src/devforge/project-config.json`
does not enumerate every key and was deliberately left alone.**

**What landed. New:** `_configure/_agent_models.py` (pure logic + the consumer-side twin
`CLAUDE_AGENT_DEFAULTS_BY_TIER`), `_configure/_cmds_agent_models.py` (`cmd_apply_agent_models`),
`scripts/lib/model_version_tripwire.py`; tests `test_effort_fields.py`,
`test_apply_agent_models.py`, `test_agent_models.py`, `test_model_version_tripwire.py`.
**Modified:** `_schema.py` (three effort fields appended last; ⚠ **`CLAUDE_MODEL_ALIASES` lives
HERE, not in `_cmds_set.py`** — the package DAG runs base modules → `_cmds_*` and never the
reverse), `_cmds_set.py`, `_cli.py` (`set-claude-effort-*`, `Step 5b: apply-agent-models`,
`--install-root` help), `_render.py`, `_summary.py`, `_cmds_verify.py` (docstring only — the
`"default"` baseline needs no exemption, and a test proves it), `scripts/generate-agents.py`,
`scripts/lib/install_defaults.py` (comments), `tests/lib/test_configure_helper.py`,
`tests/lib/_configure/test_substitute_file.py`, `tests/scripts/test_generate_agents.py`.

⚠ **A latent defect was found and fixed in passing, and it is NOT this plan's:** `_render.py`'s
`_write_file_atomic` **left every rewritten file at mkstemp's `0o600`**; it now PRESERVES the
target's mode. **The same defect is shared with `substitute-templates`** — recorded here because a
future session meeting a permissions surprise there should know it was seen and where.

**Deliverable 4 as shipped.** Emitted order `name`, `description`, [`tools`], `model`,
`model_tier`, [`applies_to`] — Step 0's answer 2 executed. `model_tier` stays REQUIRED in every
source. ⚠ **The `model_pin` regex was TIGHTENED to `^[a-z][a-z-]*$` (no digit)**: the reviewer
demonstrated `sonnet-4-5` passing the drafted `[a-z0-9-]` shape **and slipping both tripwire
patterns** — a version string entering `src/` through the one field designed to bypass the tier.
**A pin is an alias, not a version, and the regex now says so.**

**Deliverable 5 as shipped.** The display-name pattern was **WIDENED to
`\b(opus|sonnet|haiku|fable)[\s-]+[0-9]`** for the same reason; the walker is
`os.walk(followlinks=False)`, symlink-cycle safe on every supported Python; **both baselines
clean.** ⚠ **Build observation worth keeping: the tripwire's live gate FAILED once mid-build, on a
real instance** — run A's docstring example `claude-opus-4-7-bedrock` — and the example became
`my-bedrock-route`. **That is the gate doing its job before it was ever committed**, and it is the
only evidence this plan has that the tripwire catches anything.

**Deliverable 3 as shipped — the contract `update.sh` and `/devforge:configure` print.** stdout
`{"applied": [{agent, tier, model, effort|null, changed}], "skipped": [{agent, reason}]}`, sorted by
agent, with `reason ∈ {no-frontmatter, unclosed-frontmatter, no-model-tier}`. Exit **0**; exit **2**
on validation (unknown tier, effort outside the enum, a DUPLICATED `model_tier:` / `model:` /
`effort:` key, or `model_tier:` with no sibling `model:`) — **two-pass, nothing written**; exit
**1** on a missing or malformed config or an IO error. ⚠ **The exit-1 bound, stated because it is
the one place the verb is not clean: a WRITE-phase IO error can leave a PARTIALLY APPLIED set** —
each write is atomic, **the batch is not transactional.** Also shipped: alias case normalized at
apply time too, so a legacy stored `Opus` reaches the file as `opus`; `effort:` inserted
immediately after `model:`; `model_tier: scan` has no config knob and takes the static default with
no effort line. ⚠ **CRLF is handled end to end, and the reason is worth keeping**: the command reads
`read_bytes().decode()` because `Path.read_text()` **silently translates `\r\n` to `\n`** and would
have quietly rewritten every line ending in a CRLF consumer's agent files.

**Cross-phase note.** Phase 2 landed `model_pin: opus` on `security-reviewer.md` **in parallel**, so
the real-roster emitter test became `test_every_shipped_agent_emits_model_tier_except_the_declared_pins`
— which pins the LIVE pin set `{security-reviewer: opus}` — plus
`test_security_reviewer_frontmatter_order_unchanged_around_the_pin`.

**Verify block — every bullet satisfied, with the test that proves it.** Step 0's pass and its
record: the block above. Idempotence, an agent with no `model_tier:` left untouched, `default`
removing the `effort:` line, a `null` tier applying the D2 default, and post-apply body
byte-identity: `test_apply_agent_models.py`. The equality pin proved by **mutating a copy**, not by
reasoning: `test_agent_models.py`. The tripwire failing on **both planted shapes**:
`test_model_version_tripwire.py`. `configure_helper verify` exiting 0 with the effort fields unset
**and on a legacy `configure.yaml`**: `test_effort_fields.py`. ⚠ **The last bullet — "zero files
modified under `src/commands/`" — holds for Phase 1's OWN diff only.** The working tree also carries
Phase 2's edits and another session's unrelated edits, **so the Phase 1 commit is made BY EXPLICIT
PATH**, never `git add -A`.

**Suites.** configure + tripwire + emitter = **660 passed / 53 subtests** at the last re-check; full
`tests/lib` green at **11492** as of run A's checkpoint, **re-run at commit time.**

⚠ **One accepted overage, recorded rather than waived:** `test_apply_agent_models.py` is **727
lines**, over the 600-line threshold. **Accepted because ONE source module backs it**, so a split
would divide a single contract across files; **a concern-based third split is the recorded option**
if it grows again.

---

### Phase 2 — The question surface and the contract *(instruction-only)* — **BUILT 2026-09-03** (instruction-reviewer clean; commit pending)

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide` for THIS phase's own
surface.** `q11-tiers.md` ships to `.devforge/command-refs/configure/` and `configure/main.md`
ships into `.claude/commands/devforge/`; **plan 90's Phase-0 orchestrator ruling binds — every
command-spec edit in a plan owes the pass, with no frontmatter carve-out.**

⚠ **This phase does NOT re-ask Phase 1's three frontmatter questions — it CITES their recorded
answers.** Unknown-key tolerance for `model_tier:`, frontmatter key ORDER, and `effort:` on a
`haiku`-aliased agent were all settled at **Phase 1's Step 0**, because Deliverable 4's emitter
change depended on them. **Read that build record and quote it**; asking again would produce a
second answer that can disagree with the code already shipped. **This phase's own pass covers the
question surface Phase 1 never touched** — the `q11-tiers.md` AskUserQuestion shape and the
`configure/main.md` command-spec body.

Scope, four files:

- **`src/commands/configure/references/q11-tiers.md`** — rewritten end to end: D5's four-alias
  probe and its one-line report; then **one AskUserQuestion call per tier carrying BOTH the model
  question and the effort question** (fact 22); the `Other` arm's session-known ID suggestions,
  **labelled unverified** (D3); the six setter calls; recommended labels derived from D2/OQ-1; and
  a one-line Fable note — **needs access, requires 30-day data retention, priced above Opus, and
  `security-reviewer` stays pinned regardless** (D6). ⚠ **The `## Defaults rationale` section's
  `verify = Haiku` recommendation is CORRECTED to `sonnet`** (D2 half 2) with its reasoning
  rewritten, not merely retitled.
  ⚠ **One shape constraint the drafting could not resolve and Phase 2 must:** an option list needs
  **at least two** named options (fact 22). If D5's probe leaves exactly one alias available, the
  model question **falls back to a plain free-text prompt** — the house rule that a free-text-only
  question bypasses the tool. **Write that arm; do not leave it to inference.**
  ⚠ **SUPERSEDED BY THE BUILD, 2026-09-03 — read the free-text sentence as the drafting-time
  proposal, never as the shipped rule.** The one-alias arm **sets that alias** and says so, with a
  reversibility clause keeping the pin route open; a **zero-alias arm** was added beside it. **The
  constraint the drafting named was real; the resolution it guessed was ceremony.** Full reasoning
  at `#### Phase 2 build record`, divergences 1 and 2.
- **`src/commands/configure/main.md`** — the Q11 pointer paragraph (now two questions per call, not
  one); **Phase 5's fourth sub-step** (`apply-agent-models`) with its ordering rationale — it runs
  **after** `substitute-templates` because that step walks the post-prune file set, and applying
  before pruning would rewrite agents about to be deleted; and **every count site reconciled LIVE**
  (fact 15). ⚠ **Plan 89's D6 `regression_gate` note carries its own arithmetic and is UPDATED IN
  PLACE, never removed** — its no-prompt instruction for `regression_gate` is untouched by this
  plan.
- **`src/agents-AUTHORING.md`** — the `model_tier` row **re-derived**: it is no longer *"Emitted as
  `model:` … Not a placeholder"* but *emitted as `model_tier:`, plus a static default `model:` that
  `apply-agent-models` overwrites from configuration*. A new **`model_pin`** row. **A dated note
  recording that the "fixed" contract was consciously EXTENDED by this plan** (D6), naming what was
  added and what was not.
- **`src/agents/security-reviewer.md`** — its meta block gains `model_pin: opus`. ⚠ **The REASON
  lives in `agents-AUTHORING.md`, not in the agent body** — the body is the agent's system prompt,
  and a paragraph explaining a framework-level model choice would be context the agent pays for on
  every dispatch and can act on in no way.

**Verify:**

- Instruction-reviewer clean.
- **claude-code-guide invoked for THIS phase's surface and its answers RECORDED** — the
  command-spec body and the AskUserQuestion shape — **plus a citation of Phase 1's Step-0 answers**
  for unknown-key tolerance, key ORDER and `effort:` on a `haiku`-aliased agent. ⚠ **Re-asking
  those three is a FAILURE of this bullet, not extra rigour**: a second answer that disagrees with
  already-shipped emitter code leaves the plan with two records and no resolution. **An unrecorded
  pass is indistinguishable from one that never ran.**
- **The emitted text does not contradict Phase 1's recorded answers** — instruction-reviewer reads
  the Phase-1 build record before judging the `model_tier:` / `model_pin` prose.
- **`grep -n "Haiku" src/commands/configure/references/q11-tiers.md` shows Haiku is no longer the
  verify recommendation**, and `## Defaults rationale` states the D2 reasons rather than the old
  cost argument. ⚠ **THREE reasons, not four** — the fourth was weakened at Step 0, and the emitted
  text must not repeat a claim this plan corrected (Phase 2's build record, divergence 4).
- **Each per-tier AskUserQuestion call carries exactly two questions and each question 2–4 options**
  — instruction-reviewer confirms against fact 22, and confirms **no authored `Other`** appears
  anywhere (the tool injects it).
- **The single-available-alias fallback arm exists** and names the free-text route.
  ⚠ **AMENDED BY THE BUILD, 2026-09-03 — what shipped is NOT the free-text route.** The arm SETS the
  sole available alias, says so, still asks the effort question, and carries a reversibility clause
  so the pin route stays reachable; **a zero-alias arm the plan never specified was added beside
  it.** The criterion now reads: **both arms exist, and neither asks a free-text question for a
  choice with fewer than two options** (build record, divergences 1 and 2).
- **BOTH tripwire patterns return nothing against
  `src/commands/configure/references/q11-tiers.md`** — the API-ID shape and the
  display-name-with-version shape (D3). The session-known IDs are DESCRIBED as a run-time listing,
  never enumerated in the file. ⚠ **This is the one site most likely to break it**, and the prose
  shape is the likelier breakage here: a Fable note naming a version reads perfectly natural and
  passes the API-ID pattern untouched.
- **The `configure/main.md` counts match a fresh count of the live tuples** (fact 15), the counted
  numbers are in the commit message, and **plan 89's D6 note is updated in place**.
- **`agents-AUTHORING.md`'s meta-block table has one more row and its fixity clause carries a dated
  extension note** — a table silently grown by one row is exactly the drift that clause exists to
  prevent.
- **`git diff src/agents/security-reviewer.md` touches the fenced `yaml` meta block ONLY** — zero
  body bytes.
- **No plan vocabulary in emitted text** — "D6", "OQ-1", "Phase 2" and this plan's number are
  maintainer vocabulary. Emitted text names only commands, files and behaviors.

#### Phase 2 build record (2026-09-03)

**BUILT and instruction-reviewer clean; the commit is pending.** Route as run: **claude-code-guide
for this phase's own surface FIRST**, then instruction-author → instruction-reviewer, which returned
**6 findings — 1 high, 2 medium, 2 low, 1 nit.** Four were in-file fixes, applied and **CONFIRMED on
re-check**; the fifth is this record; the sixth was a cite digit.

**The guide's answers (2026-09-03), and three of the four are "not documented".**

- **The Agent tool's per-invocation `model` parameter IS documented** — `sonnet|opus|haiku|fable`,
  full IDs, `inherit` (`code.claude.com/docs/en/sub-agents.md`). ⚠ **So D5's probe stands on
  documented ground**, which fact 20 could only call an observed tool schema.
- **AskUserQuestion's bounds are NOT documented.** The docs confirm only that a user may pick an
  option or type custom text; the 1–4 questions, 2–4 named options and the injected `Other` row stay
  **OBSERVED** (fact 22's degradation note is unchanged and still binds).
- **What happens when a subagent starts on an inaccessible model is NOT documented.** The probe
  treats **any** error as unavailable — as designed (D5), and now known to be undocumented rather
  than merely unverified.
- **How a running session learns its OWN model is NOT documented** — the docs state that subagents
  do not know theirs. ⚠ **That is D7's session-model half**, it is **Phase 4's** concern, and **it
  stays OBSERVED.** D7's honest bound (i) is unchanged and was not weakened by asking.

⚠ **The HIGH finding was a product of PARALLEL EXECUTION, and the lesson generalizes.** Phase 3
landed its `update.sh` call while this phase was being written, so `main.md`'s Phase 5.4 closing
sentence — *"a follow-up change adds this same call … until that call lands"* — **was already false
when it reached review.** It now describes the landed behavior in the present tense. **Write build
records and forward-looking sentences from the TREE, not from the phase order**: phase numbers are
a plan's sequence, not a guarantee about what is on disk when a sentence is read.

**Five deliberate divergences from this plan's own Phase-2 text. None is ratified elsewhere, and
divergence (1) AMENDS the plan's text by this record rather than silently.**

1. **The exactly-one-available-alias arm.** The plan said *"a plain free-text prompt"*. What shipped
   **SETS the sole available alias** through the setter, says so in one line, **still asks the
   effort question**, and carries a reversibility clause (`set-claude-tier-<tier>` +
   `render-config` — the pattern `main.md` already uses for `require_ticket` and `regression_gate`)
   **so the pin route stays reachable.** Reason: **a free-text prompt for a one-option choice is
   ceremony.** ⚠ **The plan's Phase-2 scope bullet still names the free-text route; THIS RECORD is
   its amendment.**
2. **A zero-aliases-available arm the plan never specified:** save no model, **the built-in tier
   default stands**, still ask effort.
3. **A new rule, first of its kind in that file:** when a tier's recommended alias is unavailable,
   **NO option carries `(Recommended)`** — the marker is **never moved** to another alias. **This
   sets a precedent for future additions to `q11-tiers.md`**: the recommendation belongs to a named
   alias, not to a position in the list.
4. **`## Defaults rationale` gives THREE reasons for `verify = sonnet`**, the fourth having been
   weakened at Step 0 — and **the Haiku/effort fact rides the `haiku` option descriptions as the
   DOCUMENTED SILENT FALLBACK, never as an API error.** The emitted text does not repeat a claim
   this plan corrected.
5. **Two docs URLs are cited inline in emitted text** (`sub-agents.md`, `model-config.md`) — **new
   for `q11-tiers.md`**, and a precedent for that file. **No plan vocabulary reached either emitted
   file.**

**What landed.** `q11-tiers.md` rewritten end to end — intro · `## Availability probe — run before
Q11.1` · `## Q11.1/2/3`, one call carrying two questions each · `## Pinning a model the list did not
offer` · `## Saving the answers` · `## Defaults rationale` with the three honest bounds.
`configure/main.md` — line 9, the Outputs bullets, the Phase 4 intro (**ten** user-only prompts,
with Q11 named as the one-call-two-questions exception), `### Q11`, the Phase 5 intro renamed
**`Render + prune + substitute + apply`** with four sub-steps, a new **`### Phase 5.4 — Apply agent
models`** carrying the JSON shape and exit codes 0/1/2 **including all four validation causes**,
plan 89's `regression_gate` note **updated IN PLACE with its guidance verbatim**, and the Closing.
`agents-AUTHORING.md` — the `model_tier` row re-derived (**emitted TWICE**), a new `model_pin` row,
a dated contract-extension note naming **what stayed fixed** (the field names and their
required/optional status) and **the one emitted-form change** (`model_tier`'s companion line), the
skeleton parenthetical, the checklist, and every cite re-derived live
(`generate-agents.py:260→:328`, `:168→:195`, `:215→:278`; `install_defaults.py:30→:39`; plus `:84`
for `_MODEL_PIN_RE`). `src/agents/security-reviewer.md` — meta gains `model_pin: opus`.

**Counts written, COUNTED live:** schema **35**; **34** populated by the command = **24**
detection-derived + **10** user-only prompts (Q9, Q10, Q11 × 6, Q12 mode, Q13); keys **43** = 35 + 5
+ 3.

**Verify — satisfied.** The three greps clean: no stale 31/32/40, no *"Which model name"*, and no
version string of either shape anywhere under `src/`. `python3 scripts/lib/model_version_tripwire.py
src` → **PASS** after the edits. The emitter roster test is recorded in Phase 1's block.

⚠ **Carry-forwards — Phase 5's sweep list is TOO NARROW and is widened by this record.** Four sites
sit outside it today, and the last two are pre-existing rather than this plan's:

- **`DEVELOPMENT-STATUS.md:58`** — a **SECOND** stale `MODEL_THINK` / `MODEL_DO` / `MODEL_VERIFY`
  site beside the `:104` one Phase 5 already names. **A fix that corrects only `:104` leaves `:58`
  looking verified.**
- **`docs/v2/ARCHITECTURE.md`** — `:260` / `:285` / `:321` / `:328` / `:384` say 29 fields / 37
  keys, `:398` recommends `verify=Haiku`, and `:277` / `:310` describe Q11 as a bare tier triple.
  ⚠ **No plan's sweep has ever covered `docs/`** — an accumulating gap that is **a maintainer
  decision, not a Phase-5 judgment call**: frozen history, or owed a sweep.
- **`src/agents-AUTHORING.md:87`** — *"17 agents in four families"*; **the census is 19** (fact 3).
  **Pre-existing.**
- **`install.sh:298`'s *"35-key ALL-NULL stub"* comment and `src/devforge/project-config.json`
  itself** — 35 keys against 43 live. **Functionally harmless for `apply-agent-models`, verified**:
  its `.get()` reads a null and an absent key alike. **Recorded options:** regenerate the stub from
  `_PROJECT_CONFIG_KEY_ORDER`, or pin the two equal with a maintainer test, plan-89 style.

---

### Phase 3 — The `update.sh` post-merge apply call *(shell)* — **BUILT 2026-09-03** (python-reviewer clean; commit pending)

**Route: python-engineer → python-reviewer** (the repo's shell edits ride the same review loop; no
claude-code-guide pass is owed — `update.sh` ships nowhere inside `.claude/`).

**Deliverable — the smallest possible call.** After the merge loop and the new-agent install loop
(fact 11), under the **same `HAS_CONFIG` guard `substitute_placeholders()` already uses**, invoke
`configure_helper apply-agent-models` and **print its summary** through the script's existing
reporting helpers. `update.sh` already calls `configure_helper render-config` directly (fact 12),
so the shape has a precedent and needs no new mechanism.

**Verify `install.sh` needs nothing** — and **record the check as a finding either way.** The
reasoning to confirm: `install.sh` runs before `/devforge:configure` has ever run, so there is no
configuration to apply, and the emitted static defaults are correct at that moment (D1).

**⚠ Two constraints:**

1. **The call runs AFTER the snapshot refresh, never before.** The snapshot must keep the RAW
   regen (fact 11), so an apply that ran first would poison every future three-way merge with a
   consumer-specific model line.
   ⚠ **THE CONSTRAINT STANDS; THIS EXPLANATION WAS TRACED AND FOUND WRONG (2026-09-03).** Every
   snapshot write sources from `$REGEN_AGENTS_DIR` / `$TEMPLATE_DIR`, **never from the live
   target**, so an early apply **cannot** poison the baseline and the *"poison the baseline"*
   framing is **retired from this plan's vocabulary.** **The real hazard:** an apply that ran BEFORE
   the merge **pre-mutates the live file's *current* side before the diff is computed** — and if the
   same release also changed a tier's static default, that manufactures a **spurious three-way
   conflict**, whereupon the file's snapshot refresh is skipped and the snapshot goes **stale**.
   Full trace in `#### Phase 3 build record`.
2. **A failure is reported, not fatal.** `update.sh` warns and continues elsewhere in this same
   loop; an apply failure leaves agents on their static defaults, which is a degraded state and
   not a broken one.

**Verify:**

- python-reviewer clean.
- **A configured install keeps its model through an update** — the Phase-6 anchor 3 recipe, run
  here as far as a local reproduction allows, with the result recorded as a build observation and
  **never as a consumer validation.**
- **An UNCONFIGURED install is unaffected** — `HAS_CONFIG` false means no apply, and the run's
  output is byte-comparable to a pre-change run except for the absent call.
  ⚠ **TRUE BUT NOT THE REALISTIC CASE, found 2026-09-03.** `install.sh` ships an **ALL-NULL
  `project-config.json` stub**, so **`HAS_CONFIG` is TRUE from the very first update** and the block
  DOES run — as a **byte-level no-op** (every null tier resolves to its default, which matches the
  emitted static `model:`). **The criterion that actually matters is the no-op, not the skip**, and
  both were verified; see the build record.
- **⚠ The static-default merge-conflict question is ANSWERED, not assumed** (Trap 3). Construct the
  case — a consumer file whose `model:` differs from both the old and the new static default — and
  **record what `git merge-file` actually does.** If it conflicts, `update.sh` leaves the whole file
  unchanged (fact 11), which means the agent's BODY update is skipped too. **Record the finding; do
  not repair it in this phase.**
  ✅ **ANSWERED 2026-09-03 — it CONFLICTS, and the consequence is worse than the bullet anticipated.**
  See the build record's item (c): the file's whole update is skipped **body included**, its snapshot
  goes stale, the condition **recurs on every subsequent update**, and the post-merge apply then
  makes the `model:` field read correct **while the stale body stays invisible.** **Recorded as an
  OPEN residual, not repaired.**
- `grep -n "apply-agent-models" update.sh install.sh` returns hits in `update.sh` only, and the
  `install.sh` no-op is recorded in the commit message as deliberate.

#### Phase 3 build record (2026-09-03)

**BUILT and python-reviewer clean; the commit is pending.** Route as run: python-engineer →
python-reviewer, **7 findings — 3 medium, 3 low, 1 nit.** Six were applied and **CONFIRMED on
re-check**; the seventh — `install.sh:298`'s *"35-key"* stub comment and the 35-vs-43
`project-config.json` gap — is **pre-existing and was carried to Phase 5**, where it already sits on
the widened sweep list. **One further Low surfaced during the re-check** (a missing `2>/dev/null` on
the changed-agent listing `jq`) and was **closed in the same pass**. `shellcheck` — installed during
review — reports **zero findings in both touched ranges**; `bash -n` clean.

**What landed — `update.sh` ONLY, +48 lines.** An `# ── Execute: apply-agent-models (plan 92 D1)`
block placed **after the removed-agent prune loop and the `REGEN_AGENTS_DIR` cleanup, before
`# ── Execute: mergeFiles`**, under the **same `HAS_CONFIG` guard** `substitute_placeholders()`
already uses. It captures the verb's stdout and exit code **without tripping `set -e`**, and on
exit 0 prints `Applied agent models: N with model_tier (M changed), K skipped` plus one `info` line
per changed agent (`<agent>: model=<model> effort=<effort or default>`). The `--dry-run` report
gained a matching `APPLY agent models: …` preview line beside the agent previews. `--only <command>`
surgical mode **exits before agents and never reaches the block** — correct, since it touches no
agent file.

⚠ **A latent WHOLE-SCRIPT ABORT was found by the reviewer and confirmed by simulation.** Every
downstream `jq` is now guarded (`2>/dev/null` + `|| VAR="?"`, the listing `done || true`), so a
helper regression that emits malformed stdout **degrades to a legible `?` line instead of killing
the update**: a `{not valid json` stdout now yields `? with model_tier (? changed), ? skipped` and
**the run continues.**

⚠ **The failure warning is worded to be TRUE on all three failing paths**, which is why it is vague
about which one happened: *"some agents' model/effort lines may be out of date or partially applied;
re-run `/devforge:configure` to reconcile"* covers **exit 2** (nothing written), **exit 1 in pass 1**
(nothing written) **and exit 1 in pass 2** (a partial batch — D1's recorded non-transactional bound).
Each stderr line is then printed through its own `warn`, and the run continues.

**`install.sh` needs nothing, and the check is recorded as a finding:** it runs before
`/devforge:configure` ever has, so the emitted static defaults are correct at that moment (D1).
**`grep -n apply-agent-models install.sh` is empty BY DESIGN.**

⚠ **The ordering comment was CORRECTED during review — record the TRACED mechanism, not the drafted
one.** The constraint (apply **after** the snapshot refresh) is unchanged; **its explanation was
wrong.** Every snapshot write sources from `$REGEN_AGENTS_DIR` / `$TEMPLATE_DIR` and **never from
the live target**, so an early apply **cannot** "poison the baseline" — that framing is retired. The
real hazard is that an early apply **pre-mutates the live file's *current* side before the diff is
computed**; combined with a release that also changed a tier's static default, it manufactures a
**spurious conflict**, and a conflicted merge **skips that file's snapshot refresh**, leaving the
snapshot stale. **A correct constraint resting on a wrong reason is a latent trap** — the next
person to "simplify" it would have reasoned from the retired framing.

**Verify results — LOCAL REPRODUCTION, a build observation and NOT consumer validation.** ⚠ **None
of this is Phase 6.** Nothing below was run on a real consumer install, and a passing local
reproduction is not an anchor.

- **(a) Phase-6 anchor 3, run locally.** A scratch copy of the repo installed into a scratch target,
  configured `think = fable` / effort `xhigh`; then an agent-**BODY** edit in the scratch template's
  `src/agents/architect.md` and a non-interactive `update.sh`. **The body change arrived,
  `model: fable` / `effort: xhigh` survived, and the summary line printed.** A second reproduction
  from a **configured-but-never-applied** state showed non-zero `changed` counts and the per-agent
  lines.
- **(b) The unconfigured install, and the realistic case is the OTHER one.** With no config at all:
  no apply line, agents byte-identical. ⚠ **But the real post-install state differs** — `install.sh`
  ships an **ALL-NULL `project-config.json` stub**, so `HAS_CONFIG` is true from the first update and
  the block runs as a **byte-level NO-OP**: every null tier resolves to its default, which matches
  the emitted static `model:`; `changed: false` everywhere; `security-reviewer` appears under
  `skipped` as `no-model-tier`. **Verified with md5 before and after.**
- **(c) Trap 3 ANSWERED — it CONFLICTS, and the consequence is worse than the trap predicted.**
  `git merge-file` on base `model: opus` / current `model: fable` / other `model: sonnet` **conflicts
  (exit 1, conflict markers).** So a future change to a tier's **static default** would, for every
  consumer whose configured model differs from both, leave that agent file's **WHOLE update
  unapplied — body included** — and its **snapshot stale**, a condition that **recurs on every
  subsequent update** until someone resolves it by hand. ⚠ **And the failure is camouflaged:** the
  post-merge apply re-derives `model:` / `effort:` from configuration regardless, **so the model
  field reads correct while the stale body is invisible from the `Applied agent models` line.** The
  **only** signal is the earlier, decoupled `Merge conflicts in <file>` warn. **RECORDED, NOT
  REPAIRED** — out of this phase by the plan's own instruction. ⚠ **OPEN RESIDUAL for a future
  plan**, with its two candidate shapes: **change a static tier default only with a migration note**,
  or **teach the merge to treat the `model:` line as consumer-owned.**
- **(d) A forced malformed config:** the script **warns and completes with rc=0.**

---

### Phase 4 — The D7 advisory lines *(instruction-only)* — **BUILT 2026-09-03 — reviewed CLEAN** (instruction-reviewer re-check, zero new findings)

**Route: instruction-author → instruction-reviewer → claude-code-guide** (every command-spec edit
owes the pass; plan 90's Phase-0 ruling).

**Deliverable.** One PHASE-0 advisory line in each command of OQ-2's ratified set, **each naming
its own tier inline** (D7 — no central table). The line is printed always, asks nothing, and gates
nothing.

**⚠ Three constraints:**

1. **The session-model half degrades to `unknown`** (fact 21). An orchestrator that cannot state
   the session model prints `unknown` and continues — it never omits the line and never guesses.
2. **The configured-model half reads `project-config.json`.** An absent or `null` `CLAUDE_TIER_*`
   prints the D2 default, matching what apply would have written.
3. **No command's PHASE 0 gains a question, a branch or an exit path.** `stakes-hint`'s contract is
   the model: always exit 0, gates nothing (fact 17).

**Verify:**

- Instruction-reviewer clean; **claude-code-guide invoked per command-spec edit and each answer
  RECORDED.**
- **The line appears in exactly the ratified command set** — `grep -c` the line's distinctive
  phrase across `src/commands/` and compare against OQ-2's count. **A line in a command outside the
  set is scope creep, not thoroughness.**
- **Every instance names a tier and none names a version.** **BOTH** tripwire greps over `src/`
  still return zero — the API-ID shape and the display-name-with-version shape (D3).
- **No instance contains "must", "block", "abort" or a question mark.** Instruction-reviewer
  confirms the line is advisory in its GRAMMAR, not only in a nearby sentence.
- **The `unknown` arm is written**, not left to inference.
- **Each edited command's PHASE 0 has the same number of exit paths before and after** — capture
  the pre-change structure first.

#### Phase 4 build record (2026-09-03)

**BUILT and instruction-reviewer CLEAN** — the re-check returned **zero new findings**. One step per
command across OQ-2's eight, **title identical
in all eight** — `Model advisory (printed, never gating)` — with the **heading shape following each
file's own convention** rather than a single imposed level: `### Phase 0.6` (specify),
`## PHASE 0b.5` (plan, breakdown), `### 0.4` (grill, review, verify), `### 0.5` (fix), and a bold
lead-in (implement). **The printed line is byte-identical modulo the tier word.**

**The configured value is read in PROSE from `project-config.json`, not by a helper call.** ⚠ **`jq`
appears in none of the eight target files** — a prose read is the house idiom there — and a `null`
tier resolves to the D2 default, matching what `apply-agent-models` would have written. Each step
**names `apply-agent-models` for provenance with an explicit "NOT invoked by this step" clause**, so
a reader cannot mistake the advisory for the apply. `verify/main.md`'s helper-interaction invariant
is untouched **because the step makes no Bash call at all.**

⚠ **One deliberate divergence from the brief's wording, and it is a correctness fix.** The brief
said to place the step *before* each chain's trailing exit arm; the build placed it **AFTER** them,
so the line prints **only when the chain continues.** **Printing a model advisory on a failure path
would be wrong** — the command is not about to do the judgment work the line describes.

**Constraint checks, all three met.** The `unknown` arm is written explicitly. The `null` arm reads
the D2 default. **Exit-path counts are identical before and after in all eight** — specify 10, plan
12, grill 6, breakdown 11, implement 2, fix 22, review 8, verify 8. **`judgment work belongs to the`
occurs exactly EIGHT times under `src/`**, matching OQ-2's set with nothing outside it; both
tripwire greps return zero; and no added line contains *must*, *block*, *abort* or a question mark.

**One pre-existing sentence amended, and it was necessary rather than incidental:**
`specify/main.md` Phase 0.5's *"proceed directly to Phase 1"* became *"Phase 0.6"* — **without it
the common path would have skipped the new step entirely.** ⚠ **Deliberately NOT amended:**
`specify/main.md:29`'s *"Four preflight steps"* sentence **counts gates, not headings**, so the new
non-gating step does not move it.

**The `claude-code-guide` pass for this phase returned four things, and the fourth was the big one.**
(i) **There is no documented way for a command to learn the session model** — `env-vars` lists
`ANTHROPIC_MODEL` as a *startup* setting only, and the skill substitution variables are
`CLAUDE_SESSION_ID`, `CLAUDE_EFFORT`, `CLAUDE_SKILL_DIR`, `CLAUDE_PROJECT_DIR`,
`CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, **none of which carries a model** — so **the `unknown`
arm is the documented-correct fallback**, not a gap left open. (ii) Command bodies are unconstrained
(*"Skill files can contain any instructions"*). (iii) `disable-model-invocation` governs **who may
invoke** a command, never **what it prints**. (iv) ⚠ **Commands DO support `model:` and `effort:`
in their own frontmatter** — which **refuted fact 19 and D7's stated premise**, and is recorded at
fact 19, at D7's alternative and honest bound (iii), and as **OQ-5**. **The advisory line ships as
ratified; what changed is that it is now known to be a choice rather than the only option.**

**Instruction-reviewer, first pass — TWO HIGH findings, both the same shape: the step was
BYPASSABLE on a live path.** A line placed after the trailing exit arms prints only when the chain
continues (the divergence above), **but a chain can continue through an arm that is not the
trailing one** — and in two commands it did:

- **`/devforge:implement`** — its **four continuing arms** (`Absent`, resume, rollback, skip) each
  resumed the chain past the advisory. All four now route through it. **Exit arms still 2**, so the
  fix moved control flow into the step without adding an exit.
- **`/devforge:specify`** — the **matched-seed arm at Phase 0.5** continued without reaching the
  step; it now routes to Phase 0.6, and the **multi-seed sub-case deliberately names no downstream
  phase**, so it cannot go stale when a phase is renumbered.

⚠ **The lesson is narrower than "check the arms": placement after the trailing exit is necessary and
not sufficient**, because "the chain continues" is a property of every arm, not of the last one.

**Reviewer finding 1 was D7's premise, and it was NOT closed inside this phase** — it is a plan-level
correction, closed at **fact 19, D7 and OQ-5**. Recorded here so the phase's clean re-check is not
read as having settled it.

**One LOW, and the ruling that came with it.** `verify/main.md`'s step gained the clause *"via the
Read tool and not a Bash call"*, because that file carries a helper-interaction invariant a silent
new step could appear to violate. ⚠ **The reviewer ruled that `grill`, `review` and `fix` need NO
such clause** — their helper-interaction paragraphs make **no completeness promise**, so adding one
there would assert a constraint those files do not carry. **Four files, one clause, by their own
text — not a uniformity edit.**

**One nit declined on the file's own evidence:** the colon stays **off** in `implement`, that file's
idiom being unanimous.

⚠ **A PRE-EXISTING BUG was repaired BEYOND this phase's brief, and the reviewer accepted it as
in-scope.** `specify/main.md` Phase 0.4's **three pick arms** (`:127`–`:129`) and its **warning
path** (`:135`) all said *"Continue to Phase 1"* — **textually skipping the "unconditional" seed
check at Phase 0.5**, and therefore 0.6 as well. All four now say *"Continue to Phase 0.5"*.
**Semantics preserved, exit arms unchanged at 10.** ⚠ **This is the second time in this plan that a
step described as unconditional was reachable only on some paths** (the first being the two HIGHs
above) — **"unconditional" in prose is a claim about the writer's intent, not about the control
flow**, and only reading every arm distinguishes them.

---

### Phase 5 — Docs sweep — **BUILT 2026-09-03** (instruction-reviewer route; commit pending)

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit; **plus
claude-code-guide for `src/CLAUDE.md`** if it is touched (it ships as the consumer's root
`CLAUDE.md`).

Open the phase with `grep -rn "CLAUDE_TIER\|model_tier\|MODEL_THINK\|tier" src/ scripts/ *.md` and
reconcile every hit against what this build made true. **This sweep list is NOT certified
exhaustive** — treat a hit not named below as an omission in this plan, not as a new defect.

Scope:

- **`DEVELOPMENT-STATUS.md:104`** — corrected on **both** counts (fact 10): the key names become
  `CLAUDE_TIER_THINK` / `CLAUDE_TIER_DO` / `CLAUDE_TIER_VERIFY`, and **the claim becomes true for
  the first time.** ⚠ **Its parenthetical enumeration of think-tier agents is incomplete** — five
  agents, not three (fact 3). **Fix it or drop the enumeration; do not leave it half-corrected.**
  ⚠ **WIDENED 2026-09-03 by Phase 2's build: `:104` is NOT the only site.** `DEVELOPMENT-STATUS.md:58`
  carries a **SECOND** stale `MODEL_THINK` / `MODEL_DO` / `MODEL_VERIFY` triple. **A fix that corrects
  only `:104` leaves `:58` looking verified** — grep the file for the three key names rather than
  going to a line number.
- ⚠ **`docs/v2/ARCHITECTURE.md` — OUTSIDE this plan's original scope, and the decision is the
  MAINTAINER'S, not Phase 5's** (found by Phase 2's build). It says 29 fields / 37 keys at `:260`,
  `:285`, `:321`, `:328`, `:384`; recommends `verify=Haiku` at `:398`; and describes Q11 as a bare
  tier triple at `:277` and `:310` — **every one of those falsified by this plan.** ⚠ **No plan's
  sweep has ever covered `docs/`**, so this is an accumulating gap rather than a defect this build
  introduced. **Surface it and ASK: frozen history, or owed a sweep?** Do not decide it inside a
  docs-sweep phase.
- ⚠ **`src/agents-AUTHORING.md:87` — PRE-EXISTING, unrelated to this plan.** It says *"17 agents in
  four families"*; **the census is 19** (fact 3). **Record it as pre-existing** wherever it is fixed.
- ⚠ **`install.sh:298`'s *"35-key ALL-NULL stub"* comment and `src/devforge/project-config.json`** —
  35 keys against 43 live. **Functionally harmless for `apply-agent-models`, and that was VERIFIED,
  not assumed**: its `.get()` reads a null and an absent key alike. **Two recorded options, neither
  built here**: regenerate the stub from `_PROJECT_CONFIG_KEY_ORDER`, or pin the two equal with a
  maintainer test in plan 89's style. **Phase 1 deliberately left that file alone**; if Phase 5 also
  leaves it, **record the no-op as deliberate** rather than silent.
- **`scripts/lib/install_defaults.py` and `scripts/generate-agents.py`** — the two unbuilt-intent
  comments (facts 1, 2). ⚠ **These are COMMENTS in Python files, so this is the one Phase-5 edit
  that touches a `.py` file** — it changes no code, and a reviewer must be able to see that from
  the diff. *"Wizard's Q10a may override per tier"* and *"The post-install config step may
  OVERWRITE these via key-based regex replacement"* both become statements about
  `apply-agent-models` — **which is what they always described and never named.**
- **`CHANGELOG.md`** — an entry under the existing `## [Unreleased]` → `### Added`. **Read the file
  live.** The entry must state the honest bounds: the tier knob is now live (a fix); model choice
  is version-free by alias; effort is configurable and **unvalidated against the model**; the
  per-command line is **advisory**; and Fable is offered **only where the session can dispatch it**.
- **`README.md` and `src/CLAUDE.md`** — **grep at build; touch ONLY if they mention tiers or agent
  models.** ⚠ Plan 08's always-on-trim discipline binds `src/CLAUDE.md` — every line costs tokens in
  every session — so the bar there is "a sentence a session actually needs", and **"checked, nothing
  to amend" is a finding to record**, not a phase that failed.
- **Repo-root `CLAUDE.md`** — the plan-92 one-liner appended to the active-plans index, matching the
  neighbouring entries' density. **Read the file live for the append point**; the index grows and a
  pre-computed position rots.
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry, per this repo's index/archive split.
- **`15-AGENT-STANDARDIZATION-PLAN.md`** — a dated note that its meta-block contract gained an
  optional `model_pin` field and that `model_tier` is now emitted rather than resolved at emission
  (D6, D1). **Do not edit its reasoning** — it is still the record for the skeleton.
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** — **check only, and record the no-op as deliberate**:
  the 13/7 counts take no delta (D9). **Read them LIVE rather than quoting a remembered number** —
  that is plan 63's own standing coordination rule.
  ✅ **READ LIVE 2026-09-03 and they HAD MOVED: the counts are now 16/4**, because **plan 93**
  removed `disable-model-invocation: true` from `/devforge:grill`, `/devforge:spec-check` and
  `/devforge:fix`. ⚠ **This plan's delta is still ZERO** — it changed no flag and added no command;
  a `disable-model-invocation` grep over `src/commands/` returns the four setup commands.
  **This is exactly what plan 63's coordination rule exists to catch**: the remembered number was
  stale within a day, and quoting it would have written a false count into four files.

**Commits: one per phase**, lowercase terse subject with a scope prefix matching `git log --oneline`.
⚠ **CORRECTED 2026-09-03 — the drafting-time clause *"no AI-attribution trailer (this repo's commits
carry none)"* was FALSE at build time.** The repo's last eleven commits, across two sessions, all
carry the harness `Co-Authored-By` + `Claude-Session` trailers, and **this plan's three commits
followed that observed convention.** The clause is retired rather than reasserted: **read the live
`git log` for the trailer convention, never this sentence.**

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **`DEVELOPMENT-STATUS.md:104` names the live key names AND a true claim AND a correct agent
  enumeration** — three separate errors, and a fix that lands two of three has left the third
  looking verified.
- **Neither Python comment still describes an unbuilt mechanism.** `grep -n "Q10a\|may OVERWRITE"
  scripts/` returns nothing.
- **The `CHANGELOG.md` entry states the bounds.** An entry claiming the framework "runs on Fable"
  without "where available" and "advisory" has over-claimed by two layers.
- **The repo-root one-liner names the evidence split** — one grep-verified defect plus four
  maintainer directives; no consumer incident.
- **Plan 63's counts were read LIVE and did not move**, and the check is recorded.
  ⚠ **FALSIFIED 2026-09-03 — they DID move.** The criterion's *"and did not move"* clause was an
  assumption, not a requirement; **what the rule demands is the LIVE READ, not a particular
  result.** The counts are **16/4** via plan 93. **This plan's delta is still zero**, which is the
  thing the criterion actually tests.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass — a failure here
  means something unintended moved in the agent roster.

#### Phase 5 build record (2026-09-03)

**BUILT; commit pending.** Executed against the LIVE tree, with the scope list as widened by Phase
2's build record. ⚠ **Phase 4 was written IN PARALLEL by another author** into the eight OQ-2
command specs; **this phase touched none of those eight and none of `src/commands/configure/*`**,
and Phase 4's text is verified against the tree by the orchestrator before commit. **This is the
second time parallel execution shaped a phase in this plan** — the first produced Phase 2's HIGH
finding — so the rule stands: **write from the tree, not from the phase order.**

**Edited — nine files.** `DEVELOPMENT-STATUS.md` (**both** stale sites: `:58`'s key list, which now
also states that the tier/effort keys are **not** placeholder-substituted but read by
`apply-agent-models`, and `:104`'s three errors — key names, the configurability claim now **true
for the first time**, and the think-tier enumeration corrected to all five agents, with a sub-bullet
recording that the knob was write-only until this build); `CHANGELOG.md` (one `### Added` entry in
the house's dense single-bullet style, carrying the evidence split, what shipped, and every honest
bound — **it never says "runs on Fable"**); repo-root `CLAUDE.md` (the plan-92 index line, between
the `91-` and `93-` lines); `PLAN-STATUS-ARCHIVE.md` (the mirrored full entry, same position);
`15-AGENT-STANDARDIZATION-PLAN.md` (a dated note under its *"build contract (fixed …)"* section —
**its reasoning is untouched**); `src/agents-AUTHORING.md` (`:87`); `docs/v2/ARCHITECTURE.md`
(narrowly — see below, **thirteen sites after the reviewer's correction, not the five this record
first claimed**); and this plan file.

⚠ **`docs/v2/ARCHITECTURE.md` changed from DO-NOT-EDIT to a NARROW edit on the maintainer's
2026-09-03 pick, recorded verbatim: *"fix only the falsified sites"*.** The full-sweep option was
**explicitly NOT chosen.** First pass corrected: the setter table's user-prefs row (5 → 8, naming
the three effort setters and the enum asymmetry), a new `apply-agent-models` row, `render-config`'s
key count (37 → **43**), the schema line (29 → **35** fields, ENUM_FIELDS 3 → **8** with all eight
named, the *"claude_tier_* deliberately NOT in ENUM_FIELDS"* clause KEPT and extended with the alias
normalization), the Q11 description in the phase diagram (a bare tier triple → three calls each
carrying a model and an effort question, preceded by the probe), and the recommended defaults
(`think=Opus, do=Sonnet, verify=Haiku` → `think=opus, do=sonnet, verify=sonnet`, effort `default`,
**lowercase as Claude Code spells the aliases**).

⚠ **THE FIRST PASS WAS INCOMPLETE, and this record reports the corrected state rather than the
earlier claim.** instruction-reviewer found **five more sites of the SAME falsified class** that the
sweep had missed — the overview line (*"fills 29 configuration fields … 37-key substitution map"*),
the Phase-7 line in the phase diagram, **§4.3's own heading formula** (recomputed **35 + 5 + 3 =
43**), the *"canonical 29-field state"* tree comment and the *"37-key render artifact"* one — plus a
**sixth the reviewer did not name and this pass found while re-grepping**: the field-classification
table's *"Verbatim from the 37-key map"*. **A narrow fix is only narrow if it is complete over its
own class**, and `\b(29|37)\b` now returns **zero** across that file.

⚠ **A MEDIUM the reviewer raised separately, and it was already wrong before this plan touched it:**
§4.3's *"User-only (6 fields via Phase 4 sequential prompts)"* omitted the three `CLAUDE_EFFORT_*`
fields **and `REQUIRE_TICKET`**. Re-derived LIVE from `configure/main.md`'s Phase 4 — Q9, Q10,
Q11 × 6 (three calls, each a tier's model plus its effort), Q12's mode, Q13 — it is **10**, and the
list now names each field with its question number. **The AC runtime triple stays counted with the
detection-derived group**, as that section already had it.

⚠ **One further arithmetic repair, and it is a SCOPE CALL made explicitly rather than silently.**
Correcting the user-only count to 10 left §4.3 self-contradicting, because its detection-derived
count still read **23** while `configure/main.md` composes **24** — a falsification owned by
**plan 90's `E2E_COMMAND`**, not by this plan. Fixing it required adding one enumeration line
(`E2E (1)`). **Done, because a section whose own numbers do not add up is worse than either number
alone**, and because both figures are mechanically derivable from the live tree; **recorded here as
crossing into another plan's field so the next reader knows it was deliberate.**

⚠ **Still deliberately NOT touched: that file's genuinely unrelated stale counts** — *"~32
subcommands"* at `:266` and `:568` — **left as an accumulated gap for a separate maintainer item**,
per the pick. **All counts were COUNTED from `_schema.py`, `_render.py` and `configure/main.md`,
never carried.**

**Verified no-ops, each recorded as a finding rather than a silence.** `README.md` and
`src/CLAUDE.md`: **checked, nothing to amend** — a case-insensitive grep for `model_tier` and the
four aliases returns nothing in either, and plan 08's trim discipline binds the latter, so adding a
sentence a session does not need would have been the wrong outcome. `scripts/lib/install_defaults.py`
and `scripts/generate-agents.py`: **already done at Phase 1, verified** —
`grep -n "Q10a\|may OVERWRITE" scripts/` returns nothing, so **this phase edited no `.py` file at
all** and the plan's *"one Phase-5 edit that touches a `.py` file"* sentence describes work Phase 1
absorbed. `install.sh:298` and `src/devforge/project-config.json`: **left alone deliberately**, the
35-key stub against 43 live keys being **functionally harmless and VERIFIED so** (`apply-agent-models`
reads a null and an absent key alike); the two recorded options — regenerate the stub from
`_PROJECT_CONFIG_KEY_ORDER`, or pin the two equal with a maintainer test in plan 89's style —
**stay unbuilt.** `63-SKILL-COLLISION-SUPPRESSION-PLAN.md`: **check only, no-op deliberate.**

⚠ **Plan 63's coordination rule EARNED ITSELF on this run.** The counts were read live and **had
moved: 13/7 → 16/4**, because plan 93 removed `disable-model-invocation: true` from
`/devforge:grill`, `/devforge:spec-check` and `/devforge:fix` on the same day. **This plan changed
no flag and added no command, so its delta is still ZERO** — the live grep over `src/commands/`
returns the four setup commands. **Quoting the remembered figure would have written a false count
into four ledger files.** The five in-plan `13/7` mentions now each carry a dated note; the repo-root
router row was already updated by plan 93 and was **left alone**.

⚠ **`src/agents-AUTHORING.md:87` — a PRE-EXISTING correction, unrelated to this plan's mechanism.**
*"17 agents in four families"* became the live **19**, counted from `src/agents/*.md`. **The four
family lists name only 17**: `devils-advocate` (added by plan 23) and `spec-formalizer` (plan 62)
are named by **no** family. Both are `model_tier: think` with read-only `tools:` allowlists, so they
satisfy the tools-locked family's constraints — **but which family they belong to has never been
decided, and this edit RECORDS the gap rather than deciding it.** Filing them would have been an
editorial call this plan has no mandate to make.

⚠ **One claim in this plan's own text was falsified and corrected here**: the Phase-5 commit
instruction said *"no AI-attribution trailer (this repo's commits carry none)"*. **The repo's last
eleven commits across two sessions all carry the harness `Co-Authored-By` + `Claude-Session`
trailers**, and this plan's three commits followed that observed convention. The clause is retired
in favour of reading `git log`.

**Verify — results, reported as they actually came back rather than as the phase predicted.**

`grep -rn "MODEL_THINK\|MODEL_DO\|MODEL_VERIFY" *.md src/ scripts/` → **ZERO hits in `src/` and
`scripts/`**, which is the criterion. The surviving `.md` hits are all deliberate: the released
`CHANGELOG.md` entry describing the **v1 `{{MODEL_THINK}}` placeholders** (history, correctly left —
**grep the string, not a line number; this phase's own insertion shifted it**), this plan's
quotations of the defect at fact 10 and in `## Origin`, the Phase-5 scope bullet naming the two
sites, and the new `PLAN-STATUS-ARCHIVE.md` entry quoting the same defect.

⚠ **`grep -n "13/7" CLAUDE.md DEVELOPMENT-STATUS.md README.md src/CLAUDE.md` does NOT return zero —
it returns SIX, all in repo-root `CLAUDE.md`, and none is a live claim about today's counts.**
Reported rather than "fixed", because five belong to other plans' records and one is not about
commands at all:

- **Plan 74's line — a FALSE POSITIVE on the string.** Its *"13/7 disposition table"* is the
  memory-lane disposition table, unrelated to model-invocable commands.
- **Plans 82, 85, 88, 89 and 90's lines — HISTORICAL, and correct as dated.** Each records what its
  own plan decided while the counts *were* 13/7 (*"plan 63's 13/7 carve-out is NOT reopened"*,
  *"Plan 63's 13/7 counts UNCHANGED"*, and two non-goal statements). **Rewriting them would falsify
  the record of what those plans decided.** Plan 93 already appended dated corrections to the two
  entries where a reader could most easily mistake the historical figure for a live one (plans 63
  and 82), which is the right shape; **extending that to the other three is a decision for whoever
  owns those entries, not a side effect of this sweep.**

**The criterion this phase actually owed is met**: no file it wrote carries a live 13/7 claim, and
the five in-plan mentions each gained a dated 16/4 note.

`grep -n "Q10a\|may OVERWRITE" scripts/` → **ZERO**. `python3 scripts/lib/model_version_tripwire.py
src` → **PASS**. ⚠ **`docs/` is outside the tripwire's scope**, so the no-version-string rule was
applied to `docs/v2/ARCHITECTURE.md` **by authorship, not by the gate** — the edited lines name
aliases only.

---

### Phase 6 — Consumer e2e *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim any of
this has been observed on a real install.

**Batched per OQ-4** — after plan 85's baseline wall-clock run, never before it.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **The apply happens, and the pin holds.** Run `/devforge:configure` on testForge20 with
   `think = fable`. **MUST** produce: **(1a)** `.claude/agents/architect.md` carrying
   `model: fable`, and **(1b)** `.claude/agents/security-reviewer.md` carrying `model: opus`.
   **Scored as a PAIR** — an apply that rewrites everything passes 1a and fails 1b; an apply that
   rewrites nothing passes 1b and fails 1a. **Neither is meaningful alone.**
2. **The effort sentinel round-trips.** Configure one tier at effort `default` and another at
   `high`. **MUST** produce: **no `effort:` line at all** on the first tier's agents, and
   `effort: high` on the second's.
3. **An update preserves the choice.** Change an agent BODY in `src/`, run `update.sh` against the
   configured install. **MUST** produce: the body change merged, `model: fable` still present, and
   **the apply summary printed in the run output.** ⚠ **Record whether any agent reported a merge
   conflict** — Phase 3's constraint 2 finding is what this anchor observes in the wild.
4. **A session without Fable degrades cleanly.** Run `/devforge:configure` in a session where the
   `fable` probe fails. **MUST** produce: the probe's one-line report, and **`fable` absent from
   every option list** — with the `Other` pin route still reachable. This is directive (d),
   observed.
5. **The advisory prints.** Run `/devforge:plan`. **MUST** print the PHASE-0 line naming the
   configured think model AND the session model — **or `unknown` for the second half**, which is a
   PASS for this anchor and a finding for D7's bound.
6. **The OQ-1 A/B.** One feature, run twice: `think = opus`, then `think = fable`. Record the
   **wall-clock via `profile_helper`** (plan 70) **as a NUMBER**, plus any known-answer probe
   available in that feature. ⚠ **This is the ONLY evidence that may flip OQ-1's default**, and one
   run of each attributes nothing to any single change.

⚠ **TWO ANCHORS RESTATED 2026-09-04 (plan 94 D2/D3/D6) — score the restated form, not the original,
and the original is kept above so the change is visible.**

- **Anchor 1b** — *"`security-reviewer.md` carrying `model: opus`"* is **no longer the expected
  result**, because the pin is gone (D6 replaced). **It now reads: `security-reviewer.md` carries
  whatever Q11.4 chose**, and on an install where Q11.4 was never answered it carries
  `model: inherit` like any other agent. **Anchors 1a and 1b are still scored as a PAIR** — 1a is
  unchanged.
- **Anchor 3** — the update anchor now also checks the **mapped commands**: after `update.sh`, a
  command in `COMMAND_TIERS` (e.g. `.claude/commands/devforge/plan.md`) must still carry its
  `model:` line **after** the promoted-command re-emit, and the summary line names both classes.
  ⚠ **Its "record whether any agent reported a merge conflict" clause is now the observation of the
  Trap-3 transition and its residual** — see that trap's own dated note.

**Verify:**

- All six anchors are scored **explicitly** — stated, not summarized.
- **Anchors 1a and 1b are scored as a PAIR** (see anchor 1).
- **Anchor 3 records the merge outcome per agent**, not a summary verdict.
- **Anchor 4 diffs the transcript for the string `fable`** — an offered-but-unavailable option is a
  D5 failure, not a nit.
- **Anchor 6 records the wall-clock as a NUMBER even if it is uninteresting** — this plan family's
  numbers do not exist yet (plan 70 Phase 2 is deferred), and OQ-4 exists to keep this one clean.
- **If it fails**, record the negative here with the artifacts and identify which mechanism produced
  it before proposing anything: agents not rewritten is a D1 finding; `security-reviewer` rewritten
  is a D6 finding; a stray `effort:` line is a D4 finding; a reverted model after update is a D1
  `update.sh`-seat finding; an offered-but-undispatchable alias is a D5 finding; a missing advisory
  is a D7 finding. **They have different fixes.**
- **A clean run is NOT evidence that Fable helps this pipeline.** It is evidence the configuration
  path works. **Only anchor 6 speaks to the model question, and one run of each speaks quietly.**

---

## Non-goals

- **Pinning any model version inside `src/`.** D3, enforced by the tripwire test. A consumer may pin
  through `Other`; the framework may not.
- **Validating model × effort compatibility.** D4's bound — that table is the version maintenance
  directive (a) forbids. An unsupported combination fails at dispatch.
- **Setting the orchestrator's model.** ⚠ **CORRECTED 2026-09-03 — this non-goal now rests on a
  DECISION, not on impossibility.** The drafted line read *"Impossible via frontmatter (fact 19),
  not merely declined"*; that verification was wrong, a command CAN carry `model:` / `effort:`, and
  the override is **declined for this plan and deferred to its own decision (OQ-5).**
- **Fable prompt de-prescription.** D8, with a named observed trigger.
- **Per-task or per-agent model routing beyond the single `security-reviewer` pin.** D6. A second
  pin needs its own reason, recorded beside its own agent.
- **Removing the unused `scan` tier.** OQ-3.
- **Any gate, `verify-*` number, or hard-fail validator.** D9 — plan 75's tripwire, both halves.
- **Back-porting into shipped installs.** They arrive via `update.sh` (D1's designed consequence)
  and a re-run of `/devforge:configure`.
- **A cost dashboard, a spend estimate, or any priced claim in emitted text.** `## Model facts`
  stays in this plan.
- **Changing which agents exist, or which tier any agent belongs to.** The census (fact 3) is input,
  not subject.
- **Any change to plan 63's model-invocable counts.** D9 — no frontmatter invocation route changes;
  this plan contributes NO delta and owes no description trim. ⚠ **The counts themselves MOVED on
  2026-09-03 — 13/7 → 16/4 — by plan 93, not by this plan.** The non-goal is unchanged; only the
  number a reader would otherwise carry away is.
- **Repairing `_probe_tier.py`, `init_helper`'s unreachable detector, or any other lane this sweep
  did not touch.** Out of scope by construction.

---

## Dependencies + related

- **`15-AGENT-STANDARDIZATION-PLAN.md`** and `src/agents-AUTHORING.md` — the 19-agent skeleton and
  the meta-block contract **D6 extends** (fact 16). ⚠ **The contract's own text says it is
  *"fixed — author to it, never change it"***, so the extension is a real decision that Phase 0
  ratifies and Phase 2 records with a dated note. **Plan 15's reasoning is not edited.**
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** — the model-invocable carve-out. **Untouched and
  unaffected** (D9). ⚠ **Its standing coordination rule binds: read the counts LIVE at Phase 5,
  never from a remembered delta.** ✅ **Read live 2026-09-03 — and the rule EARNED ITSELF: the
  counts had moved from 13/7 to 16/4 within a day**, via plan 93's removal of the flag from
  `/devforge:grill`, `/devforge:spec-check` and `/devforge:fix`. **This plan's delta is still zero**
  (a `disable-model-invocation` grep over `src/commands/` returns the four setup commands), and
  quoting the remembered figure would have written a false count into four ledger files.
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number / no-new-validator
  tripwire. **Both halves hold** (D9).
- **`89-TEST-FOUNDATION-HARDENING-PLAN.md`** and **`90-E2E-TEST-LANE-PLAN.md`** — the live-count
  reconciliation rule this plan inherits for `configure/main.md` (fact 15), and **plan 89's
  byte-consistency test precedent** that D2 half 1 copies. ⚠ **Plan 89's D6 `regression_gate` note
  lives in a file Phase 2 edits and is UPDATED IN PLACE, never removed.** Plan 90's Phase-1 build
  record is the `FIELD_DEFAULTS`-baseline precedent Phase 1's constraint 1 leans on.
- **`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`** — the profiler Phase 6's anchor 6 uses. Its Phase-2
  real-run diagnosis is deferred, so **no per-command wall-clock number exists in this repo** and
  anchor 6 would be among the first.
- **`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`** — its **D7** established the wall-clock cost-line
  obligation, and its **Phase-5 batching decision** is what OQ-4 orders against. ⚠ **`D7` is an
  overloaded token across this repo — plan 85's D7 is the grill cost line, plan 89's D7 is
  test-meaningfulness, and THIS plan's D7 is the per-command advisory.** Every cross-reference names
  the plan.
- **`81-INFERENCE-RULES-PLAN.md`** — its Phase 7 pins the model `claude-fable-5` while the
  maintainer's session default became Fable 5.1 on 2026-09-03. ⚠ **That confound belongs to plan 81
  and is recorded there when its Phase 7 runs** — this plan neither edits it nor resolves it
  (OQ-4).
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — the English-only rule binding every byte of this plan
  and of everything it emits, and **the predicted-gap-with-no-incident framing** this plan's
  `## Evidence constraint` copies for its directive half.
- **`44-CONSTITUTION-DRIFT-WIRING-PLAN.md`** — its WARN-only update-time drift check is the
  precedent D9's rejected drift-check alternative is measured against. **Cited; not revived.**
- **`48-REVIEW-MANDATORY-GATE-PLAN.md`** — the shelve-until-OBSERVED precedent D8's and D9's
  strengthening triggers both use. **Not revived by this plan.**
- **`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`** — the always-on-trim discipline binding any `src/CLAUDE.md`
  edit at Phase 5, and the reason that file is touched only if it already names tiers.
- **`26-REINTRODUCE-FIX-PLAN.md` / `88-COLD-FIX-BUGS-LANE-PLAN.md`** — the *"extend the one binary,
  never a second composer"* rule D1's alternative (c) is rejected under. **Cited for the stance;
  neither is edited.**

---

## Context for next session

**The one sentence that governs everything here:** a tier's model and effort are CHOSEN at
`/devforge:configure`, WRITTEN into `.claude/agents/*.md` frontmatter by one idempotent helper verb
that runs at configure time and again after every update, expressed as version-free aliases with
pinning available, and RECOMMENDED — never enforced — at the commands where the choice matters.

**Trap 1 — believing the tier knob already works.** It does not: Q11 asks, validates, persists and
renders three answers that **nothing reads** (fact 8), while two shipped comments and one
`DEVELOPMENT-STATUS.md` line describe the override as though it exists (facts 1, 2, 10). **Any
sentence in this build saying "the configured tier model is used" is FALSE until Phase 1's
Deliverable 3 and Phase 3's call both land.**

**Trap 2 — writing a model version into `src/`, in EITHER shape.** The whole point of directive (a)
is that the framework never needs a release to track a model release. **The tripwire test is what
makes that falsifiable, and it asserts TWO patterns** — the API-ID shape `claude-[a-z]+-[0-9]` and
the display-name-with-version shape **`\b(opus|sonnet|haiku|fable)[\s-]+[0-9]`** (widened at build
from `\s+`), case-insensitive. ⚠ **The second is the one that catches real prose**: a rationale
sentence or a `CHANGELOG` line naming `Opus 5`, `Haiku 4.5`, `Fable 5.1` — **or the hyphenated
`sonnet-4-5`, which slipped BOTH drafted patterns until run C1's reviewer caught it** — sails
straight past the first. **Both baselines were clean at drafting time** (fact 18) **and at build**
— so a failing tripwire after this build means THIS build broke it, not that it was always broken.
⚠ **The gate has already fired once on a real instance** (a docstring example in run A); see
`#### Phase 1 build record — Deliverables 1–5`.

**Trap 3 — changing the emitted static default without thinking about `git merge-file`.** The
static default is one side of a three-way merge on every configured install (fact 11). Change it,
and for any consumer whose configured value differs from BOTH the old and the new default, the
`model:` line may conflict — and `update.sh` responds to a conflict by leaving **the entire file
unchanged**, so the agent's BODY update is skipped too. ⚠ **Phase 3's Verify block ANSWERS this
rather than assuming it**; until it runs, treat the static default as something to keep stable.
✅ **ANSWERED 2026-09-03 and the trap is CONFIRMED, not dispelled — it now binds harder.** A
three-way merge of base `opus` / current `fable` / other `sonnet` **conflicts**. Beyond what this
trap predicted: the file's **snapshot refresh is skipped too**, so the staleness **recurs on every
subsequent update**, and the post-merge apply **camouflages it** — `model:` reads correct while the
body is old, and the only signal is the earlier `Merge conflicts in <file>` warn. ⚠ **Treat a static
tier default as effectively FROZEN**: changing one is a migration, not an edit, and the two
candidate repairs are recorded (unbuilt) at `#### Phase 3 build record` item (c).

⚠ **CLOSED BY CONSTRUCTION 2026-09-04 (plan 94 D2), with ONE transition and ONE residual — read all
three clauses or do not cite this note.** **(1) The trap cannot recur**: with the default map gone,
the emitted `model:` line is the constant `inherit` forever, so base and other are always identical
on that line and `git merge-file` keeps the consumer's value. **(2) It fires ONCE, on the release
that removes the default** — base `<old tier default>` / current `<configured>` / other `inherit`
conflicts exactly as this trap predicts — and that transition is mitigated, not endured: plan 94's
second `update.sh` seat runs `apply-models --install-root .devforge/template` **before** the agent
merge loop, so the baseline carries the consumer's own configured value and the merge is clean. **A
three-file `git merge-file` experiment reproduced BOTH sides at plan 94's Phase 1** (the conflict
before, the clean merge after), and a full local `update.sh` reproduction reported zero merge
conflicts. **(3) The residual is WIDER than a hand-edited file**: normalization writes the CURRENT
configuration into the baseline, so **any live agent whose `model:` / `effort:` is stale relative to
`project-config.json` at merge time still conflicts** — a setter run without a following apply, or
an update landing between a configuration edit and the next apply. **The class is narrowed, not
closed**, and the two candidate repairs above stay unbuilt.

**Trap 4 — reading D9's no-gate as a gap to fill.** It is a decision with a named trigger. **A
session that adds `verify-agent-models` because "the other lanes have gates" has left this plan** —
D1's verb is idempotent, so the repair for a disagreement is to run apply, and a gate would only
announce what apply would silently fix.

**Trap 5 — assuming the frontmatter `model:` line always wins.** Two documented environment
variables say otherwise (`### Claude Code authoring surface`). **Omitting `model:` is not
`inherit`** — the resolution order puts `CLAUDE_CODE_SUBAGENT_MODEL` between the frontmatter and
the session model, so an agent with no `model:` line is at the mercy of a variable the framework
does not set and cannot see. **And `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` overrides the frontmatter
outright**, running every subagent on `CLAUDE_CODE_SUBAGENT_MODEL` no matter what D1's verb wrote —
**including D6's `security-reviewer` pin.** ⚠ **A Phase-6 anchor that fails with that variable set
is an ENVIRONMENT finding, not a D1 or D6 finding**, and the framework has no way to tell the
difference for you.

⚠ **And the order itself is VERSION-DEPENDENT — confirmed 2026-09-03 at Phase 1's Step 0.** The
resolution order above is current behavior; **before Claude Code v2.1.251 `CLAUDE_CODE_SUBAGENT_MODEL`
came FIRST and overrode the frontmatter outright.** So **a consumer on an older Claude Code with
that variable set never sees the emitted `model:` line at all** — not the tier value, not the
`security-reviewer` pin — and every agent runs on the variable. **This is a second silent-defeat
path with no version floor anywhere in this plan**: nothing checks the consumer's Claude Code
version, and D1 builds no such check. **Rule out both variables before diagnosing any
"apply didn't work" report.**

**Trap 6 — incrementing the configure counts instead of counting them.** `FIELD_SCHEMA` was 32 and
`_PROJECT_CONFIG_KEY_ORDER` was 40 on 2026-09-03 (fact 14), and D4 moves both. ⚠ **FOUR assertions
pin them, not two** — two for each tuple. Count the live tuples; adding three to a remembered
number produces a differently wrong number.
⚠ **Phase 1 MOVED them on 2026-09-03: `FIELD_SCHEMA` → 35, `_PROJECT_CONFIG_KEY_ORDER` → 43, and
the four pins were renamed to carry the live numbers.** **Those figures are themselves a dated
observation and this trap still binds** — count the tuples, never quote 35/43 from here. ⚠ **The
build also found THREE pre-existing stale counts** in `_render.py`, `_cmds_verify.py` and
`_cmds_set.py` (the last already wrong before this plan existed), which is what this trap predicts
happens when numbers are carried rather than counted.

**Trap 7 — treating the probe as an entitlement check.** D5 observes what **this session's build**
can dispatch (fact 20). It sees no billing plan, no retention policy and no tomorrow. **A green
probe followed by a 400 at dispatch is the documented behavior, not a probe failure.**

**Trap 8 — treating a clean Phase-6 run as evidence that Fable helps.** Anchors 1–5 observe the
configuration path. **Only anchor 6 speaks to the model question**, and one run of each arm
attributes nothing.

**The working tree carries uncommitted work throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather than
released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **The drafting brief named TWO configure count pins; there are FOUR assertions** (fact 14) —
   `test_default_state_has_32_keys` sits immediately after `test_field_schema_has_32_fields`, and
   the 40-key count is asserted twice (`test_all_40_keys_present`, `test_renders_40_keys_with_defaults`).
   **Recorded so Phase 1 does not discover them as a red suite.**
2. **`DEVELOPMENT-STATUS.md:104` carries a THIRD error nobody had named**: its think-tier agent
   enumeration lists three of five (facts 3, 10). **Phase 5 owns it; it is recorded here because a
   fix that corrects only the key names and the claim leaves the third error looking verified.**
3. **The stored Q11 value is a capitalized OPTION LABEL** (`Opus`), while Claude Code's alias is
   lowercase (fact 5). **Today this is inert because nothing reads the value; D1 makes it live**,
   which is why D3's normalization is part of this plan rather than a follow-on.
4. **Claude Code's docs do not document unknown-frontmatter-key handling** — the sub-agents page
   enumerates its fields and says nothing about the rest (`### Claude Code authoring surface`). The
   repo has relied on that tolerance since plan 15 via `applies_to`, and `agents-AUTHORING.md:21`
   states it as fact. **D1's `model_tier:` line inherits a working precedent, not a documented
   guarantee**, and **Phase 1's Step 0 is where that gets asked directly** — before the emitter
   code depends on the answer, not after.
   ✅ **ASKED 2026-09-03 and the finding STANDS UNCHANGED** — the docs still do not document it
   either way. What Step 0 added is the **enumerated skip list**, which lists the conditions under
   which a subagent file is skipped and **does not include an unknown key**. ⚠ **That is evidence,
   not a guarantee**, and this finding remains open exactly as written.

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — twenty-two rows, each checkable
   in under a minute. **If rows 1, 2, 8, 11, 13, 14, 19 or 22 no longer hold, stop and re-derive**:
   they are the defect itself, D1's whole basis, the update-path mechanics, the live counts, the
   frontmatter surface and the question-shape constraints.
2. **Read `scripts/lib/install_defaults.py` and `scripts/generate-agents.py:156`–`:197` before
   touching the emitter.** The two unbuilt-intent comments are what this plan finally makes true,
   and the frontmatter key ORDER is part of every consumer's merge baseline.
3. **Read `update.sh:806`–`:902` in full before Phase 3** — not just the insertion point. The
   `HAS_CONFIG` guard, the substitution skip on exit 2, the snapshot-refresh line and the
   first-write semantics for new agents all constrain where the apply call may sit.
4. **Read `src/devforge/lib/_configure/_schema.py`, `_cmds_set.py`, `_render.py`, `_summary.py` and
   `_cmds_verify.py` before adding the effort fields.** Plan 90's Phase-1 build record names the
   `FIELD_DEFAULTS`-baseline route that avoided an exemption; the same shape is available here
   because `default` is a real enum member.
5. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `CLAUDE_AGENT_DEFAULTS_BY_TIER`, `_claude_tier_model`, `Wizard's Q10a may override per tier`,
   `may OVERWRITE these via key-based regex replacement`, `intentionally NOT enum-restricted`,
   `_PROJECT_CONFIG_KEY_ORDER`, `## Defaults rationale`, `The contract is **fixed**`,
   `Refresh snapshot with new raw`, `## [Unreleased]`.
6. **Invoke the `claude-code-guide` agent before writing or amending any frontmatter — and note
   WHERE that lands: at Phase 1's Step 0, BEFORE the emitter code.** ⚠ **Phase 1 is a Python phase
   that still owes the pass**, because Deliverable 4 changes `emit_claude()` and therefore the
   frontmatter shipped into every consumer's `.claude/agents/*.md`; a phase that skips it on
   "this is Python" has read the file extension instead of the artifact.
   ✅ **RAN 2026-09-03 — all four answers are at `#### Phase 1 build record — Step 0`, and that
   block is what to READ before re-asking anything.** The three questions put were: **(i)** are
   unknown frontmatter keys ignored — **answered NOT DOCUMENTED either way**; **(ii)** is the
   frontmatter key ORDER significant — **answered no, and positions were then chosen and pinned**;
   **(iii)** what does Claude Code do with an `effort:` line on a `haiku`-aliased agent —
   **answered SILENT FALLBACK, which weakened two sentences elsewhere in this plan.** **Phase 2
   CITES those recorded answers and does not re-ask them.** **The pages read are
   `https://code.claude.com/docs/en/sub-agents.md`,
   `https://code.claude.com/docs/en/model-config.md` and
   `https://code.claude.com/docs/en/plugins-reference.md`.** If any answer has changed, D1's
   `model_tier:` route, D4's sentinel and D7's whole premise must be **re-derived, not extended.**
7. **Route every edit through the house loops:** **python-engineer → python-reviewer, test-first**
   for Phases 1 and 3 — **with `claude-code-guide` FIRST in Phase 1** (step 6); **instruction-author
   → instruction-reviewer** for Phases 2, 4 and 5, with **claude-code-guide** added for every
   command-spec, agent-file-frontmatter and `src/CLAUDE.md` edit. **Phases 2 and 4 dispatch no
   python-engineer** — a phase that finds itself needing one has crossed its own boundary and must
   stop. ⚠ **Phase 5's two Python-COMMENT edits are the one exception, and they change no code** —
   a reviewer must be able to see that from the diff.
8. **Every file byte stays English** (plan 87), including this plan and every emitted question,
   option label and advisory line — regardless of any operator response-language setting.
9. **Do not let Phase 1's momentum decide OQ-1.** The think default is `opus` **because nothing has
   measured the alternative**, not because Opus won an argument. **Phase 6's anchor 6 is the only
   thing that may flip it**, and it is batched behind plan 85's baseline run (OQ-4) so that the
   first wall-clock number this plan family ever produces is not confounded at birth.
