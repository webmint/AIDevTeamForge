# 90 — The e2e test lane: a declared scenario, an owning task, and one feature-level run

**Status:** **Phase 0 CLOSED 2026-08-27 — D1–D8 RATIFIED and OQ-1–OQ-7 RESOLVED. Phases 1–5 CLEARED TO BUILD, none started. Phase 6 stays a deferred user-driven HARD GATE.**

- **Phase 0 CLOSED 2026-08-27** — D1–D8 and OQ-1–OQ-7 ALL answered, with **the four explicit picks answered in-session by the maintainer**: **D3** = advisory **fork (i)**, no status gates the verdict in v1, and its reporting sub-question resolved **reasons-only** (`compute-verdict` gains an `--e2e` input that adds a `reasons` line and **NO blocker**; `render-report` unchanged; no new `verification.md` section); **D1** = the top-level `E2E_COMMAND` key, with its **seeding fork resolved to the THIRD arm** — `/devforge:configure` composes the field's default from the `MANIFESTS_JSON` manifests it already parses, so **`init_helper`'s detector is NOT wired in and `.devforge/init.yaml`'s `test_infra.e2e` is read by nothing**; **D5's placement fork** = the **dedicated-e2e-directory rule**, with the runner-config exclude arm reaching NO emitted text; **D5's section fork** = **arm (a)**, rename and widen `## Mobile Testing`, every mobile bullet byte-identical. **Everything off the pick-list ratified AS RECOMMENDED.** Full record: `## Phase 0 close record`.
- **Phases 1–5 are CLEARED TO BUILD and NOT STARTED.** No Python, no instruction text and no docs sweep exists yet, and **nothing in this file may be read as shipped.** Every phase keeps the route named in its own block; **Phase 1 and Phase 4's Deliverables 1–2 are the only Python**, and Phases 2, 3 and 5 dispatch none.
- **Phase 6 consumer e2e stays a deferred user-driven HARD GATE, NOT run.** Everything Phases 1–5 will produce is build-verified and **NOT consumer-validated**. The three known-answer anchors are unchanged — the declared happy path, the silent install, the broken flow — with **anchors 1 and 2 scored as a PAIR** and anchor 3 recording the verdict as a STRING. ⚠ **Ratification observes nothing:** a ratified decision is not a validated one, and no anchor has been run.

**Branch:** `develop-2.0-init`
**Created:** 2026-08-26.

**Amended 2026-08-27 — staleness reconciliation after plan 89 shipped (no ratification content; every D and OQ stays OPEN):**

- **Plan 89 is DONE (build) 2026-08-27** — its Phases 0–5 are complete and its Phase 6
  consumer e2e is DEFERRED, **not waived**. **So this plan definitively ships SECOND**, and
  Phase 5's coordination rule — *"whichever ships second reads the LIVE text of each shared
  surface and re-derives its edit from what it finds"* — now names **THIS** plan
  unconditionally, where it was drafted as a conditional binding on whichever went first.
- **All THREE unconditional shared surfaces MOVED.** `src/CLAUDE.md`'s `### Always` list is
  now **SIXTEEN** items, item 16 being *"**Test behavior changes** — every change to
  observable behavior ships with a test that asserts it; the configured test command must
  pass on changed files before task completion"*; `src/devforge/storage-rules.md`'s task-file
  Done-When skeleton now carries **FIVE** standing lines, the fifth being *"Tests pass on
  changed files (see Development Commands section)"*; and `src/agents/qa-reviewer.md`'s
  **Approach step 4** and **Rule 3** now carry plan 89's vacuous-test shapes with its OQ-6
  severity floor inline. ⚠ **Step 6's mobile-parity sentence was verified INTACT and
  byte-identical on 2026-08-27** — the clobber hazard Phase 3 and Trap 7 name has not fired,
  and confirming that again at build time is still this plan's job.
- **Plan 89's OQ-3 RESOLVED to arm (i)** — accept §3.4's emptiness, add nothing — so
  **`src/agents/qa-engineer.md` was NOT touched by plan 89 and is NOT a shared surface.** The
  conditional-fourth branch never fired: this plan is that file's only prospective editor,
  and **D5's SECTION fork applies to virgin text**.
- ⚠ **This block records OBSERVED STATE as of 2026-08-27 and does NOT substitute for the
  live read Phases 3 and 5 owe at build time.** The coordination rule binds the **READ**, not
  the edit; a build that quotes these bullets instead of opening the files has done the exact
  thing the rule forbids.
- **Where the per-site notes are:** facts **20**, **21a** and **28**; **Phase 1's build
  constraint 3**; **D3's second reasoning bullet**; **Phase 3's** `qa-reviewer.md` scope
  bullet **and** its matching Verify bullet; **Phase 5's** `configure/main.md`,
  `src/CLAUDE.md`, `storage-rules.md` and plan-89 bullets; the **`## Non-goals`**
  constitution-edit bullet; **Trap 7**; the **`## Dependencies + related`** entries for
  plans **89** and **85**; and **`## When resuming work` step 1**. ⚠ **This index is a
  convenience, NOT a certified-exhaustive map** — a dated note found elsewhere in this file
  is an omission in this list, not an unauthorized edit.
- ⚠ **CORRECTED 2026-08-27, later the same day — this block's own header clause *"no
  ratification content; every D and OQ stays OPEN"* was TRUE when written and is now
  FALSE.** Phase 0 CLOSED 2026-08-27: D1–D8 are RATIFIED and OQ-1–OQ-7 RESOLVED — see the
  Status block above and `## Phase 0 close record`. **Every other sentence in this block is
  unaffected**: it records observed shared-surface state as of 2026-08-27, and the live read
  Phases 3 and 5 owe at build time is unchanged by ratification.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

**There is no incident behind this plan and none is claimed.** Its evidentiary base is
(a) one maintainer question dated 2026-08-26, recorded verbatim in `## Origin`, and (b) a
full `src/` sweep run the same day, whose results are the rows of `## Verified mechanics`.
No consumer run failed, no defect escaped, and no measurement exists. This is a
**predicted-gap plan** in the shape of plan 87 (whose origin was likewise a configuration
observation, not an incident) — say so wherever this plan is summarized, and never let a
later session read the gap as an observed loss.

The two UNTRACKED private-client evidence files at repo root
(`81-EVIDENCE-V2-BENCHMARK-RUN.md`, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`) are
neither read nor cited here, and no phase may import from them.

---

## Origin — a question, and a sweep that answered it worse than expected, 2026-08-26

**The question.** The maintainer asked, on 2026-08-26, whether end-to-end tests are needed
in the emitted pipeline and what adding them would take. Nothing in the question named a
failure; it named an absence.

**What the sweep found — three findings, and the third is the one nobody had named:**

**1. The emitted framework contains no web-e2e concept at all.** A grep of every markdown
file under `src/` for `playwright|cypress|selenium|puppeteer|webdriver` returns **zero**
hits (fact 1). The only end-to-end vocabulary anywhere in the emitted instruction set is
**mobile-only and advisory**: one bullet in `qa-engineer.md`'s `## Mobile Testing` section
naming Detox / XCTest UI / Espresso / `integration_test`, and its mirror sentence in
`qa-reviewer.md`'s step 6 (fact 2). A web project installing this framework gets a
pipeline with an acceptance-criteria verifier, a four-reviewer panel, a full-suite
regression gate and six decomposition gates — and no notion that a user flow can be
exercised end to end.

**2. There is no test-tier taxonomy to hang one on.** Configuration carries exactly one
`test_command` per package plus one flat `TEST_COMMANDS` array (fact 4), and nothing —
not the config, not the task-file schema, not any handoff — distinguishes unit from
integration from e2e. **This is the plan's central structural problem, and it is why
"just add e2e to the test command" is not an option** (see the rejected alternative
below).

**3. Detection for e2e already exists, is never run, and could not be used if it were.**
`init_helper` maps `playwright` and `cypress` to an `e2e` bucket and persists a
`{frontend, backend, e2e, status}` record, with a `set-test-infra --e2e` override verb
and per-bucket validation (fact 7). **No command spec ever invokes `detect-test-infra` or
`set-test-infra`** — a grep of all of `src/` for those verb names returns hits only inside
`init_helper.py` itself (fact 8) — so on a real install the block sits at its
all-`None`/`status: absent` default unless someone runs the helper by hand. And the one
reader of the record's bucket VALUES filters them through a schema-valid set that
**excludes playwright and cypress**, so the `e2e` bucket's value is unreachable by
construction: the only thing that bucket can influence today is the derived `status`
count (fact 9). `/devforge:research` reads that `status` and nothing else (fact 10). The
detector is, end to end, write-only.

**The direction this plan proposes:** an e2e lane that is **declared** at `/devforge:plan`,
**owned** by a `qa-engineer` task at `/devforge:breakdown`, and **run once per feature** at
`/devforge:verify` — advisory in v1, never a gate — with the e2e command in its own
config key that the per-task and regression paths cannot see. **Nothing in the existing
test plumbing changes.**

### The rejected alternative, with its reasoning (recorded so it is not re-proposed)

The obvious cheap move is to **put the e2e suite in `test_command`** (or in
`TEST_COMMANDS[0]`) and let the existing machinery run it. It is rejected on two
independent grounds, either of which decides it:

- **It runs per task, inside `/devforge:implement`.** `verify-touched` matches each touched
  file to its package and runs that package's `test_command` on **every task**, with a
  helper-owned self-repair cap of 3 (fact 5). An e2e suite there is paid once per task and
  re-paid up to three more times per failing task, for a signal that is feature-level by
  nature.
- **It is broken by construction inside the regression gate.** `regression-gate` runs
  `TEST_COMMANDS[0]` twice: once at the merge-base **inside a detached `git worktree` under
  the system temp dir**, and once at HEAD in the real `source_root` (fact 6). The baseline
  run is a bare checkout with a best-effort symlink of `node_modules`/`.venv`/`venv`/
  `vendor` and nothing built and nothing served — an e2e suite that needs a running
  application does not merely fail there, it fails **for a reason that has nothing to do
  with the feature**, and the gate's own semantics would then read that as
  `baseline-failing` and stop gating. **A gate that silently disarms itself is worse than
  no gate.**

A third, weaker objection is recorded because it will be raised: both runs are capped at
`_TEST_TIMEOUT = 600` seconds each (fact 6), so a slow e2e suite in that slot doubles a
ten-minute ceiling. That is a cost argument; the two above are correctness arguments.

---

## What is actually being added

Four things. **Phase 0 ratifies each independently; a future session must not read any one
as depending on the others.**

1. **One config key** (Phase 1) — where the e2e command lives, seeded from the detection
   that already exists and is currently discarded (D1). **Python.**
   ⚠ **CORRECTED 2026-08-27 by Phase 0's ratified seeding arm — the clause *"seeded from the
   detection that already exists and is currently discarded"* is FALSE as ratified.**
   `/devforge:configure` composes the default from the `MANIFESTS_JSON` manifests it already
   parses; **`init_helper`'s detector is NOT wired in and stays exactly as unused as it is
   today**, and `.devforge/init.yaml`'s `test_infra.e2e` is read by nothing this build
   produces (D1's ratification paragraph; Phase 1's Deliverable 2).
2. **A declaration point** (Phase 2) — a new architect sub-question at `/devforge:plan`
   §1.3 and a conditional `### E2E Scenarios` plan subsection (D2). **Instruction-only.**
3. **An owner** (Phase 3) — `/devforge:breakdown` renders a dedicated `qa-engineer` task
   for the declared scenarios, and `qa-engineer` / `qa-reviewer` gain a web arm beside
   their mobile one (D5). **Instruction-only.**
4. **An execution seat** (Phase 4) — a new fail-soft `/devforge:verify` sub-phase that runs
   the suite once at HEAD in the real workspace and reports (D3). **Python + instruction.**

**⚠ Three honest bounds that must survive into every emitted sentence:**

- **v1 gates nothing.** D3 recommends advisory-only: no e2e status blocks the verdict, and
  the strengthening path is named with its trigger (D4). A summary claiming the framework
  "now requires e2e tests" has over-claimed by a full layer.
- **Nothing checks the declaration.** D4 deliberately builds no PHASE-3.5 gate, so a plan
  that declares an e2e scenario and a decomposition that renders no task for it produce no
  error. The claim is that the ABSENCE is visible in the task set, exactly as plan 86's
  `Regression net:` line claims (fact 17) — not that it is enforced.
- **The lane is silent by default.** D8 requires every seat to no-op cleanly when no e2e
  infrastructure exists and no command is configured. A framework that nags a Python CLI
  project about browser tests has made itself worse.

---

## Verified mechanics (2026-08-26)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token
is the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep
the string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **Zero web-e2e vocabulary in the emitted instruction set.** A `playwright\|cypress\|selenium\|puppeteer\|webdriver` grep over `src/**/*.md` returns NOTHING. The only hits anywhere under `src/` are in three Python files: `init_helper.py`'s bucket maps, `_research/_probe_tier.py`'s extension map, and `_generate_docs/_project_input.py`'s detection tuples | repo grep, 2026-08-26 |
| 2 | **The only E2E vocabulary is mobile-only and advisory, at exactly two sites**: `qa-engineer.md`'s *"**E2E frameworks**: write tests in Detox (React Native), XCTest UI (iOS), Espresso (Android), integration_test (Flutter)"* and `qa-reviewer.md` step 6's *"Note the relevant E2E framework (Detox, XCTest UI, Espresso, integration_test) the parity tests would live in."* | `src/agents/qa-engineer.md:55`; `src/agents/qa-reviewer.md:29` |
| 3 | **`qa-engineer.md` already carries ONE section beyond the canonical skeleton** — `## Mobile Testing`, sitting between `## Approach` and `## Output`. `agents-AUTHORING.md`'s D-Skeleton fixes six heading names and states only *"`architect` and `tech-writer` keep additional substantive sections **beyond** this skeleton"*, so this section is an unrecorded divergence. ⚠ Its heading string `## Mobile Testing` occurs **exactly once repo-wide**, so renaming it is citation-safe | `src/agents/qa-engineer.md:53`; `src/agents-AUTHORING.md:35`–`:45`, `:80`; repo grep |
| 4 | **No test-tier taxonomy anywhere.** `PACKAGE_STACKS` records carry ONE `test_command` per package — *"`null` when the package has no test script — do NOT invent an ecosystem-default guess"* — plus a flat `TEST_COMMANDS` array. The 8-key record shape is stated at **three** sites in that one file | `src/commands/configure/main.md:128`, `:134`, `:233`, `:266` |
| 5 | **`verify-touched` consumes exactly those two things, per task.** It *"loads `PACKAGE_STACKS` … longest-path-prefix matches each source-relative touched file to its package's `type_check_command` + `lint_command` + `test_command` (files outside any package fall back to the primary-stack … `TEST_COMMANDS[0]`)"*, in the fixed order static → build → tests, and **"The helper owns the self-repair cap (3); the orchestrator cannot extend it."** | `src/commands/implement/main.md:160`–`:163` |
| 6 | **`regression-gate`'s two runs are NOT symmetric.** The baseline runs `TEST_COMMANDS[0]` inside a detached worktree created with `tempfile.mkdtemp(prefix="forge-regression-")`; the **HEAD run executes in `source_root`, the real working tree** (`# --- HEAD run (main working tree, source_root) ---`). Dependency dirs are best-effort symlinked (`_DEP_DIRS = ("node_modules", ".venv", "venv", "vendor")`, top-level only) and each run is capped at `_TEST_TIMEOUT = 600` seconds | `src/devforge/lib/_verify/_regression.py:444`–`:446`, `:409`–`:435`, `:107`, `:113` |
| 7 | **e2e detection exists**: `_TEST_INFRA_BUCKETS` maps `"playwright"` and `"cypress"` to `"e2e"`; the record is `{"frontend": None, "backend": None, "e2e": None, "status": "absent"}`; `status` is derived by counting populated buckets (0 → `absent`, 3 → `present`, else `partial`); and `set-test-infra --e2e` validates against `_VALID_FRAMEWORKS_BY_BUCKET["e2e"] = {"playwright", "cypress"}` | `src/devforge/lib/init_helper.py:801`–`:802`, `:161`, `:852`–`:861`, `:815`, `:1400`–`:1404` |
| 8 | ⚠ **No command spec ever runs the detector.** A `detect-test-infra\|set-test-infra` grep across all of `src/` returns hits **only inside `init_helper.py`**. `/devforge:init-forge` never calls either verb (its `init_helper` calls are `reset`, `set-workspace-mode`, `set-project-root`, `set-project-state`, `set-default-branch`, `find-nested-git`, `add-package`, `summary`, `verify`). The ONLY thing that mentions them at runtime is `init_helper verify`'s soft-warn — *"test_infra: status=absent but detector finds {0}; consider running `init_helper detect-test-infra …`"* — which `/devforge:init-forge` DOES reach | repo grep 2026-08-26; `src/commands/init-forge/main.md:24`–`:147`; `init_helper.py:1263`–`:1275` |
| 9 | ⚠ **The `e2e` bucket's VALUE is unreachable in its only reader.** `_pick_framework_from_test_infra` iterates `("frontend", "backend", "e2e")` but returns a value only when it is in `_SCHEMA_VALID_FRAMEWORKS = frozenset({"vitest", "jest", "pytest", "go-test", "cargo-test", "rspec"})` — which contains **neither playwright nor cypress**. A playwright-only project therefore yields `status: "partial"` → tier 1 → framework `None` → *"demote to tier=1.5"* | `src/devforge/lib/_research/_probe_tier.py:105`–`:118`, `:37`, `:185`–`:191` |
| 10 | **`/devforge:research` reads `status` and nothing else**, by grepping `.devforge/init.yaml` for `^  status:` and interpreting *"a line `  status: absent` (or empty/missing output) satisfies the condition; `  status: present` does not"* | `src/commands/research/main.md:915`–`:921` |
| 11 | **The architect's qa-engineer consult row exists and its relay works, but nothing downstream consumes an e2e answer**: `- **qa-engineer** — integration/e2e strategy decision, shared fixtures, explicit coverage requirement`, and `qa-engineer` is in `/devforge:plan`'s named-specialist list. **Sub-questions 1–11 name no test-strategy question**, no `plan.md` subsection holds one, and no task header field carries one | `src/agents/architect.md:77`; `src/commands/plan/main.md:366`, `:382`–`:394` |
| 12 | **A live-app concept already exists, and it produces no tests.** `read-ac-config` emits `ac_verification_mode` (`code-only` \| `tests` \| `runtime-assisted` \| `off`, default `off`) plus `ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command`; under `runtime-assisted` the `ac-verifier` agent *"verifies each AC against the running app"*. Those are per-run OBSERVATIONS feeding a verdict — no test file is written and none is re-runnable | `src/commands/verify/main.md:172`, `:190`; `src/agents/ac-verifier.md:15` |
| 13 | **The fail-soft precedent, in full.** `regression-gate` *"is **FAIL-SOFT by design**: it ALWAYS exits 0, even on a git error, a missing merge-base, or an absent test command"*; its `status` is one of `off` / `inconclusive` / `clean` / `baseline-failing` / `regression`; and the branch rule is *"only `regression` gates; every other status is informational, never a silent pass but never a false gate"* | `src/commands/verify/main.md:242`, `:244`–`:252` |
| 14 | **How a fail-soft result reaches the verdict and the report.** `compute-verdict --regression` folds it: *"A regression (`regression:true` …) adds a blocker → NEEDS WORK, and never anything else"*. `render-report` takes **no** regression input — *"the regression result reaches `verification.md` only through the verdict's reasons/blockers"* — so `verification.md` has no dedicated regression section | `src/commands/verify/main.md:290`, `:43`, `:297`; `src/commands/verify/references/report-format.md:98` |
| 15 | **The declared-lane precedent, end to end (property tests).** Architect sub-question **8** names pure builders → `plan.md`'s conditional `### Pure-Builder Targets` subsection → `PureBuilderRow` on the plan handoff → `/devforge:breakdown` PHASE 3 renders a DEDICATED `qa-engineer` task with `--property-targets` → the `**Property targets**:` header line → PHASE 3.5's `verify-property-coverage` HARD gate matching on exact name | `src/commands/plan/main.md:391`, `:477`–`:485`; `src/devforge/lib/_plan/handoff_schema.py:239`–`:262`, `:336`; `src/commands/breakdown/main.md:359`–`:369`, `:529`; `src/devforge/storage-rules.md:154`, `:200` |
| 16 | **The ZERO-PYTHON carry precedent.** The dead-code kill-list is NOT surfaced by the handoff render: *"The `read-plan-handoff` seeds block above surfaces the decomposition seed sub-sections only — it does NOT carry the change-induced dead-code rows. Read those from `plan.md`'s `### Change-Induced Dead Code` table directly, the same `plan.md` this phase's no-handoff path and Phase 0 / Phase 1 read as the full source."* **So a plan→breakdown declaration can travel with no schema change at all** | `src/commands/breakdown/main.md:72`, `:101` |
| 17 | **The no-gate declaration precedent (plan 86 F3).** `Regression net:` is a fixed-prefix line in free-form `## Change Details`, and its own text states both bounds: *"NOTHING CHECKS the declaration: there is no Phase 3.5 gate for it, no `verify-*` verb, and no helper flag"*, and *"the TRIGGER RESTS ON A BELIEF, not on a measurement"*. It also states *"this lane adds NO flag and NO header field"* | `src/commands/breakdown/main.md:410`–`:419` |
| 18 | **`qa-engineer` is a real executor.** The Agent Assignment table's *"Dedicated test-authoring / coverage-gap task"* row routes to it; the separate-task rule fires *"ONLY when decomposition or the Phase-2 architect consult flags a coverage gap or a test-heavy acceptance criterion"*; and *"`qa-engineer` is `model_tier: do` — a valid implementer"*. ⚠ Its meta-block carries **no `tools:` key**, so it inherits the full tool surface (unlike `qa-reviewer`, which is locked to `Read, Grep, Glob, Bash`) | `src/commands/breakdown/main.md:274`, `:283`; `src/agents/qa-engineer.md:1`–`:6`; `src/agents/qa-reviewer.md:4` |
| 19 | **The config surface a new key must pass through — SIX files.** `FIELD_SCHEMA` (30 `(name, kind)` pairs), `ENUM_FIELDS`, `FIELD_DEFAULTS`; the setter in `_cmds_set.py`; the verb registration in `_cli.py`; `_PROJECT_CONFIG_KEY_ORDER` in `_render.py` (38 keys); the display group tuple in `_summary.py`; and `_cmds_verify.py`, which requires **every** field non-null with a THREE-name exemption set `_AC_RUNTIME_FIELDS` gated on `ac_verification_mode == "runtime-assisted"` | `_configure/_schema.py:18`–`:93`; `_cmds_set.py:526`; `_configure/_cli.py:306`–`:310`; `_render.py:19`–`:69`; `_summary.py:52`–`:61`; `_cmds_verify.py:19`–`:59` |
| 20 | **The defaulted-and-unasked-key precedent.** `regression_gate` is in `FIELD_SCHEMA`, has an enum `{off, full}`, a `FIELD_DEFAULTS` entry `"full"`, and a registered `set-regression-gate` verb — and **`/devforge:configure` never calls it**: it appears in neither the Phase-3 setter mapping (22 rows) nor the Phase-4 questions (Q9–Q12). ⚠ **AMENDED 2026-08-27 — the "undocumented" reading no longer holds; the "unasked" half does.** Plan 89's **D6** shipped a note in `configure/main.md` (anchor *"One emitted key is set by no phase of this command"*) naming the key, its `"full"` default, its `set-regression-gate` setter and its `/devforge:verify` PHASE-4.3 reader, so **the key IS documented in the command's own text as of 2026-08-27**. **The precedent this row supplies to D1's counter-argument stands byte-true**: still no Phase-3 setter-mapping row, still no Phase-4 question, and D6's note explicitly forbids adding one — what is corrected is only the reading that a defaulted-and-unasked key is also an unmentioned one | `_configure/_schema.py:69`, `:84`, `:92`; `_configure/_cli.py:306`; `src/commands/configure/main.md:208`–`:231`, `:274`–`:299`; `:316` (plan 89 D6, verified 2026-08-27) |
| 21 | ⚠ **A live count drift that a new field will make worse.** `_cmds_verify.py`'s docstring says *"All 30 configure.yaml fields populated"* and `FIELD_SCHEMA` holds 30 pairs; `configure/main.md` says *"fills 29 configuration fields"*, *"canonical state (29 fields)"*, *"37 keys: 29 from configure.yaml + 5 from init.yaml + 3 derived"*, and *"Once `configure.yaml` is fully populated (29 fields set)"* — while `_PROJECT_CONFIG_KEY_ORDER` holds **38**. **The markdown is one behind the code, presumably since `regression_gate` landed.** This plan does not own the drift, but Phase 1 touches exactly those counts | `_cmds_verify.py:28`; `_configure/_schema.py:18`–`:70`; `src/commands/configure/main.md:9`, `:13`, `:14`, `:303`; `_render.py:19`–`:69` |
| 21a | ⚠ **AMENDED 2026-08-27 — three corrections; the row above is no longer either complete or uniformly true.** **(i) A SIXTH count-bearing site now exists.** Plan 89's D6 note (anchor *"One emitted key is set by no phase of this command"*) states *"The schema carries 30 fields; the 29 this command populates are set in Phase 3 (23 detection-derived values) and Phase 4 (6 user-only prompts)"* — **the first in-file statement of the LIVE schema count.** So the file is **no longer uniformly one behind**: the *"fills 29 configuration fields"* / *"fully populated (29 fields set)"* statements are now **explained-correct arithmetic** under that note (23 + 6 = 29, the 30th set by no phase), while the TOTALS — *"canonical state (29 fields)"* and *"37 keys: 29 from configure.yaml + 5 from init.yaml + 3 derived"* — **remain behind the code (30 / 38).** **(ii) The four-site list above was INCOMPLETE at drafting**, independently of plan 89: the completion message is a FIFTH pre-existing count site (*"The 29 configuration fields are persisted"*, *"carries all 37 keys"*). **(iii) Consequence for THIS plan.** Phase 1's `e2e_command` falsifies the D6 note's numbers too — schema → **31**, and if `/devforge:configure` seeds the field (D1's seeding step) the populated and detection-derived counts move as well. ⚠ **Phase 5's opening `grep -rn "e2e\|E2E"` sweep does NOT reach that note** — it carries no `e2e` token — so it must be reconciled **EXPLICITLY**, **updated in place and never deleted**: it is plan 89's ratified D6 deliverable, not incidental prose. **⚠ RECONCILED 2026-08-27 (Phase-0 close) — the conditional in (iii) is now DETERMINATE.** D1's ratified seeding arm HAS `/devforge:configure` compose the default, so the D6 note's arithmetic moves on BOTH terms: its Phase-3 figure goes **23 → 24 detection-derived values** and its populated total **29 → 30**, against a schema of **31**. **The instruction is unchanged and binds harder — COUNT the live file at every one of the six sites and write what you counted; never increment a printed number**, these three figures included | `src/commands/configure/main.md:9`, `:13`, `:14`, `:303`, `:316`, `:483`; live grep 2026-08-27 |
| 22 | **The don't-guess rule this plan must mirror**, verbatim: `test_command` is *"`MANIFESTS_JSON.packages[<path>].scripts.test` (or the ecosystem-equivalent test script). `null` when the package has no test script — do NOT invent an ecosystem-default guess."* | `src/commands/configure/main.md:134` |
| 23 | **PHASE 3.5 holds exactly six `verify-*` gates today**, and its opening line says so — *"Six forcing-functions walk the task set mechanically."* They are `verify-contract-chain`, `verify-ac-coverage`, `verify-agent-roster`, `verify-manifest-present`, `verify-property-coverage`, `verify-dead-code-coverage`. The first two carry a documented `## Risk Assessment` deferral; the last four are HARD with **NO bypass**. **Plan 75's tripwire counts THIS sequence**, not prose checklists | `src/commands/breakdown/main.md:477`–`:479`, `:484`, `:494`, `:504`, `:517`, `:529`, `:544` |
| 24 | **`/devforge:summarize` reads only `verification.md`** for AC status and the referenced verdict (`read-verification`), takes *"AC status … VERBATIM from `verification.md`'s table"*, and is *"Read-only on inputs"* | `src/commands/summarize/main.md:127`, `:133`, `:213`, `:214` |
| 25 | **`/devforge:verify`'s frontmatter is three keys** — `name`, `description`, `argument-hint` — with **no `allowed-tools`**. So the command already invokes every `verify_helper` verb without a pre-approval grant | `src/commands/verify/main.md:1`–`:5` |
| 26 | **Constitution §3.4 Testing Requirements is `[project-specific]`**, holding only `- **Framework**: {{TESTING}}` plus a multi-stack note, and it is **NOT** in `_UNIVERSAL_SECTIONS` (`"§3.5", "§3.6", "§3.7", "§3.8", "§4.1", "§4.2", "§4.3", "§6.1", "§6.2", "§6.3", "§6.4"`). A §3.4 edit would therefore NOT trip the universal-defaults drift check — and a §3.6 edit would, as plan 86 recorded | `src/constitution.md:55`–`:60`; `_constitute/_schema.py:296`–`:300` |
| 27 | `CHANGELOG.md` carries a `## [Unreleased]` section whose first subsection is `### Added` | `CHANGELOG.md:8`, `:10` |
| 28 | **`src/CLAUDE.md`'s `### Always` list held 15 items on 2026-08-26**, item 15 being *"English in files"*; its `### Verification (explicit, scope-aware — no per-edit hooks)` section describes the scope-aware flow in six numbered steps and closes *"Full specification in `/devforge:implement`."* ⚠ **This count is a dated observation with a KNOWN mover: plan 89 appends to that list.** Every use of it in this plan is a count-live instruction, never the literal 15. ✅ **AMENDED 2026-08-27 — the known mover MOVED.** Plan 89's Phase 4 appended item **16**, *"**Test behavior changes** — every change to observable behavior ships with a test that asserts it; the configured test command must pass on changed files before task completion"*, as a pure append leaving items 1–15 byte-identical (item 15 is still plan 87's *"English in files"*). **The list holds SIXTEEN items as of 2026-08-27** — and every use of the count in this plan **remains a count-live instruction**, never the literal 16 either | `src/CLAUDE.md`, `### Always` + `### Verification`; `src/CLAUDE.md:222`–`:223` verified 2026-08-27 |

### Claude Code authoring surface, verified against current docs

Fetched 2026-08-26 from `https://code.claude.com/docs/en/slash-commands` (which redirects to
the skills page — custom commands were merged into skills, and the page states *"A file at
`.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create
`/deploy` and work the same way. Your existing `.claude/commands/` files keep working."*).
**Cited here so a future author re-verifies rather than trusting this file.**

- **`allowed-tools` is a PRE-APPROVAL grant, not a restriction.** Verbatim: *"Tools Claude
  can use without asking permission during the turn that invokes this skill. The grant
  clears when you send your next message."* **Consequence: fact 25 is not a defect, and
  Phase 4 owes no `allowed-tools` line** — adding one would remove a permission prompt and
  nothing else.
- **`disallowed-tools` is the restricting field**: *"Tools removed from Claude's available
  pool while this skill is active."* This plan proposes none.
- **`description`**: *"What the skill does and when to use it. Claude uses this to decide
  when to apply the skill. … the combined `description` and `when_to_use` text is truncated
  at 1,536 characters in the skill listing to reduce context usage."* **Consequence for
  OQ-6: any widening of `/devforge:verify`'s description competes for that budget.**
- **`disable-model-invocation`**: *"Set to `true` to prevent Claude from automatically
  loading this skill."* Default `false`. `/devforge:verify` does not set it and this plan
  does not change that — **plan 63's 13/7 counts take no delta from this plan** (OQ-6).
- **There is NO frontmatter field that restricts which files a command may write.** The
  field list is `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`,
  `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`,
  `metadata`, `license`, `compatibility`. **So every scoping claim this plan makes is
  enforced by helper contracts or by prose, never by the Claude Code surface.**

---

## Decisions — ALL RATIFIED 2026-08-27

Each carries the rule, the alternatives, the reasoning, and the strongest counter-argument.
**The counter-arguments are load-bearing: a decision ratified with its counter-argument
deleted cannot be re-opened honestly later.** **Each entry now opens with its dated
ratification paragraph; every recommendation, alternative and counter-argument below it
survives unedited.**

### D1 — Where the e2e command lives: one top-level `E2E_COMMAND` key *(RATIFIED 2026-08-27 — top-level key; seeding composed by `/devforge:configure`)*

**RATIFIED 2026-08-27 — the single top-level `E2E_COMMAND` key, as recommended.** Alternative
(b), a per-package field, stays the recorded widening path and is NOT built; alternative (c),
no key at all, stays rejected. **The load-bearing constraint ratifies with it:** the key stays
INVISIBLE to `verify-touched` and to `regression-gate`, which is a mechanical consequence of
facts 5 and 6 rather than a promise.

**⚠ The seeding fork was ALSO picked, and it does NOT match this decision's drafted seeding
sentence.** Phase 1's Deliverable 2 offered three arms; **the THIRD was ratified**:
`/devforge:configure` composes the field's default from the `MANIFESTS_JSON` manifests it
already parses — the same `devDependencies` it reads for `test_command` — inheriting fact 22's
*"do NOT invent an ecosystem-default guess"* rule verbatim. **Consequences, stated so no phase
re-derives them:** nothing reads `.devforge/init.yaml`'s `test_infra.e2e`; **Phase 1 does NOT
touch `init_helper`**, whose detector stays exactly as unused as it is today (fact 8) —
**honest rather than tidy**; and fact 9's unreachable `e2e` bucket value stays recorded and
unrepaired.

⚠ **Where the composition text is actually written — 2026-08-27, so this paragraph is not
read as covering it.** This decision names the ARM; it writes none of the instruction. The
seeding arm is **three instruction-only sites inside `configure/main.md`** — a compose rule,
a bulk-confirmation echo-template line, and the setter-mapping row — enumerated at **Phase
5's `configure/main.md` scope bullet**, which is where a builder must look. **A build that
adds only the setter row ships a field that stays `""` forever, which is alternative (c) by
another route.**

*The counter-argument below is ACCEPTED, not answered:* the six-file Python surface (fact 19)
is the real cost of this arm, and it is why Phase 1 is a Python phase with its own review loop.

**RECOMMENDED RULE.** A single top-level config key, `E2E_COMMAND` (`e2e_command` in
`configure.yaml`), holding the one command that runs the project's e2e suite. Empty string
when the project has none. **The load-bearing constraint, and it decides the shape:
the key must be INVISIBLE to `verify-touched` and to `regression-gate`.** Both read only
`PACKAGE_STACKS[].test_command` and `TEST_COMMANDS[0]` (facts 5, 6), so a new top-level key
is read by neither — the per-task path and the regression gate keep their current behavior
byte-for-byte, and that is a mechanical consequence rather than a promise.

**Why one key rather than one per package:** an e2e suite is a property of the deployed
product, not of a package. A monorepo with a web app, an API and a shared library has one
set of user flows, and Playwright's own model already owns process orchestration for the
whole app (its `webServer` block starts what the suite needs — D6). A per-package field
would ask the configurer to answer "what is this package's e2e command?" for packages
where the honest answer is "the product's, not mine."

**Seeding, and this is where the dead detector finally gets a consumer.** `/devforge:configure`
composes the default for this field from `.devforge/init.yaml`'s `test_infra.e2e` value —
which means Phase 1 must ALSO make that value real, because today no command populates it
(fact 8). **The don't-guess rule is inherited verbatim from `test_command`** (fact 22): when
detection yields nothing, the field is empty and no ecosystem default is invented. A
project that runs Playwright through a non-obvious script gets it from the user, not from a
guess.

⚠ **SUPERSEDED 2026-08-27 by Phase 0's ratified seeding arm — read the preceding paragraph as
the drafting-time proposal, never as the live rule.** Its bolded lead and its first sentence
do NOT survive: `/devforge:configure` composes the default from the **`MANIFESTS_JSON`
manifests it already parses**, not from `.devforge/init.yaml`'s `test_infra.e2e`, and
**Phase 1 therefore does NOT make that value real and does NOT touch
`init_helper`** — the detector stays unused and
`test_infra.e2e` stays empty on every install. **The paragraph's last two sentences survive
unchanged and are the whole point of the arm**: fact 22's don't-guess rule is inherited
verbatim, so an empty detection yields an empty field and the user supplies the command. **The
dead detector does NOT get a consumer** — that clause is retired with the arm it belonged to.

**Alternatives considered:**

- *(b) A per-package `e2e_command` inside `PACKAGE_STACKS`.* Recorded as the real
  alternative and as the **named widening path** if a monorepo turns out to need per-app
  suites. NOT recommended for v1: the 8-key record shape is asserted at **three** sites in
  `configure/main.md` alone (fact 4) plus the schema and the bulk `set-package-stacks`
  validator, every one of which would move to nine keys, and every record would carry one
  more `null` for the overwhelmingly common single-suite case.
- *(c) No config key at all* — the e2e command is named in the plan's declaration and
  carried into the task, with no execution seat. **REJECTED, but note what it costs:** it
  collapses D3 entirely, because `/devforge:verify` would have no command to run. A
  ratifier who wants a declaration-only v1 should decline D3 explicitly rather than reach
  it through D1.

*Counter-argument, recorded:* the Python surface is not small. A new scalar field passes
through **six files** (fact 19), and `_cmds_verify.py` requires every `FIELD_SCHEMA` field
to be non-null, so `e2e_command` must join an exemption path or every existing install
fails `configure_helper verify` the moment it upgrades. **Accepted as the real cost**, and
it is why Phase 1 is a Python phase with its own review loop rather than a footnote. The
mitigation is fact 20's precedent: `regression_gate` shows the repo already ships a
config key that has a default, has a setter, and is never asked about — so the *question*
surface can stay at zero even when the *field* surface does not.

### D2 — The declaration point: a plan-side architect sub-question *(RATIFIED 2026-08-27 — as recommended)*

**RATIFIED 2026-08-27 — as recommended**: architect **sub-question 12** at `/devforge:plan`
§1.3, feeding a conditional `### E2E Scenarios` subsection in `plan.md`, carried to
`/devforge:breakdown` with **ZERO Python** by reading the table from `plan.md` directly.
Alternative (a), spec-side only, and alternative (b), breakdown-side only, stay rejected as
recorded. **The honest bound ratifies with the rule and must reach the emitted bracket text:
nothing checks the declaration — the claim is visibility, not enforcement.** *The
counter-argument is ACCEPTED, not answered:* a twelfth sub-question is added to a list of
eleven with no evidence about its marginal cost, because plan 84 closed having found
architect-consult accumulation unmeasurable.

**RECOMMENDED RULE.** `/devforge:plan` §1.3 gains architect **sub-question 12**: which
acceptance criteria describe a user-visible flow that only a full-stack run can verify, and
what is the minimal scenario that exercises each. The answer is verbatim-ready rows for a
new conditional `plan.md` subsection, `### E2E Scenarios`, following the shape every other
conditional subsection there already uses (fact 15): included only when the sub-question
returned ≥1 row, omitted heading-and-table otherwise. **A feature with no such AC returns
nothing and the subsection does not exist.**

**This is the property-test lane's shape, minus its gate** (facts 15, 17). It is chosen
over the alternatives because it is the only option that produces an OWNER: a row in
`plan.md` is what `/devforge:breakdown` turns into a task with an assigned agent.

**It also gives `architect.md`'s `qa-engineer` consult row its first consumer.** That row
names *"integration/e2e strategy decision, shared fixtures, explicit coverage requirement"*
as reasons to consult, and the orchestrator-mediated relay that would carry the answer back
exists and lists `qa-engineer` among the namable specialists — but **no sub-question asks
for it, no `plan.md` subsection holds it, and no task field carries it** (fact 11).
Sub-question 12 is where the answer lands.

**The carry to `/devforge:breakdown` is ZERO-Python** (fact 16): `/devforge:breakdown` reads
the `### E2E Scenarios` table **directly from `plan.md`**, exactly as it already reads the
`### Change-Induced Dead Code` table, rather than through a new `BreakdownSeeds` field. This
is the whole reason Phase 2 and Phase 3 are instruction-only.

**Alternatives considered:**

- *(a) Spec-side only* — an AC subsection naming e2e coverage. Cheaper and closer to where
  user flows are described, but it produces no task and no owner: `/devforge:specify` writes
  no assignment and `/devforge:breakdown` decomposes from the plan. **REJECTED** — a
  declaration nobody owns is a wish.
- *(b) Breakdown-side only* — decide at decomposition which tasks need e2e coverage.
  REJECTED for the reason plan 86's F3 gives for its own placement: decomposition is
  downstream of the design decision, and by then the argument for whether a flow *needs* a
  full-stack run has already been had implicitly.

**⚠ Honest bound, and it must appear in the emitted text:** without D4's gate, the declared
scenario list is checked by nothing. A plan that declares three scenarios and a task set
that covers none produces no error. **The claim is visibility, not enforcement** — the same
claim, in the same words, that `Regression net:` already makes (fact 17).

*Counter-argument, recorded:* sub-question 12 makes the architect brief longer on every
feature, including the many with no e2e-shaped AC, and plan 84 already closed having found
architect-consult accumulation unmeasurable (its `U` metric never computed — no install had
≥5 completed plans). **Accepted:** this plan adds a twelfth sub-question to a list of
eleven and can offer no evidence about the marginal cost, because none exists. The
mitigation is that the empty answer is one word and the subsection is omitted, so a non-web
feature pays one question and nothing else.

### D3 — The execution seat: a fail-soft `/devforge:verify` sub-phase *(RATIFIED 2026-08-27 — advisory fork (i), reasons-only)*

**RATIFIED 2026-08-27 — fork (i): NO status gates the verdict in v1.** The new fail-soft
PHASE 4.5 ships as recommended, always exiting 0, with the four statuses unchanged. Fork (ii),
an `e2e-failing` NEEDS-WORK blocker, stays the recorded alternative and **the strengthening
trigger stays exactly as named** — the first e2e-catchable defect that reaches a consumer
DESPITE an `e2e-failing` status having been surfaced. That trigger is an OBSERVATION; a build
that flips the arm on reasoning has left this plan.

**The reporting sub-question was resolved in the same breath, as recommended: REASONS-ONLY.**
`compute-verdict` gains an `--e2e` input that adds a `reasons` line and **NO blocker**;
`render-report` takes no e2e input and is unchanged; **`verification.md` gains no dedicated
e2e section** — the same shape the regression gate already has (fact 14). This is the minimum
change that leaves a durable trace, and it is what makes OQ-6's answer determinate rather than
conditional.

⚠ *The counter-argument below is the strongest one against this plan, and ratification
ACCEPTS it rather than answering it:* **a lane that runs a suite, watches it go red and
approves the feature anyway produces a green verdict beside a red suite in the same run.**
Phase 6's anchor 3 is where a ratifier meets that in a real run, and the repair is fork (ii).

**RECOMMENDED RULE.** A new sub-phase **`/devforge:verify` PHASE 4.5 — e2e run**, invoking a
new `verify_helper e2e-gate` verb that runs `E2E_COMMAND` **once, at HEAD, in the real
`source_root`** — never in a worktree, never at the merge-base. It is built in the
`regression-gate` mould (fact 13): **it ALWAYS exits 0**, and it emits a `status` field the
orchestrator branches on:

- **`off`** — no `E2E_COMMAND` configured. Note nothing; do not gate. (D8.)
- **`inconclusive`** — the command could not be executed (missing binary, timeout, non-test
  failure signal). Surface the `note`; do not gate.
- **`e2e-clean`** — the suite ran and passed. Note it; do not gate.
- **`e2e-failing`** — the suite ran and failed. Surface the failing-output tail; **do not
  gate in v1.**

**Fork — does any status gate the verdict?** RECOMMENDED: **(i) NO status gates in v1.** The
result reaches the user through the in-run surface and the verdict's `reasons` prose, and
`compute-verdict` gains no new blocker. **(ii) `e2e-failing` adds a NEEDS-WORK blocker**,
exactly as `regression:true` does (fact 14), is the recorded alternative.

The argument for (i) is threefold and none of the three is aesthetic:

- **Plan 75's tripwire.** v1 adds a mode and a report, not a gate. A fail-soft verb that
  can only ever exit 0 is not a hard-fail validator.
- **Plan 85's D8 concern applies before plan 85 has even ratified.** Two mandatory
  adversarial stages already sit in sequence there; adding a third blocking stage here,
  from a plan with **no incident behind it**, decides a cost question by accretion instead
  of once.
  ⚠ **CORRECTED 2026-08-27 — plan 85 has since ratified and shipped (DONE build
  2026-08-26); see `## Dependencies + related`'s plan-85 bullet. The correction STRENGTHENS
  this reason — the D8 concern is now ratified law, not a sibling proposal — it does not
  weaken it.**
- **e2e suites are the flakiest test tier there is** (OQ-4), and this plan builds no
  retry, no quarantine and no flake accounting. A blocking gate over an unaccounted flake
  source teaches its users to work around it, which is worse than not having it.

**The strengthening trigger is NAMED, so (i) is a decision rather than a deferral:** the
first e2e-catchable defect that reaches a consumer **despite** an `e2e-failing` status
having been surfaced. That is the shape plan 48 (shelve until an OBSERVED skip) and plan 87
(WARN until the first confirmed leak) both use. Until it fires, the arm stays advisory.

**⚠ Reporting is Python whichever fork wins, and the plan must not pretend otherwise.**
`render-report` has no e2e input and `verification.md` has no place to put one, exactly as
it has none for the regression gate (fact 14). Under (i) the e2e result therefore reaches
`verification.md` only by `compute-verdict` folding it into `reasons` — **a change inside
`compute-verdict`** — or not at all, in which case it lives only in the transcript. Phase 0
must say which; the recommendation is **reasons-only, no blocker, no new report section**,
which is the minimum change that leaves a durable trace.

*Counter-argument, recorded, and it is the strongest one against this plan:* a lane that
runs a suite, watches it go red, and approves the feature anyway is arguably worse than no
lane, because it produces a green verdict beside a red suite in the same run. **This is not
fully answered.** The partial answer is that `verification.md` records the verdict's
reasons and the transcript records the failure, so nothing is hidden — but a Phase-6
observer who sees APPROVED printed under a failing e2e run has found the real cost of (i),
and the repair is (ii).

### D4 — No new PHASE-3.5 gate in v1 *(RATIFIED 2026-08-27 — as recommended, no seventh gate)*

**RATIFIED 2026-08-27 — as recommended: NO seventh PHASE-3.5 gate.** The sequence stays at its
six `verify-*` gates (fact 23), and **plan 75's tripwire holds in both halves** — no new check
number, no new hard-fail validator. `verify-e2e-coverage`'s shape and its OBSERVED-dropped-
scenario trigger stay RECORDED, not built. ⚠ **The combination the pick-list warned about did
not arise:** D3 ratified fork (i), so no lane blocks a verdict on a suite whose existence
nothing checks. *The counter-argument is ACCEPTED, not answered:* a declared-but-uncovered
scenario is at least as easy to drop as a declared-but-uncovered pure builder, and this build
ships nothing that would notice.

**RECOMMENDED RULE.** The scenario-list-to-task reconciliation gate — a
`verify-property-coverage` clone that would fail decomposition when a declared `### E2E
Scenarios` row is covered by no task — is **deliberately NOT built.** PHASE 3.5 stays at
its current six `verify-*` gates (fact 23). The declaration rides the plan subsection and
the rendered task, and its absence is visible in the task set.

**Why**, and the reasoning is already in the repo: plan 86's F3 shipped precisely this
shape — an obligation to DECLARE, with no gate, and both bounds stated in the emitted text
(fact 17). Adding a seventh gate here would mean this plan's very first build introduces a
mechanical blocker for a lane with **zero observed failures**, and plan 75's tripwire reads
on both halves: no new check number, no new hard-fail validator.

**The strengthening path is named with its trigger**, so a future session does not have to
re-derive it: a `breakdown_helper verify-e2e-coverage` gate over an `**E2E scenarios**:`
task header field, modelled line-for-line on `verify-property-coverage`, triggered by the
first OBSERVED decomposition that dropped a declared scenario. **That trigger is an
observation, not a suspicion** — a build that adds the gate on the strength of "it could
happen" has left this plan.

*Counter-argument, recorded:* the property-test lane's gate exists precisely because a
declared-but-uncovered target is easy to produce and invisible afterwards, and an e2e
scenario is at least as easy to drop. **Accepted.** The reply is that plan 66's gate was
built alongside a lane whose obligation was mechanical (a named function either has a
property test or it does not), while an e2e scenario's coverage is a judgment about whether
a test exercises a flow — which a name-match gate would approximate by matching strings and
would then be satisfied by a task file that names the scenario and tests nothing.

### D5 — Who writes the tests: a dedicated `qa-engineer` task, and a web arm in two agents *(RATIFIED 2026-08-27 — dedicated-directory placement; section arm (a))*

**RATIFIED 2026-08-27 — the dedicated `qa-engineer` task as recommended, and BOTH forks picked
explicitly:**

- **PLACEMENT fork — the dedicated-e2e-directory rule.** E2e spec files go in a dedicated e2e
  directory that the package's ordinary test command does not match. **The runner-config
  exclude arm appears in NO emitted text** — not as an alternative, not as a parenthetical.
  A rule offering both would reintroduce the judgment call the fork exists to remove, at
  exactly the point where a wrong guess costs three self-repair rounds.
- **SECTION fork — arm (a): rename and widen.** `qa-engineer.md`'s `## Mobile Testing` heading
  becomes a wider testing-surface section carrying a mobile block and a web block, and
  **every existing mobile bullet survives byte-identical** (OQ-2). Arm (b), appending a second
  extra section, is declined — (a) keeps the unchartered-section divergence at one.

**The framework-selection rule ships VERBATIM as drafted** — escape-hatch-free, one mandatory
action plus a stop, blocked-not-guessed. *Two counter-arguments are ACCEPTED, not answered:*
**consumer-merge friction** — a rename touches a shipped agent file and consumers who
customized it meet a conflict at `update.sh` time, which is the recorded cost of (a) — and
**nothing checks the placement rule**: D4 builds no gate, so a misplaced e2e spec produces a
confusing red run at the next `/devforge:implement` task rather than an error.

**RECOMMENDED RULE.** When `plan.md` carries a non-empty `### E2E Scenarios` table,
`/devforge:breakdown` PHASE 3 creates at least one **dedicated `qa-engineer` task** covering
every declared scenario. This needs no new routing rule: the Agent Assignment table's
dedicated test-authoring row already exists and its separate-task trigger already names
*"a test-heavy acceptance criterion"* (fact 18) — an AC that only a full-stack run can
verify **is** one. The task carries **no new header field** (D4 builds no gate to consume
one), and the scenarios ride `## Change Details`, the same free-form section plan 86's
`Regression net:` line rides (fact 17).

**The framework-selection rule, stated with no escape hatch.** The task names the framework
by this single mandatory rule:

> Write the e2e tests in the framework the project's e2e configuration names. When that
> configuration is empty, the task is BLOCKED and says so — name the missing configuration
> and stop. Never choose a framework the project has not adopted.

**The recommendation of Playwright is a `/devforge:configure` DEFAULT, not an agent
behavior**, and it belongs to D1's seeding step: when detection finds Playwright, the
configured command comes from Playwright. When detection finds nothing, the field is empty
and the user supplies it (fact 22's rule, inherited). **The agent never picks.** This
separation is what keeps the rule escape-hatch-free: an agent rule reading "use the
detected framework, or Playwright, or …" would be exactly the OR-clause the meta-rule
forbids.

**The placement rule, and it is not cosmetic — it is what keeps D1's separation true of the
FILES as well as the KEY.** D1 makes `E2E_COMMAND` invisible to `verify-touched`, but that
covers the config key only. The e2e spec files the task WRITES are ordinary touched files:
`verify-touched` matches each to its package and runs that package's `test_command`
(fact 5). **Playwright and Vitest/Jest share the `*.spec.ts` convention**, so an unscoped
unit-test glob will happily pick up a freshly-authored e2e spec and execute it under the
wrong runner — which fails, is not a defect, and burns iterations of the helper-owned
self-repair cap of 3 (fact 5) on a task whose real work was correct. The task therefore
carries this single mandatory rule:

> Put the e2e spec files in a dedicated e2e directory that the package's ordinary test
> command does not match.

**Fork 2 — one action, no OR.** The alternative — leave the files where the unit glob
reaches them and add a runner-config exclude — is **recorded as the arm Phase 0 may ratify
instead**, not offered beside it: an exclude edits a config file the framework does not
own, in a syntax that differs per runner, and a rule offering both would be a judgment call
at exactly the point where a wrong guess costs three self-repair rounds. **Phase 0 picks
one; the emitted text states only the picked one.**

✅ **RESOLVED 2026-08-27 — Phase 0 ratified the dedicated-e2e-directory arm; this paragraph's
*"Phase 0 may ratify instead"* / *"Phase 0 picks one"* phrasing is drafting-time, superseded
by the RATIFIED lead paragraph above.** The runner-config exclude reaches no emitted text.

⚠ **This rule is authoring guidance, and nothing checks it.** D4 builds no gate, so a task
that writes `tests/e2e-flow.spec.ts` beside the unit specs produces no error — it produces a
confusing red run at the next `/devforge:implement` task. **Say the bound in the emitted
text; do not imply the placement is enforced.**

**Fork 1 — where the web arm goes in `qa-engineer.md`.** RECOMMENDED: **(a) rename and widen
the existing `## Mobile Testing` section** into a testing-surface section carrying both a
mobile block and a web block, over **(b) add a second extra section beside it.**

✅ **RESOLVED 2026-08-27 — arm (a) ratified**; the wording below stays recommendation-shaped
and is superseded by the RATIFIED lead paragraph above.

The reasoning is fact 3: `qa-engineer.md` already carries ONE section beyond the canonical
D-Skeleton, and `agents-AUTHORING.md` charters extra sections for `architect` and
`tech-writer` only. **(a) keeps the divergence at one section; (b) makes it two.** The
rename is citation-safe — the string `## Mobile Testing` occurs exactly once repo-wide —
and **every existing mobile bullet survives byte-identical** (OQ-2). `qa-reviewer.md` step
6 gets the mirror: a web-flow parity sentence beside the mobile-parity one, its existing
sentence unchanged.

*Counter-argument, recorded:* a rename touches a shipped agent file for a cosmetic reason,
and consumers who have customized `qa-engineer.md` will see it as a conflict at
`update.sh` time. **Accepted as a real cost**, and it is why the fork is a fork: (b)
appends and touches nothing existing, at the price of compounding an undocumented skeleton
divergence. A ratifier who weights consumer-merge friction above skeleton hygiene should
pick (b) deliberately.

### D6 — App lifecycle: the suite owns it, and `ac_runtime_*` stays uncoupled *(RATIFIED 2026-08-27 — as recommended)*

**RATIFIED 2026-08-27 — as recommended.** The suite owns the application lifecycle and the
framework starts nothing; `ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command`
stay a **separate, uncoupled channel** that PHASE 4.5 neither reads nor writes. The
future-unification note stays RECORDED, not built — and it stays pointed at
`ac_runtime_cli_command`, never at `E2E_COMMAND`. *The counter-argument is recorded in the
decision's own opening and stands:* one shared launch mechanism would be more coherent, and it
is declined on failure modes, not on cost.

**RECOMMENDED RULE.** **The framework never starts the application.** `E2E_COMMAND` is
invoked as a single command in `source_root` and the suite is responsible for whatever
process it needs — the Playwright `webServer` model, a `docker compose` wrapper, a `make
e2e` target. `/devforge:verify` PHASE 4.5 starts nothing, waits on nothing, and tears down
nothing.

**`ac_runtime_url` / `ac_runtime_api_base` / `ac_runtime_cli_command` stay a SEPARATE,
uncoupled channel in v1** (fact 12). They are read only by `read-ac-config` and used only
to compose the `ac-verifier` brief; PHASE 4.5 does not read them and does not write them.

**Why**, and the counter-argument is genuinely strong so it is stated first: the framework
already HAS a live-app concept, and one shared launch mechanism for "the running app" is
obviously more coherent than two. It loses on failure modes. `ac_runtime_*` feeds a
per-run OBSERVATION channel whose degradation path is already defined (an empty value or a
downed MCP reclassifies an AC to code-reading — fact 12). Coupling a test-suite runner to
it means an e2e failure and an AC-verification degradation become indistinguishable at the
config layer, and each channel inherits the other's outages. **Two channels with two clear
failure modes beat one channel with four.**

**Recorded for the future, not built:** if a later plan does unify them, the unification
belongs in `ac_runtime_cli_command`'s definition, not in `E2E_COMMAND` — that key already
means "how to launch the runtime" and would be the natural home.

### D7 — The wall-clock cost line *(RATIFIED 2026-08-27 — as recommended, structural cost line)*

**RATIFIED 2026-08-27 — as recommended: the cost line is STRUCTURAL.** One full e2e-suite
execution per `/devforge:verify` run — not per task, not per commit, not doubled — and the
three mechanical bounds ratify with it. *The counter-argument is ACCEPTED and not argued
away:* **a structural cost line with no number is exactly what plan 85's D7 was written to
prevent, and this plan reproduces the gap it was meant to close.** Plan 70's Phase-2 numbers
are the prerequisite and they do not exist, so **Phase 6's wall-clock anchor is the first
datum this plan family will ever have** — and it is owed even if it turns out uninteresting.

⚠ **One drafting-time clause inside this decision is corrected by the ratification.** The third
bound below reads *"Phase 0 sets the value (OQ-5)"*; **that is FALSE as ratified.** OQ-5
resolved as recommended, and its recommendation always placed the choice at **Phase 4** — a
separate constant in the new module, defaulted higher than 600, with its adequacy recorded at
Phase 6. **Phase 0 set no timeout value and none is owed from it.**

**RECOMMENDED RULE — stated because plan 85's D7 established that a plan adding a slow
stage owes one.** The cost this plan adds is **one full e2e-suite execution per
`/devforge:verify` run**, and nothing else. It is not per task (D3 rejects the
`/devforge:implement` seat), not per commit, and not doubled (the run is HEAD-only — the
merge-base half of the regression pattern is deliberately not reproduced, per `## Origin`).

**What can be said honestly about the number: nothing.** Per-command wall-clock figures do
not exist in this repo — plan 70 built the profiler and its Phase 2 real-run diagnosis is
deferred. So the cost line is structural, not numeric: **one suite run, once per feature,
at the last pipeline stage before summarization.**

**Three things bound it, all mechanical:**

- **`off` costs nothing.** A project with no `E2E_COMMAND` pays a config read (D8).
- **The run is advisory in v1** (D3 fork (i)), so it never triggers a re-run cycle. A
  blocking arm would multiply the cost by the number of NEEDS-WORK loops.
- **A timeout is inconclusive, not a hang.** Phase 4's verb inherits the `_TEST_TIMEOUT`
  discipline `regression-gate` already applies (fact 6); Phase 0 sets the value (OQ-5).

**The revival lever on unacceptable cost is scoping — a smaller declared scenario set, or
`E2E_COMMAND` pointed at a tagged subset — never a silent skip.** An arm that lets a run
decide for itself not to execute is the escape-hatch shape this repo forbids.

*Counter-argument, recorded:* a structural cost line with no number is exactly what plan 85
D7 was written to prevent, and this plan reproduces the gap it was meant to close.
**Accepted, and not argued away.** The honest position is that plan 70's numbers are the
prerequisite and they do not exist; Phase 6's consumer run is instructed to RECORD the
wall-clock delta as a number (its Verify block), which makes this the first plan in the
family that can close the gap with data instead of a promise.

### D8 — Greenfield and no-e2e-infra installs: silent at every seat *(RATIFIED 2026-08-27 — as recommended, silent at every seat)*

**RATIFIED 2026-08-27 — as recommended.** All four seat-level no-ops ship as specified:
`/devforge:configure` seeds the field empty and asks nothing, `/devforge:plan` omits the
subsection heading-and-table, `/devforge:breakdown` writes no table and no task and **no
"no e2e scenarios" line anywhere**, and `/devforge:verify` reports status `off` with no
user-facing note and no report line. **No nagging line is added at any seat.** *The
counter-argument is ACCEPTED, not answered:* a web project that genuinely should have e2e
coverage is never told, and **the reply is sub-question 12** — it fires on the ACs rather than
on the config, and D5's blocked-not-guessed rule surfaces the missing configuration at the
moment someone is about to write a test.

**RECOMMENDED RULE.** When a project has no e2e infrastructure and no configured
`E2E_COMMAND`, **the entire lane is a clean no-op at every seat**, and each seat's no-op is
specified rather than assumed:

- **`/devforge:configure`** — the field is seeded empty; no question is asked (fact 20's
  precedent), and no warning is printed.
- **`/devforge:plan`** — sub-question 12 returns nothing and the `### E2E Scenarios`
  subsection is omitted heading-and-table, exactly as `### Pure-Builder Targets` is
  (fact 15).
- **`/devforge:breakdown`** — no table, no task. **No "no e2e scenarios" line is written
  anywhere**, following the rule the tasks-index `**Design fidelity**:` line already states
  for a non-UI feature: *"OMIT the line entirely — do not emit a 'not a design feature'
  line."*
- **`/devforge:verify`** — status `off`, no user-facing note, no report line.

**No nagging, and the reason is not politeness.** `init_helper verify`'s existing
test-infra soft-warn (fact 8) is the anti-pattern in miniature: it fires on a state that is
correct for most projects and recommends a verb no command runs. A lane that tells a Python
CLI project it has no browser tests trains its user to ignore the pipeline's warnings.

*Counter-argument, recorded:* silence means a web project that genuinely should have e2e
coverage is never told. **Accepted.** The reply is that the telling belongs to
sub-question 12, which fires on the ACs rather than on the config — an architect looking at
a user-visible flow answers it whether or not any e2e infrastructure exists today, and
D5's blocked-not-guessed rule is what surfaces the missing configuration at the point where
someone is actually about to write a test.

---

## Open questions (OQ-N) — ALL RESOLVED 2026-08-27

### OQ-1 — CI wiring, and the spec's §5.4 *(RESOLVED 2026-08-27 — no CI claim)*

**RESOLVED 2026-08-27 — NO, as recommended.** The lane says nothing about CI and makes no CI
claim: this framework configures a local pipeline, writes no CI files and reads none.
**Phase 5's `CHANGELOG.md` entry must not imply CI coverage.**

Does the lane say anything about running the suite in CI? The question is not idle: the AC
schema `/devforge:specify` renders already has a CI subsection — `ci_pipeline` maps to
**`5.4 CI / pipeline`** in its `--subsection` enum (`src/commands/specify/main.md:639`,
`:652`) — so a spec CAN carry a CI acceptance criterion today.

**RECOMMENDATION: no, and record why.** This framework configures a local pipeline; it
writes no CI files and reads none. An e2e suite that runs at `/devforge:verify` and never in
CI is a real bound, and it is the same bound every other check here already has —
`verify-touched`, `regression-gate` and all six PHASE-3.5 gates run locally and nowhere
else. **Adding a CI claim would be the first one in the repo and would need its own plan.**
A §5.4 AC asking for e2e-in-CI is verified exactly as any other §5.4 AC is today (by the
`ac-verifier`, per the ratified mode), and this lane neither helps nor hinders it. Phase 5's
`CHANGELOG.md` entry must not imply CI coverage.

### OQ-2 — Mobile parity: beside, not instead *(RESOLVED 2026-08-27 — byte-identical)*

**RESOLVED 2026-08-27 — NO, as recommended: the mobile text survives BYTE-IDENTICAL** in both
`qa-engineer.md` and `qa-reviewer.md`. ⚠ **The two-arm phrasing below is now determinate**:
D5's SECTION fork ratified **arm (a)**, so the section is renamed and a web block is added
beside the mobile block — the fork-(b) clause describes an arm that was declined. Phase 3's
byte-comparison criterion is unchanged and is what pins this.

Does the new web arm change the existing Detox / XCTest UI / Espresso / `integration_test`
text?

**RECOMMENDATION: no — the mobile bullets survive BYTE-IDENTICAL**, in both `qa-engineer.md`
and `qa-reviewer.md` (fact 2). Under D5 fork (a) the section is renamed and a web block is
added beside the mobile block; under fork (b) a new section is appended. **In neither case
does a mobile sentence move.** Phase 3's verify criteria pin this with a byte-comparison,
because a rename is exactly the kind of edit that quietly reflows its neighbours.

### OQ-3 — Does `/devforge:implement` ever run the e2e suite? *(RESOLVED 2026-08-27 — the AGENT runs it, the HELPER does not)*

**RESOLVED 2026-08-27 — the AGENT runs the suite and the HELPER does not, as recommended.** No
new flag, no `verify-touched` branch, no per-task e2e execution. ⚠ **The bound below is now
determinate rather than conditional:** the answer holds **only under D5's ratified
dedicated-e2e-directory placement rule**, which Phase 0 picked — so *"the per-task path is
unchanged"* stays true of the CONFIG KEY by construction and true of the FILES only by
authoring discipline. **Two different kinds of true, and this build does not merge them.**

The `qa-engineer` task that WRITES the suite must run it at least once — an unrun test does
not count (`qa-engineer` Rule 4: *"Run tests after writing — unrun tests don't count"*). But
`E2E_COMMAND` is deliberately not `test_command`, so `verify-touched` will never execute it
(D1). What happens at PHASE 5 of that task?

**RECOMMENDATION: the AGENT runs it, the HELPER does not.** `qa-engineer` inherits the full
tool surface (fact 18), so it runs the suite itself as part of authoring, and reports the
result in its Completion Notes. **No new flag, no `verify-touched` branch, no per-task e2e
execution.**

**⚠ The runner collision, named explicitly the way OQ-4 names flakiness — this answer is
BOUNDED, not unconditional.** `verify-touched` will see the new spec files, match them to
their package, and run that package's ordinary `test_command` (fact 5). That is correct
**only under D5's placement rule** — e2e specs in a dedicated directory the unit-test glob
does not match. Without it, the shared `*.spec.ts` convention between Playwright and
Vitest/Jest means the unit runner picks up an e2e spec, fails on it, and spends the
helper-owned self-repair cap of 3 (fact 5) repairing a non-defect. **So the sentence "the
per-task path is unchanged" is true of the CONFIG KEY by construction (D1) and true of the
FILES only by authoring discipline (D5)** — two different kinds of true, and conflating
them is how this lane would ship a per-task failure mode it never budgeted.

**⚠ The second honest bound:** the e2e suite's first HELPER-run execution is at
`/devforge:verify` PHASE 4.5, one or more tasks later. A suite that passes when the agent
runs it and fails later is a real sequence, and D3's advisory arm is where it surfaces.

### OQ-4 — Flakiness: retries, quarantine, accounting *(RESOLVED 2026-08-27 — out of scope, and load-bearing for D3)*

**RESOLVED 2026-08-27 — explicitly OUT OF SCOPE for v1, as recommended.** No retry count, no
quarantine list, no flake-rate accounting: the lane runs the configured command once and
reports what it returned. **This answer is load-bearing for D3's ratified fork (i)** — an
unaccounted flake source is one of the three reasons the v1 arm is advisory. ⚠ **The closing
clause below did NOT fire:** fork (ii) was not taken, so nobody took a gate without a flake
policy. **A future plan that proposes gating on `e2e-failing` owes one in the same document.**

**RECOMMENDATION: explicitly OUT OF SCOPE for v1, and recorded as such rather than left
unmentioned.** No retry count, no quarantine list, no flake-rate accounting, no
`--repeat-each`. The lane runs the configured command once and reports what it returned.

**This is load-bearing for D3**, not a footnote: an unaccounted flake source is one of the
three reasons the v1 arm is advisory. **A future plan that proposes gating on
`e2e-failing` owes a flake policy in the same plan** — and a ratifier who takes D3 fork
(ii) now is taking it without one.

### OQ-5 — The timeout value *(RESOLVED 2026-08-27 — separate constant, value chosen at Phase 4)*

**RESOLVED 2026-08-27 — as recommended: a separate constant in the new module, defaulted
higher than 600, with its VALUE chosen at Phase 4 and its adequacy recorded at Phase 6.**
`_regression._TEST_TIMEOUT` is never imported — two tiers, two tuning dials. **A timeout
produces `inconclusive`, never `e2e-failing`.** ⚠ **Phase 0 did NOT set the value**, and D7's
bullet claiming it does is corrected in D7's own ratification paragraph.

`regression-gate` caps each run at `_TEST_TIMEOUT = 600` seconds (fact 6). An e2e suite is
typically slower than a unit suite.

**RECOMMENDATION: a separate constant in the new module, defaulted higher than 600, with
its value chosen at Phase 4 and its adequacy recorded at Phase 6.** Do NOT import
`_regression._TEST_TIMEOUT` — the two tiers have different shapes and a shared constant
would couple two unrelated tuning dials. **A timeout produces `inconclusive`, never
`e2e-failing`**: a suite that ran out of clock has not reported a defect, and conflating
the two would put a false failure in front of the user under D3 fork (ii).

### OQ-6 — Does the e2e result reach `/devforge:summarize` or `/devforge:finalize`? *(RESOLVED 2026-08-27 — through `verification.md`'s reasons only)*

**RESOLVED 2026-08-27 — only through `verification.md`, as recommended, and the condition is
DISCHARGED: D3 ratified the reasons-only arm**, so the e2e status DOES land in the verdict's
`reasons` and is visible to `/devforge:summarize` for free. **No `summarize_helper` verb
changes, no `/devforge:finalize` change, and no widening of `/devforge:verify`'s frontmatter
`description`** — so the 1,536-character skill-listing budget is untouched and **plan 63's
13/7 counts take no delta from this plan.**

**RECOMMENDATION: only through `verification.md`, and only if D3's reasons-only arm
ratifies.** `/devforge:summarize` reads `verification.md` and nothing else, takes AC status
verbatim from it, and is read-only on its inputs (fact 24). So if the e2e status lands in
the verdict's `reasons`, it is visible to `/devforge:summarize` for free and needs no
change there; if it does not, `/devforge:summarize` never sees it. **No `summarize_helper`
verb changes, no `finalize` change, and no widening of `/devforge:verify`'s frontmatter
`description`** — which also protects the 1,536-character skill-listing budget the docs
name (verified above).

### OQ-7 — Naming: `E2E_COMMAND` vs a tier-neutral name *(RESOLVED 2026-08-27 — `E2E_COMMAND`)*

**RESOLVED 2026-08-27 — `E2E_COMMAND`, as recommended**, on consistency with the only
test-tier vocabulary the codebase already uses. **The naming is settled and is not
re-litigated at Phase 1**: the tier-neutral alternatives were considered and declined on
consistency grounds, not because "e2e" is the more exact word.

The key could be named for the tier (`E2E_COMMAND`) or for the property
(`FULL_STACK_TEST_COMMAND`, `INTEGRATION_TEST_COMMAND`).

**RECOMMENDATION: `E2E_COMMAND`**, because "e2e" is the term the codebase already uses in
its only test-tier vocabulary — `init_helper`'s bucket name, its `--e2e` flag, the
`test_infra.e2e` field, and both agents' `E2E frameworks` bullets (facts 2, 7). **Consistency
with the existing vocabulary beats a more precise word nobody here uses.** ⚠ Recorded so
the naming is not re-litigated at Phase 1: the alternative was considered and declined on
consistency grounds, not because the term is exact.

---

## Phases

### Phase 0 — Ratification *(doc-only)* — **CLOSED 2026-08-27**

**Objective:** ratify or amend D1–D8 and answer OQ-1–OQ-7, recording each answer in this
file with its reasoning. **Nothing else may start.**

**✅ CLOSED 2026-08-27 — see `## Phase 0 close record` below. Phases 1, 2, 3, 4 and 5 are
cleared to build; Phase 6 stays a deferred user-driven HARD GATE.** The pick-list below is
retained as the record of what needed an explicit answer, **and every item on it got one** —
four as picks between named arms, and the fifth (**D4**) as the combination warning it always
was, which did not arise because D3 ratified fork (i).

Five items need an explicit pick rather than a nod, because each has a named fork whose
arms lead to different builds:

- **D1's fork** — one top-level key vs per-package. Picking (b) changes Phase 1 from a
  six-file edit to a schema-and-three-doc-sites edit and should be taken deliberately.
- **D3's fork** — advisory (i) vs gating (ii). **This is the plan's central question.**
  Taking (ii) means taking it without OQ-4's flake policy, and the ratifier should say so.
- **D4** — a Phase-0 that ratifies D4 while ratifying D3 fork (ii) has produced a lane that
  blocks the verdict on a suite whose existence nothing checks. **That combination is
  coherent but should be chosen, not fallen into.**
- **D5's section fork** — rename the existing `## Mobile Testing` section vs append a
  second one.
- **D5's placement fork** — the dedicated-directory rule vs the runner-config exclude.
  **Only ONE reaches the emitted text**, and the choice decides whether a freshly-authored
  e2e spec can be swept up by the package's unit-test glob and burn `/devforge:implement`'s
  self-repair cap on a non-defect (OQ-3's bound).

**Verify:**

- `grep -n "^### D[1-8] " 90-E2E-TEST-LANE-PLAN.md` returns eight lines and **every one
  carries a ratification marker with a date** — no `*(OPEN)*` remains anywhere in the file.
- `grep -n "^### OQ-[1-7] " 90-E2E-TEST-LANE-PLAN.md` returns seven lines, each with a
  recorded answer.
- **Every decision still carries its counter-argument.** A ratified decision with its
  counter-argument deleted cannot be re-opened honestly.
- The status line at the top names the ratification date and which phases are cleared.
- **D3's fork is resolved by a stated pick, not by silence**, and if (ii) is chosen, OQ-4's
  out-of-scope answer is re-opened in the same breath rather than left standing.
- **The no-incident framing survives ratification.** A Phase 0 that upgrades this plan's
  origin from a question to a finding has changed the evidence base and must say where the
  finding came from.

---

## Phase 0 close record

**Ratified 2026-08-27 by the maintainer, in-session, answering the four explicit picks
directly; everything off the pick-list ratified as recommended.** No item was amended,
deferred or declined except where a decision's own recommendation was to decline (D4's
seventh gate, D5's runner-config exclude arm and its section arm (b), D1's alternatives (b)
and (c), D3's fork (ii)) — **those declines ARE the recommendation, not a departure from it.**

**The four picks, as answered:**

| Pick | Answer |
|---|---|
| D3's fork, and its reporting sub-question | **fork (i) — advisory, no status gates the verdict in v1** — with reporting **reasons-only**: `compute-verdict` gains an `--e2e` input adding a `reasons` line and NO blocker, `render-report` unchanged, no new `verification.md` section |
| D1's arm, and its seeding fork | **one top-level `E2E_COMMAND` key**, seeded by the **THIRD arm** — `/devforge:configure` composes the default from the `MANIFESTS_JSON` manifests it already parses; **`init_helper` untouched**, `test_infra.e2e` read by nothing |
| D5's placement fork | **the dedicated-e2e-directory rule** — the runner-config exclude arm reaches NO emitted text |
| D5's section fork | **arm (a)** — rename and widen `## Mobile Testing`, every mobile bullet byte-identical (OQ-2) |

**The fifth pick-list item was never a fork, and its warning did not fire.** **D4** asked that
a Phase 0 ratifying "no gate" alongside D3 fork (ii) choose that combination deliberately.
**D3 ratified fork (i)**, so the combination did not arise: nothing here blocks a verdict on a
suite whose existence nothing checks. **Recorded as not-fired rather than left ambiguous.**

**One consequence of the D1 seeding pick reaches beyond D1 and is written where it lands:**
the drafted seeding sentence inside D1 and the `## What is actually being added` clause
*"seeded from the detection that already exists and is currently discarded"* both describe the
arm that was NOT taken. **Both carry a dated note at their own site** — D1's marked
`SUPERSEDED`, the summary clause marked `CORRECTED` — and **Phase 1's Deliverable 2 carries
the resolution.** A future session must not re-derive the `init_helper` route from any of them.

⚠ **One sentence this record does NOT discharge, named so it is not read as discharged.**
Phase 2's route paragraph says *"Phase 0 confirms that reading rather than this sentence being
taken as license"* — the reading being that a `plan/main.md` edit touching no frontmatter owes
no claude-code-guide pass. **That reading was NOT among the ratified items and this closure
does not confirm it.** It stands as a **build-time obligation on Phase 2's route**, to be
settled when Phase 2 runs, exactly as Phase 3's parallel meta-block reading is.

✅ **RESOLVED 2026-08-27 (orchestrator ruling; site list WIDENED the same day to all four
command specs) — the entry above is DISCHARGED, and this record carries no undischarged
item.** The ruling was decided from **plan 89's two precedents**, not from the drafted
sentence, and **the CONSERVATIVE reading binds**: **EVERY command-spec `main.md` edit in this
plan owes a claude-code-guide pass — Phase 2's `plan/main.md`, Phase 3's `breakdown/main.md`,
Phase 4's `verify/main.md` (Deliverable 3) and Phase 5's `configure/main.md`** — because all
four ship into `.claude/commands/devforge/`, plan 89's Phase 3 ran the pass for this same
body-only class, and **the repo rule carries no frontmatter carve-out.** `src/CLAUDE.md`
already owed it and still does. **Phase 3's `qa-engineer.md` / `qa-reviewer.md` edits keep the
recorded-skip route only while their fenced `yaml` meta-blocks stay byte-unchanged** (plan
89's Phase 2b precedent), **with the skip reason recorded rather than silent** — that half is
unchanged by the widening. ⚠ **This is an orchestrator ruling at Phase-0 close, not a ratified
D-item** — it changes no decision, no OQ and no marker, and **it widens the route, never the
scope.** The notes live at the route paragraphs of **Phases 2, 3, 4 and 5**, each phase's
**Verify block**, and **`## When resuming work` step 7**.

**What ratification did NOT change — recorded so a future session does not read closure as
scope growth:**

- **Every counter-argument survives verbatim.** D3's green-verdict-beside-a-red-suite
  objection, D5's consumer-merge-friction objection, D7's no-number objection, D2's
  architect-brief-accumulation objection, D4's easy-to-drop-scenario objection and D8's
  never-told objection are **accepted costs, not answered ones**. A ratified decision whose
  counter-argument was deleted could not be re-opened honestly, and none was.
- **Plan 75's tripwire still holds, both halves**: zero gates, zero new `verify-*` numbers,
  zero hard-fail validators, zero new agents, zero new verdict values. **The lane adds a MODE
  and a REPORT.**
- **Python is still Phase 1 and Phase 4's Deliverables 1–2 only.** The seeding pick keeps it
  there — composing a default inside `/devforge:configure` needs no `init_helper` change.
- **The no-incident framing survives.** There is still no incident behind this plan and none
  is claimed; it is still a **predicted-gap** plan in plan 87's class. **Ratifying a gap does
  not upgrade it from a question to a finding**, and no summary of this plan may imply a
  consumer failure.
- **The honest bounds are unchanged.** v1 gates nothing; nothing checks the declaration;
  nothing checks the placement rule; the lane is silent by default. **Ratifying a claim does
  not strengthen it.**
- **Phase 6 is NOT cleared.** It is a deferred user-driven HARD GATE with three known-answer
  anchors, two of them pair-scored. **Everything Phases 1–5 produce will be build-verified and
  NOT consumer-validated.**

---

### Phase 1 — The config key *(Python)*

**Route: python-engineer → python-reviewer, test-first.** No `.claude/`-shipping file
changes here, so no claude-code-guide pass is owed by this phase.

**Deliverable 1 — the field.** Under D1's recommended arm, `e2e_command` joins the config
surface across the six files fact 19 enumerates: `FIELD_SCHEMA` (as a `"scalar"`), the
setter in `_cmds_set.py`, the verb registration in `_configure/_cli.py`,
`_PROJECT_CONFIG_KEY_ORDER` in `_render.py` (emitting `E2E_COMMAND`), a display group in
`_summary.py`, and — **the one that fails closed if missed** — an exemption in
`_cmds_verify.py`, whose loop currently violates on any `None` scalar.

**⚠ Three build constraints, each a fact rather than a fork:**

1. **`e2e_command` is legitimately empty.** Most projects have no e2e suite (D8), so the
   field must not be required. **The two available styles are NOT symmetric, and the
   asymmetry decides it:** `_AC_RUNTIME_FIELDS`' conditional exemption is keyed on a
   discriminator — its three fields are exempt exactly when
   `ac_verification_mode != "runtime-assisted"` (`_cmds_verify.py:19`–`:21`, `:57`) — and
   **`e2e_command` has no analogous discriminator in this design**, so copying that shape
   would mean inventing a gating field this plan does not create. **A `FIELD_DEFAULTS`
   entry of `""` is therefore the structurally simpler default**, and Phase 1 takes it
   unless it finds a reason to add a discriminator, which it then states. **Do not invent a
   third style.**
2. **Nothing may make `verify-touched` or `regression-gate` see the key** (D1). Both read
   `PACKAGE_STACKS[].test_command` and `TEST_COMMANDS[0]` (facts 5, 6) and neither takes a
   new input in this phase.
3. **The count drift is pre-existing** (fact 21). `configure/main.md` says 29 fields / 37
   keys; the code says 30 / 38. Phase 1 makes them 31 / 39. **Phase 5 fixes the markdown to
   the LIVE number by counting, never by adding one to the printed number** — adding to a
   wrong number produces a differently wrong number.
   ⚠ **AMENDED 2026-08-27 — the count surface is now SIX sites, not four (fact 21a).** Plan
   89's D6 note is a sixth, and unlike the other five it states the LIVE schema count and its
   23 + 6 split, so **this build moves its numbers too.** **The instruction is unchanged**:
   count the live `FIELD_SCHEMA` and `_PROJECT_CONFIG_KEY_ORDER` tuples and write what you
   counted — never increment a printed number, at any of the six.

**Deliverable 2 — the detection actually runs.** `/devforge:configure` composes the seeded
default from `.devforge/init.yaml`'s `test_infra.e2e`, which is empty on every real install
today because no command populates it (fact 8). **Phase 0 must say which arm closes that**,
and the options are: `/devforge:init-forge` calls `detect-test-infra`; `/devforge:configure`
calls it; or `/devforge:configure` reads the manifests it already reads and composes the
default itself. **The third is the smallest** — `/devforge:configure` already parses
`MANIFESTS_JSON` for `test_command` (fact 22) and can read the same `devDependencies` — and
it leaves `init_helper`'s detector exactly as unused as it is today, which is honest rather
than tidy.

✅ **RESOLVED 2026-08-27 — Phase 0 picked the THIRD arm.** `/devforge:configure` composes the
`e2e_command` default from the `MANIFESTS_JSON` manifests it already parses, inheriting fact
22's don't-guess rule verbatim: no playwright/cypress evidence in the manifests means an empty
field and no invented default. **Three consequences bind this deliverable:** **(a)
`init_helper` is NOT touched by this phase** — no `detect-test-infra` call is wired in, no verb
is added, and its detector stays unreachable from every command (fact 8); **(b)
`.devforge/init.yaml`'s `test_infra.e2e` is read by nothing this build produces**, so it stays
empty on every install and the `/devforge:init-forge` route is not built; **(c) this
deliverable's own title is a drafting-time label** — what starts running is
`/devforge:configure`'s manifest read, **not "the detection"**, and a build that reads the
title as a mandate to make `init_helper` run has taken the arm Phase 0 declined.

⚠ **This phase writes NONE of the composition text — 2026-08-27, so this note is not read as
covering it.** The manifest-reading rule is instruction, not Python: it lives at **three sites
inside `configure/main.md`** enumerated at **Phase 5's `configure/main.md` scope bullet**.
**Phase 1 ships the FIELD** — schema entry, default, setter, render key, display group,
`verify` exemption — **and Phase 5 ships the COMPOSER.** A build that stops after this phase
leaves `e2e_command` permanently `""`.

**⚠ Recorded, not fixed:** the `e2e` bucket's value is unreachable in `_probe_tier.py`
(fact 9). **This plan does not repair that** — repairing it changes `/devforge:research`'s
probe-tier classification, which is a different command's behavior and needs its own
argument. Phase 1 must not "fix it while it's in there."

**Tests — written and RUN in the same turn as the code**, per repo discipline (every
function gets its own test that runs), and **round-tripped through the real producers,
never hand-authored fixtures**: a `render-config` → `project-config.json` → `read` round
trip proves the key lands under the right name, and a `configure_helper verify` test proves
an install with an empty `e2e_command` still passes.

**Verify:**

- python-reviewer clean; the `tests/lib/` configure suites green.
- **Every pre-existing configure test passes unchanged.** This phase adds tests; it edits
  none.
- **A test proves `configure_helper verify` exits 0 with `e2e_command` unset** (constraint
  1). An install that upgrades and then fails its own config check has shipped a
  regression to every consumer at once.
- **`grep -rn "e2e" src/devforge/lib/_implement/ src/devforge/lib/_verify/_regression.py`
  returns nothing** (constraint 2). Capture the pre-change output first — it is already
  empty, and that is the point.
- **The rendered `project-config.json` key order is deterministic** — a round-trip
  comparison of two consecutive `render-config` runs is byte-identical.
- `git status` shows zero files modified under `src/commands/` or `src/agents/` — this
  phase is Python-only.

---

### Phase 2 — `/devforge:plan` — the declaration *(instruction-only)*

**Route: instruction-author → instruction-reviewer.** `plan/main.md` ships into
`.claude/commands/devforge/`, but this phase touches no frontmatter, so the
claude-code-guide pass is not owed by this phase's edits — **Phase 0 confirms that reading
rather than this sentence being taken as license.**

⚠ **RESOLVED 2026-08-27 (orchestrator ruling) — the paragraph above is OVERRULED: this phase
DOES owe a claude-code-guide pass.** The ruling was decided at Phase-0 close from plan 89's
two precedents rather than from the drafted sentence, and **the CONSERVATIVE reading binds**:

1. **Command-spec BODY edits owe the pass.** `plan/main.md` here and `breakdown/main.md` at
   Phase 3 both ship into `.claude/commands/devforge/`, and **plan 89's Phase 3 ran the pass
   for exactly this class of body-only command-spec edit.** The repo-level rule — invoke the
   `claude-code-guide` agent per edit to a file shipping into a target project's `.claude/` —
   **has no frontmatter carve-out**, so *"touches no frontmatter"* exempts nothing.
2. **Agent-file edits keep the recorded-skip route, CONDITIONALLY.** Phase 3's
   `qa-engineer.md` / `qa-reviewer.md` edits may skip the pass **only while the fenced `yaml`
   meta-blocks stay byte-unchanged** — plan 89's Phase 2b precedent — **and the skip reason is
   RECORDED, never silent.** A meta-block edit voids the skip and the pass becomes owed.

**So this phase's route is instruction-author → instruction-reviewer → claude-code-guide**,
and the paragraph above survives only as the drafting-time reading it always was.

Scope, two files:

- **`src/commands/plan/main.md` §1.3** — architect **sub-question 12**, in the voice and
  return shape sub-questions 8 and 9 already use (fact 15): which ACs describe a
  user-visible flow only a full-stack run can verify, and one verbatim-ready table row per
  scenario. **Empty answers are EXPLICIT**, matching sub-question 9's `renders nothing
  unreachable` convention — silence is not an answer.
- **`src/commands/plan/main.md` PHASE 2** — the conditional `### E2E Scenarios` subsection,
  written in the exact bracketed-conditional shape its neighbours use (*"[Include this
  subsection ONLY if …]"* / *"Omit the entire subsection — heading and table — when …"*).
  **The bracket text must state the honest bound** (D2): each row becomes a decomposition
  obligation at `/devforge:breakdown`, and **no gate enforces it** — the contrast with
  `### Pure-Builder Targets`' bracket text, which promises a gate, is deliberate and must
  not be copied over.
- **`src/agents/architect.md`** — nothing. **Recorded as a deliberate no-op:** the
  `qa-engineer` consult row already names *"integration/e2e strategy decision"* (fact 11)
  and needs no edit to become reachable; sub-question 12 is what reaches it.

**Verify:**

- Instruction-reviewer clean.
- **claude-code-guide invoked for the `plan/main.md` edit, and its answer RECORDED** — the
  2026-08-27 orchestrator ruling at this phase's route paragraph. **A phase that reports
  "no frontmatter touched, so the pass was skipped" has applied the OVERRULED reading**, and
  an unrecorded pass is indistinguishable from one that never ran.
- **`grep -n "^12\." src/commands/plan/main.md` returns the new sub-question**, and
  `grep -c "^11\." ` confirms sub-question 11 is untouched. Capture the pre-change
  sub-question list first — this phase appends, it renumbers nothing.
- **`grep -n "### E2E Scenarios" src/commands/plan/main.md` returns exactly two sites** —
  the PHASE-2 subsection and its mention in the sub-question's return shape — and the
  subsection's bracket text **does NOT promise a gate**.
- **The `### Pure-Builder Targets` and `### Change-Induced Dead Code` bracket texts are
  byte-unchanged.** A phase that "harmonized" the three has broken two working lanes.
- **No plan vocabulary in emitted text** — "D2", "OQ-3", "Phase 2" and this plan's number
  are maintainer vocabulary. Emitted text names only commands, files and behaviors.

---

### Phase 3 — `/devforge:breakdown` + the two QA agents *(instruction-only)*

**Route: instruction-author → instruction-reviewer.** No frontmatter is touched in
`breakdown/main.md`. `qa-engineer.md` / `qa-reviewer.md` carry a fenced `yaml` meta-block
rather than Claude Code frontmatter (the emitter builds the agent frontmatter), so the
integration pass is likewise not owed here — **verify that reading against
`src/agents-AUTHORING.md`'s meta-block contract before relying on it.** ⚠ **Leaving both
meta-blocks byte-unchanged is a CROSS-PLAN commitment, not this plan's private choice**:
plan 89's Phase 2b edits `qa-reviewer.md` too and rests on the same fact for the same
excuse. **A meta-block edit here would silently invalidate that plan's stated reasoning.**

⚠ **RESOLVED 2026-08-27 (orchestrator ruling) — full ruling at Phase 2's route paragraph.**
`breakdown/main.md` **DOES owe a claude-code-guide pass** (it ships into
`.claude/commands/devforge/` and the repo rule has no frontmatter carve-out), while
`qa-engineer.md` / `qa-reviewer.md` keep the recorded-skip route **only while their fenced
`yaml` meta-blocks stay byte-unchanged** — and **this note IS that recording**, so the skip is
never silent.

Scope, three files:

- **`src/commands/breakdown/main.md` PHASE 0a.5** — one paragraph, modelled line-for-line on
  the change-induced-dead-code paragraph (fact 16): the `### E2E Scenarios` table is read
  from `plan.md` DIRECTLY, not from the handoff, and surfaced as its own sub-block when
  non-empty. **When `plan.md` has no such table, surface nothing — no empty sub-block, no
  "none" line** (that sentence exists verbatim in the dead-code paragraph; reuse its shape,
  not its words).
- **`src/commands/breakdown/main.md` PHASE 3** — an `### E2E scenario tasks` subsection
  beside the property-test and regression-net subsections. It states: a dedicated
  `qa-engineer` task per D5, created under the Agent Assignment table's existing
  test-authoring row (fact 18) rather than a new row; scenarios ride `## Change Details`;
  **this lane adds NO flag and NO header field**; the framework-selection rule of D5,
  verbatim and escape-hatch-free; **and D5's placement rule in the arm Phase 0 ratified —
  ONE of the two arms, never both**, with the one-sentence reason it exists (an e2e spec
  the package's unit-test glob can reach is run by the wrong runner at the next
  `/devforge:implement` task and burns the self-repair cap on a non-defect). ⚠ **The two
  existing zero-flag lanes phrase that sentence differently** — the Two-hats subsection says
  *"NO flag and NO header line"*, the Regression-net subsection says *"NO flag and NO header
  field"* — so **grep both strings when locating them, and match ONE of the two rather than
  inventing a third wording.**
- **`src/agents/qa-engineer.md`** — under D5 fork (a), the `## Mobile Testing` heading is
  renamed and a web block added beside the mobile block, **every mobile bullet
  byte-identical** (OQ-2). The web block names the configured-framework rule, the
  blocked-not-guessed stop, and **the ratified placement rule** — the agent is the party
  that actually chooses where the file lands, so the rule has to reach it and not only the
  task file.
- **`src/agents/qa-reviewer.md`** — one mirror sentence beside step 6's mobile-parity
  sentence, which stays byte-identical. ⚠ **SHARED SURFACE — read it live before editing.**
  Plan 89's Phase 2b edits **Approach step 4** (extending *"Flag weak, vacuous, or
  implementation-coupled assertions"* with its vacuous-test shapes) and **Rule 3** in this
  same file. **Different sentences, so there is no contradiction to resolve — the hazard is
  writing over them from a stale copy.** If plan 89 shipped first, its step-4 and Rule-3 text
  must be present and byte-identical after this phase's edit.
  ⚠ **AMENDED 2026-08-27 — the conditional is now determinate: plan 89 SHIPPED FIRST.** Its
  step-4 and Rule-3 text is on disk (step 4 carries the three vacuous-by-construction shapes
  at ≥ High plus the two further shapes; Rule 3 carries the failability clause), so this
  phase **MUST** find both present and byte-identical after its own step-6 edit — the "if"
  is discharged and only the obligation remains. **The live read is still owed at build
  time**; this note records observed state on 2026-08-27, it does not stand in for opening
  the file.

**⚠ The Agent Assignment table gains NO row.** The dedicated test-authoring row already
routes this work (fact 18), and adding a parallel e2e row would create two rows that both
match a test-authoring task — a routing ambiguity where none exists today.

**Verify:**

- Instruction-reviewer clean.
- **claude-code-guide invoked for the `breakdown/main.md` edit, and its answer RECORDED** —
  the 2026-08-27 orchestrator ruling at this phase's route paragraph. **For
  `qa-engineer.md` / `qa-reviewer.md` the recorded skip is valid ONLY if `git diff` shows
  both fenced `yaml` meta-blocks byte-identical** — diff them and **record the result**,
  because a meta-block edit voids the skip and makes the pass owed for those files too.
  ⚠ **The existing meta-block bullet below now justifies the skip for the TWO AGENT FILES
  ONLY**, never for `breakdown/main.md`, which owes the pass regardless.
- **`grep -n "Agent Assignment" -A 20 src/commands/breakdown/main.md` shows the same row
  count as before.** Capture the pre-change table first.
- **The framework rule contains no `OR`, no `unless`, no `if none`, and no "use judgment"**
  — instruction-reviewer confirms it names ONE mandatory action plus a stop.
- **The placement rule appears in BOTH `breakdown/main.md` and `qa-engineer.md`, in ONE
  arm** — the emitted text names the ratified arm only, and instruction-reviewer confirms
  the unratified arm appears nowhere. **A rule offering the dedicated directory "or" a
  runner-config exclude has reintroduced the judgment call the fork exists to remove.**
- **`git diff src/agents/qa-engineer.md` shows the four mobile bullets unchanged**, and
  `git diff src/agents/qa-reviewer.md` shows step 6's existing sentence unchanged (OQ-2).
- **`qa-reviewer.md`'s clobber check** — if plan 89 shipped first, its **Approach step 4**
  and **Rule 3** text is present and byte-identical after this phase. Capture both
  pre-change, and confirm `git diff` touches step 6 ONLY. **A diff that also rewrites step 4
  has overwritten a shipped plan from a stale read**, which is the one failure this shared
  surface can produce.
  ⚠ **AMENDED 2026-08-27 — the "if" is discharged: plan 89 shipped first**, so this
  criterion is now unconditional. Step 4's vacuous-test shapes and Rule 3's failability
  clause are on disk and MUST survive byte-identical; step 6's mobile-parity sentence was
  verified intact on 2026-08-27 and this phase is what puts it at risk. **Still capture both
  pre-change from the live file** — the criterion tests the diff, not this note.
- **Both agent files' fenced `yaml` meta-blocks are byte-identical** — diff them. This is
  what justifies not running claude-code-guide here AND what plan 89's Phase 2b relies on.
- **`grep -rn "## Mobile Testing" .` returns either the renamed heading (fork a) or the
  original plus a new sibling (fork b) — and in the fork-(a) case, ZERO stale references**
  anywhere in the repo. The pre-change grep returns exactly one line; capture it first.
- **`breakdown/main.md`'s six PHASE-3.5 gates are byte-unchanged** (fact 23) — this phase
  adds none, and a diff touching that section means the tripwire was crossed.
- **No `{{` placeholder leaks**: `grep -rl "{{" src/commands/breakdown/` returns nothing
  new against the pre-change list.

---

### Phase 4 — `/devforge:verify` PHASE 4.5 *(Python + instruction)*

**Route: python-engineer → python-reviewer, test-first, then instruction-author →
instruction-reviewer** for the `main.md` block. This phase touches no frontmatter (fact 25),
so no `allowed-tools` line is added — **the field is a grant, not a restriction (verified
against current docs 2026-08-26), so its absence cannot break the verb.**

⚠ **RESOLVED 2026-08-27 (orchestrator ruling) — Deliverable 3's `verify/main.md` edit DOES owe
a claude-code-guide pass.** `verify/main.md` ships into `.claude/commands/devforge/`, so it is
the same body-only command-spec class as Phases 2 and 3; full ruling at Phase 2's route
paragraph. ⚠ **The `allowed-tools` discussion above answers a NARROWER question — whether a
frontmatter line is owed — and does NOT discharge this one.** **Deliverable 3's route is
therefore instruction-author → instruction-reviewer → claude-code-guide**; Deliverables 1–2
stay python-engineer → python-reviewer and owe no pass, touching no shipped `.claude/` file.

**Deliverable 1 — the verb.** A new `verify_helper e2e-gate` over a new
`src/devforge/lib/_verify/_e2e.py`, built in `_regression.py`'s shape:

- **ALWAYS exits 0.** Every internal failure is a `status`, never a crash and never a
  non-zero exit (fact 13).
- **Statuses**: `off` / `inconclusive` / `e2e-clean` / `e2e-failing`, plus a `note` that is
  always present and an output tail only on `e2e-failing`.
- **Runs at HEAD in `source_root` only.** No worktree, no merge-base, no second run.
- **Its own timeout constant** (OQ-5), never an import of `_regression._TEST_TIMEOUT`.

**Deliverable 2 — the fold.** Under D3 fork (i), `compute-verdict` gains an `--e2e` input
that adds a `reasons` line and **no blocker** (fact 14's channel, minus the blocker).
`render-report` takes no e2e input and `verification.md` gains no dedicated section — the
same shape the regression gate already has.

**Deliverable 3 — the orchestration block.** `verify/main.md` gains `### 4.5 — e2e run`
after 4.4, its branch list written in the shape 4.3's already uses, plus the
`$WORKDIR/e2e.json` entry in `### Intermediate scratch files`, plus the `--e2e` flag on the
5.1 `compute-verdict` invocation, plus a sentence in the PHASE-4 heading line (which today
reads *"Assembled mechanical checks + hygiene + regression gate + dead-code removal"*).

**⚠ Four constraints, each a fact rather than a fork:**

1. **`off` prints nothing** (D8) — unlike 4.3's `off` branch, which says *"Note it in the
   run"*. The divergence is deliberate: a regression gate that is switched off was switched
   off by someone, while an absent `E2E_COMMAND` is the default state of most projects.
   **Say the divergence in the plan record so Phase 5 does not "harmonize" it.**
2. **`e2e-failing` never gates in v1** (D3 fork (i)) — so `compute-verdict` gains no
   blocker branch at all, and a test asserting the verdict is unchanged across all four
   statuses is the criterion that proves it.
3. **A timeout is `inconclusive`, not `e2e-failing`** (OQ-5).
4. **The heading-line edit is easy to miss.** PHASE 4's `## ` heading enumerates its
   sub-phases; a 4.5 that is not named there leaves the file describing four sub-phases and
   containing five.

**Tests — written and RUN in the same turn as the code**, covering: no configured command →
`off`; a command that exits 0 → `e2e-clean`; exit non-zero → `e2e-failing` with a tail; a
missing binary → `inconclusive`; a timeout → `inconclusive`; and **an unchanged-verdict test
across all four statuses** (constraint 2).

**Verify:**

- python-reviewer clean; instruction-reviewer clean; the `tests/lib/_verify/` suite green.
- **claude-code-guide invoked for Deliverable 3's `verify/main.md` edit, and its answer
  RECORDED** — the 2026-08-27 orchestrator ruling at this phase's route paragraph. **The
  `allowed-tools` reasoning does not substitute for it**, and Deliverables 1–2 owe no pass.
- **Every pre-existing `_verify` test passes unchanged.** A failure in a `compute-verdict`
  test means the fold changed a verdict it was not supposed to change.
- **A test proves the verb exits 0 on every path**, including a deliberately broken command
  (fact 13's contract).
- **A test proves the verdict is IDENTICAL for `off`, `inconclusive`, `e2e-clean` and
  `e2e-failing`** given the same other inputs (constraint 2). **This is the single criterion
  that distinguishes D3 fork (i) from fork (ii) mechanically.**
- **`grep -n "worktree\|merge-base" src/devforge/lib/_verify/_e2e.py` returns nothing** —
  the HEAD-only rule is what makes the seat correct at all (`## Origin`).
- **`grep -n "### 4.5" src/commands/verify/main.md` returns the new block, and the PHASE-4
  heading line names it.** Capture the pre-change heading first.
- **`$WORKDIR/e2e.json` appears in `### Intermediate scratch files`** — that list is
  documented as complete, and a scratch file missing from it is a contract break.

---

### Phase 5 — Docs sweep + the `configure` composer + dated reconciliation notes

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document
edit. `src/CLAUDE.md` ships as the consumer's root `CLAUDE.md`, so **claude-code-guide is
owed for that file's edits.**

⚠ **RESOLVED 2026-08-27 (orchestrator ruling) — the claude-code-guide pass is owed for this
phase's `configure/main.md` edit TOO, not only for `src/CLAUDE.md`.** `configure/main.md`
ships into `.claude/commands/devforge/`, the same body-only command-spec class as Phases 2, 3 and 4;
full ruling at Phase 2's route paragraph. **Both files in this phase take the pass**; the
plan-document and `CHANGELOG.md` / repo-root-ledger edits do not, shipping nowhere.

Open the phase with `grep -rn "e2e\|E2E" src/ *.md` and reconcile every hit against what
this build made true. **This sweep list is NOT certified exhaustive** — treat a hit not
named below as an omission in this plan, not as a new defect.

Scope:

- **`src/commands/configure/main.md` — the field counts** (fact 21). The file says 29
  fields / 37 keys; the code said 30 / 38 before this build and says 31 / 39 after.
  **Count the live `FIELD_SCHEMA` and `_PROJECT_CONFIG_KEY_ORDER` tuples and write what you
  counted** — the printed numbers are already wrong, so incrementing them propagates the
  error. Four sites carry a count in that file; the setter-mapping table gains a row.
  ⚠ **CORRECTED 2026-08-27 — SIX sites carry a count, not four** (fact 21a): the four quoted
  in fact 21, the **pre-existing completion-message site** (*"The 29 configuration fields are
  persisted"*, *"carries all 37 keys"*) that fact 21 did not list, and **plan 89's D6 note**
  (anchor *"One emitted key is set by no phase of this command"*), whose *"30 fields"* /
  *"23 detection-derived"* / *"6 user-only prompts"* arithmetic this build also moves.
  **The D6 note is UPDATED IN PLACE with the post-build numbers — never removed and never
  contradicted**: it is plan 89's ratified D6 deliverable, and its no-prompt instruction for
  `regression_gate` is untouched by this plan.
  ⚠ **AMENDED 2026-08-27 (Phase-0 close) — this bullet named ONE composition site and the
  ratified D1 seeding arm needs THREE.** `test_command`, the sibling this arm mirrors, is
  composed by a three-site instruction-only mechanism in this same file, and **a build that
  adds only the setter-mapping row ships a field that stays `""` forever — functionally D1's
  REJECTED alternative (c), reached by omission.** ⚠ **The phase numbers below are
  `/devforge:configure`'s OWN phases, not this plan's** — a confusion that would send the
  edit to the wrong section. All three are owed:
  1. **A compose bullet in `/devforge:configure`'s own Phase 2**, mirroring the
     `test_command` derivation rule's shape (fact 22): derive `e2e_command` from
     `MANIFESTS_JSON.packages[<path>].devDependencies` naming `playwright` or `cypress`,
     plus the associated script, and **inherit fact 22's don't-guess rule VERBATIM** — empty
     when detection yields nothing, and **never an invented ecosystem default.**
  2. **An echo-template line in `/devforge:configure`'s own Phase 3 bulk confirmation**,
     which moves that phase's detection-derived figure **23 → 24** and the populated total
     **29 → 30** (fact 21a's reconciliation note). **Count the live file and write what you
     counted; never increment a printed number.**
  3. **The setter-mapping table row** — the one site this bullet already named.
- **`src/CLAUDE.md`** — a `### Verification` note that the e2e run is feature-level and
  advisory, kept TIGHT (plan 08's always-on-trim discipline binds this file; every line
  costs tokens in every session). ⚠ **Read the `### Always` list and the `### Verification`
  section LIVE** (fact 28) — the list was at 15 items on 2026-08-26 and **plan 89 appends
  to it**, so count it rather than trusting any number written here. **This plan proposes
  NO new `### Always` item**; if Phase 5 finds itself writing one, it has exceeded the
  plan.
  ✅ **AMENDED 2026-08-27 — plan 89 HAS appended item 16** (*"Test behavior changes"*), so
  the list holds SIXTEEN. **The count-live instruction stands unchanged**: count the list
  rather than trusting 15 or 16, and this plan still proposes no new item.
- **`src/devforge/storage-rules.md`** — the task-file schema section lists the two optional
  header lines (fact 15's `**Property targets**:` and `**Dead code removal**:`). **This
  lane adds neither** (D4/D5), so the correct edit is a sentence in the `## Change Details`
  vicinity naming the e2e scenarios as free-form content, or **no edit at all** — Phase 5
  reads the file and records which, because "checked, nothing to amend" is a finding.
  ⚠ **Plan 89 edits this file's `## Done When` skeleton**, so read the skeleton live and
  count its standing lines rather than trusting any count.
  ✅ **AMENDED 2026-08-27 — plan 89 HAS made the skeleton FIVE standing lines**, the fifth
  being *"Tests pass on changed files (see Development Commands section)"*, appended last and
  pinned to `_DONE_WHEN_FIXED_LINES` by a standing test. **The count-live instruction stands
  unchanged**: read the skeleton and count it, and note that the two optional header lines
  this bullet names are a separate list that plan 89 did not touch.
- **Repo-root `CLAUDE.md`** — the plan-90 one-liner appended to the active-plans index,
  matching the neighbouring entries' density. **Read the file live for the append point**;
  the index grows and a pre-computed position rots.
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry, per this repo's index/archive
  split.
- **`CHANGELOG.md`** — an entry under the existing `## [Unreleased]` → `### Added`
  (fact 27). **Read the file live.** The entry must state the honest bounds: advisory, not
  a gate; declared but unenforced; local, not CI (OQ-1).
- **`66-PROPERTY-BASED-TESTING-AND-NARROWING-RULE-PLAN.md`** — a dated note that the e2e
  lane deliberately reuses its declaration SHAPE and deliberately does NOT reuse its gate
  (D4), with the trigger that would change that. **Do not edit plan 66's reasoning** — it
  is still the record for the property lane.
- **`86-FOWLER-REFACTORING-GAPS-PLAN.md`** — a dated note that its F3 no-gate declaration
  precedent (fact 17) was cited and applied. Its own text is not edited.
- **`34-VERIFY-HYGIENE-FALSE-POSITIVE-PLAN.md`, plan 44, plan 87** — **check only, and
  record the no-op as deliberate.** They are the ADVISORY/WARN family D3's stance joins;
  none is touched.
- **`89-TEST-FOUNDATION-HARDENING-PLAN.md`** — a dated cross-reference recording that the
  shared surfaces were re-derived live per the coordination rule below, and what was found.
  ⚠ **Read plan 89 live**, and read its `## Cross-plan coordination — plan 90` section and
  its **OQ-3** together: OQ-3 is what decides whether the **FOURTH** surface
  (`qa-engineer.md`) is shared at all (**corrected 2026-08-27 from *"the third surface"* — a
  drafting-time inconsistency, not a change of position: that wording predates
  `qa-reviewer.md` joining the shared set as the THIRD, after which every other passage in
  this file calls `qa-engineer.md` the conditional FOURTH**).
  ✅ **AMENDED 2026-08-27 — OQ-3 is RESOLVED to arm (i)** (accept §3.4's emptiness, add
  nothing), so **the fourth surface is NOT shared**: plan 89 did not touch
  `src/agents/qa-engineer.md`, and this plan is its only prospective editor. Read that
  resolved answer live all the same; this note records it, it does not replace it.

**⚠ The cross-plan coordination rule, and it binds whichever of 89/90 ships SECOND.**
Plans 89 and 90 were drafted in the same 2026-08-26 session. Plan 89 ships FIRST by intent.
**Whichever ships second reads the LIVE text of each shared surface and re-derives its edit
from what it finds — never a pre-computed diff.** This is the rule plans 82/85 and 83/85
established. **THREE surfaces are shared unconditionally, and a FOURTH is conditional**,
matching plan 89's own lead-in — *"**THREE surfaces this plan edits unconditionally, and a
FOURTH that is conditional and probably never joins them**"*:

- **`src/CLAUDE.md`** (the `### Always` list and the `### Verification` section) — plan 89
  appends one `### Always` item at its Phase 4. **Shared.**
- **`src/devforge/storage-rules.md`** (the task-file `## Done When` skeleton) — plan 89
  edits it at its Phase 1. **Shared.**
- **`src/agents/qa-reviewer.md`** — **Shared, and it is the NEWEST and least obvious of the
  three**: plan 89 gained a **D7** (test-meaningfulness) on 2026-08-26 whose **Phase 2b**
  edits that file at **Approach step 4** (extending *"Flag weak, vacuous, or
  implementation-coupled assertions"*) and at **Rule 3**. **This plan edits a DIFFERENT part
  of the same file** — one mirror sentence beside **step 6's** mobile-parity note (Phase 3
  here). ⚠ **Different sentences, same file, so the risk is a CLOBBERED EDIT on a stale
  read, not a contradiction**: whichever ships second reads the file live and confirms the
  other's sentence survived. **Both plans leave the fenced `yaml` meta-block byte-unchanged**
  — that is what excuses both from a claude-code-guide pass, and it is a shared commitment,
  not this plan's private choice.
- **`src/agents/qa-engineer.md`** — **CONDITIONAL, and the likely outcome is that plan 89
  never touches it.** Its OQ-3 offers three candidates and only arm **(iii)** (repoint
  `qa-engineer` Rule 6 away from *"its testing requirements"*) would edit that file; **(iii)
  is marked NOT recommended** and arm **(i) — accept, add nothing — is RECOMMENDED**. ⚠ **Plan
  89's D7 considered this file and left it alone deliberately**, so that D7 does NOT move it
  into the shared set; plan 89's own bullet says a reader *"must check OQ-3's RESOLVED answer
  before treating it as contested."* (⚠ **`D7` is an overloaded token across the two plans** —
  plan 89's D7 is test-meaningfulness; **this plan's D7 is the wall-clock cost line.** Every
  cross-plan reference here names the plan.)

**So Phase 5 must read plan 89's RESOLVED OQ-3 answer before treating `qa-engineer.md` as
contested.** If OQ-3 resolved to (i) or (ii), this plan is that file's only editor and D5's
SECTION fork applies to virgin text. If it resolved to (iii), the coordination rule binds
and that fork must be re-derived against whatever Rule 6 says by then. ⚠ **Plan 89's
standing rule binds the READ, not the edit** — it states in its own text that it makes no
claim about what plan 90 writes, and it already records that plan 90 as drafted proposes no
new `### Always` item. **So the live read exists to place this plan's `### Verification`
edit correctly, not to append after plan 89's item.**

**Commits: one per phase, no AI-attribution trailer** (this repo's commits carry none —
match the trailer-free convention), lowercase terse subject with a scope prefix matching
`git log --oneline`.

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **claude-code-guide invoked for BOTH shipped files this phase edits — `src/CLAUDE.md` AND
  `configure/main.md` — and each answer RECORDED** (the 2026-08-27 orchestrator ruling at
  this phase's route paragraph). **A phase that ran it for `src/CLAUDE.md` only has covered
  half its shipped surface.**
- **`configure/main.md` carries the `e2e_command` compose rule in `/devforge:configure`'s own
  Phase 2 AND its echo-template line in that command's own Phase 3 bulk confirmation**, not
  just the setter-mapping row. ⚠ **A build that added only the setter row FAILS this
  criterion** — the field would render, be settable, and stay `""` on every install, which is
  D1's rejected alternative (c) reached by omission. **Grep `configure/main.md` for
  `e2e_command` and confirm THREE distinct sites.**
- **The configure counts match a fresh count of the live tuples**, not an increment of the
  printed number (fact 21). State the counted numbers in the commit message. ⚠ **Plan 89's D6
  note moves on both terms** — 23 → 24 detection-derived, 29 → 30 populated, schema 31 (fact
  21a's reconciliation note) — and it is **updated in place, never removed.**
- **`src/CLAUDE.md`'s `### Always` list has the SAME item count before and after this
  phase** — capture the pre-change count by counting, and confirm the last item is
  byte-unchanged. **Do not compare against any number printed in this plan** (fact 28).
- **The `CHANGELOG.md` entry states all three honest bounds.** An entry claiming the
  framework "now runs end-to-end tests" without "advisory" and "when configured" has
  over-claimed by two layers.
- **The repo-root one-liner names the no-incident origin** — a predicted-gap plan, no
  consumer failure behind it.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass
  (`qa-engineer` was already reachable — fact 18 — so a failure here means something
  unintended moved).
- **The plan-89 note reflects what plan 89 ACTUALLY says**, read at write time.

---

### Phase 6 — Consumer e2e *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim the
e2e lane has been observed.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **The declared happy path.** On an install with a real Playwright suite, run a feature
   whose spec carries a user-visible flow AC. **MUST** produce: an `### E2E Scenarios`
   subsection in `plan.md`; a `qa-engineer` task naming those scenarios; a suite that the
   agent runs during that task; and `/devforge:verify` PHASE 4.5 reporting **`e2e-clean`**.
2. **The silent install.** On an install with no e2e infrastructure and no configured
   command, run a feature end to end. **MUST** produce: no sub-question-12 answer, no
   `### E2E Scenarios` subsection, no `qa-engineer` e2e task, status `off`, and **no
   user-facing mention of e2e anywhere in the run** (D8).
3. **The broken flow.** Break one flow deliberately and re-run `/devforge:verify`. **MUST**
   flip the status to **`e2e-failing`**, surface the failing tail, **and behave per the
   ratified D3 arm** — under (i) the verdict is whatever it would have been without the
   e2e result; under (ii) it is NEEDS WORK.

**Verify:**

- All three anchors are scored **explicitly** — stated, not summarized.
- **Anchors 1 and 2 are scored as a PAIR.** A lane that fires on everything passes 1 and
  fails 2; a lane that never fires passes 2 and fails 1. **Neither is meaningful alone.**
- **Anchor 3 records the VERDICT as a string**, not as "behaved correctly" — this is the
  only place D3's fork is observed in a real run, and a ratifier who chose (i) should see
  APPROVED printed beside a red suite and decide whether they still want it.
- **Anchor 1 records where the e2e spec files LANDED and whether any later
  `/devforge:implement` task's `verify-touched` run picked one up** (D5's placement rule,
  OQ-3's bound). **This is the only place the runner collision can be observed**, and a
  self-repair round spent on an e2e spec executed by the unit runner is a D5 finding, not a
  flake.
- **Anchor 1 records the wall-clock delta as a NUMBER** — `/devforge:verify` with the lane
  versus with `E2E_COMMAND` unset, on the same feature (D7). **This is the first number
  this plan family has ever had; record it even if it is uninteresting.**
- **Anchor 2 diffs the whole transcript for the string `e2e`** — a single advisory line is
  a failure of D8, not a nit.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything: a missing scenario declaration is a D2 finding, a
  missing task is a D5 finding (or the D4 gate's absence, which is BY DESIGN and not a
  defect), an e2e spec run by the unit runner is a D5 **placement** finding, a wrong status
  is a D3 finding, and a nagging no-op install is a D8 finding. **They have different
  fixes.**
- **A clean run is NOT evidence that e2e tests were needed.** It is evidence the lane
  works. **This plan's premise rests on a 2026-08-26 question and a sweep, and nothing this
  phase can produce changes that** — one working lane demonstrates no defect it would have
  caught.

---

## Non-goals

- **Changing anything about how existing tests run.** `verify-touched`, `regression-gate`,
  `PACKAGE_STACKS[].test_command` and `TEST_COMMANDS` are byte-unchanged in behavior. **The
  rejected "put e2e in `test_command`" alternative is what a change there would have
  been**, and `## Origin` records why it was rejected.
- **A test-tier taxonomy.** This plan adds ONE key for ONE tier. It does not introduce
  unit/integration/e2e as a general dimension of `PACKAGE_STACKS`, task files, or handoffs
  — D1's per-package arm is the recorded widening path and needs its own ratification.
- **Any new mechanical check, `verify-*` gate, or hard-fail validator.** Plan 75's tripwire
  holds in both halves: **the lane adds a MODE and a REPORT, not a gate.** D4 records the
  gate's shape and its trigger without building it, and D3's verb always exits 0.
- **Gating the verdict on an e2e result.** D3 fork (i) — advisory in v1, with a named
  strengthening trigger. **A future plan that flips this owes OQ-4's flake policy in the
  same document.**
- **A constitution edit.** §3.4 Testing Requirements is `[project-specific]` and §3.6 is
  universal (fact 26); this plan edits neither, so no consumer install sees
  `verify-universal-defaults` drift — deliberately unlike plan 86, which accepted that
  cost for a §3.6 rule.
  ⚠ **AMENDED 2026-08-27 — plan 89 accepted the same drift cost on 2026-08-27**, appending a
  universal block to **§3.5** (chosen over §3.4 precisely because §3.4 is outside
  `_UNIVERSAL_SECTIONS` and produces no drift finding at all). **So a consumer upgrading past
  both plans 86 and 89 sees TWO drift findings, §3.5 AND §3.6.** **This plan still adds none
  and contributes no third** — the non-goal is unchanged, and the reason to state this is
  that a Phase-6 observer meeting two drift findings must not attribute either to the e2e
  lane.
- **Coupling to `ac_runtime_*`.** D6 — the runtime-assisted AC channel and the e2e suite
  stay separate, and the unification, if ever wanted, belongs in `ac_runtime_cli_command`.
- **Repairing the unreachable `e2e` bucket value in `_probe_tier.py`** (fact 9). Recorded
  as discovered, deliberately not fixed: it changes `/devforge:research`'s probe-tier
  classification and needs its own argument.
- **Repairing the `init_helper verify` soft-warn that recommends a verb no command runs**
  (fact 8). Recorded, not fixed — D8's no-nagging stance names it as the anti-pattern it
  is, but removing it is a separate change to a separate command.
- **CI wiring.** OQ-1 — this framework configures a local pipeline and writes no CI files.
- **Flake handling.** OQ-4 — no retries, no quarantine, no accounting. Explicitly out of
  scope, and load-bearing for D3.
- **Mobile e2e changes.** OQ-2 — the Detox / XCTest UI / Espresso / `integration_test`
  guidance survives byte-identical in both agents.
- **Any change to plan 63's 13/7 model-invocable counts.** No frontmatter invocation route
  changes; this plan contributes NO delta and owes no description trim (OQ-6).

---

## Dependencies + related

- **`89-TEST-FOUNDATION-HARDENING-PLAN.md`** — the unit/regression foundation, drafted in
  the same 2026-08-26 session and shipping FIRST. **This plan builds the second floor and
  assumes nothing about the first beyond its existence.** ⚠ **The coordination rule in
  Phase 5 binds whichever ships second** — read the shared surfaces live. Plan 89 carries
  the reciprocal rule in its own `## Cross-plan coordination — plan 90` section:
  **THREE surfaces are shared unconditionally** (**corrected 2026-08-27 from *"TWO"* — a
  drafting-time inconsistency, not a change of position: the enumeration that immediately
  follows already lists three, and plan 89's own quoted lead-in says THREE**) — it appends
  one `### Always` item to `src/CLAUDE.md`
  at its Phase 4, edits `storage-rules.md`'s `## Done When` skeleton at its Phase 1, and
  (added 2026-08-26 by its **D7**) edits `src/agents/qa-reviewer.md` at **Approach step 4
  and Rule 3** under its **Phase 2b**. ⚠ **`qa-reviewer.md` is the one to miss**: this plan
  edits the same file at a **different** sentence (beside step 6's mobile-parity note), so
  the hazard is a **clobbered edit on a stale read**, not a contradiction — and **both plans
  commit to leaving the fenced `yaml` meta-block byte-unchanged.**
  **`src/agents/qa-engineer.md` is a CONDITIONAL fourth**, shared only if plan 89's OQ-3
  ratifies its arm (iii) — which that plan marks NOT recommended while recommending arm (i),
  add nothing; **its D7 considered that file and deliberately left it alone**, so D7 did not
  move it into the shared set. Plan 89's lead-in states the split: *"**THREE surfaces this
  plan edits unconditionally, and a FOURTH that is conditional and probably never joins
  them**"*. ⚠ **Its standing rule binds the READ, not the edit**, and it explicitly makes no
  claim about what this plan writes.
  ✅ **AMENDED 2026-08-27 — plan 89 is DONE (build) 2026-08-27** (Phases 0–5 complete; its
  Phase 6 consumer e2e DEFERRED, **not waived**). **It shipped first, so the coordination
  rule now binds THIS plan**, all three unconditional surfaces have moved, and its **OQ-3
  resolved to arm (i)** — the conditional fourth, `qa-engineer.md`, **did NOT join the shared
  set**. See the amendment block at the top of this file for the observed state of each
  surface; the live read is still owed at build time.
- **`66-PROPERTY-BASED-TESTING-AND-NARROWING-RULE-PLAN.md`** — the declaration-lane shape
  D2 copies (fact 15) and the gate D4 declines to copy. **Read, and annotated in Phase 5;
  its mechanism is unchanged.**
- **`86-FOWLER-REFACTORING-GAPS-PLAN.md`** — its F3 regression-net declaration is the
  no-gate precedent, including the two honest-bound sentences this plan reuses in shape
  (fact 17). **Cited for the stance; its text is not edited.**
- **`34-VERIFY-HYGIENE-FALSE-POSITIVE-PLAN.md`, plan 44, `87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`**
  — the ADVISORY / WARN-only family D3 joins, and plan 87 additionally supplies the
  predicted-gap-with-no-incident framing this plan's `## Evidence constraint` copies.
  **Cited; none is touched.**
- **`48-REVIEW-MANDATORY-GATE-PLAN.md`** — the shelve-until-observed precedent D3's
  strengthening trigger and D4's gate trigger both use. **Not revived by this plan.**
- **`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`** — its D7 established the wall-clock
  cost-line obligation D7 here discharges, and its D8 (two mandatory stages in sequence
  cost the SUM, decide the policy once) is one of the three reasons D3 recommends advisory.
  **Untouched — and note it is still NOT STARTED**, so D8's closing rule about which plan
  ratifies second may bind against this one too if both are open at the same time.
  ***(The preceding sentence is the DRAFTING-TIME clause, preserved verbatim and RETIRED
  2026-08-27 — read it as the corrected wording below, never as a live claim about plan
  85.)***
  ⚠ **CORRECTED 2026-08-27 — the quoted clause *"it is still NOT STARTED"* is FALSE as of
  2026-08-26.** Plan 85 is **DONE (build) 2026-08-26** — Phases 0–4 complete, Phase 5
  consumer e2e deferred as a batched run (**not waived**) — so **the both-open contingency
  is moot and never fired.** Its **D7 and D8 are now RATIFIED law rather than a sibling
  plan's proposal**, which **strengthens** the obligation this plan's own D7 discharges
  rather than weakening it: the cost line is owed because a ratified decision says a plan
  adding a slow stage owes one. ⚠ **`D7` stays an overloaded token — plan 85's D7 and plan
  89's D7 and this plan's D7 are three different decisions**; the rest of this bullet is
  unchanged, and plan 85 is still untouched by this plan. **D3's third reason is likewise
  restated, not withdrawn**: the drafted wording *"plan 85's D8 concern applies before plan
  85 has even ratified"* is now the stronger case, D8 having ratified.
- **`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`** — the profiler whose Phase-2 numbers do not
  exist, which is why D7's cost line is structural. **Phase 6's wall-clock anchor is the
  first datum this plan family produces.**
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number /
  no-new-validator tripwire. **Both halves hold.**
- **`15-AGENT-STANDARDIZATION-PLAN.md`** and `src/agents-AUTHORING.md` — the D-Skeleton
  D5's SECTION fork is argued against (fact 3). **Neither is edited**; the fork picks whether to
  reduce or compound an existing divergence.
- **`41-AGENT-EXECUTOR-REACHABILITY-PLAN.md`** — `qa-engineer` is already a reachable
  executor (fact 18), so the reachability gate takes no change. **Recorded so a Phase-5
  sweep does not go hunting one.**
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** — the 13/7 carve-out. **Untouched and
  unaffected** (OQ-6): no frontmatter invocation route changes. **There is no count to
  update.**
- **`08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`** — the always-on-trim discipline binding Phase 5's
  `src/CLAUDE.md` edit.

---

## Context for next session

**The one sentence that governs everything here:** an e2e scenario is DECLARED at
`/devforge:plan`, OWNED by a `qa-engineer` task at `/devforge:breakdown`, and RUN once per
feature at `/devforge:verify` in the real workspace at HEAD — advisory in v1, silent when
unconfigured, and invisible to every existing test path.

**Trap 1 — putting the e2e command anywhere the existing machinery can see it.** It runs
per task under `/devforge:implement` (fact 5, self-repair cap 3) and it runs in a bare
detached worktree under `regression-gate`'s baseline half (fact 6), where an app-dependent
suite fails for reasons unrelated to the feature and the gate then reads its own failure as
`baseline-failing` and stops gating. **A gate that disarms itself is worse than no gate**,
and this is the single reason D1's key is separate.

**Trap 2 — believing `test_infra.e2e` already works.** It does not, twice over: no command
runs the detector (fact 8), and its only reader filters the value out (fact 9). **Any
sentence in this build that says "the framework detects your e2e framework" is false until
Phase 1's Deliverable 2 lands**, and Phase 0 must pick which arm makes it true.
⚠ **AMENDED 2026-08-27 — Phase 0 picked, and the pick HARDENS this trap rather than closing
it.** The ratified arm is `/devforge:configure` composing the default from the
`MANIFESTS_JSON` manifests, so **`test_infra.e2e` is still read by nothing after this build
and `init_helper`'s detector is still reachable from no command.** Both halves of the trap
therefore survive the build: **the only true post-build sentence is that `/devforge:configure`
reads the project's package manifests** — any sentence crediting `init_helper` or
`.devforge/init.yaml` stays false, before and after.

**Trap 3 — reading D4's no-gate as a gap to fill.** It is a decision with a named trigger,
argued from plan 86's F3 and plan 75's tripwire. **A session that adds
`verify-e2e-coverage` because "the property lane has one" has left this plan** — the
trigger is an OBSERVED dropped scenario, not a structural analogy.

**Trap 4 — letting D3's advisory arm drift into a gate during Phase 4.** The single
mechanical criterion is the unchanged-verdict test across all four statuses (Phase 4's
verify block). If `compute-verdict` grows an e2e blocker branch, fork (ii) has been built
without being ratified.

**Trap 5 — "harmonizing" PHASE 4.5's `off` branch with 4.3's.** 4.3's `off` says *"Note it
in the run"*; 4.5's says nothing (D8, constraint 1 of Phase 4). **The divergence is
deliberate**: a disabled regression gate was disabled by a person, while an absent
`E2E_COMMAND` is the default state of most projects.

**Trap 6 — incrementing the configure counts instead of counting them.** `configure/main.md`
says 29 fields / 37 keys and the code said 30 / 38 BEFORE this build (fact 21). Adding one
to a wrong number produces a differently wrong number. **Count the live tuples.**

**Trap 7 — pre-computing the shared-surface edits against plan 89, or miscounting them.**
**THREE surfaces are shared unconditionally** — `src/CLAUDE.md`'s `### Always` list,
`storage-rules.md`'s `## Done When` skeleton, and **`src/agents/qa-reviewer.md`** — and plan
89 ships first, so all three move. ⚠ **The third is the one a stale reading misses**: it
became shared only on 2026-08-26, when plan 89 gained its D7 and a Phase 2b editing that
file at **Approach step 4 and Rule 3**. **This plan edits the same file at step 6**, so the
hazard is a clobbered edit, not a contradiction — Phase 3 must confirm plan 89's sentences
survived, and **neither plan may touch the fenced `yaml` meta-block.**
**`qa-engineer.md` is a CONDITIONAL FOURTH**, shared only if plan 89's OQ-3 ratifies its arm
(iii), which that plan marks NOT recommended while recommending arm (i) (add nothing).
**Read plan 89's RESOLVED OQ-3 before treating that file as contested**, and read every file
named here live rather than applying any diff computed in this plan. ⚠ **Treating
`qa-engineer.md` as shared when it is not is the mirror error**, and it costs D5's SECTION
fork a re-derivation it does not owe.
⚠ **AMENDED 2026-08-27 — every conditional in this trap is now determinate.** Plan 89
shipped first: all three unconditional surfaces have moved (`### Always` → 16 items,
Done-When skeleton → 5 standing lines, `qa-reviewer.md` step 4 + Rule 3 rewritten), and its
**OQ-3 RESOLVED to arm (i)**, so **`qa-engineer.md` did NOT join the shared set.** The trap
itself is unchanged and still binds: **the live read is owed at build time**, and this note
is observed state on 2026-08-27, not a substitute for opening the files.

**Trap 8 — treating a clean Phase-6 run as evidence the gap was real.** There is no
incident behind this plan and none is claimed. A working lane demonstrates a working lane.

**The working tree is uncommitted throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather
than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`init_helper`'s test-infra detector is unreachable from any command** (fact 8), and
   `init_helper verify` — which `/devforge:init-forge` DOES run — soft-warns by
   recommending a verb no command runs. **Recorded as an observation about the existing
   setup chain**, not a bug this plan repairs; D8 names it as the nagging anti-pattern the
   e2e lane must not copy.
2. **The `e2e` bucket's VALUE is unreachable in its only reader** (fact 9):
   `_pick_framework_from_test_infra` filters through a schema-valid set that excludes
   playwright and cypress, so a Playwright-only project yields `status: "partial"` → tier 1
   → framework `None` → demote to 1.5. **Repairing it changes `/devforge:research`'s
   probe-tier classification** and needs its own plan.
3. **`configure/main.md`'s field/key counts are one behind the code** (fact 21) —
   29/37 printed against 30/38 live. **Pre-existing; Phase 5 corrects it as a side effect
   of touching the same sites, and records that it was pre-existing.**
4. **`qa-engineer.md` carries an unchartered extra section** (`## Mobile Testing`, fact 3)
   against a D-Skeleton that names only `architect` and `tech-writer` as agents keeping
   extra sections. **Recorded; D5's SECTION fork decides whether this build reduces or compounds
   it, and either way `agents-AUTHORING.md` is not edited by this plan.**

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — twenty-eight rows, each
   checkable in under a minute *(plus the lettered sub-row **21a**, added 2026-08-27 by the
   staleness reconciliation; the NUMBERED facts are still twenty-eight)*. **If rows 3, 4, 5, 6, 8, 9, 15, 16, 17, 19 or 25 no longer
   hold, stop and re-derive**: they are D1's whole basis, D2's zero-Python carry, D3's
   fail-soft mould and its correctness argument, D4's precedent, D5's two forks, and Phase 4's
   frontmatter reasoning.
2. **Read `src/commands/verify/main.md` in full before touching it** — not just PHASE 4.
   The `### Intermediate scratch files` contract, the `$WORKDIR` re-derivation rule, the
   `compute-verdict` flag list and the report-format reference all constrain Phase 4.
3. **Read `src/devforge/lib/_verify/_regression.py` in full before writing `_e2e.py`** —
   the module docstring's contract, the always-exit-0 wrapper, the worktree try/finally and
   the timeout constants are the shape to mirror, and the HEAD-run line is the one thing
   `_e2e.py` keeps while dropping everything above it.
4. **Read `src/devforge/lib/_configure/_schema.py`, `_cmds_verify.py` and `_render.py`
   before adding the field.** The required-field loop in `_cmds_verify.py` is what a new
   nullable scalar breaks, and `_AC_RUNTIME_FIELDS` is the only exemption shape the file
   currently has.
5. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `_TEST_INFRA_BUCKETS`, `_SCHEMA_VALID_FRAMEWORKS`, `_AC_RUNTIME_FIELDS`,
   `FIELD_DEFAULTS`, `_PROJECT_CONFIG_KEY_ORDER`, `## Mobile Testing`, `### Pure-Builder
   Targets`, `Regression net:`, `do NOT invent an ecosystem-default guess`,
   `# --- HEAD run (main working tree, source_root) ---`, `## [Unreleased]`.
6. **Re-fetch the Claude Code authoring page before writing or amending any frontmatter**
   (`https://code.claude.com/docs/en/slash-commands`, which redirects to the skills page).
   The load-bearing facts are that **`allowed-tools` grants rather than restricts** and
   that **no field restricts which files a command may write**; if a future version changes
   either, Phase 4's frontmatter reasoning must be re-derived, not extended.
7. **Route every edit through the house loops:** **python-engineer → python-reviewer,
   test-first** for Phases 1 and 4's Deliverables 1–2; **instruction-author →
   instruction-reviewer** for Phases 2, 3, 4's Deliverable 3 and 5, with
   **claude-code-guide** added for Phase 5's `src/CLAUDE.md` edit. **Phases 2 and 3
   dispatch no python-engineer** — a phase that finds itself needing one has crossed its own
   boundary and must stop.
   ⚠ **CORRECTED 2026-08-27 (orchestrator ruling; site list WIDENED the same day to all four
   command specs) — this step UNDER-STATES the claude-code-guide route; it is corrected here,
   not rewritten.** The pass is owed for **EVERY command-spec `main.md` edit in this plan —
   Phase 2's `plan/main.md`, Phase 3's `breakdown/main.md`, Phase 4's `verify/main.md`
   (Deliverable 3 only) and Phase 5's `configure/main.md`** — as well as Phase 5's
   `src/CLAUDE.md` edit. All five ship into a target project's `.claude/`, and the repo rule
   has **no frontmatter carve-out**. **Phase 3's `qa-engineer.md` / `qa-reviewer.md` edits
   keep the recorded-skip route only while their fenced `yaml` meta-blocks stay
   byte-unchanged.** Full ruling at Phase 2's route paragraph. **The python-engineer boundary
   sentence above is unchanged and still binds**, and Phases 1 and 4's Deliverables 1–2 owe
   no pass, touching no shipped `.claude/` file.
8. **Do not let Phase 4's momentum turn the advisory arm into a gate.** D3 fork (i) is a
   ratified position with a named trigger, not a first draft. The lane's value in v1 is
   that a feature's user flows get declared, owned, written and run at all — **the gate is
   a later, separate decision that owes a flake policy (OQ-4) it does not yet have.**
   ⚠ **CORRECTED 2026-08-27 — drafting-time overstatement:** while Phase 0 is open, fork
   (i) is the RECOMMENDED arm, not a ratified position. This step's guidance binds once
   Phase 0 ratifies D3, and only in the arm it picks — under (i) the step stands as
   written; under (ii) it is RETIRED, not softened. Until then nothing here is decided
   (the Status line owns that claim).
   ✅ **RESOLVED 2026-08-27 — Phase 0 CLOSED and D3 ratified fork (i), so this step STANDS AS
   WRITTEN and binds from now on.** The retirement branch never fires, and the correction
   above has discharged its own forward reference: fork (i) IS a ratified position with a
   named trigger, exactly as the step's original wording says.
