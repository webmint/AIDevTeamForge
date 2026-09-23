# 101 — Non-Web Stack Readiness Plan

**Created**: 2026-09-20
**Status**: **Phase 0 NOT closed — nothing below is ratified, and no build phase may start.** Drafted 2026-09-20. No phase is built, no file is edited, and every decision (D1–D8) and open question (OQ-1–OQ-4) is awaiting an outcome. **Phase 5 is a user-driven consumer e2e HARD GATE, DEFERRED and NOT run** — so nothing this plan proposes is consumer-validated, and nothing may later be summarized as if it were.

⚠ **Evidence class, to be repeated in every summary of this plan: NO consumer incident, none claimed, nothing measured.** This is a predicted-gap plan in plan 87's class. **The purpose is a capability, not a port:** the framework should be able to drive Unity work as ongoing work, and the first Unity project it meets is the FIRST CONSUMER and Phase 5's subject — not the reason the plan exists. **No such project exists yet (verified 2026-09-20)**, so Phase 5 is runnable in principle and unrunnable today. ⚠ **A broader purpose is not evidence.** A clean Phase 5 would show the mechanisms behave on planted cases; it would never show that any gap here cost anything.

The framework drives web and backend work well and has never been pointed at a compiled game engine. Four things are proposed, and four more are declined or recorded. Proposed: one config key so a project whose toolchain is measured in minutes is not killed at 120 seconds (D1); one `game-engineer` builder so a game-nature project has a code-writing owner at all, with the reachability and count bookkeeping that makes the agent real rather than an orphan file (D4, D5, D6); and four names in the index walk's skip list so an engine's cache directories never enter the codebase graph (D8). Declined or recorded, each with its reason stated rather than implied: the framework's own gate timeout stays (D2), the regression gate stays structurally disarmed for such projects and says so (D3), and two verified observations — hygiene noise over engine asset files, and the review panel's uncapped changed-file list — are RECORDED with named observation triggers instead of fixed on speculation (D7). ⚠ **The line between D8 and D7 is the plan's whole scope discipline, and it is stated rather than implied: fix what breaks before it can be observed; record what can be observed as it happens.**

---

## Origin & evidence

- **Request.** ONE maintainer request, given 2026-09-20: prepare the framework so it can drive Unity work — **as an ongoing capability, not as one port.** The first Unity project the framework meets is the first consumer and Phase 5's subject; it is not the reason the plan exists.
- **The relay, and what it is worth.** The request reached this plan through a peer Claude session's written briefing. The orchestrator verified every claim in that briefing against the tree on 2026-09-20 and **corrected three of them**: two are recorded as explicit corrections at **F25** (detection is not npm-shaped — `.csproj` is already a first-class manifest) and **F27** (`install.sh` appends only `.devforge/` rules to a target `.gitignore`), and the third is the failure MECHANISM for a game project, which **F17** states: human escalation at assignment time, not the roster gate. ⚠ **Nothing in a relayed briefing is a fact until it is re-derived from the tree.** F1–F32 below are the orchestrator's own reads, not the briefing's.
- ⚠ **Evidence class.** NO consumer incident, none claimed, nothing measured. Predicted-gap plan in plan 87's class. **The purpose is broader than any one project, and a broader purpose is not evidence.** A first real Unity project makes Phase 5 runnable; it does not make anything here observed.
- **Target shape.** A brownfield C# Unity project with decompiled sources: IMGUI, legacy animation, no existing tests, Unity batchmode commands measured in minutes, no browser, no HTTP API. Every fact below is read against that SHAPE, never against a particular project.

### Verified structure (2026-09-20)

Every fact below was checked against the tree on 2026-09-20 by the orchestrator — greps, file reads, and two modules executed for the counts at F10 and F15. ⚠ **Line digits drift — grep the quoted text, never the digits.**

#### What bounds a command today — timeouts

**F1 — The project-toolchain timeout.** `_CMD_TIMEOUT = 120` at `src/devforge/lib/_implement/_cmds_verify.py:157`, applied at `:396`. It bounds EVERY collected type-check, lint, build and test command. The run is `shell=True`, `cwd=source_root`.

**F2 — A timeout is scored as an ordinary failure.** On expiry the function returns `(1, "Command timed out after 120s: <cmd>")` (`:401`). `_is_tooling_unavailable` (`:427-451`) matches ONLY `returncode == 127` or two anchored shell strings — *"command not found"* and *"not recognized as an internal or external command"* — so a timeout matches nothing and **enters the self-repair loop as though the code were broken.**

**F3 — The self-repair cap is helper-owned, and the worst case is bounded by the FIRST failure.** `SELF_REPAIR_CAP = 3` (`:153-154`); the orchestrator cannot extend it. The loop restarts the command list from index 0 on each iteration (`:597`) but **breaks at the first failure** — the `break  # Stop at first failure` line in the same module — so a command that times out is paid for up to **four sequences of the commands that precede it plus itself**, never four times the whole list, before the helper returns `{"status": "failed"}`. ⚠ **At a 1200-second ceiling with one slow command that is roughly 80 minutes**; it approaches several hours only when a second slow command succeeds ahead of the failing one.

**F4 — The repairing agent is told almost nothing.** On a timeout the subprocess output is discarded; the agent receives only the one-line timeout string as `output`. It has no compiler error to repair, and no way to tell "slow" from "broken" from that string.

**F5 — A SECOND, independent timeout.** `_CMD_TIMEOUT = 120` at `src/devforge/lib/_implement/_cmds_gate.py:66`, applied at `:193`. It bounds the framework's OWN `constitute_helper` calls — an argv list, no `shell=True`. A timeout there is converted into a rule **FAILURE with an empty report string** (`:194-196`).

**F6 — The regression gate's timeouts.** `src/devforge/lib/_verify/_regression.py` carries `_WORKTREE_TIMEOUT = 120` (`:104`) and `_TEST_TIMEOUT = 600` (`:107`). The suite it runs is `TEST_COMMANDS[0]` ONLY (`_get_test_command` `:154-171`), executed twice — once at the merge base, once at HEAD.

**F7 — The baseline worktree is never built.** The baseline is a detached `git worktree` in a temp dir. `_symlink_deps` (`:267-287`) symlinks ONLY `node_modules`, `.venv`, `venv` and `vendor` (`_DEP_DIRS` `:113`) and **builds nothing.** A project whose suite needs compiled artifacts therefore fails at the merge base, which lands on `baseline-failing` (`:450-462`) and sets `regression: False` — **the gate reports and never gates.**

**F8 — The e2e lane.** `src/devforge/lib/_verify/_e2e.py` carries `_E2E_TIMEOUT = 1800` (`:146`); the suite runs once at HEAD in `source_root`, never in a worktree. Statuses are `off` / `inconclusive` / `e2e-clean` / `e2e-failing`, and the lane is ADVISORY — no status changes the verdict.

**F9 — No timeout anywhere is config-driven.** A grep over `src/devforge/lib/_configure/` returns zero `TIMEOUT` hits, and a grep over `src/` for a `TIMEOUT` key in any json, md or yaml file returns zero. **Every timeout in the framework is a module-level constant or an inline literal.**

#### The config surface a new key crosses

**F10 — The counts, obtained by EXECUTING the modules on 2026-09-20.** `FIELD_SCHEMA` = 37, `ENUM_FIELDS` = 9, `FIELD_DEFAULTS` = 7, `_PROJECT_CONFIG_KEY_ORDER` = 45. The only field kinds are `scalar`, `string_array` and `package_stack_array` (`_configure/_schema.py:14-17`) — **there is no integer kind**, so a timeout is stored as a string scalar.

**F11 — `FIELD_DEFAULTS` is two mechanisms at once.** It is the legacy-upgrade back-fill (`_configure/_state.py:102-104` fills any `None` field on load) AND the exemption from the null-scalar loop at `_configure/_cmds_verify.py:72-86`. **A new field WITHOUT a `FIELD_DEFAULTS` entry fails `configure_helper verify` on every existing install.** The mechanism is stated in-tree at `_configure/_schema.py:173-175`.

**F12 — The render is a case transposition.** `render-config` maps `configure.yaml` → `project-config.json` by `key.lower()` (`_configure/_render.py:174-190`). The two names must be exact case-transposes, or the field renders `None` and the round-trip check at `_cmds_verify.py:118-133` fails.

**F13 — There is NO shared `project-config.json` reader, deliberately.** 33 files under `src/devforge/lib/` each own a private one. The rationale is in-tree at `_shared/feature_alloc.py:470-480`: *"two independent config readers for two independent keys, so a change to one gate's read path can never silently move the other's."* A new key therefore adds its own read at its one consumer and touches no other reader.

#### Agent installation, the roster and its gate

**F14 — How an agent is kept or dropped, and what the nature vocabulary actually is.** `_decide_agent` (`_configure/_render.py:407-427`) keeps an agent when `applies_to` is None, when it contains `"all"`, or when it intersects `project_natures`. The match is exact Python membership — **case-SENSITIVE, with no normalisation.** ⚠ **The nature vocabulary is ADVISORY, not enum-enforced**, and the tree says so in three places: `_configure/_schema.py` reads *"Vocabulary (advisory, not enum-restricted at setter time): web, backend, mobile, desktop, cli, library, plugin, data, ml, game, infra, docs"*, `_configure/_cmds_set.py`'s `cmd_set_project_natures` reads *"Accepts any non-empty atomic nature strings (no enum restriction — LLM Phase 2 derives from PROJECT_TYPE + FRAMEWORKS; users may name custom natures)"*, and the setter's own `--help` at `_configure/_cli.py:173-178` calls it an *"Advisory vocabulary"*. `project_natures` is a `string_array` and is **NOT in `ENUM_FIELDS`.** So the twelve values are a convention the setter does not police: **any string can be written, and `_decide_agent` still compares it exactly and case-sensitively.** ⚠ **What IS fixed is the writer, not the validator:** `/devforge:configure`'s Phase 2 composition rule at `src/commands/configure/main.md:116` maps `PROJECT_TYPE == "game"` → `game`, so the literal `game` is what a correctly-composed run produces — **and nothing at any layer enforces that it did** (residual 9). ⚠ **A FOURTH site contradicts those three in WORDING, and it is the one a reader lands on first.** `src/commands/configure/main.md:109` — seven lines above the composition rule at `:116`, and the opening of the same `PROJECT_NATURES` bullet — reads *"Closed vocabulary: `web`, `backend`, `mobile`, `desktop`, `cli`, `library`, `plugin`, `data`, `ml`, `game`, `infra`, `docs`"*; a repo-wide grep for `Closed vocabulary` returns that one line in that one file (checked 2026-09-20). **On substance the two are NOT in conflict:** `:109` describes the intended VALUE SET a correctly-composed run writes, the three `_configure/` sites describe ENFORCEMENT, and there is none. ⚠ **But the first word a reader meets is "Closed"**, so anyone sent to this file by the composition rule reads the vocabulary as enum-enforced unless told otherwise — which is why Trap 3 names `:109` explicitly. **Nothing about the decision changes: D4 rests on the composition rule, never on enforcement.**

**F15 — The structural finding, computed by the orchestrator on 2026-09-20** by parsing every `applies_to` in `src/agents/*.md` and applying F14's rule per nature: `web` keeps 4 builders, `backend` 6, `mobile` 3, and **every one of the other NINE natures — desktop, cli, library, plugin, data, ml, game, infra, docs — keeps exactly TWO: `devops-engineer` and `qa-engineer`.** Discounting `infra` (devops-engineer's own domain per the Agent Assignment table) and `docs` (tech-writer, an `["all"]` agent), **SEVEN natures have no code-writing owner at all.** `game` is one of them. ⚠ **This plan fixes ONLY `game`**; the other six stay ownerless by scope, not by oversight.

**F16 — The Agent Assignment table has no engine row.** `src/commands/breakdown/main.md:299-314` carries the table, with no game or engine row. Its not-generated arm (`:320`) routes an absent implementer to *"split or escalate to the human"*, and `:316` forbids falling back to `architect` (*"the architect cannot implement"*).

**F17 — The roster gate is the WRONG mechanism to cite here.** `verify-agent-roster` (PHASE 3.5, `src/commands/breakdown/main.md:560-568`) is a HARD gate, but it fires only when a task assigns an agent that is NOT installed. A game project's real failure mode is F16's human escalation at assignment time, before any task names a missing agent. ⚠ **Do not describe a game project as "hard-blocked by the roster gate" — that is not what happens.**

**F18 — The maintainer reachability gate, and the minimum fix.** `scripts/verify-agent-reachability.py` + `scripts/lib/agent_reachability.py` + `tests/lib/test_agent_reachability.py` was RUN on 2026-09-20 and **PASSES**. A new agent source with no executor path is a type-1 orphan and FAILS it — the live-`src/` test IS the permanent gate. Naming the agent only on a relay line produces a `relay_only` FAIL instead. **The minimum sufficient fix is a row in the Agent Assignment table.** `RELAY_ONLY_ALLOWLIST` is empty and must stay empty.

**F19 — The authoring contract.** `src/agents-AUTHORING.md` governs an agent source: it opens with a fenced ```yaml block (NOT `---` frontmatter); required keys are `name`, `description` and `model_tier` ∈ {think, do, verify, security}; `tools:` appears ONLY on the 6 pure reviewers; a source declares NO `model:`, NO `model_pin` (removed from the contract by plan 94) and NO `effort:`. Body order is fixed: identity line (no heading) → `## Core Expertise` → `## Project Paths` (exactly `{{PROJECT_PATHS}}`) → `## Approach` → [`## Output`] → `## Boundaries & Handoffs` → `## Rules`. ⚠ **A builder's `## Output` is OPTIONAL, never forbidden** — `agents-AUTHORING.md` states it verbatim, *"`## Output` optional (a code-only builder may omit it)"*, against *"`## Output` **mandatory**"* for the 6 pure reviewers — and of the **8 current builders, five omit it and three carry one** (`api-designer`, `migration-engineer`, `qa-engineer`). What is true unconditionally is the narrower statement: **a pure builder produces code rather than findings, so it carries no severity vocabulary and no verdict vocab.** `## Rules` closes with three fixed lines: constitution+memory, minimal scope, and the verbatim grounding rule.

**F20 — Where the roster counts live.** `src/agents-AUTHORING.md:88` carries the ONE numeric roster count (*"The roster is **19** agents … The four families below name **17** of them"*); `:100` reads *"### Builders (8)"*; `:102` is the builder membership list. **No other file under `src/` carries a numeric agent-roster count.** ⚠ **Counts DO appear outside `src/`** — `CHANGELOG.md`, `PLAN-STATUS-ARCHIVE.md` and several plan documents — **and none of them needs this change, nor may any of them be "corrected" by a count sweep**: each is frozen historical prose stating the roster as it stood on that plan's date, not a live claim about the current tree. ⚠ **The repo `CLAUDE.md` is NOT on that list and must not be added back to it:** it carried plan prose until the 2026-09-20 ledger relocation and carries no plan status and no roster digit now. D6's practical conclusion is unchanged: the three sites in `agents-AUTHORING.md` are the whole edit.

**F21 — Nothing hardcodes the roster.** `scripts/generate-agents.py:307` globs `src/agents/*.md`, and `AGENT_LIST` is derived from the on-disk listing at render time. `update.sh:501-517` auto-delivers a new agent source to existing installs. A new file is therefore picked up with no generator edit.

**F22 — The memory-lane gate owes nothing here, with one trap.** `scripts/lib/memory_lane.py` is COMMAND-scoped and never reads `src/agents/`. ⚠ Its Rule 4 sweep DOES walk every file under `src/`, so **the literal `.claude/memory` must not appear in a new agent source.**

#### What the framework does with a project's files

**F23 — Hygiene reads every changed non-skipped file.** `src/devforge/lib/_verify/_hygiene.py`: `_SKIP_EXTENSIONS` (`:299`) = `.md .html .htm .txt .json .yaml .yml .csv .svg .lock`. `_is_code_file` (`:306`) is a DENYLIST that deliberately defaults to scanning (*"prefer false negatives over false positives"*). `:781` calls `readlines()` on every non-skipped changed file with `errors="replace"` and **no size cap and no binary check.** Unity's `.unity`, `.prefab`, `.asset`, `.mat`, `.anim`, `.controller` and `.meta`, and every binary asset extension, are absent from the skip list. Hygiene findings are ADVISORY (plan 34) and changed-files-only.

**F24 — The index walk has no engine-cache exclusions.** `src/devforge/lib/index_helper.py`: `_FILE_WALK_SKIP_DIRS` (`:64`) = node_modules, dist, build, target, out, .git, `__pycache__`, .venv, venv, .idea, .vscode, .next, .nuxt, .turbo, bin, obj. It does **NOT** contain `Library`, `Temp`, `Logs` or `UserSettings`. `_MAX_FILES_PER_PACKAGE = 10000` (`:90`); exceeding it sets `files_truncated: true` and stops the walk. ⚠ **Forward reference: Phase 1b changes the first half of this fact** — D8 adds those four names — so F24 records the tree BEFORE that phase runs, and the cap is untouched by it.

**F25 — A briefing claim CORRECTED: detection is not npm-shaped.** `*.csproj` is a first-class manifest with its own glob pass in `index_helper._detect_manifest` (`:190-209`), and `_generate_docs/_manifest.py:296-300` composes `dotnet build` / `dotnet test` / `dotnet run` for it. **A `.csproj`-bearing project is already detected.** ⚠ **One nuance, a Unity-domain claim from a review and NOT a tree fact:** in Unity, `.csproj` and `.sln` are **generated by the IDE packages when the editor opens the project**, are excluded by the standard Unity `.gitignore`, and embed absolute paths — so a fresh clone may carry no manifest on disk, and a git worktree never carries one. The markers always present in git are `ProjectSettings/ProjectVersion.txt` and `Packages/manifest.json`. **F25's statement stands as written** — a `.csproj`-bearing project is detected — but **whether the file is on disk is not guaranteed**, which D1's fourth rejected alternative depends on.

**F26 — Package selection is operator-correctable.** `packages_detected` is read from `init.yaml` by `index_helper.cmd_build_index` (the `for record in init_state.get("packages_detected", [])` loop) and is populated by the LLM at `/devforge:init-forge`. So F24's truncation risk can be removed with no code change, by declaring packages precisely — **which is what makes it testable rather than certain.**

**F27 — A briefing claim CORRECTED: `install.sh` adds no ecosystem rules.** `install.sh:339-352` appends ONLY the `.devforge/` runtime-state rules to a target project's `.gitignore`, sourced from `src/files/devforge.gitignore`. That template is `.devforge/`-scoped by design and carries no ecosystem rules. **A Unity `.gitignore` is the project's own file**, and adding engine rules to that template would be a category error.

**F31 — The index walk never consults `.gitignore`.** `src/devforge/lib/index_helper.py` names gitignore exactly ONCE, in a comment explaining that dot-files are excluded. `_list_package_files` skips only `_FILE_WALK_SKIP_DIRS` members and directories whose name starts with a dot — **there is no ignore-file read anywhere in the walk.** A gitignored directory is therefore walked in full, however thoroughly the project ignores it, and `Library/` is neither a skip-list member nor dot-prefixed. **This is D8's third reason.**

**F32 — The discovery-gate hook is shipped, fires ONCE, and is extension-blind.** `src/hooks/cbm-code-discovery-gate` is a 14-line `PreToolUse` hook on matcher `Read|Grep|Glob`, wired through `src/settings.template.json` and documented in `src/CLAUDE.md`'s CBM-first Protocol Enforcement table. It keys a gate file on the parent PID, blocks the FIRST matched call of a session with a stderr reminder, and lets every later call through. **It applies no extension filter of any kind.** ⚠ **This REFUTES a briefing suggestion** that non-code extensions should be exempted from it: there is nothing to exempt, because a project with many non-code text files pays exactly ONE block per session, the same as any other project. See the matching non-goal.

#### AC verification with no browser

**F28 — `runtime-assisted` has two channels, and a game has neither.** The `ac_verification_mode` enum (`_configure/_schema.py:156`) is `{code-only, tests, runtime-assisted, off}`. `runtime-assisted`'s only channels are Chrome DevTools MCP and shell `curl`/`fetch` — proved by the agent's tool grant (`src/agents/ac-verifier.md:4`), its channels line (`:15`), its classification table (`:50-52`) and Rule 7 (`:131`). With no browser and no API base, **every `frontend`- and `backend`-classified item reclassifies to `code-fallback` (`:56`), while a `manual`-classified item stays MANUAL either way** (`:52` — *"Cannot automate — report as MANUAL with a reason"*). ⚠ **So the AUTOMATABLE items degrade to code-only behaviour — the MODE does not become `code-only`:** a degraded `runtime-assisted` run still classifies, so it can still emit MANUAL verdicts, and a literal `code-only` run never classifies at all (`:44` — the classification machinery is `runtime-assisted`'s) and therefore never produces one. ⚠ `AC_RUNTIME_CLI_COMMAND` is **NEVER executed by any helper** — it is a string handed to the agent, with no timeout, no lifecycle and no output capture.

**F29 — `tests` mode does not make the AC verifier run tests.** Under `tests` the `ac-verifier` still only code-reads (`ac-verifier.md:38`, `verify/main.md:212`). The real test signal is the orchestrator's independent PHASE 4 `verify-touched` run, whose non-`pass` status blocks APPROVED on its own.

#### The checkout

**F30 — Another session is mid-build in this tree.** At drafting time the working tree carries UNCOMMITTED edits from another session: `src/CLAUDE.md`, `src/commands/constitute/main.md`, `src/commands/constitute/references/section-shapes.md`, `src/commands/summarize/main.md`, plus `CHANGELOG.md`, `README.md`, `VERSION`, `DEVELOPMENT-STATUS.md` and `src/manifest.json`. ⚠ **Every phase of this plan commits BY EXPLICIT PATH and must not sweep those files.** Re-read `git status` before touching any ledger.

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, a recommendation, and the strongest counter-argument, recorded rather than answered away. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D1", "plan 101", "Phase 0").

### D1 — ONE new config key, `command_timeout` / `COMMAND_TIMEOUT`

A string scalar (F10), with a `FIELD_DEFAULTS` entry of `"120"` (F11 — **mandatory**, or every existing install fails `configure_helper verify`), appended LAST to both `FIELD_SCHEMA` and `_PROJECT_CONFIG_KEY_ORDER` per the in-tree byte-stability rule. The two names are exact case-transposes, as F12 requires.

- **Exactly ONE consumer reads it:** `src/devforge/lib/_implement/_cmds_verify.py`, replacing the `_CMD_TIMEOUT` literal at its single use site (F1). The module constant is KEPT as the fallback when the key is absent or unparseable, so a helper invoked outside a configured install behaves exactly as today.
- **Validation lives INSIDE the setter** — a positive-integer check. **Do NOT add a fifth shared validator** to `_validators.py`: one key with one setter does not earn a shared validator, and F13's no-shared-reader rationale applies the same way to writes.
- **The counts move and nothing else does:** `FIELD_SCHEMA` 37 → 38, `FIELD_DEFAULTS` 7 → 8, `_PROJECT_CONFIG_KEY_ORDER` 45 → 46. `ENUM_FIELDS` stays **9** — a string scalar is not an enum. Say so explicitly, so a future session can prove it rather than re-derive it.

**Why.** The ceiling is a property of the project's toolchain, not of a command class. One key, one read site, and with the `"120"` default every existing install's behaviour is **byte-identical**.

**Rejected alternative:** per-class keys (`BUILD_TIMEOUT` / `TEST_TIMEOUT` / …) — three to four times the blast radius, for a distinction no project has asked for.

**Rejected alternative:** a per-package field inside `PACKAGE_STACKS` — the heaviest surface of all (record shape, render, detection prose, every consumer), for a precision no consumer needs yet.

**Rejected alternative:** raise the constant globally with no key — it takes the fast-fail property away from every project to serve one.

**Rejected alternative:** do nothing, and proxy the slow commands. This works for type-check (`dotnet build` on the generated `.csproj` is seconds) and can be made to work for build, but **cannot be made to work for the test command**, which needs the editor in batchmode. ⚠ **It also depends on that `.csproj` being on disk, which is not guaranteed** — F25's review nuance: the file is generated by the IDE packages, excluded by the standard engine `.gitignore`, absent from a fresh clone and never present in a git worktree. **The decision does not change** — the alternative was already rejected on the test command alone — but a future session must not revive it on the assumption that the manifest is always there.

**RECOMMEND D1 as stated.**

**Counter-argument, recorded:** one key means a hung linter in that same project also gets the long ceiling — the fast-fail that 120 seconds buys is spent on every command, not only the slow ones. The plan accepts this because the key is per-project, and a project with a slow toolchain has no fast-fail to lose. Second, **a string scalar holding a number is a type smell the schema forces** (F10). The setter's own check is the only guard, and a value hand-edited into `configure.yaml` bypasses it entirely — at which point the consumer's unparseable-value fallback is what stands between the run and a crash.

### D2 — `_cmds_gate.py`'s own timeout is NOT touched

It bounds the framework's OWN `constitute_helper` subprocesses (F5), not the project's toolchain, so a slow Unity build has no bearing on it. No key reads it, no phase edits it, and its constant stays byte-identical.

**RECOMMEND D2 as stated.**

**Counter-argument, recorded:** F5 also documents a genuine defect — a timeout there becomes a **silent rule FAILURE with an empty report string**, which reads to every downstream consumer as "the rule was checked and it failed" rather than "the check did not finish". That defect is REAL and is **left unfixed here.** It is recorded as a residual with an observed-occurrence trigger, because fixing a second timeout path on speculation is exactly the spending this plan's D7 argues against.

### D3 — the regression gate is NOT re-timed and NOT repaired

For a project whose suite needs a built tree, the gate is **structurally disarmed regardless of any timeout** (F7): the merge-base worktree is never built, the baseline run fails, `baseline-failing` sets `regression: False`, and the gate reports without gating. Raising `_TEST_TIMEOUT` would only make a disarmed gate slower to disarm.

- **The supported disposition is the EXISTING `REGRESSION_GATE=off` key**, which `/devforge:configure`'s Phase 5.1 note already documents as a setter-only change. **Zero code.**
- `_regression.py`'s two constants stay byte-identical.

**RECOMMEND D3 as stated.**

**Counter-argument, recorded:** this leaves such a project with **no regression protection whatever**, and the plan says that plainly rather than implying the gate works. The named strengthening arm — a baseline-preparation command run inside the worktree before the suite — is **NOT built**, and its trigger is an OBSERVED need on a real run, never a predicted one. ⚠ Anyone reading `REGRESSION_GATE=off` as a configuration preference has misread it: it is the honest name for a gate that cannot function here.

### D4 — a new `game-engineer` agent, NOT `unity-engineer`

- **Shape:** `applies_to: ["game"]`, `model_tier: do`, builder shape per F19 — no `tools:` line, no severity vocabulary, `{{PROJECT_PATHS}}` verbatim, and the three fixed closing `## Rules` lines. It **OMITS `## Output` because it is a code-only builder — a CHOICE the contract permits, never a prohibition** (F19: optional for a builder, and three of the eight current builders carry one). `{{FRAMEWORK}}` and `{{LANGUAGE}}` placeholders carry the engine and language in `## Core Expertise`.
- **Why the generic name.** `applies_to` is matched against `project_natures` exactly and case-sensitively (F14), and the documented vocabulary contains `game` and **no engine names** — so a `unity-engineer` would be installed for every Godot and Unreal project too. ⚠ **The vocabulary is advisory rather than enum-enforced (F14), and the decision does not rest on enforcement:** it rests on the documented composition rule at `src/commands/configure/main.md:116`, which maps `PROJECT_TYPE == "game"` → `game`, so a correctly-composed run writes the literal `game` and a generically-named agent is the one that matches it. The house precedent is `frontend-engineer`, which is not `react-engineer` and carries `{{FRAMEWORK}}` rather than a framework name.
- **Why concrete engine guidance is still allowed.** `mobile-engineer` names Xcode, Gradle, iOS and Android inside its `## Approach` while keeping a generic name. So `game-engineer`'s `## Approach` **MAY** state engine-generic obligations — generated asset and metadata files are machine-owned and not hand-edited; scene and prefab serialisation belongs to the engine; headless and batch runs are how verification happens — but **MUST NOT carry a version-specific API migration table**, which would rot inside the framework. Engine-version specifics belong in the consuming project's constitution.

**RECOMMEND D4 as stated.**

**Counter-argument, recorded:** a thinner agent is **less immediately useful** than a Unity-specialised one — the first Unity consumer would get more from a file that named its engine version's actual migration surface. And it pushes the burden of engine knowledge onto the project's constitution, **which nothing in this plan writes, seeds or checks.**

### D5 — reachability: the table row is mandatory, the rest is convention

- **The ONE thing that satisfies the reachability gate is a row in the Agent Assignment table** at `src/commands/breakdown/main.md` (F18). Without it, the new source is a type-1 orphan and `scripts/verify-agent-reachability.py` FAILS. Naming the agent only on a relay line yields a `relay_only` FAIL instead, which is the same failure wearing a different word.
- **Everything else is a consistency edit with no gate behind it, and the plan says so:** the two relay availability lines (`src/commands/breakdown/main.md:247`, `src/commands/plan/main.md:390`), and the convention sites — `src/agents/architect.md`'s specialist roster and its consult row, and the **engineer-deferral lists, each in its OWN phrasing**, in `src/agents/performance-analyst.md`, `src/agents/devops-engineer.md` and `src/agents/design-auditor.md`. ⚠ **No single literal finds all three** (checked 2026-09-20): the first two defer *"to the owning engineer"*, while `design-auditor.md:103` names the engineers directly — *"Defer the actual CSS/markup fix to `frontend-engineer` (web) or `mobile-engineer` (native)"*. A builder who greps one phrase will conclude a file is missing a list it actually has.
- `RELAY_ONLY_ALLOWLIST` stays empty.

**RECOMMEND D5 as stated.**

**Counter-argument, recorded:** adding the row makes the agent **assignable before anything has measured whether it produces usable engine code.** The roster gate checks that a name resolves; it never checks that the agent behind the name is competent, and no phase of this plan measures that either. The first real measurement is Phase 5, and Phase 5 is deferred.

### D6 — `agents-AUTHORING.md`'s counts move

- `:88` — *"The roster is **19** agents"* → 20, and *"name **17** of them"* → 18.
- `:100` — *"### Builders (8)"* → (9).
- `:102` — the builder membership list gains `game-engineer` in alphabetical position.
- **F20 establishes these are the only numeric agent-roster count sites under `src/`**, so no other `src/` file needs the same change. ⚠ **The agent counts OUTSIDE `src/` are deliberately left alone** — `CHANGELOG.md`, `PLAN-STATUS-ARCHIVE.md` and several plan documents state the roster as it stood on their own date, and a sweep that "corrects" them would falsify a historical record (F20).
- **The pure-reviewer count (6), the Actor (1) and the Specials (2) do NOT move.** State that explicitly in the phase record, so a future session can prove it rather than re-derive it.

**RECOMMEND D6 as stated.**

**Counter-argument, recorded:** these counts are **prose that nothing pins mechanically.** F21 shows the roster itself is derived from a glob at render time, so no test, generator or gate ever compares the sentence at `:88` against the directory listing — the sentence went stale before (plan 92 corrected *"17 agents"* to the live 19) and will go stale again the next time an agent lands. This plan moves the digits and adds **no mechanism to keep them moving**; a test that pins the count against the glob is a candidate for a future plan, not this one.

### D7 — hygiene noise and the review panel's file list are RECORDED, not fixed

Both are verified real, and **neither is fixed here**. Both are written up as **hypotheses with named observation triggers**, to be decided from the first real run (Phase 5 anchor 5).

- **Hygiene (F23).** The hypothesis: a changed `.unity`, `.prefab`, `.asset` or `.meta` file is read line-by-line with no size cap and no binary check, producing findings about machine-generated serialisation. It **blocks nothing** — hygiene findings are advisory and changed-files-only. The trigger: hygiene findings observed over engine asset files on a real run.
- **The review panel's input.** F23 covers HYGIENE ONLY. The four-reviewer panel's input and the diff shown at the per-task hard gate are not covered by it: `files_for_finders` in `src/devforge/lib/_shared/feature_scope.py` carries **no size cap and no extension filter**, so the full changed-file list is handed on as-is. The hypothesis: a multi-megabyte engine scene or asset in a task's diff reaches the panel and the gate whole. ⚠ **This is a context-overflow risk — a different CLASS of consequence from advisory noise**, and the plan says so rather than filing it beside hygiene as more of the same. The trigger: the panel's behaviour observed on a task whose diff carries a large engine asset file.

**Why this is the plan's central scope discipline.** This repository carries roughly thirty plans whose own status lines record *"no incident, none claimed, nothing measured"*. **The first real Unity project is the first chance to decide something from evidence instead of prediction**, and spending that chance on a speculative fix would waste it — a fix shipped now can never be shown to have been needed. ⚠ **That argument now covers the two observations above and no longer covers the index walk: the index item was CARVED OUT by an explicit maintainer decision and became D8.** It was not overlooked, and a future reader must not restore it here. D8 states the line the carve-out draws: **fix what breaks before it can be observed; record what can be observed as it happens.**

**RECOMMEND D7 as stated.**

**Counter-argument, recorded:** the two observations are not equal, and treating them alike is the weak point. Hygiene noise is advisory, cheap, and visible the moment it happens — recording it costs a run's worth of noise. **The panel's uncapped file list is not advisory**: if it overflows, the run fails or degrades, and the cost of recording is paid in a broken run rather than in noise. ⚠ The reason it is still recorded rather than fixed is narrow and must not be widened: **its damage IS observable when it happens**, which is exactly what the index item's was not — so the same line that moved the index into D8 leaves this one here. If the first run shows an overflow, that is the evidence that buys the fix, and the fix re-enters at Phase 0 as a new decision.

### D8 — the index walk excludes engine caches

`Library`, `Temp`, `Logs` and `UserSettings` are added to `_FILE_WALK_SKIP_DIRS` in `src/devforge/lib/index_helper.py` (F24). Four names added to one existing constant, and **no other edit in that module** — no new constant, no new parameter, no change to the walk itself.

- ⚠ **The membership test is EXACT.** The walk filters with `d not in _FILE_WALK_SKIP_DIRS`, and **every existing entry is lowercase while the engine's directories are capitalised** — `Library`, not `library`. A lowercase addition would match nothing and **fail silently, looking exactly like a correct change.** The four names go in with the engine's own capitalisation, and Phase 1b's Verify asserts the capitalisation and the skipping behaviour rather than the presence of the word.

**Why now, and not on observation.** The walk runs at `/devforge:init-forge` / index time and feeds `/devforge:generate-docs`, which runs ONCE at setup. A polluted graph poisons every later context read, and **the damage happens BEFORE any run could observe it.** That is the line this plan draws, and it is the whole of what separates D8 from D7: **fix what breaks before it can be observed; record what can be observed as it happens.**

**Second reason — the observation trigger was insufficient.** ⚠ **Unity-domain claim from a review, orchestrator-confirmed, NOT a tree fact:** `Library/PackageCache/` holds thousands of third-party `.cs` files — the sources of the engine's own packages. They enter the graph and `/devforge:generate-docs` **as if they were project code**, and **without necessarily tripping `_MAX_FILES_PER_PACKAGE`** (F24). So `files_truncated: true` — the trigger this plan carried for the index before the carve-out — **can stay false while the damage is done.** A trigger that does not fire on the damage it names is not a trigger.

**Third reason — the walk never consults `.gitignore` (F31).** `index_helper.py` names gitignore once, in a comment about excluding dot-files; `_list_package_files` skips only `_FILE_WALK_SKIP_DIRS` members and dot-prefixed entries. `Library/` is neither, so it is walked **no matter how thoroughly the project ignores it.** The project's own hygiene cannot reach this.

**RECOMMEND D8 as stated.**

**Counter-argument, recorded:** `_FILE_WALK_SKIP_DIRS` is **global and not nature-gated** — the walk runs before `project_natures` exists, so there is no way to apply this to game projects only. **Every project now skips a directory named `Library`, `Temp`, `Logs` or `UserSettings`, including one where such a directory holds real source.** ⚠ The mitigation is **precedent, not argument**: `build`, `bin`, `obj`, `out` and `target` are already in that list and already over-skip on exactly the same terms, so this adds a **known cost rather than a new kind of cost** — a project that keeps source in a directory with one of these names is already unserved by this walk. **F26's operator route still exists** and remains the finer instrument.

### OQ-1 — The default value

- **RECOMMEND `"120"`** — today's behaviour preserved exactly, on every existing install and on every new one that never answers a question about it.
- **Alternative:** a higher default, which would change behaviour for every project to serve one.
- Recorded either way: the default is what F11's back-fill writes into every legacy config on load, so it is not merely a new-install default.

### OQ-2 — Is the key detected, prompted, or default-only?

- **RECOMMEND DEFAULT-ONLY**, on the `regression_gate` precedent documented at `src/commands/configure/main.md:348`. The operator sets it with the setter when their toolchain needs it.
- **This keeps `/devforge:configure`'s arithmetic intact:** the *"24 detection-derived"* and *"12 user-only prompts"* figures do not move, and neither does the populated-field figure; only the schema-count and key-count sentences do. **That is this answer's own reasoning** — a default-only key is emitted without being populated by any phase, so the detected / prompted / populated arithmetic is untouched by construction.
- ⚠ **One sentence changes meaning:** the existing `**One emitted key is set by no phase of this command**` paragraph becomes a **two-key** paragraph. Name both keys there, or the sentence is false the moment this ships. ⚠ **That edit is OWNED BY PHASE 1c**, together with the three other count sentences in the same file — an owner this plan did not have in its first drafting, which is the defect Phase 1c closes. If this OQ is answered any way other than DEFAULT-ONLY, Phase 1c's site list is re-derived from that answer before it is built.
- **Alternative:** a twelfth prompt, which asks every operator of every project about a ceiling almost none of them need.

### OQ-3 — Should `/devforge:configure` detect a slow toolchain and propose a higher value?

- **RECOMMEND NO for v1.** Detection with no evidence of the right value is a guess, and the operator can make that guess better than a heuristic can — they have run the build.
- **Alternative:** time a probe command at configure time and propose a multiple of it. Recorded as a named strengthening arm; its trigger is an observed run where the operator could not pick a value.

### OQ-4 — Should the new agent be named in the perf and accessibility rows of the Agent Assignment table?

- **RECOMMEND NO.** Those rows have their own owners, and adding a third name to each widens the assignment surface for a benefit nothing has asked for. The engine-code row is what F18 requires; the others are not.
- **Alternative:** name it in the perf row, on the argument that engine performance work is engine work. Recorded, not taken.

---

## Phases

### Phase 0 — Ratification

No code. Every decision (D1–D8) and every open question (OQ-1–OQ-4) gets an outcome in a `## Phase 0 close record`: ratified, amended or declined.

#### Verify

- The record names **each** of D1–D8 and OQ-1–OQ-4 with its outcome. No item is silently omitted.
- The record states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation (plan 98's D1 distinction).
- **Each decision still carries its counter-argument.** A ratified decision with its counter-argument deleted cannot be re-opened honestly.
- The record says which files the outcomes put in scope: **OQ-2 decides whether a twelfth prompt joins `/devforge:configure`'s Phase 4 question set, or whether Phase 1c edits only that command spec's count sentences**, **OQ-4 decides whether Phase 2 touches two more Agent Assignment rows**, and **D8 decides whether Phase 1b exists at all** — declined, Phase 1b is not built and Phase 5 anchor 5(a) reverts from a scored verification to an observation, ⚠ **and `docs/v2/ARCHITECTURE.md:81` stays byte-identical, since Phase 1b is the only phase that falsifies it** (Phase 4).
- ⚠ **D1 decides whether Phase 1c exists at all.** Phase 1c edits only sentences that D1's count move falsifies, so D1 declined means Phase 1c is not built; **D1 ratified means Phase 1c is mandatory, because the four sentences it owns go false the moment Phase 1 lands.**
- ⚠ After a blanket close, **check each ratified item against the per-phase lists BY NAME, never against a range** — plan 100's Phase-4 record states why: a range reads as complete while the enumeration beside it drops a member, and an item with no Verify line cannot fail.

### Phase 1 — Python: the `command_timeout` field

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path (F30).

**The seven files.** Six under `src/devforge/lib/_configure/`, plus the one consumer:

- `_schema.py` — the `FIELD_SCHEMA` entry (scalar, appended last) and the `FIELD_DEFAULTS` entry `"120"` (F11).
- `_cmds_set.py` — the setter, carrying the positive-integer check (D1). No shared validator is added.
- `_cli.py` — the import and the subparser.
- `_render.py` — `_PROJECT_CONFIG_KEY_ORDER` (appended last) and **its two count comments, named so neither is missed:** `:15` (*"# 37 from configure.yaml (FIELD_SCHEMA, uppercased) +"*) and `:19` (*"# Total: 45 keys."*). ⚠ Both belong to THIS phase, not to the Phase 4 docs sweep — they sit in a file this phase already edits.
- `_summary.py` — **display-group membership.** ⚠ A field in no group is **silently absent** from the Phase 7 report the user reads, which is the failure that looks like success. It joins an existing group rather than opening a new single-field one, on plan 90's recorded precedent.
- `_cmds_verify.py` — **the two "37" comments** and the defaults-exemption sentence.
- `src/devforge/lib/_implement/_cmds_verify.py` — the consumer read, replacing the `_CMD_TIMEOUT` literal at its single use site (F1), with the module constant kept as the fallback.

**Files that need NO edit, and why — record each as a verified no-op:**

- `_cmds_render.py` — the mapping is **derived** (`key.lower()`, F12), so the verb needs no per-field edit.
- `_state.py` — **generic loops**; the back-fill walks `FIELD_DEFAULTS` and needs no new branch.
- `_yaml.py` — **generic loops**; it reads and writes whatever keys exist.
- `configure_helper.py` — **constant re-exports** only.
- `scripts/post-update-checks.sh` — it **shells out** to the Python it does not duplicate.

**Tests — all three are mandatory:**

- `tests/lib/_configure/test_substitute_file.py`'s `minimal_config` guard — an existing **schema-drift guard that hard-fails on any new key.**
- `tests/scripts/test_post_update_checks.py`'s `_LEGACY_MISSING_KEYS` — the second such guard.
- A **new per-plan test file under `tests/lib/_configure/`** for the setter, the render round-trip and the consumer's fallback.

#### Verify

- **Legacy install:** `configure_helper verify` passes against a `configure.yaml` written BEFORE this change, with no setter call — the `FIELD_DEFAULTS` back-fill supplies the value (F11). A test pins it.
- **Round-trip:** the setter → `configure.yaml` → `render-config` → `project-config.json` carries `COMMAND_TIMEOUT` at the **last** position, and `_cmds_verify.py`'s round-trip check passes (F12).
- **Setter validation:** a non-integer, a zero and a negative value each exit 2 with a named message; a positive integer succeeds.
- **Consumer:** with the key present the collected commands are bounded by its value; with the key **absent** and with the key **unparseable**, the module constant applies. A test pins all three.
- **Counts:** `FIELD_SCHEMA` 38, `FIELD_DEFAULTS` 8, `_PROJECT_CONFIG_KEY_ORDER` 46, `ENUM_FIELDS` **9, unchanged**. Every count comment in `_render.py` and `_cmds_verify.py` matches, verified by executing the modules rather than by reading the comments.
- **Untouched, and each for its OWN reason** — `git diff` is **empty** on all three: `src/devforge/lib/_implement/_cmds_gate.py` (D2), `src/devforge/lib/_verify/_regression.py` (D3), and `src/devforge/lib/_verify/_e2e.py` (**out of scope — no decision touches it at all; F8 is the only place in this plan it is discussed**). ⚠ Do not attribute `_e2e.py` to D2, D3 or D7: none of them mentions it.
- **No second literal:** a grep for a new `TIMEOUT` constant or literal anywhere outside the one consumer read returns nothing (F9 is the baseline it is measured against).
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 1b — Python: the index walk exclusion

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path (F30). **Lettered because it is a second, independent Python change** with its own file and its own Verify — the house precedent is plan 100's 1a / 1b / 3a / 3b / 3c. It depends on nothing in Phase 1, and Phase 1 depends on nothing here.

- `src/devforge/lib/index_helper.py` — `Library`, `Temp`, `Logs` and `UserSettings` added to `_FILE_WALK_SKIP_DIRS` (D8), **with the engine's own capitalisation.** Nothing else in the module is touched.
- A test that walks a tree containing all four directories, placed with the module's existing coverage under `tests/lib/`.

#### Verify

- **Capitalisation, ASSERTED and not assumed:** the four names are present as `Library`, `Temp`, `Logs` and `UserSettings`. ⚠ **A lowercase entry matches nothing** and fails silently (D8), so the test asserts the exact strings AND a walk that actually skips those directories — never a lowercase membership check.
- **A walk over a tree containing all four** returns no path under any of them **and still returns the files outside them** — both halves, because an exclusion that skipped everything would pass the first half alone.
- **`_MAX_FILES_PER_PACKAGE` and every other constant in `index_helper.py` are byte-unchanged:** a `git diff` on the module shows the four added names and nothing else.
- **The index shape does not move:** `files_truncated` keeps its meaning and its cap — D8 removes what inflates the count, it does not change what the count is measured against (F24).
- ⚠ **The constant-NAME sweep is run here and its result handed to Phase 4.** Grepping `_FILE_WALK_SKIP_DIRS` across `docs/` and `src/` is a different sweep from any count grep (Trap 21), and it reaches one live doc that enumerates this constant's members — `docs/v2/ARCHITECTURE.md:81`, which **Phase 4 edits, not this phase.** This phase records that the sweep was run and what it returned; a `git diff` for this phase shows `index_helper.py` and its test file only.
- ⚠ **A VERIFIED FACT this phase must record rather than re-derive: `_FILE_WALK_SKIP_DIRS` is pinned by NO existing test.** A grep for the constant's name over `tests/` returns **nothing**, and this repo contains no directory named `Library`, `Temp`, `Logs` or `UserSettings` for a walk test to collide with. Two consequences, both binding on this phase: **(1) the test above is WRITTEN, never amended** — there is no existing assertion to extend, so a builder who goes looking for one and finds nothing has confirmed this fact rather than missed a file; **(2) the list is currently UNGUARDED** — a future edit could drop `node_modules` or `.git` from it and no test would fail. This phase's new test closes that gap **for the four names it adds and for nothing else**; the pre-existing sixteen stay unpinned, and pinning them is not in this plan's scope.
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 1c — instruction: the `/devforge:configure` spec's count sentences

**Route: instruction-author → instruction-reviewer.** ⚠ **This phase is INSTRUCTION-ONLY — it writes no Python and touches no helper module**, so the tripwire *"Python is confined to Phases 1 and 1b"* stays TRUE with this phase in the plan. It is lettered rather than numbered because it is the prose half of Phase 1's count move, and it must land in the same working session as Phase 1: until it does, the command spec states counts that Phase 1 has already falsified. Commit by explicit path (F30).

**The one file: `src/commands/configure/main.md`. FOUR sentences move, and six that look similar do NOT.**

- `:13` — *"canonical state (37 fields)"* → **38**.
- `:14` — *"(45 keys: 37 from configure.yaml + 5 from init.yaml + 3 derived)"* → **46 keys: 38 from configure.yaml**; the `5` and the `3` are untouched.
- `:348` — the whole `**One emitted key is set by no phase of this command: `regression_gate`.**` paragraph becomes a **TWO-key** paragraph naming both keys, and its *"The schema carries 37 fields"* clause → **38**. ⚠ This is the sentence OQ-2 warns about; it is false the moment Phase 1 lands.
- `:538` — *"`.devforge/project-config.json` carries all 45 keys"* → **46**. ⚠ **The same line also says *"The 36 configuration fields are persisted"* — that clause does NOT move.**

**Six sentences that do NOT move — record each as a verified no-op, so no builder "helpfully" bumps them:** `:9` (*"fills 36 configuration fields"*), `:95` / `:155` (*"24 detection-derived values"*), `:207` (⚠ **the same 24 in DIFFERENT words** — *"apply all 24 Phase 2 values via setters"*, checked 2026-09-20), `:283` (*"These twelve fields"*), `:335` (*"fully populated (36 fields set)"*). ⚠ **The reason is OQ-2's own answer:** a DEFAULT-ONLY key is emitted without any phase populating it, so the populated / detected / prompted arithmetic is unchanged by construction. **If OQ-2 is answered any other way, this list is re-derived before the phase is built.**

#### Verify

- **The four moved sentences each read the new digit**, quoted and checked one at a time: `38 fields` at `:13`; `46 keys: 38 from configure.yaml` at `:14`; a two-key paragraph naming both keys plus `38 fields` at `:348`; `all 46 keys` at `:538`.
- **The six unmoved sentences are byte-identical**, each checked by its own quoted text: *"fills 36 configuration fields"*; the two *"24 detection-derived values"* sites at `:95` and `:155`; ⚠ **`:207` checked by ITS OWN text — *"apply all 24 Phase 2 values via setters"*** — because the third `24` site does not carry the other two's phrasing (checked 2026-09-20), so one quoted literal cannot check all three, and **grepping the bare digit `24` is weaker rather than a substitute**; *"These twelve fields"*; *"fully populated (36 fields set)"* — and, on `:538`, *"The 36 configuration fields are persisted"*.
- ⚠ **A grep for one phrase under-reports this file.** `grep -n "37 fields"` finds `:13` and `:348` and misses `:14` and `:538`, which say `45 keys`. Grep `37 fields`, `45 keys` and `36 ` separately and classify every hit as moved or unmoved. ⚠ **The three `24` sites need their own pass for the same reason — one number, two phrasings** (`:95` / `:155` against `:207`).
- **The paragraph at `:348` still states the setter route** for `regression_gate` and still forbids adding a prompt for it — this phase adds a second key to that paragraph and **removes nothing from it**.
- `git diff --stat` shows **exactly one file** changed by this phase.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — the `game-engineer` agent

**Route: instruction-author → instruction-reviewer.** ⚠ **Invoke `claude-code-guide` before writing the source** — an agent source becomes a file in a target project's `.claude/agents/`, which is the repo's standing rule for every Claude-Code-integration surface. Commit by explicit path (F30).

- `src/agents/game-engineer.md` — the new source, in F19's builder shape.
- `src/commands/breakdown/main.md` — **the Agent Assignment row** (D5, the only gate-satisfying edit) and the relay availability line.
- `src/commands/plan/main.md` — the relay availability line.
- `src/agents-AUTHORING.md` — the three count sites (D6).

#### Verify

- **RUN `python3 scripts/verify-agent-reachability.py` — expect PASS.** A `relay_only` result means the table row is missing or mis-shaped (F18).
- **RUN `python3 -m pytest tests/lib/test_agent_reachability.py tests/lib/test_memory_lane.py`** — both green.
- **RUN `python3 scripts/generate-agents.py --src src/agents --target <scratch>`** — the new agent renders, and the scratch output is inspected rather than assumed (F21).
- **Shape:** the source opens with a fenced ```yaml block, carries `name`, `description` and `model_tier: do`, and carries **no `model:`, no `model_pin`, no `effort:` and no `tools:`** (F19). `## Project Paths` is exactly `{{PROJECT_PATHS}}`. `## Rules` closes with the three fixed lines.
- **`## Output` is ABSENT — as a choice, not as a rule.** The agent is a code-only builder and omits it (D4). ⚠ **Do not score this as a prohibition:** `## Output` is optional for a builder and three of the eight current builders carry one (F19), so a Verify that rejected the section outright would be asserting a contract the tree does not have.
- **Nature match:** `applies_to: ["game"]` — exactly that spelling, lowercase. The match is case-sensitive membership (F14), and ⚠ **the vocabulary is advisory rather than enum-enforced**, so nothing rejects a misspelling at any layer — the spelling is asserted here because no mechanism asserts it anywhere else.
- ⚠ **`grep -n "\.claude/memory" src/agents/game-engineer.md` returns nothing** (F22).
- **No version-specific API migration table** appears anywhere in the source (D4).
- **Counts:** `src/agents-AUTHORING.md` reads 20 / 18 / Builders (9), with `game-engineer` in alphabetical position in the membership list; **the pure-reviewer count (6), the Actor (1) and the Specials (2) are byte-identical**, recorded explicitly.
- `grep -rn "unity-engineer" src/` returns nothing.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — convention sites

**Route: instruction-author → instruction-reviewer.** Consistency edits with **no gate behind them** (D5) — the plan says so rather than implying a mechanism.

- `src/agents/architect.md` — the specialist roster and the consult row.
- `src/agents/performance-analyst.md`, `src/agents/devops-engineer.md`, `src/agents/design-auditor.md` — the engineer-deferral lists, **each in its own phrasing** (D5): the first two say *"to the owning engineer"*, `design-auditor.md:103` names `frontend-engineer` and `mobile-engineer` directly. **Read each file; do not grep one literal.**

#### Verify

- `grep -rn "game-engineer" src/agents src/commands` returns the Phase 2 sites plus exactly these four files, and no others.
- **Nothing in this phase is load-bearing:** `python3 scripts/verify-agent-reachability.py` still PASSES, and it passed before this phase ran — which is the point. Record that it was already satisfied by Phase 2.
- No file in this phase **gains** a severity vocabulary, an `## Output` section or a `tools:` line. ⚠ **`performance-analyst.md` and `design-auditor.md` are pure reviewers that already carry all three** — the assertion is that this phase ADDS none, never that these files have none.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Apply F30 before touching any ledger: re-read `git status`, read each ledger LIVE, and commit BY EXPLICIT PATH — another session's uncommitted edits sit in this tree and must not be swept in.**

- **`CHANGELOG.md`** — a new entry under `## [Unreleased]`, with **the evidence class FIRST and the honest bounds LAST**. ⚠ **`CHANGELOG.md:40` is an explicit DO-NOT-TOUCH.** It sits inside a released version section (plan 94's entry) and reads *"the schema is 37 fields, the render map 45 keys, the enum set 9"* — **frozen historical record**, a statement of what was counted live on that plan's date, not a live claim about the current tree. A count sweep that "corrects" it falsifies the record. **This is the same reasoning F20 applies to the agent counts outside `src/`.**
- **`DEVELOPMENT-STATUS.md`** — the config-surface and roster-count sites, each an edit or a recorded verified no-op. ⚠ **This file is LIVE status prose, not a frozen record** — F20's reasoning and the `CHANGELOG.md:40` exclusion do NOT extend to it, and plan 92 edited a stale count here. Read it live and classify each hit.
- **`docs/v2/ARCHITECTURE.md`** — **EIGHT sites falsified by Phase 1's count move**, named individually because no single grep finds them all:
  - `:260` — *"fills 36 of 37 configuration fields"* → `36 of 38`, **and** *"(45-key substitution map)"* → `46-key`. **Two moves on one line.**
  - `:279` — *"| Render | `render-config` | Atomic JSON write of project-config.json (45 keys) |"* → `46 keys`.
  - `:286` — *"Schema: `FIELD_SCHEMA` carries 37 fields"* → `38 fields`. ⚠ **The SAME line reads *"`ENUM_FIELDS` carries 9 entries"* and names the nine — that half does NOT move**, because D1's key is a plain string scalar that never joins `ENUM_FIELDS`. Bumping it to 10 would be a new falsehood introduced by the fix.
  - `:324` — *"verify cross-checks 37-field configure.yaml + 45-key"* → `38-field` **and** `46-key`. **Two moves on one line.**
  - `:331` — the section heading *"### 4.3 Field-source map (37 configure.yaml + 5 init.yaml + 3 derived = 45 project-config.json keys)"* → `38 configure.yaml` **and** `46 project-config.json keys`. **Two moves on one line**; the `5` and the `3` are untouched. ⚠ **No value pattern in the list below reaches this line** — it spells the counts as `37 configure.yaml` and `45 project-config.json keys`, so `45-key`, `45 keys`, `37-field` and `37 fields` all miss it. It is found by `Field-source map`.
  - `:369` — *"| (A) Direct project-config.json keys | 12 | Verbatim from the 45-key map |"* → `46-key`. ⚠ **The `12` on that row is a different quantity — direct keys — and does NOT move.**
  - `:388` — *"configure.yaml            # canonical 37-field state — single source of truth"* → `38-field`.
  - `:390` — *"project-config.json       # 45-key render artifact (regenerated each run)"* → `46-key`.
  - ⚠ **Why a naive grep under-reports this file, stated so the builder does not trust one pattern.** Pattern by pattern, checked against the tree on 2026-09-20: the `36 of 37` phrasing matches **`:260` alone**; `45-key` matches `:260`, `:324`, `:369` and `:390`; `45 keys` matches **`:279` alone**; `37-field` matches `:324` and `:388`; `37 fields` matches **`:286` alone**; and `Field-source map` matches **`:331` alone**. ⚠ **The four VALUE patterns run together return exactly seven lines — `:260`, `:279`, `:286`, `:324`, `:369`, `:388`, `:390` — and NOT `:331`**, whose own phrasing none of them contains. **No single pattern reaches all eight.** Grep `45-key`, `45 keys`, `37-field`, `37 fields` **and `Field-source map`** **separately — FIVE patterns, not four — and their union is exactly the eight**; classify every hit, and note that two sites are double-counted across the value patterns (`:260` and `:324` each carry two moves). ⚠ **Run that fifth pattern scoped to this file:** repo-wide it also matches `done-plans/CONFIGURE-PLAN.md:129`, an archived plan that is never edited (Trap 18's class).
  - ⚠ **Why plan 92's precedent does NOT cover this file.** Plan 92 deliberately left `docs/v2/ARCHITECTURE.md`'s *pre-existing* stale counts alone as a separate item — and that carve-out covers counts plan 92 did not cause. **These eight are falsified by THIS plan's own Phase 1, so they are this plan's to fix**, and leaving them is not the plan-92 precedent being followed.
- **`docs/v2/ARCHITECTURE.md:81` — a SECOND, INDEPENDENT falsification in the same file, and a DIFFERENT PHASE causes it.** ⚠ **It is kept apart from the count bullet above on purpose: the eight count sites are falsified by Phase 1; `:81` is falsified by Phase 1b.** A builder who does not run Phase 1b leaves `:81` byte-identical; a builder who runs Phase 1b edits `:81` even if Phase 1 never ran.
  - The line enumerates the MEMBERS of a constant in prose — *"Skip dirs: `_FILE_WALK_SKIP_DIRS` (`node_modules`, `dist`, `build`, `target`, `out`, `.git`, `__pycache__`, `.venv`, `venv`, `.idea`, `.vscode`, `.next`, `.nuxt`, `.turbo`, `bin`, `obj`) plus any dot-prefixed directory."* — the same sixteen names F24 records. Phase 1b appends four, so this line **under-reports the live constant by four names the moment Phase 1b lands.**
  - **The four names go into that prose in the engine's own capitalisation** — `Library`, `Temp`, `Logs`, `UserSettings` — matching the constant exactly, per D8's capitalisation discipline (Trap 15). A lowercase name in the doc would describe a constant the tree does not have.
  - ⚠ **This is the ONLY file outside `index_helper.py` that enumerates this constant's membership** — checked 2026-09-20 by grepping the constant's NAME across the repo, which returns `src/devforge/lib/index_helper.py` (the definition plus a docstring and the walk's use), `docs/v2/ARCHITECTURE.md:81`, and this plan file, and nothing else. **No count grep reaches this site**, which is the new Trap 21's worked example.
- **`PLAN-STATUS-ARCHIVE.md`'s `## Index` section** — this plan's INDEX entry in the "Currently active" list there, and it is **ONE LINE — a hard size constraint, not a style preference.** ⚠ That section's own preamble records why; read it LIVE, and as it stood on 2026-09-20 it reads: *"One line per plan, in execution order — the scannable view of the `## Entries` below; each entry there is the full record and stays the authority. Relocated from `CLAUDE.md` on 2026-09-20, which no longer names this file at all: that file is the framework's development instructions, not its history. When a plan's status changes, amend BOTH its line here and its entry below."* ⚠ **The repo `CLAUDE.md` gets NOTHING — no index line, and no mention of the archive either.** That relocation ran on 2026-09-20, the day this plan was drafted, and it took every plan line and the archive pointer out of that file deliberately; **a line added back there is not a fuller record, it is a reversal.**
- ⚠ **The SPLIT is explicit, and it now lives inside ONE FILE: ONE LINE in `PLAN-STATUS-ARCHIVE.md`'s `## Index`, the FULL record in that same file's `## Entries`.** Every sentence of status beyond that one line goes to the `## Entries` entry and nowhere else. **The two must still AGREE** — the split does not weaken the sync this phase's Verify already requires: the index line is a true summary of the `## Entries` entry, never a different claim and never a shorter competing one.
- **`PLAN-STATUS-ARCHIVE.md`'s `## Entries` section** — this plan's full status entry, and **`## Entries` is the authority**; the `## Index` line above it summarizes this entry and never replaces it. **The convention is actively practised, not merely documented:** a grep for plan-numbered entries there returns **one for every plan from 90 through 100, with no gap** — so a plan that writes only the index line is the odd one out, not the norm. ⚠ **Two sites, one status** — writing one and not the other is exactly the drift the archive's own text names when it says to *"amend BOTH its line here and its entry below."*

#### Verify

- Every site above is recorded as an **EDIT or an explicit VERIFIED NO-OP**, with the grep that shows it.
- ⚠ **All EIGHT `docs/v2/ARCHITECTURE.md` count sites are recorded as EDITS — `:260`, `:279`, `:286`, `:324`, `:331`, `:369`, `:388`, `:390` — each named individually.** A record that names fewer than eight has missed one; a record that names a range rather than the eight digits cannot show which. **FIVE separate greps back the record** (`45-key`, `45 keys`, `37-field`, `37 fields` **and `Field-source map`**) — ⚠ **the first four return exactly seven lines and never `:331`; the fifth is the one that reaches it** — **their union is exactly the eight**, and every hit each one returns is classified.
- ⚠ **`docs/v2/ARCHITECTURE.md:81` is recorded SEPARATELY from those eight, and against a DIFFERENT phase.** If Phase 1b ran, `:81` is an EDIT whose prose carries `Library`, `Temp`, `Logs` and `UserSettings` in that capitalisation; if Phase 1b did not run (D8 declined), `:81` is a recorded VERIFIED NO-OP. Either way the lines around it in that section are **byte-identical** — this phase edits `:81` and no neighbour. ⚠ **No count grep finds this site**: it is found by grepping `_FILE_WALK_SKIP_DIRS`, run as its own sweep (Trap 21).
- **Two NO-MOVES inside that file are recorded explicitly:** `ENUM_FIELDS` still reads **9 entries** at `:286`, and the direct-keys `12` still reads **12** at `:369`. Both are byte-identical after this phase.
- **`CHANGELOG.md:40` is byte-identical** — recorded as a deliberate exclusion with its reason (frozen released record), never as a site that was missed.
- **No agent-roster count outside `src/` was edited** (F20): `CHANGELOG.md` and `PLAN-STATUS-ARCHIVE.md` keep every roster digit they carried. ⚠ `DEVELOPMENT-STATUS.md` is the exception and is classified on its own terms — live status prose, edited or recorded as a no-op, never waved through under this rule.
- `grep -rn "101-NON-WEB" --include=*.md .` returns the ledger sites plus this file.
- **No ledger line claims more than the build supports:** *"built and build-verified"* is the ceiling, and **Phase 5 is named as DEFERRED and NOT run** in every line written.
- Every summary written in this phase **repeats the evidence class**: no consumer incident, none claimed, nothing measured.
- **The `## Index` entry is ONE LINE.** `git diff` on `PLAN-STATUS-ARCHIVE.md` shows exactly one line added to the "Currently active" list under `## Index`, this plan's entry added under `## Entries`, and nothing else moved. ⚠ **A multi-paragraph entry under `## Index` is a FAILURE of this phase, not a fuller record** — the fuller record is the `## Entries` entry, and a multi-paragraph line destroys the scannable view the index exists to be. ⚠ **The repo `CLAUDE.md` is byte-identical after this phase** — no index line there, and no pointer to the archive either.
- **The `## Entries` entry and the one-line `## Index` entry AGREE with each other** — same phase states, same deferral, same evidence class. Quote one against the other rather than writing each from memory; the archive's own text demands the sync (*"amend BOTH its line here and its entry below"*), and nothing mechanical checks it.
- ⚠ **No tracked file this sweep writes names a consumer path or a specific product** — not a client, a client component, a client ticket, a benchmark path, a directory or a named project. The subject is Unity work as a capability, and that is how the ledgers name it. ⚠ **This plan file names no consumer path and no specific product either**, so a ledger line that named one would be the first in the set.
- `git status` after the commit shows the other session's files **still uncommitted and unmodified by this phase**.

### Phase 5 — Consumer e2e on the first real Unity project — user-driven HARD GATE, DEFERRED, NOT run

**Everything above is build-verified at best, never consumer-validated, until this phase runs.** ⚠ **No such project exists yet (verified 2026-09-20)**, so this phase cannot run until the framework meets one. **The frozen benchmark install is never touched.**

The anchors are known-answer cases. **Anchors 1 and 2 are scored as a PAIR.**

1. **A Unity command that exceeds 120 s completes under the configured timeout** — and **record the measured wall-clock as a NUMBER**. Without the number this anchor proves only that nothing crashed. **PAIRED WITH 2.**
2. **A genuinely failing command still fails and still enters self-repair** — and **record the measured wall-clock of the FAILING run as a NUMBER too.** Without it the pair cannot show that the ceiling bounds a failure as well as a success, which is half of what the pair exists to show. Paired with 1, because **a timeout raised without bound would pass 1 and fail 2**, and a run that only scores 1 cannot tell the two apart. ⚠ **The worst case is 4 × (the commands that succeed before the failing one, plus the failing one)** — the loop breaks at the first failure (F3) — so at a 1200-second ceiling with one slow command it is roughly 80 minutes, and it approaches several hours only when a second slow command succeeds ahead of the failing one.
3. **Two anchors, deliberately SPLIT — installation and assignment are different failures with different fixes.**
   - **(a) INSTALLATION:** after `/devforge:configure`, `.devforge/configure.yaml`'s `project_natures` contains the literal `game`, **and** `game-engineer.md` survives `prune-agents` and is present in `.claude/agents/`. **Record the `project_natures` value as a STRING**, not as "correct".
   - **(b) ASSIGNMENT:** `/devforge:breakdown` on a C# task assigns `game-engineer`, and `verify-agent-roster` exits 0.
   - ⚠ **Why they are split:** an unsplit anchor cannot tell **"never installed"** — the advisory-vocabulary residual, where an off-list nature string silently drops the agent (F14, residual 9) — from **"installed but not assigned"**, which is D5's table row. A single failing anchor would point at both and fix neither. Splitting them makes the failure name its own mechanism.
4. **A non-game project's `project-config.json` differs only by the new key at its appended position** — a byte diff against the pre-change render, with the new key the only difference.
5. **One verification and two observations — do not score them alike.**
   - **(a) SCORED pass/fail — D8's known-answer case:** `index.json` contains **no path under `Library/`, `Temp/`, `Logs/` or `UserSettings/`**. This is a VERIFICATION, not an observation: D8 shipped the exclusion at Phase 1b, so a path under any of those four is a **failure of Phase 1b**, not evidence for a future decision.
   - **(b) RECORD ONLY:** whether hygiene flagged engine asset files (`.unity`, `.prefab`, `.asset`, `.meta`). **D7's first trigger.**
   - **(c) RECORD ONLY:** how the four-reviewer panel and the per-task hard gate behaved on a task whose diff carries a large engine asset file. **D7's second trigger.**
   - ⚠ **(b) and (c) produce a record and never a change; only (a) can fail this anchor.**

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with anchors 1 and 2 scored together. ⚠ **Anchors 3(a) and 3(b) are scored SEPARATELY and never collapsed into one result**, which is the whole reason they were split.
- **If an anchor fails,** record the negative with its artifacts and name the mechanism before proposing any fix. A command still killed early is D1's consumer read; a broken command that no longer self-repairs is the D1 fallback or the F2 classification; **a `game-engineer` MISSING from `.claude/agents/` is an off-list `project_natures` string, the advisory-vocabulary residual (F14, residual 9) — never D5's row**; an **installed but unassigned** `game-engineer` is D5's table row, not the roster gate (F17); a diff wider than one key is D1's append position; **a path under `Library/` in `index.json` is Phase 1b's exclusion — not D7, and not F26's operator route.** **They have different fixes.**
- **Anchor 5(a) is scored; 5(b) and 5(c) produce a record, never a change.** A fix proposed from (b) or (c) re-enters at Phase 0 as a new decision; a failure of (a) is a Phase 1b defect and is fixed as one.
- ⚠ **A clean run shows the mechanisms behave on planted cases, never that any gap cost anything** — no incident stands behind this plan.

---

## Honest bounds

- **The key changes WHEN a command is killed, never whether the framework understands the toolchain.** Nothing here teaches any phase what a Unity build is.
- ⚠ **ANY non-code failure is still classified as an ordinary command failure and still enters self-repair** (F2, residual 2) — a timeout is one instance of that shape, not the shape itself. This plan moves the threshold and does **NOT** change the classification, and a failure that comes back FAST — an engine editor lockfile is the likeliest first case — is untouched by a ceiling of any size. Whether such a failure deserves its own status is a residual with a trigger, not a fix here.
- **The regression gate stays disarmed for such projects BY DECISION** (D3), not by oversight — and `REGRESSION_GATE=off` is the honest name for that, not a preference.
- **Nothing measures whether `game-engineer` produces usable engine code.** The reachability gate checks that a name resolves; the roster gate checks that an assigned agent is installed. Neither checks competence.
- ⚠ **Nothing guarantees the agent is INSTALLED either, and the failure is silent** (F14, residual 9). The nature vocabulary is advisory, not enum-enforced, so an off-list `project_natures` value — `"Game"`, `"unity"`, anything — is accepted by the setter and matches nothing in `_decide_agent`, and `game-engineer` is dropped with no error and no warning. **The whole of D4's reliance is on `/devforge:configure`'s composition rule writing the literal `game`**, and this plan adds no check that it did.
- **Nothing checks that the project's constitution carries the engine-version knowledge D4 relies on** — this plan neither writes nor seeds it.
- **The roster counts are prose that nothing pins** (D6's counter-argument). They will go stale again.
- **The index exclusion is GLOBAL, not nature-gated** (D8). Every project now skips a directory named `Library`, `Temp`, `Logs` or `UserSettings`, including one where such a directory holds real source — a **known cost on the terms `build`, `bin`, `obj`, `out` and `target` already set**, not a new kind of cost, and not a cost this plan removes.
- **No incident, nothing measured, and no Unity project exists yet to run Phase 5 against.**

---

## Tripwires

- **Plan 75's tripwire, BOTH halves:** zero new `verify-*` gate numbers, zero new check numbers, zero new hard-fail validators. The setter's positive-integer check is **inside one setter**, not a fifth shared validator (D1).
- **Python is confined to Phases 1 and 1b.** ⚠ **Phase 1c is INSTRUCTION-ONLY despite its letter** — it edits one command spec and writes no Python, so the lettering marks it as the prose half of Phase 1's count move and never as a third Python phase. Phases 1c, 2, 3 and 4 are instruction and docs only.
  - Python goes python-engineer → python-reviewer, with a test per function, run in the same turn.
  - Every markdown edit goes instruction-author → instruction-reviewer.
  - **Every Claude-Code-integration fact is checked through `claude-code-guide`** — Phase 2 owes that check before the agent source is written.
- **No constitution edit.**
- **No `src/CLAUDE.md` `### Always` or `### Never` item.**
- **No plan-63/93 count delta** — 16 model-invocable / 4 human-typed-only is untouched, and **no `disable-model-invocation` flag moves.**
- **No back-porting into shipped installs.** They arrive via `install.sh` / `update.sh` (F21).
- **Commit by explicit path, never `git add -A`** (F30).

---

## Residuals (found during drafting, not fixed)

⚠ Each of these is **verified against the tree** (its F-number, or the file it names, says where) and **left unfixed by scope, not by oversight.** Each carries a trigger — an observation from a real run, **except residual 10's, which is the next work that would reach the site**; none is a speculative fix waiting for permission.

1. **A gate timeout becomes a silent rule FAILURE with an empty report (F5).** `_cmds_gate.py` converts a timed-out `constitute_helper` call into a rule failure carrying an empty report string, which reads downstream as "checked and failed" rather than "did not finish". **Trigger:** an observed empty-report rule failure on a real run. D2 records why it is not fixed here.
2. **ANY non-code failure is laundered into self-repair as though the code were broken, and the partial output is discarded (F2, F4).** `_is_tooling_unavailable` matches only exit 127 and two anchored strings, so **everything else** — a timeout, an environment lock, a refused licence — enters the repair loop as a code defect, and the repairing agent gets one line of text rather than the output that was already produced. ⚠ **A timeout is ONE INSTANCE of this shape, not the shape itself**, and stating it as "a timeout is misclassified" understates it. **The most likely first real trigger is an engine editor lockfile:** ⚠ **Unity-domain claim from a review, NOT a tree fact** — Unity refuses batchmode on a project already open in the editor (`Temp/UnityLockfile`) and fails **FAST rather than by timing out**, so the failure is neither exit 127 nor either anchored string, and **D1's larger ceiling cannot reach it.** **Trigger:** an observed self-repair cycle whose input was a non-code failure of any kind. ⚠ D1 raises the threshold and leaves this shape exactly as it is.
3. **The baseline worktree is never built (F7).** `_symlink_deps` links four dependency directories and builds nothing, so any suite needing compiled artifacts fails at the merge base and disarms the gate. **Trigger:** an observed need on a real run, per D3's named strengthening arm.
4. **Seven natures have no code-writing owner (F15).** desktop, cli, library, plugin, data, ml and game keep only `devops-engineer` and `qa-engineer`; **this plan fixes only `game`.** **Trigger:** a project of one of the other six natures reaching `/devforge:breakdown`.
5. **Hygiene calls `readlines()` with no size cap and no binary check (F23).** The denylist defaults to scanning, and no engine asset extension is on it. **Trigger:** Phase 5 anchor 5(b).
6. **The index walk still never consults `.gitignore`, and its skip list is still global (F31, D8).** D8 removes the four engine-cache names and **nothing more**: the walk reads no ignore file, so any OTHER gitignored directory is walked in full, and `_FILE_WALK_SKIP_DIRS` remains a fixed list that runs before `project_natures` exists. **Trigger:** an observed graph polluted by a directory D8 does not name. ⚠ F26's package-declaration route is the operator's instrument here and needs no code change.
7. **There is no non-browser runtime AC channel, and `AC_RUNTIME_CLI_COMMAND` is executed by nothing (F28).** For any project with no browser and no API base, **every `frontend`- and `backend`-classified item degrades to `code-fallback` — code-only behaviour for everything that could have been automated — while `manual`-classified items still report MANUAL** (F28: the MODE does not become `code-only`). The CLI key is a string handed to an agent with no timeout, no lifecycle and no output capture. **Trigger:** an observed run where `runtime-assisted` was configured and silently produced `code-fallback` for every automatable item.
8. **The review panel's changed-file list carries no size cap and no extension filter.** `files_for_finders` in `src/devforge/lib/_shared/feature_scope.py` hands the full changed-file list on as-is, so a multi-megabyte engine scene or asset in a task's diff reaches the four-reviewer panel and the per-task hard gate whole. ⚠ **This is a context-overflow risk — a different class of consequence from advisory hygiene noise.** **Trigger:** Phase 5 anchor 5(c). D7 records why it is not fixed here, and why its recorded-not-fixed reason is narrower than hygiene's.
9. **An off-list nature string drops the agent SILENTLY (F14).** The nature vocabulary is advisory rather than enum-enforced — `set-project-natures` accepts any non-empty string — while `_decide_agent`'s membership test is exact and case-sensitive. So an LLM at `/devforge:configure` Phase 2 that composes `"Game"`, `"unity"`, `"game-dev"` or any other off-list value produces a `project_natures` the setter accepts, `prune-agents` then finds no overlap with `applies_to: ["game"]`, and **`game-engineer` is simply not installed — no error, no warning, no report line anywhere.** The first visible symptom is F16's human escalation at assignment time, one command later and with nothing pointing back at the cause. ⚠ **Nothing mechanical prevents this, and this plan adds nothing that would:** D4's decision rests on the composition rule writing `game` (`src/commands/configure/main.md:116`), not on anything checking that it did. **Trigger:** observed on a real run — Phase 5 anchor 3(a) is the first place it would show.
10. **`docs/v2/ARCHITECTURE.md` under-reports the index walk's file cap by a factor of twenty (F24).** `docs/v2/ARCHITECTURE.md:80` reads *"Walk source tree (capped at 500 files; `files_truncated: true` flag set on overflow)"*, while `src/devforge/lib/index_helper.py:90` reads `_MAX_FILES_PER_PACKAGE = 10000` and the comment above it records the historical 500 cap and why it was raised. ⚠ **It is PRE-EXISTING and NOT caused by this plan.** F24 and Phase 1b's Verify both state that the cap is untouched here, and they are right: D8 adds four names to a **different** constant in the same module and moves nothing else. **Why it is RECORDED rather than fixed:** it is exactly the class plan 92's precedent leaves alone — `docs/v2/ARCHITECTURE.md` staleness that a plan did not cause. Phase 4's own bullet draws that line for the eight count sites and `:81`: this plan fixes those **because its own Phases 1 and 1b falsify them.** `:80` is falsified by neither, so it stays on the plan-92 side of the line. ⚠ **Why it is recorded AT ALL, rather than ignored:** `:80` is the line IMMEDIATELY ABOVE `:81`, which Phase 4 does edit — so a builder working on `:81` will have `:80` on screen. Naming it here makes a drive-by edit a **recognised scope departure rather than an accident**, and Phase 4's Verify clause — *"the lines around it in that section are byte-identical — this phase edits `:81` and no neighbour"* — is the mechanical half of the same guard. ⚠ **The irony is the point, and it is a THIRD sweep class beyond Trap 21's two.** `:80` carries neither a count this plan moves nor the name of a constant this plan edits: it states a **different** constant's VALUE, and **it does not name that constant anywhere on the line** — so the constant-NAME sweep Trap 21 prescribes could not reach it even if some phase owed one for `_MAX_FILES_PER_PACKAGE`, and no phase does. **No grep in this plan's Verify would ever have reached this site.** It was found only because a human read the line next to one being edited: **Trap 21's two sweeps are necessary and NOT sufficient, and proximity reading found what patterns could not.** **Trigger:** a plan that touches `_MAX_FILES_PER_PACKAGE` itself, or a general `docs/v2/ARCHITECTURE.md` freshness sweep. ⚠ **Neither is this plan.**

---

## Non-goals

- **Unity rules in `src/files/devforge.gitignore`.** That template is `.devforge/`-scoped by design (F27); a Unity `.gitignore` is the project's own file, and ecosystem rules there would be a category error.
- **A configurable index-exclusion SURFACE.** D8 adds four literal names to an existing skip list and adds **no mechanism**: no config key, no per-project exclusion list, no nature gate, no ignore-file read (F31). A surface an operator could configure is a separate plan with its own evidence bar; **F26's package-declaration route is the operator instrument that already exists.**
- **No change to the CBM discovery-gate hook.** The briefing suggested exempting non-code extensions from it. ⚠ **The premise is wrong** (F32): the hook fires ONCE per session and applies no extension filter of any kind, so a project with many non-code text files pays exactly one block, the same as any other project. **There is nothing to exempt.** ⚠ **Recorded as REFUTED, not deferred** — it carries no trigger, nothing would revive it, and a future session must not re-raise it as unfinished business.
- **A new AC runtime channel.** A screenshot or CLI-assertion channel is a separate plan with its own evidence bar; F28 records the gap, and recording it is the whole of this plan's claim there.
- **An implementer for the other six ownerless natures** (F15). Each needs its own domain knowledge and its own consumer; `game` has a stated purpose behind it and they do not.
- **Back-porting into shipped installs.** They arrive via `install.sh` / `update.sh` (F21), and the `FIELD_DEFAULTS` back-fill makes the upgrade silent (F11).
- **Any change to `/devforge:verify`'s verdict inputs.** D3 turns a gate off through an existing key; it adds no status, no reason and no blocker.
- **Anything that touches the frozen benchmark install,** and **any consumer path or specific product in a tracked file** — no client, component, ticket, benchmark path, directory or named project, here or in anything this plan writes.

---

## Context for next session

⚠ **Evidence class, repeated: NO consumer incident, none claimed, nothing measured.** The purpose is a Unity CAPABILITY, not one port, and **no Unity project exists yet to run Phase 5 against.** ⚠ **A broader purpose is not evidence.** ⚠ **All line digits drift — grep the quoted text, never the digits.**

⚠ **A short index line is not a short plan.** This plan's entry in `PLAN-STATUS-ARCHIVE.md`'s `## Index` "Currently active" list is ONE LINE — by convention and by the one-line constraint Phase 4 records — while this file carries **32 facts (F1–F32), 8 decisions (D1–D8), 4 open questions, 8 phases, 21 traps and 10 residuals**, and the full status record lives in that same file's `## Entries`. The convention states it in its own words: *"A short index line is not evidence that a plan is simple or its history thin; this file is the full record."* **Read the `## Entries` entry and this file — never the index line alone.**

**The one sentence that governs everything here:** a project whose toolchain is measured in minutes and whose language is not on the web path gets a timeout it can configure, a builder that can own its code, and an index walk that does not swallow the engine's caches — and everything else the framework does badly there is RECORDED with a trigger rather than guessed at, on one line: **fix what breaks before it can be observed; record what can be observed as it happens.**

**Trap 1 — raising `_cmds_gate.py`'s timeout.** It bounds the framework's own `constitute_helper` calls, not the project's toolchain (F5, D2). Two constants share the name `_CMD_TIMEOUT`; only the one in `_cmds_verify.py` is the project's.

**Trap 2 — describing a game project as "hard-blocked by the roster gate".** It is not. The failure is human escalation at assignment time (F16); the roster gate fires only on a task that assigns an agent that is not installed (F17).

**Trap 3 — naming the agent `unity-engineer`.** `applies_to` is matched case-sensitively against `project_natures`, and the documented vocabulary contains `game` and no engine names (F14, D4). ⚠ **Do not defend this with "the vocabulary is closed" — it is ADVISORY, not enum-enforced** (F14). The argument that holds is the composition rule at `src/commands/configure/main.md:116`, which writes `game`. ⚠ **The file itself will tell you otherwise seven lines earlier:** `src/commands/configure/main.md:109` opens the `PROJECT_NATURES` bullet with *"Closed vocabulary:"* and lists the twelve. That sentence describes the intended VALUE SET, **not a validator** — no setter, schema entry or gate rejects an off-list string (F14, residual 9) — so a reader who arrives at `:116` and takes `:109` at its word has adopted the very defence this trap forbids.

**Trap 4 — adding the field without a `FIELD_DEFAULTS` entry.** That entry is both the legacy back-fill and the null-scalar exemption; without it, **every existing install fails `configure_helper verify`** (F11).

**Trap 5 — a name whose case does not transpose.** `render-config` maps by `key.lower()`; a mismatch renders `None` and fails the round-trip check (F12).

**Trap 6 — hunting for a shared `project-config.json` reader.** There is none, deliberately — 33 private readers, with the rationale in-tree (F13). The new key adds its own read at one consumer.

**Trap 7 — a field in no display group.** It is **silently absent** from the Phase 7 report the user reads (Phase 1). Nothing fails; the field just never appears.

**Trap 8 — expecting the regression gate to work once the timeout is raised.** It is disarmed by the unbuilt worktree, not by time (F7, D3).

**Trap 9 — adding Unity rules to `devforge.gitignore`.** That template is `.devforge/`-scoped (F27).

**Trap 10 — assuming `.csproj` is undetected, or assuming it is on disk.** It is already a first-class manifest with composed `dotnet` commands (F25) — and, per the same fact's review nuance, it is **generated by the IDE packages and excluded by the standard engine `.gitignore`**, so a fresh clone may carry none and a git worktree never does.

**Trap 11 — writing an engine-version API table into the agent.** It would rot inside the framework; version specifics belong in the consuming project's constitution (D4).

**Trap 12 — the literal `.claude/memory` in a new agent source.** The memory-lane Rule 4 sweep walks every file under `src/` (F22).

**Trap 13 — sweeping another session's uncommitted files.** They are in this tree right now (F30). Re-read `git status`, commit by explicit path.

**Trap 14 — reading a predicted gap as observed.** No incident stands behind any item here, and a clean Phase 5 never converts one into an incident that happened. ⚠ The broadened purpose does not change this: **a capability goal is not evidence.**

**Trap 15 — adding the engine cache names in lowercase.** The membership test is exact, every existing entry in `_FILE_WALK_SKIP_DIRS` is lowercase, and the engine's directories are capitalised — `library` matches nothing and **fails silently, looking exactly like a correct change** (D8, Phase 1b).

**Trap 16 — computing the self-repair worst case as four times the whole command list.** The loop breaks at the first failure, so it is four times the commands that precede the failing one plus the failing one (F3) — roughly 80 minutes at a 1200-second ceiling with one slow command, not several hours.

**Trap 17 — exempting extensions from the CBM discovery-gate hook.** It fires once per session and applies no extension filter, so there is nothing to exempt (F32). ⚠ Recorded as **refuted, not deferred** — do not re-raise it as unfinished business.

**Trap 18 — "correcting" a count that is a historical record.** The schema and key counts appear in a released `CHANGELOG.md` entry (`:40`) and the agent counts appear in `PLAN-STATUS-ARCHIVE.md` and several plan documents. **Each states what was counted live on its own date; editing it falsifies the record** (F20, Phase 4). ⚠ `DEVELOPMENT-STATUS.md` is the ONE outside-`src/` file that IS live status prose — classify it on its own terms, not under this trap.

**Trap 19 — scoring a missing `game-engineer` as D5's table row.** If the agent is absent from `.claude/agents/` it was never installed, and the cause is an off-list `project_natures` string that `set-project-natures` accepted and `_decide_agent` did not match — **silently** (F14, residual 9). D5's row governs ASSIGNMENT of an installed agent. Phase 5 anchor 3 is split into (a) and (b) for exactly this reason.

**Trap 20 — treating a builder's `## Output` as forbidden.** It is **optional**; five of the eight current builders omit it and three carry one (F19). `game-engineer` omits it by choice (D4), and a Verify that rejected the section outright would assert a contract the tree does not have.

**Trap 21 — sweeping a constant's edit with value-greps only.** ⚠ **Two sweep CLASSES are different, and conflating them is what produced two late findings in this plan's own drafting.** A **COUNT** can be grepped by its VALUE — **but only if every phrasing is enumerated**: `docs/v2/ARCHITECTURE.md:331` spells the same two counts as `37 configure.yaml` and `45 project-config.json keys`, so four value patterns returned seven sites and missed it, and a fifth pattern (`Field-source map`) was needed to reach it. An **ENUMERATION** — a live doc that mirrors a constant's MEMBERS, as `:81` mirrors `_FILE_WALK_SKIP_DIRS` — ⚠ **can NEVER be found by grepping values at all**, because it carries no count to grep. **It is found only by grepping the CONSTANT'S NAME.** So for every constant a phase edits, the constant's name is grepped across `docs/` and `src/` as a **SEPARATE sweep from the value greps**. The worked example is `_FILE_WALK_SKIP_DIRS` → `docs/v2/ARCHITECTURE.md:81` (Phase 1b's constant, Phase 4's edit); **Phase 1 owes the same sweep for `FIELD_SCHEMA` and `_PROJECT_CONFIG_KEY_ORDER`**, and whatever it returns is classified before Phase 4 is called done. ⚠ **Two sweep classes are still not enough — do not read this trap as complete.** Neither sweep reaches a THIRD class: a doc line that states a **different** constant's VALUE without naming that constant, carrying no count this plan moves and no constant name this plan edits. **Residual 10 is the worked example** — `docs/v2/ARCHITECTURE.md:80`, found only by reading the line next to one being edited, by no pattern at all. **The two sweeps are necessary, not sufficient.**

**File anchors:**

- `src/devforge/lib/_implement/_cmds_verify.py` — `_CMD_TIMEOUT`, `_is_tooling_unavailable`, `SELF_REPAIR_CAP`, the repair loop's restart **and its first-failure break** (F3).
- `src/devforge/lib/_implement/_cmds_gate.py` — the second `_CMD_TIMEOUT` (read-only here, D2).
- `src/devforge/lib/_verify/_regression.py` — read-only here (D3); `_hygiene.py` — read-only here (D7); `_e2e.py` — read-only and **out of scope: no decision mentions it at all, and F8 is the only place in this plan it is discussed.**
- `src/devforge/lib/_configure/` — `_schema.py`, `_cmds_set.py`, `_cli.py`, `_render.py`, `_summary.py`, `_cmds_verify.py`.
- `src/devforge/lib/index_helper.py` — `_FILE_WALK_SKIP_DIRS` (**the ONLY thing Phase 1b edits**, D8); `_list_package_files`, `_MAX_FILES_PER_PACKAGE` and `_detect_manifest` (read-only, byte-unchanged).
- `src/devforge/lib/_shared/feature_scope.py` — `files_for_finders` (read-only here, D7).
- `src/hooks/cbm-code-discovery-gate` + `src/settings.template.json` — read-only, never edited (F32, and the non-goal it refutes).
- `src/agents/` — the new `game-engineer.md`; `architect.md`, `performance-analyst.md`, `devops-engineer.md`, `design-auditor.md` (Phase 3); `ac-verifier.md` (read-only, F28).
- `src/agents-AUTHORING.md` — the contract and the three count sites.
- `src/commands/breakdown/main.md` — the Agent Assignment table, its not-generated arm, the relay line, `verify-agent-roster`.
- `src/commands/plan/main.md` — the relay line.
- `src/commands/configure/main.md` — **Phase 1c's ONLY file**: four count sentences move, six do not; `:116` is the `PROJECT_TYPE == "game"` → `game` composition rule D4 rests on (read-only).
- `docs/v2/ARCHITECTURE.md` — **Phase 4, EIGHT falsified count sites** (`:260`, `:279`, `:286`, `:324`, `:331`, `:369`, `:388`, `:390`), with the `ENUM_FIELDS` 9 at `:286` and the direct-keys `12` at `:369` byte-unchanged — ⚠ **and `:81` SEPARATELY**: the prose enumeration of `_FILE_WALK_SKIP_DIRS`'s members, falsified by **Phase 1b** rather than by Phase 1, reached by no count grep, and edited only if Phase 1b runs (Trap 21).
- `CHANGELOG.md:40` — **read-only, never edited**: a released entry's frozen count record (Phase 4, F20's reasoning).
- `scripts/verify-agent-reachability.py`, `scripts/generate-agents.py` — run, never edited.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `## Phase 0 close record` first.** If this file has none, **nothing is ratified and no build phase may start.**
3. **Re-verify F1–F32 against the live tree.** Grep the quoted text, never the digits: `_CMD_TIMEOUT`, `Command timed out after`, `SELF_REPAIR_CAP`, `Stop at first failure`, `not recognized as an internal or external command`, `_WORKTREE_TIMEOUT`, `_DEP_DIRS`, `baseline-failing`, `_E2E_TIMEOUT`, `FIELD_DEFAULTS`, `_PROJECT_CONFIG_KEY_ORDER`, `two independent config readers`, `applies_to`, `The roster is`, `### Builders (`, `_FILE_WALK_SKIP_DIRS`, `_MAX_FILES_PER_PACKAGE`, `_list_package_files`, `packages_detected`, `_SKIP_EXTENSIONS`, `prefer false negatives over false positives`, `files_for_finders`, `cbm-code-discovery-gate`, `AC_RUNTIME_CLI_COMMAND`.
4. **Re-run the two counts rather than quoting F10 and F15.** Both were obtained by EXECUTING modules on 2026-09-20; another session's landed work moves them.
5. **Build order:** Phase 1, Phase 1b and Phase 2 are mutually independent — Phase 1b is a second, separate Python change, not a continuation of Phase 1. **Phase 1c follows Phase 1 and must land in the same working session as it**: it states the counts Phase 1 creates, so between the two the command spec is false. Phase 3 follows Phase 2 (it names the agent Phase 2 creates). Phase 4 runs last, because it records what the earlier phases did.
6. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit (Phases 1 and 1b **only**), with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit — **including Phase 1c, which is instruction-only despite its letter**;
   - `claude-code-guide` before Phase 2 writes the agent source, and for every new Claude-Code-integration fact.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first (F30).
8. **After each phase, cross-check.** Grep every key, verb, constant and heading touched — `COMMAND_TIMEOUT`, `command_timeout`, `game-engineer`, `Builders (`, `RELAY_ONLY_ALLOWLIST`, `_FILE_WALK_SKIP_DIRS` — and fix any dangling reference in the SAME change. ⚠ **For the count move, grep FIVE patterns, not one** — `37 fields`, `37-field`, `45 keys`, `45-key` **and `Field-source map`** — and classify every hit as a site that moves, a site that does not, or a frozen historical record that is never touched (Phase 1c, Phase 4, Trap 18). ⚠ **Then run a SECOND sweep of a different KIND: grep the NAME of every constant a phase edited** — `FIELD_SCHEMA`, `_PROJECT_CONFIG_KEY_ORDER`, `_FILE_WALK_SKIP_DIRS` — across `docs/` and `src/`, **because a doc that mirrors a constant's MEMBERS rather than its count is falsified by an edit no value-grep can see** (`docs/v2/ARCHITECTURE.md:81` is the worked example; Trap 21).
9. **Run Phases 1, 1c, 1b, 2, 3 and 4, then leave Phase 5 to the maintainer**, and leave every D7 observation undecided until that run produces it.
10. **Keep the evidence class attached.** Any summary of this plan repeats it: NO consumer incident, none claimed, nothing measured — and no Unity project existed to run Phase 5 against when the plan was written. ⚠ **The plan's purpose is a capability, not a port, and the purpose is not evidence.**
